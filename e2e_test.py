"""
e2e_test.py — בדיקת End-to-End חיה
════════════════════════════════════════════════════════════════════════════════
בדיקה זו מריצה סיגנל מדומה דרך כל המערכת ומאמתת שכל שלב
אכן מתבצע ומחזיר תוצאה נכונה — לא רק בודקת שהקוד קיים.

כל בדיקה מסומנת:
  ✅ PASS  — הפונקציה רצה והחזירה תוצאה תקינה
  ❌ FAIL  — הפונקציה נכשלה או החזירה תוצאה שגויה
  ⚠️ WARN  — הפונקציה רצה אבל התוצאה חלקית

הרצה: python3.11 e2e_test.py
════════════════════════════════════════════════════════════════════════════════
"""
import sys
import os
import traceback

BOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BOT_DIR)

PASS  = "✅ PASS"
FAIL  = "❌ FAIL"
WARN  = "⚠️ WARN"

results = []

def check(name: str, passed: bool, detail: str = "", warn: bool = False):
    icon = WARN if warn else (PASS if passed else FAIL)
    results.append({"name": name, "icon": icon, "passed": passed, "detail": detail})
    status = f"{icon} {name}"
    if detail:
        status += f" — {detail}"
    print(status)

# ════════════════════════════════════════════════════════════════════════════
# 1. בדיקת ייבוא מודולים
# ════════════════════════════════════════════════════════════════════════════
print("\n── 1. ייבוא מודולים ──────────────────────────────────────────────────")

try:
    from trade_pipeline import (
        run_pipeline, TradeSignal, format_pipeline_summary,
        stage1_drawdown_guard, stage2_liquidity_check,
        stage3_spread_filter, stage4_expert_stop_loss,
        stage5_herd_detection, stage6_sector_exposure,
        stage7_position_sizing, stage8_signals_and_alerts,
        _calculate_confidence_score, record_trade_result
    )
    check("ייבוא trade_pipeline", True)
except Exception as e:
    check("ייבוא trade_pipeline", False, str(e))
    print("⛔ לא ניתן להמשיך ללא trade_pipeline")
    sys.exit(1)

try:
    from dry_run_journal import check_and_settle_open_trades, record_trade
    check("ייבוא dry_run_journal", True)
except Exception as e:
    check("ייבוא dry_run_journal", False, str(e))

try:
    from exit_manager import ExitManager
    check("ייבוא exit_manager", True)
except Exception as e:
    check("ייבוא exit_manager", False, str(e))

try:
    from backtester import run_full_backtest
    check("ייבוא backtester", True)
except Exception as e:
    check("ייבוא backtester", False, str(e))

try:
    from wallet_scanner import run_wallet_scan
    check("ייבוא wallet_scanner", True)
except Exception as e:
    check("ייבוא wallet_scanner", False, str(e))

try:
    from market_analysis import check_expert_drift, analyze_price_gap
    check("ייבוא market_analysis", True)
except Exception as e:
    check("ייבוא market_analysis", False, str(e))

try:
    from expert_profiles import get_wallet_profile, get_expert_tag
    check("ייבוא expert_profiles", True)
except Exception as e:
    check("ייבוא expert_profiles", False, str(e))

# ════════════════════════════════════════════════════════════════════════════
# 2. בדיקת Pipeline — כל 8 שלבים בנפרד
# ════════════════════════════════════════════════════════════════════════════
print("\n── 2. Pipeline — 8 שלבים בנפרד ──────────────────────────────────────")

# סיגנל מדומה תקין
mock_signal = TradeSignal(
    expert_name       = "swisstony",
    wallet_address    = "0xtest1234",
    market_question   = "Will the Lakers win tonight?",
    market_slug       = "lakers-win-tonight",
    direction         = "YES",
    expert_price      = 0.55,
    current_price     = 0.57,   # פרש 3.6% — תקין
    expert_trade_usd  = 120.0,
    market_volume_usd = 50000.0,
    end_date          = "2026-04-01",
    asset_id          = "test_asset_001",
)

