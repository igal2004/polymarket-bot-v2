"""
market_analysis.py — ניתוח שוק, פערי מחיר, ניתוח AI, וגילוי מומחים חדשים
כולל שיפורים 1-4 ו-7 לפי ניתוח קלוד:
  1. פרש מחיר דינמי לפי גודל עסקה (10% לעסקות >$50K, 20% לשאר)
  2. בדיקת נזילות מינימלית ($5,000)
  3. Kelly Criterion + פרופיל סיכון (low×1.2, medium×1.0, high×0.7)
  4. עצירה אוטומטית על Drawdown מקסימלי (30%)
  7. Drift Detection — זיהוי שינוי התנהגות מומחים (30 יום vs. היסטוריה)
"""
import logging
import requests
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


# ─── שיפור 4: מעקב Drawdown ──────────────────────────────────────────────────
_peak_balance    = None
_trading_halted  = False

def update_peak_balance(current_balance: float):
    """מעדכן את יתרת השיא לחישוב Drawdown."""
    global _peak_balance
    if _peak_balance is None or current_balance > _peak_balance:
        _peak_balance = current_balance

def check_drawdown_halt(current_balance: float) -> tuple:
    """
    בודק האם הפורטפוליו ירד מעל MAX_DRAWDOWN_PERCENT מהשיא.
    מחזיר (halt: bool, message: str).
    """
    global _trading_halted
    from config import MAX_DRAWDOWN_PERCENT
    if _peak_balance is None or _peak_balance == 0:
        return False, ""
    drawdown_pct = ((_peak_balance - current_balance) / _peak_balance) * 100
    if drawdown_pct >= MAX_DRAWDOWN_PERCENT:
        _trading_halted = True
        msg = (
            f"🛑 מסחר הופסק אוטומטית!\n"
            f"Drawdown: {drawdown_pct:.1f}% (מקסימום: {MAX_DRAWDOWN_PERCENT}%)\n"
            f"יתרת שיא: ${_peak_balance:.2f} | יתרה נוכחית: ${current_balance:.2f}\n"
            f"שלח /p_resume_trading להמשך לאחר בחינה"
        )
        return True, msg
    _trading_halted = False
    return False, ""

def is_trading_halted() -> bool:
    return _trading_halted

def resume_trading(new_peak: float = None):
    """מאפס את מצב ה-Drawdown Guard. אם new_peak סופק — מאפס גם את יתרת השיא."""
    global _trading_halted, _peak_balance
    _trading_halted = False
    if new_peak is not None:
        _peak_balance = new_peak


# ─── מחיר שוק נוכחי ──────────────────────────────────────────────────────────
def get_current_market_price(asset_id: str) -> float | None:
    """שולף את המחיר הנוכחי של שוק מה-API של Polymarket."""
    if not asset_id:
        return None
    try:
        r = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={"clob_token_ids": asset_id},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                m = data[0]
                for field in ["lastTradePrice", "bestAsk", "bestBid", "price"]:
                    val = m.get(field)
                    if val is not None:
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            continue
    except Exception as e:
        logger.warning(f"שגיאה בשליפת מחיר שוק: {e}")
    return None


# ─── שיפור 2: בדיקת נזילות שוק ──────────────────────────────────────────────
def get_market_volume(asset_id: str) -> float | None:
    """שולף את נפח המסחר הכולל של שוק מה-API."""
    if not asset_id:
        return None
    try:
        r = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={"clob_token_ids": asset_id},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                m = data[0]
                for field in ["volume", "volumeNum", "liquidity"]:
                    val = m.get(field)
                    if val is not None:
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            continue
    except Exception as e:
        logger.warning(f"שגיאה בשליפת נפח שוק: {e}")
    return None

def check_market_liquidity(asset_id: str) -> tuple:
    """
    בודק האם לשוק יש נזילות מספקת.
    מחזיר (ok: bool, message: str, volume: float).
    """
    from config import MIN_MARKET_VOLUME_USD
    volume = get_market_volume(asset_id)
    if volume is None:
        return True, "⚠️ לא ניתן לאמת נזילות", 0
    if volume < MIN_MARKET_VOLUME_USD:
        return False, f"🚫 נזילות נמוכה: ${volume:,.0f} (מינימום: ${MIN_MARKET_VOLUME_USD:,})", volume
    return True, f"✅ נזילות תקינה: ${volume:,.0f}", volume


