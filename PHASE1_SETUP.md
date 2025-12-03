# Phase 1 Setup Guide

This guide will help you get Phase 1 of the Todo Aggregator up and running.

## What Phase 1 Includes

Phase 1 provides the **foundation** for the todo aggregation system:

- ✅ Notion database integration (read/write operations)
- ✅ Claude AI-powered todo extraction
- ✅ Intelligent deduplication using semantic similarity
- ✅ Completion detection across platforms
- ✅ Daily summary generation
- ✅ Complete orchestration pipeline

**Note:** Phase 1 focuses on the core infrastructure. Platform integrations (Slack, Zoom, Gmail) will be added in later phases.

## Prerequisites

1. **Python 3.11+** installed
2. **Anthropic API Key** - Get from https://console.anthropic.com
3. **Notion API Key** - Create integration at https://www.notion.so/my-integrations
4. **Notion Database** - Set up with the required schema (instructions below)

## Step 1: Install Dependencies

```bash
cd todo-aggregator
pip install -r requirements.txt
```

## Step 2: Set Up Notion Database

### Create Database

1. Go to Notion and create a new database (full page or inline)
2. Name it "Todo Aggregator" or similar

### Configure Properties

Your database needs these properties (case-sensitive):

| Property Name | Type | Description | Required |
|--------------|------|-------------|----------|
| **Task** | Title | The todo description | ✅ Yes |
| **Status** | Select | Options: Open, In Progress, Done | ✅ Yes |
| **Source** | Multi-select | Options: Slack, Gmail, Zoom, Notion | ✅ Yes |
| **Source URL** | URL | Link to original message/email | No |
| **Assigned To** | Person | Who owns this todo | No |
| **Due Date** | Date | If mentioned | No |
| **Created** | Created time | Auto-populated | No |
| **Completed** | Date | When marked done | No |
| **Confidence** | Number | AI confidence score (0-1) | No |
| **Dedupe Hash** | Text | For detecting duplicates | No |

### Set Up Status Property

Make sure the **Status** property has these exact options:
- `Open` (default)
- `In Progress`
- `Done`

### Set Up Source Property

Add these options to the **Source** multi-select:
- `Slack`
- `Gmail`
- `Zoom`
- `Notion`

### Share Database with Integration

1. Click "Share" in the top right of your database
2. Click "Invite"
3. Select your Notion integration
4. Grant access

### Get Database ID

The database ID is in the URL when viewing the database:
```
https://www.notion.so/YOUR_DATABASE_ID?v=...
                      ^^^^^^^^^^^^^^^^^^^
```

Copy this ID for your `.env` file.

## Step 3: Get API Keys

### Anthropic API Key

1. Go to https://console.anthropic.com
2. Navigate to "API Keys"
3. Create a new key
4. Copy the key (starts with `sk-ant-`)

### Notion API Key

1. Go to https://www.notion.so/my-integrations
2. Click "+ New integration"
3. Name it "Todo Aggregator"
4. Select your workspace
5. Submit
6. Copy the "Internal Integration Token" (starts with `secret_`)

## Step 4: Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```bash
# Anthropic API Configuration
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Notion Configuration
NOTION_API_KEY=secret_your-key-here
NOTION_DATABASE_ID=your-database-id-here

# Optional: Runtime Settings
DEBUG=false
LOG_LEVEL=INFO
```

**Important:** Never commit your `.env` file to git. It's already in `.gitignore`.

## Step 5: Test the Setup

Run the test script to verify everything is configured correctly:

```bash
python3 test_phase1.py
```

This will:
- ✅ Verify all modules can be imported
- ✅ Test Claude AI extraction with sample data
- ✅ Test Notion database connectivity

Expected output:
```
============================================================
Phase 1 Implementation Test
============================================================

1. Testing imports...
✓ Successfully imported ClaudeProcessor
✓ Successfully imported NotionClient

2. Testing Claude extraction...
✓ Successfully initialized ClaudeProcessor
Testing todo extraction with sample data...
✓ Extracted N todos

