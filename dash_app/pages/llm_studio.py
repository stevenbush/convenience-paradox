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
from dash import html, dcc, callback, clientside_callback, Input, Output, State, ctx, no_update

from api.schemas import SimulationParams
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


def _default_llm_studio_state() -> dict[str, Any]:
    """Return the default browser-session state for the LLM Studio page."""
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
    return datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")


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
        )

    if status in {"empty", "error"}:
        return card(
            title="Parser Error",
            subtitle=subtitle,
            children=html.Div(
                scenario_state.get("error") or "Unable to parse the scenario.",
                className="cp-scenario__reply-error",
            ),
        )

    result = scenario_state.get("result") or {}
    params_rows = []
    for param_key in SCENARIO_PARAM_KEYS:
        source = (result.get("parameter_sources") or {}).get(param_key, "llm")
        params_rows.append(
            html.Tr([
                html.Td(
                    _scenario_param_label(param_key),
                    style={"fontSize": "var(--cp-text-sm)"},
                ),
                html.Td(
                    [
                        html.Span(
                            _format_scenario_value(result.get(param_key)),
                            style={
                                "fontFamily": "var(--cp-font-mono)",
                                "fontSize": "var(--cp-text-sm)",
                            },
                        ),
                        html.Span(
                            "Neutral default" if source == "default" else "LLM-derived",
                            className=(
                                "cp-badge cp-badge--warning ms-2"
                                if source == "default"
                                else "cp-badge cp-badge--primary ms-2"
                            ),
                        ),
                    ],
                ),
            ])
        )

    children = [
        html.Div("Parsed Feedback", className="cp-scenario__section-label"),
        html.P(
            result.get("scenario_summary", ""),
            className="cp-scenario__reply-summary",
        ),
        html.P(
            result.get("reasoning", ""),
            className="cp-scenario__reply-reasoning",
        ),
    ]
    if result.get("coverage_warning"):
        children.extend([
            html.Div("Coverage Warning", className="cp-scenario__section-label"),
            html.Div(
                [
                    html.Div(result.get("coverage_warning"), className="cp-scenario__warning-text"),
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
        dbc.Table(
            html.Tbody(params_rows),
            bordered=True,
            size="sm",
            className="mt-2",
        ),
        html.Div("How To Use These Parameters", className="cp-scenario__section-label"),
        html.Div(
            result.get("next_step_guidance", SCENARIO_NEXT_STEP_GUIDANCE),
            className="cp-scenario__next-step",
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
    history = data.get("history")
    if isinstance(history, list):
        state["history"] = [item for item in history if isinstance(item, dict)]
    context_snapshot = data.get("context")
    if isinstance(context_snapshot, dict):
        state["context"] = context_snapshot

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
        )

    summary_badges = html.Div(
        [
            status_badge(f"Step {context_snapshot.get('current_step', 0)}", "info"),
            status_badge(f"Preset: {str(context_snapshot.get('preset', 'custom')).replace('_', ' ').title()}", "neutral"),
            status_badge("Live results", "success"),
        ],
        className="d-flex gap-2 flex-wrap mb-3",
    )

    metric_rows = [
        html.Tr([
            html.Td(label, style={"fontSize": "var(--cp-text-sm)"}),
            html.Td(
                _format_scenario_value((context_snapshot.get("latest_metrics") or {}).get(key)),
                style={"fontFamily": "var(--cp-font-mono)", "fontSize": "var(--cp-text-sm)"},
            ),
        ])
        for key, label in CHAT_CONTEXT_METRICS
        if key in (context_snapshot.get("latest_metrics") or {})
    ]

    param_rows = [
        html.Tr([
            html.Td(label, style={"fontSize": "var(--cp-text-sm)"}),
            html.Td(
                _format_scenario_value((context_snapshot.get("params") or {}).get(key)),
                style={"fontFamily": "var(--cp-font-mono)", "fontSize": "var(--cp-text-sm)"},
            ),
        ])
        for key, label in CHAT_CONTEXT_PARAMS
        if key in (context_snapshot.get("params") or {})
    ]

    children = [
        summary_badges,
        html.Div(str(context_snapshot.get("note") or ""), className="cp-scenario__reply-reasoning"),
        html.Div("Latest Metrics", className="cp-scenario__section-label"),
        dbc.Table(html.Tbody(metric_rows), bordered=True, size="sm", className="mt-2"),
        html.Div("Model Parameters", className="cp-scenario__section-label"),
        dbc.Table(html.Tbody(param_rows), bordered=True, size="sm", className="mt-2"),
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
    )


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
                                    maxLength=500,
                                    persistence=True,
                                    persistence_type="session",
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
                                    "The message is sent immediately; the parser reply appears as soon as validation finishes.",
                                    className="cp-scenario__composer-note",
                                ),
                            ],
                            className="cp-scenario-composer",
                        ),
                    ],
                ),
            ], md=7),
            dbc.Col(
                html.Div(id="scenario-output"),
                md=5,
            ),
        ]),
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
                                    persistence=True,
                                    persistence_type="session",
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
                                    "Your question is sent together with the current simulation snapshot shown on the right.",
                                    className="cp-scenario__composer-note",
                                ),
                            ],
                            className="cp-scenario-composer",
                        ),
                    ],
                ),
            ], md=7),
            dbc.Col(
                html.Div(id="chat-context-output"),
                md=5,
            ),
        ]),
    ], className="p-3")


