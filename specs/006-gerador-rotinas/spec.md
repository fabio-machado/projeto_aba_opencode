# Feature Specification: Gerador de Rotinas (Módulo Rotinas)

**Feature Branch**: `006-gerador-rotinas`  
**Created**: 2026-04-29  
**Status**: Draft  
**Input**: User description: "Implementar o Gerador de Rotinas, o produto low ticket de entrada da plataforma Autismo em Foco. O objetivo é fornecer aos cuidadores uma ferramenta extremamente simples, operável com uma mão (mobile-first), para criar, gerenciar e exportar rotinas visuais (pictogramas) que reduzem a ansiedade da criança."

## Clarifications

### Session 2026-04-29

- Q: Qual o número máximo de pictogramas por rotina? → A: 15 pictogramas (alinhado com o limite do PDF no SC-005).
- Q: Qual padrão de acessibilidade deve ser atendido? → A: WCAG 2.1 AA.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar Minha Primeira Rotina (Priority: P1)

O cuidador acessa o módulo de rotinas, vê um estado inicial acolhedor com uma mensagem encorajadora e um botão de ação principal. Ao tocar, ele define um título e seleciona pictogramas de categorias disponíveis (Higiene, Alimentação, Escola, Lazer, etc.) tocando neles. Os pictogramas aparecem imediatamente em uma linha do tempo vertical. Ao tocar "Salvar", a rotina é gravada e o cuidador retorna ao mural onde seu novo card aparece.

**Why this priority**: É a funcionalidade core do produto. Sem a capacidade de criar uma rotina, nenhum outro fluxo faz sentido. Representa o MVP absoluto.

**Independent Test**: Pode ser testado totalmente acessando o módulo, tocando no CTA de criação, preenchendo título, selecionando pictogramas e salvando. Ao retornar ao mural, o card da rotina recém-criada deve estar visível.

**Acceptance Scenarios**:

1. **Given** que o cuidador está na tela "Mural" sem nenhuma rotina, **When** ele visualiza a tela, **Then** ele vê uma ilustração acolhedora, uma mensagem sobre os benefícios das rotinas visuais e um botão principal "Criar Minha Primeira Rotina".
2. **Given** que o cuidador toca em "Criar Minha Primeira Rotina", **When** a tela do construtor abre, **Then** ele vê um campo de título vazio, uma área de timeline vazia e uma gaveta inferior com pictogramas categorizados por abas.
3. **Given** que o cuidador está no construtor, **When** ele digita um título e toca em pictogramas na gaveta, **Then** cada pictograma tocado aparece instantaneamente na timeline central, abaixo de qualquer pictograma já adicionado.
4. **Given** que a timeline tem pictogramas, **When** o cuidador toca no ícone "X" de um pictograma, **Then** o pictograma é removido imediatamente da timeline.
5. **Given** que o título está preenchido e há ao menos um pictograma na timeline, **When** o cuidador toca em "Salvar Rotina", **Then** a rotina é salva com sucesso e ele retorna ao mural vendo o novo card.
6. **Given** que o título está vazio OU a timeline não tem pictogramas, **When** o cuidador olha o botão "Salvar Rotina", **Then** o botão está visualmente desabilitado e não pode ser acionado.
7. **Given** que o cuidador está no construtor com alterações não salvas e tenta voltar atrás, **When** ele navega para fora da tela, **Then** o sistema alerta que há alterações pendentes (confirmação de abandono).

---

### User Story 2 - Reordenar e Refinar a Rotina (Priority: P2)

O cuidador abre uma rotina existente a partir do "Mural" e entra no construtor com os pictogramas já carregados. Ele pode adicionar novos pictogramas, remover os que não quer mais e, principalmente, reordená-los arrastando e soltando na timeline para refletir a sequência ideal do dia da criança. Ao salvar, a nova ordem é mantida.

**Why this priority**: Após criar uma rotina, a necessidade natural do cuidador é ajustar a ordem das atividades conforme aprende o que funciona melhor para a criança. O drag-and-drop é o diferencial de usabilidade do produto.

**Independent Test**: Pode ser testado abrindo uma rotina existente, arrastando um pictograma para nova posição na timeline, adicionando um novo, removendo outro e salvando. Ao reabrir a rotina, a ordem e composição devem refletir exatamente as alterações feitas.

