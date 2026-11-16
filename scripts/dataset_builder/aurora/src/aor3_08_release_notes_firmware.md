# Release Notes and Firmware Compatibility

Document ref: aor3_08_release_notes_firmware | Revision: Rev 3.2 (2026-03) | Classification: Fictional training material

## 1. Purpose and scope

This document lists the firmware releases that apply to the Aurora Open Rack AOR-3 in Revision 3.2. It covers three firmware families: the BIOS on each compute sled CS-2U, the BMC (OpenBMC) on each compute sled, and the switch operating system (AOS) on the Top-of-Rack Switch AS-100G. It gives the release notes for each version, the firmware compatibility matrix, the upgrade order, the rollback procedure, the known issues that are tied to fault codes, and a set of compatibility questions and answers.

The compatibility matrix in Section 4 is the only authority for which firmware combinations are supported. A sled or switch running a combination that is not listed in the matrix is outside the supported configuration, even if the hardware powers up and the LEDs look normal.

The release notes in Section 3 are limited to the changes and effects recorded in the engineering specification for this revision. This revision does not include a full changelog. Where a version has no recorded change, the entry says so.

Read this document together with *Preventive Maintenance and Safety Manual*, which sets the safety rules and the escalation levels for firmware work, and with *BMC, Redfish and CLI Operations Guide*, which lists the commands used to export the System Event Log and reset the BMC.

## 2. Firmware releases in this revision

Three BIOS builds, three BMC builds and three switch OS builds are covered by this revision. The table below gives the status of each build in the context of this revision. The status describes how the build is used. It does not describe its quality.

| Component | Build | Status in Rev 3.2 |
|---|---|---|
| BIOS | 1.8.0 | Legacy. Listed in the matrix, missing the watchdog fix for fault 0x9A05. |
| BIOS | 1.9.2 | Recommended baseline for AOR-3 Rev 3.2. |
| BIOS | 2.0.0 | Supported with BMC 2.14.3 and AOS 5.3. Adds DDR5 retraining improvements. |
| BMC (OpenBMC) | 2.12.x | Legacy. Paired with BIOS 1.8.0 only. |
| BMC (OpenBMC) | 2.13.x | Not supported with BIOS 2.0.0. Triggers fault 0x9A10. |
| BMC (OpenBMC) | 2.14.3 | Target release for the fault 0x9A05 remediation. Paired with BIOS 1.9.2 and BIOS 2.0.0. |
| Switch OS (AOS) | 5.1 | Paired with BIOS 1.8.0 and BMC 2.12.x only. |
| Switch OS (AOS) | 5.2 | Paired with BIOS 1.9.2 and BMC 2.14.3. |
| Switch OS (AOS) | 5.3 | Paired with BIOS 2.0.0 and BMC 2.14.3. |

The BMC on every compute sled is the OpenBMC 2.14 platform described in the component specification. The 2.14.3 build is the BMC release that the matrix pairs with the baseline BIOS, and it is the release named in the remediation for fault 0x9A05_BMC_WDT_RESET.

> **NOTE:** The BMC 2.13.x and BMC 2.12.x families are identified by their minor version only in this revision. Use the full build string from the release package when you record a version, and compare the full string with the matrix.

## 3. Release notes by version

The notes below follow the component order used in Section 2. Each note gives the pairing, the status, the recorded change or effect, and any fault code linked to the version.

### 3.1 BIOS 1.8.0

- **Pairing:** BMC 2.12.x and AOS 5.1.
- **Status:** Legacy.
- **Recorded change:** The build is missing the watchdog fix associated with fault 0x9A05_BMC_WDT_RESET. A sled on this build can see the BMC reboot itself after the watchdog timer expires.
- **Action:** Plan the move to a later row of the matrix. Use the upgrade procedure in Section 5. Do not install this build on any new sled.

### 3.2 BIOS 1.9.2

- **Pairing:** BMC 2.14.3 and AOS 5.2.
- **Status:** Recommended baseline for AOR-3 Rev 3.2.
- **Recorded change:** This is the baseline build for the revision. The specification records no change for this build beyond its matrix pairing.
- **Action:** Use this build as the target for any sled that needs a supported configuration without moving to BIOS 2.0.0.

