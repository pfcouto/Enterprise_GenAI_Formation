"""
Aurora Open Rack AOR-3 — single source of truth for the synthetic hardware corpus.

EVERYTHING in the hardware_manuals corpus (manual text, figures, entity graph,
golden evaluation set) is derived from or checked against the facts in this file.
The vendor, the product line and every value below are FICTIONAL. They are
inspired by public Open Compute Project (OCP) Open Rack V3 concepts but are not
real specifications. Never use them for real hardware.
"""

VENDOR = "Aurora Systems"
PRODUCT = "Aurora Open Rack AOR-3"
DOC_REV = "Rev 3.2 (2026-03)"

# ----------------------------------------------------------------------------
# Hardware building blocks
# ----------------------------------------------------------------------------
COMPONENTS = {
    "PS-3000": {
        "name": "Power Shelf PS-3000",
        "rack_units": "U20-U22",
        "description": "3U power shelf holding six hot-swappable 3 kW rectifier modules (R1-R6) in an N+1 arrangement, "
                       "converting 3-phase 400 V AC mains into a 48 V DC busbar.",
        "specs": {"rectifier_modules": 6, "rectifier_rating_kw": 3, "redundancy": "N+1 (5 active + 1 spare)",
                  "busbar_nominal_v": 48, "busbar_range_v": "44.0-52.0 V", "ovp_cutoff_v": 54.2,
                  "uvp_cutoff_v": 40.5, "max_output_kw": 15, "efficiency": "97.5 % at 50 % load"},
    },
    "CS-2U": {
        "name": "Compute Sled CS-2U",
        "rack_units": "U02-U19 (nine sleds, two units each)",
        "description": "Dual-socket compute sled with 16 DDR5 DIMM slots (A1-A8 on CPU0, B1-B8 on CPU1), "
                       "two NVMe bays, a 48 V to 12 V point-of-load (PoL) stage and an on-board BMC.",
        "specs": {"sockets": 2, "dimm_slots": 16, "dimm_type": "DDR5-5600 RDIMM", "max_memory_gb": 2048,
                  "nvme_bays": 2, "bmc": "OpenBMC 2.14 (Redfish 1.17)", "input_v": "48 V DC from busbar",
                  "typical_power_w": 780, "max_power_w": 1100},
    },
    "FW-6": {
        "name": "Fan Wall FW-6",
        "rack_units": "rear of U02-U19",
        "description": "Rear fan wall made of six hot-swappable fan modules FM1-FM6, each with a tachometer wire.",
        "specs": {"modules": 6, "rated_rpm": 9000, "min_rpm": 2800, "tach_fail_rpm": 600,
                  "swap_time_s": 30, "airflow_cfm_per_module": 85},
    },
    "AS-100G": {
        "name": "Top-of-Rack Switch AS-100G",
        "rack_units": "U23",
        "description": "1U 100 GbE switch built on the Aurora TS-3200 switch ASIC (3.2 Tbps aggregate port capacity) "
                       "with 32 QSFP28 ports, a dedicated 1 GbE out-of-band management port and a serial console.",
        "specs": {"asic": "Aurora TS-3200", "capacity_tbps": 3.2, "qsfp28_ports": 32, "port_speed": "100 GbE",
                  "mgmt_port": "MGMT0 (RJ45, 1GbE Base-T)", "mgmt_vlan": "MGMT_VLAN_102",
                  "console": "RJ45 serial 115200 8N1", "uplink_ports": "QSFP28_01-QSFP28_16",
                  "server_ports": "QSFP28_17-QSFP28_32"},
    },
    "BMC": {
        "name": "Baseboard Management Controller (OpenBMC)",
        "rack_units": "on every compute sled",
        "description": "Each sled BMC polls sensors every 2 seconds, writes fault codes to the System Event Log (SEL) "
                       "and drives the front-panel LEDs. Management is available over Redfish and the bmc-cli tool.",
        "specs": {"poll_interval_s": 2, "sel_capacity_entries": 4096, "redfish_base": "/redfish/v1",
                  "cli": "bmc-cli", "warm_reset": "bmc-reset --warm", "cold_reset": "bmc-reset --cold"},
    },
}

