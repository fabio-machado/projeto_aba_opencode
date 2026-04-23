# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

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
| I. UX Fricção Zero | Ações primárias exigem ≤ 5 segundos e área de toque ≥ 48×48 dp? | [ ] |
| I. UX Fricção Zero | Inputs frequentes usam Toggle/Radio Buttons (nenhum `<select>` primário)? | [ ] |
| II. SSR Dinâmico | Nenhum framework SPA (React/Vue/Angular/Svelte) proposto? | [ ] |
| II. SSR Dinâmico | Conteúdo dinâmico usará HTMX com fragmentos `_partial.html`? | [ ] |
| III. Service Layer | Lógica de negócio isolada em `services.py` (views sem regras)? | [ ] |
| III. Service Layer | Dados core de pacientes usarão `supabase-py` (Anti-ORM)? | [ ] |
| III. Service Layer | Type hints estritos definidos para toda interface Python? | [ ] |
| IV. RLS-First | UUIDs serializados como `str(uuid)` antes do SDK Supabase? | [ ] |
| IV. RLS-First | Queries filtram por `parent_id = auth.uid()` ou validação equivalente? | [ ] |
| IV. RLS-First | Escritas em dados de pacientes geram log de auditoria? | [ ] |
| V. Offline-First | Estado local persiste via Alpine.js + LocalStorage? | [ ] |
| V. Offline-First | UI indica estado de sincronização (online/offline/pendente)? | [ ] |
| V. Offline-First | Conflitos usam last-write-wins com log para auditoria? | [ ] |

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
src/
├── manage.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py / asgi.py
├── apps/
│   ├── [app_name]/
│   │   ├── services.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── templates/
│   │       └── [app_name]/
│   │           └── partials/
│   │               └── _partial.html
│   └── ...
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
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
