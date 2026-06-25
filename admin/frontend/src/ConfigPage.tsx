import { useEffect, useMemo, useState } from "react";
import {
  fetchConfig,
  fetchChannels,
  fetchRoles,
  saveConfig,
  type ConfigField,
  type ConfigResponse,
  type DiscordChannel,
  type DiscordRole,
} from "./api";

const MASK = "••••••••";
const GROUP_ORDER = ["Channels", "Filter", "Rollen", "Secrets"];

function toText(field: ConfigField, value: unknown): string {
  if (value === null || value === undefined) return "";
  if (field.type === "idlist" || field.type === "hostlist") {
    return Array.isArray(value) ? value.join(", ") : String(value);
  }
  return String(value);
}

function fromText(field: ConfigField, text: string): unknown {
  if (field.type === "idlist" || field.type === "hostlist") {
    return text
      .split(/[\s,;/]+/)
      .map((s) => s.trim())
      .filter(Boolean);
  }
  return text.trim();
}

function channelsForKind(kind: string | undefined, channels: DiscordChannel[]) {
  if (kind === "voice") return channels.filter((c) => c.type.includes("voice"));
  if (kind === "category") return channels.filter((c) => c.type === "category");
  return channels.filter((c) => ["text", "news", "forum", "announcement"].includes(c.type));
}

