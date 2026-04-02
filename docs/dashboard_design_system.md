# Dashboard Design System — The Convenience Paradox

**Date**: 2026-03-24
**Status**: Draft — Pending user review
**Base Theme**: Bootswatch LITERA (minimalist, whitespace-heavy) with FLATLY-inspired color accents
**Color Mode**: Light only

---

## 1. Design Principles

1. **Clarity over decoration** — every pixel serves a purpose; avoid ornamental elements
2. **Whitespace is structure** — generous margins and padding create visual hierarchy without borders
3. **Progressive disclosure** — show the most important information first; details on interaction
4. **Consistent rhythm** — all spacing, sizing, and layout follows the 8px grid
5. **Responsive by default** — fluid containers, Bootstrap grid, no fixed pixel widths for content areas

---

## 2. Design Tokens

Design tokens are CSS custom properties defined in `dash_app/assets/tokens.css`. All components reference these tokens — never hardcoded values. This ensures future pages and components automatically inherit the visual style.

### 2.1 Color Palette

```css
:root {
  /* --- Brand --- */
  --cp-primary:           #2C8C99;   /* Muted teal — main interactive elements */
  --cp-primary-hover:     #237580;   /* Darker teal for hover states */
  --cp-primary-light:     #E8F4F6;   /* Very light teal — selected/active backgrounds */
  --cp-primary-subtle:    #D0EAED;   /* Subtle teal — tag backgrounds, light fills */

  /* --- Neutrals --- */
  --cp-bg:                #FAFBFC;   /* Page background — near-white, not pure white */
  --cp-surface:           #FFFFFF;   /* Card/panel surface */
  --cp-surface-raised:    #FFFFFF;   /* Elevated cards (differentiated by shadow, not color) */
  --cp-border:            #E2E8F0;   /* Subtle dividers and card borders */
  --cp-border-strong:     #CBD5E1;   /* Stronger borders for active/focused elements */

  /* --- Text --- */
  --cp-text-primary:      #1E293B;   /* Headings and primary content — near-black */
  --cp-text-secondary:    #64748B;   /* Descriptions, labels, secondary info */
  --cp-text-tertiary:     #94A3B8;   /* Placeholders, disabled states, timestamps */
  --cp-text-inverse:      #FFFFFF;   /* Text on dark/primary backgrounds */

  /* --- Semantic --- */
  --cp-success:           #27AE60;   /* Confirmed hypotheses, healthy status */
  --cp-success-light:     #E8F8EF;
  --cp-warning:           #E67E22;   /* Supported/partial hypotheses, caution */
  --cp-warning-light:     #FEF3E2;
  --cp-danger:            #E74C3C;   /* Errors, failed validations, high stress */
  --cp-danger-light:      #FDEDEB;
  --cp-info:              #3498DB;   /* Informational badges, pending states */
  --cp-info-light:        #EBF5FB;

  /* --- Chart palette (8 colors, accessible, distinguishable) --- */
  --cp-chart-1:           #2C8C99;   /* Primary teal */
  --cp-chart-2:           #E67E22;   /* Warm orange */
  --cp-chart-3:           #27AE60;   /* Green */
  --cp-chart-4:           #8E44AD;   /* Purple */
  --cp-chart-5:           #E74C3C;   /* Red */
  --cp-chart-6:           #3498DB;   /* Blue */
  --cp-chart-7:           #F39C12;   /* Gold */
  --cp-chart-8:           #1ABC9C;   /* Mint */
}
```

### 2.2 Typography

