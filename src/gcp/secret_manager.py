"""Secret Manager client for credential storage.

Handles reading and writing secrets for both shared and per-user credentials.
"""

import logging
from typing import Optional

from google.api_core import exceptions
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


class SecretManagerClient:
    """Client for managing secrets in Google Secret Manager."""

    def __init__(self, project_id: str):
        """Initialize Secret Manager client.

        Args:
            project_id: GCP project ID
        """
        self.client = secretmanager.SecretManagerServiceClient()
        self.project_id = project_id

    def _secret_path(self, secret_id: str) -> str:
        """Get the full path for a secret."""
        return f"projects/{self.project_id}/secrets/{secret_id}"

    def _version_path(self, secret_id: str, version: str = "latest") -> str:
        """Get the full path for a secret version."""
        return f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"

    def get_secret(self, secret_id: str) -> Optional[str]:
        """Get the latest version of a secret.

        Args:
            secret_id: Secret identifier

        Returns:
            Secret value or None if not found
        """
        try:
            response = self.client.access_secret_version(
                name=self._version_path(secret_id)
            )
            return response.payload.data.decode("UTF-8")
        except exceptions.NotFound:
            logger.warning(f"Secret not found: {secret_id}")
            return None
        except exceptions.PermissionDenied:
            logger.error(f"Permission denied for secret: {secret_id}")
            return None

    def create_secret(self, secret_id: str, value: str) -> bool:
        """Create a new secret with an initial value.

        Args:
            secret_id: Secret identifier
            value: Secret value

        Returns:
            True if created successfully
        """
        try:
            # Create the secret
            self.client.create_secret(
                request={
                    "parent": f"projects/{self.project_id}",
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )

            # Add the secret version
            self.client.add_secret_version(
                request={
                    "parent": self._secret_path(secret_id),
                    "payload": {"data": value.encode("UTF-8")},
                }
            )

            logger.info(f"Created secret: {secret_id}")
            return True

        except exceptions.AlreadyExists:
            logger.warning(f"Secret already exists: {secret_id}")
            return False

    def update_secret(self, secret_id: str, value: str) -> bool:
        """Add a new version to an existing secret.

        Args:
            secret_id: Secret identifier
            value: New secret value

        Returns:
            True if updated successfully
        """
        try:
            self.client.add_secret_version(
                request={
                    "parent": self._secret_path(secret_id),
                    "payload": {"data": value.encode("UTF-8")},
                }
            )
            logger.info(f"Updated secret: {secret_id}")
            return True

        except exceptions.NotFound:
            logger.error(f"Secret not found for update: {secret_id}")
            return False

    def set_secret(self, secret_id: str, value: str) -> bool:
        """Create or update a secret.

        Args:
            secret_id: Secret identifier
            value: Secret value

        Returns:
            True if successful
        """
        # Try to update first (more common case)
        if self.update_secret(secret_id, value):
            return True

        # If not found, create it
        return self.create_secret(secret_id, value)

    def delete_secret(self, secret_id: str) -> bool:
        """Delete a secret.

        Args:
            secret_id: Secret identifier

        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete_secret(name=self._secret_path(secret_id))
            logger.info(f"Deleted secret: {secret_id}")
            return True
        except exceptions.NotFound:
            logger.warning(f"Secret not found for deletion: {secret_id}")
            return False

    # Convenience methods for user credentials

    def get_user_slack_token(self, user_id: str) -> Optional[str]:
        """Get a user's Slack token."""
        return self.get_secret(f"slack-token-{user_id}")

    def set_user_slack_token(self, user_id: str, token: str) -> bool:
        """Set a user's Slack token."""
        return self.set_secret(f"slack-token-{user_id}", token)

    def delete_user_slack_token(self, user_id: str) -> bool:
        """Delete a user's Slack token."""
        return self.delete_secret(f"slack-token-{user_id}")

    def get_user_gmail_token(self, user_id: str) -> Optional[str]:
        """Get a user's Gmail refresh token."""
        return self.get_secret(f"gmail-refresh-token-{user_id}")

    def set_user_gmail_token(self, user_id: str, token: str) -> bool:
        """Set a user's Gmail refresh token."""
        return self.set_secret(f"gmail-refresh-token-{user_id}", token)

    def delete_user_gmail_token(self, user_id: str) -> bool:
        """Delete a user's Gmail refresh token."""
        return self.delete_secret(f"gmail-refresh-token-{user_id}")

    def delete_user_secrets(self, user_id: str) -> None:
        """Delete all secrets for a user."""
        self.delete_user_slack_token(user_id)
        self.delete_user_gmail_token(user_id)
        logger.info(f"Deleted all secrets for user: {user_id}")