# Research: App Shell e Identidade Visual

**Feature**: 002-app-shell-identidade-visual  
**Date**: 2026-04-24  
**Purpose**: Documentar decisões técnicas investigadas para o App Shell e sistema de design tokens.

---

## Decision 1: Ícones — Heroicons via CDN (SVG inline)

**Decision**: Usar Heroicons (v2) via CDN/script com suporte a variantes `outline` e `solid`.

**Rationale**:
- Heroicons é o sistema de ícones oficial do Tailwind CSS (mesma equipe), garantindo consistência visual.
- Suporta nativamente as duas variantes necessárias pelo spec: `outline` (inativo) e `solid` (ativo).
- Disponível via CDN unpkg/jsdelivr sem necessidade de build step ou npm.
- Licença MIT, compatível com uso comercial.
- Cada ícone é um SVG inline otimizado (~0.5KB), não depende de fontes web que podem falhar no carregamento.

**Alternatives considered**:
- **Font Awesome**: Mais ícones disponíveis, mas requer carregamento de fonte web completa (~70KB). A proposta é minimalista.
- **Phosphor Icons**: Excelente, mas requer dependência npm ou script customizado. Heroicons é mais integrado ao ecossistema Tailwind.
- **SVGs inline manuais**: Máximo controle, mas adiciona complexidade de manutenção. Heroicons padroniza o formato.

---

## Decision 2: Dark Mode — Tailwind `darkMode: 'class'` Strategy

**Decision**: Usar a estratégia `class` do Tailwind CSS para dark mode, aplicando a classe `dark` no elemento `<html>` via Alpine.js.

