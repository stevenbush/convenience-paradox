"""model/forums.py — Agent Communication Forums (Phase 5 Experimental Feature)

This module implements "Agent Communication Forums" — the experimental
LLM-in-loop simulation mode described in the master plan (§2, Role 5).

Architecture position:
    Unlike Roles 1–4 (which operate at the input/output periphery), forums
    sit inside the simulation loop. This moves the LLM from "white-box" to
    "grey-box" territory — hence the explicit experimental labelling in the
    dashboard UI and the strict norm-update bounds applied to forum outcomes.

How it works:
    1. At the start of each forum step, a random sample of agents is divided
       into small groups (size 2–3).
    2. Each group participates in a brief dialogue (1–3 turns) via Ollama.
       The LLM generates persona-appropriate responses for each agent.
    3. The dialogue is parsed to extract a "norm signal": a directional
       influence on delegation_preference (positive = more delegation,
       negative = less delegation).
    4. Each participating agent's delegation_preference is updated by a
       small amount (capped at ±NORM_UPDATE_CAP to prevent LLM from
       dominating the simulation dynamics).
    5. All dialogues and norm updates are logged in the ForumSession record
       for the audit trail displayed on the dashboard.

White-box vs. grey-box trade-off:
    Standard mode:  delegation_preference ← rule-based (adaptation_rate × conformity)
    Forum mode:     delegation_preference ← rule-based + small LLM norm signal
                    The LLM's influence is additive and bounded.
                    The dashboard shows both modes side-by-side for comparison.
    This design is intentional: it lets users see the difference between
    rule-based norm evolution and LLM-influenced norm evolution, demonstrating
    the interpretability trade-off discussed in Vanhee et al. (2507.05723).

Limitations at Qwen 3.5 4B:
    - Agents at this model size may sound similar to each other.
    - Dialogue becomes repetitive after 2-3 exchanges.
    - These limitations are displayed in the dashboard's experimental notice.
    See: master plan §2 "Honest Quality Trade-offs at 1B–4B".

See also:
    - api/llm_service.py  — the peripheral LLM roles (non-experimental)
    - model/agents.py     — Resident agent class (delegation_preference field)
"""

from __future__ import annotations

import json
import logging
import os
import random
import textwrap
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

import ollama
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from api.llm_audit import LlmAuditRecorder
    from model.agents import Resident

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# LLM model for forum dialogues. Follows the same env-var pattern as llm_service.py.
# Override: LLM_PRIMARY_MODEL=your-model:tag python run.py
FORUM_MODEL = os.environ.get("LLM_PRIMARY_MODEL", "qwen3.5:4b")

# Maximum absolute change to delegation_preference per forum session.
# This cap ensures the LLM cannot dominate simulation dynamics.
NORM_UPDATE_CAP = 0.06

# Default fraction of agents invited to the forum per step.
# 0.2 = 20% of agents, keeping per-step cost modest.
DEFAULT_FORUM_FRACTION = 0.20

# Default group size for dialogue sessions.
DEFAULT_GROUP_SIZE = 2

# Default number of dialogue turns per group.
DEFAULT_NUM_TURNS = 2


# ---------------------------------------------------------------------------
# Pydantic schemas for forum outputs
# ---------------------------------------------------------------------------

class ForumOutcome(BaseModel):
    """Structured output from a forum dialogue group.

    The LLM extracts:
    - norm_signal: direction of consensus from the dialogue [-1, +1].
      Positive = group moved toward delegation (more service use).
      Negative = group moved toward autonomy (more self-service).
    - confidence: how strong/clear the consensus was [0, 1].
    - summary: one-sentence description of the dialogue outcome.

    The actual delta applied to delegation_preference is:
        delta = norm_signal * confidence * NORM_UPDATE_CAP
    """
    norm_signal: float = Field(
        ge=-1.0, le=1.0,
        description="Direction and strength of norm influence: +1 = toward delegation, "
                    "-1 = toward autonomy. 0 = no consensus.",
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="How strongly/clearly the group reached a consensus [0–1].",
    )
    summary: str = Field(
        description="One sentence summarising the dialogue's norm conclusion.",
    )


# ---------------------------------------------------------------------------
# Data structures for forum records
# ---------------------------------------------------------------------------

@dataclass
class DialogueTurn:
    """One turn in a group dialogue session."""
    speaker_id: int           # Agent unique_id
    speaker_label: str        # Short persona description
    content: str              # What the agent said


