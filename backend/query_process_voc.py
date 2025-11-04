"""
Simpler script to query process_voc table.
Run: railway run python query_process_voc.py
Or: railway connect postgres and run SQL manually
"""
import os
from sqlalchemy import create_engine, text

# Get DATABASE_URL from environment (Railway injects this)
database_url = os.getenv('DATABASE_URL')
if not database_url:
    print("❌ DATABASE_URL not found in environment")
    print("Make sure you're running via: railway run python query_process_voc.py")
    exit(1)

# Convert to psycopg format
database_url = database_url.replace('postgresql://', 'postgresql+psycopg://')

print(f"🔌 Connecting to database...")
engine = create_engine(database_url)

try:
    with engine.connect() as conn:
        # Get table structure
        print("\n📊 process_voc Table Structure:")
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
        for row in result:
            col_name = row[0]
            data_type = row[1]
            max_length = f"({row[2]})" if row[2] else ""
            nullable = row[3]
            default = str(row[4])[:20] if row[4] else ""
            type_str = f"{data_type}{max_length}"
            print(f"{col_name:<35} {type_str:<30} {nullable:<10} {default}")
        
        # Get row count
        result = conn.execute(text("SELECT COUNT(*) FROM process_voc"))
        count = result.scalar()
        print(f"\n📈 Total rows: {count:,}")
        
        # Get sample rows
        print("\n📝 Sample Data (first 2 rows):")
        print("=" * 100)
        result = conn.execute(text("SELECT * FROM process_voc LIMIT 2"))
        rows = result.fetchall()
        columns = result.keys()
        
        if rows:
            print(f"Columns: {', '.join(columns)}\n")
            for i, row in enumerate(rows, 1):
                print(f"\n--- Row {i} ---")
                for col, val in zip(columns, row):
                    val_str = str(val)
                    if len(val_str) > 150:
                        val_str = val_str[:150] + "..."
                    print(f"  {col}: {val_str}")
        
        # Check for relationships/foreign keys
        print("\n🔗 Foreign Keys:")
        print("=" * 100)
        result = conn.execute(text("""
            SELECT
                tc.constraint_name,
                tc.table_name,
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
                print(f"  {fk[2]} -> {fk[3]}.{fk[4]}")
        else:
            print("  (No foreign keys found)")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)



