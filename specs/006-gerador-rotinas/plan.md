# Implementation Plan: Gerador de Rotinas (Módulo Rotinas)

**Branch**: `006-gerador-rotinas` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-gerador-rotinas/spec.md`

## Summary

Implementar o módulo de rotinas visuais — produto *low ticket* de entrada da plataforma Autismo em Foco. O cuidador cria rotinas compostas por pictogramas via construtor mobile-first com drag-and-drop (Alpine.js + SortableJS), gerencia-as em um mural de cards, e exporta cada rotina como PDF. A arquitetura segue Service Layer (Anti-ORM): views delegam toda lógica para `routine_service.py`, que usa exclusivamente `supabase-py`. Sincronização offline-first via LocalStorage + Alpine.js.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: Django 5.x, django-htmx, HTMX, Alpine.js, Tailwind CSS, supabase-py, SortableJS  
**Storage**: Supabase (PostgreSQL + RLS) — tabelas: `routines`, `routine_items`, `pictograms`, `pictogram_categories`  
**Testing**: pytest, Django TestCase  
**Target Platform**: Web (Mobile First browsers, PWA-ready)  
**Project Type**: web (Django app server-rendered with HTMX partials)  
**Performance Goals**: Pictograma adicionado à timeline < 200ms; PDF export < 3s; Salvamento offline com resiliência 95%  
**Constraints**: Offline-first via LocalStorage + Alpine.js; Anti-SPA (zero React/Vue/Angular); Anti-ORM para dados core; Área de toque ≥ 48×48 dp; WCAG 2.1 AA  
**Scale/Scope**: Cuidadores de crianças com TEA; baixo volume de rotinas por cuidador (50-100), cada rotina com até 15 pictogramas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I. UX Fricção Zero | Pictograma adicionado com 1 toque, construtor operável com 1 mão, zona do polegar | ✅ |
| I. UX Fricção Zero | Input de título (texto livre, sem `<select>`) + botões grandes (≥48dp) | ✅ |
| II. SSR Dinâmico | Sem frameworks SPA — apenas Alpine.js para estado do builder + HTMX para card actions | ✅ |
| II. SSR Dinâmico | Templates parciais HTMX (ex: `_routine_card.html`, `_pictogram_timeline.html`) | ✅ |
| III. Service Layer | Toda lógica de negócio em `routine_service.py`; views apenas validam + delegam | ✅ |
| III. Service Layer | Dados core (routines, pictograms, routine_items) usam `supabase-py` exclusivamente | ✅ |
| III. Service Layer | Type hints estritos em todas as interfaces Python | ✅ |
| IV. RLS-First | UUIDs serializados como `str(uuid)` antes de operações Supabase | ✅ |
| IV. RLS-First | Queries filtram por `parent_id = auth.uid()` via RLS policies + service layer | ✅ |
| IV. RLS-First | Escritas geram log de auditoria via `AuditLogService` existente | ✅ |
| V. Offline-First | Estado do builder persiste em LocalStorage (título + array pictogramas) | ✅ |
| V. Offline-First | UI indica estado de sincronização (pendente/salvo) no botão Salvar | ✅ |
| V. Offline-First | Conflitos last-write-wins com log para auditoria | ✅ |

**Gate Result**: ALL PASS — Nenhuma violação. Prosseguir para Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/006-gerador-rotinas/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── routine_builder.md
│   └── pdf_export.md
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
src/
├── apps/
│   └── routines/
│       ├── __init__.py
│       ├── apps.py
│       ├── services.py          # routine_service — CRUD Supabase, batch edit, PDF gen
│       ├── views.py             # routine_list_view, routine_builder_view, routine_save, routine_rename, routine_delete, routine_export_pdf
│       ├── urls.py              # /routines/, /routines/create/, /routines/save/, /routines/<uuid>/delete/, /routines/<uuid>/rename/, /routines/<uuid>/export/
│       └── templates/
│           └── routines/
│               ├── routine_list.html          # Mural (cards, empty state, FAB)
│               ├── routine_builder.html       # Construtor (timeline, gaveta, drag-drop)
│               └── partials/
│                   ├── _routine_card.html     # Card individual com ações (HTMX)
│                   ├── _empty_state.html      # Estado vazio acolhedor
│                   ├── _timeline_item.html    # Item da timeline (pictograma)
│                   └── _pictogram_grid.html   # Grade de pictogramas da gaveta
├── static/
│   └── js/
│       └── routine-builder.js    # Alpine.js: estado do builder, array pictogramas, SortableJS init (binding manual via x-init), LocalStorage sync
└── templates/
    └── routines/                 # (já existe — será substituído por app-level templates)
```

**Structure Decision**: Templates colocalizados dentro de `src/apps/routines/templates/routines/` (padrão Django com namespace de app) em vez de `src/templates/routines/`. O diretório existente `src/templates/routines/` (placeholders) será removido. Scripts Alpine.js em `src/static/js/` seguindo o padrão existente.

## Complexity Tracking

> Nenhuma violação detectada. Seção vazia.
