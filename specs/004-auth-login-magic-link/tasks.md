# Tasks: Auth Login Screen (Magic Link Flow)

**Input**: Design documents from `/specs/004-auth-login-magic-link/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in the feature specification. Test tasks omitted.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `apps/auth_app` Django app and register it in project configuration.

- [ ] T001 Create `src/apps/auth_app/` directory structure with `__init__.py`, `apps.py`, `services.py`, `views.py`, `urls.py`, `middleware.py`, and template directories `templates/auth_app/partials/`
- [ ] T002 [P] Register `apps.auth_app` in `INSTALLED_APPS` in `src/config/settings/base.py`
- [ ] T003 [P] Add `path('', include('apps.auth_app.urls'))` to `urlpatterns` in `src/config/urls.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Supabase schema (login_attempts table) and core app wiring that ALL user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T004 Run Supabase migration `005_add_login_attempts` to create `login_attempts` table with indexes and RLS policy per `data-model.md` Section 4 (migration SQL in data-model.md §Migration)
- [ ] T005 Implement `AuthAppConfig` in `src/apps/auth_app/apps.py` following the pattern from `src/apps/payments/apps.py` (AppConfig with `default_auto_field`, `name = 'apps.auth_app'`, `label = 'auth_app'`)
- [ ] T006 [P] Implement Supabase client helper and shared type definitions in `src/apps/auth_app/services.py` (reuse `SupabaseService` singleton from `src/apps/core/services.py`; define type aliases for `LoginResult`, `LoginError`; import `AuditLogService`)
- [ ] T007 [P] Define URL patterns in `src/apps/auth_app/urls.py`: `login/` (GET), `login/` (POST), `logout/` (GET), `auth/callback/` (GET) with `app_name = 'auth_app'`

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 + 2 — Login com Magic Link & Rejeição de E-mail (Priority: P1) 🎯 MVP

**Goal**: Tela de login funcional em `/login`. Usuário pagante informa e-mail → recebe Magic Link → clica → entra na área restrita. E-mail não cadastrado/inativo recebe mensagem de erro amigável. Formulário substituído por feedback de sucesso após envio.

**Independent Test**: Submeter e-mail pagante válido → confirmar "Link enviado!". Submeter e-mail inexistente → confirmar "E-mail não encontrado". Clicar no Magic Link recebido → confirmar redirecionamento para área restrita com sessão ativa.

### Implementation for User Story 1 + 2

