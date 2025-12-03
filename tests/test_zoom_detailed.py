"""Test updated Zoom client with detailed output."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from mcp_clients.zoom_client import ZoomClient

zoom = ZoomClient()

print("Testing updated get_recent_meetings...")
print()

meetings = zoom.get_recent_meetings(days=7)

print(f"Total meetings returned: {len(meetings)}")
print()

if meetings:
    print("First 3 meetings:")
    for i, meeting in enumerate(meetings[:3], 1):
        print(f"{i}. {meeting.get('topic')}")
        print(f"   ID: {meeting.get('uuid')}")
        print(f"   Start: {meeting.get('start_time')}")
        print()
else:
    print("No meetings found. Checking logs above for errors...")
