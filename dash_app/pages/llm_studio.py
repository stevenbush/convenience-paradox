"""
Page 2: LLM Studio

Unified interface for all 5 LLM roles: scenario parser, result interpreter,
profile generator, visualization annotator, and agent forums.
Includes per-role model selection and a session audit log viewer.

Callback architecture:
    - Model config panel queries Ollama for available models and populates
      per-role dropdowns. Selections are stored in dash_app.state.
    - Each role tab has its own input/output UI and callback.
    - All LLM calls go through api/llm_service.py (Roles 1-4) or
      model/forums.py (Role 5), with audit entries accumulated in state.
    - The audit log tab reads from state.get_audit_log().

Goals served: A (interactive UI), C (LLM-enhanced interface)
"""

from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import html, dcc, callback, clientside_callback, Input, Output, State, ctx, no_update, ALL

from api.llm_audit import make_json_safe
from api.schemas import SimulationParams, AgentProfileOutput
from dash_app.components.card import card
from dash_app.components.badges import status_badge, llm_status_dot
from dash_app.components.charts import CHART_COLORWAY
import dash_app.state as app_state

logger = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path="/llm-studio",
    name="LLM Studio",
    order=1,
)

# Role definitions for building the model config and tabs
ROLES = [
    ("role_1", "Role 1", "Scenario Parser", "fas fa-wand-magic-sparkles"),
    ("role_2", "Role 2", "Profile Generator", "fas fa-user-gear"),
    ("role_3", "Role 3", "Result Interpreter", "fas fa-comments"),
    ("role_4", "Role 4", "Viz Annotator", "fas fa-pen-fancy"),
    ("role_5", "Role 5", "Agent Forums", "fas fa-people-group"),
]

SCENARIO_PARAM_KEYS = [
    "delegation_preference_mean",
    "service_cost_factor",
    "social_conformity_pressure",
    "tasks_per_step_mean",
    "num_agents",
]

SCENARIO_PARAM_LABELS = {
    "delegation_preference_mean": "Delegation Preference Mean",
    "service_cost_factor": "Service Cost Factor",
    "social_conformity_pressure": "Social Conformity Pressure",
    "tasks_per_step_mean": "Tasks Per Step Mean",
    "num_agents": "Num Agents",
}

SCENARIO_PARAM_DEFAULTS = {
    key: SimulationParams().model_dump()[key]
    for key in SCENARIO_PARAM_KEYS
}

SCENARIO_DESCRIPTION_EXAMPLE = (
    "A mid-sized society of around 120 residents relies on delivery, laundry, and "
    "household services when workdays get crowded. Services are affordable but not "
    "free, so people still handle some tasks themselves. Neighbours notice each "
    "other's convenience choices, creating moderate peer pressure to delegate. Most "
    "residents juggle about 3 to 4 tasks per day."
)

SCENARIO_NEXT_STEP_GUIDANCE = (
    "These values map directly to the Simulation Dashboard controls. Use them to set "
    "delegation, service cost, conformity, workload, and population size, then "
    "initialize a run and compare stress, delegation rate, and total labor hours over "
    "30 to 50 steps."
)

CHAT_CONTEXT_METRICS = [
    ("avg_stress", "Avg Stress"),
    ("avg_delegation_rate", "Delegation Rate"),
    ("total_labor_hours", "Total Labor Hours"),
    ("social_efficiency", "Social Efficiency"),
    ("unmatched_tasks", "Unmatched Tasks"),
    ("avg_income", "Avg Income"),
]

CHAT_CONTEXT_PARAMS = [
    ("delegation_preference_mean", "Delegation Mean"),
    ("service_cost_factor", "Service Cost"),
    ("social_conformity_pressure", "Conformity"),
    ("tasks_per_step_mean", "Tasks / Step"),
    ("num_agents", "Num Agents"),
    ("network_type", "Network"),
]

PROFILE_PARAM_FIELDS = [
    ("delegation_preference", "Delegation Preference"),
    ("skill_domestic", "Domestic Skill"),
    ("skill_administrative", "Administrative Skill"),
    ("skill_errand", "Errand Skill"),
    ("skill_maintenance", "Maintenance Skill"),
]

PROFILE_PARAM_HELP = {
    "delegation_preference": (
        "Higher values mean this agent type is more likely to outsource tasks "
        "instead of handling them alone."
    ),
    "skill_domestic": (
        "Comfort with cooking, cleaning, and day-to-day household management."
    ),
    "skill_administrative": (
        "Capability for paperwork, scheduling, and routine coordination tasks."
    ),
    "skill_errand": (
        "Capability for shopping, delivery pickup, and other outside errands."
    ),
    "skill_maintenance": (
        "Capability for repairs, DIY, and technical upkeep around the home."
    ),
}

PROFILE_DESCRIPTION_EXAMPLE = (
    "A time-constrained professional who is comfortable using paid services. "
    "They can handle scheduling and errands fairly well, but prefer to outsource "
    "household chores and small repairs when work becomes intense."
)

PROFILE_SUGGESTED_PROMPTS = [
    (
        "btn-profile-prompt-busy",
        "Busy Service User",
        (
            "A time-constrained professional who is comfortable using paid services. "
            "They handle scheduling and errands fairly well, but prefer to outsource "
            "household chores and small repairs during intense work periods."
        ),
    ),
    (
        "btn-profile-prompt-self-serve",
        "Self-Reliant Resident",
        (
            "A self-reliant resident who values autonomy and usually handles household "
            "tasks personally. They are comfortable with cooking, cleaning, errands, "
            "and minor repairs, and only outsource when deadlines become extreme."
        ),
    ),
    (
        "btn-profile-prompt-coordinator",
        "Household Coordinator",
        (
            "A household coordinator who keeps track of schedules, errands, and family "
            "logistics. They are strong at administrative work and daily errands, but "
            "delegate cleaning or repair work when the week becomes overloaded."
        ),
    ),
]

PROFILE_NEXT_STEP_GUIDANCE = (
    "Use this as one simulation-ready agent type. Delegation Preference controls "
    "how often the archetype outsources tasks, while the four skill values shape "
    "how capable the agent is at self-serving across task domains. Generate a few "
    "contrasting profiles to create a more heterogeneous population."
)

ANNOTATION_GUIDANCE = (
    "Review the exact dashboard charts being sent to the Visualization Annotator. "
    "Click Annotate All Charts to have the LLM produce one caption and one key "
    "insight per chart, grounded in the current simulation run."
)

ANNOTATION_WORKFLOW_NOTE = (
    "Run a simulation first, then annotate the current chart set. Each card below "
    "shows the chart preview, the compact data summary injected into the prompt, "
    "and the generated interpretation once the role finishes."
)

FORUM_GUIDANCE = (
    "Invite part of the current simulation population into a bounded set of discussion groups. "
    "Each group runs a short 1 to 3 turn dialogue about delegation norms, then the forum "
    "extracts one bounded norm signal that nudges delegation preference without replacing "
    "the rule-based adaptation logic or hiding the transcript."
)

FORUM_WORKFLOW_NOTE = (
    "Choose the invited fraction, optionally override it with an exact agent count, then set "
    "the number of groups and dialogue turns before clicking Run Forum. The scale preview below "
    "shows how many residents and LLM calls the current configuration implies. Forum groups are "
    "processed one step at a time so dialogue stays visible and the interface remains responsive. "
    "Use Stop Forum to halt after the current in-flight turn finishes."
)

ANNOTATION_CHART_SPECS = [
    {
        "chart_key": "total_labor_hours",
        "chart_label": "Total Labor Hours",
        "display_title": "Total Labor Hours (H1)",
        "subtitle": "System-wide labor demand over time",
        "description": "Shows whether delegation raises aggregate labor instead of reducing it.",
    },
    {
        "chart_key": "stress_delegation",
        "chart_label": "Stress & Delegation",
        "display_title": "Stress & Delegation (H2/H3)",
        "subtitle": "Dual-axis view of stress and delegation",
        "description": "Shows whether convenience is reducing strain or amplifying it.",
    },
    {
        "chart_key": "social_efficiency",
        "chart_label": "Social Efficiency",
        "display_title": "Social Efficiency (H2)",
        "subtitle": "Tasks completed per unit of labor",
        "description": "Shows whether the system becomes more efficient as delegation grows.",
    },
    {
        "chart_key": "market_health",
        "chart_label": "Market Health",
        "display_title": "Market Health",
        "subtitle": "Unmatched demand and delegation share",
        "description": "Shows whether the service market can absorb delegated work.",
    },
]

AUDIT_LOG_GUIDANCE = (
    "Review the session-level trail of every LLM interaction triggered from LLM Studio. "
    "Use Inspect on any row to open the original request context and the original response "
    "captured for that call, without leaving the current workspace."
)

AUDIT_LOG_DETAIL_NOTE = (
    "The table gives a compact cross-role summary, while the detail panel below exposes the "
    "full input and output payloads used for manual verification, debugging, and prompt review."
)


def _default_llm_studio_state() -> dict[str, Any]:
    """Return the default in-memory UI state for the LLM Studio page."""
    return {
        "active_tab": "tab-scenario",
        "scenario": _default_scenario_state(),
    }


def _default_scenario_state() -> dict[str, Any]:
    """Return the initial Scenario Parser state."""
    return {
        "description": "",
        "status": "idle",
        "error": None,
        "elapsed": None,
        "model": None,
        "result": None,
        "raw_response": None,
        "request_id": None,
        "history": [],
        "last_parse_clicks": 0,
        "last_submit_count": 0,
        "last_clear_clicks": 0,
    }


def _normalize_llm_studio_state(data: dict[str, Any] | None) -> dict[str, Any]:
    """Merge arbitrary store payloads with the expected LLM Studio schema."""
    state = _default_llm_studio_state()
    if not isinstance(data, dict):
        return state

    active_tab = data.get("active_tab")
    if isinstance(active_tab, str) and active_tab:
        state["active_tab"] = active_tab

    scenario = data.get("scenario")
    if isinstance(scenario, dict):
        state["scenario"]["description"] = str(scenario.get("description") or "")
        state["scenario"]["status"] = str(scenario.get("status") or "idle")
        state["scenario"]["error"] = scenario.get("error")
        state["scenario"]["elapsed"] = scenario.get("elapsed")
        state["scenario"]["model"] = scenario.get("model")
        state["scenario"]["result"] = scenario.get("result")
        state["scenario"]["raw_response"] = scenario.get("raw_response")
        state["scenario"]["request_id"] = scenario.get("request_id")
        state["scenario"]["last_parse_clicks"] = int(scenario.get("last_parse_clicks") or 0)
        state["scenario"]["last_submit_count"] = int(scenario.get("last_submit_count") or 0)
        state["scenario"]["last_clear_clicks"] = int(scenario.get("last_clear_clicks") or 0)
        history = scenario.get("history")
        if isinstance(history, list):
            state["scenario"]["history"] = [item for item in history if isinstance(item, dict)]

    return state


def _scenario_placeholder(text: str):
    """Return a centered placeholder used by the Scenario Parser views."""
    return html.Div(
        text,
        style={
            "color": "var(--cp-text-tertiary)",
            "fontSize": "var(--cp-text-sm)",
            "textAlign": "center",
            "padding": "var(--cp-space-8)",
        },
    )


def _make_request_id() -> str:
    """Generate a stable request identifier for one Scenario Parser turn."""
    return datetime.now().strftime("%Y%m%dT%H%M%S%f")


def _format_scenario_value(value: Any) -> str:
    """Format one parsed parameter value for compact display."""
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def _scenario_param_label(param_key: str) -> str:
    """Return the display label for one Scenario Parser parameter."""
    return SCENARIO_PARAM_LABELS.get(param_key, param_key.replace("_", " ").title())


def _resolve_scenario_result(result: dict[str, Any] | None) -> dict[str, Any]:
    """Fill missing Scenario Parser values with neutral defaults and source metadata."""
    resolved = dict(result or {})
    parameter_sources: dict[str, str] = {}
    defaulted_parameters: list[str] = []

    for param_key in SCENARIO_PARAM_KEYS:
        if resolved.get(param_key) is None:
            resolved[param_key] = SCENARIO_PARAM_DEFAULTS[param_key]
            parameter_sources[param_key] = "default"
            defaulted_parameters.append(param_key)
        else:
            parameter_sources[param_key] = "llm"

    if defaulted_parameters:
        missing_labels = ", ".join(_scenario_param_label(key) for key in defaulted_parameters)
        resolved["coverage_warning"] = (
            "Your description did not provide enough detail to infer every parameter. "
            f"Neutral defaults were used for: {missing_labels}."
        )
    else:
        resolved["coverage_warning"] = ""

    resolved["parameter_sources"] = parameter_sources
    resolved["defaulted_parameters"] = defaulted_parameters
    resolved["example_description"] = SCENARIO_DESCRIPTION_EXAMPLE
    resolved["next_step_guidance"] = SCENARIO_NEXT_STEP_GUIDANCE
    return resolved


def _format_raw_json(raw_response: Any) -> str:
    """Pretty-format the raw LLM output for UI display."""
    if raw_response is None:
        return ""
    if isinstance(raw_response, str):
        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError:
            return raw_response
    else:
        parsed = raw_response
    return json.dumps(parsed, indent=2, ensure_ascii=False)


def _build_scenario_param_chips(result: dict[str, Any] | None):
    """Render compact parameter chips for the assistant reply bubble."""
    result = result or {}
    chips = []
    for param_key in SCENARIO_PARAM_KEYS:
        source = (result.get("parameter_sources") or {}).get(param_key, "llm")
        chips.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(
                                _scenario_param_label(param_key),
                                className="cp-scenario__metric-label",
                            ),
                            html.Span(
                                "Neutral default" if source == "default" else "LLM",
                                className=(
                                    "cp-badge cp-badge--warning"
                                    if source == "default"
                                    else "cp-badge cp-badge--primary"
                                ),
                            ),
                        ],
                        className="cp-scenario__metric-header",
                    ),
                    html.Div(
                        _format_scenario_value(result.get(param_key)),
                        className="cp-scenario__metric-value",
                    ),
                ],
                className="cp-scenario__metric-chip",
            )
        )
    return html.Div(chips, className="cp-scenario__metric-grid")


def _build_scenario_output_param_grid(result: dict[str, Any] | None):
    """Render scenario parameters as a compact inspector grid for responsive layouts."""
    result = result or {}
    cards = []
    for param_key in SCENARIO_PARAM_KEYS:
        source = (result.get("parameter_sources") or {}).get(param_key, "llm")
        cards.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(_scenario_param_label(param_key), className="cp-chat-context__label"),
                            html.Span(
                                "Neutral default" if source == "default" else "LLM-derived",
                                className=(
                                    "cp-badge cp-badge--warning"
                                    if source == "default"
                                    else "cp-badge cp-badge--primary"
                                ),
                            ),
                        ],
                        className="cp-scenario__metric-header",
                    ),
                    html.Div(
                        _format_scenario_value(result.get(param_key)),
                        className="cp-chat-context__value",
                    ),
                ],
                className="cp-chat-context__chip",
            )
        )
    return html.Div(cards, className="cp-chat-context__grid")


def _build_scenario_intro():
    """Render an inline guide showing what Scenario Parser does and how to use it."""
    return html.Div(
        [
            html.Div("How To Use Scenario Parser", className="cp-scenario-guide__label"),
            html.Div(
                "Describe service use, cost, peer pressure, workload, and population. "
                "The parser returns validated parameters, highlights any neutral defaults, "
                "and explains how to use the result in the Simulation Dashboard.",
                className="cp-scenario-guide__text",
            ),
        ],
        className="cp-scenario-guide",
    )


def _build_scenario_raw_output(raw_response: Any, summary_text: str = "View raw LLM JSON"):
    """Render a collapsible raw-response block when available."""
    pretty = _format_raw_json(raw_response)
    if not pretty:
        return None
    return html.Details(
        [
            html.Summary(summary_text, className="cp-scenario__details-summary"),
            dcc.Markdown(
                f"```json\n{pretty}\n```",
                className="cp-scenario__raw-block",
            ),
        ],
        className="cp-scenario__details",
    )


def _stage_scenario_request(
    store_data: dict[str, Any] | None,
    description: str,
    model_name: str,
    request_id: str,
) -> dict[str, Any]:
    """Append the user turn and a pending assistant turn before the LLM returns."""
    state = _normalize_llm_studio_state(store_data)
    scenario_state = state["scenario"]
    scenario_state.update({
        "description": description,
        "status": "pending",
        "error": None,
        "elapsed": None,
        "model": model_name,
        "result": None,
        "raw_response": None,
        "request_id": request_id,
    })
    scenario_state["history"].append({
        "id": f"{request_id}-user",
        "role": "user",
        "content": description,
    })
    scenario_state["history"].append({
        "id": f"{request_id}-assistant",
        "role": "assistant",
        "request_id": request_id,
        "status": "pending",
        "model": model_name,
        "content": "Reading your description and extracting structured simulation parameters.",
    })
    return state


