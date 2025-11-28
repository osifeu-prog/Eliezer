from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN
from crm_manager import crm

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # רישום ב-CRM
    crm.add_user(user.id, user.username, user.first_name)
    crm.create_lead(user.id, "User started the bot")
    
    await update.message.reply_text(f"שלום {user.first_name}! אני הבוט אליעזר. איך אני יכול לעזור?")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("פקודות זמינות:\n/start - התחלה\n/help - עזרה")

def create_bot_application():
    """יוצר ומחזיר את אפליקציית הבוט אך לא מפעיל אותה"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    return application
