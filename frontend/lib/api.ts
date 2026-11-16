// Browser-side endpoints. NEXT_PUBLIC_* values are inlined at build time; the defaults match docker-compose.
export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000";
export const NEO4J_URL = process.env.NEXT_PUBLIC_NEO4J_URL || "http://localhost:17474";
export const QDRANT_URL = process.env.NEXT_PUBLIC_QDRANT_URL || "http://localhost:16333";
export const LITELLM_URL = process.env.NEXT_PUBLIC_LITELLM_URL || "http://localhost:14000";
export const LANGFUSE_URL = process.env.NEXT_PUBLIC_LANGFUSE_URL || "http://localhost:13000";
export const PROMETHEUS_URL = process.env.NEXT_PUBLIC_PROMETHEUS_URL || "http://localhost:19090";
export const GRAFANA_URL = process.env.NEXT_PUBLIC_GRAFANA_URL || "http://localhost:13001";
export const JUPYTER_URL = process.env.NEXT_PUBLIC_JUPYTER_URL || "http://localhost:18888";

export const assetUrl = (path?: string) => (path && path.startsWith("/") ? `${API}${path}` : path || "");
