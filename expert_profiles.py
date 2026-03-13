"""
expert_profiles.py — פרופילי סיכון של מומחים ולווייתנים
נוצר מניתוח היסטורי של עסקאות אמיתיות מ-Polymarket API (מרץ 2026).

סיווג רמות סיכון לפי מחיר כניסה:
  LOW    = מחיר > 0.60  (סבירות גבוהה, סיכון נמוך)
  MEDIUM = מחיר 0.30–0.60 (סבירות בינונית)
  HIGH   = מחיר < 0.30  (סבירות נמוכה, סיכון גבוה)

המלצות:
  STRONG_BUY   = Win ≥ 85% + ROI > 100%
  BUY          = Win ≥ 70% + ROI > 30%
  CAUTIOUS_BUY = Win ≥ 60% + ROI > 0%
  NEUTRAL      = Win ≥ 50%
  AVOID        = Win < 50%

Master Report Conclusions (מרץ 2026):
  1. שלושה לווייתנים עם 100% הצלחה: Fredi9999, Len9311238, RepTrump — HOT SIGNAL תמיד.
  2. Theo4 הוא הלווייתן הגדול ביותר ($34M) עם 82% הצלחה — BUY חזק.
  3. GCottrell93 הוא המומחה הרווחי ביותר (ROI 1553%) — אפס עסקאות גבוה-סיכון.
  4. KeyTransporter: 71% הצלחה, אפס סיכון גבוה — הכי אמין לאוטומציה.
  5. GamblingIsAllYouNeed: 62% הצלחה, 23% עסקאות גבוה-סיכון — להיזהר.
  6. kch123 ו-anoin123: ROI שלילי — להימנע.
  7. סדר עדיפות לאוטומציה: Fredi9999 > Len9311238 > RepTrump > Theo4 > KeyTransporter > GCottrell93
"""

# ─── WHALE WALLETS (Top performers by total wealth) ───────────────────────────
WHALE_PROFILES = {
    "Theo4": {
        "total_wealth_usd": 34_121_129,
        "realized_pnl_usd": 34_121_129,
        "win_rate_pct": 82.0,
        "roi_pct": 477,
        "total_trades": 180,
        "dominant_risk": "HIGH",          # מתמחה בעסקאות HIGH (מחיר נמוך) — אבל מנצח!
        "risk_distribution": {"LOW": 10, "MEDIUM": 30, "HIGH": 60},
        "high_risk_pct": 60.0,
        "avg_size_usd": 189_000,
        "size_tier": "WHALE",
        "hot_signal": True,
        "hot_reason": "לווייתן #1 בפולימרקט | $34M רווח | 82% הצלחה | ROI 477%",
        "auto_approved": True,
        "recommendation": "BUY",
        "tag": "🐋🔥 לווייתן-על #1 | $34M | 82% הצלחה",
        "note": "הלווייתן הגדול ביותר בפולימרקט. מתמחה בעסקאות HIGH-risk אך מנצח 82% מהזמן.",
    },
    "Fredi9999": {
        "total_wealth_usd": 29_207_916,
        "realized_pnl_usd": 29_207_916,
        "win_rate_pct": 100.0,
        "roi_pct": 792,
        "total_trades": 45,
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 15, "MEDIUM": 75, "HIGH": 10},
        "high_risk_pct": 10.0,
        "avg_size_usd": 648_000,
        "size_tier": "WHALE",
        "hot_signal": True,
        "hot_reason": "100% הצלחה | $29M רווח | ROI 792% — הכי מדויק בפולימרקט",
        "auto_approved": True,
        "recommendation": "STRONG_BUY",
        "tag": "🐋🔥💯 לווייתן-על #2 | 100% הצלחה | ROI 792%",
        "note": "100% אחוז הצלחה על שווקים שנסגרו. כל עסקה שלו = המלצה חמה ביותר.",
    },
    "Len9311238": {
        "total_wealth_usd": 10_408_280,
        "realized_pnl_usd": 10_408_280,
        "win_rate_pct": 100.0,
        "roi_pct": 245,
        "total_trades": 12,
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 40, "MEDIUM": 55, "HIGH": 5},
        "high_risk_pct": 5.0,
        "avg_size_usd": 867_000,
        "size_tier": "WHALE",
        "hot_signal": True,
        "hot_reason": "100% הצלחה | $10.4M רווח | ROI 245%",
        "auto_approved": True,
        "recommendation": "STRONG_BUY",
        "tag": "🐋🔥💯 לווייתן-על #3 | 100% הצלחה | ROI 245%",
        "note": "100% אחוז הצלחה. מתמחה בסיכון נמוך-בינוני — עסקאות בטוחות יותר.",
    },
    "zxgngl": {
        "total_wealth_usd": 21_787_707,
        "realized_pnl_usd": 21_787_707,
        "win_rate_pct": 80.0,
        "roi_pct": 156,
        "total_trades": 95,
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 10, "MEDIUM": 70, "HIGH": 20},
        "high_risk_pct": 20.0,
        "avg_size_usd": 229_000,
        "size_tier": "WHALE",
        "hot_signal": False,
        "hot_reason": "",
        "auto_approved": True,
        "recommendation": "BUY",
        "tag": "🐋 לווייתן-על #4 | $21.8M | 80% הצלחה",
        "note": "עושר עצום ו-80% הצלחה — אות חזק. 20% עסקאות גבוה-סיכון — לשים לב.",
    },
    "RepTrump": {
        "total_wealth_usd": 9_902_085,
        "realized_pnl_usd": 9_902_085,
        "win_rate_pct": 100.0,
        "roi_pct": 312,
        "total_trades": 8,
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 55, "MEDIUM": 40, "HIGH": 5},
        "high_risk_pct": 5.0,
        "avg_size_usd": 1_237_000,
        "size_tier": "WHALE",
        "hot_signal": True,
        "hot_reason": "100% הצלחה | $9.9M רווח | ROI 312%",
        "auto_approved": True,
        "recommendation": "STRONG_BUY",
        "tag": "🐋🔥💯 לווייתן-על #5 | 100% הצלחה | ROI 312%",
        "note": "100% אחוז הצלחה. מתמחה בסיכון נמוך-בינוני.",
    },
}

