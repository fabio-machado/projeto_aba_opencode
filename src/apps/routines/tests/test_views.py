"""
Testes para as Views do módulo Routines.

Cobre:
- Validações de roteamento e redirecionamento.
- Verificação de renderização de partials via HTMX (quando aplicável).
- O isolamento completo da camada de services (mocks).
- Tratamento de status codes (200, 400, 403, 404, 405).
"""

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import Client, TestCase
from django.urls import reverse


class TestRoutineViews(TestCase):
    """Conjunto de testes para as views de Routines."""

    def setUp(self) -> None:
        """Setup inicial comum a todos os testes."""
        self.client = Client()
        self.fake_parent_id = "11111111-1111-1111-1111-111111111111"
        self.fake_routine_id = uuid4()
        
        # Simula o cookie 'supabase_session' preenchido para mockar autenticação
        # O _get_parent_id apenas decodifica base64. Simulamos um base64 válido.
        # "eyJhbGciOiJIUzI1NiIsInR5cCI... . eyJzdWIiOiAiMTExMTExMTEtMTExMS0xMTExLTExMTEtMTExMTExMTExMTExIn0 . sig"
        import base64
        import json
        payload = json.dumps({"sub": self.fake_parent_id}).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")
        fake_jwt = f"header.{payload_b64}.signature"
        self.client.cookies["supabase_session"] = fake_jwt

    # ── Testes: routine_list ──────────────────────────────────────────────────

    @patch("apps.routines.views.routine_service.list_routines")
    def test_routine_list_success(self, mock_list_routines: MagicMock) -> None:
        """routine_list deve renderizar o template principal com as rotinas."""
        mock_list_routines.return_value = [{"id": self.fake_routine_id, "title": "Teste", "item_count": 2}]
        
        # Fazendo mock também do get_profile_by_id que é chamado dentro do bloco try
        with patch("apps.auth.services.get_profile_by_id") as mock_profile:
            mock_profile.return_value = {"email": "user@example.com"}
            url = reverse("routines:routine_list")
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "routines/routine_list.html")
            self.assertEqual(response.context["child_name"], "User")
            mock_list_routines.assert_called_once_with(parent_id=self.fake_parent_id)

    def test_routine_list_unauthenticated_redirects(self) -> None:
        """Se não houver cookie supabase_session, redireciona para login."""
        self.client.cookies.pop("supabase_session", None)
        url = reverse("routines:routine_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/login/"))

    # ── Testes: routine_builder ───────────────────────────────────────────────

    @patch("apps.routines.views.routine_service.list_categories")
    @patch("apps.routines.views.routine_service.get_all_pictograms_by_category")
    def test_routine_builder_create_mode(self, mock_pics: MagicMock, mock_cats: MagicMock) -> None:
        """routine_builder sem routine_id renderiza no modo de criação."""
        mock_cats.return_value = []
        mock_pics.return_value = {}

        url = reverse("routines:routine_builder_create")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "routines/routine_builder.html")
        self.assertFalse(response.context["is_edit_mode"])

    @patch("apps.routines.views.routine_service.list_categories")
    @patch("apps.routines.views.routine_service.get_all_pictograms_by_category")
    @patch("apps.routines.views.routine_service.get_routine")
    @patch("apps.routines.views.routine_service.get_routine_items")
    def test_routine_builder_edit_mode_success(
        self, mock_items: MagicMock, mock_routine: MagicMock, mock_pics: MagicMock, mock_cats: MagicMock
    ) -> None:
        """routine_builder com routine_id carrega os dados e renderiza em modo de edição."""
        mock_cats.return_value = []
        mock_pics.return_value = {}
        mock_routine.return_value = {"id": str(self.fake_routine_id), "title": "Teste"}
        mock_items.return_value = [{"id": "item1"}]

        url = reverse("routines:routine_builder_edit", kwargs={"routine_id": self.fake_routine_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "routines/routine_builder.html")
        self.assertTrue(response.context["is_edit_mode"])

    @patch("apps.routines.views.routine_service.get_routine")
    def test_routine_builder_edit_mode_not_found(self, mock_routine: MagicMock) -> None:
        """routine_builder com rotina inexistente redireciona para a listagem."""
        mock_routine.return_value = None
        url = reverse("routines:routine_builder_edit", kwargs={"routine_id": self.fake_routine_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/routines/")

    # ── Testes: routine_save ──────────────────────────────────────────────────

    @patch("apps.routines.views.routine_service.save_routine")
    def test_routine_save_success(self, mock_save: MagicMock) -> None:
        """routine_save retorna JSON com status 201 em caso de sucesso (criação)."""
        mock_save.return_value = {"success": True, "routine_id": "123", "redirect": "/routines/"}
        
        url = reverse("routines:routine_save")
        payload = {"title": "Manhã", "pictogram_ids": ["uuid1"]}
        response = self.client.post(url, data=payload, content_type="application/json")
        
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["success"])

    @patch("apps.routines.views.routine_service.save_routine")
    def test_routine_save_validation_error(self, mock_save: MagicMock) -> None:
        """routine_save retorna JSON com status 400 em caso de erro de validação."""
        mock_save.return_value = {"success": False, "error": "validation_error"}
        
        url = reverse("routines:routine_save")
        payload = {"title": "", "pictogram_ids": []}
        response = self.client.post(url, data=payload, content_type="application/json")
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_routine_save_invalid_json(self) -> None:
        """routine_save retorna 400 se o JSON da requisição for malformado."""
        url = reverse("routines:routine_save")
        response = self.client.post(url, data="invalid json", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    # ── Testes: routine_rename ────────────────────────────────────────────────

    @patch("apps.routines.views.routine_service.rename_routine")
    @patch("apps.routines.views.routine_service.list_routines")
    def test_routine_rename_htmx_partial(self, mock_list: MagicMock, mock_rename: MagicMock) -> None:
        """routine_rename deve retornar o partial (_routine_card.html) para injeção via HTMX."""
        mock_rename.return_value = {"success": True, "title": "Novo Título"}
        mock_list.return_value = [{"id": str(self.fake_routine_id), "title": "Novo Título", "item_count": 0}]

        url = reverse("routines:routine_rename", kwargs={"routine_id": self.fake_routine_id})
        payload = {"title": "Novo Título"}
        # Simulamos chamada HTMX (PATCH / JSON)
        response = self.client.patch(
            url, 
            data=payload, 
            content_type="application/json", 
            HTTP_HX_REQUEST="true"
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "routines/partials/_routine_card.html")

    # ── Testes: routine_delete ────────────────────────────────────────────────

    @patch("apps.routines.views.routine_service.delete_routine")
    @patch("apps.routines.views.routine_service.list_routines")
    def test_routine_delete_htmx_success(self, mock_list: MagicMock, mock_delete: MagicMock) -> None:
        """routine_delete deve retornar 200 OK vazio para remoção pelo HTMX."""
        mock_delete.return_value = True
        mock_list.return_value = [{"id": "outra-rotina"}]  # Ainda sobram rotinas
        
        url = reverse("routines:routine_delete", kwargs={"routine_id": self.fake_routine_id})
        response = self.client.delete(url, HTTP_HX_REQUEST="true")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")

    @patch("apps.routines.views.routine_service.delete_routine")
    @patch("apps.routines.views.routine_service.list_routines")
    def test_routine_delete_last_item_trigger(self, mock_list: MagicMock, mock_delete: MagicMock) -> None:
        """routine_delete deve acionar o header showEmptyState quando exclui a última rotina."""
        mock_delete.return_value = True
        mock_list.return_value = []  # Última rotina excluída
        
        url = reverse("routines:routine_delete", kwargs={"routine_id": self.fake_routine_id})
        response = self.client.delete(url, HTTP_HX_REQUEST="true")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("HX-Trigger", response)
        self.assertIn("showEmptyState", response["HX-Trigger"])

    # ── Testes: routine_export_pdf ────────────────────────────────────────────

    @patch("apps.routines.views.routine_service.get_routine_for_export")
    @patch("apps.routines.views.routine_service.generate_routine_pdf")
    def test_routine_export_pdf_success(self, mock_generate: MagicMock, mock_export: MagicMock) -> None:
        """routine_export_pdf deve retornar um FileResponse com Content-Type application/pdf."""
        mock_export.return_value = ({"title": "Rotina"}, [])
        mock_generate.return_value = b"%PDF-1.4 Fake PDF Data"

        with patch("apps.core.services.AuditLogService"):
            url = reverse("routines:routine_export_pdf", kwargs={"routine_id": self.fake_routine_id})
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "application/pdf")
            self.assertIn('filename="Rotina - Rotina.pdf"', response["Content-Disposition"])

    @patch("apps.routines.views.routine_service.get_routine_for_export")
    def test_routine_export_pdf_not_found(self, mock_export: MagicMock) -> None:
        """routine_export_pdf deve retornar 404 se a rotina não existir."""
        mock_export.return_value = None
        url = reverse("routines:routine_export_pdf", kwargs={"routine_id": self.fake_routine_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
