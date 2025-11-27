from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, Application, CommandHandler, CallbackQueryHandler
from config import Config
from database import SessionLocal
from crm_manager import CRMManager
import os

# Decorator לבדיקת הרשאות מנהל
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ אין לך הרשאה להשתמש בבוט זה.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

@admin_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **ברוך הבא למערכת ה-CRM!**\n\n"
        "אני כאן כדי לנהל את הלידים שמגיעים מהאתר.\n"
        "השתמש בתפריט למטה כדי לנווט."
    )
    keyboard = [
        [InlineKeyboardButton("📊 סטטיסטיקות", callback_data='stats')],
        [InlineKeyboardButton("📥 לידים אחרונים", callback_data='leads')],
        [InlineKeyboardButton("💾 ייצוא לאקסל", callback_data='export')],
        [InlineKeyboardButton("❓ עזרה", callback_data='help')]
    ]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    db = SessionLocal()
    
    if query.data == 'stats':
        stats = CRMManager.get_stats(db)
        text = (
            "📊 **סטטיסטיקות בזמן אמת:**\n\n"
            f"📅 לידים היום: `{stats['today']}`\n"
            f"⏳ ממתינים לטיפול: `{stats['pending']}`\n"
            f"📈 סה\"כ לידים: `{stats['total']}`"
        )
        await query.edit_message_text(text, parse_mode='Markdown')

    elif query.data == 'leads':
        leads = CRMManager.get_recent_leads(db)
        if not leads:
            await query.edit_message_text("📭 אין לידים חדשים במערכת.")
        else:
            text = "📥 **5 לידים אחרונים:**\n\n"
            for lead in leads:
                text += f"👤 {lead.name} | 📱 {lead.phone}\n📝 {lead.notes}\n\n"
            await query.edit_message_text(text)

    elif query.data == 'export':
        await query.message.reply_text("⏳ מכין קובץ נתונים...")
        filename = CRMManager.export_to_csv(db, Config.CSV_FILENAME)
        await query.message.reply_document(document=open(filename, 'rb'), caption="📑 הנה דוח הלידים המלא שלך")
        os.remove(filename) # ניקוי הקובץ

    elif query.data == 'help':
        await query.edit_message_text(
            "🛠 **עזרה ופקודות:**\n\n"
            "/start - תפריט ראשי\n"
            "/stats - צפייה בנתונים\n"
            "הבוט מתעדכן אוטומטית כשנכנס ליד באתר."
        )
    
    db.close()

# פונקציה לשליחת התראה יזומה (כשיש ליד חדש)
async def notify_admins(app: Application, lead_data: dict):
    msg = (
        "🚀 **ליד חדש התקבל!**\n\n"
        f"👤 שם: {lead_data['name']}\n"
        f"📱 טלפון: {lead_data['phone']}\n"
        f"📧 מייל: {lead_data['email']}\n"
        f"📌 הערות: {lead_data['notes']}\n"
        f"🔗 מקור: {lead_data['source']}"
    )
    for admin_id in Config.ADMIN_IDS:
        try:
            await app.bot.send_message(chat_id=admin_id, text=msg, parse_mode='Markdown')
        except Exception as e:
            print(f"Error sending to {admin_id}: {e}")

def setup_bot(app: Application):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    return app
