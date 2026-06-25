import { useEffect, useState } from "react";
import {
  fetchLevels,
  updateLevel,
  type LevelList,
  type LevelUser,
} from "./api";

const PAGE_SIZE = 25;

export default function LevelPage({ canEdit }: { canEdit: boolean }) {
  const [data, setData] = useState<LevelList | null>(null);
  const [search, setSearch] = useState("");
  // "applied" = der tatsächlich abgeschickte Suchbegriff; treibt das Laden,
  // damit Suche und Pagination nicht in eine Race-Condition geraten.
  const [applied, setApplied] = useState("");
  const [sort, setSort] = useState("level");
  const [direction, setDirection] = useState("desc");
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<LevelUser | null>(null);

  function load() {
    fetchLevels({ search: applied, sort, direction, page, page_size: PAGE_SIZE })
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => setError(String(e.message ?? e)));
  }

  useEffect(load, [sort, direction, page, applied]);

  function onSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setApplied(search);
  }

  function toggleSort(col: string) {
    if (sort === col) setDirection(direction === "desc" ? "asc" : "desc");
    else {
      setSort(col);
      setDirection("desc");
    }
    setPage(1);
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const startRank = data ? (data.page - 1) * data.page_size : 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">Level &amp; Ränge</h2>
        <form onSubmit={onSearchSubmit} className="flex gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Name oder User-ID …"
            className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm placeholder:text-slate-600"
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
              <th className="px-4 py-2">#</th>
              <Th label="Name" col="username" sort={sort} dir={direction} onClick={toggleSort} />
              <Th label="Level" col="level" sort={sort} dir={direction} onClick={toggleSort} />
              <Th label="XP" col="exp" sort={sort} dir={direction} onClick={toggleSort} />
              {canEdit && <th className="px-4 py-2" />}
            </tr>
          </thead>
          <tbody>
            {data?.items.map((u, i) => (
              <tr key={u.user_id} className="border-t border-slate-800">
                <td className="px-4 py-2 text-slate-500">{startRank + i + 1}</td>
                <td className="px-4 py-2">
                  {u.username ?? <span className="text-slate-600">—</span>}
                  <span className="ml-2 font-mono text-xs text-slate-600">{u.user_id}</span>
                </td>
                <td className="px-4 py-2">{u.level}</td>
                <td className="px-4 py-2">{u.exp}</td>
                {canEdit && (
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => setEditing(u)}
                      className="rounded-md border border-slate-700 px-2 py-1 text-xs hover:bg-slate-800"
                    >
                      Bearbeiten
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {data && data.items.length === 0 && (
              <tr>
                <td colSpan={canEdit ? 5 : 4} className="px-4 py-6 text-center text-slate-500">
                  Keine Einträge.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm text-slate-400">
        <span>{data ? `${data.total} Nutzer` : "…"}</span>
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

      {editing && (
        <EditModal
          user={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            load();
          }}
        />
      )}
    </div>
  );
}

function Th({
  label,
  col,
  sort,
  dir,
  onClick,
}: {
  label: string;
  col: string;
  sort: string;
  dir: string;
  onClick: (c: string) => void;
}) {
  const active = sort === col;
  return (
    <th
      onClick={() => onClick(col)}
      className="cursor-pointer select-none px-4 py-2 hover:text-slate-200"
    >
      {label} {active ? (dir === "desc" ? "▼" : "▲") : ""}
    </th>
  );
}

function EditModal({
  user,
  onClose,
  onSaved,
}: {
  user: LevelUser;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [level, setLevel] = useState(String(user.level));
  const [exp, setExp] = useState(String(user.exp));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function save() {
    const lvl = Number(level.trim());
    const xp = Number(exp.trim());
    if (
      level.trim() === "" ||
      exp.trim() === "" ||
      !Number.isInteger(lvl) ||
      !Number.isInteger(xp)
    ) {
      setError("Level und XP müssen ganze Zahlen sein.");
      return;
    }
    setSaving(true);
    setError(null);
    const res = await updateLevel(user.user_id, lvl, xp);
    setSaving(false);
    if (res.ok) onSaved();
    else setError(res.error ?? "Speichern fehlgeschlagen.");
  }

  return (
    <div className="fixed inset-0 z-10 flex items-center justify-center bg-black/60 px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-700 bg-slate-900 p-5">
        <h3 className="mb-1 font-medium">
          {user.username ?? user.user_id} bearbeiten
        </h3>
        <p className="mb-4 font-mono text-xs text-slate-500">{user.user_id}</p>
        <label className="mb-1 block text-sm">Level</label>
        <input
          value={level}
          inputMode="numeric"
          onChange={(e) => setLevel(e.target.value)}
          className="mb-3 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
        />
        <label className="mb-1 block text-sm">XP</label>
        <input
          value={exp}
          inputMode="numeric"
          onChange={(e) => setExp(e.target.value)}
          className="mb-4 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
        />
        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="rounded-md border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-800">
            Abbrechen
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {saving ? "Speichert …" : "Speichern"}
          </button>
        </div>
      </div>
    </div>
  );
}
