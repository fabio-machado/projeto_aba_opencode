"""
Service Layer para o módulo Auth App.

Toda lógica de negócio para autenticação (Magic Link Flow) reside aqui.
Views NUNCA devem chamar o Supabase diretamente.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

from django.conf import settings
from supabase import Client, create_client

from apps.core.services import AuditLogService

logger = logging.getLogger(__name__)

# -----------------------------------------------------------
# Refresh token debounce — previne race condition em
# múltiplas requisições concorrentes com o mesmo token expirado.
# O Supabase usa refresh token rotation: cada token só pode ser
# usado uma vez. Sem debounce, a primeira requisição consome o
# token e as demais falham com "Already Used".
# -----------------------------------------------------------

_refresh_lock = threading.Lock()
_refreshing_tokens: set[str] = set()

# -----------------------------------------------------------
# Configuration
# -----------------------------------------------------------

REDIRECT_TO_URL: str = os.getenv("APP_URL", "http://localhost:8000")
CALLBACK_PATH: str = "/auth/callback"

SESSION_CONFIG: dict[str, int] = {
    "jwt_expiry_seconds": 3600,          # 1 hora — padrão Supabase OTP
    "cookie_max_age_seconds": 7776000,    # 90 dias
    "rate_limit_window_seconds": 60,
    "rate_limit_max_per_email": 3,
    "rate_limit_max_per_ip": 10,
    "enumeration_threshold": 5,           # 5+ e-mails distintos → bloqueio
}

SUPPORT_EMAIL: str = os.getenv("SUPPORT_EMAIL", "")

# -----------------------------------------------------------
# Type aliases
# -----------------------------------------------------------

LoginResult = dict[str, Any] | None
LoginError = str | None

# -----------------------------------------------------------
# Custom exceptions
# -----------------------------------------------------------


class AccountInactiveError(Exception):
    """Conta existe mas subscription_status não está ativo/trial."""

    def __init__(self, email: str, status: str) -> None:
        self.email = email
        self.status = status
        super().__init__(
            f"Account inactive: email={email}, status={status}"
        )


# -----------------------------------------------------------
# Supabase admin client helper (service_role key)
# -----------------------------------------------------------


def _get_admin_client() -> Client:
    """Retorna um cliente Supabase autenticado com service_role key.

    Usa a service_role key para bypass de RLS em operações administrativas
    (validação de usuário, envio de Magic Link, logging).

    Returns:
        Cliente Supabase com privilégios de serviço.
    """
    url: str = settings.SUPABASE_URL
    service_key: str = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY

    if not url or not service_key:
        raise RuntimeError(
            "SUPABASE_URL e SUPABASE_SERVICE_KEY devem estar configurados."
        )

    return create_client(url, service_key)


# -----------------------------------------------------------
# validate_user — Verifica se e-mail pertence a usuário pagante ativo
# -----------------------------------------------------------


def validate_user(email: str) -> dict[str, Any] | None:
    """Valida se o e-mail pertence a um usuário pagante ativo.

    Fluxo:
        1. Normalizar e-mail (trim, lowercase).
        2. Validar formato básico.
        3. Query na tabela ``profiles`` via service_role key.
        4. Verificar ``subscription_status``.

    Args:
        email: E-mail informado pelo usuário (já normalizado pela view).

    Returns:
        Dicionário com ``id``, ``subscription_status``, ``has_generator_access``,
        ``has_library_access`` se encontrado e ativo. ``None`` se não encontrado.

    Raises:
        ValueError: Se o formato do e-mail for inválido.
        AccountInactiveError: Se a conta existe mas está inativa/cancelada.
    """
    normalized: str = email.strip().lower()

    # 2. Validar formato básico
    if "@" not in normalized or len(normalized.split("@")) != 2:
        raise ValueError("Email inválido.")

    local_part, domain = normalized.split("@")
    if not local_part or not domain or "." not in domain:
        raise ValueError("Email inválido.")

    client: Client = _get_admin_client()

    # 3. Query profiles pelo e-mail (service_role bypass RLS)
    try:
        response = (
            client.table("profiles")
            .select("id, email, subscription_status, has_generator_access, has_library_access")
            .eq("email", normalized)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception(
            "Failed to query profiles for user validation",
            extra={"email": normalized},
        )
        return None

    if not response.data or len(response.data) == 0:
        logger.info(
            "No profile found for email",
            extra={"email": normalized},
        )
        return None

    profile: dict = response.data[0]
    status: str = str(profile.get("subscription_status", "")).lower()
    user_id: str = str(profile.get("id", ""))

    # 4. Verificar subscription_status
    if status not in ("active", "trialing"):
        logger.info(
            "Account found but inactive",
            extra={"email": normalized, "user_id": user_id, "status": status},
        )
        raise AccountInactiveError(email=normalized, status=status)

    logger.info(
        "User validated successfully",
        extra={"email": normalized, "user_id": user_id},
    )

    return {
        "id": user_id,
        "subscription_status": status,
        "has_generator_access": bool(profile.get("has_generator_access", False)),
        "has_library_access": bool(profile.get("has_library_access", False)),
    }


# -----------------------------------------------------------
# send_magic_link — Dispara Magic Link via Supabase Auth
# -----------------------------------------------------------


def send_magic_link(email: str, user_id: str) -> bool:
    """Envia um Magic Link (OTP) para o e-mail do usuário via Supabase Auth.

    Args:
        email: E-mail normalizado do usuário.
        user_id: UUID do usuário (já serializado como str).

    Returns:
        ``True`` se o envio foi bem-sucedido, ``False`` em caso de falha
        (a falha é logada mas não propaga erro).
    """
    client: Client = _get_admin_client()
    redirect_to: str = f"{REDIRECT_TO_URL}{CALLBACK_PATH}"

    try:
        client.auth.sign_in_with_otp(
            {
                "email": email,
                "options": {"email_redirect_to": redirect_to},
            }
        )
        logger.info(
            "Magic link sent",
            extra={"user_id": user_id, "email": email, "triggered_by": "user_request"},
        )
    except Exception:
        logger.exception(
            "Failed to send magic link (non-fatal)",
            extra={"user_id": user_id, "email": email},
        )
        return False

    # Log na tabela magic_link_logs
    try:
        client.table("magic_link_logs").insert({
            "user_id": user_id,
            "email": email,
            "triggered_by": "user_request",
            "status": "sent",
        }).execute()
    except Exception:
        logger.warning(
            "Failed to log magic link send (non-fatal)",
            extra={"user_id": user_id},
        )

    # Audit log
    try:
        audit = AuditLogService()
        audit.log(
            user_id=user_id,
            action="magic_link_sent",
            table_name="magic_link_logs",
            payload={"email": email, "triggered_by": "user_request"},
        )
    except Exception:
        logger.warning(
            "Failed to write audit log for magic_link_sent (non-fatal)",
            extra={"user_id": user_id},
        )

    return True


# -----------------------------------------------------------
# check_rate_limit — Rate limiting por e-mail, IP e enumeração
# -----------------------------------------------------------


def check_rate_limit(email: str, ip_address: str) -> str | None:
    """Verifica limites de tentativas de login por e-mail, IP e enumeração.

    Args:
        email: E-mail normalizado.
        ip_address: Endereço IP do cliente.

    Returns:
        Código de bloqueio (``'rate_limit_email'``, ``'rate_limit_ip'``,
        ``'enumeration_detected'``) ou ``None`` se todas as verificações
        passarem.
    """
    client: Client = _get_admin_client()
    window_s: int = SESSION_CONFIG["rate_limit_window_seconds"]
    from datetime import datetime, timedelta, timezone

    since: str = (datetime.now(timezone.utc) - timedelta(seconds=window_s)).isoformat()

    # Step 1: Rate limit por e-mail
    try:
        resp = (
            client.table("login_attempts")
            .select("id", count="exact")
            .eq("email", email)
            .gte("attempted_at", since)
            .execute()
        )
        email_count: int = resp.count or 0
        if email_count >= SESSION_CONFIG["rate_limit_max_per_email"]:
            logger.warning(
                "Rate limit hit: email",
                extra={"email": email, "count": email_count},
            )
            return "rate_limit_email"
    except Exception:
        logger.exception(
            "Failed to check email rate limit (allowing through)",
            extra={"email": email},
        )

    # Step 2: Rate limit por IP
    try:
        resp = (
            client.table("login_attempts")
            .select("id", count="exact")
            .eq("ip_address", ip_address)
            .gte("attempted_at", since)
            .execute()
        )
        ip_count: int = resp.count or 0
        if ip_count >= SESSION_CONFIG["rate_limit_max_per_ip"]:
            logger.warning(
                "Rate limit hit: IP",
                extra={"ip_address": ip_address, "count": ip_count},
            )
            return "rate_limit_ip"
    except Exception:
        logger.exception(
            "Failed to check IP rate limit (allowing through)",
            extra={"ip_address": ip_address},
        )

    # Step 3: Detecção de enumeração
    try:
        resp = (
            client.table("login_attempts")
            .select("email")
            .eq("ip_address", ip_address)
            .eq("result", "rejected")
            .eq("rejection_reason", "email_not_found")
            .gte("attempted_at", since)
            .execute()
        )
        if resp.data:
            distinct_emails: set[str] = {row["email"] for row in resp.data}
            if len(distinct_emails) >= SESSION_CONFIG["enumeration_threshold"]:
                logger.warning(
                    "Enumeration detected",
                    extra={
                        "ip_address": ip_address,
                        "distinct_emails": len(distinct_emails),
                    },
                )
                return "enumeration_detected"
    except Exception:
        logger.exception(
            "Failed to check enumeration (allowing through)",
            extra={"ip_address": ip_address},
        )

    return None


# -----------------------------------------------------------
# log_attempt — Registra tentativa de login
# -----------------------------------------------------------


def log_attempt(
    email: str,
    ip_address: str,
    result: str,
    rejection_reason: str | None,
) -> None:
    """Registra uma tentativa de login na tabela ``login_attempts``.

    Args:
        email: E-mail normalizado.
        ip_address: Endereço IP do cliente.
        result: Resultado da tentativa (``'success'`` ou ``'rejected'``).
        rejection_reason: Razão da rejeição se ``result='rejected'``
            (ex: ``'email_not_found'``, ``'account_inactive'``, etc.).
    """
    client: Client = _get_admin_client()

    record: dict[str, Any] = {
        "email": email,
        "ip_address": ip_address,
        "result": result,
    }
    if rejection_reason is not None:
        record["rejection_reason"] = rejection_reason

    try:
        client.table("login_attempts").insert(record).execute()
        logger.info(
            "Login attempt logged",
            extra={
                "email": email,
                "result": result,
                "rejection_reason": rejection_reason,
            },
        )
    except Exception:
        logger.exception(
            "Failed to log login attempt (non-fatal)",
            extra={"email": email, "result": result},
        )


# -----------------------------------------------------------
# refresh_session — Renova sessão via refresh token
# -----------------------------------------------------------


def refresh_session(refresh_token: str) -> dict[str, Any] | None:
    """Renova uma sessão Supabase usando refresh token.

    O Supabase Auth faz rotação automática de refresh tokens — cada token
    só pode ser usado uma vez. Para evitar race conditions entre múltiplas
    requisições concorrentes, esta função usa um debounce por token.

    Args:
        refresh_token: Refresh token atual.

    Returns:
        Dicionário com ``access_token``, ``refresh_token`` e ``user``
        da nova sessão, ou ``None`` se o token expirou / é inválido.
    """
    # ── Debounce: evita que múltiplas threads façam refresh do mesmo token ──
    with _refresh_lock:
        if refresh_token in _refreshing_tokens:
            logger.debug("Refresh already in progress for this token — waiting")
            return None
        _refreshing_tokens.add(refresh_token)

    try:
        client: Client = _get_admin_client()
        resp = client.auth.refresh_session(refresh_token)
        if resp and resp.session:
            session = resp.session
            logger.info(
                "Session refreshed successfully",
                extra={"user_id": str(session.user.id) if session.user else "unknown"},
            )
            return {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "user": session.user,
            }
        return None
    except Exception:
        logger.exception("Failed to refresh session")
        return None
    finally:
        with _refresh_lock:
            _refreshing_tokens.discard(refresh_token)


# -----------------------------------------------------------
# set_callback_cookies — Setter helper para cookies da view
# -----------------------------------------------------------


def set_callback_cookies(
    response: Any,
    access_token: str,
    refresh_token: str,
) -> None:
    """Configura cookies HTTP-only de sessão no objeto response.

    Args:
        response: Objeto HttpResponse do Django.
        access_token: JWT access token.
        refresh_token: Refresh token do Supabase.
    """
    max_age: int = SESSION_CONFIG["cookie_max_age_seconds"]
    secure: bool = not settings.DEBUG

    response.set_cookie(
        key="supabase_session",
        value=access_token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="Lax",
        path="/",
    )
    response.set_cookie(
        key="supabase_refresh",
        value=refresh_token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="Lax",
        path="/",
    )


# -----------------------------------------------------------
# validate_magic_link_callback — Valida tokens do callback
# -----------------------------------------------------------


def validate_magic_link_callback(
    access_token: str,
    refresh_token: str,
    token_type: str,
) -> dict[str, str] | None:
    """Valida os parâmetros de callback do magic link e extrai o user_id.

    Verifica se o tipo de token é ``magiclink`` e se os tokens estão presentes.
    Decodifica o payload JWT para extrair o ``sub`` (user_id). Não verifica
    assinatura — o Supabase já validou o token antes do redirect.

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


