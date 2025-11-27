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
import aiohttp

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

# אתחול בוט
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# אחסון נתונים
leads = []
active_users = set()

class CRMStates(StatesGroup):
    waiting_for_lead_name = State()
    waiting_for_lead_phone = State()

# ===== WEBHOOK MANAGEMENT =====
async def setup_webhook():
    """הגדרת webhook אוטומטית"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 Attempt {attempt + 1}/{max_retries} to setup webhook...")
            
            # מחק webhook קיים
            await bot.delete_webhook(drop_pending_updates=True)
            await asyncio.sleep(1)
            
            # הגדר webhook חדש
            result = await bot.set_webhook(
                url=WEBHOOK_URL,
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"]
            )
            
            # בדוק את הסטטוס
            webhook_info = await bot.get_webhook_info()
            
            if webhook_info.url == WEBHOOK_URL:
                logger.info(f"✅ Webhook setup successful: {WEBHOOK_URL}")
                logger.info(f"📊 Pending updates: {webhook_info.pending_update_count}")
                return True
            else:
                logger.warning(f"⚠️ Webhook URL mismatch: {webhook_info.url} != {WEBHOOK_URL}")
                
        except Exception as e:
            logger.error(f"❌ Webhook setup attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(2)
    
    logger.error("🚨 All webhook setup attempts failed!")
    return False

async def manual_webhook_setup():
    """הגדרת webhook ידנית דרך Telegram API"""
    try:
        logger.info("🔧 Trying manual webhook setup via Telegram API...")
        
        async with aiohttp.ClientSession() as session:
            # מחיקת webhook קיים
            async with session.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook",
                json={"drop_pending_updates": True}
            ) as response:
                delete_result = await response.json()
                logger.info(f"🗑️ Delete webhook result: {delete_result}")
            
            await asyncio.sleep(1)
            
            # הגדרת webhook חדש
            async with session.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
                json={
                    "url": WEBHOOK_URL,
                    "drop_pending_updates": True,
                    "allowed_updates": ["message", "callback_query"]
                }
            ) as response:
                set_result = await response.json()
                logger.info(f"🌐 Set webhook result: {set_result}")
                
                if set_result.get('ok'):
                    logger.info("✅ Manual webhook setup successful!")
                    return True
                else:
                    logger.error(f"❌ Manual webhook setup failed: {set_result}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Manual webhook setup error: {e}")
        return False

# ===== LIFESPAN MANAGEMENT =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """ניהול מחזור חיים של האפליקציה"""
    logger.info("🚀 Starting Telegram CRM Bot...")
    
    try:
        # ניסוי הגדרת webhook אוטומטית
        webhook_success = await setup_webhook()
        
        if not webhook_success:
            logger.warning("🔄 Falling back to manual webhook setup...")
            await manual_webhook_setup()
        
        # בדיקה סופית
        webhook_info = await bot.get_webhook_info()
        logger.info(f"🎯 Final webhook status: {webhook_info.url}")
        logger.info(f"📨 Pending updates: {webhook_info.pending_update_count}")
        
        bot_user = await bot.get_me()
        logger.info(f"🤖 Bot ready: @{bot_user.username}")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
    
    yield
    
    logger.info("🛑 Shutting down bot...")
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

# ===== UTILITY FUNCTIONS =====
async def safe_send_message(chat_id: int, text: str, **kwargs):
    """שליחת הודעה בטוחה עם טיפול בשגיאות"""
    try:
        await bot.send_message(chat_id, text, **kwargs)
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send message to {chat_id}: {e}")
        return False

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
            f"🎉 **הבוט פעיל!** שלום {message.from_user.first_name}!\n\n"
            "🤖 **בוט CRM למשרד פרסום**\n\n"
            "✅ **Webhook מוגדר ופעיל**\n"
            "📞 ניהול לידים אוטומטי\n"
            "📈 מעקב סטטיסטיקות\n"
            "🔔 התראות מיידיות\n\n"
            "**בחר פעולה:**"
        )
        
        await message.answer(welcome_text, reply_markup=keyboard)
        logger.info(f"✅ Sent welcome to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in start: {e}")

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
            f"👥 **משתמשים פעילים:** {len(active_users)}\n"
            f"📋 **לידים:** {len(leads)}\n\n"
        )
        
        if webhook_info.url == WEBHOOK_URL:
            status_text += "🟢 **סטטוס:** Webhook פעיל ומחובר!"
        else:
            status_text += "🔴 **סטטוס:** Webhook לא מוגדר!\n"
            status_text += "**פתרון:** שלח /fix_webhook"
        
        await message.answer(status_text)
        
    except Exception as e:
        logger.error(f"❌ Error in webhook_status: {e}")
        await message.answer("❌ שגיאה בבדיקת סטטוס")

@dp.message(Command("fix_webhook"))
async def handle_fix_webhook(message: Message):
    """תיקון webhook ידני"""
    try:
        await message.answer("🔄 **מתקן webhook...**")
        
        success = await setup_webhook()
        
        if success:
            webhook_info = await bot.get_webhook_info()
            response_text = (
                "✅ **Webhook תוקן בהצלחה!**\n\n"
                f"🌐 **URL:** {webhook_info.url}\n"
                f"⏳ **עדכונים:** {webhook_info.pending_update_count}\n\n"
                "**ניתן לשלוח /start לבדיקה**"
            )
        else:
            response_text = (
                "❌ **תיקון Webhook נכשל**\n\n"
                "**פתרונות:**\n"
                "1. בדוק את ה-TELEGRAM_BOT_TOKEN\n"
                "2. בדוק שה-RAILWAY_URL תקין\n"
                "3. נסה שוב בעוד דקה"
            )
        
        await message.answer(response_text)
        
    except Exception as e:
        logger.error(f"❌ Error fixing webhook: {e}")
        await message.answer(f"❌ שגיאה בתיקון webhook: {e}")

@dp.message(Command("force_webhook"))
async def handle_force_webhook(message: Message):
    """הגדרת webhook דרך Telegram API"""
    try:
        await message.answer("🔧 **מגדיר webhook דרך Telegram API...**")
        
        success = await manual_webhook_setup()
        
        if success:
            response_text = "✅ **Webhook הוגדר דרך Telegram API!**\n\nנסה /start"
        else:
            response_text = "❌ **הגדרת Webhook נכשלה**\n\nבדוק את הלוגים לפרטים."
        
        await message.answer(response_text)
        
    except Exception as e:
        logger.error(f"❌ Error in force_webhook: {e}")
        await message.answer(f"❌ שגיאה: {e}")

@dp.message(Command("test"))
async def handle_test(message: Message):
    """פקודת בדיקה"""
    await message.answer("✅ **בוט פעיל!**\n\nהמערכת עובדת ומוכנה לקבל הודעות.")

# ===== CALLBACK HANDLERS =====
@dp.callback_query(F.data == "view_leads")
async def handle_view_leads(callback: types.CallbackQuery):
    """צפייה בלידים"""
    if not leads:
        await callback.message.edit_text("📝 אין לידים במערכת.")
    else:
        leads_text = "📋 **לידים:**\n\n"
        for lead in leads[-5:]:
            leads_text += f"• {lead['name']} - {lead['phone']}\n"
        await callback.message.edit_text(leads_text)
    await callback.answer()

@dp.callback_query(F.data == "view_stats")
async def handle_view_stats(callback: types.CallbackQuery):
    """סטטיסטיקות"""
    stats_text = f"📊 **סטטיסטיקות:**\n\n👥 משתמשים: {len(active_users)}\n📋 לידים: {len(leads)}"
    await callback.message.edit_text(stats_text)
    await callback.answer()

@dp.callback_query(F.data == "system_check")
async def handle_system_check(callback: types.CallbackQuery):
    """בדיקת מערכת"""
    try:
        webhook_info = await bot.get_webhook_info()
        
        status = "🟢 פעיל" if webhook_info.url == WEBHOOK_URL else "🔴 לא פעיל"
        
        check_text = (
            "🔍 **בדיקת מערכת**\n\n"
            f"🌐 **Webhook:** {status}\n"
            f"📨 **עדכונים:** {webhook_info.pending_update_count}\n"
            f"👥 **משתמשים:** {len(active_users)}\n"
            f"📋 **לידים:** {len(leads)}\n\n"
        )
        
        if webhook_info.url != WEBHOOK_URL:
            check_text += "**לפתרון:** שלח /fix_webhook"
        
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
        logger.info("📨 Received Telegram webhook")
        
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
            "leads_count": len(leads),
            "webhook_configured": webhook_info.url == WEBHOOK_URL
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/reset-webhook")
async def reset_webhook():
    """איפוס webhook דרך API"""
    try:
        success = await setup_webhook()
        webhook_info = await bot.get_webhook_info()
        
        return {
            "status": "success" if success else "error",
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count,
            "message": "Webhook reset successfully" if success else "Webhook reset failed"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/")
async def root():
    return {
        "message": "CRM Bot is Running",
        "status": "active", 
        "webhook_url": WEBHOOK_URL,
        "endpoints": {
            "health": "GET /health",
            "reset_webhook": "POST /reset-webhook",
            "telegram_webhook": f"POST {WEBHOOK_PATH}"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