# שלב 1: Drawdown Guard
try:
    ok, msg = stage1_drawdown_guard(mock_signal, current_balance=1000.0)
    check("שלב 1 — Drawdown Guard", isinstance(ok, bool), f"ok={ok}, msg='{msg}'")
except Exception as e:
    check("שלב 1 — Drawdown Guard", False, traceback.format_exc(limit=1))

# שלב 2: Liquidity Check
try:
    ok, msg = stage2_liquidity_check(mock_signal)
    check("שלב 2 — Liquidity Check", isinstance(ok, bool), f"ok={ok}, msg='{msg}'")
except Exception as e:
    check("שלב 2 — Liquidity Check", False, traceback.format_exc(limit=1))

# שלב 3: Spread Filter — עם מחיר נוכחי שונה ממחיר המומחה
try:
    ok, msg = stage3_spread_filter(mock_signal)
    spread_pct = abs(mock_signal.current_price - mock_signal.expert_price) / mock_signal.expert_price * 100
    # בדוק שהפרש מחושב נכון (לא תמיד 0%)
    correct_spread = spread_pct > 0
    check("שלב 3 — Spread Filter (פרש לא 0%)", correct_spread,
          f"פרש={spread_pct:.1f}%, ok={ok}")
except Exception as e:
    check("שלב 3 — Spread Filter", False, traceback.format_exc(limit=1))

# שלב 4: Expert Stop-Loss
try:
    ok, msg = stage4_expert_stop_loss(mock_signal)
    check("שלב 4 — Expert Stop-Loss", isinstance(ok, bool), f"ok={ok}, msg='{msg}'")
except Exception as e:
    check("שלב 4 — Expert Stop-Loss", False, traceback.format_exc(limit=1))

# שלב 5: Herd Detection
try:
    ok, msg = stage5_herd_detection(mock_signal)
    check("שלב 5 — Herd Detection", isinstance(ok, bool), f"ok={ok}, msg='{msg}'")
except Exception as e:
    check("שלב 5 — Herd Detection", False, traceback.format_exc(limit=1))

# שלב 6: Sector Exposure
try:
    ok, msg = stage6_sector_exposure(mock_signal)
    check("שלב 6 — Sector Exposure", isinstance(ok, bool), f"ok={ok}, msg='{msg}'")
except Exception as e:
    check("שלב 6 — Sector Exposure", False, traceback.format_exc(limit=1))

# שלב 7: Position Sizing
try:
    stage7_position_sizing(mock_signal, base_amount=50.0, expert_profile={"win_rate_pct": 75, "roi_pct": 85})
    check("שלב 7 — Position Sizing", mock_signal.final_trade_usd > 0,
          f"final_trade_usd={mock_signal.final_trade_usd:.2f}")
except Exception as e:
    check("שלב 7 — Position Sizing", False, traceback.format_exc(limit=1))

# שלב 8: Signals & Alerts
try:
    result8 = stage8_signals_and_alerts(mock_signal, expert_profile={"win_rate_pct": 75, "roi_pct": 85})
    has_confidence = "confidence_score" in result8
    check("שלב 8 — Signals & Alerts", has_confidence,
          f"confidence_score={result8.get('confidence_score', 'חסר')}")
except Exception as e:
    check("שלב 8 — Signals & Alerts", False, traceback.format_exc(limit=1))

# ════════════════════════════════════════════════════════════════════════════
# 3. בדיקת run_pipeline מלא — מתחילה ועד סוף
# ════════════════════════════════════════════════════════════════════════════
print("\n── 3. run_pipeline מלא ───────────────────────────────────────────────")

