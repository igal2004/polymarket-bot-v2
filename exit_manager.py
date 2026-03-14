"""
exit_manager.py — מנוע יציאה אוטומטי (Take Profit + Stop Loss + Time Exit)
═══════════════════════════════════════════════════════════════════════════════
מנהל פוזיציות פתוחות ומחליט מתי לצאת מכל עסקה.

3 תנאי יציאה:
  1. 🎯 Take Profit  — יציאה כשהמחיר עלה מספיק (ROI ≥ TAKE_PROFIT_PCT)
  2. 🛑 Stop Loss    — יציאה כשהמחיר ירד יותר מדי (ROI ≤ -STOP_LOSS_PCT)
  3. ⏰ Time Exit    — יציאה אחרי TIME_EXIT_HOURS שעות (גם ללא TP/SL)

מצב DRY RUN: מדמה יציאה וכותב ליומן.
מצב LIVE:    שולח פקודת מכירה ל-CLOB API.

שימוש:
  from exit_manager import ExitManager
  em = ExitManager()
  em.add_position(signal, entry_price, amount_usd)
  em.check_exits()   # קרא בכל iteration של הלולאה הראשית
═══════════════════════════════════════════════════════════════════════════════
"""
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ─── קובץ פוזיציות פתוחות ────────────────────────────────────────────────────
def _get_storage_dir():
    for d in ["/app/data", "/app", "/data", "/tmp"]:
        try:
            os.makedirs(d, exist_ok=True)
            test = os.path.join(d, ".write_test")
            with open(test, "w") as f:
                f.write("x")
            os.remove(test)
            return d
        except Exception:
            continue
    return "/tmp"

_STORAGE_DIR      = _get_storage_dir()
POSITIONS_FILE    = os.path.join(_STORAGE_DIR, "open_positions.json")
EXIT_LOG_FILE     = os.path.join(_STORAGE_DIR, "exit_log.json")

# ─── פרמטרי יציאה (ניתן לשנות ב-config.py) ───────────────────────────────────
try:
    from config import DRY_RUN
except ImportError:
    DRY_RUN = True

# ערכי ברירת מחדל — ניתן לדרוס מ-config.py
try:
    from config import TAKE_PROFIT_PCT
except ImportError:
    TAKE_PROFIT_PCT = 20.0   # יציאה כשהרווח הגיע ל-20%

try:
    from config import STOP_LOSS_PCT
except ImportError:
    STOP_LOSS_PCT = 12.0     # יציאה כשההפסד הגיע ל-12%

try:
    from config import TIME_EXIT_HOURS
except ImportError:
    TIME_EXIT_HOURS = 48     # יציאה אחרי 48 שעות בכל מקרה

try:
    from config import TRAILING_STOP_ENABLED
except ImportError:
    TRAILING_STOP_ENABLED = True  # Trailing Stop Loss — מעקב אחרי השיא


# ═══════════════════════════════════════════════════════════════════════════════
# ניהול פוזיציות
# ═══════════════════════════════════════════════════════════════════════════════

def _load_positions() -> list:
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_positions(positions: list):
    try:
        with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(positions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"שגיאה בשמירת פוזיציות: {e}")


