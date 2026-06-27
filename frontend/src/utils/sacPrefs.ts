import type { LlmParams, SacStartConfig } from "../types";

const SESSION_KEY = "truepaleo_sac_session";
const MODELS_KEY = "truepaleo_sac_models";

export function saveLastSession(config: Partial<SacStartConfig>): void {
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(config));
  } catch {
    /* ignore */
  }
}

export function getLastSession(): Partial<SacStartConfig> | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as Partial<SacStartConfig>) : null;
  } catch {
    return null;
  }
}

export function saveLastModels(clienteModel: string, sacModel: string): void {
  try {
    localStorage.setItem(MODELS_KEY, JSON.stringify({ clienteModel, sacModel }));
  } catch {
    /* ignore */
  }
}

export function getLastModels(): { clienteModel?: string; sacModel?: string } | null {
  try {
    const raw = localStorage.getItem(MODELS_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function resolveModelChoice(
  stored: string | undefined,
  catalog: string[],
  fallback: string,
): string {
  if (stored && catalog.includes(stored)) return stored;
  if (fallback && catalog.includes(fallback)) return fallback;
  return catalog[0] ?? fallback;
}

export function buildLlmPayload(params: LlmParams): Record<string, number> | undefined {
  const payload: Record<string, number> = {};
  if (params.temperature != null) payload.temperature = params.temperature;
  if (params.top_p != null) payload.top_p = params.top_p;
  if (params.max_tokens != null) payload.max_tokens = params.max_tokens;
  return Object.keys(payload).length ? payload : undefined;
}