- [ ] T008 [US1] Create login page template `src/apps/auth_app/templates/auth_app/login.html` extending `base.html` with: single email input (`rounded-lg`, placeholder "seu@email.com", label associado), "Receber Acesso" button (`rounded-xl`, Teal-500 background, full width, min 48x48dp touch), instructional text "Enviaremos um link de acesso para o seu e-mail. Não é necessário senha.", support link "Problemas com seu acesso? Fale conosco" (reads `SUPPORT_EMAIL` from Django settings/env, renders as `mailto:` link), LGPD privacy notice link. Layout minimalista sem header fixo/bottom nav (login is public route). Uses HTMX `hx-post="/login" hx-target="#login-form" hx-swap="outerHTML"`. Follows spec 002 design tokens: Inter font, Slate surface, Teal-500 primary, WCAG AA contrast.
- [ ] T009 [P] [US1] Create HTMX feedback partial `src/apps/auth_app/templates/auth_app/partials/_login_feedback.html` with three states: (a) success card — "Link enviado! Verifique sua caixa de entrada e spam." (green bg, `role="status"`), (b) error inline — red/amber banner above the form for re-try (`role="alert"`), (c) loading — spinner indicator on button during submission. Form DOM ID is `login-form`, error DOM ID is `login-error`.
- [ ] T010 [P] [US1] Create Alpine.js login form controller `src/static/js/auth.js`: `loginForm()` component with `submitting: false`, `email: ''`, `error: ''`. Disables button while submitting via Alpine `x-bind:disabled`. Clears error on new input. Syncs loading state with HTMX events (`htmx:beforeRequest`, `htmx:afterRequest`).
- [ ] T011 [US1] Implement `validate_user(email: str) -> dict | None` in `src/apps/auth_app/services.py`: normalizes email (trim, lowercase), validates format (contains `@`), queries Supabase `profiles` JOIN `auth.users` by email with service_role key, returns `{id, subscription_status, has_generator_access, has_library_access}` if found and status is `active`/`trialing`, returns `None` if not found, raises `AccountInactiveError` if status is `canceled`/`past_due`.
- [ ] T012 [P] [US1] Implement `send_magic_link(email: str, user_id: str) -> bool` in `src/apps/auth_app/services.py`: calls `supabase.auth.signInWithOtp({email, options: {emailRedirectTo: REDIRECT_TO_URL + '/auth/callback'}})`, inserts record in Supabase `magic_link_logs` with `triggered_by='user_request'` and `status='sent'`, inserts audit log via `AuditLogService.log_audit_event(action='magic_link_sent', user_id, metadata={email})`. Returns `True` on success, `False` on Supabase error. Note: Supabase Auth OTP default expiry is 3600s (1h) — no custom config needed (FR-018).
- [ ] T013 [US1] Implement `login_view(request: HttpRequest) -> TemplateResponse` in `src/apps/auth_app/views.py` (GET `/login`): if user already has valid `supabase_session` cookie → redirect to `REDIRECT_TO_URL` (FR-014). Otherwise render `auth_app/login.html` without navigation shell. Define `REDIRECT_TO_URL` from env `APP_URL` (default `http://localhost:8000`) in `services.py` and import in views.
- [ ] T014 [US1] Implement `login_submit(request: HttpRequest) -> TemplateResponse` in `src/apps/auth_app/views.py` (POST `/login`, `@require_POST`): extracts and normalizes email from `request.POST`, calls `validate_user()` → `send_magic_link()`, on success returns `_login_feedback.html` with success state and `HX-Retarget: #login-form`, on `AccountInactiveError` returns same partial with "Seu acesso não está disponível" error, on `ValueError` (invalid format) returns error, on user not found returns "E-mail não encontrado. Certifique-se de usar o mesmo e-mail utilizado na compra.", on Supabase send failure returns generic error. View is THIN — all logic delegated to services.
- [ ] T015 [US1] Refactor `auth_callback` view: move from `src/apps/payments/views.py` to `src/apps/auth_app/views.py`. Keep existing logic (extract tokens from query params, validate via Supabase, set HTTP-only `supabase_session` + `supabase_refresh` cookies with `max_age=7776000`). Add: verify `profiles.subscription_status` after token validation → if inactive, redirect to `/login?error=account_inactive`. On success redirect to `REDIRECT_TO_URL`. Log `magic_link_logs.status = 'clicked'` and audit log `login_success`. Remove duplicate from `payments/views.py` and update `payments/urls.py` if needed.
- [ ] T016 [US1] Add error query param handling in `login_view` (GET): detect `?error=invalid_magic_link` or `?error=account_inactive` or `?error=unexpected` in request.GET, pre-populate `login-error` div with appropriate message styled via `_login_feedback.html` patterns.

**Checkpoint**: Login screen fully functional — success and rejection flows work end-to-end. MVP achieved.

---

## Phase 4: User Story 3 — Persistência de Sessão (Priority: P2)

**Goal**: Após autenticar, o usuário permanece logado por 90 dias sem reautenticação manual. Refresh tokens renovam a sessão automaticamente.

**Independent Test**: Realizar login, fechar navegador, reabrir após 24h, acessar área restrita → sessão ainda ativa.

### Implementation for User Story 3

