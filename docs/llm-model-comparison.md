# Local LLM Model Comparison: 1B–4B Parameter Range

**Target Hardware:** MacBook Pro M4 Pro, 24GB RAM  
**Runtime:** Ollama  
**Date:** March 2026  

## Use Cases

1. **Structured JSON output** — parsing natural language into simulation parameters via Pydantic schemas
2. **Narrative generation** — interpreting simulation data as readable stories
3. **Personality profiles** — generating diverse agent profiles as structured JSON
4. **Agent dialogue** — brief natural-language discussions between simulated agents

---

## Executive Summary

**Primary Recommendation: Qwen 3.5 4B** (`qwen3.5:4b`)  
**Secondary Recommendation: Qwen 3 4B** (`qwen3:4b`)  
**Budget/Speed Pick: Qwen 3 1.7B** (`qwen3:1.7b`)  
**Avoid for this project:** Llama 3.2 (poor tool calling), SmolLM2 (too limited), DeepSeek R1 distilled (reasoning-focused, not instruction-tuned)

---

## Detailed Model Comparison

### Tier 1: The 4B Class (Recommended)

#### Qwen 3.5 4B — BEST OVERALL

| Attribute | Value |
|---|---|
| Parameters | 4.66B |
| Q4_K_M size | 3.4 GB |
| Q8 size | ~5.3 GB |
| Context window | 256K tokens (1M extended) |
| Ollama tag | `qwen3.5:4b` or `qwen3.5:4b-q4_K_M` |
| License | Apache 2.0 |
| Languages | 201 languages |
| Multimodal | Yes (text + image) |

