from database import execute_query
from config import logger

class CRMManager:
    @staticmethod
    def add_user(user_id, username, first_name):
        query = """
        INSERT OR IGNORE INTO users (user_id, username, first_name) 
        VALUES (?, ?, ?)
        """
        execute_query(query, (user_id, username, first_name))
        logger.info(f"User {user_id} handled in CRM.")

    @staticmethod
    def create_lead(user_id, note="New interaction"):
        query = """
        INSERT INTO crm_leads (user_id, note) VALUES (?, ?)
        """
        execute_query(query, (user_id, note))
        logger.info(f"Lead created for user {user_id}.")

    @staticmethod
    def get_stats():
        query = "SELECT count(*) as count FROM users"
        res = execute_query(query, fetch_one=True)
        return res['count'] if res else 0

crm = CRMManager()
