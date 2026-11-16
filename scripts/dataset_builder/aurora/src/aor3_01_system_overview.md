# AOR-3 System Overview and Architecture

Document ref: aor3_01_system_overview | Revision: Rev 3.2 (2026-03) | Classification: Fictional training material

## 1. Introduction

This manual describes the Aurora Open Rack AOR-3 at system level. It explains how the rack is laid out, which components occupy which rack units, how power and network traffic move through the rack, and how the management plane observes the hardware. It is the entry point to the Aurora Systems service library. Read it first, then move to the component manual that covers the procedure you need.

The AOR-3 is a fictional training product. Its layout follows public Open Compute Project Open Rack V3 concepts, but every value in this manual is defined for this exercise and must not be applied to real equipment.

The manual is written for three audiences:

- Level 1 technicians, who identify components, read the front-panel LEDs and locate the rack unit named in a work order.
- Level 2 technicians, who replace modules and perform the procedures in the component manuals.
- Engineers, who plan capacity, network changes and firmware baselines.

Every numeric value in this manual comes from the AOR-3 engineering specification, Rev 3.2 (2026-03). If a component manual gives more detail on the same subject, the component manual governs the procedure.

### 1.1 Conventions

Rack units are written as U01 to U42, counted from the bottom of the rack. Temperatures are in degrees Celsius and written as "75 C". Voltages are DC unless marked AC. Fault codes are written in full with their hex value, subsystem and descriptor, for example `0x4A7B_VRM_OVERVOLT`. Use the full code when you search the System Event Log (SEL), when you open a ticket and when you consult the *Fault Code Reference and Troubleshooting Flowcharts*.

Safety callouts use three levels:

> **WARNING:** A condition that can cause death, serious injury or damage to the rack if the instruction is not followed.

> **CAUTION:** A condition that can damage a module, a cable or a fuse if the instruction is not followed.

> **NOTE:** Information that helps you complete a task correctly.

## 2. Product summary

### 2.1 Key specifications

The table below lists the system-level values for the reference configuration of the AOR-3 Rev 3.2.

| Parameter | Value |
|---|---|
| Product | Aurora Open Rack AOR-3, Rev 3.2 |
| Vendor | Aurora Systems |
| Compute sleds | 9 x Compute Sled CS-2U, located at U02-U19 |
| Power shelf | 1 x Power Shelf PS-3000, located at U20-U22 |
| Top-of-rack switch | 1 x Top-of-Rack Switch AS-100G, located at U23 |
| Patch panel | QSFP28 breakout panel, located at U24 |
| Reserved space | U25-U42, reserved for future expansion |
| Fan wall | FW-6, six fan modules at the rear of U02-U19 |
| Mains input | 3-phase 400 V AC |
| Busbar | 48 V DC nominal, operating range 44.0-52.0 V |
| Power shelf output | Up to 15 kW from five active 3 kW rectifier modules |
| Switch capacity | 3.2 Tbps aggregate, 32 QSFP28 ports at 100 GbE |
| Management | OpenBMC 2.14, Redfish 1.17, bmc-cli |

### 2.2 Design principles

**Separated power and data.** Power enters through the PS-3000 and leaves as a 48 V DC busbar. Each compute sled converts that voltage to 12 V locally in its point-of-load (PoL) stage. Network traffic never travels on the power path.

**Redundancy at the shelf.** The PS-3000 holds six rectifier modules in an N+1 arrangement, five active and one spare. A single rectifier failure does not stop the rack, as section 5.2 explains.

**Isolated management.** Every sled BMC uses a dedicated out-of-band network on VLAN 102. The switch management port MGMT0 is never routed through the QSFP28 fabric, so a data-plane fault does not remove the ability to observe the hardware.

**Standard interfaces.** The BMC exposes the same information through Redfish and through the bmc-cli tool. Both read the same System Event Log.

## 3. Rack layout

### 3.1 Rack elevation

