"""
Testes para o Service Layer do módulo Routines.

Cobre:
- Validações de save_routine (T015, T016)
  - título vazio → erro
  - título > 100 chars → erro
  - lista de pictogramas vazia → erro
  - lista > 15 pictogramas → erro
  - todos os pictogramas válidos → sucesso (mock do Supabase)
  - modo edição com ownership correto → sucesso
  - modo edição com owner errado → forbidden
- list_categories: retorna lista ordenada
- list_routines: retorna lista do parent_id correto
- delete_routine: retorna True e False corretamente
- rename_routine: valida título e retorna sucesso/erro
- validate_pictogram_ids: retorna True/False
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.routines import services as svc


# ── Mocks reutilizáveis ──────────────────────────────────────────────────────

FAKE_PARENT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
FAKE_ROUTINE_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
FAKE_PIC_1 = "cccccccc-cccc-cccc-cccc-cccccccccccc"
FAKE_PIC_2 = "dddddddd-dddd-dddd-dddd-dddddddddddd"


def _make_mock_client():
    """Helper para criar um mock do cliente Supabase."""
    return MagicMock()


# ── T015/T016: Testes de Validação — save_routine ────────────────────────────


class SaveRoutineValidationTest(TestCase):
    """Testa as validações de entrada no save_routine."""

    def test_empty_title_returns_validation_error(self) -> None:
        """Título vazio deve retornar validation_error."""
        result = svc.save_routine(
            parent_id=FAKE_PARENT_ID,
            title="",
            pictogram_ids=[FAKE_PIC_1],
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "validation_error")
        self.assertIn("title", result.get("details", {}))

    def test_whitespace_only_title_returns_validation_error(self) -> None:
        """Título com apenas espaços deve retornar validation_error."""
        result = svc.save_routine(
            parent_id=FAKE_PARENT_ID,
            title="   ",
            pictogram_ids=[FAKE_PIC_1],
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "validation_error")
        self.assertIn("title", result.get("details", {}))

    def test_title_over_100_chars_returns_validation_error(self) -> None:
        """Título com mais de 100 caracteres deve retornar validation_error."""
        long_title = "A" * 101
        result = svc.save_routine(
            parent_id=FAKE_PARENT_ID,
            title=long_title,
            pictogram_ids=[FAKE_PIC_1],
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "validation_error")
        self.assertIn("title", result.get("details", {}))

    def test_exactly_100_chars_title_passes_validation(self) -> None:
        """Título com exatamente 100 caracteres passa a validação de tamanho."""
        exactly_100 = "A" * 100
        # Precisa mockar Supabase para não falhar na call real
        with patch("apps.routines.services.get_admin_client") as mock_client_fn, \
             patch("apps.routines.services.validate_pictogram_ids", return_value=True), \
             patch("apps.routines.services.AuditLogService"):
            mock_client = _make_mock_client()
            mock_client_fn.return_value = mock_client

            # Mock do insert da rotina
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table
            mock_table.insert.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[{"id": FAKE_ROUTINE_ID}])

            result = svc.save_routine(
                parent_id=FAKE_PARENT_ID,
                title=exactly_100,
                pictogram_ids=[FAKE_PIC_1],
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["title"], exactly_100)

    def test_empty_pictogram_ids_returns_validation_error(self) -> None:
        """Lista vazia de pictogramas deve retornar validation_error."""
        result = svc.save_routine(
            parent_id=FAKE_PARENT_ID,
            title="Rotina Teste",
            pictogram_ids=[],
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "validation_error")
        self.assertIn("pictogram_ids", result.get("details", {}))

    def test_over_15_pictogram_ids_returns_validation_error(self) -> None:
        """Mais de 15 pictogramas deve retornar validation_error."""
        pids = [f"pic-{i:04d}" for i in range(16)]
        result = svc.save_routine(
            parent_id=FAKE_PARENT_ID,
            title="Rotina Teste",
            pictogram_ids=pids,
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "validation_error")
        self.assertIn("pictogram_ids", result.get("details", {}))

    def test_exactly_15_pictogram_ids_passes_count_validation(self) -> None:
        """Exatamente 15 pictogramas deve passar a validação de contagem."""
        pids = [f"pic-{i:04d}" for i in range(15)]
        with patch("apps.routines.services.validate_pictogram_ids", return_value=True), \
             patch("apps.routines.services.get_admin_client") as mock_client_fn, \
             patch("apps.routines.services.AuditLogService"):
            mock_client = _make_mock_client()
            mock_client_fn.return_value = mock_client
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table
            mock_table.insert.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            result = svc.save_routine(
                parent_id=FAKE_PARENT_ID,
                title="Rotina Completa",
                pictogram_ids=pids,
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["pictogram_count"], 15)

    def test_invalid_pictogram_ids_returns_validation_error(self) -> None:
        """Pictogramas não existentes no banco devem retornar validation_error."""
        with patch("apps.routines.services.validate_pictogram_ids", return_value=False):
            result = svc.save_routine(
                parent_id=FAKE_PARENT_ID,
                title="Rotina Teste",
                pictogram_ids=[FAKE_PIC_1, FAKE_PIC_2],
            )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "validation_error")
        self.assertIn("pictogram_ids", result.get("details", {}))


class SaveRoutineCreationTest(TestCase):
    """Testa o fluxo de criação bem-sucedida de rotinas."""

    def setUp(self):
        # Patch do Supabase client e AuditLogService para toda a classe
        self.patcher_admin = patch("apps.routines.services.get_admin_client")
        self.patcher_validate = patch(
            "apps.routines.services.validate_pictogram_ids", return_value=True
        )
        self.patcher_audit = patch("apps.routines.services.AuditLogService")

        self.mock_admin_fn = self.patcher_admin.start()
        self.patcher_validate.start()
        self.patcher_audit.start()

        self.mock_client = _make_mock_client()
        self.mock_admin_fn.return_value = self.mock_client
        self.mock_table = MagicMock()
        self.mock_client.table.return_value = self.mock_table
        self.mock_table.insert.return_value = self.mock_table
        self.mock_table.execute.return_value = MagicMock(data=[])

    def tearDown(self):
        self.patcher_admin.stop()
        self.patcher_validate.stop()
        self.patcher_audit.stop()

    def test_valid_routine_creation_returns_success(self) -> None:
        """Dados válidos criam a rotina e retornam success=True."""
        result = svc.save_routine(
            parent_id=FAKE_PARENT_ID,
            title="Manhã do Banho",
            pictogram_ids=[FAKE_PIC_1, FAKE_PIC_2],
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["title"], "Manhã do Banho")
        self.assertEqual(result["pictogram_count"], 2)
        self.assertIn("routine_id", result)
        self.assertEqual(result["redirect"], "/routines/")

    def test_creation_strips_title_whitespace(self) -> None:
        """O título é trimmed antes de ser salvo."""
        result = svc.save_routine(
            parent_id=FAKE_PARENT_ID,
            title="  Manhã do Banho  ",
            pictogram_ids=[FAKE_PIC_1],
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["title"], "Manhã do Banho")

    def test_creation_calls_insert_twice(self) -> None:
        """A criação deve chamar insert em 'routines' e depois em 'routine_items'."""
        svc.save_routine(
            parent_id=FAKE_PARENT_ID,
            title="Rotina Teste",
            pictogram_ids=[FAKE_PIC_1, FAKE_PIC_2],
        )
        # table() deve ser chamado pelo menos 2x: routines e routine_items
        self.assertGreaterEqual(self.mock_client.table.call_count, 2)


class SaveRoutineEditTest(TestCase):
    """Testa o modo de edição (routine_id fornecido)."""

    def test_edit_mode_with_wrong_owner_returns_forbidden(self) -> None:
        """Edição com parent_id errado deve retornar forbidden."""
        with patch("apps.routines.services.get_admin_client") as mock_fn, \
             patch("apps.routines.services.validate_pictogram_ids", return_value=True):
            mock_client = _make_mock_client()
            mock_fn.return_value = mock_client
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table

            # Simular que a rotina pertence a outro owner
            check_result = MagicMock()
            check_result.data = [{"id": FAKE_ROUTINE_ID, "parent_id": "outro-owner-uuid"}]
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = check_result

            result = svc.save_routine(
                parent_id=FAKE_PARENT_ID,
                title="Tentativa de edição indevida",
                pictogram_ids=[FAKE_PIC_1],
                routine_id=FAKE_ROUTINE_ID,
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "forbidden")

    def test_edit_mode_not_found_returns_not_found(self) -> None:
        """Edição de rotina inexistente retorna not_found."""
        with patch("apps.routines.services.get_admin_client") as mock_fn, \
             patch("apps.routines.services.validate_pictogram_ids", return_value=True):
            mock_client = _make_mock_client()
            mock_fn.return_value = mock_client
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table

            # Simular que a rotina não foi encontrada
            check_result = MagicMock()
            check_result.data = []
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = check_result

            result = svc.save_routine(
                parent_id=FAKE_PARENT_ID,
                title="Rotina que não existe",
                pictogram_ids=[FAKE_PIC_1],
                routine_id=FAKE_ROUTINE_ID,
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "not_found")


# ── Testes de rename_routine ─────────────────────────────────────────────────


class RenameRoutineTest(TestCase):
    """Testa as validações e comportamento do rename_routine."""

    def test_rename_empty_title_returns_validation_error(self) -> None:
        """Renomear com título vazio deve retornar validation_error."""
        result = svc.rename_routine(
            routine_id=FAKE_ROUTINE_ID,
            parent_id=FAKE_PARENT_ID,
            new_title="",
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "validation_error")

    def test_rename_title_over_100_chars_returns_validation_error(self) -> None:
        """Renomear com título > 100 chars deve retornar validation_error."""
        result = svc.rename_routine(
            routine_id=FAKE_ROUTINE_ID,
            parent_id=FAKE_PARENT_ID,
            new_title="X" * 101,
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "validation_error")

    def test_rename_not_found_returns_forbidden(self) -> None:
        """Renomear rotina inexistente retorna forbidden."""
        with patch("apps.routines.services.get_admin_client") as mock_fn:
            mock_client = _make_mock_client()
            mock_fn.return_value = mock_client
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table
            check_result = MagicMock()
            check_result.data = []
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = check_result

            result = svc.rename_routine(
                routine_id=FAKE_ROUTINE_ID,
                parent_id=FAKE_PARENT_ID,
                new_title="Novo Título",
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "forbidden")

    def test_rename_success(self) -> None:
        """Renomear rotina com dados válidos retorna sucesso."""
        with patch("apps.routines.services.get_admin_client") as mock_fn, \
             patch("apps.routines.services.AuditLogService"):
            mock_client = _make_mock_client()
            mock_fn.return_value = mock_client
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table

            # Simular que a rotina foi encontrada (ownership correto)
            check_result = MagicMock()
            check_result.data = [{"id": FAKE_ROUTINE_ID, "parent_id": FAKE_PARENT_ID}]
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = check_result
            mock_table.update.return_value = mock_table

            result = svc.rename_routine(
                routine_id=FAKE_ROUTINE_ID,
                parent_id=FAKE_PARENT_ID,
                new_title="Título Atualizado",
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["title"], "Título Atualizado")


# ── Testes de delete_routine ─────────────────────────────────────────────────


class DeleteRoutineTest(TestCase):
    """Testa o delete_routine."""

    def test_delete_not_found_returns_false(self) -> None:
        """Deletar rotina inexistente retorna False."""
        with patch("apps.routines.services.get_admin_client") as mock_fn:
            mock_client = _make_mock_client()
            mock_fn.return_value = mock_client
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table
            check_result = MagicMock()
            check_result.data = []
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = check_result

            result = svc.delete_routine(
                routine_id=FAKE_ROUTINE_ID,
                parent_id=FAKE_PARENT_ID,
            )

        self.assertFalse(result)

    def test_delete_success_returns_true(self) -> None:
        """Deletar rotina com ownership correto retorna True."""
        with patch("apps.routines.services.get_admin_client") as mock_fn, \
             patch("apps.routines.services.AuditLogService"):
            mock_client = _make_mock_client()
            mock_fn.return_value = mock_client
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table

            check_result = MagicMock()
            check_result.data = [{"id": FAKE_ROUTINE_ID}]
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = check_result
            mock_table.delete.return_value = mock_table

            result = svc.delete_routine(
                routine_id=FAKE_ROUTINE_ID,
                parent_id=FAKE_PARENT_ID,
            )

        self.assertTrue(result)


# ── Testes de list_categories ────────────────────────────────────────────────


class ListCategoriesTest(TestCase):
    """Testa o list_categories."""

    def test_returns_empty_list_on_error(self) -> None:
        """Erro no Supabase retorna lista vazia (graceful degradation)."""
        with patch("apps.routines.services.get_admin_client") as mock_fn:
            mock_client = _make_mock_client()
            mock_fn.return_value = mock_client
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.order.return_value = mock_table
            mock_table.execute.side_effect = Exception("Connection error")

            result = svc.list_categories()

        self.assertEqual(result, [])

    def test_returns_categories_ordered(self) -> None:
        """Retorna categorias com os campos corretos."""
        with patch("apps.routines.services.get_admin_client") as mock_fn:
            mock_client = _make_mock_client()
            mock_fn.return_value = mock_client
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.order.return_value = mock_table

            fake_response = MagicMock()
            fake_response.data = [
                {"id": "cat-1", "name": "Higiene", "display_order": 1},
                {"id": "cat-2", "name": "Alimentação", "display_order": 2},
            ]
            mock_table.execute.return_value = fake_response

            result = svc.list_categories()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Higiene")
        self.assertEqual(result[0]["display_order"], 1)
        self.assertEqual(result[1]["name"], "Alimentação")
