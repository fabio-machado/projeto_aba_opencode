"""
Testes de Service Layer — payments (US1–US4 / FR-001–FR-018).

Cobre standalone para cada função pública do services.py:
- log_audit_event: sucesso, falha não-fatal
- validate_stripe_signature: sucesso, assinatura inválida
- create_supabase_user: sucesso, usuário já existe, erro propaga
- create_profile: sucesso (campos obrigatórios + opcionais), falha sem dados
- find_user_by_email: encontrado, não encontrado, normalização, erro de query
- send_magic_link: sucesso, falha, log de magic_link_logs
- is_event_processed: encontrado, não encontrado
- has_active_session: já coberto em test_edge_cases.py
- mark_event_processed: já coberto em test_idempotency.py
- validate_magic_link_callback: já coberto em test_magic_link.py
- process_payment_intent_succeeded: já coberto em test_account_creation.py
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import stripe
from django.test import TestCase, override_settings

from apps.payments.services import (
    create_profile,
    create_supabase_user,
    find_user_by_email,
    is_event_processed,
    log_audit_event,
    send_magic_link,
    validate_stripe_signature,
)

from .conftest import TEST_USER_ID, TEST_SETTINGS  # noqa: E402

# ---------------------------------------------------------------------------
# Constantes locais (não compartilhadas)
# ---------------------------------------------------------------------------

TEST_EMAIL: str = "novo@exemplo.com"
TEST_FULL_NAME: str = "João da Silva"


# ---------------------------------------------------------------------------
# Helpers — espelham os padrões de apps.auth.tests.test_services
# ---------------------------------------------------------------------------


def _mock_client() -> MagicMock:
    """Retorna um MagicMock configurado como cliente Supabase.

    Todas as tabelas retornam dados vazios por padrão. Testes podem
    sobrescrever ``client.table.side_effect`` com seu próprio handler.
    """
    client: MagicMock = MagicMock()

    def _table_handler(name: str) -> MagicMock:
        t: MagicMock = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.limit.return_value = t
        t.order.return_value = t
        t.insert.return_value = t
        t.execute.return_value = MagicMock(data=[])
        return t

    client.table.side_effect = _table_handler
    client.auth.sign_in_with_otp = MagicMock(return_value=None)

    mock_user: MagicMock = MagicMock()
    mock_user.id = TEST_USER_ID
    client.auth.admin.create_user = MagicMock(
        return_value=MagicMock(user=mock_user)
    )

    return client


def _mock_table_with_data(
    client: MagicMock, table_name: str, data: list[dict]
) -> None:
    """Sobrescreve o side_effect de client.table para retornar dados em uma tabela.

    Args:
        client: MagicMock do cliente Supabase.
        table_name: Nome da tabela.
        data: Dados que a query deve retornar.
    """

    def _handler(name: str) -> MagicMock:
        t: MagicMock = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.limit.return_value = t
        t.order.return_value = t
        t.insert.return_value = t
        t.execute.return_value = MagicMock(
            data=data if name == table_name else []
        )
        return t

    client.table.side_effect = _handler


def _capture_insert_mock(
    client: MagicMock, table_name: str
) -> MagicMock:
    """Configura o mock do cliente para capturar o mock de insert de uma tabela.

    Retorna o MagicMock da tabela alvo para que o teste possa inspecionar
    ``.insert.call_args`` após a execução.

    Args:
        client: MagicMock do cliente Supabase.
        table_name: Nome da tabela cujo insert deve ser capturado.

    Returns:
        O MagicMock da tabela (persistente — não recriado a cada chamada).
    """
    captured_table: MagicMock = MagicMock()
    captured_insert_chain: MagicMock = MagicMock()
    captured_insert_chain.execute.return_value = MagicMock(data=[])
    captured_table.insert.return_value = captured_insert_chain

    def _handler(name: str) -> MagicMock:
        if name == table_name:
            return captured_table
        # Para outras tabelas, cria mock genérico com dados vazios
        t: MagicMock = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.limit.return_value = t
        t.order.return_value = t
        t.insert.return_value = t
        t.execute.return_value = MagicMock(data=[])
        return t

    client.table.side_effect = _handler

    return captured_table


# ---------------------------------------------------------------------------
# log_audit_event (T023b — Constitution IV: Auditabilidade)
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class LogAuditEventTest(TestCase):
    """Testes de registro de eventos de auditoria."""

    @patch("apps.payments.services._get_admin_client")
    def test_sucesso_insere_registro_retorna_true(
        self, mock_get: MagicMock
    ) -> None:
        """FR-008: Given user_id e ação válidos, When registrado, Then retorna True."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client

        # Captura o mock de insert da audit_logs
        audit_table: MagicMock = _capture_insert_mock(client, "audit_logs")

        result: bool = log_audit_event(
            user_id=TEST_USER_ID,
            action="user_created",
            metadata={"event_id": "evt_001"},
        )

        self.assertTrue(result)
        # Verifica que o insert foi chamado com os dados corretos
        insert_chain = audit_table.insert
        insert_chain.assert_called_once()
        record: dict = insert_chain.call_args[0][0]
        self.assertEqual(record["user_id"], TEST_USER_ID)
        self.assertEqual(record["action"], "user_created")
        self.assertEqual(record["metadata"]["event_id"], "evt_001")

    @patch("apps.payments.services._get_admin_client")
    def test_falha_nao_propaga_erro_retorna_false(
        self, mock_get: MagicMock
    ) -> None:
        """FR-008: Given erro no Supabase, When registrado, Then retorna False (não-fatal)."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client

        # Sobrescreve a audit_logs para lançar erro no execute
        audit_table: MagicMock = _capture_insert_mock(client, "audit_logs")
        audit_table.insert.return_value.execute.side_effect = ConnectionError(
            "DB offline"
        )

        result: bool = log_audit_event(
            user_id=TEST_USER_ID, action="webhook_processed"
        )

        self.assertFalse(result)


# ---------------------------------------------------------------------------
# validate_stripe_signature (FR-001, FR-002)
# ---------------------------------------------------------------------------


class ValidateStripeSignatureTest(TestCase):
    """Testes de validação de assinatura do webhook Stripe."""

    def test_assinatura_valida_retorna_evento(self) -> None:
        """FR-001: Given payload e signature válidos, When validado, Then retorna dict do evento."""
        expected: dict = {
            "id": "evt_test_001",
            "type": "payment_intent.succeeded",
            "data": {"object": {}},
        }

        mock_event: MagicMock = MagicMock()
        mock_event.to_dict.return_value = expected

        with patch(
            "stripe.Webhook.construct_event", return_value=mock_event
        ) as mock_construct:
            result: dict = validate_stripe_signature(
                payload=b'{"id":"evt_test_001"}',
                signature="t=123,v1=abc",
                webhook_secret="whsec_test",
            )

        self.assertEqual(result["id"], "evt_test_001")
        self.assertEqual(result["type"], "payment_intent.succeeded")
        mock_construct.assert_called_once_with(
            payload=b'{"id":"evt_test_001"}',
            sig_header="t=123,v1=abc",
            secret="whsec_test",
        )

    def test_assinatura_invalida_propaga_erro(self) -> None:
        """FR-002: Given assinatura inválida, When validado, Then lança SignatureVerificationError."""
        with patch(
            "stripe.Webhook.construct_event"
        ) as mock_construct:
            mock_construct.side_effect = stripe.error.SignatureVerificationError(
                "Invalid signature", sig_header="t=xxx,v1=yyy"
            )

            with self.assertRaises(stripe.error.SignatureVerificationError):
                validate_stripe_signature(
                    payload=b"payload",
                    signature="t=xxx,v1=yyy",
                    webhook_secret="whsec_test",
                )


# ---------------------------------------------------------------------------
# create_supabase_user (FR-005 / T011)
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class CreateSupabaseUserTest(TestCase):
    """Testes de criação de usuário no Supabase Auth (Admin API)."""

    @patch("apps.payments.services._get_admin_client")
    def test_criacao_bem_sucedida_retorna_id_e_email(
        self, mock_get: MagicMock
    ) -> None:
        """FR-005: Given email e nome válidos, When criado, Then retorna id (str) e email."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client

        result: dict = create_supabase_user(
            email=TEST_EMAIL, full_name=TEST_FULL_NAME
        )

        self.assertEqual(result["id"], TEST_USER_ID)
        self.assertEqual(result["email"], TEST_EMAIL)
        # Verifica que os atributos corretos foram passados
        create_call = client.auth.admin.create_user.call_args
        self.assertEqual(
            create_call.kwargs["attributes"]["email"], TEST_EMAIL
        )
        self.assertTrue(create_call.kwargs["attributes"]["email_confirm"])
        self.assertEqual(
            create_call.kwargs["attributes"]["user_metadata"]["full_name"],
            TEST_FULL_NAME,
        )

    @patch("apps.payments.services._get_admin_client")
    def test_usuario_ja_existente_retorna_dict_vazio(
        self, mock_get: MagicMock
    ) -> None:
        """FR-005: Given email já registrado, When criado, Then retorna dict vazio."""
        client: MagicMock = _mock_client()
        client.auth.admin.create_user.side_effect = Exception(
            "User already registered"
        )
        mock_get.return_value = client

        result: dict = create_supabase_user(
            email=TEST_EMAIL, full_name=TEST_FULL_NAME
        )

        self.assertEqual(result, {})

    @patch("apps.payments.services._get_admin_client")
    def test_usuario_ja_existente_string_alternativa_retorna_dict_vazio(
        self, mock_get: MagicMock
    ) -> None:
        """FR-005: Given email já registrado com mensagem "already exists", When criado, Then retorna dict vazio.

        Cobre a variante da string de erro do Supabase Auth: "User already exists"
        (diferente de "User already registered").
        """
        client: MagicMock = _mock_client()
        client.auth.admin.create_user.side_effect = Exception(
            "User already exists"
        )
        mock_get.return_value = client

        result: dict = create_supabase_user(
            email=TEST_EMAIL, full_name=TEST_FULL_NAME
        )

        self.assertEqual(result, {})

    @patch("apps.payments.services._get_admin_client")
    def test_usuario_ja_existente_string_duplicate_retorna_dict_vazio(
        self, mock_get: MagicMock
    ) -> None:
        """FR-005: Given email já registrado com mensagem "duplicate", When criado, Then retorna dict vazio.

        Cobre a variante da string de erro do Supabase Auth: "duplicate key ..."
        """
        client: MagicMock = _mock_client()
        client.auth.admin.create_user.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )
        mock_get.return_value = client

        result: dict = create_supabase_user(
            email=TEST_EMAIL, full_name=TEST_FULL_NAME
        )

        self.assertEqual(result, {})

    @patch("apps.payments.services._get_admin_client")
    def test_erro_inesperado_propaga_excecao(
        self, mock_get: MagicMock
    ) -> None:
        """FR-005: Given erro genérico (não "already registered"), When criado, Then propaga exceção."""
        client: MagicMock = _mock_client()
        client.auth.admin.create_user.side_effect = RuntimeError(
            "Supabase Auth API unreachable"
        )
        mock_get.return_value = client

        with self.assertRaises(RuntimeError):
            create_supabase_user(email=TEST_EMAIL, full_name=TEST_FULL_NAME)


