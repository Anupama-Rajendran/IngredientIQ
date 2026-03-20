#!/usr/bin/env python3
"""Test that ANTHROPIC_API_KEY is properly loaded from .env"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings

print("\n" + "="*60)
print("ANTHROPIC API KEY TEST")
print("="*60)

if settings.ANTHROPIC_API_KEY:
    key_preview = settings.ANTHROPIC_API_KEY[:20] + "..." + settings.ANTHROPIC_API_KEY[-10:]
    print(f"✅ API Key Found: {key_preview}")
    print(f"   Length: {len(settings.ANTHROPIC_API_KEY)} characters")
    print(f"\n✅ Backend is properly configured for image analysis")
else:
    print("❌ ANTHROPIC_API_KEY NOT FOUND")
    print("\nPlease ensure:")
    print("  1. backend/.env file exists")
    print("  2. ANTHROPIC_API_KEY= is set in .env")
    print("  3. Backend is restarted after modifying .env")

print(f"\nLLM Provider: {settings.LLM_PROVIDER}")
print(f"LLM Model: {settings.LLM_MODEL}")
print("="*60 + "\n")