# ─── שיפור 1: ניתוח פרש מחיר דינמי ─────────────────────────────────────────
def analyze_price_gap(expert_price: float, current_price: float, outcome: str,
                      expert_trade_usd: float = 0) -> dict:
    """
    מנתח את הפרש המחיר בין מחיר קניית המומחה למחיר הנוכחי.
    שיפור 1: פרש מחיר מחמיר יותר לעסקאות גדולות (>$50K).
    """
    from config import MAX_SPREAD_PCT_DEFAULT, MAX_SPREAD_PCT_LARGE, LARGE_TRADE_THRESHOLD

    if current_price is None or expert_price <= 0:
        return {"gap": None, "analysis": None, "favorable": None, "blocked": False}

    gap     = current_price - expert_price
    gap_pct = (gap / expert_price) * 100 if expert_price > 0 else 0

    # שיפור 1: בחר סף לפי גודל עסקת המומחה
    is_large_trade = expert_trade_usd >= LARGE_TRADE_THRESHOLD
    max_spread     = MAX_SPREAD_PCT_LARGE if is_large_trade else MAX_SPREAD_PCT_DEFAULT
    spread_label   = f" (עסקה גדולה >{LARGE_TRADE_THRESHOLD/1000:.0f}K — סף מחמיר)" if is_large_trade else ""

    # בדיקת חסימה
    blocked      = False
    block_reason = ""
    if outcome.upper() == "YES" and gap_pct > max_spread:
        blocked      = True
        block_reason = f"🚫 חסום: מחיר גבוה ב-{gap_pct:.1f}% ממחיר המומחה (מקסימום: {max_spread}%){spread_label}"
    elif outcome.upper() == "NO" and gap_pct < -max_spread:
        blocked      = True
        block_reason = f"🚫 חסום: מחיר גבוה ב-{abs(gap_pct):.1f}% ממחיר המומחה (מקסימום: {max_spread}%){spread_label}"

    if outcome.upper() == "YES":
        if gap < -0.03:
            favorable = True
            analysis  = (f"✅ מחיר ירד {abs(gap_pct):.1f}% מאז קניית המומחה — כניסה טובה יותר ממנו!"
                         if gap_pct < -10 else
                         f"✅ מחיר נמוך ב-{abs(gap_pct):.1f}% ממחיר המומחה — הזדמנות טובה")
        elif gap > 0.05:
            favorable = False
            analysis  = (f"⚠️ מחיר עלה {gap_pct:.1f}% מאז קניית המומחה — כניסה יקרה יותר"
                         if gap_pct > 15 else
                         f"⚠️ מחיר גבוה ב-{gap_pct:.1f}% ממחיר המומחה — שים לב")
        else:
            favorable = True
            analysis  = f"✅ מחיר דומה למחיר המומחה (פרש {gap_pct:+.1f}%)"
    else:
        if gap > 0.03:
            favorable = True
            analysis  = f"✅ מחיר YES עלה — NO זול יותר ב-{gap_pct:.1f}% ממחיר המומחה"
        elif gap < -0.05:
            favorable = False
            analysis  = f"⚠️ מחיר YES ירד — NO יקר יותר ב-{abs(gap_pct):.1f}% ממחיר המומחה"
        else:
            favorable = True
            analysis  = f"✅ מחיר דומה למחיר המומחה (פרש {gap_pct:+.1f}%)"

    if blocked:
        analysis  = block_reason
        favorable = False

    return {
        "gap":            round(gap, 4),
        "gap_pct":        round(gap_pct, 1),
        "current_price":  current_price,
        "analysis":       analysis,
        "favorable":      favorable,
        "blocked":        blocked,
        "block_reason":   block_reason,
        "max_spread_used": max_spread,
        "is_large_trade": is_large_trade,
    }


# ─── ניתוח AI ────────────────────────────────────────────────────────────────
def get_ai_risk_analysis(market_question: str, outcome: str, price: float,
                         expert_name: str, usd_value: float) -> str:
    """מבקש מ-GPT ניתוח סיכון קצר לעסקה."""
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        prompt = (
            f"ניתוח סיכון קצר לעסקת Polymarket:\n"
            f"שוק: {market_question}\n"
            f"כיוון: {outcome}\n"
            f"מחיר: {price:.3f} ({price*100:.1f}%)\n"
            f"מומחה: {expert_name} | סכום: ${usd_value:.0f}\n\n"
            f"תן ניתוח סיכון קצר ב-2 שורות בעברית:\n"
            f"שורה 1: הערכת הסיכון (נמוך/בינוני/גבוה) ולמה\n"
            f"שורה 2: המלצה קצרה (כן/לא/זהירות)\n"
            f"ענה בפורמט: 🔍 [סיכון]: ... | 💡 [המלצה]: ..."
        )
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"שגיאה בניתוח AI: {e}")
        return None


