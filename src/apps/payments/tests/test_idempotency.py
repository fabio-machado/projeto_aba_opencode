"""
T3 — Garantia de Idempotência (US3 / FR-006, FR-007, FR-008).

Cobre:
- Mesmo evento processado 2x → apenas 1 usuário criado
- Evento já registrado em processed_webhook_events → idempotent
- mark_event_processed com duplicate key → retorna True (idempotente)
- mark_event_processed com erro inesperado → retorna False
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.payments.services import (
    is_event_processed,
    mark_event_processed,
    process_payment_intent_succeeded,
)

from .conftest import (  # noqa: E402
    VALID_EVENT,
    TEST_USER_ID,
    TEST_SETTINGS,
    make_mock_supabase_client as _make_mock_supabase_client,
)


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class IdempotencyTests(TestCase):
    """Testes de garantia de idempotência no processamento de webhooks."""

    @patch("apps.payments.services.is_event_processed")
    @patch("apps.payments.services._get_admin_client")
    def test_mesmo_evento_duas_vezes_apenas_um_usuario(
        self, mock_get_client: MagicMock, mock_is_processed: MagicMock
    ) -> None:
        """Given mesmo evt_id 2x, When processado, Then apenas 1 usuário criado."""
        mock_client: MagicMock = _make_mock_supabase_client()
        mock_get_client.return_value = mock_client

        # Primeira chamada: evento não processado → cria usuário
        # Segunda chamada: evento já processado → idempotent
        mock_is_processed.side_effect = [False, True]

        with patch(
            "apps.payments.services.send_magic_link", return_value=True
        ):
            result1: dict = process_payment_intent_succeeded(VALID_EVENT)
            self.assertEqual(result1["action"], "created")

            result2: dict = process_payment_intent_succeeded(VALID_EVENT)
            self.assertEqual(result2["action"], "idempotent")

        # create_user chamado apenas 1 vez
        self.assertEqual(
            mock_client.auth.admin.create_user.call_count, 1
        )

    @patch("apps.payments.services._get_admin_client")
    def test_evento_ja_registrado_retorna_idempotent(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given evento já na tabela processed_webhook_events, When processado, Then idempotent."""
        mock_client: MagicMock = _make_mock_supabase_client()
        mock_get_client.return_value = mock_client

        # Sobrescreve resposta da tabela processed_webhook_events como já existente
        def _table_handler(name: str) -> MagicMock:
            t: MagicMock = MagicMock()
            if name == "processed_webhook_events":
                # select retorna o evento já processado
                t.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                    MagicMock(data=[{"stripe_event_id": "evt_test_001"}])
                )
            return t

        mock_client.table.side_effect = _table_handler

        result: dict = process_payment_intent_succeeded(VALID_EVENT)

        self.assertEqual(result["action"], "idempotent")
        self.assertEqual(result["status"], "success")
        mock_client.auth.admin.create_user.assert_not_called()

    def test_mark_event_processed_duplicate_key_nao_falha(self) -> None:
        """Given insert com erro de unique constraint, When mark_event_processed, Then retorna True."""
        mock_client: MagicMock = MagicMock()
        # insert.execute() lança erro de chave duplicada
        mock_client.table.return_value.insert.return_value.execute.side_effect = (
            Exception("duplicate key value violates unique constraint")
        )

        with patch(
            "apps.payments.services._get_admin_client",
            return_value=mock_client,
        ):
            result: bool = mark_event_processed(
                "evt_test_001", "payment_intent.succeeded", "success"
            )

        self.assertTrue(result)

    def test_mark_event_processed_erro_inesperado_retorna_false(self) -> None:
        """Given insert com erro de conexão, When mark_event_processed, Then retorna False."""
        mock_client: MagicMock = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = (
            ConnectionError("Database connection lost")
        )

        with patch(
            "apps.payments.services._get_admin_client",
            return_value=mock_client,
        ):
            result: bool = mark_event_processed(
                "evt_test_003", "payment_intent.succeeded", "success"
            )

        self.assertFalse(result)
