import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import asyncio

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

user_ids = set()
app_flask = Flask(__name__)

# Ініціалізуємо Application один раз і запускаємо event loop окремо
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Обробники
async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_ids.add(update.effective_user.id)

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

# Створюємо і запускаємо event loop вручну
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

@app_flask.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, telegram_app.bot)

    future = asyncio.run_coroutine_threadsafe(
        telegram_app.process_update(update),
        loop
    )
    try:
        future.result(timeout=10)
    except Exception as e:
        print(f"Error processing update: {e}")

    return "OK"

if __name__ == "__main__":
    # Спочатку налаштовуємо webhook
    loop.run_until_complete(telegram_app.bot.delete_webhook())
    loop.run_until_complete(telegram_app.bot.set_webhook(WEBHOOK_URL))
    print(f"Webhook set to: {WEBHOOK_URL}")

    # Запускаємо Flask сервер
    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
