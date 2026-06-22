import type { Gesture } from "../types";

const DEBOCHE = ["absurdo", "ridículo", "patético", "vergonha", "sinergia", "disruptivo", "elite"];
const ALEGRIA = ["evidência", "dado", "métrica", "comprov", "estudo", "análise", "correto"];
const REJEICAO = ["errado", "falso", "mentira", "inaceitável", "nunca", "jamais", "contra"];

export function inferSpeakerGesture(text: string): Gesture {
  const lower = text.toLowerCase();
  if (DEBOCHE.some((w) => lower.includes(w))) return "deboche";
  if (ALEGRIA.some((w) => lower.includes(w))) return "alegria";
  if (REJEICAO.some((w) => lower.includes(w))) return "rejeicao";
  return "talk";
}
