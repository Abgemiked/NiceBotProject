import { useEffect, useMemo, useState } from "react";
import {
  fetchConfig,
  saveConfig,
  type ConfigField,
  type ConfigResponse,
} from "./api";

const MASK = "••••••••";

/** Wandelt einen Feldwert in die Anzeige-/Editierform (string) um. */
function toText(field: ConfigField, value: unknown): string {
  if (value === null || value === undefined) return "";
  if (field.type === "idlist" || field.type === "hostlist") {
    return Array.isArray(value) ? value.join(", ") : String(value);
  }
  return String(value);
}

/** Parst die Editierform zurück in den API-Wert. */
function fromText(field: ConfigField, text: string): unknown {
  if (field.type === "idlist" || field.type === "hostlist") {
    return text
      .split(/[,\n]/)
      .map((s) => s.trim())
      .filter(Boolean);
  }
  return text.trim();
}

export default function ConfigPage() {
  const [data, setData] = useState<ConfigResponse | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
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

  useEffect(load, []);

  const groups = useMemo(() => {
    const g: Record<string, ConfigField[]> = {};
    for (const f of data?.fields ?? []) (g[f.group] ??= []).push(f);
    return g;
  }, [data]);

  if (!data) {
    return <p className="text-sm text-slate-400">{status?.msg ?? "Lade Konfiguration …"}</p>;
  }

  async function onSave() {
    if (!data) return;
    setSaving(true);
    setStatus(null);
    setFieldErrors({});
    // Nur geänderte, editierbare Felder senden.
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

      {Object.entries(groups).map(([group, fields]) => (
        <section key={group} className="rounded-xl border border-slate-800 p-5">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            {group}
          </h3>
          <div className="space-y-3">
            {fields.map((f) => {
              const masked = f.secret && !data.can_view_secrets;
              const value = masked ? MASK : draft[f.key] ?? "";
              const multiline = f.type === "idlist" || f.type === "hostlist";
              return (
                <div key={f.key}>
                  <label className="mb-1 flex items-center justify-between text-sm">
                    <span>{f.label}</span>
                    <span className="font-mono text-xs text-slate-600">{f.key}</span>
                  </label>
                  {multiline ? (
                    <textarea
                      rows={2}
                      value={value}
                      disabled={!f.editable}
                      onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value })}
                      className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm disabled:opacity-60"
                    />
                  ) : (
                    <input
                      type="text"
                      value={value}
                      disabled={!f.editable}
                      onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value })}
                      className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm disabled:opacity-60"
                    />
                  )}
                  {data.restart_required_keys.includes(f.key) && (
                    <p className="mt-1 text-xs text-amber-400">
                      Änderung wirkt erst nach Bot-Neustart.
                    </p>
                  )}
                  {fieldErrors[f.key] && (
                    <p className="mt-1 text-xs text-red-400">{fieldErrors[f.key]}</p>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
