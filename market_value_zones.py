"""
market_value_zones.py — מנוע Value Zone משולב
שכבה 1: מגמות שוק כלליות (כל שווקי Polymarket)
שכבה 2: ביצועי המומחים והלווייתנים שלנו

ניקוד משולב: שכבה 2 מקבלת משקל גבוה יותר כשיש מספיק נתונים.
"""

import json
import os
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# ─── נתיבי קבצי JSON ──────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GLOBAL_ZONES_PATH  = os.path.join(_BASE_DIR, "value_zones_global.json")
EXPERT_ZONES_PATH  = os.path.join(_BASE_DIR, "value_zones_experts.json")

# ─── מילות מפתח לסיווג תחומים ────────────────────────────────────────────────
DOMAIN_KEYWORDS = {
    "ספורט": [
        "nba", "nfl", "mlb", "nhl", "soccer", "football", "basketball", "baseball",
        "tennis", "golf", "ufc", "mma", "boxing", "cricket", "rugby", "olympics",
        "world cup", "champions league", "premier league", "la liga", "serie a",
        "bundesliga", "super bowl", "playoffs", "championship", "tournament",
        "match", "game", "season", "win", "score", "player", "team", "league",
        "cup", "bowl", "series", "race", "f1", "formula", "nascar", "esports",
        "fifa", "uefa", "ncaa", "march madness", "wimbledon", "us open",
        "boilermakers", "purdue", "college",
    ],
    "פוליטיקה": [
        "president", "election", "vote", "senate", "congress", "democrat",
        "republican", "biden", "trump", "harris", "governor", "mayor", "primary",
        "ballot", "poll", "approval", "impeach", "cabinet", "secretary", "minister",
        "parliament", "legislation", "bill", "law", "supreme court", "justice",
        "nomination", "candidate", "campaign", "inauguration", "resign", "veto",
        "vance", "macron", "starmer",
    ],
    "גיאופוליטיקה": [
        "war", "ukraine", "russia", "china", "taiwan", "nato", "united nations",
        "sanctions", "ceasefire", "invasion", "military", "troops", "nuclear",
        "missile", "treaty", "diplomacy", "israel", "gaza", "iran", "north korea",
        "conflict", "peace", "attack", "offensive", "territory", "border",
        "zelensky", "putin", "xi ",
    ],
    "קריפטו": [
        "bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain", "defi",
        "nft", "solana", "sol", "binance", "coinbase", "altcoin",
        "stablecoin", "usdc", "usdt", "doge", "dogecoin", "ripple", "xrp",
        "polygon", "matic", "avalanche", "avax", "cardano", "ada", "web3",
        "token", "dao", "yield", "staking", "halving", "100k", "200k", "50k",
    ],
    "כלכלה": [
        "fed", "federal reserve", "interest rate", "inflation", "gdp", "recession",
        "unemployment", "stock", "s&p", "nasdaq", "dow", "market cap", "ipo",
        "earnings", "revenue", "profit", "debt ceiling", "budget", "tariff",
        "trade war", "oil price", "gold price", "dollar", "euro", "yen",
        "cpi", "pce", "fomc", "rate hike", "rate cut", "bond", "yield curve",
        "powell", "treasury",
    ],
    "טכנולוגיה": [
        "artificial intelligence", "openai", "gpt", "chatgpt", "google",
        "apple", "microsoft", "meta", "amazon", "tesla", "spacex", "elon musk",
        "sam altman", "nvidia", "chip", "semiconductor", "launch", "release",
        "product", "app", "software", "hardware", "robot", "autonomous",
    ],
    "בידור": [
        "oscar", "emmy", "grammy", "golden globe", "movie", "film", "tv show",
        "series", "album", "song", "artist", "celebrity", "award", "box office",
        "streaming", "netflix", "disney", "spotify", "concert", "tour",
        "taylor swift",
    ],
}

# ─── טעינת נתונים ─────────────────────────────────────────────────────────────

_global_data = None
_expert_data = None

def _load_global():
    global _global_data
    if _global_data is None:
        try:
            with open(GLOBAL_ZONES_PATH, encoding="utf-8") as f:
                _global_data = json.load(f)
        except Exception as e:
            logger.warning(f"לא ניתן לטעון value_zones_global.json: {e}")
            _global_data = {}
    return _global_data

def _load_expert():
    global _expert_data
    if _expert_data is None:
        try:
            with open(EXPERT_ZONES_PATH, encoding="utf-8") as f:
                _expert_data = json.load(f)
        except Exception as e:
            logger.warning(f"לא ניתן לטעון value_zones_experts.json: {e}")
            _expert_data = {}
    return _expert_data

# ─── סיווג תחום ───────────────────────────────────────────────────────────────

def classify_domain(title: str) -> str:
    """מסווג שוק לתחום לפי מילות מפתח."""
    if not title:
        return "אחר"
    t = title.lower()
    scores = defaultdict(int)
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in t:
                scores[domain] += 1
    if scores:
        return max(scores, key=scores.get)
    return "אחר"

