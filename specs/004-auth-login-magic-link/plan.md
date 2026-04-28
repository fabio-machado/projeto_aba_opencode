# Implementation Plan: Auth Login Screen (Magic Link Flow)

**Branch**: `004-auth-login-magic-link` | **Date**: 2026-04-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-auth-login-magic-link/spec.md`

## Summary

Implementar tela de login (`/login`) com autenticação exclusiva por Magic Link via Supabase Auth. A tela é pública, com campo único de e-mail, validação de usuário pagante ativo antes do disparo do link, rate limiting por e-mail e IP, detecção de enumeração, e sessão persistente de 90 dias com refresh tokens. O design segue rigorosamente os tokens visuais estabelecidos na spec 002 (Teal-500, Inter, rounded-xl, contrastes WCAG AA).

**Technical approach**: Novo app Django `apps/auth_app` seguindo o Service Layer pattern (services.py com toda lógica de negócio, views thin). Integração com Supabase Auth Admin API para disparo de Magic Link e verificação de usuário. Proteção de rotas via middleware Django + Supabase session cookie. Rate limiting e logging implementados via tabelas Supabase.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: Django 5.x, django-htmx, HTMX 2.0.4, Alpine.js 3.14.8, Tailwind CSS (CDN), supabase-py, Stripe Python SDK
**Storage**: Supabase (PostgreSQL + RLS) — tabelas `profiles`, `magic_link_logs`, `audit_logs` já existentes via spec 003
**Testing**: pytest, Django TestCase (padrões do projeto em `apps/payments/tests/`)
**Target Platform**: Web Mobile First (smartphones Android/iOS ≤ 3 anos, 5.5–6.7 polegadas)
**Project Type**: web-service
**Performance Goals**: Submissão do formulário → resposta ≤ 5s (UX Fricção Zero); troca de fragmentos HTMX ≤ 200ms p95
**Constraints**: Anti-SPA (HTMX + Alpine.js apenas); Service Layer; Type hints estritos; área de toque ≥ 48×48 dp; contraste WCAG AA 4.5:1
**Scale/Scope**: Cuidadores de crianças com TEA; autenticação sem senha; acesso condicionado a conta pagante ativa

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I. UX Fricção Zero | Ações primárias exigem ≤ 5 segundos e área de toque ≥ 48×48 dp? | ✅ PASS — Login: campo e-mail único + botão "Receber Acesso". Toque: 48×48dp herdado do spec 002. US1 esc.3: submissão ≤ 5s. |
| I. UX Fricção Zero | Inputs frequentes usam Toggle/Radio Buttons (nenhum `<select>` primário)? | ✅ N/A — Apenas `<input type="email">`, nenhum `<select>`. |
| II. SSR Dinâmico | Nenhum framework SPA (React/Vue/Angular/Svelte) proposto? | ✅ PASS — Django SSR + HTMX para submissão parcial + Alpine.js para estado do formulário. |
| II. SSR Dinâmico | Conteúdo dinâmico usará HTMX com fragmentos `_partial.html`? | ✅ PASS — Resposta de erro/sucesso via HTMX partial swap (`_login_feedback.html`). |
| III. Service Layer | Lógica de negócio isolada em `services.py` (views sem regras)? | ✅ PASS — `apps/auth_app/services.py`: validação de e-mail, lookup Supabase, rate limiting, disparo Magic Link, logging. |
| III. Service Layer | Dados core de pacientes usarão `supabase-py` (Anti-ORM)? | ✅ N/A — Login não manipula dados de pacientes. |
| III. Service Layer | Type hints estritos definidos para toda interface Python? | ✅ PASS — Todas as funções em services.py e views.py com type hints. |
| IV. RLS-First | UUIDs serializados como `str(uuid)` antes do SDK Supabase? | ✅ N/A — Queries no login são read-only em `profiles` e write em `magic_link_logs`. |
| IV. RLS-First | Queries filtram por `parent_id = auth.uid()` ou validação equivalente? | ✅ N/A — Não são dados de pacientes. |
| IV. RLS-First | Escritas em dados de pacientes geram log de auditoria? | ✅ N/A — Não há escrita em dados de pacientes. Logging de tentativas de login feito em tabela separada. |
| V. Offline-First | Estado local persiste via Alpine.js + LocalStorage? | ✅ N/A — Login é operação intrinsicamente online (requer rede para Magic Link). |
| V. Offline-First | UI indica estado de sincronização (online/offline/pendente)? | ✅ PASS — Indicador de loading durante submissão + feedback de erro de rede. |
| V. Offline-First | Conflitos usam last-write-wins com log para auditoria? | ✅ N/A — Sem escritas offline no fluxo de login. |

**Gate Result**: ALL PASS — Nenhuma violação. Zero entradas no Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/004-auth-login-magic-link/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── login-form.md    # POST /login contract
│   └── auth-callback.md # GET /auth/callback contract (existing, needs update)
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── apps/
│   └── auth_app/                     # NOVO: app de autenticação
│       ├── __init__.py
│       ├── apps.py                   # AppConfig
│       ├── services.py               # Lógica: login_request, validate_user, rate_limit_check, send_magic_link, invalidate_session
│       ├── views.py                  # Thin views: login_view (GET), login_submit (POST), logout_view, auth_callback (refactored)
│       ├── urls.py                   # /login, /logout, /auth/callback
│       ├── middleware.py             # LoginRequiredMiddleware: proteção de rotas
│       └── templates/
│           └── auth_app/
│               ├── login.html        # Tela de login (estende base.html, override header/nav)
│               └── partials/
│                   └── _login_feedback.html  # HTMX partial: sucesso/erro
├── templates/
│   ├── base.html                     # Layout mestre (já existe — spec 002)
│   ├── partials/
│   │   └── nav/
│   │       ├── _header.html          # Header existente
│   │       ├── _bottom_nav.html      # Bottom nav existente
│   │       └── _bottom_sheet.html    # Bottom sheet existente
│   └── ...
├── config/
│   ├── urls.py                       # Adicionar: path('', include('apps.auth_app.urls'))
│   ├── settings/
│   │   └── base.py                   # Adicionar: 'apps.auth_app' em INSTALLED_APPS
│   └── logging_config.py             # Já existe (structlog)
└── static/
    ├── css/
    │   └── theme.css                 # Design tokens (spec 002)
    ├── js/
    │   ├── app-shell.js              # Alpine.js: tema, sheet (spec 002)
    │   └── auth.js                   # NOVO: Alpine.js login form state
    └── images/
```

