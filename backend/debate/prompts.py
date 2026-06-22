from __future__ import annotations

import re

from backend.config import load_config
from backend.debate.session import DebatePhase, DebateSession, DebaterId
from backend.debate.persona_store import get_profile, get_skills

RULES = """Responda em português do Brasil. Produza APENAS a fala do personagem.
PROIBIDO repetir, parafrasear ou reescrever a pergunta do debate.
Comece direto com seu argumento — nunca com a pergunta."""


def _context_turn_limit() -> int:
    return int(load_config().get("debate", {}).get("context_turns", 6))

PHASE_LABELS = {
    DebatePhase.OPENING: "Abertura",
    DebatePhase.ARGUMENT: "Argumento",
    DebatePhase.REPLICA: "Réplica",
    DebatePhase.TREPLICA: "Tréplica",
}

_PT_STOPWORDS = frozenset(
    {
        "que",
        "com",
        "para",
        "por",
        "uma",
        "uns",
        "umas",
        "dos",
        "das",
        "nos",
        "nas",
        "pelo",
        "pela",
        "deve",
        "deveria",
        "ser",
        "estar",
        "como",
        "sobre",
        "mais",
        "menos",
        "muito",
        "pouco",
        "isso",
        "essa",
        "esse",
        "este",
        "esta",
        "qual",
        "quais",
        "quando",
        "onde",
        "porque",
        "pois",
        "mas",
        "porém",
        "então",
        "ainda",
        "também",
        "existir",
        "dever",
    }
)


def _phase_instruction(phase: DebatePhase, position_label: str) -> str:
    if phase == DebatePhase.OPENING:
        return (
            f'Abertura: comece com "Estou {position_label} porque" e dê 2 frases de argumento. '
            f"Não escreva a pergunta do debate."
        )
    if phase == DebatePhase.ARGUMENT:
        return f"Desenvolva seu argumento {position_label} em 2–3 frases. Sem repetir a pergunta."
    if phase == DebatePhase.REPLICA:
        return f"Rebata o oponente em 2–3 frases. Mantenha-se {position_label}."
    return f"Defenda-se da réplica em 2 frases. Reforce que está {position_label}."


def _skills_prompt(debater: DebaterId, skill_ids: list[str]) -> str:
    debater_key = "rico" if debater == DebaterId.RICO else "pobre"
    skills = get_skills(debater_key, skill_ids)
    if not skills:
        return "Nenhuma skill adicional."
    return "\n".join(f"- {s['name']}: {s['prompt']}" for s in skills)


def _debater_persona(debater: DebaterId, profile_key: str, skill_ids: list[str]) -> str:
    debater_key = "rico" if debater == DebaterId.RICO else "pobre"
    profile = get_profile(debater_key, profile_key)
    name = profile.get("name", debater_key.title())
    profile_prompt = (profile.get("prompt") or profile.get("description") or "").strip()
    skills = _skills_prompt(debater, skill_ids)
    return f"""PERSONA: {name}

PERFIL DE PERSONALIDADE (obrigatório — comporte-se exatamente assim):
{profile_prompt}

SKILLS ADICIONAIS (reforce na fala):
{skills}"""


def build_system_prompt(
    session: DebateSession,
    debater: DebaterId,
    phase: DebatePhase,
    word_limit: int | None = None,
    *,
    thinking: bool = False,
    strict: bool = False,
) -> str:
    profile_key = session.rico_profile if debater == DebaterId.RICO else session.pobre_profile
    skill_ids = session.rico_skills if debater == DebaterId.RICO else session.pobre_skills
    persona = _debater_persona(debater, profile_key, skill_ids)
    position = session.rico_position if debater == DebaterId.RICO else session.pobre_position
    position_label = "A FAVOR" if position == "a_favor" else "CONTRA"
    topic = session.topic.strip()
    phase_inst = _phase_instruction(phase, position_label)

    limit_note = f"\nLimite: até {word_limit} palavras." if word_limit else ""
    strict_note = (
        "\nIMPORTANTE: foque no tema e responda diretamente ao oponente."
        if strict
        else ""
    )

    return f"""{persona}
{RULES}

[Contexto interno — NÃO repetir em voz alta]
Assunto: {topic}
Posição: {position_label} | Fase: {PHASE_LABELS[phase]}
Tarefa: {phase_inst}{limit_note}{strict_note}

Exemplo CORRETO (CONTRA): "Estou CONTRA porque isso penaliza quem construiu patrimônio com visão de longo prazo. Herança não é lucro — é continuidade familiar."
Exemplo ERRADO: repetir ou reescrever a pergunta do debate."""


