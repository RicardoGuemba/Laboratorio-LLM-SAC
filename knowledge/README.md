# Base de Conhecimento TRUEPALEO SAC

Arquivos Markdown usados pelo RAG BM25 para enriquecer respostas do simulador SAC.

## Schema (reclame_aqui/)

```yaml
---
id: identificador-unico
categoria: atraso_entrega | produto_defeituoso | ...
produto: Nome do produto
status_reclamacao: resolvido | respondido | pendente
fonte: reclame_aqui
data_reclamacao: YYYY-MM-DD
data_resposta: YYYY-MM-DD
tags: [tag1, tag2]
---
```

Seções obrigatórias:
- `## Reclamação do cliente`
- `## Resposta TRUEPALEO SAC`

## Políticas (policies/)

Use `tipo: policy` no frontmatter. Conteúdo livre sobre produtos e políticas.

## Atualização

Novos arquivos podem ser adicionados via interface "Base de Conhecimento" ou diretamente na pasta. Reindexe após alterações.