**Benchmarks (Thinking Mode):**
- MMLU-Pro: 79.1% (approaches Qwen3-30B's 80.9)
- GPQA Diamond: 76.2% (beats Qwen3-30B's 73.4)
- IFEval: 89.8% (excellent instruction following)

**Strengths:**
- Best-in-class reasoning for a 4B model — benchmark scores rival models 7x its size
- Native thinking mode enables chain-of-thought reasoning, which dramatically improves structured output accuracy
- Excellent instruction following (IFEval 89.8%) — critical for JSON schema adherence
- Multimodal support future-proofs the project
- 256K context is more than sufficient for all use cases
- Apache 2.0 license — fully permissive
- Massive multilingual support (201 languages) is excellent for culturally diverse agent profiles

**Weaknesses:**
- Released March 2026 — newest model, less community testing
- Thinking mode adds 15–25% latency (can be disabled with `/no_think` prefix)
- Slightly larger than Qwen 3 4B at Q4 quantization
- Agent dialogue quality will still be noticeably inferior to 7B+ models

**Estimated speed on M4 Pro:** ~30–40 tok/s (Q4_K_M)

**Verdict for your use cases:**
- Structured JSON: ★★★★☆ (excellent with schema-constrained output)
- Narrative generation: ★★★☆☆ (adequate but not literary)
- Personality profiles: ★★★★☆ (good diversity with proper prompting)
- Agent dialogue: ★★★☆☆ (functional but can feel formulaic)

---

#### Qwen 3 4B — STRONG ALTERNATIVE

| Attribute | Value |
|---|---|
| Parameters | 4B |
| Q4_K_M size | ~2.6 GB |
| Q8 size | ~4.5 GB |
| Context window | 32K tokens |
| Ollama tag | `qwen3:4b` or `qwen3:4b-q4_K_M` |
| License | Apache 2.0 |
| Languages | 119 languages |

**Benchmarks:**
- MMLU-Pro: ~70%
- Tool calling: Excellent (74% overall on agentic benchmarks at 1.7B — 4B is better)
- Native thinking/non-thinking mode support

**Strengths:**
- Proven and well-tested (released April 2025, extensive community use)
- Strong tool calling and structured output support
- Smaller download than Qwen 3.5 4B
- Excellent instruction following
- Dual thinking/non-thinking mode

**Weaknesses:**
- Shorter context window (32K vs 256K)
- Slightly lower benchmark scores than Qwen 3.5 4B
- Fewer supported languages (119 vs 201)
- No multimodal support

**Estimated speed on M4 Pro:** ~35–45 tok/s (Q4_K_M)

**Verdict for your use cases:**
- Structured JSON: ★★★★☆
- Narrative generation: ★★★☆☆
- Personality profiles: ★★★★☆
- Agent dialogue: ★★★☆☆

---

#### Gemma 3 4B — SOLID BUT OUTCLASSED

| Attribute | Value |
|---|---|
| Parameters | 4B |
| Q4_K_M size | ~3.3 GB |
| Context window | 128K tokens |
| Ollama tag | `gemma3:4b` |
| License | Gemma Terms of Use |
| Multimodal | Yes (image recognition) |

**Benchmarks:**
- MMLU-Pro: 43.6%
- GPQA Diamond: 30.8%
- IFEval: 90.2% (slightly above Qwen 3.5 4B)

**Strengths:**
- Excellent instruction following (IFEval 90.2%)
- Strong multimodal support
- 128K context window
- Good multilingual capability (a major focus for Gemma 3)
- Well-optimized for Apple Silicon

**Weaknesses:**
- Significantly lower reasoning benchmarks than Qwen models
- Struggles with negation logic and spatial reasoning
- Restrictive license compared to Apache 2.0
- MMLU-Pro nearly half of Qwen 3.5 4B's score

**Estimated speed on M4 Pro:** ~34 tok/s (measured benchmark)

**Verdict for your use cases:**
- Structured JSON: ★★★☆☆ (good instruction following, weaker reasoning)
- Narrative generation: ★★★☆☆
- Personality profiles: ★★★☆☆
- Agent dialogue: ★★★☆☆

---

#### Phi-4 Mini 3.8B — REASONING SPECIALIST

| Attribute | Value |
|---|---|
| Parameters | 3.8B |
| Q4_K_M size | ~2.5 GB |
| Context window | 128K tokens |
| Ollama tag | `phi4-mini:3.8b` |
| License | MIT |
| Multimodal | No (text only) |

**Benchmarks:**
- MMLU-Pro: 52.8%
- GPQA Diamond: 25.2%
- Strong on math and logic reasoning

**Strengths:**
- Excellent reasoning and math capabilities
- MIT license — most permissive
- Smallest memory footprint in the 4B class
- Supports function calling natively
- 128K context window

**Weaknesses:**
- Lower overall benchmark scores than Qwen 3.5 4B
- Text only — no vision capability
- Knowledge cutoff June 2024 (older training data)
- Can be verbose and overly structured in free-form text
- Weaker on creative/narrative tasks compared to Qwen

**Estimated speed on M4 Pro:** ~35 tok/s (measured benchmark)

**Verdict for your use cases:**
- Structured JSON: ★★★☆☆ (decent function calling, mid-tier accuracy)
- Narrative generation: ★★☆☆☆ (tends toward dry, analytical prose)
- Personality profiles: ★★★☆☆
- Agent dialogue: ★★☆☆☆ (formulaic, lacks personality)

---

### Tier 2: The 1.5B–3B Class (Viable for Budget/Speed)

#### Qwen 3 1.7B — BEST LIGHTWEIGHT OPTION

| Attribute | Value |
|---|---|
| Parameters | 1.7B |
| Q4_K_M size | ~1.2 GB |
| Q8 size | ~2.0 GB |
| Context window | 32K tokens |
| Ollama tag | `qwen3:1.7b` |
| License | Apache 2.0 |

**Key result:** Qwen3 1.7B scored 74% on agentic benchmarks vs Llama 3.2 3B's 15%. Despite being half the parameter count, it dramatically outperforms Llama for tool calling: 100% on coding tasks vs 0%, 80% on multi-step tool use vs 8%.

**Strengths:**
- Exceptional tool calling for its size — best-in-class for structured output among sub-2B models
- Thinking mode for improved reasoning
- Tiny memory footprint (~1.2 GB at Q4)
- Can run multiple instances simultaneously on 24GB RAM

**Weaknesses:**
- Chat baseline score only 50% (significantly worse than Llama 3.2 3B's 93% for pure conversation)
- Limited narrative quality — noticeable repetition and shallow reasoning
- 32K context window
- Agent dialogue will feel robotic and repetitive

**Estimated speed on M4 Pro:** ~60–80 tok/s (Q4_K_M)

**Verdict for your use cases:**
- Structured JSON: ★★★★☆ (surprisingly good with schema constraints)
- Narrative generation: ★★☆☆☆ (adequate for summaries, poor for stories)
- Personality profiles: ★★★☆☆ (workable with strong prompting)
- Agent dialogue: ★★☆☆☆ (noticeably formulaic)

---

#### Llama 3.2 3B Instruct — POOR FOR THIS PROJECT

| Attribute | Value |
|---|---|
| Parameters | 3B |
| Q4_K_M size | ~2.0 GB |
| Context window | 128K tokens |
| Ollama tag | `llama3.2:3b` |
| License | Llama 3.2 Community |

**Strengths:**
- Best pure chat quality in the 1B–3B range (93% chat baseline)
- Long context window (128K)
- Most natural conversational tone at this size
- Strong community and Meta backing

**Critical Weakness:** Catastrophically bad at tool calling (15% overall vs Qwen3 1.7B's 74%). Scored 0/6 on explicit tool tasks, 0/6 on coding, 0/6 on multi-step. This makes it unsuitable for structured JSON output via function calling.

**Verdict for your use cases:**
- Structured JSON: ★★☆☆☆ (poor tool calling, unreliable schema adherence)
- Narrative generation: ★★★☆☆ (natural tone but shallow)
- Personality profiles: ★★☆☆☆ (can't reliably produce structured output)
- Agent dialogue: ★★★★☆ (best conversational tone at this size)

**Note:** If you must use Llama in this range, pair it with grammar-constrained decoding (GBNF) via Ollama's structured output feature to force JSON compliance. But Qwen is simply better for your use cases.

---

#### Llama 3.2 1B Instruct

| Attribute | Value |
|---|---|
| Parameters | 1B |
| Q4_K_M size | ~0.7 GB |
| Ollama tag | `llama3.2:1b` |

Not recommended. Tool calling performance is even worse than 3B. Only useful as a baseline or for extremely constrained environments. MMLU-Pro 20%, MATH 500 14%.

---

#### Qwen 2.5 3B Instruct

| Attribute | Value |
|---|---|
| Parameters | 3B |
| Q4_K_M size | ~2.0 GB |
| Context window | 32K tokens |
| Ollama tag | `qwen2.5:3b` |

Superseded by Qwen 3 4B and Qwen 3 1.7B. Qwen 3.5 shows "consistent gains" over 2.5 across all metrics. Only consider if you need maximum stability with a well-tested model and don't want to use the newer Qwen 3/3.5 series. Still a reasonable choice but no longer best-in-class.

---

#### Qwen 2.5 1.5B Instruct

| Attribute | Value |
|---|---|
| Parameters | 1.5B |
| Ollama tag | `qwen2.5:1.5b` |

Superseded by Qwen 3 1.7B. The Qwen 3 generation adds thinking mode and substantially better tool calling. No reason to use this unless you need Qwen 2.5 specific fine-tuning compatibility.

---

### Tier 3: Specialized / Not Recommended

#### DeepSeek R1 Distill Qwen 1.5B

| Attribute | Value |
|---|---|
| Parameters | 1.5B |
| Ollama tag | `deepseek-r1:1.5b` |
| License | MIT |

**Why not recommended:** This model is optimized for chain-of-thought *reasoning* (math, logic), not instruction following or structured output. It was distilled specifically to transfer reasoning patterns, not general-purpose capabilities. It produces verbose `<think>` blocks before every response, which is wasteful for structured output tasks. The model explicitly warns it is "not recommended for JSON structured output" in its documentation.

---

#### SmolLM2 1.7B

| Attribute | Value |
|---|---|
| Parameters | 1.7B |
| Q4_K_M size | ~1.0 GB |
| Context window | 8K tokens |
| Ollama tag | `smollm2:1.7b` |

**Why not recommended for this project:**
- Only 8K context window (vs Qwen3 1.7B's 32K)
- IFEval 56.7 (much lower than Qwen models)
- MMLU-Pro 19.3 (very limited knowledge)
- Designed for on-device applications, not complex structured output
- Qwen3 1.7B is strictly superior for every use case in this project

---

#### Gemma 3 1B

| Attribute | Value |
|---|---|
| Parameters | 1B |
| Size | 0.8 GB |
| Ollama tag | `gemma3:1b` |

**Why not recommended:** Struggles with negation logic, spatial reasoning, and number parsing (e.g., "five thousand fifty six" → 556). Text-only at 1B. At this size, Qwen3 1.7B is significantly better.

---

#### Qwen 2.5 0.5B / Qwen 3 0.6B

Too small for reliable structured output. These models frequently hallucinate JSON fields, produce malformed schemas, and cannot maintain coherent multi-turn dialogue. Only useful for embedding or extremely simple classification tasks.

---

#### Mistral (No models in 1B–4B range)

Mistral's smallest model is Mistral Small 3 at 24B parameters. There are no Mistral models in the 1B–4B range. Not applicable for this comparison.

---

## Head-to-Head Summary Table

| Model | Params | Q4 Size | JSON Output | Instruction Following | Narrative Quality | Dialogue Quality | Speed (M4 Pro) | Ollama Tag |
|---|---|---|---|---|---|---|---|---|
| **Qwen 3.5 4B** | 4.66B | 3.4 GB | ★★★★☆ | ★★★★★ | ★★★☆☆ | ★★★☆☆ | ~35 tok/s | `qwen3.5:4b` |
| **Qwen 3 4B** | 4B | 2.6 GB | ★★★★☆ | ★★★★☆ | ★★★☆☆ | ★★★☆☆ | ~40 tok/s | `qwen3:4b` |
| **Gemma 3 4B** | 4B | 3.3 GB | ★★★☆☆ | ★★★★★ | ★★★☆☆ | ★★★☆☆ | ~35 tok/s | `gemma3:4b` |
| **Phi-4 Mini** | 3.8B | 2.5 GB | ★★★☆☆ | ★★★★☆ | ★★☆☆☆ | ★★☆☆☆ | ~35 tok/s | `phi4-mini:3.8b` |
| **Qwen 3 1.7B** | 1.7B | 1.2 GB | ★★★★☆ | ★★★☆☆ | ★★☆☆☆ | ★★☆☆☆ | ~70 tok/s | `qwen3:1.7b` |
| **Llama 3.2 3B** | 3B | 2.0 GB | ★★☆☆☆ | ★★★☆☆ | ★★★☆☆ | ★★★★☆ | ~40 tok/s | `llama3.2:3b` |
| **Llama 3.2 1B** | 1B | 0.7 GB | ★☆☆☆☆ | ★★☆☆☆ | ★★☆☆☆ | ★★☆☆☆ | ~90 tok/s | `llama3.2:1b` |
| **SmolLM2 1.7B** | 1.7B | 1.0 GB | ★★☆☆☆ | ★★☆☆☆ | ★★☆☆☆ | ★★☆☆☆ | ~70 tok/s | `smollm2:1.7b` |
| **DeepSeek R1 1.5B** | 1.5B | ~1.0 GB | ★☆☆☆☆ | ★★☆☆☆ | ★★☆☆☆ | ★☆☆☆☆ | ~70 tok/s | `deepseek-r1:1.5b` |

---

## Honest Quality Assessment: 1B–4B vs Larger Models

### What works well at 1B–4B:
- **Structured JSON output with schema constraints**: Ollama's constrained decoding forces valid JSON regardless of model quality. The model just needs to pick reasonable *values*. A 4B model with a well-defined Pydantic schema and clear prompts will reliably produce valid structured output. This is your strongest use case at this size.
- **Simple parameter extraction**: "Set population to 500 with a cooperation rate of 0.3" → JSON. Even 1.7B models handle this well.
- **Template-driven personality profiles**: With a clear schema and diverse prompt seeds, 4B models produce varied and reasonable profiles.

### What is noticeably degraded at 1B–4B:
- **Narrative interpretation**: Prose will be functional but not elegant. Expect repetitive sentence structures, limited vocabulary, and occasional logical gaps. A 4B model can summarize simulation results but won't write compelling stories about them.
- **Agent dialogue quality**: This is the biggest concern. Research shows a 39% average performance drop in multi-turn interactions even for large models. At 1B–4B:
  - Agents will sound similar to each other despite different personality prompts
  - Dialogue becomes formulaic after 2–3 exchanges
  - Models struggle to maintain distinct "voices" across a conversation
  - Cultural nuance and subtext are largely absent
  - Expect "committee report" tone rather than natural conversation

### Recommended mitigation strategies:
1. **Use Ollama's structured output (`format` parameter)** with JSON schemas for all structured output tasks — this guarantees schema compliance regardless of model intelligence
2. **Keep dialogue exchanges short** — 1–3 turns maximum per agent interaction
3. **Use strong system prompts** with explicit personality traits and speech patterns
4. **Pre-generate personality archetypes** rather than relying on the model to create truly diverse personalities
5. **Consider a hybrid approach**: Use Qwen 3.5 4B for all structured output tasks locally, but optionally call a larger API model (Claude, GPT-4o) for the agent dialogue forum when quality matters
6. **Use thinking mode** for complex parameter parsing, disable it (`/no_think`) for simple structured output to save latency

### RAM budget on 24GB M4 Pro:
With 24GB unified memory, you can comfortably run:
- Qwen 3.5 4B at Q4_K_M (3.4 GB) with plenty of headroom
- Multiple instances of Qwen 3 1.7B (1.2 GB each) for parallel agent simulation
- Even Q8 quantization of the 4B models (5.3 GB) with room to spare
- The OS and Ollama overhead typically consume 4–6 GB, leaving 18–20 GB for models

---

## Final Recommendation

### For this project specifically:

**Use Qwen 3.5 4B (`qwen3.5:4b`) as your primary model.** It dominates every relevant benchmark in the 1B–4B range, has the best instruction following, and its thinking mode significantly improves structured output accuracy. The Apache 2.0 license is ideal, and 201-language support adds cultural depth to agent profiles.

**Use Qwen 3 1.7B (`qwen3:1.7b`) as your fast/lightweight model** for high-throughput tasks like bulk personality generation or simple parameter extraction where speed matters more than quality. Its tool calling is exceptional for its size, and at ~1.2 GB you can run several instances.

**Do not use Llama 3.2 for this project.** Despite its conversational quality, Llama 3.2 in the 1B–3B range has catastrophically poor tool calling (15% vs Qwen's 74%). For structured JSON output — your most critical use case — Llama is the wrong choice at this size. The Llama advantage only emerges at 8B+ where it matches Qwen's instruction following.

### Why Qwen over Llama at 1B–4B:

The Qwen team specifically optimized their small models for agentic and tool-calling workloads. Llama 3.2's small models were designed primarily for on-device conversational AI. This architectural decision shows dramatically in benchmarks: Qwen3 1.7B achieves 100% on coding tool tasks where Llama 3.2 3B scores 0%. For a project centered on structured JSON output via Pydantic schemas, this difference is decisive.

### If you can tolerate slightly larger models:

Consider keeping **Qwen 3.5 9B** (`qwen3.5:9b`, ~6 GB at Q4) as an optional "quality" tier. On your 24GB M4 Pro it would run at ~20 tok/s and produce substantially better narratives and dialogue. You could route structured output tasks to the 4B model and narrative/dialogue tasks to the 9B model.
