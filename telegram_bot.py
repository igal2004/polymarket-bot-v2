"""
telegram_bot.py — בוט מומחים פולימרקט
מריץ שרת Flask לקבלת webhook + לולאת מעקב ברקע לסריקת ארנקי מומחים.
"""
_PENDING_TRADES = {}
_PENDING_TRADES_FILE = "/tmp/pending_trades.json"

import asyncio
import threading
import time
import logging
import datetime
import pytz
import os
import json
import requests as req
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DRY_RUN, WALLET_ADDRESS,
    ENFORCE_BALANCE_CHECK, MAX_SINGLE_TRADE_PERCENT, DAILY_REPORT_HOUR, DAILY_REPORT_MINUTE,
    POLL_INTERVAL_SECONDS
)
from polymarket_client import get_wallet_usdc_balance
from portfolio import get_portfolio_summary
from dry_run_journal import format_summary_message, format_trades_list, record_trade, check_and_settle_open_trades, reset_journal
from tracker import ExpertTracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)
ISRAEL_TZ = pytz.timezone("Asia/Jerusalem")

# Global event loop reference so the background thread can schedule coroutines
_main_loop: asyncio.AbstractEventLoop = None
_ptb_app: Application = None


def _load_pending_trades():
    """Load pending trades from disk on startup."""
    global _PENDING_TRADES
    try:
        if os.path.exists(_PENDING_TRADES_FILE):
            with open(_PENDING_TRADES_FILE, 'r') as f:
                _PENDING_TRADES = json.load(f)
            logger.info(f"טעינת {len(_PENDING_TRADES)} עסקאות ממתינות מהדיסק")
    except Exception as e:
        logger.warning(f"לא ניתן לטעון עסקאות ממתינות: {e}")
        _PENDING_TRADES = {}


def _save_pending_trades():
    """Save pending trades to disk."""
    try:
        with open(_PENDING_TRADES_FILE, 'w') as f:
            json.dump(_PENDING_TRADES, f)
    except Exception as e:
        logger.warning(f"לא ניתן לשמור עסקאות ממתינות: {e}")


def _store_pending(signal: dict) -> str:
    """Store signal in memory and on disk, return a short key."""
    key = signal['trade_id'][:10]
    _PENDING_TRADES[key] = signal
    if len(_PENDING_TRADES) > 50:
        oldest_keys = list(_PENDING_TRADES.keys())[:-50]
        for k in oldest_keys:
            _PENDING_TRADES.pop(k, None)
    _save_pending_trades()
    return key


# ─── Command Handlers ────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    mode = "DRY RUN (בדיקה)" if DRY_RUN else "מסחר אמיתי"
    await update.message.reply_text(
        f"*בוט מומחים פולימרקט*\n\nמצב: {mode}\n\n"
        f"/p\_ping — בדוק אם הבוט פעיל\n"
        f"/p\_portfolio — פורטפוליו\n"
        f"/p\_status — סטטוס\n"
        f"/p\_report — דוח\n"
        f"/p\_dryrun — סיכום עסקאות מדומות\n"
        f"/p\_dryrun\_trades — רשימת עסקאות\n"
        f"/p\_validate — בדיקת כתובות\n"
        f"/cutdry — סיכום DRY RUN",
        parse_mode="Markdown"
    )


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from config import EXPERT_WALLETS, WHALE_WALLETS
    mode = "DRY RUN" if DRY_RUN else "מסחר אמיתי"
    balance = get_wallet_usdc_balance(WALLET_ADDRESS)
    max_per_trade = balance * MAX_SINGLE_TRADE_PERCENT / 100 if balance > 0 else 0
    await update.message.reply_text(
        f"*סטטוס בוט פולימרקט*\n\n"
        f"מצב: {mode}\n"
        f"🐋 לווייתנים במעקב: {len(WHALE_WALLETS)}\n"
        f"🧐 מומחים במעקב: {len(EXPERT_WALLETS)}\n"
        f"בדיקה כל: {POLL_INTERVAL_SECONDS} שניות\n\n"
        f"*הגנות ארנק:*\n"
        f"יתרה: ${balance:.2f} USDC\n"
        f"מקסימום לעסקה: ${max_per_trade:.2f}",
        parse_mode="Markdown"
    )