Look at Figure F1 when you need to confirm which rack unit holds a given component, or when you plan where a new module or sled goes. Rack units are numbered from the bottom, so U01 is the lowest position.

![Figure F1: Rack elevation of the AOR-3 (U01 at the bottom)](figures/F1_rack_elevation.png)

*Figure F1: Rack elevation of the AOR-3 (U01 at the bottom).*

The table below gives the same information in text form. Use the text form when you write a work order, because it is easier to search.

| Rack units | Occupant | Notes |
|---|---|---|
| U01 | Cable management or blank panel | Lowest position |
| U02-U19 | Compute sleds CS-2U x 9 | Sled 1 at U02-U03 through sled 9 at U18-U19 |
| U20-U22 | Power shelf PS-3000 | Holds rectifier modules R1-R6 |
| U23 | Top-of-rack switch AS-100G | One 1U switch |
| U24 | Patch panel | QSFP28 breakout |
| U25-U42 | Reserved | Future expansion |

### 3.2 Compute sled positions

Each compute sled occupies two rack units. Sled numbers increase from the bottom of the rack to the top. Always record the sled number and the rack units together in a ticket.

| Sled | Rack units | Sled | Rack units |
|---|---|---|---|
| Sled 1 | U02-U03 | Sled 6 | U12-U13 |
| Sled 2 | U04-U05 | Sled 7 | U14-U15 |
| Sled 3 | U06-U07 | Sled 8 | U16-U17 |
| Sled 4 | U08-U09 | Sled 9 | U18-U19 |
| Sled 5 | U10-U11 | | |

> **NOTE:** The fan wall FW-6 is mounted at the rear of U02-U19. A fan fault at a given sled position must be serviced from the rear of the rack.

Keep every empty U position within U02-U24 covered with a blanking panel. The *Thermal and Cooling Manual* explains the airflow-blocked condition reported as `0x8F20_AIRFLOW_BLOCK`. Do not place equipment in U25-U42 without an engineering change.

## 4. Components

### 4.1 Component summary

The table below lists the main components of the AOR-3. The detailed specifications appear in the component manual named in the last column.

| Component | Designation | Rack units | Key specification | Manual |
|---|---|---|---|---|
| Compute sled | CS-2U | U02-U19 (nine sleds) | Two sockets, 16 DDR5 DIMM slots, two NVMe bays | *BMC, Redfish and CLI Operations Guide* |
| Power shelf | PS-3000 | U20-U22 | Six 3 kW rectifiers in N+1 | *Power Shelf PS-3000 Service Manual* |
| Fan wall | FW-6 | Rear of U02-U19 | Six hot-swappable fan modules | *Thermal and Cooling Manual* |
| Switch | AS-100G | U23 | 32 QSFP28 ports, MGMT0 and serial console | *Top-of-Rack Switch AS-100G Manual* |
| Management | OpenBMC | On each compute sled | Polls sensors every 2 seconds | *BMC, Redfish and CLI Operations Guide* |

### 4.2 Compute sled CS-2U

The compute sled is a dual-socket server in a 2U enclosure. Socket CPU0 serves DIMM slots A1-A8 and socket CPU1 serves DIMM slots B1-B8. The sled holds 16 DDR5-5600 RDIMM modules, up to 2048 GB in total, and two NVMe bays. It receives 48 V DC from the busbar and converts it to 12 V in its PoL stage. The sled consumes a typical 780 W and a maximum of 1100 W.

A sled weighs 21 kg. That is above the 18 kg two-person lift threshold, so two people must lift a sled.

### 4.3 Power shelf PS-3000

The power shelf is a 3U unit. It holds six hot-swappable 3 kW rectifier modules, R1 to R6, in an N+1 arrangement. It converts 3-phase 400 V AC mains into the 48 V DC busbar that feeds every sled. Section 5 gives the power architecture in outline. The *Power Shelf PS-3000 Service Manual* gives the full procedures.

