/**
 * Autismo em Foco — Bottom Sheet Alpine.js Component
 *
 * Gerencia:
 * - Swipe para baixo (threshold 80px) para fechar
 * - Focus trap enquanto o sheet está aberto
 * - Focus restoration ao FAB ao fechar
 *
 * Delega open/close para appShell() via escopo pai do Alpine.
 * < 50 linhas — conforme Constitution II.
 */

function bottomSheet() {
  return {
    _touchStartY: 0,
    _swipeThreshold: 80,

    init() {
      // Focus no primeiro botão quando abrir
      this.$watch('sheetOpen', (open) => {
        if (open) {
          this.$nextTick(() => {
            const firstBtn = this.$el.querySelector('a, button');
            if (firstBtn) firstBtn.focus();
          });
        }
      });
    },

    onTouchStart(e) {
      this._touchStartY = e.touches[0].clientY;
    },

    onTouchEnd(e) {
      const delta = e.changedTouches[0].clientY - this._touchStartY;
      if (delta > this._swipeThreshold) {
        this.closeSheet();
      }
    },

    closeSheet() {
      // Delega para appShell() via escopo pai
      this.$parent.closeSheet();
      // Focus restoration: retorna ao FAB
      this.$nextTick(() => {
        const fab = document.getElementById('fab-create');
        if (fab) fab.focus();
      });
    },

    trapFocus(e) {
      const focusable = this.$el.querySelectorAll(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (!focusable.length) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    },
  };
}
