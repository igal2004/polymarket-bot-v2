"""
trade_pipeline.py — מנוע החלטה מאוחד בן 8 שלבים
═══════════════════════════════════════════════════════════════════════════════
כל עסקה חדשה עוברת את 8 השלבים בסדר קבוע.
כל שלב עצמאי, מתועד, וניתן להפעלה/כיבוי בנפרד.
סה"כ 25 בדיקות מ-3 מקורות: המערכת שלנו + ניתוח קלוד + ניתוח ג'מיני.

שלב 1: 🛑 Drawdown Guard       — עצירה אם הפורטפוליו ירד >30% מהשיא
שלב 2: 💧 Liquidity Check      — חסימת שווקים עם נפח < $5,000
שלב 3: 📉 Spread Filter        — פרש מחיר דינמי (+10%/>$50K, +20%/רגיל)
שלב 4: 🚦 Expert Stop-Loss     — חסימה אם המומחה ב-5 הפסדים רצופים
שלב 5: 🐑 Herd Detection       — אזהרה/חסימה אם 5+ מומחים נכנסו (עדר)
שלב 6: 🗂️ Sector Exposure      — חסימה אם >3 עסקאות פתוחות על אותו נושא
שלב 7: ⚖️ Position Sizing      — Kelly × סיכון × קונברגנציה × drift
שלב 8: 📡 Signals & Alerts     — Drift Detection + קונברגנציה + Slippage

מקורות:
  [OUR]    = המערכת המקורית שלנו
  [CLAUDE] = ניתוח קלוד (13/03/2026)
  [GEMINI] = ניתוח ג'מיני (13/03/2026)
═══════════════════════════════════════════════════════════════════════════════
"""
import logging
import json
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ─── מבנה נתוני עסקה ──────────────────────────────────────────────────────────
@dataclass
class TradeSignal:
    """מייצג עסקה שמחכה להחלטה."""
    expert_name: str
    wallet_address: str
    market_question: str
    market_slug: str
    direction: str          # YES / NO
    expert_price: float     # מחיר שהמומחה קנה בו
    current_price: float    # מחיר נוכחי בשוק
    expert_trade_usd: float # גודל עסקת המומחה בדולרים
    market_volume_usd: float = 0.0
    end_date: Optional[str] = None
    asset_id: Optional[str] = None
    market_id: Optional[str] = None
    # שדות שמתמלאים על ידי ה-Pipeline
    approved: bool = False
    rejection_reason: str = ""
    final_trade_usd: float = 0.0
    convergence_count: int = 0
    convergence_names: list = field(default_factory=list)
    drift_warning: str = ""
    herd_warning: str = ""
    slippage_pct: float = 0.0
    pipeline_log: list = field(default_factory=list)

# ─── מסד נתוני ביצועי מומחים (נשמר בקובץ JSON) ────────────────────────────────
EXPERT_PERF_FILE = os.path.join(os.path.dirname(__file__), "expert_performance.json")

