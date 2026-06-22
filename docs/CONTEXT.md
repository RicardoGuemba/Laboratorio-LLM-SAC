# Contexto do projeto

Documentação detalhada de **uso e arquitetura**: [`SISTEMA.md`](SISTEMA.md).

## Resumo

- **O quê:** simulador de diálogo entre dois LLMs locais com personas editáveis.
- **Modos:** debate formal (12 turnos, placar) e conversa casual (infinita, automática).
- **Stack:** FastAPI + React + LM Studio (porta 1234) + launcher macOS.

## Links

| Documento | Conteúdo |
|-----------|----------|
| [SISTEMA.md](SISTEMA.md) | Uso, arquitetura, fluxos, estrutura |
| [DEBATE_RULES.md](DEBATE_RULES.md) | Regras do debate e personas |
| [README.md](../README.md) | Instalação e início rápido |

## LM Studio (checklist)

1. Start Server na porta **1234**
2. JIT + Auto-Evict ON
3. Conferir nomes: `GET http://127.0.0.1:1234/v1/models`
4. Ajustar [`config.yaml`](../config.yaml) se necessário

## Entrada recomendada

Duplo clique em **`Abrir Laboratorio Personas LLM.app`** (não confundir com `Laboratorio-Personas-LLM.app`, que é o bundle interno do servidor).
