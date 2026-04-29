# Implementation Plan: PWA com Sessão Persistente

**Branch**: `005-pwa-persistent-auth` | **Date**: 2026-04-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-pwa-persistent-auth/spec.md`

## Summary

Adicionar capacidades PWA à aplicação Django existente usando `django-pwa`, garantindo que o app possa ser instalado na tela inicial de dispositivos móveis, carregue instantaneamente via cache de assets, e mantenha a sessão do usuário persistente através da integração com Supabase Auth. Esta feature não cria nova lógica de autenticação — ela reutiliza a sessão de 90 dias e o refresh token já implementados pela feature 004 (Auth Login Magic Link) — mas adiciona a camada PWA (manifesto, service worker, meta tags) e scripts de UX (banner de instalação, verificação de sessão ao abrir).

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: Django 5.x, django-htmx, HTMX, Alpine.js, Tailwind CSS, supabase-py, django-pwa
**Storage**: Supabase (PostgreSQL + RLS) — tokens de sessão persistidos em cookies HTTP-only; frontend usa LocalStorage para estado UI
**Testing**: pytest, Django TestCase
**Target Platform**: Web (Mobile First browsers) — PWA instalável em Android/iOS
**Project Type**: web-service
**Performance Goals**: Registros ABC ≤ 5s; troca de fragmentos HTMX ≤ 200ms p95; carregamento visual do app em aberturas subsequentes < 1s
**Constraints**: Offline-first via LocalStorage; Anti-SPA; Anti-ORM para dados core de pacientes; área de toque ≥ 48×48 dp
**Scale/Scope**: Cuidadores de crianças com TEA; funil Low Ticket → Order Bump → Core SaaS

### Decisões de Arquitetura

- **django-pwa**: Biblioteca madura e mantida que gera automaticamente o manifest.json, registra URLs para manifest/serviceworker, e fornece template tags (`{% progressive_web_app_meta %}`). Evita reimplementar manualmente.
- **Service Worker**: Usar o template padrão do django-pwa como ponto de partida, customizado para fazer cache dos assets estáticos do projeto (CSS, JS, ícones). Não usar Workbox (adição de complexidade desnecessária para cache simples).
- **Persistência de Sessão**: O Supabase JS client no frontend já suporta `persistSession: true`. O backend (feature 004) já configura cookies HTTP-only com 90 dias de duração. O script frontend apenas verifica se a sessão está próxima de expirar e chama `refreshSession()`.
- **Banner de Instalação**: Script customizado em JavaScript vanilla (≤ 50 linhas, conforme Constitution) que escuta `beforeinstallprompt`, guarda o evento, e exibe um banner discreto. Usa Alpine.js para toggle de visibilidade.
- **Logout no Menu**: O botão de logout já existe na service layer (`auth/services.py::clear_session_cookies`). Esta feature apenas expõe o botão no menu da header, reutilizando a rota `/logout/` existente.

### O que NÃO será implementado (já existe em outras features)

| Funcionalidade | Feature Responsável |
|----------------|---------------------|
| Estrutura base Django, HTMX, Alpine.js, Tailwind | 001-django-core-scaffold |
| App Shell, Header, Bottom Nav, Dark Mode, Design Tokens | 002-app-shell-identidade-visual |
| Criação automática de conta via Stripe webhook | 003-stripe-webhook-auto-account |
| Magic Link flow, sessão de 90 dias, refresh tokens, proteção de rotas, rate limiting | 004-auth-login-magic-link |
| Rota `/logout/` e `clear_session_cookies()` | 004-auth-login-magic-link |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design — all gates pass.*

| Principle | Check | Status |
|-----------|-------|--------|
| I. UX Fricção Zero | Ações primárias exigem ≤ 5 segundos e área de toque ≥ 48×48 dp? | ✅ Pass |
| I. UX Fricção Zero | Inputs frequentes usam Toggle/Radio Buttons (nenhum `<select>` primário)? | ✅ Pass (não aplica) |
| II. SSR Dinâmico | Nenhum framework SPA (React/Vue/Angular/Svelte) proposto? | ✅ Pass |
| II. SSR Dinâmico | Conteúdo dinâmico usará HTMX com fragmentos `_partial.html`? | ✅ Pass |
| III. Service Layer | Lógica de negócio isolada em `services.py` (views sem regras)? | ✅ Pass (logout reutiliza auth/services.py) |
| III. Service Layer | Dados core de pacientes usarão `supabase-py` (Anti-ORM)? | ✅ Pass (não envolve dados core) |
| III. Service Layer | Type hints estritos definidos para toda interface Python? | ✅ Pass |
| IV. RLS-First | UUIDs serializados como `str(uuid)` antes do SDK Supabase? | ✅ Pass (não aplica) |
| IV. RLS-First | Queries filtram por `parent_id = auth.uid()` ou validação equivalente? | ✅ Pass (não aplica) |
| IV. RLS-First | Escritas em dados de pacientes geram log de auditoria? | ✅ Pass (não aplica) |
| V. Offline-First | Estado local persiste via Alpine.js + LocalStorage? | ✅ Pass (service worker adiciona cache de assets) |
| V. Offline-First | UI indica estado de sincronização (online/offline/pendente)? | ✅ Pass (indicadores já existem) |
| V. Offline-First | Conflitos usam last-write-wins com log para auditoria? | ✅ Pass (não aplica a esta feature) |

## Project Structure

### Documentation (this feature)

```text
specs/005-pwa-persistent-auth/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (minimal — no new entities)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (service worker contract)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── config/
│   ├── settings/base.py          # + PWA_APP_CONFIG, + 'pwa' em INSTALLED_APPS
│   └── urls.py                   # + path('', include('pwa.urls'))
├── templates/
│   └── base.html                 # + {% load pwa %}, + {% progressive_web_app_meta %}
├── static/
│   ├── css/
│   │   └── (theme.css já existe — sem alterações)
│   ├── js/
│   │   ├── app-shell.js          # (já existe)
│   │   ├── bottom-sheet.js       # (já existe)
│   │   ├── pwa-install-banner.js # NOVO: banner de instalação + beforeinstallprompt
│   │   └── pwa-session-manager.js# NOVO: verificação/refresh de sessão Supabase
│   └── images/
│       └── pwa/
│           ├── icon-192x192.png  # NOVO
│           ├── icon-512x512.png  # NOVO
│           └── maskable-icon.png # NOVO (opcional, recomendado)
└── apps/
    └── auth/
        ├── services.py           # (já existe — reutiliza clear_session_cookies)
        ├── views.py              # (já existe — reutiliza logout view)
        └── urls.py               # (já existe — reutiliza /logout/)
