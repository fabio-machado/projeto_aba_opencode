# Tasks: App Shell e Identidade Visual

**Feature**: 002-app-shell-identidade-visual  
**Branch**: `002-app-shell-identidade-visual`  
**Date**: 2026-04-24  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)  
**Tests**: NOT requested (no TDD approach specified)

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tasks | 34 |
| Setup Tasks | 2 |
| Foundational Tasks | 5 |
| US1 Tasks (P1) | 6 |
| US2 Tasks (P1) | 6 |
| US3 Tasks (P2) | 6 |
| US4 Tasks (P2) | 5 |
| Polish Tasks | 2 |
| Parallelizable Tasks | 14 |

---

## Dependency Graph

```
Phase 1 (Setup)
  └── T001 → T002

Phase 2 (Foundational)
  └── T003 → T004 → T005
  └── T006 → T007

Phase 3 (US1 - Navegação com Uma Mão)
  └── T008 → T009 → T010
  └── T011 [P] → T012 [P]

Phase 4 (US2 - Identidade Visual Calm e Acessível)
  └── T013 → T014 → T015
  └── T016 [P] → T017 [P] → T018 [P]

Phase 5 (US3 - Criação Rápida de Registros)
  └── T019 → T020 → T021
  └── T022 [P] → T023 [P] → T024 [P] → T025b [P]

Phase 6 (US4 - Orientação Visual de Navegação)
  └── T025 → T026 → T027
  └── T028 [P] → T029 [P] → T030b [P]

Final Phase (Polish)
  └── T030 → T031
  └── T032
```

---

## Implementation Strategy

**MVP Scope**: User Stories 1 + 2 (P1) — App Shell estrutural com navegação one-handed e identidade visual completa (cores, tipografia, dark mode). Sem bottom sheet funcional nem estados de navegação ativa.

**Incremental Delivery**:
1. **Sprint 1 (MVP)**: Phase 1 + Phase 2 + Phase 3 + Phase 4 — App Shell navegável com design tokens aplicados
2. **Sprint 2**: Phase 5 — Bottom sheet e FAB interativos
3. **Sprint 3**: Phase 6 — Estados de navegação ativa e header completo
4. **Sprint 4**: Final Phase — Acessibilidade, edge cases e validação Lighthouse

---

## Phase 1: Setup

**Goal**: Preparar estrutura de diretórios para templates, partials e assets estáticos.

**Independent Test**: `ls src/templates/partials/nav/` retorna 3 arquivos `.html`; `ls src/static/js/` e `ls src/static/css/` existem.

- [ ] T001 Criar estrutura de diretórios para templates e partials em `src/templates/` e `src/templates/partials/nav/`
- [ ] T002 Criar diretórios para assets estáticos em `src/static/js/` e `src/static/css/`

---

## Phase 2: Foundational (Design Tokens & Tailwind Config)

**Goal**: Configurar design tokens semânticos no Tailwind CSS e estabelecer base técnica para dark mode.

**Independent Test**: Abrir um arquivo HTML simples com o Tailwind CDN configurado mostra `bg-primary` como teal e `text-on-surface` como slate. O modo escuro funciona ao adicionar `class="dark"` no `<html>`.

- [ ] T003 Inserir script anti-FART **inline** no `<head>` de `src/templates/base.html` (síncrono, antes de qualquer CSS) para ler `localStorage.aef_theme` e aplicar classe `dark` no `<html>` antes da renderização
- [ ] T004 Configurar design tokens no Tailwind CDN em `src/templates/base.html` (cores, fonte, arredondamento, sombras)
- [ ] T005 Criar `src/static/css/theme.css` com variáveis CSS custom properties como fallback para tokens semânticos
- [ ] T006 [P] Configurar Google Fonts (Inter) no `<head>` de `src/templates/base.html`
- [ ] T007 [P] Configurar HTMX, Alpine.js e Heroicons CDN no `<head>` de `src/templates/base.html`

