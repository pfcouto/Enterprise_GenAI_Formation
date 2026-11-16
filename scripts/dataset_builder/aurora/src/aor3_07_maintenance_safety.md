# Preventive Maintenance and Safety Manual

Document ref: aor3_07_maintenance_safety | Revision: Rev 3.2 (2026-03) | Classification: Fictional training material

## 1. Scope and audience

This manual sets out the safety rules, handling limits, preventive maintenance schedule and escalation levels for the Aurora Open Rack AOR-3. It applies to every technician and engineer who opens, lifts, cables or services the Power Shelf PS-3000 (U20-U22), the compute sleds CS-2U (U02-U19), the fan wall FW-6 and the Top-of-Rack Switch AS-100G (U23). It also covers NVMe drives and DDR5 memory modules inside the compute sleds.

Read Section 2 before any physical work in the rack. The rules in Section 2 take precedence over any task step in this manual, in a ticket or in a verbal instruction. If a task cannot be performed within those rules, stop and escalate as described in Section 4.

For diagnosis of a specific fault code, use *Fault Code Reference and Troubleshooting Flowcharts*. For firmware changes, use *Release Notes and Firmware Compatibility*. For BMC commands, use *BMC, Redfish and CLI Operations Guide*. For thermal limits and fan behaviour, use *Thermal and Cooling Manual*.

## 2. Safety

### 2.1 Energy hazard of the 48 V busbar

The 48 V DC busbar is fed by the six hot-swappable rectifier modules R1 to R6 in the Power Shelf PS-3000, which convert 3-phase 400 V AC mains. The busbar is nominally 48 V and operates within 44.0 V to 52.0 V. It can deliver more than 300 A. Treat the busbar as a high-energy source at all times, including when the rack appears idle.

| Parameter | Value | Where it applies |
|---|---|---|
| Busbar nominal voltage | 48 V DC | Busbar, all sleds |
| Busbar operating range | 44.0 V to 52.0 V | Normal operation |
| Overvoltage cutoff | 54.2 V | Fault 0x4A7B_VRM_OVERVOLT |
| Undervoltage cutoff | 40.5 V | Fault 0x4A7C_VRM_UNDERVOLT |
| Shelf maximum output | 15 kW | Five active rectifiers of 3 kW each |
| Power distribution board fuse F2 | 30 A, 80 V DC rated | Fault 0x7D01_PDB_FUSE_BLOWN |

> **WARNING:** The busbar can deliver more than 300 A. A short between busbar conductors, or a metal tool that bridges two terminals, can cause arc flash and severe burns. Remove rings, watches and metal jewellery before you work near the busbar or the rectifier bays.

> **WARNING:** Do not re-energise the busbar after an overvoltage event (fault 0x4A7B_VRM_OVERVOLT) until you have measured the busbar voltage and confirmed that it is inside 44.0 V to 52.0 V. The remediation replaces fuse F2, which must not be done while the cause is still present.

### 2.2 Personal protective equipment

The minimum PPE for any work in the power or compute zones is insulated gloves rated 1000 V, safety glasses, and an ESD wrist strap for any work that exposes electronic assemblies, DIMMs or NVMe drives.

| Task | Insulated gloves (1000 V) | Safety glasses | ESD wrist strap |
|---|---|---|---|
| Visual LED and cable inspection | No | Yes | No |
| Fan module swap (FM1-FM6) | No | Yes | Yes |
| Rectifier module hot swap (R1-R6) | Yes | Yes | Yes |
| Work at busbar or rectifier connections | Yes | Yes | Yes |
| Sled removal, DIMM or NVMe work | No | Yes | Yes |
| Optical transceiver cleaning | No | Yes | Yes |

### 2.3 Lock-out/tag-out

Lock-out/tag-out (LOTO) of the AC feeder is mandatory before you touch rectifier connections. If your hands or tools will be near a rectifier connection, the AC feeder that supplies that rectifier must be locked out first.

