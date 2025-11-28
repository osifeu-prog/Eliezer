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
    """Handle /start command"""
    user = update.effective_user
    await update.message.reply_text(
        f'👋 שלום {user.first_name}! \n\nהבוט עובד בהצלחה! 🚀'
    )

async def help_command(update, context):
    """Handle /help command"""
    await update.message.reply_text('📖 שלח /start כדי להתחיל')

async def echo(update, context):
    """Echo the user message"""
    await update.message.reply_text(f'אתה אמרת: {update.message.text}')

def main():
    """Main function to start the bot"""
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Start the webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/telegram",
        secret_token=None,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
