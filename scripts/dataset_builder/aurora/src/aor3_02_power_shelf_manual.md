# Power Shelf PS-3000 Service Manual

Document ref: aor3_02_power_shelf_manual | Revision: Rev 3.2 (2026-03) | Classification: Fictional training material

## 1. Purpose and scope

This manual covers the Power Shelf PS-3000 of the Aurora Open Rack AOR-3. It describes the rectifier arrangement, the 48 V DC busbar, the power distribution board (PDB) and its fuse F2, the power-related LED states, the power-related fault codes, and the replacement procedures for each power component.

The manual covers these fault codes:

- `0x4A7B_VRM_OVERVOLT`
- `0x4A7C_VRM_UNDERVOLT`
- `0x4A80_VRM_OVERCURRENT`
- `0x4B10_PSU_RECT_FAIL`
- `0x4B22_PSU_AC_LOSS`
- `0x7D01_PDB_FUSE_BLOWN`
- `0x7D02_BUSBAR_RIPPLE`

The BMC, the fan wall and the switch have their own manuals, listed in section 9.
This manual is written for Level 2 technicians who replace modules and for engineers who diagnose power events. Level 1 technicians should read sections 2, 3 and 6 before they escalate a power event. Read the *Preventive Maintenance and Safety Manual* in full before you start any procedure in section 8.

> **WARNING:** The procedures in this manual work on a high-energy 48 V DC busbar and on 3-phase 400 V AC mains. Only qualified personnel may perform them.

## 2. Safety

### 2.1 Personal protective equipment

Wear the following equipment for every task in this manual. Do not start a task if any item is missing.

| Item | Requirement |
|---|---|
| Insulated gloves | Rated 1000 V |
| Eye protection | Safety glasses |
| ESD protection | ESD wrist strap connected to a grounded point |

### 2.2 Energy hazard

The 48 V DC busbar can deliver more than 300 A. A short across the busbar, or between a busbar connection and a metal part, can cause severe burns, arc flash and damage to the rack.
> **WARNING:** Never place a metal tool, a jewellery item or a loose cable across the busbar or across two busbar connections. Use insulated tools only.

### 2.3 Lock-out and tag-out

Lock out and tag out the AC feeder before you touch any rectifier connection. The rule applies to every module swap in section 8, because a rectifier connector is a rectifier connection. Apply the lock at the upstream feeder breaker, attach a tag that names the technician and the work order, and verify that the feeder is isolated before you proceed.

> **CAUTION:** Hot-swap of a rectifier module does not remove the lock-out and tag-out requirement. The shelf keeps the rack powered on the other modules, but the module connector is still a live connection.

## 3. Shelf overview

### 3.1 Physical layout

The PS-3000 is a 3U unit located at U20 to U22. It holds six rectifier modules, labelled R1 to R6. Each module is hot-swappable and has a rated output of 3 kW. The shelf converts 3-phase 400 V AC mains into a 48 V DC busbar that feeds every compute sled in the rack.

Figure F3 shows the power distribution from the mains to the busbar and to the 12 V point-of-load stage of each sled. Look at it when you need to identify the stage of the power path that a fault belongs to.

![Figure F3: Power distribution from 400 V AC through the rectifiers to the 48 V busbar and the 12 V PoL stage](figures/F3_power_distribution_block.png)

*Figure F3: Power distribution: 400 V AC to rectifiers, 48 V busbar, 12 V PoL.*

### 3.2 Specifications

| Parameter | Value |
|---|---|
| Rack units | U20-U22 (3U) |
| Rectifier modules | 6 (R1 to R6), 3 kW each |
| Redundancy | N+1: 5 active and 1 spare |
| Maximum output | 15 kW |
| Mains input | 3-phase 400 V AC |
| Busbar nominal voltage | 48 V DC |
| Busbar operating range | 44.0-52.0 V |
| Overvoltage protection cutoff | 54.2 V |
| Undervoltage protection cutoff | 40.5 V |
| Efficiency | 97.5 % at 50 % load |
| PMBus address | 0x03 (BMC to shelf) |
| PDB fuse | F2, 30 A, 80 V DC rated |

