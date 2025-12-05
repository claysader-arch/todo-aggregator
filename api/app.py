"""FastAPI endpoint for todo aggregation.

This API provides:
- User registration and management
- Per-user and batch todo aggregation
- Cloud Scheduler integration for automated daily runs
"""

import hashlib
import logging
import os
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Header, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, EmailStr

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mcp_clients.slack_client import SlackClient
from mcp_clients.gmail_client import GmailClient
from mcp_clients.notion_client import NotionClient
from processors.claude_processor import ClaudeProcessor
from gcp.firestore_client import FirestoreClient
from gcp.secret_manager import SecretManagerClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Todo Aggregator API",
    description="GCP-native todo aggregation service with multi-user support",
    version="1.0.0",
)

# Mount static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Environment variables (shared across all users)
API_SECRET = os.environ.get("API_SECRET", "")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
GMAIL_CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET", "")
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "todo-aggregator-480119")

# Initialize GCP clients (lazy loading)
_firestore: Optional[FirestoreClient] = None
_secrets: Optional[SecretManagerClient] = None


def get_firestore() -> FirestoreClient:
    """Get or create Firestore client."""
    global _firestore
    if _firestore is None:
        _firestore = FirestoreClient(project_id=GCP_PROJECT_ID)
    return _firestore


def get_secrets() -> SecretManagerClient:
    """Get or create Secret Manager client."""
    global _secrets
    if _secrets is None:
        _secrets = SecretManagerClient(project_id=GCP_PROJECT_ID)
    return _secrets


def get_registration_access_code() -> str:
    """Get the registration access code from Secret Manager."""
    return get_secrets().get_secret("registration-access-code") or ""

# SMTP configuration for error notifications
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@company.com")


class RunRequest(BaseModel):
    """Request body for the /run endpoint."""

    # User credentials (from Secret Manager)
    slack_token: str = ""
    gmail_refresh_token: str = ""
    notion_database_id: str

    # User context
    user_name: str
    user_email: str = ""
    user_slack_username: str = ""


class RunResponse(BaseModel):
    """Response from the /run endpoint."""

    status: str
    message: str


class RegisterRequest(BaseModel):
    """Request body for the /register endpoint."""

    access_code: str
    name: str
    email: EmailStr
    slack_username: str
    slack_token: str
    gmail_refresh_token: str
    notion_database_id: str


class RegisterResponse(BaseModel):
    """Response from the /register endpoint."""

    status: str
    message: str
    user_id: str


class UserResponse(BaseModel):
    """Response for user details."""

    id: str
    email: str
    name: str
    slack_username: str
    notion_database_id: str
    enabled: bool
    created_at: Optional[str] = None
    last_run: Optional[str] = None
    last_run_status: Optional[str] = None


def generate_user_id(email: str) -> str:
    """Generate a deterministic user ID from email.

    Args:
        email: User's email address

    Returns:
        8-character hash of the email
    """
    return hashlib.sha256(email.lower().encode()).hexdigest()[:8]


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


def send_welcome_email(
    user_email: str,
    user_name: str,
    user_id: str,
    personal_token: str,
    notion_database_id: str,
) -> None:
    """Send welcome email with personal trigger URL.

    Args:
        user_email: User's email address
        user_name: User's display name
        user_id: User's ID
        personal_token: User's personal trigger token
        notion_database_id: User's Notion database ID
    """
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, user_email]):
        logger.warning("SMTP not configured or no user email, skipping welcome email")
        return

    # Build the trigger URL (will be filled in with actual host in production)
    # For now, use a placeholder that works with Cloud Run
    base_url = os.environ.get("BASE_URL", "https://todo-aggregator-908833572352.us-central1.run.app")
    trigger_url = f"{base_url}/trigger/{user_id}/{personal_token}"
    notion_url = f"https://notion.so/{notion_database_id}"

    msg = MIMEText(f"""Hi {user_name},

Your Todo Aggregator is ready! It will run automatically every day at 7am PT.

Want to run it now? Click here:
{trigger_url}

You can bookmark this link or save it to run anytime.

Your todos will appear in your Notion database:
{notion_url}

- Todo Aggregator
""")
    msg["Subject"] = "Todo Aggregator - You're All Set!"
    msg["From"] = SMTP_FROM
    msg["To"] = user_email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Sent welcome email to {user_email}")
    except Exception as e:
        logger.error(f"Failed to send welcome email: {e}")


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