**Rationale**:
- A estratégia `class` permite controle manual (menu de perfil) + detecção automática do sistema operacional.
- A estratégia `media` (baseada em `prefers-color-scheme`) não permite sobrescrever manualmente, violando FR-014.
- A transição de tema é instantânea porque o Tailwind aplica classes utilitárias; não há recarregamento de CSS.
- Alpine.js pode gerenciar o estado do tema (`x-data="{ darkMode: ... }")` e sincronizar com LocalStorage.

**Alternatives considered**:
- **`media` strategy**: Não permite override manual. Rejeitado por violar FR-014.
- **CSS custom properties manual**: Funciona, mas perde a conveniência das classes utilitárias do Tailwind. Rejeitado por adicionar complexidade desnecessária.

---

## Decision 3: Bottom Sheet — Alpine.js + Tailwind CSS puro

**Decision**: Implementar o bottom sheet como um componente Alpine.js puro, usando transições CSS do Tailwind (`transition`, `transform`, `translate-y`).

**Rationale**:
- Não requer bibliotecas externas adicionais — já usamos Alpine.js e Tailwind.
- O bottom sheet é um componente relativamente simples: overlay semitransparente + painel deslizante da base.
- Alpine.js gerencia o estado (`open`/`closed`) e as animações via `x-transition`.
- Consistente com a restrição Anti-SPA e a abordagem HTMX + Alpine.js da Constitution.

**Implementation pattern**:
- Overlay: `fixed inset-0 bg-black/50` com `x-show` e `x-transition: opacity`
- Painel: `fixed bottom-0 w-full` com `x-transition: translate-y`
- Fechar ao tocar fora: `@click.outside` do Alpine.js
- Fechar ao deslizar para baixo: evento `touchstart`/`touchend` com cálculo de delta Y

**Alternatives considered**:
- **SheetJS / Bottom Sheet libraries**: Adicionam dependências desnecessárias. Rejeitado.
- **HTMX para abrir o bottom sheet**: O bottom sheet é um estado efêmero de UI (não requer dados do servidor), então Alpine.js é mais apropriado que HTMX.

---

## Decision 4: Design Tokens no Tailwind — Configuração via `tailwind.config.js`

**Decision**: Mapear os design tokens semânticos como customizações do `tailwind.config.js` (ou script de configuração inline via CDN).

**Rationale**:
- Tailwind permite estender o tema com cores customizadas: `theme.extend.colors.primary: '#14b8a6'`.
- Isso permite usar classes utilitárias como `bg-primary`, `text-on-surface`, `shadow-fab`.
- Como usamos Tailwind via CDN inicialmente (conforme spec 001), a configuração será feita via `<script>` de configuração antes do script do Tailwind CDN.
- Futuramente, quando houver build step, a mesma configuração pode ser movida para `tailwind.config.js` sem alterar as classes nos templates.

**Token mapping**:
```javascript
tailwind.config = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: '#14b8a6',
        'primary-variant': '#0d9488',
        surface: '#f8fafc',
        'surface-variant': '#f1f5f9',
        'on-surface': '#0f172a',
        error: '#ef4444',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
}
```

**Alternatives considered**:
- **CSS custom properties puras**: Funciona, mas perde a produtividade das classes utilitárias do Tailwind. Rejeitado.
- **Design token JSON separado**: Bom para sistemas grandes, mas adiciona complexidade de build. Rejeitado para o MVP.

---

## Decision 5: Estrutura de Templates Parciais

**Decision**: Fragmentar o App Shell em partials reutilizáveis conforme a convenção da Constitution:
- `src/templates/base.html` — App Shell mestre
- `src/templates/partials/nav/_header.html` — Header fixo
- `src/templates/partials/nav/_bottom_nav.html` — Barra de navegação inferior
- `src/templates/partials/nav/_bottom_sheet.html` — Bottom sheet de criação rápida

**Rationale**:
- Permite reutilização e manutenção isolada de cada componente.
- Alinhado com a convenção `templates/<app>/partials/_*.html` da Constitution.
- O header e footer podem ser incluídos no `base.html` via `{% include %}` do Django.
- O bottom sheet é incluído uma vez no `base.html` e controlado por Alpine.js.

**Alternatives considered**:
- **Tudo em base.html**: Mais simples inicialmente, mas dificulta manutenção e reuso. Rejeitado.
- **Componentes Django custom template tags**: Muito verboso para o escopo atual. Rejeitado.

---

## Decision 6: Logo e Identidade Visual Marca

**Decision**: Usar texto "Autismo em Foco" como marca no header inicialmente, com placeholder para logo SVG futuro.

**Rationale**:
- Não há asset de logo definido no escopo desta feature.
- Texto com tipografia Inter em peso semibold transmite identidade imediatamente.
- O espaço reservado para logo (ícone/avatar) permite substituição futura sem alterar a estrutura do template.

**Alternatives considered**:
- **Gerar logo SVG placeholder**: Fora do escopo. Rejeitado.
- **Usar emoji ou ícone como logo**: Não profissional o suficiente. Rejeitado.

---

## Decision 7: Indicador de Notificações no Header

**Decision**: Implementar indicador de notificações como um badge numérico sobre o ícone de sino, com atualização via HTMX polling (ouSSE futuramente).

**Rationale**:
- O spec exige indicador de notificações no header (FR-006).
- Como esta feature é puramente visual/estrutural, a lógica de notificações será um stub/mock inicialmente.
- O badge deve ser acessível (aria-label="N notificações não lidas") e ter contraste adequado.
- Quando o backend de notificações for implementado, o HTMX pode fazer swap do badge sem recarregar a página.

**Alternatives considered**:
- **Pular notificações nesta feature**: Violates FR-006. Rejeitado.
- **Badge sempre visível (mesmo com 0)**: Polui visualmente. Rejeitado — badge só aparece quando > 0.

---

## Decision 8: Animações e Transições

**Decision**: Usar transições CSS do Tailwind (`transition-colors`, `transition-transform`, `duration-200`) para todos os estados interativos.

**Rationale**:
- Tailwind fornece utilitários de transição prontos para uso.
- `duration-200` (200ms) é rápido o suficiente para parecer responsivo, mas suave o suficiente para não causar fadiga visual.
- A transição de tema claro/escuro usará `transition-colors` no elemento `<html>` para garantir SC-004 (< 300ms).

**Alternatives considered**:
- **Sem transições**: Interface parece "seca" e não atende à expectativa de modernidade. Rejeitado.
- **Animações complexas com keyframes**: Fora do escopo; adicionam complexidade. Rejeitado.

---

## Summary of Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Heroicons via CDN (outline/solid) | Oficial Tailwind, suporte nativo às variantes necessárias |
| 2 | Dark mode `class` strategy | Permite override manual + detecção automática |
| 3 | Bottom sheet Alpine.js puro | Sem dependências extras, consistente com stack |
| 4 | Tokens no `tailwind.config` (CDN) | Mapeamento semântico via classes utilitárias |
| 5 | Partials para header, nav, bottom sheet | Reuso e manutenção isolada |
| 6 | Texto como marca inicial | Placeholder para logo futuro |
| 7 | Badge de notificações com HTMX stub | Preparação para backend futuro |
| 8 | Transições Tailwind `duration-200` | Responsividade + suavidade |
