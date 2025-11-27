import os
import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import aiohttp

from database import DatabaseManager
from crm_manager import CRMManager
from config import config

# ===== CONFIGURATION =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== ENVIRONMENT VARIABLES =====
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
RAILWAY_URL = os.getenv("RAILWAY_URL", "https://fun-production-8132.up.railway.app")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{RAILWAY_URL}{WEBHOOK_PATH}"

# ולידציה
if not BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN is missing!")
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

logger.info("✅ Environment variables loaded")

# ===== INITIALIZATION =====
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# אתחול מסד נתונים ו-CRM
db_manager = DatabaseManager()
crm_manager = CRMManager(db_manager)

# אחסון נתונים זמני
active_users = set()

class LeadForm(StatesGroup):
    name = State()
    phone = State()
    email = State()
    notes = State()

# ===== WEBHOOK MANAGEMENT =====
async def setup_webhook():
    """הגדרת webhook אוטומטית"""
    try:
        logger.info("🔄 Setting up webhook...")
        
        # מחק webhook קיים
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(1)
        
        # הגדר webhook חדש
        await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query", "chat_member"]
        )
        
        # בדוק את הסטטוס
        webhook_info = await bot.get_webhook_info()
        
        if webhook_info.url == WEBHOOK_URL:
            logger.info(f"✅ Webhook setup successful: {WEBHOOK_URL}")
            return True
        else:
            logger.warning(f"⚠️ Webhook URL mismatch: {webhook_info.url}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Webhook setup failed: {e}")
        return False

# ===== LIFESPAN MANAGEMENT =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """ניהול מחזור חיים של האפליקציה"""
    logger.info("🚀 Starting Telegram CRM Bot...")
    
    try:
        # הגדרת webhook
        webhook_success = await setup_webhook()
        
        if webhook_success:
            logger.info("✅ Bot started successfully with webhook")
        else:
            logger.error("❌ Failed to setup webhook")
        
        # בדיקה סופית
        webhook_info = await bot.get_webhook_info()
        logger.info(f"🎯 Webhook status: {webhook_info.url}")
        logger.info(f"📨 Pending updates: {webhook_info.pending_update_count}")
        
        bot_user = await bot.get_me()
        logger.info(f"🤖 Bot ready: @{bot_user.username}")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
    
    yield
    
    logger.info("🛑 Shutting down bot...")
    await bot.session.close()

app = FastAPI(
    title="Telegram CRM Bot",
    description="בוט CRM חכם לניהול לידים ומשרד פרסום",
    version="1.0.0",
    lifespan=lifespan
)

# ===== TELEGRAM HANDLERS =====
@dp.message(CommandStart())
async def handle_start(message: Message):
    """טיפול בפקודת /start"""
    try:
        user_id = message.from_user.id
        active_users.add(user_id)
        
        # הוסף משתמש למסד הנתונים
        crm_manager.add_user(
            telegram_id=user_id,
            first_name=message.from_user.first_name,
            username=message.from_user.username
        )
        
        logger.info(f"👤 User {user_id} started the bot")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 צפה בלידים", callback_data="view_leads")],
            [InlineKeyboardButton(text="📈 סטטיסטיקות", callback_data="view_stats")],
            [InlineKeyboardButton(text="👥 הוסף ליד", callback_data="add_lead")],
            [InlineKeyboardButton(text="🔧 בדיקת מערכת", callback_data="system_check")]
        ])
        
        welcome_text = (
            f"🎉 **ברוך הבא!** שלום {message.from_user.first_name}!\n\n"
            "🤖 **בוט CRM למשרד פרסום**\n\n"
            "✅ **מערכת פעילה ומוכנה**\n"
            "📞 ניהול לידים אוטומטי\n"
            "📈 מעקב סטטיסטיקות\n"
            "🔔 התראות מיידיות\n\n"
            "**בחר פעולה:**"
        )
        
        await message.answer(welcome_text, reply_markup=keyboard)
        logger.info(f"✅ Sent welcome to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in start: {e}")

