import { useCallback, useEffect, useRef, useState } from "react";
import type {
  RagChunk,
  RoleId,
  SacSession,
  SacStartConfig,
  StreamEvent,
} from "../types";
import { buildLlmPayload, saveLastModels, saveLastSession } from "../utils/sacPrefs";
import { readApiError } from "../utils/apiError";

interface UseSacStreamResult {
  session: SacSession | null;
  liveComplaint: string;
  liveResponse: string;
  streamingRole: RoleId | null;
  ragChunks: RagChunk[];
  isStreaming: boolean;
  lmOnline: boolean | null;
  error: string | null;
  startSession: (config: SacStartConfig) => Promise<void>;
  simulate: (config?: SacStartConfig) => Promise<void>;
  respondManual: (config: SacStartConfig, complaint: string) => Promise<void>;
  refreshHealth: () => Promise<void>;
}

export function useSacStream(): UseSacStreamResult {
  const [session, setSession] = useState<SacSession | null>(null);
  const [liveComplaint, setLiveComplaint] = useState("");
  const [liveResponse, setLiveResponse] = useState("");
  const [streamingRole, setStreamingRole] = useState<RoleId | null>(null);
  const [ragChunks, setRagChunks] = useState<RagChunk[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [lmOnline, setLmOnline] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const sessionIdRef = useRef<string | null>(null);

  const refreshHealth = useCallback(async () => {
    try {
      const res = await fetch("/health");
      const data = await res.json();
      setLmOnline(data.lmstudio?.online ?? false);
    } catch {
      setLmOnline(false);
    }
  }, []);

  useEffect(() => {
    refreshHealth();
  }, [refreshHealth]);

  const connectStream = useCallback((sessionId: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      eventSourceRef.current?.close();
      const es = new EventSource(`/api/sac/${sessionId}/stream`);
      eventSourceRef.current = es;
      let settled = false;

      es.onopen = () => {
        if (!settled) {
          settled = true;
          resolve();
        }
      };

      es.onmessage = (msg) => {
        const event: StreamEvent = JSON.parse(msg.data);
        if (event.type === "closed") {
          es.close();
          eventSourceRef.current = null;
          setIsStreaming(false);
          setStreamingRole(null);
          return;
        }

        switch (event.type) {
          case "complaint_start":
            setIsStreaming(true);
            setLiveResponse("");
            setRagChunks([]);
            if (event.manual) {
              setStreamingRole(null);
            } else {
              setStreamingRole("cliente");
              setLiveComplaint("");
            }
            if (event.category && event.session) {
              setSession(event.session);
            }
            break;
          case "token":
            if (event.role === "cliente" && event.content) {
              setLiveComplaint((prev) => prev + event.content);
            } else if (event.role === "sac" && event.content) {
              setLiveResponse((prev) => prev + event.content);
            }
            break;
          case "token_replace":
            if (event.role === "cliente" && event.content) {
              setLiveComplaint(event.content);
            } else if (event.role === "sac" && event.content) {
              setLiveResponse(event.content);
            }
            break;
          case "complaint_done":
            if (event.turn?.text) setLiveComplaint(event.turn.text);
            if (event.session) setSession(event.session);
            break;
          case "rag_context":
            if (event.chunks) setRagChunks(event.chunks);
            break;
          case "response_start":
            setStreamingRole("sac");
            setLiveResponse("");
            break;
          case "response_done":
            if (event.turn?.text) setLiveResponse(event.turn.text);
            if (event.session) setSession(event.session);
            setIsStreaming(false);
            setStreamingRole(null);
            break;
          case "error":
            setError(event.message ?? "Erro na simulação");
            setIsStreaming(false);
            setStreamingRole(null);
            if (event.fallback && event.role === "cliente") {
              setLiveComplaint(event.fallback);
            } else if (event.fallback && event.role === "sac") {
              setLiveResponse(event.fallback);
            }
            break;
        }
      };

      es.onerror = () => {
        if (!settled) {
          settled = true;
          reject(new Error("Falha na conexão SSE"));
        }
      };
    });
  }, []);

  const startSession = useCallback(
    async (config: SacStartConfig) => {
      setError(null);
      eventSourceRef.current?.close();
      eventSourceRef.current = null;

      const body = {
        cliente_profile: config.clienteProfile,
        sac_profile: config.sacProfile,
        cliente_model: config.clienteModel || undefined,
        sac_model: config.sacModel || undefined,
        cliente_thinking: config.clienteThinking,
        sac_thinking: config.sacThinking,
        cliente_skills: config.clienteSkills,
        sac_skills: config.sacSkills,
        cliente_llm_params: buildLlmPayload(config.clienteLlmParams),
        sac_llm_params: buildLlmPayload(config.sacLlmParams),
      };

      const res = await fetch("/api/sac/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        throw new Error(await readApiError(res, "Falha ao iniciar sessão"));
      }

      const data: SacSession = await res.json();
      sessionIdRef.current = data.id;
      setSession(data);
      setLiveComplaint("");
      setLiveResponse("");
      setRagChunks([]);
      saveLastSession(config);
      saveLastModels(config.clienteModel, config.sacModel);
      await connectStream(data.id);
    },
    [connectStream],
  );

  const simulate = useCallback(
    async (config?: SacStartConfig) => {
      setError(null);

      try {
        if (!config) {
          setError("Configure os modelos antes de simular");
          return;
        }

        await startSession(config);

        const sessionId = sessionIdRef.current;
        if (!sessionId) return;

        setIsStreaming(true);
        await connectStream(sessionId);

        const res = await fetch(`/api/sac/${sessionId}/simulate`, { method: "POST" });
        if (!res.ok) {
          throw new Error(await readApiError(res, "Falha ao iniciar simulação"));
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erro na simulação");
        setIsStreaming(false);
      }
    },
    [connectStream, startSession],
  );

  const respondManual = useCallback(
    async (config: SacStartConfig, complaint: string) => {
      const text = complaint.trim();
      if (!text) {
        setError("Escreva uma reclamação antes de enviar");
        return;
      }

      setError(null);

      try {
        await startSession(config);

        const sessionId = sessionIdRef.current;
        if (!sessionId) return;

        setIsStreaming(true);
        setStreamingRole(null);
        setLiveComplaint(text);
        setLiveResponse("");

        const res = await fetch(`/api/sac/${sessionId}/respond`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ complaint: text }),
        });
        if (!res.ok) {
          throw new Error(await readApiError(res, "Falha ao enviar reclamação"));
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erro na resposta SAC");
        setIsStreaming(false);
      }
    },
    [connectStream, startSession],
  );

  useEffect(() => {
    return () => eventSourceRef.current?.close();
  }, []);

  return {
    session,
    liveComplaint,
    liveResponse,
    streamingRole,
    ragChunks,
    isStreaming,
    lmOnline,
    error,
    startSession,
    simulate,
    respondManual,
    refreshHealth,
  };
}
