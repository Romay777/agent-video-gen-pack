# Research: tracking each client's spend when you provide the OpenRouter access

*Owner-facing document, not instructions for video-making agents. Researched 2026-10-12 from OpenRouter's public docs, its public `/api/v1/models` list, and LiteLLM's docs. Nothing here was tested with a real API key, so the "unverified" items are listed at the end as a checklist.*

## Recommendation

**Do not give clients your real OpenRouter key. Put a small relay on your own server, give each client a key that only your relay understands, and write one ledger row per request.**

```
 client machine                         your server                          OpenRouter
┌──────────────────┐   ck_live_...   ┌─────────────────────────┐  sk-or-... ┌──────────────┐
│ agent-video-gen- │ ───────────────▶│ relay                   │───────────▶│ /audio/speech│
│ pack (unchanged) │ ◀───────────────│  · auth client key      │◀───────────│              │
└──────────────────┘   audio bytes   │  · limits / budget      │ audio +    └──────────────┘
                                     │  · inject user=client_id│ X-Generation-Id     ▲
                                     │  · ledger row           │                     │
                                     └───────────┬─────────────┘   GET /generation?id=
                                                 │ later: fill real cost ───────────┘
                                                 ▼
                                          ledger DB (SQLite → Postgres)
```

Why this and not the alternatives:

- **Zero changes in this repo.** `scripts/tts.py` already honours `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`. Clients set `OPENROUTER_BASE_URL=https://relay.yourdomain/v1` and `OPENROUTER_API_KEY=<their client key>`; the `openai` SDK call is identical.
- **The real key never leaves your server**, so a leaked client key costs you one revocation, not a rotated master key and every other client.
- **You control what can be spent**: model allow-list, max characters per request, per-client daily/monthly budget, rate limit. OpenRouter-side per-key limits only cap dollars.
- **Attribution is yours**, not dependent on dashboards that retain 30 days of daily aggregates (see below).
- **It is small**: one forwarding endpoint, one table. The TTS surface is a single endpoint (`POST /audio/speech`).

Use OpenRouter's own per-key limits *in addition* as a safety net (e.g. one capped "relay" key per tier), not as the accounting system.

## What OpenRouter gives you (and what it doesn't)