# ─── EXPERT WALLETS (Tracked for copy-trading) ────────────────────────────────
EXPERT_PROFILES = {
    "GCottrell93": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 55, "MEDIUM": 45, "HIGH": 0},
        "avg_price": 0.64,
        "avg_size_usd": 76_113,
        "size_tier": "WHALE",
        "high_risk_pct": 0.0,
        "total_wealth_usd": 11_801_395,
        "win_rate_pct": 75.0,
        "roi_pct": 1553,
        "total_trades": 320,
        "hot_signal": False,
        "auto_approved": True,
        "recommendation": "BUY",
        "tag": "🐋 מומחה #1 | $11.8M | ROI 1553% | אפס סיכון גבוה",
        "note": "המומחה הרווחי ביותר עם $11.8M. אפס עסקאות גבוה-סיכון. 75% הצלחה.",
    },
    "KeyTransporter": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 41, "MEDIUM": 59, "HIGH": 0},
        "avg_price": 0.57,
        "avg_size_usd": 78_825,
        "size_tier": "WHALE",
        "high_risk_pct": 0.0,
        "total_wealth_usd": 5_709_663,
        "win_rate_pct": 71.0,
        "roi_pct": 89,
        "total_trades": 210,
        "hot_signal": False,
        "auto_approved": True,
        "recommendation": "BUY",
        "tag": "🐋 מומחה | אפס סיכון גבוה | 71% הצלחה | ROI 89%",
        "note": "אפס עסקאות גבוה-סיכון, 71% הצלחה — הכי אמין לאוטומציה.",
    },
    "RN1": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 45, "MEDIUM": 33, "HIGH": 22},
        "avg_price": 0.67,
        "avg_size_usd": 293,
        "size_tier": "SMALL",
        "high_risk_pct": 22.0,
        "total_wealth_usd": 95_000,
        "win_rate_pct": 68.0,
        "roi_pct": 45,
        "total_trades": 180,
        "hot_signal": False,
        "auto_approved": True,
        "recommendation": "CAUTIOUS_BUY",
        "tag": "מומחה | 68% הצלחה | סיכון נמוך | עסקאות קטנות",
        "note": "68% הצלחה. עסקאות קטנות בממוצע — כשמשקיע סכום גדול זה אות חזק במיוחד.",
    },
    "swisstony": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 33, "MEDIUM": 45, "HIGH": 22},
        "avg_price": 0.54,
        "avg_size_usd": 154,
        "size_tier": "SMALL",
        "high_risk_pct": 22.0,
        "total_wealth_usd": 45_000,
        "win_rate_pct": 66.0,
        "roi_pct": 38,
        "total_trades": 150,
        "hot_signal": False,
        "auto_approved": True,
        "recommendation": "CAUTIOUS_BUY",
        "tag": "מומחה | 66% הצלחה | סיכון בינוני",
        "note": "66% הצלחה, פרופיל בינוני-מאוזן. 22% עסקאות גבוה-סיכון — לשים לב.",
    },
    "YatSen": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 57, "MEDIUM": 23, "HIGH": 20},
        "avg_price": 0.65,
        "avg_size_usd": 50_125,
        "size_tier": "WHALE",
        "high_risk_pct": 20.0,
        "total_wealth_usd": 75_395,
        "win_rate_pct": 63.0,
        "roi_pct": 35,
        "total_trades": 95,
        "hot_signal": False,
        "auto_approved": True,
        "recommendation": "CAUTIOUS_BUY",
        "tag": "לווייתן | 63% הצלחה | סיכון נמוך בעיקר",
        "note": "63% הצלחה. 20% עסקאות גבוה-סיכון — לסנן עסקאות HIGH.",
    },
    "GamblingIsAllYouNeed": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 14, "MEDIUM": 63, "HIGH": 23},
        "avg_price": 0.48,
        "avg_size_usd": 600,
        "size_tier": "MEDIUM",
        "high_risk_pct": 23.0,
        "total_wealth_usd": 3_237_942,
        "win_rate_pct": 62.0,
        "roi_pct": 28,
        "total_trades": 280,
        "hot_signal": False,
        "auto_approved": True,
        "recommendation": "CAUTIOUS_BUY",
        "tag": "מומחה | 62% הצלחה | סיכון בינוני | 23% גבוה-סיכון",
        "note": "62% הצלחה. 23% עסקאות גבוה-סיכון — להיזהר בעסקאות מחיר נמוך.",
    },
    "beachboy4": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 18, "MEDIUM": 81, "HIGH": 1},
        "avg_price": 0.55,
        "avg_size_usd": 239_349,
        "size_tier": "WHALE",
        "high_risk_pct": 1.0,
        "total_wealth_usd": 3_965_776,
        "win_rate_pct": 60.0,
        "roi_pct": 22,
        "total_trades": 140,
        "hot_signal": False,
        "auto_approved": True,
        "recommendation": "CAUTIOUS_BUY",
        "tag": "🐋 לווייתן ענק | $239K ממוצע | 60% הצלחה | אפס סיכון גבוה",
        "note": "המשקיע הגדול ביותר — $239K ממוצע, 81% בינוני, 60% הצלחה.",
    },
    "SwissMiss": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 77, "MEDIUM": 22, "HIGH": 2},
        "avg_price": 0.81,
        "avg_size_usd": 20_057,
        "size_tier": "WHALE",
        "high_risk_pct": 1.8,
        "total_wealth_usd": 22_692,
        "win_rate_pct": 59.0,
        "roi_pct": 20,
        "total_trades": 88,
        "hot_signal": False,
        "auto_approved": True,
        "recommendation": "NEUTRAL",
        "tag": "לווייתן שמרן | 59% הצלחה | סיכון נמוך | ROI 20%",
        "note": "77% עסקאות נמוך-סיכון. 59% הצלחה — שמרני ועקבי.",
    },
    "DrPufferfish": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 4, "MEDIUM": 76, "HIGH": 19},
        "avg_price": 0.40,
        "avg_size_usd": 45_894,
        "size_tier": "WHALE",
        "high_risk_pct": 19.2,
        "total_wealth_usd": 1_132_615,
        "win_rate_pct": 58.0,
        "roi_pct": 15,
        "total_trades": 809,
        "hot_signal": False,
        "auto_approved": False,
        "recommendation": "NEUTRAL",
        "tag": "🐋 לווייתן | 58% הצלחה | סיכון בינוני-גבוה | 19% HIGH",
        "note": "לווייתן חזק אבל 19% עסקאות גבוה-סיכון — לסנן. 58% הצלחה.",
    },
    "gmpm": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 13, "MEDIUM": 84, "HIGH": 3},
        "avg_price": 0.52,
        "avg_size_usd": 25_735,
        "size_tier": "WHALE",
        "high_risk_pct": 3.0,
        "total_wealth_usd": 15_000,
        "win_rate_pct": 57.0,
        "roi_pct": 18,
        "total_trades": 130,
        "hot_signal": False,
        "auto_approved": True,
        "recommendation": "NEUTRAL",
        "tag": "לווייתן | 57% הצלחה | מתמחה סיכון בינוני | 3% HIGH",
        "note": "84% עסקאות בינוניות, לווייתן — מומלץ מאוד.",
    },
    "gmanas": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 44, "MEDIUM": 44, "HIGH": 12},
        "avg_price": 0.59,
        "avg_size_usd": 26_232,
        "size_tier": "WHALE",
        "high_risk_pct": 12.4,
        "total_wealth_usd": 12_000,
        "win_rate_pct": 55.0,
        "roi_pct": 12,
        "total_trades": 120,
        "hot_signal": False,
        "auto_approved": True,
        "recommendation": "NEUTRAL",
        "tag": "לווייתן | 55% הצלחה | סיכון נמוך-בינוני",
        "note": "לווייתן מאוזן, 12% גבוה-סיכון — סביר. 55% הצלחה.",
    },
    "weflyhigh": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 10, "MEDIUM": 85, "HIGH": 6},
        "avg_price": 0.50,
        "avg_size_usd": 31_456,
        "size_tier": "WHALE",
        "high_risk_pct": 5.8,
        "total_wealth_usd": 358_328,
        "win_rate_pct": 54.0,
        "roi_pct": 10,
        "total_trades": 110,
        "hot_signal": False,
        "auto_approved": True,
        "recommendation": "NEUTRAL",
        "tag": "לווייתן | 54% הצלחה | מתמחה סיכון בינוני",
        "note": "85% עסקאות בינוניות. 54% הצלחה — ניטרלי.",
    },
    "blackwall": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 9, "MEDIUM": 91, "HIGH": 0},
        "avg_price": 0.55,
        "avg_size_usd": 103_416,
        "size_tier": "WHALE",
        "high_risk_pct": 0.0,
        "total_wealth_usd": 2_309_157,
        "win_rate_pct": 52.0,
        "roi_pct": 8,
        "total_trades": 95,
        "hot_signal": False,
        "auto_approved": True,
        "recommendation": "NEUTRAL",
        "tag": "🐋 לווייתן | 52% הצלחה | סיכון בינוני טהור | אפס HIGH",
        "note": "91% עסקאות בינוניות, אפס גבוה-סיכון — אות חזק כשמשקיע.",
    },
    "anoin123": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 79, "MEDIUM": 16, "HIGH": 6},
        "avg_price": 0.78,
        "avg_size_usd": 3_201,
        "size_tier": "LARGE",
        "high_risk_pct": 5.5,
        "total_wealth_usd": None,
        "win_rate_pct": 48.0,
        "roi_pct": -5,
        "total_trades": 75,
        "hot_signal": False,
        "auto_approved": False,
        "recommendation": "AVOID",
        "tag": "⚠️ מומחה שמרן | 48% הצלחה | ROI שלילי | להימנע",
        "note": "79% עסקאות נמוך-סיכון אך 48% הצלחה ו-ROI שלילי — לא מומלץ.",
    },
    "kch123": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 44, "MEDIUM": 34, "HIGH": 22},
        "avg_price": 0.65,
        "avg_size_usd": 8_000,
        "size_tier": "WHALE",
        "high_risk_pct": 22.0,
        "total_wealth_usd": 511_157,
        "win_rate_pct": 34.0,
        "roi_pct": -45,
        "total_trades": 71,
        "hot_signal": False,
        "auto_approved": False,
        "recommendation": "AVOID",
        "tag": "❌ 34% הצלחה | ROI -45% | להימנע",
        "note": "ROI שלילי (-45%) ו-34% הצלחה בלבד — לא מומלץ לעקוב.",
    },
}

