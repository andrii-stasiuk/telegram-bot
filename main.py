import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = Flask(__name__)

# Зберігаємо user_id по chat_id
user_ids = {}  # {chat_id: set(user_id)}

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Зберігаємо user_id, хто написав щось у групу
async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type in ["group", "supergroup"]:
        if chat.id not in user_ids:
            user_ids[chat.id] = set()
        user_ids[chat.id].add(user.id)
        print(f"✅ Додано {user.id} до групи {chat.id}")

# /all — тегає усіх, хто щось писав
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.id not in user_ids or not user_ids[chat.id]:
        await update.message.reply_text("Немає збережених користувачів для тегання.")
        return

    mentions = [f"[User](tg://user?id={uid})" for uid in user_ids[chat.id]]
    chunks = [mentions[i:i+10] for i in range(0, len(mentions), 10)]

    for group in chunks:
        await update.message.reply_text(" ".join(group), parse_mode="Markdown")

telegram_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), save_user))
telegram_app.add_handler(CommandHandler("all", tag_all))

@app.post("/webhook")
def webhook():
    data = request.get_data()
    print("📦 request.data:", data)
    print("📡 POST /webhook")

    try:
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        print("📥 RAW update from Telegram:", update.to_dict())
        asyncio.run(telegram_app.process_update(update))
    except Exception as e:
        print("❌ Exception in webhook handler:", e)
    return "OK"

# Запуск
if __name__ == "__main__":
    async def main():
        await telegram_app.bot.delete_webhook()
        await telegram_app.bot.set_webhook(WEBHOOK_URL)
        print("🚀 Webhook встановлено:", WEBHOOK_URL)
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

    asyncio.run(main())
