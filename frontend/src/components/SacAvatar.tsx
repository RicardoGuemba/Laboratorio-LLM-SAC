import type { RoleId } from "../types";
import type { AvatarMood } from "../utils/avatarMood";
import { avatarAriaLabel } from "../utils/avatarMood";

interface SacAvatarProps {
  role: RoleId;
  mood?: AvatarMood;
  size?: number;
}

export function SacAvatar({ role, mood = "idle", size = 72 }: SacAvatarProps) {
  const isCliente = role === "cliente";
  const label = avatarAriaLabel(role, mood);

  return (
    <div
      className={`sac-avatar sac-avatar--${role} sac-avatar--${mood}`}
      style={{ width: size, height: size }}
      role="img"
      aria-label={label}
    >
      <svg
        viewBox="0 0 80 80"
        width={size}
        height={size}
        className="sac-avatar__svg"
        aria-hidden="true"
      >
        {isCliente ? (
          <ClientePortrait mood={mood} />
        ) : (
          <SacPortrait mood={mood} />
        )}
      </svg>
      {mood === "speaking" && (
        <span className="sac-avatar__pulse" aria-hidden="true" />
      )}
    </div>
  );
}

function ClientePortrait({ mood }: { mood: AvatarMood }) {
  const browY = mood === "frustrated" ? 26 : mood === "anxious" ? 27 : 28;
  const browRotate = mood === "frustrated" ? -8 : mood === "anxious" ? 6 : 0;
  const mouthPath =
    mood === "frustrated"
      ? "M 30 52 Q 40 46 50 52"
      : mood === "anxious"
        ? "M 34 54 Q 40 50 46 54"
        : mood === "speaking"
          ? "M 32 50 Q 40 56 48 50"
          : "M 34 52 Q 40 55 46 52";

  return (
    <>
      <defs>
        <linearGradient id="clienteBg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#fde8d8" />
          <stop offset="100%" stopColor="#f5d0b8" />
        </linearGradient>
        <linearGradient id="clienteHair" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#3d2c24" />
          <stop offset="100%" stopColor="#5c4033" />
        </linearGradient>
      </defs>
      <circle cx="40" cy="40" r="38" fill="url(#clienteBg)" stroke="#d4a574" strokeWidth="1.5" />
      <ellipse cx="40" cy="72" rx="22" ry="8" fill="#e8c4a0" opacity="0.5" />
      <path
        d="M 14 38 Q 18 12 40 10 Q 62 12 66 38 Q 58 22 40 20 Q 22 22 14 38"
        fill="url(#clienteHair)"
      />
      <ellipse cx="40" cy="42" rx="18" ry="20" fill="#f0c9a8" />
      <ellipse cx="40" cy="44" rx="14" ry="16" fill="#e8b896" />
      <ellipse cx="31" cy="40" rx="3.2" ry="4" fill="#fff" />
      <ellipse cx="49" cy="40" rx="3.2" ry="4" fill="#fff" />
      <circle cx="31" cy="41" r="2" fill="#3d2c24" />
      <circle cx="49" cy="41" r="2" fill="#3d2c24" />
      {mood === "anxious" && (
        <>
          <path d="M 26 36 Q 31 34 36 36" stroke="#8b6914" strokeWidth="1.2" fill="none" />
          <path d="M 44 36 Q 49 34 54 36" stroke="#8b6914" strokeWidth="1.2" fill="none" />
        </>
      )}
      <line
        x1="26"
        y1={browY}
        x2="36"
        y2={browY - 1}
        stroke="#5c4033"
        strokeWidth="1.8"
        strokeLinecap="round"
        transform={`rotate(${-browRotate} 31 ${browY})`}
      />
      <line
        x1="44"
        y1={browY - 1}
        x2="54"
        y2={browY}
        stroke="#5c4033"
        strokeWidth="1.8"
        strokeLinecap="round"
        transform={`rotate(${browRotate} 49 ${browY})`}
      />
      <path d={mouthPath} stroke="#a0522d" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      {mood === "frustrated" && (
        <path
          d="M 58 24 L 62 20 M 62 24 L 58 20"
          stroke="#b33a3a"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      )}
      {mood === "speaking" && (
        <>
          <circle cx="62" cy="18" r="2" fill="#8b6914" opacity="0.7" className="avatar-dot" />
          <circle cx="68" cy="22" r="1.5" fill="#8b6914" opacity="0.5" className="avatar-dot avatar-dot--2" />
        </>
      )}
      <rect x="22" y="58" width="36" height="14" rx="4" fill="#6b8cae" />
      <path d="M 28 58 L 32 52 L 48 52 L 52 58" fill="#5a7a9a" />
    </>
  );
}

