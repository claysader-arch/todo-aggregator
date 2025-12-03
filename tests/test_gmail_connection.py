#!/usr/bin/env python3
"""Test script for Gmail API connection and functionality."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import Config
from mcp_clients.gmail_client import GmailClient


def main():
    print("=" * 60)
    print("Gmail Connection Test")
    print("=" * 60)
    print()

    # Check credentials
    missing = []
    if not Config.GMAIL_CLIENT_ID:
        missing.append("GMAIL_CLIENT_ID")
    if not Config.GMAIL_CLIENT_SECRET:
        missing.append("GMAIL_CLIENT_SECRET")
    if not Config.GMAIL_REFRESH_TOKEN:
        missing.append("GMAIL_REFRESH_TOKEN")

    if missing:
        print(f"Missing required credentials: {', '.join(missing)}")
        print()
        print("To set up Gmail integration:")
        print("  1. Create OAuth credentials at https://console.cloud.google.com")
        print("  2. Run: python3 scripts/gmail_oauth_setup.py /path/to/credentials.json")
        print("  3. Add the output to your .env file")
        return False

    print(f"GMAIL_CLIENT_ID: {Config.GMAIL_CLIENT_ID[:20]}...")
    print(f"GMAIL_CLIENT_SECRET: {Config.GMAIL_CLIENT_SECRET[:10]}...")
    print(f"GMAIL_REFRESH_TOKEN: {Config.GMAIL_REFRESH_TOKEN[:20]}...")
    print()

    # Test connection
    print("Testing Gmail API connection...")
    gmail = GmailClient()

    if not gmail.test_connection():
        return False

    print()

    # Test fetching emails
    lookback_days = Config.GMAIL_LOOKBACK_DAYS
    print(f"Fetching emails from last {lookback_days} day(s)...")

    try:
        content = gmail.get_gmail_content(days=lookback_days)

        if content:
            print(f"Found {len(content)} emails")

            # Show sample
            print()
            print("Sample output (first email, truncated):")
            print("-" * 40)
            sample = content[0][:500] + "..." if len(content[0]) > 500 else content[0]
            print(sample)
            print("-" * 40)
        else:
            print("No emails found in the specified time period")
            print("  This might be normal if there was no email activity")

    except Exception as e:
        print(f"Error fetching emails: {e}")
        return False

    print()
    print("=" * 60)
    print("Gmail connection test complete!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