## 4. Rectifier arrangement

### 4.1 N+1 operation

The shelf runs an N+1 arrangement. N is the number of modules needed to carry the full load, and the shelf has one extra module as a spare. With six modules, five carry the load and one stands by. The five active modules together deliver up to 15 kW. The spare adds no output while the set is complete, but it takes over when an active module leaves the set.

When a rectifier reports an internal fault, the BMC records `0x4B10_PSU_RECT_FAIL` and the module drops out of the set. The remaining five modules carry the load and the rack stays up. After the first failure the shelf has no spare, so the replacement must happen as soon as possible.

### 4.2 Rectifier positions

| Position | Rating | Role |
|---|---|---|
| R1 | 3 kW | Active or spare, as assigned by the shelf |
| R2 | 3 kW | Active or spare, as assigned by the shelf |
| R3 | 3 kW | Active or spare, as assigned by the shelf |
| R4 | 3 kW | Active or spare, as assigned by the shelf |
| R5 | 3 kW | Active or spare, as assigned by the shelf |
| R6 | 3 kW | Active or spare, as assigned by the shelf |

> **NOTE:** Rectifier R3 is the module that reports repeated PMBus CRC errors under `0x99A1_PMBUS_CRC_ERR`. A CRC error on R3 is a Minor condition. Log it and reseat R3 during the next maintenance window, as the fault table directs.

## 5. The 48 V DC busbar

### 5.1 Busbar voltage

The busbar nominal voltage is 48 V DC and the operating range is 44.0 to 52.0 V. The overvoltage protection cutoff is 54.2 V and the undervoltage protection cutoff is 40.5 V. A voltage above 54.2 V is recorded as `0x4A7B_VRM_OVERVOLT`. A voltage below 40.5 V is recorded as `0x4A7C_VRM_UNDERVOLT`.

### 5.2 Busbar ripple

Busbar ripple is the residual AC component on the DC busbar. The limit is 50 mV peak-to-peak. A ripple above this limit is recorded as `0x7D02_BUSBAR_RIPPLE`, which is a Warning. The shelf keeps operating, but ripple above the limit points to a degraded rectifier output stage or a poor busbar connection.

### 5.3 Busbar connections

Every busbar connection is torqued to 14 N·m. Over-torque and under-torque both cause damage. An under-torqued connection heats up and can fail. An over-torqued connection can crack the busbar or strip the thread.

> **CAUTION:** Use a calibrated torque driver for every busbar connection and set it to 14 N·m. Do not use an impact driver on a busbar connection.

## 6. Power distribution board and fuse F2

### 6.1 Function

The PDB carries fuse F2, which protects the 48 V DC busbar from over-current. The fuse is rated 30 A and 80 V DC. When the fuse opens, the shelf records `0x7D01_PDB_FUSE_BLOWN`.

> **NOTE:** The physical position of fuse F2 on the PDB is not defined in the engineering specification. Identify the holder from the PDB label and the rack build drawing before you start section 8.2.

### 6.2 Fuse rules

- Replace the fuse only with a 30 A, 80 V DC rated part.
- Never replace the fuse with a different rating, a wire link or a temporary jumper.
- Never replace the fuse until you have found the cause of the over-current. A new fuse opens again if the cause remains.
- Check the holder contacts for discolouration, pitting or heat damage before you fit the new fuse.

> **WARNING:** A blown F2 fuse often accompanies a short on the busbar or a sled that has drawn excessive current. Do not re-energise the shelf until you have measured the busbar, as section 8.2 describes.

## 7. LED states for power

### 7.1 PWR LED

The power state of each sled is reported by the front-panel PWR LED. Figure F2 shows the complete front-panel LED legend. Use the figure when you need to compare the PWR LED with the NET, BMC and ID LEDs.

