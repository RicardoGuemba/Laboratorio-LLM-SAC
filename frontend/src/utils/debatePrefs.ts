const TOPIC_KEY = "lab-personas-llm:last-topic";
const MODELS_KEY = "lab-personas-llm:last-models";
const SESSION_KEY = "lab-personas-llm:last-session";

export interface LastModels {
  rico: string;
  pobre: string;
}

export interface LastSession {
  ricoModel: string;
  pobreModel: string;
  ricoProfile: string;
  pobreProfile: string;
  ricoSkills: string[];
  pobreSkills: string[];
  ricoLlmParams?: { temperature?: number; top_p?: number; max_tokens?: number };
  pobreLlmParams?: { temperature?: number; top_p?: number; max_tokens?: number };
  timestamp: number;
}

export function getLastTopic(): string {
  try {
    return (
      localStorage.getItem(TOPIC_KEY)?.trim() ||
      localStorage.getItem("arena-debates:last-topic")?.trim() ||
      ""
    );
  } catch {
    return "";
  }
}

export function saveLastTopic(topic: string): void {
  try {
    localStorage.setItem(TOPIC_KEY, topic.trim());
  } catch {
    /* ignore quota / private mode */
  }
}

export function getLastModels(): LastModels {
  try {
    const raw = localStorage.getItem(MODELS_KEY) || localStorage.getItem("arena-debates:last-models");
    if (!raw) return { rico: "", pobre: "" };
    const parsed = JSON.parse(raw) as Partial<LastModels>;
    return {
      rico: typeof parsed.rico === "string" ? parsed.rico.trim() : "",
      pobre: typeof parsed.pobre === "string" ? parsed.pobre.trim() : "",
    };
  } catch {
    return { rico: "", pobre: "" };
  }
}

export function saveLastModels(rico: string, pobre: string): void {
  try {
    localStorage.setItem(
      MODELS_KEY,
      JSON.stringify({ rico: rico.trim(), pobre: pobre.trim() }),
    );
  } catch {
    /* ignore quota / private mode */
  }
}

export function resolveModelChoice(
  debater: keyof LastModels,
  catalog: { models: string[]; defaults: LastModels },
  current = "",
): string {
  const saved = getLastModels()[debater];
  const session = getLastSession();
  const sessionModel = debater === "rico" ? session?.ricoModel : session?.pobreModel;
  const fallback = catalog.defaults[debater];
  const isAvailable = (model: string) =>
    Boolean(model) && (catalog.models.length === 0 || catalog.models.includes(model));

  if (isAvailable(current)) return current;
  if (isAvailable(sessionModel || "")) return sessionModel!;
  if (isAvailable(saved)) return saved;
  return fallback;
}

export function getLastSession(): LastSession | null {
  try {
    const raw =
      localStorage.getItem(SESSION_KEY) || localStorage.getItem("arena-debates:last-session");
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<LastSession>;
    const oneWeekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
    if ((parsed.timestamp ?? 0) < oneWeekAgo) return null;
    return {
      ricoModel: parsed.ricoModel ?? "",
      pobreModel: parsed.pobreModel ?? "",
      ricoProfile: parsed.ricoProfile ?? "",
      pobreProfile: parsed.pobreProfile ?? "",
      ricoSkills: Array.isArray(parsed.ricoSkills) ? parsed.ricoSkills : [],
      pobreSkills: Array.isArray(parsed.pobreSkills) ? parsed.pobreSkills : [],
      ricoLlmParams: parsed.ricoLlmParams,
      pobreLlmParams: parsed.pobreLlmParams,
      timestamp: parsed.timestamp ?? Date.now(),
    };
  } catch {
    return null;
  }
}

export function saveLastSession(session: Omit<LastSession, "timestamp">): void {
  try {
    localStorage.setItem(
      SESSION_KEY,
      JSON.stringify({ ...session, timestamp: Date.now() }),
    );
    saveLastModels(session.ricoModel, session.pobreModel);
  } catch {
    /* ignore */
  }
}
