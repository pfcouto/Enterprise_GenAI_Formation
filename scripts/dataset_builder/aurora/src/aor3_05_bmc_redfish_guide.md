# BMC, Redfish and CLI Operations Guide

Document ref: aor3_05_bmc_redfish_guide | Revision: Rev 3.2 (2026-03) | Classification: Fictional training material

## 1. Scope and audience

This guide explains how to operate the baseboard management controller (BMC) on each compute sled of the Aurora Open Rack AOR-3. It covers the three ways a technician or engineer reaches the BMC: the front-panel LEDs on the sled, the `bmc-cli` command-line tool together with the `bmc-reset` utility, and the Redfish API under `/redfish/v1`. It is written for Technician L2 staff and for engineers who export the System Event Log (SEL), reset the controller, restart the sensor daemon, or clear a chassis intrusion latch.

The guide does not describe how to replace sleds, rectifier modules or fan modules. Those procedures are in *Power Shelf PS-3000 Service Manual*, *Thermal and Cooling Manual* and *Preventive Maintenance and Safety Manual*. The meaning of every fault code is in *Fault Code Reference and Troubleshooting Flowcharts*. Read this guide to learn how to act on the BMC. Read the fault code reference to learn what the BMC is reporting.

> **NOTE:** Each compute sled runs its own BMC. A reset, an export or an intrusion clear applies to one sled only. Confirm the sled position before you run any command. Sled 1 occupies U02-U03 and sled 9 occupies U18-U19.

## 2. BMC architecture

### 2.1 Role of the BMC

Every compute sled, model CS-2U, carries one OpenBMC controller. The sled itself is a dual-socket unit with 16 DDR5 DIMM slots, two NVMe bays, a 48 V to 12 V point-of-load (PoL) stage and the BMC. The BMC runs OpenBMC 2.14 and exposes Redfish 1.17. It has four core jobs:

1. It polls the sensors on the sled every 2 seconds.
2. It writes every detected fault to the System Event Log, which holds up to 4,096 entries.
3. It drives the four front-panel LEDs described in section 3.
4. It starts the emergency shutdown when CPU temperature reaches 90 C, after logging `0x8F11_TEMP_CRIT`.

The BMC also talks to the power shelf PS-3000 over PMBus at address 0x03. When that link times out, the BMC logs `0x99A0_PSU_COMM_LOST`.

### 2.2 Background duties and the codes they produce

The BMC performs several duties without operator input. Each duty can produce a fault code, so an operator who understands the duty can read the code faster.

| BMC duty | Behaviour | Related code |
|---|---|---|
| Sensor polling | Reads sensors every 2 seconds | `0x6E01_SENSOR_STALE` when a reading is not updated for more than 10 seconds |
| SEL logging | Writes each fault to the SEL, capacity 4,096 entries | Every code in the fault table, each with its own SEL event number |
| Watchdog | Reboots the BMC itself when the timer expires | `0x9A05_BMC_WDT_RESET` |
| PMBus master | Communicates with the power shelf at address 0x03 | `0x99A0_PSU_COMM_LOST`, `0x99A1_PMBUS_CRC_ERR` |
| Thermal shutdown | Starts the emergency shutdown at 90 C CPU temperature | `0x8F11_TEMP_CRIT` |
| LED control | Drives the PWR, NET, BMC and ID LEDs | See section 3 |
| Firmware compatibility | Checks that BMC and BIOS builds belong to the matrix | `0x9A10_BMC_FW_MISMATCH` |

### 2.3 Management paths

There are three ways to see or change the state of a sled's BMC.

- **Front-panel LEDs.** Visible at the rack without any tool. They give a coarse view only.
- **bmc-cli and bmc-reset.** Commands run from an administrative session on the BMC. They perform the actions in this guide: exporting the SEL, resetting the BMC, restarting the sensor daemon and clearing the chassis intrusion latch.
- **Redfish.** An HTTP API rooted at `/redfish/v1`. It exposes the same information in structured form and is suited to remote reads and to scripts.

