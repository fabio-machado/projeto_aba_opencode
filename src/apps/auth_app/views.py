"""Views para o módulo Auth App.

Views são "mudas" — apenas validam input, chamam services e retornam response.
Toda lógica de negócio reside em ``services.py``.

Constitution III: Proibição absoluta de lógica de negócio em views.
"""

from __future__ import annotations

import logging
from uuid import UUID

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
)
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET, require_POST

from apps.core.services import AuditLogService
from . import services as auth_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# login_view — GET /login
# ---------------------------------------------------------------------------


@require_GET
def login_view(request: HttpRequest) -> HttpResponse:
    """Exibe a tela de login.

    Se o usuário já possui sessão ativa (cookie ``supabase_session``),
    redireciona para a área restrita (FR-014).

    Query params aceitos:
        - ``error``: ``invalid_magic_link`` | ``account_inactive`` | ``unexpected``
        - ``next``: URL de destino após login bem-sucedido
    """
    # FR-014: Usuário já autenticado → redirecionar
    if request.COOKIES.get("supabase_session"):
        return HttpResponseRedirect(auth_service.REDIRECT_TO_URL)

    # Mapear código de erro para mensagem amigável
    error_param: str = request.GET.get("error", "")
    login_error: str = ""
    if error_param == "invalid_magic_link":
        login_error = "O link de acesso é inválido ou expirou. Solicite um novo abaixo."
    elif error_param == "account_inactive":
        login_error = "Seu acesso não está disponível no momento."
    elif error_param == "unexpected":
        login_error = "Ocorreu um erro inesperado. Tente novamente."

    next_url: str = request.GET.get("next", "")

    context: dict = {
        "login_error": login_error,
        "support_email": auth_service.SUPPORT_EMAIL,
        "next_url": next_url,
    }

    return TemplateResponse(request, "auth_app/login.html", context)


# ---------------------------------------------------------------------------
# login_submit — POST /login (submissão HTMX do formulário)
# ---------------------------------------------------------------------------


@require_POST
def login_submit(request: HttpRequest) -> HttpResponse:
    """Processa a submissão do formulário de login via Magic Link.

    Fluxo (todo delegado a services):
        1. Extrair e normalizar e-mail e IP.
        2. Rate limiting (e-mail, IP, enumeração).
        3. Validar usuário pagante ativo.
        4. Enviar Magic Link.
        5. Registrar tentativa.
    """
    # 1. Extrair input
    email: str = request.POST.get("email", "").strip().lower()
    ip_address: str = request.META.get(
        "HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "0.0.0.0")
    )
    # X-Forwarded-For pode conter lista separada por vírgula — pegar o primeiro
    if "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()
    next_url: str = request.POST.get("next", "")

    context: dict = {
        "login_error": "",
        "login_result": "",
        "support_email": auth_service.SUPPORT_EMAIL,
    }

    # 2. Validar formato básico do e-mail (antes de ir ao service)
    if not email or "@" not in email:
        context["login_error"] = "invalid_format"
        return TemplateResponse(
            request, "auth_app/partials/_login_feedback.html", context
        )

    # 3. Rate limiting
    rate_limit_reason: str | None = auth_service.check_rate_limit(email, ip_address)
    if rate_limit_reason is not None:
        logger.warning(
            "Login blocked by rate limit",
            extra={"email": email, "ip": ip_address, "reason": rate_limit_reason},
        )
        auth_service.log_attempt(email, ip_address, "rejected", rate_limit_reason)
        context["login_error"] = "rate_limit"
        return TemplateResponse(
            request, "auth_app/partials/_login_feedback.html", context
        )

    # 4. Validar usuário
    try:
        user_data: dict | None = auth_service.validate_user(email)
    except ValueError:
        auth_service.log_attempt(email, ip_address, "rejected", "email_not_found")
        context["login_error"] = "invalid_format"
        return TemplateResponse(
            request, "auth_app/partials/_login_feedback.html", context
        )
    except auth_service.AccountInactiveError:
        auth_service.log_attempt(email, ip_address, "rejected", "account_inactive")
        context["login_error"] = "account_inactive"
        return TemplateResponse(
            request, "auth_app/partials/_login_feedback.html", context
        )

    if user_data is None:
        auth_service.log_attempt(email, ip_address, "rejected", "email_not_found")
        context["login_error"] = (
            "E-mail não encontrado. Certifique-se de usar o mesmo e-mail "
            "utilizado na compra."
        )
        return TemplateResponse(
            request, "auth_app/partials/_login_feedback.html", context
        )

    # 5. Enviar Magic Link
    user_id: str = user_data["id"]
    sent: bool = auth_service.send_magic_link(email=email, user_id=user_id)

    if sent:
        auth_service.log_attempt(email, ip_address, "success", None)
        context["login_result"] = "success"
        return TemplateResponse(
            request, "auth_app/partials/_login_feedback.html", context
        )
    else:
        auth_service.log_attempt(email, ip_address, "rejected", "send_error")
        context["login_error"] = "send_error"
        return TemplateResponse(
            request, "auth_app/partials/_login_feedback.html", context
        )


