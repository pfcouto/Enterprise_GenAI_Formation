"""
Golden evaluation set (34 questions) for both corpora.

Every expected answer is checkable against the source documents:
  * Syone items quote the scraped pages in data/raw_syone_corp (facts as of the scrape date in _manifest.json).
  * Aurora items are derived from scripts/dataset_builder/aurora/spec.py, the single source of truth of the manuals.

Fields
  expected_keywords : strings that a correct answer must contain (case-insensitive)
  expected_docs     : doc_ids that must be among the retrieved/opened documents (retrieval metric, no LLM needed)
  expected_images   : figure files a visual answer should cite
  should_refuse     : the corpus does NOT contain the answer; a good system says so instead of inventing one
  category          : the capability the question probes (shown in the eval table)
"""

from typing import Any, Dict, List

S, H = "syone_corp", "hardware_manuals"


def q(id_, corpus, question, expected_answer, keywords, docs, category, images=None, difficulty="medium", refuse=False):
    return {"id": id_, "corpus": corpus, "question": question, "expected_answer": expected_answer,
            "expected_keywords": keywords, "expected_docs": docs, "expected_images": images or [],
            "category": category, "difficulty": difficulty, "should_refuse": refuse}


GOLDEN_EVALUATION_DATASET: List[Dict[str, Any]] = [
    # ------------------------------------------------------------------ Syone (scraped website)
    q("syone_001", S, "When was Syone founded, where, and how many specialists and countries does the About page mention?",
      "Syone was founded in 1999 in Lisbon; it has 150+ specialists and has delivered solutions in more than 15 countries.",
      ["1999", "Lisbon", "150", "15"], ["about"], "factual", difficulty="easy"),
    q("syone_002", S, "In which regions does the Syone footprint map show that Syone has delivered projects?",
      "The map highlights Portugal, the United Kingdom, Belgium, Germany, Switzerland, Norway, Denmark, Sweden, Cape Verde and Mozambique.",
      ["Portugal", "Scandinavia", "Mozambique"], ["about"], "visual_grounding", images=["syone-footprint-map.png"]),
    q("syone_003", S, "Is Syone an official Zabbix partner in Portugal, and what kind of partner is it?",
      "Yes: Syone is an Official Zabbix Partner and Authorized Reseller in Portugal.",
      ["Official", "Partner", "Authorized Reseller"], ["partners-zabbix-partner"], "faq"),
    q("syone_004", S, "How many devices did Syone monitor during Portugal's national elections, and which technologies did the architecture use?",
      "More than 29,500 devices, using a high-availability architecture based on Zabbix, Grafana and MySQL Cluster.",
      ["29,500", "Zabbix", "Grafana", "MySQL"], ["news-syone-monitored-29500-devices-during-portugals-national-elections"], "factual"),
    q("syone_005", S, "How many consecutive years has Syone renewed its ISO 9001 and ISO 27001 certifications as of the 2025 renewal?",
      "The fourth consecutive year, with zero non-conformities.",
      ["fourth", "ISO 9001", "ISO 27001"], ["news-syone-renews-iso-9001-and-27001-certifications-for-2025"], "factual", difficulty="easy"),
    q("syone_006", S, "What is ezSearch and what key features does it offer?",
      "ezSearch is Syone's AI-powered search tool; features include Intelligent Search, Document Finder, Content Generation, Translation and Key Contact Information.",
      ["ezSearch", "Document Finder", "Content Generation", "Translation"], ["ezsearch-syone"], "factual", images=["ezsearch-banner.jpg"]),
    q("syone_007", S, "In the Elastic Stack diagram on Syone's Elastic partner page, which component handles data shipping and which handles visualization?",
      "Logstash handles data shipping and Kibana handles shaping and visualization (Beats parses data, Elasticsearch provides the analytical capability).",
      ["Logstash", "Kibana"], ["partners-elastic-official-partner"], "text_in_diagram", images=["elastic-stack-layers.jpg"]),
    q("syone_008", S, "Who presented at the Zabbix Meetup '26 for Syone and what was the talk about?",
      "Vitor Carvalho, Senior Account Manager at Syone, presented 'Connecting Odemira: Modernizing public services with Zabbix'.",
      ["Vitor Carvalho", "Odemira"], ["news-syone-zabbix-online-meetup"], "text_in_diagram", images=["zabbix-meetup-2026-poster.jpg"]),
    q("syone_009", S, "What does Syone's nearshore model offer and from which country and time zone do the teams work?",
      "Teams based in Portugal, in a European time zone, managed by Syone while the client controls the outcomes.",
      ["Portugal", "European"], ["how-we-do-it-nearshore-portugal"], "factual"),
    q("syone_010", S, "What support levels does Syone's Service Desk provide?",
      "Level 1 and Level 2 support with centralized contact channels, defined SLAs and various coverage models.",
      ["Level 1", "Level 2", "SLA"], ["what-we-do-service-desk"], "factual", difficulty="easy"),
    q("syone_011", S, "Which monitoring and observability tools does Syone use, and which of them does it hold official partnerships for?",
      "Elastic, Zabbix and Grafana for observability; Syone is the official partner for Zabbix and Elastic in Portugal.",
      ["Elastic", "Zabbix", "Grafana"], ["what-we-do-observability-and-data-monitoring", "partners-zabbix-partner", "partners-elastic-official-partner"],
      "multi_hop_graph", difficulty="hard"),
    q("syone_012", S, "According to Syone's comparison, how does Prometheus collect metrics, and how does that differ from Zabbix?",
      "Prometheus uses a pull-based model scraping metrics over HTTP from exporters; Zabbix is agent/polling based with a broader built-in feature set.",
      ["pull", "HTTP", "exporters"], ["blog-zabbix-vs-prometheus-which-tool-should-you-choose"], "faq"),
    q("syone_013", S, "Where are Syone's offices located?",
      "Lisbon (Ed. Stern, R. Alfredo da Silva) and Porto (Matosinhos, Javacowork).",
      ["Lisboa", "Porto"], ["contact-us"], "factual", difficulty="easy"),
    q("syone_014", S, "What was Syone's revenue in 2030 and what is its stock market ticker?",
      "The knowledge base does not contain this information (it is out of scope).",
      [], [], "no_answer", refuse=True, difficulty="hard"),

    # ------------------------------------------------------------------ Aurora AOR-3 (synthetic manuals)
    q("hw_001", H, "What is the root cause and required remediation for fault code 0x4A7B_VRM_OVERVOLT?",
      "The busbar input voltage exceeded the 54.2 V cutoff. Engage the secondary backup PSU and replace PDB fuse F2.",
      ["0x4A7B_VRM_OVERVOLT", "54.2", "F2"], ["aor3_06_fault_code_reference", "aor3_02_power_shelf_manual"], "bm25_exact_match"),
    q("hw_002", H, "What does fault 0x4A7C_VRM_UNDERVOLT mean and how does it differ from 0x4A7B_VRM_OVERVOLT?",
      "0x4A7C is an undervoltage event below 40.5 V (Major, blinking amber); 0x4A7B is an overvoltage above 54.2 V (Critical, solid red).",
      ["40.5", "54.2", "undervolt"], ["aor3_06_fault_code_reference"], "near_duplicate_codes", difficulty="hard"),
    q("hw_003", H, "What does a blinking amber PWR LED mean, and where can I see the full LED legend?",
      "Blinking amber at 1 Hz signals a thermal warning above 75 C (fans forced to 100 %, CPU throttled); other faults share the LED so the SEL code decides. Figure F2 shows the legend.",
      ["Blinking amber", "75", "Figure F2"], ["aor3_02_power_shelf_manual", "aor3_05_bmc_redfish_guide"], "visual_grounding",
      images=["F2_front_panel_led_legend.png"]),
    q("hw_004", H, "What does a solid blue BMC LED indicate and what must the technician not do?",
      "The BMC is booting or a firmware update is in progress; do not power cycle.",
      ["Solid blue", "firmware", "power cycle"], ["aor3_05_bmc_redfish_guide"], "visual_grounding", images=["F2_front_panel_led_legend.png"]),
    q("hw_005", H, "Which fault code reports an uncorrectable multi-bit error on DIMM_A2 and what should be done?",
      "0x10E4_ECC_MULTI_BIT: halt the node and replace the DIMM in slot A2.",
      ["0x10E4_ECC_MULTI_BIT", "A2", "replace"], ["aor3_06_fault_code_reference", "aor3_07_maintenance_safety"], "bm25_exact_match"),
    q("hw_006", H, "How do 0x10E4_ECC_MULTI_BIT and 0x10E5_ECC_SINGLE_BIT differ in severity and action?",
      "0x10E4 is critical (multi-bit, DIMM_A2, replace immediately); 0x10E5 is a warning (single-bit errors on DIMM_B5 above 24 per hour, schedule replacement).",
      ["Critical", "Warning", "DIMM_B5"], ["aor3_06_fault_code_reference"], "near_duplicate_codes", difficulty="hard"),
    q("hw_007", H, "Which port on the AS-100G is used for out-of-band management and which VLAN does it carry?",
      "MGMT0 (RJ45, 1GbE Base-T) carrying MGMT_VLAN_102.",
      ["MGMT0", "MGMT_VLAN_102"], ["aor3_04_network_switch_manual"], "text_in_diagram", images=["F4_switch_port_map.png"]),
    q("hw_008", H, "Which QSFP28 ports are uplinks and which connect to the compute sleds?",
      "QSFP28_01-QSFP28_16 are uplinks to the spine; QSFP28_17-QSFP28_32 are server-facing ports.",
      ["QSFP28_01", "QSFP28_16", "QSFP28_17", "QSFP28_32"], ["aor3_04_network_switch_manual"], "table_lookup", images=["F4_switch_port_map.png"]),
    q("hw_009", H, "In which rack units is the power shelf installed, and what sits directly above it?",
      "The PS-3000 power shelf occupies U20-U22; the AS-100G top-of-rack switch is at U23 directly above it.",
      ["U20", "U22", "U23"], ["aor3_01_system_overview"], "visual_grounding", images=["F1_rack_elevation.png"]),
    q("hw_010", H, "At what CPU temperature do the fans reach 100 % duty and when does the BMC shut the sled down?",
      "Fans reach 100 % at 75 C (warning, 0x8F10_TEMP_WARN); at 90 C the BMC performs an emergency shutdown (0x8F11_TEMP_CRIT).",
      ["75", "90", "0x8F11_TEMP_CRIT"], ["aor3_03_thermal_cooling_manual"], "text_in_diagram", images=["F5_thermal_fan_curve.png"]),
    q("hw_011", H, "Which DIMM slots belong to CPU1 on the compute sled?",
      "CPU1 owns slots B1 to B8 (CPU0 owns A1-A8).",
      ["B1", "B8"], ["aor3_03_thermal_cooling_manual"], "text_in_diagram", images=["F8_dimm_slot_layout.png"]),
    q("hw_012", H, "A sled shows a blinking amber PWR LED. What is the first troubleshooting step?",
      "Read the System Event Log (bmc-cli sel list) to get the newest event code, then follow the branch for that code family.",
      ["SEL", "bmc-cli"], ["aor3_06_fault_code_reference"], "visual_grounding", images=["F6_troubleshooting_flowchart_amber.png"]),
    q("hw_013", H, "Which command warm-resets the BMC and which fault code does that remediation belong to?",
      "bmc-reset --warm, for 0x99A0_PSU_COMM_LOST (PMBus communication lost).",
      ["bmc-reset --warm", "0x99A0_PSU_COMM_LOST"], ["aor3_05_bmc_redfish_guide", "aor3_06_fault_code_reference"], "bm25_exact_match"),
    q("hw_014", H, "Which Thermal-subsystem fault codes are critical and show a solid red PWR LED?",
      "0x8F02_FAN_ALL_FAIL and 0x8F11_TEMP_CRIT (also 0x5F01_COOLANT_LEAK for the optional liquid-cooling kit).",
      ["0x8F02_FAN_ALL_FAIL", "0x8F11_TEMP_CRIT"], ["aor3_06_fault_code_reference", "aor3_03_thermal_cooling_manual"], "multi_hop_graph", difficulty="hard"),
    q("hw_015", H, "Which BMC firmware version is the recommended baseline for Rev 3.2 and which combination triggers 0x9A10_BMC_FW_MISMATCH?",
      "BMC 2.14.3 (with BIOS 1.9.2 and AOS 5.2); BIOS 2.0.0 with BMC 2.13.x is not supported and triggers 0x9A10_BMC_FW_MISMATCH.",
      ["2.14.3", "0x9A10_BMC_FW_MISMATCH", "2.13"], ["aor3_08_release_notes_firmware"], "table_lookup"),
    q("hw_016", H, "What torque value applies to the busbar connections and which personal protective equipment is required?",
      "14 N-m for busbar connections; insulated gloves rated 1000 V, safety glasses and an ESD wrist strap.",
      ["14", "1000 V", "gloves"], ["aor3_07_maintenance_safety"], "table_lookup"),
    q("hw_017", H, "How often must optical transceivers be cleaned and inspected, and by which role?",
      "Quarterly, by Technician L2 (about 45 minutes planned).",
      ["Quarterly", "L2"], ["aor3_07_maintenance_safety"], "table_lookup", images=["F9_maintenance_schedule.png"]),
    q("hw_018", H, "How many rectifier modules does the PS-3000 hold and how is redundancy arranged?",
      "Six 3 kW rectifier modules (R1-R6) in an N+1 arrangement (5 active + 1 spare), 15 kW maximum.",
      ["six", "3 kW", "N+1"], ["aor3_02_power_shelf_manual", "aor3_01_system_overview"], "factual", difficulty="easy"),
    q("hw_019", H, "Which hardware component raises the Network PHY fault codes and which LED shows 'no link'?",
      "The AS-100G switch / sled NICs raise 0xC029 etc.; the NET LED is off when there is no link (0xC029_ETH_PHY_LINKDN).",
      ["NET", "0xC029_ETH_PHY_LINKDN"], ["aor3_06_fault_code_reference", "aor3_04_network_switch_manual"], "multi_hop_graph", difficulty="hard"),
    q("hw_020", H, "What is the warranty period of the AS-100G switch?",
      "The manuals do not state a warranty period (out of scope).",
      [], [], "no_answer", refuse=True, difficulty="hard"),
]

# A cheap slice for live sessions: one question per capability, including Track A's known failure syone_013, so the
# judges have something to disagree about. Track A on these 8 questions costs well under one cent.
DEMO_SLICE = ["hw_001", "hw_002", "hw_003", "hw_007", "hw_014", "syone_003", "syone_013", "syone_014"]


def get_dataset_by_corpus(corpus: str = "all") -> List[Dict[str, Any]]:
    if corpus == "all":
        return GOLDEN_EVALUATION_DATASET
    return [d for d in GOLDEN_EVALUATION_DATASET if d.get("corpus") == corpus]
