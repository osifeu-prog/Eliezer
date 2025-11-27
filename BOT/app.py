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

# ===== CONFIGURATION =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== ENVIRONMENT VARIABLES =====
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook-123")
RAILWAY_URL = os.getenv("RAILWAY_URL", "https://fun-production-8132.up.railway.app")
WEBHOOK_URL = f"{RAILWAY_URL}{WEBHOOK_PATH}"
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# ולידציה
if not BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN is missing!")
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

logger.info(f"✅ Environment loaded - Bot Token: {'✓' if BOT_TOKEN else '✗'}")

# אתחול בוט
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# אחסון נתונים
leads = []
active_users = set()

# ===== LIFESPAN MANAGEMENT =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """ניהול מחזור חיים של האפליקציה"""
    logger.info("🚀 Starting Telegram CRM Bot...")
    
    try:
        # בדוק את סטטוס ה-webhook הנוכחי
        webhook_info = await bot.get_webhook_info()
        logger.info(f"📋 Current Webhook: {webhook_info.url}")
        logger.info(f"⏳ Pending Updates: {webhook_info.pending_update_count}")
        
        if webhook_info.url != WEBHOOK_URL:
            logger.info("🔄 Webhook URL mismatch, setting new webhook...")
            await bot.delete_webhook(drop_pending_updates=True)
            await asyncio.sleep(1)
            
            await bot.set_webhook(
                url=WEBHOOK_URL,
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"]
            )
            logger.info(f"✅ Webhook set to: {WEBHOOK_URL}")
        else:
            logger.info("✅ Webhook already set correctly")
        
        # בדיקה סופית
        webhook_info = await bot.get_webhook_info()
        logger.info(f"🎯 Final Webhook: {webhook_info.url}")
        
        bot_user = await bot.get_me()
        logger.info(f"🤖 Bot Ready: @{bot_user.username}")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
    
    yield
    
    logger.info("🛑 Shutting down bot...")
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

# ===== TELEGRAM HANDLERS =====
@dp.message(CommandStart())
async def handle_start(message: Message):
    """טיפול בפקודת /start"""
    try:
        user_id = message.from_user.id
        active_users.add(user_id)
        
        logger.info(f"👤 User {user_id} started the bot")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 צפה בלידים", callback_data="view_leads")],
            [InlineKeyboardButton(text="📈 סטטיסטיקות", callback_data="view_stats")],
            [InlineKeyboardButton(text="👥 הוסף ליד", callback_data="add_lead")],
            [InlineKeyboardButton(text="🔧 בדיקת מערכת", callback_data="system_check")]
        ])
        
        welcome_text = (
            f"👋 שלום {message.from_user.first_name}!\n\n"
            "🤖 **בוט CRM למשרד פרסום**\n\n"
            "✅ **המערכת פעילה!**\n"
            "📞 ניהול לידים אוטומטי\n"
            "📈 מעקב סטטיסטיקות\n"
            "🔔 התראות מיידיות\n\n"
            "**בחר פעולה:**"
        )
        
        await message.answer(welcome_text, reply_markup=keyboard)
        logger.info(f"✅ Sent welcome to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in start: {e}")

@dp.message(Command("status"))
async def handle_status(message: Message):
    """בדיקת סטטוס המערכת"""
    try:
        webhook_info = await bot.get_webhook_info()
        
        status_text = (
            "🔧 **סטטוס מערכת - CRM Bot**\n\n"
            f"🤖 **בוט:** פעיל\n"
            f"🌐 **Webhook:** {webhook_info.url or 'לא מוגדר'}\n"
            f"⏳ **עדכונים ממתינים:** {webhook_info.pending_update_count}\n"
            f"👥 **משתמשים פעילים:** {len(active_users)}\n"
            f"📋 **לידים במערכת:** {len(leads)}\n"
            f"🟢 **סטטוס:** {'פעיל' if webhook_info.url else 'לא פעיל'}\n\n"
        )
        
        if not webhook_info.url:
            status_text += "❌ **בעיה:** Webhook לא מוגדר!\n"
            status_text += "**פתרון:** השתמש ב-/setup_webhook"
        
        await message.answer(status_text)
        
    except Exception as e:
        logger.error(f"❌ Error in status: {e}")
        await message.answer("❌ שגיאה בבדיקת סטטוס")

