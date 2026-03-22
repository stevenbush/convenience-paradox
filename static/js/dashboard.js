/**
 * static/js/dashboard.js — Dashboard Controller and Plotly.js Visualisations
 *
 * This file drives all interactive behaviour on the dashboard:
 *   - Fetching simulation data from the Flask REST API
 *   - Rendering and updating Plotly.js charts
 *   - Handling preset selection, slider changes, and control buttons
 *   - Loading run history and overlaying past runs on charts
 *
 * Architecture:
 *   The dashboard is stateless HTML; all simulation state lives server-side.
 *   This file only fetches and renders data — it never holds a model instance.
 *   Every action (init, step, run, reset) is a fetch() call to api/routes.py.
 *
 * Chart inventory (what each chart shows and which hypothesis it addresses):
 *   #chart-timeseries    — avg_stress, avg_delegation_rate, social_efficiency over time (H1·H3·H4)
 *   #chart-labour        — total_labor_hours over time (H1: does delegation increase work?)
 *   #chart-efficiency    — social_efficiency over time (H2: threshold to involution spiral?)
 *   #chart-stress-dist   — histogram of current agent stress_level (H3: well-being distribution)
 *   #chart-delegation-dist — histogram of current delegation_preference (H4: norm convergence?)
 *   #chart-gini          — gini_income over time (inequality exploratory)
 *
 * Colour conventions (matching analysis/plots.py):
 *   Type A (Autonomy) → #2166AC (blue)
 *   Type B (Convenience) → #D6604D (red)
 *   Current run → #4DAF4A (green) or theme accent
 */

// ---------------------------------------------------------------------------
// State: current parameter values (reflects sliders or applied preset)
// ---------------------------------------------------------------------------
let currentParams = {
  num_agents: 100,
  delegation_preference_mean: 0.50,
  delegation_preference_std: 0.10,
  service_cost_factor: 0.40,
  social_conformity_pressure: 0.30,
  tasks_per_step_mean: 2.50,
  tasks_per_step_std: 0.75,
  stress_threshold: 2.5,
  stress_recovery_rate: 0.10,
  adaptation_rate: 0.03,
  initial_available_time: 8.0,
  network_type: 'small_world',
  seed: 42,
};

// Track which preset is active so we can highlight the button.
let activePreset = null;

// Guard flag: suppresses the "revert to Custom" behaviour in onSliderChange
// while applyPreset is programmatically updating slider values.
let _applyingPreset = false;

// Overlay traces for past runs (run_id → {name, color, data})
const overlayRuns = {};

// Colour palette for overlay runs (cycle through on each new addition)
const OVERLAY_COLORS = ['#984EA3', '#FF7F00', '#A65628', '#F781BF', '#999999'];
let overlayColorIdx = 0;

