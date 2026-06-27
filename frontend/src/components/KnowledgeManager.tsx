import { useCallback, useEffect, useState } from "react";
import type { KnowledgeFile, KnowledgeStats } from "../types";

interface KnowledgeManagerProps {
  open: boolean;
  onClose: () => void;
}

const TEMPLATE = `---
id: nova-reclamacao-01
categoria: atraso_entrega
produto: Desodorante Natural
status_reclamacao: respondido
fonte: reclame_aqui
data_reclamacao: 2026-06-27
data_resposta: 2026-06-28
tags: [entrega]
---

# Título da reclamação

## Reclamação do cliente
Descreva a reclamação do cliente aqui.

## Resposta TRUEPALEO SAC
Descreva a resposta do SAC aqui.
`;

export function KnowledgeManager({ open, onClose }: KnowledgeManagerProps) {
  const [files, setFiles] = useState<KnowledgeFile[]>([]);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [isNew, setIsNew] = useState(false);

  const reload = useCallback(async () => {
    const res = await fetch("/api/knowledge");
    const data = await res.json();
    setFiles(data.files ?? []);
    setStats(data.stats ?? null);
  }, []);

  useEffect(() => {
    if (open) reload().catch(() => setError("Falha ao carregar base"));
  }, [open, reload]);

  if (!open) return null;

  const selectFile = async (path: string) => {
    setError(null);
    setIsNew(false);
    setSelectedPath(path);
    const res = await fetch(`/api/knowledge/${path}`);
    if (!res.ok) {
      setError("Falha ao carregar arquivo");
      return;
    }
    const data = await res.json();
    setContent(data.content);
  };

  const startNew = () => {
    setIsNew(true);
    setSelectedPath("reclame_aqui/nova-reclamacao.md");
    setContent(TEMPLATE);
    setError(null);
  };

  const saveFile = async () => {
    if (!selectedPath) return;
    setSaving(true);
    setError(null);
    try {
      const method = isNew ? "POST" : "PUT";
      const url = isNew ? "/api/knowledge" : `/api/knowledge/${selectedPath}`;
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: selectedPath, content }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Erro ao salvar");
      }
      setIsNew(false);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  };

  const deleteFile = async () => {
    if (!selectedPath || isNew) return;
    if (!confirm(`Remover ${selectedPath}?`)) return;
    setSaving(true);
    try {
      const res = await fetch(`/api/knowledge/${selectedPath}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Erro ao remover");
      }
      setSelectedPath(null);
      setContent("");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao remover");
    } finally {
      setSaving(false);
    }
  };

  const reindex = async () => {
    setSaving(true);
    try {
      const res = await fetch("/api/knowledge/reindex", { method: "POST" });
      const data = await res.json();
      setStats(data);
      await reload();
    } catch {
      setError("Falha ao reindexar");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="persona-overlay" onClick={onClose}>
      <div className="knowledge-manager" onClick={(e) => e.stopPropagation()}>
        <header className="persona-editor-header">
          <div>
            <h2>Base de Conhecimento RAG</h2>
            {stats && (
              <p className="knowledge-stats">
                {stats.doc_count} docs · {stats.chunk_count} chunks
                {stats.last_indexed && ` · indexado ${new Date(stats.last_indexed).toLocaleString("pt-BR")}`}
              </p>
            )}
          </div>
          <div className="knowledge-header-actions">
            <button type="button" className="btn btn--ghost" disabled={saving} onClick={() => void reindex()}>
              Reindexar BM25
            </button>
            <button type="button" className="btn btn--ghost" onClick={onClose}>
              Fechar
            </button>
          </div>
        </header>

        {error && <div className="banner banner--error persona-error">{error}</div>}

        <div className="persona-editor-body">
          <aside className="persona-list knowledge-list">
            <button type="button" className="btn btn--ghost persona-new-btn" onClick={startNew}>
              + Novo .md
            </button>
            {files.map((f) => (
              <button
                key={f.path}
                type="button"
                className={`persona-list-item${selectedPath === f.path ? " active" : ""}`}
                onClick={() => void selectFile(f.path)}
              >
                <span className="knowledge-item-title">{f.title}</span>
                <span className={`knowledge-badge${f.valid ? " valid" : " invalid"}`}>
                  {f.valid ? "OK" : "!"}
                </span>
              </button>
            ))}
          </aside>

          <div className="persona-form knowledge-editor">
            {selectedPath ? (
              <>
                <label className="setup-field">
                  Caminho
                  <input
                    value={selectedPath}
                    disabled={!isNew}
                    onChange={(e) => setSelectedPath(e.target.value)}
                  />
                </label>
                <label className="setup-field">
                  Conteúdo Markdown
                  <textarea
                    rows={18}
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    className="knowledge-textarea"
                  />
                </label>
                <div className="persona-form-actions">
                  <button type="button" className="btn btn--primary" disabled={saving} onClick={() => void saveFile()}>
                    Salvar
                  </button>
                  {!isNew && (
                    <button type="button" className="btn btn--secondary" disabled={saving} onClick={() => void deleteFile()}>
                      Remover
                    </button>
                  )}
                </div>
              </>
            ) : (
              <p className="setup-hint">Selecione um arquivo ou crie um novo para enriquecer o RAG.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
