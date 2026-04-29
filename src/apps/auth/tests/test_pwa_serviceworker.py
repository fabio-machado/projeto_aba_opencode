"""
T011 — PWA Service Worker (US1 / FR-019).

Verifica que o endpoint /serviceworker.js (servido pelo django-pwa)
retorna 200 com Content-Type application/javascript.
"""

from __future__ import annotations

from django.test import TestCase


class PwaServiceWorkerTest(TestCase):
    """Testes do service worker para PWA."""

    def test_serviceworker_returns_200(self) -> None:
        """GET /serviceworker.js retorna HTTP 200."""
        response = self.client.get("/serviceworker.js")
        self.assertEqual(response.status_code, 200)

    def test_serviceworker_has_javascript_content_type(self) -> None:
        """Service worker é servido com Content-Type application/javascript."""
        response = self.client.get("/serviceworker.js")
        content_type = response["Content-Type"]
        self.assertIn("javascript", content_type)