// ---------------------------------------------------------------------------
// Plotly layout defaults (shared across all time-series charts)
// ---------------------------------------------------------------------------
const LAYOUT_DEFAULTS = {
  margin: { t: 10, r: 10, b: 40, l: 50 },
  paper_bgcolor: 'white',
  plot_bgcolor: 'white',
  font: { family: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif', size: 11 },
  xaxis: { gridcolor: '#eee', zerolinecolor: '#ddd', title: { text: 'Simulation Day', font: { size: 11 } } },
  yaxis: { gridcolor: '#eee', zerolinecolor: '#ddd' },
  legend: { orientation: 'h', y: -0.2, font: { size: 10 } },
  hovermode: 'x unified',
  autosize: true,
};

const PLOTLY_CONFIG = { responsive: true, displayModeBar: false };

// ---------------------------------------------------------------------------
// Chart initialisation (empty charts on page load)
// ---------------------------------------------------------------------------

/**
 * initCharts — Create empty Plotly chart containers.
 * Called once on page load. Charts are populated with data after the user
 * initialises a simulation and calls fetchAndUpdateCharts().
 */
function initCharts() {
  // Chart 1: Primary time-series (avg_stress, avg_delegation_rate, social_efficiency)
  // This is the central diagnostic chart — all three key metrics on one canvas.
  Plotly.newPlot('chart-timeseries', [], {
    ...LAYOUT_DEFAULTS,
    yaxis: { ...LAYOUT_DEFAULTS.yaxis, title: { text: 'Value', font: { size: 11 } }, range: [0, 1] },
  }, PLOTLY_CONFIG);

  // Chart 2: Total labour hours — the H1 test variable.
  // We expect this to rise with delegation as provider overhead accumulates.
  Plotly.newPlot('chart-labour', [], {
    ...LAYOUT_DEFAULTS,
    yaxis: { ...LAYOUT_DEFAULTS.yaxis, title: { text: 'Hours / day', font: { size: 11 } } },
  }, PLOTLY_CONFIG);

  // Chart 3: Social efficiency — tasks completed per collective labour-hour.
  // Involution manifests as a falling curve (more time spent, less output per hour).
  Plotly.newPlot('chart-efficiency', [], {
    ...LAYOUT_DEFAULTS,
    yaxis: { ...LAYOUT_DEFAULTS.yaxis, title: { text: 'Tasks / labour-hour', font: { size: 11 } } },
  }, PLOTLY_CONFIG);

  // Chart 4: Stress distribution histogram — agent-level well-being at the current step.
  // H3: Type A should show a left-skewed (low-stress) distribution at equilibrium.
  Plotly.newPlot('chart-stress-dist', [], {
    ...LAYOUT_DEFAULTS,
    xaxis: { ...LAYOUT_DEFAULTS.xaxis, title: { text: 'Stress Level [0–1]', font: { size: 11 } }, range: [0, 1] },
    yaxis: { ...LAYOUT_DEFAULTS.yaxis, title: { text: 'Number of Agents', font: { size: 11 } } },
    legend: {},
    hovermode: 'x',
    bargap: 0.05,
  }, PLOTLY_CONFIG);

  // Chart 5: Delegation preference distribution — the norm landscape.
  // H4: A moderate-delegation society should show a bimodal or drift distribution
  // as agents conform to local network norms rather than holding the initial mean.
  Plotly.newPlot('chart-delegation-dist', [], {
    ...LAYOUT_DEFAULTS,
    xaxis: { ...LAYOUT_DEFAULTS.xaxis, title: { text: 'Delegation Preference [0–1]', font: { size: 11 } }, range: [0, 1] },
    yaxis: { ...LAYOUT_DEFAULTS.yaxis, title: { text: 'Number of Agents', font: { size: 11 } } },
    legend: {},
    hovermode: 'x',
    bargap: 0.05,
  }, PLOTLY_CONFIG);

  // Chart 6: Income Gini over time — inequality of earnings from service provision.
  // Higher Gini indicates income concentration among service providers.
  Plotly.newPlot('chart-gini', [], {
    ...LAYOUT_DEFAULTS,
    yaxis: { ...LAYOUT_DEFAULTS.yaxis, title: { text: 'Gini Coefficient [0–1]', font: { size: 11 } }, range: [0, 1] },
  }, PLOTLY_CONFIG);
}

// ---------------------------------------------------------------------------
// Data fetch and chart update
// ---------------------------------------------------------------------------

/**
 * fetchAndUpdateCharts — Fetch current simulation data and refresh all charts.
 * Called after each step/run, or when the user loads a saved run.
 */
async function fetchAndUpdateCharts() {
  try {
    const res = await fetch('/api/simulation/data');
    if (!res.ok) return;
    const data = await res.json();
    updateAllCharts(data.model_data, data.agent_states);
  } catch (e) {
    console.error('fetchAndUpdateCharts error:', e);
  }
}

/**
 * updateAllCharts — Render all charts from model_data and agent_states.
 *
 * @param {Array} modelData - Array of {step, avg_stress, ...} objects (one per step)
 * @param {Array} agentStates - Array of current-step agent state dicts
 */
function updateAllCharts(modelData, agentStates) {
  if (!modelData || modelData.length === 0) return;

  const steps = modelData.map(d => d.step);

  // --- Chart 1: Primary time-series ---
  // Three metrics on one chart, each with a distinct colour and dashed/solid line.
  const tsTraces = [
    {
      x: steps, y: modelData.map(d => d.avg_stress),
      name: 'Avg Stress', mode: 'lines',
      line: { color: '#D6604D', width: 2 },
    },
    {
      x: steps, y: modelData.map(d => d.avg_delegation_rate),
      name: 'Avg Delegation Rate', mode: 'lines',
      line: { color: '#2166AC', width: 2, dash: 'dot' },
    },
    {
      x: steps, y: modelData.map(d => d.social_efficiency),
      name: 'Social Efficiency', mode: 'lines',
      line: { color: '#4DAF4A', width: 2, dash: 'dash' },
    },
  ];

  // Add any overlay runs (past runs loaded from run history)
  for (const [runId, overlay] of Object.entries(overlayRuns)) {
    tsTraces.push({
      x: overlay.data.map(d => d.step),
      y: overlay.data.map(d => d.avg_stress),
      name: `${overlay.name} (stress)`,
      mode: 'lines',
      line: { color: overlay.color, width: 1.5, dash: 'longdash' },
      opacity: 0.7,
    });
  }

  Plotly.react('chart-timeseries', tsTraces, {
    ...LAYOUT_DEFAULTS,
    yaxis: { ...LAYOUT_DEFAULTS.yaxis, title: { text: 'Value', font: { size: 11 } } },
  }, PLOTLY_CONFIG);

  // --- Chart 2: Total labour hours ---
  const labourTraces = [{
    x: steps, y: modelData.map(d => d.total_labor_hours),
    name: 'Total Labour Hours', mode: 'lines',
    fill: 'tozeroy', fillcolor: 'rgba(91,141,238,0.10)',
    line: { color: '#5b8dee', width: 2 },
  }];
  for (const [runId, overlay] of Object.entries(overlayRuns)) {
    labourTraces.push({
      x: overlay.data.map(d => d.step),
      y: overlay.data.map(d => d.total_labor_hours),
      name: `${overlay.name}`,
      mode: 'lines', line: { color: overlay.color, width: 1.5, dash: 'longdash' },
      opacity: 0.7,
    });
  }
  Plotly.react('chart-labour', labourTraces, {
    ...LAYOUT_DEFAULTS,
    yaxis: { ...LAYOUT_DEFAULTS.yaxis, title: { text: 'Hours / day', font: { size: 11 } } },
  }, PLOTLY_CONFIG);

  // --- Chart 3: Social efficiency ---
  const effTraces = [{
    x: steps, y: modelData.map(d => d.social_efficiency),
    name: 'Social Efficiency', mode: 'lines',
    line: { color: '#4DAF4A', width: 2 },
  }];
  Plotly.react('chart-efficiency', effTraces, {
    ...LAYOUT_DEFAULTS,
    yaxis: { ...LAYOUT_DEFAULTS.yaxis, title: { text: 'Tasks / labour-hour', font: { size: 11 } } },
  }, PLOTLY_CONFIG);

  // --- Chart 4: Stress distribution histogram ---
  // Shows the current distribution of stress_level across all agents.
  const stressValues = (agentStates || []).map(a => a.stress_level);
  Plotly.react('chart-stress-dist', [{
    x: stressValues,
    type: 'histogram',
    nbinsx: 20,
    name: 'Agent Stress',
    marker: { color: '#D6604D', opacity: 0.8 },
  }], {
    ...LAYOUT_DEFAULTS,
    xaxis: { ...LAYOUT_DEFAULTS.xaxis, title: { text: 'Stress Level [0–1]', font: { size: 11 } }, range: [0, 1] },
    yaxis: { ...LAYOUT_DEFAULTS.yaxis, title: { text: 'Number of Agents', font: { size: 11 } } },
    hovermode: 'x', bargap: 0.05,
  }, PLOTLY_CONFIG);

  // --- Chart 5: Delegation preference distribution histogram ---
  // Shows the current spread of delegation_preference across agents.
  // H4 predicts this should become bimodal in mixed-delegation systems.
  const delValues = (agentStates || []).map(a => a.delegation_preference);
  Plotly.react('chart-delegation-dist', [{
    x: delValues,
    type: 'histogram',
    nbinsx: 20,
    name: 'Delegation Preference',
    marker: { color: '#2166AC', opacity: 0.8 },
  }], {
    ...LAYOUT_DEFAULTS,
    xaxis: { ...LAYOUT_DEFAULTS.xaxis, title: { text: 'Delegation Preference [0–1]', font: { size: 11 } }, range: [0, 1] },
    yaxis: { ...LAYOUT_DEFAULTS.yaxis, title: { text: 'Number of Agents', font: { size: 11 } } },
    hovermode: 'x', bargap: 0.05,
  }, PLOTLY_CONFIG);

  // --- Chart 6: Gini coefficient over time ---
  Plotly.react('chart-gini', [{
    x: steps, y: modelData.map(d => d.gini_income),
    name: 'Income Gini', mode: 'lines',
    line: { color: '#984EA3', width: 2 },
  }], {
    ...LAYOUT_DEFAULTS,
    yaxis: { ...LAYOUT_DEFAULTS.yaxis, title: { text: 'Gini [0–1]', font: { size: 11 } }, range: [0, 1] },
  }, PLOTLY_CONFIG);
}

// ---------------------------------------------------------------------------
// Status bar update
// ---------------------------------------------------------------------------

/**
 * updateStatusBar — Poll /api/simulation/status and update header indicators.
 * Called every 2 seconds via setInterval().
 */
async function updateStatusBar() {
  try {
    const res = await fetch('/api/simulation/status');
    if (!res.ok) return;
    const s = await res.json();

    const dot = document.getElementById('sim-dot');
    const txt = document.getElementById('sim-status-text');
    const counter = document.getElementById('step-counter');

    if (!s.initialised) {
      dot.className = 'status-dot';
      txt.textContent = 'Not initialised';
      counter.textContent = '—';
      setButtonStates(false);
    } else if (s.is_running) {
      dot.className = 'status-dot running';
      txt.textContent = 'Running…';
      counter.textContent = s.current_step;
    } else {
      dot.className = 'status-dot active';
      txt.textContent = s.params.preset
        ? (s.params.preset === 'type_a' ? 'Type A' : s.params.preset === 'type_b' ? 'Type B' : 'Custom')
        : 'Initialised';
      counter.textContent = s.current_step;
      setButtonStates(true);
    }
  } catch (e) { /* silently ignore polling errors */ }
}

/** setButtonStates — Enable or disable control buttons based on model state. */
function setButtonStates(hasModel) {
  ['btn-step1', 'btn-step10', 'btn-run', 'btn-reset', 'btn-forum-step'].forEach(id => {
    document.getElementById(id).disabled = !hasModel;
  });
}

// ---------------------------------------------------------------------------
// Simulation control actions
// ---------------------------------------------------------------------------

/** initSimulation — POST /api/simulation/init with current slider params. */
async function initSimulation() {
  const btn = document.getElementById('btn-init');
  btn.disabled = true;
  btn.textContent = '⏳ Initialising…';
  try {
    const body = activePreset && activePreset !== 'custom'
      ? { preset: activePreset, seed: currentParams.seed }
      : { ...currentParams };

    const res = await fetch('/api/simulation/init', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json();
      alert('Initialisation failed: ' + (err.error || 'Unknown error'));
      return;
    }
    await fetchAndUpdateCharts();
    await loadRunHistory();
    clearOverlays();
  } finally {
    btn.disabled = false;
    btn.textContent = '⚡ Initialise';
  }
}

/** stepSimulation — POST /api/simulation/step and update charts. */
async function stepSimulation(n) {
  try {
    const res = await fetch('/api/simulation/step', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steps: n }),
    });
    if (!res.ok) return;
    // Update charts with the fresh data from the run endpoint response.
    await fetchAndUpdateCharts();
  } catch (e) { console.error('stepSimulation error:', e); }
}

