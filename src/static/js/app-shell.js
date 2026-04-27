/**
 * Autismo em Foco — App Shell Alpine.js Component
 *
 * Gerencia:
 * - Tema (light / dark) com persistência em LocalStorage
 * - Seção ativa da navegação (detectada via URL + dicionário)
 * - Estado do bottom sheet
 *
 * < 50 linhas de lógica — conforme Constitution II.
 */

if (!window.URL_TO_SECTION) {
  window.URL_TO_SECTION = {
    '/routines': 'routines',
    '/guide': 'guide',
    '/monitor': 'monitor',
  };
}

function appShell() {
  return {
    theme: localStorage.getItem('aef_theme') || 'light',
    activeSection: 'home',
    parentSection: null,
    sheetOpen: false,
    notificationCount: 3,

    init() {
      this.applyTheme();
      this.detectActiveSection();
    },

    applyTheme() {
      const isDark = this.theme === 'dark';
      document.documentElement.classList.toggle('dark', isDark);
    },

    toggleTheme() {
      this.theme = this.theme === 'dark' ? 'light' : 'dark';
      localStorage.setItem('aef_theme', this.theme);
      this.applyTheme();
    },

    setActiveSection(section) {
      this.activeSection = section;
      this.parentSection = null;
    },

    detectActiveSection() {
      const path = window.location.pathname;
      for (const [prefix, section] of Object.entries(window.URL_TO_SECTION)) {
        if (path.startsWith(prefix)) {
          this.activeSection = section;
          this.parentSection = path !== prefix ? section : null;
          return;
        }
      }
      this.activeSection = 'home';
      this.parentSection = null;
    },

    isActive(section) { return this.activeSection === section; },
    openSheet() { this.sheetOpen = true; },
    closeSheet() { this.sheetOpen = false; },
  };
}
