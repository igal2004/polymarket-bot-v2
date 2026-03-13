"""
market_analysis.py — ניתוח שוק, פערי מחיר, ניתוח AI, וגילוי מומחים חדשים
"""
import logging
import requests
import os
import json
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


def get_current_market_price(asset_id: str) -> float | None:
    """שולף את המחיר הנוכחי של שוק מה-API של Polymarket."""
    if not asset_id:
        return None
    try:
        r = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={"clob_token_ids": asset_id},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                m = data[0]
                # Try multiple price fields
                for field in ["lastTradePrice", "bestAsk", "bestBid", "price"]:
                    val = m.get(field)
                    if val is not None:
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            continue
    except Exception as e:
        logger.warning(f"שגיאה בשליפת מחיר שוק: {e}")
    return None


def analyze_price_gap(expert_price: float, current_price: float, outcome: str) -> dict:
    """
    מנתח את הפרש המחיר בין מחיר קניית המומחה למחיר הנוכחי.
    מחזיר ניתוח האם ההפרש לטובת הקונה או לרעתו.
    """
    if current_price is None or expert_price <= 0:
        return {"gap": None, "analysis": None, "favorable": None}

    gap = current_price - expert_price
    gap_pct = (gap / expert_price) * 100 if expert_price > 0 else 0

    if outcome.upper() == "YES":
        # For YES: lower current price = better entry for us
        if gap < -0.03:  # Current price is 3%+ lower than expert paid
            favorable = True
            if gap_pct < -10:
                analysis = f"✅ מחיר ירד {abs(gap_pct):.1f}% מאז קניית המומחה — כניסה טובה יותר ממנו!"
            else:
                analysis = f"✅ מחיר נמוך ב-{abs(gap_pct):.1f}% ממחיר המומחה — הזדמנות טובה"
        elif gap > 0.05:  # Current price is 5%+ higher than expert paid
            favorable = False
            if gap_pct > 15:
                analysis = f"⚠️ מחיר עלה {gap_pct:.1f}% מאז קניית המומחה — כניסה יקרה יותר"
            else:
                analysis = f"⚠️ מחיר גבוה ב-{gap_pct:.1f}% ממחיר המומחה — שים לב"
        else:
            favorable = True
            analysis = f"✅ מחיר דומה למחיר המומחה (פרש {gap_pct:+.1f}%)"
    else:
        # For NO: higher current price = better entry (NO is cheaper)
        if gap > 0.03:
            favorable = True
            analysis = f"✅ מחיר YES עלה — NO זול יותר ב-{gap_pct:.1f}% ממחיר המומחה"
        elif gap < -0.05:
            favorable = False
            analysis = f"⚠️ מחיר YES ירד — NO יקר יותר ב-{abs(gap_pct):.1f}% ממחיר המומחה"
        else:
            favorable = True
            analysis = f"✅ מחיר דומה למחיר המומחה (פרש {gap_pct:+.1f}%)"

    return {
        "gap": round(gap, 4),
        "gap_pct": round(gap_pct, 1),
        "current_price": current_price,
        "analysis": analysis,
        "favorable": favorable,
    }


def get_ai_risk_analysis(market_question: str, outcome: str, price: float, expert_name: str, usd_value: float) -> str:
    """
    מבקש מ-GPT ניתוח סיכון קצר לעסקה.
    מחזיר מחרוזת קצרה (2-3 שורות) עם הערכת סיכון.
    """
    if not OPENAI_API_KEY:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        )

        prompt = (
            f"ניתוח סיכון קצר לעסקת Polymarket:\n"
            f"שוק: {market_question}\n"
            f"כיוון: {outcome}\n"
            f"מחיר: {price:.3f} ({price*100:.1f}%)\n"
            f"מומחה: {expert_name} | סכום: ${usd_value:.0f}\n\n"
            f"תן ניתוח סיכון קצר ב-2 שורות בעברית:\n"
            f"שורה 1: הערכת הסיכון (נמוך/בינוני/גבוה) ולמה\n"
            f"שורה 2: המלצה קצרה (כן/לא/זהירות)\n"
            f"ענה בפורמט: 🔍 [סיכון]: ... | 💡 [המלצה]: ..."
        )

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"שגיאה בניתוח AI: {e}")
        return None