def process_aggregation(request: RunRequest) -> None:
    """Background task to run the todo aggregation.

    Args:
        request: User credentials and configuration
    """
    logger.info(f"Starting background aggregation for {request.user_name}")
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
            logger.error("NOTION_API_KEY not configured on server")
            return

        notion = NotionClient(
            api_key=NOTION_API_KEY,
            database_id=request.notion_database_id,
        )
        logger.info("Initialized Notion client")

        claude = ClaudeProcessor()

        # Collect content from all sources
        raw_content = {"slack": [], "gmail": []}

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

    except Exception as e:
        logger.exception(f"Run failed for {request.user_name}: {e}")
        if request.user_email:
            send_error_email(request.user_email, request.user_name, str(e))
        raise  # Re-raise for status tracking


def process_user_from_firestore(user: dict) -> dict:
    """Process a single user using credentials from Firestore/Secret Manager.

    Args:
        user: User document from Firestore

    Returns:
        Dict with status and stats
    """
    user_id = user["id"]
    user_name = user["name"]
    logger.info(f"Processing user {user_id} ({user_name})")

    firestore = get_firestore()
    secrets = get_secrets()

    try:
        # Fetch credentials from Secret Manager
        slack_token = secrets.get_user_slack_token(user_id)
        gmail_refresh_token = secrets.get_user_gmail_token(user_id)

        if not slack_token and not gmail_refresh_token:
            raise ValueError("No credentials found for user")

        # Build request object
        request = RunRequest(
            slack_token=slack_token or "",
            gmail_refresh_token=gmail_refresh_token or "",
            notion_database_id=user["notion_database_id"],
            user_name=user_name,
            user_email=user.get("email", ""),
            user_slack_username=user.get("slack_username", ""),
        )

        # Run aggregation (synchronously for now)
        process_aggregation(request)

        # Update status on success
        firestore.update_run_status(user_id, "success")
        logger.info(f"Successfully processed user {user_id}")

        return {"user_id": user_id, "status": "success"}

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to process user {user_id}: {error_msg}")

        # Update status on failure
        firestore.update_run_status(user_id, "error", error_msg)

        # Send error email
        if user.get("email"):
            send_error_email(user["email"], user_name, error_msg)

        return {"user_id": user_id, "status": "error", "error": error_msg}


def process_all_users() -> dict:
    """Process all enabled users sequentially.

    Returns:
        Summary of processing results
    """
    firestore = get_firestore()
    users = firestore.get_enabled_users()

    logger.info(f"Starting batch processing for {len(users)} users")

    results = {"success": 0, "error": 0, "users": []}

    for user in users:
        result = process_user_from_firestore(user)
        results["users"].append(result)

        if result["status"] == "success":
            results["success"] += 1
        else:
            results["error"] += 1

    logger.info(f"Batch processing complete: {results['success']} success, {results['error']} errors")
    return results


@app.post("/run-all", status_code=202)
async def run_all_users(
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
    x_api_secret: Optional[str] = Header(None),
) -> dict:
    """Run todo aggregation for all enabled users.

    This endpoint is designed to be called by Cloud Scheduler with OIDC auth,
    or manually with API secret authentication.

    Args:
        background_tasks: FastAPI background tasks
        authorization: OIDC Bearer token from Cloud Scheduler
        x_api_secret: API secret for manual invocation

    Returns:
        Acknowledgment that batch processing was queued
    """
    # Validate authentication (either OIDC or API secret)
    is_authenticated = False

    # Check API secret first (for manual invocation)
    if x_api_secret and API_SECRET and x_api_secret == API_SECRET:
        is_authenticated = True
        logger.info("Authenticated via API secret")

    # Check OIDC token (from Cloud Scheduler)
    # In production, you'd verify the token properly
    # For now, we just check it exists and starts with "Bearer"
    elif authorization and authorization.startswith("Bearer "):
        is_authenticated = True
        logger.info("Authenticated via OIDC token")

    if not is_authenticated:
        raise HTTPException(401, "Authentication required")

    # Get user count for response
    firestore = get_firestore()
    users = firestore.get_enabled_users()
    user_count = len(users)

    if user_count == 0:
        return {"status": "skipped", "message": "No enabled users to process"}

    # Queue background processing
    background_tasks.add_task(process_all_users)

    return {
        "status": "queued",
        "message": f"Batch processing queued for {user_count} users",
        "user_count": user_count,
    }


@app.post("/run/{user_id}", status_code=202)
async def run_single_user(
    user_id: str,
    background_tasks: BackgroundTasks,
    x_api_secret: str = Header(..., description="API secret for authentication"),
) -> dict:
    """Run todo aggregation for a specific user.

    Args:
        user_id: User identifier
        background_tasks: FastAPI background tasks
        x_api_secret: API secret for authentication

    Returns:
        Acknowledgment that processing was queued
    """
    # Validate API secret
    if not API_SECRET:
        raise HTTPException(500, "API_SECRET not configured")
    if x_api_secret != API_SECRET:
        raise HTTPException(401, "Invalid API secret")

    # Get user from Firestore
    firestore = get_firestore()
    user = firestore.get_user(user_id)

    if not user:
        raise HTTPException(404, f"User {user_id} not found")

    if not user.get("enabled", False):
        raise HTTPException(400, f"User {user_id} is disabled")

    # Queue background processing
    background_tasks.add_task(process_user_from_firestore, user)

    return {
        "status": "queued",
        "message": f"Processing queued for user {user['name']}",
        "user_id": user_id,
    }


