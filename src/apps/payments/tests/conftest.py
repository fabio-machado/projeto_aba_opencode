"""
Fixtures e helpers compartilhados para os testes do app payments.

Extraídos de duplicações entre test_services.py, test_webhook_signature.py,
test_idempotency.py, test_magic_link.py, test_edge_cases.py,
test_account_creation.py e test_performance.py durante a revisão de
infraestrutura de testes (2026-04-28).
"""

from __future__ import annotations

import base64
import json
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

# ---------------------------------------------------------------------------
# Constantes de teste compartilhadas
# ---------------------------------------------------------------------------

TEST_USER_ID: str = "00000000-0000-0000-0000-000000000001"

TEST_SETTINGS: dict[str, Any] = {
    "STRIPE_WEBHOOK_SECRET": "whsec_test_secret",
    "STRIPE_SECRET_KEY": "sk_test_key",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "eyJ.test.service",
    "SUPABASE_ANON_KEY": "eyJ.test.anon",
    "APP_URL": "http://localhost:8000",
}

# ---------------------------------------------------------------------------
# Eventos Stripe de teste
# ---------------------------------------------------------------------------

VALID_EVENT: dict[str, Any] = {
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

NON_PAYMENT_EVENT: dict[str, Any] = {
    "id": "evt_test_other",
    "type": "charge.refunded",
    "data": {"object": {}},
}

EVENT_WITHOUT_EMAIL: dict[str, Any] = {
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


# ---------------------------------------------------------------------------
# Helpers de mock
# ---------------------------------------------------------------------------


def make_mock_supabase_client() -> MagicMock:
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


def build_fake_jwt(sub: str) -> str:
    """Constrói um JWT falso com o claim 'sub' fornecido."""
    payload_bytes: bytes = json.dumps({"sub": sub}).encode()
    payload_b64: str = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")
    return f"header.{payload_b64}.signature"