def get_price_bin(price: float) -> str:
    """מחזיר קטגוריית מחיר."""
    if price < 0.20:
        return "0.00-0.20"
    elif price < 0.35:
        return "0.20-0.35"
    elif price < 0.50:
        return "0.35-0.50"
    elif price < 0.65:
        return "0.50-0.65"
    elif price <= 0.75:
        return "0.65-0.75"
    else:
        return "0.75+"

# ─── ניתוח Value Zone ─────────────────────────────────────────────────────────

def get_value_zone_analysis(market_title: str, entry_price: float) -> dict:
    """
    מחזיר ניתוח Value Zone משולב עבור שוק ומחיר כניסה נתונים.
    
    מחזיר:
    {
        "domain": "ספורט",
        "price_bin": "0.35-0.50",
        "layer1": {
            "yes_win_rate": 35.1,
            "total_markets": 208,
            "reliable": True,
        },
        "layer2": {
            "win_rate": 89.1,
            "wins": 1033,
            "total": 1159,
            "reliable": True,
        },
        "combined_score": 78.2,   # ממוצע משוקלל
        "recommendation": "חזק",  # חזק / בינוני / חלש / לא מספיק נתונים
        "confidence": "גבוהה",    # גבוהה / בינונית / נמוכה
    }
    """
    domain = classify_domain(market_title)
    price_bin = get_price_bin(entry_price)

    global_data = _load_global()
    expert_data = _load_expert()

    # שכבה 1: מגמות שוק כלליות
    layer1 = None
    if global_data:
        domain_rates = global_data.get("domain_win_rates", {})
        if domain in domain_rates:
            layer1 = domain_rates[domain]
        elif "אחר" in domain_rates:
            layer1 = domain_rates["אחר"]

    # שכבה 2: ביצועי המומחים שלנו
    layer2 = None
    layer2_by_price = None
    if expert_data:
        aggregated = expert_data.get("aggregated", {})
        domain_summary = aggregated.get("domain_summary", {})
        value_zones = aggregated.get("value_zones_by_domain_price", {})

        # ניסיון 1: חיפוש לפי תחום + מחיר
        if domain in value_zones and price_bin in value_zones[domain]:
            layer2_by_price = value_zones[domain][price_bin]

        # ניסיון 2: חיפוש לפי תחום בלבד
        if domain in domain_summary:
            layer2 = domain_summary[domain]
        elif "אחר" in domain_summary:
            layer2 = domain_summary["אחר"]

    # ─── חישוב ניקוד משולב ────────────────────────────────────────────────────
    # משקלים:
    # - שכבה 2 (מומחים שלנו) עם נתוני מחיר: 70%
    # - שכבה 2 (מומחים שלנו) ללא נתוני מחיר: 60%
    # - שכבה 1 (שוק כללי): 30-40%
    
    combined_score = None
    confidence = "נמוכה"
    
    if layer2_by_price and layer2_by_price.get("reliable") and layer1:
        # שכבה 2 עם מחיר + שכבה 1
        l2_rate = layer2_by_price["win_rate"]
        l1_rate = layer1["yes_win_rate"]
        combined_score = round(l2_rate * 0.70 + l1_rate * 0.30, 1)
        confidence = "גבוהה" if layer2_by_price["total"] >= 50 else "בינונית"
    elif layer2_by_price and layer1:
        # שכבה 2 עם מחיר (לא אמין) + שכבה 1
        l2_rate = layer2_by_price["win_rate"]
        l1_rate = layer1["yes_win_rate"]
        combined_score = round(l2_rate * 0.60 + l1_rate * 0.40, 1)
        confidence = "נמוכה"
    elif layer2 and layer2.get("reliable") and layer1:
        # שכבה 2 ללא מחיר (אמין) + שכבה 1
        l2_rate = layer2["win_rate"]
        l1_rate = layer1["yes_win_rate"]
        combined_score = round(l2_rate * 0.60 + l1_rate * 0.40, 1)
        confidence = "בינונית"
    elif layer2 and layer1:
        # שכבה 2 ללא מחיר (לא אמין) + שכבה 1
        l2_rate = layer2["win_rate"]
        l1_rate = layer1["yes_win_rate"]
        combined_score = round(l2_rate * 0.50 + l1_rate * 0.50, 1)
        confidence = "נמוכה"
    elif layer1:
        # רק שכבה 1
        combined_score = layer1["yes_win_rate"]
        confidence = "נמוכה"

    # המלצה לפי ניקוד משולב
    if combined_score is None:
        recommendation = "אין נתונים"
    elif combined_score >= 80:
        recommendation = "חזק מאוד"
    elif combined_score >= 65:
        recommendation = "חזק"
    elif combined_score >= 50:
        recommendation = "בינוני"
    elif combined_score >= 35:
        recommendation = "חלש"
    else:
        recommendation = "חלש מאוד"

    return {
        "domain": domain,
        "price_bin": price_bin,
        "layer1": layer1,
        "layer2": layer2,
        "layer2_by_price": layer2_by_price,
        "combined_score": combined_score,
        "recommendation": recommendation,
        "confidence": confidence,
    }

