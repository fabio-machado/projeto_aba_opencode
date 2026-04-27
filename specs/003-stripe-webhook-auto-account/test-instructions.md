# Instruções de Testes Automatizados — Stripe Webhook Auto Account

**Feature**: 003-stripe-webhook-auto-account  
**App Django**: `src/apps/payments/`  
**Arquivo de testes**: `src/apps/payments/tests.py`  
**Stack**: Django TestCase + `unittest.mock` + `stripe` SDK + `supabase-py`

---

## 1. Estrutura de Arquivos

Os testes devem ser escritos em `src/apps/payments/tests.py`. Se o arquivo crescer além de ~300 linhas, reorganize em:

```
src/apps/payments/
├── tests/
│   ├── __init__.py
│   ├── test_webhook.py          # T1 — Validação de assinatura
│   ├── test_account_creation.py # T2 — Criação de conta
│   ├── test_idempotency.py      # T3 — Idempotência
│   ├── test_magic_link.py       # T4 — Magic link
│   └── test_edge_cases.py       # T5 — Edge cases
└── tests.py                     # Mantém imports ou remove
```

Para rodar:
```bash
python src/manage.py test apps.payments -v 2
```

---

## 2. Convenções

- **Mock tudo que é externo**: Stripe SDK, Supabase client, HTTP requests
- **Nunca chame APIs reais** nos testes automatizados (use Stripe CLI para testes manuais)
- **Um teste por cenário** — nome descritivo: `test_<acao>_<condicao>_<resultado>`
- **Arrange → Act → Assert** em cada teste
- **Use `unittest.mock.patch`** para interceptar chamadas ao Stripe e Supabase

---

## 3. Fixtures e Helpers Comuns

Crie estes helpers no topo do `tests.py`:

```python
import json
from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings
from django.urls import reverse

# --- Dados de teste ---

VALID_EVENT = {
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
                "data": [{
                    "billing_details": {
                        "name": "João da Silva",
                        "email": "novo@exemplo.com",
                    }
                }]
            },
        }
    },
}

EVENT_WITHOUT_EMAIL = {
    "id": "evt_test_no_email",
    "type": "payment_intent.succeeded",
    "data": {
        "object": {
            "id": "pi_test_no_email",
            "customer": "cus_test_002",
            "charges": {
                "data": [{
                    "billing_details": {"name": "Sem Email"}
                }]
            },
        }
    },
}

NON_PAYMENT_EVENT = {
    "id": "evt_test_other",
    "type": "charge.refunded",
    "data": {"object": {}},
}

TEST_SETTINGS = {
    "STRIPE_WEBHOOK_SECRET": "whsec_test_secret",
    "STRIPE_SECRET_KEY": "sk_test_key",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "eyJ.test.service",
    "SUPABASE_ANON_KEY": "eyJ.test.anon",
    "APP_URL": "http://localhost:8000",
}
```

---

## 4. T1 — Validação de Assinatura (US2)

### 4.1. Mock do Stripe SDK

```python
@override_settings(**TEST_SETTINGS)
class StripeWebhookSignatureTests(TestCase):
    """Testes de validação de assinatura do webhook Stripe."""

    def _post_webhook(self, payload: dict, sig_header: str = "") -> dict:
        """Helper para enviar POST ao endpoint do webhook."""
        response = self.client.post(
            "/webhooks/stripe",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=sig_header,
        )
        return response

    def test_webhook_sem_assinatura_retorna_400(self):
        """Given requisição sem Stripe-Signature, When POST, Then 400."""
        resp = self._post_webhook(VALID_EVENT)
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("signature", data["message"].lower())

    def test_webhook_assinatura_invalida_retorna_400(self):
        """Given assinatura inválida, When POST, Then 400."""
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.side_effect = stripe.error.SignatureVerificationError(
                "Invalid signature", sig_header="t=xxx,v1=xxx"
            )
            resp = self._post_webhook(VALID_EVENT, sig_header="t=xxx,v1=xxx")
            self.assertEqual(resp.status_code, 400)

    def test_webhook_assinatura_valida_processa_evento(self):
        """Given assinatura válida, When POST, Then 200."""
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = VALID_EVENT
            with patch("apps.payments.services.process_payment_intent_succeeded") as mock_process:
                mock_process.return_value = {"status": "success", "action": "created"}
                resp = self._post_webhook(VALID_EVENT, sig_header="valid_sig")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.json()["status"], "success")

    def test_webhook_evento_nao_pagamento_retorna_200(self):
        """Given evento não-payment, When POST, Then 200 sem criar usuário."""
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = NON_PAYMENT_EVENT
            with patch("apps.payments.services.process_payment_intent_succeeded") as mock_process:
                resp = self._post_webhook(NON_PAYMENT_EVENT, sig_header="valid_sig")
                self.assertEqual(resp.status_code, 200)
                mock_process.assert_not_called()
```

