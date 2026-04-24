# Tasks: Django Core Scaffold

**Input**: Design documents from `/specs/001-django-core-scaffold/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are NOT requested for this scaffold feature. Focus is on infrastructure setup and Constitution compliance.

**Organization**: Tasks are grouped by user story to enable traceability, though scaffold tasks have natural sequential dependencies.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below assume single project structure per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and root-level configuration files

- [X] T001 Create `.gitignore` for Python/Django project at repository root
- [X] T002 [P] Create `requirements.txt` with Django 5.x, django-htmx, supabase-py, stripe, structlog, python-dotenv, pytest, django-stubs, mypy at repository root
- [X] T003 [P] Create `.env.example` documenting all required environment variables (SUPABASE_URL, SUPABASE_KEY, STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, SECRET_KEY, DEBUG, LOG_LEVEL) at repository root
- [X] T004 [P] Create initial `Dockerfile` using `python:3.12-slim` with Python base image, non-root user, and working directory set at repository root
- [X] T005 Create `docker-compose.yml` with web service, volume mounts for hot-reload, and environment variable passthrough at repository root
- [X] T006 [P] Create `tests/` directory structure (`contract/`, `integration/`, `unit/`) at repository root
- [X] T007 [P] Create `mypy.ini` with strict mode configuration for Python 3.12 and django-stubs at repository root

**Checkpoint**: Root infrastructure files ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core Django configuration that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 Create `src/manage.py` with `DJANGO_SETTINGS_MODULE=config.settings.dev` default
- [X] T009 [P] Create `src/config/__init__.py`
- [X] T010 [P] Create `src/config/settings/__init__.py`
- [X] T011 Create `src/config/settings/base.py` with shared settings: INSTALLED_APPS (including `django_htmx`), MIDDLEWARE (including `django_htmx.middleware.HtmxMiddleware`), TEMPLATES config, STATIC_URL, ROOT_URLCONF
- [X] T012 [P] Create `src/config/settings/dev.py` inheriting from base.py with DEBUG=True, LOG_LEVEL=DEBUG, and dev-specific middleware
- [X] T013 [P] Create `src/config/settings/prd.py` inheriting from base.py with DEBUG=False, LOG_LEVEL=INFO, and security headers (SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS)
- [X] T014 Create `src/config/urls.py` with root URL configuration and inclusion pattern for app URLs
- [X] T015 [P] Create `src/config/wsgi.py`
- [X] T016 [P] Create `src/config/asgi.py`
- [X] T017 Create logging configuration module `src/config/logging_config.py` with structlog setup: JSON formatter for PRD, colored console for DEV, support for DEBUG/INFO/WARNING/ERROR levels
- [X] T018 Integrate logging configuration into `src/config/settings/base.py` via `LOGGING` dict config

**Checkpoint**: Foundation ready - Django can boot with `python src/manage.py check`; user story implementation can now begin

---

## Phase 3: User Story 1 - Ambiente Django Estruturado (Priority: P1) 🎯 MVP

**Goal**: Create the `src/` directory structure and app `core` demonstrating Service Layer Pattern, with all required files per Constitution

**Independent Test**: `python src/manage.py check` passes without errors; `src/apps/core/` exists with `services.py`, `views.py`, `urls.py`, and partials directory

### Implementation for User Story 1

- [X] T019 [P] Create `src/apps/` directory
- [X] T020 [P] Create `src/templates/` directory
- [X] T021 [P] Create `src/static/css/`, `src/static/js/`, `src/static/images/` directories
- [X] T022 Create app `core` at `src/apps/core/` with `__init__.py`
- [X] T023 [US1] Create `src/apps/core/services.py` with `BaseService` class, type hints, and docstring pattern per contract
- [X] T024 [US1] Create `src/apps/core/views.py` with example view following View Response Pattern contract (validates input, calls service, returns TemplateResponse)
- [X] T025 [US1] Create `src/apps/core/urls.py` with URL pattern for the example view
- [X] T026 [US1] Create `src/apps/core/templates/core/partials/` directory
- [X] T027 [US1] Create `src/apps/core/templates/core/partials/_example_partial.html` as HTMX partial reference
- [X] T028 [US1] Register `core` app in `src/config/settings/base.py` INSTALLED_APPS
- [X] T029 [US1] Include `core.urls` in `src/config/urls.py`
- [X] T065 [US1] Create `src/apps/core/forms.py` with a Django Form example demonstrating backend validation (required fields, min/max length) per dual-validation requirement

**Checkpoint**: At this point, User Story 1 should be fully functional. `manage.py check` passes and core app structure exists as template for future apps.

---

## Phase 4: User Story 2 - Containerização com Paridade DEV/PRD (Priority: P1)

**Goal**: Validate Docker setup provides parity between DEV and PRD with hot-reload support

**Independent Test**: `docker-compose up --build` succeeds and serves app at `http://localhost:8000`; file changes reflect without rebuild

