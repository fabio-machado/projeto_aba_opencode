"""
T6 — Performance (SC-001: < 3 segundos).

Cobre:
- Webhook responde em menos de 3000ms com service mockado
"""

import json
import time
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse

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
            "charges": {
                "data": [
                    {"billing_details": {"name": "João da Silva"}}
                ]
            },
        }
    },
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
class PerformanceTests(TestCase):
    """Testes de performance do webhook (SC-001: < 3s)."""

    def test_webhook_responde_em_menos_de_3_segundos(self) -> None:
        """Given webhook válido com services mockados, When POST, Then resposta < 3000ms."""
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
                }

                start: float = time.time()
                resp = self.client.post(
                    reverse("payments:stripe_webhook"),
                    data=json.dumps(VALID_EVENT),
                    content_type="application/json",
                    HTTP_STRIPE_SIGNATURE="valid_sig",
                )
                elapsed_ms: float = (time.time() - start) * 1000

                self.assertEqual(resp.status_code, 200)
                self.assertLess(
                    elapsed_ms,
                    3000,
                    f"Webhook demorou {elapsed_ms:.0f}ms (> 3000ms)",
                )
