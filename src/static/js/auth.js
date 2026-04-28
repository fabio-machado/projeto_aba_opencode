/**
 * Autismo em Foco — Auth Login Form (Alpine.js)
 *
 * Gerencia o estado do formulário de login (magic link):
 * - submissão via HTMX
 * - estado disabled/enabled do botão
 * - limpeza de erro no input
 *
 * ≤ 50 linhas — conforme Constitution II.
 */
document.addEventListener('alpine:init', () => {
  Alpine.data('loginForm', () => ({
    submitting: false,
    email: '',
    error: '',

    init() {
      document.body.addEventListener('htmx:beforeRequest', (e) => {
        if (e.detail.target && e.detail.target.closest('#login-form')) {
          this.submitting = true;
          this.error = '';
        }
      });
      document.body.addEventListener('htmx:afterRequest', (e) => {
        if (e.detail.target && e.detail.target.closest('#login-form')) {
          this.submitting = false;
        }
      });
    },

    clearError() {
      this.error = '';
    },
  }));
});