def _complete_scenario_request(
    store_data: dict[str, Any] | None,
    request_id: str,
    model_name: str,
    elapsed: float,
    *,
    result: dict[str, Any] | None = None,
    raw_response: Any = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Replace the pending assistant turn with the final Scenario Parser reply."""
    state = _normalize_llm_studio_state(store_data)
    scenario_state = state["scenario"]
    resolved_result = _resolve_scenario_result(result) if error is None and result is not None else None
    is_success = error is None and resolved_result is not None

    for message in scenario_state["history"]:
        if message.get("role") == "assistant" and message.get("request_id") == request_id:
            message.update({
                "status": "success" if is_success else "error",
                "model": model_name,
                "elapsed": elapsed,
                "content": (
                    (resolved_result or {}).get("scenario_summary", "Parsed scenario ready.")
                    if is_success else error
                ),
                "reasoning": (resolved_result or {}).get("reasoning", "") if is_success else "",
                "result": resolved_result if is_success else None,
                "raw_response": raw_response,
                "error": error,
            })
            break

    if scenario_state.get("request_id") == request_id or scenario_state.get("status") != "pending":
        scenario_state.update({
            "status": "success" if is_success else "error",
            "error": error,
            "elapsed": elapsed,
            "model": model_name,
            "result": resolved_result if is_success else None,
            "raw_response": raw_response,
            "request_id": request_id,
        })

    return state


def _build_scenario_thread(scenario_state: dict[str, Any] | None):
    """Render the chat-style Scenario Parser transcript."""
    scenario_state = scenario_state or {}
    history = scenario_state.get("history") or []
    if not history:
        return _scenario_placeholder(
            "Describe a society and the parser will translate it into explicit simulation parameters."
        )

    bubbles = []
    for message in history:
        if message.get("role") == "user":
            bubbles.append(
                html.Div([
                    html.Div("You", className="cp-chat__sender"),
                    html.Div(message.get("content", "")),
                ], className="cp-chat__message cp-chat__message--user")
            )
            continue

        meta = []
        if message.get("model"):
            meta.append(str(message.get("model")))
        if isinstance(message.get("elapsed"), (int, float)):
            meta.append(f"{message['elapsed']:.1f}s")

        body_children = [
            html.Div("Scenario Parser", className="cp-chat__sender"),
            html.Div(
                message.get("content", ""),
                className="cp-scenario__reply-summary",
            ),
        ]

        if message.get("status") == "pending":
            body_children.extend([
                html.Div(
                    "Thinking through delegation, costs, conformity, workload, and population scale.",
                    className="cp-scenario__reply-reasoning",
                ),
                html.Div(
                    [
                        html.Span(className="cp-scenario__thinking-dot"),
                        html.Span(className="cp-scenario__thinking-dot"),
                        html.Span(className="cp-scenario__thinking-dot"),
                    ],
                    className="cp-scenario__thinking",
                ),
            ])
        elif message.get("status") == "error":
            body_children.append(
                html.Div(
                    message.get("error", "Parser failed."),
                    className="cp-scenario__reply-error",
                )
            )
        else:
            body_children.extend([
                html.Div(
                    message.get("reasoning", ""),
                    className="cp-scenario__reply-reasoning",
                ),
                _build_scenario_param_chips(message.get("result")),
            ])
            raw_block = _build_scenario_raw_output(
                message.get("raw_response"),
                summary_text="View raw LLM output",
            )
            if raw_block is not None:
                body_children.append(raw_block)

        if meta:
            body_children.append(
                html.Div(" · ".join(meta), className="cp-scenario__message-meta")
            )

        bubbles.append(
            html.Div(
                body_children,
                className="cp-chat__message cp-chat__message--ai cp-scenario__assistant-message",
            )
        )

    return html.Div(bubbles, className="cp-chat")


def _build_scenario_output(scenario_state: dict[str, Any] | None):
    """Render the latest structured Scenario Parser inspector."""
    scenario_state = scenario_state or {}
    status = scenario_state.get("status", "idle")
    subtitle_parts = []
    elapsed = scenario_state.get("elapsed")
    if isinstance(elapsed, (int, float)):
        subtitle_parts.append(f"{elapsed:.1f}s")
    model_name = scenario_state.get("model")
    if model_name:
        subtitle_parts.append(str(model_name))
    subtitle = " · ".join(subtitle_parts) if subtitle_parts else None

    if status == "idle":
        return card(
            title="Latest Parsed Scenario",
            subtitle="Structured inspector",
            children=_scenario_placeholder(
                "Submit a scenario to see the validated summary, parameter mapping, and raw LLM JSON."
            ),
            class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
        )

    if status == "pending":
        return card(
            title="Parser Working",
            subtitle=subtitle,
            children=[
                html.Div(
                    scenario_state.get("description", ""),
                    className="cp-scenario__pending-description",
                ),
                html.Div(
                    "The request has been sent. Structured fields will appear here as soon as validation completes.",
                    className="cp-scenario__reply-reasoning",
                ),
                html.Div(
                    [
                        html.Span(className="cp-scenario__thinking-dot"),
                        html.Span(className="cp-scenario__thinking-dot"),
                        html.Span(className="cp-scenario__thinking-dot"),
                    ],
                    className="cp-scenario__thinking",
                ),
            ],
            class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
        )

    if status in {"empty", "error"}:
        return card(
            title="Parser Error",
            subtitle=subtitle,
            children=html.Div(
                scenario_state.get("error") or "Unable to parse the scenario.",
                className="cp-scenario__reply-error",
            ),
            class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
        )

    result = scenario_state.get("result") or {}
    children = [
        html.Div("Parsed Feedback", className="cp-scenario__section-label"),
        html.P(
            result.get("scenario_summary", ""),
            className="cp-scenario__reply-summary cp-llm-inspector__prose",
        ),
        html.P(
            result.get("reasoning", ""),
            className="cp-scenario__reply-reasoning cp-llm-inspector__prose",
        ),
    ]
    if result.get("coverage_warning"):
        children.extend([
            html.Div("Coverage Warning", className="cp-scenario__section-label"),
            html.Div(
                [
                    html.Div(result.get("coverage_warning"), className="cp-scenario__warning-text cp-llm-inspector__prose"),
                    html.Div(
                        "Scenario Description Example",
                        className="cp-scenario__warning-example-label",
                    ),
                    html.Div(
                        result.get("example_description", SCENARIO_DESCRIPTION_EXAMPLE),
                        className="cp-scenario__warning-example",
                    ),
                ],
                className="cp-scenario__warning-panel",
            ),
        ])
    children.extend([
        html.Div("Model Parameters", className="cp-scenario__section-label"),
        _build_scenario_output_param_grid(result),
        html.Div("How To Use These Parameters", className="cp-scenario__section-label"),
        html.Div(
            result.get("next_step_guidance", SCENARIO_NEXT_STEP_GUIDANCE),
            className="cp-scenario__next-step cp-llm-inspector__prose",
        ),
    ])
    raw_block = _build_scenario_raw_output(scenario_state.get("raw_response"))
    if raw_block is not None:
        children.extend([
            html.Div("Raw LLM Output", className="cp-scenario__section-label"),
            raw_block,
        ])

    return card(
        title="Latest Parsed Scenario",
        subtitle=subtitle,
        children=children,
        class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
    )


def _default_chat_state() -> dict[str, Any]:
    """Return the initial Result Interpreter state."""
    return {
        "status": "idle",
        "error": None,
        "elapsed": None,
        "model": None,
        "request_id": None,
        "history": [],
        "context": None,
        "raw_response": None,
        "last_send_clicks": 0,
        "last_submit_count": 0,
        "last_clear_clicks": 0,
    }


def _normalize_chat_state(data: dict[str, Any] | list[Any] | None) -> dict[str, Any]:
    """Merge arbitrary chat store payloads with the expected Interpreter schema."""
    state = _default_chat_state()

    # Backward compatibility for the previous store shape: a plain history list.
    if isinstance(data, list):
        state["history"] = [item for item in data if isinstance(item, dict)]
        if state["history"]:
            state["status"] = "success"
        return state

    if not isinstance(data, dict):
        return state

    state["status"] = str(data.get("status") or "idle")
    state["error"] = data.get("error")
    state["elapsed"] = data.get("elapsed")
    state["model"] = data.get("model")
    state["request_id"] = data.get("request_id")
    state["raw_response"] = data.get("raw_response")
    state["last_send_clicks"] = int(data.get("last_send_clicks") or 0)
    state["last_submit_count"] = int(data.get("last_submit_count") or 0)
    state["last_clear_clicks"] = int(data.get("last_clear_clicks") or 0)
    history = data.get("history")
    if isinstance(history, list):
        state["history"] = [item for item in history if isinstance(item, dict)]
    context_snapshot = data.get("context")
    if isinstance(context_snapshot, dict):
        state["context"] = context_snapshot

    return state


def _default_profile_state() -> dict[str, Any]:
    """Return the initial Profile Generator state."""
    return {
        "status": "idle",
        "error": None,
        "elapsed": None,
        "model": None,
        "request_id": None,
        "description": "",
        "result": None,
        "raw_response": None,
        "history": [],
        "last_generate_clicks": 0,
        "last_submit_count": 0,
        "last_clear_clicks": 0,
    }


def _normalize_profile_state(data: dict[str, Any] | None) -> dict[str, Any]:
    """Merge arbitrary store payloads with the expected Profile Generator schema."""
    state = _default_profile_state()
    if not isinstance(data, dict):
        return state

    state["status"] = str(data.get("status") or "idle")
    state["error"] = data.get("error")
    state["elapsed"] = data.get("elapsed")
    state["model"] = data.get("model")
    state["request_id"] = data.get("request_id")
    state["description"] = str(data.get("description") or "")
    state["result"] = data.get("result") if isinstance(data.get("result"), dict) else None
    state["raw_response"] = data.get("raw_response")
    state["last_generate_clicks"] = int(data.get("last_generate_clicks") or 0)
    state["last_submit_count"] = int(data.get("last_submit_count") or 0)
    state["last_clear_clicks"] = int(data.get("last_clear_clicks") or 0)
    history = data.get("history")
    if isinstance(history, list):
        state["history"] = [item for item in history if isinstance(item, dict)]

    return state


def _compact_value(value: Any) -> Any:
    """Round floats for compact context display while leaving other values untouched."""
    if isinstance(value, float):
        return round(value, 4)
    return value


def _build_chat_context_snapshot() -> dict[str, Any]:
    """Build the exact simulation snapshot injected into the Result Interpreter."""
    sim_model = app_state.get_model()
    preset = app_state.get_current_preset() or "custom"

    if sim_model is None or sim_model.current_step == 0:
        return {
            "initialized": False,
            "current_step": 0,
            "preset": preset,
            "note": "No simulation results are available yet. Initialize a simulation and run at least one step to ground the interpretation in data.",
            "latest_metrics": {},
            "params": {},
        }

    df = sim_model.get_model_dataframe()
    latest = df.iloc[-1].to_dict() if not df.empty else {}
    params = sim_model.get_params()

    return {
        "initialized": True,
        "current_step": sim_model.current_step,
        "preset": preset,
        "note": "This snapshot is injected into the interpreter prompt together with your question.",
        "latest_metrics": {
            key: _compact_value(latest.get(key))
            for key, _ in CHAT_CONTEXT_METRICS
            if key in latest
        },
        "params": {
            key: _compact_value(params.get(key))
            for key, _ in CHAT_CONTEXT_PARAMS
            if key in params
        },
    }


def _build_chat_intro():
    """Render a compact guide for the Result Interpreter tab."""
    return html.Div(
        [
            html.Div("How To Use Chat Interpreter", className="cp-scenario-guide__label"),
            html.Div(
                "Ask questions about the current simulation run. Your message is sent together with the latest experiment snapshot, and the interpreter explains the results, connects them to hypotheses, and notes important caveats.",
                className="cp-scenario-guide__text",
            ),
        ],
        className="cp-scenario-guide",
    )


def _build_chat_context_chip(label: str, value: Any, accent: bool = False):
    """Render one compact dashboard-style context chip."""
    classes = "cp-chat-context__chip"
    if accent:
        classes += " cp-chat-context__chip--accent"
    return html.Div(
        [
            html.Div(label, className="cp-chat-context__label"),
            html.Div(_format_scenario_value(value), className="cp-chat-context__value"),
        ],
        className=classes,
    )


def _build_chat_context_grid(values: dict[str, Any], fields: list[tuple[str, str]], *, accent_first: bool = False):
    """Render a compact grid of dashboard-style context chips."""
    chips = [
        _build_chat_context_chip(label, values.get(key), accent=accent_first and index == 0)
        for index, (key, label) in enumerate(fields)
        if key in values
    ]
    return html.Div(chips, className="cp-chat-context__grid")


def _build_chat_context_panel(chat_state: dict[str, Any] | None):
    """Render the current simulation snapshot being interpreted."""
    chat_state = chat_state or {}
    context_snapshot = chat_state.get("context") or _build_chat_context_snapshot()
    initialized = bool(context_snapshot.get("initialized"))
    subtitle = "Simulation snapshot injected into the interpreter"

    if not initialized:
        return card(
            title="Current Interpretation Context",
            subtitle=subtitle,
            children=_scenario_placeholder(str(context_snapshot.get("note") or "No simulation context available.")),
            class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
        )

    latest_metrics = context_snapshot.get("latest_metrics") or {}
    params = context_snapshot.get("params") or {}
    summary_values = {
        "current_step": context_snapshot.get("current_step", 0),
        "preset": str(context_snapshot.get("preset", "custom")).replace("_", " ").title(),
        "avg_stress": latest_metrics.get("avg_stress"),
        "avg_delegation_rate": latest_metrics.get("avg_delegation_rate"),
    }

    children = [
        html.Div(
            [
                status_badge("Live results", "success"),
                status_badge("Prompt-grounded", "info"),
            ],
            className="d-flex gap-2 flex-wrap mb-3",
        ),
        _build_chat_context_grid(
            summary_values,
            [
                ("current_step", "Current Step"),
                ("preset", "Preset"),
                ("avg_stress", "Avg Stress"),
                ("avg_delegation_rate", "Delegation Rate"),
            ],
            accent_first=True,
        ),
        html.Div(
            str(context_snapshot.get("note") or ""),
            className="cp-scenario__reply-reasoning cp-llm-inspector__prose",
        ),
        html.Div("Latest Metrics", className="cp-scenario__section-label"),
        _build_chat_context_grid(latest_metrics, CHAT_CONTEXT_METRICS),
        html.Div("Model Parameters", className="cp-scenario__section-label"),
        _build_chat_context_grid(params, CHAT_CONTEXT_PARAMS),
    ]

    raw_block = _build_scenario_raw_output(
        context_snapshot,
        summary_text="View injected context JSON",
    )
    if raw_block is not None:
        children.extend([
            html.Div("Prompt Context", className="cp-scenario__section-label"),
            raw_block,
        ])

    return card(
        title="Current Interpretation Context",
        subtitle=subtitle,
        children=children,
        class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
    )


def _profile_prompt_text(button_id: str | None) -> str | None:
    """Return the full prompt text for one suggested-profile button id."""
    for prompt_button_id, _, prompt_text in PROFILE_SUGGESTED_PROMPTS:
        if prompt_button_id == button_id:
            return prompt_text
    return None


def _profile_skill_fields() -> list[tuple[str, str]]:
    """Return the subset of profile fields that belong to task skills."""
    return [field for field in PROFILE_PARAM_FIELDS if field[0].startswith("skill_")]


def _profile_strength_label(value: Any) -> str:
    """Return a readable qualitative label for one profile score."""
    if not isinstance(value, (int, float)):
        return "Unknown"
    if value < 0.4:
        return "Low"
    if value < 0.7:
        return "Moderate"
    return "High"


def _profile_delegation_style(value: Any) -> str:
    """Return a plain-language behavioural label for delegation preference."""
    if not isinstance(value, (int, float)):
        return "Underspecified"
    if value < 0.35:
        return "Mostly self-serve"
    if value < 0.65:
        return "Mixed strategy"
    return "Service-oriented"


def _build_profile_intro():
    """Render a compact guide for the Profile Generator tab."""
    return html.Div(
        [
            html.Div("How To Use Profile Generator", className="cp-scenario-guide__label"),
            html.Div(
                "Describe one agent type in plain language, including routines, time pressure, comfort with services, and strengths across chores, paperwork, errands, or repairs. "
                "The generator returns a readable archetype summary together with explicit delegation and skill attributes you can use in simulation setup.",
                className="cp-scenario-guide__text",
            ),
            html.Div(
                [
                    html.Div("Suggested prompts", className="cp-profile__prompt-label"),
                    html.Div(
                        [
                            dbc.Button(
                                label,
                                id=button_id,
                                className="cp-btn-outline cp-profile__prompt-btn",
                                size="sm",
                            )
                            for button_id, label, _ in PROFILE_SUGGESTED_PROMPTS
                        ],
                        className="cp-profile__prompt-row",
                    ),
                ],
                className="cp-profile__prompt-strip",
            ),
        ],
        className="cp-scenario-guide",
    )


def _build_profile_skill_figure(result: dict[str, Any] | None) -> go.Figure:
    """Build a radar chart that visualises the generated task-skill mix."""
    result = result or {}
    skill_fields = _profile_skill_fields()
    labels = [label.replace(" Skill", "") for _, label in skill_fields]
    values = [float(result.get(key, 0.0) or 0.0) for key, _ in skill_fields]
    if values:
        labels.append(labels[0])
        values.append(values[0])

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=labels,
        fill="toself",
        fillcolor="rgba(44,140,153,0.14)",
        line=dict(color=CHART_COLORWAY[0], width=2),
        name="Skill mix",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickfont=dict(size=10),
            ),
        ),
        showlegend=False,
        margin=dict(t=24, b=16, l=36, r=36),
        height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _build_profile_summary_grid(result: dict[str, Any] | None):
    """Render a compact summary of the generated agent archetype."""
    result = result or {}
    skill_fields = _profile_skill_fields()
    strongest_skill = max(
        skill_fields,
        key=lambda item: float(result.get(item[0], 0.0) or 0.0),
    )
    weakest_skill = min(
        skill_fields,
        key=lambda item: float(result.get(item[0], 0.0) or 0.0),
    )
    summary_cards = [
        _build_chat_context_chip(
            "Delegation Style",
            _profile_delegation_style(result.get("delegation_preference")),
            accent=True,
        ),
        _build_chat_context_chip(
            "Delegation Preference",
            f"{_format_scenario_value(result.get('delegation_preference'))} · {_profile_strength_label(result.get('delegation_preference'))}",
        ),
        _build_chat_context_chip(
            "Strongest Skill",
            f"{strongest_skill[1].replace(' Skill', '')} · {_format_scenario_value(result.get(strongest_skill[0]))}",
        ),
        _build_chat_context_chip(
            "Lowest Skill",
            f"{weakest_skill[1].replace(' Skill', '')} · {_format_scenario_value(result.get(weakest_skill[0]))}",
        ),
    ]
    return html.Div(summary_cards, className="cp-chat-context__grid")


def _build_profile_param_grid(result: dict[str, Any] | None):
    """Render simulation-facing profile parameters with explanation text."""
    result = result or {}
    cards = []
    for field_key, field_label in PROFILE_PARAM_FIELDS:
        cards.append(
            html.Div(
                [
                    html.Div(field_label, className="cp-chat-context__label"),
                    html.Div(
                        _format_scenario_value(result.get(field_key)),
                        className="cp-chat-context__value",
                    ),
                    html.Div(
                        PROFILE_PARAM_HELP.get(
                            field_key,
                            AgentProfileOutput.model_fields[field_key].description or "",
                        ),
                        className="cp-profile__param-help",
                    ),
                ],
                className="cp-chat-context__chip cp-profile__param-card",
            )
        )
    return html.Div(cards, className="cp-chat-context__grid")


def _build_profile_message_chips(result: dict[str, Any] | None):
    """Render compact profile metrics inside the assistant reply bubble."""
    result = result or {}
    strongest_skill = max(
        _profile_skill_fields(),
        key=lambda item: float(result.get(item[0], 0.0) or 0.0),
    )
    chips = [
        html.Div(
            [
                html.Div("Delegation Style", className="cp-scenario__metric-label"),
                html.Div(
                    _profile_delegation_style(result.get("delegation_preference")),
                    className="cp-scenario__metric-value",
                ),
            ],
            className="cp-scenario__metric-chip",
        ),
        html.Div(
            [
                html.Div("Delegation Preference", className="cp-scenario__metric-label"),
                html.Div(
                    _format_scenario_value(result.get("delegation_preference")),
                    className="cp-scenario__metric-value",
                ),
            ],
            className="cp-scenario__metric-chip",
        ),
        html.Div(
            [
                html.Div("Strongest Skill", className="cp-scenario__metric-label"),
                html.Div(
                    f"{strongest_skill[1].replace(' Skill', '')} · {_format_scenario_value(result.get(strongest_skill[0]))}",
                    className="cp-scenario__metric-value",
                ),
            ],
            className="cp-scenario__metric-chip",
        ),
    ]
    return html.Div(chips, className="cp-scenario__metric-grid")


def _build_profile_thread(profile_state: dict[str, Any] | None):
    """Render the chat-style Profile Generator transcript."""
    profile_state = profile_state or {}
    history = profile_state.get("history") or []
    if not history:
        return _scenario_placeholder(
            "Describe one agent type and the generator will translate it into explicit delegation and skill attributes."
        )

    bubbles = []
    for message in history:
        if message.get("role") == "user":
            bubbles.append(
                html.Div([
                    html.Div("You", className="cp-chat__sender"),
                    html.Div(message.get("content", "")),
                ], className="cp-chat__message cp-chat__message--user")
            )
            continue

        meta = []
        if message.get("model"):
            meta.append(str(message.get("model")))
        if isinstance(message.get("elapsed"), (int, float)):
            meta.append(f"{message['elapsed']:.1f}s")

        body_children = [
            html.Div("Profile Generator", className="cp-chat__sender"),
            html.Div(
                message.get("content", ""),
                className="cp-scenario__reply-summary",
            ),
        ]

        if message.get("status") == "pending":
            body_children.extend([
                html.Div(
                    "Translating your description into one simulation-ready agent archetype with explicit delegation and task-skill values.",
                    className="cp-scenario__reply-reasoning",
                ),
                html.Div(
                    [
                        html.Span(className="cp-scenario__thinking-dot"),
                        html.Span(className="cp-scenario__thinking-dot"),
                        html.Span(className="cp-scenario__thinking-dot"),
                    ],
                    className="cp-scenario__thinking",
                ),
            ])
        elif message.get("status") == "error":
            body_children.append(
                html.Div(
                    message.get("error", "Profile generation failed."),
                    className="cp-scenario__reply-error",
                )
            )
        else:
            body_children.extend([
                _build_profile_message_chips(message.get("result")),
                html.Div(
                    "The structured profile is ready in the inspector on the right.",
                    className="cp-scenario__reply-reasoning",
                ),
            ])
            raw_block = _build_scenario_raw_output(
                message.get("raw_response"),
                summary_text="View raw profile JSON",
            )
            if raw_block is not None:
                body_children.append(raw_block)

        if meta:
            body_children.append(
                html.Div(" · ".join(meta), className="cp-scenario__message-meta")
            )

        bubbles.append(
            html.Div(
                body_children,
                className="cp-chat__message cp-chat__message--ai cp-scenario__assistant-message",
            )
        )

    return html.Div(bubbles, className="cp-chat")


def _build_profile_output(profile_state: dict[str, Any] | None):
    """Render the generated profile inspector."""
    profile_state = profile_state or {}
    status = profile_state.get("status", "idle")
    subtitle_parts = []
    elapsed = profile_state.get("elapsed")
    if isinstance(elapsed, (int, float)):
        subtitle_parts.append(f"{elapsed:.1f}s")
    model_name = profile_state.get("model")
    if model_name:
        subtitle_parts.append(str(model_name))
    subtitle = " · ".join(subtitle_parts) if subtitle_parts else "Simulation-ready agent archetype"

    if status == "idle":
        return card(
            title="Generated Agent Type",
            subtitle=subtitle,
            children=_scenario_placeholder(
                "Generate a profile to inspect the archetype summary, delegation tendency, task-skill mix, and raw LLM JSON."
            ),
            class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
        )

    if status == "pending":
        return card(
            title="Generating Profile",
            subtitle=subtitle,
            children=[
                html.Div(
                    profile_state.get("description", ""),
                    className="cp-scenario__pending-description",
                ),
                html.Div(
                    "The description has been sent. Delegation and skill attributes will appear here as soon as the structured profile is validated.",
                    className="cp-scenario__reply-reasoning",
                ),
                html.Div(
                    [
                        html.Span(className="cp-scenario__thinking-dot"),
                        html.Span(className="cp-scenario__thinking-dot"),
                        html.Span(className="cp-scenario__thinking-dot"),
                    ],
                    className="cp-scenario__thinking",
                ),
            ],
            class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
        )

    if status in {"empty", "error"}:
        return card(
            title="Profile Generator Error",
            subtitle=subtitle,
            children=html.Div(
                profile_state.get("error") or "Unable to generate the agent profile.",
                className="cp-scenario__reply-error",
            ),
            class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
        )

    result = profile_state.get("result") or {}
    children = [
        html.Div(
            [
                status_badge("Profile ready", "success"),
                status_badge("Simulation-ready", "info"),
            ],
            className="d-flex gap-2 flex-wrap mb-1",
        ),
        html.Div("Agent Type Summary", className="cp-scenario__section-label"),
        html.P(
            result.get("profile_description", ""),
            className="cp-scenario__reply-summary cp-llm-inspector__prose",
        ),
        _build_profile_summary_grid(result),
        html.Div("Skill Profile", className="cp-scenario__section-label"),
        html.Div(
            [
                html.Div(
                    dcc.Graph(
                        figure=_build_profile_skill_figure(result),
                        config={"displayModeBar": False},
                    ),
                    className="cp-profile__chart-shell",
                ),
                html.Div(
                    "Higher skill values mean the archetype can self-serve more effectively in that task domain, which reduces the need to delegate when time allows.",
                    className="cp-scenario__reply-reasoning cp-llm-inspector__prose",
                ),
            ],
            className="cp-profile__visual-wrap",
        ),
        html.Div("Parameter Breakdown", className="cp-scenario__section-label"),
        _build_profile_param_grid(result),
        html.Div("How To Use This Agent Type", className="cp-scenario__section-label"),
        html.Div(
            PROFILE_NEXT_STEP_GUIDANCE,
            className="cp-scenario__next-step cp-llm-inspector__prose",
        ),
    ]
    raw_block = _build_scenario_raw_output(
        profile_state.get("raw_response"),
        summary_text="View raw profile JSON",
    )
    if raw_block is not None:
        children.extend([
            html.Div("Raw LLM Output", className="cp-scenario__section-label"),
            raw_block,
        ])

    return card(
        title="Generated Agent Type",
        subtitle=subtitle,
        children=children,
        class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
    )


def _stage_profile_request(
    profile_data: dict[str, Any] | None,
    description: str,
    model_name: str,
    request_id: str,
) -> dict[str, Any]:
    """Append the user turn and a pending assistant turn before the LLM returns."""
    state = _normalize_profile_state(profile_data)
    state.update({
        "status": "pending",
        "error": None,
        "elapsed": None,
        "model": model_name,
        "request_id": request_id,
        "description": description,
        "result": None,
        "raw_response": None,
    })
    state["history"].append({
        "id": f"{request_id}-user",
        "role": "user",
        "content": description,
    })
    state["history"].append({
        "id": f"{request_id}-assistant",
        "role": "assistant",
        "request_id": request_id,
        "status": "pending",
        "model": model_name,
        "content": "Reading your description and drafting one simulation-ready agent profile.",
    })
    return state


def _complete_profile_request(
    profile_data: dict[str, Any] | None,
    request_id: str,
    model_name: str,
    elapsed: float,
    *,
    result: dict[str, Any] | None = None,
    raw_response: Any = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Replace the pending assistant turn with the final Profile Generator reply."""
    state = _normalize_profile_state(profile_data)
    is_success = error is None and result is not None

    for message in state["history"]:
        if message.get("role") == "assistant" and message.get("request_id") == request_id:
            message.update({
                "status": "success" if is_success else "error",
                "model": model_name,
                "elapsed": elapsed,
                "content": (result or {}).get("profile_description", "Profile ready.") if is_success else error,
                "result": result if is_success else None,
                "raw_response": raw_response,
                "error": error,
            })
            break

    state.update({
        "status": "success" if is_success else "error",
        "error": error,
        "elapsed": elapsed,
        "model": model_name,
        "request_id": request_id,
        "result": result if is_success else None,
        "raw_response": raw_response,
    })
    return state


def _default_annotation_state() -> dict[str, Any]:
    """Return the initial Visualization Annotator state."""
    return {
        "status": "idle",
        "error": None,
        "note": ANNOTATION_WORKFLOW_NOTE,
        "current_step": 0,
        "preset": "custom",
        "model": None,
        "request_id": None,
        "items": [],
        "generated_at": None,
        "last_annotate_clicks": 0,
        "last_clear_clicks": 0,
    }


def _normalize_annotation_state(data: dict[str, Any] | None) -> dict[str, Any]:
    """Merge arbitrary store payloads with the expected annotation schema."""
    state = _default_annotation_state()
    if not isinstance(data, dict):
        return state

    state["status"] = str(data.get("status") or "idle")
    state["error"] = data.get("error")
    state["note"] = str(data.get("note") or ANNOTATION_WORKFLOW_NOTE)
    state["current_step"] = int(data.get("current_step") or 0)
    state["preset"] = str(data.get("preset") or "custom")
    state["model"] = data.get("model")
    state["request_id"] = data.get("request_id")
    state["generated_at"] = data.get("generated_at")
    state["last_annotate_clicks"] = int(data.get("last_annotate_clicks") or 0)
    state["last_clear_clicks"] = int(data.get("last_clear_clicks") or 0)
    items = data.get("items")
    if isinstance(items, list):
        state["items"] = [item for item in items if isinstance(item, dict)]

    return state


import threading

# --- Server-Side Forum State ---
# The forum processing callback fires on an interval. In a threaded Dash server,
# multiple interval ticks can fire concurrently, each carrying stale client-side
# State values. To prevent duplicate processing, the authoritative forum state
# lives here on the server. The callback reads/writes this variable under a lock,
# then returns the state to forum-history-store for UI rendering only.
_forum_server_state: dict[str, Any] | None = None
_forum_stop_requested: bool = False
_forum_lock = threading.Lock()


def _default_forum_state() -> dict[str, Any]:
    """Return the initial Agent Forums state."""
    return {
        "status": "idle",
        "error": None,
        "note": FORUM_WORKFLOW_NOTE,
        "model": None,
        "model_instance_id": None,
        "request_id": None,
        "current_step": 0,
        "forum_fraction": 0.20,
        "requested_agent_count": 0,
        "requested_group_count": 2,
        "participant_source": "fraction",
        "num_turns": 2,
        "agent_count": 0,
        "group_count": 0,
        "group_sizes": [],
        "estimated_turns": 0,
        "estimated_llm_calls": 0,
        "stop_requested": False,
        "elapsed": None,
        "generated_at": None,
        "started_at": None,
        "groups": [],
        "last_run_clicks": 0,
        "last_clear_clicks": 0,
    }


def _normalize_forum_state(data: dict[str, Any] | None) -> dict[str, Any]:
    """Merge arbitrary store payloads with the expected forum schema."""
    state = _default_forum_state()
    if not isinstance(data, dict):
        return state

    state["status"] = str(data.get("status") or "idle")
    state["error"] = data.get("error")
    state["note"] = str(data.get("note") or FORUM_WORKFLOW_NOTE)
    state["model"] = data.get("model")
    state["model_instance_id"] = data.get("model_instance_id")
    state["request_id"] = data.get("request_id")
    state["current_step"] = int(data.get("current_step") or 0)
    state["forum_fraction"] = float(data.get("forum_fraction") or 0.20)
    state["requested_agent_count"] = int(data.get("requested_agent_count") or 0)
    state["requested_group_count"] = int(
        data.get("requested_group_count")
        or data.get("group_count")
        or data.get("group_size")
        or 2
    )
    state["participant_source"] = str(data.get("participant_source") or "fraction")
    state["num_turns"] = int(data.get("num_turns") or 2)
    state["agent_count"] = int(data.get("agent_count") or 0)
    state["group_count"] = int(data.get("group_count") or 0)
    group_sizes = data.get("group_sizes")
    if isinstance(group_sizes, list):
        state["group_sizes"] = [int(size) for size in group_sizes if isinstance(size, (int, float))]
    state["estimated_turns"] = int(data.get("estimated_turns") or 0)
    state["estimated_llm_calls"] = int(data.get("estimated_llm_calls") or 0)
    state["stop_requested"] = bool(data.get("stop_requested"))
    state["elapsed"] = data.get("elapsed")
    state["generated_at"] = data.get("generated_at")
    state["started_at"] = data.get("started_at")
    state["last_run_clicks"] = int(data.get("last_run_clicks") or 0)
    state["last_clear_clicks"] = int(data.get("last_clear_clicks") or 0)
    groups = data.get("groups")
    if isinstance(groups, list):
        state["groups"] = [item for item in groups if isinstance(item, dict)]

    return state


def _default_forum_control_state() -> dict[str, Any]:
    """Keep transient forum execution controls separate from transcript state."""
    return {
        "request_id": None,
        "stop_requested": False,
        "last_stop_clicks": 0,
    }


def _normalize_forum_control_state(data: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize the forum control store payload."""
    state = _default_forum_control_state()
    if not isinstance(data, dict):
        return state

    state["request_id"] = data.get("request_id")
    state["stop_requested"] = bool(data.get("stop_requested"))
    state["last_stop_clicks"] = int(data.get("last_stop_clicks") or 0)
    return state


def _copy_forum_state(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Clone the authoritative forum state so concurrent responses can replay it safely."""
    if not isinstance(data, dict):
        return None

    state = dict(data)
    state["groups"] = [dict(group) for group in (state.get("groups") or []) if isinstance(group, dict)]
    return state


def _build_annotations_intro():
    """Render a compact guide for the Visualization Annotator tab."""
    return html.Div(
        [
            html.Div("How To Use Annotations", className="cp-scenario-guide__label"),
            html.Div(
                ANNOTATION_GUIDANCE,
                className="cp-scenario-guide__text",
            ),
        ],
        className="cp-scenario-guide",
    )


def _build_forum_intro():
    """Render a compact guide for the Agent Forums tab."""
    return html.Div(
        [
            html.Div("How To Use Agent Forums", className="cp-scenario-guide__label"),
            html.Div(
                FORUM_GUIDANCE,
                className="cp-scenario-guide__text",
            ),
            html.Div(
                [
                    status_badge("Experimental Mode", "warning"),
                    status_badge("Role 5", "primary"),
                    html.Span(
                        "Short 1–3 turn exchanges keep the experimental layer bounded and readable.",
                        className="cp-scenario-guide__text",
                    ),
                ],
                className="cp-forum__guide-meta",
            ),
        ],
        className="cp-scenario-guide",
    )


def _build_forum_scale_summary(
    forum_fraction: float,
    requested_agent_count: int,
    requested_group_count: int,
    num_turns: int,
) -> Any:
    """Render a compact scale preview so users can judge forum load before running."""
    from model.forums import plan_forum_groups

    sim_model = app_state.get_model()
    if sim_model is None:
        return html.Div(
            "Initialize a simulation first to preview how many residents can join the forum.",
            className="cp-scenario__composer-note",
        )

    total_agents = len(list(sim_model.agents))
    plan = plan_forum_groups(
        total_agents,
        forum_fraction=float(forum_fraction or 0.0),
        group_count=int(requested_group_count or 1),
        participant_count=int(requested_agent_count or 0) or None,
    )
    participant_count = int(plan.get("participant_count") or 0)
    actual_group_count = int(plan.get("actual_group_count") or 0)
    group_sizes = list(plan.get("group_sizes") or [])
    estimated_turns = participant_count * int(num_turns or 0)
    estimated_llm_calls = estimated_turns + actual_group_count if actual_group_count else 0
    size_distribution = " / ".join(str(size) for size in group_sizes) if group_sizes else "—"

    badges = []
    if plan.get("participant_source") == "count" and int(requested_agent_count or 0) > 0:
        badges.append(status_badge("Exact participant count", "primary"))
    else:
        badges.append(status_badge("Fraction-derived participant count", "info"))
    if plan.get("group_count_adjusted"):
        badges.append(status_badge("Groups adjusted to fit available participants", "warning"))
    if plan.get("participant_count_adjusted"):
        badges.append(status_badge("Participants capped to keep groups readable", "warning"))
    if estimated_llm_calls > 36:
        badges.append(status_badge("High LLM load", "warning"))
    elif estimated_llm_calls > 0:
        badges.append(status_badge("Bounded workload", "info"))

    note = (
        "You can invite residents by fraction or override with an exact count. Group membership is "
        "distributed automatically from the requested group count, and each group is capped to a small, "
        "readable discussion size so the transcript stays responsive. Each participant speaks once per turn "
        "round, and each group needs one extra extraction call."
    )

    return html.Div(
        [
            html.Div(badges, className="d-flex gap-2 flex-wrap mb-3"),
            _build_chat_context_grid(
                {
                    "total_population": total_agents,
                    "requested_agent_count": int(requested_agent_count or 0) or "—",
                    "participant_count": participant_count,
                    "requested_group_count": requested_group_count,
                    "actual_group_count": actual_group_count,
                    "group_sizes": size_distribution,
                    "num_turns": int(num_turns or 0),
                    "estimated_turns": estimated_turns,
                    "estimated_llm_calls": estimated_llm_calls,
                },
                [
                    ("total_population", "Population"),
                    ("requested_agent_count", "Requested Agents"),
                    ("participant_count", "Invited Agents"),
                    ("requested_group_count", "Requested Groups"),
                    ("actual_group_count", "Actual Groups"),
                    ("group_sizes", "Agents Per Group"),
                    ("num_turns", "Turn Rounds"),
                    ("estimated_turns", "Dialogue Turns"),
                    ("estimated_llm_calls", "Estimated LLM Calls"),
                ],
                accent_first=True,
            ),
            html.Div(note, className="cp-scenario__composer-note"),
        ],
        className="cp-forum__plan-summary",
    )


def _forum_resident_short_label(agent_id: Any) -> str:
    """Return a compact resident label for group chips and pending states."""
    try:
        return f"Resident #{int(agent_id) % 100}"
    except (TypeError, ValueError):
        return "Resident"


def _forum_group_status_badge(status: str):
    """Map one forum-group status to a compact badge."""
    badge_map = {
        "queued": ("Queued", "neutral"),
        "active": ("Dialogue live", "info"),
        "waiting_outcome": ("Extracting norm signal", "warning"),
        "success": ("Forum complete", "success"),
        "stopped": ("Stopped gracefully", "warning"),
        "error": ("Forum failed", "danger"),
    }
    label, variant = badge_map.get(status, ("Idle", "neutral"))
    return status_badge(label, variant)


def _build_forum_group_participants(group: dict[str, Any] | None):
    """Render compact participant chips for one forum group."""
    group = group or {}
    chips = [
        html.Div(
            [
                html.Div("Participant", className="cp-chat-context__label"),
                html.Div(_forum_resident_short_label(agent_id), className="cp-chat-context__value"),
            ],
            className="cp-chat-context__chip",
        )
        for agent_id in group.get("agent_ids", [])
    ]
    return html.Div(chips, className="cp-chat-context__grid")


def _build_forum_thread(group: dict[str, Any] | None):
    """Render one group transcript with a pending speaker bubble when active."""
    group = group or {}
    turns = group.get("turns") or []
    status = str(group.get("status") or "queued")
    bubbles = []

    if not turns and status == "queued":
        return _scenario_placeholder(
            "This group is queued. Its discussion will begin automatically when earlier groups finish."
        )

    for turn in turns:
        bubbles.append(
            html.Div(
                [
                    html.Div(str(turn.get("speaker_label") or "Resident"), className="cp-chat__sender"),
                    html.Div(str(turn.get("content") or "")),
                ],
                className="cp-chat__message cp-chat__message--ai cp-forum__message",
            )
        )

    current_agent_ids = group.get("agent_ids") or []
    turn_cursor = int(group.get("turn_cursor") or 0)
    if status == "active" and current_agent_ids:
        current_speaker_id = current_agent_ids[turn_cursor % len(current_agent_ids)]
        bubbles.append(
            html.Div(
                [
                    html.Div(_forum_resident_short_label(current_speaker_id), className="cp-chat__sender"),
                    html.Div(
                        "Thinking about the group's delegation norms before replying.",
                        className="cp-scenario__reply-reasoning",
                    ),
                    html.Div(
                        [
                            html.Span(className="cp-scenario__thinking-dot"),
                            html.Span(className="cp-scenario__thinking-dot"),
                            html.Span(className="cp-scenario__thinking-dot"),
                        ],
                        className="cp-scenario__thinking",
                    ),
                ],
                className="cp-chat__message cp-chat__message--ai cp-forum__message cp-forum__message--pending",
            )
        )
    elif status == "waiting_outcome":
        bubbles.append(
            html.Div(
                [
                    html.Div("Forum Summary", className="cp-chat__sender"),
                    html.Div(
                        "Dialogue complete. Extracting the group's norm signal and bounded preference update.",
                        className="cp-scenario__reply-reasoning",
                    ),
                    html.Div(
                        [
                            html.Span(className="cp-scenario__thinking-dot"),
                            html.Span(className="cp-scenario__thinking-dot"),
                            html.Span(className="cp-scenario__thinking-dot"),
                        ],
                        className="cp-scenario__thinking",
                    ),
                ],
                className="cp-chat__message cp-chat__message--ai cp-forum__message cp-forum__message--pending",
            )
        )
    elif status in {"success", "stopped"} and isinstance(group.get("outcome"), dict):
        outcome = group.get("outcome") or {}
        bubbles.append(
            html.Div(
                [
                    html.Div("Forum Summary", className="cp-chat__sender"),
                    html.Div(
                        str(outcome.get("summary") or "The group finished its discussion."),
                        className="cp-scenario__reply-summary",
                    ),
                    html.Div(
                        (
                            f"Norm signal {_format_scenario_value(outcome.get('norm_signal'))} · confidence "
                            f"{_format_scenario_value(outcome.get('confidence'))}"
                            if status == "success"
                            else
                            f"Partial stop summary · norm signal {_format_scenario_value(outcome.get('norm_signal'))} · confidence "
                            f"{_format_scenario_value(outcome.get('confidence'))}"
                        ),
                        className="cp-scenario__message-meta",
                    ),
                ],
                className="cp-chat__message cp-chat__message--ai cp-forum__message cp-scenario__assistant-message",
            )
        )
    elif status == "stopped":
        bubbles.append(
            html.Div(
                [
                    html.Div("Forum Summary", className="cp-chat__sender"),
                    html.Div(
                        str(group.get("stop_note") or "This group was stopped before a summary could be produced."),
                        className="cp-scenario__reply-reasoning",
                    ),
                ],
                className="cp-chat__message cp-chat__message--ai cp-forum__message cp-scenario__assistant-message",
            )
        )
    elif status == "error":
        bubbles.append(
            html.Div(
                [
                    html.Div("Forum Summary", className="cp-chat__sender"),
                    html.Div(
                        str(group.get("error") or "This group could not be completed."),
                        className="cp-scenario__reply-error",
                    ),
                ],
                className="cp-chat__message cp-chat__message--ai cp-forum__message cp-scenario__assistant-message",
            )
        )

    return html.Div(bubbles, className="cp-chat")


def _build_forum_group_detail(group: dict[str, Any] | None, *, forums_pending: bool = False):
    """Render the right-side status and outcome panel for one forum group."""
    group = group or {}
    status = str(group.get("status") or "queued")
    turn_cursor = int(group.get("turn_cursor") or 0)
    total_turns = int(group.get("total_turns") or 0)

    summary_values = {
        "turn_progress": f"{turn_cursor}/{total_turns}" if total_turns else "0/0",
        "status": status.replace("_", " ").title(),
        "delta_applied": group.get("delta_applied") if group.get("delta_applied") is not None else 0.0,
        "elapsed": group.get("elapsed") or 0.0,
    }

    children = [
        _build_forum_group_participants(group),
        html.Div("Group Status", className="cp-scenario__section-label"),
        _build_chat_context_grid(
            summary_values,
            [
                ("turn_progress", "Turn Progress"),
                ("status", "Status"),
                ("delta_applied", "Delta Applied"),
                ("elapsed", "Elapsed (s)"),
            ],
            accent_first=True,
        ),
    ]

    if status == "queued":
        children.append(
            html.Div(
                "Queued behind earlier groups. The transcript will begin filling automatically.",
                className="cp-scenario__reply-reasoning cp-llm-inspector__prose",
            )
        )
    elif status in {"active", "waiting_outcome"}:
        children.append(
            html.Div(
                "This group is currently live. New turns and the final norm signal will appear here as soon as each step finishes.",
                className="cp-scenario__reply-reasoning cp-llm-inspector__prose",
            )
        )
    elif status in {"success", "stopped"}:
        outcome = group.get("outcome") or {}
        preference_updates = group.get("preference_updates") or []
        children.extend([
            html.Div("Forum Outcome", className="cp-scenario__section-label"),
            html.Div(
                str(
                    outcome.get("summary")
                    or group.get("stop_note")
                    or "The group completed without a readable summary."
                ),
                className="cp-scenario__reply-reasoning cp-llm-inspector__prose",
            ),
            _build_chat_context_grid(
                {
                    "norm_signal": outcome.get("norm_signal"),
                    "confidence": outcome.get("confidence"),
                    "agents_updated": len(preference_updates),
                    "delta_applied": group.get("delta_applied"),
                },
                [
                    ("norm_signal", "Norm Signal"),
                    ("confidence", "Confidence"),
                    ("agents_updated", "Agents Updated"),
                    ("delta_applied", "Delta Applied"),
                ],
            ),
        ])
        if status == "stopped" and group.get("stop_note"):
            children.append(
                html.Div(
                    str(group.get("stop_note")),
                    className="cp-scenario__reply-reasoning cp-llm-inspector__prose",
                )
            )
        if preference_updates:
            children.extend([
                html.Div("Preference Updates", className="cp-scenario__section-label"),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(_forum_resident_short_label(update.get("agent_id")), className="cp-chat-context__label"),
                                html.Div(
                                    f"{_format_scenario_value(update.get('before_preference'))} → {_format_scenario_value(update.get('after_preference'))}",
                                    className="cp-chat-context__value",
                                ),
                            ],
                            className="cp-chat-context__chip",
                        )
                        for update in preference_updates
                    ],
                    className="cp-chat-context__grid",
                ),
            ])
    elif status == "error":
        children.append(
            html.Div(
                str(group.get("error") or "The forum group could not be completed."),
                className="cp-scenario__reply-error",
            )
        )

    if status in {"success", "stopped", "error"}:
        children.append(
            dbc.Button(
                [html.I(className="fas fa-rotate-right me-1"), "Rerun This Group"],
                id={"type": "forum-rerun-btn", "index": int(group.get("index") or 0)},
                className="cp-btn-outline cp-forum__rerun-btn",
                size="sm",
                disabled=forums_pending,
            )
        )

    return html.Div(children, className="cp-forum__detail")


