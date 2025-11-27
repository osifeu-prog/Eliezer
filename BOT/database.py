from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging
from config import Config

logger = logging.getLogger(__name__)
Base = declarative_base()

class Lead(Base):
    __tablename__ = 'leads'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=True)
    source = Column(String(50), default="website")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="new")  # new, contacted, closed

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'source': self.source,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'status': self.status
        }

class DatabaseManager:
    """מנהל מסד נתונים עם טיפול בשגיאות"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._setup_database()
    
    def _setup_database(self):
        """הגדרת חיבור למסד הנתונים"""
        try:
            # הגדרת חיבור עם פרמטרים מתאימים
            connect_args = {}
            if "sqlite" in Config.DATABASE_URL:
                connect_args = {"check_same_thread": False}
            
            self.engine = create_engine(
                Config.DATABASE_URL,
                connect_args=connect_args,
                pool_pre_ping=True,  # בדיקת חיבור לפני שימוש
                echo=False  # הגדר ל-True לדיבאג
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False, 
                autoflush=False, 
                bind=self.engine
            )
            
            logger.info(f"✅ Database engine created: {Config.DATABASE_URL.split('://')[0]}")
            
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
            raise
    
    def init_db(self):
        """אתחול הטבלאות במסד הנתונים"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Database tables created successfully")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    def get_session(self):
        """קבלת session עם טיפול בשגיאות"""
        try:
            session = self.SessionLocal()
            return session
        except Exception as e:
            logger.error(f"❌ Failed to create database session: {e}")
            raise
    
    def close_session(self, session):
        """סגירת session"""
        try:
            if session:
                session.close()
        except Exception as e:
            logger.error(f"❌ Error closing session: {e}")

# יצירת instance גלובלי
db_manager = DatabaseManager()

# פונקציות compatibility
def init_db():
    return db_manager.init_db()

def get_db():
    return db_manager.get_session()

SessionLocal = db_manager.SessionLocal
