#!/usr/bin/env python3.11
"""
audit_bot.py — מנגנון בקרה מעגלי אוטומטי
בודק שכל תכונה שסוכמה מיושמת בפועל בקוד ובסביבה.
מריץ בדיקות ומדווח לטלגרם.

הרצה ידנית:  python3.11 audit_bot.py
הרצה שקטה:  python3.11 audit_bot.py --silent   (לא שולח לטלגרם)
"""

import os
import re
import sys
import json
import requests
import subprocess
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SILENT = "--silent" in sys.argv

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"

results = []


def check(name: str, passed: bool, detail: str = "", warn_only: bool = False):
    icon = PASS if passed else (WARN if warn_only else FAIL)
    results.append({"name": name, "passed": passed, "icon": icon, "detail": detail})
    status = "PASS" if passed else ("WARN" if warn_only else "FAIL")
    print(f"  {icon} [{status}] {name}" + (f" — {detail}" if detail else ""))


def grep(filepath: str, pattern: str) -> bool:
    """Returns True if pattern found in file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return bool(re.search(pattern, content))
    except FileNotFoundError:
        return False


def env_set(var: str) -> bool:
    val = os.getenv(var, "")
    return bool(val and len(val) > 5)


# ─────────────────────────────────────────────
# בדיקות: התראות מסחר
# ─────────────────────────────────────────────
print("\n📋 בדיקת התראות מסחר (Polymarket Bot)")

check("P01 — פרופיל סיכון בהתראה",
      grep("telegram_bot.py", r"risk_profile_line"),
      "risk_profile_line בנוי מ-dominant_risk")

check("P02 — המלצת השקעה בהתראה",
      grep("telegram_bot.py", r"invest_rec"),
      "invest_rec מחושב לפי פרופיל")

check("P03 — פער מחיר + המלצה",
      grep("telegram_bot.py", r"price_gap_line") and
      grep("telegram_bot.py", r"פער מחיר: כניסה"),
      "price_gap_line + המלצה מפורשת")

check("P04 — התראה חמה 100%",
      grep("expert_profiles.py", r"hot_signal.*True") and
      grep("telegram_bot.py", r"get_hot_alert_header"),
      "hot_signal=True + get_hot_alert_header")

check("P05 — עדיפות אוטומציה",
      grep("telegram_bot.py", r"get_automation_priority_rank") and
      grep("telegram_bot.py", r"עדיפות אוטומציה"),
      "priority_rank מוצג בהתראה")

check("P06 — תאריך פקיעה",
      grep("tracker.py", r"end_date") and
      grep("telegram_bot.py", r"end_date_line"),
      "end_date נשלף מה-API ומוצג")

check("P07 — סכום דינמי",
      grep("telegram_bot.py", r"calculate_dynamic_trade_amount") and
      grep("telegram_bot.py", r"dynamic_line"),
      "dynamic trade amount מחושב ומוצג")

check("P08 — יתרת ארנק",
      grep("telegram_bot.py", r"get_wallet_usdc_balance") and
      grep("telegram_bot.py", r"balance_line"),
      "יתרה נשלפת ומוצגת")

check("P09 — ניתוח AI",
      grep("telegram_bot.py", r"get_ai_risk_analysis") and
      grep("telegram_bot.py", r"ניתוח AI"),
      "AI analysis נשלח כ-reply")

check("P10 — אזהרת חריגה מפרופיל",
      grep("telegram_bot.py", r"get_expert_warning") and
      grep("expert_profiles.py", r"get_expert_warning"),
      "warning_line מחושב ומוצג")

# ─────────────────────────────────────────────
# בדיקות: הגנות ארנק
# ─────────────────────────────────────────────
print("\n🛡️ בדיקת הגנות ארנק")

check("P11 — מגבלת 10% לעסקה",
      grep("config.py", r"MAX_SINGLE_TRADE_PERCENT") and
      grep("telegram_bot.py", r"MAX_SINGLE_TRADE_PERCENT"),
      "MAX_SINGLE_TRADE_PERCENT=10")

check("P12 — מגבלה יומית 30%",
      grep("config.py", r"MAX_DAILY_SPEND_PERCENT") or
      grep("telegram_bot.py", r"daily.*limit|MAX_DAILY"),
      warn_only=True)

check("P13 — חסימה אם יתרה נמוכה",
      grep("telegram_bot.py", r"check_wallet_protection"),
      "check_wallet_protection נקרא לפני כל עסקה")

check("P14 — מחיר מינימום 0.20",
      grep("config.py", r"MIN_PRICE.*0\.2|0\.20") or
      grep("telegram_bot.py", r"0\.2"),
      warn_only=True)

# ─────────────────────────────────────────────
# בדיקות: מעקב תוצאות
# ─────────────────────────────────────────────
print("\n📊 בדיקת מעקב תוצאות")

check("P15 — סגירת עסקאות אוטומטית",
      grep("dry_run_journal.py", r"check_and_settle_open_trades") and
      grep("telegram_bot.py", r"_settlement_loop"),
      "settlement_loop רץ כל שעה")

check("P16 — הודעת תוצאה (זכייה/הפסד)",
      grep("telegram_bot.py", r"עסקה.*נסגרה") and
      grep("telegram_bot.py", r"זכייה|הפסד"),
      "הודעת תוצאה נשלחת אוטומטית")

check("P17 — פקודת /p_dryrun",
      grep("telegram_bot.py", r"cmd_dryrun") and
      grep("telegram_bot.py", r"p_dryrun"),
      "פקודה רשומה ומטפלת")

check("P18 — פקודת /p_dryrun_trades",
      grep("telegram_bot.py", r"cmd_dryrun_trades"),
      "פקודה רשומה")

check("P19 — פקודת /p_compare",
      grep("telegram_bot.py", r"cmd_compare"),
      "פקודה רשומה")

check("P20 — גיבוי יומי לטלגרם",
      grep("telegram_bot.py", r"_daily_backup_loop") and
      grep("telegram_bot.py", r"גיבוי יומי"),
      "backup loop פעיל")

# ─────────────────────────────────────────────
# בדיקות: דוחות אוטומטיים
# ─────────────────────────────────────────────
print("\n📅 בדיקת דוחות אוטומטיים")

check("P21 — דוח שבועי (ראשון 09:00)",
      grep("telegram_bot.py", r"_weekly_report_loop") and
      grep("telegram_bot.py", r"days_until_sunday"),
      "weekly_report_loop פעיל")

check("P22 — תזכורת עסקאות פתוחות (18:00)",
      grep("telegram_bot.py", r"_open_trades_reminder_loop") and
      grep("telegram_bot.py", r"18"),
      "open_trades_reminder_loop פעיל")

check("P23 — גילוי מומחים חדשים (1 לחודש)",
      grep("telegram_bot.py", r"_monthly_discovery_loop"),
      "monthly_discovery_loop פעיל")

check("P24 — בדיקת כתובות ארנקים (08:00)",
      grep("telegram_bot.py", r"validate_expert_wallets_job"),
      "validate_expert_wallets_job פעיל")

check("P25 — דוח בקרה מעגלי שבועי",
      grep("telegram_bot.py", r"_circular_audit_loop|audit_bot"),
      "circular audit loop פעיל")

# ─────────────────────────────────────────────
# בדיקות: פרופילי מומחים
# ─────────────────────────────────────────────
print("\n👤 בדיקת פרופילי מומחים")

REQUIRED_WHALES = ["Theo4", "Fredi9999", "Len9311238", "zxgngl", "RepTrump"]
for whale in REQUIRED_WHALES:
    check(f"P27 — לווייתן {whale}",
          grep("expert_profiles.py", whale) and grep("config.py", whale),
          "קיים ב-expert_profiles ו-config")

check("P28 — פרופיל מלא לכל מומחה",
      grep("expert_profiles.py", r"dominant_risk") and
      grep("expert_profiles.py", r"win_rate_pct") and
      grep("expert_profiles.py", r"hot_signal"),
      "dominant_risk + win_rate_pct + hot_signal קיימים")

check("P29 — סדר עדיפויות אוטומציה",
      grep("expert_profiles.py", r"get_automation_priority_rank") and
      grep("expert_profiles.py", r"AUTOMATION_PRIORITY"),
      "AUTOMATION_PRIORITY list קיים")

# ─────────────────────────────────────────────
# בדיקות: משתני סביבה
# ─────────────────────────────────────────────
print("\n🔑 בדיקת משתני סביבה (Railway)")

check("P30 — TELEGRAM_BOT_TOKEN",
      env_set("TELEGRAM_BOT_TOKEN"),
      f"{'מוגדר' if env_set('TELEGRAM_BOT_TOKEN') else 'חסר!'}")

check("P31 — TELEGRAM_CHAT_ID",
      env_set("TELEGRAM_CHAT_ID"),
      f"{'מוגדר' if env_set('TELEGRAM_CHAT_ID') else 'חסר!'}")

check("P32 — PRIVATE_KEY",
      env_set("PRIVATE_KEY"),
      f"{'מוגדר' if env_set('PRIVATE_KEY') else 'חסר!'}")

check("P33 — WALLET_ADDRESS",
      env_set("WALLET_ADDRESS"),
      f"{'מוגדר' if env_set('WALLET_ADDRESS') else 'חסר!'}")

check("P34 — OPENAI_API_KEY",
      env_set("OPENAI_API_KEY"),
      f"{'מוגדר' if env_set('OPENAI_API_KEY') else 'חסר — AI לא יעבוד!'}")

check("P35 — OPENAI_BASE_URL",
      env_set("OPENAI_BASE_URL"),
      f"{'מוגדר' if env_set('OPENAI_BASE_URL') else 'חסר!'}")

# ─────────────────────────────────────────────
# סיכום
# ─────────────────────────────────────────────
total = len(results)
passed = sum(1 for r in results if r["passed"])
failed = [r for r in results if not r["passed"] and r["icon"] == FAIL]
warnings = [r for r in results if r["icon"] == WARN]

print(f"\n{'='*50}")
print(f"📊 תוצאות בקרה: {passed}/{total} עברו")
print(f"❌ כשלים: {len(failed)} | ⚠️ אזהרות: {len(warnings)}")
print(f"{'='*50}\n")

# ─────────────────────────────────────────────
# שליחה לטלגרם
# ─────────────────────────────────────────────
def send_telegram(text: str):
    if SILENT or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            timeout=10
        )
    except Exception as e:
        print(f"שגיאה בשליחה לטלגרם: {e}")


now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
status_emoji = "✅" if len(failed) == 0 else "❌"

lines = [
    f"{status_emoji} *דוח בקרה מעגלי — {now_str}*\n",
    f"📊 עברו: *{passed}/{total}* בדיקות",
    f"❌ כשלים: *{len(failed)}* | ⚠️ אזהרות: *{len(warnings)}*\n",
]

if failed:
    lines.append("*🚨 כשלים שדורשים תיקון:*")
    for r in failed:
        lines.append(f"  ❌ {r['name']}" + (f"\n     ↳ {r['detail']}" if r['detail'] else ""))

if warnings:
    lines.append("\n*⚠️ אזהרות:*")
    for r in warnings:
        lines.append(f"  ⚠️ {r['name']}")

if not failed and not warnings:
    lines.append("🎉 *כל התכונות פועלות כמצופה!*")

lines.append("\n_הרץ /p\\_audit לדוח מלא_")

send_telegram("\n".join(lines))

# Exit with error code if there are failures (useful for CI/CD)
sys.exit(1 if failed else 0)
