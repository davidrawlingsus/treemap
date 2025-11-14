#!/usr/bin/env python3
"""
Quick test script to verify magic link token generation and validation.
This script tests the token flow without sending emails or making API calls.

USAGE:
    cd backend
    source venv/bin/activate  # Activate virtual environment first
    python test_magic_link.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))

from app.auth import generate_magic_link_token, hash_token, is_magic_link_token_valid
from app.models import User


def test_token_generation():
    """Test token generation and hashing"""
    print("=" * 60)
    print("TEST 1: Token Generation")
    print("=" * 60)
    
    token, token_hash, expires_at = generate_magic_link_token()
    
    print(f"✓ Token generated (length: {len(token)})")
    print(f"✓ Token hash (SHA-256): {token_hash}")
    print(f"✓ Expires at: {expires_at}")
    print(f"✓ Time until expiry: {(expires_at - datetime.now(timezone.utc)).total_seconds() / 60:.1f} minutes")
    
    # Verify the hash is consistent
    rehashed = hash_token(token)
    assert rehashed == token_hash, "Hash verification failed!"
    print(f"✓ Hash verification successful")
    
    return token, token_hash, expires_at


def test_token_validation():
    """Test token validation logic"""
    print("\n" + "=" * 60)
    print("TEST 2: Token Validation")
    print("=" * 60)
    
    # Create a mock user
    token, token_hash, expires_at = generate_magic_link_token()
    
    user = User()
    user.email = "test@example.com"
    user.magic_link_token = token_hash
    user.magic_link_expires_at = expires_at
    
    # Test 1: Valid token
    print("\n1. Testing valid token...")
    is_valid, reason = is_magic_link_token_valid(user, token)
    assert is_valid and reason == "valid", f"Expected valid token, got: {reason}"
    print(f"   ✓ Valid token accepted: {reason}")
    
    # Test 2: Wrong token
    print("\n2. Testing wrong token...")
    wrong_token = "wrong_token_value"
    is_valid, reason = is_magic_link_token_valid(user, wrong_token)
    assert not is_valid and reason == "token_mismatch", f"Expected token_mismatch, got: {reason}"
    print(f"   ✓ Wrong token rejected: {reason}")
    
    # Test 3: Expired token
    print("\n3. Testing expired token...")
    user.magic_link_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    is_valid, reason = is_magic_link_token_valid(user, token)
    assert not is_valid and reason == "token_expired", f"Expected token_expired, got: {reason}"
    print(f"   ✓ Expired token rejected: {reason}")
    
    # Test 4: No stored token
    print("\n4. Testing missing stored token...")
    user.magic_link_token = None
    user.magic_link_expires_at = expires_at
    is_valid, reason = is_magic_link_token_valid(user, token)
    assert not is_valid and reason == "no_stored_token", f"Expected no_stored_token, got: {reason}"
    print(f"   ✓ Missing token rejected: {reason}")
    
    # Test 5: No provided token
    print("\n5. Testing missing provided token...")
    user.magic_link_token = token_hash
    is_valid, reason = is_magic_link_token_valid(user, "")
    assert not is_valid and reason == "no_token_provided", f"Expected no_token_provided, got: {reason}"
    print(f"   ✓ Empty token rejected: {reason}")
    
    print("\n✓ All validation tests passed!")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("MAGIC LINK TOKEN TEST SUITE")
    print("=" * 60)
    
    try:
        test_token_generation()
        test_token_validation()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print("\nThe magic link token generation and validation logic is working correctly.")
        print("If you're still having issues, check:")
        print("  1. Database persistence (tokens being saved)")
        print("  2. Environment variables (FRONTEND_BASE_URL)")
        print("  3. Server logs for detailed error messages")
        print()
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

