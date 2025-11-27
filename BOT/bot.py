from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, Application, CommandHandler, CallbackQueryHandler
from telegram.error import TelegramError
import logging
from config import Config
from database import db_manager
from crm_manager import CRMManager
import os

logger = logging.getLogger(__name__)

class BotManager:
    """מנהל הבוט עם טיפול מלא בשגיאות"""
    
    def __init__(self):
        self.app = None
    
    def admin_only(self, func):
        """דקורטור לבדיקת הרשאות מנהל"""
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            try:
                user_id = update.effective_user.id
                if user_id not in Config.ADMIN_IDS:
                    await self._send_message(
                        update, 
                        "⛔ אין לך הרשאה להשתמש בבוט זה.\n"
                        "אנא פנה למנהל המערכת."
                    )
                    logger.warning(f"🚫 Unauthorized access attempt by user {user_id}")
                    return
                
                return await func(update, context, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"❌ Error in admin check: {e}")
                await self._send_message(update, "❌ אירעה שגיאה בבדיקת ההרשאות")
        
        return wrapper
    
    async def _send_message(self, update: Update, text: str, **kwargs):
        """שליחת הודעה עם טיפול בשגיאות"""
        try:
            if update.message:
                return await update.message.reply_text(text, **kwargs)
            elif update.callback_query:
                return await update.callback_query.message.reply_text(text, **kwargs)
        except TelegramError as e:
            logger.error(f"❌ Telegram error sending message: {e}")
        except Exception as e:
            logger.error(f"❌ Error sending message: {e}")
    
    async def _edit_message(self, update: Update, text: str, **kwargs):
        """עריכת הודעה עם טיפול בשגיאות"""
        try:
            query = update.callback_query
            await query.edit_message_text(text, **kwargs)
        except TelegramError as e:
            logger.error(f"❌ Telegram error editing message: {e}")
        except Exception as e:
            logger.error(f"❌ Error editing message: {e}")
    
    @admin_only
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /start"""
        try:
            welcome_text = (
                "👋 **ברוך הבא למערכת ה-CRM!**\n\n"
                "🤖 אני כאן כדי לנהל את הלידים שמגיעים מהאתר.\n"
                "📊 השתמש בתפריט למטה כדי לנווט בין האפשרויות.\n\n"
                "💡 **פיצ'רים זמינים:**\n"
                "• צפייה בסטטיסטיקות עדכניות\n"
                "• ניהול הלידים האחרונים\n"
                "• ייצוא נתונים לקובץ Excel\n"
                "• התראות בזמן אמת על לידים חדשים"
            )
            
            keyboard = [
                [InlineKeyboardButton("📊 סטטיסטיקות", callback_data='stats')],
                [InlineKeyboardButton("📥 לידים אחרונים", callback_data='leads')],
                [InlineKeyboardButton("💾 ייצוא לאקסל", callback_data='export')],
                [InlineKeyboardButton("❓ עזרה ומידע", callback_data='help')]
            ]
            
            await self._send_message(
                update, 
                welcome_text, 
                reply_markup=InlineKeyboardMarkup(keyboard), 
                parse_mode='Markdown'
            )
            logger.info(f"✅ Start command executed by user {update.effective_user.id}")
            
        except Exception as e:
            logger.error(f"❌ Error in start command: {e}")
            await self._send_message(update, "❌ אירעה שגיאה בהפעלת הבוט")
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """טיפול בלחיצות כפתורים"""
        query = update.callback_query
        await query.answer()
        
        db = None
        try:
            db = db_manager.get_session()
            
            if query.data == 'stats':
                await self._handle_stats(query, db)
            elif query.data == 'leads':
                await self._handle_leads(query, db)
            elif query.data == 'export':
                await self._handle_export(query, db)
            elif query.data == 'help':
                await self._handle_help(query)
            else:
                await self._edit_message(update, "❌ פעולה לא מזוהה")
                
        except Exception as e:
            logger.error(f"❌ Error in button handler: {e}")
            await self._edit_message(update, "❌ אירעה שגיאה בעיבוד הבקשה")
        finally:
            if db:
                db_manager.close_session(db)
    
    async def _handle_stats(self, query, db):
        """טיפול בנתוני סטטיסטיקה"""
        stats = CRMManager.get_stats(db)
        text = (
            "📊 **סטטיסטיקות בזמן אמת:**\n\n"
            f"📅 **לידים היום:** `{stats['today']}`\n"
            f"⏳ **ממתינים לטיפול:** `{stats['pending']}`\n"
            f"📈 **סה\"כ לידים:** `{stats['total']}`\n\n"
            "💡 המערכת מתעדכנת אוטומטית עם כל ליד חדש"
        )
        await query.edit_message_text(text, parse_mode='Markdown')
    
    async def _handle_leads(self, query, db):
        """טיפול בהצגת לידים אחרונים"""
        leads = CRMManager.get_recent_leads(db, 5)
        if not leads:
            await query.edit_message_text(
                "📭 **אין לידים חדשים במערכת**\n\n"
                "🤔 הלידים שיתקבלו יופיעו כאן."
            )
        else:
            text = "📥 **5 הלידים האחרונים:**\n\n"
            for i, lead in enumerate(leads, 1):
                status_icon = "🟢" if lead.status == 'new' else "🟡" if lead.status == 'contacted' else "🔴"
                text += (
                    f"{status_icon} **ליד #{i}**\n"
                    f"👤 **שם:** {lead.name}\n"
                    f"📱 **טלפון:** `{lead.phone}`\n"
                )
                if lead.email:
                    text += f"📧 **אימייל:** {lead.email}\n"
                if lead.notes:
                    text += f"📝 **הערות:** {lead.notes}\n"
                text += f"🕒 **תאריך:** {lead.created_at.strftime('%d/%m/%Y %H:%M')}\n\n"
            
            await query.edit_message_text(text, parse_mode='Markdown')
    
    async def _handle_export(self, query, db):
        """טיפול בייצוא ל-CSV"""
        try:
            await query.edit_message_text("⏳ **מכין קובץ נתונים...**\n\nהתהליך עשוי לארוך מספר שניות.")
            
            filename = CRMManager.export_to_csv(db, Config.CSV_FILENAME)
            
            with open(filename, 'rb') as file:
                await query.message.reply_document(
                    document=file,
                    filename=f"leads_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    caption=(
                        "📑 **דוח הלידים המלא**\n\n"
                        "✅ הקובץ כולל את כל הלידים מהמערכת.\n"
                        "💾 ניתן לפתוח ב-Excel או בגיליונות Google"
                    )
                )
            
            # ניקוי הקובץ
            os.remove(filename)
            logger.info("✅ CSV file sent and cleaned up")
            
        except Exception as e:
            logger.error(f"❌ Export failed: {e}")
            await query.message.reply_text("❌ אירעה שגיאה ביצירת הקובץ")
    
    async def _handle_help(self, query):
        """טיפול במסך עזרה"""
        help_text = (
            "🛠 **עזרה ומידע - CRM Bot**\n\n"
            "📋 **פקודות זמינות:**\n"
            "• `/start` - תפריט ראשי\n"
            "• `/stats` - צפייה בסטטיסטיקות\n\n"
            
            "🎯 **תכונות המערכת:**\n"
            "• 📥 קליטת לידים אוטומטית מהאתר\n"
            "• 🔔 התראות בזמן אמת\n"
            "• 📊 דוחות וסטטיסטיקות\n"
            "• 💾 ייצוא נתונים\n\n"
            
            "⚙️ **הגדרות טכניות:**\n"
            "• המערכת רצה על FastAPI\n"
            "• מסד נתונים: PostgreSQL/SQLite\n"
            "• תמיכה בווב-הוקים\n\n"
            
            "❓ **צריך עזרה?**\n"
            "פנה למנהל המערכת."
        )
        await query.edit_message_text(help_text, parse_mode='Markdown')
    
    async def notify_admins(self, lead_data: dict):
        """שליחת התראה על ליד חדש לכל המנהלים"""
        if not self.app:
            logger.error("❌ Bot app not initialized for notifications")
            return
        
        message = (
            "🚀 **ליד חדש התקבל!**\n\n"
            f"👤 **שם:** {lead_data.get('name', 'N/A')}\n"
            f"📱 **טלפון:** `{lead_data.get('phone', 'N/A')}`\n"
            f"📧 **מייל:** {lead_data.get('email', 'לא צוין')}\n"
            f"📌 **הערות:** {lead_data.get('notes', 'אין')}\n"
            f"🔗 **מקור:** {lead_data.get('source', 'אתר')}\n"
            f"🕒 **זמן:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        
        success_count = 0
        for admin_id in Config.ADMIN_IDS:
            try:
                await self.app.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode='Markdown'
                )
                success_count += 1
                logger.debug(f"✅ Notification sent to admin {admin_id}")
            except TelegramError as e:
                logger.error(f"❌ Failed to send notification to {admin_id}: {e}")
            except Exception as e:
                logger.error(f"❌ Error sending to {admin_id}: {e}")
        
        logger.info(f"📨 Lead notifications sent: {success_count}/{len(Config.ADMIN_IDS)}")
    
    def setup_bot(self, application: Application):
        """הגדרת הבוט וה-handlers"""
        self.app = application
        
        # הוספת handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("stats", self.start))  # מפנה לאותו מקום
        application.add_handler(CallbackQueryHandler(self.button_handler))
        
        logger.info("✅ Bot handlers setup completed")

# יצירת instance גלובלי
bot_manager = BotManager()
