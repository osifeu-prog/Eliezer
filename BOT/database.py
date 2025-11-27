from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from config import Config

Base = declarative_base()

class Lead(Base):
    __tablename__ = 'leads'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    phone = Column(String)
    email = Column(String, nullable=True)
    source = Column(String, default="website") # מאיפה הגיע הליד
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    status = Column(String, default="new") # new, contacted, closed

# יצירת חיבור למסד הנתונים
engine = create_engine(Config.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in Config.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
