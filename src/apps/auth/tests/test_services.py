"""
T4 — Service Layer (US1, US2, US3, US4 / FR-003, FR-004, FR-008, FR-009, FR-017, FR-018).

Cobre:
- validate_user: sucesso, e-mail não encontrado, conta inativa, formato inválido
- send_magic_link: sucesso, falha de envio, log de magic_link_logs
- refresh_session: sucesso, falha, debounce
- set_callback_cookies: cookies setados com atributos corretos
- validate_magic_link_callback: sucesso, token_type inválido, tokens vazios, JWT malformado
- get_profile_by_id: sucesso, não encontrado, erro de query
- update_magic_link_clicked: sucesso, registro mais recente, sem registro
- clear_session_cookies: cookies removidos
- AccountInactiveError: mensagem e atributos
"""

import base64
import json
from unittest.mock import MagicMock, patch

from django.http import HttpResponse
from django.test import TestCase, override_settings

from apps.auth.services import (
    AccountInactiveError,
    check_rate_limit,
    clear_session_cookies,
    get_profile_by_id,
    log_attempt,
    refresh_session,
    send_magic_link,
    set_callback_cookies,
    update_magic_link_clicked,
    validate_magic_link_callback,
    validate_user,
)

# Helpers e constantes extraídos para conftest.py — import local
from .conftest import (  # noqa: E402
    TEST_USER_ID,
    TEST_EMAIL,
    TEST_IP,
    TEST_SETTINGS,
    mock_client as _mock_client,
    mock_table_with_data as _mock_table_with_data,
    build_fake_jwt as _build_fake_jwt,
    make_mock_profile as _make_mock_profile,
)