| Capability | What the docs say | Use for billing? |
| --- | --- | --- |
| `user` field on `/audio/speech` | Accepted, string ≤ 256 chars, "End-user identifier for Broadcast and private logging. Not sent to the provider" ([speech API spec](https://openrouter.ai/docs/api/api-reference/tts/create-speech)). Also `session_id` (≤ 256) and `trace` metadata. | Yes, as the tag you attach on every request. The relay should **overwrite** it with the real `client_id`, never trust a client-sent value. |
| `X-Generation-Id` response header | Listed in the model's own `llms.txt` ("identifies the billed generation"); the OpenAPI spec page does not document response headers. `scripts/tts.py` already prints it. | Yes: the join key to the cost lookup. |
| `GET /api/v1/generation?id=` | Returns `total_cost` (USD), `upstream_inference_cost`, tokens (`native_tokens_*`), `model`, `provider_name`, `is_byok`, `external_user`, `session_id`, `app_id`, `latency`, and `api_type` whose enum includes `tts`. **No API-key field.** Docs don't say how soon after the request the row exists ([spec](https://openrouter.ai/docs/api/api-reference/generations/get-generation)). | **Yes: the authoritative per-request cost.** Fetch it asynchronously with retry. |
| `GET /api/v1/activity` | Needs a **management key**. Filters: `date` (a single UTC day, last 30 completed days only), `api_key_hash`. Rows are aggregated by date × model × endpoint/provider with `usage` (USD), `requests`, token counts. No per-`user` breakdown documented ([spec](https://openrouter.ai/docs/api/api-reference/analytics/get-user-activity)). | Only for **reconciliation** of your ledger. 30-day window and no per-client grouping make it unsuitable as the record. |
| Management API keys | `POST/GET/PATCH/DELETE /api/v1/keys`. Create takes `name`, optional `limit`; update takes `name`, `disabled`, `limit_reset` (example: `daily`), `include_byok_in_limit`. Responses carry `usage`, `usage_daily`, `usage_weekly`, `usage_monthly`, `limit_remaining`. Lists return 100 per page ([docs](https://openrouter.ai/docs/guides/overview/auth/management-api-keys)). | A fine **optional** layer: per-client capped keys created by script. Does not hide the key from the client. |
| Spend controls / guardrails | Per-key limits (daily/weekly/monthly reset), per-member limits, workspace budgets; the first limit hit blocks the request. Workspace budgets appear to be an enterprise feature per one secondary source; plans weren't confirmed ([docs](https://openrouter.ai/docs/guides/best-practices/spend-controls)). | Safety net only. |
| Broadcast → Langfuse | Send traces from OpenRouter to Langfuse from *Settings → Observability*. `user` maps to Langfuse User ID, `session_id` to Session; extra `trace` keys become metadata; privacy mode strips prompts but keeps cost/tokens ([OpenRouter](https://openrouter.ai/docs/guides/features/broadcast/langfuse), [Langfuse](https://langfuse.com/integrations/gateways/openrouter)). Whether TTS requests are broadcast was **not confirmed**. | Nice dashboard, **not** a billing source of truth and does not enforce anything. Optional add-on, free to set up once the `user` tag is in place. |

### Cost is not uniform across TTS models

From OpenRouter's public models list (`GET /api/v1/models?output_modalities=speech`, prices in USD, as of today):

| Model | Pricing fields | Reading |
| --- | --- | --- |
| `google/gemini-3.8-flash-tts` (default) | prompt `0.0000005`, completion `0.000009` | $0.50 / 1M **input text tokens** + $9 / 1M **output audio tokens** |
| `google/gemini-3.8-flash-lite-tts` | `0.0000005` / `0.000006` | same shape, cheaper audio |
| `elevenlabs/eleven-v3` | prompt `0.00004` | ≈ $40 / 1M **characters** |
| `microsoft/mai-voice-2.1-flash` | prompt `0.000015` | ≈ $15 / 1M characters |
| `bytedance-seed/seed-audio-1-0` | completion `0.0025` | billed on the **output** side (unit not verified) |

So "track characters" is only a proxy: for Gemini the bill is driven by audio tokens (longer or slower delivery costs more for the same text), and ElevenLabs bills per input character. **Record the cost OpenRouter reports, and keep characters/seconds only as a fallback estimate.** When a lookup fails, estimate from a pricing snapshot and mark the row `cost_source='estimated'`; calibrate that estimate (cost vs. seconds of audio per model) from your first few dozen real rows rather than from assumptions.

## Options compared

| | A. One OpenRouter key per client | B. One key + `user` tag + Langfuse | **C. Own relay + ledger** | D. LiteLLM proxy |
| --- | --- | --- | --- | --- |
| Client sees your OpenRouter key | **Yes** (leak = their problem becomes yours) | **Yes** | **No** | No |
| Per-client attribution | Native (key) | By `user` tag, trusts the caller | By your auth, authoritative | By virtual key / user |
| Hard spend cap | OpenRouter `limit` per key | None | Your budget check (+ optional OR limit) | LiteLLM `max_budget` |
| Per-request records | No (daily aggregates, 30-day window) | Langfuse traces | Your DB, as long as you want | Postgres SpendLogs |
| Model / size abuse control | Key can call any model | None | Allow-list, max chars, rate limit | Per-key model lists |
| Effort | Script, ~0 infra | Settings + tag | ~150 lines + DB + a small VPS | Postgres + deploy + ops |
| Main risk | Key exfiltration, no detail | Easy to spoof / bypass | You own uptime | See below |

**Why not LiteLLM here.** It is a real option (virtual keys, budgets, SpendLogs, `/spend/logs/v2`), but for this use case it looked like more risk than value:

- Its [text-to-speech docs](https://docs.litellm.ai/docs/text_to_speech) list OpenAI, Azure, Vertex/Gemini, ElevenLabs, etc. and do not mention OpenRouter as a TTS provider or an `instructions` parameter; whether `/audio/speech` through OpenRouter is priced correctly was not established.
- It needs Postgres and has a large feature surface you don't need for a single endpoint.
- LiteLLM's PyPI package was **compromised on 2026-03-24** (versions 1.82.7 and 1.82.8, credential-stealing payload, reported by several security vendors; not checked against LiteLLM's own advisory). Patched and the official Docker image was reportedly unaffected, but a proxy that holds your master OpenRouter key is the worst place for a supply-chain event. If you ever adopt it: pin the version, use the official image, and keep the key in a secret store.

I did not evaluate Portkey, Helicone or similar hosted gateways.

## Your question about "limits on API keys"

I could not find a documented cap on the *number* of OpenRouter API keys. The management-API docs mention pagination (100 per page) and per-key credit limits but no count limit; the team-spend docs mention a member limit for organizations (10 by default). If you hit something specific, it is probably a plan/organization limit; ask OpenRouter support. In any case, creating keys is **one API call**, not manual work:

```bash
curl -X POST https://openrouter.ai/api/v1/keys \
  -H "Authorization: Bearer $OPENROUTER_MANAGEMENT_KEY" -H "Content-Type: application/json" \
  -d '{"name":"client-acme","limit":20}'      # limit in USD; reset via PATCH {"limit_reset":"monthly"} (daily shown in docs)
```

If you prefer option A for the first few clients (fastest to ship), it works, but you accept key exposure and aggregate-only reporting.

## Design of the relay + ledger (option C)

**Request path** (`POST /v1/audio/speech`; add other endpoints only if you need them):

1. Authenticate `Authorization: Bearer ck_live_…` against `client_keys` (store only `sha256`); resolve `client_id`; reject disabled clients.
2. Enforce policy: model in allow-list (e.g. `google/gemini-3.8-flash-tts`), `len(input) + len(instructions)` ≤ cap (e.g. 5 000 chars), rate limit per client, remaining budget > 0 (sum of `cost_usd` this period + a reserved estimate for in-flight requests).
3. Forward to `https://openrouter.ai/api/v1/audio/speech` with **your** key; set `user = client_id` (overwrite), optionally `session_id`, and `provider: {"data_collection": "deny"}` if you want to avoid training-data routes. Stream the bytes back.
4. Insert `usage_events` immediately with what you know; take `X-Generation-Id` from the upstream response.
5. Background worker: `GET /generation?id=<gen id>` with backoff (e.g. 2 s, 5 s, 15 s, 60 s…), write `cost_usd`, tokens, provider, `cost_source='openrouter'`. On permanent failure fall back to the estimate.

**Tables (SQLite is enough to start; keep SQL portable):**

```sql
clients(id TEXT PK, name, email, created_at, status, monthly_budget_usd, markup_pct)
client_keys(key_hash TEXT PK, client_id, label, created_at, revoked_at)
usage_events(
  id INTEGER PK, ts, client_id, key_hash,
  endpoint,                 -- 'audio/speech'
  model, voice, response_format,
  input_chars, instructions_chars, audio_seconds, bytes,
  generation_id,            -- X-Generation-Id
  http_status, latency_ms,
  cost_usd, cost_source,    -- 'openrouter' | 'estimated' | NULL (pending)
  native_tokens_prompt, native_tokens_completion, provider_name
)
```

**Invoice query:**

```sql
SELECT client_id, model, COUNT(*) AS requests,
       SUM(input_chars) AS chars, SUM(audio_seconds) AS seconds,
       ROUND(SUM(cost_usd), 4) AS cost_usd,
       SUM(cost_source = 'estimated') AS estimated_rows
FROM usage_events
WHERE ts >= :month_start AND ts < :next_month_start AND http_status = 200
GROUP BY client_id, model;
```

**Reconciliation (daily cron):** call `/api/v1/activity?date=<yesterday>` with the management key and compare `sum(usage)` to `sum(cost_usd)` for the same UTC day in your ledger; alert on > 2–5 % drift. Because Activity keeps only 30 days, this must run continuously, not at month end. Also watch the account credit balance so clients don't hit a 402 mid-render.

**What to store about content:** don't store narration text by default (clients' scripts are theirs); lengths and a hash are enough for billing and support. Decide this deliberately and say so in your terms.

## Rollout path

1. **Day 0, no server:** keep using `scripts/tts.py`, add `OPENROUTER_USER=<client>` per client so requests carry a `user` tag (already supported), and enable Broadcast → Langfuse for visibility.
2. **Week 1:** build the relay (single file, FastAPI or Hono + SQLite + a worker loop), deploy on a small VPS behind TLS, issue client keys, flip clients' `OPENROUTER_BASE_URL`.
3. **Later:** budgets with soft alerts, a tiny admin page or CLI (`new-client`, `rotate-key`, `usage --month`), Postgres, per-client invoices.

I can build step 2 as `relay/` in this repo (or a separate repo) when you want it.

## Open items to verify with a real key (not testable in this research)

1. Does `GET /generation?id=` return a row for `api_type: tts` generations, with `total_cost` populated, and how many seconds after the response? (Determines the worker's retry schedule.)
2. Is `external_user` populated from the `user` field on `/audio/speech`?
3. Does `total_cost` match `prompt × input_tokens + completion × audio_tokens` for Gemini? What does `native_tokens_completion` look like for audio?
4. Do TTS requests show up in `/activity` and in Broadcast/Langfuse?
5. Is there any key-count or rate limit you actually hit on the account, and what plan do workspace budgets need?
6. **Terms of service:** I did not check OpenRouter's (or the model vendors') terms on reselling or sharing access. Check before billing clients commercially.
