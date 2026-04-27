"""
Service Layer para o módulo Payments.

Toda lógica de negócio e chamadas ao Supabase/Stripe residem aqui.
Views NUNCA devem chamar o Supabase ou Stripe diretamente.
"""

import logging
import time
import traceback
from uuid import UUID

import stripe
from django.conf import settings
from supabase import Client, create_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# T023b — Audit logging service (Constitution IV: Auditabilidade)
# ---------------------------------------------------------------------------

def log_audit_event(
    user_id: str,
    action: str,
    metadata: dict | None = None,
) -> bool:
    """Registra um evento de auditoria na tabela ``audit_logs``.

    Usa service_role key para bypass de RLS (operação administrativa).

    Args:
        user_id: UUID do usuário (serializado como str).
        action: Ação realizada (ex: ``user_created``, ``magic_link_sent``,
            ``webhook_processed``, ``user_exists``).
        metadata: Dados adicionais em formato JSONB (opcional).

    Returns:
        ``True`` se o registro foi inserido com sucesso, ``False`` em caso
        de falha (a falha é logada mas não propaga erro).
    """
    client: Client = _get_admin_client()

    record: dict = {
        "user_id": user_id,
        "action": action,
        "metadata": metadata or {},
    }

    try:
        client.table("audit_logs").insert(record).execute()
        logger.info(
            "Audit event logged",
            extra={"user_id": user_id, "action": action},
        )
        return True

    except Exception:
        logger.exception(
            "Failed to log audit event (non-fatal)",
            extra={"user_id": user_id, "action": action},
        )
        return False


# ---------------------------------------------------------------------------
# Supabase client helper (service-role key for admin operations)
# ---------------------------------------------------------------------------

def _get_admin_client() -> Client:
    """Retorna um cliente Supabase autenticado com service_role key.

    Usa a service_role key para bypass de RLS em operações administrativas
    (criação de usuários, inserção de perfis, etc.).

    Returns:
        Cliente Supabase com privilégios de serviço.
    """
    url: str = settings.SUPABASE_URL
    service_key: str = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY

    if not url or not service_key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_KEY devem estar configurados.")

    return create_client(url, service_key)


# ---------------------------------------------------------------------------
# Stripe webhook validation (existing)
# ---------------------------------------------------------------------------

def validate_stripe_signature(
    payload: bytes,
    signature: str,
    webhook_secret: str,
) -> dict:
    """Valida a assinatura de um webhook Stripe.

    Args:
        payload: Raw body bytes da requisição HTTP.
        signature: Valor do header Stripe-Signature.
        webhook_secret: Stripe webhook signing secret (WHSEC_…).

    Returns:
        Dicionário com o evento Stripe desserializado.

    Raises:
        stripe.error.SignatureVerificationError: Se a assinatura for inválida
            ou expirada (fora da tolerância de 5 minutos).
    """
    event_obj = stripe.Webhook.construct_event(
        payload=payload,
        sig_header=signature,
        secret=webhook_secret,
    )
    event: dict = event_obj.to_dict()
    logger.info(
        "Stripe webhook signature validated",
        extra={"event_id": event.get("id"), "event_type": event.get("type")},
    )
    return event


# ---------------------------------------------------------------------------
# T011 — Supabase Auth user creation
# ---------------------------------------------------------------------------

def create_supabase_user(email: str, full_name: str) -> dict:
    """Cria um usuário no Supabase Auth via Admin API.

    Args:
        email: Endereço de e-mail do usuário (deve ser único).
        full_name: Nome completo do usuário (armazenado em user_metadata).

    Returns:
        Dicionário com ``id`` (str) e ``email`` do usuário criado.

    Raises:
        RuntimeError: Se as credenciais do Supabase não estiverem configuradas.
    """
    client: Client = _get_admin_client()

    try:
        response = client.auth.admin.create_user(
            attributes={
                "email": email,
                "email_confirm": True,  # Confirma automaticamente (veio de pagamento)
                "user_metadata": {"full_name": full_name},
            }
        )
        user_id: str = str(response.user.id)
        logger.info(
            "Supabase Auth user created",
            extra={"user_id": user_id, "email": email},
        )
        return {"id": user_id, "email": email}

    except Exception as exc:
        # Verifica se o erro é por usuário já existente
        error_msg: str = str(exc).lower()
        if "already registered" in error_msg or "already exists" in error_msg or "duplicate" in error_msg:
            logger.info(
                "Supabase Auth user already exists (idempotent)",
                extra={"email": email},
            )
            # Retorna None para sinalizar que o usuário já existe
            return {}  # dict vazio = já existe
        logger.exception("Failed to create Supabase Auth user", extra={"email": email})
        raise


