"""
Service Layer para o módulo Routines.

Toda lógica de negócio para rotinas visuais reside aqui.
Views NUNCA devem chamar o Supabase diretamente.

Arquitetura: Anti-ORM (sem Django ORM para dados core).
Todas as operações usam supabase-py com RLS-First.
UUIDs sempre serializados como str() antes de chamadas ao SDK.
"""

from __future__ import annotations

import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, TypedDict
from urllib.request import urlopen

from django.conf import settings
from supabase import Client, create_client

from apps.core.services import AuditLogService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Type Aliases & TypedDicts
# ---------------------------------------------------------------------------

class CategoryDict(TypedDict):
    id: str
    name: str
    display_order: int


class PictogramDict(TypedDict):
    id: str
    category_id: str
    name: str
    image_url: str


class RoutineDict(TypedDict):
    id: str
    parent_id: str
    title: str
    created_at: str
    updated_at: str


class RoutineItemDict(TypedDict):
    id: str
    routine_id: str
    pictogram_id: str
    order_position: int
    # Joined fields (when fetched with pictogram data)
    pictogram_name: str | None
    pictogram_image_url: str | None


class SaveRoutineResult(TypedDict):
    success: bool
    routine_id: str
    title: str
    pictogram_count: int
    redirect: str


# ---------------------------------------------------------------------------
# Supabase Client Helpers
# ---------------------------------------------------------------------------

def get_supabase_client() -> Client:
    """Retorna cliente Supabase com anon key (respeita RLS).

    Usado para operações de leitura pública (pictogramas, categorias).

    Returns:
        Cliente Supabase autenticado com anon key.
    """
    url: str = settings.SUPABASE_URL
    anon_key: str = settings.SUPABASE_ANON_KEY or settings.SUPABASE_KEY

    if not url or not anon_key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_ANON_KEY devem estar configurados.")

    return create_client(url, anon_key)


def get_admin_client() -> Client:
    """Retorna cliente Supabase com service_role key (bypass RLS).

    Usado para operações que requerem acesso administrativo (seed data,
    operações de escrita em tabelas com RLS restritiva, audit logs).

    Returns:
        Cliente Supabase autenticado com service_role key.
    """
    url: str = settings.SUPABASE_URL
    service_key: str = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY

    if not url or not service_key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_KEY devem estar configurados.")

    return create_client(url, service_key)


# ---------------------------------------------------------------------------
# Pictogram Categories — Leitura pública (T018)
# ---------------------------------------------------------------------------

def list_categories() -> list[CategoryDict]:
    """Lista todas as categorias de pictogramas ordenadas por display_order.

    Returns:
        Lista de dicts {id, name, display_order}.
    """
    client: Client = get_admin_client()

    try:
        response = (
            client.table("pictogram_categories")
            .select("id, name, display_order")
            .order("display_order")
            .execute()
        )
        return [
            CategoryDict(
                id=str(row["id"]),
                name=str(row["name"]),
                display_order=int(row["display_order"]),
            )
            for row in (response.data or [])
        ]
    except Exception:
        logger.exception("Failed to list pictogram categories")
        return []


# ---------------------------------------------------------------------------
# Pictograms — Leitura pública (T019, T020)
# ---------------------------------------------------------------------------

def list_pictograms_by_category(category_id: str) -> list[PictogramDict]:
    """Lista pictogramas de uma categoria específica.

    Args:
        category_id: UUID da categoria (str).

    Returns:
        Lista de dicts {id, category_id, name, image_url}.
    """
    client: Client = get_admin_client()

    try:
        response = (
            client.table("pictograms")
            .select("id, category_id, name, image_url")
            .eq("category_id", str(category_id))
            .order("name")
            .execute()
        )
        return [
            PictogramDict(
                id=str(row["id"]),
                category_id=str(row["category_id"]),
                name=str(row["name"]),
                image_url=str(row["image_url"]),
            )
            for row in (response.data or [])
        ]
    except Exception:
        logger.exception("Failed to list pictograms for category %s", category_id)
        return []


