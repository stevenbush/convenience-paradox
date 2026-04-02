# LLM Role Probe Verification Guide

This guide shows how to verify the new LLM probe harness step by step.

## 1. Open the project root

```bash
cd "/Users/jason/Coding/Modeling Social Systems/Proj_Trial_Convenience_Paradox"
```

## 2. Activate the correct environment

```bash
eval "$(conda shell.zsh hook)"
conda activate convenience-paradox
python --version
```

Expected:

- Python should be `3.12.x`

## 3. Confirm Ollama is available

The probe harness is live-only. It will stop early if Ollama is not reachable.

```bash
ollama list
```

Check that the output includes:

- `qwen3.5:4b`
- `qwen3:1.7b`

If Ollama is not running, start it first in the way you normally use on this machine.

## 4. Run the offline regression checks first

These tests verify the recorder, harness, and mocked integrations without requiring live inference.

```bash
pytest tests/test_llm_audit.py tests/test_llm_service_audit.py tests/test_forums.py tests/test_llm_role_probe.py -q
pytest tests/test_llm_service.py tests/test_model.py -q -m "not ollama"
```

Expected:

- the first command should report `6 passed`
- the second command should report `59 passed, 3 deselected`

## 5. Run the live role probe

Use the baseline config first.

```bash
python analysis/llm_role_probe.py --roles all --tag baseline --seed 42
```

Expected terminal behavior:

- a final summary line with `Run ID`
- a `Manifest:` path under `data/results/llm_logs/<run_id>/manifest.json`
- a `Report:` path under `analysis/reports/`
- one artifact line per role

## 6. Locate the generated artifacts

List the newest run directory:

```bash
ls -td data/results/llm_logs/* | head -n 1
```

Inspect the run manifest:

```bash
python -m json.tool "$(ls -td data/results/llm_logs/* | head -n 1)/manifest.json"
```

You should see:

- `status: "completed"`
- `roles_completed`
- `llm_status`
- paths for each role artifact

## 7. Inspect the Markdown summary report

List the newest report:

```bash
ls -t analysis/reports/*llm_role_probe*.md | head -n 1
```

Open it with your editor, or print it:

```bash
sed -n '1,240p' "$(ls -t analysis/reports/*llm_role_probe*.md | head -n 1)"
```

Check that the report contains:

- a role-status table
- one section for each of the five roles
- `Input`, `Parsed Output`, and `Downstream Effect` blocks
- the manual review checklist for each role

## 8. Inspect each role artifact directly

Set the latest run directory:

```bash
RUN_DIR="$(ls -td data/results/llm_logs/* | head -n 1)"
echo "$RUN_DIR"
```

Then inspect each role file:

```bash
python -m json.tool "$RUN_DIR/role1_scenario_parser.json"
python -m json.tool "$RUN_DIR/role2_agent_profile.json"
python -m json.tool "$RUN_DIR/role3_result_interpreter.json"
python -m json.tool "$RUN_DIR/role4_visualization_annotator.json"
python -m json.tool "$RUN_DIR/role5_agent_forums.json"
```

## 9. What to verify in each role

### Role 1 — Scenario Parser

Check:

- `call.call_kind` is `scenario_parser`
- `call.raw_response` is present
- `call.schema_validation.valid` is `true`
- `parsed_output` contains scenario fields
- `downstream_effect.final_params` shows the merged parameters
- `downstream_effect.simulation_summary.latest_metrics` exists

Meaning:

- the LLM returned structured parameters
- those parameters were actually applied to a short simulation

### Role 2 — Agent Profile Generator

Check:

- `call.call_kind` is `profile_generator`
- `parsed_output` contains the generated skills and delegation preference
- `downstream_effect.decision_probe_results` exists
- each task row shows `effective_probability`, `random_draw`, and `delegated`

Meaning:

- the generated profile changed a real decision probe using the model's rule-based logic

### Role 3 — Result Interpreter

Check:

- `call.call_kind` is `result_interpreter`
- `input.context` matches the shared mini-simulation summary
- `parsed_output.answer` is non-empty
- `parsed_output.hypothesis_connection` and `confidence_note` are populated when appropriate

Meaning:

- the interpretation is grounded in actual simulation context, not an isolated prompt

### Role 4 — Visualization Annotator

Check:

- `call.call_kind` is `visualization_annotator`
- `input.chart_metrics` exists
- `parsed_output.chart_title`, `caption`, and `key_insight` are present
- `downstream_effect.chart_metrics_used` matches the input chart stats

Meaning:

- the annotation was generated from real chart summary data derived from the model

### Role 5 — Agent Forums

Check:

- the file contains `calls`, not just one `call`
- dialogue calls use `call_kind: forum_dialogue_turn`
- the outcome extraction uses `call_kind: forum_outcome_extraction`
- `downstream_effect.forum_session.groups[*].turns` contains the transcript
- `outcome` exists for the group
- `preference_updates` shows `before_preference`, `after_preference`, and `delta_applied`

Meaning:

- you can see both the language exchange and the actual parameter updates caused by it

## 10. How to judge whether the result is meaningful

This harness is for manual inspection, so use this checklist for each role:

- Was there a real LLM response, not an empty or fallback string?
- Did schema validation pass?
- Did the downstream effect block show a visible consequence in the experiment?
- Does the output look specific to the provided input rather than generic filler?

If one of these fails, inspect:

- `error`
- `schema_validation`
- `raw_response`
- the exact `messages`, `system_prompt`, or `user_prompt`

## 11. Useful rerun commands

Run only one role:

```bash
python analysis/llm_role_probe.py --roles 3 --tag role3_only --seed 42
```

Run a subset:

```bash
python analysis/llm_role_probe.py --roles 1,2,5 --tag subset --seed 42
```

Use a different config:

```bash
python analysis/llm_role_probe.py --roles all --tag alt --seed 42 --config analysis/configs/llm_role_probe_baseline.json
```

## 12. Known limitation during verification

The existing live pytest cases in `tests/test_llm_service.py` are marked `ollama`.
Run them only when Ollama is reachable:

```bash
pytest tests/test_llm_service.py -q -m ollama
```

If Ollama is offline, those live tests will fail even if the new harness code is correct.
