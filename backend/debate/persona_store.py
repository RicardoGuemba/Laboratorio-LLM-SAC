from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

import yaml

DebaterKey = Literal["rico", "pobre"]
Kind = Literal["profiles", "skills"]
MAX_LINES = 15

ROOT = Path(__file__).resolve().parents[2]
PERSONAS_DIR = ROOT / "personas"
DEFAULTS_PATH = PERSONAS_DIR / "defaults.yaml"

_ID_RE = re.compile(r"^[a-z0-9_]+$")


def _debater_dir(debater: DebaterKey, kind: Kind) -> Path:
    return PERSONAS_DIR / debater / kind


def _validate_id(item_id: str) -> None:
    if not _ID_RE.match(item_id):
        raise ValueError("ID deve usar apenas letras minúsculas, números e underscore")


def _count_lines(content: str) -> int:
    return len(content.strip().splitlines())


def _parse_header(lines: list[str]) -> tuple[dict[str, Any], int]:
    header: dict[str, Any] = {}
    body_start = len(lines)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# "):
            header["id"] = stripped[2:].strip()
        elif stripped.lower().startswith("nome:"):
            header["name"] = stripped.split(":", 1)[1].strip()
        elif stripped.lower().startswith("skills:"):
            raw = stripped.split(":", 1)[1]
            header["default_skills"] = [s.strip() for s in raw.split(",") if s.strip()]
        elif stripped == "---":
            body_start = i + 1
            break
    return header, body_start


def parse_profile_md(content: str) -> dict[str, Any]:
    if _count_lines(content) > MAX_LINES:
        raise ValueError(f"Perfil excede {MAX_LINES} linhas")
    lines = content.strip().splitlines()
    header, body_start = _parse_header(lines)
    body_lines = [ln.strip() for ln in lines[body_start:] if ln.strip()]
    if not header.get("id") or not header.get("name"):
        raise ValueError("Perfil requer linha # id e nome:")
    if not body_lines:
        raise ValueError("Perfil requer texto após ---")
    description = body_lines[0]
    prompt = " ".join(body_lines[1:]) if len(body_lines) > 1 else body_lines[0]
    return {
        "id": header["id"],
        "name": header["name"],
        "description": description,
        "prompt": prompt,
        "default_skills": header.get("default_skills", []),
    }


def parse_skill_md(content: str) -> dict[str, Any]:
    if _count_lines(content) > MAX_LINES:
        raise ValueError(f"Skill excede {MAX_LINES} linhas")
    lines = content.strip().splitlines()
    header, body_start = _parse_header(lines)
    body_lines = [ln.strip() for ln in lines[body_start:] if ln.strip()]
    if not header.get("id") or not header.get("name"):
        raise ValueError("Skill requer linha # id e nome:")
    if not body_lines:
        raise ValueError("Skill requer texto após ---")
    description = body_lines[0]
    prompt = " ".join(body_lines[1:]) if len(body_lines) > 1 else body_lines[0]
    return {
        "id": header["id"],
        "name": header["name"],
        "description": description,
        "prompt": prompt,
    }


def render_profile_md(data: dict[str, Any]) -> str:
    _validate_id(data["id"])
    skills = data.get("default_skills") or []
    desc = data["description"].strip()
    prompt = (data.get("prompt") or desc).strip()
    lines = [
        f"# {data['id']}",
        f"nome: {data['name']}",
    ]
    if skills:
        lines.append(f"skills: {', '.join(skills)}")
    lines.append("---")
    lines.append(desc)
    if prompt != desc:
        lines.append(prompt)
    content = "\n".join(lines).strip() + "\n"
    if _count_lines(content) > MAX_LINES:
        raise ValueError(f"Perfil excede {MAX_LINES} linhas")
    return content


def render_skill_md(data: dict[str, Any]) -> str:
    _validate_id(data["id"])
    desc = data["description"].strip()
    prompt = data.get("prompt", desc).strip()
    lines = [
        f"# {data['id']}",
        f"nome: {data['name']}",
        "---",
        desc,
    ]
    if prompt != desc:
        lines.append(prompt)
    content = "\n".join(lines).strip() + "\n"
    if _count_lines(content) > MAX_LINES:
        raise ValueError(f"Skill excede {MAX_LINES} linhas")
    return content


