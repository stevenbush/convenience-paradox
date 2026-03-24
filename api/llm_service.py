"""api/llm_service.py — Local LLM Service Layer (Ollama Integration)

Architecture role:
    This module implements all LLM roles that operate at the periphery of
    the simulation. The ABM core (model/model.py) is never touched here;
    the LLM exclusively enhances the input/output interface layer.

    White-box principle (from CLAUDE.md §4.3):
        All simulation logic is in explicit Python rules (model/agents.py).
        LLM outputs always pass through Pydantic validation before influencing
        any model state. Every LLM call is logged (prompt + raw output) for
        full auditability. Users can always see what the LLM received and returned.

    The five roles and their positions in the architecture:
        Role 1 — Scenario Parser       (input layer) — NL → model parameters
        Role 2 — Agent Profile Generator (input layer) — NL description → agent attrs
        Role 3 — Result Interpreter     (output layer) — data + question → narrative
        Role 4 — Visualization Annotator (output layer) — metrics → chart caption
        Role 5 — Agent Forums           (experimental in-loop) — see model/forums.py

    LLM configuration:
        Primary model:   qwen3.5:4b   (~3.4 GB Q4, ~60-80 tok/s on M4 Pro)
        Secondary model: qwen3:1.7b   (~1.2 GB Q4, ~120 tok/s, weaker structure)
        Runtime:         Ollama at localhost:11434
        think=False:     Disables Qwen 3.5's extended thinking mode for
                         structured output roles, avoiding token budget issues.
                         (See Phase 1 smoke test findings in docs/execution_log.md)

See also:
    - api/schemas.py  — Pydantic output schemas for each role
    - api/llm_routes.py — Flask endpoints that call these functions
    - CLAUDE.md §4.3  — LLM integration strategy and white-box principle
"""

from __future__ import annotations

import json
import logging
import os
import textwrap
import time
from typing import TYPE_CHECKING, Any, Optional

import ollama
from pydantic import ValidationError

from api.llm_audit import make_json_safe
from api.schemas import (
    AgentProfileOutput,
    ParsedScenarioParams,
    ResultInterpretation,
    VisualizationAnnotation,
)

if TYPE_CHECKING:
    from api.llm_audit import LlmAuditRecorder

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Primary model: best structured JSON output in the 1B–4B range (see master plan §2).
# Override at launch: LLM_PRIMARY_MODEL=your-model:tag python run.py
PRIMARY_MODEL = os.environ.get("LLM_PRIMARY_MODEL", "qwen3.5:4b")

# Secondary / lightweight model: faster, used when profile generation is batched.
# Override at launch: LLM_SECONDARY_MODEL=your-model:tag python run.py
SECONDARY_MODEL = os.environ.get("LLM_SECONDARY_MODEL", "qwen3:1.7b")