1. Tell the on-call shift lead and the rack owner which rack, shelf and feeder you are isolating.
2. Identify the AC feeder that supplies the Power Shelf PS-3000, including the upstream breaker and the PDU.
3. Open the feeder breaker. Apply your personal lock and a tag showing your name, the date and the reason.
4. Verify that 3-phase AC is absent on all three phases, L1, L2 and L3, before you touch any connection.
5. Measure the busbar before you touch any busbar connection.
6. When the work is complete and the tools are clear, remove only your own lock.
7. Record the lock ID, the start and end times, and the names of everyone who worked under the LOTO.

> **WARNING:** Lock-out of the AC feeder does not make the busbar safe by itself. Treat any busbar reading outside 44.0 V to 52.0 V as a fault and stop work.

Hot-swap of a rectifier module is a module-level action, and the procedure in *Power Shelf PS-3000 Service Manual* governs it. If there is any doubt about whether a connection will be touched, apply LOTO first.

### 2.4 Lifting limits

A compute sled weighs 21 kg, a rectifier module weighs 6.5 kg, and the two-person lift threshold is 18 kg. Any item heavier than 18 kg requires two people to lift it, whether the lift is into the rack, out of the rack or over a short distance.

| Item | Weight | Lift rule |
|---|---|---|
| Compute sled CS-2U | 21 kg | Two persons. The sled exceeds the 18 kg threshold. |
| Rectifier module (R1-R6) | 6.5 kg | One person may lift. |
| Power Shelf PS-3000 | Not stated in this revision | Two persons until the weight is confirmed. |
| Fan module (FM1-FM6) | Not stated in this revision | Confirm the weight before you lift without assistance. |

> **CAUTION:** A compute sled weighs 21 kg, above the 18 kg two-person threshold. Do not lift a sled alone, even for a short distance. Keep the load close to your body and clear the route before you lift.

### 2.5 Torque values

The only torque value defined for this revision is 14 N·m for the busbar connections. The busbar torque check is an annual Engineer-level task (see Section 3.3.6).

| Fastener | Torque | Responsible level | Interval |
|---|---|---|---|
| Busbar connection | 14 N·m | Engineer | Annual torque check |

> **CAUTION:** No other torque values are defined for this revision. Do not apply a torque value from memory, from another product or from a previous revision. Confirm the value with engineering first.

## 3. Preventive maintenance schedule

### 3.1 Schedule table

The schedule has seven tasks, grouped by interval. Each task has one responsible escalation level. The planned time is used to schedule a maintenance window. It is not a procedure limit.

| Task | Interval | Escalation level | Planned time (min) |
|---|---|---|---|
| Visual LED and cable inspection | Weekly | Technician L1 | 15 |
| Clean fan wall filters / dust check | Monthly | Technician L1 | 30 |
| Optical transceiver clean and inspect | Quarterly | Technician L2 | 45 |
| Rectifier module load test | Quarterly | Technician L2 | 60 |
| BMC and BIOS firmware review | Semi-annual | Engineer | 90 |
| Busbar torque check (14 N·m) | Annual | Engineer | 120 |
| Full thermal survey with IR camera | Annual | Engineer | 180 |

### 3.2 Schedule by interval

Look at Figure F9 to see the same schedule grouped by interval before you build a monthly or quarterly work plan. Combine the tasks that fall due together so that you open the rack as few times as possible. The annual window is the longest, because it combines the busbar torque check, which needs LOTO, with the thermal survey.

![Figure F9: Preventive maintenance schedule by interval](figures/F9_maintenance_schedule.png)
*Figure F9: Preventive maintenance schedule by interval*

### 3.3 Task procedures

#### 3.3.1 Weekly visual LED and cable inspection (Technician L1)

1. Walk the front of the rack from U02 to U23 and the rear fan wall. Note any amber or red LED, and any LED that is off without an explanation.
2. Compare each sled front panel with the front-panel LED legend. The PWR LED should be solid green in normal operation. The BMC LED should blink blue at 0.5 Hz when the BMC is healthy.
3. Check that cables are seated at the fan modules and not pinched.
4. Check that blanking panels fill every empty U position. Missing panels are a common cause of fault 0x8F20_AIRFLOW_BLOCK.
5. Open a ticket for each abnormal LED. Do not clear a fault code from the BMC during a visual inspection.

