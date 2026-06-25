import { useEffect, useState } from "react";
import { fetchSecrets, saveSecrets, type SecretEntry } from "./api";
import { BTN_PRIMARY, CARD, Icon, toast } from "./ui";

const EyeOn = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" /><circle cx="12" cy="12" r="3" /></svg>
);
const EyeOff = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3l18 18" /><path d="M10.6 6.1A9 9 0 0 1 12 6c6 0 9.5 6 9.5 6a16 16 0 0 1-2.8 3.3" /><path d="M6.6 6.6A15 15 0 0 0 2.5 12S6 18 12 18a8.6 8.6 0 0 0 3.3-.6" /></svg>
);

export default function SecretsPage() {
  const [secrets, setSecrets] = useState<SecretEntry[]>([]);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [reveal, setReveal] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  function load() {
    fetchSecrets().then((s) => {
      setSecrets(s);
      const d: Record<string, string> = {};
      for (const e of s) d[e.key] = e.value;
      setDraft(d); setLoaded(true);
    }).catch((e) => { toast("err", String(e.message ?? e)); setLoaded(true); });
  }
  useEffect(load, []);

  async function onSave() {
    const updates: Record<string, string> = {};
    for (const e of secrets) if (draft[e.key] !== e.value && draft[e.key]?.trim()) updates[e.key] = draft[e.key];
    if (Object.keys(updates).length === 0) { toast("err", "Keine Änderungen."); return; }
    setSaving(true);
    const res = await saveSecrets(updates);
    setSaving(false);
    if (res.ok) { toast("ok", `Gespeichert.${res.restartRequired ? " Bot-Neustart nötig." : ""}`); load(); }
    else toast("err", res.error ?? "Speichern fehlgeschlagen.");
  }

  if (!loaded) return <p className="text-sm text-muted">Lade Secrets …</p>;

  return (
    <div className="flex flex-col gap-3.5">
      <div className="flex items-center justify-end">
        <button onClick={onSave} disabled={saving} className={BTN_PRIMARY}>{Icon.check}{saving ? "Speichert …" : "Speichern"}</button>
      </div>

      <div className="flex items-start gap-3 rounded-[14px] border border-[rgba(245,181,68,.22)] bg-[rgba(245,181,68,.08)] px-4 py-3.5">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F5B544" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mt-0.5 flex-none"><path d="M12 9v4" /><path d="M12 17h.01" /><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /></svg>
        <div className="text-[13px] leading-relaxed text-[#d8c9a8]">Laufzeit-Secrets aus der <span className="font-mono text-[#f5c97a]">.env</span>. Standardmäßig verborgen — zum Anzeigen das Augen-Symbol nutzen. Änderungen wirken erst nach <b className="font-semibold text-[#f5c97a]">Bot-Neustart</b>.</div>
      </div>

      {secrets.map((e) => (
        <div key={e.key} className={`${CARD} p-4`}>
          <div className="mb-2.5 flex items-center justify-between gap-2.5">
            <span className="text-[13.5px] font-semibold text-[#e7e3f4]">{e.label}</span>
            <span className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-[#5a5379]">{e.key}</span>
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold" style={{ color: e.set ? "#35d9a0" : "#8a82a6" }}>
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: e.set ? "#35d9a0" : "#8a82a6" }} />{e.set ? "gesetzt" : "nicht gesetzt"}
              </span>
            </span>
          </div>
          <div className="flex gap-2.5">
            <input type={reveal[e.key] ? "text" : "password"} value={draft[e.key] ?? ""} autoComplete="off" onChange={(ev) => setDraft({ ...draft, [e.key]: ev.target.value })}
              className="flex-1 rounded-[10px] border border-line2 bg-input px-3 py-2.5 font-mono text-[13px] tracking-wide text-ink outline-none focus:border-accent focus:shadow-[0_0_0_3px_rgba(162,75,255,.16)]" />
            <button type="button" onClick={() => setReveal({ ...reveal, [e.key]: !reveal[e.key] })} title={reveal[e.key] ? "Verbergen" : "Anzeigen"}
              className="flex w-[42px] flex-none items-center justify-center rounded-[10px] border border-[#2c2546] bg-input text-[#928bb0] transition hover:border-accent hover:bg-[#1c1730] hover:text-accentsoft">
              {reveal[e.key] ? EyeOff : EyeOn}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
