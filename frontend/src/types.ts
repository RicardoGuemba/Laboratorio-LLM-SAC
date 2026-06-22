export type DebaterId = "rico" | "pobre";

export type Gesture =
  | "talk"
  | "deboche"
  | "alegria"
  | "rejeicao"
  | "nod"
  | "head_shake"
  | "facepalm"
  | "raised_brow"
  | "shrug"
  | "slow_blink"
  | "confused";

export type DebatePhase = "opening" | "argument" | "replica" | "treplica" | "chat";

export type SessionMode = "debate" | "casual";

export interface TurnRecord {
  id: string;
  debater: DebaterId;
  phase: DebatePhase;
  round_num: number;
  text: string;
  thinking?: string | null;
  reaction_from_peer?: ReactionEvent | null;
  latency_ms?: number | null;
  timestamp: string;
}

export interface Scoreboard {
  buzzwords: number;
  yellow_cards: number;
  applause: number;
}

export interface LlmParams {
  temperature?: number;
  top_p?: number;
  max_tokens?: number;
}

export interface DebateState {
  id: string;
  topic: string;
  mode?: SessionMode;
  topic_starter?: DebaterId | null;
  rico_profile: string;
  pobre_profile: string;
  rico_profile_name?: string;
  pobre_profile_name?: string;
  rico_model: string;
  pobre_model: string;
  rico_position: string;
  pobre_position: string;
  rico_thinking?: boolean;
  pobre_thinking?: boolean;
  rico_skills?: string[];
  pobre_skills?: string[];
  rico_llm_params?: LlmParams;
  pobre_llm_params?: LlmParams;
  status: string;
  current_round: number;
  turns: TurnRecord[];
  scoreboard: Scoreboard;
  next_turn?: {
    debater: DebaterId;
    phase: DebatePhase;
    round_num: number;
  };
  is_finished?: boolean;
}

export interface ReactionEvent {
  score: number;
  gesture: Gesture;
  reaction: string;
  one_liner: string;
  buzzword_count?: number;
  yellow_card?: boolean;
  listener?: DebaterId;
  speaker?: DebaterId;
}

export interface StreamEvent {
  type: string;
  debater?: DebaterId;
  listener?: DebaterId;
  speaker?: DebaterId;
  content?: string;
  phase?: DebatePhase;
  round_num?: number;
  gesture?: Gesture;
  one_liner?: string;
  turn?: TurnRecord;
  scoreboard?: Scoreboard;
  is_finished?: boolean;
  message?: string;
  fallback?: string;
}

export interface PersonaSkill {
  id: string;
  name: string;
  description: string;
  prompt?: string;
}

export interface PersonaProfile {
  id: string;
  name: string;
  description: string;
  prompt?: string;
  default_skills: string[];
}

export interface PersonaDefaults {
  profile: string;
  skills: string[];
}

export interface PersonasConfig {
  defaults: Record<DebaterId, PersonaDefaults>;
  rico: { profiles: Record<string, PersonaProfile>; skills: Record<string, PersonaSkill> };
  pobre: { profiles: Record<string, PersonaProfile>; skills: Record<string, PersonaSkill> };
}

export interface DebateStartConfig {
  mode: SessionMode;
  topic: string;
  ricoProfile: string;
  pobreProfile: string;
  ricoModel: string;
  pobreModel: string;
  ricoThinking: boolean;
  pobreThinking: boolean;
  ricoSkills: string[];
  pobreSkills: string[];
  ricoLlmParams: LlmParams;
  pobreLlmParams: LlmParams;
}

export interface ModelsCatalog {
  models: string[];
  defaults: { rico: string; pobre: string };
  configured?: { rico: string; pobre: string };
}

export const PHASE_LABELS: Record<DebatePhase, string> = {
  opening: "Abertura",
  argument: "Argumento",
  replica: "Réplica",
  treplica: "Tréplica",
  chat: "Conversa",
};

export const DEFAULT_LLM_PARAMS: Required<LlmParams> = {
  temperature: 0.7,
  top_p: 0.9,
  max_tokens: 256,
};
