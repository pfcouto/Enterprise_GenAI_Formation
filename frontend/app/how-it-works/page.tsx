import React from "react";
import Link from "next/link";
import { BookOpen } from "lucide-react";

// Static explainer: what this console is, the two tracks, and the path one question takes through the stack.

const TRACK_A = [
  ["Search Qdrant twice", "the question is turned into a dense vector (meaning) and a BM25 sparse vector (exact words); each finds its 20 best chunks", "Qdrant dashboard"],
  ["Fuse the two rankings", "Reciprocal Rank Fusion: every chunk scores 1/(60 + rank) per list, summed; the top 5 chunks win", "the chunk list in the left panel shows both ranks"],
  ["Add graph facts", "names and codes in the question are looked up in Neo4j: which subsystem, which LED, which partner", "Neo4j Browser"],
  ["Ask the model", "chunks + graph facts + the allowed figures go into one prompt, sent to the gateway alias", "Langfuse trace"],
];

const TRACK_B = [
  ["List the topics", "the agent gets the title, type, summary and entities of every document from the YAML frontmatter", "the trajectory in the right panel"],
  ["Grep for exact terms", "codes, ports and names are searched in the Markdown files, like grep in a terminal", "same"],
  ["Read whole documents", "no chunks: the best candidates are opened in full", "same"],
  ["Follow links", "the related: list in each file's YAML frontmatter leads to neighbouring documents", "same"],
  ["Answer", "the model decides at every step which tool to call next, then answers from what it read", "Langfuse: one trace per step"],
];

const PAGES = [
  ["/", "Dual Compare", "One question, both tracks at once. Pick a knowledge base and a model, then a featured scenario."],
  ["/models", "Free Models", "The gateway aliases and the free OpenRouter models available right now."],
  ["/eval", "Evaluation", "The golden set: retrieval-only (no LLM, free), full answers on a small slice, and the LLM judge panel."],
  ["/services", "Services", "Every tool of the stack with its URL, login and purpose."],
];

const CONFIG = [
  [".env", "Secrets and connection settings: provider keys (OpenCode, OpenRouter), the gateway master key, database passwords."],
  ["docker-compose.yml", "The 14 containers, their ports, and which .env values each one receives."],
  ["config/litellm_config.yaml", "The AI gateway: aliases (formation-*), the provider behind each one, the failover order, the judge panel."],
  ["config/prometheus.yml", "What Prometheus scrapes: the gateway and the backend, every 5 seconds."],
  ["config/grafana/provisioning/", "Grafana's data source and the GenAI Formation dashboard, loaded at start-up."],
  ["backend/llm.py", "The prompts of both tracks and the gateway client (retries, extractive fallback)."],
  ["backend/evaluation/", "The 34 golden questions, the scoring, the judge panel and the prompt-optimization loop."],
];

function Steps({ steps, accent }: { steps: string[][]; accent: string }) {
  return (
    <ol className="space-y-3">
      {steps.map(([t, d, see], i) => (
        <li key={t} className="flex gap-3">
          <span className={`shrink-0 w-6 h-6 rounded-full border text-xs flex items-center justify-center font-mono ${accent}`}>{i + 1}</span>
          <div className="text-xs">
            <div className="font-semibold text-slate-100">{t}</div>
            <div className="text-slate-300">{d}</div>
            <div className="text-slate-500">See it in: {see}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}

export default function HowItWorksPage() {
  return (
    <div className="space-y-8 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
          <BookOpen className="w-6 h-6 text-blue-400" /><span>How this console works</span>
        </h1>
        <p className="text-sm text-slate-300 mt-2 leading-relaxed">
          This is the demo console of the formation. It answers questions about two knowledge bases, the <b>real Syone website</b> (79 pages)
          and a <b>fictional server manual library</b> (Aurora AOR-3, 8 PDFs with tables and figures), in two different ways, side by side,
          so you can see where each one wins. Around it run the tools a company needs before it can trust such a system: an AI gateway,
          tracing, metrics and an evaluation set.
        </p>
      </div>

      <section className="grid md:grid-cols-2 gap-4">
        <div className="bg-slate-900/80 border border-blue-800/60 rounded-xl p-5 space-y-4">
          <div>
            <div className="text-xs font-mono text-blue-400">Track A, left panel</div>
            <h2 className="font-bold text-slate-100">GraphRAG + BM25: index first, then retrieve</h2>
            <p className="text-xs text-slate-400 mt-1">Documents were cut into chunks and indexed in advance. At question time it fetches a few chunks and graph facts: cheap and fast per question.</p>
          </div>
          <Steps steps={TRACK_A} accent="border-blue-700 text-blue-300" />
        </div>
        <div className="bg-slate-900/80 border border-amber-700/60 rounded-xl p-5 space-y-4">
          <div>
            <div className="text-xs font-mono text-amber-400">Track B, right panel</div>
            <h2 className="font-bold text-slate-100">OKF agent: no index, navigate the files</h2>
            <p className="text-xs text-slate-400 mt-1">The knowledge base is a folder of Markdown files in Google&apos;s Open Knowledge Format. A tool-calling agent explores it: more tokens per question, no indexing.</p>
          </div>
          <Steps steps={TRACK_B} accent="border-amber-700 text-amber-300" />
        </div>
      </section>

      <section className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-3">
        <h2 className="font-bold text-slate-100">What every model call goes through</h2>
        <p className="text-xs text-slate-300 leading-relaxed">
          Neither track talks to a model provider directly. Both send the request to the <b>LiteLLM gateway</b> and ask for an alias such as
          <code className="font-mono text-blue-300"> formation-fast</code>. The gateway decides who answers: OpenCode Zen first, then OpenRouter free models,
          then a local model, moving down the list when a provider fails or hits its limit. It records every call in <b>Langfuse</b> (trace) and
          <b> Prometheus</b> (metrics, shown in Grafana). If no model can answer, the console shows the retrieved passages with an amber banner
          instead of inventing an answer.
        </p>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/diagrams/architecture.png" alt="Architecture: data pipeline, two tracks, gateway, observability" className="w-full max-w-3xl mx-auto rounded-lg border border-slate-800" />
      </section>

      <section className="grid md:grid-cols-2 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-3">
          <h2 className="font-bold text-slate-100">The pages of this console</h2>
          <ul className="space-y-2 text-xs">
            {PAGES.map(([href, name, d]) => (
              <li key={href}><Link href={href} className="font-semibold text-blue-400 hover:text-blue-300">{name}</Link><span className="text-slate-300">: {d}</span></li>
            ))}
          </ul>
        </div>
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-3">
          <h2 className="font-bold text-slate-100">Where things are configured</h2>
          <ul className="space-y-2 text-xs">
            {CONFIG.map(([f, d]) => (
              <li key={f}><code className="font-mono text-slate-100">{f}</code><span className="text-slate-400">: {d}</span></li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