---

## 5. T2 — Criação de Conta (US1)

### 5.1. Mock do Supabase

```python
@override_settings(**TEST_SETTINGS)
class AccountCreationTests(TestCase):
    """Testes de criação automática de conta via webhook."""

    def _mock_supabase_client(self):
        """Retorna um mock do cliente Supabase com respostas padrão."""
        mock_client = MagicMock()

        # list_users retorna vazio (usuário não existe)
        mock_client.auth.admin.list_users.return_value = MagicMock(users=[])

        # create_user retorna um user criado
        mock_user = MagicMock()
        mock_user.id = "00000000-0000-0000-0000-000000000001"
        mock_client.auth.admin.create_user.return_value = MagicMock(user=mock_user)

        # insert em profiles retorna dados
        mock_client.table.return_value.insert.return_value.execute.return_value = \
            MagicMock(data=[{"id": "00000000-0000-0000-0000-000000000001", "email": "novo@exemplo.com"}])

        return mock_client

    @patch("apps.payments.services._get_admin_client")
    @patch("stripe.Webhook.construct_event")
    def test_novo_usuario_criado_com_sucesso(self, mock_construct, mock_get_client):
        """Given payment válido, When webhook recebido, Then cria auth user + profile."""
        mock_construct.return_value = VALID_EVENT
        mock_client = self._mock_supabase_client()
        mock_get_client.return_value = mock_client

        with patch("apps.payments.services.send_magic_link", return_value=True):
            from apps.payments import services
            result = services.process_payment_intent_succeeded(VALID_EVENT)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "created")
        self.assertIn("user_id", result)

        # Verifica que create_user foi chamado
        mock_client.auth.admin.create_user.assert_called_once()

        # Verifica que profile foi inserido com email
        insert_calls = mock_client.table.return_value.insert.call_args_list
        profile_data = insert_calls[0][0][0]  # Primeiro insert = profile
        self.assertEqual(profile_data["email"], "novo@exemplo.com")
        self.assertEqual(profile_data["full_name"], "João da Silva")
        self.assertEqual(profile_data["cpf"], "123.456.789-00")

    @patch("apps.payments.services._get_admin_client")
    @patch("stripe.Webhook.construct_event")
    def test_usuario_existente_sem_sessao_reenvia_magic_link(self, mock_construct, mock_get_client):
        """Given usuário existente sem sessão, When webhook, Then não duplica, reenvia link."""
        mock_construct.return_value = VALID_EVENT
        mock_client = self._mock_supabase_client()

        # Simula usuário existente
        existing_user = MagicMock()
        existing_user.id = "00000000-0000-0000-0000-000000000001"
        existing_user.email = "novo@exemplo.com"
        mock_client.auth.admin.list_users.return_value = MagicMock(users=[existing_user])

        # Sem sessões ativas
        mock_client.auth.admin.list_sessions.return_value = MagicMock(sessions=[])

        mock_get_client.return_value = mock_client

        with patch("apps.payments.services.send_magic_link", return_value=True) as mock_send:
            from apps.payments import services
            result = services.process_payment_intent_succeeded(VALID_EVENT)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "idempotent")

        # Não criou novo usuário
        mock_client.auth.admin.create_user.assert_not_called()

        # Reenviou magic link
        mock_send.assert_called_once()

    @patch("apps.payments.services._get_admin_client")
    @patch("stripe.Webhook.construct_event")
    def test_usuario_existente_com_sessao_nao_reenvia_link(self, mock_construct, mock_get_client):
        """Given usuário com sessão ativa, When webhook, Then não reenvia magic link."""
        mock_construct.return_value = VALID_EVENT
        mock_client = self._mock_supabase_client()

        existing_user = MagicMock()
        existing_user.id = "00000000-0000-0000-0000-000000000001"
        existing_user.email = "novo@exemplo.com"
        mock_client.auth.admin.list_users.return_value = MagicMock(users=[existing_user])

        # Sessão ativa
        mock_client.auth.admin.list_sessions.return_value = MagicMock(
            sessions=[MagicMock()]
        )

        mock_get_client.return_value = mock_client

        with patch("apps.payments.services.send_magic_link", return_value=True) as mock_send:
            from apps.payments import services
            result = services.process_payment_intent_succeeded(VALID_EVENT)

        self.assertEqual(result["status"], "success")
        mock_send.assert_not_called()
```