def _load_expert_perf() -> dict:
    """טוען נתוני ביצועי מומחים מקובץ JSON."""
    if os.path.exists(EXPERT_PERF_FILE):
        try:
            with open(EXPERT_PERF_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_expert_perf(data: dict):
    """שומר נתוני ביצועי מומחים לקובץ JSON."""
    try:
        with open(EXPERT_PERF_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"שגיאה בשמירת expert_performance: {e}")

def record_trade_result(expert_name: str, won: bool, roi: float):
    """
    [GEMINI] מעדכן את רצף ההפסדים/זכיות של מומחה לאחר סגירת עסקה.
    נקרא מ-telegram_bot.py כשעסקה נסגרת.
    """
    data = _load_expert_perf()
    if expert_name not in data:
        data[expert_name] = {
            "loss_streak": 0,
            "win_streak": 0,
            "suspended": False,
            "suspension_reason": "",
            "probation_wins": 0,
            "recent_30d_roi": [],
            "recent_30d_dates": [],
            "total_trades": 0,
            "total_wins": 0,
        }
    p = data[expert_name]
    p["total_trades"] = p.get("total_trades", 0) + 1
    now_str = datetime.utcnow().isoformat()
    # עדכון ROI 30 יום
    p["recent_30d_roi"].append(roi)
    p["recent_30d_dates"].append(now_str)
    # נקה ערכים ישנים מ-30 יום
    cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
    pairs = [(r, d) for r, d in zip(p["recent_30d_roi"], p["recent_30d_dates"]) if d >= cutoff]
    p["recent_30d_roi"] = [x[0] for x in pairs]
    p["recent_30d_dates"] = [x[1] for x in pairs]
    if won:
        p["total_wins"] = p.get("total_wins", 0) + 1
        p["win_streak"] = p.get("win_streak", 0) + 1
        p["loss_streak"] = 0
        # בדיקת חזרה מהשהיה — 5 זכיות ב-Dry Run
        if p.get("suspended") and p.get("probation_wins", 0) + 1 >= 5:
            p["suspended"] = False
            p["suspension_reason"] = ""
            p["probation_wins"] = 0
            logger.info(f"✅ {expert_name} חזר לסטטוס מאושר לאחר 5 זכיות")
        elif p.get("suspended"):
            p["probation_wins"] = p.get("probation_wins", 0) + 1
    else:
        p["loss_streak"] = p.get("loss_streak", 0) + 1
        p["win_streak"] = 0
    _save_expert_perf(data)
    return data[expert_name]

# ─── מאגר עסקאות פתוחות לזיהוי עדר וחשיפה סקטוריאלית ─────────────────────────
_recent_signals: list = []  # רשימת TradeSignal שאושרו לאחרונה

def _clean_old_signals():
    """מנקה סיגנלים ישנים מעל 24 שעות."""
    global _recent_signals
    cutoff = datetime.utcnow() - timedelta(hours=24)
    _recent_signals = [s for s in _recent_signals if hasattr(s, '_timestamp') and s._timestamp > cutoff]

# ═══════════════════════════════════════════════════════════════════════════════
# שלב 1: 🛑 DRAWDOWN GUARD
# מקור: [CLAUDE] שיפור 4 + [OUR] הגנות ארנק
# ═══════════════════════════════════════════════════════════════════════════════
def stage1_drawdown_guard(signal: TradeSignal, current_balance: float) -> tuple:
    """
    עוצר את כל המסחר אם הפורטפוליו ירד מעל MAX_DRAWDOWN_PERCENT מהשיא.
    מחזיר (pass: bool, message: str).
    """
    from market_analysis import check_drawdown_halt, update_peak_balance
    update_peak_balance(current_balance)
    halt, msg = check_drawdown_halt(current_balance)
    if halt:
        signal.pipeline_log.append(f"❌ שלב 1 [DRAWDOWN]: {msg}")
        return False, msg
    signal.pipeline_log.append(f"✅ שלב 1 [DRAWDOWN]: תקין (יתרה: ${current_balance:.2f})")
    return True, ""

# ═══════════════════════════════════════════════════════════════════════════════
# שלב 2: 💧 LIQUIDITY CHECK
# מקור: [CLAUDE] שיפור 2 + [GEMINI] #4
# ═══════════════════════════════════════════════════════════════════════════════
def stage2_liquidity_check(signal: TradeSignal) -> tuple:
    """
    חוסם שווקים עם נפח מסחר נמוך ממינ-MARKET_VOLUME_USD.
    שומר את רמת הגנה הדינמית לפי VOLUME_TIERS ב-signal לשימוש בשלב 3.
    """
    from config import MIN_MARKET_VOLUME_USD, VOLUME_TIERS
    vol = signal.market_volume_usd
    # ✅ תיקון: vol==0 משמעו שלא נשלף נפח מה-API — אזהרה (לא חסימה מוחלטת)
    if vol == 0:
        signal.pipeline_log.append(f"⚠️ שלב 2 [LIQUIDITY]: נפח לא ידוע — עובר באזהרה")
        # ברירת מחדל: הגנה רגילה
        signal.pipeline_log.append(f"🛡️ מדרגת הגנה: רגילה (Slippage מקסימלי: 2.0% | Spread מקסימלי: 20%)")
        signal._volume_tier = (2.0, 20)  # ברירת מחדל
        return True, ""  # אזהרה בלבד, לא חסימה — כי יתכן שה-API לא שלף נפח
    if vol < MIN_MARKET_VOLUME_USD:
        msg = f"נזילות נמוכה: ${vol:,.0f} < ${MIN_MARKET_VOLUME_USD:,} מינימום"
        signal.pipeline_log.append(f"❌ שלב 2 [LIQUIDITY]: {msg}")
        return False, msg
    # בחר מדרגת הגנה לפי נפח השוק
    slippage_limit = 2.0
    spread_limit = 20
    tier_label = "רגילה"
    for tier_vol, tier_slip, tier_spread in sorted(VOLUME_TIERS, key=lambda x: x[0]):
        if vol >= tier_vol:
            slippage_limit = tier_slip
            spread_limit = tier_spread
            if tier_vol >= 5000:
                tier_label = "רגילה"
            elif tier_vol >= 3000:
                tier_label = "מוגברת"
            else:
                tier_label = "חזקה"
    # שמור ב-signal לשימוש בשלב 3
    signal._volume_tier = (slippage_limit, spread_limit)
    signal.pipeline_log.append(
        f"✅ שלב 2 [LIQUIDITY]: נפח ${vol:,.0f} תקין "
        f"| 🛡️ מדרגת הגנה {tier_label} "
        f"(Slippage מקסימלי: {slippage_limit}% | Spread מקסימלי: {spread_limit}%)"
    )
    return True, ""

# ══# ═════════════════════════════════════════════════════════════════════════════
# שלב 2ב: 📅 EXPIRY CHECK
# מקור: [בקשת משתמש] סננון שווקים שנסגרים בתוך 90 יום
# ═════════════════════════════════════════════════════════════════════════════
def stage2b_expiry_check(signal: TradeSignal) -> tuple:
    """
    חוסם עסקאות בשווקים שנסגרים יותר מ-MAX_MARKET_DAYS_TO_EXPIRY יום מהיום.
    אם אין תאריך פקיעה או החישוב נכשל — עובר באזהרה (לא נחסם).
    """
    try:
        from config import MAX_MARKET_DAYS_TO_EXPIRY
    except ImportError:
        MAX_MARKET_DAYS_TO_EXPIRY = 90
    # 0 = ללא הגבלה
    if MAX_MARKET_DAYS_TO_EXPIRY <= 0:
        signal.pipeline_log.append(f"✅ שלב 2ב [EXPIRY]: ללא הגבלת זמן")
        return True, ""
    end_date_str = signal.end_date
    if not end_date_str:
        signal.pipeline_log.append(f"⚠️ שלב 2ב [EXPIRY]: אין תאריך פקיעה — עובר באזהרה")
        return True, ""  # בטוח — אם אין תאריך, לא נחסם
    try:
        # תמוך בפורמטים: ISO 8601 (עם/בלי Z), YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS
        end_date_str_clean = end_date_str.replace("Z", "+00:00")
        try:
            end_dt = datetime.fromisoformat(end_date_str_clean)
        except ValueError:
            # נסה פורמט פשוט YYYY-MM-DD
            end_dt = datetime.strptime(end_date_str[:10], "%Y-%m-%d")
        # הסר timezone info להשוואה פשוטה
        if hasattr(end_dt, 'tzinfo') and end_dt.tzinfo is not None:
            end_dt = end_dt.replace(tzinfo=None)
        days_to_expiry = (end_dt - datetime.utcnow()).days
        if days_to_expiry < 0:
            signal.pipeline_log.append(f"⚠️ שלב 2ב [EXPIRY]: שוק כבר נסגר — עובר באזהרה")
            return True, ""  # שוק שנסגר בעבר — אולי שגיאה בתאריך, לא נחסם
        if days_to_expiry > MAX_MARKET_DAYS_TO_EXPIRY:
            msg = (f"שוק נסגר בעוד {days_to_expiry} יום — מעל מקסימום {MAX_MARKET_DAYS_TO_EXPIRY} יום"
                  f" (פקיעה: {end_date_str[:10]})")
            signal.pipeline_log.append(f"❌ שלב 2ב [EXPIRY]: {msg}")
            return False, msg
        signal.pipeline_log.append(f"✅ שלב 2ב [EXPIRY]: נסגר בעוד {days_to_expiry} יום תקין")
        return True, ""
    except Exception as e:
        # בטוח — אם החישוב נכשל, לא נחסם את העסקה
        signal.pipeline_log.append(f"⚠️ שלב 2ב [EXPIRY]: שגיאה בבדיקת תאריך ({e}) — עובר")
        return True, ""

# ═════════════════════════════════════════════════════════════════════════════
# שלב 2ג: 💰 ENTRY PRICE FILTER
# מקור: [בקשת משתמש] חסימת עסקאות עם מחיר כניסה גבוה — יחס סיכון/תגמול לא משתלם
# ═════════════════════════════════════════════════════════════════════════════
def stage2c_entry_price_check(signal: TradeSignal) -> tuple:
    """
    חוסם עסקאות עם מחיר כניסה גבוה מדי (>MAX_ENTRY_PRICE).
    מחיר גבוה = רווח פוטנציאלי נמוך מול סיכון גבוה.
    אם MAX_ENTRY_PRICE=0 — ללא הגבלה.
    """
    try:
        from config import MAX_ENTRY_PRICE
    except ImportError:
        MAX_ENTRY_PRICE = 0.75
    if MAX_ENTRY_PRICE <= 0:
        signal.pipeline_log.append("✅ שלב 2ג [ENTRY_PRICE]: ללא הגבלת מחיר כניסה")
        return True, ""
    try:
        price = float(signal.current_price)
        if price <= 0:
            signal.pipeline_log.append("⚠️ שלב 2ג [ENTRY_PRICE]: מחיר לא תקין — עובר")
            return True, ""
        if price > MAX_ENTRY_PRICE:
            # חשב רווח פוטנציאלי לדוגמה על $32
            example_invest = 32.0
            potential_profit = example_invest * (1 - price) / price
            msg = (f"מחיר כניסה {price:.3f} מעל מקסימום {MAX_ENTRY_PRICE} "
                   f"(רווח פוטנציאלי: ${potential_profit:.2f} על $32 — לא משתלם)")
            signal.pipeline_log.append(f"❌ שלב 2ג [ENTRY_PRICE]: {msg}")
            return False, msg
        # חשב רווח פוטנציאלי ורשום בלוג
        example_invest = 32.0
        potential_profit = example_invest * (1 - price) / price
        ratio = (1 - price) / price
        signal.pipeline_log.append(
            f"✅ שלב 2ג [ENTRY_PRICE]: מחיר {price:.3f} תקין "
            f"(רווח פוטנציאלי: ${potential_profit:.2f} | יחס: 1:{ratio:.2f})"
        )
        return True, ""
    except Exception as e:
        signal.pipeline_log.append(f"⚠️ שלב 2ג [ENTRY_PRICE]: שגיאה ({e}) — עובר")
        return True, ""

# ═════════════════════════════════════════════════════════════════════════════
# שלב 3: 📉 SPREAD FILTER מקור: [CLAUDE] שיפור 1 + [GEMINI] config
# ═══════════════════════════════════════════════════════════════════════════════
def stage3_spread_filter(signal: TradeSignal) -> tuple:
    """
    בודק שהמחיר הנוכחי לא זזה יותר מדי מהמחיר שהמומחה קנה.
    עסקות גדולות (>$50K) מזיזות שוק — לכן פרש מחמיר יותר.
    [GEMINI] RETRY_ATTEMPTS=0: אם נדחה — לא לנסות שוב.
    """
    from config import MAX_SPREAD_PCT_DEFAULT, MAX_SPREAD_PCT_LARGE, LARGE_TRADE_THRESHOLD, MIN_TRADE_PRICE
    # ✅ תיקון: מחיר מומחה לא תקין — חסום (לא עובר אוטומטית)
    if signal.expert_price <= 0:
        msg = f"מחיר מומחה לא תקין: {signal.expert_price} — עסקאה נחסמת"
        signal.pipeline_log.append(f"❌ שלב 3 [SPREAD]: {msg}")
        return False, msg
    # ✅ תיקון: חסום עסקאות עם מחיר נמוך מדי (סיכון גבוה מאוד)
    if signal.expert_price < MIN_TRADE_PRICE:
        msg = (f"מחיר נמוך מדי: {signal.expert_price:.3f} < {MIN_TRADE_PRICE:.2f} מינימום "
               f"(סיכון גבוה מאוד — סיכוי ניצחון נמוך מב-{MIN_TRADE_PRICE*100:.0f}%)")
        signal.pipeline_log.append(f"❌ שלב 3 [SPREAD/MIN_PRICE]: {msg}")
        return False, msg
    if signal.current_price < MIN_TRADE_PRICE:
        msg = (f"מחיר נוכחי נמוך מדי: {signal.current_price:.3f} < {MIN_TRADE_PRICE:.2f} מינימום "
               f"(סיכון גבוה מאוד)")
        signal.pipeline_log.append(f"❌ שלב 3 [SPREAD/MIN_PRICE]: {msg}")
        return False, msg
    # חישוב פרש
    spread_pct = abs(signal.current_price - signal.expert_price) / signal.expert_price * 100
    signal.slippage_pct = spread_pct
    # בחר סף Spread: קודם כל בדוק מדרגת הגנה דינמית (משלב 2), אחרכך לפי גודל עסקה
    volume_tier_spread = getattr(signal, '_volume_tier', (2.0, MAX_SPREAD_PCT_DEFAULT))[1]
    # עסקאות גדולות (>$50K) מזיזות שוק — סף נפרד ומחמיר יותר
    if signal.expert_trade_usd >= LARGE_TRADE_THRESHOLD:
        max_spread = min(MAX_SPREAD_PCT_LARGE, volume_tier_spread)
        spread_source = f"עסקה גדולה + מדרגת נפח"
    else:
        max_spread = volume_tier_spread
        spread_source = f"מדרגת נפח שוק"
    if spread_pct > max_spread:
        msg = (f"פרש מחיר גבוה: {spread_pct:.1f}% > {max_spread}% מקסימום "
               f"({spread_source} | עסקת מומחה: ${signal.expert_trade_usd:,.0f})")
        signal.pipeline_log.append(f"❌ שלב 3 [SPREAD]: {msg}")
        return False, msg
    signal.pipeline_log.append(
        f"✅ שלב 3 [SPREAD]: פרש {spread_pct:.1f}% תקין "
        f"(מקסימום {max_spread}% לפי {spread_source})"
    )
    return True, ""

# ═══════════════════════════════════════════════════════════════════════════════
# שלב 4: 🚦 EXPERT STOP-LOSS
# מקור: [GEMINI] #3 — חדש לחלוטין
# ═══════════════════════════════════════════════════════════════════════════════
def stage4_expert_stop_loss(signal: TradeSignal) -> tuple:
    """
    מושהה מומחה שנמצא ברצף של 5 הפסדים רצופים.
    גם בודק ROI שלילי >10% ב-30 יום האחרונים.
    תנאי חזרה: 5 זכיות ב-Dry Run.
    """
    data = _load_expert_perf()
    perf = data.get(signal.expert_name, {})
    # בדיקת השהיה קיימת
    if perf.get("suspended"):
        reason = perf.get("suspension_reason", "ביצועים ירודים")
        probation = perf.get("probation_wins", 0)
        msg = f"מומחה מושהה: {reason} | {probation}/5 זכיות לחזרה"
        signal.pipeline_log.append(f"❌ שלב 4 [STOP-LOSS]: {msg}")
        return False, msg
    # בדיקת רצף הפסדים
    try:
        from config import EXPERT_STOP_LOSS_STREAK as _STREAK
    except ImportError:
        _STREAK = 5
    loss_streak = perf.get("loss_streak", 0)
    if loss_streak >= _STREAK:
        # השהה את המומחה
        perf["suspended"] = True
        perf["suspension_reason"] = f"רצף {loss_streak} הפסדים רצופים"
        perf["probation_wins"] = 0
        data[signal.expert_name] = perf
        _save_expert_perf(data)
        msg = f"מומחה הושהה: {loss_streak} הפסדים רצופים"
        signal.pipeline_log.append(f"❌ שלב 4 [STOP-LOSS]: {msg}")
        return False, msg
    # בדיקת ROI שלילי ב-30 יום
    recent_roi = perf.get("recent_30d_roi", [])
    if len(recent_roi) >= 5:
        avg_roi_30d = sum(recent_roi) / len(recent_roi)
        if avg_roi_30d < -10:
            msg = f"ROI שלילי ב-30 יום: {avg_roi_30d:.1f}% — עובר לאישור ידני"
            signal.pipeline_log.append(f"⚠️ שלב 4 [STOP-LOSS]: {msg}")
            return False, msg
    signal.pipeline_log.append(f"✅ שלב 4 [STOP-LOSS]: {signal.expert_name} תקין (רצף הפסדים: {loss_streak})")
    return True, ""

# ═══════════════════════════════════════════════════════════════════════════════
# שלב 5: 🐑 HERD DETECTION
# מקור: [GEMINI] #1 — חדש לחלוטין
# ═══════════════════════════════════════════════════════════════════════════════
def stage5_herd_detection(signal: TradeSignal) -> tuple:
    """
    מזהה "עדר" — כשיותר מדי מומחים נכנסים לאותו שוק.
    3-4 מומחים = קונברגנציה חיובית (הגדל פוזיציה).
    5+ מומחים = עדר — המחיר כבר מוצה, חסום.
    """
    _clean_old_signals()
    # ספור כמה מומחים שונים קנו באותו שוק ב-24 שעות האחרונות
    same_market = [s for s in _recent_signals
                   if s.market_slug == signal.market_slug
                   and s.direction == signal.direction
                   and s.expert_name != signal.expert_name]
    count = len(set(s.expert_name for s in same_market)) + 1  # +1 לכולל הנוכחי
    signal.convergence_count = count
    signal.convergence_names = list(set(s.expert_name for s in same_market))
    if count >= 5:
        msg = (f"🐑 עדר זוהה! {count} מומחים נכנסו לאותו שוק — "
               f"המחיר כבר מוצה. חסום.")
        signal.herd_warning = msg
        signal.pipeline_log.append(f"❌ שלב 5 [HERD]: {msg}")
        return False, msg
    if count >= 3:
        signal.herd_warning = f"🌊 קונברגנציה חיובית: {count} מומחים"
        signal.pipeline_log.append(f"✅ שלב 5 [HERD]: קונברגנציה {count} מומחים — הגדל פוזיציה")
    else:
        signal.pipeline_log.append(f"✅ שלב 5 [HERD]: {count} מומחה/ים — תקין")
    return True, ""

# ═══════════════════════════════════════════════════════════════════════════════
# שלב 6: 🗂️ SECTOR EXPOSURE
# מקור: [GEMINI] #3 — חדש לחלוטין
# ═══════════════════════════════════════════════════════════════════════════════
# מילות מפתח לזיהוי סקטורים
SECTOR_KEYWORDS = {
    "politics":  ["trump", "biden", "election", "president", "congress", "senate", "democrat", "republican", "vote", "poll"],
    "sports":    ["nfl", "nba", "mlb", "soccer", "football", "basketball", "tennis", "golf", "olympic", "championship", "league", "cup"],
    "crypto":    ["bitcoin", "btc", "ethereum", "eth", "crypto", "defi", "nft", "blockchain", "solana", "polygon"],
    "economy":   ["fed", "inflation", "gdp", "recession", "interest rate", "stock", "market", "economy", "dollar", "oil"],
    "geopolitics": ["war", "ukraine", "russia", "china", "israel", "iran", "nato", "military", "conflict", "sanction"],
}
MAX_SECTOR_EXPOSURE = 3  # מקסימום עסקאות פתוחות על אותו סקטור

def _detect_sector(question: str) -> str:
    """מזהה את הסקטור של שוק לפי מילות מפתח."""
    q_lower = question.lower()
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(kw in q_lower for kw in keywords):
            return sector
    return "general"

def stage6_sector_exposure(signal: TradeSignal) -> tuple:
    """
    מונע חשיפה יתרה לסקטור אחד.
    אם כבר יש 3+ עסקאות פתוחות על אותו נושא (פוליטיקה/ספורט/קריפטו) — חסום.
    """
    _clean_old_signals()
    sector = _detect_sector(signal.market_question)
    # ספור עסקאות פתוחות באותו סקטור
    sector_count = sum(1 for s in _recent_signals
                       if _detect_sector(s.market_question) == sector)
    if sector_count >= MAX_SECTOR_EXPOSURE:
        msg = (f"חשיפה סקטוריאלית גבוהה: {sector_count} עסקאות פתוחות "
               f"בסקטור '{sector}' (מקסימום {MAX_SECTOR_EXPOSURE})")
        signal.pipeline_log.append(f"❌ שלב 6 [SECTOR]: {msg}")
        return False, msg
    signal.pipeline_log.append(f"✅ שלב 6 [SECTOR]: סקטור '{sector}' — {sector_count}/{MAX_SECTOR_EXPOSURE} עסקאות")
    return True, ""

# ═══════════════════════════════════════════════════════════════════════════════
# שלב 6ב: 🏆 DOMAIN SPECIALIZATION CHECK
# מקור: [OUR] — ניתוח תחומי מומחיות לפי היסטוריית הפוזיציות
# ═══════════════════════════════════════════════════════════════════════════════
def stage6b_domain_check(signal: TradeSignal) -> tuple:
    """
    בודק אם השוק הנוכחי הוא בתחום המומחיות של המומחה.
    לא חוסם — רק מוסיף מידע לציון ולהתראה.
    """
    try:
        from expert_domain_analyzer import get_expert_domain_profile, classify_market, format_domain_alert_line
        
        wallet = signal.wallet_address
        market_title = signal.market_question
        
        if not wallet:
            signal.pipeline_log.append("📊 שלב 6ב [DOMAIN]: אין כתובת ארנק — דילוג")
            signal._domain_line = ""
            return True, ""
        
        profile = get_expert_domain_profile(wallet)
        current_domain = classify_market(market_title)
        best_domain = profile.get("best_domain")
        best_rate = profile.get("best_domain_win_rate")
        domains = profile.get("domains", {})
        current_stats = domains.get(current_domain, {})
        current_rate = current_stats.get("win_rate")
        current_closed = current_stats.get("wins", 0) + current_stats.get("losses", 0)
        
        # שמור את שורת ההתראה לשימוש בטלגרם
        signal._domain_line = format_domain_alert_line(wallet, market_title)
        signal._current_domain = current_domain
        
        # לוג Pipeline
        if current_rate is not None and current_closed >= 2:
            pct = int(current_rate * 100)
            if current_rate >= 0.70:
                signal.pipeline_log.append(
                    f"✅ שלב 6ב [DOMAIN]: תחום '{current_domain}' — {pct}% הצלחה ({current_closed} עסקאות) — תחום חוזקה!"
                )
            elif current_rate >= 0.50:
                signal.pipeline_log.append(
                    f"🟡 שלב 6ב [DOMAIN]: תחום '{current_domain}' — {pct}% הצלחה ({current_closed} עסקאות) — בינוני"
                )
            else:
                signal.pipeline_log.append(
                    f"⚠️ שלב 6ב [DOMAIN]: תחום '{current_domain}' — {pct}% הצלחה ({current_closed} עסקאות) — תחום חולשה"
                )
        elif current_stats.get("count", 0) > 0:
            signal.pipeline_log.append(
                f"📊 שלב 6ב [DOMAIN]: תחום '{current_domain}' — נתונים חלקיים ({current_stats.get('count', 0)} עסקאות)"
            )
        else:
            signal.pipeline_log.append(
                f"📊 שלב 6ב [DOMAIN]: תחום '{current_domain}' — אין היסטוריה"
            )
        
        if best_domain and best_domain != current_domain and best_rate:
            signal.pipeline_log.append(
                f"🥇 תחום החוזקה: '{best_domain}' ({int(best_rate*100)}%)"
            )
        
        return True, ""
    
    except Exception as e:
        logger.debug(f"שגיאה בשלב 6ב: {e}")
        signal.pipeline_log.append(f"📊 שלב 6ב [DOMAIN]: שגיאה — {e}")
        signal._domain_line = ""
        return True, ""  # לא חוסם בשגיאה


# ═══════════════════════════════════════════════════════════════════════════════
# שלב 7: ⚖️ POSITION SIZING
# מקור: [OUR] + [CLAUDE] שיפורים 3,5 + [GEMINI] #2
# ═══════════════════════════════════════════════════════════════════════════════
def stage7_position_sizing(signal: TradeSignal, base_amount: float, expert_profile: dict) -> float:
    """
    מחשב את גודל הפוזיציה הסופי:
    סכום בסיס × מכפיל ROI × מכפיל סיכון × מכפיל קונברגנציה × מכפיל drift

    מכפיל סיכון [GEMINI/CLAUDE]:
      low    × 1.2
      medium × 1.0
      high   × 0.6 (פשרה בין קלוד 0.7 לג'מיני 0.5)

    מכפיל קונברגנציה [CLAUDE שיפור 5]:
      3 מומחים × 1.5
      4 מומחים × 2.0
      (5+ נחסם בשלב 5)

    מכפיל drift [CLAUDE שיפור 7]:
      אם מומחה השתנה — הקטן ב-30%
    """
    from config import KELLY_RISK_MULTIPLIERS, DEFAULT_TRADE_AMOUNT_USD, MAX_SINGLE_TRADE_PERCENT
    amount = base_amount if base_amount > 0 else DEFAULT_TRADE_AMOUNT_USD
    # מכפיל ROI
    roi = expert_profile.get("roi_pct", 0)
    if roi > 500:
        roi_mult = 1.5
    elif roi > 200:
        roi_mult = 1.3
    elif roi > 100:
        roi_mult = 1.1
    elif roi > 0:
        roi_mult = 1.0
    else:
        roi_mult = 0.7
    # מכפיל סיכון
    risk = expert_profile.get("risk_level", "medium").lower()
    risk_mult = KELLY_RISK_MULTIPLIERS.get(risk, 1.0)
    # HIGH×0.6 (פשרה קלוד 0.7 / ג'מיני 0.5)
    if risk == "high":
        risk_mult = 0.6
    # מכפיל קונברגנציה
    conv_count = signal.convergence_count
    if conv_count >= 4:
        conv_mult = 2.0
    elif conv_count >= 3:
        conv_mult = 1.5
    else:
        conv_mult = 1.0
    # מכפיל drift
    drift_mult = 0.7 if signal.drift_warning else 1.0
    # חישוב סופי
    final = amount * roi_mult * risk_mult * conv_mult * drift_mult
    # הגבלת מקסימום — מ-config.py (לא קבוע)
    try:
        from config import MAX_TRADE_AMOUNT_USD as _max_trade
    except ImportError:
        _max_trade = 50.0
    max_allowed = _max_trade
    final = min(final, max_allowed)
    final = max(final, 5.0)  # מינימום $5
    signal.final_trade_usd = round(final, 2)
    signal.pipeline_log.append(
        f"✅ שלב 7 [SIZING]: ${amount:.0f} × ROI({roi_mult:.1f}) × "
        f"סיכון({risk_mult:.1f}) × קונברגנציה({conv_mult:.1f}) × "
        f"drift({drift_mult:.1f}) = ${final:.2f}"
    )
    return final

# ═══════════════════════════════════════════════════════════════════════════════
# שלב 8: 📡 SIGNALS & ALERTS
# מקור: [CLAUDE] שיפורים 4,7 + [GEMINI] #5 (Slippage tracking)
# ═══════════════════════════════════════════════════════════════════════════════
# מאגר מעקב Slippage ב-DRY RUN
SLIPPAGE_LOG_FILE = os.path.join(os.path.dirname(__file__), "slippage_log.json")

def _log_slippage(signal: TradeSignal):
    """[GEMINI] מתעד את פער הזמן בין מחיר המומחה למחיר הנוכחי."""
    try:
        log = []
        if os.path.exists(SLIPPAGE_LOG_FILE):
            with open(SLIPPAGE_LOG_FILE, "r") as f:
                log = json.load(f)
        log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "expert": signal.expert_name,
            "market": signal.market_question[:60],
            "expert_price": signal.expert_price,
            "current_price": signal.current_price,
            "slippage_pct": signal.slippage_pct,
            "expert_trade_usd": signal.expert_trade_usd,
        })
        # שמור רק 500 האחרונים
        log = log[-500:]
        with open(SLIPPAGE_LOG_FILE, "w") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"שגיאה בתיעוד slippage: {e}")