```css
:root {
  /* --- Font families --- */
  --cp-font-sans:         'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --cp-font-mono:         'Fira Code', 'SF Mono', 'Cascadia Code', monospace;

  /* --- Font sizes (modular scale, ratio ~1.2) --- */
  --cp-text-xs:           0.75rem;    /* 12px — timestamps, fine print */
  --cp-text-sm:           0.8125rem;  /* 13px — labels, captions */
  --cp-text-base:         0.875rem;   /* 14px — body text (slightly compact for dashboards) */
  --cp-text-md:           1rem;       /* 16px — emphasized body */
  --cp-text-lg:           1.125rem;   /* 18px — section headers */
  --cp-text-xl:           1.375rem;   /* 22px — card titles */
  --cp-text-2xl:          1.75rem;    /* 28px — page titles */
  --cp-text-3xl:          2.25rem;    /* 36px — KPI hero numbers */

  /* --- Font weights --- */
  --cp-weight-normal:     400;
  --cp-weight-medium:     500;
  --cp-weight-semibold:   600;
  --cp-weight-bold:       700;

  /* --- Line heights --- */
  --cp-leading-tight:     1.25;
  --cp-leading-normal:    1.5;
  --cp-leading-relaxed:   1.75;
}
```

### 2.3 Spacing (8px grid)

```css
:root {
  --cp-space-0:    0;
  --cp-space-1:    0.25rem;   /*  4px */
  --cp-space-2:    0.5rem;    /*  8px */
  --cp-space-3:    0.75rem;   /* 12px */
  --cp-space-4:    1rem;      /* 16px */
  --cp-space-5:    1.25rem;   /* 20px */
  --cp-space-6:    1.5rem;    /* 24px */
  --cp-space-8:    2rem;      /* 32px */
  --cp-space-10:   2.5rem;    /* 40px */
  --cp-space-12:   3rem;      /* 48px */
}
```

### 2.4 Elevation (Shadows)

```css
:root {
  --cp-shadow-sm:    0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --cp-shadow-md:    0 1px 3px 0 rgba(0, 0, 0, 0.08), 0 1px 2px -1px rgba(0, 0, 0, 0.06);
  --cp-shadow-lg:    0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
  --cp-shadow-xl:    0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04);
}
```

### 2.5 Border Radius

```css
:root {
  --cp-radius-sm:    4px;
  --cp-radius-md:    6px;
  --cp-radius-lg:    8px;
  --cp-radius-xl:    12px;
  --cp-radius-full:  9999px;  /* Pills, badges */
}
```

### 2.6 Transitions

```css
:root {
  --cp-transition-fast:    150ms ease;
  --cp-transition-normal:  250ms ease;
  --cp-transition-slow:    350ms ease;
}
```

---

## 3. Layout Architecture

### 3.1 Shell Structure

```
+------------------------------------------------------+
|                  Top Bar (48px)                       |
|  [Logo + Title]              [LLM Status] [Settings] |
+----------+-------------------------------------------+
|          |                                           |
| Sidebar  |           Page Content                    |
| (240px)  |           (fluid)                         |
|          |                                           |
| [Nav]    |  +--------------------------------------+ |
| [Items]  |  |  Page Header + Breadcrumb            | |
|          |  +--------------------------------------+ |
| [Active] |  |                                      | |
| [State]  |  |  Content Grid                        | |
|          |  |  (Bootstrap Row/Col)                  | |
|          |  |                                      | |
|          |  +--------------------------------------+ |
+----------+-------------------------------------------+
```

- **Top bar**: 48px height, fixed. Contains project title (left), LLM status indicator + settings gear (right).
- **Sidebar**: 240px width, fixed position, full height minus top bar. Contains vertical navigation with icons + labels. Active page highlighted with `--cp-primary-light` background and `--cp-primary` left border accent.
- **Content area**: Fluid, fills remaining width. Has a consistent inner padding of `--cp-space-6` (24px).
- **All content within the content area** uses Bootstrap's 12-column grid (`dbc.Row` / `dbc.Col`) for responsive layout.

### 3.2 Responsive Breakpoints

| Breakpoint | Width | Sidebar Behavior | Content Layout |
|-----------|-------|-------------------|----------------|
| xl (default) | >= 1200px | Visible, 240px fixed | Full multi-column grid |
| lg | >= 992px | Visible, 200px | Charts may stack to fewer columns |
| md | >= 768px | Collapsed to icons-only (60px) | Full width available |
| sm | < 768px | Hidden, hamburger toggle | Single column stack |

### 3.3 Content Grid Patterns

