"""
סקריפט לאתחול מסד הנתונים
"""
import logging
from database import db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        logger.info("🔧 Initializing database tables...")
        db_manager.init_db()
        logger.info("✅ Database tables created successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        exit(1)
