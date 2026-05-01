# Contract: PDF Export

**Endpoint**: `GET /routines/<uuid:routine_id>/export/`  
**Auth**: Required (session cookie + middleware)  
**Method**: GET (link/botão direto)  
**Response**: `application/pdf` (download)

## Request

```http
GET /routines/660e8400-e29b-41d4-a716-446655440010/export/
Cookie: supabase_session=<jwt>
```

### Query Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| (nenhum) | — | — | — |

## Success Response

### 200 — PDF gerado

```http
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="Rotina - Hora do Banho.pdf"
Content-Length: 28473

<binary PDF data>
```

**Behavior**: O navegador inicia download automático (`Content-Disposition: attachment`). O botão de exportação usa `window.open()` ou `<a download>` com target — sem interromper a navegação no mural.

## Error Responses

### 404 — Rotina não encontrada ou acesso negado

```http
HTTP/1.1 404 Not Found
Content-Type: text/html

<h1>Rotina não encontrada</h1>
<p>A rotina solicitada não existe ou você não tem acesso a ela.</p>
```

### 500 — Erro na geração

```http
HTTP/1.1 500 Internal Server Error
Content-Type: text/html

<h1>Erro ao gerar PDF</h1>
<p>Ocorreu um erro ao gerar o PDF. Por favor, tente novamente em instantes.</p>
```

## PDF Layout Specification

### Dimensões

- **Página**: A4 (210mm × 297mm)
- **Margens**: 15mm todos os lados
- **Fonte**: Helvetica (built-in reportlab)
- **Tamanhos**: Título 18pt, Pictograma nome 14pt

### Estrutura da Página

```
┌────────────────────────────────────────┐
│                                        │  ← margem 15mm
│  "Hora do Banho"                       │  ← título centralizado, bold, 18pt
│                                        │
│  ┌──────┐                              │
│  │ 🪥   │  1. Escovar os dentes        │  ← imagem 50×50px + nome 14pt
│  └──────┘                              │
│                                        │
│  ┌──────┐                              │
│  │ 🛁   │  2. Tomar banho              │
│  └──────┘                              │
│                                        │
│  ┌──────┐                              │
│  │ 👕   │  3. Vestir o pijama          │
│  └──────┘                              │
│                                        │
│           ... (até 15 itens)           │
│                                        │
│  ───────────────────────────────       │
│  Autismo em Foco — Gerado em DD/MM/AAAA│  ← rodapé 8pt
└────────────────────────────────────────┘
```

### Regras de Paginação

- **1 página**: Rotinas com 1-8 pictogramas
- **2 páginas**: Rotinas com 9-15 pictogramas (auto page break após o 8º item)
- Cada pictograma ocupa ~15mm de altura (imagem + texto + espaçamento)

## Server-Side Logic

### `routine_service.generate_routine_pdf(parent_id, routine_id) -> bytes`

1. Buscar rotina + itens via Supabase (filtrando por `parent_id`)
2. Se rotina não encontrada → `None` (view retorna 404)
3. Buscar pictogramas referenciados nos itens
4. Montar PDF com `reportlab`:
   a. Canvas A4
   b. Desenhar título centralizado
   c. Para cada item (ordenado por `order_position`):
      - Baixar imagem do Supabase Storage (ou usar URL pública + `urllib`)
      - Desenhar imagem na margem esquerda
      - Desenhar nome do pictograma à direita da imagem
      - Avançar para próxima linha
   d. Adicionar rodapé em cada página
5. Retornar `bytes` do PDF

### Performance Target

- PDF com 15 pictogramas: ≤ 3 segundos (SC-005)
- Cache: Sem cache de PDF (rotinas mudam frequentemente; regeneração garante dados atualizados)