---

## Phase 3: US1 - Navegação com Uma Mão (P1)

**Goal**: Implementar App Shell com header fixo, área de conteúdo scrollável e bottom navigation com áreas de toque ≥ 48px.

**Independent Test**: Abrir a página em um iPhone 12 Pro (390×844) no DevTools permite tocar em todos os 5 itens da barra inferior com o polegar, sem reajustar a pegada. O conteúdo rola independentemente dos elementos fixos.

- [ ] T008 [US1] Criar `src/templates/base.html` com estrutura mestre (header, main#app-canvas, bottom-nav placeholders)
- [ ] T009 [US1] Criar `src/templates/partials/nav/_header.html` com logo "Autismo em Foco", placeholder de notificações e menu de perfil
- [ ] T010 [US1] Implementar header fixo com `position: fixed`, `h-16` (64px), `z-30`, safe-area-inset-top
- [ ] T011 [P] [US1] Criar `src/templates/partials/nav/_bottom_nav.html` com 5 itens: Início, Rotinas, FAB "+", Guia, Monitor
- [ ] T012 [P] [US1] Garantir área de toque mínima de 48×48px em todos os itens da bottom nav (`min-w-[48px] min-h-[48px]`)
- [ ] T013 [US1] Configurar scroll independente do `#app-canvas` com padding compensatório para header e bottom nav (`pt-16 pb-16`)

---

## Phase 4: US2 - Identidade Visual Calm e Acessível (P1)

**Goal**: Aplicar paleta de cores, tipografia Inter, dark mode funcional e garantir contraste WCAG AA.

**Independent Test**: Executar Lighthouse Accessibility Audit retorna score ≥ 95. Verificar contraste com axe DevTools em todos os estados (claro, escuro, botão ativo/inativo) passa WCAG AA.

- [ ] T014 [US2] Aplicar classes de cor semântica (`bg-primary`, `text-on-surface`, `bg-error`, etc.) nos elementos do App Shell (`base.html`, `_header.html`, `_bottom_nav.html`, `_bottom_sheet.html`)
- [ ] T015 [US2] Configurar tipografia Inter com escala de 4 tamanhos (headline 24px, title 20px, body 16px, caption 12px) e pesos (400, 600, 700)
- [ ] T016 [P] [US2] Implementar dark mode com `darkMode: 'class'` e mapeamento de cores escuras (surface → #0f172a, on-surface → #f8fafc)
- [ ] T017 [P] [US2] Implementar componente Alpine.js `appShell()` para gerenciar tema (light/dark/system) com persistência em LocalStorage (`aef_theme`)
- [ ] T018 [P] [US2] Adicionar toggle de tema no menu de perfil do header (ícone sol/lua)
- [ ] T019 [US2] Garantir transição suave entre temas com `transition-colors duration-200` em todos os elementos interativos

---

## Phase 5: US3 - Criação Rápida de Registros (P2)

**Goal**: Implementar FAB central com bottom sheet de criação rápida (Nova Rotina, Novo Registro).

**Independent Test**: Em qualquer tela, tocar no FAB "+" abre o bottom sheet em menos de 200ms. Tocar fora ou deslizar para baixo fecha o painel. Selecionar "Nova Rotina" navega para `/routines/create/`.

- [ ] T020 [US3] Estilizar FAB central com `shadow-lg`, cor primária, tamanho aumentado (`w-14 h-14`), e posicionamento acima da barra de navegação
- [ ] T021 [US3] Criar `src/templates/partials/nav/_bottom_sheet.html` com overlay e painel deslizante
- [ ] T022 [P] [US3] Implementar componente Alpine.js `bottomSheet()` com estados (open/closed), ações (Nova Rotina, Novo Registro) e navegação
- [ ] T023 [P] [US3] Implementar animações de entrada/saída do bottom sheet (`translate-y-full` → `translate-y-0`, opacity fade)
- [ ] T024 [P] [US3] Implementar fechamento por toque no overlay, swipe para baixo (threshold 80px) e tecla Escape
- [ ] T025 [US3] Implementar handle indicator (barra cinza no topo do painel) para comunicar affordance de arrasto
- [ ] T025b [P] [US3] Implementar atributos ARIA no bottom sheet: `role="dialog"`, `aria-modal="true"`, gerenciamento de foco (foco no primeiro item ao abrir, retorno ao FAB ao fechar), e suporte à tecla Escape

---

## Phase 6: US4 - Orientação Visual de Navegação (P2)

**Goal**: Comunicar visualmente o estado ativo na barra de navegação (ícone sólido/outline + cor primária/cinza) e no header.

**Independent Test**: Navegar para a seção "Rotinas" torna o ícone de rotinas preenchido (solid) e verde-teal, enquanto os demais ficam outline e cinza. Em uma subpágina `/routines/123/`, o ícone "Rotinas" continua ativo.

- [ ] T026 [US4] Implementar estado visual de navegação ativa: ícone `solid` + `text-primary` para item ativo; `outline` + `text-gray-400` para inativos
- [ ] T027 [US4] Configurar `NavigationState` no Alpine.js (`active_section`, `parent_section`) para refletir seção atual
- [ ] T028 [P] [US4] Implementar badge de notificações no header (stub com contador mock, visível apenas quando `count > 0`)
- [ ] T029 [P] [US4] Implementar menu de perfil dropdown no header com links para configurações, assinatura (`href="#"` — stub para feature de pagamentos futura) e toggle de tema
- [ ] T030 [US4] Garantir que subpáginas mantenham o item pai ativo na bottom nav (ex: `/routines/123/` → "Rotinas" ativo)
- [ ] T030b [P] [US4] Implementar dicionário de mapeamento URL→seção no Alpine.js (`/routines/*` → `routines`, `/monitor/*` → `monitor`, etc.) para alimentar `parent_section`

---

## Final Phase: Polish & Cross-Cutting Concerns

**Goal**: Validar acessibilidade, cobrir edge cases e garantir conformidade com a Constitution.

- [ ] T031 [P] Verificar e corrigir edge cases: telas < 360px (labels ocultos), orientação paisagem, teclado virtual, aumento de fonte 200%
- [ ] T032 [P] Executar Lighthouse Accessibility Audit e validar critérios WCAG AA (contraste, áreas de toque, labels ARIA)

---

## Parallel Execution Examples

### Within US1 (Phase 3)
```bash
# T011 e T012 podem ser feitos em paralelo
code src/templates/partials/nav/_bottom_nav.html  # T011
code src/templates/partials/nav/_bottom_nav.html  # T012 (touch targets no mesmo arquivo)
```

### Within US2 (Phase 4)
```bash
# T016, T017, T018 são independentes após T015
# T016: CSS dark mode tokens
# T017: Alpine.js theme component
# T018: Header toggle button
```

### Within US3 (Phase 5)
```bash
# T022, T023, T024 podem ser desenvolvidos em paralelo
# T022: Alpine.js bottomSheet data/actions
# T023: Tailwind transition classes
# T024: Event handlers (click outside, swipe, Escape)
```

---

## Story Completion Order

1. **US1 + US2 (P1) → MVP**: App Shell navegável com design tokens, dark mode e estrutura de layout. Testável por usuários finais.
2. **US3 (P2)**: Adiciona bottom sheet e FAB interativos. Depende de US1 (estrutura do shell) mas não de US2 (tokens já aplicados em US1).
3. **US4 (P2)**: Adiciona estados visuais de navegação e header completo. Depende de US1 e US3.

**Note**: US1 e US2 têm interdependência parcial (US1 cria a estrutura onde US2 aplica os tokens). Recomenda-se desenvolver T008-T013 (US1) antes de T014-T019 (US2), ou em paralelo com coordenação.
