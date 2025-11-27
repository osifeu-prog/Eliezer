import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import asyncio
import json

# ===== CONFIGURATION =====
# הגדרות לוגים מפורטות
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# משתני סביבה
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8274046661:AAF3fCbwL4c6Uj6qJ9xY9wXqZ9xY9wXqZ9x")
WEBHOOK_PATH = "/webhook-123"
WEBHOOK_URL = f"https://fun-production-8132.up.railway.app{WEBHOOK_PATH}"
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

# אתחול בוט
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# אחסון נתונים (בפרודקשן - מסד נתונים אמיתי)
leads = []
active_users = set()
bot_stats = {
    "start_count": 0,
    "messages_received": 0,
    "leads_created": 0,
    "last_activity": None
}

class CRMStates(StatesGroup):
    waiting_for_lead_name = State()
    waiting_for_lead_phone = State()
    waiting_for_lead_email = State()

# ===== LIFESPAN MANAGEMENT =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """ניהול מחזור חיים של האפליקציה"""
    logger.info("🚀 Starting Telegram CRM Bot...")
    
    try:
        # 1. מחק webhook קיים
        logger.info("🗑️ Deleting existing webhook...")
        delete_result = await bot.delete_webhook(drop_pending_updates=True)
        logger.info(f"✅ Webhook deleted: {delete_result}")
        
        await asyncio.sleep(2)  # המתן לפני הגדרת webhook חדש
        
        # 2. הגדר webhook חדש
        logger.info(f"🌐 Setting new webhook to: {WEBHOOK_URL}")
        set_result = await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query", "chat_member"]
        )
        logger.info(f"✅ Webhook set: {set_result}")
        
        # 3. בדוק את ה-webhook
        webhook_info = await bot.get_webhook_info()
        logger.info(f"📋 Webhook Info:")
        logger.info(f"   URL: {webhook_info.url}")
        logger.info(f"   Pending Updates: {webhook_info.pending_update_count}")
        logger.info(f"   Last Error: {webhook_info.last_error_message}")
        
        # 4. בדוק שהבוט פעיל
        bot_user = await bot.get_me()
        logger.info(f"🤖 Bot Info: @{bot_user.username} ({bot_user.first_name})")
        
        logger.info("🎉 Bot startup completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        logger.error("🔧 Please check your BOT_TOKEN and WEBHOOK_URL")
    
    yield
    
    # ניקוי לפני כיבוי
    logger.info("🛑 Shutting down bot...")
    await bot.session.close()

app = FastAPI(
    lifespan=lifespan,
    title="Telegram CRM Bot",
    description="בוט CRM חכם למשרד פרסום עם אינטגרציית אתר",
    version="1.0.0"
)

# ===== UTILITY FUNCTIONS =====
async def safe_send_message(chat_id: int, text: str, **kwargs):
    """שליחת הודעה בטוחה עם טיפול בשגיאות"""
    try:
        await bot.send_message(chat_id, text, **kwargs)
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send message to {chat_id}: {e}")
        return False

async def log_activity(action: str, user_id: int = None, details: str = ""):
    """רישום פעילות למערכת"""
    bot_stats["last_activity"] = datetime.now().isoformat()
    bot_stats["messages_received"] += 1
    
    log_msg = f"📊 Activity: {action}"
    if user_id:
        log_msg += f" | User: {user_id}"
    if details:
        log_msg += f" | Details: {details}"
    
    logger.info(log_msg)

# ===== TELEGRAM HANDLERS =====
@dp.message(CommandStart())
async def handle_start(message: Message):
    """טיפול בפקודת /start"""
    try:
        user_id = message.from_user.id
        active_users.add(user_id)
        bot_stats["start_count"] += 1
        
        await log_activity("START_COMMAND", user_id, f"User: {message.from_user.first_name}")
        
        # יצירת מקלדת
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 צפה בלידים", callback_data="view_leads")],
            [InlineKeyboardButton(text="📈 סטטיסטיקות", callback_data="view_stats")],
            [InlineKeyboardButton(text="👥 הוסף ליד חדש", callback_data="add_lead")],
            [InlineKeyboardButton(text="🐛 מידע מערכת", callback_data="system_info")],
            [InlineKeyboardButton(text="🔄 בדיקת Webhook", callback_data="check_webhook")]
        ])
        
        welcome_text = (
            f"👋 שלום {message.from_user.first_name}!\n\n"
            "🤖 **ברוך הבא לבוט CRM למשרד פרסום**\n\n"
            "✅ **המערכת פעילה ומוכנה!**\n"
            "📞 ניהול לידים אוטומטי מהאתר\n"
            "📈 מעקב סטטיסטיקות בזמן אמת\n"
            "🔔 התראות מיידיות על לידים חדשים\n\n"
            "**בחר פעולה מהתפריט:**"
        )
        
        await message.answer(welcome_text, reply_markup=keyboard)
        logger.info(f"✅ Welcome message sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in start handler: {e}")
        await message.answer("❌ אירעה שגיאה בהפעלת הבוט. נסה שוב.")

