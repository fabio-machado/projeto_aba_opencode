"""
T5 — Edge Cases & Audit (FR-008, FR-013, FR-014).

Cobre:
- Falha na criação do auth user propaga erro
- Falha na criação do profile retorna erro
- Audit logs registrados no fluxo completo (user_created, magic_link_sent, webhook_processed)
- Audit log para user_exists
- has_active_session fallback (list_sessions indisponível → get_user_by_id)
- Auth callback view (cookie + redirect)
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.payments.services import (
    has_active_session,
    log_audit_event,
    process_payment_intent_succeeded,
)

# ---------------------------------------------------------------------------
# Dados de teste
# ---------------------------------------------------------------------------

VALID_EVENT: dict = {
    "id": "evt_test_001",
    "type": "payment_intent.succeeded",
    "data": {
        "object": {
            "id": "pi_test_001",
            "status": "succeeded",
            "customer": "cus_test_001",
            "receipt_email": "novo@exemplo.com",
            "metadata": {"cpf": "123.456.789-00"},
            "charges": {
                "data": [
                    {
                        "billing_details": {
                            "name": "João da Silva",
                            "email": "novo@exemplo.com",
                        }
                    }
                ]
            },
        }
    },
}

TEST_USER_ID: str = "00000000-0000-0000-0000-000000000001"

TEST_SETTINGS: dict = {
    "STRIPE_WEBHOOK_SECRET": "whsec_test_secret",
    "STRIPE_SECRET_KEY": "sk_test_key",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "eyJ.test.service",
    "SUPABASE_ANON_KEY": "eyJ.test.anon",
    "APP_URL": "http://localhost:8000",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_supabase_client() -> MagicMock:
    """Retorna um MagicMock configurado como cliente Supabase."""
    mock_client: MagicMock = MagicMock()

    mock_client.auth.admin.list_users.return_value = MagicMock(users=[])

    mock_user: MagicMock = MagicMock()
    mock_user.id = TEST_USER_ID
    mock_client.auth.admin.create_user.return_value = MagicMock(user=mock_user)

    def _table_handler(name: str) -> MagicMock:
        t: MagicMock = MagicMock()
        if name == "processed_webhook_events":
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                MagicMock(data=[])
            )
            t.insert.return_value.execute.return_value = MagicMock(data=[])
        elif name == "profiles":
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                MagicMock(data=[])
            )
            t.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": TEST_USER_ID, "email": "novo@exemplo.com"}]
            )
        elif name == "audit_logs":
            t.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": TEST_USER_ID}]
            )
        elif name == "magic_link_logs":
            t.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": TEST_USER_ID}]
            )
        return t

    mock_client.table.side_effect = _table_handler
    return mock_client


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class EdgeCaseTests(TestCase):
    """Testes de cenários de borda e erro."""

    @patch("apps.payments.services._get_admin_client")
    def test_falha_criacao_auth_user_propaga_erro(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given falha na criação do auth user, When processado, Then exceção propaga (view retorna 500)."""
        mock_client: MagicMock = MagicMock()
        mock_client.auth.admin.list_users.return_value = MagicMock(users=[])
        # Erro genérico (não "already registered") — propaga via raise
        mock_client.auth.admin.create_user.side_effect = RuntimeError(
            "Supabase Auth API unreachable"
        )
        mock_get_client.return_value = mock_client

        # O serviço não captura exceções de create_supabase_user —
        # elas propagam para a view que retorna HTTP 500 (FR-014)
        with self.assertRaises(RuntimeError):
            process_payment_intent_succeeded(VALID_EVENT)

    @patch("apps.payments.services._get_admin_client")
    def test_falha_criacao_profile_retorna_erro(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given falha na inserção do profile, When processado, Then retorna erro."""
        mock_client: MagicMock = MagicMock()
        mock_client.auth.admin.list_users.return_value = MagicMock(users=[])

        mock_user: MagicMock = MagicMock()
        mock_user.id = TEST_USER_ID
        mock_client.auth.admin.create_user.return_value = MagicMock(user=mock_user)

        # Profile insert falha
        def _table_handler(name: str) -> MagicMock:
            t: MagicMock = MagicMock()
            if name == "profiles":
                t.insert.return_value.execute.side_effect = Exception(
                    "Constraint violation"
                )
            return t

        mock_client.table.side_effect = _table_handler
        mock_get_client.return_value = mock_client

        result: dict = process_payment_intent_succeeded(VALID_EVENT)

        self.assertEqual(result["status"], "error")
        self.assertIn("profile", result["message"].lower())

    @patch("apps.payments.services._get_admin_client")
    @patch("apps.payments.services.send_magic_link", return_value=True)
    @patch("apps.payments.services.log_audit_event")
    def test_audit_events_fluxo_criacao_completo(
        self,
        mock_log_audit: MagicMock,
        mock_send: MagicMock,
        mock_get_client: MagicMock,
    ) -> None:
        """Given novo usuário criado, When fluxo completo, Then 3 audit events registrados."""
        mock_client: MagicMock = _make_mock_supabase_client()
        mock_get_client.return_value = mock_client

        process_payment_intent_succeeded(VALID_EVENT)

        # Verifica os 3 eventos de auditoria
        audit_calls = mock_log_audit.call_args_list
        actions: list[str] = [
            call.kwargs["action"] for call in audit_calls
        ]

        self.assertIn("user_created", actions)
        self.assertIn("magic_link_sent", actions)
        self.assertIn("webhook_processed", actions)

        # Verifica que user_id está em todas as chamadas
        for call in audit_calls:
            self.assertEqual(call.kwargs["user_id"], TEST_USER_ID)

    @patch("apps.payments.services._get_admin_client")
    @patch("apps.payments.services.log_audit_event")
    def test_audit_event_user_exists_registrado(
        self,
        mock_log_audit: MagicMock,
        mock_get_client: MagicMock,
    ) -> None:
        """Given usuário já existe, When webhook, Then audit event 'user_exists' registrado."""
        mock_client: MagicMock = _make_mock_supabase_client()
        mock_get_client.return_value = mock_client

        # Sobrescreve profiles para retornar usuário existente
        def _table_handler(name: str) -> MagicMock:
            t: MagicMock = MagicMock()
            if name == "profiles":
                t.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                    MagicMock(data=[{"id": TEST_USER_ID, "email": "novo@exemplo.com"}])
                )
            return t

        mock_client.table.side_effect = _table_handler

        process_payment_intent_succeeded(VALID_EVENT)

        # Verifica que log_audit_event foi chamado com user_exists
        user_exists_calls = [
            c
            for c in mock_log_audit.call_args_list
            if c.kwargs.get("action") == "user_exists"
        ]
        self.assertEqual(len(user_exists_calls), 1)
        self.assertEqual(
            user_exists_calls[0].kwargs["user_id"], TEST_USER_ID
        )

    @patch("apps.payments.services._get_admin_client")
    def test_has_active_session_fallback_get_user_by_id(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given list_sessions dispara AttributeError, When, Then fallback get_user_by_id."""
        mock_client: MagicMock = MagicMock()
        # list_sessions não disponível → AttributeError
        mock_client.auth.admin.list_sessions.side_effect = AttributeError(
            "not available"
        )

        mock_user: MagicMock = MagicMock()
        mock_user.last_sign_in_at = "2026-04-01T00:00:00Z"
        mock_client.auth.admin.get_user_by_id.return_value = MagicMock(
            user=mock_user
        )

        mock_get_client.return_value = mock_client

        result: bool = has_active_session(TEST_USER_ID)

        self.assertTrue(result)
        # Deve ter chamado o fallback
        mock_client.auth.admin.get_user_by_id.assert_called_once_with(
            TEST_USER_ID
        )

    @patch("apps.payments.services._get_admin_client")
    def test_has_active_session_list_sessions_erro_generico(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given list_sessions lança Exception genérica, When, Then retorna False."""
        mock_client: MagicMock = MagicMock()
        mock_client.auth.admin.list_sessions.side_effect = Exception(
            "API unreachable"
        )
        mock_get_client.return_value = mock_client

        result: bool = has_active_session(TEST_USER_ID)

        self.assertFalse(result)

    @override_settings(**TEST_SETTINGS)
    def test_auth_callback_valido_redirect_com_cookie(self) -> None:
        """Given magic link callback válido, When GET /auth/callback, Then redirect + cookie."""
        import base64
        import json

        payload: bytes = json.dumps({"sub": TEST_USER_ID}).encode()
        payload_b64: str = (
            base64.urlsafe_b64encode(payload).decode().rstrip("=")
        )
        fake_token: str = f"header.{payload_b64}.signature"

        resp = self.client.get(
            reverse("auth_app:auth_callback"),
            {
                "access_token": fake_token,
                "refresh_token": "refresh_xxx",
                "type": "magiclink",
            },
        )

        # Deve redirecionar para /dashboard
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard", resp.url)

        # Deve setar cookie HTTP-only
        cookie: str = resp.cookies.get("supabase_session").value
        self.assertEqual(cookie, fake_token)

    @override_settings(**TEST_SETTINGS)
    def test_auth_callback_invalido_redirect_login(self) -> None:
        """Given callback inválido (token_type errado), When GET, Then redirect /login."""
        resp = self.client.get(
            reverse("auth_app:auth_callback"),
            {
                "access_token": "any",
                "refresh_token": "any",
                "type": "signup",
            },
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)