### 3.3 BIOS 2.0.0

- **Pairing:** BMC 2.14.3 and AOS 5.3. The pairing with BMC 2.13.x is not supported.
- **Status:** Supported with the 2.14.3 BMC and AOS 5.3.
- **Recorded change:** Adds DDR5 retraining improvements. The improvement is linked to fault 0x10F0_DIMM_TRAINING_FAIL, which is raised when memory training fails for DIMM_A7 at boot.
- **Action:** Do not install BIOS 2.0.0 with any BMC build other than 2.14.3. A BIOS 2.0.0 sled on BMC 2.13.x raises fault 0x9A10_BMC_FW_MISMATCH.

### 3.4 BMC 2.12.x

- **Pairing:** BIOS 1.8.0 and AOS 5.1.
- **Status:** Legacy.
- **Recorded change:** This build is the BMC side of the legacy row, which the matrix marks as missing the watchdog fix tied to fault 0x9A05_BMC_WDT_RESET. The fault remediation names BMC 2.14.3 or later as the target.
- **Action:** Move the sled to BMC 2.14.3 or later, following the upgrade order in Section 5.

### 3.5 BMC 2.13.x

- **Pairing:** None in a supported configuration. The matrix lists this build only with BIOS 2.0.0, and that pairing is not supported.
- **Status:** Not supported with BIOS 2.0.0.
- **Recorded change:** A BIOS 2.0.0 sled running a 2.13.x BMC raises fault 0x9A10_BMC_FW_MISMATCH with the LED solid green on the PWR indicator.
- **Action:** Do not install this build on a sled that runs BIOS 2.0.0. If you find this build on such a sled, flash the matching BMC build from the matrix, which is 2.14.3 for BIOS 2.0.0.

### 3.6 BMC 2.14.3

- **Pairing:** BIOS 1.9.2 and AOS 5.2, or BIOS 2.0.0 and AOS 5.3.
- **Status:** Baseline BMC release for Rev 3.2.
- **Recorded change:** The remediation for fault 0x9A05_BMC_WDT_RESET names BMC 2.14.3 or later as the target. This release is the baseline BMC of the matrix.
- **Action:** Use 2.14.3 as the target BMC release for every sled. Do not downgrade a sled from this release to an earlier BMC build without the Engineer's approval.

### 3.7 Switch OS (AOS) 5.1, 5.2 and 5.3

- **AOS 5.1:** Paired with BIOS 1.8.0 and BMC 2.12.x. Legacy row of the matrix.
- **AOS 5.2:** Paired with BIOS 1.9.2 and BMC 2.14.3. Baseline row of the matrix.
- **AOS 5.3:** Paired with BIOS 2.0.0 and BMC 2.14.3. The row that carries the BIOS 2.0.0 pairing.
- **Recorded change:** The specification records no change in the switch OS itself beyond the pairing in the matrix. Check the switch OS release notes for any change that is not described here.
- **Action:** Keep the switch OS on the same row of the matrix as the sleds it serves. The upgrade and rollback steps in this document include the switch OS in the correct position.

## 4. Firmware compatibility matrix

The matrix below lists every supported and unsupported combination for this revision. Each row is a complete set: a BIOS build, a BMC build and a switch OS build that are used together. A combination that is not listed is not supported.

| BIOS | BMC | Switch OS (AOS) | Notes |
|---|---|---|---|
| BIOS 1.8.0 | BMC 2.12.x | AOS 5.1 | Legacy. Missing watchdog fix (0x9A05). |
| BIOS 1.9.2 | BMC 2.14.3 | AOS 5.2 | Recommended baseline for AOR-3 Rev 3.2. |
| BIOS 2.0.0 | BMC 2.14.3 | AOS 5.3 | Adds DDR5 retraining improvements (0x10F0). |
| BIOS 2.0.0 | BMC 2.13.x | AOS 5.3 | NOT supported: triggers 0x9A10_BMC_FW_MISMATCH. |

Three points apply when you read the matrix.

1. The first three rows are the supported configurations. The fourth row is a known bad configuration. It is shown so that you can recognise it in the field.
2. A sled that is in the middle of an upgrade can be in a combination that is not on the matrix. Section 5 describes the expected states during an upgrade and the fault that appears in them.
3. The matrix does not give a release date for any build. Use the release package for the date and the change log of each build.

