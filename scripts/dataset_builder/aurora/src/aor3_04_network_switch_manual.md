# Top-of-Rack Switch AS-100G Manual

Document ref: aor3_04_network_switch_manual | Revision: Rev 3.2 (2026-03) | Classification: Fictional training material

## 1. Scope and intended readers

This manual describes the Top-of-Rack Switch AS-100G, the 1U 100 GbE switch that sits in position U23 of the Aurora Open Rack AOR-3. It covers the port layout, the out-of-band management network, the VLAN plan, the leaf-spine connectivity of the rack, the network fault codes that the switch and the sled BMCs write to the System Event Log (SEL), and the firmware baseline. It is written for Technician L1 and Technician L2 staff and for the network engineers who support the rack.

The manual assumes that the reader has completed the general rack orientation in *AOR-3 System Overview and Architecture*. For the fan trays and the switch thermal limits see *Thermal and Cooling Manual*. For BMC commands and Redfish paths see *BMC, Redfish and CLI Operations Guide*. For firmware pairings see *Release Notes and Firmware Compatibility*. For scheduled optical cleaning see *Preventive Maintenance and Safety Manual*.

> **NOTE:** Every numeric value in this manual is taken from the AOR-3 engineering specification for Revision 3.2. Port numbers, VLAN identifiers and fault codes must be quoted exactly. Where the specification does not define a value, this manual does not supply one.

## 2. Switch overview

The AS-100G is built on the Aurora TS-3200 switch ASIC, which provides 3.2 Tbps of aggregate port capacity. The switch has 32 QSFP28 ports, each running at 100 GbE. It also has two management paths that are kept separate from the data ports:

- **MGMT0**, a dedicated out-of-band management port. It is an RJ45 connector running 1 GbE Base-T.
- **Serial console**, an RJ45 serial port with settings of 115200 baud, 8 data bits, no parity and 1 stop bit (115200 8N1).

The switch runs Aurora switch operating system (AOS). The firmware compatibility matrix in section 8 lists the AOS releases that are supported with each BIOS and BMC build.

**Table 2-1. AS-100G key specifications**

| Parameter | Value |
|---|---|
| Position | U23 |
| Switch ASIC | Aurora TS-3200 |
| Aggregate port capacity | 3.2 Tbps |
| Data ports | 32 x QSFP28, 100 GbE each |
| Management port | MGMT0, RJ45, 1 GbE Base-T |
| Management VLAN | MGMT_VLAN_102 |
| Serial console | RJ45, 115200 8N1 |
| Uplink ports | QSFP28_01 to QSFP28_16 |
| Server ports | QSFP28_17 to QSFP28_32 |

## 3. QSFP28 port map

The 32 QSFP28 ports are split into two groups of 16. The first group, QSFP28_01 to QSFP28_16, is the uplink group. These ports connect the rack to the spine layer. The second group, QSFP28_17 to QSFP28_32, is the server group, which connects the compute sleds in the rack. Figure F4 shows the port map on the switch face, including the uplink group, the server group, the MGMT0 port and the serial console. Use Figure F4 when you need to find a port physically, or to check that a cable is in the group it should be in.

![Figure F4: AS-100G port map: QSFP28 uplinks, server ports, MGMT0 and console](figures/F4_switch_port_map.png)

*Figure F4: AS-100G port map: QSFP28 uplinks, server ports, MGMT0 and console.*

**Table 3-1. Port groups**

| Group | Port range | Number of ports | Connects to | Speed |
|---|---|---|---|---|
| Uplinks | QSFP28_01 to QSFP28_16 | 16 | Spine switches SP-1 and SP-2 | 100 GbE |
| Server ports | QSFP28_17 to QSFP28_32 | 16 | Compute sleds CS-2U | 100 GbE |
| Management | MGMT0 | 1 | Out-of-band management network (MGMT_VLAN_102) | 1 GbE Base-T |
| Console | Serial RJ45 | 1 | Local technician laptop | 115200 8N1 |

