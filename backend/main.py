from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import load_config
from backend.llm.lmstudio import LMStudioClient
from backend.personas.persona_store import (
    delete_item,
    get_personas_config,
    load_defaults,
    save_defaults,
    save_item,
    validate_role_selection,
)
from backend.rag.loader import (
    delete_knowledge_file,
    get_knowledge_file,
    list_knowledge_files,
    save_knowledge_file,
)
from backend.rag.retriever import get_index, reindex
from backend.sac.orchestrator import run_manual_response, run_simulation
from backend.sac.session import SacSession


@asynccontextmanager
async def lifespan(app: FastAPI):
    reindex()
    yield


app = FastAPI(title="TRUEPALEO SAC Simulator", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

lm_client = LMStudioClient()
sessions: dict[str, SacSession] = {}
stream_queues: dict[str, asyncio.Queue[dict[str, Any] | None]] = {}
simulation_lock = asyncio.Lock()
running_simulations: set[str] = set()

STATIC_DIR = Path(__file__).resolve().parent / "static"


class LlmParamsPayload(BaseModel):
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=32, le=4096)


class StartSacRequest(BaseModel):
    cliente_profile: str = "cliente_irritado"
    sac_profile: str = "atendente_empatico"
    cliente_model: str | None = None
    sac_model: str | None = None
    cliente_thinking: bool = False
    sac_thinking: bool = False
    cliente_skills: list[str] = Field(default_factory=list)
    sac_skills: list[str] = Field(default_factory=list)
    cliente_llm_params: LlmParamsPayload | None = None
    sac_llm_params: LlmParamsPayload | None = None


class ManualComplaintRequest(BaseModel):
    complaint: str = Field(min_length=3, max_length=4000)
    title: str | None = Field(default=None, max_length=120)


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
    cliente: dict[str, Any]
    sac: dict[str, Any]


class KnowledgePayload(BaseModel):
    path: str = Field(min_length=5, max_length=200)
    content: str = Field(min_length=10, max_length=8192)


# --- Personas ---


@app.get("/api/personas")
async def personas_config() -> dict[str, Any]:
    return get_personas_config()


@app.put("/api/personas/defaults")
async def update_defaults(body: DefaultsPayload) -> dict[str, Any]:
    try:
        for role in ("cliente", "sac"):
            cfg = getattr(body, role)
            validate_role_selection(role, cfg.get("profile"), cfg.get("skills") or [])
        save_defaults({"cliente": body.cliente, "sac": body.sac})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return get_personas_config()


@app.post("/api/personas/{role}/profiles")
async def create_profile(role: str, body: ProfilePayload) -> dict[str, Any]:
    if role not in ("cliente", "sac"):
        raise HTTPException(status_code=400, detail="Role inválido")
    try:
        return save_item(role, "profiles", body.model_dump())  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/personas/{role}/profiles/{profile_id}")
async def update_profile(role: str, profile_id: str, body: ProfilePayload) -> dict[str, Any]:
    if role not in ("cliente", "sac"):
        raise HTTPException(status_code=400, detail="Role inválido")
    if body.id != profile_id:
        raise HTTPException(status_code=400, detail="ID do corpo deve coincidir com a URL")
    try:
        return save_item(role, "profiles", body.model_dump())  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/personas/{role}/profiles/{profile_id}")
async def remove_profile(role: str, profile_id: str) -> dict[str, str]:
    if role not in ("cliente", "sac"):
        raise HTTPException(status_code=400, detail="Role inválido")
    try:
        delete_item(role, "profiles", profile_id)  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"deleted": profile_id}


@app.post("/api/personas/{role}/skills")
async def create_skill(role: str, body: SkillPayload) -> dict[str, Any]:
    if role not in ("cliente", "sac"):
        raise HTTPException(status_code=400, detail="Role inválido")
    try:
        return save_item(role, "skills", body.model_dump())  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/personas/{role}/skills/{skill_id}")
async def update_skill(role: str, skill_id: str, body: SkillPayload) -> dict[str, Any]:
    if role not in ("cliente", "sac"):
        raise HTTPException(status_code=400, detail="Role inválido")
    if body.id != skill_id:
        raise HTTPException(status_code=400, detail="ID do corpo deve coincidir com a URL")
    try:
        return save_item(role, "skills", body.model_dump())  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/personas/{role}/skills/{skill_id}")
async def remove_skill(role: str, skill_id: str) -> dict[str, str]:
    if role not in ("cliente", "sac"):
        raise HTTPException(status_code=400, detail="Role inválido")
    try:
        delete_item(role, "skills", skill_id)  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"deleted": skill_id}


# --- Health & Models ---