@dataclass
class GroupSession:
    """Record of one group's forum dialogue session."""
    step: int                 # Simulation step at which forum occurred
    agent_ids: list[int]      # Participating agent unique_ids
    turns: list[DialogueTurn] # The full dialogue transcript
    outcome: Optional[ForumOutcome] = None  # Extracted norm signal
    delta_applied: float = 0.0             # Actual delta applied to delegation_preference
    preference_updates: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ForumSession:
    """Record of one full forum event (all groups in one simulation step).

    Stored in the model's `forum_log` for display in the dashboard audit trail.
    """
    step: int
    groups: list[GroupSession] = field(default_factory=list)
    n_agents_participating: int = 0
    total_norm_updates: int = 0
    elapsed_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

FORUM_SYSTEM_PROMPT = textwrap.dedent("""\
    You are simulating a conversation between residents of an abstract society.
    These residents are discussing whether people should handle their own
    daily tasks (cooking, cleaning, errands) or delegate them to paid services.

    Each resident has a persona based on their situation. They speak naturally,
    share their perspective, and may be influenced by what others say.

    Rules:
    - Keep each response to 1–3 sentences. Be concise.
    - Speak in first person as the character.
    - Do NOT name specific countries, cities, or cultures.
    - Stay in character based on the persona description.
""")

OUTCOME_EXTRACTION_PROMPT = textwrap.dedent("""\
    You just observed this dialogue between residents discussing service delegation:

    {transcript}

    Based on this dialogue, extract the norm signal:
    - norm_signal: Did the conversation lean toward MORE delegation (+0.5 to +1.0),
      LESS delegation (-0.5 to -1.0), or NO clear consensus (near 0)?
    - confidence: How clear/strong was the consensus? [0.0 to 1.0]
    - summary: One sentence describing the dialogue's conclusion about delegation norms.

    Output ONLY valid JSON matching the specified schema.
""")


# ---------------------------------------------------------------------------
# Core forum functions
# ---------------------------------------------------------------------------

def _build_agent_persona(agent: "Resident") -> str:
    """Construct a brief persona description for the agent from its attributes.

    The persona is written in abstract terms (no country references) and
    describes the agent's lifestyle in terms relevant to task delegation.
    This is what the LLM receives as character context.

    Args:
        agent: A Resident agent from the simulation.

    Returns:
        A one-paragraph persona description string.
    """
    # Map delegation_preference to a lifestyle description.
    if agent.delegation_preference > 0.70:
        lifestyle = "busy professional who delegates most household tasks"
    elif agent.delegation_preference > 0.45:
        lifestyle = "moderate person who sometimes uses services but also handles tasks personally"
    else:
        lifestyle = "self-reliant individual who prefers to handle daily tasks independently"

    # Map stress to a wellbeing description.
    stress_desc = "stressed and time-poor" if agent.stress_level > 0.5 else (
        "moderately busy" if agent.stress_level > 0.2 else "relaxed and comfortable"
    )

    # Map income to economic framing.
    if agent.income > 0.3:
        econ = "has sufficient income for occasional services"
    elif agent.income > -0.1:
        econ = "watches spending carefully"
    else:
        econ = "finds services financially challenging"

    return (
        f"Resident #{agent.unique_id % 100}: A {lifestyle}. "
        f"Currently {stress_desc}. {econ.capitalize()}. "
        f"Delegation preference: {agent.delegation_preference:.0%}."
    )