# ─── Automation priority order (from master report, March 2026) ───────────────
AUTOMATION_PRIORITY = [
    "Fredi9999",      # 100% win rate, $29M, ROI 792%
    "Len9311238",     # 100% win rate, $10.4M, ROI 245%
    "RepTrump",       # 100% win rate, $9.9M, ROI 312%
    "Theo4",          # 82% win rate, $34.1M, ROI 477%
    "zxgngl",         # 80% win rate, $21.8M, ROI 156%
    "GCottrell93",    # Best expert: $11.8M, ROI 1553%
    "KeyTransporter", # 71% win rate, $5.7M, zero high-risk
    "beachboy4",      # 60% win rate, largest avg trade size
]

# ─── Vetting criteria for new experts ────────────────────────────────────────
NEW_EXPERT_VETTING = {
    "min_trades": 50,
    "max_high_risk_pct": 15.0,
    "min_avg_size_usd": 500,
    "active_days_window": 90,
    "trial_period_days": 30,
    "min_win_rate_pct": 55.0,
    "min_total_wealth_usd": 50_000,
}

# ─── Helper functions ─────────────────────────────────────────────────────────

def get_wallet_profile(wallet_name: str) -> dict | None:
    """Return profile dict for either a whale or expert wallet."""
    return WHALE_PROFILES.get(wallet_name) or EXPERT_PROFILES.get(wallet_name)


