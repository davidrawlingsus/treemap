"""
Inspect process_voc table using DATABASE_URL from Railway environment.
This script can be run locally if DATABASE_URL is set.
"""
import os
import sys
from sqlalchemy import create_engine, text

def main():
    # Try to get DATABASE_URL from environment
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        print("\nTo use this script:")
        print("1. Run via Railway: railway run -s <service> python inspect_db.py")
        print("2. Or set DATABASE_URL locally: export DATABASE_URL=...")
        sys.exit(1)
    
    print(f"🔌 Using DATABASE_URL from environment")
    print(f"   Database: {database_url.split('@')[1] if '@' in database_url else 'unknown'}\n")
    
    # Convert to psycopg format if needed
    if database_url.startswith('postgresql://') and '+psycopg' not in database_url:
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg://')
    
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Check if process_voc exists
            print("🔍 Checking for process_voc table...")
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'process_voc'
                );
            """))
            exists = result.scalar()
            
            if not exists:
                print("❌ Table 'process_voc' does not exist")
                # List all tables
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                """))
                tables = [row[0] for row in result]
                print(f"\n📋 Available tables: {', '.join(tables)}")
                return
            
            print("✅ Table 'process_voc' exists\n")
            
            # Get table structure
            print("📊 Table Structure:")
            print("=" * 100)
            result = conn.execute(text("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = 'process_voc'
                ORDER BY ordinal_position;
            """))
            
            print(f"{'Column Name':<35} {'Type':<30} {'Nullable':<10} {'Default'}")
            print("-" * 100)
            columns = []
            for row in result:
                col_name = row[0]
                data_type = row[1]
                max_length = f"({row[2]})" if row[2] else ""
                nullable = row[3]
                default = str(row[4])[:20] if row[4] else ""
                type_str = f"{data_type}{max_length}"
                print(f"{col_name:<35} {type_str:<30} {nullable:<10} {default}")
                columns.append(col_name)
            
            # Get row count
            print("\n📈 Statistics:")
            result = conn.execute(text("SELECT COUNT(*) FROM process_voc"))
            count = result.scalar()
            print(f"   Total rows: {count:,}")
            
            # Get sample rows
            print("\n📝 Sample Data (first 2 rows):")
            print("=" * 100)
            result = conn.execute(text("SELECT * FROM process_voc LIMIT 2"))
            rows = result.fetchall()
            col_names = result.keys()
            
            if rows:
                print(f"Columns ({len(col_names)}): {', '.join(col_names)}\n")
                for i, row in enumerate(rows, 1):
                    print(f"\n--- Row {i} ---")
                    for col, val in zip(col_names, row):
                        if val is None:
                            val_str = "NULL"
                        else:
                            val_str = str(val)
                            if len(val_str) > 150:
                                val_str = val_str[:150] + "..."
                        print(f"  {col}: {val_str}")
            else:
                print("   (No data found)")
            
            # Check for foreign keys
            print("\n🔗 Foreign Keys:")
            print("=" * 100)
            result = conn.execute(text("""
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = 'process_voc';
            """))
            fks = result.fetchall()
            if fks:
                for fk in fks:
                    print(f"  {fk[0]} -> {fk[1]}.{fk[2]}")
            else:
                print("  (No foreign keys found)")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()








