# Phase 3 Setup: Slack Integration

Phase 3 adds Slack integration to extract todos from channel messages, threads, and AI-generated summaries.

## What Phase 3 Includes

**Slack Content Sources:**
- Channel messages with action items
- Thread conversations with commitments
- @mentions and assignments
- Slack AI summaries (if available)
- Canvas documents with meeting notes

**Intelligent Extraction:**
- Identifies todos from natural conversation
- Detects assignments via @mentions
- Extracts due dates from context
- Links back to original Slack messages

## Prerequisites

### Slack Plan Requirements

Choose one of these approaches based on your Slack plan:

| Approach | Slack Plan Required | Features |
|----------|---------------------|----------|
| **A. Slack AI** | Business+ or Enterprise | AI summaries, best extraction |
| **B. Bot + API** | Any paid plan | Direct message access |
| **C. Canvas only** | Business+ | Manual AI summaries via Canvas |

### Recommended: Approach A (Slack AI)

If you have Slack Business+ or Enterprise:
1. Slack AI generates daily/weekly channel summaries
2. Summaries are written to a Canvas
3. Our system reads the Canvas for todos

### Alternative: Approach B (Bot + API)

For any Slack paid plan:
1. Create a Slack bot app
2. Bot reads channel history directly
3. Claude extracts todos from raw messages

## Setup Instructions

### Step 1: Create Slack App

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name: "Todo Aggregator"
4. Select your workspace

### Step 2: Configure Bot Permissions

Add these OAuth scopes under "OAuth & Permissions":

**Required Scopes:**
- `channels:history` - Read public channel messages
- `channels:read` - View basic channel info
- `groups:history` - Read private channel messages (if needed)
- `groups:read` - View private channel info
- `users:read` - View user information (for @mentions)

**Optional Scopes (for Canvas):**
- `canvases:read` - Read Canvas documents

### Step 3: Install App to Workspace

1. Go to "Install App" in sidebar
2. Click "Install to Workspace"
3. Authorize the requested permissions
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### Step 4: Add Credentials to .env

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_CANVAS_ID=F123456789  # Optional: Canvas with AI summaries
```

### Step 5: Invite Bot to Channels

For each channel you want to monitor:
1. Open the channel in Slack
2. Type `/invite @Todo Aggregator` (or your bot name)
3. Confirm the invitation

### Step 6: (Optional) Set Up Slack AI Summaries

If using Slack AI:

1. **Create a Workflow:**
   - Go to Workflow Builder
   - Create workflow triggered daily/weekly
   - Add "Generate AI summary" step
   - Add "Post to Canvas" step

2. **Get Canvas ID:**
   - Open the Canvas in Slack
   - Click "..." menu → "Copy link"
   - Extract the Canvas ID (e.g., `F07ABC123XYZ`)

### Step 7: Test Connection

```bash
python3 test_slack_connection.py
```

Expected output:
```
Testing Slack API connection...
✓ Successfully authenticated
✓ Bot name: Todo Aggregator
✓ Found X accessible channels
✓ Slack integration ready
```

## Configuration Options

### Specify Channels to Monitor

By default, the bot monitors all channels it's invited to. To limit to specific channels:

```bash
# In .env
SLACK_CHANNELS=general,engineering,product
```

### Adjust Message Lookback

```python
# In src/mcp_clients/slack_client.py
messages = slack.get_channel_history(channel_id, days=7)  # Default: 7 days
```

### Filter by User Mentions

The system uses the same `MY_NAME` filtering from Phase 2:
```bash
MY_NAME=Clay,clay,Clay Sader
FILTER_MY_TODOS_ONLY=true
```

## How It Works

### Message Flow

```
Slack Channels → Bot reads messages → Claude extracts todos
       ↓
Slack AI Summary → Canvas → Read via API → Claude extracts todos
```

### What Gets Extracted

From Slack messages, Claude identifies:

- **Direct assignments**: "@clay can you handle the API integration?"
- **Self-commitments**: "I'll review the PR by tomorrow"
- **Action items**: "TODO: update the documentation"
- **Meeting follow-ups**: "Let's schedule a call to discuss"

### Deduplication

Slack todos are deduplicated against:
- Existing Notion todos
- Zoom meeting todos (same task mentioned in both)
- Other Slack channels (cross-posted messages)

## Troubleshooting

### "not_in_channel" Error

**Issue**: Bot can't read channel messages

**Fix**: Invite the bot to the channel:
```
/invite @Todo Aggregator
```

### "missing_scope" Error

**Issue**: Bot doesn't have required permissions

**Fix**:
1. Go to Slack App settings → OAuth & Permissions
2. Add the missing scope
3. Reinstall the app to workspace

### No Messages Found

**Issue**: Bot returns empty message history

**Possible causes:**
- Bot not invited to any channels
- Messages older than lookback period
- Private channels require `groups:history` scope

### Rate Limiting

**Issue**: Slack API rate limit errors

**Fix**: The client includes automatic retry logic, but for large workspaces:
- Reduce number of monitored channels
- Increase polling interval
- Use Slack AI summaries instead of raw messages

## Cost Considerations

**Slack API:**
- Free for read operations
- Rate limits: Tier 3 (50+ requests/minute)

**Anthropic API (Claude):**
- ~$0.01-0.05 per channel depending on message volume
- Slack AI summaries reduce token usage significantly
- Estimate: $1-3/month for typical usage

## Files to Create

Phase 3 implementation will create:

```
src/mcp_clients/slack_client.py   # Slack API integration
test_slack_connection.py          # Connection testing
test_phase3_mock.py              # Mock data testing
test_phase3_real.py              # Real data testing
```

## Next Steps

After Phase 3:
- **Phase 4**: Gmail integration (Google Apps Script + Gemini)
- **Phase 5**: Intelligence layer enhancements
- **Phase 6**: Scheduling and output configuration
