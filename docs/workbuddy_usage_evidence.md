# WorkBuddy Usage Evidence for GenBuddy

> **DORMATHON 2026 Track 2 -- Agentic Solutions**
>
> This document provides evidence that WorkBuddy AI was used to develop GenBuddy and to act as the runtime investigation agent. It explains how, where, and in what scenario WorkBuddy was used.

---

## 1. How WorkBuddy Was Used to Develop GenBuddy

The entire GenBuddy project was built using WorkBuddy AI as the development agent. WorkBuddy performed the following development tasks:

| Phase | What WorkBuddy Did | Evidence |
|-------|---------------------|----------|
| Project setup | Created directory structure, README.md, generator specs | `README.md`, `docs/generator_specs.json` |
| Data generation | Wrote and executed `scripts/generate_data.py` to create 176 timestamped telemetry records + 176 ATS events + 4 maintenance records | `data/generator_data.csv`, `data/ats_events.csv`, `data/maintenance_history.csv` |
| Data validation | Wrote `scripts/validate_data.py` with 13 automated checks (column presence, electrical consistency, timestamp sync, scenario verification, etc.) | `scripts/validate_data.py`, `data/validation_report.md` |
| Fault investigation | Wrote `scripts/fault_investigation.py` with pattern-based detection (NORMAL_OPERATION, OVERHEATING, ATS_TRANSFER_FAILURE) | `scripts/fault_investigation.py`, `reports/generator_health_report.md`, `reports/maintenance_action_plan.csv` |
| Web dashboard | Wrote `app.py` (Flask backend with 12 API endpoints) and `templates/index.html` (playback UI, charts, ATS panel, findings, reports) | `app.py`, `templates/index.html` |
| Report generation | WorkBuddy agent itself generated 7 AI investigation reports through runtime LLM reasoning | `reports/ai_*.md` (7 files) |
| Feature iteration | Added AI Investigation Center, request system, demo-reset, output file viewer, security hardening | `app.py` endpoints, `templates/index.html` sections |

WorkBuddy was not a tool that was "plugged in" -- it was the agent that planned, wrote, tested, and iterated on every component of GenBuddy.

---

## 2. How WorkBuddy Acted as the Runtime AI Investigation Agent

WorkBuddy performed **three genuine AI investigations** using the GenBuddy data and tools. Each investigation was triggered by a natural-language business question pasted into the WorkBuddy workspace:

### Investigation 1: Readiness Assessment

**Trigger question:** "Is my backup generator ready for the next power outage? Investigate the available telemetry, ATS events and maintenance history, identify potential problems, and prepare a prioritized maintenance action plan."

**Agent's plan (13 steps, created before executing any tools):**
1. Run data validation script
2. Run fault investigation script
3. Read script-generated reports
4. Read maintenance history
5. Read generator specifications
6. Read raw CSV data directly (independent verification)
7. Start Flask server and query API endpoints (cross-verification)
8. Examine 12 critical timestamps
9. Examine full thermal progression
10. Examine full ATS failure sequence
11. Perform cross-scenario comparison
12. Analyze battery, fuel, and general health
13. Synthesize findings with LLM reasoning

**Key agent findings (beyond what the scripts found):**
- FACILITY_NO_POWER alarm in ATS `alarm_events` field -- the script did not examine this field
- Cross-scenario thermal comparison: 60.2% load peaked at 84.9C vs 70.0% load reached 107.7C shutdown (9.8 percentage points more load caused 22.8C higher temperature)
- Maintenance adequacy assessment: both failed systems (ATS and cooling) were serviced 17 days before the failure

**Verdict:** NOT READY FOR SERVICE

**Deliverables:**
- `reports/ai_readiness_assessment.md` (262 lines) -- full readiness assessment
- `reports/ai_maintenance_work_orders.md` (172 lines) -- 3 prioritized work orders (CRITICAL, HIGH, INFORMATIONAL)
- `reports/ai_agent_execution_log.md` (362 lines) -- full tool/decision audit trail

### Investigation 2: Root Cause Analysis

**Trigger question:** "My generator shut down during last week's power outage. Investigate what happened, identify the root cause, and tell me exactly what to tell my maintenance contractor to fix."

