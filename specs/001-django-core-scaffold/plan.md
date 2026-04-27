# Implementation Plan: Django Core Scaffold

**Branch**: `001-django-core-scaffold` | **Date**: 2026-04-23 | **Spec**: [specs/001-django-core-scaffold/spec.md](specs/001-django-core-scaffold/spec.md)
**Input**: Feature specification from `/specs/001-django-core-scaffold/spec.md`

## Summary

O objetivo deste plano é construir o esqueleto base da aplicação **Autismo em Foco**, garantindo que toda a arquitetura nasça em conformidade com a Constitution v1.0.0. O escopo abrange: estrutura de diretórios `src/` com Django 5.x, containerização Docker com paridade DEV/PRD, integração MCP com Supabase e Stripe, templates base HTMX/Alpine.js/Tailwind CSS (CDN), settings multi-ambiente, logging estruturado nativo, e um app de exemplo demonstrando o Service Layer Pattern.

A abordagem é bottom-up: infraestrutura Docker → configuração Django → integrações externas → templates base → app de referência. Cada passo é validado contra a Constitution Check antes de prosseguir.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: Django 5.x, django-htmx, HTMX, Alpine.js, Tailwind CSS, supabase-py, Stripe  
**Storage**: Supabase (PostgreSQL + RLS)  
**Testing**: pytest, Django TestCase  
**Target Platform**: Web (Mobile First browsers)
**Project Type**: web-service  
**Performance Goals**: Registros ABC ≤ 5s; troca de fragmentos HTMX ≤ 200ms p95  
**Constraints**: Offline-first via LocalStorage; Anti-SPA; Anti-ORM para dados core de pacientes; área de toque ≥ 48×48 dp  
**Scale/Scope**: Cuidadores de crianças com TEA; funil Low Ticket → Order Bump → Core SaaS

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I. UX Fricção Zero | Ações primárias exigem ≤ 5 segundos e área de toque ≥ 48×48 dp? | ✅ Templates base usarão botões grandes (≥48dp) e contraste ≥4.5:1 |
| I. UX Fricção Zero | Inputs frequentes usam Toggle/Radio Buttons (nenhum `<select>` primário)? | ✅ Base CSS preparada para Toggle/Radio; `<select>` proibido em partials de registro |
| II. SSR Dinâmico | Nenhum framework SPA (React/Vue/Angular/Svelte) proposto? | ✅ Apenas HTMX + Alpine.js no requirements e templates |
| II. SSR Dinâmico | Conteúdo dinâmico usará HTMX com fragmentos `_partial.html`? | ✅ Convenção `templates/<app>/partials/_*.html` estabelecida |
| III. Service Layer | Lógica de negócio isolada em `services.py` (views sem regras)? | ✅ App `core` demonstra views delegando para `services.py` |
| III. Service Layer | Dados core de pacientes usarão `supabase-py` (Anti-ORM)? | ✅ `SupabaseService` isolado; ORM Django proibido para dados de pacientes |
| III. Service Layer | Type hints estritos definidos para toda interface Python? | ✅ mypy/pyright configurado; type hints obrigatórios em `services.py` |
| IV. RLS-First | UUIDs serializados como `str(uuid)` antes do SDK Supabase? | ✅ Helper `serialize_uuid()` em `services.py` |
| IV. RLS-First | Queries filtram por `parent_id = auth.uid()` ou validação equivalente? | ✅ `SupabaseService` aplica `eq("parent_id", user_id)` em toda query |
| IV. RLS-First | Escritas em dados de pacientes geram log de auditoria? | ✅ `AuditLog` integrado ao service layer |
| V. Offline-First | Estado local persiste via Alpine.js + LocalStorage? | ✅ `x-data` com `localStorage` no template base; indicador de sync visível |
| V. Offline-First | UI indica estado de sincronização (online/offline/pendente)? | ✅ Badge de status no header do `base.html` |
| V. Offline-First | Conflitos usam last-write-wins com log para auditoria? | ✅ Estratégia documentada em `services.py` com timestamp de resolução |

## Project Structure

### Documentation (this feature)

```text
specs/001-django-core-scaffold/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── manage.py
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prd.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   └── core/
│       ├── __init__.py
│       ├── services.py
│       ├── views.py
│       ├── urls.py
│       └── templates/
│           └── core/
│               └── partials/
│                   └── _example_partial.html
├── templates/
│   └── base.html
└── static/
    ├── css/
    ├── js/
    └── images/

tests/
├── contract/
├── integration/
└── unit/

# Infrastructure (repository root)
Dockerfile
docker-compose.yml
requirements.txt
.env.example
```

**Structure Decision**: A estrutura segue rigorosamente a Constitution: código-fonte em `src/`, apps Django em `src/apps/`, settings divididos por ambiente (`dev`/`prd`), e infra na raiz. O app `core` serve como referência de implementação para o Service Layer Pattern e partials HTMX.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Nenhuma violação detectada. Todos os checks da Constitution passam sem necessidade de justificativa.

## Phase 0: Research & Decisions

Ver [research.md](research.md) para detalhes completos das decisões técnicas investigadas.

Resumo das decisões críticas:

1. **Docker base image**: `python:3.12-slim` para equilibrar tamanho e compatibilidade
2. **Django settings**: Split obrigatório (`base.py`, `dev.py`, `prd.py`) via variável `DJANGO_SETTINGS_MODULE`
3. **Supabase client**: `supabase-py` com padrão Singleton para reutilização de conexão
4. **Stripe MCP**: Integração via MCP já habilitada no ambiente; usar SDK `stripe` com isolamento em `services.py`
5. **Tailwind CSS**: CDN inicial com script `<script src="https://cdn.tailwindcss.com"></script>`; reavaliação futura
6. **HTMX + Alpine.js**: Carregados via CDN no `base.html` para zero build step inicial
7. **Logging**: `structlog` ou `logging` padrão do Python com formato JSON em PRD e texto colorido em DEV
8. **Type hints**: `mypy` configurado em pre-commit/CI para garantir conformidade

## Phase 1: Design & Contracts

### Data Model

Ver [data-model.md](data-model.md) para o modelo de dados completo.

Entidades principais do scaffold:
- **ProjectConfig**: Settings e variáveis de ambiente (não persistente em DB)
- **AuditLog**: Registro de auditoria para RLS-First (Supabase table)
- **OfflineQueue**: Fila local de sync (LocalStorage via Alpine.js)

### Contracts

Ver diretório [contracts/](contracts/) para contratos de interface.

Contratos definidos:
- **HTMX Partial Response**: Formato padrão de resposta para trocas parciais
- **Service Layer Interface**: Padrão de `services.py` com type hints e separação de responsabilidades
- **View Response Pattern**: Views Django delegando para services e retornando `TemplateResponse` ou `HttpResponse`

### Quickstart

Ver [quickstart.md](quickstart.md) para guia de primeiro acesso.

## Phase 2: Tasks

Será gerado pelo comando `/speckit.tasks` com base neste plano e na especificação.
