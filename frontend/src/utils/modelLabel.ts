/** Rótulo curto do modelo LM Studio para exibição discreta. */
export function formatModelLabel(modelId: string): string {
  if (!modelId) return "";
  const base = modelId.split("/").pop() ?? modelId;
  return base.length > 28 ? `${base.slice(0, 26)}…` : base;
}
