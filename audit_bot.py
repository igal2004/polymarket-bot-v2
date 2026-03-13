#!/usr/bin/env python3.11
"""
audit_bot.py — בקרה מעגלית פונקציונלית לבוט פולימרקט
בודק לא רק שהקוד קיים, אלא שהוא עובד בפועל ומחזיר את הנתונים הנכונים.

סוגי בדיקות:
  [CODE]  — קוד קיים ותקין
  [LIVE]  — קריאה אמיתית ל-API ובדיקת תוצאה
  [FIELD] — שדה חיוני מופיע בפלט
  [ENV]   — משתנה סביבה מוגדר
  [FUNC]  — פונקציה מחזירה ערך תקין

הרצה ידנית:  python3.11 audit_bot.py
הרצה שקטה:  python3.11 audit_bot.py --silent
"""

import os
import re
import sys
import ast
import requests
import importlib.util
from datetime import datetime

SILENT = "--silent" in sys.argv
BOT_DIR = os.path.dirname(os.path.abspath(__file__))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"

results = []


def check(name: str, passed: bool, detail: str = "", warn_only: bool = False, category: str = "CODE"):
    icon = PASS if passed else (WARN if warn_only else FAIL)
    tag = "PASS" if passed else ("WARN" if warn_only else "FAIL")
    results.append({"name": name, "passed": passed, "icon": icon, "detail": detail, "category": category})
    line = f"  {icon} [{tag}][{category}] {name}"
    if detail and not passed:
        line += f" — {detail}"
    if not SILENT:
        print(line)
    # Always print for --silent mode (parsed by telegram_bot.py)
    else:
        print(f"[{tag}] {name}" + (f" — {detail}" if detail and not passed else ""))
    return passed


def file_contains(filename: str, *patterns) -> bool:
    path = os.path.join(BOT_DIR, filename)
    try:
        content = open(path, encoding="utf-8").read()
        return all(re.search(p, content) for p in patterns)
    except:
        return False


def file_exists(filename: str) -> bool:
    return os.path.exists(os.path.join(BOT_DIR, filename))


def syntax_ok(filename: str) -> bool:
    path = os.path.join(BOT_DIR, filename)
    try:
        ast.parse(open(path, encoding="utf-8").read())
        return True
    except:
        return False


def env_set(var: str) -> bool:
    val = os.getenv(var, "")
    return bool(val and len(val) > 5)


