"""Test Phase 2 Zoom integration with mock data."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from mcp_clients.notion_client import NotionClient
from processors.claude_processor import ClaudeProcessor

# Mock Zoom meeting summaries
mock_zoom_data = [
    """Meeting: Q4 Planning Session (2025-12-01T10:00:00Z)

AI Summary:
The team discussed Q4 priorities and resource allocation. Key decisions made:
- Sarah will lead the new API integration project, targeting completion by end of Q4
- John needs to finalize the contract with the legal team by Wednesday
- Marketing team to prepare campaign materials for product launch
- Everyone should review and approve the budget proposal by Friday

Action items:
- Sarah: Start API integration work
- John: Follow up with legal on contract
- Marketing: Draft campaign materials
- All: Review budget proposal
""",
    """Meeting: Sprint Planning (2025-11-30T14:00:00Z)

Transcript excerpt:
Sarah: "I'll take on the authentication refactor this sprint. Should be done in 2 weeks."
John: "Can someone help me debug the payment gateway issue? It's blocking the release."
Maria: "I'll pair with John on the payment issue tomorrow morning."
Alex: "Don't forget we need to update the deployment docs before Friday's release."
""",
    """Meeting: Client Sync - Acme Corp (2025-11-29T15:00:00Z)

AI Summary:
Productive meeting with Acme Corp to discuss their requirements. Client requested:
- Custom reporting dashboard - timeline 3 weeks
- SSO integration with their Azure AD
- Training session for their team scheduled for Dec 15

Next steps:
- Send revised proposal with custom dashboard pricing
- Schedule technical call to discuss SSO implementation
- Prepare training materials and agenda
""",
]

print("=" * 80)
print("Phase 2 Test - Zoom Integration (Mock Data)")
print("=" * 80)
print()

# Initialize clients
notion = NotionClient()
claude = ClaudeProcessor()

# Step 1: Simulate Zoom content collection
print("1. Simulating Zoom meeting content collection...")
raw_content = {
    "slack": [],
    "gmail": [],
    "zoom": mock_zoom_data,
    "notion": [],
}
print(f"   ✓ Collected {len(mock_zoom_data)} Zoom meeting summaries")
print()

# Step 2: Extract todos using Claude
print("2. Extracting todos from Zoom meetings...")
extracted = claude.extract_todos(raw_content)
print(f"   ✓ Extracted {len(extracted)} todos")
print()

zoom_todos = [t for t in extracted if t.get("source") == "ZOOM"]
print(f"   Zoom-specific todos: {len(zoom_todos)}")
print()

for i, todo in enumerate(zoom_todos, 1):
    print(f"   Todo #{i}:")
    print(f"     Task: {todo.get('task', 'N/A')}")
    print(f"     Type: {todo.get('type', 'N/A')}")
    print(f"     Confidence: {todo.get('confidence', 0):.2f}")
    if todo.get('assigned_to'):
        print(f"     Assigned to: {todo['assigned_to']}")
    if todo.get('due_date'):
        print(f"     Due: {todo['due_date']}")
    print()

# Step 3: Check for duplicates
print("3. Checking for duplicates...")
existing = notion.get_all_todos()
print(f"   Found {len(existing)} existing todos in Notion")

deduplicated = claude.deduplicate_todos(extracted, existing)
new_count = len([t for t in deduplicated if "_update_id" not in t])
dup_count = len([t for t in deduplicated if "_update_id" in t])
print(f"   ✓ {new_count} new todos, {dup_count} duplicates")
print()

# Step 4: Option to write to Notion
print("4. Write new todos to Notion?")
response = input("   Write to Notion database? (yes/no): ")

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

print()
print("=" * 80)
print("Phase 2 test complete!")
print("=" * 80)
