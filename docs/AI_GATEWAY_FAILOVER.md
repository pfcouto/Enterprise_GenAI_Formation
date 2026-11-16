# AI gateway failover: how to set it up (and teach it)

**The problem.** Free LLM tiers are capped (OpenRouter: 20 requests/minute and 50/day unless the account holds $10 of credit), providers have outages, and models disappear every few weeks. If each service calls one provider directly, every limit is an outage of *your* product.

**The gateway answer.** Services call a stable **alias** (`formation-fast`). A gateway (LiteLLM) sits in between and owns the providers, the keys and the failover rules. When provider A hits its limit, the gateway silently serves the request from provider B. That is the single most useful thing an AI gateway does, and it is configured in one file: `config/litellm_config.yaml`.

![Gateway failover diagram](diagrams/ai_gateway_failover_1.png)

*Source: `diagrams/ai_gateway_failover_1.mmd`.*

## LiteLLM in five minutes: providers, models, accounts, local

**What LiteLLM is.** A small server that speaks the OpenAI API (port 4000 inside Docker, <http://localhost:14000> from your machine) and translates it to ~100 providers. Your code always sends `model="formation-fast"`; `config/litellm_config.yaml` decides which real provider and model answers.

**The model line is `<provider>/<model>`.** Everything before the first slash selects the provider adapter; everything after is the provider's own model id. So *yes, you can pin one specific model from one specific provider*, and you swap it by editing one line:

| Provider | `model:` value | Key | Account? | Cost |
|---|---|---|---|---|
| OpenRouter, free model | `openrouter/google/gemma-4-31b-it:free` | `OPENROUTER_API_KEY` | **Yes, free account + API key**. **50 free requests/day**, 20/min; **$10 of credit lifts it to 1,000/day** | free |
| OpenCode Zen, paid model | `openai/deepseek-v4.1-flash` + `api_base: https://opencode.ai/inference/openai/v1` | `OPENCODE_API_KEY` | Yes, with a prepaid balance | $0.30 in / $1.20 out per 1M tokens |
| OpenCode **free** models (e.g. `deepseek-v4.1-flash-free`) | not usable here | n/a | n/a | n/a |
| LM Studio / Ollama on your Mac | `openai/local-model` + `api_base: http://host.docker.internal:1234/v1` | any text | No | free, but slow on a laptop |

* **OpenCode free models do not work through an API key.** We called `deepseek-v4.1-flash-free` with a valid key and got `FreeTierError: OpenCode's free tier can only be used from within OpenCode`. The free tier is for the OpenCode app only. The paid `deepseek-v4.1-flash` (no `-free`) works with a key and costs cents.
* **OpenRouter free models need no payment, but they do need an account and a key.** The `:free` suffix is part of the model id. The daily cap is per account, not per model, which is the reason the gateway has a failover ladder.
* The local model is served by whatever is loaded in LM Studio: the config says `local-model` and LM Studio answers with the loaded model, so swapping models happens in LM Studio, not in LiteLLM.

**Three ways to choose, and where each lives**

1. **Default (failover ladder):** call `formation-fast`. OpenCode first, then OpenRouter free, then the fallback aliases, with `formation-local` as the very last resort. This is what the UI uses.
2. **Pinned model:** call `formation-opencode` or `formation-openrouter-free`. One provider, one model, no failover. Select them in the UI model selector. Use this to show or debug a single provider.
3. **Local for the presentation:** select `formation-local` in the UI (offline, no quota, no key). It is also the last rung of the ladder, so it only answers when every online provider failed. If you want it to be the *only* answer during a demo, pick it explicitly; nothing else needs to change.

To add a provider: add one `- model_name: ...` entry (copy a block), put its key in `.env` (the gateway container reads every key in `.env`, and in the file `SECRETS_FILE` points to), then `docker compose up -d --force-recreate litellm`. Available models are listed live by the provider (`GET https://openrouter.ai/api/v1/models`, `GET https://opencode.ai/inference/openai/v1/models`) and by the UI's *Free Models* page.

## The three layers

| Layer | Config | Behaviour |
|---|---|---|
| **1. Deployments in order** | several `- model_name: formation-fast` entries, each with `order: 1`, `2`, `3`... and `router_settings.enable_pre_call_checks: true` | The router tries `order: 1`. If the call fails (429, 5xx, timeout) it is **retried** (`num_retries`) on the next deployment of the same alias. |
| **2. Cooldown** | `allowed_fails: 1`, `cooldown_time: 30` | A deployment that failed is **skipped for 30 s**. Later requests do not waste time on it, then it is tried again (self-healing). |
| **3. Alias fallbacks** | `fallbacks: [{formation-fast: [formation-reasoning, formation-local]}]` | If the entire alias fails, the gateway tries another alias (another model family, then a local model). |

Your application adds the last safety net (this repository does): if the gateway still fails, return an **extractive answer** (retrieved passages, clearly labelled), never a made-up one.

## Set it up

1. **One key per provider** in `.env` (a provider you do not use can stay empty; its deployment just fails fast and is put in cooldown).
2. **One deployment per provider** under the same alias, with increasing `order`:

```yaml
model_list:
  - model_name: formation-fast
    litellm_params:
      model: openai/deepseek-v4.1-flash                       # OpenCode Zen speaks the OpenAI protocol
      api_base: https://opencode.ai/inference/openai/v1
      api_key: "os.environ/OPENCODE_API_KEY"
      order: 1
  - model_name: formation-fast
    litellm_params:
      model: openrouter/nvidia/nemotron-3.5-super-vl:free
      api_key: "os.environ/OPENROUTER_API_KEY"
      order: 2
  - model_name: formation-fast
    litellm_params:
      model: groq/llama-3.3-70b-versatile          # check the id on the provider's model list: ids change
      api_key: "os.environ/GROQ_API_KEY"
      order: 3

router_settings:
  enable_pre_call_checks: true
  num_retries: 2
  allowed_fails: 1
  cooldown_time: 30
  fallbacks:
    - formation-fast: ["formation-reasoning", "formation-local"]
```
3. Run `docker compose up -d --force-recreate litellm` (the container reads every key in `.env`; nothing to add in `docker-compose.yml`).
4. **Check the live model list** before you rely on an id: `curl localhost:18000/api/models/free` (OpenRouter) or the provider's own `/models` endpoint.

Providers with a free API tier that fit this pattern: **OpenRouter** (free models, capped), **Groq**, **Google AI Studio (Gemini)**, **Mistral La Plateforme**. Local servers (**LM Studio**, **Ollama**) are OpenAI-compatible too and make a good last rung.

## Provider #1 in this project: OpenCode Zen (pay-as-you-go)

OpenCode Zen is a paid, pay-as-you-go API gateway for models; the Console says its endpoints are for "applications calling the endpoints directly". We use **`deepseek-v4.1-flash`** ($0.30 input / $1.20 output per 1M tokens; tool calling works, which the agent track needs).

* `OPENCODE_API_KEY` in `.env`; base URL `https://opencode.ai/inference/openai/v1` for OpenAI-compatible models (DeepSeek, GLM, Kimi...) and `https://opencode.ai/inference/anthropic` for the models Zen serves through the Anthropic Messages API (Claude, Qwen3.8 Flash). The older `https://opencode.ai/zen/v1` still answers chat calls, and the model list is at `https://opencode.ai/zen/v1/models` (with your key). Add the key to the `litellm` container environment (already done in `docker-compose.yml`).
* **Measured cost:** the complete 34-question evaluation of **both** tracks (68 runs, about 840,000 tokens) cost **about $0.28**. Through a restricted trainee key, three dual-track questions (both tracks answering the same question, as the UI does) cost **$0.032**: **about $0.01 per click** (Track A about 3k tokens, the agent track 20-60k because it reads whole documents). Twenty trainees asking twenty questions each is therefore on the order of **$4**: set `--budget 0.50` per key (about 45 clicks).
* **Rate limit matters:** one click makes 4-8 gateway requests (the agent calls tools in a loop). With `--rpm 12` one answer waited **82 s** on 429 + retry backoff; use `--rpm 30` or more.
* `input_cost_per_token` / `output_cost_per_token` in the deployment let the gateway compute spend, which is what makes per-key budgets (next section) work.

> **What does NOT work as a backend, and why.** OpenCode's **free** models answer `FreeTierError: OpenCode's free tier can only be used from within OpenCode` when called through the API (the Zen docs: *"Free-tier chat models only work through OpenCode"*). The **Go** subscription has its own endpoint (`https://opencode.ai/inference/go/v1/...`) and the Zen docs say paid models and Go *"can be used from other clients"*, but the Go docs describe those clients: Go is *"designed for OpenCode and other coding agents that produce similar types of requests"*, clients must *"send typical coding agent traffic"*, identify with their own user agent and *"send a stable session ID in `x-opencode-session`"*, and *"traffic is monitored for abuse"*. RAG answers and judge calls from our own service are not coding-agent traffic, so we did not put Go behind the gateway. Go is fine inside OpenCode and other coding agents; for a service behind your own gateway use the pay-as-you-go **Zen** balance. Always read a provider's terms before putting it behind your own service.

## The judge panel: three pinned aliases

The evaluation grades answers with three judges of different families (`backend/evaluation/langfuse_evals.py`, `JUDGE_PANEL`):

| Alias | Model | Price per 1M tokens (in / out) | Note |
|---|---|---|---|
| `formation-judge-deepseek` | `openai/deepseek-v4.1-flash` on Zen | $0.30 / $1.20 | the same model that writes the answers (self-preference) |
| `formation-judge-haiku` | `anthropic/claude-haiku-5-5` on Zen (`api_base: https://opencode.ai/inference/anthropic`) | $0.10 / $0.50 | cheaper than Qwen3.8 Flash ($0.15 / $0.47), which also spends output tokens on thinking |
| `formation-judge-nemotron` | `openrouter/nvidia/nemotron-3.5-super-vl:free` | free | 50 requests/day on a free OpenRouter account |

The judge aliases have **no failover on purpose**: a judge silently replaced by another model would make its scores meaningless. All three are reasoning models: give them `max_tokens` of about 3,000 or they spend the budget thinking and return nothing.

**Thinking level** (measured 2026-10-25, six calls per setting): Haiku on Zen thinks about 250 tokens by default; `thinking: {type: disabled}` in its `litellm_params` brings that to 0, cuts its output by about 70 % and makes its grades steadier. DeepSeek V4.1 Flash on Zen showed no measurable difference between `reasoning_effort` low, high and the default (each ranged about 550-1,950 tokens; Zen spreads calls over upstream providers, one of which rejects `none`), so nothing is set for it. Nemotron gets `reasoning_effort: low` (accepted by OpenRouter; effect not measured yet). A setting in `litellm_params` applies to every caller of the alias, which is the point of a gateway.

## Sharing the gateway with trainees: virtual keys

The provider key (OpenCode, OpenRouter...) must never be handed out. A gateway issues its own **virtual keys**, each limited to chosen aliases, with a budget, a rate limit and an expiry. This needs the gateway database (`litellm-db`, already in `docker-compose.yml`).

```bash
python scripts/create_trainee_key.py --count 20 --budget 0.50 --rpm 30 --hours 8 --alias room-a
# prints one key per trainee:  room-a-01  sk-...
```

Each trainee puts two lines in their `.env` and runs `docker compose up -d`:

```
LITELLM_URL=http://<speaker-ip>:14000/v1
LITELLM_MASTER_KEY=<the virtual key they received>
```

What we tested on a throw-away key (`formation-fast` only, `$0.02`, 3 requests/minute):

| Request with the trainee key | Result |
|---|---|
| model `formation-fast` | **200**, answered |
| model `formation-reasoning` (another alias) | **403** *not available for this API key* |
| `deepseek-v4-pro`, `openrouter/openai/gpt-4o` (other models / wildcard) | **403** |
| 4 requests in one minute (limit 3) | **200, 200, 429, 429** |
| spending past `max_budget` (tested with $0.0003) | **422 Budget has been exceeded** after 2 requests |

Operational checklist for a shared gateway:
* **Change `LITELLM_MASTER_KEY`** from the demo default before exposing the gateway (it is the admin key: it can mint and delete keys). Keep it out of the trainees' hands.
* Trainees reach the gateway at your machine's LAN IP; set `GATEWAY_BIND=0.0.0.0` in `.env` (every port is bound to 127.0.0.1 by default), `docker compose up -d --force-recreate litellm`, and allow inbound TCP 14000 only on the training network.
* Inspect and revoke: `curl localhost:14000/key/info?key=<key>` and `POST /key/delete` (admin key), or the gateway UI.
* Restrict the **provider** side as well: in the OpenCode Console you can enable only the models you want per workspace (*Models* tab) and set monthly budgets per workspace and per member. A dedicated workspace for the formation with only `deepseek-v4.1-flash` enabled and a small monthly budget is a second, independent fence. (The Console documents workspace-level model enablement and budgets, not per-key model restrictions; the per-key restriction is done by the gateway as above. Check the Console for the exact options of your plan.)

## Prove it works without burning quota: the failover drill

The alias `formation-failover-drill` has a primary deployment pointing at a **closed port** (a simulated outage or quota wall) and a secondary that returns a canned answer.

```bash
for i in 1 2 3; do
  curl -s -i localhost:14000/v1/chat/completions \
    -H 'Authorization: Bearer sk-syone-formation-master-key' -H 'content-type: application/json' \
    -d '{"model":"formation-failover-drill","messages":[{"role":"user","content":"hi"}]}' \
  | grep -iE 'x-litellm-attempted|x-litellm-response-duration|SERVED'
done
```

What we measured:

| Call | `attempted-fallbacks` / `retries` | Duration | What happened |
|---|---|---|---|
| 1 | 1 / 0 | about 20-700 ms | tried the dead primary, failed, **served by the secondary** |
| 2 | 0 / 1 | about 10-30 ms | primary already in **cooldown**, retried straight on the secondary |
| 3 | 0 / 0 | about 2-3 ms | primary skipped, **no failure visible at all** |

Notebook 04, section 3, runs the same drill and prints this table.

## Watching it in production

* **Response headers** of every call: `x-litellm-attempted-fallbacks`, `x-litellm-attempted-retries`, `x-litellm-model-id`, `x-litellm-response-duration-ms`.
* **Langfuse** shows which underlying model answered each call (the `model` field of the trace differs from the alias you asked for).
* **Grafana / Prometheus**: *Gateway Failures & Fallbacks* panel (`litellm_deployment_failed_requests`).
* **A real example from this project:** while one OpenRouter free model had used up its daily quota, a call to `formation-reasoning` was answered with `attempted-fallbacks: 1` by a different free model chosen by OpenRouter's free router (`openrouter/openrouter/free`). The application saw a normal 200.

## Limits of the pattern (say this out loud in the session)

* Failover protects **availability**, not **consistency**: a different model may answer with a different style or quality. Keep the alias to models of comparable capability, and record which model answered (Langfuse does).
* A **daily quota** cannot be retried away within one request; only another provider helps. Cooldown keeps you from hammering a blocked provider.
* Fallbacks multiply latency in the worst case (every layer tried in turn). Set `timeout` and `num_retries` deliberately.
* Do not fail over to a model that your data policy does not allow.
