# GenBuddy Data Validation Report

> **DISCLAIMER:** All data is simulated. No real equipment involved.

**Generated:** 2026-10-10 11:07:41

**Records:** 176 generator, 177 ATS, 4 maintenance

## Summary

| Metric | Result |
|--------|--------|
| Critical issues | 0 |
| Warnings | 1 |
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
  Max active power: 197.6kW (rated: 275.0kW)
  Within rated capacity ✓
CHECK 4: Electrical consistency (P ≈ sqrt(3) * V * I * PF)
  Checked 75 RUNNING rows with load
  Max discrepancy: 2.91%
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
  Scenario C (ATS transfer fail): 12 FAILED transfer records

## Warnings

- ⚡ Electrical discrepancy up to 2.91% (within 5% tolerance)

## Conclusion

No critical issues found. Minor warnings noted above. Data is suitable for development use.

Temperature, oil pressure, and battery warning limits remain **unverified** until manufacturer DSE6120 settings are obtained.