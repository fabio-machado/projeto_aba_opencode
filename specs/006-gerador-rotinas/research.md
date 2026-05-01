# Research: Gerador de Rotinas

**Feature**: 006-gerador-rotinas  
**Date**: 2026-04-29

## 1. PDF Generation — Server-side Python

### Decision: `reportlab`

Servir PDF via Django view server-side usando `reportlab` (já amplamente usado em projetos Django para geração de documentos).

### Rationale

- **Zero dependência de browser**: PDF gerado no servidor, compatível com qualquer dispositivo
- **Layout controlado**: `reportlab` permite controle preciso de posicionamento via Canvas (coordenadas) — essencial para grid de pictogramas A4
- **Instalação mínima**: `pip install reportlab` (sem binários externos como `wkhtmltopdf` do WeasyPrint)
- **Performance**: Geração puramente programática (sem parsing HTML/CSS) → < 1s para 15 pictogramas
- **Padrão no ecossistema Django**: Amplamente documentado, usado em projetos como Django PDF reports

### Alternatives Considered

| Alternativa | Motivo da rejeição |
|-------------|-------------------|
| WeasyPrint | Requer dependências de sistema (Pango, Cairo, GDK-Pixbuf). Sobrecarga para layout simples de grade. |
| jsPDF (client-side) | PDF gerado no browser depende de canvas rendering. Inconsistente entre dispositivos mobile. Violaria constraint Anti-SPA indiretamente. |
| xhtml2pdf | Não mantido ativamente; suporte a Python 3.12 instável. |

### Implementation Approach

```python
# routine_service.py
def generate_routine_pdf(routine: dict, items: list[dict]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas
    # Layout: título no topo, 1 pictograma por linha (imagem + nome)
    # Retorna bytes do PDF para a view servir como FileResponse
```

---

## 2. Drag-and-Drop — SortableJS + Alpine.js

### Decision: SortableJS v1.15 com binding manual via `x-init`

Usar SortableJS como lib standalone (CDN), inicializado dentro de `x-init` do Alpine.js no builder. O array local de pictogramas (`x-data`) é atualizado via callback `onUpdate` do Sortable.

### Rationale

- **SortableJS é o padrão de facto** para drag-and-drop tátil: suporte nativo a touch events, animações CSS, ghost dragging
- **Leve**: 25KB min+gzip; sem dependências (não requer jQuery)
- **Binding manual > wrapper**: Plugins Alpine-SortableJS são abandonados ou mal mantidos. Inicializar Sortable no `x-init` é 15 linhas de código e dá controle total sobre o array reativo Alpine
- **Constitution II compliance**: SortableJS não é um framework SPA — é uma lib de interação puntual. O estado permanece no Alpine.js
- **Compatibilidade mobile**: Touch events testados em iOS Safari, Chrome Android — funcionamento idêntico

### Alternatives Considered

| Alternativa | Motivo da rejeição |
|-------------|-------------------|
| HTML5 Drag and Drop API nativa | Não funciona em touch devices sem polyfills pesados |
| @shopify/draggable | Excelente, mas 2x maior que SortableJS; sem suporte oficial a Sortable |
| interact.js | Foco em resize/gesture; drag-and-drop é secundário. Overkill |
| Alpine Sort plugin | Repositórios abandonados (último commit 2022), bugs com Alpine 3.x |

### Implementation Pattern

```html
<!-- routine_builder.html -->
<div x-data="routineBuilder()" x-init="initSortable()">
  <div id="timeline" x-ref="timeline">
    <template x-for="(item, idx) in items" :key="item.id">
      <div class="timeline-item" :data-id="item.id">
        <img :src="item.image_url" :alt="item.name">
        <span x-text="item.name"></span>
        <button @click="removeItem(idx)">&times;</button>
      </div>
    </template>
  </div>
</div>
```