# ---------------------------------------------------------------------------
# auth_callback — GET /auth/callback (página de extração de hash fragment)
# ---------------------------------------------------------------------------


@require_GET
def auth_callback(request: HttpRequest) -> TemplateResponse:
    """Renderiza a página que extrai os tokens do hash fragment via JavaScript.

    O Supabase Auth envia os tokens no hash (#fragment) da URL após o Magic Link.
    O Django não tem acesso ao hash no servidor, então esta página usa JavaScript
    para extrair os parâmetros e redirecionar para /auth/callback/process/ com
    query string (?), onde o servidor consegue ler os tokens.
    """
    return TemplateResponse(request, "auth_app/auth_callback.html", {})


# ---------------------------------------------------------------------------
# auth_callback_process — GET /auth/callback/process (processa tokens)
# ---------------------------------------------------------------------------


@require_GET
def auth_callback_process(request: HttpRequest) -> HttpResponseRedirect:
    """Processa o callback do Magic Link após extração dos tokens.

    Recebe os tokens como query parameters (convertidos do hash pelo JS na página
    auth_callback.html).

    Fluxo:
        1. Extrair query parameters (access_token, refresh_token, type).
        2. Delegar validação ao service layer.
        3. Verificar subscription_status do perfil.
        4. Setar cookies HTTP-only com access e refresh tokens.
        5. Atualizar status do magic_link_logs para ``clicked``.
        6. Registrar audit log.
        7. Redirecionar para área restrita.
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

    # 2. Validar tokens via service
    callback_data: dict | None = auth_service.validate_magic_link_callback(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type=token_type,
    )

    if callback_data is None:
        logger.warning("Magic link callback validation failed")
        return redirect("/login?error=invalid_magic_link")

    user_id: str = callback_data["user_id"]

    # 3. Verificar subscription_status via profile
    profile: dict | None = auth_service.get_profile_by_id(user_id)

    if profile is None:
        logger.warning(
            "Profile not found for callback user",
            extra={"user_id": user_id},
        )
        return redirect("/login?error=invalid_magic_link")

    status: str = str(profile.get("subscription_status", "")).lower()
    if status not in ("active", "trialing"):
        logger.warning(
            "Callback: account inactive",
            extra={"user_id": user_id, "status": status},
        )
        return redirect("/login?error=account_inactive")

    # 4. Setar cookies HTTP-only
    response: HttpResponseRedirect = redirect(auth_service.REDIRECT_TO_URL)

    auth_service.set_callback_cookies(
        response=response,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    # 5. Atualizar status do magic_link_logs
    auth_service.update_magic_link_clicked(user_id)

    # 6. Audit log
    try:
        audit = AuditLogService()
        audit.log(
            user_id=UUID(user_id),
            action="login_success",
            table_name="profiles",
            payload={"method": "magic_link", "email": profile.get("email", "")},
        )
    except Exception:
        logger.exception(
            "Failed to write audit log for login_success (non-fatal)",
            extra={"user_id": user_id},
        )

    logger.info(
        "Magic link authentication successful — session created",
        extra={"user_id": user_id},
    )

    return response


# ---------------------------------------------------------------------------
# logout_view — GET /logout
# ---------------------------------------------------------------------------


@require_GET
def logout_view(request: HttpRequest) -> HttpResponseRedirect:
    """Encerra a sessão ativa e redireciona para a tela de login.

    Remove os cookies ``supabase_session`` e ``supabase_refresh``.
    """
    response: HttpResponseRedirect = redirect("/login")

    auth_service.clear_session_cookies(response)

    logger.info("User logged out")

    return response
