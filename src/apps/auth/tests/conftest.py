"""
Fixtures e helpers compartilhados para os testes do app auth.

Extraídos de duplicações entre test_services.py, test_login_flow.py,
test_callback_middleware.py e test_rate_limiting.py durante a
revisão de infraestrutura de testes (2026-04-28).
"""

from __future__ import annotations

import base64
import json
from typing import Any
from unittest.mock import MagicMock

from django.http import HttpRequest
from django.test import RequestFactory

# ---------------------------------------------------------------------------
# Constantes de teste compartilhadas
# ---------------------------------------------------------------------------

TEST_USER_ID: str = "00000000-0000-0000-0000-000000000001"
TEST_EMAIL: str = "teste@exemplo.com"
TEST_IP: str = "192.168.1.100"

TEST_SETTINGS: dict[str, Any] = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "eyJ.test.service",
    "SUPABASE_KEY": "eyJ.test.anon",
    "APP_URL": "http://localhost:8000",
    "DEBUG": True,  # Para cookies não-Secure em testes
}


# ---------------------------------------------------------------------------
# Helpers de mock do Supabase
# ---------------------------------------------------------------------------


def mock_client() -> MagicMock:
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
        t.gte.return_value = t
        t.insert.return_value = t
        t.update.return_value = t
        t.execute.return_value = MagicMock(data=[])
        return t

    client.table.side_effect = _table_handler
    client.auth.sign_in_with_otp = MagicMock(return_value=None)
    client.auth.refresh_session = MagicMock(return_value=None)
    return client


def mock_table_with_data(
    client: MagicMock, table_name: str, data: list[dict], *, chain: str = "select"
) -> None:
    """Sobrescreve o side_effect de client.table para retornar dados em uma tabela.

    Args:
        client: MagicMock do cliente Supabase.
        table_name: Nome da tabela.
        data: Dados que a query deve retornar.
        chain: Método que inicia a chain (padrão: select). Use 'insert' ou 'update'.
    """

    def _handler(name: str) -> MagicMock:
        t: MagicMock = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.limit.return_value = t
        t.order.return_value = t
        t.gte.return_value = t
        t.insert.return_value = t
        t.update.return_value = t
        t.execute.return_value = MagicMock(data=data if name == table_name else [])
        return t

    client.table.side_effect = _handler


def build_fake_jwt(sub: str) -> str:
    """Constrói um JWT falso com o claim 'sub' fornecido."""
    payload_bytes: bytes = json.dumps({"sub": sub}).encode()
    payload_b64: str = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")
    return f"header.{payload_b64}.signature"


def make_mock_profile(overrides: dict | None = None) -> dict:
    """Retorna um dicionário de perfil padrão, com overrides opcionais."""
    profile: dict = {
        "id": TEST_USER_ID,
        "email": TEST_EMAIL,
        "subscription_status": "active",
        "has_generator_access": True,
        "has_library_access": False,
    }
    if overrides:
        profile.update(overrides)
    return profile


# ---------------------------------------------------------------------------
# Helpers de requisição HTTP (unificados de test_login_flow e test_callback)
# ---------------------------------------------------------------------------


def make_request(
    method: str, path: str, data: dict | None = None
) -> HttpRequest:
    """Cria um HttpRequest com o método, path e dados especificados."""
    factory = RequestFactory()
    if method == "GET":
        return factory.get(path, data or {})
    return factory.post(path, data or {})