# ---------------------------------------------------------------------------
# T012 — Profile insertion
# ---------------------------------------------------------------------------

def create_profile(
    user_id: str,
    email: str,
    full_name: str,
    stripe_customer_id: str | None = None,
    cpf: str | None = None,
    subscription_status: str = "active",
) -> dict:
    """Insere um registro na tabela ``profiles`` do Supabase.

    Args:
        user_id: UUID do usuário Auth (já serializado como str).
        email: Endereço de email do usuário.
        full_name: Nome completo do usuário.
        stripe_customer_id: ID do cliente Stripe (opcional).
        cpf: CPF do usuário (opcional).
        subscription_status: Status da assinatura (default: ``active``).

    Returns:
        Dicionário com o perfil criado.

    Raises:
        RuntimeError: Se as credenciais do Supabase não estiverem configuradas.
    """
    client: Client = _get_admin_client()

    profile_data: dict = {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "subscription_status": subscription_status,
    }
    if stripe_customer_id:
        profile_data["stripe_customer_id"] = stripe_customer_id
    if cpf:
        profile_data["cpf"] = cpf

    response = client.table("profiles").insert(profile_data).execute()

    if not response.data:
        raise RuntimeError("Falha ao criar perfil: nenhuma resposta do Supabase.")

    profile: dict = response.data[0]
    logger.info(
        "Profile created",
        extra={"user_id": user_id, "profile_id": str(profile.get("id"))},
    )
    return profile


# ---------------------------------------------------------------------------
# T013 — Existing user detection by email
# ---------------------------------------------------------------------------

def find_user_by_email(email: str) -> dict | None:
    """Busca um usuário existente pelo e-mail usando a tabela ``profiles``.

    Query direta na tabela profiles com índice único em email — O(1).

    Args:
        email: Endereço de e-mail a buscar.

    Returns:
        Dicionário com ``id`` (str) e ``email`` se encontrado, ``None`` caso
        contrário.
    """
    client: Client = _get_admin_client()

    try:
        response = (
            client.table("profiles")
            .select("id, email")
            .eq("email", email.lower())
            .limit(1)
            .execute()
        )

        if response.data and len(response.data) > 0:
            user = response.data[0]
            return {
                "id": str(user["id"]),
                "email": user["email"],
            }

        return None

    except Exception:
        logger.exception("Failed to search user by email", extra={"email": email})
        return None


# ---------------------------------------------------------------------------
# T018 — Active session check
# ---------------------------------------------------------------------------

def has_active_session(user_id: str) -> bool:
    """Verifica se um usuário possui sessões ativas no Supabase Auth.

    Usa a Auth Admin API para listar sessões do usuário. Se o método
    ``list_sessions`` não estiver disponível na versão do supabase-py,
    faz fallback para verificar ``last_sign_in_at`` do usuário.

    Args:
        user_id: UUID do usuário (serializado como str).

    Returns:
        ``True`` se o usuário possui ao menos uma sessão ativa, ``False``
        caso contrário. Falhas são logadas e retornam ``False``.
    """
    client: Client = _get_admin_client()

    try:
        # Tenta usar list_sessions (disponível em versões mais recentes)
        response = client.auth.admin.list_sessions(user_id)
        sessions = getattr(response, "sessions", []) or []
        return len(sessions) > 0

    except (AttributeError, TypeError):
        # Fallback: verifica last_sign_in_at do usuário
        try:
            user_response = client.auth.admin.get_user_by_id(user_id)
            user = getattr(user_response, "user", None)
            if user:
                last_sign_in: str | None = getattr(user, "last_sign_in_at", None)
                return last_sign_in is not None
            return False

        except Exception:
            logger.exception(
                "Failed to check active session (fallback)",
                extra={"user_id": user_id},
            )
            return False

    except Exception:
        logger.exception(
            "Failed to check active session",
            extra={"user_id": user_id},
        )
        return False


