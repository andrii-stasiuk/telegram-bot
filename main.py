import os
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import asyncio

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Словник: chat_id -> множина user_id
user_ids = {}

# Flask сервер
app_flask = Flask(__name__)

# Telegram Application
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Логування та збереження користувачів
async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    print(f"📨 Повідомлення в чаті {chat.id} від користувача: {user}")

    if user is None or chat is None:
        print("❌ Немає інформації про користувача або чат")
        return

    if chat.id not in user_ids:
        user_ids[chat.id] = set()

    user_ids[chat.id].add(user.id)
    print(f"✅ Додано користувача {user.id} до чату {chat.id}")

# Команда /all — тегати всіх у цьому чаті
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in user_ids or not user_ids[chat_id]:
        await update.message.reply_text("Немає збережених користувачів у цьому чаті.")
        return

    mentions = [f"[User](tg://user?id={uid})" for uid in user_ids[chat_id]]
    chunks = [mentions[i:i+10] for i in range(0, len(mentions), 10)]

    for group in chunks:
        await update.message.reply_text(" ".join(group), parse_mode="Markdown")

# Обробники
telegram_app.add_handler(MessageHandler(filters.TEXT, save_user))
telegram_app.add_handler(CommandHandler("all", tag_all))

# Async loop для Flask
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Вебхук
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
        print(f"❌ Помилка обробки оновлення: {e}")

    return "OK"

# Запуск
if __name__ == "__main__":
    loop.run_until_complete(telegram_app.bot.delete_webhook())
    loop.run_until_complete(telegram_app.bot.set_webhook(WEBHOOK_URL))
    print(f"🚀 Webhook встановлено: {WEBHOOK_URL}")
    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
