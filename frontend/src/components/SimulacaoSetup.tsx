import { useEffect, useState } from "react";
import { PersonaEditor } from "./PersonaEditor";
import type { LlmParams, ModelsCatalog, PersonasConfig, RoleId, SacStartConfig } from "../types";
import { DEFAULT_LLM_PARAMS } from "../types";
import { getLastModels, getLastSession, resolveModelChoice } from "../utils/sacPrefs";

interface SimulacaoSetupProps {
  onSimulate: (config: SacStartConfig) => void;
  onConfigChange?: (config: SacStartConfig) => void;
  disabled?: boolean;
  isStreaming?: boolean;
  lmOnline: boolean | null;
}

function applyDefaults(data: PersonasConfig) {
  const clienteDef = data.defaults?.cliente;
  const sacDef = data.defaults?.sac;
  return {
    clienteProfile: clienteDef?.profile ?? Object.keys(data.cliente.profiles)[0] ?? "",
    sacProfile: sacDef?.profile ?? Object.keys(data.sac.profiles)[0] ?? "",
    clienteSkills: clienteDef?.skills?.length
      ? [...clienteDef.skills]
      : [...(data.cliente.profiles[clienteDef?.profile ?? ""]?.default_skills ?? [])],
    sacSkills: sacDef?.skills?.length
      ? [...sacDef.skills]
      : [...(data.sac.profiles[sacDef?.profile ?? ""]?.default_skills ?? [])],
  };
}