@app.get("/health")
async def health() -> dict[str, Any]:
    lm_status = await lm_client.health_check()
    rag_stats = get_index().stats()
    return {
        "status": "ok",
        "lmstudio": lm_status,
        "rag": rag_stats,
        "features": {
            "manual_complaint": True,
        },
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


# --- SAC Simulation ---


@app.post("/api/sac/start")
async def start_sac(body: StartSacRequest) -> dict[str, Any]:
    defaults = load_defaults()
    cliente_skills = body.cliente_skills or defaults.get("cliente", {}).get("skills", [])
    sac_skills = body.sac_skills or defaults.get("sac", {}).get("skills", [])
    try:
        validate_role_selection("cliente", body.cliente_profile, cliente_skills)
        validate_role_selection("sac", body.sac_profile, sac_skills)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    available = await lm_client.list_models()
    try:
        cliente_model = lm_client.pick_model(body.cliente_model, "cliente_truepaleo", available)
        sac_model = lm_client.pick_model(body.sac_model, "truepaleo_sac", available)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    cliente_llm = body.cliente_llm_params.model_dump(exclude_none=True) if body.cliente_llm_params else {}
    sac_llm = body.sac_llm_params.model_dump(exclude_none=True) if body.sac_llm_params else {}

    session = SacSession.create(
        cliente_profile=body.cliente_profile,
        sac_profile=body.sac_profile,
        cliente_model=cliente_model,
        sac_model=sac_model,
        cliente_thinking=body.cliente_thinking,
        sac_thinking=body.sac_thinking,
        cliente_skills=cliente_skills,
        sac_skills=sac_skills,
        cliente_llm_params=cliente_llm,
        sac_llm_params=sac_llm,
    )
    sessions[session.id] = session
    stream_queues[session.id] = asyncio.Queue()
    return session.to_dict()


@app.get("/api/sac/{session_id}")
async def get_sac_session(session_id: str) -> dict[str, Any]:
    return _get_session(session_id).to_dict()


@app.post("/api/sac/{session_id}/simulate")
async def simulate(session_id: str) -> dict[str, Any]:
    _get_session(session_id)
    if session_id in running_simulations:
        raise HTTPException(status_code=409, detail="Simulação já em andamento")
    asyncio.create_task(_run_simulation(session_id))
    return {"started": True, "session_id": session_id}


@app.post("/api/sac/{session_id}/respond")
async def respond_manual(session_id: str, body: ManualComplaintRequest) -> dict[str, Any]:
    _get_session(session_id)
    if session_id in running_simulations:
        raise HTTPException(status_code=409, detail="Simulação já em andamento")
    asyncio.create_task(_run_manual_response(session_id, body.complaint.strip(), body.title))
    return {"started": True, "session_id": session_id, "manual": True}


@app.get("/api/sac/{session_id}/stream")
async def stream_events(session_id: str) -> StreamingResponse:
    _get_session(session_id)
    if session_id not in stream_queues:
        stream_queues[session_id] = asyncio.Queue()

    async def event_generator():
        queue = stream_queues[session_id]
        while True:
            event = await queue.get()
            if event is None:
                yield 'data: {"type": "closed"}\n\n'
                break
            yield f"data: {json.dumps(jsonable_encoder(event), ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --- Knowledge / RAG ---


@app.get("/api/knowledge")
async def knowledge_list() -> dict[str, Any]:
    return {"files": list_knowledge_files(), "stats": get_index().stats()}


@app.get("/api/knowledge/stats")
async def knowledge_stats() -> dict[str, Any]:
    return get_index().stats()


@app.get("/api/knowledge/{path:path}")
async def knowledge_get(path: str) -> dict[str, Any]:
    try:
        content = get_knowledge_file(path)
        return {"path": path, "content": content}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/knowledge")
async def knowledge_create(body: KnowledgePayload) -> dict[str, Any]:
    try:
        result = save_knowledge_file(body.path, body.content)
        reindex()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/knowledge/{path:path}")
async def knowledge_update(path: str, body: KnowledgePayload) -> dict[str, Any]:
    if body.path != path:
        raise HTTPException(status_code=400, detail="Path do corpo deve coincidir com a URL")
    try:
        result = save_knowledge_file(path, body.content)
        reindex()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/knowledge/{path:path}")
async def knowledge_delete(path: str) -> dict[str, str]:
    try:
        delete_knowledge_file(path)
        reindex()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": path}


@app.post("/api/knowledge/reindex")
async def knowledge_reindex() -> dict[str, Any]:
    return reindex()


def _get_session(session_id: str) -> SacSession:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    return sessions[session_id]


async def _emit(session_id: str, event: dict[str, Any] | None) -> None:
    if session_id in stream_queues:
        await stream_queues[session_id].put(event)


async def _run_simulation(session_id: str) -> None:
    if session_id in running_simulations:
        return
    running_simulations.add(session_id)
    try:
        async with simulation_lock:
            session = sessions[session_id]

            async def emit(event: dict[str, Any] | None) -> None:
                await _emit(session_id, event)

            await run_simulation(session, lm_client, emit)
            await _emit(session_id, None)
    except Exception as exc:
        await _emit(
            session_id,
            {"type": "error", "message": str(exc)},
        )
        await _emit(session_id, None)
    finally:
        running_simulations.discard(session_id)


async def _run_manual_response(
    session_id: str,
    complaint: str,
    title: str | None,
) -> None:
    if session_id in running_simulations:
        return
    running_simulations.add(session_id)
    try:
        async with simulation_lock:
            session = sessions[session_id]

            async def emit(event: dict[str, Any] | None) -> None:
                await _emit(session_id, event)

            await run_manual_response(session, complaint, lm_client, emit, title=title)
            await _emit(session_id, None)
    except Exception as exc:
        await _emit(
            session_id,
            {"type": "error", "message": str(exc)},
        )
        await _emit(session_id, None)
    finally:
        running_simulations.discard(session_id)


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