@dp.message(Command("help"))
async def handle_help(message: Message):
    """טיפול בפקודת /help"""
    help_text = (
        "🤖 **בוט CRM - מדריך שימוש**\n\n"
        "**פקודות זמינות:**\n"
        "• /start - תפריט ראשי והפעלה\n"
        "• /leads - הצג לידים אחרונים\n" 
        "• /stats - סטטיסטיקות מערכת\n"
        "• /debug - מידע טכני\n"
        "• /help - מדריך זה\n\n"
        "**סנכרון אתר:**\n"
        "הבוט מקבל לידים אוטומטית דרך webhook בכתובת:\n"
        "`POST /webhook/lead`\n\n"
        "**תמיכה:**\n"
        "לבעיות טכניות, השתמש ב-/debug"
    )
    
    await message.answer(help_text)
    await log_activity("HELP_COMMAND", message.from_user.id)

@dp.message(Command("debug"))
async def handle_debug(message: Message):
    """טיפול בפקודת /debug"""
    try:
        webhook_info = await bot.get_webhook_info()
        bot_user = await bot.get_me()
        
        debug_text = (
            "🐛 **מידע מערכת - DEBUG**\n\n"
            f"🤖 **בוט:** @{bot_user.username}\n"
            f"🌐 **Webhook:** {webhook_info.url or 'לא מוגדר'}\n"
            f"⏳ **עדכונים ממתינים:** {webhook_info.pending_update_count}\n"
            f"❌ **שגיאה אחרונה:** {webhook_info.last_error_message or 'אין'}\n\n"
            f"📊 **סטטיסטיקות:**\n"
            f"• 👥 משתמשים: {len(active_users)}\n"
            f"• 📋 לידים: {len(leads)}\n"
            f"• 🚀 הפעלות: {bot_stats['start_count']}\n"
            f"• 💬 הודעות: {bot_stats['messages_received']}\n"
            f"• ⏰ פעילות אחרונה: {bot_stats['last_activity']}\n\n"
            "**לאפס webhook:**\n"
            "`/reset_webhook`"
        )
        
        await message.answer(debug_text)
        await log_activity("DEBUG_COMMAND", message.from_user.id)
        
    except Exception as e:
        logger.error(f"❌ Error in debug: {e}")
        await message.answer(f"❌ שגיאה במידע debug: {e}")

@dp.message(Command("leads"))
async def handle_leads(message: Message):
    """טיפול בפקודת /leads"""
    try:
        if not leads:
            await message.answer("📝 **אין לידים במערכת**\n\nהשתמש ב'הוסף ליד חדש' או שלח ליד מהאתר.")
            return
        
        leads_text = "📋 **לידים אחרונים במערכת:**\n\n"
        for i, lead in enumerate(leads[-10:], 1):
            status_icon = "🟢" if lead.get('status') == 'new' else "🟡" if lead.get('status') == 'contacted' else "🔴"
            leads_text += f"{status_icon} **{i}. {lead['name']}**\n"
            leads_text += f"   📞 {lead['phone']}\n"
            if lead.get('email'):
                leads_text += f"   📧 {lead['email']}\n"
            leads_text += f"   📅 {lead['date']}\n"
            if lead.get('source'):
                leads_text += f"   🌐 {lead['source']}\n"
            leads_text += "─" * 25 + "\n"
        
        await message.answer(leads_text)
        await log_activity("LEADS_COMMAND", message.from_user.id, f"Showed {len(leads)} leads")
        
    except Exception as e:
        logger.error(f"❌ Error showing leads: {e}")
        await message.answer("❌ אירעה שגיאה בהצגת הלידים.")