# Ollama host. Override: OLLAMA_HOST=http://other-host:11434 python run.py
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# Maximum tokens to generate. 600 covers all roles; thinking traces use tokens
# before the answer, so a higher limit prevents truncated JSON.
# (See Phase 1 finding: 'think=False' eliminates this issue for structured roles.)
MAX_TOKENS = 600


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _chat(
    prompt: str,
    system: str,
    schema: type,
    model: str = PRIMARY_MODEL,
    think: bool = False,
    recorder: Optional["LlmAuditRecorder"] = None,
    role: str = "role_unknown",
    call_kind: str = "structured_chat",
) -> dict[str, Any]:
    """Core Ollama chat call with Pydantic-enforced structured output.

    Uses Ollama's constrained decoding (`format`) to guarantee the response
    matches the given Pydantic schema's JSON schema. This is the strongest
    available guarantee that LLM output is parseable before use.

    Args:
        prompt: The user-facing prompt to send.
        system: The system prompt establishing role and constraints.
        schema: Pydantic model class whose json_schema() is passed as `format`.
        model: Ollama model identifier.
        think: Whether to enable Qwen's extended thinking mode. Disabled for
               structured output roles to avoid token budget exhaustion.

    Returns:
        Parsed dict from the LLM response content, validated against `schema`.

    Raises:
        RuntimeError: If Ollama is unreachable or returns empty content.
        ValidationError: If output does not conform to the schema (should be
                         rare with constrained decoding, but retained for safety).

    Note:
        All prompts and raw outputs are logged at DEBUG level for auditability.
        Failed calls are logged at ERROR level with the full exception.
    """
    logger.debug("LLM call | model=%s | think=%s | prompt_chars=%d", model, think, len(prompt))
    t0 = time.perf_counter()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    content = ""
    parsed: dict[str, Any] | None = None
    schema_validation = {
        "schema": schema.__name__,
        "valid": None,
        "error": None,
    }

    try:
        response = ollama.chat(
            model=model,
            messages=messages,
            format=schema.model_json_schema(),
            options={
                "num_predict": MAX_TOKENS,
                "temperature": 0.3,  # Low temperature for structured tasks
                "top_p": 0.9,
            },
            think=think,
        )
    except Exception as e:
        if recorder:
            recorder.record_call(
                role=role,
                call_kind=call_kind,
                model=model,
                think=think,
                system_prompt=system,
                user_prompt=prompt,
                raw_response=content or None,
                parsed_output=parsed,
                schema_validation=schema_validation,
                elapsed_seconds=time.perf_counter() - t0,
                error=e,
            )
        logger.error("Ollama call failed: %s", e)
        raise RuntimeError(f"Ollama is unreachable or errored: {e}") from e

    elapsed = time.perf_counter() - t0
    content = response.message.content

    if not content or not content.strip():
        if recorder:
            recorder.record_call(
                role=role,
                call_kind=call_kind,
                model=model,
                think=think,
                system_prompt=system,
                user_prompt=prompt,
                raw_response=content,
                parsed_output=None,
                schema_validation=schema_validation,
                elapsed_seconds=elapsed,
                error=RuntimeError("Ollama returned empty content."),
            )
        raise RuntimeError(
            f"Ollama returned empty content. Model: {model}. "
            "Try increasing num_predict or checking model availability."
        )

    logger.debug("LLM response | elapsed=%.2fs | chars=%d | content=%s",
                 elapsed, len(content), content[:200])

    # Parse JSON and validate against the schema.
    # ValidationError is intentionally not caught here — callers handle it.
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        if recorder:
            recorder.record_call(
                role=role,
                call_kind=call_kind,
                model=model,
                think=think,
                system_prompt=system,
                user_prompt=prompt,
                raw_response=content,
                parsed_output=None,
                schema_validation=schema_validation,
                elapsed_seconds=elapsed,
                error=e,
            )
        logger.error("LLM output is not valid JSON: %s | content=%s", e, content[:400])
        raise RuntimeError(f"LLM returned invalid JSON: {e}") from e

    try:
        schema(**parsed)
        schema_validation["valid"] = True
    except ValidationError as e:
        schema_validation["valid"] = False
        schema_validation["error"] = str(e)

    if recorder:
        recorder.record_call(
            role=role,
            call_kind=call_kind,
            model=model,
            think=think,
            system_prompt=system,
            user_prompt=prompt,
            raw_response=content,
            parsed_output=make_json_safe(parsed),
            schema_validation=schema_validation,
            elapsed_seconds=elapsed,
        )

    return parsed


def _check_ollama_health() -> bool:
    """Check whether the Ollama server is reachable and has the primary model.

    Returns:
        True if healthy; False otherwise.
    """
    try:
        models = ollama.list()
        names = [m.model for m in models.models]
        return any(PRIMARY_MODEL.split(":")[0] in n for n in names)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Role 1: Scenario Parser — NL description → model parameters
# ---------------------------------------------------------------------------

ROLE1_SYSTEM = textwrap.dedent("""\
    You are a parameter extraction assistant for an agent-based social simulation.
    The simulation models "Service Convenience vs. Autonomy" dynamics.
    Your task is to read a user's natural-language description of a social scenario
    and extract the most appropriate numerical model parameters.

    Parameter meanings:
    - delegation_preference_mean: How much agents tend to delegate tasks to services.
      0.0 = everyone does everything themselves; 1.0 = everyone always delegates.
    - service_cost_factor: How expensive services are relative to doing tasks yourself.
      0.05 = nearly free services; 1.0 = very costly services.
    - social_conformity_pressure: How much peer behaviour influences choices.
      0.0 = fully independent; 1.0 = strong herd behaviour.
    - tasks_per_step_mean: Average number of tasks each person faces per day. Range 1–6.
    - num_agents: Population size. Default 100 if not specified.

    Rules:
    - Output ONLY valid JSON matching the specified schema. No prose outside JSON.
    - If the user does not specify a value, set that field to null.
    - The scenario_summary must be abstract and not name any specific country or culture.
    - reasoning should explain the parameter choices in 1–2 sentences.
""")


