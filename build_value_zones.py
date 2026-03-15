"""
Build Value Zones from Polymarket historical closed markets data.
Layer 1: General market trends (all Polymarket closed markets)
Layer 2: Our experts/whales historical positions
"""
import requests
import json
import time
from collections import defaultdict

# ─── Domain classification keywords ───────────────────────────────────────────
DOMAIN_KEYWORDS = {
    "ספורט": [
        "nba", "nfl", "mlb", "nhl", "soccer", "football", "basketball", "baseball",
        "tennis", "golf", "ufc", "mma", "boxing", "cricket", "rugby", "olympics",
        "world cup", "champions league", "premier league", "la liga", "serie a",
        "bundesliga", "super bowl", "playoffs", "championship", "tournament",
        "match", "game", "season", "win", "score", "player", "team", "league",
        "cup", "bowl", "series", "race", "f1", "formula", "nascar", "esports",
        "fifa", "uefa", "ncaa", "march madness", "wimbledon", "us open"
    ],
    "פוליטיקה": [
        "president", "election", "vote", "senate", "congress", "democrat",
        "republican", "biden", "trump", "harris", "governor", "mayor", "primary",
        "ballot", "poll", "approval", "impeach", "cabinet", "secretary", "minister",
        "parliament", "legislation", "bill", "law", "supreme court", "justice",
        "nomination", "candidate", "campaign", "inauguration", "resign", "veto"
    ],
    "גיאופוליטיקה": [
        "war", "ukraine", "russia", "china", "taiwan", "nato", "un ", "united nations",
        "sanctions", "ceasefire", "invasion", "military", "troops", "nuclear",
        "missile", "treaty", "diplomacy", "israel", "gaza", "iran", "north korea",
        "conflict", "peace", "attack", "offensive", "territory", "border"
    ],
    "קריפטו": [
        "bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain", "defi",
        "nft", "solana", "sol", "binance", "coinbase", "sec crypto", "altcoin",
        "stablecoin", "usdc", "usdt", "doge", "dogecoin", "ripple", "xrp",
        "polygon", "matic", "avalanche", "avax", "cardano", "ada", "web3",
        "token", "dao", "yield", "staking", "halving", "etf bitcoin"
    ],
    "כלכלה": [
        "fed", "federal reserve", "interest rate", "inflation", "gdp", "recession",
        "unemployment", "stock", "s&p", "nasdaq", "dow", "market cap", "ipo",
        "earnings", "revenue", "profit", "debt ceiling", "budget", "tariff",
        "trade war", "oil price", "gold price", "dollar", "euro", "yen",
        "cpi", "pce", "fomc", "rate hike", "rate cut", "bond", "yield curve"
    ],
    "טכנולוגיה": [
        "ai ", "artificial intelligence", "openai", "gpt", "chatgpt", "google",
        "apple", "microsoft", "meta", "amazon", "tesla", "spacex", "elon musk",
        "sam altman", "nvidia", "chip", "semiconductor", "launch", "release",
        "product", "app", "software", "hardware", "robot", "autonomous", "self-driving"
    ],
    "בידור": [
        "oscar", "emmy", "grammy", "golden globe", "movie", "film", "tv show",
        "series", "album", "song", "artist", "celebrity", "award", "box office",
        "streaming", "netflix", "disney", "spotify", "concert", "tour"
    ]
}

def classify_domain(question: str) -> str:
    """Classify a market question into a domain."""
    q = question.lower()
    scores = defaultdict(int)
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in q:
                scores[domain] += 1
    if scores:
        return max(scores, key=scores.get)
    return "אחר"

def get_price_bin(price: float) -> str:
    """Get price bin label for a given entry price."""
    if price < 0.20:
        return "0.00-0.20"
    elif price < 0.35:
        return "0.20-0.35"
    elif price < 0.50:
        return "0.35-0.50"
    elif price < 0.65:
        return "0.50-0.65"
    elif price < 0.75:
        return "0.65-0.75"
    else:
        return "0.75+"

