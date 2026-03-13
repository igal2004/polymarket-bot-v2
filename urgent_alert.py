"""
urgent_alert.py — התראות דחופות לעסקאות עם פוטנציאל הצלחה גבוה מאוד (מעל 85%)

מנגנונים:
1. הודעת טלגרם נפרדת עם צליל + סימון "🚨🚨🚨 דחוף"
2. אימייל דחוף ל-igal2004@gmail.com

הפעלה: send_urgent_alert(signal, win_rate, roi, confidence_score)
"""

import os
import smtplib
import logging
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── הגדרות ───────────────────────────────────────────────────────────────────
URGENT_THRESHOLD_WIN_RATE = 85.0   # % הצלחה מינימלי להתראה דחופה
URGENT_THRESHOLD_PRICE    = 0.70   # מחיר מינימלי (70% סבירות)

# Gmail SMTP — משתמש ב-App Password (לא סיסמה רגילה)
GMAIL_SENDER   = os.getenv("GMAIL_SENDER",   "")   # כתובת Gmail של השולח
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")   # App Password של Gmail
ALERT_EMAIL    = "igal2004@gmail.com"

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "")


def should_send_urgent(signal: dict, win_rate: float, price: float) -> tuple[bool, str]:
    """
    בודק האם עסקה עומדת בסף להתראה דחופה.
    מחזיר (True/False, סיבה).
    """
    reasons = []

    # קריטריון 1: אחוז הצלחה מעל 85%
    if win_rate >= URGENT_THRESHOLD_WIN_RATE:
        reasons.append(f"הצלחה {win_rate:.0f}% ≥ {URGENT_THRESHOLD_WIN_RATE:.0f}%")

    # קריטריון 2: מחיר גבוה (סבירות גבוהה)
    if price >= URGENT_THRESHOLD_PRICE:
        reasons.append(f"מחיר {price*100:.0f}% ≥ {URGENT_THRESHOLD_PRICE*100:.0f}%")

    # שני הקריטריונים חייבים להתקיים
    if len(reasons) == 2:
        return True, " | ".join(reasons)

    # חריג: לווייתן עם hot_signal — תמיד דחוף
    from expert_profiles import get_wallet_profile
    profile = get_wallet_profile(signal.get("expert_name", ""))
    if profile and profile.get("hot_signal"):
        return True, "🔥 לווייתן 100% הצלחה"

    return False, ""


async def send_urgent_telegram(bot, signal: dict, win_rate: float, reason: str):
    """שולח הודעת טלגרם דחופה נפרדת עם צליל (disable_notification=False)."""
    expert    = signal.get("expert_name", "")
    market    = signal.get("market_question", "")
    outcome   = signal.get("outcome", "")
    price     = signal.get("price", 0)
    usd_val   = signal.get("usd_value", 0)
    url       = signal.get("market_url", "")
    end_date  = signal.get("end_date", "")
    trade_amt = signal.get("_trade_amount", 32)
    now_str   = datetime.now().strftime("%H:%M")

    end_line = f"\n📅 פקיעת שוק: *{end_date}*" if end_date else ""

    text = (
        f"🚨🚨🚨 *התראה דחופה — הזדמנות מעולה!* 🚨🚨🚨\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ *{reason}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 מומחה/לווייתן: *{expert}*\n"
        f"📊 שוק: {market[:100]}\n"
        f"🎯 כיוון: *{outcome}*\n"
        f"💵 מחיר: *{price:.3f}* ({price*100:.1f}%) — סבירות גבוהה מאוד\n"
        f"🏆 אחוז הצלחה היסטורי: *{win_rate:.0f}%*\n"
        f"💰 סכום מומלץ: *${trade_amt:.0f}*\n"
        f"💼 סכום המומחה: ${usd_val:.0f}"
        f"{end_line}\n\n"
        f"⏰ זמן: {now_str}\n"
        f"🔗 [לחץ כאן לפתיחת השוק ומסחר]({url})\n\n"
        f"_⚠️ פעל מהר — הזדמנויות כאלה נסגרות מהר!_"
    )

    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="Markdown",
            disable_web_page_preview=True,
            disable_notification=False  # ← צליל תמיד, גם כשהנייד על שקט
        )
        logger.info(f"התראה דחופה נשלחה לטלגרם: {expert} | {reason}")
    except Exception as e:
        logger.error(f"שגיאה בשליחת התראה דחופה לטלגרם: {e}")