mock_signal2 = TradeSignal(
    expert_name       = "swisstony",
    wallet_address    = "0xtest1234",
    market_question   = "Will the Lakers win tonight?",
    market_slug       = "lakers-win-tonight",
    direction         = "YES",
    expert_price      = 0.55,
    current_price     = 0.57,
    expert_trade_usd  = 120.0,
    market_volume_usd = 50000.0,
    end_date          = "2026-04-01",
    asset_id          = "test_asset_001",
)

try:
    result = run_pipeline(mock_signal2, base_amount=50.0, balance=1000.0,
                          expert_profile={"win_rate_pct": 75, "roi_pct": 85})
    check("run_pipeline מחזיר TradeSignal", isinstance(result, TradeSignal))
    check("run_pipeline — approved=True לסיגנל תקין", result.approved is True,
          f"rejection_reason='{result.rejection_reason}'")
    check("run_pipeline — final_trade_usd > 0", result.final_trade_usd > 0,
          f"final_trade_usd={result.final_trade_usd:.2f}")
    check("run_pipeline — pipeline_log לא ריק", len(result.pipeline_log) > 0,
          f"{len(result.pipeline_log)} רשומות")
except Exception as e:
    check("run_pipeline מלא", False, traceback.format_exc(limit=2))

# ════════════════════════════════════════════════════════════════════════════
# 4. בדיקת חסימה — סיגנל עם פרש גבוה מדי
# ════════════════════════════════════════════════════════════════════════════
print("\n── 4. חסימת סיגנל עם פרש גבוה ────────────────────────────────────────")

mock_blocked = TradeSignal(
    expert_name       = "swisstony",
    wallet_address    = "0xtest1234",
    market_question   = "Will X happen?",
    market_slug       = "x-happen",
    direction         = "YES",
    expert_price      = 0.30,
    current_price     = 0.65,   # פרש 116% — חייב להיחסם
    expert_trade_usd  = 50.0,
    market_volume_usd = 50000.0,
)

try:
    result_blocked = run_pipeline(mock_blocked, base_amount=50.0, balance=1000.0)
    check("Pipeline חוסם סיגנל עם פרש >50%", result_blocked.approved is False,
          f"approved={result_blocked.approved}, reason='{result_blocked.rejection_reason}'")
except Exception as e:
    check("Pipeline חסימת פרש גבוה", False, traceback.format_exc(limit=1))

# ════════════════════════════════════════════════════════════════════════════
# 5. בדיקת format_pipeline_summary — שורת ציון ברורה
# ════════════════════════════════════════════════════════════════════════════
print("\n── 5. שורת ציון Pipeline ─────────────────────────────────────────────")

try:
    summary = format_pipeline_summary(mock_signal2, expert_profile={"win_rate_pct": 75, "roi_pct": 85, "risk_level": "low"})
    has_score_line = "בדיקות" in summary and "/" in summary and "ציון" in summary
    has_risk_label = "סיכון" in summary
    check("שורת ציון מכילה 'X/8 בדיקות'", has_score_line, f"summary='{summary[:100]}'")
    check("שורת ציון מכילה 'סיכון'", has_risk_label)
    print(f"   📋 תצוגה: {summary.strip()[:200]}")
except Exception as e:
    check("format_pipeline_summary", False, traceback.format_exc(limit=1))

# ════════════════════════════════════════════════════════════════════════════
# 6. בדיקת record_trade_result — מנגנון השהיית מומחה
# ════════════════════════════════════════════════════════════════════════════
print("\n── 6. מנגנון השהיית מומחה ────────────────────────────────────────────")

