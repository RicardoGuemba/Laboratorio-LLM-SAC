import { useState, type KeyboardEvent } from "react";
import { SacAvatar } from "./SacAvatar";
import type { RagChunk, RoleId } from "../types";
import { ROLE_LABELS } from "../types";
import { inferAvatarMood } from "../utils/avatarMood";

interface TicketThreadProps {
  sessionId: string | null;
  complaintTitle: string;
  complaintText: string;
  responseText: string;
  liveComplaint: string;
  liveResponse: string;
  streamingRole: RoleId | null;
  category?: string | null;
  isStreaming?: boolean;
  manualDisabled?: boolean;
  onManualSubmit?: (complaint: string) => void;
}

export function TicketThread({
  sessionId,
  complaintTitle,
  complaintText,
  responseText,
  liveComplaint,
  liveResponse,
  streamingRole,
  category,
  isStreaming = false,
  manualDisabled = false,
  onManualSubmit,
}: TicketThreadProps) {
  const [draft, setDraft] = useState("");

  const displayComplaint = streamingRole === "cliente" ? liveComplaint : complaintText || liveComplaint;
  const displayResponse = streamingRole === "sac" ? liveResponse : responseText || liveResponse;
  const hasContent = Boolean(sessionId || displayComplaint || displayResponse);

  const clienteMood = inferAvatarMood(
    "cliente",
    displayComplaint,
    streamingRole === "cliente",
  );
  const sacMood = inferAvatarMood("sac", displayResponse, streamingRole === "sac");

  const submitManual = () => {
    const text = draft.trim();
    if (!text || manualDisabled || isStreaming) return;
    onManualSubmit?.(text);
    setDraft("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitManual();
    }
  };

  return (
    <div className="ticket-thread">
      <div className="ticket-header">
        <span className="ticket-id">#{sessionId?.slice(0, 8) ?? "—"}</span>
        {category && <span className="ticket-category">{category.replace(/_/g, " ")}</span>}
      </div>

      <div className="ticket-columns">
        <div className="ticket-col ticket-col--cliente">
          <div className="ticket-col__head">
            <SacAvatar role="cliente" mood={clienteMood} size={40} />
            <div>
              <span className="ticket-role">{ROLE_LABELS.cliente}</span>
              {complaintTitle && <h3 className="ticket-title">{complaintTitle}</h3>}
            </div>
          </div>
          <article className="ticket-bubble ticket-bubble--complaint">
            <div className={`ticket-body${streamingRole === "cliente" ? " streaming" : ""}`}>
              {displayComplaint ||
                (streamingRole === "cliente"
                  ? "Gerando reclamação..."
                  : hasContent
                    ? ""
                    : "Sua reclamação aparecerá aqui.")}
            </div>
          </article>
          <label className="manual-complaint">
            <span className="manual-complaint__label">Reclamação manual</span>
            <textarea
              className="manual-complaint__input"
              rows={2}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={manualDisabled || isStreaming}
              placeholder="Escreva sua reclamação… Enter envia, Shift+Enter quebra linha"
              aria-label="Reclamação manual — Enter para enviar ao SAC"
            />
          </label>
        </div>

        <div className="ticket-col ticket-col--sac">
          <div className="ticket-col__head">
            <SacAvatar role="sac" mood={sacMood} size={40} />
            <div>
              <span className="ticket-role">{ROLE_LABELS.sac}</span>
            </div>
          </div>
          <article className="ticket-bubble ticket-bubble--response">
            <div className={`ticket-body${streamingRole === "sac" ? " streaming" : ""}`}>
              {displayResponse ||
                (streamingRole === "sac" ? "Gerando resposta..." : "A resposta SAC aparecerá aqui.")}
            </div>
          </article>
        </div>
      </div>
    </div>
  );
}

interface RagContextPanelProps {
  chunks: RagChunk[];
  open: boolean;
  onToggle: () => void;
}

export function RagContextPanel({ chunks, open, onToggle }: RagContextPanelProps) {
  if (!chunks.length) return null;

  return (
    <div className="rag-panel">
      <button type="button" className="rag-panel__toggle" onClick={onToggle}>
        {open ? "Ocultar RAG" : `RAG (${chunks.length})`}
      </button>
      {open && (
        <div className="rag-panel__content">
          {chunks.map((chunk, i) => (
            <details key={`${chunk.doc_id}-${i}`} className="rag-chunk">
              <summary>
                {chunk.doc_id} — {chunk.section} ({chunk.score.toFixed(2)})
              </summary>
              <pre>{chunk.text}</pre>
            </details>
          ))}
        </div>
      )}
    </div>
  );
}