# ─── שיפור 3: Kelly + פרופיל סיכון ──────────────────────────────────────────
def get_expert_roi_from_journal(expert_name: str) -> float | None:
    """מחזיר ROI ממוצע של מומחה מהיומן."""
    try:
        from dry_run_journal import get_summary
        s = get_summary()
        by_expert = s.get("by_expert", {})
        if expert_name in by_expert:
            return by_expert[expert_name].get("avg_roi", None)
    except Exception:
        pass
    return None


def calculate_dynamic_trade_amount(expert_name: str, base_amount: float,
                                   balance: float | None) -> tuple:
    """
    שיפור 3: מחשב סכום עסקה דינמי לפי ROI היסטורי + פרופיל סיכון המומחה.
    מחזיר (amount, explanation).
    """
    from config import KELLY_RISK_MULTIPLIERS
    try:
        from expert_profiles import get_expert_profile
        profile   = get_expert_profile(expert_name)
        risk_tier = profile.get("risk_tier", "medium") if profile else "medium"
    except Exception:
        risk_tier = "medium"

    roi = get_expert_roi_from_journal(expert_name)

    # מכפיל ROI
    if roi is None:
        roi_multiplier = 1.0
        roi_label      = "סכום בסיס (אין היסטוריה)"
    elif roi > 50:
        roi_multiplier = 1.5
        roi_label      = f"ROI {roi:.0f}% — מצוין ↑"
    elif roi > 20:
        roi_multiplier = 1.2
        roi_label      = f"ROI {roi:.0f}% — טוב ↑"
    elif roi > 0:
        roi_multiplier = 1.0
        roi_label      = f"ROI {roi:.0f}% — ממוצע"
    elif roi > -20:
        roi_multiplier = 0.7
        roi_label      = f"ROI {roi:.0f}% — חלש ↓"
    else:
        roi_multiplier = 0.5
        roi_label      = f"ROI {roi:.0f}% — גרוע ↓↓"

    # מכפיל סיכון (שיפור 3)
    risk_multiplier = KELLY_RISK_MULTIPLIERS.get(risk_tier, 1.0)
    risk_labels     = {"low": "סיכון נמוך ↑", "medium": "סיכון בינוני", "high": "סיכון גבוה ↓"}
    risk_label      = risk_labels.get(risk_tier, "")

    combined = roi_multiplier * risk_multiplier
    amount   = base_amount * combined

    if balance:
        amount = min(amount, balance * 0.10)

    label = f"{roi_label} | {risk_label} (×{combined:.2f})"
    return round(amount, 2), label


# ─── שיפור 7: Drift Detection ─────────────────────────────────────────────────
def detect_expert_drift(expert_name: str, wallet_address: str) -> dict | None:
    """
    מזהה שינוי משמעותי בהתנהגות מומחה בין 30 הימים האחרונים לכל ההיסטוריה.
    מחזיר dict עם פרטי ה-drift, או None אם אין שינוי משמעותי.
    """
    from config import DRIFT_DETECTION_DAYS, DRIFT_ALERT_THRESHOLD
    try:
        from expert_profiles import get_expert_profile
        profile              = get_expert_profile(expert_name)
        historical_win_rate  = profile.get("win_rate", 0) if profile else 0
    except Exception:
        historical_win_rate  = 0

    try:
        r = requests.get(
            "https://data-api.polymarket.com/activity",
            params={"user": wallet_address, "limit": 50},
            timeout=15
        )
        if r.status_code != 200:
            return None
        raw    = r.json()
        trades = raw if isinstance(raw, list) else raw.get("data", [])

        cutoff        = datetime.utcnow() - timedelta(days=DRIFT_DETECTION_DAYS)
        recent_trades = []
        for t in trades:
            ts = t.get("timestamp", t.get("createdAt", 0))
            if isinstance(ts, (int, float)) and ts > cutoff.timestamp():
                recent_trades.append(t)
            elif isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if dt.replace(tzinfo=None) > cutoff:
                        recent_trades.append(t)
                except Exception:
                    pass

        if len(recent_trades) < 5:
            return None

        wins             = sum(1 for t in recent_trades if float(t.get("size", 0) or 0) > 0)
        recent_win_rate  = (wins / len(recent_trades)) * 100
        drift            = recent_win_rate - historical_win_rate

        if abs(drift) >= DRIFT_ALERT_THRESHOLD:
            direction = "שיפור 📈" if drift > 0 else "הידרדרות 📉"
            return {
                "expert":               expert_name,
                "historical_win_rate":  historical_win_rate,
                "recent_win_rate":      round(recent_win_rate, 1),
                "drift":                round(drift, 1),
                "direction":            direction,
                "recent_trades_count":  len(recent_trades),
                "alert": (
                    f"⚠️ Drift זוהה: {expert_name}\n"
                    f"היסטוריה: {historical_win_rate:.0f}% → 30 יום אחרון: {recent_win_rate:.1f}%\n"
                    f"שינוי: {drift:+.1f}% ({direction})"
                )
            }
    except Exception as e:
        logger.warning(f"שגיאה ב-Drift Detection עבור {expert_name}: {e}")

    return None


