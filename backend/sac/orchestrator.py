from __future__ import annotations

import re
import uuid
from typing import Any, Callable, Awaitable

from backend.config import load_config
from backend.llm.lmstudio import LMStudioClient
from backend.rag.retriever import get_index
from backend.sac.fallbacks import fallback_complaint, fallback_sac_response
from backend.sac.prompts import (
    build_complaint_messages,
    build_sac_messages,
    enforce_max_sentences,
    infer_complaint_category,
    parse_complaint_output,
    parse_manual_complaint,
    pick_complaint_category,
)
from backend.sac.session import RagChunkRef, RoleId, SacSession, SacStatus, TurnRecord, extract_thinking

EmitFn = Callable[[dict[str, Any] | None], Awaitable[None]]

ROLE_CLIENTE = "cliente_truepaleo"
ROLE_SAC = "truepaleo_sac"

_PLACEHOLDER_MARKERS = (
    "[texto da reclamação]",
    "[título curto",
    "[texto da resposta]",
    "corpo:\n[",
)

_META_MARKERS = (
    "user said",
    "the user",
    "output format",
    "body can have",
    "sentences",
    "checklist",
    "instruction",
    "regra de",
    "o usuário quer",
    "formato de saída",
    "must write",
    "need to",
    "let me",
)

_PT_HINTS = (
    "ção",
    "ões",
    "ã",
    " não ",
    " uma ",
    " que ",
    " pedido",
    " truepaleo",
    " comprei",
    " olá",
    "olá",
    " pedimos",
    " desculp",
    " lament",
    " reembolso",
    " equipe",
    " seu ",
    " sua ",
)


def _is_thinking_model(model: str) -> bool:
    lower = model.lower()
    return "thinking" in lower or "lfm" in lower


def _looks_like_valid_pt(text: str, *, min_len: int = 40) -> bool:
    cleaned = text.strip()
    if len(cleaned) < min_len:
        return False
    lower = cleaned.lower()
    if any(m in lower for m in _META_MARKERS):
        return False
    if any(m in lower for m in _PLACEHOLDER_MARKERS):
        return False
    pt_score = sum(1 for h in _PT_HINTS if h in lower)
    en_hits = sum(1 for w in (" the ", " and ", " but ", " user ", " output ") if w in lower)
    return pt_score >= 2 and en_hits == 0


def _sanitize_response(text: str) -> str:
    if not text:
        return ""
    result = text.strip()
    result = re.sub(
        r"^(Assistente|Assistant|Resposta|Response|Cliente|SAC)\s*[:：]\s*",
        "",
        result,
        flags=re.IGNORECASE,
    )
    result = re.sub(r"<\|.*?\|>", "", result)
    result = re.sub(r" {2,}", " ", result)
    return result.strip()


def _speech_from_reasoning(reasoning: str) -> str:
    text = reasoning.strip()
    if not text:
        return ""

    quotes = re.findall(r'"([^"]{20,400})"', text)
    for candidate in reversed(quotes):
        if _looks_like_valid_pt(candidate, min_len=25):
            return candidate.strip()

    sentences = re.findall(r"[^.!?\n]{25,400}[.!?]", text)
    for candidate in reversed(sentences):
        cleaned = candidate.strip()
        if _looks_like_valid_pt(cleaned, min_len=25):
            return cleaned
    return ""


async def _generate_text(
    lm_client: LMStudioClient,
    role_key: str,
    messages: list[dict[str, str]],
    *,
    thinking: bool,
    model: str,
    profile_key: str,
    generation_overrides: dict[str, Any],
    emit: EmitFn,
    stream_role: str,
) -> str:
    use_non_stream = thinking or _is_thinking_model(model)
    full_text = ""

    try:
        if use_non_stream:
            content, reasoning = await lm_client.complete_non_stream(
                role_key,
                messages,
                thinking=thinking or _is_thinking_model(model),
                model=model,
                profile_key=profile_key,
                generation_overrides=generation_overrides,
            )
            full_text = (content or _speech_from_reasoning(reasoning) or "").strip()
            if full_text:
                await emit({"type": "token", "role": stream_role, "content": full_text})
        else:
            async for chunk in lm_client.stream_completion(
                role_key,
                messages,
                thinking=thinking,
                model=model,
                profile_key=profile_key,
                generation_overrides=generation_overrides,
            ):
                if chunk["kind"] == "content":
                    full_text += chunk["text"]
                    await emit({"type": "token", "role": stream_role, "content": chunk["text"]})
    except Exception as exc:
        await emit({"type": "error", "role": stream_role, "message": str(exc)})

    if not full_text.strip() or not _looks_like_valid_pt(full_text, min_len=20):
        try:
            content, reasoning = await lm_client.complete_non_stream(
                role_key,
                messages,
                thinking=True,
                model=model,
                profile_key=profile_key,
                generation_overrides=generation_overrides,
            )
            candidate = (content or _speech_from_reasoning(reasoning) or "").strip()
            if candidate and _looks_like_valid_pt(candidate, min_len=20):
                full_text = candidate
                await emit({"type": "token_replace", "role": stream_role, "content": full_text})
        except Exception as exc:
            await emit({"type": "error", "role": stream_role, "message": str(exc)})

    sanitized = _sanitize_response(full_text)
    clean, _ = extract_thinking(sanitized)
    return (clean or sanitized).strip()


