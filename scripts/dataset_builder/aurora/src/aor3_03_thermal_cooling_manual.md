# Thermal and Cooling Manual

Document ref: aor3_03_thermal_cooling_manual | Revision: Rev 3.2 (2026-03) | Classification: Fictional training material

## 1. Scope and intended readers

This manual describes how the Aurora Open Rack AOR-3 controls heat and airflow. It covers the thermal thresholds the controllers enforce, the fan control curve, the rear fan wall FW-6 and its hot-swap procedure, the DDR5 DIMM slot layout of the compute sleds, and the thermal and liquid-cooling fault codes written to the System Event Log (SEL). It is written for Technician L1 and Technician L2 staff and for the engineers who review thermal escalations.

Electrical work on the rectifiers and the 48 V busbar is outside this manual. See *Power Shelf PS-3000 Service Manual* for those tasks. For BMC commands see *BMC, Redfish and CLI Operations Guide*. For the decision flowchart used with amber PWR faults see *Fault Code Reference and Troubleshooting Flowcharts*. For fan filter checks, thermal surveys and sled removal steps see *Preventive Maintenance and Safety Manual*. For switch cooling see *Top-of-Rack Switch AS-100G Manual*.

> **NOTE:** Every numeric value in this manual is taken from the AOR-3 engineering specification for Revision 3.2. Where a value is not stated in that specification, this manual does not supply one. Do not estimate a missing value from another value in a table.

## 2. Thermal architecture

Heat is produced in three places: the compute sleds in U02-U19, the power shelf PS-3000 in U20-U22, and the top-of-rack switch AS-100G in U23. The cooling design centres on the sleds, which produce most of the load. The power shelf and the switch have their own monitoring and are covered in their own manuals.

Each compute sled (Compute Sled CS-2U) carries an on-board baseboard management controller (BMC) running OpenBMC 2.14 with Redfish 1.17. The BMC makes the thermal decisions for its sled. It polls the sled sensors every 2 seconds, writes fault codes to a SEL that holds 4096 entries, sets the fan duty command from the curve in section 4, drives the front-panel PWR LED, and starts an emergency shutdown when the CPU reaches the critical temperature.

Cooling air is pulled through the sleds by the rear fan wall FW-6. The fan wall consists of six hot-swappable fan modules, FM1 to FM6, each with its own tachometer wire that the BMC reads to confirm that the fan is turning. The switch has its own fan trays, and its airflow runs front-to-back. The airflow direction is one of the items checked when the switch reports a high ASIC temperature.

> **WARNING:** Do not reverse, block or bypass any fan path to make a sled run cooler. A blocked or reversed path produces the same symptoms as a failed fan and can drive a sled into a critical shutdown.

## 3. Thermal thresholds

Table 3-1 lists the thresholds that trigger a warning or a critical event. A warning sets the front-panel PWR LED to blinking amber. A critical event sets it to solid red. The table gives the fault code written to the SEL at each level where one exists.

**Table 3-1. Thermal thresholds**

| Sensor | Warning threshold | Critical threshold | Fault code at warning | Fault code at critical | Notes |
|---|---|---|---|---|---|
| Sled CPU temperature | 75 C | 90 C | 0x8F10_TEMP_WARN | 0x8F11_TEMP_CRIT | At the critical level the BMC starts an emergency shutdown. |
| Sled inlet temperature | 35 C | 42 C | None assigned in this revision | None assigned in this revision | See note 3.2. |
| Switch ASIC junction (TS-3200) | 85 C | 95 C | None assigned in this revision | 0xC055_SWITCH_ASIC_TEMP | The switch writes its code only at 95 C. |

### 3.1 How the thresholds are used

At 75 C the BMC forces all fan modules to 100 % duty and throttles the CPU, and the PWR LED blinks amber at 1 Hz. The warning state alone does not shut the sled down. At 90 C the BMC logs 0x8F11_TEMP_CRIT, sets the PWR LED to solid red, and starts the emergency shutdown. A technician who sees the critical code should confirm the sled state through the BMC before doing any other work on it.

The ASIC thresholds apply to the switch. Readings between 85 C and 95 C produce no SEL event in this revision, but they call for the same airflow and fan tray checks described in *Top-of-Rack Switch AS-100G Manual*.

### 3.2 Inlet threshold reference discrepancy

> **NOTE:** The threshold set lists the sled inlet warning at 35 C and the inlet critical at 42 C. The definition of 0x8F10_TEMP_WARN states its trigger as a CPU or inlet temperature above 75 C. The two reference values for inlet temperature are not reconciled in this revision.

