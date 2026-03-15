"""
expert_domain_analyzer.py
מנתח את תחומי המומחיות של מומחים לפי היסטוריית העסקאות שלהם ב-Polymarket.

מקור הנתונים: data-api.polymarket.com/positions (כולל עסקאות סגורות)
סיווג: לפי מילות מפתח בשם השוק
"""

import requests
import logging
import time
from collections import defaultdict
from functools import lru_cache

logger = logging.getLogger(__name__)

# ─── קטגוריות ומילות מפתח לסיווג ───────────────────────────────────────────

DOMAIN_KEYWORDS = {
    "ספורט": [
        "win", "beat", "champion", "cup", "league", "tournament", "match",
        "game", "nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball",
        "baseball", "tennis", "golf", "ufc", "boxing", "f1", "formula",
        "superbowl", "super bowl", "world cup", "playoff", "finals",
        "boilermakers", "purdue", "ncaa", "college", "team", "score",
        "middlesbrough", "premier league", "champions league",
    ],
    "פוליטיקה": [
        "president", "election", "vote", "win", "senator", "congress",
        "democrat", "republican", "trump", "biden", "harris", "vance",
        "governor", "mayor", "parliament", "minister", "chancellor",
        "macron", "starmer", "fidesz", "bardella", "mamdani", "miyares",
        "cdU", "coalition", "government", "seats", "party", "poll",
        "nomination", "primary", "inauguration", "impeach", "resign",
        "attorney general", "supreme court",
    ],
    "גיאופוליטיקה": [
        "iran", "israel", "russia", "ukraine", "china", "taiwan", "nato",
        "ceasefire", "war", "strike", "attack", "invasion", "sanctions",
        "nuclear", "missile", "troops", "military", "conflict", "peace",
        "treaty", "deal", "agreement", "xi", "putin", "zelensky",
    ],
    "קריפטו": [
        "bitcoin", "btc", "ethereum", "eth", "crypto", "solana", "sol",
        "xrp", "ripple", "doge", "dogecoin", "coinbase", "binance",
        "blockchain", "defi", "nft", "token", "price", "halving",
        "100k", "200k", "50k", "ath", "all-time high",
    ],
    "כלכלה": [
        "fed", "interest rate", "inflation", "gdp", "recession", "market",
        "stock", "s&p", "nasdaq", "dow", "oil", "gold", "dollar",
        "tariff", "trade", "economy", "unemployment", "jobs", "cpi",
        "fomc", "powell", "treasury", "bond", "yield",
    ],
    "טכנולוגיה": [
        "ai", "artificial intelligence", "openai", "gpt", "chatgpt",
        "google", "apple", "microsoft", "meta", "amazon", "tesla",
        "elon", "musk", "spacex", "starship", "launch", "ipo",
        "acquisition", "merger", "antitrust",
    ],
    "בידור": [
        "oscar", "grammy", "emmy", "award", "movie", "film", "show",
        "album", "song", "artist", "celebrity", "taylor swift",
        "box office", "streaming", "netflix", "disney",
    ],
}

# ─── סיווג שוק לפי שם ────────────────────────────────────────────────────────

def classify_market(title: str) -> str:
    """מסווג שוק לקטגוריה לפי שם השוק."""
    if not title:
        return "אחר"
    title_lower = title.lower()
    
    # בדיקת כל קטגוריה לפי מילות מפתח
    scores = defaultdict(int)
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                scores[domain] += 1
    
    if not scores:
        return "אחר"
    
    # החזרת הקטגוריה עם הניקוד הגבוה ביותר
    return max(scores, key=scores.get)


# ─── שליפת היסטוריית פוזיציות ────────────────────────────────────────────────

def fetch_expert_positions(wallet: str, limit: int = 200) -> list:
    """שולף את כל הפוזיציות (פתוחות וסגורות) של מומחה."""
    try:
        url = f"https://data-api.polymarket.com/positions?user={wallet}&limit={limit}&sizeThreshold=0.01"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.warning(f"שגיאה בשליפת פוזיציות עבור {wallet}: {e}")
    return []


