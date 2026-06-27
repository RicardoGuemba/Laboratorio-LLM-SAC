from __future__ import annotations

import random
import re
from typing import Any

from backend.config import load_config
from backend.personas.persona_store import get_profile, get_skills
from backend.sac.session import SacSession

TRUEPALEO_PRODUCTS = [
    "Desodorante Natural Tallow e Coco (R$ 58,90)",
    "Tallow Balm True Paleo (R$ 109,90)",
    "Full Paleo Kit (R$ 182,16)",
    "Purple Paleo Kit (R$ 143,48)",
    "Red Paleo Kit (R$ 143,48)",
]

CATEGORY_HINTS: dict[str, str] = {
    "atraso_entrega": "Atraso na entrega, pedido não chegou no prazo prometido, rastreio parado.",
    "produto_defeituoso": "Produto com defeito, textura estranha, desodorante esfarela ao usar.",
    "reacao_alergica": "Reação na pele, irritação, vermelhidão após uso do produto.",
    "sac_sem_resposta": "Empresa não responde e-mails ou WhatsApp, falta de suporte.",
    "reembolso": "Solicitação de reembolso conforme garantia de eficácia de 30 dias.",
    "produto_vencido": "Produto recebido com validade vencida ou próxima do vencimento.",
    "produto_nao_enviado": "Pedido pago mas não saiu para envio.",
    "desodorante_ineficaz": "Desodorante não funciona mesmo após período de adaptação.",
}


def _persona_block(role: str, profile_id: str, skill_ids: list[str]) -> str:
    profile = get_profile(role, profile_id)  # type: ignore[arg-type]
    skills = get_skills(role, skill_ids)  # type: ignore[arg-type]
    lines = [
        f"Perfil: {profile.get('name', profile_id)}",
        profile.get("prompt") or profile.get("description", ""),
    ]
    for skill in skills:
        lines.append(f"- Skill {skill['name']}: {skill.get('prompt') or skill['description']}")
    return "\n".join(lines)


def pick_complaint_category() -> str:
    config = load_config()
    categories = config.get("sac", {}).get("complaint_categories", list(CATEGORY_HINTS.keys()))
    return random.choice(categories)


