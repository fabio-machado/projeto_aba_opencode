# Contract: Routine Builder (Save/Edit)

**Endpoint**: `POST /routines/save/`  
**Auth**: Required (session cookie + middleware)  
**Content-Type**: `application/json`  
**Method**: `fetch()` via Alpine.js (não HTMX — payload JSON)  

## Request

### Create (nova rotina)

```http
POST /routines/save/
Content-Type: application/json
Cookie: supabase_session=<jwt>

{
  "title": "Hora do Banho",
  "pictogram_ids": [
    "550e8400-e29b-41d4-a716-446655440001",
    "550e8400-e29b-41d4-a716-446655440002",
    "550e8400-e29b-41d4-a716-446655440003"
  ]
}
```

### Edit (rotina existente)

```http
POST /routines/save/
Content-Type: application/json
Cookie: supabase_session=<jwt>

{
  "routine_id": "660e8400-e29b-41d4-a716-446655440010",
  "title": "Hora do Banho (atualizado)",
  "pictogram_ids": [
    "550e8400-e29b-41d4-a716-446655440003",
    "550e8400-e29b-41d4-a716-446655440001"
  ]
}
```

### Fields

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `routine_id` | `UUID string` | Edit only | Deve pertencer ao `parent_id` da sessão |
| `title` | `string` | Always | 1-100 chars, trimmed |
| `pictogram_ids` | `UUID[]` | Always | 1-15 UUIDs, ordem = posição na timeline |

## Success Response

### 201 Created / 200 Updated

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "success": true,
  "routine_id": "660e8400-e29b-41d4-a716-446655440010",
  "title": "Hora do Banho",
  "pictogram_count": 3,
  "redirect": "/routines/"
}
```

**Behavior**: O Alpine.js no frontend, ao receber `success: true`, redireciona para `redirect` (mural). Alternativamente, pode usar HTMX `HX-Redirect` header.

## Error Responses

### 400 — Validação

```json
{
  "success": false,
  "error": "validation_error",
  "details": {
    "title": ["Este campo é obrigatório."],
    "pictogram_ids": ["Máximo de 15 pictogramas por rotina."]
  }
}
```

### 401 — Não autenticado

```json
{
  "success": false,
  "error": "unauthorized"
}
```

### 403 — Rotina não pertence ao usuário (edit)

```json
{
  "success": false,
  "error": "forbidden",
  "message": "Rotina não encontrada ou acesso negado."
}
```

### 404 — Rotina não encontrada (edit com ID inexistente)

```json
{
  "success": false,
  "error": "not_found",
  "message": "Rotina não encontrada."
}
```

## Server-Side Logic (Service Layer)

### `routine_service.save_routine(parent_id, title, pictogram_ids, routine_id=None)`

1. Validar `title` (1-100 chars, strip)
2. Validar `pictogram_ids` (lista não-vazia, 1-15 itens, UUIDs válidos)
3. Se `routine_id` fornecido (edit):
   a. Buscar rotina existente filtrando por `parent_id` (RLS check)
   b. Se não encontrada → 403/404
   c. DELETE todos os `routine_items` com `routine_id` (batch delete)
   d. UPDATE `routines` SET `title`, `updated_at`
4. Se `routine_id` não fornecido (create):
   a. INSERT em `routines` (id = `uuid.uuid4()`, parent_id, title)
5. INSERT em massa em `routine_items`:
   - Para cada `(index, pictogram_id)` no array:
     - `order_position = index`
     - `routine_id`, `pictogram_id`
6. Registrar `AuditLogService.log()` com action `routine.created` ou `routine.updated`
7. Retornar `{"success": True, "routine_id": str(routine_id), ...}`

## Validation Matrix

| Condição | Código | Mensagem |
|----------|--------|----------|
| Título vazio ou só espaços | 400 | "O título da rotina é obrigatório." |
| Título > 100 caracteres | 400 | "O título deve ter no máximo 100 caracteres." |
| `pictogram_ids` vazio | 400 | "Adicione ao menos um pictograma à rotina." |
| `pictogram_ids` > 15 itens | 400 | "Máximo de 15 pictogramas por rotina." |
| `pictogram_ids` contém UUID inválido | 400 | "Pictograma inválido." |
| `routine_id` não pertence ao usuário | 403 | "Rotina não encontrada ou acesso negado." |
| Sessão expirada | 401 | (middleware redireciona para /login/) |
