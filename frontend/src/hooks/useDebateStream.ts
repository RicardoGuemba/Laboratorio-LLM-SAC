import { useCallback, useEffect, useRef, useState } from "react";
import type {
  DebateStartConfig,
  DebateState,
  DebaterId,
  Gesture,
  LlmParams,
  Scoreboard,
  StreamEvent,
  TurnRecord,
} from "../types";
import { saveLastModels, saveLastSession, saveLastTopic } from "../utils/debatePrefs";
import { inferSpeakerGesture } from "../utils/speakerEmotion";

interface UseDebateStreamResult {
  debate: DebateState | null;
  liveText: string;
  speakingDebater: DebaterId | null;
  speakingRound: number | null;
  speakerGesture: Partial<Record<DebaterId, Gesture>>;
  isStreaming: boolean;
  lmOnline: boolean | null;
  error: string | null;
  startDebate: (config: DebateStartConfig) => Promise<void>;
  nextTurn: () => Promise<void>;
  endDebate: () => Promise<void>;
  newDebate: () => Promise<void>;
  refreshHealth: () => Promise<void>;
}

function buildLlmPayload(params: LlmParams) {
  const payload: Record<string, number> = {};
  if (params.temperature != null) payload.temperature = params.temperature;
  if (params.top_p != null) payload.top_p = params.top_p;
  if (params.max_tokens != null) payload.max_tokens = params.max_tokens;
  return Object.keys(payload).length ? payload : undefined;
}

