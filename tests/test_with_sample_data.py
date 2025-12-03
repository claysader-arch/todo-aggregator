"""Test Phase 1 with sample data to see full pipeline in action."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from mcp_clients.notion_client import NotionClient
from processors.claude_processor import ClaudeProcessor

# Sample content from different platforms
sample_data = {
    "slack": [
        "Hey team, can someone send me the Q4 financial report by end of week? Thanks!",
        "I'll review the new design mockups and provide feedback by tomorrow.",
        "Meeting notes: Action item - @john to follow up with legal team about contract.",
    ],
    "gmail": [
        "Action items from today's meeting:\n1. Schedule follow-up call with client\n2. Send proposal document",
        "Don't forget - presentation slides need to be ready for Thursday's meeting.",
    ],
    "zoom": [
        "From yesterday's standup: Sarah mentioned she'll finish the API integration this week.",
    ],
    "notion": [],
}

print("=" * 80)
print("Testing Phase 1 with Sample Data")
print("=" * 80)
print()

# Initialize clients
notion = NotionClient()
claude = ClaudeProcessor()

# Step 1: Extract todos
print("1. Extracting todos from sample content...")
extracted = claude.extract_todos(sample_data)
print(f"   ✓ Extracted {len(extracted)} todos")
print()

for i, todo in enumerate(extracted, 1):
    print(f"   Todo #{i}:")
    print(f"     Task: {todo.get('task', 'N/A')}")
    print(f"     Source: {todo.get('source', 'N/A')}")
    print(f"     Type: {todo.get('type', 'N/A')}")
    print(f"     Confidence: {todo.get('confidence', 0):.2f}")
    if todo.get('assigned_to'):
        print(f"     Assigned to: {todo['assigned_to']}")
    if todo.get('due_date'):
        print(f"     Due: {todo['due_date']}")
    print()

# Step 2: Check existing todos in Notion
print("2. Checking existing todos in Notion...")
existing = notion.get_all_todos()
print(f"   ✓ Found {len(existing)} existing todos")
print()

# Step 3: Deduplicate
print("3. Deduplicating against existing todos...")
deduplicated = claude.deduplicate_todos(extracted, existing)
new_count = len([t for t in deduplicated if "_update_id" not in t])
dup_count = len([t for t in deduplicated if "_update_id" in t])
print(f"   ✓ {new_count} new todos, {dup_count} duplicates")
print()

# Step 4: Write to Notion
print("4. Writing to Notion database...")
for todo in deduplicated:
    if "_update_id" not in todo:
        # Create with all properties
        page_data = {
            "task": todo.get("task", ""),
            "status": "Open",
            "source": [todo.get("source", "unknown")],
            "due_date": todo.get("due_date"),
            "confidence": todo.get("confidence", 0.0),
            "dedupe_hash": todo.get("dedupe_hash", ""),
        }
        notion.create_page(page_data)
        print(f"   ✓ Created: {todo.get('task', 'N/A')[:50]}...")

print()
print("=" * 80)
print("Test complete! Check your Notion database to see the new todos.")
print("=" * 80)