### 3.1 Port assignment to sleds

The specification gives the port ranges for the sled-facing group, but it does not give a fixed formula that maps each of the nine compute sleds to a specific server port in this revision. Do not work out a port for a sled by counting. Take the port assignment from the cabling record for the rack, and confirm the physical position of the cable against Figure F4.

### 3.2 Transceivers and cables

The QSFP28 cages accept optical transceivers and direct-attach copper (DAC) cables. Both must be rated for 100G operation. The degraded-link code 0xC02A_ETH_PHY_DEGRADED specifically requires the transceiver to be verified as rated for 100G, and it names the DAC cable as the first item to replace. A link that negotiates a slower speed should be checked as a cable or transceiver question first, as the remediation for 0xC02A_ETH_PHY_DEGRADED shows.

> **WARNING:** Do not connect a transceiver or cable that is not rated for 100G to any QSFP28 port. A rate mismatch can produce a link that comes up at a lower speed, and it can hide a fault that is only found later.

## 4. Management network: MGMT0 and MGMT_VLAN_102

MGMT0 is the dedicated out-of-band management port of the switch. It carries only MGMT_VLAN_102, which is the VLAN used for out-of-band management of the BMCs and the switch. MGMT0 is never routed through the QSFP28 fabric. Traffic on the QSFP28 ports cannot reach the management network through MGMT0, and management traffic cannot leave MGMT0 onto the data fabric. This separation is intentional. It means that a data-plane failure does not remove the ability to manage the rack, and a management problem does not disturb the data ports.

The serial console is the local path to the switch when MGMT0 is not available. Connect a laptop to the console RJ45 port and set the terminal to 115200 baud, 8 data bits, no parity and 1 stop bit. Use the console to check the switch state, to confirm the VLAN on MGMT0, and to recover the management path if the MGMT0 link has been lost.

**Procedure: first management check on a new rack**

1. Connect the MGMT0 cable to the management network. Confirm that the link is up before you continue.
2. Connect to the serial console with the settings in section 4 if you need local access.
3. Check that MGMT0 is in MGMT_VLAN_102. Management traffic seen outside this VLAN produces 0xC040_MGMT_VLAN_MISMATCH.
4. Confirm that the BMCs in the rack can be reached on MGMT_VLAN_102. The sled BMCs use this VLAN for their out-of-band management, as described in *BMC, Redfish and CLI Operations Guide*.
5. Record the MGMT0 address and the switch serial number on the rack record. Do not record the address on any shared document without the approval of the rack owner.

> **CAUTION:** MGMT0 is a 1 GbE port and is not a data path. Do not move production traffic onto MGMT0 to relieve a congested data port.

## 5. VLAN plan

The rack uses four VLANs. Table 5-1 lists them. The VLAN identifiers and names are the values used in every AOR-3 configuration and in every fault code that refers to them. Do not rename a VLAN on one switch without updating the rest of the rack, and do not reuse a VLAN identifier for another purpose.

**Table 5-1. VLAN table**

| VLAN ID | VLAN name | Purpose |
|---|---|---|
| 101 | PROD_DATA | Server data plane |
| 102 | MGMT_VLAN_102 | Out-of-band management (BMC, MGMT0) |
| 103 | STORAGE | NVMe-oF storage traffic |
| 104 | PXE_PROVISION | Bare-metal provisioning |

VLAN 102 has a special role. It is the only VLAN carried on MGMT0, and it is the VLAN that the BMC management network uses. VLANs 101, 103 and 104 belong to the data fabric and must not be carried onto MGMT0. When a port is configured as a trunk, the allowed list must include the VLANs the port needs and no others. Check the trunk allowed list whenever you investigate a VLAN mismatch, because the remediation for 0xC040_MGMT_VLAN_MISMATCH includes that check.

> **NOTE:** The specification does not list which VLANs are allowed on each individual server port. Use the rack design record for the per-port VLAN assignment, and do not infer it from the VLAN table alone.

