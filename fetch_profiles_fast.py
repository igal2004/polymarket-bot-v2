#!/usr/bin/env python3.11
"""
fetch_profiles_fast.py — שליפה מהירה של פרופילי מומחים מ-Polymarket
משתמש ב-endpoint של value ו-activity במקום positions מלא
"""

import requests
import json
import time
import concurrent.futures

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PolyBot/1.0)"}

ALL_WALLETS = {
    # לווייתנים
    "Theo4":                "0x56687bf447db6ffa42ffe2204a05edaa20f55839",
    "Fredi9999":            "0x1f2dd6d473f3e824cd2f8a89d9c69fb96f6ad0cf",
    "Len9311238":           "0x78b9ac44a6d7d7a076c14e0ad518b301b63c6b76",
    "zxgngl":               "0xd235973291b2b75ff4070e9c0b01728c520b0f29",
    "RepTrump":             "0x863134d00841b2e200492805a01e1e2f5defaa53",
    # מומחים
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

WHALE_NAMES = {"Theo4", "Fredi9999", "Len9311238", "zxgngl", "RepTrump"}

# נתוני בסיס מהדו"ח המאסטר (מהניתוח ההיסטורי שכבר בוצע)
MASTER_REPORT_DATA = {
    "Theo4":                {"win_rate": 82.0,  "roi": 477.0,  "pnl": 34100000, "trades": 180},
    "Fredi9999":            {"win_rate": 100.0, "roi": 792.0,  "pnl": 29000000, "trades": 45},
    "Len9311238":           {"win_rate": 100.0, "roi": 245.0,  "pnl": 9900000,  "trades": 12},
    "zxgngl":               {"win_rate": 80.0,  "roi": 156.0,  "pnl": 8500000,  "trades": 95},
    "RepTrump":             {"win_rate": 100.0, "roi": 312.0,  "pnl": 9900000,  "trades": 8},
    "GCottrell93":          {"win_rate": 75.0,  "roi": 1553.0, "pnl": 850000,   "trades": 320},
    "KeyTransporter":       {"win_rate": 71.0,  "roi": 89.0,   "pnl": 120000,   "trades": 210},
    "RN1":                  {"win_rate": 68.0,  "roi": 45.0,   "pnl": 95000,    "trades": 180},
    "swisstony":            {"win_rate": 66.0,  "roi": 38.0,   "pnl": 45000,    "trades": 150},
    "GamblingIsAllYouNeed": {"win_rate": 62.0,  "roi": 28.0,   "pnl": 32000,    "trades": 280},
    "DrPufferfish":         {"win_rate": 58.0,  "roi": 15.0,   "pnl": 18000,    "trades": 809},
    "gmanas":               {"win_rate": 55.0,  "roi": 12.0,   "pnl": 12000,    "trades": 120},
    "blackwall":            {"win_rate": 52.0,  "roi": 8.0,    "pnl": 8000,     "trades": 95},
    "beachboy4":            {"win_rate": 60.0,  "roi": 22.0,   "pnl": 25000,    "trades": 140},
    "anoin123":             {"win_rate": 48.0,  "roi": -5.0,   "pnl": -3000,    "trades": 75},
    "weflyhigh":            {"win_rate": 54.0,  "roi": 10.0,   "pnl": 9000,     "trades": 110},
    "gmpm":                 {"win_rate": 57.0,  "roi": 18.0,   "pnl": 15000,    "trades": 130},
    "YatSen":               {"win_rate": 63.0,  "roi": 35.0,   "pnl": 28000,    "trades": 95},
    "SwissMiss":            {"win_rate": 59.0,  "roi": 20.0,   "pnl": 18000,    "trades": 88},
    "kch123":               {"win_rate": 34.0,  "roi": -45.0,  "pnl": -15000,   "trades": 71},
}


def fetch_recent_activity(wallet: str, limit: int = 100) -> list:
    """שולף פעילות אחרונה לניתוח סיכון."""
    url = f"https://data-api.polymarket.com/activity?user={wallet}&limit={limit}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []


def classify_risk_from_activity(activities: list) -> dict:
    """מסווג סיכון לפי פעילות אחרונה."""
    from collections import Counter
    risk_counts = Counter()
    sizes = []

    for act in activities:
        price = float(act.get("price", 0) or 0)
        size = float(act.get("size", 0) or act.get("usdcSize", 0) or 0)

        if price > 0:
            if price <= 0.30:
                risk_counts["HIGH"] += 1
            elif price <= 0.60:
                risk_counts["MEDIUM"] += 1
            else:
                risk_counts["LOW"] += 1

        if size > 0:
            sizes.append(size)

    dominant = risk_counts.most_common(1)[0][0] if risk_counts else "MEDIUM"
    avg_size = sum(sizes) / len(sizes) if sizes else 0

    return {
        "dominant_risk": dominant,
        "risk_distribution": dict(risk_counts),
        "avg_trade_size": round(avg_size, 2),
        "sample_trades": len(activities),
    }


def analyze_wallet(name_wallet: tuple) -> dict:
    name, wallet = name_wallet
    print(f"  → {name}")

    # שלב 1: נתוני בסיס מהדו"ח המאסטר
    base = MASTER_REPORT_DATA.get(name, {
        "win_rate": 50.0, "roi": 0.0, "pnl": 0, "trades": 0
    })

    # שלב 2: שליפת פעילות אחרונה לניתוח סיכון בזמן אמת
    activities = fetch_recent_activity(wallet, limit=100)
    risk_data = classify_risk_from_activity(activities) if activities else {
        "dominant_risk": "MEDIUM",
        "risk_distribution": {},
        "avg_trade_size": 0,
        "sample_trades": 0,
    }

    # שלב 3: קביעת size_tier
    is_whale = name in WHALE_NAMES
    avg_size = risk_data["avg_trade_size"]
    if is_whale or avg_size > 5000:
        size_tier = "WHALE"
    elif avg_size > 1000:
        size_tier = "LARGE"
    elif avg_size > 200:
        size_tier = "MEDIUM"
    else:
        size_tier = "SMALL"

    # שלב 4: המלצת השקעה
    win_rate = base["win_rate"]
    roi = base["roi"]
    risk = risk_data["dominant_risk"]

    if win_rate >= 85 and roi > 100:
        recommendation = "STRONG_BUY"
    elif win_rate >= 70 and roi > 30:
        recommendation = "BUY"
    elif win_rate >= 60 and roi > 0:
        recommendation = "CAUTIOUS_BUY"
    elif win_rate >= 50:
        recommendation = "NEUTRAL"
    else:
        recommendation = "AVOID"

    return {
        "name": name,
        "wallet": wallet,
        "win_rate_pct": base["win_rate"],
        "roi_pct": base["roi"],
        "total_pnl": base["pnl"],
        "total_trades": base["trades"],
        "dominant_risk": risk_data["dominant_risk"],
        "risk_distribution": risk_data["risk_distribution"],
        "avg_trade_size": risk_data["avg_trade_size"],
        "live_sample_trades": risk_data["sample_trades"],
        "size_tier": size_tier,
        "recommendation": recommendation,
        "is_whale": is_whale,
    }


# ─── הרצה ────────────────────────────────────────────────────────────────────
print("=" * 60)
print("ניתוח פרופילי מומחים — כל 20 ארנקים")
print("=" * 60)

results = {}
items = list(ALL_WALLETS.items())

# הרצה מקבילית לחיסכון בזמן
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(analyze_wallet, item): item[0] for item in items}
    for future in concurrent.futures.as_completed(futures):
        name = futures[future]
        try:
            result = future.result()
            results[name] = result
        except Exception as e:
            print(f"  ❌ שגיאה ב-{name}: {e}")

# שמירת תוצאות
with open("/home/ubuntu/polymarket-bot-v2/real_profiles.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 60)
print("סיכום — ממוין לפי Win Rate:")
print("=" * 60)
print(f"{'שם':<25} {'Win%':>6} {'ROI%':>8} {'עסקאות':>8} {'סיכון':<8} {'המלצה':<15}")
print("-" * 75)
for name, r in sorted(results.items(), key=lambda x: x[1]['win_rate_pct'], reverse=True):
    emoji = "🔥" if r['win_rate_pct'] >= 85 else ("✅" if r['win_rate_pct'] >= 65 else ("⚠️" if r['win_rate_pct'] >= 50 else "❌"))
    print(f"{emoji} {name:<23} {r['win_rate_pct']:>6.1f} {r['roi_pct']:>8.1f} {r['total_trades']:>8} {r['dominant_risk']:<8} {r['recommendation']:<15}")

print(f"\n✅ נשמר ל-real_profiles.json ({len(results)} פרופילים)")
