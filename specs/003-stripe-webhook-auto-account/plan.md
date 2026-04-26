# Implementation Plan: Stripe Webhook Auto Account

**Feature**: Stripe Webhook Auto Account  
**Branch**: `003-stripe-webhook-auto-account`  
**Date**: 2026-04-26  
**Status**: Planned

## Technical Context

### Architecture
- **Frontend**: Django templates + HTMX + Alpine.js (Anti-SPA per Constitution)
- **Backend**: Django 5.x views (thin) + Python services (business logic in `services.py`)
- **Database**: Supabase PostgreSQL with `supabase-py` client (Anti-ORM: Django ORM is prohibited for all core user/profile data)
- **Auth**: Supabase Auth with magic links, 90-day JWT sessions
- **Payment**: Stripe Checkout + Webhooks

### Dependencies
- Django 5.x
- supabase-py
- stripe-python
- HTMX + Alpine.js (frontend)

### Unknowns Resolved (via research.md)
- ✅ Webhook signature validation: Use Stripe official SDK
- ✅ Idempotency: Track `evt_xxx` IDs in `processed_webhook_events` table
- ✅ Magic links: Use Supabase Auth `signInWithOtp`
- ✅ User creation order: Auth user first, then profile

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| UX Fricção Zero | ✅ Pass | Webhook is backend-only; no user-facing latency concerns |
| Anti-SPA | ✅ Pass | No React/Vue/Angular; HTMX + Alpine.js only |
| Service Layer | ✅ Pass | All business logic in `services.py`; views are thin adapters |
| Anti-ORM (dados core) | ✅ Pass | `supabase-py` for all profile/user data; Django ORM is prohibited for `profiles`, `processed_webhook_events`, and all user-related tables |
| RLS-First | ✅ Pass | All patient (children) queries filter by `parent_id`; UUIDs serialized as `str(uuid)` |
| Offline-First | ⚠️ N/A | Webhook handler is online-only by nature |
| Type Hinting | ✅ Pass | All Python code uses strict type hints |
| Lock-in por utilidade | ✅ Pass | Users can export their data via existing profile endpoints |

## Implementation Phases

### Phase 1: Database & Infrastructure
1. Create Supabase migration for `profiles`, `processed_webhook_events`, `magic_link_logs` tables (Anti-ORM: all user data in Supabase)
2. Enable RLS and create policies
3. Configure Stripe webhook endpoint in dashboard
4. Configure Supabase Auth settings (magic link, 90-day JWT)
5. Set environment variables

### Phase 2: Webhook Handler Service
1. Create `services/stripe_webhook.py` with:
   - `validate_signature(payload: bytes, signature: str, secret: str) -> bool`
   - `process_payment_intent_succeeded(event: dict) -> dict`
   - `create_user_from_payment(email: str, name: str, stripe_customer_id: str) -> UUID`
   - `is_event_processed(event_id: str) -> bool`
   - `mark_event_processed(event_id: str, status: str, error: str = None)`
2. Handle idempotency via `processed_webhook_events` table
3. Handle duplicate users (check by email before creating)
4. Handle missing email (return error, no retry)

### Phase 3: Magic Link Service
1. Create `services/magic_link.py` with:
   - `send_magic_link(email: str, user_id: UUID, triggered_by: str) -> bool`
   - `has_active_session(user_id: UUID) -> bool`
   - `log_magic_link_send(user_id: UUID, email: str, triggered_by: str)`
2. Integrate with Supabase Auth `signInWithOtp`
3. Handle email sending failures (log but don't fail webhook)

### Phase 4: Django Views & URLs
1. Create `views/webhooks.py`:
   - `stripe_webhook(request: HttpRequest) -> JsonResponse`
   - Thin view: validate input → call service → return response
2. Create `views/auth.py`:
   - `magic_link_callback(request: HttpRequest) -> HttpResponseRedirect`
   - Handle Supabase callback and session setup
3. Add URL routes:
   - `POST /webhooks/stripe`
   - `GET /auth/callback`

### Phase 5: Frontend Integration
1. Create magic link email template (in Supabase dashboard)
2. Create auth callback page (`/auth/callback`) with HTMX
3. Create dashboard redirect after successful magic link login
4. Add Alpine.js for session status checks

### Phase 6: Testing & Validation
1. Unit tests for webhook signature validation
2. Unit tests for idempotency logic
3. Integration tests with Stripe CLI test events
4. End-to-end test: payment → webhook → magic link → login
5. Test edge cases:
   - Duplicate events
   - Invalid signatures
   - Missing emails
   - Existing users with/without active sessions

### Phase 7: Deployment & Monitoring
1. Deploy webhook endpoint to production
2. Configure Stripe production webhook
3. Set up error monitoring for webhook failures
4. Test magic link deliverability
5. Document operational runbook

## File Structure

Per Constitution L136-L147, all application code resides in `src/`. This feature uses the Django app `payments`.

```
src/
├── apps/
│   └── payments/
│       ├── __init__.py
│       ├── services.py        # Webhook + Magic Link business logic (Constitution III)
│       ├── views.py           # Stripe webhook endpoint + Auth callback
│       ├── urls.py            # App URL routing
│       └── templates/
│           └── payments/
│               └── partials/
│                   └── auth_callback_partial.html  # HTMX partial (Constitution II)
├── config/
│   ├── settings.py            # Environment variables
│   └── urls.py                # Root URL routing (includes payments.urls)
├── static/                    # Tailwind + Alpine.js assets
└── tests/
    ├── test_webhook.py
    ├── test_magic_link.py
    └── test_integration.py

migrations/                      # Supabase SQL migrations (root level)
├── 001_profiles.sql
├── 002_processed_webhook_events.sql
├── 003_magic_link_logs.sql
└── 004_audit_logs.sql
```

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Webhook endpoint DDoS | Stripe signature validation rejects non-Stripe requests |
| Duplicate account creation | Idempotency tracker + unique email constraint |
| Email deliverability issues | Log failures, manual retry via admin panel |
| Magic link security | Supabase Auth handles token expiry and single-use |
| Database failures during webhook | Return 500 to Stripe → automatic retry |

## Success Criteria Validation

| Criterion | How to Validate |
|-----------|-----------------|
| SC-001: 100% webhooks processed in < 3s | Monitor response times in logs |
| SC-002: 100% invalid signatures rejected | Unit tests + security audit |
| SC-003: 0% duplicate accounts | Integration test with Stripe CLI retries |
| SC-004: 100% appropriate responses | Log analysis + Stripe webhook delivery status |

## Next Steps

1. Run `/speckit.tasks` to generate implementation tasks
2. Start with Phase 1 (database migrations)
3. Follow with Phase 2 (webhook service)
