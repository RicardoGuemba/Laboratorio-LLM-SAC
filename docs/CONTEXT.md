# Contexto do projeto

Documentação detalhada: [`SISTEMA.md`](SISTEMA.md).

## Resumo

- **O quê:** simulador SAC TRUEPALEO — reclamação gerada por LLM cliente, resposta gerada por LLM SAC com RAG BM25.
- **Comando:** digite `simule` na barra de comando para iniciar um ciclo.
- **Stack:** FastAPI + React + LM Studio (porta 1234) + rank-bm25.

## Links

| Documento | Conteúdo |
|-----------|----------|
| [SISTEMA.md](SISTEMA.md) | Uso, arquitetura, fluxos |
| [README.md](../README.md) | Instalação e início rápido |
| [knowledge/README.md](../knowledge/README.md) | Schema RAG |

## LM Studio

1. Start Server na porta **1234**
2. Carregue modelos para `cliente_truepaleo` e `truepaleo_sac`
3. Ajuste [`config.yaml`](../config.yaml) se necessário

## Roles

| Role | Função |
|------|--------|
| `cliente_truepaleo` | Gera reclamações realistas estilo Reclame AQUI |
| `truepaleo_sac` | Responde com empatia, políticas e contexto RAG |
