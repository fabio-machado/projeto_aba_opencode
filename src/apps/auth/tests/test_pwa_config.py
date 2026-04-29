"""
T035 — PWA Config (US1 / FR-019).

Verifica que as configurações PWA no Django settings (individuais PWA_APP_*)
estão corretamente configuradas para instalação e experiência standalone.
"""

from __future__ import annotations

from django.conf import settings
from django.test import TestCase


class PwaConfigTest(TestCase):
    """Testes para as configurações PWA no Django settings."""

    def test_pwa_in_installed_apps(self) -> None:
        """'pwa' está presente em INSTALLED_APPS."""
        self.assertIn("pwa", settings.INSTALLED_APPS)

    def test_pwa_app_name_configured(self) -> None:
        """PWA_APP_NAME está configurado como 'Autismo em Foco'."""
        self.assertTrue(hasattr(settings, "PWA_APP_NAME"))
        self.assertEqual(settings.PWA_APP_NAME, "Autismo em Foco")

    def test_pwa_display_standalone(self) -> None:
        """PWA_APP_DISPLAY está configurado como 'standalone'."""
        self.assertTrue(hasattr(settings, "PWA_APP_DISPLAY"))
        self.assertEqual(settings.PWA_APP_DISPLAY, "standalone")

    def test_pwa_orientation_portrait(self) -> None:
        """PWA_APP_ORIENTATION está configurado como 'portrait'."""
        self.assertTrue(hasattr(settings, "PWA_APP_ORIENTATION"))
        self.assertEqual(settings.PWA_APP_ORIENTATION, "portrait")

    def test_pwa_theme_color_is_teal(self) -> None:
        """PWA_APP_THEME_COLOR está configurado como '#14b8a6'."""
        self.assertTrue(hasattr(settings, "PWA_APP_THEME_COLOR"))
        self.assertEqual(settings.PWA_APP_THEME_COLOR, "#14b8a6")

    def test_pwa_background_color(self) -> None:
        """PWA_APP_BACKGROUND_COLOR está configurado como '#f8fafc'."""
        self.assertTrue(hasattr(settings, "PWA_APP_BACKGROUND_COLOR"))
        self.assertEqual(settings.PWA_APP_BACKGROUND_COLOR, "#f8fafc")

    def test_pwa_icons_configured(self) -> None:
        """PWA_APP_ICONS é uma lista com pelo menos 2 entradas de ícones."""
        self.assertTrue(hasattr(settings, "PWA_APP_ICONS"))
        self.assertIsInstance(settings.PWA_APP_ICONS, list)
        self.assertGreaterEqual(len(settings.PWA_APP_ICONS), 2)

    def test_pwa_service_worker_path_set(self) -> None:
        """PWA_SERVICE_WORKER_PATH está configurado e não vazio."""
        self.assertTrue(hasattr(settings, "PWA_SERVICE_WORKER_PATH"))
        self.assertTrue(len(settings.PWA_SERVICE_WORKER_PATH) > 0)