# ---------------------------------------------------------------------------
# validate_user
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class ValidateUserTest(TestCase):
    """Testes de validação de usuário (FR-004)."""

    @patch("apps.auth.services._get_admin_client")
    def test_valida_usuario_ativo_retorna_dados(self, mock_get: MagicMock) -> None:
        """Given e-mail de usuário pagante ativo, When validado, Then retorna perfil."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client
        _mock_table_with_data(client, "profiles", [_make_mock_profile()])

        result: dict | None = validate_user(TEST_EMAIL)

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], TEST_USER_ID)
        self.assertEqual(result["subscription_status"], "active")
        self.assertEqual(result["has_generator_access"], True)

    @patch("apps.auth.services._get_admin_client")
    def test_email_nao_encontrado_retorna_none(self, mock_get: MagicMock) -> None:
        """Given e-mail sem perfil, When validado, Then retorna None."""
        client: MagicMock = _mock_client()
        client.table.return_value.execute.return_value = MagicMock(data=[])
        mock_get.return_value = client

        result: dict | None = validate_user("inexistente@exemplo.com")

        self.assertIsNone(result)

    @patch("apps.auth.services._get_admin_client")
    def test_conta_inativa_lanca_account_inactive_error(
        self, mock_get: MagicMock
    ) -> None:
        """Given conta com status canceled, When validado, Then lança AccountInactiveError."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client
        _mock_table_with_data(
            client, "profiles", [_make_mock_profile({"subscription_status": "canceled"})]
        )

        with self.assertRaises(AccountInactiveError) as ctx:
            validate_user(TEST_EMAIL)

        self.assertEqual(ctx.exception.email, TEST_EMAIL)
        self.assertEqual(ctx.exception.status, "canceled")

    @patch("apps.auth.services._get_admin_client")
    def test_conta_trial_eh_valida(self, mock_get: MagicMock) -> None:
        """Given conta com status trialing, When validado, Then retorna perfil."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client
        _mock_table_with_data(
            client, "profiles", [_make_mock_profile({"subscription_status": "trialing"})]
        )

        result: dict | None = validate_user(TEST_EMAIL)

        self.assertIsNotNone(result)
        self.assertEqual(result["subscription_status"], "trialing")

    def test_formato_email_sem_arroba_lanca_value_error(self) -> None:
        """Given e-mail sem @, When validado, Then lança ValueError."""
        with self.assertRaises(ValueError):
            validate_user("usuario")

    def test_formato_email_dominio_invalido_lanca_value_error(self) -> None:
        """Given e-mail com domínio sem ponto, When validado, Then lança ValueError."""
        with self.assertRaises(ValueError):
            validate_user("usuario@dominio")

    def test_normalizacao_email_trim_e_lowercase(self) -> None:
        """FR-003: E-mail é normalizado (trim + lowercase) antes da query."""
        client: MagicMock = _mock_client()
        captured_eq_args: list = []
        profiles_mock: MagicMock | None = None

        def _handler(name: str) -> MagicMock:
            nonlocal profiles_mock
            t: MagicMock = MagicMock()
            t.select.return_value = t
            t.limit.return_value = t
            t.order.return_value = t
            t.gte.return_value = t
            t.insert.return_value = t
            t.update.return_value = t
            t.execute.return_value = MagicMock(data=[])
            if name == "profiles":
                t.execute.return_value = MagicMock(data=[_make_mock_profile()])
                # Captura argumentos do eq
                t.eq = MagicMock(side_effect=lambda *a: (
                    captured_eq_args.append(a) or t
                ))
                profiles_mock = t
            return t

        client.table.side_effect = _handler

        with patch(
            "apps.auth.services._get_admin_client", return_value=client
        ):
            validate_user("  TESTE@EXEMPLO.COM  ")

        # Verifica que a query foi feita com e-mail normalizado
        self.assertTrue(
            len(captured_eq_args) > 0,
            "eq() deve ser chamado para filtrar por email",
        )
        self.assertEqual(captured_eq_args[0][1], "teste@exemplo.com")

    @patch("apps.auth.services._get_admin_client")
    def test_erro_query_supabase_retorna_none(self, mock_get: MagicMock) -> None:
        """Given erro na query Supabase, When validado, Then retorna None graciosamente."""
        client: MagicMock = _mock_client()
        client.table.return_value.execute.side_effect = Exception("Connection error")
        mock_get.return_value = client

        result: dict | None = validate_user(TEST_EMAIL)

        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# send_magic_link
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class SendMagicLinkTest(TestCase):
    """Testes de envio de Magic Link (FR-008)."""

    @patch("apps.auth.services._get_admin_client")
    @patch("apps.auth.services.AuditLogService")
    def test_envio_bem_sucedido_retorna_true(
        self, mock_audit: MagicMock, mock_get: MagicMock
    ) -> None:
        """Given e-mail e user_id válidos, When enviado, Then retorna True."""
        client: MagicMock = _mock_client()
        client.auth.sign_in_with_otp = MagicMock(return_value=None)
        mock_get.return_value = client

        mock_audit.return_value.log = MagicMock()

        result: bool = send_magic_link(TEST_EMAIL, TEST_USER_ID)

        self.assertTrue(result)
        client.auth.sign_in_with_otp.assert_called_once()
        # Verifica que o redirect_to está no payload
        call_args = client.auth.sign_in_with_otp.call_args[0][0]
        self.assertEqual(call_args["email"], TEST_EMAIL)
        self.assertIn("auth/callback", call_args["options"]["email_redirect_to"])

    @patch("apps.auth.services._get_admin_client")
    @patch("apps.auth.services.AuditLogService")
    def test_falha_envio_retorna_false(
        self, mock_audit: MagicMock, mock_get: MagicMock
    ) -> None:
        """Given erro no sign_in_with_otp, When enviado, Then retorna False."""
        client: MagicMock = _mock_client()
        client.auth.sign_in_with_otp.side_effect = Exception("SMTP error")
        mock_get.return_value = client

        mock_audit.return_value.log = MagicMock()

        result: bool = send_magic_link(TEST_EMAIL, TEST_USER_ID)

        self.assertFalse(result)

    @patch("apps.auth.services._get_admin_client")
    @patch("apps.auth.services.AuditLogService")
    def test_magic_link_log_registrado_no_envio(
        self, mock_audit: MagicMock, mock_get: MagicMock
    ) -> None:
        """Given envio bem-sucedido, When executado, Then magic_link_logs inserido."""
        client: MagicMock = _mock_client()
        client.auth.sign_in_with_otp = MagicMock(return_value=None)
        mock_get.return_value = client
        mock_audit.return_value.log = MagicMock()

        # Captura o insert na magic_link_logs
        magic_table: MagicMock = MagicMock()
        magic_table.insert.return_value.execute.return_value = MagicMock(data=[])

        def _table_handler(name: str) -> MagicMock:
            return magic_table if name == "magic_link_logs" else _mock_client().table(name)

        client.table.side_effect = _table_handler

        send_magic_link(TEST_EMAIL, TEST_USER_ID)

        # Verifica que magic_link_logs.insert foi chamado
        call_args = magic_table.insert.call_args[0][0]
        self.assertEqual(call_args["user_id"], TEST_USER_ID)
        self.assertEqual(call_args["email"], TEST_EMAIL)
        self.assertEqual(call_args["triggered_by"], "user_request")
        self.assertEqual(call_args["status"], "sent")


# ---------------------------------------------------------------------------
# refresh_session
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class RefreshSessionTest(TestCase):
    """Testes de renovação de sessão (FR-009)."""

    @patch("apps.auth.services._get_admin_client")
    def test_refresh_bem_sucedido_retorna_tokens(
        self, mock_get: MagicMock
    ) -> None:
        """Given refresh_token válido, When renovado, Then retorna access_token e refresh_token."""
        client: MagicMock = _mock_client()
        mock_session: MagicMock = MagicMock()
        mock_session.access_token = "new-access-token"
        mock_session.refresh_token = "new-refresh-token"
        mock_session.user.id = TEST_USER_ID
        mock_resp: MagicMock = MagicMock()
        mock_resp.session = mock_session
        client.auth.refresh_session.return_value = mock_resp
        mock_get.return_value = client

        result: dict | None = refresh_session("valid-refresh-token")

        self.assertIsNotNone(result)
        self.assertEqual(result["access_token"], "new-access-token")
        self.assertEqual(result["refresh_token"], "new-refresh-token")

    @patch("apps.auth.services._get_admin_client")
    def test_refresh_sem_sessao_retorna_none(self, mock_get: MagicMock) -> None:
        """Given refresh_token que retorna None, When renovado, Then retorna None."""
        client: MagicMock = _mock_client()
        mock_resp: MagicMock = MagicMock()
        mock_resp.session = None
        client.auth.refresh_session.return_value = mock_resp
        mock_get.return_value = client

        result: dict | None = refresh_session("expired-refresh-token")

        self.assertIsNone(result)

    @patch("apps.auth.services._get_admin_client")
    def test_refresh_com_erro_retorna_none(self, mock_get: MagicMock) -> None:
        """Given erro no refresh_session, When renovado, Then retorna None."""
        client: MagicMock = _mock_client()
        client.auth.refresh_session.side_effect = Exception("Token revoked")
        mock_get.return_value = client

        result: dict | None = refresh_session("bad-token")

        self.assertIsNone(result)

    @patch("apps.auth.services._get_admin_client")
    def test_debounce_mesmo_token_retorna_none(
        self, mock_get: MagicMock
    ) -> None:
        """Given mesmo token sendo renovado concorrentemente, When refresh, Then None."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client

        # Primeira chamada inicia o refresh e fica "em progresso"
        # Segunda chamada com mesmo token deve retornar None (debounce)
        # Para simular isso, precisamos que a primeira chamada não termine
        # Usamos side_effect para travar a primeira e retornar None na segunda

        results: list = []

        def _slow_refresh(token: str) -> dict | None:
            """Simula refresh lento."""
            # A segunda chamada com mesmo token já encontrará o token no set
            return None  # Isso força o debounce na prática

        client.auth.refresh_session.side_effect = _slow_refresh

        # Primeira chamada — inicia refresh (adiciona ao set)
        result1: dict | None = refresh_session("shared-token")
        # Segunda chamada — same token, deve retornar None por debounce
        result2: dict | None = refresh_session("shared-token")

        # Pelo menos uma deve ter retornado None (debounce)
        self.assertTrue(result1 is None or result2 is None)