# ---------------------------------------------------------------------------
# T014 — Magic link sending
# ---------------------------------------------------------------------------

def send_magic_link(
    email: str,
    user_id: str,
    triggered_by: str = "webhook_auto_account",
) -> bool:
    """Envia um magic link (OTP) para o e-mail do usuário via Supabase Auth.

    Args:
        email: Endereço de e-mail para envio.
        user_id: UUID do usuário (já serializado como str).
        triggered_by: Origem do envio (default: ``webhook_auto_account``).

    Returns:
        ``True`` se o envio foi bem-sucedido, ``False`` em caso de falha
        (a falha é logada mas não propaga erro).
    """
    client: Client = _get_admin_client()

    app_url: str = getattr(settings, "APP_URL", "http://localhost:8000")
    redirect_to: str = f"{app_url}/auth/callback"

    try:
        client.auth.sign_in_with_otp(
            {"email": email, "options": {"email_redirect_to": redirect_to}}
        )
        logger.info(
            "Magic link sent",
            extra={"user_id": user_id, "email": email, "triggered_by": triggered_by},
        )

        # Log na tabela magic_link_logs
        _log_magic_link_sent(
            client=client,
            user_id=user_id,
            email=email,
            triggered_by=triggered_by,
        )

        return True

    except Exception:
        logger.exception(
            "Failed to send magic link (non-fatal)",
            extra={"user_id": user_id, "email": email},
        )
        return False


def _log_magic_link_sent(
    client: Client,
    user_id: str,
    email: str,
    triggered_by: str,
) -> None:
    """Registra o envio de magic link na tabela ``magic_link_logs``.

    Args:
        client: Cliente Supabase já inicializado.
        user_id: UUID do usuário (serializado como str).
        email: E-mail para o qual o link foi enviado.
        triggered_by: Origem do envio.
    """
    try:
        client.table("magic_link_logs").insert({
            "user_id": user_id,
            "email": email,
            "triggered_by": triggered_by,
            "status": "sent",
        }).execute()
    except Exception:
        # Falha no log não deve impedir o fluxo principal
        logger.warning(
            "Failed to log magic link send (non-fatal)",
            extra={"user_id": user_id},
        )


# ---------------------------------------------------------------------------
# T016 / T017 — Idempotency: event tracking via processed_webhook_events
# ---------------------------------------------------------------------------

def is_event_processed(stripe_event_id: str) -> bool:
    """Verifica se um evento Stripe já foi processado.

    Consulta a tabela ``processed_webhook_events`` usando service_role key
    (bypass RLS).

    Args:
        stripe_event_id: ID do evento Stripe (ex: ``evt_1Nxxx...``).

    Returns:
        ``True`` se o evento já foi processado, ``False`` caso contrário.
    """
    client: Client = _get_admin_client()

    response = (
        client.table("processed_webhook_events")
        .select("stripe_event_id")
        .eq("stripe_event_id", stripe_event_id)
        .limit(1)
        .execute()
    )

    return len(response.data or []) > 0


def mark_event_processed(
    stripe_event_id: str,
    event_type: str,
    status: str = "success",
    error_message: str | None = None,
) -> bool:
    """Registra que um evento Stripe foi processado.

    Insere um registro na tabela ``processed_webhook_events``. Se o evento
    já estiver registrado (chave duplicada), retorna ``True`` silenciosamente
    — isso garante idempotência em nível de banco.

    Args:
        stripe_event_id: ID do evento Stripe (ex: ``evt_1Nxxx...``).
        event_type: Tipo do evento (ex: ``payment_intent.succeeded``).
        status: Status do processamento (default: ``success``).
        error_message: Mensagem de erro opcional se status for ``error``.

    Returns:
        ``True`` se o registro foi inserido ou já existia, ``False`` em caso
        de erro inesperado.
    """
    client: Client = _get_admin_client()

    record: dict = {
        "stripe_event_id": stripe_event_id,
        "event_type": event_type,
        "status": status,
    }
    if error_message is not None:
        record["error_message"] = error_message

    try:
        client.table("processed_webhook_events").insert(record).execute()
        logger.info(
            "Event marked as processed",
            extra={"stripe_event_id": stripe_event_id, "event_type": event_type, "status": status},
        )
        return True

    except Exception as exc:
        error_msg: str = str(exc).lower()
        # Duplicate key = event already marked (idempotent)
        if "duplicate" in error_msg or "already exists" in error_msg or "unique" in error_msg:
            logger.info(
                "Event already marked as processed (idempotent)",
                extra={"stripe_event_id": stripe_event_id},
            )
            return True

        logger.exception(
            "Failed to mark event as processed",
            extra={"stripe_event_id": stripe_event_id},
        )
        return False


