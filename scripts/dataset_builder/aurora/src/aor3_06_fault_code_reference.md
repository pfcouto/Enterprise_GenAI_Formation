# Fault Code Reference and Troubleshooting Flowcharts

Document ref: aor3_06_fault_code_reference | Revision: Rev 3.2 (2026-03) | Classification: Fictional training material

## 1. Using this reference

This reference defines all 30 fault codes that the Aurora Open Rack AOR-3 can raise. For each code it gives the subsystem, severity, front-panel LED state, root cause, remediation and System Event Log (SEL) event number. Section 2 is the master table. Sections 3 and 4 explain the codes in prose, by subsystem and by near-duplicate pair. Section 5 is the troubleshooting flowchart for a blinking amber PWR LED.

Export the SEL before you use this reference. The commands are in *BMC, Redfish and CLI Operations Guide*. The physical procedures named in each remediation are in *Power Shelf PS-3000 Service Manual*, *Thermal and Cooling Manual*, *Top-of-Rack Switch AS-100G Manual* and *Preventive Maintenance and Safety Manual*.

### 1.1 Code format and matching

Each code has a hexadecimal identifier, an underscore and an uppercase suffix, for example `0x4A7B_VRM_OVERVOLT`. Match on the complete string, never on the prefix or the suffix alone. Several codes share a prefix or a word and mean different things (section 4). The SEL event number, such as `SEL-0101`, identifies a log entry. It does not describe the fault.

### 1.2 Severity levels

- **Critical.** The sled is at risk of immediate damage or shutdown. Act first.
- **Major.** A subsystem has failed or lost redundancy. Act during the current service visit.
- **Warning.** A value is outside its normal range. Correct the cause or schedule the correction.
- **Minor.** The condition is recorded for trend analysis. Log it and monitor it.

### 1.3 Front-panel LED states

The LED column names the indicator and its state, for example `Solid red PWR` or `NET LED solid amber`. Look at Figure F2 to match the LED on a sled to the table entry.

![Figure F2: Front-panel LED legend](figures/F2_front_panel_led_legend.png)

*Figure F2: Front-panel LED legend: PWR, NET, BMC and ID LEDs*

Blinking amber on PWR covers ten codes, so the LED colour alone never identifies a fault. Section 5 explains how to narrow it down.

## 2. Master fault code table

The table lists all 30 codes in catalogue order. Remediation text is given as it appears in the catalogue.