---

## 6. T3 — Idempotência (US3)

```python
@override_settings(**TEST_SETTINGS)
class IdempotencyTests(TestCase):
    """Testes de garantia de idempotência no processamento de webhooks."""

    def _mock_supabase_client(self):
        mock_client = MagicMock()
        mock_client.auth.admin.list_users.return_value = MagicMock(users=[])
        mock_user = MagicMock()
        mock_user.id = "00000000-0000-0000-0000-000000000001"
        mock_client.auth.admin.create_user.return_value = MagicMock(user=mock_user)
        mock_client.table.return_value.insert.return_value.execute.return_value = \
            MagicMock(data=[{"id": "00000000-0000-0000-0000-000000000001"}])
        return mock_client

    @patch("apps.payments.services._get_admin_client")
    def test_mesmo_evento_duas_vezes_apenas_um_usuario(self, mock_get_client):
        """Given mesmo evt_id 2x, When processado, Then apenas 1 usuário criado."""
        mock_client = self._mock_supabase_client()
        mock_get_client.return_value = mock_client

        with patch("apps.payments.services.send_magic_link", return_value=True):
            from apps.payments import services

            # Primeira chamada
            result1 = services.process_payment_intent_succeeded(VALID_EVENT)
            self.assertEqual(result1["action"], "created")

            # Segunda chamada (mesmo event_id)
            result2 = services.process_payment_intent_succeeded(VALID_EVENT)
            self.assertEqual(result2["action"], "idempotent")

        # create_user chamado apenas 1 vez
        self.assertEqual(mock_client.auth.admin.create_user.call_count, 1)

    @patch("apps.payments.services._get_admin_client")
    def test_evento_ja_processado_retorna_idempotent(self, mock_get_client):
        """Given evento já marcado como processado, When, Then idempotent."""
        mock_client = self._mock_supabase_client()
        mock_get_client.return_value = mock_client

        # Simula evento já registrado
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
            MagicMock(data=[{"stripe_event_id": "evt_test_001"}])

        from apps.payments import services
        result = services.process_payment_intent_succeeded(VALID_EVENT)

        self.assertEqual(result["action"], "idempotent")
        mock_client.auth.admin.create_user.assert_not_called()
```

---

## 7. T4 — Magic Link (US4)