# Rack elevation (bottom = U01). Used by figure F1.
RACK_ELEVATION = [
    ("U01", "Cable management / blank panel"),
    ("U02-U19", "Compute sleds CS-2U x9 (sled 1 at U02-U03 ... sled 9 at U18-U19)"),
    ("U20-U22", "Power shelf PS-3000 (rectifiers R1-R6)"),
    ("U23", "Top-of-rack switch AS-100G"),
    ("U24", "Patch panel (QSFP28 breakout)"),
    ("U25-U42", "Reserved / future expansion"),
]

# ----------------------------------------------------------------------------
# Front-panel LED legend (figure F2)
# ----------------------------------------------------------------------------
LEDS = [
    {"id": "PWR", "name": "Power / health LED", "position": 1, "states": [
        ("Solid green", "Normal operation: 48 V busbar present, ripple below 50 mV, all rails good."),
        ("Blinking amber (1 Hz)", "Thermal warning: temperature above 75 C. Fans forced to 100 %, CPU throttled."),
        ("Solid red", "Critical fault: rail overvoltage or short (for example 0x4A7B_VRM_OVERVOLT). Immediate power cutoff."),
        ("Off", "No 48 V input or sled not seated."),
    ]},
    {"id": "NET", "name": "Network link LED", "position": 2, "states": [
        ("Solid green", "100 GbE link up at full speed."),
        ("Blinking green", "Link up, traffic present."),
        ("Solid amber", "Link up but degraded to 25 GbE or 40 GbE."),
        ("Off", "No link (see fault code 0xC029_ETH_PHY_LINKDN)."),
    ]},
    {"id": "BMC", "name": "BMC heartbeat LED", "position": 3, "states": [
        ("Blinking blue (0.5 Hz)", "BMC healthy and polling sensors."),
        ("Solid blue", "BMC booting or firmware update in progress. Do not power cycle."),
        ("Off", "BMC unresponsive (see fault code 0x99A0_PSU_COMM_LOST)."),
    ]},
    {"id": "ID", "name": "Locator (ID) LED", "position": 4, "states": [
        ("Solid white", "Locator active: a technician or the BMC asked to identify this sled."),
        ("Off", "Locator inactive."),
    ]},
]

