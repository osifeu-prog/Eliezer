import os
import logging

# הגדרות לוגים
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=LOG_LEVEL
)
logger = logging.getLogger(__name__)

# טוקנים ופרטי בוט
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8080))

# ניהול הרשאות וקבוצות
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
LOG_GROUP_ID = os.getenv("LOG_GROUP_ID") 
SUPPORT_GROUP_ID = os.getenv("SUPPORT_GROUP_ID")

# משתנים חדשים לניהול
DATABASE_URL = os.getenv("DATABASE_URL")
DB_EXPORT_PASSKEY = os.getenv("DB_EXPORT_PASSKEY") # סיסמה סודית לייצוא נתונים

# AI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

# וודא שהטוקן קיים
if not TELEGRAM_BOT_TOKEN:
    logger.error("Must provide TELEGRAM_BOT_TOKEN!")
