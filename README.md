# Todo Aggregator

AI-powered system that aggregates todos from Slack, Zoom, Gmail, and Notion with intelligent deduplication, priority scoring, and cross-platform completion tracking.

## Overview

This system uses Claude Opus 4.5 to:
- Extract todos from multiple platforms (both explicit assignments and implicit commitments)
- Deduplicate todos mentioned across different tools
- Detect when todos are completed in any platform
- Score priority and categorize todos automatically
- Infer due dates from relative references ("by Friday", "next week")
- Maintain a canonical todo list in Notion with clickable source links

## Deployment Options

### Option 1: Hosted API + Zapier (Recommended for Teams)

The API is deployed to GCP Cloud Run and can be triggered via Zapier webhooks:

- **API URL**: `https://todo-aggregator-908833572352.us-central1.run.app`
- **Endpoints**:
  - `POST /run` - Run the aggregator for a user
  - `GET /health` - Health check

See [Multi-User Setup](#multi-user-setup-with-zapier) below.

### Option 2: GitHub Actions (Single User)

Runs automatically via GitHub Actions on a schedule. See [GitHub Actions](#github-actions-automated-scheduling) below.

### Option 3: Local Execution

Run manually with `python src/orchestrator.py`.

## Architecture

```
Slack API  ──┐
Gmail API  ──┼──→ Claude Opus 4.5 ──→ Notion Database
Zoom API   ──┘    (extraction,         (canonical state)
                   deduplication,
                   intelligence)
```

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/claysader-arch/todo-aggregator.git
cd todo-aggregator
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | From https://console.anthropic.com |
| `NOTION_API_KEY` | Yes | From https://www.notion.so/my-integrations |
| `NOTION_DATABASE_ID` | Yes | Your todo database ID |
| `SLACK_USER_TOKEN` | Optional | User token (xoxp-...) for Slack messages |
| `ZOOM_ACCOUNT_ID` | Optional | For Zoom meeting summaries |
| `ZOOM_CLIENT_ID` | Optional | Server-to-Server OAuth |
| `ZOOM_CLIENT_SECRET` | Optional | Server-to-Server OAuth |
| `GMAIL_CLIENT_ID` | Optional | From Google Cloud Console |
| `GMAIL_CLIENT_SECRET` | Optional | OAuth credentials |
| `GMAIL_REFRESH_TOKEN` | Optional | Generated via setup script |

### 3. Set Up Notion Database

Create a Notion database with these properties:

| Property | Type | Description |
|----------|------|-------------|
| Task | Title | Todo description |
| Status | Select | Open / In Progress / Done / Done? |
| Source | Multi-select | slack / gmail / zoom / notion |
| Source URL | URL | Clickable link to original message |
| Assigned To | Rich text | Who owns this todo |
| Due Date | Date | Extracted or inferred date |
| Priority | Select | High / Medium / Low |
| Category | Multi-select | follow-up, review, meeting, etc. |
| Created | Created time | When first detected |
| Completed | Date | When marked done |
| Confidence | Number | AI confidence score (0-1) |
| Dedupe Hash | Text | For detecting duplicates |

Share the database with your Notion integration.

### 4. Run Locally

```bash
python src/orchestrator.py
```

### 5. Set Up Gmail OAuth (if using Gmail)

```bash
python scripts/gmail_oauth_setup.py /path/to/google-credentials.json
```

Follow the prompts to authorize and get your refresh token.

## GitHub Actions (Automated Scheduling)

The aggregator runs automatically via GitHub Actions.

### Configure Secrets

Go to your repo **Settings** → **Secrets and variables** → **Actions**:

**Secrets** (required):
- `ANTHROPIC_API_KEY`
- `NOTION_API_KEY`
- `NOTION_DATABASE_ID`

**Secrets** (optional, per integration):
- `SLACK_USER_TOKEN`
- `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`
- `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`
- `NOTION_MEETINGS_DATABASE_ID`

**Variables** (non-sensitive):
- `MY_NAME` - Your name variations for filtering (e.g., `Clay,clay,Clay Sader`)

### Schedule

By default, runs daily at 7am PT. Edit `.github/workflows/todo-aggregator.yml` to change.

### Manual Run

Go to **Actions** → **Todo Aggregator** → **Run workflow**

## Project Structure

```
todo-aggregator/
├── src/
│   ├── orchestrator.py              # Main entry point
│   ├── config.py                    # Configuration management
│   ├── mcp_clients/
│   │   ├── notion_client.py         # Notion API client
│   │   ├── slack_client.py          # Slack API client
│   │   ├── gmail_client.py          # Gmail API client
│   │   └── zoom_client.py           # Zoom API client
│   └── processors/
│       └── claude_processor.py      # AI extraction & deduplication
├── scripts/
│   └── gmail_oauth_setup.py         # Gmail OAuth helper
├── tests/
│   ├── test_slack_connection.py
│   ├── test_gmail_connection.py
│   └── ...
├── .github/
│   └── workflows/
│       └── todo-aggregator.yml      # GitHub Actions config
├── .env.example                     # Environment template
└── requirements.txt
```

## Features

### Intelligence Layer (Phase 5)
- **Priority Scoring**: Detects urgency keywords (urgent, ASAP, blocker, P0)
- **Category Tagging**: Auto-categorizes (follow-up, review, meeting, technical, etc.)
- **Due Date Inference**: Converts "by Friday" or "next week" to actual dates

### Source URLs (Phase 6)
- Every todo links back to its original message
- Click to jump directly to Slack conversation, Gmail thread, or Zoom meeting

### Zoom Integration
- **API meetings**: Fetches AI summaries from meetings you host via Zoom API
- **Email meetings**: Meetings you attend (hosted by others) are captured via Zoom AI Companion emails
- Zoom emails are automatically re-attributed from "gmail" to "zoom" source
- HTML emails are parsed using BeautifulSoup for accurate text extraction

### Slack Hybrid Approach (Performance Optimized)
- **Two-bucket strategy** for ~12x faster performance:
  - Bucket 1: DMs via Search API (`is:dm`) - ~10 seconds
  - Bucket 2: Only channels where user actively participated - ~60 seconds
- **Total: ~70 seconds** vs 15+ minutes with full scan
- Requires `search:read` scope for optimal performance
- Falls back to full scan if search scope unavailable

### Slack Thread Support
- Fetches both channel messages and thread replies
- Each message gets its own trackable source URL
- Rate limiting protection with exponential backoff

### Source Context Comments
- New todos get a comment with the original source context
- Shows the exact message/email that generated the todo
- Makes it easy to understand why a todo was created without clicking through

### Configurable Filtering

```bash
# In .env
MY_NAME=Clay,clay,Clay Sader
FILTER_MY_TODOS_ONLY=true
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `FILTER_MY_TODOS_ONLY` | `true` | Only include todos assigned to you |
| `MY_NAME` | - | Comma-separated name variations for todo ownership |
| `MY_SLACK_USERNAME` | - | Your Slack display name (for accurate extraction) |
| `MY_EMAIL` | - | Your email address (for Gmail matching) |
| `GMAIL_LOOKBACK_DAYS` | `1` | Days of email history to scan |
| `ENABLE_PRIORITY_SCORING` | `true` | AI priority detection |
| `ENABLE_CATEGORY_TAGGING` | `true` | AI categorization |
| `ENABLE_DUE_DATE_INFERENCE` | `true` | Relative date parsing |
| `HIGH_PRIORITY_KEYWORDS` | `urgent,asap,critical,today,p0,immediately,blocker` | Priority triggers |
| `COMPLETION_CONFIDENCE_THRESHOLD` | `0.85` | Confidence level for auto-completing (below = "Done?") |

## Development

### Run Tests

```bash
pytest
```

### Format Code

```bash
black src/
ruff check src/
```

### View Logs

- Console output during execution
- GitHub Actions: Download from **Artifacts** after each run

## Troubleshooting

### "Missing required configuration"
Check that required secrets are set in GitHub repo settings (not environment secrets).

### Gmail authentication errors
Re-run `scripts/gmail_oauth_setup.py` to refresh your token.

### Slack URLs have spaces
Fixed in v1.0 - uses `team_domain` instead of `team` for workspace name.

### Todos link to wrong messages
Fixed in v1.0 - uses `source_id` tracking instead of fuzzy matching.

### Notion comments show 403 Forbidden
The Notion integration needs "Insert comments" capability. Go to https://www.notion.so/my-integrations, select your integration, and enable "Insert comments" under Capabilities. Comments are optional - completion detection still works without them.

### Zoom meetings not appearing
The Zoom API only returns meetings **you hosted**. Meetings you attended (hosted by others) are captured via Zoom AI Companion emails instead. Make sure Gmail integration is enabled to capture these.

## Multi-User Setup with Zapier

For distributing the aggregator to multiple users in your organization.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Zapier (per user)                        │
│                                                             │
│  Trigger: Schedule (daily 7am PT)                           │
│      ↓                                                      │
│  Action: Webhook POST to Cloud Run API                      │
│     Headers: X-API-Secret: {{secret}}                       │
│     Body: { user credentials }                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Cloud Run API (shared)                         │
│                                                             │
│  POST /run                                                  │
│  ├── Fetch Slack messages                                   │
│  ├── Fetch Gmail threads                                    │
│  ├── Extract todos via Claude                               │
│  ├── Deduplicate against existing                           │
│  ├── Detect completed todos                                 │
│  └── Write to user's Notion database                        │
└─────────────────────────────────────────────────────────────┘
```

### Credential Types

| Credential | Shared/Per-User | Where Stored |
|------------|-----------------|--------------|
| `ANTHROPIC_API_KEY` | Shared | Cloud Run env |
| `GMAIL_CLIENT_ID` | Shared | Cloud Run env |
| `GMAIL_CLIENT_SECRET` | Shared | Cloud Run env |
| `API_SECRET` | Shared | Cloud Run env + Zapier |
| `slack_token` | Per-user | Zapier webhook body |
| `gmail_refresh_token` | Per-user | Zapier webhook body |
| `notion_api_key` | Per-user | Zapier webhook body |
| `notion_database_id` | Per-user | Zapier webhook body |

### User Onboarding (~15 min per user)

#### Step 1: Notion Setup (5 min)

1. User duplicates your Notion template database
2. User creates a Notion integration at https://www.notion.so/my-integrations
   - Give it a name like "Todo Aggregator"
   - Copy the **Internal Integration Secret**
3. User shares their database with the integration (click Share → Invite → select integration)
4. Get the database ID from the URL: `notion.so/[workspace]/[DATABASE_ID]?v=...`

User provides you: **Notion API Key** + **Database ID**

#### Step 2: Slack Setup (2 min)

1. Go to https://api.slack.com/apps (your company's Slack app)
2. User OAuth Token is under **OAuth & Permissions** → **User OAuth Token** (starts with `xoxp-`)

User provides you: **Slack User Token**

#### Step 3: Gmail Setup (5 min)

1. User runs the OAuth setup script:
   ```bash
   python scripts/gmail_oauth_setup.py /path/to/google-credentials.json
   ```
2. Browser opens, user authorizes with their Google account
3. Script outputs the refresh token

User provides you: **Gmail Refresh Token**

#### Step 4: Create Zapier Zap (2 min)

1. **Trigger**: Schedule by Zapier
   - Every Day at 7:00 AM (or preferred time)

2. **Action**: Webhooks by Zapier → POST
   - **URL**: `https://todo-aggregator-908833572352.us-central1.run.app/run`
   - **Payload Type**: JSON
   - **Headers**:
     ```
     X-API-Secret: [your API secret]
     Content-Type: application/json
     ```
   - **Data**:
     ```json
     {
       "slack_token": "xoxp-user-token",
       "gmail_refresh_token": "user-refresh-token",
       "notion_api_key": "secret_user-notion-key",
       "notion_database_id": "user-database-id",
       "notion_meetings_db_id": "",
       "user_name": "FirstName",
       "user_email": "user@company.com",
       "user_slack_username": "User Name"
     }
     ```

3. Turn on the Zap

### Notion Database Template

Create a template database with these properties:

| Property | Type | Options |
|----------|------|---------|
| Task | Title | - |
| Status | Select | Open, In Progress, Done, Done? |
| Source | Multi-select | slack, gmail, zoom, notion |
| Source URL | URL | - |
| Assigned To | Rich text | - |
| Due Date | Date | - |
| Priority | Select | high, medium, low |
| Category | Multi-select | follow-up, review, meeting, technical, discussion, approval |
| Created | Created time | - |
| Completed | Date | - |
| Confidence | Number | Format: Percent |
| Dedupe Hash | Text | - |

### API Reference

#### POST /run

Run the todo aggregator for a user.

**Headers:**
- `X-API-Secret`: Required. Shared API secret.
- `Content-Type`: `application/json`

**Body:**
```json
{
  "slack_token": "xoxp-...",
  "gmail_refresh_token": "1//...",
  "notion_api_key": "secret_...",
  "notion_database_id": "abc123...",
  "notion_meetings_db_id": "",
  "user_name": "Clay",
  "user_email": "clay@company.com",
  "user_slack_username": "Clay Sader"
}
```

**Response:**
```json
{
  "created": 3,
  "skipped": 8,
  "completed": 2,
  "duration_seconds": 180.5
}
```

#### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-12-04T12:00:00.000000"
}
```

### Updating the Deployment

When you make code changes:

```bash
# Build and deploy via Cloud Build
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/todo-aggregator-480119/todo-aggregator/api:latest

# Deploy to Cloud Run
gcloud run deploy todo-aggregator \
  --image us-central1-docker.pkg.dev/todo-aggregator-480119/todo-aggregator/api:latest \
  --region us-central1 \
  --port 8000
```

### Viewing Logs

```bash
# Recent logs
gcloud run services logs read todo-aggregator --region us-central1

# Or view in GCP Console
# https://console.cloud.google.com/run/detail/us-central1/todo-aggregator/logs?project=todo-aggregator-480119
```

## License

MIT