/** runSimulation — POST /api/simulation/run and update charts when done. */
async function runSimulation() {
  const maxSteps = parseInt(document.getElementById('run-steps').value) || 50;
  const label = document.getElementById('run-label').value || null;

  const btn = document.getElementById('btn-run');
  btn.disabled = true;
  btn.textContent = '⏳ Running…';

  try {
    const res = await fetch('/api/simulation/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ max_steps: maxSteps, save_run: true, run_label: label }),
    });
    if (!res.ok) {
      const err = await res.json();
      alert('Run failed: ' + (err.error || 'Unknown error'));
      return;
    }
    const runResult = await res.json();
    // Fetch full data including agent_states (the run endpoint omits them),
    // so histograms render alongside time-series charts.
    await fetchAndUpdateCharts();
    await loadRunHistory();
    // LLM Role 4: annotate all charts with key insights (non-blocking).
    annotateDashboard(runResult.model_data, activePreset);
  } finally {
    btn.disabled = false;
    btn.textContent = '▶▶ Run';
  }
}

/** resetSimulation — POST /api/simulation/reset and clear charts. */
async function resetSimulation() {
  if (!confirm('Reset and clear the current simulation?')) return;
  await fetch('/api/simulation/reset', { method: 'POST' });
  clearOverlays();
  initCharts();
  // Clear LLM annotations and forum log from the previous run.
  document.querySelectorAll('.chart-annotation').forEach(el => {
    el.innerHTML = '';
    el.classList.remove('visible');
  });
  clearForumLog();
  document.getElementById('sim-dot').className = 'status-dot';
  document.getElementById('sim-status-text').textContent = 'Not initialised';
  document.getElementById('step-counter').textContent = '—';
  setButtonStates(false);
}

