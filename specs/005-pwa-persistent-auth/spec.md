# Feature Specification: PWA com Sessão Persistente

**Feature Branch**: `005-pwa-persistent-auth`  
**Created**: 2026-04-29  
**Status**: Draft  
**Input**: User description: "Implementar PWA com sessão persistente via Supabase"

## Clarifications

### Session 2026-04-29

- **Q**: Qual deve ser a experiência do usuário quando a sessão não pode ser renovada de forma alguma? → **A**: Modo leitura com banner de login — a interface exibe dados já carregados, mas ações de escrita são bloqueadas até nova autenticação.
- **Q**: Qual nível de controle de segurança em dispositivos compartilhados deve ser suportado nesta feature? → **A**: Botão de logout explícito no menu da header, junto às funcionalidades de assinatura, configurações e dark mode.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instalar App na Tela Inicial (Priority: P1)

O usuário acessa a aplicação pelo navegador do celular e deseja instalar o app na tela inicial para acesso rápido e direto, sem precisar abrir o navegador manualmente.

**Why this priority**: Elimina a barreira de acesso à aplicação. Usuários que precisam registrar dados com frequência (ex: pais de crianças com autismo) precisam de acesso imediato. Sem instalação, o risco de abandono por fricção de acesso é alto.

**Independent Test**: Pode ser testado verificando se o usuário consegue adicionar o app à tela inicial a partir do navegador móvel e abri-lo em modo standalone (sem barra de endereço).

**Acceptance Scenarios**:

1. **Given** que o usuário acessa a aplicação em um navegador compatível com instalação de apps, **When** o sistema detecta que o app ainda não foi instalado, **Then** um banner discreto oferece a opção de instalação.
2. **Given** que o usuário aceita a instalação, **When** o processo é concluído, **Then** um ícone é adicionado à tela inicial do dispositivo e ao tocar nele o app abre em tela cheia, sem barra de navegação do navegador.

---

### User Story 2 - Acesso Sem Repetir Login (Priority: P1)

O usuário abre o app pela tela inicial e deve ser reconhecido automaticamente, sem precisar inserir credenciais ou solicitar novo link de acesso, mesmo após dias sem uso.

**Why this priority**: A fricção de login repetitivo é uma das principais causas de abandono em apps de registro comportamental. Profissionais e pais precisam registrar dados rapidamente no momento do comportamento; qualquer atraso compromete a qualidade do registro.

**Independent Test**: Pode ser testado simulando o fechamento do app, reinício do dispositivo e reabertura após 7 dias, verificando se o usuário permanece autenticado.

**Acceptance Scenarios**:

1. **Given** que o usuário está autenticado e fecha o app, **When** reabre o app após 24 horas, **Then** o acesso é concedido automaticamente sem solicitar login.
2. **Given** que a sessão do usuário está próxima de expirar, **When** o app é aberto, **Then** a sessão é renovada silenciosamente antes que o usuário perceba qualquer interrupção.
3. **Given** que o usuário abre o app em uma conexão de rede instável, **When** a autenticação precisa ser verificada, **Then** o sistema tenta renovar a sessão e, se falhar por falta de conexão, permite acesso offline aos dados já carregados.
4. **Given** que a sessão do usuário expirou além da janela de recuperação (ex: inativo por mais de 30 dias), **When** o app é aberto, **Then** os dados já carregados continuam visíveis em modo leitura, mas um banner fixo informa que a sessão expirou e solicita novo login para realizar ações de escrita.
5. **Given** que um usuário autenticado deseja encerrar a sessão em um dispositivo compartilhado, **When** toca no botão de logout no menu da header, **Then** a sessão é encerrada imediatamente e o app retorna à tela de login.

---

### User Story 3 - Cache de Assets para Carregamento Instantâneo (Priority: P2)

O usuário abre o app e a interface carrega instantaneamente, mesmo em conexões 3G instáveis ou em áreas com sinal fraco, porque os recursos visuais e de código já estão disponíveis localmente.

