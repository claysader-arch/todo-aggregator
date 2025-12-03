"""Configuration management for todo aggregator."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Central configuration for all API keys and settings."""

    # Anthropic
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Notion
    NOTION_API_KEY: str = os.getenv("NOTION_API_KEY", "")
    NOTION_DATABASE_ID: str = os.getenv("NOTION_DATABASE_ID", "")
    NOTION_MEETINGS_DATABASE_ID: str = os.getenv("NOTION_MEETINGS_DATABASE_ID", "")  # Optional: For Notion AI meeting notes

    # Slack
    SLACK_USER_TOKEN: str = os.getenv("SLACK_USER_TOKEN", "")  # User OAuth Token (xoxp-...)
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")  # Legacy, kept for compatibility
    SLACK_CANVAS_ID: str = os.getenv("SLACK_CANVAS_ID", "")

    # Zoom
    ZOOM_ACCOUNT_ID: str = os.getenv("ZOOM_ACCOUNT_ID", "")
    ZOOM_CLIENT_ID: str = os.getenv("ZOOM_CLIENT_ID", "")
    ZOOM_CLIENT_SECRET: str = os.getenv("ZOOM_CLIENT_SECRET", "")

    # Google/Gmail (Phase 4)
    GMAIL_CLIENT_ID: str = os.getenv("GMAIL_CLIENT_ID", "")
    GMAIL_CLIENT_SECRET: str = os.getenv("GMAIL_CLIENT_SECRET", "")
    GMAIL_REFRESH_TOKEN: str = os.getenv("GMAIL_REFRESH_TOKEN", "")
    GMAIL_LOOKBACK_DAYS: int = int(os.getenv("GMAIL_LOOKBACK_DAYS", "1"))
    GMAIL_QUERY: str = os.getenv("GMAIL_QUERY", "")  # Optional custom Gmail search query

    # Runtime settings
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Filtering settings
    MY_NAME: str = os.getenv("MY_NAME", "")  # Comma-separated list of name variations (e.g., "Clay,clay,Clay Sader")
    FILTER_MY_TODOS_ONLY: bool = os.getenv("FILTER_MY_TODOS_ONLY", "true").lower() == "true"

    # Phase 5: Intelligence Layer Feature Flags
    ENABLE_PRIORITY_SCORING: bool = os.getenv("ENABLE_PRIORITY_SCORING", "true").lower() == "true"
    ENABLE_CATEGORY_TAGGING: bool = os.getenv("ENABLE_CATEGORY_TAGGING", "true").lower() == "true"
    ENABLE_DUE_DATE_INFERENCE: bool = os.getenv("ENABLE_DUE_DATE_INFERENCE", "true").lower() == "true"

    # Priority keywords (comma-separated)
    HIGH_PRIORITY_KEYWORDS: str = os.getenv("HIGH_PRIORITY_KEYWORDS", "urgent,asap,critical,today,p0,immediately,blocker")

    # Phase 6: Zoom email senders for re-attribution (comma-separated)
    ZOOM_EMAIL_SENDERS: str = os.getenv("ZOOM_EMAIL_SENDERS", "meetings-noreply@zoom.us,no-reply@zoom.us,noreply@zoom.us")

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration values are present."""
        missing = []

        # Check required keys (start with just Anthropic and Notion for Phase 1)
        if not cls.ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY")
        if not cls.NOTION_API_KEY:
            missing.append("NOTION_API_KEY")
        if not cls.NOTION_DATABASE_ID:
            missing.append("NOTION_DATABASE_ID")

        return missing
