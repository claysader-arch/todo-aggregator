"""Test Phase 2 with real Zoom data."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from config import Config
from mcp_clients.zoom_client import ZoomClient
from mcp_clients.notion_client import NotionClient
from processors.claude_processor import ClaudeProcessor

print("=" * 80)
print("Phase 2 Test - Real Zoom Data")
print("=" * 80)
print()

# Check credentials
if not Config.ZOOM_ACCOUNT_ID or not Config.ZOOM_CLIENT_ID or not Config.ZOOM_CLIENT_SECRET:
    print("✗ Zoom credentials not configured")
    print("Run test_zoom_connection.py first")
    sys.exit(1)

try:
    # Initialize clients
    zoom = ZoomClient()
    notion = NotionClient()
    claude = ClaudeProcessor()

    # Step 1: Fetch real Zoom meetings
    print("1. Fetching Zoom meeting content...")
    zoom_content = zoom.get_meeting_content(days=7)

    if not zoom_content:
        print("   ⚠ No meeting content found")
        print()
        print("   Possible reasons:")
        print("   - No meetings in past 7 days")
        print("   - Meetings don't have AI summaries or transcripts")
        print("   - Cloud recording not enabled")
        print()
        print("   Try running test_phase2_mock.py instead to see how it works")
        sys.exit(0)

    print(f"   ✓ Retrieved content from {len(zoom_content)} meetings")
    print()

    # Show preview of content
    print("   Preview of first meeting:")
    first_meeting = zoom_content[0]
    preview = first_meeting[:200] + "..." if len(first_meeting) > 200 else first_meeting
    print(f"   {preview}")
    print()

    # Step 2: Extract todos
    print("2. Extracting todos from meetings...")
    raw_content = {
        "slack": [],
        "gmail": [],
        "zoom": zoom_content,
        "notion": [],
    }

    extracted = claude.extract_todos(raw_content)
    zoom_todos = [t for t in extracted if t.get("source") == "ZOOM"]

    print(f"   ✓ Extracted {len(zoom_todos)} todos from Zoom meetings")
    print()

    if zoom_todos:
        print("   Extracted todos:")
        for i, todo in enumerate(zoom_todos[:10], 1):  # Show first 10
            print(f"   {i}. {todo.get('task', 'N/A')[:60]}...")
            if todo.get('assigned_to'):
                print(f"      → Assigned to: {todo['assigned_to']}")
            if todo.get('due_date'):
                print(f"      → Due: {todo['due_date']}")
            print(f"      → Confidence: {todo.get('confidence', 0):.2f}")
        if len(zoom_todos) > 10:
            print(f"   ... and {len(zoom_todos) - 10} more")
        print()

    # Step 3: Check duplicates
    print("3. Checking for duplicates...")
    existing = notion.get_all_todos()
    deduplicated = claude.deduplicate_todos(extracted, existing)

    new_count = len([t for t in deduplicated if "_update_id" not in t])
    dup_count = len([t for t in deduplicated if "_update_id" in t])

    print(f"   ✓ {new_count} new todos, {dup_count} duplicates")
    print()

    # Step 4: Option to write
    if new_count > 0:
        print("4. Write new todos to Notion?")
        response = input(f"   Write {new_count} todos to Notion? (yes/no): ")

        if response.lower() == "yes":
            created = 0
            for todo in deduplicated:
                if "_update_id" not in todo:
                    notion.create_page({
                        "task": todo.get("task", ""),
                        "status": "Open",
                        "source": [todo.get("source", "unknown")],
                        "due_date": todo.get("due_date"),
                        "confidence": todo.get("confidence", 0.0),
                        "dedupe_hash": todo.get("dedupe_hash", ""),
                    })
                    created += 1
                    print(f"   ✓ Created: {todo.get('task', 'N/A')[:50]}...")

            print()
            print(f"✓ Created {created} new todos in Notion")
        else:
            print("   Skipped writing to Notion")
    else:
        print("4. No new todos to write (all are duplicates)")

    print()
    print("=" * 80)
    print("Phase 2 test complete!")
    print("=" * 80)
    print()
    print("Next: Run `python3 src/orchestrator.py` for full pipeline")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
