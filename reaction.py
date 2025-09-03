import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

def _get_reaction_state(context: ContextTypes.DEFAULT_TYPE):
    bd = context.bot_data
    if "reactions" not in bd:
        bd["reactions"] = {}
    return bd["reactions"]

def _target_id(v):
    try:
        return v if (isinstance(v, str) and v.startswith("@")) else int(v)
    except Exception:
        return v

async def on_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mr = update.message_reaction
    if not mr:
        return
    reactions = _get_reaction_state(context)
    chat = getattr(mr, "chat", None)
    chat_id = getattr(chat, "id", None)
    if chat_id is None:
        return
    msg_id = mr.message_id
    if chat_id not in reactions:
        reactions[chat_id] = {}
    if msg_id not in reactions[chat_id]:
        reactions[chat_id][msg_id] = {}
    if mr.new_reaction:
        for r in mr.new_reaction:
            e = getattr(r, "emoji", None)
            if not e:
                continue
            reactions[chat_id][msg_id][e] = reactions[chat_id][msg_id].get(e, 0) + 1
    if mr.old_reaction:
        for r in mr.old_reaction:
            e = getattr(r, "emoji", None)
            if not e:
                continue
            reactions[chat_id][msg_id][e] = max(0, reactions[chat_id][msg_id].get(e, 0) - 1)
            if reactions[chat_id][msg_id][e] == 0:
                reactions[chat_id][msg_id].pop(e, None)
    if not reactions[chat_id][msg_id]:
        reactions[chat_id].pop(msg_id, None)
    if not reactions[chat_id]:
        reactions.pop(chat_id, None)
    logger.info(f"reaction update chat={chat_id} msg={msg_id} stats={reactions.get(chat_id, {}).get(msg_id, {})}")

async def cmd_reactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("请先回复一条消息再使用 /reactions")
        return
    reactions = _get_reaction_state(context)
    chat_id = update.effective_chat.id
    msg_id = update.message.reply_to_message.message_id
    if chat_id not in reactions or msg_id not in reactions[chat_id]:
        await update.message.reply_text("这条消息没有统计到 reactions。")
        return
    stats = reactions[chat_id][msg_id]
    total = sum(stats.values())
    lines = [f"{k}: {v}" for k, v in sorted(stats.items(), key=lambda x: (-x[1], x[0]))]
    text = "📊 Reaction 统计：\n" + ("\n".join(lines) if lines else "（无）") + f"\n合计: {total}"
    await update.message.reply_text(text)

async def cmd_topreactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    reactions = _get_reaction_state(context)
    chat_id = update.effective_chat.id
    n = 10
    try:
        if update.message.text:
            parts = update.message.text.strip().split()
            if len(parts) >= 2:
                n = max(1, min(50, int(parts[1])))
    except Exception:
        n = 10
    if chat_id not in reactions or not reactions[chat_id]:
        await update.message.reply_text("当前会话没有统计到 reactions。")
        return
    items = []
    for mid, emap in reactions[chat_id].items():
        total = sum(emap.values())
        items.append((mid, total, emap))
    items.sort(key=lambda t: (-t[1], t[0]))
    items = items[:n]
    lines = []
    for mid, total, emap in items:
        emolist = ", ".join(f"{e}:{c}" for e, c in sorted(emap.items(), key=lambda x: (-x[1], x[0])))
        lines.append(f"message_id={mid} 合计={total} [{emolist}]")
    text = "🏆 本会话 Top Reactions：\n" + ("\n".join(lines) if lines else "（无）")
    await update.message.reply_text(text)

async def cmd_topreactions_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    reactions = _get_reaction_state(context)
    tgt = _target_id(context.bot_data.get("target_channel_id"))
    n = 10
    try:
        if update.message.text:
            parts = update.message.text.strip().split()
            if len(parts) >= 2:
                n = max(1, min(50, int(parts[1])))
    except Exception:
        n = 10
    if tgt not in reactions or not reactions[tgt]:
        await update.message.reply_text("目标频道没有统计到 reactions。")
        return
    items = []
    for mid, emap in reactions[tgt].items():
        total = sum(emap.values())
        items.append((mid, total, emap))
    items.sort(key=lambda t: (-t[1], t[0]))
    items = items[:n]
    lines = []
    for mid, total, emap in items:
        emolist = ", ".join(f"{e}:{c}" for e, c in sorted(emap.items(), key=lambda x: (-x[1], x[0])))
        lines.append(f"message_id={mid} 合计={total} [{emolist}]")
    text = "🏆 目标频道 Top Reactions：\n" + ("\n".join(lines) if lines else "（无）")
    await update.message.reply_text(text)
