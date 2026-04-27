# Data Model: App Shell e Identidade Visual

**Feature**: 002-app-shell-identidade-visual  
**Date**: 2026-04-24  
**Purpose**: Definir entidades, atributos e relacionamentos para o estado de UI, tema e navegação.

---

## Entity: UserThemePreference

**Description**: Preferência de tema (claro/escuro/sistema) do usuário, persistida no LocalStorage do navegador. Não é uma entidade de banco de dados, mas sim um objeto JSON no LocalStorage.

**Attributes**:
| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `mode` | `str` | `light`, `dark`, `system` | Modo de tema selecionado pelo usuário |
| `updated_at` | `str` | ISO 8601 | Timestamp da última alteração |

**Validation Rules**:
- `mode` deve ser um dos três valores permitidos
- Se `mode` for `system`, a aplicação deve detectar `prefers-color-scheme` do SO
- Fallback automático para `system` quando não houver registro no LocalStorage

**Lifecycle**:
```
first_access → detect_system_preference → apply_theme
  → user_changes_theme → save_to_localStorage → apply_theme
```

---

## Entity: NavigationState

**Description**: Estado atual da navegação da aplicação, determinando qual seção está ativa e refletido visualmente na barra inferior.

**Attributes**:
| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `active_section` | `str` | `home`, `routines`, `guide`, `monitor` | Seção atualmente ativa |
| `parent_section` | `str` | nullable | Seção pai quando em subpágina (ex: `routines` ao visualizar detalhe de rotina) |
| `bottom_sheet_open` | `bool` | default `false` | Indica se o bottom sheet de criação rápida está aberto |

**Validation Rules**:
- `active_section` deve corresponder a uma das 4 seções principais (excluindo o FAB)
- `parent_section` é usado para manter o indicador ativo em subpáginas

---

## Entity: AppShellLayout

**Description**: Configuração estrutural do App Shell, definindo dimensões e comportamentos fixos do layout.

**Attributes**:
| Attribute | Type | Value | Description |
|-----------|------|-------|-------------|
| `header_height` | `int` | 64 | Altura fixa do header em pixels (mobile) |
| `bottom_nav_height` | `int` | 64 | Altura fixa da barra de navegação inferior em pixels |
| `safe_area_top` | `int` | env-dependent | Padding para notch/status bar (usar `env(safe-area-inset-top)`) |
| `safe_area_bottom` | `int` | env-dependent | Padding para home indicator (usar `env(safe-area-inset-bottom)`) |
| `touch_target_min` | `int` | 48 | Dimensão mínima de toque em pixels (WCAG) |

**Validation Rules**:
- `header_height` + `bottom_nav_height` devem deixar pelo menos 60% da viewport para conteúdo em telas de 360px
- `touch_target_min` é imutável (regra da Constitution)

---

## Entity: DesignTokenRegistry

**Description**: Registro centralizado de todos os design tokens semânticos. Representado como um objeto JavaScript no frontend (configuração Tailwind) e referenciado nos templates Django.

**Attributes**:
| Token | Type | Light Value | Dark Value | Description |
|-------|------|-------------|------------|-------------|
| `color-primary` | `hex` | #14b8a6 | #2dd4bf | Cor primária (teal) |
| `color-primary-variant` | `hex` | #0d9488 | #14b8a6 | Variante da primária |
| `color-surface` | `hex` | #f8fafc | #0f172a | Fundo principal |
| `color-surface-variant` | `hex` | #f1f5f9 | #1e293b | Fundo secundário |
| `color-on-surface` | `hex` | #0f172a | #f8fafc | Texto sobre surface |
| `color-error` | `hex` | #ef4444 | #f87171 | Cor de erro |
| `typography-headline` | `str` | Inter 24px/700 | Inter 24px/700 | Títulos principais |
| `typography-title` | `str` | Inter 20px/600 | Inter 20px/600 | Subtítulos |
| `typography-body` | `str` | Inter 16px/400 | Inter 16px/400 | Texto corpo |
| `typography-caption` | `str` | Inter 12px/400 | Inter 12px/400 | Legendas |
| `spacing-base` | `int` | 4px | 4px | Grid base |
| `border-radius-button` | `int` | 12px | 12px | Botões (rounded-xl) |
| `border-radius-card` | `int` | 16px | 16px | Cards (rounded-2xl) |
| `border-radius-input` | `int` | 8px | 8px | Inputs (rounded-lg) |
| `shadow-sm` | `str` | Tailwind value | Tailwind value | Sombra sutil |
| `shadow-md` | `str` | Tailwind value | Tailwind value | Sombra padrão |
| `shadow-lg` | `str` | Tailwind value | Tailwind value | Sombra elevada (FAB) |

---

## Entity: BottomSheetAction

**Description**: Ações disponíveis no bottom sheet de criação rápida. Definidas como um array de objetos no frontend (Alpine.js data).

**Attributes**:
| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | `str` | unique | Identificador da ação |
| `label` | `str` | max 30 chars | Texto exibido (ex: "Nova Rotina") |
| `icon` | `str` | Heroicon name | Nome do ícone Heroicon (outline) |
| `href` | `str` | URL path | Destino ao clicar (ex: `/routines/create/`) |
| `priority` | `int` | 1-3 | Ordem de exibição no bottom sheet |

**Current Actions**:
| ID | Label | Icon | Href | Priority |
|----|-------|------|------|----------|
| `new-routine` | Nova Rotina | `clipboard-document-list` | `/routines/create/` | 1 |
| `new-record` | Novo Registro | `pencil-square` | `/records/create/` | 2 |

**Validation Rules**:
- Máximo de 3 ações simultâneas (para não sobrecarregar o bottom sheet)
- `label` deve ser acionável (verbo + substantivo)
- `href` pode ser nulo se a ação requerer JavaScript customizado

---

## Entity: NotificationBadge

**Description**: Estado do indicador de notificações no header. Inicialmente um stub/mock; futuramente integrado com backend de notificações.

**Attributes**:
| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `count` | `int` | ≥ 0 | Número de notificações não lidas |
| `visible` | `bool` | default `false` | Badge só visível quando `count > 0` |
| `last_updated` | `str` | ISO 8601 | Timestamp da última atualização |

**Validation Rules**:
- `visible` é derivado: `visible = count > 0`
- `count` deve ser atualizado via HTMX swap (não full page reload)

---

## Relationships

```
[UserThemePreference] --(persisted_in)--> [LocalStorage]
  │
  └──(applied_to)--> [AppShellLayout] --(renders)--> [base.html]

[NavigationState] --(reflects)--> [BottomNav] --(contains)--> [BottomSheetAction]
  │
  └──(indicates)--> [active_section]

[DesignTokenRegistry] --(configures)--> [TailwindConfig] --(styles)--> [AppShellLayout]

[NotificationBadge] --(displayed_in)--> [Header]
```

## Notas de Implementação

1. **LocalStorage**: Todas as preferências de UI (tema, bottom sheet estado) usam LocalStorage. A chave deve ser prefixada para evitar conflitos: `aef_theme`, `aef_nav_state`.
2. **SSR + Dark Mode**: Como o dark mode é aplicado via classe no `<html>`, pode ocorrer "flash de tema errado" (FART — Flash of Accurate Theme). Mitigar com script inline no `<head>` que lê LocalStorage antes de qualquer renderização.
3. **Touch Targets**: Todos os botões da barra de navegação devem ter `min-w-[48px] min-h-[48px]` mesmo que o ícone visual seja menor (24px).
4. **Bottom Sheet Z-Index**: O overlay do bottom sheet deve ter `z-index` superior ao header e à barra de navegação para garantir foco total.
