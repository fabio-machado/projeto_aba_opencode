"""
T4 — Magic Link (US4 / FR-010, FR-011).

Cobre:
- Magic link enviado para novo usuário
- Falha no envio não quebra o webhook
- Log de magic_link_logs registrado
- Validação de callback: sucesso, tipo inválido, tokens vazios, JWT malformado
"""

import base64
import json
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.payments.services import (
    process_payment_intent_succeeded,
    send_magic_link,
    validate_magic_link_callback,
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


def _build_fake_jwt(sub: str) -> str:
    """Constrói um JWT falso com o claim 'sub' fornecido."""
    payload_bytes: bytes = json.dumps({"sub": sub}).encode()
    payload_b64: str = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")
    return f"header.{payload_b64}.signature"


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class MagicLinkTests(TestCase):
    """Testes de envio e validação de magic link."""

    @patch("apps.payments.services._get_admin_client")
    def test_magic_link_enviado_para_novo_usuario(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given novo usuário criado, When processado, Then magic link enviado."""
        mock_client: MagicMock = _make_mock_supabase_client()
        mock_get_client.return_value = mock_client

        with patch(
            "apps.payments.services.send_magic_link", return_value=True
        ) as mock_send:
            process_payment_intent_succeeded(VALID_EVENT)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        self.assertEqual(call_kwargs["email"], "novo@exemplo.com")
        self.assertEqual(call_kwargs["triggered_by"], "webhook_auto_account")

    @patch("apps.payments.services._get_admin_client")
    def test_falha_envio_magic_link_nao_falha_webhook(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given falha no envio do email, When processado, Then webhook retorna success."""
        mock_client: MagicMock = _make_mock_supabase_client()
        mock_get_client.return_value = mock_client

        with patch(
            "apps.payments.services.send_magic_link", return_value=False
        ):
            result: dict = process_payment_intent_succeeded(VALID_EVENT)

        self.assertEqual(result["status"], "success")

    @patch("apps.payments.services._get_admin_client")
    def test_magic_link_log_registrado(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given magic link enviado, When fluxo executa, Then magic_link_logs inserido."""
        mock_client: MagicMock = _make_mock_supabase_client()
        mock_get_client.return_value = mock_client

        # Captura o insert na tabela magic_link_logs
        magic_link_table: MagicMock = MagicMock()
        magic_link_insert_spy: MagicMock = MagicMock()
        magic_link_insert_spy.execute.return_value = MagicMock(
            data=[{"id": TEST_USER_ID}]
        )
        magic_link_table.insert.return_value = magic_link_insert_spy

        mock_client.table.side_effect = lambda name: (
            magic_link_table
            if name == "magic_link_logs"
            else _make_mock_supabase_client().table.side_effect(name)
        )

        process_payment_intent_succeeded(VALID_EVENT)

        # Verifica que magic_link_logs.insert foi chamado com os dados corretos
        magic_link_table.insert.assert_called_once()
        inserted: dict = magic_link_table.insert.call_args[0][0]
        self.assertEqual(inserted["user_id"], TEST_USER_ID)
        self.assertEqual(inserted["email"], "novo@exemplo.com")
        self.assertEqual(inserted["triggered_by"], "webhook_auto_account")
        self.assertEqual(inserted["status"], "sent")

    def test_validate_callback_valido(self) -> None:
        """Given tokens válidos, When validado, Then retorna user_id."""
        fake_token: str = _build_fake_jwt(TEST_USER_ID)

        result: dict | None = validate_magic_link_callback(
            access_token=fake_token,
            refresh_token="refresh_xxx",
            token_type="magiclink",
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["user_id"], TEST_USER_ID)

    def test_validate_callback_token_type_invalido(self) -> None:
        """Given token_type != magiclink, When validado, Then retorna None."""
        result: dict | None = validate_magic_link_callback(
            access_token="any_token",
            refresh_token="any_refresh",
            token_type="signup",
        )

        self.assertIsNone(result)

    def test_validate_callback_tokens_vazios(self) -> None:
        """Given tokens vazios, When validado, Then retorna None."""
        result: dict | None = validate_magic_link_callback(
            access_token="",
            refresh_token="",
            token_type="magiclink",
        )

        self.assertIsNone(result)

    def test_validate_callback_jwt_malformado_base64_invalido(self) -> None:
        """Given JWT com payload inválido (base64), When validado, Then retorna None."""
        result: dict | None = validate_magic_link_callback(
            access_token="header.!!!invalid_base64!!!.signature",
            refresh_token="refresh_xxx",
            token_type="magiclink",
        )

        self.assertIsNone(result)

    def test_validate_callback_jwt_malformado_apenas_2_partes(self) -> None:
        """Given JWT com apenas 2 partes, When validado, Then retorna None."""
        result: dict | None = validate_magic_link_callback(
            access_token="apenas.duas_partes",
            refresh_token="refresh_xxx",
            token_type="magiclink",
        )

        self.assertIsNone(result)

    def test_validate_callback_jwt_sem_sub_claim(self) -> None:
        """Given JWT válido mas sem claim 'sub', When validado, Then retorna None."""
        payload_bytes: bytes = json.dumps({"outro": "valor"}).encode()
        payload_b64: str = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")
        token: str = f"header.{payload_b64}.signature"

        result: dict | None = validate_magic_link_callback(
            access_token=token,
            refresh_token="refresh_xxx",
            token_type="magiclink",
        )

        self.assertIsNone(result)
