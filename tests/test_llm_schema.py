from types import SimpleNamespace

from pydantic import BaseModel

from bbos.llm.client import estimate_cost, stage_config, strict_json_schema


class Inner(BaseModel):
    quote: str
    confidence: float = 0.5


class Outer(BaseModel):
    items: list[Inner]
    note: str | None = None


def test_strict_schema_closes_every_object():
    s = strict_json_schema(Outer)
    assert s["additionalProperties"] is False
    assert set(s["required"]) == {"items", "note"}
    inner = s["$defs"]["Inner"]
    assert inner["additionalProperties"] is False
    assert set(inner["required"]) == {"quote", "confidence"}
    assert "default" not in inner["properties"]["confidence"]


def test_cost_estimate_opus():
    usage = SimpleNamespace(
        input_tokens=1_000_000, output_tokens=100_000, cache_read_input_tokens=0, cache_creation_input_tokens=0
    )
    assert round(estimate_cost("claude-opus-5-5", usage), 2) == 6.00


def test_stage_config_merges_defaults():
    cfg = stage_config("extraction")
    assert cfg.model == "claude-opus-5-5" and cfg.batch is True
