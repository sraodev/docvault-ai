#!/usr/bin/env python3
"""
Test OpenRouter API Key Configuration
This script helps verify and test your OpenRouter API key setup.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, AI_PROVIDER
from app.services.providers import OpenRouterProvider
from openai import OpenAI

def test_openrouter_key(api_key: str = None):
    """Test OpenRouter API key."""
    key_to_test = api_key or OPENROUTER_API_KEY
    
    print("=" * 60)
    print("OpenRouter API Key Test")
    print("=" * 60)
    print()
    
    if not key_to_test:
        print("✗ No API key provided")
        print("\nTo set your API key:")
        print("1. Get your key from: https://openrouter.ai/keys")
        print("2. Add to .env file: OPENROUTER_API_KEY=your-key-here")
        return False
    
    print(f"✓ API Key found: {key_to_test[:15]}...{key_to_test[-10:]}")
    print(f"  Length: {len(key_to_test)} characters")
    print()
    
    # Initialize client
    try:
        client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=key_to_test
        )
        print("✓ Client initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize client: {e}")
        return False
    
    # Test API call
    print("\nTesting API call...")
    try:
        response = client.chat.completions.create(
            model="anthropic/claude-3-haiku",
            messages=[{"role": "user", "content": "Say 'Hello' in one word"}],
            max_tokens=10
        )
        print("✓ API call successful!")
        print(f"  Response: {response.choices[0].message.content}")
        print("\n🎉 Your OpenRouter API key is working correctly!")
        return True
    except Exception as e:
        error_str = str(e)
        print(f"✗ API call failed")
        
        if "402" in error_str or "insufficient credits" in error_str.lower():
            print("\n⚠️  Issue: Insufficient Credits")
            print("   Your API key is valid but your account needs credits.")
            print("\n   To add credits:")
            print("   1. Visit: https://openrouter.ai/settings/credits")
            print("   2. Add credits to your account")
            print("   3. Try again")
        elif "401" in error_str or "unauthorized" in error_str.lower():
            print("\n✗ Issue: Invalid API Key")
            print("   Your API key is not valid or has been revoked.")
            print("\n   To get a new key:")
            print("   1. Visit: https://openrouter.ai/keys")
            print("   2. Create a new API key")
            print("   3. Update .env file with the new key")
        else:
            print(f"\n   Error details: {error_str[:300]}")
        
        return False

def check_configuration():
    """Check current configuration."""
    print("=" * 60)
    print("Current Configuration")
    print("=" * 60)
    print(f"AI Provider: {AI_PROVIDER}")
    print(f"OpenRouter Base URL: {OPENROUTER_BASE_URL}")
    print(f"OpenRouter API Key: {'✓ Set' if OPENROUTER_API_KEY else '✗ Not Set'}")
    print()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test OpenRouter API Key")
    parser.add_argument("--key", type=str, help="API key to test (optional, uses .env if not provided)")
    parser.add_argument("--check", action="store_true", help="Only check configuration, don't test")
    
    args = parser.parse_args()
    
    check_configuration()
    
    if not args.check:
        success = test_openrouter_key(args.key)
        sys.exit(0 if success else 1)