## 6. Leaf-spine topology

The AOR-3 rack uses a leaf-spine design. The AS-100G is the leaf switch for the rack, and the spine layer is formed by two 400G spine switches, SP-1 and SP-2. Each leaf connects to both spines through its uplink group, QSFP28_01 to QSFP28_16. The sleds connect to the leaf through the server group, QSFP28_17 to QSFP28_32. Figure F7 shows the topology and the four VLANs in one diagram. Use it when you explain a fault to another team, or when you need to see which path a VLAN takes between the sleds and the spines.

![Figure F7: Leaf-spine topology with VLANs 101-104](figures/F7_network_topology_vlans.png)

*Figure F7: Leaf-spine topology with VLANs 101-104.*

**Table 6-1. Fabric roles**

| Device or port group | Role | Connects to | Carries |
|---|---|---|---|
| AS-100G (U23) | Leaf (top-of-rack) switch | Spine switches SP-1 and SP-2; compute sleds CS-2U | VLANs 101, 103, 104; VLAN 102 on MGMT0 |
| SP-1 and SP-2 | Spine switches, 400G | Leaf uplinks QSFP28_01 to QSFP28_16 | Data fabric |
| QSFP28_01 to QSFP28_16 | Uplinks | Spine layer | Data fabric |
| QSFP28_17 to QSFP28_32 | Server ports | Compute sleds CS-2U | Data fabric |
| MGMT0 | Out-of-band port | Management network | MGMT_VLAN_102 only |

The management network is a separate path from the leaf-spine fabric. A fault on the fabric does not automatically remove management access, provided that MGMT0 is still connected to the management network. The reverse is also true: a management problem on MGMT0 does not change the state of the data links.

## 7. Network fault codes and procedures

The network fault codes are written to the System Event Log. Table 7-1 lists the four codes in this manual. Write the full code in every case note, and do not shorten it to the prefix.

**Table 7-1. Network fault codes**

| Fault code | Subsystem | Severity | LED state | Trigger | Remediation | SEL event |
|---|---|---|---|---|---|---|
| 0xC029_ETH_PHY_LINKDN | Network PHY | Major | NET LED off | Signal integrity loss on port QSFP28_12 | Clean the optical transceiver end-face; re-seat the fiber | SEL-0601 |
| 0xC02A_ETH_PHY_DEGRADED | Network PHY | Warning | NET LED solid amber | Port QSFP28_21 negotiated 25 GbE instead of 100 GbE | Replace the DAC cable; verify the transceiver is rated for 100G | SEL-0602 |
| 0xC040_MGMT_VLAN_MISMATCH | Network PHY | Minor | Solid green PWR | Management traffic seen outside MGMT_VLAN_102 | Reconfigure the switch port to access VLAN 102 on MGMT0; check the trunk allowed list | SEL-0610 |
| 0xC055_SWITCH_ASIC_TEMP | Network PHY | Major | Blinking amber PWR | Switch ASIC TS-3200 junction temperature above 95 C | Check switch fan trays and airflow direction (front-to-back); replace fan tray if needed | SEL-0611 |

### 7.1 Link down: 0xC029_ETH_PHY_LINKDN

0xC029_ETH_PHY_LINKDN is raised on port QSFP28_12, which is an uplink to the spine layer. Treat it as a priority, because the port is part of the rack's spine connectivity. The NET LED is off for this event.

**Procedure: 0xC029_ETH_PHY_LINKDN**

1. Confirm the port in the SEL entry. The port must be QSFP28_12. If the event names a different port, stop and check the event against Figure F4.
2. Check that the transceiver and fiber are in the expected uplink port. Do not move the fiber to another port to test it while the spine is in service.
3. Remove the fiber from the transceiver. Clean the optical transceiver end-face with an approved fiber cleaning tool, and inspect it.
4. Clean the fiber end-face as well, and then re-seat the fiber in the transceiver until it clicks into place.
5. Confirm the link. The NET LED should show solid green for a 100 GbE link, or blinking green when traffic is present.
6. If the link does not come up after cleaning and re-seating, escalate to Technician L2. Do not replace the spine connection without an engineer's approval.