# ---------------------------------------------------------------------------
# T020 — Magic link callback validation
# ---------------------------------------------------------------------------

def validate_magic_link_callback(
    access_token: str,
    refresh_token: str,
    token_type: str,
) -> dict | None:
    """Valida os parâmetros de callback do magic link e retorna dados da sessão.

    Verifica se o tipo de token é ``magiclink`` e se os tokens estão presentes.
    Em produção, o Supabase já validou o token antes do redirect — esta função
    faz validação defensiva dos parâmetros recebidos.

    Args:
        access_token: JWT access token fornecido pelo Supabase Auth.
        refresh_token: Refresh token para renovação de sessão.
        token_type: Tipo do token (deve ser ``magiclink``).

    Returns:
        Dicionário com ``access_token``, ``refresh_token`` e ``user_id``
        se válido, ``None`` se inválido.
    """
    if token_type != "magiclink":
        logger.warning(
            "Magic link callback with invalid token type",
            extra={"token_type": token_type},
        )
        return None

    if not access_token or not refresh_token:
        logger.warning("Magic link callback missing required tokens")
        return None

    # Extrair user_id do JWT (payload decodificado sem verificação de assinatura)
    # O Supabase já validou o token antes do redirect — extraímos apenas o sub.
    try:
        import base64
        import json

        parts: list[str] = access_token.split(".")
        if len(parts) != 3:
            logger.warning("Malformed JWT in magic link callback")
            return None

        # Decodificar payload (segunda parte do JWT)
        payload_b64: str = parts[1]
        # Adicionar padding se necessário
        padding: int = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload_bytes: bytes = base64.urlsafe_b64decode(payload_b64)
        payload: dict = json.loads(payload_bytes)

        user_id: str = payload.get("sub", "")
        if not user_id:
            logger.warning("JWT payload missing 'sub' claim")
            return None

        logger.info(
            "Magic link callback validated successfully",
            extra={"user_id": user_id},
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": user_id,
        }

    except Exception:
        logger.exception("Failed to decode JWT from magic link callback")
        return None


# ---------------------------------------------------------------------------
# T015 — Complete account creation flow (called from webhook view)
# ---------------------------------------------------------------------------

