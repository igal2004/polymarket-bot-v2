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
from exit_manager import ExitManager

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


async def cmd_resume_trading(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """הפעלת מסחר מחדש אחרי עצירת Drawdown — /p_resume_trading [סכום]"""
    try:
        from market_analysis import resume_trading as _resume
        from polymarket_client import get_wallet_usdc_balance as _get_bal
        from config import WALLET_ADDRESS as _WA

        # אפשרות לציין סכום ידני: /p_resume_trading 350
        args = ctx.args if ctx and ctx.args else []
        if args:
            try:
                cur_bal = float(args[0])
            except ValueError:
                await update.message.reply_text("❌ סכום לא תקין. שימוש: /p_resume_trading [סכום]")
                return
        else:
            # נסה לשלוף מה-RPC
            cur_bal = _get_bal(_WA)
            if cur_bal is None or cur_bal <= 0:
                # RPC נכשל — בקש מהמשתמש לציין ידנית
                await update.message.reply_text(
                    "⚠️ לא ניתן לשלוף יתרה אוטומטית.\n"
                    "שלח: `/p_resume_trading 323` (הכנס את היתרה הנוכחית שלך)",
                    parse_mode="Markdown"
                )
                return

        _resume(new_peak=cur_bal)   # אפס שיא ליתרה הנוכחית
        await update.message.reply_text(
            f"✅ *מסחר הופעל מחדש!*\n"
            f"יתרת שיא חדשה: *${cur_bal:.2f}*\n"
            f"Drawdown Guard יתחיל למדוד מיתרה זו מעכשיו",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ שגיאה: {e}")


async def cmd_audit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """הרצת בקרה מעגלית ידנית — /p_audit"""
    await update.message.reply_text(
        "🔍 *מריץ בדיקת בקרה מעגלית...* (זה עשוי לקחת 10 שניות)",
        parse_mode="Markdown"
    )
    try:
        import subprocess as _sp
        import os as _os
        _bot_dir = _os.path.dirname(_os.path.abspath(__file__))
        result = _sp.run(
            ["python3.11", "audit_bot.py", "--silent"],
            capture_output=True, text=True, timeout=60,
            cwd=_bot_dir
        )
        output = result.stdout
        passed = output.count("[PASS]")
        failed_count = output.count("[FAIL]")
        warn_count = output.count("[WARN]")
        total = passed + failed_count + warn_count
        status_emoji = "✅" if failed_count == 0 else "❌"
        now_str = datetime.datetime.now(ISRAEL_TZ).strftime("%d/%m/%Y %H:%M")

        lines = [
            f"{status_emoji} *בקרה מעגלית ידנית — {now_str}*\n",
            f"📊 עברו: *{passed}/{total}* | ❌ כשלים: *{failed_count}* | ⚠️ אזהרות: *{warn_count}*\n",
        ]
        if failed_count > 0:
            fail_lines = [l for l in output.split("\n") if "[FAIL]" in l]
            lines.append("*🚨 כשלים:*")
            for fl in fail_lines:
                lines.append(f"  {fl.strip()}")
        if warn_count > 0:
            warn_lines = [l for l in output.split("\n") if "[WARN]" in l]
            lines.append("\n*⚠️ אזהרות:*")
            for wl in warn_lines:
                lines.append(f"  {wl.strip()}")
        if failed_count == 0 and warn_count == 0:
            lines.append("🎉 *כל התכונות פועלות כמצופה!*")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ שגיאה בבקרה: {e}")


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
    # ✅ תיקון: balance יכול להיות None אם ה-RPC נכשל
    if balance is None or balance <= 0:
        return False, "לא ניתן לשלוף יתרת ארנק — עסקה נחסמת"
    if trade_amount_usd > balance:
        return False, f"סכום עסקה (${trade_amount_usd:.2f}) גדול מהיתרה (${balance:.2f})"
    max_allowed = max(balance * MAX_SINGLE_TRADE_PERCENT / 100, 50.0)
    if trade_amount_usd > max_allowed:
        return False, f"חורג מ-{MAX_SINGLE_TRADE_PERCENT}% מהיתרה (מקסימום: ${max_allowed:.2f})"
    return True, ""


async def send_trade_alert(signal: dict):
    """Sends a trade alert message to Telegram with enhanced analysis."""

    # ═══════════════════════════════════════════════════════════════
    # 🔴 PIPELINE — 8-stage unified decision engine
    # ═══════════════════════════════════════════════════════════════
    try:
        from trade_pipeline import run_pipeline, TradeSignal, format_pipeline_summary
        from market_analysis import get_current_market_price as _get_cur_price
        from polymarket_client import get_wallet_usdc_balance as _get_bal
        from config import WALLET_ADDRESS as _WA, DEFAULT_TRADE_AMOUNT_USD
        _bal = _get_bal(_WA)
        # ✅ תיקון: אם balance=None (RPC נכשל) — חסום את העסקה
        if _bal is None:
            logger.warning("יתרת ארנק לא זמינה (RPC נכשל) — עסקה נחסמת")
            return
        _base = DEFAULT_TRADE_AMOUNT_USD

        # ✅ תיקון באג 1: מחיר נוכחי אמיתי מה-API (לא מחיר המומחה)
        _asset_id_pipeline = signal.get("asset_id", "")
        _expert_price      = float(signal.get("price", 0.5))
        _cur_price_real    = _get_cur_price(_asset_id_pipeline)

        # ✅ תיקון: אם לא הצלחנו לשלוף מחיר נוכחי — חסום (לא להניח פרש 0%)
        if _cur_price_real is None:
            logger.info(
                f"Pipeline חסם — לא ניתן לשלוף מחיר נוכחי לבדיקת פרש: "
                f"{signal.get('expert_name','')} | asset_id={_asset_id_pipeline!r}"
            )
            return
        _current_price = _cur_price_real

        # ✅ תיקון: חסום עסקאות עם מחיר מתחת ל-MIN_TRADE_PRICE (סיכון גבוה מדי)
        try:
            from config import MIN_TRADE_PRICE as _MIN_PRICE
        except ImportError:
            _MIN_PRICE = 0.20  # ברירת מחדל: 20%
        if _expert_price < _MIN_PRICE:
            logger.info(
                f"Pipeline חסם — מחיר נמוך מדי ({_expert_price:.3f} < {_MIN_PRICE:.2f}): "
                f"{signal.get('expert_name','')} | {signal.get('market_question','')[:60]}"
            )
            return

        # ✅ תיקון: שלוף נפח אמיתי מה-API לבדיקת נזילות (במקום 0.0 קבוע)
        _market_volume = 0.0
        try:
            from polymarket_client import get_market_info as _get_mkt
            _cond_id = signal.get("condition_id", "")
            if _cond_id:
                _mkt_info = _get_mkt(_cond_id)
                _market_volume = float(_mkt_info.get("volume", _mkt_info.get("volumeNum", 0)) or 0)
        except Exception:
            pass

        _ts = TradeSignal(
            expert_name       = signal.get("expert_name", ""),
            wallet_address    = signal.get("wallet_address", ""),
            market_question   = signal.get("market_question", ""),
            market_slug       = signal.get("market_url", ""),
            direction         = signal.get("outcome", "YES"),
            expert_price      = _expert_price,
            current_price     = _current_price,   # ← מחיר נוכחי אמיתי
            expert_trade_usd  = float(signal.get("usd_value", 0)),
            market_volume_usd = _market_volume,   # ✅ נפח אמיתי
            end_date          = signal.get("end_date"),
            asset_id          = _asset_id_pipeline,
        )
        _result = run_pipeline(_ts, base_amount=_base, balance=_bal)
        if not _result.approved:
            # Pipeline rejected — silent drop, log only
            logger.info(f"Pipeline חסם (לא נשלח): {_result.rejection_reason} | {signal.get('expert_name','')}")
            return
        # Attach pipeline data to signal for use below
        signal["_pipeline"]         = _result
        signal["_pipeline_summary"] = format_pipeline_summary(_result)  # profile added below after load
        signal["_pipeline_result"]  = _result  # store for re-format after profile loaded
        signal["_trade_amount_pipeline"] = _result.final_trade_usd
        if _result.herd_warning:
            signal["_herd_warning"] = _result.herd_warning
    except Exception as _pipe_err:
        # ✅ תיקון באג 3: שגיאה ב-Pipeline = חסום, לא ממשיך
        logger.error(f"שגיאה קריטית ב-Pipeline — עסקה נחסמת: {_pipe_err}")
        return

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
    from expert_profiles import get_wallet_profile
    profile = get_wallet_profile(expert)
    expert_warning = get_expert_warning(expert, price)
    hot_header = get_hot_alert_header(expert)
    priority_rank = get_automation_priority_rank(expert)
    priority_line = f"\n🏆 עדיפות אוטומציה: *#{priority_rank}*" if priority_rank <= 8 else ""

    # Build risk profile line — always show, even for unknown experts
    if profile:
        dom_risk = profile.get("dominant_risk", "MEDIUM")
        risk_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(dom_risk, "⚪")
        risk_label = {"LOW": "סיכון נמוך", "MEDIUM": "סיכון בינוני", "HIGH": "סיכון גבוה"}.get(dom_risk, "לא ידוע")
        win_rate = profile.get("win_rate_pct")
        wr_str = f" | הצלחה {win_rate:.0f}%" if win_rate is not None else ""
        roi = profile.get("roi_pct")
        roi_str = f" | ROI {roi:+.0f}%" if roi is not None else ""
        size_tier = profile.get("size_tier", "")
        size_icon = "🐋" if size_tier == "WHALE" else "🐟" if size_tier == "LARGE" else "🐠"
        risk_profile_line = f"\n{risk_icon}{size_icon} *{risk_label}{wr_str}{roi_str}*"
    else:
        risk_profile_line = f"\n⚪ *מומחה חדש | בבדיקה*"

    warning_line = f"\n{expert_warning}" if expert_warning else ""

    # ✅ עדכון שורת ציון Pipeline עם פרופיל מומחה אמיתי
    if signal.get("_pipeline_result"):
        try:
            from trade_pipeline import format_pipeline_summary as _fmt_pipe
            _expert_profile_for_pipe = {
                "win_rate_pct": profile.get("win_rate_pct", 50) if profile else 50,
                "roi_pct":      profile.get("roi_pct", 0)       if profile else 0,
                "risk_level":   profile.get("dominant_risk", "MEDIUM").lower() if profile else "medium",
            }
            signal["_pipeline_summary"] = _fmt_pipe(signal["_pipeline_result"], _expert_profile_for_pipe)
        except Exception:
            pass  # fallback to existing summary

    # Investment recommendation based on expert profile (uses recommendation field)
    if profile:
        from expert_profiles import get_invest_recommendation
        invest_rec = f"\n{get_invest_recommendation(expert)}"
    else:
        invest_rec = "\n⚪ *המלצה: מומחה חדש — המתן לנתונים נוספים*"

    # Real-time price & gap analysis (for display only — blocking already done in Pipeline stage3)
    # ✅ תיקון: הסרנו את החסימה הכפולה ב-analyze_price_gap — Pipeline כבר בדק פרש בשלב 3
    current_price = get_current_market_price(asset_id)
    gap_info = analyze_price_gap(price, current_price, outcome)  # לתצוגה בלבד

    if current_price is not None:
        curr_pct = current_price * 100
        price_gap_line = (
            f"\n📊 מחיר נוכחי: *{current_price:.3f}* ({curr_pct:.1f}%)"
        )
        if gap_info["analysis"]:
            price_gap_line += f"\n{gap_info['analysis']}"
            # Add explicit gap-based recommendation
            if gap_info.get("favorable") is True:
                price_gap_line += "\n💡 *פער מחיר: כניסה טובה — מחיר נוח ביחס למומחה*"
            elif gap_info.get("favorable") is False:
                price_gap_line += "\n⚠️ *פער מחיר: כניסה יקרה — שקול להמתין*"
    else:
        price_gap_line = "\n📊 מחיר נוכחי: *לא זמין*"

    # Dynamic sizing label
    dynamic_line = f"\n🧠 סכום דינמי: *${trade_amount:.2f}* ({dynamic_label})" if dynamic_label else ""

    # שיפור 5: קונברגנציה — הגדלת פוזיציה כש-3+ לווייתנים מסכימים
    convergence_line = ""
    try:
        from convergence_detector import record_whale_entry, get_convergence_info
        from config import CONVERGENCE_MULTIPLIER
        record_whale_entry(signal)
        conv_info = get_convergence_info(signal)
        if conv_info:
            trade_amount = round(trade_amount * CONVERGENCE_MULTIPLIER, 2)
            convergence_line = (
                f"\n🌊🌊🌊 *קונברגנציה! {conv_info['whale_count']} לווייתנים מסכימים!*"
                f"\n👥 {', '.join(conv_info['whale_names'])}"
                f"\n📈 פוזיציה הוגדלה ×{CONVERGENCE_MULTIPLIER} → ${trade_amount:.0f}"
            )
    except Exception as _conv_err:
        logger.warning(f"שגיאה בקונברגנציה: {_conv_err}")

    # Pipeline summary lines
    pipeline_summary_line = ""
    herd_line             = ""
    if signal.get("_pipeline_summary"):
        pipeline_summary_line = f"\n{signal['_pipeline_summary']}"
    if signal.get("_herd_warning"):
        herd_line = f"\n{signal['_herd_warning']}"
    # Use pipeline trade amount if available
    if signal.get("_trade_amount_pipeline"):
        trade_amount = signal["_trade_amount_pipeline"]

    # ניתוח תחום מומחיות
    domain_line = ""
    try:
        _pipeline_obj = signal.get('_pipeline_result') or signal.get('_pipeline')
        if _pipeline_obj:
            domain_line = getattr(_pipeline_obj, '_domain_line', '') or ""
    except Exception:
        domain_line = ""

    # Value Zone Analysis (שכבה 1 + שכבה 2)
    value_zone_line = ""
    try:
        _pipeline_obj = signal.get('_pipeline_result') or signal.get('_pipeline')
        if _pipeline_obj:
            value_zone_line = getattr(_pipeline_obj, '_value_zone_line', '') or ""
    except Exception:
        value_zone_line = ""

    # חישוב רווח פוטנציאלי ויחס סיכון/תגמול
    profit_loss_line = ""
    try:
        entry_price = float(current_price) if current_price else float(price)
        if entry_price > 0:
            potential_profit = trade_amount * (1 - entry_price) / entry_price
            risk_reward_ratio = (1 - entry_price) / entry_price
            # צבע לפי איכות העסקא
            if risk_reward_ratio >= 1.0:        # רווח > סיכון — מצוין
                rr_emoji = "🟢"
            elif risk_reward_ratio >= 0.5:      # רווח = 50-100% מהסיכון — בינוני
                rr_emoji = "🟡"
            else:                               # רווח < 50% מהסיכון — גרוע
                rr_emoji = "🔴"
            profit_loss_line = (
                f"\n{rr_emoji} רווח פוטנציאלי: *+${potential_profit:.2f}* אם ניצחת"
                f" | סיכון: *-${trade_amount:.2f}* אם הפסדת"
                f"\n⚖️ יחס סיכון/תגמול: *1:{risk_reward_ratio:.2f}*"
            )
    except Exception as _pl_err:
        logger.debug(f"שגיאה בחישוב רווח/סיכון: {_pl_err}")

    text = (
        f"{hot_header}{alert_header}\n\n"
        f"👤 {trader_label}: *{expert}*\n"
        f"📊 שוק: {market[:80]}\n"
        f"🎯 כיוון: *{outcome}*\n"
        f"💵 מחיר מומחה: *{price:.3f}* ({price_pct:.1f}%) — {price_emoji}"
        f"{risk_profile_line}{warning_line}"
        f"{invest_rec}"
        f"{price_gap_line}"
        f"{profit_loss_line}"
        f"{domain_line}"
        f"{value_zone_line}\n"
        f"💰 סכום {trader_label}: ${usd_val:.0f}"
        f"{convergence_line}"
        f"{herd_line}"
        f"{pipeline_summary_line}"
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
        # 💾 שמירת message_id למחיקה עתידית אם פרש עלה מעל הסף
        _PENDING_TRADES[short_key]["_msg_id"] = msg.message_id
        _PENDING_TRADES[short_key]["_asset_id"] = asset_id
        _PENDING_TRADES[short_key]["_expert_price"] = price
        _PENDING_TRADES[short_key]["_outcome"] = outcome
        _save_pending_trades()

        # 🚨 Urgent alert — fires BEFORE AI analysis so user gets it immediately
        try:
            from urgent_alert import maybe_send_urgent_alerts
            await maybe_send_urgent_alerts(_ptb_app.bot, signal)
        except Exception as ue:
            logger.warning(f"שגיאה בהתראה דחופה: {ue}")

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
                trade_id, _ = record_trade(signal, trade_amount)
                # הוסף פוזיציה ל-Exit Manager
                try:
                    _em = ExitManager()
                    _em.add_position(
                        signal,
                        entry_price=signal.get("price", 0.5),
                        amount_usd=trade_amount,
                        trade_id=f"dry_{trade_id}"
                    )
                except Exception as _em_err:
                    logger.warning(f"שגיאה ב-ExitManager.add_position: {_em_err}")
                await query.edit_message_text(
                    f"✅ *DRY RUN — נרשם ביומן*\n\n"
                    f"מומחה: {expert}\n"
                    f"שוק: {market}\n"
                    f"כיוון: {outcome}\n"
                    f"סכום: ${trade_amount:.2f}{balance_line}\n\n"
                    f"📋 מספר עסקה: #{trade_id}\n"
                    f"🎯 TP: +20% | SL: -12% | זמן: 48h\n"
                    f"הקלד /p\_dryrun לסיכום",
                    parse_mode="Markdown"
                )
            else:
                # הוסף פוזיציה ל-Exit Manager גם ב-LIVE
                try:
                    _em = ExitManager()
                    _em.add_position(
                        signal,
                        entry_price=signal.get("price", 0.5),
                        amount_usd=trade_amount,
                        trade_id=f"live_{int(time.time())}"
                    )
                except Exception as _em_err:
                    logger.warning(f"שגיאה ב-ExitManager.add_position (LIVE): {_em_err}")
                await query.edit_message_text(
                    f"✅ *פקודת קנייה נשלחה*\n\n"
                    f"מומחה: {expert}\n"
                    f"שוק: {market}\n"
                    f"כיוון: {outcome}\n"
                    f"סכום: ${trade_amount:.2f}\n"
                    f"🎯 TP: +20% | SL: -12% | זמן: 48h",
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
    _ptb_app.add_handler(CommandHandler("p_audit", cmd_audit))
    _ptb_app.add_handler(CommandHandler("p_resume_trading", cmd_resume_trading))
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

                # סריקת ארנקים משודרגת באמצעות wallet_scanner
                from wallet_scanner import run_wallet_scan, format_scan_telegram
                scan_results = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: run_wallet_scan(top_n=50, min_pnl=10000)
                )

                if not scan_results:
                    await _ptb_app.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text="🔍 *סריקת ארנקים* — לא נמצאו תוצאות החודש.",
                        parse_mode="Markdown"
                    )
                    continue

                scan_msg = format_scan_telegram(scan_results)
                await _ptb_app.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=scan_msg,
                    parse_mode="Markdown"
                )
                logger.info(f"סריקת ארנקים נשלחה — {scan_results.get('total_scanned', 0)} נסרקו, {scan_results.get('new_discoveries', 0)} גילויים חדשים")
            except Exception as e:
                logger.warning(f"\u05e9\u05d2\u05d9\u05d0\u05d4 \u05d1\u05d2\u05d9\u05dc\u05d5\u05d9 \u05de\u05d5\u05de\u05d7\u05d9\u05dd: {e}")
                await asyncio.sleep(3600)

    asyncio.ensure_future(_monthly_discovery_loop())

    # ─── Circular Audit Loop (DAILY at 08:00 Israel time) ──────────────────
    async def _circular_audit_loop():
        """מנגנון בקרה מעגלי — בודק שכל תכונה שסוכמה מיושמת. כל יום 08:00."""
        await asyncio.sleep(120)  # First check after 2 minutes (startup)
        _last_failed_count = -1  # Track changes between runs
        first_run = True
        while True:
            try:
                now = datetime.datetime.now(ISRAEL_TZ)
                if not first_run:
                    # Calculate seconds until NEXT DAY at 08:00
                    next_run = now.replace(hour=8, minute=0, second=0, microsecond=0)
                    if now.hour >= 8:
                        next_run += datetime.timedelta(days=1)
                    wait_secs = (next_run - now).total_seconds()
                    logger.info(f"בקרה מעגלית: בדיקה הבאה ב-{next_run.strftime('%d/%m %H:%M')} ({wait_secs/3600:.1f} שעות)")
                    await asyncio.sleep(wait_secs)

                first_run = False
                now = datetime.datetime.now(ISRAEL_TZ)
                now_str = now.strftime("%d/%m/%Y %H:%M")
                day_name = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"][now.weekday()]

                # Run audit_bot.py as subprocess and capture output
                import subprocess as _sp, os as _os
                _bot_dir = _os.path.dirname(_os.path.abspath(__file__))
                result = _sp.run(
                    ["python3.11", "audit_bot.py", "--silent"],
                    capture_output=True, text=True, timeout=60,
                    cwd=_bot_dir
                )
                output = result.stdout

                # Parse results
                passed = output.count("[PASS]")
                failed_count = output.count("[FAIL]")
                warn_count = output.count("[WARN]")
                total = passed + failed_count + warn_count
                status_emoji = "✅" if failed_count == 0 else "❌"

                # Detect changes from last run
                status_changed = (_last_failed_count != -1 and failed_count != _last_failed_count)
                change_note = ""
                if status_changed:
                    if failed_count < _last_failed_count:
                        change_note = f"\n📈 *שיפור!* כשלים קטנו מ-{_last_failed_count} ל-{failed_count}"
                    else:
                        change_note = f"\n📉 *הידרדות!* כשלים עלו מ-{_last_failed_count} ל-{failed_count}"
                _last_failed_count = failed_count

                lines = [
                    f"{status_emoji} *בקרה מעגלית יומית — {day_name} {now_str}*\n",
                    f"📊 עברו: *{passed}/{total}* | ❌ כשלים: *{failed_count}* | ⚠️ אזהרות: *{warn_count}*",
                ]

                if change_note:
                    lines.append(change_note)

                if failed_count > 0:
                    fail_lines = [l for l in output.split("\n") if "[FAIL]" in l]
                    lines.append("\n*🚨 כשלים שדורשים תיקון:*")
                    for fl in fail_lines:
                        lines.append(f"  {fl.strip()}")
                    lines.append("\n⚠️ שלח /p\\_audit לפרטים ותיקון")
                elif warn_count > 0:
                    warn_lines = [l for l in output.split("\n") if "[WARN]" in l]
                    lines.append("\n*⚠️ אזהרות:*")
                    for wl in warn_lines:
                        lines.append(f"  {wl.strip()}")
                else:
                    lines.append("🎉 כל התכונות פועלות כמצופה — המערכת תקינה!")

                lines.append("\n_/p\\_audit לבדיקה ידנית_")

                await _ptb_app.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text="\n".join(lines),
                    parse_mode="Markdown"
                )
                logger.info(f"בקרה יומית נשלחה: {passed}/{total} עברו, {failed_count} כשלים")
            except Exception as e:
                logger.warning(f"שגיאה בבקרה מעגלית: {e}")
                await asyncio.sleep(3600)

    asyncio.ensure_future(_circular_audit_loop())

    # ─── Exit Manager Loop (every 15 minutes) ──────────────────────────────
    async def _exit_manager_loop():
        """בודק פוזיציות פתוחות ומבצע Take Profit / Stop Loss / Time Exit."""
        await asyncio.sleep(180)  # First check after 3 minutes
        _exit_mgr = ExitManager(
            telegram_callback=lambda msg: asyncio.ensure_future(
                _ptb_app.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=msg,
                    parse_mode="Markdown"
                )
            )
        )
        while True:
            try:
                closed = await asyncio.get_event_loop().run_in_executor(
                    None, _exit_mgr.check_exits
                )
                if closed:
                    logger.info(f"Exit Manager: {len(closed)} פוזיציות נסגרו")
            except Exception as e:
                logger.warning(f"שגיאה ב-Exit Manager: {e}")
            await asyncio.sleep(900)  # Check every 15 minutes

    asyncio.ensure_future(_exit_manager_loop())

    # ─── Spread Monitor Loop (every 5 minutes) ──────────────────────────────
    async def _spread_monitor_loop():
        """בודק כל 5 דקות את כל ההתראות הפתוחות — אם פרש עלה מעל הסף — מוחק את ההתראה מטלגרם."""
        from market_analysis import get_current_market_price, analyze_price_gap
        await asyncio.sleep(120)  # First check after 2 minutes
        while True:
            try:
                keys_to_delete = []
                for key, sig in list(_PENDING_TRADES.items()):
                    msg_id     = sig.get("_msg_id")
                    asset_id_s = sig.get("_asset_id")
                    exp_price  = sig.get("_expert_price")
                    outcome_s  = sig.get("_outcome", "YES")
                    if not msg_id or not asset_id_s or exp_price is None:
                        continue
                    cur_price = get_current_market_price(asset_id_s)
                    if cur_price is None:
                        continue
                    gap_info = analyze_price_gap(exp_price, cur_price, outcome_s)
                    if gap_info.get("blocked"):
                        try:
                            await _ptb_app.bot.delete_message(
                                chat_id=TELEGRAM_CHAT_ID,
                                message_id=msg_id
                            )
                            keys_to_delete.append(key)
                            logger.info(
                                f"🗑️ Spread Monitor מחק התראה: key={key} | "
                                f"{sig.get('expert_name','')} | {gap_info.get('block_reason','')}"
                            )
                        except Exception as _del_err:
                            logger.warning(f"לא ניתן למחוק התראה key={key}: {_del_err}")
                for k in keys_to_delete:
                    _PENDING_TRADES.pop(k, None)
                if keys_to_delete:
                    _save_pending_trades()
            except Exception as _sm_err:
                logger.warning(f"שגיאה ב-Spread Monitor: {_sm_err}")
            await asyncio.sleep(300)  # Check every 5 minutes

    asyncio.ensure_future(_spread_monitor_loop())

    # Keep running forever
    try:
        await asyncio.Event().wait()
    finally:
        await _ptb_app.updater.stop()
        await _ptb_app.stop()
        await _ptb_app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
