# GenBuddy Data Validation Report

> **DISCLAIMER:** All data is simulated. No real equipment involved.

**Generated:** 2026-10-10 20:01:40

**Records:** 176 generator, 176 ATS, 4 maintenance

## Summary

| Metric | Result |
|--------|--------|
| Critical issues | 0 |
| Warnings | 0 |
| Overall | **PASS** |

## Detailed Checks

CHECK 1: Column presence
  generator_data.csv: All 13 columns present ✓
  ats_events.csv: All 8 columns present ✓
  maintenance_history.csv: All 5 columns present ✓
CHECK 2: State vs power consistency
  No nonzero power/current/voltage when stopped or starting ✓
CHECK 3: Unrealistic numerical values
  No unrealistic numerical values detected ✓
  Max active power: 199.4kW (rated: 275.0kW)
  Within rated capacity ✓
CHECK 4: Electrical consistency (P ≈ sqrt(3) * V * I * PF)
  Checked 75 RUNNING rows with load
  Max discrepancy: 0.03%
  Electrical values consistent within 2% tolerance ✓
CHECK 5: ATS event contradictions
  No ATS contradictions found ✓
CHECK 6: Fuel tank capacity compliance
  Fuel range: 425.2L – 480.0L (tank: 522.0L)
  All fuel levels within tank capacity ✓
  Fuel decreases during operation ✓
CHECK 7: Timestamp synchronization
  Generator timestamps: 176
  ATS timestamps: 176
  Gen timestamps without ATS match: 0
  ATS timestamps without Gen match: 0
  All ATS timestamps have matching generator records ✓
CHECK 8: Scenario verification
  Scenario A (successful transfer): 77 confirmed gen-source transfers
  Scenario B (rising coolant): 5 degraded records, temp range 105.1–107.7°C
  Scenario C (ATS transfer fail): 11 FAILED transfer records
CHECK 9: Duplicate event records
  generator_data: No exact duplicates ✓
  ats_events: No exact duplicates ✓
CHECK 10: Maintenance date chronology
  All maintenance dates precede 2026-06-01 ✓
  All running hours < 1350.0 ✓
  Chronological order maintained ✓
CHECK 11: Missing values (empty fields)
  No missing/empty values found ✓
CHECK 12: Power calculation accuracy (strict)
  Checked 75 loaded RUNNING records
  Max discrepancy: 0.029%
  All power values match formula within 1% ✓
CHECK 13: ATS-position vs load-current topology consistency
  Assumption: single-ATS topology (generator feeds building via ATS)
  NOTE: Building power continuity cannot be confirmed without
        load-bus voltage data (not present in this dataset).
  No ATS-UTILITY + significant-generator-current cases found ✓

## Conclusion

All validation checks passed. The simulated data is internally consistent, states are coherent, electrical values are within tolerance, ATS events are non-contradictory, and fuel levels respect the 522L tank capacity.

Temperature, oil pressure, and battery warning limits remain **unverified** until manufacturer DSE6120 settings are obtained.

**Topology note:** ATS-position vs load-current consistency checked under single-ATS assumption. Building power continuity cannot be confirmed without load-bus voltage data.