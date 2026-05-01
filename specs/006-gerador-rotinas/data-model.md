# Data Model: Gerador de Rotinas

**Feature**: 006-gerador-rotinas  
**Date**: 2026-04-29

## Entity-Relationship Diagram

```
┌──────────────────────┐       ┌──────────────────────┐
│  pictogram_categories│       │     pictograms        │
├──────────────────────┤       ├──────────────────────┤
│ PK id: UUID          │◄──────│ FK category_id: UUID  │
│    name: TEXT         │  1:N  │ PK id: UUID           │
│    display_order: INT │       │    name: TEXT          │
└──────────────────────┘       │    image_url: TEXT     │
                               └──────────┬───────────┘
                                          │
                                          │ 1:N
                                          ▼
┌──────────────────────┐       ┌──────────────────────┐
│      routines         │       │    routine_items      │
├──────────────────────┤       ├──────────────────────┤
│ PK id: UUID           │◄──────│ FK routine_id: UUID   │
│    parent_id: UUID    │  1:N  │ FK pictogram_id: UUID │
│    title: VARCHAR(100)│       │ PK id: UUID           │
│    created_at: TZ     │       │    order_position: INT │
│    updated_at: TZ     │       └──────────────────────┘
└──────────────────────┘
```

## Tables

### 1. `pictogram_categories`

Categorias temáticas que agrupam pictogramas na gaveta do construtor.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | PK, DEFAULT `uuid_generate_v4()` | Identificador único |
| `name` | `TEXT` | NOT NULL | Nome da categoria (ex: "Higiene") |
| `display_order` | `INTEGER` | NOT NULL, DEFAULT 0 | Ordem de exibição das abas no builder |

**RLS Policy**: SELECT público. INSERT/UPDATE/DELETE somente service_role.

**Seed Data**: Higiene (1), Alimentação (2), Escola (3), Lazer (4), Terapia (5), Sono (6), Outros (7).

---

### 2. `pictograms`

Pictogramas individuais (imagens SVG/PNG) que representam atividades.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | PK, DEFAULT `uuid_generate_v4()` | Identificador único |
| `category_id` | `UUID` | FK → `pictogram_categories.id`, NOT NULL | Categoria do pictograma |
| `name` | `TEXT` | NOT NULL | Nome da atividade (ex: "Escovar os dentes") |
| `image_url` | `TEXT` | NOT NULL | URL pública da imagem no Supabase Storage |

**RLS Policy**: SELECT público. INSERT/UPDATE/DELETE somente service_role.

**Notes**: Imagens hospedadas no bucket `pictograms` do Supabase Storage. URLs com padrão: `/storage/v1/object/public/pictograms/<category>/<name>.svg`.

---

### 3. `routines`

Rotinas visuais criadas pelo cuidador. Isoladas por `parent_id` via RLS.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | PK, DEFAULT `uuid_generate_v4()` | Identificador único da rotina |
| `parent_id` | `UUID` | NOT NULL | Cuidador proprietário (FK → `profiles.id`) |
| `title` | `VARCHAR(100)` | NOT NULL | Título exibido no card e PDF (máx. 100 chars) |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `NOW()` | Data de criação |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `NOW()` | Data da última modificação |

**RLS Policy**: 
- SELECT: `parent_id = auth.uid()`
- INSERT: `parent_id = auth.uid()`
- UPDATE: `parent_id = auth.uid()`
- DELETE: `parent_id = auth.uid()`

**Validation Rules** (service layer):
- `title`: 1-100 caracteres, obrigatório
- `parent_id`: UUID válido, deve corresponder ao usuário da sessão

**Index**: `idx_routines_parent_id` ON `routines(parent_id)` para queries rápidas do mural.

---

### 4. `routine_items`

Itens (pictogramas) que compõem uma rotina, com ordenação explícita.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | PK, DEFAULT `uuid_generate_v4()` | Identificador único do item |
| `routine_id` | `UUID` | FK → `routines.id` ON DELETE CASCADE, NOT NULL | Rotina a que pertence |
| `pictogram_id` | `UUID` | FK → `pictograms.id`, NOT NULL | Pictograma associado |
| `order_position` | `INTEGER` | NOT NULL, CHECK ≥ 0 | Posição ordinal (0-based) na timeline |

**RLS Policy**:
- SELECT: `EXISTS (SELECT 1 FROM routines WHERE routines.id = routine_items.routine_id AND routines.parent_id = auth.uid())`
- INSERT: mesmo critério de SELECT + `auth.uid()` é o `parent_id` da rotina alvo
- UPDATE: mesmo critério de SELECT
- DELETE: mesmo critério de SELECT

**Validation Rules** (service layer):
- `order_position`: inteiro sequencial sem gaps (0, 1, 2, ...)
- Máximo 15 itens por rotina (FR-018)
- Permitir pictogramas duplicados na mesma rotina

**Index**: `idx_routine_items_routine` ON `routine_items(routine_id, order_position)` para queries ordenadas.

---

## State Transitions

### Routine Lifecycle

```
                    ┌──────────┐
         create     │          │    save/edit
   ───────────────► │  ACTIVE   │ ◄──────────────
                    │          │
                    └────┬─────┘
                         │
                         │ delete (hard)
                         ▼
                    ┌──────────┐
                    │ DELETED  │  (removido do banco)
                    └──────────┘
```

- **ACTIVE**: Rotina visível no mural, editável. Estado padrão após criação.
- **DELETED**: Hard delete (sem soft delete nesta versão, conforme assumptions). Itens são removidos em cascata (`ON DELETE CASCADE`).

### Builder State (Alpine.js — client-side apenas)

```
┌──────────┐    add pictogram      ┌──────────┐
│  CLEAN    │ ──────────────────►  │  DIRTY    │
│ (salvo)  │ ◄──────────────────  │ (não salvo)│
└──────────┘    save success       └──────────┘
     │                                   │
     │  navigate away                    │  navigate away
     ▼                                   ▼
  (sem prompt)                    (prompt: "Alterações não salvas")
```

- `isDirty = true` quando title ou items[] diferem do estado original carregado
- LocalStorage é atualizado a cada mudança no array de items (FR-017)

---

## Data Volume Assumptions

| Entidade | Volume estimado por cuidador | Total esperado (MVP) |
|----------|------------------------------|----------------------|
| `pictograms` | Catálogo fixo (~70-100 pictogramas) | ~100 registros |
| `pictogram_categories` | Fixo | 7 registros |
| `routines` | 5-30 por cuidador | ~500 registros (50 cuidadores) |
| `routine_items` | 1-15 por rotina | ~3750 registros |

---

## Integrity Constraints Summary

| Constraint | Type | Enforcement |
|-----------|------|-------------|
| Rotina com 0 itens não pode ser salva | Lógica | Service layer (FR-004) |
| Máximo 15 itens por rotina | Lógica | Service layer + frontend Alpine (FR-018) |
| `order_position` sequencial sem gaps | Lógica | Service layer (batch insert) |
| `parent_id` deve ser o usuário da sessão | Segurança | RLS + service layer (FR-016) |
| Título 1-100 caracteres | Validação | Service layer + frontend Alpine |
| `routine_id` FK com CASCADE | Integridade | PostgreSQL FK constraint |
| `category_id` FK | Integridade | PostgreSQL FK constraint |
