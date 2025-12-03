# Phase 6: Productization & Integration Improvements

## Overview

Phase 6 focuses on making the todo aggregator production-ready:
- **Hosting** - Consistent automated execution
- **Staff Rollout** - Easy setup for team members
- **Source URLs** - Clickable links back to original messages
- **Integration Improvements** - Better Zoom/Notion handling

---

## 6.1 Source URL Integration

### Problem
Infrastructure exists (Notion has `**Source URL**` field, orchestrator passes it) but URLs aren't being captured. The MCP clients return `List[str]` formatted text, losing the metadata needed to construct URLs.

### Current State
```
Slack/Gmail/Zoom clients
    ↓
get_*_content() → List[str] (formatted text only, NO URLs)
    ↓
Claude extracts todos → source_url is None
    ↓
Notion receives empty source_url
```

### Solution
Return structured data from clients instead of just text strings.

### URL Formats by Platform
| Platform | URL Format | Data Needed |
|----------|-----------|-------------|
| Slack | `https://{workspace}.slack.com/archives/{channel_id}/p{ts_no_dot}` | workspace, channel_id, message ts |
| Gmail | `https://mail.google.com/mail/u/0/?msgid={message_id}` | message_id |
| Zoom | `https://zoom.us/rec/play/{recording_id}` | recording_id or meeting join link |

### Implementation Steps

#### Step 1: Modify Client Return Types
Change from `List[str]` to `List[Dict[str, Any]]`:
```python
# New return format
{
    "text": "Formatted message content for Claude",
    "source_url": "https://...",
    "source": "slack",  # or gmail, zoom
    "metadata": {
        "channel_id": "C123",
        "ts": "1234567890.123456",
        # ... platform-specific data
    }
}
```

#### Step 2: Slack Client Changes
**File**: `src/mcp_clients/slack_client.py`

1. Add workspace name retrieval:
```python
def get_workspace_name(self) -> str:
    """Get workspace name from Slack API."""
    response = requests.post(
        "https://slack.com/api/auth.test",
        headers={"Authorization": f"Bearer {self.token}"}
    )
    return response.json().get("team", "workspace")
```

2. Build message URLs:
```python
def _build_message_url(self, channel_id: str, ts: str) -> str:
    """Build permalink to Slack message."""
    ts_no_dot = ts.replace(".", "")
    return f"https://{self.workspace}.slack.com/archives/{channel_id}/p{ts_no_dot}"
```

#### Step 3: Gmail Client Changes
**File**: `src/mcp_clients/gmail_client.py`

Build message URLs:
```python
def _build_message_url(self, message_id: str) -> str:
    """Build URL to open Gmail message."""
    return f"https://mail.google.com/mail/u/0/?msgid={message_id}"
```

#### Step 4: Zoom Client Changes
**File**: `src/mcp_clients/zoom_client.py`

Build meeting URLs (prefer recording if available):
```python
def _build_meeting_url(self, meeting_id: str, recording_id: str = None) -> str:
    """Build URL to Zoom meeting/recording."""
    if recording_id:
        return f"https://zoom.us/rec/play/{recording_id}"
    return f"https://zoom.us/j/{meeting_id}"
```

#### Step 5: Update Orchestrator
**File**: `src/orchestrator.py`

Handle structured data:
```python
def collect_todos(...) -> dict:
    raw_content = {
        "slack": [],  # Now List[Dict] instead of List[str]
        "gmail": [],
        "zoom": [],
    }
    # ... rest of collection
```

#### Step 6: Update Claude Processor
**File**: `src/processors/claude_processor.py`

1. Accept metadata alongside text
2. After extraction, map source_url to todos based on source_context matching

---

## 6.2 Zoom Emails via Gmail

### Finding
Zoom AI Companion summary emails ARE captured by Gmail integration, but attributed as "gmail" source instead of "zoom".

### Solution
Add sender detection to re-attribute Zoom emails.

### Implementation

#### Step 1: Add Config
**File**: `src/config.py`
```python
# Zoom email senders (comma-separated)
ZOOM_EMAIL_SENDERS: str = os.getenv(
    "ZOOM_EMAIL_SENDERS",
    "meetings-noreply@zoom.us,no-reply@zoom.us,noreply@zoom.us"
)
```