async def cmd_portfolio(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("מושך נתוני פורטפוליו...")
    summary = get_portfolio_summary()
    await update.message.reply_text(summary, parse_mode="Markdown")


async def cmd_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("מכין דוח...")
    summary = get_portfolio_summary()
    await update.message.reply_text(f"*דוח — בוט פולימרקט*\n\n{summary}", parse_mode="Markdown")


async def cmd_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now(ISRAEL_TZ).strftime("%H:%M:%S")
    mode = "DRY RUN" if DRY_RUN else "מסחר אמיתי"
    await update.message.reply_text(
        f"🟢 *הבוט פעיל!*\n\nשעה: {now}\nמצב: {mode}",
        parse_mode="Markdown"
    )


async def cmd_validate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("מתחיל בדיקת כתובות... (30 שניות)")
    await validate_expert_wallets_job(ctx)


async def cmd_dryrun(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = format_summary_message()
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_reset_dryrun(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """איפוס יומן DRY RUN — מחיקת כל העסקאות ואיפוס היתרה."""
    # First ask for confirmation via inline keyboard
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ כן, אפס הכל", callback_data="reset_dryrun|confirm"),
        InlineKeyboardButton("❌ ביטול", callback_data="reset_dryrun|cancel")
    ]])
    await update.message.reply_text(
        "⚠️ *אזהרה — איפוס יומן DRY RUN*\n\n"
        "פעולה זו תמחק את *כל* העסקאות הקיימות ותאפס את היתרה המדומה.\n\n"
        "האם אתה בטוח?",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def cmd_dryrun_trades(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = format_trades_list()
    await update.message.reply_text(msg, parse_mode="Markdown")




async def cmd_compare(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from dry_run_journal import get_summary
    s = get_summary()
    if s["total"] == 0:
        await update.message.reply_text("אין עסקאות ביומן עדיין.")
        return
    by_expert = s["by_expert"]
    if not by_expert:
        await update.message.reply_text("אין נתוני מומחים עדיין.")
        return
    sorted_experts = sorted(by_expert.items(), key=lambda x: x[1].get("avg_roi", 0), reverse=True)
    header = "📊 *השוואת מומחים — לפי ROI*\n"
    lines = [header]
    medals = ["🥇", "🥈", "🥉"]
    for rank, (exp, data) in enumerate(sorted_experts, 1):
        medal = medals[rank-1] if rank <= 3 else str(rank) + "."
        closed = data["won"] + data["lost"]
        wr = round(data["won"] / closed * 100, 0) if closed > 0 else 0
        pnl = data["pnl"]
        pnl_str = "+${:.2f}".format(pnl) if pnl >= 0 else "-${:.2f}".format(abs(pnl))
        status_icon = "✅" if data["avg_roi"] > 0 else "❌"
        line = (
            "{} *{}*\n"
            "   ROI: {} {:.1f}% | הצלחה: {}%\n"
            "   עסקאות: {} | פתוחות: {} | {}\n"
        ).format(medal, exp, status_icon, data["avg_roi"], int(wr), data["total"], data["open"], pnl_str)
        lines.append(line)
    lines.append("/p\_dryrun — סיכום מלא")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_discover(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 *סורק מומחים חדשים...* (זה עשוי לקחת 15 שניות)",
        parse_mode="Markdown"
    )
    try:
        from market_analysis import discover_top_traders
        import asyncio as _asyncio
        candidates = await _asyncio.get_event_loop().run_in_executor(None, discover_top_traders)
        if not candidates:
            await update.message.reply_text(
                "🔍 לא נמצאו מועמדים חדשים העומדים בקריטריונים."
            )
            return
        lines = ["🔍 *מומחים חדשים שנמצאו*\n"]
        for c in candidates:
            lines.append(
                "  🆕 *{}*\n"
                "    💰 רווח: ${:,.0f} | 🎯 הצלחה: {:.0f}%\n"
                "    💳 כתובת: `{}`\n".format(
                    c["name"], c["pnl"], c["win_rate"], c["wallet"]
                )
            )
        lines.append("\nלהוספת מומחה למעקב — עדכן את config.py ב-EXPERT\_WALLETS")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("שגיאה בסריקה: {}".format(e))


# ─── Core Logic ──────────────────────────────────────────────────────────────

def check_wallet_protection(trade_amount_usd: float) -> tuple:
    if not ENFORCE_BALANCE_CHECK:
        return True, ""
    balance = get_wallet_usdc_balance(WALLET_ADDRESS)
    if balance <= 0:
        return False, "לא ניתן לשלוף יתרת ארנק"
    if trade_amount_usd > balance:
        return False, f"סכום עסקה (${trade_amount_usd:.2f}) גדול מהיתרה (${balance:.2f})"
    max_allowed = max(balance * MAX_SINGLE_TRADE_PERCENT / 100, 50.0)
    if trade_amount_usd > max_allowed:
        return False, f"חורג מ-{MAX_SINGLE_TRADE_PERCENT}% מהיתרה (מקסימום: ${max_allowed:.2f})"
    return True, ""


async def send_trade_alert(signal: dict):
    """Sends a trade alert message to Telegram with enhanced analysis."""
    from config import DEFAULT_TRADE_AMOUNT_USD
    from expert_profiles import get_expert_tag, get_expert_warning, get_hot_alert_header, get_automation_priority_rank
    from market_analysis import (
        get_current_market_price, analyze_price_gap,
        get_ai_risk_analysis, calculate_dynamic_trade_amount
    )

    expert = signal["expert_name"]
    market = signal["market_question"]
    outcome = signal["outcome"]
    price = signal["price"]
    usd_val = signal["usd_value"]
    url = signal.get("market_url", "")
    asset_id = signal.get("asset_id", "")
    is_new_expert = signal.get("is_new_expert", False)

    balance = get_wallet_usdc_balance(WALLET_ADDRESS) if ENFORCE_BALANCE_CHECK else None

    # Dynamic trade amount based on expert ROI history
    base_amount = min(DEFAULT_TRADE_AMOUNT_USD,
                      (balance * MAX_SINGLE_TRADE_PERCENT / 100) if balance and balance > 0 else DEFAULT_TRADE_AMOUNT_USD)
    trade_amount, dynamic_label = calculate_dynamic_trade_amount(expert, base_amount, balance)

    signal["_trade_amount"] = trade_amount
    signal['timestamp'] = datetime.datetime.utcnow().isoformat()
    now_il = datetime.datetime.now(ISRAEL_TZ).strftime("%H:%M")

    short_key = _store_pending(signal)

    price_pct = price * 100
    if price <= 0.3:
        price_emoji = "סיכון גבוה"
    elif price <= 0.5:
        price_emoji = "לא בטוח"
    elif price <= 0.7:
        price_emoji = "סביר"
    else:
        price_emoji = "סבירות גבוהה"

    balance_line = f"\n💰 יתרתך: ${balance:.2f}" if balance else ""

    trader_type = signal.get("trader_type", "expert")
    new_tag = " 🆕בבדיקה" if is_new_expert else ""
    if trader_type == "whale":
        alert_header = f"🐋 *עסקת לווייתן חדשה{new_tag}* — {now_il}"
        trader_label = "לווייתן"
    else:
        alert_header = f"🚨 *עסקת מומחה חדשה{new_tag}* — {now_il}"
        trader_label = "מומחה"

    end_date = signal.get("end_date")
    end_date_line = f"\n📅 פקיעת שוק: *{end_date}*" if end_date else ""

    # Expert risk profile tag + hot signal check
    expert_tag = get_expert_tag(expert)
    expert_warning = get_expert_warning(expert, price)
    risk_profile_line = f"\n🏷️ פרופיל: *{expert_tag}*"
    warning_line = f"\n{expert_warning}" if expert_warning else ""
    hot_header = get_hot_alert_header(expert)
    priority_rank = get_automation_priority_rank(expert)
    priority_line = f"\n🏆 עדיפות אוטומציה: *#{priority_rank}*" if priority_rank <= 8 else ""

    # Real-time price & gap analysis
    current_price = get_current_market_price(asset_id)
    gap_info = analyze_price_gap(price, current_price, outcome)
    price_gap_line = ""
    if gap_info["analysis"] and current_price is not None:
        curr_pct = current_price * 100
        price_gap_line = (
            f"\n📊 מחיר נוכחי: *{current_price:.3f}* ({curr_pct:.1f}%)"
            f"\n{gap_info['analysis']}"
        )

    # Dynamic sizing label
    dynamic_line = f"\n🧠 סכום דינמי: *${trade_amount:.2f}* ({dynamic_label})" if dynamic_label else ""

    text = (
        f"{hot_header}{alert_header}\n\n"
        f"👤 {trader_label}: *{expert}*\n"
        f"📊 שוק: {market[:80]}\n"
        f"🎯 כיוון: *{outcome}*\n"
        f"💵 מחיר מומחה: *{price:.3f}* ({price_pct:.1f}%) — {price_emoji}"
        f"{risk_profile_line}{warning_line}"
        f"{price_gap_line}\n"
        f"💰 סכום {trader_label}: ${usd_val:.0f}"
        f"{dynamic_line}{priority_line}{balance_line}{end_date_line}\n\n"
        f"🔗 [פתח שוק]({url})"
    )

    # Quick amount buttons + confirm/cancel
    half = round(trade_amount * 0.5, 2)
    double = round(min(trade_amount * 2, base_amount * 2), 2)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"✅ ${trade_amount:.0f} (מומלץ)", callback_data=f"ok|{short_key}"),
            InlineKeyboardButton(f"🟡 ${half:.0f} (חצי)", callback_data=f"ok_custom|{short_key}|{half}"),
        ],
        [
            InlineKeyboardButton(f"🟢 ${double:.0f} (כפול)", callback_data=f"ok_custom|{short_key}|{double}"),
            InlineKeyboardButton("❌ בטל", callback_data=f"no|{short_key}"),
        ]
    ])

    try:
        msg = await _ptb_app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text=text,
            parse_mode="Markdown", reply_markup=keyboard,
            disable_web_page_preview=True
        )
        logger.info(f"התראה נשלחה, key={short_key}, expert={expert}")

        # Send AI risk analysis as follow-up (non-blocking)
        ai_analysis = get_ai_risk_analysis(market, outcome, price, expert, usd_val)
        if ai_analysis:
            await _ptb_app.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f"🧠 *ניתוח AI לעסקה:*\n{ai_analysis}",
                parse_mode="Markdown",
                reply_to_message_id=msg.message_id
            )
    except Exception as e:
        logger.error(f"שגיאה בשליחת התראה: {e}")


