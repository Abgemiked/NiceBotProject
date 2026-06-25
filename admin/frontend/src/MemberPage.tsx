import { useEffect, useState } from "react";
import { fetchMembers, type MemberList } from "./api";
import { Avatar, Icon, INPUT, Pager, roleColor, TABLE_WRAP, TH, toast } from "./ui";

const PAGE_SIZE = 25;

export default function MemberPage() {
  const [data, setData] = useState<MemberList | null>(null);
  const [search, setSearch] = useState("");
  const [applied, setApplied] = useState("");
  const [page, setPage] = useState(1);

  function load() {
    fetchMembers({ search: applied || undefined, page, page_size: PAGE_SIZE })
      .then(setData).catch((e) => toast("err", String(e.message ?? e)));
  }
  useEffect(load, [applied, page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <form onSubmit={(e) => { e.preventDefault(); setPage(1); setApplied(search); }} className="relative w-[340px] max-w-full">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#6f688c]">{Icon.search}</span>
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Name oder ID suchen…" className={`${INPUT} bg-surface !border-line pl-10`} />
        </form>
        <span className="font-mono text-xs text-[#857ea6]">{data ? `${data.total} Mitglieder` : "…"}</span>
      </div>

      <div className={TABLE_WRAP}>
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-surface2">
              <th className={TH}>Mitglied</th>
              <th className={TH}>Rollen</th>
              <th className={`${TH} text-right`}>Discord-ID</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((m) => {
              const shown = m.roles.slice(0, 4);
              const more = m.roles.length - shown.length;
              return (
                <tr key={m.id} className="border-t border-[#201a34] align-top hover:bg-hover">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <Avatar seed={m.id} label={m.display_name} />
                      <div className="min-w-0"><div className="text-sm font-semibold text-ink">{m.display_name}</div><div className="font-mono text-[10.5px] text-[#6b6390]">@{m.name}</div></div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1.5">
                      {shown.map((r) => {
                        const c = roleColor(r.name);
                        return (
                          <span key={r.id} className="inline-flex items-center gap-1.5 rounded-md border px-2 py-[3px] text-xs font-semibold" style={{ background: c + "1e", borderColor: c + "3a", color: c }}>
                            <span className="h-1.5 w-1.5 rounded-full" style={{ background: c }} />{r.name}
                          </span>
                        );
                      })}
                      {more > 0 && <span className="rounded-md bg-[#221c38] px-2 py-[3px] text-xs font-semibold text-[#857ea6]">+{more}</span>}
                      {m.roles.length === 0 && <span className="text-xs text-faint">—</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs text-faint">{m.id}</td>
                </tr>
              );
            })}
            {data && data.items.length === 0 && <tr><td colSpan={3} className="px-4 py-12 text-center text-sm text-faint">Keine Mitglieder gefunden.</td></tr>}
          </tbody>
        </table>
      </div>

      <Pager page={page} totalPages={totalPages} onPrev={() => setPage(page - 1)} onNext={() => setPage(page + 1)} label={`Seite ${data?.page ?? 1} / ${totalPages}`} />
    </div>
  );
}
