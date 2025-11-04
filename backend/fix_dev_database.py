"""
Script to fix dev database by creating missing tables.
Run this on Railway dev server or locally with dev DATABASE_URL.

Usage:
    # On Railway dev server
    railway run python fix_dev_database.py
    
    # Or locally with dev DATABASE_URL
    export DATABASE_URL="your-dev-database-url"
    python fix_dev_database.py
"""
import sys
import os
from sqlalchemy import text, inspect
from app.database import engine, Base
from app.models import User, Membership, Client, DataSource, DimensionName

def check_tables():
    """Check which tables exist in the database."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    print("📊 Current tables in database:")
    for table in sorted(existing_tables):
        print(f"  ✓ {table}")
    
    return existing_tables

def create_missing_tables():
    """Create all tables if they don't exist."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    required_tables = {
        'users': User,
        'memberships': Membership,
        'clients': Client,
        'data_sources': DataSource,
        'dimension_names': DimensionName
    }
    
    missing_tables = [t for t in required_tables.keys() if t not in existing_tables]
    
    if missing_tables:
        print(f"\n⚠️  Missing tables: {', '.join(missing_tables)}")
        print("Creating missing tables...")
        
        # Create all tables defined in models
        Base.metadata.create_all(bind=engine)
        
        print("✅ Tables created!")
        
        # Verify
        inspector = inspect(engine)
        new_tables = inspector.get_table_names()
        print(f"\n📊 Tables now in database ({len(new_tables)}):")
        for table in sorted(new_tables):
            print(f"  ✓ {table}")
    else:
        print("\n✅ All required tables exist!")

def verify_users_table():
    """Verify users table structure matches expected schema."""
    inspector = inspect(engine)
    
    if 'users' not in inspector.get_table_names():
        print("❌ users table does not exist")
        return False
    
    columns = {col['name']: col for col in inspector.get_columns('users')}
    required_columns = ['id', 'email', 'name', 'is_founder', 'is_active', 'created_at', 'updated_at']
    
    missing_columns = [col for col in required_columns if col not in columns]
    if missing_columns:
        print(f"⚠️  users table missing columns: {', '.join(missing_columns)}")
        return False
    
    print("✅ users table structure is correct")
    return True

def main():
    """Main function."""
    print("🔍 Checking database tables...")
    print(f"   Database: {os.getenv('DATABASE_URL', 'unknown')[:50]}...\n")
    
    try:
        existing_tables = check_tables()
        
        # Check if users table exists and has correct structure
        if 'users' in existing_tables:
            verify_users_table()
        else:
            print("\n❌ users table is missing")
            create_missing_tables()
        
        # Check users data and seed if needed
        if 'users' in existing_tables or 'users' in inspect(engine).get_table_names():
            print("\n👤 Checking users in database...")
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                users = db.query(User).all()
                print(f"   Found {len(users)} users:")
                for u in users:
                    print(f"     - {u.email} (active: {u.is_active}, founder: {u.is_founder})")
                
                # Seed default user if none exist
                if len(users) == 0:
                    print("\n🌱 No users found. Seeding default founder user...")
                    default_email = os.getenv("DEFAULT_USER_EMAIL", "david@rawlings.us")
                    default_name = os.getenv("DEFAULT_USER_NAME", "David Rawlings")
                    
                    default_user = User(
                        email=default_email,
                        name=default_name,
                        is_founder=True,
                        is_active=True
                    )
                    db.add(default_user)
                    db.commit()
                    db.refresh(default_user)
                    print(f"   ✅ Created default user: {default_user.email} (founder: {default_user.is_founder})")
                    
            except Exception as e:
                print(f"   ⚠️  Error querying/creating users: {e}")
                import traceback
                traceback.print_exc()
                db.rollback()
            finally:
                db.close()
        
        print("\n✅ Database check complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

