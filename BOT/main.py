from bot import create_application
from config import TOKEN, WEBHOOK_URL, PORT
import logging
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse
from starlette.routing import Route

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create bot application
application = create_application()

async def set_webhook():
    """Set the webhook for Telegram"""
    webhook_url = f"{WEBHOOK_URL}/telegram"
    await application.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")

async def telegram_webhook(request: Request):
    """Handle incoming Telegram updates via webhook"""
    try:
        data = await request.json()
        update = await application.update_queue.get()
        await application.process_update(update)
        return Response()
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return Response(status_code=500)

async def health_check(request: Request):
    """Health check endpoint"""
    return PlainTextResponse("OK")

# Create Starlette app
app = Starlette(
    routes=[
        Route("/telegram", telegram_webhook, methods=["POST"]),
        Route("/health", health_check, methods=["GET"]),
        Route("/", health_check, methods=["GET"]),
    ]
)

@app.on_event("startup")
async def on_startup():
    """Initialize the bot application on startup"""
    await application.initialize()
    await application.start()
    await set_webhook()

@app.on_event("shutdown")
async def on_shutdown():
    """Shutdown the bot application"""
    await application.stop()
    await application.shutdown()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )
