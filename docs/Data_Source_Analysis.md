# Data Source Analysis: Service Convenience vs. Autonomy ABM

## 1. Dataset-by-Dataset Assessment

---

### 1.1 OECD Better Life Index

**What it is:** Tracks 11 well-being topics (housing, income, jobs, community, education, environment, civic engagement, health, life satisfaction, safety, work-life balance) across 38 OECD countries + partner countries. ~80 indicators with demographic breakdowns.

**Relevant variables:**
- **Work-life balance:** Employees working very long hours (%), time devoted to leisure and personal care
- **Life satisfaction:** Self-reported life satisfaction scores (0–10)
- **Jobs:** Employment rate, long-term unemployment rate

**Accessibility:** Fully free. Available via official site (oecdbetterlifeindex.org), OECD Data Explorer API (JSON/TSV), and Kaggle. No registration barriers.

**Relevance to this project:** **MODERATE.** Provides aggregate country-level comparison of work-life balance and life satisfaction — useful for a "sanity check" (e.g., do European countries actually report higher life satisfaction and fewer long hours than China?). However, it does **not** contain any variables about service delegation, self-service behavior, or convenience culture. It's a validation reference, not a calibration source.

**Effort to integrate:** Very low (~1 hour to download and reference a few numbers).

---

### 1.2 Harmonised European Time Use Surveys (HETUS)

**What it is:** Coordinated collection of national time-use diaries across European countries. Respondents record activities in 10-minute slots over diary days.

**Relevant variables:**
- Time spent on **paid work** vs. **household tasks** (cooking, cleaning, repairs — the "self-service" activities)
- Time spent **purchasing goods/services** vs. doing things yourself
- Time for **leisure and personal care**
- ~1,950 variables per record across 17 countries (HETUS 2010 round)

**Accessibility:** Aggregate comparative tables are **freely accessible** (no registration needed). Microdata requires institutional affiliation, approved research project, and binding contract — **not practical for a 2-week project**.

**Relevance to this project:** **HIGH in theory, LOW in practice.** The aggregate tables showing "time spent on domestic work" vs. "time spent on paid work" across European countries could provide interesting comparisons. But HETUS covers only Europe — no China data — and the aggregate tables don't break down "delegated vs. self-performed" services.

**Effort to integrate:** Low for aggregate tables (2–3 hours). Impractical for microdata.

---

### 1.3 Eurostat Time Use Surveys (General)

**What it is:** The broader Eurostat time-use data infrastructure that feeds into HETUS. Includes prefabricated tables on daily time allocation.

**Relevant variables:** Same as HETUS (time allocation across activity categories).

**Accessibility:** Free aggregate tables via Eurostat website. Same microdata restrictions as HETUS.

**Relevance to this project:** Largely overlaps with HETUS. No additional unique value.

**Effort to integrate:** Same as HETUS.

---

### 1.4 European Quality of Life Survey (EQLS)

**What it is:** Pan-European survey by Eurofound, conducted every 4 years since 2003. Covers objective circumstances and subjective well-being of EU citizens aged 18+.

**Relevant variables:**
- **Work-life balance** and care responsibilities
- **Quality ratings of public services** (healthcare, childcare, etc.)
- **Social care receipt, provision, and need**
- Happiness, life satisfaction, social exclusion
- Trust in institutions

**Accessibility:** Microdata available through UK Data Service (requires registration but is free for researchers). Aggregate findings published freely.

**Relevance to this project:** **MODERATE.** The "quality of public services" and "social care provision" variables are somewhat relevant to the "convenience" dimension. But it's Europe-only and doesn't directly measure "service delegation vs. self-service" behavior.

**Effort to integrate:** Moderate (3–5 hours to explore, extract relevant variables).

---

### 1.5 China Time Use Survey

**What it is:** National survey by China's National Bureau of Statistics. The Third National Time Use Survey was completed in 2024, covering time allocation across 13+ activity categories.

**Relevant variables:**
- **Labor and employment time:** Average 6h23m/day for employed persons
- **Housework time**
- **Purchasing goods/services time**
- **Caring for family members**
- **Culture, leisure, entertainment**
- ICT usage, location, social context of activities

**Accessibility:** **Problematic.** Summary statistics published via NBS press releases (in Chinese). Raw microdata access is opaque — no clear public repository or researcher application process documented. Summary data available from UN Statistics Division presentations.

**Relevance to this project:** **HIGH in theory, LOW in practice.** This is the most directly relevant dataset for the "Chinese side" of the comparison, but extracting usable data would require navigating Chinese-language government publications with uncertain microdata access.

**Effort to integrate:** High (5–10+ hours, mostly language barriers and data hunting). Likely only summary statistics are feasible.

---

### 1.6 World Values Survey (WVS)

**What it is:** Global survey of values and beliefs, covering ~100 countries across 7 waves (1981–2022). Free download in SPSS, Stata, SAS, R, CSV.