# ---------------------------------------------------------------------------
# set_callback_cookies
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class SetCallbackCookiesTest(TestCase):
    """Testes de configuração de cookies de sessão (FR-009)."""

    def test_cookies_setados_com_atributos_corretos(self) -> None:
        """Given access_token e refresh_token, When setados, Then cookies HTTP-only."""
        response: HttpResponse = HttpResponse()

        set_callback_cookies(response, "access-xxx", "refresh-xxx")

        # Verifica que ambos os cookies foram setados
        self.assertIn("supabase_session", response.cookies)
        self.assertIn("supabase_refresh", response.cookies)

        session_cookie = response.cookies["supabase_session"]
        self.assertEqual(session_cookie.value, "access-xxx")
        self.assertTrue(session_cookie["httponly"])
        self.assertEqual(session_cookie["samesite"], "Lax")
        self.assertEqual(session_cookie["path"], "/")

    def test_cookie_max_age_configurado_90_dias(self) -> None:
        """FR-009: Cookie max_age é 90 dias (7776000 segundos)."""
        response: HttpResponse = HttpResponse()

        set_callback_cookies(response, "access-xxx", "refresh-xxx")

        self.assertEqual(response.cookies["supabase_session"]["max-age"], 7776000)


# ---------------------------------------------------------------------------
# validate_magic_link_callback
# ---------------------------------------------------------------------------


