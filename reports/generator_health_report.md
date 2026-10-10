# GenBuddy — Generator Health Report

> **DISCLAIMER:** All data is SIMULATED. No real equipment connected. DSE6120 alarm thresholds remain UNVERIFIED.

**Generated:** 2026-10-10 20:01:40

**Reference Generator:** AI Power ASC344 — 344 kVA / 275 kW, 400/230V, 50Hz

## Data Validation Summary

- Validation status: **PASS** ✓
- Issues: 0, Warnings: 0

## General Health Assessment

| Metric | Value |
|--------|-------|
| Minimum fuel level | 425.2L (81.5% of 522.0L tank) |
| Battery voltage range | 22.08V – 28.04V (nominal 24.0V) |
| Maximum load | 199.4kW (72.5% of 275.0kW rating) |
| Last maintenance | 2026-05-15 at 1250 running hours |
| Hours since last maintenance | 100h |
| Next inspection due | 2026-08-15 |

**Note:** Battery voltage, coolant temperature, and oil pressure warning limits are UNVERIFIED pending manufacturer DSE6120 configuration. Alarm thresholds used in this analysis are SIMULATION ASSUMPTIONS.

## Scenario Analysis

> Scenarios are identified by telemetry and ATS event patterns (pattern-based classification), not by positional order.

### Normal Operation & Successful ATS Transfer

**Classification:** NORMAL (no abnormality)

**Detection pattern:** NORMAL_OPERATION

**Key Timestamps:**

| Event | Timestamp |
|-------|-----------|
| utility_fail | 2026-06-01T08:15:00 |
| gen_running | 2026-06-01T08:17:00 |
| ats_transferred | 2026-06-01T08:17:00 |
| utility_restored | 2026-06-01T08:45:30 |
| gen_stopped | 2026-06-01T08:49:30 |

**Supporting Measurements:**

| Metric | Value |
|--------|-------|
| avg_load_kW | 165.6 |
| avg_load_pct | 60.2 |
| fuel_used_L | 17.1 |
| running_records | 28 |

**Observed Issue:**
None — generator started, ATS transferred load to generator, utility restored, ATS transferred back, generator stopped normally.

**Possible Causes:**
N/A (normal operation)

**Missing Evidence:**
N/A

**Suggested Inspection / Maintenance Action:**
No corrective action required. Continue scheduled maintenance.

**Priority:** INFORMATIONAL

**Priority Justification:** All parameters within expected ranges. Successful start, transfer, and shutdown sequence.

---

### Rising Coolant Temperature

**Classification:** ABNORMAL — thermal anomaly with engine shutdown

**Detection pattern:** OVERHEATING

**Key Timestamps:**

| Event | Timestamp |
|-------|-----------|
| utility_fail | 2026-06-01T11:15:30 |
| coolant_normal_start | 44.8°C at 2026-06-01T11:17:00 |
| degraded_start | 2026-06-01T11:59:30 |
| temp_peak | 107.7°C at 2026-06-01T12:03:30 |
| shutdown | 2026-06-01T12:04:30 |

**Supporting Measurements:**

| Metric | Value |
|--------|-------|
| coolant_start_C | 44.8 |
| coolant_peak_C | 107.7 |
| oil_pressure_start_bar | 4.09 |
| oil_pressure_end_bar | 3.24 |
| oil_decline_bar | 0.85 |
| avg_load_kW | 192.4 |
| running_records | 48 |
| degraded_records | 5 |

**Observed Issue:**
Coolant temperature rose from 44.8°C to 107.7°C during ~48 minutes of generator operation at ~192 kW. Generator entered RUNNING_DEGRADED state at 2026-06-01T11:59:30 when coolant exceeded ~105°C (simulated threshold — DSE6120 actual setting UNVERIFIED). Oil pressure declined from 4.1 to 3.2 bar, correlating with rising temperature. Engine shut down due to over-temperature protection at 2026-06-01T12:04:30.

**Possible Causes:**
1. Blocked or fouled radiator reducing heat dissipation. 2. Low coolant level or coolant degradation (old coolant). 3. Thermostat stuck closed preventing coolant circulation. 4. Water pump failure or reduced impeller efficiency. 5. Sustained high load (~70%) combined with high ambient temperature. 6. Coolant hose restriction or collapsed hose. NOTE: These are possible causes, not confirmed diagnoses. DSE6120 alarm setpoints remain unverified.

**Missing Evidence:**
1. Ambient air temperature at generator location. 2. Coolant flow rate or pump output. 3. Radiator condition (fins, airflow path). 4. Thermostat position/operation. 5. Actual DSE6120 alarm threshold for coolant temperature. 6. Coolant level and recent coolant service date. 7. Engine room ventilation adequacy.

**Suggested Inspection / Maintenance Action:**
1. Inspect radiator for blockage, clean fins, verify airflow path. 2. Check coolant level and quality; replace if degraded. 3. Test thermostat operation; replace if stuck. 4. Inspect water pump for wear or impeller damage. 5. Verify engine room ventilation is adequate for standby rating. 6. Obtain DSE6120 alarm setpoint configuration to confirm thresholds. 7. Review load profile — 70% sustained load may require derating assessment.

