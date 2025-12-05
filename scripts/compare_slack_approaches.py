#!/usr/bin/env python3
"""Compare Slack channel discovery approaches.

Approach 1 (Current): Iterate all conversations, check history for each
Approach 2 (Search): Use search API with from:@me to find active channels
"""

import os
import sys
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
load_dotenv()

from mcp_clients.slack_client import SlackClient


def approach_1_iterate_channels(client: SlackClient, days: int = 1) -> dict:
    """Current approach: iterate all channels and check history."""
    print("\n=== APPROACH 1: Iterate All Channels ===")
    start = time.time()

    # Get all conversations
    conversations = client.get_all_conversations()
    print(f"Found {len(conversations)} total conversations")

    my_user_id = client._get_my_user_id()
    active_channels = []
    channels_checked = 0

    for conv in conversations:
        # Skip DMs
        if conv.get("is_im") or conv.get("is_mpim"):
            continue
        if conv.get("is_archived"):
            continue
        if not conv.get("is_member", False):
            continue

        channel_id = conv.get("id")
        channel_name = conv.get("name", channel_id)
        channels_checked += 1

        # Check if user posted recently
        if client._user_posted_recently(channel_id, days, my_user_id):
            active_channels.append({
                "id": channel_id,
                "name": channel_name,
            })
            print(f"  ✓ Active in: #{channel_name}")

    elapsed = time.time() - start
    print(f"\nApproach 1 Results:")
    print(f"  Channels checked: {channels_checked}")
    print(f"  Active channels: {len(active_channels)}")
    print(f"  Time: {elapsed:.1f}s")

    return {
        "channels": active_channels,
        "count": len(active_channels),
        "time": elapsed,
        "api_calls": channels_checked + 1,  # +1 for conversations.list
    }


def approach_2_search_api(client: SlackClient, days: int = 1) -> dict:
    """New approach: use search API to find channels with user's messages."""
    print("\n=== APPROACH 2: Search API ===")
    start = time.time()

    # Build date filter - use days+1 because 'after:' is exclusive
    date_str = (datetime.now() - timedelta(days=days + 1)).strftime("%Y-%m-%d")

    # Search for user's messages in channels (not DMs)
    # from:me finds messages from the authenticated user
    query = f"from:me after:{date_str}"
    print(f"Search query: {query}")

    try:
        # Paginate through all search results
        all_messages = []
        page = 1
        while True:
            params = {
                "query": query,
                "sort": "timestamp",
                "sort_dir": "desc",
                "count": 100,
                "page": page,
            }
            data = client._make_request("search.messages", params)
            messages = data.get("messages", {}).get("matches", [])
            total = data.get("messages", {}).get("total", 0)

            if not messages:
                break

            all_messages.extend(messages)
            print(f"  Page {page}: {len(messages)} messages (total: {total})")

            if len(all_messages) >= total:
                break
            page += 1

        messages = all_messages
        print(f"Search returned {len(messages)} total messages")

        # Extract unique channels
        channels_by_id = {}
        for msg in messages:
            channel = msg.get("channel", {})
            channel_id = channel.get("id", "")
            channel_name = channel.get("name", "")

            # Skip DMs (channel names starting with D or no name)
            if channel_id.startswith("D") or not channel_name:
                continue

            if channel_id not in channels_by_id:
                channels_by_id[channel_id] = {
                    "id": channel_id,
                    "name": channel_name,
                }
                print(f"  ✓ Found activity in: #{channel_name}")

        active_channels = list(channels_by_id.values())

    except Exception as e:
        print(f"Search failed: {e}")
        active_channels = []

    elapsed = time.time() - start
    print(f"\nApproach 2 Results:")
    print(f"  Active channels: {len(active_channels)}")
    print(f"  Time: {elapsed:.1f}s")

    return {
        "channels": active_channels,
        "count": len(active_channels),
        "time": elapsed,
        "api_calls": 1,  # Just the search call
    }


def compare_results(result1: dict, result2: dict):
    """Compare the two approaches."""
    print("\n" + "=" * 50)
    print("COMPARISON")
    print("=" * 50)

    channels1 = {c["id"]: c["name"] for c in result1["channels"]}
    channels2 = {c["id"]: c["name"] for c in result2["channels"]}

    # Find differences
    only_in_1 = set(channels1.keys()) - set(channels2.keys())
    only_in_2 = set(channels2.keys()) - set(channels1.keys())
    in_both = set(channels1.keys()) & set(channels2.keys())

    print(f"\nChannels found by BOTH approaches ({len(in_both)}):")
    for ch_id in sorted(in_both):
        print(f"  #{channels1[ch_id]}")

    if only_in_1:
        print(f"\nChannels ONLY in Approach 1 - iterate ({len(only_in_1)}):")
        for ch_id in sorted(only_in_1):
            print(f"  #{channels1[ch_id]} ← MISSING from search!")

    if only_in_2:
        print(f"\nChannels ONLY in Approach 2 - search ({len(only_in_2)}):")
        for ch_id in sorted(only_in_2):
            print(f"  #{channels2[ch_id]}")

    print(f"\n{'Metric':<25} {'Approach 1':>15} {'Approach 2':>15}")
    print("-" * 55)
    print(f"{'Active channels':<25} {result1['count']:>15} {result2['count']:>15}")
    print(f"{'API calls':<25} {result1['api_calls']:>15} {result2['api_calls']:>15}")
    print(f"{'Time (seconds)':<25} {result1['time']:>15.1f} {result2['time']:>15.1f}")

    if result1['time'] > 0:
        speedup = result1['time'] / result2['time'] if result2['time'] > 0 else float('inf')
        print(f"{'Speedup':<25} {'-':>15} {speedup:>14.1f}x")


def main():
    token = os.environ.get("SLACK_USER_TOKEN")
    if not token:
        print("Error: SLACK_USER_TOKEN not set in environment")
        sys.exit(1)

    client = SlackClient(token=token)
    days = 1

    print(f"Comparing Slack channel discovery approaches (last {days} day(s))")
    print("=" * 50)

    # Run approach 2 first (faster)
    result2 = approach_2_search_api(client, days)

    # Run approach 1 (slower)
    result1 = approach_1_iterate_channels(client, days)

    # Compare
    compare_results(result1, result2)


if __name__ == "__main__":
    main()