def _build_forum_group_card(group: dict[str, Any] | None, *, forums_pending: bool = False):
    """Render one forum group as a transcript card plus compact outcome panel."""
    group = group or {}
    group_index = int(group.get("index") or 0) + 1
    agent_ids = group.get("agent_ids") or []
    subtitle = f"{len(agent_ids)} agents · {' / '.join(_forum_resident_short_label(agent_id) for agent_id in agent_ids)}"
    return card(
        title=f"Group {group_index}",
        subtitle=subtitle,
        header_right=_forum_group_status_badge(str(group.get("status") or "queued")),
        children=html.Div(
            [
                html.Div(
                    _build_forum_thread(group),
                    className="cp-forum__thread-shell",
                ),
                _build_forum_group_detail(group, forums_pending=forums_pending),
            ],
            className="cp-forum__body",
        ),
        class_name="cp-forum__card",
    )


def _build_forum_output(forum_data: dict[str, Any] | None):
    """Render the Agent Forums workspace from the in-memory forum state."""
    state = _normalize_forum_state(forum_data)
    status = state.get("status", "idle")
    groups = state.get("groups") or []

    if status == "idle":
        return card(
            title="Forum Workspace",
            subtitle="Experimental small-group dialogue and bounded norm influence",
            children=[
                html.Div(
                    FORUM_WORKFLOW_NOTE,
                    className="cp-scenario__reply-reasoning cp-llm-inspector__prose",
                ),
                _scenario_placeholder(
                    "Click Run Forum to stage the discussion groups and watch each conversation appear as the forum progresses."
                ),
            ],
            class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
        )

    if status == "error" and not groups:
        return card(
            title="Forum Workspace",
            subtitle="Agent Forums",
            children=html.Div(
                str(state.get("error") or "Unable to stage the forum discussion."),
                className="cp-scenario__reply-error",
            ),
            class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
        )

    completed_groups = len([group for group in groups if group.get("status") == "success"])
    error_groups = len([group for group in groups if group.get("status") == "error"])
    stopped_groups = len([group for group in groups if group.get("status") == "stopped"])
    summary_values = {
        "current_step": state.get("current_step"),
        "forum_fraction": state.get("forum_fraction"),
        "requested_agent_count": state.get("requested_agent_count") or "—",
        "requested_group_count": state.get("requested_group_count"),
        "num_turns": state.get("num_turns"),
        "agent_count": state.get("agent_count"),
        "group_count": state.get("group_count"),
        "group_sizes": " / ".join(str(size) for size in state.get("group_sizes") or []) or "—",
        "estimated_llm_calls": state.get("estimated_llm_calls"),
        "participant_source": "Exact count" if state.get("participant_source") == "count" else "Forum Fraction",
        "model": state.get("model") or "—",
    }

    badges = [status_badge("Experimental Mode", "warning")]
    if status == "pending":
        badges.extend([
            status_badge(f"{completed_groups}/{len(groups)} groups complete", "info"),
            status_badge("LLM thinking", "warning"),
        ])
    elif error_groups:
        badges.extend([
            status_badge(f"{completed_groups}/{len(groups)} groups complete", "warning"),
            status_badge(f"{error_groups} group errors", "danger"),
        ])
    elif status == "stopped":
        badges.extend([
            status_badge(f"{completed_groups + stopped_groups}/{len(groups)} groups processed", "warning"),
            status_badge("Stopped gracefully", "warning"),
        ])
    else:
        badges.extend([
            status_badge(f"{len(groups)} groups complete", "success"),
            status_badge("Bounded norm updates applied", "info"),
        ])

    children = [
        html.Div(badges, className="d-flex gap-2 flex-wrap mb-3"),
        _build_chat_context_grid(
            summary_values,
            [
                ("current_step", "Current Step"),
                ("forum_fraction", "Forum Fraction"),
                ("requested_agent_count", "Requested Agents"),
                ("requested_group_count", "Requested Groups"),
                ("num_turns", "Dialogue Turns"),
                ("agent_count", "Participating Agents"),
                ("group_count", "Actual Groups"),
                ("group_sizes", "Agents Per Group"),
                ("estimated_llm_calls", "Estimated LLM Calls"),
                ("participant_source", "Invitation Mode"),
                ("model", "Model"),
            ],
            accent_first=True,
        ),
        html.Div(
            str(state.get("note") or FORUM_WORKFLOW_NOTE),
            className="cp-scenario__reply-reasoning cp-annotation__summary-note cp-llm-inspector__prose",
        ),
    ]

    if status == "error" and state.get("error"):
        children.append(
            html.Div(str(state.get("error")), className="cp-scenario__reply-error")
        )

    children.append(
        html.Div(
            [_build_forum_group_card(group, forums_pending=status == "pending") for group in groups],
            className="cp-forum__list",
        )
    )

    return html.Div(children)


