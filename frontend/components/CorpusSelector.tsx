"use client";

import React, { useEffect, useState } from "react";
import { Building2, Cpu } from "lucide-react";
import { API } from "@/lib/api";

interface CorpusSelectorProps {
  selectedCorpus: string;
  onSelectCorpus: (corpus: string) => void;
}

interface CorpusInfo {
  documents: number;
  figures: number;
}

const CORPORA = [
  {
    id: "syone_corp",
    name: "1. Syone (scraped from syone.com)",
    sub: "Services, partners, ezSearch, news, blog articles, FAQs",
    icon: Building2,
    activeColor: "border-blue-500 bg-blue-900/40 text-white shadow-md ",
  },
  {
    id: "hardware_manuals",
    name: "2. Aurora AOR-3 manuals (synthetic)",
    sub: "Fault codes, LED legends, switch port map, thermal charts",
    icon: Cpu,
    activeColor: "border-amber-500 bg-amber-900/40 text-white shadow-md ",
  },
];

export default function CorpusSelector({ selectedCorpus, onSelectCorpus }: CorpusSelectorProps) {
  const [info, setInfo] = useState<Record<string, CorpusInfo>>({});

  useEffect(() => {
    fetch(`${API}/api/corpora`)
      .then((r) => r.json())
      .then(setInfo)
      .catch(() => setInfo({}));
  }, []);

  return (
    <div className="flex flex-col sm:flex-row gap-3" data-testid="corpus-selector">
      {CORPORA.map((c) => {
        const Icon = c.icon;
        const isActive = selectedCorpus === c.id;
        const stats = info[c.id];
        return (
          <button
            key={c.id}
            type="button"
            onClick={() => onSelectCorpus(c.id)}
            className={`flex-1 flex items-start gap-3 p-3 rounded-xl border transition-all text-left ${
              isActive ? c.activeColor : "border-slate-800 bg-slate-900/40 hover:bg-slate-800/60 text-slate-400"
            }`}
          >
            <div className={`p-2 rounded-lg ${isActive ? "bg-slate-800 text-white" : "bg-slate-800/80 text-slate-400"}`}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <div className="font-semibold text-sm">{c.name}</div>
              <div className="text-xs text-slate-400 mt-0.5">{c.sub}</div>
              {stats && (
                <div className="text-[11px] font-mono text-slate-500 mt-1">
                  {stats.documents} documents · {stats.figures} figures
                </div>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
