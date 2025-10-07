from sqlalchemy import Column, String, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from database import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

class SystemStatus(Base):
    __tablename__ = 'system_status'
    key = Column(String, primary_key=True)
    value = Column(String)
    last_updated = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_status(key: str, default: str = "N/A") -> str:
    db = SessionLocal()
    try:
        status = db.query(SystemStatus).filter(SystemStatus.key == key).first()
        return status.value if status else default
    finally:
        db.close()

def set_status(key: str, value: str):
    db = SessionLocal()
    try:
        status = db.query(SystemStatus).filter(SystemStatus.key == key).first()
        if status:
            status.value = value
        else:
            status = SystemStatus(key=key, value=value)
            db.add(status)
        db.commit()
        logger.info(f"Set system status: {key} = {value}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to set system status for key {key}: {e}")
    finally:
        db.close()

def initialize_status_table():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("System status table checked/created.")
    except Exception as e:
        logger.error(f"Failed to create system_status table: {e}")