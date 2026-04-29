"""
T036 — PWA Logout Header (US2 / FR-020).

Verifica que o partial do header (_header.html) contém o link de logout
para /logout/ com o texto 'Sair', integrado ao dropdown de perfil.
"""

from __future__ import annotations

from django.test import TestCase
from django.template.loader import render_to_string


class PwaLogoutHeaderTest(TestCase):
    """Testes do botão de logout no partial do header."""

    def test_header_contains_logout_link(self) -> None:
        """_header.html contém um link apontando para /logout/."""
        html: str = render_to_string("partials/nav/_header.html")
        self.assertIn("/logout/", html)

    def test_header_logout_text_is_sair(self) -> None:
        """O link de logout exibe o texto 'Sair'."""
        html: str = render_to_string("partials/nav/_header.html")
        self.assertIn("Sair", html)
