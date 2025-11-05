"""
Setup script to create database tables and test the connection.
Run this after updating .env with your Railway public database URL.
"""
import sys
from sqlalchemy import text
from app.database import engine, Base
from app.models import DataSource
from app.config import get_settings

def main():
    try:
        settings = get_settings()
        print(f"🔌 Connecting to database...")
        print(f"   URL: {settings.database_url[:30]}...")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"✅ Connected to PostgreSQL")
            print(f"   Version: {version[:50]}...")
        
        # Create tables
        print(f"\n📦 Creating tables...")
        Base.metadata.create_all(bind=engine)
        print(f"✅ Tables created successfully!")
        
        # List tables
        print(f"\n📋 Tables in database:")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            for row in result:
                print(f"   - {row[0]}")
        
        print(f"\n🎉 Database setup complete!")
        print(f"\nNext steps:")
        print(f"1. Run the server: ./start.sh")
        print(f"2. Upload data using: python upload_all_data.py")
        print(f"3. Open index.html in your browser")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