@dp.message(Command("stats"))
async def handle_stats(message: Message):
    """טיפול בפקודת /stats"""
    try:
        total_leads = len(leads)
        today = datetime.now().strftime('%d/%m/%Y')
        today_leads = len([lead for lead in leads if lead['date'].startswith(today)])
        
        # ניתוח מקורות
        sources = {}
        for lead in leads:
            source = lead.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        sources_text = "\n".join([f"• {source}: {count}" for source, count in sources.items()])
        
        stats_text = (
            "📊 **סטטיסטיקות CRM - סך הכל**\n\n"
            f"👥 **משתמשים פעילים:** {len(active_users)}\n"
            f"📋 **סך לידים:** {total_leads}\n"
            f"📈 **לידים היום:** {today_leads}\n"
            f"🚀 **הפעלות בוט:** {bot_stats['start_count']}\n"
            f"💬 **הודעות התקבלו:** {bot_stats['messages_received']}\n\n"
            f"**מקורות לידים:**\n{sources_text}\n\n"
            f"🟢 **מערכת:** פעילה\n"
            f"⏰ **עדכון אחרון:** {datetime.now().strftime('%H:%M')}"
        )
        
        await message.answer(stats_text)
        await log_activity("STATS_COMMAND", message.from_user.id)
        
    except Exception as e:
        logger.error(f"❌ Error in stats: {e}")
        await message.answer("❌ שגיאה בהצגת סטטיסטיקות")

@dp.message(Command("reset_webhook"))
async def handle_reset_webhook(message: Message):
    """טיפול בפקודת /reset_webhook"""
    try:
        await message.answer("🔄 **מאפס webhook...**")
        
        # מחק והגדר מחדש
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(2)
        await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True
        )
        
        webhook_info = await bot.get_webhook_info()
        
        result_text = (
            "✅ **Webhook אופס בהצלחה!**\n\n"
            f"🌐 **כתובת:** {webhook_info.url}\n"
            f"⏳ **עדכונים ממתינים:** {webhook_info.pending_update_count}\n"
            f"🟢 **סטטוס:** פעיל\n\n"
            "ניתן לשלוח /start לבדיקה"
        )
        
        await message.answer(result_text)
        await log_activity("RESET_WEBHOOK", message.from_user.id, "Manual webhook reset")
        
    except Exception as e:
        logger.error(f"❌ Error resetting webhook: {e}")
        await message.answer(f"❌ שגיאה באיפוס webhook: {e}")

# ===== CALLBACK HANDLERS =====
@dp.callback_query(F.data == "view_leads")
async def handle_view_leads(callback: types.CallbackQuery):
    """צפייה בלידים"""
    try:
        if not leads:
            await callback.message.edit_text("📝 אין לידים להצגה. השתמש ב'הוסף ליד חדש'.")
            await callback.answer()
            return
        
        leads_text = "📋 **לידים אחרונים:**\n\n"
        for i, lead in enumerate(leads[-5:], 1):
            leads_text += f"{i}. **{lead['name']}**\n"
            leads_text += f"   📞 {lead['phone']}\n"
            leads_text += f"   📅 {lead['date']}\n\n"
        
        await callback.message.edit_text(leads_text)
        await callback.answer()
        await log_activity("VIEW_LEADS_BUTTON", callback.from_user.id)
        
    except Exception as e:
        logger.error(f"❌ Error in view_leads callback: {e}")
        await callback.answer("❌ שגיאה בהצגת לידים", show_alert=True)

@dp.callback_query(F.data == "view_stats")
async def handle_view_stats(callback: types.CallbackQuery):
    """הצגת סטטיסטיקות"""
    try:
        total_leads = len(leads)
        today = datetime.now().strftime('%d/%m/%Y')
        today_leads = len([lead for lead in leads if lead['date'].startswith(today)])
        
        stats_text = (
            "📊 **סטטיסטיקות מהירות:**\n\n"
            f"📋 **לידים:** {total_leads}\n"
            f"📈 **היום:** {today_leads}\n"
            f"👥 **משתמשים:** {len(active_users)}\n"
            f"🟢 **מערכת:** פעילה\n\n"
            "לפרטים מלאים: /stats"
        )
        
        await callback.message.edit_text(stats_text)
        await callback.answer()
        await log_activity("VIEW_STATS_BUTTON", callback.from_user.id)
        
    except Exception as e:
        logger.error(f"❌ Error in view_stats callback: {e}")
        await callback.answer("❌ שגיאה בסטטיסטיקות", show_alert=True)

