from __future__ import annotations

import re

from backend.config import load_config
from backend.debate.persona_store import get_profile, get_skills
from backend.debate.session import DebateSession, DebaterId

CASUAL_RULES = """Responda em português do Brasil. Produza APENAS a fala do personagem.
Tom informal, como papo de dia a dia entre conhecidos — sem debate formal, sem posições A FAVOR/CONTRA.
Use no máximo 5 frases. Pode incluir perguntas, exclamações, interjeições e gírias compatíveis com o perfil.
Não use rótulos como "Rico:" ou "Assistente:". Não repita instruções."""


def _context_turn_limit() -> int:
    cfg = load_config().get("casual", {})
    return int(cfg.get("context_turns", load_config().get("debate", {}).get("context_turns", 6)))


def _max_sentences() -> int:
    return int(load_config().get("casual", {}).get("max_sentences", 5))


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

SKILLS ADICIONAIS:
{skills}"""


def build_casual_system_prompt(
    session: DebateSession,
    debater: DebaterId,
) -> str:
    profile_key = session.rico_profile if debater == DebaterId.RICO else session.pobre_profile
    skill_ids = session.rico_skills if debater == DebaterId.RICO else session.pobre_skills
    persona = _debater_persona(debater, profile_key, skill_ids)
    max_sent = _max_sentences()
    return f"""{persona}

CONTEXTO DA CONVERSA:
Assunto do papo: {session.topic}

REGRAS:
{CASUAL_RULES}
Limite rígido: no máximo {max_sent} frases por resposta."""


def build_casual_user_prompt(
    session: DebateSession,
    debater: DebaterId,
    *,
    is_opener: bool,
) -> str:
    if is_opener:
        return (
            f"Inicie a conversa informal sobre: {session.topic}. "
            "Puxe o assunto de forma natural, como quem encontra o amigo e solta o papo. "
            "Pode ser pergunta, comentário ou história curta."
        )
    opponent = DebaterId.POBRE if debater == DebaterId.RICO else DebaterId.RICO
    last_opponent = None
    for turn in reversed(session.turns):
        if turn.debater == opponent:
            last_opponent = turn.text.strip()
            break
    if last_opponent:
        excerpt = last_opponent[:280] + ("…" if len(last_opponent) > 280 else "")
        return (
            f"Seu amigo acabou de dizer:\n\"{excerpt}\"\n\n"
            "Responda de forma casual e natural, reagindo ao que ele disse. "
            "Pode concordar, discordar levemente, fazer piada, perguntar algo ou contar algo relacionado."
        )
    return "Continue a conversa informal de forma natural."


def build_casual_messages(
    session: DebateSession,
    debater: DebaterId,
) -> list[dict[str, str]]:
    is_opener = session.turn_index == 0 and debater == session.topic_starter
    messages: list[dict[str, str]] = [
        {"role": "system", "content": build_casual_system_prompt(session, debater)},
    ]
    history = session.turns[-_context_turn_limit() :]
    for turn in history:
        role = "assistant" if turn.debater == debater else "user"
        messages.append({"role": role, "content": turn.text.strip()})
    messages.append(
        {
            "role": "user",
            "content": build_casual_user_prompt(session, debater, is_opener=is_opener),
        }
    )
    return messages


def build_topic_generation_messages(
    debater: DebaterId,
    profile_key: str,
    skill_ids: list[str],
) -> list[dict[str, str]]:
    persona = _debater_persona(debater, profile_key, skill_ids)
    return [
        {
            "role": "system",
            "content": f"""{persona}

TAREFA: Sugira UM assunto informal de conversa do dia-a-dia, alinhado ao seu jeito de ser.
Exemplos: fila do mercado, vizinho barulhento, série nova, preço do café, trânsito, fofoca leve.
Responda APENAS com o assunto em uma frase curta (máx. 15 palavras). Sem aspas, sem explicação.""",
        },
        {
            "role": "user",
            "content": "Qual assunto informal você puxaria num papo de corredor agora?",
        },
    ]


def enforce_max_sentences(text: str, maximum: int | None = None) -> str:
    limit = maximum if maximum is not None else _max_sentences()
    cleaned = text.strip()
    if not cleaned:
        return cleaned
    parts = re.findall(r"[^.!?]+[.!?]+|[^.!?]+$", cleaned)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return cleaned
    if len(parts) <= limit:
        return cleaned
    truncated = " ".join(parts[:limit]).strip()
    if truncated and truncated[-1] not in ".!?":
        truncated += "."
    return truncated


FALLBACK_TOPICS = [
    "O preço absurdo do delivery ontem à noite",
    "Aquela série que todo mundo fala mas ninguém terminou",
    "O vizinho que liga o som às 7 da manhã",
    "Fila interminável no mercado no sábado",
    "Café que subiu de preço de novo",
    "O trânsito da volta do trabalho hoje",
    "Meme que viralizou e ninguém entendeu direito",
    "Plano de fim de semana que desmoronou na última hora",
]
