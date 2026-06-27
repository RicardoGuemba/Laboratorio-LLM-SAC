import type { PersonasConfig, RoleId } from "../types";

const ROLE_DISPLAY: Record<RoleId, string> = {
  cliente: "Cliente",
  sac: "SAC",
};

export function roleDisplayName(role: RoleId): string {
  return ROLE_DISPLAY[role];
}

export function profileDisplayName(
  config: PersonasConfig | null,
  role: RoleId,
  profileId: string,
): string {
  if (!config || !profileId) return roleDisplayName(role);
  const profile = config[role]?.profiles?.[profileId];
  return profile?.name ?? profileId;
}

export function resolveCharacterName(
  config: PersonasConfig | null,
  role: RoleId,
  profileId: string,
): string {
  return profileDisplayName(config, role, profileId);
}
