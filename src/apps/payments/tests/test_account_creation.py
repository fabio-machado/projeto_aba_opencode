"""
T2 — Criação Automática de Conta (US1 / FR-005, FR-009, FR-010, FR-012).

Cobre:
- Novo usuário: auth user + profile + magic link
- Usuário existente sem sessão: reenvia magic link (Spec-first — G1)
- Usuário existente com sessão: não reenvia (Spec-first — G1)
- Payment sem email: retorna erro
- Race condition no create_supabase_user
- Todos os campos do perfil persistidos corretamente
"""

import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from django.test import TestCase, override_settings

from apps.payments import services
from apps.payments.services import (
    _get_admin_client,
    create_profile,
    create_supabase_user,
    find_user_by_email,
    has_active_session,
    is_event_processed,
    log_audit_event,
    mark_event_processed,
    process_payment_intent_succeeded,
    send_magic_link,
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

EVENT_WITHOUT_EMAIL: dict = {
    "id": "evt_test_no_email",
    "type": "payment_intent.succeeded",
    "data": {
        "object": {
            "id": "pi_test_no_email",
            "customer": "cus_test_002",
            "charges": {
                "data": [{"billing_details": {"name": "Sem Email"}}]
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
    """Retorna um MagicMock configurado como cliente Supabase.

    Todas as tabelas retornam dados vazios por padrão (usuário inexistente,
    evento não processado). Testes podem sobrescrever comportamentos
    específicos.
    """
    mock_client: MagicMock = MagicMock()

    # Auth defaults
    mock_client.auth.admin.list_users.return_value = MagicMock(users=[])

    mock_user: MagicMock = MagicMock()
    mock_user.id = UUID(TEST_USER_ID)
    mock_client.auth.admin.create_user.return_value = MagicMock(user=mock_user)

    # Table routing: cada nome de tabela retorna um mock com respostas padrão
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
class AccountCreationTests(TestCase):
    """Testes de criação automática de conta via webhook."""

    @patch("apps.payments.services._get_admin_client")
    def test_novo_usuario_criado_com_sucesso(self, mock_get_client: MagicMock) -> None:
        """Given payment válido para novo email, When processado, Then cria auth user + profile + magic link."""
        mock_client: MagicMock = _make_mock_supabase_client()
        mock_get_client.return_value = mock_client

        with patch(
            "apps.payments.services.send_magic_link", return_value=True
        ) as mock_send:
            result: dict = process_payment_intent_succeeded(VALID_EVENT)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "created")
        self.assertIn("user_id", result)

        # Auth user criado uma vez
        mock_client.auth.admin.create_user.assert_called_once()

        # Profile inserido com campos corretos
        insert_calls = mock_client.table.call_args_list
        profiles_inserted: bool = any(
            call.args[0] == "profiles" for call in insert_calls
        )
        self.assertTrue(profiles_inserted, "Profile deve ser inserido")

        # Magic link enviado
        mock_send.assert_called_once_with(
            email="novo@exemplo.com",
            user_id=TEST_USER_ID,
            triggered_by="webhook_auto_account",
        )

    @unittest.expectedFailure  # G1: has_active_session() não é chamado no código atual
    @patch("apps.payments.services._get_admin_client")
    @patch("apps.payments.services.has_active_session")
    def test_usuario_existente_sem_sessao_reenvia_magic_link(
        self, mock_has_session: MagicMock, mock_get_client: MagicMock
    ) -> None:
        """Given usuário existente sem sessão ativa, When webhook, Then reenvia magic link."""
        mock_client: MagicMock = _make_mock_supabase_client()
        mock_get_client.return_value = mock_client

        # Usuário já existe na tabela profiles
        existing_data: list[dict] = [
            {"id": TEST_USER_ID, "email": "novo@exemplo.com"}
        ]

        def _table_handler(name: str) -> MagicMock:
            t: MagicMock = MagicMock()
            if name == "profiles":
                t.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                    MagicMock(data=existing_data)
                )
            return t

        mock_client.table.side_effect = _table_handler

        # Sem sessão ativa
        mock_has_session.return_value = False

        with patch(
            "apps.payments.services.send_magic_link", return_value=True
        ) as mock_send:
            result: dict = process_payment_intent_succeeded(VALID_EVENT)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "idempotent")
        mock_client.auth.admin.create_user.assert_not_called()

        # G1: Estas assertions falham porque has_active_session nunca é chamado
        mock_has_session.assert_called_once_with(TEST_USER_ID)
        mock_send.assert_called_once()  # Deve reenviar magic link

    @unittest.expectedFailure  # G1: has_active_session() não é chamado no código atual
    @patch("apps.payments.services._get_admin_client")
    @patch("apps.payments.services.has_active_session")
    def test_usuario_existente_com_sessao_nao_reenvia_link(
        self, mock_has_session: MagicMock, mock_get_client: MagicMock
    ) -> None:
        """Given usuário com sessão ativa, When webhook, Then não reenvia magic link."""
        mock_client: MagicMock = _make_mock_supabase_client()
        mock_get_client.return_value = mock_client

        existing_data: list[dict] = [
            {"id": TEST_USER_ID, "email": "novo@exemplo.com"}
        ]

        def _table_handler(name: str) -> MagicMock:
            t: MagicMock = MagicMock()
            if name == "profiles":
                t.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                    MagicMock(data=existing_data)
                )
            return t

        mock_client.table.side_effect = _table_handler

        # Sessão ativa
        mock_has_session.return_value = True

        with patch(
            "apps.payments.services.send_magic_link", return_value=True
        ) as mock_send:
            result: dict = process_payment_intent_succeeded(VALID_EVENT)

        self.assertEqual(result["status"], "success")

        # G1: Esta assertion falha porque has_active_session nunca é chamado
        mock_has_session.assert_called_once_with(TEST_USER_ID)
        mock_send.assert_not_called()  # Não deve reenviar

    @patch("apps.payments.services._get_admin_client")
    def test_payment_sem_email_retorna_erro(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given payment_intent sem email, When processado, Then retorna erro."""
        mock_client: MagicMock = MagicMock()
        mock_get_client.return_value = mock_client

        # is_event_processed é chamado antes da verificação de email
        def _table_handler(name: str) -> MagicMock:
            t: MagicMock = MagicMock()
            if name == "processed_webhook_events":
                t.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                    MagicMock(data=[])
                )
            return t

        mock_client.table.side_effect = _table_handler

        result: dict = process_payment_intent_succeeded(EVENT_WITHOUT_EMAIL)

        self.assertEqual(result["status"], "error")
        self.assertIn("email", result["message"].lower())

    @patch("apps.payments.services._get_admin_client")
    def test_criacao_auth_user_race_condition(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given create_supabase_user retorna dict vazio (race), When processado, Then idempotent."""
        mock_client: MagicMock = _make_mock_supabase_client()
        mock_get_client.return_value = mock_client

        # Simula race condition: create_user lança "already registered"
        mock_client.auth.admin.create_user.side_effect = Exception(
            "User already registered"
        )

        with patch("apps.payments.services.send_magic_link") as mock_send:
            result: dict = process_payment_intent_succeeded(VALID_EVENT)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "idempotent")
        self.assertIn("User already exists", result["message"])
        mock_send.assert_not_called()

    @patch("apps.payments.services._get_admin_client")
    def test_profile_criado_com_todos_campos(
        self, mock_get_client: MagicMock
    ) -> None:
        """Given payment com todos os dados, When perfil criado, Then todos os campos persistidos."""
        mock_client: MagicMock = MagicMock()
        mock_get_client.return_value = mock_client

        mock_user: MagicMock = MagicMock()
        mock_user.id = UUID(TEST_USER_ID)
        mock_client.auth.admin.create_user.return_value = MagicMock(user=mock_user)

        # Captura o insert na tabela profiles
        profiles_table: MagicMock = MagicMock()
        profiles_table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": TEST_USER_ID}]
        )

        mock_client.table.side_effect = lambda name: (
            profiles_table if name == "profiles" else MagicMock()
        )

        from apps.payments.services import create_profile as cp

        cp(
            user_id=TEST_USER_ID,
            email="novo@exemplo.com",
            full_name="João da Silva",
            stripe_customer_id="cus_test_001",
            cpf="123.456.789-00",
            subscription_status="active",
        )

        # Verifica os dados enviados para profiles.insert()
        insert_arg: dict = profiles_table.insert.call_args[0][0]
        self.assertEqual(insert_arg["id"], TEST_USER_ID)
        self.assertEqual(insert_arg["email"], "novo@exemplo.com")
        self.assertEqual(insert_arg["full_name"], "João da Silva")
        self.assertEqual(insert_arg["stripe_customer_id"], "cus_test_001")
        self.assertEqual(insert_arg["cpf"], "123.456.789-00")
        self.assertEqual(insert_arg["subscription_status"], "active")
