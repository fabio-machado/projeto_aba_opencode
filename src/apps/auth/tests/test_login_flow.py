"""
T1 — Login Flow (US1, US2 / FR-001–FR-008, FR-012–FR-014).

Cobre:
- GET /login renderiza a página de login
- POST /login/submit com e-mail válido → sucesso (Magic Link enviado)
- POST /login/submit com e-mail não cadastrado → erro
- POST /login/submit com formato inválido → erro
- POST /login/submit com conta inativa → erro
- GET /login já autenticado → redireciona para área restrita
"""

from unittest.mock import MagicMock, patch

from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.auth import services as auth_service
from apps.auth.views import login_view, login_submit

from .conftest import make_request as _request  # noqa: E402

# ---------------------------------------------------------------------------
# GET /login
# ---------------------------------------------------------------------------


class LoginPageTest(TestCase):
    """Verifica a renderização da página de login."""

    def test_login_page_renders(self) -> None:
        """GET /login retorna 200 com o template de login."""
        request = _request("GET", "/login/")
        response: TemplateResponse = login_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("auth/login.html", response.template_name)

    @override_settings(LOGIN_URL="/login/")
    def test_login_page_authenticated_user_redirects(self) -> None:
        """FR-014: Usuário com cookie supabase_session é redirecionado para área restrita."""
        request = _request("GET", "/login/")
        request.COOKIES["supabase_session"] = "fake-token"
        response: HttpResponse = login_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], auth_service.REDIRECT_TO_URL)

    def test_login_page_error_param_invalid_magic_link(self) -> None:
        """?error=invalid_magic_link exibe mensagem apropriada."""
        request = _request("GET", "/login/?error=invalid_magic_link")
        response: TemplateResponse = login_view(request)
        response.render()
        content: str = response.content.decode()
        self.assertIn("inválido", content.lower())

    def test_login_page_error_param_account_inactive(self) -> None:
        """?error=account_inactive exibe mensagem apropriada."""
        request = _request("GET", "/login/?error=account_inactive")
        response: TemplateResponse = login_view(request)
        response.render()
        content: str = response.content.decode()
        self.assertIn("não está disponível", content.lower())

    def test_login_page_error_param_unexpected(self) -> None:
        """?error=unexpected exibe mensagem de erro genérica."""
        request = _request("GET", "/login/?error=unexpected")
        response: TemplateResponse = login_view(request)
        response.render()
        content: str = response.content.decode()
        self.assertIn("inesperado", content.lower())

    def test_login_page_preserves_next_url_in_context(self) -> None:
        """?next=/routines/ preserva a URL de destino no contexto do template."""
        request = _request("GET", "/login/?next=/routines/")
        response: TemplateResponse = login_view(request)
        response.render()
        content: str = response.content.decode()
        self.assertIn("/routines/", content)

    def test_login_page_contains_support_email(self) -> None:
        """Página de login contém o link de suporte."""
        request = _request("GET", "/login/")
        response: TemplateResponse = login_view(request)
        response.render()
        content: str = response.content.decode()
        self.assertIn("Fale conosco", content)

    def test_login_page_contains_instructional_text(self) -> None:
        """Página de login contém texto instrucional sobre Magic Link."""
        request = _request("GET", "/login/")
        response: TemplateResponse = login_view(request)
        response.render()
        content: str = response.content.decode()
        self.assertIn("não é necessário senha", content.lower())


# ---------------------------------------------------------------------------
# POST /login/submit — Validação de formato
# ---------------------------------------------------------------------------


class LoginSubmitFormatTest(TestCase):
    """Validação de formato do e-mail."""

    def test_empty_email_returns_error(self) -> None:
        """E-mail vazio retorna erro de formato."""
        request = _request("POST", "/login/submit/", {"email": ""})
        response: TemplateResponse = login_submit(request)
        response.render()
        content: str = response.content.decode()
        self.assertIn("login-error", content)
        self.assertIn("formato", content.lower())

    def test_no_at_symbol_returns_error(self) -> None:
        """E-mail sem @ retorna erro de formato."""
        request = _request("POST", "/login/submit/", {"email": "usuario"})
        response: TemplateResponse = login_submit(request)
        response.render()
        content: str = response.content.decode()
        self.assertIn("login-error", content)

    @patch("apps.auth.views.auth_service.send_magic_link", return_value=True)
    @patch("apps.auth.views.auth_service.validate_user")
    @patch("apps.auth.views.auth_service.check_rate_limit", return_value=None)
    @patch("apps.auth.views.auth_service.log_attempt")
    def test_valid_format_passes_validation(
        self,
        mock_log: MagicMock,
        mock_rate: MagicMock,
        mock_validate: MagicMock,
        mock_send: MagicMock,
    ) -> None:
        """FR-002: E-mail com @ passa pela validação de formato e chega ao service."""
        mock_validate.return_value = {
            "id": "user-123",
            "subscription_status": "active",
            "has_generator_access": True,
            "has_library_access": False,
        }
        request = _request("POST", "/login/submit/", {"email": "usuario@exemplo.com"})
        response: TemplateResponse = login_submit(request)
        response.render()
        content: str = response.content.decode()
        self.assertNotIn("formato", content.lower())
        # Valida que o e-mail passou pela validação de formato e chegou ao service
        mock_validate.assert_called_once_with("usuario@exemplo.com")