def get_all_pictograms_by_category() -> dict[str, list[PictogramDict]]:
    """Retorna todos os pictogramas agrupados por category_id.

    Otimizado: uma única query para carregar todos os pictogramas.

    Returns:
        Dict {category_id: [PictogramDict, ...]}
    """
    client: Client = get_admin_client()

    try:
        response = (
            client.table("pictograms")
            .select("id, category_id, name, image_url")
            .order("name")
            .execute()
        )
        result: dict[str, list[PictogramDict]] = {}
        for row in (response.data or []):
            cat_id = str(row["category_id"])
            if cat_id not in result:
                result[cat_id] = []
            result[cat_id].append(
                PictogramDict(
                    id=str(row["id"]),
                    category_id=cat_id,
                    name=str(row["name"]),
                    image_url=str(row["image_url"]),
                )
            )
        return result
    except Exception:
        logger.exception("Failed to load all pictograms by category")
        return {}


def validate_pictogram_ids(pictogram_ids: list[str]) -> bool:
    """Verifica se todos os UUIDs existem na tabela pictograms.

    Args:
        pictogram_ids: Lista de UUIDs como strings.

    Returns:
        True se todos os IDs existem, False se algum não existe ou erro.
    """
    if not pictogram_ids:
        return False

    client: Client = get_admin_client()

    try:
        # Serializar todos como str (Constitution IV)
        ids_str = [str(pid) for pid in pictogram_ids]
        response = (
            client.table("pictograms")
            .select("id", count="exact")
            .in_("id", ids_str)
            .execute()
        )
        found_count: int = response.count or 0
        return found_count == len(ids_str)
    except Exception:
        logger.exception("Failed to validate pictogram IDs")
        return False


# ---------------------------------------------------------------------------
# Routines — CRUD completo (T021, T035, T036, T045, T046, T047)
# ---------------------------------------------------------------------------

def save_routine(
    parent_id: str,
    title: str,
    pictogram_ids: list[str],
    routine_id: str | None = None,
) -> SaveRoutineResult | dict[str, Any]:
    """Cria ou atualiza uma rotina visual com seus pictogramas.

    Validações:
    - title: 1-100 chars, strip whitespace
    - pictogram_ids: 1-15 UUIDs, todos válidos
    - Se routine_id fornecido (edit): verifica ownership via parent_id

    Args:
        parent_id: UUID do cuidador (str).
        title: Título da rotina.
        pictogram_ids: Lista ordenada de UUIDs de pictogramas.
        routine_id: UUID da rotina existente para edição (None = criar).

    Returns:
        Dict com {success, routine_id, title, pictogram_count, redirect}
        ou {success: False, error, details} em caso de erro.
    """
    # 1. Validar título
    title = title.strip()
    if not title:
        return {
            "success": False,
            "error": "validation_error",
            "details": {"title": ["O título da rotina é obrigatório."]},
        }
    if len(title) > 100:
        return {
            "success": False,
            "error": "validation_error",
            "details": {"title": ["O título deve ter no máximo 100 caracteres."]},
        }

    # 2. Validar pictogram_ids
    if not pictogram_ids:
        return {
            "success": False,
            "error": "validation_error",
            "details": {"pictogram_ids": ["Adicione ao menos um pictograma à rotina."]},
        }
    if len(pictogram_ids) > 15:
        return {
            "success": False,
            "error": "validation_error",
            "details": {"pictogram_ids": ["Máximo de 15 pictogramas por rotina."]},
        }

    # Serializar UUIDs (Constitution IV)
    parent_id_str = str(parent_id)
    ids_str = [str(pid) for pid in pictogram_ids]

    # Validar que todos os pictogramas existem
    if not validate_pictogram_ids(ids_str):
        return {
            "success": False,
            "error": "validation_error",
            "details": {"pictogram_ids": ["Pictograma inválido."]},
        }

    client: Client = get_admin_client()
    audit = AuditLogService()

    try:
        if routine_id is not None:
            # 3. Modo edição: verificar ownership
            routine_id_str = str(routine_id)
            check = (
                client.table("routines")
                .select("id, parent_id")
                .eq("id", routine_id_str)
                .limit(1)
                .execute()
            )
            if not check.data or len(check.data) == 0:
                return {
                    "success": False,
                    "error": "not_found",
                    "message": "Rotina não encontrada.",
                }
            if str(check.data[0]["parent_id"]) != parent_id_str:
                return {
                    "success": False,
                    "error": "forbidden",
                    "message": "Rotina não encontrada ou acesso negado.",
                }

            # c. Deletar itens antigos (batch delete)
            client.table("routine_items").delete().eq("routine_id", routine_id_str).execute()

            # d. Atualizar título e updated_at
            now_iso = datetime.now(timezone.utc).isoformat()
            client.table("routines").update({
                "title": title,
                "updated_at": now_iso,
            }).eq("id", routine_id_str).execute()

            final_routine_id = routine_id_str
            action = "routine.updated"
        else:
            # 4. Modo criação: INSERT nova rotina
            routine_id_str = str(uuid.uuid4())
            client.table("routines").insert({
                "id": routine_id_str,
                "parent_id": parent_id_str,
                "title": title,
            }).execute()
            final_routine_id = routine_id_str
            action = "routine.created"

        # 5. INSERT em massa nos routine_items
        items_to_insert = [
            {
                "id": str(uuid.uuid4()),
                "routine_id": final_routine_id,
                "pictogram_id": str(pic_id),
                "order_position": idx,
            }
            for idx, pic_id in enumerate(ids_str)
        ]
        if items_to_insert:
            client.table("routine_items").insert(items_to_insert).execute()

        # 6. Audit log
        try:
            audit.log(
                user_id=parent_id_str,  # type: ignore[arg-type]
                action=action,
                table_name="routines",
                record_id=final_routine_id,  # type: ignore[arg-type]
                payload={"title": title, "pictogram_count": len(ids_str)},
            )
        except Exception:
            logger.warning("Audit log failed for %s (non-fatal)", action)

        logger.info(
            "Routine saved: id=%s, parent_id=%s, action=%s",
            final_routine_id, parent_id_str, action,
        )

        return {
            "success": True,
            "routine_id": final_routine_id,
            "title": title,
            "pictogram_count": len(ids_str),
            "redirect": "/routines/",
        }

    except Exception:
        logger.exception("Failed to save routine: parent_id=%s", parent_id_str)
        return {
            "success": False,
            "error": "server_error",
            "message": "Erro interno ao salvar a rotina.",
        }


