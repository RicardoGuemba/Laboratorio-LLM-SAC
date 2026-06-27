import type { RoleId } from "../types";

export type AvatarMood = "idle" | "speaking" | "frustrated" | "anxious" | "empathetic";

const FRUSTRATED_MARKERS = [
  "indignad",
  "absurdo",
  "não aguento",
  "nao aguento",
  "cadê",
  "cade",
  "inaceit",
  "vergonha",
  "péssim",
  "pessim",
  "horrível",
  "horrivel",
];

const ANXIOUS_MARKERS = [
  "alerg",
  "coceira",
  "vermelhid",
  "irritação",
  "irritacao",
  "medo",
  "preocup",
  "ardência",
  "ardencia",
  "dor",
  "reação",
  "reacao",
];

const EMPATHETIC_MARKERS = [
  "desculp",
  "lament",
  "entend",
  "compreens",
  "sentimos",
  "acolh",
  "apoio",
  "transtorno",
  "prioriz",
];

export function inferClienteMood(text: string, isSpeaking: boolean): AvatarMood {
  if (isSpeaking) return "speaking";
  const lower = text.toLowerCase();
  if (ANXIOUS_MARKERS.some((m) => lower.includes(m))) return "anxious";
  if (FRUSTRATED_MARKERS.some((m) => lower.includes(m))) return "frustrated";
  return "idle";
}

export function inferSacMood(text: string, isSpeaking: boolean): AvatarMood {
  if (isSpeaking) return "speaking";
  const lower = text.toLowerCase();
  if (EMPATHETIC_MARKERS.some((m) => lower.includes(m))) return "empathetic";
  return "idle";
}

export function inferAvatarMood(
  role: RoleId,
  text: string,
  isSpeaking: boolean,
): AvatarMood {
  return role === "cliente"
    ? inferClienteMood(text, isSpeaking)
    : inferSacMood(text, isSpeaking);
}

export function avatarAriaLabel(role: RoleId, mood: AvatarMood): string {
  const roleName = role === "cliente" ? "Cliente TRUEPALEO" : "Atendente SAC TRUEPALEO";
  const moodLabels: Record<AvatarMood, string> = {
    idle: "aguardando",
    speaking: "falando",
    frustrated: "frustrado",
    anxious: "preocupado",
    empathetic: "empático",
  };
  return `${roleName}, ${moodLabels[mood]}`;
}