#### Step 2: Detect Zoom Emails
**File**: `src/mcp_clients/gmail_client.py`

In `get_gmail_content()`, check sender:
```python
from_addr = self._get_header(headers, "From").lower()
zoom_senders = [s.strip().lower() for s in Config.ZOOM_EMAIL_SENDERS.split(",")]

source = "gmail"
if any(zoom_sender in from_addr for zoom_sender in zoom_senders):
    source = "zoom"  # Re-attribute to Zoom
```

#### Step 3: Pass Source to Return Data
Include `source` in the structured return data so Claude processor can use correct attribution.

---

## 6.3 Notion Meeting Notes Integration

### Finding
Notion's built-in AI meeting notes page is system-owned and cannot be queried via the API directly. However, Notion Calendar allows redirecting AI meeting notes to a user-controlled database.

### Solution: Notion Calendar + Matter Intelligence

Redirect Notion AI meeting notes to a personal database that the todo aggregator can access.

### User Setup Steps (Required)

1. **Enable Notion Calendar** - Connect Notion Calendar to your workspace
2. **Create a personal meeting summary database** - Create a new database anywhere in your Notion workspace
3. **Configure Matter Intelligence**:
   - Open Notion Calendar settings
   - Navigate to **Matter Intelligence** section
   - Set the **default database for AI notes** to your personal meeting summary database
4. **New AI meeting notes** will now be created in your user-controlled database
5. **Grant API access** - Share the database with your Notion integration (same as the Todos database)

### Implementation

#### Step 1: Add Config
**File**: `src/config.py`
```python
# Optional meetings database (for Notion AI meeting notes)
NOTION_MEETINGS_DATABASE_ID: str = os.getenv("NOTION_MEETINGS_DATABASE_ID", "")
```

#### Step 2: Query Meetings
**File**: `src/mcp_clients/notion_client.py`

Add method to query meetings database:
```python
def get_recent_meetings(self, days: int = 1) -> List[Dict[str, Any]]:
    """Query recent meeting notes from meetings database."""
    if not Config.NOTION_MEETINGS_DATABASE_ID:
        return []

    # Query meetings database for pages created in last N days
    # Extract page content (AI-generated meeting summary/transcript)
    # Return formatted for Claude processing with source="notion-meeting"
```

#### Step 3: Update Orchestrator
Collect from meetings database and attribute as "notion-meeting" source:
```python
if Config.NOTION_MEETINGS_DATABASE_ID:
    meeting_content = notion.get_recent_meetings(days=1)
    raw_content["notion"] = meeting_content
```

### API Limitation (as of Dec 2025)
**Important**: Notion's AI transcription blocks are currently marked as "unsupported" in the API:
```
"Block type transcription is not supported via the API."
```

The meeting pages exist and contain AI-generated summaries, but the content cannot be read via the public API. This integration is ready for when Notion exposes these block types.

**Current workarounds**:
1. Manually copy meeting summaries into a "Summary" rich text property
2. Use Zapier/Make to copy visible text into a property
3. Wait for Notion API to support transcription blocks

### Database Schema
Notion AI meeting notes pages are created automatically with:
- **Name** (Title) - Meeting title
- **Page content** - AI-generated summary and transcript (not API accessible yet)

---

## 6.4 Hosting & Scheduling

### Goal
Run the aggregator consistently without manual execution.

### Option A: GitHub Actions (Recommended - Free)

#### Setup Steps

