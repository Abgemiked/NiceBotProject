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

// --- Bot-Konfiguration (M2) ---

export interface ConfigField {
  key: string;
  group: string;
  type: "id" | "idlist" | "string" | "hostlist" | "secret";
  label: string;
  secret: boolean;
  editable: boolean;
}

export interface ConfigResponse {
  fields: ConfigField[];
  values: Record<string, unknown>;
  can_view_secrets: boolean;
  restart_required_keys: string[];
}

export async function fetchConfig(): Promise<ConfigResponse> {
  const res = await fetch("/api/config", { credentials: "same-origin" });
  if (!res.ok) throw new Error(`Konfiguration konnte nicht geladen werden (${res.status})`);
  return res.json();
}

export interface SaveResult {
  ok: boolean;
  updated?: string[];
  error?: string;
  fieldErrors?: Record<string, string>;
}

export async function saveConfig(updates: Record<string, unknown>): Promise<SaveResult> {
  const res = await fetch("/api/config", {
    method: "PUT",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ updates }),
  });
  if (res.ok) return { ok: true, ...(await res.json()) };
  let detail: unknown = null;
  try {
    detail = (await res.json()).detail;
  } catch {
    /* kein JSON-Body */
  }
  if (detail && typeof detail === "object" && "validation_errors" in (detail as object)) {
    return { ok: false, fieldErrors: (detail as { validation_errors: Record<string, string> }).validation_errors };
  }
  return { ok: false, error: typeof detail === "string" ? detail : `Fehler ${res.status}` };
}
