"""Zoom API client for fetching meeting summaries and transcripts."""

import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
import base64
from config import Config

logger = logging.getLogger(__name__)


class ZoomClient:
    """Client for interacting with Zoom API to fetch meeting data."""

    def __init__(self):
        """Initialize Zoom client with OAuth credentials."""
        self.account_id = Config.ZOOM_ACCOUNT_ID
        self.client_id = Config.ZOOM_CLIENT_ID
        self.client_secret = Config.ZOOM_CLIENT_SECRET
        self.base_url = "https://api.zoom.us/v2"
        self.access_token = None
        self.token_expiry = None

    def _build_meeting_url(self, meeting_id: str, recording_id: str = None) -> str:
        """
        Build URL to Zoom meeting or recording.

        Args:
            meeting_id: Zoom meeting ID
            recording_id: Optional recording ID for direct link to recording

        Returns:
            URL to the meeting or recording
        """
        if recording_id:
            return f"https://zoom.us/rec/play/{recording_id}"
        # Clean meeting ID (remove any dashes)
        clean_id = str(meeting_id).replace("-", "")
        return f"https://zoom.us/j/{clean_id}"

    def _get_access_token(self) -> str:
        """
        Get OAuth access token for Zoom API using Server-to-Server OAuth.

        Returns:
            Access token string
        """
        # Check if we have a valid cached token
        if self.access_token and self.token_expiry:
            if datetime.now() < self.token_expiry:
                return self.access_token

        # Get new token
        url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={self.account_id}"

        # Create Basic Auth header
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            self.access_token = data["access_token"]
            # Set expiry with 5 min buffer
            expires_in = data.get("expires_in", 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)

            logger.info("Successfully obtained Zoom access token")
            return self.access_token

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting Zoom access token: {e}")
            raise

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make authenticated request to Zoom API.

        Args:
            endpoint: API endpoint (without base URL)
            params: Optional query parameters

        Returns:
            Response JSON data
        """
        token = self._get_access_token()
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error making Zoom API request to {endpoint}: {e}")
            if hasattr(response, 'text'):
                logger.error(f"Response: {response.text}")
            raise

    def get_recent_meetings(
        self, user_id: str = "me", days: int = 7, page_size: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get list of recent past meeting instances.

        Args:
            user_id: Zoom user ID or "me" for authenticated user
            days: Number of days to look back
            page_size: Number of results per page

        Returns:
            List of past meeting instance objects
        """
        try:
            # First, get all scheduled meetings
            params = {"type": "scheduled", "page_size": page_size}
            data = self._make_request(f"/users/{user_id}/meetings", params=params)
            scheduled_meetings = data.get("meetings", [])

            logger.info(f"Found {len(scheduled_meetings)} scheduled meetings")

            # Now get past instances for each scheduled meeting
            past_meetings = []
            cutoff_date = datetime.now() - timedelta(days=days)

            for meeting in scheduled_meetings:
                meeting_id = meeting.get("id")
                try:
                    # Get past instances for this meeting
                    instances_data = self._make_request(f"/past_meetings/{meeting_id}/instances")
                    instances = instances_data.get("meetings", [])

                    # Filter instances within the date range
                    for instance in instances:
                        start_time_str = instance.get("start_time", "")
                        if start_time_str:
                            try:
                                # Parse the datetime (handle Z timezone)
                                start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%SZ")
                                # Make cutoff_date timezone-naive for comparison
                                if start_time >= cutoff_date.replace(tzinfo=None):
                                    # Add meeting topic from scheduled meeting
                                    instance["topic"] = meeting.get("topic", "Unknown Meeting")
                                    past_meetings.append(instance)
                            except ValueError:
                                # If parsing fails, include the meeting anyway
                                instance["topic"] = meeting.get("topic", "Unknown Meeting")
                                past_meetings.append(instance)

                except Exception as e:
                    logger.debug(f"No past instances for meeting {meeting_id}: {e}")
                    continue

            logger.info(f"Retrieved {len(past_meetings)} past meeting instances from last {days} days")
            return past_meetings

        except Exception as e:
            logger.error(f"Error fetching recent meetings: {e}")
            return []

    def get_meeting_summary(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """
        Get AI-generated summary for a meeting.

        Args:
            meeting_id: Zoom meeting ID

        Returns:
            Meeting summary data or None
        """
        try:
            # Note: This endpoint requires Zoom AI Companion to be enabled
            data = self._make_request(f"/meetings/{meeting_id}/meeting_summary")
            logger.info(f"Retrieved summary for meeting {meeting_id}")
            return data

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"No AI summary available for meeting {meeting_id}")
            else:
                logger.error(f"Error fetching meeting summary: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching meeting summary: {e}")
            return None

    def get_meeting_transcript(self, meeting_id: str) -> Optional[str]:
        """
        Get transcript for a meeting.

        Args:
            meeting_id: Zoom meeting ID

        Returns:
            Transcript text or None
        """
        try:
            # Get list of transcript files
            data = self._make_request(f"/meetings/{meeting_id}/recordings")

            # Find transcript file
            recording_files = data.get("recording_files", [])
            for file in recording_files:
                if file.get("file_type") == "TRANSCRIPT":
                    # Download transcript
                    download_url = file.get("download_url")
                    if download_url:
                        token = self._get_access_token()
                        response = requests.get(
                            download_url,
                            headers={"Authorization": f"Bearer {token}"},
                        )
                        response.raise_for_status()

                        # Parse VTT transcript
                        transcript_text = self._parse_transcript(response.text)
                        logger.info(f"Retrieved transcript for meeting {meeting_id}")
                        return transcript_text

            logger.debug(f"No transcript available for meeting {meeting_id}")
            return None

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"No recordings/transcript for meeting {meeting_id}")
            else:
                logger.error(f"Error fetching transcript: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching transcript: {e}")
            return None

    def _parse_transcript(self, vtt_text: str) -> str:
        """
        Parse VTT transcript format to plain text.

        Args:
            vtt_text: VTT formatted transcript

        Returns:
            Plain text transcript
        """
        lines = []
        in_cue = False

        for line in vtt_text.split("\n"):
            line = line.strip()

            # Skip VTT headers and timestamps
            if line.startswith("WEBVTT") or "-->" in line or line.isdigit():
                in_cue = False
                continue

            # Empty line indicates end of cue
            if not line:
                in_cue = False
                continue

            # This is transcript text
            if not in_cue:
                in_cue = True
                lines.append(line)

        return " ".join(lines)

    def get_meeting_content(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get AI-generated meeting summaries from recent meetings.

        Args:
            days: Number of days to look back

        Returns:
            List of structured content dicts with text, source_url, source, and metadata
        """
        logger.info(f"Fetching Zoom meeting summaries from last {days} days...")

        content = []
        cutoff_date = datetime.now() - timedelta(days=days)

        try:
            # Get all scheduled meetings
            data = self._make_request("/users/me/meetings", params={
                "type": "scheduled",
                "page_size": 100
            })
            scheduled_meetings = data.get("meetings", [])
            logger.info(f"Found {len(scheduled_meetings)} scheduled meetings")

            # For each scheduled meeting, get past instances within date range
            for meeting in scheduled_meetings:
                meeting_id = meeting.get("id")
                meeting_topic = meeting.get("topic", "Unknown Meeting")

                try:
                    # Get past instances
                    instances_data = self._make_request(f"/past_meetings/{meeting_id}/instances")
                    instances = instances_data.get("meetings", [])

                    for instance in instances:
                        start_time_str = instance.get("start_time", "")
                        if not start_time_str:
                            continue

                        try:
                            # Parse datetime and check if within range
                            start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%SZ")
                            if start_time < cutoff_date.replace(tzinfo=None):
                                continue

                            # Try to get AI summary for this instance
                            instance_uuid = instance.get("uuid")
                            if instance_uuid:
                                summary = self.get_meeting_summary(instance_uuid)
                                if summary:
                                    # Use pre-formatted summary_content if available, otherwise build it
                                    summary_text = summary.get("summary_content", "")

                                    if not summary_text:
                                        # Build summary from components
                                        summary_overview = summary.get("summary_overview", "")
                                        summary_details = summary.get("summary_details", [])
                                        next_steps = summary.get("next_steps", [])

                                        summary_text = f"{summary_overview}\n\n"

                                        if summary_details:
                                            summary_text += "Details:\n"
                                            for detail in summary_details:
                                                label = detail.get('label', '')
                                                text = detail.get('summary', '')
                                                summary_text += f"\n{label}:\n{text}\n"
                                            summary_text += "\n"

                                        if next_steps:
                                            summary_text += "Next Steps:\n"
                                            for step in next_steps:
                                                summary_text += f"- {step}\n"

                                    if summary_text.strip():
                                        header = f"=== Zoom Meeting: {meeting_topic} ({start_time_str}) ==="
                                        formatted_text = f"{header}\n\n{summary_text}"

                                        # Build URL to the meeting
                                        source_url = self._build_meeting_url(meeting_id)

                                        content.append({
                                            "text": formatted_text,
                                            "source_url": source_url,
                                            "source": "zoom",
                                            "metadata": {
                                                "meeting_id": meeting_id,
                                                "instance_uuid": instance_uuid,
                                                "topic": meeting_topic,
                                                "start_time": start_time_str,
                                            }
                                        })
                                        logger.debug(f"Retrieved summary for {meeting_topic}")

                        except ValueError:
                            # Skip instances with invalid date format
                            continue

                except Exception as e:
                    # No past instances for this meeting, or other error
                    logger.debug(f"No past instances or summaries for {meeting_topic}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching meeting summaries: {e}")

        logger.info(f"Retrieved summaries from {len(content)} Zoom meetings")
        return content

    def test_connection(self) -> bool:
        """
        Test Zoom API connection and credentials.

        Returns:
            True if connection successful
        """
        try:
            token = self._get_access_token()
            # Try to get user info
            self._make_request("/users/me")
            logger.info("✓ Zoom API connection successful")
            return True
        except Exception as e:
            logger.error(f"✗ Zoom API connection failed: {e}")
            return False
