import { useCallback, useEffect, useState } from "react";
import type { PersonasConfig, RoleId } from "../types";
import { roleDisplayName } from "../utils/personaLabel";

type Kind = "profiles" | "skills";

interface PersonaEditorProps {
  open: boolean;
  onClose: () => void;
  onUpdated: (config: PersonasConfig) => void;
}

interface ProfileForm {
  id: string;
  name: string;
  description: string;
  prompt: string;
  default_skills: string[];
}

interface SkillForm {
  id: string;
  name: string;
  description: string;
  prompt: string;
}

const emptyProfile = (): ProfileForm => ({
  id: "",
  name: "",
  description: "",
  prompt: "",
  default_skills: [],
});

const emptySkill = (): SkillForm => ({
  id: "",
  name: "",
  description: "",
  prompt: "",
});

function estimateProfileLines(form: ProfileForm): number {
  const skills = form.default_skills.length ? 1 : 0;
  const body = form.description.trim().split("\n").length;
  const promptExtra = form.prompt.trim() && form.prompt.trim() !== form.description.trim() ? 1 : 0;
  return 3 + skills + body + promptExtra;
}

function estimateSkillLines(form: SkillForm): number {
  const body = form.description.trim() ? 1 : 0;
  const extra = form.prompt.trim() && form.prompt.trim() !== form.description.trim() ? 1 : 0;
  return 3 + body + extra;
}

