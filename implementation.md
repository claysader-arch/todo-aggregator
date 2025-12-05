# Template Implementation Plan: Notion + Zapier Templates

## Overview
Create detailed specifications for:
1. **Notion Template** - Shareable database + setup instructions
2. **Zapier Template** - Copyable Zap with placeholders

All documentation lives in Notion as part of the setup process.

---

## Part 1: Notion Template Specification

### 1.1 Template Structure

```
📁 Todo Aggregator (Template Page)
├── 📄 Setup Guide (child page)
│   ├── Prerequisites
│   ├── Step 1: Notion Setup
│   ├── Step 2: Slack Setup
│   ├── Step 3: Gmail Setup
│   ├── Step 4: Zapier Setup
│   └── Troubleshooting
│
└── 🗃️ Todos Database (inline database)
```

### 1.2 Todos Database Schema

| Property | Type | Required | Options/Format | Description |
|----------|------|----------|----------------|-------------|
| **Task** | Title | Yes | - | Todo description |
| **Status** | Select | Yes | `Open`, `In Progress`, `Done`, `Done?` | Current state |
| **Source** | Multi-select | Yes | `slack`, `gmail`, `zoom`, `notion` | Where todo originated |
| **Source URL** | URL | Yes | - | Link to original message |
| **Priority** | Select | No | `high`, `medium`, `low` | Urgency level |
| **Category** | Multi-select | No | `follow-up`, `review`, `meeting`, `finance`, `hr`, `technical`, `communication` | Auto-categorization |
| **Due Date** | Date | No | - | Deadline |
| **Confidence** | Number | No | Percent format (0-100%) | AI confidence score |
| **Dedupe Hash** | Text | No | - | Internal deduplication ID |
| **Completed** | Date | No | - | When marked done |
| **Created** | Created time | Auto | - | System timestamp |

### 1.3 Database Views to Create

1. **All Todos** (Table) - Default view, all properties visible
2. **Active** (Table) - Filter: Status is `Open` or `In Progress`
3. **By Priority** (Board) - Group by Priority column
4. **By Source** (Board) - Group by Source column
5. **This Week** (Table) - Filter: Due Date is within this week

### 1.4 Select Option Colors (Suggested)

**Status:**
- Open: Gray
- In Progress: Blue
- Done: Green
- Done?: Yellow

**Priority:**
- high: Red
- medium: Yellow
- low: Gray

**Source:**
- slack: Purple
- gmail: Red
- zoom: Blue
- notion: Black

---

## Part 2: Setup Guide Page Specification

### 2.1 Page Structure

```markdown
# Todo Aggregator Setup Guide

Welcome! This guide will help you set up automatic todo extraction from Slack, Gmail, and Zoom.

## Prerequisites
- [ ] Zapier account (Free or paid)
- [ ] Notion workspace (you're here!)
- [ ] Slack workspace access
- [ ] Gmail account
- [ ] Zoom account with AI Companion (optional - captured via Gmail)

## Step 1: Notion Setup (Required)

### 1.1 Connect Your Database
1. Open your Todos database in Notion
2. Click the **"..."** menu in the top right
3. Select **"Connections"** → **"Connect to"** → **"Todo Aggregator"**

### 1.2 Get Your Database ID
1. Open the Todos database in full page view
2. Look at the URL: `notion.so/[workspace]/[DATABASE_ID]?v=...`
3. Copy just the 32-character ID (the part before `?v=`)

### 1.3 Your Notion Credentials
- **Database ID**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## Step 2: Slack Setup (Required)

### 2.1 Install the Todo Aggregator App
1. Click this link: [Install Todo Aggregator for Slack](https://matterintelligence.slack.com/oauth?client_id=5416048952740.10046227645252&scope=&user_scope=channels%3Ahistory%2Cchannels%3Aread%2Cgroups%3Ahistory%2Cgroups%3Aread%2Cim%3Ahistory%2Cim%3Aread%2Cmpim%3Ahistory%2Cmpim%3Aread%2Cusers%3Aread&redirect_uri=&state=&granular_bot_scope=1&single_channel=0&install_redirect=&tracked=1&user_default=0&team=)
2. Select your workspace (if prompted)
3. Review permissions and click "Allow"
4. Copy your "User OAuth Token" (starts with `xoxp-`)

### 2.2 Your Slack Credentials
- **Slack User Token**: `xoxp-xxxxxxxxxx-xxxxxxxxxx-xxxxxxxxxxxxx`

---

## Step 3: Gmail Setup (Required)

### 3.1 Create Google Cloud Project
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create new project: "Todo Aggregator"
3. Enable Gmail API:
   - Go to "APIs & Services" → "Library"
   - Search "Gmail API" → Enable

### 3.2 Create OAuth Credentials
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: "Desktop app"
4. Name: "Todo Aggregator"
5. Download the JSON file

### 3.3 Generate Refresh Token
Run the Gmail OAuth setup script (one-time):
```bash
python scripts/gmail_oauth_setup.py
```
This will open a browser, authenticate, and print your refresh token.

### 3.4 Your Gmail Credentials
- **Gmail Refresh Token**: `1//0gxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## Step 4: Zapier Setup (Required)