@dp.message(Command("leads"))
async def handle_leads(message: Message):
    """הצגת הלידים האחרונים"""
    try:
        leads = crm_manager.get_recent_leads(limit=5)
        
        if not leads:
            await message.answer("📝 אין לידים במערכת כרגע.")
            return
        
        leads_text = "📋 **לידים אחרונים:**\n\n"
        for lead in leads:
            leads_text += f"• **{lead['name']}** - {lead['phone']}\n"
            leads_text += f"  📧 {lead['email'] or 'לא צוין'}\n"
            leads_text += f"  🕒 {lead['created_at']}\n"
            leads_text += f"  📊 סטטוס: {lead['status']}\n\n"
        
        await message.answer(leads_text)
        
    except Exception as e:
        logger.error(f"❌ Error showing leads: {e}")
        await message.answer("❌ שגיאה בטעינת הלידים")

@dp.message(Command("stats"))
async def handle_stats(message: Message):
    """הצגת סטטיסטיקות"""
    try:
        stats = crm_manager.get_stats()
        
        stats_text = (
            "📊 **סטטיסטיקות מערכת:**\n\n"
            f"👥 **משתמשים פעילים:** {len(active_users)}\n"
            f"📋 **סך הלידים:** {stats['total_leads']}\n"
            f"🆕 **לידים חדשים:** {stats['new_leads']}\n"
            f"📞 **לידים בטיפול:** {stats['contacted_leads']}\n"
            f"✅ **לידים שהסתיימו:** {stats['completed_leads']}\n"
            f"📈 **אחוז המרה:** {stats['conversion_rate']}%\n"
            f"📅 **לידים מהיום:** {stats['today_leads']}\n"
        )
        
        await message.answer(stats_text)
        
    except Exception as e:
        logger.error(f"❌ Error showing stats: {e}")
        await message.answer("❌ שגיאה בטעינת הסטטיסטיקות")

@dp.message(Command("webhook_status"))
async def handle_webhook_status(message: Message):
    """בדיקת סטטוס webhook"""
    try:
        webhook_info = await bot.get_webhook_info()
        
        status_text = (
            "🔧 **סטטוס Webhook**\n\n"
            f"🌐 **URL:** {webhook_info.url or '❌ לא מוגדר'}\n"
            f"⏳ **עדכונים ממתינים:** {webhook_info.pending_update_count}\n"
            f"❌ **שגיאה אחרונה:** {webhook_info.last_error_message or 'אין'}\n"
            f"👥 **משתמשים פעילים:** {len(active_users)}\n\n"
        )
        
        if webhook_info.url == WEBHOOK_URL:
            status_text += "🟢 **סטטוס:** Webhook פעיל ומחובר!"
        else:
            status_text += "🔴 **סטטוס:** Webhook לא מוגדר!\n"
        
        await message.answer(status_text)
        
    except Exception as e:
        logger.error(f"❌ Error in webhook_status: {e}")
        await message.answer("❌ שגיאה בבדיקת סטטוס")

@dp.message(Command("help"))
async def handle_help(message: Message):
    """הצגת עזרה"""
    help_text = (
        "🆘 **עזרה - פקודות זמינות:**\n\n"
        "/start - התחלת שימוש בבוט\n"
        "/leads - הצג לידים אחרונים\n"
        "/stats - הצג סטטיסטיקות\n"
        "/webhook_status - בדיקת סטטוס\n"
        "/help - הצג הודעה זו\n\n"
        "**ניתן גם להשתמש בלחצנים בתפריט**"
    )
    
    await message.answer(help_text)

# ===== CALLBACK HANDLERS =====
@dp.callback_query(F.data == "view_leads")
async def handle_view_leads(callback: types.CallbackQuery):
    """צפייה בלידים"""
    try:
        leads = crm_manager.get_recent_leads(limit=5)
        
        if not leads:
            await callback.message.edit_text("📝 אין לידים במערכת כרגע.")
        else:
            leads_text = "📋 **לידים אחרונים:**\n\n"
            for lead in leads:
                leads_text += f"• **{lead['name']}** - {lead['phone']}\n"
                leads_text += f"  📧 {lead['email'] or 'לא צוין'}\n"
                leads_text += f"  🕒 {lead['created_at']}\n\n"
            
            await callback.message.edit_text(leads_text)
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Error in view_leads: {e}")
        await callback.answer("❌ שגיאה בטעינת הלידים", show_alert=True)