| Code | Subsystem | Severity | LED state | Root cause | Remediation | SEL event |
|---|---|---|---|---|---|---|
| `0x4A7B_VRM_OVERVOLT` | Power VRM | Critical | Solid red PWR | Input voltage exceeded the 54.2 V cutoff threshold on the 48 V busbar. | Engage the secondary backup PSU; replace the PDB fuse (F2). Do not re-energise before measuring the busbar. | SEL-0101 |
| `0x4A7C_VRM_UNDERVOLT` | Power VRM | Major | Blinking amber PWR | Busbar voltage fell below the 40.5 V undervoltage threshold. | Check rectifier modules R1-R6 for a failed unit; reseat the module; verify AC feed on phase L2. | SEL-0102 |
| `0x4A80_VRM_OVERCURRENT` | Power VRM | Critical | Solid red PWR | Sled PoL stage drew more than 120 A on the 12 V rail. | Remove the sled, inspect the PoL stage for a short, then replace the sled if the fault repeats. | SEL-0103 |
| `0x4B10_PSU_RECT_FAIL` | Power shelf | Major | Blinking amber PWR | A rectifier module reported an internal fault and dropped out of the N+1 set. | Hot-swap the failed rectifier (LED on the module is red). Rack stays up on the remaining 5 modules. | SEL-0110 |
| `0x4B22_PSU_AC_LOSS` | Power shelf | Critical | Solid red PWR | Loss of 3-phase AC mains on one or more phases. | Check the upstream breaker and PDU; confirm all three phases L1-L3 are present before restart. | SEL-0111 |
| `0x8F01_FAN_TACH_FAIL` | Thermal | Major | Blinking amber PWR | Tachometer signal lost on Fan Module #4 (below 600 RPM). | Inspect the fan cable seating; swap Fan Module 4 (FM4) using the hot-swap procedure. | SEL-0201 |
| `0x8F02_FAN_ALL_FAIL` | Thermal | Critical | Solid red PWR | Two or more fan modules report tachometer failure. | Gracefully shut down the sled within 5 minutes; replace both fan modules before restart. | SEL-0202 |
| `0x8F10_TEMP_WARN` | Thermal | Warning | Blinking amber PWR | CPU or inlet temperature above 75 C. | Fans are forced to 100 % and the CPU is throttled. Check airflow blockage, blanking panels and ambient temperature. | SEL-0210 |
| `0x8F11_TEMP_CRIT` | Thermal | Critical | Solid red PWR | CPU temperature above 90 C; the BMC starts an emergency shutdown. | Let the sled cool for 10 minutes; verify fan wall FW-6 and cold-aisle temperature before restart. | SEL-0211 |
| `0x8F20_AIRFLOW_BLOCK` | Thermal | Warning | Blinking amber PWR | Pressure sensor shows restricted airflow across the sled. | Install missing blanking panels in empty U positions; clear obstructions in front of the sled. | SEL-0212 |
| `0x99A0_PSU_COMM_LOST` | PMBus | Major | BMC LED off | I2C communication timeout on PMBus address 0x03 between BMC and power shelf. | Reset the BMC with the OpenBMC CLI: bmc-reset --warm. If it repeats, replace the PMBus ribbon cable. | SEL-0301 |
| `0x99A1_PMBUS_CRC_ERR` | PMBus | Minor | Solid green PWR | Repeated CRC errors on PMBus frames from rectifier R3. | Log and monitor; reseat rectifier R3 during the next maintenance window. | SEL-0302 |
| `0x9A05_BMC_WDT_RESET` | BMC | Major | Solid blue BMC | BMC watchdog timer expired and the BMC rebooted itself. | Collect the SEL with bmc-cli sel export; upgrade BMC firmware to 2.14.3 or later. | SEL-0310 |
| `0x9A10_BMC_FW_MISMATCH` | BMC | Warning | Solid green PWR | BMC firmware is not in the compatibility matrix for the installed BIOS. | Flash the matching BMC build listed in the firmware compatibility matrix (Release Notes). | SEL-0311 |
| `0x10E4_ECC_MULTI_BIT` | DDR5 Memory | Critical | Solid red PWR | Uncorrectable multi-bit parity failure on DIMM_A2. | Halt the node; replace the DIMM in slot A2 immediately. | SEL-0401 |
| `0x10E5_ECC_SINGLE_BIT` | DDR5 Memory | Warning | Solid green PWR | Correctable single-bit errors on DIMM_B5 exceeded 24 per hour. | Schedule DIMM_B5 replacement; no immediate downtime required. | SEL-0402 |
| `0x10F0_DIMM_TRAINING_FAIL` | DDR5 Memory | Major | Blinking amber PWR | Memory training failed for DIMM_A7 at boot. | Reseat DIMM_A7; if the failure persists, test the slot with a known-good DIMM. | SEL-0403 |
| `0x2B30_NVME_SMART_WARN` | Storage | Warning | Solid green PWR | NVMe bay 1 reports less than 10 % endurance remaining. | Order a replacement drive; migrate data during the next window. | SEL-0501 |
| `0x2B31_NVME_LINK_DOWN` | Storage | Major | Blinking amber PWR | PCIe link to NVMe bay 2 failed to train. | Reseat the drive; test with a different NVMe bay; replace the backplane if both fail. | SEL-0502 |
| `0xC029_ETH_PHY_LINKDN` | Network PHY | Major | NET LED off | Signal integrity loss on port QSFP28_12. | Clean the optical transceiver end-face; re-seat the fiber. | SEL-0601 |
| `0xC02A_ETH_PHY_DEGRADED` | Network PHY | Warning | NET LED solid amber | Port QSFP28_21 negotiated 25 GbE instead of 100 GbE. | Replace the DAC cable; verify the transceiver is rated for 100G. | SEL-0602 |
| `0xC040_MGMT_VLAN_MISMATCH` | Network PHY | Minor | Solid green PWR | Management traffic seen outside MGMT_VLAN_102. | Reconfigure the switch port to access VLAN 102 on MGMT0; check the trunk allowed list. | SEL-0610 |
| `0xC055_SWITCH_ASIC_TEMP` | Network PHY | Major | Blinking amber PWR | Switch ASIC TS-3200 junction temperature above 95 C. | Check switch fan trays and airflow direction (front-to-back); replace fan tray if needed. | SEL-0611 |
| `0x7D01_PDB_FUSE_BLOWN` | Power VRM | Major | Solid red PWR | Power distribution board fuse F2 is open. | Replace fuse F2 (30 A, 80 V DC rated) after finding the cause of the over-current. | SEL-0120 |
| `0x7D02_BUSBAR_RIPPLE` | Power VRM | Warning | Solid green PWR | Busbar ripple exceeded 50 mV peak-to-peak. | Inspect rectifier output capacitors and busbar connections for corrosion. | SEL-0121 |
| `0x6E01_SENSOR_STALE` | BMC | Minor | Solid green PWR | A sensor reading has not updated for more than 10 seconds. | Restart the sensor daemon: bmc-cli service restart sensord. | SEL-0320 |
| `0x6E10_CHASSIS_INTRUSION` | Security | Warning | Solid white ID | Chassis intrusion switch opened without a service ticket. | Verify the maintenance ticket; reset the intrusion latch with bmc-cli chassis clear-intrusion. | SEL-0701 |
| `0x6E20_TPM_ATTEST_FAIL` | Security | Major | Blinking amber PWR | TPM measurement differs from the golden attestation value. | Quarantine the sled, re-image firmware, and re-enroll the TPM attestation key. | SEL-0702 |
| `0x5F01_COOLANT_LEAK` | Liquid cooling | Critical | Solid red PWR | Rear-door heat exchanger leak sensor wet (optional liquid-cooling kit only). | Close the manual valves, power down the affected sleds, call the facility team. | SEL-0801 |
| `0x5F02_COOLANT_FLOW_LOW` | Liquid cooling | Warning | Blinking amber PWR | Coolant flow below 8 L/min (optional liquid-cooling kit only). | Check pump status and quick-disconnect couplings. | SEL-0802 |