def get_slippage_stats() -> dict:
    """מחזיר סטטיסטיקת Slippage לדוח DRY RUN."""
    if not os.path.exists(SLIPPAGE_LOG_FILE):
        return {"count": 0, "avg_slippage": 0, "max_slippage": 0}
    try:
        with open(SLIPPAGE_LOG_FILE, "r") as f:
            log = json.load(f)
        if not log:
            return {"count": 0, "avg_slippage": 0, "max_slippage": 0}
        slippages = [e["slippage_pct"] for e in log]
        return {
            "count": len(slippages),
            "avg_slippage": round(sum(slippages) / len(slippages), 2),
            "max_slippage": round(max(slippages), 2),
            "profitable_pct": round(sum(1 for s in slippages if s < 10) / len(slippages) * 100, 1),
        }
    except Exception:
        return {"count": 0, "avg_slippage": 0, "max_slippage": 0}

def stage8_signals_and_alerts(signal: TradeSignal, expert_profile: dict) -> dict:
    """
    בדיקות אחרונות ויצירת מטא-מידע להתראה:
    - Drift Detection [CLAUDE שיפור 7]
    - תיעוד Slippage [GEMINI שיפור 5]
    - חישוב ציון ביטחון כולל
    """
    from market_analysis import check_expert_drift
    # Drift Detection
    drift_result = check_expert_drift(signal.expert_name, expert_profile)
    if drift_result.get("drift_detected"):
        signal.drift_warning = drift_result.get("message", "")
        signal.pipeline_log.append(f"⚠️ שלב 8 [DRIFT]: {signal.drift_warning}")
    else:
        signal.pipeline_log.append(f"✅ שלב 8 [DRIFT]: לא זוהה שינוי התנהגות")
    # תיעוד Slippage
    _log_slippage(signal)
    # ציון ביטחון כולל (0-100)
    confidence = _calculate_confidence_score(signal, expert_profile)
    signal.pipeline_log.append(f"✅ שלב 8 [CONFIDENCE]: ציון {confidence}/100")
    return {
        "drift_warning": signal.drift_warning,
        "slippage_pct": signal.slippage_pct,
        "confidence_score": confidence,
        "convergence_count": signal.convergence_count,
    }

