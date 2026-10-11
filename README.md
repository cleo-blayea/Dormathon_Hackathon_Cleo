# GenBuddy

**AI-Powered Backup Generator Readiness Monitoring for SMEs**
> Open https://dormathon-hackathon-cleo.onrender.com/ - read-only monitoring (generator telemetry, ATS events, historical playback, and published AI reports).
> **DISCLAIMER:** All data in this project is **simulated**. No real generator is connected, monitored, or controlled. Nothing in this repository interacts with physical equipment.

> **DORMATHON 2026 — Track 2: Agentic Solutions**

---

## 1. The Business Problem

Small and medium enterprises (SMEs) that rely on backup generators for business continuity face a critical question: **will the generator actually work when the next power outage hits?**

Typical SME generator management looks like this:

- A standby generator sits in a basement or yard, started only during outages.
- Maintenance is performed on a fixed schedule (e.g., quarterly) by an external contractor who does a visual inspection.
- Telemetry is available from the generator controller (e.g., Deep Sea DSE6120) but nobody reads it between services.
- ATS (Automatic Transfer Switch) operation is never load-tested — it is assumed to work.
- When an outage occurs, the generator may start but fail to transfer the load, overheat under sustained operation, or run out of fuel. The first indication of a problem is **a dark building**.

GenBuddy addresses this gap by providing:

1. **Telemetry playback** — timestamped historical data showing what happened during simulated utility failures.
2. **Pattern-based fault detection** — deterministic Python scripts that classify scenarios and flag anomalies.
3. **AI agent investigation** — WorkBuddy AI agent reads the data, executes engineering tools, reasons about findings, and generates actionable maintenance reports.

---

