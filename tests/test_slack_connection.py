#!/usr/bin/env python3
"""Test script for Slack API connection and functionality."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import Config
from mcp_clients.slack_client import SlackClient


def main():
    print("=" * 60)
    print("Slack Connection Test")
    print("=" * 60)
    print()

    # Check token format
    token = Config.SLACK_USER_TOKEN
    if not token:
        print("✗ SLACK_USER_TOKEN not set in .env")
        print("\nPlease add your Slack User OAuth Token to .env:")
        print("SLACK_USER_TOKEN=xoxp-...")
        return False

    if not token.startswith("xoxp-"):
        print(f"⚠ Token doesn't start with 'xoxp-' (user token)")
        print(f"  Got: {token[:10]}...")
        print("\nMake sure you're using the User OAuth Token, not Bot Token")

    print(f"✓ Token found: {token[:15]}...")
    print()

    # Test connection
    print("Testing Slack API connection...")
    slack = SlackClient()

    if not slack.test_connection():
        return False

    print()

    # List conversations
    print("Fetching conversations...")
    conversations = slack.get_all_conversations()

    # Categorize conversations
    public_channels = [c for c in conversations if c.get("is_channel") and not c.get("is_private")]
    private_channels = [c for c in conversations if c.get("is_private") or c.get("is_group")]
    dms = [c for c in conversations if c.get("is_im")]
    group_dms = [c for c in conversations if c.get("is_mpim")]

    print(f"\nConversation breakdown:")
    print(f"  Public channels:  {len(public_channels)}")
    print(f"  Private channels: {len(private_channels)}")
    print(f"  DMs:              {len(dms)}")
    print(f"  Group DMs:        {len(group_dms)}")
    print(f"  Total:            {len(conversations)}")

    # Show some examples
    print("\nSample conversations:")
    for conv in conversations[:5]:
        name = slack._get_conversation_name(conv)
        print(f"  - {name}")

    if len(conversations) > 5:
        print(f"  ... and {len(conversations) - 5} more")

    print()

    # Test fetching messages
    print("Testing message retrieval (last 1 day)...")
    content = slack.get_slack_content(days=1)

    if content:
        print(f"✓ Retrieved messages from {len(content)} active conversations")

        # Show sample
        print("\nSample output (first conversation):")
        print("-" * 40)
        sample = content[0][:500] + "..." if len(content[0]) > 500 else content[0]
        print(sample)
        print("-" * 40)
    else:
        print("⚠ No messages found in the last day")
        print("  This might be normal if there was no activity")

    print()
    print("=" * 60)
    print("✓ Slack connection test complete!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