# ----------------------------------------------------------------------------
# Fault codes. The first rows keep the codes used since the first version of the formation.
# near_duplicate_of marks codes that look alike on purpose (dense-vs-BM25 teaching point).
# ----------------------------------------------------------------------------
FAULT_CODES = [
    # code, subsystem, severity, led_state, root_cause, remediation, sel_event
    ("0x4A7B_VRM_OVERVOLT", "Power VRM", "Critical", "Solid red PWR",
     "Input voltage exceeded the 54.2 V cutoff threshold on the 48 V busbar.",
     "Engage the secondary backup PSU; replace the PDB fuse (F2). Do not re-energise before measuring the busbar.", "SEL-0101"),
    ("0x4A7C_VRM_UNDERVOLT", "Power VRM", "Major", "Blinking amber PWR",
     "Busbar voltage fell below the 40.5 V undervoltage threshold.",
     "Check rectifier modules R1-R6 for a failed unit; reseat the module; verify AC feed on phase L2.", "SEL-0102"),
    ("0x4A80_VRM_OVERCURRENT", "Power VRM", "Critical", "Solid red PWR",
     "Sled PoL stage drew more than 120 A on the 12 V rail.",
     "Remove the sled, inspect the PoL stage for a short, then replace the sled if the fault repeats.", "SEL-0103"),
    ("0x4B10_PSU_RECT_FAIL", "Power shelf", "Major", "Blinking amber PWR",
     "A rectifier module reported an internal fault and dropped out of the N+1 set.",
     "Hot-swap the failed rectifier (LED on the module is red). Rack stays up on the remaining 5 modules.", "SEL-0110"),
    ("0x4B22_PSU_AC_LOSS", "Power shelf", "Critical", "Solid red PWR",
     "Loss of 3-phase AC mains on one or more phases.",
     "Check the upstream breaker and PDU; confirm all three phases L1-L3 are present before restart.", "SEL-0111"),
    ("0x8F01_FAN_TACH_FAIL", "Thermal", "Major", "Blinking amber PWR",
     "Tachometer signal lost on Fan Module #4 (below 600 RPM).",
     "Inspect the fan cable seating; swap Fan Module 4 (FM4) using the hot-swap procedure.", "SEL-0201"),
    ("0x8F02_FAN_ALL_FAIL", "Thermal", "Critical", "Solid red PWR",
     "Two or more fan modules report tachometer failure.",
     "Gracefully shut down the sled within 5 minutes; replace both fan modules before restart.", "SEL-0202"),
    ("0x8F10_TEMP_WARN", "Thermal", "Warning", "Blinking amber PWR",
     "CPU or inlet temperature above 75 C.",
     "Fans are forced to 100 % and the CPU is throttled. Check airflow blockage, blanking panels and ambient temperature.", "SEL-0210"),
    ("0x8F11_TEMP_CRIT", "Thermal", "Critical", "Solid red PWR",
     "CPU temperature above 90 C; the BMC starts an emergency shutdown.",
     "Let the sled cool for 10 minutes; verify fan wall FW-6 and cold-aisle temperature before restart.", "SEL-0211"),
    ("0x8F20_AIRFLOW_BLOCK", "Thermal", "Warning", "Blinking amber PWR",
     "Pressure sensor shows restricted airflow across the sled.",
     "Install missing blanking panels in empty U positions; clear obstructions in front of the sled.", "SEL-0212"),
    ("0x99A0_PSU_COMM_LOST", "PMBus", "Major", "BMC LED off",
     "I2C communication timeout on PMBus address 0x03 between BMC and power shelf.",
     "Reset the BMC with the OpenBMC CLI: bmc-reset --warm. If it repeats, replace the PMBus ribbon cable.", "SEL-0301"),
    ("0x99A1_PMBUS_CRC_ERR", "PMBus", "Minor", "Solid green PWR",
     "Repeated CRC errors on PMBus frames from rectifier R3.",
     "Log and monitor; reseat rectifier R3 during the next maintenance window.", "SEL-0302"),
    ("0x9A05_BMC_WDT_RESET", "BMC", "Major", "Solid blue BMC",
     "BMC watchdog timer expired and the BMC rebooted itself.",
     "Collect the SEL with bmc-cli sel export; upgrade BMC firmware to 2.14.3 or later.", "SEL-0310"),
    ("0x9A10_BMC_FW_MISMATCH", "BMC", "Warning", "Solid green PWR",
     "BMC firmware is not in the compatibility matrix for the installed BIOS.",
     "Flash the matching BMC build listed in the firmware compatibility matrix (Release Notes).", "SEL-0311"),
    ("0x10E4_ECC_MULTI_BIT", "DDR5 Memory", "Critical", "Solid red PWR",
     "Uncorrectable multi-bit parity failure on DIMM_A2.",
     "Halt the node; replace the DIMM in slot A2 immediately.", "SEL-0401"),
    ("0x10E5_ECC_SINGLE_BIT", "DDR5 Memory", "Warning", "Solid green PWR",
     "Correctable single-bit errors on DIMM_B5 exceeded 24 per hour.",
     "Schedule DIMM_B5 replacement; no immediate downtime required.", "SEL-0402"),
    ("0x10F0_DIMM_TRAINING_FAIL", "DDR5 Memory", "Major", "Blinking amber PWR",
     "Memory training failed for DIMM_A7 at boot.",
     "Reseat DIMM_A7; if the failure persists, test the slot with a known-good DIMM.", "SEL-0403"),
    ("0x2B30_NVME_SMART_WARN", "Storage", "Warning", "Solid green PWR",
     "NVMe bay 1 reports less than 10 % endurance remaining.",
     "Order a replacement drive; migrate data during the next window.", "SEL-0501"),
    ("0x2B31_NVME_LINK_DOWN", "Storage", "Major", "Blinking amber PWR",
     "PCIe link to NVMe bay 2 failed to train.",
     "Reseat the drive; test with a different NVMe bay; replace the backplane if both fail.", "SEL-0502"),
    ("0xC029_ETH_PHY_LINKDN", "Network PHY", "Major", "NET LED off",
     "Signal integrity loss on port QSFP28_12.",
     "Clean the optical transceiver end-face; re-seat the fiber.", "SEL-0601"),
    ("0xC02A_ETH_PHY_DEGRADED", "Network PHY", "Warning", "NET LED solid amber",
     "Port QSFP28_21 negotiated 25 GbE instead of 100 GbE.",
     "Replace the DAC cable; verify the transceiver is rated for 100G.", "SEL-0602"),
    ("0xC040_MGMT_VLAN_MISMATCH", "Network PHY", "Minor", "Solid green PWR",
     "Management traffic seen outside MGMT_VLAN_102.",
     "Reconfigure the switch port to access VLAN 102 on MGMT0; check the trunk allowed list.", "SEL-0610"),
    ("0xC055_SWITCH_ASIC_TEMP", "Network PHY", "Major", "Blinking amber PWR",
     "Switch ASIC TS-3200 junction temperature above 95 C.",
     "Check switch fan trays and airflow direction (front-to-back); replace fan tray if needed.", "SEL-0611"),
    ("0x7D01_PDB_FUSE_BLOWN", "Power VRM", "Major", "Solid red PWR",
     "Power distribution board fuse F2 is open.",
     "Replace fuse F2 (30 A, 80 V DC rated) after finding the cause of the over-current.", "SEL-0120"),
    ("0x7D02_BUSBAR_RIPPLE", "Power VRM", "Warning", "Solid green PWR",
     "Busbar ripple exceeded 50 mV peak-to-peak.",
     "Inspect rectifier output capacitors and busbar connections for corrosion.", "SEL-0121"),
    ("0x6E01_SENSOR_STALE", "BMC", "Minor", "Solid green PWR",
     "A sensor reading has not updated for more than 10 seconds.",
     "Restart the sensor daemon: bmc-cli service restart sensord.", "SEL-0320"),
    ("0x6E10_CHASSIS_INTRUSION", "Security", "Warning", "Solid white ID",
     "Chassis intrusion switch opened without a service ticket.",
     "Verify the maintenance ticket; reset the intrusion latch with bmc-cli chassis clear-intrusion.", "SEL-0701"),
    ("0x6E20_TPM_ATTEST_FAIL", "Security", "Major", "Blinking amber PWR",
     "TPM measurement differs from the golden attestation value.",
     "Quarantine the sled, re-image firmware, and re-enroll the TPM attestation key.", "SEL-0702"),
    ("0x5F01_COOLANT_LEAK", "Liquid cooling", "Critical", "Solid red PWR",
     "Rear-door heat exchanger leak sensor wet (optional liquid-cooling kit only).",
     "Close the manual valves, power down the affected sleds, call the facility team.", "SEL-0801"),
    ("0x5F02_COOLANT_FLOW_LOW", "Liquid cooling", "Warning", "Blinking amber PWR",
     "Coolant flow below 8 L/min (optional liquid-cooling kit only).",
     "Check pump status and quick-disconnect couplings.", "SEL-0802"),
]

