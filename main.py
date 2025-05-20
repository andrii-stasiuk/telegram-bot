import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackContext,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Структура: {chat_id: set(user_id)}
user_ids = {}

# Flask App
app = Flask(__name__)
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Зберігаємо користувача при будь-якому тексті
async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not chat or not user:
        print("❌ Немає чату або користувача в update")
        return

    chat_id = chat.id
    user_id = user.id

    if chat_id not in user_ids:
        user_ids[chat_id] = set()
    user_ids[chat_id].add(user_id)

    print(f"✅ Збережено user_id {user_id} у чаті {chat_id}")

# Тегати всіх командою /all
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in user_ids or not user_ids[chat_id]:
        await update.message.reply_text("Немає збережених користувачів.")
        return

    mentions = [f"[User](tg://user?id={uid})" for uid in user_ids[chat_id]]
    chunks = [mentions[i:i + 10] for i in range(0, len(mentions), 10)]

    for group in chunks:
        await update.message.reply_text(" ".join(group), parse_mode="Markdown")

# Діагностика: лог усіх типів оновлень
async def debug_all(update: Update, context: CallbackContext):
    print("🧩 DEBUG UPDATE:", update.to_dict())

# Додаємо хендлери
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_user))
telegram_app.add_handler(CommandHandler("all", tag_all))
telegram_app.add_handler(MessageHandler(filters.ALL, debug_all))  # для діагностики

# Flask вебхук
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

@app.route("/webhook", methods=["POST"])
def webhook():
    update_data = request.get_json(force=True)
    print("📥 RAW update from Telegram:", update_data)

    update = Update.de_json(update_data, telegram_app.bot)

    future = asyncio.run_coroutine_threadsafe(
        telegram_app.process_update(update),
        loop
    )

    try:
        future.result(timeout=10)
    except Exception as e:
        print(f"❌ Помилка обробки update: {e}")

    return "OK"

# Запуск
if __name__ == "__main__":
    loop.run_until_complete(telegram_app.bot.delete_webhook())
    loop.run_until_complete(telegram_app.bot.set_webhook(WEBHOOK_URL))
    print(f"🚀 Webhook встановлено: {WEBHOOK_URL}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