```javascript
// routine-builder.js
function routineBuilder() {
  return {
    items: [],
    initSortable() {
      new Sortable(this.$refs.timeline, {
        animation: 200,
        onUpdate: (evt) => {
          const moved = this.items.splice(evt.oldIndex, 1)[0];
          this.items.splice(evt.newIndex, 0, moved);
        }
      });
    }
  };
}
```

---

## 3. Supabase Schema Design — RLS-First

### Decision: 4 tabelas com RLS policies baseadas em `parent_id`

Seguindo o padrão existente do projeto (tabela `profiles`, `login_attempts`, `magic_link_logs`), todas as tabelas de dados core usam `parent_id` como chave de isolamento multi-tenant.

### Rationale

- **Consistência com o projeto**: Todas as tabelas existentes usam `parent_id = auth.uid()` nas policies RLS
- **Segurança em camadas**: RLS no banco + filtro explícito no service layer (defesa em profundidade)
- **Batch edit atômico**: Editar itens da rotina = DELETE todos os `routine_items` antigos + INSERT em massa dos novos — isso garante integridade da ordenação e evita gaps no `order_position`
- **UUID como PK**: Segue o padrão Supabase de `uuid_generate_v4()` para todas as chaves primárias
- **Serialização**: `str(uuid)` antes de qualquer chamada ao SDK Supabase (Constitution IV)

### Schema Preview (detalhado em data-model.md)

```sql
CREATE TABLE pictogram_categories (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  display_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE pictograms (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  category_id UUID REFERENCES pictogram_categories(id),
  name TEXT NOT NULL,
  image_url TEXT NOT NULL
);

CREATE TABLE routines (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  parent_id UUID NOT NULL,
  title VARCHAR(100) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE routine_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  routine_id UUID NOT NULL REFERENCES routines(id) ON DELETE CASCADE,
  pictogram_id UUID NOT NULL REFERENCES pictograms(id),
  order_position INTEGER NOT NULL
);
```

### RLS Policies

- `routines`: `SELECT/INSERT/UPDATE/DELETE` apenas se `parent_id = auth.uid()`
- `routine_items`: `SELECT` via join com `routines.parent_id = auth.uid()`; `INSERT/UPDATE/DELETE` via função RLS que verifica ownership da rotina pai
- `pictograms`, `pictogram_categories`: Leitura pública (`SELECT` para todos); escrita apenas admin

---

## 4. Alpine.js Builder State Architecture

### Decision: `x-data` com array reativo + proxy `$watch` para persistência LocalStorage

O estado do construtor (`title`, `items[]`, `isDirty`) é gerenciado inteiramente no Alpine.js. O salvamento envia payload JSON via `fetch()` nativo (não HTMX) porque:
1. O payload é complexo (array aninhado de objetos)
2. HTMX é otimizado para formulários HTML, não JSON arbitrário
3. A resposta de sucesso redireciona para o mural (full page redirect após save é aceitável)

### Rationale

- **fetch() > HTMX para este caso**: O endpoint de save recebe JSON, não `application/x-www-form-urlencoded`
- **LocalStorage sync**: `$watch('items', ...)` do Alpine persiste automaticamente mudanças para recuperação offline
- **Desabilitação reativa**: Botão Salvar usa `:disabled="!title || items.length === 0"` — zero JS extra

---

## 5. Pictogram Storage — Supabase Storage

### Decision: Imagens hospedadas no Supabase Storage (bucket `pictograms`), URLs públicas

### Rationale

- Já provisionado no plano Supabase do projeto
- URLs estáveis para referência no builder + PDF
- Sem necessidade de servir imagens via Django (performance)
- Caminho: `https://<project>.supabase.co/storage/v1/object/public/pictograms/<category>/<filename>.svg`

### Data Seeding

Pictogramas são pré-carregados via migration SQL (seed data). Categorias definidas na spec assumptions: Higiene, Alimentação, Escola, Lazer, Terapia, Sono, Outros.