> **WARNING:** Do not mix builds from different rows. For example, do not install BIOS 2.0.0 on a sled that runs BMC 2.12.x or BMC 2.13.x, and do not pair a sled on BIOS 1.9.2 with switch OS AOS 5.3 unless the Engineer has approved the mixed state in writing.

## 5. Upgrade order procedure

Firmware upgrades follow a fixed order: BIOS first, then BMC, then the switch OS. The BMC checks its build against the installed BIOS. Updating the BIOS first lets you confirm the BIOS level, then bring the BMC to the build that matches it. The switch OS is updated last, after the sleds are on their target row.

The upgrade is performed on one row transition at a time. Identify the current row and the target row in Section 4 before you start. The most common transitions are:

- Row 1 to row 2, from BIOS 1.8.0 and BMC 2.12.x to BIOS 1.9.2 and BMC 2.14.3. This is the watchdog fix transition.
- Row 2 to row 3, from BIOS 1.9.2 and BMC 2.14.3 to BIOS 2.0.0 and BMC 2.14.3. The BMC does not change in this transition.

### 5.1 Before you start

1. Obtain approval for the maintenance window from the Engineer. Firmware work is an Engineer-level task under the escalation levels in *Preventive Maintenance and Safety Manual*.
2. Confirm the workload owner has drained or moved the workloads from the sled, or has agreed that the sled may be taken out of service.
3. Export the System Event Log from the sled with the BMC CLI. Save the file with the sled identifier and the date in its name.
4. Record the current BIOS, BMC and switch OS builds for the sled and the switch.
5. Check the BMC LED. It must blink blue at the healthy rate. If it is solid blue, a firmware update may already be in progress. Do not start a new update until the first update is complete.
6. Do not start the upgrade on a sled that has an open Critical fault. Resolve the Critical fault first, using *Fault Code Reference and Troubleshooting Flowcharts*.

### 5.2 Upgrade steps

| Step | Component | Action | Check before the next step |
|---|---|---|---|
| 1 | BIOS | Install the BIOS build of the target row. | BIOS build reads the target value. |
| 2 | SEL | Export the SEL after the BIOS update. | A fault 0x9A10_BMC_FW_MISMATCH entry is expected if the BMC does not yet match the new BIOS. Record it. Do not start fault remediation at this step. |
| 3 | BMC | Install the BMC build of the target row. | BMC LED solid blue during the update, then blinking blue when the BMC is healthy. |
| 4 | BMC | If the new BMC build requires a restart to activate, restart it with the warm reset. | BMC returns to a healthy blinking blue state. Use the cold reset only if the warm reset does not recover the BMC, as described in *BMC, Redfish and CLI Operations Guide*. |
| 5 | SEL | Export the SEL after the BMC update. | No new 0x9A10_BMC_FW_MISMATCH entry. If the entry persists, stop and escalate to the Engineer. |
| 6 | Switch OS | Install the AOS build of the target row on the top-of-rack switch AS-100G. | Management access to MGMT0 is working on MGMT_VLAN_102. |
| 7 | Sled | Return the sled to service and confirm the LEDs. | See Section 5.3. |

> **WARNING:** When the BMC LED is solid blue, the BMC is booting or a firmware update is in progress. Do not power cycle the sled during this state.

> **NOTE:** The 0x9A10 entry in step 2 is expected when the BMC has not yet been updated to match the new BIOS. It is not a reason to change the BIOS back. Complete step 3 and confirm in step 5 that the entry has not returned.

### 5.3 Verification after the upgrade

| Check | Expected result |
|---|---|
| Installed builds | Match the target row of the matrix for BIOS, BMC and switch OS. |
| PWR LED | Solid green, meaning normal operation. |
| BMC LED | Blinking blue at the healthy rate. |
| NET LED | Solid green on each 100 GbE link. |
| SEL | No new entry for 0x9A05_BMC_WDT_RESET or 0x9A10_BMC_FW_MISMATCH. |
| Switch management | MGMT0 reachable on MGMT_VLAN_102. |

Record the verification results in the maintenance record. If any check does not match, do not return the sled to service. Escalate to the Engineer level.

