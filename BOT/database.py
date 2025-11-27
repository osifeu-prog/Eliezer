from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Lead(Base):
    """מודל ליד"""
    __tablename__ = 'leads'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100))
    source = Column(String(50), default='website')
    status = Column(String(20), default='new')  # new, contacted, converted, lost
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(Base):
    """מודל משתמש (צוות המשרד)"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    """מחלקה לניהול מסד הנתונים"""
    
    def __init__(self, database_url=None):
        if database_url is None:
            database_url = os.getenv('DATABASE_URL', 'sqlite:///crm_bot.db')
        
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # יצירת הטבלאות
        Base.metadata.create_all(bind=self.engine)
        print("✅ Database tables created successfully")
    
    def get_session(self):
        """קבלת session למסד הנתונים"""
        return self.SessionLocal()
    
    def add_lead(self, name, phone, email=None, source='website', notes=None):
        """הוספת ליד חדש"""
        session = self.get_session()
        try:
            lead = Lead(
                name=name,
                phone=phone,
                email=email,
                source=source,
                notes=notes
            )
            session.add(lead)
            session.commit()
            session.refresh(lead)
            return lead
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_leads(self, status=None, limit=100):
        """קבלת לידים עם אפשרות לסינון לפי סטטוס"""
        session = self.get_session()
        try:
            query = session.query(Lead)
            if status:
                query = query.filter(Lead.status == status)
            
            return query.order_by(Lead.created_at.desc()).limit(limit).all()
        finally:
            session.close()
    
    def update_lead_status(self, lead_id, status):
        """עדכון סטטוס ליד"""
        session = self.get_session()
        try:
            lead = session.query(Lead).filter(Lead.id == lead_id).first()
            if lead:
                lead.status = status
                lead.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def add_user(self, telegram_id, first_name, username=None, last_name=None):
        """הוספת משתמש חדש"""
        session = self.get_session()
        try:
            # בדיקה אם המשתמש כבר קיים
            existing_user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if existing_user:
                return existing_user
            
            user = User(
                telegram_id=telegram_id,
                first_name=first_name,
                username=username,
                last_name=last_name
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_user_by_telegram_id(self, telegram_id):
        """קבלת משתמש לפי telegram ID"""
        session = self.get_session()
        try:
            return session.query(User).filter(User.telegram_id == telegram_id).first()
        finally:
            session.close()
    
    def get_stats(self):
        """קבלת סטטיסטיקות"""
        session = self.get_session()
        try:
            total_leads = session.query(Lead).count()
            new_leads = session.query(Lead).filter(Lead.status == 'new').count()
            contacted_leads = session.query(Lead).filter(Lead.status == 'contacted').count()
            completed_leads = session.query(Lead).filter(Lead.status == 'converted').count()
            
            # לידים מהיום
            today = datetime.utcnow().date()
            today_leads = session.query(Lead).filter(
                Lead.created_at >= datetime(today.year, today.month, today.day)
            ).count()
            
            # אחוז המרה
            conversion_rate = (completed_leads / total_leads * 100) if total_leads > 0 else 0
            
            return {
                'total_leads': total_leads,
                'new_leads': new_leads,
                'contacted_leads': contacted_leads,
                'completed_leads': completed_leads,
                'today_leads': today_leads,
                'conversion_rate': round(conversion_rate, 2)
            }
        finally:
            session.close()