export function SimulacaoSetup({
  onSimulate,
  onConfigChange,
  disabled,
  isStreaming,
  lmOnline,
}: SimulacaoSetupProps) {
  const [personas, setPersonas] = useState<PersonasConfig | null>(null);
  const [clienteProfile, setClienteProfile] = useState("");
  const [sacProfile, setSacProfile] = useState("");
  const [clienteSkills, setClienteSkills] = useState<string[]>([]);
  const [sacSkills, setSacSkills] = useState<string[]>([]);
  const [clienteThinking, setClienteThinking] = useState(false);
  const [sacThinking, setSacThinking] = useState(false);
  const [clienteModel, setClienteModel] = useState("");
  const [sacModel, setSacModel] = useState("");
  const [clienteLlmParams, setClienteLlmParams] = useState<LlmParams>({ ...DEFAULT_LLM_PARAMS });
  const [sacLlmParams, setSacLlmParams] = useState<LlmParams>({ ...DEFAULT_LLM_PARAMS });
  const [modelsCatalog, setModelsCatalog] = useState<ModelsCatalog | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
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

        const cProf =
          lastSession?.clienteProfile && data.cliente.profiles[lastSession.clienteProfile]
            ? lastSession.clienteProfile
            : applied.clienteProfile;
        const sProf =
          lastSession?.sacProfile && data.sac.profiles[lastSession.sacProfile]
            ? lastSession.sacProfile
            : applied.sacProfile;

        setClienteProfile(cProf);
        setSacProfile(sProf);

        const cSk = lastSession?.clienteSkills?.length
          ? lastSession.clienteSkills.filter((s) => s in data.cliente.skills)
          : [];
        const sSk = lastSession?.sacSkills?.length
          ? lastSession.sacSkills.filter((s) => s in data.sac.skills)
          : [];

        setClienteSkills(cSk.length ? cSk : applied.clienteSkills);
        setSacSkills(sSk.length ? sSk : applied.sacSkills);
        setClienteThinking(lastSession?.clienteThinking ?? false);
        setSacThinking(lastSession?.sacThinking ?? false);
        if (lastSession?.clienteLlmParams) setClienteLlmParams({ ...lastSession.clienteLlmParams });
        if (lastSession?.sacLlmParams) setSacLlmParams({ ...lastSession.sacLlmParams });
      });

  useEffect(() => {
    Promise.all([
      loadPersonas(),
      fetch("/api/models")
        .then((r) => r.json())
        .then((data: ModelsCatalog) => {
          setModelsCatalog(data);
          const last = getLastModels();
          setClienteModel(
            resolveModelChoice(
              last?.clienteModel,
              data.models,
              data.defaults?.cliente_truepaleo ?? "",
            ),
          );
          setSacModel(
            resolveModelChoice(last?.sacModel, data.models, data.defaults?.truepaleo_sac ?? ""),
          );
        }),
    ])
      .catch(() => setValidationError("Falha ao carregar configuração"))
      .finally(() => setIsBootstrapping(false));
  }, []);

  const toggleSkill = (role: RoleId, skillId: string) => {
    const setter = role === "cliente" ? setClienteSkills : setSacSkills;
    setter((prev) =>
      prev.includes(skillId) ? prev.filter((s) => s !== skillId) : [...prev, skillId],
    );
  };

  const buildConfig = (): SacStartConfig => ({
    clienteProfile,
    sacProfile,
    clienteModel,
    sacModel,
    clienteThinking,
    sacThinking,
    clienteSkills,
    sacSkills,
    clienteLlmParams,
    sacLlmParams,
  });

  useEffect(() => {
    if (isBootstrapping || !clienteProfile || !sacProfile) return;
    onConfigChange?.(buildConfig());
  }, [
    isBootstrapping,
    clienteProfile,
    sacProfile,
    clienteModel,
    sacModel,
    clienteThinking,
    sacThinking,
    clienteSkills,
    sacSkills,
    clienteLlmParams,
    sacLlmParams,
    onConfigChange,
  ]);

  const handleSimulate = () => {
    setValidationError(null);
    if (!clienteProfile || !sacProfile) {
      setValidationError("Selecione perfis para cliente e SAC");
      return;
    }
    onSimulate(buildConfig());
  };

  const renderRoleSetup = (role: RoleId) => {
    const isCliente = role === "cliente";
    const profile = isCliente ? clienteProfile : sacProfile;
    const setProfile = isCliente ? setClienteProfile : setSacProfile;
    const skills = isCliente ? clienteSkills : sacSkills;
    const model = isCliente ? clienteModel : sacModel;
    const setModel = isCliente ? setClienteModel : setSacModel;
    const thinking = isCliente ? clienteThinking : sacThinking;
    const setThinking = isCliente ? setClienteThinking : setSacThinking;
    const llmParams = isCliente ? clienteLlmParams : sacLlmParams;
    const setLlmParams = isCliente ? setClienteLlmParams : setSacLlmParams;
    const roleData = personas?.[role];
    const modelKey = isCliente ? "cliente_truepaleo" : "truepaleo_sac";

    return (
      <div className="setup-role" key={role}>
        <h3 className="setup-role__title">{isCliente ? "Cliente" : "SAC"}</h3>
        <div className="setup-role__row">
          <label className="setup-field">
            Perfil
            <select value={profile} onChange={(e) => setProfile(e.target.value)} disabled={disabled}>
              {Object.values(roleData?.profiles ?? {}).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="setup-field setup-field--model">
            Modelo
            <select value={model} onChange={(e) => setModel(e.target.value)} disabled={disabled}>
              {(modelsCatalog?.models ?? [model]).filter(Boolean).map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
          <div className="setup-skills">
            {Object.values(roleData?.skills ?? {}).map((s) => (
              <label key={s.id} className="skill-chip" title={s.name}>
                <input
                  type="checkbox"
                  checked={skills.includes(s.id)}
                  onChange={() => toggleSkill(role, s.id)}
                  disabled={disabled}
                />
                {s.name}
              </label>
            ))}
          </div>
        </div>
        {showAdvanced && (
          <div className="setup-advanced">
            <label className="setup-field setup-field--inline">
              <input
                type="checkbox"
                checked={thinking}
                onChange={(e) => setThinking(e.target.checked)}
                disabled={disabled}
              />
              Modo thinking
            </label>
            <label className="setup-field">
              Temperature
              <input
                type="number"
                min={0}
                max={2}
                step={0.05}
                value={llmParams.temperature ?? DEFAULT_LLM_PARAMS.temperature}
                onChange={(e) =>
                  setLlmParams((p) => ({ ...p, temperature: parseFloat(e.target.value) }))
                }
              />
            </label>
            <label className="setup-field">
              Top P
              <input
                type="number"
                min={0}
                max={1}
                step={0.05}
                value={llmParams.top_p ?? DEFAULT_LLM_PARAMS.top_p}
                onChange={(e) => setLlmParams((p) => ({ ...p, top_p: parseFloat(e.target.value) }))}
              />
            </label>
            <label className="setup-field">
              Max tokens
              <input
                type="number"
                min={32}
                max={4096}
                value={llmParams.max_tokens ?? DEFAULT_LLM_PARAMS.max_tokens}
                onChange={(e) =>
                  setLlmParams((p) => ({ ...p, max_tokens: parseInt(e.target.value, 10) }))
                }
              />
            </label>
            <p className="setup-hint">Default: {modelsCatalog?.defaults?.[modelKey] ?? "—"}</p>
          </div>
        )}
      </div>
    );
  };

  if (isBootstrapping) {
    return <div className="setup-loading">Carregando configuração...</div>;
  }

  return (
    <section className="simulacao-setup">
      <div className="setup-header">
        <div className="setup-header__left">
          <span className={`lm-status${lmOnline ? " online" : lmOnline === false ? " offline" : ""}`}>
            {lmOnline ? "● LM Studio" : lmOnline === false ? "○ LM Studio offline" : "… LM Studio"}
          </span>
        </div>
        <div className="setup-header__actions">
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => setShowAdvanced((v) => !v)}>
            {showAdvanced ? "− LLM" : "+ LLM"}
          </button>
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => setEditorOpen(true)}>
            Personas
          </button>
          <button
            type="button"
            className="btn btn--primary btn--sm setup-simulate"
            disabled={disabled || isStreaming || lmOnline === false}
            onClick={handleSimulate}
          >
            {isStreaming ? "Simulando…" : "Simular"}
          </button>
        </div>
      </div>

      {validationError && <div className="banner banner--error banner--compact">{validationError}</div>}

      <div className="setup-roles">
        {renderRoleSetup("cliente")}
        {renderRoleSetup("sac")}
      </div>

      <PersonaEditor
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        onUpdated={(cfg) => {
          setPersonas(cfg);
          loadPersonas();
        }}
      />
    </section>
  );
}