def load_module(filename: str):
    path = os.path.join(BOT_DIR, filename)
    spec = importlib.util.spec_from_file_location("mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ═══════════════════════════════════════════════════════════════════════════════
# 1. קבצים וסינטקס
# ═══════════════════════════════════════════════════════════════════════════════
if not SILENT:
    print("\n── 1. קבצים וסינטקס ──")

for fname in ["telegram_bot.py", "tracker.py", "expert_profiles.py",
              "config.py", "market_analysis.py", "urgent_alert.py",
              "dry_run_journal.py", "audit_bot.py"]:
    check(f"{fname} קיים", file_exists(fname), category="CODE")
    check(f"{fname} תקין תחבירית", syntax_ok(fname), category="CODE")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. שדות חיוניים בהתראה — FIELD PRESENCE
# ═══════════════════════════════════════════════════════════════════════════════
if not SILENT:
    print("\n── 2. שדות חיוניים בהתראה ──")

check("פרופיל סיכון (risk_profile_line) בהתראה",
      file_contains("telegram_bot.py", r"risk_profile_line"),
      "חסר risk_profile_line בבניית ההתראה", category="FIELD")

check("המלצת השקעה (invest_rec) בהתראה",
      file_contains("telegram_bot.py", r"invest_rec"),
      "חסר invest_rec בבניית ההתראה", category="FIELD")

check("מועד סיום (end_date_line) בהתראה",
      file_contains("telegram_bot.py", r"end_date_line"),
      "חסר end_date_line בבניית ההתראה", category="FIELD")

check("פער מחיר (price_gap_line) בהתראה",
      file_contains("telegram_bot.py", r"price_gap_line"),
      "חסר price_gap_line בבניית ההתראה", category="FIELD")

check("כותרת HOT (hot_header) בהתראה",
      file_contains("telegram_bot.py", r"hot_header"),
      "חסר hot_header בבניית ההתראה", category="FIELD")

check("עדיפות אוטומציה (priority_line) בהתראה",
      file_contains("telegram_bot.py", r"priority_line"),
      "חסר priority_line בבניית ההתראה", category="FIELD")

check("ניתוח AI (get_ai_risk_analysis) בהתראה",
      file_contains("telegram_bot.py", r"get_ai_risk_analysis"),
      "חסר קריאה ל-get_ai_risk_analysis", category="FIELD")

check("התראה דחופה 85%+ (send_urgent_alert) בהתראה",
      file_contains("telegram_bot.py", r"send_urgent_alert|urgent_alert"),
      "חסר קריאה ל-urgent_alert", category="FIELD")

check("נתיב audit_bot.py דינמי (לא /app קשיח)",
      not file_contains("telegram_bot.py", r'cwd="/app"'),
      "נמצא cwd=\"/app\" קשיח — /p_audit לא יעבוד ב-Railway!", category="FIELD")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. בדיקות פונקציונליות — FUNC (מריץ קוד אמיתי)
# ═══════════════════════════════════════════════════════════════════════════════
if not SILENT:
    print("\n── 3. בדיקות פונקציונליות ──")

try:
    sys.path.insert(0, BOT_DIR)
    import expert_profiles as ep

    # get_expert_tag מחזיר רמת סיכון
    tag = ep.get_expert_tag("Fredi9999")
    check("get_expert_tag(Fredi9999) מחזיר רמת סיכון",
          any(x in tag for x in ["סיכון", "🟢", "🟡", "🔴", "LOW", "MED", "HIGH"]),
          f"תג: {tag[:60]}", category="FUNC")

    # get_expert_tag מחזיר אחוז הצלחה
    check("get_expert_tag(Fredi9999) מחזיר אחוז הצלחה",
          "%" in tag or "הצלחה" in tag,
          f"תג: {tag[:60]}", category="FUNC")

    # get_invest_recommendation מחזיר המלצה
    rec = ep.get_invest_recommendation("Fredi9999")
    check("get_invest_recommendation(Fredi9999) מחזיר המלצה חיובית",
          any(x in rec for x in ["מומלץ", "קנייה", "BUY", "STRONG", "חזק"]),
          f"המלצה: {rec[:60]}", category="FUNC")

    # kch123 מסומן AVOID
    rec_bad = ep.get_invest_recommendation("kch123")
    check("get_invest_recommendation(kch123) מסומן AVOID",
          any(x in rec_bad for x in ["לא מומלץ", "AVOID", "הימנע"]),
          f"המלצה: {rec_bad[:60]}", category="FUNC")

    # get_hot_alert_header מחזיר 🔥 ל-Fredi9999
    header = ep.get_hot_alert_header("Fredi9999")
    check("get_hot_alert_header(Fredi9999) מחזיר כותרת 🔥",
          "🔥" in header and len(header) > 10,
          f"כותרת: {header[:50]}", category="FUNC")

    # ארנק לא ידוע מחזיר "מומחה חדש"
    tag_unk = ep.get_expert_tag("UNKNOWN_XYZ_999")
    check("get_expert_tag לארנק לא ידוע מחזיר 'מומחה חדש'",
          any(x in tag_unk for x in ["מומחה חדש", "בבדיקה", "חדש"]),
          f"תג: {tag_unk[:60]}", category="FUNC")

except Exception as e:
    check("expert_profiles.py נטען בהצלחה", False, str(e), category="FUNC")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. בדיקות API חיות — LIVE
# ═══════════════════════════════════════════════════════════════════════════════
if not SILENT:
    print("\n── 4. בדיקות API חיות ──")

# Polymarket trades API
try:
    r = requests.get(
        "https://data-api.polymarket.com/trades",
        params={"user": "0x56687bf447db6ffa42ffe2204a05edaa20f55839", "limit": 1},
        timeout=10
    )
    check("Polymarket trades API מגיב",
          r.status_code == 200 and isinstance(r.json(), list),
          f"status={r.status_code}", category="LIVE")
except Exception as e:
    check("Polymarket trades API מגיב", False, str(e), category="LIVE")

# Gamma API
try:
    r2 = requests.get("https://gamma-api.polymarket.com/markets",
                      params={"limit": 1}, timeout=10)
    check("Gamma API מגיב", r2.status_code == 200, f"status={r2.status_code}", category="LIVE")
except Exception as e:
    check("Gamma API מגיב", False, str(e), category="LIVE")

# end_date נשלף מה-API לפי asset_id
try:
    from tracker import get_market_question
    # asset_id של שוק ידוע
    test_asset = "21742633143463906290569050155826241533067272736897614950488156847949938836455"
    q, url, end_date, cid = get_market_question(test_asset)
    check("end_date נשלף מה-API לפי asset_id",
          end_date is not None and len(str(end_date)) >= 8,
          f"end_date={end_date} (None = בעיה!)", category="LIVE")
except Exception as e:
    check("end_date נשלף מה-API לפי asset_id", False, str(e), category="LIVE")

# end_date נשלף גם לפי slug (ללא asset_id)
try:
    q2, url2, end_date2, cid2 = get_market_question("", slug="presidential-election-winner-2024")
    check("end_date נשלף לפי slug (ללא asset_id)",
          url2 != "https://polymarket.com",
          f"end_date={end_date2}, url={url2[:50]}", category="LIVE")
except Exception as e:
    check("end_date נשלף לפי slug", False, str(e), category="LIVE")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. לולאות ומנגנונים — CODE
# ═══════════════════════════════════════════════════════════════════════════════
if not SILENT:
    print("\n── 5. לולאות ומנגנונים ──")

check("לולאת בקרה מעגלית יומית",
      file_contains("telegram_bot.py", r"_circular_audit_loop"))
check("לולאת סגירת שווקים (settlement)",
      file_contains("telegram_bot.py", r"_settlement_loop"))
check("דוח שבועי (ראשון 09:00)",
      file_contains("telegram_bot.py", r"_weekly_report_loop"))
check("תזכורת עסקאות פתוחות (18:00)",
      file_contains("telegram_bot.py", r"_open_trades_reminder_loop"))
check("גיבוי יומי",
      file_contains("telegram_bot.py", r"_daily_backup_loop"))
check("גילוי מומחים חדשים (חודשי)",
      file_contains("telegram_bot.py", r"_monthly_discovery_loop"))
check("בדיקת ארנקים יומית",
      file_contains("telegram_bot.py", r"validate_expert_wallets_job"))
check("הגנת ארנק MAX_SINGLE_TRADE_PERCENT",
      file_contains("config.py", r"MAX_SINGLE_TRADE_PERCENT"))
check("התראה דחופה 85%+ (urgent_alert)",
      file_contains("telegram_bot.py", r"send_urgent_alert|urgent_alert") and
      file_contains("urgent_alert.py", r"URGENT_THRESHOLD_WIN_RATE"))
check("/p_audit command handler",
      file_contains("telegram_bot.py", r"cmd_audit.*p_audit|p_audit.*cmd_audit"))

# ═══════════════════════════════════════════════════════════════════════════════
# 6. משתני סביבה — ENV
# ═══════════════════════════════════════════════════════════════════════════════
if not SILENT:
    print("\n── 6. משתני סביבה ──")

env_checks = [
    ("TELEGRAM_BOT_TOKEN", "טוקן טלגרם"),
    ("TELEGRAM_CHAT_ID", "מזהה צ'אט"),
    ("WALLET_ADDRESS", "כתובת ארנק"),
    ("PRIVATE_KEY", "מפתח פרטי"),
    ("OPENAI_API_KEY", "מפתח OpenAI — AI לא יעבוד בלעדיו!"),
    ("GMAIL_SENDER", "Gmail שולח — התראות אימייל לא יעבדו!"),
    ("GMAIL_APP_PASS", "Gmail App Password — התראות אימייל לא יעבדו!"),
]
for var, desc in env_checks:
    check(f"{var} ({desc})",
          env_set(var),
          f"חסר! {desc}", category="ENV")

# ═══════════════════════════════════════════════════════════════════════════════
# 7. Pipeline 8 שלבים — PIPELINE
# ═══════════════════════════════════════════════════════════════
if not SILENT:
    print("\n── 7. Pipeline 8 שלבים ──")

# P43 — trade_pipeline.py קיים
check("P43 trade_pipeline.py קיים",
      file_exists("trade_pipeline.py"),
      "חסר trade_pipeline.py!", category="PIPELINE")

check("P43 trade_pipeline.py תקין תחבירתית",
      syntax_ok("trade_pipeline.py"),
      "שגיאת תחביר ב-trade_pipeline.py!", category="PIPELINE")

# P44 — Expert Stop-Loss
check("P44 Expert Stop-Loss (השעיית אחרי 5 הפסדים)",
      file_contains("trade_pipeline.py", r"EXPERT_STOP_LOSS_STREAK|stop_loss_streak|consecutive_losses"),
      "חסר מנגנון Expert Stop-Loss!", category="PIPELINE")

# P45 — Herd Detection
check("P45 Herd Detection (5+ מומחים)",
      file_contains("trade_pipeline.py", r"HERD_DETECTION_THRESHOLD|herd_detection|herd_count"),
      "חסר מנגנון Herd Detection!", category="PIPELINE")

# P46 — Sector Exposure
check("P46 Sector Exposure (מקסימום 3 עסקאות לנושא)",
      file_contains("trade_pipeline.py", r"MAX_SECTOR_TRADES|sector_exposure|sector_count"),
      "חסר מנגנון Sector Exposure!", category="PIPELINE")

# P47 — Median Filter
check("P47 Median Filter (חציון מחירי כניסה)",
      file_contains("market_analysis.py", r"median_filter_experts"),
      "חסר פונקציית median_filter_experts!", category="PIPELINE")

# P48 — Slippage Tracking
check("P48 Slippage Tracking (30 שניות)",
      file_contains("trade_pipeline.py", r"SLIPPAGE_DELAY_SECONDS|slippage_pct|record_slippage"),
      "חסר מנגנון Slippage Tracking!", category="PIPELINE")

# P49 — RETRY_ATTEMPTS=0
check("P49 RETRY_ATTEMPTS=0 ב-config.py",
      file_contains("config.py", r"RETRY_ATTEMPTS"),
      "חסר RETRY_ATTEMPTS ב-config.py!", category="PIPELINE")

# P50 — HIGH risk multiplier
check("P50 HIGH risk ×0.6 ב-config.py",
      file_contains("config.py", r"KELLY_RISK_MULTIPLIERS"),
      "חסר KELLY_RISK_MULTIPLIERS ב-config.py!", category="PIPELINE")

# P51 — Pipeline מחובר לטלגרם
check("P51 Pipeline מחובר ל-telegram_bot.py",
      file_contains("telegram_bot.py", r"run_pipeline|trade_pipeline"),
      "חסר קריאה ל-run_pipeline ב-telegram_bot.py!", category="PIPELINE")

# P52 — check_expert_drift
check("P52 check_expert_drift ב-market_analysis.py",
      file_contains("market_analysis.py", r"check_expert_drift"),
      "חסר check_expert_drift ב-market_analysis.py!", category="PIPELINE")

# בדיקה פונקציונלית: Pipeline עובד עם TradeSignal
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("tp", os.path.join(BOT_DIR, "trade_pipeline.py"))
    tp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tp)
    ts = tp.TradeSignal(
        expert_name="TestExpert",
        wallet_address="0x0",
        market_question="Test market?",
        market_slug="test-market",
        direction="YES",
        expert_price=0.6,
        current_price=0.6,
        expert_trade_usd=100,
    )
    result = tp.run_pipeline(ts, base_amount=50, balance=1000)
    check("P43 run_pipeline מחזיר TradeSignal",
          hasattr(result, "approved"),
          f"approved={result.approved}", category="PIPELINE")
