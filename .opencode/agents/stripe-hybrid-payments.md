---
description: Especialista em integração Stripe para o projeto Autismo em Foco, cobrindo Checkout Sessions, Webhooks e Billing Portal.
mode: subagent
temperature: 0.1
---

# Stripe Hybrid Payments Expert — Autismo em Foco

Skill de governança para toda integração com Stripe neste projeto.
Toda instrução é derivada da **Constitution v1.0.0** (Princípio III — Service Layer)
e do **extracted-business-logic.md** (Módulo Payments).

---

## Quando usar esta Skill

- Criar ou modificar **Checkout Sessions** (Stripe).
- Implementar ou modificar **handlers de webhook**.
- Configurar **provisão de acesso** baseada em eventos Stripe.
- Implementar **Order Bumps** no checkout.
- Gerenciar **trials** e transições de status de assinatura.
- Criar integração com **Billing Portal**.
- Sincronizar **flags de acesso** entre Stripe e Supabase.

---

## Modelo de Receita (3 Produtos)

```
Anúncio → Landing Page → Checkout Stripe
                              ├── Low-Ticket: Gerador de Rotinas (pagamento único)
                              ├── Order Bump: Biblioteca de Crises (checkbox no checkout)
                              └── Core SaaS: Monitor de Evolução (assinatura + 7d trial)
```

### Produtos e Configuração

| Produto | Env Var | Tipo | Trial | Flag de Acesso |
|---|---|---|---|---|
| Gerador de Rotinas | `STRIPE_PRICE_GENERATOR` | `payment` (único) | — | `has_generator_access = True` |
| Biblioteca de Crises | `STRIPE_PRICE_LIBRARY` | `payment` (Order Bump) | — | `has_library_access = True` |
| Monitor de Evolução | `STRIPE_PRICE_MONITOR` | `subscription` | 7 dias | `subscription_status` |

### Valores de `subscription_status`

| Valor | Significado | Acesso ao Behavior |
|---|---|---|
| `free` | Sem assinatura | ❌ Bloqueado |
| `trialing` | Em período de teste (7d) | ✅ Liberado |
| `active` | Assinatura ativa | ✅ Liberado |
| `past_due` | Pagamento em atraso | ❌ Bloqueado |
| `canceled` | Assinatura cancelada | ❌ Bloqueado |

---

## Instruções Estritas (NÃO VIOLAR)

### 1. Service Layer Obrigatório — Stripe API isolado em services.py

> **Constitution III**: "Toda lógica de negócio — incluindo integrações com Stripe —
> DEVE residir em `services.py` dentro de cada app."

```python
# ❌ PROIBIDO — Stripe API direto na view
def checkout_create(request):
    session = stripe.checkout.Session.create(...)  # NÃO!

# ✅ CORRETO — Stripe API no service
def checkout_create(request):
    session_url = payment_service.create_checkout_session(
        user_id=..., product=..., bump=...
    )
    return redirect(session_url)
```

### 2. Webhook Handlers Isolados

Todos os handlers de webhook DEVEM residir em um arquivo dedicado:
`src/apps/payments/webhook_handlers.py`

Cada handler é uma função pura que recebe o evento Stripe e executa
a ação correspondente. A view de webhook apenas roteia.

### 3. Webhook como Fonte Única de Provisão

> **Débito PAY-02a**: No projeto anterior, havia race condition entre provisão
> síncrona (success page) e webhook. O webhook DEVE ser a fonte ÚNICA de provisão.

A success page (`/payments/checkout/success/`) DEVE apenas exibir mensagem
de confirmação, NUNCA provisionar acesso diretamente.

### 4. Segurança HMAC Obrigatória

Toda requisição de webhook DEVE ser validada via `stripe.Webhook.construct_event`
com a chave `STRIPE_WEBHOOK_SECRET`.

### 5. Metadados Obrigatórios no Checkout

Todo Checkout Session DEVE incluir nos metadados:
- `supabase_user_id`: UUID do usuário no Supabase
- `product`: tipo do produto (`generator`, `library`, `monitor`)

### 6. Configuração Obrigatória do Checkout

- `allow_promotion_codes = True` (cupons habilitados)
- `locale = 'pt-BR'`
- Order Bump: quando `bump=1`, adicionar Library ao checkout do Generator

---

## Padrões de Implementação

### Estrutura de Arquivos

```
src/apps/payments/
├── __init__.py
├── services.py              # ← Stripe API calls (checkout, portal, customer)
├── webhook_handlers.py      # ← Handlers isolados por evento
├── views.py                 # ← Apenas orquestração (validar → service → response)
├── urls.py
└── templates/payments/
    ├── success.html
    └── partials/
```

### Service de Checkout (Template)

