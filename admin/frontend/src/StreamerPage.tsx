import { useEffect, useState } from "react";
import { fetchStreamers, createStreamer, deleteStreamer, type Streamer } from "./api";
import { Avatar, BTN_PRIMARY, CARD, Icon, toast } from "./ui";

export default function StreamerPage({ canManage }: { canManage: boolean }) {
  const [streamers, setStreamers] = useState<Streamer[]>([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  function load() {
    fetchStreamers().then((s) => { setStreamers(s); setLoaded(true); })
      .catch((e) => { toast("err", String(e.message ?? e)); setLoaded(true); });
  }
  useEffect(load, []);

  async function onCreate() {
    if (!name.trim()) return;
    setBusy(true);
    const res = await createStreamer(name.trim());
    setBusy(false);
    if (res.ok) { toast("ok", `Streamer „${name.trim()}" angelegt.`); setName(""); load(); }
    else toast("err", res.error ?? "Anlegen fehlgeschlagen.");
  }
  async function onDelete(s: Streamer) {
    if (!confirm(`Streamer „${s.name}" inkl. Kategorie, Channels und Rollen wirklich löschen?`)) return;
    setBusy(true);
    const res = await deleteStreamer(s.name);
    setBusy(false);
    if (res.ok) { toast("ok", `Streamer „${s.name}" entfernt.`); load(); }
    else toast("err", res.error ?? "Löschen fehlgeschlagen.");
  }

  if (!loaded) return <p className="text-sm text-muted">Lade Streamer …</p>;

  return (
    <div className="flex flex-col gap-[18px]">
      {canManage && (
        <div className={`${CARD} p-[18px]`}>
          <div className="mb-[11px] text-[13.5px] font-semibold text-[#e7e3f4]">Streamer hinzufügen</div>
          <div className="flex gap-2.5">
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Twitch-Name, z. B. abgemiked"
              className="flex-1 rounded-[10px] border border-line2 bg-input px-3 py-2.5 text-sm font-medium text-ink outline-none focus:border-accent focus:shadow-[0_0_0_3px_rgba(162,75,255,.16)]" />
            <button onClick={onCreate} disabled={busy || !name.trim()} className={BTN_PRIMARY}>{Icon.plus}Anlegen</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {streamers.map((s) => (
          <div key={s.category_id} className="flex items-center gap-3.5 rounded-[14px] border border-line bg-surface p-3.5 transition hover:border-[#322a4d]">
            <Avatar seed={s.name} label={s.name} size={42} />
            <div className="min-w-0 flex-1">
              <div className="text-[14.5px] font-semibold text-ink">{s.name}</div>
              <div className="mt-0.5 font-mono text-[10.5px] text-[#6b6390]">{s.channels} Channels · cat {s.category_id}</div>
            </div>
            {canManage && (
              <button onClick={() => onDelete(s)} disabled={busy} title="Entfernen" className="flex h-8 w-8 flex-none items-center justify-center rounded-[9px] border border-[#2c2546] text-[#928bb0] transition hover:border-danger hover:bg-[rgba(255,84,112,.14)] hover:text-danger2 disabled:opacity-50">{Icon.trash}</button>
            )}
          </div>
        ))}
      </div>
      {streamers.length === 0 && (
        <div className="rounded-2xl border border-dashed border-[#2c2546] bg-surface p-12 text-center text-sm text-faint">Noch keine Streamer angelegt.</div>
      )}
    </div>
  );
}
