"""Quick test script for Phase 1 implementation.

This script tests the basic functionality without requiring full API credentials.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from processors.claude_processor import ClaudeProcessor
from mcp_clients.notion_client import NotionClient


def test_imports():
    """Test that all modules can be imported."""
    print("✓ Successfully imported ClaudeProcessor")
    print("✓ Successfully imported NotionClient")


def test_mock_extraction():
    """Test todo extraction with mock data (requires ANTHROPIC_API_KEY)."""
    try:
        from config import Config

        if not Config.ANTHROPIC_API_KEY:
            print("⚠ ANTHROPIC_API_KEY not set - skipping extraction test")
            return

        claude = ClaudeProcessor()
        print("✓ Successfully initialized ClaudeProcessor")

        # Mock some sample content
        mock_data = {
            "slack": [
                "Hey @john, can you send me the Q4 report by Friday?",
                "I'll review the design mockups tomorrow morning.",
            ],
            "gmail": ["Meeting notes: Action item - follow up with client about contract"],
            "zoom": [],
            "notion": [],
        }

        print("\nTesting todo extraction with sample data...")
        todos = claude.extract_todos(mock_data)
        print(f"✓ Extracted {len(todos)} todos")

        if todos:
            print("\nSample extracted todo:")
            print(f"  Task: {todos[0].get('task', 'N/A')}")
            print(f"  Source: {todos[0].get('source', 'N/A')}")
            print(f"  Confidence: {todos[0].get('confidence', 'N/A')}")

    except Exception as e:
        print(f"✗ Error during extraction test: {e}")
        import traceback

        traceback.print_exc()


def test_notion_client():
    """Test Notion client initialization (requires NOTION_API_KEY)."""
    try:
        from config import Config

        if not Config.NOTION_API_KEY or not Config.NOTION_DATABASE_ID:
            print("⚠ NOTION_API_KEY or NOTION_DATABASE_ID not set - skipping Notion test")
            return

        notion = NotionClient()
        print("✓ Successfully initialized NotionClient")

        # Test querying the database (this will actually call the API)
        print("\nTesting Notion database query...")
        todos = notion.get_all_todos()
        print(f"✓ Successfully queried Notion database")
        print(f"  Found {len(todos)} existing todos")

    except Exception as e:
        print(f"✗ Error during Notion test: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 1 Implementation Test")
    print("=" * 60)
    print()

    print("1. Testing imports...")
    test_imports()
    print()

    print("2. Testing Claude extraction...")
    test_mock_extraction()
    print()

    print("3. Testing Notion client...")
    test_notion_client()
    print()

    print("=" * 60)
    print("Test complete!")
    print("=" * 60)
    print()
    print("To run the full orchestrator, ensure you have:")
    print("  1. Created a .env file with your API keys")
    print("  2. Set up your Notion database with the required properties")
    print("  3. Run: python src/orchestrator.py")


if __name__ == "__main__":
    main()
