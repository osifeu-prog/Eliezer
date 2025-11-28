import os

# Bot configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + "/telegram"
PORT = int(os.getenv("PORT", 8443))
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")