def _calculate_confidence_score(signal: TradeSignal, expert_profile: dict) -> int:
    """מחשב ציון ביטחון כולל (0-100) לעסקה."""
    score = 50  # בסיס
    # Win rate
    win_rate = expert_profile.get("win_rate_pct", 50)
    score += (win_rate - 50) * 0.5
    # ROI
    roi = expert_profile.get("roi_pct", 0)
    if roi > 200: score += 15
    elif roi > 100: score += 10
    elif roi > 0: score += 5
    elif roi < 0: score -= 10
    # קונברגנציה
    if signal.convergence_count >= 3: score += 10
    elif signal.convergence_count >= 2: score += 5
    # פרש מחיר
    if signal.slippage_pct < 5: score += 5
    elif signal.slippage_pct > 15: score -= 10
    # drift
    if signal.drift_warning: score -= 15
    # סיכון
    risk = expert_profile.get("risk_level", "medium")
    if risk == "low": score += 5
    elif risk == "high": score -= 5
    return max(0, min(100, int(score)))

# ═══════════════════════════════════════════════════════════════════════════════
# פונקציה ראשית — הרץ את כל 8 השלבים
# ═══════════════════════════════════════════════════════════════════════════════
def run_pipeline(signal: TradeSignal, current_balance: float = None,
                 base_amount: float = 50.0, expert_profile: dict = None,
                 balance: float = None) -> TradeSignal:
    """
    מריץ את כל 8 שלבי ה-Pipeline על עסקה נתונה.
    מחזיר את ה-TradeSignal עם signal.approved=True/False ופרטי ההחלטה.
    """
    # תמוכה בשם פרמטר 'balance' וגם 'current_balance'
    if balance is not None and current_balance is None:
        current_balance = balance
    if current_balance is None:
        current_balance = 1000.0
    if expert_profile is None:
        expert_profile = {}
    logger.info(f"🔄 Pipeline: {signal.expert_name} | {signal.market_question[:50]}")
    # שלב 1: Drawdown
    ok, msg = stage1_drawdown_guard(signal, current_balance)
    if not ok:
        signal.approved = False
        signal.rejection_reason = f"[שלב 1] {msg}"
        return signal
    # שלב 2: נזילות
    ok, msg = stage2_liquidity_check(signal)
    if not ok:
        signal.approved = False
        signal.rejection_reason = f"[שלב 2] {msg}"
        return signal
    # שלב 2ב: פקיעת שוק מקסימלית (90 יום)
    ok, msg = stage2b_expiry_check(signal)
    if not ok:
        signal.approved = False
        signal.rejection_reason = f"[שלב 2ב] {msg}"
        return signal
    # שלב 2ג: מחיר כניסה מקסימלי (0.75)
    ok, msg = stage2c_entry_price_check(signal)
    if not ok:
        signal.approved = False
        signal.rejection_reason = f"[שלב 2ג] {msg}"
        return signal
    # שלב 3: פרש מחיר
    ok, msg = stage3_spread_filter(signal)
    if not ok:
        signal.approved = False
        signal.rejection_reason = f"[שלב 3] {msg}"
        return signal
    # שלב 4: Stop-Loss מומחה
    ok, msg = stage4_expert_stop_loss(signal)
    if not ok:
        signal.approved = False
        signal.rejection_reason = f"[שלב 4] {msg}"
        return signal
    # שלב 5: זיהוי עדר
    ok, msg = stage5_herd_detection(signal)
    if not ok:
        signal.approved = False
        signal.rejection_reason = f"[שלב 5] {msg}"
        return signal
    # שלב 6: חשיפה סקטוריאלית
    ok, msg = stage6_sector_exposure(signal)
    if not ok:
        signal.approved = False
        signal.rejection_reason = f"[שלב 6] {msg}"
        return signal
    # שלב 6ב: ניתוח תחומי מומחיות (לא חוסם — מוסיף מידע)
    stage6b_domain_check(signal)
    # שלב 7: חישוב גודל פוזיציה
    stage7_position_sizing(signal, base_amount, expert_profile)
    # שלב 8: סיגנלים והתראות
    stage8_signals_and_alerts(signal, expert_profile)
    # ✅ עברה את כל השלבים
    signal.approved = True
    # ✅ תיקון: קבע _timestamp לפני append כדי ש-_clean_old_signals לא יזרוק KeyError
    signal._timestamp = datetime.utcnow()
    _recent_signals.append(signal)
    # שמור רק 200 סיגנלים אחרונים למניעת דליפת זיכרון
    if len(_recent_signals) > 200:
        _recent_signals[:] = _recent_signals[-200:]
    logger.info(f"✅ Pipeline אישר: {signal.expert_name} | ${signal.final_trade_usd:.2f}")
    return signal