BMC management traffic belongs on the out-of-band management VLAN, MGMT_VLAN_102, carried on the switch MGMT0 port. If the switch reports `0xC040_MGMT_VLAN_MISMATCH`, check the switch port configuration before you troubleshoot the BMC itself.

### 2.4 Firmware baseline

The BMC and the BIOS must belong to the same row of the firmware compatibility matrix. The matrix is reproduced below for convenience. The authoritative version is in *Release Notes and Firmware Compatibility*.

| BIOS | BMC | Switch OS | Notes |
|---|---|---|---|
| BIOS 1.8.0 | BMC 2.12.x | AOS 5.1 | Legacy. Missing watchdog fix (0x9A05). |
| BIOS 1.9.2 | BMC 2.14.3 | AOS 5.2 | Recommended baseline for AOR-3 Rev 3.2. |
| BIOS 2.0.0 | BMC 2.14.3 | AOS 5.3 | Adds DDR5 retraining improvements (0x10F0). |
| BIOS 2.0.0 | BMC 2.13.x | AOS 5.3 | NOT supported: triggers 0x9A10_BMC_FW_MISMATCH. |

> **WARNING:** Do not flash a BMC build that is not listed for the installed BIOS. The combination of BIOS 2.0.0 and BMC 2.13.x is explicitly unsupported and raises `0x9A10_BMC_FW_MISMATCH`.

## 3. Front-panel LEDs

Look at Figure F2 whenever you need the state of a sled from the front of the rack, before you connect any tool to the BMC. The legend numbers the four LEDs 1 to 4 in the order PWR, NET, BMC and ID.

![Figure F2: Front-panel LED legend](figures/F2_front_panel_led_legend.png)

*Figure F2: Front-panel LED legend: PWR, NET, BMC and ID LEDs*

The table below reproduces the legend. The BMC heartbeat LED is the one most relevant to this guide.

| LED | Position | State | Meaning |
|---|---|---|---|
| PWR (power / health) | 1 | Solid green | Normal operation: 48 V busbar present, ripple below 50 mV, all rails good. |
| PWR (power / health) | 1 | Blinking amber (1 Hz) | Thermal warning: temperature above 75 C. Fans forced to 100 %, CPU throttled. |
| PWR (power / health) | 1 | Solid red | Critical fault: rail overvoltage or short (for example `0x4A7B_VRM_OVERVOLT`). Immediate power cutoff. |
| PWR (power / health) | 1 | Off | No 48 V input or sled not seated. |
| NET (network link) | 2 | Solid green | 100 GbE link up at full speed. |
| NET (network link) | 2 | Blinking green | Link up, traffic present. |
| NET (network link) | 2 | Solid amber | Link up but degraded to 25 GbE or 40 GbE. |
| NET (network link) | 2 | Off | No link (see `0xC029_ETH_PHY_LINKDN`). |
| BMC (heartbeat) | 3 | Blinking blue (0.5 Hz) | BMC healthy and polling sensors. |
| BMC (heartbeat) | 3 | Solid blue | BMC booting or firmware update in progress. Do not power cycle. |
| BMC (heartbeat) | 3 | Off | BMC unresponsive (see `0x99A0_PSU_COMM_LOST`). |
| ID (locator) | 4 | Solid white | Locator active: a technician or the BMC asked to identify this sled. |
| ID (locator) | 4 | Off | Locator inactive. |

### 3.1 Reading the BMC heartbeat LED

The BMC LED is the first indicator to check before you run any command on a sled.

- **Blinking blue at 0.5 Hz** means the BMC is healthy. You can run `bmc-cli` and Redfish reads with confidence.
- **Solid blue** means the BMC is booting or a firmware update is running. Wait. Do not reset the BMC and do not power cycle the sled while this state persists.
- **Off** means the BMC is unresponsive. Commands sent to it may fail. Follow the procedure in section 4.3 for a warm reset, and escalate if the LED stays off after the reset.

### 3.2 Reading the PWR LED