When a case involves an inlet reading, record the inlet temperature in degrees Celsius next to the SEL entry, and record which reference value you used. Escalate the difference to engineering. Do not choose one value yourself and close the case on that basis.

## 4. Fan control curve

The BMC sets the fan duty command from the sled CPU temperature using the curve in Table 4-1. Figure F5 shows the same curve as a chart with the warning and critical thresholds marked. Look at it when you need to explain why the fans are running at a given duty level, or when you need to judge whether a reading is in the expected range.

![Figure F5: Fan duty versus temperature with warning and critical thresholds](figures/F5_thermal_fan_curve.png)

*Figure F5: Fan duty versus temperature with warning and critical thresholds.*

**Table 4-1. Fan control curve**

| CPU temperature (C) | Fan duty command (%) |
|---|---|
| 30 | 30 |
| 40 | 40 |
| 50 | 55 |
| 60 | 70 |
| 70 | 85 |
| 75 | 100 |
| 90 | 100 |

### 4.1 Reading the curve

The curve has seven defined points. Duty rises with temperature and reaches 100 % at 75 C, the same temperature as the thermal warning. Between 75 C and the 90 C critical point the duty stays at 100 %, so the fans give no further response in that band.

The curve does not list values between the defined points. A CPU at 65 C, for example, lies between the 60 C and 70 C points, but this manual does not give the duty for 65 C. Read the actual duty and the fan tachometer values from the BMC rather than interpolating on paper.

### 4.2 Duty is a command, not a speed

The duty percentage is the command that the BMC sends to the fan modules. It is not a measured speed. The rated speed of each FW-6 module is 9000 RPM and the minimum speed is 2800 RPM. The specification does not publish a conversion from duty to RPM, so do not calculate RPM from the duty percentage. Use the tachometer values reported by the BMC, and compare them with the failure threshold in section 5.1.

> **WARNING:** A commanded duty does not prove that a fan is turning. Always confirm the tachometer reading before you decide that a fan is working.

## 5. Fan wall FW-6

The Fan Wall FW-6 is the rear fan assembly of the AOR-3. It consists of six fan modules, FM1 to FM6, mounted at the rear of the sled bays U02-U19. Each module is hot-swappable, so a single failed module can be replaced while the sled stays in service.

### 5.1 Specifications

**Table 5-1. FW-6 specifications**

| Parameter | Value |
|---|---|
| Location | Rear of U02-U19 |
| Number of modules | 6 (FM1 to FM6), hot-swappable |
| Rated speed per module | 9000 RPM |
| Minimum speed per module | 2800 RPM |
| Tachometer failure threshold | Below 600 RPM |
| Swap time per module | 30 seconds |
| Airflow per module | 85 CFM |

A module that reads below 600 RPM triggers 0x8F01_FAN_TACH_FAIL. The minimum speed of 2800 RPM is the value a healthy module should not fall below in normal operation. A module that runs but stays below the minimum speed is a case for the investigation in section 9, not an immediate swap.

### 5.2 Fault behaviour

The fan wall reports two fault conditions, and they require different responses.

- **One module fails its tachometer check.** The BMC logs 0x8F01_FAN_TACH_FAIL with severity Major and the PWR LED blinks amber. The sled keeps running, and the failed module is replaced under the hot-swap procedure in section 5.3.
- **Two or more modules fail their tachometer check.** The BMC logs 0x8F02_FAN_ALL_FAIL with severity Critical and the PWR LED is solid red. The sled must be shut down gracefully within 5 minutes, and the fan modules must be replaced before the sled is restarted.

> **WARNING:** Do not start a hot swap on a sled that reports 0x8F02_FAN_ALL_FAIL. A critical fan event is a shutdown case. Follow section 7.1.

### 5.3 Hot-swap procedure for one fan module

This procedure applies only when the SEL shows a single tachometer failure, 0x8F01_FAN_TACH_FAIL. The fault definition uses Fan Module 4 (FM4) as its example. Use the same steps for any module, and record the module number that the BMC reports.

**Procedure: hot-swap of one FW-6 fan module**