def build_complaint_messages(session: SacSession, category: str) -> list[dict[str, str]]:
    product = random.choice(TRUEPALEO_PRODUCTS)
    hint = CATEGORY_HINTS.get(category, "Reclamação sobre produto ou serviço TRUEPALEO.")
    persona = _persona_block("cliente", session.cliente_profile, session.cliente_skills)
    max_sentences = int(load_config().get("sac", {}).get("max_complaint_sentences", 10))

    system = f"""Você é um cliente brasileiro real da TRUEPALEO (marca de cuidados pessoais naturais).
Escreva uma reclamação autêntica no estilo Reclame AQUI sobre a TRUEPALEO.

{persona}

Regras:
- Escreva SOMENTE em português brasileiro coloquial
- NUNCA explique instruções, regras ou o que o usuário pediu
- NUNCA escreva em inglês nem meta-comentários sobre o formato
- Máximo {max_sentences} frases no corpo
- Mencione produto TRUEPALEO quando fizer sentido: {product}
- Categoria desta reclamação: {category} — {hint}
- Inclua detalhes plausíveis (data aproximada, valor, expectativa)
- NÃO escreva como assistente; escreva como cliente insatisfeito
- Formato de saída EXATO:
TITULO: [título curto da reclamação]
CORPO:
[texto da reclamação]"""

    user = "Gere agora a reclamação sobre a TRUEPALEO."
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_sac_messages(
    session: SacSession,
    complaint_title: str,
    complaint_text: str,
    rag_context: list[dict[str, Any]],
) -> list[dict[str, str]]:
    persona = _persona_block("sac", session.sac_profile, session.sac_skills)
    max_sentences = int(load_config().get("sac", {}).get("max_response_sentences", 15))

    rag_block = ""
    if rag_context:
        parts = []
        for i, chunk in enumerate(rag_context, 1):
            parts.append(
                f"### Referência {i} ({chunk.get('doc_id', '?')} — {chunk.get('section', '?')})\n"
                f"{chunk.get('text', '')}"
            )
        rag_block = "## Contexto RAG (reclamações e respostas anteriores)\n" + "\n\n".join(parts)

    policies = """## Políticas TRUEPALEO
- Garantia de eficácia: reembolso em até 30 dias se o desodorante não funcionar
- Produtos naturais: tallow grass-fed, óleo de coco, cera de abelha, sem fragrâncias artificiais
- Prazo de entrega: 4-7 dias úteis conforme região
- SAC responde em até 24-48 horas úteis
- Para logística: solicitar nº pedido e e-mail de compra"""

    system = f"""Você é o atendimento SAC oficial da TRUEPALEO (True Paleo Ltda).
Responda à reclamação do cliente com empatia, clareza e solução prática.

{persona}

{policies}

{rag_block}

Regras:
- Escreva SOMENTE em português brasileiro profissional e acolhedor
- NUNCA explique instruções nem escreva meta-comentários
- Máximo {max_sentences} frases
- Use o contexto RAG como referência de tom e soluções, sem copiar literalmente
- Peça dados necessários (nº pedido, e-mail) quando relevante
- Proponha solução concreta (reembolso, reposição, rastreio, orientação de uso)
- NÃO invente políticas que contradigam as acima
- Assine como "Equipe TRUEPALEO" ou similar"""

    user = f"""Reclamação recebida:

Título: {complaint_title}

{complaint_text}

Escreva a resposta oficial do SAC TRUEPALEO."""

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_complaint_output(raw: str) -> tuple[str, str]:
    text = raw.strip()
    title_match = re.search(r"TITULO:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else "Reclamação sobre TRUEPALEO"

    body_match = re.search(r"CORPO:\s*\n?(.*)", text, re.IGNORECASE | re.DOTALL)
    if body_match:
        body = body_match.group(1).strip()
    else:
        body = re.sub(r"^TITULO:.*?\n", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
        if not body:
            body = text

    return title, body


def enforce_max_sentences(text: str, maximum: int) -> str:
    sentences = re.findall(r"[^.!?]+[.!?]+", text.strip())
    if not sentences:
        return text.strip()
    if len(sentences) <= maximum:
        return text.strip()
    return " ".join(s.strip() for s in sentences[:maximum])


def parse_manual_complaint(raw: str, *, title: str | None = None) -> tuple[str, str]:
    text = raw.strip()
    if not text:
        raise ValueError("Reclamação vazia")
    if title and title.strip():
        return title.strip(), text

    title_match = re.search(r"^TITULO:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    body_match = re.search(r"CORPO:\s*\n?(.*)", text, re.IGNORECASE | re.DOTALL)
    if title_match and body_match:
        return title_match.group(1).strip(), body_match.group(1).strip()

    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if len(lines) >= 2 and len(lines[0]) <= 80:
        return lines[0], "\n".join(lines[1:]).strip()

    first_sentence = re.match(r"^(.{10,120}?[.!?])", text)
    if first_sentence:
        title_text = first_sentence.group(1).strip()
        return title_text, text

    if len(text) <= 80:
        return text, text
    return f"{text[:57].rstrip()}…", text


def infer_complaint_category(text: str) -> str:
    lower = text.lower()
    best_cat = ""
    best_score = 0
    for cat, hint in CATEGORY_HINTS.items():
        score = 0
        for token in re.findall(r"[a-záàâãéêíóôõúç]+", hint.lower()):
            if len(token) > 3 and token in lower:
                score += 1
        for part in cat.split("_"):
            if len(part) > 4 and part in lower:
                score += 3
        if score > best_score:
            best_score = score
            best_cat = cat
    return best_cat or pick_complaint_category()
