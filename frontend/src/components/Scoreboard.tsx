import type { Scoreboard } from "../types";

interface ScoreboardProps {
  scoreboard: Scoreboard;
  compact?: boolean;
}

export function ScoreboardPanel({ scoreboard, compact }: ScoreboardProps) {
  return (
    <div className={`scoreboard${compact ? " scoreboard--compact" : ""}`}>
      <div className="scoreboard-item">
        <span className="scoreboard-label">Buzzwords</span>
        <span className="scoreboard-value scoreboard-value--buzz">{scoreboard.buzzwords}</span>
      </div>
      <div className="scoreboard-item">
        <span className="scoreboard-label">Cartões</span>
        <span className="scoreboard-value scoreboard-value--cards">{scoreboard.yellow_cards}</span>
      </div>
      <div className="scoreboard-item scoreboard-item--applause">
        <span className="scoreboard-label">Aplausos</span>
        <div className="applause-bar">
          <div className="applause-fill" style={{ width: `${scoreboard.applause}%` }} />
        </div>
        <span className="scoreboard-value">{scoreboard.applause}%</span>
      </div>
    </div>
  );
}
