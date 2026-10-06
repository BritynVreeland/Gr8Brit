"""The single doorway to Claude for pipeline stages.

Every call: versioned prompt, per-stage model/effort from config/models.yaml, JSON-schema structured
output validated by Pydantic, refusal handling with server-side fallback, and a row in `llm_calls`
(tokens, cost, prompt version) for audits and cost tracking.
"""

import json
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import anthropic
import psycopg
import yaml
from pydantic import BaseModel, ValidationError

from bbos.settings import get_settings

# USD per million tokens: (input, output, cache_read). Cache writes bill at 1.25x input.
PRICING = {
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-haiku-4-5": (1.00, 5.00, 0.10),
}
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class StageConfig:
    model: str
    effort: str
    batch: bool = False


@lru_cache
def _models_config() -> dict:
    return yaml.safe_load((get_settings().config_dir / "models.yaml").read_text())


def stage_config(stage: str) -> StageConfig:
    cfg = _models_config()
    merged = {**cfg["default"], **(cfg.get("stages", {}).get(stage) or {})}
    return StageConfig(model=merged["model"], effort=merged["effort"], batch=merged.get("batch", False))


def strict_json_schema(model: type[BaseModel]) -> dict:
    """Pydantic schema -> structured-output schema: every object closed and fully required."""
    schema = deepcopy(model.model_json_schema())

    def close(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"].keys())
            for key in ("title", "default"):
                node.pop(key, None)
            for v in node.values():
                close(v)
        elif isinstance(node, list):
            for v in node:
                close(v)

    close(schema)
    return schema


def estimate_cost(model: str, usage: Any) -> float | None:
    if model not in PRICING:
        return None
    p_in, p_out, p_cache = PRICING[model]
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    return (
        usage.input_tokens * p_in + usage.output_tokens * p_out + cache_read * p_cache + cache_write * p_in * 1.25
    ) / 1_000_000


def _log_call(conn: psycopg.Connection | None, **row: Any) -> None:
    if conn is None:
        return
    cols = ", ".join(row)
    conn.execute(f"insert into llm_calls ({cols}) values ({', '.join(['%s'] * len(row))})", list(row.values()))


def call_structured[T: BaseModel](
    *,
    stage: str,
    prompt_key: str,
    prompt_version: str,
    system: str,
    user: str,
    output_model: type[T],
    conn: psycopg.Connection | None = None,
    pipeline_run_id: uuid.UUID | None = None,
    max_tokens: int = 16000,
    client: anthropic.Anthropic | None = None,
) -> T:
    """Run one structured-output call. `system` should hold stable context (cached); `user` the item.

    Untrusted text (posts, comments, emails) must be placed inside `user`, wrapped as data by the caller.
    """
    cfg = stage_config(stage)
    client = client or anthropic.Anthropic()
    started = time.monotonic()
    log = {
        "pipeline_run_id": pipeline_run_id,
        "stage": stage,
        "model": cfg.model,
        "prompt_key": prompt_key,
        "prompt_version": prompt_version,
    }
    try:
        resp = client.beta.messages.create(
            model=cfg.model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_config={
                "effort": cfg.effort,
                "format": {"type": "json_schema", "schema": strict_json_schema(output_model)},
            },
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
    except anthropic.APIError as e:
        _log_call(
            conn, **log, status="failed", error=str(e)[:2000], latency_ms=int((time.monotonic() - started) * 1000)
        )
        raise

    usage = resp.usage
    log.update(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_read_tokens=getattr(usage, "cache_read_input_tokens", None),
        cache_write_tokens=getattr(usage, "cache_creation_input_tokens", None),
        cost_usd=estimate_cost(resp.model, usage),
        stop_reason=resp.stop_reason,
        latency_ms=int((time.monotonic() - started) * 1000),
        model=resp.model,
    )
    if resp.stop_reason == "refusal":
        _log_call(conn, **log, status="refused")
        raise LLMError(f"{stage}: model declined ({getattr(resp, 'stop_details', None)})")
    if resp.stop_reason == "max_tokens":
        _log_call(conn, **log, status="invalid_output", error="hit max_tokens")
        raise LLMError(f"{stage}: output truncated at max_tokens={max_tokens}")

    text = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        parsed = output_model.model_validate(json.loads(text))
    except (ValueError, ValidationError) as e:
        _log_call(conn, **log, status="invalid_output", error=str(e)[:2000])
        raise LLMError(f"{stage}: output failed validation: {e}") from e
    _log_call(conn, **log, status="succeeded")
    return parsed