@app.post("/run", response_model=RunResponse, status_code=202)
async def run_aggregator(
    request: RunRequest,
    background_tasks: BackgroundTasks,
    x_api_secret: str = Header(..., description="API secret for authentication"),
) -> RunResponse:
    """Run the todo aggregator for a specific user.

    This endpoint is used for ad-hoc runs with explicit credentials. It:
    1. Validates the request
    2. Queues the aggregation to run in the background
    3. Returns immediately with 202 Accepted

    Args:
        request: User credentials and configuration
        background_tasks: FastAPI background tasks
        x_api_secret: API secret for authentication

    Returns:
        Acknowledgment that the job was queued
    """
    # Validate API secret
    if not API_SECRET:
        raise HTTPException(500, "API_SECRET not configured on server")
    if x_api_secret != API_SECRET:
        raise HTTPException(401, "Invalid API secret")

    # Validate NOTION_API_KEY is configured
    if not NOTION_API_KEY:
        raise HTTPException(500, "NOTION_API_KEY not configured on server")

    logger.info(f"Queuing aggregation for {request.user_name}")

    # Queue the background task
    background_tasks.add_task(process_aggregation, request)

    return RunResponse(
        status="accepted",
        message=f"Aggregation queued for {request.user_name}. Check Notion for results.",
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/trigger/{user_id}/{token}", response_class=HTMLResponse)
async def trigger_user_run(
    user_id: str,
    token: str,
    background_tasks: BackgroundTasks,
) -> HTMLResponse:
    """Trigger a run for a user via their personal URL.

    This is a user-facing endpoint that validates the personal token
    and queues a run. Returns a friendly HTML page.

    Args:
        user_id: User identifier
        token: Personal token for authentication
        background_tasks: FastAPI background tasks

    Returns:
        HTML page confirming the run was started
    """
    firestore = get_firestore()
    user = firestore.get_user(user_id)

    # Validate user and token
    if not user:
        return HTMLResponse(
            content="""
            <html>
            <head><title>Error</title></head>
            <body style="font-family: sans-serif; padding: 2rem; text-align: center;">
                <h1>Invalid Link</h1>
                <p>This link is not valid. Please check you have the correct URL.</p>
            </body>
            </html>
            """,
            status_code=404,
        )

    if user.get("personal_token") != token:
        return HTMLResponse(
            content="""
            <html>
            <head><title>Error</title></head>
            <body style="font-family: sans-serif; padding: 2rem; text-align: center;">
                <h1>Invalid Link</h1>
                <p>This link is not valid. Please check you have the correct URL.</p>
            </body>
            </html>
            """,
            status_code=401,
        )

    if not user.get("enabled", False):
        return HTMLResponse(
            content="""
            <html>
            <head><title>Account Disabled</title></head>
            <body style="font-family: sans-serif; padding: 2rem; text-align: center;">
                <h1>Account Disabled</h1>
                <p>Your account is currently disabled. Please contact support.</p>
            </body>
            </html>
            """,
            status_code=403,
        )

    # Queue background processing
    background_tasks.add_task(process_user_from_firestore, user)
    logger.info(f"User {user_id} triggered their own run via personal URL")

    return HTMLResponse(
        content=f"""
        <html>
        <head>
            <title>Todo Aggregator - Running</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body style="font-family: -apple-system, sans-serif; padding: 2rem; text-align: center; max-width: 500px; margin: 0 auto;">
            <h1 style="color: #28a745;">Run Started!</h1>
            <p>Hi {user['name']}, your todo aggregation is running now.</p>
            <p>Check your Notion database in a few minutes for new todos.</p>
            <p style="margin-top: 2rem; color: #666; font-size: 0.9rem;">
                You can bookmark this page to run again anytime.
            </p>
        </body>
        </html>
        """,
        status_code=202,
    )


@app.get("/", response_class=FileResponse)
async def registration_form():
    """Serve the registration form."""
    return FileResponse(os.path.join(STATIC_DIR, "register.html"))


# =============================================================================
# User Management Endpoints
# =============================================================================


@app.post("/register", response_model=RegisterResponse)
async def register_user(request: RegisterRequest) -> RegisterResponse:
    """Register a new user.

    This endpoint creates a new user in Firestore and stores their
    credentials in Secret Manager.

    Args:
        request: User registration data including access code

    Returns:
        Registration confirmation with user ID
    """
    # Validate access code
    valid_code = get_registration_access_code()
    if not valid_code:
        raise HTTPException(500, "Registration not configured")
    if request.access_code != valid_code:
        raise HTTPException(401, "Invalid access code")

    # Generate user ID from email
    user_id = generate_user_id(request.email)

    # Check if user already exists
    firestore = get_firestore()
    existing = firestore.get_user(user_id)
    if existing:
        # Update existing user's credentials
        secrets = get_secrets()
        secrets.set_user_slack_token(user_id, request.slack_token)
        secrets.set_user_gmail_token(user_id, request.gmail_refresh_token)

        # Update Firestore record
        firestore.update_user(user_id, {
            "name": request.name,
            "slack_username": request.slack_username,
            "notion_database_id": request.notion_database_id,
            "enabled": True,
        })

        logger.info(f"Updated existing user: {user_id}")
        return RegisterResponse(
            status="updated",
            message=f"User {request.name} updated successfully",
            user_id=user_id,
        )

    # Create new user in Firestore
    user_data = firestore.create_user(
        user_id=user_id,
        email=request.email,
        name=request.name,
        slack_username=request.slack_username,
        notion_database_id=request.notion_database_id,
    )

    # Store credentials in Secret Manager
    secrets = get_secrets()
    secrets.set_user_slack_token(user_id, request.slack_token)
    secrets.set_user_gmail_token(user_id, request.gmail_refresh_token)

    logger.info(f"Registered new user: {user_id} ({request.email})")

    # Send welcome email with personal trigger URL
    send_welcome_email(
        user_email=request.email,
        user_name=request.name,
        user_id=user_id,
        personal_token=user_data.get("personal_token", ""),
        notion_database_id=request.notion_database_id,
    )

    return RegisterResponse(
        status="created",
        message=f"User {request.name} registered successfully",
        user_id=user_id,
    )


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    x_api_secret: str = Header(..., description="API secret for authentication"),
) -> UserResponse:
    """Get user details by ID.

    This is an admin endpoint that requires API secret authentication.

    Args:
        user_id: User identifier
        x_api_secret: API secret for authentication

    Returns:
        User details (excluding credentials)
    """
    # Validate API secret
    if not API_SECRET:
        raise HTTPException(500, "API_SECRET not configured")
    if x_api_secret != API_SECRET:
        raise HTTPException(401, "Invalid API secret")

    firestore = get_firestore()
    user = firestore.get_user(user_id)

    if not user:
        raise HTTPException(404, f"User {user_id} not found")

    # Convert datetime fields to strings
    created_at = user.get("created_at")
    last_run = user.get("last_run")

    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        slack_username=user["slack_username"],
        notion_database_id=user["notion_database_id"],
        enabled=user["enabled"],
        created_at=created_at.isoformat() if created_at else None,
        last_run=last_run.isoformat() if last_run else None,
        last_run_status=user.get("last_run_status"),
    )


