import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class CRMManager:
    """מחלקה לניהול הלוגיקה של ה-CRM"""
    
    def __init__(self, database_manager):
        self.db = database_manager
        self.notification_channels = []
    
    def add_lead(self, name: str, phone: str, email: Optional[str] = None, 
                 source: str = 'website', notes: Optional[str] = None):
        """הוספת ליד חדש"""
        return self.db.add_lead(name, phone, email, source, notes)
    
    def get_recent_leads(self, limit: int = 10) -> List[Dict]:
        """קבלת הלידים האחרונים"""
        leads = self.db.get_leads(limit=limit)
        return [
            {
                'id': lead.id,
                'name': lead.name,
                'phone': lead.phone,
                'email': lead.email,
                'source': lead.source,
                'status': lead.status,
                'created_at': lead.created_at.strftime('%d/%m/%Y %H:%M'),
                'notes': lead.notes
            }
            for lead in leads
        ]
    
    def get_leads_by_status(self, status: str) -> List[Dict]:
        """קבלת לידים לפי סטטוס"""
        leads = self.db.get_leads(status=status)
        return [
            {
                'id': lead.id,
                'name': lead.name,
                'phone': lead.phone,
                'email': lead.email,
                'created_at': lead.created_at.strftime('%d/%m/%Y %H:%M')
            }
            for lead in leads
        ]
    
    def update_lead_status(self, lead_id: int, status: str) -> bool:
        """עדכון סטטוס ליד"""
        valid_statuses = ['new', 'contacted', 'converted', 'lost']
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        
        return self.db.update_lead_status(lead_id, status)
    
    def get_stats(self) -> Dict:
        """קבלת סטטיסטיקות"""
        return self.db.get_stats()
    
    def add_user(self, telegram_id: int, first_name: str, username: Optional[str] = None):
        """הוספת משתמש חדש"""
        return self.db.add_user(telegram_id, first_name, username)
    
    def notify_new_lead(self, lead):
        """שליחת התראה על ליד חדש"""
        logger.info(f"🔔 New lead notification: {lead.name} - {lead.phone}")
        # ניתן להוסיף כאן שליחה להודעות טלגרם למנהלים
    
    def get_daily_report(self) -> Dict:
        """קבלת דוח יומי"""
        stats = self.get_stats()
        
        return {
            'date': datetime.now().strftime('%d/%m/%Y'),
            'new_leads_today': stats['today_leads'],
            'total_leads': stats['total_leads'],
            'conversion_rate': stats['conversion_rate']
        }
