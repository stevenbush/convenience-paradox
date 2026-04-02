"""model/params.py — Parameter Definitions and Society Presets

This module is the single source of truth for all configurable parameters
in the Convenience Paradox simulation. It serves three purposes:

  1. **Preset definition**: TYPE_A_PRESET and TYPE_B_PRESET define two
     archetypal abstract societies — Autonomy-Oriented and
     Convenience-Oriented — whose parameters are informed by stylised
     facts from ILO, WVS, and OECD data (see data/empirical/README.md).

  2. **Parameter metadata**: PARAMETER_DEFINITIONS provides the full
     specification of each parameter (type, range, description) used by
     the Flask API for input validation and by the dashboard for
     building interactive slider controls.

  3. **Neutrality compliance**: All preset labels are abstract. The code
     contains no country, region, or cultural references.

Empirical grounding:
  - ILO ILOSTAT 2022-2024: working hours inform available_time and
    tasks_per_step ranges.
  - WVS Wave 7 (2017-2022): autonomy/obedience dimension scores inform
    delegation_preference_mean for each preset.
  - OECD Better Life Index 2023: work-life balance scores serve as
    qualitative validation targets for simulated stress outcomes.
  - World Bank WDI 2022: service sector employment informs service_cost_factor.

  Full mapping is documented in data/empirical/README.md.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Task type definitions
# ---------------------------------------------------------------------------
# The "menu" of daily tasks agents may receive each simulation step (= day).
# Each entry specifies a base time cost (hours at average skill) and a
# skill threshold below which self-service becomes notably inefficient.
# These values are intentionally stylised — the goal is plausible relative
# ordering, not empirical precision.

TASK_TYPES: dict[str, dict[str, float]] = {
    # Routine domestic tasks: cooking, cleaning, laundry.
    # Low skill barrier; most people can do these adequately.
    "domestic": {
        "base_time": 0.8,
        "skill_requirement": 0.3,
    },
    # Administrative tasks: paperwork, banking, scheduling, bureaucracy.
    # Higher skill requirement (literacy, organisational ability).
    "administrative": {
        "base_time": 1.2,
        "skill_requirement": 0.5,
    },
    # Quick errands: shopping, parcel collection, short deliveries.
    # Low skill and low time cost — frequently delegated in convenience societies.
    "errand": {
        "base_time": 0.5,
        "skill_requirement": 0.2,
    },
    # Maintenance and repair: household fixes, vehicle upkeep, DIY.
    # Highest skill requirement and most time-intensive when self-served.
    "maintenance": {
        "base_time": 1.5,
        "skill_requirement": 0.65,
    },
}


# ---------------------------------------------------------------------------
# Society presets
# ---------------------------------------------------------------------------
# These presets define two archetypal abstract society configurations.
# They are used as the default starting points for simulation runs and
# as the basis for the Type A vs. Type B comparative analysis.
#
# IMPORTANT: These labels are abstract. They do NOT refer to any real-world
# country, culture, or geographic region. See CLAUDE.md §7 (Neutrality Policy).


TYPE_A_PRESET: dict[str, Any] = {
    # -------------------------------------------------------------------
    # Label (shown in UI, documentation, and analysis reports)
    # -------------------------------------------------------------------
    "label": "Type A Society (Autonomy-Oriented)",
    "description": (
        "An abstract society where self-reliance is the cultural norm. "
        "Individuals prefer to manage daily tasks personally. Services exist "
        "but are moderately priced, making delegation a deliberate choice. "
        "Social conformity pressure is low, allowing diverse individual "
        "strategies to persist."
    ),
    # -------------------------------------------------------------------
    # Empirical grounding note (for documentation and analysis reports)
    # -------------------------------------------------------------------
    "empirical_basis": (
        "Parameters informed by ILO ILOSTAT 2022-2024 data for high-autonomy "
        "regions (avg ~36.8h/week worked), WVS Wave 7 autonomy scores "
        "(0.65-0.72 range), and OECD Better Life Index work-life balance "
        "scores (8.0-9.0 range). See data/empirical/README.md."
    ),
    # -------------------------------------------------------------------
    # Core simulation parameters
    # -------------------------------------------------------------------
    "num_agents": 100,
    # Starting delegation preference is low: most agents default to self-service.
    # Drawn from a normal distribution; std captures individual variation.
    # Grounded in WVS autonomy score ~0.68 → delegation_preference ≈ 1 - 0.68 = 0.32,
    # slightly adjusted to reflect that not all tasks map equally to WVS items.
    "delegation_preference_mean": 0.25,
    "delegation_preference_std": 0.10,
    # Service cost: moderately expensive relative to agents' time value.
    # Grounded in World Bank service employment data for high-autonomy regions
    # (service sector competitive but not overwhelmingly cheap).
    "service_cost_factor": 0.65,
    # Low conformity pressure: agents are less influenced by neighbours'
    # delegation behaviour. Individual strategies persist longer.
    "social_conformity_pressure": 0.15,
    # Task load: moderate. Grounded in ILO weekly hours data (~36.8h/week
    # → ~7.4h/day), suggesting moderate daily task burden.
    "tasks_per_step_mean": 2.2,
    "tasks_per_step_std": 0.7,
    # Available time: higher in autonomy-oriented societies because the ILO
    # data shows fewer total working hours, leaving more discretionary time.
    "initial_available_time": 8.0,
    # Stress threshold: agents experience stress if they have fewer than
    # 2.5 hours of free time remaining at end of day.
    "stress_threshold": 2.5,
    # Stress recovery rate: how quickly stress falls when agents have surplus time.
    "stress_recovery_rate": 0.10,
    # Adaptation rate: how quickly delegation preference shifts each step.
    # Lower in Type A — social norms are more stable and change-resistant.
    "adaptation_rate": 0.02,
    # Network topology for social influence.
    "network_type": "small_world",
    # Fixed seed for reproducibility across comparative runs.
    "seed": 42,
}


TYPE_B_PRESET: dict[str, Any] = {
    # -------------------------------------------------------------------
    # Label
    # -------------------------------------------------------------------
    "label": "Type B Society (Convenience-Oriented)",
    "description": (
        "An abstract society where extensive service delegation is the norm. "
        "Daily tasks are routinely outsourced to a large service economy. "
        "Services are abundant and cheap relative to personal time value. "
        "Strong social conformity pressure reinforces delegation behaviour."
    ),
    # -------------------------------------------------------------------
    # Empirical grounding note
    # -------------------------------------------------------------------
    "empirical_basis": (
        "Parameters informed by ILO ILOSTAT 2022-2024 data for high-delegation "
        "regions (avg ~49.8h/week worked), WVS Wave 7 autonomy scores "
        "(0.30-0.40 range), and OECD Better Life Index work-life balance "
        "scores (4.5-6.0 range). See data/empirical/README.md."
    ),
    # -------------------------------------------------------------------
    # Core simulation parameters
    # -------------------------------------------------------------------
    "num_agents": 100,
    # Starting delegation preference is high: most agents default to delegation.
    # Grounded in WVS autonomy score ~0.35 → delegation_preference ≈ 1 - 0.35 = 0.65.
    "delegation_preference_mean": 0.72,
    "delegation_preference_std": 0.10,
    # Service cost: low. Abundant competition and informal service economy
    # drive prices down. Grounded in World Bank data (high service employment
    # fractions create downward price pressure).
    "service_cost_factor": 0.20,
    # High conformity pressure: strong social norm to use services.
    # Agents whose neighbours delegate heavily will shift their own preferences.
    "social_conformity_pressure": 0.65,
    # Task load: slightly higher than Type A (more tasks per day reflects
    # the busier pace of convenience-oriented societies), but agents expect
    # to delegate many of them.
    "tasks_per_step_mean": 2.8,
    "tasks_per_step_std": 0.8,
    # Available time: same starting budget as Type A (both societies have
    # 24-hour days). The *difference* in outcomes emerges from task management
    # behaviour, not from different initial budgets.
    "initial_available_time": 8.0,
    # Stress threshold: same as Type A for comparability.
    "stress_threshold": 2.5,
    # Stress recovery: same as Type A.
    "stress_recovery_rate": 0.10,
    # Adaptation rate: higher in Type B — social norms are more dynamic
    # and agents adjust their behaviour more rapidly in response to peers.
    "adaptation_rate": 0.05,
    # Network topology.
    "network_type": "small_world",
    # Fixed seed for reproducibility.
    "seed": 42,
}


# ---------------------------------------------------------------------------
# Parameter definitions (metadata for API validation and dashboard sliders)
# ---------------------------------------------------------------------------
# Each entry describes one tuneable model parameter:
#   - type: Python type for input validation
#   - min / max: valid range (inclusive)
#   - default: value to use if not specified (midpoint between A and B presets)
#   - description: shown in dashboard tooltips and analysis reports
#   - unit: human-readable unit string for axis labels

PARAMETER_DEFINITIONS: dict[str, dict[str, Any]] = {
    "num_agents": {
        "type": int,
        "min": 20,
        "max": 500,
        "default": 100,
        "description": "Total number of resident agents in the simulation.",
        "unit": "agents",
    },
    "delegation_preference_mean": {
        "type": float,
        "min": 0.0,
        "max": 1.0,
        "default": 0.50,
        "description": (
            "Mean starting delegation preference across agents. "
            "0 = always self-serve; 1 = always delegate. "
            "This is the primary independent variable for H1-H4."
        ),
        "unit": "probability [0–1]",
    },
    "delegation_preference_std": {
        "type": float,
        "min": 0.0,
        "max": 0.3,
        "default": 0.10,
        "description": "Standard deviation of initial delegation preferences (agent heterogeneity).",
        "unit": "probability",
    },
    "service_cost_factor": {
        "type": float,
        "min": 0.05,
        "max": 1.0,
        "default": 0.40,
        "description": (
            "Price level of services relative to tasks' base time cost. "
            "Higher values make services more expensive, reducing delegation."
        ),
        "unit": "multiplier",
    },
    "social_conformity_pressure": {
        "type": float,
        "min": 0.0,
        "max": 1.0,
        "default": 0.30,
        "description": (
            "Strength of peer influence on delegation preference adaptation. "
            "Higher values cause agents to mirror their neighbours' behaviour more strongly."
        ),
        "unit": "weight [0–1]",
    },
    "tasks_per_step_mean": {
        "type": float,
        "min": 1.0,
        "max": 6.0,
        "default": 2.5,
        "description": "Mean number of tasks each agent receives per simulation day.",
        "unit": "tasks/day",
    },
    "tasks_per_step_std": {
        "type": float,
        "min": 0.0,
        "max": 2.0,
        "default": 0.75,
        "description": "Standard deviation of daily task count (day-to-day variability).",
        "unit": "tasks/day",
    },
    "initial_available_time": {
        "type": float,
        "min": 4.0,
        "max": 12.0,
        "default": 8.0,
        "description": (
            "Discretionary hours each agent has available per day before tasks begin. "
            "Represents time beyond fixed obligations (sleep, baseline work)."
        ),
        "unit": "hours/day",
    },
    "stress_threshold": {
        "type": float,
        "min": 0.5,
        "max": 5.0,
        "default": 2.5,
        "description": (
            "Hours of remaining available_time below which stress begins to accumulate. "
            "If an agent ends the day with fewer than this many hours, stress increases."
        ),
        "unit": "hours",
    },
    "stress_recovery_rate": {
        "type": float,
        "min": 0.01,
        "max": 0.30,
        "default": 0.10,
        "description": "Per-step reduction in stress_level when agent ends day with surplus time.",
        "unit": "stress units/step",
    },
    "adaptation_rate": {
        "type": float,
        "min": 0.005,
        "max": 0.15,
        "default": 0.03,
        "description": (
            "Learning rate for delegation preference updates. "
            "Controls how quickly agents shift behaviour in response to stress and peer influence."
        ),
        "unit": "preference units/step",
    },
    "network_type": {
        "type": str,
        "options": ["small_world", "random"],
        "default": "small_world",
        "description": (
            "Social network topology for peer influence. "
            "'small_world' (Watts-Strogatz) models realistic community structure. "
            "'random' (Erdos-Renyi) is a baseline comparison."
        ),
        "unit": "topology",
    },
}


def get_preset(name: str) -> dict[str, Any]:
    """Return a parameter preset dictionary by name.

    Args:
        name: Preset name — "type_a", "type_b", or "default".

    Returns:
        Dict of parameter name → value for the chosen preset.

    Raises:
        ValueError: If name is not a recognised preset.
    """
    presets = {
        "type_a": TYPE_A_PRESET,
        "type_b": TYPE_B_PRESET,
        "default": {
            **{k: v["default"] for k, v in PARAMETER_DEFINITIONS.items()
               if "default" in v and k != "network_type"},
            "network_type": "small_world",
            "seed": 42,
        },
    }
    if name.lower() not in presets:
        raise ValueError(
            f"Unknown preset '{name}'. Valid options: {list(presets.keys())}"
        )
    return presets[name.lower()]