# -----------------------------------------------------------
# get_profile_by_id — Busca perfil por user_id (service_role)
# -----------------------------------------------------------


def get_profile_by_id(user_id: str) -> dict[str, Any] | None:
    """Busca um perfil pelo user_id usando service_role key.

    Args:
        user_id: UUID do usuário (já serializado como str).

    Returns:
        Dicionário com os dados do perfil ou ``None`` se não encontrado.
    """
    client: Client = _get_admin_client()

    try:
        response = (
            client.table("profiles")
            .select("id, email, subscription_status, has_generator_access, has_library_access")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        if response.data and len(response.data) > 0:
            profile: dict = response.data[0]
            return {
                "id": str(profile["id"]),
                "email": profile.get("email", ""),
                "subscription_status": str(profile.get("subscription_status", "")),
                "has_generator_access": bool(profile.get("has_generator_access", False)),
                "has_library_access": bool(profile.get("has_library_access", False)),
            }

        return None

    except Exception:
        logger.exception(
            "Failed to get profile by id",
            extra={"user_id": user_id},
        )
        return None


# -----------------------------------------------------------
# update_magic_link_clicked — Atualiza status do magic link
# -----------------------------------------------------------


def update_magic_link_clicked(user_id: str) -> None:
    """Atualiza o registro mais recente de magic_link_logs para status ``clicked``.

    Args:
        user_id: UUID do usuário (serializado como str).
    """
    client: Client = _get_admin_client()

    try:
        # Buscar o registro mais recente com status 'sent' para este usuário
        resp = (
            client.table("magic_link_logs")
            .select("id")
            .eq("user_id", user_id)
            .eq("status", "sent")
            .order("sent_at", desc=True)
            .limit(1)
            .execute()
        )

        if resp.data and len(resp.data) > 0:
            log_id: str = str(resp.data[0]["id"])
            client.table("magic_link_logs").update({"status": "clicked"}).eq(
                "id", log_id
            ).execute()
            logger.info(
                "Magic link status updated to clicked",
                extra={"user_id": user_id, "log_id": log_id},
            )
        else:
            logger.warning(
                "No sent magic link log found to update",
                extra={"user_id": user_id},
            )

    except Exception:
        logger.exception(
            "Failed to update magic link status (non-fatal)",
            extra={"user_id": user_id},
        )


# -----------------------------------------------------------
# clear_session_cookies — Helper para remover cookies de sessão
# -----------------------------------------------------------


def clear_session_cookies(response: Any) -> None:
    """Remove cookies de sessão do objeto response.

    Args:
        response: Objeto HttpResponse do Django.
    """
    response.delete_cookie("supabase_session", path="/")
    response.delete_cookie("supabase_refresh", path="/")
