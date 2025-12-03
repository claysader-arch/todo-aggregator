"""Test Zoom API connection and credentials."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from config import Config
from mcp_clients.zoom_client import ZoomClient

print("=" * 60)
print("Zoom API Connection Test")
print("=" * 60)
print()

# Check if credentials are configured
if not Config.ZOOM_ACCOUNT_ID or not Config.ZOOM_CLIENT_ID or not Config.ZOOM_CLIENT_SECRET:
    print("✗ Zoom credentials not configured")
    print()
    print("Please add the following to your .env file:")
    print("  ZOOM_ACCOUNT_ID=your-account-id")
    print("  ZOOM_CLIENT_ID=your-client-id")
    print("  ZOOM_CLIENT_SECRET=your-client-secret")
    print()
    print("See PHASE2_SETUP.md for detailed instructions.")
    sys.exit(1)

print("Testing Zoom API connection...")
print()

try:
    # Initialize client
    zoom = ZoomClient()

    # Test connection
    if zoom.test_connection():
        print()
        print("=" * 60)
        print("Connection successful!")
        print("=" * 60)
        print()

        # Try to fetch recent meetings
        print("Fetching recent meetings...")
        meetings = zoom.get_recent_meetings(days=7)

        print(f"✓ Found {len(meetings)} meetings in the past 7 days")
        print()

        if meetings:
            print("Recent meetings:")
            for meeting in meetings[:5]:  # Show first 5
                topic = meeting.get("topic", "Unknown")
                start_time = meeting.get("start_time", "")
                print(f"  - {topic} ({start_time})")

            if len(meetings) > 5:
                print(f"  ... and {len(meetings) - 5} more")
        else:
            print("No meetings found in the past 7 days.")
            print()
            print("Tips:")
            print("  - Ensure you have had at least one Zoom meeting")
            print("  - Try increasing the lookback period")
            print("  - Check that cloud recording is enabled")

        print()
        print("✓ Phase 2 is ready to use!")

    else:
        print()
        print("✗ Connection failed")
        print()
        print("Please check:")
        print("  1. Credentials are correct in .env")
        print("  2. Zoom Server-to-Server OAuth app is activated")
        print("  3. Required scopes are configured")
        print()
        print("See PHASE2_SETUP.md for troubleshooting.")

except Exception as e:
    print(f"✗ Error: {e}")
    print()
    print("See PHASE2_SETUP.md for troubleshooting.")
    import traceback
    traceback.print_exc()
