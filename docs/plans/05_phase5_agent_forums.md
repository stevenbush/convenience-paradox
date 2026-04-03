# Phase 5: Agent Forums & Advanced Features (Days 11-12)

**Goal**: Experimental agent communication forums mode, advanced visualizations, scenario comparison.

## Tasks

### Day 11: Agent Communication Forums (Experimental Mode)

- [ ] Implement Role 5 -- Agent Communication Forums:
  - Use Mesa-LLM's built-in forum feature
  - Agents discuss delegation norms in 1-3 turn natural-language exchanges
  - Forum outcomes influence agent `delegation_preference` adaptation
  - Limit exchanges to 1-3 turns to manage quality at 4B model size
- [ ] Implement mode toggle on dashboard:
  - **Standard Mode**: Pure rule-based simulation (white-box)
  - **Forum-Enhanced Mode**: Adds LLM-driven agent dialogue (experimental)
  - Clear labeling: "Experimental -- LLM in simulation loop"
- [ ] Add forum transcript viewer: display agent dialogue exchanges in dashboard
- [ ] Document limitations of agent dialogue at 4B model size

### Day 12: Advanced Visualizations and UI Polish

- [ ] Build side-by-side comparison view: standard mode vs. forum-enhanced mode
  - Same parameters, different modes, overlaid time-series
- [ ] Add advanced visualizations:
  - Parameter sweep heatmaps (delegation rate vs. service cost, colored by outcome metric)
  - Stress/well-being distribution histograms (animated over time)
  - Scenario comparison overlays (Type A vs. Type B on same chart)
  - Agent network visualization (who serves whom)
- [ ] UI polish:
  - Responsive layout for different screen sizes
  - Consistent color scheme and typography
  - Loading states and progress indicators
  - Error handling and user feedback messages

## Deliverable

Complete dashboard with both simulation modes (standard + forum-enhanced) and full visualization suite including heatmaps, distributions, comparisons, and network views.
