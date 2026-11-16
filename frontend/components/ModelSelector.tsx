"use client";

import React, { useEffect, useState } from "react";
import { API } from "@/lib/api";
import { Sparkles, Zap, ChevronDown, Check, Eye, FileText } from "lucide-react";

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  context_length: number;
  modality: string;
  supports_vision?: boolean;
  description?: string;
}

interface ModelSelectorProps {
  selectedModel: string;
  onSelectModel: (modelId: string) => void;
}

export default function ModelSelector({ selectedModel, onSelectModel }: ModelSelectorProps) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/models/free`)
      .then((res) => res.json())
      .then((data) => {
        if (data?.models) {
          setModels(data.models);
          if (!selectedModel && data.models.length > 0) {
            onSelectModel(data.models[0].id);
          }
        }
      })
      .catch((err) => {
        console.error("Failed to load free models:", err);
      })
      .finally(() => setLoading(false));
  }, []);

  const currentModel = models.find((m) => m.id === selectedModel) || {
    id: selectedModel || "formation-fast",
    name: "Gateway alias: formation-fast",
    context_length: 1000000,
    provider: "openrouter",
    supports_vision: true
  };

  const formatContext = (tokens: number) => {
    if (!tokens) return "n/a";
    if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(1)}M tokens`;
    if (tokens >= 1000) return `${Math.round(tokens / 1000)}k tokens`;
    return `${tokens} tokens`;
  };

  return (
    <div className="relative">
      <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">
        AI Gateway Free Model Routing (Ordered by Context Window)
      </label>

      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3.5 py-2.5 bg-slate-900/90 border border-slate-700 hover:border-slate-600 rounded-xl text-left transition"
      >
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-blue-900/40 text-blue-400 border border-blue-800/50">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <span>{currentModel.name}</span>
              {currentModel.supports_vision ? (
                <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-800">
                  <Eye className="w-3 h-3 text-amber-400" />
                  <span>Vision</span>
                </span>
              ) : (
                <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                  <FileText className="w-3 h-3 text-slate-400" />
                  <span>Text</span>
                </span>
              )}
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-800">
                {currentModel.provider}
              </span>
            </div>
            <div className="text-xs text-slate-400 font-mono mt-0.5">
              Context: {formatContext(currentModel.context_length)} • Free Tier
            </div>
          </div>
        </div>

        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <div className="absolute left-0 right-0 mt-2 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-2 z-50 max-h-80 overflow-y-auto">
          <div className="text-[11px] font-semibold text-slate-400 px-3 py-1.5 uppercase tracking-wider border-b border-slate-800 mb-1">
            Available Free Models (No Paid Key Required)
          </div>

          {models.map((m) => {
            const isSelected = m.id === selectedModel;
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => {
                  onSelectModel(m.id);
                  setIsOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-left transition mb-1 ${
                  isSelected ? "bg-blue-600/20 text-blue-200 border border-blue-500/40" : "hover:bg-slate-800 text-slate-300"
                }`}
              >
                <div>
                  <div className="text-sm font-medium text-slate-100 flex items-center gap-2">
                    {m.name}
                    {m.supports_vision ? (
                      <span className="flex items-center gap-1 text-[9px] px-1.5 py-0.2 rounded bg-amber-950 text-amber-300 border border-amber-800 font-mono">
                        <Eye className="w-2.5 h-2.5" />
                        <span>Vision</span>
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">
                        <FileText className="w-2.5 h-2.5" />
                        <span>Text</span>
                      </span>
                    )}
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 uppercase font-mono">
                      {m.provider}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 font-mono mt-0.5">
                    Context Window: <span className="text-amber-400 font-semibold">{formatContext(m.context_length)}</span>
                  </div>
                </div>

                {isSelected && <Check className="w-4 h-4 text-blue-400" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
