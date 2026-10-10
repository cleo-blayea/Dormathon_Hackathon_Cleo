#!/usr/bin/env python3
"""
GenBuddy — Autonomous Fault Investigation Workflow
DORMATHON 2026 Track 2

GOAL: "Analyze generator readiness and prepare a maintenance action plan."

Steps:
  1. Validate CSV data (reuses scripts/validate_data.py)
  2. Load and analyze generator telemetry, ATS events, maintenance history
  3. Identify the three simulated scenarios
  4. Produce structured findings with causes, evidence, actions, priority
  5. Generate reports:
     - reports/generator_health_report.md
     - reports/maintenance_action_plan.csv
     - reports/agent_execution_log.md

DISCLAIMER: All data is simulated. No real equipment is connected.
Manufacturer DSE6120 alarm thresholds remain UNVERIFIED.
"""

import csv
import os
import subprocess
import sys
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("GENBUDDY_DATA_DIR", os.path.join(BASE, "data"))
REPORTS_DIR = os.environ.get("GENBUDDY_REPORTS_DIR", os.path.join(BASE, "reports"))
SCRIPTS_DIR = os.path.join(BASE, "scripts")

GEN_CSV = os.path.join(DATA_DIR, "generator_data.csv")
ATS_CSV = os.path.join(DATA_DIR, "ats_events.csv")
MAINT_CSV = os.path.join(DATA_DIR, "maintenance_history.csv")

VAL_SCRIPT = os.path.join(SCRIPTS_DIR, "validate_data.py")

# ── Constants (from generator_specs.json) ─────────────────────────────
SQRT3 = 1.7320508
V_LL_NOMINAL = 400.0           # Line-to-line voltage (V)
V_LN_NOMINAL = 230.0           # Line-to-neutral voltage (V)
FREQ_NOMINAL = 50.0
PF_NOMINAL = 0.8
S_RATED_KVA = 344.0
P_RATED_KW = 275.0
I_FULL_LOAD = S_RATED_KVA * 1000 / (SQRT3 * V_LL_NOMINAL)
FUEL_TANK_L = 522.0
BATT_NOMINAL = 24.0
RPM_NOMINAL = 1500
SIM_START_DATE = "2026-06-01"
SIM_START_HOURS = 1350.0

# ── Execution log ─────────────────────────────────────────────────────
_log_lines = []
_workflow_start = datetime.now()


def log(msg):
    """Append a timestamped line to the execution log."""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    _log_lines.append(line)
    print(line)


def load_csv(path):
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


# ═══════════════════════════════════════════════════════════════════════
# STEP 1: VALIDATION
# ═══════════════════════════════════════════════════════════════════════
def run_validation():
    """Run the existing validate_data.py and capture results."""
    log("STEP 1: Running validation (scripts/validate_data.py)")
    py = sys.executable
    result = subprocess.run(
        [py, VAL_SCRIPT],
        capture_output=True, text=True, timeout=60
    )
    output = result.stdout
    has_issues = "Issues: 0," not in output
    log(f"  Validation exit code: {result.returncode}")

    # Parse summary
    for line in output.splitlines():
        if line.strip().startswith("Issues:") or line.strip().startswith("  CHECK"):
            log(f"  {line.strip()}")

    if has_issues:
        log("  ⚠️ Validation found issues — proceeding with caution")
    else:
        log("  ✓ Validation passed — 0 issues")

    return result.returncode, output


# ═══════════════════════════════════════════════════════════════════════
# STEP 2: LOAD DATA
# ═══════════════════════════════════════════════════════════════════════
def load_data():
    """Load all three CSV files into memory."""
    log("STEP 2: Loading CSV data files")
    gen_rows, gen_cols = load_csv(GEN_CSV)
    ats_rows, ats_cols = load_csv(ATS_CSV)
    maint_rows, maint_cols = load_csv(MAINT_CSV)
    log(f"  generator_data.csv: {len(gen_rows)} records, {len(gen_cols)} columns")
    log(f"  ats_events.csv:     {len(ats_rows)} records, {len(ats_cols)} columns")
    log(f"  maintenance_history.csv: {len(maint_rows)} records, {len(maint_cols)} columns")
    return gen_rows, ats_rows, maint_rows


# ═══════════════════════════════════════════════════════════════════════
# STEP 3: SCENARIO ANALYSIS
# ═══════════════════════════════════════════════════════════════════════
def find_utility_failures(ats_rows):
    """Find each utility-failure event (UTILITY_FAIL_ALARM marks the start)."""
    failures = []
    for r in ats_rows:
        if "UTILITY_FAIL_ALARM" in r["alarm_events"]:
            failures.append(r["timestamp"])
    return failures