## 2. How the Input → WorkBuddy Investigation → Output Workflow Works

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Flask Dashboard (app.py)                                │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Read-only   │  │  Write (local│  │  Example AI  │  │
│  │  Data &      │  │  mode only)  │  │  Reports     │  │
│  │  Playback     │  │              │  │  (reports/)   │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
│        │                   │                    │        │
│  ┌─────┴────┐     ┌───────┴────────┐     ┌──────┴──────┐ │
│  │data/*.csv │     │requests/*.json │     │reports/     │ │
│  │13 columns │     │outputs/<id>/   │     │ai_*.md (7  │ │
│  │176 records│     │                │     │  files)     │ │
│  └───────────┘     └────────────────┘     └─────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │  WorkBuddy  │
                    │  AI Agent   │
                    │  (external) │
                    └─────────────┘
```

### Workflow Steps

1. **User submits a question** on the dashboard's AI Investigation Center (e.g., "Is my backup generator ready for the next power outage?").
2. **Flask saves the question** as a JSON file in `requests/` with status `awaiting_workbuddy`. Flask does **not** invoke WorkBuddy — the dashboard is a file manager, not an AI gateway.
3. **User copies the question** (Copy Request button) and pastes it into their WorkBuddy AI workspace.
4. **WorkBuddy agent investigates**:
   - Reads the pending request from `requests/` via curl to the Flask API
   - Updates status to `investigating`
   - Executes `validate_data.py` — 13 automated data integrity checks
   - Executes `fault_investigation.py` — pattern-based fault detection
   - Reads raw CSV data independently (356 records: 176 generator + 176 ATS + 4 maintenance)
   - Queries Flask API endpoints for cross-verification
   - Performs cross-scenario comparison and root cause analysis using LLM reasoning
   - Updates status to `generating_reports`
   - Writes report files to `outputs/<request_id>/`
   - Updates status to `completed`
5. **Dashboard auto-polls** every 5 seconds and displays the status timeline, then shows the completed output files with download links.

### Manual Triggering

The organizer confirmed: **WorkBuddy does not need to be directly integrated into the final application.** The agent is triggered manually (paste the question into WorkBuddy). This is a deliberate design choice — the dashboard manages files and displays results, while WorkBuddy provides the genuine AI reasoning. See `docs/api_integration_analysis.md` for a full analysis of why direct API integration is not available with the current WorkBuddy installation.

---

## 3. Deterministic Python vs. Genuine WorkBuddy LLM Reasoning

| Component                          | Type                      | What It Does                                                                                                                                                                                                   |
| ---------------------------------- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/generate_data.py`         | Deterministic Python      | Generates simulated telemetry, ATS events, and maintenance records                                                                                                                                             |
| `scripts/validate_data.py`         | Deterministic Python      | 13 automated checks: column presence, electrical consistency, timestamp sync, scenario verification, duplicates                                                                                                |
| `scripts/fault_investigation.py`   | Deterministic Python      | Pattern-based detection (NORMAL_OPERATION, OVERHEATING, ATS_TRANSFER_FAILURE) and report generation                                                                                                            |
| `app.py` (Flask backend)           | Deterministic Python      | Serves data, manages request files, provides API endpoints                                                                                                                                                     |
| `templates/index.html`             | Deterministic JavaScript  | Dashboard UI with playback, charts, ATS panel, findings                                                                                                                                                        |
| `/api/ask` endpoint                | Rule-based Python         | Keyword matching routes to pre-built analysis functions                                                                                                                                                        |
| **WorkBuddy agent investigations** | **Genuine LLM reasoning** | **Plans before acting, selects tools, reads raw data independently, performs cross-scenario comparison, reasons about root causes, adapts workflow per question, generates audience-appropriate deliverables** |

### What WorkBuddy Does That the Python Scripts Cannot

1. **Cross-scenario thermal comparison**: The scripts detect that Scenario 2 had overheating. WorkBuddy independently computed that a 9.8 percentage-point load increase (60.2% → 70.0%) caused a disproportionate 22.8°C temperature rise (84.9°C → 107.7°C), suggesting the cooling system may have limited thermal reserve at higher loads.
2. **Maintenance adequacy assessment**: The scripts report the last service date. WorkBuddy independently observed that both systems that later failed (radiator and ATS contacts) were serviced 17 days before the incident, and noted that visual inspection alone may not have been sufficient — functional load testing could plausibly have identified one or both issues before the incident.
3. **Workflow adaptation**: For Investigation 1 (readiness), WorkBuddy created a 13-step plan covering all 356 records and all 3 scenarios. For Investigation 2 (root cause), it created an 8-step plan focused on 92 records in the failure window. Different plans, different data scope, different analysis method, different deliverable format — all decided by the agent.
4. **Self-correction**: In Investigation 3, WorkBuddy found and corrected a temperature rise rate calculation error in 3 report files (4 instances), replacing incorrect values with data derived from actual CSV timestamps.

---

## 4. Public Read-Only Demo vs. Local Agent Demonstration

### Public Read-Only Demo

When deployed with `PUBLIC_DEMO_MODE=1`, the dashboard provides:

- Full telemetry playback (176 timestamped records with 13 parameters)
- ATS event history (176 records with transfer confirmations and alarms)
- Maintenance history
- Scenario filtering (Normal Operation, Overheating, ATS Failure)
- Interactive charts (voltage, current, power, temperature, fuel, oil pressure)
- ATS source state diagram
- Findings table (3 prioritized findings from deterministic analysis)
- Example AI Investigation Reports (7 WorkBuddy-generated reports)
- Report file downloads (whitelisted .md and .csv files)

**Disabled in public mode:**

- Submit Investigation (no new requests)
- Status updates (no agent-triggered updates)
- Demo Reset (no file deletion)
- Run Analysis (no script execution)
- Request listing and output file access (no local runtime files exposed)

### Reproducing the Local Agent Demonstration

To reproduce the full input → WorkBuddy → output workflow:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/cleo-blayea/Dormathon_Hackathon_Cleo.git
   cd GenBuddy_Hackathon
   pip install -r requirements.txt
   ```
2. **Start the dashboard in local mode:**
   ```bash
   python app.py
   ```
   The dashboard runs on <http://127.0.0.1:5000> (localhost only).
3. **Submit a question** in the AI Investigation Center. Click "Submit Investigation", then "Copy Request".
4. **Paste the question into WorkBuddy AI** (desktop app or browser). The agent will:
   - Detect the pending request via `GET /api/requests`
   - Update status to `investigating`
   - Execute engineering scripts
   - Read raw CSV data
   - Synthesize findings with LLM reasoning
   - Write reports to `outputs/<request_id>/`
   - Update status to `completed`
5. **The dashboard auto-polls** every 5 seconds and displays results when ready.

For evidence of genuine WorkBuddy usage, see:

- `docs/workbuddy_usage_evidence.md` — 7-section evidence document
- `reports/ai_*.md` — 7 actual AI-generated investigation reports
- `docs/api_integration_analysis.md` — analysis of WorkBuddy API integration options

---

## 5. Limitations

1. **Simulated historical data**: All telemetry comes from `scripts/generate_data.py`. No real generator is connected. The DSE6120 alarm thresholds are unverified — they are reasonable defaults, not manufacturer-confirmed values.
2. **Manual WorkBuddy triggering**: The dashboard does not automatically invoke the WorkBuddy agent. A human must copy the question from the dashboard and paste it into WorkBuddy. This is a deliberate design choice based on the organizer's clarification that WorkBuddy integration is not required — only proof of usage.
3. **Single-user request system**: The file-based request system stores JSON in `requests/` and outputs in `outputs/`. There is no authentication, no multi-user isolation, and no database. This is sufficient for local demonstration but not for production multi-user deployment.
4. **Local runtime files**: The `requests/` and `outputs/` directories contain local runtime artifacts (submitted questions, investigation outputs). These are excluded from the public deployment via `.gitignore` and the PUBLIC_DEMO_MODE flag.
5. **Rule-based Q&A**: The `/api/ask` endpoint uses keyword matching, not an LLM. It provides structured analysis based on deterministic data processing. Genuine LLM reasoning is demonstrated through the WorkBuddy agent investigations, not through this endpoint.
6. **ATS facility power indicator**: The `FACILITY_NO_POWER` alarm in the ATS event log is a simulated controller field, not an independent load-bus voltage measurement. It indicates possible building power loss but does not definitively confirm it. No load-bus voltage data is present in the dataset.

---

## 6. Reference Generator

| Parameter        | Value                         |
| ---------------- | ----------------------------- |
| Manufacturer     | AI Power                      |
| Model            | ASC344                        |
| Engine           | SDEC SC13G420D2               |
| Application      | Simulated standby generator   |
| Standby rating   | 344 kVA / 275 kW              |
| Output           | 400/230 V, three-phase, 50 Hz |
| Power factor     | 0.8                           |
| Engine speed     | 1500 rpm                      |
| Starting battery | 24 V                          |
| Fuel tank        | 522 L                         |
| Controller       | Deep Sea Electronics DSE6120  |

---

## 7. Project Structure

```
GenBuddy_Hackathon/
├── README.md                           ← this file
├── requirements.txt                    ← Python dependencies
├── .gitignore                          ← excludes runtime/test artifacts
├── wsgi.py                             ← WSGI entry point for production
├── app.py                              ← Flask backend (17 API endpoints)
├── templates/
│   └── index.html                      ← Dashboard frontend (playback, charts, AI center)
├── docs/
│   ├── generator_specs.json            ← reference generator specifications
│   ├── workbuddy_usage_evidence.md     ← proof of WorkBuddy usage (7 sections)
│   └── api_integration_analysis.md      ← WorkBuddy API integration feasibility analysis
├── scripts/
│   ├── generate_data.py                ← simulation data generator
│   ├── fix_data.py                     ← data correction script
│   ├── validate_data.py               ← 13-check validation script
│   └── fault_investigation.py          ← pattern-based fault detection + report generation
├── data/
│   ├── generator_data.csv              ← 176 timestamped telemetry records (13 columns)
│   ├── ats_events.csv                  ← 176 ATS event records (8 columns)
│   ├── maintenance_history.csv         ← 4 maintenance records
│   ├── validation_report.md            ← automated validation report
│   ├── DATA_INTEGRITY.md               ← data integrity documentation
│   └── backup/                         ← pre-correction backups (preserved)
├── reports/
│   ├── generator_health_report.md     ← health analysis with scenario findings
│   ├── maintenance_action_plan.csv    ← prioritized action items (3 findings)
│   ├── agent_execution_log.md         ← deterministic workflow execution trace
│   ├── ai_readiness_assessment.md     ← WorkBuddy Investigation 1: readiness (262 lines)
│   ├── ai_maintenance_work_orders.md  ← WorkBuddy Investigation 1: work orders (172 lines)
│   ├── ai_agent_execution_log.md      ← WorkBuddy Investigation 1: full audit trail (362 lines)
│   ├── ai_root_cause_analysis.md      ← WorkBuddy Investigation 2: root cause (178 lines)
│   ├── ai_contractor_briefing.md      ← WorkBuddy Investigation 2: contractor briefing (145 lines)
│   ├── ai_investigation_comparison.md ← WorkBuddy strategy comparison (51 lines)
│   └── ai_agent_work_order_report.md  ← additional work order report
├── requests/                           ← local runtime (gitignored)
└── outputs/                            ← local runtime (gitignored)
```

---

## 8. Data Files

### generator_data.csv

Simulated telemetry with columns: timestamp, operating_state, voltage_LL_V, frequency_Hz, current_A, active_power_kW, power_factor, engine_speed_rpm, coolant_temp_C, oil_pressure_bar, battery_V, fuel_level_L, running_hours.

### ats_events.csv

ATS event log with columns: timestamp, utility_supply_status, generator_start_command, generator_running_status, ats_commanded_source, ats_actual_position, transfer_confirmation, alarm_events.

### maintenance_history.csv

Maintenance log with columns: maintenance_date, running_hours, maintenance_type, work_description, next_inspection_date.

### Scenarios Simulated

| Scenario             | Description                                                                                                                                                           | Severity |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| A — Normal Operation | Utility fails → generator starts → ATS transfers → utility restores → generator stops. 77 confirmed transfers.                                                        | INFO     |
| B — Overheating      | At 70% load, coolant temperature rose from 44.8°C to 107.7°C over 47 minutes. Oil pressure declined from 4.54 to 3.24 bar. Over-temp shutdown triggered.              | HIGH     |
| C — ATS Failure      | Generator started correctly (402V, 50.07Hz) but ATS could not transfer to GENERATOR position. 11 consecutive failed transfers. FACILITY_NO_POWER alarm present for ~10 minutes (simulated alarm field; no independent load-bus voltage measurement in dataset). | CRITICAL |

---

## 9. Running GenBuddy

### Local Development Mode

```bash
cd GenBuddy_Hackathon
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000> — all features available (submit, analyze, reset, request system).
Open <https://dormathon-hackathon-cleo.onrender.com/> - read-only monitoring (generator telemetry, ATS events, historical playback, and published AI reports).

### Public Demo Mode (Read-Only)

**Linux / macOS / Git Bash (Windows):**
```bash
cd GenBuddy_Hackathon
pip install -r requirements.txt
PUBLIC_DEMO_MODE=1 python app.py
```

**Windows Command Prompt:**
```cmd
cd GenBuddy_Hackathon
pip install -r requirements.txt
set PUBLIC_DEMO_MODE=1 && python app.py
```

**Windows PowerShell:**
```powershell
cd GenBuddy_Hackathon
pip install -r requirements.txt
$env:PUBLIC_DEMO_MODE=1; python app.py
```

Or using the WSGI entry point (auto-sets `PUBLIC_DEMO_MODE=1`, all platforms):
```bash
waitress-serve --host=0.0.0.0 --port=5000 wsgi:application
```

All write endpoints return 403. Local request/output files are not exposed. The dashboard shows all read-only content (telemetry, playback, example reports).

### Running Engineering Scripts

```bash
# Validate all CSV data (13 checks)
python scripts/validate_data.py

# Run fault investigation and generate reports
python scripts/fault_investigation.py
```

---

## 10. Security

- **Path traversal prevention**: All file-serving endpoints validate request IDs against `^[a-zA-Z0-9_-]{8,64}$`, block `..`/`/`/`\` in filenames, enforce an extension whitelist (`.md`, `.csv`, `.txt`, `.json`), and verify resolved paths against the output root.
- **Report whitelist**: Only files in the `APPROVED_REPORTS` set are served via `/api/reports/<filename>`.
- **Public demo mode**: All write-producing and script-executing endpoints return 403. Local request/output files are not exposed.
- **Local binding**: In development mode, Flask binds to `127.0.0.1` only. In public mode, waitress binds to `0.0.0.0` but write endpoints are blocked.
- **No credentials**: The repository contains no API keys, tokens, passwords, or personal information. Security scan verified (see deployment checklist).

---

## 11. WorkBuddy Usage Evidence

For DORMATHON 2026 Track 2 judging, see `docs/workbuddy_usage_evidence.md` for:

1. How WorkBuddy was used to develop GenBuddy (7 development phases)
2. How WorkBuddy acted as runtime AI investigation agent (3 investigations)
3. Engineering tools executed by the agent (5 tool types)
4. How the agent adapted its workflow per question (7 dimensions)
5. Actual reports and recommendations generated (7 files)
6. Suggested WorkBuddy screenshots for presentation (10 moments)
7. Track 2 judging criteria alignment (5 criteria)