def get_routine(routine_id: str, parent_id: str) -> dict[str, Any] | None:
    """Busca uma rotina pelo ID verificando ownership.

    Args:
        routine_id: UUID da rotina (str).
        parent_id: UUID do cuidador (str).

    Returns:
        Dict com dados da rotina ou None se não encontrada/sem acesso.
    """
    client: Client = get_admin_client()

    try:
        response = (
            client.table("routines")
            .select("id, parent_id, title, created_at, updated_at")
            .eq("id", str(routine_id))
            .eq("parent_id", str(parent_id))
            .limit(1)
            .execute()
        )
        if not response.data or len(response.data) == 0:
            return None

        row = response.data[0]
        return {
            "id": str(row["id"]),
            "parent_id": str(row["parent_id"]),
            "title": str(row["title"]),
            "created_at": str(row.get("created_at", "")),
            "updated_at": str(row.get("updated_at", "")),
        }
    except Exception:
        logger.exception("Failed to get routine: id=%s", routine_id)
        return None


def get_routine_items(routine_id: str) -> list[dict[str, Any]]:
    """Lista os itens de uma rotina com dados do pictograma.

    Inclui name e image_url do pictograma via join.

    Args:
        routine_id: UUID da rotina (str).

    Returns:
        Lista de dicts com dados do item + pictograma, ordenada por order_position.
    """
    client: Client = get_admin_client()

    try:
        response = (
            client.table("routine_items")
            .select("id, routine_id, pictogram_id, order_position, pictograms(id, name, image_url)")
            .eq("routine_id", str(routine_id))
            .order("order_position")
            .execute()
        )
        items = []
        for row in (response.data or []):
            pic = row.get("pictograms") or {}
            items.append({
                "id": str(row["id"]),
                "routine_id": str(row["routine_id"]),
                "pictogram_id": str(row["pictogram_id"]),
                "order_position": int(row["order_position"]),
                "pictogram_name": str(pic.get("name", "")) if pic else "",
                "pictogram_image_url": str(pic.get("image_url", "")) if pic else "",
            })
        return items
    except Exception:
        logger.exception("Failed to get routine items: routine_id=%s", routine_id)
        return []


