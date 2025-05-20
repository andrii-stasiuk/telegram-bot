import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Example: https://your-service.onrender.com/webhook

user_ids = set()
app_flask = Flask(__name__)  # Flask web server

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Handler: save user who sends any message
async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_ids.add(update.effective_user.id)

# Handler: command /all - tag all collected users
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_ids:
        await update.message.reply_text("Немає збережених користувачів для тегання.")
        return

    mentions = [f"[User](tg://user?id={uid})" for uid in user_ids]
    chunks = [mentions[i:i+10] for i in range(0, len(mentions), 10)]
    for group in chunks:
        await update.message.reply_text(" ".join(group), parse_mode="Markdown")

telegram_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), save_user))
telegram_app.add_handler(CommandHandler("all", tag_all))

# Webhook endpoint for Telegram
@app_flask.post("/webhook")
async def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    await telegram_app.process_update(update)
    return "OK"

# Start everything
if __name__ == "__main__":
    import asyncio

    async def main():
        await telegram_app.bot.delete_webhook()
        await telegram_app.bot.set_webhook(WEBHOOK_URL)
        print("Webhook set to:", WEBHOOK_URL)
        app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

    asyncio.run(main())