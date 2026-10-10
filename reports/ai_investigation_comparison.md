# GenBuddy -- Investigation Strategy Comparison

> **SIMULATED HISTORICAL DATA** -- This document demonstrates dynamic adaptation: the WorkBuddy AI agent changed its investigation strategy based on the specific business question asked.

---

## Two Investigations, Two Strategies

### Investigation 1: Readiness Assessment

**Business owner request:** "Is my backup generator ready for the next power outage? Investigate the available telemetry, ATS events and maintenance history, identify potential problems, and prepare a prioritized maintenance action plan."

| Dimension | Approach |
|---|---|
| **Question type** | Forward-looking ("will it work next time?") |
| **Scope** | All 3 scenarios (Normal, Overheating, ATS Failure) |
| **Planning** | 13 steps: validate, run scripts, read all CSVs, query API, examine 12 critical timestamps, full thermal progression, full ATS sequence, cross-scenario comparison, general health, synthesize |
| **Tools executed** | 20 tool calls (scripts, API queries, direct CSV reads, curl) |
| **Key analysis** | Cross-scenario thermal comparison: 60% load vs 70% load, 84.9C peak vs 107.7C shutdown |
| **Agent's unique findings** | (1) FACILITY_NO_POWER alarm in alarm_events field -- script didn't examine this field (2) Cross-scenario comparison showing 9.8 percentage points more load caused 22.8C higher temperature |
| **Deliverables** | Readiness verdict (NOT READY), 3 prioritized work orders (CRITICAL, HIGH, INFO), full execution log |
| **Maintenance angle** | "Was it serviced recently?" -- yes, 17 days before, both failed systems were serviced |

### Investigation 2: Root Cause Analysis

**Business owner request:** "My generator shut down during last week's power outage. Investigate what happened, identify the root cause, and tell me exactly what to tell my maintenance contractor to fix."

| Dimension | Approach |
|---|---|
| **Question type** | Backward-looking ("why did it fail last time?") |
| **Scope** | ATS failure scenario only (drilled into the specific failure event) |
| **Planning** | 8 steps: validate, run scripts, read ATS failure window, read generator failure window, read maintenance history, reconstruct timeline, analyze root cause, prepare contractor briefing |
| **Tools executed** | 5 tool executions (2 scripts + 3 direct CSV reads) + 3 LLM reasoning steps (timeline, root cause, maintenance adequacy) |
| **Key analysis** | Timestamp-level timeline reconstruction (30-to-60-second sampling intervals): ATS commanded source vs actual position mismatch, 0A current consistent with unsuccessful transfer, 4-phase failure sequence |
| **Agent's unique findings** | (1) Distinguished observed facts (0A current, commanded vs actual mismatch) from suspected causes (contactor seizure, wiring fault, sensor fault) (2) Assessed maintenance adequacy: visual inspection vs functional test |
| **Deliverables** | Failure timeline (4 phases, 30-to-60-second intervals), root cause analysis (3 suspected causes ranked by probability), contractor briefing (specific check instructions) |
| **Maintenance angle** | "Was the service adequate?" -- ATS contacts were inspected 17 days before, but visual inspection missed the impending failure |

---

## How the Strategy Changed

| Aspect | Investigation 1 | Investigation 2 | Why It Changed |
|---|---|---|---|
| **Data scope** | All 352 records (176 gen + 176 ATS) across all 3 scenarios | 88 records in failure window only (44 gen + 44 ATS) | Different question requires different focus |
| **Analysis method** | Cross-scenario comparison (broad) | Timeline reconstruction (deep) | Readiness needs breadth; root cause needs depth |
| **Tool selection** | Flask API queries + direct CSV reads | Direct CSV reads only (API not needed for focused analysis) | Agent decided API cross-verification was unnecessary for a focused timeline |
| **Deliverable format** | Prioritized work orders (technician-facing) | Contractor briefing (contractor-facing) | Different audience requires different format |
| **Key metric** | Peak temperature (107.7C) | Zero current (0A) throughout failure | Readiness looks at what went wrong broadly; root cause looks at the specific failure mechanism |
| **Maintenance question** | "When was last service?" | "Was the service adequate?" | Readiness checks compliance; root cause evaluates effectiveness |

---

## Proof of Dynamic Adaptation

The agent did **not** reuse the same plan for both investigations. Key evidence of adaptation:

1. **Different step count:** 13 planned steps (Inv 1) vs 8 steps (5 tool executions + 3 LLM reasoning) (Inv 2) -- the agent simplified its plan for a more focused question
2. **Different data scope:** All scenarios (Inv 1) vs single failure window (Inv 2) -- the agent narrowed its analysis to the relevant event
3. **Different tool selection:** API cross-verification included (Inv 1) vs direct CSV reads only (Inv 2) -- the agent decided cross-verification was unnecessary for a focused timeline
4. **Different deliverable format:** Work orders (Inv 1) vs contractor briefing (Inv 2) -- the agent matched the output to the stated audience
5. **Different analysis method:** Cross-scenario statistical comparison (Inv 1) vs chronological timeline reconstruction (Inv 2) -- the agent chose the analytical method that fit the question

---

## Summary

| Metric | Investigation 1 | Investigation 2 |
|---|---|---|
| Business question | Readiness | Root cause |
| Planned steps | 13 | 8 (5 tools + 3 reasoning) |
| Tools executed | 20 | 5 (scripts + CSV reads) |
| Data records examined | All 356 (176 gen + 176 ATS + 4 maint) | 92 (44 gen + 44 ATS + 4 maint, failure window) |
| Deliverables | 3 reports (assessment, work orders, log) | 2 reports (root cause, contractor briefing) |
| Key finding | NOT READY -- 2 problems, cross-scenario comparison | ATS did not transfer -- 0A current, position mismatch, and failed confirmations are consistent with unsuccessful transfer |

Both investigations used the same data sources and scripts, but the agent's **plan, scope, tools, analysis method, and deliverable format** all changed based on the business question. This demonstrates dynamic adaptation -- the core requirement for Track 2 (Agentic Solutions).