## 6. Rollback

Rollback returns a sled or the switch to an earlier row of the matrix. A rollback is an Engineer-level decision. It must be recorded with the reason, the target row and the approval.

The rollback rules are:

1. Roll back only to a row that is listed in Section 4.
2. Reverse the upgrade order. The order is switch OS first, then BMC, then BIOS. Skip any component that does not change.
3. BMC 2.14.3 is paired with both BIOS 1.9.2 and BIOS 2.0.0. When you move between those two rows, the BMC normally stays at 2.14.3.
4. Do not roll back to row 1 (BIOS 1.8.0, BMC 2.12.x, AOS 5.1) without the Engineer's approval. Row 1 is the row that lacks the watchdog fix associated with fault 0x9A05.
5. BMC 2.13.x is not a rollback target. The matrix lists it only with BIOS 2.0.0, and that pairing is not supported.

### 6.1 Rollback paths

| From | To | Order of steps | Notes |
|---|---|---|---|
| Row 3: BIOS 2.0.0, BMC 2.14.3, AOS 5.3 | Row 2: BIOS 1.9.2, BMC 2.14.3, AOS 5.2 | (1) AOS 5.3 to 5.2. (2) BIOS 2.0.0 to 1.9.2. BMC stays at 2.14.3. | Most common rollback. Export the SEL before the change. If fault 0x10F0 returns on DIMM_A7 after the rollback, follow the memory procedure in *Preventive Maintenance and Safety Manual*. |
| Row 2: BIOS 1.9.2, BMC 2.14.3, AOS 5.2 | Row 1: BIOS 1.8.0, BMC 2.12.x, AOS 5.1 | (1) AOS 5.2 to 5.1. (2) BMC 2.14.3 to 2.12.x. (3) BIOS 1.9.2 to 1.8.0. | Not recommended. Requires Engineer approval. The BMC step creates a state that is not on the matrix, and fault 0x9A10 is expected until step (3) is complete. Fault 0x9A05 is the known issue for this row. |
| Row 3 to Row 1 | Row 1 | Do not perform in one step. Go to Row 2 first, then to Row 1 as above. | Requires Engineer approval. |

> **CAUTION:** Rolling back to row 1 re-introduces the watchdog exposure that fault 0x9A05_BMC_WDT_RESET describes. Record the approval, the reason and the expected SEL entries before you start the rollback.

Before any rollback, export the SEL, record the current builds and record the reason for the change. After the rollback, run the verification checks in Section 5.3 for the target row.

## 7. Known issues

Three known issues in this revision are tied to fault codes. Each one lists the affected builds, the fault that is raised, the status and the recommended action. The fault codes are written exactly as they appear in the Fault Code Reference.

| Known issue | Fault code | Severity | Affected builds | Action |
|---|---|---|---|---|
| BMC watchdog resets | 0x9A05_BMC_WDT_RESET | Major | BIOS 1.8.0 and BMC 2.12.x | Upgrade the BMC to 2.14.3 or later. Export the SEL first. |
| BMC firmware mismatch | 0x9A10_BMC_FW_MISMATCH | Warning | BIOS 2.0.0 with BMC 2.13.x | Flash the matching BMC build from the matrix, 2.14.3 for BIOS 2.0.0. |
| DIMM training failure | 0x10F0_DIMM_TRAINING_FAIL | Major | Sleds on BIOS builds before 2.0.0, since BIOS 2.0.0 adds the retraining improvement | Reseat DIMM_A7. Check the BIOS level for the retraining improvement in BIOS 2.0.0. |

### 7.1 Fault 0x9A05_BMC_WDT_RESET

The BMC watchdog timer expired and the BMC rebooted itself. The fault is Major and the BMC LED is solid blue while the BMC is recovering. The SEL event is SEL-0310.

The affected configuration is BIOS 1.8.0 with BMC 2.12.x, which has no watchdog fix. The remediation is to collect the SEL with the BMC CLI and upgrade the BMC firmware to 2.14.3 or later.

Use Section 5 for the upgrade. If the sled is on BIOS 1.8.0, the target row is row 2 (BIOS 1.9.2, BMC 2.14.3, AOS 5.2). The BIOS step therefore comes first, then the BMC step, then the switch OS step. Expect a fault 0x9A10 entry between the BIOS and BMC steps.