def _build_audit_intro():
    """Render a compact guide for the Audit Log tab."""
    return html.Div(
        [
            html.Div("How To Use Audit Log", className="cp-scenario-guide__label"),
            html.Div(
                AUDIT_LOG_GUIDANCE,
                className="cp-scenario-guide__text",
            ),
        ],
        className="cp-scenario-guide",
    )


def _annotation_trend_label(values: list[float]) -> str:
    """Return a coarse trend label for one chart series."""
    if len(values) < 2:
        return "stable"
    start, end = float(values[0]), float(values[-1])
    tolerance = max(abs(start), abs(end), 1.0) * 0.02
    if abs(end - start) <= tolerance:
        return "stable"
    return "rising" if end > start else "falling"


def _annotation_series_values(df, column: str) -> list[float]:
    """Return one dataframe column as a JSON-serialisable float list."""
    return [round(float(value), 4) for value in df[column].tolist()]


def _build_annotation_item(spec: dict[str, str], df) -> dict[str, Any]:
    """Construct one chart preview payload and summary metrics for annotation."""
    # Match the simulation dashboard's step axis exactly so the preview cards
    # show the same time index the user sees on the main charts.
    steps = list(range(len(df)))
    chart_key = spec["chart_key"]

    if chart_key == "total_labor_hours":
        labor_values = _annotation_series_values(df, "total_labor_hours")
        metrics = {
            "min": round(min(labor_values), 4),
            "max": round(max(labor_values), 4),
            "mean": round(sum(labor_values) / len(labor_values), 4),
            "last": labor_values[-1],
            "trend": _annotation_trend_label(labor_values),
            "steps": len(labor_values),
        }
        summary_metrics = [
            {"label": "Latest", "value": metrics["last"]},
            {"label": "Mean", "value": metrics["mean"]},
            {"label": "Trend", "value": str(metrics["trend"]).title()},
            {"label": "Steps", "value": metrics["steps"]},
        ]
        preview = {
            "kind": "line",
            "steps": steps,
            "traces": [
                {
                    "type": "line",
                    "name": "Labor Hours",
                    "values": labor_values,
                    "color": CHART_COLORWAY[0],
                },
            ],
        }
    elif chart_key == "stress_delegation":
        stress_values = _annotation_series_values(df, "avg_stress")
        delegation_values = _annotation_series_values(df, "avg_delegation_rate")
        metrics = {
            "avg_stress_min": round(min(stress_values), 4),
            "avg_stress_max": round(max(stress_values), 4),
            "avg_stress_mean": round(sum(stress_values) / len(stress_values), 4),
            "avg_stress_last": stress_values[-1],
            "avg_stress_trend": _annotation_trend_label(stress_values),
            "avg_delegation_rate_min": round(min(delegation_values), 4),
            "avg_delegation_rate_max": round(max(delegation_values), 4),
            "avg_delegation_rate_mean": round(sum(delegation_values) / len(delegation_values), 4),
            "avg_delegation_rate_last": delegation_values[-1],
            "avg_delegation_rate_trend": _annotation_trend_label(delegation_values),
            "steps": len(stress_values),
        }
        summary_metrics = [
            {"label": "Stress", "value": metrics["avg_stress_last"]},
            {"label": "Delegation", "value": metrics["avg_delegation_rate_last"]},
            {"label": "Stress Trend", "value": str(metrics["avg_stress_trend"]).title()},
            {"label": "Steps", "value": metrics["steps"]},
        ]
        preview = {
            "kind": "dual_line",
            "steps": steps,
            "traces": [
                {
                    "type": "line",
                    "name": "Avg Stress",
                    "values": stress_values,
                    "color": CHART_COLORWAY[4],
                    "axis": "y",
                },
                {
                    "type": "line",
                    "name": "Delegation Rate",
                    "values": delegation_values,
                    "color": CHART_COLORWAY[5],
                    "axis": "y2",
                    "dash": "dash",
                },
            ],
        }
    elif chart_key == "social_efficiency":
        efficiency_values = _annotation_series_values(df, "social_efficiency")
        metrics = {
            "min": round(min(efficiency_values), 4),
            "max": round(max(efficiency_values), 4),
            "mean": round(sum(efficiency_values) / len(efficiency_values), 4),
            "last": efficiency_values[-1],
            "trend": _annotation_trend_label(efficiency_values),
            "steps": len(efficiency_values),
        }
        summary_metrics = [
            {"label": "Latest", "value": metrics["last"]},
            {"label": "Mean", "value": metrics["mean"]},
            {"label": "Trend", "value": str(metrics["trend"]).title()},
            {"label": "Steps", "value": metrics["steps"]},
        ]
        preview = {
            "kind": "line",
            "steps": steps,
            "traces": [
                {
                    "type": "line",
                    "name": "Social Efficiency",
                    "values": efficiency_values,
                    "color": CHART_COLORWAY[2],
                },
            ],
        }
    else:
        unmatched_values = _annotation_series_values(df, "unmatched_tasks")
        delegation_values = _annotation_series_values(df, "tasks_delegated_frac")
        metrics = {
            "unmatched_tasks_min": round(min(unmatched_values), 4),
            "unmatched_tasks_max": round(max(unmatched_values), 4),
            "unmatched_tasks_mean": round(sum(unmatched_values) / len(unmatched_values), 4),
            "unmatched_tasks_last": unmatched_values[-1],
            "unmatched_tasks_trend": _annotation_trend_label(unmatched_values),
            "tasks_delegated_frac_mean": round(sum(delegation_values) / len(delegation_values), 4),
            "tasks_delegated_frac_last": delegation_values[-1],
            "tasks_delegated_frac_trend": _annotation_trend_label(delegation_values),
            "steps": len(unmatched_values),
        }
        summary_metrics = [
            {"label": "Unmatched", "value": metrics["unmatched_tasks_last"]},
            {"label": "Delegation", "value": metrics["tasks_delegated_frac_last"]},
            {"label": "Trend", "value": str(metrics["unmatched_tasks_trend"]).title()},
            {"label": "Steps", "value": metrics["steps"]},
        ]
        preview = {
            "kind": "bar_line",
            "steps": steps,
            "traces": [
                {
                    "type": "bar",
                    "name": "Unmatched Tasks",
                    "values": unmatched_values,
                    "color": CHART_COLORWAY[4],
                    "axis": "y",
                },
                {
                    "type": "line",
                    "name": "Delegation Fraction",
                    "values": delegation_values,
                    "color": CHART_COLORWAY[1],
                    "axis": "y2",
                },
            ],
        }

    return {
        "chart_key": chart_key,
        "chart_label": spec["display_title"],
        "chart_subtitle": spec["subtitle"],
        "chart_description": spec["description"],
        "metrics": metrics,
        "summary_metrics": summary_metrics,
        "preview": preview,
        "status": "pending",
        "caption": None,
        "key_insight": None,
        "chart_title": None,
        "hypothesis_tag": None,
        "elapsed": None,
        "model": None,
        "error": None,
    }


def _build_annotation_snapshot() -> dict[str, Any]:
    """Capture the exact chart summaries that will be sent to the annotator."""
    sim_model = app_state.get_model()
    preset = app_state.get_current_preset() or "custom"
    model_name = app_state.get_role_model("role_4")

    if sim_model is None or sim_model.current_step == 0:
        return {
            "initialized": False,
            "current_step": 0,
            "preset": preset,
            "model": model_name,
            "note": "Initialize a simulation and run at least one step to preview and annotate charts.",
            "items": [],
        }

    df = sim_model.get_model_dataframe()
    if df.empty:
        return {
            "initialized": False,
            "current_step": sim_model.current_step,
            "preset": preset,
            "model": model_name,
            "note": "Run at least one simulation step so the chart summaries contain observable data.",
            "items": [],
        }

    return {
        "initialized": True,
        "current_step": sim_model.current_step,
        "preset": preset,
        "model": model_name,
        "note": "Each chart preview and summary below is injected into the prompt before the annotator writes a caption and key insight.",
        "items": [_build_annotation_item(spec, df) for spec in ANNOTATION_CHART_SPECS],
    }


def _build_annotation_preview_figure(item: dict[str, Any] | None) -> go.Figure:
    """Render one compact chart preview from the stored annotation snapshot."""
    item = item or {}
    preview = item.get("preview") or {}
    steps = preview.get("steps") or []

    fig = go.Figure()
    for trace in preview.get("traces", []):
        axis = "y2" if trace.get("axis") == "y2" else None
        if trace.get("type") == "bar":
            fig.add_trace(go.Bar(
                x=steps,
                y=trace.get("values", []),
                name=trace.get("name"),
                marker_color=trace.get("color"),
                opacity=0.72,
                yaxis=axis,
            ))
        else:
            fig.add_trace(go.Scatter(
                x=steps,
                y=trace.get("values", []),
                mode="lines",
                name=trace.get("name"),
                line=dict(
                    color=trace.get("color"),
                    width=2.2,
                    dash=trace.get("dash") or "solid",
                ),
                yaxis=axis,
            ))

    fig.update_layout(
        height=220,
        margin=dict(t=8, b=28, l=36, r=36),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(
            title=dict(text="Step", font=dict(size=10)),
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(148, 163, 184, 0.16)",
            zeroline=False,
            tickfont=dict(size=10),
        ),
    )

    if preview.get("kind") in {"dual_line", "bar_line"}:
        fig.update_layout(
            yaxis2=dict(
                overlaying="y",
                side="right",
                showgrid=False,
                zeroline=False,
                tickfont=dict(size=10),
            )
        )

    return fig


def _build_annotation_metric_grid(item: dict[str, Any] | None):
    """Render a compact data-summary grid for one chart snapshot."""
    item = item or {}
    chips = [
        html.Div(
            [
                html.Div(str(metric.get("label") or ""), className="cp-chat-context__label"),
                html.Div(
                    _format_scenario_value(metric.get("value")),
                    className="cp-chat-context__value",
                ),
            ],
            className="cp-chat-context__chip",
        )
        for metric in item.get("summary_metrics", [])
        if isinstance(metric, dict)
    ]
    return html.Div(chips, className="cp-chat-context__grid")


def _build_annotation_status_badges(item: dict[str, Any] | None):
    """Render compact status badges for one chart annotation card."""
    item = item or {}
    badges = []
    status = item.get("status")
    if status == "pending":
        badges.append(status_badge("LLM thinking", "info"))
    elif status == "success":
        badges.append(status_badge("Annotation ready", "success"))
    elif status == "error":
        badges.append(status_badge("Annotation failed", "danger"))

    if item.get("hypothesis_tag"):
        badges.append(status_badge(str(item.get("hypothesis_tag")), "primary"))
    return html.Div(badges, className="d-flex gap-2 flex-wrap")


def _build_annotation_result_panel(item: dict[str, Any] | None):
    """Render the right-side interpretation panel for one chart card."""
    item = item or {}
    status = item.get("status", "pending")

    children = [
        html.Div("Visualization Annotator", className="cp-chat__sender"),
        html.Div("Injected Data Summary", className="cp-scenario__section-label"),
        _build_annotation_metric_grid(item),
    ]

    raw_metrics_block = _build_scenario_raw_output(
        item.get("metrics"),
        summary_text="View injected chart summary",
    )

    if status == "pending":
        children[1:1] = [
            html.Div(
                "Reviewing the chart trend, current level, and hypothesis relevance before writing the annotation.",
                className="cp-scenario__reply-reasoning",
            ),
            html.Div(
                [
                    html.Span(className="cp-scenario__thinking-dot"),
                    html.Span(className="cp-scenario__thinking-dot"),
                    html.Span(className="cp-scenario__thinking-dot"),
                ],
                className="cp-scenario__thinking",
            ),
        ]
    elif status == "error":
        children[1:1] = [
            html.Div(
                str(item.get("error") or "Annotation failed."),
                className="cp-scenario__reply-error",
            ),
        ]
    else:
        children[1:1] = [
            html.Div(
                str(item.get("chart_title") or item.get("chart_label") or ""),
                className="cp-scenario__reply-summary",
            ),
            html.Div(
                str(item.get("caption") or ""),
                className="cp-scenario__reply-reasoning",
            ),
            html.Div(
                [
                    html.I(className="fas fa-lightbulb me-1"),
                    str(item.get("key_insight") or ""),
                ],
                className="cp-annotation__insight",
            ),
        ]

    if raw_metrics_block is not None:
        children.append(raw_metrics_block)

    meta_bits = []
    if item.get("model"):
        meta_bits.append(str(item.get("model")))
    if isinstance(item.get("elapsed"), (int, float)):
        meta_bits.append(f"{float(item['elapsed']):.1f}s")
    if meta_bits:
        children.append(html.Div(" · ".join(meta_bits), className="cp-scenario__message-meta"))

    return html.Div(children, className="cp-annotation__analysis")


def _build_annotation_card(item: dict[str, Any] | None):
    """Render one responsive chart-preview plus annotation-result card."""
    item = item or {}
    preview_panel = html.Div(
        [
            html.Div(
                str(item.get("chart_description") or ""),
                className="cp-scenario__reply-reasoning cp-llm-inspector__prose",
            ),
            html.Div(
                dcc.Graph(
                    figure=_build_annotation_preview_figure(item),
                    config={
                        "displayModeBar": False,
                        "displaylogo": False,
                        "responsive": True,
                        "staticPlot": True,
                    },
                    className="cp-annotation__graph",
                ),
                className="cp-annotation__preview-shell",
            ),
        ],
        className="cp-annotation__preview",
    )

    return card(
        title=str(item.get("chart_label") or "Chart"),
        subtitle=str(item.get("chart_subtitle") or ""),
        header_right=_build_annotation_status_badges(item),
        children=html.Div(
            [
                preview_panel,
                _build_annotation_result_panel(item),
            ],
            className="cp-annotation__body",
        ),
        class_name="cp-annotation__card",
    )


def _build_annotations_output(annotation_state: dict[str, Any] | None):
    """Render persisted annotation chart cards and their current interpretation status."""
    state = _normalize_annotation_state(annotation_state)
    status = state.get("status", "idle")
    items = state.get("items") or []

    if status == "idle":
        return card(
            title="Annotation Workspace",
            subtitle="Run a simulation and annotate the current chart set",
            children=[
                html.Div(ANNOTATION_WORKFLOW_NOTE, className="cp-scenario__reply-reasoning cp-llm-inspector__prose"),
                _scenario_placeholder(
                    "Click Annotate All Charts to preview the exact dashboard plots that will be interpreted here."
                ),
            ],
            class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
        )

    if status == "error" and not items:
        return card(
            title="Annotation Workspace",
            subtitle="Visualization Annotator",
            children=html.Div(
                state.get("error") or "Unable to annotate the current charts.",
                className="cp-scenario__reply-error",
            ),
            class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
        )

    summary_values = {
        "current_step": state.get("current_step"),
        "preset": str(state.get("preset", "custom")).replace("_", " ").title(),
        "chart_count": len(items),
        "model": state.get("model") or "—",
    }
    summary_badges = []
    if status == "pending":
        summary_badges.extend([
            status_badge(f"{len(items)} charts queued", "info"),
            status_badge("LLM thinking", "warning"),
        ])
    elif status == "error":
        summary_badges.extend([
            status_badge(f"{len(items)} charts processed", "warning"),
            status_badge("Some annotations failed", "danger"),
        ])
    else:
        summary_badges.extend([
            status_badge(f"{len(items)} charts annotated", "success"),
            status_badge("Prompt-grounded", "info"),
        ])

    return html.Div(
        [
            html.Div(summary_badges, className="d-flex gap-2 flex-wrap mb-3"),
            _build_chat_context_grid(
                summary_values,
                [
                    ("current_step", "Current Step"),
                    ("preset", "Preset"),
                    ("chart_count", "Charts"),
                    ("model", "Model"),
                ],
                accent_first=True,
            ),
            html.Div(
                str(state.get("note") or ANNOTATION_WORKFLOW_NOTE),
                className="cp-scenario__reply-reasoning cp-annotation__summary-note cp-llm-inspector__prose",
            ),
            html.Div(
                [_build_annotation_card(item) for item in items],
                className="cp-annotation__list",
            ),
        ]
    )


def _build_audit_io_payloads(
    call: dict[str, Any] | None,
    *,
    fallback_input: Any = None,
    fallback_output: Any = None,
) -> tuple[Any, Any]:
    """Extract raw input/output payloads from an audit recorder call when available."""
    input_payload = fallback_input
    output_payload = fallback_output

    if not isinstance(call, dict):
        return input_payload, output_payload

    call_input = {
        "system_prompt": call.get("system_prompt"),
        "user_prompt": call.get("user_prompt"),
        "messages": call.get("messages"),
        "think": call.get("think"),
    }
    call_input = {key: value for key, value in call_input.items() if value is not None}
    if call_input:
        input_payload = call_input

    call_output = {
        "raw_response": call.get("raw_response"),
        "parsed_output": call.get("parsed_output"),
        "schema_validation": call.get("schema_validation"),
    }
    call_output = {key: value for key, value in call_output.items() if value is not None}
    if call_output:
        output_payload = call_output

    return input_payload, output_payload


