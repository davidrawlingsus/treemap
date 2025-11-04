"""
Script to remove rows from process_voc table for dimensions that have empty topics.
Specifically targets:
- 'results hoped for  (but not experienced)'
- 'brands used'
- 'bought from'

Usage:
    railway run python cleanup_empty_dimensions.py [--dry-run]
    python cleanup_empty_dimensions.py [--dry-run]

Options:
    --dry-run: Show what would be deleted without actually deleting
"""
import os
import sys
from sqlalchemy import create_engine, text
from app.config import get_settings

# Dimensions to remove (case-insensitive matching)
DIMENSIONS_TO_REMOVE = [
    'Results Hoped For (But NOT Experienced)'
]

def main():
    # Check for dry-run flag
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")
    
    settings = get_settings()
    database_url = settings.get_database_url()
    
    # Convert to psycopg format if needed
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg://')
    
    print(f"🔌 Connecting to database...")
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # First, let's see what we're dealing with
            print("\n📊 Checking for rows with empty dimensions...")
            print("=" * 80)
            
            # Build a query to find rows matching these dimensions
            # Match by dimension_name (case-insensitive, with some flexibility for spacing)
            dimension_conditions = []
            for dim in DIMENSIONS_TO_REMOVE:
                # Use ILIKE for case-insensitive matching and handle variations
                # Escape single quotes in dimension names
                escaped_dim = dim.replace("'", "''")
                dimension_conditions.append(f"dimension_name ILIKE '%{escaped_dim}%'")
            
            where_clause = " OR ".join(dimension_conditions)
            
            # Count rows matching these dimensions
            count_query = text(f"""
                SELECT COUNT(*) 
                FROM process_voc 
                WHERE {where_clause}
            """)
            
            result = conn.execute(count_query)
            total_matching = result.scalar()
            
            print(f"Found {total_matching:,} rows matching target dimensions")
            
            if total_matching == 0:
                print("⚠️  No rows found matching these exact dimensions.")
                print("   Searching for similar dimension names...")
                
                # Search for similar dimension names
                search_query = text("""
                    SELECT DISTINCT dimension_name, COUNT(*) as count
                    FROM process_voc
                    WHERE dimension_name ILIKE '%results hoped%' 
                       OR dimension_name ILIKE '%hoped for%'
                       OR dimension_name ILIKE '%not experienced%'
                    GROUP BY dimension_name
                    ORDER BY count DESC
                    LIMIT 10
                """)
                
                result = conn.execute(search_query)
                similar = result.fetchall()
                
                if similar:
                    print("\n   Found similar dimensions:")
                    for name, count in similar:
                        print(f"     • '{name}': {count:,} rows")
                    print("\n   💡 You may need to adjust the dimension name in the script.")
                else:
                    print("   No similar dimensions found.")
                
                print("\n✅ Nothing to clean up.")
                return
            
            # Show breakdown by dimension
            print("\n📋 Breakdown by dimension:")
            print("-" * 80)
            for dim in DIMENSIONS_TO_REMOVE:
                escaped_dim = dim.replace("'", "''")
                count_query = text(f"""
                    SELECT COUNT(*) 
                    FROM process_voc 
                    WHERE dimension_name ILIKE '%{escaped_dim}%'
                """)
                result = conn.execute(count_query)
                count = result.scalar()
                print(f"  • '{dim}': {count:,} rows")
            
            # Check how many have null/empty topics
            topics_query = text(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE topics IS NULL) as null_topics,
                    COUNT(*) FILTER (WHERE topics = '[]'::jsonb) as empty_array_topics,
                    COUNT(*) FILTER (WHERE topics IS NOT NULL AND topics != '[]'::jsonb) as has_topics
                FROM process_voc 
                WHERE {where_clause}
            """)
            
            result = conn.execute(topics_query)
            row = result.fetchone()
            total, null_topics, empty_array, has_topics = row
            
            print(f"\n📊 Topics analysis:")
            print("-" * 80)
            print(f"  • Total rows: {total:,}")
            print(f"  • Null topics: {null_topics:,}")
            print(f"  • Empty array topics: {empty_array:,}")
            print(f"  • Rows with topics: {has_topics:,}")
            
            # Show sample rows
            sample_query = text(f"""
                SELECT 
                    id,
                    dimension_ref,
                    dimension_name,
                    respondent_id,
                    topics IS NULL as has_null_topics,
                    topics = '[]'::jsonb as has_empty_array
                FROM process_voc 
                WHERE {where_clause}
                LIMIT 5
            """)
            
            result = conn.execute(sample_query)
            samples = result.fetchall()
            
            if samples:
                print(f"\n📝 Sample rows (first 5):")
                print("-" * 80)
                for sample in samples:
                    id_val, ref, name, resp_id, null_top, empty_arr = sample
                    topics_status = "NULL" if null_top else ("EMPTY" if empty_arr else "HAS DATA")
                    name_short = (name[:50] + "...") if name and len(name) > 50 else (name or "N/A")
                    print(f"  ID {id_val}: {name_short} | topics: {topics_status}")
            
            if dry_run:
                print("\n" + "=" * 80)
                print("🔍 DRY RUN: Would delete the following rows:")
                print("=" * 80)
                print(f"  • Total rows to delete: {total:,}")
                if has_topics > 0:
                    print(f"  ⚠️  {has_topics:,} rows have topics data (would also be deleted)")
                print("\n💡 Run without --dry-run to actually delete these rows")
                return
            
            # Ask for confirmation
            print("\n" + "=" * 80)
            print("⚠️  WARNING: This will DELETE all rows matching these dimensions!")
            print("=" * 80)
            
            if has_topics > 0:
                print(f"⚠️  WARNING: {has_topics:,} rows have topics data. These will also be deleted!")
                print("   Consider reviewing these rows first.")
            
            response = input("\n❓ Proceed with deletion? (type 'yes' to confirm): ")
            
            if response.lower() != 'yes':
                print("❌ Deletion cancelled.")
                return
            
            # Perform deletion
            print("\n🗑️  Deleting rows...")
            delete_query = text(f"""
                DELETE FROM process_voc 
                WHERE {where_clause}
            """)
            
            # Use begin() for transaction management
            with conn.begin():
                result = conn.execute(delete_query)
                deleted_count = result.rowcount
            
            print(f"✅ Successfully deleted {deleted_count:,} rows")
            
            # Verify deletion
            result = conn.execute(count_query)
            remaining = result.scalar()
            print(f"📊 Remaining rows matching these dimensions: {remaining:,}")
            
            if remaining == 0:
                print("✅ All target rows have been removed.")
            else:
                print(f"⚠️  {remaining:,} rows still match (may be due to case/spacing differences)")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

