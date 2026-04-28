"""
T3 — Auth Callback & Middleware (US3, US4 / FR-009, FR-010, FR-017, FR-020).

Cobre:
- GET /auth/callback renderiza página de extração de hash (JavaScript)
- GET /auth/callback/process com tokens válidos → redireciona + seta cookies
- GET /auth/callback/process com tokens inválidos → redireciona para /login?error=
- GET /auth/callback/process com conta inativa → redireciona para /login?error=account_inactive
- GET /logout limpa cookies e redireciona
- LoginRequiredMiddleware redireciona sem sessão
- LoginRequiredMiddleware permite rotas públicas (login, health)
- LoginRequiredMiddleware next param preservado
"""

from unittest.mock import MagicMock, patch

from django.http import HttpRequest, HttpResponseRedirect
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.auth.middleware import LoginRequiredMiddleware
from apps.auth.views import auth_callback, auth_callback_process, logout_view


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get(path: str, data: dict | None = None) -> HttpRequest:
    return RequestFactory().get(path, data or {})


# ---------------------------------------------------------------------------
# GET /auth/callback (página de extração de hash)
# ---------------------------------------------------------------------------


class AuthCallbackPageTest(TestCase):
    """Página de callback que extrai hash fragment via JavaScript."""

    def test_callback_page_renders(self) -> None:
        """GET /auth/callback renderiza a página de extração de hash."""
        request = _get("/auth/callback/")
        response = auth_callback(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("auth/auth_callback.html", response.template_name)

    def test_callback_page_contains_hash_extraction_js(self) -> None:
        """A página contém JavaScript para extrair hash fragment."""
        request = _get("/auth/callback/")
        response = auth_callback(request)
        response.render()
        content: str = response.content.decode()
        self.assertIn("window.location.hash", content)


# ---------------------------------------------------------------------------
# GET /auth/callback/process (processamento dos tokens)
# ---------------------------------------------------------------------------


class AuthCallbackProcessTest(TestCase):
    """Processamento dos tokens após extração do hash."""

    @patch("apps.auth.views.auth_service.get_profile_by_id")
    @patch("apps.auth.views.auth_service.validate_magic_link_callback")
    @patch("apps.auth.views.auth_service.set_callback_cookies")
    @patch("apps.auth.views.auth_service.update_magic_link_clicked")
    def test_valid_callback_redirects_and_sets_cookies(
        self,
        mock_update: MagicMock,
        mock_set_cookies: MagicMock,
        mock_validate: MagicMock,
        mock_profile: MagicMock,
    ) -> None:
        """Callback válido redireciona e seta cookies HTTP-only."""
        mock_validate.return_value = {
            "access_token": "at",
            "refresh_token": "rt",
            "user_id": "user-123",
        }
        mock_profile.return_value = {
            "id": "user-123",
            "email": "test@test.com",
            "subscription_status": "active",
        }

        request = _get(
            "/auth/callback/process/",
            {"access_token": "at", "refresh_token": "rt", "type": "magiclink"},
        )
        response: HttpResponseRedirect = auth_callback_process(request)

        self.assertEqual(response.status_code, 302)
        mock_set_cookies.assert_called_once()
        mock_update.assert_called_once_with("user-123")

    @patch("apps.auth.views.auth_service.validate_magic_link_callback",
           return_value=None)
    def test_invalid_tokens_redirects_to_login(
        self, mock_validate: MagicMock
    ) -> None:
        """Tokens inválidos redirecionam para /login?error=invalid_magic_link."""
        request = _get(
            "/auth/callback/process/",
            {"access_token": "bad", "refresh_token": "bad", "type": "bad"},
        )
        response: HttpResponseRedirect = auth_callback_process(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("invalid_magic_link", response["Location"])

    @patch("apps.auth.views.auth_service.get_profile_by_id")
    @patch("apps.auth.views.auth_service.validate_magic_link_callback")
    def test_inactive_account_redirects(
        self,
        mock_validate: MagicMock,
        mock_profile: MagicMock,
    ) -> None:
        """Conta inativa redireciona para /login?error=account_inactive."""
        mock_validate.return_value = {
            "access_token": "at",
            "refresh_token": "rt",
            "user_id": "user-123",
        }
        mock_profile.return_value = {
            "id": "user-123",
            "subscription_status": "canceled",
        }

        request = _get(
            "/auth/callback/process/",
            {"access_token": "at", "refresh_token": "rt", "type": "magiclink"},
        )
        response: HttpResponseRedirect = auth_callback_process(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("account_inactive", response["Location"])


# ---------------------------------------------------------------------------
# GET /logout
# ---------------------------------------------------------------------------


class LogoutTest(TestCase):
    """Rota de logout."""

    def test_logout_clears_cookies(self) -> None:
        """FR-020: GET /logout limpa cookies e redireciona."""
        request = _get("/logout/")
        request.COOKIES["supabase_session"] = "token"
        request.COOKIES["supabase_refresh"] = "refresh"
        response: HttpResponseRedirect = logout_view(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])
        # FR-020: Verifica que os cookies de sessão foram removidos
        # (delete_cookie seta max_age=0 ou valor vazio)
        self.assertIn("supabase_session", response.cookies)
        self.assertIn("supabase_refresh", response.cookies)
        # Cookies devem ter max_age=0 (expiração imediata) para limpeza
        self.assertEqual(response.cookies["supabase_session"]["max-age"], 0)
        self.assertEqual(response.cookies["supabase_refresh"]["max-age"], 0)


# ---------------------------------------------------------------------------
# LoginRequiredMiddleware
# ---------------------------------------------------------------------------


class LoginRequiredMiddlewareTest(TestCase):
    """Middleware de proteção de rotas."""

    def setUp(self) -> None:
        self.middleware = LoginRequiredMiddleware(lambda r: None)

    def _make_request(self, path: str) -> HttpRequest:
        return RequestFactory().get(path)

    def test_exempt_url_login_is_allowed(self) -> None:
        """FR-013: Rota /login/ é pública (whitelist)."""
        request = self._make_request("/login/")
        result = self.middleware.process_view(request, None, None, None)
        self.assertIsNone(result)  # None = permite continuar

    def test_exempt_url_health_is_allowed(self) -> None:
        """Rota /health/ é pública."""
        request = self._make_request("/health/")
        result = self.middleware.process_view(request, None, None, None)
        self.assertIsNone(result)

    @override_settings(LOGIN_URL="/login/")
    def test_protected_route_without_session_redirects(self) -> None:
        """Rota protegida sem cookie de sessão redireciona para /login."""
        request = self._make_request("/routines/")
        result = self.middleware.process_view(request, None, None, None)
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 302)
        self.assertIn("/login/", result["Location"])

    @override_settings(LOGIN_URL="/login/")
    def test_protected_route_preserves_next_param(self) -> None:
        """Rota protegida inclui ?next= na URL de redirect."""
        request = self._make_request("/routines/")
        result = self.middleware.process_view(request, None, None, None)
        self.assertIn("?next=", result["Location"])
        self.assertIn("/routines/", result["Location"])

    @patch("apps.auth.middleware._decode_jwt")
    @patch("apps.auth.middleware.auth_service.get_profile_by_id")
    def test_valid_session_allows_access(
        self,
        mock_profile: MagicMock,
        mock_decode: MagicMock,
    ) -> None:
        """Sessão válida permite acesso à rota protegida."""
        mock_decode.return_value = {"sub": "user-123", "exp": 9999999999}
        mock_profile.return_value = {"subscription_status": "active"}

        request = self._make_request("/routines/")
        request.COOKIES["supabase_session"] = "valid.jwt.token"
        result = self.middleware.process_view(request, None, None, None)
        self.assertIsNone(result)

    @patch("apps.auth.middleware._decode_jwt")
    @patch("apps.auth.middleware.auth_service.get_profile_by_id")
    def test_canceled_subscription_redirects(
        self,
        mock_profile: MagicMock,
        mock_decode: MagicMock,
    ) -> None:
        """Assinatura cancelada redireciona para login com erro."""
        mock_decode.return_value = {"sub": "user-123", "exp": 9999999999}
        mock_profile.return_value = {"subscription_status": "canceled"}

        request = self._make_request("/routines/")
        request.COOKIES["supabase_session"] = "valid.jwt.token"
        result = self.middleware.process_view(request, None, None, None)
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 302)
        self.assertIn("account_inactive", result["Location"])