def get_expert_roi_from_journal(expert_name: str) -> float | None:
    """מחזיר ROI ממוצע של מומחה מהיומן."""
    try:
        from dry_run_journal import get_summary
        s = get_summary()
        by_expert = s.get("by_expert", {})
        if expert_name in by_expert:
            return by_expert[expert_name].get("avg_roi", None)
    except Exception:
        pass
    return None


def calculate_dynamic_trade_amount(expert_name: str, base_amount: float, balance: float | None) -> tuple:
    """
    מחשב סכום עסקה דינמי לפי ביצועי המומחה בעבר.
    מחזיר (amount, explanation).
    """
    roi = get_expert_roi_from_journal(expert_name)

    if roi is None:
        # No history — use base amount
        return base_amount, f"סכום בסיס (אין היסטוריה למומחה)"

    if roi > 50:
        multiplier = 1.5
        label = f"ROI {roi:.0f}% — מומחה מצוין ↑"
    elif roi > 20:
        multiplier = 1.2
        label = f"ROI {roi:.0f}% — מומחה טוב ↑"
    elif roi > 0:
        multiplier = 1.0
        label = f"ROI {roi:.0f}% — מומחה ממוצע"
    elif roi > -20:
        multiplier = 0.7
        label = f"ROI {roi:.0f}% — מומחה חלש ↓"
    else:
        multiplier = 0.5
        label = f"ROI {roi:.0f}% — מומחה גרוע ↓↓"

    amount = base_amount * multiplier
    if balance:
        max_allowed = balance * 0.10
        amount = min(amount, max_allowed)

    return round(amount, 2), label


def discover_top_traders(min_volume_usd: float = 50000, limit: int = 50) -> list:
    """
    סורק את הסוחרים הפעילים ביותר בפוליקמרקט ב-30 הימים האחרונים.
    מחזיר רשימה של מועמדים חדשים שלא נמצאים כבר ברשימת המעקב.
    """
    from config import EXPERT_WALLETS, WHALE_WALLETS
    known_wallets = set(w.lower() for w in {**EXPERT_WALLETS, **WHALE_WALLETS}.values())

    candidates = []
    try:
        # Use Polymarket leaderboard API
        r = requests.get(
            "https://data-api.polymarket.com/activity/leaderboard",
            params={"window": "1m", "limit": limit},
            timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            entries = data if isinstance(data, list) else data.get("data", [])
            for entry in entries:
                wallet = entry.get("proxyWallet") or entry.get("wallet") or entry.get("address", "")
                if not wallet or wallet.lower() in known_wallets:
                    continue

                pnl = float(entry.get("pnl", entry.get("profit", 0)) or 0)
                volume = float(entry.get("volume", entry.get("amount", 0)) or 0)
                win_rate = float(entry.get("winRate", entry.get("win_rate", 0)) or 0)

                if pnl > 5000 and win_rate > 60:
                    candidates.append({
                        "wallet": wallet,
                        "pnl": pnl,
                        "volume": volume,
                        "win_rate": win_rate,
                        "name": entry.get("name", wallet[:8]),
                    })
    except Exception as e:
        logger.warning(f"שגיאה בגילוי סוחרים: {e}")

    # Sort by PnL
    candidates.sort(key=lambda x: x["pnl"], reverse=True)
    return candidates[:10]


def get_open_trades_summary() -> list:
    """מחזיר רשימת עסקאות פתוחות עם מועד פקיעה."""
    try:
        from dry_run_journal import get_summary
        s = get_summary()
        trades = s.get("trades", [])
        open_trades = [t for t in trades if t.get("status") == "open"]
        return open_trades
    except Exception:
        return []
