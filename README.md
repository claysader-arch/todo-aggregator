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

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Cloud Scheduler (7am PT daily)                             │
│  POST /run-all with OIDC auth                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Cloud Run API                                              │
│  ├── POST /run-all       Process all enabled users          │
│  ├── POST /run/{user_id} Process single user               │
│  ├── GET /trigger/{id}/{token} Personal trigger URL        │
│  ├── POST /register      User self-registration            │
│  └── GET /health         Health check                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌──────────────────┐    ┌─────────────────────┐
│  Firestore       │    │  Secret Manager     │
│  users/{uid}     │    │  slack-token-{uid}  │
│  - email         │    │  gmail-token-{uid}  │
│  - name          │    │  (shared secrets)   │
│  - notion_db_id  │    │  - anthropic-api-key│
│  - enabled       │    │  - notion-api-key   │
└──────────────────┘    └─────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│  Data Sources                                               │
│  Slack API  ──┐                                             │
│  Gmail API  ──┼──→ Claude Opus 4.5 ──→ Notion Database     │
│  Zoom API   ──┘    (extraction,         (canonical state)   │
│                     deduplication)                          │
└─────────────────────────────────────────────────────────────┘
```

## Deployment

### GCP Cloud Run (Production)

The API is deployed to GCP Cloud Run with automated daily scheduling via Cloud Scheduler.

- **API URL**: `https://todo-aggregator-908833572352.us-central1.run.app`
- **Registration**: `https://todo-aggregator-908833572352.us-central1.run.app/register`

### Local Execution (Development)

Run manually with `python src/orchestrator.py`.

## Quick Start (Local Development)

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

## Multi-User Setup (GCP Native)

The system supports multiple users with self-service registration and automated daily runs.

### User Registration

1. User visits `/register` on the Cloud Run URL
2. Enters access code (shared via internal docs)
3. Provides their credentials:
   - Slack User Token
   - Gmail Refresh Token
   - Notion Database ID
4. Credentials are stored securely in Secret Manager
5. User config is stored in Firestore
6. Welcome email is sent with personal trigger URL

### Personal Trigger URLs

Each user gets a personal URL to manually trigger their aggregation:
```
GET /trigger/{user_id}/{personal_token}
```

This allows users to run on-demand without waiting for the daily schedule.

### Automated Daily Runs

Cloud Scheduler triggers `POST /run-all` at 7am PT daily, which:
1. Fetches all enabled users from Firestore
2. Retrieves credentials from Secret Manager for each user
3. Processes each user sequentially
4. Updates run status in Firestore

### Credential Storage

| Credential | Storage | Type |
|------------|---------|------|
| Anthropic API Key | Secret Manager | Shared |
| Notion API Key | Secret Manager | Shared |
| Gmail OAuth Credentials | Secret Manager | Shared |
| Registration Access Code | Secret Manager | Shared |
| Slack User Token | Secret Manager | Per-user |
| Gmail Refresh Token | Secret Manager | Per-user |
| User Config | Firestore | Per-user |

## Project Structure

```
todo-aggregator/
├── api/
│   ├── app.py                    # FastAPI application
│   └── static/
│       ├── register.html         # Registration form
│       └── style.css             # Form styling
├── src/
│   ├── orchestrator.py           # Local entry point
│   ├── config.py                 # Configuration management
│   ├── gcp/
│   │   ├── firestore_client.py   # Firestore operations
│   │   └── secret_manager.py     # Secret Manager operations
│   ├── mcp_clients/
│   │   ├── notion_client.py      # Notion API client
│   │   ├── slack_client.py       # Slack API client
│   │   ├── gmail_client.py       # Gmail API client
│   │   └── zoom_client.py        # Zoom API client
│   └── processors/
│       └── claude_processor.py   # AI extraction & deduplication
├── scripts/
│   └── gmail_oauth_setup.py      # Gmail OAuth helper
├── tests/
│   └── ...
├── Dockerfile                    # Cloud Run container
├── .env.example                  # Environment template
└── requirements.txt
```

## Features

### Intelligence Layer
- **Priority Scoring**: Detects urgency keywords (urgent, ASAP, blocker, P0)
- **Category Tagging**: Auto-categorizes (follow-up, review, meeting, technical, etc.)
- **Due Date Inference**: Converts "by Friday" or "next week" to actual dates

### Source URLs
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

## API Reference

### POST /run-all

Process all enabled users (used by Cloud Scheduler).

**Authentication**: OIDC token or X-API-Secret header

**Response**:
```json
{
  "processed": 3,
  "successful": 3,
  "failed": 0
}
```

### POST /run/{user_id}

Process a single user by ID.

**Headers**: `X-API-Secret` required

**Response**:
```json
{
  "created": 3,
  "skipped": 8,
  "completed": 2,
  "duration_seconds": 180.5
}
```

### GET /trigger/{user_id}/{token}

Personal trigger URL for users to run on-demand.

**Response**: HTML confirmation page

### POST /register

Register a new user (form submission).

**Body**: Form data with access_code, credentials, etc.

### GET /health

Health check endpoint.

**Response**:
```json
{
  "status": "ok",
  "timestamp": "2024-12-04T12:00:00.000000"
}
```

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

### Deploy to Cloud Run

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

### View Logs

```bash
# Recent logs
gcloud logging read 'resource.type="cloud_run_revision" resource.labels.service_name="todo-aggregator"' \
  --project=todo-aggregator-480119 --limit=50

# Or view in GCP Console
# https://console.cloud.google.com/run/detail/us-central1/todo-aggregator/logs?project=todo-aggregator-480119
```

## Troubleshooting

### "Missing required configuration"
Check that required secrets are set in GCP Secret Manager.

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

## License

MIT
