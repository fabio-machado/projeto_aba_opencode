# Tasks: Gerador de Rotinas (Módulo Rotinas)

**Input**: Design documents from `/specs/006-gerador-rotinas/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/routine_builder.md, contracts/pdf_export.md

**Tests**: Test tasks included for critical service-layer logic and contracts (pytest).

**Agent Legend**: Each task is tagged with the best-fit AI agent:
- `[supabase]` → supabase-persistence-expert (migrations, RLS, supabase-py queries)
- `[django]` → django-backend-expert (views, services, URLs, decorators)
- `[frontend]` → htmx-alpine-frontend (templates, Alpine.js, SortableJS, Tailwind CSS)
- `[empathy]` → aba-domain-empathy (empty state copy, labels, acolhimento)
- `[qa]` → qa-tester-expert (testes pytest, contract tests)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Agent] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Agent]**: Best-fit AI agent for this task
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup — Supabase Schema & Seed Data

**Purpose**: Create tables, RLS policies, and seed pictogram data. Blocks all other work.

- [x] T001 [supabase] Create migration for `pictogram_categories` table (id UUID PK, name TEXT, display_order INT) with RLS: SELECT público, INSERT/UPDATE/DELETE service_role
- [x] T002 [P] [supabase] Create migration for `pictograms` table (id UUID PK, category_id UUID FK → pictogram_categories, name TEXT, image_url TEXT) with RLS: SELECT público, INSERT/UPDATE/DELETE service_role
- [x] T003 [P] [supabase] Create migration for `routines` table (id UUID PK, parent_id UUID NOT NULL, title VARCHAR(100), created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ) with RLS: all CRUD filtered by parent_id = auth.uid()
- [x] T004 [P] [supabase] Create migration for `routine_items` table (id UUID PK, routine_id UUID FK → routines ON DELETE CASCADE, pictogram_id UUID FK → pictograms, order_position INT CHECK ≥ 0) with RLS: ownership via join on routines.parent_id
- [x] T005 [supabase] Add index `idx_routines_parent_id` ON routines(parent_id) and `idx_routine_items_routine` ON routine_items(routine_id, order_position)
- [x] T006 [supabase] Seed 7 pictogram categories (Higiene, Alimentação, Escola, Lazer, Terapia, Sono, Outros) with display_order 1-7
- [x] T007 [empathy] [supabase] Define and insert 70 seed pictograms (10 per category × 7 categories) with empathetic Portuguese names into `pictograms` table with Supabase Storage image URLs

**Checkpoint**: Supabase schema ready — 4 tables with RLS policies + seed data populated.

---

## Phase 2: Foundational — Service Layer Skeleton & Routing

**Purpose**: Core infrastructure that MUST be complete before ANY user story template can be rendered. The `routine_service.py` is the single gateway to Supabase.

**⚠️ CRITICAL**: No user story template/UI work can begin until the service layer skeleton exists.

- [x] T008 [django] Add `reportlab>=4.0` to `requirements.txt` and verify import works in Django shell
- [x] T009 [supabase] Implement `get_supabase_client()` helper (anon key) in `src/apps/routines/services.py` — pattern: `create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)`
- [x] T010 [P] [supabase] Implement `get_admin_client()` helper (service_role key) in `src/apps/routines/services.py` — pattern from `apps/auth/services.py`
- [x] T011 [django] Define type aliases and dataclasses for Routine, RoutineItem, Pictogram, Category in `src/apps/routines/services.py` with strict type hints (e.g., `RoutineDict = TypedDict(...)`)
- [x] T012 [django] Rewrite `src/apps/routines/urls.py` with named routes: `routine_list` (GET /), `routine_builder` (GET /create/, GET /<uuid:id>/), `routine_save` (POST /save/), `routine_rename` (PATCH /<uuid:id>/rename/), `routine_delete` (DELETE /<uuid:id>/delete/), `routine_export_pdf` (GET /<uuid:id>/export/)
- [x] T013 [django] Register routines URLs in `src/config/urls.py` under the `routines/` prefix (already exists — verify, update if needed)
- [x] T014 [django] Skeleton views in `src/apps/routines/views.py` with `@require_GET`/`@require_POST` decorators and `TemplateResponse` placeholders — each view delegates to `routine_service.py` stubs
- [x] T015 [django] Verify `LoginRequiredMiddleware` covers all `/routines/` routes (check `LOGIN_EXEMPT_URLS` in `src/config/settings/base.py` — routines routes should NOT be exempt)

**Checkpoint**: Foundation ready — Supabase client initialized, URL routing wired, views skeleton created, all gated behind auth middleware.

---

## Phase 3: User Story 1 — Criar Minha Primeira Rotina (Priority: P1) 🎯 MVP

**Goal**: Cuidador visualiza empty state acolhedor, toca CTA para abrir construtor, adiciona pictogramas com 1 toque, salva rotina via POST JSON, retorna ao mural vendo o novo card.

**Independent Test**: Acessar `/routines/` → ver empty state → tocar "Criar Minha Primeira Rotina" → preencher título → tocar pictogramas na gaveta → ver timeline atualizar → tocar "Salvar" → ser redirecionado ao mural com card visível.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T016 [P] [qa] [US1] Contract test for POST /routines/save/ (create mode) in `src/apps/routines/tests/test_contract_save.py` — verify 201 on valid payload, 400 on missing title/pictogram_ids, 400 on >15 items, 401 on no session
- [ ] T017 [P] [qa] [US1] Integration test for full create flow in `src/apps/routines/tests/test_integration_us1.py` — call `routine_service.save_routine()` → verify routine + items persisted in Supabase

### Implementation for User Story 1

- [x] T018 [supabase] [US1] Implement `list_categories()` in `src/apps/routines/services.py` — SELECT * FROM pictogram_categories ORDER BY display_order — returns list[dict]
- [x] T019 [P] [supabase] [US1] Implement `list_pictograms_by_category(category_id)` in `src/apps/routines/services.py` — SELECT * FROM pictograms WHERE category_id = {id} — returns list[dict]
- [x] T020 [P] [supabase] [US1] Implement `validate_pictogram_ids(pictogram_ids: list[str]) -> bool` in `src/apps/routines/services.py` — verifies all UUIDs exist in pictograms table, returns False if any missing
- [x] T021 [supabase] [US1] Implement `save_routine(parent_id: str, title: str, pictogram_ids: list[str], routine_id: str | None = None) -> dict` in `src/apps/routines/services.py` — validates title (1-100 chars), validates pictogram_ids (1-15, all valid), batch deletes old items if edit, inserts routine/items, returns {"success": True, "routine_id": str, "title": str, "pictogram_count": int}
- [x] T022 [django] [US1] Implement `routine_save` view in `src/apps/routines/views.py` — POST-only, extracts parent_id from session cookie (JWT decode), parses JSON body {title, pictogram_ids}, delegates to `routine_service.save_routine()`, returns JsonResponse
- [x] T023 [django] [US1] Implement `routine_builder` view in `src/apps/routines/views.py` — GET, renders `routine_builder.html` with context: {categories: list_categories(), pictograms_by_category: dict, routine: None (create mode)}
- [x] T024 [frontend] [US1] Create `src/apps/routines/templates/routines/routine_list.html` — extends base.html, placeholder for mural (Phase 5 will expand), for now just shows a link to `/routines/create/`
- [x] T025 [frontend] [US1] Create `src/apps/routines/templates/routines/routine_builder.html` — extends base.html, contains Alpine.js x-data with {title, items[], isDirty, categories, pictogramsByCategory}
- [x] T026 [frontend] [US1] Implement category tab drawer in `routine_builder.html` — horizontal scrollable tabs (Higiene, Alimentação, ...) using Alpine.js `x-show` / `:class` to switch active category
- [x] T027 [frontend] [US1] Implement pictogram grid in `routine_builder.html` — grid of clickable pictogram cards (imagem + nome) filtered by active category tab; @click adds to items[]
- [x] T028 [frontend] [US1] Implement timeline display in `routine_builder.html` — vertical list rendering `items` array with `<template x-for>`, showing pictogram image + name + remove button (X)
- [x] T029 [frontend] [US1] Implement save button logic in `routine_builder.html` — `:disabled="!title.trim() || items.length === 0"`, @click calls `fetch('/routines/save/', {method: 'POST', body: JSON.stringify({...})})`, on success redirects to `/routines/`
- [ ] T030 [frontend] [US1] Create `src/static/js/routine-builder.js` — Alpine.data('routineBuilder', () => ({...})) with full state management: title, items[], addItem(), removeItem(), save(), isDirty detection
- [ ] T031 [empathy] [US1] Write empathetic empty state copy and CTA text in `src/apps/routines/templates/routines/routine_list.html` — "As rotinas visuais reduzem a ansiedade e trazem previsibilidade ao dia a dia da criança." + button "Criar Minha Primeira Rotina"
- [ ] T032 [empathy] [US1] Review and refine Portuguese labels in `src/apps/routines/templates/routines/routine_builder.html` — title placeholder "Ex: Hora do Banho", category tab names, Save button text (Salvar Rotina), remove button aria-label — for empathetic tone per ABA domain conventions

**Checkpoint**: User Story 1 fully functional — cuidador CAN create a routine via builder with title + pictograms, save, and see it persisted.

---

## Phase 4: User Story 2 — Reordenar e Refinar a Rotina (Priority: P2)

**Goal**: Cuidador abre rotina existente do mural no construtor, carrega pictogramas na ordem salva, arrasta e solta para reordenar, adiciona/remove itens, salva com batch update atômico.

**Independent Test**: Abrir rotina existente do mural → ver pictogramas carregados na timeline → arrastar item para nova posição → salvar → reabrir e confirmar nova ordem.

### Tests for User Story 2

- [ ] T033 [P] [qa] [US2] Contract test for POST /routines/save/ (edit mode) in `src/apps/routines/tests/test_contract_save.py` — verify 200 on valid edit (routine_id + title + pictogram_ids), 404 on non-existent routine_id, 403 on routine owned by different parent_id
- [ ] T034 [P] [qa] [US2] Integration test for batch edit in `src/apps/routines/tests/test_integration_us2.py` — create routine, save_routine with different pictogram_ids order, verify old items deleted and new items with correct order_position

### Implementation for User Story 2

- [x] T035 [supabase] [US2] Implement `get_routine(routine_id: str, parent_id: str) -> dict | None` in `src/apps/routines/services.py` — SELECT routine + LEFT JOIN routine_items + pictograms, ordered by order_position, filtered by parent_id
- [x] T036 [supabase] [US2] Implement `get_routine_items(routine_id: str) -> list[dict]` in `src/apps/routines/services.py` — SELECT routine_items JOIN pictograms WHERE routine_id, ORDER BY order_position
- [x] T037 [django] [US2] Update `routine_builder` view in `src/apps/routines/views.py` to support edit mode — when `routine_id` URL param present, call `routine_service.get_routine()`, pass {routine: {...}, items: [...]} to template context, pre-fill Alpine.js state via `x-data` JSON
- [x] T038 [frontend] [US2] Initialize SortableJS in `routine-builder.js` — `x-init="initSortable()"` on timeline container, `onUpdate` callback updates `items[]` array preserving Alpine reactivity
- [ ] T039 [frontend] [US2] Add `isDirty` tracking in `routine-builder.js` — compare current {title, items[].id order} against initial state loaded from server; set `isDirty = true` on first change
- [ ] T040 [frontend] [US2] Implement unsaved changes confirmation in `routine-builder.js` — `window.addEventListener('beforeunload', ...)` + Alpine `@click` interception on back navigation when `isDirty`
- [ ] T041 [frontend] [US2] Add drag handle visual affordance (6-dots grip icon) to each timeline item in `routine_builder.html` per sortable-js CSS convention
- [ ] T042 [frontend] [US2] Add 15-pictogram limit indicator in `routine_builder.html` — show "N/M" counter near timeline, disable pictogram click in grid when items.length >= 15, add `aria-label` for screen readers

**Checkpoint**: User Story 2 fully functional — edit mode loads existing routine, drag-and-drop reordering works, unsaved changes prompt, 15-item limit enforced.

---

## Phase 5: User Story 3 — Gerenciar Rotinas pelo Mural (Priority: P3)

**Goal**: Cuidador visualiza cards de todas as rotinas no mural, header mostra nome da criança, renomeia e exclui via menu de contexto (ellipsis), empty state reaparece ao excluir última rotina.

**Independent Test**: Ver mural com rotinas → ver cards com título → abrir menu ellipsis → renomear → ver título atualizado → excluir outra rotina → ver card removido → excluir última → ver empty state.

### Tests for User Story 3

- [ ] T043 [P] [qa] [US3] Contract test for PATCH /routines/<uuid>/rename/ in `src/apps/routines/tests/test_contract_rename.py` — verify 200 on valid rename, 400 on empty/overlong title, 403 on wrong parent_id
- [ ] T044 [P] [qa] [US3] Contract test for DELETE /routines/<uuid>/delete/ in `src/apps/routines/tests/test_contract_delete.py` — verify 200 on delete, 404 on non-existent, 403 on wrong parent_id, verify routine_items cascade-deleted

### Implementation for User Story 3

- [x] T045 [supabase] [US3] Implement `list_routines(parent_id: str) -> list[dict]` in `src/apps/routines/services.py` — SELECT * FROM routines WHERE parent_id, ORDER BY updated_at DESC, include count of items per routine (subquery or separate COUNT query)
- [x] T046 [supabase] [US3] Implement `rename_routine(routine_id: str, parent_id: str, new_title: str) -> dict` in `src/apps/routines/services.py` — validate title (1-100 chars, trimmed), UPDATE routines SET title + updated_at, log audit event
- [x] T047 [supabase] [US3] Implement `delete_routine(routine_id: str, parent_id: str) -> bool` in `src/apps/routines/services.py` — DELETE from routines WHERE id AND parent_id (RLS-safe), returns True if deleted, False if not found. ON DELETE CASCADE removes routine_items.
- [x] T048 [django] [US3] Implement `routine_list` view in `src/apps/routines/views.py` — GET, extracts parent_id from session, calls `routine_service.list_routines()`, renders `routine_list.html` with {routines: [...], child_name: str, has_routines: bool}
- [x] T049 [django] [US3] Implement `routine_rename` view in `src/apps/routines/views.py` — PATCH, parses JSON {title}, delegates to `routine_service.rename_routine()`, returns updated card HTML partial via HTMX
- [x] T050 [django] [US3] Implement `routine_delete` view in `src/apps/routines/views.py` — DELETE, delegates to `routine_service.delete_routine()`, returns 200 with empty body (HTMX removes card element from DOM via hx-swap="delete")
- [x] T051 [frontend] [US3] Build `routine_list.html` — extends base.html, shows header "Rotinas do(a) [Nome da Criança]", grid of routine cards, FAB button fixed bottom-right linking to /routines/create/
- [x] T052 [frontend] [US3] Create `src/apps/routines/templates/routines/partials/_routine_card.html` — HTMX partial for individual card: shows title, pictogram count, PDF export button, ellipsis menu with Rename/Delete options; uses hx-target/hx-swap for actions
- [ ] T053 [empathy] [US3] Create `src/apps/routines/templates/routines/partials/_empty_state.html` — HTMX partial: illustration SVG, empathetic copy (from US1), CTA button linking to /routines/create/. Shown when list_routines returns empty.
- [ ] T054 [frontend] [US3] Implement inline rename in `_routine_card.html` — ellipsis → "Renomear" → Alpine.js toggle to show inline input → Enter/blur triggers PATCH to /routines/<uuid>/rename/ → HTMX updates card title
- [ ] T055 [frontend] [US3] Implement delete confirmation in `_routine_card.html` — ellipsis → "Excluir" → `confirm('Tem certeza?')` → DELETE to /routines/<uuid>/delete/ → HTMX removes card, if last card swap in empty state via hx-swap-oob
- [ ] T056 [frontend] [US3] Implement FAB button in `routine_list.html` — fixed z-50 bottom-6 right-6, 56x56dp touch target, "+" icon, links to /routines/create/
- [ ] T057 [django] [US3] Resolve child name for header — call `auth.services.get_profile_by_id(parent_id)` or decode JWT to get user metadata; fallback to "Minhas Rotinas" if name unavailable (edge case)

**Checkpoint**: User Story 3 fully functional — mural shows cards, rename/delete work via HTMX, empty state reappears when last routine deleted.

---

## Phase 6: User Story 4 — Exportar Rotina em PDF (Priority: P4)

**Goal**: Cuidador toca botão PDF no card do mural, arquivo PDF é gerado server-side com reportlab e download inicia.

**Independent Test**: Tocar botão PDF em um card → ver download iniciar → abrir PDF → ver título + pictogramas na ordem correta, layout A4, 1 pictograma por linha.

### Tests for User Story 4

- [ ] T058 [P] [qa] [US4] Contract test for GET /routines/<uuid>/export/ in `src/apps/routines/tests/test_contract_export.py` — verify 200 Content-Type application/pdf, Content-Disposition attachment, 404 on missing routine, 403 on wrong parent_id
- [ ] T059 [P] [qa] [US4] Unit test for PDF content in `src/apps/routines/tests/test_export_pdf.py` — mock Supabase, call `generate_routine_pdf()`, verify PDF bytes contain routine title and pictogram names in correct order

### Implementation for User Story 4

- [x] T060 [supabase] [US4] Implement `get_routine_for_export(routine_id: str, parent_id: str) -> tuple[dict, list[dict]] | None` in `src/apps/routines/services.py` — fetch routine + items (with pictogram name + image_url) for PDF generation, returns (routine, items) or None
- [x] T061 [supabase] [US4] Implement `generate_routine_pdf(routine: dict, items: list[dict]) -> bytes` in `src/apps/routines/services.py` — uses `reportlab` Canvas A4 (210mm×297mm), draws title centered at top (Helvetica-Bold 18pt), draws each pictogram as image (50×50px) with name label (Helvetica 14pt), 1 per row, auto page break after 8 items, footer "Autismo em Foco — Gerado em DD/MM/AAAA"
- [x] T062 [django] [US4] Implement `routine_export_pdf` view in `src/apps/routines/views.py` — GET, extracts parent_id + routine_id from URL, calls `routine_service.get_routine_for_export()`, calls `routine_service.generate_routine_pdf()`, returns `FileResponse(pdf_bytes, content_type='application/pdf', filename='Rotina - {title}.pdf')` with Content-Disposition: attachment
- [ ] T063 [frontend] [US4] Add PDF export button to `_routine_card.html` — styled as secondary action button with PDF/download icon, hx-get to /routines/<uuid>/export/ with hx-target/_blank handling, or plain `<a>` tag with `download` attribute
- [ ] T064 [frontend] [US4] Handle PDF generation error in `_routine_card.html` — on 500 response from export endpoint, show toast/alert: "Erro ao gerar PDF. Tente novamente." (edge case from spec)

**Checkpoint**: User Story 4 fully functional — PDF generated and downloaded correctly for any routine.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Constitution compliance, offline resilience, accessibility audit, cleanup.

- [ ] T065 [frontend] [P] Implement LocalStorage offline persistence in `routine-builder.js` — `$watch('items', val => localStorage.setItem('draft_items', JSON.stringify(val)))`; restore from localStorage on init if available; clear on successful save
- [ ] T066 [frontend] [P] Add sync state indicator to save button in `routine_builder.html` — show "Salvando..." spinner during fetch, show checkmark on success, show "⚠ Pendente" when offline (navigator.onLine === false)
- [ ] T067 [django] [P] Add AuditLogService integration in `src/apps/routines/services.py` — log routine.created, routine.updated, routine.deleted, routine.exported events with user_id/action/timestamp via existing `AuditLogService` from `apps/core/services.py`
- [ ] T068 [django] [P] Add `AuditLogService` import helper or adapter in `src/apps/routines/services.py` — follow pattern from `apps/payments/services.py` which also uses AuditLogService
- [ ] T069 [frontend] [P] WCAG 2.1 AA — Contrast & Color audit: verify all text elements have contrast ratio ≥ 4.5:1 against background; verify no information conveyed solely by color; check focus indicator visibility ≥ 3:1
- [ ] T070 [frontend] [P] WCAG 2.1 AA — Keyboard Navigation audit: verify all interactive elements (pictogram grid, timeline items, save button, rename input, ellipsis menu, FAB) are reachable via Tab; verify correct Tab order; verify Enter/Space activate buttons; verify Escape closes modals/menus; verify no keyboard traps
- [ ] T071 [frontend] [P] WCAG 2.1 AA — Screen Reader audit: add aria-labels to pictogram buttons (e.g., "Adicionar Escovar os dentes à rotina"), timeline items (e.g., "Item 1: Escovar os dentes — remover"), rename input, delete confirm dialog; verify landmark roles (banner, main, navigation); verify dynamic content updates announced via aria-live regions
- [ ] T072 [frontend] [P] WCAG 2.1 AA — Focus & Semantic audit: verify focus trap in inline rename input; verify heading hierarchy (h1 title, h2 card titles); verify form labels associated with inputs; verify 48×48dp touch target minimum on all interactive elements; verify zoom support up to 200% without content loss
- [ ] T073 [qa] [P] Run full test suite — `pytest src/apps/routines/tests/ -v --cov=src/apps/routines` — verify ≥ 80% coverage on services.py
- [ ] T074 [frontend] [P] Remove old placeholder templates in `src/templates/routines/` (routines.html, routines_create.html) — replaced by app-level templates
- [ ] T075 [django] [P] Run mypy type check — `mypy src/apps/routines/` — verify zero type errors with strict mode
- [ ] T076 [qa] [P] Run quickstart validation — follow `specs/006-gerador-rotinas/quickstart.md` end-to-end, verify all steps work on clean environment
- [ ] T077 [frontend] Verify no `<select>` elements in any routine template (Constitution I); verify JS per file ≤ 50 lines or documented exception
- [ ] T078 [django] [P] Type hints static analysis check across `src/apps/routines/services.py` and `src/apps/routines/views.py` — all function signatures, TypedDict usage, Optional/Union types per Constitution III
- [ ] T079 [supabase] [P] RLS-First audit — verify all service functions filter by parent_id; verify all UUIDs serialized as str(uuid) before Supabase SDK calls; verify delete_routine uses parent_id in WHERE clause
- [ ] T080 [qa] [P] Performance validation SC-003: add timing assertion in builder JS test or browser test — verify `addItem()` (pictogram click → DOM update) completes within 200ms measured via `performance.now()`
- [ ] T081 [qa] [P] Performance validation SC-005: add timing assertion in `src/apps/routines/tests/test_export_pdf.py` — wrap `generate_routine_pdf()` call with `time.perf_counter()`, assert PDF generation for 15 pictograms ≤ 3 seconds
- [ ] T082 [qa] [P] Performance validation SC-007: add integration test in `src/apps/routines/tests/test_offline_sync.py` — simulate offline state (mock `navigator.onLine`), save draft to LocalStorage, restore online, sync, verify no data loss; repeat 20 times and assert ≥ 95% success rate

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 (tables must exist before service layer can query them)
- **Phase 3 (US1 - Create)**: Depends on Phase 2 (service skeleton, URLs, views)
- **Phase 4 (US2 - Reorder)**: Depends on Phase 3 (builder template + Alpine.js exist, service save_routine exists)
- **Phase 5 (US3 - Manage)**: Depends on Phase 3 (routines exist to list/manage); can run parallel with Phase 4
- **Phase 6 (US4 - Export)**: Depends on Phase 3 (routines exist to export); can run parallel with Phase 4+5
- **Phase 7 (Polish)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Phase 1 ──► Phase 2 ──► Phase 3 (US1 ─► MVP ready)
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              Phase 4     Phase 5    Phase 6
               (US2)       (US3)      (US4)
                    │         │         │
                    └─────────┼─────────┘
                              ▼
                          Phase 7
                         (Polish)
```