![Figure F2: Front-panel LED legend: PWR, NET, BMC and ID LEDs](figures/F2_front_panel_led_legend.png)

*Figure F2: Front-panel LED legend: PWR, NET, BMC and ID LEDs.*

| PWR LED state | Meaning | Power fault codes that list this state |
|---|---|---|
| Solid green | Normal operation: 48 V busbar present, ripple below 50 mV, all rails good | `0x7D02_BUSBAR_RIPPLE` (Warning), `0x99A1_PMBUS_CRC_ERR` (Minor) |
| Blinking amber (1 Hz) | Thermal warning: temperature above 75 C. Fans forced to 100 %, CPU throttled | `0x4A7C_VRM_UNDERVOLT`, `0x4B10_PSU_RECT_FAIL` |
| Solid red | Critical fault: rail overvoltage or short. Immediate power cutoff | `0x4A7B_VRM_OVERVOLT`, `0x4A80_VRM_OVERCURRENT`, `0x4B22_PSU_AC_LOSS`, `0x7D01_PDB_FUSE_BLOWN` |
| Off | No 48 V input, or the sled is not seated | Not listed in the fault table |

### 7.2 Reading the LED with the SEL

The PWR LED is a summary, not a diagnosis. A blinking amber PWR LED can mean a thermal warning, a busbar undervoltage or a rectifier failure. A solid red PWR LED can mean an overvoltage, an over-current, an AC loss or a blown fuse. Read the SEL entry before you choose a procedure. The SEL entry names the fault code and an identifier such as SEL-0110. Use the code, not the LED colour, to select the procedure in section 8.

> **NOTE:** The LED legend and the fault table do not agree on every state. The legend defines solid green as "ripple below 50 mV", but the fault table lists solid green for `0x7D02_BUSBAR_RIPPLE`, which is a ripple-exceeded condition. Use the SEL entry and a measured ripple value to confirm the state.

## 8. Power faults and replacement procedures

### 8.1 Fault table

The table below lists the seven power-related fault codes, with the values from the engineering specification. The procedures in section 8.2 onward give the full steps.

| Fault code | Subsystem | Severity | LED state | Root cause | First remediation step | SEL event |
|---|---|---|---|---|---|---|
| `0x4A7B_VRM_OVERVOLT` | Power VRM | Critical | Solid red PWR | Input voltage exceeded the 54.2 V cutoff on the 48 V busbar | Engage the secondary backup PSU; replace the PDB fuse (F2). Do not re-energise before measuring the busbar | SEL-0101 |
| `0x4A7C_VRM_UNDERVOLT` | Power VRM | Major | Blinking amber PWR | Busbar voltage fell below the 40.5 V undervoltage threshold | Check rectifier modules R1-R6 for a failed unit; reseat the module; verify AC feed on phase L2 | SEL-0102 |
| `0x4A80_VRM_OVERCURRENT` | Power VRM | Critical | Solid red PWR | Sled PoL stage drew more than 120 A on the 12 V rail | Remove the sled, inspect the PoL stage for a short, then replace the sled if the fault repeats | SEL-0103 |
| `0x4B10_PSU_RECT_FAIL` | Power shelf | Major | Blinking amber PWR | A rectifier module reported an internal fault and dropped out of the N+1 set | Hot-swap the failed rectifier (module LED is red). Rack stays up on the remaining 5 modules | SEL-0110 |
| `0x4B22_PSU_AC_LOSS` | Power shelf | Critical | Solid red PWR | Loss of 3-phase AC mains on one or more phases | Check the upstream breaker and PDU; confirm all three phases L1-L3 are present before restart | SEL-0111 |
| `0x7D01_PDB_FUSE_BLOWN` | Power VRM | Major | Solid red PWR | Power distribution board fuse F2 is open | Replace fuse F2 (30 A, 80 V DC rated) after finding the cause of the over-current | SEL-0120 |
| `0x7D02_BUSBAR_RIPPLE` | Power VRM | Warning | Solid green PWR | Busbar ripple exceeded 50 mV peak-to-peak | Inspect rectifier output capacitors and busbar connections for corrosion | SEL-0121 |

