import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    # רשימת ה-ID של המנהלים בטלגרם (מופרדים בפסיק)
    ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
    
    # Webhook / Server
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:8000")
    PORT = int(os.getenv("PORT", 8000))
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crm_bot.db")

    # CRM Settings
    CSV_FILENAME = "leads_export.csv"