def _tab_profile() -> html.Div:
    """Role 2: Profile Generator — demographic description to agent attributes."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Input(
                    id="profile-input",
                    placeholder="Describe an agent type (e.g., 'An elderly retiree who values self-sufficiency')...",
                    type="text",
                ),
                html.Div([
                    dbc.Button(
                        [html.I(className="fas fa-user-gear me-1"), "Generate Profile"],
                        id="btn-generate-profile",
                        className="cp-btn-primary mt-2",
                        size="sm",
                    ),
                    dbc.Spinner(
                        html.Span(id="profile-spinner"),
                        size="sm", color="primary",
                        spinner_class_name="ms-2",
                    ),
                ], className="d-flex align-items-center"),
            ], md=5),
            dbc.Col(
                html.Div(id="profile-output"),
                md=7,
            ),
        ]),
    ], className="p-3")


def _tab_annotations() -> html.Div:
    """Role 4: Visualization Annotator — auto-generate chart captions."""
    return html.Div([
        html.Div([
            dbc.Button(
                [html.I(className="fas fa-pen-fancy me-1"), "Annotate All Charts"],
                id="btn-annotate-charts",
                className="cp-btn-primary",
                size="sm",
            ),
            dbc.Spinner(
                html.Span(id="annotate-spinner"),
                size="sm", color="primary",
                spinner_class_name="ms-2",
            ),
        ], className="d-flex align-items-center mb-3"),
        html.Div(id="annotations-output"),
    ], className="p-3")


def _tab_forums() -> html.Div:
    """Role 5: Agent Forums — experimental LLM-powered group discussions."""
    return html.Div([
        html.Div([
            status_badge("Experimental Mode", "warning"),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                html.Label("Forum Fraction", className="cp-controls__slider-label"),
                dcc.Slider(
                    id="forum-fraction-slider",
                    min=0.05, max=0.5, step=0.05, value=0.20,
                    marks=None,
                    tooltip={"placement": "bottom"},
                ),
            ], md=4),
            dbc.Col([
                html.Label("Group Size", className="cp-controls__slider-label"),
                dbc.RadioItems(
                    id="forum-group-size",
                    options=[{"label": str(i), "value": i} for i in [2, 3, 4]],
                    value=2, inline=True,
                ),
            ], md=3),
            dbc.Col([
                html.Label("Dialogue Turns", className="cp-controls__slider-label"),
                dbc.RadioItems(
                    id="forum-num-turns",
                    options=[{"label": str(i), "value": i} for i in [1, 2, 3]],
                    value=2, inline=True,
                ),
            ], md=3),
            dbc.Col([
                dbc.Button(
                    [html.I(className="fas fa-people-group me-1"), "Run Forum"],
                    id="btn-run-forum",
                    className="cp-btn-primary mt-3",
                    size="sm",
                ),
            ], md=2),
        ], className="mb-3"),
        dbc.Spinner(
            html.Div(id="forum-output"),
            color="primary",
        ),
    ], className="p-3")


def _tab_audit() -> html.Div:
    """Audit log viewer for all LLM interactions during this session."""
    return html.Div([
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
        ], className="d-flex mb-3"),
        html.Div(id="audit-log-content"),
    ], className="p-3")


def _tab_content() -> dbc.Tabs:
    """Horizontal tab bar for the 6 LLM role interfaces."""
    return dbc.Tabs([
        dbc.Tab(_tab_scenario(), label="Scenario Parser", tab_id="tab-scenario"),
        dbc.Tab(_tab_chat(), label="Chat Interpreter", tab_id="tab-chat"),
        dbc.Tab(_tab_profile(), label="Profile Generator", tab_id="tab-profile"),
        dbc.Tab(_tab_annotations(), label="Annotations", tab_id="tab-annotations"),
        dbc.Tab(_tab_forums(), label="Agent Forums", tab_id="tab-forums"),
        dbc.Tab(_tab_audit(), label="Audit Log", tab_id="tab-audit"),
    ], id="llm-tabs", active_tab="tab-scenario", className="cp-tabs")


layout = html.Div([
    dcc.Store(id="llm-studio-page-store", data={"mounted": True}),
    dcc.Store(id="scenario-thread-scroll-store", data=0),
    dcc.Store(id="chat-thread-scroll-store", data=0),
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
                  elapsed: float, error: str | None = None) -> None:
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
    Input("llm-studio-page-store", "data"),
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
    Input("llm-studio-page-store", "data"),
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
    """Persist the current LLM Studio tab in session storage."""
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
    state["scenario"] = _default_scenario_state()
    return state, ""


# =========================================================================
# Callback 8: Stage Scenario Parser request immediately
# =========================================================================

@callback(
    Output("llm-studio-store", "data", allow_duplicate=True),
    Output("scenario-parse-request-store", "data"),
    Output("scenario-input", "value"),
    Input("btn-parse-scenario", "n_clicks"),
    State("scenario-input", "value"),
    State("llm-studio-store", "data"),
    prevent_initial_call=True,
)
def stage_scenario_request(n_clicks, description, store_data):
    """Append the user message and a pending assistant bubble before parsing starts."""
    if not description or not description.strip():
        state = _normalize_llm_studio_state(store_data)
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
    next_state = _stage_scenario_request(store_data, description.strip(), model_name, request_id)
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
        return no_update

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
        raw_response = role_calls[-1].get("raw_response") if role_calls else None
        _record_audit("Role 1", "scenario_parser", model_name,
                      description, result, elapsed)
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
        )
    except Exception as e:
        elapsed = time.perf_counter() - t0
        role_calls = recorder.get_calls("role_1")
        raw_response = role_calls[-1].get("raw_response") if role_calls else None
        _record_audit("Role 1", "scenario_parser", model_name,
                      description, None, elapsed, str(e))
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
        )


# =========================================================================
# Callback 10: Rehydrate Scenario Parser views on page remount
# =========================================================================

@callback(
    Output("scenario-thread", "children"),
    Output("scenario-output", "children"),
    Input("llm-studio-store", "data"),
    Input("llm-studio-page-store", "data"),
)
def render_scenario_views(store_data, page_state):
    """Render the transcript and the structured inspector from session state."""
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
    Input("llm-studio-page-store", "data"),
    prevent_initial_call=True,
)


# =========================================================================
# Callback 12: Clear Chat Interpreter conversation
# =========================================================================

@callback(
    Output("chat-history-store", "data", allow_duplicate=True),
    Output("chat-input", "value", allow_duplicate=True),
    Input("btn-clear-chat", "n_clicks"),
    prevent_initial_call=True,
)
def clear_chat_conversation(n_clicks):
    """Reset the Result Interpreter transcript so the user can start over."""
    return _default_chat_state(), ""


# =========================================================================
# Callback 13: Stage Chat Interpreter request immediately
# =========================================================================

@callback(
    Output("chat-history-store", "data", allow_duplicate=True),
    Output("chat-interpret-request-store", "data"),
    Output("chat-input", "value"),
    Input("btn-chat-send", "n_clicks"),
    State("chat-input", "value"),
    State("chat-history-store", "data"),
    prevent_initial_call=True,
)
def stage_chat_request(n_clicks, question, chat_data):
    """Append the user message and a pending assistant bubble before interpretation starts."""
    if not question or not question.strip():
        return no_update, no_update, no_update

    context_snapshot = _build_chat_context_snapshot()
    if not context_snapshot.get("initialized"):
        state = _normalize_chat_state(chat_data)
        state.update({
            "status": "error",
            "error": str(context_snapshot.get("note") or "No simulation results are available."),
            "context": context_snapshot,
        })
        return state, no_update, no_update

    model_name = app_state.get_role_model("role_3")
    request_id = _make_request_id()
    next_state = _stage_chat_request(
        chat_data,
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
        return no_update

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
        raw_response = role_calls[-1].get("raw_response") if role_calls else None
        _record_audit("Role 3", "result_interpreter", model_name, question, result, elapsed)
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
        )
    except Exception as e:
        elapsed = time.perf_counter() - t0
        role_calls = recorder.get_calls("role_3")
        raw_response = role_calls[-1].get("raw_response") if role_calls else None
        _record_audit("Role 3", "result_interpreter", model_name, question, None, elapsed, str(e))
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
        )


# =========================================================================
# Callback 15: Rehydrate Chat Interpreter views on page remount
# =========================================================================

@callback(
    Output("chat-thread", "children"),
    Output("chat-context-output", "children"),
    Input("chat-history-store", "data"),
    Input("llm-studio-page-store", "data"),
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
    Input("llm-studio-page-store", "data"),
    prevent_initial_call=True,
)


# =========================================================================
# Callback 6: Profile Generator (Role 2)
# =========================================================================

@callback(
    Output("profile-output", "children"),
    Input("btn-generate-profile", "n_clicks"),
    State("profile-input", "value"),
    prevent_initial_call=True,
)
def generate_profile_cb(n_clicks, description):
    if not description or not description.strip():
        return html.Div("Please enter a demographic description.",
                        style={"color": "var(--cp-danger)", "fontSize": "var(--cp-text-sm)"})

    import time
    model_name = app_state.get_role_model("role_2")
    t0 = time.perf_counter()
    try:
        from api.llm_service import generate_agent_profile
        result = generate_agent_profile(description, model=model_name)
        elapsed = time.perf_counter() - t0
        _record_audit("Role 2", "profile_generator", model_name,
                      description, result, elapsed)

        # Radar chart of 4 skills
        skills = ["domestic", "administrative", "errand", "maintenance"]
        skill_vals = [result.get(f"skill_{s}", 0.5) for s in skills]
        skill_vals.append(skill_vals[0])  # close the polygon
        labels = [s.title() for s in skills] + [skills[0].title()]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=skill_vals, theta=labels,
            fill="toself",
            fillcolor="rgba(44,140,153,0.15)",
            line=dict(color=CHART_COLORWAY[0], width=2),
            name="Skills",
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 1]),
            ),
            showlegend=False,
            margin=dict(t=30, b=30, l=60, r=60),
            height=250,
        )

        return card(
            title="Generated Profile",
            subtitle=f"{elapsed:.1f}s · {model_name}",
            children=[
                html.P(
                    result.get("profile_description", ""),
                    style={"fontStyle": "italic", "fontSize": "var(--cp-text-sm)"},
                ),
                dbc.Row([
                    dbc.Col([
                        html.Div(
                            f"Delegation: {result.get('delegation_preference', 0):.2f}",
                            style={"fontSize": "var(--cp-text-lg)",
                                   "fontWeight": "var(--cp-weight-bold)",
                                   "color": "var(--cp-primary)"},
                        ),
                        html.Div("delegation_preference",
                                 style={"fontSize": "var(--cp-text-xs)",
                                        "color": "var(--cp-text-tertiary)"}),
                    ], md=4, className="d-flex flex-column justify-content-center"),
                    dbc.Col(
                        dcc.Graph(figure=fig, config={"displayModeBar": False},
                                  style={"height": "250px"}),
                        md=8,
                    ),
                ]),
            ],
        )
    except Exception as e:
        elapsed = time.perf_counter() - t0
        _record_audit("Role 2", "profile_generator", model_name,
                      description, None, elapsed, str(e))
        return html.Div(
            f"Error: {e}",
            style={"color": "var(--cp-danger)", "fontSize": "var(--cp-text-sm)"},
        )


# =========================================================================
# Callback 7: Annotations (Role 4)
# =========================================================================

ANNOTATABLE_CHARTS = [
    ("total_labor_hours", "Total Labor Hours (H1)"),
    ("stress_delegation", "Stress & Delegation (H2/H3)"),
    ("social_efficiency", "Social Efficiency (H2)"),
    ("market_health", "Market Health"),
]


@callback(
    Output("annotations-output", "children"),
    Input("btn-annotate-charts", "n_clicks"),
    prevent_initial_call=True,
)
def annotate_charts_cb(n_clicks):
    sim_model = app_state.get_model()
    if sim_model is None or sim_model.current_step == 0:
        return html.Div("Initialize and run a simulation first.",
                        style={"color": "var(--cp-text-tertiary)",
                               "fontSize": "var(--cp-text-sm)"})

    import time
    from api.llm_service import annotate_visualization
    model_name = app_state.get_role_model("role_4")
    df = sim_model.get_model_dataframe()

    annotation_cards = []
    for chart_key, chart_label in ANNOTATABLE_CHARTS:
        col_map = {
            "total_labor_hours": "total_labor_hours",
            "stress_delegation": "avg_stress",
            "social_efficiency": "social_efficiency",
            "market_health": "unmatched_tasks",
        }
        col = col_map.get(chart_key, chart_key)
        if col in df.columns:
            series = df[col]
            metrics = {
                "min": round(float(series.min()), 4),
                "max": round(float(series.max()), 4),
                "mean": round(float(series.mean()), 4),
                "last": round(float(series.iloc[-1]), 4),
                "trend": "rising" if series.iloc[-1] > series.iloc[0] else "falling",
                "steps": len(series),
            }
        else:
            metrics = {"note": "Column not found"}

        t0 = time.perf_counter()
        try:
            result = annotate_visualization(
                chart_label, metrics, model=model_name,
            )
            elapsed = time.perf_counter() - t0
            _record_audit("Role 4", "visualization_annotator", model_name,
                          chart_label, result, elapsed)

            annotation_cards.append(card(
                title=result.get("chart_title", chart_label),
                subtitle=result.get("hypothesis_tag", ""),
                children=[
                    html.P(result.get("caption", ""),
                           style={"fontSize": "var(--cp-text-sm)"}),
                    html.Div(
                        [html.I(className="fas fa-lightbulb me-1"),
                         result.get("key_insight", "")],
                        style={"fontSize": "var(--cp-text-sm)",
                               "color": "var(--cp-primary)",
                               "fontWeight": "var(--cp-weight-semibold)"},
                    ),
                ],
                footer=html.Span(f"{elapsed:.1f}s · {model_name}",
                                 style={"fontSize": "var(--cp-text-xs)",
                                        "color": "var(--cp-text-tertiary)"}),
            ))
        except Exception as e:
            elapsed = time.perf_counter() - t0
            _record_audit("Role 4", "visualization_annotator", model_name,
                          chart_label, None, elapsed, str(e))
            annotation_cards.append(card(
                title=chart_label,
                children=html.Div(f"Error: {e}",
                                  style={"color": "var(--cp-danger)",
                                         "fontSize": "var(--cp-text-sm)"}),
            ))

    return html.Div(annotation_cards)


# =========================================================================
# Callback 8: Agent Forums (Role 5)
# =========================================================================

@callback(
    Output("forum-output", "children"),
    Input("btn-run-forum", "n_clicks"),
    State("forum-fraction-slider", "value"),
    State("forum-group-size", "value"),
    State("forum-num-turns", "value"),
    prevent_initial_call=True,
)
def run_forum_cb(n_clicks, fraction, group_size, num_turns):
    sim_model = app_state.get_model()
    if sim_model is None:
        return html.Div("Initialize a simulation first.",
                        style={"color": "var(--cp-danger)",
                               "fontSize": "var(--cp-text-sm)"})

    import time
    from model.forums import run_forum_step, format_session_for_api

    model_name = app_state.get_role_model("role_5")
    t0 = time.perf_counter()
    try:
        session = run_forum_step(
            sim_model,
            forum_fraction=fraction or 0.20,
            group_size=group_size or 2,
            num_turns=num_turns or 2,
            llm_model=model_name,
        )
        elapsed = time.perf_counter() - t0
        session_data = format_session_for_api(session)
        _record_audit("Role 5", "agent_forums", model_name,
                      f"fraction={fraction}, groups={group_size}",
                      f"{len(session_data.get('groups', []))} groups",
                      elapsed)

        group_cards = []
        for gi, group in enumerate(session_data.get("groups", [])):
            # Build dialogue bubbles
            bubbles = []
            for turn in group.get("turns", []):
                bubbles.append(html.Div([
                    html.Div(
                        turn.get("speaker_label", "Agent"),
                        className="cp-chat__sender",
                    ),
                    html.Div(turn.get("content", "")),
                ], className="cp-chat__message cp-chat__message--ai"))

            outcome = group.get("outcome", {}) or {}
            norm_signal = outcome.get("norm_signal", 0)
            confidence = outcome.get("confidence", 0)
            summary = outcome.get("summary", "No consensus extracted")

            norm_color = CHART_COLORWAY[2] if norm_signal < 0 else CHART_COLORWAY[1]
            norm_label = f"{'→ Autonomy' if norm_signal < 0 else '→ Delegation'}"

            group_cards.append(card(
                title=f"Group {gi + 1}",
                subtitle=f"Agents {group.get('agent_ids', [])}",
                children=[
                    html.Div(bubbles, className="cp-chat",
                             style={"maxHeight": "200px", "overflowY": "auto"}),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            html.Div("Norm Signal", style={"fontSize": "var(--cp-text-xs)",
                                                           "color": "var(--cp-text-tertiary)"}),
                            html.Div(
                                f"{norm_signal:+.2f} {norm_label}",
                                style={"fontWeight": "var(--cp-weight-bold)",
                                       "color": norm_color},
                            ),
                        ], md=3),
                        dbc.Col([
                            html.Div("Confidence", style={"fontSize": "var(--cp-text-xs)",
                                                          "color": "var(--cp-text-tertiary)"}),
                            html.Div(f"{confidence:.2f}",
                                     style={"fontWeight": "var(--cp-weight-bold)"}),
                        ], md=3),
                        dbc.Col([
                            html.Div("Delta Applied",
                                     style={"fontSize": "var(--cp-text-xs)",
                                            "color": "var(--cp-text-tertiary)"}),
                            html.Div(f"{group.get('delta_applied', 0):+.4f}",
                                     style={"fontFamily": "var(--cp-font-mono)"}),
                        ], md=3),
                        dbc.Col([
                            html.Div("Summary", style={"fontSize": "var(--cp-text-xs)",
                                                       "color": "var(--cp-text-tertiary)"}),
                            html.Div(summary, style={"fontSize": "var(--cp-text-sm)"}),
                        ], md=3),
                    ]),
                ],
            ))

        return html.Div([
            html.Div([
                html.Span(f"Completed in {elapsed:.1f}s · {model_name} · ",
                          style={"fontSize": "var(--cp-text-sm)",
                                 "color": "var(--cp-text-secondary)"}),
                html.Span(
                    f"{session_data.get('n_agents_participating', 0)} agents, "
                    f"{len(session_data.get('groups', []))} groups",
                    style={"fontSize": "var(--cp-text-sm)",
                           "fontWeight": "var(--cp-weight-semibold)"},
                ),
            ], className="mb-3"),
            *group_cards,
        ])
    except Exception as e:
        elapsed = time.perf_counter() - t0
        _record_audit("Role 5", "agent_forums", model_name,
                      f"fraction={fraction}", None, elapsed, str(e))
        return html.Div(
            f"Error: {e}",
            style={"color": "var(--cp-danger)", "fontSize": "var(--cp-text-sm)"},
        )


# =========================================================================
# Callback 9: Audit Log Viewer
# =========================================================================

@callback(
    Output("audit-log-content", "children"),
    Input("btn-refresh-audit", "n_clicks"),
    Input("btn-clear-audit", "n_clicks"),
    prevent_initial_call=True,
)
def update_audit_log(n_refresh, n_clear):
    triggered = ctx.triggered_id
    if triggered == "btn-clear-audit":
        app_state.clear_audit_log()
        return html.Div(
            "Audit log cleared.",
            style={"color": "var(--cp-text-tertiary)",
                   "fontSize": "var(--cp-text-sm)", "textAlign": "center",
                   "padding": "var(--cp-space-8)"},
        )

    log = app_state.get_audit_log()
    if not log:
        return html.Div(
            "No LLM calls recorded in this session. Use any role above to generate entries.",
            style={"color": "var(--cp-text-tertiary)",
                   "fontSize": "var(--cp-text-sm)", "textAlign": "center",
                   "padding": "var(--cp-space-8)"},
        )

    rows = []
    for entry in reversed(log):
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
                               "maxWidth": "200px", "overflow": "hidden",
                               "textOverflow": "ellipsis", "whiteSpace": "nowrap"}),
            ])
        )

    return dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th("Time"), html.Th("Role"), html.Th("Kind"),
                html.Th("Model"), html.Th("Time"), html.Th("Status"),
                html.Th("Prompt"),
            ])),
            html.Tbody(rows),
        ],
        bordered=True, hover=True, responsive=True, size="sm",
        style={"fontSize": "var(--cp-text-sm)"},
    )
