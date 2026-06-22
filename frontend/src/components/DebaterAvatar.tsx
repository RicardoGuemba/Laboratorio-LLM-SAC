import type { Gesture } from "../types";
import { formatModelLabel } from "../utils/modelLabel";

interface DebaterAvatarProps {
  debater: "rico" | "pobre";
  isSpeaking: boolean;
  gesture?: Gesture;
  position: string;
  characterName?: string;
  modelName?: string;
  compact?: boolean;
}

function resolveSpeakingGesture(gesture?: Gesture): Gesture {
  if (!gesture || gesture === "talk") return "talk";
  const legacy: Partial<Record<Gesture, Gesture>> = {
    nod: "alegria",
    head_shake: "rejeicao",
    facepalm: "rejeicao",
    raised_brow: "deboche",
    confused: "rejeicao",
    slow_blink: "shrug",
  };
  return legacy[gesture] ?? gesture;
}

export function DebaterAvatar({
  debater,
  isSpeaking,
  gesture,
  position,
  characterName,
  modelName,
  compact,
}: DebaterAvatarProps) {
  const activeGesture = isSpeaking ? resolveSpeakingGesture(gesture) : undefined;
  const isRico = debater === "rico";
  const displayName = characterName?.trim() || "…";
  const modelLabel = modelName ? formatModelLabel(modelName) : "";
  const title = modelName ? `${displayName} · ${modelName}` : displayName;

  return (
    <div className={`avatar-stage avatar-stage--${debater}${compact ? " avatar-stage--compact" : ""}`}>
      <div className="avatar-platform" />
      <div className={`avatar-spotlight${isSpeaking ? " avatar-spotlight--on" : ""}`} />
      <div
        className={`avatar-wrapper${isSpeaking ? ` gesture-${activeGesture ?? "talk"}` : " avatar-wrapper--idle"}`}
      >
        {isRico ? <RicoLionSvg isSpeaking={isSpeaking} /> : <PobreFoxSvg isSpeaking={isSpeaking} />}
      </div>
      <div className="avatar-meta">
        <h3 title={title}>{displayName}</h3>
        {modelLabel && (
          <span className="avatar-model" title={modelName}>
            {modelLabel}
          </span>
        )}
        <span className="avatar-position">
          {position === "casual" ? "PAPO" : position === "a_favor" ? "A FAVOR" : "CONTRA"}
        </span>
      </div>
    </div>
  );
}

function RicoLionSvg({ isSpeaking }: { isSpeaking: boolean }) {
  return (
    <svg viewBox="0 0 200 240" className="avatar-svg avatar-svg--rico" aria-hidden="true">
      <defs>
        <linearGradient id="ricoGold" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#F5D76E" />
          <stop offset="100%" stopColor="#B8860B" />
        </linearGradient>
        <linearGradient id="ricoMane" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#FFD700" />
          <stop offset="100%" stopColor="#8B6914" />
        </linearGradient>
      </defs>

      <polygon className="mane mane-1" points="100,20 60,70 100,55" fill="url(#ricoMane)" />
      <polygon className="mane mane-2" points="100,15 140,70 100,55" fill="url(#ricoMane)" />
      <polygon className="mane mane-3" points="100,10 75,65 125,65" fill="#DAA520" opacity="0.8" />

      <polygon className="ear ear-l" points="65,55 55,35 80,48" fill="#B8860B" />
      <polygon className="ear ear-r" points="135,55 145,35 120,48" fill="#B8860B" />

      <polygon className="head" points="100,50 130,75 120,110 80,110 70,75" fill="url(#ricoGold)" stroke="#1a1a2e" strokeWidth="2" />

      <polygon className="eye eye-l" points="85,78 90,83 85,88 80,83" fill="#1a1a2e" />
      <polygon className="eye eye-r" points="115,78 120,83 115,88 110,83" fill="#1a1a2e" />
      <line className="eye-spark eye-spark-l" x1="82" y1="76" x2="88" y2="82" stroke="#fff" strokeWidth="1.5" opacity="0" />
      <line className="eye-spark eye-spark-r" x1="118" y1="76" x2="112" y2="82" stroke="#fff" strokeWidth="1.5" opacity="0" />

      <rect
        className={`mouth mouth-default ${isSpeaking ? "mouth--open" : ""}`}
        x="92"
        y="95"
        width="16"
        height={isSpeaking ? "10" : "4"}
        rx="2"
        fill="#1a1a2e"
      />
      <path className="mouth mouth-smirk" d="M 91 99 Q 100 104 111 97" fill="none" stroke="#1a1a2e" strokeWidth="2.2" strokeLinecap="round" />
      <path className="mouth mouth-smile" d="M 91 98 Q 100 107 109 98" fill="none" stroke="#1a1a2e" strokeWidth="2.2" strokeLinecap="round" />
      <path className="mouth mouth-frown" d="M 91 103 Q 100 95 109 103" fill="none" stroke="#1a1a2e" strokeWidth="2.2" strokeLinecap="round" />

      <polygon className="body" points="100,115 145,140 130,195 70,195 55,140" fill="url(#ricoGold)" stroke="#1a1a2e" strokeWidth="2" />

      <rect className="tie-top" x="95" y="115" width="10" height="8" fill="#8B0000" />
      <polygon className="tie" points="100,123 110,160 100,175 90,160" fill="#CC0000" />

      <rect className="arm arm-l" x="48" y="130" width="18" height="50" rx="4" fill="#B8860B" transform="rotate(-15 57 155)" />
      <rect className="arm arm-r" x="134" y="130" width="18" height="50" rx="4" fill="#B8860B" transform="rotate(15 143 155)" />

      <rect className="palm" x="72" y="68" width="22" height="14" rx="3" fill="#DAA520" opacity="0" />
    </svg>
  );
}

