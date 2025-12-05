"""Email sending utilities for Todo Aggregator notifications."""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .templates import get_error_template, get_success_template, get_welcome_template

logger = logging.getLogger(__name__)

# SMTP configuration
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@company.com")
BASE_URL = os.environ.get(
    "BASE_URL", "https://todo-aggregator-908833572352.us-central1.run.app"
)


def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send an HTML email.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML content

    Returns:
        True if sent successfully, False otherwise
    """
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, to_email]):
        logger.warning("SMTP not configured or no recipient, skipping email")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    # Add HTML content
    html_part = MIMEText(html_body, "html")
    msg.attach(html_part)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Sent email to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_success_email(
    user_email: str,
    user_name: str,
    notion_database_id: str,
    created: int,
    completed: int,
    slack_count: int = 0,
    gmail_count: int = 0,
) -> bool:
    """Send success summary email after a successful run.

    Args:
        user_email: User's email address
        user_name: User's display name
        notion_database_id: User's Notion database ID
        created: Number of new todos created
        completed: Number of todos auto-completed
        slack_count: Number of Slack messages scanned
        gmail_count: Number of Gmail threads scanned

    Returns:
        True if sent successfully, False otherwise
    """
    notion_url = f"https://notion.so/{notion_database_id}"

    subject, html_body = get_success_template(
        name=user_name,
        created=created,
        completed=completed,
        slack_count=slack_count,
        gmail_count=gmail_count,
        notion_url=notion_url,
    )

    return _send_email(user_email, subject, html_body)


def send_error_email(
    user_email: str,
    user_name: str,
    error: str,
) -> bool:
    """Send error notification when aggregator run fails.

    Args:
        user_email: User's email address
        user_name: User's display name
        error: Error message

    Returns:
        True if sent successfully, False otherwise
    """
    registration_url = f"{BASE_URL}/register"

    subject, html_body = get_error_template(
        name=user_name,
        error=error,
        registration_url=registration_url,
    )

    return _send_email(user_email, subject, html_body)


def send_welcome_email(
    user_email: str,
    user_name: str,
    user_id: str,
    personal_token: str,
    notion_database_id: str,
) -> bool:
    """Send welcome email with personal trigger URL.

    Args:
        user_email: User's email address
        user_name: User's display name
        user_id: User's ID
        personal_token: User's personal trigger token
        notion_database_id: User's Notion database ID

    Returns:
        True if sent successfully, False otherwise
    """
    trigger_url = f"{BASE_URL}/trigger/{user_id}/{personal_token}"
    notion_url = f"https://notion.so/{notion_database_id}"

    subject, html_body = get_welcome_template(
        name=user_name,
        trigger_url=trigger_url,
        notion_url=notion_url,
    )

    return _send_email(user_email, subject, html_body)
