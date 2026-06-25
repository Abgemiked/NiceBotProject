import { useEffect, useState } from "react";
import { fetchMembers, type MemberList } from "./api";

const PAGE_SIZE = 25;

export default function MemberPage() {
  const [data, setData] = useState<MemberList | null>(null);
  const [search, setSearch] = useState("");
  const [applied, setApplied] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);

  function load() {
    fetchMembers({ search: applied || undefined, page, page_size: PAGE_SIZE })
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => setError(String(e.message ?? e)));
  }

  useEffect(load, [applied, page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">Mitglieder</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setPage(1);
            setApplied(search);
          }}
          className="flex gap-2"
        >
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Name oder User-ID …"
            className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm"
          />
          <button className="rounded-md border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-800">
            Suchen
          </button>
        </form>
      </div>

      {error && <div className="rounded-md bg-red-900/40 px-3 py-2 text-sm text-red-300">{error}</div>}

      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900/60 text-left text-slate-400">
            <tr>
              <th className="px-4 py-2">Name</th>
              <th className="px-4 py-2">Rollen</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((m) => (
              <tr key={m.id} className="border-t border-slate-800 align-top">
                <td className="px-4 py-2">
                  {m.display_name}
                  <span className="ml-2 font-mono text-xs text-slate-600">{m.id}</span>
                </td>
                <td className="px-4 py-2">
                  <div className="flex flex-wrap gap-1">
                    {m.roles.map((r) => (
                      <span
                        key={r.id}
                        className="rounded bg-slate-800 px-1.5 py-0.5 text-xs text-slate-300"
                      >
                        {r.name}
                      </span>
                    ))}
                    {m.roles.length === 0 && <span className="text-xs text-slate-600">—</span>}
                  </div>
                </td>
              </tr>
            ))}
            {data && data.items.length === 0 && (
              <tr>
                <td colSpan={2} className="px-4 py-6 text-center text-slate-500">
                  Keine Mitglieder.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm text-slate-400">
        <span>{data ? `${data.total} Mitglieder` : "…"}</span>
        <div className="flex items-center gap-3">
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
    </div>
  );
}
