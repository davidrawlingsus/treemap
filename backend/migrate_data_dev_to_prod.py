"""
Migrate data from Railway dev environment to production environment.

This script:
1. Connects to dev database (source)
2. Connects to production database (target)
3. Copies data in correct order:
   - Users
   - Clients
   - Memberships
   - process_voc
4. Handles conflicts and duplicates

Usage:
    # Set environment variables for both databases
    export DEV_DATABASE_URL="postgresql://..."
    export PROD_DATABASE_URL="postgresql://..."
    python migrate_data_dev_to_prod.py
"""
import sys
import os
import argparse
import json
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session, sessionmaker
from app.models import User, Client, Membership, ProcessVoc
from app.config import get_settings

def get_database_url(env_var_name, default_env_var='DATABASE_URL'):
    """Get database URL from environment variable."""
    # Try the specific env var first
    db_url = os.getenv(env_var_name)
    if db_url:
        return db_url
    
    # Fall back to default if env_var_name is DATABASE_URL
    if env_var_name == default_env_var:
        settings = get_settings()
        return settings.get_database_url()
    
    return None

def create_engine_from_url(url):
    """Create SQLAlchemy engine from URL."""
    if url.startswith('postgresql://') and '+psycopg' not in url:
        url = url.replace('postgresql://', 'postgresql+psycopg://')
    # Configure engine to handle stale connections
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)

def copy_table_data(source_session, target_session, model_class, table_name, skip_duplicates=True):
    """Copy data from source to target database using raw SQL for better performance."""
    print(f"\n📋 Copying {table_name}...")
    
    # Get primary key column for duplicate checking
    pk_column = 'id'  # Default
    
    # Get metadata first (count, columns)
    temp_conn = source_session.connection()
    try:
        # Get count from source
        result = temp_conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        total_count = result.scalar()
        print(f"   Found {total_count:,} records in source")
        
        if total_count == 0:
            print(f"   ⏭️  No records to copy")
            return 0
        
        # Get column names and types from source
        result = temp_conn.execute(text(f"""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            ORDER BY ordinal_position
        """))
        source_column_info = [(row[0], row[1], row[2]) for row in result]
        
        # Get column names from target
        target_check_conn = target_session.connection()
        try:
            result = target_check_conn.execute(text(f"""
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns 
                WHERE table_name = '{table_name}' 
                ORDER BY ordinal_position
            """))
            target_column_names = {row[0] for row in result}
        finally:
            target_check_conn.close()
        
        # Only use columns that exist in both databases
        column_info = [col for col in source_column_info if col[0] in target_column_names]
        columns = [col[0] for col in column_info]
        jsonb_columns = {col[0] for col in column_info if col[2] == 'jsonb'}
        
        if not columns:
            print(f"   ⚠️  No matching columns found between source and target")
            return 0
        
        column_names = ', '.join(columns)
        # Create placeholders with CAST for JSONB columns
        placeholders = ', '.join([f'CAST(:{col} AS jsonb)' if col in jsonb_columns else f':{col}' for col in columns])
    finally:
        temp_conn.close()
    
    # Copy in batches - use fresh connections for each batch
    batch_size = 500
    copied = 0
    skipped = 0
    offset = 0
    
    while offset < total_count:
        # Get fresh connections for each batch
        with source_session.connection() as source_conn, target_session.connection() as target_conn:
            # Fetch batch
            result = source_conn.execute(text(f"""
                SELECT {column_names} FROM {table_name}
                ORDER BY {pk_column}
                LIMIT :limit OFFSET :offset
            """), {"limit": batch_size, "offset": offset})
            
            rows = result.fetchall()
            
            if not rows:
                break
            
            batch_copied = 0
            batch_skipped = 0
            
            for row in rows:
                try:
                    # Build values dict, converting dict/list to JSON strings for JSONB columns
                    values = {}
                    for i, col in enumerate(columns):
                        val = row[i]
                        # Convert dict/list to JSON string for JSONB columns
                        if col in jsonb_columns and isinstance(val, (dict, list)):
                            values[col] = json.dumps(val)
                        else:
                            values[col] = val
                    
                    # Check for duplicate
                    if skip_duplicates:
                        check_result = target_conn.execute(text(f"""
                            SELECT {pk_column} FROM {table_name} 
                            WHERE {pk_column} = :pk_value
                        """), {"pk_value": values[pk_column]})
                        
                        if check_result.fetchone():
                            batch_skipped += 1
                            continue
                    
                    # Insert row
                    insert_sql = f"""
                        INSERT INTO {table_name} ({column_names})
                        VALUES ({placeholders})
                    """
                    
                    target_conn.execute(text(insert_sql), values)
                    batch_copied += 1
                    
                except Exception as e:
                    # If it's a duplicate constraint error, skip it
                    if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
                        batch_skipped += 1
                        continue
                    print(f"   ⚠️  Error copying record: {e}")
                    continue
            
            # Commit through connection
            try:
                target_conn.commit()
                copied += batch_copied
                skipped += batch_skipped
            except Exception as e:
                print(f"   ⚠️  Commit error: {e}")
                target_conn.rollback()
        
        # Commit session to ensure persistence
        try:
            target_session.commit()
        except Exception as e:
            target_session.rollback()
        
        offset += batch_size
        
        if offset % 1000 == 0 or offset >= total_count:
            print(f"   ... copied {copied:,} records, skipped {skipped:,} duplicates ({offset:,} processed)")
    
    print(f"   ✅ Copied {copied:,} records, skipped {skipped:,} duplicates")
    return copied

