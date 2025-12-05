# Project Plan: GCP Native Todo Aggregator

## Overview
Replace Zapier-based automation with a fully GCP-native solution featuring:
- Simple web form for user registration
- Firestore for user config storage
- Secret Manager for credential security
- Cloud Scheduler for daily automation
- Email summaries of results

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Simple Web Form (Cloud Run)                                │
│  /register - User enters credentials                        │
│  /dashboard - View/edit config (future)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌──────────────────┐    ┌─────────────────────┐
│  Firestore       │    │  Secret Manager     │
│  users/{uid}     │    │  slack_{uid}        │
│  - email         │    │  gmail_{uid}        │
│  - name          │    │                     │
│  - notion_db_id  │    │  (shared)           │
│  - enabled       │    │  anthropic_api_key  │
│  - created_at    │    │  notion_api_key     │
└──────────────────┘    └─────────────────────┘
          │                       │
          └───────────┬───────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Cloud Scheduler                                            │
│  - Cron: "0 14 * * *" (7am PT = 14:00 UTC)                 │
│  - Target: POST /run-all                                    │
│  - Auth: OIDC token                                         │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Cloud Run API                                              │
│  POST /run-all        - Process all enabled users          │
│  POST /run/{user_id}  - Process single user                │
│  POST /register       - Create new user                    │
│  GET  /health         - Health check                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌──────────────────┐    ┌─────────────────────┐
│  Notion API      │    │  SMTP (Email)       │
│  Write todos     │    │  Send summary       │
└──────────────────┘    └─────────────────────┘
```

---

## Implementation Phases

### Phase 1: GCP Infrastructure Setup ✅ COMPLETE
**Goal**: Set up Firestore, Secret Manager, and update Cloud Run permissions

**Tasks**:
- [x] Enable Firestore in Native mode
- [x] Create Secret Manager secrets for shared credentials
- [x] Grant Cloud Run service account access to Firestore + Secret Manager

**Completed**: 2025-12-04

**What was set up**:
- **Firestore**: Native mode, us-central1, free tier
- **Secrets created**:
  - `anthropic-api-key`
  - `notion-api-key`
  - `gmail-client-id`
  - `gmail-client-secret`
  - `registration-access-code` (value: shared in Notion)
- **Service Account**: `908833572352-compute@developer.gserviceaccount.com`
  - Granted `roles/datastore.user`
  - Granted `roles/secretmanager.secretAccessor`

---

### Phase 2: User Management Backend ✅ COMPLETE
**Goal**: API endpoints for user registration and retrieval

**Tasks**:
- [x] Create Firestore client utility
- [x] Create Secret Manager client utility
- [x] Add POST /register endpoint
- [x] Add GET /users/{user_id} endpoint (admin)
- [x] Add DELETE /users/{user_id} endpoint (admin)
- [x] Add GET /users endpoint (admin - list all)

**Completed**: 2025-12-04

**Files to create**:
- `src/gcp/firestore_client.py` - Firestore operations
- `src/gcp/secret_manager.py` - Secret Manager operations

**Files to modify**:
- `api/app.py` - Add new endpoints

**Data Model** (Firestore):
```python
# users/{user_id}
{
    "email": "user@example.com",
    "name": "User Name",
    "slack_username": "user",
    "notion_database_id": "abc123...",
    "enabled": True,
    "created_at": datetime,
    "last_run": datetime | None,
    "last_run_status": "success" | "error" | None,
}
```

**Secrets** (Secret Manager):
- `slack-token-{user_id}` - User's Slack token
- `gmail-refresh-token-{user_id}` - User's Gmail refresh token

---

### Phase 3: Registration Web Form ✅ COMPLETE
**Goal**: Simple HTML form for user self-registration

**Tasks**:
- [x] Create static HTML registration form
- [x] Add form validation (client-side)
- [x] Add access code field (simple password protection)
- [x] Connect form to POST /register
- [x] Add success/error feedback

**Completed**: 2025-12-04

**Files created**:
- `api/static/register.html` - Registration form with all fields
- `api/static/style.css` - Clean, responsive styling

**Files modified**:
- `api/app.py` - Added static file mounting and root route

**Form Features**:
- Access code validation (server-side via Secret Manager)
- Client-side validation for Notion database ID (hex chars, 32 max)
- Help links for obtaining Slack token
- Success/error feedback with clear messaging
- Responsive design for mobile
- Idempotent registration (re-register updates existing user)

**Access Code**: Stored in Secret Manager as `registration-access-code`

---

### Phase 4: Batch Processing Endpoint ✅ COMPLETE
**Goal**: /run-all endpoint that processes all enabled users

**Tasks**:
- [x] Add POST /run-all endpoint
- [x] Fetch all enabled users from Firestore
- [x] Fetch credentials from Secret Manager for each user
- [x] Process users sequentially
- [x] Track success/failure per user
- [x] Update last_run and last_run_status in Firestore
- [x] Add POST /run/{user_id} endpoint for single-user runs

**Completed**: 2025-12-04

**New Endpoints**:
- `POST /run-all` - Process all enabled users (OIDC or API secret auth)
- `POST /run/{user_id}` - Process single user (API secret auth)

**Authentication**:
- Cloud Scheduler: OIDC Bearer token in Authorization header
- Manual: X-API-Secret header

**Processing Flow**:
1. Fetch enabled users from Firestore
2. For each user, fetch credentials from Secret Manager
3. Build RunRequest and call existing process_aggregation
4. Update last_run/last_run_status in Firestore
5. Send error email on failure

---

### Phase 4.5: Personal Trigger URLs ✅ COMPLETE
**Goal**: Allow users to trigger their own runs via a personal URL

**Tasks**:
- [x] Add `personal_token` field to Firestore user documents
- [x] Add `GET /trigger/{user_id}/{token}` endpoint
- [x] Add `send_welcome_email()` function
- [x] Send welcome email after registration

**Completed**: 2025-12-04

**New Endpoint**:
- `GET /trigger/{user_id}/{token}` - User triggers their own run (returns friendly HTML)

**Welcome Email**:
- Sent automatically after registration
- Contains personal trigger URL
- Note about automatic daily runs at 7am PT
- Link to Notion database

**Flow**:
1. User registers → `personal_token` generated in Firestore
2. Welcome email sent with trigger URL
3. User clicks URL anytime → validates token → queues run → shows HTML confirmation

---

### Phase 5: Email Notifications ✅ COMPLETE
**Goal**: Send email with aggregation results (success or failure)

**Tasks**:
- [x] Create success email template (HTML)
- [x] Create failure email template (HTML)
- [x] Add summary generation to process flow
- [x] Send success email after successful run
- [x] Send failure email if run fails (with error details)

**Completed**: 2025-12-05

**Files created**:
- `src/notifications/__init__.py` - Package exports
- `src/notifications/email_sender.py` - Email sending utility (send_success_email, send_error_email, send_welcome_email)
- `src/notifications/templates.py` - HTML email templates

**Files modified**:
- `api/app.py` - Imports from notifications module, calls send_success_email after successful runs

**Email Features**:
- HTML templates with inline CSS for email compatibility
- Success email includes: new todos created, todos auto-completed, Slack/Gmail message counts
- Error email includes: error details, link to re-register
- Welcome email includes: personal trigger URL, Notion database link
- All emails have emoji subjects for visual distinction

---

### Phase 6: Cloud Scheduler Setup ← NEXT
**Goal**: Automated daily trigger at 7am PT

**Status**: Not started - Cloud Scheduler API needs to be enabled

**Tasks**:
- [ ] Enable Cloud Scheduler API
- [ ] Create Cloud Scheduler job
- [ ] Configure OIDC authentication
- [ ] Test scheduled execution
- [ ] Verify first automated run

**Commands**:
```bash
# Enable Cloud Scheduler API
gcloud services enable cloudscheduler.googleapis.com --project=todo-aggregator-480119

