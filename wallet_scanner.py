"""
wallet_scanner.py — סורק ומדרג ארנקים אוטומטי בפולימרקט
═══════════════════════════════════════════════════════════════════════════════
מזהה לווייתנים חדשים ומומחים לפני כולם על ידי:

  1. שליפת Top Traders מ-Polymarket Leaderboard API
  2. ניתוח ביצועים: Win Rate, ROI, Total PnL, Avg Trade Size
  3. דירוג לפי ציון מורכב (Composite Score)
  4. השוואה לרשימה הקיימת — זיהוי ארנקים חדשים שכדאי להוסיף
  5. שמירת דוח + שליחה לטלגרם

מריץ אוטומטית פעם בשבוע (ב-_monthly_discovery_loop ב-telegram_bot.py).

שימוש ידני:
  python3.11 wallet_scanner.py                  # סריקה מלאה
  python3.11 wallet_scanner.py --top 20         # Top 20 בלבד
  python3.11 wallet_scanner.py --min-pnl 50000  # רק עם PnL > $50K
═══════════════════════════════════════════════════════════════════════════════
"""
import argparse
import json
import logging
import os
import time
from datetime import datetime
from typing import Optional

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── הגדרות ──────────────────────────────────────────────────────────────────
SCAN_RESULTS_FILE = os.path.join(os.path.dirname(__file__), "wallet_scan_results.json")
API_DELAY         = 0.3   # שניות בין קריאות API
DEFAULT_TOP_N     = 50    # כמה ארנקים מהטופ לסרוק
MIN_TRADES        = 5     # מינימום עסקאות לדירוג
MIN_PNL_USD       = 10_000  # מינימום רווח כולל לשקול הוספה

# ─── ייבוא ארנקים קיימים ─────────────────────────────────────────────────────
try:
    from config import EXPERT_WALLETS, WHALE_WALLETS
    KNOWN_WALLETS = set(list(EXPERT_WALLETS.values()) + list(WHALE_WALLETS.values()))
    KNOWN_NAMES   = set(list(EXPERT_WALLETS.keys()) + list(WHALE_WALLETS.keys()))
except ImportError:
    KNOWN_WALLETS = set()
    KNOWN_NAMES   = set()