**Relevant variables:**
- **Autonomy Index:** Computed from child-rearing values (independence vs. obedience) — directly relevant to the autonomy vs. delegation cultural dimension
- **Secular vs. Traditional values**
- **Self-expression vs. Survival values** (the "Survself" factor)
- **Emancipative values**
- Work importance, life satisfaction, trust, competition attitudes
- Covers both European countries AND China

**Accessibility:** **Fully free** with simple registration. Multiple formats. Excellent documentation and codebooks.

**Relevance to this project:** **HIGH.** The Autonomy Index (independence vs. obedience as valued child qualities) is a direct proxy for the cultural dimension this model explores. The secular-traditional and self-expression axes of Inglehart-Welzel's Cultural Map align well with the European autonomy vs. Chinese service convenience framing. This is the most directly relevant dataset that covers both sides of the comparison.

**Effort to integrate:** Low–moderate (2–4 hours for targeted variable extraction).

---

### 1.7 ILO Working Hours Data (ILOSTAT)

**What it is:** Global labor statistics covering 98+ economies. Weekly and annual hours actually worked, disaggregated by gender, age, employment status.

**Relevant variables:**
- **Average weekly hours worked** by country
- **Hours by employment status** (wage workers vs. self-employed)
- Service sector employment rates (via linked World Bank data)

**Accessibility:** **Fully free** via ILOSTAT website with no registration required. Also available via World Bank Data portal.

**Relevance to this project:** **HIGH.** Provides the empirical anchor for "do Chinese workers actually work more hours?" — a core premise of the model. China's average 49 hours/week (2023) vs. EU averages of 36–40 hours/week is a critical stylized fact.

**Effort to integrate:** Very low (~1 hour to pull key numbers).

---

### 1.8 World Bank – Service Sector Employment Data

**What it is:** "Employment in services (% of total employment)" and "Services value added (% of GDP)" by country.

**Relevant variables:**
- Service sector employment share by country
- Service sector contribution to GDP

**Accessibility:** **Fully free** via data.worldbank.org. No registration.

**Relevance to this project:** **MODERATE.** Provides context for whether higher service-sector employment correlates with the "convenience economy" phenomenon. Useful as background context but doesn't directly measure delegation behavior.

**Effort to integrate:** Very low (~30 minutes).

---

### 1.9 Other Potentially Relevant Sources

| Source | Relevance | Access | Notes |
|--------|-----------|--------|-------|
| **Meituan/Ele.me gig economy reports** | High (Chinese delivery/service economy data) | Summary reports only (Chinese language) | Could provide anecdotal "convenience economy" statistics |
| **China Labor Statistical Yearbook** | Moderate (formal working hours by sector) | Partially free via NBS | Supplements ILO data |
| **EU-SILC (EU Statistics on Income and Living Conditions)** | Low–Moderate | Eurostat microdata application | Income, deprivation, work intensity |
| **ISSP (International Social Survey Programme)** | Moderate | Free for researchers | Work orientations module has work hours, work-life conflict |

---

## 2. Critical Analysis: Is External Data Actually Needed?

### 2.1 Types of ABMs and Their Data Requirements

Agent-based models in social science exist on a spectrum:

| Type | Purpose | Data Requirement | Examples |
|------|---------|-----------------|----------|
| **Theoretical / Exploratory** | Generate insight, explore mechanisms, test "what if" scenarios | Minimal — stylized facts sufficient | Schelling segregation, Epstein Sugarscape, Axelrod cooperation |
| **Middle-range** | Explain specific phenomena with empirically grounded parameters | Moderate — key parameters informed by data | Opinion dynamics models calibrated to survey data |
| **Calibrated / Predictive** | Replicate and predict specific empirical patterns | Extensive — formal calibration required | Epidemiological ABMs, urban traffic models |

### 2.2 Standard Practice in Computational Social Science

**The Epstein/Generativist tradition:** Joshua Epstein's foundational principle — "If you didn't grow it, you didn't explain it" — does **not** require empirical calibration. It requires demonstrating that simple, plausible micro-rules can *generate* observed macro-patterns. The Schelling segregation model, arguably the most influential ABM in social science, uses zero empirical data. It demonstrates a *mechanism* (mild in-group preference → total segregation) rather than calibrating against census tract data.

**Standard practice for theory-building ABMs:**
- Use **stylized facts** (widely accepted empirical observations) to motivate parameters and validate outputs
- Perform **sensitivity analysis** over parameter ranges rather than pinning down exact values
- Focus on **qualitative pattern matching** — does the model produce the *type* of dynamics observed? — not quantitative fit
- Cite empirical literature in the paper to justify "plausible" parameter ranges, without formally calibrating

**What reviewers expect:** For a theoretical ABM in venues like JASSS (Journal of Artificial Societies and Social Simulation), reviewers expect (1) clear motivation from real-world phenomena, (2) plausible parameter choices, (3) sensitivity analysis, and (4) discussion of how findings relate to empirical evidence. They do **not** expect formal calibration for exploratory models.

### 2.3 Pros and Cons for THIS Specific Project

