# Conftest para testes do módulo routines
# Helper para criação de requests de teste

from unittest.mock import MagicMock

from django.http import HttpRequest
from django.test import RequestFactory

_factory = RequestFactory()


def make_request(
    method: str,
    path: str,
    data: dict | None = None,
    cookies: dict | None = None,
    json_body: str | None = None,
) -> HttpRequest:
    """Cria um HttpRequest de teste para as views de routines.

    Args:
        method: HTTP method ('GET', 'POST', etc.)
        path: URL path (ex: '/routines/')
        data: Dict com dados de POST (form data)
        cookies: Dict com cookies a adicionar
        json_body: String JSON para o body (quando Content-Type: application/json)

    Returns:
        HttpRequest pronto para uso nos testes.
    """
    method = method.upper()

    if method == "GET":
        request = _factory.get(path)
    elif method == "POST":
        if json_body is not None:
            request = _factory.post(
                path,
                data=json_body,
                content_type="application/json",
            )
        else:
            request = _factory.post(path, data=data or {})
    elif method == "DELETE":
        request = _factory.delete(path)
    elif method == "PATCH":
        if json_body is not None:
            request = _factory.patch(
                path,
                data=json_body,
                content_type="application/json",
            )
        else:
            request = _factory.patch(path, data=data or {})
    else:
        request = _factory.generic(method, path)

    # Adicionar cookies
    if cookies:
        for key, value in cookies.items():
            request.COOKIES[key] = value

    return request


# JWT válido no formato supabase (header.payload.sig)
# payload: {"sub": "test-parent-uuid-1234", "role": "authenticated"}
import base64
import json


def make_jwt(sub: str = "test-parent-uuid-1234") -> str:
    """Gera um JWT fake no formato supabase_session para testes.

    Args:
        sub: UUID do usuário (parent_id)

    Returns:
        String JWT com formato header.payload.signature (sem assinatura real)
    """
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()

    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": sub, "role": "authenticated"}).encode()
    ).rstrip(b"=").decode()

    return f"{header}.{payload}.fake-signature"


FAKE_JWT = make_jwt("test-parent-uuid-1234")
FAKE_PARENT_ID = "test-parent-uuid-1234"