#### 3.3.2 Monthly fan wall and dust check (Technician L1)

1. Check that all six fan modules, FM1 to FM6, are present and seated.
2. Read the fan speeds from the management interface. The rated speed is 9000 RPM and the minimum speed is 2800 RPM. A tachometer reading below 600 RPM raises fault 0x8F01_FAN_TACH_FAIL against the failing module, for example Fan Module 4. A module below the minimum speed also requires a swap, using the hot-swap procedure.
3. Clean the fan wall filters and the intake area with the approved site method. Do not blow dust into the sled inlets.
4. Two or more tachometer failures are fault 0x8F02_FAN_ALL_FAIL, which is Critical. Follow Section 4.

#### 3.3.3 Quarterly optical transceiver clean and inspect (Technician L2)

1. Identify the ports to be inspected. Uplink ports QSFP28_01 to QSFP28_16 connect to the spine layer. Server ports QSFP28_17 to QSFP28_32 connect to the compute sleds.
2. Confirm that the port is down and the laser is off before you look into an open port or fiber end.
3. Remove the transceiver, inspect the end-face and clean it with the approved method. Reseat the fiber connector until it clicks.
4. Confirm that a 100 GbE port uses a transceiver rated for 100G. A port that negotiates 25 GbE, as in fault 0xC02A_ETH_PHY_DEGRADED on QSFP28_21, needs a cable or transceiver check.
5. Record the port, the transceiver serial number and the result.

> **WARNING:** Do not look into an open optical port or fiber end while any laser may be active.

#### 3.3.4 Quarterly rectifier module load test (Technician L2)

1. Confirm that the shelf runs in its normal N+1 arrangement, with five active rectifiers and one spare.
2. Test one rectifier module at a time. Testing more than one removes the N+1 margin.
3. Keep the busbar inside 44.0 V to 52.0 V throughout. If it leaves that range, stop the test, remove the load and escalate.
4. Read the PMBus status for each module. Fault 0x99A1_PMBUS_CRC_ERR is raised for rectifier R3 when CRC errors repeat. Reseat R3 during the next window when this fault is present.
5. Record the module identifier, the load level, the busbar voltage and any PMBus error count.

> **CAUTION:** Do not begin the test if another rectifier is already in fault or if the shelf is running on fewer than five active rectifiers.

#### 3.3.5 Semi-annual BMC and BIOS firmware review (Engineer)

1. Record the BIOS, BMC and switch OS versions for each sled and for the switch.
2. Compare each version set with the compatibility matrix in *Release Notes and Firmware Compatibility*. A combination that is not listed is not supported.
3. Export the System Event Log from each sled and search it for fault 0x9A05_BMC_WDT_RESET and fault 0x9A10_BMC_FW_MISMATCH.
4. Decide whether a firmware change is needed, and follow the upgrade order in *Release Notes and Firmware Compatibility*.

#### 3.3.6 Annual busbar torque check (Engineer)

1. Apply LOTO to the AC feeder as described in Section 2.3, and measure the busbar voltage before you touch any connection.
2. Inspect each busbar connection for corrosion and discolouration. The remediation for fault 0x7D02_BUSBAR_RIPPLE asks for the same inspection when busbar ripple is high.
3. Check each connection with a calibrated torque tool at 14 N·m. Record the value found and the value set.
4. If a connection is below 14 N·m, tighten it to 14 N·m. If a connection shows corrosion, escalate for a decision on replacement.

#### 3.3.7 Annual full thermal survey with IR camera (Engineer)

1. Survey the sled inlets and outlets, the Power Shelf PS-3000 and the Top-of-Rack Switch AS-100G with the IR camera.
2. Compare the readings with the thermal thresholds in *Thermal and Cooling Manual*. The inlet warning threshold is 35 C and the inlet critical threshold is 42 C. The CPU warning threshold is 75 C and the CPU critical threshold is 90 C. The switch ASIC warning threshold is 85 C and the switch ASIC critical threshold is 95 C.
3. Note any sled whose outlet is hotter than its neighbours. This is a sign of airflow blockage or a fan problem.

