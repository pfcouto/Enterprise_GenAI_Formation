"""
Domain gazetteers shared by the OKF compiler (tags / related links) and the graph entity extractor.

A gazetteer is a small, explicit vocabulary of the things we care about in each corpus. It is NOT the
knowledge itself: all facts (tiers, fault-code causes, LED states, ...) are read from the documents.
Adding a new partner or component to the demo means adding one line here.
"""

import re
from typing import Dict, List

# ----------------------------------------------------------------------------------------------
# Corpus 1: Syone (scraped from syone.com)
# ----------------------------------------------------------------------------------------------
# canonical name -> aliases that count as a mention (case-insensitive, word-boundary matched)
SYONE_PARTNERS: Dict[str, List[str]] = {
    "Red Hat": ["red hat", "redhat", "openshift", "rhel", "ansible"],
    "Elastic": ["elastic", "elasticsearch", "kibana", "logstash"],
    "Zabbix": ["zabbix"],
    "Microsoft": ["microsoft", "azure"],
    "SUSE": ["suse", "rancher"],
    "Camunda": ["camunda"],
    "GitLab": ["gitlab"],
    "Syntevo": ["syntevo", "smartgit"],
}

SYONE_TECHNOLOGIES: Dict[str, List[str]] = {
    "Angular": ["angular"], "React": ["react"], "JavaScript": ["javascript"], "Java": ["java"],
    "Kotlin": ["kotlin"], "Flutter": ["flutter"], "Swift": ["swift"], "Spring": ["spring boot", "spring framework", "spring"],
    "C#/.NET": [".net", "c#"], "Kubernetes": ["kubernetes"], "OpenShift": ["openshift"], "Docker": ["docker"],
    "Ansible": ["ansible"], "Prometheus": ["prometheus"], "Grafana": ["grafana"], "Elasticsearch": ["elasticsearch"],
    "Kibana": ["kibana"], "Logstash": ["logstash"], "Proxmox": ["proxmox"], "VMware": ["vmware"],
    "RHEL": ["rhel", "red hat enterprise linux"], "OpenSearch": ["opensearch"], "Terraform": ["terraform"],
    "CI/CD": ["ci/cd"], "SharePoint": ["sharepoint"],
}

SYONE_OTHER: Dict[str, Dict[str, List[str]]] = {
    "Certification": {"ISO 9001": ["iso 9001"], "ISO 27001": ["iso 27001"]},
    "Location": {"Lisbon": ["lisboa", "lisbon"], "Porto": ["porto", "matosinhos"], "Portugal": ["portugal"]},
    "Solution": {"ezSearch": ["ezsearch"]},
    "Event": {"Open Source Lisbon": ["open source lisbon"], "Zabbix Meetup": ["zabbix meetup", "zabbix online meetup"]},
}

# Section (first URL segment, see scraper) -> the kind of entity the page itself is about
SECTION_ENTITY_KIND = {
    "partners": "Partner", "what-we-do": "Service", "how-we-do-it": "DeliveryModel", "technologies": "Technology",
    "ezsearch-syone": "Solution", "news": "NewsItem", "blog": "Article",
}

# ----------------------------------------------------------------------------------------------
# Corpus 2: Aurora AOR-3 hardware manuals (synthetic)
# ----------------------------------------------------------------------------------------------
HARDWARE_COMPONENTS: Dict[str, List[str]] = {
    "PS-3000 power shelf": ["ps-3000", "power shelf", "rectifier"],
    "CS-2U compute sled": ["cs-2u", "compute sled"],
    "FW-6 fan wall": ["fw-6", "fan wall", "fan module"],
    "AS-100G switch": ["as-100g", "top-of-rack switch", "qsfp28"],
    "BMC (OpenBMC)": ["bmc", "openbmc", "redfish"],
    "48 V busbar": ["busbar"],
    "PDB": ["pdb", "power distribution board", "fuse f2"],
}

FAULT_CODE_RE = re.compile(r"\b(0x[0-9A-F]{4})_([A-Z0-9_]+)\b")
FRU_RE = re.compile(r"\b(DIMM_[AB][1-8]|QSFP28_\d{2}|FM[1-6]|R[1-6](?=\b)|SP-[12]|NVMe bay [12]|MGMT_VLAN_\d+|MGMT0)\b")
LED_STATE_RE = re.compile(r"\b(Solid|Blinking)\s+(green|amber|red|blue|white)\b[^|]*?\b(PWR|NET|BMC|ID)\b", re.I)

STOPWORDS = {
    "the", "and", "for", "what", "which", "that", "this", "with", "from", "does", "how", "are", "was", "were",
    "have", "has", "when", "where", "who", "why", "should", "would", "could", "their", "there", "about", "into",
    "your", "you", "can", "any", "all", "not", "but", "its", "than", "then", "them", "they", "will", "also",
}


def find_mentions(text: str, vocab: Dict[str, List[str]]) -> List[str]:
    """Canonical names from `vocab` whose aliases appear in `text` (word-boundary, case-insensitive)."""
    low = text.lower()
    found = []
    for canon, aliases in vocab.items():
        for a in aliases:
            if re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", low):
                found.append(canon)
                break
    return found
