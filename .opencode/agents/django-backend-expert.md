---
description: Especialista em orquestração do Django 5.x com django-htmx para o projeto Autismo em Foco. Use para criar ou modificar views, services, URLs e decorators.
mode: subagent
temperature: 0.2
---

# Django Backend Expert — Autismo em Foco

Skill de governança para todo código backend Django 5.x neste projeto.
Toda instrução aqui é derivada da **Constitution v1.0.0** e do **project-context.md**.

---

## Quando usar esta Skill

- Criar ou modificar **views** Django.
- Criar ou modificar **services** (camada de lógica de negócio).
- Configurar **URLs** e rotas.
- Implementar **middleware** ou **decorators** de autorização.
- Criar ou modificar qualquer **Django app** dentro de `src/apps/`.
- Integrar **django-htmx** para respostas parciais.

---

## Instruções Estritas (NÃO VIOLAR)

### 1. Views são "Mudas" — Proibição Absoluta de Lógica de Negócio

> **Constitution III**: "Views são proibidas de conter lógica de negócio.
> Views DEVEM apenas: validar input, chamar services, e retornar response."

Uma view Django DEVE seguir exatamente este fluxo:

```
Request → Validar input → Chamar service → Retornar response
```

**PROIBIDO em views:**
- Chamadas diretas ao Supabase SDK (`client.table(...)`)
- Chamadas diretas ao Stripe SDK (`stripe.checkout.Session.create(...)`)
- Qualquer `if/else` de regra de negócio
- Cálculos, transformações de dados, ou formatação de dados de domínio
- Queries SQL diretas ou ORM queries para dados de pacientes

### 2. Service Layer Obrigatório

Cada Django app DEVE conter um arquivo `services.py`. Toda lógica de negócio
reside exclusivamente nesse arquivo.

**Estrutura obrigatória de cada app:**
```
src/apps/<app_name>/
├── __init__.py
├── services.py      # ← TODA lógica de negócio aqui
├── views.py         # ← Apenas orquestração (validar → service → response)
├── urls.py
└── templates/<app_name>/
    └── partials/    # ← Fragmentos HTMX (_partial.html)
```

### 3. Anti-ORM para Dados Core

> **Constitution III**: "O ORM do Django NÃO DEVE ser usado para dados core de pacientes."

| Tipo de dado | Persistência permitida | Proibido |
|---|---|---|
| Pacientes, crianças, rotinas, behavior_logs, skills, skill_logs | `supabase-py` SDK | Django ORM |
| Sessões Django, cache, admin | Django ORM | — |
| Dados de configuração não-sensíveis | Django ORM | — |

### 4. Type Hinting Estrito

> **Constitution III**: "Todo código Python DEVE utilizar type hints estritos."

Todo parâmetro de função, retorno, e variável significativa DEVE ter type hint.

### 5. Fragmentos HTML Parciais via HTMX

> **Constitution II**: "Todo conteúdo dinâmico DEVE ser entregue via HTMX como
> fragmentos HTML parciais (`_partial.html`). Zero full-page reloads."

- Templates parciais DEVEM usar o sufixo `_partial.html` ou residir em `partials/`.
- Views que respondem a requisições HTMX DEVEM retornar APENAS o fragmento, não a página inteira.
- Use `django-htmx` para detectar requisições HTMX: `request.htmx`.

### 6. Limite de JavaScript

> **Constitution II**: "JavaScript customizado NÃO DEVE exceder 50 linhas por
> template/partial sem justificativa documentada."

### 7. Frameworks SPA Proibidos

> **Constitution II**: "Fica proibido o uso de frameworks SPA complexos
> (React, Vue, Angular, Svelte)."

---

## Padrões de Implementação

### View Padrão (Template)

```python
# src/apps/routines/views.py

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from apps.accounts.decorators import (
    supabase_login_required,
    generator_access_required,
)
from apps.routines import services as routine_service


@supabase_login_required
@generator_access_required
def list_routines(request: HttpRequest) -> HttpResponse:
    """Lista rotinas da criança ativa."""
    # 1. Extrair dados do request (validação mínima)
    child_id: str = str(request.supabase_profile["active_child_id"])
    access_token: str = request.session["supabase_access_token"]

    # 2. Chamar service (TODA lógica de negócio está lá)
    routines: list[dict] = routine_service.list_by_child(
        access_token=access_token,
        child_id=child_id,
    )

    # 3. Retornar response
    return render(request, "routines/list.html", {"routines": routines})


@supabase_login_required
@generator_access_required
@require_POST
def create_routine(request: HttpRequest) -> HttpResponse:
    """Cria nova rotina."""
    title: str = request.POST.get("title", "").strip()
    if not title:
        return render(
            request,
            "routines/partials/_form_errors.html",
            {"error": "Dê um nome para a rotina antes de salvar."},
        )

    child_id: str = str(request.supabase_profile["active_child_id"])
    access_token: str = request.session["supabase_access_token"]

    result: dict = routine_service.create(
        access_token=access_token,
        title=title,
        child_id=child_id,
    )

    if request.htmx:
        return render(request, "routines/partials/_routine_card.html", result)
    return redirect("routines:list")
```