The codes `0x4A7B_VRM_OVERVOLT` and `0x4A7C_VRM_UNDERVOLT` are opposite conditions on the same busbar. Read the descriptor before you choose a procedure.

### 8.2 Rectifier module replacement (`0x4B10_PSU_RECT_FAIL`, or `0x4A7C_VRM_UNDERVOLT` with a faulty rectifier)

**Entry conditions:** The SEL records `0x4B10_PSU_RECT_FAIL` or `0x4A7C_VRM_UNDERVOLT`. The PWR LED shows blinking amber, or a rectifier indicator is red. No second rectifier is out of the set.

**Steps**

1. Read the SEL entry and identify the failed rectifier by its position, R1 to R6. Record the position and the SEL identifier in the work order.
2. Confirm that no other rectifier is out of the set. If a second rectifier is faulty, stop and escalate to an engineer.
3. Put on the PPE in section 2.1 and connect the ESD wrist strap.
4. Apply lock-out and tag-out to the AC feeder, as section 2.3 describes. Verify that the feeder is isolated.
5. Locate the failed module by its position and its red indicator. Confirm that the position matches step 1.
6. Release the module retention mechanism, as marked on the module label. Withdraw the module slowly and support its 6.5 kg weight with both hands.
7. Inspect the module connector and the shelf slot for burn marks, bent pins, corrosion and debris. Do not install a module into a damaged slot. Escalate slot damage to an engineer.
8. Place the failed module in an anti-static bag and label it with the position, the SEL identifier and the work order number.
9. Check that the replacement module is rated 3 kW. Align it with the empty slot, insert it slowly and seat it fully until the retention mechanism engages.
10. Remove the lock-out and tag-out from the AC feeder, in reverse order, and restore the feeder.
11. Check that the module indicator is not red, that the PWR LED returns to solid green, and that the shelf shows five active rectifiers and one spare.
12. Complete the verification in section 8.6.
13. Record the old and new module serial numbers and the time of the swap in the work order.

> **WARNING:** Do not replace a second rectifier until the replacement from step 9 has been verified in step 11. Each swap completes in full before the next one starts.

### 8.3 PDB fuse F2 replacement (`0x7D01_PDB_FUSE_BLOWN`, or `0x4A7B_VRM_OVERVOLT`)

**Entry conditions:** The SEL records `0x7D01_PDB_FUSE_BLOWN` or `0x4A7B_VRM_OVERVOLT`. The PWR LED on the sleds shows solid red. The fuse F2 holder is accessible and its label is legible.

**Steps**

1. Read the SEL entry and record the identifier, for example SEL-0120.
2. Put on the PPE in section 2.1 and connect the ESD wrist strap.
3. Apply lock-out and tag-out to the AC feeder. Verify that the feeder is isolated.
4. Find the cause of the over-current before you replace the fuse. Check the SEL for `0x4A80_VRM_OVERCURRENT` entries from the sleds, and check each suspect sled for a short in its PoL stage, as section 8.5 describes. Do not replace the fuse until the cause is removed.
5. Locate fuse F2 on the PDB and confirm its position against the PDB label and the rack build drawing.
6. Remove the failed fuse from its holder and check that its marking is 30 A, 80 V DC.
7. Inspect the holder contacts. If they show discolouration, pitting or heat damage, do not reuse the holder. Escalate it to an engineer.
8. Fit the replacement fuse, which must be 30 A and 80 V DC rated.
9. If any busbar connection was loosened, torque it to 14 N·m with a calibrated torque driver.
10. Measure the busbar before you re-energise the shelf. Confirm that the voltage is inside the 44.0-52.0 V range, with a nominal value of 48 V, and that no short is present. Escalate any reading outside the range.
11. Remove the lock-out and tag-out and restore the feeder.
12. Check that each sled PWR LED returns to solid green and that no new `0x4A7B_VRM_OVERVOLT` or `0x7D01_PDB_FUSE_BLOWN` entry appears in the SEL.
13. Record the replacement, the fuse batch number and the time of the swap in the work order.