- [ ] T017 [US3] Configure Supabase Auth session settings in `src/apps/auth_app/services.py`: JWT expiry 3600s (1h), refresh token rotation enabled, `max_age` for `supabase_session` and `supabase_refresh` cookies set to 7776000 seconds (90 days). Document in a `SESSION_CONFIG` dict at module level.
- [ ] T018 [US3] Implement `refresh_session(request: HttpRequest) -> bool` in `src/apps/auth_app/services.py`: checks if `supabase_refresh` cookie exists and `supabase_session` is expired/near-expiry, calls `supabase.auth.refreshSession(refresh_token)`, updates `supabase_session` cookie with new access token. Returns `True` if refreshed, `False` if refresh token is also expired (user must re-login).
- [ ] T019 [US3] Integrate session refresh into `LoginRequiredMiddleware` flow: before checking session validity, attempt `refresh_session()` if access token is expired but refresh token exists.

**Checkpoint**: Sessions persist across browser restarts for up to 90 days.

---

## Phase 5: User Story 4 — Proteção de Rotas (Priority: P2)

**Goal**: Qualquer rota interna sem sessão ativa redireciona para `/login`. Rotas públicas (whitelist) permanecem acessíveis. Sessão cancelada/inativa é invalidada.

**Independent Test**: Acessar `/routines/` sem sessão → redireciona para `/login?next=/routines/`. Acessar `/login` sem sessão → permitido.

### Implementation for User Story 4

- [ ] T020 [US4] Implement `LoginRequiredMiddleware` in `src/apps/auth_app/middleware.py`: middleware class with `__init__`, `process_view` (Django middleware hook). Checks if request path matches any pattern in `settings.LOGIN_EXEMPT_URLS` (skip if match). Checks for `supabase_session` cookie → if missing, redirect to `LOGIN_URL` with `?next=<original_path>`. If cookie exists, verifies JWT validity (basic decode check, no full DB query every request). Also queries `profiles.subscription_status` by `user_id` from JWT — if `canceled`/`past_due`, clears cookies and redirects to `/login?error=account_inactive`.
- [ ] T021 [US4] Configure `LOGIN_EXEMPT_URLS` in `src/config/settings/base.py`: list of regex patterns for `/login`, `/auth/callback`, `/health`, `/webhooks/stripe`, `/static/`, `/admin/`. Also set `LOGIN_URL = '/login'`.
- [ ] T022 [P] [US4] Add `LoginRequiredMiddleware` to `MIDDLEWARE` list in `src/config/settings/base.py` AFTER `SecurityMiddleware` and BEFORE `SessionMiddleware`.
- [ ] T023 [US4] Implement `logout_view(request: HttpRequest) -> HttpResponse` in `src/apps/auth_app/views.py` (GET `/logout`): clears `supabase_session` and `supabase_refresh` cookies (set max_age=0), redirects to `/login`. Implements FR-020.
- [ ] T024 [P] [US4] Add `next` redirect support in `login_view` (GET): after successful login, the `login_submit` response should include `HX-Redirect` header to `request.GET.get('next', REDIRECT_TO_URL)` so user lands on the page they originally requested.

**Checkpoint**: All internal routes protected. Login page publicly accessible. Session invalidation on cancel works.

---

## Phase 6: User Story 5 — Proteção contra Abuso e Enumeração (Priority: P3)

**Goal**: Rate limiting por e-mail (3/60s), por IP (10/60s), e detecção de enumeração (5+ e-mails distintos rejeitados do mesmo IP → bloqueio). Mensagens genéricas durante bloqueio, sem vazar existência do e-mail.

**Independent Test**: Submeter mesmo e-mail 4x em 60s → bloqueado. Submeter 11 e-mails diferentes do mesmo IP em 60s → bloqueado com mensagem genérica.

### Implementation for User Story 5

