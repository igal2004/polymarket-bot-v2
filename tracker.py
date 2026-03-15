"""
tracker.py - The core logic for tracking expert wallets on Polymarket.

שתי רשימות מעקב:
  ACTIVE_WALLETS      — polling שוטף בכל סיבוב (20 ארנקים פעילים)
  WHALE_ALERT_WALLETS — בדיקה מדי 10 סיבובים בלבד; אם חוזרים — התראה חמה!
"""
import logging
import time
import json
import os
import requests
from config import ACTIVE_WALLETS, WHALE_ALERT_WALLETS, MIN_EXPERT_TRADE_USD, POLL_INTERVAL_SECONDS

# תאימות לאחורה — קוד ישן שמשתמש ב-EXPERT_WALLETS / WHALE_WALLETS ימשיך לעבוד
EXPERT_WALLETS = ACTIVE_WALLETS
WHALE_WALLETS  = ACTIVE_WALLETS

logger = logging.getLogger(__name__)

# Use /app (Railway working dir) first, fallback to /tmp
def _get_data_dir():
    for d in ["/app", "/tmp"]:
        if os.path.isdir(d) and os.access(d, os.W_OK):
            return d
    return "/tmp"

DATA_DIR = _get_data_dir()
SEEN_TRADES_FILE = os.path.join(DATA_DIR, "polymarket_seen_trades.json")

# כמה סיבובים בין כל בדיקה של WHALE_ALERT_WALLETS
WHALE_ALERT_CHECK_INTERVAL = 10


def get_recent_trades(wallet: str, limit: int = 20) -> list:
    try:
        r = requests.get(
            "https://data-api.polymarket.com/trades",
            params={"user": wallet, "limit": limit},
            timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"שגיאה בשליפת עסקאות {wallet[:8]}: {e}")
    return []


