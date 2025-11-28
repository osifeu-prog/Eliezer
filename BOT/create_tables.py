from database import get_db_pool, logger

async def create_tables():
    """
    יוצר את סכמת הטבלאות ב-PostgreSQL.
    
    שימו לב: פקודות DROP TABLE הן זמניות! 
    לאחר שהבוט עולה ועובד, יש להסיר שתי פקודות אלו (DROP TABLE) כדי למנוע מחיקת נתונים עתידית.
    """
    pool = await get_db_pool()
    if not pool:
        return

    async with pool.acquire() as conn:
        try:
            # שלב 1 (זמני): מחיקת הטבלאות הישנות כדי לאפשר יצירה מחדש עם סכמה מעודכנת.
            await conn.execute("DROP TABLE IF EXISTS users CASCADE")
            await conn.execute("DROP TABLE IF EXISTS crm_leads CASCADE")
            logger.info("Existing tables DROPPED for schema refresh.")
            
            # שלב 2: יצירת הטבלאות מחדש עם הסכמה המעודכנת
            # טבלת משתמשים - עם שדות ניקוד וקמפיין
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    referred_by BIGINT,
                    campaign_source TEXT,          -- עמודה חדשה
                    lead_score INTEGER DEFAULT 1,  -- עמודה חדשה
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # טבלת CRM / לידים - הוספת סיווג כוונות AI
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS crm_leads (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    message_content TEXT,
                    intent_type TEXT,              -- עמודה חדשה
                    source TEXT DEFAULT 'bot',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            logger.info("Tables created/verified successfully with new schema.")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
