import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # רשימת מנהלים - המרת מחרוזת לרשימת מספרים
    admin_env = os.getenv("ADMIN_IDS", "")
    ADMIN_IDS = [int(x.strip()) for x in admin_env.split(",") if x.strip().isdigit()]
    
    # Webhook / Server
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:8000")
    
    # Database
    # תיקון באג ידוע ב-Railway: החלפת postgres:// ב-postgresql://
    db_url = os.getenv("DATABASE_URL", "sqlite:///./crm_bot.db")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    DATABASE_URL = db_url

    # CRM Settings
    CSV_FILENAME = "leads_export.csv"
