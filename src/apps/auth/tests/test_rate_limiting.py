"""
T2 — Rate Limiting & Enumeration (US5 / FR-011, FR-015, FR-016).

Cobre:
- check_rate_limit bloqueia por e-mail (3 tentativas/60s)
- check_rate_limit bloqueia por IP (10 tentativas/60s)
- check_rate_limit detecta enumeração (5+ e-mails distintos/60s)
- check_rate_limit retorna None quando abaixo dos limites
- log_attempt registra tentativas com todos os campos
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.auth.services import check_rate_limit, log_attempt


# ---------------------------------------------------------------------------
# check_rate_limit
# ---------------------------------------------------------------------------


class RateLimitEmailTest(TestCase):
    """Rate limiting por e-mail."""

    @patch("apps.auth.services._get_admin_client")
    def test_rate_limit_email_below_threshold(self, mock_client: MagicMock) -> None:
        """Abaixo de 3 tentativas, retorna None."""
        mock_resp = MagicMock()
        mock_resp.count = 2
        # Passa a 1ª verificação (email), 2ª (IP) e 3ª (enumeração)
        mock_client.return_value.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_resp
        result = check_rate_limit("teste@exemplo.com", "192.168.0.1")
        self.assertIsNone(result)

    @patch("apps.auth.services._get_admin_client")
    def test_rate_limit_email_blocked(self, mock_client: MagicMock) -> None:
        """3+ tentativas no mesmo e-mail em 60s → bloqueado."""
        mock_resp = MagicMock()
        mock_resp.count = 3
        mock_client.return_value.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_resp
        result = check_rate_limit("teste@exemplo.com", "192.168.0.1")
        self.assertEqual(result, "rate_limit_email")


class RateLimitIPTest(TestCase):
    """Rate limiting por IP."""

    @patch("apps.auth.services._get_admin_client")
    def test_rate_limit_ip_blocked(self, mock_client: MagicMock) -> None:
        """10+ tentativas do mesmo IP em 60s → bloqueado."""
        # Primeira chamada: email count = 1 (passa)
        # Segunda chamada: ip count = 10 (bloqueia)
        mock_email = MagicMock()
        mock_email.count = 1
        mock_ip = MagicMock()
        mock_ip.count = 10

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.gte.return_value.execute.side_effect = [
            mock_email,
            mock_ip,
        ]
        mock_client.return_value.table.return_value = mock_table

        result = check_rate_limit("teste@exemplo.com", "192.168.0.99")
        self.assertEqual(result, "rate_limit_ip")


class EnumerationDetectionTest(TestCase):
    """Detecção de enumeração."""

    @patch("apps.auth.services._get_admin_client")
    def test_enumeration_detected(self, mock_client: MagicMock) -> None:
        """5+ e-mails distintos rejeitados do mesmo IP em 60s → enumeração."""
        mock_email = MagicMock()
        mock_email.count = 1
        mock_ip = MagicMock()
        mock_ip.count = 1

        mock_enum = MagicMock()
        mock_enum.data = [
            {"email": "a@test.com"},
            {"email": "b@test.com"},
            {"email": "c@test.com"},
            {"email": "d@test.com"},
            {"email": "e@test.com"},
        ]

        # A 3ª chamada à chain é a de enumeração (depois de email e IP)
        call_count = 0
        mock_execute = MagicMock()

        def side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_email
            elif call_count == 2:
                return mock_ip
            else:
                return mock_enum

        mock_execute.execute.side_effect = side_effect
        # Todas as chains retornam o mesmo execute mock
        mock_chain = MagicMock()
        mock_chain.eq.return_value = mock_chain
        mock_chain.gte.return_value = mock_chain
        mock_chain.execute = mock_execute.execute
        mock_chain.select.return_value = mock_chain

        mock_client.return_value.table.return_value = mock_chain
        result = check_rate_limit("f@test.com", "192.168.0.100")
        self.assertEqual(result, "enumeration_detected")

    @patch("apps.auth.services._get_admin_client")
    def test_enumeration_not_detected_below_threshold(self, mock_client: MagicMock) -> None:
        """Menos de 5 e-mails distintos → sem enumeração."""
        mock_email = MagicMock()
        mock_email.count = 1
        mock_ip = MagicMock()
        mock_ip.count = 1

        mock_enum = MagicMock()
        mock_enum.data = [
            {"email": "a@test.com"},
            {"email": "b@test.com"},
        ]  # Apenas 2 e-mails distintos

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.gte.return_value.execute.side_effect = [
            mock_email,
            mock_ip,
            mock_enum,
        ]
        mock_client.return_value.table.return_value = mock_table

        result = check_rate_limit("c@test.com", "192.168.0.100")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# log_attempt
# ---------------------------------------------------------------------------


class LogAttemptTest(TestCase):
    """Registro de tentativas de login."""

    @patch("apps.auth.services._get_admin_client")
    def test_log_attempt_success(self, mock_client: MagicMock) -> None:
        """Tentativa bem-sucedida é registrada com result='success'."""
        log_attempt("teste@exemplo.com", "192.168.0.1", "success", None)
        mock_client.return_value.table.assert_called_with("login_attempts")
        mock_client.return_value.table.return_value.insert.assert_called_once()

    @patch("apps.auth.services._get_admin_client")
    def test_log_attempt_rejected_with_reason(self, mock_client: MagicMock) -> None:
        """Tentativa rejeitada registra o motivo da recusa."""
        log_attempt("teste@exemplo.com", "192.168.0.1", "rejected", "email_not_found")
        insert_call = mock_client.return_value.table.return_value.insert.call_args[0][0]
        self.assertEqual(insert_call["result"], "rejected")
        self.assertEqual(insert_call["rejection_reason"], "email_not_found")

    @patch("apps.auth.services._get_admin_client")
    def test_rate_limit_error_graceful_fallback(self, mock_client: MagicMock) -> None:
        """Erro na query de rate limit faz fallback (retorna None)."""
        mock_client.return_value.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.side_effect = Exception("DB error")
        result = check_rate_limit("teste@exemplo.com", "192.168.0.1")
        self.assertIsNone(result)
