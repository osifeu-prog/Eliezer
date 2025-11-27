from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database import Lead
from datetime import datetime, date
import csv
import os
import logging

logger = logging.getLogger(__name__)

class CRMManager:
    """מנהל CRM עם טיפול מלא בשגיאות"""
    
    @staticmethod
    def add_lead(db: Session, data: dict):
        """
        הוספת ליד חדש עם ולידציה
        """
        try:
            # ולידציה של שדות חובה
            if not data.get('name') or not data.get('phone'):
                raise ValueError("Name and phone are required fields")
            
            new_lead = Lead(
                name=data['name'].strip(),
                phone=data['phone'].strip(),
                email=data.get('email', '').strip() if data.get('email') else None,
                source=data.get('source', 'website').strip(),
                notes=data.get('notes', '').strip() if data.get('notes') else None
            )
            
            db.add(new_lead)
            db.commit()
            db.refresh(new_lead)
            
            logger.info(f"✅ New lead added: {new_lead.name} ({new_lead.phone})")
            return new_lead
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"❌ Database error adding lead: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error adding lead: {e}")
            raise
    
    @staticmethod
    def get_recent_leads(db: Session, limit: int = 5):
        """קבלת הלידים האחרונים"""
        try:
            leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()
            logger.debug(f"📥 Retrieved {len(leads)} recent leads")
            return leads
        except Exception as e:
            logger.error(f"❌ Error getting recent leads: {e}")
            return []
    
    @staticmethod
    def get_stats(db: Session):
        """קבלת סטטיסטיקות"""
        try:
            total = db.query(Lead).count()
            
            # לידים מהיום
            today_start = datetime.combine(date.today(), datetime.min.time())
            today = db.query(Lead).filter(Lead.created_at >= today_start).count()
            
            # לידים במצב חדש
            pending = db.query(Lead).filter(Lead.status == 'new').count()
            
            stats = {
                "total": total,
                "today": today,
                "pending": pending
            }
            
            logger.debug(f"📊 Stats retrieved: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting stats: {e}")
            return {"total": 0, "today": 0, "pending": 0}
    
    @staticmethod
    def export_to_csv(db: Session, filename: str):
        """ייצוא לידים ל-CSV"""
        try:
            leads = db.query(Lead).order_by(Lead.created_at.desc()).all()
            
            # וידוא שהתיקייה קיימת
            os.makedirs(os.path.dirname(os.path.abspath(filename)) or '.', exist_ok=True)
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                
                # כותרת עם תווים בעברית
                writer.writerow([
                    "ID", "שם", "טלפון", "אימייל", "מקור", 
                    "סטטוס", "תאריך יצירה", "הערות"
                ])
                
                for lead in leads:
                    writer.writerow([
                        lead.id,
                        lead.name or '',
                        lead.phone or '',
                        lead.email or '',
                        lead.source or '',
                        lead.status or '',
                        lead.created_at.strftime("%Y-%m-%d %H:%M") if lead.created_at else '',
                        lead.notes or ''
                    ])
            
            logger.info(f"✅ CSV export completed: {filename} ({len(leads)} leads)")
            return filename
            
        except Exception as e:
            logger.error(f"❌ CSV export failed: {e}")
            raise
    
    @staticmethod
    def get_lead_by_id(db: Session, lead_id: int):
        """קבלת ליד לפי ID"""
        try:
            return db.query(Lead).filter(Lead.id == lead_id).first()
        except Exception as e:
            logger.error(f"❌ Error getting lead {lead_id}: {e}")
            return None
    
    @staticmethod
    def update_lead_status(db: Session, lead_id: int, status: str):
        """עדכון סטטוס ליד"""
        try:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if lead:
                lead.status = status
                db.commit()
                logger.info(f"✅ Updated lead {lead_id} status to {status}")
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error updating lead status: {e}")
            return False
