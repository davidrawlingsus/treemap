"""
Script to create missing tables (users, memberships) in the database.

Run this if the dev database is missing tables:
    python create_missing_tables.py
"""
import sys
from sqlalchemy import text, inspect
from app.database import engine, Base
from app.models import User, Membership, Client

def check_and_create_tables():
    """Check which tables exist and create missing ones."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    print("📊 Current tables in database:")
    for table in sorted(existing_tables):
        print(f"  ✓ {table}")
    
    required_tables = ['users', 'memberships', 'clients', 'data_sources', 'dimension_names']
    missing_tables = [t for t in required_tables if t not in existing_tables]
    
    if not missing_tables:
        print("\n✅ All required tables exist!")
        return
    
    print(f"\n⚠️  Missing tables: {', '.join(missing_tables)}")
    print("\nCreating missing tables...")
    
    # Create all tables defined in models
    Base.metadata.create_all(bind=engine)
    
    print("✅ Tables created!")
    
    # Verify
    inspector = inspect(engine)
    new_tables = inspector.get_table_names()
    print(f"\n📊 Tables now in database ({len(new_tables)}):")
    for table in sorted(new_tables):
        print(f"  ✓ {table}")

if __name__ == "__main__":
    try:
        check_and_create_tables()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