def parse_scenario(
    description: str,
    recorder: Optional["LlmAuditRecorder"] = None,
) -> dict[str, Any]:
    """Role 1: Convert a natural-language scenario description into model parameters.

    The LLM extracts semantically clear parameters from the description.
    Fields not mentioned by the user return null (None) and are filled with
    preset defaults by the calling Flask endpoint.

    Args:
        description: Free-text scenario description from the user.

    Returns:
        Dict matching ParsedScenarioParams schema:
        {delegation_preference_mean, service_cost_factor, social_conformity_pressure,
         tasks_per_step_mean, num_agents, scenario_summary, reasoning}

    Example:
        Input: "A society where everyone uses delivery apps and nobody cooks"
        Output: {"delegation_preference_mean": 0.85, "service_cost_factor": 0.15,
                 "social_conformity_pressure": 0.65, ...}
    """
    prompt = f"User scenario description:\n\n{description}"

    raw = _chat(
        prompt,
        ROLE1_SYSTEM,
        ParsedScenarioParams,
        recorder=recorder,
        role="role_1",
        call_kind="scenario_parser",
    )
    parsed = ParsedScenarioParams(**raw)

    logger.info(
        "Role 1 Scenario Parser | summary=%s | del=%.2f | cost=%.2f | conf=%.2f",
        parsed.scenario_summary,
        parsed.delegation_preference_mean or -1,
        parsed.service_cost_factor or -1,
        parsed.social_conformity_pressure or -1,
    )
    return parsed.model_dump()


# ---------------------------------------------------------------------------
# Role 2: Agent Profile Generator — demographic description → agent attributes
# ---------------------------------------------------------------------------

ROLE2_SYSTEM = textwrap.dedent("""\
    You are an agent profile generator for an agent-based social simulation.
    The simulation models daily task management and service delegation behaviour.
    Given a demographic or persona description, output numerical attributes for
    one agent type.

    Attribute meanings:
    - delegation_preference: Probability of delegating tasks [0.02–0.98].
      High = tends to outsource; Low = prefers self-reliance.
    - skill_domestic: Skill in cooking, cleaning, home management [0.3–0.9].
    - skill_administrative: Skill in paperwork, scheduling, official tasks [0.3–0.9].
    - skill_errand: Skill in shopping, errands, deliveries [0.3–0.9].
    - skill_maintenance: Skill in repairs, DIY, technical tasks [0.3–0.9].
    - profile_description: One sentence characterising this agent type.

    Rules:
    - Output ONLY valid JSON matching the specified schema.
    - All numeric values must be within the stated ranges.
    - The profile_description must not reference specific countries or cultures.
    - Vary the attributes meaningfully based on the description.
""")


def generate_agent_profile(
    demographic_description: str,
    recorder: Optional["LlmAuditRecorder"] = None,
) -> dict[str, Any]:
    """Role 2: Generate numerical agent attributes from a demographic description.

    All outputs are logged alongside the input prompt for auditability.
    The profile is applied to agents via Resident.__init__; every parameter
    is explicit and inspectable (white-box principle maintained).

    Args:
        demographic_description: Text describing the agent archetype
            (e.g., "A busy professional with high income but limited time").

    Returns:
        Dict matching AgentProfileOutput schema:
        {delegation_preference, skill_domestic, skill_administrative,
         skill_errand, skill_maintenance, profile_description}

    Example:
        Input: "An elderly retiree who values self-sufficiency"
        Output: {"delegation_preference": 0.18, "skill_domestic": 0.80,
                 "skill_administrative": 0.60, ..., "profile_description": "..."}
    """
    prompt = f"Agent demographic description:\n\n{demographic_description}"

    # Use the lighter secondary model for batch profile generation.
    # Quality is sufficient for numerical attribute extraction.
    raw = _chat(
        prompt,
        ROLE2_SYSTEM,
        AgentProfileOutput,
        model=SECONDARY_MODEL,
        recorder=recorder,
        role="role_2",
        call_kind="profile_generator",
    )
    profile = AgentProfileOutput(**raw)

    logger.info(
        "Role 2 Profile Generator | del_pref=%.2f | profile=%s",
        profile.delegation_preference,
        profile.profile_description[:60],
    )
    return profile.model_dump()


