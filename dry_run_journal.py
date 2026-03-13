"""
dry_run_journal.py - יומן עסקאות מדומות (DRY RUN) עם מעקב יתרה מדומה ויעילות
"""
import json
import os
import logging
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

# Use /app for Railway persistence (survives restarts), fallback to /tmp
def _get_storage_dir():
    """Find a writable directory that persists across restarts."""
    for d in ["/app/data", "/app", "/data", "/tmp"]:
        try:
            os.makedirs(d, exist_ok=True)
            test_file = os.path.join(d, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            logger.info("DRY RUN storage directory: %s", d)
            return d
        except Exception:
            continue
    return "/tmp"

_STORAGE_DIR = _get_storage_dir()
JOURNAL_FILE = os.path.join(_STORAGE_DIR, "polymarket_dry_run_journal.json")
BALANCE_FILE = os.path.join(_STORAGE_DIR, "polymarket_sim_balance.json")

# Starting simulated balance — matches real wallet at bot launch
INITIAL_SIM_BALANCE = 323.46


def _load():
    if os.path.exists(JOURNAL_FILE):
        try:
            with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save(trades):
    try:
        with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("שגיאה בשמירת יומן: %s", e)


def _send_telegram_backup(trades, balance_data):
    """Send a silent backup of all DRY RUN data to Telegram. Runs in background thread."""
    try:
        import requests as _req
        from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        backup_data = {
            "_backup": True,
            "trades": trades,
            "balance": balance_data
        }
        backup_json = json.dumps(backup_data, ensure_ascii=False)
        # Split into chunks if too long (Telegram max 4096 chars)
        max_len = 3800
        chunks = [backup_json[i:i+max_len] for i in range(0, len(backup_json), max_len)]
        total = len(chunks)
        for idx, chunk in enumerate(chunks, 1):
            part_label = f" ({idx}/{total})" if total > 1 else ""
        text = f"💾 *DRY RUN Backup{part_label}*\n`{chunk}`"
        _req.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text,
                  "parse_mode": "Markdown", "disable_notification": True},
            timeout=10
        )
        logger.info("DRY RUN backup sent to Telegram (%d trades)", len(trades))
    except Exception as e:
        logger.warning("שגיאה בשליחת גיבוי לטלגרם: %s", e)


def _load_balance():
    if os.path.exists(BALANCE_FILE):
        try:
            with open(BALANCE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"balance": INITIAL_SIM_BALANCE, "initial": INITIAL_SIM_BALANCE}