### 4.4 Fan wall FW-6

The fan wall is a rear-mounted assembly of six hot-swappable fan modules, FM1 to FM6. Each module has a tachometer wire. The rated speed is 9000 RPM and the minimum speed is 2800 RPM. A module that reports less than 600 RPM is treated as failed. Each module moves 85 CFM. The swap time for a fan module is 30 seconds.

### 4.5 Top-of-rack switch AS-100G

The switch is a 1U device built on the Aurora TS-3200 switch ASIC, which has a capacity of 3.2 Tbps. It has 32 QSFP28 ports at 100 GbE, a 1 GbE out-of-band management port named MGMT0 (RJ45, 1GbE Base-T), and an RJ45 serial console at 115200 8N1. The first sixteen ports are uplinks and the last sixteen are server ports.

### 4.6 Baseboard management controller

Each compute sled has its own baseboard management controller (BMC) running OpenBMC 2.14 with Redfish 1.17. The BMC polls its sensors every 2 seconds, writes fault codes to the System Event Log, and drives the front-panel LEDs. The SEL holds up to 4096 entries. The BMC is therefore the first source of evidence for most fault investigations.

## 5. Power architecture

### 5.1 Power path

Power flows through the AOR-3 along a single path:

1. The facility delivers 3-phase 400 V AC to the rack through the upstream breaker and the PDU.
2. The PS-3000 rectifiers R1 to R6 convert the AC input to 48 V DC.
3. The 48 V DC busbar distributes the power to every sled. The busbar is protected at the power distribution board (PDB) by fuse F2.
4. Each compute sled converts 48 V to 12 V in its PoL stage.
5. The 12 V rail feeds the processors, memory, NVMe bays and the BMC.

Figure F3 shows the same path as a block diagram. Look at it when you need to decide which stage a fault belongs to.

![Figure F3: Power distribution from 400 V AC through the rectifiers to the 48 V busbar and the 12 V PoL stage](figures/F3_power_distribution_block.png)

*Figure F3: Power distribution: 400 V AC to rectifiers, 48 V busbar, 12 V PoL.*

### 5.2 Redundancy

The PS-3000 uses an N+1 arrangement. Five rectifier modules are active and one is a spare. With five active modules at 3 kW each, the shelf delivers up to 15 kW. If one rectifier reports an internal fault and leaves the set, the rack stays up on the remaining five modules. The fault is recorded as `0x4B10_PSU_RECT_FAIL`.

> **WARNING:** While one rectifier is out of service, the shelf has no spare. Replace the failed module at the first opportunity, and do not remove a second rectifier while the first is still out.

### 5.3 Thresholds

The table below lists the power thresholds that drive the fault codes in the power part of the library.

| Quantity | Threshold or value | Related fault code |
|---|---|---|
| Busbar nominal voltage | 48 V DC | Not applicable |
| Busbar operating range | 44.0-52.0 V | Not applicable |
| Overvoltage protection cutoff | 54.2 V | `0x4A7B_VRM_OVERVOLT` |
| Undervoltage protection cutoff | 40.5 V | `0x4A7C_VRM_UNDERVOLT` |
| PoL overcurrent on the 12 V rail | More than 120 A | `0x4A80_VRM_OVERCURRENT` |
| Busbar ripple limit | 50 mV peak-to-peak | `0x7D02_BUSBAR_RIPPLE` |
| PDB fuse F2 rating | 30 A, 80 V DC | `0x7D01_PDB_FUSE_BLOWN` |
| Shelf efficiency | 97.5 % at 50 % load | Not applicable |
| Shelf maximum output | 15 kW | Not applicable |

### 5.4 Energy hazard

The 48 V DC busbar is a high-energy source. It can deliver more than 300 A. Treat the busbar as a live, high-energy conductor at all times, even when the shelf reports a healthy state.