### Implementation for User Story 2

- [X] T030 [US2] Add Docker volume mount for `src/` in `docker-compose.yml` to enable hot-reload
- [X] T031 [US2] Add `DJANGO_SETTINGS_MODULE=config.settings.dev` to Docker Compose environment
- [X] T032 [US2] Add Django-specific CMD (`python src/manage.py runserver 0.0.0.0:8000` for dev) and healthcheck to existing `Dockerfile`
- [X] T033 [US2] Add healthcheck endpoint in `src/config/urls.py` or `src/apps/core/views.py` for Docker health verification
- [ ] T034 [US2] Test `docker-compose up --build` and verify app responds with HTTP 200 on `GET http://localhost:8000/` within 10 seconds of container start
- [ ] T035 [US2] Verify hot-reload: modify `src/apps/core/views.py`, save, and confirm content change is visible in browser within 5 seconds without `docker-compose restart`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Containerized environment matches Constitution requirements.

---

## Phase 5: User Story 3 - Integração Supabase com RLS-First (Priority: P2)

**Goal**: Configure `supabase-py` and `stripe` clients in Service Layer with RLS-First, UUID serialization, and audit logging

**Independent Test**: A test script connects to Supabase, filters by `parent_id`, and validates UUID string serialization. Stripe client initializes without errors.

### Implementation for User Story 3

- [X] T036 [US3] Create `src/apps/core/services.py` `SupabaseService` class with Singleton pattern, `create_client` using settings, and type hints
- [X] T037 [US3] [P] Create `src/apps/core/services.py` `StripeService` class with API key from settings and type hints
- [X] T038 [US3] Create `src/apps/core/services.py` `AuditLogService` class with `log(user_id, action, table_name, record_id, payload)` method
- [X] T039 [US3] Create `src/apps/core/utils.py` with `serialize_uuid(uuid_obj: UUID) -> str` helper function
- [X] T040 [US3] Add RLS filter helper in `SupabaseService`: `eq("parent_id", str(user_id))` applied to all patient-data queries
- [X] T041 [US3] Add UUID serialization enforcement: all UUID parameters converted via `serialize_uuid()` before SDK operations
- [X] T042 [US3] Integrate `AuditLogService.log()` into `SupabaseService` write methods (create, update, delete)
- [X] T043 [US3] Add graceful offline handling: `SupabaseService` retries with timeout when Supabase is unavailable
- [X] T044 [US3] Add `.env` validation in `src/config/settings/base.py`: fail startup with clear message if `SUPABASE_URL` or `SUPABASE_KEY` is missing in PRD

**Checkpoint**: At this point, User Story 3 is functional. Supabase and Stripe clients are isolated in services, RLS and audit logging are enforced.

---

## Phase 6: User Story 4 - Templates Base Anti-SPA e Offline-First (Priority: P2)

**Goal**: Create `base.html` and supporting templates for HTMX partials, Alpine.js local state, Tailwind CSS, and offline-first indicators

**Independent Test**: Render `base.html` shows mobile-first layout; disconnect internet and verify LocalStorage persistence and "pendente" indicator

### Implementation for User Story 4

- [X] T045 [US4] Create `src/templates/base.html` with HTML5 boilerplate, viewport meta tag, and mobile-first structure
- [X] T046 [US4] [P] Add HTMX CDN (`https://unpkg.com/htmx.org@2.0.0`) to `base.html`
- [X] T047 [US4] [P] Add Alpine.js CDN (`https://cdn.jsdelivr.net/npm/alpinejs@3.14.0/dist/cdn.min.js`) with `defer` to `base.html`
- [X] T048 [US4] [P] Add Tailwind CSS CDN (`https://cdn.tailwindcss.com`) to `base.html`
- [X] T049 [US4] Create `src/static/js/offline.js` with Alpine.js `x-data` store for LocalStorage persistence, sync status tracking (`online/offline/pending`), and conflict resolution (last-write-wins with timestamp logging)
- [X] T050 [US4] Add sync status indicator badge to `base.html` header (visible on all pages) using Alpine.js
- [X] T051 [US4] Create `src/templates/partials/` directory for global partials
- [X] T052 [US4] Update `src/apps/core/templates/core/partials/_example_partial.html` to demonstrate HTMX swap with button touch target ≥ 48×48 dp and contrast ≥ 4.5:1
- [X] T053 [US4] Add `hx-boost="true"` to `base.html` body for progressive enhancement via HTMX
- [X] T054 [US4] Ensure `base.html` loads `offline.js` and initializes offline detection on page load
- [X] T066 [US4] Add Alpine.js frontend validation to `_example_partial.html` (real-time field validation: required, min-length) to demonstrate dual-validation pattern per Constitution