def _run_group_dialogue(
    agents: list["Resident"],
    step: int,
    num_turns: int,
    recorder: Optional["LlmAuditRecorder"] = None,
    llm_model: Optional[str] = None,
) -> GroupSession:
    """Run one group's forum dialogue via Ollama.

    Each agent takes `num_turns` turns in sequence. The LLM is called
    once per turn with the full transcript so far as context, producing
    the next agent's response.

    After the dialogue, a second LLM call extracts the ForumOutcome.

    Args:
        agents: The participating Resident agents (2–3).
        step: Current simulation step (for the session record).
        num_turns: Number of dialogue turns per agent.

    Returns:
        A GroupSession record with the full dialogue and outcome.
    """
    personas = {a.unique_id: _build_agent_persona(a) for a in agents}
    session = GroupSession(step=step, agent_ids=[a.unique_id for a in agents], turns=[])

    # Build conversation history across all turns.
    transcript_lines = []
    messages = [{"role": "system", "content": FORUM_SYSTEM_PROMPT}]

    # Opening topic prompt for the first speaker.
    topic = (
        "The topic today: Should people in our neighbourhood use more paid services "
        "for daily tasks, or should we handle them ourselves? What do you think?"
    )
    messages.append({"role": "user", "content": topic})

    # Rotate through agents for each turn.
    agent_cycle = agents * num_turns

    for i, agent in enumerate(agent_cycle):
        persona = personas[agent.unique_id]
        # Inject persona as the current speaker context.
        speaker_prompt = f"You are: {persona}\n\nPlease respond to the ongoing discussion."
        if i > 0:
            speaker_prompt = f"You are: {persona}\n\nRespond to what was just said."

        use_model = llm_model or FORUM_MODEL
        call_messages = messages + [{"role": "user", "content": speaker_prompt}]
        t0 = time.perf_counter()
        try:
            resp = ollama.chat(
                model=use_model,
                messages=call_messages,
                options={"num_predict": 120, "temperature": 0.7, "top_p": 0.9},
                think=False,
            )
            content = resp.message.content.strip()
            if not content:
                content = "[No response generated]"
            if recorder:
                recorder.record_call(
                    role="role_5",
                    call_kind="forum_dialogue_turn",
                    model=use_model,
                    think=False,
                    messages=call_messages,
                    raw_response=content,
                    elapsed_seconds=time.perf_counter() - t0,
                    extra={
                        "step": step,
                        "speaker_id": agent.unique_id,
                        "group_agent_ids": [a.unique_id for a in agents],
                    },
                )
        except Exception as e:
            logger.warning("Forum dialogue LLM call failed: %s", e)
            content = "[Connection error during dialogue]"
            if recorder:
                recorder.record_call(
                    role="role_5",
                    call_kind="forum_dialogue_turn",
                    model=use_model,
                    think=False,
                    messages=call_messages,
                    raw_response=None,
                    elapsed_seconds=time.perf_counter() - t0,
                    error=e,
                    extra={
                        "step": step,
                        "speaker_id": agent.unique_id,
                        "group_agent_ids": [a.unique_id for a in agents],
                    },
                )

        turn = DialogueTurn(
            speaker_id=agent.unique_id,
            speaker_label=persona.split(":")[1].strip()[:60],
            content=content,
        )
        session.turns.append(turn)
        transcript_lines.append(f"Resident #{agent.unique_id % 100}: {content}")

        # Add this turn to the conversation history for subsequent speakers.
        messages.append({"role": "assistant", "content": content})

    # Extract norm signal from the completed dialogue.
    transcript_str = "\n".join(transcript_lines)
    outcome = _extract_forum_outcome(
        transcript_str,
        recorder=recorder,
        step=step,
        agent_ids=[a.unique_id for a in agents],
        llm_model=llm_model,
    )
    session.outcome = outcome

    return session


def _extract_forum_outcome(
    transcript: str,
    recorder: Optional["LlmAuditRecorder"] = None,
    step: int | None = None,
    agent_ids: Optional[list[int]] = None,
    llm_model: Optional[str] = None,
) -> Optional[ForumOutcome]:
    """Run the outcome extraction LLM call and parse the ForumOutcome.

    This is a separate, structured call from the dialogue itself.
    Uses constrained JSON decoding to guarantee schema compliance.

    Args:
        transcript: The full dialogue transcript as a string.

    Returns:
        ForumOutcome if successful; None if LLM call fails.
    """
    use_model = llm_model or FORUM_MODEL
    prompt = OUTCOME_EXTRACTION_PROMPT.format(transcript=transcript[:1200])
    t0 = time.perf_counter()
    messages = [{"role": "user", "content": prompt}]
    content = ""

    try:
        resp = ollama.chat(
            model=use_model,
            messages=messages,
            format=ForumOutcome.model_json_schema(),
            options={"num_predict": 200, "temperature": 0.2},
            think=False,
        )
        content = resp.message.content
        if not content:
            if recorder:
                recorder.record_call(
                    role="role_5",
                    call_kind="forum_outcome_extraction",
                    model=use_model,
                    think=False,
                    messages=messages,
                    raw_response=content,
                    schema_validation={
                        "schema": "ForumOutcome",
                        "valid": False,
                        "error": "Empty response",
                    },
                    elapsed_seconds=time.perf_counter() - t0,
                    error=RuntimeError("Empty forum outcome response."),
                    extra={"step": step, "group_agent_ids": agent_ids},
                )
            return None
        data = json.loads(content)
        outcome = ForumOutcome(**data)
        if recorder:
            recorder.record_call(
                role="role_5",
                call_kind="forum_outcome_extraction",
                model=use_model,
                think=False,
                messages=messages,
                raw_response=content,
                parsed_output=outcome.model_dump(),
                schema_validation={
                    "schema": "ForumOutcome",
                    "valid": True,
                    "error": None,
                },
                elapsed_seconds=time.perf_counter() - t0,
                extra={"step": step, "group_agent_ids": agent_ids},
            )
        return outcome
    except Exception as e:
        logger.warning("Forum outcome extraction failed: %s", e)
        if recorder:
            recorder.record_call(
                role="role_5",
                call_kind="forum_outcome_extraction",
                model=use_model,
                think=False,
                messages=messages,
                raw_response=content or None,
                schema_validation={
                    "schema": "ForumOutcome",
                    "valid": False,
                    "error": str(e),
                },
                elapsed_seconds=time.perf_counter() - t0,
                error=e,
                extra={"step": step, "group_agent_ids": agent_ids},
            )
        return None