def _on_new_trade(signal: dict):
    """Callback from ExpertTracker (runs in background thread). Schedules the async alert."""
    if _main_loop is None or _ptb_app is None:
        logger.warning("לולאת האירועים עדיין לא מוכנה, מדלג על התראה")
        return
    future = asyncio.run_coroutine_threadsafe(send_trade_alert(signal), _main_loop)
    try:
        future.result(timeout=30)
    except Exception as e:
        logger.error(f"שגיאה בשליחת התראה מהחוט הרקע: {e}")


def _tracker_loop():
    """Background thread: runs ExpertTracker.check_once() every POLL_INTERVAL_SECONDS."""
    logger.info(f"לולאת מעקב מומחים מתחילה (כל {POLL_INTERVAL_SECONDS} שניות)")
    tracker = ExpertTracker(on_new_trade_callback=_on_new_trade)
    while True:
        try:
            tracker.check_once()
        except Exception as e:
            logger.error(f"שגיאה בלולאת המעקב: {e}")
        time.sleep(POLL_INTERVAL_SECONDS)


# ─── Callback Handler ─────────────────────────────────────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        data = query.data
        parts = data.split('|')
        if len(parts) < 2:
            await query.edit_message_text("❌ נתוני כפתור לא תקינים.")
            return

        action = parts[0]

        # Handle reset_dryrun confirmation
        if action == "reset_dryrun":
            choice = parts[1] if len(parts) > 1 else "cancel"
            if choice == "confirm":
                try:
                    result = reset_journal()
                    await query.edit_message_text(
                        f"✅ *יומן DRY RUN אופס בהצלחה*\n\n"
                        f"🗑 נמחקו: *{result['deleted']}* עסקאות\n"
                        f"💰 יתרה חדשה: *${result['new_balance']:.2f}*\n\n"
                        f"📋 /p\_dryrun — סיכום נקי",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    await query.edit_message_text(f"❌ שגיאה באיפוס: {e}")
            else:
                await query.edit_message_text("❌ ביטול — היומן נשמר.")
            return

        short_key = parts[1]
        signal = _PENDING_TRADES.get(short_key)

        if signal is None:
            await query.edit_message_text(
                "⚠️ *פג תוקף ההתראה*\n\n"
                "הבוט הופעל מחדש ואיבד את נתוני העסקה.\n"
                "המתן להתראה חדשה.",
                parse_mode="Markdown"
            )
            return

        trade_amount = signal.get("_trade_amount", 50.0)
        market = signal.get("market_question", "שוק")[:40]
        expert = signal.get("expert_name", "מומחה")
        outcome = signal.get("outcome", "YES")

        if action in ("ok", "ok_custom"):
            # Determine actual amount
            if action == "ok_custom" and len(parts) >= 3:
                try:
                    trade_amount = float(parts[2])
                except ValueError:
                    trade_amount = signal.get("_trade_amount", 50.0)

            allowed, reason = check_wallet_protection(trade_amount)
            balance = get_wallet_usdc_balance(WALLET_ADDRESS) if ENFORCE_BALANCE_CHECK else None
            balance_line = f"\nיתרה: ${balance:.2f}" if balance else ""

            if not allowed:
                await query.edit_message_text(
                    f"🛑 *נחסם — הגנת ארנק*\n\n{reason}",
                    parse_mode="Markdown"
                )
                return

            if DRY_RUN:
                trade_id = record_trade(signal, trade_amount)
                await query.edit_message_text(
                    f"✅ *DRY RUN — נרשם ביומן*\n\n"
                    f"מומחה: {expert}\n"
                    f"שוק: {market}\n"
                    f"כיוון: {outcome}\n"
                    f"סכום: ${trade_amount:.2f}{balance_line}\n\n"
                    f"📋 מספר עסקה: #{trade_id}\n"
                    f"הקלד /p\_dryrun לסיכום",
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(
                    f"✅ *פקודת קנייה נשלחה*\n\n"
                    f"מומחה: {expert}\n"
                    f"שוק: {market}\n"
                    f"כיוון: {outcome}\n"
                    f"סכום: ${trade_amount:.2f}",
                    parse_mode="Markdown"
                )

        elif action == "no":
            await query.edit_message_text(
                f"❌ *בוטל*\n\nשוק: {market}",
                parse_mode="Markdown"
            )

        _PENDING_TRADES.pop(short_key, None)

    except Exception as e:
        logger.error(f"שגיאה ב-handle_callback: {e}", exc_info=True)
        try:
            await query.edit_message_text("❌ אירעה שגיאה. נסה שוב.")
        except Exception:
            pass


# ─── Scheduled Jobs ───────────────────────────────────────────────────────────

async def validate_expert_wallets_job(ctx: ContextTypes.DEFAULT_TYPE):
    from config import EXPERT_WALLETS
    valid, invalid, inactive = [], [], []
    for name, wallet in EXPERT_WALLETS.items():
        try:
            if not wallet.startswith("0x") or len(wallet) != 42:
                invalid.append(f"❌ {name}: פורמט שגוי")
                continue
            r = req.get(
                "https://data-api.polymarket.com/trades",
                params={"user": wallet, "limit": 5},
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                count = len(data) if isinstance(data, list) else 0
                if count > 0:
                    valid.append(f"✅ {name}: {count} עסקאות")
                else:
                    inactive.append(f"⚠️ {name}: אין עסקאות")
            else:
                inactive.append(f"⚠️ {name}: API error {r.status_code}")
        except Exception:
            inactive.append(f"⚠️ {name}: שגיאה")

    lines = [f"*בדיקת כתובות מומחים*\n\nסה\"כ: {len(EXPERT_WALLETS)} ארנקים\n"]
    if valid:
        lines.append(f"*תקינים ({len(valid)}):*")
        lines.extend(valid)
    if inactive:
        lines.append(f"\n*לא פעילים ({len(inactive)}):*")
        lines.extend(inactive)
    if invalid:
        lines.append(f"\n*שגויים ({len(invalid)}):*")
        lines.extend(invalid)

    await ctx.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text="\n".join(lines),
        parse_mode="Markdown"
    )


async def daily_report_job(ctx: ContextTypes.DEFAULT_TYPE):
    balance = get_wallet_usdc_balance(WALLET_ADDRESS) if ENFORCE_BALANCE_CHECK else None
    summary = get_portfolio_summary()
    balance_line = f"\n💰 יתרה: ${balance:.2f} USDC" if balance else ""
    await ctx.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=f"*דוח יומי — בוט פולימרקט*{balance_line}\n\n{summary}",
        parse_mode="Markdown"
    )


# ─── Main Entry Point ─────────────────────────────────────────────────────────

async def main():
    global _main_loop, _ptb_app

    _main_loop = asyncio.get_running_loop()

    # Load persisted pending trades from disk
    _load_pending_trades()

    # Build the PTB application
    _ptb_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    _ptb_app.add_handler(CommandHandler("p_ping", cmd_ping))
    _ptb_app.add_handler(CommandHandler("start", cmd_start))
    _ptb_app.add_handler(CommandHandler("p_start", cmd_start))
    _ptb_app.add_handler(CommandHandler("p_status", cmd_status))
    _ptb_app.add_handler(CommandHandler("p_portfolio", cmd_portfolio))
    _ptb_app.add_handler(CommandHandler("p_report", cmd_report))
    _ptb_app.add_handler(CommandHandler("p_validate", cmd_validate))
    _ptb_app.add_handler(CommandHandler("p_dryrun", cmd_dryrun))
    _ptb_app.add_handler(CommandHandler("p_dryrun_trades", cmd_dryrun_trades))
    _ptb_app.add_handler(CommandHandler("p_reset_dryrun", cmd_reset_dryrun))
    _ptb_app.add_handler(CommandHandler("p_compare", cmd_compare))
    _ptb_app.add_handler(CommandHandler("p_discover", cmd_discover))
    _ptb_app.add_handler(CommandHandler("cutdry", cmd_dryrun))
    _ptb_app.add_handler(CallbackQueryHandler(handle_callback))

    # Start the background tracker thread
    tracker_thread = threading.Thread(target=_tracker_loop, daemon=True, name="expert-tracker")
    tracker_thread.start()
    logger.info("חוט מעקב מומחים הופעל")

    # Initialize and start PTB (polling mode — no webhook needed)
    await _ptb_app.initialize()
    await _ptb_app.start()

    # Send startup message
    try:
        from config import EXPERT_WALLETS, WHALE_WALLETS
        now_il = datetime.datetime.now(ISRAEL_TZ).strftime("%H:%M:%S")
        await _ptb_app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=(
                f"🟢 *בוט פולימרקט הופעל*\n\n"
                f"שעה: {now_il}\n"
                f"מצב: {'DRY RUN' if DRY_RUN else 'מסחר אמיתי'}\n"
                f"🧐 מומחים במעקב: {len(EXPERT_WALLETS)}\n"
                f"🐋 לווייתנים במעקב: {len(WHALE_WALLETS)}\n"
                f"💾 גיבוי יומי אוטומטי פעיל"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"לא ניתן לשלוח הודעת הפעלה: {e}")

    # Run polling
    logger.info("מתחיל polling...")
    await _ptb_app.updater.start_polling(drop_pending_updates=True)

    # Schedule daily backup job (every 24 hours)
    async def _daily_backup_loop():
        await asyncio.sleep(3600)  # First backup after 1 hour
        while True:
            try:
                from dry_run_journal import get_summary
                import json as _json
                s = get_summary()
                backup_data = {
                    "_poly_backup": True,
                    "timestamp": datetime.datetime.now(ISRAEL_TZ).strftime("%Y-%m-%d %H:%M:%S"),
                    "trades": s.get("trades", []),
                    "sim_balance": s.get("sim_balance"),
                    "initial_balance": s.get("initial_balance"),
                    "total": s.get("total"),
                    "won": s.get("won"),
                    "lost": s.get("lost"),
                }
                backup_json = _json.dumps(backup_data, ensure_ascii=False)
                max_len = 3800
                chunks = [backup_json[i:i+max_len] for i in range(0, len(backup_json), max_len)]
                for idx, chunk in enumerate(chunks, 1):
                    part = f" ({idx}/{len(chunks)})" if len(chunks) > 1 else ""
                    await _ptb_app.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=f"💾 *גיבוי יומי — בוט פולימרקט{part}*\n`{chunk}`",
                        parse_mode="Markdown",
                        disable_notification=True,
                    )
                logger.info("גיבוי יומי נשלח לטלגרם")
            except Exception as e:
                logger.warning(f"שגיאה בגיבוי יומי: {e}")
            await asyncio.sleep(86400)  # 24 hours

    asyncio.ensure_future(_daily_backup_loop())

    # Schedule settlement check loop (every hour)
    async def _settlement_loop():
        await asyncio.sleep(300)  # First check after 5 minutes
        while True:
            try:
                settled = await asyncio.get_event_loop().run_in_executor(
                    None, check_and_settle_open_trades
                )
                for trade in settled:
                    status = trade["status"]
                    emoji = "✅" if status == "won" else "❌"
                    result = trade.get("result_usd", 0) or 0
                    result_str = f"+${result:.2f}" if result >= 0 else f"-${abs(result):.2f}"
                    winning = trade.get("winning_outcome", "?")
                    outcome_label = 'זכייה' if status == 'won' else 'הפסד'
                    settle_text = (
                        f"{emoji} *עסקה #{trade['id']} נסגרה \u2014 {outcome_label}*\n\n"
                        f"👤 מומחה: {trade['expert']}\n"
                        f"📊 שוק: {trade['market'][:70]}\n"
                        f"🎯 כיוון שלך: *{trade['outcome']}* | תוצאה בפועל: *{winning}*\n"
                        f"💰 השקעת: ${trade['amount_usd']:.2f} | תוצאה: *{result_str}*\n\n"
                        f"📋 /p\_dryrun \u2014 סיכום מעודכן"
                    )
                    await _ptb_app.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=settle_text,
                        parse_mode="Markdown"
                    )
                    logger.info(f"Settlement notification sent for trade #{trade['id']}")
            except Exception as e:
                logger.warning(f"שגיאה בלולאת הסגירה: {e}")
            await asyncio.sleep(3600)  # Check every hour

    asyncio.ensure_future(_settlement_loop())

    # Weekly performance report (every Sunday at 09:00 Israel time)
    async def _weekly_report_loop():
        while True:
            try:
                now = datetime.datetime.now(ISRAEL_TZ)
                # Calculate seconds until next Sunday 09:00
                days_until_sunday = (6 - now.weekday()) % 7  # 6 = Sunday in Python
                if days_until_sunday == 0 and now.hour >= 9:
                    days_until_sunday = 7
                next_sunday = now.replace(hour=9, minute=0, second=0, microsecond=0) + datetime.timedelta(days=days_until_sunday)
                wait_secs = (next_sunday - now).total_seconds()
                await asyncio.sleep(wait_secs)

                from dry_run_journal import get_summary
                s = get_summary()
                if s["total"] == 0:
                    continue

                pnl_sign = "+" if s["total_pnl"] >= 0 else ""
                pnl_emoji = "\U0001f4c8" if s["total_pnl"] >= 0 else "\U0001f4c9"

                # Top 3 experts by ROI
                top_experts = sorted(
                    s["by_expert"].items(),
                    key=lambda x: x[1].get("avg_roi", 0),
                    reverse=True
                )[:3]
                top_lines = []
                for rank, (exp, data) in enumerate(top_experts, 1):
                    medals = ["\U0001f947", "\U0001f948", "\U0001f949"]
                    top_lines.append(
                        f"  {medals[rank-1]} {exp}: ROI {data.get('avg_roi', 0):.1f}% | "
                        f"{data['total']} \u05e2\u05e1\u05e7\u05d0\u05d5\u05ea"
                    )

                report = (
                    f"\U0001f4ca *\u05d3\u05d5\"\u05d7 \u05e9\u05d1\u05d5\u05e2\u05d9 \u2014 \u05d1\u05d5\u05d8 \u05e4\u05d5\u05dc\u05d9\u05de\u05e8\u05e7\u05d8*\n"
                    f"\u05e9\u05d1\u05d5\u05e2: {(now - datetime.timedelta(days=7)).strftime('%d/%m')} \u2014 {now.strftime('%d/%m/%Y')}\n\n"
                    f"\U0001f4b0 *\u05d9\u05ea\u05e8\u05d4:* ${s['sim_balance']:.2f} (\u05d4\u05ea\u05d7\u05dc\u05d4: ${s['initial_balance']:.2f})\n"
                    f"{pnl_emoji} *\u05e8\u05d5\u05d5\u05d7/\u05d4\u05e4\u05e1\u05d3:* {pnl_sign}${s['total_pnl']:.2f}\n\n"
                    f"\U0001f4ca *\u05e1\u05d8\u05d8\u05d9\u05e1\u05d8\u05d9\u05e7\u05d5\u05ea:*\n"
                    f"  \u05e1\u05d4\"\u05db \u05e2\u05e1\u05e7\u05d0\u05d5\u05ea: {s['total']} | \u05e4\u05ea\u05d5\u05d7\u05d5\u05ea: {s['open']}\n"
                    f"  \u2705 \u05d6\u05db\u05d9\u05d9\u05d5\u05ea: {s['won']} | \u274c \u05d4\u05e4\u05e1\u05d3\u05d5\u05ea: {s['lost']}\n"
                    f"  \U0001f3af \u05d0\u05d7\u05d5\u05d6 \u05d4\u05e6\u05dc\u05d7\u05d4: {s['win_rate']}%\n\n"
                    f"\U0001f3c6 *\u05de\u05d5\u05de\u05d7\u05d9\u05dd \u05de\u05d5\u05d1\u05d9\u05dc\u05d9\u05dd:*\n" +
                    "\n".join(top_lines) +
                    f"\n\n/p\_dryrun \u2014 \u05e1\u05d9\u05db\u05d5\u05dd \u05de\u05dc\u05d0"
                )
                await _ptb_app.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=report,
                    parse_mode="Markdown"
                )
                logger.info("\u05d3\u05d5\u05d7 \u05e9\u05d1\u05d5\u05e2\u05d9 \u05e0\u05e9\u05dc\u05d7")
            except Exception as e:
                logger.warning(f"\u05e9\u05d2\u05d9\u05d0\u05d4 \u05d1\u05d3\u05d5\u05d7 \u05e9\u05d1\u05d5\u05e2\u05d9: {e}")
                await asyncio.sleep(3600)

    asyncio.ensure_future(_weekly_report_loop())

    # Open trades daily reminder (every day at 18:00 Israel time)
    async def _open_trades_reminder_loop():
        await asyncio.sleep(600)  # First check after 10 minutes
        while True:
            try:
                now = datetime.datetime.now(ISRAEL_TZ)
                next_18 = now.replace(hour=18, minute=0, second=0, microsecond=0)
                if now.hour >= 18:
                    next_18 += datetime.timedelta(days=1)
                wait_secs = (next_18 - now).total_seconds()
                await asyncio.sleep(wait_secs)

                from market_analysis import get_open_trades_summary
                open_trades = get_open_trades_summary()
                if not open_trades:
                    continue

                lines = [f"\U0001f4cb *\u05ea\u05d6\u05db\u05d5\u05e8\u05ea \u05e2\u05e1\u05e7\u05d0\u05d5\u05ea \u05e4\u05ea\u05d5\u05d7\u05d5\u05ea* \u2014 {len(open_trades)} \u05e2\u05e1\u05e7\u05d0\u05d5\u05ea\n"]
                for t in open_trades[:10]:
                    end = t.get("end_date", "\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2")
                    lines.append(
                        f"  #{t['id']} {t['expert']} | {t['outcome']} | "
                        f"${t['amount_usd']:.0f} | \U0001f4c5 {end}"
                    )
                if len(open_trades) > 10:
                    lines.append(f"  ... \u05d5\u05e2\u05d5\u05d3 {len(open_trades)-10} \u05e2\u05e1\u05e7\u05d0\u05d5\u05ea")
                lines.append("\n/p\_dryrun\_trades \u2014 \u05e8\u05e9\u05d9\u05de\u05d4 \u05de\u05dc\u05d0\u05d4")

                await _ptb_app.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text="\n".join(lines),
                    parse_mode="Markdown",
                    disable_notification=True
                )
            except Exception as e:
                logger.warning(f"\u05e9\u05d2\u05d9\u05d0\u05d4 \u05d1\u05ea\u05d6\u05db\u05d5\u05e8\u05ea \u05e2\u05e1\u05e7\u05d0\u05d5\u05ea: {e}")
                await asyncio.sleep(3600)

    asyncio.ensure_future(_open_trades_reminder_loop())

    # Monthly expert discovery (every 1st of month at 08:00)
    async def _monthly_discovery_loop():
        await asyncio.sleep(1800)  # First check after 30 minutes
        while True:
            try:
                now = datetime.datetime.now(ISRAEL_TZ)
                # Calculate seconds until 1st of next month at 08:00
                if now.day == 1 and now.hour < 8:
                    next_run = now.replace(hour=8, minute=0, second=0, microsecond=0)
                else:
                    if now.month == 12:
                        next_run = now.replace(year=now.year+1, month=1, day=1, hour=8, minute=0, second=0, microsecond=0)
                    else:
                        next_run = now.replace(month=now.month+1, day=1, hour=8, minute=0, second=0, microsecond=0)
                wait_secs = (next_run - now).total_seconds()
                await asyncio.sleep(wait_secs)

                from market_analysis import discover_top_traders
                candidates = await asyncio.get_event_loop().run_in_executor(
                    None, discover_top_traders
                )

                if not candidates:
                    await _ptb_app.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text="\U0001f50d *\u05e1\u05e8\u05d9\u05e7\u05ea \u05de\u05d5\u05de\u05d7\u05d9\u05dd \u05d7\u05d3\u05e9\u05d9\u05dd* \u2014 \u05dc\u05d0 \u05e0\u05de\u05e6\u05d0\u05d5 \u05de\u05d5\u05e2\u05de\u05d3\u05d9\u05dd \u05d7\u05d3\u05e9\u05d9\u05dd \u05d4\u05d7\u05d5\u05d3\u05e9.",
                        parse_mode="Markdown"
                    )
                    continue

                lines = [f"\U0001f50d *\u05de\u05d5\u05de\u05d7\u05d9\u05dd \u05d7\u05d3\u05e9\u05d9\u05dd \u05e9\u05e0\u05de\u05e6\u05d0\u05d5* \u2014 {now.strftime('%m/%Y')}\n"]
                for c in candidates:
                    lines.append(
                        f"  \U0001f195 *{c['name']}*\n"
                        f"    \U0001f4b0 \u05e8\u05d5\u05d5\u05d7: ${c['pnl']:,.0f} | \U0001f3af \u05d4\u05e6\u05dc\u05d7\u05d4: {c['win_rate']:.0f}%\n"
                        f"    \U0001f4b3 \u05db\u05ea\u05d5\u05d1\u05ea: `{c['wallet']}`"
                    )
                lines.append("\n\u05dc\u05d4\u05d5\u05e1\u05e4\u05ea \u05de\u05d5\u05de\u05d7\u05d4 \u05dc\u05de\u05e2\u05e7\u05d1 \u2014 \u05e2\u05d3\u05db\u05df \u05d0\u05ea config.py \u05d1-EXPERT\_WALLETS")

                await _ptb_app.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text="\n".join(lines),
                    parse_mode="Markdown"
                )
                logger.info(f"\u05d3\u05d5\u05d7 \u05d2\u05d9\u05dc\u05d5\u05d9 \u05de\u05d5\u05de\u05d7\u05d9\u05dd \u05e0\u05e9\u05dc\u05d7 \u2014 {len(candidates)} \u05de\u05d5\u05e2\u05de\u05d3\u05d9\u05dd")
            except Exception as e:
                logger.warning(f"\u05e9\u05d2\u05d9\u05d0\u05d4 \u05d1\u05d2\u05d9\u05dc\u05d5\u05d9 \u05de\u05d5\u05de\u05d7\u05d9\u05dd: {e}")
                await asyncio.sleep(3600)

    asyncio.ensure_future(_monthly_discovery_loop())

    # Keep running forever
    try:
        await asyncio.Event().wait()
    finally:
        await _ptb_app.updater.stop()
        await _ptb_app.stop()
        await _ptb_app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
