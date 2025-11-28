from database import get_db_pool, logger

class CRMManager:
    @staticmethod
    async def add_user(user_id, username, first_name, referred_by=None):
        pool = await get_db_pool()
        if not pool: return
        
        async with pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO users (user_id, username, first_name, referred_by)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id) DO NOTHING
                """, user_id, username, first_name, referred_by)
            except Exception as e:
                logger.error(f"DB Error add_user: {e}")

    @staticmethod
    async def log_interaction(user_id, content, source="ai_chat"):
        pool = await get_db_pool()
        if not pool: return

        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO crm_leads (user_id, message_content, source)
                VALUES ($1, $2, $3)
            """, user_id, content, source)

    @staticmethod
    async def get_referral_count(user_id):
        pool = await get_db_pool()
        if not pool: return 0
        async with pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM users WHERE referred_by = $1", user_id)

crm = CRMManager()
