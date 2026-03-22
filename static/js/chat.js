/**
 * static/js/chat.js — LLM Chat Widget (Phase 4 / Role 1 + Role 3)
 *
 * This file implements the AI assistant chat panel on the dashboard.
 * It handles:
 *   - Sending user messages to the Flask LLM endpoints (Phase 4, api/llm_service.py)
 *   - Displaying responses as styled chat bubbles
 *   - Detecting "scenario description" intent and routing to Role 1 (Scenario Parser)
 *   - Otherwise routing to Role 3 (Result Interpreter) for data analysis questions
 *
 * LLM Roles served by this widget:
 *   Role 1 (Scenario Parser) — POST /api/llm/parse_scenario
 *     Input: natural-language scenario description
 *     Output: structured JSON parameters → auto-applied to sliders on confirmation
 *
 *   Role 3 (Result Interpreter) — POST /api/llm/interpret
 *     Input: user question + simulation context (current model_data summary)
 *     Output: narrative explanation of simulation results
 *
 * The widget gracefully degrades if the LLM endpoints are not yet available:
 *   - If the API returns 404 (Phase 4 not complete), a friendly notice is shown.
 *   - If Ollama is offline, the API returns 503 and the widget shows a retry suggestion.
 *
 * Note on latency: Qwen 3.5 4B on M4 Pro produces ~60-80 tok/s.
 * A 200-token response takes approximately 2-3 seconds. The chat widget
 * shows a typing indicator during inference to signal activity.
 */

// ---------------------------------------------------------------------------
// Chat state
// ---------------------------------------------------------------------------

// Conversation history (for multi-turn context in Role 3)
const chatHistory = [];

// Maximum messages to send as context (prevent token overflow)
const MAX_HISTORY_CONTEXT = 6;

// ---------------------------------------------------------------------------
// Core send/receive loop
// ---------------------------------------------------------------------------

/**
 * sendChatMessage — Read the chat input, classify intent, call the right endpoint.
 *
 * Intent classification is simple heuristic-based:
 *   - "scenario" keywords → Role 1 (parse_scenario)
 *   - All other messages → Role 3 (interpret)
 *
 * The LLM on the server side does the real classification for structured parsing;
 * this client-side check just routes the HTTP request to the right endpoint.
 */
async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;

  // Show user's message in the chat window
  appendChatMessage('user', message);
  input.value = '';
  chatHistory.push({ role: 'user', content: message });

  // Show typing indicator while waiting for LLM
  const typingId = appendTypingIndicator();

  try {
    // Classify intent: "set up", "configure", "create a scenario" → Role 1
    const isScenarioRequest = /\b(set up|configure|create|make|scenario|parameters?|society that|world where)\b/i.test(message);

    if (isScenarioRequest) {
      await handleScenarioRequest(message, typingId);
    } else {
      await handleInterpretRequest(message, typingId);
    }
  } catch (e) {
    removeTypingIndicator(typingId);
    appendChatMessage('assistant', '⚠️ Could not reach the AI service. Is Ollama running? Try `ollama serve` in a terminal.', 'error');
    console.error('chat error:', e);
  }
}

// ---------------------------------------------------------------------------
// Role 1: Scenario Parser
// ---------------------------------------------------------------------------

/**
 * handleScenarioRequest — Send to Role 1 endpoint, then offer to apply the params.
 *
 * If the LLM successfully parses the scenario into structured parameters,
 * we show a confirmation card with the parsed values. On "Apply", the sliders
 * are updated to match (via onSliderChange calls in dashboard.js).
 *
 * @param {string} message - Raw user message describing the scenario
 * @param {string} typingId - DOM id of the typing indicator to remove
 */
