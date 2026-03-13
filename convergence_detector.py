"""
convergence_detector.py — שיפור 5: זיהוי קונברגנציה של לווייתנים
כאשר 3+ לווייתנים מובילים נכנסים לאותו שוק באותו כיוון תוך 24 שעות —
הפוזיציה מוגדלת אוטומטית פי CONVERGENCE_MULTIPLIER.
"""
import logging
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConvergenceDetector:
    """
    מנגנון זיהוי קונברגנציה: עוקב אחרי כניסות לווייתנים לשווקים.
    כאשר 3+ לווייתנים מובילים נכנסים לאותו שוק + כיוון תוך 24 שעות —
    מסמן את הסיגנל כ-CONVERGENCE ומגדיל את הפוזיציה.
    """

    def __init__(self):
        # market_key -> list of {"name", "outcome", "price", "usd_value", "timestamp"}
        self._market_entries = defaultdict(list)

    def _market_key(self, market_question: str, outcome: str) -> str:
        """מפתח ייחודי לשוק + כיוון."""
        return f"{market_question[:80].strip().lower()}|{outcome.upper()}"

    def record_entry(self, signal: dict):
        """רושם כניסה חדשה של לווייתן לשוק."""
        key = self._market_key(signal.get("market_question", ""), signal.get("outcome", ""))
        self._market_entries[key].append({
            "name":      signal.get("expert_name", ""),
            "outcome":   signal.get("outcome", ""),
            "price":     signal.get("price", 0),
            "usd_value": signal.get("usd_value", 0),
            "timestamp": datetime.utcnow(),
        })
        # ניקוי ישן (מחוץ לחלון הזמן)
        self._cleanup(key)

    def _cleanup(self, key: str):
        """מסיר כניסות ישנות מחוץ לחלון הזמן."""
        from config import CONVERGENCE_WINDOW_HOURS
        cutoff = datetime.utcnow() - timedelta(hours=CONVERGENCE_WINDOW_HOURS)
        self._market_entries[key] = [
            e for e in self._market_entries[key]
            if e["timestamp"] > cutoff
        ]

    def check_convergence(self, signal: dict) -> dict | None:
        """
        בודק האם הסיגנל הנוכחי יוצר קונברגנציה.
        מחזיר dict עם פרטי הקונברגנציה, או None אם אין.
        """
        from config import CONVERGENCE_MIN_WHALES, CONVERGENCE_MULTIPLIER, WHALE_WALLETS

        key     = self._market_key(signal.get("market_question", ""), signal.get("outcome", ""))
        entries = self._market_entries.get(key, [])

        # ספור רק לווייתנים מובילים (לא כל מומחה)
        whale_names   = set(WHALE_WALLETS.keys())
        whale_entries = [e for e in entries if e["name"] in whale_names]

        # הוסף את הסיגנל הנוכחי אם הוא לווייתן
        current_name = signal.get("expert_name", "")
        if current_name in whale_names:
            whale_entries_with_current = whale_entries + [{"name": current_name}]
        else:
            whale_entries_with_current = whale_entries

        unique_whales = set(e["name"] for e in whale_entries_with_current)

        if len(unique_whales) >= CONVERGENCE_MIN_WHALES:
            total_usd = sum(e["usd_value"] for e in entries)
            avg_price = (sum(e["price"] for e in entries) / len(entries)) if entries else signal.get("price", 0)

            return {
                "is_convergence":    True,
                "whale_count":       len(unique_whales),
                "whale_names":       list(unique_whales),
                "total_usd":         total_usd,
                "avg_entry_price":   round(avg_price, 4),
                "multiplier":        CONVERGENCE_MULTIPLIER,
                "alert": (
                    f"🌊🌊🌊 קונברגנציה! {len(unique_whales)} לווייתנים מסכימים!\n"
                    f"לווייתנים: {', '.join(unique_whales)}\n"
                    f"סה\"כ הושקע: ${total_usd:,.0f} | מחיר ממוצע: {avg_price:.3f}\n"
                    f"📈 פוזיציה מוגדלת ×{CONVERGENCE_MULTIPLIER}"
                )
            }

        return None

    def get_convergence_multiplier(self, signal: dict) -> float:
        """מחזיר מכפיל פוזיציה לפי קונברגנציה (1.0 אם אין)."""
        result = self.check_convergence(signal)
        if result:
            return result["multiplier"]
        return 1.0


# Singleton instance
_detector = ConvergenceDetector()

def record_whale_entry(signal: dict):
    """רושם כניסת לווייתן לזיהוי קונברגנציה."""
    _detector.record_entry(signal)

def get_convergence_info(signal: dict) -> dict | None:
    """מחזיר מידע על קונברגנציה אם קיימת."""
    return _detector.check_convergence(signal)

def get_position_multiplier(signal: dict) -> float:
    """מחזיר מכפיל פוזיציה לפי קונברגנציה."""
    return _detector.get_convergence_multiplier(signal)