1. Create workflow file:
**File**: `.github/workflows/aggregate-todos.yml`
```yaml
name: Todo Aggregator
on:
  schedule:
    # Run at 9am and 5pm EST on weekdays
    - cron: '0 14,22 * * 1-5'
  workflow_dispatch:  # Allow manual trigger

jobs:
  aggregate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run aggregator
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          NOTION_API_KEY: ${{ secrets.NOTION_API_KEY }}
          NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
          SLACK_USER_TOKEN: ${{ secrets.SLACK_USER_TOKEN }}
          GMAIL_CLIENT_ID: ${{ secrets.GMAIL_CLIENT_ID }}
          GMAIL_CLIENT_SECRET: ${{ secrets.GMAIL_CLIENT_SECRET }}
          GMAIL_REFRESH_TOKEN: ${{ secrets.GMAIL_REFRESH_TOKEN }}
          ZOOM_ACCOUNT_ID: ${{ secrets.ZOOM_ACCOUNT_ID }}
          ZOOM_CLIENT_ID: ${{ secrets.ZOOM_CLIENT_ID }}
          ZOOM_CLIENT_SECRET: ${{ secrets.ZOOM_CLIENT_SECRET }}
          MY_NAME: ${{ secrets.MY_NAME }}
        run: python src/orchestrator.py
```

2. Add secrets in GitHub repo settings → Secrets → Actions

3. Test with manual trigger (workflow_dispatch)

#### Pros & Cons
| Pros | Cons |
|------|------|
| Free tier (2000 min/month) | 6-hour max runtime |
| Reliable scheduling | Secrets in GitHub |
| Easy to debug with logs | Cold start each run |
| Manual trigger option | |

### Option B: Railway/Render (~$5/month)

#### Railway Setup
1. Connect GitHub repo to Railway
2. Add environment variables in dashboard
3. Create cron job service with schedule

#### Pros & Cons
| Pros | Cons |
|------|------|
| Simpler setup | ~$5/month cost |
| Better logs/monitoring | Another service to manage |
| Persistent environment | |

### Option C: Local Cron (Development)

Add to crontab:
```bash
# Run at 9am and 5pm daily
0 9,17 * * * cd /path/to/todo-aggregator && python src/orchestrator.py >> /var/log/todo-aggregator.log 2>&1
```

---

## 6.5 Staff Rollout & Productization

### Goal
Make it easy for team members to set up their own todo aggregator instance.

### Option A: Notion Config Template (Recommended)

#### Concept
Create a Notion template that includes:
1. **Setup Instructions** page with step-by-step guide
2. **Config** database to store API keys (private)
3. **Todos** database with pre-configured schema

Users duplicate the template, fill in their keys, and the system reads config from Notion.

#### Implementation

##### Step 1: Create NotionConfigClient
**File**: `src/mcp_clients/notion_config_client.py`
```python
class NotionConfigClient:
    """Read configuration from Notion database instead of .env"""

    def __init__(self, config_db_id: str, api_key: str):
        self.config_db_id = config_db_id
        self.api_key = api_key

    def get_config(self) -> Dict[str, str]:
        """Fetch all config values from Notion database."""
        # Query config database
        # Return as dict: {"ANTHROPIC_API_KEY": "sk-...", ...}
```

##### Step 2: Update Config Class
**File**: `src/config.py`
```python
class Config:
    # Try Notion config first, fall back to .env
    _notion_config = None

    @classmethod
    def _load_notion_config(cls):
        if os.getenv("NOTION_CONFIG_DATABASE_ID"):
            client = NotionConfigClient(
                os.getenv("NOTION_CONFIG_DATABASE_ID"),
                os.getenv("NOTION_API_KEY")
            )
            cls._notion_config = client.get_config()

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        """Get config value from Notion or .env"""
        if cls._notion_config and key in cls._notion_config:
            return cls._notion_config[key]
        return os.getenv(key, default)
```

##### Step 3: Config Database Schema
Create Notion database with:
- **Key** (Title) - e.g., "ANTHROPIC_API_KEY"
- **Value** (Rich Text) - the secret value
- **Description** (Rich Text) - what this key is for
- **Required** (Checkbox) - is this required?

##### Step 4: Setup Script
**File**: `scripts/setup_from_notion.py`
```python
"""
Helper script to validate Notion config and test connections.
Usage: python scripts/setup_from_notion.py <config_database_id>
"""
```

