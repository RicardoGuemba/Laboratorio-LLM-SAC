import type { DebaterId, TurnRecord } from "../types";

interface SpeechFeedProps {
  debater: DebaterId;
  characterName?: string;
  turns: TurnRecord[];
  currentRound: number;
  liveText?: string;
  isSpeaking: boolean;
  isLive: boolean;
  showAllTurns?: boolean;
}

export function SpeechFeed({
  debater,
  characterName,
  turns,
  currentRound,
  liveText,
  isSpeaking,
  isLive,
  showAllTurns = false,
}: SpeechFeedProps) {
  const cycleTurns = showAllTurns
    ? turns.filter((t) => t.debater === debater)
    : turns.filter((t) => t.debater === debater && t.round_num === currentRound);

  return (
    <div className={`speech-feed speech-feed--${debater}`}>
      {characterName && (
        <div className="speech-feed-header">
          <span className="speech-feed-title">{characterName}</span>
        </div>
      )}
      <div className="speech-feed-list">
        {cycleTurns.length === 0 && !isSpeaking && (
          <p className="speech-feed-empty">Aguardando fala neste ciclo...</p>
        )}

        {cycleTurns.map((turn) => (
          <article key={turn.id} className="speech-card">
            <p className="speech-card-text">{turn.text}</p>
          </article>
        ))}

        {isSpeaking && (
          <article className={`speech-card speech-card--live${isLive ? " is-streaming" : ""}`}>
            <p className="speech-card-text">
              {liveText || "..."}
              {isLive && <span className="cursor-blink">|</span>}
            </p>
          </article>
        )}
      </div>
    </div>
  );
}