1. Read the SEL with `bmc-cli sel export` or through Redfish, as described in *BMC, Redfish and CLI Operations Guide*. Confirm the code 0x8F01_FAN_TACH_FAIL and note the module number, for example FM4.
2. Check that no other module reports a tachometer failure. If a second module is reported, stop and follow section 7.1.
3. Confirm the sled is still running and that no critical thermal event is present. If the CPU is at or above the critical temperature, stop and follow section 9.
4. Fit an ESD wrist strap before you touch the fan wall. Wear the protective equipment listed in *Preventive Maintenance and Safety Manual* for work at the rear of the rack.
5. Inspect the tachometer cable of the failed module and check that it is seated at both ends. Reseat it if it is loose. This is the first remediation step for 0x8F01_FAN_TACH_FAIL.
6. If the cable is seated and the module still shows the fault, prepare the replacement before you touch the failed module. Confirm that it is the FW-6 module type and that its tachometer wire is available.
7. Release the failed module using its retention mechanism and withdraw it. The specified swap time is 30 seconds per module, so plan the swap so that the bay is open for no longer than this. Do not leave the bay open while you look for tools.
8. Insert the replacement module fully until it is seated, and connect its tachometer wire.
9. Confirm the result. The BMC should report the module as present with a tachometer reading above the 600 RPM failure threshold. The SEL should show no new 0x8F01_FAN_TACH_FAIL event. When the sled has no other thermal condition, the PWR LED returns to solid green.
10. Record the swap on the job record, including the module number, the time, the SEL event identifiers and the technician name.

> **CAUTION:** A swapped module does not mean the sled is in its normal state. Watch the CPU temperature for a few minutes after the swap. If it rises to the warning level again, return to section 9 rather than closing the case on the fan swap alone.

### 5.4 Airflow during a swap

Each module moves 85 CFM, so a removed module reduces airflow across the sleds for as long as its bay is open. Keep the swap short and do not start other work on the fan wall while a module is out. If the replacement cannot be fitted within the swap time, keep the failed module in place until the replacement is ready. Never remove two modules at once.

## 6. DIMM layout and memory faults

The compute sled has 16 DDR5-5600 RDIMM slots, with a maximum memory capacity of 2048 GB. The slots are split between the two CPU sockets: CPU0 owns the A-row slots and CPU1 owns the B-row slots. Figure F8 shows the physical slot layout on the sled board. Use it to locate a slot, or when the SEL names a DIMM that you need to find.

![Figure F8: Compute sled DIMM slot layout (CPU0 A1-A8, CPU1 B1-B8)](figures/F8_dimm_slot_layout.png)

*Figure F8: Compute sled DIMM slot layout (CPU0 A1-A8, CPU1 B1-B8).*

**Table 6-1. DIMM slot allocation**

| CPU socket | Slot range | Number of slots | Memory type |
|---|---|---|---|
| CPU0 | A1 to A8 | 8 | DDR5-5600 RDIMM |
| CPU1 | B1 to B8 | 8 | DDR5-5600 RDIMM |
| Total | A1-A8 and B1-B8 | 16 | Up to 2048 GB |

### 6.1 Slot naming in the SEL

The BMC names each slot in the SEL with its DIMM number, for example DIMM_A2 for slot A2 or DIMM_B5 for slot B5. Use the name from the SEL event rather than an estimate from the physical position of the sled.

### 6.2 Memory fault codes

Three memory codes often appear in a thermal investigation because a sled reboots while a thermal alarm is open. Table 6-2 lists them. The full memory fault list is in *Fault Code Reference and Troubleshooting Flowcharts*.

**Table 6-2. Memory fault codes referenced in this manual**

| Fault code | Slot | Severity | PWR LED | Required action |
|---|---|---|---|---|
| 0x10E4_ECC_MULTI_BIT | DIMM_A2 (slot A2) | Critical | Solid red | Halt the node. Replace the DIMM in slot A2 immediately. |
| 0x10E5_ECC_SINGLE_BIT | DIMM_B5 (slot B5) | Warning | Solid green | More than 24 correctable errors per hour. Schedule replacement. No immediate downtime is required. |
| 0x10F0_DIMM_TRAINING_FAIL | DIMM_A7 (slot A7) | Major | Blinking amber | Memory training failed at boot. Reseat DIMM_A7. If the failure persists, test the slot with a known-good DIMM. |

> **WARNING:** 0x10E4_ECC_MULTI_BIT is an uncorrectable error. Halt the node and replace the DIMM in slot A2 first. Do not restart the node to see whether the error returns.

### 6.3 Handling a sled for DIMM work

