#!/usr/bin/env python3
"""
Migration script to update existing data sources with normalized data.

This script:
1. Adds new columns to the data_sources table (source_format, normalized_data, is_normalized)
2. Transforms existing raw_data to normalized_data format
3. Updates records in the database
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models import DataSource
from app.transformers import DataTransformer, DataSourceType


def add_columns_if_not_exist():
    """Add new columns to data_sources table if they don't exist"""
    with engine.connect() as connection:
        # Check if columns exist and add them if they don't
        try:
            # Add source_format column
            connection.execute(text("""
                ALTER TABLE data_sources 
                ADD COLUMN IF NOT EXISTS source_format VARCHAR(50) DEFAULT 'intercom_mrt'
            """))
            
            # Add normalized_data column
            connection.execute(text("""
                ALTER TABLE data_sources 
                ADD COLUMN IF NOT EXISTS normalized_data JSONB
            """))
            
            # Add is_normalized column
            connection.execute(text("""
                ALTER TABLE data_sources 
                ADD COLUMN IF NOT EXISTS is_normalized BOOLEAN DEFAULT FALSE
            """))
            
            connection.commit()
            print("✓ Database columns added/verified")
        except Exception as e:
            print(f"Error adding columns: {e}")
            raise


def migrate_existing_data():
    """Transform existing raw_data to normalized format"""
    db = SessionLocal()
    try:
        # Get all data sources
        data_sources = db.query(DataSource).all()
        print(f"\nFound {len(data_sources)} data sources to migrate")
        
        for ds in data_sources:
            print(f"\nMigrating: {ds.name} (ID: {ds.id})")
            
            # Skip if already normalized
            if ds.is_normalized and ds.normalized_data:
                print(f"  ✓ Already normalized, skipping")
                continue
            
            # Detect format
            detected_format = DataTransformer.detect_format(ds.raw_data)
            print(f"  Detected format: {detected_format.value}")
            
            # Transform data
            try:
                normalized_data = DataTransformer.transform(ds.raw_data, detected_format)
                print(f"  Transformed {len(ds.raw_data)} raw rows → {len(normalized_data)} normalized rows")
                
                # Update the record
                ds.source_format = detected_format.value
                ds.normalized_data = normalized_data
                ds.is_normalized = True
                
                db.commit()
                print(f"  ✓ Migration successful")
            except Exception as e:
                print(f"  ✗ Error transforming data: {e}")
                db.rollback()
                continue
        
        print("\n✓ Migration complete!")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Run the migration"""
    print("=" * 60)
    print("Data Source Migration Script")
    print("=" * 60)
    print("\nThis script will:")
    print("1. Add new columns to the database")
    print("2. Transform existing data to normalized format")
    print("3. Update all data source records")
    print("\n" + "=" * 60)
    
    try:
        # Step 1: Add columns
        print("\nStep 1: Adding database columns...")
        add_columns_if_not_exist()
        
        # Step 2: Migrate data
        print("\nStep 2: Migrating existing data sources...")
        migrate_existing_data()
        
        print("\n" + "=" * 60)
        print("✓ MIGRATION SUCCESSFUL")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ MIGRATION FAILED")
        print("=" * 60)
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