3. Testing Notion client...
✓ Successfully initialized NotionClient
Testing Notion database query...
✓ Successfully queried Notion database
  Found N existing todos

============================================================
Test complete!
============================================================
```

## Step 6: Run the Orchestrator

Once testing passes, run the full orchestrator:

```bash
python3 src/orchestrator.py
```

### What It Does

The orchestrator will:

1. **Collect** - Gather content from all sources (currently empty for Phase 1)
2. **Extract** - Use Claude to identify todos from content
3. **Deduplicate** - Match against existing todos in Notion
4. **Detect Completions** - Check if any open todos are now done
5. **Update Notion** - Write new todos and mark completions
6. **Generate Summary** - Create daily digest with Claude

### Expected Behavior (Phase 1)

Since platform integrations aren't added yet:
- No new todos will be extracted (no content sources yet)
- Existing todos in your Notion database will be queried and processed
- A daily summary will be generated
- Logs will show the complete pipeline execution

## Understanding the Output

### Log Files

A log file is created for each run:
```
aggregator_YYYYMMDD.log
```

### Console Output

You'll see:
```
================================================================================
Todo Aggregator - Starting run
Timestamp: 2024-01-15T10:30:00
================================================================================
INFO - Collection complete. Found content from 0 sources
INFO - Found 5 existing todos in Notion
INFO - Deduplication complete. 0 unique todos
INFO - Completion detection complete. Found 0 completed todos
INFO - Notion update complete. Created: 0, Updated: 0, Completed: 0
================================================================================
DAILY SUMMARY
================================================================================
[Claude-generated summary of your todos]
================================================================================
Todo aggregation run completed successfully
```

## Testing with Sample Data

To test the extraction pipeline, you can modify the `collect_todos()` function temporarily:

```python
def collect_todos() -> dict:
    # Test with sample data
    raw_content = {
        "slack": [
            "Hey @john, can you send me the Q4 report by Friday?",
            "I'll review the design mockups tomorrow morning."
        ],
        "gmail": [
            "Action item: Follow up with client about contract"
        ],
        "zoom": [],
        "notion": []
    }
    return raw_content
```

This will test the full pipeline with mock data.

## Next Steps

Once Phase 1 is working:

- **Phase 2**: Add Zoom integration (meeting summaries via MCP)
- **Phase 3**: Add Slack integration (Canvas reading via MCP)
- **Phase 4**: Add Gmail integration (Apps Script + Gemini)
- **Phase 5**: Enhance intelligence layer (better deduplication)
- **Phase 6**: Add scheduling and output configuration

## Troubleshooting

### "Missing required configuration" error

Make sure your `.env` file has all three required keys:
- `ANTHROPIC_API_KEY`
- `NOTION_API_KEY`
- `NOTION_DATABASE_ID`

### "401 Unauthorized" from Notion

- Verify your Notion integration token is correct
- Make sure you shared the database with your integration
- Check that the database ID is correct

### "Invalid API key" from Anthropic

- Verify your Anthropic API key is correct
- Check that it starts with `sk-ant-`
- Ensure you have credits in your Anthropic account

### Import errors

```bash
pip install -r requirements.txt
```

### Database schema errors

Make sure your Notion database has the exact property names listed above. Property names are case-sensitive.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Orchestrator                         │
│                  (src/orchestrator.py)                   │
└─────────────────────────────────────────────────────────┘
                          │
         ┌────────────────┴────────────────┐
         │                                  │
         ▼                                  ▼
┌──────────────────┐              ┌──────────────────┐
│  Notion Client   │              │ Claude Processor │
│  (Read/Write)    │              │  (AI Analysis)   │
└──────────────────┘              └──────────────────┘
         │                                  │
         │                                  │
         ▼                                  ▼
┌──────────────────┐              ┌──────────────────┐
│ Notion Database  │              │  Claude Opus 4.5 │
│  (State Store)   │              │   (Anthropic)    │
└──────────────────┘              └──────────────────┘
```

## Questions?

Check the main [README.md](README.md) for general information or open an issue on GitHub.