def get_gen_rows_in_window(gen_rows, t_start, t_end):
    """Return generator rows between t_start and t_end (inclusive)."""
    return [r for r in gen_rows if t_start <= r["timestamp"] <= t_end]


def get_ats_rows_in_window(ats_rows, t_start, t_end):
    """Return ATS rows between t_start and t_end (inclusive)."""
    return [r for r in ats_rows if t_start <= r["timestamp"] <= t_end]


def classify_scenario_window(window_gen, window_ats):
    """Classify a utility-failure window by telemetry and ATS event patterns.

    Examines actual data patterns — NOT positional order — to determine
    which scenario type each window represents.

    Returns one of:
      - 'NORMAL_OPERATION':   successful ATS transfer, no degradation
      - 'OVERHEATING':        RUNNING_DEGRADED or over-temp alarm present
      - 'ATS_TRANSFER_FAILURE': FAILED transfer confirmation
      - 'UNKNOWN':            no clear pattern matched
    """
    # Pattern 1: ATS transfer failure — transfer_confirmation = FAILED
    #           (distinct from utility_supply_status = "FAILED")
    failed_transfers = [r for r in window_ats
                        if r["transfer_confirmation"] == "FAILED"]

    # Pattern 2: Overheating — RUNNING_DEGRADED state or OVER_TEMP alarm
    degraded = [r for r in window_gen
                if r["operating_state"] == "RUNNING_DEGRADED"]
    over_temp = [r for r in window_ats
                 if "OVER_TEMP" in r.get("alarm_events", "")]

    # Pattern 3: Normal operation — CONFIRMED transfer to GENERATOR source
    confirmed_gen = [r for r in window_ats
                      if r["transfer_confirmation"] == "CONFIRMED"
                      and r["ats_commanded_source"] == "GENERATOR"]

    # Classification (priority order: transfer failure > overheating > normal)
    if failed_transfers:
        return "ATS_TRANSFER_FAILURE"
    if degraded or over_temp:
        return "OVERHEATING"
    if confirmed_gen:
        return "NORMAL_OPERATION"
    return "UNKNOWN"


def analyze_scenario_a(gen_rows, ats_rows, failure_ts):
    """Scenario A: Normal operation and successful ATS transfer."""
    log("STEP 3a: Analyzing Scenario A — Normal operation & successful ATS transfer")

    # Find the end of this scenario (utility restore or next failure)
    next_failure = None
    failures = find_utility_failures(ats_rows)
    for f in failures:
        if f > failure_ts:
            next_failure = f
            break

    window_ats = [r for r in ats_rows if r["timestamp"] >= failure_ts
                  and (next_failure is None or r["timestamp"] < next_failure)]
    window_gen = [r for r in gen_rows if r["timestamp"] >= failure_ts
                  and (next_failure is None or r["timestamp"] < next_failure)]

    # Key events
    gen_start = next((r for r in window_ats
                      if r["generator_running_status"] == "RUNNING"), None)
    transfer_confirmed = next((r for r in window_ats
                               if r["transfer_confirmation"] == "CONFIRMED"
                               and r["ats_commanded_source"] == "GENERATOR"), None)
    utility_restore = next((r for r in window_ats
                            if r["utility_supply_status"] == "NORMAL"
                            and r["ats_commanded_source"] == "UTILITY"
                            and r["transfer_confirmation"] == "CONFIRMED"), None)
    gen_stop = next((r for r in window_ats
                     if r["generator_running_status"] == "STOPPED"
                     and r["utility_supply_status"] == "NORMAL"
                     and r["timestamp"] > failure_ts), None)

    # Load period analysis
    running_loaded = [r for r in window_gen
                      if r["operating_state"] == "RUNNING"
                      and float(r["current_A"]) > 0]
    if running_loaded:
        powers = [float(r["active_power_kW"]) for r in running_loaded]
        avg_power = sum(powers) / len(powers)
        avg_load_pct = avg_power / P_RATED_KW * 100
        fuel_start = float(running_loaded[0]["fuel_level_L"])
        fuel_end = float(running_loaded[-1]["fuel_level_L"])
        fuel_used = fuel_start - fuel_end
    else:
        avg_power = 0
        avg_load_pct = 0
        fuel_used = 0

    finding = {
        "scenario": "Normal Operation & Successful ATS Transfer",
        "detection_pattern": "NORMAL_OPERATION",
        "classification": "NORMAL (no abnormality)",
        "timestamps": {
            "utility_fail": failure_ts,
            "gen_running": gen_start["timestamp"] if gen_start else "N/A",
            "ats_transferred": transfer_confirmed["timestamp"] if transfer_confirmed else "N/A",
            "utility_restored": utility_restore["timestamp"] if utility_restore else "N/A",
            "gen_stopped": gen_stop["timestamp"] if gen_stop else "N/A",
        },
        "measurements": {
            "avg_load_kW": round(avg_power, 1),
            "avg_load_pct": round(avg_load_pct, 1),
            "fuel_used_L": round(fuel_used, 1),
            "running_records": len(running_loaded),
        },
        "observed_issue": "None — generator started, ATS transferred load to generator, "
                          "utility restored, ATS transferred back, generator stopped normally.",
        "possible_causes": "N/A (normal operation)",
        "missing_evidence": "N/A",
        "suggested_action": "No corrective action required. Continue scheduled maintenance.",
        "priority": "INFORMATIONAL",
        "priority_justification": "All parameters within expected ranges. "
                                  "Successful start, transfer, and shutdown sequence.",
    }
    log(f"  Utility fail: {failure_ts}")
    log(f"  ATS transfer confirmed: {transfer_confirmed['timestamp'] if transfer_confirmed else 'N/A'}")
    log(f"  Avg load: {avg_power:.1f} kW ({avg_load_pct:.1f}%)")
    log(f"  Fuel used: {fuel_used:.1f} L")
    log(f"  Result: NORMAL — no abnormalities detected ✓")
    return finding