Blinking amber on the PWR LED has two meanings in practice. The legend describes it as a thermal warning. The fault table, however, also assigns blinking amber to several non-thermal faults, such as rectifier failure and TPM attestation failure. Do not assume a cause from the LED colour alone. Export the SEL first and use the fault code, as described in *Fault Code Reference and Troubleshooting Flowcharts*.

### 3.3 Locator LED

The ID LED is solid white only when the locator is active. A technician or the BMC can activate it to identify a sled in a crowded rack. The fault table also uses the solid white ID state for a chassis intrusion event, so a white ID LED after a service visit deserves a check against the SEL. Section 4.6 explains how to clear the latch.

## 4. bmc-cli and bmc-reset reference

### 4.1 Command summary

The two reset commands are invoked as `bmc-reset`, not as subcommands of `bmc-cli`. Type each command exactly as shown. Every other operation in this section is a `bmc-cli` subcommand.

| Task | Command | Use it when | Related code |
|---|---|---|---|
| Warm reset | `bmc-reset --warm` | The BMC is not responding or the PMBus link has timed out | `0x99A0_PSU_COMM_LOST` |
| Cold reset | `bmc-reset --cold` | A warm reset did not clear the condition and an engineer has approved escalation | None dedicated |
| Export SEL | `bmc-cli sel export` | Before any reset, and whenever a fault must be recorded | `0x9A05_BMC_WDT_RESET` |
| Restart sensor daemon | `bmc-cli service restart sensord` | A sensor reading has not updated for more than 10 seconds | `0x6E01_SENSOR_STALE` |
| Clear intrusion latch | `bmc-cli chassis clear-intrusion` | Authorised service has been completed and recorded | `0x6E10_CHASSIS_INTRUSION` |

### 4.2 Exporting the SEL

Export the SEL before any other action on a sled. The export is the record of what the BMC saw, and a reset can change what the live log shows.

1. Open an administrative session to the BMC of the target sled.
2. Run `bmc-cli sel export`. Direct the output to a file whose name includes the sled position and the date.
3. Open the file and find the most recent entries. Each entry carries a fault code and a SEL event number, for example `SEL-0301` for `0x99A0_PSU_COMM_LOST`.
4. Copy the export into the case record before you run a reset or a clear command.

> **NOTE:** The SEL holds up to 4,096 entries. Export on every visit so the history survives.

### 4.3 Warm reset

A warm reset is the less disruptive of the two reset options, so use it first. Use it when the BMC is unresponsive, or when the PMBus link to the power shelf has timed out.

> **WARNING:** Do not start a warm reset while the PWR LED is solid red. A solid red state is a critical fault and must be handled through the subsystem procedure first.

> **WARNING:** Do not start a warm reset while the BMC LED is solid blue. Solid blue means the BMC is booting or a firmware update is running.

> **CAUTION:** The BMC starts the emergency shutdown at 90 C CPU temperature. If the sled is above the 75 C warning threshold, a reset removes the BMC from that role for the duration of the reset. Obtain approval from the thermal engineer before you reset a sled in a thermal warning.

Procedure:

1. Confirm that the BMC LED is not solid blue and that the PWR LED is not solid red.
2. Export the SEL as described in section 4.2.
3. Run `bmc-reset --warm`.
4. Wait until the BMC LED shows blinking blue at 0.5 Hz. Do not issue further commands before this state appears.
5. Run `bmc-cli sel export` again and compare the new entries with the first export.
6. Check the PWR LED. If it shows solid green and no new fault is logged, the reset has cleared the condition.
7. If `0x99A0_PSU_COMM_LOST` recurs, follow the remediation in the fault table: replace the PMBus ribbon cable. Record the recurrence in the case record and escalate to an engineer.

### 4.4 Cold reset

A cold reset is more disruptive than a warm reset. Use it only after a warm reset has failed to clear the condition, and only with the approval of an engineer. Record the time of the reset in the case record.

Follow the same preconditions and steps as section 4.3, with two differences:

