# Todo Aggregator

AI-powered system that aggregates todos from Slack, Zoom, Gmail, and Notion with intelligent deduplication and cross-platform completion tracking.

## Overview

This system uses Claude Opus 4.5 to:
- Extract todos from multiple platforms (both explicit assignments and implicit commitments)
- Deduplicate todos mentioned across different tools
- Detect when todos are completed in any platform
- Maintain a canonical todo list in Notion
- Generate daily summaries

## Architecture

```
Slack → MCP →
Gmail → MCP → Claude Opus 4.5 → Notion Database (State Store)
Zoom → MCP →
Notion → MCP →
```

## Setup

### 1. Clone and Install

```bash
git clone <your-repo-url>
cd todo-aggregator
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

#### Phase 1 (Foundation) - Required:
- `ANTHROPIC_API_KEY` - Get from https://console.anthropic.com
- `NOTION_API_KEY` - Create integration at https://www.notion.so/my-integrations
- `NOTION_DATABASE_ID` - ID of your todo database

#### Later Phases:
- `SLACK_USER_TOKEN` - From Slack app configuration (xoxp-...)
- `ZOOM_*` - From Zoom Marketplace app
- `GMAIL_*` - From Google Cloud Console OAuth credentials

### 3. Set Up Notion Database

Create a Notion database with the following properties:

| Property | Type | Description |
|----------|------|-------------|
| Task | Title | Todo description |
| Status | Select | Open / In Progress / Done |
| Source | Multi-select | Slack / Gmail / Zoom / Notion |
| Source URL | URL | Link to original message/email |
| Assigned To | Person | Who owns this todo |
| Due Date | Date | If mentioned |
| Created | Created time | When first detected |
| Completed | Date | When marked done |
| Confidence | Number | AI confidence score (0-1) |
| Dedupe Hash | Text | For detecting duplicates |

Share the database with your Notion integration.

### 4. Run Locally

```bash
python src/orchestrator.py
```

### 5. Set Up GitHub Actions (Automated Scheduling)

1. Push this repo to GitHub
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Add all required secrets from your `.env` file:
   - `ANTHROPIC_API_KEY`
   - `NOTION_API_KEY`
   - `NOTION_DATABASE_ID`
   - (Add others as you implement more phases)

4. The workflow will run daily at 6 AM UTC automatically
5. To test immediately, go to **Actions** tab → **Todo Aggregator** → **Run workflow**

## Project Structure

```
todo-aggregator/
├── src/
│   ├── orchestrator.py          # Main entry point
│   ├── config.py                # Configuration management
│   ├── mcp_clients/             # MCP client wrappers
│   ├── processors/              # Todo extraction, deduplication
│   └── outputs/                 # Notion writer, summary generator
├── scripts/
│   ├── gmail_apps_script.js     # Gmail + Gemini integration
│   └── slack_workflow.json      # Slack Workflow config
├── mcp_servers/
│   └── zoom_extended/           # Custom Zoom MCP
├── .github/
│   └── workflows/
│       └── todo-aggregator.yml  # GitHub Actions config
└── tests/
```

## Implementation Phases

- [x] **Phase 1**: Foundation (Notion setup, basic orchestrator) - [Setup Guide](PHASE1_SETUP.md)
- [x] **Phase 2**: Zoom integration (meeting summaries/transcripts) - [Setup Guide](PHASE2_SETUP.md) | [Complete](PHASE2_COMPLETE.md)
- [x] **Phase 3**: Slack integration - [Setup Guide](PHASE3_SETUP.md)
- [x] **Phase 4**: Gmail integration - [Setup Guide](PHASE4_SETUP.md) | [Complete](PHASE4_COMPLETE.md)
- [ ] **Phase 5**: Intelligence layer enhancements - [Setup Guide](PHASE5_SETUP.md)
- [ ] **Phase 6**: Scheduling and output configuration

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

Logs are written to:
- Console (stdout)
- Daily log file: `aggregator_YYYYMMDD.log`
- GitHub Actions artifacts (when running via Actions)

## Platform-Specific Notes

### Slack
- Requires Slack AI add-on or Business+/Enterprise plan
- Uses Workflow Builder to generate AI summaries → Canvas
- Canvas is read via MCP server

### Gmail
- Uses Gmail API with OAuth 2.0 authentication
- Processes emails from last 24 hours
- Extracts todos via Claude (same as other sources)

### Zoom
- Best API support for AI summaries
- Requires Zoom Workplace paid plan
- Can use webhooks for real-time updates

### Notion
- Official MCP server from Notion
- Serves as canonical state store
- Tracks deduplication and completion

## Troubleshooting

### Missing API Keys
Check that all required environment variables are set in `.env` or GitHub Secrets.

### GitHub Actions Not Running
- Verify secrets are added in repo settings
- Check Actions tab for error logs
- Try manual trigger via "Run workflow" button

### MCP Connection Issues
- Ensure MCP servers are properly installed
- Check authentication credentials
- Review MCP server documentation

## Contributing

This project follows the implementation phases outlined in the specification.
Please coordinate phase work to avoid conflicts.

## License

MIT
