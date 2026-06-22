import { useEffect, useState } from "react";
import { PersonaEditor } from "./PersonaEditor";
import type { DebateStartConfig, LlmParams, ModelsCatalog, PersonasConfig, SessionMode } from "../types";
import { DEFAULT_LLM_PARAMS } from "../types";
import { getLastTopic, getLastSession, resolveModelChoice } from "../utils/debatePrefs";
import { profileDisplayName } from "../utils/personaLabel";

interface DebateSetupProps {
  onStart: (config: DebateStartConfig) => void;
  disabled?: boolean;
  lmOnline: boolean | null;
}

function applyDefaults(data: PersonasConfig) {
  const ricoDef = data.defaults?.rico;
  const pobreDef = data.defaults?.pobre;
  return {
    ricoProfile: ricoDef?.profile ?? Object.keys(data.rico.profiles)[0] ?? "",
    pobreProfile: pobreDef?.profile ?? Object.keys(data.pobre.profiles)[0] ?? "",
    ricoSkills: ricoDef?.skills?.length
      ? [...ricoDef.skills]
      : [...(data.rico.profiles[ricoDef?.profile ?? ""]?.default_skills ?? [])],
    pobreSkills: pobreDef?.skills?.length
      ? [...pobreDef.skills]
      : [...(data.pobre.profiles[pobreDef?.profile ?? ""]?.default_skills ?? [])],
  };
}

function profileHasPrompt(personas: PersonasConfig, debater: "rico" | "pobre", profileId: string) {
  const profile = personas[debater].profiles[profileId];
  return Boolean((profile?.prompt || profile?.description || "").trim());
}