def _last_opponent_turn(session: DebateSession, debater: DebaterId):
    for turn in reversed(session.turns):
        if turn.debater != debater:
            return turn
    return None


def build_turn_user_prompt(
    session: DebateSession,
    debater: DebaterId,
    phase: DebatePhase,
    *,
    strict: bool = False,
) -> str:
    position = session.rico_position if debater == DebaterId.RICO else session.pobre_position
    position_label = "A FAVOR" if position == "a_favor" else "CONTRA"
    last_opp = _last_opponent_turn(session, debater)

    if strict:
        return (
            f'CORREÇÃO: sua fala anterior só repetiu a pergunta. '
            f'Comece com "Estou {position_label} porque" e dê 2 frases de argumento. '
            f"Não escreva a pergunta do debate."
        )

    if last_opp:
        opp_text = last_opp.text.strip()[:220]
        return (
            f"O oponente disse: «{opp_text}»\n\n"
            f"Rebata em 2 frases (sem repetir a pergunta do debate):"
        )

    if phase == DebatePhase.OPENING:
        return (
            f'Comece EXATAMENTE com "Estou {position_label} porque" '
            f"e explique em 2 frases. Não escreva a pergunta do debate."
        )

    return f"Continue o debate com 2 frases ({position_label}, sem repetir a pergunta):"


def build_messages(
    session: DebateSession,
    debater: DebaterId,
    phase: DebatePhase,
    word_limit: int | None = None,
    *,
    thinking: bool = False,
    strict: bool = False,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": build_system_prompt(
                session, debater, phase, word_limit, thinking=thinking, strict=strict
            ),
        },
    ]

    # Histórico: dá contexto das falas anteriores (próprias e do oponente).
    # role=assistant para as próprias falas, role=user para as do oponente,
    # com texto limpo (sem rótulos) para não induzir o modelo a imitar formato.
    history = session.turns[-_context_turn_limit() :]
    for turn in history:
        role = "assistant" if turn.debater == debater else "user"
        messages.append({"role": role, "content": turn.text.strip()})

    messages.append(
        {
            "role": "user",
            "content": build_turn_user_prompt(session, debater, phase, strict=strict),
        }
    )
    return messages


