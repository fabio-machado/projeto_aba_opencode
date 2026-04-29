"""
T018 — PWA Session Refresh (US2 / FR-009).

Testa a renovação de sessão no contexto PWA (cookie-based).
O PWA envia o refresh_token via cookie HTTP-only e espera receber
um novo access_token para manter a sessão persistente.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.auth.services import refresh_session

from .conftest import (
    TEST_SETTINGS,
    TEST_USER_ID,
    mock_client as _mock_client,
)


@override_settings(**TEST_SETTINGS)
class PwaSessionRefreshTest(TestCase):
    """Testes de renovação de sessão no contexto PWA (cookie-based)."""

    @patch("apps.auth.services._get_admin_client")
    def test_refresh_com_refresh_cookie_valido_retorna_sessao(
        self, mock_get: MagicMock
    ) -> None:
        """Given refresh_token válido via cookie, When renovado, Then retorna access_token."""
        client: MagicMock = _mock_client()
        mock_session: MagicMock = MagicMock()
        mock_session.access_token = "new-access-token-123"
        mock_session.refresh_token = "new-refresh-token-456"
        mock_session.user.id = TEST_USER_ID
        mock_resp: MagicMock = MagicMock()
        mock_resp.session = mock_session
        client.auth.refresh_session.return_value = mock_resp
        mock_get.return_value = client

        result: dict | None = refresh_session("valid-refresh-token")

        self.assertIsNotNone(result)
        self.assertEqual(result["access_token"], "new-access-token-123")
        self.assertEqual(result["refresh_token"], "new-refresh-token-456")

    @patch("apps.auth.services._get_admin_client")
    def test_refresh_com_cookie_expirado_retorna_none(
        self, mock_get: MagicMock
    ) -> None:
        """Given refresh_token expirado, When renovado, Then retorna None."""
        client: MagicMock = _mock_client()
        mock_resp: MagicMock = MagicMock()
        mock_resp.session = None
        client.auth.refresh_session.return_value = mock_resp
        mock_get.return_value = client

        result: dict | None = refresh_session("expired-refresh-token")

        self.assertIsNone(result)

    @patch("apps.auth.services._get_admin_client")
    def test_refresh_com_erro_no_supabase_retorna_none(
        self, mock_get: MagicMock
    ) -> None:
        """Given erro na API Supabase, When renovado, Then retorna None graciosamente."""
        client: MagicMock = _mock_client()
        client.auth.refresh_session.side_effect = Exception("Token revoked")
        mock_get.return_value = client

        result: dict | None = refresh_session("bad-token")

        self.assertIsNone(result)
