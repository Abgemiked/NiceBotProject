import { useEffect, useState } from "react";
import { fetchMe, logout, type Me } from "./api";
import ConfigPage from "./ConfigPage";
import LevelPage from "./LevelPage";

type View = "config" | "levels";

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<View>("config");

  useEffect(() => {
    fetchMe()
      .then(setMe)
      .catch(() => setMe(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <Centered>Lade …</Centered>;
  }

  if (!me) {
    return (
      <Centered>
        <h1 className="text-2xl font-semibold mb-2">nicebot — Verwaltung</h1>
        <p className="text-slate-400 mb-6">
          Anmeldung über Discord erforderlich.
        </p>
        <a
          href="/api/auth/login"
          className="rounded-lg bg-indigo-600 px-5 py-2.5 font-medium text-white hover:bg-indigo-500"
        >
          Mit Discord anmelden
        </a>
      </Centered>
    );
  }

  const p = me.permissions;
  const tierLabel =
    p.tier === "full_admin" ? "Voll-Admin" : p.tier === "dc_mod" ? "DC-Mod" : "—";

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
        <div className="flex items-center gap-6">
          <h1 className="text-lg font-semibold">nicebot — Verwaltung</h1>
          <nav className="flex gap-1 text-sm">
            <NavBtn label="Konfiguration" active={view === "config"} onClick={() => setView("config")} />
            <NavBtn label="Level & Ränge" active={view === "levels"} onClick={() => setView("levels")} />
          </nav>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-slate-400">
            {me.username} · <span className="text-indigo-400">{tierLabel}</span>
          </span>
          <button
            onClick={() => logout().then(() => location.reload())}
            className="rounded-md border border-slate-700 px-3 py-1 hover:bg-slate-800"
          >
            Abmelden
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-10">
        {view === "config" ? <ConfigPage /> : <LevelPage canEdit={p.tier === "full_admin"} />}
      </main>
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 px-6 text-center text-slate-100">
      {children}
    </div>
  );
}

function NavBtn({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-md px-3 py-1 ${
        active ? "bg-slate-800 text-slate-100" : "text-slate-400 hover:text-slate-200"
      }`}
    >
      {label}
    </button>
  );
}
