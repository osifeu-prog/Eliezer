import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
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

# הגדרת לוגר
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# קבלת משתני סביבה
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_PATH = f"/webhook-123"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://fun-production-8132.up.railway.app") + WEBHOOK_PATH

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
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        await bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Webhook set to: {WEBHOOK_URL}")

# handlers עבור טלגרם
@dp.message(CommandStart())
async def on_start(message: Message):
    """פקודת /start"""
    user_id = message.from_user.id
    users.add(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 צפה בלידים", callback_data="view_leads")],
        [InlineKeyboardButton(text="📈 סטטיסטיקות", callback_data="view_stats")],
        [InlineKeyboardButton(text="👥 הוסף ליד", callback_data="add_lead")]
    ])
    
    await message.answer(
        f"ברוך הבא {message.from_user.first_name}!\n\n"
        "אני בוט ה-CRM של המשרד שלך. אני יכול לעזור לך:\n"
        "• לנהל לידים מהאתר\n"
        "• לעקוב אחר סטטיסטיקות\n"
        "• לסנכרן עם מערכות חיצוניות\n\n"
        "בחר אפשרות מהתפריט:",
        reply_markup=keyboard
    )

@dp.message(Command("leads"))
async def on_leads(message: Message):
    """פקודת /leads - הצגת לידים"""
    if not leads:
        await message.answer("❌ אין לידים חדשים להצגה.")
        return
    
    leads_text = "📋 **לידים אחרונים:**\n\n"
    for i, lead in enumerate(leads[-10:], 1):
        leads_text += f"{i}. **שם:** {lead['name']}\n"
        leads_text += f"   **טלפון:** {lead['phone']}\n"
        leads_text += f"   **תאריך:** {lead['date']}\n"
        leads_text += "─" * 20 + "\n"
    
    await message.answer(leads_text)

@dp.message(Command("stats"))
async def on_stats(message: Message):
    """פקודת /stats - הצגת סטטיסטיקות"""
    total_leads = len(leads)
    today_leads = len([lead for lead in leads if lead['date'] == datetime.now().strftime('%d/%m/%Y')])
    total_users = len(users)
    
    stats_text = "📊 **סטטיסטיקות CRM:**\n\n"
    stats_text += f"👥 **סך הכל לידים:** {total_leads}\n"
    stats_text += f"📈 **לידים היום:** {today_leads}\n"
    stats_text += f"👤 **משתמשים פעילים:** {total_users}\n"
    
    await message.answer(stats_text)

@dp.callback_query(F.data == "view_leads")
async def on_view_leads(callback: types.CallbackQuery):
    """הצגת לידים בלחיצת כפתור"""
    if not leads:
        await callback.message.edit_text("❌ אין לידים חדשים להצגה.")
        return
    
    leads_text = "📋 **לידים אחרונים:**\n\n"
    for i, lead in enumerate(leads[-5:], 1):
        leads_text += f"{i}. **{lead['name']}** - {lead['phone']}\n"
    
    await callback.message.edit_text(leads_text)

@dp.callback_query(F.data == "view_stats")
async def on_view_stats(callback: types.CallbackQuery):
    """הצגת סטטיסטיקות בלחיצת כפתור"""
    total_leads = len(leads)
    today_leads = len([lead for lead in leads if lead['date'] == datetime.now().strftime('%d/%m/%Y')])
    
    stats_text = "📊 **סטטיסטיקות:**\n\n"
    stats_text += f"👥 סך לידים: {total_leads}\n"
    stats_text += f"📈 היום: {today_leads}\n"
    
    await callback.message.edit_text(stats_text)

@dp.callback_query(F.data == "add_lead")
async def on_add_lead(callback: types.CallbackQuery, state: FSMContext):
    """הוספת ליד חדש"""
    await callback.message.edit_text("📝 אנא הזן את שם הלקוח:")
    await state.set_state(CRMStates.waiting_for_lead_name)

@dp.message(CRMStates.waiting_for_lead_name)
async def on_lead_name_received(message: Message, state: FSMContext):
    """קבלת שם הלקוח"""
    await state.update_data(lead_name=message.text)
    await message.answer("📞 אנא הזן את מספר הטלפון של הלקוח:")
    await state.set_state(CRMStates.waiting_for_lead_phone)

@dp.message(CRMStates.waiting_for_lead_phone)
async def on_lead_phone_received(message: Message, state: FSMContext):
    """קבלת טלפון הלקוח ושמירת הליד"""
    data = await state.get_data()
    lead_name = data.get('lead_name')
    lead_phone = message.text
    
    # שמירת הליד
    new_lead = {
        'name': lead_name,
        'phone': lead_phone,
        'date': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'source': 'telegram'
    }
    leads.append(new_lead)
    
    # שליחת הודעה למשתמש
    await message.answer(f"✅ ליד נוסף בהצלחה!\n**שם:** {lead_name}\n**טלפון:** {lead_phone}")
    
    # שליחת התראה למנהלים
    for user_id in users:
        try:
            await bot.send_message(
                user_id,
                f"🔔 **ליד חדש נוסף!**\n\n**שם:** {lead_name}\n**טלפון:** {lead_phone}\n**מקור:** טלגרם"
            )
        except Exception as e:
            logger.error(f"Failed to send notification to user {user_id}: {e}")
    
    await state.clear()

# endpoint עבור webhook מטלגרם
@app.post(WEBHOOK_PATH)
async def handle_update(request: Request):
    """טיפול בעדכונים מטלגרם"""
    try:
        update_data = await request.json()
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(f"Error handling update: {e}")
        return JSONResponse(content={"status": "error"}, status_code=500)

# endpoint לקבלת לידים מהאתר
@app.post("/webhook/lead")
async def handle_webhook_lead(request: Request):
    """טיפול בלידים מהאתר"""
    try:
        data = await request.json()
        
        # וידוא שדות חובה
        if not data.get('name') or not data.get('phone'):
            raise HTTPException(status_code=400, detail="Missing required fields: name, phone")
        
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
        lead_message = f"🌐 **ליד חדש מהאתר!**\n\n**שם:** {new_lead['name']}\n**טלפון:** {new_lead['phone']}\n**אימייל:** {new_lead['email']}\n**הערות:** {new_lead['notes']}"
        
        for user_id in users:
            try:
                await bot.send_message(user_id, lead_message)
            except Exception as e:
                logger.error(f"Failed to send lead notification to user {user_id}: {e}")
        
        return JSONResponse(content={"status": "success", "message": "Lead added successfully"})
    
    except Exception as e:
        logger.error(f"Error handling webhook lead: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

# endpoint לבדיקת סטטוס
@app.get("/health")
async def health_check():
    """בדיקת בריאות השרת"""
    return JSONResponse(content={"status": "healthy", "service": "Telegram CRM Bot"})

# endpoint ראשי
@app.get("/")
async def root():
    """דף הבית"""
    return {"message": "Telegram CRM Bot is running!"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