def fetch_closed_markets_layer1(max_pages=50):
    """Fetch closed binary markets from Polymarket Gamma API."""
    print("📥 שולף שווקים סגורים מ-Polymarket...")
    all_markets = []
    limit = 100

    for page in range(max_pages):
        offset = page * limit
        url = f"https://gamma-api.polymarket.com/markets?closed=true&limit={limit}&offset={offset}"
        try:
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                print(f"  שגיאה בדף {page}: {r.status_code}")
                break
            data = r.json()
            if not data:
                print(f"  אין יותר נתונים בדף {page}")
                break
            all_markets.extend(data)
            print(f"  דף {page+1}: {len(data)} שווקים (סה\"כ: {len(all_markets)})")
            time.sleep(0.3)  # Rate limit
        except Exception as e:
            print(f"  שגיאה: {e}")
            break

    print(f"\n✅ סה\"כ שווקים שנשלפו: {len(all_markets)}")
    return all_markets

def analyze_markets_layer1(markets):
    """Analyze markets and build value zones."""
    print("\n🔍 מנתח שווקים...")

    # Structure: {domain: {price_bin: {wins: int, total: int}}}
    zones = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "total": 0}))

    skipped = 0
    processed = 0

    for mkt in markets:
        try:
            question = mkt.get("question", "")
            if not question:
                skipped += 1
                continue

            # Get outcome prices — for binary markets [yes_price, no_price]
            outcome_prices_raw = mkt.get("outcomePrices", "[]")
            if isinstance(outcome_prices_raw, str):
                outcome_prices = json.loads(outcome_prices_raw)
            else:
                outcome_prices = outcome_prices_raw

            if len(outcome_prices) != 2:
                skipped += 1
                continue

            yes_price = float(outcome_prices[0])
            no_price = float(outcome_prices[1])

            # Determine winner: if yes_price == 1.0 → YES won, if no_price == 1.0 → NO won
            if yes_price >= 0.99:
                winner = "Yes"
            elif no_price >= 0.99:
                winner = "No"
            else:
                skipped += 1  # Not clearly resolved
                continue

            # Get volume for weighting
            volume = float(mkt.get("volume", 0) or 0)
            if volume < 100:  # Skip tiny markets
                skipped += 1
                continue

            # Classify domain
            domain = classify_domain(question)

            # We analyze from the perspective of a YES buyer
            # Entry price = what YES was trading at (we don't have this directly for historical)
            # Use the final price as proxy — but we need the ENTRY price
            # For closed markets, we can use the fact that:
            # - If YES won and final price = 1.0, the "smart" entry was at lower prices
            # We'll use volume-weighted approach: assume entry was at ~0.5 for now
            # Better: use the market's liquidity/volume as signal

            # Actually for Layer 1, we track: given a market in domain X,
            # what % of YES outcomes happened? This gives base rate.
            # We'll bin by "what would the entry price have been" using
            # the market's characteristics

            # For simplicity: record YES win rate by domain
            # Price bin: we'll use the final resolved price direction
            # For a more meaningful analysis, let's use volume as proxy for confidence
            # High volume markets = price was probably well-calibrated

            # Simple approach: record win (YES=1) or loss (YES=0) by domain
            # and by approximate entry price (we'll use 0.5 as neutral)
            # This gives us base rates by domain

            # Better: for each market, the "entry price" is unknown
            # but we know the outcome. We'll create a synthetic entry price
            # based on what a typical trader might have paid.
            # For now, record by domain only (not price bin) for Layer 1 base rates

            won = 1 if winner == "Yes" else 0
            zones[domain]["all"]["total"] += 1
            zones[domain]["all"]["wins"] += won
            processed += 1

        except Exception as e:
            skipped += 1
            continue

    print(f"  עובדו: {processed}, דולגו: {skipped}")
    return zones