> **CAUTION:** An IR camera measures surface temperature, not the air temperature at the sled inlet. Use the inlet sensor values reported by the BMC for threshold decisions, and use the IR image only to locate hot spots.

## 4. Escalation levels

Three escalation levels apply to all maintenance and fault work. Work outside a level's scope must be escalated to the next level, and the escalation is recorded in the ticket.

| Level | Who | Typical work | Escalate when |
|---|---|---|---|
| L1 | Technician L1 | Weekly and monthly tasks. Fan and rectifier module hot swap. Reseating of listed cables and drives. First response to Warning and Minor codes whose listed remediation is inspection, reseat or logging. | Any Critical code. Any Major code that the listed remediation does not clear. Any fault that recurs. |
| L2 | Technician L2 | Quarterly tasks. Optical transceiver cleaning. Rectifier load test. PMBus ribbon, DAC cable and switch fan tray replacement. Fuse F2 replacement after the cause is found. DIMM replacement for a memory fault. | Firmware decisions. Repeated Critical events. TPM attestation faults. Coolant events. Any task outside the L2 list. |
| Engineer | Engineer | Semi-annual and annual tasks. Firmware and rollback decisions. Busbar torque check. Thermal survey. TPM quarantine and re-enrollment. Coolant incidents with the facility team. | Not applicable. The Engineer owns the final decision. |

> **WARNING:** On any Critical code, the first responder performs only the safe action named in the remediation, then escalates to Technician L2 at once. Do not run a diagnostic on a Critical fault until the safe action is complete.

If you are unsure which level applies, escalate one level. Escalation is not a failure.

## 5. Storage, NVMe and memory handling

### 5.1 General handling rules

- Wear an ESD wrist strap before you handle any drive, DIMM or circuit board.
- Hold each component by its edges. Do not touch DIMM contacts or NVMe connectors.
- Place removed parts in an ESD bag or on an ESD mat, not on bare metal.
- Label each removed part with the sled number, the slot or bay, and the date.

### 5.2 NVMe drive handling

Each compute sled has two NVMe bays, referred to here as bay 1 and bay 2. The storage fault codes name the bay: fault 0x2B30_NVME_SMART_WARN is raised for bay 1, and fault 0x2B31_NVME_LINK_DOWN is raised for bay 2. The sled's NVMe-oF storage traffic uses VLAN 103 (STORAGE).

| Code | Bay | Severity | LED | Meaning | Remediation |
|---|---|---|---|---|---|
| 0x2B30_NVME_SMART_WARN | Bay 1 | Warning | Solid green PWR | Less than 10 % endurance remaining | Order a replacement drive. Migrate data during the next window. |
| 0x2B31_NVME_LINK_DOWN | Bay 2 | Major | Blinking amber PWR | PCIe link failed to train | Reseat the drive. Test with a different NVMe bay. Replace the backplane if both fail. |

Fault 0x2B30_NVME_SMART_WARN is not an emergency. The drive is still in service, so plan the replacement and migrate the data in the next window rather than waiting for the drive to fail.

For fault 0x2B31_NVME_LINK_DOWN, the drive may already be unreachable. Export the System Event Log first. Then reseat the drive in bay 2 and check the log for a PCIe link training result. If the link still fails, move the drive to bay 1. If the drive trains in bay 1, the fault is in bay 2 or its connection, so escalate to Technician L2. If both bays fail, replace the backplane and escalate.

> **NOTE:** After any NVMe drive or backplane change, confirm that the VLAN 103 storage paths are up before you return the sled to service.

### 5.3 DIMM handling

Each compute sled has 16 DDR5-5600 RDIMM slots. Slots A1 to A8 belong to CPU0 and slots B1 to B8 belong to CPU1. The maximum installed memory per sled is 2048 GB.

1. Power down the sled as described in the sled service procedure before you remove or insert a DIMM. Do not hot-plug a DIMM.
2. Insert the DIMM straight into the slot and press both ends evenly until the latches close.
3. Quarantine any DIMM with a bent pin or cracked edge connector, and escalate.