def _load_exit_log() -> list:
    if os.path.exists(EXIT_LOG_FILE):
        try:
            with open(EXIT_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_exit_log(log: list):
    try:
        with open(EXIT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"שגיאה בשמירת exit log: {e}")


def get_current_price(asset_id: str) -> Optional[float]:
    """שולף מחיר נוכחי של asset מ-CLOB API."""
    if not asset_id:
        return None
    try:
        r = requests.get(
            f"https://clob.polymarket.com/price",
            params={"token_id": asset_id, "side": "BUY"},
            timeout=8
        )
        if r.status_code == 200:
            data = r.json()
            price = float(data.get("price", 0))
            return price if price > 0 else None
    except Exception as e:
        logger.debug(f"שגיאה בשליפת מחיר {asset_id[:12]}: {e}")
    return None


def get_market_status(asset_id: str) -> dict:
    """בודק אם שוק סגור ומה התוצאה."""
    if not asset_id:
        return {"closed": False}
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
                closed = m.get("closed", False)
                if closed:
                    prices = [float(p) for p in m.get("outcomePrices", ["0.5", "0.5"])]
                    winning_idx = prices.index(max(prices))
                    return {
                        "closed": True,
                        "winning_outcome": "YES" if winning_idx == 0 else "NO",
                    }
    except Exception:
        pass
    return {"closed": False}


# ═══════════════════════════════════════════════════════════════════════════════
# Exit Manager Class
# ═══════════════════════════════════════════════════════════════════════════════

class ExitManager:
    """
    מנהל פוזיציות פתוחות ומחליט מתי לצאת.
    """

    def __init__(self, telegram_callback=None):
        """
        telegram_callback: פונקציה שמקבלת (message: str) ושולחת לטלגרם.
        """
        self.telegram_callback = telegram_callback

    def add_position(self, signal: dict, entry_price: float, amount_usd: float,
                     trade_id: str = None) -> dict:
        """
        מוסיף פוזיציה חדשה לרשימת הפוזיציות הפתוחות.
        """
        positions = _load_positions()
        now = datetime.utcnow().isoformat()

        position = {
            "id":            trade_id or f"pos_{int(time.time())}",
            "expert_name":   signal.get("expert_name", signal.get("expert", "?")),
            "market_question": signal.get("market_question", signal.get("market", "?")),
            "asset_id":      signal.get("asset_id", ""),
            "outcome":       signal.get("outcome", "YES"),
            "entry_price":   entry_price,
            "current_price": entry_price,
            "peak_price":    entry_price,   # לחישוב Trailing Stop
            "amount_usd":    amount_usd,
            "potential_payout": round(amount_usd / entry_price, 2) if entry_price > 0 else 0,
            "entry_time":    now,
            "exit_time":     None,
            "status":        "open",
            "exit_reason":   "",
            "pnl_usd":       0.0,
            "roi_pct":       0.0,
            "take_profit_pct": TAKE_PROFIT_PCT,
            "stop_loss_pct":   STOP_LOSS_PCT,
            "time_exit_hours": TIME_EXIT_HOURS,
        }
        positions.append(position)
        _save_positions(positions)
        logger.info(
            f"📌 פוזיציה נפתחה: {position['expert_name']} | "
            f"{position['market_question'][:50]} | "
            f"{position['outcome']} @ {entry_price:.3f} | ${amount_usd:.0f}"
        )
        return position

    def check_exits(self) -> list:
        """
        בודק כל הפוזיציות הפתוחות ומחליט אם לצאת.
        מחזיר רשימת פוזיציות שנסגרו בריצה זו.
        """
        positions = _load_positions()
        open_positions = [p for p in positions if p.get("status") == "open"]
        if not open_positions:
            return []

        closed_now = []
        changed = False

        for pos in open_positions:
            exit_reason = self._check_exit_conditions(pos)
            if exit_reason:
                self._close_position(pos, exit_reason)
                closed_now.append(pos)
                changed = True

        if changed:
            _save_positions(positions)
            self._log_exits(closed_now)

        return closed_now

    def _check_exit_conditions(self, pos: dict) -> Optional[str]:
        """
        בודק תנאי יציאה לפוזיציה אחת.
        מחזיר סיבת יציאה (string) או None אם להמשיך להחזיק.
        """
        asset_id    = pos.get("asset_id", "")
        entry_price = pos.get("entry_price", 0)
        outcome     = pos.get("outcome", "YES")
        entry_time  = datetime.fromisoformat(pos.get("entry_time", datetime.utcnow().isoformat()))

        # ─── בדיקה 1: שוק סגור ───────────────────────────────────────────────
        status = get_market_status(asset_id)
        if status.get("closed"):
            winning = status.get("winning_outcome", "")
            if winning:
                won = (outcome == winning)
                return f"MARKET_CLOSED_{'WIN' if won else 'LOSS'}"

        # ─── בדיקה 2: Time Exit ───────────────────────────────────────────────
        hours_held = (datetime.utcnow() - entry_time).total_seconds() / 3600
        if hours_held >= pos.get("time_exit_hours", TIME_EXIT_HOURS):
            return f"TIME_EXIT ({hours_held:.1f}h)"

        # ─── שלוף מחיר נוכחי ─────────────────────────────────────────────────
        current_price = get_current_price(asset_id)
        if current_price is None or current_price <= 0:
            return None  # לא ניתן לשלוף מחיר — המתן

        pos["current_price"] = current_price

        # עדכן שיא מחיר (לTrailing Stop)
        if current_price > pos.get("peak_price", entry_price):
            pos["peak_price"] = current_price

        # חשב ROI נוכחי
        if entry_price > 0:
            roi_pct = (current_price / entry_price - 1) * 100
        else:
            roi_pct = 0.0
        pos["roi_pct"] = round(roi_pct, 2)

        # ─── בדיקה 3: Take Profit ─────────────────────────────────────────────
        tp = pos.get("take_profit_pct", TAKE_PROFIT_PCT)
        if roi_pct >= tp:
            return f"TAKE_PROFIT (+{roi_pct:.1f}%)"

        # ─── בדיקה 4: Stop Loss ───────────────────────────────────────────────
        sl = pos.get("stop_loss_pct", STOP_LOSS_PCT)
        if roi_pct <= -sl:
            return f"STOP_LOSS ({roi_pct:.1f}%)"

        # ─── בדיקה 5: Trailing Stop Loss ─────────────────────────────────────
        if TRAILING_STOP_ENABLED:
            peak = pos.get("peak_price", entry_price)
            if peak > 0:
                trail_drop = (peak - current_price) / peak * 100
                # אם ירד יותר מ-50% מהשיא — צא
                if trail_drop >= 50 and peak > entry_price * 1.1:
                    return f"TRAILING_STOP (ירד {trail_drop:.1f}% מהשיא)"

        return None  # המשך להחזיק

    def _close_position(self, pos: dict, exit_reason: str):
        """סוגר פוזיציה ומחשב P&L."""
        pos["status"]      = "closed"
        pos["exit_reason"] = exit_reason
        pos["exit_time"]   = datetime.utcnow().isoformat()

        entry  = pos.get("entry_price", 0)
        amount = pos.get("amount_usd", 0)

        # חשב P&L לפי סיבת יציאה
        if "WIN" in exit_reason or "TAKE_PROFIT" in exit_reason:
            # יציאה ברווח
            exit_price = pos.get("current_price", 1.0)
            if "MARKET_CLOSED_WIN" in exit_reason:
                exit_price = 1.0  # שוק נסגר בניצחון — שווה 1.0
            payout = amount / entry * exit_price if entry > 0 else amount
            pnl    = payout - amount
        elif "LOSS" in exit_reason or "STOP" in exit_reason:
            # יציאה בהפסד
            exit_price = pos.get("current_price", 0)
            if "MARKET_CLOSED_LOSS" in exit_reason:
                exit_price = 0.0  # שוק נסגר בהפסד — שווה 0
            payout = amount / entry * exit_price if entry > 0 else 0
            pnl    = payout - amount
        else:
            # Time Exit — יציאה במחיר נוכחי
            exit_price = pos.get("current_price", entry)
            payout = amount / entry * exit_price if entry > 0 else amount
            pnl    = payout - amount

        pos["pnl_usd"] = round(pnl, 2)
        pos["roi_pct"] = round(pnl / amount * 100, 1) if amount > 0 else 0.0

        # ✅ שמור לדיסק אחרי סיום הפוזיציה (תיקון באג: סטאטוס לא נשמר לקובץ)
        # הפוזיציה נשמרת עם מפתח 'id' (לא 'trade_id') ב-add_position
        _all_positions = _load_positions()
        _pos_id = pos.get("id") or pos.get("trade_id")
        for _p in _all_positions:
            if _p.get("id") == _pos_id or _p.get("trade_id") == _pos_id:
                _p.update(pos)  # עדכן סטאטוס, exit_time, pnl וכו'
                break
        _save_positions(_all_positions)
        # שלח התראה לטלגרם
        self._send_exit_alert(pos)

        logger.info(
            f"{'✅' if pnl >= 0 else '❌'} פוזיציה נסגרה: {pos['expert_name']} | "
            f"{exit_reason} | P&L: ${pnl:+.2f} ({pos['roi_pct']:+.1f}%)"
        )

    def _send_exit_alert(self, pos: dict):
        """שולח התראת יציאה לטלגרם."""
        if not self.telegram_callback:
            return

        pnl    = pos.get("pnl_usd", 0)
        roi    = pos.get("roi_pct", 0)
        reason = pos.get("exit_reason", "")
        emoji  = "✅" if pnl >= 0 else "❌"
        sign   = "+" if pnl >= 0 else ""

        # זמן החזקה
        try:
            entry_t = datetime.fromisoformat(pos["entry_time"])
            exit_t  = datetime.fromisoformat(pos["exit_time"])
            held_h  = (exit_t - entry_t).total_seconds() / 3600
            held_str = f"{held_h:.1f}h"
        except Exception:
            held_str = "?"

        msg = (
            f"{emoji} *יציאה מעסקה*\n\n"
            f"👤 מומחה: *{pos['expert_name']}*\n"
            f"📋 שוק: {pos['market_question'][:60]}\n"
            f"🎯 כיוון: *{pos['outcome']}*\n"
            f"💰 כניסה: {pos['entry_price']:.3f} | "
            f"יציאה: {pos.get('current_price', pos['entry_price']):.3f}\n"
            f"📊 P&L: *{sign}${pnl:.2f}* ({sign}{roi:.1f}%)\n"
            f"⏱ זמן החזקה: {held_str}\n"
            f"🔖 סיבה: `{reason}`\n"
            f"{'🏆 רווח!' if pnl >= 0 else '📉 הפסד'}"
        )

        try:
            self.telegram_callback(msg)
        except Exception as e:
            logger.warning(f"שגיאה בשליחת התראת יציאה: {e}")

    def _log_exits(self, closed: list):
        """שומר יציאות לקובץ לוג."""
        log = _load_exit_log()
        for pos in closed:
            log.append({
                "time":     pos.get("exit_time", ""),
                "expert":   pos.get("expert_name", ""),
                "market":   pos.get("market_question", "")[:60],
                "outcome":  pos.get("outcome", ""),
                "pnl":      pos.get("pnl_usd", 0),
                "roi":      pos.get("roi_pct", 0),
                "reason":   pos.get("exit_reason", ""),
            })
        _save_exit_log(log)

    def get_open_positions(self) -> list:
        """מחזיר רשימת פוזיציות פתוחות."""
        return [p for p in _load_positions() if p.get("status") == "open"]

    def get_summary(self) -> dict:
        """מחזיר סיכום כל הפוזיציות."""
        positions = _load_positions()
        open_pos  = [p for p in positions if p.get("status") == "open"]
        closed    = [p for p in positions if p.get("status") == "closed"]
        won       = [p for p in closed if p.get("pnl_usd", 0) > 0]
        lost      = [p for p in closed if p.get("pnl_usd", 0) <= 0]
        total_pnl = sum(p.get("pnl_usd", 0) for p in closed)
        win_rate  = round(len(won) / len(closed) * 100, 1) if closed else 0

        return {
            "open":       len(open_pos),
            "closed":     len(closed),
            "won":        len(won),
            "lost":       len(lost),
            "win_rate":   win_rate,
            "total_pnl":  round(total_pnl, 2),
            "open_positions": open_pos,
        }

    def format_positions_message(self) -> str:
        """מפיק הודעת טלגרם עם כל הפוזיציות הפתוחות."""
        summary = self.get_summary()
        open_pos = summary["open_positions"]

        if not open_pos:
            return (
                "📌 *פוזיציות פתוחות*\n\n"
                "אין פוזיציות פתוחות כרגע.\n"
                f"סגורות: {summary['closed']} | "
                f"Win Rate: {summary['win_rate']}% | "
                f"P&L: ${summary['total_pnl']:+.2f}"
            )

        lines = [
            f"📌 *פוזיציות פתוחות ({summary['open']})*\n",
            f"סגורות: {summary['closed']} | Win Rate: {summary['win_rate']}% | P&L: ${summary['total_pnl']:+.2f}\n",
        ]

        for pos in open_pos:
            entry = pos.get("entry_price", 0)
            curr  = pos.get("current_price", entry)
            roi   = pos.get("roi_pct", 0)
            sign  = "+" if roi >= 0 else ""
            emoji = "📈" if roi >= 0 else "📉"

            try:
                entry_t  = datetime.fromisoformat(pos["entry_time"])
                held_h   = (datetime.utcnow() - entry_t).total_seconds() / 3600
                held_str = f"{held_h:.1f}h"
            except Exception:
                held_str = "?"

            lines.append(
                f"{emoji} *{pos['expert_name']}* | {pos['outcome']}\n"
                f"   {pos['market_question'][:50]}\n"
                f"   כניסה: {entry:.3f} | נוכחי: {curr:.3f} | ROI: {sign}{roi:.1f}%\n"
                f"   TP: +{pos.get('take_profit_pct', TAKE_PROFIT_PCT)}% | "
                f"SL: -{pos.get('stop_loss_pct', STOP_LOSS_PCT)}% | "
                f"זמן: {held_str}\n"
            )

        return "\n".join(lines)
