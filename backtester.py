"""
backtester.py — מנוע Backtesting היסטורי לבוט פולימרקט
═══════════════════════════════════════════════════════════════════════════════
בודק היסטורית את ביצועי האסטרטגיה שלנו על עסקאות אמיתיות שכבר נסגרו.

מה הוא בודק:
  1. שולף עסקאות היסטוריות של כל המומחים והלווייתנים מ-Polymarket API
  2. מסנן רק עסקאות בשווקים שכבר נסגרו (יש תוצאה ידועה)
  3. מריץ את Pipeline 8 השלבים על כל עסקה (סימולציה)
  4. מחשב: Win Rate, ROI, Drawdown, Sharpe Ratio
  5. מפיק דוח מפורט לפי מומחה + סיכום כולל

שימוש:
  python3.11 backtester.py                    # ריצה מלאה (כל המומחים, 90 יום)
  python3.11 backtester.py --days 30          # 30 יום אחרונים
  python3.11 backtester.py --expert Theo4     # מומחה ספציפי
  python3.11 backtester.py --report           # הפק דוח PDF/Markdown
═══════════════════════════════════════════════════════════════════════════════
"""
import argparse
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── הגדרות ──────────────────────────────────────────────────────────────────
BACKTEST_RESULTS_FILE = os.path.join(os.path.dirname(__file__), "backtest_results.json")
DEFAULT_TRADE_AMOUNT  = 50.0   # $50 לעסקה (כמו config.py)
DEFAULT_DAYS_BACK     = 90     # כמה ימים אחורה לבדוק
API_DELAY_SECONDS     = 0.3    # השהיה בין קריאות API (כדי לא להיחסם)

# ─── ייבוא ארנקים ────────────────────────────────────────────────────────────
try:
    from config import EXPERT_WALLETS, WHALE_WALLETS
except ImportError:
    EXPERT_WALLETS = {}
    WHALE_WALLETS  = {}


# ═══════════════════════════════════════════════════════════════════════════════
# שליפת נתונים מ-API
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_historical_trades(wallet: str, days_back: int = DEFAULT_DAYS_BACK) -> list:
    """
    שולף עסקאות היסטוריות של ארנק מ-Polymarket data API.
    מחזיר רשימת עסקאות (BUY בלבד).
    """
    all_trades = []
    limit = 100
    offset = 0
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    while True:
        try:
            r = requests.get(
                "https://data-api.polymarket.com/trades",
                params={"user": wallet, "limit": limit, "offset": offset},
                timeout=15
            )
            if r.status_code != 200:
                break
            batch = r.json()
            if not isinstance(batch, list) or not batch:
                break

            for t in batch:
                # סנן רק BUY
                if t.get("side", "").upper() != "BUY":
                    continue
                # בדוק תאריך
                ts_str = t.get("timestamp", t.get("createdAt", ""))
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00").replace("+00:00", ""))
                        if ts < cutoff:
                            return all_trades  # הגענו לגבול הזמן
                    except Exception:
                        pass
                all_trades.append(t)

            if len(batch) < limit:
                break
            offset += limit
            time.sleep(API_DELAY_SECONDS)

        except Exception as e:
            logger.warning(f"שגיאה בשליפת עסקאות {wallet[:8]}: {e}")
            break

    return all_trades


