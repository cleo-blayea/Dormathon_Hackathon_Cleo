# GenBuddy DORMATHON 2026 — Story Document

## Audience & Purpose

- **Track 2 judges** evaluating "Agentic Solutions"
- Need to see: real problem → real AI agent → real evidence
- Non-engineering judges must understand the value; engineering judges must see depth

## Narrative Arc (10 slides)

The deck follows the classic problem-solution-proof-value-close arc, but emphasizes the **AI agent's adaptive behavior** as the differentiator:

1. **Cover** — project identity
2. **Business Problem** — why SMEs need this
3. **Our Solution** — what GenBuddy does
5. **System Architecture** — how data flows (engineering vs AI split)
5. **Agentic Workflow** — what makes it genuinely agentic
6. **Product Demonstration** — visual proof (dashboard screenshot)
7. **Investigation Results** — concrete findings from real investigations
8. **Proof of Dynamic AI Planning** — the agent changed strategy per question
9. **Business Value and Limitations** — honest assessment
10. **Conclusion and Demo Access** — close + links

## Key Claims (must be evidence-backed)

### Verified facts (use freely)

- 176 generator telemetry records + 176 ATS events + 4 maintenance records (all simulated)
- 3 scenarios: Normal Operation (29 confirmed transfers), Overheating (coolant 44.8°C → 107.7°C at 70% load), ATS Failure (11 FAILED transfers, 9-min facility outage)
- WorkBuddy performed 3 investigations (readiness, root cause, verification/correction)
- 7 AI reports in `reports/ai_*.md`
- Investigation 1: 13 planned steps, ~20 tool executions
- Investigation 2: 8 steps, ~5 tool executions, focused on failure window
- Agent found `FACILITY_NO_POWER` alarm in `alarm_events` field — script missed this
- Agent performed cross-scenario thermal comparison: 9.8 percentage points more load → 22.8°C higher temperature
- Agent self-corrected temperature rise rate calculation in 3 report files (4 instances)
- Deterministic Python: validate_data.py (13 checks), fault_investigation.py
- Reference generator: AI Power ASC344, 344 kVA / 275 kW, DSE6120 controller

### Limitations to mention (per user requirement)

- All data is simulated — no physical equipment
- Manual WorkBuddy triggering (user copies question from dashboard to WorkBuddy)
- No direct Flask → WorkBuddy API integration available
- No validated real-world cost savings
- 105°C/107.7°C DSE6120 thresholds are simulation assumptions (UNVERIFIED)

### Items NOT to invent (per user requirement)

- Team member names (not provided)
- Real-world testimonials
- Specific cost-savings figures
- Live WorkBuddy execution screenshots (only the agent execution log + actual reports exist)
- GitHub URL or deployed URL (use clearly marked placeholders)

## Slide Structure (verbatim from user spec)

### Slide 1 — Title
- Title: "GenBuddy: AI-Powered Backup Generator Maintenance Assistant"
- Subtitle: "DORMATHON 2026 — Track 2: Agentic Solutions"
- Note: "SIMULATED HISTORICAL DATA" disclaimer

### Slide 2 — Business Problem
- SMEs with standby generators often lack dedicated technical staff
- Visualize with a small supermarket as illustrative business example
- First sign of trouble = a dark building
- Three failure modes: no start, no transfer, no sustained run

### Slide 3 — Our Solution
- Convert telemetry, ATS events, maintenance records
- Into understandable readiness assessments
- Into prioritized maintenance recommendations
- Diagram: data sources → GenBuddy → actionable insights

### Slide 4 — System Architecture
- Flask dashboard (read-only demo or full local mode)
- User submits question → JSON request file
- User copies question to WorkBuddy (manual trigger)
- WorkBuddy LLM agent investigates using Python tools
- Report files written to outputs/
- Flask dashboard displays results
- Split visualization: deterministic Python (left) vs WorkBuddy reasoning (right)

### Slide 5 — Agentic Workflow
- One Prompt → One Goal → End-to-End Execution
- 5 stages: Plan → Execute Tools → Check Evidence → Reason About Uncertainty → Produce Report

### Slide 6 — Product Demonstration
- Show GenBuddy AI Investigation Center
- 4 example questions
- Use genuine dashboard screenshot from `test_data/dashboard_playback.png`

### Slide 7 — Investigation Results
- Scenario A: Normal Operation (INFO, no action)
- Scenario B: Overheating at 70% load (HIGH priority WO-02)
- Scenario C: ATS Transfer Failure (CRITICAL priority WO-01)
- Distinguish observed simulated evidence from suspected causes

### Slide 8 — Proof of Dynamic AI Planning
- Side-by-side comparison
- Inv 1 (Readiness): 13 steps, 20 tool calls, all 356 records, cross-scenario analysis
- Inv 2 (Root Cause): 8 steps, ~5 tool calls, 92 failure-window records, timeline reconstruction
- Different plans, scopes, tools, deliverables

### Slide 9 — Business Value and Limitations
- Value: maintenance prioritization, contractor communication
- Limitations: simulated data, manual triggering, no validated savings, no physical equipment

### Slide 10 — Conclusion and Demo Access
- Summary of value
- Placeholders for GitHub URL and deployed app URL (clearly labeled as placeholders)

## Tone & Style

- Confident but honest — "we proved it works on simulated data; here's what we'd do next"
- Use real numbers from the project (176 telemetry records, 11 FAILED transfers, 107.7°C, 9-minute outage)
- Avoid marketing language; favor engineering precision
- Diagrams first, text second; each slide's main message must be clear without reading body copy