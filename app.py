#!/usr/bin/env python3
"""
GenBuddy Dashboard - Flask Backend
DORMATHON 2026 Track 2

Serves the existing CSV data, reports, and executes validation +
fault investigation scripts on demand via the /api/analyze endpoint.

PUBLIC_DEMO_MODE:
  Set PUBLIC_DEMO_MODE=1 to enable read-only public deployment.
  All write endpoints (request creation, status updates, demo reset,
  script execution) return 403. Local request/output files are not
  exposed. Use waitress as the WSGI server.

DISCLAIMER: All data is SIMULATED. No real equipment connected.
"""

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from flask import Flask, render_template, jsonify, send_file, request, abort

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
REPORTS_DIR = os.path.join(BASE, "reports")
SCRIPTS_DIR = os.path.join(BASE, "scripts")
REQUESTS_DIR = os.path.join(BASE, "requests")
OUTPUTS_DIR = os.path.join(BASE, "outputs")

# ── Public Demo Mode ──────────────────────────────────────────────────
# When True, all write-producing and script-executing endpoints are
# disabled (return 403). Local request/output files are not exposed.
PUBLIC_DEMO_MODE = os.environ.get("PUBLIC_DEMO_MODE", "0") == "1"

# Ensure request/output directories exist at startup (local mode only)
if not PUBLIC_DEMO_MODE:
    os.makedirs(REQUESTS_DIR, exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

app = Flask(__name__, template_folder=os.path.join(BASE, "templates"))

# ── Overlap prevention for /api/analyze ───────────────────────────────
_analyze_lock = threading.Lock()


def _public_mode_blocked():
    """Return a 403 JSON response if public demo mode is active.

    Used at the start of every write-producing or script-executing
    endpoint to block access in public deployment.
    """
    return jsonify({
        "error": "This operation is disabled in public demo mode.",
        "public_demo_mode": True,
    }), 403


@app.route("/api/public_mode")
def api_public_mode():
    """Report whether the server is running in public demo mode.

    The frontend uses this to hide write UI elements (submit button,
    demo reset, analyze button) when public mode is active.
    """
    return jsonify({
        "public_demo_mode": PUBLIC_DEMO_MODE,
        "features": {
            "view_generator_data": True,
            "view_ats_events": True,
            "view_maintenance": True,
            "view_scenarios": True,
            "view_findings": True,
            "view_reports": True,
            "view_ai_summary": True,
            "view_playback": True,
            "submit_investigation": not PUBLIC_DEMO_MODE,
            "update_status": not PUBLIC_DEMO_MODE,
            "demo_reset": not PUBLIC_DEMO_MODE,
            "run_analysis": not PUBLIC_DEMO_MODE,
            "view_requests": not PUBLIC_DEMO_MODE,
        },
    })

# ── Whitelist of approved report/data files for download ─────────────
APPROVED_REPORTS = {
    "generator_health_report.md",
    "maintenance_action_plan.csv",
    "agent_execution_log.md",
    "ai_readiness_assessment.md",
    "ai_maintenance_work_orders.md",
    "ai_agent_execution_log.md",
    "ai_root_cause_analysis.md",
    "ai_contractor_briefing.md",
    "ai_investigation_comparison.md",
}
APPROVED_DATA = {
    "validation_report.md",
}


def load_csv(path):
    """Load a CSV file into a list of dicts."""
    with open(path, "r", newline="") as f:
        return list(csv.DictReader(f))


def classify_window(window_gen, window_ats):
    """Classify a utility-failure window by telemetry and ATS patterns.

    Pattern-based detection (not positional order):
      - ATS_TRANSFER_FAILURE: transfer_confirmation = FAILED
      - OVERHEATING: RUNNING_DEGRADED or OVER_TEMP alarm
      - NORMAL_OPERATION: CONFIRMED transfer to GENERATOR
    """
    failed_transfers = [r for r in window_ats
                        if r["transfer_confirmation"] == "FAILED"]
    degraded = [r for r in window_gen
                if r["operating_state"] == "RUNNING_DEGRADED"]
    over_temp = [r for r in window_ats
                 if "OVER_TEMP" in r.get("alarm_events", "")]
    confirmed_gen = [r for r in window_ats
                      if r["transfer_confirmation"] == "CONFIRMED"
                      and r["ats_commanded_source"] == "GENERATOR"]

    if failed_transfers:
        return "ATS_TRANSFER_FAILURE"
    if degraded or over_temp:
        return "OVERHEATING"
    if confirmed_gen:
        return "NORMAL_OPERATION"
    return "UNKNOWN"


PATTERN_LABELS = {
    "NORMAL_OPERATION": "Normal Operation",
    "OVERHEATING": "Overheating",
    "ATS_TRANSFER_FAILURE": "ATS Failure",
    "UNKNOWN": "Unknown",
}


def find_focus_ts(pattern, window_gen, window_ats, fallback_ts):
    """Find the most informative timestamp within a scenario window.

    Returns the timestamp of the defining event for each pattern so the
    playback can jump to an interesting record when a scenario is selected.
    """
    if pattern == "ATS_TRANSFER_FAILURE":
        for r in window_ats:
            if r["transfer_confirmation"] == "FAILED":
                return r["timestamp"]
    elif pattern == "OVERHEATING":
        for r in window_gen:
            if r["operating_state"] == "RUNNING_DEGRADED":
                return r["timestamp"]
        for r in window_ats:
            if "OVER_TEMP" in r.get("alarm_events", ""):
                return r["timestamp"]
    elif pattern == "NORMAL_OPERATION":
        for r in window_ats:
            if (r["transfer_confirmation"] == "CONFIRMED"
                    and r["ats_commanded_source"] == "GENERATOR"):
                return r["timestamp"]
    return fallback_ts


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generator_data")
def api_generator_data():
    rows = load_csv(os.path.join(DATA_DIR, "generator_data.csv"))
    return jsonify(rows)


@app.route("/api/ats_events")
def api_ats_events():
    rows = load_csv(os.path.join(DATA_DIR, "ats_events.csv"))
    return jsonify(rows)


@app.route("/api/maintenance")
def api_maintenance():
    rows = load_csv(os.path.join(DATA_DIR, "maintenance_history.csv"))
    return jsonify(rows)


@app.route("/api/scenarios")
def api_scenarios():
    """Return scenario boundary timestamps for chart filtering.

    Scenarios are classified by telemetry/ATS patterns (not positional order).
    """
    ats = load_csv(os.path.join(DATA_DIR, "ats_events.csv"))
    gen = load_csv(os.path.join(DATA_DIR, "generator_data.csv"))
    failures = [r["timestamp"] for r in ats if "UTILITY_FAIL_ALARM" in r["alarm_events"]]
    scenarios = []
    for i, f_ts in enumerate(failures):
        end_ts = failures[i + 1] if i + 1 < len(failures) else None
        # Extract window rows for pattern classification
        window_gen = [r for r in gen if r["timestamp"] >= f_ts
                      and (end_ts is None or r["timestamp"] < end_ts)]
        window_ats = [r for r in ats if r["timestamp"] >= f_ts
                      and (end_ts is None or r["timestamp"] < end_ts)]
        pattern = classify_window(window_gen, window_ats)
        label = PATTERN_LABELS.get(pattern, f"Scenario {i + 1}")
        focus_ts = find_focus_ts(pattern, window_gen, window_ats, f_ts)
        scenarios.append({"label": label, "start": f_ts, "end": end_ts,
                           "pattern": pattern, "focus_ts": focus_ts})
    return jsonify(scenarios)


@app.route("/api/findings")
def api_findings():
    """Parse findings from the maintenance action plan CSV."""
    plan_path = os.path.join(REPORTS_DIR, "maintenance_action_plan.csv")
    if os.path.exists(plan_path):
        rows = load_csv(plan_path)
        return jsonify(rows)
    return jsonify([])


@app.route("/api/reports/<path:filename>")
def api_report(filename):
    """Serve an approved report or data file.

    Only whitelisted filenames are served. Path traversal is blocked
    by rejecting any filename containing directory separators.
    """
    # Block path traversal attempts
    if "/" in filename or "\\" in filename or ".." in filename:
        return jsonify({"error": "Invalid filename"}), 400

    # Check whitelist
    if filename in APPROVED_REPORTS:
        path = os.path.join(REPORTS_DIR, filename)
        if os.path.isfile(path):
            return send_file(path)
    if filename in APPROVED_DATA:
        path = os.path.join(DATA_DIR, filename)
        if os.path.isfile(path):
            return send_file(path)

    return jsonify({"error": "File not found or not approved for download"}), 404


@app.route("/api/report_list")
def api_report_list():
    """List all available approved report files."""
    files = []
    for fn in sorted(APPROVED_REPORTS):
        fp = os.path.join(REPORTS_DIR, fn)
        if os.path.isfile(fp):
            files.append({"name": fn, "folder": "reports"})
    for fn in sorted(APPROVED_DATA):
        fp = os.path.join(DATA_DIR, fn)
        if os.path.isfile(fp):
            files.append({"name": fn, "folder": "data"})
    return jsonify(files)


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """Execute validation + fault investigation scripts and return results.

    Protected against overlapping requests by a threading lock.
    Handles subprocess timeouts and non-zero exit codes.

    Disabled in public demo mode (returns 403).
    """
    if PUBLIC_DEMO_MODE:
        return _public_mode_blocked()

    # Prevent overlapping analysis requests
    if not _analyze_lock.acquire(blocking=False):
        return jsonify({
            "success": False,
            "error": "An analysis is already running. Please wait for it to complete.",
        }), 429

    try:
        return _run_analysis()
    finally:
        _analyze_lock.release()


def _run_analysis():
    """Internal: run validation + fault investigation subprocesses."""
    py = sys.executable
    results = {"steps": [], "success": True}

    # Step 1: Run validation
    val_script = os.path.join(SCRIPTS_DIR, "validate_data.py")
    try:
        r = subprocess.run(
            [py, val_script],
            capture_output=True, text=True, timeout=60,
        )
        output = r.stdout
        stderr = r.stderr
        issues_line = [l for l in output.splitlines() if "Issues:" in l]

        step = {
            "tool": "validate_data.py",
            "exit_code": r.returncode,
            "summary": issues_line[0].strip() if issues_line else "No summary line found",
            "checks_passed": "Issues: 0" in output,
        }
        if r.returncode != 0:
            step["warning"] = f"Non-zero exit code ({r.returncode})"
            if stderr.strip():
                step["stderr"] = stderr.strip()[:500]
        results["steps"].append(step)

    except subprocess.TimeoutExpired:
        results["steps"].append({
            "tool": "validate_data.py",
            "error": "Script timed out after 60 seconds",
        })
        results["success"] = False
    except FileNotFoundError:
        results["steps"].append({
            "tool": "validate_data.py",
            "error": "Script file not found",
        })
        results["success"] = False
    except Exception as e:
        results["steps"].append({
            "tool": "validate_data.py",
            "error": f"Unexpected error: {type(e).__name__}: {e}",
        })
        results["success"] = False

    # Step 2: Run fault investigation
    fi_script = os.path.join(SCRIPTS_DIR, "fault_investigation.py")
    try:
        r = subprocess.run(
            [py, fi_script],
            capture_output=True, text=True, timeout=90,
        )
        output = r.stdout
        stderr = r.stderr
        scenarios = [l for l in output.splitlines() if "Scenarios identified:" in l]
        criticals = [l for l in output.splitlines() if "CRITICAL:" in l]

        step = {
            "tool": "fault_investigation.py",
            "exit_code": r.returncode,
            "summary": scenarios[0].strip() if scenarios else "No summary line found",
            "details": criticals[0].strip() if criticals else "",
        }
        if r.returncode != 0:
            step["warning"] = f"Non-zero exit code ({r.returncode})"
            if stderr.strip():
                step["stderr"] = stderr.strip()[:500]
        results["steps"].append(step)

    except subprocess.TimeoutExpired:
        results["steps"].append({
            "tool": "fault_investigation.py",
            "error": "Script timed out after 90 seconds",
        })
        results["success"] = False
    except FileNotFoundError:
        results["steps"].append({
            "tool": "fault_investigation.py",
            "error": "Script file not found",
        })
        results["success"] = False
    except Exception as e:
        results["steps"].append({
            "tool": "fault_investigation.py",
            "error": f"Unexpected error: {type(e).__name__}: {e}",
        })
        results["success"] = False

    # Reload findings after analysis
    plan_path = os.path.join(REPORTS_DIR, "maintenance_action_plan.csv")
    if os.path.exists(plan_path):
        results["findings"] = load_csv(plan_path)

    return jsonify(results)


# ── AI Assistant Q&A endpoint ────────────────────────────────────────

# Keyword map: each category maps to a set of keywords the user might type.
_QA_KEYWORDS = {
    "temperature": {"temperature", "coolant", "hot", "overheat", "thermal",
                    "cooling", "radiator", "temp"},
    "ats": {"ats", "transfer", "switch", "contactor", "utility", "source",
            "position", "facility", "power outage", "outage"},
    "maintenance": {"maintenance", "service", "repair", "inspection",
                     "serviced", "last service", "next service", "schedule"},
    "readiness": {"ready", "readiness", "prepared", "next outage", "backup",
                  "rely", "depend", "trust", "can it", "will it"},
    "problems": {"problem", "issue", "fault", "error", "wrong", "fail",
                 "broken", "concern", "abnormal", "alarm"},
    "recommendations": {"recommend", "action", "fix", "should", "advice",
                        "suggest", "what do", "what to", "plan", "do about",
                        "address", "resolve"},
}


def _match_categories(question):
    """Match a lowercased question against keyword categories.

    Returns a list of category strings. If no specific category matches,
    returns ["general"] for a default overall assessment.
    """
    matched = []
    for cat, keywords in _QA_KEYWORDS.items():
        for kw in keywords:
            if kw in question:
                matched.append(cat)
                break
    if not matched:
        matched = ["general"]
    return matched


def _analyze_temperature(gen, ats):
    """Analyze coolant temperature data."""
    temps = [(r["timestamp"], float(r["coolant_temp_C"]), r["operating_state"])
             for r in gen if r["operating_state"] != "STANDBY"]

    if not temps:
        return {"peak": None, "peak_ts": None, "rise_rate": None,
                "shutdown": False, "summary": "No temperature data available."}

    peak = max(temps, key=lambda t: t[1])
    # Check for over-temp shutdown
    shutdown = any(float(r["coolant_temp_C"]) > 100 for r in gen)

    # Calculate rise rate during normal-temp climbing phase
    climbing = [t for t in temps if t[1] < 90 and t[2] == "RUNNING"]
    rise_rate = None
    if len(climbing) >= 2:
        dt_minutes = _ts_diff_minutes(climbing[0][0], climbing[-1][0])
        dtemp = climbing[-1][1] - climbing[0][1]
        if dt_minutes and dt_minutes > 0:
            rise_rate = round(dtemp / dt_minutes, 2)

    summary = (f"Peak coolant temperature was {peak[1]:.1f}C at "
               f"{peak[0][11:16]}. ")
    if shutdown:
        summary += ("Temperature exceeded 100C, triggering over-temperature "
                     "shutdown. ")
    if rise_rate:
        summary += (f"During the normal-temperature climbing phase, the rate "
                    f"was {rise_rate}C/min. ")
    summary += ("The gradual, linear temperature rise pattern is consistent "
                "with progressive cooling system inefficiency (blocked "
                "radiator, coolant degradation, or thermostat issue) rather "
                "than sudden failure.")

    return {"peak": round(peak[1], 1), "peak_ts": peak[0],
            "rise_rate": rise_rate, "shutdown": shutdown,
            "summary": summary}


def _analyze_ats(ats):
    """Analyze ATS transfer events."""
    failed = [r for r in ats if r["transfer_confirmation"] == "FAILED"]
    confirmed = [r for r in ats if r["transfer_confirmation"] == "CONFIRMED"]
    facility_alarm = [r for r in ats
                      if "FACILITY_NO_POWER" in r.get("alarm_events", "")]

    summary_parts = []
    if failed:
        first_fail = failed[0]["timestamp"]
        last_fail = failed[-1]["timestamp"]
        summary_parts.append(
            f"{len(failed)} consecutive FAILED ATS transfers from "
            f"{first_fail[11:16]} to {last_fail[11:16]}. ")
    if facility_alarm:
        first_alarm = facility_alarm[0]["timestamp"]
        last_alarm = facility_alarm[-1]["timestamp"]
        duration = _ts_diff_minutes(first_alarm, last_alarm)
        summary_parts.append(
            f"FACILITY_NO_POWER alarm present for {len(facility_alarm)} records "
            f"({first_alarm[11:16]} to {last_alarm[11:16]}, "
            f"{duration:.0f}-minute span). This simulated alarm field indicates "
            f"(but does not independently measure) a facility power outage. ")
    if confirmed:
        summary_parts.append(
            f"{len(confirmed)} successful CONFIRMED transfers occurred in "
            f"normal operation scenarios. ")

    # Check commanded vs actual mismatch
    mismatch = [r for r in ats
                if r["ats_commanded_source"] == "GENERATOR"
                and r["ats_actual_position"] == "UTILITY"]
    if mismatch:
        summary_parts.append(
            f"In {len(mismatch)} records, the ATS was commanded to GENERATOR "
            f"but actual position remained UTILITY, indicating the contactor "
            f"did not physically transfer. ")

    return {
        "failed_transfers": len(failed),
        "confirmed_transfers": len(confirmed),
        "facility_alarm_records": len(facility_alarm),
        "facility_alarm_duration_min": (_ts_diff_minutes(
            facility_alarm[0]["timestamp"],
            facility_alarm[-1]["timestamp"]) if facility_alarm else None),
        "commanded_actual_mismatch": len(mismatch),
        "summary": "".join(summary_parts) or "ATS operating normally.",
    }


def _analyze_maintenance(maint):
    """Analyze maintenance history."""
    if not maint:
        return {"summary": "No maintenance history available."}

    last = maint[-1]
    next_date = last.get("next_inspection_date", "N/A")

    return {
        "last_service_date": last["maintenance_date"],
        "last_service_type": last["maintenance_type"],
        "last_service_work": last["work_description"],
        "last_service_hours": float(last["running_hours"]),
        "next_inspection_date": next_date,
        "total_services": len(maint),
        "summary": (f"Last service: {last['maintenance_date']} "
                    f"({last['maintenance_type']}) at "
                    f"{float(last['running_hours']):.0f} running hours. "
                    f"Work performed: {last['work_description']}. "
                    f"Next inspection due: {next_date}."),
    }


def _analyze_readiness(gen, ats, maint):
    """Assess overall generator readiness."""
    problems = []
    ok_items = []

    # Check ATS failures
    failed = [r for r in ats if r["transfer_confirmation"] == "FAILED"]
    if failed:
        problems.append({
            "severity": "CRITICAL",
            "title": "ATS Transfer Failure",
            "detail": (f"{len(failed)} consecutive FAILED transfers. The ATS "
                       "contactor did not physically move when commanded. The "
                       "generator started correctly but could not supply the "
                       "building load."),
        })
    else:
        ok_items.append("ATS transfers function correctly in all scenarios.")

    # Check overheating
    overheating = [r for r in gen if r["operating_state"] == "RUNNING_DEGRADED"]
    shutdown = [r for r in gen if r["operating_state"] == "SHUTDOWN"]
    if overheating or shutdown:
        peak_temp = max(float(r["coolant_temp_C"]) for r in gen
                        if r["operating_state"] != "STANDBY")
        problems.append({
            "severity": "HIGH",
            "title": "Over-Temperature Shutdown",
            "detail": (f"Coolant temperature reached {peak_temp:.1f}C at 70% "
                       "load, triggering over-temperature shutdown. The cooling "
                       "system cannot handle sustained operation at moderate "
                       "load. Gradual temperature rise indicates progressive "
                       "cooling system inefficiency."),
        })
    else:
        ok_items.append("Coolant temperature stays within normal range.")

    # Check engine/alternator health
    running_records = [r for r in gen if r["operating_state"]
                       in ("RUNNING", "RUNNING_DEGRADED")]
    if running_records:
        voltages = [float(r["voltage_LL_V"]) for r in running_records
                    if float(r["voltage_LL_V"]) > 0]
        freqs = [float(r["frequency_Hz"]) for r in running_records
                 if float(r["frequency_Hz"]) > 0]
        if voltages and all(395 <= v <= 405 for v in voltages):
            ok_items.append(f"Voltage nominal ({min(voltages):.0f}-"
                            f"{max(voltages):.0f}V) across all runs.")
        if freqs and all(49.5 <= f <= 50.5 for f in freqs):
            ok_items.append(f"Frequency nominal ({min(freqs):.1f}-"
                            f"{max(freqs):.1f}Hz) across all runs.")

    # Check fuel
    fuel = [float(r["fuel_level_L"]) for r in gen]
    if fuel and min(fuel) > 100:
        ok_items.append(f"Fuel level adequate (min {min(fuel):.0f}L of 522L).")
    else:
        problems.append({
            "severity": "MEDIUM",
            "title": "Low Fuel Level",
            "detail": f"Fuel dropped to {min(fuel):.0f}L during operation.",
        })

    # Check battery
    batt = [float(r["battery_V"]) for r in gen]
    if batt and min(batt) >= 22:
        ok_items.append(f"Battery voltage healthy (min {min(batt):.1f}V).")
    else:
        problems.append({
            "severity": "MEDIUM",
            "title": "Low Battery Voltage",
            "detail": f"Battery dropped to {min(batt):.1f}V (nominal 24V).",
        })

    # Verdict
    critical = [p for p in problems if p["severity"] == "CRITICAL"]
    high = [p for p in problems if p["severity"] == "HIGH"]
    if critical or high:
        verdict = "NOT READY FOR SERVICE"
    else:
        verdict = "READY FOR SERVICE"

    summary = (f"Verdict: {verdict}. "
               f"{len(problems)} problem(s) identified, "
               f"{len(ok_items)} system(s) healthy. ")
    if critical or high:
        summary += ("The generator cannot be relied upon for backup power "
                    "until the identified issues are resolved. ")
    summary += "All data is SIMULATED."

    return {
        "verdict": verdict,
        "problems": problems,
        "healthy_systems": ok_items,
        "summary": summary,
    }


def _ts_diff_minutes(ts1, ts2):
    """Calculate minutes between two ISO timestamp strings."""
    try:
        from datetime import datetime
        t1 = datetime.fromisoformat(ts1)
        t2 = datetime.fromisoformat(ts2)
        return abs((t2 - t1).total_seconds()) / 60.0
    except Exception:
        return None


def _build_answer(question, gen, ats, maint):
    """Build a structured Q&A response based on the user's question."""
    categories = _match_categories(question)
    response = {
        "categories": categories,
        "answer": "",
        "problems": [],
        "recommendations": [],
        "data_points": {},
    }

    # Always compute readiness as a baseline
    readiness = _analyze_readiness(gen, ats, maint)
    response["data_points"]["verdict"] = readiness["verdict"]
    response["problems"] = readiness["problems"]

    # Build the narrative answer based on categories
    parts = []

    if "general" in categories or "readiness" in categories:
        parts.append(readiness["summary"])
        parts.append("Healthy systems: " + "; ".join(readiness["healthy_systems"]))

    if "temperature" in categories:
        temp = _analyze_temperature(gen, ats)
        response["data_points"].update({
            "peak_temp_c": temp["peak"],
            "peak_temp_ts": temp["peak_ts"],
            "temp_rise_rate_c_per_min": temp["rise_rate"],
            "over_temp_shutdown": temp["shutdown"],
        })
        parts.append("\n\n**Temperature Analysis:**\n" + temp["summary"])

    if "ats" in categories:
        ats_analysis = _analyze_ats(ats)
        response["data_points"].update({
            "ats_failed_transfers": ats_analysis["failed_transfers"],
            "ats_confirmed_transfers": ats_analysis["confirmed_transfers"],
            "facility_alarm_records": ats_analysis["facility_alarm_records"],
            "facility_alarm_duration_min": ats_analysis["facility_alarm_duration_min"],
        })
        parts.append("\n\n**ATS Analysis:**\n" + ats_analysis["summary"])

    if "maintenance" in categories:
        maint_analysis = _analyze_maintenance(maint)
        response["data_points"].update({
            "last_service_date": maint_analysis["last_service_date"],
            "last_service_type": maint_analysis["last_service_type"],
            "next_inspection_date": maint_analysis["next_inspection_date"],
        })
        parts.append("\n\n**Maintenance History:**\n" + maint_analysis["summary"])

    if "problems" in categories:
        if readiness["problems"]:
            prob_text = "\n".join(
                f"  - [{p['severity']}] {p['title']}: {p['detail']}"
                for p in readiness["problems"])
            parts.append("\n\n**Problems Found:**\n" + prob_text)
        else:
            parts.append("\n\n**Problems Found:** No critical issues detected.")

    if "recommendations" in categories or "general" in categories:
        recs = []
        for p in readiness["problems"]:
            if p["severity"] == "CRITICAL":
                recs.append(f"URGENT: Investigate and repair the ATS "
                           f"transfer mechanism. Test the contactor, "
                           f"actuator, and control wiring. Do not return "
                           f"to service until a successful transfer test "
                           f"is completed under load.")
            elif p["severity"] == "HIGH":
                recs.append(f"Inspect the cooling system: check radiator "
                           f"for blockage, verify coolant condition and "
                           f"level, test thermostat operation. Perform "
                           f"a load test at 70% rated capacity to verify "
                           f"temperature stays below 95C.")
            elif p["severity"] == "MEDIUM":
                recs.append(f"Address {p['title'].lower()}: {p['detail']}")
        if not recs:
            recs.append("Continue scheduled maintenance. No urgent "
                       "actions needed based on current data.")
        response["recommendations"] = recs
        parts.append("\n\n**Recommendations:**\n" + "\n".join(
            f"  {i+1}. {r}" for i, r in enumerate(recs)))

    # If only "general" with no other category, add a brief overview
    if categories == ["general"] and not parts:
        parts.append(readiness["summary"])

    response["answer"] = "".join(parts) if parts else readiness["summary"]

    return response


@app.route("/api/ask", methods=["POST"])
def api_ask():
    """Answer a natural language question about generator condition.

    Accepts {"question": "..."} and returns a structured response with
    answer text, problems, recommendations, and data points.

    Uses keyword matching to route to the relevant analysis. This is a
    rule-based assistant -- it can be upgraded to a cloud LLM later.

    Disabled in public demo mode (returns 403).
    """
    if PUBLIC_DEMO_MODE:
        return _public_mode_blocked()

    data = request.get_json(silent=True)
    if not data or "question" not in data:
        return jsonify({"error": "Missing 'question' field"}), 400

    question = data["question"].strip()
    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    # Load data
    try:
        gen = load_csv(os.path.join(DATA_DIR, "generator_data.csv"))
        ats = load_csv(os.path.join(DATA_DIR, "ats_events.csv"))
        maint = load_csv(os.path.join(DATA_DIR, "maintenance_history.csv"))
    except Exception as e:
        return jsonify({"error": f"Failed to load data: {e}"}), 500

    result = _build_answer(question.lower(), gen, ats, maint)
    result["source"] = "rule-based"
    result["disclaimer"] = ("SIMULATED HISTORICAL DATA -- Analysis is based on "
                            "pre-recorded telemetry, not live monitoring. "
                            "DSE6120 alarm thresholds remain UNVERIFIED.")

    return jsonify(result)


# ── AI Investigation Summary endpoint ────────────────────────────────

def _read_report_text(filename):
    """Read a report markdown file and return its text content."""
    path = os.path.join(REPORTS_DIR, filename)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def _extract_ai_summary():
    """Extract structured summaries from actual AI-generated report files.

    Reads the real .md files written by WorkBuddy AI agent investigations
    and parses them into structured data for the dashboard. No hardcoded
    conclusions — all values come from the report files on disk.
    """
    summary = {
        "investigations": [],
        "comparison_file": None,
        "available": False,
        "disclaimer": ("SIMULATED HISTORICAL DATA — Reports generated by "
                        "WorkBuddy AI agent runtime LLM reasoning, not by "
                        "fixed Python automation."),
    }

    # ── Investigation 1: Readiness Assessment ──
    readiness_text = _read_report_text("ai_readiness_assessment.md")
    inv1 = {"id": 1, "title": "Readiness Assessment",
            "report_file": "ai_readiness_assessment.md", "available": False}

    if readiness_text:
        inv1["available"] = True

        # Business owner request
        m = re.search(r'\*\*Business owner request:\*\*\s*"?([^"\n]+)"?',
                      readiness_text)
        if m:
            inv1["business_request"] = m.group(1).strip()

        # Generated timestamp
        m = re.search(r'\*\*Generated:\*\*\s*(.+)', readiness_text)
        if m:
            inv1["generated"] = m.group(1).strip()

        # Verdict
        m = re.search(r'## Verdict:\s*(.+)', readiness_text)
        if m:
            inv1["verdict"] = m.group(1).strip()

        # Problems table rows: | # | Issue | Priority | Impact |
        problems = []
        for m in re.finditer(
            r'\|\s*\d+\s*\|\s*(.+?)\s*\|\s*(CRITICAL|HIGH|MEDIUM|'
            r'INFORMATIONAL|INFO)\s*\|\s*(.+?)\s*\|',
            readiness_text,
        ):
            problems.append({
                "issue": m.group(1).strip(),
                "priority": m.group(2).strip(),
                "impact": m.group(3).strip(),
            })
        inv1["problems"] = problems

        summary["investigations"].append(inv1)

    # ── Work Orders (from ai_maintenance_work_orders.md) ──
    wo_text = _read_report_text("ai_maintenance_work_orders.md")
    if wo_text:
        work_orders = []
        for m in re.finditer(
            r'\|\s*(WO-\d+)\s*\|\s*(.+?)\s*\|\s*(CRITICAL|HIGH|MEDIUM|'
            r'INFORMATIONAL|INFO)\s*\|\s*(.+?)\s*\|\s*(\S+)\s*\|',
            wo_text,
        ):
            work_orders.append({
                "id": m.group(1).strip(),
                "title": m.group(2).strip(),
                "priority": m.group(3).strip(),
                "system": m.group(4).strip(),
                "status": m.group(5).strip(),
            })
        if inv1.get("available"):
            inv1["work_orders"] = work_orders
            inv1["work_orders_file"] = "ai_maintenance_work_orders.md"

    # ── Investigation 2: Root Cause Analysis ──
    rca_text = _read_report_text("ai_root_cause_analysis.md")
    inv2 = {"id": 2, "title": "Root Cause Analysis",
            "report_file": "ai_root_cause_analysis.md", "available": False}

    if rca_text:
        inv2["available"] = True

        # Business owner request
        m = re.search(r'\*\*Business owner request:\*\*\s*"?([^"\n]+)"?',
                      rca_text)
        if m:
            inv2["business_request"] = m.group(1).strip()

        # Generated timestamp
        m = re.search(r'\*\*Generated:\*\*\s*(.+)', rca_text)
        if m:
            inv2["generated"] = m.group(1).strip()

        # Executive summary (first paragraph after heading)
        m = re.search(
            r'## Executive Summary\s*\n(.+?)(?=\n---|\n## )',
            rca_text, re.DOTALL,
        )
        if m:
            inv2["summary"] = re.sub(r'\s+', ' ',
                                     m.group(1).strip())[:400]

        # Conclusion (first paragraph after heading)
        m = re.search(
            r'## Conclusion\s*\n(.+?)(?=\n---|\n## |\Z)',
            rca_text, re.DOTALL,
        )
        if m:
            inv2["conclusion"] = re.sub(r'\s+', ' ',
                                        m.group(1).strip())[:500]

        summary["investigations"].append(inv2)

    # ── Contractor briefing summary ──
    cb_text = _read_report_text("ai_contractor_briefing.md")
    if cb_text:
        m = re.search(
            r'## What Happened \(Plain Language\)\s*\n(.+?)(?=\n---|\n## )',
            cb_text, re.DOTALL,
        )
        if m and inv2.get("available"):
            inv2["contractor_summary"] = re.sub(
                r'\s+', ' ', m.group(1).strip()
            )[:300]
            inv2["contractor_briefing_file"] = "ai_contractor_briefing.md"

    # ── Comparison file ──
    comp_text = _read_report_text("ai_investigation_comparison.md")
    if comp_text:
        summary["comparison_file"] = "ai_investigation_comparison.md"

    # Overall availability
    summary["available"] = any(inv.get("available")
                               for inv in summary["investigations"])

    return summary


@app.route("/api/ai_summary")
def api_ai_summary():
    """Return structured summaries of actual AI-generated investigation reports.

    Reads the real .md files written by WorkBuddy AI agent investigations.
    Does NOT hardcode conclusions — all data is parsed from files on disk
    at request time, so new investigations appear automatically.
    """
    return jsonify(_extract_ai_summary())


# ── File-based Investigation Request System ─────────────────────────
#
# Workflow:
#   1. Dashboard user submits a question → JSON file written to requests/
#   2. Status = "awaiting_workbuddy" (Flask does NOT invoke WorkBuddy)
#   3. WorkBuddy agent reads the pending request, updates status to
#      "investigating" → "generating_reports" → "completed"
#   4. WorkBuddy writes report files to outputs/<request_id>/
#   5. Dashboard polls /api/request/<id> and displays results when ready
#
# Security:
#   - request_id validated against [a-zA-Z0-9_-]{8,64}
#   - filename must not contain .., /, or \
#   - only .md, .csv, .txt extensions allowed for output files
#   - Flask bound to 127.0.0.1 (localhost only)

VALID_STATUSES = [
    "awaiting_workbuddy",
    "investigating",
    "generating_reports",
    "completed",
    "failed",
]

# Allowed output file extensions (whitelist)
ALLOWED_OUTPUT_EXTS = {".md", ".csv", ".txt", ".json"}

# Regex for safe request IDs
_REQUEST_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{8,64}$")


def _gen_request_id():
    """Generate a unique, human-readable request ID."""
    ts = time.strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return f"req_{ts}_{suffix}"


def _request_path(rid):
    """Return the JSON file path for a request ID."""
    return os.path.join(REQUESTS_DIR, f"{rid}.json")


def _output_dir(rid):
    """Return the output directory path for a request ID."""
    return os.path.join(OUTPUTS_DIR, rid)


def _read_request(rid):
    """Read a request JSON file and return its contents as a dict, or None."""
    path = _request_path(rid)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_request(rid, data):
    """Write a request dict to its JSON file."""
    path = _request_path(rid)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _list_output_files(rid):
    """List output files for a completed request."""
    odir = _output_dir(rid)
    if not os.path.isdir(odir):
        return []
    files = []
    for fn in sorted(os.listdir(odir)):
        ext = os.path.splitext(fn)[1].lower()
        if ext in ALLOWED_OUTPUT_EXTS:
            files.append(fn)
    return files


def _validate_filename(filename):
    """Validate a filename for safe serving. Returns True if safe."""
    if not filename or len(filename) > 255:
        return False
    if ".." in filename or "/" in filename or "\\" in filename:
        return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_OUTPUT_EXTS


@app.route("/api/request/new", methods=["POST"])
def api_request_new():
    """Create a new investigation request.

    Accepts {"question": "..."} and creates a uniquely-identified JSON
    file in requests/. The status is set to "awaiting_workbuddy" — Flask
    does NOT invoke WorkBuddy. The user must copy the question and paste
    it into WorkBuddy, where the agent will pick up the request.

    Disabled in public demo mode (returns 403).
    """
    if PUBLIC_DEMO_MODE:
        return _public_mode_blocked()

    data = request.get_json(silent=True)
    if not data or "question" not in data:
        return jsonify({"error": "Missing 'question' field"}), 400

    question = str(data["question"]).strip()
    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400
    if len(question) > 2000:
        return jsonify({"error": "Question too long (max 2000 chars)"}), 400

    rid = _gen_request_id()
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    req_data = {
        "request_id": rid,
        "question": question,
        "status": "awaiting_workbuddy",
        "submitted_at": now,
        "status_history": [
            {"status": "awaiting_workbuddy", "timestamp": now}
        ],
        "outputs": [],
        "error": None,
    }
    _write_request(rid, req_data)

    return jsonify({
        "request_id": rid,
        "status": "awaiting_workbuddy",
        "message": ("Request saved. Copy the question into your WorkBuddy "
                    "workspace to start the investigation."),
    })


@app.route("/api/requests")
def api_requests_list():
    """List all investigation requests with their current status.

    Disabled in public demo mode — local request files are not exposed.
    """
    if PUBLIC_DEMO_MODE:
        return jsonify({"error": "Request listing disabled in public demo mode.",
                        "public_demo_mode": True}), 403

    results = []
    if os.path.isdir(REQUESTS_DIR):
        for fn in sorted(os.listdir(REQUESTS_DIR), reverse=True):
            if not fn.endswith(".json"):
                continue
            rid = fn[:-5]  # strip .json
            req = _read_request(rid)
            if req:
                results.append({
                    "request_id": rid,
                    "question": req.get("question", ""),
                    "status": req.get("status", "unknown"),
                    "submitted_at": req.get("submitted_at", ""),
                    "output_count": len(req.get("outputs", [])),
                    "error": req.get("error"),
                })
    return jsonify(results)


@app.route("/api/request/<request_id>")
def api_request_detail(request_id):
    """Get full details of a specific request including status and outputs.

    Disabled in public demo mode — local request files are not exposed.
    """
    if PUBLIC_DEMO_MODE:
        return jsonify({"error": "Request details disabled in public demo mode.",
                        "public_demo_mode": True}), 403

    if not _REQUEST_ID_RE.match(request_id):
        return jsonify({"error": "Invalid request ID format"}), 400

    req = _read_request(request_id)
    if not req:
        return jsonify({"error": "Request not found"}), 404

    # Attach current output file list
    req["outputs"] = _list_output_files(request_id)
    return jsonify(req)


@app.route("/api/request/<request_id>/status", methods=["POST"])
def api_request_update_status(request_id):
    """Update the status of a request.

    This endpoint is called by the WorkBuddy agent (via curl from the
    same machine) to signal investigation progress. It is NOT called
    by the dashboard frontend.

    Accepts {"status": "...", "error": "...optional..."} and updates
    the request JSON file.

    Disabled in public demo mode (returns 403).
    """
    if PUBLIC_DEMO_MODE:
        return _public_mode_blocked()

    if not _REQUEST_ID_RE.match(request_id):
        return jsonify({"error": "Invalid request ID format"}), 400

    req = _read_request(request_id)
    if not req:
        return jsonify({"error": "Request not found"}), 404

    data = request.get_json(silent=True)
    if not data or "status" not in data:
        return jsonify({"error": "Missing 'status' field"}), 400

    new_status = str(data["status"]).strip().lower()
    if new_status not in VALID_STATUSES:
        return jsonify({"error": f"Invalid status. Must be one of: {VALID_STATUSES}"}), 400

    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    req["status"] = new_status
    req["status_history"].append({"status": new_status, "timestamp": now})

    if new_status == "completed":
        req["outputs"] = _list_output_files(request_id)
        req["completed_at"] = now
    elif new_status == "failed":
        req["error"] = str(data.get("error", "Investigation failed"))
        req["completed_at"] = now

    _write_request(request_id, req)

    return jsonify({
        "request_id": request_id,
        "status": new_status,
        "outputs": req.get("outputs", []),
    })


@app.route("/api/request/<request_id>/output/<path:filename>")
def api_request_output(request_id, filename):
    """Serve an output file from a completed investigation.

    Security:
    - request_id validated against safe pattern
    - filename must not contain path traversal characters
    - only whitelisted file extensions (.md, .csv, .txt, .json)
    - file must exist in outputs/<request_id>/

    Disabled in public demo mode — local output files are not exposed.
    """
    if PUBLIC_DEMO_MODE:
        return jsonify({"error": "Output file access disabled in public demo mode.",
                        "public_demo_mode": True}), 403

    if not _REQUEST_ID_RE.match(request_id):
        return jsonify({"error": "Invalid request ID format"}), 400

    # Block path traversal — also block path: prefix from <path:filename>
    if ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "Invalid filename"}), 400

    if not _validate_filename(filename):
        return jsonify({"error": "File type not allowed"}), 400

    file_path = os.path.join(_output_dir(request_id), filename)

    # Final safety: ensure resolved path is within the output directory
    output_root = os.path.abspath(_output_dir(request_id))
    resolved = os.path.abspath(file_path)
    if not resolved.startswith(output_root + os.sep):
        return jsonify({"error": "Path traversal blocked"}), 400

    if not os.path.isfile(file_path):
        return jsonify({"error": "File not found"}), 404

    return send_file(file_path)