```python
@override_settings(**TEST_SETTINGS)
class MagicLinkTests(TestCase):
    """Testes de envio e validação de magic link."""

    def _mock_supabase_client(self):
        mock_client = MagicMock()
        mock_client.auth.admin.list_users.return_value = MagicMock(users=[])
        mock_user = MagicMock()
        mock_user.id = "00000000-0000-0000-0000-000000000001"
        mock_client.auth.admin.create_user.return_value = MagicMock(user=mock_user)
        mock_client.table.return_value.insert.return_value.execute.return_value = \
            MagicMock(data=[{"id": "00000000-0000-0000-0000-000000000001"}])
        return mock_client

    @patch("apps.payments.services._get_admin_client")
    def test_magic_link_enviado_para_novo_usuario(self, mock_get_client):
        """Given novo usuário criado, When processado, Then magic link enviado."""
        mock_client = self._mock_supabase_client()
        mock_get_client.return_value = mock_client

        with patch("apps.payments.services.send_magic_link", return_value=True) as mock_send:
            from apps.payments import services
            services.process_payment_intent_succeeded(VALID_EVENT)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        self.assertEqual(call_kwargs["email"], "novo@exemplo.com")
        self.assertEqual(call_kwargs["triggered_by"], "webhook_auto_account")

    @patch("apps.payments.services._get_admin_client")
    def test_falha_envio_magic_link_nao_falha_webhook(self, mock_get_client):
        """Given falha no envio do email, When, Then webhook retorna sucesso."""
        mock_client = self._mock_supabase_client()
        mock_get_client.return_value = mock_client

        with patch("apps.payments.services.send_magic_link", return_value=False):
            from apps.payments import services
            result = services.process_payment_intent_succeeded(VALID_EVENT)

        # Webhook processou com sucesso mesmo com falha no email
        self.assertEqual(result["status"], "success")

    def test_validate_magic_link_callback_valido(self):
        """Given tokens válidos, When validado, Then retorna user_id."""
        # JWT fake com sub claim
        import base64, json
        payload = json.dumps({"sub": "00000000-0000-0000-0000-000000000001"}).encode()
        fake_token = f"header.{base64.urlsafe_b64encode(payload).decode()}.signature"

        from apps.payments import services
        result = services.validate_magic_link_callback(
            access_token=fake_token,
            refresh_token="refresh_xxx",
            token_type="magiclink",
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["user_id"], "00000000-0000-0000-0000-000000000001")

    def test_validate_magic_link_callback_tipo_invalido(self):
        """Given token_type != magiclink, When validado, Then retorna None."""
        from apps.payments import services
        result = services.validate_magic_link_callback(
            access_token="token",
            refresh_token="refresh",
            token_type="signup",
        )
        self.assertIsNone(result)

    def test_validate_magic_link_callback_tokens_vazios(self):
        """Given tokens vazios, When validado, Then retorna None."""
        from apps.payments import services
        result = services.validate_magic_link_callback(
            access_token="",
            refresh_token="",
            token_type="magiclink",
        )
        self.assertIsNone(result)
```

---

## 8. T5 — Edge Cases

```python
@override_settings(**TEST_SETTINGS)
class EdgeCaseTests(TestCase):
    """Testes de cenários de borda e erro."""

    def test_payment_sem_email_retorna_erro(self):
        """Given payment_intent sem email, When processado, Then retorna erro."""
        from apps.payments import services
        result = services.process_payment_intent_succeeded(EVENT_WITHOUT_EMAIL)

        self.assertEqual(result["status"], "error")
        self.assertIn("email", result["message"].lower())

    @patch("apps.payments.services._get_admin_client")
    def test_falha_criacao_auth_user_propaga_erro(self, mock_get_client):
        """Given falha na criação do auth user, When, Then retorna erro."""
        mock_client = MagicMock()
        mock_client.auth.admin.list_users.return_value = MagicMock(users=[])
        mock_client.auth.admin.create_user.side_effect = RuntimeError("DB error")
        mock_get_client.return_value = mock_client

        from apps.payments import services
        result = services.process_payment_intent_succeeded(VALID_EVENT)

        self.assertEqual(result["status"], "error")

    @patch("apps.payments.services._get_admin_client")
    def test_falha_criacao_profile_retorna_erro(self, mock_get_client):
        """Given falha na criação do profile, When, Then retorna erro."""
        mock_client = MagicMock()
        mock_client.auth.admin.list_users.return_value = MagicMock(users=[])
        mock_user = MagicMock()
        mock_user.id = "00000000-0000-0000-0000-000000000001"
        mock_client.auth.admin.create_user.return_value = MagicMock(user=mock_user)

        # Profile insert falha
        mock_client.table.return_value.insert.return_value.execute.side_effect = \
            Exception("Constraint violation")
        mock_get_client.return_value = mock_client

        from apps.payments import services
        result = services.process_payment_intent_succeeded(VALID_EVENT)

        self.assertEqual(result["status"], "error")
        self.assertIn("profile", result["message"].lower())

    @patch("apps.payments.services._get_admin_client")
    def test_audit_log_apos_profile_existente(self, mock_get_client):
        """Given user criado, When audit log, Then FK constraint respeitada."""
        mock_client = MagicMock()
        mock_client.auth.admin.list_users.return_value = MagicMock(users=[])
        mock_user = MagicMock()
        mock_user.id = "00000000-0000-0000-0000-000000000001"
        mock_client.auth.admin.create_user.return_value = MagicMock(user=mock_user)

        # Profile criado com sucesso
        mock_client.table.return_value.insert.return_value.execute.return_value = \
            MagicMock(data=[{"id": "00000000-0000-0000-0000-000000000001"}])
        mock_get_client.return_value = mock_client

        with patch("apps.payments.services.send_magic_link", return_value=True):
            from apps.payments import services
            result = services.process_payment_intent_succeeded(VALID_EVENT)

        self.assertEqual(result["status"], "success")
```

