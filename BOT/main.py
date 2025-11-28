from telegram.ext import Application, CommandHandler
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8080))

async def start(update, context):
    await update.message.reply_text('✅ הבוט עובד!')

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

print("Starting bot...")
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    webhook_url=f"{WEBHOOK_URL}/telegram"
)
