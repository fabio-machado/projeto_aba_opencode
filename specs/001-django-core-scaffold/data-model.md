# Data Model: Django Core Scaffold

**Feature**: 001-django-core-scaffold  
**Date**: 2026-04-23  
**Purpose**: Definir entidades, atributos e relacionamentos para o esqueleto base.

---

## Entity: ProjectConfig

**Description**: Configurações centralizadas do projeto Django. Não é uma entidade persistente em banco de dados, mas sim um conjunto de variáveis de ambiente e settings.

**Attributes**:
| Attribute | Type | Source | Description |
|-----------|------|--------|-------------|
| `DJANGO_SETTINGS_MODULE` | `str` | Environment | `config.settings.dev` ou `config.settings.prd` |
| `SECRET_KEY` | `str` | Environment | Chave secreta do Django (diferente por ambiente) |
| `DEBUG` | `bool` | Environment | `True` em dev, `False` em prd |
| `SUPABASE_URL` | `str` | Environment | URL do projeto Supabase |
| `SUPABASE_KEY` | `str` | Environment | Service Role Key do Supabase |
| `STRIPE_SECRET_KEY` | `str` | Environment | Chave secreta da API Stripe |
| `STRIPE_PUBLISHABLE_KEY` | `str` | Environment | Chave pública da API Stripe |
| `LOG_LEVEL` | `str` | Environment | `DEBUG` (dev) ou `INFO` (prd) |

**Validation Rules**:
- Todas as variáveis são obrigatórias em PRD
- Em DEV, `SUPABASE_URL` e `SUPABASE_KEY` podem ser mockadas para desenvolvimento offline
- `SECRET_KEY` deve ter mínimo 50 caracteres em PRD

---

## Entity: AuditLog

**Description**: Registro de auditoria para todas as operações de escrita em dados de pacientes. Persistido no Supabase (PostgreSQL).

**Attributes**:
| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | `UUID` | PK, auto-generated | Identificador único do log |
| `user_id` | `UUID` | NOT NULL | ID do usuário que executou a ação |
| `action` | `str` | NOT NULL, max 50 chars | Tipo da ação: `CREATE`, `UPDATE`, `DELETE`, `SYNC` |
| `table_name` | `str` | NOT NULL, max 100 chars | Nome da tabela afetada |
| `record_id` | `UUID` | nullable | ID do registro afetado |
| `timestamp` | `datetime` | NOT NULL, default now() | Momento da ação |
| `payload` | `JSONB` | nullable | Dados relevantes da operação (snapshot ou delta) |

**Validation Rules**:
- `user_id` deve corresponder a um `auth.uid()` válido
- `action` deve ser um dos valores permitidos
- `timestamp` é gerado automaticamente pelo banco

**RLS Policy**:
```sql
CREATE POLICY audit_log_select ON audit_log
  FOR SELECT USING (user_id = auth.uid());
```

---

## Entity: OfflineQueue

**Description**: Fila local de sincronização para ações realizadas offline. Persistido no LocalStorage do navegador (não no servidor).

**Attributes**:
| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `queue_id` | `str` | UUID v4 como string | Identificador único da ação enfileirada |
| `action` | `str` | NOT NULL | `CREATE`, `UPDATE`, `DELETE` |
| `table_name` | `str` | NOT NULL | Nome da tabela alvo no Supabase |
| `payload` | `JSON` | NOT NULL | Dados da operação |
| `created_at` | `str` | ISO 8601 | Timestamp de criação local |
| `sync_status` | `str` | `pending`, `syncing`, `failed` | Estado atual da sincronização |
| `retry_count` | `int` | default 0 | Número de tentativas de sync |

**Validation Rules**:
- `payload` deve conter `parent_id` para RLS
- `created_at` usado como critério de last-write-wins em conflitos
- Máximo de 3 retries antes de marcar como `failed`

**Lifecycle**:
```
offline_action → localStorage (pending)
  → online_detected → sync_to_supabase (syncing)
    → success → remove_from_queue
    → failure → retry (max 3) → failed (logged)
```

---

## Entity: CoreExample (App de Referência)

**Description**: Entidade de exemplo no app `core` para demonstrar o padrão Service Layer + HTMX. Não é uma entidade de negócio real, mas serve como template.

**Attributes**:
| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | `UUID` | PK | Identificador único |
| `title` | `str` | max 200 chars | Título de exemplo |
| `status` | `str` | `active`, `inactive` | Status demonstrando Toggle Button |
| `created_at` | `datetime` | auto | Timestamp de criação |

**Validation Rules**:
- `title` obrigatório, mínimo 3 caracteres
- `status` usa Toggle Button (não `<select>`) conforme Constitution

---

## Relationships

```
[User] --(auth.uid())--> [AuditLog]
  │
  ├──(parent_id)--> [PatientData] (Supabase tables, não definidas no scaffold)
  │
  └──(offline_actions)--> [OfflineQueue] (LocalStorage)

[ProjectConfig] --(settings)--> [DjangoApp]
  │
  ├──(SUPABASE_URL/K)--> [SupabaseService]
  └──(STRIPE_SECRET_KEY)--> [StripeService]
```

## State Transitions

### OfflineQueue Sync Status

```
         +-----------+
         |  pending  |
         +-----+-----+
               |
         online detected
               |
               v
         +-----------+
         |  syncing  |
         +-----+-----+
               |
      +--------+--------+
      |                 |
   success           failure
      |                 |
      v                 v
+-----------+     +-----------+
|  removed  |     |  failed   |
+-----------+     +-----+-----+
                        |
                   retry < 3?
                        |
              +---------+---------+
              |                   |
             yes                 no
              |                   |
              v                   v
        +-----------+       +-----------+
        |  syncing  |       |  failed   |
        | (retry++) |       | (permanent)
        +-----------+       +-----------+
```

## Notas de Implementação

1. **Anti-ORM**: As entidades `AuditLog` e futuras entidades de paciente NÃO devem ter `models.py` Django. Usar `supabase-py` para CRUD.
2. **UUID Serialization**: Todo UUID deve ser convertido para `str(uuid)` antes de passar para o SDK Supabase.
3. **Type Hints**: Todo service deve declarar tipos de entrada e saída explicitamente.
4. **RLS**: Todo acesso a dados de pacientes deve incluir filtro `parent_id = auth.uid()`.
