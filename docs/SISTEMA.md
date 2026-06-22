# Laboratório Personas LLM — Sistema

Simulador local de diálogo entre dois personagens (Rico e Pobre), cada um powered por um LLM distinto via **LM Studio**. Suporta **debate formal** (turnos estruturados, placar) e **conversa casual** (papinho infinito até parar).

---

## 1. Visão de uso

### Pré-requisitos

| Componente | Função |
|------------|--------|
| **Python 3.11+** | Backend FastAPI |
| **Node 18+** | Build do frontend (primeira vez / dev) |
| **LM Studio** | Inferência local na porta **1234** |

No LM Studio: aba **Developer** → **Start Server** (porta 1234), **JIT loading** e **Auto-Evict** ligados.

### Como iniciar

1. Primeira vez:
   ```bash
   bash scripts/install_deps.sh
   bash scripts/preparar-app.sh
   ```
2. **Duplo clique** em `Abrir Laboratorio Personas LLM.app` (recomendado).
3. O navegador abre em `http://127.0.0.1:8765`.
4. Para encerrar: `Laboratorio-Personas-LLM-Stop.command`.

### Fluxo na interface

```
Configuração → Escolher modo → Iniciar → Arena (avatares + falas) → Encerrar / Nova sessão
```

1. **Perfis** — personalidade base de cada debatedor (Markdown em `personas/`).
2. **Skills** — comportamentos extras opcionais (jargão, ironia técnica, etc.).
3. **Modelos** — qualquer LLM de chat listado pelo LM Studio.
4. **Parâmetros LLM** — temperature, top_p, max_tokens por debatedor.

### Modo: Debate formal

- Você define o **tema** (mín. 3 caracteres).
- Posições **a favor / contra** sorteadas ao iniciar.
- Até **12 turnos** (3 rodadas × 4 fases: abertura, argumento, réplica, tréplica).
- Avance manualmente com **Próximo turno**.
- **Placar** reage às falas (buzzwords, cartões, aplausos).

### Modo: Conversa casual

- **Sem tema manual** — um dos modelos sorteia assunto informal alinhado ao perfil.
- Tom de **dia a dia**; respostas limitadas a **5 frases**.
- Turnos **alternam automaticamente** até clicar em **Parar conversa**.
- Sem placar nem fases de debate.

### Laboratório de personas

Botão **Laboratório: Perfis & Skills** na tela inicial — CRUD de perfis e skills (persistidos em `personas/` como `.md`).

---

## 2. Arquitetura

### Diagrama de componentes

```
┌─────────────────────────────────────────────────────────────┐
│  Navegador (React SPA em backend/static ou Vite :5173 dev)  │
│  Arena · DebateSetup · SSE EventSource                      │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP / SSE
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI — backend/main.py (:8765)                          │
│  · Sessões em memória                                       │
│  · Orquestração de turnos (debate | casual)                 │
│  · API personas CRUD                                        │
└───────────────────────────┬─────────────────────────────────┘
                            │ OpenAI-compatible API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  LM Studio — http://127.0.0.1:1234/v1                       │
│  · /models · /chat/completions                              │
└─────────────────────────────────────────────────────────────┘
```

### Camadas do backend

| Módulo | Responsabilidade |
|--------|------------------|
| `backend/main.py` | Rotas REST, SSE, `_run_debate_turn` / `_run_casual_turn` |
| `backend/debate/session.py` | `DebateSession`, turnos, placar, `SessionMode` |
| `backend/debate/state_machine.py` | Agenda finita do debate (12 turnos) |
| `backend/debate/casual_state_machine.py` | Alternância infinita até `ENDED` |
| `backend/debate/prompts.py` | Prompts de debate (posição, fase, retries) |
| `backend/debate/casual_prompts.py` | Prompts informais + limite de frases |
| `backend/debate/topic_generator.py` | Tema casual via LLM + fallback |
| `backend/debate/persona_store.py` | Leitura/escrita de perfis e skills |
| `backend/llm/lmstudio.py` | Cliente HTTP (stream + non-stream) |
| `backend/reactions/heuristics.py` | Gestos e placar (sem LLM extra) |

### Fluxo de um turno (SSE)

```
POST /api/debate/start
  → DebateSession.create()
GET  /api/debate/{id}/stream     (EventSource)
POST /api/debate/{id}/next       (debate) ou kickoff automático (casual)
  → turn_start → token(s) → reaction → turn_done
  → casual: auto-advance após delay
```

Eventos SSE: `turn_start`, `token`, `token_replace`, `reaction`, `turn_done`, `error`, `debate_ended`, `closed`.

### Personas (dados)

```
personas/
  defaults.yaml              # perfil/skill padrão por debatedor
  rico/profiles/*.md         # personalidade Rico
  rico/skills/*.md
  pobre/profiles/*.md
  pobre/skills/*.md
```

Formato Markdown (≤15 linhas): metadados YAML + prompt de comportamento.

### Configuração

[`config.yaml`](../config.yaml):

- `lmstudio` — URL, modelos padrão, timeouts, temperature por debatedor
- `debate` — rodadas, contexto, retries, limites de palavras
- `casual` — contexto, max frases, delay entre turnos, timeout de tema
- `server` — host/porta do FastAPI

### Launchers (macOS)

| Artefato | Papel |
|----------|--------|
| `Abrir Laboratorio Personas LLM.app` | Entrada recomendada (AppleScript → launcher) |
| `Laboratorio-Personas-LLM.app` | Bundle com script bash do servidor |
| `Laboratorio-Personas-LLM-Stop.command` | Mata processo na porta 8765 |

### Frontend (dev)

- **Produção:** `bash scripts/build.sh` → copia `frontend/dist` para `backend/static/`
- **Dev:** `uvicorn` na 8765 + `npm run dev` na 5173 (proxy Vite → API)

### Testes

| Tipo | Onde |
|------|------|
| Unitários / API mock | `tests/test_*.py` — `pytest` |
| E2E (servidor + LM Studio live) | `tests/integration/test_*_e2e.py` |

---

## 3. Estrutura de diretórios (essencial)

```
Abrir Laboratorio Personas LLM.app/   # duplo clique
Laboratorio-Personas-LLM.app/         # launcher interno
Laboratorio-Personas-LLM-Stop.command
backend/                              # FastAPI + static build
frontend/src/                         # React (fonte)
personas/                             # perfis e skills
config.yaml
scripts/                              # install_deps, build, preparar-app
docs/                                 # documentação
tests/                                # pytest + integration E2E
```

Artefatos **gerados localmente** (não versionar): `.venv/`, `frontend/node_modules/`, logs, PID, `.pytest_cache/`, `backend/static/` (rebuild via `scripts/build.sh`).

---

## 4. Documentação relacionada

- [`DEBATE_RULES.md`](DEBATE_RULES.md) — fases, placar, personas cadastradas
- [`README.md`](../README.md) — início rápido e troubleshooting
