"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Server } from "lucide-react";
import { API } from "@/lib/api";

interface HealthStatus {
  status: string;
  neo4j_connected: boolean;
  qdrant_connected: boolean;
  embeddings_ready: boolean;
  qdrant_points?: Record<string, number>;
}

export default function Header() {
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    const load = () =>
      fetch(`${API}/api/health`)
        .then((res) => res.json())
        .then(setHealth)
        .catch(() => setHealth(null));
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  const indexed = health ? Object.values(health.qdrant_points || {}).reduce((a, b) => a + b, 0) : 0;
  const ready = !!health && health.neo4j_connected && health.qdrant_connected && indexed > 0;
  const label = !health ? "Backend starting..." : !health.neo4j_connected || !health.qdrant_connected ? "Databases not reachable"
    : indexed === 0 ? "Not indexed yet: run notebook 02" : `Ready · ${indexed} chunks indexed`;

  return (
    <header className="border-b border-slate-700 bg-slate-900 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/syone-logo-white.png" alt="Syone" className="h-9 w-auto" />
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-slate-100">Enterprise GenAI</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-900/60 text-blue-300 border border-blue-700 font-mono">Formation 2026</span>
            </div>
            <p className="text-xs text-slate-400">GraphRAG + BM25 vs. Google OKF agentic navigation</p>
          </div>
        </div>

        <nav className="flex items-center gap-1 bg-slate-900/60 p-1 rounded-lg border border-slate-800">
          <Link href="/" className="px-3 py-1.5 text-xs font-medium rounded-md hover:bg-slate-800 text-slate-200 transition-colors">Dual Compare</Link>
          <Link href="/how-it-works" className="px-3 py-1.5 text-xs font-medium rounded-md hover:bg-slate-800 text-slate-300 transition-colors">How it works</Link>
          <Link href="/models" className="px-3 py-1.5 text-xs font-medium rounded-md hover:bg-slate-800 text-slate-300 transition-colors">Free Models</Link>
          <Link href="/eval" className="px-3 py-1.5 text-xs font-medium rounded-md hover:bg-slate-800 text-slate-300 transition-colors">Evaluation</Link>
        </nav>

        <div className="flex items-center gap-3">
          <Link href="/services" className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 transition" title="Every tool of the stack: URLs, logins, status">
            <Server className="w-3.5 h-3.5 text-blue-400" /><span>Services</span>
          </Link>
          <div className="flex items-center gap-1.5 pl-2 border-l border-slate-800 text-xs" data-testid="health-pill">
            <span className={`w-2 h-2 rounded-full ${ready ? "bg-green-400 animate-pulse" : "bg-amber-400"}`} />
            <span className="text-slate-400 hidden sm:inline">{label}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
