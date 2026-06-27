from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = ROOT / "knowledge"
RECLAME_AQUI_DIR = KNOWLEDGE_DIR / "reclame_aqui"
POLICIES_DIR = KNOWLEDGE_DIR / "policies"

REQUIRED_FRONTMATTER = ("id", "categoria")
REQUIRED_SECTIONS = ("Reclamação do cliente", "Resposta TRUEPALEO SAC")


@dataclass
class KnowledgeDocument:
    doc_id: str
    path: Path
    metadata: dict[str, Any]
    title: str
    complaint: str
    response: str
    raw_content: str


@dataclass
class Chunk:
    doc_id: str
    section: str
    text: str
    metadata: dict[str, Any]


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    if not content.startswith("---"):
        return {}, content
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}, content
    meta = yaml.safe_load(match.group(1)) or {}
    body = content[match.end() :]
    return meta, body


def _extract_section(body: str, heading: str) -> str:
    pattern = rf"##\s*{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _extract_title(body: str) -> str:
    match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    return match.group(1).strip() if match else ""


def load_document(path: Path) -> KnowledgeDocument:
    content = path.read_text(encoding="utf-8")
    metadata, body = _parse_frontmatter(content)
    doc_id = str(metadata.get("id") or path.stem)
    return KnowledgeDocument(
        doc_id=doc_id,
        path=path,
        metadata=metadata,
        title=_extract_title(body) or doc_id,
        complaint=_extract_section(body, "Reclamação do cliente"),
        response=_extract_section(body, "Resposta TRUEPALEO SAC"),
        raw_content=content,
    )


def load_all_documents() -> list[KnowledgeDocument]:
    docs: list[KnowledgeDocument] = []
    for directory in (RECLAME_AQUI_DIR, POLICIES_DIR):
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            if path.name.startswith("_"):
                continue
            try:
                docs.append(load_document(path))
            except Exception:
                continue
    return docs


def document_to_chunks(doc: KnowledgeDocument) -> list[Chunk]:
    chunks: list[Chunk] = []
    if doc.complaint:
        chunks.append(
            Chunk(
                doc_id=doc.doc_id,
                section="reclamacao",
                text=f"{doc.title}\n{doc.complaint}",
                metadata={**doc.metadata, "section": "reclamacao"},
            )
        )
    if doc.response:
        chunks.append(
            Chunk(
                doc_id=doc.doc_id,
                section="resposta",
                text=f"{doc.title}\n{doc.response}",
                metadata={**doc.metadata, "section": "resposta"},
            )
        )
    if not chunks and doc.raw_content:
        chunks.append(
            Chunk(
                doc_id=doc.doc_id,
                section="full",
                text=doc.raw_content[:2000],
                metadata={**doc.metadata, "section": "full"},
            )
        )
    return chunks


def validate_knowledge_content(content: str, *, policy_mode: bool = False) -> list[str]:
    errors: list[str] = []
    if len(content.encode("utf-8")) > 8192:
        errors.append("Arquivo excede 8 KB")
    metadata, body = _parse_frontmatter(content)
    for field in REQUIRED_FRONTMATTER:
        if not metadata.get(field):
            errors.append(f"Frontmatter obrigatório ausente: {field}")
    is_policy = policy_mode or metadata.get("tipo") == "policy"
    if is_policy:
        if not _extract_title(body) and not body.strip():
            errors.append("Documento de política requer conteúdo")
        return errors
    for section in REQUIRED_SECTIONS:
        if not _extract_section(body, section):
            errors.append(f"Seção obrigatória ausente: ## {section}")
    return errors


def list_knowledge_files() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for directory in (RECLAME_AQUI_DIR, POLICIES_DIR):
        if not directory.exists():
            continue
        rel_dir = directory.relative_to(KNOWLEDGE_DIR)
        for path in sorted(directory.glob("*.md")):
            if path.name.startswith("_"):
                continue
            try:
                doc = load_document(path)
                errors = validate_knowledge_content(doc.raw_content)
                result.append(
                    {
                        "id": doc.doc_id,
                        "path": str(path.relative_to(KNOWLEDGE_DIR)),
                        "directory": str(rel_dir),
                        "title": doc.title,
                        "metadata": doc.metadata,
                        "valid": len(errors) == 0,
                        "errors": errors,
                        "size_bytes": path.stat().st_size,
                    }
                )
            except Exception as exc:
                result.append(
                    {
                        "id": path.stem,
                        "path": str(path.relative_to(KNOWLEDGE_DIR)),
                        "directory": str(rel_dir),
                        "title": path.stem,
                        "metadata": {},
                        "valid": False,
                        "errors": [str(exc)],
                        "size_bytes": path.stat().st_size,
                    }
                )
    return result


def get_knowledge_file(relative_path: str) -> str:
    path = KNOWLEDGE_DIR / relative_path
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {relative_path}")
    if path.suffix != ".md":
        raise ValueError("Apenas arquivos .md são permitidos")
    return path.read_text(encoding="utf-8")


def save_knowledge_file(relative_path: str, content: str) -> dict[str, Any]:
    policy_mode = relative_path.startswith("policies/")
    errors = validate_knowledge_content(content, policy_mode=policy_mode)
    if errors:
        raise ValueError("; ".join(errors))
    path = KNOWLEDGE_DIR / relative_path
    if path.suffix != ".md":
        raise ValueError("Apenas arquivos .md são permitidos")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    doc = load_document(path)
    return {
        "id": doc.doc_id,
        "path": relative_path,
        "title": doc.title,
        "metadata": doc.metadata,
        "valid": True,
        "errors": [],
    }


def delete_knowledge_file(relative_path: str) -> None:
    path = KNOWLEDGE_DIR / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {relative_path}")
    path.unlink()
