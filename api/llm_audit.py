"""api/llm_audit.py — Shared Audit Recorder for LLM Experiment Probes

Architecture role:
    This module provides a small, file-backed recorder for LLM interactions.
    It is used by the phase-4 service layer and the phase-5 forum module when
    a caller wants explicit experimental visibility into prompts, raw outputs,
    schema validation, and downstream effects.

Design intent:
    The recorder is opt-in. Production routes can continue calling the LLM
    service without writing per-call JSON artifacts, while the experiment
    harness can attach a recorder and capture the full prompt/response chain
    for manual review under data/results/llm_logs/.

See also:
    - api/llm_service.py      — Roles 1–4
    - model/forums.py         — Role 5
    - analysis/llm_role_probe.py — CLI experiment harness
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _timestamp_utc() -> str:
    """Return an ISO-8601 UTC timestamp for audit entries."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def make_json_safe(value: Any) -> Any:
    """Convert arbitrary values into JSON-serialisable structures."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): make_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(v) for v in value]
    if is_dataclass(value):
        return make_json_safe(asdict(value))
    if hasattr(value, "model_dump"):
        return make_json_safe(value.model_dump())
    if hasattr(value, "errors"):
        return make_json_safe(value.errors())
    return str(value)


class LlmAuditRecorder:
    """Collect and persist role-level LLM audit artifacts for one probe run."""

    def __init__(self, run_id: str, output_dir: str | Path) -> None:
        self.run_id = run_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._calls: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def record_call(
        self,
        *,
        role: str,
        call_kind: str,
        model: str,
        think: bool,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        raw_response: str | None = None,
        parsed_output: Any = None,
        schema_validation: dict[str, Any] | None = None,
        elapsed_seconds: float | None = None,
        error: Exception | dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append one LLM call entry to the in-memory audit log."""
        entry = {
            "run_id": self.run_id,
            "role": role,
            "call_kind": call_kind,
            "timestamp": _timestamp_utc(),
            "model": model,
            "think": think,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "messages": make_json_safe(messages) if messages is not None else None,
            "raw_response": raw_response,
            "parsed_output": make_json_safe(parsed_output) if parsed_output is not None else None,
            "schema_validation": make_json_safe(schema_validation) if schema_validation else None,
            "elapsed_seconds": round(elapsed_seconds, 6) if elapsed_seconds is not None else None,
            "error": self._format_error(error),
            "extra": make_json_safe(extra) if extra else None,
        }
        self._calls[role].append(entry)
        return entry

    def get_calls(self, role: str) -> list[dict[str, Any]]:
        """Return all recorded calls for one role."""
        return [dict(call) for call in self._calls.get(role, [])]

    def write_json(self, filename: str, payload: dict[str, Any]) -> Path:
        """Write one JSON artifact into the recorder output directory."""
        path = self.output_dir / filename
        path.write_text(
            json.dumps(make_json_safe(payload), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path

    def write_role_artifact(
        self,
        *,
        role: str,
        filename: str,
        payload: dict[str, Any],
    ) -> Path:
        """Write one role artifact, injecting the recorded LLM calls."""
        calls = self.get_calls(role)
        final_payload = {
            "run_id": self.run_id,
            **make_json_safe(payload),
        }
        if len(calls) == 1:
            final_payload["call"] = calls[0]
        else:
            final_payload["calls"] = calls
        return self.write_json(filename, final_payload)

    @staticmethod
    def _format_error(error: Exception | dict[str, Any] | None) -> dict[str, Any] | None:
        """Normalise errors to a small JSON shape."""
        if error is None:
            return None
        if isinstance(error, dict):
            return make_json_safe(error)
        return {
            "type": type(error).__name__,
            "message": str(error),
        }