**Agent's plan (8 steps -- simplified from Investigation 1):**
1. Run validation script
2. Run fault investigation script
3. Read ATS failure window from CSV (44 records)
4. Read generator failure window from CSV (44 records)
5. Read maintenance history
6. Reconstruct 4-phase failure timeline (LLM reasoning)
7. Analyze root cause (LLM reasoning)
8. Assess maintenance adequacy (LLM reasoning)

**Key agent findings:**
- Distinguished observed facts (0A current, commanded vs actual position mismatch) from suspected causes (contactor seizure, wiring fault, sensor fault)
- Reconstructed timestamp-level timeline: 30-to-60-second sampling intervals, 11 consecutive FAILED transfers, 10-minute no-load run, safety shutdown
- Assessed maintenance adequacy: ATS contacts were inspected 17 days before but visual inspection may not have been sufficient — a functional transfer test could plausibly have identified the problem

**Deliverables:**
- `reports/ai_root_cause_analysis.md` (178 lines) -- 4-phase failure timeline, root cause analysis
- `reports/ai_contractor_briefing.md` (145 lines) -- plain-language briefing with specific check instructions

### Investigation 3: Verification and Correction

**Trigger question:** Same as Investigation 1 (re-run from dashboard to demonstrate end-to-end flow).

**Agent's actions:**
- Re-executed all scripts and verified all 352 records independently
- Found and corrected a temperature rise rate calculation error in 3 report files (4 instances):
  - Original: "1.59C/min (55.0C over 34 min)" -- incorrect delta and rate
  - Corrected: "0.56C/min (19.2C over 34 min, from 88.5C at 11:29:30 to 107.7C at 12:03:30)" -- based on actual CSV data
- Verified all 7 AI reports accessible via Flask API (HTTP 200)
- Verified `/api/ai_summary` endpoint returns correct structured data after corrections

---

## 3. Engineering Tools Executed by the Agent

The WorkBuddy agent executed the following engineering tools during its investigations:

| Tool | Type | What It Does | Invocations |
|------|------|--------------|-------------|
| `scripts/validate_data.py` | Python script | 13 automated data integrity checks (columns, electrical consistency, timestamps, scenarios, duplicates) | 3 times (Inv 1, Inv 2, Inv 3) |
| `scripts/fault_investigation.py` | Python script | Pattern-based fault detection (NORMAL_OPERATION, OVERHEATING, ATS_TRANSFER_FAILURE) and report generation | 3 times (Inv 1, Inv 2, Inv 3) |
| Direct CSV reads | Bash/file reads | Agent independently read raw CSV data to verify script findings -- 352 records (176 gen + 176 ATS + 4 maint) | 2 times (Inv 1, Inv 2) |
| Flask API queries | curl HTTP requests | Cross-verified data consistency between direct CSV reads and API (`/api/scenarios`, `/api/findings`) | 1 time (Inv 1) |
| Report file writes | File writes | Agent wrote 7 `.md` report files to `reports/` directory | Inv 1 (3 files), Inv 2 (2 files), corrections (3 files) |

The agent did not use any external AI API. All reasoning was performed by the WorkBuddy agent's runtime LLM.

---

## 4. How the Agent Adapted Its Workflow

The agent changed its strategy based on the business question. This is documented in `reports/ai_investigation_comparison.md`:

| Aspect | Investigation 1 (Readiness) | Investigation 2 (Root Cause) | Why It Changed |
|--------|---------------------------|------------------------------|----------------|
| Question type | Forward-looking ("will it work next time?") | Backward-looking ("why did it fail?") | Different question requires different approach |
| Data scope | All 356 records, all 3 scenarios | 92 records, failure window only | Readiness needs breadth; root cause needs depth |
| Planning | 13 planned steps | 8 steps (simplified) | Focused question requires fewer steps |
| Tool selection | Flask API + direct CSV reads | Direct CSV reads only | Agent decided API cross-verification unnecessary for focused timeline |
| Analysis method | Cross-scenario statistical comparison | Chronological timeline reconstruction | Different analytical method fits different question |
| Deliverable format | Prioritized work orders (technician-facing) | Contractor briefing (contractor-facing) | Different audience requires different format |
| Maintenance question | "When was last service?" | "Was the service adequate?" | Readiness checks compliance; root cause evaluates effectiveness |

**Key evidence of adaptation:** The agent did not reuse the same plan. It independently decided step count, data scope, tool selection, analysis method, and deliverable format for each question.

---

## 5. Actual Reports and Recommendations Generated

### Investigation 1 Deliverables