## 3. Subsystem reference

The 30 codes group into ten subsystems. Use the master table for the exact text of a code and this section for context.

### 3.1 Power VRM

This group covers the 48 V busbar, the power distribution board and the 12 V point-of-load stage. It holds `0x4A7B_VRM_OVERVOLT`, `0x4A7C_VRM_UNDERVOLT`, `0x4A80_VRM_OVERCURRENT`, `0x7D01_PDB_FUSE_BLOWN` and `0x7D02_BUSBAR_RIPPLE`. The busbar is judged against the power shelf limits: 48 V nominal, a 44.0-52.0 V operating range, a 54.2 V overvoltage cutoff and a 40.5 V undervoltage cutoff. Overvoltage cuts power immediately. Undervoltage points first to the rectifiers. Fuse F2 is a protective result, so find the cause of the over-current before you replace it.

> **WARNING:** The 48 V busbar can deliver more than 300 A. Apply lock-out/tag-out to the AC feeder before you touch any rectifier connection, and wear insulated gloves rated 1000 V.

### 3.2 Power shelf

The PS-3000 converts 3-phase 400 V AC into the busbar with six 3 kW rectifiers in an N+1 arrangement. Five modules carry the load and one is spare. `0x4B10_PSU_RECT_FAIL` means one module has left the set. The rack stays powered with less margin, so replace the module at the next opportunity. `0x4B22_PSU_AC_LOSS` is critical. Restart only when phases L1-L3 are all present.

