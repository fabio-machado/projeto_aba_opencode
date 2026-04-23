---
description: Especialista em persistência de dados via SDK Python supabase-py para o projeto Autismo em Foco.
mode: subagent
temperature: 0.1
---

# Supabase Persistence Expert — Autismo em Foco

Skill de governança para toda operação de persistência de dados core neste projeto.
Toda instrução aqui é derivada da **Constitution v1.0.0**, princípios III e IV.

> **CRITICAL**: Esta skill governa o acesso a dados de pacientes menores de idade
> no espectro autista. Violações de segurança (RLS bypass, admin client para queries
> de usuário) são falhas de compliance com LGPD/HIPAA.

---

## Quando usar esta Skill

- Criar ou modificar **queries** ao Supabase (select, insert, update, delete).
- Implementar ou revisar **services.py** que acessam banco de dados.
- Configurar **clients Supabase** (autenticados ou admin).
- Implementar **filtros de isolamento** multi-tenant.
- Serializar **UUIDs** para operações com o SDK.
- Trabalhar com **Supabase Storage** (upload, download, URLs assinadas).
- Implementar **logs de auditoria** em operações de escrita.

---

## Instruções Estritas — CRITICAL (NÃO VIOLAR)

### 1. Anti-ORM: Django ORM PROIBIDO para Dados Core

> **Constitution III**: "O ORM do Django NÃO DEVE ser usado para dados core de pacientes.
> Use exclusivamente o cliente `supabase-py`."

```python
# ❌ PROIBIDO — NÃO usar ORM para dados de pacientes
from apps.models import Child
children = Child.objects.filter(parent_id=user_id)

# ✅ CORRETO — Usar supabase-py
response = client.table("children").select("*").eq("parent_id", user_id).execute()
```

**Exceções permitidas para Django ORM:**
- Sessões Django (`django.contrib.sessions`)
- Cache framework
- Django Admin (se implementado para dados não-sensíveis)

### 2. Client Autenticado OBRIGATÓRIO — Admin Client PROIBIDO

> **Constitution IV / Débito AUTH-01**: "PROIBIDO usar `service_role` / admin client
> para queries de usuário. Usar credenciais autenticadas com RLS ativo."

```python
# ❌ PROIBIDO — Client admin bypassa RLS
from supabase import create_client
client = create_client(url, service_role_key)  # NÃO!

# ✅ CORRETO — Client autenticado com RLS ativo
def get_authenticated_client(access_token: str) -> Client:
    """Cria client Supabase autenticado (RLS ativo).

    NUNCA use service_role para queries de usuário.
    O débito AUTH-01 do projeto anterior NÃO DEVE ser reproduzido.
    """
    from supabase import create_client, ClientOptions
    import os

    client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_ANON_KEY"],
        options=ClientOptions(
            headers={"Authorization": f"Bearer {access_token}"}
        ),
    )
    return client
```

**Única exceção para admin client:** Operações de webhook do Stripe onde não há
sessão de usuário, mas o `supabase_user_id` vem dos metadados do evento.
Neste caso, documente explicitamente o motivo.

### 3. Serialização Obrigatória de UUIDs

> **Constitution IV**: "Todos os UUIDs vindos do frontend ou gerados internamente
> DEVEM ser convertidos para `str(uuid)` antes de qualquer operação no SDK do Supabase."

```python
# ❌ PROIBIDO — UUID object direto no SDK
import uuid
child_uuid = uuid.uuid4()
client.table("children").select("*").eq("parent_id", child_uuid)

# ✅ CORRETO — Serializar para string ANTES da operação
child_id: str = str(request.supabase_profile["id"])
client.table("children").select("*").eq("parent_id", child_id)
```

**Regra**: Sempre converta UUIDs com `str()` na fronteira de entrada (view ou service),
nunca delegue ao SDK.

### 4. Filtro RLS Obrigatório em TODA Query

> **Constitution IV**: "Nenhuma query pode ser disparada sem o filtro explícito
> de `parent_id = auth.uid()` ou validação equivalente no backend Django."

