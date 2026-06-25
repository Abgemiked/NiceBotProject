import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  fetchConfig, fetchChannels, fetchRoles, saveConfig,
  type ConfigField, type ConfigResponse, type DiscordChannel, type DiscordRole,
} from "./api";
import { BTN_PRIMARY, INPUT, CARD, Icon, roleColor, toast } from "./ui";

const GROUP_ORDER = ["Channels", "Filter", "Rollen"];

function toText(f: ConfigField, v: unknown): string {
  if (v === null || v === undefined) return "";
  if (f.type === "idlist" || f.type === "hostlist") return Array.isArray(v) ? v.join(", ") : String(v);
  return String(v);
}
function fromText(f: ConfigField, t: string): unknown {
  if (f.type === "idlist" || f.type === "hostlist") return t.split(/[\s,;/]+/).map((s) => s.trim()).filter(Boolean);
  return t.trim();
}
function splitIds(v: string): string[] {
  return v.split(/[\s,;]+/).map((s) => s.trim()).filter(Boolean);
}
function channelsForKind(kind: string | undefined, channels: DiscordChannel[]) {
  if (kind === "voice") return channels.filter((c) => c.type.includes("voice"));
  if (kind === "category") return channels.filter((c) => c.type === "category");
  return channels.filter((c) => ["text", "news", "forum", "announcement"].includes(c.type));
}

