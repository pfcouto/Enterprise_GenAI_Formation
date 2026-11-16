"""
Shared LLM-gateway client + prompt builders used by both retrieval tracks.

All model traffic goes through the LiteLLM gateway (OpenAI-compatible). If the gateway or the model is not reachable
(no API key yet, rate limit, offline) a `GatewayError` is raised and the pipelines fall back to an EXTRACTIVE answer:
the best retrieved passages, clearly labelled as such. The system never invents an answer and never pretends the LLM ran.
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

def _load_dotenv() -> None:
    """Host-side scripts and notebooks read the same .env as docker-compose (only the connection settings, never overriding the environment)."""
    env = Path(__file__).parent.parent / ".env"
    if not env.exists():
        return
    wanted = ("LITELLM_", "LANGFUSE_", "NEO4J_", "QDRANT_")
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if key.startswith(wanted):
                os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()
LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:14000/v1")
LITELLM_MASTER_KEY = os.getenv("LITELLM_MASTER_KEY", "sk-syone-formation-master-key")

OFFLINE_BANNER = ("**Offline extractive mode** - the LLM gateway could not answer ({reason}). "
                  "Below are the most relevant passages found by the retrieval track, unmodified. "
                  "Add a free OpenRouter key to `.env` (or enable a local model) to get generated answers.")


RETRYABLE = {408, 429, 502, 503}
RETRY_WAITS = tuple(int(x) for x in os.getenv("LLM_RETRY_WAITS", "8,25,45").split(","))


class GatewayError(Exception):
    """The LLM gateway/model could not produce a completion."""


async def chat(messages: List[Dict[str, Any]], model: str, tools: Optional[List[Dict[str, Any]]] = None,
               temperature: float = 0.2, max_tokens: int = 3000, timeout: float = 300.0) -> Dict[str, Any]:
    """One chat completion through LiteLLM. Returns the assistant message dict (may contain tool_calls)."""
    payload: Dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    if tools:
        payload["tools"] = tools
    headers = {"Authorization": f"Bearer {LITELLM_MASTER_KEY}", "Content-Type": "application/json"}
    # Free tiers rate-limit (429) and providers blip (502/503/408): retry with growing waits before giving up.
    resp = None
    for attempt, wait in enumerate((0,) + RETRY_WAITS):
        if wait:
            await asyncio.sleep(wait)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{LITELLM_URL}/chat/completions", json=payload, headers=headers)
        except Exception as e:  # noqa: BLE001
            if attempt == len(RETRY_WAITS):
                raise GatewayError(f"gateway unreachable: {type(e).__name__}") from e
            continue
        if resp.status_code not in RETRYABLE or attempt == len(RETRY_WAITS):
            break
        if resp.status_code == 429 and "per-day" in resp.text:
            break  # a daily quota cannot be retried away within a request
    if resp.status_code != 200:
        detail = resp.text[:200].replace("\n", " ")
        raise GatewayError(f"gateway HTTP {resp.status_code}: {detail}")
    try:
        msg = resp.json()["choices"][0]["message"]
    except Exception as e:  # noqa: BLE001
        raise GatewayError("malformed gateway response") from e
    if not (msg.get("content") or msg.get("tool_calls")):
        raise GatewayError("empty completion")
    return msg


def figures_block(images: List[Dict[str, Any]]) -> str:
    """The figures the model is ALLOWED to cite: it never sees pixels, so it gets path + caption + text description."""
    if not images:
        return "(no figures are associated with the retrieved material)"
    out = []
    for img in images:
        desc = (img.get("description") or img.get("caption") or "").strip()
        out.append(f"- ![{img.get('caption', '')[:90]}]({img['path']})\n  what it shows: {desc[:420]}")
    return "\n".join(out)


FIGURE_RULES = (
    "FIGURES: you cannot see images, but the section 'AVAILABLE FIGURES' lists each figure with a text description of what it shows. "
    "When a figure is relevant to the question (a map, diagram, LED legend, flowchart...), include its exact markdown image line "
    "`![caption](/static/images/...)` in your answer so the reader can verify it. Never invent image paths."
)

GRAPHRAG_PROMPT = """You are a careful technical assistant answering from a private knowledge base.
Answer ONLY from the retrieved passages and graph facts below. Quote codes, ports, values and names exactly as written.
If the material does not contain the answer, say so plainly instead of guessing.
{figure_rules}

=== RETRIEVED PASSAGES (hybrid dense + BM25) ===
{text_context}

=== KNOWLEDGE-GRAPH FACTS (Neo4j) ===
{graph_context}

=== AVAILABLE FIGURES ===
{figures}
"""

OKF_PROMPT = """You are an autonomous knowledge agent navigating an OKF knowledge base (a folder of Markdown files with YAML frontmatter).
You explore it with tools, read whole documents (no chunking) and answer ONLY from what you read.
Quote codes, ports, values and names exactly as written. If you cannot find the answer, say so.
{figure_rules}

Workflow: 1) list_okf_topics  2) grep_okf for exact terms/codes  3) read_okf_document for the best candidates
4) follow_related_links if the answer spans documents  5) answer. Be economical: stop as soon as you can answer.
"""

OKF_SYNTH_PROMPT = """You are an autonomous knowledge agent that navigated an OKF knowledge base. The complete, un-chunked documents you opened are below.
Answer ONLY from them. Quote codes, ports, values and names exactly as written. If the documents do not contain the answer, say so.
{figure_rules}

=== OPENED OKF DOCUMENTS ===
{documents}

=== AVAILABLE FIGURES ===
{figures}
"""


def extractive_answer(passages: List[Dict[str, Any]], images: List[Dict[str, Any]], reason: str, limit: int = 3) -> str:
    """Honest no-LLM answer: the best passages verbatim + the figures that go with them."""
    parts = [OFFLINE_BANNER.format(reason=reason)]
    for p in passages[:limit]:
        text = re.sub(r"\s+", " ", p.get("text", "")).strip()
        parts.append(f"> **{p.get('title', p.get('doc_id', 'source'))}**: {text[:700]}")
    for img in images[:2]:
        parts.append(f"![{img.get('caption', '')[:90]}]({img['path']})")
    return "\n\n".join(parts)
