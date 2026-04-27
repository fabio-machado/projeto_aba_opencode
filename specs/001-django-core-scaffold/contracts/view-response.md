# Contract: View Response Pattern

**Version**: 1.0.0  
**Date**: 2026-04-23  
**Scope**: Define o padrão de implementação para views Django no projeto.

---

## Padrão de View

Toda view DEVE seguir este fluxo:

```python
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.template.response import TemplateResponse
from typing import Any

from .services import ExampleService


def example_view(request: HttpRequest) -> HttpResponse:
    """
    View de exemplo demonstrando o padrão correto.
    
    Regras:
    1. Apenas validar input
    2. Chamar service
    3. Retornar response
    """
    # 1. VALIDAÇÃO DE INPUT
    if request.method != "POST":
        return HttpResponseBadRequest("Método não permitido")
    
    user_id = request.user.id  # ou request.session.get("user_id")
    data = request.POST.get("data")
    
    if not data:
        return HttpResponseBadRequest("Dados obrigatórios")
    
    # 2. CHAMAR SERVICE (nenhuma lógica de negócio aqui!)
    service = ExampleService()
    try:
        result = service.create_record(user_id=user_id, data={"field": data})
    except ValueError as e:
        return HttpResponseBadRequest(str(e))
    except PermissionError:
        return HttpResponse("Forbidden", status=403)
    
    # 3. RETORNAR RESPONSE
    # Se HTMX request: partial
    if request.headers.get("HX-Request"):
        return TemplateResponse(
            request,
            "core/partials/_example_partial.html",
            {"result": result}
        )
    
    # Se request normal: página completa
    return TemplateResponse(
        request,
        "core/example_page.html",
        {"result": result}
    )
```

## Regras Obrigatórias

1. **Zero Lógica de Negócio**: Views não devem conter regras de negócio, validações complexas, ou transformações de dados
2. **Type Hints**: Assinatura da view deve tipar `request: HttpRequest` e retorno `HttpResponse`
3. **HTMX Detection**: Verificar `request.headers.get("HX-Request")` para decidir entre partial ou página completa
4. **Error Handling**: Capturar exceções do service e retornar status HTTP apropriado
5. **User Injection**: Passar `user_id` explicitamente para o service (não confiar no request dentro do service)

## Anti-Patterns Proibidos

```python
# ❌ NUNCA faça isso em views.py:

# Lógica de negócio na view
def create_patient(request):
    if request.POST["age"] < 0:  # Validação de negócio → vai para service
        ...
    patient = Patient.objects.create(...)  # ORM para dados core → proibido

# Query direta ao banco
patients = Patient.objects.filter(parent_id=request.user.id)  # Use service

# UUID não serializado
service.create(id=uuid.uuid4())  # Sempre converter para str

# Acesso a settings/supabase direto na view
from supabase import create_client  # Isso vai para service.py
```

## HTMX Swap Targets

Quando retornando partials, usar `id` consistente para o elemento alvo:

```html
<!-- O partial deve conter o mesmo ID do elemento que será substituído -->
<div id="patient-list">
  {% for patient in patients %}
    <div>{{ patient.name }}</div>
  {% endfor %}
</div>
```

## Status Codes para HTMX

| Cenário | Status | Comportamento HTMX |
|---------|--------|-------------------|
| Sucesso | 200 | Swap normal do conteúdo |
| Validação | 400 | Swap do conteúdo de erro (se `hx-swap="outerHTML"`) |
| Não autenticado | 401 | Redirecionar para login (via `HX-Redirect`) |
| Sem permissão | 403 | Mostrar mensagem de erro |
| Não encontrado | 404 | Mostrar mensagem de erro |
| Erro interno | 500 | Mostrar mensagem genérica (nunca detalhes técnicos) |