export function PersonaEditor({ open, onClose, onUpdated }: PersonaEditorProps) {
  const [config, setConfig] = useState<PersonasConfig | null>(null);
  const [debater, setDebater] = useState<RoleId>("cliente");
  const [kind, setKind] = useState<Kind>("profiles");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [profileForm, setProfileForm] = useState<ProfileForm>(emptyProfile());
  const [skillForm, setSkillForm] = useState<SkillForm>(emptySkill());
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const reload = useCallback(async () => {
    const res = await fetch("/api/personas");
    const data: PersonasConfig = await res.json();
    setConfig(data);
    onUpdated(data);
    return data;
  }, [onUpdated]);

  useEffect(() => {
    if (open) {
      reload().catch(() => setError("Falha ao carregar perfis"));
    }
  }, [open, reload]);

  if (!open) return null;

  const items =
    kind === "profiles"
      ? Object.values(config?.[debater]?.profiles ?? {})
      : Object.values(config?.[debater]?.skills ?? {});

  const skillOptions = Object.values(config?.[debater]?.skills ?? {});

  const selectItem = (id: string) => {
    setSelectedId(id);
    setError(null);
    if (kind === "profiles") {
      const p = config?.[debater].profiles[id];
      if (p) {
        setProfileForm({
          id: p.id,
          name: p.name,
          description: p.description,
          prompt: p.prompt ?? p.description,
          default_skills: [...p.default_skills],
        });
      }
    } else {
      const s = config?.[debater].skills[id] as SkillForm | undefined;
      if (s) {
        setSkillForm({
          id: s.id,
          name: s.name,
          description: s.description,
          prompt: s.prompt ?? s.description,
        });
      }
    }
  };

  const startNew = () => {
    setSelectedId(null);
    setError(null);
    if (kind === "profiles") setProfileForm(emptyProfile());
    else setSkillForm(emptySkill());
  };

  const saveItem = async () => {
    setSaving(true);
    setError(null);
    try {
      const isNew = !selectedId;
      const payload =
        kind === "profiles"
          ? {
              ...profileForm,
              prompt: profileForm.prompt.trim() || profileForm.description.trim(),
            }
          : skillForm;
      const url =
        kind === "profiles"
          ? `/api/personas/${debater}/profiles${isNew ? "" : `/${profileForm.id}`}`
          : `/api/personas/${debater}/skills${isNew ? "" : `/${skillForm.id}`}`;
      const method = isNew ? "POST" : "PUT";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Erro ao salvar");
      }
      const data = await reload();
      const savedId = kind === "profiles" ? profileForm.id : skillForm.id;
      if (kind === "profiles") {
        selectItem(savedId);
      } else {
        const s = data[debater].skills[savedId];
        setSelectedId(savedId);
        setSkillForm({
          id: s.id,
          name: s.name,
          description: s.description,
          prompt: s.prompt ?? s.description,
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  };

  const deleteItem = async () => {
    if (!selectedId) return;
    if (!confirm(`Remover ${selectedId}?`)) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`/api/personas/${debater}/${kind}/${selectedId}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Erro ao remover");
      }
      await reload();
      startNew();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao remover");
    } finally {
      setSaving(false);
    }
  };

  const saveAsDefault = async () => {
    if (!config) return;
    setSaving(true);
    setError(null);
    try {
      const next = { ...config.defaults };
      if (kind === "profiles" && profileForm.id) {
        next[debater] = { ...next[debater], profile: profileForm.id };
      } else if (kind === "skills" && skillForm.id) {
        next[debater] = { ...next[debater], skills: [skillForm.id] };
      }
      const res = await fetch("/api/personas/defaults", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(next),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Erro ao salvar padrão");
      }
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar padrão");
    } finally {
      setSaving(false);
    }
  };

  const lineCount =
    kind === "profiles" ? estimateProfileLines(profileForm) : estimateSkillLines(skillForm);

  return (
    <div className="persona-overlay" onClick={onClose}>
      <div className="persona-editor" onClick={(e) => e.stopPropagation()}>
        <header className="persona-editor-header">
          <h2>TRUEPALEO — Perfis & Skills</h2>
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            Fechar
          </button>
        </header>

        <div className="persona-tabs">
          {(["cliente", "sac"] as RoleId[]).map((d) => (
            <button
              key={d}
              type="button"
              className={`persona-tab${debater === d ? " active" : ""}`}
              onClick={() => {
                setDebater(d);
                startNew();
              }}
            >
              {roleDisplayName(d)}
            </button>
          ))}
          <span className="persona-tab-sep" />
          {(["profiles", "skills"] as Kind[]).map((k) => (
            <button
              key={k}
              type="button"
              className={`persona-tab${kind === k ? " active" : ""}`}
              onClick={() => {
                setKind(k);
                startNew();
              }}
            >
              {k === "profiles" ? "Perfis" : "Skills"}
            </button>
          ))}
        </div>

        {error && <div className="banner banner--error persona-error">{error}</div>}

        <div className="persona-editor-body">
          <aside className="persona-list">
            <button type="button" className="btn btn--ghost persona-new-btn" onClick={startNew}>
              + Novo
            </button>
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`persona-list-item${selectedId === item.id ? " active" : ""}`}
                onClick={() => selectItem(item.id)}
              >
                {item.name}
                {config?.defaults[debater]?.profile === item.id && kind === "profiles" && (
                  <span className="persona-badge">padrão</span>
                )}
                {config?.defaults[debater]?.skills?.includes(item.id) && kind === "skills" && (
                  <span className="persona-badge">básica</span>
                )}
              </button>
            ))}
          </aside>

          <div className="persona-form">
            {kind === "profiles" ? (
              <>
                <label className="setup-field">
                  ID (slug)
                  <input
                    value={profileForm.id}
                    disabled={!!selectedId}
                    onChange={(e) =>
                      setProfileForm((f) => ({
                        ...f,
                        id: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""),
                      }))
                    }
                    placeholder="ex: herdeiro"
                  />
                </label>
                <label className="setup-field">
                  Nome
                  <input
                    value={profileForm.name}
                    onChange={(e) => setProfileForm((f) => ({ ...f, name: e.target.value }))}
                  />
                </label>
                <label className="setup-field">
                  Resumo curto
                  <input
                    value={profileForm.description}
                    onChange={(e) =>
                      setProfileForm((f) => ({ ...f, description: e.target.value }))
                    }
                  />
                </label>
                <label className="setup-field">
                  Prompt de personalidade (instrução ao LLM — funciona como skill principal)
                  <textarea
                    rows={4}
                    value={profileForm.prompt}
                    onChange={(e) =>
                      setProfileForm((f) => ({ ...f, prompt: e.target.value }))
                    }
                    placeholder="Ex.: Você é esnobe, usa jargão premium, despreza argumentos técnicos..."
                  />
                </label>
                <div className="setup-skills">
                  <span className="setup-skills-label">Skills sugeridas</span>
                  {skillOptions.map((s) => (
                    <label key={s.id} className="skill-chip">
                      <input
                        type="checkbox"
                        checked={profileForm.default_skills.includes(s.id)}
                        onChange={() =>
                          setProfileForm((f) => ({
                            ...f,
                            default_skills: f.default_skills.includes(s.id)
                              ? f.default_skills.filter((x) => x !== s.id)
                              : [...f.default_skills, s.id],
                          }))
                        }
                      />
                      {s.name}
                    </label>
                  ))}
                </div>
              </>
            ) : (
              <>
                <label className="setup-field">
                  ID (slug)
                  <input
                    value={skillForm.id}
                    disabled={!!selectedId}
                    onChange={(e) =>
                      setSkillForm((f) => ({
                        ...f,
                        id: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""),
                      }))
                    }
                    placeholder="ex: jargao_premium"
                  />
                </label>
                <label className="setup-field">
                  Nome
                  <input
                    value={skillForm.name}
                    onChange={(e) => setSkillForm((f) => ({ ...f, name: e.target.value }))}
                  />
                </label>
                <label className="setup-field">
                  Descrição curta
                  <input
                    value={skillForm.description}
                    onChange={(e) =>
                      setSkillForm((f) => ({ ...f, description: e.target.value }))
                    }
                  />
                </label>
                <label className="setup-field">
                  Instrução para o LLM
                  <textarea
                    rows={3}
                    value={skillForm.prompt}
                    onChange={(e) => setSkillForm((f) => ({ ...f, prompt: e.target.value }))}
                  />
                </label>
              </>
            )}

            <p className={`persona-line-count${lineCount > 15 ? " over-limit" : ""}`}>
              {lineCount}/15 linhas no .md
            </p>

            <div className="persona-form-actions">
              <button
                type="button"
                className="btn btn--primary"
                disabled={saving}
                onClick={() => void saveItem()}
              >
                Salvar
              </button>
              {selectedId && (
                <>
                  <button
                    type="button"
                    className="btn btn--ghost"
                    disabled={saving}
                    onClick={() => void saveAsDefault()}
                  >
                    Definir como padrão
                  </button>
                  <button
                    type="button"
                    className="btn btn--secondary"
                    disabled={saving}
                    onClick={() => void deleteItem()}
                  >
                    Remover
                  </button>
                </>
              )}
            </div>

            <p className="setup-hint">
              Arquivos em <code>personas/{debater}/{kind}/</code>. Máximo 15 linhas por arquivo.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
