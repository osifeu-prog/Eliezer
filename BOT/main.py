from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
import uvicorn
from bot import create_bot_application
from webhook_handler import process_webhook_update
from config import WEBHOOK_URL, PORT, TELEGRAM_BOT_TOKEN, logger
from create_tables import init_db

# אתחול הבוט
bot_app = create_bot_application()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Starting up...")
    init_db()  # יצירת טבלאות
    await bot_app.initialize()
    await bot_app.start()
    
    # הגדרת Webhook מול טלגרם
    webhook_path = f"{WEBHOOK_URL}/telegram"
    logger.info(f"Setting webhook to: {webhook_path}")
    await bot_app.bot.set_webhook(url=webhook_path)
    
    yield
    
    # --- Shutdown ---
    logger.info("Shutting down...")
    await bot_app.stop()
    await bot_app.shutdown()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def health_check():
    return {"status": "ok", "bot": "Eliezer"}

@app.post("/telegram")
async def telegram_webhook(request: Request):
    """הנתיב שאליו טלגרם שולח עדכונים"""
    try:
        body = await request.json()
        await process_webhook_update(bot_app, body)
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return Response(status_code=500)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, log_level="info")
