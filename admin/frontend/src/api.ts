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

// --- Audit-Log & Statistiken (M5 + M4) ---

export interface AuditEvent {
  id: number;
  ts: string;
  event_type: string;
  actor_name: string | null;
  target_id: string | null;
  target_name: string | null;
  channel_id: string | null;
  content: string | null;
  meta: unknown;
}

export interface AuditList {
  event_types: string[];
  items: AuditEvent[];
  total: number;
  page: number;
  page_size: number;
}

export async function fetchAudit(params: {
  event_type?: string;
  page?: number;
  page_size?: number;
}): Promise<AuditList> {
  const q = new URLSearchParams();
  if (params.event_type) q.set("event_type", params.event_type);
  q.set("page", String(params.page ?? 1));
  q.set("page_size", String(params.page_size ?? 25));
  const res = await fetch(`/api/audit?${q.toString()}`, { credentials: "same-origin" });
  if (!res.ok) throw new Error(`Audit-Log konnte nicht geladen werden (${res.status})`);
  return res.json();
}

export interface Stats {
  member_count: number;
  members_without_ignored: number;
  ignored_role_members: number;
}

export async function fetchStats(): Promise<Stats | null> {
  const res = await fetch("/api/stats", { credentials: "same-origin" });
  if (!res.ok) return null; // Bot evtl. nicht erreichbar — Seite bleibt nutzbar
  return res.json();
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

// --- Level-System (M3) ---

export interface LevelUser {
  user_id: string;
  username: string | null;
  level: number;
  exp: number;
}

export interface LevelList {
  items: LevelUser[];
  total: number;
  page: number;
  page_size: number;
}

export async function fetchLevels(params: {
  search?: string;
  sort?: string;
  direction?: string;
  page?: number;
  page_size?: number;
}): Promise<LevelList> {
  const q = new URLSearchParams();
  if (params.search) q.set("search", params.search);
  if (params.sort) q.set("sort", params.sort);
  if (params.direction) q.set("direction", params.direction);
  q.set("page", String(params.page ?? 1));
  q.set("page_size", String(params.page_size ?? 25));
  const res = await fetch(`/api/levels?${q.toString()}`, { credentials: "same-origin" });
  if (!res.ok) throw new Error(`Rangliste konnte nicht geladen werden (${res.status})`);
  return res.json();
}

export async function updateLevel(
  userId: string,
  level: number,
  exp: number
): Promise<SaveResult> {
  const res = await fetch(`/api/levels/${userId}`, {
    method: "PUT",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ level, exp }),
  });
  if (res.ok) return { ok: true };
  let detail: unknown = null;
  try {
    detail = (await res.json()).detail;
  } catch {
    /* kein JSON-Body */
  }
  return { ok: false, error: typeof detail === "string" ? detail : `Fehler ${res.status}` };
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
