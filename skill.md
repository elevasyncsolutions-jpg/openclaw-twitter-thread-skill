# OpenClaw skill: viral X (Twitter) thread generator + publisher

An [OpenClaw](https://github.com/openclaw) skill with two commands:

- `thread_generate(topic, tone, tweets)` — writes a structured viral thread
  using a configurable LLM (OpenAI-compatible API; works with Gemini, Groq,
  OpenRouter, NEAR AI Inference).
- `thread_publish(thread_id)` — posts the thread to X/Twitter via API v2
  (Bearer token). No-op safe mode when `X_BEARER_TOKEN` is unset — returns a
  simulated success with the full thread text so it can be pasted manually.

## Install

```bash
mkdir -p ~/.openclaw/skills/
cp -r this-directory ~/.openclaw/skills/twitter-thread-writer
```

Set env (in `.env` or the gateway config):

```env
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_API_KEY=your_key
LLM_MODEL=gemini-2.0-flash            # default: gpt-4o-mini
X_BEARER_TOKEN=your_x_api_v2_bearer   # optional; omit for dry-run mode
OPENCLAW_GATEWAY_TOKEN=...            # only if you want gateway-facing
```

## Commands

### `thread_generate`

```python
@skill.command("thread_generate")
async def thread_generate(
    topic: str,
    tone: str = "engaging",
    tweets: int = 5,
) -> list:
    """Generate a viral Twitter thread on a topic."""
```

Returns a list of 1..N tweets. Each tweet fits 280 chars; the thread follows a
virality structure (hook → context → insight → proof → call-to-action).

### `thread_publish`

```python
@skill.command("thread_publish")
async def thread_publish(thread_id: str) -> dict:
    """Publish a previously generated thread to X/Twitter."""
```

Requires `X_BEARER_TOKEN` with `tweet.write` scope. Uses API v2
`POST /2/tweets`; supports **replies chained to the previous tweet ID** so the
thread renders correctly in Timeline (each tweet replies_to the prior).

## Files

- `skill.md` — this file
- `thread_writer.py` — implementation (stdlib + httpx/requests)

## Security notes

- Model output is returned as structured JSON (list of strings) — no markdown
  or HTML to avoid XSS-in-render on client dashboards.
- Dry-run mode never touches the X API.
- The publish command is deliberately *idempotent*: it stores the posted tweet
  IDs under `thread_id` state so re-runs don't double-post.