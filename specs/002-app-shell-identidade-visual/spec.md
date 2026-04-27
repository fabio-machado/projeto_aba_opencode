# Feature Specification: App Shell e Identidade Visual

**Feature Branch**: `002-app-shell-identidade-visual`  
**Created**: 2026-04-24  
**Status**: Draft  
**Input**: User description: "Crie o App Shell Mestre e a Identidade Visual. O objetivo é estabelecer a estrutura de navegação e os padrões visuais que regerão todo o SaaS."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navegação com Uma Mão (Priority: P1)

Como cuidador ou terapeuta ABA, quero navegar pelo aplicativo usando apenas uma mão (teste do supermercado), para que eu possa interagir com o sistema enquanto cuido da criança ou anoto observações no campo.

**Why this priority**: O público-alvo do SaaS passa a maior parte do tempo em atividades práticas (sessões ABA, registros de comportamento). Se a navegação exigir dois dedos, zoom ou alcance no topo da tela, o aplicativo será abandonado. O "Teste do Supermercado" é um critério de aceitação não negociável da Constitution.

**Independent Test**: Um usuário com um smartphone de 6,1 polegadas consegue acessar as 5 principais seções do aplicativo usando apenas o polegar da mão dominante, sem precisar de reajuste de pegada.

**Acceptance Scenarios**:

1. **Given** o usuário está na tela inicial, **When** ele toca em qualquer botão da barra de navegação inferior, **Then** a área de toque visível é de no mínimo 48×48 pixels independentemente do tamanho do ícone.
2. **Given** o usuário está segurando o celular com uma mão, **When** ele tenta acessar o botão de ação primária ("+"), **Then** o botão está posicionado na zona de conforto do polegar (base da tela, centralizado) e aciona um painel deslizante (bottom sheet) com opções de criação rápida.
3. **Given** o usuário rola o conteúdo principal, **When** ele atinge o final da página, **Then** a barra de navegação inferior permanece fixa e acessível sem interferir no scroll do conteúdo.

---

### User Story 2 - Identidade Visual Calm e Acessível (Priority: P1)

Como usuário do sistema, quero uma interface visualmente calma, com cores suaves e tipografia legível, para que eu possa usar o aplicativo por longos períodos (sessões de 2–3 horas) sem fadiga visual ou estresse.

**Why this priority**: O contexto clínico-educacional do autismo exige ambientes de baixa estimulação. Cores saturadas ou contraste agressivo aumentam a ansiedade dos cuidadores e, indiretamente, interferem na qualidade do registro. A identidade visual é um diferencial competitivo de mercado.

**Independent Test**: A interface passa em verificação automática de contraste WCAG AA (4.5:1 para texto normal, 3:1 para componentes grandes) em todos os estados (claro, escuro, ativo, inativo).

**Acceptance Scenarios**:

1. **Given** o usuário acessa o aplicativo pela primeira vez, **When** a página carrega, **Then** a paleta de cores transmite calma (tons de verde-teal como cor primária, superfícies claras/neutras, sem vermelhos agressivos em estado padrão).
2. **Given** o usuário está em ambiente externo (luz solar), **When** ele lê um texto na interface, **Then** a tipografia mantém legibilidade sem necessidade de zoom ou aumento de brilho manual.
3. **Given** o usuário alterna entre modo claro e modo escuro, **When** a transição ocorre, **Then** todos os elementos da interface adaptam-se coerentemente sem elementos "quebrados" ou invisíveis.

---

### User Story 3 - Criação Rápida de Registros (Priority: P2)

Como terapeuta durante uma sessão ABA, quero criar uma nova rotina ou registro com no máximo 2 toques, para que eu não perca o foco da criança ou o timing da intervenção.

**Why this priority**: Em sessões ABA, o tempo de reação é crítico. Se o registro de um comportamento demorar mais de 5 segundos, o profissional pode perder a janela de oportunidade para anotação precisa ou interrupção da sessão.

**Independent Test**: O usuário consegue iniciar a criação de "Nova Rotina" ou "Novo Registro" a partir de qualquer tela do aplicativo em menos de 3 segundos.

**Acceptance Scenarios**:

