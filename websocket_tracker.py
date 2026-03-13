"""
websocket_tracker.py — שיפור 6: מעקב בזמן אמת דרך WebSocket
מנסה להתחבר ל-WebSocket של Polymarket לקבלת עדכונים מיידיים.
אם WebSocket לא זמין — חוזר ל-polling רגיל (fallback).
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── ניסיון WebSocket ─────────────────────────────────────────────────────────
POLYMARKET_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

async def try_websocket_connection(asset_ids: list, on_trade_callback) -> bool:
    """
    מנסה להתחבר ל-WebSocket של Polymarket.
    מחזיר True אם הצליח, False אם לא.
    """
    try:
        import websockets
    except ImportError:
        logger.info("websockets לא מותקן — משתמש ב-polling")
        return False

    try:
        async with websockets.connect(POLYMARKET_WS_URL, ping_interval=30, ping_timeout=10) as ws:
            # Subscribe to all tracked asset_ids
            sub_msg = {
                "auth": {},
                "markets": asset_ids[:20],  # WebSocket מגביל ל-20 שווקים
                "type": "Market"
            }
            await ws.send(json.dumps(sub_msg))
            logger.info(f"✅ WebSocket מחובר — מאזין ל-{len(asset_ids[:20])} שווקים")

            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=60)
                    data = json.loads(msg)
                    if isinstance(data, list):
                        for event in data:
                            if event.get("type") == "trade":
                                on_trade_callback(event)
                except asyncio.TimeoutError:
                    # שלח ping לשמירת החיבור
                    await ws.ping()
                    continue

    except Exception as e:
        logger.warning(f"WebSocket נכשל: {e}")
        return False

    return True


class HybridTracker:
    """
    מעקב היברידי: מנסה WebSocket תחילה, חוזר ל-polling אם לא עובד.
    מפחית latency מ-60 שניות ל-~1 שנייה כשWebSocket זמין.
    """

    def __init__(self, poll_callback):
        """
        poll_callback: הפונקציה הקיימת check_once() מ-ExpertTracker.
        """
        self.poll_callback   = poll_callback
        self.ws_active       = False
        self.last_ws_attempt = 0
        self.ws_retry_hours  = 6  # נסה שוב כל 6 שעות

    def get_poll_interval(self) -> int:
        """
        מחזיר את מרווח ה-polling:
        - אם WebSocket פעיל: 300 שניות (גיבוי בלבד)
        - אם WebSocket לא פעיל: 60 שניות (רגיל)
        """
        from config import POLL_INTERVAL_SECONDS
        if self.ws_active:
            return 300  # 5 דקות — WebSocket מטפל בזמן אמת
        return POLL_INTERVAL_SECONDS

    async def run_websocket_layer(self, asset_ids: list, on_trade_callback):
        """מריץ את שכבת ה-WebSocket ברקע."""
        now = time.time()
        if now - self.last_ws_attempt < self.ws_retry_hours * 3600:
            return  # לא ננסה שוב עדיין

        self.last_ws_attempt = now
        logger.info("מנסה להתחבר ל-WebSocket של Polymarket...")
        success = await try_websocket_connection(asset_ids, on_trade_callback)
        self.ws_active = success
        if not success:
            logger.info(f"WebSocket לא זמין — ממשיך ב-polling כל {self.get_poll_interval()}s")

    def get_status(self) -> dict:
        """מחזיר סטטוס המעקב."""
        return {
            "ws_active":       self.ws_active,
            "poll_interval":   self.get_poll_interval(),
            "detection_mode":  "WebSocket (זמן אמת)" if self.ws_active else f"Polling (כל {self.get_poll_interval()}s)",
            "latency_estimate": "~1 שנייה" if self.ws_active else f"~{self.get_poll_interval()} שניות",
        }
