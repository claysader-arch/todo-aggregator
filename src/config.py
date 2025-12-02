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

    # Slack
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_CANVAS_ID: str = os.getenv("SLACK_CANVAS_ID", "")

    # Zoom
    ZOOM_ACCOUNT_ID: str = os.getenv("ZOOM_ACCOUNT_ID", "")
    ZOOM_CLIENT_ID: str = os.getenv("ZOOM_CLIENT_ID", "")
    ZOOM_CLIENT_SECRET: str = os.getenv("ZOOM_CLIENT_SECRET", "")

    # Google/Gmail
    GOOGLE_CREDENTIALS_PATH: Optional[str] = os.getenv("GOOGLE_CREDENTIALS_PATH")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Runtime settings
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

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