**Dashboard page (Page 1)** — 3-zone layout:
```
Row 1: KPI Cards (4 across on xl, 2 on md, 1 on sm)
Row 2: [Chart Col-8] [Distribution Col-4]
Row 3: [Chart Col-8] [Distribution Col-4]
Row 4: [Sankey Col-6] [Network Col-6]
Row 5: [Waterfall Col-6] [Radar + Agent Card Col-6]
```

**LLM Studio (Page 2)** — tabbed sections:
```
Row 1: Model Configuration (collapsible)
Row 2: Tab bar (Scenario | Chat | Profile | Annotations | Forums | Audit)
Row 3: Tab content (full width, layout varies per tab)
```

**Run Manager (Page 3)** — table + detail:
```
Row 1: Search/filter bar
Row 2: AG Grid table (full width)
Row 3: Comparison panel or Detail view (appears on selection)
```

**Analysis (Page 4)** — research presentation:
```
Row 1: Hypothesis Cards (4 across)
Row 2: Type A vs B Comparison (full width)
Row 3: Interactive Sensitivity Heatmap (full width)
```

---

## 4. Component Library

Each component is a Python function in `dash_app/components/` returning a Dash component tree. All use design tokens via CSS classes, never inline styles for token values.

### 4.1 Card (`cp-card`)

The fundamental container. All content sections are wrapped in cards.

```
+----------------------------------+
|  [Icon] Card Title      [Action] |  <- Header (optional)
|  Subtitle / description          |
+----------------------------------+
|                                  |
|  Card body content               |
|  (chart, form, table, etc.)     |
|                                  |
+----------------------------------+
|  Footer (optional)               |
+----------------------------------+
```

CSS: `background: var(--cp-surface)`, `border: 1px solid var(--cp-border)`, `border-radius: var(--cp-radius-lg)`, `box-shadow: var(--cp-shadow-sm)`.

Variants: `cp-card--flush` (no padding, for full-bleed charts), `cp-card--highlight` (left border accent in `--cp-primary`).

### 4.2 KPI Metric Card (`cp-kpi`)

Compact metric display for key indicators.

```
+-------------------------+
|  [icon]  Label          |
|  42.3%   ▲ +3.2%       |
|  ████████░░  (sparkline)|
+-------------------------+
```

- Label: `--cp-text-sm`, `--cp-text-secondary`
- Value: `--cp-text-3xl`, `--cp-weight-bold`, `--cp-text-primary`
- Change indicator: colored arrow + delta value (`--cp-success` for up, `--cp-danger` for down)
- Optional mini sparkline below the value

### 4.3 Chart Container (`cp-chart`)

Wrapper for all Plotly `dcc.Graph` instances. Provides consistent sizing and spacing.

- Fixed aspect ratios: `cp-chart--16x9` (default), `cp-chart--4x3`, `cp-chart--square`
- Plotly config: `displayModeBar: False` by default (modebar on hover), responsive: True
- Plotly layout template (shared across all charts):
  - `font.family`: matches `--cp-font-sans`
  - `font.color`: matches `--cp-text-secondary`
  - `paper_bgcolor`: transparent (card background shows through)
  - `plot_bgcolor`: transparent
  - `margin`: compact (`t=30, b=30, l=50, r=20`)
  - `colorway`: the 8-color chart palette from tokens

### 4.4 Control Panel (`cp-controls`)

Sidebar-style control group for parameter sliders and selectors.

```
+-----------------------------+
|  SIMULATION PARAMETERS      |
+-----------------------------+
|  Preset: [Type A ▼]        |
|                             |
|  Delegation Mean            |
|  ═══════●═══════  0.50     |
|                             |
|  Service Cost               |
|  ═══●═══════════  0.25     |
|                             |
|  ▸ Advanced Parameters      |
+-----------------------------+
|  [Initialize] [Step] [Run]  |
+-----------------------------+
```

- Section title: uppercase, `--cp-text-xs`, `--cp-weight-semibold`, `--cp-text-tertiary`, letter-spacing 0.05em
- Sliders: `dcc.Slider` with `--cp-primary` track color
- Collapsible "Advanced" section using `dbc.Collapse`
- Action buttons: primary style for "Run", outline style for others

