import { useEffect, useState } from "react";
import {
  fetchAudit,
  fetchStats,
  type AuditList,
  type Stats,
} from "./api";

const PAGE_SIZE = 25;

const TYPE_LABEL: Record<string, string> = {
  message_delete: "Nachricht gelöscht",
  member_leave: "Member verlassen",
  dm_sent: "DM gesendet",
  admin_override: "Admin-Änderung",
};

export default function AuditPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [data, setData] = useState<AuditList | null>(null);
  const [type, setType] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStats().then(setStats).catch(() => setStats(null));
  }, []);

  useEffect(() => {
    fetchAudit({ event_type: type || undefined, page, page_size: PAGE_SIZE })
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => setError(String(e.message ?? e)));
  }, [type, page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-medium">Logs &amp; Statistiken</h2>

      {/* Statistik-Karten */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Mitglieder gesamt" value={stats?.member_count} />
        <StatCard label="Ohne Bots/Ignoriert" value={stats?.members_without_ignored} />
        <StatCard label="Audit-Einträge" value={data?.total} />
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-slate-400">Typ:</span>
        <select
          value={type}
          onChange={(e) => {
            setType(e.target.value);
            setPage(1);
          }}
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm"
        >
          <option value="">Alle</option>
          {(data?.event_types ?? Object.keys(TYPE_LABEL)).map((t) => (
            <option key={t} value={t}>
              {TYPE_LABEL[t] ?? t}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="rounded-md bg-red-900/40 px-3 py-2 text-sm text-red-300">{error}</div>}

      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900/60 text-left text-slate-400">
            <tr>
              <th className="px-4 py-2">Zeit</th>
              <th className="px-4 py-2">Typ</th>
              <th className="px-4 py-2">Betroffen</th>
              <th className="px-4 py-2">Details</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((e) => (
              <tr key={e.id} className="border-t border-slate-800 align-top">
                <td className="whitespace-nowrap px-4 py-2 text-slate-400">{fmt(e.ts)}</td>
                <td className="px-4 py-2">{TYPE_LABEL[e.event_type] ?? e.event_type}</td>
                <td className="px-4 py-2">
                  {e.target_name ?? "—"}
                  {e.actor_name && (
                    <span className="block text-xs text-slate-500">durch {e.actor_name}</span>
                  )}
                </td>
                <td className="px-4 py-2 text-slate-400">{detail(e)}</td>
              </tr>
            ))}
            {data && data.items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                  Keine Einträge.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-end gap-3 text-sm text-slate-400">
        <button
          disabled={page <= 1}
          onClick={() => setPage(page - 1)}
          className="rounded-md border border-slate-700 px-3 py-1 disabled:opacity-40"
        >
          Zurück
        </button>
        <span>
          Seite {data?.page ?? 1} / {totalPages}
        </span>
        <button
          disabled={page >= totalPages}
          onClick={() => setPage(page + 1)}
          className="rounded-md border border-slate-700 px-3 py-1 disabled:opacity-40"
        >
          Weiter
        </button>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value?: number }) {
  return (
    <div className="rounded-xl border border-slate-800 p-4">
      <div className="text-2xl font-semibold">{value ?? "—"}</div>
      <div className="text-xs text-slate-400">{label}</div>
    </div>
  );
}

function fmt(ts: string): string {
  const d = new Date(ts);
  return isNaN(d.getTime()) ? ts : d.toLocaleString("de-DE");
}

function detail(e: { content: string | null; meta: unknown }): string {
  if (e.content) return e.content.length > 80 ? e.content.slice(0, 80) + "…" : e.content;
  if (e.meta && typeof e.meta === "object") {
    const m = e.meta as Record<string, unknown>;
    if (m.old && m.new) return `${JSON.stringify(m.old)} → ${JSON.stringify(m.new)}`;
  }
  return "";
}
