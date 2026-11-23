# Simulação de atendimento com modelos locais

Simulador de atendimento ao cliente (SAC) da **TRUEPALEO**: o LLM `cliente_truepaleo` gera reclamações realistas e o `Truepaleo-SAC` responde usando skills configuráveis e RAG BM25 sobre histórico do Reclame AQUI.

**Arquivos de referência**

- [config.yaml](config.yaml)

## Início rápido

1. Instale **Python 3.11+**, **Node 18+** e **LM Studio**
2. No LM Studio: Start Server na porta **1234**, JIT + Auto-Evict ON
3. Primeira vez:

```bash
bash scripts/install_deps.sh
bash scripts/preparar-app.sh
```

4. Desenvolvimento — terminal 1 (backend):

```bash
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn backend.main:app --reload --host 127.0.0.1 --port 8765
```

Terminal 2 (frontend):

```bash
cd frontend && npm install && npm run dev
```

Abra `http://localhost:5173`

## Uso

1. Configure perfis, skills e modelos LM Studio para **cliente_truepaleo** e **Truepaleo-SAC**
2. Clique em **Aplicar configuração**
3. Na barra de comando, digite `simule` e pressione Enter
4. A reclamação é gerada, o RAG recupera contexto e a resposta SAC é exibida

## Base de conhecimento (RAG)

Arquivos Markdown em `knowledge/reclame_aqui/` e `knowledge/policies/`. Gerenciáveis pela interface **Base de Conhecimento**. Indexação BM25 automática no startup.

## Configuração

Edite [`config.yaml`](config.yaml) — modelos LM Studio por role, parâmetros SAC e RAG.

## Testes

```bash
pytest tests/                    # backend: unitários + funcionais (21 testes)
cd frontend && npm run test      # frontend: avatares e UI (15 testes)
```

## Documentação

- [`docs/GUIA_DIDATICO.md`](docs/GUIA_DIDATICO.md) — explicação didática, casos de uso, diagramas e arquitetura
- [`docs/SISTEMA.md`](docs/SISTEMA.md) — arquitetura e fluxos
- [`docs/CONTEXT.md`](docs/CONTEXT.md) — índice do projeto
- [`knowledge/README.md`](knowledge/README.md) — schema dos arquivos RAG

## Estrutura

```
backend/
  sac/          # sessão, prompts, orchestrator
  rag/          # BM25 index e loader
  personas/     # CRUD profiles/skills
  llm/          # cliente LM Studio
frontend/src/   # React UI TRUEPALEO
personas/       # cliente/ e sac/ (Markdown)
knowledge/      # base RAG
config.yaml
```
