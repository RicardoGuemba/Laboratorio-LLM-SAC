export type RoleId = "cliente" | "sac";

export interface TurnRecord {
  id: string;
  role: RoleId;
  text: string;
  title?: string | null;
  thinking?: string | null;
  latency_ms?: number | null;
  timestamp: string;
}

export interface RagChunk {
  doc_id: string;
  section: string;
  text: string;
  score: number;
  metadata?: Record<string, unknown>;
}

export interface LlmParams {
  temperature?: number;
  top_p?: number;
  max_tokens?: number;
}

export interface SacSession {
  id: string;
  cliente_profile: string;
  sac_profile: string;
  cliente_profile_name?: string;
  sac_profile_name?: string;
  cliente_model: string;
  sac_model: string;
  cliente_thinking?: boolean;
  sac_thinking?: boolean;
  cliente_skills?: string[];
  sac_skills?: string[];
  cliente_llm_params?: LlmParams;
  sac_llm_params?: LlmParams;
  status: string;
  complaint_title: string;
  complaint_text: string;
  response_text: string;
  category?: string | null;
  rag_chunks: RagChunk[];
  turns: TurnRecord[];
}

export interface StreamEvent {
  type: string;
  role?: RoleId;
  content?: string;
  category?: string;
  manual?: boolean;
  chunks?: RagChunk[];
  turn?: Partial<TurnRecord> & { title?: string };
  session?: SacSession;
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
  defaults: Record<RoleId, PersonaDefaults>;
  cliente: { profiles: Record<string, PersonaProfile>; skills: Record<string, PersonaSkill> };
  sac: { profiles: Record<string, PersonaProfile>; skills: Record<string, PersonaSkill> };
}

export interface SacStartConfig {
  clienteProfile: string;
  sacProfile: string;
  clienteModel: string;
  sacModel: string;
  clienteThinking: boolean;
  sacThinking: boolean;
  clienteSkills: string[];
  sacSkills: string[];
  clienteLlmParams: LlmParams;
  sacLlmParams: LlmParams;
}

export interface ModelsCatalog {
  models: string[];
  defaults: { cliente_truepaleo: string; truepaleo_sac: string };
  configured?: { cliente_truepaleo: string; truepaleo_sac: string };
}

export interface KnowledgeFile {
  id: string;
  path: string;
  directory: string;
  title: string;
  metadata: Record<string, unknown>;
  valid: boolean;
  errors: string[];
  size_bytes: number;
}

export interface KnowledgeStats {
  doc_count: number;
  chunk_count: number;
  last_indexed: string | null;
}

export const DEFAULT_LLM_PARAMS: Required<LlmParams> = {
  temperature: 0.7,
  top_p: 0.9,
  max_tokens: 256,
};

export const ROLE_LABELS: Record<RoleId, string> = {
  cliente: "cliente_truepaleo",
  sac: "Truepaleo-SAC",
};