The compute sled weighs 21 kg, which is above the 18 kg two-person lift limit. Two technicians are required to lift the sled out of the rack or onto a bench, so confirm that the second person is available before the work starts. Follow the sled removal steps in *Preventive Maintenance and Safety Manual*, and confirm the sled state through the BMC before any removal begins.

## 7. Thermal and liquid-cooling fault codes

This section lists the thermal fault codes and the two liquid-cooling codes. The codes are written exactly as they appear in the SEL.

**Table 7-1. Thermal and liquid-cooling fault codes**

| Fault code | Subsystem | Severity | PWR LED | Trigger | SEL event |
|---|---|---|---|---|---|
| 0x8F01_FAN_TACH_FAIL | Thermal | Major | Blinking amber | Tachometer signal lost on Fan Module 4 (below 600 RPM) | SEL-0201 |
| 0x8F02_FAN_ALL_FAIL | Thermal | Critical | Solid red | Two or more fan modules report tachometer failure | SEL-0202 |
| 0x8F10_TEMP_WARN | Thermal | Warning | Blinking amber | CPU or inlet temperature above 75 C | SEL-0210 |
| 0x8F11_TEMP_CRIT | Thermal | Critical | Solid red | CPU temperature above 90 C | SEL-0211 |
| 0x8F20_AIRFLOW_BLOCK | Thermal | Warning | Blinking amber | Pressure sensor shows restricted airflow across the sled | SEL-0212 |
| 0x5F01_COOLANT_LEAK | Liquid cooling | Critical | Solid red | Rear-door heat exchanger leak sensor is wet (optional liquid-cooling kit only) | SEL-0801 |
| 0x5F02_COOLANT_FLOW_LOW | Liquid cooling | Warning | Blinking amber | Coolant flow below 8 L/min (optional liquid-cooling kit only) | SEL-0802 |

### 7.1 Fan codes

Use section 5.3 for 0x8F01_FAN_TACH_FAIL. Inspect the fan cable seating first, then swap the failed module under the hot-swap procedure.

The critical code 0x8F02_FAN_ALL_FAIL requires a graceful shutdown within 5 minutes of the event. The remediation names both failed modules, and the sled must not be restarted until both have been replaced. Do not delay the shutdown while you collect parts. If the sled is already shutting down because of a critical temperature, let the shutdown complete and check the thermal state before any restart.

### 7.2 Temperature codes

0x8F10_TEMP_WARN and 0x8F11_TEMP_CRIT share the prefix 0x8F1 and the same subsystem, so they are easy to confuse. The difference is severity and threshold. 0x8F10_TEMP_WARN is a warning at 75 C: the sled stays up, the fans run at 100 %, and the CPU is throttled. 0x8F11_TEMP_CRIT is critical at 90 C: the PWR LED is solid red and the BMC starts an emergency shutdown. Always write the full code in a case note.

For 0x8F10_TEMP_WARN, check airflow blockage, blanking panels and ambient temperature. The fans are already at 100 % at this level, so the fan wall is not the first component to replace.

For 0x8F11_TEMP_CRIT, let the sled cool for 10 minutes. Before the restart, verify the fan wall FW-6 and the cold-aisle temperature.

### 7.3 Airflow code

0x8F20_AIRFLOW_BLOCK is a warning raised by a pressure sensor on the sled. It means that airflow across the sled is restricted. The usual causes are missing blanking panels in empty U positions and obstructions in front of the sled. Section 8 gives the procedure.

### 7.4 Liquid-cooling codes

The two liquid-cooling codes apply only to racks with the optional liquid-cooling kit and its rear-door heat exchanger. Confirm that the kit is installed before you treat either code as a real event.

0x5F01_COOLANT_LEAK is critical. Close the manual valves, power down the affected sleds, and call the facility team. Do not wipe up the liquid and restart the sled.

0x5F02_COOLANT_FLOW_LOW is a warning. The coolant flow is below 8 L/min. Check the pump status and the quick-disconnect couplings. Do not clear the event until the flow has been measured again.

## 8. Airflow management and blanking panels

The fan wall pulls air through the sleds, and gaps in the front of the rack reduce that flow. The 0x8F20_AIRFLOW_BLOCK warning is the BMC's signal that the pressure across a sled is not what it should be.

**Procedure: airflow inspection**

