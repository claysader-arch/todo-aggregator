# Gmail OAuth Setup Instructions

This document contains the remaining steps to complete the Gmail one-click OAuth implementation.

## Status

✅ **Completed:**
- GCP OAuth consent screen configured
- Web OAuth client created with redirect URIs
- Backend OAuth endpoints implemented (`/oauth/gmail/start`, `/oauth/gmail/callback`)
- Frontend "Connect Gmail" button added to registration form
- Session middleware configured for CSRF protection
- JavaScript OAuth flow with popup and postMessage
- CSS styling for OAuth button
- Dependencies updated (httpx added to requirements.txt)

⏳ **Remaining Tasks:**

### 1. Create Session Secret in Secret Manager

Run these commands to create and configure the session secret:

```bash
# Create the session secret (for CSRF protection)
echo -n "052830c5796ff2433a933e0a994f44be8ffa2746a7f2a5246836cfeefc7bf29c" | gcloud secrets create session-secret --data-file=- --project=todo-aggregator-480119

# Grant Cloud Run access to the secret
gcloud secrets add-iam-policy-binding session-secret \
  --member="serviceAccount:908833572352-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=todo-aggregator-480119
```

### 2. Update Gmail OAuth Credentials

Update the existing secrets with the new web OAuth client credentials:

```bash
# Update Gmail client ID (web application type)
# Replace <CLIENT_ID> with the OAuth client ID from GCP Console
echo -n "<CLIENT_ID>" | gcloud secrets versions add gmail-client-id --data-file=- --project=todo-aggregator-480119

# Update Gmail client secret
# Replace <CLIENT_SECRET> with the OAuth client secret from GCP Console
echo -n "<CLIENT_SECRET>" | gcloud secrets versions add gmail-client-secret --data-file=- --project=todo-aggregator-480119
```

**Note:** Use the Client ID and Client Secret from the web OAuth client you created in step 1.
- Client ID: Format like `XXXXXXXXX-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX.apps.googleusercontent.com`
- Client Secret: Format like `GOCSPX-XXXXXXXXXXXXXXXXXXXXXXXXXXXX`

### 3. Deploy to Cloud Run

Deploy the updated application:

```bash
# Navigate to project directory
cd todo-aggregator

# Deploy to Cloud Run (builds from source)
gcloud run deploy todo-aggregator \
  --source . \
  --region us-central1 \
  --project todo-aggregator-480119 \
  --allow-unauthenticated
```

**Note:** The deployment will automatically:
- Install the new httpx dependency
- Configure session middleware
- Enable the OAuth endpoints

### 4. Test the OAuth Flow

After deployment, test the complete flow:

1. **Go to registration page:**
   ```
   https://todo-aggregator-908833572352.us-central1.run.app
   ```

2. **Test OAuth flow:**
   - Fill in the non-Gmail fields (Name, Email, Slack token, etc.)
   - Click the "Connect Gmail" button
   - A popup should open with Google OAuth consent screen
   - Authorize the app with your Google account
   - The popup should close and the refresh token should auto-populate in the form
   - The button should change to "✓ Connected" with green background

3. **Complete registration:**
   - Submit the form with all fields filled
   - Verify the user is created successfully

4. **Test aggregation:**
   - Trigger a manual run using your personal trigger URL
   - Verify Gmail emails are fetched successfully
   - Check Notion for extracted todos

### 5. Troubleshooting

**If OAuth popup doesn't open:**
- Check browser popup blocker settings
- Try again (popup blocker may need to be disabled for the site)

**If "No refresh token" error:**
- The app was already authorized previously
- Go to https://myaccount.google.com/permissions
- Find and remove "Todo Aggregator"
- Try connecting again

**If state validation fails:**
- This is usually a timing issue or session problem
- Try again (sessions expire after 15 minutes)
- Check browser cookies are enabled

**If token exchange fails:**
- Check Cloud Run logs: `gcloud run logs read --service=todo-aggregator --region=us-central1`
- Verify the OAuth credentials are correct in Secret Manager
- Verify redirect URI matches exactly: `https://todo-aggregator-908833572352.us-central1.run.app/oauth/gmail/callback`

### 6. Update Documentation

After successful testing, update the README.md:

**Changes needed in README.md:**

1. **Gmail Setup Section:**
   - Change primary instructions to: "Click 'Connect Gmail' button in registration form"
   - Move manual script setup to an "Advanced Setup (Optional)" section
   - Add troubleshooting section for "No refresh token" error

2. **Example text:**
   ```markdown
   ### Gmail Setup

   Gmail authentication is handled automatically through the registration form:

   1. Click the "Connect Gmail" button in the registration form
   2. Sign in with your Google account
   3. Click "Allow" to grant access
   4. The refresh token will auto-populate in the form

   **Troubleshooting:** If you see "No refresh token received", you've already authorized the app previously. Go to [Google Account Permissions](https://myaccount.google.com/permissions), remove "Todo Aggregator", and try again.

   #### Advanced Setup (Manual Method)

   If you prefer to generate the refresh token manually:
   [Keep existing manual setup instructions here...]
   ```

## Architecture Details

### OAuth Flow Sequence

```
1. User clicks "Connect Gmail" button
   ↓
2. JavaScript opens popup: /oauth/gmail/start
   ↓
3. Server generates CSRF state token, stores in session
   ↓
4. Server redirects to Google OAuth consent screen
   ↓
5. User authorizes with Google account
   ↓
6. Google redirects to: /oauth/gmail/callback?code=...&state=...
   ↓
7. Server validates state (CSRF protection)
   ↓
8. Server exchanges authorization code for refresh token
   ↓
9. Server returns HTML page with postMessage
   ↓
10. Parent window receives refresh token via postMessage
   ↓
11. Form field auto-populated, popup closes
```

### Security Features

- **CSRF Protection:** State parameter validated against server-side session
- **Session Expiry:** OAuth state expires after 15 minutes
- **Origin Validation:** postMessage origin checked before accepting token
- **HTTPS Only:** Session cookies require HTTPS (enforced by Cloud Run)
- **HTTPOnly Cookies:** Session cookies not accessible to JavaScript

### Files Modified

- `api/app.py` - Added OAuth endpoints and session middleware
- `api/static/register.html` - Added "Connect Gmail" button and JavaScript
- `api/static/style.css` - Added OAuth button styles
- `requirements.txt` - Added httpx dependency

## Verification Checklist

After completing all steps, verify:

- [ ] Session secret exists in Secret Manager
- [ ] Gmail OAuth credentials updated in Secret Manager
- [ ] Application deployed to Cloud Run successfully
- [ ] Registration page loads correctly
- [ ] "Connect Gmail" button opens OAuth popup
- [ ] OAuth consent screen shows "Todo Aggregator"
- [ ] Refresh token auto-populates after authorization
- [ ] Button changes to "✓ Connected" with green color
- [ ] Full registration completes successfully
- [ ] Gmail emails are fetched during aggregation run
- [ ] Todos appear in Notion database
- [ ] README.md updated with new instructions

## Next Steps

Once everything is working:

1. Update Notion setup guide (external documentation)
2. Notify existing users about the easier setup method
3. Consider deprecating the manual script method in future
4. Monitor error rates and OAuth flow completion rates

## Support

If you encounter issues:

1. Check Cloud Run logs for error details
2. Verify all Secret Manager secrets are accessible
3. Confirm OAuth redirect URIs match exactly in GCP Console
4. Test with different Google accounts
5. Check browser console for JavaScript errors