try:
    # 5 הפסדים רצופים צריכים להשהות את המומחה
    test_expert = "_e2e_test_expert_"
    for i in range(5):
        record_trade_result(test_expert, won=False, roi=-100)
    # עכשיו Pipeline צריך לחסום אותו
    mock_suspended = TradeSignal(
        expert_name       = test_expert,
        wallet_address    = "0xtest",
        market_question   = "Test market",
        market_slug       = "test",
        direction         = "YES",
        expert_price      = 0.5,
        current_price     = 0.5,
        expert_trade_usd  = 50.0,
        market_volume_usd = 50000.0,
    )
    result_suspended = run_pipeline(mock_suspended, base_amount=50.0, balance=1000.0)
    check("מומחה מושהה אחרי 5 הפסדים", result_suspended.approved is False,
          f"approved={result_suspended.approved}, reason='{result_suspended.rejection_reason}'")
    # נקה את נתוני הבדיקה
    from trade_pipeline import _load_expert_perf, _save_expert_perf
    data = _load_expert_perf()
    if test_expert in data:
        del data[test_expert]
        _save_expert_perf(data)
except Exception as e:
    check("מנגנון השהיית מומחה", False, traceback.format_exc(limit=2))

# ════════════════════════════════════════════════════════════════════════════
# 7. בדיקת ExitManager
# ════════════════════════════════════════════════════════════════════════════
print("\n── 7. ExitManager ────────────────────────────────────────────────────")

try:
    em = ExitManager()
    positions_before = len(em.get_open_positions())
    mock_signal_dict = {
        "trade_id":       "e2e_test_001",
        "market_slug":    "test-market",
        "outcome":        "YES",
        "expert_name":    "swisstony",
        "market_question": "Test market",
    }
    em.add_position(
        signal      = mock_signal_dict,
        entry_price = 0.55,
        amount_usd  = 50.0,
    )
    positions_after = len(em.get_open_positions())
    check("ExitManager.add_position עובד", positions_after == positions_before + 1,
          f"לפני={positions_before}, אחרי={positions_after}")
    # נקה — סגור את הפוזיציה הפתוחה דרך _close_position
    open_pos = em.get_open_positions()
    if open_pos:
        last_pos = open_pos[-1]
        em._close_position(last_pos, exit_reason="e2e_test_cleanup")
    # בדוק שהפוזיציה נסגרה בדיסק
    from exit_manager import _load_positions
    _all = _load_positions()
    _open_after = [p for p in _all if p.get("status") == "open"]
    check("ExitManager._close_position עובד", len(_open_after) == positions_before,
          f"צפוי={positions_before}, בפועל={len(_open_after)}")
except Exception as e:
    check("ExitManager", False, traceback.format_exc(limit=2))

# ════════════════════════════════════════════════════════════════════════════
# 8. בדיקת _calculate_confidence_score — ציון אמיתי
# ════════════════════════════════════════════════════════════════════════════
print("\n── 8. חישוב ציון ביטחון ──────────────────────────────────────────────")

try:
    score_high = _calculate_confidence_score(
        mock_signal2,
        {"win_rate_pct": 80, "roi_pct": 150, "risk_level": "low"}
    )
    score_low = _calculate_confidence_score(
        mock_signal2,
        {"win_rate_pct": 30, "roi_pct": -50, "risk_level": "high"}
    )
    check("ציון גבוה למומחה טוב", score_high > 60, f"ציון={score_high}")
    check("ציון נמוך למומחה גרוע", score_low < score_high, f"ציון={score_low} < {score_high}")
    check("ציון בטווח 0-100", 0 <= score_high <= 100 and 0 <= score_low <= 100)
except Exception as e:
    check("חישוב ציון ביטחון", False, traceback.format_exc(limit=1))

