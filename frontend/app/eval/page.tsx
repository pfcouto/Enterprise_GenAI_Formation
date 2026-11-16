"use client";

import React, { useState } from "react";
import { Award, Play, Wand2, CheckCircle, XCircle, AlertTriangle, Scale } from "lucide-react";
import { API } from "@/lib/api";

interface EvalResult {
  pipeline: string;
  corpus: string;
  mode: string;
  model_used: string;
  total_tests: number;
  passed_tests: number;
  pass_rate: string;
  avg_retrieval_doc_hit: number | null;
  avg_context_keyword_recall: number | null;
  avg_keyword_recall: number | null;
  avg_visual_grounding_score: number | null;
  extractive_fallbacks: number;
  avg_judge_scores: Record<string, number | null>;
  judge_disagreements: number;
  details: any[];
}

const judgeName = (alias: string) => alias.replace("formation-judge-", "");

const pct = (v: number | null | undefined) => (v === null || v === undefined ? "n/a" : `${(v * 100).toFixed(0)}%`);

const TRACK = { graph_rag: "Track A (GraphRAG + BM25)", okf_agent: "Track B (OKF agent)" } as Record<string, string>;
const CORPUS = { all: "both knowledge bases", syone_corp: "Syone website", hardware_manuals: "Aurora manuals" } as Record<string, string>;
const QUESTIONS = (limit: number) => (limit === -1 ? "demo slice" : limit > 0 ? `first ${limit}` : "all");
const secs = (ms: number) => (ms < 10000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms / 1000)} s`);

/** One sentence saying what a run actually did: which pipeline, with or without an LLM, on which questions. */
function describeRun(r: EvalResult, info: { questions: string; ms: number }) {
  const what = r.mode === "retrieval"
    ? (r.pipeline === "okf_agent"
        ? "retrieval only: the agent's scripted plan (list topics, grep, read), no LLM"
        : "retrieval only: hybrid search + graph facts, no LLM")
    : (r.pipeline === "okf_agent"
        ? `full: the LLM agent chooses the tools and answers (${r.model_used})`
        : `full: retrieval + one LLM answer per question (${r.model_used})`);
  const judged = Object.keys(r.avg_judge_scores || {}).length > 0 ? " · judge panel on" : "";
  return `${TRACK[r.pipeline] || r.pipeline} · ${what} · ${info.questions} questions (${r.total_tests}) from ${CORPUS[r.corpus] || r.corpus}${judged} · ${secs(info.ms)}`;
}

export default function EvalPage() {
  const [evalResult, setEvalResult] = useState<EvalResult | null>(null);
  const [optimizer, setOptimizer] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [runningOpt, setRunningOpt] = useState(false);
  const [pipeline, setPipeline] = useState("graph_rag");
  const [corpus, setCorpus] = useState("all");
  const [mode, setMode] = useState("retrieval");
  const [limit, setLimit] = useState(0); // 0 = all, -1 = the demo slice
  const [judge, setJudge] = useState(false);
  const [runInfo, setRunInfo] = useState<{ questions: string; ms: number } | null>(null);
  const [optMs, setOptMs] = useState<number | null>(null);

  const runBenchmark = async () => {
    setRunning(true);
    setEvalResult(null);
    setError(null);
    const started = Date.now();
    const questions = QUESTIONS(limit);
    try {
      const res = await fetch(`${API}/api/eval/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          corpus, pipeline, mode, model_name: "formation-fast",
          limit: limit > 0 ? limit : null, demo_slice: limit === -1, judge: mode === "full" && judge,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setEvalResult(data);
      setRunInfo({ questions, ms: Date.now() - started });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  const runOptimizer = async () => {
    setRunningOpt(true);
    setOptimizer(null);
    setError(null);
    const started = Date.now();
    try {
      const res = await fetch(`${API}/api/eval/optimize-prompts`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setOptimizer(data);
      setOptMs(Date.now() - started);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunningOpt(false);
    }
  };

  const sel = "bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-xs text-slate-200";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
          <Award className="w-6 h-6 text-blue-400" />
          <span>Evaluation on the golden set (34 questions)</span>
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          <b>Retrieval mode</b> needs no LLM: it measures whether the right documents and facts reach the generator.{" "}
          <b>Full mode</b> also generates the answer and scores keywords, figure citation and refusals; the <b>judge panel</b> adds
          three LLMs of different families that grade each answer against the reference. In a live session use the demo slice:
          full mode on all 34 questions of Track B costs about $0.25 and takes minutes.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3 bg-slate-900/60 border border-slate-800 rounded-xl p-4">
        <label className="text-[11px] text-slate-400 flex flex-col gap-1">Mode
          <select className={sel} value={mode} onChange={(e) => setMode(e.target.value)} data-testid="eval-mode">
            <option value="retrieval">retrieval only (no LLM; Track B uses a scripted plan)</option>
            <option value="full">full (retrieval + answer)</option>
          </select></label>
        <label className="text-[11px] text-slate-400 flex flex-col gap-1">Track
          <select className={sel} value={pipeline} onChange={(e) => setPipeline(e.target.value)} data-testid="eval-pipeline">
            <option value="graph_rag">Track A: GraphRAG + BM25</option>
            <option value="okf_agent">Track B: OKF agent</option>
          </select></label>
        <label className="text-[11px] text-slate-400 flex flex-col gap-1">Corpus
          <select className={sel} value={corpus} onChange={(e) => setCorpus(e.target.value)}>
            <option value="all">all</option>
            <option value="syone_corp">Syone</option>
            <option value="hardware_manuals">Aurora manuals</option>
          </select></label>
        <label className="text-[11px] text-slate-400 flex flex-col gap-1">Questions
          <select className={sel} value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
            <option value={0}>all 34</option><option value={-1}>demo slice (8)</option><option value={6}>first 6</option><option value={12}>first 12</option>
          </select></label>
        <label className={`text-[11px] flex items-center gap-2 pb-2.5 ${mode === "full" ? "text-slate-300" : "text-slate-600"}`} title="Only in full mode">
          <input type="checkbox" disabled={mode !== "full"} checked={mode === "full" && judge} onChange={(e) => setJudge(e.target.checked)} data-testid="eval-judge" />
          Judge panel (3 LLMs)
        </label>
        <button type="button" disabled={running} onClick={runBenchmark} data-testid="eval-run"
          className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold rounded-xl flex items-center gap-2 text-xs shadow-lg transition">
          <Play className="w-4 h-4" /><span>{running ? "Evaluating..." : "Run benchmark"}</span>
        </button>
        <button type="button" disabled={runningOpt} onClick={runOptimizer}
          className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold rounded-xl flex items-center gap-2 text-xs shadow-lg transition ml-auto">
          <Wand2 className="w-4 h-4" /><span>{runningOpt ? "Optimizing..." : "Prompt optimization loop (needs LLM)"}</span>
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-2 text-xs text-amber-300 bg-amber-950/40 border border-amber-800/60 rounded-lg p-3">
          <AlertTriangle className="w-4 h-4 shrink-0" /><span>{error}</span>
        </div>
      )}

      {evalResult && runInfo && (
        <div className="text-xs text-slate-300 bg-slate-900/60 border border-slate-800 rounded-lg px-3 py-2 font-mono" data-testid="eval-run-info">
          <span className="text-slate-500">This run: </span>{describeRun(evalResult, runInfo)}
        </div>
      )}
      {evalResult && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4" data-testid="eval-summary">
          {[
            ["Pass rate", evalResult.pass_rate, `${evalResult.passed_tests} of ${evalResult.total_tests}`, "text-green-400"],
            ["Expected doc retrieved", pct(evalResult.avg_retrieval_doc_hit), "retrieval stage", "text-blue-400"],
            ["Facts in context", pct(evalResult.avg_context_keyword_recall), "retrieval stage", "text-blue-300"],
            ["Facts in answer", evalResult.mode === "full" ? pct(evalResult.avg_keyword_recall) : "n/a", evalResult.mode === "full" ? "generation stage" : "run in full mode", "text-amber-400"],
            ["Figure cited", evalResult.mode === "full" ? pct(evalResult.avg_visual_grounding_score) : "n/a", evalResult.mode === "full" ? "multimodal" : "run in full mode", "text-slate-300"],
          ].map(([t, v, s, c]) => (
            <div key={t as string} className="bg-slate-900/80 p-4 rounded-xl border border-slate-800">
              <div className="text-xs text-slate-400">{t}</div>
              <div className={`text-2xl font-bold mt-1 ${c}`}>{v}</div>
              <div className="text-[11px] text-slate-500 mt-0.5 font-mono">{s}</div>
            </div>
          ))}
        </div>
      )}
      {evalResult && Object.keys(evalResult.avg_judge_scores || {}).length > 0 && (
        <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 space-y-2" data-testid="judge-summary">
          <div className="text-xs text-slate-400 flex items-center gap-1.5"><Scale className="w-3.5 h-3.5 text-amber-400" />Judge panel: average grade (0-1) of the same answers</div>
          <div className="flex flex-wrap gap-6">
            {Object.entries(evalResult.avg_judge_scores).map(([j, v]) => (
              <div key={j}><div className="text-xl font-bold text-amber-300">{v === null ? "n/a" : v.toFixed(2)}</div><div className="text-[11px] font-mono text-slate-500">{judgeName(j)}</div></div>
            ))}
            <div><div className="text-xl font-bold text-slate-200">{evalResult.judge_disagreements}</div><div className="text-[11px] font-mono text-slate-500">answers where judges disagree</div></div>
          </div>
        </div>
      )}
      {evalResult && evalResult.extractive_fallbacks > 0 && (
        <div className="text-xs text-amber-300">{evalResult.extractive_fallbacks} answers fell back to extractive mode (LLM unreachable): they count as failed.</div>
      )}

      {optimizer && (
        <div className="bg-slate-900 border border-blue-800/60 p-5 rounded-2xl shadow-xl space-y-3">
          <div className="font-bold text-sm text-blue-400">Prompt variants scored on the real pipeline (best: {optimizer.best_variant})</div>
          <div className="text-xs text-slate-300 font-mono" data-testid="optimizer-run-info">
            <span className="text-slate-500">This run: </span>Track A (GraphRAG + BM25) · full: retrieval + one LLM answer per question (formation-fast) ·
            {" "}{optimizer.history.length} system prompts × {optimizer.dataset_slice.length} questions = {optimizer.history.length * optimizer.dataset_slice.length} answers
            {" "}· its own questions, mostly about figures: {optimizer.dataset_slice.join(", ")} · keyword + figure scoring{optMs !== null ? ` · ${secs(optMs)}` : ""}
          </div>
          <div className="text-[11px] text-slate-500">Scores move from run to run (models are not deterministic); compare the ranking, and run it more than once.</div>
          {optimizer.history.map((h: any) => (
            <div key={h.variant} className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono">
              <div className="flex justify-between text-slate-400 mb-1"><span className="text-blue-400 font-bold">{h.variant}</span><span className="text-green-400">{h.passed} passed</span></div>
              <div className="text-slate-300 whitespace-pre-wrap">{h.prompt}</div>
            </div>
          ))}
        </div>
      )}

      {evalResult && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-800 font-semibold text-xs text-slate-300 uppercase tracking-wider">Per-question breakdown</div>
          <div className="divide-y divide-slate-800">
            {evalResult.details.map((item, idx) => (
              <div key={idx} className="p-4 space-y-2 text-xs">
                <div className="flex items-start justify-between gap-4">
                  <div className="font-semibold text-slate-100 flex items-center gap-2">
                    {item.score.passed ? <CheckCircle className="w-4 h-4 text-green-400 shrink-0" /> : <XCircle className="w-4 h-4 text-red-400 shrink-0" />}
                    <span>{item.question}</span>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono shrink-0">{item.category}</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-[11px] text-slate-400 bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <div>Doc retrieved: <span className="text-slate-200">{pct(item.score.retrieval_doc_hit)}</span></div>
                  <div>Facts in context: <span className="text-slate-200">{pct(item.score.context_keyword_recall)}</span></div>
                  <div>Facts in answer: <span className="text-slate-200">{evalResult.mode === "full" ? item.score.found_keywords : "n/a"}</span></div>
                  <div>Figure cited: <span className="text-slate-200">{evalResult.mode === "full" ? pct(item.score.visual_grounding_score) : "n/a"}</span></div>
                </div>
                {item.score.judges && (
                  <div className="grid md:grid-cols-3 gap-2">
                    {Object.entries(item.score.judges as Record<string, { score: number; reason: string } | null>).map(([j, v]) => (
                      <div key={j} className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-[11px]">
                        <div className="flex justify-between font-mono"><span className="text-slate-400">{judgeName(j)}</span>
                          <span className={v ? (v.score >= 0.5 ? "text-green-400" : "text-red-400") : "text-slate-500"}>{v ? v.score.toFixed(2) : "no verdict"}</span></div>
                        {v && <div className="text-slate-400 mt-1">{v.reason}</div>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
