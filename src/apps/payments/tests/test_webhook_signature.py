"""
T1 — Validação de Assinatura do Webhook Stripe (US2 / FR-001 a FR-004).

Cobre:
- Requisição sem header Stripe-Signature
- Assinatura inválida via SignatureVerificationError
- Assinatura válida → processamento do evento
- Evento de tipo não-pagamento ignorado
- STRIPE_WEBHOOK_SECRET não configurado
"""

import json
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode

import stripe
from django.test import TestCase, override_settings
from django.urls import reverse

# ---------------------------------------------------------------------------
# Dados de teste comuns
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

NON_PAYMENT_EVENT: dict = {
    "id": "evt_test_other",
    "type": "charge.refunded",
    "data": {"object": {}},
}

TEST_SETTINGS: dict = {
    "STRIPE_WEBHOOK_SECRET": "whsec_test_secret",
    "STRIPE_SECRET_KEY": "sk_test_key",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "eyJ.test.service",
    "SUPABASE_ANON_KEY": "eyJ.test.anon",
    "APP_URL": "http://localhost:8000",
}


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


@override_settings(**TEST_SETTINGS)
class StripeWebhookSignatureTests(TestCase):
    """Testes de validação de assinatura do webhook Stripe."""

    def _post_webhook(self, payload: dict, sig_header: str = "") -> dict:
        """Helper: envia POST ao endpoint do webhook e retorna o response."""
        return self.client.post(
            reverse("payments:stripe_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=sig_header,
        )

    def test_sem_assinatura_retorna_400(self) -> None:
        """Given requisição sem Stripe-Signature, When POST, Then 400."""
        resp = self._post_webhook(VALID_EVENT)
        self.assertEqual(resp.status_code, 400)
        data: dict = resp.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("signature", data["message"].lower())

    def test_assinatura_invalida_retorna_400(self) -> None:
        """Given assinatura inválida, When POST, Then 400 sem criar usuário."""
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.side_effect = stripe.error.SignatureVerificationError(
                "Invalid signature", sig_header="t=xxx,v1=xxx"
            )
            resp = self._post_webhook(VALID_EVENT, sig_header="t=xxx,v1=xxx")
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.json()["status"], "error")

    def test_assinatura_valida_processa_evento(self) -> None:
        """Given assinatura válida, When POST, Then 200 e event é processado."""
        with patch(
            "stripe.Webhook.construct_event"
        ) as mock_construct:
            mock_event: MagicMock = MagicMock()
            mock_event.to_dict.return_value = VALID_EVENT
            mock_construct.return_value = mock_event
            with patch(
                "apps.payments.services.process_payment_intent_succeeded"
            ) as mock_process:
                mock_process.return_value = {
                    "status": "success",
                    "action": "created",
                    "user_id": "00000000-0000-0000-0000-000000000001",
                }
                resp = self._post_webhook(VALID_EVENT, sig_header="valid_sig")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.json()["status"], "success")
                mock_process.assert_called_once_with(VALID_EVENT)

    def test_evento_nao_payment_retorna_200_sem_processar(self) -> None:
        """Given evento charge.refunded, When POST, Then 200 sem acionar processor."""
        with patch(
            "stripe.Webhook.construct_event"
        ) as mock_construct:
            mock_event: MagicMock = MagicMock()
            mock_event.to_dict.return_value = NON_PAYMENT_EVENT
            mock_construct.return_value = mock_event
            with patch(
                "apps.payments.services.process_payment_intent_succeeded"
            ) as mock_process:
                resp = self._post_webhook(NON_PAYMENT_EVENT, sig_header="valid_sig")
                self.assertEqual(resp.status_code, 200)
                mock_process.assert_not_called()

    def test_webhook_secret_nao_configurado_retorna_500(self) -> None:
        """Given STRIPE_WEBHOOK_SECRET vazio, When POST, Then 500."""
        with self.settings(STRIPE_WEBHOOK_SECRET=""):
            resp = self._post_webhook(VALID_EVENT, sig_header="valid_sig")
            self.assertEqual(resp.status_code, 500)
            self.assertEqual(resp.json()["status"], "error")
