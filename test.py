#!/usr/bin/env python3
"""
LiteLLM proxy test — hardcoded QAstra config (no .env).

- Discovers all models via GET /v1/models for your virtual key.
- Runs chat completion for chat models, embeddings API for embedding models.
- user / metadata / spend-log tags use qastra@amzur.com for log correlation.

Do not commit real keys; rotate if this file is ever pushed to git.

Usage (from AmzurQAstra-V2, with httpx + openai installed):
    uv run test_litellm_setup.py
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone

import httpx
from openai import OpenAI

# =============================================================================
# Hardcoded configuration (no os.environ / .env)
# =============================================================================
LITELLM_HOST = "http://litellm.amzur.com:4000"  # no trailing slash required
VIRTUAL_KEY = "sk-TnCDWXoSYCIANRXlJoOagw"

# OpenAI SDK expects base URL including /v1
OPENAI_BASE_URL = f"{LITELLM_HOST.rstrip('/')}/v1"

# Log / spend attribution — QAstra
USER_ID = "qastra@amzur.com"
USER_METADATA = {
    "department": "QA",
    "environment": "testing",
    "application": "qastra",
    "source": "test_litellm_setup.py",
    "run_id": str(uuid.uuid4()),
    "started_at_utc": datetime.now(timezone.utc).isoformat(),
}
SPEND_LOGS_METADATA = json.dumps(
    {
        "end_user": "qastra@amzur.com",
        "department": "QA",
        "environment": "qastra-litellm-test",
        "application": "AmzurQAstra-V2",
        "component": "test_litellm_setup",
    }
)

# Optional: curl-like UA if an upstream proxy filters non-browser clients
HTTP_USER_AGENT = "curl/8.5.0"
HTTP_TIMEOUT = 120.0

# Redis (optional local check; LiteLLM server Redis is separate)
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_PASSWORD: str | None = None  # set if you want a local ping


def _is_embedding_model(model_id: str) -> bool:
    m = model_id.lower()
    if "embed" in m:
        return True
    if "text-embedding" in m:
        return True
    if "ada-002" in m and "chat" not in m:
        return True
    return False


def fetch_model_ids() -> list[str]:
    url = f"{LITELLM_HOST.rstrip('/')}/v1/models"
    with httpx.Client(timeout=HTTP_TIMEOUT, headers={"User-Agent": HTTP_USER_AGENT}) as h:
        r = h.get(
            url,
            headers={
                "Authorization": f"Bearer {VIRTUAL_KEY.strip()}",
                "Content-Type": "application/json",
            },
        )
    if r.status_code != 200:
        raise SystemExit(f"GET {url} failed: HTTP {r.status_code}\n{r.text}")
    data = r.json().get("data") or []
    ids: list[str] = []
    for item in data:
        mid = item.get("id")
        if isinstance(mid, str) and mid:
            ids.append(mid)
    return ids


def _extra_headers() -> dict[str, str]:
    return {
        "x-litellm-spend-logs-metadata": SPEND_LOGS_METADATA,
        "X-Internal-App": "AmzurQAstra-V2",
        "X-Internal-Script": "test_litellm_setup.py",
    }


def _extra_body_base() -> dict:
    return {"metadata": dict(USER_METADATA)}


def test_chat(client: OpenAI, model: str) -> bool:
    print(f"\n{'=' * 80}\n[CHAT] {model}\n{'=' * 80}")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello from QAstra!' in one short line."},
            ],
            max_tokens=80,
            temperature=0.3,
            user=USER_ID,
            extra_body=_extra_body_base(),
            extra_headers=_extra_headers(),
        )
        msg = response.choices[0].message.content
        print("OK")
        print(f"  model: {response.model}")
        print(f"  reply: {msg!r}")
        if response.usage:
            print(f"  tokens: {response.usage.total_tokens}")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False


def test_streaming(client: OpenAI, model: str) -> bool:
    print(f"\n{'=' * 80}\n[STREAM] {model}\n{'=' * 80}")
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Count 1 2 3."}],
            max_tokens=40,
            stream=True,
            user=USER_ID,
            extra_body={**_extra_body_base(), "metadata": {**USER_METADATA, "test_type": "streaming"}},
            extra_headers=_extra_headers(),
        )
        print("OK stream: ", end="", flush=True)
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print()
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False


def test_embedding(client: OpenAI, model: str) -> bool:
    print(f"\n{'=' * 80}\n[EMBEDDING] {model}\n{'=' * 80}")
    try:
        response = client.embeddings.create(
            model=model,
            input="QAstra LiteLLM connectivity test.",
            user=USER_ID,
            extra_body={**_extra_body_base(), "metadata": {**USER_METADATA, "test_type": "embedding"}},
            extra_headers=_extra_headers(),
        )
        emb = response.data[0].embedding
        print("OK")
        print(f"  model: {response.model}")
        print(f"  dimensions: {len(emb)}")
        if response.usage:
            print(f"  tokens: {response.usage.total_tokens}")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False


def check_redis_optional() -> bool | None:
    print(f"\n{'=' * 80}\nOptional local Redis ping\n{'=' * 80}")
    try:
        import redis
    except ImportError:
        print("redis not installed — skip (pip install redis)")
        return None
    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        if r.ping():
            print("OK local Redis responded to PING")
            return True
    except Exception as e:
        print(f"No local Redis (expected if only remote LiteLLM): {e}")
    return False


def main() -> int:
    key = VIRTUAL_KEY.strip()
    if not key.startswith("sk-"):
        print("VIRTUAL_KEY must start with sk- (check for leading spaces).", file=sys.stderr)
        return 1

    print("=" * 80)
    print("LiteLLM setup test — QAstra (hardcoded, no .env)")
    print("=" * 80)
    print(f"OPENAI_BASE_URL: {OPENAI_BASE_URL}")
    print(f"Virtual key: {key[:12]}...")
    print(f"user (OpenAI user=): {USER_ID}")
    print(f"metadata: {USER_METADATA}")
    print(f"spend logs (x-litellm-spend-logs-metadata): {SPEND_LOGS_METADATA}")

    check_redis_optional()

    print(f"\n{'=' * 80}\nFetching /v1/models\n{'=' * 80}")
    try:
        model_ids = fetch_model_ids()
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 1

    if not model_ids:
        print("No models returned for this key.", file=sys.stderr)
        return 1

    print(f"Models for this key ({len(model_ids)}):")
    for mid in model_ids:
        kind = "embedding" if _is_embedding_model(mid) else "chat"
        print(f"  - {mid}  [{kind}]")

    http_client = httpx.Client(
        verify=True,
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": HTTP_USER_AGENT},
    )
    client = OpenAI(api_key=key, base_url=OPENAI_BASE_URL, http_client=http_client)

    chat_models = [m for m in model_ids if not _is_embedding_model(m)]
    embed_models = [m for m in model_ids if _is_embedding_model(m)]

    results_chat: dict[str, bool] = {}
    results_embed: dict[str, bool] = {}
    stream_ok: bool | None = None

    print(f"\n{'=' * 80}\nPART 1 — Chat completions (all non-embedding models)\n{'=' * 80}")
    for m in chat_models:
        results_chat[m] = test_chat(client, m)

    if chat_models:
        print(f"\n{'=' * 80}\nPART 2 — Streaming (first chat model only)\n{'=' * 80}")
        stream_ok = test_streaming(client, chat_models[0])

    print(f"\n{'=' * 80}\nPART 3 — Embeddings (all embedding models)\n{'=' * 80}")
    if not embed_models:
        print("(none detected by name heuristic; skipped)")
    for m in embed_models:
        results_embed[m] = test_embedding(client, m)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed = 0
    total = 0
    for m, ok in results_chat.items():
        total += 1
        passed += int(ok)
        print(f"  chat {'OK' if ok else 'FAIL'}  {m}")
    for m, ok in results_embed.items():
        total += 1
        passed += int(ok)
        print(f"  embed {'OK' if ok else 'FAIL'}  {m}")
    if stream_ok is not None:
        total += 1
        passed += int(stream_ok)
        print(f"  stream {'OK' if stream_ok else 'FAIL'}  {chat_models[0]}")

    print(f"\nTOTAL: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())