> **WARNING:** The fault table for `0x4A7B_VRM_OVERVOLT` states "Do not re-energise before measuring the busbar". A busbar above the 54.2 V cutoff trips the shelf again, and a busbar with a short can deliver more than 300 A.

The overvoltage remediation also lists "Engage the secondary backup PSU" as the first step. Follow the site runbook for the secondary backup supply. Do not improvise a backup connection, and record the backup action in the work order.

### 8.4 Busbar ripple investigation (`0x7D02_BUSBAR_RIPPLE`)

**Entry conditions:** The SEL records `0x7D02_BUSBAR_RIPPLE`. The PWR LED on the sleds shows solid green, because the fault is a Warning. The shelf keeps operating, but do not wait for the next maintenance window if the ripple reading is rising.

**Steps**

1. Read the SEL entry and record the identifier, for example SEL-0121.
2. Put on the PPE in section 2.1 and connect the ESD wrist strap.
3. Measure the busbar ripple with an instrument rated for the busbar voltage and record the peak-to-peak value. A value above 50 mV peak-to-peak confirms the fault.
4. Inspect each busbar connection for corrosion, discolouration and looseness. Look for green or white deposits on the connection faces.
5. Apply lock-out and tag-out to the AC feeder and verify that the feeder is isolated.
6. Check the torque of each busbar connection against 14 N·m with a calibrated torque driver. Record each reading that differs from the target.
7. Inspect the rectifier output capacitors when a module is out of the shelf, using section 8.2. Do not open a rectifier module in the field. Escalate a module with a suspect capacitor to an engineer.
8. Remove the lock-out and tag-out and restore the feeder.
9. Measure the busbar ripple again and record the value. The ripple must be below 50 mV peak-to-peak.
10. If the ripple remains above the limit, escalate to an engineer. Do not replace the shelf without an engineering decision.

> **CAUTION:** Do not clean a busbar connection with an abrasive or with a solvent that leaves residue. Record corrosion as a finding in the work order, even if the ripple value falls after cleaning.

### 8.5 Sled removal after PoL over-current (`0x4A80_VRM_OVERCURRENT`)

**Entry conditions:** The SEL records `0x4A80_VRM_OVERCURRENT` for a specific sled, meaning its PoL stage drew more than 120 A on the 12 V rail. The PWR LED on that sled shows solid red.

**Steps**

1. Read the SEL entry and record the sled number, the rack units and the identifier, for example SEL-0103.
2. Put on the PPE in section 2.1 and connect the ESD wrist strap.
3. Shut down the sled through the BMC, using Redfish or bmc-cli as the *BMC, Redfish and CLI Operations Guide* describes.
4. Confirm through the BMC that the sled has powered down before you remove it.
5. Remove the sled from the rack. It weighs 21 kg, so two people must lift it. Keep it level and support it with both hands.
6. Place the sled on a bench with the top cover facing up. Inspect the PoL stage for a short, including burn marks, melted components and debris.
7. Do not power the sled on the bench.
8. If the PoL stage shows a short, escalate the sled to an engineer. If there is no visible damage, reinstall the sled once the cause is identified.
9. Reinstall the sled and confirm that its PWR LED returns to solid green.
10. If `0x4A80_VRM_OVERCURRENT` returns, replace the sled. This is the remedy stated in the engineering specification.

> **CAUTION:** A sled that has recorded `0x4A80_VRM_OVERCURRENT` must not return to service without inspection. A repeated over-current event on the same sled is a reason to replace the sled.

### 8.6 Post-replacement verification

After any procedure in this section, verify the shelf with the checks below. Do not close the work order until every check is complete.