def is_hot_signal(wallet_name: str) -> tuple[bool, str]:
    """Returns (True, reason_string) if this wallet triggers a HOT BUY recommendation."""
    profile = get_wallet_profile(wallet_name)
    if not profile:
        return False, ""
    if profile.get("hot_signal"):
        return True, profile.get("hot_reason", "")
    return False, ""


def get_expert_tag(wallet_name: str) -> str:
    """Get the risk profile tag for display in trade alerts."""
    profile = get_wallet_profile(wallet_name)
    if not profile:
        return "⚪ מומחה חדש | בבדיקה"

    tag = profile.get("tag", "")
    win_rate = profile.get("win_rate_pct")
    roi = profile.get("roi_pct")
    wr_str = f" | {win_rate:.0f}% הצלחה" if win_rate is not None else ""
    roi_str = f" | ROI {roi:+.0f}%" if roi is not None else ""

    # סיווג סיכון לתצוגה
    risk = profile.get("dominant_risk", "MEDIUM")
    risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(risk, "⚪")
    risk_label = {"LOW": "סיכון נמוך", "MEDIUM": "סיכון בינוני", "HIGH": "סיכון גבוה"}.get(risk, "")

    return f"🏷️ {tag}\n{risk_emoji} {risk_label}{wr_str}{roi_str}"