**Why this priority**: Muitos usuários acessam o app em contextos clínicos ou escolares onde a conectividade pode ser limitada. Esperar por carregamento de CSS, JS ou ícones cria fricção desnecessária.

**Independent Test**: Pode ser testado ativando o modo offline do navegador e verificando se o app continua carregando e exibindo a interface corretamente.

**Acceptance Scenarios**:

1. **Given** que o usuário já abriu o app anteriormente com conexão ativa, **When** abre o app novamente sem conexão de rede, **Then** a interface carrega completamente com todos os estilos, scripts e ícones visuais.
2. **Given** que o app possui novas versões de arquivos estáticos após uma atualização, **When** o usuário abre o app com conexão ativa, **Then** os novos arquivos são baixados e armazenados automaticamente para uso futuro offline.

---

### User Story 4 - Experiência Visual Nativa em Mobile (Priority: P2)

O usuário interage com o app como se fosse uma aplicação nativa, com orientação fixa em retrato, cores consistentes com a identidade visual e ícones adaptados para diferentes tamanhos de tela.

**Why this priority**: A percepção de qualidade e confiança no app aumenta quando a experiência visual é coesa e profissional. Isso é especialmente importante para profissionais de saúde que usam o app em contextos formais.

**Independent Test**: Pode ser testado verificando a aparência do app em diferentes dispositivos móveis e confirmando que a orientação permanece em retrato e as cores da barra de status combinam com o app.

**Acceptance Scenarios**:

1. **Given** que o usuário abre o app em um smartphone, **When** o app é carregado, **Then** a orientação é fixada em retrato e a barra de status do sistema assume a cor principal da aplicação.
2. **Given** que o usuário adiciona o app à tela inicial, **When** o ícone é exibido, **Then** ele aparece nítido em todos os tamanhos padrão de ícones do sistema operacional (pequeno, médio, grande).

---

### Edge Cases

- O que acontece quando o usuário limpa os dados de navegação do dispositivo?
- Como o sistema lida com tentativas de abrir o app em um navegador que não suporta instalação de PWA?
- O que ocorre se o usuário tenta renovar a sessão mas o servidor de autenticação está indisponível?
- Como o app se comporta quando a sessão expirou irreversivelmente: exibe dados em cache em modo leitura ou redireciona para login?
- Como o app se comporta quando o usuário alterna entre o app e outras aplicações rapidamente?
- O que acontece se o usuário tenta acessar o app offline após nunca ter aberto online antes?
- O que acontece quando um dispositivo é compartilhado entre múltiplos cuidadores e um deles esquece de fazer logout?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que usuários instalem a aplicação na tela inicial de seus dispositivos móveis a partir de navegadores compatíveis.
- **FR-002**: O sistema DEVE manter a sessão do usuário ativa por pelo menos 30 dias sem exigir nova autenticação, desde que o usuário abra o app periodicamente.
- **FR-003**: O sistema DEVE renovar a sessão do usuário automaticamente quando o app é aberto, antes que o usuário interaja com a interface.
- **FR-004**: O sistema DEVE exibir um banner ou botão discreto oferecendo instalação do app apenas para usuários que ainda não o instalaram.
- **FR-005**: O sistema DEVE armazenar localmente os recursos visuais e de interface (folhas de estilo, scripts, ícones) para que o app carregue instantaneamente em aberturas subsequentes.
- **FR-006**: O sistema DEVE detectar quando novas versões dos recursos estáticos estão disponíveis e atualizar o cache local automaticamente.
- **FR-007**: O sistema DEVE abrir em modo standalone (tela cheia, sem barra de endereço do navegador) quando acessado pelo ícone da tela inicial.
- **FR-008**: O sistema DEVE fixar a orientação do app em retrato em dispositivos móveis.
- **FR-009**: O sistema DEVE fornecer ícones em múltiplas resoluções para garantir exibição nítida em diferentes tamanhos de tela e densidades de pixel.
- **FR-010**: O sistema DEVE permitir que o usuário continue visualizando dados já carregados mesmo quando offline, embora funcionalidades que exigem sincronização em tempo real possam estar indisponíveis.
- **FR-011**: Quando a sessão do usuário expirou além da janela de recuperação, o sistema DEVE manter os dados já carregados acessíveis em modo leitura e exibir um banner fixo solicitando novo login para ações de escrita.
- **FR-012**: O sistema DEVE oferecer um botão de logout explícito no menu da header, posicionado junto às funcionalidades de assinatura, configurações e dark mode, que encerra a sessão imediatamente e redireciona para a tela de login.

