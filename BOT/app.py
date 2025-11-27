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

# ===== ENVIRONMENT VARIABLES =====
# כל המשתנים נקראים רק מ-environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook-123")
RAILWAY_URL = os.getenv("RAILWAY_URL", "https://fun-production-8132.up.railway.app")
WEBHOOK_URL = f"{RAILWAY_URL}{WEBHOOK_PATH}"
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# ===== VALIDATION =====
# בדיקה שהמשתנים החיוניים קיימים
if not BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN is missing! Please set it in Railway environment variables.")
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

if not RAILWAY_URL:
    logger.error("❌ RAILWAY_URL is missing! Please set it in Railway environment variables.")
    raise ValueError("RAILWAY_URL environment variable is required")

logger.info(f"✅ Environment loaded - Bot: {'✓' if BOT_TOKEN else '✗'}, URL: {'✓' if RAILWAY_URL else '✗'}")

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
        logger.error("🔧 Please check your BOT_TOKEN and RAILWAY_URL environment variables")
    
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

# ... (כל שאר הפונקציות נשארות אותו דבר כמו בקוד הקודם)
# המשך הקוד זהה לקוד הקודם, רק ללא ה-hardcoded token

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
        "environment": "production",
        "endpoints": {
            "health": "GET /health",
            "webhook_lead": "POST /webhook/lead",
            "reset_webhook": "POST /reset-webhook",
            "telegram_webhook": f"POST {WEBHOOK_PATH}"
        },
        "usage": "Send /start to your bot on Telegram",
        "documentation": "Use /help in the bot for instructions"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
