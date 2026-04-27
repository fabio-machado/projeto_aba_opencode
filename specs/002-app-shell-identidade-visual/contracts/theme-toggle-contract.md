# Contract: Theme Toggle

**Feature**: 002-app-shell-identidade-visual  
**Date**: 2026-04-24  
**Purpose**: Definir a API de alternância de tema (claro/escuro/sistema) via Alpine.js e LocalStorage.

---

## Interface

### Alpine.js Data Component

```javascript
function appShell() {
  return {
    // State
    darkMode: false,
    themeMode: 'system', // 'light' | 'dark' | 'system'
    
    // Initialization
    init() {
      this.loadTheme();
      this.watchSystemTheme();
    },
    
    // Load from LocalStorage
    loadTheme() {
      const saved = localStorage.getItem('aef_theme');
      if (saved) {
        const parsed = JSON.parse(saved);
        this.themeMode = parsed.mode || 'system';
      }
      this.applyTheme();
    },
    
    // Apply theme based on mode
    applyTheme() {
      if (this.themeMode === 'system') {
        this.darkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
      } else {
        this.darkMode = this.themeMode === 'dark';
      }
      // Sync to <html> class
      if (this.darkMode) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    },
    
    // Set theme explicitly
    setTheme(mode) {
      this.themeMode = mode;
      this.applyTheme();
      localStorage.setItem('aef_theme', JSON.stringify({
        mode: this.themeMode,
        updated_at: new Date().toISOString()
      }));
    },
    
    // Watch system theme changes
    watchSystemTheme() {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      mediaQuery.addEventListener('change', (e) => {
        if (this.themeMode === 'system') {
          this.darkMode = e.matches;
          this.applyTheme();
        }
      });
    },
    
    // Toggle between light/dark (quick toggle)
    toggleTheme() {
      const newMode = this.darkMode ? 'light' : 'dark';
      this.setTheme(newMode);
    }
  };
}
```

### HTML Usage

```html
<!-- Toggle rápido (header ou menu) -->
<button @click="toggleTheme()" 
        :aria-label="darkMode ? 'Ativar modo claro' : 'Ativar modo escuro'"
        class="min-w-[48px] min-h-[48px] p-2 rounded-xl">
  <svg x-show="!darkMode" ...><!-- Sun icon --></svg>
  <svg x-show="darkMode" ...><!-- Moon icon --></svg>
</button>

<!-- Seleção no menu de perfil -->
<div x-data="{ open: false }">
  <button @click="open = !open">Tema</button>
  <div x-show="open" @click.outside="open = false">
    <button @click="setTheme('light')" :class="{ 'text-primary': themeMode === 'light' }">Claro</button>
    <button @click="setTheme('dark')" :class="{ 'text-primary': themeMode === 'dark' }">Escuro</button>
    <button @click="setTheme('system')" :class="{ 'text-primary': themeMode === 'system' }">Sistema</button>
  </div>
</div>
```

---

## Invariants

1. A classe `dark` no `<html>` é a única fonte de verdade para o estado visual do tema.
2. `localStorage` sempre armazena o objeto completo `{ mode, updated_at }`.
3. A chave no LocalStorage é sempre `aef_theme`.
4. Quando `mode === 'system'`, o tema deve responder em tempo real a mudanças do sistema operacional.
5. A transição entre temas deve usar `transition-colors duration-200` para atender SC-004 (< 300ms).

---

## Anti-FART Script

Para evitar "Flash of Accurate Theme" (FART), o seguinte script deve ser inline no `<head>` do `base.html`, ANTES de qualquer CSS:

```html
<script>
  (function() {
    const saved = localStorage.getItem('aef_theme');
    let dark = false;
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.mode === 'dark') dark = true;
        else if (parsed.mode === 'system') {
          dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        }
      } catch (e) {}
    } else {
      dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    if (dark) document.documentElement.classList.add('dark');
  })();
</script>
```
