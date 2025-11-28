import os

# Bot configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://eliezer-production.up.railway.app")
PORT = int(os.getenv("PORT", 8080))
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",") if os.getenv("ADMIN_IDS") else []

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
