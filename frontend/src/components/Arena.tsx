import { useEffect, useMemo, useState } from "react";
import { DebaterAvatar } from "./DebaterAvatar";
import { DebateSetup } from "./DebateSetup";
import { ScoreboardPanel } from "./Scoreboard";
import { SpeechFeed } from "./SpeechFeed";
import type { DebateStartConfig, DebateState, DebaterId, Gesture, PersonasConfig } from "../types";
import { PHASE_LABELS } from "../types";
import { resolveCharacterName } from "../utils/personaLabel";
import { inferSpeakerGesture } from "../utils/speakerEmotion";

interface ArenaProps {
  debate: DebateState | null;
  liveText: string;
  speakingDebater: DebaterId | null;
  speakingRound: number | null;
  speakerGesture: Partial<Record<DebaterId, Gesture>>;
  isStreaming: boolean;
  lmOnline: boolean | null;
  error: string | null;
  onStart: (config: DebateStartConfig) => Promise<void>;
  onNextTurn: () => Promise<void>;
  onEnd: () => Promise<void>;
  onNewDebate: () => Promise<void>;
}

export function Arena({
  debate,
  liveText,
  speakingDebater,
  speakingRound,
  speakerGesture,
  isStreaming,
  lmOnline,
  error,
  onStart,
  onNextTurn,
  onEnd,
  onNewDebate,
}: ArenaProps) {
  const [personas, setPersonas] = useState<PersonasConfig | null>(null);

  useEffect(() => {
    fetch("/api/personas")
      .then((r) => r.json())
      .then((data: PersonasConfig) => setPersonas(data))
      .catch(() => undefined);
  }, []);

  const isCasual = debate?.mode === "casual";
  const isFinished =
    debate?.is_finished || debate?.status === "completed" || debate?.status === "ended";
  const nextTurn = debate?.next_turn;
  const phaseLabel = nextTurn ? PHASE_LABELS[nextTurn.phase] : "";
  const lastTurnRound = debate?.turns.length
    ? debate.turns[debate.turns.length - 1].round_num
    : 0;
  const nextRound = nextTurn?.round_num ?? debate?.current_round ?? 1;
  const displayRound =
    isStreaming && speakingRound != null
      ? speakingRound
      : nextRound > lastTurnRound && lastTurnRound > 0
        ? lastTurnRound
        : nextRound || 1;

  const previousRounds = useMemo(() => {
    if (!debate) return [];
    const rounds = new Set(debate.turns.map((t) => t.round_num));
    return [...rounds].filter((r) => r < displayRound).sort((a, b) => b - a);
  }, [debate, displayRound]);

  const ricoGesture =
    speakingDebater === "rico"
      ? speakerGesture.rico ?? (liveText ? inferSpeakerGesture(liveText) : "talk")
      : undefined;
  const pobreGesture =
    speakingDebater === "pobre"
      ? speakerGesture.pobre ?? (liveText ? inferSpeakerGesture(liveText) : "talk")
      : undefined;

  const ricoCharacterName = useMemo(
    () =>
      debate
        ? resolveCharacterName(personas, "rico", debate.rico_profile, debate.rico_profile_name)
        : "",
    [debate, personas],
  );
  const pobreCharacterName = useMemo(
    () =>
      debate
        ? resolveCharacterName(personas, "pobre", debate.pobre_profile, debate.pobre_profile_name)
        : "",
    [debate, personas],
  );

  return (
    <div className="arena-layout">
      <header className="arena-topbar">
        <div className="arena-brand">
          <h1>Laboratório Personas LLM</h1>
          {debate ? (
            <p className="arena-topic-inline">
              <strong>{debate.topic}</strong>
              {isCasual ? (
                <span className="arena-badge arena-badge--phase">Conversa casual</span>
              ) : (
                <>
                  <span className="arena-badge">Ciclo {displayRound}</span>
                  {nextTurn && !isFinished && (
                    <span className="arena-badge arena-badge--phase">{phaseLabel}</span>
                  )}
                </>
              )}
            </p>
          ) : (
            <p className="arena-subtitle">Configure personas, skills e inicie o debate ou a conversa</p>
          )}
        </div>
        {debate && !isCasual && <ScoreboardPanel scoreboard={debate.scoreboard} compact />}
      </header>

      {!debate && (
        <section className="arena-setup-section">
          <DebateSetup onStart={(c) => void onStart(c)} lmOnline={lmOnline} />
        </section>
      )}

      {error && <div className="banner banner--error">{error}</div>}

      {debate && (
        <main className="arena-main">
          {previousRounds.length > 0 && !isCasual && (
            <div className="cycle-archive">
              Ciclos anteriores arquivados: {previousRounds.join(", ")}
            </div>
          )}

          <div className="arena-duel">
            <section className="duel-column duel-column--rico">
              <div className="duel-avatar-wrap">
                <DebaterAvatar
                  debater="rico"
                  isSpeaking={speakingDebater === "rico"}
                  gesture={ricoGesture}
                  position={debate.rico_position}
                  characterName={ricoCharacterName}
                  modelName={debate.rico_model}
                  compact
                />
              </div>
              <SpeechFeed
                debater="rico"
                characterName={ricoCharacterName}
                turns={debate.turns}
                currentRound={displayRound}
                liveText={speakingDebater === "rico" ? liveText : undefined}
                isSpeaking={speakingDebater === "rico"}
                isLive={isStreaming && speakingDebater === "rico"}
                showAllTurns={isCasual}
              />
            </section>

            <div className="duel-divider">
              <span>VS</span>
            </div>

            <section className="duel-column duel-column--pobre">
              <div className="duel-avatar-wrap">
                <DebaterAvatar
                  debater="pobre"
                  isSpeaking={speakingDebater === "pobre"}
                  gesture={pobreGesture}
                  position={debate.pobre_position}
                  characterName={pobreCharacterName}
                  modelName={debate.pobre_model}
                  compact
                />
              </div>
              <SpeechFeed
                debater="pobre"
                characterName={pobreCharacterName}
                turns={debate.turns}
                currentRound={displayRound}
                liveText={speakingDebater === "pobre" ? liveText : undefined}
                isSpeaking={speakingDebater === "pobre"}
                isLive={isStreaming && speakingDebater === "pobre"}
                showAllTurns={isCasual}
              />
            </section>
          </div>
        </main>
      )}

      {debate && (
        <footer className="arena-footer">
          {!isFinished && !isCasual && (
            <button
              className="btn btn--primary"
              onClick={onNextTurn}
              disabled={isStreaming}
              type="button"
            >
              {isStreaming
                ? "Falando..."
                : debate.turns.length === 0 && isStreaming
                  ? "Abrindo debate..."
                  : debate.turns.length === 0
                    ? "Começar debate"
                    : `Próximo turno (${phaseLabel})`}
            </button>
          )}
          {isCasual && !isFinished && isStreaming && (
            <span className="arena-badge">Conversando…</span>
          )}
          <button
            className="btn btn--secondary"
            onClick={onEnd}
            disabled={isStreaming && !isCasual}
            type="button"
          >
            {isCasual ? "Parar conversa" : "Encerrar"}
          </button>
          <button
            className="btn btn--ghost"
            onClick={() => void onNewDebate()}
            disabled={isStreaming && !isCasual}
            type="button"
          >
            {isCasual ? "Nova conversa" : "Novo debate"}
          </button>
          {isFinished && (
            <span className="debate-finished">{isCasual ? "Conversa encerrada" : "Debate encerrado"}</span>
          )}
        </footer>
      )}
    </div>
  );
}
