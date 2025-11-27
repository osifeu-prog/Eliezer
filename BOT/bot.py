import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, WebhookInfo
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import json
from datetime import datetime
import aiohttp

# הגדרת לוגר
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# קבלת משתני סביבה
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_PATH = f"/webhook-123"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://fun-production-8132.up.railway.app") + WEBHOOK_PATH
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # הוסף את ה-chat ID שלך כאן

# אתחול בוט ו-dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# מדינות עבור FSM
class CRMStates(StatesGroup):
    waiting_for_lead_name = State()
    waiting_for_lead_phone = State()

# מילון זמני לאחסון לידים (בפרודקשן יש להשתמש במסד נתונים)
leads = []
users = set()

# הגדרת FastAPI עם lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    await set_webhook()
    yield
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

async def set_webhook():
    """הגדרת webhook עבור הבוט"""
    try:
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Current webhook: {webhook_info.url}")
        
        if webhook_info.url != WEBHOOK_URL:
            await bot.set_webhook(
                url=WEBHOOK_URL,
                drop_pending_updates=True
            )
            logger.info(f"Webhook set to: {WEBHOOK_URL}")
        else:
            logger.info("Webhook already set correctly")
            
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")

async def send_admin_notification(message: str):
    """שליחת התראה למנהל"""
    if ADMIN_CHAT_ID:
        try:
            await bot.send_message(ADMIN_CHAT_ID, message)
        except Exception as e:
            logger.error(f"Failed to send admin notification: {e}")

# handlers עבור טלגרם
@dp.message(CommandStart())
async def on_start(message: Message):
    """פקודת /start"""
    try:
        user_id = message.from_user.id
        users.add(user_id)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 צפה בלידים", callback_data="view_leads")],
            [InlineKeyboardButton(text="📈 סטטיסטיקות", callback_data="view_stats")],
            [InlineKeyboardButton(text="👥 הוסף ליד", callback_data="add_lead")],
            [InlineKeyboardButton(text="🔄 סנכרון אתר", callback_data="sync_website")]
        ])
        
        welcome_text = (
            f"ברוך הבא {message.from_user.first_name}!\n\n"
            "🤖 **בוט CRM למשרד פרסום**\n\n"
            "אני יכול לעזור לך:\n"
            "• לנהל לידים מהאתר\n"
            "• לעקוב אחר סטטיסטיקות\n"
            "• לסנכרן עם מערכות חיצוניות\n\n"
            "בחר אפשרות מהתפריט:"
        )
        
        await message.answer(welcome_text, reply_markup=keyboard)
        
        # הודעה למנהל על משתמש חדש
        await send_admin_notification(
            f"👤 משתמש חדש בבוט:\n"
            f"שם: {message.from_user.first_name}\n"
            f"Username: @{message.from_user.username}\n"
            f"ID: {user_id}"
        )
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")

@dp.message(Command("leads"))
async def on_leads(message: Message):
    """פקודת /leads - הצגת לידים"""
    try:
        if not leads:
            await message.answer("❌ אין לידים חדשים להצגה.")
            return
        
        leads_text = "📋 **לידים אחרונים:**\n\n"
        for i, lead in enumerate(leads[-10:], 1):
            leads_text += f"{i}. **שם:** {lead['name']}\n"
            leads_text += f"   **טלפון:** {lead['phone']}\n"
            leads_text += f"   **תאריך:** {lead['date']}\n"
            if lead.get('email'):
                leads_text += f"   **אימייל:** {lead['email']}\n"
            if lead.get('source'):
                leads_text += f"   **מקור:** {lead['source']}\n"
            leads_text += "─" * 20 + "\n"
        
        await message.answer(leads_text)
    except Exception as e:
        logger.error(f"Error showing leads: {e}")
        await message.answer("❌ אירעה שגיאה בהצגת הלידים.")

@dp.message(Command("stats"))
async def on_stats(message: Message):
    """פקודת /stats - הצגת סטטיסטיקות"""
    try:
        total_leads = len(leads)
        today = datetime.now().strftime('%d/%m/%Y')
        today_leads = len([lead for lead in leads if lead['date'].startswith(today)])
        total_users = len(users)
        
        stats_text = (
            "📊 **סטטיסטיקות CRM:**\n\n"
            f"👥 **סך הכל לידים:** {total_leads}\n"
            f"📈 **לידים היום:** {today_leads}\n"
            f"👤 **משתמשים פעילים:** {total_users}\n"
            f"🌐 **Webhook:** פעיל\n"
        )
        
        await message.answer(stats_text)
    except Exception as e:
        logger.error(f"Error showing stats: {e}")
        await message.answer("❌ אירעה שגיאה בהצגת הסטטיסטיקות.")

