# Phase 3: Web Interface & Dashboard (Days 5-7)

**Goal**: Interactive web dashboard for controlling and visualizing simulations.

## Tasks

### Day 5: Flask Application and REST API

- [ ] Implement Flask application factory (`api/app.py`)
- [ ] Implement REST API endpoints (`api/routes.py`):
  - `POST /api/init` -- initialize a new simulation with parameters
  - `POST /api/step` -- advance simulation by N steps
  - `POST /api/run` -- run simulation to completion
  - `POST /api/batch` -- run batch of simulations with parameter sweep
  - `GET /api/data` -- retrieve current simulation data (model and agent level)
  - `GET /api/presets` -- list available parameter presets
  - `GET /api/status` -- current simulation status

### Day 6: Dashboard Layout and Core Visualizations

- [ ] Build main dashboard page (`templates/index.html`):
  - Responsive layout with sidebar controls and main visualization area
  - Parameter control panel with sliders and preset selector (Type A / Type B / Custom)
  - Simulation control buttons (Initialize, Step, Run, Reset)
- [ ] Implement Plotly.js visualizations (`static/js/dashboard.js`):
  - Time-series chart: avg_stress, total_labor_hours, delegation_rate over steps
  - Agent state distribution: histogram of stress levels, delegation preferences
  - Social efficiency metric over time
- [ ] Basic CSS styling (`static/css/style.css`)

### Day 7: Interactivity and Persistence

- [ ] Add real-time chart updates during simulation runs
- [ ] Implement parameter slider interactivity (live updates to parameter values)
- [ ] Implement run persistence (SQLite) for comparing multiple simulation runs
- [ ] Add run history panel: list past runs, select for comparison overlay
- [ ] Test dashboard end-to-end with Type A and Type B presets

## Deliverable

Working web dashboard at `http://localhost:5000` where users can:
1. Select a preset or configure custom parameters
2. Run simulations with visual feedback
3. View interactive time-series and distribution charts
4. Compare multiple runs
