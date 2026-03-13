#!/usr/bin/env python3.11
"""
fetch_all_profiles.py — שליפת נתונים אמיתיים מ-Polymarket API עבור כל המומחים והלווייתנים
מחשב: win_rate, ROI, dominant_risk, size_tier, total_trades, pnl
"""

import requests
import json
import time
from collections import defaultdict

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


def fetch_positions(wallet: str) -> list:
    """שולף פוזיציות סגורות (settled) עבור ארנק."""
    all_positions = []
    offset = 0
    limit = 500
    while True:
        url = f"https://data-api.polymarket.com/positions?user={wallet}&limit={limit}&offset={offset}&sizeThreshold=0"
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                break
            data = r.json()
            if not data:
                break
            all_positions.extend(data)
            if len(data) < limit:
                break
            offset += limit
            time.sleep(0.3)
        except Exception as e:
            print(f"  שגיאה בשליפת פוזיציות: {e}")
            break
    return all_positions


def fetch_pnl(wallet: str) -> dict:
    """שולף נתוני P&L מסוכמים."""
    url = f"https://data-api.polymarket.com/earnings?user={wallet}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return {}


def classify_price_risk(price: float) -> str:
    """מסווג מחיר לרמת סיכון."""
    if price <= 0.30:
        return "HIGH"
    elif price <= 0.60:
        return "MEDIUM"
    else:
        return "LOW"


def analyze_wallet(name: str, wallet: str) -> dict:
    """מנתח ארנק ומחשב פרופיל מלא."""
    print(f"  שולף: {name} ({wallet[:10]}...)")

    positions = fetch_positions(wallet)
    pnl_data = fetch_pnl(wallet)

    if not positions:
        print(f"    ⚠️  אין נתוני פוזיציות")
        return None

    # חישוב סטטיסטיקות
    settled = [p for p in positions if p.get("curPrice") is not None]
    wins = 0
    losses = 0
    total_invested = 0.0
    total_returned = 0.0
    risk_counts = defaultdict(int)
    trade_sizes = []

    for pos in settled:
        cur_price = float(pos.get("curPrice", 0))
        init_price = float(pos.get("avgPrice", 0) or pos.get("price", 0))
        size = float(pos.get("size", 0))
        cash_balance = float(pos.get("cashBalance", 0) or 0)
        redeemable = float(pos.get("redeemable", 0) or 0)

        # סיווג סיכון לפי מחיר הכניסה
        if init_price > 0:
            risk_counts[classify_price_risk(init_price)] += 1

        # גודל עסקה
        if size > 0:
            trade_sizes.append(size)

        # ניצחון/הפסד לפי מחיר נוכחי
        if cur_price >= 0.95:  # כמעט ודאי ניצחון
            wins += 1
        elif cur_price <= 0.05:  # כמעט ודאי הפסד
            losses += 1

        total_invested += size * init_price if init_price > 0 else size
        total_returned += redeemable + cash_balance

    total_settled = wins + losses
    win_rate = (wins / total_settled * 100) if total_settled > 0 else 0
    roi = ((total_returned - total_invested) / total_invested * 100) if total_invested > 0 else 0

    # dominant risk
    if risk_counts:
        dominant_risk = max(risk_counts, key=risk_counts.get)
    else:
        dominant_risk = "MEDIUM"

    # size tier
    is_whale = name in WHALE_NAMES
    avg_trade = sum(trade_sizes) / len(trade_sizes) if trade_sizes else 0
    if is_whale or avg_trade > 5000:
        size_tier = "WHALE"
    elif avg_trade > 500:
        size_tier = "LARGE"
    else:
        size_tier = "MEDIUM"

    # total PnL from API
    total_pnl = 0
    if pnl_data:
        total_pnl = float(pnl_data.get("profit", 0) or pnl_data.get("pnl", 0) or 0)

    result = {
        "name": name,
        "wallet": wallet,
        "total_positions": len(positions),
        "settled_trades": total_settled,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(win_rate, 1),
        "roi_pct": round(roi, 1),
        "dominant_risk": dominant_risk,
        "risk_counts": dict(risk_counts),
        "size_tier": size_tier,
        "avg_trade_size": round(avg_trade, 2),
        "total_pnl": round(total_pnl, 2),
        "is_whale": is_whale,
    }

    print(f"    ✅ {total_settled} עסקאות | Win: {win_rate:.1f}% | ROI: {roi:.1f}% | Risk: {dominant_risk}")
    return result


# ─── הרצה ────────────────────────────────────────────────────────────────────
print("=" * 60)
print("שליפת פרופילים אמיתיים מ-Polymarket API")
print("=" * 60)

all_results = {}
for name, wallet in ALL_WALLETS.items():
    result = analyze_wallet(name, wallet)
    if result:
        all_results[name] = result
    time.sleep(0.5)

# שמירת תוצאות
with open("/home/ubuntu/polymarket-bot-v2/real_profiles.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 60)
print("סיכום תוצאות:")
print("=" * 60)
print(f"{'שם':<25} {'Win%':>6} {'ROI%':>7} {'עסקאות':>8} {'סיכון':<8} {'Tier':<8}")
print("-" * 65)
for name, r in sorted(all_results.items(), key=lambda x: x[1]['win_rate_pct'], reverse=True):
    print(f"{name:<25} {r['win_rate_pct']:>6.1f} {r['roi_pct']:>7.1f} {r['settled_trades']:>8} {r['dominant_risk']:<8} {r['size_tier']:<8}")

print(f"\n✅ נשמר ל-real_profiles.json")