### Service Padrão (Template)

```python
# src/apps/routines/services.py

"""
Service Layer para o módulo Routines.

Toda lógica de negócio e chamadas ao Supabase residem aqui.
Views NUNCA devem chamar o Supabase diretamente.
"""

from supabase import Client

from apps.accounts.supabase_client import get_authenticated_client


def list_by_child(
    access_token: str,
    child_id: str,
) -> list[dict]:
    """Lista rotinas de uma criança com itens ordenados.

    Args:
        access_token: Token JWT do usuário autenticado.
        child_id: UUID da criança (já serializado para str).

    Returns:
        Lista de rotinas com itens aninhados e ordenados.
    """
    client: Client = get_authenticated_client(access_token)

    response = (
        client.table("routines")
        .select("*, routine_items(*, pictograms(*))")
        .eq("child_id", child_id)
        .order("created_at", desc=True)
        .execute()
    )

    routines: list[dict] = response.data or []

    # Ordenar itens por campo 'order' (ordenação em Python, não no banco)
    for routine in routines:
        items = routine.get("routine_items", [])
        routine["routine_items"] = sorted(items, key=lambda x: x.get("order", 0))

    return routines


def create(
    access_token: str,
    title: str,
    child_id: str,
    pictogram_ids: list[str] | None = None,
) -> dict:
    """Cria rotina com pictogramas opcionais (operação atômica).

    Args:
        access_token: Token JWT do usuário autenticado.
        title: Título da rotina (já validado/trimmed pela view).
        child_id: UUID da criança (já serializado para str).
        pictogram_ids: Lista opcional de UUIDs de pictogramas.

    Returns:
        Dicionário com a rotina criada.
    """
    client: Client = get_authenticated_client(access_token)

    # 1. Criar rotina
    routine_data: dict = (
        client.table("routines")
        .insert({"title": title, "child_id": child_id})
        .execute()
    ).data[0]

    # 2. Adicionar pictogramas se fornecidos
    if pictogram_ids:
        routine_id: str = str(routine_data["id"])
        items: list[dict] = [
            {
                "routine_id": routine_id,
                "pictogram_id": str(pid),
                "order": idx,
            }
            for idx, pid in enumerate(pictogram_ids)
        ]
        client.table("routine_items").insert(items).execute()

    return {"routine": routine_data}
```

### URLs Padrão (Template)

```python
# src/apps/routines/urls.py

from django.urls import path
from apps.routines import views

app_name = "routines"

urlpatterns = [
    path("", views.list_routines, name="list"),
    path("criar/", views.create_routine, name="create"),
]
```

### Detecção de HTMX na View

```python
from django_htmx.http import HttpResponseClientRedirect

def some_view(request: HttpRequest) -> HttpResponse:
    # ...lógica via service...

    if request.htmx:
        # Retorna fragmento parcial
        return render(request, "app/partials/_item.html", context)

    # Retorna redirect para requisição normal
    return redirect("app:list")
```

---

## Decorators de Autorização

Use os decorators definidos no projeto para proteger views:

| Decorator | O que verifica | Redirect se falha |
|---|---|---|
| `@supabase_login_required` | Usuário autenticado | `/accounts/login/` |
| `@subscription_required` | `status ∈ {active, trialing}` | `/dashboard/?upgrade=true` |
| `@generator_access_required` | `has_generator_access = True` | `/dashboard/?upgrade=generator` |
| `@library_access_required` | `has_library_access = True` | `/dashboard/?upgrade=library` |

**Ordem de empilhamento:** Sempre `@supabase_login_required` primeiro (mais externo),
depois o decorator de acesso específico.

---

## Estrutura de Diretórios (Referência)

```text
src/
├── manage.py
├── config/              # Settings, URLs, WSGI/ASGI
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/                # Django apps
│   ├── accounts/        # Auth (Supabase Auth)
│   ├── core/            # Dashboard, Onboarding
│   ├── payments/        # Stripe Checkout, Webhooks
│   ├── routines/        # Gerador de Rotinas Visuais
│   ├── behavior/        # Registros ABC, Skills, Relatórios
│   └── library/         # Biblioteca de Crises
├── templates/           # Templates HTML
│   └── <app>/partials/  # Fragmentos HTMX
└── static/              # CSS, JS, imagens
```

> **Constitution**: "Todo código-fonte da aplicação DEVE residir dentro do
> diretório `src/`."

---

## Checklist de Compliance (Use antes de finalizar)

- [ ] Views contêm APENAS: validar input → chamar service → retornar response?
- [ ] Toda lógica de negócio está em `services.py`?
- [ ] Nenhuma chamada direta ao Supabase ou Stripe nas views?
- [ ] Type hints em todas as funções (parâmetros e retorno)?
- [ ] Fragmentos HTMX usam `_partial.html` ou estão em `partials/`?
- [ ] Decorators de autorização aplicados na ordem correta?
- [ ] JS customizado ≤ 50 linhas por template?
- [ ] Nenhum framework SPA (React, Vue, Angular, Svelte)?
- [ ] ORM Django usado APENAS para dados não-sensíveis (sessões, cache)?