# Pairs of codes that are intentionally similar (exact-match vs dense retrieval demo).
NEAR_DUPLICATES = [("0x4A7B_VRM_OVERVOLT", "0x4A7C_VRM_UNDERVOLT"), ("0x10E4_ECC_MULTI_BIT", "0x10E5_ECC_SINGLE_BIT"),
                   ("0x8F10_TEMP_WARN", "0x8F11_TEMP_CRIT")]

# ----------------------------------------------------------------------------
# Thermal behaviour (figure F5)
# ----------------------------------------------------------------------------
THERMAL = {
    "inlet_warning_c": 35, "inlet_critical_c": 42,
    "cpu_warning_c": 75, "cpu_critical_c": 90,
    "asic_warning_c": 85, "asic_critical_c": 95,
    # (temperature C, fan duty %) control curve
    "fan_curve": [(30, 30), (40, 40), (50, 55), (60, 70), (70, 85), (75, 100), (90, 100)],
    "emergency_shutdown": "BMC shuts the sled down at 90 C CPU temperature after logging 0x8F11_TEMP_CRIT.",
}

# ----------------------------------------------------------------------------
# Network design (figure F7, switch figure F4)
# ----------------------------------------------------------------------------
NETWORK = {
    "vlans": [(101, "PROD_DATA", "Server data plane"), (102, "MGMT_VLAN_102", "Out-of-band management (BMC, MGMT0)"),
              (103, "STORAGE", "NVMe-oF storage traffic"), (104, "PXE_PROVISION", "Bare-metal provisioning")],
    "uplinks": "QSFP28_01-QSFP28_16 go to the spine layer (2 x 400G spine switches SP-1 and SP-2).",
    "server_ports": "QSFP28_17-QSFP28_32 are the server-facing ports; the sled-to-port assignment is recorded in the rack cabling record.",
    "mgmt": "MGMT0 carries only MGMT_VLAN_102 on dedicated 1GbE Base-T; it is never routed through the QSFP28 fabric.",
}