def _build_audit_log_table(log: list[dict[str, Any]] | None):
    """Render the session audit entries as a compact table with inspect actions."""
    entries = list(reversed(log or []))
    rows = []
    for index, entry in enumerate(entries):
        status_class = "cp-badge cp-badge--success" if entry.get("status") == "success" \
            else "cp-badge cp-badge--danger"
        rows.append(
            html.Tr([
                html.Td(entry.get("timestamp", ""),
                        style={"fontFamily": "var(--cp-font-mono)",
                               "fontSize": "var(--cp-text-xs)"}),
                html.Td(entry.get("role", ""),
                        style={"fontSize": "var(--cp-text-sm)",
                               "fontWeight": "var(--cp-weight-semibold)"}),
                html.Td(entry.get("call_kind", ""),
                        style={"fontSize": "var(--cp-text-xs)"}),
                html.Td(entry.get("model", ""),
                        style={"fontSize": "var(--cp-text-xs)",
                               "fontFamily": "var(--cp-font-mono)"}),
                html.Td(f"{entry.get('elapsed', 0):.1f}s",
                        style={"fontSize": "var(--cp-text-xs)",
                               "fontFamily": "var(--cp-font-mono)"}),
                html.Td(html.Span(
                    entry.get("status", ""),
                    className=status_class,
                )),
                html.Td(entry.get("prompt_preview", ""),
                        style={"fontSize": "var(--cp-text-xs)",
                               "maxWidth": "240px", "overflow": "hidden",
                               "textOverflow": "ellipsis", "whiteSpace": "nowrap"}),
                html.Td(
                    dbc.Button(
                        [html.I(className="fas fa-search-plus me-1"), "Inspect"],
                        id={"type": "audit-view-btn", "index": index},
                        className="cp-btn-outline",
                        size="sm",
                    ),
                    style={"whiteSpace": "nowrap"},
                ),
            ])
        )

    return dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th("Time"),
                html.Th("Role"),
                html.Th("Kind"),
                html.Th("Model"),
                html.Th("Time"),
                html.Th("Status"),
                html.Th("Prompt"),
                html.Th("Inspect"),
            ])),
            html.Tbody(rows),
        ],
        bordered=True, hover=True, responsive=True, size="sm",
        style={"fontSize": "var(--cp-text-sm)"},
    )


def _build_audit_detail(entry: dict[str, Any] | None):
    """Render the inspector panel for one selected audit log entry."""
    if not isinstance(entry, dict):
        return card(
            title="Interaction Details",
            subtitle="Select any audit row to inspect the original request and response",
            children=[
                html.Div(
                    AUDIT_LOG_DETAIL_NOTE,
                    className="cp-scenario__reply-reasoning cp-llm-inspector__prose",
                ),
                _scenario_placeholder(
                    "Click Inspect on any row to review the original input and the original output for that LLM interaction."
                ),
            ],
            class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
        )

    status = str(entry.get("status") or "unknown")
    status_variant = "success" if status == "success" else "danger"
    summary_values = {
        "role": entry.get("role") or "—",
        "kind": entry.get("call_kind") or "—",
        "model": entry.get("model") or "—",
        "timestamp": entry.get("timestamp") or "—",
        "elapsed": f"{float(entry.get('elapsed', 0.0)):.1f}s",
        "status": status.title(),
    }
    input_payload = entry.get("input_payload")
    output_payload = entry.get("output_payload")
    if output_payload is None and entry.get("error"):
        output_payload = {"error": entry.get("error")}

    input_block = _build_scenario_raw_output(
        input_payload,
        summary_text="View Original Input",
    )
    output_block = _build_scenario_raw_output(
        output_payload,
        summary_text="View Original Output",
    )

    children = [
        html.Div(
            [
                status_badge(entry.get("role", "LLM"), "primary"),
                status_badge(summary_values["status"], status_variant),
            ],
            className="d-flex gap-2 flex-wrap mb-3",
        ),
        _build_chat_context_grid(
            summary_values,
            [
                ("role", "Role"),
                ("kind", "Kind"),
                ("model", "Model"),
                ("timestamp", "Time"),
                ("elapsed", "Elapsed"),
                ("status", "Status"),
            ],
            accent_first=True,
        ),
        html.Div(
            AUDIT_LOG_DETAIL_NOTE,
            className="cp-scenario__reply-reasoning cp-annotation__summary-note cp-llm-inspector__prose",
        ),
        html.Div("Original Input", className="cp-scenario__section-label"),
    ]

    if input_block is not None:
        children.append(input_block)
    else:
        children.append(
            html.Div("No original input payload was captured for this entry.", className="cp-scenario__reply-reasoning")
        )

    children.append(html.Div("Original Output", className="cp-scenario__section-label"))
    if output_block is not None:
        children.append(output_block)
    else:
        children.append(
            html.Div("No original output payload was captured for this entry.", className="cp-scenario__reply-reasoning")
        )

    if entry.get("error"):
        children.append(
            html.Div(
                f"Captured error: {entry.get('error')}",
                className="cp-scenario__reply-error",
            )
        )

    return card(
        title="Interaction Details",
        subtitle=str(entry.get("prompt_preview") or entry.get("call_kind") or "LLM call"),
        children=children,
        class_name="cp-llm-workspace__card cp-llm-workspace__card--inspector",
    )


