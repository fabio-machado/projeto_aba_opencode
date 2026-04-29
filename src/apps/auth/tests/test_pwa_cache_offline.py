"""
T025 — PWA Cache Offline (US3 / FR-022).

Testa que o service worker declara um cache versionado e referencia
os arquivos estáticos críticos (CSS, JS, ícones) no array de pre-cache.
"""

from __future__ import annotations

from django.test import TestCase


class PwaCacheOfflineTest(TestCase):
    """Tests for the service worker pre-cache configuration."""

    def test_serviceworker_contains_cache_name(self) -> None:
        """Service worker declares a versioned cache name."""
        response = self.client.get("/serviceworker.js")
        content = response.content.decode("utf-8")
        self.assertIn("aef-static", content)

    def test_serviceworker_precaches_theme_css(self) -> None:
        """Service worker pre-caches theme.css for offline access."""
        response = self.client.get("/serviceworker.js")
        content = response.content.decode("utf-8")
        self.assertIn("theme.css", content)

    def test_serviceworker_precaches_app_shell_js(self) -> None:
        """Service worker pre-caches app-shell.js for offline rendering."""
        response = self.client.get("/serviceworker.js")
        content = response.content.decode("utf-8")
        self.assertIn("app-shell.js", content)

    def test_serviceworker_precaches_pwa_icons(self) -> None:
        """Service worker pre-caches PWA icons for offline access."""
        response = self.client.get("/serviceworker.js")
        content = response.content.decode("utf-8")
        self.assertIn("icon-192x192", content)