def get_market_question(asset_id: str, slug: str = "", title: str = "") -> tuple:
    """Returns (question, url, end_date, condition_id)."""
    # Always try asset_id first — it gives us end_date reliably
    if asset_id:
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
                    q = m.get("question", m.get("title", title or "שוק לא ידוע"))
                    s = m.get("slug", slug or "")
                    url = f"https://polymarket.com/event/{s}" if s else "https://polymarket.com"
                    end_date = m.get("endDateIso") or None
                    if not end_date and m.get("endDate"):
                        end_date = str(m["endDate"])[:10]
                    if not end_date and m.get("end_date_iso"):
                        end_date = m["end_date_iso"]
                    if not end_date and m.get("closingTime"):
                        end_date = str(m["closingTime"])[:10]
                    condition_id = m.get("conditionId", "")
                    return q, url, end_date, condition_id
        except Exception:
            pass
    # Fallback: if we have title+slug but no asset_id, try searching by slug
    if slug:
        try:
            r = requests.get(
                "https://gamma-api.polymarket.com/events",
                params={"slug": slug},
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and data:
                    ev = data[0]
                    url = f"https://polymarket.com/event/{slug}"
                    end_date = ev.get("endDate", "")[:10] if ev.get("endDate") else None
                    if not end_date and ev.get("markets"):
                        first_mkt = ev["markets"][0]
                        end_date = first_mkt.get("endDate", "")[:10] if first_mkt.get("endDate") else None
                    q = title or ev.get("title", "שוק לא ידוע")
                    return q, url, end_date, ""
        except Exception:
            pass
    # Last resort
    if title and slug:
        return title, f"https://polymarket.com/event/{slug}", None, None
    return "שוק לא ידוע", "https://polymarket.com", None, None


def _parse_trade(t: dict, name: str) -> dict:
    """Parses a trade dict and returns a signal dict or None."""
    tid = t.get("transactionHash", t.get("id", ""))
    if not tid:
        return None

    side = t.get("side", "BUY").upper()
    if side != "BUY":
        return None

    size = float(t.get("size", 0))
    price = float(t.get("price", 0))
    usd = size * price
    if usd == 0:
        usd = float(t.get("usdcSize", t.get("amount", t.get("cashPayout", 0))))

    if usd < MIN_EXPERT_TRADE_USD:
        return None

    outcome = t.get("outcome", "YES")
    if isinstance(outcome, int):
        outcome = "YES" if outcome == 0 else "NO"

    asset_id = t.get("asset", t.get("asset_id", t.get("assetId", "")))
    title = t.get("title", "")
    slug = t.get("eventSlug", t.get("slug", ""))
    question, url, end_date, condition_id = get_market_question(asset_id, slug=slug, title=title)

    return {
        "trade_id": tid,
        "expert_name": name,
        "market_question": question,
        "market_url": url,
        "asset_id": asset_id,
        "outcome": outcome,
        "price": price,
        "usd_value": usd,
        "size": size,
        "end_date": end_date,
        "condition_id": condition_id or "",
    }


class ExpertTracker:
    def __init__(self, on_new_trade_callback):
        self.callback = on_new_trade_callback
        self.seen_ids = set()
        self._first_run = True
        self._poll_count = 0          # סופר סיבובים לבדיקת WHALE_ALERT_WALLETS
        self._load_seen()

    def _load_seen(self):
        if os.path.exists(SEEN_TRADES_FILE):
            try:
                with open(SEEN_TRADES_FILE, 'r') as f:
                    self.seen_ids = set(json.load(f))
                logger.info(f"טעינת {len(self.seen_ids)} עסקאות ידועות מהדיסק")
                self._first_run = False
            except (json.JSONDecodeError, FileNotFoundError):
                self.seen_ids = set()
        else:
            self.seen_ids = set()

    def _save_seen(self):
        try:
            ids = list(self.seen_ids)[-2000:]
            with open(SEEN_TRADES_FILE, 'w') as f:
                json.dump(ids, f)
        except Exception as e:
            logger.error(f"שגיאה בשמירת seen trades: {e}")

    def _seed_existing_trades(self):
        """
        On first run (no seen_trades file), collect all current trades
        and mark them as seen WITHOUT sending any alerts.
        This prevents flooding on restart.
        """
        logger.info("הפעלה ראשונה — סורק עסקאות קיימות בלי לשלוח התראות...")
        count = 0
        # Seed both active and whale-alert wallets
        all_wallets = {**ACTIVE_WALLETS, **WHALE_ALERT_WALLETS}
        for name, wallet in all_wallets.items():
            try:
                trades = get_recent_trades(wallet, limit=10)
                for t in trades:
                    tid = t.get("transactionHash", t.get("id", ""))
                    if tid:
                        self.seen_ids.add(tid)
                        count += 1
            except Exception as e:
                logger.warning(f"שגיאה בסריקה ראשונית {name}: {e}")
        self._save_seen()
        self._first_run = False
        logger.info(f"סריקה ראשונית הושלמה — {count} עסקאות סומנו כידועות")

    def check_once(self):
        """
        Checks wallets and triggers the callback for new trades.

        סדר בדיקה:
          1. ACTIVE_WALLETS — בכל סיבוב (polling שוטף)
          2. WHALE_ALERT_WALLETS — כל WHALE_ALERT_CHECK_INTERVAL סיבובים
             (לווייתנים היסטוריים שאינם פעילים — התראה חמה אם חוזרים)
        """
        if self._first_run:
            self._seed_existing_trades()
            return

        self._poll_count += 1
        new_trades_found = False

        # ─── שלב 1: POLLING שוטף — ארנקים פעילים בלבד ───────────────────────
        for name, wallet in ACTIVE_WALLETS.items():
            try:
                trades = get_recent_trades(wallet, limit=20)
                for t in trades:
                    tid = t.get("transactionHash", t.get("id", ""))
                    if not tid or tid in self.seen_ids:
                        continue

                    self.seen_ids.add(tid)
                    new_trades_found = True

                    signal = _parse_trade(t, name)
                    if signal is None:
                        continue

                    signal["trader_type"] = "active"
                    logger.info(
                        f"[{name}] עסקה חדשה: {signal['market_question'][:60]} | "
                        f"{signal['outcome']} @ {signal['price']:.3f} | ${signal['usd_value']:.0f}"
                    )
                    self.callback(signal)
                    time.sleep(1)

            except Exception as e:
                logger.warning(f"שגיאה בבדיקת {name}: {e}")

        # ─── שלב 2: WHALE ALERT — בדיקה כל N סיבובים בלבד ──────────────────
        if self._poll_count % WHALE_ALERT_CHECK_INTERVAL == 0:
            logger.debug(f"🐋 בדיקת WHALE_ALERT_WALLETS (סיבוב {self._poll_count})")
            for name, wallet in WHALE_ALERT_WALLETS.items():
                try:
                    trades = get_recent_trades(wallet, limit=5)
                    for t in trades:
                        tid = t.get("transactionHash", t.get("id", ""))
                        if not tid or tid in self.seen_ids:
                            continue

                        self.seen_ids.add(tid)
                        new_trades_found = True

                        signal = _parse_trade(t, name)
                        if signal is None:
                            continue

                        # סמן כ-whale_alert — התראה חמה מיוחדת!
                        signal["trader_type"] = "whale_alert"
                        signal["whale_alert"] = True
                        logger.warning(
                            f"🚨 WHALE ALERT! [{name}] חזר לסחור! "
                            f"{signal['market_question'][:60]} | "
                            f"{signal['outcome']} @ {signal['price']:.3f} | ${signal['usd_value']:.0f}"
                        )
                        self.callback(signal)
                        time.sleep(1)

                except Exception as e:
                    logger.warning(f"שגיאה בבדיקת whale_alert {name}: {e}")

        if new_trades_found:
            self._save_seen()