- [ ] T025 [US5] Implement `check_rate_limit(email: str, ip_address: str) -> str | None` in `src/apps/auth_app/services.py`: queries `login_attempts` table. Step 1: COUNT by email in last 60s → if ≥ 3, return `'rate_limit_email'`. Step 2: COUNT by ip_address in last 60s → if ≥ 10, return `'rate_limit_ip'`. Step 3: COUNT DISTINCT email by ip_address in last 60s WHERE `result='rejected'` AND `rejection_reason='email_not_found'` → if ≥ 5, return `'enumeration_detected'`. Returns `None` if all checks pass.
- [ ] T026 [US5] Implement `log_attempt(email: str, ip_address: str, result: str, rejection_reason: str | None)` in `src/apps/auth_app/services.py`: inserts record into Supabase `login_attempts` table with all fields. Called for every login attempt regardless of outcome.
- [ ] T027 [US5] Integrate rate limiting into `login_submit` flow in `src/apps/auth_app/views.py`: call `check_rate_limit()` BEFORE `validate_user()`. If blocked, call `log_attempt(email, ip, 'rejected', reason)`, return `_login_feedback.html` with generic amber error "Muitas tentativas. Aguarde alguns instantes antes de tentar novamente." — NEVER reveal whether the email exists. On enumeration detected, also call `AuditLogService.log_audit_event(action='enumeration_blocked', metadata={ip_address, email_count})`.
- [ ] T028 [US5] Add `log_attempt()` call to all outcomes in `login_submit`: success → `('success', None)`, user not found → `('rejected', 'email_not_found')`, account inactive → `('rejected', 'account_inactive')`, send error → `('rejected', 'send_error')`. Extract `ip_address` from `request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '0.0.0.0'))`.

**Checkpoint**: Rate limiting and enumeration detection fully operational. All login attempts logged.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: WCAG 2.1 AA compliance, dark mode verification, Constitution audits, quickstart validation.

- [ ] T029 [P] WCAG 2.1 AA accessibility audit on login page: verify contrast ≥ 4.5:1 (normal text) and ≥ 3:1 (large components) using Lighthouse in DevTools, confirm screen-reader labels (`aria-label` on button, `role="alert"` on error, `role="status"` on success, `<label for="email">`), verify keyboard navigation tab order (email → button → support link), visible `:focus-visible` outline on all interactive elements, font scaling to 200% without layout breakage. Fix any violations found.
- [ ] T030 [P] Dark mode verification on login page: test both light and dark modes, verify all colors adapt correctly (Teal-500 visible on dark surface, error messages legible, input borders visible), ensure transition is smooth (< 300ms, no flash). The page inherits dark mode from `theme.css` + `app-shell.js` (LocalStorage); verify it works on a standalone login page without nav shell.
- [ ] T031 [P] Service Layer audit: verify `src/apps/auth_app/views.py` contains ZERO business logic (no Supabase calls, no rate limit queries, no email validation beyond format check). Verify all external integrations (Supabase, Stripe SDK) are isolated in `services.py`. Verify `services.py` functions have strict type hints.
- [ ] T032 [P] Type hints static analysis: run `mypy src/apps/auth_app/` or `pyright src/apps/auth_app/` to verify all functions have type annotations, no `Any` type leaks, all return types declared. Fix any violations.
- [ ] T033 [P] Anti-SPA verification: confirm `login.html` uses only HTMX + Alpine.js for interactivity, zero React/Vue/Angular/Svelte usage, JavaScript in `auth.js` ≤ 50 lines (if exceeding, document justification). Check `_login_feedback.html` is a partial HTML fragment (no full page reload on login submit).
- [ ] T034 Run `quickstart.md` validation end-to-end: (1) GET `/login` → 200, (2) POST invalid email → error, (3) POST valid paid email → success message + Magic Link arrives, (4) click Magic Link → redirect to area restrita, (5) close/reopen browser → still logged in, (6) access `/routines/` without session → redirect to `/login`, (7) 4x same email in 60s → rate limited, (8) verify dark mode, (9) verify keyboard nav, (10) verify mobile touch targets ≥ 48x48dp.
- [ ] T035 [P] UX Fricção Zero audit on login: measure form submission to response time (must be ≤ 5s), verify button touch area ≥ 48×48dp, confirm no `<select>` elements used, verify single-handed operability on 6.1" smartphone viewport.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories.
- **User Story 1+2 (Phase 3)**: Depends on Foundational (Phase 2). No dependency on other stories.
- **User Story 3 (Phase 4)**: Depends on Phase 3 (needs callback working to test session persistence).
- **User Story 4 (Phase 5)**: Depends on Phase 3 (needs login/callback working to protect routes). Can parallel with Phase 4.
- **User Story 5 (Phase 6)**: Depends on Phase 3 (needs login_submit to integrate rate limiting). Independent of Phase 4 and 5.
- **Polish (Phase 7)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1+US2 (P1)**: Can start after Foundational. No dependencies on other stories.
- **US3 (P2)**: Depends on US1+US2 for session creation in callback. Start after Phase 3.
- **US4 (P2)**: Depends on US1+US2 for login endpoint. Can start in parallel with US3.
- **US5 (P3)**: Depends on US1+US2 for login submit integration. Can start in parallel with US3 and US4.

