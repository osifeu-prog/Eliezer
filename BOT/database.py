import asyncpg
from config import DATABASE_URL, logger

pool = None

async def init_db_pool():
    """יצירת Pool של חיבורים למסד הנתונים"""
    global pool
    if not DATABASE_URL:
        logger.error("DATABASE_URL is missing!")
        return

    try:
        # תיקון קטן לפורמט ה-URL אם Railway נותן postgres://
        dsn = DATABASE_URL.replace("postgres://", "postgresql://")
        pool = await asyncpg.create_pool(dsn)
        logger.info("Database pool created successfully.")
    except Exception as e:
        logger.error(f"Failed to create DB pool: {e}")

async def get_db_pool():
    return pool

async def close_db_pool():
    if pool:
        await pool.close()
        logger.info("Database pool closed.")
