from fastapi import FastAPI, Request, BackgroundTasks
from telegram.ext import ApplicationBuilder
from contextlib import asynccontextmanager
import uvicorn
from config import Config
from database import init_db, SessionLocal
from crm_manager import CRMManager
from bot import setup_bot, notify_admins
from pydantic import BaseModel

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
    init_db() # יצירת טבלאות אם לא קיימות
    
    # בניית הבוט
    bot_app = ApplicationBuilder().token(Config.BOT_TOKEN).build()
    setup_bot(bot_app)
    
    # הפעלת הבוט (Initialize)
    await bot_app.initialize()
    await bot_app.start()
    
    # אם אנחנו בפיתוח לוקאלי, נריץ Polling
    # ב-Production מומלץ להגדיר Webhook לטלגרם, אך בדוגמה זו נשתמש בשיטה ההיברידית לפשטות
    if "localhost" in Config.WEBHOOK_URL or "127.0.0.1" in Config.WEBHOOK_URL:
        await bot_app.updater.start_polling()
        print("🤖 Bot started in Polling mode")
    
    yield
    
    # כיבוי בירידת השרת
    await bot_app.stop()
    await bot_app.shutdown()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def health_check():
    return {"status": "ok", "bot": "running"}

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
        
        # 2. שליחת התראה לטלגרם (ברקע, כדי לא לתקוע את הבקשה מהאתר)
        background_tasks.add_task(notify_admins, bot_app, lead_dict)
        
        return {"status": "success", "lead_id": new_lead.id}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=Config.PORT, reload=True)