### 3.3 Thermal

This group covers fans and temperatures: `0x8F01_FAN_TACH_FAIL`, `0x8F02_FAN_ALL_FAIL`, `0x8F10_TEMP_WARN`, `0x8F11_TEMP_CRIT` and `0x8F20_AIRFLOW_BLOCK`. The fan wall FW-6 has six modules rated at 9000 RPM with a 2800 RPM minimum. One tachometer failure is major and the sled keeps running. Two or more are critical, and the sled must be shut down gracefully within 5 minutes. The 75 C CPU warning forces the fans to 100 % and throttles the CPU. The 90 C critical threshold starts the BMC emergency shutdown. Airflow blockage is detected by a pressure sensor and often underlies the other thermal codes.

### 3.4 PMBus

This group covers the link between the BMC and the rectifiers. `0x99A0_PSU_COMM_LOST` is a timeout on the link. `0x99A1_PMBUS_CRC_ERR` is a data-integrity error on frames from rectifier R3. Both are covered with their procedures in section 6.4 of *BMC, Redfish and CLI Operations Guide*.

### 3.5 BMC

This group covers the controller itself: `0x9A05_BMC_WDT_RESET`, `0x9A10_BMC_FW_MISMATCH` and `0x6E01_SENSOR_STALE`. A watchdog reset means the BMC rebooted itself, which is easy to miss when the sled looks normal. A firmware mismatch means the BMC build is unsupported with the installed BIOS. A stale sensor means a reading has stopped updating, so the BMC cannot judge it.

### 3.6 Security

This group holds `0x6E10_CHASSIS_INTRUSION` and `0x6E20_TPM_ATTEST_FAIL`. The intrusion code records a cover opened without a service ticket. Its LED is solid white, which is the locator colour, so do not read it as a locate request. The TPM code means the measured platform state differs from the golden attestation value. It is the only code here that calls for quarantine, and it should be handled as a security event.

### 3.7 DDR5 Memory

The 16 DDR5-5600 RDIMM slots are A1-A8 on CPU0 and B1-B8 on CPU1. `0x10E4_ECC_MULTI_BIT` is an uncorrectable error and is critical. `0x10E5_ECC_SINGLE_BIT` is a correctable error that becomes a warning above 24 events per hour on DIMM_B5. `0x10F0_DIMM_TRAINING_FAIL` is a boot-time training failure on DIMM_A7. BIOS 2.0.0 adds DDR5 retraining improvements that bear on this code.

### 3.8 Storage

The two NVMe bays are covered here. `0x2B30_NVME_SMART_WARN` is a wear warning on bay 1, raised when less than 10 % endurance remains. `0x2B31_NVME_LINK_DOWN` means the PCIe link to bay 2 failed to train. It is blinking amber and appears in the flowchart in section 5. Testing the drive in the other bay separates a drive fault from a backplane fault.

### 3.9 Network PHY

This group covers the optical and copper paths through the AS-100G QSFP28 ports. `0xC029_ETH_PHY_LINKDN` is signal loss on uplink port QSFP28_12. `0xC02A_ETH_PHY_DEGRADED` means server port QSFP28_21 negotiated 25 GbE. `0xC040_MGMT_VLAN_MISMATCH` means management traffic is seen outside MGMT_VLAN_102. `0xC055_SWITCH_ASIC_TEMP` means the TS-3200 junction is above 95 C. The thermal specification lists an 85 C ASIC warning threshold, but the fault is raised only at 95 C.

### 3.10 Liquid cooling