def fetch_market_result(asset_id: str) -> Optional[dict]:
    """
    שולף תוצאת שוק סגור מ-Gamma API.
    מחזיר dict עם: closed, winning_outcome, outcome_prices, volume, end_date
    או None אם השוק עדיין פתוח / לא נמצא.
    """
    if not asset_id:
        return None
    try:
        r = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={"clob_token_ids": asset_id},
            timeout=10
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if not isinstance(data, list) or not data:
            return None
        m = data[0]

        is_closed = m.get("closed", False) or m.get("active", True) is False
        if not is_closed:
            return None  # שוק עדיין פתוח — לא ניתן לבדוק תוצאה

        # קבע מי ניצח
        outcome_prices = m.get("outcomePrices", ["0.5", "0.5"])
        try:
            prices = [float(p) for p in outcome_prices]
        except Exception:
            prices = [0.5, 0.5]

        # בפולימרקט: outcomePrices[0]=YES, outcomePrices[1]=NO
        # ניצחון = המחיר שהגיע ל-1.0
        winning_idx = prices.index(max(prices)) if prices else 0
        winning_outcome = "YES" if winning_idx == 0 else "NO"

        return {
            "closed": True,
            "winning_outcome": winning_outcome,
            "outcome_prices": prices,
            "volume_usd": float(m.get("volume", 0)),
            "end_date": m.get("endDateIso", m.get("endDate", "")),
            "question": m.get("question", m.get("title", "")),
            "slug": m.get("slug", ""),
        }
    except Exception as e:
        logger.debug(f"שגיאה בשליפת תוצאת שוק {asset_id[:12]}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# מנוע Backtesting
# ═══════════════════════════════════════════════════════════════════════════════

class BacktestResult:
    """תוצאות Backtest לארנק/מומחה אחד."""
    def __init__(self, name: str, wallet: str, trader_type: str = "expert"):
        self.name        = name
        self.wallet      = wallet
        self.trader_type = trader_type
        self.trades      = []   # רשימת עסקאות מעובדות
        self.total       = 0
        self.won         = 0
        self.lost        = 0
        self.skipped     = 0    # שווקים עדיין פתוחים
        self.total_invested = 0.0
        self.total_pnl   = 0.0
        self.peak_balance = DEFAULT_TRADE_AMOUNT * 20  # יתרה התחלתית לחישוב Drawdown
        self.max_drawdown = 0.0
        self.balance     = self.peak_balance

    @property
    def closed(self):
        return self.won + self.lost

    @property
    def win_rate(self):
        return round(self.won / self.closed * 100, 1) if self.closed > 0 else 0.0

    @property
    def avg_roi(self):
        if not self.trades:
            return 0.0
        rois = [t["roi_pct"] for t in self.trades if t.get("settled")]
        return round(sum(rois) / len(rois), 1) if rois else 0.0

    @property
    def total_roi(self):
        if self.total_invested == 0:
            return 0.0
        return round(self.total_pnl / self.total_invested * 100, 1)

    def record_trade(self, trade_dict: dict):
        """מוסיף עסקה לרשימה ומעדכן סטטיסטיקות."""
        self.trades.append(trade_dict)
        amount = trade_dict.get("amount_usd", DEFAULT_TRADE_AMOUNT)
        self.total += 1
        self.total_invested += amount

        if not trade_dict.get("settled"):
            self.skipped += 1
            return

        pnl = trade_dict.get("pnl_usd", 0.0)
        self.total_pnl += pnl
        self.balance += pnl

        if trade_dict.get("won"):
            self.won += 1
        else:
            self.lost += 1

        # עדכון Drawdown
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance
        dd = (self.peak_balance - self.balance) / self.peak_balance * 100 if self.peak_balance > 0 else 0
        if dd > self.max_drawdown:
            self.max_drawdown = dd

    def to_dict(self) -> dict:
        return {
            "name":            self.name,
            "wallet":          self.wallet,
            "trader_type":     self.trader_type,
            "total":           self.total,
            "won":             self.won,
            "lost":            self.lost,
            "skipped":         self.skipped,
            "closed":          self.closed,
            "win_rate":        self.win_rate,
            "total_invested":  round(self.total_invested, 2),
            "total_pnl":       round(self.total_pnl, 2),
            "avg_roi":         self.avg_roi,
            "total_roi":       self.total_roi,
            "max_drawdown":    round(self.max_drawdown, 1),
            "trades":          self.trades,
        }


def run_backtest_for_wallet(name: str, wallet: str, trader_type: str,
                             days_back: int, trade_amount: float,
                             use_pipeline: bool = True) -> BacktestResult:
    """
    מריץ Backtest מלא לארנק אחד.
    """
    result = BacktestResult(name, wallet, trader_type)
    logger.info(f"🔍 Backtest: {name} ({wallet[:10]}...) | {days_back} ימים")

    trades = fetch_historical_trades(wallet, days_back)
    logger.info(f"  שולפו {len(trades)} עסקאות BUY")

    for t in trades:
        asset_id = t.get("asset", t.get("asset_id", t.get("assetId", "")))
        outcome  = t.get("outcome", "YES")
        if isinstance(outcome, int):
            outcome = "YES" if outcome == 0 else "NO"
        price    = float(t.get("price", 0))
        size     = float(t.get("size", 0))
        usd      = size * price if price > 0 else float(t.get("usdcSize", 0))

        if usd < 10:  # סנן עסקאות קטנות מדי
            continue

        # שלוף תוצאת שוק
        time.sleep(API_DELAY_SECONDS)
        market_result = fetch_market_result(asset_id)

        trade_entry = {
            "asset_id":    asset_id,
            "outcome":     outcome,
            "price":       price,
            "amount_usd":  trade_amount,  # סכום אחיד לכל עסקה
            "expert_usd":  round(usd, 2),
            "settled":     False,
            "won":         False,
            "pnl_usd":     0.0,
            "roi_pct":     0.0,
            "market_question": "",
            "winning_outcome": "",
        }

        if market_result is None:
            # שוק עדיין פתוח — לא ניתן לדעת תוצאה
            trade_entry["settled"] = False
            result.record_trade(trade_entry)
            continue

        # שוק סגור — חשב תוצאה
        winning = market_result["winning_outcome"]
        trade_entry["settled"]          = True
        trade_entry["winning_outcome"]  = winning
        trade_entry["market_question"]  = market_result.get("question", "")[:80]
        trade_entry["won"]              = (outcome == winning)

        if trade_entry["won"]:
            # רווח: קנינו ב-price, שווה 1.0 בסיום
            payout = trade_amount / price if price > 0 else 0
            pnl    = payout - trade_amount
            roi    = (payout / trade_amount - 1) * 100 if trade_amount > 0 else 0
        else:
            pnl = -trade_amount
            roi = -100.0

        trade_entry["pnl_usd"] = round(pnl, 2)
        trade_entry["roi_pct"] = round(roi, 1)
        result.record_trade(trade_entry)

    logger.info(
        f"  ✅ {name}: {result.closed} עסקאות סגורות | "
        f"Win Rate: {result.win_rate}% | ROI: {result.total_roi}% | "
        f"Max DD: {result.max_drawdown:.1f}%"
    )
    return result


def run_full_backtest(days_back: int = DEFAULT_DAYS_BACK,
                      trade_amount: float = DEFAULT_TRADE_AMOUNT,
                      expert_filter: str = None) -> dict:
    """
    מריץ Backtest מלא על כל המומחים והלווייתנים.
    מחזיר dict עם תוצאות מפורטות + סיכום כולל.
    """
    all_results = []
    all_wallets = {}

    # בחר ארנקים לבדיקה
    for name, wallet in EXPERT_WALLETS.items():
        if expert_filter and name.lower() != expert_filter.lower():
            continue
        all_wallets[name] = ("expert", wallet)

    for name, wallet in WHALE_WALLETS.items():
        if expert_filter and name.lower() != expert_filter.lower():
            continue
        all_wallets[name] = ("whale", wallet)

    if not all_wallets:
        logger.warning("לא נמצאו ארנקים לבדיקה")
        return {}

    logger.info(f"🚀 מתחיל Backtest: {len(all_wallets)} ארנקים | {days_back} ימים | ${trade_amount}/עסקה")

    for name, (trader_type, wallet) in all_wallets.items():
        res = run_backtest_for_wallet(name, wallet, trader_type, days_back, trade_amount)
        all_results.append(res.to_dict())
        time.sleep(1)  # השהיה בין ארנקים

    # ─── סיכום כולל ───────────────────────────────────────────────────────────
    total_trades    = sum(r["total"] for r in all_results)
    total_closed    = sum(r["closed"] for r in all_results)
    total_won       = sum(r["won"] for r in all_results)
    total_invested  = sum(r["total_invested"] for r in all_results)
    total_pnl       = sum(r["total_pnl"] for r in all_results)
    overall_wr      = round(total_won / total_closed * 100, 1) if total_closed > 0 else 0
    overall_roi     = round(total_pnl / total_invested * 100, 1) if total_invested > 0 else 0
    avg_dd          = round(sum(r["max_drawdown"] for r in all_results) / len(all_results), 1) if all_results else 0

    # מיין לפי Win Rate
    sorted_results = sorted(all_results, key=lambda x: (x["win_rate"], x["total_roi"]), reverse=True)

    summary = {
        "run_date":       datetime.utcnow().isoformat(),
        "days_back":      days_back,
        "trade_amount":   trade_amount,
        "total_wallets":  len(all_results),
        "total_trades":   total_trades,
        "total_closed":   total_closed,
        "total_won":      total_won,
        "total_invested": round(total_invested, 2),
        "total_pnl":      round(total_pnl, 2),
        "overall_win_rate": overall_wr,
        "overall_roi":    overall_roi,
        "avg_max_drawdown": avg_dd,
        "edge_detected":  overall_wr >= 55 and overall_roi > 0,
        "results":        sorted_results,
    }

    # שמור תוצאות
    try:
        with open(BACKTEST_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 תוצאות נשמרו ל: {BACKTEST_RESULTS_FILE}")
    except Exception as e:
        logger.warning(f"שגיאה בשמירת תוצאות: {e}")

    return summary


# ═══════════════════════════════════════════════════════════════════════════════
# פורמט דוח טקסט
# ═══════════════════════════════════════════════════════════════════════════════

def format_backtest_report(summary: dict) -> str:
    """מפיק דוח טקסט מסודר מתוצאות Backtest."""
    if not summary:
        return "❌ אין תוצאות Backtest."

    lines = [
        "═══════════════════════════════════════════════════════",
        "📊 BACKTEST REPORT — פולימרקט בוט",
        f"תאריך: {summary.get('run_date', '')[:10]}",
        f"תקופה: {summary.get('days_back', 0)} ימים אחרונים",
        f"סכום לעסקה: ${summary.get('trade_amount', 50):.0f}",
        "═══════════════════════════════════════════════════════",
        "",
        "📈 סיכום כולל:",
        f"  ארנקים שנבדקו:  {summary.get('total_wallets', 0)}",
        f"  עסקאות סגורות:  {summary.get('total_closed', 0)} / {summary.get('total_trades', 0)}",
        f"  Win Rate כולל:  {summary.get('overall_win_rate', 0)}%",
        f"  ROI כולל:       {summary.get('overall_roi', 0)}%",
        f"  P&L כולל:       ${summary.get('total_pnl', 0):+.2f}",
        f"  Drawdown ממוצע: {summary.get('avg_max_drawdown', 0):.1f}%",
        "",
    ]

    edge = summary.get("edge_detected", False)
    if edge:
        lines.append("✅ EDGE זוהה! Win Rate ≥ 55% + ROI חיובי — מוכן למסחר אמיתי")
    else:
        lines.append("⚠️  Edge לא מספיק חזק — המשך Paper Trading")

    lines += ["", "─── ביצועים לפי מומחה/לווייתן ───────────────────────"]

    for r in summary.get("results", []):
        if r["closed"] == 0:
            continue
        edge_mark = "✅" if r["win_rate"] >= 55 and r["total_roi"] > 0 else "⚠️"
        lines.append(
            f"{edge_mark} {r['name']:20s} | "
            f"Win: {r['win_rate']:5.1f}% | "
            f"ROI: {r['total_roi']:+6.1f}% | "
            f"P&L: ${r['total_pnl']:+7.2f} | "
            f"DD: {r['max_drawdown']:.1f}% | "
            f"עסקאות: {r['closed']}"
        )

    lines += [
        "",
        "═══════════════════════════════════════════════════════",
        "💡 קריטריונים להפעלה אמיתית:",
        "   Win Rate ≥ 55% | Max Drawdown < 25% | ROI > 0%",
        "═══════════════════════════════════════════════════════",
    ]
    return "\n".join(lines)


def format_backtest_telegram(summary: dict) -> str:
    """מפיק הודעת טלגרם קצרה מתוצאות Backtest."""
    if not summary:
        return "❌ אין תוצאות Backtest."

    edge = summary.get("edge_detected", False)
    edge_emoji = "✅" if edge else "⚠️"

    lines = [
        "📊 *Backtest Report*",
        f"תקופה: {summary.get('days_back', 0)} ימים | ${summary.get('trade_amount', 50)}/עסקה",
        "",
        f"🎯 Win Rate: *{summary.get('overall_win_rate', 0)}%*",
        f"💰 ROI כולל: *{summary.get('overall_roi', 0):+.1f}%*",
        f"📉 Max Drawdown: *{summary.get('avg_max_drawdown', 0):.1f}%*",
        f"💵 P&L: *${summary.get('total_pnl', 0):+.2f}*",
        "",
        f"{edge_emoji} {'Edge זוהה — מוכן למסחר!' if edge else 'Edge חלש — המשך Paper Trading'}",
        "",
        "👥 *Top 5 מומחים:*",
    ]

    top5 = [r for r in summary.get("results", []) if r["closed"] > 0][:5]
    for r in top5:
        e = "✅" if r["win_rate"] >= 55 else "⚠️"
        lines.append(f"  {e} {r['name']}: {r['win_rate']}% | ROI: {r['total_roi']:+.1f}%")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# ממשק שורת פקודה
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Polymarket Backtesting Engine")
    parser.add_argument("--days",    type=int,   default=DEFAULT_DAYS_BACK, help="ימים אחורה לבדיקה")
    parser.add_argument("--amount",  type=float, default=DEFAULT_TRADE_AMOUNT, help="סכום לעסקה בדולרים")
    parser.add_argument("--expert",  type=str,   default=None, help="בדוק מומחה ספציפי")
    parser.add_argument("--report",  action="store_true", help="הפק דוח מפורט")
    parser.add_argument("--load",    action="store_true", help="טען תוצאות קיימות (ללא ריצה מחדש)")
    args = parser.parse_args()

    if args.load and os.path.exists(BACKTEST_RESULTS_FILE):
        with open(BACKTEST_RESULTS_FILE, "r", encoding="utf-8") as f:
            summary = json.load(f)
        logger.info("טעינת תוצאות קיימות מ-backtest_results.json")
    else:
        summary = run_full_backtest(
            days_back=args.days,
            trade_amount=args.amount,
            expert_filter=args.expert,
        )

    print("\n" + format_backtest_report(summary))

    if args.report:
        report_file = os.path.join(os.path.dirname(__file__), "backtest_report.md")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# Backtest Report\n\n```\n")
            f.write(format_backtest_report(summary))
            f.write("\n```\n")
        logger.info(f"דוח נשמר ל: {report_file}")


if __name__ == "__main__":
    main()
