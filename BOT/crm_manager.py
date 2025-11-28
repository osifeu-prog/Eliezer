from database import get_db_pool, logger

class CRMManager:
    @staticmethod
    async def add_user(user_id, username, first_name, referred_by=None, campaign_source=None):
        pool = await get_db_pool()
        if not pool: return
        
        async with pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO users (user_id, username, first_name, referred_by, campaign_source)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (user_id) DO NOTHING
                """, user_id, username, first_name, referred_by, campaign_source)
            except Exception as e:
                logger.error(f"DB Error add_user: {e}")

    @staticmethod
    async def log_interaction(user_id, content, source="ai_chat", intent_type=None):
        pool = await get_db_pool()
        if not pool: return

        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO crm_leads (user_id, message_content, source, intent_type)
                VALUES ($1, $2, $3, $4)
            """, user_id, content, source, intent_type)
    
    @staticmethod
    async def update_lead_score(user_id, points=1):
        """מעלה את ניקוד הליד (מקסימום 10)"""
        pool = await get_db_pool()
        if not pool: return

        async with pool.acquire() as conn:
            # שימוש ב-LEAST כדי להגביל לניקוד מקסימלי 10
            await conn.execute("""
                UPDATE users SET lead_score = LEAST(lead_score + $1, 10)
                WHERE user_id = $2
            """, points, user_id)
            logger.info(f"Lead score updated for {user_id}. Added {points} points.")

    @staticmethod
    async def get_stats():
        pool = await get_db_pool()
        if not pool: return {"total_users": 0, "avg_score": 0}
        
        async with pool.acquire() as conn:
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            avg_score = await conn.fetchval("SELECT AVG(lead_score) FROM users")
            return {"total_users": total_users, "avg_score": round(float(avg_score or 0), 2)}

    @staticmethod
    async def get_user_lead_score(user_id):
        pool = await get_db_pool()
        if not pool: return 1
        async with pool.acquire() as conn:
            return await conn.fetchval("SELECT lead_score FROM users WHERE user_id = $1", user_id)

    @staticmethod
    async def get_referral_count(user_id):
        """סופר כמה משתמשים הופנו ישירות על ידי המשתמש הזה"""
        pool = await get_db_pool()
        if not pool: return 0
        async with pool.acquire() as conn:
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM users WHERE referred_by = $1
            """, user_id)
            return count or 0

    @staticmethod
    async def get_referral_downline_count(user_id):
        """סופר את כל המשתמשים שהופנו על ידי המשתמש הזה ומטה (דורות)"""
        pool = await get_db_pool()
        if not pool: return 0
        async with pool.acquire() as conn:
            # Recursive CTE (Common Table Expression) to count all downline referrals
            count = await conn.fetchval("""
                WITH RECURSIVE downline AS (
                    -- Anchor member: הדרגה הראשונה שהופנתה ישירות
                    SELECT user_id
                    FROM users
                    WHERE referred_by = $1
                    UNION ALL
                    -- Recursive member: חיבור משתמשים שהופנו על ידי הדרגה הקודמת
                    SELECT u.user_id
                    FROM users u
                    JOIN downline d ON u.referred_by = d.user_id
                )
                SELECT COUNT(*) FROM downline
            """, user_id)
            return count or 0

crm = CRMManager()
