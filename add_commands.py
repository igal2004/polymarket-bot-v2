"""Helper script to add cmd_compare and cmd_discover to telegram_bot.py"""
import re

with open('/home/ubuntu/polymarket-bot-v2/telegram_bot.py', 'r') as f:
    content = f.read()

# The new commands to add
new_commands = '''
async def cmd_compare(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """השוואת ביצועי מומחים — /p_compare"""
    from dry_run_journal import get_summary
    s = get_summary()
    if s["total"] == 0:
        await update.message.reply_text("אין עסקאות ביומן עדיין.")
        return

    by_expert = s["by_expert"]
    if not by_expert:
        await update.message.reply_text("אין נתוני מומחים עדיין.")
        return

    sorted_experts = sorted(by_expert.items(), key=lambda x: x[1].get("avg_roi", 0), reverse=True)

    lines = ["\U0001f4ca *השוואת מומחים \u2014 לפי ROI*\n"]
    medals = ["\U0001f947", "\U0001f948", "\U0001f949"]
    for rank, (exp, data) in enumerate(sorted_experts, 1):
        medal = medals[rank-1] if rank <= 3 else f"{rank}."
        closed = data["won"] + data["lost"]
        wr = round(data["won"] / closed * 100, 0) if closed > 0 else 0
        pnl = data["pnl"]
        pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
        status = "\u2705" if data["avg_roi"] > 0 else "\u274c"
        lines.append(
            f"{medal} *{exp}*\n"
            f"   ROI: {status} {data['avg_roi']:.1f}% | הצלחה: {int(wr)}%\n"
            f"   עסקאות: {data['total']} | פתוחות: {data['open']} | {pnl_str}\n"
        )

    lines.append("/p\\_dryrun \u2014 סיכום מלא")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_discover(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """סריקת מומחים חדשים — /p_discover"""
    await update.message.reply_text(
        "\U0001f50d *סורק מומחים חדשים...* (זה עשוי לקחת 15 שניות)",
        parse_mode="Markdown"
    )
    try:
        from market_analysis import discover_top_traders
        import asyncio as _asyncio
        candidates = await _asyncio.get_event_loop().run_in_executor(None, discover_top_traders)

        if not candidates:
            await update.message.reply_text(
                "\U0001f50d לא נמצאו מועמדים חדשים העומדים בקריטריונים."
            )
            return

        lines = ["\U0001f50d *מומחים חדשים שנמצאו*\n"]
        for c in candidates:
            lines.append(
                f"  \U0001f195 *{c['name']}*\n"
                f"    \U0001f4b0 רווח: ${c['pnl']:,.0f} | \U0001f3af הצלחה: {c['win_rate']:.0f}%\n"
                f"    \U0001f4b3 כתובת: `{c['wallet']}`\n"
            )
        lines.append("\nלהוספת מומחה למעקב — עדכן את config.py ב-EXPERT\\_WALLETS")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"שגיאה בסריקה: {e}")

'''

# Insert before "# ─── Core Logic ──────────────────────────────────────────────────────────"
marker = '# ─── Core Logic ──────────────────────────────────────────────────────────'
if marker in content:
    content = content.replace(marker, new_commands + '\n' + marker)
    print("Commands added successfully")
else:
    print("Marker not found!")

# Also register the commands in main()
register_marker = '    _ptb_app.add_handler(CommandHandler("p_reset_dryrun", cmd_reset_dryrun))'
register_new = '''    _ptb_app.add_handler(CommandHandler("p_reset_dryrun", cmd_reset_dryrun))
    _ptb_app.add_handler(CommandHandler("p_compare", cmd_compare))
    _ptb_app.add_handler(CommandHandler("p_discover", cmd_discover))'''

if register_marker in content and 'p_compare' not in content:
    content = content.replace(register_marker, register_new)
    print("Commands registered in main()")

with open('/home/ubuntu/polymarket-bot-v2/telegram_bot.py', 'w') as f:
    f.write(content)

print("Done!")
