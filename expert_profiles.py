"""
Expert & Whale risk profiles — generated from historical trade analysis (March 2026).
Based on analysis of ~50,000 historical transactions across 15 wallets.

Master Report Conclusions (March 2026):
  1. Top whales (Theo4, Fredi9999, zxgngl) focus on MEDIUM risk (0.3–0.6 price range).
  2. Three whales hold 100% win rate: Fredi9999, Len9311238, RepTrump — treat as HOT signals.
  3. GCottrell93 is the #1 expert wallet with $11.8M total wealth and zero high-risk trades.
  4. KeyTransporter: 71% win rate, zero high-risk trades — most reliable expert for automation.
  5. Wallets with negative realized P&L (SwissMiss, weflyhigh, kch123) are still accumulating
     open positions — follow their BUYs only when portfolio value is growing.
  6. Automation priority order: Fredi9999 > Len9311238 > RepTrump > Theo4 > KeyTransporter > GCottrell93
"""

# ─── WHALE WALLETS (Top performers by total wealth) ───────────────────────────
# These are the "super whales" — tracked separately from experts.
# hot_signal = True → send "🔥 המלצה חמה" alert regardless of other filters.
WHALE_PROFILES = {
    "Theo4": {
        "total_wealth_usd": 34_121_129,
        "realized_pnl_usd": 34_121_129,
        "portfolio_value_usd": 0,
        "win_rate_pct": 81.8,
        "roi_pct": 477,
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 10, "MEDIUM": 80, "HIGH": 10},
        "hot_signal": True,
        "hot_reason": "לווייתן #1 בפולימרקט | $34M רווח | 82% הצלחה | ROI 477%",
        "auto_approved": True,
        "tag": "🐋🔥 לווייתן-על #1 | $34M",
        "note": "הלווייתן הגדול ביותר בפולימרקט. כל עסקה שלו היא אות חזק מאוד.",
    },
    "Fredi9999": {
        "total_wealth_usd": 29_207_916,
        "realized_pnl_usd": 29_207_916,
        "portfolio_value_usd": 0,
        "win_rate_pct": 100.0,
        "roi_pct": 792,
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 15, "MEDIUM": 75, "HIGH": 10},
        "hot_signal": True,
        "hot_reason": "100% הצלחה | $29M רווח | ROI 792% — הכי מדויק בפולימרקט",
        "auto_approved": True,
        "tag": "🐋🔥💯 לווייתן-על #2 | 100% הצלחה",
        "note": "100% אחוז הצלחה על שווקים שנסגרו. כל עסקה שלו = המלצה חמה ביותר.",
    },
    "Len9311238": {
        "total_wealth_usd": 10_408_280,
        "realized_pnl_usd": 10_408_280,
        "portfolio_value_usd": 0,
        "win_rate_pct": 100.0,
        "roi_pct": 178,
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 60, "MEDIUM": 35, "HIGH": 5},
        "hot_signal": True,
        "hot_reason": "100% הצלחה | $10.4M רווח | מתמחה בסיכון נמוך",
        "auto_approved": True,
        "tag": "🐋🔥💯 לווייתן-על #3 | 100% הצלחה",
        "note": "100% אחוז הצלחה. מתמחה בסיכון נמוך — עסקאות בטוחות יותר.",
    },
    "zxgngl": {
        "total_wealth_usd": 21_787_707,
        "realized_pnl_usd": 21_787_707,
        "portfolio_value_usd": 0,
        "win_rate_pct": 42.9,
        "roi_pct": 284,
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 10, "MEDIUM": 70, "HIGH": 20},
        "hot_signal": False,
        "hot_reason": "",
        "auto_approved": True,
        "tag": "🐋 לווייתן-על #4 | $21.8M",
        "note": "עושר עצום אך אחוז הצלחה נמוך (43%) — לא מומלץ לעקוב עיוור.",
    },
    "RepTrump": {
        "total_wealth_usd": 9_902_085,
        "realized_pnl_usd": 9_902_085,
        "portfolio_value_usd": 0,
        "win_rate_pct": 100.0,
        "roi_pct": 243,
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 55, "MEDIUM": 40, "HIGH": 5},
        "hot_signal": True,
        "hot_reason": "100% הצלחה | $9.9M רווח | מתמחה בסיכון נמוך-בינוני",
        "auto_approved": True,
        "tag": "🐋🔥💯 לווייתן-על #5 | 100% הצלחה",
        "note": "100% אחוז הצלחה. מתמחה בסיכון נמוך-בינוני.",
    },
}

