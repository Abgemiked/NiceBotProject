import { useEffect, useState } from "react";
import { fetchLevels, updateLevel, type LevelList, type LevelUser } from "./api";
import { Avatar, BTN_PRIMARY, BTN_SECONDARY, Icon, INPUT, Pager, TABLE_WRAP, TH, toast } from "./ui";

const PAGE_SIZE = 25;

export default function LevelPage({ canEdit }: { canEdit: boolean }) {
  const [data, setData] = useState<LevelList | null>(null);
  const [search, setSearch] = useState("");
  const [applied, setApplied] = useState("");
  const [sort, setSort] = useState("level");
  const [direction, setDirection] = useState("desc");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<LevelUser | null>(null);

  function load() {
    fetchLevels({ search: applied || undefined, sort, direction, page, page_size: PAGE_SIZE })
      .then(setData).catch((e) => toast("err", String(e.message ?? e)));
  }
  useEffect(load, [sort, direction, page, applied]);

  function toggleSort(col: string) {
    if (sort === col) setDirection(direction === "desc" ? "asc" : "desc");
    else { setSort(col); setDirection("desc"); }
    setPage(1);
  }
  const arrow = (c: string) => (sort === c ? (direction === "desc" ? " ↓" : " ↑") : "");
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const startRank = data ? (data.page - 1) * data.page_size : 0;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <form onSubmit={(e) => { e.preventDefault(); setPage(1); setApplied(search); }} className="relative w-80 max-w-full">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#6f688c]">{Icon.search}</span>
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Nutzer oder ID suchen…"
            className={`${INPUT} bg-surface !border-line pl-10`} />
        </form>
        <span className="font-mono text-xs text-[#857ea6]">
          {data ? (data.total === 0 ? "0 Einträge" : `${startRank + 1}–${startRank + data.items.length} von ${data.total}`) : "…"}
        </span>
      </div>

      <div className={TABLE_WRAP}>
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-surface2">
              <th className={`${TH} w-14`}>#</th>
              <th className={TH}><button onClick={() => toggleSort("username")} className="text-inherit hover:text-accentsoft">NUTZER{arrow("username")}</button></th>
              <th className={TH}>Fortschritt</th>
              <th className={`${TH} text-right`}><button onClick={() => toggleSort("level")} className="hover:text-accentsoft">LEVEL{arrow("level")}</button></th>
              <th className={`${TH} text-right`}><button onClick={() => toggleSort("exp")} className="hover:text-accentsoft">EXP{arrow("exp")}</button></th>
              {canEdit && <th className="w-14" />}
            </tr>
          </thead>
          <tbody>
            {data?.items.map((u, i) => {
              const need = (u.level + 1) * 1000;
              const cur = u.exp % need;
              const pct = Math.max(6, Math.round((cur / need) * 100));
              return (
                <tr key={u.user_id} className="border-t border-[#201a34] hover:bg-hover">
                  <td className="px-4 py-3 font-mono text-[13px] text-faint">{startRank + i + 1}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <Avatar seed={u.user_id} label={u.username ?? "?"} />
                      <div className="min-w-0">
                        <div className="text-sm font-semibold text-ink">{u.username ?? "—"}</div>
                        <div className="font-mono text-[10.5px] text-[#6b6390]">{u.user_id}</div>
                      </div>
                    </div>
                  </td>
                  <td className="w-[200px] px-4 py-3">
                    <div className="h-[7px] overflow-hidden rounded-[4px] bg-[#221c38]"><div className="h-full rounded-[4px] bg-[linear-gradient(90deg,#8b45ff,#d846c9)]" style={{ width: pct + "%" }} /></div>
                    <div className="mt-1.5 font-mono text-[10px] text-[#6b6390]">{cur.toLocaleString("de-DE")} / {need.toLocaleString("de-DE")} EXP</div>
                  </td>
                  <td className="px-4 py-3 text-right"><span className="inline-block min-w-[32px] rounded-lg bg-[rgba(162,75,255,.14)] px-2.5 py-1 text-center font-sora text-[13px] font-bold text-accentsoft">{u.level}</span></td>
                  <td className="px-4 py-3 text-right font-mono text-[13px] text-[#b3aacb]">{u.exp.toLocaleString("de-DE")}</td>
                  {canEdit && (
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => setEditing(u)} title="Bearbeiten" className="inline-flex h-8 w-8 items-center justify-center rounded-[9px] border border-[#2c2546] text-[#928bb0] transition hover:border-accent hover:bg-[rgba(162,75,255,.14)] hover:text-accentsoft">{Icon.edit}</button>
                    </td>
                  )}
                </tr>
              );
            })}
            {data && data.items.length === 0 && <tr><td colSpan={canEdit ? 6 : 5} className="px-4 py-12 text-center text-sm text-faint">Keine Treffer.</td></tr>}
          </tbody>
        </table>
      </div>

      <Pager page={page} totalPages={totalPages} onPrev={() => setPage(page - 1)} onNext={() => setPage(page + 1)} label={`Seite ${data?.page ?? 1} / ${totalPages}`} />

      {editing && <EditModal user={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />}
    </div>
  );
}

