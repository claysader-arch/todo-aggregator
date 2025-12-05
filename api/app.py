"""FastAPI endpoint for Zapier-triggered todo aggregation.

This API allows Zapier to trigger the todo aggregator for individual users,
passing their credentials as part of the request.
"""

import logging
import os
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mcp_clients.slack_client import SlackClient
from mcp_clients.gmail_client import GmailClient
from mcp_clients.notion_client import NotionClient
from processors.claude_processor import ClaudeProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Todo Aggregator API",
    description="API endpoint for Zapier-triggered todo aggregation",
    version="1.0.0",
)

# Environment variables (shared across all users)
API_SECRET = os.environ.get("API_SECRET", "")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
GMAIL_CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET", "")

# SMTP configuration for error notifications
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@company.com")


class RunRequest(BaseModel):
    """Request body for the /run endpoint."""

    # User credentials (from Zapier webhook config)
    slack_token: str = ""
    gmail_refresh_token: str = ""
    notion_database_id: str
    notion_meetings_db_id: str = ""

    # User context
    user_name: str
    user_email: str = ""
    user_slack_username: str = ""


class RunResponse(BaseModel):
    """Response from the /run endpoint."""

    created: int
    skipped: int
    completed: int
    duration_seconds: float


def send_error_email(user_email: str, user_name: str, error: str) -> None:
    """Send email notification when aggregator run fails.

    Args:
        user_email: User's email address
        user_name: User's display name
        error: Error message
    """
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, user_email]):
        logger.warning("SMTP not configured or no user email, skipping error notification")
        return

    msg = MIMEText(f"""Hi {user_name},

Your Todo Aggregator run failed this morning.

Error: {error}

This usually means one of your tokens expired. Please reach out to get it fixed.

- Todo Aggregator Bot
""")
    msg["Subject"] = "Todo Aggregator Run Failed"
    msg["From"] = SMTP_FROM
    msg["To"] = user_email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Sent error notification to {user_email}")
    except Exception as e:
        logger.error(f"Failed to send error email: {e}")


def filter_my_todos(todos: list, user_name: str) -> list:
    """Filter todos to only include those assigned to the user.

    Args:
        todos: List of todos to filter
        user_name: User's name variations (comma-separated)

    Returns:
        Filtered list of todos
    """
    if not user_name:
        return todos

    # Parse name variations (comma-separated)
    my_names = [name.strip().lower() for name in user_name.split(",")]

    filtered = []
    for todo in todos:
        assigned_to = (todo.get("assigned_to") or "").strip().lower()

        # Check if assigned to user (match any name variation)
        if any(name in assigned_to for name in my_names if name):
            filtered.append(todo)
        # Also keep unassigned todos
        elif not assigned_to:
            filtered.append(todo)

    logger.info(f"Filtered {len(todos)} todos to {len(filtered)} assigned to {user_name}")
    return filtered