> **WARNING:** Do not place a metal tool across the busbar or across any two busbar connections. Use insulated tools and insulated gloves rated 1000 V.

## 6. Network overview

### 6.1 Leaf-spine topology

The AS-100G switch is the leaf for the rack. Its sixteen uplink ports connect to two 400G spine switches, SP-1 and SP-2. Its sixteen server ports connect to the compute sleds. Figure F7 shows the topology and the four VLANs that run over it.

![Figure F7: Leaf-spine topology with VLANs 101-104](figures/F7_network_topology_vlans.png)

*Figure F7: Leaf-spine topology with VLANs 101-104.*

### 6.2 Port groups

| Port group | Ports | Connects to | Notes |
|---|---|---|---|
| Uplinks | QSFP28_01 to QSFP28_16 | Spine switches SP-1 and SP-2 (2 x 400G) | Carries the data plane upward |
| Server ports | QSFP28_17 to QSFP28_32 | Compute sleds | Carries sled data traffic |
| Management | MGMT0 (RJ45, 1GbE Base-T) | Out-of-band management network | Carries only MGMT_VLAN_102 |
| Console | RJ45 serial, 115200 8N1 | Local serial console | Direct switch access |

The per-sled assignment of server ports is documented in the *Top-of-Rack Switch AS-100G Manual*. Do not assume a sled-to-port mapping from the port range alone. Confirm the mapping against that manual before you move a cable.

### 6.3 VLAN plan

| VLAN | Name | Purpose |
|---|---|---|
| 101 | PROD_DATA | Server data plane |
| 102 | MGMT_VLAN_102 | Out-of-band management (BMC and MGMT0) |
| 103 | STORAGE | NVMe-oF storage traffic |
| 104 | PXE_PROVISION | Bare-metal provisioning |

### 6.4 Management isolation rule

MGMT0 carries only MGMT_VLAN_102 on a dedicated 1 GbE Base-T link. It is never routed through the QSFP28 fabric. A technician who needs to reach a BMC during a data-plane outage uses MGMT0, not a server port.

Management traffic seen outside MGMT_VLAN_102 is a configuration error. The switch reports it as `0xC040_MGMT_VLAN_MISMATCH`. The remedy is to reconfigure the switch port to access VLAN 102 on MGMT0 and to check the trunk allowed list.

## 7. Management plane

### 7.1 Interfaces

The BMC offers two interfaces that read the same data.

- **Redfish:** The base path is `/redfish/v1`. Use Redfish when a script must query many sleds.
- **bmc-cli:** This command-line tool runs on the BMC. Use it for one-off tasks, such as exporting the SEL with `bmc-cli sel export` or restarting a service with `bmc-cli service restart sensord`.

Two reset commands are defined. The warm reset is `bmc-reset --warm` and the cold reset is `bmc-reset --cold`. The *BMC, Redfish and CLI Operations Guide* describes when to use each one.

> **CAUTION:** A BMC reset interrupts the management plane for the sled. Do not reset a BMC while a firmware update is in progress.

### 7.2 Telemetry and logging

The BMC polls every sensor every 2 seconds. A sensor reading that has not updated for more than 10 seconds triggers `0x6E01_SENSOR_STALE`. The BMC writes every fault event to the SEL, which holds 4096 entries. Each SEL entry carries an identifier such as SEL-0101. Use that identifier to move from a log entry to the matching troubleshooting step.

### 7.3 Front-panel LED summary

Every compute sled has four front-panel LEDs. The LED states are the first indication a technician sees, so learn them before you open the rack.

