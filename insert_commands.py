# -*- coding: utf-8 -*-
"""Insert cmd_compare and cmd_discover into telegram_bot.py"""

new_code = '''
async def cmd_compare(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from dry_run_journal import get_summary
    s = get_summary()
    if s["total"] == 0:
        await update.message.reply_text("\u05d0\u05d9\u05df \u05e2\u05e1\u05e7\u05d0\u05d5\u05ea \u05d1\u05d9\u05d5\u05de\u05df \u05e2\u05d3\u05d9\u05d9\u05df.")
        return
    by_expert = s["by_expert"]
    if not by_expert:
        await update.message.reply_text("\u05d0\u05d9\u05df \u05e0\u05ea\u05d5\u05e0\u05d9 \u05de\u05d5\u05de\u05d7\u05d9\u05dd \u05e2\u05d3\u05d9\u05d9\u05df.")
        return
    sorted_experts = sorted(by_expert.items(), key=lambda x: x[1].get("avg_roi", 0), reverse=True)
    header = "\U0001f4ca *\u05d4\u05e9\u05d5\u05d5\u05d0\u05ea \u05de\u05d5\u05de\u05d7\u05d9\u05dd \u2014 \u05dc\u05e4\u05d9 ROI*\\n"
    lines = [header]
    medals = ["\U0001f947", "\U0001f948", "\U0001f949"]
    for rank, (exp, data) in enumerate(sorted_experts, 1):
        medal = medals[rank-1] if rank <= 3 else str(rank) + "."
        closed = data["won"] + data["lost"]
        wr = round(data["won"] / closed * 100, 0) if closed > 0 else 0
        pnl = data["pnl"]
        pnl_str = "+${:.2f}".format(pnl) if pnl >= 0 else "-${:.2f}".format(abs(pnl))
        status_icon = "\u2705" if data["avg_roi"] > 0 else "\u274c"
        line = (
            "{} *{}*\\n"
            "   ROI: {} {:.1f}% | \u05d4\u05e6\u05dc\u05d7\u05d4: {}%\\n"
            "   \u05e2\u05e1\u05e7\u05d0\u05d5\u05ea: {} | \u05e4\u05ea\u05d5\u05d7\u05d5\u05ea: {} | {}\\n"
        ).format(medal, exp, status_icon, data["avg_roi"], int(wr), data["total"], data["open"], pnl_str)
        lines.append(line)
    lines.append("/p\\_dryrun \u2014 \u05e1\u05d9\u05db\u05d5\u05dd \u05de\u05dc\u05d0")
    await update.message.reply_text("\\n".join(lines), parse_mode="Markdown")


async def cmd_discover(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "\U0001f50d *\u05e1\u05d5\u05e8\u05e7 \u05de\u05d5\u05de\u05d7\u05d9\u05dd \u05d7\u05d3\u05e9\u05d9\u05dd...* (\u05d6\u05d4 \u05e2\u05e9\u05d5\u05d9 \u05dc\u05e7\u05d7\u05ea 15 \u05e9\u05e0\u05d9\u05d5\u05ea)",
        parse_mode="Markdown"
    )
    try:
        from market_analysis import discover_top_traders
        import asyncio as _asyncio
        candidates = await _asyncio.get_event_loop().run_in_executor(None, discover_top_traders)
        if not candidates:
            await update.message.reply_text(
                "\U0001f50d \u05dc\u05d0 \u05e0\u05de\u05e6\u05d0\u05d5 \u05de\u05d5\u05e2\u05de\u05d3\u05d9\u05dd \u05d7\u05d3\u05e9\u05d9\u05dd \u05d4\u05e2\u05d5\u05de\u05d3\u05d9\u05dd \u05d1\u05e7\u05e8\u05d9\u05d8\u05e8\u05d9\u05d5\u05e0\u05d9\u05dd."
            )
            return
        lines = ["\U0001f50d *\u05de\u05d5\u05de\u05d7\u05d9\u05dd \u05d7\u05d3\u05e9\u05d9\u05dd \u05e9\u05e0\u05de\u05e6\u05d0\u05d5*\\n"]
        for c in candidates:
            lines.append(
                "  \U0001f195 *{}*\\n"
                "    \U0001f4b0 \u05e8\u05d5\u05d5\u05d7: ${:,.0f} | \U0001f3af \u05d4\u05e6\u05dc\u05d7\u05d4: {:.0f}%\\n"
                "    \U0001f4b3 \u05db\u05ea\u05d5\u05d1\u05ea: `{}`\\n".format(
                    c["name"], c["pnl"], c["win_rate"], c["wallet"]
                )
            )
        lines.append("\\n\u05dc\u05d4\u05d5\u05e1\u05e4\u05ea \u05de\u05d5\u05de\u05d7\u05d4 \u05dc\u05de\u05e2\u05e7\u05d1 \u2014 \u05e2\u05d3\u05db\u05df \u05d0\u05ea config.py \u05d1-EXPERT\\_WALLETS")
        await update.message.reply_text("\\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("\u05e9\u05d2\u05d9\u05d0\u05d4 \u05d1\u05e1\u05e8\u05d9\u05e7\u05d4: {}".format(e))

'''

with open('/home/ubuntu/polymarket-bot-v2/telegram_bot.py', 'r') as f:
    content = f.read()

marker = '# \u2500\u2500\u2500 Core Logic \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500'
if marker in content:
    content = content.replace(marker, new_code + '\n' + marker)
    print("Inserted successfully")
else:
    # Try partial match
    import re
    m = re.search(r'# \u2500+ Core Logic \u2500+', content)
    if m:
        pos = m.start()
        content = content[:pos] + new_code + '\n' + content[pos:]
        print("Inserted via regex")
    else:
        print("ERROR: marker not found")
        print("Searching for Core Logic...")
        idx = content.find('Core Logic')
        print(f"Found at: {idx}")

# Register commands in main
reg_marker = '    _ptb_app.add_handler(CommandHandler("p_reset_dryrun", cmd_reset_dryrun))'
reg_new = '''    _ptb_app.add_handler(CommandHandler("p_reset_dryrun", cmd_reset_dryrun))
    _ptb_app.add_handler(CommandHandler("p_compare", cmd_compare))
    _ptb_app.add_handler(CommandHandler("p_discover", cmd_discover))'''

if reg_marker in content and 'p_compare' not in content:
    content = content.replace(reg_marker, reg_new)
    print("Registered in main()")

with open('/home/ubuntu/polymarket-bot-v2/telegram_bot.py', 'w') as f:
    f.write(content)

print("Done!")