def analyze_scenario_b(gen_rows, ats_rows, failure_ts):
    """Scenario B: Rising coolant temperature during generator operation."""
    log("STEP 3b: Analyzing Scenario B — Rising coolant temperature")

    # Find next utility failure (scenario C start) or end of data
    failures = find_utility_failures(ats_rows)
    next_failure = None
    for f in failures:
        if f > failure_ts:
            next_failure = f
            break

    window_gen = [r for r in gen_rows if r["timestamp"] >= failure_ts
                  and (next_failure is None or r["timestamp"] < next_failure)]
    window_ats = [r for r in ats_rows if r["timestamp"] >= failure_ts
                  and (next_failure is None or r["timestamp"] < next_failure)]

    # Find RUNNING and RUNNING_DEGRADED records
    running = [r for r in window_gen
               if r["operating_state"] in ("RUNNING", "RUNNING_DEGRADED")]
    if not running:
        log("  ⚠️ No running records found in window")
        return None

    # Temperature trend
    temps = [(r["timestamp"], float(r["coolant_temp_C"]),
              r["operating_state"]) for r in running]
    temp_start = temps[0][1]
    temp_peak = max(t[1] for t in temps)
    temp_peak_ts = next(t[0] for t in temps if t[1] == temp_peak)

    degraded = [r for r in window_gen
                if r["operating_state"] == "RUNNING_DEGRADED"]
    degraded_start = degraded[0]["timestamp"] if degraded else "N/A"

    # Oil pressure trend
    oil_start = float(running[0]["oil_pressure_bar"])
    oil_end = float(running[-1]["oil_pressure_bar"])
    oil_decline = oil_start - oil_end

    # Shutdown
    shutdown = next((r for r in window_gen
                     if r["operating_state"] == "SHUTDOWN"), None)
    shutdown_ats = next((r for r in window_ats
                         if "OVER_TEMP" in r["alarm_events"]), None)

    # Load during this period
    loaded = [r for r in running if float(r["current_A"]) > 0]
    avg_load = sum(float(r["active_power_kW"]) for r in loaded) / len(loaded) if loaded else 0

    finding = {
        "scenario": "Rising Coolant Temperature",
        "detection_pattern": "OVERHEATING",
        "classification": "ABNORMAL — thermal anomaly with engine shutdown",
        "timestamps": {
            "utility_fail": failure_ts,
            "coolant_normal_start": f"{temp_start:.1f}°C at {temps[0][0]}",
            "degraded_start": degraded_start,
            "temp_peak": f"{temp_peak:.1f}°C at {temp_peak_ts}",
            "shutdown": shutdown["timestamp"] if shutdown else "N/A",
        },
        "measurements": {
            "coolant_start_C": round(temp_start, 1),
            "coolant_peak_C": round(temp_peak, 1),
            "oil_pressure_start_bar": round(oil_start, 2),
            "oil_pressure_end_bar": round(oil_end, 2),
            "oil_decline_bar": round(oil_decline, 2),
            "avg_load_kW": round(avg_load, 1),
            "running_records": len(running),
            "degraded_records": len(degraded),
        },
        "observed_issue": (
            f"Coolant temperature rose from {temp_start:.1f}°C to {temp_peak:.1f}°C "
            f"during ~{len(running)} minutes of generator operation at ~{avg_load:.0f} kW. "
            f"Generator entered RUNNING_DEGRADED state at {degraded_start} when coolant "
            f"exceeded ~105°C (simulated threshold — DSE6120 actual setting UNVERIFIED). "
            f"Oil pressure declined from {oil_start:.1f} to {oil_end:.1f} bar, "
            f"correlating with rising temperature. "
            f"Engine shut down due to over-temperature protection "
            f"at {shutdown['timestamp'] if shutdown else 'N/A'}."
        ),
        "possible_causes": (
            "1. Blocked or fouled radiator reducing heat dissipation. "
            "2. Low coolant level or coolant degradation (old coolant). "
            "3. Thermostat stuck closed preventing coolant circulation. "
            "4. Water pump failure or reduced impeller efficiency. "
            "5. Sustained high load (~70%) combined with high ambient temperature. "
            "6. Coolant hose restriction or collapsed hose. "
            "NOTE: These are possible causes, not confirmed diagnoses. "
            "DSE6120 alarm setpoints remain unverified."
        ),
        "missing_evidence": (
            "1. Ambient air temperature at generator location. "
            "2. Coolant flow rate or pump output. "
            "3. Radiator condition (fins, airflow path). "
            "4. Thermostat position/operation. "
            "5. Actual DSE6120 alarm threshold for coolant temperature. "
            "6. Coolant level and recent coolant service date. "
            "7. Engine room ventilation adequacy."
        ),
        "suggested_action": (
            "1. Inspect radiator for blockage, clean fins, verify airflow path. "
            "2. Check coolant level and quality; replace if degraded. "
            "3. Test thermostat operation; replace if stuck. "
            "4. Inspect water pump for wear or impeller damage. "
            "5. Verify engine room ventilation is adequate for standby rating. "
            "6. Obtain DSE6120 alarm setpoint configuration to confirm thresholds. "
            "7. Review load profile — 70% sustained load may require derating assessment."
        ),
        "priority": "HIGH",
        "priority_justification": (
            "Over-temperature shutdown caused total loss of generator backup power. "
            "If this recurs during a real utility outage, the facility has no backup. "
            "Thermal degradation risks engine damage (warped head, blown gasket). "
            "Must be resolved before next outage test."
        ),
    }
    log(f"  Coolant: {temp_start:.1f}°C → {temp_peak:.1f}°C (peak at {temp_peak_ts})")
    log(f"  Oil pressure: {oil_start:.1f} → {oil_end:.1f} bar (decline: {oil_decline:.1f})")
    log(f"  Degraded records: {len(degraded)}, shutdown: {'YES' if shutdown else 'NO'}")
    log(f"  Result: ABNORMAL — thermal anomaly with over-temp shutdown ⚠️")
    return finding


