"use client";

import React, { useState } from "react";
import CorpusSelector from "@/components/CorpusSelector";
import ModelSelector from "@/components/ModelSelector";
import ChatDualView from "@/components/ChatDualView";

export default function HomePage() {
  const [selectedCorpus, setSelectedCorpus] = useState("syone_corp");
  const [selectedModel, setSelectedModel] = useState("formation-fast");

  return (
    <div className="space-y-6">
      {/* Top Controls Grid: Corpus Selection & Dynamic Free Model Selector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-7">
          <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">
            Select Active Knowledge Base
          </label>
          <CorpusSelector
            selectedCorpus={selectedCorpus}
            onSelectCorpus={(c) => setSelectedCorpus(c)}
          />
        </div>
        <div className="lg:col-span-5">
          <ModelSelector
            selectedModel={selectedModel}
            onSelectModel={(m) => setSelectedModel(m)}
          />
        </div>
      </div>

      {/* Main Dual-Track Comparison View */}
      <ChatDualView
        selectedCorpus={selectedCorpus}
        selectedModel={selectedModel}
        onCorpusChange={setSelectedCorpus}
      />
    </div>
  );
}
