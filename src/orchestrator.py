"""Main orchestrator for todo aggregation system.

This script coordinates the collection, extraction, deduplication, and
storage of todos from multiple platforms.
"""

import logging
import sys
import time
from datetime import datetime
from contextlib import contextmanager
from config import Config
from mcp_clients.notion_client import NotionClient
from mcp_clients.zoom_client import ZoomClient
from mcp_clients.slack_client import SlackClient
from mcp_clients.gmail_client import GmailClient
from processors.claude_processor import ClaudeProcessor


# Set up logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"aggregator_{datetime.now().strftime('%Y%m%d')}.log"),
    ],
)

logger = logging.getLogger(__name__)


@contextmanager
def timed_phase(phase_name: str):
    """Context manager to time and log phase duration."""
    start = time.time()
    logger.info(f"Starting {phase_name}...")
    try:
        yield
    finally:
        duration = time.time() - start
        logger.info(f"Completed {phase_name} in {duration:.1f}s")


def validate_config() -> bool:
    """Validate that all required configuration is present."""
    missing = Config.validate()
    if missing:
        logger.error(f"Missing required configuration: {', '.join(missing)}")
        logger.error("Please set these environment variables or add them to .env file")
        return False
    return True


def collect_todos(zoom: ZoomClient = None, slack: SlackClient = None, gmail: GmailClient = None, notion: NotionClient = None) -> dict:
    """
    Collect todos from all sources.

    Args:
        zoom: Optional Zoom client instance
        slack: Optional Slack client instance
        gmail: Optional Gmail client instance
        notion: Optional Notion client instance (for meeting notes)

    Returns:
        Dictionary with raw content from each platform
    """
    raw_content = {
        "slack": [],
        "gmail": [],
        "zoom": [],
        "notion": [],
    }

    # Phase 2: Zoom integration
    if zoom:
        try:
            zoom_content = zoom.get_meeting_content(days=1)
            raw_content["zoom"] = zoom_content
            logger.info(f"Collected {len(zoom_content)} Zoom meeting summaries/transcripts")
        except Exception as e:
            logger.error(f"Error collecting Zoom content: {e}")

    # Phase 3: Slack integration
    if slack:
        try:
            slack_content = slack.get_slack_content(days=1)
            raw_content["slack"] = slack_content
            logger.info(f"Collected messages from {len(slack_content)} Slack conversations")
        except Exception as e:
            logger.error(f"Error collecting Slack content: {e}")

    # Phase 4: Gmail integration
    if gmail:
        try:
            gmail_content = gmail.get_gmail_content()
            raw_content["gmail"] = gmail_content
            logger.info(f"Collected {len(gmail_content)} Gmail messages")
        except Exception as e:
            logger.error(f"Error collecting Gmail content: {e}")

    # Phase 6: Notion AI meeting notes integration
    if notion and Config.NOTION_MEETINGS_DATABASE_ID:
        try:
            meeting_content = notion.get_recent_meetings(days=1)
            raw_content["notion"] = meeting_content
            logger.info(f"Collected {len(meeting_content)} Notion AI meeting notes")
        except Exception as e:
            logger.error(f"Error collecting Notion meeting notes: {e}")

    total_items = sum(len(v) for v in raw_content.values())
    logger.info(f"Collection complete. Found {total_items} items from sources")
    return raw_content


def extract_todos(raw_data: dict, claude: ClaudeProcessor) -> list:
    """
    Phase 2: Use Claude to extract structured todos from raw content.

    Args:
        raw_data: Raw content from each platform
        claude: Claude processor instance

    Returns:
        List of extracted todo objects
    """
    # Use Claude to extract todos from raw content
    extracted = claude.extract_todos(raw_data)

    logger.info(f"Extraction complete. Found {len(extracted)} todos")
    return extracted


