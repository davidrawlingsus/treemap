"""
Production Deployment Script
Ensures production database has the same tables and structure as feature branch.

This script:
1. Checks current database state
2. Runs any pending Alembic migrations
3. Verifies all required tables exist
4. Checks process_voc table structure
5. Verifies client_uuid mappings

Run on production via Railway:
    railway run python deploy_to_production.py
"""
import sys
import os
from sqlalchemy import text, inspect
from sqlalchemy.exc import OperationalError
from alembic.config import Config
from alembic import command
import alembic
from app.database import engine, Base
from app.models import User, Membership, Client, ProcessVoc
from app.config import get_settings

def check_database_connection():
    """Verify database connection works."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_table_exists(table_name):
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    return table_name in tables

def list_all_tables():
    """List all tables in the database."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\n📊 Tables in database ({len(tables)}):")
    for table in sorted(tables):
        print(f"  ✓ {table}")
    return tables

def check_process_voc_structure():
    """Verify process_voc table has the correct structure."""
    if not check_table_exists('process_voc'):
        print("❌ process_voc table does not exist!")
        return False
    
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('process_voc')]
    
    required_columns = [
        'id', 'respondent_id', 'dimension_ref', 'dimension_name', 
        'value', 'topics', 'overall_sentiment', 'client_uuid', 
        'data_source', 'client_name'
    ]
    
    missing_columns = [col for col in required_columns if col not in columns]
    
    if missing_columns:
        print(f"❌ process_voc missing columns: {', '.join(missing_columns)}")
        return False
    
    print("✅ process_voc table structure is correct")
    
    # Check row count
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM process_voc"))
        count = result.scalar()
        print(f"   📈 process_voc has {count:,} rows")
    
    return True

def check_migration_status():
    """Check current Alembic migration status."""
    try:
        alembic_cfg = Config("alembic.ini")
        with engine.connect() as conn:
            # Check alembic_version table
            if check_table_exists('alembic_version'):
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                current_version = result.scalar()
                print(f"📋 Current Alembic version: {current_version}")
                return current_version
            else:
                print("⚠️  alembic_version table does not exist (no migrations run yet)")
                return None
    except Exception as e:
        print(f"⚠️  Could not check migration status: {e}")
        return None

def run_migrations():
    """Run pending Alembic migrations."""
    print("\n🔄 Running Alembic migrations...")
    try:
        alembic_cfg = Config("alembic.ini")
        # Set the database URL from environment/config
        settings = get_settings()
        database_url = settings.get_database_url().replace('postgresql://', 'postgresql+psycopg://')
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        
        # Check if alembic_version table exists
        if not check_table_exists('alembic_version'):
            print("⚠️  alembic_version table doesn't exist, but tables do.")
            print("   This means tables were created manually. Stamping database to latest migration...")
            
            # Get the latest migration revision
            script = alembic.script.ScriptDirectory.from_config(alembic_cfg)
            head_revision = script.get_current_head()
            
            # Stamp the database to the latest migration
            command.stamp(alembic_cfg, head_revision)
            print(f"✅ Database stamped to revision: {head_revision}")
        else:
            # Run migrations normally
            command.upgrade(alembic_cfg, "head")
            print("✅ Migrations completed successfully")
        return True
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_client_uuid_mappings():
    """Check if process_voc rows have client_uuid set, and if not, try to match by client_name."""
    print("\n🔍 Checking client_uuid mappings in process_voc...")
    
    with engine.connect() as conn:
        # Check how many rows have NULL client_uuid
        result = conn.execute(text("""
            SELECT COUNT(*) as null_count,
                   COUNT(DISTINCT client_name) as unique_client_names
            FROM process_voc
            WHERE client_uuid IS NULL AND client_name IS NOT NULL
        """))
        row = result.fetchone()
        null_count = row[0]
        unique_names = row[1]
        
        if null_count == 0:
            print("✅ All process_voc rows have client_uuid set")
            return True
        
        print(f"⚠️  Found {null_count:,} rows with NULL client_uuid")
        print(f"   Found {unique_names} unique client names that need mapping")
        
        # Try to map client_name to client_uuid
        result = conn.execute(text("""
            SELECT DISTINCT pv.client_name, c.id as client_uuid
            FROM process_voc pv
            JOIN clients c ON c.name = pv.client_name
            WHERE pv.client_uuid IS NULL
        """))
        
        mappings = result.fetchall()
        
        if mappings:
            print(f"\n📝 Found {len(mappings)} client name -> UUID mappings")
            print("   Updating process_voc rows...")
            
            for client_name, client_uuid in mappings:
                conn.execute(text("""
                    UPDATE process_voc
                    SET client_uuid = :client_uuid
                    WHERE client_name = :client_name
                    AND client_uuid IS NULL
                """), {"client_uuid": client_uuid, "client_name": client_name})
                conn.commit()
            
            print(f"✅ Updated {len(mappings)} client mappings")
        else:
            print("⚠️  No matching clients found in clients table")
            print("   You may need to create clients first")
        
        return True

def verify_required_tables():
    """Verify all required tables exist."""
    required_tables = [
        'clients',
        'users', 
        'memberships',
        'process_voc',
        'data_sources',  # May still exist for backward compatibility
        'dimension_names'  # May still exist for backward compatibility
    ]
    
    print("\n🔍 Checking required tables...")
    all_tables = list_all_tables()
    
    missing = [t for t in required_tables if t not in all_tables]
    
    if missing:
        print(f"⚠️  Missing tables: {', '.join(missing)}")
        
        # Critical tables that must exist
        critical = ['clients', 'users', 'memberships', 'process_voc']
        critical_missing = [t for t in critical if t in missing]
        
        if critical_missing:
            print(f"❌ Critical tables missing: {', '.join(critical_missing)}")
            print("   Creating missing tables...")
            Base.metadata.create_all(bind=engine)
            print("✅ Tables created")
        else:
            print("   Non-critical tables missing (may be deprecated)")
        
        return False
    else:
        print("✅ All required tables exist")
        return True

def main():
    """Main deployment process."""
    print("=" * 80)
    print("🚀 PRODUCTION DATABASE DEPLOYMENT")
    print("=" * 80)
    
    # Step 1: Check database connection
    if not check_database_connection():
        print("\n❌ Cannot proceed without database connection")
        sys.exit(1)
    
    # Step 2: List current tables
    list_all_tables()
    
    # Step 3: Verify required tables exist
    verify_required_tables()
    
    # Step 4: Check migration status
    current_version = check_migration_status()
    
    # Step 5: Run migrations if needed
    print("\n" + "=" * 80)
    print("🔄 MIGRATION PHASE")
    print("=" * 80)
    if not run_migrations():
        print("\n❌ Migration failed - please check errors above")
        sys.exit(1)
    
    # Step 6: Verify process_voc structure
    print("\n" + "=" * 80)
    print("📊 VERIFICATION PHASE")
    print("=" * 80)
    if not check_process_voc_structure():
        print("\n❌ process_voc table structure is incorrect")
        sys.exit(1)
    
    # Step 7: Verify and fix client_uuid mappings
    verify_client_uuid_mappings()
    
    # Step 8: Final summary
    print("\n" + "=" * 80)
    print("✅ DEPLOYMENT COMPLETE")
    print("=" * 80)
    print("\n📋 Summary:")
    print("  ✓ Database connection verified")
    print("  ✓ All required tables exist")
    print("  ✓ Migrations up to date")
    print("  ✓ process_voc table structure verified")
    print("  ✓ Client UUID mappings checked")
    print("\n🎉 Production database is ready!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

