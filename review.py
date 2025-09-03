import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

def _get_state(context: ContextTypes.DEFAULT_TYPE):
    bd = context.bot_data
    return (
        bd["pending_by_user_msg"],
        bd["pending_by_review_msg"],
        int(bd["review_group_id"]),
        bd["target_channel_id"],
    )

def _target_id(v):
    try:
        return v if (isinstance(v, str) and v.startswith("@")) else int(v)
    except Exception:
        return v

async def group_yes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _group_decision(update, context, approved=True)

async def group_no(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _group_decision(update, context, approved=False)

async def _group_decision(update: Update, context: ContextTypes.DEFAULT_TYPE, approved: bool) -> None:
    msg = update.message
    if not msg or not msg.reply_to_message:
        await msg.reply_text("请对“投稿消息”点『回复』再发送命令。")
        return

    pending_user, pending_review, review_group_id, target_channel_id = _get_state(context)
    review_msg_id = msg.reply_to_message.message_id
    meta = pending_review.get(review_msg_id)
    if not meta:
        await msg.reply_text("没有找到这条投稿（可能已处理或缓存丢失）。")
        return

    text = msg.text or ""
    parts = text.split(maxsplit=1)
    comment_text = parts[1].strip() if len(parts) > 1 else ""

    pending_review.pop(review_msg_id, None)
    pending_user.pop((meta["src_chat_id"], meta["src_message_id"]), None)

    if approved:
        try:
            sign = "" if meta["is_anon"] else (meta.get("from_username") or meta.get("from_name"))
            tail = ""
            if sign:
                tail += f"\n— 投稿人：{sign}"
            if comment_text:
                tail += f"\n小编意见：{comment_text}"

            if meta.get("text"):
                await context.bot.send_message(
                    chat_id=_target_id(target_channel_id),
                    text=meta["text"] + "\n\n" + tail
                )
            elif meta.get("photo_file_id"):
                await context.bot.send_photo(
                    chat_id=_target_id(target_channel_id),
                    photo=meta["photo_file_id"],
                    caption=(meta.get("caption") or "") + "\n\n" + tail
                )
            elif meta.get("video_file_id"):
                await context.bot.send_video(
                    chat_id=_target_id(target_channel_id),
                    video=meta["video_file_id"],
                    caption=(meta.get("caption") or "") + "\n\n" + tail
                )
            elif meta.get("document_file_id"):
                await context.bot.send_document(
                    chat_id=_target_id(target_channel_id),
                    document=meta["document_file_id"],
                    caption=(meta.get("caption") or "") + "\n\n" + tail
                )
            elif meta.get("audio_file_id"):
                await context.bot.send_audio(
                    chat_id=_target_id(target_channel_id),
                    audio=meta["audio_file_id"],
                    caption=(meta.get("caption") or "") + "\n\n" + tail
                )
            elif meta.get("voice_file_id"):
                await context.bot.send_voice(
                    chat_id=_target_id(target_channel_id),
                    voice=meta["voice_file_id"],
                    caption=(meta.get("caption") or "") + "\n\n" + tail
                )
            elif meta.get("animation_file_id"):
                await context.bot.send_animation(
                    chat_id=_target_id(target_channel_id),
                    animation=meta["animation_file_id"],
                    caption=(meta.get("caption") or "") + "\n\n" + tail
                )
            elif meta.get("sticker_file_id"):
                await context.bot.send_sticker(
                    chat_id=_target_id(target_channel_id),
                    sticker=meta["sticker_file_id"]
                )
                if tail:
                    await context.bot.send_message(
                        chat_id=_target_id(target_channel_id),
                        text=tail
                    )
            elif meta.get("video_note_file_id"):
                await context.bot.send_video_note(
                    chat_id=_target_id(target_channel_id),
                    video_note=meta["video_note_file_id"]
                )
                if tail:
                    await context.bot.send_message(
                        chat_id=_target_id(target_channel_id),
                        text=tail
                    )
            else:
                await context.bot.copy_message(
                    chat_id=_target_id(target_channel_id),
                    from_chat_id=meta["src_chat_id"],
                    message_id=meta["src_message_id"]
                )
                if tail:
                    await context.bot.send_message(
                        chat_id=_target_id(target_channel_id),
                        text=tail
                    )
        except Exception as e:
            logger.exception("发布到频道失败: %s", e)
            await msg.reply_text("❌ 发布到频道失败，请检查频道权限或 bot 权限。")
            return

        await msg.reply_text("✅ 已通过并发布到频道。")
        try:
            who = meta.get("from_user_id")
            if who:
                text = "你的投稿已通过并发布到频道！"
                if comment_text:
                    text += f"\n审稿备注：{comment_text}"
                await context.bot.send_message(chat_id=who, text=text)
        except Exception:
            pass
    else:
        await msg.reply_text("已标记不通过。")
        try:
            who = meta.get("from_user_id")
            if who:
                text = "很抱歉，你的投稿未通过。"
                if comment_text:
                    text += f"\n原因：{comment_text}"
                await context.bot.send_message(chat_id=who, text=text)
        except Exception:
            pass
