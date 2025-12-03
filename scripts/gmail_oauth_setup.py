#!/usr/bin/env python3
"""
One-time OAuth setup script for Gmail API.

This script helps you obtain a refresh token for Gmail API access.

Usage:
    python3 scripts/gmail_oauth_setup.py /path/to/credentials.json

Prerequisites:
    1. Create a Google Cloud project at https://console.cloud.google.com
    2. Enable the Gmail API
    3. Create OAuth 2.0 credentials (Desktop app type)
    4. Download the credentials JSON file
"""

import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/gmail_oauth_setup.py /path/to/credentials.json")
        print()
        print("Download your OAuth credentials from Google Cloud Console:")
        print("  1. Go to https://console.cloud.google.com")
        print("  2. Select your project")
        print("  3. Go to APIs & Services > Credentials")
        print("  4. Create OAuth client ID (Desktop app)")
        print("  5. Download JSON file")
        sys.exit(1)

    credentials_path = Path(sys.argv[1])

    if not credentials_path.exists():
        print(f"Error: Credentials file not found: {credentials_path}")
        sys.exit(1)

    print("=" * 60)
    print("Gmail OAuth Setup")
    print("=" * 60)
    print()
    print("This script will open a browser window for Google sign-in.")
    print("After authorizing, you'll receive a refresh token to add to .env")
    print()

    try:
        # Load credentials file to extract client ID and secret
        with open(credentials_path) as f:
            creds_data = json.load(f)

        # Handle both "installed" (desktop) and "web" credential types
        if "installed" in creds_data:
            client_config = creds_data["installed"]
        elif "web" in creds_data:
            client_config = creds_data["web"]
        else:
            print("Error: Invalid credentials file format")
            print("Expected 'installed' or 'web' credentials")
            sys.exit(1)

        client_id = client_config.get("client_id")
        client_secret = client_config.get("client_secret")

        if not client_id or not client_secret:
            print("Error: Could not extract client_id or client_secret from credentials file")
            sys.exit(1)

        # Run OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path),
            scopes=SCOPES
        )

        print("Opening browser for authentication...")
        print()

        credentials = flow.run_local_server(
            port=8080,
            prompt="consent",
            access_type="offline"  # Required to get refresh token
        )

        if not credentials.refresh_token:
            print()
            print("Warning: No refresh token received.")
            print("This can happen if you've previously authorized this app.")
            print()
            print("To get a new refresh token:")
            print("  1. Go to https://myaccount.google.com/permissions")
            print("  2. Remove access for 'Todo Aggregator' (or your app name)")
            print("  3. Run this script again")
            sys.exit(1)

        print()
        print("=" * 60)
        print("SUCCESS! Add these to your .env file:")
        print("=" * 60)
        print()
        print(f"GMAIL_CLIENT_ID={client_id}")
        print(f"GMAIL_CLIENT_SECRET={client_secret}")
        print(f"GMAIL_REFRESH_TOKEN={credentials.refresh_token}")
        print()
        print("=" * 60)

    except Exception as e:
        print(f"Error during OAuth flow: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