def analyze_scenario_c(gen_rows, ats_rows, failure_ts):
    """Scenario C: Generator starts but ATS fails to confirm transfer."""
    log("STEP 3c: Analyzing Scenario C — Unsuccessful ATS transfer")

    window_ats = [r for r in ats_rows if r["timestamp"] >= failure_ts]
    window_gen = [r for r in gen_rows if r["timestamp"] >= failure_ts]

    # Generator started successfully?
    gen_running = next((r for r in window_ats
                        if r["generator_running_status"] == "RUNNING"), None)

    # ATS commanded GENERATOR but actual stayed UTILITY
    transfer_failed = [r for r in window_ats
                       if r["transfer_confirmation"] == "FAILED"]
    first_fail = transfer_failed[0] if transfer_failed else None

    # Generator ran with no load (RUNNING_NL = voltage present but no current)
    no_load = [r for r in window_gen
               if r["operating_state"] == "RUNNING_NL"]
    no_load_duration = len(no_load)

    # Safety shutdown
    gen_stop = next((r for r in window_ats
                     if r["generator_running_status"] == "STOPPED"
                     and r["timestamp"] > failure_ts), None)

    # Facility dark period (utility failed, generator stopped)
    facility_dark = [r for r in window_ats
                     if "FACILITY_NO_POWER" in r.get("alarm_events", "")
                     or "NO_LOAD_TRANSFER" in r.get("alarm_events", "")]

    # Did utility eventually restore?
    utility_restore = next((r for r in window_ats
                           if r["utility_supply_status"] == "NORMAL"
                           and r["generator_running_status"] == "STOPPED"
                           and r["timestamp"] > failure_ts), None)

    # Voltage/freq present during no-load running (generator healthy)
    if no_load:
        v_vals = [float(r["voltage_LL_V"]) for r in no_load]
        f_vals = [float(r["frequency_Hz"]) for r in no_load]
        v_avg = sum(v_vals) / len(v_vals)
        f_avg = sum(f_vals) / len(f_vals)
    else:
        v_avg = 0
        f_avg = 0

    finding = {
        "scenario": "Unsuccessful ATS Transfer",
        "detection_pattern": "ATS_TRANSFER_FAILURE",
        "classification": "CRITICAL — generator healthy but load not transferred",
        "timestamps": {
            "utility_fail": failure_ts,
            "gen_running": gen_running["timestamp"] if gen_running else "N/A",
            "ats_fail_first": first_fail["timestamp"] if first_fail else "N/A",
            "gen_stopped": gen_stop["timestamp"] if gen_stop else "N/A",
            "utility_restored": utility_restore["timestamp"] if utility_restore else "N/A",
        },
        "measurements": {
            "gen_voltage_avg_V": round(v_avg, 1),
            "gen_freq_avg_Hz": round(f_avg, 2),
            "no_load_records": no_load_duration,
            "failed_transfer_records": len(transfer_failed),
            "facility_dark_records": len(facility_dark),
        },
        "observed_issue": (
            f"OBSERVED FACT: Utility failed at {failure_ts}. Generator started "
            f"successfully and produced nominal voltage ({v_avg:.0f}V) and "
            f"frequency ({f_avg:.1f}Hz). ATS commanded source = GENERATOR but "
            f"actual position reported UTILITY — transfer_confirmation = FAILED "
            f"for {len(transfer_failed)} consecutive records. Generator ran with "
            f"no load (RUNNING_NL, current=0) for {no_load_duration} minutes "
            f"before being commanded to stop for safety. "
            f"BUILDING POWER STATUS: Cannot be confirmed without load-bus voltage "
            f"data (not present in this dataset). The ATS position sensor reports "
            f"UTILITY, and the generator current sensor reports 0A, which is "
            f"consistent — but neither confirms whether the building had power "
            f"from utility or was without power."
        ),
        "possible_causes": (
            "The following are possible causes, NOT confirmed diagnoses. "
            "The fault has NOT been attributed to mechanical failure:\n"
            "1. SENSOR: ATS position sensor error — sensor may report UTILITY "
            "incorrectly while the switch actually transferred.\n"
            "2. SENSOR: ATS position limit switch intermittent fault.\n"
            "3. MEASUREMENT: Transfer-confirmation logic artefact — the DSE6120 "
            "confirmation input may have a transient or wiring issue.\n"
            "4. CONTROL: ATS control circuit fault — relay, contactor coil, or "
            "actuator command not reaching the mechanism.\n"
            "5. TOPOLOGY: Bypass path or dual-source configuration not modelled "
            "in this dataset — the facility may have a secondary transfer path.\n"
            "6. SIMULATION: Data generation artefact — this is simulated data; "
            "the FAILED status may represent a modelling choice, not a real fault.\n"
            "NOTE: Generator output was healthy (V, Hz normal), so any fault "
            "is in the ATS transfer path or its sensing, not the generator."
        ),
        "missing_evidence": (
            "1. Load-bus voltage — critical for confirming whether building had "
            "power during this period (NOT available in this dataset).\n"
            "2. ATS position sensor raw signal — to verify if position reading "
            "is accurate or if sensor is faulty.\n"
            "3. ATS contactor mechanical position — visual inspection needed.\n"
            "4. ATS control circuit voltage and continuity.\n"
            "5. Facility single-line diagram — to verify single-ATS topology "
            "assumption and rule out bypass paths.\n"
            "6. ATS motor/actuator coil resistance.\n"
            "7. Wiring continuity from DSE6120 to ATS.\n"
            "8. ATS maintenance/inspection history (last serviced date).\n"
            "9. ATS manufacturer model and specifications.\n"
            "10. Environmental conditions (moisture, dust in ATS enclosure)."
        ),
        "suggested_action": (
            "1. Verify topology — obtain facility single-line diagram to confirm "
            "single-ATS assumption and check for bypass paths.\n"
            "2. Inspect ATS position sensor and limit switches — do NOT assume "
            "mechanical failure before ruling out sensor issues.\n"
            "3. Test ATS control circuit voltage and relay operation.\n"
            "4. Measure ATS motor/actuator coil resistance; replace if out of spec.\n"
            "5. Inspect wiring between DSE6120 and ATS for corrosion or damage.\n"
            "6. Manually exercise ATS transfer to verify mechanical freedom.\n"
            "7. Install or verify load-bus voltage monitoring to confirm "
            "building power status during transfer events.\n"
            "8. Schedule ATS manufacturer service if internal fault suspected.\n"
            "9. Review ATS maintenance history — last service was "
            f"radiator/ATS contact inspection (see maintenance_history.csv)."
        ),
        "priority": "CRITICAL",
        "priority_justification": (
            "Generator was fully functional but ATS transfer was not confirmed — "
            "the generator was not feeding the building load (current=0A). "
            "Whether the building had power from utility during this period "
            "cannot be confirmed without load-bus voltage data. "
            "However, the ATS transfer-confirmation failure itself is critical: "
            "if the utility was truly failed and the ATS could not transfer, "
            "the standby system's core function is compromised. "
            "ATS transfer reliability is the single most critical function of "
            "a standby system. Must be investigated and resolved before "
            "returning to service."
        ),
    }
    log(f"  Generator started: {'YES' if gen_running else 'NO'}")
    log(f"  ATS transfer failed: {len(transfer_failed)} records")
    log(f"  No-load running: {no_load_duration} min")
    log(f"  Facility dark: {len(facility_dark)} records")
    log(f"  Gen voltage avg: {v_avg:.0f}V, freq avg: {f_avg:.1f}Hz")
    log(f"  Result: CRITICAL — ATS transfer failure, building power unconfirmed ⚠️")
    return finding