1. **Given** o usuário está em qualquer tela do aplicativo, **When** ele toca no botão "+" central da barra de navegação, **Then** um painel deslizante (bottom sheet) surge da base da tela com 2–3 atalhos de criação rápida.
2. **Given** o painel de criação rápida está aberto, **When** o usuário toca fora do painel ou desliza para baixo, **Then** o painel fecha sem criar nenhum registro.
3. **Given** o painel está aberto, **When** o usuário seleciona "Nova Rotina", **Then** ele é direcionado ao formulário de criação de rotina com o foco no primeiro campo.

---

### User Story 4 - Orientação Visual de Navegação (Priority: P2)

Como usuário, quero saber claramente em qual seção do aplicativo estou, para que eu não me perca entre as diferentes áreas (Início, Rotinas, Guia, Monitor).

**Why this priority**: A arquitetura de informação do SaaS terá múltiplas seções especializadas. Sem feedback visual claro de localização, usuários com pouca familiaridade digital (pais de primeira viagem, estagiários) podem sentir-se perdidos e cometer erros de navegação.

**Independent Test**: Um novo usuário, sem treinamento prévio, consegue identificar em qual seção está apenas olhando para a barra de navegação inferior.

**Acceptance Scenarios**:

1. **Given** o usuário está na seção "Rotinas", **When** ele olha para a barra de navegação, **Then** o ícone "Rotinas" está preenchido (sólido) e colorido na cor primária (verde-teal), enquanto os demais ícones estão em contorno (outline) e cor neutra (cinza).
2. **Given** o usuário toca em um item inativo da barra, **When** a transição de tela ocorre, **Then** o estado visual do ícone ativo se move instantaneamente para o novo item selecionado, sem atraso perceptível.
3. **Given** o usuário está em uma subpágina (ex: detalhe de uma rotina), **When** ele observa a barra de navegação, **Then** o item pai correspondente ("Rotinas") continua marcado como ativo.

---

### Edge Cases