| Tabela | Filtro obrigatório |
|---|---|
| `children` | `.eq("parent_id", user_id)` |
| `routines` | `.eq("child_id", child_id)` — onde child_id pertence ao parent |
| `routine_items` | Via join com routines (cascade) |
| `behavior_logs` | `.eq("child_id", child_id)` |
| `skills` | `.eq("child_id", child_id)` |
| `skill_logs` | Via join com skills (cascade) |
| `exported_reports` | `.eq("child_id", child_id)` |
| `library_contents` | `.eq("is_published", True)` (dados públicos) |
| `pictograms` | `.eq("is_public", True)` (dados públicos) |

### 5. Dupla Validação

> **Constitution IV**: "Inputs DEVEM ser validados tanto no frontend (Alpine.js)
> quanto no backend (Django forms/serializers) antes de alcançar o Supabase."

Mesmo que o frontend valide, o service DEVE validar dados críticos antes de
inserir no Supabase.

### 6. Log de Auditoria em Operações de Escrita

> **Constitution IV**: "Operações de escrita em dados de pacientes DEVEM gerar
> log com `user_id`, `action`, e `timestamp`."

```python
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def create_behavior_log(
    access_token: str,
    child_id: str,
    user_id: str,
    data: dict,
    ) -> dict:
    client = get_authenticated_client(access_token)

    result = client.table("behavior_logs").insert({
        "child_id": child_id,
        **data,
    }).execute()

    # Log de auditoria obrigatório
    logger.info(
        "AUDIT: behavior_log.create | user_id=%s | child_id=%s | timestamp=%s",
        user_id,
        child_id,
        datetime.now(timezone.utc).isoformat(),
    )

    return result.data[0]
```

---

## Padrões de Implementação

### CRUD Padrão (Template de Service)

```python
# src/apps/<app>/services.py

"""
Service Layer para o módulo <App>.

REGRAS:
- Toda operação CRUD usa supabase-py (NUNCA Django ORM para dados core).
- Client SEMPRE autenticado (NUNCA service_role para queries de usuário).
- UUIDs SEMPRE serializados para str() antes de qualquer operação.
- Filtro de isolamento (parent_id/child_id) SEMPRE presente.
- Log de auditoria em TODA operação de escrita.
"""

import logging
from datetime import datetime, timezone

from supabase import Client

from apps.accounts.supabase_client import get_authenticated_client

logger = logging.getLogger(__name__)


# ─── READ ────────────────────────────────────────────────

def list_items(access_token: str, child_id: str) -> list[dict]:
    """Lista itens filtrados por child_id (isolamento RLS)."""
    client: Client = get_authenticated_client(access_token)

    response = (
        client.table("items")
        .select("*")
        .eq("child_id", child_id)        # ← FILTRO RLS OBRIGATÓRIO
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def get_item(access_token: str, item_id: str, child_id: str) -> dict | None:
    """Busca item por ID COM validação de ownership."""
    client: Client = get_authenticated_client(access_token)

    response = (
        client.table("items")
        .select("*")
        .eq("id", item_id)
        .eq("child_id", child_id)         # ← FILTRO RLS OBRIGATÓRIO
        .maybe_single()
        .execute()
    )
    return response.data


# ─── WRITE ───────────────────────────────────────────────

def create_item(
    access_token: str,
    child_id: str,
    user_id: str,
    data: dict,
) -> dict:
    """Cria item com log de auditoria."""
    client: Client = get_authenticated_client(access_token)

    result = (
        client.table("items")
        .insert({"child_id": child_id, **data})
        .execute()
    )

    logger.info(
        "AUDIT: item.create | user_id=%s | child_id=%s | timestamp=%s",
        user_id, child_id, datetime.now(timezone.utc).isoformat(),
    )
    return result.data[0]


def update_item(
    access_token: str,
    item_id: str,
    child_id: str,
    user_id: str,
    data: dict,
) -> dict:
    """Atualiza item com validação de ownership + auditoria."""
    client: Client = get_authenticated_client(access_token)

    result = (
        client.table("items")
        .update(data)
        .eq("id", item_id)
        .eq("child_id", child_id)         # ← FILTRO RLS OBRIGATÓRIO
        .execute()
    )

    logger.info(
        "AUDIT: item.update | user_id=%s | item_id=%s | timestamp=%s",
        user_id, item_id, datetime.now(timezone.utc).isoformat(),
    )
    return result.data[0]


def delete_item(
    access_token: str,
    item_id: str,
    child_id: str,
    user_id: str,
) -> bool:
    """Deleta item com validação de ownership + auditoria."""
    client: Client = get_authenticated_client(access_token)

    client.table("items").delete().eq("id", item_id).eq(
        "child_id", child_id             # ← FILTRO RLS OBRIGATÓRIO
    ).execute()

    logger.info(
        "AUDIT: item.delete | user_id=%s | item_id=%s | timestamp=%s",
        user_id, item_id, datetime.now(timezone.utc).isoformat(),
    )
    return True
```

