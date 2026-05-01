# Quickstart: Gerador de Rotinas

**Feature**: 006-gerador-rotinas  
**Date**: 2026-04-29

## Pré-requisitos

- Docker em execução (`docker compose up -d`)
- Variáveis de ambiente configuradas (`.env` com `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, `SUPABASE_ANON_KEY`)
- Ambiente virtual Python ativado (`source .venv/bin/activate`)
- Node.js (apenas para lint/format, se configurado)

## 1. Criar Tabelas no Supabase

Aplicar as migrations que criam as tabelas do módulo de rotinas.

```bash
# A partir da raiz do projeto
python manage.py migrate_routines_schema
```

Ou, se usar Supabase CLI local:

```bash
supabase db push
```

### Verificar tabelas criadas

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('routines', 'routine_items', 'pictograms', 'pictogram_categories');
```

## 2. Popular Pictogramas (Seed)

```bash
python manage.py seed_pictograms
```

Isso insere as 7 categorias e pictogramas de exemplo no Supabase.

### Verificar seed

```sql
SELECT c.name AS category, COUNT(p.id) AS pictogram_count
FROM pictogram_categories c
LEFT JOIN pictograms p ON p.category_id = c.id
GROUP BY c.name
ORDER BY c.display_order;
```

## 3. Rodar o Servidor

```bash
python manage.py runserver
```

Acessar: `http://localhost:8000/routines/`

## 4. Fluxo de Desenvolvimento

### Estrutura de Arquivos

```text
src/apps/routines/
├── services.py          # Lógica de negócio (CRUD Supabase, batch edit, PDF)
├── views.py             # Endpoints HTTP
├── urls.py              # Rotas do app
└── templates/routines/
    ├── routine_list.html          # Mural (cards + empty state + FAB)
    ├── routine_builder.html       # Construtor (timeline + gaveta + drag-drop)
    └── partials/
        ├── _routine_card.html     # Card individual (HTMX para rename/delete)
        ├── _empty_state.html      # Estado vazio acolhedor
        ├── _timeline_item.html    # Item da timeline
        └── _pictogram_grid.html   # Grade de pictogramas da gaveta

src/static/js/
├── routine-builder.js    # Alpine.js: estado do builder, SortableJS, LocalStorage
```

### Ordem de Implementação Sugerida

1. **Migrations** — Criar 4 tabelas no Supabase + seed data
2. **`routine_service.py`** — CRUD via supabase-py (anti-ORM)
3. **`views.py`** — Endpoints: list, builder (GET), save (POST), rename (PATCH), delete (DELETE), export (GET)
4. **Templates** — `routine_list.html` (mural) → `routine_builder.html` (construtor)
5. **JavaScript** — `routine-builder.js` (Alpine.js + SortableJS + LocalStorage)
6. **PDF** — `generate_routine_pdf()` no service + endpoint de export

### Testar Localmente

```bash
# Rodar testes do módulo
pytest src/apps/routines/tests/ -v

# Rodar todos os testes
pytest -v
```

## 5. Variáveis de Ambiente Adicionais

Nenhuma nova variável necessária além das já existentes para Supabase.

## 6. Dependências Novas

Adicionar ao `requirements.txt`:

```
reportlab>=4.0,<5.0
```

Adicionar ao `base.html` (CDN):

```html
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"></script>
```