def send_urgent_email(signal: dict, win_rate: float, reason: str):
    """שולח אימייל דחוף ל-igal2004@gmail.com."""
    if not GMAIL_SENDER or not GMAIL_APP_PASS:
        logger.warning("GMAIL_SENDER או GMAIL_APP_PASS לא מוגדרים — אימייל לא נשלח")
        return

    expert    = signal.get("expert_name", "")
    market    = signal.get("market_question", "")
    outcome   = signal.get("outcome", "")
    price     = signal.get("price", 0)
    usd_val   = signal.get("usd_value", 0)
    url       = signal.get("market_url", "")
    end_date  = signal.get("end_date", "")
    trade_amt = signal.get("_trade_amount", 32)
    now_str   = datetime.now().strftime("%d/%m/%Y %H:%M")

    subject = f"🚨 הזדמנות דחופה! {expert} — {win_rate:.0f}% הצלחה — {now_str}"

    html_body = f"""
    <html><body style="font-family: Arial, sans-serif; direction: rtl; text-align: right;">
    <div style="background:#ff4444; color:white; padding:15px; border-radius:8px; text-align:center;">
        <h1>🚨 התראה דחופה — הזדמנות מעולה!</h1>
        <h2>{reason}</h2>
    </div>
    <div style="padding:20px; background:#f9f9f9; border-radius:8px; margin-top:10px;">
        <table style="width:100%; border-collapse:collapse;">
            <tr><td style="padding:8px; font-weight:bold;">👤 מומחה/לווייתן:</td><td style="padding:8px;">{expert}</td></tr>
            <tr style="background:#fff;"><td style="padding:8px; font-weight:bold;">📊 שוק:</td><td style="padding:8px;">{market}</td></tr>
            <tr><td style="padding:8px; font-weight:bold;">🎯 כיוון:</td><td style="padding:8px; color:#007700; font-size:18px;"><b>{outcome}</b></td></tr>
            <tr style="background:#fff;"><td style="padding:8px; font-weight:bold;">💵 מחיר:</td><td style="padding:8px;">{price:.3f} ({price*100:.1f}%)</td></tr>
            <tr><td style="padding:8px; font-weight:bold;">🏆 אחוז הצלחה:</td><td style="padding:8px; color:#cc0000; font-size:18px;"><b>{win_rate:.0f}%</b></td></tr>
            <tr style="background:#fff;"><td style="padding:8px; font-weight:bold;">💰 סכום מומלץ:</td><td style="padding:8px; font-size:18px;"><b>${trade_amt:.0f}</b></td></tr>
            <tr><td style="padding:8px; font-weight:bold;">💼 סכום המומחה:</td><td style="padding:8px;">${usd_val:.0f}</td></tr>
            {"<tr style='background:#fff;'><td style='padding:8px; font-weight:bold;'>📅 פקיעת שוק:</td><td style='padding:8px;'>" + end_date + "</td></tr>" if end_date else ""}
            <tr><td style="padding:8px; font-weight:bold;">⏰ זמן:</td><td style="padding:8px;">{now_str}</td></tr>
        </table>
    </div>
    <div style="text-align:center; margin-top:15px;">
        <a href="{url}" style="background:#007bff; color:white; padding:15px 30px; border-radius:8px; text-decoration:none; font-size:18px; font-weight:bold;">
            🔗 פתח שוק ובצע עסקה עכשיו
        </a>
    </div>
    <p style="color:#888; font-size:12px; margin-top:20px; text-align:center;">
        ⚠️ פעל מהר — הזדמנויות כאלה נסגרות מהר! | Polymarket Expert Bot
    </p>
    </body></html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_SENDER
        msg["To"]      = ALERT_EMAIL
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER, GMAIL_APP_PASS)
            server.sendmail(GMAIL_SENDER, ALERT_EMAIL, msg.as_string())

        logger.info(f"אימייל דחוף נשלח ל-{ALERT_EMAIL}: {expert} | {reason}")
    except Exception as e:
        logger.error(f"שגיאה בשליחת אימייל דחוף: {e}")


async def maybe_send_urgent_alerts(bot, signal: dict):
    """
    הפונקציה הראשית — נקראת מ-send_trade_alert.
    בודקת האם העסקה עומדת בסף ושולחת התראות דחופות אם כן.
    """
    from expert_profiles import get_wallet_profile

    expert  = signal.get("expert_name", "")
    price   = signal.get("price", 0)
    profile = get_wallet_profile(expert)

    win_rate = 0.0
    if profile:
        win_rate = profile.get("win_rate_pct") or 0.0

    is_urgent, reason = should_send_urgent(signal, win_rate, price)

    if not is_urgent:
        return  # לא עומד בסף — לא שולחים

    logger.info(f"🚨 עסקה דחופה זוהתה: {expert} | {reason}")

    # 1. טלגרם דחוף (עם צליל)
    await send_urgent_telegram(bot, signal, win_rate, reason)

    # 2. אימייל דחוף (non-blocking)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, send_urgent_email, signal, win_rate, reason)