# ─── ניתוח תחומי מומחיות ─────────────────────────────────────────────────────

def analyze_expert_domains(wallet: str) -> dict:
    """
    מנתח את תחומי המומחיות של מומחה לפי היסטוריית הפוזיציות שלו.
    
    מחזיר:
    {
        "total_positions": int,
        "domains": {
            "פוליטיקה": {"count": 5, "wins": 4, "losses": 1, "win_rate": 0.80},
            "ספורט": {"count": 3, "wins": 2, "losses": 1, "win_rate": 0.67},
            ...
        },
        "best_domain": "פוליטיקה",
        "best_domain_win_rate": 0.80,
        "worst_domain": "קריפטו",
    }
    """
    positions = fetch_expert_positions(wallet)
    
    if not positions:
        return {"total_positions": 0, "domains": {}, "best_domain": None}
    
    domain_stats = defaultdict(lambda: {"count": 0, "wins": 0, "losses": 0, "open": 0})
    
    for pos in positions:
        title = pos.get("title", "")
        if not title:
            continue
        
        domain = classify_market(title)
        cur_price = float(pos.get("curPrice", 0) or 0)
        redeemable = pos.get("redeemable", False)
        
        # קביעת תוצאה:
        # - מחיר > 0.99 או redeemable=True → ניצח
        # - מחיר < 0.01 ולא redeemable → הפסיד
        # - אחרת → פתוח
        if cur_price >= 0.99 or redeemable:
            result = "win"
        elif cur_price <= 0.02:
            result = "loss"
        else:
            result = "open"
        
        domain_stats[domain]["count"] += 1
        if result == "win":
            domain_stats[domain]["wins"] += 1
        elif result == "loss":
            domain_stats[domain]["losses"] += 1
        else:
            domain_stats[domain]["open"] += 1
    
    # חישוב אחוז הצלחה לכל תחום
    result_domains = {}
    for domain, stats in domain_stats.items():
        closed = stats["wins"] + stats["losses"]
        win_rate = stats["wins"] / closed if closed > 0 else None
        result_domains[domain] = {
            "count": stats["count"],
            "wins": stats["wins"],
            "losses": stats["losses"],
            "open": stats["open"],
            "win_rate": win_rate,
        }
    
    # מציאת תחום הטוב ביותר (לפחות 2 עסקאות סגורות)
    best_domain = None
    best_rate = 0
    worst_domain = None
    worst_rate = 1.0
    
    for domain, stats in result_domains.items():
        closed = stats["wins"] + stats["losses"]
        if closed >= 2 and stats["win_rate"] is not None:
            if stats["win_rate"] > best_rate:
                best_rate = stats["win_rate"]
                best_domain = domain
            if stats["win_rate"] < worst_rate:
                worst_rate = stats["win_rate"]
                worst_domain = domain
    
    return {
        "total_positions": len(positions),
        "domains": result_domains,
        "best_domain": best_domain,
        "best_domain_win_rate": best_rate if best_domain else None,
        "worst_domain": worst_domain,
        "worst_domain_win_rate": worst_rate if worst_domain else None,
    }


# ─── Cache לביצועים (לא לשלוף כל פעם) ───────────────────────────────────────

_domain_cache = {}  # wallet -> (timestamp, result)
CACHE_TTL_SECONDS = 3600  # שעה אחת

def get_expert_domain_profile(wallet: str) -> dict:
    """
    מחזיר פרופיל תחומי מומחיות עם cache של שעה.
    """
    now = time.time()
    if wallet in _domain_cache:
        cached_time, cached_result = _domain_cache[wallet]
        if now - cached_time < CACHE_TTL_SECONDS:
            return cached_result
    
    result = analyze_expert_domains(wallet)
    _domain_cache[wallet] = (now, result)
    return result