@dp.callback_query(F.data == "add_lead")
async def handle_add_lead(callback: types.CallbackQuery, state: FSMContext):
    """הוספת ליד חדש"""
    try:
        await callback.message.edit_text(
            "👤 **הוספת ליד חדש**\n\n"
            "אנא הזן את שם הלקוח:"
        )
        await state.set_state(CRMStates.waiting_for_lead_name)
        await callback.answer()
        await log_activity("ADD_LEAD_BUTTON", callback.from_user.id)
        
    except Exception as e:
        logger.error(f"❌ Error in add_lead callback: {e}")
        await callback.answer("❌ שגיאה בהוספת ליד", show_alert=True)

@dp.callback_query(F.data == "system_info")
async def handle_system_info(callback: types.CallbackQuery):
    """מידע מערכת"""
    try:
        webhook_info = await bot.get_webhook_info()
        
        info_text = (
            "🐛 **מידע מערכת:**\n\n"
            f"🌐 **Webhook:** {webhook_info.url or 'לא מוגדר'}\n"
            f"⏳ **עדכונים בתור:** {webhook_info.pending_update_count}\n"
            f"👥 **משתמשים פעילים:** {len(active_users)}\n"
            f"📋 **לידים:** {len(leads)}\n"
            f"🟢 **סטטוס:** פעיל\n\n"
            "לאפס webhook: /reset_webhook"
        )
        
        await callback.message.edit_text(info_text)
        await callback.answer()
        await log_activity("SYSTEM_INFO_BUTTON", callback.from_user.id)
        
    except Exception as e:
        logger.error(f"❌ Error in system_info callback: {e}")
        await callback.answer("❌ שגיאה במידע מערכת", show_alert=True)

@dp.callback_query(F.data == "check_webhook")
async def handle_check_webhook(callback: types.CallbackQuery):
    """בדיקת webhook"""
    try:
        webhook_info = await bot.get_webhook_info()
        
        status = "🟢 פעיל" if webhook_info.url else "🔴 לא מוגדר"
        
        webhook_text = (
            "🔍 **בדיקת Webhook:**\n\n"
            f"**סטטוס:** {status}\n"
            f"**כתובת:** {webhook_info.url or 'לא מוגדר'}\n"
            f"**עדכונים בתור:** {webhook_info.pending_update_count}\n"
            f"**שגיאה אחרונה:** {webhook_info.last_error_message or 'אין'}\n\n"
        )
        
        if not webhook_info.url:
            webhook_text += "**פתרון:** השתמש ב-/reset_webhook"
        
        await callback.message.edit_text(webhook_text)
        await callback.answer()
        await log_activity("CHECK_WEBHOOK_BUTTON", callback.from_user.id)
        
    except Exception as e:
        logger.error(f"❌ Error in check_webhook callback: {e}")
        await callback.answer("❌ שגיאה בבדיקת webhook", show_alert=True)

# ===== STATE HANDLERS =====
@dp.message(CRMStates.waiting_for_lead_name)
async def handle_lead_name(message: Message, state: FSMContext):
    """קבלת שם הלקוח"""
    try:
        if len(message.text) < 2:
            await message.answer("❌ שם חייב להכיל לפחות 2 תווים. נסה שוב:")
            return
        
        await state.update_data(lead_name=message.text)
        await message.answer("📞 אנא הזן את מספר הטלפון של הלקוח:")
        await state.set_state(CRMStates.waiting_for_lead_phone)
        
    except Exception as e:
        logger.error(f"❌ Error handling lead name: {e}")
        await message.answer("❌ שגיאה בשמירת השם. נסה שוב:")
        await state.set_state(CRMStates.waiting_for_lead_name)

@dp.message(CRMStates.waiting_for_lead_phone)
async def handle_lead_phone(message: Message, state: FSMContext):
    """קבלת טלפון הלקוח"""
    try:
        phone = message.text.strip()
        # ולידציה בסיסית של טלפון
        if len(phone) < 9:
            await message.answer("❌ מספר טלפון לא תקין. נסה שוב:")
            return
        
        await state.update_data(lead_phone=phone)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📧 אין אימייל", callback_data="no_email")],
            [InlineKeyboardButton(text="🔚 בטל", callback_data="cancel_lead")]
        ])
        
        await message.answer(
            "📧 האם תרצה להוסיף אימייל? (אופציונלי)\n\n"
            "אם כן, שלח את כתובת האימייל. אחרת, לחץ על 'אין אימייל':",
            reply_markup=keyboard
        )
        await state.set_state(CRMStates.waiting_for_lead_email)
        
    except Exception as e:
        logger.error(f"❌ Error handling lead phone: {e}")
        await message.answer("❌ שגיאה בשמירת הטלפון. נסה שוב:")
        await state.set_state(CRMStates.waiting_for_lead_phone)

