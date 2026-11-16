"use client";

import React, { useEffect, useState } from "react";
import { Server, ExternalLink, Copy, Check, KeyRound } from "lucide-react";
import { API } from "@/lib/api";
import { INTERNAL_SERVICES, SERVICE_GROUPS, Service } from "@/lib/services";

type Status = Record<string, boolean>;

function CopyValue({ value }: { value: string }) {
  const [done, setDone] = useState(false);
  return (
    <button type="button" title="Copy" className="inline-flex items-center gap-1 font-mono text-slate-100 hover:text-blue-300"
      onClick={() => navigator.clipboard?.writeText(value).then(() => { setDone(true); setTimeout(() => setDone(false), 1200); })}>
      <span>{value}</span>{done ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3 text-slate-500" />}
    </button>
  );
}

function StatusDot({ up, optional }: { up: boolean | undefined; optional?: boolean }) {
  const label = up === undefined ? "checking" : up ? "up" : optional ? "not running (optional)" : "down";
  const color = up === undefined ? "bg-slate-600" : up ? "bg-green-400" : optional ? "bg-slate-500" : "bg-amber-400";
  return <span className="flex items-center gap-1.5 text-[11px] text-slate-400"><span className={`w-2 h-2 rounded-full ${color}`} />{label}</span>;
}

function ServiceCard({ s, status }: { s: Service; status: Status | null }) {
  const up = s.key === "frontend" ? true : status ? status[s.key] : undefined;
  const external = s.url.startsWith("http");
  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col gap-3" data-testid={`service-${s.key}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold text-slate-100">{s.name}</div>
          <a href={s.url} target={external ? "_blank" : undefined} rel="noreferrer" className="text-xs font-mono text-blue-400 hover:text-blue-300 inline-flex items-center gap-1 break-all">
            {external ? s.url.replace(/^https?:\/\//, "") : "localhost:13002"}{external && <ExternalLink className="w-3 h-3 shrink-0" />}
          </a>
        </div>
        <StatusDot up={up} optional={s.optional} />
      </div>
      <p className="text-xs text-slate-300 leading-relaxed">{s.what}</p>
      <div className="text-[11px] text-slate-400 space-y-1">
        <div><span className="text-slate-500">Look at: </span>{s.use}</div>
        <div><span className="text-slate-500">Used in session: </span>{s.sessions}</div>
      </div>
      <div className="mt-auto text-[11px] bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-2 space-y-0.5">
        {s.login ? (
          <>
            <div className="flex items-center gap-1.5 text-slate-500"><KeyRound className="w-3 h-3" />Login</div>
            {s.login.user && <div className="text-slate-400">user <CopyValue value={s.login.user} /></div>}
            <div className="text-slate-400">{s.login.user ? "password " : ""}{s.login.password.includes(" ") ? <span className="text-slate-200">{s.login.password}</span> : <CopyValue value={s.login.password} />}</div>
            {s.login.note && <div className="text-slate-500">{s.login.note}</div>}
          </>
        ) : <div className="text-slate-500">No login needed</div>}
      </div>
    </div>
  );
}

export default function ServicesPage() {
  const [status, setStatus] = useState<Status | null>(null);

  useEffect(() => {
    const load = () => fetch(`${API}/api/services/status`).then((r) => r.json()).then(setStatus).catch(() => setStatus({}));
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
          <Server className="w-6 h-6 text-blue-400" /><span>Services: every tool of the stack</span>
        </h1>
        <p className="text-sm text-slate-400 mt-1 max-w-3xl">
          Where each tool lives, how to log in and what to look at. The logins are the public demo defaults of this repository:
          fine on your laptop, change them before you expose any port. The status is checked by the backend every 15 seconds.
        </p>
      </div>

      {SERVICE_GROUPS.map((g) => (
        <section key={g.title} className="space-y-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">{g.title}</h2>
            <p className="text-xs text-slate-500">{g.blurb}</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {g.services.map((s) => <ServiceCard key={s.key} s={s} status={status} />)}
          </div>
        </section>
      ))}

      <section className="space-y-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">Behind the scenes (no web page)</h2>
          <p className="text-xs text-slate-500">The other containers in <code className="font-mono">docker compose ps</code>. You never open them; they hold the data of the tools above.</p>
        </div>
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
          <table className="w-full text-xs">
            <thead className="text-slate-500 text-left"><tr><th className="px-4 py-2 font-medium">Container</th><th className="px-4 py-2 font-medium">What it does</th><th className="px-4 py-2 font-medium">Credentials</th></tr></thead>
            <tbody className="divide-y divide-slate-800">
              {INTERNAL_SERVICES.map((s) => (
                <tr key={s.name}><td className="px-4 py-2 font-mono text-slate-200">{s.name}</td><td className="px-4 py-2 text-slate-300">{s.what}</td><td className="px-4 py-2 font-mono text-slate-400">{s.login}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
