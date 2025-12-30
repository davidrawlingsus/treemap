from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()


def normalize_database_url(database_url: str) -> str:
    """
    Normalize database URL for psycopg3 compatibility.
    
    Replaces 'postgresql://' with 'postgresql+psycopg://' if psycopg driver
    is not already specified.
    
    Args:
        database_url: Original database URL
        
    Returns:
        Normalized database URL
    """
    # Replace 'postgresql://' with 'postgresql+psycopg://' to use psycopg3
    if database_url.startswith('postgresql://') and '+psycopg' not in database_url:
        return database_url.replace('postgresql://', 'postgresql+psycopg://')
    return database_url


# Get database URL (prefers public URL for local dev)
database_url = settings.get_database_url()

# Normalize database URL for psycopg3 compatibility
database_url = normalize_database_url(database_url)

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