### 4.1 Create New Zap
1. Go to [zapier.com](https://zapier.com) and create new Zap
2. Or use our template: [TEMPLATE_LINK]

### 4.2 Configure Trigger
- **App**: Schedule by Zapier
- **Event**: Every Day
- **Time**: 7:00 AM (your timezone)
- **Day of Week**: Every day (or customize)

### 4.3 Configure Action
- **App**: Webhooks by Zapier
- **Event**: POST
- **URL**: `https://todo-aggregator-[your-deployment].run.app/run`
- **Payload Type**: JSON
- **Headers**:
  - `X-API-Secret`: [Your API Secret]
  - `Content-Type`: application/json

### 4.4 Request Body
```json
{
  "slack_token": "xoxp-your-token-here",
  "gmail_refresh_token": "1//your-refresh-token",
  "notion_database_id": "your-database-id",
  "notion_meetings_db_id": "",
  "user_name": "Your Name",
  "user_email": "you@email.com",
  "user_slack_username": "Your Slack Display Name"
}
```

### 4.5 Test & Enable
1. Click "Test" to verify connection
2. Turn on your Zap

---

## Troubleshooting

### Common Issues

**"Invalid API secret"**
- Check X-API-Secret header matches your deployment

**"No todos created"**
- Verify Slack/Gmail tokens are valid
- Check that you have recent messages (last 24h)
- Ensure user_name matches how you're mentioned in messages

**"Notion API error"**
- Verify database is connected to integration
- Check all required properties exist in database

**Rate Limits**
- Slack: The app handles rate limits automatically
- Gmail: If you hit limits, reduce GMAIL_LOOKBACK_DAYS

### Getting Help
- GitHub Issues: [link]
- Email: [support email]
```

---

## Part 3: Zapier Template Specification

### 3.1 Template Metadata

- **Name**: Todo Aggregator - Daily Sync
- **Description**: Automatically extract todos from Slack, Gmail, and Zoom into your Notion database using AI.
- **Category**: Productivity

### 3.2 Trigger Configuration

| Setting | Value |
|---------|-------|
| **App** | Schedule by Zapier |
| **Trigger Event** | Every Day |
| **Time of Day** | 7:00 AM |
| **Timezone** | User's timezone (placeholder) |
| **Days of Week** | Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday |

### 3.3 Action Configuration

| Setting | Value |
|---------|-------|
| **App** | Webhooks by Zapier |
| **Action Event** | POST |
| **URL** | `https://todo-aggregator-908833572352.us-central1.run.app/run` |
| **Payload Type** | JSON |
| **Unflatten** | No |

### 3.4 Headers

| Header | Value | User Input? |
|--------|-------|-------------|
| `X-API-Secret` | `[placeholder]` | Yes - Required |
| `Content-Type` | `application/json` | No - Pre-filled |

### 3.5 Request Body Fields

| Field | Placeholder Text | Required | Help Text |
|-------|------------------|----------|-----------|
| `notion_database_id` | `xxx` | Yes | The 32-character ID from your Todos database URL |
| `slack_token` | `xoxp-xxx` | Yes | Your Slack User OAuth Token from Step 2. |
| `gmail_refresh_token` | `1//xxx` | Yes | Your Gmail refresh token from Step 3. |
| `notion_meetings_db_id` | `` | No | Database ID for Notion AI meeting notes. Leave empty to skip. |
| `user_name` | `Your Name` | Yes | Your name (or comma-separated variations like "Clay,clay,Clay Sader") |
| `user_email` | `you@email.com` | No | Your email for error notifications |
| `user_slack_username` | `Your Display Name` | No | Your Slack display name for accurate todo extraction |

### 3.6 Template JSON Structure

```json
{
  "notion_database_id": "",
  "notion_meetings_db_id": "",
  "slack_token": "",
  "gmail_refresh_token": "",
  "user_name": "",
  "user_email": "",
  "user_slack_username": ""
}
```

---

## Part 4: Implementation Checklist

### Notion Template Creation
- [ ] Create template page "Todo Aggregator"
- [ ] Add inline Todos database with all properties
- [ ] Configure select options with colors
- [ ] Create 5 database views (All, Active, By Priority, By Source, This Week)
- [ ] Create "Setup Guide" child page
- [ ] Write all setup instructions
- [ ] Add credential placeholder sections
- [ ] Publish template as shareable

### Zapier Template Creation
- [ ] Create new Zap
- [ ] Configure Schedule trigger (daily 7am)
- [ ] Configure Webhooks POST action
- [ ] Set URL to production endpoint
- [ ] Add X-API-Secret header (placeholder)
- [ ] Add Content-Type header (pre-filled)
- [ ] Configure JSON body with all fields
- [ ] Add help text for each field
- [ ] Test the template
- [ ] Publish as shareable template

---

## Files to Reference (No Code Changes Needed)

- [api/app.py](api/app.py) - API endpoint contract (RunRequest model)
- [src/mcp_clients/notion_client.py](src/mcp_clients/notion_client.py) - Database property names
- [src/config.py](src/config.py) - Environment variable names

---

## Notes

- **No code changes required** - This is purely external template creation
- **Users provide their own secrets** - Zapier handles secure storage per-user
- **Documentation lives in Notion** - No markdown files in the repo
- **Production URL**: `https://todo-aggregator-908833572352.us-central1.run.app/run`

---

## Part 5: Notion Template Content (For Refinement)

This is the full content to create in Notion. Copy/paste and refine as needed.

---

### Main Page: Todo Aggregator

```
# 🎯 Todo Aggregator

Automatically extract todos from Slack, Gmail, and Zoom into this Notion database using AI.

## How It Works

1. **Connect** your Slack, Gmail, and Notion accounts
2. **Schedule** a daily Zapier automation
3. **Relax** as todos are automatically extracted and organized

The AI analyzes your messages to find:
- Explicit requests ("Can you review this?")
- Commitments you made ("I'll send that over")
- Action items from meetings

Each todo links back to the original message so you never lose context.

---

## 📋 Your Todos

[INLINE DATABASE: Todos]

---

## 🚀 Get Started

👉 **[Setup Guide](./Setup%20Guide)** - Follow the step-by-step instructions to connect your accounts

---

## Features

✅ **Multi-platform** - Slack, Gmail, Zoom, Notion AI notes
✅ **Smart extraction** - AI identifies todos from natural conversation
✅ **Deduplication** - Same todo mentioned twice? Only added once
✅ **Completion detection** - Marks todos done when you say "Done!" in the original thread
✅ **Priority scoring** - Detects urgent keywords and assigns priority
✅ **Auto-categorization** - Tags todos as follow-up, review, meeting, etc.
✅ **Source links** - Click through to the original message
```

---

### Setup Guide Page

```
# 🛠️ Setup Guide

Welcome! This guide will help you set up automatic todo extraction from Slack, Gmail, and Zoom.

**Estimated time: 20-30 minutes**

---

## ✅ Prerequisites

Before you begin, make sure you have:

- [ ] A Zapier account (free tier works)
- [ ] Admin access to your Slack workspace (or ability to install apps)
- [ ] A Gmail account
- [ ] A Zoom account with AI Companion enabled (optional)

---

## Step 1: Notion Setup

### 1.1 Connect Your Database

1. Go back to the **Todos database** on the main page
2. Click the **"..."** menu in the top right
3. Select **"Connections"** → **"Connect to"** → **"Todo Aggregator"**

### 1.2 Get Your Database ID

1. Open the Todos database in full page view
2. Look at the URL: `notion.so/[workspace]/[DATABASE_ID]?v=...`
3. Copy the **32-character ID** (the part before `?v=`)

> 💡 Example: If URL is `notion.so/myspace/abc123def456...?v=xyz`, copy `abc123def456...`

### 📝 Your Notion Credentials

| Credential | Value |
|------------|-------|
| **Database ID** | `________________________________` |

---

## Step 2: Slack Setup

### 2.1 Install the Todo Aggregator App

1. Click this link to install: **[Install Todo Aggregator for Slack](https://matterintelligence.slack.com/oauth?client_id=5416048952740.10046227645252&scope=&user_scope=channels%3Ahistory%2Cchannels%3Aread%2Cgroups%3Ahistory%2Cgroups%3Aread%2Cim%3Ahistory%2Cim%3Aread%2Cmpim%3Ahistory%2Cmpim%3Aread%2Cusers%3Aread&redirect_uri=&state=&granular_bot_scope=1&single_channel=0&install_redirect=&tracked=1&user_default=0&team=)**
2. Select your workspace (if prompted)
3. Review the permissions and click **"Allow"**
4. After authorization, you'll see a page with your **User OAuth Token**
5. Copy the token (starts with `xoxp-`)

> ⚠️ Keep this token secret! Anyone with it can read your Slack messages.

### 📝 Your Slack Credentials

| Credential | Value |
|------------|-------|
| **Slack User Token** | `xoxp-____________________________` |

---

## Step 3: Gmail Setup

### 3.1 Create a Google Cloud Project

1. Go to **[console.cloud.google.com](https://console.cloud.google.com)**
2. Click the project dropdown → **"New Project"**
3. Name it `Todo Aggregator` and click **"Create"**
4. Make sure your new project is selected

### 3.2 Enable Gmail API

1. Go to **"APIs & Services"** → **"Library"**
2. Search for **"Gmail API"**
3. Click on it and then click **"Enable"**

### 3.3 Configure OAuth Consent Screen

1. Go to **"APIs & Services"** → **"OAuth consent screen"**
2. Select **"External"** and click **"Create"**
3. Fill in required fields:
   - **App name**: `Todo Aggregator`
   - **User support email**: Your email
   - **Developer contact**: Your email
4. Click **"Save and Continue"** through the remaining steps
5. Under **"Test users"**, add your email address

### 3.4 Create OAuth Credentials

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"+ Create Credentials"** → **"OAuth client ID"**
3. Select:
   - **Application type**: `Desktop app`
   - **Name**: `Todo Aggregator`
4. Click **"Create"**
5. Click **"Download JSON"** and save the file

### 3.5 Generate Your Refresh Token

You'll need to run a one-time script to get your refresh token:

1. Install Python if you haven't already
2. Download our OAuth setup script
3. Place the downloaded JSON file in the same folder
4. Run:

```bash
pip install google-auth-oauthlib
python gmail_oauth_setup.py
```

5. A browser will open - sign in and authorize
6. Copy the **refresh token** that's printed

> 💡 The refresh token is long-lived - you only need to do this once

### 📝 Your Gmail Credentials

| Credential | Value |
|------------|-------|
| **Gmail Refresh Token** | `1//_____________________________` |

---

## Step 4: Zapier Setup

### 4.1 Create a New Zap

1. Go to **[zapier.com](https://zapier.com)** and sign in
2. Click **"+ Create"** → **"Zaps"** → **"New Zap"**

### 4.2 Configure the Trigger

1. Search for **"Schedule by Zapier"**
2. Select **"Every Day"** as the trigger event
3. Configure:
   - **Time of Day**: `7:00 AM` (or your preferred time)
   - **Timezone**: Your timezone
   - **Days of Week**: Select all days (or customize)
4. Click **"Continue"** and **"Test trigger"**

### 4.3 Configure the Action

1. Click **"+"** to add an action
2. Search for **"Webhooks by Zapier"**
3. Select **"POST"** as the action event
4. Configure:

| Field | Value |
|-------|-------|
| **URL** | `https://todo-aggregator-908833572352.us-central1.run.app/run` |
| **Payload Type** | `json` |

5. Add **Headers**:

| Key | Value |
|-----|-------|
| `X-API-Secret` | `[Ask Clay for the API secret]` |
| `Content-Type` | `application/json` |

6. Add **Data** fields:

| Key | Value |
|-----|-------|
| `notion_database_id` | Your Database ID from Step 1 |
| `slack_token` | Your Slack token from Step 2 |
| `gmail_refresh_token` | Your Gmail refresh token from Step 3 |
| `user_name` | Your name (e.g., `Clay` or `Clay,clay,Clay Sader`) |
| `user_email` | Your email (for error notifications) |
| `user_slack_username` | Your Slack display name |
| `notion_meetings_db_id` | Leave empty (or add Notion AI notes DB) |

### 4.4 Test & Publish

1. Click **"Test step"** to verify the connection
2. If successful, you'll see a response like:
   ```json
   {"created": 0, "skipped": 0, "completed": 0, "duration_seconds": 5.2}
   ```
3. Click **"Publish"** to activate your Zap

---

## 🎉 You're All Set!

Your Todo Aggregator will now run daily and extract todos from your Slack, Gmail, and Zoom messages.

### What to Expect

- **First run**: May find todos from the past 24 hours
- **Daily**: New todos appear automatically
- **Duplicates**: Same todo won't be added twice
- **Completions**: Say "Done!" in the original thread to auto-complete

### Tips

- Check your Todos database daily
- Use the "Active" view to focus on open items
- Click "Source URL" to jump to the original message
- Mark "Done?" items as "Done" or "Open" after reviewing

---

## 🔧 Troubleshooting

### "Invalid API secret"
- Double-check the `X-API-Secret` header in Zapier
- Contact Clay to verify you have the correct secret

### "No todos created"
- This is normal if you have no recent messages with todos
- Check that your Slack/Gmail tokens are valid
- Verify `user_name` matches how people address you

### "Notion API error"
- Ensure the database is connected to your integration (Step 1.2)
- Verify all required properties exist in the database

### Token Expired
- **Slack**: Tokens don't expire unless you revoke them
- **Gmail**: Refresh tokens are long-lived but may expire after inactivity
- **Notion**: Integration secrets don't expire

### Still stuck?
- Check the Zapier task history for error details
- Contact Clay with the error message
```

---

### Gmail OAuth Setup Script

Users will need this script. Consider hosting it or including download link:

```python
# gmail_oauth_setup.py
"""
One-time script to generate Gmail refresh token.
Run this locally, then copy the refresh token to Zapier.
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json',  # Downloaded from Google Cloud Console
        SCOPES
    )
    creds = flow.run_local_server(port=0)

    print("\n" + "="*50)
    print("SUCCESS! Here's your refresh token:")
    print("="*50)
    print(f"\n{creds.refresh_token}\n")
    print("="*50)
    print("Copy this token and paste it into Zapier.")
    print("You only need to do this once.")

if __name__ == '__main__':
    main()
```
