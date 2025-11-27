from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Depends
from telegram.ext import ApplicationBuilder
from contextlib import asynccontextmanager
import uvicorn
import logging
from config import Config
from database import db_manager, get_db
from crm_manager import CRMManager
from bot import bot_manager
from pydantic import BaseModel, validator
import os
from sqlalchemy.orm import Session

# הגדרת logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# מודל ולידציה למידע ליד
class LeadSchema(BaseModel):
    name: str
    phone: str
    email: str = None
    notes: str = None
    source: str = "website"

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()

    @validator('phone')
    def phone_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Phone cannot be empty')
        return v.strip()

    @validator('email')
    def email_optional_but_valid(cls, v):
        if v is None or v == "":
            return None
        # ולידציה בסיסית של אימייל
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.strip()

# משתנה גלובלי לאפליקציית הבוט
bot_application = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """ניהול מחזור חיים של האפליקציה"""
    global bot_application
    
    logger.info("🚀 Starting CRM Bot Application...")
    
    try:
        # אתחול מסד הנתונים
        db_manager.init_db()
        logger.info("✅ Database initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    # בניית והפעלת הבוט
    try:
        bot_application = (
            ApplicationBuilder()
            .token(Config.BOT_TOKEN)
            .build()
        )
        
        bot_manager.setup_bot(bot_application)
        
        # אתחול הבוט
        await bot_application.initialize()
        await bot_application.start()
        
        logger.info("🤖 Telegram Bot started successfully")
        
        # בדיקת חיבור
        bot_info = await bot_application.bot.get_me()
        logger.info(f"✅ Bot connected: @{bot_info.username} ({bot_info.first_name})")
        
    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}")
        bot_application = None
        # אל תעלה exception כאן כדי שהשרת יעבוד גם אם הבוט נכשל
    
    yield  # האפליקציה רצה כאן
    
    # ניקוי משאבים
    logger.info("🛑 Shutting down application...")
    
    if bot_application:
        try:
            await bot_application.stop()
            await bot_application.shutdown()
            logger.info("✅ Bot shutdown completed")
        except Exception as e:
            logger.error(f"❌ Error during bot shutdown: {e}")

# יצירת אפליקציית FastAPI
app = FastAPI(
    title="Telegram CRM Bot",
    description="בוט טלגרם חכם לניהול לידים עם FastAPI backend",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Endpoint ראשי"""
    return {
        "message": "🤖 Telegram CRM Bot is Running",
        "status": "active",
        "version": "1.0.0",
        "features": [
            "Lead Management",
            "Telegram Notifications", 
            "CSV Export",
            "Real-time Statistics"
        ]
    }

@app.get("/health")
async def health_check():
    """Endpoint לבדיקת בריאות המערכת"""
    health_status = {
        "status": "healthy",
        "database": "connected",
        "bot": "running" if bot_application else "not running",
        "timestamp": datetime.now().isoformat()
    }
    
    # בדיקת חיבור למסד נתונים
    try:
        db = db_manager.get_session()
        db.execute("SELECT 1")
        db_manager.close_session(db)
    except Exception as e:
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"
        logger.error(f"❌ Health check - Database error: {e}")
    
    # בדיקת סטטוס הבוט
    if not bot_application:
        health_status["bot"] = "not running"
        health_status["status"] = "degraded"
    
    return health_status

@app.post("/webhook/lead")
async def receive_lead(
    lead: LeadSchema, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    endpoint לקבלת לידים חדשים מהאתר
    """
    logger.info(f"📥 Received new lead: {lead.name} ({lead.phone})")
    
    try:
        # המרה ל-dict
        lead_data = lead.model_dump()
        
        # שמירה במסד הנתונים
        new_lead = CRMManager.add_lead(db, lead_data)
        
        # שליחת התראות למנהלים (ברקע)
        if bot_application:
            background_tasks.add_task(bot_manager.notify_admins, lead_data)
            logger.info("✅ Lead saved and notifications queued")
        else:
            logger.warning("⚠️ Lead saved but bot not available for notifications")
        
        return {
            "status": "success",
            "message": "Lead processed successfully",
            "lead_id": new_lead.id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing lead: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing lead: {str(e)}"
        )

@app.get("/leads/stats")
async def get_leads_stats(db: Session = Depends(get_db)):
    """Endpoint לקבלת סטטיסטיקות לידים"""
    try:
        stats = CRMManager.get_stats(db)
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving statistics")

@app.get("/leads/recent")
async def get_recent_leads(db: Session = Depends(get_db)):
    """Endpoint לקבלת הלידים האחרונים"""
    try:
        leads = CRMManager.get_recent_leads(db, 10)
        return {
            "status": "success",
            "data": [lead.to_dict() for lead in leads],
            "count": len(leads),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Error getting recent leads: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving leads")

# טיפול בשגיאות גלובלי
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """טיפול בשגיאות גלובלי"""
    logger.error(f"❌ Global error: {exc}", exc_info=True)
    return {
        "status": "error",
        "message": "An internal server error occurred",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🌐 Starting server on port {port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # כבוי ב-production
        log_level=Config.LOG_LEVEL.lower()
    )
