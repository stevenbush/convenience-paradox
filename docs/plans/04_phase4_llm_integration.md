# Phase 4: LLM Integration (Days 8-10)

**Goal**: All 4 peripheral LLM roles operational, chat interface on dashboard.

## Tasks

### Day 8: LLM Service Layer and Scenario Parser

- [ ] Implement LLM service layer (`api/llm_service.py`):
  - Ollama client wrapper with configurable model selection
  - Think mode control (disable for structured output, enable for interpretation)
  - Error handling and timeout management
  - Logging of all LLM interactions (prompt + response) for auditability
- [ ] Define Pydantic schemas (`api/schemas.py`):
  - `SimulationParams`: schema for scenario parser output
  - `AgentProfile`: schema for agent profile generator output
  - `InterpretationRequest`: schema for result interpretation context
- [ ] Implement Role 1 -- Scenario Parser:
  - Accepts natural language scenario description
  - Uses Ollama structured output (format=schema) to produce SimulationParams JSON
  - Validates output against Pydantic model
  - Returns structured parameters to frontend

### Day 9: Result Interpreter and Profile Generator

- [ ] Implement Role 3 -- Result Interpreter:
  - Constructs context window from simulation data (summary statistics, key time-series slices)
  - Accepts user question about simulation results
  - Generates narrative explanation grounded in data
  - Supports follow-up questions within conversation context
- [ ] Implement Role 2 -- Agent Profile Generator:
  - Accepts demographic/social description
  - Generates diverse agent profiles as structured JSON (explicit numerical parameters)
  - Logs full prompt + output for auditability
  - Integrates with model initialization

### Day 10: Visualization Annotator, Chat UI, and Integration

- [ ] Implement Role 4 -- Visualization Annotator:
  - Receives chart data summary
  - Generates contextual caption and insight highlights
  - Auto-annotates key visualizations on dashboard
- [ ] Build chat UI widget (`static/js/chat.js`):
  - Chat panel embedded in dashboard (collapsible sidebar or modal)
  - Message history display
  - Input field with send button
  - Loading indicator during LLM inference
  - Mode selector: Scenario Input / Ask About Results
- [ ] Add Flask endpoints for chat:
  - `POST /api/chat/scenario` -- scenario parser
  - `POST /api/chat/interpret` -- result interpreter
  - `POST /api/chat/annotate` -- visualization annotator
  - `POST /api/llm/profiles` -- agent profile generation
- [ ] Test all 4 roles with Qwen 3.5 4B, verify structured output quality

## Deliverable

Dashboard with working LLM chat, natural language scenario input, annotated charts, and agent profile generation. All LLM interactions are logged.
