#!/usr/bin/env python3
"""
One-time script to update business_summary for all clients using OpenAI.

This script:
1. Gets the live business_context prompt from the prompts table
2. For each client, uses the prompt's system_message with the client's 
   business_summary (or client_url if business_summary is empty) as user_message
3. Calls OpenAI to generate/update the business_summary
4. Updates the client's business_summary field
"""

import sys
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# Load environment variables FIRST, before any imports
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parent
# Load .env.local first if it exists, then .env (so .env.local takes precedence)
LOCAL_ENV_FILE = PROJECT_ROOT / ".env.local"
if LOCAL_ENV_FILE.exists():
    load_dotenv(LOCAL_ENV_FILE, override=True)
# Always also load .env to ensure we get all variables
load_dotenv(PROJECT_ROOT / ".env", override=False)

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models import Client, Prompt
from app.services.openai_service import OpenAIService
from app.config import get_settings

settings = get_settings()


def get_business_context_prompt(db):
    """Get the live business_context prompt"""
    prompt = db.query(Prompt).filter(
        Prompt.prompt_purpose == "business_context",
        Prompt.status == "live"
    ).order_by(Prompt.version.desc()).first()
    
    if not prompt:
        raise ValueError("No live business_context prompt found in the prompts table")
    
    print(f"✓ Found prompt: {prompt.name} (version {prompt.version})")
    return prompt


def fetch_website_content(url, max_chars=3000):
    """Fetch and extract text content from a website"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up excessive whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        # Limit to max_chars to avoid token limits (leave room for system message and user message wrapper)
        if len(text) > max_chars:
            text = text[:max_chars] + '...'
        
        return text
    except Exception as e:
        return None


def update_client_business_summary(db, client, prompt, openai_service):
    """Update a single client's business_summary using OpenAI"""
    # Build user message - prioritize URL for fresh generation
    if client.client_url:
        # Fetch website content
        print(f"  Fetching website content from {client.client_url}...")
        website_content = fetch_website_content(client.client_url)
        
        if website_content:
            user_message = f"Client website: {client.client_url}\n\nWebsite content:\n{website_content}\n\nPlease provide a comprehensive business context based on this website content."
        else:
            print(f"  ⚠ Could not fetch website content, using URL only")
            user_message = f"Client website: {client.client_url}\n\nPlease provide a comprehensive business context based on this client's website."
    elif client.business_summary:
        user_message = f"Current business context:\n\n{client.business_summary}"
    else:
        user_message = f"Client name: {client.name}\n\nPlease provide a comprehensive business context for this client."
    
    try:
        # Call OpenAI
        result = openai_service.execute_prompt(
            system_message=prompt.system_message,
            user_message=user_message,
            model=prompt.llm_model
        )
        
        # Update business_summary with the generated content
        client.business_summary = result['content']
        
        db.commit()
        return True, result.get('tokens_used', 0)
    except Exception as e:
        db.rollback()
        return False, str(e)


def main():
    """Update business_summary for all clients or specific clients if names provided"""
    # Parse command-line arguments for specific client names
    client_names = sys.argv[1:] if len(sys.argv) > 1 else None
    
    print("=" * 60)
    print("Update Business Summaries Script")
    if client_names:
        print(f"Targeting specific clients: {', '.join(client_names)}")
    print("=" * 60)
    
    # Check OpenAI configuration
    openai_api_key = os.getenv('OPENAI_API_KEY') or getattr(settings, 'openai_api_key', None)
    if not openai_api_key:
        print("\n✗ Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    openai_service = OpenAIService(api_key=openai_api_key)
    
    db = SessionLocal()
    try:
        # Get the live business_context prompt
        print("\nStep 1: Finding business_context prompt...")
        prompt = get_business_context_prompt(db)
        
        # Get clients (all or filtered by name)
        print("\nStep 2: Loading clients...")
        if client_names:
            clients = db.query(Client).filter(Client.name.in_(client_names)).all()
            print(f"Found {len(clients)} matching clients")
            if len(clients) != len(client_names):
                found_names = {c.name for c in clients}
                missing = set(client_names) - found_names
                if missing:
                    print(f"⚠ Warning: Could not find clients: {', '.join(missing)}")
        else:
            clients = db.query(Client).all()
            print(f"Found {len(clients)} clients")
        
        # Update each client
        print("\nStep 3: Updating business summaries...")
        print("-" * 60)
        
        success_count = 0
        error_count = 0
        total_tokens = 0
        
        for i, client in enumerate(clients, 1):
            print(f"\n[{i}/{len(clients)}] Processing: {client.name}")
            
            # Skip "Bother" client (should be deleted) and "Prompt Engineering" (no URL)
            # unless they were specifically requested
            if client.name in ["Bother", "Prompt Engineering"] and not client_names:
                print(f"  ⚠ Skipping '{client.name}' client")
                continue
            
            if client.client_url:
                print(f"  URL: {client.client_url}")
            if client.business_summary:
                print(f"  Current summary: {client.business_summary[:100]}...")
            
            success, result = update_client_business_summary(db, client, prompt, openai_service)
            
            if success:
                success_count += 1
                tokens = result
                total_tokens += tokens
                print(f"  ✓ Updated successfully (tokens: {tokens})")
                print(f"  New summary: {client.business_summary[:100]}...")
            else:
                error_count += 1
                print(f"  ✗ Error: {result}")
        
        print("\n" + "=" * 60)
        print("✓ SCRIPT COMPLETE")
        print("=" * 60)
        print(f"Successfully updated: {success_count}")
        print(f"Errors: {error_count}")
        print(f"Total tokens used: {total_tokens}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

