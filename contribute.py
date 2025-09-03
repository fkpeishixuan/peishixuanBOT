import uuid
import logging
import time
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatType
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "👋 投稿机器人使用说明\n\n"
    "【用户私聊 bot】\n"
    "1) 直接把文本/图片/视频/文件/语音 发给我\n"
    "2) 选择：实名投稿 或 匿名投稿\n"
    "3) 我会将内容提交到审稿群等待审核\n\n"
    "【审稿群内】\n"
    "请对 bot 转发的“投稿消息”点『回复』，然后发送：\n"
    "• /yes 可选评论 —— 通过并发布到频道\n"
    "• /no  可选评论 —— 不通过（会私聊通知投稿者）\n"
)

def _is_private(update: Update) -> bool:
    return update.effective_chat and update.effective_chat.type == ChatType.PRIVATE

def _get_state(context: ContextTypes.DEFAULT_TYPE):
    bd = context.bot_data
    if "last_submission_time" not in bd:
        bd["last_submission_time"] = {}
    return (
        bd["pending_by_user_msg"],
        bd["pending_by_review_msg"],
        int(bd["review_group_id"]),
        bd["target_channel_id"],
        bd["last_submission_time"],
    )

async def cmd_help(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(HELP_TEXT)

async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update) or not update.message:
        return
    await update.message.reply_text("嗨！把你的内容直接发给我即可开始投稿。\n\n" + HELP_TEXT)

async def handle_user_submission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update) or not update.message:
        return

    pending_user, pending_review, review_group_id, _, last_submission_time = _get_state(context)
    msg = update.message
    user = msg.from_user
    now = time.time()

    last_time = last_submission_time.get(user.id)
    if last_time and now - last_time < 600:  # 600 秒 = 10 分钟
        await msg.reply_text("⏳ 请稍候再试，每位用户 10 分钟内只能投稿一次。")
        return
    last_submission_time[user.id] = now

    key = (msg.chat.id, msg.message_id)
    submission_id = str(uuid.uuid4())[:8]
    meta = {
        "submission_id": submission_id,
        "from_user_id": user.id,
        "from_name": (user.full_name or "").strip() or "某用户",
        "from_username": (f"@{user.username}" if user and user.username else None),
        "is_anon": None,
        "src_chat_id": msg.chat.id,
        "src_message_id": msg.message_id,
        "text": msg.text or None,
        "caption": msg.caption or None,
        "photo_file_id": msg.photo[-1].file_id if msg.photo else None,
        "video_file_id": msg.video.file_id if msg.video else None,
        "document_file_id": msg.document.file_id if msg.document else None,
        "audio_file_id": msg.audio.file_id if msg.audio else None,
        "voice_file_id": msg.voice.file_id if msg.voice else None,
        "animation_file_id": msg.animation.file_id if msg.animation else None,
        "sticker_file_id": msg.sticker.file_id if msg.sticker else None,
        "video_note_file_id": msg.video_note.file_id if msg.video_note else None,
    }
    pending_user[key] = meta

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("确定投稿（实名）✔️", callback_data=f"confirm|{msg.chat.id}|{msg.message_id}|sign"),
            InlineKeyboardButton("确定投稿（匿名）✔️", callback_data=f"confirm|{msg.chat.id}|{msg.message_id}|anon"),
        ],
        [InlineKeyboardButton("取消投稿 ❌", callback_data=f"cancel|{msg.chat.id}|{msg.message_id}")]
    ])
    await msg.reply_text("收到！请选择投稿方式：", reply_markup=kb, allow_sending_without_reply=True)

async def on_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()

    try:
        payload = q.data.split("|")
        action = payload[0]
        chat_id = int(payload[1])
        msg_id = int(payload[2])
    except Exception:
        return

    pending_user, pending_review, review_group_id, _, _ = _get_state(context)
    key = (chat_id, msg_id)

    if action == "cancel":
        pending_user.pop(key, None)
        await q.edit_message_text("已取消投稿。")
        return

    if action == "confirm":
        mode = payload[3]
        meta = pending_user.get(key)
        if not meta:
            await q.edit_message_text("这条投稿已失效或不存在。")
            return

        meta["is_anon"] = (mode == "anon")
        try:
            review_msg = await context.bot.copy_message(
                chat_id=review_group_id,
                from_chat_id=meta["src_chat_id"],
                message_id=meta["src_message_id"],
            )
        except Exception as e:
            logger.exception("复制到审稿群失败: %s", e)
            await q.edit_message_text("❌ 提交失败，请稍后重试或联系管理员。")
            return

        explain = (
            f"📝 投稿ID: {meta['submission_id']}\n"
            f"投稿人：{'匿名' if meta['is_anon'] else (meta.get('from_username') or meta.get('from_name'))}\n"
            f"匿名：{'是' if meta['is_anon'] else '否（实名）'}\n\n"
            f"请对【上面那条投稿消息】点“回复”，然后发送：\n"
            f"/yes 可选评论 —— 通过并发布到频道\n"
            f"/no  可选评论 —— 不通过并通知投稿者"
        )
        await context.bot.send_message(
            chat_id=review_group_id,
            text=explain,
            reply_to_message_id=review_msg.message_id,
        )

        meta2 = meta.copy()
        meta2["review_msg_id"] = review_msg.message_id
        pending_review[review_msg.message_id] = meta2

        await q.edit_message_text("✅ 已提交到审稿群，等待审核结果。")