# ─── EXPERT WALLETS (Tracked for copy-trading) ────────────────────────────────
EXPERT_PROFILES = {
    "kch123": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 44.0, "MEDIUM": 34.0, "HIGH": 22.0},
        "avg_price": 0.65,
        "avg_size_usd": 8000,
        "size_tier": "WHALE",
        "high_risk_pct": 22.0,
        "total_wealth_usd": 511_157,
        "win_rate_pct": 43.4,
        "roi_pct": -55,
        "hot_signal": False,
        "tag": "סיכון נמוך-בינוני",
        "auto_approved": True,
        "note": "פרופיל מאוזן, 22% עסקאות גבוה-סיכון — בדוק מחיר. ROI שלילי.",
    },
    "DrPufferfish": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 4.3, "MEDIUM": 76.4, "HIGH": 19.2},
        "avg_price": 0.40,
        "avg_size_usd": 45894,
        "size_tier": "WHALE",
        "high_risk_pct": 19.2,
        "total_wealth_usd": 1_132_615,
        "win_rate_pct": 15.6,
        "roi_pct": 12,
        "hot_signal": False,
        "tag": "לווייתן | סיכון בינוני-גבוה",
        "auto_approved": False,
        "note": "לווייתן חזק אבל 19% עסקאות גבוה-סיכון ו-16% הצלחה בלבד — לסנן.",
    },
    "KeyTransporter": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 40.9, "MEDIUM": 59.1, "HIGH": 0.0},
        "avg_price": 0.57,
        "avg_size_usd": 78825,
        "size_tier": "WHALE",
        "high_risk_pct": 0.0,
        "total_wealth_usd": 5_709_663,
        "win_rate_pct": 71.4,
        "roi_pct": 1140,
        "hot_signal": False,
        "tag": "🐋 לווייתן מקצועי | אפס סיכון גבוה | 71% הצלחה",
        "auto_approved": True,
        "note": "אפס עסקאות גבוה-סיכון, 71% הצלחה, ROI 1140% — הכי מקצועי ברשימה.",
    },
    "RN1": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 45.0, "MEDIUM": 33.0, "HIGH": 22.0},
        "avg_price": 0.67,
        "avg_size_usd": 293,
        "size_tier": "SMALL",
        "high_risk_pct": 22.0,
        "total_wealth_usd": None,
        "win_rate_pct": None,
        "roi_pct": None,
        "hot_signal": False,
        "tag": "סיכון נמוך | עסקאות גדולות = אות חזק",
        "auto_approved": True,
        "note": "עסקאות קטנות בממוצע — כשמשקיע סכום גדול זה אות חזק במיוחד.",
    },
    "GCottrell93": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 55.4, "MEDIUM": 44.6, "HIGH": 0.0},
        "avg_price": 0.64,
        "avg_size_usd": 76113,
        "size_tier": "WHALE",
        "high_risk_pct": 0.0,
        "total_wealth_usd": 11_801_395,
        "win_rate_pct": 33.3,
        "roi_pct": 1553,
        "hot_signal": False,
        "tag": "🐋 לווייתן | מומחה #1 | $11.8M | ROI 1553%",
        "auto_approved": True,
        "note": "המומחה הרווחי ביותר עם $11.8M. אפס עסקאות גבוה-סיכון.",
    },
    "swisstony": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 32.6, "MEDIUM": 45.0, "HIGH": 22.4},
        "avg_price": 0.54,
        "avg_size_usd": 154,
        "size_tier": "SMALL",
        "high_risk_pct": 22.4,
        "total_wealth_usd": None,
        "win_rate_pct": None,
        "roi_pct": None,
        "hot_signal": False,
        "tag": "סיכון בינוני",
        "auto_approved": True,
        "note": "פרופיל בינוני-מאוזן, עסקאות קטנות.",
    },
    "gmanas": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 44.1, "MEDIUM": 43.5, "HIGH": 12.4},
        "avg_price": 0.59,
        "avg_size_usd": 26232,
        "size_tier": "WHALE",
        "high_risk_pct": 12.4,
        "total_wealth_usd": None,
        "win_rate_pct": None,
        "roi_pct": None,
        "hot_signal": False,
        "tag": "לווייתן | סיכון נמוך-בינוני",
        "auto_approved": True,
        "note": "לווייתן מאוזן, 12% גבוה-סיכון — סביר.",
    },
    "GamblingIsAllYouNeed": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 14.0, "MEDIUM": 63.0, "HIGH": 23.0},
        "avg_price": 0.48,
        "avg_size_usd": 600,
        "size_tier": "MEDIUM",
        "high_risk_pct": 23.0,
        "total_wealth_usd": 3_237_942,
        "win_rate_pct": 0.0,
        "roi_pct": -8,
        "hot_signal": False,
        "tag": "מתמחה סיכון בינוני | תיק פתוח $3.5M",
        "auto_approved": True,
        "note": "תיק פתוח ענק ($3.5M) אך 0% הצלחה בשווקים שנסגרו — עדיין בהצטברות.",
    },
    "blackwall": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 8.6, "MEDIUM": 91.4, "HIGH": 0.0},
        "avg_price": 0.55,
        "avg_size_usd": 103416,
        "size_tier": "WHALE",
        "high_risk_pct": 0.0,
        "total_wealth_usd": 2_309_157,
        "win_rate_pct": 62.5,
        "roi_pct": 219,
        "hot_signal": False,
        "tag": "🐋 לווייתן מתמחה | סיכון בינוני טהור | 62% הצלחה",
        "auto_approved": True,
        "note": "91% עסקאות בינוניות, אפס גבוה-סיכון, 62% הצלחה — אות חזק מאוד.",
    },
    "beachboy4": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 18.1, "MEDIUM": 80.9, "HIGH": 1.0},
        "avg_price": 0.55,
        "avg_size_usd": 239349,
        "size_tier": "WHALE",
        "high_risk_pct": 1.0,
        "total_wealth_usd": 3_965_776,
        "win_rate_pct": 66.0,
        "roi_pct": 18,
        "hot_signal": False,
        "tag": "🐋 לווייתן ענק | $239K ממוצע | 66% הצלחה",
        "auto_approved": True,
        "note": "המשקיע הגדול ביותר — $239K ממוצע, 81% בינוני, 66% הצלחה.",
    },
    "anoin123": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 78.5, "MEDIUM": 15.9, "HIGH": 5.5},
        "avg_price": 0.78,
        "avg_size_usd": 3201,
        "size_tier": "LARGE",
        "high_risk_pct": 5.5,
        "total_wealth_usd": None,
        "win_rate_pct": None,
        "roi_pct": None,
        "hot_signal": False,
        "tag": "מומחה שמרן | סיכון נמוך",
        "auto_approved": True,
        "note": "79% עסקאות נמוך-סיכון — שמרני ועקבי.",
    },
    "weflyhigh": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 9.6, "MEDIUM": 84.5, "HIGH": 5.8},
        "avg_price": 0.50,
        "avg_size_usd": 31456,
        "size_tier": "WHALE",
        "high_risk_pct": 5.8,
        "total_wealth_usd": 358_328,
        "win_rate_pct": 33.3,
        "roi_pct": -41,
        "hot_signal": False,
        "tag": "לווייתן | מתמחה סיכון בינוני | תיק פתוח $1.26M",
        "auto_approved": True,
        "note": "85% עסקאות בינוניות. ROI שלילי אך תיק פתוח גדול — עדיין בהצטברות.",
    },
    "gmpm": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 13.3, "MEDIUM": 83.7, "HIGH": 3.0},
        "avg_price": 0.52,
        "avg_size_usd": 25735,
        "size_tier": "WHALE",
        "high_risk_pct": 3.0,
        "total_wealth_usd": None,
        "win_rate_pct": None,
        "roi_pct": None,
        "hot_signal": False,
        "tag": "לווייתן | מתמחה סיכון בינוני",
        "auto_approved": True,
        "note": "84% עסקאות בינוניות, לווייתן — מומלץ מאוד.",
    },
    "YatSen": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 57.1, "MEDIUM": 23.0, "HIGH": 19.9},
        "avg_price": 0.65,
        "avg_size_usd": 50125,
        "size_tier": "WHALE",
        "high_risk_pct": 19.9,
        "total_wealth_usd": 75_395,
        "win_rate_pct": 31.3,
        "roi_pct": -9,
        "hot_signal": False,
        "tag": "לווייתן | פרופיל מעורב | ROI שלילי",
        "auto_approved": False,
        "note": "לווייתן חזק אבל 20% עסקאות גבוה-סיכון ו-31% הצלחה — לסנן.",
    },
    "SwissMiss": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 76.6, "MEDIUM": 21.6, "HIGH": 1.8},
        "avg_price": 0.81,
        "avg_size_usd": 20057,
        "size_tier": "WHALE",
        "high_risk_pct": 1.8,
        "total_wealth_usd": 22_692,
        "win_rate_pct": 34.5,
        "roi_pct": -99,
        "hot_signal": False,
        "tag": "לווייתן שמרן | סיכון נמוך | תיק פתוח $1.88M",
        "auto_approved": True,
        "note": "77% עסקאות נמוך-סיכון. ROI -99% אך תיק פתוח $1.88M — עדיין בהצטברות.",
    },
}