#### Pros of Using Empirical Data
1. **Credibility:** Anchoring key parameters (e.g., working hours, service sector size) in real numbers makes the model more persuasive
2. **Motivation:** Real data helps justify WHY this model matters (e.g., "Chinese workers average 49 hrs/week vs. 36 hrs in Germany")
3. **Validation reference:** If the model reproduces known patterns (e.g., higher work hours correlating with lower self-reported autonomy), it increases confidence in the model's mechanisms
4. **Skill demonstration:** The project document explicitly lists "data stewardship and using data to inform and validate simulation models" as a target skill

#### Cons of Using Empirical Data
1. **Time cost:** The 2-week timeline is tight. Data cleaning, transformation, and integration could consume 3–5 days that should go toward model development and visualization
2. **False precision:** Calibrating a theoretical model to specific numbers implies a level of accuracy the model doesn't warrant. This can be misleading
3. **No direct dataset exists:** No dataset directly measures "service delegation vs. self-service behavior." Any data usage would be proxies, introducing additional assumptions
4. **Scope creep:** Data integration often reveals inconsistencies and missing values, leading to rabbit holes
5. **Methodological mismatch:** The project explores a theoretical mechanism (convenience→involution spiral). Precise calibration isn't necessary to demonstrate whether the mechanism *can* produce involution dynamics

#### The Core Tension
The project requirement document specifically mentions "Data stewardship and using data to inform and validate simulation models" as a skill to demonstrate. This creates a practical incentive to include *some* data integration, even though the ABM itself doesn't strictly require it.

### 2.4 Is Data Integration Realistic in 2 Weeks?

**Full calibration:** No. Absolutely not. Formal calibration (SMD, Bayesian calibration, indirect inference) requires weeks to months and is inappropriate for an exploratory model.

**Stylized facts from aggregate data:** Yes, very realistic. Pulling 5–10 key numbers from ILO, OECD, and WVS takes 2–4 hours total.

**Light data integration (parameter ranges):** Feasible if scoped tightly. Using 2–3 variables from WVS + ILO to define parameter ranges would take 1–2 days and add genuine value.

---

## 3. Recommendation

### The "Strategic Minimum" Approach

**Use external data, but minimally and selectively.** Specifically:

#### Tier 1: Use Immediately (2–3 hours total)
These provide "stylized facts" that motivate and ground the model:

| Data Point | Source | Use in Model |
|-----------|--------|-------------|
| Average weekly working hours: China (~49h) vs. Germany (~34h) vs. France (~36h) vs. EU average (~37h) | ILO / OECD | Anchor the "working hours" parameter range |
| Service sector employment share: China (~47%) vs. EU (~72%) | World Bank | Contextualize the "service delegation" density |
| Autonomy Index values by country | WVS | Anchor the "autonomy preference" parameter across cultures |
| Life satisfaction scores by country | OECD BLI | Validation: does the model's "well-being" output correlate with real satisfaction differences? |

#### Tier 2: Light Integration if Time Permits (1–2 days)
- Download WVS Wave 7 data, extract Autonomy Index and work importance values for China, Germany, France, Sweden, and use these as agent "culture profiles" in the model
- Create a simple comparison table of time-use allocation (paid work vs. domestic work vs. leisure) from HETUS aggregate tables for European countries, contrasted with China Time Use Survey summary statistics

#### Tier 3: Skip Entirely
- HETUS microdata (access barriers too high)
- China Time Use Survey microdata (access barriers, language barriers)
- Formal calibration of any kind
- EU-SILC, EQLS microdata (marginal value for high effort)

### How to Present This in the Project

Frame data usage as **"empirically grounded theoretical modeling"**:

> "Our model is theoretical and exploratory in the Epstein (2006) generativist tradition. We do not calibrate to specific empirical targets. However, we ground our parameter choices in empirical stylized facts drawn from ILO working hours data, the World Values Survey autonomy index, and OECD well-being indicators, and we discuss our model outputs in relation to observed cross-national patterns."

This language simultaneously:
1. Demonstrates data stewardship (a stated project goal)
2. Sets appropriate expectations (no false precision)
3. Follows established methodological standards for theoretical ABMs
4. Is honest about the model's scope

### Summary Table

| Dataset | Use? | Effort | Value |
|---------|------|--------|-------|
| ILO Working Hours | **Yes** | ~1h | High — anchors core premise |
| WVS Autonomy Index | **Yes** | ~2–4h | High — culture parameter |
| OECD Better Life Index | **Yes** | ~1h | Moderate — validation reference |
| World Bank Service Employment | **Yes** | ~30min | Moderate — context |
| HETUS Aggregate Tables | **Maybe** | ~2–3h | Moderate — time use comparison |
| China Time Use Summary Stats | **Maybe** | ~3–5h | Moderate — but access issues |
| EQLS | **No** | ~5h+ | Low marginal value |
| HETUS Microdata | **No** | Days | Access barriers |
| China TUS Microdata | **No** | Days | Access + language barriers |

**Bottom line:** ~4–6 hours of targeted data gathering provides 90% of the empirical grounding value. Anything beyond that faces sharply diminishing returns given the timeline and the model's theoretical nature.