**Acceptance Scenarios**:

1. **Given** que o cuidador está no "Mural" com rotinas existentes, **When** ele toca em um card de rotina, **Then** o construtor abre com o título preenchido e os pictogramas carregados na ordem salva.
2. **Given** que o cuidador está no construtor com pictogramas na timeline, **When** ele arrasta um pictograma para uma nova posição, **Then** os pictogramas se reorganizam visualmente em tempo real mantendo a nova ordem.
3. **Given** que o cuidador fez alterações em uma rotina existente, **When** ele toca em "Salvar Rotina", **Then** a rotina é atualizada atomicamente com o título atual, a nova lista de pictogramas e a ordem correta.

---

### User Story 3 - Gerenciar Rotinas pelo Mural (Priority: P3)

O cuidador visualiza todas as suas rotinas no "Mural", identifica cada uma pelo título em formato de card. A partir de cada card, ele pode rapidamente renomear uma rotina (via menu de contexto) ou excluí-la quando não for mais necessária. O mural sempre mostra a lista atualizada e, se todas as rotinas forem excluídas, o estado vazio acolhedor reaparece.

**Why this priority**: Gestão do conjunto de rotinas é essencial para uso continuado. Sem renomear/excluir, o cuidador acumularia rotinas obsoletas e perderia organização — essencial para famílias atípicas que já lidam com alta carga cognitiva.

**Independent Test**: Pode ser testado visualizando o mural com múltiplas rotinas, renomeando uma via menu de contexto e verificando a atualização do título no card, e excluindo outra confirmando a remoção do card. Ao excluir a última rotina, o empty state deve reaparecer.

**Acceptance Scenarios**:

1. **Given** que o cuidador está no "Mural" com uma ou mais rotinas, **When** ele visualiza a tela, **Then** cada rotina aparece como um card mostrando seu título e ações disponíveis.
2. **Given** que o cuidador toca no menu de contexto (ellipsis) de um card, **When** o menu abre, **Then** ele vê as opções "Renomear" e "Excluir".
3. **Given** que o cuidador seleciona "Renomear", **When** ele confirma o novo nome, **Then** o título do card é atualizado imediatamente no mural.
4. **Given** que o cuidador seleciona "Excluir", **When** ele confirma a exclusão, **Then** o card é removido do mural.
5. **Given** que a última rotina foi excluída, **When** o mural é recarregado, **Then** o estado vazio acolhedor com o CTA "Criar Minha Primeira Rotina" é exibido novamente.
6. **Given** que o cuidador está no "Mural", **When** ele visualiza a tela, **Then** o cabeçalho exibe "Rotinas do(a) [Nome da Criança]" personalizado.

---

### User Story 4 - Exportar Rotina em PDF (Priority: P4)

O cuidador, a partir do "Mural", toca em um botão de ação rápida em um card de rotina para gerar um arquivo PDF daquela rotina. O PDF contém a sequência visual dos pictogramas da rotina para que possa ser impresso, compartilhado com a escola ou terapeuta, ou usado offline.

**Why this priority**: A exportação é o passo que leva a rotina para fora da tela — para a parede, a geladeira ou a mochila da criança. É o fechamento do ciclo de valor, mas depende da existência da rotina (P1) para ser útil.

**Independent Test**: Pode ser testado tocando no botão de exportação de um card, verificando que um arquivo PDF é gerado e baixado, contendo o título da rotina e os pictogramas na ordem correta.

**Acceptance Scenarios**:

1. **Given** que o cuidador está no "Mural" com uma rotina existente, **When** ele toca no botão de exportação (PDF) do card, **Then** um arquivo PDF é gerado e o download se inicia.
2. **Given** que o PDF foi gerado, **When** o cuidador abre o arquivo, **Then** ele visualiza o título da rotina e todos os pictogramas na sequência correta.
3. **Given** que o download do PDF falha (ex: conexão instável), **When** ocorre o erro, **Then** o sistema exibe uma mensagem amigável orientando o cuidador a tentar novamente.

---

### Edge Cases