# ─── Automation priority order (from master report, March 2026) ───────────────
# Use this order when deciding which wallet signals to prioritize in auto-trading.
AUTOMATION_PRIORITY = [
    "Fredi9999",      # 100% win rate, $29M, ROI 792%
    "Len9311238",     # 100% win rate, $10.4M, low-risk specialist
    "RepTrump",       # 100% win rate, $9.9M, low-medium risk
    "Theo4",          # 82% win rate, $34.1M, ROI 477%
    "KeyTransporter", # 71% win rate, $5.7M, zero high-risk
    "GCottrell93",    # Best expert: $11.8M, ROI 1553%
    "blackwall",      # 62% win rate, pure medium-risk
    "beachboy4",      # 66% win rate, largest avg trade size
]

# ─── Vetting criteria for new experts ────────────────────────────────────────
NEW_EXPERT_VETTING = {
    "min_trades": 50,
    "max_high_risk_pct": 15.0,
    "min_avg_size_usd": 500,
    "active_days_window": 90,
    "trial_period_days": 30,
    # New: minimum win rate required for auto-approval
    "min_win_rate_pct": 55.0,
    # New: minimum total wealth to be considered a serious player
    "min_total_wealth_usd": 50_000,
}

# ─── Helper functions ─────────────────────────────────────────────────────────

