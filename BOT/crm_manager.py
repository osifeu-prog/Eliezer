from sqlalchemy.orm import Session
from database import Lead
from datetime import datetime
import csv
import os

class CRMManager:
    @staticmethod
    def add_lead(db: Session, data: dict):
        new_lead = Lead(
            name=data.get('name'),
            phone=data.get('phone'),
            email=data.get('email'),
            source=data.get('source', 'website'),
            notes=data.get('notes')
        )
        db.add(new_lead)
        db.commit()
        db.refresh(new_lead)
        return new_lead

    @staticmethod
    def get_recent_leads(db: Session, limit: int = 5):
        return db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_stats(db: Session):
        total = db.query(Lead).count()
        today = db.query(Lead).filter(Lead.created_at >= datetime.now().date()).count()
        new_status = db.query(Lead).filter(Lead.status == 'new').count()
        return {
            "total": total,
            "today": today,
            "pending": new_status
        }

    @staticmethod
    def export_to_csv(db: Session, filename: str):
        leads = db.query(Lead).all()
        
        # יצירת קובץ CSV
        with open(filename, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow(["ID", "שם", "טלפון", "אימייל", "מקור", "סטטוס", "תאריך", "הערות"])
            
            for lead in leads:
                writer.writerow([
                    lead.id, lead.name, lead.phone, lead.email, 
                    lead.source, lead.status, 
                    lead.created_at.strftime("%Y-%m-%d %H:%M"), lead.notes
                ])
        return filename