- O que acontece quando o cuidador adiciona o mesmo pictograma múltiplas vezes à mesma rotina? O sistema deve permitir — pictogramas repetidos são válidos (ex: "Lavar as mãos" antes e depois do lanche).
- O que acontece quando a gaveta de categorias tem apenas uma categoria com pictogramas? As abas ainda devem ser exibidas, permitindo navegação entre categorias mesmo que algumas estejam vazias.
- O que acontece quando o cuidador tenta salvar com título acima do limite de 100 caracteres? O sistema deve rejeitar com mensagem clara de validação (limite máximo definido nas assumptions).
- O que acontece durante a edição se a conexão com o servidor cair ao salvar? O sistema deve preservar os dados localmente (LocalStorage) e oferecer nova tentativa de sincronização.
- O que acontece quando o cuidador acessa o construtor sem pictogramas disponíveis no banco? A gaveta deve exibir mensagem informativa ("Nenhum pictograma disponível no momento") em vez de uma grade vazia.
- O que acontece quando o nome da criança não está disponível (ex: primeiro acesso, perfil incompleto)? O cabeçalho do mural deve exibir um fallback genérico como "Minhas Rotinas".
- O que acontece quando o cuidador tenta adicionar um 16º pictograma à rotina? O sistema deve impedir a adição, exibir um indicador de limite atingido (ex: "15/15") e desabilitar visualmente os pictogramas na gaveta.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE exibir um estado vazio acolhedor (ilustração + texto encorajador) quando o cuidador não possui rotinas cadastradas.
- **FR-002**: O sistema DEVE exibir o cabeçalho do mural com o nome da criança associada ao perfil logado, no formato "Rotinas do(a) [Nome]".
- **FR-003**: O cuidador DEVE poder criar uma nova rotina fornecendo um título e selecionando ao menos um pictograma, em uma única operação de salvamento.
- **FR-004**: O sistema DEVE impedir o salvamento (botão desabilitado) quando o título está vazio ou a timeline não contém pictogramas.
- **FR-005**: O sistema DEVE adicionar pictogramas à timeline com um único toque, com feedback visual imediato (sem recarregamento de página).
- **FR-006**: O cuidador DEVE poder remover pictogramas individuais da timeline durante a edição.
- **FR-007**: O cuidador DEVE poder reordenar os pictogramas na timeline arrastando e soltando (drag-and-drop), com reorganização visual em tempo real.
- **FR-008**: O sistema DEVE preservar a ordem dos pictogramas definida pelo cuidador após o salvamento.
- **FR-009**: O cuidador DEVE poder visualizar todas as suas rotinas no mural, cada uma representada como um card com título visível.
- **FR-010**: O cuidador DEVE poder renomear uma rotina existente a partir do menu de contexto (ellipsis) do card no mural.
- **FR-011**: O cuidador DEVE poder excluir uma rotina existente a partir do menu de contexto (ellipsis) do card no mural, com confirmação prévia.
- **FR-012**: O cuidador DEVE poder gerar e baixar um arquivo PDF de qualquer rotina a partir do botão de exportação no card do mural.
- **FR-013**: O PDF exportado DEVE conter o título da rotina e todos os pictogramas na ordem definida.
- **FR-014**: O sistema DEVE organizar os pictogramas disponíveis em categorias (abas) na gaveta inferior do construtor (ex: Higiene, Alimentação, Escola, Lazer).
- **FR-015**: O sistema DEVE alertar o cuidador sobre alterações não salvas antes de abandonar o construtor (confirmação de navegação).
- **FR-016**: Todas as operações de escrita (criar, editar, excluir, renomear) DEVEM ser filtradas pelo `parent_id` do cuidador autenticado (RLS-First).
- **FR-017**: O sistema DEVE persistir tentativas de salvamento no armazenamento local do dispositivo e sincronizar quando a conexão for restaurada (Offline-First).
- **FR-018**: O sistema DEVE impor um limite máximo de 15 pictogramas por rotina, desabilitando a adição de novos pictogramas ao atingir esse teto e exibindo indicador visual do limite.
- **FR-019**: O sistema DEVE atender aos critérios de acessibilidade WCAG 2.1 AA em todos os componentes do módulo de rotinas (contraste, navegação por teclado, leitores de tela, alvos de toque mínimos).

