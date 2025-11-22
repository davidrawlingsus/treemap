"""migrate metadata columns to survey_metadata

Revision ID: 009
Revises: 008
Create Date: 2025-11-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text, table, column, Integer
import json
import sys

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    """
    Migrate existing metadata columns (region, response_type, user_type, start_date, submit_date)
    to the survey_metadata JSONB column in the format:
    {
        "metadata": {
            "region": "...",
            "response_type": "...",
            "user_type": "...",
            "start_date": "...",
            "submit_date": "..."
        }
    }
    """
    conn = op.get_bind()
    
    # Get all rows that have at least one metadata field set
    result = conn.execute(text("""
        SELECT id, region, response_type, user_type, start_date, submit_date, survey_metadata
        FROM process_voc
        WHERE region IS NOT NULL 
           OR response_type IS NOT NULL 
           OR user_type IS NOT NULL 
           OR start_date IS NOT NULL 
           OR submit_date IS NOT NULL
    """))
    
    rows = result.fetchall()
    total_rows = len(rows)
    
    print(f"\n📊 Found {total_rows:,} rows with metadata to migrate...", flush=True)
    print("=" * 60, flush=True)
    sys.stdout.flush()
    
    # Define table structure once for efficiency
    process_voc_table = table('process_voc',
        column('id', Integer),
        column('survey_metadata', postgresql.JSONB)
    )
    
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    # Process in batches for better progress tracking - show progress more frequently
    batch_size = 50  # Show progress every 50 rows instead of 100
    commit_interval = 500  # Commit every 500 rows
    
    for idx, row in enumerate(rows, 1):
        try:
            row_id, region, response_type, user_type, start_date, submit_date, existing_survey_metadata = row
            
            # Build metadata object from existing columns
            metadata = {}
            
            if region is not None:
                metadata['region'] = region
            if response_type is not None:
                metadata['response_type'] = response_type
            if user_type is not None:
                metadata['user_type'] = user_type
            if start_date is not None:
                # Convert datetime to ISO format string
                if hasattr(start_date, 'isoformat'):
                    metadata['start_date'] = start_date.isoformat()
                else:
                    metadata['start_date'] = str(start_date)
            if submit_date is not None:
                # Convert datetime to ISO format string
                if hasattr(submit_date, 'isoformat'):
                    metadata['submit_date'] = submit_date.isoformat()
                else:
                    metadata['submit_date'] = str(submit_date)
            
            # Only proceed if we have metadata to migrate
            if not metadata:
                skipped_count += 1
                continue
            
            # Handle existing survey_metadata - merge if it exists
            if existing_survey_metadata and isinstance(existing_survey_metadata, dict):
                # If survey_metadata already has a "metadata" key, merge our values into it
                if 'metadata' in existing_survey_metadata:
                    # Merge existing metadata with new values (new values take precedence)
                    existing_metadata = existing_survey_metadata.get('metadata', {})
                    merged_metadata = {**existing_metadata, **metadata}
                    survey_metadata = {
                        **existing_survey_metadata,
                        'metadata': merged_metadata
                    }
                else:
                    # survey_metadata exists but doesn't have "metadata" key, wrap it
                    survey_metadata = {
                        'metadata': metadata,
                        **existing_survey_metadata  # Preserve other top-level keys
                    }
            else:
                # No existing survey_metadata, create new structure
                survey_metadata = {
                    'metadata': metadata
                }
            
            # Update using SQLAlchemy table update - this properly handles JSONB
            # SQLAlchemy will automatically convert the dict to JSONB
            conn.execute(
                process_voc_table.update().where(
                    process_voc_table.c.id == row_id
                ).values(
                    survey_metadata=survey_metadata
                )
            )
            
            migrated_count += 1
            
            # Progress indicator - flush immediately so it shows up
            if idx == 1:
                print(f"  Starting migration...", flush=True)
                sys.stdout.flush()
            elif idx % batch_size == 0:
                progress_pct = (idx / total_rows) * 100
                print(f"  Progress: {idx:,}/{total_rows:,} ({progress_pct:.1f}%) - Migrated: {migrated_count:,}, Skipped: {skipped_count:,}, Errors: {error_count:,}", flush=True)
                sys.stdout.flush()
            
            # Commit periodically to see progress and ensure it's saved
            if migrated_count % commit_interval == 0:
                conn.commit()
                print(f"  ✓ Committed {migrated_count:,} migrated rows so far...", flush=True)
                sys.stdout.flush()
                
        except Exception as e:
            error_count += 1
            print(f"  ❌ Error processing row {row_id}: {str(e)}", flush=True)
            sys.stdout.flush()
            if error_count <= 10:  # Show first 10 errors
                import traceback
                print(f"  Traceback: {traceback.format_exc()}", flush=True)
                sys.stdout.flush()
    
    # Final commit
    conn.commit()
    sys.stdout.flush()
    
    print("", flush=True)
    print("=" * 60, flush=True)
    print(f"✅ Migration complete!", flush=True)
    print(f"   Total rows processed: {total_rows:,}", flush=True)
    print(f"   Successfully migrated: {migrated_count:,}", flush=True)
    print(f"   Skipped (no metadata): {skipped_count:,}", flush=True)
    print(f"   Errors: {error_count:,}", flush=True)
    print("=" * 60, flush=True)
    sys.stdout.flush()


def downgrade():
    """
    Reverse migration: extract metadata from survey_metadata JSONB back to individual columns.
    Note: This will only restore the fields that were migrated, and may lose data if
    survey_metadata was modified after migration.
    """
    conn = op.get_bind()
    
    # Get all rows with survey_metadata
    result = conn.execute(text("""
        SELECT id, survey_metadata
        FROM process_voc
        WHERE survey_metadata IS NOT NULL
    """))
    
    rows = result.fetchall()
    
    for row in rows:
        row_id, survey_metadata = row
        
        if not survey_metadata or not isinstance(survey_metadata, dict):
            continue
        
        # Extract metadata from survey_metadata.metadata
        metadata = survey_metadata.get('metadata', {})
        
        if not metadata:
            continue
        
        # Build update statement with only non-null values
        update_fields = []
        update_values = {'id': row_id}
        
        if 'region' in metadata:
            update_fields.append('region = :region')
            update_values['region'] = metadata['region']
        
        if 'response_type' in metadata:
            update_fields.append('response_type = :response_type')
            update_values['response_type'] = metadata['response_type']
        
        if 'user_type' in metadata:
            update_fields.append('user_type = :user_type')
            update_values['user_type'] = metadata['user_type']
        
        if 'start_date' in metadata:
            update_fields.append('start_date = :start_date::timestamp with time zone')
            update_values['start_date'] = metadata['start_date']
        
        if 'submit_date' in metadata:
            update_fields.append('submit_date = :submit_date::timestamp with time zone')
            update_values['submit_date'] = metadata['submit_date']
        
        if update_fields:
            update_query = f"""
                UPDATE process_voc 
                SET {', '.join(update_fields)}
                WHERE id = :id
            """
            conn.execute(text(update_query), update_values)