### 4.5 Status Badge (`cp-badge`)

Small pill-shaped indicators for hypothesis status, LLM status, etc.

| Variant | Background | Text | Use |
|---------|-----------|------|-----|
| `cp-badge--success` | `--cp-success-light` | `--cp-success` | Confirmed, Online, Valid |
| `cp-badge--warning` | `--cp-warning-light` | `--cp-warning` | Supported, Partial |
| `cp-badge--danger` | `--cp-danger-light` | `--cp-danger` | Error, Offline, Failed |
| `cp-badge--info` | `--cp-info-light` | `--cp-info` | Pending, In Progress |
| `cp-badge--neutral` | `--cp-border` | `--cp-text-secondary` | Default, Inactive |

CSS: `border-radius: var(--cp-radius-full)`, `font-size: var(--cp-text-xs)`, `font-weight: var(--cp-weight-semibold)`, `padding: 2px 10px`.

### 4.6 Chat Bubble (`cp-chat`)

For Role 3 (Interpreter) and Role 5 (Forums) conversation display.

```
+---  User  ---------------------------+
|  What caused the stress increase?    |  <- Right-aligned, primary-light bg
+--------------------------------------+

+---  AI  ---+
|  The stress increase correlates...   |  <- Left-aligned, surface bg + border
|  [H2 Supported] [Confidence: High]  |  <- Badges inline
+--------------------------------------+
```

### 4.7 Sidebar Navigation (`cp-sidebar`)

```
+----------------------------+
|  ◉  Simulation Dashboard  |  <- Active state
|  ◇  LLM Studio            |
|  ◇  Run Manager            |
|  ◇  Analysis               |
+----------------------------+
|                            |
|  (spacer)                  |
|                            |
+----------------------------+
|  v1.0  •  Ollama ●        |  <- Version + LLM status dot
+----------------------------+
```

- Active item: `background: var(--cp-primary-light)`, `color: var(--cp-primary)`, `border-left: 3px solid var(--cp-primary)`, `font-weight: var(--cp-weight-semibold)`
- Inactive: `color: var(--cp-text-secondary)`, transparent background
- Hover: `background: var(--cp-bg)` transition
- Icons: Font Awesome or Bootstrap Icons, 18px

---

## 5. Plotly Chart Theme

A unified Plotly template applied to all charts for visual consistency.

```python
CP_PLOTLY_TEMPLATE = {
    "layout": {
        "font": {
            "family": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
            "color": "#64748B",
            "size": 12,
        },
        "title": {
            "font": {"color": "#1E293B", "size": 16, "weight": 600},
            "x": 0,
            "xanchor": "left",
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "colorway": [
            "#2C8C99", "#E67E22", "#27AE60", "#8E44AD",
            "#E74C3C", "#3498DB", "#F39C12", "#1ABC9C",
        ],
        "margin": {"t": 40, "b": 40, "l": 56, "r": 16},
        "xaxis": {
            "gridcolor": "#E2E8F0",
            "linecolor": "#E2E8F0",
            "zerolinecolor": "#E2E8F0",
            "showgrid": True,
            "gridwidth": 1,
        },
        "yaxis": {
            "gridcolor": "#E2E8F0",
            "linecolor": "#E2E8F0",
            "zerolinecolor": "#E2E8F0",
            "showgrid": True,
            "gridwidth": 1,
        },
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 11},
        },
        "hoverlabel": {
            "bgcolor": "#FFFFFF",
            "bordercolor": "#E2E8F0",
            "font": {"family": "Inter, sans-serif", "size": 12, "color": "#1E293B"},
        },
    }
}
```

---

## 6. Page Wireframes

### 6.1 Page 1: Simulation Dashboard

