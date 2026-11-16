"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Send, Network, Compass, Clock, ChevronRight, CheckCircle2, AlertTriangle, ImageIcon } from "lucide-react";
import { API, assetUrl } from "@/lib/api";

interface QueryResult {
  pipeline: string;
  answer: string;
  answer_mode?: string;
  agent_mode?: string;
  llm_error?: string | null;
  latency_seconds: number;
  keywords?: string[];
  retrieved_chunks?: any[];
  graph_subgraph?: { nodes: any[]; relationships: any[]; available?: boolean };
  agent_trajectory?: any[];
  inspected_documents?: string[];
  associated_images?: { path: string; caption: string }[];
  context_chars?: number;
  error?: string;
}

interface ChatDualViewProps {
  selectedCorpus: string;
  selectedModel: string;
  onCorpusChange?: (corpus: string) => void;
}

// One featured question per capability: each is verified in the golden set (backend/evaluation/golden_dataset.py)
const SAMPLE_PROMPTS = [
  { title: "BM25 exact match", corpus: "hardware_manuals", text: "What is the root cause and required remediation for fault code 0x4A7B_VRM_OVERVOLT?" },
  { title: "Near-duplicate codes", corpus: "hardware_manuals", text: "What does fault 0x4A7C_VRM_UNDERVOLT mean and how does it differ from 0x4A7B_VRM_OVERVOLT?" },
  { title: "Visual: LED legend", corpus: "hardware_manuals", text: "What does a blinking amber PWR LED mean, and where can I see the full LED legend?" },
  { title: "Text inside a diagram", corpus: "hardware_manuals", text: "Which port on the AS-100G is used for out-of-band management and which VLAN does it carry?" },
  { title: "Real website: footprint map", corpus: "syone_corp", text: "In which regions does the Syone footprint map show that Syone has delivered projects?" },
  { title: "Real website: FAQ", corpus: "syone_corp", text: "Is Syone an official Zabbix partner in Portugal, and what kind of partner is it?" },
  { title: "Multi-hop graph", corpus: "syone_corp", text: "Which monitoring and observability tools does Syone use, and which of them does it hold official partnerships for?" },
  { title: "Unanswerable (honesty)", corpus: "syone_corp", text: "What was Syone's revenue in 2030 and what is its stock market ticker?" },
];

function Answer({ result, onZoom }: { result: QueryResult; onZoom: (u: string) => void }) {
  return (
    <>
      {result.answer_mode === "extractive" && (
        <div className="flex items-start gap-2 text-[11px] text-amber-300 bg-amber-950/40 border border-amber-800/60 rounded-lg p-2" data-testid="extractive-banner">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
          <span>No LLM answer: {result.llm_error}. Showing retrieved passages only.</span>
        </div>
      )}
      <div className="prose-markdown text-sm text-slate-200 bg-slate-950/50 p-4 rounded-xl border border-slate-800/80" data-testid="answer">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            img: ({ node, ...props }) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img {...props} src={assetUrl(props.src as string)} alt={props.alt || "figure"}
                className="cursor-pointer hover:opacity-90 transition rounded-lg bg-white max-h-72"
                onClick={() => onZoom(assetUrl(props.src as string))} />
            ),
          }}
        >
          {result.answer || ""}
        </ReactMarkdown>
      </div>
      {result.associated_images && result.associated_images.length > 0 && (
        <div className="text-xs">
          <div className="font-semibold text-slate-400 mb-1.5 flex items-center gap-1.5"><ImageIcon className="w-3.5 h-3.5" />Figures linked to the retrieved material</div>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {result.associated_images.map((im, i) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img key={i} src={assetUrl(im.path)} alt={im.caption} title={im.caption}
                className="h-20 rounded border border-slate-700 bg-white cursor-pointer hover:opacity-90"
                onClick={() => onZoom(assetUrl(im.path))} />
            ))}
          </div>
        </div>
      )}
    </>
  );
}