# ---------------------------------------------------------------------------
# create_profile (FR-005 / T012)
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class CreateProfileTest(TestCase):
    """Testes de criação de perfil na tabela profiles."""

    @patch("apps.payments.services._get_admin_client")
    def test_perfil_criado_com_todos_campos_obrigatorios(
        self, mock_get: MagicMock
    ) -> None:
        """FR-005: Given user_id, email e nome, When criado, Then perfil retornado."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client

        # Captura o mock de insert da profiles e configura retorno
        profiles_table: MagicMock = _capture_insert_mock(client, "profiles")
        profiles_table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": TEST_USER_ID, "email": TEST_EMAIL}]
        )

        result: dict = create_profile(
            user_id=TEST_USER_ID,
            email=TEST_EMAIL,
            full_name=TEST_FULL_NAME,
            subscription_status="active",
        )

        self.assertEqual(result["id"], TEST_USER_ID)
        self.assertEqual(result["email"], TEST_EMAIL)

        # Verifica que o insert foi chamado com os dados corretos
        insert_call = profiles_table.insert.call_args[0][0]
        self.assertEqual(insert_call["id"], TEST_USER_ID)
        self.assertEqual(insert_call["email"], TEST_EMAIL)
        self.assertEqual(insert_call["full_name"], TEST_FULL_NAME)
        self.assertEqual(insert_call["subscription_status"], "active")

    @patch("apps.payments.services._get_admin_client")
    def test_perfil_criado_com_campos_opcionais(
        self, mock_get: MagicMock
    ) -> None:
        """FR-005: Given stripe_customer_id e cpf, When criado, Then campos opcionais incluídos."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client

        profiles_table: MagicMock = _capture_insert_mock(client, "profiles")
        profiles_table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": TEST_USER_ID}]
        )

        result: dict = create_profile(
            user_id=TEST_USER_ID,
            email=TEST_EMAIL,
            full_name=TEST_FULL_NAME,
            stripe_customer_id="cus_test_001",
            cpf="123.456.789-00",
            subscription_status="active",
        )

        self.assertIsNotNone(result)

        insert_call = profiles_table.insert.call_args[0][0]
        self.assertEqual(insert_call["stripe_customer_id"], "cus_test_001")
        self.assertEqual(insert_call["cpf"], "123.456.789-00")

    @patch("apps.payments.services._get_admin_client")
    def test_falha_supabase_sem_dados_levanta_runtime_error(
        self, mock_get: MagicMock
    ) -> None:
        """FR-005: Given resposta vazia do Supabase, When criado, Then RuntimeError."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client

        profiles_table: MagicMock = _capture_insert_mock(client, "profiles")
        profiles_table.insert.return_value.execute.return_value = MagicMock(
            data=[]
        )

        with self.assertRaises(RuntimeError) as ctx:
            create_profile(
                user_id=TEST_USER_ID,
                email=TEST_EMAIL,
                full_name=TEST_FULL_NAME,
            )

        self.assertIn("Falha ao criar perfil", str(ctx.exception))


# ---------------------------------------------------------------------------
# find_user_by_email (FR-005 / T013)
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class FindUserByEmailTest(TestCase):
    """Testes de busca de usuário por e-mail na tabela profiles."""

    @patch("apps.payments.services._get_admin_client")
    def test_usuario_encontrado_retorna_dados(
        self, mock_get: MagicMock
    ) -> None:
        """FR-005: Given e-mail cadastrado, When buscado, Then retorna id e email."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client

        _mock_table_with_data(
            client,
            "profiles",
            [{"id": TEST_USER_ID, "email": TEST_EMAIL}],
        )

        result: dict | None = find_user_by_email(TEST_EMAIL)

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], TEST_USER_ID)
        self.assertEqual(result["email"], TEST_EMAIL)

    @patch("apps.payments.services._get_admin_client")
    def test_usuario_nao_encontrado_retorna_none(
        self, mock_get: MagicMock
    ) -> None:
        """FR-005: Given e-mail não cadastrado, When buscado, Then retorna None."""
        client: MagicMock = _mock_client()
        # Dados vazios por padrão
        mock_get.return_value = client

        result: dict | None = find_user_by_email("inexistente@exemplo.com")

        self.assertIsNone(result)

    @patch("apps.payments.services._get_admin_client")
    def test_email_normalizado_para_lowercase_na_query(
        self, mock_get: MagicMock
    ) -> None:
        """FR-003: E-mail é normalizado (lowercase) antes da query ao Supabase."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client

        captured_eq_arg: list = []

        def _handler(name: str) -> MagicMock:
            t: MagicMock = MagicMock()
            t.select.return_value = t
            t.limit.return_value = t
            t.insert.return_value = t
            t.execute.return_value = MagicMock(data=[])
            if name == "profiles":
                t.eq = MagicMock(
                    side_effect=lambda *a: (
                        captured_eq_arg.append(a) or t
                    )
                )
            return t

        client.table.side_effect = _handler

        # Envio com e-mail em maiúsculas (sem espaços — o código só faz .lower())
        find_user_by_email("NOVO@EXEMPLO.COM")

        self.assertTrue(len(captured_eq_arg) > 0, "eq() deve ser chamado")
        self.assertEqual(captured_eq_arg[0][1], "novo@exemplo.com")

    @patch("apps.payments.services._get_admin_client")
    def test_erro_de_query_retorna_none_graciosamente(
        self, mock_get: MagicMock
    ) -> None:
        """FR-005: Given erro na query Supabase, When buscado, Then retorna None."""
        client: MagicMock = _mock_client()
        client.table.return_value.execute.side_effect = Exception(
            "Connection timeout"
        )
        mock_get.return_value = client

        result: dict | None = find_user_by_email(TEST_EMAIL)

        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# send_magic_link (FR-010 / T014)
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class SendMagicLinkTest(TestCase):
    """Testes de envio de magic link via Supabase Auth."""

    @patch("apps.payments.services._get_admin_client")
    def test_envio_bem_sucedido_retorna_true(
        self, mock_get: MagicMock
    ) -> None:
        """FR-010: Given email e user_id válidos, When enviado, Then retorna True."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client

        # Sobrescreve magic_link_logs para aceitar o insert
        def _handler(name: str) -> MagicMock:
            t: MagicMock = MagicMock()
            t.select.return_value = t
            t.eq.return_value = t
            t.limit.return_value = t
            t.insert.return_value = t
            t.execute.return_value = MagicMock(data=[])
            return t

        client.table.side_effect = _handler

        result: bool = send_magic_link(
            email=TEST_EMAIL,
            user_id=TEST_USER_ID,
            triggered_by="webhook_auto_account",
        )

        self.assertTrue(result)
        client.auth.sign_in_with_otp.assert_called_once()
        call_args = client.auth.sign_in_with_otp.call_args[0][0]
        self.assertEqual(call_args["email"], TEST_EMAIL)
        self.assertIn(
            "auth/callback",
            call_args["options"]["email_redirect_to"],
        )

    @patch("apps.payments.services._get_admin_client")
    def test_falha_envio_retorna_false_nao_fatal(
        self, mock_get: MagicMock
    ) -> None:
        """FR-010: Given erro no sign_in_with_otp, When enviado, Then retorna False."""
        client: MagicMock = _mock_client()
        client.auth.sign_in_with_otp.side_effect = Exception("SMTP error")
        mock_get.return_value = client

        result: bool = send_magic_link(
            email=TEST_EMAIL,
            user_id=TEST_USER_ID,
        )

        self.assertFalse(result)

    @patch("apps.payments.services._get_admin_client")
    def test_magic_link_log_registrado_no_envio(
        self, mock_get: MagicMock
    ) -> None:
        """FR-010: Given envio bem-sucedido, When executado, Then log inserido em magic_link_logs."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client

        magic_table: MagicMock = MagicMock()
        magic_table.insert.return_value.execute.return_value = MagicMock(
            data=[]
        )

        def _handler(name: str) -> MagicMock:
            return (
                magic_table
                if name == "magic_link_logs"
                else _mock_client().table(name)
            )

        client.table.side_effect = _handler

        send_magic_link(
            email=TEST_EMAIL,
            user_id=TEST_USER_ID,
            triggered_by="webhook_auto_account",
        )

        call_args = magic_table.insert.call_args[0][0]
        self.assertEqual(call_args["user_id"], TEST_USER_ID)
        self.assertEqual(call_args["email"], TEST_EMAIL)
        self.assertEqual(call_args["triggered_by"], "webhook_auto_account")
        self.assertEqual(call_args["status"], "sent")


# ---------------------------------------------------------------------------
# is_event_processed (FR-006, FR-007 / T016)
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class IsEventProcessedTest(TestCase):
    """Testes de verificação de idempotência de eventos Stripe."""

    @patch("apps.payments.services._get_admin_client")
    def test_evento_ja_processado_retorna_true(
        self, mock_get: MagicMock
    ) -> None:
        """FR-006: Given evento já na tabela, When verificado, Then retorna True."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client

        _mock_table_with_data(
            client,
            "processed_webhook_events",
            [{"stripe_event_id": "evt_test_001"}],
        )

        result: bool = is_event_processed("evt_test_001")

        self.assertTrue(result)

    @patch("apps.payments.services._get_admin_client")
    def test_evento_nao_processado_retorna_false(
        self, mock_get: MagicMock
    ) -> None:
        """FR-007: Given evento não registrado, When verificado, Then retorna False."""
        client: MagicMock = _mock_client()
        # Dados vazios por padrão
        mock_get.return_value = client

        result: bool = is_event_processed("evt_novo_999")

        self.assertFalse(result)