```

**Structure Decision**: A feature não cria um novo Django app. As alterações são cross-cutting, afetando `config/`, `templates/`, e `static/`. O `django-pwa` é adicionado como app de terceiros. Scripts JS são colocados em `static/js/` e ícones em `static/images/pwa/`. O botão de logout é adicionado ao template parcial do header (`templates/partials/nav/_header.html`) que já existe.

## Complexity Tracking

> No Constitution violations detected. No complexity tracking required.

## Phase 0: Research

See [research.md](research.md) for consolidated findings.

**Key decisions**:
- `django-pwa` escolhido por ser a solução mais madura e de menor fricção para Django
- Service worker usa estratégia Cache-First para assets estáticos (CSS, JS, ícones), Network-First para dados dinâmicos (não cacheados — dados vêm do servidor via HTMX)
- `persistSession: true` no Supabase JS client garante que tokens sejam armazenados no LocalStorage do navegador e recuperados automaticamente
- Banner de instalação guarda o evento `beforeinstallprompt` e o dispara quando o usuário clica no botão; se já instalado, banner fica oculto

## Phase 1: Design

### Data Model

Esta feature **não introduz novas entidades de dados** no banco. Reutiliza:
- **Sessão de Usuário** (feature 004): cookies `supabase_session` e `supabase_refresh`
- **Magic Link Logs** (feature 004): tabela `magic_link_logs`
- **Profiles** (feature 003): tabela `profiles`

A única adição é o **Cache de Aplicação** (browser-side), gerenciado pelo Service Worker, que persiste em `CacheStorage` (API do navegador).

Ver [data-model.md](data-model.md) para detalhes.

### Contracts

Ver [contracts/service-worker.md](contracts/service-worker.md) para o contrato do Service Worker.

### Quickstart

Ver [quickstart.md](quickstart.md) para instruções de desenvolvimento e teste.

## Testability & Unit Tests

Esta feature possui pontos testáveis com testes unitários e de integração:

### Testes Unitários (Python — pytest)

1. **Configuração PWA** (`tests/unit/test_pwa_config.py`):
   - Verificar que `PWA_APP_CONFIG` contém `name`, `short_name`, `display`, `orientation`, `theme_color`, `background_color`, `icons`
   - Verificar que `'pwa'` está em `INSTALLED_APPS`
   - Verificar que as URLs do PWA estão registradas em `urls.py`

2. **Manifesto JSON** (`tests/unit/test_pwa_manifest.py`):
   - Fazer request GET para `/manifest.json` (URL provida pelo django-pwa)
   - Verificar que o JSON retornado contém todos os campos obrigatórios do manifesto
   - Verificar que `display` é `standalone` e `orientation` é `portrait`

3. **Template Base** (`tests/unit/test_pwa_template.py`):
   - Renderizar `base.html`
   - Verificar que contém `<link rel="manifest"`
   - Verificar que contém meta tags `theme-color` e `apple-mobile-web-app-capable`

4. **Service Worker Acessível** (`tests/unit/test_pwa_serviceworker.py`):
   - Fazer request GET para `/serviceworker.js` (URL provida pelo django-pwa)
   - Verificar status 200 e Content-Type `application/javascript`

### Testes de Integração / E2E

1. **Instalação PWA**: Verificar que o app é instalável via Lighthouse PWA audit
2. **Cache de Assets**: Desconectar rede, abrir app, verificar que CSS/JS/ícones carregam
3. **Sessão Persistente**: Fechar app, reabrir após 7 dias, verificar que usuário permanece autenticado
4. **Banner de Instalação**: Simular `beforeinstallprompt`, verificar que banner aparece; após instalação, verificar que banner desaparece

## Implementation Checklist

- [ ] Adicionar `django-pwa` ao `requirements.txt`
- [ ] Adicionar `'pwa'` a `INSTALLED_APPS` em `settings/base.py`
- [ ] Configurar `PWA_APP_CONFIG` em `settings/base.py`
- [ ] Adicionar `path('', include('pwa.urls'))` a `urls.py`
- [ ] Adicionar `{% load pwa %}` e `{% progressive_web_app_meta %}` ao `base.html`
- [ ] Criar `static/js/pwa-session-manager.js` — verificação/refresh de sessão Supabase
- [ ] Criar `static/js/pwa-install-banner.js` — banner de instalação com `beforeinstallprompt`
- [ ] Criar `static/images/pwa/icon-192x192.png`
- [ ] Criar `static/images/pwa/icon-512x512.png`
- [ ] Adicionar botão de logout ao menu da header (`templates/partials/nav/_header.html`)
- [ ] Criar testes unitários para configuração PWA, manifesto, template, service worker
- [ ] Executar auditoria Lighthouse PWA e verificar pontuação ≥ 90