export function useDebateStream(): UseDebateStreamResult {
  const [debate, setDebate] = useState<DebateState | null>(null);
  const [liveText, setLiveText] = useState("");
  const [speakingDebater, setSpeakingDebater] = useState<DebaterId | null>(null);
  const [speakingRound, setSpeakingRound] = useState<number | null>(null);
  const [speakerGesture, setSpeakerGesture] = useState<Partial<Record<DebaterId, Gesture>>>({});
  const [isStreaming, setIsStreaming] = useState(false);
  const [lmOnline, setLmOnline] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const debateIdRef = useRef<string | null>(null);

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
      const es = new EventSource(`/api/debate/${sessionId}/stream`);
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
        return;
      }

      switch (event.type) {
        case "turn_start":
          setIsStreaming(true);
          setLiveText("");
          setSpeakingDebater(event.debater ?? null);
          setSpeakingRound(event.round_num ?? null);
          if (event.debater) {
            setSpeakerGesture({ [event.debater]: event.gesture ?? "talk" });
          }
          break;

        case "token":
          if (event.content) {
            setLiveText((prev) => {
              const next = prev + event.content;
              if (event.debater) {
                setSpeakerGesture((g) => ({
                  ...g,
                  [event.debater!]: inferSpeakerGesture(next),
                }));
              }
              return next;
            });
          }
          break;

        case "token_replace":
          if (event.content) {
            setLiveText(event.content);
            if (event.debater) {
              setSpeakerGesture((g) => ({
                ...g,
                [event.debater!]: inferSpeakerGesture(event.content!),
              }));
            }
          }
          break;

        case "turn_done":
          setIsStreaming(false);
          if (event.turn?.debater && event.gesture) {
            setSpeakerGesture((g) => ({
              ...g,
              [event.turn!.debater]: event.gesture!,
            }));
          }
          setSpeakingDebater(null);
          setSpeakingRound(null);
          if (event.turn && event.scoreboard) {
            setDebate((prev) => {
              if (!prev) return prev;
              return {
                ...prev,
                turns: [...prev.turns, event.turn as TurnRecord],
                scoreboard: event.scoreboard as Scoreboard,
                current_round: event.turn?.round_num ?? prev.current_round,
                is_finished: event.is_finished,
                status: event.is_finished ? "completed" : prev.status,
              };
            });
          }
          setLiveText("");
          fetch(`/api/debate/${sessionId}`)
            .then((r) => r.json())
            .then((data) => setDebate(data))
            .catch(() => undefined);
          break;

        case "error":
          setError(event.message ?? "Erro no turno");
          setIsStreaming(false);
          break;

        case "debate_ended":
          setDebate((prev) => (prev ? { ...prev, status: "ended", is_finished: true } : prev));
          break;
      }
    };

    es.onerror = () => {
      if (!settled) {
        settled = true;
        reject(new Error("Falha ao conectar ao stream da sessão"));
      }
    };
  });
  }, []);

  const startDebate = useCallback(
    async (config: DebateStartConfig) => {
      setError(null);
      try {
        const res = await fetch("/api/debate/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            mode: config.mode,
            topic: config.mode === "casual" ? undefined : config.topic,
            rico_profile: config.ricoProfile,
            pobre_profile: config.pobreProfile,
            rico_model: config.ricoModel,
            pobre_model: config.pobreModel,
            rico_thinking: config.ricoThinking,
            pobre_thinking: config.pobreThinking,
            rico_skills: config.ricoSkills,
            pobre_skills: config.pobreSkills,
            rico_llm_params: buildLlmPayload(config.ricoLlmParams),
            pobre_llm_params: buildLlmPayload(config.pobreLlmParams),
          }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(typeof err.detail === "string" ? err.detail : "Falha ao iniciar debate");
        }
        const data: DebateState = await res.json();
        if (config.mode === "debate") {
          saveLastTopic(config.topic);
        }
        saveLastSession({
          ricoModel: config.ricoModel,
          pobreModel: config.pobreModel,
          ricoProfile: config.ricoProfile,
          pobreProfile: config.pobreProfile,
          ricoSkills: config.ricoSkills,
          pobreSkills: config.pobreSkills,
          ricoLlmParams: config.ricoLlmParams,
          pobreLlmParams: config.pobreLlmParams,
        });
        setDebate(data);
        debateIdRef.current = data.id;
        await connectStream(data.id);
        if (config.mode === "debate") {
          const nextRes = await fetch(`/api/debate/${data.id}/next`, { method: "POST" });
          if (!nextRes.ok) {
            const err = await nextRes.json().catch(() => ({}));
            throw new Error(typeof err.detail === "string" ? err.detail : "Falha ao iniciar primeiro turno");
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Falha ao iniciar debate");
      }
    },
    [connectStream],
  );

  const nextTurn = useCallback(async () => {
    if (!debate?.id) return;
    setError(null);
    const res = await fetch(`/api/debate/${debate.id}/next`, { method: "POST" });
    if (!res.ok) {
      const err = await res.json();
      setError(err.detail ?? "Erro ao avançar turno");
    }
  }, [debate?.id]);

  const endDebate = useCallback(async () => {
    if (!debate?.id) return;
    await fetch(`/api/debate/${debate.id}/end`, { method: "POST" });
    eventSourceRef.current?.close();
    setDebate((prev) => (prev ? { ...prev, status: "ended", is_finished: true } : prev));
  }, [debate?.id]);

  const newDebate = useCallback(async () => {
    setError(null);
    if (debate?.topic) {
      saveLastTopic(debate.topic);
    }
    if (debate?.rico_model && debate?.pobre_model) {
      saveLastModels(debate.rico_model, debate.pobre_model);
    }
    if (debate?.id && debate.status !== "ended" && !debate.is_finished) {
      try {
        await fetch(`/api/debate/${debate.id}/end`, { method: "POST" });
      } catch {
        /* segue para tela inicial mesmo se falhar */
      }
    }
    eventSourceRef.current?.close();
    debateIdRef.current = null;
    setDebate(null);
    setLiveText("");
    setSpeakingDebater(null);
    setSpeakingRound(null);
    setSpeakerGesture({});
    setIsStreaming(false);
  }, [debate?.id, debate?.status, debate?.is_finished, debate?.topic, debate?.rico_model, debate?.pobre_model]);

  useEffect(() => {
    return () => eventSourceRef.current?.close();
  }, []);

  return {
    debate,
    liveText,
    speakingDebater,
    speakingRound,
    speakerGesture,
    isStreaming,
    lmOnline,
    error,
    startDebate,
    nextTurn,
    endDebate,
    newDebate,
    refreshHealth,
  };
}