# Create scheduler job (7am PT = 14:00 UTC during PST, 15:00 UTC during PDT)
gcloud scheduler jobs create http todo-aggregator-daily \
  --location=us-central1 \
  --schedule="0 15 * * *" \
  --time-zone="America/Los_Angeles" \
  --uri="https://todo-aggregator-908833572352.us-central1.run.app/run-all" \
  --http-method=POST \
  --oidc-service-account-email=908833572352-compute@developer.gserviceaccount.com \
  --oidc-token-audience="https://todo-aggregator-908833572352.us-central1.run.app" \
  --project=todo-aggregator-480119

# Verify job was created
gcloud scheduler jobs list --location=us-central1 --project=todo-aggregator-480119
```

---

### Phase 7: Testing & Deployment
**Goal**: End-to-end testing and production deployment

**Tasks**:
- [ ] Test registration flow locally
- [ ] Test /run-all with multiple users
- [ ] Test email delivery
- [ ] Deploy updated Cloud Run service
- [ ] Create Cloud Scheduler job
- [ ] Monitor first automated run

---

## Files Summary

### New Files
| File | Purpose |
|------|---------|
| `src/gcp/__init__.py` | Package init |
| `src/gcp/firestore_client.py` | Firestore operations |
| `src/gcp/secret_manager.py` | Secret Manager operations |
| `src/notifications/__init__.py` | Package exports |
| `src/notifications/email_sender.py` | Email sending (success, error, welcome) |
| `src/notifications/templates.py` | HTML email templates |
| `api/static/register.html` | Registration form |
| `api/static/style.css` | Form styling |

### Modified Files
| File | Changes |
|------|---------|
| `api/app.py` | Add /register, /run-all endpoints; serve static files; validate access code |
| `requirements.txt` | Add google-cloud-firestore, google-cloud-secret-manager |
| `Dockerfile` | Copy static files |

### Secret Manager Secrets
| Secret | Purpose |
|--------|---------|
| `anthropic-api-key` | Claude API (shared) |
| `notion-api-key` | Notion API (shared) |
| `gmail-client-id` | Gmail OAuth client (shared) |
| `gmail-client-secret` | Gmail OAuth client (shared) |
| `registration-access-code` | Form password (shared) |
| `slack-token-{user_id}` | Per-user Slack token |
| `gmail-refresh-token-{user_id}` | Per-user Gmail token |

---

## Security Considerations

1. **Registration form protection**: Add a simple shared secret/password to prevent spam registrations
2. **Admin endpoints**: Protect /users endpoints with API key
3. **Secret Manager**: User credentials never logged or returned in responses
4. **OIDC auth**: Cloud Scheduler uses service account, not shared API secret

---

## Cost Estimate (Monthly)

| Service | Estimate |
|---------|----------|
| Cloud Run | ~$0-5 (low traffic) |
| Firestore | ~$0 (free tier: 50K reads/day) |
| Secret Manager | ~$0.06 per secret version |
| Cloud Scheduler | ~$0.10 per job |
| **Total** | **~$1-5/month** |

---

## Decisions

1. **Registration protection**: Simple shared password field (shared in Notion setup guide)
2. **User management**: No dashboard - Firestore console + gcloud commands
3. **Error handling**: Send email notification on failure (no auto-retry)
4. **Processing**: Sequential (optimize later if needed)

---

## Next Steps

1. ~~Phase 1: GCP Infrastructure Setup~~ ✅ Complete
2. ~~Phase 2: User Management Backend~~ ✅ Complete
3. ~~Phase 3: Registration Web Form~~ ✅ Complete
4. ~~Phase 4: Batch Processing Endpoint~~ ✅ Complete
5. ~~Phase 4.5: Personal Trigger URLs~~ ✅ Complete
6. ~~Phase 5: Email Notifications~~ ✅ Complete
7. **Phase 6: Cloud Scheduler Setup** ← Next (required for automated daily runs)
8. Phase 7: Testing & Deployment
