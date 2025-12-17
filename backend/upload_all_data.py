#!/usr/bin/env python3
"""
Bulk upload script for importing all data sources from the data_sources/ directory.
Automatically creates clients and data sources with proper relationships.
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional
import re

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import Client, DataSource
from app.transformers import DataTransformer


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def parse_folder_name(folder_name: str) -> Tuple[str, str]:
    """
    Parse folder name to extract client name and source type.
    Format: "{Client Name} - {Source Type}"
    
    Examples:
        "Ancient & Brave - Success Page Survey" -> ("Ancient & Brave", "Success Page Survey")
        "The Whisky Exchange - Email Survey" -> ("The Whisky Exchange", "Email Survey")
    """
    # Split by " - " (space-dash-space)
    parts = folder_name.split(' - ')
    
    if len(parts) >= 2:
        client_name = parts[0].strip()
        source_name = ' - '.join(parts[1:]).strip()  # Join remaining parts in case there are multiple " - "
        return client_name, source_name
    else:
        # If no separator found, use entire name as client, and "Unknown Source" as source
        return folder_name.strip(), "Unknown Source"


def get_or_create_client(db: Session, client_name: str) -> Client:
    """Get existing client or create new one"""
    # Check if client exists
    client = db.query(Client).filter(Client.name == client_name).first()
    
    if client:
        print(f"  ✓ Using existing client: {client_name}")
        return client
    
    # Create new client
    slug = slugify(client_name)
    
    # Ensure slug is unique
    base_slug = slug
    counter = 1
    while db.query(Client).filter(Client.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    client = Client(
        name=client_name,
        slug=slug,
        is_active=True,
        settings={}
    )
    
    db.add(client)
    db.commit()
    db.refresh(client)
    
    print(f"  ✓ Created new client: {client_name} (slug: {slug})")
    return client


def upload_data_source(
    db: Session,
    folder_path: Path,
    client: Client,
    source_name: str
) -> Optional[DataSource]:
    """Upload a single data source from a folder"""
    
    project_info_path = folder_path / "project_info.json"
    rows_path = folder_path / "rows.json"
    
    # Check if required files exist
    if not project_info_path.exists():
        print(f"  ✗ Skipping: project_info.json not found")
        return None
    
    if not rows_path.exists():
        print(f"  ✗ Skipping: rows.json not found")
        return None
    
    try:
        # Read project info
        with open(project_info_path, 'r', encoding='utf-8') as f:
            project_info = json.load(f)
        
        # Read rows data
        with open(rows_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        if not isinstance(raw_data, list):
            print(f"  ✗ Skipping: rows.json is not a list")
            return None
        
        print(f"  → Loaded {len(raw_data)} rows")
        
        # Detect format
        detected_format = DataTransformer.detect_format(raw_data)
        print(f"  → Detected format: {detected_format.value}")
        
        # Transform data
        normalized_data = DataTransformer.transform(raw_data, detected_format)
        print(f"  → Transformed to {len(normalized_data)} normalized rows")
        
        # Create full name for the data source
        full_name = f"{client.name} - {source_name}"
        
        # Check if data source already exists
        existing = db.query(DataSource).filter(
            DataSource.name == full_name,
            DataSource.client_id == client.id
        ).first()
        
        if existing:
            print(f"  ⚠ Data source already exists: {full_name}")
            return existing
        
        # Create data source
        data_source = DataSource(
            name=full_name,
            client_id=client.id,
            source_name=source_name,
            source_type=project_info.get('tags', [''])[0] if project_info.get('tags') else 'survey',
            source_format=detected_format.value,
            raw_data=raw_data,
            normalized_data=normalized_data,
            is_normalized=True
        )
        
        db.add(data_source)
        db.commit()
        db.refresh(data_source)
        
        print(f"  ✓ Created data source: {full_name}")
        return data_source
        
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON decode error: {e}")
        return None
    except Exception as e:
        print(f"  ✗ Error: {e}")
        db.rollback()
        return None


def main():
    """Main upload process"""
    print("=" * 80)
    print("Multi-Tenant Data Upload Script")
    print("=" * 80)
    print()
    
    # Get data_sources directory
    # Assumes script is in backend/ and data_sources/ is in parent directory
    script_dir = Path(__file__).parent
    data_sources_dir = script_dir.parent / "data_sources"
    
    if not data_sources_dir.exists():
        print(f"Error: data_sources directory not found at {data_sources_dir}")
        return
    
    print(f"Scanning directory: {data_sources_dir}")
    print()
    
    # Get all subdirectories
    folders = [f for f in data_sources_dir.iterdir() if f.is_dir()]
    folders.sort()
    
    print(f"Found {len(folders)} folders to process")
    print()
    
    # Create database session
    db = SessionLocal()
    
    try:
        stats = {
            'total_folders': len(folders),
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'clients_created': 0,
            'data_sources_created': 0
        }
        
        clients_before = db.query(Client).count()
        
        for folder in folders:
            folder_name = folder.name
            print(f"[{stats['processed'] + stats['skipped'] + stats['errors'] + 1}/{stats['total_folders']}] Processing: {folder_name}")
            
            # Parse folder name
            client_name, source_name = parse_folder_name(folder_name)
            print(f"  → Client: {client_name}")
            print(f"  → Source: {source_name}")
            
            try:
                # Get or create client
                client = get_or_create_client(db, client_name)
                
                # Upload data source
                data_source = upload_data_source(db, folder, client, source_name)
                
                if data_source:
                    stats['processed'] += 1
                else:
                    stats['skipped'] += 1
                
            except Exception as e:
                print(f"  ✗ Unexpected error: {e}")
                stats['errors'] += 1
                db.rollback()
            
            print()
        
        clients_after = db.query(Client).count()
        data_sources_after = db.query(DataSource).count()
        
        stats['clients_created'] = clients_after - clients_before
        stats['data_sources_created'] = stats['processed']
        
        # Print summary
        print("=" * 80)
        print("Upload Summary")
        print("=" * 80)
        print(f"Total folders scanned:    {stats['total_folders']}")
        print(f"Successfully processed:   {stats['processed']}")
        print(f"Skipped:                  {stats['skipped']}")
        print(f"Errors:                   {stats['errors']}")
        print(f"Clients created:          {stats['clients_created']}")
        print(f"Data sources created:     {stats['data_sources_created']}")
        print(f"Total clients in DB:      {clients_after}")
        print(f"Total data sources in DB: {data_sources_after}")
        print("=" * 80)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()

