// Every tool of the stack in one place: where it is, how to log in, what it is for and when the formation uses it.
// The logins are the public demo defaults from docker-compose.yml / .env.example: change them before exposing any port.
import { API, GRAFANA_URL, JUPYTER_URL, LANGFUSE_URL, LITELLM_URL, NEO4J_URL, PROMETHEUS_URL, QDRANT_URL } from "@/lib/api";

export interface Service {
  key: string; // matches GET /api/services/status
  name: string;
  url: string;
  login?: { user?: string; password: string; note?: string };
  what: string;
  use: string;
  sessions: string;
  optional?: boolean;
}

export interface ServiceGroup {
  title: string;
  blurb: string;
  services: Service[];
}

export const SERVICE_GROUPS: ServiceGroup[] = [
  {
    title: "Apps you work in",
    blurb: "The formation console and the code that answers it.",
    services: [
      { key: "frontend", name: "Formation UI", url: "/", what: "This website: ask one question to both tracks, explore models, run the evaluation.",
        use: "Dual Compare, Evaluation, Services", sessions: "2, 3" },
      { key: "backend", name: "FastAPI backend (API docs)", url: `${API}/docs`, what: "The Python API behind the UI: both retrieval tracks, evaluation, health.",
        use: "Try POST /api/query in the docs page to see the raw JSON of an answer", sessions: "2" },
      { key: "jupyter", name: "Jupyter Lab", url: JUPYTER_URL, login: { password: "token syone2026", note: "runs on your machine: jupyter lab --notebook-dir=notebooks --port 18888 --IdentityProvider.token=syone2026" },
        what: "The five notebooks: parsing, indexing, the agent, the gateway, evaluation.", use: "Run the cells live", sessions: "1, 2, 3", optional: true },
    ],
  },
  {
    title: "Knowledge stores",
    blurb: "Where Track A keeps what it knows. Track B needs no database: it reads the OKF Markdown files directly.",
    services: [
      { key: "qdrant", name: "Qdrant dashboard", url: `${QDRANT_URL}/dashboard`, what: "Vector database: every chunk with a dense vector (meaning) and a BM25 sparse vector (exact words).",
        use: "Collections → syone_knowledge_hybrid → open a point", sessions: "2" },
      { key: "neo4j", name: "Neo4j Browser", url: NEO4J_URL, login: { user: "neo4j", password: "syone2026", note: "connect URL bolt://localhost:17687" },
        what: "Graph database: fault codes, subsystems, LED states, partners and the links between them.", use: "Run the Cypher queries from notebook 02", sessions: "2" },
    ],
  },
  {
    title: "AI gateway",
    blurb: "Every model call goes through one gateway. The app asks for an alias (formation-fast); the gateway picks the provider.",
    services: [
      { key: "litellm", name: "LiteLLM admin UI", url: `${LITELLM_URL}/ui`, login: { user: "syone", password: "syone2026" },
        what: "Models and aliases, virtual keys with budgets, spend per key, request logs.", use: "Virtual Keys, Usage, Logs", sessions: "3" },
      { key: "lmstudio", name: "LM Studio server", url: "http://localhost:1234/v1/models", what: "Optional local model behind the alias formation-local: the last rung of the failover ladder.",
        use: "Load a model in LM Studio and start its server", sessions: "3", optional: true },
    ],
  },
  {
    title: "Observability",
    blurb: "Two layers: is the system healthy (Prometheus, Grafana) and are the answers good (Langfuse traces and scores).",
    services: [
      { key: "langfuse", name: "Langfuse", url: LANGFUSE_URL, login: { user: "syone@syone.com", password: "syone2026" },
        what: "One trace per model call: prompt, answer, tokens, cost, latency and the model that really answered. Evaluation and judge scores.",
        use: "Project Enterprise GenAI Formation → Traces, Scores", sessions: "3" },
      { key: "grafana", name: "Grafana", url: GRAFANA_URL, login: { user: "syone", password: "syone2026" },
        what: "Dashboards over the Prometheus metrics: request rate, latency, tokens, failovers.", use: "Dashboards → GenAI Formation", sessions: "3" },
      { key: "prometheus", name: "Prometheus", url: `${PROMETHEUS_URL}/targets`, what: "Collects metrics every 5 s from the gateway and the backend; Grafana reads from it.",
        use: "Status → Targets: both UP", sessions: "3" },
    ],
  },
];

// Containers without a web UI: listed so nothing in `docker compose ps` is a mystery.
export const INTERNAL_SERVICES = [
  { name: "litellm-db", what: "PostgreSQL for the gateway: virtual keys, budgets, spend logs", login: "litellm / litellm" },
  { name: "langfuse-db", what: "PostgreSQL for Langfuse: users, projects, prompts", login: "langfuse / langfuse" },
  { name: "langfuse-clickhouse", what: "ClickHouse: where Langfuse stores traces and scores (fast analytics)", login: "clickhouse / clickhouse" },
  { name: "langfuse-redis", what: "Redis: Langfuse's queue between web server and worker", login: "password redispassword" },
  { name: "langfuse-minio", what: "MinIO (S3-compatible storage): raw trace events and media", login: "minio / miniosecret" },
  { name: "langfuse-worker", what: "Processes incoming traces in the background", login: "none" },
];
