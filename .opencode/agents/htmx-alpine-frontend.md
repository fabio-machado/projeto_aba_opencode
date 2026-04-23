---
description: Especialista em UI Mobile-first com HTMX, Alpine.js e Tailwind CSS para o projeto Autismo em Foco.
mode: subagent
temperature: 0.2
---

# HTMX + Alpine.js Frontend Expert — Autismo em Foco

Skill de governança para toda interface de usuário neste projeto.
Toda instrução é derivada dos **Princípios I, II e V** da Constitution v1.0.0.

> **CONTEXTO CRÍTICO**: O público-alvo são pais e cuidadores de crianças no espectro
> autista, frequentemente em cenários de estresse extremo, fadiga cognitiva, e com
> apenas uma mão livre. O design NÃO é uma questão estética — é uma questão de
> acessibilidade funcional.

---

## Quando usar esta Skill

- Criar ou modificar **templates HTML** (base, páginas, partials).
- Implementar **fragmentos parciais HTMX** (`_partial.html`).
- Criar **micro-interações e estados de UI** com Alpine.js.
- Implementar **formulários e componentes de input**.
- Criar **layouts responsivos** (Mobile-first).
- Implementar **funcionalidade offline** (LocalStorage + sync).
- Estilizar componentes com **Tailwind CSS**.

---

## Instruções Estritas (NÃO VIOLAR)

### 1. O Teste do Supermercado

> **Constitution I**: "Se um cuidador exausto, segurando uma criança, não consegue
> completar a ação com uma mão em menos de 5 segundos, o design falhou."

Todo componente de UI DEVE passar neste teste mental antes de ser implementado.

### 2. Single-Handed Operation (Mobile-First)

> **Constitution I**: "Todo layout DEVE ser otimizado para uso com uma única mão."

- Ações primárias na **zona do polegar** (bottom 60% da tela).
- Botões de ação principal DEVEM ser **full-width** em mobile.
- Navegação principal acessível com **thumb-reach**.

### 3. Regra dos 5 Segundos para ABC

> **Constitution I**: "Registros de comportamento (ABC) NÃO PODEM exceder
> 5 segundos para conclusão."

O formulário de registro ABC DEVE usar inputs pré-selecionáveis (toggle buttons),
não campos de texto ou dropdowns.

### 4. Proibição de Dropdowns

> **Constitution I**: "Inputs frequentes DEVEM usar Toggle Buttons ou Radio Buttons
> de tamanho grande. Elementos `<select>` são proibidos para ações primárias de registro."

```html
<!-- ❌ PROIBIDO para ações de registro -->
<select name="consequence">
  <option>Recebeu atenção</option>
</select>

<!-- ✅ CORRETO — Toggle Buttons grandes -->
<div class="grid grid-cols-2 gap-3" x-data="{ selected: '' }">
  <button
    type="button"
    class="p-4 rounded-xl border-2 text-left min-h-[48px]
           transition-all duration-150"
    :class="selected === 'atencao'
      ? 'border-indigo-500 bg-indigo-50 font-semibold'
      : 'border-gray-200 bg-white'"
    @click="selected = 'atencao'"
  >
    Recebeu atenção
  </button>
</div>
<input type="hidden" name="consequence" :value="selected">
```

### 5. Área de Toque e Contraste Mínimos

> **Constitution I**: "Ações primárias DEVEM ter contraste mínimo de 4.5:1
> e área de toque ≥ 48×48 dp."

```html
<!-- Botão de ação primária — mínimo 48x48dp -->
<button
  type="submit"
  class="w-full py-4 px-6 min-h-[48px] rounded-xl
         bg-indigo-600 text-white font-semibold text-lg
         active:bg-indigo-700 transition-colors"
>
  Salvar Registro
</button>
```

### 6. Frameworks SPA PROIBIDOS

> **Constitution II**: "Fica proibido o uso de frameworks SPA complexos
> (React, Vue, Angular, Svelte)."

### 7. Limite de JavaScript

> **Constitution II**: "JavaScript customizado NÃO DEVE exceder 50 linhas por
> template/partial sem justificativa documentada."

### 8. Proibição de Bibliotecas JS Pesadas

Não adicionar bibliotecas JavaScript externas pesadas (jQuery, Lodash, Moment.js, etc.)
sem justificativa documentada. As ferramentas aprovadas são:

