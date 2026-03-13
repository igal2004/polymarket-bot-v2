"""
Expert risk profiles — generated from historical trade analysis (March 2026).
Based on analysis of ~6,500 historical trades across 15 expert wallets.
"""

# Risk profile for each expert based on historical trade analysis
# dominant_risk: LOW (>0.65), MEDIUM (0.25-0.65), HIGH (<0.25)
# size_tier: WHALE (avg > $10K), LARGE ($1K-$10K), MEDIUM ($100-$1K), SMALL (<$100)
# auto_approved: True = safe for full automation, False = manual confirmation recommended

EXPERT_PROFILES = {
    "kch123": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 44.0, "MEDIUM": 34.0, "HIGH": 22.0},
        "avg_price": 0.65,
        "avg_size_usd": 8000,
        "size_tier": "WHALE",
        "high_risk_pct": 22.0,
        "tag": "סיכון נמוך-בינוני",
        "auto_approved": True,
        "note": "פרופיל מאוזן, 22% עסקאות גבוה-סיכון — בדוק מחיר",
    },
    "DrPufferfish": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 4.3, "MEDIUM": 76.4, "HIGH": 19.2},
        "avg_price": 0.40,
        "avg_size_usd": 45894,
        "size_tier": "WHALE",
        "high_risk_pct": 19.2,
        "tag": "לווייתן | סיכון בינוני-גבוה",
        "auto_approved": False,
        "note": "לווייתן חזק אבל 19% עסקאות גבוה-סיכון — מומלץ לסנן מחיר < 0.25",
    },
    "KeyTransporter": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 40.9, "MEDIUM": 59.1, "HIGH": 0.0},
        "avg_price": 0.57,
        "avg_size_usd": 78825,
        "size_tier": "WHALE",
        "high_risk_pct": 0.0,
        "tag": "לווייתן מקצועי | אפס סיכון גבוה",
        "auto_approved": True,
        "note": "אפס עסקאות גבוה-סיכון — הכי מקצועי ברשימה",
    },
    "RN1": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 45.0, "MEDIUM": 33.0, "HIGH": 22.0},
        "avg_price": 0.67,
        "avg_size_usd": 293,
        "size_tier": "SMALL",
        "high_risk_pct": 22.0,
        "tag": "סיכון נמוך | עסקאות גדולות = אות חזק",
        "auto_approved": True,
        "note": "עסקאות קטנות בממוצע — כשמשקיע סכום גדול זה אות חזק במיוחד",
    },
    "GCottrell93": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 55.4, "MEDIUM": 44.6, "HIGH": 0.0},
        "avg_price": 0.64,
        "avg_size_usd": 76113,
        "size_tier": "WHALE",
        "high_risk_pct": 0.0,
        "tag": "לווייתן | סיכון נמוך-בינוני",
        "auto_approved": True,
        "note": "אפס עסקאות גבוה-סיכון, לווייתן — מומלץ מאוד",
    },
    "swisstony": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 32.6, "MEDIUM": 45.0, "HIGH": 22.4},
        "avg_price": 0.54,
        "avg_size_usd": 154,
        "size_tier": "SMALL",
        "high_risk_pct": 22.4,
        "tag": "סיכון בינוני",
        "auto_approved": True,
        "note": "פרופיל בינוני-מאוזן, עסקאות קטנות",
    },
    "gmanas": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 44.1, "MEDIUM": 43.5, "HIGH": 12.4},
        "avg_price": 0.59,
        "avg_size_usd": 26232,
        "size_tier": "WHALE",
        "high_risk_pct": 12.4,
        "tag": "לווייתן | סיכון נמוך-בינוני",
        "auto_approved": True,
        "note": "לווייתן מאוזן, 12% גבוה-סיכון — סביר",
    },
    "GamblingIsAllYouNeed": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 14.0, "MEDIUM": 63.0, "HIGH": 23.0},
        "avg_price": 0.48,
        "avg_size_usd": 600,
        "size_tier": "MEDIUM",
        "high_risk_pct": 23.0,
        "tag": "מתמחה סיכון בינוני",
        "auto_approved": True,
        "note": "63% עסקאות בינוניות — הכי עקבי בפרופיל בינוני",
    },
    "blackwall": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 8.6, "MEDIUM": 91.4, "HIGH": 0.0},
        "avg_price": 0.55,
        "avg_size_usd": 103416,
        "size_tier": "WHALE",
        "high_risk_pct": 0.0,
        "tag": "לווייתן מתמחה | סיכון בינוני טהור",
        "auto_approved": True,
        "note": "91% עסקאות בינוניות, אפס גבוה-סיכון — אות חזק מאוד",
    },
    "beachboy4": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 18.1, "MEDIUM": 80.9, "HIGH": 1.0},
        "avg_price": 0.55,
        "avg_size_usd": 239349,
        "size_tier": "WHALE",
        "high_risk_pct": 1.0,
        "tag": "לווייתן ענק | אות חזק מאוד",
        "auto_approved": True,
        "note": "המשקיע הגדול ביותר — $239K ממוצע, 81% בינוני, 1% גבוה-סיכון",
    },
    "anoin123": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 78.5, "MEDIUM": 15.9, "HIGH": 5.5},
        "avg_price": 0.78,
        "avg_size_usd": 3201,
        "size_tier": "LARGE",
        "high_risk_pct": 5.5,
        "tag": "מומחה שמרן | סיכון נמוך",
        "auto_approved": True,
        "note": "79% עסקאות נמוך-סיכון — שמרני ועקבי",
    },
    "weflyhigh": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 9.6, "MEDIUM": 84.5, "HIGH": 5.8},
        "avg_price": 0.50,
        "avg_size_usd": 31456,
        "size_tier": "WHALE",
        "high_risk_pct": 5.8,
        "tag": "לווייתן | מתמחה סיכון בינוני",
        "auto_approved": True,
        "note": "85% עסקאות בינוניות, לווייתן — מומלץ מאוד",
    },
    "gmpm": {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {"LOW": 13.3, "MEDIUM": 83.7, "HIGH": 3.0},
        "avg_price": 0.52,
        "avg_size_usd": 25735,
        "size_tier": "WHALE",
        "high_risk_pct": 3.0,
        "tag": "לווייתן | מתמחה סיכון בינוני",
        "auto_approved": True,
        "note": "84% עסקאות בינוניות, לווייתן — מומלץ מאוד",
    },
    "YatSen": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 57.1, "MEDIUM": 23.0, "HIGH": 19.9},
        "avg_price": 0.65,
        "avg_size_usd": 50125,
        "size_tier": "WHALE",
        "high_risk_pct": 19.9,
        "tag": "לווייתן | פרופיל מעורב",
        "auto_approved": False,
        "note": "לווייתן חזק אבל 20% עסקאות גבוה-סיכון — מומלץ לסנן",
    },
    "SwissMiss": {
        "dominant_risk": "LOW",
        "risk_distribution": {"LOW": 76.6, "MEDIUM": 21.6, "HIGH": 1.8},
        "avg_price": 0.81,
        "avg_size_usd": 20057,
        "size_tier": "WHALE",
        "high_risk_pct": 1.8,
        "tag": "לווייתן שמרן | סיכון נמוך מאוד",
        "auto_approved": True,
        "note": "77% עסקאות נמוך-סיכון, לווייתן — הכי בטוח ברשימה",
    },
}

