"""Firestore client for user management.

Handles CRUD operations for user documents in the 'users' collection.
"""

import logging
import secrets
from datetime import datetime
from typing import Optional

from google.cloud import firestore

logger = logging.getLogger(__name__)


class FirestoreClient:
    """Client for managing users in Firestore."""

    COLLECTION = "users"

    def __init__(self, project_id: Optional[str] = None):
        """Initialize Firestore client.

        Args:
            project_id: GCP project ID. If None, uses default from environment.
        """
        self.db = firestore.Client(project=project_id)
        self.users = self.db.collection(self.COLLECTION)

    def create_user(
        self,
        user_id: str,
        email: str,
        name: str,
        slack_username: str,
        notion_database_id: str,
    ) -> dict:
        """Create a new user document.

        Args:
            user_id: Unique user identifier
            email: User's email address
            name: User's display name
            slack_username: User's Slack display name
            notion_database_id: User's Notion database ID

        Returns:
            Created user document data
        """
        # Generate a personal token for self-service trigger URL
        personal_token = secrets.token_hex(16)  # 32 hex chars

        user_data = {
            "email": email,
            "name": name,
            "slack_username": slack_username,
            "notion_database_id": notion_database_id,
            "personal_token": personal_token,
            "enabled": True,
            "created_at": datetime.utcnow(),
            "last_run": None,
            "last_run_status": None,
        }

        self.users.document(user_id).set(user_data)
        logger.info(f"Created user {user_id}")

        return {"id": user_id, **user_data}

    def get_user(self, user_id: str) -> Optional[dict]:
        """Get a user by ID.

        Args:
            user_id: User identifier

        Returns:
            User document data or None if not found
        """
        doc = self.users.document(user_id).get()
        if doc.exists:
            return {"id": doc.id, **doc.to_dict()}
        return None

    def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get a user by email address.

        Args:
            email: User's email address

        Returns:
            User document data or None if not found
        """
        docs = self.users.where("email", "==", email).limit(1).stream()
        for doc in docs:
            return {"id": doc.id, **doc.to_dict()}
        return None

    def update_user(self, user_id: str, updates: dict) -> bool:
        """Update a user document.

        Args:
            user_id: User identifier
            updates: Fields to update

        Returns:
            True if updated, False if user not found
        """
        doc_ref = self.users.document(user_id)
        if not doc_ref.get().exists:
            return False

        doc_ref.update(updates)
        logger.info(f"Updated user {user_id}")
        return True

    def delete_user(self, user_id: str) -> bool:
        """Delete a user document.

        Args:
            user_id: User identifier

        Returns:
            True if deleted, False if user not found
        """
        doc_ref = self.users.document(user_id)
        if not doc_ref.get().exists:
            return False

        doc_ref.delete()
        logger.info(f"Deleted user {user_id}")
        return True

    def get_enabled_users(self) -> list[dict]:
        """Get all enabled users.

        Returns:
            List of enabled user documents
        """
        docs = self.users.where("enabled", "==", True).stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]

    def get_all_users(self) -> list[dict]:
        """Get all users.

        Returns:
            List of all user documents
        """
        docs = self.users.stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]

    def update_run_status(
        self, user_id: str, status: str, error: Optional[str] = None
    ) -> None:
        """Update a user's last run status.

        Args:
            user_id: User identifier
            status: Run status ('success' or 'error')
            error: Error message if status is 'error'
        """
        updates = {
            "last_run": datetime.utcnow(),
            "last_run_status": status,
        }
        if error:
            updates["last_run_error"] = error

        self.users.document(user_id).update(updates)
        logger.info(f"Updated run status for {user_id}: {status}")