- Expect the BMC LED to show solid blue while the controller boots, before it returns to blinking blue. This is normal behaviour, not a new fault.
- Engineer approval must be recorded before the command is run.

### 4.5 Restarting the sensor daemon

Use this procedure for `0x6E01_SENSOR_STALE`. The code means that a sensor reading has not updated for more than 10 seconds, so the BMC cannot judge the state of that sensor.

1. Export the SEL as described in section 4.2.
2. Run `bmc-cli service restart sensord`.
3. Check that sensor readings are being updated, using the Redfish sensor endpoint in section 5.2.
4. If the sensor goes stale again, escalate. A repeated stale reading points to a hardware or firmware problem, not to the daemon.

> **CAUTION:** While a sensor is stale, the BMC cannot assess that sensor reliably. If the sled is also in a thermal warning, do not treat the stale sensor as a normal state. Check the thermal condition through *Thermal and Cooling Manual* before you restart the daemon.

### 4.6 Clearing the chassis intrusion latch

The chassis intrusion switch records that a sled cover was opened. The latch clears only through the command below. Clearing it is a record-keeping action as much as a technical one.

> **WARNING:** Never clear the intrusion latch without a service ticket. The latch is the record that a sled was opened. Clearing it without a ticket removes that record and hides unauthorised physical access.

1. Confirm that a maintenance ticket exists for this sled and that its time window matches the intrusion event in SEL-0701.
2. Confirm that all covers are closed and seated.
3. Run `bmc-cli chassis clear-intrusion`.
4. Check the ID LED. It should return to off. If it stays solid white, the latch has not cleared and you must not return the sled to service until the cause is known.
5. Export the SEL again and record the clearance in the ticket.

## 5. Redfish API

### 5.1 Base path and access

All Redfish resources sit under `/redfish/v1` on the sled BMC. Requests are made over HTTPS to the BMC address on MGMT_VLAN_102. Use the accounts issued by the site administrator. Identifiers in curly braces, such as `{SystemId}`, are placeholders. Read the real identifiers from the collection responses before you build a request on them.

Use Redfish for reads and evidence collection. Use the CLI for actions that change state: resets, service restarts and intrusion clears. This split keeps a remote session from changing a sled by accident.

### 5.2 Endpoint reference

The endpoints below are the ones this guide uses. Each is a GET request. They do not change the state of the BMC.

| Method | Endpoint | Returns |
|---|---|---|
| GET | `/redfish/v1` | Service root with links to the top-level collections |
| GET | `/redfish/v1/Systems` | Collection of compute systems on the sled |
| GET | `/redfish/v1/Systems/{SystemId}` | Host power and health status |
| GET | `/redfish/v1/Systems/{SystemId}/LogServices/SEL/Entries` | SEL entries, the same content as `bmc-cli sel export` |
| GET | `/redfish/v1/Chassis` | Collection of chassis resources |
| GET | `/redfish/v1/Chassis/{ChassisId}` | Chassis state, including the physical security status used for intrusion |
| GET | `/redfish/v1/Chassis/{ChassisId}/Sensors` | Sensor readings, updated by the BMC every 2 seconds |
| GET | `/redfish/v1/Managers/{ManagerId}` | BMC state and firmware version |
| GET | `/redfish/v1/UpdateService` | Firmware update service status |
| GET | `/redfish/v1/EventService` | Event service configuration, used for subscriptions |

### 5.3 Example requests

The following examples read the service root, the BMC manager resource and the SEL. Replace the placeholders with values from your site.

```
curl -u <username> https://<sled-bmc-address>/redfish/v1
curl -u <username> https://<sled-bmc-address>/redfish/v1/Managers/<ManagerId>
curl -u <username> https://<sled-bmc-address>/redfish/v1/Systems/<SystemId>/LogServices/SEL/Entries
```

The `curl` client prompts for the password when only the username is supplied. Do not place the password on the command line, because it is then stored in the shell history.

### 5.4 Choosing between Redfish and the CLI

