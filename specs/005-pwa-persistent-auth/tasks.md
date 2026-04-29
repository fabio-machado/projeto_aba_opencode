# Tasks: PWA com Sessão Persistente

**Input**: Design documents from `/specs/005-pwa-persistent-auth/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included — user explicitly requested testable points with unit tests.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install django-pwa and prepare project dependencies

- [x] T001 Add `django-pwa>=2.0.0` to `requirements.txt` and run `pip install -r requirements.txt`
- [x] T002 [P] Create directory `src/static/images/pwa/` for PWA icons

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Configure Django settings, URLs, and base template so PWA infrastructure is active. MUST complete before any user story work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Add `'pwa'` to `INSTALLED_APPS` in `src/config/settings/base.py`
- [x] T004 Add `PWA_APP_CONFIG` dictionary to `src/config/settings/base.py` with `name`, `short_name`, `display: 'standalone'`, `orientation: 'portrait'`, `theme_color: '#14b8a6'`, `background_color: '#f8fafc'`, and `icons` pointing to `/static/images/pwa/icon-192x192.png` and `/static/images/pwa/icon-512x512.png`
- [x] T005 Add `path("", include("pwa.urls"))` to `src/config/urls.py`
- [x] T006 Add `{% load pwa %}` and `{% progressive_web_app_meta %}` to `<head>` in `src/templates/base.html`
- [x] T007 [P] Add `<script src="/static/js/pwa-session-manager.js"></script>` before closing `</body>` in `src/templates/base.html`
- [x] T008 [P] Add `<script src="/static/js/pwa-install-banner.js"></script>` before closing `</body>` in `src/templates/base.html`

**Checkpoint**: Foundation ready — `python src/manage.py check` passes; `/manifest.json` and `/serviceworker.js` are served by django-pwa

---

## Phase 3: User Story 1 — Instalar App na Tela Inicial (Priority: P1) 🎯 MVP

**Goal**: O usuário pode instalar o app na tela inicial a partir do navegador móvel e abri-lo em modo standalone.

**Independent Test**: Verificar que o app é instalável via Chrome menu (⋮ → Instalar app) e que, após instalação, abre em modo standalone sem barra de endereço.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T009 [P] [US1] Create `src/apps/auth/tests/test_pwa_manifest.py` with test that GET `/manifest.json` returns 200 and JSON contains `display: 'standalone'`, `orientation: 'portrait'`, `theme_color`, and `icons` array
- [x] T010 [P] [US1] Create `src/apps/auth/tests/test_pwa_template.py` with test that rendered `base.html` contains `<link rel="manifest"` and `theme-color` meta tag
- [x] T011 [P] [US1] Create `src/apps/auth/tests/test_pwa_serviceworker.py` with test that GET `/serviceworker.js` returns 200 and Content-Type is `application/javascript`

### Implementation for User Story 1

- [x] T012 [P] [US1] Create `src/static/images/pwa/icon-192x192.png` (192×192px PNG, ícone do app)
- [x] T013 [P] [US1] Create `src/static/images/pwa/icon-512x512.png` (512×512px PNG, ícone do app para splash screen)
- [x] T014 [US1] Create `src/static/js/pwa-install-banner.js` — script vanilla JS (≤ 50 linhas) que escuta `beforeinstallprompt`, guarda o evento em `window.deferredPrompt`, e dispara `event.prompt()` quando o usuário clica no botão de instalação
- [x] T015 [US1] Add banner HTML component to `src/templates/base.html` (ou partial `src/templates/partials/pwa/_install_banner.html`) com texto "Instalar App para registro rápido", visível apenas quando `beforeinstallprompt` foi disparado e app ainda não instalado; usar Alpine.js (`x-show`) para toggle de visibilidade
- [x] T016 [US1] Add dismiss handler no banner que guarda `aef_pwa_banner_dismissed = true` no LocalStorage e oculta o banner por 30 dias
- [x] T017 [US1] Add listener para `appinstalled` que define `aef_pwa_installed = true` no LocalStorage e oculta permanentemente o banner

**Checkpoint**: User Story 1 funcionando — banner aparece em navegadores compatíveis, instalação funciona, app abre em standalone

---

## Phase 4: User Story 2 — Acesso Sem Repetir Login (Priority: P1)

**Goal**: O usuário abre o app pela tela inicial e é reconhecido automaticamente, com sessão renovada silenciosamente; logout explícito disponível no menu.

**Independent Test**: Fechar app, reabrir após 24h, verificar que o usuário permanece autenticado sem tela de login; sessão expirada mostra modo leitura com banner de login; logout funciona.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T018 [P] [US2] Create `src/apps/auth/tests/test_pwa_session_refresh.py` with test que simula cookie `supabase_refresh` válido e verifica que `refresh_session()` em `services.py` retorna nova sessão com `access_token`
- [x] T019 [P] [US2] Create `src/apps/auth/tests/test_pwa_logout_button.py` with test que verifica que GET `/logout/` remove cookies `supabase_session` e `supabase_refresh` e redireciona para `/login/`

### Implementation for User Story 2

- [x] T020 [US2] Create `src/static/js/pwa-session-manager.js` — script que inicializa Supabase client no frontend com `persistSession: true`, verifica se a sessão está próxima de expirar (comparando `expires_at` com timestamp atual + margem de 5 minutos), e chama `supabase.auth.refreshSession()` silenciosamente ao abrir o app
- [x] T021 [US2] Add tratamento de erro no `pwa-session-manager.js`: se `refreshSession()` falhar por token expirado (> 90 dias), exibe banner fixo "Sessão expirada — faça login para editar" e bloqueia ações de escrita (atributo `data-session-expired` no body; CSS desabilita botões de submit)
- [x] T022 [US2] Add tratamento offline no `pwa-session-manager.js`: se não houver conexão de rede, não tenta refresh; permite acesso normal aos dados já carregados
- [x] T023 [US2] Add botão de logout ao menu da header em `src/templates/partials/nav/_header.html`, posicionado junto às opções de assinatura, configurações e dark mode; link para `/logout/` com área de toque ≥ 48×48 dp
- [x] T024 [US2] Ensure `apps/auth/views.py` logout view calls `clear_session_cookies()` from `services.py` and redirects to `/login/`

**Checkpoint**: User Story 2 funcionando — sessão persiste, renova silenciosamente, logout funciona, modo leitura ativo quando expirada

---

## Phase 5: User Story 3 — Cache de Assets para Carregamento Instantâneo (Priority: P2)

**Goal**: O app carrega instantaneamente em aberturas subsequentes, mesmo offline, porque assets estáticos são cacheados pelo Service Worker.

**Independent Test**: Ativar modo offline no navegador, abrir app, verificar que CSS, JS e ícones carregam corretamente; após atualização de assets, novo cache é baixado automaticamente.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T025 [P] [US3] Create `src/apps/auth/tests/test_pwa_cache_offline.py` with test que verifica que `/serviceworker.js` contém referências a arquivos estáticos (`theme.css`, `app-shell.js`, ícones) na lista de pré-cache

### Implementation for User Story 3

- [x] T026 [US3] Customize django-pwa service worker template (ou criar `src/static/js/serviceworker.js` customizado) para pré-cachear assets críticos: `/static/css/theme.css`, `/static/js/app-shell.js`, `/static/js/bottom-sheet.js`, `/static/js/pwa-session-manager.js`, `/static/js/pwa-install-banner.js`, `/static/images/pwa/icon-192x192.png`, `/static/images/pwa/icon-512x512.png`
- [x] T027 [US3] Implement estratégia Cache-First no service worker: intercepta requests de assets estáticos (CSS, JS, PNG) e responde do cache; para requests HTMX/API, passa-through para rede (não cacheia dados dinâmicos)
- [x] T028 [US3] Implement versionamento do cache no service worker: nome do cache `aef-static-v1`; no evento `activate`, deleta caches antigos (nomes diferentes) para invalidação
- [x] T029 [US3] Add `clients.claim()` no evento `activate` do service worker para que o novo worker tome controle imediato das páginas

**Checkpoint**: User Story 3 funcionando — app carrega CSS/JS offline; caches são atualizados quando há nova versão

---

## Phase 6: User Story 4 — Experiência Visual Nativa em Mobile (Priority: P2)

**Goal**: O app parece nativo em mobile: orientação retrato, cores na barra de status, ícones nítidos em múltiplas resoluções.

**Independent Test**: Abrir app em smartphone, verificar orientação fixa em retrato, cor da barra de status combinando com o app, ícones nítidos na tela inicial.

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T030 [P] [US4] Create `src/apps/auth/tests/test_pwa_meta_tags.py` with test que verifica que `base.html` contém `meta name="theme-color"` com valor `#14b8a6` e `meta name="apple-mobile-web-app-capable"` com valor `yes`

