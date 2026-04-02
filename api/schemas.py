"""api/schemas.py — Pydantic Schemas for Input Validation and Structured Output

Architecture role:
    This module defines all Pydantic data schemas used in the project:
      - Phase 3: Input validation for Flask API simulation parameters.
      - Phase 4: Structured output schemas for LLM responses (Roles 1–4).
      - Phase 5: Forum dialogue schemas for agent communication.

    All LLM structured outputs pass through Pydantic validation before
    being used by the simulation or displayed in the UI. This enforces
    the white-box principle: LLM outputs are always checked against explicit
    schemas before they can influence any model state.

    Pydantic v2 is used (installed as part of the project environment).
    All schemas use strict type annotations for clarity and auditability.

See also:
    - api/llm_service.py — uses these schemas for Ollama structured output
    - api/routes.py      — uses SimulationParams for API input validation
    - CLAUDE.md §6.3     — LLM implementation requirements (logging, validation)
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Phase 3: Simulation Parameter Schemas
# ---------------------------------------------------------------------------

class SimulationParams(BaseModel):
    """Validated parameters for initialising a ConvenienceParadoxModel.

    Used by POST /api/simulation/init to parse and validate the request body.
    All fields have defaults so a minimal {} body initialises a default model.

    Attributes:
        num_agents: Number of resident agents (20–500).
        delegation_preference_mean: Mean starting delegation probability [0, 1].
        delegation_preference_std: Std dev of starting preference.
        service_cost_factor: Service price multiplier [0.05, 1.0].
        social_conformity_pressure: Peer influence strength [0, 1].
        tasks_per_step_mean: Mean daily tasks per agent [1, 6].
        tasks_per_step_std: Std dev of daily task count.
        stress_threshold: Hours below which stress grows.
        stress_recovery_rate: Per-step stress reduction when surplus time.
        adaptation_rate: Preference learning rate.
        initial_available_time: Daily discretionary hours per agent.
        network_type: Social network topology.
        seed: Random seed for reproducibility.
        preset: Optional preset name ("type_a", "type_b", "default").
            If provided, overrides all other fields with preset values.
    """

    num_agents: int = Field(default=100, ge=20, le=500)
    delegation_preference_mean: float = Field(default=0.50, ge=0.0, le=1.0)
    delegation_preference_std: float = Field(default=0.10, ge=0.0, le=0.30)
    service_cost_factor: float = Field(default=0.40, ge=0.05, le=1.0)
    social_conformity_pressure: float = Field(default=0.30, ge=0.0, le=1.0)
    tasks_per_step_mean: float = Field(default=2.5, ge=1.0, le=6.0)
    tasks_per_step_std: float = Field(default=0.75, ge=0.0, le=2.0)
    stress_threshold: float = Field(default=2.5, ge=0.5, le=5.0)
    stress_recovery_rate: float = Field(default=0.10, ge=0.01, le=0.30)
    adaptation_rate: float = Field(default=0.03, ge=0.005, le=0.15)
    initial_available_time: float = Field(default=8.0, ge=4.0, le=12.0)
    network_type: str = Field(default="small_world")
    seed: int = Field(default=42, ge=0)
    preset: Optional[str] = Field(default=None)

    @field_validator("network_type")
    @classmethod
    def validate_network_type(cls, v: str) -> str:
        """Ensure network_type is one of the supported options."""
        valid = {"small_world", "random"}
        if v not in valid:
            raise ValueError(f"network_type must be one of {valid}. Got: '{v}'")
        return v

    @field_validator("preset")
    @classmethod
    def validate_preset(cls, v: Optional[str]) -> Optional[str]:
        """Ensure preset name is valid if provided."""
        if v is not None:
            valid = {"type_a", "type_b", "default"}
            if v.lower() not in valid:
                raise ValueError(f"preset must be one of {valid}. Got: '{v}'")
            return v.lower()
        return v

    def to_model_kwargs(self) -> dict[str, Any]:
        """Convert to kwargs dict for ConvenienceParadoxModel constructor.

        Returns:
            Dict of parameter name → value, excluding the `preset` field.
        """
        d = self.model_dump(exclude={"preset"})
        return d


class StepRequest(BaseModel):
    """Request body for POST /api/simulation/step.

    Attributes:
        steps: Number of steps to advance (1–200).
    """
    steps: int = Field(default=1, ge=1, le=200)


class RunRequest(BaseModel):
    """Request body for POST /api/simulation/run.

    Attributes:
        max_steps: Maximum steps to run (1–1000).
        save_run: Whether to persist this run to SQLite.
        run_label: Optional label for the saved run.
    """
    max_steps: int = Field(default=50, ge=1, le=1000)
    save_run: bool = Field(default=True)
    run_label: Optional[str] = Field(default=None, max_length=100)


# ---------------------------------------------------------------------------
# Phase 4: LLM Structured Output Schemas
# ---------------------------------------------------------------------------
# These schemas define the JSON structure that Ollama must return for each
# LLM role. The `format=MySchema.model_json_schema()` parameter in
# ollama.chat() enforces this structure via constrained decoding.
# See api/llm_service.py for usage.

class ParsedScenarioParams(BaseModel):
    """Output schema for Role 1 — Scenario Parser.

    Maps a user's natural language scenario description to structured
    model parameters. Fields marked Optional may not always be extractable
    from the description; they default to None and are filled with preset
    defaults by the LLM service layer.

    Note:
        This schema is intentionally a subset of SimulationParams.
        The LLM is only asked to extract the most semantically clear
        parameters from natural language. Technical parameters like
        `delegation_preference_std` are set by the service layer, not the LLM.
    """
    delegation_preference_mean: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="How much agents in this scenario tend to delegate [0=never, 1=always].",
    )
    service_cost_factor: Optional[float] = Field(
        default=None, ge=0.05, le=1.0,
        description="How expensive services are relative to personal time [0=free, 1=very costly].",
    )
    social_conformity_pressure: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="How strongly peer behaviour influences individual choices [0=none, 1=strong].",
    )
    tasks_per_step_mean: Optional[float] = Field(
        default=None, ge=1.0, le=6.0,
        description="Average number of daily tasks each person faces.",
    )
    num_agents: Optional[int] = Field(
        default=None, ge=20, le=500,
        description="Approximate population size for this scenario.",
    )
    scenario_summary: str = Field(
        default="Custom scenario",
        description="A one-sentence summary of the scenario for display in the dashboard.",
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of why these parameter values were chosen.",
    )


class AgentProfileOutput(BaseModel):
    """Output schema for Role 2 — Agent Profile Generator.

    Defines the numerical attributes for one agent based on a natural
    language demographic description. All attributes are logged alongside
    the generating prompt for full auditability (white-box principle).
    """
    delegation_preference: float = Field(
        ge=0.02, le=0.98,
        description="How likely this agent is to delegate tasks [0–1].",
    )
    skill_domestic: float = Field(
        ge=0.3, le=0.9,
        description="Proficiency in domestic tasks (cooking, cleaning) [0.3–0.9].",
    )
    skill_administrative: float = Field(
        ge=0.3, le=0.9,
        description="Proficiency in administrative tasks (paperwork, scheduling) [0.3–0.9].",
    )
    skill_errand: float = Field(
        ge=0.3, le=0.9,
        description="Proficiency in errand tasks (shopping, deliveries) [0.3–0.9].",
    )
    skill_maintenance: float = Field(
        ge=0.3, le=0.9,
        description="Proficiency in maintenance tasks (repairs, DIY) [0.3–0.9].",
    )
    profile_description: str = Field(
        description="One sentence characterising this agent type for display.",
    )

    def to_skill_set(self) -> dict[str, float]:
        """Convert profile to the skill_set dict format expected by Resident."""
        return {
            "domestic": self.skill_domestic,
            "administrative": self.skill_administrative,
            "errand": self.skill_errand,
            "maintenance": self.skill_maintenance,
        }


class ResultInterpretation(BaseModel):
    """Output schema for Role 3 — Result Interpreter.

    A narrative explanation of simulation results in response to a user question.
    Structured to ensure the LLM provides both an answer and a reasoning trace.

    All fields except `answer` have defaults to tolerate LLM outputs that omit
    optional fields despite constrained decoding (observed with Qwen 3.5 4B).
    """
    answer: str = Field(
        description="Direct, concise answer to the user's question (1–3 sentences).",
    )
    detailed_explanation: str = Field(
        default="",
        description="Longer explanation of what the data shows and why (2–4 sentences).",
    )
    hypothesis_connection: str = Field(
        default="",
        description="Which of H1–H4 this observation relates to, if any.",
    )
    confidence_note: str = Field(
        default="",
        description="Any caveats about model limitations or result uncertainty.",
    )


class VisualizationAnnotation(BaseModel):
    """Output schema for Role 4 — Visualization Annotator.

    Auto-generated caption and insight for a dashboard chart.

    All fields have defaults to tolerate partial LLM outputs gracefully.
    """
    chart_title: str = Field(
        default="",
        description="A clear, descriptive title for the chart (max 60 chars).",
        max_length=60,
    )
    caption: str = Field(
        default="",
        description="2–3 sentence caption explaining what the chart shows.",
    )
    key_insight: str = Field(
        default="",
        description="The single most important observation from this chart (1 sentence).",
    )
    hypothesis_tag: Optional[str] = Field(
        default=None,
        description="Which hypothesis (H1/H2/H3/H4) this chart most directly informs.",
    )