### Key Entities

- **Sessão de Usuário**: Representa o estado de autenticação ativa do usuário, incluindo tempo de expiração e token de renovação.
- **Cache de Aplicação**: Conjunto de recursos estáticos armazenados localmente no dispositivo do usuário para carregamento rápido e acesso offline.
- **Manifesto do App**: Metadados que descrevem o app ao sistema operacional (nome, ícones, cores, modo de exibição).

## Constraints & Non-Negotiables *(mandatory)*

- **UX Fricção Zero**: Nenhuma ação primária pode exceder 5 segundos ou usar
  `<select>` para inputs frequentes. Área de toque mínima: 48×48 dp.
- **Anti-SPA**: Proibido uso de React, Vue, Angular ou Svelte. Interatividade
  via HTMX + Alpine.js apenas.
- **Service Layer**: Toda lógica de negócio reside em `services.py`; views
  apenas validam input e retornam response.
- **Anti-ORM (dados core)**: Dados de pacientes usam `supabase-py`; ORM do
  Django é proibido para esses dados.
- **RLS-First**: Toda query em dados de pacientes filtra por `parent_id`;
  UUIDs serializados como `str(uuid)` antes do SDK Supabase.
- **Offline-First**: Ações de registro DEVEM persistir em LocalStorage e
  sincronizar quando online; conflitos usam last-write-wins.
- **Type Hinting**: Todo código Python DEVE usar type hints estritos.
- **Lock-in por utilidade**: Nenhuma feature pode dificultar entrada ou
  exportação de dados do usuário.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O tempo de carregamento visual da interface em aberturas subsequentes do app deve ser inferior a 1 segundo, mesmo em conexões 3G simuladas.
- **SC-002**: 95% dos usuários que abrem o app pelo ícone da tela inicial devem ser reconhecidos automaticamente sem precisar interagir com uma tela de login.
- **SC-003**: O app deve permanecer funcional (exibindo interface e dados já carregados) por pelo menos 30 dias sem que o usuário precise se autenticar novamente, desde que abra o app pelo menos uma vez a cada 7 dias.
- **SC-004**: A taxa de instalação do app (usuários que adicionam à tela inicial após ver o banner) deve ser mensurável, com meta inicial de 30% dos usuários ativos mobile.
- **SC-005**: O app deve alcançar uma pontuação mínima de 90 em auditorias de PWA (Progressive Web App) em ferramentas de análise de performance e compatibilidade.

## Assumptions

- Os usuários principais acessam a aplicação principalmente por dispositivos móveis (smartphones e tablets).
- A maioria dos navegadores modernos (Chrome, Safari, Edge mobile) suporta instalação de PWAs; navegadores antigos ou limitados recebem a experiência web padrão sem degradação funcional.
- O sistema de autenticação existente suporta renovação de sessão e persistência de tokens de longa duração.
- A instalação do PWA é uma facilidade opcional; usuários que preferem acessar via navegador continuam tendo acesso total às funcionalidades.
- O banner de instalação deve ser não-intrusivo e respeitar preferências do usuário (não reaparecer após ser explicitamente dispensado por 30 dias).
