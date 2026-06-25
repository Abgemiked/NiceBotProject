import { useEffect, useState } from "react";
import { fetchMe, logout, type Me } from "./api";

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

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
        <h1 className="text-lg font-semibold">nicebot — Verwaltung</h1>
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

      <main className="mx-auto max-w-3xl px-6 py-10 space-y-4">
        <Card title="Einstellungen" enabled={p.edit_settings}>
          Bot-Konfiguration verwalten (folgt in M2).
        </Card>
        {/* Secret-Bereich nur für Voll-Admin sichtbar */}
        {p.view_secrets ? (
          <Card title="Secrets / Keys" enabled={p.edit_secrets}>
            Bot-Token & Service-Token (sichtbar, da Voll-Admin).
          </Card>
        ) : (
          <Card title="Secrets / Keys" enabled={false} muted>
            Für deine Rolle ausgeblendet.
          </Card>
        )}
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

function Card({
  title,
  enabled,
  muted,
  children,
}: {
  title: string;
  enabled: boolean;
  muted?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section
      className={`rounded-xl border border-slate-800 p-5 ${
        muted ? "opacity-50" : ""
      }`}
    >
      <div className="mb-1 flex items-center justify-between">
        <h2 className="font-medium">{title}</h2>
        <span className="text-xs text-slate-500">
          {enabled ? "bearbeitbar" : "nur Anzeige"}
        </span>
      </div>
      <p className="text-sm text-slate-400">{children}</p>
    </section>
  );
}