def analyze_general_health(gen_rows, ats_rows, maint_rows):
    """General health summary: fuel, battery, maintenance schedule."""
    log("STEP 3d: General health assessment")

    # Fuel
    fuels = [float(r["fuel_level_L"]) for r in gen_rows]
    fuel_min = min(fuels)
    fuel_pct = fuel_min / FUEL_TANK_L * 100
    log(f"  Min fuel: {fuel_min:.1f}L ({fuel_pct:.1f}% of tank)")

    # Battery
    batts = [float(r["battery_V"]) for r in gen_rows]
    batt_min = min(batts)
    batt_max = max(batts)
    log(f"  Battery range: {batt_min:.1f}V – {batt_max:.1f}V (nominal {BATT_NOMINAL}V)")

    # Max power
    powers = [float(r["active_power_kW"]) for r in gen_rows if float(r["active_power_kW"]) > 0]
    max_power = max(powers) if powers else 0
    log(f"  Max power: {max_power:.1f}kW / {P_RATED_KW}kW rated ({max_power/P_RATED_KW*100:.1f}%)")

    # Maintenance gap
    last_maint = maint_rows[-1]["maintenance_date"]
    last_maint_hours = float(maint_rows[-1]["running_hours"])
    sim_hours = SIM_START_HOURS
    gap_hours = sim_hours - last_maint_hours
    next_due = maint_rows[-1]["next_inspection_date"]
    log(f"  Last maintenance: {last_maint} at {last_maint_hours:.0f}h (gap to sim: {gap_hours:.0f}h)")
    log(f"  Next inspection due: {next_due}")

    health = {
        "min_fuel_L": round(fuel_min, 1),
        "fuel_tank_pct": round(fuel_pct, 1),
        "battery_min_V": round(batt_min, 2),
        "battery_max_V": round(batt_max, 2),
        "max_power_kW": round(max_power, 1),
        "max_load_pct": round(max_power / P_RATED_KW * 100, 1),
        "last_maint_date": last_maint,
        "last_maint_hours": last_maint_hours,
        "hours_since_maint": round(gap_hours),
        "next_inspection": next_due,
    }
    return health