1. Walk the front of the rack and check every empty U position. This includes the reserved range U25-U42 and any slot left open after a sled removal.
2. Install a blanking panel in each empty U position. A missing blanking panel is the most common cause of restricted airflow in an otherwise healthy rack.
3. Remove any obstruction in front of the sled, such as cable bundles, boxes or tools.
4. Check the switch fan trays and the switch airflow direction as described in *Top-of-Rack Switch AS-100G Manual*.
5. Check the ambient and cold-aisle temperature near the rack. If the room is warm, the problem lies in the facility rather than the rack.
6. Clear the 0x8F20_AIRFLOW_BLOCK event only after the blanking panels are in place and the pressure reading has returned to normal.

> **CAUTION:** A blanking panel goes in an empty U position. Do not use it to cover a fan or the front inlet of an occupied sled.

## 9. Thermal triage workflow

Use this workflow when a PWR LED shows a thermal state or the SEL contains a code from section 7. It is the thermal branch of the wider flowchart in *Fault Code Reference and Troubleshooting Flowcharts*. Follow the steps in order and stop at the first step that gives a clear answer.

1. Read the PWR LED. Blinking amber at 1 Hz means a thermal warning. Solid red means a critical fault. Solid green means the sled is normal, so do not treat a thermal alarm as active until the SEL confirms it.
2. Export the SEL with `bmc-cli sel export` and find the most recent thermal code.
3. If the code is 0x8F11_TEMP_CRIT or 0x8F02_FAN_ALL_FAIL, the sled is in a critical state. Confirm that it is shut down or shutting down. Do not restart it until the checks in section 7 are complete.
4. If the code is 0x8F10_TEMP_WARN, check airflow and ambient temperature as described in section 8. Confirm that the fan duty is at 100 % in the BMC view. Do not replace the fan wall unless a tachometer code is also present.
5. If the code is 0x8F01_FAN_TACH_FAIL, follow section 5.3.
6. If the code is 0x8F20_AIRFLOW_BLOCK, follow section 8.
7. If the code is 0x5F01_COOLANT_LEAK or 0x5F02_COOLANT_FLOW_LOW, follow section 7.4 and do not continue until the coolant status is known.
8. After the corrective action, watch the CPU temperature for at least a few minutes. If it returns to the warning level, repeat this workflow from step 2.
9. Record the codes, the actions taken and the final temperature reading on the job record.

## 10. Frequently asked questions

**Q: The PWR LED on a sled is blinking amber and the SEL shows 0x8F10_TEMP_WARN. Do I need to shut the sled down?**

A: No. The warning level does not trigger the emergency shutdown. At this level the BMC forces the fans to 100 % duty and throttles the CPU. Check airflow, blanking panels and ambient temperature as described in section 8. The emergency shutdown happens at the critical level, 0x8F11_TEMP_CRIT at 90 C.

**Q: Can I replace one FW-6 fan module while the sled is running?**

A: Yes, if the only fan event is 0x8F01_FAN_TACH_FAIL for one module. Follow section 5.3. If two or more modules report a tachometer failure, the event is 0x8F02_FAN_ALL_FAIL. That is a critical event, and the sled must be shut down within 5 minutes before the fan modules are replaced.

**Q: What is the difference between 0x8F10_TEMP_WARN and 0x8F11_TEMP_CRIT?**

A: The first is a warning at 75 C and the second is a critical event at 90 C. The codes look alike, but they have different LED states and different responses. The warning sets the fans to 100 % and throttles the CPU. The critical event starts the emergency shutdown.

**Q: The fan curve gives 30 % duty at 30 C. Does that mean the fans turn at 2700 RPM?**

A: Do not calculate that. The duty percentage is a command, and the specification gives no conversion from duty to RPM. Read the tachometer values from the BMC. The rated speed is 9000 RPM and the minimum speed is 2800 RPM.

**Q: The SEL shows 0x8F20_AIRFLOW_BLOCK. What should I check first?**

A: Check the empty U positions at the front of the rack. Install blanking panels in every empty position and clear any obstruction in front of the sled. The warning is a pressure reading, so it should clear once the airflow path is complete again.

**Q: The inlet reading on a sled is 38 C. Is that a warning?**

A: The threshold set gives an inlet warning level of 35 C, which would make 38 C a warning. The fault code definition for 0x8F10_TEMP_WARN uses 75 C for CPU or inlet temperature. The two reference values are not reconciled in this revision. Record the reading and the SEL entry, and escalate the difference as described in section 3.2.

**Q: Which DIMM must I replace for 0x10E4_ECC_MULTI_BIT?**

A: The slot named in the event, DIMM_A2 (slot A2). This is an uncorrectable error. Halt the node and replace the DIMM in slot A2 immediately. Do not restart the node to test whether the error returns.
