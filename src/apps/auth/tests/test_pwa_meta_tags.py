"""
T030 — PWA Meta Tags iOS (US4 / FR-025).

Testa que o template base.html renderiza as meta tags específicas
para iOS (apple-mobile-web-app-capable, apple-touch-icon, theme-color).
"""

from __future__ import annotations

from django.test import TestCase


class PwaMetaTagsTest(TestCase):
    """Tests for iOS PWA meta tags in base template."""

    def test_theme_color_meta_is_teal(self) -> None:
        """base.html has theme-color meta with #14b8a6."""
        response = self.client.get("/login/")
        content = response.content.decode("utf-8")
        self.assertIn('name="theme-color"', content)
        self.assertIn("#14b8a6", content)

    def test_apple_mobile_web_app_capable(self) -> None:
        """base.html has apple-mobile-web-app-capable meta set to yes."""
        response = self.client.get("/login/")
        content = response.content.decode("utf-8")
        self.assertIn("apple-mobile-web-app-capable", content)
        self.assertIn("yes", content)

    def test_apple_touch_icon_links(self) -> None:
        """base.html has apple-touch-icon links for iOS home screen."""
        response = self.client.get("/login/")
        content = response.content.decode("utf-8")
        self.assertIn("apple-touch-icon", content)
        self.assertIn("icon-192x192", content)