### Within Each User Story

- Templates before views
- Services before views
- Middleware after views (needs URL patterns defined)
- Integration (rate limiting) after base flow works

### Parallel Opportunities

- T002, T003 in Setup can run in parallel
- T006, T007 in Foundational can run in parallel
- T009, T010 in US1+US2 can run in parallel (different files)
- T011, T012 in US1+US2 can run in parallel (different service functions)
- T022, T024 in US4 can run in parallel
- All Polish tasks (T029-T035) can run in parallel
- US4 and US5 can be developed in parallel after Phase 3

---

## Parallel Example: User Story 1+2

```bash
# Launch templates and static JS in parallel:
Task: "Create login.html template in src/apps/auth_app/templates/auth_app/login.html"
Task: "Create _login_feedback.html partial in src/apps/auth_app/templates/auth_app/partials/_login_feedback.html"
Task: "Create auth.js in src/static/js/auth.js"

# After templates are ready, launch service functions in parallel:
Task: "Implement validate_user in src/apps/auth_app/services.py"
Task: "Implement send_magic_link in src/apps/auth_app/services.py"

# After services, implement views:
Task: "Implement login_view (GET) in src/apps/auth_app/views.py"
Task: "Implement login_submit (POST) in src/apps/auth_app/views.py"
Task: "Refactor auth_callback to src/apps/auth_app/views.py"
```

---

## Implementation Strategy

### MVP First (User Story 1+2 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T007)
3. Complete Phase 3: US1+US2 (T008-T016)
4. **STOP and VALIDATE**: Test login independently — success flow, rejection flow, magic link callback
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1+US2 → Test independently → Deploy/Demo (MVP!)
3. Add US3 → Test independently → Deploy/Demo (session persistence)
4. Add US4 → Test independently → Deploy/Demo (route protection)
5. Add US5 → Test independently → Deploy/Demo (abuse protection)
6. Polish → Final audit → Release

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1+US2 (login form + callback)
   - Once Phase 3 done:
     - Developer A: US3 (session persistence)
     - Developer B: US4 (route protection)
     - Developer C: US5 (abuse protection)
3. All developers: Polish phase (divide audit tasks)

---

## Notes

- SC-003 (Magic Link delivery ≤ 10s in 90% cases) depends on Supabase's external email provider and is validated via Supabase dashboard metrics, not application code. No implementation task required.
- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- US1 and US2 are merged into a single phase because they share the same code path (POST /login handles both success and rejection)
- Each user story should be independently completable and testable after Foundational
- Commit after each task or logical group (e.g., all templates together)
- Stop at any checkpoint to validate story independently
- The `auth_callback` view currently exists in `apps/payments/views.py` — T015 refactors it to `auth_app` and removes the duplicate
- All Supabase queries use service_role key (before user is authenticated) or anon key (after authentication)
- Design tokens from spec 002 (Teal-500 #14b8a6, Inter font, rounded-xl, 48×48dp, dark mode) are non-negotiable