- **US1 (P1)**: Can start after Phase 2 — No dependencies on other stories
- **US2 (P2)**: Depends on US1 (builder template + save_routine exist) 
- **US3 (P3)**: Depends on US1 (routines must exist to list/manage); independently testable from US2
- **US4 (P4)**: Depends on US1 (routines must exist to export); independently testable from US2/US3

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Services (supabase) before views (django)
- Views before templates (frontend)
- Templates before JavaScript (frontend)
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities (Agent-Based)

| Parallel Group | Tasks | Reason |
|---------------|-------|--------|
| Phase 1: T002, T003, T004 | 3 migration files | Different tables, no conflicts |
| Phase 2: T010, T011 | get_admin_client() + type definitions | Different concerns in same file but independent sections |
| US1: T018, T019, T020 | list_categories + list_pictograms + validate | Different Supabase queries, no interdependencies |
| US1: T025, T026, T027, T028 | Builder template sections | Same file but independent Alpine.js sections |
| US1: T031, T032 | Empathetic copy | Independent text content from code |
| US2: T033, T034 | Contract + integration tests | Separate test files |
| US3: T043, T044 | Rename + delete contract tests | Separate test files |
| US3: T052, T053 | _routine_card.html + _empty_state.html | Independent partials |
| US4: T058, T059 | Export contract + unit tests | Separate test files |
| Phase 7: T065, T066, T067 | LocalStorage + sync indicator + audit log | Different files (JS → service layer, service layer → audit) |
| Phase 7: T069, T070, T071, T072 | WCAG 2.1 AA sub-audits | Different audit concerns, different files |
| Phase 7: T075, T078, T079 | mypy + type hints + RLS audit | Different tools, different concerns |
| Phase 7: T080, T081, T082 | Performance validations SC-003/005/007 | Separate test files, independent measurements |

