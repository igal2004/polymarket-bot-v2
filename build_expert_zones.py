"""
build_expert_zones.py
שכבה 2 — ניתוח ביצועי המומחים והלווייתנים שלנו לפי תחום
מקור: data-api.polymarket.com/positions (כולל עסקאות סגורות)
"""
import requests
import json
import time
from collections import defaultdict

# ─── ארנקי מומחים ולווייתנים ───────────────────────────────────────────────
EXPERT_WALLETS = {
    "kch123":               "0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee",
    "DrPufferfish":         "0xdb27bf2ac5d428a9c63dbc914611036855a6c56e",
    "KeyTransporter":       "0x94f199fb7789f1aef7fff6b758d6b375100f4c7a",
    "RN1":                  "0x2005d16a84ceefa912d4e380cd32e7ff827875ea",
    "GCottrell93":          "0x94a428cfa4f84b264e01f70d93d02bc96cb36356",
    "swisstony":            "0x204f72f35326db932158cba6adff0b9a1da95e14",
    "gmanas":               "0xe90bec87d9ef430f27f9dcfe72c34b76967d5da2",
    "GamblingIsAllYouNeed": "0x507e52ef684ca2dd91f90a9d26d149dd3288beae",
    "blackwall":            "0xac44cb78be973ec7d91b69678c4bdfa7009afbd7",
    "beachboy4":            "0xc2e7800b5af46e6093872b177b7a5e7f0563be51",
    "anoin123":             "0x96489abcb9f583d6835c8ef95ffc923d05a86825",
    "weflyhigh":            "0x03e8a544e97eeff5753bc1e90d46e5ef22af1697",
    "gmpm":                 "0x14964aefa2cd7caff7878b3820a690a03c5aa429",
    "YatSen":               "0x5bffcf561bcae83af680ad600cb99f1184d6ffbe",
    "SwissMiss":            "0xdbade4c82fb72780a0db9a38f821d8671aba9c95",
}

WHALE_WALLETS = {
    "Theo4":      "0x56687bf447db6ffa42ffe2204a05edaa20f55839",
    "Fredi9999":  "0x1f2dd6d473f3e824cd2f8a89d9c69fb96f6ad0cf",
    "Len9311238": "0x78b9ac44a6d7d7a076c14e0ad518b301b63c6b76",
    "zxgngl":     "0xd235973291b2b75ff4070e9c0b01728c520b0f29",
    "RepTrump":   "0x863134d00841b2e200492805a01e1e2f5defaa53",
}

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
        "taylor swift", "box office",
    ],
}

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

def fetch_positions(wallet: str, limit: int = 500) -> list:
    """שולף פוזיציות מ-data-api.polymarket.com."""
    all_positions = []
    offset = 0
    while True:
        try:
            url = (
                f"https://data-api.polymarket.com/positions"
                f"?user={wallet}&limit={limit}&offset={offset}&sizeThreshold=0.01"
            )
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            if not data:
                break
            all_positions.extend(data)
            if len(data) < limit:
                break
            offset += limit
            time.sleep(0.2)
        except Exception as e:
            print(f"    שגיאה: {e}")
            break
    return all_positions

def analyze_wallet(name: str, wallet: str, trader_type: str) -> dict:
    """מנתח ביצועי ארנק לפי תחום ומחיר."""
    print(f"  🔍 {name} ({trader_type}) — {wallet[:10]}...")
    positions = fetch_positions(wallet)
    print(f"     {len(positions)} פוזיציות")

    # {domain: {price_bin: {wins, losses, total}}}
    stats = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "losses": 0, "total": 0}))
    domain_totals = defaultdict(lambda: {"wins": 0, "losses": 0, "total": 0})

    for pos in positions:
        title = pos.get("title", "") or pos.get("market", "")
        if not title:
            continue

        cur_price = float(pos.get("curPrice", 0) or 0)
        redeemable = pos.get("redeemable", False)
        size = float(pos.get("size", 0) or 0)
        avg_price = float(pos.get("avgPrice", 0) or 0)

        # קביעת תוצאה
        if cur_price >= 0.99 or redeemable:
            result = "win"
        elif cur_price <= 0.02:
            result = "loss"
        else:
            continue  # פתוח — מדלגים

        domain = classify_domain(title)
        price_bin = get_price_bin(avg_price) if avg_price > 0 else get_price_bin(0.5)

        stats[domain][price_bin]["total"] += 1
        domain_totals[domain]["total"] += 1
        if result == "win":
            stats[domain][price_bin]["wins"] += 1
            domain_totals[domain]["wins"] += 1
        else:
            stats[domain][price_bin]["losses"] += 1
            domain_totals[domain]["losses"] += 1

    return {
        "name": name,
        "wallet": wallet,
        "type": trader_type,
        "total_positions": len(positions),
        "domain_price_stats": {d: dict(pb) for d, pb in stats.items()},
        "domain_totals": dict(domain_totals),
    }

