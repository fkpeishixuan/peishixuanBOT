import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("请先设置环境变量 BOT_TOKEN")

async def show_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if update.message:
        await update.message.reply_text(
            f"Chat title: {chat.title}\nChat ID: {chat.id}"
        )
    else:
        print(f"Chat title: {chat.title}, Chat ID: {chat.id}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, show_id))
    app.run_polling()

if __name__ == "__main__":
    main()