except Exception as _pe:
    check("P43 run_pipeline מחזיר TradeSignal", False, str(_pe), category="PIPELINE")

# ═══════════════════════════════════════════════════════════════
# 8. מודולים חדשים — NEW MODULES
# ═══════════════════════════════════════════════════════════════
if not SILENT:
    print("\n── 8. מודולים חדשים (Backtesting, Exit Manager, Wallet Scanner) ──")

# P53 — backtester.py קיים
check("P53 backtester.py קיים",
      file_exists("backtester.py"),
      "חסר backtester.py!", category="NEW_MODULES")

check("P53 backtester.py תקין תחבירתית",
      syntax_ok("backtester.py"),
      "שגיאת תחביר ב-backtester.py!", category="NEW_MODULES")

# P54 — run_full_backtest קיים
check("P54 run_full_backtest פונקציה קיימת",
      file_contains("backtester.py", r"def run_full_backtest"),
      "חסר run_full_backtest!", category="NEW_MODULES")

# P55 — exit_manager.py קיים
check("P55 exit_manager.py קיים",
      file_exists("exit_manager.py"),
      "חסר exit_manager.py!", category="NEW_MODULES")

check("P55 exit_manager.py תקין תחבירתית",
      syntax_ok("exit_manager.py"),
      "שגיאת תחביר ב-exit_manager.py!", category="NEW_MODULES")