# ═══════════════════════════════════════════════════════════════════════════════
# פונקציות עזר לטלגרם
# ═══════════════════════════════════════════════════════════════════════════════
def format_pipeline_summary(signal: TradeSignal, expert_profile: dict = None) -> str:
    """מייצר סיכום Pipeline להצגה בהתראת טלגרם — כולל שורת ציון ברורה."""
    if expert_profile is None:
        expert_profile = {}
    lines = []

    # ─── שורת ציון ברורה (תמיד מוצגת) ────────────────────────────────────────
    confidence = _calculate_confidence_score(signal, expert_profile)
    stages_passed = 8  # הגענו לכאן = עברנו את כל 8 השלבים

    # ציון רמת סיכון
    if confidence >= 80:
        risk_label = "נמוך 🟢"
        score_emoji = "🏆"
    elif confidence >= 65:
        risk_label = "בינוני 🟡"
        score_emoji = "✅"
    elif confidence >= 50:
        risk_label = "מוגבר 🟠"
        score_emoji = "⚠️"
    else:
        risk_label = "גבוה 🔴"
        score_emoji = "⚠️"

    lines.append(
        f"\n{score_emoji} *עברה {stages_passed}/8 בדיקות* | "
        f"ציון: *{confidence}/100* | "
        f"סיכון: *{risk_label}*"
    )

    # ─── מידע נוסף (מוצג רק אם רלוונטי) ─────────────────────────────────────
    if signal.convergence_count >= 3 and not signal.herd_warning.startswith("🐑"):
        lines.append(f"🌊 קונברגנציה: {signal.convergence_count} מומחים מסכימים!")
        if signal.convergence_names:
            lines.append(f"   👥 {', '.join(signal.convergence_names[:3])}")
    if signal.drift_warning:
        lines.append(f"⚠️ {signal.drift_warning}")
    if signal.slippage_pct > 10:
        lines.append(f"⚠️ פרש מחיר: {signal.slippage_pct:.1f}% — כניסה יקרה")
    return "\n".join(lines)

