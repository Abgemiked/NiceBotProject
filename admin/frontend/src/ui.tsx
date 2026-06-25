import { useEffect, useState } from "react";

// --- Klassen-Konstanten (Design-System) ---
export const GRAD = "bg-[linear-gradient(135deg,#8b45ff,#d846c9)]";
export const CARD = "rounded-2xl border border-line bg-surface shadow-card";
export const INPUT =
  "w-full rounded-[10px] border border-line2 bg-input px-3 py-2.5 text-sm font-medium text-ink outline-none transition focus:border-accent focus:shadow-[0_0_0_3px_rgba(162,75,255,.16)]";
export const BTN_PRIMARY =
  `inline-flex items-center justify-center gap-2 ${GRAD} rounded-[11px] px-[18px] py-[11px] text-sm font-semibold text-white shadow-glow transition hover:brightness-110 disabled:opacity-50`;
export const BTN_SECONDARY =
  "inline-flex items-center justify-center gap-2 rounded-[10px] border border-[#2f2848] bg-[#1b1730] px-4 py-2.5 text-sm font-semibold text-[#cfc9e2] transition hover:bg-[#221c38] disabled:opacity-50";
export const BTN_DANGER =
  "inline-flex items-center justify-center gap-2 rounded-[10px] border border-[rgba(255,84,112,.3)] bg-[rgba(255,84,112,.12)] px-4 py-2.5 text-sm font-semibold text-danger2 transition hover:bg-[rgba(255,84,112,.2)] disabled:opacity-50";
export const ICON_BTN =
  "flex h-8 w-8 items-center justify-center rounded-[9px] border border-[#2c2546] bg-transparent text-[#928bb0] transition";
export const TABLE_WRAP =
  "overflow-hidden rounded-2xl border border-line bg-surface shadow-[0_22px_40px_-32px_rgba(0,0,0,.9)]";
export const TH =
  "px-4 py-3 text-left text-[11px] font-bold uppercase tracking-[.06em] text-[#7a7298]";

// --- Avatar / Initialen / Rollenfarben ---
const AV_PALETTE = [
  "linear-gradient(135deg,#8B45FF,#D846C9)",
  "linear-gradient(135deg,#5B8CFF,#3FC8D8)",
  "linear-gradient(135deg,#FF7AD9,#FF5470)",
  "linear-gradient(135deg,#35D9A0,#3FC8D8)",
  "linear-gradient(135deg,#C065FF,#8B45FF)",
  "linear-gradient(135deg,#F5B544,#FF7AD9)",
];
const ROLE_PALETTE = [
  "#FF5470", "#FF7AD9", "#A24BFF", "#5B8CFF", "#C065FF",
  "#FF8FE0", "#3FC8D8", "#35D9A0", "#F5B544", "#7CA3FF",
];

function hash(seed: string): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return h;
}

export function initialOf(s: string | null | undefined): string {
  const m = (s || "?").replace(/[^A-Za-zÄÖÜäöü0-9]/g, "");
  return (m.charAt(0) || "?").toUpperCase();
}

export function avatarGradient(seed: string): string {
  return AV_PALETTE[hash(seed || "x") % AV_PALETTE.length];
}

export function roleColor(seed: string): string {
  return ROLE_PALETTE[hash(seed || "x") % ROLE_PALETTE.length];
}

/** Avatar-Kachel mit Initiale. */
export function Avatar({ seed, label, size = 34 }: { seed: string; label: string; size?: number }) {
  return (
    <span
      className="flex flex-none items-center justify-center rounded-[10px] font-sora font-bold text-white"
      style={{ width: size, height: size, background: avatarGradient(seed), fontSize: size * 0.41 }}
    >
      {initialOf(label)}
    </span>
  );
}

// --- Toast-System (global) ---
export interface ToastMsg {
  kind: "ok" | "err";
  msg: string;
}
let current: ToastMsg | null = null;
const subs = new Set<(t: ToastMsg | null) => void>();
let timer: ReturnType<typeof setTimeout> | undefined;

export function toast(kind: "ok" | "err", msg: string) {
  current = { kind, msg };
  subs.forEach((f) => f(current));
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => {
    current = null;
    subs.forEach((f) => f(null));
  }, 2800);
}

export function useToast(): ToastMsg | null {
  const [t, setT] = useState<ToastMsg | null>(current);
  useEffect(() => {
    subs.add(setT);
    return () => {
      subs.delete(setT);
    };
  }, []);
  return t;
}

export function Toast() {
  const t = useToast();
  if (!t) return null;
  const ok = t.kind === "ok";
  return (
    <div
      className="fixed bottom-6 right-6 z-[80] flex min-w-[250px] animate-tIn items-center gap-3 rounded-[13px] border bg-[#171327] px-4 py-3 shadow-[0_22px_44px_-16px_rgba(0,0,0,.8)]"
      style={{ borderColor: ok ? "rgba(53,217,160,.32)" : "rgba(255,84,112,.32)" }}
    >
      <span
        className="flex h-[26px] w-[26px] flex-none items-center justify-center rounded-lg"
        style={{ background: ok ? "rgba(53,217,160,.16)" : "rgba(255,84,112,.16)" }}
      >
        {ok ? (
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#35D9A0" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5L20 7" /></svg>
        ) : (
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#FF7A92" strokeWidth="2.4" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
        )}
      </span>
      <span className="text-sm font-medium text-ink">{t.msg}</span>
    </div>
  );
}

/** Kleiner SVG-Icon-Satz (stroke=currentColor). */
export const Icon = {
  search: (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.5" y2="16.5" /></svg>
  ),
  chevron: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6" /></svg>
  ),
  check: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5L20 7" /></svg>
  ),
  plus: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
  ),
  x: (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
  ),
  prev: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
  ),
  next: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6" /></svg>
  ),
  edit: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" /></svg>
  ),
  trash: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 7h16" /><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" /><path d="m6 7 1 13h10l1-13" /></svg>
  ),
  restart: (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 8v4l2.5 2.5" /><circle cx="12" cy="12" r="9" /></svg>
  ),
};

/** Pagination-Leiste (Zurück/Seite/Weiter). */
export function Pager({
  page,
  totalPages,
  onPrev,
  onNext,
  label,
}: {
  page: number;
  totalPages: number;
  onPrev: () => void;
  onNext: () => void;
  label: string;
}) {
  const btn =
    "flex items-center gap-1.5 rounded-[9px] border border-[#2c2546] bg-surface px-3 py-2 text-[13px] font-semibold text-[#b3aacb] transition hover:bg-[#1c1730] hover:border-[#3a3358] disabled:opacity-40";
  return (
    <div className="flex items-center justify-end gap-3">
      <span className="font-mono text-xs text-[#857ea6]">{label}</span>
      <button disabled={page <= 1} onClick={onPrev} className={btn}>
        {Icon.prev}Zurück
      </button>
      <button disabled={page >= totalPages} onClick={onNext} className={btn}>
        Weiter{Icon.next}
      </button>
    </div>
  );
}
