"""Notion MCP client for todo database operations."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests
from config import Config

logger = logging.getLogger(__name__)


class NotionClient:
    """Client for interacting with Notion database via Notion API."""

    def __init__(self):
        """Initialize Notion client with API credentials."""
        self.api_key = Config.NOTION_API_KEY
        self.database_id = Config.NOTION_DATABASE_ID
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    def query_database(
        self,
        filter_dict: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query Notion database for existing todos.

        Args:
            filter_dict: Optional filter criteria
            sorts: Optional sort configuration

        Returns:
            List of todo items from database
        """
        url = f"{self.base_url}/databases/{self.database_id}/query"

        payload = {}
        if filter_dict:
            payload["filter"] = filter_dict
        if sorts:
            payload["sorts"] = sorts

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()

            todos = []
            for page in data.get("results", []):
                todo = self._parse_page(page)
                todos.append(todo)

            logger.info(f"Retrieved {len(todos)} todos from Notion")
            return todos

        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying Notion database: {e}")
            raise

    def create_page(self, todo: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new todo page in Notion database.

        Args:
            todo: Todo object with properties

        Returns:
            Created page data
        """
        url = f"{self.base_url}/pages"

        properties = self._build_properties(todo)
        payload = {"parent": {"database_id": self.database_id}, "properties": properties}

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()

            logger.info(f"Created todo in Notion: {todo.get('task', 'Untitled')}")
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating Notion page: {e}")
            if hasattr(response, 'text'):
                logger.error(f"Response: {response.text}")
            raise

    def update_page(self, page_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing todo page in Notion.

        Args:
            page_id: Notion page ID to update
            updates: Dictionary of properties to update

        Returns:
            Updated page data
        """
        url = f"{self.base_url}/pages/{page_id}"

        properties = self._build_properties(updates)
        payload = {"properties": properties}

        try:
            response = requests.patch(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()

            logger.info(f"Updated todo in Notion: {page_id}")
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating Notion page: {e}")
            raise

    def add_comment(self, page_id: str, comment_text: str) -> Dict[str, Any]:
        """
        Add a comment to a Notion page.

        Args:
            page_id: Notion page ID to comment on
            comment_text: Text content of the comment

        Returns:
            Created comment data
        """
        url = f"{self.base_url}/comments"

        payload = {
            "parent": {"page_id": page_id},
            "rich_text": [{"type": "text", "text": {"content": comment_text}}],
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()

            logger.debug(f"Added comment to Notion page: {page_id}")
            return data

        except requests.exceptions.RequestException as e:
            logger.warning(f"Error adding comment to Notion page {page_id}: {e}")
            # Don't raise - comments are nice-to-have, not critical
            return {}

    def _parse_page(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Notion page into simplified todo object.

        Args:
            page: Raw Notion page data

        Returns:
            Simplified todo dictionary
        """
        props = page.get("properties", {})

        def get_title(prop):
            """Extract title text."""
            if not prop or prop.get("type") != "title":
                return ""
            title_list = prop.get("title", [])
            return title_list[0].get("plain_text", "") if title_list else ""

        def get_rich_text(prop):
            """Extract rich text."""
            if not prop or prop.get("type") != "rich_text":
                return ""
            text_list = prop.get("rich_text", [])
            return text_list[0].get("plain_text", "") if text_list else ""

        def get_select(prop):
            """Extract select value."""
            if not prop or prop.get("type") != "select":
                return None
            select = prop.get("select")
            return select.get("name") if select else None

        def get_multi_select(prop):
            """Extract multi-select values."""
            if not prop or prop.get("type") != "multi_select":
                return []
            return [item.get("name") for item in prop.get("multi_select", [])]

        def get_url(prop):
            """Extract URL value."""
            if not prop or prop.get("type") != "url":
                return None
            return prop.get("url")

        def get_date(prop):
            """Extract date value."""
            if not prop or prop.get("type") != "date":
                return None
            date = prop.get("date")
            return date.get("start") if date else None

        def get_number(prop):
            """Extract number value."""
            if not prop or prop.get("type") != "number":
                return None
            return prop.get("number")

        def get_checkbox(prop):
            """Extract checkbox value."""
            if not prop or prop.get("type") != "checkbox":
                return False
            return prop.get("checkbox", False)

        return {
            "id": page.get("id"),
            "task": get_title(props.get("**Task**") or props.get("Task")),
            "status": get_select(props.get("**Status**") or props.get("Status")),
            "source": get_multi_select(props.get("**Source**") or props.get("Source")),
            "source_url": get_url(props.get("**Source URL**") or props.get("Source URL")),
            "due_date": get_date(props.get("**Due Date**") or props.get("Due Date")),
            "completed": get_date(props.get("**Completed**") or props.get("Completed")),
            "confidence": get_number(props.get("**Confidence**") or props.get("Confidence")),
            "dedupe_hash": get_rich_text(props.get("**Dedupe Hash**") or props.get("Dedupe Hash")),
            # Phase 5: New fields
            "priority": get_select(props.get("**Priority**") or props.get("Priority")),
            "category": get_multi_select(props.get("**Category**") or props.get("Category")),
            "recurring": get_checkbox(props.get("**Recurring**") or props.get("Recurring")),
            "created_time": page.get("created_time"),
            "last_edited_time": page.get("last_edited_time"),
        }

    def _build_properties(self, todo: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build Notion properties object from todo dictionary.

        Args:
            todo: Todo dictionary

        Returns:
            Notion properties object
        """
        properties = {}

        if "task" in todo:
            properties["**Task**"] = {"title": [{"text": {"content": todo["task"]}}]}

        if "status" in todo:
            properties["**Status**"] = {"select": {"name": todo["status"]}}

        if "source" in todo:
            # Ensure source is a list
            sources = todo["source"] if isinstance(todo["source"], list) else [todo["source"]]
            properties["**Source**"] = {"multi_select": [{"name": s} for s in sources]}

        if "source_url" in todo:
            properties["**Source URL**"] = {"url": todo["source_url"]}

        if "due_date" in todo and todo["due_date"]:
            properties["**Due Date**"] = {"date": {"start": todo["due_date"]}}

        if "completed" in todo and todo["completed"]:
            properties["**Completed**"] = {"date": {"start": todo["completed"]}}

        if "confidence" in todo:
            properties["**Confidence**"] = {"number": todo["confidence"]}

        if "dedupe_hash" in todo:
            properties["**Dedupe Hash**"] = {"rich_text": [{"text": {"content": todo["dedupe_hash"]}}]}

        # Phase 5: Priority (Select property)
        if "priority" in todo and todo["priority"]:
            properties["**Priority**"] = {"select": {"name": todo["priority"].capitalize()}}

        # Phase 5: Category (Multi-select property)
        if "category" in todo and todo["category"]:
            categories = todo["category"] if isinstance(todo["category"], list) else [todo["category"]]
            properties["**Category**"] = {"multi_select": [{"name": cat} for cat in categories]}

        # Phase 5: Recurring (Checkbox property - for future use)
        if "recurring" in todo:
            properties["**Recurring**"] = {"checkbox": bool(todo["recurring"])}

        return properties

    def get_open_todos(self) -> List[Dict[str, Any]]:
        """
        Get all open (not completed) todos from database.

        Returns:
            List of open todos
        """
        # Try both with and without markdown formatting
        try:
            filter_dict = {
                "or": [
                    {"property": "**Status**", "select": {"equals": "Open"}},
                    {"property": "**Status**", "select": {"equals": "In Progress"}},
                ]
            }
            return self.query_database(filter_dict=filter_dict)
        except:
            # Fallback to plain property name
            filter_dict = {
                "or": [
                    {"property": "Status", "select": {"equals": "Open"}},
                    {"property": "Status", "select": {"equals": "In Progress"}},
                ]
            }
            return self.query_database(filter_dict=filter_dict)

    def get_all_todos(self) -> List[Dict[str, Any]]:
        """
        Get all todos from database.

        Returns:
            List of all todos
        """
        return self.query_database()

    def get_recent_meetings(self, days: int = 1) -> List[Dict[str, Any]]:
        """
        Query recent meeting notes from Notion AI meetings database.

        Requires NOTION_MEETINGS_DATABASE_ID to be configured.
        Users must set up Notion Calendar > Matter Intelligence to redirect
        AI meeting notes to a user-controlled database.

        Args:
            days: Number of days to look back (default: 1)

        Returns:
            List of meeting notes formatted for Claude processing
        """
        meetings_db_id = Config.NOTION_MEETINGS_DATABASE_ID
        if not meetings_db_id:
            logger.debug("NOTION_MEETINGS_DATABASE_ID not configured, skipping meetings collection")
            return []

        from datetime import timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        url = f"{self.base_url}/databases/{meetings_db_id}/query"
        payload = {
            "filter": {
                "timestamp": "created_time",
                "created_time": {"on_or_after": cutoff_date}
            },
            "sorts": [{"timestamp": "created_time", "direction": "descending"}]
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()

            meetings = []
            for page in data.get("results", []):
                meeting = self._parse_meeting_page(page)
                if meeting:
                    meetings.append(meeting)

            logger.info(f"Retrieved {len(meetings)} meeting notes from Notion")
            return meetings

        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying Notion meetings database: {e}")
            return []

    def _parse_meeting_page(self, page: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a meeting notes page and fetch its content.

        Args:
            page: Raw Notion page data

        Returns:
            Meeting note with text content formatted for Claude, or None if empty
        """
        page_id = page.get("id")
        props = page.get("properties", {})

        # Get the meeting title (Name property)
        title = ""
        for prop_name in ["Name", "**Name**", "Title", "**Title**"]:
            prop = props.get(prop_name)
            if prop and prop.get("type") == "title":
                title_list = prop.get("title", [])
                if title_list:
                    title = title_list[0].get("plain_text", "")
                    break

        # Fetch page content (blocks)
        content = self._get_page_content(page_id)
        if not content.strip():
            logger.debug(f"Skipping empty meeting page: {title or page_id}")
            return None

        # Format for Claude processing
        formatted_text = f"=== Notion Meeting: {title} ===\n{content}"

        return {
            "text": formatted_text,
            "source_url": f"https://notion.so/{page_id.replace('-', '')}",
            "source": "notion-meeting",
            "metadata": {
                "page_id": page_id,
                "title": title,
                "created_time": page.get("created_time"),
            }
        }

    def _get_page_content(self, page_id: str) -> str:
        """
        Fetch all text content from a Notion page's blocks.

        Args:
            page_id: Notion page ID

        Returns:
            Concatenated text content from all blocks
        """
        return self._get_block_content(page_id)

    def _get_block_content(self, block_id: str, depth: int = 0) -> str:
        """
        Recursively fetch text content from blocks and their children.

        Args:
            block_id: Notion block or page ID
            depth: Current recursion depth (max 3 levels)

        Returns:
            Concatenated text content from all blocks
        """
        if depth > 3:  # Prevent infinite recursion
            return ""

        url = f"{self.base_url}/blocks/{block_id}/children"
        content_parts = []

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            for block in data.get("results", []):
                # Extract text from this block
                text = self._extract_block_text(block)
                if text:
                    content_parts.append(text)

                # Recursively get children if they exist (skip unsupported blocks)
                if block.get("has_children") and block.get("type") != "unsupported":
                    child_content = self._get_block_content(block["id"], depth + 1)
                    if child_content:
                        content_parts.append(child_content)

            return "\n".join(content_parts)

        except requests.exceptions.RequestException as e:
            logger.debug(f"Could not fetch block content (may be unsupported block type): {e}")
            return ""

    def _extract_block_text(self, block: Dict[str, Any]) -> str:
        """
        Extract text content from a Notion block.

        Args:
            block: Notion block data

        Returns:
            Text content from the block
        """
        block_type = block.get("type", "")
        block_data = block.get(block_type, {})

        # Handle rich_text blocks (paragraph, heading, bulleted_list_item, etc.)
        if "rich_text" in block_data:
            texts = []
            for text_item in block_data.get("rich_text", []):
                plain_text = text_item.get("plain_text", "")
                if plain_text:
                    texts.append(plain_text)
            return " ".join(texts)

        # Handle toggle blocks (may contain nested content)
        if block_type == "toggle":
            texts = []
            for text_item in block_data.get("rich_text", []):
                plain_text = text_item.get("plain_text", "")
                if plain_text:
                    texts.append(plain_text)
            return " ".join(texts)

        return ""