def run_forum_step(
    model: Any,
    forum_fraction: float = DEFAULT_FORUM_FRACTION,
    group_size: int = DEFAULT_GROUP_SIZE,
    num_turns: int = DEFAULT_NUM_TURNS,
    recorder: Optional["LlmAuditRecorder"] = None,
    rng_seed: int | None = None,
    llm_model: Optional[str] = None,
) -> ForumSession:
    """Run one forum event for a subset of the model's agents.

    This is called by the forum-enhanced simulation mode from the Flask API
    endpoint (POST /api/simulation/forum_step).

    The function:
    1. Selects a random fraction of agents to participate.
    2. Divides them into groups of `group_size`.
    3. Runs each group's dialogue in sequence (parallel possible but adds complexity).
    4. Applies the bounded norm updates to each agent's delegation_preference.
    5. Returns a ForumSession record for the audit trail.

    Args:
        model: The active ConvenienceParadoxModel instance.
        forum_fraction: Fraction of agents to include [0, 1]. Default 0.20.
        group_size: Agents per dialogue group. Default 2.
        num_turns: Dialogue turns per agent. Default 2.

    Returns:
        ForumSession record containing all group dialogues and norm updates.
    """
    t0 = time.perf_counter()
    all_agents = list(model.agents)
    n_invite = max(group_size, int(len(all_agents) * forum_fraction))
    n_invite = min(n_invite, len(all_agents))

    # Random sample of agents for this forum event.
    rng = random.Random(rng_seed) if rng_seed is not None else random
    participants = rng.sample(all_agents, n_invite)

    # Divide into groups of group_size.
    groups_agents: list[list] = [
        participants[i:i + group_size]
        for i in range(0, len(participants), group_size)
    ]
    # Drop incomplete groups (last group may be short)
    groups_agents = [g for g in groups_agents if len(g) >= 2]

    session = ForumSession(
        step=model.current_step,
        n_agents_participating=n_invite,
    )

    for group in groups_agents:
        group_session = _run_group_dialogue(
            group,
            model.current_step,
            num_turns,
            recorder=recorder,
            llm_model=llm_model,
        )
        session.groups.append(group_session)

        # Apply bounded norm update to each participating agent.
        if group_session.outcome:
            outcome = group_session.outcome
            delta = outcome.norm_signal * outcome.confidence * NORM_UPDATE_CAP
            group_session.delta_applied = delta
            session.total_norm_updates += len(group)

            for agent in group:
                # Apply update and clamp to [0.02, 0.98] (same bounds as normal adaptation).
                before = agent.delegation_preference
                new_pref = agent.delegation_preference + delta
                agent.delegation_preference = max(0.02, min(0.98, new_pref))
                group_session.preference_updates.append({
                    "agent_id": agent.unique_id,
                    "before_preference": round(before, 6),
                    "after_preference": round(agent.delegation_preference, 6),
                    "delta_applied": round(agent.delegation_preference - before, 6),
                })

            logger.debug(
                "Forum group [%s] | norm=%.2f | conf=%.2f | delta=%.3f",
                [a.unique_id for a in group],
                outcome.norm_signal,
                outcome.confidence,
                delta,
            )

    session.elapsed_seconds = time.perf_counter() - t0
    logger.info(
        "Forum step %d | groups=%d | agents=%d | elapsed=%.1fs",
        model.current_step, len(session.groups),
        session.n_agents_participating, session.elapsed_seconds,
    )
    return session


def format_session_for_api(session: ForumSession) -> dict:
    """Serialise a ForumSession to a JSON-compatible dict for the Flask API.

    This is the format returned by POST /api/simulation/forum_step and
    GET /api/simulation/forum_log. Used by the dashboard to display the
    audit trail of all forum dialogues.

    Args:
        session: ForumSession to serialise.

    Returns:
        Dict with groups, turns, outcomes, and norm updates.
    """
    groups_out = []
    for g in session.groups:
        groups_out.append({
            "agent_ids": g.agent_ids,
            "turns": [
                {
                    "speaker_id": t.speaker_id,
                    "speaker_label": t.speaker_label,
                    "content": t.content,
                }
                for t in g.turns
            ],
            "outcome": g.outcome.model_dump() if g.outcome else None,
            "delta_applied": round(g.delta_applied, 4),
            "preference_updates": g.preference_updates,
        })

    return {
        "step": session.step,
        "n_agents_participating": session.n_agents_participating,
        "total_norm_updates": session.total_norm_updates,
        "elapsed_seconds": round(session.elapsed_seconds, 2),
        "groups": groups_out,
    }