These codes apply only when the optional liquid-cooling kit is fitted. `0x5F01_COOLANT_LEAK` is critical. `0x5F02_COOLANT_FLOW_LOW` is raised below 8 L/min. A sled without the kit should never raise them. If one appears, check the sled configuration with an engineer before acting.

## 4. Near-duplicate code pairs

Three pairs of codes look alike on purpose: `0x4A7B_VRM_OVERVOLT` with `0x4A7C_VRM_UNDERVOLT`, `0x10E4_ECC_MULTI_BIT` with `0x10E5_ECC_SINGLE_BIT`, and `0x8F10_TEMP_WARN` with `0x8F11_TEMP_CRIT`. Each pair shares a prefix and a descriptive word, but the two codes mean different things.

### 4.1 Overvoltage versus undervoltage

`0x4A7B_VRM_OVERVOLT` means the busbar went above 54.2 V. It is critical, shows solid red and requires an immediate power cutoff. `0x4A7C_VRM_UNDERVOLT` means the busbar fell below 40.5 V. It is major, shows blinking amber and points to the rectifiers. The two codes differ by one hex digit, and the LED colour is the fastest discriminator on site.

### 4.2 Multi-bit versus single-bit ECC

`0x10E4_ECC_MULTI_BIT` is an uncorrectable failure on DIMM_A2. It is critical and the node must be halted. `0x10E5_ECC_SINGLE_BIT` is a correctable error on DIMM_B5 above 24 per hour. It is a warning, shows solid green, and the sled keeps running while the DIMM is scheduled for replacement. The slot letter also separates them: A-series slots sit on CPU0 and B-series slots on CPU1.

### 4.3 Temperature warning versus critical

`0x8F10_TEMP_WARN` is raised when the CPU or inlet is above 75 C. It shows blinking amber, and the fans go to 100 %. `0x8F11_TEMP_CRIT` is raised when the CPU is above 90 C. It shows solid red, and the BMC starts an emergency shutdown. The temperature threshold is the discriminator, so read the code on each SEL entry.

### 4.4 How to tell them apart

Use this checklist whenever a SEL entry shows one code of a pair and you need to rule out the other.

1. Read the complete hex code from the SEL entry, not the descriptive name. Compare the final hex digit: `4A7B` and `4A7C` differ only there.
2. Check the LED state. Critical codes in each pair show solid red. Warning and major codes show blinking amber or solid green.
3. For memory codes, read the DIMM label. A2 and B5 are on different sockets.
4. For thermal codes, read the CPU temperature. A reading between 75 C and 90 C is `0x8F10_TEMP_WARN`. A reading above 90 C is `0x8F11_TEMP_CRIT`.
5. Do not decide from the SEL event number. `SEL-0101` and `SEL-0102` are adjacent, and so are `SEL-0210` and `SEL-0211`. The number identifies the log entry only.

| Code | LED state | Severity | Trigger | Location | Primary action |
|---|---|---|---|---|---|
| `0x4A7B_VRM_OVERVOLT` | Solid red PWR | Critical | Busbar above 54.2 V | 48 V busbar | Engage backup PSU; replace fuse F2 after measuring the busbar |
| `0x4A7C_VRM_UNDERVOLT` | Blinking amber PWR | Major | Busbar below 40.5 V | Rectifiers R1-R6, AC phase L2 | Find and reseat the failed rectifier |
| `0x10E4_ECC_MULTI_BIT` | Solid red PWR | Critical | Uncorrectable multi-bit failure | DIMM_A2 on CPU0 | Halt the node and replace DIMM A2 |
| `0x10E5_ECC_SINGLE_BIT` | Solid green PWR | Warning | Correctable errors above 24 per hour | DIMM_B5 on CPU1 | Schedule DIMM_B5 replacement |
| `0x8F10_TEMP_WARN` | Blinking amber PWR | Warning | CPU or inlet above 75 C | Airflow and ambient | Check airflow and blanking panels |
| `0x8F11_TEMP_CRIT` | Solid red PWR | Critical | CPU above 90 C | CPU temperature | Let the sled cool 10 minutes; verify FW-6 before restart |

