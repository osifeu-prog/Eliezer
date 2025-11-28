from telegram.ext import Application, CommandHandler, MessageHandler, filters
import os
import logging

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8080))

async def start(update, context):
    await update.message.reply_text('🚀 הבוט עובד! שלח /help לעזרה.')

async def help_command(update, context):
    await update.message.reply_text('📖 זה בוט דוגמה. שלח /start להתחלה.')

async def echo(update, context):
    await update.message.reply_text(f'אתה אמרת: {update.message.text}')

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    print("Setting webhook...")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/telegram",
        secret_token=None
    )

if __name__ == "__main__":
    main()