// ---------------------------------------------------------------------------
// Preset handling
// ---------------------------------------------------------------------------

/**
 * applyPreset — Load preset parameter values and highlight the preset button.
 *
 * For 'type_a' and 'type_b': fetch from /api/presets and update sliders.
 * For 'custom': just mark as custom (user has already adjusted sliders).
 *
 * @param {string} presetName - 'type_a', 'type_b', or 'custom'
 */
async function applyPreset(presetName) {
  activePreset = presetName;

  // Highlight active button
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  const btnId = presetName === 'type_a' ? 'preset-type-a'
                : presetName === 'type_b' ? 'preset-type-b' : 'preset-custom';
  document.getElementById(btnId).classList.add('active');

  if (presetName === 'custom') return;

  try {
    const res = await fetch('/api/presets');
    const presets = await res.json();
    const preset = presets[presetName];
    if (!preset) return;
    const params = preset.params;

    // Apply preset values to sliders and currentParams.
    // Guard prevents onSliderChange from reverting activePreset to 'custom'.
    _applyingPreset = true;
    const sliderMap = {
      delegation_preference_mean: 'delegation_preference_mean',
      service_cost_factor: 'service_cost_factor',
      social_conformity_pressure: 'social_conformity_pressure',
      tasks_per_step_mean: 'tasks_per_step_mean',
      num_agents: 'num_agents',
    };
    for (const [key, sliderId] of Object.entries(sliderMap)) {
      if (params[key] !== undefined) {
        onSliderChange(sliderId, params[key]);
        const slider = document.getElementById(`slider-${sliderId}`);
        if (slider) slider.value = params[key];
      }
    }
    _applyingPreset = false;
    // Also update the hidden params (adaptation_rate, stress_recovery_rate, etc.)
    Object.assign(currentParams, params);
    currentParams.seed = params.seed || 42;
  } catch (e) { console.error('applyPreset error:', e); }
}