def get_wallet_profile(wallet_name: str) -> dict | None:
    """Return profile dict for either a whale or expert wallet."""
    return WHALE_PROFILES.get(wallet_name) or EXPERT_PROFILES.get(wallet_name)


def is_hot_signal(wallet_name: str) -> tuple[bool, str]:
    """
    Returns (True, reason_string) if this wallet triggers a HOT BUY recommendation.
    Hot signals are reserved for wallets with 100% win rate or exceptional track record.
    """
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
    wr_str = f" | {win_rate:.0f}% הצלחה" if win_rate is not None else ""
    return f"🏷️ {tag}{wr_str}"


def get_expert_warning(wallet_name: str, trade_price: float) -> str:
    """Get a warning message if the trade is outside the expert's typical profile."""
    profile = get_wallet_profile(wallet_name)
    if not profile:
        return ""

    trade_risk = "HIGH" if trade_price < 0.25 else "MEDIUM" if trade_price < 0.65 else "LOW"
    dominant = profile.get("dominant_risk", "MEDIUM")

    if trade_risk == "HIGH" and dominant != "HIGH":
        return f"⚠️ עסקה זו ({trade_price:.2f}) חריגה לפרופיל הרגיל של {wallet_name}"
    if trade_risk == "HIGH" and profile.get("high_risk_pct", 0) < 10:
        return f"⚠️ עסקת סיכון גבוה — נדיר עבור {wallet_name}"
    return ""


def is_auto_approved(wallet_name: str) -> bool:
    """Check if wallet is approved for automatic trading."""
    profile = get_wallet_profile(wallet_name)
    return profile.get("auto_approved", False) if profile else False


def get_hot_alert_header(wallet_name: str) -> str:
    """
    Returns a prominent Hebrew hot-alert header for 100%-win-rate wallets.
    Used at the top of trade alert messages.
    """
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