| Task | Preferred route | Reason |
|---|---|---|
| Read the BMC firmware version | Redfish `Managers` endpoint | Read only, structured output |
| Read the SEL for a report | Redfish SEL endpoint, or `bmc-cli sel export` | Both give the same content |
| Check sensor freshness | Redfish `Sensors` endpoint | Shows the current reading and update state |
| Reset the BMC | `bmc-reset --warm` or `bmc-reset --cold` | Action command, not available as a read |
| Restart the sensor daemon | `bmc-cli service restart sensord` | Action command |
| Clear the intrusion latch | `bmc-cli chassis clear-intrusion` | Action command, requires a ticket |

## 6. BMC and security fault codes

Seven fault codes belong to the BMC and security groups. They are listed below as they appear in the fault table. Section 6.1 onward explains the procedure for each. The full set of 30 codes is in *Fault Code Reference and Troubleshooting Flowcharts*.

| Code | Subsystem | Severity | LED state | Root cause | Remediation | SEL event |
|---|---|---|---|---|---|---|
| `0x99A0_PSU_COMM_LOST` | PMBus | Major | BMC LED off | I2C communication timeout on PMBus address 0x03 between BMC and power shelf. | Reset the BMC with the OpenBMC CLI: bmc-reset --warm. If it repeats, replace the PMBus ribbon cable. | SEL-0301 |
| `0x99A1_PMBUS_CRC_ERR` | PMBus | Minor | Solid green PWR | Repeated CRC errors on PMBus frames from rectifier R3. | Log and monitor; reseat rectifier R3 during the next maintenance window. | SEL-0302 |
| `0x9A05_BMC_WDT_RESET` | BMC | Major | Solid blue BMC | BMC watchdog timer expired and the BMC rebooted itself. | Collect the SEL with bmc-cli sel export; upgrade BMC firmware to 2.14.3 or later. | SEL-0310 |
| `0x9A10_BMC_FW_MISMATCH` | BMC | Warning | Solid green PWR | BMC firmware is not in the compatibility matrix for the installed BIOS. | Flash the matching BMC build listed in the firmware compatibility matrix (Release Notes). | SEL-0311 |
| `0x6E01_SENSOR_STALE` | BMC | Minor | Solid green PWR | A sensor reading has not updated for more than 10 seconds. | Restart the sensor daemon: bmc-cli service restart sensord. | SEL-0320 |
| `0x6E10_CHASSIS_INTRUSION` | Security | Warning | Solid white ID | Chassis intrusion switch opened without a service ticket. | Verify the maintenance ticket; reset the intrusion latch with bmc-cli chassis clear-intrusion. | SEL-0701 |
| `0x6E20_TPM_ATTEST_FAIL` | Security | Major | Blinking amber PWR | TPM measurement differs from the golden attestation value. | Quarantine the sled, re-image firmware, and re-enroll the TPM attestation key. | SEL-0702 |

### 6.1 Watchdog reset (`0x9A05_BMC_WDT_RESET`)

This code means the BMC rebooted itself after its watchdog timer expired. The sled may appear to run normally afterwards, so the event is easy to miss.

1. Export the SEL and record the entry for `0x9A05_BMC_WDT_RESET` with its SEL-0310 event number.
2. Read the BMC firmware version through `/redfish/v1/Managers/{ManagerId}`.
3. If the BMC is below 2.14.3, schedule an upgrade to 2.14.3 or later.
4. If the BIOS is 1.8.0, note that this is the legacy row of the matrix. It is missing the watchdog fix. Plan the move to the recommended baseline, BIOS 1.9.2 with BMC 2.14.3, in the same maintenance window.

### 6.2 Firmware mismatch (`0x9A10_BMC_FW_MISMATCH`)

This code means the BMC firmware does not belong to the compatibility matrix for the installed BIOS. The sled runs, but the combination is not supported.