/**
 * onSliderChange — Update currentParams and the displayed value label.
 *
 * @param {string} param - Parameter key (matches currentParams field name)
 * @param {number|string} value - New value from the slider
 */
function onSliderChange(param, value) {
  const numVal = parseFloat(value);
  currentParams[param] = numVal;
  const display = document.getElementById(`val-${param}`);
  if (display) display.textContent = Number.isInteger(numVal) ? numVal : numVal.toFixed(2);
  // When the USER manually moves a slider, deactivate the preset.
  // Skip this when applyPreset is programmatically setting slider values.
  if (!_applyingPreset && activePreset !== 'custom') {
    activePreset = 'custom';
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('preset-custom').classList.add('active');
  }
}

// ---------------------------------------------------------------------------
// Run history
// ---------------------------------------------------------------------------

/** loadRunHistory — Fetch saved runs and populate the #runs-tbody table. */
async function loadRunHistory() {
  try {
    const res = await fetch('/api/runs');
    const runs = await res.json();
    const tbody = document.getElementById('runs-tbody');
    if (!runs || runs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--light-muted);padding:12px">No saved runs yet.</td></tr>';
      return;
    }
    tbody.innerHTML = runs.map(r => `
      <tr>
        <td>${r.id}</td>
        <td>${r.created_at ? r.created_at.split(' ')[0] : '—'}</td>
        <td>${r.label || r.preset || '—'}</td>
        <td>${r.steps_run}</td>
        <td>${r.final_avg_stress !== null ? r.final_avg_stress.toFixed(3) : '—'}</td>
        <td>${r.final_avg_delegation_rate !== null ? r.final_avg_delegation_rate.toFixed(3) : '—'}</td>
        <td><button class="run-overlay-btn" onclick="overlayRun(${r.id}, '${r.label || r.preset || 'Run ' + r.id}')">Overlay</button></td>
      </tr>
    `).join('');
  } catch (e) { console.error('loadRunHistory error:', e); }
}