### Supabase Storage (Upload/Download)

```python
def upload_report_pdf(
    access_token: str,
    child_id: str,
    filename: str,
    pdf_bytes: bytes,
) -> str:
    """Upload de PDF para Supabase Storage com tratamento de erro.

    Returns:
        Path do arquivo no Storage.

    Raises:
        StorageUploadError: Se o upload falhar (NÃO ignorar silenciosamente).
    """
    client: Client = get_authenticated_client(access_token)

    path: str = f"{child_id}/{filename}"

    # NÃO ignorar erros de upload (débito BEH-11a do projeto anterior)
    try:
        client.storage.from_("reports").upload(path, pdf_bytes)
    except Exception as e:
        logger.error("Storage upload failed: %s", e)
        raise StorageUploadError(f"Falha no upload: {path}") from e

    return path


def get_signed_url(
    access_token: str,
    path: str,
    expires_in: int = 3600,
) -> str | None:
    """Gera URL assinada com validade (padrão: 1 hora)."""
    client: Client = get_authenticated_client(access_token)

    try:
        result = client.storage.from_("reports").create_signed_url(path, expires_in)
        return result.get("signedURL")
    except Exception:
        logger.warning("Failed to generate signed URL for: %s", path)
        return None
```

---

## Mapa de Entidades e Tabelas

| Entidade | Tabela Supabase | Ownership |
|---|---|---|
| Responsável (Parent) | `profiles` | `id = auth.uid()` |
| Criança (Child) | `children` | `parent_id → profiles.id` |
| Rotina | `routines` | `child_id → children.id` |
| Item de Rotina | `routine_items` | `routine_id → routines.id` |
| Pictograma | `pictograms` | `is_public = true` (global) |
| Registro ABC | `behavior_logs` | `child_id → children.id` |
| Habilidade | `skills` | `child_id → children.id` |
| Log de Habilidade | `skill_logs` | `skill_id → skills.id` |
| Conteúdo da Biblioteca | `library_contents` | Global (`is_published`) |
| Relatório Exportado | `exported_reports` | `child_id → children.id` |

---

## Débitos do Projeto Anterior — NÃO REPRODUZIR

| ID | Severidade | Descrição | Resolução |
|---|---|---|---|
| AUTH-01 | **CRÍTICA** | `service_role` usado para TODAS as queries | Client autenticado com RLS |
| ACC-MIDW-01 | Alta | Novo client por requisição (sem pool) | Connection pooling/cache |
| ACC-MIDW-02 | Alta | Query `profiles.*` em TODA requisição | Cache de perfil em sessão Django |
| BEH-04a | Média | Data Healing runtime para JSONB corrompido | Validação estrita na escrita |
| BEH-11a | Média | Upload ignora erros silenciosamente | Tratamento de erro obrigatório |

---

## Checklist de Compliance — CRITICAL

- [ ] Nenhum Django ORM para dados core de pacientes?
- [ ] Client Supabase é autenticado (NUNCA service_role para queries de usuário)?
- [ ] Todos os UUIDs convertidos para `str()` antes das operações?
- [ ] Filtro `parent_id`/`child_id` presente em TODA query?
- [ ] Log de auditoria (`user_id`, `action`, `timestamp`) em escritas?
- [ ] Erros de Storage tratados explicitamente (não ignorados)?
- [ ] Dupla validação (frontend + backend) antes de insert/update?
- [ ] Type hints estritos em todas as funções?