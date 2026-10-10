# GenBuddy — DORMATHON 2026 Demo Guide

> Quick-reference for running the live demonstration.

## Prerequisites

- Python venv (already set up): `C:/Users/cleol/.workbuddy-ai/binaries/python/envs/genbuddy/`
- Dependencies installed: Flask, waitress
- Project root: `C:/Users/cleol/Documents/Dormathon/GenBuddy_Hackathon/`

## Part 1 — Start the Dashboard (30 seconds)

Open a terminal and run:

```bash
cd C:/Users/cleol/Documents/Dormathon/GenBuddy_Hackathon
"C:/Users/cleol/.workbuddy-ai/binaries/python/envs/genbuddy/Scripts/python.exe" app.py
```

Open browser to: **http://127.0.0.1:5000**

You should see the GenBuddy dashboard with:
- Simulated data banner
- 12 generator status cards
- 4 interactive charts
- ATS monitoring panel
- Scenario selector with playback slider
- AI Investigation Center
- Fault findings and reports

## Part 2 — Show Dashboard Features (2-3 minutes)

### Telemetry Playback
1. Use the **timestamp slider** at the top to scrub through the 176 data points
2. Click the **Scenario dropdown** — select each scenario:
   - **Normal Operation** — successful ATS transfer, 60% load
   - **Overheating** — coolant rising 44.8C to 107.7C, shutdown
   - **ATS Failure** — 11 failed transfers, generator ran with no load
3. Click **Play** to auto-advance through the timeline
4. Point out the ATS panel updating: utility status, transfer confirmation, alarms

### Fault Findings
- Scroll to the **Fault Findings** section
- Show the 3 findings: INFORMATIONAL (normal), HIGH (overheating), CRITICAL (ATS failure)
- Click report links to download the full investigation reports

### AI Investigation Center (if showing the full workflow)
1. Type a question in the textarea, e.g.: "Is my backup generator ready for the next power outage?"
2. Click **Submit Investigation**
3. Show the request being saved (status: awaiting_workbuddy)
4. Click **Copy Request** to copy the question
5. Paste into WorkBuddy AI workspace to trigger the agent investigation
6. Watch the dashboard auto-poll and show status updates (investigating -> generating_reports -> completed)

## Part 3 — Run Engineering Scripts (1-2 minutes)

Open a **second terminal** and run:

### Data Validation (13 automated checks)
```bash
cd C:/Users/cleol/Documents/Dormathon/GenBuddy_Hackathon
"C:/Users/cleol/.workbuddy-ai/binaries/python/envs/genbuddy/Scripts/python.exe" scripts/validate_data.py
```
Expected output: `Issues: 0, Warnings: 0` — all 13 checks pass. Exit code 0.

### Fault Investigation (autonomous workflow)
```bash
"C:/Users/cleol/.workbuddy-ai/binaries/python/envs/genbuddy/Scripts/python.exe" scripts/fault_investigation.py
```
Expected output: 3 scenarios identified (NORMAL_OPERATION, OVERHEATING, ATS_TRANSFER_FAILURE).
CRITICAL: 1, HIGH: 1, INFORMATIONAL: 1. Reports generated in `reports/`.

## Part 4 — Run Autonomous Agent Test (1-2 minutes)

This demonstrates the AI agent's ability to detect unexpected anomalies:

```bash
"C:/Users/cleol/.workbuddy-ai/binaries/python/envs/genbuddy/Scripts/python.exe" scripts/test_autonomous.py
```

Expected output:
- Validation finds 1 issue in test data (exit code 1 — correctly detected, NOT a crash)
- 3 scenario windows correctly identified with no mixing
- 1 injected anomaly detected at 2026-06-01T08:25:30
- Reports generated in `test_reports/`

## Part 5 — Public Demo Mode (optional, for judges)

If you want to show the read-only public deployment mode:

```bash
# Option A: Environment variable
PUBLIC_DEMO_MODE=1 "C:/Users/cleol/.workbuddy-ai/binaries/python/envs/genbuddy/Scripts/python.exe" app.py

# Option B: WSGI entry point (auto-sets PUBLIC_DEMO_MODE=1)
"C:/Users/cleol/.workbuddy-ai/binaries/python/envs/genbuddy/Scripts/waitress-serve.exe" --host=0.0.0.0 --port=5000 wsgi:application
```

In this mode:
- All write endpoints return 403 (submit, analyze, reset, request system)
- Read-only content fully available (telemetry, playback, reports, AI summary)
- Dashboard shows a "Read-Only Public Demo" banner

## Quick Reference — Key Files

| What | Path |
|------|------|
| Dashboard | http://127.0.0.1:5000 |
| Data (3 CSVs) | `data/` |
| Engineering scripts | `scripts/validate_data.py`, `scripts/fault_investigation.py` |
| Autonomous test | `scripts/test_autonomous.py` |
| Reports | `reports/` (health report, action plan, execution log, AI reports) |
| AI evidence | `docs/workbuddy_usage_evidence.md` |
| Presentation | `presentation/GenBuddy_DORMATHON_2026.pptx` |
| README | `README.md` |

## Troubleshooting

- **Port 5000 in use**: Kill the old process, or change the port in `app.py` line `app.run(host="127.0.0.1", port=5000)`
- **Module not found**: Make sure you're using the genbuddy venv Python, not system Python
- **Dashboard shows no data**: Check that `data/*.csv` files exist (176 records each)
- **Scripts fail**: Run from the project root directory, not from `scripts/`
