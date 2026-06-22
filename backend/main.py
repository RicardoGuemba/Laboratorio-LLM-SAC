from __future__ import annotations

import asyncio
import json
import random
import re
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import load_config
from backend.debate.casual_prompts import build_casual_messages, enforce_max_sentences
from backend.debate.casual_state_machine import CasualStateMachine
from backend.debate.topic_generator import generate_casual_topic, pick_topic_starter
from backend.debate.prompts import (
    build_messages,
    fallback_argument,
    is_topic_echo,
    needs_context_retry,
    needs_topic_retry,
    references_opponent,
    strip_echoed_topic,
    topic_relevance_score,
)
from backend.debate.persona_store import (
    delete_item,
    get_personas_config,
    load_defaults,
    save_defaults,
    save_item,
    validate_debate_selection,
)
from backend.debate.session import (
    DebateSession,
    DebateStatus,
    DebaterId,
    SessionMode,
    TurnRecord,
    extract_thinking,
)
from backend.debate.state_machine import DebateStateMachine
from backend.llm.lmstudio import LMStudioClient
from backend.reactions.heuristics import analyze_reaction, analyze_speaker_gesture, update_scoreboard

app = FastAPI(title="Laboratório Personas LLM")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

config = load_config()
state_machine = DebateStateMachine(max_rounds=config["debate"]["max_rounds"])
casual_state_machine = CasualStateMachine()
lm_client = LMStudioClient()

sessions: dict[str, DebateSession] = {}
stream_queues: dict[str, asyncio.Queue[dict[str, Any] | None]] = {}
turn_lock = asyncio.Lock()
running_turns: set[str] = set()

STATIC_DIR = Path(__file__).resolve().parent / "static"


class LlmParamsPayload(BaseModel):
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=32, le=4096)


class StartDebateRequest(BaseModel):
    mode: Literal["debate", "casual"] = "debate"
    topic: str | None = Field(default=None, max_length=500)
    rico_profile: str = "herdeiro"
    pobre_profile: str = "doutor"
    rico_model: str | None = None
    pobre_model: str | None = None
    rico_thinking: bool = False
    pobre_thinking: bool = False
    rico_skills: list[str] = Field(default_factory=list)
    pobre_skills: list[str] = Field(default_factory=list)
    rico_llm_params: LlmParamsPayload | None = None
    pobre_llm_params: LlmParamsPayload | None = None


class ProfilePayload(BaseModel):
    id: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=5, max_length=600)
    prompt: str = Field(default="", max_length=1200)
    default_skills: list[str] = Field(default_factory=list)


class SkillPayload(BaseModel):
    id: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=5, max_length=300)
    prompt: str = Field(min_length=5, max_length=300)


class DefaultsPayload(BaseModel):
    rico: dict[str, Any]
    pobre: dict[str, Any]


def _machine_for(session: DebateSession) -> DebateStateMachine | CasualStateMachine:
    if session.mode == SessionMode.CASUAL:
        return casual_state_machine
    return state_machine


@app.get("/api/personas")
async def personas_config() -> dict[str, Any]:
    return get_personas_config()


@app.put("/api/personas/defaults")
async def update_defaults(body: DefaultsPayload) -> dict[str, Any]:
    try:
        for debater in ("rico", "pobre"):
            cfg = getattr(body, debater)
            profile = cfg.get("profile")
            skills = cfg.get("skills") or []
            validate_debate_selection(debater, profile, skills)
        save_defaults({"rico": body.rico, "pobre": body.pobre})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return get_personas_config()


