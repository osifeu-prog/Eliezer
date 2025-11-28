import asyncpg
from config import DATABASE_URL, logger
import io
import csv

pool = None

async def init_db_pool():
    global pool
    if not DATABASE_URL:
        logger.error("DATABASE_URL is missing!")
        return
    try:
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

async def fetch_all_users_csv():
    """שולף את כל נתוני המשתמשים ומחזיר אותם כקובץ CSV בזיכרון."""
    pool = await get_db_pool()
    if not pool: return None

    async with pool.acquire() as conn:
        try:
            # שלוף את כל העמודות הרלוונטיות
            records = await conn.fetch("""
                SELECT user_id, username, first_name, referred_by, campaign_source, lead_score, created_at 
                FROM users 
                ORDER BY created_at DESC
            """)
            
            if not records:
                return None

            # יצירת קובץ בזיכרון
            output = io.StringIO()
            writer = csv.writer(output)
            
            # כתיבת כותרות
            headers = ['user_id', 'username', 'first_name', 'referred_by', 'campaign_source', 'lead_score', 'created_at']
            writer.writerow(headers)
            
            # כתיבת נתונים
            for record in records:
                # הופך את ה-record Object לרשימה של ערכים
                row = [record[h] for h in headers]
                writer.writerow(row)

            output.seek(0)
            return output

        except Exception as e:
            logger.error(f"DB Export Error: {e}")
            return None