def copy_process_voc_data(source_session, target_session):
    """Copy process_voc data with special handling."""
    print(f"\n📋 Copying process_voc...")
    
    # Get count first
    temp_conn = source_session.connection()
    try:
        result = temp_conn.execute(text("SELECT COUNT(*) FROM process_voc"))
        total_count = result.scalar()
        print(f"   Found {total_count:,} rows in source")
        
        if total_count == 0:
            print(f"   ⏭️  No records to copy")
            return 0
        
        # Get column names and types from source
        result = temp_conn.execute(text("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns 
            WHERE table_name = 'process_voc' 
            ORDER BY ordinal_position
        """))
        source_column_info = [(row[0], row[1], row[2]) for row in result]
        
        # Get column names from target
        target_check_conn = target_session.connection()
        try:
            result = target_check_conn.execute(text("""
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns 
                WHERE table_name = 'process_voc' 
                ORDER BY ordinal_position
            """))
            target_column_names = {row[0] for row in result}
        finally:
            target_check_conn.close()
        
        # Only use columns that exist in both databases
        column_info = [col for col in source_column_info if col[0] in target_column_names]
        columns = [col[0] for col in column_info]
        jsonb_columns = {col[0] for col in column_info if col[2] == 'jsonb'}
        
        if not columns:
            print(f"   ⚠️  No matching columns found between source and target")
            return 0
        
        column_names = ', '.join(columns)
        # Create placeholders with CAST for JSONB columns
        placeholders = ', '.join([f'CAST(:{col} AS jsonb)' if col in jsonb_columns else f':{col}' for col in columns])
    finally:
        temp_conn.close()
    
    # Copy in batches - use fresh connections for each batch
    batch_size = 500  # Smaller batches to avoid connection timeouts
    copied = 0
    offset = 0
    
    while offset < total_count:
        # Get fresh connections for each batch
        with source_session.connection() as source_conn, target_session.connection() as target_conn:
            # Fetch batch from source
            result = source_conn.execute(text(f"""
                SELECT {column_names} FROM process_voc
                ORDER BY id
                LIMIT :limit OFFSET :offset
            """), {"limit": batch_size, "offset": offset})
            
            rows = result.fetchall()
            
            if not rows:
                break
            
            # Build batch insert
            batch_copied = 0
            for row in rows:
                try:
                    # Build values dict, converting dict/list to JSON strings for JSONB columns
                    values = {}
                    for i, col in enumerate(columns):
                        val = row[i]
                        # Convert dict/list to JSON string for JSONB columns (like topics)
                        if col in jsonb_columns and isinstance(val, (dict, list)):
                            values[col] = json.dumps(val)
                        else:
                            values[col] = val
                    
                    # Check for duplicate by id first, then by respondent_id + dimension_ref
                    check_result = target_conn.execute(text("""
                        SELECT id FROM process_voc 
                        WHERE id = :id
                    """), {
                        "id": values.get('id')
                    })
                    
                    if check_result.fetchone():
                        continue  # Skip duplicate by id
                    
                    # Also check by respondent_id + dimension_ref (in case ids differ)
                    check_result2 = target_conn.execute(text("""
                        SELECT id FROM process_voc 
                        WHERE respondent_id = :respondent_id 
                        AND dimension_ref = :dimension_ref
                        LIMIT 1
                    """), {
                        "respondent_id": values['respondent_id'],
                        "dimension_ref": values['dimension_ref']
                    })
                    
                    if check_result2.fetchone():
                        continue  # Skip duplicate by respondent_id + dimension_ref
                    
                    # Insert row
                    insert_sql = f"""
                        INSERT INTO process_voc ({column_names})
                        VALUES ({placeholders})
                    """
                    
                    target_conn.execute(text(insert_sql), values)
                    batch_copied += 1
                    
                except Exception as e:
                    # If it's a duplicate constraint error, skip it
                    if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
                        continue
                    print(f"   ⚠️  Error copying row: {e}")
                    continue
            
            # Commit through connection (not session)
            try:
                target_conn.commit()
                copied += batch_copied
            except Exception as e:
                print(f"   ⚠️  Commit error: {e}")
                target_conn.rollback()
        
        # Commit session to ensure everything is persisted
        try:
            target_session.commit()
        except Exception as e:
            target_session.rollback()
        
        offset += batch_size
        
        if offset % 5000 == 0 or offset >= total_count:
            print(f"   ... copied {copied:,} / {total_count:,} rows ({offset:,} processed)")
    
    print(f"   ✅ Copied {copied:,} process_voc rows")
    return copied

def main():
    """Main migration process."""
    parser = argparse.ArgumentParser(description='Migrate data from dev to production database')
    parser.add_argument('--dev-url', help='Dev database URL (overrides DEV_DATABASE_URL env var)')
    parser.add_argument('--prod-url', help='Production database URL (overrides PROD_DATABASE_URL env var)')
    args = parser.parse_args()
    
    print("=" * 80)
    print("🚀 MIGRATE DATA: DEV → PRODUCTION")
    print("=" * 80)
    
    # Get database URLs (command-line args take precedence)
    dev_url = args.dev_url or get_database_url('DEV_DATABASE_URL')
    prod_url = args.prod_url or get_database_url('PROD_DATABASE_URL')
    
    if not dev_url:
        print("❌ DEV_DATABASE_URL not set")
        print("   Set it with: export DEV_DATABASE_URL='postgresql://...'")
        print("   Or use: --dev-url 'postgresql://...'")
        print("   Or get it from Railway: railway variables --service <dev-service>")
        sys.exit(1)
    
    if not prod_url:
        print("❌ PROD_DATABASE_URL not set")
        print("   Set it with: export PROD_DATABASE_URL='postgresql://...'")
        print("   Or use: --prod-url 'postgresql://...'")
        print("   Or get it from Railway: railway variables --service <prod-service>")
        sys.exit(1)
    
    print(f"\n🔌 Connecting to databases...")
    print(f"   Dev: {dev_url[:50]}...")
    print(f"   Prod: {prod_url[:50]}...")
    
    # Create engines
    dev_engine = create_engine_from_url(dev_url)
    prod_engine = create_engine_from_url(prod_url)
    
    # Test connections
    try:
        with dev_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("   ✅ Dev database connected")
    except Exception as e:
        print(f"   ❌ Dev database connection failed: {e}")
        sys.exit(1)
    
    try:
        with prod_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("   ✅ Prod database connected")
    except Exception as e:
        print(f"   ❌ Prod database connection failed: {e}")
        sys.exit(1)
    
    # Create sessions
    DevSession = sessionmaker(bind=dev_engine)
    ProdSession = sessionmaker(bind=prod_engine)
    
    dev_session = DevSession()
    prod_session = ProdSession()
    
    try:
        print("\n" + "=" * 80)
        print("📦 COPYING DATA")
        print("=" * 80)
        
        # Step 1: Copy Users (must be first)
        copy_table_data(dev_session, prod_session, User, 'users')
        
        # Step 2: Copy Clients
        copy_table_data(dev_session, prod_session, Client, 'clients')
        
        # Step 3: Copy Memberships
        copy_table_data(dev_session, prod_session, Membership, 'memberships')
        
        # Step 4: Copy process_voc (largest table)
        copy_process_voc_data(dev_session, prod_session)
        
        print("\n" + "=" * 80)
        print("✅ MIGRATION COMPLETE")
        print("=" * 80)
        
        # Verify counts
        print("\n📊 Verification:")
        with prod_session.connection() as conn:
            for table in ['users', 'clients', 'memberships', 'process_voc']:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"   {table}: {count:,} rows")
        
    except Exception as e:
        print(f"\n❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        prod_session.rollback()
        sys.exit(1)
    finally:
        dev_session.close()
        prod_session.close()

if __name__ == "__main__":
    main()