---

## Agent-Task Assignment Summary

| Agent | Primary Tasks | Phase(s) |
|-------|---------------|----------|
| **supabase-persistence-expert** | T001-T007, T009-T010, T018-T021, T035-T036, T045-T047, T060-T061, T079 | Setup, Foundational, US1, US2, US3, US4, Polish |
| **django-backend-expert** | T008, T011-T015, T022-T023, T037, T048-T050, T057, T062, T067-T068, T075, T078 | Foundational, US1, US2, US3, US4, Polish |
| **htmx-alpine-frontend** | T024-T030, T038-T042, T051-T052, T054-T056, T063-T066, T069-T072, T074, T077 | US1, US2, US3, US4, Polish |
| **qa-tester-expert** | T016-T017, T033-T034, T043-T044, T058-T059, T073, T076, T080-T082 | US1, US2, US3, US4, Polish |
| **aba-domain-empathy** | T007, T031-T032, T053 | Setup (seed), US1, US3 |

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (Supabase schema + seed data) — 7 tasks
2. Complete Phase 2: Foundational (service skeleton, routing, auth gate) — 8 tasks
3. Complete Phase 3: User Story 1 (create routine end-to-end) — 17 tasks
4. **STOP and VALIDATE**: Test US1 independently — can create routine with title + pictograms
5. Deploy/demo if ready — this is the core value proposition

