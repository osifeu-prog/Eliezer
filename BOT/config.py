import os
from dataclasses import dataclass

@dataclass
class Config:
    """מחלקה להגדרות הקונפיגורציה"""
    
    # Telegram Bot Token
    BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    # Webhook URL
    WEBHOOK_URL: str = os.getenv('RAILWAY_URL', '') + "/webhook"
    
    # Database settings
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///crm_bot.db')
    
    # Admin user IDs
    ADMIN_IDS: list = None
    
    # CRM settings
    LEAD_EXPIRY_DAYS: int = 30
    AUTO_REMINDER_HOURS: int = 24
    
    def __post_init__(self):
        if self.ADMIN_IDS is None:
            self.ADMIN_IDS = []

# יצירת אובייקט קונפיגורציה גלובלי
config = Config()