def process_payment_intent_succeeded(event: dict) -> dict:
    """Processa um evento ``payment_intent.succeeded`` e cria a conta do usuário.

    Fluxo:
        0. Verificar idempotência — se evento já processado, retornar imediatamente.
        1. Extrair email e nome do evento Stripe.
        2. Verificar se o usuário já existe (T013).
        3. Se existir: retornar idempotente.
        4. Se não: criar Auth user (T011) + criar perfil (T012) + enviar magic link (T014).
        5. Marcar evento como processado (T017).

    Args:
        event: Dicionário do evento Stripe desserializado.

    Returns:
        Dicionário com ``status`` e detalhes do processamento.
    """
    event_id: str = event.get("id", "unknown")
    event_type: str = event.get("type", "unknown")

    # 0. Idempotência — verificar se evento já foi processado
    if is_event_processed(event_id):
        logger.info(
            "Event already processed (idempotent skip)",
            extra={"event_id": event_id, "event_type": event_type},
        )
        return {
            "status": "success",
            "message": "Event already processed",
            "action": "idempotent",
        }

    data: dict = event.get("data", {}).get("object", {})

    # 1. Extrair email, nome e metadata
    email: str | None = data.get("receipt_email")
    full_name: str | None = None
    stripe_customer_id: str | None = data.get("customer")
    cpf: str | None = None

    # Extrair metadata customizada (ex: cpf passado no checkout)
    metadata: dict = data.get("metadata", {})
    if metadata:
        cpf = metadata.get("cpf")

    # Tentar extrair nome dos charges
    charges: list = data.get("charges", {}).get("data", [])
    if charges:
        billing_details: dict = charges[0].get("billing_details", {})
        full_name = billing_details.get("name")
        if not email:
            email = billing_details.get("email")

    if not email:
        logger.warning(
            "Missing email in payment_intent.succeeded event",
            extra={"event_id": event_id},
        )
        return {"status": "error", "message": "Missing email in payment intent"}

    full_name = full_name or email  # Fallback: usa email como nome

    logger.info(
        "Processing payment_intent.succeeded for account creation",
        extra={"event_id": event_id, "email": email},
    )

    # 2. Verificar se usuário já existe
    existing_user: dict | None = find_user_by_email(email)
    if existing_user:
        logger.info(
            "User already exists (idempotent)",
            extra={"event_id": event_id, "user_id": existing_user["id"]},
        )
        # Audit log: user_exists
        log_audit_event(
            user_id=existing_user["id"],
            action="user_exists",
            metadata={"event_id": event_id, "event_type": event_type},
        )
        # Marcar evento como processado para futuros duplicatas hitarem o fast path
        mark_event_processed(
            stripe_event_id=event_id,
            event_type=event_type,
            status="success",
        )
        return {
            "status": "success",
            "message": "User already exists",
            "user_id": existing_user["id"],
            "action": "idempotent",
        }

    # 3. Criar Auth user
    user_result: dict = create_supabase_user(email=email, full_name=full_name)
    if not user_result:
        # Usuário já existia (race condition)
        logger.info(
            "User creation returned empty (race condition — user already exists)",
            extra={"event_id": event_id, "email": email},
        )
        mark_event_processed(
            stripe_event_id=event_id,
            event_type=event_type,
            status="success",
        )
        return {
            "status": "success",
            "message": "User already exists (race condition)",
            "action": "idempotent",
        }

    user_id: str = user_result["id"]

    # 4. Criar perfil
    try:
        create_profile(
            user_id=user_id,
            email=email,
            full_name=full_name,
            stripe_customer_id=stripe_customer_id,
            cpf=cpf,
            subscription_status="active",
        )
    except Exception:
        logger.exception(
            "Failed to create profile after Auth user creation",
            extra={"event_id": event_id, "user_id": user_id},
        )
        return {
            "status": "error",
            "message": "Failed to create user profile",
        }

    # Audit log: user_created (after profile exists for FK constraint)
    log_audit_event(
        user_id=user_id,
        action="user_created",
        metadata={"event_id": event_id, "email": email, "full_name": full_name},
    )

    # 5. Enviar magic link
    magic_link_sent: bool = send_magic_link(
        email=email,
        user_id=user_id,
        triggered_by="webhook_auto_account",
    )

    # Audit log: magic_link_sent (even if failed, we log the attempt)
    log_audit_event(
        user_id=user_id,
        action="magic_link_sent",
        metadata={"event_id": event_id, "success": magic_link_sent},
    )

    # 6. Marcar evento como processado (idempotência)
    if not mark_event_processed(
        stripe_event_id=event_id,
        event_type=event_type,
        status="success",
    ):
        logger.error(
            "Failed to mark event as processed — Stripe will retry",
            extra={"event_id": event_id},
        )
        return {
            "status": "error",
            "message": "Failed to record event processing",
        }

    logger.info(
        "Account creation completed successfully",
        extra={"event_id": event_id, "user_id": user_id},
    )

    # Audit log: webhook_processed
    log_audit_event(
        user_id=user_id,
        action="webhook_processed",
        metadata={"event_id": event_id, "event_type": event_type, "action": "created"},
    )

    return {
        "status": "success",
        "message": "Account created successfully",
        "user_id": user_id,
        "action": "created",
    }
