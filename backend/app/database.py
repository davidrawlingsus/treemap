from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

# Create synchronous engine for now (simpler for Phase 1)
# Replace 'postgresql://' with 'postgresql+psycopg://' to use psycopg3
database_url = settings.database_url.replace('postgresql://', 'postgresql+psycopg://')
engine = create_engine(database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