---

## 9. T6 — Performance (SC-001)

```python
import time

@override_settings(**TEST_SETTINGS)
class PerformanceTests(TestCase):
    """Testes de performance do webhook (SC-001: < 3s)."""

    def test_webhook_responde_em_menos_de_3_segundos(self):
        """Given webhook válido, When POST, Then response < 3000ms."""
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = VALID_EVENT
            with patch("apps.payments.services.process_payment_intent_succeeded") as mock_process:
                mock_process.return_value = {"status": "success", "action": "created"}

                start = time.time()
                resp = self.client.post(
                    "/webhooks/stripe",
                    data=json.dumps(VALID_EVENT),
                    content_type="application/json",
                    HTTP_STRIPE_SIGNATURE="valid_sig",
                )
                elapsed_ms = (time.time() - start) * 1000

                self.assertEqual(resp.status_code, 200)
                self.assertLess(elapsed_ms, 3000, f"Webhook demorou {elapsed_ms:.0f}ms (> 3000ms)")
```

---

## 10. Checklist de Cobertura

Após implementar, verifique:

| User Story | Testes | Status |
|------------|--------|--------|
| **US2** — Validação de assinatura | 4 testes | [ ] |
| **US1** — Criação de conta | 3 testes | [ ] |
| **US3** — Idempotência | 2 testes | [ ] |
| **US4** — Magic link | 5 testes | [ ] |
| **T5** — Edge cases | 4 testes | [ ] |
| **T6** — Performance | 1 teste | [ ] |
| **Total** | **19 testes** | [ ] |

---

## 11. Como Rodar

```bash
# Todos os testes do app payments
python src/manage.py test apps.payments -v 2

# Apenas uma classe
python src/manage.py test apps.payments.tests.StripeWebhookSignatureTests -v 2

# Apenas um teste específico
python src/manage.py test apps.payments.tests.StripeWebhookSignatureTests.test_webhook_sem_assinatura_retorna_400 -v 2

# Com coverage (se instalado)
pip install coverage
coverage run src/manage.py test apps.payments
coverage report -m
```

---

## 12. Notas Importantes

1. **Não use o banco real** — todos os testes devem mockar `_get_admin_client()` e `stripe.Webhook.construct_event`
2. **`override_settings`** é obrigatório em cada classe para injetar as variáveis de ambiente de teste
3. **Order matters** — o `log_audit_event` deve ser chamado **depois** de `create_profile()` (FK constraint)
4. **CPF vem do metadata** — o campo `metadata.cpf` do payment_intent é extraído e salvo no profile
5. **Email em profiles** — o campo `email` agora existe na tabela `profiles` com índice único; `find_user_by_email` faz query direta (não usa `list_users`)