# ═══════════════════════════════════════════════════════════════════════
# STEP 4: REPORT GENERATION
# ═══════════════════════════════════════════════════════════════════════
def generate_health_report(findings, health, val_output):
    """Write reports/generator_health_report.md"""
    log("STEP 4a: Generating generator_health_report.md")
    path = os.path.join(REPORTS_DIR, "generator_health_report.md")
    lines = []

    lines.append("# GenBuddy — Generator Health Report\n")
    lines.append("> **DISCLAIMER:** All data is SIMULATED. No real equipment connected. "
                 "DSE6120 alarm thresholds remain UNVERIFIED.\n")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"**Reference Generator:** AI Power ASC344 — "
                 f"{S_RATED_KVA:.0f} kVA / {P_RATED_KW:.0f} kW, "
                 f"{V_LL_NOMINAL:.0f}/{V_LN_NOMINAL:.0f}V, 50Hz\n")

    # ── Validation summary ──
    lines.append("## Data Validation Summary\n")
    val_pass = "Issues: 0," in val_output
    lines.append(f"- Validation status: {'**PASS** ✓' if val_pass else '⚠️ ISSUES FOUND'}")
    for line in val_output.splitlines():
        s = line.strip()
        if s.startswith("Issues:"):
            lines.append(f"- {s}")
    lines.append("")

    # ── General health ──
    lines.append("## General Health Assessment\n")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Minimum fuel level | {health['min_fuel_L']}L "
                 f"({health['fuel_tank_pct']}% of {FUEL_TANK_L}L tank) |")
    lines.append(f"| Battery voltage range | {health['battery_min_V']}V – {health['battery_max_V']}V "
                 f"(nominal {BATT_NOMINAL}V) |")
    lines.append(f"| Maximum load | {health['max_power_kW']}kW "
                 f"({health['max_load_pct']}% of {P_RATED_KW}kW rating) |")
    lines.append(f"| Last maintenance | {health['last_maint_date']} at "
                 f"{health['last_maint_hours']:.0f} running hours |")
    lines.append(f"| Hours since last maintenance | {health['hours_since_maint']}h |")
    lines.append(f"| Next inspection due | {health['next_inspection']} |\n")

    lines.append("**Note:** Battery voltage, coolant temperature, and oil pressure "
                 "warning limits are UNVERIFIED pending manufacturer DSE6120 configuration. "
                 "Alarm thresholds used in this analysis are SIMULATION ASSUMPTIONS.\n")

    # ── Scenario findings ──
    lines.append("## Scenario Analysis\n")
    lines.append("> Scenarios are identified by telemetry and ATS event patterns "
                 "(pattern-based classification), not by positional order.\n")
    for f in findings:
        if f is None:
            continue
        lines.append(f"### {f['scenario']}\n")
        lines.append(f"**Classification:** {f['classification']}\n")
        lines.append(f"**Detection pattern:** {f.get('detection_pattern', 'N/A')}\n")

        lines.append("**Key Timestamps:**\n")
        lines.append("| Event | Timestamp |")
        lines.append("|-------|-----------|")
        for k, v in f["timestamps"].items():
            lines.append(f"| {k} | {v} |")
        lines.append("")

        lines.append("**Supporting Measurements:**\n")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for k, v in f["measurements"].items():
            lines.append(f"| {k} | {v} |")
        lines.append("")

        lines.append(f"**Observed Issue:**\n{f['observed_issue']}\n")
        lines.append(f"**Possible Causes:**\n{f['possible_causes']}\n")
        lines.append(f"**Missing Evidence:**\n{f['missing_evidence']}\n")
        lines.append(f"**Suggested Inspection / Maintenance Action:**\n{f['suggested_action']}\n")
        lines.append(f"**Priority:** {f['priority']}\n")
        lines.append(f"**Priority Justification:** {f['priority_justification']}\n")
        lines.append("---\n")

    # ── Readiness conclusion ──
    lines.append("## Generator Readiness Assessment\n")
    critical = [f for f in findings if f and f["priority"] == "CRITICAL"]
    high = [f for f in findings if f and f["priority"] == "HIGH"]
    if critical or high:
        lines.append(f"**Status: NOT READY FOR SERVICE**\n")
        if critical:
            lines.append(f"- {len(critical)} CRITICAL issue(s) must be resolved immediately:")
            for c in critical:
                lines.append(f"  - {c['scenario']}: {c['observed_issue'][:80]}...")
        if high:
            lines.append(f"- {len(high)} HIGH priority issue(s) require attention:")
            for h in high:
                lines.append(f"  - {h['scenario']}: {h['observed_issue'][:80]}...")
    else:
        lines.append("**Status: READY** — No critical or high-priority issues detected.\n")

    lines.append("\n---\n*Report generated by GenBuddy Autonomous Fault Investigation Workflow.*")

    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    log(f"  Written: {path}")


