import os
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    MessageReactionHandler,
    filters,
)
import contribute
import review
import reaction

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

def getenv_or_exit(key: str) -> str:
    val = os.environ.get(key, "")
    if not val:
        raise SystemExit(f"请先设置环境变量 {key}")
    return val

def main() -> None:
    BOT_TOKEN = getenv_or_exit("BOT_TOKEN")
    REVIEW_GROUP_ID = getenv_or_exit("REVIEW_GROUP_ID")
    TARGET_CHANNEL_ID = getenv_or_exit("TARGET_CHANNEL_ID")

    app = Application.builder().token(BOT_TOKEN).build()

    app.bot_data["review_group_id"] = int(REVIEW_GROUP_ID)
    app.bot_data["target_channel_id"] = TARGET_CHANNEL_ID
    app.bot_data["pending_by_user_msg"] = {}
    app.bot_data["pending_by_review_msg"] = {}
    app.bot_data["reactions"] = {}

    app.add_handler(CommandHandler("start", contribute.cmd_start, filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("help", contribute.cmd_help, filters.ChatType.PRIVATE))

    group_filter = filters.Chat(int(REVIEW_GROUP_ID))
    app.add_handler(CommandHandler("yes", review.group_yes, group_filter))
    app.add_handler(CommandHandler("no", review.group_no, group_filter))

    private_incoming = filters.ChatType.PRIVATE & (
        filters.TEXT
        | filters.PHOTO
        | filters.VIDEO
        | filters.ATTACHMENT
        | filters.AUDIO
        | filters.VOICE
        | filters.ANIMATION
        | filters.VIDEO_NOTE
    )
    app.add_handler(MessageHandler(private_incoming, contribute.handle_user_submission))
    app.add_handler(CallbackQueryHandler(contribute.on_choice))

    app.add_handler(MessageReactionHandler(reaction.on_reaction))
    app.add_handler(CommandHandler("reactions", reaction.cmd_reactions))
    app.add_handler(CommandHandler("topreactions", reaction.cmd_topreactions))
    app.add_handler(CommandHandler("topreactions_channel", reaction.cmd_topreactions_channel))

    logger.info("Bot starting…")
    app.run_polling()

if __name__ == "__main__":
    main()
