import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from webhook_handler import WebhookHandler
from crm_manager import CRMManager
from database import DatabaseManager
import json

# הגדרות לוג
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramCRMBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.webhook_url = os.getenv('WEBHOOK_URL')
        self.db = DatabaseManager()
        self.crm = CRMManager(self.db)
        self.webhook_handler = WebhookHandler(self.crm)
        
        # יצירת האפליקציה
        self.application = Application.builder().token(self.token).build()
        
        # הוספת handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """הגדרת כל ה-handlers של הבוט"""
        # handlers לפקודות
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("leads", self.show_leads))
        self.application.add_handler(CommandHandler("stats", self.show_stats))
        
        # handlers להודעות רגילות
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # handlers ל-callbacks
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת start - התחלת שימוש בבוט"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        # שמירת המשתמש במערכת
        self.crm.add_user(user_id, user_name, update.effective_user.username)
        
        keyboard = [
            [InlineKeyboardButton("📊 צפה בלידים", callback_data="view_leads")],
            [InlineKeyboardButton("📈 סטטיסטיקות", callback_data="view_stats")],
            [InlineKeyboardButton("👥 ניהול לקוחות", callback_data="manage_clients")],
            [InlineKeyboardButton("🔄 סנכרון אתר", callback_data="sync_website")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"ברוך הבא {user_name}!\n\n"
            "אני בוט ה-CRM של המשרד שלך. אני יכול לעזור לך:\n"
            "• לנהל לידים מהאתר\n"
            "• לעקוב אחר סטטיסטיקות\n"
            "• לסנכרן עם מערכות חיצוניות\n\n"
            "בחר אפשרות מהתפריט:",
            reply_markup=reply_markup
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת help - הצגת עזרה"""
        help_text = """
🤖 **בוט CRM למשרד פרסום**

**פקודות זמינות:**
/start - התחל שימוש בבוט
/leads - הצג לידים חדשים
/stats - הצג סטטיסטיקות
/help - הצג עזרה זו

**תפקידי הבוט:**
• ניהול לידים אוטומטי מהאתר
• מעקב אחר ביצועי שיווק
• התראות על לידים חדשים
• סנכרון עם מערכות CRM

**סנכרון עם האתר:**
הבוט מקבל לידים אוטומטית מהאתר דרך webhook.
        """
        await update.message.reply_text(help_text)
    
    async def show_leads(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """הצגת הלידים האחרונים"""
        leads = self.crm.get_recent_leads(limit=10)
        
        if not leads:
            await update.message.reply_text("❌ אין לידים חדשים להצגה.")
            return
        
        leads_text = "📋 **לידים אחרונים:**\n\n"
        for lead in leads:
            status_icon = "🟢" if lead['status'] == 'new' else "🟡" if lead['status'] == 'contacted' else "🔴"
            leads_text += f"{status_icon} **שם:** {lead['name']}\n"
            leads_text += f"📞 **טלפון:** {lead['phone']}\n"
            leads_text += f"📧 **אימייל:** {lead['email']}\n"
            leads_text += f"📅 **תאריך:** {lead['created_at']}\n"
            leads_text += f"🏷️ **סטטוס:** {lead['status']}\n"
            leads_text += "─" * 20 + "\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 עדכן סטטוס", callback_data="update_status")],
            [InlineKeyboardButton("📤 ייצוא ל-CSV", callback_data="export_leads")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(leads_text, reply_markup=reply_markup)
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """הצגת סטטיסטיקות"""
        stats = self.crm.get_stats()
        
        stats_text = "📊 **סטטיסטיקות CRM:**\n\n"
        stats_text += f"👥 **סך הכל לידים:** {stats['total_leads']}\n"
        stats_text += f"🟢 **לידים חדשים:** {stats['new_leads']}\n"
        stats_text += f"🟡 **בטיפול:** {stats['contacted_leads']}\n"
        stats_text += f"🔴 **הושלמו:** {stats['completed_leads']}\n"
        stats_text += f"📈 **לידים היום:** {stats['today_leads']}\n"
        stats_text += f"🏆 **אחוז המרה:** {stats['conversion_rate']}%\n"
        
        await update.message.reply_text(stats_text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """טיפול בהודעות טקסט רגילות"""
        user_message = update.message.text
        user_id = update.effective_user.id
        
        # כאן ניתן להוסיף לוגיקה לעיבוד הודעות
        if "ליד" in user_message or "lead" in user_message.lower():
            await self.show_leads(update, context)
        elif "סטט" in user_message or "stats" in user_message.lower():
            await self.show_stats(update, context)
        else:
            await update.message.reply_text(
                "🤖 אני בוט ה-CRM. השתמש בפקודות או בתפריט לניווט."
            )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """טיפול בלחיצות על כפתורים"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        if callback_data == "view_leads":
            await self.show_leads_query(query)
        elif callback_data == "view_stats":
            await self.show_stats_query(query)
        elif callback_data == "manage_clients":
            await self.manage_clients(query)
        elif callback_data == "sync_website":
            await self.sync_website(query)
        elif callback_data == "export_leads":
            await self.export_leads(query)
    
    async def show_leads_query(self, query):
        """הצגת לידים מ-callback query"""
        leads = self.crm.get_recent_leads(limit=5)
        
        if not leads:
            await query.edit_message_text("❌ אין לידים חדשים להצגה.")
            return
        
        leads_text = "📋 **לידים אחרונים:**\n\n"
        for lead in leads:
            status_icon = "🟢" if lead['status'] == 'new' else "🟡" if lead['status'] == 'contacted' else "🔴"
            leads_text += f"{status_icon} **{lead['name']}** - {lead['phone']}\n"
        
        await query.edit_message_text(leads_text)
    
    async def show_stats_query(self, query):
        """הצגת סטטיסטיקות מ-callback query"""
        stats = self.crm.get_stats()
        
        stats_text = "📊 **סטטיסטיקות:**\n\n"
        stats_text += f"👥 סך לידים: {stats['total_leads']}\n"
        stats_text += f"🟢 חדשים: {stats['new_leads']}\n"
        stats_text += f"📈 היום: {stats['today_leads']}\n"
        stats_text += f"🏆 המרה: {stats['conversion_rate']}%\n"
        
        await query.edit_message_text(stats_text)
    
    async def manage_clients(self, query):
        """ניהול לקוחות"""
        keyboard = [
            [InlineKeyboardButton("📞 לידים חדשים", callback_data="new_leads")],
            [InlineKeyboardButton("🔄 לקוחות בטיפול", callback_data="active_clients")],
            [InlineKeyboardButton("✅ לקוחות שהומרו", callback_data="converted_clients")],
            [InlineKeyboardButton("↩️ חזרה", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👥 **ניהול לקוחות**\n\n"
            "בחר קטגוריה לניהול:",
            reply_markup=reply_markup
        )
    
    async def sync_website(self, query):
        """סנכרון עם האתר"""
        webhook_status = "🟢 פעיל" if self.webhook_handler.is_active() else "🔴 לא פעיל"
        
        await query.edit_message_text(
            f"🔄 **סנכרון עם האתר**\n\n"
            f"סטטוס Webhook: {webhook_status}\n"
            f"כתובת: {self.webhook_url}\n\n"
            "הבוט מקבל לידים אוטומטית מהאתר."
        )
    
    async def export_leads(self, query):
        """ייצוא לידים"""
        # כאן ניתן ליישם ייצוא ל-CSV או Excel
        await query.edit_message_text(
            "📤 **ייצוא לידים**\n\n"
            "הפונקציה נמצאת בפיתוח.\n"
            "בעתיד תוכל לייצא ל-CSV או Excel."
        )
    
    def run_webhook(self):
        """הרצת הבוט עם webhook"""
        self.application.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv('PORT', 8443)),
            webhook_url=self.webhook_url,
            cert=None  # ניתן להוסיף SSL certificate אם צריך
        )
    
    def run_polling(self):
        """הרצת הבוט עם polling (לפיתוח)"""
        self.application.run_polling()

if __name__ == '__main__':
    bot = TelegramCRMBot()
    
    # הרצה עם webhook (ל� production) או polling (לפיתוח)
    if os.getenv('USE_WEBHOOK', 'false').lower() == 'true':
        bot.run_webhook()
    else:
        bot.run_polling()
