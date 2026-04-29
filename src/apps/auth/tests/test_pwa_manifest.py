"""
T009 — PWA Manifest (US1 / FR-019).

Verifica que o endpoint /manifest.json (servido pelo django-pwa) retorna
200 com os campos obrigatórios: display, orientation, theme_color e icons.
"""

from __future__ import annotations

from django.test import TestCase


class PwaManifestTest(TestCase):
    """Testes do web manifest para PWA."""

    def test_manifest_returns_200(self) -> None:
        """GET /manifest.json retorna HTTP 200."""
        response = self.client.get("/manifest.json")
        self.assertEqual(response.status_code, 200)

    def test_manifest_has_correct_content_type(self) -> None:
        """Manifest é servido com Content-Type application/json."""
        response = self.client.get("/manifest.json")
        self.assertEqual(response["Content-Type"], "application/json")

    def test_manifest_contains_display_standalone(self) -> None:
        """Manifest declara display: standalone para experiência PWA."""
        response = self.client.get("/manifest.json")
        data = response.json()
        self.assertEqual(data["display"], "standalone")

    def test_manifest_contains_orientation_portrait(self) -> None:
        """Manifest declara orientation: portrait."""
        response = self.client.get("/manifest.json")
        data = response.json()
        self.assertEqual(data["orientation"], "portrait")

    def test_manifest_contains_theme_color(self) -> None:
        """Manifest declara theme_color com o token de design do projeto."""
        response = self.client.get("/manifest.json")
        data = response.json()
        self.assertIn("theme_color", data)
        self.assertEqual(data["theme_color"], "#14b8a6")

    def test_manifest_contains_icons_array(self) -> None:
        """Manifest contém um array icons com pelo menos 2 entradas."""
        response = self.client.get("/manifest.json")
        data = response.json()
        self.assertIn("icons", data)
        self.assertIsInstance(data["icons"], list)
        self.assertGreaterEqual(len(data["icons"]), 2)
