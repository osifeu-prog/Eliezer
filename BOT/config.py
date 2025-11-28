import os

# Bot configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://eliezer-production.up.railway.app")
PORT = int(os.getenv("PORT", 8080))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Validate required environment variables
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL environment variable is required")