async function handleScenarioRequest(message, typingId) {
  const res = await fetch('/api/llm/parse_scenario', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description: message }),
  });

  removeTypingIndicator(typingId);

  if (res.status === 404) {
    appendChatMessage('assistant', '🔧 Scenario parsing (LLM Role 1) is not yet active — it will be enabled in Phase 4.', 'info');
    return;
  }
  if (res.status === 503) {
    appendChatMessage('assistant', '⚠️ Ollama is not running. Start it with `ollama serve`.', 'error');
    return;
  }
  if (!res.ok) {
    const err = await res.json();
    appendChatMessage('assistant', `⚠️ Error: ${err.error || 'Unknown error from scenario parser.'}`, 'error');
    return;
  }

  const data = await res.json();
  const params = data.params;
  const rationale = data.rationale || '';

  // Build a "parsed parameters" confirmation card
  const paramsHtml = Object.entries(params).map(([k, v]) =>
    `<div style="display:flex;justify-content:space-between;font-size:10px;padding:2px 0">
       <span style="color:#555">${k.replace(/_/g, ' ')}</span>
       <span style="font-family:monospace;font-weight:600">${typeof v === 'number' ? v.toFixed(2) : v}</span>
     </div>`
  ).join('');

  const html = `
    <div>
      <p style="margin:0 0 8px">${rationale || 'Parsed scenario parameters:'}</p>
      <div style="background:#f5f5f5;border-radius:4px;padding:8px 10px;margin-bottom:8px">${paramsHtml}</div>
      <button onclick="applyParsedParams(${JSON.stringify(JSON.stringify(params))})"
              style="background:var(--accent);color:white;border:none;border-radius:4px;
                     padding:5px 12px;cursor:pointer;font-size:11px">
        ✅ Apply to Simulation
      </button>
    </div>`;

  appendChatMessage('assistant', html, 'card');
  chatHistory.push({ role: 'assistant', content: `Parsed scenario: ${JSON.stringify(params)}` });
}

/**
 * applyParsedParams — Apply LLM-parsed parameters to the dashboard sliders.
 * Called by the "Apply" button in the scenario confirmation card.
 *
 * @param {string} paramsJson - JSON string of parsed parameter object
 */
function applyParsedParams(paramsJson) {
  const params = JSON.parse(paramsJson);
  const sliderKeys = ['delegation_preference_mean', 'service_cost_factor',
                      'social_conformity_pressure', 'tasks_per_step_mean', 'num_agents'];
  for (const key of sliderKeys) {
    if (params[key] !== undefined) {
      onSliderChange(key, params[key]);
      const slider = document.getElementById(`slider-${key}`);
      if (slider) slider.value = params[key];
    }
  }
  // Signal that params came from LLM parsing
  activePreset = 'custom';
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('preset-custom').classList.add('active');

  appendChatMessage('system', '✅ Parameters applied. Click Initialise to start the simulation.');
}

// ---------------------------------------------------------------------------
// Role 3: Result Interpreter
// ---------------------------------------------------------------------------

/**
 * handleInterpretRequest — Send to Role 3 endpoint with data context.
 *
 * We include a brief summary of current simulation state as context so the
 * LLM can answer questions grounded in the actual run data.
 *
 * @param {string} message - User question about the simulation
 * @param {string} typingId - DOM id of the typing indicator to remove
 */
async function handleInterpretRequest(message, typingId) {
  // Gather a compact data context from the running simulation
  const context = await buildDataContext();

  const res = await fetch('/api/llm/interpret', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: message,
      context,
      history: chatHistory.slice(-MAX_HISTORY_CONTEXT),
    }),
  });

  removeTypingIndicator(typingId);

  if (res.status === 404) {
    appendChatMessage('assistant', '🔧 Result interpretation (LLM Role 3) will be enabled in Phase 4.', 'info');
    return;
  }
  if (res.status === 503) {
    appendChatMessage('assistant', '⚠️ Ollama is not running. Start it with `ollama serve`.', 'error');
    return;
  }
  if (!res.ok) {
    const err = await res.json();
    appendChatMessage('assistant', `⚠️ Error: ${err.error || 'Unknown error from interpreter.'}`, 'error');
    return;
  }

  const data = await res.json();
  const interpretation = data.interpretation || '';
  const caveats = data.caveats || [];

  let html = `<p style="margin:0 0 8px">${interpretation}</p>`;
  if (caveats.length > 0) {
    html += `<ul style="margin:0;padding-left:16px;font-size:10px;color:#666">
      ${caveats.map(c => `<li>${c}</li>`).join('')}
    </ul>`;
  }

  appendChatMessage('assistant', html, 'card');
  chatHistory.push({ role: 'assistant', content: interpretation });
}

