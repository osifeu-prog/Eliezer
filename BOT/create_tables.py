from database import get_db_pool, logger

async def create_tables():
    pool = await get_db_pool()
    if not pool:
        return

    async with pool.acquire() as conn:
        try:
            # טבלת משתמשים - עם שדות ניקוד וקמפיין
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    referred_by BIGINT,
                    campaign_source TEXT,          -- חדש: קוד קמפיין מ-UTM/Start Param
                    lead_score INTEGER DEFAULT 1,  -- חדש: ניקוד הליד (1-10)
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # טבלת CRM / לידים - הוספת סיווג כוונות AI
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS crm_leads (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    message_content TEXT,
                    intent_type TEXT,              -- חדש: סיווג כוונות ע"י AI
                    source TEXT DEFAULT 'bot',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            logger.info("Tables created/verified successfully with new schema.")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
