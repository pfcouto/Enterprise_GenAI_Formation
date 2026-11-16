#!/usr/bin/env python3
"""
Renders the nine Aurora AOR-3 figures (F1-F9) as PNGs, straight from spec.py.

Every number, label, port and code drawn here comes from the spec, so the pictures cannot drift from the manuals.
Pure matplotlib: no browser or external tool needed.

Usage: python scripts/dataset_builder/aurora/render_figures.py
Output: scripts/dataset_builder/aurora/figures/F<n>_<stem>.png (+ figure_captions.json, a text description of each
        figure that ingestion uses as the machine-readable caption)
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, FancyArrowPatch

sys.path.insert(0, str(Path(__file__).parent))
import spec  # noqa: E402

OUT = Path(__file__).parent / "figures"
INK, MUTED, LINE, PAPER = "#1f2937", "#6b7280", "#9ca3af", "#ffffff"
GREEN, AMBER, RED, BLUE, WHITE_LED = "#16a34a", "#f59e0b", "#dc2626", "#2563eb", "#e5e7eb"
TINT = {"blue": "#dbeafe", "green": "#dcfce7", "amber": "#fef3c7", "red": "#fee2e2", "gray": "#f3f4f6", "violet": "#ede9fe"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "text.color": INK, "axes.edgecolor": LINE})


def canvas(w=11, h=6.2, title=None, subtitle=None, ymax=100):
    fig, ax = plt.subplots(figsize=(w, h), dpi=150)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, ymax)
    ax.axis("off")
    fig.patch.set_facecolor(PAPER)
    if title:
        ax.text(2, ymax - 2, title, fontsize=15, fontweight="bold", va="top")
    if subtitle:
        ax.text(2, ymax - 7.5, subtitle, fontsize=9.5, color=MUTED, va="top")
    return fig, ax


def box(ax, x, y, w, h, text="", fc="gray", ec=LINE, fs=10, bold=False, lw=1.4, align="center", color=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.8", fc=TINT.get(fc, fc), ec=ec, lw=lw))
    if text:
        tx = x + w / 2 if align == "center" else x + 1.2
        ax.text(tx, y + h / 2, text, ha=align, va="center", fontsize=fs, fontweight="bold" if bold else "normal", color=color)


def arrow(ax, x1, y1, x2, y2, color=MUTED, lw=1.6, style="-|>"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=12, color=color, lw=lw, shrinkA=0, shrinkB=0))


def save(fig, key):
    stem = spec.FIGURES[key][0]
    path = OUT / f"{key}_{stem}.png"
    fig.savefig(path, facecolor=PAPER, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print(f"  rendered {path.name}")
    return path


# ---------------------------------------------------------------- F1
def f1():
    fig, ax = canvas(10, 9.4, "Aurora Open Rack AOR-3: rack elevation", f"{spec.DOC_REV}. U01 is at the bottom of the rack.")
    base, unit = 3.0, 1.95
    rx, rw = 9, 36
    ax.add_patch(Rectangle((rx - 1.5, base - 1), rw + 3, 42 * unit + 2, fc="#f9fafb", ec=INK, lw=2))

    def yof(u):  # bottom edge of rack unit u (U01 = bottom)
        return base + (u - 1) * unit

    for u in range(1, 43):
        ax.add_patch(Rectangle((rx, yof(u)), rw, unit, fc="none", ec="#e5e7eb", lw=0.5))
        if u in (1, 2, 20, 23, 24, 25, 42) or u % 5 == 0:
            ax.text(rx - 2, yof(u) + unit / 2, f"U{u:02d}", ha="right", va="center", fontsize=6.5, color=MUTED)

    def block(u0, u1, text, fc, ec, fs=8.5):
        box(ax, rx + 0.5, yof(u0) + 0.15, rw - 1, (u1 - u0 + 1) * unit - 0.3, text, fc=fc, ec=ec, fs=fs, bold=True)

    block(1, 1, "Cable management / blank panel", "gray", LINE, 7)
    for k in range(9):
        a = 2 + 2 * k
        box(ax, rx + 0.5, yof(a) + 0.15, rw - 1, 2 * unit - 0.3, f"CS-2U sled {k + 1}  (U{a:02d}-U{a + 1:02d})", fc="blue", ec=BLUE, fs=7.2)
    block(20, 22, "Power shelf PS-3000 (R1-R6)", "amber", AMBER)
    block(23, 23, "AS-100G switch", "violet", "#7c3aed", 7.5)
    block(24, 24, "Patch panel", "gray", LINE, 7)
    block(25, 42, "Reserved / future expansion", "gray", LINE)
    notes = [
        (1, "U01: cable management / blank panel", "gray"),
        (10.5, "U02-U19: nine CS-2U compute sleds (two units each),\nfan wall FW-6 at the rear", "blue"),
        (21, "U20-U22: PS-3000, six 3 kW rectifiers, N+1,\n48 V DC busbar", "amber"),
        (23, "U23: AS-100G switch: 32 x QSFP28 + MGMT0", "violet"),
        (24.7, "U24: patch panel (QSFP28 breakout)", "gray"),
        (33.5, "U25-U42: reserved / future expansion", "gray"),
    ]
    ys = {1: 6, 10.5: 30, 21: 56, 23: 66, 24.7: 76, 33.5: 86}
    for u, t, c in notes:
        yy = ys[u]
        box(ax, 52, yy - 2.6, 46, 5.2, t, fc=c, fs=8.5, align="left")
        arrow(ax, 52, yy, rx + rw + 0.5, yof(u) + unit / 2 if u not in (10.5, 21, 33.5) else yof(u) + unit, color=LINE, lw=1)
    return save(fig, "F1")


# ---------------------------------------------------------------- F2
def f2():
    fig, ax = canvas(12, 7.6, "Front-panel LED legend", "Each sled has four LEDs, left to right: PWR, NET, BMC, ID. The LED is coarse; the SEL fault code is precise.")
    colors = {"green": GREEN, "amber": AMBER, "red": RED, "blue": BLUE, "white": WHITE_LED, "off": "#4b5563"}

    def led_color(label):
        low = label.lower()
        for k in ("green", "amber", "red", "blue", "white"):
            if k in low:
                return colors[k]
        return colors["off"]

    y = 88
    for led in spec.LEDS:
        height = 4.3 * len(led["states"]) + 6
        y -= height
        box(ax, 2, y, 96, height - 1.2, "", fc="#f9fafb", ec=LINE)
        ax.text(4, y + height - 3.6, f"LED {led['position']}: {led['id']}", fontsize=11, fontweight="bold")
        ax.text(4, y + height - 7.6, led["name"], fontsize=8.5, color=MUTED)
        for i, (state, desc) in enumerate(led["states"]):
            yy = y + height - 4.2 - 4.3 * (i + 0.5)
            ax.plot(27, yy, "o", ms=12, mfc=led_color(state), mec=INK, mew=1)
            ax.text(31, yy, state, fontsize=9.2, fontweight="bold", va="center")
            short = desc if len(desc) < 92 else desc[:89].rsplit(" ", 1)[0] + " ..."
            ax.text(50, yy, short, fontsize=7.4, va="center", color=INK)
        y -= 1.2
    return save(fig, "F2")


# ---------------------------------------------------------------- F3
def f3():
    ps = spec.COMPONENTS["PS-3000"]["specs"]
    fig, ax = canvas(12, 5.4, "Power distribution: 400 V AC to 48 V busbar to 12 V PoL", "Left to right: mains feed, power shelf, busbar and protection, compute sled, management plane.", ymax=72)
    y = 30
    box(ax, 1, y, 13, 22, "3-phase\n400 V AC mains\nL1  L2  L3", fc="gray", fs=9, bold=True)
    box(ax, 19, y - 4, 22, 30, "", fc="amber", ec=AMBER)
    ax.text(30, y + 22, "Power shelf PS-3000", ha="center", fontsize=10, fontweight="bold")
    for i in range(6):
        r, c = divmod(i, 3)
        box(ax, 20.5 + c * 6.3, y + 9 - r * 8.5, 5.6, 7, f"R{i + 1}\n3 kW", fc="#fde68a", ec=AMBER, fs=7.5)
    ax.text(30, y - 2.5, "6 x 3 kW rectifiers, N+1 (5 active + 1 spare)", ha="center", fontsize=7.5, color=MUTED)
    box(ax, 46, y + 2, 15, 18, f"48 V DC busbar\nrange {ps['busbar_range_v']}\nOVP cutoff {ps['ovp_cutoff_v']} V\nUVP cutoff {ps['uvp_cutoff_v']} V", fc="red", ec=RED, fs=8, bold=True)
    box(ax, 66, y + 6, 11, 10, "PDB fuse F2\n(30 A, 80 V DC)", fc="gray", fs=8)
    box(ax, 82, y - 4, 16, 30, "", fc="blue", ec=BLUE)
    ax.text(90, y + 22, "Compute sled CS-2U", ha="center", fontsize=9.5, fontweight="bold")
    box(ax, 84, y + 10, 12, 8, "PoL stage\n48 V -> 12 V", fc="#bfdbfe", ec=BLUE, fs=8)
    box(ax, 84, y, 12, 8, "CPU0 / CPU1\nDDR5 DIMMs", fc="#bfdbfe", ec=BLUE, fs=8)
    for (x1, x2) in ((14, 19), (41, 46), (61, 66), (77, 82)):
        arrow(ax, x1, y + 12, x2, y + 12)
    box(ax, 40, 3, 36, 9, "BMC polls PMBus every 2 s\n(fault 0x99A0_PSU_COMM_LOST if lost)", fc="violet", ec="#7c3aed", fs=8.5)
    arrow(ax, 58, 12, 33, y - 4, color="#7c3aed", lw=1.2, style="<|-|>")
    arrow(ax, 76, 8, 88, y - 4, color="#7c3aed", lw=1.2, style="<|-|>")
    return save(fig, "F3")


# ---------------------------------------------------------------- F4
def f4():
    fig, ax = canvas(12, 4.2, "AS-100G front panel and port map", "32 x QSFP28 (100 GbE), MGMT0 (1GbE Base-T, MGMT_VLAN_102) and an RJ45 serial console. Port names use the QSFP28_nn format.", ymax=62)
    box(ax, 2, 18, 96, 30, "", fc="#f9fafb", ec=INK, lw=2)
    box(ax, 4, 22, 11, 9, "MGMT0\nRJ45 1GbE\nMGMT_VLAN_102", fc="amber", ec=AMBER, fs=7)
    box(ax, 4, 34, 11, 9, "CONSOLE\nRJ45 serial\n115200 8N1", fc="gray", fs=7)
    for n in range(1, 33):
        row = 0 if n <= 16 else 1
        col = (n - 1) % 16
        x = 19 + col * 4.85
        y = 34 if row == 0 else 22
        fc = "violet" if n <= 16 else "green"
        ec = "#7c3aed" if n <= 16 else GREEN
        box(ax, x, y, 4.1, 9, f"{n:02d}", fc=fc, ec=ec, fs=7.5, bold=True)
    ax.text(19, 45.2, "QSFP28_01 - QSFP28_16: uplinks to spine SP-1 / SP-2", fontsize=8.5, color="#6d28d9", fontweight="bold")
    ax.text(19, 19.6, "QSFP28_17 - QSFP28_32: server ports to compute sleds", fontsize=8.5, color="#15803d", fontweight="bold")
    ax.text(2, 11, "ASIC: Aurora TS-3200, 3.2 Tbps aggregate port capacity.  Management traffic is never routed through the QSFP28 fabric.", fontsize=8.5, color=MUTED)
    ax.text(2, 6, "Fault examples: port QSFP28_12 link down = 0xC029_ETH_PHY_LINKDN;  QSFP28_21 degraded to 25 GbE = 0xC02A_ETH_PHY_DEGRADED.", fontsize=8.5, color=MUTED)
    return save(fig, "F4")


# ---------------------------------------------------------------- F5
def f5():
    t = spec.THERMAL
    fig, ax = plt.subplots(figsize=(11, 6), dpi=150)
    xs, ys = zip(*t["fan_curve"])
    ax.plot(xs, ys, "-o", color=BLUE, lw=2.5, ms=6, label="Fan duty (%)")
    ax.axvspan(t["cpu_warning_c"], t["cpu_critical_c"], color="#fef3c7", alpha=0.8, label="Warning zone: blinking amber, CPU throttled")
    ax.axvline(t["cpu_warning_c"], color=AMBER, lw=2, ls="--")
    ax.axvline(t["cpu_critical_c"], color=RED, lw=2, ls="--")
    ax.text(t["cpu_warning_c"] - 0.6, 36, f"{t['cpu_warning_c']} C\nwarning\n(0x8F10_TEMP_WARN)", ha="right", color="#b45309", fontsize=9, fontweight="bold")
    ax.text(t["cpu_critical_c"] - 0.6, 36, f"{t['cpu_critical_c']} C\ncritical, shutdown\n(0x8F11_TEMP_CRIT)", ha="right", color=RED, fontsize=9, fontweight="bold")
    ax.annotate("100 % duty from 75 C", (75, 100), (58, 104), arrowprops=dict(arrowstyle="->", color=MUTED), fontsize=9)
    ax.set_xlabel("CPU package temperature (C)")
    ax.set_ylabel("Fan duty (%)")
    ax.set_ylim(20, 112)
    ax.set_xlim(28, 92)
    ax.grid(True, color="#e5e7eb")
    ax.set_title("Fan duty versus temperature (AOR-3 fan wall FW-6)", loc="left", fontsize=14, fontweight="bold")
    ax.legend(loc="lower right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return save(fig, "F5")


# ---------------------------------------------------------------- F6
def f6():
    fig, ax = canvas(12, 8, "Troubleshooting flowchart: blinking amber PWR LED", "The amber LED is shared by many faults: always read the SEL code first.")
    box(ax, 38, 80, 24, 6, "PWR LED blinking amber", fc="amber", ec=AMBER, bold=True, fs=10)
    box(ax, 33, 68, 34, 7, "Read the SEL:  bmc-cli sel list\n(newest event code)", fc="gray", fs=9.5)
    arrow(ax, 50, 80, 50, 75.2)
    branches = [
        (2, "Thermal\n0x8F10 TEMP_WARN\n0x8F20 AIRFLOW_BLOCK", "Check blanking panels,\nairflow, ambient temp", "red"),
        (21, "Fan\n0x8F01 FAN_TACH_FAIL", "Reseat / swap\nFan Module FM4", "red"),
        (40, "Power\n0x4A7C UNDERVOLT\n0x4B10 RECT_FAIL", "Check rectifiers R1-R6,\nreplace failed unit", "amber"),
        (59, "Memory / storage\n0x10F0 TRAINING_FAIL\n0x2B31 NVME_LINK_DOWN", "Reseat DIMM_A7 or\nNVMe bay 2", "blue"),
        (78, "Other\n0xC055 ASIC_TEMP\n0x6E20 TPM_ATTEST_FAIL", "Switch fan trays / quarantine\nsled and re-enroll TPM", "violet"),
    ]
    for x, label, action, c in branches:
        box(ax, x, 48, 19, 11, label, fc="gray", fs=7.6, bold=True)
        box(ax, x, 30, 19, 11, action, fc=c, fs=7.8)
        arrow(ax, 50, 68, x + 9.5, 59.2, lw=1.2)
        arrow(ax, x + 9.5, 48, x + 9.5, 41.2, lw=1.2)
        box(ax, x, 15, 19, 9, "Verify: LED solid green,\nSEL entry cleared", fc="green", ec=GREEN, fs=7.8)
        arrow(ax, x + 9.5, 30, x + 9.5, 24.2, lw=1.2)
    box(ax, 15, 2.5, 70, 7, "Still amber after the fix, or code repeats: escalate to Technician L2 / Engineer", fc="red", ec=RED, fs=9, bold=True)
    return save(fig, "F6")


# ---------------------------------------------------------------- F7
def f7():
    fig, ax = canvas(12, 5.8, "Leaf-spine topology and VLANs", "Two 400G spines, one AS-100G top-of-rack switch per rack, out-of-band management on its own VLAN.", ymax=72)
    box(ax, 22, 52, 18, 7, "Spine SP-1 (400G)", fc="violet", ec="#7c3aed", bold=True, fs=9)
    box(ax, 56, 52, 18, 7, "Spine SP-2 (400G)", fc="violet", ec="#7c3aed", bold=True, fs=9)
    box(ax, 33, 32, 30, 8, "AS-100G top-of-rack (U23)\nuplinks QSFP28_01-16", fc="blue", ec=BLUE, bold=True, fs=9)
    for sx in (31, 65):
        arrow(ax, 48, 40.2, sx, 51.8, color="#7c3aed", style="<|-|>")
    for i in range(4):
        x = 6 + i * 22
        box(ax, x, 12, 18, 8, f"CS-2U sled\n(QSFP28_{17 + i})", fc="green", ec=GREEN, fs=8)
        arrow(ax, 48, 32, x + 9, 20.2, color=GREEN, style="<|-|>", lw=1.2)
    box(ax, 80, 30, 18, 14, "MGMT0 (1GbE)\nBMCs + switch\nMGMT_VLAN_102", fc="amber", ec=AMBER, fs=8.5, bold=True)
    arrow(ax, 63, 36, 80, 36, color=AMBER, style="<|-|>")
    y = 6.5
    ax.text(2, y, "VLANs:", fontsize=9, fontweight="bold")
    x = 9
    for vid, name, desc in spec.NETWORK["vlans"]:
        ax.text(x, y, f"{vid}  {name}", fontsize=8.3, color=INK)
        x += 22
    return save(fig, "F7")


# ---------------------------------------------------------------- F8
def f8():
    fig, ax = canvas(12, 5.0, "Compute sled DIMM slot layout", "CPU0 owns slots A1-A8, CPU1 owns B1-B8. Highlighted slots are the ones named in the fault codes.", ymax=72)
    marked = {"A2": ("red", "0x10E4_ECC_MULTI_BIT"), "A7": ("amber", "0x10F0_DIMM_TRAINING_FAIL"), "B5": ("blue", "0x10E5_ECC_SINGLE_BIT")}
    for row, (cpu, letter, y) in enumerate((("CPU0", "A", 42), ("CPU1", "B", 14))):
        box(ax, 2, y, 12, 18, f"{cpu}\n(socket {row})", fc="gray", fs=10, bold=True)
        for n in range(1, 9):
            key = f"{letter}{n}"
            fc, tag = marked.get(key, ("green", ""))
            ec = {"red": RED, "amber": AMBER, "blue": BLUE, "green": GREEN}[fc]
            box(ax, 18 + (n - 1) * 10.2, y, 8.6, 18, "", fc=fc, ec=ec, lw=1.6)
            ax.text(18 + (n - 1) * 10.2 + 4.3, y + 12, key, ha="center", fontsize=10, fontweight="bold")
            ax.text(18 + (n - 1) * 10.2 + 4.3, y + 6, "DDR5\n5600", ha="center", fontsize=6.5, color=MUTED)
    ly = 7
    x = 4
    for key, (fc, code) in marked.items():
        ec = {"red": RED, "amber": AMBER, "blue": BLUE}[fc]
        ax.add_patch(Rectangle((x, ly - 1), 3, 3, fc=TINT[fc], ec=ec, lw=1.4))
        ax.text(x + 4, ly + 0.4, f"DIMM_{key}: {code}", fontsize=8.4, va="center")
        x += 32
    return save(fig, "F8")


# ---------------------------------------------------------------- F9
def f9():
    fig, ax = plt.subplots(figsize=(11, 5.6), dpi=150)
    pal = {"Weekly": GREEN, "Monthly": BLUE, "Quarterly": AMBER, "Semi-annual": "#7c3aed", "Annual": RED}
    tasks = list(reversed(spec.MAINTENANCE))
    for i, (task, interval, who, minutes) in enumerate(tasks):
        ax.barh(i, minutes, color=pal[interval], height=0.6)
        ax.text(minutes + 2, i, f"{minutes} min  |  {interval}  |  {who}", va="center", fontsize=8.8)
    ax.set_yticks(range(len(tasks)))
    ax.set_yticklabels([t[0] for t in tasks], fontsize=9.5)
    ax.set_xlim(0, 330)
    ax.set_xlabel("Planned time per rack (minutes)")
    ax.set_title("Preventive maintenance schedule", loc="left", fontsize=14, fontweight="bold")
    ax.grid(axis="x", color="#e5e7eb")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    handles = [Rectangle((0, 0), 1, 1, color=c) for c in pal.values()]
    ax.legend(handles, pal.keys(), title="Interval", loc="lower right")
    return save(fig, "F9")


def captions():
    """Machine-readable descriptions of what each figure shows (text that is IN the picture)."""
    c = spec
    led_lines = "; ".join(f"{l['id']} LED {s[0]}: {s[1]}" for l in c.LEDS for s in l["states"])
    return {
        "F1": "Rack elevation of the AOR-3. " + " ".join(f"{u}: {d}." for u, d in c.RACK_ELEVATION),
        "F2": "Front-panel LED legend with four LEDs (PWR, NET, BMC, ID) and their states. " + led_lines,
        "F3": "Power distribution block diagram: 3-phase 400 V AC mains feed the PS-3000 power shelf (six 3 kW rectifiers R1-R6, N+1), "
              "which feeds a 48 V DC busbar (range 44.0-52.0 V, OVP cutoff 54.2 V, UVP cutoff 40.5 V) through PDB fuse F2 (30 A) "
              "to each compute sled's PoL stage (48 V to 12 V). The BMC polls PMBus every 2 seconds.",
        "F4": "AS-100G port map. Top row QSFP28_01-QSFP28_16 are uplinks to the spine; bottom row QSFP28_17-QSFP28_32 are server ports. "
              "MGMT0 (RJ45 1GbE, MGMT_VLAN_102) and the serial console (RJ45, 115200 8N1) are on the left. ASIC Aurora TS-3200, 3.2 Tbps.",
        "F5": "Line chart of fan duty (%) versus CPU temperature (C): 30 C 30 %, 40 C 40 %, 50 C 55 %, 60 C 70 %, 70 C 85 %, 75 C 100 %, 90 C 100 %. "
              "Warning threshold at 75 C (blinking amber, 0x8F10_TEMP_WARN); critical threshold and emergency shutdown at 90 C (0x8F11_TEMP_CRIT).",
        "F6": "Flowchart for a blinking amber PWR LED: read the SEL with bmc-cli sel list, then branch by code family - thermal (0x8F10, 0x8F20): check airflow; "
              "fan (0x8F01): swap Fan Module FM4; power (0x4A7C, 0x4B10): check rectifiers R1-R6; memory/storage (0x10F0, 0x2B31): reseat DIMM_A7 or NVMe bay 2; "
              "other (0xC055, 0x6E20): switch fan trays or quarantine the sled. Verify LED is solid green; otherwise escalate to Technician L2 or Engineer.",
        "F7": "Leaf-spine topology: two 400G spines SP-1 and SP-2 connect to the AS-100G top-of-rack switch (uplinks QSFP28_01-16), which connects the compute sleds "
              "(QSFP28_17 onward). MGMT0 carries MGMT_VLAN_102 for BMCs. VLANs: " + "; ".join(f"{v} {n}" for v, n, _ in c.NETWORK["vlans"]) + ".",
        "F8": "DIMM slot layout: CPU0 has slots A1-A8, CPU1 has slots B1-B8. Highlighted: DIMM_A2 (0x10E4_ECC_MULTI_BIT, red), "
              "DIMM_A7 (0x10F0_DIMM_TRAINING_FAIL, amber), DIMM_B5 (0x10E5_ECC_SINGLE_BIT, blue).",
        "F9": "Bar chart of preventive maintenance tasks and planned minutes: " + "; ".join(f"{t} ({i}, {w}, {m} min)" for t, i, w, m in c.MAINTENANCE) + ".",
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("Rendering Aurora AOR-3 figures from spec.py")
    for fn in (f1, f2, f3, f4, f5, f6, f7, f8, f9):
        fn()
    cap = {}
    for key, text in captions().items():
        stem, title = spec.FIGURES[key]
        cap[f"{key}_{stem}.png"] = {"figure": key, "title": title, "description": text}
    (OUT / "figure_captions.json").write_text(json.dumps(cap, indent=2), encoding="utf-8")
    print(f"Wrote {len(cap)} captions to figure_captions.json")


if __name__ == "__main__":
    main()
