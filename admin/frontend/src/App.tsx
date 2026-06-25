import { useEffect, useState, type ReactNode } from "react";
import { BrowserRouter, Routes, Route, Navigate, NavLink, Outlet, useLocation } from "react-router-dom";
import { fetchMe, logout, type Me } from "./api";
import { Avatar, Toast } from "./ui";
import ConfigPage from "./ConfigPage";
import LevelPage from "./LevelPage";
import AuditPage from "./AuditPage";
import SecretsPage from "./SecretsPage";
import StreamerPage from "./StreamerPage";
import MemberPage from "./MemberPage";

const LOGO = (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2 4 14h6l-1 8 9-12h-6z" /></svg>
);

const NAV_ICON: Record<string, ReactNode> = {
  konfiguration: <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><line x1="4" y1="8" x2="20" y2="8" /><circle cx="9" cy="8" r="2.3" /><line x1="4" y1="16" x2="20" y2="16" /><circle cx="15" cy="16" r="2.3" /></svg>,
  level: <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M7 4h10v4a5 5 0 0 1-10 0z" /><path d="M7 6H4v1a3 3 0 0 0 3 3" /><path d="M17 6h3v1a3 3 0 0 1-3 3" /><line x1="12" y1="13" x2="12" y2="17" /><path d="M8 20h8l-1-3H9z" /></svg>,
  streamer: <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="6" width="13" height="12" rx="2.4" /><path d="m16 10 5-3v10l-5-3z" /></svg>,
  mitglieder: <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="9" cy="8" r="3.2" /><path d="M3.5 19a5.5 5.5 0 0 1 11 0" /><path d="M16 5.5a3.2 3.2 0 0 1 0 6" /><path d="M17.5 14.2A5.5 5.5 0 0 1 20.5 19" /></svg>,
  logs: <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12h4l2-7 4 14 2-7h4" /></svg>,
  secrets: <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="8" cy="14" r="4" /><path d="m11 12 9-9 1 3 2 1-3 3-2-1" /><path d="m14 9 2 2" /></svg>,
};

const PAGE_META: Record<string, [string, string]> = {
  "/konfiguration": ["Konfiguration", "Channels, Filter & Rollen des Bots verwalten"],
  "/level": ["Level & Ränge", "EXP-Stände der Community einsehen und anpassen"],
  "/streamer": ["Streamer", "Beobachtete Streamer & deren Kanäle verwalten"],
  "/mitglieder": ["Mitglieder", "Alle Server-Mitglieder mit ihren Rollen"],
  "/logs": ["Logs & Statistiken", "Audit-Log und Kennzahlen des Servers"],
  "/secrets": ["Secrets", "Laufzeit-Geheimnisse aus der .env (nur Voll-Admin)"],
};

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMe().then(setMe).catch(() => setMe(null)).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-canvas text-muted">Lade …</div>;
  }
  if (!me) return <Login />;

  const fullAdmin = me.permissions.tier === "full_admin";

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout me={me} fullAdmin={fullAdmin} />}>
          <Route index element={<Navigate to="/konfiguration" replace />} />
          <Route path="konfiguration" element={<ConfigPage />} />
          <Route path="level" element={<LevelPage canEdit={fullAdmin} />} />
          <Route path="streamer" element={<StreamerPage canManage={fullAdmin} />} />
          <Route path="mitglieder" element={<MemberPage />} />
          <Route path="logs" element={<AuditPage />} />
          <Route path="secrets" element={fullAdmin ? <SecretsPage /> : <Navigate to="/konfiguration" replace />} />
          <Route path="*" element={<Navigate to="/konfiguration" replace />} />
        </Route>
      </Routes>
      <Toast />
    </BrowserRouter>
  );
}