export default function ConfigPage() {
  const [data, setData] = useState<ConfigResponse | null>(null);
  const [channels, setChannels] = useState<DiscordChannel[]>([]);
  const [roles, setRoles] = useState<DiscordRole[]>([]);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [tab, setTab] = useState("Channels");
  const [status, setStatus] = useState<{ kind: "ok" | "err"; msg: string } | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  function load() {
    fetchConfig()
      .then((d) => {
        setData(d);
        const init: Record<string, string> = {};
        for (const f of d.fields) init[f.key] = toText(f, d.values[f.key]);
        setDraft(init);
      })
      .catch((e) => setStatus({ kind: "err", msg: String(e.message ?? e) }));
  }

  useEffect(() => {
    load();
    fetchChannels().then(setChannels).catch(() => setChannels([]));
    fetchRoles().then(setRoles).catch(() => setRoles([]));
  }, []);

  const groups = useMemo(() => {
    const g: Record<string, ConfigField[]> = {};
    for (const f of data?.fields ?? []) (g[f.group] ??= []).push(f);
    return g;
  }, [data]);

  const tabs = GROUP_ORDER.filter((g) => groups[g]?.length);

  if (!data) {
    return <p className="text-sm text-slate-400">{status?.msg ?? "Lade Konfiguration …"}</p>;
  }

  async function onSave() {
    if (!data) return;
    setSaving(true);
    setStatus(null);
    setFieldErrors({});
    const updates: Record<string, unknown> = {};
    for (const f of data.fields) {
      if (!f.editable) continue;
      const original = toText(f, data.values[f.key]);
      if (draft[f.key] !== original) updates[f.key] = fromText(f, draft[f.key]);
    }
    if (Object.keys(updates).length === 0) {
      setSaving(false);
      setStatus({ kind: "err", msg: "Keine Änderungen." });
      return;
    }
    const res = await saveConfig(updates);
    setSaving(false);
    if (res.ok) {
      setStatus({ kind: "ok", msg: `Gespeichert: ${res.updated?.join(", ")}` });
      load();
    } else if (res.fieldErrors) {
      setFieldErrors(res.fieldErrors);
      setStatus({ kind: "err", msg: "Bitte markierte Felder korrigieren." });
    } else {
      setStatus({ kind: "err", msg: res.error ?? "Speichern fehlgeschlagen." });
    }
  }

  const activeFields = groups[tab] ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">Bot-Konfiguration</h2>
        <button
          onClick={onSave}
          disabled={saving}
          className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {saving ? "Speichert …" : "Speichern"}
        </button>
      </div>

      {status && (
        <div
          className={`rounded-md px-3 py-2 text-sm ${
            status.kind === "ok"
              ? "bg-emerald-900/40 text-emerald-300"
              : "bg-red-900/40 text-red-300"
          }`}
        >
          {status.msg}
        </div>
      )}

      {/* Gruppen-Tabs */}
      <div className="flex gap-1 border-b border-slate-800">
        {tabs.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm ${
              tab === t
                ? "border-indigo-500 text-slate-100"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {activeFields.map((f) => (
          <Field
            key={f.key}
            field={f}
            value={draft[f.key] ?? ""}
            error={fieldErrors[f.key]}
            restart={data.restart_required_keys.includes(f.key)}
            canViewSecrets={data.can_view_secrets}
            channels={channels}
            roles={roles}
            onChange={(v) => setDraft({ ...draft, [f.key]: v })}
          />
        ))}
      </div>
    </div>
  );
}

function Field({
  field,
  value,
  error,
  restart,
  canViewSecrets,
  channels,
  roles,
  onChange,
}: {
  field: ConfigField;
  value: string;
  error?: string;
  restart: boolean;
  canViewSecrets: boolean;
  channels: DiscordChannel[];
  roles: DiscordRole[];
  onChange: (v: string) => void;
}) {
  const masked = field.secret && !canViewSecrets;
  const kind = field.kind;
  const isChannel = kind === "channel" || kind === "voice" || kind === "category";
  const isRole = kind === "role";
  const isRoleList = kind === "rolelist";
  const multiline = field.type === "idlist" || field.type === "hostlist";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
      <label className="mb-1.5 flex items-center justify-between">
        <span className="text-sm font-medium">{field.label}</span>
        <span className="font-mono text-[10px] text-slate-600">{field.key}</span>
      </label>

      {masked ? (
        <input
          value={MASK}
          disabled
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm opacity-60"
        />
      ) : isChannel && channels.length > 0 ? (
        <Picker
          value={value}
          options={channelsForKind(kind, channels).map((c) => ({ id: c.id, name: "#" + c.name }))}
          disabled={!field.editable}
          onChange={onChange}
        />
      ) : isRole && roles.length > 0 ? (
        <Picker
          value={value}
          options={roles.map((r) => ({ id: r.id, name: "@" + r.name }))}
          disabled={!field.editable}
          onChange={onChange}
        />
      ) : isRoleList && roles.length > 0 ? (
        <MultiPicker
          value={value}
          options={roles.map((r) => ({ id: r.id, name: "@" + r.name }))}
          disabled={!field.editable}
          onChange={onChange}
        />
      ) : multiline ? (
        <textarea
          rows={2}
          value={value}
          disabled={!field.editable}
          placeholder={kind === "hostlist" ? "tenor.com, klipy.com, giphy.com" : "123, 456"}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm placeholder:text-slate-600 disabled:opacity-60"
        />
      ) : (
        <input
          type="text"
          value={value}
          disabled={!field.editable}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm disabled:opacity-60"
        />
      )}

      {kind === "hostlist" && !error && (
        <p className="mt-1 text-xs text-slate-500">
          Mehrere durch Komma, Leerzeichen oder Zeilenumbruch trennen.
        </p>
      )}
      {isRoleList && roles.length > 0 && !error && (
        <p className="mt-1 text-xs text-slate-500">Mehrfachauswahl möglich.</p>
      )}
      {restart && (
        <p className="mt-1 text-xs text-amber-400">Änderung wirkt erst nach Bot-Neustart.</p>
      )}
      {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
    </div>
  );
}

function MultiPicker({
  value,
  options,
  disabled,
  onChange,
}: {
  value: string;
  options: { id: string; name: string }[];
  disabled: boolean;
  onChange: (v: string) => void;
}) {
  const selected = new Set(
    value
      .split(/[\s,;]+/)
      .map((s) => s.trim())
      .filter(Boolean)
  );
  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange(Array.from(next).join(", "));
  }
  const unknown = Array.from(selected).filter((id) => !options.some((o) => o.id === id));
  return (
    <div className="max-h-44 space-y-1 overflow-y-auto rounded-md border border-slate-700 bg-slate-950 p-2">
      {options.map((o) => (
        <label key={o.id} className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={selected.has(o.id)}
            disabled={disabled}
            onChange={() => toggle(o.id)}
          />
          <span>{o.name}</span>
        </label>
      ))}
      {unknown.map((id) => (
        <label key={id} className="flex items-center gap-2 text-sm text-slate-500">
          <input type="checkbox" checked disabled={disabled} onChange={() => toggle(id)} />
          <span>ID {id} (unbekannt)</span>
        </label>
      ))}
    </div>
  );
}

function Picker({
  value,
  options,
  disabled,
  onChange,
}: {
  value: string;
  options: { id: string; name: string }[];
  disabled: boolean;
  onChange: (v: string) => void;
}) {
  const known = options.some((o) => o.id === value);
  return (
    <select
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm disabled:opacity-60"
    >
      <option value="">— nicht gesetzt —</option>
      {options.map((o) => (
        <option key={o.id} value={o.id}>
          {o.name}
        </option>
      ))}
      {value && !known && <option value={value}>ID {value} (unbekannt)</option>}
    </select>
  );
}