export function DebateSetup({ onStart, disabled, lmOnline }: DebateSetupProps) {
  const [personas, setPersonas] = useState<PersonasConfig | null>(null);
  const [topic, setTopic] = useState("");
  const [mode, setMode] = useState<SessionMode>("debate");
  const [ricoProfile, setRicoProfile] = useState("");
  const [pobreProfile, setPobreProfile] = useState("");
  const [ricoSkills, setRicoSkills] = useState<string[]>([]);
  const [pobreSkills, setPobreSkills] = useState<string[]>([]);
  const [ricoThinking, setRicoThinking] = useState(false);
  const [pobreThinking, setPobreThinking] = useState(false);
  const [ricoModel, setRicoModel] = useState("");
  const [pobreModel, setPobreModel] = useState("");
  const [ricoLlmParams, setRicoLlmParams] = useState<LlmParams>({ ...DEFAULT_LLM_PARAMS });
  const [pobreLlmParams, setPobreLlmParams] = useState<LlmParams>({ ...DEFAULT_LLM_PARAMS });
  const [modelsCatalog, setModelsCatalog] = useState<ModelsCatalog | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(true);
  const [editorOpen, setEditorOpen] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);

  const loadPersonas = () =>
    fetch("/api/personas")
      .then((r) => r.json())
      .then((data: PersonasConfig) => {
        setPersonas(data);
        const applied = applyDefaults(data);
        const lastSession = getLastSession();

        const ricoProf =
          lastSession?.ricoProfile && data.rico.profiles[lastSession.ricoProfile]
            ? lastSession.ricoProfile
            : applied.ricoProfile;
        const pobreProf =
          lastSession?.pobreProfile && data.pobre.profiles[lastSession.pobreProfile]
            ? lastSession.pobreProfile
            : applied.pobreProfile;

        setRicoProfile(ricoProf);
        setPobreProfile(pobreProf);

        const ricoSk = lastSession?.ricoSkills?.length
          ? lastSession.ricoSkills.filter((s) => s in data.rico.skills)
          : [];
        const pobreSk = lastSession?.pobreSkills?.length
          ? lastSession.pobreSkills.filter((s) => s in data.pobre.skills)
          : [];

        setRicoSkills(ricoSk.length ? ricoSk : applied.ricoSkills);
        setPobreSkills(pobreSk.length ? pobreSk : applied.pobreSkills);

        if (lastSession?.ricoLlmParams) setRicoLlmParams({ ...DEFAULT_LLM_PARAMS, ...lastSession.ricoLlmParams });
        if (lastSession?.pobreLlmParams) setPobreLlmParams({ ...DEFAULT_LLM_PARAMS, ...lastSession.pobreLlmParams });
      });

  const loadModels = () =>
    fetch("/api/models")
      .then((r) => r.json())
      .then((data: ModelsCatalog) => {
        setModelsCatalog(data);
        setRicoModel((current) => resolveModelChoice("rico", data, current));
        setPobreModel((current) => resolveModelChoice("pobre", data, current));
      });

  useEffect(() => {
    const saved = getLastTopic();
    if (saved) setTopic(saved);
    Promise.all([loadPersonas(), loadModels()])
      .catch(() => undefined)
      .finally(() => setIsBootstrapping(false));
  }, []);

  useEffect(() => {
    if (lmOnline) loadModels().catch(() => undefined);
  }, [lmOnline]);

  const handlePersonasUpdated = (data: PersonasConfig) => {
    setPersonas(data);
    const applied = applyDefaults(data);
    setRicoProfile((prev) => (data.rico.profiles[prev] ? prev : applied.ricoProfile));
    setPobreProfile((prev) => (data.pobre.profiles[prev] ? prev : applied.pobreProfile));
    setRicoSkills((prev) => {
      const filtered = prev.filter((s) => s in data.rico.skills);
      return filtered.length ? filtered : applied.ricoSkills;
    });
    setPobreSkills((prev) => {
      const filtered = prev.filter((s) => s in data.pobre.skills);
      return filtered.length ? filtered : applied.pobreSkills;
    });
  };

  const handleProfileChange = (debater: "rico" | "pobre", profileId: string) => {
    if (!personas) return;
    const profile = personas[debater].profiles[profileId];
    const suggested = profile?.default_skills?.length
      ? [...profile.default_skills]
      : personas.defaults[debater]?.skills ?? [];
    if (debater === "rico") {
      setRicoProfile(profileId);
      if (suggested.length) setRicoSkills(suggested);
    } else {
      setPobreProfile(profileId);
      if (suggested.length) setPobreSkills(suggested);
    }
  };

  const toggleSkill = (debater: "rico" | "pobre", skillId: string) => {
    const selected = debater === "rico" ? ricoSkills : pobreSkills;
    const setter = debater === "rico" ? setRicoSkills : setPobreSkills;
    if (selected.includes(skillId)) {
      setter(selected.filter((s) => s !== skillId));
    } else {
      setter([...selected, skillId]);
    }
    setValidationError(null);
  };

  const modelsReady = Boolean(ricoModel && pobreModel && modelsCatalog);
  const canSubmit = Boolean(personas && modelsReady && !isBootstrapping && !disabled);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === "debate" && topic.trim().length < 3) {
      setValidationError("Informe um tema com ao menos 3 caracteres.");
      return;
    }
    if (!personas) return;
    if (!ricoProfile || !pobreProfile) {
      setValidationError("Selecione um Perfil para cada debatedor.");
      return;
    }
    const ricoOk = ricoSkills.length > 0 || profileHasPrompt(personas, "rico", ricoProfile);
    const pobreOk = pobreSkills.length > 0 || profileHasPrompt(personas, "pobre", pobreProfile);
    if (!ricoOk || !pobreOk) {
      setValidationError("Cada debatedor precisa de um Perfil com prompt ou ao menos uma Skill.");
      return;
    }
    if (!ricoModel || !pobreModel) {
      setValidationError("Selecione o modelo LM Studio para cada debatedor.");
      return;
    }
    setValidationError(null);
    onStart({
      mode,
      topic: topic.trim(),
      ricoProfile,
      pobreProfile,
      ricoModel,
      pobreModel,
      ricoThinking,
      pobreThinking,
      ricoSkills,
      pobreSkills,
      ricoLlmParams,
      pobreLlmParams,
    });
  };

  const modelOptions = (() => {
    if (!modelsCatalog) return [] as string[];
    const { models, defaults } = modelsCatalog;
    if (models.length) return [...models];
    return [...new Set([defaults.rico, defaults.pobre])];
  })();

  const renderLlmParams = (
    params: LlmParams,
    setter: React.Dispatch<React.SetStateAction<LlmParams>>,
  ) => (
    <div className="setup-llm-params">
      <span className="setup-skills-label">Parâmetros LLM</span>
      <label className="setup-field setup-field--inline">
        Temperature
        <input
          type="number"
          min={0}
          max={2}
          step={0.05}
          value={params.temperature ?? DEFAULT_LLM_PARAMS.temperature}
          disabled={disabled}
          onChange={(e) => setter((p) => ({ ...p, temperature: parseFloat(e.target.value) }))}
        />
      </label>
      <label className="setup-field setup-field--inline">
        Top P
        <input
          type="number"
          min={0}
          max={1}
          step={0.05}
          value={params.top_p ?? DEFAULT_LLM_PARAMS.top_p}
          disabled={disabled}
          onChange={(e) => setter((p) => ({ ...p, top_p: parseFloat(e.target.value) }))}
        />
      </label>
      <label className="setup-field setup-field--inline">
        Max tokens
        <input
          type="number"
          min={32}
          max={4096}
          step={1}
          value={params.max_tokens ?? DEFAULT_LLM_PARAMS.max_tokens}
          disabled={disabled}
          onChange={(e) => setter((p) => ({ ...p, max_tokens: parseInt(e.target.value, 10) }))}
        />
      </label>
    </div>
  );

  const renderDebaterConfig = (debater: "rico" | "pobre", label: string) => {
    if (!personas) return null;
    const profileId = debater === "rico" ? ricoProfile : pobreProfile;
    const selectedSkills = debater === "rico" ? ricoSkills : pobreSkills;
    const selectedModel = debater === "rico" ? ricoModel : pobreModel;
    const setModel = debater === "rico" ? setRicoModel : setPobreModel;
    const llmParams = debater === "rico" ? ricoLlmParams : pobreLlmParams;
    const setLlmParams = debater === "rico" ? setRicoLlmParams : setPobreLlmParams;
    const defaultModel = modelsCatalog?.defaults[debater];
    const profile = personas[debater].profiles[profileId];
    const skills = Object.values(personas[debater].skills);
    const defaultProfile = personas.defaults[debater]?.profile;
    const defaultSkills = personas.defaults[debater]?.skills ?? [];

    return (
      <div className={`setup-debater setup-debater--${debater}`}>
        <h3>{label}</h3>
        <label className="setup-field">
          Modelo (qualquer LLM do LM Studio)
          <select
            value={selectedModel}
            disabled={disabled || modelOptions.length === 0}
            onChange={(e) => setModel(e.target.value)}
          >
            {modelOptions.length === 0 && <option value="">Carregando modelos…</option>}
            {modelOptions.map((m) => (
              <option key={m} value={m}>
                {m}
                {m === defaultModel ? " (padrão)" : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="setup-field">
          Perfil de personalidade
          <select
            value={profileId}
            disabled={disabled}
            onChange={(e) => handleProfileChange(debater, e.target.value)}
          >
            {Object.values(personas[debater].profiles).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
                {p.id === defaultProfile ? " (padrão)" : ""}
              </option>
            ))}
          </select>
        </label>
        {profile && <p className="setup-desc">{profile.description}</p>}
        <div className="setup-skills">
          <span className="setup-skills-label">
            Skills adicionais <span className="setup-optional">(opcional se o perfil tiver prompt)</span>
          </span>
          {skills.length === 0 && <p className="setup-hint">Nenhuma skill cadastrada.</p>}
          {skills.map((skill) => (
            <label key={skill.id} className="skill-chip" title={skill.description}>
              <input
                type="checkbox"
                checked={selectedSkills.includes(skill.id)}
                disabled={disabled}
                onChange={() => toggleSkill(debater, skill.id)}
              />
              {skill.name}
              {defaultSkills.includes(skill.id) ? " ★" : ""}
            </label>
          ))}
        </div>
        {renderLlmParams(llmParams, setLlmParams)}
        <label className="thinking-toggle">
          <input
            type="checkbox"
            checked={debater === "rico" ? ricoThinking : pobreThinking}
            disabled={disabled}
            onChange={(e) =>
              debater === "rico"
                ? setRicoThinking(e.target.checked)
                : setPobreThinking(e.target.checked)
            }
          />
          Thinking profundo
        </label>
      </div>
    );
  };

  return (
    <>
      <form className="setup-panel" onSubmit={handleSubmit} noValidate>
        {lmOnline === false && (
          <div className="banner banner--warning">
            LM Studio offline — respostas fallback possíveis.
          </div>
        )}

        <div className="setup-mode-row">
          <span className="setup-skills-label">Modo</span>
          <label className="skill-chip">
            <input
              type="radio"
              name="session-mode"
              checked={mode === "debate"}
              disabled={disabled}
              onChange={() => setMode("debate")}
            />
            Debate formal
          </label>
          <label className="skill-chip">
            <input
              type="radio"
              name="session-mode"
              checked={mode === "casual"}
              disabled={disabled}
              onChange={() => setMode("casual")}
            />
            Conversa casual
          </label>
        </div>

        <div className="setup-topic-row">
          {mode === "debate" ? (
            <input
              className="topic-input"
              placeholder="Qual o tema do debate?"
              value={topic}
              disabled={disabled}
              onChange={(e) => setTopic(e.target.value)}
              minLength={3}
              required
            />
          ) : (
            <p className="setup-hint setup-hint--inline">
              O tema será sorteado automaticamente por um dos modelos, alinhado ao perfil dele.
            </p>
          )}
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => setEditorOpen(true)}
          >
            Laboratório: Perfis & Skills
          </button>
          <button type="button" className="btn btn--ghost" onClick={() => setShowAdvanced((v) => !v)}>
            {showAdvanced ? "Ocultar config" : "Configurar debatedores"}
          </button>
          <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
            {isBootstrapping ? "Carregando…" : mode === "casual" ? "Iniciar conversa" : "Iniciar Debate"}
          </button>
        </div>

        {validationError && (
          <div className="banner banner--error setup-validation">{validationError}</div>
        )}

        {showAdvanced && personas && (
          <div className="setup-debaters-grid">
            {renderDebaterConfig("rico", profileDisplayName(personas, "rico", ricoProfile))}
            {renderDebaterConfig("pobre", profileDisplayName(personas, "pobre", pobreProfile))}
          </div>
        )}

        <p className="setup-hint">
          Todos os LLMs de chat carregados no LM Studio aparecem na lista. Modelos e parâmetros da última sessão são restaurados.
        </p>
      </form>

      <PersonaEditor
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        onUpdated={handlePersonasUpdated}
      />
    </>
  );
}
