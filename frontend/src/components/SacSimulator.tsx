import { useRef, useState } from "react";
import { KnowledgeManager } from "./KnowledgeManager";
import { SimulacaoSetup } from "./SimulacaoSetup";
import { RagContextPanel, TicketThread } from "./TicketThread";
import type { SacStartConfig } from "../types";

interface SacSimulatorProps {
  session: ReturnType<typeof import("../hooks/useSacStream").useSacStream>;
}

export function SacSimulator({
  session: {
    session,
    liveComplaint,
    liveResponse,
    streamingRole,
    ragChunks,
    isStreaming,
    lmOnline,
    error,
    simulate,
    respondManual,
  },
}: SacSimulatorProps) {
  const [knowledgeOpen, setKnowledgeOpen] = useState(false);
  const [ragOpen, setRagOpen] = useState(false);
  const [configReady, setConfigReady] = useState(false);
  const configRef = useRef<SacStartConfig | null>(null);

  const handleSimulate = (config: SacStartConfig) => {
    configRef.current = config;
    void simulate(config);
  };

  const handleManualSubmit = (complaint: string) => {
    const config = configRef.current;
    if (!config) return;
    void respondManual(config, complaint);
  };

  return (
    <div className="sac-app">
      <header className="sac-header">
        <div className="sac-header__brand">
          <img src="/assets/truepaleo-logo.svg" alt="TRUEPALEO" className="sac-logo" />
          <h1>Simulador SAC</h1>
        </div>
        <div className="sac-header__actions">
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => setKnowledgeOpen(true)}>
            Conhecimento
          </button>
        </div>
      </header>

      <main className="sac-main">
        <SimulacaoSetup
          onSimulate={handleSimulate}
          onConfigChange={(cfg) => {
            configRef.current = cfg;
            setConfigReady(true);
          }}
          disabled={isStreaming}
          isStreaming={isStreaming}
          lmOnline={lmOnline}
        />

        {error && <div className="banner banner--error banner--compact">{error}</div>}

        <section className="sac-workspace">
          <TicketThread
            sessionId={session?.id ?? null}
            complaintTitle={session?.complaint_title ?? ""}
            complaintText={session?.complaint_text ?? ""}
            responseText={session?.response_text ?? ""}
            liveComplaint={liveComplaint}
            liveResponse={liveResponse}
            streamingRole={streamingRole}
            category={session?.category}
            isStreaming={isStreaming}
            manualDisabled={!configReady || lmOnline === false}
            onManualSubmit={handleManualSubmit}
          />
          <RagContextPanel chunks={ragChunks} open={ragOpen} onToggle={() => setRagOpen((v) => !v)} />
        </section>
      </main>

      <KnowledgeManager open={knowledgeOpen} onClose={() => setKnowledgeOpen(false)} />
    </div>
  );
}
