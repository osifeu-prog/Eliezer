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

# הגדרת לוגר מפורט
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# קבלת משתני סביבה
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_PATH = "/webhook-123"  # חייב להתאים לכתובת ב-Railway
WEBHOOK_URL = f"https://fun-production-8132.up.railway.app{WEBHOOK_PATH}"
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

# אתחול בוט ו-dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# אחסון נתונים (בפרודקשן יש להשתמש במסד נתונים אמיתי)
leads = []
active_users = set()

class CRMStates(StatesGroup):
    waiting_for_lead_name = State()
    waiting_for_lead_phone = State()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """ניהול מחזור חיים של האפליקציה"""
    logger.info("Starting application...")
    
    try:
        # הגדרת webhook
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(0.1)
        
        await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        logger.info(f"✅ Webhook set successfully: {WEBHOOK_URL}")
        
        # בדיקת webhook
        webhook_info = await bot.get_webhook_info()
        logger.info(f"📋 Webhook info: {webhook_info.url}")
        logger.info(f"📊 Pending updates: {webhook_info.pending_update_count}")
        
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")
    
    yield
    
    logger.info("Shutting down application...")
    await bot.session.close()

app = FastAPI(lifespan=lifespan, title="Telegram CRM Bot")

async def safe_send_message(chat_id: int, text: str, **kwargs):
    """שליחת הודעה בטוחה עם טיפול בשגיאות"""
    try:
        await bot.send_message(chat_id, text, **kwargs)
        return True
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")
        return False

# ===== TELEGRAM HANDLERS =====
@dp.message(CommandStart())
async def handle_start(message: Message):
    """טיפול בפקודת /start"""
    try:
        user_id = message.from_user.id
        active_users.add(user_id)
        
        logger.info(f"👤 User {user_id} started the bot")
        
        # יצירת מקלדת
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 צפה בלידים", callback_data="view_leads")],
            [InlineKeyboardButton(text="📈 סטטיסטיקות", callback_data="view_stats")],
            [InlineKeyboardButton(text="👥 הוסף ליד", callback_data="add_lead")],
            [InlineKeyboardButton(text="🔄 מידע סנכרון", callback_data="sync_info")]
        ])
        
        welcome_text = (
            f"👋 שלום {message.from_user.first_name}!\n\n"
            "🤖 **ברוך הבא לבוט CRM למשרד פרסום**\n\n"
            "✅ הבוט פעיל ומחובר למערכת\n"
            "📞 ניתן לנהל לידים אוטומטית מהאתר\n"
            "📈 מעקב סטטיסטיקות בזמן אמת\n\n"
            "בחר פעולה מהתפריט:"
        )
        
        await message.answer(welcome_text, reply_markup=keyboard)
        logger.info(f"✅ Welcome message sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in start handler: {e}")

@dp.message(Command("help"))
async def handle_help(message: Message):
    """טיפול בפקודת /help"""
    help_text = (
        "🤖 **בוט CRM - עזרה**\n\n"
        "**פקודות זמינות:**\n"
        "/start - התחל שימוש בבוט\n"
        "/leads - הצג לידים אחרונים\n"
        "/stats - הצג סטטיסטיקות\n"
        "/help - הצג עזרה זו\n\n"
        "**סנכרון אתר:**\n"
        "הבוט מקבל לידים אוטומטית דרך webhook"
    )
    await message.answer(help_text)

@dp.message(Command("leads"))
async def handle_leads(message: Message):
    """טיפול בפקודת /leads"""
    try:
        if not leads:
            await message.answer("📝 אין לידים חדשים להצגה.")
            return
        
        leads_text = "📋 **לידים אחרונים:**\n\n"
        for i, lead in enumerate(leads[-5:], 1):
            leads_text += f"{i}. **{lead['name']}**\n"
            leads_text += f"   📞 {lead['phone']}\n"
            leads_text += f"   📅 {lead['date']}\n"
            if lead.get('source'):
                leads_text += f"   🌐 {lead['source']}\n"
            leads_text += "─" * 20 + "\n"
        
        await message.answer(leads_text)
    except Exception as e:
        logger.error(f"Error showing leads: {e}")
        await message.answer("❌ אירעה שגיאה בהצגת הלידים.")

@dp.message(Command("stats"))
async def handle_stats(message: Message):
    """טיפול בפקודת /stats"""
    try:
        total_leads = len(leads)
        today = datetime.now().strftime('%d/%m/%Y')
        today_leads = len([lead for lead in leads if lead['date'].startswith(today)])
        
        stats_text = (
            "📊 **סטטיסטיקות CRM:**\n\n"
            f"👥 **סך לידים:** {total_leads}\n"
            f"📈 **לידים היום:** {today_leads}\n"
            f"👤 **משתמשים פעילים:** {len(active_users)}\n"
            f"🟢 **מערכת:** פעילה\n"
            f"🌐 **Webhook:** מוגדר\n"
        )
        
        await message.answer(stats_text)
    except Exception as e:
        logger.error(f"Error showing stats: {e}")
        await message.answer("❌ אירעה שגיאה בהצגת הסטטיסטיקות.")