def filter_my_todos(todos: list) -> list:
    """
    Filter todos to only include those assigned to the configured user.

    Args:
        todos: List of todos to filter

    Returns:
        Filtered list of todos assigned to user
    """
    if not Config.FILTER_MY_TODOS_ONLY:
        logger.info("Todo filtering disabled, keeping all todos")
        return todos

    if not Config.MY_NAME:
        logger.warning("FILTER_MY_TODOS_ONLY is enabled but MY_NAME not configured, keeping all todos")
        return todos

    # Parse name variations (comma-separated)
    my_names = [name.strip().lower() for name in Config.MY_NAME.split(",")]
    logger.info(f"Filtering todos for: {', '.join(my_names)}")

    filtered = []
    skipped_others = 0
    for todo in todos:
        assigned_to = (todo.get("assigned_to") or "").strip().lower()

        # Check if assigned to user (match any name variation)
        if any(name in assigned_to for name in my_names if name):
            filtered.append(todo)
        # Also keep unassigned todos (empty assigned_to)
        elif not assigned_to:
            filtered.append(todo)
        else:
            skipped_others += 1

    logger.info(f"Filtered {len(todos)} todos to {len(filtered)} assigned to you (skipped {skipped_others} assigned to others)")
    return filtered


def deduplicate_todos(extracted_todos: list, existing_todos: list, claude: ClaudeProcessor) -> list:
    """
    Phase 3: Use Claude to deduplicate todos across sources.

    Args:
        extracted_todos: Newly extracted todos
        existing_todos: Todos already in Notion DB
        claude: Claude processor instance

    Returns:
        Deduplicated list of todos
    """
    # Use Claude for semantic similarity matching
    deduplicated = claude.deduplicate_todos(extracted_todos, existing_todos)

    logger.info(f"Deduplication complete. {len(deduplicated)} unique todos")
    return deduplicated


def detect_completions(open_todos: list, raw_data: dict, claude: ClaudeProcessor) -> list:
    """
    Phase 4: Detect todos that have been completed across platforms.

    Args:
        open_todos: Current open todo list
        raw_data: Raw content to scan for completion signals
        claude: Claude processor instance

    Returns:
        List of completed todo IDs and evidence
    """
    # Use Claude to detect completion signals
    completions = claude.detect_completions(open_todos, raw_data)

    logger.info(f"Completion detection complete. Found {len(completions)} completed todos")
    return completions


def update_notion_db(todos: list, completions: list, notion: NotionClient) -> dict:
    """
    Phase 5: Write updated todos to Notion database.

    Args:
        todos: Final processed todo list (new and duplicates)
        completions: List of completed todo information
        notion: Notion client instance

    Returns:
        Stats about the update operation
    """
    logger.info("Updating Notion database...")

    stats = {"created": 0, "skipped": 0, "completed": 0}

    # Process new and duplicate todos
    for todo in todos:
        if "_update_id" in todo:
            # Duplicate detected - todo already exists in Notion, skip creation
            logger.debug(f"Skipping duplicate todo (already exists): {todo.get('task', '')[:50]}")
            stats["skipped"] += 1
        else:
            # This is a new todo - create it
            page_data = notion.create_page(
                {
                    "task": todo.get("task", ""),
                    "status": "Open",
                    "source": [todo.get("source", "unknown")],
                    "source_url": todo.get("source_url"),
                    "due_date": todo.get("due_date"),
                    "confidence": todo.get("confidence", 0.0),
                    "dedupe_hash": todo.get("dedupe_hash", ""),
                    # Phase 5: Intelligence layer fields
                    "priority": todo.get("priority", "medium"),
                    "category": todo.get("category", []),
                }
            )
            stats["created"] += 1

            # Add source context as comment for traceability
            source_context = todo.get("source_context")
            if source_context and page_data:
                page_id = page_data.get("id")
                if page_id:
                    source = todo.get("source", "unknown")
                    # Truncate very long contexts
                    context_text = source_context[:500] + "..." if len(source_context) > 500 else source_context
                    comment = f"📍 Source ({source}): {context_text}"
                    try:
                        notion.add_comment(page_id, comment)
                    except Exception as e:
                        logger.warning(f"Could not add context comment: {e}")

    # Process completions with confidence-based status
    for completion in completions:
        confidence = completion.get("confidence", 0)
        threshold = Config.COMPLETION_CONFIDENCE_THRESHOLD
        status = "Done" if confidence >= threshold else "Done?"
        evidence = completion.get("evidence", "")

        notion.update_page(
            completion["todo_id"],
            {"status": status, "completed": datetime.now().date().isoformat()},
        )
        stats["completed"] += 1

        # Add comment with completion evidence
        if status == "Done":
            comment = f"✓ Auto-completed ({confidence:.0%}): \"{evidence[:200]}\"" if evidence else f"✓ Auto-completed ({confidence:.0%})"
        else:
            comment = f"? Needs review ({confidence:.0%}): \"{evidence[:200]}\"" if evidence else f"? Needs review ({confidence:.0%})"
            logger.info(f"Low confidence completion ({confidence:.0%}): {completion.get('todo_id')} - {evidence[:50] if evidence else 'no evidence'}")

        notion.add_comment(completion["todo_id"], comment)

    logger.info(
        f"Notion update complete. Created: {stats['created']}, "
        f"Skipped duplicates: {stats['skipped']}, Completed: {stats['completed']}"
    )
    return stats