# ---------------------------------------------------------------------------
# Role 3: Result Interpreter — user question + data context → narrative
# ---------------------------------------------------------------------------

ROLE3_SYSTEM = textwrap.dedent("""\
    You are an analytical assistant for an agent-based social simulation called
    "The Convenience Paradox." Your role is to help users understand their
    simulation results by providing clear, grounded explanations.

    The simulation models how residents choose between self-service and delegation
    of daily tasks (cooking, cleaning, errands, maintenance). It tracks:
    - avg_stress: Mean stress level across all agents [0–1]
    - avg_delegation_rate: Fraction of tasks delegated to services [0–1]
    - total_labor_hours: Total hours spent on tasks system-wide per day
    - social_efficiency: Tasks completed per collective labour-hour
    - gini_income: Inequality of income among agents [0–1, higher = more unequal]

    The four research hypotheses being explored:
    - H1: Higher delegation leads to higher total systemic labour hours (involution).
    - H2: A critical delegation threshold exists beyond which the system spirals.
    - H3: Higher autonomy achieves lower stress and higher aggregate well-being.
    - H4: Mixed-delegation societies are unstable and drift toward extremes.

    Rules:
    - Base your answer on the simulation context data provided.
    - Keep answers grounded in the model's explicit logic — not speculation.
    - Note if the run is too short to confirm a hypothesis (H3 requires ~100+ steps).
    - Do NOT name specific countries or cultures; use abstract terms only.
    - The answer field must be concise (1–3 sentences).
    - Output ONLY valid JSON matching the specified schema.
""")