1. Read the BIOS version and the BMC version from the Redfish service.
2. Find the matching row in the matrix in section 2.4.
3. Flash the matching BMC build listed in *Release Notes and Firmware Compatibility*.
4. Export the SEL and confirm that SEL-0311 is not logged again after the reboot.

> **WARNING:** Do not flash a BMC 2.13.x build onto a BIOS 2.0.0 sled. That combination is not supported and triggers this code.

### 6.3 Sensor stale (`0x6E01_SENSOR_STALE`)

Use the procedure in section 4.5. The minor severity of this code does not reduce the caution required while a thermal warning is active.

### 6.4 PMBus timeout and CRC errors (`0x99A0_PSU_COMM_LOST`, `0x99A1_PMBUS_CRC_ERR`)

These two codes concern the link between the BMC and the power shelf. They are not the same fault.

- For `0x99A0_PSU_COMM_LOST`, the LED on the BMC is off and the link has timed out. Perform a warm reset as described in section 4.3. If the timeout recurs, replace the PMBus ribbon cable and record the replacement.
- For `0x99A1_PMBUS_CRC_ERR`, the link is working but frames from rectifier R3 arrive with errors. The PWR LED stays solid green. Log the event and monitor it. Reseat rectifier R3 during the next maintenance window, following *Power Shelf PS-3000 Service Manual*.

### 6.5 Chassis intrusion (`0x6E10_CHASSIS_INTRUSION`)

Use the procedure in section 4.6. Verify the ticket before you clear the latch, and never clear it to silence the ID LED.

### 6.6 TPM attestation failure (`0x6E20_TPM_ATTEST_FAIL`)

This code means that the trusted platform module measurement differs from the golden attestation value. The sled may be running firmware that has been altered or that does not match its enrolled state. Treat it as a security incident, not as a routine fault.

1. Quarantine the sled. Isolate it from workloads and from the data network until the investigation is complete.
2. Export the SEL and retain the export with the case record.
3. Re-image the firmware, using the approved image for the installed BIOS and BMC row in the matrix.
4. Re-enroll the TPM attestation key.
5. Confirm that the attestation value matches the golden value before the sled returns to service.

> **WARNING:** Do not return a sled with `0x6E20_TPM_ATTEST_FAIL` to service on the basis of a successful reboot alone. Only a matching attestation value clears this fault.

## 7. Frequently asked questions

**Q: My BMC LED is blinking blue. Do I need to do anything before I run a command?**

No. Blinking blue at 0.5 Hz means the BMC is healthy and polling sensors. Export the SEL first, as described in section 4.2, and then run the command you need.

**Q: Can I run `bmc-reset --warm` while the sled is updating its firmware?**

No. A solid blue BMC LED means that the BMC is booting or a firmware update is in progress. Wait until the LED returns to blinking blue before you run any reset.

**Q: Should I use Redfish or `bmc-cli` to collect the SEL?**

Either route gives the same content. Use Redfish from a remote session or in a script, and use `bmc-cli sel export` when you are at the sled and want a file for the case record.

**Q: I cleared the intrusion latch and the ID LED is still solid white. What now?**

The latch has not cleared. Do not return the sled to service. Export the SEL, confirm the state through the Chassis Redfish resource, and escalate to an engineer with the maintenance ticket number.

**Q: The legend says that blinking amber means a thermal warning. Why does a rectifier fault also show blinking amber?**

The fault table assigns blinking amber to several non-thermal faults. The LED colour narrows the search but does not identify the cause. Export the SEL and read the fault code. *Fault Code Reference and Troubleshooting Flowcharts* contains the decision tree for blinking amber.

**Q: A sled shows `0x9A10_BMC_FW_MISMATCH`. Can I flash the newest BMC build?**

Not without checking the matrix. Read the installed BIOS version and flash the BMC build that the compatibility matrix lists for that BIOS. The newest build is not always the supported one.

Cross-reference: for the full meaning of each code in this guide and for the blinking amber decision tree, see *Fault Code Reference and Troubleshooting Flowcharts*. For firmware builds and release notes, see *Release Notes and Firmware Compatibility*.