@app.route("/api/demo_reset", methods=["POST"])
def api_demo_reset():
    """Clear all test requests and their associated test outputs.

    This endpoint clears:
    - All JSON files in requests/
    - All directories in outputs/

    It does NOT touch:
    - reports/ (genuine investigation reports and engineering data)
    - data/ (original datasets)
    - scripts/ (validation and investigation scripts)

    This is intended for resetting the dashboard to a clean state
    after testing. Genuine WorkBuddy investigation reports live in
    reports/ and are unaffected.

    Disabled in public demo mode (returns 403).
    """
    if PUBLIC_DEMO_MODE:
        return _public_mode_blocked()

    cleared = {"requests": 0, "outputs": 0}

    # Clear request JSON files
    if os.path.isdir(REQUESTS_DIR):
        for fn in os.listdir(REQUESTS_DIR):
            if fn.endswith(".json"):
                try:
                    os.remove(os.path.join(REQUESTS_DIR, fn))
                    cleared["requests"] += 1
                except Exception:
                    pass

    # Clear output directories (each subdirectory, not the outputs/ root)
    if os.path.isdir(OUTPUTS_DIR):
        for dn in os.listdir(OUTPUTS_DIR):
            dp = os.path.join(OUTPUTS_DIR, dn)
            if os.path.isdir(dp):
                try:
                    shutil.rmtree(dp)
                    cleared["outputs"] += 1
                except Exception:
                    pass

    return jsonify({
        "success": True,
        "cleared": cleared,
        "message": (f"Cleared {cleared['requests']} request(s) and "
                    f"{cleared['outputs']} output directory/directories. "
                    f"Reports in reports/ and data in data/ are unaffected."),
    })


if __name__ == "__main__":
    debug_mode = os.environ.get("GENBUDDY_DEBUG", "0") == "1"

    if PUBLIC_DEMO_MODE:
        # Production deployment using waitress WSGI server.
        # Binds to 0.0.0.0 so the dashboard is accessible externally.
        try:
            from waitress import serve
            port = int(os.environ.get("PORT", "5000"))
            print(f"GenBuddy public demo mode starting on 0.0.0.0:{port}")
            print("Write endpoints disabled. Local request/output files not exposed.")
            serve(app, host="0.0.0.0", port=port)
        except ImportError:
            print("ERROR: waitress is not installed.")
            print("Install with: pip install waitress")
            print("Or run without PUBLIC_DEMO_MODE for local development.")
            sys.exit(1)
    else:
        # Local development mode — Flask dev server on localhost only.
        app.run(host="127.0.0.1", port=5000, debug=debug_mode)
