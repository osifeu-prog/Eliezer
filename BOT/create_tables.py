from database import get_db_pool, logger

async def create_tables():
    pool = await get_db_pool()
    if not pool:
        return

    async with pool.acquire() as conn:
        try:
            # טבלת משתמשים
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    referred_by BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # טבלת CRM / לידים
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS crm_leads (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    message_content TEXT,
                    source TEXT DEFAULT 'bot',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            logger.info("Tables created/verified successfully.")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