**`reports/ai_readiness_assessment.md`** (262 lines):
- Verdict: NOT READY FOR SERVICE
- 2 problems identified:
  1. [CRITICAL] ATS transfer failure -- 11 consecutive FAILED transfers, 9-minute facility outage
  2. [HIGH] Over-temperature shutdown -- coolant reached 107.7C at 70% load
- Cross-scenario comparison: 9.8 percentage points more load caused 22.8C higher temperature

**`reports/ai_maintenance_work_orders.md`** (172 lines):
- WO-01 [CRITICAL]: ATS Transfer Failure Investigation and Repair
- WO-02 [HIGH]: Cooling System Investigation and Repair
- WO-03 [INFORMATIONAL]: Continue Scheduled Maintenance

### Investigation 2 Deliverables

**`reports/ai_root_cause_analysis.md`** (178 lines):
- Root cause: ATS transfer failure -- contactor did not transfer building load despite correct command
- Generator healthy: 399-402V, 49.9-50.2Hz, 0A (no load transferred)
- 4-phase failure timeline (30-to-60-second intervals)

**`reports/ai_contractor_briefing.md`** (145 lines):
- Plain-language summary for maintenance contractor
- Specific check instructions (do NOT assume mechanical failure before ruling out sensor issues)
- Functional transfer test requirement

### Investigation 3 Deliverables

- Corrected temperature rise rate in 3 report files (4 instances)
- Verified all reports accurate and accessible

### Strategy Comparison

**`reports/ai_investigation_comparison.md`** (51 lines):
- Side-by-side comparison of the two investigation strategies
- Proves dynamic adaptation: different plans, scopes, tools, methods, deliverables

---

## 6. Suggested WorkBuddy Screenshots for Presentation

The following are real WorkBuddy conversation moments that should be captured as screenshots for presentation evidence. Do NOT fabricate screenshots -- capture these from the actual WorkBuddy sessions.

| # | What to Capture | Why It Matters |
|---|-----------------|----------------|
| 1 | WorkBuddy's investigation plan for Question 1 (13-step plan displayed before any tool execution) | Shows the agent plans before acting -- core agentic behavior |
| 2 | WorkBuddy executing `validate_data.py` (Bash tool call + 13/13 checks passed output) | Shows the agent uses engineering tools |
| 3 | WorkBuddy reading raw CSV data (Read tool with generator_data.csv showing 176 records) | Shows independent data verification |
| 4 | WorkBuddy's cross-scenario thermal comparison reasoning (text showing 60.2% vs 70.0% load analysis) | Shows LLM reasoning producing unique insights |
| 5 | WorkBuddy writing the readiness assessment report (Write tool creating ai_readiness_assessment.md) | Shows the agent generates real deliverables |
| 6 | WorkBuddy's investigation plan for Question 2 (8-step plan -- different from Question 1) | Shows dynamic adaptation |
| 7 | WorkBuddy's root cause analysis reasoning (distinguishing observed facts from suspected causes) | Shows the agent's diagnostic reasoning quality |
| 8 | WorkBuddy's contractor briefing (Write tool creating ai_contractor_briefing.md) | Shows audience-appropriate deliverable |
| 9 | WorkBuddy finding and correcting the temperature rise rate error (Edit tool on ai_readiness_assessment.md) | Shows the agent self-corrects |
| 10 | Dashboard showing AI Investigation Center with example questions and investigation results | Shows the end-to-end product |

---

## 7. Track 2 Judging Criteria Alignment

| Criterion | How GenBuddy Meets It |
|-----------|----------------------|
| Real Problem and User Value | Businesses with standby generators need to know if their backup will work during an outage. GenBuddy answers this question with data-driven investigation. |
| Agentic Workflow | WorkBuddy plans before acting, executes engineering tools, reads raw data independently, cross-verifies, and generates deliverables -- all without hardcoded logic. |
| Meaningful Use of WorkBuddy | WorkBuddy is both the development agent (built the entire project) and the runtime investigation agent (performed 3 genuine investigations with different strategies). |
| End-to-End Execution | Complete flow: user submits question -> request saved -> WorkBuddy investigates -> reports generated -> dashboard displays results -> files downloadable. |
| Usable & Verifiable Results | Dashboard displays verdict, problems, work orders, contractor briefing. All claims are traceable to raw CSV data. Security tested (path traversal blocked). |