## 5. Troubleshooting flowchart: blinking amber PWR

### 5.1 When to use this flowchart

Use this flowchart when the PWR LED is blinking amber at 1 Hz and the SEL has been exported. It does not apply to solid red, solid green or off, which have their own codes in the subsystem sections. Blinking amber is the LED state for ten codes, and the flowchart narrows the cause from the code in the SEL.

### 5.2 Flowchart figure

Look at Figure F6 when the PWR LED is blinking amber and you need to choose a branch. The numbered text in section 5.3 gives the same decision tree in text form.

![Figure F6: Troubleshooting flowchart for a blinking amber PWR LED](figures/F6_troubleshooting_flowchart_amber.png)

*Figure F6: Troubleshooting flowchart for a blinking amber PWR LED*

### 5.3 Decision tree (numbered text version)

1. Confirm that the PWR LED is blinking amber at 1 Hz. If it is solid red, solid green or off, stop and use the subsystem section for the code in the SEL.
2. Check the BMC heartbeat LED. If it is solid blue, a boot or firmware update is running. Wait and do not reset. If it is off, the BMC is unresponsive. Follow section 4.3 of *BMC, Redfish and CLI Operations Guide*, and return here only when the BMC LED is blinking blue.
3. Export the SEL with `bmc-cli sel export`. Find the most recent entry that carries a fault code.
4. Check whether the code is one of the ten blinking-amber codes in section 5.4.
   - 4a. If it is, go to step 5.
   - 4b. If there is no matching code, read the CPU temperature. Above 75 C, the warning in the LED legend applies: go to branch T2. Otherwise, record the state and escalate to an engineer.
5. Select the branch for the code:
   - 5.1 Power: `0x4A7C_VRM_UNDERVOLT` goes to P1. `0x4B10_PSU_RECT_FAIL` goes to P2.
   - 5.2 Thermal: `0x8F01_FAN_TACH_FAIL` goes to T1. `0x8F10_TEMP_WARN` goes to T2. `0x8F20_AIRFLOW_BLOCK` goes to T3.
   - 5.3 Memory: `0x10F0_DIMM_TRAINING_FAIL` goes to M1.
   - 5.4 Storage: `0x2B31_NVME_LINK_DOWN` goes to S1.
   - 5.5 Network: `0xC055_SWITCH_ASIC_TEMP` goes to N1.
   - 5.6 Liquid cooling: `0x5F02_COOLANT_FLOW_LOW` goes to L1.
   - 5.7 Security: `0x6E20_TPM_ATTEST_FAIL` goes to X1.
6. Perform the branch actions in section 5.4, then go to step 7.
7. Verify the result. The PWR LED should show solid green, and a new export should not contain the code again. If the LED is still blinking amber or the code recurs, go to step 8.
8. Escalate to an engineer with the SEL export, the SEL event number and the list of actions already taken.

### 5.4 Branch actions

The table lists the ten blinking-amber codes with their branch and steps. Complete the steps in order and stop when the code clears.

