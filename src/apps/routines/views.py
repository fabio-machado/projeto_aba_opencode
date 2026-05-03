"""
Views para o módulo Routines.

Arquitetura: Service Layer Pattern (Constitution III).
Views APENAS validam, extraem parent_id da sessão, e delegam para services.py.
Sem lógica de negócio nas views.

Auth: Toda rota é protegida pelo LoginRequiredMiddleware.
parent_id: Extraído do cookie JWT supabase_session (decodificado sem verificação de assinatura).
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any
from uuid import UUID

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseNotFound,
    JsonResponse,
)
from django.template.response import TemplateResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import services as routine_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper — extrai parent_id do JWT na sessão
# ---------------------------------------------------------------------------

def _get_parent_id(request: HttpRequest) -> str | None:
    """Extrai o user_id (sub) do JWT de sessão Supabase.

    O middleware LoginRequiredMiddleware já validou o token — aqui apenas
    decodificamos o payload para extrair o sub sem verificar assinatura.

    Args:
        request: Requisição Django com cookie supabase_session.

    Returns:
        UUID do usuário como str, ou None se não encontrado.
    """
    access_token: str = request.COOKIES.get("supabase_session", "")
    if not access_token:
        return None

    try:
        parts = access_token.split(".")
        if len(parts) != 3:
            return None

        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload: dict = json.loads(payload_bytes)
        user_id = str(payload.get("sub", ""))
        return user_id if user_id else None

    except Exception:
        logger.exception("Failed to extract parent_id from JWT")
        return None


# ---------------------------------------------------------------------------
# US3: Mural de Rotinas (T048)
# ---------------------------------------------------------------------------

@require_GET
def routine_list(request: HttpRequest) -> HttpResponse:
    """Lista todas as rotinas do cuidador no mural de cards.

    GET /routines/

    Context:
        routines: Lista de dicts com dados das rotinas + item_count
        has_routines: bool
        child_name: Nome da criança (do perfil) ou fallback
    """
    parent_id = _get_parent_id(request)
    if not parent_id:
        from django.shortcuts import redirect
        return redirect("/login/")

    routines: list[dict[str, Any]] = routine_service.list_routines(parent_id=parent_id)

    # Tentar obter nome da criança/usuário do perfil
    child_name = "Minhas Rotinas"
    try:
        from apps.auth import services as auth_service
        profile = auth_service.get_profile_by_id(parent_id)
        if profile and profile.get("email"):
            # Usar parte antes do @ como nome amigável
            email_name = profile["email"].split("@")[0]
            child_name = email_name.title()
    except Exception:
        logger.warning("Could not resolve child name, using fallback")

    return TemplateResponse(
        request,
        "routines/routine_list.html",
        context={
            "routines": routines,
            "has_routines": len(routines) > 0,
            "child_name": child_name,
        },
    )


# ---------------------------------------------------------------------------
# US1 + US2: Construtor de Rotinas (T023, T037)
# ---------------------------------------------------------------------------

@require_GET
def routine_builder(request: HttpRequest, routine_id: UUID | None = None) -> HttpResponse:
    """Renderiza o construtor de rotinas (criar ou editar).

    GET /routines/create/         → Modo criação
    GET /routines/<uuid>/         → Modo edição

    Context:
        categories: Lista de categorias de pictogramas
        pictograms_by_category: Dict {category_id: [pictograms]}
        routine: Dict com dados da rotina (None se criação)
        items: Lista de itens da rotina ([] se criação)
        is_edit_mode: bool
    """
    parent_id = _get_parent_id(request)
    if not parent_id:
        from django.shortcuts import redirect
        return redirect("/login/")

    categories = routine_service.list_categories()
    pictograms_by_category = routine_service.get_all_pictograms_by_category()

    routine: dict[str, Any] | None = None
    items: list[dict[str, Any]] = []
    is_edit_mode = False

    if routine_id is not None:
        # Modo edição: carregar rotina existente
        routine = routine_service.get_routine(
            routine_id=str(routine_id),
            parent_id=parent_id,
        )
        if routine is not None:
            items = routine_service.get_routine_items(routine_id=str(routine_id))
            is_edit_mode = True
        else:
            # Rotina não encontrada ou acesso negado → redirecionar
            from django.shortcuts import redirect
            return redirect("/routines/")

    return TemplateResponse(
        request,
        "routines/routine_builder.html",
        context={
            "categories": categories,
            "pictograms_by_category": pictograms_by_category,
            "routine": routine,
            "items": items,
            "is_edit_mode": is_edit_mode,
        },
    )


# ---------------------------------------------------------------------------
# US1 + US2: Salvar Rotina via JSON (T022)
# ---------------------------------------------------------------------------

@require_POST
@csrf_exempt
def routine_save(request: HttpRequest) -> JsonResponse:
    """Cria ou atualiza uma rotina via POST JSON.

    POST /routines/save/
    Content-Type: application/json

    Body:
        {
          "title": "Hora do Banho",
          "pictogram_ids": ["uuid1", "uuid2", ...],
          "routine_id": "uuid"  // opcional — edição
        }

    Returns:
        JsonResponse com {success, routine_id, title, pictogram_count, redirect}
        ou {success: false, error, details} em caso de erro.
    """
    parent_id = _get_parent_id(request)
    if not parent_id:
        return JsonResponse({"success": False, "error": "unauthorized"}, status=401)

    try:
        body: dict[str, Any] = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse(
            {"success": False, "error": "validation_error", "details": {"body": ["JSON inválido."]}},
            status=400,
        )

    title: str = str(body.get("title", "")).strip()
    pictogram_ids: list[str] = body.get("pictogram_ids", [])
    routine_id: str | None = body.get("routine_id") or None

    if not isinstance(pictogram_ids, list):
        return JsonResponse(
            {"success": False, "error": "validation_error", "details": {"pictogram_ids": ["Lista inválida."]}},
            status=400,
        )

    result = routine_service.save_routine(
        parent_id=parent_id,
        title=title,
        pictogram_ids=[str(p) for p in pictogram_ids],
        routine_id=str(routine_id) if routine_id else None,
    )

    if not result.get("success"):
        error_code = result.get("error", "server_error")
        if error_code == "validation_error":
            return JsonResponse(result, status=400)
        elif error_code in ("forbidden", "not_found"):
            status_code = 403 if error_code == "forbidden" else 404
            return JsonResponse(result, status=status_code)
        else:
            return JsonResponse(result, status=500)

    status_code = 201 if not body.get("routine_id") else 200
    return JsonResponse(result, status=status_code)


# ---------------------------------------------------------------------------
# US3: Renomear Rotina via HTMX (T049)
# ---------------------------------------------------------------------------

def routine_rename(request: HttpRequest, routine_id: UUID) -> HttpResponse:
    """Renomeia uma rotina e retorna o card atualizado via HTMX.

    PATCH /routines/<uuid>/rename/

    Body (JSON ou form):
        {"title": "Novo Título"}

    Returns:
        Partial HTML do card atualizado (hx-swap="outerHTML")
        ou JsonResponse com erro.
    """
    if request.method not in ("PATCH", "POST"):
        return HttpResponse(status=405)

    parent_id = _get_parent_id(request)
    if not parent_id:
        return JsonResponse({"success": False, "error": "unauthorized"}, status=401)

    try:
        body: dict[str, Any] = json.loads(request.body)
        new_title = str(body.get("title", "")).strip()
    except (json.JSONDecodeError, ValueError):
        # Fallback para form data
        new_title = request.POST.get("title", "").strip()

    result = routine_service.rename_routine(
        routine_id=str(routine_id),
        parent_id=parent_id,
        new_title=new_title,
    )

    if not result.get("success"):
        error_code = result.get("error", "server_error")
        if error_code == "validation_error":
            return JsonResponse(result, status=400)
        else:
            return JsonResponse(result, status=403)

    # Buscar dados atualizados da rotina para renderizar o card
    routines = routine_service.list_routines(parent_id=parent_id)
    updated_routine = next(
        (r for r in routines if str(r["id"]) == str(routine_id)),
        {"id": str(routine_id), "title": new_title, "item_count": 0},
    )

    return TemplateResponse(
        request,
        "routines/partials/_routine_card.html",
        context={"routine": updated_routine},
    )


# ---------------------------------------------------------------------------
# US3: Excluir Rotina via HTMX (T050)
# ---------------------------------------------------------------------------

def routine_delete(request: HttpRequest, routine_id: UUID) -> HttpResponse:
    """Exclui uma rotina e retorna resposta vazia para HTMX.

    DELETE /routines/<uuid>/delete/

    Returns:
        200 OK vazio (HTMX remove o elemento via hx-swap="delete")
        ou 404/403 em caso de erro.
    """
    if request.method not in ("DELETE", "POST"):
        return HttpResponse(status=405)

    parent_id = _get_parent_id(request)
    if not parent_id:
        return JsonResponse({"success": False, "error": "unauthorized"}, status=401)

    success = routine_service.delete_routine(
        routine_id=str(routine_id),
        parent_id=parent_id,
    )

    if not success:
        return HttpResponse(status=404)

    # Verificar se era a última rotina (para resposta com oob swap do empty state)
    remaining_routines = routine_service.list_routines(parent_id=parent_id)
    if not remaining_routines:
        # Sinalizar ao frontend para mostrar empty state
        response = HttpResponse(status=200)
        response["HX-Trigger"] = '{"showEmptyState": true}'
        return response

    return HttpResponse(status=200)


# ---------------------------------------------------------------------------
# US4: Exportar Rotina em PDF (T062)
# ---------------------------------------------------------------------------

@require_GET
def routine_export_pdf(request: HttpRequest, routine_id: UUID) -> HttpResponse:
    """Gera e retorna PDF de uma rotina para download.

    GET /routines/<uuid>/export/

    Returns:
        FileResponse com Content-Type: application/pdf
        ou 404 se rotina não encontrada.
    """
    parent_id = _get_parent_id(request)
    if not parent_id:
        from django.shortcuts import redirect
        return redirect("/login/")

    result = routine_service.get_routine_for_export(
        routine_id=str(routine_id),
        parent_id=parent_id,
    )

    if result is None:
        return HttpResponseNotFound(
            "<h1>Rotina não encontrada</h1>"
            "<p>A rotina solicitada não existe ou você não tem acesso a ela.</p>"
        )

    routine_data, items = result

    try:
        pdf_bytes = routine_service.generate_routine_pdf(
            routine=routine_data,
            items=items,
        )
    except Exception:
        logger.exception("PDF generation failed for routine_id=%s", routine_id)
        from django.http import HttpResponseServerError
        return HttpResponseServerError(
            "<h1>Erro ao gerar PDF</h1>"
            "<p>Ocorreu um erro ao gerar o PDF. Por favor, tente novamente em instantes.</p>"
        )

    # Sanitizar nome do arquivo
    safe_title = routine_data.get("title", "Rotina").replace("/", "-").replace("\\", "-")
    filename = f"Rotina - {safe_title}.pdf"

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Content-Length"] = str(len(pdf_bytes))

    # Audit log para exportação
    try:
        from apps.core.services import AuditLogService
        audit = AuditLogService()
        audit.log(
            user_id=parent_id,  # type: ignore[arg-type]
            action="routine.exported",
            table_name="routines",
            record_id=str(routine_id),  # type: ignore[arg-type]
            payload={"format": "pdf"},
        )
    except Exception:
        logger.warning("Audit log failed for routine.exported (non-fatal)")

    return response
