# Regras do Debate

## Modos de sessão

| Modo | Tema | Turnos | Placar |
|------|------|--------|--------|
| **debate** | Definido pelo usuário | 12 (finito) | Sim |
| **casual** | Sorteado por um LLM | Infinito até parar | Não |

Detalhes do modo casual: [`SISTEMA.md`](SISTEMA.md).

---

## Debate formal — estrutura

3 rodadas × 4 fases = até 12 turnos:

| Fase | Descrição |
|------|-----------|
| Abertura | Posição inicial (Rico abre) |
| Argumento | Argumento principal alternado |
| Réplica | Ataque curto ao colega (≤80 palavras) |
| Tréplica | Defesa curta (≤50 palavras) |

Posições (a favor / contra) são sorteadas ao iniciar.

---

## Personas Rico (`personas/rico/`)

| ID | Nome / foco |
|----|-------------|
| `herdeiro` | Esnobe, jargão corporativo, citações fake |
| `influencer` | Hot takes, slogans, polarização |
| `herdeira_exigente` | Exigente, premium, autoridade |
| `empresaria_truepaleo` | Empresária, estilo true-paleo / wellness |

**Skills:** `jargao_premium`, `autoridade_imaginaria`

---

## Personas Pobre (`personas/pobre/`)

| ID | Nome / foco |
|----|-------------|
| `doutor` | Engenheiro técnico, evidências, trade-offs |
| `founder` | Empreendedor anti-status, execução > ostentação |
| `jose` | Perfil operacional / pragmático |
| `empresaria` | Visão de negócios e métricas |

**Skills:** `reducao_dimensional`, `prova_de_campo`

Padrões atuais em [`personas/defaults.yaml`](../personas/defaults.yaml): Rico `herdeira_exigente`, Pobre `jose`.

---

## Placar (somente debate)

| Métrica | Como sobe/desce |
|---------|-----------------|
| Buzzwords | Jargão corporativo nas falas do Rico |
| Cartões amarelos | Citações sem fonte detectadas |
| Aplausos | 0–100, base 50, ajustado por reações heurísticas |

---

## Reações dos avatares

Heurística local (sem LLM extra) — ouvinte reage à fala do colega:

| Sinal | Gesto típico |
|-------|--------------|
| ≥3 buzzwords | rejeição / head_shake |
| Citação fake | deboche / raised_brow |
| Texto longo (>120 palavras) | rejeição / facepalm |
| Pergunta técnica | alegria / nod |
| Default | talk / shrug |

---

## Conversa casual — regras

- Tom informal, dia a dia, sem posições a favor/contra.
- Máximo **5 frases** por resposta.
- Um debatedor sorteado gera o **tema** e **abre** a conversa.
- Turnos alternam automaticamente; pare com **Parar conversa**.
