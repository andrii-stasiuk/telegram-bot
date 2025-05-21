import os
import asyncio
import threading
import time
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://your-service.onrender.com/webhook

app = Flask(__name__)

# Зберігаємо user_ids окремо для кожного чату
user_ids_by_chat = {}

# Створюємо telegram_app з можливістю manual initialization
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# 🧠 Записуємо всіх, хто щось писав
async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if update.effective_chat.type in ["group", "supergroup"]:
        if chat_id not in user_ids_by_chat:
            user_ids_by_chat[chat_id] = set()
        user_ids_by_chat[chat_id].add(user_id)
        print(f"➕ Додано user {user_id} до чату {chat_id}")

# 📣 Команда /all тегне всіх збережених користувачів
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_ids_by_chat or not user_ids_by_chat[chat_id]:
        await update.message.reply_text("Немає збережених користувачів.")
        return

    mentions = [f"[user](tg://user?id={uid})" for uid in user_ids_by_chat[chat_id]]
    chunks = [mentions[i:i + 10] for i in range(0, len(mentions), 10)]

    for group in chunks:
        await update.message.reply_text(" ".join(group), parse_mode="Markdown")

# 🧩 Обробники
telegram_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), save_user))
telegram_app.add_handler(CommandHandler("all", tag_all))

# 🌐 Flask endpoint
@app.post("/webhook")
def webhook():
    data = request.get_json(force=True)
    print("📥 RAW update from Telegram:", data)

    async def handle_update():
        if not telegram_app._initialized:
            await telegram_app.initialize()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        asyncio.create_task(handle_update())
    else:
        loop.run_until_complete(handle_update())

    return "OK"

# ✅ Простий пінг-ендпоінт
@app.route("/ping")
def ping():
    return "pong", 200

# 🕒 Фонове завдання для підтримання активності інстанції
def keep_alive():
    while True:
        try:
            time.sleep(50)
            requests.get(f"{WEBHOOK_URL}/ping")
            print("🔄 Активність: надіслано ping на /ping")
        except Exception as e:
            print(f"⚠️ Ping error: {e}")

# 🟢 Ping endpoint for keeping the service awake
@app.get("/webhook/ping")
def ping():
    print("🔄 Ping received to prevent spin down.")
    return "Pong", 200

# 🚀 Запуск
if __name__ == "__main__":
    # Запускаємо пінг в окремому потоці
    threading.Thread(target=keep_alive, daemon=True).start()

    async def main():
        await telegram_app.initialize()
        await telegram_app.bot.delete_webhook()
        await telegram_app.bot.set_webhook(WEBHOOK_URL)
        print("✅ Webhook встановлено:", WEBHOOK_URL)
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

    asyncio.run(main())