export default function ConfigPage() {
  const [data, setData] = useState<ConfigResponse | null>(null);
  const [channels, setChannels] = useState<DiscordChannel[]>([]);
  const [roles, setRoles] = useState<DiscordRole[]>([]);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [tab, setTab] = useState("Channels");
  const [openSel, setOpenSel] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  function load() {
    fetchConfig().then((d) => {
      setData(d);
      const init: Record<string, string> = {};
      for (const f of d.fields) init[f.key] = toText(f, d.values[f.key]);
      setDraft(init);
    }).catch((e) => toast("err", String(e.message ?? e)));
  }
  useEffect(() => {
    load();
    fetchChannels().then(setChannels).catch(() => setChannels([]));
    fetchRoles().then(setRoles).catch(() => setRoles([]));
  }, []);

  const groups = useMemo(() => {
    const g: Record<string, ConfigField[]> = {};
    for (const f of data?.fields ?? []) (g[f.group] ??= []).push(f);
    return g;
  }, [data]);
  const tabs = GROUP_ORDER.filter((g) => groups[g]?.length);

  if (!data) return <p className="text-sm text-muted">Lade Konfiguration …</p>;

  async function onSave() {
    if (!data) return;
    setSaving(true);
    setFieldErrors({});
    const updates: Record<string, unknown> = {};
    for (const f of data.fields) {
      if (!f.editable) continue;
      const orig = toText(f, data.values[f.key]);
      if (draft[f.key] !== orig) updates[f.key] = fromText(f, draft[f.key]);
    }
    if (Object.keys(updates).length === 0) { setSaving(false); toast("err", "Keine Änderungen."); return; }
    const res = await saveConfig(updates);
    setSaving(false);
    if (res.ok) { toast("ok", "Konfiguration gespeichert."); load(); }
    else if (res.fieldErrors) { setFieldErrors(res.fieldErrors); toast("err", "Bitte markierte Felder korrigieren."); }
    else toast("err", res.error ?? "Speichern fehlgeschlagen.");
  }

  const fields = groups[tab] ?? [];

  return (
    <div className="flex flex-col gap-5" onClick={() => setOpenSel(null)}>
      <div className="flex items-center justify-between">
        <div className="flex gap-1.5 border-b border-[#211b38]">
          {tabs.map((t) => (
            <button key={t} onClick={(e) => { e.stopPropagation(); setTab(t); setOpenSel(null); }}
              className={`-mb-px flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-sm font-semibold ${tab === t ? "border-accent text-[#f1ecfb]" : "border-transparent text-[#9a93b4] hover:text-ink"}`}>
              {t}<span className="font-mono text-[11px] text-[#6b6390]">{groups[t]?.length}</span>
            </button>
          ))}
        </div>
        <button onClick={(e) => { e.stopPropagation(); onSave(); }} disabled={saving} className={BTN_PRIMARY}>
          {Icon.check}{saving ? "Speichert …" : "Speichern"}
        </button>
      </div>

      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
        {fields.map((f) => (
          <div key={f.key} className={`${CARD} p-4`} onClick={(e) => e.stopPropagation()}>
            <div className="mb-[11px] flex items-center justify-between gap-2.5">
              <span className="text-[13.5px] font-semibold text-[#e7e3f4]">{f.label}</span>
              <span className="font-mono text-[9.5px] text-[#5a5379]">{f.key}</span>
            </div>
            <FieldControl
              field={f} value={draft[f.key] ?? ""} channels={channels} roles={roles}
              open={openSel === f.key} onToggle={() => setOpenSel(openSel === f.key ? null : f.key)}
              onChange={(v) => setDraft({ ...draft, [f.key]: v })}
            />
            {f.kind === "hostlist" && !fieldErrors[f.key] && <p className="mt-2 text-[11.5px] text-[#6f688c]">Mehrere durch Komma trennen.</p>}
            {f.kind === "rolelist" && !fieldErrors[f.key] && <p className="mt-2 text-[11.5px] text-[#6f688c]">Mehrfachauswahl — gespeichert als ID-Liste.</p>}
            {data.restart_required_keys.includes(f.key) && (
              <p className="mt-1.5 flex items-center gap-1.5 text-[11.5px] text-warning">{Icon.restart}Wirkt erst nach Bot-Neustart.</p>
            )}
            {fieldErrors[f.key] && <p className="mt-1.5 text-[11.5px] text-danger2">{fieldErrors[f.key]}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}

function FieldControl({ field, value, channels, roles, open, onToggle, onChange }: {
  field: ConfigField; value: string; channels: DiscordChannel[]; roles: DiscordRole[];
  open: boolean; onToggle: () => void; onChange: (v: string) => void;
}) {
  const kind = field.kind;
  const isRole = kind === "role";
  const isChannel = kind === "channel" || kind === "voice" || kind === "category";
  const isMulti = kind === "rolelist";
  const multiline = field.type === "idlist" || field.type === "hostlist";

  if ((isChannel && channels.length > 0) || (isRole && roles.length > 0)) {
    const opts = isRole
      ? roles.map((r) => ({ id: r.id, name: "@" + r.name, color: roleColor(r.name) }))
      : channelsForKind(kind, channels).map((c) => ({ id: c.id, name: "#" + c.name, color: "#a24bff" }));
    const sel = opts.find((o) => o.id === value);
    return (
      <div className="relative">
        <button onClick={onToggle} className="flex w-full items-center justify-between gap-2 rounded-[10px] border border-line2 bg-input px-3 py-2.5 transition hover:border-[#3a3358]">
          <span className="flex min-w-0 items-center gap-2.5">
            <span className="h-2 w-2 flex-none rounded-full" style={{ background: sel ? sel.color : "#5d567c" }} />
            <span className="truncate text-sm font-medium" style={{ color: sel ? "#d8d2ec" : "#6f688c" }}>{sel ? sel.name : "— nicht gesetzt —"}</span>
          </span>
          <span className="flex-none text-[#7d76a0]">{Icon.chevron}</span>
        </button>
        {open && (
          <Popover>
            <Opt color="#5d567c" name="— nicht gesetzt —" selected={!value} onPick={() => { onChange(""); onToggle(); }} />
            {opts.map((o) => (
              <Opt key={o.id} color={o.color} name={o.name} selected={o.id === value} onPick={() => { onChange(o.id); onToggle(); }} />
            ))}
          </Popover>
        )}
      </div>
    );
  }

  if (isMulti && roles.length > 0) {
    const selected = new Set(splitIds(value));
    const toggle = (id: string) => {
      const next = new Set(selected);
      next.has(id) ? next.delete(id) : next.add(id);
      onChange([...next].join(", "));
    };
    return (
      <div className="relative">
        <div className="flex min-h-[44px] flex-wrap items-center gap-1.5 rounded-[10px] border border-line2 bg-input p-2">
          {[...selected].map((id) => {
            const r = roles.find((x) => x.id === id);
            const c = roleColor(r?.name ?? id);
            return (
              <span key={id} className="inline-flex items-center gap-1.5 rounded-lg border py-1 pl-2.5 pr-1.5 text-[12.5px] font-semibold"
                style={{ background: c + "22", borderColor: c + "44", color: c }}>
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: c }} />{r ? r.name : "ID " + id}
                <button onClick={() => toggle(id)} className="flex opacity-70 hover:opacity-100" style={{ color: c }}>{Icon.x}</button>
              </span>
            );
          })}
          <button onClick={onToggle} className="inline-flex items-center gap-1.5 rounded-lg border border-dashed border-[#3a3358] px-2.5 py-[5px] text-[12.5px] font-semibold text-muted transition hover:border-accent hover:text-accentsoft">{Icon.plus}Rolle</button>
        </div>
        {open && (
          <Popover>
            {roles.map((r) => {
              const c = roleColor(r.name);
              const on = selected.has(r.id);
              return (
                <button key={r.id} onClick={() => toggle(r.id)} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2.5 text-left hover:bg-[#241d3a]">
                  <span className="flex h-[17px] w-[17px] flex-none items-center justify-center rounded-[5px] border-[1.5px]" style={{ borderColor: on ? "#a24bff" : "#3a3358", background: on ? "#a24bff" : "transparent" }}>
                    {on && <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5L20 7" /></svg>}
                  </span>
                  <span className="h-2 w-2 flex-none rounded-full" style={{ background: c }} />
                  <span className="flex-1 text-[13.5px] text-[#d8d2ec]">@{r.name}</span>
                </button>
              );
            })}
          </Popover>
        )}
      </div>
    );
  }

  if (multiline) {
    return (
      <textarea rows={2} value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={kind === "hostlist" ? "tenor.com, klipy.com, giphy.com" : "123456789, 987654321"} className={INPUT} />
    );
  }
  return <input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={kind === "keyword" ? "z. B. oof" : ""} className={INPUT} />;
}

function Popover({ children }: { children: ReactNode }) {
  return (
    <div className="absolute left-0 right-0 top-[calc(100%+6px)] z-40 max-h-60 animate-fIn overflow-y-auto rounded-xl border border-[#322a4d] bg-raised p-1.5 shadow-[0_24px_48px_-16px_rgba(0,0,0,.85)]">
      {children}
    </div>
  );
}

function Opt({ color, name, selected, onPick }: { color: string; name: string; selected: boolean; onPick: () => void }) {
  return (
    <button onClick={onPick} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2.5 text-left hover:bg-[#241d3a]">
      <span className="h-2 w-2 flex-none rounded-full" style={{ background: color }} />
      <span className="flex-1 truncate text-[13.5px] text-[#d8d2ec]">{name}</span>
      {selected && <span className="text-accentsoft">{Icon.check}</span>}
    </button>
  );
}