### 7.2 Fault 0x9A10_BMC_FW_MISMATCH

The BMC firmware is not in the compatibility matrix for the installed BIOS. The fault is a Warning. The PWR LED remains solid green, so the fault is found in the System Event Log, not on the front panel. The SEL event is SEL-0311.

The known configuration that raises this fault is BIOS 2.0.0 with BMC 2.13.x. The remediation is to flash the BMC build that the matrix pairs with the installed BIOS. For BIOS 2.0.0 that is BMC 2.14.3.

A fault 0x9A10 entry that appears during an upgrade, between the BIOS step and the BMC step, is expected and is covered in Section 5.2. A fault 0x9A10 entry that persists after the matching BMC build is installed is not expected. Stop and escalate to the Engineer level.

### 7.3 Fault 0x10F0_DIMM_TRAINING_FAIL

Memory training failed for DIMM_A7 at boot. The fault is Major and the PWR LED blinks amber. The SEL event is SEL-0403.

The BIOS 2.0.0 build adds DDR5 retraining improvements, which are linked to this fault. A sled on an earlier BIOS build should be evaluated for the move to BIOS 2.0.0, with BMC 2.14.3 and AOS 5.3, as a planned change.

A BIOS upgrade does not replace the hardware step. The remediation for the fault still requires the DIMM_A7 slot to be reseated first. If the failure persists, test the slot with a known-good DIMM, as described in *Preventive Maintenance and Safety Manual*. The BIOS decision belongs to the Engineer level.

## Frequently asked questions

**Q1. Can I run BIOS 2.0.0 with BMC 2.13.x?**

No. The combination of BIOS 2.0.0 and BMC 2.13.x is marked NOT supported in the compatibility matrix. It triggers fault 0x9A10_BMC_FW_MISMATCH. Install BMC 2.14.3 with BIOS 2.0.0 instead.

**Q2. What is the recommended firmware set for AOR-3 Rev 3.2?**

The recommended baseline is BIOS 1.9.2, BMC 2.14.3 and AOS 5.2. This is the second row of the compatibility matrix and it is the recommended baseline for this revision.

**Q3. Is BIOS 1.8.0 still supported?**

BIOS 1.8.0 is listed in the matrix as a legacy row, paired with BMC 2.12.x and AOS 5.1. It is missing the watchdog fix associated with fault 0x9A05. It is not the recommended baseline, and a sled on this build should be moved to a later row as a planned change.

**Q4. Why is the BIOS updated before the BMC?**

The upgrade order is BIOS first, then BMC, then the switch OS. The BMC checks its build against the installed BIOS, so the BIOS is set first and the BMC is then brought to the matching build. You may see fault 0x9A10 between the BIOS and BMC steps. That entry is expected in that window and must be checked again after the BMC step.

**Q5. I see fault 0x9A10 after the BMC update. What do I do?**

Check that the installed BMC build is the one the matrix pairs with the installed BIOS. For BIOS 2.0.0, that is BMC 2.14.3. If the build is correct and the fault remains, stop, do not return the sled to service, and escalate to the Engineer level.

**Q6. Which BMC release fixes the watchdog reset?**

The remediation for fault 0x9A05_BMC_WDT_RESET names BMC 2.14.3 or later as the target. The 2.12.x family is the legacy row that the matrix marks as missing the watchdog fix.

**Q7. Does fault 0x10F0 mean I need to upgrade the BIOS?**

Not in every case. Fault 0x10F0_DIMM_TRAINING_FAIL is remediated first by reseating DIMM_A7 and, if the failure persists, testing the slot with a known-good DIMM. BIOS 2.0.0 adds DDR5 retraining improvements linked to this fault. Whether to move a sled to BIOS 2.0.0 is an Engineer decision.

**Q8. Do I have to change the switch OS when I change the sled firmware?**

Yes, when the sled and the switch are being moved to a new row. Each row of the matrix pairs a BIOS build, a BMC build and a switch OS build. Upgrade the switch OS last, after the sleds are on the target row, and confirm management access to MGMT0 on MGMT_VLAN_102 afterwards.
