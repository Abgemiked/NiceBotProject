export interface Permissions {
  tier: "full_admin" | "dc_mod" | "none";
  view_secrets: boolean;
  edit_settings: boolean;
  edit_secrets: boolean;
}

export interface Me {
  discord_id: string;
  username: string;
  permissions: Permissions;
}

/** Lädt die eigene Identität. null = nicht angemeldet (401) oder kein Zugriff (403). */
export async function fetchMe(): Promise<Me | null> {
  const res = await fetch("/api/me", { credentials: "same-origin" });
  if (res.status === 401 || res.status === 403) return null;
  if (!res.ok) throw new Error(`Unerwarteter Fehler: ${res.status}`);
  return res.json();
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
}