function Login() {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[radial-gradient(120%_120%_at_50%_0%,#16102b_0%,#0a0814_55%)] px-5">
      <div className="pointer-events-none absolute -left-16 -top-32 h-[520px] w-[520px] animate-blob rounded-full bg-[radial-gradient(circle,rgba(139,69,255,.32),transparent_65%)] blur-2xl" />
      <div className="pointer-events-none absolute -bottom-40 -right-20 h-[560px] w-[560px] animate-blob rounded-full bg-[radial-gradient(circle,rgba(216,70,201,.22),transparent_65%)] blur-2xl" />
      <div className="relative w-[430px] max-w-full animate-mIn rounded-3xl border border-[#2a2342] bg-[rgba(20,16,38,.72)] p-[34px] pt-[38px] shadow-[0_40px_90px_-30px_rgba(0,0,0,.85)] backdrop-blur-xl">
        <div className="mb-[30px] flex items-center gap-3">
          <span className="flex h-[46px] w-[46px] items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#8b45ff,#d846c9)] shadow-[0_10px_28px_-8px_rgba(150,70,240,.9)]">{LOGO}</span>
          <span className="leading-tight">
            <span className="block font-sora text-xl font-bold tracking-tight text-ink2">nicebot</span>
            <span className="block font-mono text-[11px] text-[#857ea6]">nicebot.abgemiked.de</span>
          </span>
        </div>
        <h1 className="mb-2 font-sora text-[26px] font-bold tracking-tight text-ink2">Willkommen zurück</h1>
        <p className="mb-[26px] text-[14.5px] leading-relaxed text-muted">
          Melde dich mit deinem Discord-Konto an, um die Verwaltung des Abgemiked-Servers zu öffnen.
        </p>
        <a href="/api/auth/login" className="flex w-full items-center justify-center gap-3 rounded-[13px] bg-discord px-4 py-[15px] text-[15.5px] font-semibold text-white shadow-[0_14px_30px_-12px_rgba(88,101,242,.8)] transition hover:brightness-110">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="#fff"><path d="M19.3 5.4A17 17 0 0 0 15 4l-.2.4a13 13 0 0 1 3.7 1.2A14.6 14.6 0 0 0 5.5 5.6 12.6 12.6 0 0 1 9.2 4.4L9 4a17 17 0 0 0-4.3 1.4C2 9.3 1.3 13.1 1.6 16.8A17.2 17.2 0 0 0 6.8 19.4l.4-.7a11 11 0 0 1-1.7-.8l.4-.3a12.2 12.2 0 0 0 10.4 0l.4.3a11 11 0 0 1-1.7.8l.4.7a17.1 17.1 0 0 0 5.2-2.6c.4-4.3-.6-8-2.7-11zM8.5 14.7c-1 0-1.9-1-1.9-2.1s.8-2.1 1.9-2.1 1.9 1 1.9 2.1-.8 2.1-1.9 2.1zm7 0c-1 0-1.9-1-1.9-2.1s.8-2.1 1.9-2.1 1.9 1 1.9 2.1-.8 2.1-1.9 2.1z" /></svg>
          Mit Discord anmelden
        </a>
        <div className="mt-[22px] flex items-center gap-2.5 rounded-xl border border-[rgba(162,75,255,.18)] bg-[rgba(162,75,255,.08)] px-3.5 py-3">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#C9A6FF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="flex-none"><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></svg>
          <span className="text-[12.5px] leading-snug text-[#b3aacb]">Zugriff nur für Team-Rollen — <b className="font-semibold text-accentsoft">Voll-Admin</b> &amp; <b className="font-semibold text-accentsoft">DC-Mod</b>.</span>
        </div>
        <p className="mt-5 text-center font-mono text-[10.5px] tracking-wide text-[#5f5880]">geschützt durch Discord OAuth2</p>
      </div>
    </div>
  );
}

function Layout({ me, fullAdmin }: { me: Me; fullAdmin: boolean }) {
  const loc = useLocation();
  const [title, sub] = PAGE_META[loc.pathname] ?? ["nicebot", ""];
  const roleLabel = fullAdmin ? "Voll-Admin" : me.permissions.tier === "dc_mod" ? "DC-Mod" : "—";

  return (
    <div className="flex h-screen bg-canvas text-ink">
      {/* Sidebar */}
      <aside className="flex h-screen w-[264px] flex-none flex-col border-r border-linedim bg-sidebar">
        <div className="flex items-center gap-3 px-5 pb-4 pt-[22px]">
          <span className="flex h-[38px] w-[38px] flex-none items-center justify-center rounded-[11px] bg-[linear-gradient(135deg,#8b45ff,#d846c9)] shadow-[0_8px_20px_-8px_rgba(150,70,240,.85)]">{LOGO}</span>
          <span className="leading-tight">
            <span className="block font-sora text-[17px] font-bold tracking-tight text-ink2">nicebot</span>
            <span className="block font-mono text-[10px] text-[#7d76a0]">abgemiked.de</span>
          </span>
        </div>

        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-3 py-1">
          <SectionLabel>Verwaltung</SectionLabel>
          <NavItem to="/konfiguration" icon={NAV_ICON.konfiguration} label="Konfiguration" />
          <NavItem to="/level" icon={NAV_ICON.level} label="Level & Ränge" />
          <NavItem to="/streamer" icon={NAV_ICON.streamer} label="Streamer" />
          <NavItem to="/mitglieder" icon={NAV_ICON.mitglieder} label="Mitglieder" />
          <NavItem to="/logs" icon={NAV_ICON.logs} label="Logs & Statistiken" />
          {fullAdmin && (
            <>
              <SectionLabel>Administration</SectionLabel>
              <NavItem to="/secrets" icon={NAV_ICON.secrets} label="Secrets" badge="ADMIN" />
            </>
          )}
        </nav>

        <div className="border-t border-linedim p-3">
          <div className="flex items-center gap-2.5 rounded-[13px] border border-[#221c38] bg-[#141026] p-2.5">
            <Avatar seed={me.username || me.discord_id} label={me.username || "?"} size={34} />
            <div className="min-w-0 flex-1">
              <div className="truncate text-[13px] font-semibold text-[#ebe7f6]">{me.username}</div>
              <div className="mt-px text-[11px] font-semibold" style={{ color: fullAdmin ? "#c9a6ff" : "#7ca3ff" }}>{roleLabel}</div>
            </div>
            <button onClick={() => logout().then(() => location.assign("/"))} title="Abmelden" className="flex h-8 w-8 flex-none items-center justify-center rounded-[9px] border border-[#2c2546] text-[#928bb0] transition hover:bg-[#1c1730] hover:text-danger2">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3" /><path d="m16 17 5-5-5-5" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex h-screen min-w-0 flex-1 flex-col bg-canvas">
        <header className="flex flex-none items-center justify-between gap-4 border-b border-[#1a1530] bg-[rgba(12,10,24,.55)] px-8 py-[18px] backdrop-blur">
          <div>
            <h1 className="font-sora text-[22px] font-bold tracking-tight text-ink2">{title}</h1>
            <p className="mt-1 text-[13px] text-muted2">{sub}</p>
          </div>
        </header>
        <div className="flex-1 overflow-y-auto px-8 pb-16 pt-7">
          <div className="mx-auto max-w-[1060px] animate-fIn">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}

function SectionLabel({ children }: { children: ReactNode }) {
  return <div className="px-3 pb-[7px] pt-3.5 text-[10px] font-bold uppercase tracking-[.13em] text-[#574f76]">{children}</div>;
}

function NavItem({ to, icon, label, badge }: { to: string; icon: ReactNode; label: string; badge?: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-[10px] px-3 py-2.5 text-sm font-semibold transition ${
          isActive
            ? "bg-[rgba(162,75,255,.13)] text-[#f1ecfb] shadow-[inset_3px_0_0_#a24bff]"
            : "text-[#ada6c4] hover:bg-hover"
        }`
      }
    >
      <span className="flex-none">{icon}</span>
      <span className="flex-1">{label}</span>
      {badge && <span className="rounded-md bg-[rgba(162,75,255,.16)] px-1.5 py-0.5 text-[9px] font-bold tracking-wide text-accentsoft">{badge}</span>}
    </NavLink>
  );
}