def generate_action_plan(findings):
    """Write reports/maintenance_action_plan.csv"""
    log("STEP 4b: Generating maintenance_action_plan.csv")
    path = os.path.join(REPORTS_DIR, "maintenance_action_plan.csv")
    header = [
        "finding_id", "scenario", "detection_pattern", "priority", "observed_issue",
        "possible_causes", "missing_evidence",
        "suggested_action", "priority_justification",
    ]
    rows = []
    for i, f in enumerate(findings, 1):
        if f is None:
            continue
        # Truncate issue for CSV readability
        issue_short = f["observed_issue"].replace("\n", " ")[:300]
        rows.append([
            f"F-{i:02d}",
            f["scenario"],
            f.get("detection_pattern", "N/A"),
            f["priority"],
            issue_short,
            f["possible_causes"].replace("\n", " "),
            f["missing_evidence"].replace("\n", " "),
            f["suggested_action"].replace("\n", " "),
            f["priority_justification"].replace("\n", " "),
        ])

    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    log(f"  Written: {path} ({len(rows)} findings)")


def generate_exec_log(val_output, findings, report_files):
    """Write reports/agent_execution_log.md"""
    log("STEP 4c: Generating agent_execution_log.md")
    path = os.path.join(REPORTS_DIR, "agent_execution_log.md")
    lines = []

    lines.append("# GenBuddy — Agent Execution Log\n")
    lines.append("> **DISCLAIMER:** All data is SIMULATED. No real equipment connected.\n")
    lines.append(f"**Workflow goal:** Analyze generator readiness and prepare a maintenance action plan.\n")
    lines.append(f"**Execution started:** {_workflow_start.strftime('%Y-%m-%d %H:%M:%S')}\n")

    lines.append("## Steps Executed\n")
    for line in _log_lines:
        lines.append(f"- {line}")

    lines.append("\n## Validation Results\n")
    lines.append("```")
    for line in val_output.splitlines():
        s = line.strip()
        if s.startswith("Issues:") or s.startswith("CHECK") or s.startswith("  "):
            lines.append(s)
    lines.append("```")

    lines.append("\n## Findings Summary\n")
    lines.append("| ID | Scenario | Pattern | Priority | Classification |")
    lines.append("|----|----------|---------|----------|----------------|")
    for i, f in enumerate(findings, 1):
        if f is None:
            continue
        pattern = f.get("detection_pattern", "N/A")
        lines.append(f"| F-{i:02d} | {f['scenario']} | {pattern} | {f['priority']} | {f['classification'][:40]} |")

    lines.append("\n## Generated Files\n")
    for rf in report_files:
        lines.append(f"- `{rf}`")

    elapsed = (datetime.now() - _workflow_start).total_seconds()
    lines.append(f"\n**Execution completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
                 f"({elapsed:.1f}s elapsed)")

    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    log(f"  Written: {path}")