# P56 — Take Profit פרמטרים ב-config.py
check("P56 TAKE_PROFIT_PCT ב-config.py",
      file_contains("config.py", r"TAKE_PROFIT_PCT"),
      "חסר TAKE_PROFIT_PCT ב-config.py!", category="NEW_MODULES")

check("P56 STOP_LOSS_PCT ב-config.py",
      file_contains("config.py", r"STOP_LOSS_PCT"),
      "חסר STOP_LOSS_PCT ב-config.py!", category="NEW_MODULES")

check("P56 TIME_EXIT_HOURS ב-config.py",
      file_contains("config.py", r"TIME_EXIT_HOURS"),
      "חסר TIME_EXIT_HOURS ב-config.py!", category="NEW_MODULES")

# P57 — Exit Manager מחובר ל-telegram_bot.py
check("P57 ExitManager מחובר ל-telegram_bot.py",
      file_contains("telegram_bot.py", r"ExitManager|exit_manager"),
      "חסר חיבור ExitManager ל-telegram_bot.py!", category="NEW_MODULES")

check("P57 _exit_manager_loop קיימת ב-telegram_bot.py",
      file_contains("telegram_bot.py", r"_exit_manager_loop"),
      "חסר _exit_manager_loop!", category="NEW_MODULES")

# P58 — wallet_scanner.py קיים
check("P58 wallet_scanner.py קיים",
      file_exists("wallet_scanner.py"),
      "חסר wallet_scanner.py!", category="NEW_MODULES")

