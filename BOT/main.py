from bot import create_application
from config import TOKEN, WEBHOOK_URL, PORT
import logging
import asyncio

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """Main function to run the bot with webhook"""
    try:
        # Create application
        application = create_application()
        
        # Set webhook
        webhook_url = f"{WEBHOOK_URL}/telegram"
        await application.bot.set_webhook(webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")
        
        # Run webhook server
        await application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=webhook_url,
            secret_token=None,
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