# ═══════════════════════════════════════════════════════════════════════
# MAIN WORKFLOW
# ═══════════════════════════════════════════════════════════════════════
def main():
    """Execute the complete autonomous fault investigation workflow."""
    log("=" * 60)
    log("GenBuddy Autonomous Fault Investigation Workflow")
    log("GOAL: Analyze generator readiness and prepare a maintenance action plan.")
    log("=" * 60)

    os.makedirs(REPORTS_DIR, exist_ok=True)

    # STEP 1: Validate
    rc, val_output = run_validation()

    # STEP 2: Load data
    gen_rows, ats_rows, maint_rows = load_data()

    # STEP 3: Analyze scenarios by telemetry and ATS event patterns
    log("STEP 3: Analyzing generator telemetry and ATS events")
    log("  Detection method: pattern-based classification (not positional order)")
    failures = find_utility_failures(ats_rows)
    log(f"  Found {len(failures)} utility-failure event(s): {failures}")

    findings = []
    for i, fail_ts in enumerate(failures):
        # Determine window end: next utility failure or end of data
        next_fail = failures[i + 1] if i + 1 < len(failures) else None

        # Extract rows within this utility-failure window
        window_gen = [r for r in gen_rows if r["timestamp"] >= fail_ts
                      and (next_fail is None or r["timestamp"] < next_fail)]
        window_ats = [r for r in ats_rows if r["timestamp"] >= fail_ts
                      and (next_fail is None or r["timestamp"] < next_fail)]

        # Classify window by actual telemetry and ATS event patterns
        pattern = classify_scenario_window(window_gen, window_ats)
        log(f"  Window {i + 1} (start: {fail_ts}): classified as {pattern}")

        if pattern == "NORMAL_OPERATION":
            findings.append(analyze_scenario_a(gen_rows, ats_rows, fail_ts))
        elif pattern == "OVERHEATING":
            findings.append(analyze_scenario_b(gen_rows, ats_rows, fail_ts))
        elif pattern == "ATS_TRANSFER_FAILURE":
            findings.append(analyze_scenario_c(gen_rows, ats_rows, fail_ts))
        else:
            log(f"  WARNING: Unclassified pattern for window starting at {fail_ts} — skipping")

    # General health
    health = analyze_general_health(gen_rows, ats_rows, maint_rows)

    # STEP 4: Generate reports
    log("STEP 4: Generating reports")
    generate_health_report(findings, health, val_output)
    generate_action_plan(findings)

    report_files = [
        os.path.join(REPORTS_DIR, "generator_health_report.md"),
        os.path.join(REPORTS_DIR, "maintenance_action_plan.csv"),
    ]
    generate_exec_log(val_output, findings, report_files)

    # Summary
    log("=" * 60)
    log("WORKFLOW COMPLETE")
    critical = sum(1 for f in findings if f and f["priority"] == "CRITICAL")
    high = sum(1 for f in findings if f and f["priority"] == "HIGH")
    normal = sum(1 for f in findings if f and f["priority"] == "INFORMATIONAL")
    log(f"  Scenarios identified: {len([f for f in findings if f])}")
    log(f"  CRITICAL: {critical}, HIGH: {high}, INFORMATIONAL: {normal}")
    log(f"  Reports in: {REPORTS_DIR}/")
    log("=" * 60)


if __name__ == "__main__":
    main()