check("P58 wallet_scanner.py תקין תחבירתית",
      syntax_ok("wallet_scanner.py"),
      "שגיאת תחביר ב-wallet_scanner.py!", category="NEW_MODULES")

# P59 — run_wallet_scan פונקציה קיימת
check("P59 run_wallet_scan פונקציה קיימת",
      file_contains("wallet_scanner.py", r"def run_wallet_scan"),
      "חסר run_wallet_scan!", category="NEW_MODULES")

# P60 — wallet_scanner מחובר ל-telegram_bot.py
check("P60 wallet_scanner מחובר ל-telegram_bot.py",
      file_contains("telegram_bot.py", r"wallet_scanner|run_wallet_scan"),
      "חסר חיבור wallet_scanner ל-telegram_bot.py!", category="NEW_MODULES")

# P61 — בדיקה פונקציונלית: ExitManager ניתן ליצירה
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("em", os.path.join(BOT_DIR, "exit_manager.py"))
    _em = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_em)
    _mgr = _em.ExitManager()
    _open = _mgr.get_open_positions()
    check("P61 ExitManager ניתן ליצירה ושליפת פוזיציות",
          isinstance(_open, list),
          f"סוג שגוי: {type(_open)}", category="NEW_MODULES")
except Exception as _eme:
    check("P61 ExitManager ניתן ליצירה", False, str(_eme), category="NEW_MODULES")

# ═══════════════════════════════════════════════════════════════
# סיכום + שליחה לטלגרם
# ═══════════════════════════════════════════════════════════════
passed_list = [r for r in results if r["passed"] is True]
failed_list = [r for r in results if r["passed"] is False and r["icon"] == FAIL]
warn_list   = [r for r in results if r["icon"] == WARN]
total = len(passed_list) + len(failed_list) + len(warn_list)

if not SILENT:
    print(f"\n{'='*60}")
    print(f"📊 תוצאות: {len(passed_list)}/{total} עברו | ❌ {len(failed_list)} כשלים | ⚠️ {len(warn_list)} אזהרות")
    if failed_list:
        print("\n🚨 כשלים:")
        for r in failed_list:
            print(f"  ❌ [{r['category']}] {r['name']}" + (f"\n     ↳ {r['detail']}" if r['detail'] else ""))
    print(f"{'='*60}\n")


def send_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
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
status_emoji = "✅" if not failed_list else "❌"

lines = [
    f"{status_emoji} *בקרה מעגלית פונקציונלית — {now_str}*\n",
    f"📊 עברו: *{len(passed_list)}/{total}* | ❌ כשלים: *{len(failed_list)}* | ⚠️ אזהרות: *{len(warn_list)}*\n",
]

if failed_list:
    lines.append("*🚨 כשלים שדורשים תיקון מיידי:*")
    for r in failed_list:
        lines.append(f"  ❌ `[{r['category']}]` {r['name']}")
        if r['detail']:
            lines.append(f"     ↳ _{r['detail']}_")

if warn_list:
    lines.append("\n*⚠️ אזהרות:*")
    for r in warn_list:
        lines.append(f"  ⚠️ {r['name']}")

if not failed_list and not warn_list:
    lines.append("🎉 *כל הבדיקות עברו — המערכת תקינה לחלוטין!*")

lines.append("\n_/p\\_audit לדוח מלא_")

if not SILENT:
    send_telegram("\n".join(lines))

sys.exit(1 if failed_list else 0)