| LED | Position | State | Meaning |
|---|---|---|---|
| PWR (power and health) | 1 | Solid green | Normal operation: 48 V busbar present, ripple below 50 mV, all rails good |
| PWR | 1 | Blinking amber (1 Hz) | Thermal warning: temperature above 75 C, fans at 100 %, CPU throttled |
| PWR | 1 | Solid red | Critical fault, such as a rail overvoltage or short. Immediate power cutoff |
| PWR | 1 | Off | No 48 V input, or the sled is not seated |
| NET (network link) | 2 | Solid green | 100 GbE link up at full speed |
| NET | 2 | Blinking green | Link up with traffic present |
| NET | 2 | Solid amber | Link up but degraded to 25 GbE or 40 GbE |
| NET | 2 | Off | No link |
| BMC (heartbeat) | 3 | Blinking blue (0.5 Hz) | BMC healthy and polling sensors |
| BMC | 3 | Solid blue | BMC booting or firmware update in progress. Do not power cycle |
| BMC | 3 | Off | BMC unresponsive |
| ID (locator) | 4 | Solid white | Locator active. A technician or the BMC asked to identify this sled |
| ID | 4 | Off | Locator inactive |

> **NOTE:** The amber and red states of the PWR LED are shared between thermal, power and other subsystems. A blinking amber PWR LED does not identify its cause. Read the SEL entry before you choose a procedure.

## 8. Thermal overview

The AOR-3 uses warning and critical thresholds for each heat source. The BMC uses these thresholds.

| Location | Warning threshold | Critical threshold | Related fault codes |
|---|---|---|---|
| Inlet air | 35 C | 42 C | None in the fault table; see the *Thermal and Cooling Manual* |
| CPU | 75 C | 90 C | `0x8F10_TEMP_WARN`, `0x8F11_TEMP_CRIT` |
| Switch ASIC | 85 C | 95 C | `0xC055_SWITCH_ASIC_TEMP` |

The fan duty follows a fixed curve. The fans run at 30 % at 30 C, 55 % at 50 C and 100 % at 75 C and above. The *Thermal and Cooling Manual* gives the full curve.

If a CPU reaches 90 C, the BMC records `0x8F11_TEMP_CRIT` and begins an emergency shutdown of the sled. Do not restart the sled until it has cooled for 10 minutes and the fan wall and cold-aisle temperature have been verified.

## 9. Firmware baseline

Firmware must be matched across the BIOS, the BMC and the switch operating system. The matrix below lists the combinations in the compatibility table of the release notes. The *Release Notes and Firmware Compatibility* document contains the full history.

| BIOS | BMC | Switch OS (AOS) | Status |
|---|---|---|---|
| BIOS 1.8.0 | BMC 2.12.x | AOS 5.1 | Legacy. Missing watchdog fix (`0x9A05`) |
| BIOS 1.9.2 | BMC 2.14.3 | AOS 5.2 | Recommended baseline for AOR-3 Rev 3.2 |
| BIOS 2.0.0 | BMC 2.14.3 | AOS 5.3 | Adds DDR5 retraining improvements (`0x10F0`) |
| BIOS 2.0.0 | BMC 2.13.x | AOS 5.3 | Not supported. Triggers `0x9A10_BMC_FW_MISMATCH` |

## 10. Fault code overview

A fault code has three parts: a four-digit hex identifier, a subsystem name and a descriptor. For example, `0x4A7B_VRM_OVERVOLT` identifies an overvoltage event in the VRM subsystem. The reference set defines thirty fault codes. The table below groups them by subsystem.

| Subsystem | Fault codes | Count |
|---|---|---|
| Power VRM | `0x4A7B`, `0x4A7C`, `0x4A80`, `0x7D01`, `0x7D02` | 5 |
| Power shelf | `0x4B10`, `0x4B22` | 2 |
| Thermal | `0x8F01`, `0x8F02`, `0x8F10`, `0x8F11`, `0x8F20` | 5 |
| PMBus | `0x99A0`, `0x99A1` | 2 |
| BMC | `0x9A05`, `0x9A10`, `0x6E01` | 3 |
| DDR5 Memory | `0x10E4`, `0x10E5`, `0x10F0` | 3 |
| Storage | `0x2B30`, `0x2B31` | 2 |
| Network PHY | `0xC029`, `0xC02A`, `0xC040`, `0xC055` | 4 |
| Security | `0x6E10`, `0x6E20` | 2 |
| Liquid cooling | `0x5F01`, `0x5F02` | 2 |