def list_routines(parent_id: str) -> list[dict[str, Any]]:
    """Lista todas as rotinas de um cuidador com contagem de itens.

    Args:
        parent_id: UUID do cuidador (str).

    Returns:
        Lista de dicts com dados da rotina + item_count, ordenada por updated_at DESC.
    """
    client: Client = get_admin_client()

    try:
        response = (
            client.table("routines")
            .select("id, parent_id, title, created_at, updated_at, routine_items(count)")
            .eq("parent_id", str(parent_id))
            .order("updated_at", desc=True)
            .execute()
        )
        routines = []
        for row in (response.data or []):
            # Contagem de itens via aggregation do Supabase
            items_data = row.get("routine_items", [])
            item_count = 0
            if isinstance(items_data, list):
                if len(items_data) > 0 and isinstance(items_data[0], dict) and "count" in items_data[0]:
                    item_count = items_data[0]["count"]
                else:
                    item_count = len(items_data)
            elif isinstance(items_data, dict) and "count" in items_data:
                item_count = items_data["count"]

            routines.append({
                "id": str(row["id"]),
                "parent_id": str(row["parent_id"]),
                "title": str(row["title"]),
                "created_at": str(row.get("created_at", "")),
                "updated_at": str(row.get("updated_at", "")),
                "item_count": item_count,
            })
        return routines
    except Exception:
        logger.exception("Failed to list routines: parent_id=%s", parent_id)
        return []


def rename_routine(routine_id: str, parent_id: str, new_title: str) -> dict[str, Any]:
    """Renomeia uma rotina verificando ownership.

    Args:
        routine_id: UUID da rotina (str).
        parent_id: UUID do cuidador (str).
        new_title: Novo título (será trimmed, 1-100 chars).

    Returns:
        Dict com {success, routine_id, title} ou {success: False, error, ...}.
    """
    new_title = new_title.strip()
    if not new_title:
        return {
            "success": False,
            "error": "validation_error",
            "details": {"title": ["O título da rotina é obrigatório."]},
        }
    if len(new_title) > 100:
        return {
            "success": False,
            "error": "validation_error",
            "details": {"title": ["O título deve ter no máximo 100 caracteres."]},
        }

    client: Client = get_admin_client()

    try:
        # Verificar ownership antes de atualizar
        check = (
            client.table("routines")
            .select("id, parent_id")
            .eq("id", str(routine_id))
            .eq("parent_id", str(parent_id))
            .limit(1)
            .execute()
        )
        if not check.data or len(check.data) == 0:
            return {
                "success": False,
                "error": "forbidden",
                "message": "Rotina não encontrada ou acesso negado.",
            }

        now_iso = datetime.now(timezone.utc).isoformat()
        client.table("routines").update({
            "title": new_title,
            "updated_at": now_iso,
        }).eq("id", str(routine_id)).eq("parent_id", str(parent_id)).execute()

        # Audit log
        try:
            audit = AuditLogService()
            audit.log(
                user_id=parent_id,  # type: ignore[arg-type]
                action="routine.renamed",
                table_name="routines",
                record_id=routine_id,  # type: ignore[arg-type]
                payload={"new_title": new_title},
            )
        except Exception:
            logger.warning("Audit log failed for routine.renamed (non-fatal)")

        logger.info("Routine renamed: id=%s, new_title=%s", routine_id, new_title)
        return {
            "success": True,
            "routine_id": str(routine_id),
            "title": new_title,
        }
    except Exception:
        logger.exception("Failed to rename routine: id=%s", routine_id)
        return {
            "success": False,
            "error": "server_error",
            "message": "Erro interno ao renomear a rotina.",
        }


def delete_routine(routine_id: str, parent_id: str) -> bool:
    """Deleta uma rotina (hard delete) verificando ownership.

    Os routine_items são removidos automaticamente via ON DELETE CASCADE.

    Args:
        routine_id: UUID da rotina (str).
        parent_id: UUID do cuidador (str).

    Returns:
        True se deletada com sucesso, False se não encontrada.
    """
    client: Client = get_admin_client()

    try:
        # Verificar ownership antes
        check = (
            client.table("routines")
            .select("id")
            .eq("id", str(routine_id))
            .eq("parent_id", str(parent_id))
            .limit(1)
            .execute()
        )
        if not check.data or len(check.data) == 0:
            logger.warning("Routine not found or access denied: id=%s", routine_id)
            return False

        client.table("routines").delete().eq("id", str(routine_id)).eq(
            "parent_id", str(parent_id)
        ).execute()

        # Audit log
        try:
            audit = AuditLogService()
            audit.log(
                user_id=parent_id,  # type: ignore[arg-type]
                action="routine.deleted",
                table_name="routines",
                record_id=routine_id,  # type: ignore[arg-type]
                payload={"deleted": True},
            )
        except Exception:
            logger.warning("Audit log failed for routine.deleted (non-fatal)")

        logger.info("Routine deleted: id=%s, parent_id=%s", routine_id, parent_id)
        return True
    except Exception:
        logger.exception("Failed to delete routine: id=%s", routine_id)
        return False


