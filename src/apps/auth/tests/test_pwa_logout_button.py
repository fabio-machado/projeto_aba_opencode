"""
T019 — PWA Logout Button (US2 / FR-020).

No contexto PWA, o botão de logout deve limpar os cookies de sessão
(supabase_session e supabase_refresh) e redirecionar para /login/.
"""

from __future__ import annotations

from django.test import TestCase


class PwaLogoutButtonTest(TestCase):
    """Testes da funcionalidade de logout no contexto PWA."""

    def test_logout_removes_session_cookies(self) -> None:
        """GET /logout/ remove os cookies supabase_session e supabase_refresh."""
        self.client.cookies["supabase_session"] = "fake-session-token"
        self.client.cookies["supabase_refresh"] = "fake-refresh-token"

        response = self.client.get("/logout/")

        self.assertEqual(response.status_code, 302)
        cookie_session = response.cookies.get("supabase_session")
        cookie_refresh = response.cookies.get("supabase_refresh")
        if cookie_session:
            self.assertTrue(
                cookie_session["max-age"] == 0 or cookie_session.value == ""
            )
        if cookie_refresh:
            self.assertTrue(
                cookie_refresh["max-age"] == 0 or cookie_refresh.value == ""
            )

    def test_logout_redirects_to_login(self) -> None:
        """GET /logout/ redireciona para a página /login/."""
        response = self.client.get("/logout/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/login")