def generate_summary(open_todos: list, stats: dict, claude: ClaudeProcessor) -> str:
    """
    Phase 6: Generate daily summary using Claude.

    Args:
        open_todos: Current open todo list
        stats: Statistics from update operation
        claude: Claude processor instance

    Returns:
        Formatted summary text
    """
    logger.info("Generating daily summary...")

    # Add additional stats
    summary_stats = {
        **stats,
        "open_todos": len(open_todos),
        "overdue_todos": len([t for t in open_todos if t.get("due_date") and t["due_date"] < datetime.now().date().isoformat()]),
    }

    summary = claude.generate_summary(open_todos, summary_stats)

    logger.info("Summary generation complete")
    return summary


def main():
    """Main entry point for todo aggregator."""
    logger.info("=" * 80)
    logger.info("Todo Aggregator - Starting run")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 80)

    # Validate configuration
    if not validate_config():
        logger.error("Configuration validation failed. Exiting.")
        sys.exit(1)

    try:
        # Initialize clients
        notion = NotionClient()
        claude = ClaudeProcessor()

        # Initialize Zoom client if credentials are available
        zoom = None
        if Config.ZOOM_ACCOUNT_ID and Config.ZOOM_CLIENT_ID and Config.ZOOM_CLIENT_SECRET:
            logger.info("Initializing Zoom client...")
            zoom = ZoomClient()
        else:
            logger.info("Zoom credentials not configured, skipping Zoom integration")

        # Initialize Slack client if credentials are available
        slack = None
        if Config.SLACK_USER_TOKEN:
            logger.info("Initializing Slack client...")
            slack = SlackClient()
        else:
            logger.info("Slack credentials not configured, skipping Slack integration")

        # Initialize Gmail client if credentials are available
        gmail = None
        if Config.GMAIL_CLIENT_ID and Config.GMAIL_CLIENT_SECRET and Config.GMAIL_REFRESH_TOKEN:
            logger.info("Initializing Gmail client...")
            gmail = GmailClient()
        else:
            logger.info("Gmail credentials not configured, skipping Gmail integration")

        # Log Notion meetings database status
        if Config.NOTION_MEETINGS_DATABASE_ID:
            logger.info("Notion AI meeting notes database configured")
        else:
            logger.info("Notion meetings database not configured, skipping meeting notes collection")

        # Execute aggregation pipeline with timing
        run_start = time.time()

        with timed_phase("collection"):
            raw_data = collect_todos(zoom=zoom, slack=slack, gmail=gmail, notion=notion)

        with timed_phase("extraction"):
            extracted = extract_todos(raw_data, claude)
            filtered = filter_my_todos(extracted)

        with timed_phase("deduplication"):
            existing_todos = notion.get_all_todos()
            logger.info(f"Found {len(existing_todos)} existing todos in Notion")
            deduplicated = deduplicate_todos(filtered, existing_todos, claude)

        with timed_phase("completion detection"):
            open_todos = notion.get_open_todos()
            completions = detect_completions(open_todos, raw_data, claude)

        with timed_phase("Notion update"):
            stats = update_notion_db(deduplicated, completions, notion)

        with timed_phase("summary generation"):
            open_todos = notion.get_open_todos()
            summary = generate_summary(open_todos, stats, claude)

        total_duration = time.time() - run_start
        logger.info(f"Total pipeline duration: {total_duration:.1f}s")

        logger.info("=" * 80)
        logger.info("DAILY SUMMARY")
        logger.info("=" * 80)
        logger.info(summary)
        logger.info("=" * 80)
        logger.info("Todo aggregation run completed successfully")

    except Exception as e:
        logger.exception(f"Error during aggregation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
