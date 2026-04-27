# Contract: App Shell Response

**Feature**: 002-app-shell-identidade-visual  
**Date**: 2026-04-24  
**Purpose**: Definir a estrutura do template `base.html` e convenções de partials para o App Shell.

---

## Response Format

O App Shell é entregue como um template Django `base.html` que serve como estrutura mestre para todas as páginas da aplicação.

### base.html Structure

```html
<!DOCTYPE html>
<html lang="pt-BR" x-data="appShell()" :class="{ 'dark': darkMode }">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{% block title %}Autismo em Foco{% endblock %}</title>
  
  <!-- Anti-FART script -->
  <script src="{% static 'js/theme.js' %}"></script>
  
  <!-- Tailwind CSS CDN + Config -->
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: { /* design tokens */ },
          fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] },
        },
      },
    };
  </script>
  <script src="https://cdn.tailwindcss.com"></script>
  
  <!-- Google Fonts: Inter -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  
  <!-- HTMX -->
  <script src="https://unpkg.com/htmx.org@1.9.12"></script>
  
  <!-- Alpine.js -->
  <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
  
  <!-- Heroicons -->
  <script src="https://unpkg.com/heroicons@2.0.13/24/outline/index.js" type="module"></script>
</head>
<body class="bg-surface text-on-surface font-sans antialiased">
  
  <!-- Header -->
  {% include "partials/nav/_header.html" %}
  
  <!-- Main Content Area -->
  <main id="app-canvas" class="pt-16 pb-16 px-4 overflow-y-auto" hx-target="#app-canvas" hx-swap="innerHTML">
    {% block content %}{% endblock %}
  </main>
  
  <!-- Bottom Navigation -->
  {% include "partials/nav/_bottom_nav.html" %}
  
  <!-- Bottom Sheet -->
  {% include "partials/nav/_bottom_sheet.html" %}
  
</body>
</html>
```

### Partial Conventions

| Partial | Path | Purpose |
|---------|------|---------|
| Header | `templates/partials/nav/_header.html` | Logo, notificações, menu de perfil |
| Bottom Nav | `templates/partials/nav/_bottom_nav.html` | 5 itens de navegação (FAB central) |
| Bottom Sheet | `templates/partials/nav/_bottom_sheet.html` | Painel de criação rápida |

### Block Definitions

| Block | Description | Required |
|-------|-------------|----------|
| `title` | Título da página (sufixo " \| Autismo em Foco") | Optional |
| `content` | Conteúdo principal da página | Required |
| `extra_css` | CSS adicional específico da página | Optional |
| `extra_js` | JavaScript adicional específico da página | Optional |

### HTMX Targets

- `#app-canvas` é o alvo padrão para todos os swaps HTMX.
- As partials de navegação NÃO devem ser alvos de swap — são parte do shell fixo.
- Apenas o conteúdo dentro de `#app-canvas` deve ser substituído durante navegação.

---

## Invariants

1. O `<html>` deve sempre ter a classe `dark` quando o modo escuro está ativo.
2. O `<main id="app-canvas">` deve sempre existir e ter `hx-target` e `hx-swap` configurados.
3. O header e bottom nav devem ser `position: fixed` para permanecerem visíveis durante scroll.
4. O `padding-top` e `padding-bottom` do `<main>` devem compensar a altura do header e bottom nav respectivamente.
