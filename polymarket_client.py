"""polymarket_client.py"""
import requests
import logging

logger = logging.getLogger(__name__)

def get_wallet_usdc_balance(wallet_address: str) -> float:
    """שלוף יתרת USDC באמצעות Polygon RPC ציבורי."""
    USDC_CONTRACT = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
    padded = wallet_address.lower().replace("0x", "").zfill(64)
    data_hex = "0x70a08231" + padded
    payload = {
        "jsonrpc": "2.0", "method": "eth_call",
        "params": [{"to": USDC_CONTRACT, "data": data_hex}, "latest"],
        "id": 1
    }
    rpc_endpoints = [
        "https://polygon-bor-rpc.publicnode.com",
        "https://1rpc.io/matic",
        "https://polygon.meowrpc.com",
    ]
    for rpc in rpc_endpoints:
        try:
            r = requests.post(rpc, json=payload, timeout=10)
            result = r.json().get("result", "0x0")
            balance = int(result, 16) / 1_000_000
            if balance > 0:
                logger.info(f"יתרה ({rpc}): ${balance:.2f}")
                return balance
        except Exception as e:
            logger.warning(f"RPC {rpc}: {e}")
            continue
    logger.warning("לא ניתן לשלוף יתרה — fallback $323")
    return 323.0

def get_expert_recent_trades(wallet_address: str, limit: int = 20) -> list:
    """שלוף עסקאות אחרונות של מומחה."""
    try:
        url = "https://data-api.polymarket.com/trades"
        params = {"user": wallet_address, "limit": limit}
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.json() if isinstance(r.json(), list) else []
    except Exception as e:
        logger.warning(f"שגיאה בשליפת עסקאות: {e}")
    return []

def get_market_info(condition_id: str) -> dict:
    """שלוף מידע על שוק לפי condition_id."""
    try:
        url = f"https://gamma-api.polymarket.com/markets"
        params = {"condition_id": condition_id}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0]
    except Exception as e:
        logger.warning(f"שגיאה בשליפת שוק: {e}")
    return {}