# Vetting criteria for new experts
NEW_EXPERT_VETTING = {
    "min_trades": 50,               # Minimum historical trades
    "max_high_risk_pct": 15.0,      # Max % of high-risk trades (price < 0.25)
    "min_avg_size_usd": 500,        # Minimum average trade size
    "active_days_window": 90,       # Must have traded in last 90 days
    "trial_period_days": 30,        # Days as "trial" before full approval
}

def get_expert_tag(expert_name: str) -> str:
    """Get the risk profile tag for display in trade alerts."""
    profile = EXPERT_PROFILES.get(expert_name)
    if not profile:
        return "מומחה חדש | בבדיקה"
    
    risk = profile["dominant_risk"]
    tag = profile["tag"]
    size = profile["avg_size_usd"]
    
    risk_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(risk, "⚪")
    whale_icon = "🐋" if size >= 10000 else ""
    
    return f"{risk_icon}{whale_icon} {tag}"

def get_expert_warning(expert_name: str, trade_price: float) -> str:
    """Get a warning message if the trade is outside the expert's typical profile."""
    profile = EXPERT_PROFILES.get(expert_name)
    if not profile:
        return ""
    
    trade_risk = "HIGH" if trade_price < 0.25 else "MEDIUM" if trade_price < 0.65 else "LOW"
    dominant = profile["dominant_risk"]
    
    if trade_risk == "HIGH" and dominant != "HIGH":
        return f"⚠️ עסקה זו ({trade_price:.2f}) חריגה לפרופיל הרגיל של {expert_name}"
    elif trade_risk == "HIGH" and profile["high_risk_pct"] < 10:
        return f"⚠️ עסקת סיכון גבוה — נדיר עבור {expert_name}"
    return ""

def is_auto_approved(expert_name: str) -> bool:
    """Check if expert is approved for automatic trading."""
    profile = EXPERT_PROFILES.get(expert_name)
    return profile.get("auto_approved", False) if profile else False