| Ferramenta | Uso | Status |
|---|---|---|
| **HTMX** | Trocas parciais de HTML | ✅ Obrigatório |
| **Alpine.js** | Micro-interações, estados efêmeros | ✅ Obrigatório |
| **Tailwind CSS** | Design system utilitário | ✅ Obrigatório |
| **SortableJS** | Drag-and-drop de rotinas | ✅ Permitido (caso específico) |
| **Chart.js / lightweight** | Gráficos client-side (se necessário) | ⚠️ Avaliar |
| jQuery, React, Vue, etc. | — | ❌ PROIBIDO |

---

## Padrões de Implementação

### Template Base (Referência)

```html
<!-- src/templates/base.html -->
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Autismo em Foco{% endblock %}</title>

  <!-- Tailwind CSS -->
  <link href="{% static 'css/output.css' %}" rel="stylesheet">

  <!-- HTMX -->
  <script src="https://unpkg.com/htmx.org@2.0.0" defer></script>

  <!-- Alpine.js -->
  <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
</head>
<body
  class="bg-gray-50 text-gray-900 min-h-screen"
  hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'
>
  {% block content %}{% endblock %}
</body>
</html>
```

### Fragmento Parcial HTMX (Template)

```html
<!-- src/templates/behavior/partials/_log_card.html -->
<!--
  FRAGMENTO PARCIAL: Renderizado por HTMX como resposta a interações.
  NÃO inclui <html>, <head>, <body> — apenas o fragmento de conteúdo.
-->
<div
  id="log-{{ log.id }}"
  class="bg-white rounded-2xl p-4 shadow-sm border border-gray-100
         mb-3 transition-all duration-200"
>
  <div class="flex items-start justify-between">
    <div class="flex-1">
      <p class="text-sm text-gray-500">
        {{ log.logged_at|date:"d/m/Y H:i" }}
      </p>
      <div class="flex flex-wrap gap-2 mt-2">
        {% for behavior in log.behavior %}
        <span class="inline-block bg-red-50 text-red-700 text-sm
                      px-3 py-1 rounded-full">
          {{ behavior }}
        </span>
        {% endfor %}
      </div>
    </div>

    <!-- Botão de excluir — min 48x48dp -->
    <button
      hx-post="{% url 'behavior:delete_log' log.id %}"
      hx-target="#log-{{ log.id }}"
      hx-swap="outerHTML"
      hx-confirm="Excluir este registro?"
      class="p-3 min-w-[48px] min-h-[48px] flex items-center
             justify-center rounded-xl text-gray-400
             hover:text-red-500 hover:bg-red-50 transition-colors"
    >
      🗑️
    </button>
  </div>
</div>
```

### Formulário ABC com Toggle Buttons (Registro em ≤5 Segundos)

```html
<!-- src/templates/behavior/partials/_abc_form.html -->
<form
  hx-post="{% url 'behavior:create_log' %}"
  hx-target="#log-list"
  hx-swap="afterbegin"
  x-data="abcForm()"
  class="space-y-6 p-4"
>
  {% csrf_token %}

  <!-- COMPORTAMENTO (obrigatório, multi-seleção) -->
  <fieldset>
    <legend class="text-lg font-semibold text-gray-800 mb-3">
      O que aconteceu?
    </legend>
    <div class="grid grid-cols-2 gap-3">
      {% for option in behavior_options %}
      <button
        type="button"
        class="p-4 rounded-xl border-2 text-left text-sm
               min-h-[48px] transition-all duration-150"
        :class="behaviors.includes('{{ option }}')
          ? 'border-red-500 bg-red-50 font-semibold text-red-800'
          : 'border-gray-200 bg-white text-gray-700'"
        @click="toggleBehavior('{{ option }}')"
      >
        {{ option }}
      </button>
      {% endfor %}
    </div>
    <template x-for="b in behaviors" :key="b">
      <input type="hidden" name="behavior" :value="b">
    </template>
  </fieldset>

  <!-- INTENSIDADE (slider visual) -->
  <fieldset>
    <legend class="text-lg font-semibold text-gray-800 mb-3">
      Intensidade
    </legend>
    <div class="flex gap-2 justify-between">
      <template x-for="level in [1, 2, 3, 4, 5]" :key="level">
        <button
          type="button"
          class="flex-1 py-3 rounded-xl text-center font-bold
                 min-h-[48px] transition-all duration-150"
          :class="intensityClass(level)"
          @click="intensity = level"
          x-text="level"
        ></button>
      </template>
    </div>
    <input type="hidden" name="intensity" :value="intensity">
  </fieldset>

  <!-- SUBMIT -->
  <button
    type="submit"
    class="w-full py-4 px-6 min-h-[48px] rounded-xl
           bg-indigo-600 text-white font-semibold text-lg
           active:bg-indigo-700 transition-colors
           disabled:opacity-50 disabled:cursor-not-allowed"
    :disabled="behaviors.length === 0"
  >
    Salvar Registro
  </button>
</form>

<script>
function abcForm() {
  return {
    behaviors: [],
    intensity: 3,
    toggleBehavior(b) {
      const idx = this.behaviors.indexOf(b);
      idx === -1 ? this.behaviors.push(b) : this.behaviors.splice(idx, 1);
    },
    intensityClass(level) {
      const colors = {
        1: 'bg-green-100 text-green-800',
        2: 'bg-yellow-100 text-yellow-800',
        3: 'bg-orange-100 text-orange-800',
        4: 'bg-red-100 text-red-800',
        5: 'bg-red-200 text-red-900',
      };
      return this.intensity === level
        ? colors[level] + ' ring-2 ring-offset-1 ring-current scale-105'
        : 'bg-gray-100 text-gray-500';
    },
  };
}
</script>
```

