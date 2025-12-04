"""Gmail API client for fetching email content."""

import base64
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import Config

logger = logging.getLogger(__name__)


class GmailClient:
    """Client for interacting with Gmail API to fetch email content."""

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    # Default Zoom email senders for re-attribution
    DEFAULT_ZOOM_SENDERS = "meetings-noreply@zoom.us,no-reply@zoom.us,noreply@zoom.us"

    def __init__(self):
        """Initialize Gmail client with OAuth credentials."""
        self.client_id = Config.GMAIL_CLIENT_ID
        self.client_secret = Config.GMAIL_CLIENT_SECRET
        self.refresh_token = Config.GMAIL_REFRESH_TOKEN
        self._service = None

    def _build_message_url(self, message_id: str) -> str:
        """
        Build URL to open Gmail message.

        Args:
            message_id: Gmail message ID

        Returns:
            URL to the message in Gmail web interface
        """
        return f"https://mail.google.com/mail/u/0/#inbox/{message_id}"

    def _detect_zoom_email(self, from_addr: str) -> bool:
        """
        Detect if an email is from Zoom (for source re-attribution).

        Args:
            from_addr: From header value

        Returns:
            True if email is from a Zoom sender
        """
        from_addr_lower = from_addr.lower()
        zoom_senders = getattr(Config, 'ZOOM_EMAIL_SENDERS', self.DEFAULT_ZOOM_SENDERS)
        zoom_list = [s.strip().lower() for s in zoom_senders.split(",")]
        return any(zoom_sender in from_addr_lower for zoom_sender in zoom_list)

    def _get_credentials(self) -> Credentials:
        """
        Create credentials from refresh token.

        Returns:
            Google OAuth credentials object
        """
        return Credentials(
            token=None,  # Will be auto-refreshed
            refresh_token=self.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES,
        )

    def _get_service(self):
        """
        Build Gmail API service, reusing if already created.

        Returns:
            Gmail API service object
        """
        if self._service is None:
            credentials = self._get_credentials()
            self._service = build("gmail", "v1", credentials=credentials)
        return self._service

    def _get_header_value(self, headers: List[Dict], name: str) -> str:
        """
        Get a header value from message headers.

        Args:
            headers: List of header dicts with 'name' and 'value' keys
            name: Header name to find (case-insensitive)

        Returns:
            Header value or empty string if not found
        """
        name_lower = name.lower()
        for header in headers:
            if header.get("name", "").lower() == name_lower:
                return header.get("value", "")
        return ""

    def _get_message_body(self, payload: Dict) -> str:
        """
        Extract plain text body from message payload.

        Args:
            payload: Message payload from Gmail API

        Returns:
            Decoded plain text body
        """
        body = ""

        # Check for simple body
        if payload.get("body", {}).get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
            return body

        # Check for multipart message
        parts = payload.get("parts", [])
        for part in parts:
            mime_type = part.get("mimeType", "")

            # Prefer plain text
            if mime_type == "text/plain":
                if part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    return body

            # Recurse into nested multipart
            if mime_type.startswith("multipart/"):
                nested_body = self._get_message_body(part)
                if nested_body:
                    return nested_body

        # Fall back to HTML if no plain text found
        for part in parts:
            if part.get("mimeType") == "text/html":
                if part.get("body", {}).get("data"):
                    # Return HTML as-is, Claude can handle it
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    return body

        return body

    def _format_email(self, message: Dict) -> str:
        """
        Format an email message for Claude processing.

        Args:
            message: Full message object from Gmail API

        Returns:
            Formatted string with email details
        """
        payload = message.get("payload", {})
        headers = payload.get("headers", [])

        subject = self._get_header_value(headers, "Subject") or "(no subject)"
        from_addr = self._get_header_value(headers, "From")
        to_addr = self._get_header_value(headers, "To")
        date_str = self._get_header_value(headers, "Date")

        # Parse and format date
        try:
            date_obj = parsedate_to_datetime(date_str)
            formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
        except Exception:
            formatted_date = date_str[:20] if date_str else "unknown date"

        # Determine if sent or received
        direction = "to" if "SENT" in message.get("labelIds", []) else "from"
        address = to_addr if direction == "to" else from_addr

        # Get body
        body = self._get_message_body(payload)

        # Truncate very long bodies
        max_body_length = 3000
        if len(body) > max_body_length:
            body = body[:max_body_length] + "\n... [truncated]"

        # Format output
        header = f"=== Gmail: {subject} ({direction}: {address}) ==="
        content = f"[{formatted_date}]\n{body}"

        return f"{header}\n{content}"

    def _build_query(self, days: int) -> str:
        """
        Build Gmail search query.

        Args:
            days: Number of days to look back

        Returns:
            Gmail search query string
        """
        # Use custom query if provided
        if Config.GMAIL_QUERY:
            return Config.GMAIL_QUERY

        # Calculate date threshold
        after_date = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")

        # Default query: recent emails excluding promotions/social
        query = f"after:{after_date} -category:promotions -category:social"

        return query

    def _format_thread(self, thread: Dict) -> str:
        """
        Format an entire email thread for Claude processing.

        Args:
            thread: Full thread object from Gmail API

        Returns:
            Formatted string with all messages in chronological order
        """
        messages = thread.get("messages", [])
        if not messages:
            return ""

        # Get subject from first message
        first_payload = messages[0].get("payload", {})
        first_headers = first_payload.get("headers", [])
        subject = self._get_header_value(first_headers, "Subject") or "(no subject)"

        # Format each message in the thread (oldest first)
        formatted_messages = []
        for message in messages:
            payload = message.get("payload", {})
            headers = payload.get("headers", [])

            from_addr = self._get_header_value(headers, "From")
            date_str = self._get_header_value(headers, "Date")

            # Parse and format date
            try:
                date_obj = parsedate_to_datetime(date_str)
                formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
            except Exception:
                formatted_date = date_str[:20] if date_str else "unknown"

            # Get body
            body = self._get_message_body(payload)

            # Truncate very long bodies
            max_body_length = 2000
            if len(body) > max_body_length:
                body = body[:max_body_length] + "\n... [truncated]"

            formatted_messages.append(f"[{formatted_date}] From: {from_addr}\n{body}")

        # Combine into thread format
        header = f"=== Gmail Thread: {subject} ==="
        thread_content = "\n---\n".join(formatted_messages)

        return f"{header}\n{thread_content}"

    def get_gmail_content(self, days: int = None) -> List[Dict[str, Any]]:
        """
        Get formatted emails from the last N days, grouped by thread.

        This is the main method called by the orchestrator.

        Args:
            days: Number of days to look back (defaults to GMAIL_LOOKBACK_DAYS)

        Returns:
            List of structured content dicts with text, source_url, source, and metadata
        """
        if days is None:
            days = Config.GMAIL_LOOKBACK_DAYS

        logger.info(f"Fetching Gmail messages from last {days} day(s)...")

        content = []
        service = self._get_service()

        try:
            query = self._build_query(days)
            logger.debug(f"Gmail query: {query}")

            # List messages matching query
            results = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=50  # Limit to avoid overwhelming Claude
            ).execute()

            messages = results.get("messages", [])
            logger.info(f"Found {len(messages)} emails matching query")

            # Group messages by thread ID
            thread_ids = set()
            for msg_ref in messages:
                thread_ids.add(msg_ref.get("threadId"))

            logger.info(f"Grouped into {len(thread_ids)} email threads")

            # Fetch full thread content for each unique thread
            for thread_id in thread_ids:
                try:
                    thread = service.users().threads().get(
                        userId="me",
                        id=thread_id,
                        format="full"
                    ).execute()

                    thread_messages = thread.get("messages", [])
                    if not thread_messages:
                        continue

                    # Get metadata from most recent message
                    latest_msg = thread_messages[-1]
                    latest_id = latest_msg.get("id")
                    latest_payload = latest_msg.get("payload", {})
                    latest_headers = latest_payload.get("headers", [])

                    from_addr = self._get_header_value(latest_headers, "From")
                    subject = self._get_header_value(latest_headers, "Subject") or "(no subject)"

                    # Detect if this is a Zoom email for source re-attribution
                    # Check if ANY message in thread is from Zoom
                    is_zoom_email = any(
                        self._detect_zoom_email(
                            self._get_header_value(
                                msg.get("payload", {}).get("headers", []), "From"
                            )
                        )
                        for msg in thread_messages
                    )
                    source = "zoom" if is_zoom_email else "gmail"

                    # Format the full thread
                    formatted_text = self._format_thread(thread)

                    # Build URL to latest message in thread
                    source_url = self._build_message_url(latest_id)

                    content.append({
                        "text": formatted_text,
                        "source_url": source_url,
                        "source": source,
                        "metadata": {
                            "thread_id": thread_id,
                            "message_count": len(thread_messages),
                            "subject": subject,
                            "from": from_addr,
                            "is_zoom_email": is_zoom_email,
                        }
                    })

                    if is_zoom_email:
                        logger.debug(f"Detected Zoom thread (re-attributed): {subject}")

                except HttpError as e:
                    logger.warning(f"Error fetching thread {thread_id}: {e}")
                    continue

        except HttpError as e:
            logger.error(f"Error listing Gmail messages: {e}")
            raise

        logger.info(f"Collected {len(content)} Gmail threads ({sum(1 for c in content if c['source'] == 'zoom')} from Zoom)")
        return content

    def test_connection(self) -> bool:
        """
        Test Gmail API connection and credentials.

        Returns:
            True if connection successful
        """
        try:
            service = self._get_service()

            # Get user profile
            profile = service.users().getProfile(userId="me").execute()
            email = profile.get("emailAddress", "unknown")
            messages_total = profile.get("messagesTotal", 0)

            logger.info(f"Gmail API connection successful (email: {email})")
            logger.info(f"Mailbox contains {messages_total} total messages")
            return True

        except HttpError as e:
            logger.error(f"Gmail API connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Gmail API connection failed: {e}")
            return False