> **CAUTION:** Never look directly into an optical connector or a fiber end. Use the cleaning and inspection tools listed in *Preventive Maintenance and Safety Manual*.

### 7.2 Degraded link: 0xC02A_ETH_PHY_DEGRADED

0xC02A_ETH_PHY_DEGRADED is a warning. Port QSFP28_21 negotiated 25 GbE instead of 100 GbE. Port QSFP28_21 is a server port, so the affected sled is running at a quarter of its link speed. The NET LED is solid amber for a link that has been degraded to 25 GbE or 40 GbE.

**Procedure: 0xC02A_ETH_PHY_DEGRADED**

1. Confirm the port in the SEL entry. The port must be QSFP28_21. Confirm the negotiated speed from the switch.
2. Identify the cable type on the port. The remediation names the DAC cable, so check that the connected cable is a DAC cable before replacing it.
3. Verify that the transceiver is rated for 100G. A transceiver that is not rated for 100G is a cause of this event even if the cable is good.
4. Replace the DAC cable with a cable rated for 100G, and check that the cable seats fully at both ends.
5. Confirm the link speed. The NET LED should be solid green, which indicates a 100 GbE link at full speed.
6. Close the event only when the speed is confirmed as 100 GbE, not when the link merely comes up.

### 7.3 VLAN mismatch: 0xC040_MGMT_VLAN_MISMATCH

0xC040_MGMT_VLAN_MISMATCH is a minor event raised when management traffic is seen outside MGMT_VLAN_102. The LED state for this event is solid green PWR. The event is still a configuration error, and it needs to be corrected even though it is minor.

**Procedure: 0xC040_MGMT_VLAN_MISMATCH**

1. Identify the device and port that the event refers to. Traffic on MGMT0 belongs only on MGMT_VLAN_102, so an event that names MGMT0 needs the MGMT0 configuration checked first.
2. Reconfigure the switch port to access VLAN 102 on MGMT0. Access mode is used because MGMT0 carries only MGMT_VLAN_102.
3. If the event refers to a QSFP28 port rather than MGMT0, check its trunk allowed list. Management VLAN traffic should not be permitted on a data trunk unless the rack design says so.
4. Save the configuration and confirm that management traffic is seen only on MGMT_VLAN_102.
5. Check that the BMCs remain reachable on MGMT_VLAN_102 after the change.

> **NOTE:** The remediation text says to reconfigure "the switch port" for MGMT0. MGMT0 is a dedicated port, so the configuration change is made to its management VLAN setting. Check the local configuration guide for the exact command for the AOS release on the switch.

### 7.4 Switch ASIC temperature: 0xC055_SWITCH_ASIC_TEMP

0xC055_SWITCH_ASIC_TEMP is a major event raised when the junction temperature of the TS-3200 ASIC is above 95 C. It is the critical level for the ASIC, and the PWR LED blinks amber for this event. The ASIC has a warning threshold at 85 C, but this revision does not assign a SEL code to that level. A switch that is running between 85 C and 95 C should be checked before it reaches the 0xC055 level.

**Procedure: 0xC055_SWITCH_ASIC_TEMP**

1. Check the switch fan trays. Confirm that every fan tray is seated and running.
2. Check the airflow direction. The switch moves air front-to-back. A tray that is installed the wrong way, or a rack that has its air path reversed, produces the same symptom as a failed fan.
3. Check the blanking panels in the rack, as described in *Thermal and Cooling Manual*. An open U position can reduce the airflow that reaches the switch.
4. Replace a fan tray only if the earlier checks do not show the cause. The remediation names the fan tray as the replacement item.
5. Watch the ASIC junction temperature after the change, and record the final value on the job record.

> **WARNING:** Do not block the switch exhaust or the front intake to lower the reading. The switch needs its full airflow path to stay under the 95 C limit.