#### Template Structure
```
📄 Todo Aggregator Template
├── 📄 Setup Instructions
│   ├── Step 1: Duplicate this template
│   ├── Step 2: Get API keys (links to each service)
│   ├── Step 3: Fill in Config database
│   ├── Step 4: Run setup script
│   └── Step 5: Schedule with GitHub Actions
├── 🗄️ Config (Database - Private)
│   ├── ANTHROPIC_API_KEY
│   ├── NOTION_API_KEY
│   ├── SLACK_USER_TOKEN
│   └── ... etc
└── 🗄️ Todos (Database - Main storage)
    └── Pre-configured with all properties
```

### Option B: Fork + Secrets (Simpler)

For technical teams, simpler approach:
1. Fork the GitHub repo
2. Add secrets in GitHub repo settings
3. Enable GitHub Actions
4. Done

#### Setup Guide for Option B
Create `STAFF_SETUP.md`:
```markdown
# Staff Setup Guide

1. Fork this repo to your GitHub account
2. Go to Settings → Secrets → Actions
3. Add required secrets:
   - ANTHROPIC_API_KEY
   - NOTION_API_KEY
   - NOTION_DATABASE_ID
   - ... etc
4. Go to Actions tab → Enable workflows
5. Manually trigger first run to test
```

---

## 6.6 Additional Improvements (Future)

### Better Cross-Source Deduplication
- Include `source_url` in dedupe hash
- Merge capability: same todo from Slack + Gmail = single entry with both sources listed

### Slack Thread Context
- Currently captures individual messages
- Add parent thread context for replies
- Better understanding of conversation flow

### Gmail Label Support
- Auto-apply label to processed emails (e.g., "Todo-Processed")
- Skip already-labeled emails to avoid reprocessing
- Requires additional Gmail scope: `gmail.modify`

### Web Dashboard (Future Phase)
- Simple Flask/FastAPI web app
- OAuth flows for all services (no manual token setup)
- Multi-tenant support
- Real-time status dashboard

---

## Implementation Priority

| Feature | Priority | Effort | Impact |
|---------|----------|--------|--------|
| GitHub Actions hosting | High | Low | High - consistent execution |
| Source URLs | High | Medium | High - clickable source links |
| Notion config template | High | Medium | High - easy staff rollout |
| Zoom email re-attribution | Medium | Low | Medium - better tracking |
| Notion meetings database | Medium | Medium | Medium - unified meetings |
| Web dashboard | Low | High | Future consideration |

## Recommended Execution Order

1. **6.4 Hosting** - Set up GitHub Actions (1 hour)
2. **6.1 Source URLs** - Fix URL pipeline (half day)
3. **6.5 Staff Rollout** - Create Notion template (half day)
4. **6.2 Zoom Emails** - Add sender detection (1 hour)
5. **6.3 Notion Meetings** - Optional database (2 hours)

---

## Environment Variables Reference

### New in Phase 6
```bash
# Zoom email detection (6.2)
ZOOM_EMAIL_SENDERS=meetings-noreply@zoom.us,no-reply@zoom.us

# Optional meetings database (6.3)
NOTION_MEETINGS_DATABASE_ID=

# Notion-based config (6.5)
NOTION_CONFIG_DATABASE_ID=
```

### All Variables
```bash
# Core (Required)
ANTHROPIC_API_KEY=
NOTION_API_KEY=
NOTION_DATABASE_ID=

# Slack (Optional)
SLACK_USER_TOKEN=

# Gmail (Optional)
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REFRESH_TOKEN=

# Zoom (Optional)
ZOOM_ACCOUNT_ID=
ZOOM_CLIENT_ID=
ZOOM_CLIENT_SECRET=

# Filtering
MY_NAME=
FILTER_MY_TODOS_ONLY=true

# Phase 5: Intelligence
ENABLE_PRIORITY_SCORING=true
ENABLE_CATEGORY_TAGGING=true
ENABLE_DUE_DATE_INFERENCE=true
HIGH_PRIORITY_KEYWORDS=urgent,asap,critical,today,p0,immediately,blocker

# Phase 6: New
ZOOM_EMAIL_SENDERS=meetings-noreply@zoom.us,no-reply@zoom.us
NOTION_MEETINGS_DATABASE_ID=
NOTION_CONFIG_DATABASE_ID=
```