```
+----------+-----------------------------------------------------+
| SIDEBAR  |  Simulation Dashboard                                |
|          |                                                     |
| [●] Sim  |  +----------+ +----------+ +----------+ +----------+|
| [ ] LLM  |  | Avg      | | Total    | | Social   | | Income   ||
| [ ] Runs |  | Stress   | | Labor    | | Efficien | | Gini     ||
| [ ] Anal |  | 0.34  ▲  | | 423  ▲   | | 0.56  ▼  | | 0.21  ▲  ||
|          |  +----------+ +----------+ +----------+ +----------+|
|          |                                                     |
| PARAMS   |  +-------------------------------+ +---------------+|
| -------- |  |                               | | Stress        ||
| Preset   |  |  Labor Hours (time series)    | | Distribution  ||
| [Type A] |  |  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ | | [histogram]   ||
|          |  |                               | |               ||
| Deleg.   |  +-------------------------------+ +---------------+|
| ══●════  |                                                     |
|          |  +-------------------------------+ +---------------+|
| Cost     |  |                               | | Delegation    ||
| ═●═════  |  |  Stress & Delegation (dual)   | | Preference    ||
|          |  |  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ | | Distribution  ||
| Conform  |  |                               | | [histogram]   ||
| ═══●═══  |  +-------------------------------+ +---------------+|
|          |                                                     |
| Tasks    |  +-------------------------------+ +---------------+|
| ═══●═══  |  |  Social Efficiency            | | Provider vs   ||
|          |  |  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ | | Consumer      ||
| Time     |  |                               | | [scatter]     ||
| ═════●═  |  +-------------------------------+ +---------------+|
|          |                                                     |
| Agents   |  +-------------------------------+ +---------------+|
| [  100 ] |  |  Market Health (dual-axis)    | |               ||
|          |  |  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ | |               ||
| ▸ Advanc |  |                               | |               ||
|          |  +-------------------------------+ +---------------+|
| -------- |                                                     |
| [Init]   |  +---------------+ +---------------+ +-------------+|
| [Step 1] |  | Task Flow     | | Fee Flow      | | Network     ||
| [Run 50] |  | [Sankey]      | | [Waterfall]   | | [Graph]     ||
| [Reset]  |  |               | |               | |             ||
|          |  +---------------+ +---------------+ +-------------+|
+----------+-----------------------------------------------------+
```

**Key design notes:**
- KPI cards at top provide instant summary of simulation state
- Time series charts on the left (2/3 width) paired with distributions on the right (1/3 width)
- Each time series has its chart title inside the card header
- Bottom row: three advanced visualizations side by side
- Control panel is part of the sidebar, below navigation — scrolls with sidebar if content overflows
- Skill radar chart appears as a modal/popover when clicking an agent in the network graph

### 6.2 Page 2: LLM Studio

```
+----------+-----------------------------------------------------+
| SIDEBAR  |  LLM Studio                                         |
|          |                                                     |
| [ ] Sim  |  ▾ Model Configuration                              |
| [●] LLM  |  +------------------------------------------------+|
| [ ] Runs |  | Role 1 Parser  [qwen3.5:4b ▼] ●                ||
| [ ] Anal |  | Role 2 Profile [qwen3:1.7b  ▼] ●                ||
|          |  | Role 3 Interp  [qwen3.5:4b ▼] ●                ||
|          |  | Role 4 Annot   [qwen3.5:4b ▼] ●                ||
|          |  | Role 5 Forums  [qwen3.5:4b ▼] ●   [Refresh]    ||
|          |  +------------------------------------------------+|
|          |                                                     |
|          |  [Scenario] [Chat] [Profile] [Annotate] [Forums]   |
|          |  [Audit Log]                                        |
|          |  ================================================= |
|          |                                                     |
|          |  (Example: Chat tab active)                         |
|          |  +------------------------------------------------+|
|          |  | AI Result Interpreter           [H2] [H3]      ||
|          |  |                                                ||
|          |  |  +---------User---------+                      ||
|          |  |  | Why is stress rising |                      ||
|          |  |  +----------------------+                      ||
|          |  |                                                ||
|          |  |  +---AI----------------------------+           ||
|          |  |  | The stress increase after step  |           ||
|          |  |  | 20 correlates with delegation   |           ||
|          |  |  | rates exceeding 0.6...          |           ||
|          |  |  | [Confidence: Moderate]          |           ||
|          |  |  +--------------------------------+           ||
|          |  |                                                ||
|          |  |  [Ask a question...              ] [Send]      ||
|          |  +------------------------------------------------+|
+----------+-----------------------------------------------------+
```

