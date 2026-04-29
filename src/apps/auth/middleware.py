"""
Middleware de Autenticação — LoginRequiredMiddleware.

Verifica sessão Supabase em todas as requisições. Exceções configuradas
via ``settings.LOGIN_EXEMPT_URLS``. Tentativa automática de refresh do
token se expirado. Verifica subscription_status para bloquear contas
inativas.

Constitution III: Middleware NÃO contém lógica de negócio — apenas chama
funções de ``services.py``.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin

from . import services as auth_service

logger = logging.getLogger(__name__)


def _decode_jwt(token: str) -> dict | None:
    """Decodifica o payload de um JWT **sem verificar assinatura**.

    Usado apenas para extrair ``sub`` (user_id) e ``exp``. O Supabase
    já validou o token antes de emiti-lo; a assinatura não precisa ser
    verificada novamente no middleware.

    Args:
        token: JWT bruto (raw).

    Returns:
        Dicionário decodificado do payload ou ``None`` em caso de erro.
    """
    try:
        parts: list[str] = token.split(".")
        if len(parts) != 3:
            return None

        payload_b64: str = parts[1]
        # Adicionar padding se necessário (base64url)
        padding: int = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload_bytes: bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_bytes)

    except Exception:
        logger.exception("Failed to decode JWT in middleware")
        return None


class LoginRequiredMiddleware(MiddlewareMixin):
    """Bloqueia acesso a rotas protegidas sem sessão Supabase válida.

    Fluxo (tudo delegado a services):
        1. Verifica se a URL está na lista de isenção.
        2. Lê o cookie ``supabase_session``.
        3. Se ausente → redireciona para login.
        4. Decodifica payload JWT para extrair ``user_id`` e ``exp``.
        5. Se expirado → tenta refresh via ``supabase_refresh`` cookie.
        6. Se refresh falhar → limpa cookies e redireciona.
        7. Verifica ``subscription_status`` do perfil → bloqueia
           ``canceled`` e ``past_due``.
        8. Se tudo ok → delega para a view (retorna ``None``).

    Cookies renovados são persistidos via ``process_response``.
    """

    def __init__(self, get_response: Callable) -> None:
        """Compila padrões regex das URLs isentas de autenticação."""
        super().__init__(get_response)

        exempt: list[str] = getattr(settings, "LOGIN_EXEMPT_URLS", [])
        self._exempt_patterns: list[re.Pattern] = [
            re.compile(pattern) for pattern in exempt
        ]

        logger.debug(
            "LoginRequiredMiddleware initialized with %d exempt patterns",
            len(self._exempt_patterns),
        )

    # ------------------------------------------------------------------
    # process_view — gating principal
    # ------------------------------------------------------------------

    def process_view(
        self,
        request: HttpRequest,
        view_func: object,  # noqa: ARG002
        view_args: tuple,  # noqa: ARG002
        view_kwargs: dict,  # noqa: ARG002
    ) -> HttpResponse | None:
        """Verifica sessão antes de cada view (exceto URLs isentas).

        Returns:
            ``None`` se a sessão é válida (continua para a view).
            ``HttpResponseRedirect`` para ``/login/`` se inválida.
        """
        path: str = request.path

        # ── 1. URLs isentas ─────────────────────────────────────
        for pattern in self._exempt_patterns:
            if pattern.search(path):
                return None

        # ── 2. Cookie de sessão ─────────────────────────────────
        access_token: str = request.COOKIES.get("supabase_session", "")
        refresh_token: str = request.COOKIES.get("supabase_refresh", "")

        if not access_token:
            logger.debug("No session cookie — redirecting to login")
            return self._redirect_to_login(request)

        # ── 3. Decodificar JWT ─────────────────────────────────
        payload: dict | None = _decode_jwt(access_token)
        if payload is None:
            logger.warning("Malformed JWT — clearing cookies and redirecting")
            return self._redirect_to_login(request, clear=True)

        user_id: str = payload.get("sub", "")
        exp: int = payload.get("exp", 0)

        # ── 4. Token expirado? Tentar refresh ──────────────────
        now: int = int(time.time())
        if exp > 0 and now >= exp:
            logger.debug("Access token expired — attempting refresh")

            if not refresh_token:
                logger.info("No refresh token available — redirecting")
                return self._redirect_to_login(request, clear=True)

            new_session = auth_service.refresh_session(refresh_token)
            if new_session is None:
                # Falha real: token expirado, inválido ou já consumido.
                # Limpa cookies e redireciona — sessão não pode ser recuperada.
                logger.warning("Session refresh definitively failed — redirecting to login")
                return self._redirect_to_login(request, clear=True)

            if new_session is auth_service._refresh_debounced:
                # Outra requisição concorrente já está fazendo refresh deste
                # mesmo token. Prossegue sem redirecionar — a requisição que
                # concluir o refresh atualizará os cookies no response.
                logger.debug("Session refresh debounced — proceeding with request")
                return None

            # Armazena novos tokens para persistir em process_response
            new_access: str = str(new_session["access_token"])
            new_refresh: str = str(new_session["refresh_token"])
            request._supabase_new_tokens = {  # type: ignore[attr-defined]
                "access_token": new_access,
                "refresh_token": new_refresh,
            }

            # Re-decodificar para checar subscription
            payload = _decode_jwt(new_access)
            if payload is None:
                return self._redirect_to_login(request, clear=True)
            user_id = payload.get("sub", "")

            logger.info(
                "Session refreshed via middleware",
                extra={"user_id": user_id},
            )

        # ── 5. Verificar subscription_status ────────────────────
        if user_id:
            profile: dict | None = auth_service.get_profile_by_id(user_id)
            if profile is not None:
                status: str = str(profile.get("subscription_status", "")).lower()
                if status in ("canceled", "past_due"):
                    logger.info(
                        "Middleware: account inactive — redirecting",
                        extra={"user_id": user_id, "status": status},
                    )
                    response: HttpResponseRedirect = HttpResponseRedirect(
                        "/login?error=account_inactive"
                    )
                    auth_service.clear_session_cookies(response)
                    return response

        return None

    # ------------------------------------------------------------------
    # process_response — persiste cookies renovados
    # ------------------------------------------------------------------

    def process_response(
        self,
        request: HttpRequest,
        response: HttpResponse,
    ) -> HttpResponse:
        """Se a sessão foi renovada em ``process_view``, seta os novos cookies.

        Chamado automaticamente pelo Django após a view retornar.
        """
        new_tokens: dict | None = getattr(request, "_supabase_new_tokens", None)
        if new_tokens:
            auth_service.set_callback_cookies(
                response=response,
                access_token=str(new_tokens["access_token"]),
                refresh_token=str(new_tokens["refresh_token"]),
            )
            # Limpar atributo para evitar reprocessamento
            try:
                delattr(request, "_supabase_new_tokens")
            except AttributeError:
                pass

        return response

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _redirect_to_login(
        self,
        request: HttpRequest,
        clear: bool = False,
    ) -> HttpResponseRedirect:
        """Redireciona para a tela de login preservando a URL de destino.

        Args:
            request: Requisição atual.
            clear: Se ``True``, remove cookies de sessão no response.

        Returns:
            Redirect para ``/login/?next=<caminho original>``.
        """
        login_url: str = getattr(settings, "LOGIN_URL", "/login/")
        next_param: str = request.path

        # Evitar loop: não redirecionar se já está na URL de login
        if next_param == login_url or next_param.startswith(login_url):
            next_param = ""

        url: str = f"{login_url}" + (f"?next={next_param}" if next_param else "")
        response: HttpResponseRedirect = HttpResponseRedirect(url)
        if clear:
            auth_service.clear_session_cookies(response)
        return response