### Key Entities

- **Rotina (Routine)**: Representa uma rotina visual criada pelo cuidador. Atributos: título, relação com o cuidador (`parent_id`), data de criação e modificação.
- **Item da Rotina (RoutineItem)**: Associação entre uma rotina e um pictograma com uma posição ordinal. Atributos: rotina (`routine_id`), pictograma (`pictogram_id`), ordem (`order_position`).
- **Pictograma (Pictogram)**: Imagem representando uma atividade (ex: escovar dentes, comer, dormir). Atributos: nome, imagem, categoria (`category_id`).
- **Categoria (Category)**: Agrupamento temático de pictogramas. Atributos: nome (ex: "Higiene", "Alimentação"), ordem de exibição.

## Constraints & Non-Negotiables *(mandatory)*

- **UX Fricção Zero**: Nenhuma ação primária pode exceder 5 segundos ou usar `<select>` para inputs frequentes. Área de toque mínima: 48×48 dp. O construtor deve ser operável com uma mão (mobile-first), com a gaveta de pictogramas fixa na zona do polegar.
- **Anti-SPA**: Proibido uso de React, Vue, Angular ou Svelte. Interatividade via HTMX + Alpine.js apenas.
- **Service Layer**: Toda lógica de negócio reside em `routine_service.py`; views do Django apenas validam input e retornam response.
- **Anti-ORM (dados core)**: Dados de rotinas e pictogramas usam `supabase-py`; ORM do Django é proibido para esses dados. Toda operação de edição de itens da rotina deve ocorrer em batch (exclusão dos antigos e inserção em massa dos novos).
- **RLS-First**: Toda query em dados de rotinas filtra por `parent_id`; UUIDs serializados como `str(uuid)` antes do SDK Supabase.
- **Offline-First**: Ações de salvamento DEVEM persistir em LocalStorage e sincronizar quando online; conflitos usam last-write-wins.
- **Type Hinting**: Todo código Python DEVE usar type hints estritos.
- **Lock-in por utilidade**: Nenhuma feature pode dificultar a exportação de dados do usuário. A exportação PDF é um exemplo de portabilidade.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O cuidador consegue criar uma rotina completa (título + 5 pictogramas) em até 60 segundos.
- **SC-002**: 90% dos cuidadores completam a criação de sua primeira rotina na primeira tentativa, sem erros ou confusão.
- **SC-003**: A adição de um pictograma à timeline apresenta feedback visual em menos de 200ms após o toque.
- **SC-004**: A operação de arrastar e soltar pictogramas reflete a nova ordem visualmente em tempo real (sem atraso perceptível).
- **SC-005**: O PDF de uma rotina com até 15 pictogramas é gerado e o download se inicia em até 3 segundos.
- **SC-006**: O cuidador consegue operar todas as ações do construtor (adicionar, remover, reordenar, salvar) com apenas uma mão, sem precisar reposicionar o dispositivo.
- **SC-007**: O salvamento offline previne perda de dados em pelo menos 95% dos casos de queda de conexão durante a edição.
- **SC-008**: O módulo de rotinas atinge conformidade WCAG 2.1 AA, verificado por auditoria de acessibilidade (contraste, teclado, leitor de tela).

## Assumptions

- O catálogo de pictogramas é pré-carregado e mantido pela plataforma (o cuidador não faz upload de imagens próprias nesta versão).
- O nome da criança exibido no cabeçalho do mural vem do perfil vinculado ao login do cuidador.
- A confirmação de exclusão de rotina usa um diálogo modal simples ("Tem certeza?") sem opção de desfazer (soft delete não é escopo desta versão).
- O formato do PDF segue um layout de grade vertical padrão com um pictograma por linha, título no topo, adequado para impressão A4.
- As categorias de pictogramas disponíveis inicialmente são: Higiene, Alimentação, Escola, Lazer, Terapia, Sono e Outros.
- O título da rotina tem limite máximo de 100 caracteres.
- A autenticação do cuidador já está resolvida pelo módulo de login (Feature 004-auth-login-magic-link) e sessão persistente (Feature 005-pwa-persistent-auth).
