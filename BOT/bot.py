from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from config import TOKEN
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user = update.effective_user
    logger.info(f"User {user.id} started the bot")
    
    welcome_text = f"""
👋 שלום {user.first_name}!

אני בוט טלגרם לדוגמה. 
אני יכול לעזור עם:

/start - התחל את השיחה
/help - הצג עזרה
    """
    
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    help_text = """
📖 **עזרה - פקודות זמינות:**

/start - התחל את הבוט
/help - הצג הודעה זו

💡 אתה יכול גם לשלוח הודעה רגילה ואני אחזיר אותה.
    """
    await update.message.reply_text(help_text)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user's message"""
    user_message = update.message.text
    logger.info(f"Echoing message from user {update.effective_user.id}: {user_message}")
    await update.message.reply_text(f"📝 אתה אמרת: {user_message}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates"""
    logger.error(f"Exception while handling an update: {context.error}")

def create_application() -> Application:
    """Create and configure the bot application"""
    # Build application
    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    return application
