"use client";

import React, { useEffect, useState } from "react";
import { API } from "@/lib/api";
import { Sparkles, Layers, ShieldCheck, ArrowUpDown, ExternalLink } from "lucide-react";

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  context_length: number;
  modality: string;
  description?: string;
}

export default function ModelsPage() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/models/free`)
      .then((res) => res.json())
      .then((data) => {
        if (data?.models) setModels(data.models);
      })
      .catch((err) => console.error("Error fetching models:", err))
      .finally(() => setLoading(false));
  }, []);

  const formatTokens = (tokens: number) => {
    if (!tokens) return "n/a";
    if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(1)}M (${tokens.toLocaleString()})`;
    return `${Math.round(tokens / 1000)}k (${tokens.toLocaleString()})`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
          <Sparkles className="w-6 h-6 text-blue-400" />
          <span>Dynamic Free Model Discovery</span>
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Live list of the free OpenRouter models right now (the list changes every few weeks), ordered by context window. The gateway aliases formation-* are stable names that LiteLLM maps to whichever models are configured.
        </p>
      </div>

      {/* Model Cards Grid */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">
          <div className="w-8 h-8 border-3 border-blue-500/20 border-t-blue-500 rounded-full animate-spin mx-auto mb-2" />
          <p className="text-xs">Fetching dynamic free model specs...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {models.map((m, idx) => (
            <div
              key={m.id}
              className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 p-4 rounded-xl shadow-lg flex flex-col justify-between transition"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="text-xs font-mono font-bold text-blue-400">#{idx + 1}</span>
                  <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-slate-800 text-amber-300 border border-slate-700">
                    {m.provider}
                  </span>
                </div>
                <h3 className="font-bold text-slate-100 text-base mb-1">{m.name}</h3>
                <p className="text-xs text-slate-400 line-clamp-2 mb-3">{m.description}</p>
              </div>

              <div className="border-t border-slate-800 pt-3 space-y-1.5 text-xs">
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Context Window:</span>
                  <span className="font-mono text-amber-400 font-bold">{formatTokens(m.context_length)}</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Modality:</span>
                  <span className="font-mono text-xs flex items-center gap-1">
                    {m.modality.includes("vision") || m.modality.includes("multimodal") ? (
                      <span className="text-amber-400 font-bold flex items-center gap-1">
                        👁️ Vision / Multimodal
                      </span>
                    ) : (
                      <span className="text-slate-300">📝 Text Reasoning</span>
                    )}
                  </span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Model ID:</span>
                  <span className="font-mono text-[11px] text-slate-400 truncate max-w-[150px]">{m.id}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
