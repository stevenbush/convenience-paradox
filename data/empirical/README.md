# Empirical Grounding Data

This directory contains stylised facts derived from publicly available
international datasets. The data does **not** calibrate the model to real-world
outcomes. Instead, it *informs* plausible parameter ranges for the two
abstract society presets used in the simulation.

> **Neutrality notice**: All data is presented using abstract regional
> categories ("High-Autonomy Regions", "Moderate-Autonomy Regions",
> "High-Delegation Regions"). No specific country, nation, or cultural group
> is named or implied. The model explores abstract social mechanisms, not
> characteristics of any real society.

---

## Data Sources

| File | Source | Access |
|------|--------|--------|
| `ilo_working_hours_stylized.csv` | ILO (International Labour Organization), ILOSTAT database, "Mean weekly hours actually worked per employed person", 2022–2024 averages | Free, https://ilostat.ilo.org |
| `wvs_autonomy_stylized.csv` | World Values Survey Wave 7 (2017–2022), Item A001–A006 autonomy/obedience dimension | Free with registration, https://www.worldvaluessurvey.org |
| `oecd_better_life_stylized.csv` | OECD Better Life Index, Work-Life Balance and Life Satisfaction dimensions, 2023 | Free, https://www.oecdbetterlifeindex.org |

---

## How This Data Enters the Model

The data does **not** directly parameterise agents. Instead:

1. **Parameter range bounding**: The data tells us what values of
   `available_time`, `delegation_preference_mean`, and `service_cost_factor`
   produce outcomes (working hours, life satisfaction) that are plausible
   relative to real-world observations.

2. **Preset definition**: The Type A (Autonomy-Oriented) and Type B
   (Convenience-Oriented) parameter presets in `model/params.py` are
   constructed so that their simulated outcomes fall within the ranges
   observed in the corresponding regional categories below.

3. **Pattern-oriented validation**: After running the simulation, we check
   whether Type A outcomes (stress, labour hours, social efficiency) are
   qualitatively consistent with "High-Autonomy Region" real-world data,
   and whether Type B outcomes are consistent with "High-Delegation Region"
   data. This is *not* calibration — it is plausibility checking.

---

## Mapping to Model Parameters

| Empirical Observation | Model Parameter | Rationale |
|---|---|---|
| High-Autonomy avg weekly hours ~36–38h | Lower `tasks_per_step_mean`; higher `initial_available_time` | Less total task burden; more leisure |
| High-Delegation avg weekly hours ~48–52h | Higher effective labour via service provision | System creates extra work via delegation chain |
| WVS Autonomy score ~0.65–0.72 (high-autonomy) | `delegation_preference_mean` ~ 0.20–0.30 | Strong preference for self-reliance |
| WVS Autonomy score ~0.30–0.40 (high-delegation) | `delegation_preference_mean` ~ 0.65–0.75 | Strong norm of delegating to services |
| OECD Work-Life Balance ~8.0–9.0 (high-autonomy) | Lower simulated `avg_stress` target | Agents retain more discretionary time |
| OECD Work-Life Balance ~4.5–6.0 (high-delegation) | Higher simulated `avg_stress` target | Agents chronically time-pressured |
| Service sector employment ~60–75% (high-delegation) | Higher `provider_acceptance_rate` | More of the economy is service-driven |