/**
 * overlayRun — Load a past run and add its stress trace to the time-series chart.
 * This allows comparing the current run against previously saved runs.
 *
 * @param {number} runId - SQLite run ID
 * @param {string} runName - Display label for the overlay trace
 */
async function overlayRun(runId, runName) {
  if (overlayRuns[runId]) {
    // Already overlaid — toggle off
    delete overlayRuns[runId];
    await fetchAndUpdateCharts();
    return;
  }
  try {
    const res = await fetch(`/api/runs/${runId}`);
    const data = await res.json();
    const color = OVERLAY_COLORS[overlayColorIdx % OVERLAY_COLORS.length];
    overlayColorIdx++;
    overlayRuns[runId] = { name: runName, color, data: data.steps };
    await fetchAndUpdateCharts();
  } catch (e) { console.error('overlayRun error:', e); }
}

/** clearOverlays — Remove all overlay run traces. */
function clearOverlays() {
  Object.keys(overlayRuns).forEach(k => delete overlayRuns[k]);
  overlayColorIdx = 0;
}

// ---------------------------------------------------------------------------
// Chat panel toggle (Phase 4 — LLM integration)
// ---------------------------------------------------------------------------

/** toggleChat — Show or hide the floating LLM chat panel. */
function toggleChat() {
  document.getElementById('chat-panel').classList.toggle('open');
}

// ---------------------------------------------------------------------------
// Agent Forums (Phase 5 — Role 5: LLM-in-loop experimental mode)
// ---------------------------------------------------------------------------

/**
 * runForumStep — POST /api/simulation/forum_step with current forum settings.
 *
 * This is the entry point triggered by the "Run Forum Step" button.
 * After the forum completes the full log is refreshed so the new session
 * appears in the transcript panel.
 */
async function runForumStep() {
  const fraction = parseInt(document.getElementById('forum-fraction').value) / 100;
  const groupSize = parseInt(document.getElementById('forum-group-size').value);
  const numTurns = parseInt(document.getElementById('forum-num-turns').value);

  const btn = document.getElementById('btn-forum-step');
  const status = document.getElementById('forum-status');
  btn.disabled = true;
  status.style.display = 'block';

  try {
    const res = await fetch('/api/simulation/forum_step', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        forum_fraction: fraction,
        group_size: groupSize,
        num_turns: numTurns,
      }),
    });

    if (res.status === 503) {
      alert('Ollama is not running. Start it with: ollama serve');
      return;
    }
    if (!res.ok) {
      const err = await res.json();
      alert('Forum error: ' + (err.error || 'Unknown error'));
      return;
    }

    // Reload the full forum log so all sessions (including the new one) render.
    await loadForumLog();
    // Refresh charts — the forum may have nudged agent preferences.
    await fetchAndUpdateCharts();
  } catch (e) {
    console.error('runForumStep error:', e);
    alert('Could not reach the server. Is it running?');
  } finally {
    btn.disabled = false;
    status.style.display = 'none';
    // Re-enable only if model is still initialised
    updateStatusBar();
  }
}