# ----------------------------------------------------------------------------
# Maintenance schedule (figure F9)
# ----------------------------------------------------------------------------
MAINTENANCE = [
    ("Visual LED and cable inspection", "Weekly", "Technician L1", 15),
    ("Clean fan wall filters / dust check", "Monthly", "Technician L1", 30),
    ("Optical transceiver clean and inspect", "Quarterly", "Technician L2", 45),
    ("Rectifier module load test", "Quarterly", "Technician L2", 60),
    ("BMC and BIOS firmware review", "Semi-annual", "Engineer", 90),
    ("Busbar torque check (14 N·m)", "Annual", "Engineer", 120),
    ("Full thermal survey with IR camera", "Annual", "Engineer", 180),
]

# ----------------------------------------------------------------------------
# Firmware compatibility matrix
# ----------------------------------------------------------------------------
FIRMWARE_MATRIX = [
    # BIOS, BMC, switch OS, notes
    ("BIOS 1.8.0", "BMC 2.12.x", "AOS 5.1", "Legacy. Missing watchdog fix (0x9A05)."),
    ("BIOS 1.9.2", "BMC 2.14.3", "AOS 5.2", "Recommended baseline for AOR-3 Rev 3.2."),
    ("BIOS 2.0.0", "BMC 2.14.3", "AOS 5.3", "Adds DDR5 retraining improvements (0x10F0)."),
    ("BIOS 2.0.0", "BMC 2.13.x", "AOS 5.3", "NOT supported: triggers 0x9A10_BMC_FW_MISMATCH."),
]

# Safety facts
SAFETY = {
    "busbar_voltage": "48 V DC can deliver more than 300 A: treat the busbar as a high-energy source.",
    "ppe": "Insulated gloves rated 1000 V, safety glasses, ESD wrist strap.",
    "loto": "Lock-out/tag-out the AC feeder before touching rectifier connections.",
    "torque_busbar_nm": 14,
    "sled_weight_kg": 21,
    "rectifier_weight_kg": 6.5,
    "two_person_lift_kg": 18,
}

# ----------------------------------------------------------------------------
# Documents of the library (each is written from this spec, then rendered to PDF)
# ----------------------------------------------------------------------------
DOCUMENTS = [
    ("aor3_01_system_overview", "AOR-3 System Overview and Architecture", ["F1", "F3", "F7"]),
    ("aor3_02_power_shelf_manual", "Power Shelf PS-3000 Service Manual", ["F2", "F3"]),
    ("aor3_03_thermal_cooling_manual", "Thermal and Cooling Manual", ["F5", "F8"]),
    ("aor3_04_network_switch_manual", "Top-of-Rack Switch AS-100G Manual", ["F4", "F7"]),
    ("aor3_05_bmc_redfish_guide", "BMC, Redfish and CLI Operations Guide", ["F2"]),
    ("aor3_06_fault_code_reference", "Fault Code Reference and Troubleshooting Flowcharts", ["F2", "F6"]),
    ("aor3_07_maintenance_safety", "Preventive Maintenance and Safety Manual", ["F9"]),
    ("aor3_08_release_notes_firmware", "Release Notes and Firmware Compatibility", []),
]

FIGURES = {
    "F1": ("rack_elevation", "Rack elevation of the AOR-3 (U01 at the bottom)"),
    "F2": ("front_panel_led_legend", "Front-panel LED legend: PWR, NET, BMC and ID LEDs"),
    "F3": ("power_distribution_block", "Power distribution: 400 V AC to rectifiers, 48 V busbar, 12 V PoL"),
    "F4": ("switch_port_map", "AS-100G port map: QSFP28 uplinks, server ports, MGMT0 and console"),
    "F5": ("thermal_fan_curve", "Fan duty versus temperature with warning and critical thresholds"),
    "F6": ("troubleshooting_flowchart_amber", "Troubleshooting flowchart for a blinking amber PWR LED"),
    "F7": ("network_topology_vlans", "Leaf-spine topology with VLANs 101-104"),
    "F8": ("dimm_slot_layout", "Compute sled DIMM slot layout (CPU0 A1-A8, CPU1 B1-B8)"),
    "F9": ("maintenance_schedule", "Preventive maintenance schedule by interval"),
}
