from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
import uvicorn
from bot import create_bot_application
from webhook_handler import process_webhook_update
from config import WEBHOOK_URL, PORT, logger
from database import init_db_pool, close_db_pool
from create_tables import create_tables

bot_app = create_bot_application()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """פונקציית Lifecycle שמטפלת באתחול וסגירת משאבים"""
    logger.info("Starting up...")
    
    # 1. חיבור ואיחול DB
    await init_db_pool()
    await create_tables()
    
    # 2. הפעלת הבוט וה-JobQueue
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.job_queue.start() # מפעיל את מנגנון התזמון
    
    # 3. הגדרת Webhook
    webhook_path = f"{WEBHOOK_URL}/telegram"
    logger.info(f"Setting webhook: {webhook_path}")
    await bot_app.bot.set_webhook(url=webhook_path)
    
    yield
    
    # --- Shutdown ---
    logger.info("Shutting down...")
    await bot_app.job_queue.stop()
    await bot_app.stop()
    await bot_app.shutdown()
    await close_db_pool()
    

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def health_check():
    return {"status": "ok", "system": "Eliezer Advanced CRM AI"}

@app.post("/telegram")
async def telegram_webhook(request: Request):
    """הנתיב שאליו טלגרם שולח עדכונים"""
    try:
        body = await request.json()
        await process_webhook_update(bot_app, body)
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Webhook Error: {e}")
        return Response(status_code=500)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
