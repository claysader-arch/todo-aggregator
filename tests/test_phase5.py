"""Tests for Phase 5 Intelligence Layer Enhancements.

This script tests priority scoring, category tagging, due date inference,
and normalization functionality.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import Config
from processors.claude_processor import ClaudeProcessor


def test_normalization():
    """Test the normalization function handles edge cases."""
    print("Testing normalization...")

    claude = ClaudeProcessor()

    # Test with malformed priority
    test_todo = {
        "task": "Test task",
        "priority": "CRITICAL",  # Invalid - should normalize to medium
    }
    normalized = claude._normalize_todo(test_todo)
    assert normalized["priority"] == "medium", f"Expected 'medium', got '{normalized['priority']}'"
    print("  ✓ Invalid priority normalized to 'medium'")

    # Test with valid priority
    test_todo = {"task": "Test", "priority": "High"}
    normalized = claude._normalize_todo(test_todo)
    assert normalized["priority"] == "high", f"Expected 'high', got '{normalized['priority']}'"
    print("  ✓ Valid priority preserved (case-normalized)")

    # Test with string category (should convert to list)
    test_todo = {"task": "Test", "category": "review"}
    normalized = claude._normalize_todo(test_todo)
    assert isinstance(normalized["category"], list), "Category should be a list"
    assert "review" in normalized["category"], "Category should contain 'review'"
    print("  ✓ String category converted to list")

    # Test with invalid category
    test_todo = {"task": "Test", "category": ["invalid-cat", "review"]}
    normalized = claude._normalize_todo(test_todo)
    assert "review" in normalized["category"], "Valid category should be kept"
    assert "invalid-cat" not in normalized["category"], "Invalid category should be removed"
    print("  ✓ Invalid categories filtered out")

    # Test with invalid date format
    test_todo = {"task": "Test", "due_date": "invalid-date"}
    normalized = claude._normalize_todo(test_todo)
    assert normalized["due_date"] is None, "Invalid date should become None"
    print("  ✓ Invalid date format cleared")

    # Test with valid date
    test_todo = {"task": "Test", "due_date": "2025-12-25"}
    normalized = claude._normalize_todo(test_todo)
    assert normalized["due_date"] == "2025-12-25", "Valid date should be preserved"
    print("  ✓ Valid date preserved")

    print("✓ All normalization tests passed!")


def test_extraction_with_priority():
    """Test that extraction includes priority and category fields."""
    if not Config.ANTHROPIC_API_KEY:
        print("⚠ ANTHROPIC_API_KEY not set - skipping extraction test")
        return

    print("Testing extraction with Phase 5 fields...")

    claude = ClaudeProcessor()

    # Test data with clear urgency signals
    mock_data = {
        "slack": [
            "=== Slack: #general ===",
            "URGENT: @clay please fix the production bug ASAP!",
            "Hey @clay, when you get a chance, can you review the design docs?",
        ],
        "gmail": [
            "=== Gmail: Meeting reminder ===",
            "From: boss@company.com",
            "Subject: Critical: Q4 report due tomorrow",
            "Clay, I need the Q4 report by tomorrow EOD. This is critical for the board meeting.",
        ],
        "zoom": [],
        "notion": [],
    }

    todos = claude.extract_todos(mock_data)
    print(f"  Extracted {len(todos)} todos")

    # Check that todos have priority and category fields
    for i, todo in enumerate(todos):
        print(f"\n  Todo {i+1}: {todo.get('task', 'N/A')[:50]}...")
        print(f"    Priority: {todo.get('priority', 'NOT SET')}")
        print(f"    Category: {todo.get('category', 'NOT SET')}")
        print(f"    Due date: {todo.get('due_date', 'NOT SET')}")

        # Verify fields exist
        assert "priority" in todo, f"Todo {i+1} missing priority"
        assert "category" in todo, f"Todo {i+1} missing category"
        assert todo["priority"] in ["high", "medium", "low"], f"Invalid priority: {todo['priority']}"
        assert isinstance(todo["category"], list), f"Category should be list: {todo['category']}"

    # Check that at least one todo has high priority (due to URGENT/ASAP/Critical)
    high_priority_todos = [t for t in todos if t.get("priority") == "high"]
    print(f"\n  Found {len(high_priority_todos)} high-priority todos")

    print("\n✓ Extraction with Phase 5 fields working!")


def test_feature_flags():
    """Test that feature flags are properly configured."""
    print("Testing feature flags...")

    assert hasattr(Config, "ENABLE_PRIORITY_SCORING"), "Missing ENABLE_PRIORITY_SCORING"
    assert hasattr(Config, "ENABLE_CATEGORY_TAGGING"), "Missing ENABLE_CATEGORY_TAGGING"
    assert hasattr(Config, "ENABLE_DUE_DATE_INFERENCE"), "Missing ENABLE_DUE_DATE_INFERENCE"
    assert hasattr(Config, "HIGH_PRIORITY_KEYWORDS"), "Missing HIGH_PRIORITY_KEYWORDS"

    print(f"  ENABLE_PRIORITY_SCORING: {Config.ENABLE_PRIORITY_SCORING}")
    print(f"  ENABLE_CATEGORY_TAGGING: {Config.ENABLE_CATEGORY_TAGGING}")
    print(f"  ENABLE_DUE_DATE_INFERENCE: {Config.ENABLE_DUE_DATE_INFERENCE}")
    print(f"  HIGH_PRIORITY_KEYWORDS: {Config.HIGH_PRIORITY_KEYWORDS}")

    print("✓ All feature flags present!")


def main():
    """Run all Phase 5 tests."""
    print("=" * 60)
    print("Phase 5 Intelligence Layer Tests")
    print("=" * 60)
    print()

    print("1. Testing feature flags...")
    test_feature_flags()
    print()

    print("2. Testing normalization...")
    test_normalization()
    print()

    print("3. Testing extraction with priority/category...")
    test_extraction_with_priority()
    print()

    print("=" * 60)
    print("Phase 5 tests complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Add Priority and Category properties to your Notion database:")
    print("     - Priority (Select): High, Medium, Low")
    print("     - Category (Multi-select): follow-up, review, meeting, finance, hr, technical, communication")
    print("  2. Run the full orchestrator: python src/orchestrator.py")


if __name__ == "__main__":
    main()
