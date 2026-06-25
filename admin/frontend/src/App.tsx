import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  NavLink,
  Outlet,
} from "react-router-dom";
import { fetchMe, logout, type Me } from "./api";
import ConfigPage from "./ConfigPage";
import LevelPage from "./LevelPage";
import AuditPage from "./AuditPage";
import SecretsPage from "./SecretsPage";

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMe()
      .then(setMe)
      .catch(() => setMe(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Centered>Lade …</Centered>;

  if (!me) {
    return (
      <Centered>
        <h1 className="mb-2 text-2xl font-semibold">nicebot — Verwaltung</h1>
        <p className="mb-6 text-slate-400">Anmeldung über Discord erforderlich.</p>
        <a
          href="/api/auth/login"
          className="rounded-lg bg-indigo-600 px-5 py-2.5 font-medium text-white hover:bg-indigo-500"
        >
          Mit Discord anmelden
        </a>
      </Centered>
    );
  }

  const fullAdmin = me.permissions.tier === "full_admin";

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout me={me} />}>
          <Route index element={<Navigate to="/konfiguration" replace />} />
          <Route path="konfiguration" element={<ConfigPage />} />
          <Route path="level" element={<LevelPage canEdit={fullAdmin} />} />
          <Route path="logs" element={<AuditPage />} />
          <Route
            path="secrets"
            element={fullAdmin ? <SecretsPage /> : <Navigate to="/konfiguration" replace />}
          />
          <Route path="*" element={<Navigate to="/konfiguration" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

function Layout({ me }: { me: Me }) {
  const tierLabel =
    me.permissions.tier === "full_admin"
      ? "Voll-Admin"
      : me.permissions.tier === "dc_mod"
        ? "DC-Mod"
        : "—";

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
        <div className="flex items-center gap-6">
          <h1 className="text-lg font-semibold">nicebot — Verwaltung</h1>
          <nav className="flex gap-1 text-sm">
            <Tab to="/konfiguration" label="Konfiguration" />
            <Tab to="/level" label="Level & Ränge" />
            <Tab to="/logs" label="Logs" />
            {me.permissions.tier === "full_admin" && <Tab to="/secrets" label="Secrets" />}
          </nav>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-slate-400">
            {me.username} · <span className="text-indigo-400">{tierLabel}</span>
          </span>
          <button
            onClick={() => logout().then(() => location.assign("/"))}
            className="rounded-md border border-slate-700 px-3 py-1 hover:bg-slate-800"
          >
            Abmelden
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-4xl px-6 py-10">
        <Outlet />
      </main>
    </div>
  );
}

function Tab({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `rounded-md px-3 py-1 ${
          isActive ? "bg-slate-800 text-slate-100" : "text-slate-400 hover:text-slate-200"
        }`
      }
    >
      {label}
    </NavLink>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 px-6 text-center text-slate-100">
      {children}
    </div>
  );
}
