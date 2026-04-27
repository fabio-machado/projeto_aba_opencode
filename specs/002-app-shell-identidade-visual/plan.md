# Implementation Plan: App Shell e Identidade Visual

**Branch**: `002-app-shell-identidade-visual` | **Date**: 2026-04-24 | **Spec**: [specs/002-app-shell-identidade-visual/spec.md](specs/002-app-shell-identidade-visual/spec.md)
**Input**: Feature specification from `/specs/002-app-shell-identidade-visual/spec.md`

## Summary

O objetivo deste plano é construir o **App Shell mestre** e estabelecer a **Identidade Visual** do SaaS Autismo em Foco. O escopo abrange: configuração do Tailwind CSS com design tokens semânticos (cores, tipografia, espaçamento, elevação, arredondamento), suporte nativo a dark mode, template base `base.html` com estrutura de navegação (header fixo + conteúdo scrollável + barra inferior com FAB), fragmentos parciais reutilizáveis para header e navegação, bottom sheet de criação rápida, e ícones Heroicons com estados sólido/outline.

A abordagem é visual-estrutural primeiro: tokens de design → App Shell → interatividade (dark mode, bottom sheet, navegação). Cada passo é validado contra a Constitution Check e os critérios de acessibilidade WCAG AA.

## Technical Context

**Language/Version**: Python 3.12 (Django templates), JavaScript (Alpine.js), CSS (Tailwind CSS)  
**Primary Dependencies**: Tailwind CSS (CDN), HTMX (CDN), Alpine.js (CDN), Heroicons (CDN)  
**Storage**: LocalStorage (preferências de tema e estado de UI)  
**Testing**: Lighthouse Accessibility Audit, WCAG contrast checker, manual touch-target verification  
**Target Platform**: Web Mobile First (Android Chrome, iOS Safari)  
**Project Type**: web-service  
**Performance Goals**: Transição tema ≤ 300ms; bottom sheet abertura ≤ 200ms; time-to-first-interactive ≤ 3s em 3G  
**Constraints**: Anti-SPA; área de toque ≥ 48×48 dp; contraste WCAG AA; Teste do Supermercado  
**Scale/Scope**: Cuidadores e terapeutas ABA; uso com uma mão; sessões de 2–3 horas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I. UX Fricção Zero | Ações primárias exigem ≤ 5 segundos e área de toque ≥ 48×48 dp? | ✅ Bottom nav e FAB com min 48px; bottom sheet acessível em 1 toque |
| I. UX Fricção Zero | Inputs frequentes usam Toggle/Radio Buttons (nenhum `<select>` primário)? | ✅ Não há inputs nesta feature; layout preparado para botões grandes |
| II. SSR Dinâmico | Nenhum framework SPA (React/Vue/Angular/Svelte) proposto? | ✅ Apenas HTMX + Alpine.js; Tailwind via CDN |
| II. SSR Dinâmico | Conteúdo dinâmico usará HTMX com fragmentos `_partial.html`? | ✅ `#app-canvas` pronto para HTMX swaps; partials em `templates/partials/nav/` |
| III. Service Layer | Lógica de negócio isolada em `services.py` (views sem regras)? | ✅ Esta feature é puramente UI; não há lógica de negócio |
| III. Service Layer | Dados core de pacientes usarão `supabase-py` (Anti-ORM)? | ✅ Não aplicável a esta feature |
| IV. RLS-First | UUIDs serializados como `str(uuid)` antes do SDK Supabase? | ✅ Não aplicável a esta feature |
| IV. RLS-First | Queries filtram por `parent_id = auth.uid()` ou validação equivalente? | ✅ Não aplicável a esta feature |
| V. Offline-First | Estado local persiste via Alpine.js + LocalStorage? | ✅ Tema e preferências de UI em LocalStorage; script anti-FART no `<head>` |
| V. Offline-First | UI indica estado de sincronização (online/offline/pendente)? | ✅ Badge de status preparado no header (stub para backend futuro) |

## Project Structure

### Documentation (this feature)

```text
specs/002-app-shell-identidade-visual/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── templates/
│   ├── base.html                 # App Shell mestre
│   └── partials/
│       └── nav/
│           ├── _header.html      # Header fixo
│           ├── _bottom_nav.html  # Barra de navegação inferior
│           └── _bottom_sheet.html # Bottom sheet de criação rápida
├── static/
│   ├── css/
│   │   └── theme.css             # Variáveis CSS custom properties (fallback)
│   └── js/
│       └── theme.js              # Script anti-FART para dark mode
└── apps/
    └── shell/                    # Django app para views do App Shell (opcional)
        ├── __init__.py
        ├── views.py
        └── urls.py
```

**Structure Decision**: O App Shell é implementado como templates Django reutilizáveis. Como esta feature é puramente visual, pode não exigir um app Django dedicado inicialmente — os templates residem em `src/templates/` global. O app `shell` é criado apenas se houver views específicas (ex: dashboard inicial).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Nenhuma violação detectada. Todos os checks da Constitution passam sem necessidade de justificativa.

## Phase 0: Research & Decisions

Ver [research.md](research.md) para detalhes completos das decisões técnicas investigadas.

Resumo das decisões críticas:

1. **Ícones**: Heroicons v2 via CDN (outline/solid variants) — oficial Tailwind, sem build step
2. **Dark mode**: Tailwind `darkMode: 'class'` strategy — permite override manual + detecção automática
3. **Bottom sheet**: Alpine.js puro + Tailwind transitions — sem dependências extras
4. **Design tokens**: Mapeados no `tailwind.config` via script CDN — classes utilitárias semânticas (`bg-primary`, `text-on-surface`)
5. **Partials**: Header, bottom nav e bottom sheet como partials Django em `templates/partials/nav/`
6. **Marca**: Texto "Autismo em Foco" como placeholder para logo futuro
7. **Notificações**: Badge stub no header, preparado para HTMX swap futuro
8. **Transições**: `duration-200` para todos os estados interativos; tema em < 300ms

## Phase 1: Design & Contracts

### Data Model

Ver [data-model.md](data-model.md) para o modelo de dados completo.

Entidades principais:
- **UserThemePreference**: Persistência de tema no LocalStorage (`light`/`dark`/`system`)
- **NavigationState**: Seção ativa e estado do bottom sheet
- **AppShellLayout**: Dimensões fixas do layout (header 64px, bottom nav 64px, safe areas)
- **DesignTokenRegistry**: Todos os tokens semânticos mapeados para Tailwind
- **BottomSheetAction**: Ações de criação rápida (Nova Rotina, Novo Registro)
- **NotificationBadge**: Indicador de notificações no header (stub)

### Contracts

Ver diretório [contracts/](contracts/) para contratos de interface.

Contratos definidos:
- **App Shell Response**: Estrutura do `base.html` e convenção de partials
- **Theme Toggle Contract**: API JavaScript para alternância de tema (Alpine.js + LocalStorage)
- **Bottom Sheet Contract**: Estados e eventos do bottom sheet (abrir/fechar/selecionar)

### Quickstart

Ver [quickstart.md](quickstart.md) para guia de primeiro acesso.

## Phase 2: Tasks

Será gerado pelo comando `/speckit.tasks` com base neste plano e na especificação.
