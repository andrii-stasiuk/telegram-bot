import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
user_ids = set()  # �������� ID ������������, �� ���� ������

# ���� ����� ���� ������� � ������ ���� ID
async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_ids.add(update.effective_user.id)

# ������� /all � ������� ��� ���������� ������������
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_ids:
        await update.message.reply_text("���� ���������� ������������ ��� �������.")
        return

    mentions = []
    for uid in user_ids:
        mentions.append(f"[User](tg://user?id={uid})")

    chunks = [mentions[i:i+10] for i in range(0, len(mentions), 10)]
    for group in chunks:
        await update.message.reply_text(" ".join(group), parse_mode="Markdown")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), save_user))
app.add_handler(CommandHandler("all", tag_all))
print("��� ������...")
app.run_polling()