| Check | Expected result |
|---|---|
| PWR LED on each sled | Solid green |
| Busbar voltage | Inside 44.0-52.0 V, nominal 48 V |
| Busbar ripple | Below 50 mV peak-to-peak |
| Rectifier count | Five active modules and one spare |
| Rectifier indicators | No red indicator on any module |
| SEL entries | No new power fault codes after the work |
| BMC LED on each sled | Blinking blue at 0.5 Hz |
| Busbar connections | Torqued to 14 N·m where loosened |

### 8.7 AC mains loss recovery (`0x4B22_PSU_AC_LOSS`)

**Entry conditions:** The SEL records `0x4B22_PSU_AC_LOSS`. The fault is Critical and the PWR LED shows solid red. The shelf has lost mains on one or more phases.

**Steps**

1. Read the SEL entry and record the identifier, for example SEL-0111.
2. Put on the PPE in section 2.1 and connect the ESD wrist strap.
3. Check the upstream breaker and the PDU for the shelf. Look for a tripped breaker, an open switch or a damaged feed.
4. Apply lock-out and tag-out to the feeder before you touch the breaker or the PDU. Verify that the feeder is isolated.
5. Measure each phase, L1, L2 and L3, at the input terminals.
6. If any phase is missing, escalate to the facility electrical team before you restore the feeder. Do not connect a single-phase supply to the shelf.
7. Remove the lock-out and tag-out only after all three phases are confirmed present, then restore the feeder.
8. Check that the shelf starts and that the PWR LED changes from solid red to solid green.
9. Check the SEL for new entries. Confirm that no new `0x4B10_PSU_RECT_FAIL` entries appear after the restart.
10. Record the phase readings and the time of the restart in the work order.

> **WARNING:** Do not restart the shelf with a missing phase. The fault table requires all three phases, L1 to L3, to be present before restart.

## 9. Related documents

| Document | Read it for |
|---|---|
| *Preventive Maintenance and Safety Manual* | PPE, lock-out and tag-out, torque practice and scheduled busbar checks |
| *Fault Code Reference and Troubleshooting Flowcharts* | Full troubleshooting flowcharts, including the blinking amber PWR path, and the complete code list |
| *BMC, Redfish and CLI Operations Guide* | Redfish paths, bmc-cli commands, resets and the PMBus fault `0x99A0_PSU_COMM_LOST` |
| *AOR-3 System Overview and Architecture* | System-level power path and rack layout |

## Frequently asked questions

**Q1. Can the rack keep running after one rectifier fails?**

A. Yes. The PS-3000 uses five active rectifiers and one spare. When one module reports `0x4B10_PSU_RECT_FAIL`, the remaining five carry the load and the rack stays up. Replace the failed module as soon as possible, because the shelf has no spare while the module is out.

**Q2. Why must I lock out the AC feeder for a rectifier swap if the module is hot-swappable?**

A. The engineering specification requires lock-out and tag-out of the AC feeder before you touch rectifier connections. The hot-swap keeps the rack powered on the other modules, but the module connector is still a live connection. Apply the rule for every module swap.

**Q3. Can I fit a higher-rated fuse to stop F2 from blowing?**

A. No. Fuse F2 is rated 30 A and 80 V DC. A higher-rated fuse removes the protection the busbar depends on. Find and remove the cause of the over-current first, as section 8.3 describes.

**Q4. Why measure the busbar before re-energising after a fuse replacement?**

A. The fault table for `0x4A7B_VRM_OVERVOLT` states "Do not re-energise before measuring the busbar". A busbar above the 54.2 V cutoff trips the shelf again, and a short on the busbar can deliver more than 300 A.

**Q5. Is a blinking amber PWR LED always a rectifier fault?**

A. No. The LED legend defines blinking amber as a thermal warning above 75 C, and the fault table also lists it for `0x4A7C_VRM_UNDERVOLT` and `0x4B10_PSU_RECT_FAIL`. The LED state is shared, so read the SEL entry to find the fault code before you choose a procedure.