# ─── גילוי מומחים חדשים ──────────────────────────────────────────────────────
def discover_top_traders(min_volume_usd: float = 50000, limit: int = 50) -> list:
    """
    סורק את הסוחרים הפעילים ביותר בפולימרקט ב-30 הימים האחרונים.
    מחזיר רשימה של מועמדים חדשים שלא נמצאים כבר ברשימת המעקב.
    """
    from config import EXPERT_WALLETS, WHALE_WALLETS
    known_wallets = set(w.lower() for w in {**EXPERT_WALLETS, **WHALE_WALLETS}.values())
    candidates    = []
    try:
        r = requests.get(
            "https://data-api.polymarket.com/activity/leaderboard",
            params={"window": "1m", "limit": limit},
            timeout=15
        )
        if r.status_code == 200:
            data    = r.json()
            entries = data if isinstance(data, list) else data.get("data", [])
            for entry in entries:
                wallet = entry.get("proxyWallet") or entry.get("wallet") or entry.get("address", "")
                if not wallet or wallet.lower() in known_wallets:
                    continue
                pnl      = float(entry.get("pnl",      entry.get("profit",   0)) or 0)
                volume   = float(entry.get("volume",   entry.get("amount",   0)) or 0)
                win_rate = float(entry.get("winRate",  entry.get("win_rate", 0)) or 0)
                if pnl > 5000 and win_rate > 60:
                    candidates.append({
                        "wallet":   wallet,
                        "pnl":      pnl,
                        "volume":   volume,
                        "win_rate": win_rate,
                        "name":     entry.get("name", wallet[:8]),
                    })
    except Exception as e:
        logger.warning(f"שגיאה בגילוי סוחרים: {e}")
    candidates.sort(key=lambda x: x["pnl"], reverse=True)
    return candidates[:10]


def get_open_trades_summary() -> list:
    """מחזיר רשימת עסקאות פתוחות עם מועד פקיעה."""
    try:
        from dry_run_journal import get_summary
        s          = get_summary()
        trades     = s.get("trades", [])
        open_trades = [t for t in trades if t.get("status") == "open"]
        return open_trades
    except Exception:
        return []

# ─── [GEMINI] Drift check מהיר לפי פרופיל קיים (ללא API call) ─────────────────
def check_expert_drift(expert_name: str, expert_profile: dict) -> dict:
    """
    [GEMINI שלב 8] בדיקת drift מהירה לפי פרופיל מומחה קיים (ללא API call).
    משמשת את trade_pipeline.py בשלב 8.
    מחזיר dict עם drift_detected: bool ו-message: str.
    """
    win_rate = expert_profile.get("win_rate_pct", expert_profile.get("win_rate", 50))
    roi      = expert_profile.get("roi_pct",      expert_profile.get("roi",      0))
    if win_rate < 40 and roi < -20:
        return {
            "drift_detected": True,
            "message": f"⚠️ Drift: {expert_name} — win_rate {win_rate}% + ROI {roi}%"
        }
    return {"drift_detected": False, "message": ""}


# ─── [GEMINI] סינון חציון (median filter) ────────────────────────────────────
def median_filter_experts(expert_signals: list) -> dict:
    """
    [GEMINI] מחשב חציון (לא ממוצע) של מחירי כניסה ו-confidence מרשימת איתותי מומחים.
    expert_signals: רשימת dict עם שדות 'price', 'confidence', 'expert_name'.
    מחזיר dict עם median_price, median_confidence, filtered_count.
    """
    if not expert_signals:
        return {"median_price": None, "median_confidence": None, "filtered_count": 0}

    prices      = sorted([s.get("price", 0)      for s in expert_signals if s.get("price")])
    confidences = sorted([s.get("confidence", 50) for s in expert_signals if s.get("confidence")])

    def _median(lst):
        n = len(lst)
        if n == 0:
            return None
        mid = n // 2
        return lst[mid] if n % 2 == 1 else (lst[mid - 1] + lst[mid]) / 2

    return {
        "median_price":      _median(prices),
        "median_confidence": _median(confidences),
        "filtered_count":    len(expert_signals),
    }
