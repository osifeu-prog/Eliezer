from telegram import Update
from telegram.ext import Application
from config import logger

async def process_webhook_update(application: Application, request_body: dict):
    try:
        update = Update.de_json(request_body, application.bot)
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
