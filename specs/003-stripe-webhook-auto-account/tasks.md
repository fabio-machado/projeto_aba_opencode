# Tasks: Stripe Webhook Auto Account

**Input**: Design documents from `specs/003-stripe-webhook-auto-account/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL - not explicitly requested in this feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency configuration

- [X] T001 [P] Add `stripe-python` and `supabase-py` dependencies in `requirements.txt` or `pyproject.toml`
- [X] T002 [P] Add Stripe and Supabase environment variables (`STRIPE_WEBHOOK_SECRET`, `STRIPE_SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_ANON_KEY`) in `src/config/settings.py`
- [X] T002b Create Django app `payments` with `python src/manage.py startapp payments` and register in `INSTALLED_APPS`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema and core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Create SQL migration for `profiles` table with RLS policies in `migrations/001_profiles.sql`
- [X] T005 [P] Create SQL migration for `processed_webhook_events` table with RLS policies in `migrations/002_processed_webhook_events.sql`
- [X] T006 [P] Create SQL migration for `magic_link_logs` table with RLS policies in `migrations/003_magic_link_logs.sql`
- [X] T006b [P] Create SQL migration for `audit_logs` table with RLS policies in `migrations/004_audit_logs.sql` (Constitution IV: user_id/action/timestamp)
- [X] T007 Apply Supabase migrations and verify tables, indexes, and RLS policies in Supabase dashboard

**Checkpoint**: Foundation ready - all tables exist with proper RLS, user story implementation can now begin

---

## Phase 3: User Story 2 - Rejeição de webhooks com assinatura inválida (Priority: P1)

**Goal**: Secure the webhook endpoint by validating Stripe signatures, rejecting all unauthorized requests

**Independent Test**: Send POST request to `/webhooks/stripe` with invalid/missing `Stripe-Signature` header and verify HTTP 400 response with no user creation

### Implementation for User Story 2

- [X] T008 [US2] Implement Stripe signature validation function using `stripe.Webhook.construct_event` in `src/apps/payments/services.py`
- [X] T009 [US2] Create Django webhook endpoint view that validates signature, rejects invalid requests, and filters only `payment_intent.succeeded` events in `src/apps/payments/views.py`
- [X] T010 [US2] Add `POST /webhooks/stripe` route in `src/apps/payments/urls.py` and include in `src/config/urls.py`

**Checkpoint**: Webhook endpoint rejects invalid signatures with HTTP 400; only Stripe-signed requests pass through

---

## Phase 4: User Story 1 - Pagamento bem-sucedido cria conta automaticamente (Priority: P1) — MVP

**Goal**: Automatically create a Supabase Auth user and profile when a valid `payment_intent.succeeded` webhook is received

**Independent Test**: Send simulated `payment_intent.succeeded` Stripe event to `/webhooks/stripe` and verify new user exists in `auth.users` and `profiles` tables

### Implementation for User Story 1

- [X] T011 [US1] Implement Supabase Auth user creation function in `src/apps/payments/services.py`
- [X] T012 [P] [US1] Implement profile insertion with `supabase-py` (including `full_name`, `stripe_customer_id`, `subscription_status`) in `src/apps/payments/services.py`
- [X] T013 [US1] Implement existing user detection by email using Supabase Auth admin API in `src/apps/payments/services.py`
- [X] T014 [US1] Implement magic link sending for new users and existing inactive users (no active session) in `src/apps/payments/services.py`
- [X] T015 [US1] Integrate complete account creation flow into webhook view with proper HTTP 200/400/500 responses in `src/apps/payments/views.py`

**Checkpoint**: Valid Stripe webhook creates new user + profile; existing user returns 200 without duplicate; magic link sent for inactive users

---

## Phase 5: User Story 3 - Garantia de idempotência no processamento (Priority: P2)

**Goal**: Prevent duplicate processing of the same Stripe event using the event ID tracker

**Independent Test**: Send identical `payment_intent.succeeded` event (same `evt_xxx` ID) twice and verify only one user is created; second request returns HTTP 200 without side effects

### Implementation for User Story 3

- [X] T016 [US3] Implement `is_event_processed(stripe_event_id: str) -> bool` check using `processed_webhook_events` table in `src/apps/payments/services.py`
- [X] T017 [US3] Implement `mark_event_processed()` tracking and integrate idempotency check at the start of webhook flow in `src/apps/payments/services.py`

**Checkpoint**: Duplicate Stripe events are detected and silently acknowledged with HTTP 200; no duplicate users created

---

## Phase 6: User Story 4 - Acesso à conta via magic link (Priority: P2)

**Goal**: Enable passwordless login via magic link with 90-day Supabase Auth sessions

**Independent Test**: Click magic link from email and verify automatic authentication, session cookie set, and redirect to dashboard

### Implementation for User Story 4

- [X] T018 [US4] Implement `has_active_session(user_id: UUID) -> bool` check using Supabase Auth sessions in `src/apps/payments/services.py`
- [X] T019 [P] [US4] Implement magic link send via Supabase Auth `signInWithOtp` with audit logging in `src/apps/payments/services.py`
- [X] T020 [US4] Create magic link callback view that validates token and sets session cookie in `src/apps/payments/views.py`
- [X] T021 [US4] Add `GET /auth/callback` route in `src/apps/payments/urls.py`
- [X] T022 [P] [US4] Create auth callback HTMX partial (`src/apps/payments/templates/payments/partials/auth_callback_partial.html`) for session handling and dashboard redirect

**Checkpoint**: Magic link emails are sent; clicking link authenticates user with 90-day session; expired/used links show appropriate error

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, configuration, documentation, and Constitution compliance verification

- [X] T023 Add comprehensive error handling and structured logging for all webhook scenarios (signature fail, missing email, DB error, email fail) in `src/apps/payments/services.py`
- [X] T023b [P] Implement audit logging service that writes `user_id`, `action`, `timestamp` to `audit_logs` table (Constitution IV) in `src/apps/payments/services.py`
- [X] T024 Configure Stripe dashboard webhook endpoint (`/webhooks/stripe`) and Supabase Auth settings (90-day JWT expiry, magic link email template) — *Manual: requires dashboard access*
- [X] T025 [P] Create `.env.example` documentation with all required Stripe and Supabase environment variables
- [X] T025b [P] Add response time logging/metrics for webhook endpoint to validate SC-001 (< 3s processing)
- [X] T026 [P] Service Layer audit: verify all business logic resides in `src/apps/payments/services.py`, views in `src/apps/payments/views.py` are thin HTTP adapters with no business rules (Constitution III)
- [X] T027 [P] RLS-First audit: verify `profiles` queries use UUIDs serialized as `str(uuid)` before Supabase SDK calls; confirm RLS policies active on all tables (Constitution IV)
- [X] T028 [P] Type hints static analysis check (`mypy` or `pyright`) across all Python files in `src/apps/payments/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T001, T002) - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can proceed in priority order (P1 → P2) or in parallel (if staffed)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 2 (US2, P1)**: Can start after Foundational (Phase 2). No dependencies on other stories. Must be completed before US1 (webhook endpoint needs signature validation before account creation).
- **User Story 1 (US1, P1)**: Depends on US2 completion (shares webhook endpoint). Core MVP feature.
- **User Story 3 (US3, P2)**: Depends on US1 completion (enhances same webhook flow with idempotency). Can be done in parallel with US4 if desired.
- **User Story 4 (US4, P2)**: Depends on US1 completion (magic link service is called from US1's account creation flow for existing inactive users). Can be done in parallel with US3.

### Within Each User Story

- Services before views
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks (T001, T002) can run in parallel
- All database migration tasks (T003, T005, T006, T006b) can run in parallel
- T011 and T012 (US1 service functions) can run in parallel
- T018 and T019 (US4 service functions) can run in parallel
- T020, T021, T022 (US4 view, URL, template) can run in parallel after T018/T019
- All Polish tasks (T026, T027, T028) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch model/service creation tasks together:
Task: "T011 [US1] Implement Supabase Auth user creation function in src/apps/payments/services.py"
Task: "T012 [P] [US1] Implement profile insertion with supabase-py in src/apps/payments/services.py"

# Then integrate:
Task: "T013 [US1] Implement existing user detection by email in src/apps/payments/services.py"
Task: "T014 [US1] Implement magic link sending for new users and existing inactive users in src/apps/payments/services.py"
Task: "T015 [US1] Integrate complete account creation flow into webhook view in src/apps/payments/views.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: US2 - Signature Validation (security foundation)
4. Complete Phase 4: US1 - Account Creation (core value)
5. **STOP and VALIDATE**: Test MVP independently with Stripe CLI
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US2 (Signature Validation) → Test independently → Secure endpoint
3. Add US1 (Account Creation) → Test independently → Deploy/Demo (MVP!)
4. Add US3 (Idempotency) → Test independently → Deploy/Demo
5. Add US4 (Magic Link) → Test independently → Deploy/Demo
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US2 → US1 (sequential, same endpoint)
   - Developer B: US4 (magic link service, can start after US1 foundational service structure is ready)
3. Stories integrate at webhook handler level

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Total tasks: 30
- Tasks per user story: US2=3, US1=5, US3=2, US4=5
- Setup tasks: 3 | Foundational tasks: 5 | Polish tasks: 8