### Implementation for User Story 4

- [x] T031 [US4] Add `meta name="apple-mobile-web-app-capable" content="yes"` ao `<head>` de `src/templates/base.html` (já existe `theme-color` em #14b8a6 desde feature 002)
- [x] T032 [US4] Add `meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"` ao `<head>` de `src/templates/base.html` para cor da barra de status no iOS
- [x] T033 [US4] Add `link rel="apple-touch-icon"` tags ao `<head>` de `src/templates/base.html` apontando para os ícones 192×192 e 512×512
- [x] T034 [US4] Verify `PWA_APP_CONFIG` em `settings/base.py` contém `display: 'standalone'` e `orientation: 'portrait'` — o django-pwa injeta isso no manifesto automaticamente

**Checkpoint**: User Story 4 funcionando — app abre em standalone, orientação retrato, barra de status colorida, ícones nítidos

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Testes unitários adicionais, auditoria Lighthouse, verificação de conformidade com a Constitution

- [x] T035 [P] Create `src/apps/auth/tests/test_pwa_config.py` com testes que verificam: `'pwa'` está em `INSTALLED_APPS`; `PWA_APP_CONFIG` contém `name`, `short_name`, `display`, `orientation`, `theme_color`, `background_color`, `icons`
- [x] T036 [P] Create `src/apps/auth/tests/test_pwa_logout_header.py` com teste que renderiza `templates/partials/nav/_header.html` e verifica presença do link `/logout/` com texto "Sair"
- [x] T037 Run Lighthouse PWA audit no Chrome DevTools e verificar pontuação ≥ 90; documentar resultado em `specs/005-pwa-persistent-auth/lighthouse-report.md`
- [x] T038 [P] UX Fricção Zero audit: verificar que banner de instalação e botão de logout têm área de toque ≥ 48×48 dp; nenhum `<select>` é usado nesta feature
- [x] T039 [P] Anti-SPA verification: confirmar que não há React/Vue/Angular/Svelte introduzidos; `pwa-install-banner.js` e `pwa-session-manager.js` têm ≤ 50 linhas cada ou justificativa documentada
- [x] T040 [P] Type hints static analysis: rodar `mypy` em `src/apps/auth/` e garantir zero erros
- [x] T041 Commit all changes e push para branch `005-pwa-persistent-auth`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3–6)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) — Reuses base template from Phase 2; no dependency on US1
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) — Depends on US1 (ícones já criados) mas pode ser feito em paralelo se ícones placeholders forem usados
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) — No dependencies on other stories

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Assets (ícones, scripts) can be created in parallel
- Integration tasks (template updates) depend on assets being ready
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, US1 and US2 (ambos P1) can start in parallel
- US3 and US4 (ambos P2) can start in parallel após US1/US2 ou junto se capacidade permite
- All tests for a user story marked [P] can run in parallel (escrita dos testes)
- Polish phase tasks marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Create src/apps/auth/tests/test_pwa_manifest.py"
Task: "Create src/apps/auth/tests/test_pwa_template.py"
Task: "Create src/apps/auth/tests/test_pwa_serviceworker.py"

# Launch all assets for User Story 1 together:
Task: "Create src/static/images/pwa/icon-192x192.png"
Task: "Create src/static/images/pwa/icon-512x512.png"
Task: "Create src/static/js/pwa-install-banner.js"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (Instalação PWA) + Phase 4: User Story 2 (Sessão Persistente)
4. **STOP and VALIDATE**: Testar instalação e persistência de sessão
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 + User Story 2 → Testar instalação e sessão → Deploy/Demo (MVP!)
3. Add User Story 3 → Testar cache offline → Deploy/Demo
4. Add User Story 4 → Testar experiência visual nativa → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (instalação + banner)
   - Developer B: User Story 2 (sessão + logout)
3. When US1/US2 complete:
   - Developer A: User Story 3 (service worker + cache)
   - Developer B: User Story 4 (meta tags + ícones iOS)
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