**Key design notes:**
- Model Configuration panel is collapsible (default: expanded on first visit, collapsed after)
- Horizontal tab bar for switching between the 6 LLM role interfaces
- Each tab has its own layout optimized for its role
- Chat tab: standard chat interface with message history
- Audit tab: AG Grid-style log table with expandable rows

### 6.3 Page 3: Run Manager

```
+----------+-----------------------------------------------------+
| SIDEBAR  |  Run Manager                                        |
|          |                                                     |
| [ ] Sim  |  +------------------------------------------------+|
| [ ] LLM  |  | Search: [____________]  Preset: [All ▼]        ||
| [●] Runs |  | Date: [from] — [to]     [Delete Selected]      ||
| [ ] Anal |  +------------------------------------------------+|
|          |                                                     |
|          |  +------------------------------------------------+|
|          |  | ☐ | ID | Date       | Label    | Preset | Steps||
|          |  |---|----+------------+----------+--------+------||
|          |  | ☐ | 12 | 2026-03-24 | H1 sweep | type_b |   50 ||
|          |  | ☑ |  9 | 2026-03-24 | Baseline | type_a |  100 ||
|          |  | ☑ |  7 | 2026-03-23 | Long run | type_b |  200 ||
|          |  | ☐ |  5 | 2026-03-23 | Quick    | custom |   20 ||
|          |  |   |    |            |          |        |      ||
|          |  |   |    |            |          |        |      ||
|          |  +------------------------------------------------+|
|          |  | Page 1 of 3            [<] [1] [2] [3] [>]     ||
|          |  +------------------------------------------------+|
|          |                                                     |
|          |  +----- Compare (2 runs selected) ----------------+|
|          |  |  Run #9 (Type A)         Run #7 (Type B)       ||
|          |  |  Stress: 0.21            Stress: 0.45  +114%   ||
|          |  |  Labor:  395             Labor:  482   +22%    ||
|          |  |  Effic:  0.55            Effic:  0.58  +5%     ||
|          |  |  Gini:   0.15            Gini:   0.24  +60%    ||
|          |  |                                                ||
|          |  |  [Compare on Charts →]                         ||
|          |  +------------------------------------------------+|
+----------+-----------------------------------------------------+
```

### 6.4 Page 4: Analysis

```
+----------+-----------------------------------------------------+
| SIDEBAR  |  Analysis                                            |
|          |                                                     |
| [ ] Sim  |  HYPOTHESIS SCOREBOARD                              |
| [ ] LLM  |  +----------+ +----------+ +----------+ +----------+|
| [ ] Runs |  | H1       | | H2       | | H3       | | H4       ||
| [●] Anal |  | ✓ Confir | | ~ Suppor | | ~ Suppor | | ~ Partia ||
|          |  | +22% lab | | Effic.   | | Long-run | | Conform  ||
|          |  | hours    | | plateau  | | phenomen | | drives   ||
|          |  +----------+ +----------+ +----------+ +----------+|
|          |                                                     |
|          |  TYPE A vs TYPE B COMPARISON                        |
|          |  +------------------------------------------------+|
|          |  | Parameter       | Type A  | Type B  | Delta    ||
|          |  |-----------------+---------+---------+----------||
|          |  | Delegation Mean | 0.25    | 0.72    | +188%    ||
|          |  | Service Cost    | 0.65    | 0.20    | -69%     ||
|          |  | Conformity      | 0.15    | 0.65    | +333%    ||
|          |  +------------------------------------------------+|
|          |  |  [metric bar chart comparison]                  ||
|          |  |  ████████  Type A   ████████████████  Type B    ||
|          |  +------------------------------------------------+|
|          |  |  [Run Both Presets]                             ||
|          |  +------------------------------------------------+|
|          |                                                     |
|          |  SENSITIVITY EXPLORER                               |
|          |  +------------------------------------------------+|
|          |  | X: [delegation_mean ▼] Y: [conformity ▼]       ||
|          |  | Color: [avg_stress ▼]                           ||
|          |  |                                                ||
|          |  |  [interactive heatmap / imshow]                 ||
|          |  |                                                ||
|          |  +------------------------------------------------+|
+----------+-----------------------------------------------------+
```

