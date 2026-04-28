import logging
import time

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.payments import services as payment_service

logger = logging.getLogger(__name__)


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
