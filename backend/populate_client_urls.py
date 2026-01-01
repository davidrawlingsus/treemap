#!/usr/bin/env python3
"""
One-time script to populate client_url field for all clients.

This script maps client names to their URLs and updates the database.
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models import Client

# Mapping of client names to URLs
# Note: "Bother" is intentionally excluded as it should be deleted
CLIENT_URLS = {
    "Liforme": "https://liforme.com/",
    "The Whisky Exchange": "https://www.thewhiskyexchange.com/",
    "Duffells": "https://www.duffells.com/",
    "Mous": "https://www.mous.co/",
    "Martin Randall Travel": "https://www.martinrandall.com/",
    "Online Stores": "https://www.united-states-flag.com/",
    "Omlet": "https://www.omlet.co.uk/",
    "Absolute Reg": "https://absolutereg.co.uk/",
    "Prep Kitchen": "https://prepkitchen.co.uk/",
    "Usewell": "https://usewell.ai/",
    "Wattbike": "https://wattbike.com/",
    "Holy Curls": "https://www.holycurls.com/",
    "Rabbies": "https://www.rabbies.com/",
    "NEOM Organics": "https://us.neomwellbeing.com/",
    "Relish": "https://relish-life.com/",
    "Varley": "https://www.varley.com/",
    "Hux": "https://dailyhiro.com/",
    "Evolve": "https://evolve.com/",
    "Katkin": "https://www.katkin.com/",
    "Elvie": "https://elvie.com/",
    "Ancient & Brave": "https://ancientandbrave.earth/",
    "Stocked": "https://stockedfood.com/",
    "The Turmeric Co": "https://theturmeric.co/",
    "Mark Spain Real Estate": "https://markspain.com/",
    "Sila": "https://silaservices.com/",
}


def main():
    """Populate client_url for all clients"""
    print("=" * 60)
    print("Populate Client URLs Script")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Get all clients
        clients = db.query(Client).all()
        print(f"\nFound {len(clients)} clients in database")
        
        updated_count = 0
        not_found = []
        
        for client in clients:
            # Skip "Prompt Engineering" as it has null URL
            if client.name == "Prompt Engineering":
                print(f"  ⚠ Skipping 'Prompt Engineering' (no URL provided)")
                continue
            
            if client.name in CLIENT_URLS:
                url = CLIENT_URLS[client.name]
                if client.client_url != url:
                    client.client_url = url
                    updated_count += 1
                    print(f"✓ Updated {client.name}: {url}")
                else:
                    print(f"  {client.name}: already set to {url}")
            else:
                not_found.append(client.name)
                print(f"⚠ No URL mapping found for: {client.name}")
        
        if updated_count > 0:
            db.commit()
            print(f"\n✓ Successfully updated {updated_count} client URLs")
        else:
            print("\n✓ No updates needed")
        
        if not_found:
            print(f"\n⚠ Warning: {len(not_found)} clients without URL mappings:")
            for name in not_found:
                print(f"   - {name}")
        
        print("\n" + "=" * 60)
        print("✓ SCRIPT COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

