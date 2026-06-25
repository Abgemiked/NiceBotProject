import { useEffect, useState, type ReactNode } from "react";
import { fetchAudit, fetchStats, type AuditEvent, type AuditList, type Stats } from "./api";
import { CARD, Icon, Pager, TABLE_WRAP, TH, toast } from "./ui";

const PAGE_SIZE = 25;
const TYPE: Record<string, [string, string]> = {
  message_delete: ["Nachricht gelöscht", "#ff5470"],
  member_leave: ["Member verlassen", "#8a82a6"],
  dm_sent: ["DM gesendet", "#a24bff"],
  admin_override: ["Admin-Änderung", "#f5b544"],
};

function fmt(ts: string): string {
  const d = new Date(ts);
  return isNaN(d.getTime()) ? ts : d.toLocaleString("de-DE");
}
function detail(e: AuditEvent): string {
  if (e.content) return e.content.length > 80 ? e.content.slice(0, 80) + "…" : e.content;
  if (e.meta && typeof e.meta === "object") {
    const m = e.meta as Record<string, unknown>;
    if (m.old && m.new) return `${JSON.stringify(m.old)} → ${JSON.stringify(m.new)}`;
    if (m.changed_keys) return `Keys: ${(m.changed_keys as string[]).join(", ")}`;
    if (m.action) return String(m.action);
  }
  return "";
}

export default function AuditPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [data, setData] = useState<AuditList | null>(null);
  const [type, setType] = useState("");
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState(false);

  useEffect(() => { fetchStats().then(setStats).catch(() => setStats(null)); }, []);
  useEffect(() => {
    fetchAudit({ event_type: type || undefined, page, page_size: PAGE_SIZE })
      .then(setData).catch((e) => toast("err", String(e.message ?? e)));
  }, [type, page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const filterLabel = type ? (TYPE[type]?.[0] ?? type) : "Alle Typen";
  const options = ["", ...(data?.event_types ?? Object.keys(TYPE))];

  return (
    <div className="flex flex-col gap-5" onClick={() => setOpen(false)}>
      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-3">
        <Kpi icon={ICON.users} iconBg="rgba(162,75,255,.14)" iconColor="#c9a6ff" label="Mitglieder gesamt" value={stats?.member_count} />
        <Kpi icon={ICON.check} iconBg="rgba(53,217,160,.14)" iconColor="#35d9a0" label="Ohne Bots / Ignoriert" value={stats?.members_without_ignored} />
        <Kpi icon={ICON.log} iconBg="rgba(91,140,255,.14)" iconColor="#7ca3ff" label="Audit-Einträge" value={data?.total} />
      </div>

      <div className="flex items-center gap-2.5" onClick={(e) => e.stopPropagation()}>
        <span className="text-[13px] font-medium text-muted2">Ereignistyp</span>
        <div className="relative">
          <button onClick={() => setOpen(!open)} className="flex min-w-[190px] items-center gap-2.5 rounded-[10px] border border-line bg-surface px-3 py-2.5 transition hover:border-[#3a3358]">
            <span className="flex-1 text-left text-[13.5px] font-medium text-[#d8d2ec]">{filterLabel}</span>
            <span className="text-[#7d76a0]">{Icon.chevron}</span>
          </button>
          {open && (
            <div className="absolute left-0 top-[calc(100%+6px)] z-40 min-w-[210px] animate-fIn rounded-xl border border-[#322a4d] bg-raised p-1.5 shadow-[0_24px_48px_-16px_rgba(0,0,0,.85)]">
              {options.map((o) => {
                const [label, color] = o ? (TYPE[o] ?? [o, "#8a82a6"]) : ["Alle Typen", "#8a82a6"];
                return (
                  <button key={o || "all"} onClick={() => { setType(o); setPage(1); setOpen(false); }} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2.5 text-left hover:bg-[#241d3a]">
                    <span className="h-2 w-2 flex-none rounded-full" style={{ background: color }} />
                    <span className="flex-1 text-[13.5px] text-[#d8d2ec]">{label}</span>
                    {type === o && <span className="text-accentsoft">{Icon.check}</span>}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <div className={TABLE_WRAP}>
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-surface2">
              <th className={`${TH} w-[170px]`}>Zeit</th>
              <th className={TH}>Typ</th>
              <th className={TH}>Betroffen</th>
              <th className={TH}>Details</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((e) => {
              const [label, color] = TYPE[e.event_type] ?? [e.event_type, "#8a82a6"];
              return (
                <tr key={e.id} className="border-t border-[#201a34] align-top hover:bg-hover">
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-[#857ea6]">{fmt(e.ts)}</td>
                  <td className="px-4 py-3"><span className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold" style={{ background: color + "1e", color }}><span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />{label}</span></td>
                  <td className="px-4 py-3"><div className="text-[13.5px] text-ink">{e.target_name ?? "—"}</div>{e.actor_name && <div className="text-[11.5px] text-[#6b6390]">durch {e.actor_name}</div>}</td>
                  <td className="px-4 py-3 text-[13px] text-muted">{detail(e)}</td>
                </tr>
              );
            })}
            {data && data.items.length === 0 && <tr><td colSpan={4} className="px-4 py-12 text-center text-sm text-faint">Keine Einträge für diesen Filter.</td></tr>}
          </tbody>
        </table>
      </div>

      <Pager page={page} totalPages={totalPages} onPrev={() => setPage(page - 1)} onNext={() => setPage(page + 1)} label={`Seite ${data?.page ?? 1} / ${totalPages}`} />
    </div>
  );
}

function Kpi({ icon, iconBg, iconColor, label, value }: { icon: ReactNode; iconBg: string; iconColor: string; label: string; value?: number }) {
  return (
    <div className={`${CARD} p-[18px]`}>
      <div className="mb-3 flex items-center gap-2.5">
        <span className="flex h-[30px] w-[30px] items-center justify-center rounded-[9px]" style={{ background: iconBg, color: iconColor }}>{icon}</span>
        <span className="text-xs font-medium text-muted2">{label}</span>
      </div>
      <div className="font-sora text-[30px] font-bold tracking-tight text-ink2">{value?.toLocaleString("de-DE") ?? "—"}</div>
    </div>
  );
}

const ICON = {
  users: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="9" cy="8" r="3" /><path d="M3.5 19a5.5 5.5 0 0 1 11 0" /><path d="M16 5.5a3.2 3.2 0 0 1 0 6" /></svg>,
  check: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5L20 7" /></svg>,
  log: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12h4l2-7 4 14 2-7h4" /></svg>,
};