The three memory fault codes need different actions. Read the full code before you act, because the codes look alike.

| Code | Slot | Severity | LED | Action | Escalation |
|---|---|---|---|---|---|
| 0x10E4_ECC_MULTI_BIT | DIMM_A2 | Critical | Solid red PWR | Halt the node. Replace the DIMM in slot A2 immediately. | Technician L2 |
| 0x10E5_ECC_SINGLE_BIT | DIMM_B5 | Warning | Solid green PWR | Schedule replacement of DIMM_B5. No immediate downtime is required. | Technician L2 |
| 0x10F0_DIMM_TRAINING_FAIL | DIMM_A7 | Major | Blinking amber PWR | Reseat DIMM_A7. If the failure persists, test the slot with a known-good DIMM. | Technician L1, then L2 |

> **WARNING:** Fault 0x10E4_ECC_MULTI_BIT and fault 0x10E5_ECC_SINGLE_BIT share the prefix 0x10E. Fault 0x10E4 is an uncorrectable error that requires an immediate halt. Fault 0x10E5 is a correctable error that is scheduled. Do not treat a 0x10E5 entry as a reason to halt a node, and do not replace a DIMM on the basis of a partial code.

For fault 0x10F0_DIMM_TRAINING_FAIL, the BIOS 2.0.0 build adds DDR5 retraining improvements. Check the firmware level in *Release Notes and Firmware Compatibility* before you replace hardware for this fault.

## 6. Maintenance records

Every maintenance visit produces a record. Each entry must contain the rack and U position, the task or fault code, the escalation level, the LOTO details (lock ID, times and names, or the reason no LOTO was applied), the measurements taken, the part numbers and serial numbers with their slot or bay, the file name of the SEL exports taken before and after the work, and the outcome with the next scheduled task.

## Frequently asked questions

**Q1. Do I need LOTO to hot-swap a fan module?**

No. A fan module is not a rectifier connection, so the LOTO rule in Section 2.3 does not apply. Use the hot-swap procedure, wear the PPE listed for the fan module swap in Section 2.2, and confirm that the tachometer reading returns. If the task extends to a rectifier connection or to the busbar, apply LOTO first.

**Q2. What torque is required for the busbar connections?**

The busbar connections require 14 N·m, checked in the annual busbar torque check by the Engineer level. No other torque values are defined for this revision. Confirm with engineering before you tighten any fastener that is not listed in Section 2.5.

**Q3. What is the difference between fault 0x10E4 and fault 0x10E5?**

Fault 0x10E4_ECC_MULTI_BIT is a Critical, uncorrectable multi-bit parity failure on DIMM_A2. The node must be halted and the DIMM replaced immediately. Fault 0x10E5_ECC_SINGLE_BIT is a Warning for correctable single-bit errors on DIMM_B5 that exceeded 24 per hour. Its replacement is scheduled and needs no immediate downtime.

**Q4. The bay 1 NVMe drive shows fault 0x2B30. Do I replace it now?**

Plan the replacement, but do not treat it as an emergency. Fault 0x2B30_NVME_SMART_WARN means less than 10 % endurance remains. Order a replacement, migrate the data during the next window and replace the drive then.

**Q5. Can I use the IR camera to decide whether a sled is above the inlet thermal threshold?**

No. The IR camera measures surface temperature, not inlet air temperature. Use the inlet sensor readings reported by the BMC to decide whether a sled is above the 35 C warning or 42 C critical threshold. Use the IR image to find hot spots.

**Q6. A fault is Critical and the procedure says to run a diagnostic. What do I do first?**

Perform only the safe action named in the remediation, then escalate to Technician L2 at once. Do not run a diagnostic on a Critical fault until the safe action is complete. The first responder's task is to make the rack safe, not to diagnose the fault.

**Q7. Who performs the firmware review, and can a technician change firmware during a routine visit?**

The Engineer performs the semi-annual BMC and BIOS firmware review against the compatibility matrix in *Release Notes and Firmware Compatibility*. Technicians do not change firmware as part of a routine visit.