@dp.message(CRMStates.waiting_for_lead_email)
async def handle_lead_email(message: Message, state: FSMContext):
    """קבלת אימייל הלקוח"""
    await save_lead_with_email(message, message.text, state)

@dp.callback_query(F.data == "no_email")
async def handle_no_email(callback: types.CallbackQuery, state: FSMContext):
    """ללא אימייל"""
    await save_lead_with_email(callback.message, "", state)
    await callback.answer()

@dp.callback_query(F.data == "cancel_lead")
async def handle_cancel_lead(callback: types.CallbackQuery, state: FSMContext):
    """ביטול הוספת ליד"""
    await state.clear()
    await callback.message.edit_text("❌ הוספת הליד בוטלה.")
    await callback.answer()
    await log_activity("CANCEL_LEAD", callback.from_user.id)

async def save_lead_with_email(message: Message, email: str, state: FSMContext):
    """שמירת הליד במערכת"""
    try:
        data = await state.get_data()
        lead_name = data.get('lead_name')
        lead_phone = data.get('lead_phone')
        
        # יצירת הליד
        new_lead = {
            'name': lead_name,
            'phone': lead_phone,
            'email': email,
            'source': 'telegram_bot',
            'status': 'new',
            'date': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'added_by': message.from_user.id
        }
        leads.append(new_lead)
        bot_stats["leads_created"] += 1
        
        # הודעה למשתמש
        success_text = (
            "✅ **ליד נוסף בהצלחה!**\n\n"
            f"**שם:** {lead_name}\n"
            f"**טלפון:** {lead_phone}\n"
        )
        if email:
            success_text += f"**אימייל:** {email}\n"
        
        success_text += f"**תאריך:** {new_lead['date']}\n\n"
        success_text += "הליד נשמר במערכת וזמין להצגה."
        
        await message.answer(success_text)
        
        # שליחה למשתמשים אחרים
        notification_text = (
            f"👤 **ליד חדש נוסף!**\n\n"
            f"**שם:** {lead_name}\n"
            f"**טלפון:** {lead_phone}\n"
            f"**נוסף על ידי:** {message.from_user.first_name}\n"
            f"**תאריך:** {new_lead['date']}"
        )
        
        # שליחה לכל המשתמשים הפעילים (למעט המוסיף)
        sent_count = 0
        for user_id in active_users:
            if user_id != message.from_user.id:
                if await safe_send_message(user_id, notification_text):
                    sent_count += 1
        
        logger.info(f"📤 Lead notification sent to {sent_count} users")
        await log_activity("LEAD_CREATED", message.from_user.id, f"Lead: {lead_name}")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"❌ Error saving lead: {e}")
        await message.answer("❌ אירעה שגיאה בשמירת הליד. נסה שוב.")
        await state.clear()

# ===== FALLBACK HANDLER =====
@dp.message()
async def handle_all_messages(message: Message):
    """טיפול בכל ההודעות שלא טופלו"""
    try:
        logger.info(f"📨 Unhandled message from {message.from_user.id}: {message.text}")
        
        # אם זו פקודה לא מוכרת
        if message.text and message.text.startswith('/'):
            await message.answer(
                "❓ **פקודה לא מוכרת**\n\n"
                "הפקודות הזמינות הן:\n"
                "• /start - תפריט ראשי\n"
                "• /help - עזרה ומדריך\n"
                "• /leads - הצג לידים\n"
                "• /stats - סטטיסטיקות\n"
                "• /debug - מידע טכני\n"
                "• /reset_webhook - איפוס webhook"
            )
        else:
            await message.answer(
                "🤖 **בוט CRM למשרד פרסום**\n\n"
                "אני כאן כדי לעזור לך לנהל לידים וקבלות.\n\n"
                "השתמש ב-/start לתפריט הראשי\n"
                "או ב-/help למדריך מפורט."
            )
        
        await log_activity("UNHANDLED_MESSAGE", message.from_user.id, f"Text: {message.text}")
        
    except Exception as e:
        logger.error(f"❌ Error in fallback handler: {e}")

