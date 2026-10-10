#!/usr/bin/env python3
"""
GenBuddy - Data Corrections
Fixes: duplicate ATS event, maintenance chronology, active power recalculation.
"""

import csv
import math
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
GEN_CSV = os.path.join(DATA_DIR, "generator_data.csv")
ATS_CSV = os.path.join(DATA_DIR, "ats_events.csv")
MAINT_CSV = os.path.join(DATA_DIR, "maintenance_history.csv")

SQRT3 = 1.7320508

# ── FIX 1: Remove exact duplicate ATS event at 2026-06-01T15:10:00 ──
def fix_ats_duplicates():
    with open(ATS_CSV, "r", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    header = rows[0]
    data = rows[1:]

    seen = set()
    deduped = []
    removed = 0
    for r in data:
        key = tuple(r)
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        deduped.append(r)

    with open(ATS_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(deduped)

    print(f"FIX 1: Removed {removed} exact duplicate ATS row(s)")
    print(f"  ATS rows: {len(data)} -> {len(deduped)}")


# ── FIX 2: Correct maintenance chronology ───────────────────────────
def fix_maintenance():
    """Telemetry starts 2026-06-01 at 1350 running hours.
    All maintenance must precede this date and have plausible hours."""
    records = [
        ["maintenance_date", "running_hours", "maintenance_type",
         "work_description", "next_inspection_date"],
        ["2025-08-15", "500.0", "Routine (250h)",
         "Oil and filter change, battery load test, coolant level check",
         "2025-11-15"],
        ["2025-11-15", "750.0", "Routine (250h)",
         "Oil change, fuel filter replacement, air filter cleaning, alternator inspection",
         "2026-02-15"],
        ["2026-02-15", "1000.0", "Major (1000h)",
         "Full service: all filters, valve clearance adjustment, "
         "injector inspection, controller firmware update",
         "2026-05-15"],
        ["2026-05-15", "1250.0", "Routine (250h)",
         "Oil and filter change, battery replacement (24V), "
         "radiator cleaning, ATS contact inspection",
         "2026-08-15"],
    ]
    with open(MAINT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerows(records)
    print(f"FIX 2: Maintenance chronology corrected")
    print(f"  All dates now precede 2026-06-01 (simulation start)")
    print(f"  Running hours: 500 -> 750 -> 1000 -> 1250 (all < 1350)")


# ── FIX 3: Recalculate active power P = sqrt(3) * V * I * PF / 1000 ─
def fix_power():
    with open(GEN_CSV, "r", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    header = rows[0]
    data = rows[1:]

    # Column indices
    idx_state = header.index("operating_state")
    idx_v = header.index("voltage_LL_V")
    idx_i = header.index("current_A")
    idx_p = header.index("active_power_kW")
    idx_pf = header.index("power_factor")

    recalc_count = 0
    for r in data:
        state = r[idx_state]
        v = float(r[idx_v])
        i = float(r[idx_i])
        pf = float(r[idx_pf])

        # Recalculate only for loaded running states with nonzero current
        if state in ("RUNNING", "RUNNING_DEGRADED") and i > 0:
            p_new = SQRT3 * v * i * pf / 1000.0
            r[idx_p] = f"{round(p_new, 1)}"
            recalc_count += 1

    with open(GEN_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(data)

    print(f"FIX 3: Recalculated active power for {recalc_count} loaded running record(s)")
    print(f"  Formula: P = sqrt(3) * V_LL * I * PF / 1000")


if __name__ == "__main__":
    fix_ats_duplicates()
    fix_maintenance()
    fix_power()
    print("\nAll corrections applied. Run validate_data.py to verify.")