def _build_forum_groups_snapshot(
    sim_model: Any,
    forum_fraction: float,
    requested_agent_count: int,
    requested_group_count: int,
    num_turns: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Stage the forum groups up front so the UI can render them immediately."""
    from model.forums import plan_forum_groups, select_forum_groups_by_count

    plan = plan_forum_groups(
        len(list(sim_model.agents)),
        forum_fraction=forum_fraction,
        group_count=requested_group_count,
        participant_count=int(requested_agent_count or 0) or None,
    )
    selected_groups = select_forum_groups_by_count(
        sim_model,
        forum_fraction=forum_fraction,
        group_count=requested_group_count,
        participant_count=int(requested_agent_count or 0) or None,
    )
    groups = []
    agent_count = 0
    for index, group in enumerate(selected_groups):
        agent_ids = [agent.unique_id for agent in group]
        agent_count += len(agent_ids)
        groups.append({
            "id": f"group-{index + 1}",
            "index": index,
            "agent_ids": agent_ids,
            "status": "active" if index == 0 else "queued",
            "turns": [],
            "turn_cursor": 0,
            "total_turns": len(agent_ids) * int(num_turns or 0),
            "outcome": None,
            "delta_applied": 0.0,
            "preference_updates": [],
            "elapsed": 0.0,
            "error": None,
            "last_rerun_clicks": 0,
            "stop_note": None,
        })
    return groups, {
        "participant_count": agent_count,
        "requested_participant_count": int(plan.get("requested_participant_count") or requested_agent_count or 0),
        "actual_group_count": len(groups),
        "requested_group_count": int(plan.get("requested_group_count") or requested_group_count),
        "participant_source": str(plan.get("participant_source") or "fraction"),
        "group_sizes": list(plan.get("group_sizes") or []),
        "estimated_turns": agent_count * int(num_turns or 0),
        "estimated_llm_calls": (agent_count * int(num_turns or 0)) + len(groups) if groups else 0,
    }


def _forum_group_turns(turns: list[dict[str, Any]] | None):
    """Convert stored turn dicts back into DialogueTurn objects for role-5 helpers."""
    from model.forums import DialogueTurn

    output = []
    for turn in turns or []:
        if not isinstance(turn, dict):
            continue
        output.append(
            DialogueTurn(
                speaker_id=int(turn.get("speaker_id") or 0),
                speaker_label=str(turn.get("speaker_label") or "Resident"),
                content=str(turn.get("content") or ""),
            )
        )
    return output


def _finalize_forum_state(
    forum_data: dict[str, Any] | None,
    *,
    stopped: bool = False,
) -> dict[str, Any]:
    """Close a forum run after all groups have been processed."""
    import time

    state = _normalize_forum_state(forum_data)
    had_error = any(group.get("status") == "error" for group in state.get("groups", []))
    had_stopped = any(group.get("status") == "stopped" for group in state.get("groups", []))
    started_at = state.get("started_at")
    elapsed = None
    if isinstance(started_at, (int, float)):
        elapsed = round(max(0.0, time.perf_counter() - started_at), 2)

    final_status = "error" if had_error else "stopped" if stopped or had_stopped else "success"
    state.update({
        "status": final_status,
        "error": "One or more forum groups could not be completed." if had_error else None,
        "stop_requested": bool(stopped or had_stopped),
        "elapsed": elapsed,
        "generated_at": datetime.now().isoformat(),
    })
    return state


def _finalize_forum_error_state(
    forum_data: dict[str, Any] | None,
    error_message: str,
) -> dict[str, Any]:
    """Close a forum run with a specific terminal error message."""
    import time

    state = _normalize_forum_state(forum_data)
    started_at = state.get("started_at")
    elapsed = None
    if isinstance(started_at, (int, float)):
        elapsed = round(max(0.0, time.perf_counter() - started_at), 2)

    state.update({
        "status": "error",
        "error": error_message,
        "elapsed": elapsed,
        "generated_at": datetime.now().isoformat(),
    })
    return state


def _advance_to_next_queued_forum_group(
    groups: list[dict[str, Any]],
    *,
    after_index: int,
) -> int | None:
    """Activate the next queued group, if any, and return its index."""
    for next_index in range(after_index + 1, len(groups)):
        next_group = dict(groups[next_index])
        if next_group.get("status") != "queued":
            continue
        next_group["status"] = "active"
        groups[next_index] = next_group
        return next_index
    return None


def _record_forum_audit(state: dict[str, Any], model_name: str) -> None:
    """Capture one compact audit entry for a completed forum run."""
    _record_audit(
        "Role 5",
        "agent_forums",
        model_name,
        f"step={state.get('current_step')} · groups={len(state.get('groups', []))}",
        f"{len(state.get('groups', []))} groups",
        float(state.get("elapsed") or 0.0),
        state.get("error"),
        input_payload={
            "forum_fraction": state.get("forum_fraction"),
            "requested_agent_count": state.get("requested_agent_count"),
            "requested_group_count": state.get("requested_group_count"),
            "actual_group_count": state.get("group_count"),
            "participant_source": state.get("participant_source"),
            "group_sizes": state.get("group_sizes"),
            "num_turns": state.get("num_turns"),
            "estimated_llm_calls": state.get("estimated_llm_calls"),
            "current_step": state.get("current_step"),
            "model": model_name,
        },
        output_payload={
            "status": state.get("status"),
            "groups": state.get("groups"),
        },
    )


def _stop_forum_groups_gracefully(
    state: dict[str, Any],
    *,
    group_index: int,
    group_agents: list[Any],
    model_name: str,
) -> dict[str, Any]:
    """Stop the forum after the current in-flight step and preserve partial results."""
    from model.forums import apply_forum_outcome, extract_forum_outcome_from_turns

    groups = list(state.get("groups") or [])
    if group_index < len(groups):
        current_group = dict(groups[group_index])
        turns = _forum_group_turns(current_group.get("turns"))
        if turns:
            outcome = extract_forum_outcome_from_turns(
                turns,
                step=int(state.get("current_step") or 0),
                agent_ids=[int(agent.unique_id) for agent in group_agents],
                llm_model=model_name,
            )
            if outcome is not None:
                delta, preference_updates = apply_forum_outcome(group_agents, outcome)
                current_group.update({
                    "status": "stopped",
                    "outcome": outcome.model_dump(),
                    "delta_applied": round(delta, 4),
                    "preference_updates": preference_updates,
                    "error": None,
                    "stop_note": "Stopped after completing the current in-flight turn. Partial dialogue was summarized.",
                })
            else:
                current_group.update({
                    "status": "stopped",
                    "error": None,
                    "stop_note": "Stopped after the current in-flight turn. No reliable norm signal could be extracted from the partial dialogue.",
                })
        else:
            current_group.update({
                "status": "stopped",
                "error": None,
                "stop_note": "Stopped before this group produced any dialogue.",
            })
        groups[group_index] = current_group

    for queued_index, queued_group in enumerate(groups):
        if queued_index <= group_index:
            continue
        if queued_group.get("status") != "queued":
            continue
        next_group = dict(queued_group)
        next_group.update({
            "status": "stopped",
            "error": None,
            "stop_note": "Skipped because the forum was stopped before this group began.",
        })
        groups[queued_index] = next_group

    state["groups"] = groups
    state["note"] = (
        "Forum stop requested. The current in-flight turn was allowed to finish, then the workspace "
        "was finalized with the dialogue accumulated so far."
    )
    return _finalize_forum_state(state, stopped=True)


def _build_chat_thread(chat_state: dict[str, Any] | None):
    """Render the chat-style Result Interpreter transcript."""
    chat_state = chat_state or {}
    history = chat_state.get("history") or []
    if not history:
        return _scenario_placeholder(
            "Ask a question about your simulation results and the interpreter will ground the answer in the current experiment snapshot."
        )

    bubbles = []
    for message in history:
        if message.get("role") == "user":
            bubbles.append(
                html.Div([
                    html.Div("You", className="cp-chat__sender"),
                    html.Div(message.get("content", "")),
                ], className="cp-chat__message cp-chat__message--user")
            )
            continue

        meta = []
        if message.get("model"):
            meta.append(str(message.get("model")))
        if isinstance(message.get("elapsed"), (int, float)):
            meta.append(f"{message['elapsed']:.1f}s")

        body_children = [
            html.Div("Chat Interpreter", className="cp-chat__sender"),
            html.Div(
                message.get("content", ""),
                className="cp-scenario__reply-summary",
            ),
        ]

        if message.get("status") == "pending":
            body_children.extend([
                html.Div(
                    "Reviewing the latest simulation snapshot, recent metrics, and parameter settings before answering.",
                    className="cp-scenario__reply-reasoning",
                ),
                html.Div(
                    [
                        html.Span(className="cp-scenario__thinking-dot"),
                        html.Span(className="cp-scenario__thinking-dot"),
                        html.Span(className="cp-scenario__thinking-dot"),
                    ],
                    className="cp-scenario__thinking",
                ),
            ])
        elif message.get("status") == "error":
            body_children.append(
                html.Div(
                    message.get("error", "Interpreter failed."),
                    className="cp-scenario__reply-error",
                )
            )
        else:
            details = message.get("details", "")
            if details:
                body_children.append(
                    html.Div(details, className="cp-scenario__reply-reasoning")
                )

            summary_badges = []
            if message.get("hypothesis"):
                summary_badges.append(status_badge(str(message.get("hypothesis")), "primary"))
            if message.get("confidence"):
                summary_badges.append(status_badge("Caveat included", "warning"))
            if summary_badges:
                body_children.append(
                    html.Div(summary_badges, className="d-flex gap-2 flex-wrap mt-3")
                )
            if message.get("confidence"):
                body_children.append(
                    html.Div(
                        f"Caveat: {message.get('confidence')}",
                        className="cp-scenario__reply-reasoning",
                    )
                )

        if meta:
            body_children.append(
                html.Div(" · ".join(meta), className="cp-scenario__message-meta")
            )

        bubbles.append(
            html.Div(
                body_children,
                className="cp-chat__message cp-chat__message--ai cp-scenario__assistant-message",
            )
        )

    return html.Div(bubbles, className="cp-chat")


def _stage_chat_request(
    chat_data: dict[str, Any] | list[Any] | None,
    question: str,
    model_name: str,
    request_id: str,
    context_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Append the user turn and a pending assistant turn before interpretation returns."""
    state = _normalize_chat_state(chat_data)
    state.update({
        "status": "pending",
        "error": None,
        "elapsed": None,
        "model": model_name,
        "request_id": request_id,
        "context": context_snapshot,
        "raw_response": None,
    })
    state["history"].append({
        "id": f"{request_id}-user",
        "role": "user",
        "content": question,
    })
    state["history"].append({
        "id": f"{request_id}-assistant",
        "role": "assistant",
        "request_id": request_id,
        "status": "pending",
        "model": model_name,
        "content": "Preparing a grounded interpretation of your simulation results.",
    })
    return state


def _complete_chat_request(
    chat_data: dict[str, Any] | list[Any] | None,
    request_id: str,
    model_name: str,
    elapsed: float,
    *,
    result: dict[str, Any] | None = None,
    context_snapshot: dict[str, Any] | None = None,
    raw_response: Any = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Replace the pending Interpreter turn with the final assistant reply."""
    state = _normalize_chat_state(chat_data)
    is_success = error is None and result is not None

    for message in state["history"]:
        if message.get("role") == "assistant" and message.get("request_id") == request_id:
            message.update({
                "status": "success" if is_success else "error",
                "model": model_name,
                "elapsed": elapsed,
                "content": (result or {}).get("answer", "Interpretation ready.") if is_success else error,
                "details": (result or {}).get("detailed_explanation", "") if is_success else "",
                "hypothesis": (result or {}).get("hypothesis_connection", "") if is_success else "",
                "confidence": (result or {}).get("confidence_note", "") if is_success else "",
                "raw_response": raw_response,
                "error": error,
            })
            break

    state.update({
        "status": "success" if is_success else "error",
        "error": error,
        "elapsed": elapsed,
        "model": model_name,
        "request_id": request_id,
        "context": context_snapshot or state.get("context"),
        "raw_response": raw_response,
    })
    return state


# =========================================================================
# Layout helpers
# =========================================================================

def _model_config_panel() -> html.Div:
    """Collapsible panel for per-role LLM model selection."""
    rows = []
    for role_key, role_id, role_name, _ in ROLES:
        rows.append(
            dbc.Row([
                dbc.Col(
                    html.Span(
                        [html.Strong(role_id), f" — {role_name}"],
                        style={"fontSize": "var(--cp-text-sm)"},
                    ),
                    width=5, className="d-flex align-items-center",
                ),
                dbc.Col(
                    dcc.Dropdown(
                        id=f"{role_key}-model",
                        options=[],
                        placeholder="Click Refresh...",
                        clearable=False,
                        style={"fontSize": "var(--cp-text-sm)"},
                    ),
                    width=5,
                ),
                dbc.Col(
                    html.Span(
                        id=f"{role_key}-model-status",
                        className="cp-status-dot cp-status-dot--unknown",
                    ),
                    width=2,
                    className="d-flex align-items-center justify-content-center",
                ),
            ], className="mb-2 align-items-center")
        )

    rows.append(
        dbc.Row(
            dbc.Col(
                dbc.Button(
                    [html.I(className="fas fa-sync-alt me-1"), "Refresh Models"],
                    id="btn-refresh-models",
                    className="cp-btn-outline",
                    size="sm",
                ),
                width="auto", className="mt-2",
            ),
            justify="end",
        )
    )

    return html.Div([
        html.Div([
            html.Div([
                html.I(className="fas fa-cog me-2"),
                html.Span("Model Configuration",
                          style={"fontWeight": "var(--cp-weight-semibold)"}),
            ], className="d-flex align-items-center"),
            html.Div(id="model-config-summary", className="cp-model-summary"),
            dbc.Button(
                html.I(className="fas fa-chevron-down"),
                id="btn-toggle-model-config",
                className="cp-btn-outline ms-auto",
                size="sm", n_clicks=0,
            ),
        ], className="d-flex align-items-center gap-3 mb-3",
           style={"cursor": "pointer"}),
        dbc.Collapse(
            card(children=rows),
            id="model-config-collapse",
            is_open=False,
        ),
    ])


def _short_model_label(model_name: str | None, max_len: int = 18) -> str:
    """Return a compact model label suitable for the summary chips."""
    if not model_name:
        return "Unassigned"
    if len(model_name) <= max_len:
        return model_name
    return f"{model_name[:max_len - 1]}…"


def _model_status_from_class(class_name: str | None) -> str:
    """Map a status-dot className to its logical status."""
    if "cp-status-dot--online" in (class_name or ""):
        return "online"
    if "cp-status-dot--offline" in (class_name or ""):
        return "offline"
    return "unknown"


def _build_model_config_summary(
    role_values: dict[str, str] | None,
    role_statuses: dict[str, str] | None,
):
    """Build a compact status summary visible even when the config panel is collapsed."""
    role_values = role_values or {}
    role_statuses = role_statuses or {}

    if not role_values and not role_statuses:
        return status_badge("Detecting models...", "info")

    chips = []
    online_count = 0
    known_count = 0

    for role_key, role_id, _, _ in ROLES:
        status = _model_status_from_class(role_statuses.get(role_key))
        model_name = role_values.get(role_key, "")
        if status != "unknown" or model_name:
            known_count += 1
        if status == "online":
            online_count += 1

        chips.append(
            html.Div(
                [
                    llm_status_dot(status == "online" if status != "unknown" else None),
                    html.Span(role_id.replace("Role ", "R"), className="cp-model-summary__role"),
                    html.Span(_short_model_label(model_name), className="cp-model-summary__model"),
                ],
                className="cp-model-summary__chip",
            )
        )

    if known_count == 0:
        return status_badge("Detecting models...", "info")
    if online_count == 0:
        return status_badge("No local LLM model available", "neutral")
    return html.Div(chips, className="cp-model-summary__list")


def _llm_tab_label(role_marker: str, label: str) -> str:
    """Return a compact tab label that keeps role-to-tab mapping visible."""
    return f"{role_marker} · {label}"


def _tab_scenario() -> html.Div:
    """Role 1: Scenario Parser — NL description to model parameters."""
    return html.Div([
        _build_scenario_intro(),
        dbc.Row([
            dbc.Col([
                card(
                    title="Scenario Conversation",
                    subtitle="Send a free-text description, watch the parser think, then inspect the validated output.",
                    children=[
                        html.Div(id="scenario-thread", className="cp-scenario-thread"),
                        html.Div(
                            [
                                dbc.Textarea(
                                    id="scenario-input",
                                    placeholder=(
                                        "Describe daily life, service use, cost, peer pressure, workload, and "
                                        "population size when possible.\n\nExample: "
                                        + SCENARIO_DESCRIPTION_EXAMPLE
                                    ),
                                    style={"fontSize": "var(--cp-text-sm)"},
                                    className="cp-scenario__input",
                                    rows=3,
                                    n_submit=0,
                                    submit_on_enter=True,
                                    maxLength=500,
                                    persistence=True,
                                    persistence_type="memory",
                                ),
                                html.Div(
                                    [
                                        dbc.Button(
                                            [html.I(className="fas fa-wand-magic-sparkles me-1"), "Parse Scenario"],
                                            id="btn-parse-scenario",
                                            className="cp-btn-primary",
                                            size="sm",
                                        ),
                                        dbc.Button(
                                            [html.I(className="fas fa-trash-alt me-1"), "Clear Conversation"],
                                            id="btn-clear-scenario",
                                            className="cp-btn-outline",
                                            size="sm",
                                        ),
                                    ],
                                    className="cp-scenario__composer-actions",
                                ),
                                html.Div(
                                    "Press Enter to send. Use Shift+Enter for a new line. The parser reply appears as soon as validation finishes.",
                                    className="cp-scenario__composer-note",
                                ),
                            ],
                            className="cp-scenario-composer",
                        ),
                    ],
                    class_name="cp-llm-workspace__card cp-llm-workspace__card--conversation",
                ),
            ], xl=7, lg=12, className="cp-llm-workspace__col"),
            dbc.Col(
                html.Div(id="scenario-output", className="cp-llm-workspace__slot"),
                xl=5, lg=12, className="cp-llm-workspace__col",
            ),
        ], className="g-4 cp-llm-workspace"),
    ], className="p-3")


def _tab_chat() -> html.Div:
    """Role 3: Result Interpreter — chat interface for asking about simulation."""
    return html.Div([
        _build_chat_intro(),
        dbc.Row([
            dbc.Col([
                card(
                    title="Interpretation Conversation",
                    subtitle="Ask about the current simulation run, watch the interpreter reason over the live snapshot, then inspect the grounded answer.",
                    children=[
                        html.Div(id="chat-thread", className="cp-scenario-thread"),
                        html.Div(
                            [
                                dbc.Textarea(
                                    id="chat-input",
                                    placeholder="Ask about the current simulation (e.g., 'Why is stress rising even though delegation is high?')...",
                                    style={"fontSize": "var(--cp-text-sm)"},
                                    className="cp-scenario__input",
                                    rows=3,
                                    n_submit=0,
                                    submit_on_enter=True,
                                    persistence=True,
                                    persistence_type="memory",
                                ),
                                html.Div(
                                    [
                                        dbc.Button(
                                            [html.I(className="fas fa-paper-plane me-1"), "Ask Interpreter"],
                                            id="btn-chat-send",
                                            className="cp-btn-primary",
                                            size="sm",
                                        ),
                                        dbc.Button(
                                            [html.I(className="fas fa-trash-alt me-1"), "Clear Conversation"],
                                            id="btn-clear-chat",
                                            className="cp-btn-outline",
                                            size="sm",
                                        ),
                                    ],
                                    className="cp-scenario__composer-actions",
                                ),
                                html.Div(
                                    "Press Enter to send. Use Shift+Enter for a new line. Your question is sent together with the current simulation snapshot shown on the right.",
                                    className="cp-scenario__composer-note",
                                ),
                            ],
                            className="cp-scenario-composer",
                        ),
                    ],
                    class_name="cp-llm-workspace__card cp-llm-workspace__card--conversation",
                ),
            ], xl=7, lg=12, className="cp-llm-workspace__col"),
            dbc.Col(
                html.Div(id="chat-context-output", className="cp-llm-workspace__slot"),
                xl=5, lg=12, className="cp-llm-workspace__col",
            ),
        ], className="g-4 cp-llm-workspace"),
    ], className="p-3")


def _tab_profile() -> html.Div:
    """Role 2: Profile Generator — demographic description to agent attributes."""
    return html.Div([
        _build_profile_intro(),
        dbc.Row([
            dbc.Col([
                card(
                    title="Profile Conversation",
                    subtitle="Describe one simulation archetype, watch the generator think, then inspect the structured agent type.",
                    children=[
                        html.Div(id="profile-thread", className="cp-scenario-thread"),
                        html.Div(
                            [
                                dbc.Textarea(
                                    id="profile-input",
                                    placeholder=(
                                        "Describe one agent type, including daily routine, time pressure, comfort with services, "
                                        "and strengths or weaknesses across chores, paperwork, errands, or repairs.\n\nExample: "
                                        + PROFILE_DESCRIPTION_EXAMPLE
                                    ),
                                    style={"fontSize": "var(--cp-text-sm)"},
                                    className="cp-scenario__input",
                                    rows=3,
                                    n_submit=0,
                                    submit_on_enter=True,
                                    maxLength=500,
                                    persistence=True,
                                    persistence_type="memory",
                                ),
                                html.Div(
                                    [
                                        dbc.Button(
                                            [html.I(className="fas fa-user-gear me-1"), "Generate Profile"],
                                            id="btn-generate-profile",
                                            className="cp-btn-primary",
                                            size="sm",
                                        ),
                                        dbc.Button(
                                            [html.I(className="fas fa-trash-alt me-1"), "Clear Conversation"],
                                            id="btn-clear-profile",
                                            className="cp-btn-outline",
                                            size="sm",
                                        ),
                                    ],
                                    className="cp-scenario__composer-actions",
                                ),
                                html.Div(
                                    "Press Enter to send. Use Shift+Enter for a new line. The structured agent type appears in the inspector on the right.",
                                    className="cp-scenario__composer-note",
                                ),
                            ],
                            className="cp-scenario-composer",
                        ),
                    ],
                    class_name="cp-llm-workspace__card cp-llm-workspace__card--conversation",
                ),
            ], xl=7, lg=12, className="cp-llm-workspace__col"),
            dbc.Col(
                html.Div(id="profile-output", className="cp-llm-workspace__slot"),
                xl=5, lg=12, className="cp-llm-workspace__col",
            ),
        ], className="g-4 cp-llm-workspace"),
    ], className="p-3")


def _tab_annotations() -> html.Div:
    """Role 4: Visualization Annotator — auto-generate chart captions."""
    return html.Div([
        _build_annotations_intro(),
        html.Div([
            dbc.Button(
                [html.I(className="fas fa-pen-fancy me-1"), "Annotate All Charts"],
                id="btn-annotate-charts",
                className="cp-btn-primary",
                size="sm",
            ),
            dbc.Button(
                [html.I(className="fas fa-trash-alt me-1"), "Clear Annotations"],
                id="btn-clear-annotations",
                className="cp-btn-outline",
                size="sm",
            ),
        ], className="cp-scenario__composer-actions mb-3"),
        html.Div(id="annotations-output"),
    ], className="p-3")


def _tab_forums() -> html.Div:
    """Role 5: Agent Forums — experimental LLM-powered group discussions."""
    return html.Div([
        _build_forum_intro(),
        card(
            title="Forum Setup",
            subtitle="Configure the experimental group discussion before running Role 5",
            header_right=status_badge("Experimental Mode", "warning"),
            children=[
                dbc.Row([
                    dbc.Col([
                        html.Label("Forum Fraction", className="cp-controls__slider-label"),
                        dcc.Slider(
                            id="forum-fraction-slider",
                            min=0.05, max=0.5, step=0.05, value=0.20,
                            marks=None,
                            tooltip={"placement": "bottom"},
                        ),
                    ], xl=4, md=12),
                    dbc.Col([
                        html.Label("Exact Agent Count", className="cp-controls__slider-label"),
                        dbc.Input(
                            id="forum-agent-count-input",
                            type="number",
                            min=0,
                            step=1,
                            value=None,
                            placeholder="Optional override",
                            className="cp-forum__count-input",
                        ),
                        html.Div(
                            "Leave blank to derive participation from Forum Fraction.",
                            className="cp-scenario__composer-note",
                        ),
                    ], xl=2, md=6),
                    dbc.Col([
                        html.Label("Group Count", className="cp-controls__slider-label"),
                        dbc.RadioItems(
                            id="forum-group-count",
                            options=[{"label": str(i), "value": i} for i in [1, 2, 3, 4]],
                            value=2, inline=True,
                        ),
                    ], xl=3, md=6),
                    dbc.Col([
                        html.Label("Dialogue Turns", className="cp-controls__slider-label"),
                        dbc.RadioItems(
                            id="forum-num-turns",
                            options=[{"label": str(i), "value": i} for i in [1, 2, 3]],
                            value=2, inline=True,
                        ),
                    ], xl=3, md=6),
                ], className="g-3"),
                html.Div(id="forum-plan-summary", className="mt-3"),
                html.Div(
                    [
                        dbc.Button(
                            [html.I(className="fas fa-people-group me-1"), "Run Forum"],
                            id="btn-run-forum",
                            className="cp-btn-primary",
                            size="sm",
                        ),
                        dbc.Button(
                            [html.I(className="fas fa-stop-circle me-1"), "Stop Forum"],
                            id="btn-stop-forum",
                            className="cp-btn-outline",
                            size="sm",
                            disabled=True,
                        ),
                        dbc.Button(
                            [html.I(className="fas fa-trash-alt me-1"), "Clear Forums"],
                            id="btn-clear-forum",
                            className="cp-btn-outline",
                            size="sm",
                        ),
                    ],
                    className="cp-scenario__composer-actions mt-3",
                ),
                html.Div(
                    FORUM_WORKFLOW_NOTE,
                    className="cp-scenario__composer-note",
                ),
            ],
            class_name="cp-forum__setup-card",
        ),
        html.Div(id="forum-output", className="mt-3"),
    ], className="p-3")


def _tab_audit() -> html.Div:
    """Audit log viewer for all LLM interactions during this session."""
    return html.Div([
        _build_audit_intro(),
        html.Div([
            dbc.Button(
                [html.I(className="fas fa-sync-alt me-1"), "Refresh Log"],
                id="btn-refresh-audit",
                className="cp-btn-outline me-2",
                size="sm",
            ),
            dbc.Button(
                [html.I(className="fas fa-trash me-1"), "Clear Log"],
                id="btn-clear-audit",
                className="cp-btn-outline",
                size="sm",
            ),
        ], className="cp-scenario__composer-actions mb-3"),
        html.Div(id="audit-log-content"),
        html.Div(id="audit-log-detail", className="mt-3"),
    ], className="p-3")


def _tab_content() -> dbc.Tabs:
    """Horizontal tab bar for the 6 LLM role interfaces."""
    return dbc.Tabs([
        dbc.Tab(_tab_scenario(), label=_llm_tab_label("R1", "Scenario Parser"), tab_id="tab-scenario"),
        dbc.Tab(_tab_chat(), label=_llm_tab_label("R3", "Chat Interpreter"), tab_id="tab-chat"),
        dbc.Tab(_tab_profile(), label=_llm_tab_label("R2", "Profile Generator"), tab_id="tab-profile"),
        dbc.Tab(_tab_annotations(), label=_llm_tab_label("R4", "Annotations"), tab_id="tab-annotations"),
        dbc.Tab(_tab_forums(), label=_llm_tab_label("R5", "Agent Forums"), tab_id="tab-forums"),
        dbc.Tab(_tab_audit(), label=_llm_tab_label("ALL", "Audit Log"), tab_id="tab-audit"),
    ], id="llm-tabs", active_tab="tab-scenario", className="cp-tabs")


def layout() -> html.Div:
    """Build the LLM Studio page with a guaranteed remount trigger."""
    return html.Div([
        dcc.Interval(id="llm-studio-mount-interval", interval=50, n_intervals=0, max_intervals=1),
        # Polling interval for forum processing — disabled when no forum is pending.
        # Replaces the circular store-chaining pattern which stalled in Dash 4.x.
        dcc.Interval(id="forum-poll-interval", interval=500, n_intervals=0, disabled=True),
        dcc.Store(id="scenario-thread-scroll-store", data=0),
        dcc.Store(id="chat-thread-scroll-store", data=0),
        dcc.Store(id="profile-thread-scroll-store", data=0),
        html.Div([
            html.H2("LLM Studio", className="cp-page-title"),
            html.P(
                "AI-powered research assistant — 5 peripheral LLM roles for analysis and interpretation.",
                className="cp-page-subtitle",
            ),
        ], className="cp-page-header"),
        _model_config_panel(),
        html.Div(className="mb-4"),
        _tab_content(),
    ])


# =========================================================================
# Shared helper: record an LLM call to the session audit log
# =========================================================================

def _record_audit(role: str, call_kind: str, model: str,
                  prompt_preview: str, result: Any,
                  elapsed: float, error: str | None = None,
                  input_payload: Any = None,
                  output_payload: Any = None) -> None:
    """Add a lightweight audit entry to the session log."""
    app_state.append_audit_entry({
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "role": role,
        "call_kind": call_kind,
        "model": model,
        "prompt_preview": prompt_preview[:120],
        "result_preview": str(result)[:200] if result else "",
        "elapsed": round(elapsed, 2),
        "status": "error" if error else "success",
        "error": error,
        "input_payload": make_json_safe(input_payload) if input_payload is not None else None,
        "output_payload": make_json_safe(output_payload) if output_payload is not None else None,
    })


# =========================================================================
# Callback 1: Toggle model config panel
# =========================================================================

@callback(
    Output("model-config-collapse", "is_open"),
    Input("btn-toggle-model-config", "n_clicks"),
    State("model-config-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_model_config(n_clicks, is_open):
    return not is_open


# =========================================================================
# Callback 2: Refresh available models from Ollama
# =========================================================================

@callback(
    [Output(f"{rk}-model", "options") for rk, _, _, _ in ROLES]
    + [Output(f"{rk}-model", "value") for rk, _, _, _ in ROLES]
    + [Output(f"{rk}-model-status", "className") for rk, _, _, _ in ROLES],
    Input("llm-studio-mount-interval", "n_intervals"),
    Input("btn-refresh-models", "n_clicks"),
)
def refresh_models(page_state, n_clicks):
    """Query Ollama for available models and populate all role dropdowns."""
    try:
        import ollama as _ollama
        models_resp = _ollama.list()
        model_names = [m.model for m in models_resp.models]
    except Exception:
        model_names = []

    options = [{"label": m, "value": m} for m in model_names]
    if not options:
        options = [{"label": "(no models found)", "value": ""}]

    current = app_state.get_all_role_models()
    values = []
    statuses = []
    for rk, _, _, _ in ROLES:
        assigned = current.get(rk, "")
        if assigned in model_names:
            values.append(assigned)
            statuses.append("cp-status-dot cp-status-dot--online")
        elif model_names:
            values.append(model_names[0])
            app_state.set_role_model(rk, model_names[0])
            statuses.append("cp-status-dot cp-status-dot--online")
        else:
            values.append("")
            statuses.append("cp-status-dot cp-status-dot--offline")

    return [options] * 5 + values + statuses


# =========================================================================
# Callback 3: Model summary for collapsed header
# =========================================================================

@callback(
    Output("model-config-summary", "children"),
    [Input(f"{rk}-model", "value") for rk, _, _, _ in ROLES]
    + [Input(f"{rk}-model-status", "className") for rk, _, _, _ in ROLES],
)
def update_model_config_summary(*args):
    """Show current role-model assignments even when the panel is collapsed."""
    split = len(ROLES)
    values = args[:split]
    statuses = args[split:]
    role_values = {
        role_key: value or ""
        for (role_key, _, _, _), value in zip(ROLES, values, strict=False)
    }
    role_statuses = {
        role_key: status or ""
        for (role_key, _, _, _), status in zip(ROLES, statuses, strict=False)
    }
    return _build_model_config_summary(role_values, role_statuses)


# =========================================================================
# Callback 4: Save model selections to state
# =========================================================================

for _rk, _, _, _ in ROLES:
    @callback(
        Output(f"{_rk}-model-status", "className", allow_duplicate=True),
        Input(f"{_rk}-model", "value"),
        prevent_initial_call=True,
    )
    def _save_model_selection(value, role_key=_rk):
        if value:
            app_state.set_role_model(role_key, value)
            return "cp-status-dot cp-status-dot--online"
        return "cp-status-dot cp-status-dot--unknown"


# =========================================================================
# Callback 5: Restore LLM Studio tab on page remount
# =========================================================================

@callback(
    Output("llm-tabs", "active_tab"),
    Input("llm-studio-mount-interval", "n_intervals"),
    State("llm-studio-store", "data"),
)
def restore_llm_studio_tab(page_state, store_data):
    """Rehydrate the previously active tab after Dash Pages remounts the page."""
    state = _normalize_llm_studio_state(store_data)
    return state["active_tab"]


# =========================================================================
# Callback 6: Persist active LLM Studio tab
# =========================================================================

@callback(
    Output("llm-studio-store", "data"),
    Input("llm-tabs", "active_tab"),
    State("llm-studio-store", "data"),
    prevent_initial_call=True,
)
def persist_llm_studio_tab(active_tab, store_data):
    """Persist the current LLM Studio tab in the in-memory page store."""
    state = _normalize_llm_studio_state(store_data)
    state["active_tab"] = active_tab or state["active_tab"]
    return state


# =========================================================================
# Callback 7: Clear Scenario Parser conversation
# =========================================================================

@callback(
    Output("llm-studio-store", "data", allow_duplicate=True),
    Output("scenario-input", "value", allow_duplicate=True),
    Input("btn-clear-scenario", "n_clicks"),
    State("llm-studio-store", "data"),
    prevent_initial_call=True,
)
def clear_scenario_conversation(n_clicks, store_data):
    """Reset Scenario Parser history and inspector so the user can start over."""
    state = _normalize_llm_studio_state(store_data)
    current_clicks = int(n_clicks or 0)
    if current_clicks <= state["scenario"].get("last_clear_clicks", 0):
        return no_update, no_update

    reset_state = _default_scenario_state()
    reset_state["last_parse_clicks"] = state["scenario"].get("last_parse_clicks", 0)
    reset_state["last_submit_count"] = state["scenario"].get("last_submit_count", 0)
    reset_state["last_clear_clicks"] = current_clicks
    state["scenario"] = reset_state
    return state, ""


# =========================================================================
# Callback 8: Stage Scenario Parser request immediately
# =========================================================================

@callback(
    Output("llm-studio-store", "data", allow_duplicate=True),
    Output("scenario-parse-request-store", "data"),
    Output("scenario-input", "value"),
    Input("btn-parse-scenario", "n_clicks"),
    Input("scenario-input", "n_submit"),
    State("scenario-input", "value"),
    State("llm-studio-store", "data"),
    prevent_initial_call=True,
)
def stage_scenario_request(n_clicks, n_submit, description, store_data):
    """Append the user message and a pending assistant bubble before parsing starts."""
    if ctx.triggered_id not in {"btn-parse-scenario", "scenario-input"}:
        return no_update, no_update, no_update
    state = _normalize_llm_studio_state(store_data)
    scenario_state = state["scenario"]

    if ctx.triggered_id == "btn-parse-scenario":
        current_clicks = int(n_clicks or 0)
        if current_clicks <= scenario_state.get("last_parse_clicks", 0):
            return no_update, no_update, no_update
        scenario_state["last_parse_clicks"] = current_clicks
    else:
        current_submit = int(n_submit or 0)
        if current_submit <= scenario_state.get("last_submit_count", 0):
            return no_update, no_update, no_update
        scenario_state["last_submit_count"] = current_submit

    if not description or not description.strip():
        state["scenario"].update({
            "status": "empty",
            "error": "Please enter a scenario description.",
            "elapsed": None,
            "model": None,
            "result": None,
            "raw_response": None,
        })
        return state, no_update, no_update

    model_name = app_state.get_role_model("role_1")
    request_id = _make_request_id()
    next_state = _stage_scenario_request(state, description.strip(), model_name, request_id)
    request = {
        "request_id": request_id,
        "description": description.strip(),
        "model": model_name,
    }
    return next_state, request, ""


# =========================================================================
# Callback 9: Resolve Scenario Parser request
# =========================================================================

@callback(
    Output("llm-studio-store", "data", allow_duplicate=True),
    Output("scenario-parse-request-store", "data", allow_duplicate=True),
    Input("scenario-parse-request-store", "data"),
    State("llm-studio-store", "data"),
    prevent_initial_call=True,
    running=[
        (Output("btn-parse-scenario", "disabled"), True, False),
        (Output("btn-clear-scenario", "disabled"), True, False),
        (Output("scenario-input", "disabled"), True, False),
    ],
)
def resolve_scenario_request(request, store_data):
    """Perform the parse and replace the pending bubble with the final reply."""
    if not request:
        return no_update, no_update

    import time
    from api.llm_audit import LlmAuditRecorder
    from api.llm_service import parse_scenario

    request_id = request.get("request_id", _make_request_id())
    description = str(request.get("description") or "")
    model_name = str(request.get("model") or app_state.get_role_model("role_1"))
    t0 = time.perf_counter()
    recorder = LlmAuditRecorder(
        run_id=request_id,
        output_dir=Path("data/results/llm_logs"),
    )

    try:
        result = parse_scenario(description, model=model_name, recorder=recorder)
        elapsed = time.perf_counter() - t0
        role_calls = recorder.get_calls("role_1")
        role_call = role_calls[-1] if role_calls else None
        raw_response = role_call.get("raw_response") if role_call else None
        input_payload, output_payload = _build_audit_io_payloads(
            role_call,
            fallback_input={"description": description},
            fallback_output=result,
        )
        _record_audit(
            "Role 1",
            "scenario_parser",
            model_name,
            description,
            result,
            elapsed,
            input_payload=input_payload,
            output_payload=output_payload,
        )
        recorder.write_role_artifact(
            role="role_1",
            filename=f"{request_id}_scenario_parser_ui.json",
            payload={
                "source": "dash_llm_studio",
                "description": description,
                "result": result,
            },
        )
        return _complete_scenario_request(
            store_data,
            request_id,
            model_name,
            elapsed,
            result=result,
            raw_response=raw_response,
        ), None
    except Exception as e:
        elapsed = time.perf_counter() - t0
        role_calls = recorder.get_calls("role_1")
        role_call = role_calls[-1] if role_calls else None
        raw_response = role_call.get("raw_response") if role_call else None
        input_payload, output_payload = _build_audit_io_payloads(
            role_call,
            fallback_input={"description": description},
            fallback_output={"error": str(e)},
        )
        _record_audit(
            "Role 1",
            "scenario_parser",
            model_name,
            description,
            None,
            elapsed,
            str(e),
            input_payload=input_payload,
            output_payload=output_payload,
        )
        try:
            recorder.write_role_artifact(
                role="role_1",
                filename=f"{request_id}_scenario_parser_ui.json",
                payload={
                    "source": "dash_llm_studio",
                    "description": description,
                    "error": str(e),
                },
            )
        except Exception:
            logger.exception("Failed to persist Scenario Parser UI audit artifact.")
        return _complete_scenario_request(
            store_data,
            request_id,
            model_name,
            elapsed,
            raw_response=raw_response,
            error=f"Error: {e}",
        ), None


# =========================================================================
# Callback 10: Rehydrate Scenario Parser views on page remount
# =========================================================================

@callback(
    Output("scenario-thread", "children"),
    Output("scenario-output", "children"),
    Input("llm-studio-store", "data"),
    Input("llm-studio-mount-interval", "n_intervals"),
)
def render_scenario_views(store_data, page_state):
    """Render the transcript and structured inspector from in-memory UI state."""
    state = _normalize_llm_studio_state(store_data)
    return _build_scenario_thread(state["scenario"]), _build_scenario_output(state["scenario"])


# =========================================================================
# Callback 11: Auto-scroll Scenario Parser transcript
# =========================================================================

clientside_callback(
    """
    function(children, pageState) {
        const container = document.getElementById("scenario-thread");
        if (!container) {
            return window.dash_clientside.no_update;
        }

        window.requestAnimationFrame(() => {
            container.scrollTo({
                top: container.scrollHeight,
                behavior: "smooth",
            });
        });

        return Date.now();
    }
    """,
    Output("scenario-thread-scroll-store", "data"),
    Input("scenario-thread", "children"),
    Input("llm-studio-mount-interval", "n_intervals"),
    prevent_initial_call=True,
)


# =========================================================================
# Callback 12: Clear Chat Interpreter conversation
# =========================================================================

@callback(
    Output("chat-history-store", "data", allow_duplicate=True),
    Output("chat-input", "value", allow_duplicate=True),
    Input("btn-clear-chat", "n_clicks"),
    State("chat-history-store", "data"),
    prevent_initial_call=True,
)
def clear_chat_conversation(n_clicks, chat_data):
    """Reset the Result Interpreter transcript so the user can start over."""
    state = _normalize_chat_state(chat_data)
    current_clicks = int(n_clicks or 0)
    if current_clicks <= state.get("last_clear_clicks", 0):
        return no_update, no_update

    reset_state = _default_chat_state()
    reset_state["last_send_clicks"] = state.get("last_send_clicks", 0)
    reset_state["last_submit_count"] = state.get("last_submit_count", 0)
    reset_state["last_clear_clicks"] = current_clicks
    return reset_state, ""


# =========================================================================
# Callback 13: Stage Chat Interpreter request immediately
# =========================================================================

@callback(
    Output("chat-history-store", "data", allow_duplicate=True),
    Output("chat-interpret-request-store", "data"),
    Output("chat-input", "value"),
    Input("btn-chat-send", "n_clicks"),
    Input("chat-input", "n_submit"),
    State("chat-input", "value"),
    State("chat-history-store", "data"),
    prevent_initial_call=True,
)
def stage_chat_request(n_clicks, n_submit, question, chat_data):
    """Append the user message and a pending assistant bubble before interpretation starts."""
    if ctx.triggered_id not in {"btn-chat-send", "chat-input"}:
        return no_update, no_update, no_update
    state = _normalize_chat_state(chat_data)

    if ctx.triggered_id == "btn-chat-send":
        current_clicks = int(n_clicks or 0)
        if current_clicks <= state.get("last_send_clicks", 0):
            return no_update, no_update, no_update
        state["last_send_clicks"] = current_clicks
    else:
        current_submit = int(n_submit or 0)
        if current_submit <= state.get("last_submit_count", 0):
            return no_update, no_update, no_update
        state["last_submit_count"] = current_submit

    if not question or not question.strip():
        return no_update, no_update, no_update

    context_snapshot = _build_chat_context_snapshot()
    if not context_snapshot.get("initialized"):
        state.update({
            "status": "error",
            "error": str(context_snapshot.get("note") or "No simulation results are available."),
            "context": context_snapshot,
        })
        return state, no_update, no_update

    model_name = app_state.get_role_model("role_3")
    request_id = _make_request_id()
    next_state = _stage_chat_request(
        state,
        question.strip(),
        model_name,
        request_id,
        context_snapshot,
    )
    request = {
        "request_id": request_id,
        "question": question.strip(),
        "model": model_name,
        "context": context_snapshot,
    }
    return next_state, request, ""


# =========================================================================
# Callback 14: Resolve Chat Interpreter request
# =========================================================================

@callback(
    Output("chat-history-store", "data", allow_duplicate=True),
    Output("chat-interpret-request-store", "data", allow_duplicate=True),
    Input("chat-interpret-request-store", "data"),
    State("chat-history-store", "data"),
    prevent_initial_call=True,
    running=[
        (Output("btn-chat-send", "disabled"), True, False),
        (Output("btn-clear-chat", "disabled"), True, False),
        (Output("chat-input", "disabled"), True, False),
    ],
)
def resolve_chat_request(request, chat_data):
    """Perform the interpretation and replace the pending bubble with the final reply."""
    if not request:
        return no_update, no_update

    import time
    from api.llm_audit import LlmAuditRecorder
    from api.llm_service import interpret_results

    request_id = request.get("request_id", _make_request_id())
    question = str(request.get("question") or "")
    model_name = str(request.get("model") or app_state.get_role_model("role_3"))
    context_snapshot = request.get("context") if isinstance(request.get("context"), dict) else _build_chat_context_snapshot()

    state = _normalize_chat_state(chat_data)
    history_for_llm = [
        {"role": msg.get("role", "user"), "content": str(msg.get("content", ""))}
        for msg in state["history"]
        if msg.get("role") in {"user", "assistant"} and msg.get("status") != "pending"
    ]

    t0 = time.perf_counter()
    recorder = LlmAuditRecorder(
        run_id=request_id,
        output_dir=Path("data/results/llm_logs"),
    )

    try:
        result = interpret_results(
            question,
            context_snapshot,
            history=history_for_llm,
            model=model_name,
            recorder=recorder,
        )
        elapsed = time.perf_counter() - t0
        role_calls = recorder.get_calls("role_3")
        role_call = role_calls[-1] if role_calls else None
        raw_response = role_call.get("raw_response") if role_call else None
        input_payload, output_payload = _build_audit_io_payloads(
            role_call,
            fallback_input={
                "question": question,
                "context": context_snapshot,
                "history": history_for_llm,
            },
            fallback_output=result,
        )
        _record_audit(
            "Role 3",
            "result_interpreter",
            model_name,
            question,
            result,
            elapsed,
            input_payload=input_payload,
            output_payload=output_payload,
        )
        recorder.write_role_artifact(
            role="role_3",
            filename=f"{request_id}_result_interpreter_ui.json",
            payload={
                "source": "dash_llm_studio",
                "question": question,
                "context": context_snapshot,
                "result": result,
            },
        )
        return _complete_chat_request(
            chat_data,
            request_id,
            model_name,
            elapsed,
            result=result,
            context_snapshot=context_snapshot,
            raw_response=raw_response,
        ), None
    except Exception as e:
        elapsed = time.perf_counter() - t0
        role_calls = recorder.get_calls("role_3")
        role_call = role_calls[-1] if role_calls else None
        raw_response = role_call.get("raw_response") if role_call else None
        input_payload, output_payload = _build_audit_io_payloads(
            role_call,
            fallback_input={
                "question": question,
                "context": context_snapshot,
                "history": history_for_llm,
            },
            fallback_output={"error": str(e)},
        )
        _record_audit(
            "Role 3",
            "result_interpreter",
            model_name,
            question,
            None,
            elapsed,
            str(e),
            input_payload=input_payload,
            output_payload=output_payload,
        )
        try:
            recorder.write_role_artifact(
                role="role_3",
                filename=f"{request_id}_result_interpreter_ui.json",
                payload={
                    "source": "dash_llm_studio",
                    "question": question,
                    "context": context_snapshot,
                    "error": str(e),
                },
            )
        except Exception:
            logger.exception("Failed to persist Result Interpreter UI audit artifact.")
        return _complete_chat_request(
            chat_data,
            request_id,
            model_name,
            elapsed,
            context_snapshot=context_snapshot,
            raw_response=raw_response,
            error=f"Error: {e}",
        ), None


# =========================================================================
# Callback 15: Rehydrate Chat Interpreter views on page remount
# =========================================================================

@callback(
    Output("chat-thread", "children"),
    Output("chat-context-output", "children"),
    Input("chat-history-store", "data"),
    Input("llm-studio-mount-interval", "n_intervals"),
)
def render_chat_views(chat_data, page_state):
    """Render the interpreter transcript and the current simulation context."""
    state = _normalize_chat_state(chat_data)
    return _build_chat_thread(state), _build_chat_context_panel(state)


# =========================================================================
# Callback 16: Auto-scroll Chat Interpreter transcript
# =========================================================================

clientside_callback(
    """
    function(children, pageState) {
        const container = document.getElementById("chat-thread");
        if (!container) {
            return window.dash_clientside.no_update;
        }

        window.requestAnimationFrame(() => {
            container.scrollTo({
                top: container.scrollHeight,
                behavior: "smooth",
            });
        });

        return Date.now();
    }
    """,
    Output("chat-thread-scroll-store", "data"),
    Input("chat-thread", "children"),
    Input("llm-studio-mount-interval", "n_intervals"),
    prevent_initial_call=True,
)


# =========================================================================
# Callback 17: Clear Profile Generator conversation
# =========================================================================

@callback(
    Output("profile-history-store", "data", allow_duplicate=True),
    Output("profile-input", "value", allow_duplicate=True),
    Input("btn-clear-profile", "n_clicks"),
    State("profile-history-store", "data"),
    prevent_initial_call=True,
)
def clear_profile_conversation(n_clicks, profile_data):
    """Reset the Profile Generator transcript so the user can start over."""
    state = _normalize_profile_state(profile_data)
    current_clicks = int(n_clicks or 0)
    if current_clicks <= state.get("last_clear_clicks", 0):
        return no_update, no_update

    reset_state = _default_profile_state()
    reset_state["last_generate_clicks"] = state.get("last_generate_clicks", 0)
    reset_state["last_submit_count"] = state.get("last_submit_count", 0)
    reset_state["last_clear_clicks"] = current_clicks
    return reset_state, ""


# =========================================================================
# Callback 18: Load a suggested Profile Generator prompt
# =========================================================================

@callback(
    Output("profile-input", "value", allow_duplicate=True),
    [Input(button_id, "n_clicks") for button_id, _, _ in PROFILE_SUGGESTED_PROMPTS],
    prevent_initial_call=True,
)
def load_profile_prompt(*_clicks):
    """Populate the profile textarea from one of the suggested quick-start prompts."""
    prompt_text = _profile_prompt_text(ctx.triggered_id)
    if prompt_text is None:
        return no_update
    return prompt_text


# =========================================================================
# Callback 19: Stage Profile Generator request immediately
# =========================================================================

@callback(
    Output("profile-history-store", "data", allow_duplicate=True),
    Output("profile-generate-request-store", "data"),
    Output("profile-input", "value"),
    Input("btn-generate-profile", "n_clicks"),
    Input("profile-input", "n_submit"),
    State("profile-input", "value"),
    State("profile-history-store", "data"),
    prevent_initial_call=True,
)
def stage_profile_request(n_clicks, n_submit, description, profile_data):
    """Append the user message and a pending assistant bubble before generation starts."""
    if ctx.triggered_id not in {"btn-generate-profile", "profile-input"}:
        return no_update, no_update, no_update
    state = _normalize_profile_state(profile_data)

    if ctx.triggered_id == "btn-generate-profile":
        current_clicks = int(n_clicks or 0)
        if current_clicks <= state.get("last_generate_clicks", 0):
            return no_update, no_update, no_update
        state["last_generate_clicks"] = current_clicks
    else:
        current_submit = int(n_submit or 0)
        if current_submit <= state.get("last_submit_count", 0):
            return no_update, no_update, no_update
        state["last_submit_count"] = current_submit

    if not description or not description.strip():
        state.update({
            "status": "empty",
            "error": "Please enter an agent type description.",
            "elapsed": None,
            "model": None,
            "result": None,
            "raw_response": None,
        })
        return state, no_update, no_update

    model_name = app_state.get_role_model("role_2")
    request_id = _make_request_id()
    next_state = _stage_profile_request(state, description.strip(), model_name, request_id)
    request = {
        "request_id": request_id,
        "description": description.strip(),
        "model": model_name,
    }
    return next_state, request, ""


# =========================================================================
# Callback 20: Resolve Profile Generator request
# =========================================================================

@callback(
    Output("profile-history-store", "data", allow_duplicate=True),
    Output("profile-generate-request-store", "data", allow_duplicate=True),
    Input("profile-generate-request-store", "data"),
    State("profile-history-store", "data"),
    prevent_initial_call=True,
    running=[
        (Output("btn-generate-profile", "disabled"), True, False),
        (Output("btn-clear-profile", "disabled"), True, False),
        (Output("profile-input", "disabled"), True, False),
        (Output("btn-profile-prompt-busy", "disabled"), True, False),
        (Output("btn-profile-prompt-self-serve", "disabled"), True, False),
        (Output("btn-profile-prompt-coordinator", "disabled"), True, False),
    ],
)
def resolve_profile_request(request, profile_data):
    """Perform the generation and replace the pending bubble with the final reply."""
    if not request:
        return no_update, no_update

    import time
    from api.llm_audit import LlmAuditRecorder
    from api.llm_service import generate_agent_profile

    request_id = request.get("request_id", _make_request_id())
    description = str(request.get("description") or "")
    model_name = str(request.get("model") or app_state.get_role_model("role_2"))
    t0 = time.perf_counter()
    recorder = LlmAuditRecorder(
        run_id=request_id,
        output_dir=Path("data/results/llm_logs"),
    )

    try:
        result = generate_agent_profile(description, model=model_name, recorder=recorder)
        elapsed = time.perf_counter() - t0
        role_calls = recorder.get_calls("role_2")
        role_call = role_calls[-1] if role_calls else None
        raw_response = role_call.get("raw_response") if role_call else None
        input_payload, output_payload = _build_audit_io_payloads(
            role_call,
            fallback_input={"description": description},
            fallback_output=result,
        )
        _record_audit(
            "Role 2",
            "profile_generator",
            model_name,
            description,
            result,
            elapsed,
            input_payload=input_payload,
            output_payload=output_payload,
        )
        recorder.write_role_artifact(
            role="role_2",
            filename=f"{request_id}_profile_generator_ui.json",
            payload={
                "source": "dash_llm_studio",
                "description": description,
                "result": result,
            },
        )
        return _complete_profile_request(
            profile_data,
            request_id,
            model_name,
            elapsed,
            result=result,
            raw_response=raw_response,
        ), None
    except Exception as e:
        elapsed = time.perf_counter() - t0
        role_calls = recorder.get_calls("role_2")
        role_call = role_calls[-1] if role_calls else None
        raw_response = role_call.get("raw_response") if role_call else None
        input_payload, output_payload = _build_audit_io_payloads(
            role_call,
            fallback_input={"description": description},
            fallback_output={"error": str(e)},
        )
        _record_audit(
            "Role 2",
            "profile_generator",
            model_name,
            description,
            None,
            elapsed,
            str(e),
            input_payload=input_payload,
            output_payload=output_payload,
        )
        try:
            recorder.write_role_artifact(
                role="role_2",
                filename=f"{request_id}_profile_generator_ui.json",
                payload={
                    "source": "dash_llm_studio",
                    "description": description,
                    "error": str(e),
                },
            )
        except Exception:
            logger.exception("Failed to persist Profile Generator UI audit artifact.")
        return _complete_profile_request(
            profile_data,
            request_id,
            model_name,
            elapsed,
            raw_response=raw_response,
            error=f"Error: {e}",
        ), None


# =========================================================================
# Callback 21: Rehydrate Profile Generator views on page remount
# =========================================================================

@callback(
    Output("profile-thread", "children"),
    Output("profile-output", "children"),
    Input("profile-history-store", "data"),
    Input("llm-studio-mount-interval", "n_intervals"),
)
def render_profile_views(profile_data, page_state):
    """Render the profile transcript and structured agent-type inspector."""
    state = _normalize_profile_state(profile_data)
    return _build_profile_thread(state), _build_profile_output(state)


# =========================================================================
# Callback 22: Auto-scroll Profile Generator transcript
# =========================================================================

clientside_callback(
    """
    function(children, pageState) {
        const container = document.getElementById("profile-thread");
        if (!container) {
            return window.dash_clientside.no_update;
        }

        window.requestAnimationFrame(() => {
            container.scrollTo({
                top: container.scrollHeight,
                behavior: "smooth",
            });
        });

        return Date.now();
    }
    """,
    Output("profile-thread-scroll-store", "data"),
    Input("profile-thread", "children"),
    Input("llm-studio-mount-interval", "n_intervals"),
    prevent_initial_call=True,
)


# =========================================================================
# Callback 7: Annotations (Role 4)
# =========================================================================

@callback(
    Output("annotation-history-store", "data", allow_duplicate=True),
    Output("annotation-annotate-request-store", "data"),
    Input("btn-annotate-charts", "n_clicks"),
    State("annotation-history-store", "data"),
    prevent_initial_call=True,
    running=[
        (Output("btn-annotate-charts", "disabled"), True, False),
        (Output("btn-clear-annotations", "disabled"), True, False),
    ],
)
def annotate_charts_cb(n_clicks, annotation_data):
    """Stage chart previews and pending statuses before Role 4 returns."""
    state = _normalize_annotation_state(annotation_data)
    if state.get("status") == "pending":
        return no_update, no_update

    current_clicks = int(n_clicks or 0)
    if current_clicks <= state.get("last_annotate_clicks", 0):
        return no_update, no_update

    state["last_annotate_clicks"] = current_clicks
    snapshot = _build_annotation_snapshot()
    if not snapshot.get("initialized"):
        state.update({
            "status": "error",
            "error": str(snapshot.get("note") or "Initialize and run a simulation first."),
            "note": str(snapshot.get("note") or ANNOTATION_WORKFLOW_NOTE),
            "current_step": int(snapshot.get("current_step") or 0),
            "preset": str(snapshot.get("preset") or "custom"),
            "model": snapshot.get("model"),
            "items": [],
        })
        return state, None

    state.update({
        "status": "pending",
        "error": None,
        "note": str(snapshot.get("note") or ANNOTATION_WORKFLOW_NOTE),
        "current_step": int(snapshot.get("current_step") or 0),
        "preset": str(snapshot.get("preset") or "custom"),
        "model": snapshot.get("model"),
        "request_id": _make_request_id(),
        "items": snapshot.get("items", []),
        "generated_at": None,
    })
    request = {
        "request_id": state.get("request_id"),
        "model": snapshot.get("model"),
        "preset": snapshot.get("preset"),
        "items": [
            {
                "chart_key": item.get("chart_key"),
                "chart_label": item.get("chart_label"),
                "metrics": item.get("metrics"),
            }
            for item in snapshot.get("items", [])
        ],
    }
    return state, request


@callback(
    Output("annotation-history-store", "data", allow_duplicate=True),
    Output("annotation-annotate-request-store", "data", allow_duplicate=True),
    Input("annotation-annotate-request-store", "data"),
    State("annotation-history-store", "data"),
    prevent_initial_call=True,
    running=[
        (Output("btn-annotate-charts", "disabled"), True, False),
    ],
)
def resolve_annotation_request(request, annotation_data):
    """Run Role 4 on each staged chart and fill in the final annotations."""
    if not request:
        return no_update, no_update

    import time
    from api.llm_service import annotate_visualization

    state = _normalize_annotation_state(annotation_data)
    request_id = request.get("request_id")
    # Ignore stale work once the active annotation session has been cleared
    # or superseded by a newer request.
    if request_id != state.get("request_id"):
        return no_update, no_update

    model_name = request.get("model") or state.get("model") or app_state.get_role_model("role_4")
    preset = request.get("preset")
    results_by_key = {}

    for queued_item in request.get("items", []):
        chart_key = str(queued_item.get("chart_key") or "")
        chart_label = str(queued_item.get("chart_label") or chart_key or "Chart")
        metrics = queued_item.get("metrics") or {}
        t0 = time.perf_counter()
        try:
            result = annotate_visualization(
                chart_label,
                metrics,
                preset=preset,
                model=model_name,
            )
            elapsed = time.perf_counter() - t0
            _record_audit(
                "Role 4",
                "visualization_annotator",
                model_name,
                chart_label,
                result,
                elapsed,
                input_payload={
                    "chart_label": chart_label,
                    "preset": preset,
                    "metrics": metrics,
                },
                output_payload=result,
            )
            results_by_key[chart_key] = {
                "status": "success",
                "chart_title": result.get("chart_title", chart_label),
                "hypothesis_tag": result.get("hypothesis_tag", ""),
                "caption": result.get("caption", ""),
                "key_insight": result.get("key_insight", ""),
                "elapsed": elapsed,
                "model": model_name,
                "error": None,
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            _record_audit(
                "Role 4",
                "visualization_annotator",
                model_name,
                chart_label,
                None,
                elapsed,
                str(e),
                input_payload={
                    "chart_label": chart_label,
                    "preset": preset,
                    "metrics": metrics,
                },
                output_payload={"error": str(e)},
            )
            results_by_key[chart_key] = {
                "status": "error",
                "elapsed": elapsed,
                "model": model_name,
                "error": f"Error: {e}",
            }

    updated_items = []
    had_error = False
    for item in state.get("items", []):
        chart_key = str(item.get("chart_key") or "")
        result_payload = results_by_key.get(chart_key, {})
        item_state = dict(item)
        item_state.update(result_payload)
        if item_state.get("status") == "error":
            had_error = True
        updated_items.append(item_state)

    state.update({
        "status": "success" if not had_error else "error",
        "error": None if not had_error else "One or more charts could not be annotated.",
        "items": updated_items,
        "generated_at": datetime.now().isoformat(),
    })
    return state, None


@callback(
    Output("annotation-history-store", "data", allow_duplicate=True),
    Output("annotation-annotate-request-store", "data", allow_duplicate=True),
    Input("btn-clear-annotations", "n_clicks"),
    State("annotation-history-store", "data"),
    prevent_initial_call=True,
)
def clear_annotations_cb(n_clicks, annotation_data):
    """Clear persisted annotation cards so the user can start fresh."""
    state = _normalize_annotation_state(annotation_data)
    current_clicks = int(n_clicks or 0)
    if current_clicks <= state.get("last_clear_clicks", 0):
        return no_update, no_update

    reset_state = _default_annotation_state()
    reset_state["last_annotate_clicks"] = state.get("last_annotate_clicks", 0)
    reset_state["last_clear_clicks"] = current_clicks
    return reset_state, None


@callback(
    Output("annotations-output", "children"),
    Input("annotation-history-store", "data"),
    Input("llm-studio-mount-interval", "n_intervals"),
)
def render_annotations_output(annotation_data, page_state):
    """Rebuild annotation cards from in-memory state after page remounts."""
    return _build_annotations_output(annotation_data)


# =========================================================================
# Callback 8: Agent Forums (Role 5)
# =========================================================================

@callback(
    Output("btn-run-forum", "disabled"),
    Output("btn-stop-forum", "disabled"),
    Output("btn-clear-forum", "disabled"),
    Output("forum-fraction-slider", "disabled"),
    Output("forum-agent-count-input", "disabled"),
    Output("forum-group-count", "disabled"),
    Output("forum-num-turns", "disabled"),
    Output("forum-poll-interval", "disabled"),
    Input("forum-run-request-store", "data"),
    Input("forum-history-store", "data"),
    Input("forum-control-store", "data"),
    Input("llm-studio-mount-interval", "n_intervals"),
)
def sync_forum_controls(request, forum_data, forum_control, page_state):
    """Keep forum controls aligned with the current incremental run state."""
    state = _normalize_forum_state(forum_data)
    control_state = _normalize_forum_control_state(forum_control)
    is_pending = bool(request) and state.get("status") == "pending"
    return (
        is_pending,
        not is_pending or bool(control_state.get("stop_requested")),
        is_pending,
        is_pending,
        is_pending,
        is_pending,
        is_pending,
        not is_pending,  # forum-poll-interval: disabled when NOT pending
    )


@callback(
    Output("forum-plan-summary", "children"),
    Input("forum-fraction-slider", "value"),
    Input("forum-agent-count-input", "value"),
    Input("forum-group-count", "value"),
    Input("forum-num-turns", "value"),
    Input("sim-trigger-store", "data"),
    Input("llm-studio-mount-interval", "n_intervals"),
)
def render_forum_plan_summary(fraction, agent_count, group_count, num_turns, sim_trigger, page_state):
    """Show the live forum scale preview before a run begins."""
    return _build_forum_scale_summary(
        float(fraction or 0.20),
        int(agent_count or 0),
        int(group_count or 2),
        int(num_turns or 2),
    )


@callback(
    Output("forum-history-store", "data", allow_duplicate=True),
    Output("forum-run-request-store", "data"),
    Output("forum-control-store", "data"),
    Input("btn-run-forum", "n_clicks"),
    State("forum-fraction-slider", "value"),
    State("forum-agent-count-input", "value"),
    State("forum-group-count", "value"),
    State("forum-num-turns", "value"),
    State("forum-history-store", "data"),
    State("forum-control-store", "data"),
    prevent_initial_call=True,
)
def stage_forum_request(n_clicks, fraction, agent_count, group_count, num_turns, forum_data, forum_control):
    """Stage all forum groups immediately so the UI can render before LLM calls finish."""
    import time

    state = _normalize_forum_state(forum_data)
    if state.get("status") == "pending":
        return no_update, no_update, no_update

    current_clicks = int(n_clicks or 0)
    if current_clicks <= state.get("last_run_clicks", 0):
        return no_update, no_update, no_update

    sim_model = app_state.get_model()
    if sim_model is None:
        state.update({
            "status": "error",
            "error": "Initialize a simulation first.",
            "last_run_clicks": current_clicks,
        })
        return state, None, _default_forum_control_state()

    forum_fraction = float(fraction or 0.20)
    requested_agent_count = int(agent_count or 0)
    requested_group_count = int(group_count or 2)
    forum_turns = int(num_turns or 2)
    groups, plan = _build_forum_groups_snapshot(
        sim_model,
        forum_fraction,
        requested_agent_count,
        requested_group_count,
        forum_turns,
    )

    if not groups:
        state.update({
            "status": "error",
            "error": "Not enough agents are available to form a forum group. Increase the population or adjust the forum settings.",
            "forum_fraction": forum_fraction,
            "requested_agent_count": requested_agent_count,
            "requested_group_count": requested_group_count,
            "num_turns": forum_turns,
            "last_run_clicks": current_clicks,
        })
        return state, None, _default_forum_control_state()

    request_id = _make_request_id()
    model_name = app_state.get_role_model("role_5")
    state.update({
        "status": "pending",
        "error": None,
        "note": FORUM_WORKFLOW_NOTE,
        "model": model_name,
        "model_instance_id": id(sim_model),
        "request_id": request_id,
        "current_step": sim_model.current_step,
        "forum_fraction": forum_fraction,
        "requested_agent_count": requested_agent_count,
        "requested_group_count": requested_group_count,
        "participant_source": plan.get("participant_source"),
        "num_turns": forum_turns,
        "agent_count": plan.get("participant_count"),
        "group_count": plan.get("actual_group_count"),
        "group_sizes": plan.get("group_sizes"),
        "estimated_turns": plan.get("estimated_turns"),
        "estimated_llm_calls": plan.get("estimated_llm_calls"),
        "stop_requested": False,
        "elapsed": None,
        "generated_at": None,
        "started_at": time.perf_counter(),
        "groups": groups,
        "last_run_clicks": current_clicks,
    })
    # Publish to server-side state so interval-driven processing reads
    # the authoritative copy instead of stale client-side State values.
    global _forum_server_state, _forum_stop_requested
    _forum_server_state = dict(state)
    _forum_stop_requested = False

    request = {
        "request_id": request_id,
        "group_index": 0,
        "model": model_name,
        "sequence": 0,
    }
    control_state = _normalize_forum_control_state(forum_control)
    control_state.update({
        "request_id": request_id,
        "stop_requested": False,
    })
    return state, request, control_state


@callback(
    Output("forum-history-store", "data", allow_duplicate=True),
    Output("forum-run-request-store", "data", allow_duplicate=True),
    Output("forum-control-store", "data", allow_duplicate=True),
    Input({"type": "forum-rerun-btn", "index": ALL}, "n_clicks"),
    State("forum-history-store", "data"),
    State("forum-control-store", "data"),
    prevent_initial_call=True,
)
def rerun_forum_group(_clicks, forum_data, forum_control):
    """Stage a rerun for a single completed/failed forum group."""
    import time

    if not isinstance(ctx.triggered_id, dict):
        return no_update, no_update, no_update

    state = _normalize_forum_state(forum_data)
    if state.get("status") == "pending":
        return no_update, no_update, no_update

    triggered_index = ctx.triggered_id.get("index")
    if triggered_index is None:
        return no_update, no_update, no_update
    try:
        group_index = int(triggered_index)
    except (TypeError, ValueError):
        return no_update, no_update, no_update
    groups = list(state.get("groups") or [])
    if group_index < 0 or group_index >= len(groups):
        return no_update, no_update, no_update

    sim_model = app_state.get_model()
    if sim_model is None:
        state.update({
            "status": "error",
            "error": "The active simulation is no longer available. Re-initialize the model before rerunning this group.",
        })
        return state, None, _default_forum_control_state()

    current_clicks = int((ctx.triggered or [{}])[0].get("value") or 0)
    group_state = dict(groups[group_index])
    if current_clicks <= int(group_state.get("last_rerun_clicks") or 0):
        return no_update, no_update, no_update

    group_state.update({
        "status": "active",
        "turns": [],
        "turn_cursor": 0,
        "total_turns": len(group_state.get("agent_ids") or []) * int(state.get("num_turns") or 0),
        "outcome": None,
        "delta_applied": 0.0,
        "preference_updates": [],
        "elapsed": 0.0,
        "error": None,
        "last_rerun_clicks": current_clicks,
        "stop_note": None,
    })
    groups[group_index] = group_state

    request_id = _make_request_id()
    model_name = app_state.get_role_model("role_5")
    state.update({
        "status": "pending",
        "error": None,
        "model": model_name,
        "request_id": request_id,
        "model_instance_id": id(sim_model),
        "current_step": int(sim_model.current_step or 0),
        "elapsed": None,
        "generated_at": None,
        "started_at": time.perf_counter(),
        "groups": groups,
        "note": (
            "Rerunning one selected group from the current simulation state. "
            "The rest of the workspace stays visible while the new dialogue is generated."
        ),
        "stop_requested": False,
    })

    global _forum_server_state, _forum_stop_requested
    _forum_server_state = dict(state)
    _forum_stop_requested = False

    request = {
        "request_id": request_id,
        "group_index": group_index,
        "model": model_name,
        "sequence": 0,
    }
    control_state = _normalize_forum_control_state(forum_control)
    control_state.update({
        "request_id": request_id,
        "stop_requested": False,
    })
    return state, request, control_state


@callback(
    Output("forum-control-store", "data", allow_duplicate=True),
    Input("btn-stop-forum", "n_clicks"),
    State("forum-history-store", "data"),
    State("forum-control-store", "data"),
    prevent_initial_call=True,
)
def request_forum_stop(n_clicks, forum_data, forum_control):
    """Request a graceful stop after the current in-flight forum turn."""
    state = _normalize_forum_state(forum_data)
    control_state = _normalize_forum_control_state(forum_control)
    if state.get("status") != "pending" or not state.get("request_id"):
        return no_update

    current_clicks = int(n_clicks or 0)
    if current_clicks <= control_state.get("last_stop_clicks", 0):
        return no_update

    global _forum_stop_requested
    _forum_stop_requested = True

    control_state.update({
        "request_id": state.get("request_id"),
        "stop_requested": True,
        "last_stop_clicks": current_clicks,
    })
    return control_state


@callback(
    Output("forum-history-store", "data", allow_duplicate=True),
    Output("forum-run-request-store", "data", allow_duplicate=True),
    Input("forum-poll-interval", "n_intervals"),
    State("forum-run-request-store", "data"),
    prevent_initial_call=True,
)
def process_forum_request(_n_intervals, request):
    """Advance the forum by one serial step on each polling tick.

    Reads from the server-side ``_forum_server_state`` under a lock so that
    concurrent interval ticks (which carry stale client-side State values)
    never duplicate work. The updated state is written back to both the
    server variable and the ``forum-history-store`` output for UI rendering.
    """
    global _forum_server_state, _forum_stop_requested
    if not request:
        return no_update, no_update

    server_state = _copy_forum_state(_forum_server_state)
    if server_state is not None and server_state.get("status") != "pending":
        # A newer poll request can overtake the final long-running LLM response
        # in Dash's client queue. Replay the authoritative terminal snapshot so
        # the browser clears the pending request instead of polling forever.
        return server_state, None

    # Non-blocking lock — if another tick is already processing, replay the
    # latest authoritative snapshot instead of returning no_update. This keeps
    # the browser in sync even when a long LLM call causes an older response to
    # be superseded by newer interval ticks on the client.
    if not _forum_lock.acquire(blocking=False):
        if server_state is None:
            return no_update, no_update
        return server_state, request

    try:
        if _forum_server_state is None:
            return no_update, None

        import time
        from model.forums import (
            apply_forum_outcome,
            extract_forum_outcome_from_turns,
            run_forum_turn,
        )

        # Read from server-side authoritative state, not stale client State.
        state = _copy_forum_state(_forum_server_state)
        if state is None:
            return no_update, None
        if state.get("status") != "pending":
            return state, None

        model_name = str(state.get("model") or app_state.get_role_model("role_5"))

        sim_model = app_state.get_model()
        if sim_model is None:
            final_state = _finalize_forum_error_state(
                state,
                "The active simulation is no longer available. Re-initialize the model before running the forum again.",
            )
            _record_forum_audit(final_state, model_name)
            _forum_server_state = final_state
            return final_state, None
        if (
            state.get("model_instance_id") is not None
            and int(state.get("model_instance_id")) != id(sim_model)
        ) or int(state.get("current_step") or 0) != int(getattr(sim_model, "current_step", 0) or 0):
            final_state = _finalize_forum_error_state(
                state,
                (
                    "The active simulation changed after this forum was staged. "
                    "Run the forum again from the current simulation state."
                ),
            )
            _record_forum_audit(final_state, model_name)
            _forum_server_state = final_state
            return final_state, None

        stop_requested = _forum_stop_requested
        groups = list(state.get("groups") or [])

        # --- Find the active group to process ---
        group_index: int | None = None
        for i, g in enumerate(groups):
            if g.get("status") in ("active", "waiting_outcome"):
                group_index = i
                break

        if group_index is None:
            final_state = _finalize_forum_state(state, stopped=stop_requested)
            _record_forum_audit(
                final_state,
                str(final_state.get("model") or app_state.get_role_model("role_5")),
            )
            _forum_server_state = final_state
            return final_state, None

        group_state = dict(groups[group_index])
        agent_ids = [int(agent_id) for agent_id in group_state.get("agent_ids", [])]
        agent_map = {int(agent.unique_id): agent for agent in sim_model.agents}
        group_agents = [agent_map[agent_id] for agent_id in agent_ids if agent_id in agent_map]
        if len(group_agents) != len(agent_ids):
            group_state.update({
                "status": "error",
                "error": "One or more forum participants are no longer available in the active simulation.",
            })
            groups[group_index] = group_state
            next_index = _advance_to_next_queued_forum_group(groups, after_index=group_index)
            if next_index is not None:
                groups[next_index] = dict(groups[next_index])
                groups[next_index]["status"] = "active"
            state["groups"] = groups
            if next_index is None:
                final_state = _finalize_forum_state(state)
                _record_forum_audit(final_state, model_name)
                _forum_server_state = final_state
                return final_state, None
            _forum_server_state = state
            return state, request

        turn_cursor = int(group_state.get("turn_cursor") or 0)
        total_turns = int(group_state.get("total_turns") or 0)

        try:
            if stop_requested:
                stopped_state = _stop_forum_groups_gracefully(
                    state,
                    group_index=group_index,
                    group_agents=group_agents,
                    model_name=model_name,
                )
                _record_forum_audit(stopped_state, model_name)
                _forum_server_state = stopped_state
                return stopped_state, None

            if turn_cursor < total_turns:
                speaker = group_agents[turn_cursor % len(group_agents)]
                t0 = time.perf_counter()
                turn = run_forum_turn(
                    speaker,
                    group_agents,
                    _forum_group_turns(group_state.get("turns")),
                    step=int(state.get("current_step") or 0),
                    llm_model=model_name,
                )
                elapsed = time.perf_counter() - t0
                group_state["turns"] = list(group_state.get("turns") or []) + [{
                    "speaker_id": turn.speaker_id,
                    "speaker_label": turn.speaker_label,
                    "content": turn.content,
                }]
                group_state["turn_cursor"] = turn_cursor + 1
                group_state["elapsed"] = round(float(group_state.get("elapsed") or 0.0) + elapsed, 2)
                group_state["status"] = "waiting_outcome" if group_state["turn_cursor"] >= total_turns else "active"
                groups[group_index] = group_state
                state["groups"] = groups
                _forum_server_state = state
                return state, request

            t0 = time.perf_counter()
            outcome = extract_forum_outcome_from_turns(
                _forum_group_turns(group_state.get("turns")),
                step=int(state.get("current_step") or 0),
                agent_ids=agent_ids,
                llm_model=model_name,
            )
            elapsed = time.perf_counter() - t0
            group_state["elapsed"] = round(float(group_state.get("elapsed") or 0.0) + elapsed, 2)

            if outcome is None:
                group_state.update({
                    "status": "error",
                    "error": "The dialogue finished, but no norm signal could be extracted from this group.",
                })
            else:
                delta, preference_updates = apply_forum_outcome(group_agents, outcome)
                group_state.update({
                    "status": "success",
                    "outcome": outcome.model_dump(),
                    "delta_applied": round(delta, 4),
                    "preference_updates": preference_updates,
                    "error": None,
                })

            groups[group_index] = group_state
            next_index = _advance_to_next_queued_forum_group(groups, after_index=group_index)
            if next_index is not None:
                groups[next_index] = dict(groups[next_index])
                groups[next_index]["status"] = "active"
                state["groups"] = groups
                _forum_server_state = state
                return state, request

            state["groups"] = groups
            final_state = _finalize_forum_state(state)
            _record_forum_audit(final_state, model_name)
            _forum_server_state = final_state
            return final_state, None
        except Exception as e:
            group_state.update({
                "status": "error",
                "error": f"Error: {e}",
            })
            groups[group_index] = group_state
            next_index = _advance_to_next_queued_forum_group(groups, after_index=group_index)
            if next_index is not None:
                groups[next_index] = dict(groups[next_index])
                groups[next_index]["status"] = "active"
                state["groups"] = groups
                _forum_server_state = state
                return state, request

            state["groups"] = groups
            final_state = _finalize_forum_state(state)
            _record_forum_audit(final_state, model_name)
            _forum_server_state = final_state
            return final_state, None
    finally:
        _forum_lock.release()


@callback(
    Output("forum-history-store", "data", allow_duplicate=True),
    Output("forum-run-request-store", "data", allow_duplicate=True),
    Output("forum-run-dispatch-store", "data", allow_duplicate=True),
    Output("forum-control-store", "data", allow_duplicate=True),
    Input("btn-clear-forum", "n_clicks"),
    State("forum-history-store", "data"),
    prevent_initial_call=True,
)
def clear_forum_output(n_clicks, forum_data):
    """Clear the persisted forum workspace so the user can start over."""
    global _forum_server_state, _forum_stop_requested
    state = _normalize_forum_state(forum_data)
    current_clicks = int(n_clicks or 0)
    if current_clicks <= state.get("last_clear_clicks", 0):
        return no_update, no_update, no_update, no_update

    _forum_server_state = None
    _forum_stop_requested = False
    reset_state = _default_forum_state()
    reset_state["last_run_clicks"] = state.get("last_run_clicks", 0)
    reset_state["last_clear_clicks"] = current_clicks
    return reset_state, None, None, _default_forum_control_state()


@callback(
    Output("forum-output", "children"),
    Input("forum-history-store", "data"),
    Input("llm-studio-mount-interval", "n_intervals"),
)
def render_forum_output(forum_data, page_state):
    """Rebuild the Agent Forums workspace from the in-memory store."""
    return _build_forum_output(forum_data)


# =========================================================================
# Callback 9: Audit Log Viewer
# =========================================================================

@callback(
    Output("audit-log-content", "children"),
    Output("audit-trigger-store", "data"),
    Input("llm-studio-mount-interval", "n_intervals"),
    Input("btn-refresh-audit", "n_clicks"),
    Input("btn-clear-audit", "n_clicks"),
)
def update_audit_log(page_state, n_refresh, n_clear):
    triggered = ctx.triggered_id
    if triggered == "btn-clear-audit":
        app_state.clear_audit_log()
        return (
            html.Div(
                "Audit log cleared.",
                style={"color": "var(--cp-text-tertiary)",
                       "fontSize": "var(--cp-text-sm)", "textAlign": "center",
                       "padding": "var(--cp-space-8)"},
            ),
            [],
        )

    log = app_state.get_audit_log()
    if not log:
        return (
            html.Div(
                "No LLM calls recorded in this session. Use any role above to generate entries.",
                style={"color": "var(--cp-text-tertiary)",
                       "fontSize": "var(--cp-text-sm)", "textAlign": "center",
                       "padding": "var(--cp-space-8)"},
            ),
            [],
        )

    entries = list(reversed(log))
    return _build_audit_log_table(log), entries


@callback(
    Output("audit-log-detail", "children"),
    Input({"type": "audit-view-btn", "index": ALL}, "n_clicks"),
    Input("llm-studio-mount-interval", "n_intervals"),
    Input("btn-refresh-audit", "n_clicks"),
    Input("btn-clear-audit", "n_clicks"),
    State("audit-trigger-store", "data"),
)
def update_audit_detail(_view_clicks, page_state, n_refresh, n_clear, rendered_entries):
    """Render the selected audit entry below the log table."""
    triggered = ctx.triggered_id
    if triggered is None:
        return _build_audit_detail(None)
    if triggered == "llm-studio-mount-interval":
        return _build_audit_detail(None)
    if triggered == "btn-refresh-audit":
        return _build_audit_detail(None)
    if triggered == "btn-clear-audit":
        return _build_audit_detail(None)

    if isinstance(triggered, dict) and triggered.get("type") == "audit-view-btn":
        entries = rendered_entries if isinstance(rendered_entries, list) else []
        raw_index = triggered.get("index")
        index = int(raw_index) if raw_index is not None else -1
        if 0 <= index < len(entries):
            return _build_audit_detail(entries[index])

    return _build_audit_detail(None)
