from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import get_settings
import os

settings = get_settings()

# Get database URL (prefers public URL for local dev)
database_url = settings.get_database_url()

# DEBUG: Log what we're actually using
print(f"🔍 DATABASE_URL from env: {os.getenv('DATABASE_URL', 'NOT SET')[:50]}...")
print(f"🔍 DATABASE_PUBLIC_URL from env: {os.getenv('DATABASE_PUBLIC_URL', 'NOT SET')[:50]}...")
print(f"🔍 Final database_url: {database_url[:50]}...")
print(f"🔍 Database type: {'PostgreSQL' if 'postgresql' in database_url else 'SQLite' if 'sqlite' in database_url else 'Unknown'}")

# Create synchronous engine for now (simpler for Phase 1)
# Replace 'postgresql://' with 'postgresql+psycopg://' to use psycopg3
if database_url.startswith('postgresql://') and '+psycopg' not in database_url:
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg://')

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