def _load_kind(debater: DebaterKey, kind: Kind) -> dict[str, dict[str, Any]]:
    directory = _debater_dir(debater, kind)
    directory.mkdir(parents=True, exist_ok=True)
    parser = parse_profile_md if kind == "profiles" else parse_skill_md
    items: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.md")):
        try:
            item = parser(path.read_text(encoding="utf-8"))
            items[item["id"]] = item
        except ValueError:
            continue
    return items


def load_debater(debater: DebaterKey) -> dict[str, Any]:
    return {
        "profiles": _load_kind(debater, "profiles"),
        "skills": _load_kind(debater, "skills"),
    }


def load_defaults() -> dict[str, Any]:
    if not DEFAULTS_PATH.exists():
        return {
            "rico": {"profile": "herdeiro", "skills": ["jargao_premium"]},
            "pobre": {"profile": "doutor", "skills": ["reducao_dimensional"]},
        }
    data = yaml.safe_load(DEFAULTS_PATH.read_text(encoding="utf-8")) or {}
    return data


def save_defaults(defaults: dict[str, Any]) -> None:
    PERSONAS_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULTS_PATH.write_text(
        yaml.dump(defaults, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


def get_personas_config() -> dict[str, Any]:
    defaults = load_defaults()
    result: dict[str, Any] = {"defaults": defaults}
    for debater in ("rico", "pobre"):
        data = load_debater(debater)
        result[debater] = data
    return result


def validate_debate_selection(
    debater: DebaterKey,
    profile_id: str,
    skill_ids: list[str],
) -> None:
    data = load_debater(debater)
    if profile_id not in data["profiles"]:
        raise ValueError(f"Perfil '{profile_id}' não existe para {debater}")
    profile = data["profiles"][profile_id]
    has_profile_prompt = bool((profile.get("prompt") or profile.get("description") or "").strip())
    if not skill_ids and not has_profile_prompt:
        raise ValueError(f"Selecione ao menos uma skill ou defina prompt no perfil para {debater}")
    for sid in skill_ids:
        if sid not in data["skills"]:
            raise ValueError(f"Skill '{sid}' não existe para {debater}")


def save_item(debater: DebaterKey, kind: Kind, data: dict[str, Any]) -> dict[str, Any]:
    _validate_id(data["id"])
    directory = _debater_dir(debater, kind)
    directory.mkdir(parents=True, exist_ok=True)
    if kind == "profiles":
        skill_catalog = _load_kind(debater, "skills")
        for sid in data.get("default_skills", []):
            if sid not in skill_catalog:
                raise ValueError(f"Skill padrão '{sid}' não existe")
        content = render_profile_md(data)
        parsed = parse_profile_md(content)
    else:
        content = render_skill_md(data)
        parsed = parse_skill_md(content)
    path = directory / f"{data['id']}.md"
    path.write_text(content, encoding="utf-8")
    return parsed


def delete_item(debater: DebaterKey, kind: Kind, item_id: str) -> None:
    directory = _debater_dir(debater, kind)
    items = _load_kind(debater, kind)
    if item_id not in items:
        raise ValueError(f"Item '{item_id}' não encontrado")
    if len(items) <= 1:
        raise ValueError(f"Não é possível remover o único {kind[:-1]} de {debater}")
    defaults = load_defaults()
    deb_defaults = defaults.get(debater, {})
    if kind == "profiles" and deb_defaults.get("profile") == item_id:
        raise ValueError("Não é possível remover o perfil padrão; altere defaults primeiro")
    if kind == "skills" and item_id in (deb_defaults.get("skills") or []):
        raise ValueError("Não é possível remover skill usada como padrão")
    path = directory / f"{item_id}.md"
    if path.exists():
        path.unlink()


def get_profile(debater: DebaterKey, profile_id: str) -> dict[str, Any]:
    profiles = _load_kind(debater, "profiles")
    if profile_id not in profiles:
        profile_id = load_defaults().get(debater, {}).get("profile", profile_id)
    return profiles.get(profile_id, next(iter(profiles.values()), {}))


def get_skills(debater: DebaterKey, skill_ids: list[str]) -> list[dict[str, Any]]:
    catalog = _load_kind(debater, "skills")
    return [catalog[sid] for sid in skill_ids if sid in catalog]