def _save_balance(data):
    try:
        with open(BALANCE_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.warning("שגיאה בשמירת יתרה מדומה: %s", e)


def get_sim_balance():
    """Return current simulated balance."""
    return _load_balance()["balance"]


def record_trade(signal, amount_usd):
    trades = _load()
    price = signal.get("price", 0)

    # Deduct from simulated balance
    bal_data = _load_balance()
    bal_data["balance"] = round(bal_data["balance"] - amount_usd, 2)
    _save_balance(bal_data)

    entry = {
        "id": len(trades) + 1,
        "timestamp": datetime.utcnow().isoformat(),
        "expert": signal.get("expert_name", signal.get("expert", "?")),
        "market": signal.get("market_question", signal.get("market", "?")),
        "outcome": signal.get("outcome", "?"),
        "price": price,
        "amount_usd": amount_usd,
        "potential_payout": round(amount_usd / price, 2) if price > 0 else 0,
        "potential_profit": round((amount_usd / price) - amount_usd, 2) if price > 0 else 0,
        "roi_pct": round(((1 / price) - 1) * 100, 1) if price > 0 else 0,
        "status": "open",
        "result_usd": None,
        "condition_id": signal.get("condition_id", ""),
        "asset_id": signal.get("asset_id", ""),
        "end_date": signal.get("end_date", None),
        "sim_balance_after": bal_data["balance"],
    }
    trades.append(entry)
    _save(trades)
    logger.info("יומן DRY RUN: עסקה #%s נשמרה, יתרה מדומה: $%.2f", entry["id"], bal_data["balance"])
    # Send silent backup to Telegram in background (non-blocking)
    threading.Thread(
        target=_send_telegram_backup,
        args=(trades, bal_data),
        daemon=True
    ).start()
    return entry["id"], bal_data["balance"]


def get_summary():
    trades = _load()
    bal_data = _load_balance()
    if not trades:
        return {
            "total": 0, "open": 0, "won": 0, "lost": 0,
            "total_invested": 0, "total_pnl": 0, "win_rate": 0,
            "by_expert": {}, "trades": [],
            "sim_balance": bal_data["balance"],
            "initial_balance": bal_data["initial"],
            "avg_roi": 0, "best_trade": None, "worst_trade": None,
        }

    total = len(trades)
    open_trades = [t for t in trades if t["status"] == "open"]
    won = [t for t in trades if t["status"] == "won"]
    lost = [t for t in trades if t["status"] == "lost"]
    total_invested = sum(t["amount_usd"] for t in trades)
    total_pnl = sum(t.get("result_usd", 0) or 0 for t in trades if t["status"] != "open")
    closed = len(won) + len(lost)
    win_rate = round((len(won) / closed * 100) if closed > 0 else 0, 1)

    # Efficiency metrics
    avg_roi = round(sum(t.get("roi_pct", 0) for t in trades) / total, 1) if total > 0 else 0
    best_trade = max(trades, key=lambda t: t.get("roi_pct", 0)) if trades else None
    worst_trade = min(trades, key=lambda t: t.get("roi_pct", 0)) if trades else None

    # Potential payout if all open trades win
    potential_upside = sum(t.get("potential_profit", 0) for t in open_trades)

    by_expert = {}
    for t in trades:
        exp = t["expert"]
        if exp not in by_expert:
            by_expert[exp] = {"total": 0, "won": 0, "lost": 0, "open": 0, "invested": 0, "pnl": 0, "avg_roi": 0}
        by_expert[exp]["total"] += 1
        by_expert[exp]["invested"] += t["amount_usd"]
        by_expert[exp]["avg_roi"] = round(
            (by_expert[exp]["avg_roi"] * (by_expert[exp]["total"] - 1) + t.get("roi_pct", 0)) / by_expert[exp]["total"], 1
        )
        if t["status"] == "won":
            by_expert[exp]["won"] += 1
            by_expert[exp]["pnl"] += t.get("result_usd", 0) or 0
        elif t["status"] == "lost":
            by_expert[exp]["lost"] += 1
            by_expert[exp]["pnl"] -= t["amount_usd"]
        else:
            by_expert[exp]["open"] += 1

    return {
        "total": total, "open": len(open_trades), "won": len(won), "lost": len(lost),
        "total_invested": round(total_invested, 2), "total_pnl": round(total_pnl, 2),
        "win_rate": win_rate, "by_expert": by_expert, "trades": trades,
        "sim_balance": bal_data["balance"],
        "initial_balance": bal_data["initial"],
        "avg_roi": avg_roi,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "potential_upside": round(potential_upside, 2),
    }


def format_summary_message():
    s = get_summary()
    if s["total"] == 0:
        return (
            "📋 *יומן DRY RUN*\n\n"
            f"יתרה מדומה: *${s['sim_balance']:.2f}*\n\n"
            "אין עסקאות מדומות עדיין.\nאשר עסקה כדי להתחיל לעקוב."
        )

    pnl_emoji = "📈" if s["total_pnl"] >= 0 else "📉"
    pnl_sign = "+" if s["total_pnl"] >= 0 else ""

    # Balance change
    bal_change = s["sim_balance"] - s["initial_balance"]
    bal_sign = "+" if bal_change >= 0 else ""
    bal_emoji = "📈" if bal_change >= 0 else "📉"

    lines = [
        "📋 *יומן DRY RUN — סיכום ביצועים*\n",
        "💰 *יתרה מדומה:*",
        f"  התחלה: *${s['initial_balance']:.2f}*",
        f"  עכשיו:  *${s['sim_balance']:.2f}* ({bal_emoji} {bal_sign}${bal_change:.2f})",
        "",
        "📊 *סטטיסטיקות:*",
        f"  סה\"כ עסקאות: *{s['total']}*",
        f"  🟡 פתוחות: *{s['open']}* | ✅ זכייה: *{s['won']}* | ❌ הפסד: *{s['lost']}*",
        f"  🎯 אחוז הצלחה: *{s['win_rate']}%*",
        f"  💵 סה\"כ הושקע: *${s['total_invested']:.2f}*",
        f"  {pnl_emoji} רווח/הפסד ממומש: *{pnl_sign}${s['total_pnl']:.2f}*",
        f"  📊 ROI ממוצע לעסקה: *{s['avg_roi']}%*",
    ]

    if s["open"] > 0:
        lines.append(f"  ⚡ פוטנציאל רווח פתוח: *+${s['potential_upside']:.2f}*")

    if s["best_trade"]:
        bt = s["best_trade"]
        lines += [
            "",
            "🏆 *עסקה הטובה ביותר:*",
            f"  {bt['expert']} | {bt['outcome']} @ {bt['price']:.3f} | ROI: {bt.get('roi_pct', 0):.1f}%",
        ]

    lines += ["", "👥 *ביצועים לפי מומחה:*"]
    for exp, data in sorted(s["by_expert"].items(), key=lambda x: x[1]["won"], reverse=True):
        closed2 = data["won"] + data["lost"]
        wr = round(data["won"] / closed2 * 100, 0) if closed2 > 0 else 0
        ep = data["pnl"]
        pnl_s = f"+${ep:.2f}" if ep >= 0 else f"-${abs(ep):.2f}"
        lines.append(
            f"  • *{exp}*: {data['total']} עסקאות | {int(wr)}% הצלחה | {pnl_s} | ROI: {data['avg_roi']}%"
        )

    lines += [
        "",
        "💡 עסקאות פתוחות יסומנו כזכייה/הפסד כשהשוק ייסגר.",
        "\n/p\\_dryrun\\_trades — רשימת כל העסקאות"
    ]
    return "\n".join(lines)


def check_and_settle_open_trades() -> list:
    """
    Checks all open dry-run trades against the Polymarket API.
    If a market is closed, determines win/loss based on the outcome.
    Returns list of settled trade dicts (for sending notifications).
    """
    import requests as _req
    trades = _load()
    open_trades = [t for t in trades if t.get("status") == "open"]
    if not open_trades:
        return []

    settled = []
    changed = False
    bal_data = _load_balance()

    for trade in open_trades:
        asset_id = trade.get("asset_id", "")
        if not asset_id:
            continue
        try:
            r = _req.get(
                "https://gamma-api.polymarket.com/markets",
                params={"clob_token_ids": asset_id},
                timeout=10
            )
            if r.status_code != 200:
                continue
            data = r.json()
            if not isinstance(data, list) or not data:
                continue
            m = data[0]
            is_closed = m.get("closed", False)
            if not is_closed:
                continue
            # Market is closed — determine outcome
            # outcomePrices: ["1", "0"] means first outcome (YES) won
            outcome_prices = m.get("outcomePrices", [])
            outcomes = m.get("outcomes", ["Yes", "No"])
            if isinstance(outcomes, str):
                import json as _json
                try:
                    outcomes = _json.loads(outcomes)
                except Exception:
                    outcomes = ["Yes", "No"]
            if isinstance(outcome_prices, str):
                import json as _json
                try:
                    outcome_prices = _json.loads(outcome_prices)
                except Exception:
                    outcome_prices = []
            # Find which outcome resolved to 1.0 (winner)
            winning_outcome = None
            for i, op in enumerate(outcome_prices):
                try:
                    if float(op) >= 0.99:
                        winning_outcome = outcomes[i] if i < len(outcomes) else None
                        break
                except (ValueError, TypeError):
                    pass
            if winning_outcome is None:
                logger.info(f"Trade #{trade['id']}: market closed but no clear winner yet")
                continue
            # Compare with our outcome
            our_outcome = trade.get("outcome", "").strip().lower()
            won = our_outcome == winning_outcome.strip().lower()
            # Update trade
            idx = next(i for i, t in enumerate(trades) if t["id"] == trade["id"])
            if won:
                payout = trade.get("potential_payout", trade["amount_usd"])
                profit = payout - trade["amount_usd"]
                trades[idx]["status"] = "won"
                trades[idx]["result_usd"] = round(profit, 2)
                trades[idx]["winning_outcome"] = winning_outcome
                bal_data["balance"] = round(bal_data["balance"] + payout, 2)
                logger.info(f"Trade #{trade['id']} WON: +${profit:.2f}")
            else:
                trades[idx]["status"] = "lost"
                trades[idx]["result_usd"] = -trade["amount_usd"]
                trades[idx]["winning_outcome"] = winning_outcome
                logger.info(f"Trade #{trade['id']} LOST: -${trade['amount_usd']:.2f}")
            settled.append(trades[idx])
            changed = True
        except Exception as e:
            logger.warning(f"Error checking trade #{trade['id']}: {e}")
            continue

    if changed:
        _save(trades)
        _save_balance(bal_data)
        threading.Thread(
            target=_send_telegram_backup,
            args=(trades, bal_data),
            daemon=True
        ).start()

    return settled


def format_trades_list():
    trades = _load()
    if not trades:
        return "📋 אין עסקאות מדומות עדיין."
    lines = ["📋 *רשימת עסקאות DRY RUN:*\n"]
    for t in reversed(trades[-20:]):
        status_emoji = {"open": "🟡", "won": "✅", "lost": "❌"}.get(t["status"], "❓")
        date = t["timestamp"][:10]
        roi = t.get("roi_pct", 0)
        end_str = f" | פקיעה: {t['end_date']}" if t.get("end_date") else ""
        lines.append(
            f"{status_emoji} #{t['id']} | {date} | *{t['expert']}*\n"
            f"   {t['outcome']} @ {t['price']:.3f} | ${t['amount_usd']:.2f} | ROI: {roi:.1f}%{end_str}"
        )
    bal = get_sim_balance()
    lines.append(f"\n💰 יתרה מדומה נוכחית: *${bal:.2f}*")
    return "\n".join(lines)


def reset_journal(new_balance: float = INITIAL_SIM_BALANCE) -> dict:
    """מחיקת כל העסקאות ואיפוס היתרה המדומה."""
    try:
        old_trades = _load()
        old_count = len(old_trades)
        # Clear journal
        _save([])
        # Reset balance
        _save_balance({
            "balance": new_balance,
            "initial": new_balance,
            "last_updated": datetime.now().isoformat()
        })
        logger.info(f"Journal reset: deleted {old_count} trades, new balance ${new_balance:.2f}")
        return {"deleted": old_count, "new_balance": new_balance}
    except Exception as e:
        logger.error(f"שגיאה באיפוס יומן: {e}")
        raise