| Branch | Code | Subsystem | Branch steps |
|---|---|---|---|
| P1 | `0x4A7C_VRM_UNDERVOLT` | Power VRM | Measure the busbar against 40.5 V under LOTO. Check R1-R6 for a failed unit and reseat it. Verify the AC feed on phase L2. |
| P2 | `0x4B10_PSU_RECT_FAIL` | Power shelf | Find the rectifier with a red module LED and hot-swap it. Confirm the rack runs on the remaining 5 modules, then on all 6. |
| T1 | `0x8F01_FAN_TACH_FAIL` | Thermal | Inspect the cable seating on Fan Module 4 and swap FM4 with the hot-swap procedure. If a second module fails, `0x8F02_FAN_ALL_FAIL` applies. |
| T2 | `0x8F10_TEMP_WARN` | Thermal | Check airflow blockage, blanking panels and ambient temperature. Watch for the CPU reaching 90 C, which becomes `0x8F11_TEMP_CRIT`. |
| T3 | `0x8F20_AIRFLOW_BLOCK` | Thermal | Install missing blanking panels in empty U positions. Clear obstructions in front of the sled. |
| M1 | `0x10F0_DIMM_TRAINING_FAIL` | DDR5 Memory | Reseat DIMM_A7. If the failure persists, test slot A7 with a known-good DIMM. |
| S1 | `0x2B31_NVME_LINK_DOWN` | Storage | Reseat the drive in bay 2 and test it in another bay. If both fail, replace the backplane. |
| N1 | `0xC055_SWITCH_ASIC_TEMP` | Network PHY | Check the switch fan trays and the front-to-back airflow. Replace the fan tray if needed. |
| L1 | `0x5F02_COOLANT_FLOW_LOW` | Liquid cooling | Check pump status and the quick-disconnect couplings. If the sled has no liquid-cooling kit, escalate. |
| X1 | `0x6E20_TPM_ATTEST_FAIL` | Security | Quarantine the sled, export the SEL, re-image firmware and re-enroll the TPM attestation key. Do not return the sled to service until the attestation matches. |

> **WARNING:** Branches P1 and P2 involve the 48 V busbar and rectifier connections. Apply lock-out/tag-out to the AC feeder first, as required by *Preventive Maintenance and Safety Manual*.

> **CAUTION:** Branch T2 runs with the fans at 100 % and the CPU throttled. Work through it promptly. If the CPU reaches 90 C, the code changes to `0x8F11_TEMP_CRIT` and the procedure in section 3.3 applies.

## 6. Frequently asked questions

**Q: The legend says blinking amber means a thermal warning. Do I start with the thermal branch?**

No. Ten codes share this LED state. Export the SEL first and follow the branch that matches the code. Use the thermal branch for `0x8F10_TEMP_WARN`, or when the SEL shows no code and the CPU is above 75 C.

**Q: The SEL shows `0x4A7B_VRM_OVERVOLT`, but the PWR LED is blinking amber. Which is right?**

The export can hold older entries as well as the current one. `0x4A7B_VRM_OVERVOLT` is associated with solid red, so it does not explain the current LED on its own. Find the newest entry and match it to the ten blinking-amber codes. If the newest entry is not one of them, escalate with the full export.

**Q: How do I tell `0x10E4_ECC_MULTI_BIT` from `0x10E5_ECC_SINGLE_BIT`?**

Read the full code and the DIMM label. The multi-bit code is critical, shows solid red and names DIMM_A2 on CPU0. The single-bit code is a warning, shows solid green and names DIMM_B5 on CPU1. Section 4.4 gives the full checklist.

**Q: Can a sled keep running with `0x8F01_FAN_TACH_FAIL`?**

Yes. One failed fan module is a major fault, and the sled keeps running while the module is replaced. If a second module fails, the code becomes `0x8F02_FAN_ALL_FAIL`, which is critical, and the sled must be shut down gracefully within 5 minutes.

**Q: What do I do after a `0x6E20_TPM_ATTEST_FAIL`?**

Quarantine the sled, export the SEL, re-image the firmware and re-enroll the TPM attestation key. Do not return the sled to service until the attestation value matches the golden value.

**Q: Why does `0xC055_SWITCH_ASIC_TEMP` appear against the PWR LED?**

The fault table lists this code against the PWR LED, but the reading comes from the switch ASIC TS-3200 in the AS-100G at U23, not from the compute sled. Check which device logged the entry. If the switch is the source, use branch N1 and consult *Top-of-Rack Switch AS-100G Manual*. If the sled logged it, escalate, because the source of the entry is then unclear.

Cross-reference: for reset, SEL export and intrusion procedures, see *BMC, Redfish and CLI Operations Guide*. For firmware builds, see *Release Notes and Firmware Compatibility*.
