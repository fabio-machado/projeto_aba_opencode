# Contract: Bottom Sheet

**Feature**: 002-app-shell-identidade-visual  
**Date**: 2026-04-24  
**Purpose**: Definir os estados, eventos e comportamentos do bottom sheet de criação rápida.

---

## States

| State | Description | Visual |
|-------|-------------|--------|
| `closed` | Bottom sheet não visível | Painel abaixo da viewport; overlay transparente e invisível |
| `opening` | Transição de fechado para aberto | Overlay fading in; painel deslizando de baixo para cima |
| `open` | Bottom sheet totalmente visível | Overlay opaco; painel na posição final |
| `closing` | Transição de aberto para fechado | Overlay fading out; painel deslizando para baixo |

## Events

| Event | Trigger | Action |
|-------|---------|--------|
| `open` | Toque no botão "+" (FAB) | Transiciona para estado `opening` → `open` |
| `close` | Toque no overlay; swipe para baixo; toque no botão voltar | Transiciona para estado `closing` → `closed` |
| `select` | Toque em uma ação do bottom sheet | Fecha o bottom sheet e navega para o destino da ação |
| `backdrop_click` | Toque fora do painel (no overlay) | Equivalente a `close` |

## Interface (Alpine.js)

```javascript
function bottomSheet() {
  return {
    open: false,
    actions: [
      { id: 'new-routine', label: 'Nova Rotina', icon: 'clipboard-document-list', href: '/routines/create/' },
      { id: 'new-record', label: 'Novo Registro', icon: 'pencil-square', href: '/records/create/' },
    ],
    
    // Open bottom sheet
    show() {
      this.open = true;
      // Prevent body scroll
      document.body.style.overflow = 'hidden';
    },
    
    // Close bottom sheet
    hide() {
      this.open = false;
      document.body.style.overflow = '';
    },
    
    // Select an action
    select(action) {
      this.hide();
      // Navigate after transition completes
      setTimeout(() => {
        window.location.href = action.href;
      }, 200);
    },
    
    // Handle touch swipe down
    touchStartY: 0,
    handleTouchStart(e) {
      this.touchStartY = e.touches[0].clientY;
    },
    handleTouchEnd(e) {
      const endY = e.changedTouches[0].clientY;
      const deltaY = endY - this.touchStartY;
      if (deltaY > 80) { // Swipe down threshold
        this.hide();
      }
    }
  };
}
```

## HTML Structure

```html
<!-- Bottom Sheet Overlay -->
<div x-show="bottomSheetOpen" 
     x-transition:enter="transition ease-out duration-200"
     x-transition:enter-start="opacity-0"
     x-transition:enter-end="opacity-100"
     x-transition:leave="transition ease-in duration-150"
     x-transition:leave-start="opacity-100"
     x-transition:leave-end="opacity-0"
     @click="hideBottomSheet()"
     class="fixed inset-0 bg-black/50 z-40"
     style="display: none;">
</div>

<!-- Bottom Sheet Panel -->
<div x-show="bottomSheetOpen"
     x-transition:enter="transition ease-out duration-200"
     x-transition:enter-start="translate-y-full"
     x-transition:enter-end="translate-y-0"
     x-transition:leave="transition ease-in duration-150"
     x-transition:leave-start="translate-y-0"
     x-transition:leave-end="translate-y-full"
     @touchstart="handleTouchStart($event)"
     @touchend="handleTouchEnd($event)"
     class="fixed bottom-0 left-0 right-0 bg-surface rounded-t-2xl p-4 z-50"
     style="display: none;">
  
  <!-- Handle indicator -->
  <div class="w-12 h-1 bg-surface-variant rounded-full mx-auto mb-4"></div>
  
  <!-- Actions -->
  <div class="space-y-2">
    <template x-for="action in bottomSheetActions" :key="action.id">
      <a :href="action.href"
         @click.prevent="selectBottomSheetAction(action)"
         class="flex items-center gap-3 p-3 rounded-xl hover:bg-surface-variant min-h-[48px]">
        <svg class="w-6 h-6 text-primary"><!-- icon --></svg>
        <span class="font-medium" x-text="action.label"></span>
      </a>
    </template>
  </div>
</div>
```

## Invariants

1. O bottom sheet só pode estar aberto em uma tela por vez.
2. O overlay deve ter `z-index` inferior ao painel mas superior a todos os outros elementos interativos.
3. O scroll do body deve ser bloqueado quando o bottom sheet está aberto.
4. O swipe para baixo deve ter threshold mínimo de 80px para evitar fechamentos acidentais.
5. A navegação após seleção deve aguardar a transição de fechamento (200ms) para evitar jank visual.
6. O handle indicator (barra cinza no topo do painel) é obrigatório para comunicar affordance de arrasto.

## Accessibility

- O overlay deve ter `role="dialog"` e `aria-modal="true"` quando aberto.
- O botão FAB deve ter `aria-haspopup="dialog"` e `aria-expanded` sincronizado com o estado.
- Ao abrir, o foco deve mover-se para o primeiro item do bottom sheet.
- Ao fechar, o foco deve retornar ao botão FAB.
- Tecla `Escape` deve fechar o bottom sheet.