# ---------------------------------------------------------------------------
# PDF Export (T060, T061)
# ---------------------------------------------------------------------------

def get_routine_for_export(
    routine_id: str,
    parent_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    """Busca rotina + itens com dados completos para exportação PDF.

    Args:
        routine_id: UUID da rotina (str).
        parent_id: UUID do cuidador (str).

    Returns:
        Tuple (routine_dict, items_list) ou None se não encontrada/sem acesso.
    """
    routine = get_routine(routine_id=str(routine_id), parent_id=str(parent_id))
    if routine is None:
        return None

    items = get_routine_items(routine_id=str(routine_id))
    return routine, items


def generate_routine_pdf(routine: dict[str, Any], items: list[dict[str, Any]]) -> bytes:
    """Gera um PDF A4 com o layout da rotina visual.

    Layout:
    - Título centralizado no topo (Helvetica-Bold 18pt)
    - Cada pictograma: número + imagem 50x50px + nome (Helvetica 14pt)
    - 1 pictograma por linha
    - Auto page break após 8 itens (2 páginas para 9-15 itens)
    - Rodapé em cada página: "Autismo em Foco — Gerado em DD/MM/AAAA"

    Args:
        routine: Dict com dados da rotina {id, title, ...}.
        items: Lista ordenada de itens com {pictogram_name, pictogram_image_url, ...}.

    Returns:
        Bytes do PDF gerado.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as pdf_canvas

    buffer = io.BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4

    margin = 15 * mm
    title_y = page_height - margin - 20 * mm
    item_start_y = title_y - 20 * mm
    item_height = 20 * mm  # 50px image + spacing ≈ 18-20mm
    items_per_page = 8
    today = datetime.now().strftime("%d/%m/%Y")
    footer_text = f"Autismo em Foco — Gerado em {today}"

    def draw_footer(canvas: Any) -> None:
        canvas.setFont("Helvetica", 8)
        canvas.setFillColorRGB(0.5, 0.5, 0.5)
        canvas.drawCentredString(page_width / 2, margin / 2 + 3 * mm, footer_text)

    def draw_title(canvas: Any) -> None:
        canvas.setFont("Helvetica-Bold", 18)
        canvas.setFillColorRGB(0.1, 0.1, 0.1)
        canvas.drawCentredString(page_width / 2, title_y, routine.get("title", "Rotina"))

    # --- Página 1 ---
    draw_title(c)

    current_y = item_start_y
    page_item_count = 0

    for idx, item in enumerate(items):
        if page_item_count >= items_per_page:
            # Nova página
            draw_footer(c)
            c.showPage()
            draw_title(c)
            current_y = item_start_y
            page_item_count = 0

        image_x = margin
        image_size = 14 * mm  # ~50px

        # Tentar baixar e renderizar a imagem do pictograma
        image_url: str = item.get("pictogram_image_url", "")
        if image_url:
            try:
                with urlopen(image_url, timeout=5) as img_response:  # noqa: S310
                    img_data = img_response.read()
                    img_buffer = io.BytesIO(img_data)
                    c.drawImage(
                        img_buffer,
                        image_x,
                        current_y - image_size,
                        width=image_size,
                        height=image_size,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
            except Exception:
                # Fallback: quadrado cinza com número
                c.setFillColorRGB(0.85, 0.85, 0.85)
                c.rect(image_x, current_y - image_size, image_size, image_size, fill=1)
                c.setFillColorRGB(0.4, 0.4, 0.4)
                c.setFont("Helvetica", 8)
                c.drawCentredString(
                    image_x + image_size / 2,
                    current_y - image_size / 2 - 3,
                    str(idx + 1),
                )

        # Número do passo
        c.setFont("Helvetica-Bold", 12)
        c.setFillColorRGB(0.08, 0.72, 0.65)  # teal primary
        c.drawString(margin + image_size + 4 * mm, current_y - 5 * mm, f"{idx + 1}.")

        # Nome do pictograma
        c.setFont("Helvetica", 14)
        c.setFillColorRGB(0.1, 0.1, 0.1)
        pic_name = item.get("pictogram_name", "") or f"Passo {idx + 1}"
        c.drawString(margin + image_size + 14 * mm, current_y - 5 * mm, pic_name)

        current_y -= item_height
        page_item_count += 1

    draw_footer(c)
    c.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info(
        "PDF generated: routine_id=%s, items=%d, size=%d bytes",
        routine.get("id", ""),
        len(items),
        len(pdf_bytes),
    )

    return pdf_bytes
