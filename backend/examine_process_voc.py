"""
Script to examine the process_voc table structure and sample data.
Run this via Railway CLI: railway run python examine_process_voc.py
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect
from app.config import get_settings

def main():
    settings = get_settings()
    database_url = settings.database_url.replace('postgresql://', 'postgresql+psycopg://')
    
    print(f"🔌 Connecting to database...")
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Check if process_voc table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'process_voc'
                );
            """))
            table_exists = result.scalar()
            
            if not table_exists:
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
            print("=" * 80)
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
            
            print(f"{'Column Name':<30} {'Type':<25} {'Nullable':<10} {'Default':<15}")
            print("-" * 80)
            for row in result:
                col_name = row[0]
                data_type = row[1]
                max_length = f"({row[2]})" if row[2] else ""
                nullable = row[3]
                default = str(row[4])[:14] if row[4] else ""
                print(f"{col_name:<30} {data_type}{max_length:<25} {nullable:<10} {default:<15}")
            
            # Get row count
            print("\n📈 Row Count:")
            result = conn.execute(text("SELECT COUNT(*) FROM process_voc"))
            count = result.scalar()
            print(f"   Total rows: {count:,}")
            
            # Get sample data
            print("\n📝 Sample Data (first 3 rows):")
            print("=" * 80)
            result = conn.execute(text("SELECT * FROM process_voc LIMIT 3"))
            rows = result.fetchall()
            
            if rows:
                # Get column names
                columns = result.keys()
                print(f"Columns: {', '.join(columns)}\n")
                
                for i, row in enumerate(rows, 1):
                    print(f"Row {i}:")
                    for col, val in zip(columns, row):
                        # Truncate long values
                        val_str = str(val)
                        if len(val_str) > 100:
                            val_str = val_str[:100] + "..."
                        print(f"  {col}: {val_str}")
                    print()
            else:
                print("   (No data found)")
            
            # Get data distribution if there are topic/category columns
            print("\n📊 Data Distribution:")
            print("=" * 80)
            
            # Check for common columns
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns
                WHERE table_name = 'process_voc'
                AND column_name IN ('category', 'topic', 'topic_label', 'category_name', 'ref_key');
            """))
            relevant_cols = [row[0] for row in result]
            
            if relevant_cols:
                for col in relevant_cols:
                    result = conn.execute(text(f"""
                        SELECT {col}, COUNT(*) as count
                        FROM process_voc
                        WHERE {col} IS NOT NULL
                        GROUP BY {col}
                        ORDER BY count DESC
                        LIMIT 10;
                    """))
                    print(f"\n{col} distribution (top 10):")
                    for row in result:
                        print(f"  {row[0]}: {row[1]:,}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()