/**
 * buildDataContext — Summarise the current simulation state for LLM context.
 * Returns a compact dict that the server includes in the LLM prompt.
 * This keeps token usage low while giving the LLM enough to reason about.
 *
 * @returns {Object} context summary or empty object if no simulation is running
 */
async function buildDataContext() {
  try {
    const res = await fetch('/api/simulation/status');
    if (!res.ok) return {};
    const status = await res.json();
    if (!status.initialised) return { status: 'No simulation initialised.' };

    // Fetch the last 5 steps of model data for context
    const dataRes = await fetch('/api/simulation/data?last_n=5');
    const data = dataRes.ok ? await dataRes.json() : {};
    const latest = data.model_data && data.model_data.length > 0
      ? data.model_data[data.model_data.length - 1] : null;

    return {
      current_step: status.current_step,
      preset: status.params?.preset || 'custom',
      params_summary: status.params || {},
      latest_metrics: latest,
    };
  } catch (e) {
    return {};
  }
}

// ---------------------------------------------------------------------------
// UI helper functions
// ---------------------------------------------------------------------------

/**
 * appendChatMessage — Add a message bubble to the chat window.
 *
 * @param {string} role    - 'user', 'assistant', 'system', or 'error'
 * @param {string} html    - Message content (HTML allowed for 'card' type)
 * @param {string} [type]  - Optional: 'card', 'info', 'error' for special styling
 */
function appendChatMessage(role, html, type) {
  const messages = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.style.cssText = `
    padding: 8px 10px;
    border-radius: 8px;
    font-size: 12px;
    line-height: 1.5;
    max-width: 90%;
    word-break: break-word;
  `;

  if (role === 'user') {
    div.style.cssText += `
      background: var(--accent);
      color: white;
      align-self: flex-end;
      margin-left: auto;
    `;
    div.textContent = html;
  } else if (role === 'system') {
    div.style.cssText += `
      background: #e8f4ea;
      color: #2a7a2e;
      font-size: 11px;
      text-align: center;
      width: 100%;
    `;
    div.textContent = html;
  } else if (type === 'error') {
    div.style.cssText += `
      background: #fff0f0;
      color: #c0392b;
      border: 1px solid #fcc;
    `;
    div.textContent = html;
  } else if (type === 'info') {
    div.style.cssText += `
      background: #f0f4ff;
      color: #1a3a7a;
      border: 1px solid #c8d8ff;
      font-style: italic;
    `;
    div.textContent = html;
  } else if (type === 'card') {
    div.style.cssText += `background: #f9f9f9; border: 1px solid #e5e5e5;`;
    div.innerHTML = html;
  } else {
    div.style.cssText += `background: var(--dark-bg); color: var(--dark-text);`;
    div.innerHTML = html;
  }

  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

/**
 * appendTypingIndicator — Show animated "..." while waiting for the LLM.
 * Returns a unique id so the caller can remove the indicator when done.
 *
 * @returns {string} DOM id of the indicator element
 */
function appendTypingIndicator() {
  const id = 'typing-' + Date.now();
  const messages = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.id = id;
  div.style.cssText = 'padding:8px 10px;border-radius:8px;background:var(--dark-bg);color:var(--dark-muted);font-size:12px;font-style:italic;';
  div.textContent = '🤖 Thinking…';
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return id;
}

/** removeTypingIndicator — Remove the typing indicator by its DOM id. */
function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}