function PobreFoxSvg({ isSpeaking }: { isSpeaking: boolean }) {
  return (
    <svg viewBox="0 0 200 240" className="avatar-svg avatar-svg--pobre" aria-hidden="true">
      <defs>
        <linearGradient id="foxRust" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#CD853F" />
          <stop offset="100%" stopColor="#8B4513" />
        </linearGradient>
      </defs>

      <path className="helmet" d="M 70 52 A 60 35 0 0 1 130 52 L 125 65 L 75 65 Z" fill="#708090" stroke="#4a5568" strokeWidth="2" />
      <rect x="88" y="42" width="24" height="6" rx="2" fill="#FFA500" className="helmet-light" />

      <polygon className="ear ear-l" points="72,58 62,30 88,52" fill="#CD853F" stroke="#5D3A1A" strokeWidth="1" />
      <polygon className="ear ear-r" points="128,58 138,30 112,52" fill="#CD853F" stroke="#5D3A1A" strokeWidth="1" />

      <ellipse className="head" cx="100" cy="82" rx="38" ry="32" fill="url(#foxRust)" stroke="#5D3A1A" strokeWidth="2" />

      <polygon className="snout" points="100,88 118,105 82,105" fill="#DEB887" stroke="#5D3A1A" strokeWidth="1" />
      <ellipse className="nose" cx="100" cy="102" rx="5" ry="4" fill="#1a1a2e" />

      <ellipse className="eye eye-l" cx="85" cy="78" rx="6" ry="8" fill="#1a1a2e" />
      <ellipse className="eye eye-r" cx="115" cy="78" rx="6" ry="8" fill="#1a1a2e" />
      <path className="eye-curve eye-curve-l" d="M 79 74 Q 85 70 91 74" fill="none" stroke="#1a1a2e" strokeWidth="1.5" opacity="0" />
      <path className="eye-curve eye-curve-r" d="M 109 74 Q 115 70 121 74" fill="none" stroke="#1a1a2e" strokeWidth="1.5" opacity="0" />

      <path
        className={`mouth mouth-default ${isSpeaking ? "mouth--open" : ""}`}
        d={isSpeaking ? "M 92 108 Q 100 118 108 108" : "M 92 110 Q 100 113 108 110"}
        stroke="#1a1a2e"
        strokeWidth="2"
        fill="none"
      />
      <path className="mouth mouth-smirk" d="M 93 109 Q 100 114 108 106" fill="none" stroke="#1a1a2e" strokeWidth="2" strokeLinecap="round" />
      <path className="mouth mouth-smile" d="M 92 108 Q 100 116 108 108" fill="none" stroke="#1a1a2e" strokeWidth="2.2" strokeLinecap="round" />
      <path className="mouth mouth-frown" d="M 92 112 Q 100 104 108 112" fill="none" stroke="#1a1a2e" strokeWidth="2.2" strokeLinecap="round" />

      <circle className="body" cx="100" cy="155" r="42" fill="#708090" stroke="#4a5568" strokeWidth="2" />
      <polygon className="overalls" points="68,145 132,145 125,200 75,200" fill="#556B2F" stroke="#3d4f21" strokeWidth="1" />

      <rect className="arm arm-l" x="50" y="138" width="16" height="45" rx="5" fill="#CD853F" transform="rotate(-20 58 160)" />
      <rect className="arm arm-r" x="134" y="138" width="16" height="45" rx="5" fill="#CD853F" transform="rotate(20 142 160)" />

      <rect className="clipboard" x="138" y="148" width="28" height="36" rx="3" fill="#E8E8E8" stroke="#888" strokeWidth="1" />
      <line x1="144" y1="158" x2="160" y2="158" stroke="#888" strokeWidth="1" />
      <line x1="144" y1="166" x2="160" y2="166" stroke="#888" strokeWidth="1" />
      <line x1="144" y1="174" x2="155" y2="174" stroke="#888" strokeWidth="1" />

      <circle className="spark spark-1" cx="45" cy="120" r="3" fill="#FFA500" />
      <circle className="spark spark-2" cx="158" cy="125" r="2" fill="#FFA500" />
      <circle className="joy-spark joy-spark-1" cx="100" cy="48" r="2.5" fill="#feca57" opacity="0" />
      <circle className="joy-spark joy-spark-2" cx="88" cy="52" r="1.8" fill="#feca57" opacity="0" />
      <circle className="joy-spark joy-spark-3" cx="112" cy="52" r="1.8" fill="#feca57" opacity="0" />
    </svg>
  );
}