### Incremental Delivery

1. Phase 1 + 2 → Foundation ready (migrations applied, endpoints wired)
2. + Phase 3 (US1) → MVP: criar rotina funciona → Demo
3. + Phase 4 (US2) → Editor completo com drag-and-drop → Demo
4. + Phase 5 (US3) → Mural com gestão de rotinas → Demo
5. + Phase 6 (US4) → Exportação PDF → Demo
6. + Phase 7 → Production-ready com offline, WCAG 2.1 AA, auditoria

### Parallel Agent Strategy

With multiple AI agents available:

1. **Setup**: `supabase-persistence-expert` handles all Phase 1 tasks sequentially
2. **Foundational**: `django-backend-expert` handles T008, T011-T015; `supabase-persistence-expert` handles T009-T010
3. **US1 (MVP)**: 
   - `supabase-persistence-expert`: T018-T021 (service CRUD)
   - `django-backend-expert`: T022-T023 (views + endpoints)
   - `htmx-alpine-frontend`: T024-T030 (templates + Alpine.js)
   - `aba-domain-empathy`: T031-T032 (copy + labels)
   - `qa-tester-expert`: T016-T017 (tests — write FIRST)
4. **US2+US3+US4**: Can run partially in parallel after US1
   - `htmx-alpine-frontend`: US2 drag-drop + template updates
   - `django-backend-expert`: US3 views (rename, delete, list) + US4 export view
   - `supabase-persistence-expert`: US2 batch edit + US3 CRUD + US4 PDF generation

---

## Notes

- [P] tasks = different files or independent sections, no dependencies
- [Story] label maps task to specific user story for traceability (US1-US4)
- Each user story should be independently completable and testable
- Tests MUST be written and FAIL before implementation (TDD for service layer)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The `src/apps/routines/` directory already exists with placeholder code — all files will be overwritten/replaced
- SortableJS loaded via CDN in `routine_builder.html` (not bundled — per research.md decision)
- reportlab installed via `requirements.txt` (per research.md decision)
