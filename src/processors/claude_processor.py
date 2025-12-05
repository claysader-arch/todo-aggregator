"""Claude AI processor for todo extraction and analysis."""

import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any
from anthropic import Anthropic
from config import Config

logger = logging.getLogger(__name__)


class ClaudeProcessor:
    """Processor using Claude AI for todo extraction, deduplication, and analysis."""

    def __init__(self):
        """Initialize Claude client."""
        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.model = "claude-opus-4-20250514"  # Using Opus 4.5

    def extract_todos(
        self,
        raw_data: Dict[str, List[Any]],
        context: str = "",
        user_name: str = None,
        user_email: str = None,
        user_slack_username: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract structured todos from raw text content using Claude.

        Args:
            raw_data: Dictionary with platform names as keys and list of content as values.
                      Content can be either strings (legacy) or dicts with text/source_url/source/metadata.
            context: Optional additional context
            user_name: Override user name (defaults to Config.MY_NAME)
            user_email: Override user email (defaults to Config.MY_EMAIL)
            user_slack_username: Override Slack username (defaults to Config.MY_SLACK_USERNAME)

        Returns:
            List of extracted todo objects with source_url populated
        """
        logger.info("Extracting todos using Claude AI...")

        # Prepare the content for Claude while preserving source metadata
        content_parts = []
        source_metadata = []  # Track source URLs and metadata for direct lookup by source_id
        source_id_counter = 0

        for platform, items in raw_data.items():
            if not items:
                continue

            content_parts.append(f"=== {platform.upper()} ===")

            for item in items:
                if isinstance(item, dict):
                    # New structured format: {"text": str, "source_url": str, "source": str, "metadata": dict}
                    text = item.get("text", "")
                    if text:
                        # Add source ID marker so Claude can reference it
                        content_parts.append(f"[SOURCE:{source_id_counter}]\n{text}")
                        # Track metadata for direct URL lookup by source_id
                        # Include message_ts for age filtering
                        metadata = item.get("metadata", {})
                        source_metadata.append({
                            "source_id": source_id_counter,
                            "source_url": item.get("source_url"),
                            "source": item.get("source", platform),
                            "message_ts": metadata.get("message_ts"),
                        })
                        source_id_counter += 1
                else:
                    # Legacy string format (no source tracking)
                    content_parts.append(item)

            content_parts.append("")

        if len(content_parts) <= 1:  # Only has empty separator
            logger.info("No content to process")
            return []

        content = "\n".join(content_parts)

        # Build feature-specific instructions based on config
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')
        day_name = today.strftime('%A')

        priority_instructions = ""
        if Config.ENABLE_PRIORITY_SCORING:
            high_keywords = Config.HIGH_PRIORITY_KEYWORDS
            priority_instructions = f"""
- priority: Assess urgency level:
  - "high": Contains urgency signals ({high_keywords}), due within 48 hours, or from executives/managers
  - "medium": Moderate urgency, due within a week, normal requests
  - "low": No urgency signals, flexible timeline, nice-to-have"""

        category_instructions = ""
        if Config.ENABLE_CATEGORY_TAGGING:
            category_instructions = """
- category: Array of applicable tags (can have multiple):
  - "follow-up": Waiting on someone else, need to check in
  - "review": Documents, PRs, designs to review/approve
  - "meeting": Schedule or attend meetings/calls
  - "finance": Budget, invoices, expenses, payments
  - "hr": Hiring, onboarding, team management
  - "technical": Code, bugs, infrastructure, deployments
  - "communication": Emails, messages, calls to make"""

        date_instructions = """- due_date: YYYY-MM-DD format or null"""
        if Config.ENABLE_DUE_DATE_INFERENCE:
            date_instructions = f"""- due_date: Extract or infer date in YYYY-MM-DD format:
  - "today" → {today_str}
  - "tomorrow" → calculate next day
  - "by end of week" → Friday of current week
  - "next Monday" → calculate specific date
  - "within 2 days" → calculate date
  - If no date mentioned, use null
  (Today is {today_str}, {day_name})"""

        # Get user identity info for contextualized extraction
        # Use parameters if provided, otherwise fall back to Config
        config_name = Config.MY_NAME.split(",")[0].strip() if Config.MY_NAME else "the user"
        primary_name = user_name or config_name
        user_variations = user_name or Config.MY_NAME or primary_name
        slack_username = user_slack_username or Config.MY_SLACK_USERNAME or primary_name
        email_addr = user_email or Config.MY_EMAIL or ""

        # Build identity section
        identity_info = f"- Name variations: {user_variations}"
        if slack_username:
            identity_info += f"\n- Slack username: @{slack_username} (messages from this user are {primary_name}'s own words)"
        if email_addr:
            identity_info += f"\n- Email: {email_addr}"

        prompt = f"""You are extracting todos specifically for {primary_name}.

## User Identity
{identity_info}

## Message Format
- **Slack**: "[timestamp] @Username: message" - the @Username shows WHO sent each message
- **Gmail**: "=== Gmail: Subject (from: Sender) ===" - shows the sender; greeting often shows recipient
- **Zoom**: Meeting summaries with action items

## Your Task

Analyze each conversation or email thread as a whole. Consider the full context - who is talking to whom, what commitments are being made, and who is responsible for what.

**Only return a todo if {primary_name} is clearly the intended owner**, either because:
- {primary_name} agreed to do something (look for messages FROM @{slack_username})
- {primary_name} was clearly the recipient of a request or assignment, based on context
- An email or message is directly addressed to {primary_name} with an actionable ask

**Do not extract todos that belong to other people.** If two other people are discussing tasks between themselves, those are not {primary_name}'s todos - even if {primary_name} is CC'd or in the same channel/group chat.

**User must be PART of the conversation.** Only extract todos from conversations where {primary_name} is actually involved:
- {primary_name} sent a message in the conversation (look for @{slack_username} as the sender)
- {primary_name} was directly @-mentioned or addressed by name
- It's a DM or email where {primary_name} is a direct participant
- The message explicitly addresses {primary_name} (e.g., "Hey {primary_name},", "@{slack_username}")
If a conversation is between other people and {primary_name} is just observing the channel, do NOT extract todos from it.

**Outbound requests are NOT the user's todos.** When {primary_name} ASKS someone else to do something (especially in DMs), the task belongs to the OTHER person, not {primary_name}. Look for patterns like:
- "Could you...", "Can you...", "Would you mind..."
- "Please send me...", "I need you to..."
- Direct imperatives addressed to the conversation partner
In a "DM with [Name]", if @{slack_username} is the one asking/requesting, the todo belongs to [Name], NOT to {primary_name}.

**Delegation removes ownership.** If {primary_name} asks someone for help and they agree (or even if they haven't responded yet), the task belongs to that person, not {primary_name}.

**Do NOT create todos for:**
- Calendar invites or meeting requests - these are already on the calendar
- "Attend [meeting name]" - attending a scheduled meeting is not a todo
- Requests that were already resolved within the same conversation thread (look for back-and-forth that concludes the matter)
- Old requests in threads - if a request was made several days ago and there's been subsequent conversation, assume it's handled unless explicitly still pending
- Automated system notifications from noreply@, notifications@, no-reply@, or bulk mailing systems
- Low-value transactional emails (expense report reminders, lunch order confirmations, subscription renewals) unless genuinely urgent

**Look at conversation flow:** If someone requests information and later says "thank you", "I appreciate you", or similar - the request was likely fulfilled. Don't extract resolved requests as new todos.

**Prioritize personal over automated:** Distinguish between personal requests from colleagues (high value) and automated system notifications (low value). Focus on direct asks from real people, not system-generated reminders.

Set the **confidence** field to reflect how certain you are that this todo belongs to {primary_name} (0.0 to 1.0).

For each todo, determine:
- task: Clear, concise description
- assigned_to: Person's name or null if unspecified
{date_instructions}
{priority_instructions}
{category_instructions}
- source: Platform name (slack, gmail, zoom, notion)
- source_id: The [SOURCE:N] number from the content where this todo was found (e.g., if found in [SOURCE:5], return 5)
- source_context: Brief context from original message
- confidence: Your certainty level (0.0 to 1.0)
- type: "explicit" (direct request) or "implicit" (self-commitment)

{f"Additional context: {context}" if context else ""}

Content to analyze:
{content}

Return a JSON array of todos with this structure:
[
  {{
    "task": "Clear description of the todo",
    "assigned_to": "Person's name or null",
    "due_date": "YYYY-MM-DD or null",
    "priority": "high",
    "category": ["follow-up", "technical"],
    "source": "platform name",
    "source_id": 5,
    "source_context": "Brief context from original message",
    "confidence": 0.85,
    "type": "explicit"
  }}
]

Only return the JSON array, no additional text."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse the response
            response_text = response.content[0].text.strip()
            logger.debug(f"Raw Claude response (first 500 chars): {response_text[:500]}")

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                # Find the end of the code block
                end_idx = response_text.rfind("```")
                if end_idx > 3:  # Has closing ```
                    response_text = response_text[3:end_idx]
                    # Remove language identifier if present (e.g., "json")
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                    response_text = response_text.strip()

            # Try to extract just the JSON array
            start_idx = response_text.find("[")
            end_idx = response_text.rfind("]")
            if start_idx != -1 and end_idx != -1:
                response_text = response_text[start_idx:end_idx + 1]

            todos = json.loads(response_text)

            # Normalize todos to ensure consistent structure
            todos = [self._normalize_todo(todo) for todo in todos]

            # Map source URLs to todos based on source and source_context matching
            if source_metadata:
                todos = self._map_source_urls(todos, source_metadata)
                # Filter out todos from messages older than 7 days
                todos = self._filter_by_age(todos, source_metadata, max_days=7)

            logger.info(f"Extracted {len(todos)} todos from content")
            return todos

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.error(f"Response text (first 1000 chars): {response_text[:1000] if response_text else '(empty)'}")
            return []
        except Exception as e:
            logger.error(f"Error extracting todos with Claude: {e}")
            raise

    def deduplicate_todos(
        self, new_todos: List[Dict[str, Any]], existing_todos: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Use Claude to semantically deduplicate todos across sources.

        Args:
            new_todos: Newly extracted todos
            existing_todos: Existing todos from Notion

        Returns:
            Deduplicated list with merge information
        """
        logger.info(f"Deduplicating {len(new_todos)} new todos against {len(existing_todos)} existing...")

        if not new_todos:
            return []

        # If no existing todos, just add hashes to new ones
        if not existing_todos:
            return [self._add_dedupe_hash(todo) for todo in new_todos]

        # Create simplified representations for Claude
        new_todos_summary = [
            {"id": i, "task": todo.get("task", ""), "assigned_to": todo.get("assigned_to")}
            for i, todo in enumerate(new_todos)
        ]

        existing_todos_summary = [
            {
                "id": todo.get("id"),
                "task": todo.get("task", ""),
                "sources": todo.get("source", []),
            }
            for todo in existing_todos
        ]

        prompt = f"""You are analyzing todo items to identify duplicates based on semantic similarity.

Compare these new todos against existing todos and identify which ones are duplicates.

New todos:
{json.dumps(new_todos_summary, indent=2)}

Existing todos:
{json.dumps(existing_todos_summary, indent=2)}

For each new todo, determine if it matches any existing todo. Todos are duplicates if they represent the same task, even if worded differently.

Return a JSON array with this structure:
[
  {{
    "new_todo_id": 0,
    "is_duplicate": true,
    "existing_todo_id": "notion-page-id",
    "confidence": 0.9,
    "reasoning": "Brief explanation"
  }}
]

Only return the JSON array, no additional text."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])

            matches = json.loads(response_text)

            # Build result list
            result = []
            for match in matches:
                new_id = match["new_todo_id"]
                todo = new_todos[new_id].copy()

                if match["is_duplicate"]:
                    # Mark as update to existing todo
                    todo["_update_id"] = match["existing_todo_id"]
                    todo["_merge_confidence"] = match["confidence"]
                    logger.info(f"Duplicate found: '{todo['task']}' matches existing todo")
                else:
                    # New unique todo
                    todo = self._add_dedupe_hash(todo)

                result.append(todo)

            logger.info(f"Deduplication complete: {len([t for t in result if '_update_id' not in t])} new, {len([t for t in result if '_update_id' in t])} duplicates")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude deduplication response: {e}")
            # Fallback: treat all as new todos
            return [self._add_dedupe_hash(todo) for todo in new_todos]
        except Exception as e:
            logger.error(f"Error during deduplication with Claude: {e}")
            raise

    def detect_completions(
        self, open_todos: List[Dict[str, Any]], recent_content: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect which open todos have been completed based on recent messages.

        Args:
            open_todos: List of currently open todos
            recent_content: Recent messages/content from all platforms (strings or structured dicts)

        Returns:
            List of todos with updated completion status
        """
        logger.info(f"Checking {len(open_todos)} open todos for completion signals...")

        if not open_todos or not recent_content:
            return []

        # Prepare content (handle both string and structured dict formats)
        content_parts = []
        for platform, items in recent_content.items():
            if items:
                content_parts.append(f"=== {platform.upper()} ===")
                for item in items:
                    if isinstance(item, dict):
                        # New structured format
                        text = item.get("text", "")
                        if text:
                            content_parts.append(text)
                    else:
                        # Legacy string format
                        content_parts.append(item)
                content_parts.append("")

        content = "\n".join(content_parts)

        todos_summary = [
            {"id": todo.get("id"), "task": todo.get("task", "")} for todo in open_todos
        ]

        prompt = f"""You are analyzing recent messages to detect if any open todos have been ACTUALLY completed.

**BE CONSERVATIVE.** Only mark a todo as completed if you see clear evidence that the deliverable was sent, finished, or received.

Valid completion signals:
- The todo owner saying they DID the action: "I sent it", "Done!", "Just finished", "Attached"
- Recipient confirming RECEIPT of deliverable: "Got it, thanks!", "Received the document"
- Explicit status: "Done", "Completed", "Finished"

**NOT valid completion signals:**
- Acknowledging a commitment or timeline: "Thank you for the update", "Sounds good"
- Future tense: "I'll send it tomorrow", "Will do"
- Someone else doing a related but different task
- General thank-yous that don't confirm receipt of the specific deliverable

Open todos:
{json.dumps(todos_summary, indent=2)}

Recent content:
{content}

For each todo that shows CLEAR evidence of completion, identify it. When in doubt, do NOT mark as completed.

Return a JSON array with this structure:
[
  {{
    "todo_id": "notion-page-id",
    "is_completed": true,
    "confidence": 0.9,
    "evidence": "Quote from content showing completion"
  }}
]

Only return the JSON array, no additional text. Return an empty array if no completions detected."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])

            completions = json.loads(response_text)

            completed_ids = {c["todo_id"] for c in completions if c.get("is_completed")}

            logger.info(f"Detected {len(completed_ids)} completed todos")
            return [c for c in completions if c.get("is_completed")]

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude completion detection response: {e}")
            return []
        except Exception as e:
            logger.error(f"Error detecting completions with Claude: {e}")
            raise

    def generate_summary(self, todos: List[Dict[str, Any]], stats: Dict[str, Any]) -> str:
        """
        Generate a daily summary of todo activity.

        Args:
            todos: Current todo list
            stats: Statistics about todo activity

        Returns:
            Formatted markdown summary
        """
        logger.info("Generating daily summary with Claude...")

        prompt = f"""Generate a concise daily summary of todo activity.

Statistics:
- New todos added: {stats.get('new_todos', 0)}
- Todos completed: {stats.get('completed_todos', 0)}
- Total open todos: {stats.get('open_todos', 0)}
- Overdue todos: {stats.get('overdue_todos', 0)}

Current open todos:
{json.dumps([{'task': t.get('task'), 'due_date': t.get('due_date'), 'source': t.get('source')} for t in todos[:20]], indent=2)}

Create a brief, actionable summary in markdown format with:
1. Key highlights (new, completed, overdue)
2. Top priority items
3. Any patterns or insights

Keep it concise (3-5 sentences max)."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )

            summary = response.content[0].text.strip()
            logger.info("Summary generated successfully")
            return summary

        except Exception as e:
            logger.error(f"Error generating summary with Claude: {e}")
            return "Error generating summary"

    def _normalize_todo(self, todo: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize and validate extracted todo fields.

        Args:
            todo: Raw extracted todo

        Returns:
            Normalized todo with validated fields
        """
        # Ensure priority is valid
        valid_priorities = {"high", "medium", "low"}
        priority = todo.get("priority", "medium")
        if priority and isinstance(priority, str):
            priority = priority.lower()
        if priority not in valid_priorities:
            priority = "medium"
        todo["priority"] = priority

        # Ensure category is a list of valid values
        category = todo.get("category", [])
        if isinstance(category, str):
            category = [category] if category else []
        valid_categories = {"follow-up", "review", "meeting", "finance", "hr", "technical", "communication"}
        category = [c.lower() for c in category if isinstance(c, str) and c.lower() in valid_categories]
        todo["category"] = category

        # Validate due_date format (YYYY-MM-DD)
        due_date = todo.get("due_date")
        if due_date:
            try:
                datetime.strptime(due_date, "%Y-%m-%d")
            except (ValueError, TypeError):
                todo["due_date"] = None

        return todo

    def _add_dedupe_hash(self, todo: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a deduplication hash to a todo item.

        Args:
            todo: Todo dictionary

        Returns:
            Todo with dedupe_hash added
        """
        # Create hash from task description and assigned_to
        task = (todo.get('task') or '').lower()
        assigned_to = (todo.get('assigned_to') or '').lower()
        hash_input = f"{task}|{assigned_to}"
        dedupe_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        todo["dedupe_hash"] = dedupe_hash
        return todo

    def _map_source_urls(self, todos: List[Dict[str, Any]], source_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Map source URLs to extracted todos using source_id from Claude's response.

        Args:
            todos: List of extracted todos from Claude (with source_id field)
            source_metadata: List of source metadata with URLs indexed by source_id

        Returns:
            Todos with source_url populated where source_id matches
        """
        # Build lookup map: source_id -> metadata
        source_map = {m["source_id"]: m for m in source_metadata}

        mapped_count = 0
        for todo in todos:
            source_id = todo.get("source_id")
            if source_id is not None and source_id in source_map:
                source_url = source_map[source_id].get("source_url")
                if source_url:
                    todo["source_url"] = source_url
                    mapped_count += 1
                    logger.debug(f"Mapped URL to todo (source_id={source_id}): {source_url}")
            else:
                # No source_id or not found - leave source_url empty (don't guess)
                logger.debug(f"No source_id match for todo: '{todo.get('task', '')[:50]}'")

        logger.info(f"Mapped URLs to {mapped_count}/{len(todos)} todos using source_id")
        return todos

    def _filter_by_age(self, todos: List[Dict[str, Any]], source_metadata: List[Dict[str, Any]], max_days: int = 7) -> List[Dict[str, Any]]:
        """
        Filter out todos from messages older than max_days.

        This prevents stale todos from being extracted when old messages
        are included for thread context.

        Args:
            todos: List of extracted todos with source_id
            source_metadata: List of source metadata with message_ts
            max_days: Maximum age in days for a source message (default 7)

        Returns:
            Filtered list of todos from recent messages only
        """
        if max_days <= 0:
            return todos

        # Build lookup map: source_id -> message_ts
        source_map = {m["source_id"]: m.get("message_ts") for m in source_metadata}

        cutoff_ts = (datetime.now() - timedelta(days=max_days)).timestamp()
        filtered = []
        filtered_out = 0

        for todo in todos:
            source_id = todo.get("source_id")
            if source_id is None or source_id not in source_map:
                # No source tracking - keep the todo
                filtered.append(todo)
                continue

            message_ts = source_map.get(source_id)
            if message_ts is None:
                # No timestamp - keep the todo
                filtered.append(todo)
                continue

            try:
                ts_float = float(message_ts)
                if ts_float >= cutoff_ts:
                    filtered.append(todo)
                else:
                    filtered_out += 1
                    age_days = (datetime.now().timestamp() - ts_float) / 86400
                    logger.debug(f"Filtered out stale todo ({age_days:.0f} days old): '{todo.get('task', '')[:50]}'")
            except (ValueError, TypeError):
                # Can't parse timestamp - keep the todo
                filtered.append(todo)

        if filtered_out > 0:
            logger.info(f"Filtered out {filtered_out} stale todos (older than {max_days} days)")

        return filtered