---

## 7. Interaction Patterns

### 7.1 Loading States

- **Initial page load**: Skeleton placeholders (gray rectangles matching card dimensions) with subtle pulse animation
- **Simulation step**: Charts show subtle loading overlay; KPI values animate to new numbers
- **LLM calls**: Typing indicator (three animated dots) in chat; spinner in other role outputs
- **Long operations** (Run, Batch delete): Progress bar or step counter in the action button

### 7.2 Empty States

- **No simulation initialized**: Cards show centered message "Initialize a simulation to see results" with an arrow pointing to the Initialize button
- **No run history**: Friendly message with illustration: "No saved runs yet. Run a simulation and save it to build your experiment history."
- **Ollama offline**: LLM Studio shows a clear banner: "LLM features unavailable — Ollama is not running" with a retry button

### 7.3 Error States

- Non-blocking errors: Toast notification in top-right corner (auto-dismiss after 5s)
- Blocking errors: Alert component within the relevant card (e.g., validation error in parameter panel)
- LLM errors: Show error in the output area of the specific role, with raw error details in a collapsible section

### 7.4 Confirmation Modals

- Used for: Delete run, batch delete, reset simulation
- Pattern: `dbc.Modal` with clear description of consequences, Cancel (secondary) and Confirm (danger) buttons

---

## 8. Responsive Strategy

### 8.1 Fluid Charts

All `dcc.Graph` components use `responsive=True` and `style={"width": "100%", "height": "100%"}` inside a container with a fixed aspect-ratio via CSS (`aspect-ratio: 16/9`). This ensures charts resize proportionally without distortion.

### 8.2 Grid Collapse Rules

| Content | xl (>=1200) | lg (>=992) | md (>=768) | sm (<768) |
|---------|-------------|------------|------------|-----------|
| KPI cards row | 4 across | 4 across | 2 across | 1 stacked |
| Chart + distribution | 8+4 cols | 8+4 cols | 12 stacked | 12 stacked |
| Bottom viz row | 4+4+4 cols | 6+6 (2 rows) | 12 stacked | 12 stacked |
| Hypothesis cards | 4 across | 2+2 | 2+2 | 1 stacked |

### 8.3 No Misalignment Guarantee

- **No fixed pixel widths** for content elements — all use Bootstrap col classes or percentage-based widths
- **No absolute positioning** for content — all layout via flexbox (Bootstrap grid)
- **Chart containers** use CSS `aspect-ratio` rather than fixed height — prevents overflow/underflow on resize
- **AG Grid** uses `domLayout="autoHeight"` and `columnSizeToFit` for fluid columns
- **Text truncation** via CSS `text-overflow: ellipsis` where space is limited (e.g., narrow sidebar, mobile)

---

## 9. File Structure for Design System

```
dash_app/
  assets/
    tokens.css          # All CSS custom properties (design tokens)
    layout.css          # Shell layout: top bar, sidebar, content area
    components.css      # Component styles: cp-card, cp-kpi, cp-badge, etc.
    charts.css          # Chart container sizing and aspect ratios
    responsive.css      # Media queries for breakpoint adjustments
    favicon.ico         # Project favicon
  components/
    __init__.py
    card.py             # card(), kpi_card(), chart_card()
    sidebar.py          # sidebar_nav()
    topbar.py           # top_bar()
    controls.py         # parameter_panel(), simulation_controls()
    badges.py           # status_badge(), hypothesis_badge()
    chat.py             # chat_bubble(), chat_container()
    charts.py           # Plotly template, chart builder helpers
    empty_states.py     # Placeholder content for uninitialized views
```