def get_invest_recommendation(wallet_name: str) -> str:
    """Get investment recommendation for display in trade alerts."""
    profile = get_wallet_profile(wallet_name)
    if not profile:
        return "⚪ מומחה חדש — אין המלצה עדיין"

    rec = profile.get("recommendation", "NEUTRAL")
    win_rate = profile.get("win_rate_pct", 0) or 0
    roi = profile.get("roi_pct", 0) or 0

    rec_map = {
        "STRONG_BUY":   f"🟢🟢 המלצה חזקה מאוד לקנייה! ({win_rate:.0f}% הצלחה | ROI {roi:+.0f}%)",
        "BUY":          f"🟢 מומלץ להשקיע ({win_rate:.0f}% הצלחה | ROI {roi:+.0f}%)",
        "CAUTIOUS_BUY": f"🟡 השקע בזהירות ({win_rate:.0f}% הצלחה | ROI {roi:+.0f}%)",
        "NEUTRAL":      f"⚪ ניטרלי — שקול בקפידה ({win_rate:.0f}% הצלחה | ROI {roi:+.0f}%)",
        "AVOID":        f"🔴 לא מומלץ להשקיע ({win_rate:.0f}% הצלחה | ROI {roi:+.0f}%)",
    }
    return rec_map.get(rec, f"⚪ ניטרלי ({win_rate:.0f}% הצלחה)")


def get_expert_warning(wallet_name: str, trade_price: float) -> str:
    """Get a warning message if the trade is outside the expert's typical profile."""
    profile = get_wallet_profile(wallet_name)
    if not profile:
        return ""

    trade_risk = "HIGH" if trade_price < 0.25 else "MEDIUM" if trade_price < 0.65 else "LOW"
    dominant = profile.get("dominant_risk", "MEDIUM")
    high_risk_pct = profile.get("high_risk_pct", 0)

    if trade_risk == "HIGH" and dominant == "LOW":
        return f"⚠️ עסקת סיכון גבוה — חריגה מאוד לפרופיל {wallet_name} (בד\"כ LOW)"
    if trade_risk == "HIGH" and high_risk_pct < 10:
        return f"⚠️ עסקת סיכון גבוה — נדיר עבור {wallet_name} (רק {high_risk_pct:.0f}% מהעסקאות)"
    if trade_risk == "HIGH" and dominant != "HIGH":
        return f"⚠️ עסקה זו ({trade_price:.2f}) חריגה לפרופיל הרגיל של {wallet_name}"
    return ""


def is_auto_approved(wallet_name: str) -> bool:
    """Check if wallet is approved for automatic trading."""
    profile = get_wallet_profile(wallet_name)
    return profile.get("auto_approved", False) if profile else False


def get_hot_alert_header(wallet_name: str) -> str:
    """Returns a prominent Hebrew hot-alert header for 100%-win-rate wallets."""
    hot, reason = is_hot_signal(wallet_name)
    if not hot:
        return ""
    return (
        f"\n🔥🔥🔥 *המלצה חמה ביותר!* 🔥🔥🔥\n"
        f"_{reason}_\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )


def get_automation_priority_rank(wallet_name: str) -> int:
    """Returns 1-based priority rank for automation (lower = higher priority). 99 = not ranked."""
    try:
        return AUTOMATION_PRIORITY.index(wallet_name) + 1
    except ValueError:
        return 99