# ═══════════════════════════════════════════════════════════════════════════════
# שליפת נתונים
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_leaderboard(limit: int = 100) -> list:
    """
    שולף את ה-Leaderboard מ-Polymarket data API.
    מחזיר רשימת ארנקים עם נתוני ביצועים.
    """
    try:
        r = requests.get(
            "https://data-api.polymarket.com/rankings",
            params={"limit": limit, "offset": 0},
            timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "data" in data:
                return data["data"]
    except Exception as e:
        logger.warning(f"שגיאה בשליפת Leaderboard: {e}")

    # Fallback: נסה endpoint חלופי
    try:
        r = requests.get(
            "https://data-api.polymarket.com/profiles",
            params={"limit": limit, "sortBy": "profitAndLoss", "sortOrder": "DESC"},
            timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return data
    except Exception as e:
        logger.warning(f"שגיאה ב-fallback Leaderboard: {e}")

    return []


def fetch_wallet_stats(wallet: str) -> Optional[dict]:
    """
    שולף סטטיסטיקות מפורטות לארנק ספציפי.
    """
    try:
        r = requests.get(
            f"https://data-api.polymarket.com/profiles/{wallet}",
            timeout=10
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.debug(f"שגיאה בשליפת פרופיל {wallet[:10]}: {e}")

    # Fallback: נסה endpoint חלופי
    try:
        r = requests.get(
            "https://data-api.polymarket.com/trades",
            params={"user": wallet, "limit": 50},
            timeout=10
        )
        if r.status_code == 200:
            trades = r.json()
            if isinstance(trades, list) and trades:
                return _compute_stats_from_trades(wallet, trades)
    except Exception:
        pass

    return None


def _compute_stats_from_trades(wallet: str, trades: list) -> dict:
    """מחשב סטטיסטיקות בסיסיות מרשימת עסקאות."""
    buy_trades = [t for t in trades if t.get("side", "").upper() == "BUY"]
    total_usd  = sum(float(t.get("usdcSize", 0)) for t in buy_trades)
    avg_size   = total_usd / len(buy_trades) if buy_trades else 0
    return {
        "proxyWallet": wallet,
        "pnl":         0,  # לא ניתן לחשב בלי נתוני סגירה
        "numTrades":   len(buy_trades),
        "avgSize":     round(avg_size, 2),
        "_computed":   True,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# חישוב ציון דירוג
# ═══════════════════════════════════════════════════════════════════════════════

def compute_score(wallet_data: dict) -> float:
    """
    מחשב ציון מורכב לארנק (0-100).

    הציון מורכב מ:
      40% — PnL כולל (נורמלי לפי Top 1%)
      30% — Win Rate (אחוז הצלחה)
      20% — ROI (תשואה על ההשקעה)
      10% — מספר עסקאות (אמינות סטטיסטית)
    """
    pnl       = float(wallet_data.get("pnl", wallet_data.get("profitAndLoss", 0)) or 0)
    win_rate  = float(wallet_data.get("winRate", wallet_data.get("win_rate", 0)) or 0)
    roi       = float(wallet_data.get("roi", wallet_data.get("ROI", 0)) or 0)
    num_trades = int(wallet_data.get("numTrades", wallet_data.get("tradesCount", 0)) or 0)

    # נורמליזציה
    pnl_score      = min(pnl / 1_000_000 * 100, 100) if pnl > 0 else 0   # $1M = 100
    win_rate_score = min(win_rate, 100)
    roi_score      = min(roi / 5, 100) if roi > 0 else 0                   # ROI 500% = 100
    trades_score   = min(num_trades / 100 * 100, 100)                      # 100 עסקאות = 100

    composite = (
        pnl_score      * 0.40 +
        win_rate_score * 0.30 +
        roi_score      * 0.20 +
        trades_score   * 0.10
    )
    return round(composite, 1)


def classify_wallet(wallet_data: dict) -> str:
    """מסווג ארנק לפי גודל."""
    pnl = float(wallet_data.get("pnl", wallet_data.get("profitAndLoss", 0)) or 0)
    if pnl >= 5_000_000:
        return "WHALE"
    elif pnl >= 500_000:
        return "BIG_FISH"
    elif pnl >= 50_000:
        return "EXPERT"
    else:
        return "TRADER"


def get_recommendation(wallet_data: dict, score: float) -> str:
    """ממליץ על פעולה לפי הציון."""
    win_rate = float(wallet_data.get("winRate", 0) or 0)
    if score >= 70 and win_rate >= 70:
        return "STRONG_BUY"
    elif score >= 55 and win_rate >= 60:
        return "BUY"
    elif score >= 40 and win_rate >= 50:
        return "WATCH"
    else:
        return "SKIP"


# ═══════════════════════════════════════════════════════════════════════════════
# סריקה מלאה
# ═══════════════════════════════════════════════════════════════════════════════

def run_wallet_scan(top_n: int = DEFAULT_TOP_N,
                    min_pnl: float = MIN_PNL_USD,
                    include_known: bool = False) -> dict:
    """
    מריץ סריקה מלאה של Leaderboard ומדרג ארנקים.

    מחזיר dict עם:
      - ranked_wallets: רשימה מדורגת של כל הארנקים
      - new_discoveries: ארנקים חדשים שלא ברשימה הקיימת
      - upgrade_candidates: ארנקים קיימים שהשתפרו משמעותית
    """
    logger.info(f"🔍 מתחיל סריקת ארנקים | Top {top_n} | Min PnL: ${min_pnl:,.0f}")

    # שלב 1: שלוף Leaderboard
    leaderboard = fetch_leaderboard(limit=top_n * 2)
    if not leaderboard:
        logger.warning("לא ניתן לשלוף Leaderboard")
        return {}

    logger.info(f"  שולפו {len(leaderboard)} ארנקים מה-Leaderboard")

    # שלב 2: עבד כל ארנק
    ranked = []
    for entry in leaderboard[:top_n * 2]:
        wallet = entry.get("proxyWallet", entry.get("address", entry.get("user", "")))
        if not wallet:
            continue

        pnl = float(entry.get("pnl", entry.get("profitAndLoss", 0)) or 0)
        if pnl < min_pnl:
            continue

        num_trades = int(entry.get("numTrades", entry.get("tradesCount", 0)) or 0)
        if num_trades < MIN_TRADES:
            continue

        # חשב ציון
        score = compute_score(entry)
        tier  = classify_wallet(entry)
        rec   = get_recommendation(entry, score)
        is_known = wallet.lower() in {w.lower() for w in KNOWN_WALLETS}

        ranked.append({
            "wallet":      wallet,
            "name":        entry.get("name", entry.get("username", wallet[:10])),
            "pnl_usd":     round(pnl, 2),
            "win_rate":    round(float(entry.get("winRate", 0) or 0), 1),
            "roi":         round(float(entry.get("roi", entry.get("ROI", 0)) or 0), 1),
            "num_trades":  num_trades,
            "avg_size":    round(float(entry.get("avgSize", 0) or 0), 2),
            "score":       score,
            "tier":        tier,
            "recommendation": rec,
            "is_known":    is_known,
            "rank":        0,  # ימולא בהמשך
        })
        time.sleep(API_DELAY)

    # שלב 3: מיין לפי ציון
    ranked.sort(key=lambda x: x["score"], reverse=True)
    for i, r in enumerate(ranked, 1):
        r["rank"] = i

    # שלב 4: זיהוי ארנקים חדשים
    new_discoveries = [r for r in ranked if not r["is_known"] and r["recommendation"] in ("STRONG_BUY", "BUY")]
    upgrade_candidates = [r for r in ranked if r["is_known"] and r["score"] >= 70]

    # שלב 5: שמור תוצאות
    results = {
        "scan_date":          datetime.utcnow().isoformat(),
        "total_scanned":      len(ranked),
        "new_discoveries":    len(new_discoveries),
        "top_n":              top_n,
        "min_pnl":            min_pnl,
        "ranked_wallets":     ranked[:top_n],
        "new_wallets":        new_discoveries,
        "upgrade_candidates": upgrade_candidates,
    }

    try:
        with open(SCAN_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 תוצאות נשמרו ל: {SCAN_RESULTS_FILE}")
    except Exception as e:
        logger.warning(f"שגיאה בשמירת תוצאות: {e}")

    logger.info(
        f"✅ סריקה הושלמה: {len(ranked)} ארנקים | "
        f"{len(new_discoveries)} גילויים חדשים | "
        f"{len(upgrade_candidates)} מועמדים לשדרוג"
    )
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# פורמט דוחות
# ═══════════════════════════════════════════════════════════════════════════════

def format_scan_report(results: dict) -> str:
    """מפיק דוח טקסט מסודר מתוצאות הסריקה."""
    if not results:
        return "❌ אין תוצאות סריקה."

    lines = [
        "═══════════════════════════════════════════════════════",
        "🔍 WALLET SCANNER REPORT — פולימרקט",
        f"תאריך: {results.get('scan_date', '')[:10]}",
        f"ארנקים שנסרקו: {results.get('total_scanned', 0)}",
        f"גילויים חדשים: {results.get('new_discoveries', 0)}",
        "═══════════════════════════════════════════════════════",
        "",
        "🏆 TOP 10 ארנקים (לפי ציון מורכב):",
        f"{'#':>3} {'שם':20} {'PnL':>12} {'WR%':>6} {'ROI%':>7} {'ציון':>6} {'סטטוס':10}",
        "─" * 70,
    ]

    for r in results.get("ranked_wallets", [])[:10]:
        known = "✅ קיים" if r["is_known"] else "🆕 חדש"
        lines.append(
            f"{r['rank']:>3}. {r['name'][:20]:20} "
            f"${r['pnl_usd']:>10,.0f} "
            f"{r['win_rate']:>5.1f}% "
            f"{r['roi']:>6.0f}% "
            f"{r['score']:>5.1f} "
            f"{known}"
        )

    if results.get("new_wallets"):
        lines += [
            "",
            "🆕 גילויים חדשים — ארנקים שכדאי להוסיף:",
            "─" * 70,
        ]
        for r in results["new_wallets"][:5]:
            lines.append(
                f"  🎯 {r['name'][:25]:25} | "
                f"PnL: ${r['pnl_usd']:>10,.0f} | "
                f"Win: {r['win_rate']:.1f}% | "
                f"ציון: {r['score']:.1f} | "
                f"{r['tier']} | {r['recommendation']}"
            )
            lines.append(f"     ארנק: {r['wallet']}")

    lines += [
        "",
        "═══════════════════════════════════════════════════════",
        "💡 הוסף ארנקים חדשים ל-config.py ב-EXPERT_WALLETS/WHALE_WALLETS",
        "═══════════════════════════════════════════════════════",
    ]
    return "\n".join(lines)


def format_scan_telegram(results: dict) -> str:
    """מפיק הודעת טלגרם קצרה מתוצאות הסריקה."""
    if not results:
        return "❌ אין תוצאות סריקה."

    new_count = results.get("new_discoveries", 0)
    emoji = "🆕" if new_count > 0 else "📊"

    lines = [
        f"{emoji} *סריקת ארנקים שבועית*",
        f"תאריך: {results.get('scan_date', '')[:10]}",
        f"נסרקו: {results.get('total_scanned', 0)} ארנקים",
        "",
    ]

    if new_count > 0:
        lines.append(f"🎯 *{new_count} גילויים חדשים!*\n")
        for r in results.get("new_wallets", [])[:3]:
            lines.append(
                f"  🆕 *{r['name']}*\n"
                f"     PnL: ${r['pnl_usd']:,.0f} | Win: {r['win_rate']:.1f}% | "
                f"ציון: {r['score']:.1f}\n"
                f"     `{r['wallet']}`"
            )
    else:
        lines.append("✅ אין ארנקים חדשים משמעותיים השבוע")

    lines += [
        "",
        "🏆 *Top 5 ארנקים:*",
    ]
    for r in results.get("ranked_wallets", [])[:5]:
        known = "✅" if r["is_known"] else "🆕"
        lines.append(f"  {known} {r['name']}: ציון {r['score']:.1f} | Win: {r['win_rate']:.1f}%")

    return "\n".join(lines)


def format_new_wallet_suggestion(wallet_data: dict) -> str:
    """מפיק הצעת הוספה לארנק חדש בפורמט config.py."""
    name   = wallet_data.get("name", "NewWallet")
    wallet = wallet_data.get("wallet", "")
    tier   = wallet_data.get("tier", "EXPERT")
    wr     = wallet_data.get("win_rate", 0)
    roi    = wallet_data.get("roi", 0)
    pnl    = wallet_data.get("pnl_usd", 0)
    score  = wallet_data.get("score", 0)

    section = "WHALE_WALLETS" if tier == "WHALE" else "EXPERT_WALLETS"

    return (
        f"# הוסף ל-{section} ב-config.py:\n"
        f'"{name}": "{wallet}",\n'
        f"# Win Rate: {wr:.1f}% | ROI: {roi:.0f}% | PnL: ${pnl:,.0f} | ציון: {score:.1f}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ממשק שורת פקודה
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Polymarket Auto Wallet Ranking Scanner")
    parser.add_argument("--top",     type=int,   default=DEFAULT_TOP_N, help="כמה ארנקים לסרוק")
    parser.add_argument("--min-pnl", type=float, default=MIN_PNL_USD,   help="מינימום PnL בדולרים")
    parser.add_argument("--load",    action="store_true", help="טען תוצאות קיימות")
    parser.add_argument("--suggest", action="store_true", help="הצע קוד config.py לארנקים חדשים")
    args = parser.parse_args()

    if args.load and os.path.exists(SCAN_RESULTS_FILE):
        with open(SCAN_RESULTS_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
        logger.info("טעינת תוצאות קיימות")
    else:
        results = run_wallet_scan(top_n=args.top, min_pnl=args.min_pnl)

    print("\n" + format_scan_report(results))

    if args.suggest and results.get("new_wallets"):
        print("\n" + "═" * 60)
        print("💡 קוד הוספה לארנקים חדשים:")
        print("═" * 60)
        for w in results["new_wallets"][:5]:
            print(format_new_wallet_suggestion(w))
            print()


if __name__ == "__main__":
    main()