@dp.message(Command("help"))
async def on_help(message: Message):
    """פקודת /help - הצגת עזרה"""
    help_text = (
        "🤖 **בוט CRM למשרד פרסום**\n\n"
        "**פקודות זמינות:**\n"
        "/start - התחל שימוש בבוט\n"
        "/leads - הצג לידים אחרונים\n"
        "/stats - הצג סטטיסטיקות\n"
        "/help - הצג עזרה זו\n\n"
        "**סנכרון עם האתר:**\n"
        "הבוט מקבל לידים אוטומטית מהאתר דרך webhook בכתובת:\n"
        f"`POST {WEBHOOK_URL.replace('/webhook-123', '')}/webhook/lead`\n\n"
        "**פורמט הליד:**\n"
        "```json\n"
        "{\n"
        '  "name": "שם הלקוח",\n'
        '  "phone": "050-1234567",\n'
        '  "email": "email@example.com",\n'
        '  "source": "website",\n'
        '  "notes": "הערות נוספות"\n'
        "}\n"
        "```"
    )
    
    await message.answer(help_text)

@dp.callback_query(F.data == "view_leads")
async def on_view_leads(callback: types.CallbackQuery):
    """הצגת לידים בלחיצת כפתור"""
    try:
        if not leads:
            await callback.message.edit_text("❌ אין לידים חדשים להצגה.")
            return
        
        leads_text = "📋 **לידים אחרונים:**\n\n"
        for i, lead in enumerate(leads[-5:], 1):
            leads_text += f"{i}. **{lead['name']}** - {lead['phone']}\n"
            if lead.get('source'):
                leads_text += f"   ({lead['source']})\n"
        
        await callback.message.edit_text(leads_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in view_leads callback: {e}")
        await callback.answer("❌ אירעה שגיאה.", show_alert=True)

@dp.callback_query(F.data == "view_stats")
async def on_view_stats(callback: types.CallbackQuery):
    """הצגת סטטיסטיקות בלחיצת כפתור"""
    try:
        total_leads = len(leads)
        today = datetime.now().strftime('%d/%m/%Y')
        today_leads = len([lead for lead in leads if lead['date'].startswith(today)])
        
        stats_text = (
            "📊 **סטטיסטיקות:**\n\n"
            f"👥 סך לידים: {total_leads}\n"
            f"📈 היום: {today_leads}\n"
            f"🟢 מערכת: פעילה\n"
        )
        
        await callback.message.edit_text(stats_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in view_stats callback: {e}")
        await callback.answer("❌ אירעה שגיאה.", show_alert=True)

@dp.callback_query(F.data == "add_lead")
async def on_add_lead(callback: types.CallbackQuery, state: FSMContext):
    """הוספת ליד חדש"""
    try:
        await callback.message.edit_text("📝 אנא הזן את שם הלקוח:")
        await state.set_state(CRMStates.waiting_for_lead_name)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in add_lead callback: {e}")
        await callback.answer("❌ אירעה שגיאה.", show_alert=True)

@dp.message(CRMStates.waiting_for_lead_name)
async def on_lead_name_received(message: Message, state: FSMContext):
    """קבלת שם הלקוח"""
    try:
        await state.update_data(lead_name=message.text)
        await message.answer("📞 אנא הזן את מספר הטלפון של הלקוח:")
        await state.set_state(CRMStates.waiting_for_lead_phone)
    except Exception as e:
        logger.error(f"Error receiving lead name: {e}")
        await message.answer("❌ אירעה שגיאה. נסה שוב.")

@dp.message(CRMStates.waiting_for_lead_phone)
async def on_lead_phone_received(message: Message, state: FSMContext):
    """קבלת טלפון הלקוח ושמירת הליד"""
    try:
        data = await state.get_data()
        lead_name = data.get('lead_name')
        lead_phone = message.text
        
        # שמירת הליד
        new_lead = {
            'name': lead_name,
            'phone': lead_phone,
            'date': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'source': 'telegram_bot'
        }
        leads.append(new_lead)
        
        # שליחת הודעה למשתמש
        await message.answer(
            f"✅ **ליד נוסף בהצלחה!**\n\n"
            f"**שם:** {lead_name}\n"
            f"**טלפון:** {lead_phone}\n"
            f"**תאריך:** {new_lead['date']}"
        )
        
        # שליחת התראה למנהלים
        notification_text = (
            f"👤 **ליד חדש נוסף!**\n\n"
            f"**שם:** {lead_name}\n"
            f"**טלפון:** {lead_phone}\n"
            f"**מקור:** בוט טלגרם\n"
            f"**תאריך:** {new_lead['date']}"
        )
        
        # שליחה למנהל
        await send_admin_notification(notification_text)
        
        # שליחה לכל המשתמשים הרשומים
        for user_id in users:
            if user_id != message.from_user.id:  # לא לשלוח למי שהוסיף
                try:
                    await bot.send_message(user_id, notification_text)
                except Exception as e:
                    logger.error(f"Failed to send notification to user {user_id}: {e}")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error receiving lead phone: {e}")
        await message.answer("❌ אירעה שגיאה בשמירת הליד.")
        await state.clear()

@dp.callback_query(F.data == "sync_website")
async def on_sync_website(callback: types.CallbackQuery):
    """הצגת מידע על סנכרון עם האתר"""
    try:
        sync_text = (
            "🔄 **סנכרון עם האתר**\n\n"
            "**סטטוס Webhook:** 🟢 פעיל\n"
            f"**כתובת:** `{WEBHOOK_URL.replace('/webhook-123', '')}`\n\n"
            "**לקבלת לידים מהאתר, שלח POST request ל:**\n"
            "`/webhook/lead`\n\n"
            "**פורמט הנתונים:**\n"
            "```json\n"
            "{\n"
            '  "name": "שם הלקוח",\n'
            '  "phone": "050-1234567",\n'
            '  "email": "email@example.com",\n'
            '  "source": "website",\n'
            '  "notes": "הערות נוספות"\n'
            "}\n"
            "```"
        )
        
        await callback.message.edit_text(sync_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in sync_website callback: {e}")
        await callback.answer("❌ אירעה שגיאה.", show_alert=True)

# endpoint עבור webhook מטלגרם
@app.post(WEBHOOK_PATH)
async def handle_telegram_update(request: Request):
    """טיפול בעדכונים מטלגרם"""
    try:
        update_data = await request.json()
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(f"Error handling Telegram update: {e}")
        return JSONResponse(
            content={"status": "error", "message": str(e)}, 
            status_code=500
        )

# endpoint לקבלת לידים מהאתר
@app.post("/webhook/lead")
async def handle_webhook_lead(request: Request):
    """טיפול בלידים מהאתר"""
    try:
        data = await request.json()
        logger.info(f"Received lead from website: {data}")
        
        # וידוא שדות חובה
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
            'date': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        
        leads.append(new_lead)
        
        # שליחת התראה למשתמשים
        lead_message = (
            f"🌐 **ליד חדש מהאתר!**\n\n"
            f"**שם:** {new_lead['name']}\n"
            f"**טלפון:** {new_lead['phone']}\n"
            f"**אימייל:** {new_lead['email'] or 'לא צוין'}\n"
            f"**מקור:** {new_lead['source']}\n"
            f"**הערות:** {new_lead['notes'] or 'אין'}\n"
            f"**תאריך:** {new_lead['date']}"
        )
        
        # שליחה למנהל
        await send_admin_notification(lead_message)
        
        # שליחה לכל המשתמשים הרשומים
        for user_id in users:
            try:
                await bot.send_message(user_id, lead_message)
            except Exception as e:
                logger.error(f"Failed to send lead notification to user {user_id}: {e}")
        
        return JSONResponse(
            content={
                "status": "success", 
                "message": "Lead added successfully",
                "lead_id": len(leads)
            }
        )
    
    except Exception as e:
        logger.error(f"Error handling webhook lead: {e}")
        return JSONResponse(
            content={"status": "error", "message": str(e)}, 
            status_code=500
        )

# endpoint לבדיקת סטטוס
@app.get("/health")
async def health_check():
    """בדיקת בריאות השרת"""
    try:
        # בדיקה שהבוט פעיל
        bot_info = await bot.get_me()
        
        return JSONResponse(content={
            "status": "healthy",
            "service": "Telegram CRM Bot",
            "bot_username": bot_info.username,
            "total_leads": len(leads),
            "active_users": len(users),
            "webhook_url": WEBHOOK_URL
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=500
        )

# endpoint ראשי
@app.get("/")
async def root():
    """דף הבית"""
    return {
        "message": "Telegram CRM Bot is running!",
        "endpoints": {
            "health": "/health",
            "webhook_lead": "/webhook/lead",
            "telegram_webhook": WEBHOOK_PATH
        },
        "stats": {
            "total_leads": len(leads),
            "active_users": len(users)
        }
    }

# endpoint לקבלת סטטיסטיקות
@app.get("/stats")
async def api_stats():
    """API לסטטיסטיקות"""
    total_leads = len(leads)
    today = datetime.now().strftime('%d/%m/%Y')
    today_leads = len([lead for lead in leads if lead['date'].startswith(today)])
    
    return {
        "total_leads": total_leads,
        "today_leads": today_leads,
        "active_users": len(users),
        "sources": {
            lead.get('source', 'unknown'): len([l for l in leads if l.get('source') == lead.get('source')])
            for lead in leads
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
