#!/usr/bin/env python3
"""
GenBuddy - Simulated Data Generator
DORMATHON 2026 Track 2

DISCLAIMER: All data produced by this script is SIMULATED.
No real generator is connected, monitored, or controlled.
"""

import csv
import math
import os
from datetime import datetime, timedelta

# ── Electrical constants ──────────────────────────────────────────────
SQRT3 = 1.7320508
V_LL_NOMINAL = 400.0          # Line-to-line voltage (V)
FREQ_NOMINAL = 50.0           # Frequency (Hz)
PF_NOMINAL = 0.8              # Power factor
S_RATED_KVA = 344.0           # Standby rating (kVA)
P_RATED_KW = 275.0            # Standby rating (kW)
I_FULL_LOAD = S_RATED_KVA * 1000 / (SQRT3 * V_LL_NOMINAL)  # ≈ 496.55 A
RPM_NOMINAL = 1500
BATT_NOMINAL = 24.0
FUEL_TANK_L = 522.0

# Fuel consumption L/h at load fractions
FUEL_TABLE = {
    0.25: 15.8,
    0.50: 31.6,
    0.75: 47.1,
    1.00: 65.2,
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
GEN_CSV = os.path.join(DATA_DIR, "generator_data.csv")
ATS_CSV = os.path.join(DATA_DIR, "ats_events.csv")
MAINT_CSV = os.path.join(DATA_DIR, "maintenance_history.csv")


def fuel_rate(load_frac):
    """Interpolate fuel consumption (L/h) from manufacturer table."""
    if load_frac <= 0:
        return 0.0
    pts = sorted(FUEL_TABLE.items())
    if load_frac <= pts[0][0]:
        return pts[0][1] * (load_frac / pts[0][0])
    for i in range(len(pts) - 1):
        lo, hi = pts[i], pts[i + 1]
        if lo[0] <= load_frac <= hi[0]:
            t = (load_frac - lo[0]) / (hi[0] - lo[0])
            return lo[1] + t * (hi[1] - lo[1])
    return pts[-1][1]


def jitter(base, pct):
    """Add ±pct random jitter to a base value."""
    import random
    rng = random.Random()
    return round(base * (1 + rng.uniform(-pct, pct)), 2)


# ── CSV writers (shared) ──────────────────────────────────────────────
GEN_HEADER = [
    "timestamp", "operating_state", "voltage_LL_V", "frequency_Hz",
    "current_A", "active_power_kW", "power_factor", "engine_speed_rpm",
    "coolant_temp_C", "oil_pressure_bar", "battery_V", "fuel_level_L",
    "running_hours",
]

ATS_HEADER = [
    "timestamp", "utility_supply_status", "generator_start_command",
    "generator_running_status", "ats_commanded_source", "ats_actual_position",
    "transfer_confirmation", "alarm_events",
]

MAINT_HEADER = [
    "maintenance_date", "running_hours", "maintenance_type",
    "work_description", "next_inspection_date",
]

gen_rows = []
ats_rows = []


def add_gen(ts, state, v_ll, freq, current, power_kw, pf, rpm,
            coolant, oil, batt, fuel, run_hours):
    gen_rows.append([
        ts.isoformat(), state, round(v_ll, 1), round(freq, 2),
        round(current, 1), round(power_kw, 1), round(pf, 2),
        rpm, round(coolant, 1), round(oil, 2), round(batt, 2),
        round(fuel, 1), round(run_hours, 1),
    ])


def add_ats(ts, utility, start_cmd, gen_running, commanded, actual,
            confirm, alarms):
    ats_rows.append([
        ts.isoformat(), utility, start_cmd, gen_running,
        commanded, actual, confirm, alarms,
    ])


# Deterministic RNG for reproducibility
import random
RNG = random.Random(42)


def rnd(base, pct):
    return round(base * (1 + RNG.uniform(-pct, pct)), 2)


# ═══════════════════════════════════════════════════════════════════════
# SCENARIO A: Normal operation and successful ATS transfer
# ═══════════════════════════════════════════════════════════════════════
def scenario_a(start_dt, run_hours_start, fuel_start):
    """
    Timeline (~80 min):
      0-15 min  : Standby, utility normal
      15 min    : Utility fails → ATS commands generator start
      15-17 min : Generator cranks & starts (ramping)
      17 min    : ATS transfers to generator
      17-45 min : Generator running under ~60% load
      45 min    : Utility restores → ATS transfers back
      45-48 min : Generator cool-down run (no load)
      48 min    : Generator stops
      48-80 min : Back to standby, utility normal
    """
    ts = start_dt
    fuel = fuel_start
    run_h = run_hours_start
    load = 0.0
    INTERVAL = 1  # minutes

    # --- Phase 1: Standby (utility normal) — 15 records ---
    for _ in range(15):
        add_gen(ts, "STANDBY", 0.0, 0.0, 0.0, 0.0, 0.0, 0,
                rnd(28, 0.05), 0.0, rnd(24.3, 0.02), round(fuel, 1), run_h)
        add_ats(ts, "NORMAL", "OFF", "STOPPED", "UTILITY", "UTILITY",
                "N/A", "NONE")
        ts += timedelta(minutes=INTERVAL)

    # --- ATS event: utility fails ---
    add_ats(ts, "FAILED", "ON", "STARTING", "GENERATOR", "UTILITY",
            "PENDING", "UTILITY_FAIL_ALARM")
    add_gen(ts, "STARTING", 0.0, 0.0, 0.0, 0.0, 0.0, 0,
            rnd(28, 0.05), rnd(2.5, 0.1), rnd(22.0, 0.05),
            round(fuel, 1), run_h)
    ts += timedelta(seconds=30)

    # --- Phase 2: Generator cranking & starting (ramping) — 3 records ---
    for i in range(3):
        ramp = (i + 1) / 3.0
        v = rnd(V_LL_NOMINAL * ramp, 0.01)
        f = rnd(FREQ_NOMINAL * ramp, 0.01)
        rpm = int(RPM_NOMINAL * ramp)
        add_gen(ts, "STARTING", v, f, 0.0, 0.0, 0.0, rpm,
                rnd(30 + i * 3, 0.03), rnd(3.0 + i, 0.05),
                rnd(24.0, 0.03), round(fuel, 1), run_h)
        add_ats(ts, "FAILED", "ON", "STARTING", "GENERATOR", "UTILITY",
                "PENDING", "NONE")
        ts += timedelta(seconds=30)

    # --- Generator now running, ATS transfers ---
    add_gen(ts, "RUNNING", rnd(V_LL_NOMINAL, 0.005), rnd(FREQ_NOMINAL, 0.005),
            0.0, 0.0, 0.0, RPM_NOMINAL, rnd(42, 0.03), rnd(4.0, 0.05),
            rnd(24.5, 0.02), round(fuel, 1), run_h)
    add_ats(ts, "FAILED", "ON", "RUNNING", "GENERATOR", "GENERATOR",
            "CONFIRMED", "NONE")
    ts += timedelta(seconds=30)

    # --- Phase 3: Generator running under ~60% load — 28 records ---
    load = 0.60
    for _ in range(28):
        lf = load + RNG.uniform(-0.02, 0.02)
        s_kva = S_RATED_KVA * lf
        p_kw = s_kva * PF_NOMINAL
        i_a = s_kva * 1000 / (SQRT3 * V_LL_NOMINAL)
        pf = rnd(PF_NOMINAL, 0.02)
        v = rnd(V_LL_NOMINAL, 0.005)
        f = rnd(FREQ_NOMINAL, 0.003)
        fuel -= fuel_rate(lf) / 60.0  # per minute
        run_h += 1 / 60.0
        coolant = rnd(82 + RNG.uniform(-2, 3), 0.0)  # gradually warming
        add_gen(ts, "RUNNING", v, f, i_a, p_kw, pf, RPM_NOMINAL,
                round(coolant, 1), rnd(4.2, 0.05), rnd(27.5, 0.02),
                round(fuel, 1), run_h)
        add_ats(ts, "FAILED", "ON", "RUNNING", "GENERATOR", "GENERATOR",
                "CONFIRMED", "NONE")
        ts += timedelta(minutes=INTERVAL)

    # --- Phase 4: Utility restores, ATS transfers back ---
    add_ats(ts, "NORMAL", "OFF", "RUNNING", "UTILITY", "UTILITY",
            "CONFIRMED", "NONE")
    add_gen(ts, "RUNNING_NL", rnd(V_LL_NOMINAL, 0.005), rnd(FREQ_NOMINAL, 0.005),
            0.0, 0.0, 0.0, RPM_NOMINAL, rnd(80, 0.03), rnd(3.5, 0.05),
            rnd(27.0, 0.02), round(fuel, 1), run_h)
    ts += timedelta(minutes=2)

    # --- Phase 5: Cool-down run (no load) — 2 records ---
    for _ in range(2):
        fuel -= fuel_rate(0.0) / 60.0
        run_h += 1 / 60.0
        add_gen(ts, "RUNNING_NL", rnd(V_LL_NOMINAL, 0.005),
                rnd(FREQ_NOMINAL, 0.005), 0.0, 0.0, 0.0, RPM_NOMINAL,
                rnd(75, 0.03), rnd(3.2, 0.05), rnd(26.5, 0.02),
                round(fuel, 1), run_h)
        add_ats(ts, "NORMAL", "OFF", "RUNNING_NL", "UTILITY", "UTILITY",
                "CONFIRMED", "NONE")
        ts += timedelta(minutes=1)

    # --- Generator stops ---
    add_gen(ts, "SHUTDOWN", 0.0, 0.0, 0.0, 0.0, 0.0, 0,
            rnd(70, 0.03), 0.0, rnd(25.5, 0.02), round(fuel, 1), run_h)
    add_ats(ts, "NORMAL", "OFF", "STOPPED", "UTILITY", "UTILITY",
                "N/A", "NONE")
    ts += timedelta(minutes=1)

    # --- Phase 6: Back to standby — 25 records ---
    for _ in range(25):
        add_gen(ts, "STANDBY", 0.0, 0.0, 0.0, 0.0, 0.0, 0,
                rnd(30, 0.05), 0.0, rnd(24.3, 0.02), round(fuel, 1), run_h)
        add_ats(ts, "NORMAL", "OFF", "STOPPED", "UTILITY", "UTILITY",
                "N/A", "NONE")
        ts += timedelta(minutes=INTERVAL)

    return ts, run_h, fuel


# ═══════════════════════════════════════════════════════════════════════
# SCENARIO B: Rising coolant temperature during generator operation
# ═══════════════════════════════════════════════════════════════════════
def scenario_b(start_dt, run_hours_start, fuel_start):
    """
    Timeline (~60 min):
      0-3 min  : Utility fails → generator starts → ATS transfers (fast)
      3-50 min : Generator running ~70% load; coolant rises from ~85°C
                 to ~108°C (anomaly trend). Oil pressure slowly drops.
      50 min   : High temperature alarm triggered
      50-55 min: Generator continues running with alarm (degraded)
      55-58 min: Generator shuts down (over-temperature protection)
      58-60 min: Standby recovery
    """
    ts = start_dt
    fuel = fuel_start
    run_h = run_hours_start
    INTERVAL = 1

    # Utility fails & generator starts
    add_ats(ts, "FAILED", "ON", "STARTING", "GENERATOR", "UTILITY",
            "PENDING", "UTILITY_FAIL_ALARM")
    add_gen(ts, "STARTING", 0.0, 0.0, 0.0, 0.0, 0.0, 0,
            rnd(30, 0.05), rnd(2.5, 0.1), rnd(22.5, 0.05),
            round(fuel, 1), run_h)
    ts += timedelta(seconds=30)

    # Quick ramp-up & ATS transfer
    for i in range(2):
        ramp = (i + 1) / 2.0
        add_gen(ts, "STARTING", rnd(V_LL_NOMINAL * ramp, 0.01),
                rnd(FREQ_NOMINAL * ramp, 0.01), 0.0, 0.0, 0.0,
                int(RPM_NOMINAL * ramp), rnd(35 + i * 5, 0.03),
                rnd(3.0 + i, 0.05), rnd(24.0, 0.03), round(fuel, 1), run_h)
        add_ats(ts, "FAILED", "ON", "STARTING", "GENERATOR", "UTILITY",
                "PENDING", "NONE")
        ts += timedelta(seconds=30)

    # ATS transfers successfully
    add_ats(ts, "FAILED", "ON", "RUNNING", "GENERATOR", "GENERATOR",
            "CONFIRMED", "NONE")
    add_gen(ts, "RUNNING", rnd(V_LL_NOMINAL, 0.005), rnd(FREQ_NOMINAL, 0.005),
            0.0, 0.0, 0.0, RPM_NOMINAL, rnd(45, 0.03), rnd(4.0, 0.05),
            rnd(24.5, 0.02), round(fuel, 1), run_h)
    ts += timedelta(seconds=30)

    # Running with rising coolant — 47 records
    load = 0.70
    coolant_base = 85.0
    oil_base = 4.5
    alarm_threshold = 105.0
    for i in range(47):
        lf = load + RNG.uniform(-0.02, 0.02)
        s_kva = S_RATED_KVA * lf
        p_kw = s_kva * PF_NOMINAL
        i_a = s_kva * 1000 / (SQRT3 * V_LL_NOMINAL)
        pf = rnd(PF_NOMINAL, 0.02)
        v = rnd(V_LL_NOMINAL, 0.005)
        f = rnd(FREQ_NOMINAL, 0.003)
        fuel -= fuel_rate(lf) / 60.0
        run_h += 1 / 60.0

        # Coolant rises nonlinearly toward ~108°C
        progress = i / 46.0
        coolant = coolant_base + (108.0 - coolant_base) * (progress ** 1.5)
        coolant += RNG.uniform(-0.5, 0.5)

        # Oil pressure slowly drops as temperature rises
        oil = oil_base - (oil_base - 3.2) * progress + RNG.uniform(-0.1, 0.1)

        alarms = "NONE"
        state = "RUNNING"
        if coolant >= alarm_threshold:
            alarms = "HIGH_COOLANT_TEMP_WARNING"
            state = "RUNNING_DEGRADED"

        add_gen(ts, state, v, f, i_a, p_kw, pf, RPM_NOMINAL,
                round(coolant, 1), round(oil, 2), rnd(27.5, 0.02),
                round(fuel, 1), run_h)
        add_ats(ts, "FAILED", "ON", "RUNNING", "GENERATOR", "GENERATOR",
                "CONFIRMED", alarms)
        ts += timedelta(minutes=INTERVAL)

    # Over-temperature shutdown
    add_gen(ts, "SHUTDOWN", 0.0, 0.0, 0.0, 0.0, 0.0, 0,
            round(coolant, 1), 0.0, rnd(26.0, 0.02), round(fuel, 1), run_h)
    add_ats(ts, "FAILED", "OFF", "STOPPED", "GENERATOR", "GENERATOR",
            "N/A", "OVER_TEMP_SHUTDOWN")
    ts += timedelta(minutes=1)

    # Utility restores, back to standby — 3 records
    for _ in range(3):
        add_gen(ts, "STANDBY", 0.0, 0.0, 0.0, 0.0, 0.0, 0,
                rnd(50, 0.05), 0.0, rnd(24.3, 0.02), round(fuel, 1), run_h)
        add_ats(ts, "NORMAL", "OFF", "STOPPED", "UTILITY", "UTILITY",
                "N/A", "NONE")
        ts += timedelta(minutes=INTERVAL)

    return ts, run_h, fuel


# ═══════════════════════════════════════════════════════════════════════
# SCENARIO C: Generator starts but ATS fails to confirm transfer
# ═══════════════════════════════════════════════════════════════════════
def scenario_c(start_dt, run_hours_start, fuel_start):
    """
    Timeline (~45 min):
      0-2 min  : Utility fails → generator starts successfully
      2 min    : ATS commanded to transfer to GENERATOR
      2-5 min  : ATS actual position stays on UTILITY (transfer not confirmed)
      5 min    : ATS_FAIL alarm raised; generator keeps running (no load on gen)
      5-10 min : Generator runs with no load transfer (output present but
                 not connected to facility load)
      10 min   : Manual/safety: generator commanded to stop
      10-15 min: Generator cools and stops; utility remains failed
                 (facility is dark — no power)
      15-45 min: All stopped; utility eventually restores
    """
    ts = start_dt
    fuel = fuel_start
    run_h = run_hours_start
    INTERVAL = 1

    # Utility fails, generator starts
    add_ats(ts, "FAILED", "ON", "STARTING", "GENERATOR", "UTILITY",
            "PENDING", "UTILITY_FAIL_ALARM")
    add_gen(ts, "STARTING", 0.0, 0.0, 0.0, 0.0, 0.0, 0,
            rnd(28, 0.05), rnd(2.5, 0.1), rnd(22.5, 0.05),
            round(fuel, 1), run_h)
    ts += timedelta(seconds=30)

    # Quick ramp-up
    for i in range(2):
        ramp = (i + 1) / 2.0
        add_gen(ts, "STARTING", rnd(V_LL_NOMINAL * ramp, 0.01),
                rnd(FREQ_NOMINAL * ramp, 0.01), 0.0, 0.0, 0.0,
                int(RPM_NOMINAL * ramp), rnd(35 + i * 5, 0.03),
                rnd(3.0 + i, 0.05), rnd(24.0, 0.03), round(fuel, 1), run_h)
        add_ats(ts, "FAILED", "ON", "STARTING", "GENERATOR", "UTILITY",
                "PENDING", "NONE")
        ts += timedelta(seconds=30)

    # Generator is running, ATS commanded to GENERATOR but actual stays UTILITY
    add_ats(ts, "FAILED", "ON", "RUNNING", "GENERATOR", "UTILITY",
            "FAILED", "ATS_TRANSFER_FAIL_ALARM")

    # Generator runs with voltage/freq but NO load (ATS didn't transfer)
    # Current = 0, power = 0 (generator output present but not feeding load)
    # This is realistic: generator is running but not connected to facility
    for _ in range(5):
        add_gen(ts, "RUNNING_NL", rnd(V_LL_NOMINAL, 0.005),
                rnd(FREQ_NOMINAL, 0.005), 0.0, 0.0, 0.0, RPM_NOMINAL,
                rnd(65 + RNG.uniform(-2, 2), 0.0), rnd(4.0, 0.05),
                rnd(27.5, 0.02), round(fuel, 1), run_h)
        add_ats(ts, "FAILED", "ON", "RUNNING", "GENERATOR", "UTILITY",
                "FAILED", "ATS_TRANSFER_FAIL_ALARM")
        fuel -= fuel_rate(0.25) / 60.0  # light fuel use even at no load
        run_h += 1 / 60.0
        ts += timedelta(minutes=INTERVAL)

    # Alarm escalates
    for _ in range(5):
        add_gen(ts, "RUNNING_NL", rnd(V_LL_NOMINAL, 0.005),
                rnd(FREQ_NOMINAL, 0.005), 0.0, 0.0, 0.0, RPM_NOMINAL,
                rnd(72 + RNG.uniform(-2, 2), 0.0), rnd(3.8, 0.05),
                rnd(27.0, 0.02), round(fuel, 1), run_h)
        add_ats(ts, "FAILED", "ON", "RUNNING", "GENERATOR", "UTILITY",
                "FAILED", "ATS_TRANSFER_FAIL_ALARM;NO_LOAD_TRANSFER")
        fuel -= fuel_rate(0.25) / 60.0
        run_h += 1 / 60.0
        ts += timedelta(minutes=INTERVAL)

    # Generator commanded to stop (safety)
    add_gen(ts, "SHUTDOWN", 0.0, 0.0, 0.0, 0.0, 0.0, 0,
            rnd(70, 0.03), 0.0, rnd(26.0, 0.02), round(fuel, 1), run_h)
    add_ats(ts, "FAILED", "OFF", "STOPPED", "GENERATOR", "UTILITY",
            "FAILED", "ATS_TRANSFER_FAIL;GEN_STOPPED_NO_LOAD")
    ts += timedelta(minutes=1)

    # Utility still failed, generator stopped — facility dark — 10 records
    for _ in range(10):
        add_gen(ts, "STANDBY", 0.0, 0.0, 0.0, 0.0, 0.0, 0,
                rnd(45, 0.05), 0.0, rnd(24.0, 0.02), round(fuel, 1), run_h)
        add_ats(ts, "FAILED", "OFF", "STOPPED", "UTILITY", "UTILITY",
                "N/A", "FACILITY_NO_POWER")
        ts += timedelta(minutes=INTERVAL)

    # Utility restores — 20 records
    for _ in range(20):
        add_gen(ts, "STANDBY", 0.0, 0.0, 0.0, 0.0, 0.0, 0,
                rnd(30, 0.05), 0.0, rnd(24.3, 0.02), round(fuel, 1), run_h)
        add_ats(ts, "NORMAL", "OFF", "STOPPED", "UTILITY", "UTILITY",
                "N/A", "NONE")
        ts += timedelta(minutes=INTERVAL)

    return ts, run_h, fuel


# ═══════════════════════════════════════════════════════════════════════
# MAINTENANCE HISTORY
# ═══════════════════════════════════════════════════════════════════════
def generate_maintenance():
    records = [
        ["2025-08-15", 500.0, "Routine (250h)",
         "Oil and filter change, battery load test, coolant level check",
         "2025-11-15"],
        ["2025-11-15", 750.0, "Routine (250h)",
         "Oil change, fuel filter replacement, air filter cleaning, "
         "alternator inspection",
         "2026-02-15"],
        ["2026-02-15", 1000.0, "Major (1000h)",
         "Full service: all filters, valve clearance adjustment, "
         "injector inspection, controller firmware update",
         "2026-05-15"],
        ["2026-05-15", 1250.0, "Routine (250h)",
         "Oil and filter change, battery replacement (24V), "
         "radiator cleaning, ATS contact inspection",
         "2026-08-15"],
    ]
    return records


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys as _sys

    # ── Overwrite protection ──────────────────────────────────────────
    # Refuse to overwrite existing corrected datasets unless --force is given.
    existing = [f for f in ["generator_data.csv", "ats_events.csv",
                            "maintenance_history.csv"]
                if os.path.isfile(os.path.join(DATA_DIR, f))]
    if existing and "--force" not in _sys.argv:
        print("ERROR: Existing data files found in", DATA_DIR)
        for f in existing:
            print(f"  - {f}")
        print("\nThese files have been corrected and validated.")
        print("To regenerate and overwrite, use: python generate_data.py --force")
        _sys.exit(1)

    os.makedirs(DATA_DIR, exist_ok=True)

    base_time = datetime(2026, 6, 1, 8, 0, 0)
    run_hours = 1350.0
    fuel = 480.0  # start with 480L in the 522L tank

    # Run scenarios in sequence
    t, rh, fl = scenario_a(base_time, run_hours, fuel)
    t, rh, fl = scenario_b(t + timedelta(hours=2), rh, fl)
    t, rh, fl = scenario_c(t + timedelta(hours=3), rh, fl)

    # Write generator_data.csv
    with open(GEN_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(GEN_HEADER)
        w.writerows(gen_rows)

    # Write ats_events.csv
    with open(ATS_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(ATS_HEADER)
        w.writerows(ats_rows)

    # Write maintenance_history.csv
    maint = generate_maintenance()
    with open(MAINT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(MAINT_HEADER)
        w.writerows(maint)

    print(f"Generator data records: {len(gen_rows)}")
    print(f"ATS event records:      {len(ats_rows)}")
    print(f"Maintenance records:    {len(maint)}")
    print(f"\nFiles written to: {DATA_DIR}")
    for fn in ["generator_data.csv", "ats_events.csv", "maintenance_history.csv"]:
        print(f"  - {fn}")
