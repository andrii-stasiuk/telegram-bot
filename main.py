import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import asyncio

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Тепер user_ids — це словник: {chat_id: set(user_id)}
user_ids = {}

app_flask = Flask(__name__)

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Зберігаємо користувачів по чатах
async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if chat_id not in user_ids:
        user_ids[chat_id] = set()
    user_ids[chat_id].add(user_id)

# Команда /all тегає всіх користувачів, які писали у цьому чаті
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_ids or not user_ids[chat_id]:
        await update.message.reply_text("Немає збережених користувачів для тегання в цьому чаті.")
        return

    mentions = [f"[User](tg://user?id={uid})" for uid in user_ids[chat_id]]
    chunks = [mentions[i:i+10] for i in range(0, len(mentions), 10)]
    for group in chunks:
        await update.message.reply_text(" ".join(group), parse_mode="Markdown")

telegram_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), save_user))
telegram_app.add_handler(CommandHandler("all", tag_all))

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
    loop.run_until_complete(telegram_app.bot.delete_webhook())
    loop.run_until_complete(telegram_app.bot.set_webhook(WEBHOOK_URL))
    print(f"Webhook set to: {WEBHOOK_URL}")

    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