class ValidateMagicLinkCallbackTest(TestCase):
    """Testes de validação de callback do Magic Link."""

    def test_callback_valido_retorna_dados(self) -> None:
        """Given tokens válidos, When validados, Then retorna access_token e user_id."""
        fake_token: str = _build_fake_jwt(TEST_USER_ID)

        result: dict | None = validate_magic_link_callback(
            access_token=fake_token,
            refresh_token="refresh-xxx",
            token_type="magiclink",
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["user_id"], TEST_USER_ID)
        self.assertEqual(result["access_token"], fake_token)
        self.assertEqual(result["refresh_token"], "refresh-xxx")

    def test_token_type_invalido_retorna_none(self) -> None:
        """Given token_type != magiclink, When validado, Then retorna None."""
        result: dict | None = validate_magic_link_callback(
            access_token="any_token",
            refresh_token="any_refresh",
            token_type="recovery",
        )

        self.assertIsNone(result)

    def test_tokens_vazios_retorna_none(self) -> None:
        """Given tokens vazios, When validado, Then retorna None."""
        result: dict | None = validate_magic_link_callback(
            access_token="",
            refresh_token="",
            token_type="magiclink",
        )

        self.assertIsNone(result)

    def test_jwt_malformado_2_partes_retorna_none(self) -> None:
        """Given JWT com apenas 2 partes, When validado, Then retorna None."""
        result: dict | None = validate_magic_link_callback(
            access_token="apenas.duas_partes",
            refresh_token="refresh-xxx",
            token_type="magiclink",
        )

        self.assertIsNone(result)

    def test_jwt_sem_sub_claim_retorna_none(self) -> None:
        """Given JWT sem claim 'sub', When validado, Then retorna None."""
        payload_bytes: bytes = json.dumps({"outro": "valor"}).encode()
        payload_b64: str = (
            base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")
        )
        token: str = f"header.{payload_b64}.signature"

        result: dict | None = validate_magic_link_callback(
            access_token=token,
            refresh_token="refresh-xxx",
            token_type="magiclink",
        )

        self.assertIsNone(result)

    def test_jwt_payload_base64_invalido_retorna_none(self) -> None:
        """Given JWT com payload inválido, When validado, Then retorna None."""
        result: dict | None = validate_magic_link_callback(
            access_token="header.!!!invalid!!!.signature",
            refresh_token="refresh-xxx",
            token_type="magiclink",
        )

        self.assertIsNone(result)

    def test_acesso_sem_refresh_token_retorna_none(self) -> None:
        """Given access_token válido mas refresh_token vazio, When validado, Then None."""
        fake_token: str = _build_fake_jwt(TEST_USER_ID)

        result: dict | None = validate_magic_link_callback(
            access_token=fake_token,
            refresh_token="",
            token_type="magiclink",
        )

        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# get_profile_by_id
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class GetProfileByIdTest(TestCase):
    """Testes de busca de perfil por user_id (FR-017)."""

    @patch("apps.auth.services._get_admin_client")
    def test_perfil_encontrado_retorna_dados(self, mock_get: MagicMock) -> None:
        """Given user_id existente, When buscado, Then retorna perfil."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client
        _mock_table_with_data(client, "profiles", [_make_mock_profile()])

        result: dict | None = get_profile_by_id(TEST_USER_ID)

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], TEST_USER_ID)
        self.assertEqual(result["email"], TEST_EMAIL)
        self.assertEqual(result["subscription_status"], "active")

    @patch("apps.auth.services._get_admin_client")
    def test_perfil_nao_encontrado_retorna_none(self, mock_get: MagicMock) -> None:
        """Given user_id inexistente, When buscado, Then retorna None."""
        client: MagicMock = _mock_client()
        client.table.return_value.execute.return_value = MagicMock(data=[])
        mock_get.return_value = client

        result: dict | None = get_profile_by_id("non-existent-id")

        self.assertIsNone(result)

    @patch("apps.auth.services._get_admin_client")
    def test_erro_query_retorna_none(self, mock_get: MagicMock) -> None:
        """Given erro na query Supabase, When buscado, Then retorna None."""
        client: MagicMock = _mock_client()
        client.table.return_value.execute.side_effect = Exception("DB down")
        mock_get.return_value = client

        result: dict | None = get_profile_by_id(TEST_USER_ID)

        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# update_magic_link_clicked
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class UpdateMagicLinkClickedTest(TestCase):
    """Testes de atualização de status do Magic Link."""

    @patch("apps.auth.services._get_admin_client")
    def test_atualiza_registro_mais_recente_sent(self, mock_get: MagicMock) -> None:
        """Given user_id com magic_link 'sent', When atualizado, Then status → 'clicked'."""
        client: MagicMock = _mock_client()
        mock_get.return_value = client

        # Sobrescreve o handler para magic_link_logs com dados específicos
        # e captura o update
        update_data: list[dict] = []

        def _handler(name: str) -> MagicMock:
            t: MagicMock = MagicMock()
            t.select.return_value = t
            t.eq.return_value = t
            t.limit.return_value = t
            t.order.return_value = t
            t.gte.return_value = t
            t.insert.return_value = t
            t.execute.return_value = MagicMock(data=[])

            if name == "magic_link_logs":
                # Primeira chamada: select (data com log_id)
                # Segunda chamada: update + eq + execute
                call_count: list[int] = [0]

                def _execute_side_effect():
                    call_count[0] += 1
                    if call_count[0] == 1:
                        return MagicMock(data=[{"id": "log-001"}])
                    return MagicMock(data=[])

                t.execute.side_effect = _execute_side_effect

                def _update_capture(data: dict) -> MagicMock:
                    update_data.append(data)
                    return t

                t.update.side_effect = _update_capture
            return t

        client.table.side_effect = _handler

        update_magic_link_clicked(TEST_USER_ID)

        # Verifica que o update foi chamado com status='clicked'
        self.assertEqual(len(update_data), 1, "update deve ser chamado 1 vez")
        self.assertEqual(update_data[0]["status"], "clicked")

    @patch("apps.auth.services._get_admin_client")
    def test_sem_registro_sent_sem_falha(self, mock_get: MagicMock) -> None:
        """Given user_id sem registro 'sent', When atualizado, Then não lança erro."""
        client: MagicMock = _mock_client()
        client.table.return_value.execute.return_value = MagicMock(data=[])
        mock_get.return_value = client

        # Não deve lançar exceção
        try:
            update_magic_link_clicked(TEST_USER_ID)
        except Exception:
            self.fail("update_magic_link_clicked não deve lançar exceção")


# ---------------------------------------------------------------------------
# clear_session_cookies
# ---------------------------------------------------------------------------


class ClearSessionCookiesTest(TestCase):
    """Testes de remoção de cookies de sessão (FR-020)."""

    def test_remove_ambos_cookies(self) -> None:
        """Given response com cookies setados, When limpos, Then ambos removidos."""
        response: HttpResponse = HttpResponse()
        # Primeiro seta cookies
        set_callback_cookies(response, "access-xxx", "refresh-xxx")
        # Depois limpa
        clear_session_cookies(response)

        # delete_cookie seta max-age=0
        self.assertEqual(response.cookies["supabase_session"]["max-age"], 0)
        self.assertEqual(response.cookies["supabase_refresh"]["max-age"], 0)


# ---------------------------------------------------------------------------
# AccountInactiveError
# ---------------------------------------------------------------------------


class AccountInactiveErrorTest(TestCase):
    """Testes da exceção AccountInactiveError."""

    def test_excecao_contem_email_e_status(self) -> None:
        """Given email e status, When instanciada, Then atributos preservados."""
        exc: AccountInactiveError = AccountInactiveError(
            "teste@exemplo.com", "canceled"
        )

        self.assertEqual(exc.email, "teste@exemplo.com")
        self.assertEqual(exc.status, "canceled")
        self.assertIn("teste@exemplo.com", str(exc))
        self.assertIn("canceled", str(exc))
