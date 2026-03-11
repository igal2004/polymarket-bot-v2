"""portfolio.py"""
import requests
import logging
from config import WALLET_ADDRESS, POLYMARKET_GAMMA_URL

logger = logging.getLogger(__name__)

def get_open_positions(wallet_address: str) -> list:
    """שלוף פוזיציות פתוחות."""
    try:
        url = "https://data-api.polymarket.com/positions"
        params = {"user": wallet_address, "sizeThreshold": "0.01"}
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return [p for p in data if float(p.get("size", 0)) > 0]
    except Exception as e:
        logger.warning(f"שגיאה בשליפת פוזיציות: {e}")
    return []

def get_portfolio_summary() -> str:
    """בנה סיכום פורטפוליו."""
    positions = get_open_positions(WALLET_ADDRESS)
    if not positions:
        return "*פורטפוליו*\n\nאין פוזיציות פתוחות כרגע."
    lines = [f"*פורטפוליו — {len(positions)} פוזיציות פתוחות*\n"]
    total_value = 0.0
    for p in positions[:10]:
        title = p.get("title", p.get("market", "שוק"))[:50]
        outcome = p.get("outcome", "?")
        size = float(p.get("size", 0))
        price = float(p.get("currentPrice", p.get("price", 0)))
        value = size * price
        total_value += value
        lines.append(f"• {title}\n  {outcome} | {size:.1f} יחידות @ ${price:.3f} = ${value:.2f}")
    lines.append(f"\n*סה\"כ שווי: ${total_value:.2f}*")
    return "\n".join(lines)
