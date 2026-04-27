import logging
import time

from django.conf import settings
from django.http import HttpRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from apps.payments import services as payment_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# T020 — Magic link callback view
# ---------------------------------------------------------------------------

@require_GET
def auth_callback(request: HttpRequest) -> HttpResponseRedirect:
    """Processa o callback do magic link após o usuário clicar no e-mail.

    Fluxo:
        1. Extrair query parameters (access_token, refresh_token, type).
        2. Delegar validação ao service layer.
        3. Se válido: setar cookie HTTP-only com access token e redirecionar
           para /dashboard.
        4. Se inválido: redirecionar para /login com erro.
    """
    # 1. Extrair input do request
    access_token: str = request.GET.get("access_token", "").strip()
    refresh_token: str = request.GET.get("refresh_token", "").strip()
    token_type: str = request.GET.get("type", "").strip()

    logger.info(
        "Auth callback received",
        extra={
            "has_access_token": bool(access_token),
            "has_refresh_token": bool(refresh_token),
            "token_type": token_type,
        },
    )

    # 2. Delegar validação ao service
    result: dict | None = payment_service.validate_magic_link_callback(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type=token_type,
    )

    if result is None:
        logger.warning("Magic link callback validation failed")
        return redirect("/login?error=invalid_magic_link")

    # 3. Setar cookie HTTP-only com access token
    user_id: str = result["user_id"]
    response: HttpResponseRedirect = redirect("/dashboard")

    session_cookie_name: str = getattr(
        settings, "SUPABASE_SESSION_COOKIE", "supabase_session"
    )

    response.set_cookie(
        key=session_cookie_name,
        value=access_token,
        max_age=90 * 24 * 60 * 60,  # 90 dias em segundos
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path="/",
    )

    # Também armazenar no Django session para acesso via request.session
    request.session["supabase_access_token"] = access_token
    request.session["supabase_user_id"] = user_id
    request.session.save()

    logger.info(
        "Magic link authentication successful — session created",
        extra={"user_id": user_id},
    )

    return response


@csrf_exempt
@require_POST
def stripe_webhook(request: HttpRequest) -> JsonResponse:
    """Recebe e processa webhooks do Stripe.

    Fluxo:
        1. Ler raw body do request.
        2. Extrair header Stripe-Signature.
        3. Validar assinatura via service layer.
        4. Filtrar eventos payment_intent.succeeded.
        5. Para payment_intent.succeeded: criar conta do usuário via service.
        6. Retornar resposta apropriada conforme contrato.
    """
    # T025b — Response time tracking (SC-001: < 3s)
    start_time: float = time.time()

    # 1. Validar input — raw body
    payload: bytes = request.body

    # 2. Extrair header de assinatura
    sig_header: str = request.headers.get("Stripe-Signature", "")
    if not sig_header:
        logger.warning("Webhook received without Stripe-Signature header")
        return JsonResponse(
            {"status": "error", "message": "Invalid webhook signature"},
            status=400,
        )

    # 3. Chamar service para validar assinatura
    webhook_secret: str = settings.STRIPE_WEBHOOK_SECRET
    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        return JsonResponse(
            {"status": "error", "message": "Server configuration error"},
            status=500,
        )

    try:
        event: dict = payment_service.validate_stripe_signature(
            payload=payload,
            signature=sig_header,
            webhook_secret=webhook_secret,
        )
    except Exception:
        logger.exception("Invalid Stripe webhook signature")
        return JsonResponse(
            {"status": "error", "message": "Invalid webhook signature"},
            status=400,
        )

    # 4. Filtrar por tipo de evento
    event_type: str = event.get("type", "")
    event_id: str = event.get("id", "unknown")

    if event_type != "payment_intent.succeeded":
        logger.info(
            "Ignoring non-payment_intent.succeeded event",
            extra={"event_id": event_id, "event_type": event_type},
        )
        return JsonResponse(
            {"status": "success", "message": "Webhook processed successfully"},
            status=200,
        )

    # 5. Processar payment_intent.succeeded — criar conta do usuário
    try:
        result: dict = payment_service.process_payment_intent_succeeded(event)
    except Exception:
        elapsed_ms: float = (time.time() - start_time) * 1000
        logger.exception(
            "Failed to process payment_intent.succeeded event",
            extra={"event_id": event_id, "elapsed_ms": round(elapsed_ms, 1)},
        )
        return JsonResponse(
            {"status": "error", "message": "Failed to process webhook"},
            status=500,
        )

    if result.get("status") == "error":
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "Account creation failed",
            extra={"event_id": event_id, "error_detail": result.get("message"), "elapsed_ms": round(elapsed_ms, 1)},
        )
        return JsonResponse(
            {"status": "error", "message": result.get("message", "Failed to process webhook")},
            status=500,
        )

    # 6. Response time log + sucesso
    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(
        "Webhook processed successfully",
        extra={"event_id": event_id, "elapsed_ms": round(elapsed_ms, 1)},
    )
    return JsonResponse(
        {"status": "success", "message": "Webhook processed successfully"},
        status=200,
    )