async def _respond_to_complaint(
    session: SacSession,
    lm_client: LMStudioClient,
    emit: EmitFn,
    *,
    title: str,
    body: str,
    category: str,
) -> SacSession:
    config = load_config()
    sac_cfg = config.get("sac", {})

    session.category = category
    session.complaint_title = title
    session.complaint_text = body

    index = get_index()
    rag_results = index.retrieve(
        f"{title} {body}",
        top_k=int(sac_cfg.get("rag_top_k", 4)),
        min_score=float(sac_cfg.get("rag_min_score", 0.1)),
        category=category,
    )
    session.rag_chunks = [
        RagChunkRef(
            doc_id=r["doc_id"],
            section=r["section"],
            text=r["text"],
            score=r["score"],
        )
        for r in rag_results
    ]
    await emit({"type": "rag_context", "chunks": rag_results})

    await emit({"type": "response_start", "role": "sac"})
    session.current_stream_text = ""

    sac_messages = build_sac_messages(session, title, body, rag_results)
    raw_response = await _generate_text(
        lm_client,
        ROLE_SAC,
        sac_messages,
        thinking=session.sac_thinking,
        model=session.sac_model,
        profile_key=session.sac_profile,
        generation_overrides=session.sac_llm_params,
        emit=emit,
        stream_role="sac",
    )

    max_response = int(sac_cfg.get("max_response_sentences", 15))
    response_text = enforce_max_sentences(raw_response, max_response)

    if not _looks_like_valid_pt(response_text, min_len=30):
        response_text = fallback_sac_response(title)
        await emit({"type": "token_replace", "role": "sac", "content": response_text})

    session.response_text = response_text

    response_turn = TurnRecord(
        id=str(uuid.uuid4()),
        role=RoleId.SAC,
        text=response_text,
    )
    session.turns.append(response_turn)

    session.status = SacStatus.COMPLETED
    await emit(
        {
            "type": "response_done",
            "turn": {
                "id": response_turn.id,
                "role": "sac",
                "text": response_text,
            },
            "session": session.to_dict(),
            "is_finished": True,
        }
    )
    return session


async def run_manual_response(
    session: SacSession,
    complaint_text: str,
    lm_client: LMStudioClient,
    emit: EmitFn,
    *,
    title: str | None = None,
) -> SacSession:
    config = load_config()
    sac_cfg = config.get("sac", {})
    session.status = SacStatus.IN_PROGRESS
    session.complaint_title = ""
    session.complaint_text = ""
    session.response_text = ""
    session.rag_chunks = []
    session.turns = []

    parsed_title, body = parse_manual_complaint(complaint_text, title=title)
    body = enforce_max_sentences(body, int(sac_cfg.get("max_complaint_sentences", 10)))
    category = infer_complaint_category(f"{parsed_title} {body}")

    await emit(
        {
            "type": "complaint_start",
            "role": "cliente",
            "category": category,
            "manual": True,
        }
    )

    complaint_turn = TurnRecord(
        id=str(uuid.uuid4()),
        role=RoleId.CLIENTE,
        text=body,
        title=parsed_title,
    )
    session.turns.append(complaint_turn)

    await emit(
        {
            "type": "complaint_done",
            "turn": {
                "id": complaint_turn.id,
                "role": "cliente",
                "title": parsed_title,
                "text": body,
            },
            "session": session.to_dict(),
            "manual": True,
        }
    )

    return await _respond_to_complaint(
        session,
        lm_client,
        emit,
        title=parsed_title,
        body=body,
        category=category,
    )


async def run_simulation(
    session: SacSession,
    lm_client: LMStudioClient,
    emit: EmitFn,
) -> SacSession:
    config = load_config()
    sac_cfg = config.get("sac", {})
    session.status = SacStatus.IN_PROGRESS
    session.complaint_title = ""
    session.complaint_text = ""
    session.response_text = ""
    session.rag_chunks = []
    session.turns = []

    category = pick_complaint_category()
    session.category = category

    await emit({"type": "complaint_start", "role": "cliente", "category": category})
    session.current_stream_text = ""

    complaint_messages = build_complaint_messages(session, category)
    raw_complaint = await _generate_text(
        lm_client,
        ROLE_CLIENTE,
        complaint_messages,
        thinking=session.cliente_thinking,
        model=session.cliente_model,
        profile_key=session.cliente_profile,
        generation_overrides=session.cliente_llm_params,
        emit=emit,
        stream_role="cliente",
    )

    max_complaint = int(sac_cfg.get("max_complaint_sentences", 10))
    title, body = parse_complaint_output(raw_complaint)
    body = enforce_max_sentences(body, max_complaint)

    if not _looks_like_valid_pt(f"{title} {body}", min_len=30):
        title, body = fallback_complaint(category)
        await emit({"type": "token_replace", "role": "cliente", "content": f"{title}\n\n{body}"})

    session.complaint_title = title
    session.complaint_text = body

    complaint_turn = TurnRecord(
        id=str(uuid.uuid4()),
        role=RoleId.CLIENTE,
        text=body,
        title=title,
    )
    session.turns.append(complaint_turn)

    await emit(
        {
            "type": "complaint_done",
            "turn": {
                "id": complaint_turn.id,
                "role": "cliente",
                "title": title,
                "text": body,
            },
            "session": session.to_dict(),
        }
    )

    return await _respond_to_complaint(
        session,
        lm_client,
        emit,
        title=title,
        body=body,
        category=category,
    )
