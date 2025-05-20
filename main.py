import asyncio
import logging
from flask import Flask, request
from telegram import Update, ChatMember, ChatMemberUpdated
from telegram.constants import ChatType, ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

import os

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Init ===
TOKEN = os.getenv("BOT_TOKEN")  # 🔒 додай свій токен у Render env vars
WEBHOOK_PATH = "/webhook"

app = Flask(__name__)
telegram_app = Application.builder().token(TOKEN).build()

# === Handlers ===
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    # Перевірка: команда лише для груп
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ Ця команда доступна лише в групах.")
        return

    # Отримання списку учасників (до 200 — обмеження Telegram API)
    try:
        members = []
        async for member in context.bot.get_chat_administrators(chat.id):
            if not member.user.is_bot:
                name = f"@{member.user.username}" if member.user.username else member.user.first_name
                members.append(name)

        if members:
            text = "👥 " + " ".join(members)
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⚠️ Не вдалося отримати список учасників.")
    except Exception as e:
        logger.error(f"❌ Помилка при отриманні учасників: {e}")
        await update.message.reply_text("❌ Сталася помилка.")

telegram_app.add_handler(CommandHandler("all", tag_all))


# === Webhook endpoint ===
@app.post(WEBHOOK_PATH)
def webhook():
    data = request.get_json(force=True)

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

    loop.create_task(handle_update())
    return "OK"
