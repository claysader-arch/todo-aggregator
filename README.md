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

### Zoom Email Detection
- Zoom AI Companion emails are automatically re-attributed from "gmail" to "zoom" source

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

## License

MIT