@app.post("/run", response_model=RunResponse)
async def run_aggregator(
    request: RunRequest,
    x_api_secret: str = Header(..., description="API secret for authentication"),
) -> RunResponse:
    """Run the todo aggregator for a specific user.

    This endpoint is called by Zapier on a schedule. It:
    1. Fetches content from Slack, Gmail, and Notion
    2. Extracts todos using Claude
    3. Deduplicates against existing todos
    4. Detects completed todos
    5. Writes results to Notion

    Args:
        request: User credentials and configuration
        x_api_secret: API secret for authentication

    Returns:
        Statistics about the run
    """
    # Validate API secret
    if not API_SECRET:
        raise HTTPException(500, "API_SECRET not configured on server")
    if x_api_secret != API_SECRET:
        raise HTTPException(401, "Invalid API secret")

    logger.info(f"Running aggregator for {request.user_name}")
    start_time = datetime.now()

    try:
        # Initialize clients with user's credentials
        slack = None
        if request.slack_token:
            slack = SlackClient(token=request.slack_token)
            logger.info("Initialized Slack client")

        gmail = None
        if request.gmail_refresh_token and GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET:
            gmail = GmailClient(
                client_id=GMAIL_CLIENT_ID,
                client_secret=GMAIL_CLIENT_SECRET,
                refresh_token=request.gmail_refresh_token,
            )
            logger.info("Initialized Gmail client")

        if not NOTION_API_KEY:
            raise HTTPException(500, "NOTION_API_KEY not configured on server")

        notion = NotionClient(
            api_key=NOTION_API_KEY,
            database_id=request.notion_database_id,
            meetings_db_id=request.notion_meetings_db_id or None,
        )
        logger.info("Initialized Notion client")

        claude = ClaudeProcessor()

        # Collect content from all sources
        raw_content = {"slack": [], "gmail": [], "zoom": [], "notion": []}

        if slack:
            try:
                raw_content["slack"] = slack.get_slack_content(days=1)
                logger.info(f"Collected {len(raw_content['slack'])} Slack messages")
            except Exception as e:
                logger.error(f"Error collecting Slack content: {e}")

        if gmail:
            try:
                raw_content["gmail"] = gmail.get_gmail_content()
                logger.info(f"Collected {len(raw_content['gmail'])} Gmail threads")
            except Exception as e:
                logger.error(f"Error collecting Gmail content: {e}")

        if request.notion_meetings_db_id:
            try:
                raw_content["notion"] = notion.get_recent_meetings(days=1)
                logger.info(f"Collected {len(raw_content['notion'])} Notion meeting notes")
            except Exception as e:
                logger.error(f"Error collecting Notion meetings: {e}")

        # Extract todos using Claude with user context
        extracted = claude.extract_todos(
            raw_content,
            user_name=request.user_name,
            user_email=request.user_email,
            user_slack_username=request.user_slack_username,
        )
        logger.info(f"Extracted {len(extracted)} todos")

        # Filter to user's todos
        filtered = filter_my_todos(extracted, request.user_name)

        # Deduplicate against existing todos
        existing = notion.get_all_todos()
        logger.info(f"Found {len(existing)} existing todos in Notion")
        deduplicated = claude.deduplicate_todos(filtered, existing)

        # Detect completions
        open_todos = notion.get_open_todos()
        completions = claude.detect_completions(open_todos, raw_content)
        logger.info(f"Detected {len(completions)} completed todos")

        # Write to Notion
        stats = {"created": 0, "skipped": 0, "completed": 0}

        # Create new todos
        for todo in deduplicated:
            if "_update_id" not in todo:
                page_data = notion.create_page({
                    "task": todo.get("task", ""),
                    "status": "Open",
                    "source": [todo.get("source", "unknown")],
                    "source_url": todo.get("source_url"),
                    "due_date": todo.get("due_date"),
                    "confidence": todo.get("confidence", 0.0),
                    "dedupe_hash": todo.get("dedupe_hash", ""),
                    "priority": todo.get("priority", "medium"),
                    "category": todo.get("category", []),
                })
                stats["created"] += 1

                # Add source context as comment
                source_context = todo.get("source_context")
                if source_context and page_data:
                    page_id = page_data.get("id")
                    if page_id:
                        source = todo.get("source", "unknown")
                        context_text = source_context[:500] + "..." if len(source_context) > 500 else source_context
                        comment = f"Source ({source}): {context_text}"
                        try:
                            notion.add_comment(page_id, comment)
                        except Exception as e:
                            logger.warning(f"Could not add context comment: {e}")
            else:
                stats["skipped"] += 1

        # Mark completed todos
        for completion in completions:
            confidence = completion.get("confidence", 0)
            status = "Done" if confidence >= 0.85 else "Done?"
            notion.update_page(
                completion["todo_id"],
                {"status": status, "completed": datetime.now().date().isoformat()},
            )
            stats["completed"] += 1

            # Add completion evidence as comment
            evidence = completion.get("evidence", "")
            if status == "Done":
                comment = f"Auto-completed ({confidence:.0%}): \"{evidence[:200]}\"" if evidence else f"Auto-completed ({confidence:.0%})"
            else:
                comment = f"Needs review ({confidence:.0%}): \"{evidence[:200]}\"" if evidence else f"Needs review ({confidence:.0%})"
            try:
                notion.add_comment(completion["todo_id"], comment)
            except Exception as e:
                logger.warning(f"Could not add completion comment: {e}")

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Completed for {request.user_name} in {duration:.1f}s: {stats}")

        return RunResponse(
            created=stats["created"],
            skipped=stats["skipped"],
            completed=stats["completed"],
            duration_seconds=duration,
        )

    except Exception as e:
        logger.exception(f"Run failed for {request.user_name}: {e}")
        if request.user_email:
            send_error_email(request.user_email, request.user_name, str(e))
        raise HTTPException(500, f"Run failed: {e}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