def _normalize_for_compare(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def is_topic_echo(text: str, topic: str) -> bool:
    """True quando a resposta é essencialmente a pergunta repetida."""
    t = _normalize_for_compare(text)
    q = _normalize_for_compare(topic)
    if not t or not q:
        return False
    if t == q:
        return True

    t_words = t.split()
    q_words = q.split()
    q_set = set(q_words)
    if not q_set:
        return False

    overlap = len(set(t_words) & q_set) / len(q_set)
    # Eco puro: quase só palavras da pergunta, sem argumento extra.
    if overlap >= 0.9 and len(t_words) <= len(q_words) + 1:
        return True
    if q in t and len(t_words) <= len(q_words) + 1:
        return True
    return False


def strip_echoed_topic(text: str, topic: str) -> str:
    """Remove a pergunta/tema do debate quando o modelo a repete na resposta."""
    cleaned = text.strip()
    topic_norm = topic.strip().lower().rstrip("?.! ")
    if not topic_norm:
        return cleaned

    if is_topic_echo(cleaned, topic):
        return ""

    # Remove repetições literais do tema no início.
    pattern = re.compile(
        r'^["“«\s]*' + re.escape(topic.strip().rstrip("?.! ")) + r'[?.!"”»\s\-—]*',
        re.IGNORECASE,
    )
    prev = None
    while prev != cleaned:
        prev = cleaned
        cleaned = pattern.sub("", cleaned).strip()

    lines = cleaned.splitlines()
    if lines:
        first = lines[0].strip().lower().rstrip("?.! ").strip('"“«»”')
        if first and (first == topic_norm or first in topic_norm or topic_norm in first):
            cleaned = "\n".join(lines[1:]).strip()

    if not cleaned or is_topic_echo(cleaned, topic):
        return ""

    return cleaned


def _topic_tokens(topic: str) -> list[str]:
    raw = [w.lower() for w in re.findall(r"\w{3,}", topic)]
    return [t for t in raw if t not in _PT_STOPWORDS]


def topic_relevance_score(topic: str, text: str) -> float:
    """Heurística simples: quanto da questão aparece na resposta (0–1)."""
    topic_tokens = _topic_tokens(topic)
    if not topic_tokens:
        return 1.0
    text_lower = text.lower()
    hits = sum(1 for t in topic_tokens if t in text_lower)
    return hits / len(topic_tokens)


def fallback_argument(session: DebateSession, debater: DebaterId) -> str:
    """Fala mínima quando o modelo só repete a pergunta."""
    position = session.rico_position if debater == DebaterId.RICO else session.pobre_position
    label = "A FAVOR" if position == "a_favor" else "CONTRA"
    if debater == DebaterId.RICO:
        if position == "a_favor":
            return (
                f"Estou {label} porque quem constrói patrimônio merece continuidade, não punição. "
                f"Isso é visão estratégica básica — patrimônio não é lucro, é legado."
            )
        return (
            f"Estou {label} porque penalizar herança mata incentivo de longo prazo. "
            f"Quem entende de mercado premium sabe que legado familiar não é lucro especulativo."
        )
    if position == "a_favor":
        return (
            f"Estou {label} porque concentração de riqueza corrói mobilidade social e investimento público. "
            f"Herança acima de certo patamar funciona como transferência de poder, não de mérito."
        )
    return (
        f"Estou {label} porque herança é continuidade de projeto familiar, não renda corrente. "
        f"Confiscar patrimônio já tributado distorce incentivos sem ganho proporcional de equidade."
    )


def needs_echo_retry(text: str, topic: str) -> bool:
    return is_topic_echo(text, topic)


def needs_topic_retry(topic: str, text: str, threshold: float | None = None) -> bool:
    if is_topic_echo(text, topic):
        return True
    cfg = load_config().get("debate", {})
    min_score = threshold if threshold is not None else float(cfg.get("topic_relevance_min", 0.15))
    min_tokens = int(cfg.get("topic_min_tokens", 2))
    topic_tokens = _topic_tokens(topic)
    if len(topic_tokens) < min_tokens:
        return False
    return topic_relevance_score(topic, text) < min_score


_RESPONSE_MARKERS = frozenset(
    {
        "você disse",
        "voce disse",
        "você afirma",
        "voce afirma",
        "quanto ao",
        "sobre o que",
        "seu argumento",
        "seu ponto",
        "discordo quando",
        "concordo que",
        "ao contrário do que",
        "diferente do que",
        "como você mencionou",
        "como voce mencionou",
        "rebatendo",
        "respondendo ao",
        "em resposta",
    }
)


def references_opponent(text: str) -> bool:
    """Verifica se o texto faz referência explícita ao argumento do oponente."""
    text_lower = text.lower()
    return any(marker in text_lower for marker in _RESPONSE_MARKERS)


def needs_context_retry(session: DebateSession, debater: DebaterId, text: str) -> bool:
    """Verifica se a resposta precisa de retry por não referenciar o oponente."""
    last_opp = None
    for turn in reversed(session.turns):
        if turn.debater != debater:
            last_opp = turn
            break
    
    if not last_opp:
        return False
    
    if references_opponent(text):
        return False
    
    cfg = load_config().get("debate", {})
    if not cfg.get("context_retry", True):
        return False
    
    return True
