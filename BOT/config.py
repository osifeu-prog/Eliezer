import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    """הגדרות אפליקציה עם ולידציה"""
    
    # Telegram
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found in environment variables")
        raise ValueError("TELEGRAM_BOT_TOKEN is required")
    
    # Admin IDs
    admin_env = os.getenv("ADMIN_IDS", "")
    ADMIN_IDS = []
    if admin_env:
        try:
            ADMIN_IDS = [int(x.strip()) for x in admin_env.split(",") if x.strip().isdigit()]
        except Exception as e:
            logger.warning(f"⚠️ Error parsing ADMIN_IDS: {e}")
    
    if not ADMIN_IDS:
        logger.warning("⚠️ No ADMIN_IDS configured - bot will be inaccessible")
    
    # Webhook / Server
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
    if not WEBHOOK_URL:
        logger.warning("⚠️ WEBHOOK_URL not set - webhook features may not work")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crm_bot.db")
    
    # Fix for Railway PostgreSQL URL
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        logger.info("✅ Fixed PostgreSQL URL format")
    
    # CRM Settings
    CSV_FILENAME = "leads_export.csv"
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate_config(cls):
        """ולידציה של ההגדרות"""
        errors = []
        
        if not cls.BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        
        if not cls.ADMIN_IDS:
            errors.append("At least one ADMIN_ID is required")
        
        if errors:
            error_msg = "Configuration errors:\n" + "\n".join(f"• {error}" for error in errors)
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        logger.info("✅ Configuration validated successfully")
        return True

# ולידציה אוטומטית בעת ייבוא
try:
    Config.validate_config()
except Exception as e:
    logger.error(f"❌ Configuration validation failed: {e}")