export default function ChatDualView({ selectedCorpus, selectedModel, onCorpusChange }: ChatDualViewProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [graphRagResult, setGraphRagResult] = useState<QueryResult | null>(null);
  const [okfAgentResult, setOkfAgentResult] = useState<QueryResult | null>(null);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [corpus, setCorpus] = useState<string | null>(null);

  const call = (q: string, c: string, pipeline: string): Promise<QueryResult> =>
    fetch(`${API}/api/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q, corpus: c, pipeline, model_name: selectedModel }),
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      return data;
    });

  const run = async (text?: string, forcedCorpus?: string) => {
    const q = text || query;
    const c = forcedCorpus || selectedCorpus;
    if (!q.trim()) return;
    setLoading(true);
    setGraphRagResult(null);
    setOkfAgentResult(null);
    setCorpus(c);
    onCorpusChange?.(c);
    const errResult = (e: any): QueryResult => ({ pipeline: "error", answer: `**Request failed:** ${e.message}`, latency_seconds: 0, error: e.message });
    // Both tracks run concurrently; each panel fills as soon as its track answers.
    await Promise.all([
      call(q, c, "graph_rag").then(setGraphRagResult).catch((e) => setGraphRagResult(errResult(e))),
      call(q, c, "okf_agent").then(setOkfAgentResult).catch((e) => setOkfAgentResult(errResult(e))),
    ]);
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div className="bg-slate-900/40 p-4 rounded-xl border border-slate-800/80">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
          Featured scenarios (click to run both tracks; each one has a verified answer in the golden set)
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
          {SAMPLE_PROMPTS.map((p, idx) => (
            <button key={idx} type="button" data-testid={`sample-${idx}`}
              onClick={() => { setQuery(p.text); run(p.text, p.corpus); }}
              className="p-2.5 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-left transition text-xs group">
              <div className="font-semibold text-blue-400 group-hover:text-blue-300 flex items-center justify-between">
                <span>{p.title}</span>
                <ChevronRight className="w-3.5 h-3.5 opacity-60 group-hover:translate-x-1 transition-transform" />
              </div>
              <div className="text-[10px] font-mono text-slate-500 mt-0.5">{p.corpus === "syone_corp" ? "Syone" : "Aurora manuals"}</div>
              <div className="text-slate-300 mt-1 line-clamp-2">{p.text}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-2">
        <input type="text" value={query} data-testid="query-input"
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder="Ask a question about the selected knowledge base..."
          className="flex-1 px-4 py-3 bg-slate-900 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition text-sm shadow-inner" />
        <button type="button" disabled={loading || !query.trim()} onClick={() => run()} data-testid="run-button"
          className="px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold rounded-xl flex items-center gap-2  transition text-sm">
          {loading ? (<><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /><span>Running...</span></>)
            : (<><Send className="w-4 h-4" /><span>Run both tracks</span></>)}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Track A */}
        <div className="bg-slate-900/70 border border-blue-900/40 rounded-2xl p-5 shadow-xl flex flex-col min-h-[460px]" data-testid="panel-graphrag">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-blue-950 text-blue-400 border border-blue-800"><Network className="w-5 h-5" /></div>
              <div>
                <h3 className="font-bold text-sm text-slate-100">Track A: GraphRAG + BM25</h3>
                <p className="text-[11px] text-slate-400">Qdrant dense + BM25 (RRF) + Neo4j graph facts</p>
              </div>
            </div>
            {graphRagResult && !graphRagResult.error && (
              <span className="flex items-center gap-1 text-xs px-2.5 py-1 rounded bg-blue-950/80 text-blue-300 font-mono border border-blue-800">
                <Clock className="w-3 h-3" />{graphRagResult.latency_seconds}s
              </span>
            )}
          </div>
          {loading && !graphRagResult ? (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-500 py-12">
              <div className="w-8 h-8 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin mb-3" />
              <p className="text-xs">Querying Qdrant (dense + BM25) and walking the Neo4j graph...</p>
            </div>
          ) : graphRagResult ? (
            <div className="space-y-4 flex-1">
              {!graphRagResult.error && (
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">{graphRagResult.retrieved_chunks?.length || 0} chunks</span>
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">{graphRagResult.graph_subgraph?.nodes?.length || 0} graph nodes</span>
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">{graphRagResult.context_chars?.toLocaleString()} context chars</span>
                </div>
              )}
              <Answer result={graphRagResult} onZoom={setSelectedImage} />
              {graphRagResult.retrieved_chunks && graphRagResult.retrieved_chunks.length > 0 && (
                <div className="text-xs border-t border-slate-800 pt-3" data-testid="chunks">
                  <div className="font-semibold text-slate-400 mb-2">Retrieved chunks (why each one won):</div>
                  <div className="space-y-2">
                    {graphRagResult.retrieved_chunks.map((c, i) => (
                      <div key={i} className="p-2.5 bg-slate-950 rounded border border-slate-800 text-slate-300 font-mono text-[11px]">
                        <div className="text-blue-400 font-semibold mb-1 flex flex-wrap gap-x-3">
                          <span>[{i + 1}] {c.title}</span>
                          <span className="text-slate-500">dense rank {c.dense_rank ?? "-"} · BM25 rank {c.bm25_rank ?? "-"} · RRF {c.hybrid_score}</span>
                        </div>
                        <div className="text-slate-400 line-clamp-2">{c.text}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {graphRagResult.graph_subgraph && graphRagResult.graph_subgraph.nodes.length > 0 && (
                <div className="text-xs border-t border-slate-800 pt-3" data-testid="graph-nodes">
                  <div className="font-semibold text-slate-400 mb-1.5">Graph entities used as facts:</div>
                  <div className="flex flex-wrap gap-1.5">
                    {graphRagResult.graph_subgraph.nodes.filter((n: any) => n.label !== "Document").slice(0, 14).map((n: any) => (
                      <span key={n.id} className="px-2 py-0.5 rounded-full bg-blue-950 text-blue-300 border border-blue-800 text-[10px]">{n.label}: {n.name}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-500 text-xs py-12">Ready. Pick a scenario or type a question.</div>
          )}
        </div>

        {/* Track B */}
        <div className="bg-slate-900/70 border border-amber-900/40 rounded-2xl p-5 shadow-xl flex flex-col min-h-[460px]" data-testid="panel-okf">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-amber-950 text-amber-400 border border-amber-800"><Compass className="w-5 h-5" /></div>
              <div>
                <h3 className="font-bold text-sm text-slate-100">Track B: Google OKF (agentic navigation)</h3>
                <p className="text-[11px] text-slate-400">Agent lists, greps and reads whole Markdown documents</p>
              </div>
            </div>
            {okfAgentResult && !okfAgentResult.error && (
              <span className="flex items-center gap-1 text-xs px-2.5 py-1 rounded bg-amber-950/80 text-amber-300 font-mono border border-amber-800">
                <Clock className="w-3 h-3" />{okfAgentResult.latency_seconds}s
              </span>
            )}
          </div>
          {loading && !okfAgentResult ? (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-500 py-12">
              <div className="w-8 h-8 border-2 border-amber-500/20 border-t-amber-500 rounded-full animate-spin mb-3" />
              <p className="text-xs">The agent is navigating the OKF knowledge base...</p>
            </div>
          ) : okfAgentResult ? (
            <div className="space-y-4 flex-1">
              {okfAgentResult.agent_trajectory && (
                <div className="p-3 bg-amber-950/20 border border-amber-800/40 rounded-xl space-y-1.5 text-xs" data-testid="trajectory">
                  <div className="font-semibold text-amber-400 mb-1 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Navigation trajectory</span>
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-amber-950 border border-amber-800 text-amber-300">{okfAgentResult.agent_mode}</span>
                  </div>
                  {okfAgentResult.agent_trajectory.map((step, idx) => (
                    <div key={idx} className="flex items-start gap-2 font-mono text-[11px] text-slate-300">
                      <span className="text-amber-400 shrink-0">{step.step}.</span>
                      <span><span className="text-amber-300">{step.action}</span>
                        {step.args && Object.keys(step.args).length > 0 ? `(${Object.values(step.args).join(", ")})` : "()"}
                        {" → "}{step.observation}</span>
                    </div>
                  ))}
                  {okfAgentResult.inspected_documents && (
                    <div className="text-[11px] text-slate-400 pt-1">Opened in full: {okfAgentResult.inspected_documents.join(", ") || "none"} · {okfAgentResult.context_chars?.toLocaleString()} chars of context</div>
                  )}
                </div>
              )}
              <Answer result={okfAgentResult} onZoom={setSelectedImage} />
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-500 text-xs py-12">Ready. Pick a scenario or type a question.</div>
          )}
        </div>
      </div>

      {selectedImage && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setSelectedImage(null)}>
          <div className="relative max-w-5xl max-h-[92vh] bg-slate-900 p-2 rounded-2xl border border-slate-700 shadow-2xl">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={selectedImage} alt="Enlarged figure" className="rounded-xl max-h-[86vh] object-contain bg-white" />
            <button onClick={() => setSelectedImage(null)} className="absolute top-4 right-4 bg-slate-800 text-white px-3 py-1 rounded-full text-xs border border-slate-600">Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