- **Tela pequena (menos de 360px de largura)**: A barra de navegação inferior deve adaptar-se reduzindo labels ou mantendo apenas ícones, sem quebrar o layout ou sobrepor conteúdo.
- **Orientação paisagem**: O header e a barra de navegação inferior devem permanecer funcionais; o botão "+" não pode ficar fora da zona de toque.
- **Teclado virtual aberto**: A barra de navegação inferior deve permanecer visível acima do teclado ou recuar de forma previsível, nunca ficar flutuando sobre o teclado de maneira errática.
- **Dark mode do sistema alterado enquanto app está aberto**: A interface deve responder à mudança do sistema operacional em tempo real, sem exigir recarregamento manual da página.
- **Notificação push recebida enquanto usuário interage com bottom sheet**: O bottom sheet deve permanecer aberto; a notificação deve ser indicada no header sem interromper o fluxo de criação.
- **Usuário com deficiência visual (aumento de fonte do sistema em 200%)**: Todos os textos da interface devem escalar proporcionalmente sem truncamento ou sobreposição de elementos.
- **Primeiro acesso em novo dispositivo**: Como a preferência de tema é armazenada no LocalStorage, ao acessar de um novo dispositivo ou navegador, o sistema deve detectar a preferência do sistema operacional e aplicá-la imediatamente, sem exigir login ou configuração manual.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Sistema DEVE usar tokens de design semânticos (ex: `color-surface`, `color-on-surface`, `color-primary`) desde o início, permitindo futura extensão para múltiplos temas sem alteração de código nos componentes.
- **FR-002**: Sistema DEVE oferecer suporte nativo a modo claro e modo escuro desde a primeira versão, com transição suave entre os modos. A preferência do usuário (claro/escuro/sistema) DEVE ser persistida no LocalStorage do navegador; caso não haja preferência salva, o sistema DEVE adotar automaticamente a preferência do sistema operacional.
- **FR-003**: Sistema DEVE utilizar a família tipográfica **Inter** (Google Fonts) como padrão, com escala de 4 tamanhos: base 16px, headline 24px, title 20px, caption 12px. A tipografia deve ser otimizada para leitura prolongada em telas mobile.
- **FR-004**: Sistema DEVE garantir que todos os botões e áreas interativas tenham dimensão mínima de toque de 48×48 pixels, conforme diretrizes de acessibilidade mobile.
- **FR-005**: Sistema DEVE aplicar bordas arredondadas consistentes em todos os botões e cards principais: botões `rounded-xl` (12px), cards `rounded-2xl` (16px), inputs `rounded-lg` (8px). O grid de espaçamento base é 4px com múltiplos definidos (4, 8, 12, 16, 24, 32, 48).
- **FR-006**: Sistema DEVE apresentar um cabeçalho fixo no topo da tela contendo identidade da marca (logo/nome), indicador de notificações e menu de acesso rápido ao perfil do usuário.
- **FR-007**: Sistema DEVE apresentar uma área de conteúdo central com scroll independente, identificada semanticamente para permitir atualizações parciais de conteúdo sem recarregamento da página inteira.
- **FR-008**: Sistema DEVE apresentar uma barra de navegação inferior fixa contendo exatamente 5 itens: Início, Rotinas, botão de ação central "+" (FAB), Guia e Monitor.
- **FR-009**: Sistema DEVE fazer com que o botão "+" central seja visualmente distinto dos demais itens da barra (estilo FAB — Floating Action Button), destacando-se em tamanho, cor e elevação `shadow-lg` (nível mais alto de sombra).
- **FR-010**: Sistema DEVE, ao tocar no botão "+", apresentar um painel deslizante da base (bottom sheet) com 2–3 atalhos de criação rápida, como "Nova Rotina" e "Novo Registro".
- **FR-011**: Sistema DEVE comunicar visualmente o estado ativo de um item na barra de navegação usando ícone preenchido (sólido) na cor primária; itens inativos devem usar ícone em contorno (outline) na cor neutra (cinza).
- **FR-012**: Sistema DEVE manter a barra de navegação inferior acessível em todos os contextos de uso, respeitando o "Teste do Supermercado" — todas as ações primárias devem ser alcançáveis com o polegar em uma mão.
- **FR-013**: Sistema DEVE garantir que a paleta de cores primária seja baseada em tons de verde-teal, associados a calma e confiança, e que o contraste entre texto e fundo atenda aos critérios mínimos WCAG AA. A paleta concreta adotada é: primary Teal-500 (#14b8a6), primary-variant Teal-600 (#0d9488), surface Slate-50 (#f8fafc), surface-variant Slate-100 (#f1f5f9), on-surface Slate-900 (#0f172a), error Red-500 (#ef4444).
- **FR-014**: Sistema DEVE permitir acesso ao menu de perfil do usuário a partir do cabeçalho, contendo opções de configurações, gerenciamento de assinatura e alternância de tema claro/escuro.
- **FR-015**: Sistema DEVE garantir que o scroll do conteúdo principal seja independente dos elementos fixos (header e barra inferior), sem que o conteúdo fique oculto atrás desses elementos.

### Key Entities

- **Design Token**: Conjunto de variáveis semânticas que definem cores, tipografia, espaçamento, elevação e arredondamento. Exemplos concretos: `color-primary` (#14b8a6), `color-primary-variant` (#0d9488), `color-surface` (#f8fafc), `color-surface-variant` (#f1f5f9), `color-on-surface` (#0f172a), `color-error` (#ef4444), `typography-headline` (Inter 24px/700), `typography-title` (Inter 20px/600), `typography-body` (Inter 16px/400), `typography-caption` (Inter 12px/400), `spacing-base` (4px), `border-radius-button` (12px), `border-radius-card` (16px), `border-radius-input` (8px), `shadow-sm`, `shadow-md`, `shadow-lg`.
- **App Shell**: Estrutura mestre da interface composta por Header (topo), Main Content (centro) e Bottom Navigation (base). É o container que permanece estável enquanto o conteúdo muda.
- **Bottom Sheet**: Painel deslizante que surge da base da tela quando o botão "+" é acionado, apresentando atalhos de criação rápida.
- **Navigation State**: Estado atual da aplicação que determina qual seção está ativa, refletido visualmente na barra inferior via ícone sólido/outline e cor primária/cinza.

## Constraints & Non-Negotiables *(mandatory)*

- **UX Fricção Zero**: Nenhuma ação primária pode exceder 5 segundos ou usar `<select>` para inputs frequentes. Área de toque mínima: 48×48 dp. O layout deve passar no "Teste do Supermercado".
- **Anti-SPA**: Proibido uso de React, Vue, Angular ou Svelte. Interatividade via HTMX + Alpine.js apenas.
- **Service Layer**: Toda lógica de negócio reside em `services.py`; views apenas validam input e retornam response.
- **Anti-ORM (dados core)**: Dados de pacientes usam `supabase-py`; ORM do Django é proibido para esses dados.
- **RLS-First**: Toda query em dados de pacientes filtra por `parent_id`; UUIDs serializados como `str(uuid)` antes do SDK Supabase.
- **Offline-First**: Ações de registro DEVEM persistir em LocalStorage e sincronizar quando online; conflitos usam last-write-wins.
- **Type Hinting**: Todo código Python DEVE usar type hints estritos.
- **Lock-in por utilidade**: Nenhuma feature pode dificultar entrada ou exportação de dados do usuário.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário consegue acessar as 5 seções principais do aplicativo usando apenas o polegar de uma mão, sem reajustar a pegada do telefone, em 100% das tentativas em dispositivos com tela de até 6,7 polegadas.
- **SC-002**: A interface atinge pontuação mínima de 95 no Lighthouse Accessibility Audit e passa em 100% das verificações automáticas de contraste WCAG AA para todos os estados (claro, escuro, ativo, inativo, desabilitado).
- **SC-003**: O tempo médio para iniciar a criação de um novo registro (toque no "+" + seleção do tipo de registro) é inferior a 3 segundos para usuários treinados e inferior a 5 segundos para usuários novos.
- **SC-004**: A transição entre modo claro e modo escuro ocorre em menos de 300 milissegundos, sem flicker, flash branco ou elementos visuais quebrados.
- **SC-005**: A interface mantém legibilidade completa quando o usuário ativa o aumento de fonte do sistema operacional em até 200%, sem truncamento de textos ou sobreposição de elementos em telas de 360px de largura.
- **SC-006**: 90% dos usuários em teste de usabilidade não estruturado conseguem identificar corretamente em qual seção do aplicativo estão apenas observando a barra de navegação inferior, sem necessidade de ler o conteúdo da tela.

## Clarifications

### Session 2026-04-24

- **Q1**: Quais são os valores concretos da paleta de cores para os tokens semânticos principais? → **A**: Paleta Teal Calm baseada no Tailwind CSS — primary: Teal-500 (#14b8a6), primary-variant: Teal-600 (#0d9488), surface: Slate-50 (#f8fafc), surface-variant: Slate-100 (#f1f5f9), on-surface: Slate-900 (#0f172a), error: Red-500 (#ef4444).
- **Q2**: Qual fonte e escala tipográfica devem ser adotadas como padrão do sistema? → **A**: Inter (Google Fonts) com escala de 4 tamanhos: base 16px, headline 24px, title 20px, caption 12px.
- **Q3**: Quais devem ser os valores base de espaçamento (grid), níveis de arredondamento e elevação (shadow) para os design tokens? → **A**: Grid 4px com múltiplos (4, 8, 12, 16, 24, 32, 48). Arredondamento: botões `rounded-xl` (12px), cards `rounded-2xl` (16px), inputs `rounded-lg` (8px). Elevação: 3 níveis de sombra (`shadow-sm`, `shadow-md`, `shadow-lg`).
- **Q4**: Onde a preferência de tema (claro/escuro/sistema) do usuário deve ser persistida? → **A**: LocalStorage do navegador, com fallback automático para preferência do sistema operacional quando não houver escolha manual salva.

## Assumptions

- O público-alvo principal utiliza smartphones Android e iOS modernos (últimos 3 anos), com telas entre 5,5 e 6,7 polegadas.
- O aplicativo será utilizado predominantemente em modo retrato (portrait); o modo paisagem (landscape) é suportado mas não otimizado como experiência primária.
- A fonte tipográfica escolhida é a **Inter** (Google Fonts), disponível via CDN, sob licença SIL Open Font License, sem restrições de licenciamento para uso comercial.
- O dark mode será respeitado conforme preferência do sistema operacional por padrão, podendo ser sobrescrito manualmente pelo usuário no menu de perfil.
- A barra de navegação inferior sempre terá exatamente 5 itens; adições futuras exigirão reavaliação do padrão de navegação (ex: drawer ou menu secundário).
- O botão "+" sempre apresentará as opções "Nova Rotina" e "Novo Registro" no bottom sheet; uma terceira opção pode ser adicionada futuramente conforme evolução do produto.
- O cabeçalho fixo não excederá 64 pixels de altura em mobile, garantindo que o conteúdo principal tenha espaço suficiente.