```python
# src/apps/payments/services.py

"""
Service Layer para Stripe Payments.

REGRAS:
- Toda chamada Stripe reside aqui (NUNCA em views).
- Price IDs vêm de variáveis de ambiente (NUNCA hardcoded).
- Metadados obrigatórios: supabase_user_id, product.
- allow_promotion_codes = True, locale = 'pt-BR'.
"""

import os
import logging

import stripe
from supabase import Client

from apps.accounts.supabase_client import get_admin_client

logger = logging.getLogger(__name__)

# Price IDs de variáveis de ambiente
PRICE_GENERATOR: str = os.environ["STRIPE_PRICE_GENERATOR"]
PRICE_LIBRARY: str = os.environ["STRIPE_PRICE_LIBRARY"]
PRICE_MONITOR: str = os.environ["STRIPE_PRICE_MONITOR"]

PRODUCT_PRICE_MAP: dict[str, str] = {
    "generator": PRICE_GENERATOR,
    "library": PRICE_LIBRARY,
    "monitor": PRICE_MONITOR,
}


def ensure_stripe_customer(
    user_id: str,
    email: str,
    name: str,
) -> str:
    """Garante que o usuário tem um stripe_customer_id.

    Se não tem, cria Customer no Stripe e salva no perfil Supabase.

    Returns:
        stripe_customer_id
    """
    # Buscar perfil para checar se já tem customer_id
    admin_client: Client = get_admin_client()
    profile = (
        admin_client.table("profiles")
        .select("stripe_customer_id")
        .eq("id", user_id)
        .single()
        .execute()
    ).data

    if profile.get("stripe_customer_id"):
        return profile["stripe_customer_id"]

    # Criar Customer no Stripe
    customer = stripe.Customer.create(
        email=email,
        name=name,
        metadata={"supabase_user_id": user_id},
    )

    # Salvar no Supabase
    admin_client.table("profiles").update({
        "stripe_customer_id": customer.id,
    }).eq("id", user_id).execute()

    return customer.id


def create_checkout_session(
    user_id: str,
    stripe_customer_id: str,
    product: str,
    bump: bool = False,
    success_url: str = "",
    cancel_url: str = "",
) -> str:
    """Cria Stripe Checkout Session.

    Args:
        user_id: UUID do usuário no Supabase.
        stripe_customer_id: ID do customer no Stripe.
        product: Tipo do produto ('generator', 'library', 'monitor').
        bump: Se True, adiciona Library como Order Bump ao Generator.
        success_url: URL de redirecionamento após sucesso.
        cancel_url: URL de redirecionamento se cancelar.

    Returns:
        URL do Stripe Checkout (para redirect).

    Raises:
        ValueError: Se produto inválido.
    """
    if product not in PRODUCT_PRICE_MAP:
        raise ValueError(f"Produto inválido: {product}")

    price_id: str = PRODUCT_PRICE_MAP[product]

    # Construir line items
    line_items: list[dict] = [{"price": price_id, "quantity": 1}]

    # Order Bump: Generator + Library
    if product == "generator" and bump:
        line_items.append({"price": PRICE_LIBRARY, "quantity": 1})

    # Determinar modo
    mode: str = "subscription" if product == "monitor" else "payment"

    # Construir parâmetros do checkout
    checkout_params: dict = {
        "customer": stripe_customer_id,
        "line_items": line_items,
        "mode": mode,
        "success_url": success_url + "?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": cancel_url,
        "allow_promotion_codes": True,
        "locale": "pt-BR",
        "metadata": {
            "supabase_user_id": user_id,
            "product": product,
        },
    }

    # Trial de 7 dias apenas para Monitor (subscription)
    if mode == "subscription":
        checkout_params["subscription_data"] = {
            "trial_period_days": 7,
            "metadata": {
                "supabase_user_id": user_id,
                "product": product,
            },
        }

    session = stripe.checkout.Session.create(**checkout_params)
    return session.url


def create_billing_portal_session(
    stripe_customer_id: str,
    return_url: str,
) -> str:
    """Cria sessão do Stripe Billing Portal.

    Returns:
        URL do portal (para redirect).
    """
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=return_url,
    )
    return session.url
```

### Webhook Handlers Isolados (Template)

