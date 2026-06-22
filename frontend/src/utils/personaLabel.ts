import type { DebaterId, PersonasConfig } from "../types";

export function profileDisplayName(
  personas: PersonasConfig | null | undefined,
  debater: DebaterId,
  profileId: string,
): string {
  if (!profileId) return "";
  const fromCatalog = personas?.[debater]?.profiles[profileId]?.name;
  if (fromCatalog?.trim()) return fromCatalog.trim();
  return profileId.replace(/_/g, " ");
}

export function resolveCharacterName(
  personas: PersonasConfig | null | undefined,
  debater: DebaterId,
  profileId: string,
  apiName?: string | null,
): string {
  if (apiName?.trim()) return apiName.trim();
  return profileDisplayName(personas, debater, profileId);
}