def format_domain_alert_line(wallet: str, current_market_title: str) -> str:
    """
    מחזיר שורת התראה על תחום המומחיות של המומחה ביחס לשוק הנוכחי.
    
    דוגמה:
    🏆 תחום מומחיות: פוליטיקה (80% הצלחה | 4/5 עסקאות)
    ✅ זה תחום החוזקה שלו!
    
    או:
    ⚠️ תחום: פוליטיקה — לא תחום החוזקה שלו (50% הצלחה)
    🏆 הוא מצטיין ב: ספורט (90% הצלחה)
    """
    try:
        profile = get_expert_domain_profile(wallet)
        
        if not profile or not profile.get("domains"):
            return ""
        
        # סיווג השוק הנוכחי
        current_domain = classify_market(current_market_title)
        domains = profile.get("domains", {})
        best_domain = profile.get("best_domain")
        best_rate = profile.get("best_domain_win_rate")
        
        # נתוני התחום הנוכחי
        current_stats = domains.get(current_domain, {})
        current_rate = current_stats.get("win_rate")
        current_count = current_stats.get("count", 0)
        current_wins = current_stats.get("wins", 0)
        current_losses = current_stats.get("losses", 0)
        current_closed = current_wins + current_losses
        
        lines = []
        
        # שורה 1: ביצועים בתחום הנוכחי
        if current_rate is not None and current_closed >= 2:
            pct = int(current_rate * 100)
            if current_rate >= 0.70:
                emoji = "🏆"
                strength = "תחום חוזקה!"
            elif current_rate >= 0.50:
                emoji = "🟡"
                strength = "ביצועים בינוניים"
            else:
                emoji = "⚠️"
                strength = "תחום חולשה"
            lines.append(
                f"{emoji} ביצועי המומחה ב*{current_domain}*: "
                f"{pct}% הצלחה ({current_wins}/{current_closed} עסקאות) — {strength}"
            )
        elif current_count > 0:
            lines.append(f"📊 תחום *{current_domain}*: {current_count} עסקאות (נתונים חלקיים)")
        else:
            lines.append(f"📊 תחום *{current_domain}*: אין היסטוריה בתחום זה")
        
        # שורה 2: תחום הטוב ביותר (אם שונה מהנוכחי)
        if best_domain and best_domain != current_domain and best_rate is not None:
            best_pct = int(best_rate * 100)
            lines.append(f"🥇 תחום החוזקה שלו: *{best_domain}* ({best_pct}% הצלחה)")
        
        return "\n" + "\n".join(lines) if lines else ""
    
    except Exception as e:
        logger.debug(f"שגיאה בניתוח תחום מומחיות: {e}")
        return ""


# ─── בדיקה עצמאית ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # בדיקה עם GCottrell93
    wallet = "0x94a428cfa4f84b264e01f70d93d02bc96cb36356"
    print("מנתח תחומי מומחיות עבור GCottrell93...")
    profile = analyze_expert_domains(wallet)
    
    print(f"\nסה\"כ פוזיציות: {profile['total_positions']}")
    print(f"תחום הטוב ביותר: {profile['best_domain']} ({profile.get('best_domain_win_rate', 0)*100:.0f}%)")
    print(f"תחום הגרוע ביותר: {profile['worst_domain']}")
    print("\nפירוט לפי תחום:")
    for domain, stats in sorted(profile['domains'].items(), key=lambda x: x[1].get('count', 0), reverse=True):
        wr = stats.get('win_rate')
        wr_str = f"{wr*100:.0f}%" if wr is not None else "N/A"
        print(f"  {domain}: {stats['count']} עסקאות | {stats['wins']}W/{stats['losses']}L | {wr_str}")
    
    print("\n--- בדיקת שורת התראה ---")
    test_markets = [
        "Will J.D. Vance win the 2028 Republican presidential nomination?",
        "US strikes Iran by March 31?",
        "Bitcoin price above 100k by end of 2025?",
        "Purdue Boilermakers win the NCAA tournament?",
    ]
    for market in test_markets:
        line = format_domain_alert_line(wallet, market)
        print(f"\nשוק: {market[:50]}")
        print(f"שורה: {line}")
