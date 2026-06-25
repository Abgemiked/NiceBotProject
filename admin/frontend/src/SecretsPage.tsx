import { useEffect, useState } from "react";
import { fetchSecrets, saveSecrets, type SecretEntry } from "./api";

export default function SecretsPage() {
  const [secrets, setSecrets] = useState<SecretEntry[]>([]);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [reveal, setReveal] = useState<Record<string, boolean>>({});
  const [status, setStatus] = useState<{ kind: "ok" | "err"; msg: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  function load() {
    fetchSecrets()
      .then((s) => {
        setSecrets(s);
        const d: Record<string, string> = {};
        for (const e of s) d[e.key] = e.value;
        setDraft(d);
        setLoaded(true);
      })
      .catch((e) => {
        setStatus({ kind: "err", msg: String(e.message ?? e) });
        setLoaded(true);
      });
  }

  useEffect(load, []);

  async function onSave() {
    const updates: Record<string, string> = {};
    for (const e of secrets) {
      if (draft[e.key] !== e.value && draft[e.key]?.trim()) updates[e.key] = draft[e.key];
    }
    if (Object.keys(updates).length === 0) {
      setStatus({ kind: "err", msg: "Keine Änderungen." });
      return;
    }
    setSaving(true);
    setStatus(null);
    const res = await saveSecrets(updates);
    setSaving(false);
    if (res.ok) {
      setStatus({
        kind: "ok",
        msg: `Gespeichert: ${res.updated?.join(", ")}.${
          res.restartRequired ? " Bot-Neustart nötig, damit die Änderung greift." : ""
        }`,
      });
      load();
    } else {
      setStatus({ kind: "err", msg: res.error ?? "Speichern fehlgeschlagen." });
    }
  }

  if (!loaded) return <p className="text-sm text-slate-400">Lade Secrets …</p>;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">Secrets</h2>
        <button
          onClick={onSave}
          disabled={saving}
          className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {saving ? "Speichert …" : "Speichern"}
        </button>
      </div>

      <p className="text-xs text-slate-500">
        Laufzeit-Secrets aus der <span className="font-mono">.env</span>. Standardmäßig verborgen —
        zum Anzeigen das Augen-Symbol drücken. Änderungen wirken erst nach Bot-Neustart.
      </p>

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

      <div className="space-y-3">
        {secrets.map((e) => (
          <div key={e.key} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
            <label className="mb-1.5 flex items-center justify-between">
              <span className="text-sm font-medium">{e.label}</span>
              <span className="font-mono text-[10px] text-slate-600">
                {e.key} · {e.set ? "gesetzt" : "nicht gesetzt"}
              </span>
            </label>
            <div className="flex gap-2">
              <input
                type={reveal[e.key] ? "text" : "password"}
                value={draft[e.key] ?? ""}
                autoComplete="off"
                onChange={(ev) => setDraft({ ...draft, [e.key]: ev.target.value })}
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm"
              />
              <button
                type="button"
                onClick={() => setReveal({ ...reveal, [e.key]: !reveal[e.key] })}
                title={reveal[e.key] ? "Verbergen" : "Anzeigen"}
                className="rounded-md border border-slate-700 px-3 hover:bg-slate-800"
              >
                {reveal[e.key] ? "🙈" : "👁"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