def _coerce_result_interpretation(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalise common near-miss Role 3 outputs into the expected schema.

    Qwen occasionally returns semantically correct keys such as `analysis`
    instead of the required `answer`. The probe harness should treat these
    as recoverable formatting drift, not as a hard failure, as long as the
    meaning can be mapped transparently into the explicit schema.
    """
    normalized = dict(raw)

    alias_map = {
        "analysis": "answer",
        "summary": "answer",
        "response": "answer",
        "explanation": "detailed_explanation",
        "details": "detailed_explanation",
        "hypothesis": "hypothesis_connection",
        "hypothesis_tag": "hypothesis_connection",
        "caveat": "confidence_note",
        "caveats": "confidence_note",
        "limitation": "confidence_note",
        "limitations": "confidence_note",
    }

    for source_key, target_key in alias_map.items():
        if target_key not in normalized and source_key in normalized:
            value = normalized[source_key]
            if isinstance(value, list):
                value = "; ".join(str(item) for item in value)
            normalized[target_key] = value

    return normalized


def interpret_results(
    question: str,
    context: dict[str, Any],
    history: Optional[list[dict]] = None,
    recorder: Optional["LlmAuditRecorder"] = None,
) -> dict[str, Any]:
    """Role 3: Generate a narrative interpretation of simulation results.

    The LLM receives the user's question plus a compact summary of the current
    simulation state. The answer is grounded in model data, not hallucinated.

    Args:
        question: User's question about the simulation (e.g., "Why is stress rising?").
        context: Dict with current simulation metrics:
            {current_step, preset, params_summary, latest_metrics}
        history: Optional list of previous chat turns for multi-turn context.

    Returns:
        Dict matching ResultInterpretation schema:
        {answer, detailed_explanation, hypothesis_connection, confidence_note}

    Note:
        The `confidence_note` field is used to surface model limitations
        (e.g., "H3 stress divergence typically requires 100+ steps; current
        run has only 20 steps.").
    """
    # Build a concise context block for the prompt.
    # Verbose context wastes tokens; we give the LLM only what it needs.
    context_block = json.dumps(context, indent=2, default=str)

    # Include last N turns of conversation for multi-turn coherence.
    history_block = ""
    if history:
        turns = []
        for turn in history[-4:]:  # Last 4 turns max (token budget)
            role = turn.get("role", "user")
            content = turn.get("content", "")
            turns.append(f"{role.upper()}: {content}")
        if turns:
            history_block = "\nConversation history:\n" + "\n".join(turns) + "\n"

    prompt = (
        f"Simulation context:\n{context_block}\n"
        f"{history_block}"
        f"\nUser question: {question}"
    )

    raw = _chat(
        prompt,
        ROLE3_SYSTEM,
        ResultInterpretation,
        recorder=recorder,
        role="role_3",
        call_kind="result_interpreter",
    )
    result = ResultInterpretation(**_coerce_result_interpretation(raw))

    logger.info("Role 3 Result Interpreter | question=%s... | answer_chars=%d",
                question[:40], len(result.answer))
    return result.model_dump()


# ---------------------------------------------------------------------------
# Role 4: Visualization Annotator — chart metrics → caption + insight
# ---------------------------------------------------------------------------

ROLE4_SYSTEM = textwrap.dedent("""\
    You are a visualization annotator for an agent-based social simulation dashboard.
    Given summary statistics from a simulation chart, generate a clear, informative
    annotation that helps a non-expert understand what the chart shows.

    Rules:
    - chart_title: Short, descriptive (max 60 characters).
    - caption: 2–3 sentences explaining what the data shows and why it matters.
    - key_insight: The single most important observation (1 sentence, ≤80 chars).
    - hypothesis_tag: Which hypothesis (H1/H2/H3/H4) this chart most directly
      relates to, or null if exploratory.
    - Do not name specific countries or cultures.
    - Output ONLY valid JSON matching the specified schema.
""")


def annotate_visualization(
    chart_name: str,
    chart_metrics: dict[str, Any],
    preset: Optional[str] = None,
    recorder: Optional["LlmAuditRecorder"] = None,
) -> dict[str, Any]:
    """Role 4: Generate a caption and insight for a dashboard chart.

    Called after a run completes to provide contextual annotations for each
    Plotly chart on the dashboard. The annotations are stored in the DOM
    via the `#ann-<chart-name>` elements in index.html.

    Args:
        chart_name: Human-readable chart identifier (e.g., "total_labor_hours").
        chart_metrics: Dict of relevant statistics (min, max, trend direction, etc.).
        preset: Currently active preset ('type_a', 'type_b', 'custom', or None).

    Returns:
        Dict matching VisualizationAnnotation schema:
        {chart_title, caption, key_insight, hypothesis_tag}
    """
    preset_desc = ""
    if preset == "type_a":
        preset_desc = "This is an Autonomy-Oriented society (low delegation, high service cost)."
    elif preset == "type_b":
        preset_desc = "This is a Convenience-Oriented society (high delegation, low service cost)."

    prompt = (
        f"Chart: {chart_name}\n"
        f"{preset_desc}\n"
        f"Chart statistics:\n{json.dumps(chart_metrics, indent=2, default=str)}"
    )

    raw = _chat(
        prompt,
        ROLE4_SYSTEM,
        VisualizationAnnotation,
        recorder=recorder,
        role="role_4",
        call_kind="visualization_annotator",
    )
    annotation = VisualizationAnnotation(**raw)

    logger.info("Role 4 Viz Annotator | chart=%s | insight=%s",
                chart_name, annotation.key_insight[:60])
    return annotation.model_dump()


# ---------------------------------------------------------------------------
# Health check utility
# ---------------------------------------------------------------------------

def get_llm_status() -> dict[str, Any]:
    """Return the health status of the Ollama LLM service.

    Used by GET /api/llm/status to give the frontend visibility into
    whether the LLM is available. The chat panel shows a warning if
    the LLM is offline, and gracefully degrades without it.

    Returns:
        Dict: {available, primary_model, secondary_model, models_found}
    """
    try:
        models_response = ollama.list()
        available_names = [m.model for m in models_response.models]
        primary_ok = any(PRIMARY_MODEL.split(":")[0] in n for n in available_names)
        secondary_ok = any(SECONDARY_MODEL.split(":")[0] in n for n in available_names)
        return {
            "available": primary_ok,
            "primary_model": PRIMARY_MODEL,
            "primary_ready": primary_ok,
            "secondary_model": SECONDARY_MODEL,
            "secondary_ready": secondary_ok,
            "models_found": available_names,
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "primary_model": PRIMARY_MODEL,
            "secondary_model": SECONDARY_MODEL,
            "models_found": [],
        }