```python
# src/apps/payments/webhook_handlers.py

"""
Handlers de Webhook Stripe — Isolados.

REGRAS:
- Cada handler é uma função pura que recebe o evento e executa a ação.
- Provisão de acesso é feita AQUI (webhook = fonte única de provisão).
- Erros são logados mas retornam 200 (idempotência).
- Atualização de flags no Supabase via admin client (contexto webhook,
  sem sessão de usuário — DOCUMENTAR exceção ao RLS).
"""

import logging
from datetime import datetime, timezone

from supabase import Client

from apps.accounts.supabase_client import get_admin_client

logger = logging.getLogger(__name__)

# Mapeamento Price ID → Flag de acesso
PRICE_TO_FLAG: dict[str, dict] = {}  # Populado em runtime via env vars


def _get_price_flag_map() -> dict[str, dict]:
    """Lazy-load do mapa Price ID → Flag."""
    import os
    return {
        os.environ["STRIPE_PRICE_GENERATOR"]: {"has_generator_access": True},
        os.environ["STRIPE_PRICE_LIBRARY"]: {"has_library_access": True},
        os.environ["STRIPE_PRICE_MONITOR"]: {"subscription_status": "active"},
    }


# ─── HANDLER: checkout.session.completed ─────────────────

def handle_checkout_completed(event: dict) -> None:
    """Provisiona acesso baseado nos line_items do checkout.

    NOTA: Usa admin client porque webhooks não têm sessão de usuário.
    Esta é a ÚNICA exceção documentada ao princípio RLS-First.
    """
    session = event["data"]["object"]
    user_id: str | None = session.get("metadata", {}).get("supabase_user_id")

    if not user_id:
        logger.warning("Webhook checkout.completed sem supabase_user_id: %s", session["id"])
        return

    # Buscar line items do checkout
    import stripe
    line_items = stripe.checkout.Session.list_line_items(session["id"])

    price_map = _get_price_flag_map()
    updates: dict = {}

    for item in line_items.data:
        price_id: str = item.price.id
        if price_id in price_map:
            updates.update(price_map[price_id])

    if not updates:
        logger.warning("Nenhum Price ID reconhecido no checkout: %s", session["id"])
        return

    # Se é subscription (Monitor), setar como trialing (trial de 7 dias)
    import os
    if session.get("mode") == "subscription":
        updates["subscription_status"] = "trialing"
        # trial_ends_at será atualizado pelo evento de invoice

    # Atualizar perfil no Supabase (admin client — exceção RLS documentada)
    admin_client: Client = get_admin_client()
    admin_client.table("profiles").update(updates).eq("id", user_id).execute()

    logger.info(
        "AUDIT: access.provisioned | user_id=%s | flags=%s | session=%s | timestamp=%s",
        user_id, updates, session["id"], datetime.now(timezone.utc).isoformat(),
    )


# ─── HANDLER: invoice.payment_succeeded ──────────────────

def handle_invoice_succeeded(event: dict) -> None:
    """Confirma assinatura ativa após pagamento bem-sucedido."""
    invoice = event["data"]["object"]
    customer_id: str = invoice.get("customer", "")

    if not customer_id:
        return

    admin_client: Client = get_admin_client()
    admin_client.table("profiles").update({
        "subscription_status": "active",
    }).eq("stripe_customer_id", customer_id).execute()

    logger.info(
        "AUDIT: subscription.activated | customer=%s | timestamp=%s",
        customer_id, datetime.now(timezone.utc).isoformat(),
    )


# ─── HANDLER: invoice.payment_failed ─────────────────────

def handle_invoice_failed(event: dict) -> None:
    """Marca assinatura como past_due e dispara e-mail."""
    invoice = event["data"]["object"]
    customer_id: str = invoice.get("customer", "")

    if not customer_id:
        return

    admin_client: Client = get_admin_client()
    admin_client.table("profiles").update({
        "subscription_status": "past_due",
    }).eq("stripe_customer_id", customer_id).execute()

    # Disparar e-mail de pagamento falho
    _send_payment_failed_email(admin_client, customer_id)

    logger.info(
        "AUDIT: subscription.past_due | customer=%s | timestamp=%s",
        customer_id, datetime.now(timezone.utc).isoformat(),
    )


# ─── HANDLER: customer.subscription.deleted ──────────────

def handle_subscription_deleted(event: dict) -> None:
    """Cancela acesso ao módulo Behavior."""
    subscription = event["data"]["object"]
    customer_id: str = subscription.get("customer", "")

    if not customer_id:
        return

    admin_client: Client = get_admin_client()
    admin_client.table("profiles").update({
        "subscription_status": "canceled",
    }).eq("stripe_customer_id", customer_id).execute()

    logger.info(
        "AUDIT: subscription.canceled | customer=%s | timestamp=%s",
        customer_id, datetime.now(timezone.utc).isoformat(),
    )


# ─── HANDLER: customer.subscription.trial_will_end ───────

def handle_trial_will_end(event: dict) -> None:
    """Envia e-mail de aviso de fim de trial."""
    subscription = event["data"]["object"]
    customer_id: str = subscription.get("customer", "")
    trial_end: int | None = subscription.get("trial_end")

    if not customer_id or not trial_end:
        return

    # Calcular dias restantes (timezone-aware)
    from datetime import timezone as tz
    now = datetime.now(tz.utc).timestamp()
    days_left: int = max(0, int((trial_end - now) / 86400))

    _send_trial_ending_email(customer_id, days_left)

    logger.info(
        "AUDIT: trial.warning_sent | customer=%s | days_left=%d | timestamp=%s",
        customer_id, days_left, datetime.now(timezone.utc).isoformat(),
    )


# ─── HELPERS (privados) ──────────────────────────────────

def _send_payment_failed_email(admin_client: Client, customer_id: str) -> None:
    """Envia e-mail de pagamento falho. Não-crítico (falha silenciosamente)."""
    try:
        from apps.core.email_service import send_payment_failed_email
        # Buscar e-mail do usuário via perfil
        profile = (
            admin_client.table("profiles")
            .select("id")
            .eq("stripe_customer_id", customer_id)
            .maybe_single()
            .execute()
        ).data
        if profile:
            send_payment_failed_email(user_id=profile["id"])
    except Exception as e:
        logger.warning("Falha ao enviar e-mail payment_failed: %s", e)


def _send_trial_ending_email(customer_id: str, days_left: int) -> None:
    """Envia e-mail de aviso de trial. Não-crítico."""
    try:
        from apps.core.email_service import send_trial_ending_email
        send_trial_ending_email(customer_id=customer_id, days_left=days_left)
    except Exception as e:
        logger.warning("Falha ao enviar e-mail trial_ending: %s", e)
```