/**
 * loadForumLog — Fetch GET /api/simulation/forum_log and render all sessions.
 *
 * Called after each forum step and also when the page is refreshed with an
 * active simulation. Renders each ForumSession as a collapsible card showing
 * the full dialogue transcript and the norm-update delta applied.
 */
async function loadForumLog() {
  try {
    const res = await fetch('/api/simulation/forum_log');
    if (!res.ok) return;  // 409 = no model; silently skip
    const data = await res.json();
    const sessions = data.forum_sessions || [];

    const container = document.getElementById('forum-log');
    const empty = document.getElementById('forum-empty');

    if (sessions.length === 0) {
      empty.style.display = 'block';
      // Remove any previously rendered session cards.
      container.querySelectorAll('.forum-session').forEach(el => el.remove());
      return;
    }

    empty.style.display = 'none';
    // Remove old cards and re-render so the list stays consistent.
    container.querySelectorAll('.forum-session').forEach(el => el.remove());

    // Render newest session first.
    [...sessions].reverse().forEach((session, idx) => {
      const card = _buildForumSessionCard(session, sessions.length - idx);
      container.appendChild(card);
    });

    // Auto-expand the newest (first) session card.
    const first = container.querySelector('.forum-session-body');
    if (first) first.classList.add('open');
  } catch (e) {
    console.error('loadForumLog error:', e);
  }
}

/**
 * _buildForumSessionCard — Build the DOM element for one ForumSession.
 *
 * @param {Object} session - ForumSession dict from the API
 * @param {number} sessionNum - Display number (1-indexed)
 * @returns {HTMLElement}
 */
function _buildForumSessionCard(session, sessionNum) {
  const elapsed = session.elapsed_seconds
    ? ` · ${session.elapsed_seconds.toFixed(1)}s` : '';

  const card = document.createElement('div');
  card.className = 'forum-session';

  // Collapsible header
  const header = document.createElement('div');
  header.className = 'forum-session-header';
  header.innerHTML = `
    <span><strong>Session ${sessionNum}</strong> — Simulation day ${session.step}</span>
    <span class="forum-session-meta">
      ${session.n_agents_participating} agents ·
      ${(session.groups || []).length} groups ·
      ${session.total_norm_updates} updates${elapsed}
    </span>
    <span style="color:var(--light-muted);font-size:14px">▾</span>
  `;
  header.onclick = () => {
    const body = card.querySelector('.forum-session-body');
    body.classList.toggle('open');
    header.querySelector('span:last-child').textContent =
      body.classList.contains('open') ? '▴' : '▾';
  };

  const body = document.createElement('div');
  body.className = 'forum-session-body';

  (session.groups || []).forEach((group, gi) => {
    const groupEl = document.createElement('div');
    groupEl.className = 'forum-group';

    const agentIds = (group.agent_ids || []).map(id => `#${id % 100}`).join(', ');
    groupEl.innerHTML = `<div class="forum-group-header">Group ${gi + 1} — Agents ${agentIds}</div>`;

    // Dialogue turns
    (group.turns || []).forEach(turn => {
      const turnEl = document.createElement('div');
      turnEl.className = 'forum-turn';
      turnEl.innerHTML = `
        <div class="forum-speaker">Resident #${turn.speaker_id % 100}</div>
        <div class="forum-content">${_escapeHtml(turn.content)}</div>
      `;
      groupEl.appendChild(turnEl);
    });

    // Outcome (norm signal and delta)
    if (group.outcome) {
      const o = group.outcome;
      const delta = group.delta_applied || 0;
      const deltaClass = delta > 0 ? 'positive' : delta < 0 ? 'negative' : '';
      const deltaSign = delta > 0 ? '+' : '';
      const dirLabel = o.norm_signal > 0.1 ? '▲ toward delegation'
                     : o.norm_signal < -0.1 ? '▼ toward autonomy' : '↔ no clear shift';
      groupEl.innerHTML += `
        <div class="forum-outcome">
          <div class="forum-outcome-summary">
            <strong>Consensus:</strong> ${_escapeHtml(o.summary)}
          </div>
          <div class="forum-delta ${deltaClass}">
            norm_signal: ${o.norm_signal.toFixed(2)} · confidence: ${o.confidence.toFixed(2)} →
            Δ pref: <strong>${deltaSign}${delta.toFixed(4)}</strong> ${dirLabel}
          </div>
        </div>
      `;
    } else {
      groupEl.innerHTML += `<div style="font-size:10px;color:var(--light-muted);margin-top:4px">
        Outcome extraction failed — LLM may be offline.
      </div>`;
    }

    body.appendChild(groupEl);
  });

  card.appendChild(header);
  card.appendChild(body);
  return card;
}