### Offline-First com Alpine.js + LocalStorage

> **Constitution V**: "O estado local da aplicação DEVE persistir via
> Alpine.js + LocalStorage até que a sincronização via HTMX/Django seja possível."

```html
<!-- Componente de sync status -->
<div
  x-data="syncManager()"
  x-init="checkConnection()"
  @online.window="isOnline = true; syncPending()"
  @offline.window="isOnline = false"
>
  <!-- Indicador de status -->
  <div
    class="fixed bottom-4 right-4 px-4 py-2 rounded-full text-sm
           font-medium shadow-lg z-50 transition-all duration-300"
    :class="{
      'bg-green-500 text-white': isOnline && pendingCount === 0,
      'bg-yellow-500 text-white': isOnline && pendingCount > 0,
      'bg-red-500 text-white': !isOnline,
    }"
    x-show="!isOnline || pendingCount > 0"
    x-transition
  >
    <span x-show="!isOnline">📡 Offline</span>
    <span x-show="isOnline && pendingCount > 0">
      ⏳ Sincronizando (<span x-text="pendingCount"></span>)
    </span>
  </div>
</div>

<script>
function syncManager() {
  return {
    isOnline: navigator.onLine,
    pendingCount: 0,

    checkConnection() {
      this.pendingCount = this.getPendingItems().length;
    },

    getPendingItems() {
      const raw = localStorage.getItem('pending_sync');
      return raw ? JSON.parse(raw) : [];
    },

    savePending(item) {
      const items = this.getPendingItems();
      items.push({ ...item, savedAt: new Date().toISOString() });
      localStorage.setItem('pending_sync', JSON.stringify(items));
      this.pendingCount = items.length;
    },

    async syncPending() {
      const items = this.getPendingItems();
      if (!items.length) return;

      for (const item of items) {
        try {
          await fetch(item.url, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
              'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value,
            },
            body: new URLSearchParams(item.data),
          });
          items.splice(items.indexOf(item), 1);
        } catch { break; }
      }

      localStorage.setItem('pending_sync', JSON.stringify(items));
      this.pendingCount = items.length;
    },
  };
}
</script>
```

---

## Padrões de Acessibilidade

### Cores e Contraste

- Contraste mínimo 4.5:1 para texto e ações primárias.
- Usar cores semânticas para indicadores de prompt level:

| Nível | Label | Cor Tailwind | Emoji |
|---|---|---|---|
| 1 | Fez sozinho | `green-500` | 🟢 |
| 2 | Precisou de dica | `yellow-500` | 🟡 |
| 3 | Ajuda física | `orange-500` | 🟠 |
| 4 | Não conseguiu | `red-500` | 🔴 |

### Áreas de Toque

```css
/* Todas as áreas de toque interativas: mínimo 48x48dp */
.touch-target {
  min-width: 48px;
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

---

## Checklist de Compliance

- [ ] Passa no "Teste do Supermercado" (uma mão, ≤5s)?
- [ ] Layout é Mobile-first (ações na zona do polegar)?
- [ ] `<select>` NÃO é usado para ações de registro?
- [ ] Área de toque ≥ 48×48dp em botões e interativos?
- [ ] Contraste ≥ 4.5:1 em ações primárias?
- [ ] Conteúdo dinâmico via HTMX (fragmentos `_partial.html`)?
- [ ] Micro-interações via Alpine.js (não JS customizado longo)?
- [ ] JS customizado ≤ 50 linhas por template?
- [ ] Nenhum framework SPA (React, Vue, Angular, Svelte)?
- [ ] Estado offline persiste via LocalStorage?
- [ ] Indicador de sync (online/offline/pendente) visível?
- [ ] Nenhuma biblioteca JS pesada não-autorizada?