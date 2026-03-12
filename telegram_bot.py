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
from dry_run_journal import format_summary_message, format_trades_list, record_trade
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
    from config import EXPERT_WALLETS
    mode = "DRY RUN" if DRY_RUN else "מסחר אמיתי"
    balance = get_wallet_usdc_balance(WALLET_ADDRESS)
    max_per_trade = balance * MAX_SINGLE_TRADE_PERCENT / 100 if balance > 0 else 0
    await update.message.reply_text(
        f"*סטטוס בוט פולימרקט*\n\n"
        f"מצב: {mode}\n"
        f"ארנקים במעקב: {len(EXPERT_WALLETS)}\n"
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


async def cmd_dryrun_trades(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = format_trades_list()
    await update.message.reply_text(msg, parse_mode="Markdown")


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
    """Sends a trade alert message to Telegram. Called from the background thread via run_coroutine_threadsafe."""
    from config import DEFAULT_TRADE_AMOUNT_USD

    expert = signal["expert_name"]
    market = signal["market_question"]
    outcome = signal["outcome"]
    price = signal["price"]
    usd_val = signal["usd_value"]
    url = signal.get("market_url", "")

    balance = get_wallet_usdc_balance(WALLET_ADDRESS) if ENFORCE_BALANCE_CHECK else None
    max_trade = (balance * MAX_SINGLE_TRADE_PERCENT / 100) if balance and balance > 0 else DEFAULT_TRADE_AMOUNT_USD
    trade_amount = min(DEFAULT_TRADE_AMOUNT_USD, max_trade)

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

    text = (
        f"🚨 *עסקת מומחה חדשה* — {now_il}\n\n"
        f"👤 מומחה: *{expert}*\n"
        f"📊 שוק: {market[:80]}\n"
        f"🎯 כיוון: *{outcome}*\n"
        f"💵 מחיר: *{price:.3f}* ({price_pct:.1f}%) — {price_emoji}\n"
        f"💰 סכום מומחה: ${usd_val:.0f}\n"
        f"⚡ סכום מוצע: ${trade_amount:.2f}{balance_line}\n\n"
        f"🔗 [פתח שוק]({url})"
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ אשר עסקה", callback_data=f"ok|{short_key}"),
        InlineKeyboardButton("❌ בטל", callback_data=f"no|{short_key}"),
    ]])

    try:
        await _ptb_app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text=text,
            parse_mode="Markdown", reply_markup=keyboard,
            disable_web_page_preview=True
        )
        logger.info(f"התראה נשלחה, key={short_key}, expert={expert}")
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

        if action == "ok":
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
        now_il = datetime.datetime.now(ISRAEL_TZ).strftime("%H:%M:%S")
        await _ptb_app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f"🟢 *בוט פולימרקט הופעל*\n\nשעה: {now_il}\nמצב: {'DRY RUN' if DRY_RUN else 'מסחר אמיתי'}\nמעקב: {len(__import__('config').EXPERT_WALLETS)} מומחים",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"לא ניתן לשלוח הודעת הפעלה: {e}")

    # Run polling
    logger.info("מתחיל polling...")
    await _ptb_app.updater.start_polling(drop_pending_updates=True)

    # Keep running forever
    try:
        await asyncio.Event().wait()
    finally:
        await _ptb_app.updater.stop()
        await _ptb_app.stop()
        await _ptb_app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