# ===== FASTAPI ENDPOINTS =====
@app.post(WEBHOOK_PATH)
async def handle_telegram_webhook(request: Request):
    """טיפול בעדכונים מטלגרם"""
    try:
        update_data = await request.json()
        logger.info(f"📨 Received Telegram update")
        
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        
        return {"status": "ok", "message": "Update processed"}
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@app.post("/webhook/lead")
async def handle_website_lead(request: Request):
    """טיפול בלידים מהאתר"""
    try:
        data = await request.json()
        logger.info(f"🌐 Received lead from website: {data}")
        
        # ולידציה
        if not data.get('name') or not data.get('phone'):
            raise HTTPException(
                status_code=400, 
                detail="Missing required fields: name, phone"
            )
        
        # יצירת הליד
        new_lead = {
            'name': data['name'],
            'phone': data['phone'],
            'email': data.get('email', ''),
            'source': data.get('source', 'website'),
            'notes': data.get('notes', ''),
            'status': 'new',
            'date': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        leads.append(new_lead)
        bot_stats["leads_created"] += 1
        
        # התראה למשתמשים
        lead_message = (
            f"🎯 **ליד חדש מהאתר!**\n\n"
            f"**שם:** {new_lead['name']}\n"
            f"**טלפון:** {new_lead['phone']}\n"
            f"**אימייל:** {new_lead['email'] or 'לא צוין'}\n"
            f"**מקור:** {new_lead['source']}\n"
            f"**הערות:** {new_lead['notes'] or 'אין'}\n"
            f"**תאריך:** {new_lead['date']}"
        )
        
        # שליחה לכל המשתמשים הפעילים
        sent_count = 0
        for user_id in active_users:
            if await safe_send_message(user_id, lead_message):
                sent_count += 1
        
        logger.info(f"📤 Website lead notification sent to {sent_count} users")
        await log_activity("WEBSITE_LEAD", None, f"Lead: {new_lead['name']}")
        
        return {
            "status": "success",
            "message": "Lead added successfully",
            "lead_id": len(leads),
            "notifications_sent": sent_count,
            "lead": {
                "name": new_lead['name'],
                "phone": new_lead['phone'],
                "source": new_lead['source']
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error handling website lead: {e}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@app.post("/reset-webhook")
async def reset_webhook_endpoint():
    """איפוס webhook דרך API"""
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(1)
        await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True
        )
        
        webhook_info = await bot.get_webhook_info()
        
        return {
            "status": "success",
            "message": "Webhook reset successfully",
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count
        }
        
    except Exception as e:
        logger.error(f"❌ API webhook reset failed: {e}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@app.get("/health")
async def health_check():
    """בדיקת בריאות"""
    try:
        webhook_info = await bot.get_webhook_info()
        bot_info = await bot.get_me()
        
        return {
            "status": "healthy",
            "service": "Telegram CRM Bot",
            "bot": f"@{bot_info.username}",
            "webhook_url": webhook_info.url,
            "webhook_pending_updates": webhook_info.pending_update_count,
            "webhook_last_error": webhook_info.last_error_message,
            "statistics": {
                "active_users": len(active_users),
                "total_leads": len(leads),
                "leads_created": bot_stats["leads_created"],
                "start_count": bot_stats["start_count"],
                "last_activity": bot_stats["last_activity"]
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.get("/")
async def root():
    """דף הבית"""
    return {
        "message": "🤖 Telegram CRM Bot is Running!",
        "status": "active",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "webhook_lead": "POST /webhook/lead",
            "reset_webhook": "POST /reset-webhook",
            "telegram_webhook": f"POST {WEBHOOK_PATH}"
        },
        "usage": "Send /start to your bot on Telegram",
        "documentation": "Use /help in the bot for instructions"
    }

@app.get("/debug")
async def debug_info():
    """מידע debug מפורט"""
    try:
        webhook_info = await bot.get_webhook_info()
        
        return {
            "webhook": {
                "url": webhook_info.url,
                "pending_update_count": webhook_info.pending_update_count,
                "last_error_date": webhook_info.last_error_date,
                "last_error_message": webhook_info.last_error_message,
                "max_connections": webhook_info.max_connections
            },
            "statistics": {
                "active_users_count": len(active_users),
                "leads_count": len(leads),
                "start_count": bot_stats["start_count"],
                "messages_received": bot_stats["messages_received"],
                "leads_created": bot_stats["leads_created"],
                "last_activity": bot_stats["last_activity"]
            },
            "environment": {
                "bot_token_set": bool(BOT_TOKEN),
                "webhook_url": WEBHOOK_URL,
                "admin_chat_id_set": bool(ADMIN_CHAT_ID)
            },
            "active_users": list(active_users),
            "recent_leads": leads[-5:] if leads else []
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