# ─── פורמט התראה ─────────────────────────────────────────────────────────────

def format_value_zone_alert(market_title: str, entry_price: float) -> str:
    """
    מחזיר שורות התראה על Value Zone לשימוש בהתראות טלגרם.
    
    דוגמה:
    📊 Value Zone: ספורט | מחיר 0.35-0.50
    🌍 שוק כללי: 35% YES מנצח (208 שווקים)
    🏆 המומחים שלנו: 89% הצלחה (1,159 עסקאות) ✅ אמין
    ⚡ ניקוד משולב: 72% | המלצה: חזק | ביטחון: בינוני
    """
    try:
        analysis = get_value_zone_analysis(market_title, entry_price)

        domain = analysis["domain"]
        price_bin = analysis["price_bin"]
        layer1 = analysis["layer1"]
        layer2 = analysis["layer2"]
        layer2_bp = analysis["layer2_by_price"]
        combined = analysis["combined_score"]
        rec = analysis["recommendation"]
        conf = analysis["confidence"]

        lines = [f"📊 *Value Zone:* {domain} | מחיר {price_bin}"]

        # שכבה 1
        if layer1:
            l1_rate = layer1["yes_win_rate"]
            l1_total = layer1.get("total_markets", 0)
            l1_reliable = "✅" if layer1.get("reliable") else "⚠️"
            lines.append(f"🌍 שוק כללי: {l1_rate}% YES מנצח ({l1_total:,} שווקים) {l1_reliable}")
        else:
            lines.append("🌍 שוק כללי: אין נתונים")

        # שכבה 2 — לפי תחום + מחיר (אם קיים)
        if layer2_bp:
            l2_rate = layer2_bp["win_rate"]
            l2_total = layer2_bp["total"]
            l2_wins = layer2_bp["wins"]
            l2_reliable = "✅" if layer2_bp.get("reliable") else "⚠️"
            lines.append(
                f"🏆 מומחים שלנו [{price_bin}]: {l2_rate}% הצלחה "
                f"({l2_wins}/{l2_total}) {l2_reliable}"
            )
        elif layer2:
            l2_rate = layer2["win_rate"]
            l2_total = layer2["total"]
            l2_wins = layer2["wins"]
            l2_reliable = "✅" if layer2.get("reliable") else "⚠️"
            lines.append(
                f"🏆 מומחים שלנו [{domain}]: {l2_rate}% הצלחה "
                f"({l2_wins}/{l2_total}) {l2_reliable}"
            )
        else:
            lines.append("🏆 מומחים שלנו: אין נתונים")

        # ניקוד משולב
        if combined is not None:
            # אמוג'י לפי המלצה
            if rec in ("חזק מאוד", "חזק"):
                rec_emoji = "🟢"
            elif rec == "בינוני":
                rec_emoji = "🟡"
            else:
                rec_emoji = "🔴"
            lines.append(
                f"⚡ ניקוד משולב: *{combined}%* | {rec_emoji} {rec} | ביטחון: {conf}"
            )
        else:
            lines.append("⚡ ניקוד משולב: אין נתונים מספיקים")

        return "\n" + "\n".join(lines)

    except Exception as e:
        logger.debug(f"שגיאה בניתוח Value Zone: {e}")
        return ""


def get_value_zone_score(market_title: str, entry_price: float) -> float | None:
    """
    מחזיר רק את הניקוד המשולב (0-100) לשימוש בפילטרים.
    מחזיר None אם אין נתונים.
    """
    try:
        analysis = get_value_zone_analysis(market_title, entry_price)
        return analysis.get("combined_score")
    except Exception:
        return None


# ─── בדיקה עצמאית ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    test_cases = [
        ("Will the Kansas City Chiefs win Super Bowl LX?", 0.42),
        ("Will Trump win the 2028 presidential election?", 0.55),
        ("Will Bitcoin reach $200k in 2025?", 0.30),
        ("Will Russia and Ukraine sign a ceasefire by June 2025?", 0.25),
        ("Will Apple release a foldable iPhone in 2025?", 0.40),
        ("Will the Fed cut rates in March 2025?", 0.60),
        ("Will Taylor Swift win Album of the Year at the Grammys?", 0.70),
    ]

    print("=" * 70)
    print("🔬 בדיקת Value Zone Analysis")
    print("=" * 70)

    for title, price in test_cases:
        print(f"\n📌 שוק: {title[:60]}")
        print(f"   מחיר כניסה: {price}")
        alert = format_value_zone_alert(title, price)
        print(alert)
        print("-" * 50)
