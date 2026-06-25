import { useEffect, useState } from "react";
import {
  fetchStreamers,
  createStreamer,
  deleteStreamer,
  type Streamer,
} from "./api";

export default function StreamerPage({ canManage }: { canManage: boolean }) {
  const [streamers, setStreamers] = useState<Streamer[]>([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<{ kind: "ok" | "err"; msg: string } | null>(null);
  const [loaded, setLoaded] = useState(false);

  function load() {
    fetchStreamers()
      .then((s) => {
        setStreamers(s);
        setLoaded(true);
      })
      .catch((e) => {
        setStatus({ kind: "err", msg: String(e.message ?? e) });
        setLoaded(true);
      });
  }

  useEffect(load, []);

  async function onCreate() {
    if (!name.trim()) return;
    setBusy(true);
    setStatus(null);
    const res = await createStreamer(name.trim());
    setBusy(false);
    if (res.ok) {
      setStatus({ kind: "ok", msg: `Streamer „${name.trim()}" angelegt.` });
      setName("");
      load();
    } else {
      setStatus({ kind: "err", msg: res.error ?? "Anlegen fehlgeschlagen." });
    }
  }

  async function onDelete(s: Streamer) {
    if (!confirm(`Streamer „${s.name}" inkl. Kategorie, Channels und Rollen wirklich löschen?`)) {
      return;
    }
    setBusy(true);
    setStatus(null);
    const res = await deleteStreamer(s.name);
    setBusy(false);
    if (res.ok) {
      setStatus({ kind: "ok", msg: `Streamer „${s.name}" gelöscht.` });
      load();
    } else {
      setStatus({ kind: "err", msg: res.error ?? "Löschen fehlgeschlagen." });
    }
  }

  if (!loaded) return <p className="text-sm text-slate-400">Lade Streamer …</p>;

  return (
    <div className="space-y-5">
      <h2 className="text-lg font-medium">Streamer-Verwaltung</h2>

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

      {canManage && (
        <div className="flex gap-2 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Streamer-Name"
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          />
          <button
            onClick={onCreate}
            disabled={busy || !name.trim()}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            Anlegen
          </button>
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900/60 text-left text-slate-400">
            <tr>
              <th className="px-4 py-2">Streamer</th>
              <th className="px-4 py-2">Channels</th>
              {canManage && <th className="px-4 py-2" />}
            </tr>
          </thead>
          <tbody>
            {streamers.map((s) => (
              <tr key={s.category_id} className="border-t border-slate-800">
                <td className="px-4 py-2">{s.name}</td>
                <td className="px-4 py-2 text-slate-400">{s.channels}</td>
                {canManage && (
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => onDelete(s)}
                      disabled={busy}
                      className="rounded-md border border-red-900 px-2 py-1 text-xs text-red-300 hover:bg-red-900/30 disabled:opacity-50"
                    >
                      Löschen
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {streamers.length === 0 && (
              <tr>
                <td colSpan={canManage ? 3 : 2} className="px-4 py-6 text-center text-slate-500">
                  Keine Streamer angelegt.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