@app.post("/api/personas/{debater}/profiles")
async def create_profile(debater: str, body: ProfilePayload) -> dict[str, Any]:
    if debater not in ("rico", "pobre"):
        raise HTTPException(status_code=400, detail="Debatedor inválido")
    try:
        item = save_item(debater, "profiles", body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return item


@app.put("/api/personas/{debater}/profiles/{profile_id}")
async def update_profile(debater: str, profile_id: str, body: ProfilePayload) -> dict[str, Any]:
    if debater not in ("rico", "pobre"):
        raise HTTPException(status_code=400, detail="Debatedor inválido")
    if body.id != profile_id:
        raise HTTPException(status_code=400, detail="ID do corpo deve coincidir com a URL")
    try:
        item = save_item(debater, "profiles", body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return item


@app.delete("/api/personas/{debater}/profiles/{profile_id}")
async def remove_profile(debater: str, profile_id: str) -> dict[str, str]:
    if debater not in ("rico", "pobre"):
        raise HTTPException(status_code=400, detail="Debatedor inválido")
    try:
        delete_item(debater, "profiles", profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"deleted": profile_id}


@app.post("/api/personas/{debater}/skills")
async def create_skill(debater: str, body: SkillPayload) -> dict[str, Any]:
    if debater not in ("rico", "pobre"):
        raise HTTPException(status_code=400, detail="Debatedor inválido")
    try:
        item = save_item(debater, "skills", body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return item


@app.put("/api/personas/{debater}/skills/{skill_id}")
async def update_skill(debater: str, skill_id: str, body: SkillPayload) -> dict[str, Any]:
    if debater not in ("rico", "pobre"):
        raise HTTPException(status_code=400, detail="Debatedor inválido")
    if body.id != skill_id:
        raise HTTPException(status_code=400, detail="ID do corpo deve coincidir com a URL")
    try:
        item = save_item(debater, "skills", body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return item


@app.delete("/api/personas/{debater}/skills/{skill_id}")
async def remove_skill(debater: str, skill_id: str) -> dict[str, str]:
    if debater not in ("rico", "pobre"):
        raise HTTPException(status_code=400, detail="Debatedor inválido")
    try:
        delete_item(debater, "skills", skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"deleted": skill_id}


@app.get("/health")
async def health() -> dict[str, Any]:
    lm_status = await lm_client.health_check()
    return {
        "status": "ok",
        "lmstudio": lm_status,
    }


@app.get("/api/models")
async def list_models() -> dict[str, Any]:
    models = await lm_client.list_models()
    resolved = lm_client.resolved_defaults(models)
    return {
        "models": models,
        "defaults": resolved,
        "configured": lm_client.default_models(),
    }


@app.post("/api/debate/start")
async def start_debate(body: StartDebateRequest) -> dict[str, Any]:
    session_mode = SessionMode(body.mode)
    if session_mode == SessionMode.DEBATE:
        if not body.topic or len(body.topic.strip()) < 3:
            raise HTTPException(status_code=400, detail="Informe um tema com ao menos 3 caracteres.")
        topic = body.topic.strip()
    else:
        topic = body.topic.strip() if body.topic and body.topic.strip() else ""

    defaults = load_defaults()
    rico_skills = body.rico_skills or defaults.get("rico", {}).get("skills", [])
    pobre_skills = body.pobre_skills or defaults.get("pobre", {}).get("skills", [])
    try:
        validate_debate_selection("rico", body.rico_profile, rico_skills)
        validate_debate_selection("pobre", body.pobre_profile, pobre_skills)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    available = await lm_client.list_models()
    try:
        rico_model = lm_client.pick_model(body.rico_model, "rico", available)
        pobre_model = lm_client.pick_model(body.pobre_model, "pobre", available)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    rico_a_favor = random.choice([True, False])
    rico_llm = body.rico_llm_params.model_dump(exclude_none=True) if body.rico_llm_params else {}
    pobre_llm = body.pobre_llm_params.model_dump(exclude_none=True) if body.pobre_llm_params else {}

    topic_starter = pick_topic_starter() if session_mode == SessionMode.CASUAL else None

    session = DebateSession.create(
        topic=topic,
        rico_profile=body.rico_profile,
        pobre_profile=body.pobre_profile,
        rico_model=rico_model,
        pobre_model=pobre_model,
        rico_a_favor=rico_a_favor,
        rico_thinking=body.rico_thinking,
        pobre_thinking=body.pobre_thinking,
        rico_skills=rico_skills,
        pobre_skills=pobre_skills,
        rico_llm_params=rico_llm,
        pobre_llm_params=pobre_llm,
        mode=session_mode,
        topic_starter=topic_starter,
    )

    if session_mode == SessionMode.CASUAL and not session.topic:
        topic_timeout = float(config.get("casual", {}).get("topic_timeout_s", 20))
        try:
            session.topic = await asyncio.wait_for(
                generate_casual_topic(lm_client, session, topic_starter),
                timeout=topic_timeout,
            )
        except Exception:
            from backend.debate.casual_prompts import FALLBACK_TOPICS

            session.topic = random.choice(FALLBACK_TOPICS)

    sessions[session.id] = session
    stream_queues[session.id] = asyncio.Queue()
    if session_mode == SessionMode.CASUAL:
        asyncio.create_task(_kickoff_casual(session.id))
    return session.to_dict()


@app.get("/api/debate/{session_id}")
async def get_debate(session_id: str) -> dict[str, Any]:
    session = _get_session(session_id)
    machine = _machine_for(session)
    turn_info = machine.get_turn_info(session)
    data = session.to_dict()
    if turn_info:
        data["next_turn"] = {
            "debater": turn_info.debater.value,
            "phase": turn_info.phase.value,
            "round_num": turn_info.round_num,
        }
    data["is_finished"] = machine.is_finished(session)
    return data


@app.post("/api/debate/{session_id}/next")
async def next_turn(session_id: str) -> dict[str, Any]:
    session = _get_session(session_id)
    machine = _machine_for(session)
    if machine.is_finished(session):
        raise HTTPException(status_code=400, detail="Sessão já encerrada")

    turn_info = machine.get_turn_info(session)
    if not turn_info:
        raise HTTPException(status_code=400, detail="Nenhum turno disponível")

    asyncio.create_task(_schedule_turn(session_id, turn_info))

    return {
        "started": True,
        "debater": turn_info.debater.value,
        "phase": turn_info.phase.value,
        "round_num": turn_info.round_num,
    }


@app.get("/api/debate/{session_id}/stream")
async def stream_events(session_id: str) -> StreamingResponse:
    _get_session(session_id)
    if session_id not in stream_queues:
        stream_queues[session_id] = asyncio.Queue()

    async def event_generator():
        queue = stream_queues[session_id]
        while True:
            event = await queue.get()
            if event is None:
                yield "data: {\"type\": \"closed\"}\n\n"
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/debate/{session_id}/end")
async def end_debate(session_id: str) -> dict[str, Any]:
    session = _get_session(session_id)
    session.status = DebateStatus.ENDED
    await _emit(session_id, {"type": "debate_ended"})
    await _emit(session_id, None)
    return session.to_dict()


def _get_session(session_id: str) -> DebateSession:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    return sessions[session_id]


async def _emit(session_id: str, event: dict[str, Any] | None) -> None:
    if session_id in stream_queues:
        await stream_queues[session_id].put(event)


async def _schedule_turn(session_id: str, turn_info: Any) -> None:
    if session_id in running_turns:
        return
    running_turns.add(session_id)
    try:
        async with turn_lock:
            await _run_turn(session_id, turn_info)
    finally:
        running_turns.discard(session_id)


async def _kickoff_casual(session_id: str) -> None:
    """Aguarda SSE conectar e dispara o primeiro turno da conversa casual."""
    await asyncio.sleep(0.2)
    session = sessions.get(session_id)
    if not session or session.mode != SessionMode.CASUAL:
        return
    if session.turn_index > 0 or casual_state_machine.is_finished(session):
        return
    turn_info = casual_state_machine.get_turn_info(session)
    if turn_info:
        await _schedule_turn(session_id, turn_info)


async def _auto_advance_casual(session_id: str) -> None:
    delay = float(config.get("casual", {}).get("auto_advance_delay_s", 0.8))
    await asyncio.sleep(delay)
    session = sessions.get(session_id)
    if not session or session.mode != SessionMode.CASUAL:
        return
    if casual_state_machine.is_finished(session):
        return
    turn_info = casual_state_machine.get_turn_info(session)
    if not turn_info:
        return
    await _schedule_turn(session_id, turn_info)


async def _run_turn(session_id: str, turn_info: Any) -> None:
    session = sessions[session_id]
    if session.mode == SessionMode.CASUAL:
        await _run_casual_turn(session_id, turn_info)
        return
    await _run_debate_turn(session_id, turn_info)


async def _run_casual_turn(session_id: str, turn_info: Any) -> None:
    session = sessions[session_id]
    debater = turn_info.debater
    phase = turn_info.phase
    profile_key = session.rico_profile if debater == DebaterId.RICO else session.pobre_profile

    await _emit(
        session_id,
        {
            "type": "turn_start",
            "debater": debater.value,
            "phase": phase.value,
            "round_num": turn_info.round_num,
            "gesture": "talk",
        },
    )

    messages = build_casual_messages(session, debater)
    thinking_enabled = session.rico_thinking if debater == DebaterId.RICO else session.pobre_thinking
    model = session.rico_model if debater == DebaterId.RICO else session.pobre_model
    generation_overrides = (
        session.rico_llm_params if debater == DebaterId.RICO else session.pobre_llm_params
    )
    session.current_stream_text = ""
    full_text = ""

    try:
        content, reasoning = await lm_client.complete_non_stream(
            debater.value,
            messages,
            thinking=thinking_enabled,
            model=model,
            profile_key=profile_key,
            generation_overrides=generation_overrides,
        )
        full_text = (content or _speech_from_reasoning(reasoning) or "").strip()
        if full_text:
            session.current_stream_text = full_text
            await _emit(session_id, {"type": "token", "debater": debater.value, "content": full_text})
    except Exception as exc:
        fallback = _casual_fallback_message(debater, session.topic, str(exc))
        full_text = fallback
        await _emit(
            session_id,
            {"type": "error", "debater": debater.value, "message": str(exc), "fallback": fallback},
        )
        await _emit(session_id, {"type": "token", "debater": debater.value, "content": fallback})

    if not full_text.strip():
        full_text = _casual_fallback_message(debater, session.topic, "sem conteúdo")
        await _emit(session_id, {"type": "token", "debater": debater.value, "content": full_text})

    sanitized = _sanitize_response(full_text)
    clean_text, _ = extract_thinking(sanitized)
    clean_text = enforce_max_sentences(_sanitize_response(clean_text or sanitized))
    if not clean_text.strip():
        clean_text = _casual_fallback_message(debater, session.topic)

    final_text = clean_text.strip()
    speaker_gesture = analyze_speaker_gesture(final_text)

    if final_text != session.current_stream_text.strip():
        await _emit(
            session_id,
            {"type": "token_replace", "debater": debater.value, "content": final_text},
        )
    session.current_stream_text = final_text

    listener = DebaterId.POBRE if debater == DebaterId.RICO else DebaterId.RICO
    reaction = analyze_reaction(final_text, listener.value)

    turn = TurnRecord(
        id=str(uuid.uuid4()),
        debater=debater,
        phase=phase,
        round_num=turn_info.round_num,
        text=final_text,
        thinking=None,
        reaction_from_peer=reaction,
    )
    session.turns.append(turn)
    session.last_speaker = debater
    casual_state_machine.advance(session)

    await _emit(
        session_id,
        {
            "type": "reaction",
            "listener": listener.value,
            "speaker": debater.value,
            **reaction,
        },
    )
    await _emit(
        session_id,
        {
            "type": "turn_done",
            "turn": {
                "id": turn.id,
                "debater": debater.value,
                "phase": phase.value,
                "round_num": turn_info.round_num,
                "text": turn.text,
                "thinking": None,
            },
            "gesture": speaker_gesture,
            "scoreboard": {
                "buzzwords": session.scoreboard.buzzwords,
                "yellow_cards": session.scoreboard.yellow_cards,
                "applause": session.scoreboard.applause,
            },
            "is_finished": casual_state_machine.is_finished(session),
            "status": session.status.value,
        },
    )

    if not casual_state_machine.is_finished(session):
        asyncio.create_task(_auto_advance_casual(session_id))


async def _run_debate_turn(session_id: str, turn_info: Any) -> None:
    session = sessions[session_id]
    debater = turn_info.debater
    phase = turn_info.phase
    word_limits = config["debate"].get("word_limits", {})
    word_limit = word_limits.get(phase.value)
    profile_key = session.rico_profile if debater == DebaterId.RICO else session.pobre_profile

    await _emit(
        session_id,
        {
            "type": "turn_start",
            "debater": debater.value,
            "phase": phase.value,
            "round_num": turn_info.round_num,
            "gesture": "talk",
        },
    )

    messages = build_messages(
        session,
        debater,
        phase,
        word_limit,
        thinking=session.rico_thinking if debater == DebaterId.RICO else session.pobre_thinking,
    )
    thinking_enabled = session.rico_thinking if debater == DebaterId.RICO else session.pobre_thinking
    model = session.rico_model if debater == DebaterId.RICO else session.pobre_model
    generation_overrides = (
        session.rico_llm_params if debater == DebaterId.RICO else session.pobre_llm_params
    )
    session.current_stream_text = ""
    session.current_stream_thinking = ""
    full_text = ""
    full_reasoning = ""

    try:
        if debater == DebaterId.POBRE or (debater == DebaterId.RICO and thinking_enabled):
            content, reasoning = await lm_client.complete_non_stream(
                debater.value,
                messages,
                thinking=thinking_enabled,
                model=model,
                profile_key=profile_key,
                generation_overrides=generation_overrides,
            )
            if content:
                full_text = content
                session.current_stream_text = content
                await _emit(session_id, {"type": "token", "debater": debater.value, "content": content})
            else:
                full_reasoning = reasoning
                extracted = _speech_from_reasoning(reasoning)
                if extracted:
                    full_text = extracted
                    await _emit(
                        session_id, {"type": "token", "debater": debater.value, "content": extracted}
                    )
        else:
            async for chunk in lm_client.stream_completion(
                debater.value,
                messages,
                thinking=thinking_enabled,
                model=model,
                profile_key=profile_key,
                generation_overrides=generation_overrides,
            ):
                if chunk["kind"] == "content":
                    full_text += chunk["text"]
                    session.current_stream_text = full_text
                    await _emit(
                        session_id,
                        {"type": "token", "debater": debater.value, "content": chunk["text"]},
                    )
                else:
                    full_reasoning += chunk["text"]
                    session.current_stream_thinking = full_reasoning
    except Exception as exc:
        fallback = _fallback_message(debater, session.topic, str(exc))
        full_text = fallback
        await _emit(
            session_id,
            {"type": "error", "debater": debater.value, "message": str(exc), "fallback": fallback},
        )
        await _emit(session_id, {"type": "token", "debater": debater.value, "content": fallback})

    # Thinking models (LFM) may emit only reasoning during streaming if the
    # token budget is consumed before the final answer. Retry without streaming
    # first, since the non-stream `content` field carries the real reply.
    if not full_text.strip():
        try:
            content, reasoning = await lm_client.complete_non_stream(
                debater.value,
                messages,
                thinking=thinking_enabled,
                model=model,
                profile_key=profile_key,
                generation_overrides=generation_overrides,
            )
            if content.strip():
                full_text = content.strip()
                session.current_stream_text = full_text
                await _emit(session_id, {"type": "token", "debater": debater.value, "content": full_text})
            else:
                if reasoning.strip():
                    full_reasoning = reasoning
                extracted = _speech_from_reasoning(full_reasoning)
                if extracted:
                    full_text = extracted
                    await _emit(
                        session_id, {"type": "token", "debater": debater.value, "content": full_text}
                    )
        except Exception as exc:
            extracted = _speech_from_reasoning(full_reasoning) if full_reasoning.strip() else ""
            if extracted:
                full_text = extracted
                await _emit(session_id, {"type": "token", "debater": debater.value, "content": full_text})
            else:
                fallback = _fallback_message(debater, session.topic, str(exc))
                full_text = fallback
                await _emit(
                    session_id,
                    {"type": "error", "debater": debater.value, "message": str(exc), "fallback": fallback},
                )
                await _emit(session_id, {"type": "token", "debater": debater.value, "content": fallback})

    # Absolute last resort: never deliver an empty turn.
    if not full_text.strip():
        full_text = _fallback_message(debater, session.topic, "sem conteúdo")
        await _emit(session_id, {"type": "token", "debater": debater.value, "content": full_text})

    debate_cfg = config.get("debate", {})
    if (
        full_text.strip()
        and debate_cfg.get("topic_retry", True)
        and needs_topic_retry(session.topic, full_text)
    ):
        retry_messages = build_messages(
            session,
            debater,
            phase,
            word_limit,
            thinking=thinking_enabled,
            strict=True,
        )
        try:
            content, reasoning = await lm_client.complete_non_stream(
                debater.value,
                retry_messages,
                thinking=thinking_enabled,
                model=model,
                profile_key=profile_key,
                generation_overrides=generation_overrides,
            )
            candidate = content.strip() or _speech_from_reasoning(reasoning)
            if (
                candidate
                and not is_topic_echo(candidate, session.topic)
                and (
                    is_topic_echo(full_text, session.topic)
                    or topic_relevance_score(session.topic, candidate)
                    > topic_relevance_score(session.topic, full_text)
                )
            ):
                previous = full_text.strip()
                full_text = candidate
                session.current_stream_text = full_text
                if previous and previous != full_text:
                    await _emit(
                        session_id,
                        {
                            "type": "token_replace",
                            "debater": debater.value,
                            "content": full_text,
                        },
                    )
                elif not previous:
                    await _emit(
                        session_id,
                        {"type": "token", "debater": debater.value, "content": full_text},
                    )
        except Exception:
            pass

    # Retry se não referenciar o argumento do oponente
    if (
        full_text.strip()
        and debate_cfg.get("context_retry", True)
        and needs_context_retry(session, debater, full_text)
    ):
        retry_messages = build_messages(
            session,
            debater,
            phase,
            word_limit,
            thinking=thinking_enabled,
            strict=True,
        )
        try:
            content, reasoning = await lm_client.complete_non_stream(
                debater.value,
                retry_messages,
                thinking=thinking_enabled,
                model=model,
                profile_key=profile_key,
                generation_overrides=generation_overrides,
            )
            candidate = content.strip() or _speech_from_reasoning(reasoning)
            if candidate and references_opponent(candidate):
                previous = full_text.strip()
                full_text = candidate
                session.current_stream_text = full_text
                if previous and previous != full_text:
                    await _emit(
                        session_id,
                        {
                            "type": "token_replace",
                            "debater": debater.value,
                            "content": full_text,
                        },
                    )
        except Exception:
            pass

    # Sanitiza, extrai thinking e remove repetição do tema/pergunta.
    sanitized = _sanitize_response(full_text)
    clean_text, _ = extract_thinking(sanitized)
    clean_text = _sanitize_response(clean_text or sanitized)
    clean_text = strip_echoed_topic(clean_text, session.topic)
    if not clean_text.strip() or is_topic_echo(clean_text, session.topic):
        clean_text = fallback_argument(session, debater)
    thinking = None

    final_text = _ensure_min_sentences(clean_text, debater)
    speaker_gesture = analyze_speaker_gesture(final_text)

    # Como o tema pode ter sido removido após o streaming, reemite o texto
    # final limpo para a UI substituir o que foi exibido ao vivo.
    if final_text.strip() != session.current_stream_text.strip():
        await _emit(
            session_id,
            {"type": "token_replace", "debater": debater.value, "content": final_text},
        )
    session.current_stream_text = final_text

    listener = DebaterId.POBRE if debater == DebaterId.RICO else DebaterId.RICO
    reaction = analyze_reaction(final_text, listener.value)
    update_scoreboard(session.scoreboard, final_text, reaction)

    turn = TurnRecord(
        id=str(uuid.uuid4()),
        debater=debater,
        phase=phase,
        round_num=turn_info.round_num,
        text=final_text,
        thinking=thinking,
        reaction_from_peer=reaction,
    )
    session.turns.append(turn)
    session.last_speaker = debater
    state_machine.advance(session)

    await _emit(
        session_id,
        {
            "type": "reaction",
            "listener": listener.value,
            "speaker": debater.value,
            **reaction,
        },
    )
    await _emit(
        session_id,
        {
            "type": "turn_done",
            "turn": {
                "id": turn.id,
                "debater": debater.value,
                "phase": phase.value,
                "round_num": turn_info.round_num,
                "text": turn.text,
                "thinking": thinking,
            },
            "gesture": speaker_gesture,
            "scoreboard": {
                "buzzwords": session.scoreboard.buzzwords,
                "yellow_cards": session.scoreboard.yellow_cards,
                "applause": session.scoreboard.applause,
            },
            "is_finished": state_machine.is_finished(session),
            "status": session.status.value,
        },
    )


_GARBAGE_PATTERNS = [
    r"^(Assistente|Assistant|Resposta|Response|Output|Saída)\s*[:：]\s*",
    r"^(Rico|Pobre)\s*[:：]\s*",
    r"^\[.*?\]\s*[:：]?\s*",
    r"^[*_]{1,2}.*?[*_]{1,2}\s*",
    r"<\|.*?\|>",
    r"^#+\s+",
    r"```.*?```",
    r"\*\*\*+",
    r"_{3,}",
    r"={3,}",
    r"-{3,}",
]

_GARBAGE_RE = re.compile("|".join(_GARBAGE_PATTERNS), re.IGNORECASE | re.MULTILINE)


def _sanitize_response(text: str) -> str:
    """Remove artefatos de geração, prefixos indesejados e caracteres estranhos."""
    if not text:
        return ""
    
    result = text.strip()
    
    # Remove padrões de lixo conhecidos
    for _ in range(3):  # múltiplas passadas para padrões aninhados
        prev = result
        result = _GARBAGE_RE.sub("", result).strip()
        if result == prev:
            break
    
    # Remove caracteres de controle e unicode estranho
    result = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", result)
    
    # Remove repetições excessivas de pontuação
    result = re.sub(r"([.!?])\1{2,}", r"\1", result)
    result = re.sub(r"([,;:])\1+", r"\1", result)
    
    # Remove espaços múltiplos
    result = re.sub(r" {2,}", " ", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    
    # Remove aspas soltas no início/fim
    result = result.strip("\"'`")
    
    # Se começar com minúscula após limpeza, capitaliza
    if result and result[0].islower():
        result = result[0].upper() + result[1:]
    
    return result.strip()


def _count_sentences(text: str) -> int:
    parts = re.findall(r"[^.!?]+[.!?]+", text.strip())
    if parts:
        return len(parts)
    return 1 if text.strip() else 0


def _ensure_min_sentences(text: str, debater: DebaterId, minimum: int = 2) -> str:
    cleaned = text.strip()
    if not cleaned:
        return cleaned
    if _count_sentences(cleaned) >= minimum:
        return cleaned
    suffix = (
        "Isso é elementar para quem opera no mercado premium."
        if debater == DebaterId.RICO
        else "Os dados sustentam essa conclusão."
    )
    if cleaned[-1] not in ".!?":
        cleaned = f"{cleaned}."
    return f"{cleaned} {suffix}"


def _speech_from_reasoning(reasoning: str) -> str:
    """Extract a Portuguese debate reply hidden inside a thinking trace.

    Only returns clearly Portuguese candidates; English reasoning fragments are
    rejected so we never surface the model's internal monologue as the speech.
    """
    text = reasoning.strip()
    if not text:
        return ""

    # Quoted replies are the most reliable (models often draft the final answer
    # inside quotes within their reasoning).
    quotes = re.findall(r'"([^"]{20,400})"', text)
    for candidate in reversed(quotes):
        if _looks_like_speech(candidate):
            return candidate.strip()

    # Sentences ending with punctuation, scanned from the end (final answer).
    sentences = re.findall(r"[^.!?\n]{25,400}[.!?]", text)
    for candidate in reversed(sentences):
        cleaned = candidate.strip().lstrip("*- ")
        if _looks_like_speech(cleaned):
            return cleaned

    return ""


_PT_STRONG = ("ção", "ções", "ável", "ência", "mente", " é ", " não ", " uma ", " também ")
_PT_CHARS = ("ã", "õ", "é", "ê", "á", "í", "ó", "ú", "ç", "â")
_EN_MARKERS = (
    "input:", "output:", "constraint", "sentence", "checklist", "refining",
    "option a", "option b", "snobbish", "jargon", "verbose", "the user", "perhaps",
    "argue", "alternatively", "phrased", "let me", "need to", "should", "most relevant)",
    " the ", " is ", " and ", " but ", " with ", " that ",
    "usuário", "preciso garantir", "regra de", "2-4 frases", "2-4 palavras", "meta-coment",
    "o usuário quer", "já a regra",
)


def _looks_like_speech(text: str) -> bool:
    candidate = text.strip()
    if len(candidate) < 30 or candidate.startswith(("*", "-")):
        return False
    lower = candidate.lower()
    if any(m in lower for m in _EN_MARKERS):
        return False
    pt_score = sum(1 for c in _PT_CHARS if c in lower) + sum(1 for m in _PT_STRONG if m in lower)
    return pt_score >= 2


def _casual_fallback_message(debater: DebaterId, topic: str, error: str = "") -> str:
    if debater == DebaterId.RICO:
        return f"Sabe o que me irrita? {topic}. Isso é típico desse mundinho medíocre."
    return f"Olha, sobre {topic}… tenho uma opinião, mas preciso pensar melhor nisso."


def _fallback_message(debater: DebaterId, topic: str, error: str = "") -> str:
    if debater == DebaterId.RICO:
        return (
            "Estou CONTRA essa proposta — patrimônio familiar não é lucro especulativo. "
            "Quem pensa em longo prazo sabe que legado exige continuidade, não confisco."
        )
    return (
        "Estou A FAVOR de políticas que reduzam concentração sem distorcer incentivos. "
        "Herança acima de patamar crítico precisa de tributação proporcional e auditável."
    )


def _mount_static() -> None:
    if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str) -> FileResponse:
            if full_path.startswith("api/") or full_path == "health":
                raise HTTPException(status_code=404)
            index = STATIC_DIR / "index.html"
            if index.exists():
                return FileResponse(
                    index,
                    headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
                )
            raise HTTPException(status_code=404, detail="Frontend não buildado")


_mount_static()