def aggregate_all_wallets(wallet_results: list) -> dict:
    """מצבר נתונים מכל הארנקים לטבלת Value Zones."""
    # {domain: {price_bin: {wins, total}}}
    combined = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "total": 0}))
    domain_combined = defaultdict(lambda: {"wins": 0, "total": 0})

    for result in wallet_results:
        for domain, price_bins in result["domain_price_stats"].items():
            for price_bin, s in price_bins.items():
                combined[domain][price_bin]["wins"] += s["wins"]
                combined[domain][price_bin]["total"] += s["total"]
        for domain, s in result["domain_totals"].items():
            domain_combined[domain]["wins"] += s["wins"]
            domain_combined[domain]["total"] += s["total"]

    # בניית טבלת Value Zones
    value_zones = {}
    for domain, price_bins in combined.items():
        value_zones[domain] = {}
        for price_bin, s in price_bins.items():
            total = s["total"]
            wins = s["wins"]
            if total >= 5:  # מינימום 5 עסקאות לתא (המומחים שלנו יש להם פחות נתונים)
                win_rate = round(wins / total * 100, 1)
                value_zones[domain][price_bin] = {
                    "win_rate": win_rate,
                    "wins": wins,
                    "losses": total - wins,
                    "total": total,
                    "reliable": total >= 20,  # 20 עסקאות = אמינות בסיסית
                }

    # סיכום לפי תחום בלבד (ללא פיצול מחיר)
    domain_summary = {}
    for domain, s in domain_combined.items():
        total = s["total"]
        wins = s["wins"]
        if total >= 5:
            domain_summary[domain] = {
                "win_rate": round(wins / total * 100, 1),
                "wins": wins,
                "losses": total - wins,
                "total": total,
                "reliable": total >= 20,
            }

    return {
        "value_zones_by_domain_price": value_zones,
        "domain_summary": domain_summary,
    }

def main():
    print("=" * 60)
    print("🔬 בונה Value Zones — שכבה 2 (מומחים ולווייתנים שלנו)")
    print("=" * 60)

    all_results = []

    # מומחים
    print("\n📊 מנתח מומחים...")
    for name, wallet in EXPERT_WALLETS.items():
        result = analyze_wallet(name, wallet, "expert")
        all_results.append(result)
        time.sleep(0.5)

    # לווייתנים
    print("\n🐋 מנתח לווייתנים...")
    for name, wallet in WHALE_WALLETS.items():
        result = analyze_wallet(name, wallet, "whale")
        all_results.append(result)
        time.sleep(0.5)

    print(f"\n✅ נותחו {len(all_results)} ארנקים")

    # צבירה
    aggregated = aggregate_all_wallets(all_results)

    # הדפסת סיכום
    print("\n📈 סיכום לפי תחום:")
    for domain, s in sorted(aggregated["domain_summary"].items(), key=lambda x: x[1]["total"], reverse=True):
        reliable_str = "✅" if s["reliable"] else "⚠️"
        print(f"  {reliable_str} {domain}: {s['win_rate']}% ({s['wins']}/{s['total']})")

    print("\n📊 Value Zones לפי תחום + מחיר:")
    for domain, price_bins in aggregated["value_zones_by_domain_price"].items():
        print(f"\n  {domain}:")
        for pb, s in sorted(price_bins.items()):
            reliable_str = "✅" if s["reliable"] else "⚠️"
            print(f"    {reliable_str} [{pb}]: {s['win_rate']}% ({s['wins']}/{s['total']})")

    # שמירה
    output = {
        "metadata": {
            "source": "Polymarket data-api.polymarket.com/positions",
            "wallets_analyzed": len(all_results),
            "experts": list(EXPERT_WALLETS.keys()),
            "whales": list(WHALE_WALLETS.keys()),
            "description": "Win rates by domain and price bin for our tracked experts/whales",
            "min_trades_reliable": 20,
        },
        "per_wallet": [
            {
                "name": r["name"],
                "type": r["type"],
                "total_positions": r["total_positions"],
                "domain_totals": r["domain_totals"],
            }
            for r in all_results
        ],
        "aggregated": aggregated,
    }

    out_path = "/home/ubuntu/polymarket-bot-v2/value_zones_experts.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ נשמר: {out_path}")
    print(f"   תחומים: {len(aggregated['domain_summary'])}")
    print(f"   ארנקים: {len(all_results)}")

if __name__ == "__main__":
    main()