/** clearForumLog — Remove all rendered session cards and show the empty state. */
function clearForumLog() {
  const container = document.getElementById('forum-log');
  container.querySelectorAll('.forum-session').forEach(el => el.remove());
  document.getElementById('forum-empty').style.display = 'block';
}

/** _escapeHtml — Escape user-visible strings to prevent XSS in innerHTML. */
function _escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ---------------------------------------------------------------------------
// Page initialisation
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// LLM annotation helper (Phase 4 — Role 4)
// ---------------------------------------------------------------------------

/**
 * annotateDashboard — Call /api/llm/annotate_all after a run completes
 * and inject the returned captions into the chart annotation <div>s.
 *
 * Gracefully skips if the LLM is not available (ollama offline).
 *
 * @param {Array} modelData - The full model_data array from the run response
 * @param {string|null} preset - Active preset ('type_a', 'type_b', or null)
 */
async function annotateDashboard(modelData, preset) {
  try {
    const res = await fetch('/api/llm/annotate_all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_data: modelData, preset }),
    });
    if (!res.ok) return;  // LLM offline or error — skip silently
    const data = await res.json();
    const annotations = data.annotations || {};

    // Map from chart metric names to DOM element IDs
    const annMap = {
      total_labor_hours: 'ann-labour',
      avg_stress: 'ann-timeseries',
      social_efficiency: 'ann-efficiency',
      gini_income: 'ann-gini',
      avg_delegation_rate: 'ann-delegation-dist',
    };
    for (const [key, domId] of Object.entries(annMap)) {
      const ann = annotations[key];
      if (ann && ann.key_insight) {
        const el = document.getElementById(domId);
        if (el) {
          el.innerHTML = `<strong>${ann.key_insight}</strong>` +
            (ann.caption ? ` <span style="color:var(--light-muted)">${ann.caption}</span>` : '');
          el.classList.add('visible');
        }
      }
    }
  } catch (e) {
    // Annotation is purely decorative — never block the UI for it.
    console.warn('LLM annotation failed (non-critical):', e);
  }
}

/**
 * checkLlmStatus — Check Ollama health and update the chat toggle button.
 * Shows a green dot if the LLM is available, grey if offline.
 */
async function checkLlmStatus() {
  try {
    const res = await fetch('/api/llm/status');
    const btn = document.getElementById('chat-toggle');
    if (res.ok) {
      btn.title = 'AI Assistant (online)';
      btn.style.background = 'var(--green)';
    } else {
      btn.title = 'AI Assistant (offline — start ollama serve)';
      btn.style.background = '#aaa';
    }
  } catch (e) { /* ignore */ }
}

// ---------------------------------------------------------------------------
// Page initialisation
// ---------------------------------------------------------------------------

/** onLoad — Run once when the page DOM is ready. */
document.addEventListener('DOMContentLoaded', () => {
  // Set up empty Plotly chart containers
  initCharts();

  // Poll status bar every 2 seconds so the header stays current
  updateStatusBar();
  setInterval(updateStatusBar, 2000);

  // Load run history on page load
  loadRunHistory();

  // Load forum log (shows sessions from the current server-side simulation if any)
  loadForumLog();

  // Check LLM status and update chat toggle indicator
  checkLlmStatus();
  setInterval(checkLlmStatus, 30000);  // Recheck every 30 s

  // Highlight the custom preset button by default
  document.getElementById('preset-custom').classList.add('active');
});
