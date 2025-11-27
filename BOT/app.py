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

# הגדרת לוגר
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# קבלת משתני סביבה
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8274046661:AAF3fCbwL4c6Uj6qJ9xY9wXqZ9xY9wXqZ9x")
WEBHOOK_PATH = "/webhook-123"
WEBHOOK_URL = f"https://fun-production-8132.up.railway.app{WEBHOOK_PATH}"

# אתחול בוט
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# נתונים
leads = []
users = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """ניהול מחזור חיים"""
    logger.info("🚀 Starting application...")
    
    try:
        # מחק webhook קיים והגדר חדש
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(1)
        
        await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        logger.info(f"✅ Webhook set to: {WEBHOOK_URL}")
        
        # בדוק את ה-webhook
        webhook_info = await bot.get_webhook_info()
        logger.info(f"📋 Webhook info: {webhook_info.url}")
        logger.info(f"📊 Pending updates: {webhook_info.pending_update_count}")
        
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")
    
    yield
    
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

# ===== TELEGRAM HANDLERS =====
@dp.message(CommandStart())
async def handle_start(message: Message):
    """טיפול ב-/start"""
    try:
        user_id = message.from_user.id
        users.add(user_id)
        
        logger.info(f"👤 User {user_id} started the bot")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 צפה בלידים", callback_data="view_leads")],
            [InlineKeyboardButton(text="📈 סטטיסטיקות", callback_data="view_stats")],
            [InlineKeyboardButton(text="👥 הוסף ליד", callback_data="add_lead")],
        ])
        
        welcome_text = (
            f"👋 שלום {message.from_user.first_name}!\n\n"
            "🤖 **בוט CRM למשרד פרסום**\n\n"
            "המערכת פעילה ומוכנה לקבל לידים!\n\n"
            "בחר פעולה:"
        )
        
        await message.answer(welcome_text, reply_markup=keyboard)
        logger.info(f"✅ Sent welcome to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in start: {e}")

@dp.message(Command("help"))
async def handle_help(message: Message):
    """טיפול ב-/help"""
    await message.answer(
        "🤖 **בוט CRM - עזרה**\n\n"
        "פקודות:\n"
        "/start - התחל\n"
        "/leads - הצג לידים\n"
        "/stats - סטטיסטיקות\n"
        "/debug - מידע טכני"
    )

@dp.message(Command("debug"))
async def handle_debug(message: Message):
    """טיפול ב-/debug"""
    webhook_info = await bot.get_webhook_info()
    
    debug_text = (
        "🐛 **מידע Debug:**\n\n"
        f"👤 Users: {len(users)}\n"
        f"📋 Leads: {len(leads)}\n"
        f"🌐 Webhook: {webhook_info.url}\n"
        f"⏳ Pending: {webhook_info.pending_update_count}\n"
        f"❌ Last Error: {webhook_info.last_error_date}\n"
        f"💬 Error Msg: {webhook_info.last_error_message}"
    )
    
    await message.answer(debug_text)

@dp.message(Command("leads"))
async def handle_leads(message: Message):
    """טיפול ב-/leads"""
    if not leads:
        await message.answer("📝 אין לידים להצגה.")
        return
    
    leads_text = "📋 **לידים:**\n\n"
    for lead in leads[-5:]:
        leads_text += f"• {lead['name']} - {lead['phone']}\n"
    
    await message.answer(leads_text)

@dp.message(F.text)
async def handle_text(message: Message):
    """טיפול בהודעות טקסט כלליות"""
    logger.info(f"📨 Received text: {message.text} from {message.from_user.id}")
    await message.answer("🤖 השתמש ב-/start להתחלה")

# ===== FASTAPI ENDPOINTS =====
@app.post(WEBHOOK_PATH)
async def handle_webhook(request: Request):
    """טיפול בעדכונים מטלגרם"""
    try:
        update_data = await request.json()
        logger.info(f"📨 Received update: {update_data}")
        
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health_check():
    """בדיקת בריאות"""
    try:
        webhook_info = await bot.get_webhook_info()
        return {
            "status": "healthy",
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count,
            "users": len(users),
            "leads": len(leads)
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/reset-webhook")
async def reset_webhook():
    """איפוס webhook"""
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(1)
        await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)
        
        webhook_info = await bot.get_webhook_info()
        return {
            "status": "reset",
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/")
async def root():
    return {"message": "CRM Bot Running", "status": "active"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
