# Phase 4 Setup: Gmail Integration

Phase 4 adds Gmail as a todo source, extracting action items from your emails.

## What Phase 4 Includes

**Email Content Sources:**
- Sent emails with commitments you made
- Received emails with action items assigned to you
- Email threads with follow-up tasks
- Flagged/starred emails

**Intelligent Extraction:**
- Identifies todos from email content
- Detects assignments and requests
- Extracts due dates from context
- Deduplicates against Zoom/Slack todos

## Prerequisites

### Google Cloud Setup

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project (e.g., "Todo Aggregator")
   - Note your Project ID

2. **Enable Gmail API**
   - Go to APIs & Services > Library
   - Search for "Gmail API"
   - Click Enable

3. **Create OAuth 2.0 Credentials**
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: **Desktop app**
   - Name: "Todo Aggregator"
   - Download the JSON file

4. **Configure OAuth Consent Screen**
   - Go to APIs & Services > OAuth consent screen
   - User Type: External (or Internal if using Workspace)
   - Add your email as a test user
   - Scopes required:
     - `https://www.googleapis.com/auth/gmail.readonly`

## Setup Instructions

### Step 1: Install Dependencies

```bash
pip3 install google-auth-httplib2 google-auth-oauthlib google-api-python-client
```

### Step 2: Generate OAuth Tokens

Run the OAuth setup script:

```bash
python3 scripts/gmail_oauth_setup.py /path/to/downloaded/credentials.json
```

This will:
1. Open a browser for Google sign-in
2. Request Gmail read permissions
3. Output your refresh token

### Step 3: Add Credentials to .env

```bash
# Gmail Configuration (Phase 4)
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REFRESH_TOKEN=your-refresh-token-from-step-2
```

### Step 4: Test Connection

```bash
python3 tests/test_gmail_connection.py
```

Expected output:
```
Testing Gmail API connection...
✓ Successfully authenticated
✓ Email: your.email@gmail.com
✓ Found X recent emails
✓ Gmail integration ready
```

## Configuration Options

### Email Lookback Period

Default: 1 day. Adjust in orchestrator or via environment:

```bash
GMAIL_LOOKBACK_DAYS=1
```

### Email Filtering

The client uses Gmail search queries. Default filters:
- Recent emails (based on lookback)
- Excludes promotional/social categories
- Includes sent and received

Custom filters can be added:
```bash
# Only emails with specific labels
GMAIL_QUERY=label:action-required

# Only unread emails
GMAIL_QUERY=is:unread

# Emails mentioning TODO
GMAIL_QUERY=subject:(TODO OR ACTION)
```

## How It Works

### Data Flow

```
Gmail API
    ↓
GmailClient.get_gmail_content()
    ↓ [List of formatted emails]
Orchestrator collection phase
    ↓ [Combined with Zoom + Slack]
Claude extraction
    ↓ [Structured todos]
Deduplication + Notion sync
```

### What Gets Extracted

From emails, Claude identifies:
- **Direct requests**: "Can you send me the report by Friday?"
- **Commitments**: "I'll follow up with the client tomorrow"
- **Action items**: "TODO: Review the contract"
- **Deadlines**: "Please complete by EOD"

## Troubleshooting

### "Invalid grant" Error

**Issue**: Refresh token expired or revoked

**Fix**:
1. Re-run `gmail_oauth_setup.py`
2. Update `GMAIL_REFRESH_TOKEN` in `.env`

### "Access Not Configured" Error

**Issue**: Gmail API not enabled

**Fix**:
1. Go to Google Cloud Console
2. APIs & Services > Library
3. Enable Gmail API

### "Insufficient Permission" Error

**Issue**: OAuth scopes not granted

**Fix**:
1. Delete stored credentials
2. Re-run OAuth flow
3. Ensure you approve the gmail.readonly scope

### Rate Limiting

Gmail API has generous limits (250 quota units/user/second). If you hit limits:
- Reduce lookback period
- Use more specific search queries
- Add delays between requests

## Security Notes

- **Read-only access**: The app only requests `gmail.readonly` scope
- **No email modification**: Cannot send, delete, or modify emails
- **Token storage**: Store refresh token securely in `.env`
- **Test users**: In development, add yourself as a test user in OAuth consent screen

## Cost Considerations

- **Gmail API**: Free (within quota limits)
- **Claude API**: ~$0.01-0.05 per run depending on email volume
- **Estimated monthly**: $1-3 for typical usage

## Files to Create

```
scripts/gmail_oauth_setup.py    # One-time OAuth token generator
src/mcp_clients/gmail_client.py # Gmail API integration
tests/test_gmail_connection.py  # Connection testing
```

## Implementation Checklist

- [ ] Set up Google Cloud project
- [ ] Enable Gmail API
- [ ] Create OAuth credentials
- [ ] Install Python dependencies
- [ ] Run OAuth setup script to get tokens
- [ ] Add credentials to .env
- [ ] Create gmail_client.py
- [ ] Update orchestrator.py
- [ ] Create connection test
- [ ] Run full integration test

## Next Steps

After Phase 4:
- **Phase 5**: Intelligence layer enhancements
- **Phase 6**: Scheduling and output configuration
