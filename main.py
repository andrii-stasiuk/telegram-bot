import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

user_ids = {}  # {chat_id: set(user_id)}

app = Flask(__name__)
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Збір користувачів
async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat and update.effective_user:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        if chat_id not in user_ids:
            user_ids[chat_id] = set()
        user_ids[chat_id].add(user_id)
        print(f"✅ Збережено: {user_id} у чаті {chat_id}")
    else:
        print("❌ Немає даних про користувача або чат")

# Команда /all
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_ids or not user_ids[chat_id]:
        await update.message.reply_text("Немає користувачів для тегання.")
        return

    mentions = [f"[User](tg://user?id={uid})" for uid in user_ids[chat_id]]
    chunks = [mentions[i:i+10] for i in range(0, len(mentions), 10)]
    for group in chunks:
        await update.message.reply_text(" ".join(group), parse_mode="Markdown")

telegram_app.add_handler(MessageHandler(filters.TEXT, save_user))
telegram_app.add_handler(CommandHandler("all", tag_all))

# Async loop для Flask
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

@app.route("/webhook", methods=["POST"])
def webhook():
    update_data = request.get_json(force=True)
    update = Update.de_json(update_data, telegram_app.bot)

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
    print(f"✅ Webhook встановлено: {WEBHOOK_URL}")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