# ---------------------------------------------------------------------------
# POST /login/submit — Fluxo de negócio (mocked)
# ---------------------------------------------------------------------------


class LoginSubmitBusinessFlowTest(TestCase):
    """Fluxo de negócio do login com serviços mockados."""

    @patch("apps.auth.views.auth_service.validate_user")
    @patch("apps.auth.views.auth_service.send_magic_link")
    @patch("apps.auth.views.auth_service.check_rate_limit", return_value=None)
    @patch("apps.auth.views.auth_service.log_attempt")
    def test_successful_login_returns_success_partial(
        self,
        mock_log: MagicMock,
        mock_rate: MagicMock,
        mock_send: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        """Login bem-sucedido retorna partial com login_result='success'."""
        mock_validate.return_value = {
            "id": "user-123",
            "subscription_status": "active",
            "has_generator_access": True,
            "has_library_access": False,
        }
        mock_send.return_value = True

        request = _request("POST", "/login/submit/", {"email": "pago@exemplo.com"})
        response: TemplateResponse = login_submit(request)
        response.render()
        content: str = response.content.decode()

        self.assertNotIn("login-error", content)
        self.assertIn("Link enviado", content)
        mock_validate.assert_called_once()
        mock_send.assert_called_once()

    @patch("apps.auth.views.auth_service.validate_user", return_value=None)
    @patch("apps.auth.views.auth_service.check_rate_limit", return_value=None)
    @patch("apps.auth.views.auth_service.log_attempt")
    def test_user_not_found_returns_error(
        self,
        mock_log: MagicMock,
        mock_rate: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        """E-mail não encontrado retorna erro apropriado."""
        request = _request("POST", "/login/submit/", {"email": "inexistente@exemplo.com"})
        response: TemplateResponse = login_submit(request)
        response.render()
        content: str = response.content.decode()

        self.assertIn("login-error", content)
        self.assertIn("não encontrado", content.lower())

    @patch("apps.auth.views.auth_service.check_rate_limit", return_value=None)
    @patch("apps.auth.views.auth_service.log_attempt")
    def test_account_inactive_returns_error(
        self,
        mock_log: MagicMock,
        mock_rate: MagicMock,
    ) -> None:
        """FR-005: Conta inativa retorna erro apropriado com AccountInactiveError."""
        from apps.auth.services import AccountInactiveError

        request = _request("POST", "/login/submit/", {"email": "cancelado@exemplo.com"})

        with patch(
            "apps.auth.views.auth_service.validate_user",
            side_effect=AccountInactiveError("cancelado@exemplo.com", "canceled"),
        ):
            response: TemplateResponse = login_submit(request)

        response.render()
        content: str = response.content.decode()
        self.assertIn("login-error", content)
        # FR-016: Verifica que a razão da rejeição é registrada
        self.assertEqual(mock_log.call_args[0][3], "account_inactive")

    @patch("apps.auth.views.auth_service.validate_user", return_value={"id": "123"})
    @patch("apps.auth.views.auth_service.send_magic_link", return_value=False)
    @patch("apps.auth.views.auth_service.check_rate_limit", return_value=None)
    @patch("apps.auth.views.auth_service.log_attempt")
    def test_send_failure_returns_error(
        self,
        mock_log: MagicMock,
        mock_rate: MagicMock,
        mock_send: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        """Falha no envio do Magic Link retorna erro."""
        request = _request("POST", "/login/submit/", {"email": "pago@exemplo.com"})
        response: TemplateResponse = login_submit(request)
        response.render()
        content: str = response.content.decode()

        self.assertIn("login-error", content)
        self.assertIn("não foi possível", content.lower())