## 8. Firmware baseline

The switch OS and the sled BIOS and BMC builds should be taken from the same compatibility row. The firmware matrix in the specification lists four combinations. Table 8-1 gives the switch-relevant view of those combinations, showing the AOS release that goes with each BIOS and BMC build. The full notes are in *Release Notes and Firmware Compatibility*.

**Table 8-1. Firmware compatibility for AS-100G operations**

| BIOS | BMC | AOS | Status |
|---|---|---|---|
| BIOS 1.8.0 | BMC 2.12.x | AOS 5.1 | Legacy. Missing watchdog fix (0x9A05). |
| BIOS 1.9.2 | BMC 2.14.3 | AOS 5.2 | Recommended baseline for AOR-3 Rev 3.2. |
| BIOS 2.0.0 | BMC 2.14.3 | AOS 5.3 | Adds DDR5 retraining improvements (0x10F0). |
| BIOS 2.0.0 | BMC 2.13.x | AOS 5.3 | Not supported. Triggers 0x9A10_BMC_FW_MISMATCH. |

The recommended baseline for this revision is BIOS 1.9.2 with BMC 2.14.3 and AOS 5.2. Do not mix a BIOS 2.0.0 sled with a BMC 2.13.x build, because that combination is not supported. Check the switch AOS version before you start any network change, and record it on the job record with the BMC build of the sled.

## 9. Frequently asked questions

**Q: The NET LED on a port is off and the SEL shows 0xC029_ETH_PHY_LINKDN. What is the first thing to check?**

A: Confirm that the port is QSFP28_12, which is an uplink to the spine layer. Then clean the optical transceiver end-face, clean and re-seat the fiber, and confirm that the NET LED turns solid green or blinking green. Do not move the fiber to another port to test it while the spine is in service.

**Q: A server port shows 25 GbE after a change. Is that 0xC02A_ETH_PHY_DEGRADED?**

A: Yes, if the port is QSFP28_21 and the SEL shows the code. The degraded link is a warning, and the NET LED is solid amber. Replace the DAC cable with one rated for 100G, and verify that the transceiver is rated for 100G. Close the event only when the link is confirmed at 100 GbE.

**Q: Can I put a data VLAN on MGMT0 so that a sled can be reached over the management port?**

A: No. MGMT0 carries only MGMT_VLAN_102. It is never routed through the QSFP28 fabric, and VLANs 101, 103 and 104 must not be carried onto it. Use MGMT_VLAN_102 for management access.

**Q: Which port carries the uplink traffic from the rack to the spine switches?**

A: The uplinks are QSFP28_01 to QSFP28_16. They connect the AS-100G to the spine switches SP-1 and SP-2, which are both 400G switches. Figure F7 shows the topology, and Figure F4 shows the port map on the switch face.

**Q: The switch ASIC reads 88 C. Is there a fault code for that?**

A: Not in this revision. The ASIC warning level is 85 C, and no SEL code is assigned to it. The code 0xC055_SWITCH_ASIC_TEMP is written at 95 C, which is the critical level. Check the fan trays and airflow now, before the reading reaches 95 C.

**Q: The management link is up but the SEL shows 0xC040_MGMT_VLAN_MISMATCH. Is the data path affected?**

A: The event is minor, and the LED state is solid green PWR, so the data path is not expected to be affected by this event alone. The event means that management traffic was seen outside MGMT_VLAN_102. Reconfigure the port to access VLAN 102 on MGMT0 and check the trunk allowed list on any QSFP28 port named in the event.

**Q: Which AOS release should I run with the recommended sled firmware?**

A: The recommended baseline is BIOS 1.9.2, BMC 2.14.3 and AOS 5.2. If the sled runs BIOS 2.0.0, use AOS 5.3 with BMC 2.14.3. BIOS 2.0.0 with BMC 2.13.x is not supported, and it triggers 0x9A10_BMC_FW_MISMATCH.
