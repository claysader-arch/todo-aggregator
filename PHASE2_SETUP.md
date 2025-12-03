## Phase 2 Setup: Zoom Integration

Phase 2 adds Zoom meeting summary and transcript extraction to automatically capture todos from your meetings.

### What Phase 2 Includes

✅ **Zoom API Integration**
- Fetch recent meetings (past 7 days)
- Extract AI-generated meeting summaries
- Fall back to meeting transcripts if no summary available
- Parse action items and commitments from meetings

✅ **Intelligent Extraction**
- Identifies assignees mentioned in meetings
- Extracts due dates from context
- Detects both explicit action items and implicit commitments
- Links back to meeting source

### Prerequisites

**Zoom Requirements:**
1. **Zoom Workplace** (paid plan) - Required for API access
2. **Zoom AI Companion** (optional) - For AI-generated summaries
3. **Cloud Recording** enabled - For meeting transcripts

**Note:** You can use Phase 2 without Zoom AI Companion - it will use transcripts instead of summaries.

### Step 1: Create Zoom Server-to-Server OAuth App

1. Go to [Zoom App Marketplace](https://marketplace.zoom.us/)
2. Click "Develop" → "Build App"
3. Choose "Server-to-Server OAuth"
4. Fill in app information:
   - **App Name**: Todo Aggregator
   - **Company Name**: Your name/company
   - **Developer Contact**: Your email

5. On the **App Credentials** page, copy:
   - Account ID
   - Client ID
   - Client Secret

### Step 2: Configure Scopes

Add these scopes to your Zoom app:

**Required:**
- `meeting:read:admin` - Read meeting information
- `meeting:read:list_meetings:admin` - List scheduled meetings
- `meeting:read:past_meeting:admin` - Read past meeting instances
- `user:read:admin` - Read user information

**For AI Summaries (Recommended):**
- `meeting:read:summary:admin` - Read meeting summaries
- `meeting:read:ai_companion:admin` - Access AI Companion features

**Optional (for transcript fallback):**
- `recording:read:admin` - Read meeting recordings
- `cloud_recording:read:list_user_recordings:admin` - List user recordings

### Step 3: Activate the App

1. Click "Continue" through the remaining screens
2. On the "Activation" page, click "Activate your app"
3. Copy your credentials

### Step 4: Add Credentials to .env

Edit your `.env` file and add the Zoom credentials:

```bash
# Zoom Configuration
ZOOM_ACCOUNT_ID=your-account-id-here
ZOOM_CLIENT_ID=your-client-id-here
ZOOM_CLIENT_SECRET=your-client-secret-here
```

### Step 5: Enable Zoom Features

**For AI Summaries (Optional but Recommended):**
1. Go to Zoom Admin Dashboard
2. Navigate to "Settings" → "In Meeting (Advanced)"
3. Enable "Meeting Summary with AI Companion"

**For Transcripts:**
1. Go to "Settings" → "Recording"
2. Enable "Cloud Recording"
3. Enable "Audio transcript"

### Step 6: Test Zoom Connection

Run the connection test:

```bash
python3 test_zoom_connection.py
```

Expected output:
```
Testing Zoom API connection...
✓ Successfully obtained access token
✓ Zoom API connection successful
✓ Retrieved X meetings from past 7 days
```

### Step 7: Test Phase 2 with Mock Data

Test the extraction pipeline without real Zoom data:

```bash
python3 test_phase2_mock.py
```

This will show you how todos are extracted from Zoom meeting content.

### Step 8: Test with Real Zoom Data

Once your Zoom credentials are configured:

```bash
python3 test_phase2_real.py
```

This will:
- Fetch your actual recent meetings
- Extract meeting summaries
- Show extracted todos
- Prompt before writing to Notion

**Or run the automated test:**

```bash
python3 complete_phase2_test.py
```

This automatically writes todos to Notion without prompting.

### Step 9: Run Full Orchestrator

Run the complete aggregator with Zoom integration:

```bash
python3 src/orchestrator.py
```

The system will now:
1. Collect Zoom meeting content (past 7 days)
2. Extract todos using Claude AI
3. Deduplicate across all sources
4. Update your Notion database
5. Generate daily summary

## How It Works

### Meeting Discovery Process

The integration uses a three-step approach to find meetings with AI summaries:

1. **Fetch Scheduled Meetings**
   - Retrieves all scheduled recurring/regular meetings from your account

2. **Get Past Instances**
   - For each scheduled meeting, fetches instances that occurred in the lookback period (default: 7 days)
   - Uses the instance UUID to access meeting-specific data

3. **Retrieve AI Summaries**
   - Attempts to fetch AI Companion summary for each past instance
   - Uses Zoom's `/meetings/{uuid}/meeting_summary` endpoint
   - Returns structured summary with overview, details, and next steps

### AI Summary Structure

Zoom AI Companion summaries include:

- **summary_overview** - High-level meeting recap (1-2 paragraphs)
- **summary_details** - Categorized discussion points with labels
- **next_steps** - Action items extracted by Zoom AI (list of strings)
- **summary_content** - Pre-formatted markdown with all content

The system uses `summary_content` which already includes properly formatted sections, or falls back to building the summary from components if unavailable.

### What Gets Extracted

From Zoom AI summaries, Claude identifies additional structured todos:

- **Explicit Assignments**: "Clay: Send Jason Mello's consulting agreement"
- **Action Items**: "Review and marinate on the Notion framework"
- **Follow-ups**: "Ping VIN again since no response received yet"
- **Deadlines**: "Send agreement today or tomorrow" → extracted as due dates

### Deduplication

Phase 2 integrates with the existing deduplication system:
- Detects if the same todo appears in multiple meetings
- Merges todos mentioned in both Zoom and other platforms (Slack, Gmail)
- Tracks all source meetings for each todo

## Troubleshooting

### "401 Unauthorized" Error

**Issue**: Invalid or expired credentials

**Fix**:
- Verify your Account ID, Client ID, and Client Secret
- Check that your Server-to-Server OAuth app is activated
- Regenerate credentials if needed

### "404 Not Found" for Meeting Summary

**Issue**: Meeting doesn't have an AI summary

**Fix**:
- Enable Zoom AI Companion in your account
- The system will automatically fall back to transcripts
- This is normal for meetings where AI summary wasn't generated

### "No meetings found"

**Issue**: No meetings in the past 7 days

**Fix**:
- Have at least one recorded meeting
- Ensure cloud recording is enabled
- Try increasing the lookback period (modify `days` parameter)

### "Insufficient privileges"

**Issue**: Missing required scopes

**Fix**:
- Review scopes in your Zoom app configuration
- Add missing scopes listed in Step 2
- Deauthorize and reauthorize the app

## Configuration Options

### Adjust Lookback Period

Edit `src/orchestrator.py`:

```python
# Change from 7 days to 14 days
zoom_content = zoom.get_meeting_content(days=14)
```

### Filter by Meeting Type

Modify `src/mcp_clients/zoom_client.py`:

```python
params = {
    "from": from_date,
    "to": to_date,
    "type": "past",
    "page_size": page_size,
}
```

Change `type` to:
- `"past"` - All past meetings (default)
- `"pastOne"` - Single instance meetings only
- `"pastJoin"` - Only meetings you joined

## Next Steps

**Phase 3: Slack Integration**
- Read Slack Canvas with AI summaries
- Extract todos from channel messages
- Track @mentions and thread commitments

**Phase 4: Gmail Integration**
- Parse emails for action items
- Use Google Apps Script + Gemini API
- Track email-based commitments

## Cost Considerations

**Zoom API:**
- ✅ Free for Server-to-Server OAuth
- No per-request costs
- Rate limits: Sufficient for daily aggregation

**Zoom AI Companion:**
- May require additional Zoom plan
- Check with your Zoom admin
- Transcripts work without AI Companion

**Anthropic API (Claude):**
- ~$0.01-0.03 per meeting depending on length
- Estimate: $0.50-1.50/month for daily aggregation
- Monitor usage in Anthropic console

## Support

- Check Zoom API rate limits: [Zoom API Docs](https://developers.zoom.us/docs/api/rest/rate-limits/)
- Review meeting summary feature: [AI Companion Guide](https://support.zoom.us/hc/en-us/articles/18182051511309)