**Checkpoint**: All user stories should now be independently functional. Templates render with all Constitution-required libraries and offline-first behavior.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Constitution compliance verification and final validation

- [X] T055 [P] Run `python src/manage.py check` and fix any issues
- [X] T057 [P] UX Fricção Zero audit: verify all primary buttons have `min-w-[48px] min-h-[48px]`, contrast ≥ 4.5:1, no `<select>` for frequent inputs in `src/apps/core/templates/`
- [X] T058 [P] RLS-First audit: verify all `SupabaseService` queries include `eq("parent_id", ...)` filter and UUIDs use `serialize_uuid()`
- [X] T059 [P] Offline-First audit: verify `offline.js` persists to LocalStorage, implements last-write-wins, and displays sync indicator visually distinct (color + icon + text) within 2 seconds of disconnect
- [X] T060 [P] Anti-SPA verification: confirm no React/Vue/Angular/Svelte in `requirements.txt` or templates
- [X] T061 [P] Service Layer audit: confirm zero business logic in `src/apps/core/views.py`; all external calls isolated in `src/apps/core/services.py`
- [X] T062 [P] Type hints static analysis check: run `mypy --strict src/` and ensure zero errors
- [X] T063 [P] Update `AGENTS.md` quickstart validation if any paths changed during implementation
- [X] T064 [P] Run `docker-compose up --build` final validation: app boots in < 5 minutes from clean clone
- [X] T067 [P] JS limit audit: verify no inline or custom JavaScript in any `_partial.html` exceeds 50 lines without documented justification in code comment
- [X] T068 [P] Performance audit: measure `base.html` Time-to-Interactive (first interactive input visible) via browser DevTools on simulated 3G; must be < 3 seconds

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T001-T007) - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can proceed sequentially in priority order (P1 → P2)
  - US1 and US2 have some overlap (Docker needs Django structure)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Creates app structure
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Needs US1 Django structure for full validation
- **User Story 3 (P2)**: Can start after US1 - Needs `services.py` pattern established
- **User Story 4 (P2)**: Can start after US1 - Needs templates directory and core app

### Within Each User Story

- Models/utilities before services
- Services before views
- Views before URL routing
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002-T007)
- All Foundational tasks marked [P] can run in parallel (T009-T016)
- Different services in US3 can be worked on in parallel (T036-T037)
- CDN scripts in US4 can be added in parallel (T046-T048)
- All audit tasks in Polish phase marked [P] can run in parallel (T055, T057-T068)

---

## Parallel Example: User Story 3

```bash
# Launch Supabase and Stripe service creation in parallel:
Task: "Create src/apps/core/services.py SupabaseService class with Singleton pattern"
Task: "Create src/apps/core/services.py StripeService class with API key from settings"

# Launch audit helper creation in parallel:
Task: "Create src/apps/core/utils.py with serialize_uuid() helper"
Task: "Add RLS filter helper in SupabaseService"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Django structure)
4. Complete Phase 4: User Story 2 (Docker containerization)
5. **STOP and VALIDATE**: `docker-compose up --build` works; `manage.py check` passes
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Validate structure
3. Add User Story 2 → Test independently → Validate Docker parity
4. Add User Story 3 → Test independently → Validate Supabase/Stripe integration
5. Add User Story 4 → Test independently → Validate HTMX/Alpine.js/Tailwind + Offline-First
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Django structure)
   - Developer B: User Story 2 (Docker setup) - in parallel with US1
3. Once US1 is done:
   - Developer A: User Story 3 (Supabase/Stripe integration)
   - Developer B: User Story 4 (Templates HTMX/Alpine.js) - in parallel with US3
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
