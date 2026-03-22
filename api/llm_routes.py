"""api/llm_routes.py — Flask Endpoints for LLM Roles 1–4

Architecture role:
    This module adds the LLM-specific REST API endpoints to the Flask app.
    It is a separate Blueprint from simulation_bp (api/routes.py) to keep
    the simulation control API clean and LLM-free.

    All endpoints here call functions in api/llm_service.py. They:
    1. Validate and sanitise the request body.
    2. Call the relevant LLM role function.
    3. Return the structured JSON response or an appropriate error code.

    Error codes:
        400 — Bad request (missing required fields)
        503 — LLM unavailable (Ollama not running or model not found)
        500 — Unexpected LLM or server error

    The frontend's chat.js treats 404 as "not yet implemented" (from an older
    route) and 503 as "Ollama offline" — these semantics must be maintained.

Endpoints:
    GET  /api/llm/status           — Check if Ollama is healthy
    POST /api/llm/parse_scenario   — Role 1: NL → model parameters
    POST /api/llm/generate_profile — Role 2: demographic description → agent attrs
    POST /api/llm/interpret        — Role 3: question + context → narrative
    POST /api/llm/annotate         — Role 4: chart metrics → caption

See also:
    - api/llm_service.py — LLM role implementations
    - api/schemas.py     — Pydantic schemas for response validation
    - static/js/chat.js  — Frontend that calls these endpoints
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from api import llm_service as llm

logger = logging.getLogger(__name__)

llm_bp = Blueprint("llm", __name__)


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------

@llm_bp.route("/api/llm/status")
def llm_status():
    """Check whether Ollama is running and the primary model is available.

    Response (JSON):
        {available, primary_model, primary_ready, secondary_model,
         secondary_ready, models_found}

    Used by the dashboard to show/hide the chat panel or display
    a "LLM offline" notice.
    """
    status = llm.get_llm_status()
    http_code = 200 if status["available"] else 503
    return jsonify(status), http_code


# ---------------------------------------------------------------------------
# Role 1: Scenario Parser
# ---------------------------------------------------------------------------

@llm_bp.route("/api/llm/parse_scenario", methods=["POST"])
def parse_scenario():
    """Role 1: Parse a natural-language scenario description into model parameters.

    Request body (JSON):
        {"description": "A society where delivery services are extremely cheap..."}

    Response (JSON):
        {
          params: {delegation_preference_mean, service_cost_factor, ...},
          rationale: "...",
          scenario_summary: "..."
        }

    The response `params` dict can be directly applied to the dashboard sliders
    via dashboard.js's applyParsedParams() function.

    Error responses:
        400 — missing 'description' field
        503 — Ollama unavailable
        500 — LLM processing error
    """
    body = request.get_json(force=True) or {}
    description = body.get("description", "").strip()
    if not description:
        return jsonify({"error": "Missing required field: 'description'"}), 400

    # Sanitise length: cap at 500 chars to prevent prompt injection / token waste.
    description = description[:500]

    try:
        result = llm.parse_scenario(description)
    except RuntimeError as e:
        # RuntimeError from llm_service means Ollama is unreachable or returned
        # malformed output — treat as 503 to match the frontend's error handling.
        if "unreachable" in str(e).lower() or "ollama" in str(e).lower():
            return jsonify({"error": str(e)}), 503
        return jsonify({"error": f"LLM error: {e}"}), 500
    except (ValidationError, ValueError) as e:
        return jsonify({"error": f"Schema validation error: {e}"}), 500

    # Return only the extractable params (non-null fields) and the rationale.
    params = {k: v for k, v in result.items()
              if k not in {"scenario_summary", "reasoning"} and v is not None}
    return jsonify({
        "params": params,
        "rationale": result.get("reasoning", ""),
        "scenario_summary": result.get("scenario_summary", ""),
    })


# ---------------------------------------------------------------------------
# Role 2: Agent Profile Generator
# ---------------------------------------------------------------------------

@llm_bp.route("/api/llm/generate_profile", methods=["POST"])
def generate_profile():
    """Role 2: Generate numerical agent attributes from a demographic description.

    Request body (JSON):
        {"description": "A busy professional who values convenience over time",
         "count": 1}

    Response (JSON):
        {
          profiles: [{delegation_preference, skill_domestic, ..., profile_description}],
          audit_log: [{prompt, description, output}, ...]
        }

    The `audit_log` is included in the response to demonstrate the white-box
    principle: users can see exactly what prompt generated each profile.
    This is a key feature for demonstrating interpretability.

    Error responses:
        400 — missing 'description' field
        503 — Ollama unavailable
        500 — LLM processing error
    """
    body = request.get_json(force=True) or {}
    description = body.get("description", "").strip()
    count = min(int(body.get("count", 1)), 10)  # Max 10 profiles per call

    if not description:
        return jsonify({"error": "Missing required field: 'description'"}), 400

    description = description[:400]
    profiles = []
    audit_log = []

    for i in range(count):
        # Vary the prompt slightly for diversity across multiple profiles.
        varied = description
        if count > 1:
            varied = f"{description} (Profile variant {i + 1} of {count}: please vary attributes slightly for diversity)"

        try:
            profile = llm.generate_agent_profile(varied)
        except RuntimeError as e:
            if "unreachable" in str(e).lower():
                return jsonify({"error": str(e)}), 503
            return jsonify({"error": f"LLM error: {e}"}), 500
        except (ValidationError, ValueError) as e:
            return jsonify({"error": f"Schema validation error: {e}"}), 500

        profiles.append(profile)
        audit_log.append({
            "prompt_description": varied,
            "output": profile,
        })

    return jsonify({
        "profiles": profiles,
        "count": len(profiles),
        "audit_log": audit_log,
    })


# ---------------------------------------------------------------------------
# Role 3: Result Interpreter
# ---------------------------------------------------------------------------

@llm_bp.route("/api/llm/interpret", methods=["POST"])
def interpret_results():
    """Role 3: Generate a narrative interpretation of simulation results.

    Request body (JSON):
        {
          "question": "Why is stress not rising in the Type B run?",
          "context": {
              "current_step": 30,
              "preset": "type_b",
              "latest_metrics": {"avg_stress": 0.05, ...}
          },
          "history": [{"role": "user", "content": "..."}, ...]
        }

    Response (JSON):
        {
          interpretation: "...",
          detailed_explanation: "...",
          hypothesis_connection: "H3",
          caveats: ["H3 stress divergence requires 100+ steps..."]
        }

    The `caveats` field surfaces model limitations to users, implementing
    the honest interpretation principle (CLAUDE.md §8.0).

    Error responses:
        400 — missing 'question' field
        503 — Ollama unavailable
        500 — LLM processing error
    """
    body = request.get_json(force=True) or {}
    question = body.get("question", "").strip()
    context = body.get("context", {})
    history = body.get("history", [])

    if not question:
        return jsonify({"error": "Missing required field: 'question'"}), 400

    question = question[:400]

    try:
        result = llm.interpret_results(question, context, history)
    except RuntimeError as e:
        if "unreachable" in str(e).lower():
            return jsonify({"error": str(e)}), 503
        return jsonify({"error": f"LLM error: {e}"}), 500
    except (ValidationError, ValueError) as e:
        return jsonify({"error": f"Schema validation error: {e}"}), 500

    # Reshape to match what chat.js expects.
    # The confidence_note is surfaced as a caveat item if non-empty.
    caveats = []
    if result.get("confidence_note"):
        caveats.append(result["confidence_note"])

    return jsonify({
        "interpretation": result["answer"],
        "detailed_explanation": result.get("detailed_explanation", ""),
        "hypothesis_connection": result.get("hypothesis_connection", ""),
        "caveats": caveats,
    })


# ---------------------------------------------------------------------------
# Role 4: Visualization Annotator
# ---------------------------------------------------------------------------

@llm_bp.route("/api/llm/annotate", methods=["POST"])
def annotate_chart():
    """Role 4: Generate a caption and insight for a dashboard chart.

    Request body (JSON):
        {
          "chart_name": "total_labor_hours",
          "metrics": {
              "min": 380.0, "max": 425.0, "final": 412.3,
              "trend": "increasing", "steps_run": 50
          },
          "preset": "type_b"
        }

    Response (JSON):
        {
          chart_title: "Total Labour Hours Over 50 Steps",
          caption: "...",
          key_insight: "Labour hours rose by 8.5% over the simulation period.",
          hypothesis_tag: "H1",
          chart_name: "total_labor_hours"
        }

    The response is inserted into the #ann-<chart_name> DOM element by
    dashboard.js after a run completes.

    Error responses:
        400 — missing 'chart_name'
        503 — Ollama unavailable
        500 — LLM processing error
    """
    body = request.get_json(force=True) or {}
    chart_name = body.get("chart_name", "").strip()
    metrics = body.get("metrics", {})
    preset = body.get("preset")

    if not chart_name:
        return jsonify({"error": "Missing required field: 'chart_name'"}), 400

    try:
        result = llm.annotate_visualization(chart_name, metrics, preset)
    except RuntimeError as e:
        if "unreachable" in str(e).lower():
            return jsonify({"error": str(e)}), 503
        return jsonify({"error": f"LLM error: {e}"}), 500
    except (ValidationError, ValueError) as e:
        return jsonify({"error": f"Schema validation error: {e}"}), 500

    result["chart_name"] = chart_name
    return jsonify(result)


# ---------------------------------------------------------------------------
# Batch annotate (convenience endpoint for post-run annotation of all charts)
# ---------------------------------------------------------------------------

@llm_bp.route("/api/llm/annotate_all", methods=["POST"])
def annotate_all_charts():
    """Annotate all dashboard charts after a simulation run completes.

    Request body (JSON):
        {
          "model_data": [{step, avg_stress, total_labor_hours, ...}],
          "preset": "type_a"
        }

    Response (JSON):
        {annotations: {chart_name: {chart_title, caption, key_insight, ...}, ...}}

    This is called by dashboard.js after a full run to populate all chart
    captions in one request, avoiding N separate /annotate calls.

    Only called if LLM is available — dashboard degrades gracefully if offline.
    """
    body = request.get_json(force=True) or {}
    model_data = body.get("model_data", [])
    preset = body.get("preset")

    if not model_data:
        return jsonify({"error": "Missing 'model_data'"}), 400

    # Extract summary statistics for each chart from the time-series data.
    # We compute min/max/final/trend to give the LLM meaningful context.
    def _stats(key: str) -> dict:
        vals = [d[key] for d in model_data if key in d]
        if not vals:
            return {}
        steps = len(vals)
        trend = "increasing" if vals[-1] > vals[0] + 0.01 else (
                "decreasing" if vals[-1] < vals[0] - 0.01 else "stable")
        return {"min": round(min(vals), 3), "max": round(max(vals), 3),
                "final": round(vals[-1], 3), "trend": trend, "steps_run": steps}

    charts_to_annotate = {
        "total_labor_hours": _stats("total_labor_hours"),
        "avg_stress": _stats("avg_stress"),
        "social_efficiency": _stats("social_efficiency"),
        "gini_income": _stats("gini_income"),
        "avg_delegation_rate": _stats("avg_delegation_rate"),
    }

    annotations = {}
    for chart_name, metrics in charts_to_annotate.items():
        if not metrics:
            continue
        try:
            ann = llm.annotate_visualization(chart_name, metrics, preset)
            annotations[chart_name] = ann
        except (RuntimeError, ValidationError, ValueError) as e:
            # Log but don't abort the whole batch if one chart fails.
            logger.warning("Failed to annotate chart %s: %s", chart_name, e)
            annotations[chart_name] = {
                "chart_title": chart_name.replace("_", " ").title(),
                "caption": "",
                "key_insight": "",
                "hypothesis_tag": None,
                "error": str(e),
            }

    return jsonify({"annotations": annotations})