@dp.callback_query(F.data == "view_leads")
async def handle_view_leads(callback: types.CallbackQuery):
    """טיפול בלחיצה על 'צפה בלידים'"""
    try:
        if not leads:
            await callback.message.edit_text("📝 אין לידים חדשים להצגה.")
            await callback.answer()
            return
        
        leads_text = "📋 **לידים אחרונים:**\n\n"
        for i, lead in enumerate(leads[-3:], 1):
            leads_text += f"{i}. **{lead['name']}** - {lead['phone']}\n"
        
        await callback.message.edit_text(leads_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in view_leads: {e}")
        await callback.answer("❌ שגיאה בהצגת לידים", show_alert=True)

@dp.callback_query(F.data == "view_stats")
async def handle_view_stats(callback: types.CallbackQuery):
    """טיפול בלחיצה על 'סטטיסטיקות'"""
    try:
        total_leads = len(leads)
        today = datetime.now().strftime('%d/%m/%Y')
        today_leads = len([lead for lead in leads if lead['date'].startswith(today)])
        
        stats_text = (
            "📊 **סטטיסטיקות:**\n\n"
            f"📋 סך לידים: {total_leads}\n"
            f"📈 היום: {today_leads}\n"
            f"👥 משתמשים: {len(active_users)}\n"
            f"🟢 סטטוס: פעיל\n"
        )
        
        await callback.message.edit_text(stats_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in view_stats: {e}")
        await callback.answer("❌ שגיאה בהצגת סטטיסטיקות", show_alert=True)

@dp.callback_query(F.data == "sync_info")
async def handle_sync_info(callback: types.CallbackQuery):
    """טיפול בלחיצה על 'מידע סנכרון'"""
    sync_text = (
        "🔄 **סנכרון עם האתר**\n\n"
        "**סטטוס:** 🟢 פעיל\n"
        "**כתובת Webhook:**\n"
        "`POST https://fun-production-8132.up.railway.app/webhook/lead`\n\n"
        "**פורמט נתונים:**\n"
        "```json\n"
        "{\n"
        '  "name": "שם הלקוח",\n'
        '  "phone": "050-1234567",\n'
        '  "email": "client@example.com",\n'
        '  "source": "website"\n'
        "}\n"
        "```"
    )
    
    await callback.message.edit_text(sync_text)
    await callback.answer()

@dp.message(F.text)
async def handle_all_messages(message: Message):
    """טיפול בכל ההודעות הטקסט"""
    if message.text and not message.text.startswith('/'):
        logger.info(f"Received text message from {message.from_user.id}: {message.text}")
        await message.answer(
            "🤖 אני בוט CRM. השתמש בפקודות:\n"
            "/start - תפריט ראשי\n"
            "/leads - הצג לידים\n" 
            "/stats - סטטיסטיקות\n"
            "/help - עזרה"
        )

# ===== FASTAPI ENDPOINTS =====
@app.post(WEBHOOK_PATH)
async def handle_telegram_webhook(request: Request):
    """טיפול בעדכונים מטלגרם"""
    try:
        update_data = await request.json()
        logger.info(f"📨 Received Telegram update: {update_data}")
        
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(f"❌ Error handling Telegram update: {e}")
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
            raise HTTPException(400, "Missing required fields: name, phone")
        
        # יצירת ליד
        new_lead = {
            'name': data['name'],
            'phone': data['phone'],
            'email': data.get('email', ''),
            'source': data.get('source', 'website'),
            'notes': data.get('notes', ''),
            'date': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        leads.append(new_lead)
        
        # התראה למשתמשים
        lead_message = (
            f"🎯 **ליד חדש!**\n\n"
            f"**שם:** {new_lead['name']}\n"
            f"**טלפון:** {new_lead['phone']}\n"
            f"**מקור:** {new_lead['source']}\n"
            f"**תאריך:** {new_lead['date']}"
        )
        
        # שליחה לכל המשתמשים הפעילים
        sent_count = 0
        for user_id in active_users:
            if await safe_send_message(user_id, lead_message):
                sent_count += 1
        
        logger.info(f"📤 Lead notification sent to {sent_count} users")
        
        return {
            "status": "success",
            "message": "Lead added successfully",
            "lead_id": len(leads),
            "notifications_sent": sent_count
        }
        
    except Exception as e:
        logger.error(f"❌ Error handling website lead: {e}")
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
            "bot": bot_info.username,
            "webhook_url": webhook_info.url,
            "webhook_pending_updates": webhook_info.pending_update_count,
            "total_leads": len(leads),
            "active_users": len(active_users),
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
        "endpoints": {
            "health": "/health",
            "webhook_lead": "POST /webhook/lead",
            "telegram_webhook": f"POST {WEBHOOK_PATH}"
        },
        "usage": "Send /start to the bot on Telegram"
    }

@app.get("/debug")
async def debug_info():
    """מידע דיבאג"""
    try:
        webhook_info = await bot.get_webhook_info()
        return {
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count,
            "last_error": webhook_info.last_error_message,
            "active_users_count": len(active_users),
            "leads_count": len(leads),
            "environment": {
                "bot_token_set": bool(BOT_TOKEN),
                "webhook_url_set": bool(WEBHOOK_URL)
            }
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
