# Contract: HTMX Partial Response

**Version**: 1.0.0  
**Date**: 2026-04-23  
**Scope**: Define o formato padrão de resposta para todas as trocas parciais HTMX na aplicação.

---

## Request Format

Todas as requisições que esperam partials DEVEm incluir o header:

```
HX-Request: true
```

Isso é automaticamente enviado pelo HTMX em requests AJAX.

## Response Format

### Sucesso (2xx)

```html
<!-- Fragmento HTML puro — sem html, head, body -->
<div id="target-element">
  <!-- conteúdo atualizado -->
</div>
```

Headers opcionais:
```
HX-Trigger: eventName          # Dispara evento Alpine.js após swap
HX-Trigger-After-Settle: eventName  # Dispara após animação/transition
HX-Redirect: /url              # Redirecionamento full-page (casos especiais)
```

### Erro (4xx, 5xx)

```html
<div class="error-message" role="alert">
  <p>Mensagem amigável para o usuário</p>
</div>
```

Status codes:
- `400`: Validação de input falhou
- `401`: Não autenticado
- `403`: Sem permissão (RLS violation)
- `404`: Recurso não encontrado
- `422`: Dados inválidos (negócio)
- `500`: Erro interno (nunca expor detalhes técnicos)

## Convenções de Nomenclatura

- Templates parciais: `_<action>_<entity>_partial.html`
- Exemplos: `_create_patient_partial.html`, `_list_behaviors_partial.html`
- Diretório: `templates/<app_name>/partials/`

## Regras da Constitution

1. **Zero Full Page Reloads**: Todo conteúdo dinâmico deve usar este formato de partial
2. **Anti-SPA**: Nenhum JSON response para UI; sempre HTML fragment
3. **UX Fricção Zero**: Partials devem ser pequenos (< 5KB) para swap rápido (< 200ms)
