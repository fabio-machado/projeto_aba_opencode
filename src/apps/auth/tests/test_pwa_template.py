"""
T010 — PWA Meta Tags no Template (US1 / FR-019).

Verifica que o template base.html renderiza as tags obrigatórias
para instalação PWA: <link rel="manifest"> e theme-color meta.
"""

from __future__ import annotations

from django.test import TestCase


class PwaTemplateTest(TestCase):
    """Testes das tags PWA no template base."""

    def test_base_template_has_manifest_link(self) -> None:
        """base.html contém <link rel="manifest" para registro do PWA."""
        response = self.client.get("/login/")
        content = response.content.decode("utf-8")
        self.assertIn('rel="manifest"', content)

    def test_base_template_has_theme_color_meta(self) -> None:
        """base.html contém meta tag theme-color para cor do browser chrome."""
        response = self.client.get("/login/")
        content = response.content.decode("utf-8")
        self.assertIn('name="theme-color"', content)