The power-related codes are described in the *Power Shelf PS-3000 Service Manual*. The complete list, with severity, LED state and remediation, appears in the *Fault Code Reference and Troubleshooting Flowcharts*.

Some codes look alike on purpose. `0x4A7B_VRM_OVERVOLT` and `0x4A7C_VRM_UNDERVOLT` are opposite conditions on the busbar. `0x10E4_ECC_MULTI_BIT` halts the node, while `0x10E5_ECC_SINGLE_BIT` allows continued operation. Read the descriptor before you choose a remedy.

## 11. Maintenance overview

Preventive maintenance is organised by interval. The durations are planning estimates only and do not replace the procedure in the component manual.

| Task | Interval | Role | Estimated duration (min) |
|---|---|---|---|
| Visual LED and cable inspection | Weekly | Technician L1 | 15 |
| Clean fan wall filters and check dust | Monthly | Technician L1 | 30 |
| Optical transceiver clean and inspect | Quarterly | Technician L2 | 45 |
| Rectifier module load test | Quarterly | Technician L2 | 60 |
| BMC and BIOS firmware review | Semi-annual | Engineer | 90 |
| Busbar torque check (14 N·m) | Annual | Engineer | 120 |
| Full thermal survey with IR camera | Annual | Engineer | 180 |

The busbar torque check is the only annual task that touches a power connection. It must be performed with the shelf isolated. The full procedure is in the *Preventive Maintenance and Safety Manual*.

## 12. Related documents

| Document | Use it for |
|---|---|
| *Power Shelf PS-3000 Service Manual* | Rectifiers, busbar, PDB fuse F2 and power faults |
| *Thermal and Cooling Manual* | Fan wall, temperature thresholds and airflow |
| *Top-of-Rack Switch AS-100G Manual* | Port map, uplinks, server ports and switch faults |
| *BMC, Redfish and CLI Operations Guide* | Redfish, bmc-cli, resets and the SEL |
| *Fault Code Reference and Troubleshooting Flowcharts* | Lookup of every code and its troubleshooting path |
| *Preventive Maintenance and Safety Manual* | PPE, lock-out and tag-out, and scheduled tasks |
| *Release Notes and Firmware Compatibility* | Firmware history and the compatibility matrix |

## Frequently asked questions

**Q1. Which rack units are populated in the reference configuration?**

A. U01 holds a cable management or blank panel. U02 to U19 hold the nine compute sleds, U20 to U22 hold the PS-3000 power shelf, U23 holds the AS-100G switch and U24 holds the patch panel. U25 to U42 are reserved.

**Q2. How do I find the position of a given compute sled?**

A. Sled numbers increase from the bottom of the rack. Sled 1 occupies U02 and U03, and each following sled occupies the next two rack units, up to sled 9 at U18 and U19.

**Q3. Can the rack keep running if one rectifier fails?**

A. Yes. The PS-3000 has five active rectifier modules and one spare. If one module reports `0x4B10_PSU_RECT_FAIL`, the rack continues on the remaining five modules. Replace the failed module promptly, because the shelf has no spare while the module is out.

**Q4. Why is MGMT0 not connected to the QSFP28 fabric?**

A. MGMT0 carries only MGMT_VLAN_102 on a dedicated 1 GbE Base-T link. Keeping management traffic off the data fabric means that a data-plane fault does not remove the ability to reach the BMCs and the switch.

**Q5. What does a blinking blue BMC LED mean?**

A. A blinking blue BMC LED at 0.5 Hz shows that the BMC is healthy and polling sensors. A solid blue BMC LED shows that the BMC is booting or that a firmware update is in progress. Do not power cycle the sled in that state.