**Structure Decision**: `apps/auth_app` é um novo app Django seguindo os padrões estabelecidos por `apps/payments` (service layer, thin views, type hints) e `apps/core` (serviços compartilhados).

### Regra de localização de templates (Constitution §Estrutura de Projeto)

A Constitution determina que **templates de cada app residem dentro do próprio app** em `templates/<app_name>/partials/`. Templates **compartilhados** entre apps (ex: `base.html`, partials de navegação) residem no diretório central `src/templates/`. Ambos são resolvidos pelo Django via:

- `TEMPLATES[0]['DIRS'] = [BASE_DIR / 'templates']` → templates compartilhados
- `TEMPLATES[0]['APP_DIRS'] = True` → templates dentro de cada app

| Tipo de template | Localização | Exemplo |
|------------------|-------------|---------|
| Compartilhado (layout, nav, base) | `src/templates/` | `src/templates/base.html` |
| Compartilhado (partials de nav) | `src/templates/partials/nav/` | `src/templates/partials/nav/_header.html` |
| App-specific (páginas) | `src/apps/<app>/templates/<app>/` | `src/apps/auth_app/templates/auth_app/login.html` |
| App-specific (partials) | `src/apps/<app>/templates/<app>/partials/` | `src/apps/auth_app/templates/auth_app/partials/_login_feedback.html` |

**Nota sobre inconsistência atual**: Os apps placeholder (routines, guide, monitor, settings) armazenam templates em `src/templates/<app>/` — isso viola a Constitution e será corrigido quando esses apps forem implementados. O app `payments` e o novo `auth_app` seguem o padrão correto (templates dentro do app).

Os partials de navegação (header, bottom nav) são omitidos na tela de login — a página usa um layout minimalista sem shell de navegação, conforme definido no spec como rota pública.
