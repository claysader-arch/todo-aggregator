"""Slack API client for fetching conversation messages."""

import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from config import Config

logger = logging.getLogger(__name__)


class SlackClient:
    """Client for interacting with Slack API to fetch conversation messages."""

    def __init__(self, token: Optional[str] = None):
        """Initialize Slack client with User OAuth token.

        Args:
            token: Optional Slack User OAuth Token (xoxp-...).
                   Falls back to Config.SLACK_USER_TOKEN if not provided.
        """
        self.user_token = token or Config.SLACK_USER_TOKEN
        self.base_url = "https://slack.com/api"
        self.user_cache: Dict[str, str] = {}  # Cache user ID -> display name
        self._workspace_name: Optional[str] = None  # Cache workspace name
        self._my_user_id: Optional[str] = None  # Cache authenticated user's ID

    def _get_my_user_id(self) -> str:
        """
        Get the authenticated user's Slack ID (cached).

        Returns:
            The user ID of the authenticated user
        """
        if self._my_user_id:
            return self._my_user_id

        try:
            data = self._make_request("auth.test")
            self._my_user_id = data.get("user_id")
            logger.debug(f"Authenticated Slack user ID: {self._my_user_id}")
            return self._my_user_id
        except Exception as e:
            logger.warning(f"Could not get authenticated user ID: {e}")
            return None

    def get_workspace_name(self) -> str:
        """
        Get workspace name from Slack API (cached).

        Returns:
            Workspace name for building message URLs
        """
        if self._workspace_name:
            return self._workspace_name

        try:
            data = self._make_request("auth.test")
            # Use team_domain (URL-safe slug) instead of team (display name with spaces)
            team_domain = data.get("team_domain")
            team_name = data.get("team", "workspace")
            logger.debug(f"Slack auth.test response: team_domain={team_domain}, team={team_name}")
            # Fallback: remove spaces (don't add hyphens) and lowercase
            self._workspace_name = team_domain or team_name.replace(" ", "").lower()
            logger.info(f"Using Slack workspace domain: {self._workspace_name}")
            return self._workspace_name
        except Exception as e:
            logger.debug(f"Could not get workspace name: {e}")
            return "workspace"

    def _build_message_url(self, channel_id: str, ts: str) -> str:
        """
        Build permalink to Slack message.

        Args:
            channel_id: Slack channel ID
            ts: Message timestamp

        Returns:
            URL to the message in Slack
        """
        workspace = self.get_workspace_name()
        ts_no_dot = ts.replace(".", "")
        return f"https://{workspace}.slack.com/archives/{channel_id}/p{ts_no_dot}"

    def _make_request(
        self, method: str, params: Optional[Dict] = None, retries: int = 3
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Slack API with rate limiting and retries.

        Args:
            method: API method name (e.g., 'conversations.list')
            params: Optional parameters for the request
            retries: Number of retries for rate-limited requests

        Returns:
            Response JSON data

        Raises:
            Exception if request fails or Slack returns an error
        """
        url = f"{self.base_url}/{method}"
        headers = {
            "Authorization": f"Bearer {self.user_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        for attempt in range(retries + 1):
            try:
                response = requests.get(url, headers=headers, params=params)

                # Handle rate limiting with exponential backoff
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2))
                    if attempt < retries:
                        sleep_time = min(retry_after, 5) * (attempt + 1)
                        logger.debug(f"Rate limited on {method}, sleeping {sleep_time}s (attempt {attempt + 1})")
                        time.sleep(sleep_time)
                        continue
                    else:
                        logger.warning(f"Rate limited on {method} after {retries} retries")
                        raise Exception(f"Rate limited: {method}")

                response.raise_for_status()
                data = response.json()

                if not data.get("ok", False):
                    error = data.get("error", "Unknown error")
                    # Handle rate_limited error in response body
                    if error == "ratelimited":
                        if attempt < retries:
                            sleep_time = 2 * (attempt + 1)
                            logger.debug(f"Rate limited (body) on {method}, sleeping {sleep_time}s")
                            time.sleep(sleep_time)
                            continue
                    logger.error(f"Slack API error for {method}: {error}")
                    raise Exception(f"Slack API error: {error}")

                # Small delay between successful requests to avoid hitting limits
                time.sleep(0.1)
                return data

            except requests.exceptions.RequestException as e:
                if attempt < retries and "429" in str(e):
                    time.sleep(2 * (attempt + 1))
                    continue
                logger.error(f"Error making Slack API request to {method}: {e}")
                raise

        raise Exception(f"Max retries exceeded for {method}")

    def _get_user_name(self, user_id: str) -> str:
        """
        Get display name for a user ID, using cache.

        Args:
            user_id: Slack user ID

        Returns:
            User's display name or real name, or user_id if lookup fails
        """
        if user_id in self.user_cache:
            return self.user_cache[user_id]

        try:
            data = self._make_request("users.info", {"user": user_id})
            user = data.get("user", {})
            # Prefer display_name, fall back to real_name, then name
            name = (
                user.get("profile", {}).get("display_name")
                or user.get("real_name")
                or user.get("name")
                or user_id
            )
            self.user_cache[user_id] = name
            return name
        except Exception as e:
            logger.debug(f"Could not get user info for {user_id}: {e}")
            self.user_cache[user_id] = user_id
            return user_id

    def _get_conversation_name(self, conversation: Dict) -> str:
        """
        Get a readable name for a conversation.

        Args:
            conversation: Conversation object from Slack API

        Returns:
            Human-readable conversation name
        """
        # For channels, use the name
        if conversation.get("is_channel") or conversation.get("is_group"):
            return f"#{conversation.get('name', 'unknown')}"

        # For private channels (groups)
        if conversation.get("is_private"):
            return f"#{conversation.get('name', 'private-channel')}"

        # For DMs, get the other user's name
        if conversation.get("is_im"):
            user_id = conversation.get("user")
            if user_id:
                user_name = self._get_user_name(user_id)
                return f"DM with {user_name}"
            return "DM"

        # For group DMs (mpim)
        if conversation.get("is_mpim"):
            return conversation.get("name", "Group DM")

        return conversation.get("name", "unknown")

    def _get_thread_replies(
        self, channel_id: str, thread_ts: str, days: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Fetch all replies in a thread.

        Args:
            channel_id: Slack channel ID
            thread_ts: Thread parent timestamp
            days: Number of days to look back (for filtering)

        Returns:
            List of message objects from the thread
        """
        try:
            oldest = (datetime.now() - timedelta(days=days)).timestamp()
            params = {
                "channel": channel_id,
                "ts": thread_ts,
                "limit": 100,
                "oldest": str(oldest),
            }
            data = self._make_request("conversations.replies", params)
            replies = data.get("messages", [])
            # Filter same as main messages (exclude bot messages and system messages)
            return [
                m for m in replies
                if m.get("type") == "message"
                and not m.get("subtype")
                and not m.get("bot_id")
            ]
        except Exception as e:
            logger.debug(f"Could not fetch thread replies for {thread_ts}: {e}")
            return []

    def get_all_conversations(self) -> List[Dict[str, Any]]:
        """
        Get all conversations the user has access to.

        Returns:
            List of conversation objects (public, private, DMs, group DMs)
        """
        conversations = []
        cursor = None

        # Fetch all conversation types
        types = "public_channel,private_channel,mpim,im"

        while True:
            params = {
                "types": types,
                "limit": 200,  # Max per page
                "exclude_archived": "true",
            }
            if cursor:
                params["cursor"] = cursor

            try:
                data = self._make_request("conversations.list", params)
                conversations.extend(data.get("channels", []))

                # Check for pagination
                cursor = data.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break

            except Exception as e:
                logger.error(f"Error fetching conversations: {e}")
                break

        logger.info(f"Found {len(conversations)} total conversations")
        return conversations

    def get_conversation_history(
        self, channel_id: str, days: int = 1, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get message history from a conversation, including thread replies.

        Args:
            channel_id: Slack conversation ID
            days: Number of days to look back
            limit: Maximum number of messages to retrieve

        Returns:
            List of message objects with recent activity
        """
        messages = []
        oldest_ts = (datetime.now() - timedelta(days=days)).timestamp()

        try:
            # Don't use 'oldest' filter here - we need to find thread parents
            # that may be older but have recent thread replies
            params = {
                "channel": channel_id,
                "limit": min(limit, 100),  # Slack max is 100 per request
            }

            data = self._make_request("conversations.history", params)
            messages = data.get("messages", [])

            # Filter out bot messages and system messages
            messages = [
                m for m in messages
                if m.get("type") == "message"
                and not m.get("subtype")  # Exclude join/leave/etc
                and not m.get("bot_id")  # Exclude bot messages
            ]

            # Fetch thread replies for messages that are thread parents
            # Use 'oldest' filter here to only get recent thread activity
            # Limit to 5 threads per channel to avoid rate limiting
            thread_messages = []
            threads_with_recent_activity = set()
            threads_fetched = 0
            max_threads_per_channel = 5

            for msg in messages:
                if threads_fetched >= max_threads_per_channel:
                    break
                reply_count = msg.get("reply_count", 0)
                if reply_count > 0:
                    thread_ts = msg.get("thread_ts") or msg.get("ts")
                    replies = self._get_thread_replies(channel_id, thread_ts, days=days)
                    threads_fetched += 1
                    if replies:
                        threads_with_recent_activity.add(thread_ts)
                        thread_messages.extend(replies)
                        logger.debug(f"Fetched {len(replies)} recent replies from thread {thread_ts}")

            # Combine and deduplicate (parent message may appear in both)
            if thread_messages:
                all_messages = messages + thread_messages
                seen_ts = set()
                deduplicated = []
                for msg in all_messages:
                    ts = msg.get("ts")
                    if ts not in seen_ts:
                        seen_ts.add(ts)
                        deduplicated.append(msg)
                messages = deduplicated

            # Now filter to only include:
            # 1. Messages newer than the cutoff, OR
            # 2. Thread parent messages that have recent thread activity
            filtered = []
            for msg in messages:
                ts = float(msg.get("ts", 0))
                thread_ts = msg.get("thread_ts") or msg.get("ts")

                if ts >= oldest_ts:
                    # Recent message
                    filtered.append(msg)
                elif thread_ts in threads_with_recent_activity:
                    # Old thread parent with recent replies - include for context
                    filtered.append(msg)

            messages = filtered
            if messages:
                logger.debug(f"After filtering: {len(messages)} messages with recent activity")

        except Exception as e:
            # Common error: not_in_channel for private channels we can't access
            error_str = str(e)
            if "not_in_channel" in error_str or "channel_not_found" in error_str:
                logger.debug(f"Cannot access channel {channel_id}: {e}")
            else:
                logger.error(f"Error fetching history for {channel_id}: {e}")

        return messages

    def get_slack_content(self, days: int = 1) -> List[Dict[str, Any]]:
        """
        Get formatted messages from all active conversations.

        This is the main method called by the orchestrator.

        Args:
            days: Number of days to look back

        Returns:
            List of structured content dicts with text, source_url, source, and metadata
        """
        logger.info(f"Fetching Slack messages from last {days} day(s)...")

        content = []
        conversations = self.get_all_conversations()

        # Note: We don't filter by 'updated' timestamp because Slack thread replies
        # don't always update the conversation's 'updated' field. Instead, we rely on:
        # 1. is_member filter to only scan channels user is in
        # 2. conversations.history with oldest parameter to get only recent messages
        # 3. Participation filter to skip channels where user hasn't participated
        logger.info(f"Scanning {len(conversations)} conversations for recent activity")

        for conv in conversations:
            channel_id = conv.get("id")
            conv_name = self._get_conversation_name(conv)

            # Skip archived conversations
            if conv.get("is_archived"):
                continue

            # Skip channels user hasn't joined (only scan conversations user is part of)
            if not conv.get("is_member", False):
                logger.debug(f"Skipping {conv_name} - user is not a member")
                continue

            # Get messages
            messages = self.get_conversation_history(channel_id, days=days)

            if not messages:
                continue

            # For channels (not DMs), skip if user hasn't participated (no messages from user)
            # This prevents extracting todos from conversations the user just observes
            # DMs (is_im/is_mpim) are always included since they're directed at the user
            is_dm = conv.get("is_im") or conv.get("is_mpim")
            if not is_dm:
                my_user_id = self._get_my_user_id()
                if my_user_id:
                    user_participated = any(msg.get("user") == my_user_id for msg in messages)
                    if not user_participated:
                        logger.debug(f"Skipping {conv_name} - user has no messages in this channel")
                        continue

            # Create one content entry per message (for accurate source URL mapping)
            message_count = 0
            for msg in reversed(messages):  # Oldest first for context
                ts = msg.get("ts", "0")
                ts_float = float(ts)
                timestamp = datetime.fromtimestamp(ts_float).strftime("%Y-%m-%d %H:%M")

                user_id = msg.get("user", "unknown")
                user_name = self._get_user_name(user_id)

                text = msg.get("text", "")
                if text:
                    formatted_msg = f"[{timestamp}] @{user_name}: {text}"
                    source_url = self._build_message_url(channel_id, ts)

                    content.append({
                        "text": f"=== Slack: {conv_name} ===\n{formatted_msg}",
                        "source_url": source_url,
                        "source": "slack",
                        "metadata": {
                            "channel_id": channel_id,
                            "channel_name": conv_name,
                            "message_ts": ts,
                        }
                    })
                    message_count += 1

            if message_count > 0:
                logger.debug(f"Collected {message_count} messages from {conv_name}")

        logger.info(f"Collected {len(content)} Slack messages for todo extraction")
        return content

    def test_connection(self) -> bool:
        """
        Test Slack API connection and credentials.

        Returns:
            True if connection successful
        """
        try:
            data = self._make_request("auth.test")
            user = data.get("user", "unknown")
            team = data.get("team", "unknown")
            logger.info(f"✓ Slack API connection successful (user: {user}, team: {team})")
            return True
        except Exception as e:
            logger.error(f"✗ Slack API connection failed: {e}")
            return False
