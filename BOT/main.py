from fastapi import FastAPI, Request, BackgroundTasks
from telegram.ext import ApplicationBuilder
from contextlib import asynccontextmanager
import uvicorn
from config import Config
from database import init_db, SessionLocal
from crm_manager import CRMManager
from bot import setup_bot, notify_admins
from pydantic import BaseModel
import os

# מודל ולידציה למידע שמגיע מהאתר
class LeadSchema(BaseModel):
    name: str
    phone: str
    email: str = None
    notes: str = None
    source: str = "website"

# משתנה גלובלי לאפליקציית הבוט
bot_app = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # הפעלה בעליית השרת
    global bot_app
    print("🚀 Starting application...")
    
    try:
        init_db() # יצירת טבלאות
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️ Database error: {e}")

    # בניית הבוט
    bot_app = ApplicationBuilder().token(Config.BOT_TOKEN).build()
    setup_bot(bot_app)
    
    await bot_app.initialize()
    await bot_app.start()
    
    # הגדרת Webhook מול טלגרם
    webhook_url = Config.WEBHOOK_URL
    if not webhook_url.startswith("http"):
        webhook_url = f"https://{webhook_url}"
    
    # הוספת הנתיב המדויק
    webhook_path = f"{webhook_url}/webhook/lead" 
    
    # שים לב: בוט טלגרם צריך כתובת משלו לקבלת עדכונים מטלגרם, אבל כאן אנחנו משתמשים בו לשליחת הודעות.
    # אם אתה רוצה שהבוט יגיב להודעות בטלגרם עצמו (כמו /start), צריך להגדיר לו webhook נפרד.
    # כרגע לצורך ה-CRM הפשוט, זה מספיק.
    
    print(f"🤖 Bot started. Webhook URL base: {webhook_url}")
    
    yield
    
    # כיבוי בירידת השרת
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()

app = FastAPI(lifespan=lifespan)

# --- התיקון הקריטי לרילויי ---
@app.get("/health")
def health_check():
    return {"status": "ok", "bot": "running"}

@app.get("/")
def root():
    return {"message": "Telegram CRM Bot is Running"}

@app.post("/webhook/lead")
async def receive_lead(lead: LeadSchema, background_tasks: BackgroundTasks):
    """
    נקודת הקצה שמקבלת לידים מהאתר
    """
    db = SessionLocal()
    try:
        # 1. שמירה בדאטה בייס
        lead_dict = lead.model_dump()
        new_lead = CRMManager.add_lead(db, lead_dict)
        
        # 2. שליחת התראה לטלגרם (ברקע)
        if bot_app:
            background_tasks.add_task(notify_admins, bot_app, lead_dict)
        
        return {"status": "success", "lead_id": new_lead.id}
    except Exception as e:
        print(f"Error processing lead: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
