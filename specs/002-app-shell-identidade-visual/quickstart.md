# Quickstart: App Shell e Identidade Visual

**Feature**: 002-app-shell-identidade-visual  
**Date**: 2026-04-24  
**Purpose**: Guia rápido para usar o App Shell e os design tokens em novas páginas e features.

---

## Estrutura do App Shell

Todas as páginas do SaaS devem estender `base.html`:

```django
{% extends "base.html" %}

{% block title %}Minha Página{% endblock %}

{% block content %}
  <!-- Seu conteúdo aqui -->
{% endblock %}
```

O App Shell já inclui automaticamente:
- Header fixo (logo, notificações, menu de perfil)
- Área de conteúdo scrollável (`#app-canvas`)
- Barra de navegação inferior com FAB
- Bottom sheet de criação rápida
- Suporte a dark mode
- Fonte Inter e ícones Heroicons

---

## Design Tokens

Use as classes utilitárias do Tailwind que mapeiam para os tokens semânticos:

### Cores

| Token | Classe Tailwind | Uso |
|-------|-----------------|-----|
| Primary | `bg-primary`, `text-primary` | Botões ativos, ícones ativos, links |
| Primary Variant | `bg-primary-variant` | Hover states, pressed states |
| Surface | `bg-surface` | Fundo principal da página |
| Surface Variant | `bg-surface-variant` | Cards, inputs, hover backgrounds |
| On Surface | `text-on-surface` | Texto principal |
| Error | `text-error`, `bg-error` | Mensagens de erro, validação |

### Tipografia

| Estilo | Classe Tailwind | Tamanho/Peso |
|--------|-----------------|--------------|
| Headline | `text-headline font-bold` | 24px / 700 |
| Title | `text-title font-semibold` | 20px / 600 |
| Body | `text-body` | 16px / 400 |
| Caption | `text-caption` | 12px / 400 |

### Espaçamento

Use múltiplos do grid base (4px):

```html
<div class="p-4">   <!-- 16px -->
<div class="gap-2"> <!-- 8px -->
<div class="m-3">   <!-- 12px -->
<div class="space-y-6"> <!-- 24px -->
```

### Arredondamento

| Componente | Classe | Valor |
|------------|--------|-------|
| Botões | `rounded-xl` | 12px |
| Cards | `rounded-2xl` | 16px |
| Inputs | `rounded-lg` | 8px |

### Elevação

| Nível | Classe | Uso |
|-------|--------|-----|
| Sutil | `shadow-sm` | Inputs, badges |
| Padrão | `shadow-md` | Cards, dropdowns |
| Elevado | `shadow-lg` | FAB, modais, bottom sheet |

---

## Dark Mode

O dark mode é automático. Use as classes utilitárias com prefixo `dark:`:

```html
<!-- Card que adapta ao tema -->
<div class="bg-surface-variant dark:bg-slate-800 rounded-2xl shadow-md p-4">
  <h2 class="text-on-surface dark:text-white">Título</h2>
</div>
```

No entanto, como os tokens semânticos já mapeiam automaticamente para dark mode via Tailwind config, na maioria dos casos você só precisa usar:

```html
<div class="bg-surface text-on-surface">
  <!-- Funciona em ambos os temas automaticamente -->
</div>
```

---

## Ícones

Use Heroicons com as variantes `outline` (inativo) e `solid` (ativo):

```html
<!-- Ícone inativo (outline) -->
<svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="..."/>
</svg>

<!-- Ícone ativo (solid) -->
<svg class="w-6 h-6 text-primary" fill="currentColor" viewBox="0 0 24 24">
  <path d="..."/>
</svg>
```

---

## HTMX Swaps

Para atualizar apenas o conteúdo sem recarregar o App Shell:

```html
<!-- Link que troca apenas o conteúdo -->
<a href="/routines/"
   hx-get="/routines/"
   hx-target="#app-canvas"
   hx-swap="innerHTML"
   class="...">
   Rotinas
</a>
```

O `base.html` já configura `hx-target="#app-canvas"` e `hx-swap="innerHTML"` como padrão.

---

## Acessibilidade

Sempre verifique:

1. **Área de toque**: Todo elemento interativo deve ter `min-w-[48px] min-h-[48px]`
2. **Contraste**: Texto sobre fundo deve ter ratio ≥ 4.5:1
3. **Labels**: Botões com ícones devem ter `aria-label`
4. **Focus**: Estados de foco visíveis (`focus:ring-2 focus:ring-primary`)

---

## Testando o App Shell

### Verificações manuais

1. Abra o DevTools → Device Toolbar → iPhone 12 Pro (390×844)
2. Verifique se todos os 5 botões da barra inferior são tocáveis com uma mão
3. Teste o dark mode: DevTools → Rendering → Emulate CSS `prefers-color-scheme: dark`
4. Verifique o contrast ratio com a extensão "WAVE" ou "axe DevTools"

### Lighthouse Audit

```bash
# Execute no Chrome em modo headless (ou use o DevTools)
npx lighthouse http://localhost:8000 --preset=desktop --output=json
```

Meta: Accessibility score ≥ 95.
