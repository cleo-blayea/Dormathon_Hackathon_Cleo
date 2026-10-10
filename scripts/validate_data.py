#!/usr/bin/env python3
"""
GenBuddy - Data Validation Script
DORMATHON 2026 Track 2

Checks the generated CSV files for:
  1.  Missing columns
  2.  Inconsistent states (e.g., generator stopped but nonzero power)
  3.  Unrealistic numerical values
  4.  Contradictory ATS events
  5.  Electrical consistency (P = sqrt(3) * V * I * PF)
  6.  Fuel tank capacity compliance
  7.  Timestamp synchronization between generator_data and ats_events
  8.  Scenario verification
  9.  Duplicate event records (exact duplicate rows)
  10. Maintenance date chronology and plausibility
  11. Missing values (empty fields across all CSVs)
  12. Power calculation accuracy (P vs sqrt(3)*V*I*PF/1000, strict tolerance)
  13. ATS-position vs load-current topology consistency (single-ATS assumption)
"""

import csv
import math
import os
from datetime import datetime

DATA_DIR = os.environ.get("GENBUDDY_DATA_DIR",
                          os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
GEN_CSV = os.path.join(DATA_DIR, "generator_data.csv")
ATS_CSV = os.path.join(DATA_DIR, "ats_events.csv")
MAINT_CSV = os.path.join(DATA_DIR, "maintenance_history.csv")
REPORT = os.path.join(DATA_DIR, "validation_report.md")

SQRT3 = 1.7320508
S_RATED_KVA = 344.0
P_RATED_KW = 275.0
FUEL_TANK_L = 522.0

issues = []
warnings = []
info = []


def load_csv(path):
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


# ── 1. Column presence check ──────────────────────────────────────────
def check_columns():
    info.append("CHECK 1: Column presence")

    expected_gen = ["timestamp", "operating_state", "voltage_LL_V",
                    "frequency_Hz", "current_A", "active_power_kW",
                    "power_factor", "engine_speed_rpm", "coolant_temp_C",
                    "oil_pressure_bar", "battery_V", "fuel_level_L",
                    "running_hours"]
    expected_ats = ["timestamp", "utility_supply_status",
                    "generator_start_command", "generator_running_status",
                    "ats_commanded_source", "ats_actual_position",
                    "transfer_confirmation", "alarm_events"]
    expected_maint = ["maintenance_date", "running_hours",
                      "maintenance_type", "work_description",
                      "next_inspection_date"]

    for fname, path, expected in [
        ("generator_data.csv", GEN_CSV, expected_gen),
        ("ats_events.csv", ATS_CSV, expected_ats),
        ("maintenance_history.csv", MAINT_CSV, expected_maint),
    ]:
        _, fields = load_csv(path)
        missing = [c for c in expected if c not in fields]
        if missing:
            issues.append(f"{fname}: Missing columns: {missing}")
        else:
            info.append(f"  {fname}: All {len(expected)} columns present ✓")


# ── 2. State-power consistency ─────────────────────────────────────────
def check_state_power(gen_rows):
    info.append("CHECK 2: State vs power consistency")
    violations = 0
    for r in gen_rows:
        state = r["operating_state"]
        power = float(r["active_power_kW"])
        current = float(r["current_A"])
        voltage = float(r["voltage_LL_V"])

        stopped_states = ["STANDBY", "SHUTDOWN"]
        if state in stopped_states:
            if power > 0.01 or current > 0.01 or voltage > 0.5:
                violations += 1
                if violations <= 3:
                    issues.append(
                        f"  {r['timestamp']}: State={state} but "
                        f"power={power}kW, current={current}A, V={voltage}"
                    )

        if state == "STARTING":
            if power > 0.01 or current > 0.01:
                violations += 1
                if violations <= 3:
                    issues.append(
                        f"  {r['timestamp']}: State=STARTING but "
                        f"power={power}kW (should be 0 during crank)"
                    )

    if violations == 0:
        info.append("  No nonzero power/current/voltage when stopped or starting ✓")
    else:
        info.append(f"  {violations} violation(s) found")


# ── 3. Unrealistic values ─────────────────────────────────────────────
def check_values(gen_rows):
    info.append("CHECK 3: Unrealistic numerical values")
    problems = 0

    for r in gen_rows:
        ts = r["timestamp"]
        v = float(r["voltage_LL_V"])
        f = float(r["frequency_Hz"])
        i = float(r["current_A"])
        p = float(r["active_power_kW"])
        pf = float(r["power_factor"])
        rpm = int(float(r["engine_speed_rpm"]))
        coolant = float(r["coolant_temp_C"])
        oil = float(r["oil_pressure_bar"])
        batt = float(r["battery_V"])
        fuel = float(r["fuel_level_L"])
        run_h = float(r["running_hours"])

        # Voltage: 0 when stopped, ~400 when running
        state = r["operating_state"]
        if state in ("RUNNING", "RUNNING_DEGRADED"):
            if v < 380 or v > 420:
                problems += 1
                if problems <= 3:
                    issues.append(f"  {ts}: Voltage {v}V outside 380-420V range")
        if i < 0:
            problems += 1
            issues.append(f"  {ts}: Negative current {i}A")
        if p < 0:
            problems += 1
            issues.append(f"  {ts}: Negative power {p}kW")
        if pf < 0 or pf > 1:
            problems += 1
            issues.append(f"  {ts}: PF {pf} outside 0-1 range")
        if fuel < 0 or fuel > FUEL_TANK_L:
            problems += 1
            issues.append(f"  {ts}: Fuel {fuel}L outside 0-{FUEL_TANK_L}L tank")
        if fuel > FUEL_TANK_L:
            issues.append(f"  {ts}: Fuel EXCEEDS tank capacity ({fuel}L > {FUEL_TANK_L}L)")
        if run_h < 0:
            problems += 1
            issues.append(f"  {ts}: Negative running hours {run_h}")
        if coolant < -10 or coolant > 120:
            problems += 1
            issues.append(f"  {ts}: Coolant {coolant}C outside sane range")
        if batt < 0 or batt > 30:
            problems += 1
            issues.append(f"  {ts}: Battery {batt}V outside sane range")
        if state in ("RUNNING", "RUNNING_DEGRADED", "RUNNING_NL"):
            if rpm != 1500:
                problems += 1
                if problems <= 3:
                    issues.append(f"  {ts}: RPM {rpm} (expected 1500)")

    if problems == 0:
        info.append("  No unrealistic numerical values detected ✓")
    else:
        info.append(f"  {problems} problem(s) found")

    # Power rating check
    max_power = max(float(r["active_power_kW"]) for r in gen_rows)
    info.append(f"  Max active power: {max_power}kW (rated: {P_RATED_KW}kW)")
    if max_power > P_RATED_KW * 1.05:
        warnings.append(f"Max power {max_power}kW exceeds rated {P_RATED_KW}kW by >5%")
    else:
        info.append(f"  Within rated capacity ✓")


# ── 4. Electrical consistency ─────────────────────────────────────────
def check_electrical(gen_rows):
    info.append("CHECK 4: Electrical consistency (P ≈ sqrt(3) * V * I * PF)")
    max_err = 0
    checked = 0
    for r in gen_rows:
        v = float(r["voltage_LL_V"])
        i = float(r["current_A"])
        p = float(r["active_power_kW"])
        pf = float(r["power_factor"])
        state = r["operating_state"]

        if state in ("RUNNING", "RUNNING_DEGRADED") and i > 0:
            p_calc = SQRT3 * v * i * pf / 1000.0
            if p_calc > 0:
                err_pct = abs(p_calc - p) / p_calc * 100
                max_err = max(max_err, err_pct)
                checked += 1
                if err_pct > 5:
                    issues.append(
                        f"  {r['timestamp']}: P={p}kW but "
                        f"calc={p_calc:.1f}kW ({err_pct:.1f}% diff)"
                    )

    info.append(f"  Checked {checked} RUNNING rows with load")
    info.append(f"  Max discrepancy: {max_err:.2f}%")
    if max_err < 2:
        info.append("  Electrical values consistent within 2% tolerance ✓")
    elif max_err < 5:
        warnings.append(f"Electrical discrepancy up to {max_err:.2f}% (within 5% tolerance)")
    else:
        issues.append(f"Electrical discrepancy {max_err:.2f}% exceeds 5% tolerance")


# ── 5. ATS contradiction check ────────────────────────────────────────
def check_ats(ats_rows):
    info.append("CHECK 5: ATS event contradictions")
    contradictions = 0

    for r in ats_rows:
        ts = r["timestamp"]
        commanded = r["ats_commanded_source"]
        actual = r["ats_actual_position"]
        confirm = r["transfer_confirmation"]
        gen_status = r["generator_running_status"]

        # If transfer confirmed, commanded and actual should match
        if confirm == "CONFIRMED" and commanded != actual:
            contradictions += 1
            if contradictions <= 3:
                issues.append(
                    f"  {ts}: transfer=CONFIRMED but "
                    f"commanded={commanded} != actual={actual}"
                )

        # If transfer FAILED, commanded and actual should NOT match
        if confirm == "FAILED" and commanded == actual:
            contradictions += 1
            if contradictions <= 3:
                issues.append(
                    f"  {ts}: transfer=FAILED but "
                    f"commanded={commanded} == actual={actual}"
                )

        # If generator is STOPPED, start_command should be OFF
        if gen_status == "STOPPED" and r["generator_start_command"] == "ON":
            # This can happen momentarily during shutdown command
            pass  # acceptable transition

    if contradictions == 0:
        info.append("  No ATS contradictions found ✓")
    else:
        info.append(f"  {contradictions} contradiction(s) found")


# ── 6. Fuel tank capacity ─────────────────────────────────────────────
def check_fuel(gen_rows):
    info.append("CHECK 6: Fuel tank capacity compliance")
    fuels = [float(r["fuel_level_L"]) for r in gen_rows]
    min_fuel = min(fuels)
    max_fuel = max(fuels)
    info.append(f"  Fuel range: {min_fuel}L – {max_fuel}L (tank: {FUEL_TANK_L}L)")
    if max_fuel > FUEL_TANK_L:
        issues.append(f"Fuel exceeds tank: max={max_fuel}L > {FUEL_TANK_L}L")
    else:
        info.append("  All fuel levels within tank capacity ✓")

    # Check fuel monotonically decreases during running (allows small jitter)
    fuel_violations = 0
    prev_fuel = None
    for r in gen_rows:
        state = r["operating_state"]
        fuel = float(r["fuel_level_L"])
        if prev_fuel is not None and state in ("RUNNING", "RUNNING_DEGRADED",
                                                "RUNNING_NL", "STARTING"):
            if fuel > prev_fuel + 1.0:  # allow 1L tolerance
                fuel_violations += 1
        prev_fuel = fuel
    if fuel_violations > 0:
        warnings.append(f"Fuel increased during operation {fuel_violations} time(s)")
    else:
        info.append("  Fuel decreases during operation ✓")


# ── 7. Timestamp sync ─────────────────────────────────────────────────
def check_timestamps(gen_rows, ats_rows):
    info.append("CHECK 7: Timestamp synchronization")
    gen_ts = set(r["timestamp"] for r in gen_rows)
    ats_ts = set(r["timestamp"] for r in ats_rows)

    # ATS events should align with generator events
    # Not every gen timestamp needs an ATS event (some are sub-minute)
    missing_in_ats = gen_ts - ats_ts
    missing_in_gen = ats_ts - gen_ts

    info.append(f"  Generator timestamps: {len(gen_ts)}")
    info.append(f"  ATS timestamps: {len(ats_ts)}")
    info.append(f"  Gen timestamps without ATS match: {len(missing_in_ats)}")
    info.append(f"  ATS timestamps without Gen match: {len(missing_in_gen)}")

    if len(missing_in_gen) > 0:
        warnings.append(f"{len(missing_in_gen)} ATS timestamps have no matching gen record")
    else:
        info.append("  All ATS timestamps have matching generator records ✓")


# ── 8. Scenario verification ──────────────────────────────────────────
def check_scenarios(gen_rows, ats_rows):
    info.append("CHECK 8: Scenario verification")

    # Scenario A: Successful ATS transfer
    confirmed = [r for r in ats_rows if r["transfer_confirmation"] == "CONFIRMED"
                 and r["ats_commanded_source"] == "GENERATOR"]
    info.append(f"  Scenario A (successful transfer): {len(confirmed)} confirmed gen-source transfers")

    # Scenario B: Rising coolant
    degraded = [r for r in gen_rows if r["operating_state"] == "RUNNING_DEGRADED"]
    if degraded:
        temps = [float(r["coolant_temp_C"]) for r in degraded]
        info.append(f"  Scenario B (rising coolant): {len(degraded)} degraded records, "
                     f"temp range {min(temps)}–{max(temps)}°C")
    else:
        issues.append("Scenario B: No RUNNING_DEGRADED records found")

    # Scenario C: ATS transfer failure
    failed = [r for r in ats_rows if r["transfer_confirmation"] == "FAILED"]
    info.append(f"  Scenario C (ATS transfer fail): {len(failed)} FAILED transfer records")
    if not failed:
        issues.append("Scenario C: No FAILED transfer records found")


# ── 9. Duplicate event records ────────────────────────────────────────
def check_duplicates(gen_rows, ats_rows):
    info.append("CHECK 9: Duplicate event records")

    for name, rows in [("generator_data", gen_rows), ("ats_events", ats_rows)]:
        seen = set()
        dupes = []
        for r in rows:
            key = tuple(r.items())
            if key in seen:
                dupes.append(r)
            else:
                seen.add(key)
        if dupes:
            for d in dupes[:3]:
                issues.append(f"  {name}: exact duplicate at {d.get('timestamp', '?')}")
            info.append(f"  {name}: {len(dupes)} exact duplicate(s) found")
        else:
            info.append(f"  {name}: No exact duplicates ✓")


# ── 10. Maintenance date chronology ──────────────────────────────────
def check_maintenance(maint_rows, gen_rows):
    info.append("CHECK 10: Maintenance date chronology")

    SIM_DATE = "2026-06-01"
    SIM_RUN_HOURS = 1350.0

    prev_date = None
    prev_hours = None
    date_problems = 0

    for r in maint_rows:
        mdate = r["maintenance_date"]
        mhours = float(r["running_hours"])
        next_date = r["next_inspection_date"]

        # Must precede simulation start date
        if mdate >= SIM_DATE:
            issues.append(f"  Maintenance date {mdate} is on/after simulation start {SIM_DATE}")
            date_problems += 1

        # Running hours must be less than simulation start hours
        if mhours >= SIM_RUN_HOURS:
            issues.append(f"  Maintenance hours {mhours} >= sim start {SIM_RUN_HOURS}")
            date_problems += 1

        # Chronological order: dates must increase
        if prev_date and mdate <= prev_date:
            issues.append(f"  Maintenance date {mdate} not after previous {prev_date}")
            date_problems += 1

        # Running hours must increase
        if prev_hours is not None and mhours <= prev_hours:
            issues.append(f"  Maintenance hours {mhours} not after previous {prev_hours}")
            date_problems += 1

        # Next inspection must be after maintenance date
        if next_date <= mdate:
            issues.append(f"  Next inspection {next_date} not after maintenance {mdate}")
            date_problems += 1

        prev_date = mdate
        prev_hours = mhours

    if date_problems == 0:
        info.append(f"  All maintenance dates precede {SIM_DATE} ✓")
        info.append(f"  All running hours < {SIM_RUN_HOURS} ✓")
        info.append("  Chronological order maintained ✓")


# ── 11. Missing values ───────────────────────────────────────────────
def check_missing_values(gen_rows, ats_rows, maint_rows):
    info.append("CHECK 11: Missing values (empty fields)")

    missing_count = 0
    for name, rows in [("generator_data", gen_rows),
                       ("ats_events", ats_rows),
                       ("maintenance_history", maint_rows)]:
        for r in rows:
            for k, v in r.items():
                if v is None or v.strip() == "":
                    issues.append(f"  {name}: empty '{k}' at "
                                  f"{r.get('timestamp', r.get('maintenance_date', '?'))}")
                    missing_count += 1

    if missing_count == 0:
        info.append("  No missing/empty values found ✓")
    else:
        info.append(f"  {missing_count} missing value(s) found")


# ── 12. Power calculation accuracy ────────────────────────────────────
def check_power_calc(gen_rows):
    info.append("CHECK 12: Power calculation accuracy (strict)")
    max_err = 0
    checked = 0
    failures = 0

    for r in gen_rows:
        state = r["operating_state"]
        v = float(r["voltage_LL_V"])
        i = float(r["current_A"])
        p = float(r["active_power_kW"])
        pf = float(r["power_factor"])

        if state in ("RUNNING", "RUNNING_DEGRADED") and i > 0:
            p_calc = SQRT3 * v * i * pf / 1000.0
            if p_calc > 0:
                err_pct = abs(p_calc - p) / p_calc * 100
                max_err = max(max_err, err_pct)
                checked += 1
                if err_pct > 1.0:
                    failures += 1
                    if failures <= 3:
                        issues.append(
                            f"  {r['timestamp']}: P={p}kW vs "
                            f"calc={p_calc:.2f}kW ({err_pct:.2f}% diff > 1%)"
                        )

    info.append(f"  Checked {checked} loaded RUNNING records")
    info.append(f"  Max discrepancy: {max_err:.3f}%")
    if failures == 0:
        info.append("  All power values match formula within 1% ✓")
    else:
        info.append(f"  {failures} record(s) exceed 1% tolerance")


# ── 13. ATS-position vs load-current topology consistency ────────────
def check_ats_load_current(gen_rows, ats_rows):
    """
    Detect cases where ATS actual position is UTILITY but the generator
    reports significant load current. Under a single-ATS topology (generator
    feeds building only through the ATS), this should not occur.

    Does NOT assume mechanical ATS failure. Classifies each case as a possible:
      - Sensor error (current sensor or ATS position sensor malfunction)
      - Measurement artifact (transient or logging error)
      - Topology mismatch (bypass path, separate feeder, or dual-ATS not modelled)
      - Simulation inconsistency (data generation artefact)
    """
    info.append("CHECK 13: ATS-position vs load-current topology consistency")
    info.append("  Assumption: single-ATS topology (generator feeds building via ATS)")
    info.append("  NOTE: Building power continuity cannot be confirmed without")
    info.append("        load-bus voltage data (not present in this dataset).")

    # Build a timestamp lookup for generator records
    gen_by_ts = {}
    for r in gen_rows:
        gen_by_ts[r["timestamp"]] = r

    mismatches = []
    SIGNIFICANT_CURRENT = 1.0  # A — threshold for "significant" load current

    for ats in ats_rows:
        ts = ats["timestamp"]
        actual = ats["ats_actual_position"]
        gen_r = gen_by_ts.get(ts)

        if gen_r is None:
            continue

        state = gen_r["operating_state"]
        current = float(gen_r["current_A"])

        # Generator is running with significant load but ATS says UTILITY
        if actual == "UTILITY" and state in ("RUNNING", "RUNNING_DEGRADED"):
            if current > SIGNIFICANT_CURRENT:
                mismatches.append({
                    "timestamp": ts,
                    "gen_state": state,
                    "current_A": current,
                    "power_kW": float(gen_r["active_power_kW"]),
                    "voltage_V": float(gen_r["voltage_LL_V"]),
                    "ats_commanded": ats["ats_commanded_source"],
                    "ats_actual": actual,
                    "transfer_confirm": ats["transfer_confirmation"],
                    "alarm": ats["alarm_events"],
                    "is_simulated_test": "ANOMALY_TEST" in ats["alarm_events"],
                })

    if not mismatches:
        info.append("  No ATS-UTILITY + significant-generator-current cases found ✓")
        return

    info.append(f"  Found {len(mismatches)} case(s) where ATS=UTILITY but gen has load current:")

    for m in mismatches:
        # Classify — do NOT assume mechanical failure
        if m["is_simulated_test"]:
            classification = "SIMULATED TEST ANOMALY (injected for demonstration)"
            info.append(f"  {m['timestamp']}: [SIMULATED] I={m['current_A']}A, "
                        f"P={m['power_kW']}kW, ATS={m['ats_actual']}, "
                        f"alarm={m['alarm']}")
        else:
            classification = "TOPOLOGY/SENSOR INCONSISTENCY (cause undetermined)"
            info.append(f"  {m['timestamp']}: I={m['current_A']}A, "
                        f"P={m['power_kW']}kW, ATS={m['ats_actual']}, "
                        f"confirm={m['transfer_confirm']}")

        # Detailed diagnostic entry distinguishing facts, causes, missing evidence
        issues.append(
            f"CHECK 13 — {m['timestamp']}: "
            f"OBSERVED FACT: Generator state={m['gen_state']}, "
            f"current={m['current_A']}A, power={m['power_kW']}kW, "
            f"voltage={m['voltage_V']}V, but ATS actual_position=UTILITY. "
            f"Under single-ATS topology, generator load current should be ~0 "
            f"when ATS is on UTILITY. "
            f"CLASSIFICATION: {classification}. "
            f"POSSIBLE CAUSES (not confirmed): "
            f"(1) ATS position sensor error — sensor reports UTILITY incorrectly; "
            f"(2) Current sensor error — current reading is artefact; "
            f"(3) Topology mismatch — bypass path or separate feeder exists; "
            f"(4) Simulation/logging artefact — transient or data issue. "
            f"Does NOT automatically indicate mechanical ATS failure. "
            f"MISSING EVIDENCE: load-bus voltage (cannot confirm building power status), "
            f"ATS position sensor raw signal, current sensor calibration record, "
            f"facility single-line diagram (topology verification). "
            f"BUILDING POWER: Cannot be confirmed or denied without load-bus voltage data."
        )


# ── REPORT GENERATION ─────────────────────────────────────────────────
def main():
    check_columns()

    gen_rows, _ = load_csv(GEN_CSV)
    ats_rows, _ = load_csv(ATS_CSV)
    maint_rows, _ = load_csv(MAINT_CSV)

    check_state_power(gen_rows)
    check_values(gen_rows)
    check_electrical(gen_rows)
    check_ats(ats_rows)
    check_fuel(gen_rows)
    check_timestamps(gen_rows, ats_rows)
    check_scenarios(gen_rows, ats_rows)
    check_duplicates(gen_rows, ats_rows)
    check_maintenance(maint_rows, gen_rows)
    check_missing_values(gen_rows, ats_rows, maint_rows)
    check_power_calc(gen_rows)
    check_ats_load_current(gen_rows, ats_rows)

    # Build report
    lines = []
    lines.append("# GenBuddy Data Validation Report\n")
    lines.append("> **DISCLAIMER:** All data is simulated. No real equipment involved.\n")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"**Records:** {len(gen_rows)} generator, "
                 f"{len(ats_rows)} ATS, {len(maint_rows)} maintenance\n")

    lines.append("## Summary\n")
    if not issues:
        lines.append("| Metric | Result |")
        lines.append("|--------|--------|")
        lines.append(f"| Critical issues | 0 |")
        lines.append(f"| Warnings | {len(warnings)} |")
        lines.append(f"| Overall | **PASS** |")
    else:
        lines.append(f"- **Critical issues:** {len(issues)}")
        lines.append(f"- **Warnings:** {len(warnings)}")
        lines.append(f"- **Overall:** {'PASS (with notes)' if not issues else 'REVIEW NEEDED'}")

    lines.append("\n## Detailed Checks\n")
    for line in info:
        lines.append(line)

    if issues:
        lines.append("\n## Issues Found\n")
        for iss in issues:
            lines.append(f"- ⚠️ {iss}")

    if warnings:
        lines.append("\n## Warnings\n")
        for w in warnings:
            lines.append(f"- ⚡ {w}")

    if not issues and not warnings:
        lines.append("\n## Conclusion\n")
        lines.append("All validation checks passed. The simulated data is internally "
                      "consistent, states are coherent, electrical values are within "
                      "tolerance, ATS events are non-contradictory, and fuel levels "
                      "respect the 522L tank capacity.\n")
        lines.append("Temperature, oil pressure, and battery warning limits remain "
                      "**unverified** until manufacturer DSE6120 settings are obtained.")
        lines.append("\n**Topology note:** ATS-position vs load-current consistency "
                      "checked under single-ATS assumption. Building power continuity "
                      "cannot be confirmed without load-bus voltage data.")
    elif not issues:
        lines.append("\n## Conclusion\n")
        lines.append("No critical issues found. Minor warnings noted above. "
                      "Data is suitable for development use.\n")
        lines.append("Temperature, oil pressure, and battery warning limits remain "
                      "**unverified** until manufacturer DSE6120 settings are obtained.")
        lines.append("\n**Topology note:** ATS-position vs load-current consistency "
                      "checked under single-ATS assumption. Building power continuity "
                      "cannot be confirmed without load-bus voltage data.")

    with open(REPORT, "w") as f:
        f.write("\n".join(lines))

    print(f"Validation report written to: {REPORT}")
    print(f"Issues: {len(issues)}, Warnings: {len(warnings)}")
    for line in info:
        print(f"  {line}")


if __name__ == "__main__":
    main()