function EditModal({ user, onClose, onSaved }: { user: LevelUser; onClose: () => void; onSaved: () => void }) {
  const [level, setLevel] = useState(String(user.level));
  const [exp, setExp] = useState(String(user.exp));
  const [saving, setSaving] = useState(false);
  const FIELD = "w-full rounded-[10px] border border-line2 bg-input px-3 py-3 font-mono text-[15px] font-semibold text-ink outline-none focus:border-accent focus:shadow-[0_0_0_3px_rgba(162,75,255,.16)]";

  async function save() {
    const lvl = Number(level.trim()), xp = Number(exp.trim());
    if (level.trim() === "" || exp.trim() === "" || !Number.isInteger(lvl) || !Number.isInteger(xp)) {
      toast("err", "Level und EXP müssen ganze Zahlen sein."); return;
    }
    setSaving(true);
    const res = await updateLevel(user.user_id, lvl, xp);
    setSaving(false);
    if (res.ok) { toast("ok", `Level für ${user.username ?? "Nutzer"} aktualisiert.`); onSaved(); }
    else toast("err", res.error ?? "Speichern fehlgeschlagen.");
  }

  return (
    <div onClick={onClose} className="fixed inset-0 z-[60] flex animate-[fIn_.15s_ease] items-center justify-center bg-[rgba(6,4,14,.74)] p-6 backdrop-blur-sm">
      <div onClick={(e) => e.stopPropagation()} className="w-[420px] max-w-full animate-mIn overflow-hidden rounded-[20px] border border-[#2c2546] bg-surface shadow-[0_50px_100px_-30px_rgba(0,0,0,.9)]">
        <div className="flex items-center justify-between border-b border-[#221c38] px-5 py-5">
          <div className="flex items-center gap-3">
            <Avatar seed={user.user_id} label={user.username ?? "?"} size={38} />
            <div><div className="font-sora text-base font-bold text-ink2">{user.username ?? "—"}</div><div className="font-mono text-[10.5px] text-[#6b6390]">{user.user_id}</div></div>
          </div>
          <button onClick={onClose} className="flex h-8 w-8 items-center justify-center rounded-[9px] bg-[#1c1730] text-[#928bb0] transition hover:bg-[#241d3a] hover:text-ink">{Icon.x}</button>
        </div>
        <div className="flex flex-col gap-4 p-5">
          <div><label className="mb-1.5 block text-[12.5px] font-semibold text-muted">Level</label><input value={level} inputMode="numeric" onChange={(e) => setLevel(e.target.value)} className={FIELD} /></div>
          <div><label className="mb-1.5 block text-[12.5px] font-semibold text-muted">EXP</label><input value={exp} inputMode="numeric" onChange={(e) => setExp(e.target.value)} className={FIELD} /></div>
        </div>
        <div className="flex justify-end gap-2.5 px-5 pb-5">
          <button onClick={onClose} className={BTN_SECONDARY}>Abbrechen</button>
          <button onClick={save} disabled={saving} className={BTN_PRIMARY}>{saving ? "Speichert …" : "Speichern"}</button>
        </div>
      </div>
    </div>
  );
}
