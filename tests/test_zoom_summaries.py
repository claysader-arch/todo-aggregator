"""Test the updated Zoom client with real meeting summaries."""

import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from mcp_clients.zoom_client import ZoomClient

print("=" * 80)
print("Testing Zoom Meeting Summaries Integration")
print("=" * 80)
print()

zoom = ZoomClient()

# Test connection
print("1. Testing Zoom API connection...")
if not zoom.test_connection():
    print("   ✗ Connection failed. Check credentials.")
    sys.exit(1)
print()

# Get meeting summaries from last 7 days
print("2. Fetching meeting summaries from last 7 days...")
content = zoom.get_meeting_content(days=7)

print()
print("=" * 80)
print(f"Results: Found {len(content)} meetings with AI summaries")
print("=" * 80)
print()

if content:
    print("Meeting summaries:")
    print()
    for i, summary in enumerate(content, 1):
        lines = summary.split('\n')
        header = lines[0] if lines else "Unknown Meeting"
        preview = summary[:300] + "..." if len(summary) > 300 else summary

        print(f"{i}. {header}")
        print("-" * 80)
        print(preview)
        print()
        print()
else:
    print("⚠ No meeting summaries found.")
    print()
    print("Possible reasons:")
    print("  - No meetings in the last 7 days")
    print("  - AI Companion not enabled")
    print("  - Meeting summaries not generated yet")
    print()

print("=" * 80)
print("✓ Zoom integration test complete!")
print("=" * 80)
