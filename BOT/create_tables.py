from database import get_connection, logger

def init_db():
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        
        # טבלת משתמשים לדוגמה
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # טבלת לוגים או CRM פנימי
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crm_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                status TEXT DEFAULT 'new',
                note TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database tables created successfully.")
    else:
        logger.error("Failed to connect to DB for initialization.")

if __name__ == "__main__":
    init_db()