@dp.callback_query(F.data == "view_stats")
async def handle_view_stats(callback: types.CallbackQuery):
    """סטטיסטיקות"""
    try:
        stats = crm_manager.get_stats()
        
        stats_text = (
            "📊 **סטטיסטיקות:**\n\n"
            f"👥 **משתמשים פעילים:** {len(active_users)}\n"
            f"📋 **סך הלידים:** {stats['total_leads']}\n"
            f"📅 **לידים מהיום:** {stats['today_leads']}\n"
            f"📈 **אחוז המרה:** {stats['conversion_rate']}%\n"
        )
        
        await callback.message.edit_text(stats_text)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Error in view_stats: {e}")
        await callback.answer("❌ שגיאה בטעינת הסטטיסטיקות", show_alert=True)

@dp.callback_query(F.data == "system_check")
async def handle_system_check(callback: types.CallbackQuery):
    """בדיקת מערכת"""
    try:
        webhook_info = await bot.get_webhook_info()
        stats = crm_manager.get_stats()
        
        status = "🟢 פעיל" if webhook_info.url == WEBHOOK_URL else "🔴 לא פעיל"
        
        check_text = (
            "🔍 **בדיקת מערכת**\n\n"
            f"🌐 **Webhook:** {status}\n"
            f"📨 **עדכונים:** {webhook_info.pending_update_count}\n"
            f"👥 **משתמשים:** {len(active_users)}\n"
            f"📋 **לידים:** {stats['total_leads']}\n"
            f"💾 **מסד נתונים:** 🟢 פעיל\n"
            f"🤖 **בוט:** 🟢 פעיל\n\n"
            "**המערכת פועלת כשורה!**"
        )
        
        await callback.message.edit_text(check_text)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Error in system_check: {e}")
        await callback.answer("❌ שגיאה בבדיקה", show_alert=True)

# ===== FASTAPI ENDPOINTS =====
@app.post(WEBHOOK_PATH)
async def handle_telegram_webhook(request: Request):
    """טיפול בעדכונים מטלגרם"""
    try:
        update_data = await request.json()
        logger.info("📨 Received Telegram webhook update")
        
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        
        return {"status": "ok", "message": "Update processed"}
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@app.get("/health")
async def health_check():
    """בדיקת בריאות"""
    try:
        webhook_info = await bot.get_webhook_info()
        stats = crm_manager.get_stats()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count,
            "active_users": len(active_users),
            "leads_count": stats['total_leads'],
            "service": "Telegram CRM Bot"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/webhook/lead")
async def handle_webhook_lead(request: Request):
    """טיפול בלידים מ-webhook חיצוני"""
    try:
        data = await request.json()
        
        # וידוא שדות חובה
        if not data.get('name') or not data.get('phone'):
            raise HTTPException(status_code=400, detail="Name and phone are required")
        
        # הוספת הליד
        lead = crm_manager.add_lead(
            name=data['name'],
            phone=data['phone'],
            email=data.get('email'),
            source=data.get('source', 'website'),
            notes=data.get('notes')
        )
        
        logger.info(f"✅ New lead added via webhook: {lead.name} ({lead.phone})")
        
        # שליחת התראה למנהלים
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        if admin_chat_id:
            try:
                alert_text = (
                    "🔔 **ליד חדש התקבל!**\n\n"
                    f"👤 **שם:** {lead.name}\n"
                    f"📞 **טלפון:** {lead.phone}\n"
                    f"📧 **אימייל:** {lead.email or 'לא צוין'}\n"
                    f"🌐 **מקור:** {lead.source}\n"
                    f"🕒 **זמן:** {lead.created_at.strftime('%d/%m/%Y %H:%M')}"
                )
                await bot.send_message(admin_chat_id, alert_text)
            except Exception as e:
                logger.error(f"❌ Failed to send admin alert: {e}")
        
        return {
            "success": True,
            "lead_id": lead.id,
            "message": "Lead added successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Webhook lead error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/")
async def root():
    return {
        "message": "CRM Bot is Running",
        "status": "active", 
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "health": "GET /health",
            "telegram_webhook": f"POST {WEBHOOK_PATH}",
            "webhook_lead": "POST /webhook/lead"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