@dp.message(Command("setup_webhook"))
async def handle_setup_webhook(message: Message):
    """הגדרת webhook ידנית"""
    try:
        await message.answer("🔄 **מגדיר webhook...**")
        
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(2)
        
        await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True
        )
        
        webhook_info = await bot.get_webhook_info()
        
        result_text = (
            "✅ **Webhook הוגדר בהצלחה!**\n\n"
            f"🌐 **כתובת:** {webhook_info.url}\n"
            f"⏳ **עדכונים:** {webhook_info.pending_update_count}\n"
            f"🟢 **סטטוס:** פעיל\n\n"
            "**ניתן לשלוח /start לבדיקה**"
        )
        
        await message.answer(result_text)
        
    except Exception as e:
        logger.error(f"❌ Error setting webhook: {e}")
        await message.answer(f"❌ שגיאה: {e}")

@dp.message(Command("debug"))
async def handle_debug(message: Message):
    """מידע debug מפורט"""
    try:
        webhook_info = await bot.get_webhook_info()
        
        debug_text = (
            "🐛 **מידע Debug - CRM Bot**\n\n"
            f"🔧 **Webhook URL:** {webhook_info.url}\n"
            f"📮 **Pending Updates:** {webhook_info.pending_update_count}\n"
            f"❌ **Last Error:** {webhook_info.last_error_message or 'אין'}\n"
            f"👥 **Active Users:** {len(active_users)}\n"
            f"📋 **Total Leads:** {len(leads)}\n"
            f"🌐 **Server URL:** {RAILWAY_URL}\n"
            f"🛣️ **Webhook Path:** {WEBHOOK_PATH}\n\n"
            "**פקודות:**\n"
            "/status - סטטוס\n"
            "/setup_webhook - הגדר webhook\n"
            "/start - תפריט ראשי"
        )
        
        await message.answer(debug_text)
        
    except Exception as e:
        logger.error(f"❌ Error in debug: {e}")
        await message.answer(f"❌ שגיאה: {e}")

# ===== CALLBACK HANDLERS =====
@dp.callback_query(F.data == "system_check")
async def handle_system_check(callback: types.CallbackQuery):
    """בדיקת מערכת"""
    try:
        webhook_info = await bot.get_webhook_info()
        
        check_text = (
            "🔍 **בדיקת מערכת**\n\n"
            f"🌐 **Webhook:** {webhook_info.url or '❌ לא מוגדר'}\n"
            f"⏳ **עדכונים:** {webhook_info.pending_update_count}\n"
            f"👥 **משתמשים:** {len(active_users)}\n"
            f"🟢 **מערכת:** {'✅ פעילה' if webhook_info.url else '❌ לא פעילה'}\n\n"
        )
        
        if not webhook_info.url:
            check_text += "**להפעלה:** שלח /setup_webhook"
        
        await callback.message.edit_text(check_text)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Error in system_check: {e}")
        await callback.answer("❌ שגיאה בבדיקה", show_alert=True)

@dp.callback_query(F.data == "view_leads")
async def handle_view_leads(callback: types.CallbackQuery):
    """צפייה בלידים"""
    if not leads:
        await callback.message.edit_text("📝 אין לידים במערכת.")
    else:
        leads_text = "📋 **לידים:**\n\n"
        for lead in leads[-3:]:
            leads_text += f"• {lead['name']} - {lead['phone']}\n"
        await callback.message.edit_text(leads_text)
    await callback.answer()

@dp.callback_query(F.data == "view_stats")
async def handle_view_stats(callback: types.CallbackQuery):
    """סטטיסטיקות"""
    stats_text = f"📊 **סטטיסטיקות:**\n\n👥 משתמשים: {len(active_users)}\n📋 לידים: {len(leads)}"
    await callback.message.edit_text(stats_text)
    await callback.answer()

# ===== FASTAPI ENDPOINTS =====
@app.post(WEBHOOK_PATH)
async def handle_telegram_webhook(request: Request):
    """טיפול בעדכונים מטלגרם"""
    try:
        update_data = await request.json()
        logger.info("📨 Received Telegram webhook request")
        
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
        return {
            "status": "healthy",
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count,
            "active_users": len(active_users),
            "leads_count": len(leads)
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/reset-webhook")
async def reset_webhook():
    """איפוס webhook דרך API"""
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(1)
        await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)
        
        webhook_info = await bot.get_webhook_info()
        return {
            "status": "success", 
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/")
async def root():
    return {
        "message": "CRM Bot is Running",
        "status": "active",
        "endpoints": {
            "health": "/health",
            "reset_webhook": "POST /reset-webhook",
            "webhook": f"POST {WEBHOOK_PATH}"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
