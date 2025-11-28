import sqlite3
from config import logger

DB_NAME = "bot_database.db"

def get_connection():
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def execute_query(query, args=(), fetch_one=False, fetch_all=False):
    conn = get_connection()
    if not conn:
        return None
    
    cursor = conn.cursor()
    try:
        cursor.execute(query, args)
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = True
        return result
    except Exception as e:
        logger.error(f"Query Error: {e}")
        return None
    finally:
        conn.close()