@app.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    x_api_secret: str = Header(..., description="API secret for authentication"),
) -> dict:
    """Delete a user and their credentials.

    This is an admin endpoint that requires API secret authentication.

    Args:
        user_id: User identifier
        x_api_secret: API secret for authentication

    Returns:
        Deletion confirmation
    """
    # Validate API secret
    if not API_SECRET:
        raise HTTPException(500, "API_SECRET not configured")
    if x_api_secret != API_SECRET:
        raise HTTPException(401, "Invalid API secret")

    firestore = get_firestore()
    user = firestore.get_user(user_id)

    if not user:
        raise HTTPException(404, f"User {user_id} not found")

    # Delete credentials from Secret Manager
    secrets = get_secrets()
    secrets.delete_user_secrets(user_id)

    # Delete user from Firestore
    firestore.delete_user(user_id)

    logger.info(f"Deleted user: {user_id}")

    return {"status": "deleted", "message": f"User {user_id} deleted successfully"}


@app.get("/users")
async def list_users(
    x_api_secret: str = Header(..., description="API secret for authentication"),
) -> dict:
    """List all users.

    This is an admin endpoint that requires API secret authentication.

    Args:
        x_api_secret: API secret for authentication

    Returns:
        List of all users (excluding credentials)
    """
    # Validate API secret
    if not API_SECRET:
        raise HTTPException(500, "API_SECRET not configured")
    if x_api_secret != API_SECRET:
        raise HTTPException(401, "Invalid API secret")

    firestore = get_firestore()
    users = firestore.get_all_users()

    return {
        "users": [
            {
                "id": u["id"],
                "email": u["email"],
                "name": u["name"],
                "enabled": u["enabled"],
                "last_run_status": u.get("last_run_status"),
            }
            for u in users
        ],
        "count": len(users),
    }