function SacPortrait({ mood }: { mood: AvatarMood }) {
  const smilePath =
    mood === "empathetic"
      ? "M 32 50 Q 40 58 48 50"
      : mood === "speaking"
        ? "M 32 50 Q 40 56 48 50"
        : "M 34 52 Q 40 55 46 52";

  return (
    <>
      <defs>
        <linearGradient id="sacBg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#e8f0e4" />
          <stop offset="100%" stopColor="#c5d4bc" />
        </linearGradient>
        <linearGradient id="sacShirt" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#4a6b4c" />
          <stop offset="100%" stopColor="#3d5a3e" />
        </linearGradient>
      </defs>
      <circle cx="40" cy="40" r="38" fill="url(#sacBg)" stroke="#3d5a3e" strokeWidth="1.5" />
      <ellipse cx="40" cy="72" rx="22" ry="8" fill="#a8c4a0" opacity="0.4" />
      <path
        d="M 16 36 Q 20 14 40 12 Q 60 14 64 36 Q 56 20 40 18 Q 24 20 16 36"
        fill="#4a3728"
      />
      <ellipse cx="40" cy="42" rx="18" ry="20" fill="#d4a574" />
      <ellipse cx="40" cy="44" rx="14" ry="16" fill="#c4956a" />
      <ellipse cx="31" cy="40" rx="3.2" ry="3.8" fill="#fff" />
      <ellipse cx="49" cy="40" rx="3.2" ry="3.8" fill="#fff" />
      <circle cx="31" cy="40.5" r="2" fill="#2d4430" />
      <circle cx="49" cy="40.5" r="2" fill="#2d4430" />
      <path d="M 28 28 Q 31 26 34 28" stroke="#4a3728" strokeWidth="1.5" fill="none" strokeLinecap="round" />
      <path d="M 46 28 Q 49 26 52 28" stroke="#4a3728" strokeWidth="1.5" fill="none" strokeLinecap="round" />
      <path d={smilePath} stroke="#5c4033" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      <rect x="22" y="58" width="36" height="14" rx="4" fill="url(#sacShirt)" />
      <path d="M 28 58 L 34 50 L 46 50 L 52 58" fill="#2d4430" />
      <circle cx="40" cy="54" r="2.5" fill="#8b6914" opacity="0.9" />
      <path
        d="M 38 54 Q 40 48 42 54"
        fill="#6b9b4a"
        opacity="0.8"
      />
      <path
        d="M 8 52 Q 12 44 18 48 L 16 56 Q 10 58 8 52"
        fill="#3d5a3e"
        opacity="0.85"
      />
      <path
        d="M 72 52 Q 68 44 62 48 L 64 56 Q 70 58 72 52"
        fill="#3d5a3e"
        opacity="0.85"
      />
      <ellipse cx="18" cy="50" rx="5" ry="7" fill="#2d4430" />
      <ellipse cx="62" cy="50" rx="5" ry="7" fill="#2d4430" />
      <path d="M 16 48 Q 18 42 20 48" stroke="#555" strokeWidth="1" fill="none" />
      <path d="M 60 48 Q 62 42 64 48" stroke="#555" strokeWidth="1" fill="none" />
      {mood === "speaking" && (
        <>
          <circle cx="62" cy="16" r="2" fill="#3d5a3e" opacity="0.8" className="avatar-dot" />
          <circle cx="68" cy="20" r="1.5" fill="#3d5a3e" opacity="0.6" className="avatar-dot avatar-dot--2" />
        </>
      )}
      {mood === "empathetic" && (
        <path
          d="M 24 46 Q 26 44 28 46"
          stroke="#6b9b4a"
          strokeWidth="1.2"
          fill="none"
          opacity="0.7"
        />
      )}
    </>
  );
}
