"""Complete Phase 2 test - automatically write todos to Notion."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from config import Config
from mcp_clients.zoom_client import ZoomClient
from mcp_clients.notion_client import NotionClient
from processors.claude_processor import ClaudeProcessor

print("=" * 80)
print("Phase 2 Complete Test - Zoom → Claude → Notion")
print("=" * 80)
print()

try:
    # Initialize clients
    zoom = ZoomClient()
    notion = NotionClient()
    claude = ClaudeProcessor()

    # Step 1: Fetch Zoom meetings
    print("1. Fetching Zoom meeting summaries (last 7 days)...")
    zoom_content = zoom.get_meeting_content(days=7)

    if not zoom_content:
        print("   ⚠ No meeting summaries found")
        sys.exit(0)

    print(f"   ✓ Retrieved {len(zoom_content)} meeting summaries")
    print()

    # Step 2: Extract todos with Claude
    print("2. Extracting todos with Claude Opus 4.5...")
    raw_content = {
        "slack": [],
        "gmail": [],
        "zoom": zoom_content,
        "notion": [],
    }

    extracted = claude.extract_todos(raw_content)
    zoom_todos = [t for t in extracted if t.get("source") == "ZOOM"]

    print(f"   ✓ Extracted {len(zoom_todos)} todos from Zoom")
    print()

    # Show sample before filtering
    if zoom_todos:
        print("   Sample todos:")
        for i, todo in enumerate(zoom_todos[:5], 1):
            task = todo.get('task', 'N/A')
            assigned = todo.get('assigned_to', 'Unassigned')
            print(f"   {i}. {task[:70]}")
            print(f"      → {assigned}")
        if len(zoom_todos) > 5:
            print(f"   ... and {len(zoom_todos) - 5} more")
        print()

    # Step 3: Filter to only user's todos
    print("3. Filtering todos...")
    from orchestrator import filter_my_todos
    filtered = filter_my_todos(extracted)
    print()

    # Step 4: Deduplicate
    print("4. Checking for duplicates against Notion...")
    existing = notion.get_all_todos()
    deduplicated = claude.deduplicate_todos(filtered, existing)

    new_count = len([t for t in deduplicated if "_update_id" not in t])
    dup_count = len([t for t in deduplicated if "_update_id" in t])

    print(f"   ✓ {new_count} new todos, {dup_count} duplicates")
    print()

    # Step 5: Write to Notion
    if new_count > 0:
        print(f"5. Writing {new_count} new todos to Notion...")
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
                task_preview = todo.get('task', 'N/A')[:60]
                print(f"   ✓ Created: {task_preview}...")

        print()
        print(f"   ✓ Successfully created {created} todos in Notion")
    else:
        print("4. No new todos to write (all duplicates)")

    print()
    print("=" * 80)
    print("✓ Phase 2 Complete!")
    print("=" * 80)
    print()
    print(f"Summary:")
    print(f"  - Processed {len(zoom_content)} Zoom meetings")
    print(f"  - Extracted {len(zoom_todos)} todos total")
    print(f"  - Filtered to {len(filtered)} todos assigned to you")
    print(f"  - Created {new_count} new todos in Notion")
    print(f"  - Found {dup_count} duplicates (skipped)")
    print()
    print("Check your Notion database to see the new todos!")
    print()

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
