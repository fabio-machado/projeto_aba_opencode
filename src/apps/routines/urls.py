"""
URL configuration para o módulo Routines.

Rotas:
  GET  /routines/                       → routine_list (mural de rotinas)
  GET  /routines/create/               → routine_builder (criar nova rotina)
  GET  /routines/<uuid:routine_id>/    → routine_builder (editar rotina existente)
  POST /routines/save/                 → routine_save (salvar/atualizar via JSON)
  PATCH/POST /routines/<uuid>/rename/  → routine_rename (renomear via HTMX)
  DELETE/POST /routines/<uuid>/delete/ → routine_delete (excluir via HTMX)
  GET  /routines/<uuid>/export/        → routine_export_pdf (download PDF)
"""

from django.urls import path

from . import views

app_name = "routines"

urlpatterns = [
    # Mural de rotinas (lista todos os cards)
    path("", views.routine_list, name="routine_list"),

    # Construtor — criar nova rotina
    path("create/", views.routine_builder, name="routine_builder_create"),

    # Construtor — editar rotina existente
    path("<uuid:routine_id>/", views.routine_builder, name="routine_builder_edit"),

    # Salvar rotina (create ou edit) via POST JSON
    path("save/", views.routine_save, name="routine_save"),

    # Renomear rotina via HTMX (aceita PATCH via method override ou POST)
    path("<uuid:routine_id>/rename/", views.routine_rename, name="routine_rename"),

    # Excluir rotina via HTMX (aceita DELETE via method override ou POST)
    path("<uuid:routine_id>/delete/", views.routine_delete, name="routine_delete"),

    # Exportar rotina como PDF
    path("<uuid:routine_id>/export/", views.routine_export_pdf, name="routine_export_pdf"),
]