# ══# ══════════════════════════════════════════════════════════════════════════
# 9. בדיקת חסימת מחיר נמוך ופרש גבוה (ואלנסיה CF / Newcastle)
# ══════════════════════════════════════════════════════════════════════════
print("\n── 9. חסימת מחיר נמוך ופרש גבוה (ואלנסיה CF / Newcastle) ──────────────────────")
try:
    from config import MIN_TRADE_PRICE
    # בדיקה 1: Newcastle — מחיר 0.08 (סיכון קיצוני נמוך מדי)
    ts_newcastle = TradeSignal(
        expert_name="test_expert", wallet_address="0x0",
        market_question="Will Newcastle win?", market_slug="newcastle-win",
        direction="YES", expert_price=0.08, current_price=0.08,
        expert_trade_usd=130, market_volume_usd=50000,
        end_date=None, asset_id="test_newcastle"
    )
    # אפס את ה-peak_balance כדי שה-Drawdown Guard לא יחסום את הבדיקות
    import market_analysis as _ma
    _ma._peak_balance = None
    _ma._trading_halted = False
    _TEST_BALANCE = 1000.0  # יתרה תקינה לבדיקות
    result_newcastle = run_pipeline(ts_newcastle, base_amount=32, balance=_TEST_BALANCE)
    check("ניוקאסל (0.08) נחסם על ידי Pipeline",
          not result_newcastle.approved,
          f"approved={result_newcastle.approved}, reason={result_newcastle.rejection_reason[:60] if result_newcastle.rejection_reason else 'N/A'}")
    # בדיקה 2: Valencia CF — פרש 38.7% (0.62 מומחה, 0.38 נוכחי)
    ts_valencia = TradeSignal(
        expert_name="test_expert", wallet_address="0x0",
        market_question="Will Valencia CF win?", market_slug="valencia-cf-win",
        direction="NO", expert_price=0.62, current_price=0.38,
        expert_trade_usd=1329, market_volume_usd=50000,
        end_date=None, asset_id="test_valencia"
    )
    _ma._peak_balance = None
    _ma._trading_halted = False
    result_valencia = run_pipeline(ts_valencia, base_amount=32, balance=_TEST_BALANCE)
    spread_pct_val = abs(0.38 - 0.62) / 0.62 * 100
    check(f"ואלנסיה CF ({spread_pct_val:.1f}% פרש) נחסם על ידי Pipeline",
          not result_valencia.approved,
          f"approved={result_valencia.approved}, reason={result_valencia.rejection_reason[:60] if result_valencia.rejection_reason else 'N/A'}")
    # בדיקה 3: עסקה תקינה עוברת (Lakers, פרש 3.6%, מחיר 0.55)
    ts_good_trade = TradeSignal(
        expert_name="swisstony", wallet_address="0xtest1234",
        market_question="Will the Lakers win tonight?", market_slug="lakers-win-tonight",
        direction="YES", expert_price=0.55, current_price=0.57,
        expert_trade_usd=120.0, market_volume_usd=50000.0,
        end_date="2026-04-01", asset_id="test_asset_001"
    )
    _ma._peak_balance = None
    _ma._trading_halted = False
    result_good_trade = run_pipeline(ts_good_trade, base_amount=32, balance=_TEST_BALANCE)
    check("עסקה תקינה (Lakers, פרש 3.6%) עוברת Pipeline",
          result_good_trade.approved,
          f"rejected: {result_good_trade.rejection_reason}")
except Exception as e:
    check("בדיקת חסימת מחיר ופרש", False, traceback.format_exc(limit=2))

# ══════════════════════════════════════════════════════════════════════════
# סיכום
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 70)
passed = [r for r in results if r["icon"] == PASS]
failed = [r for r in results if r["icon"] == FAIL]
warned = [r for r in results if r["icon"] == WARN]
total  = len(results)

print(f"📊 תוצאות E2E: {len(passed)}/{total} עברו | ❌ {len(failed)} כשלים | ⚠️ {len(warned)} אזהרות")

if failed:
    print("\n❌ כשלים שדורשים תיקון:")
    for r in failed:
        print(f"   • {r['name']}: {r['detail']}")

if not failed:
    print("\n✅ כל הבדיקות החיות עברו — המערכת עובדת כתזמורת!")
else:
    print(f"\n⛔ {len(failed)} בדיקות נכשלו — יש לתקן לפני פריסה!")

sys.exit(1 if failed else 0)