def fetch_closed_markets_with_prices(max_pages=100):
    """Fetch closed markets with better price data for price bin analysis."""
    print("\n📥 שולף שווקים עם נתוני מחיר...")
    all_records = []
    limit = 100

    for page in range(max_pages):
        offset = page * limit
        # Use events endpoint which has more data
        url = f"https://gamma-api.polymarket.com/markets?closed=true&limit={limit}&offset={offset}&order=volume&ascending=false"
        try:
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            if not data:
                break

            for mkt in data:
                try:
                    question = mkt.get("question", "")
                    outcome_prices_raw = mkt.get("outcomePrices", "[]")
                    if isinstance(outcome_prices_raw, str):
                        outcome_prices = json.loads(outcome_prices_raw)
                    else:
                        outcome_prices = outcome_prices_raw

                    if len(outcome_prices) != 2:
                        continue

                    yes_final = float(outcome_prices[0])
                    no_final = float(outcome_prices[1])

                    # Determine winner
                    if yes_final >= 0.99:
                        winner = "Yes"
                    elif no_final >= 0.99:
                        winner = "No"
                    else:
                        continue

                    volume = float(mkt.get("volume", 0) or 0)
                    if volume < 500:
                        continue

                    liquidity = float(mkt.get("liquidity", 0) or 0)
                    domain = classify_domain(question)

                    # Estimate entry price: for YES winner, entry was likely
                    # somewhere between 0.1 and 0.9. We use liquidity/volume ratio
                    # as a proxy for market efficiency.
                    # Better approach: use the market's start price if available
                    # For now, we'll use a heuristic based on volume tiers

                    all_records.append({
                        "question": question,
                        "domain": domain,
                        "winner": winner,
                        "volume": volume,
                        "liquidity": liquidity,
                        "yes_final": yes_final,
                        "no_final": no_final
                    })
                except:
                    continue

            print(f"  דף {page+1}: {len(data)} → {len(all_records)} תקינים")
            time.sleep(0.3)
        except Exception as e:
            print(f"  שגיאה: {e}")
            break

    print(f"\n✅ סה\"כ רשומות תקינות: {len(all_records)}")
    return all_records

def build_layer1_zones(records):
    """Build Layer 1 value zones from market records."""
    print("\n🏗️ בונה Value Zones שכבה 1...")

    # For Layer 1, we compute YES win rates by domain
    # Since we don't have entry prices, we compute:
    # 1. Base YES win rate by domain (overall)
    # 2. This tells us: "in domain X, what % of YES bets win?"

    domain_stats = defaultdict(lambda: {"wins": 0, "total": 0, "volume": 0})

    for rec in records:
        domain = rec["domain"]
        won = 1 if rec["winner"] == "Yes" else 0
        domain_stats[domain]["wins"] += won
        domain_stats[domain]["total"] += 1
        domain_stats[domain]["volume"] += rec["volume"]

    # Build the zones JSON
    zones = {}
    for domain, stats in domain_stats.items():
        total = stats["total"]
        wins = stats["wins"]
        if total >= 10:
            win_rate = round(wins / total * 100, 1)
            zones[domain] = {
                "yes_win_rate": win_rate,
                "total_markets": total,
                "total_volume": round(stats["volume"]),
                "reliable": total >= 100
            }
            print(f"  {domain}: {win_rate}% הצלחה ({total} שווקים)")

    return zones

def main():
    print("=" * 60)
    print("🔬 בונה Value Zones — שכבה 1 (מגמות שוק כלליות)")
    print("=" * 60)

    # Fetch data
    records = fetch_closed_markets_with_prices(max_pages=100)

    if not records:
        print("❌ לא נשלפו נתונים")
        return

    # Build zones
    zones = build_layer1_zones(records)

    # Save to JSON
    output = {
        "metadata": {
            "source": "Polymarket Gamma API",
            "total_markets_analyzed": len(records),
            "description": "YES win rates by domain — general market trends",
            "note": "Win rate = % of YES outcomes in closed binary markets",
            "min_markets_for_reliable": 100
        },
        "domain_win_rates": zones
    }

    with open("/home/ubuntu/polymarket-bot-v2/value_zones_global.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ נשמר: value_zones_global.json")
    print(f"   תחומים: {len(zones)}")
    print(f"   שווקים: {len(records)}")

if __name__ == "__main__":
    main()