### View de Webhook (Roteador)

```python
# src/apps/payments/views.py (trecho do webhook)

import stripe
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.payments.webhook_handlers import (
    handle_checkout_completed,
    handle_invoice_succeeded,
    handle_invoice_failed,
    handle_subscription_deleted,
    handle_trial_will_end,
)

# Mapa de eventos → handlers
WEBHOOK_HANDLERS: dict[str, callable] = {
    "checkout.session.completed": handle_checkout_completed,
    "invoice.payment_succeeded": handle_invoice_succeeded,
    "invoice.payment_failed": handle_invoice_failed,
    "customer.subscription.deleted": handle_subscription_deleted,
    "customer.subscription.trial_will_end": handle_trial_will_end,
}


@csrf_exempt
@require_POST
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    """Roteador de webhooks Stripe.

    A view APENAS:
    1. Valida HMAC
    2. Roteia para o handler correto
    3. Retorna 200
    """
    payload: bytes = request.body
    sig_header: str = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            os.environ["STRIPE_WEBHOOK_SECRET"],
        )
    except ValueError:
        return HttpResponse("Invalid payload", status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse("Invalid signature", status=400)

    # Rotear para handler
    handler = WEBHOOK_HANDLERS.get(event["type"])
    if handler:
        try:
            handler(event)
        except Exception as e:
            # Log de erro mas retorna 200 (idempotência)
            logger.error(
                "Webhook handler error: type=%s error=%s",
                event["type"], e,
            )

    return HttpResponse(status=200)
```

---

## Exceção RLS Documentada — Webhooks

> **IMPORTANTE**: Webhook handlers usam **admin client** (service_role) porque
> não há sessão de usuário no contexto de webhook. Esta é a ÚNICA exceção
> ao princípio RLS-First (Constitution IV), e é justificada por:
>
> 1. Webhooks são server-to-server (Stripe → Django).
> 2. A autenticação é feita via HMAC (chave secreta), não via sessão.
> 3. O `supabase_user_id` nos metadados garante que a atualização é scoped.
>
> Toda outra operação de leitura/escrita DEVE usar client autenticado.

---

## Débitos do Projeto Anterior — NÃO REPRODUZIR

| ID | Severidade | Descrição | Resolução |
|---|---|---|---|
| PAY-02a | Alta | Race condition: provisão síncrona vs webhook | Webhook = fonte ÚNICA de provisão |
| PAY-03a | Baixa | `days_left` timezone-unaware (`time.time()`) | Usar `datetime.now(timezone.utc)` |

---

## Checklist de Compliance

- [ ] Toda chamada Stripe está em `services.py` (nunca em views)?
- [ ] Webhook handlers isolados em `webhook_handlers.py`?
- [ ] Validação HMAC via `stripe.Webhook.construct_event`?
- [ ] Success page NÃO provisiona acesso (apenas webhook)?
- [ ] Metadados incluem `supabase_user_id` e `product`?
- [ ] `allow_promotion_codes = True` e `locale = 'pt-BR'`?
- [ ] Order Bump funciona (`bump=1` adiciona Library ao Generator)?
- [ ] Trial de 7 dias configurado para Monitor?
- [ ] Flags de acesso sincronizadas corretamente no Supabase?
- [ ] Erros em handlers logados mas retornam 200 (idempotência)?
- [ ] Price IDs vêm de variáveis de ambiente (nunca hardcoded)?
- [ ] Cálculos de tempo são timezone-aware (`datetime.now(timezone.utc)`)?
- [ ] Log de auditoria em toda provisão/alteração de acesso?