def get_pipeline_status_report() -> str:
    """מייצר דוח סטטוס Pipeline לפקודת /p_pipeline."""
    data = _load_expert_perf()
    suspended = [(name, p) for name, p in data.items() if p.get("suspended")]
    slippage = get_slippage_stats()
    lines = [
        "📊 *סטטוס Pipeline — 8 שלבים*",
        "",
        f"🌊 סיגנלים פעילים (24h): {len(_recent_signals)}",
        f"📉 Slippage ממוצע: {slippage.get('avg_slippage', 0):.1f}%",
        f"📉 Slippage מקסימלי: {slippage.get('max_slippage', 0):.1f}%",
        f"✅ עסקאות עם slippage <10%: {slippage.get('profitable_pct', 0):.0f}%",
        "",
    ]
    if suspended:
        lines.append(f"🚦 מומחים מושהים ({len(suspended)}):")
        for name, p in suspended:
            lines.append(f"  ❌ {name}: {p.get('suspension_reason', '')} | {p.get('probation_wins', 0)}/5 זכיות לחזרה")
    else:
        lines.append("🚦 מומחים מושהים: אין")
    lines += [
        "",
        "שלבים פעילים:",
        "  1️⃣ Drawdown Guard ✅",
        "  2️⃣ Liquidity Check ✅",
        "  3️⃣ Spread Filter ✅",
        "  4️⃣ Expert Stop-Loss ✅",
        "  5️⃣ Herd Detection ✅",
        "  6️⃣ Sector Exposure ✅",
        "  7️⃣ Position Sizing ✅",
        "  8️⃣ Signals & Alerts ✅",
    ]
    return "\n".join(lines)