**Priority:** HIGH

**Priority Justification:** Over-temperature shutdown caused total loss of generator backup power. If this recurs during a real utility outage, the facility has no backup. Thermal degradation risks engine damage (warped head, blown gasket). Must be resolved before next outage test.

---

### Unsuccessful ATS Transfer

**Classification:** CRITICAL — generator healthy but load not transferred

**Detection pattern:** ATS_TRANSFER_FAILURE

**Key Timestamps:**

| Event | Timestamp |
|-------|-----------|
| utility_fail | 2026-06-01T15:08:30 |
| gen_running | 2026-06-01T15:10:00 |
| ats_fail_first | 2026-06-01T15:10:00 |
| gen_stopped | 2026-06-01T15:20:00 |
| utility_restored | 2026-06-01T15:31:00 |

**Supporting Measurements:**

| Metric | Value |
|--------|-------|
| gen_voltage_avg_V | 400.5 |
| gen_freq_avg_Hz | 50.06 |
| no_load_records | 10 |
| failed_transfer_records | 11 |
| facility_dark_records | 15 |

**Observed Issue:**
OBSERVED FACT: Utility failed at 2026-06-01T15:08:30. Generator started successfully and produced nominal voltage (401V) and frequency (50.1Hz). ATS commanded source = GENERATOR but actual position reported UTILITY — transfer_confirmation = FAILED for 11 consecutive records. Generator ran with no load (RUNNING_NL, current=0) for 10 minutes before being commanded to stop for safety. BUILDING POWER STATUS: Cannot be confirmed without load-bus voltage data (not present in this dataset). The ATS position sensor reports UTILITY, and the generator current sensor reports 0A, which is consistent — but neither confirms whether the building had power from utility or was without power.

**Possible Causes:**
The following are possible causes, NOT confirmed diagnoses. The fault has NOT been attributed to mechanical failure:
1. SENSOR: ATS position sensor error — sensor may report UTILITY incorrectly while the switch actually transferred.
2. SENSOR: ATS position limit switch intermittent fault.
3. MEASUREMENT: Transfer-confirmation logic artefact — the DSE6120 confirmation input may have a transient or wiring issue.
4. CONTROL: ATS control circuit fault — relay, contactor coil, or actuator command not reaching the mechanism.
5. TOPOLOGY: Bypass path or dual-source configuration not modelled in this dataset — the facility may have a secondary transfer path.
6. SIMULATION: Data generation artefact — this is simulated data; the FAILED status may represent a modelling choice, not a real fault.
NOTE: Generator output was healthy (V, Hz normal), so any fault is in the ATS transfer path or its sensing, not the generator.

**Missing Evidence:**
1. Load-bus voltage — critical for confirming whether building had power during this period (NOT available in this dataset).
2. ATS position sensor raw signal — to verify if position reading is accurate or if sensor is faulty.
3. ATS contactor mechanical position — visual inspection needed.
4. ATS control circuit voltage and continuity.
5. Facility single-line diagram — to verify single-ATS topology assumption and rule out bypass paths.
6. ATS motor/actuator coil resistance.
7. Wiring continuity from DSE6120 to ATS.
8. ATS maintenance/inspection history (last serviced date).
9. ATS manufacturer model and specifications.
10. Environmental conditions (moisture, dust in ATS enclosure).

**Suggested Inspection / Maintenance Action:**
1. Verify topology — obtain facility single-line diagram to confirm single-ATS assumption and check for bypass paths.
2. Inspect ATS position sensor and limit switches — do NOT assume mechanical failure before ruling out sensor issues.
3. Test ATS control circuit voltage and relay operation.
4. Measure ATS motor/actuator coil resistance; replace if out of spec.
5. Inspect wiring between DSE6120 and ATS for corrosion or damage.
6. Manually exercise ATS transfer to verify mechanical freedom.
7. Install or verify load-bus voltage monitoring to confirm building power status during transfer events.
8. Schedule ATS manufacturer service if internal fault suspected.
9. Review ATS maintenance history — last service was radiator/ATS contact inspection (see maintenance_history.csv).

**Priority:** CRITICAL

**Priority Justification:** Generator was fully functional but ATS transfer was not confirmed — the generator was not feeding the building load (current=0A). Whether the building had power from utility during this period cannot be confirmed without load-bus voltage data. However, the ATS transfer-confirmation failure itself is critical: if the utility was truly failed and the ATS could not transfer, the standby system's core function is compromised. ATS transfer reliability is the single most critical function of a standby system. Must be investigated and resolved before returning to service.

---

## Generator Readiness Assessment

**Status: NOT READY FOR SERVICE**

- 1 CRITICAL issue(s) must be resolved immediately:
  - Unsuccessful ATS Transfer: OBSERVED FACT: Utility failed at 2026-06-01T15:08:30. Generator started successf...
- 1 HIGH priority issue(s) require attention:
  - Rising Coolant Temperature: Coolant temperature rose from 44.8°C to 107.7°C during ~48 minutes of generator ...

---
*Report generated by GenBuddy Autonomous Fault Investigation Workflow.*