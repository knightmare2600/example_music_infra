#!/usr/bin/env python3
"""
pve-bootorder.py — Proxmox VM boot order / startup manager
===========================================================
Textual TUI for configuring Proxmox VM startup order, delays, and onboot flags.

Intelligent defaults
--------------------
VMs are auto-grouped by site (FAL → ODE → BRK) and role tier:
  Tier 1 — Firewalls / gateways   (role: fwl)
  Tier 2 — Domain controllers     (role: dc, ad)
  Tier 3 — Infrastructure         (role: ansible, mgmt, svc)
  Tier 4 — Application / other    (everything else)

Boot order within a site follows tier order.  Between sites, all FAL
tier-1 VMs boot before ODE tier-1, which boots before BRK tier-1, etc.
(interleaved by tier so critical services are up across all sites before
less-critical services start anywhere).

Usage
-----
  python3 pve-bootorder.py [--host <pve-host>] [--dry-run]
  python3 pve-bootorder.py --load vms.json   # work offline from a JSON snapshot

The script detects role + site from VM names using the naming convention:
  EXA<role><site><seq>NNN  →  EXADCSFAL001, EXAFWLODE001, EXAANSCTL001, etc.

Override detection with the JSON config (vms.json) if naming doesn't match.

Requirements
------------
  pip install textual proxmoxer requests
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from typing import Optional

# ── Textual imports ───────────────────────────────────────────────────────────
try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.color import Color
    from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
    from textual.css.query import NoMatches
    from textual.reactive import reactive
    from textual.screen import ModalScreen
    from textual.widgets import (
        Button, Checkbox, DataTable, Footer, Header, Input, Label,
        ListItem, ListView, Rule, Select, Static, Switch, TabbedContent,
        TabPane,
    )
    from textual import on, work
except ImportError:
    print("textual not installed.  Run:  pip install textual")
    sys.exit(1)

# =============================================================================
# DATA MODEL
# =============================================================================

SITES        = ["FAL", "ODE", "BRK"]
SITE_ORDER   = {s: i for i, s in enumerate(SITES)}

# Tier definitions — name substrings that map to a tier number (lower = earlier)
ROLE_TIERS: list[tuple[int, list[str]]] = [
    (1, ["FWL", "FW",  "GW",  "RTR", "ROUTER", "GATE"]),
    (2, ["DC",  "AD",  "DNS", "LDAP"]),
    (3, ["ANS", "MGMT","MGT", "MON",  "NMS", "SVR", "WDS", "PKI", "CA"]),
    (4, []),   # catch-all
]

TIER_LABELS = {1: "Firewalls", 2: "Domain Controllers", 3: "Infrastructure", 4: "Application/Other"}

# Inter-site gap (order units between one site's last VM and next site's first)
SITE_GAP  = 5
# Inter-tier gap within a site
TIER_GAP  = 3
# Default startup delay (seconds) between VMs in the same tier
DEFAULT_UP_DELAY   = 10   # seconds — wait after VM reports up before starting next
DEFAULT_DOWN_DELAY = 30   # seconds — wait during shutdown


def detect_site(name: str) -> str:
    """Extract site code from VM name.  Returns '' if not detected."""
    upper = name.upper()
    for site in SITES:
        # Match EXAxxxxxxxSITEnnn  or  anything containing the site code
        if site in upper:
            # Make sure it's not just a coincidental substring — check position
            idx = upper.find(site)
            # Typical pattern: 3-char prefix + role(3) + site(3) + seq(3) + num
            # e.g. EXADCSFAL001 → site at position 8
            # Be generous — accept if surrounded by non-alpha or at word boundary
            before = upper[idx-1] if idx > 0 else ""
            after  = upper[idx+3] if idx+3 < len(upper) else ""
            if (not before.isalpha() or idx >= 5) and (not after.isalpha() or after.isdigit()):
                return site
            # Fallback: just contains it
            return site
    return "UNK"


def detect_tier(name: str) -> int:
    """Detect boot tier from VM name substrings."""
    upper = name.upper()
    for tier, keywords in ROLE_TIERS:
        for kw in keywords:
            if kw in upper:
                return tier
    return 4


@dataclass
class VMEntry:
    vmid:       int
    name:       str
    site:       str         = ""
    tier:       int         = 4
    onboot:     bool        = True
    order:      int         = 100   # Proxmox startup order (lower = earlier)
    up_delay:   int         = DEFAULT_UP_DELAY    # seconds after 'up' before next
    down_delay: int         = DEFAULT_DOWN_DELAY  # seconds on shutdown
    status:     str         = "unknown"   # running / stopped / unknown
    node:       str         = ""
    notes:      str         = ""

    @classmethod
    def from_proxmox(cls, vm: dict, node: str) -> "VMEntry":
        name    = vm.get("name", f"vm-{vm['vmid']}")
        config  = vm.get("_config", {})
        startup = _parse_startup(config.get("startup", ""))
        return cls(
            vmid       = vm["vmid"],
            name       = name,
            site       = detect_site(name),
            tier       = detect_tier(name),
            onboot     = bool(config.get("onboot", 0)),
            order      = startup.get("order", 100),
            up_delay   = startup.get("up",    DEFAULT_UP_DELAY),
            down_delay = startup.get("down",  DEFAULT_DOWN_DELAY),
            status     = vm.get("status", "unknown"),
            node       = node,
        )

    @classmethod
    def from_dict(cls, d: dict) -> "VMEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def startup_str(self) -> str:
        """Format Proxmox startup string."""
        return f"order={self.order},up={self.up_delay},down={self.down_delay}"

    def qm_command(self) -> str:
        onboot_val = 1 if self.onboot else 0
        return (f"qm set {self.vmid} "
                f"--onboot {onboot_val} "
                f"--startup {self.startup_str()}")


def _parse_startup(s: str) -> dict:
    """Parse 'order=5,up=30,down=60' → {'order': 5, 'up': 30, 'down': 60}"""
    result = {}
    for part in s.split(","):
        if "=" in part:
            k, _, v = part.partition("=")
            try:
                result[k.strip()] = int(v.strip())
            except ValueError:
                pass
    return result


def auto_assign_orders(vms: list[VMEntry]) -> list[VMEntry]:
    """
    Assign Proxmox startup order values based on the interleaved-by-tier scheme:
      All site FAL tier-1, all site ODE tier-1, all site BRK tier-1,
      all site FAL tier-2, all site ODE tier-2, ...
    Within each (site, tier) group, preserve the existing relative order
    (as given by current .order values, or list position if equal).
    """
    vms = deepcopy(vms)

    # Group: tier → site → [vms]
    groups: dict[int, dict[str, list[VMEntry]]] = {}
    for vm in vms:
        groups.setdefault(vm.tier, {}).setdefault(vm.site, [])
        groups[vm.tier][vm.site].append(vm)

    # Sort within each group by existing order, then vmid as tiebreak
    for tier_dict in groups.values():
        for site_list in tier_dict.values():
            site_list.sort(key=lambda v: (v.order, v.vmid))

    counter = 1
    for tier in sorted(groups.keys()):
        for site in SITES + ["UNK"]:
            grp = groups.get(tier, {}).get(site, [])
            for vm in grp:
                vm.order = counter
                counter += 1
            if grp:
                counter += TIER_GAP   # gap after each (tier, site) block

    # Copy back
    by_id = {v.vmid: v for v in vms}
    return [by_id[v.vmid] for v in vms]


# =============================================================================
# PROXMOX CONNECTIVITY
# =============================================================================

def load_from_proxmox(host: str, user: str, password: str,
                      verify_ssl: bool = False) -> tuple[list[VMEntry], list[str], object]:
    """Load VMs from Proxmox API.
    Returns (vms, discovered_sites, px) — px is the live authenticated
    ProxmoxAPI instance, reused for apply so no re-auth is needed.
    """
    try:
        from proxmoxer import ProxmoxAPI
    except ImportError:
        print("proxmoxer not installed.  Run:  pip install proxmoxer requests")
        sys.exit(1)

    px = ProxmoxAPI(host, user=user, password=password, verify_ssl=verify_ssl)

    # ── Enumerate pools ───────────────────────────────────────────────────────
    # Build vmid → pool map.  A pool whose name is 3 alpha chars is a site pool.
    vmid_to_pool: dict[int, str] = {}
    site_pools:   set[str]       = set()
    try:
        for pool in px.pools.get():
            pool_id = pool.get("poolid", "")
            # Fetch pool members
            try:
                members = px.pools(pool_id).get()
                for m in members.get("members", []):
                    if m.get("type") == "qemu":
                        vmid_to_pool[int(m["vmid"])] = pool_id
            except Exception:
                pass
            # Treat 3-letter all-alpha pool names as site codes
            if len(pool_id) == 3 and pool_id.isalpha():
                site_pools.add(pool_id.upper())
    except Exception as e:
        print(f"[warn] Could not enumerate pools: {e}")

    # ── Load VMs ──────────────────────────────────────────────────────────────
    vms = []
    for node in px.nodes.get():
        node_name = node["node"]
        for vm in px.nodes(node_name).qemu.get():
            try:
                config = px.nodes(node_name).qemu(vm["vmid"]).config.get()
            except Exception:
                config = {}
            vm["_config"] = config
            entry = VMEntry.from_proxmox(vm, node_name)

            # Override site from pool if the pool is a known site pool
            pool = vmid_to_pool.get(entry.vmid, "")
            if pool.upper() in site_pools:
                entry.site = pool.upper()

            vms.append(entry)

    # Collect all sites actually seen in VMs (pool-derived + name-detected)
    all_sites = sorted(site_pools | {v.site for v in vms if v.site != "UNK"})
    return vms, all_sites, px


def apply_to_proxmox(vms: list[VMEntry], px,
                     dry_run: bool = False) -> list[tuple[VMEntry, bool, str]]:
    """Apply boot settings using an already-authenticated ProxmoxAPI instance.
    Returns list of (vm, success, message).
    """
    results = []
    for vm in vms:
        cmd = vm.qm_command()
        if dry_run:
            results.append((vm, True, f"[DRY RUN] {cmd}"))
            continue
        try:
            px.nodes(vm.node).qemu(vm.vmid).config.put(
                onboot  = 1 if vm.onboot else 0,
                startup = vm.startup_str(),
            )
            results.append((vm, True, f"OK — {cmd}"))
        except Exception as e:
            results.append((vm, False, f"FAILED: {e}"))
    return results


def apply_via_qm(vms: list[VMEntry], dry_run: bool = False) -> list[tuple[VMEntry, bool, str]]:
    """Apply via local qm binary (must run on PVE node or with sudo)."""
    results = []
    _s = ["sudo"] if os.geteuid() != 0 else []
    qm = _s + (["qm"] if subprocess.run(
        ["which", "qm"], capture_output=True).returncode == 0
        else ["/usr/sbin/qm"])

    for vm in vms:
        cmd = qm + ["set", str(vm.vmid),
                    "--onboot", "1" if vm.onboot else "0",
                    "--startup", vm.startup_str()]
        if dry_run:
            results.append((vm, True, f"[DRY RUN] {' '.join(cmd)}"))
            continue
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                results.append((vm, True, f"OK"))
            else:
                results.append((vm, False, r.stderr.strip()[:120]))
        except Exception as e:
            results.append((vm, False, str(e)))
    return results


# =============================================================================
# CSS — Solarized Dark
# =============================================================================
# Palette reference:
#   base03  #002b36  darkest bg
#   base02  #073642  dark bg highlight
#   base01  #586e75  comments / secondary content
#   base00  #657b83  body text (on light bg — avoid on dark)
#   base0   #839496  body text (on dark bg)
#   base1   #93a1a1  emphasis text
#   base2   #eee8d5  light bg (unused in dark mode)
#   base3   #fdf6e3  lightest bg (unused in dark mode)
#   yellow  #b58900
#   orange  #cb4b16
#   red     #dc322f
#   magenta #d33682
#   violet  #6c71c4
#   blue    #268bd2
#   cyan    #2aa198
#   green   #859900

CSS = """
Screen {
    background: #002b36;
    color: #839496;
}

Header {
    background: #073642;
    color: #eee8d5;
    height: 3;
    border-bottom: solid #268bd2;
}

Footer {
    background: #073642;
    color: #93a1a1;
}

#app-grid {
    layout: grid;
    grid-size: 2;
    grid-columns: 1fr 2fr;
    height: 100%;
}

/* ── Left panel ── */
#left-panel {
    border: solid #268bd2;
    height: 100%;
    padding: 0 0;
    background: #002b36;
}

#left-title {
    background: #073642;
    color: #93a1a1;
    padding: 0 1;
    height: 1;
    text-style: bold;
}

VMRow {
    height: 1;
    padding: 0 1;
    layout: horizontal;
    color: #839496;
    background: #002b36;
}

VMRow:hover {
    background: #073642;
    color: #eee8d5;
}

VMRow.selected {
    background: #073642;
    color: #eee8d5;
    border-left: solid #268bd2;
}

/* onboot-off: dimmed but still readable — NOT invisible */
VMRow.onboot-off {
    color: #586e75;
}

VMRow.onboot-off .vm-name {
    color: #586e75;
}

VMRow .vm-order {
    width: 5;
    color: #b58900;
    text-style: bold;
}

VMRow .vm-site {
    width: 5;
    color: #2aa198;
}

VMRow .vm-vmid {
    width: 7;
    color: #839496;
}

VMRow .vm-name {
    width: 1fr;
    color: #93a1a1;
}

VMRow.selected .vm-name {
    color: #eee8d5;
}

VMRow .vm-status {
    width: 3;
    color: #586e75;
}

.tier-header {
    background: #073642;
    color: #93a1a1;
    padding: 0 1;
    height: 1;
    text-style: bold italic;
    border-left: solid #586e75;
}

/* ── Right panel ── */
#right-panel {
    border: solid #268bd2;
    height: 100%;
    padding: 0 1;
    background: #002b36;
}

#right-title {
    background: #073642;
    color: #eee8d5;
    padding: 0 1;
    height: 1;
    text-style: bold;
    margin-bottom: 1;
}

#no-selection {
    color: #839496;
    padding: 1 0;
}

.field-row {
    height: 3;
    align: left middle;
    margin-bottom: 0;
}

.field-label {
    width: 22;
    color: #93a1a1;
    padding: 1 0;
}

.field-input {
    width: 12;
    background: #073642;
    color: #eee8d5;
    border: tall #268bd2;
}

Input {
    background: #073642;
    color: #eee8d5;
    border: tall #586e75;
}

Input:focus {
    border: tall #268bd2;
    color: #eee8d5;
}

Switch {
    background: #073642;
}

Switch:focus {
    border: tall #268bd2;
}

Switch.-on {
    background: #073642;
}

Switch.-on > .switch--slider {
    color: #859900;
}

Select {
    background: #073642;
    color: #eee8d5;
    border: tall #586e75;
}

Select:focus {
    border: tall #268bd2;
}

SelectCurrent {
    background: #073642;
    color: #eee8d5;
}

.section-head {
    color: #b58900;
    text-style: bold;
    margin-top: 1;
    height: 1;
}

#preview-box {
    border: solid #073642;
    background: #073642;
    color: #2aa198;
    padding: 0 1;
    margin-top: 1;
    height: auto;
    min-height: 2;
}

/* ── Buttons — plain ASCII labels, no icon glyphs ── */
#button-row {
    dock: bottom;
    height: 3;
    align: center middle;
    padding: 0 1;
    background: #002b36;
}

Button {
    margin: 0 1;
    background: #073642;
    color: #93a1a1;
    border: tall #586e75;
}

Button:hover {
    background: #586e75;
    color: #002b36;
}

Button.-success, Button.success {
    background: #859900;
    color: #002b36;
    border: tall #859900;
}

Button.-success:hover, Button.success:hover {
    background: #93a1a1;
    color: #002b36;
}

Button.-warning, Button.warning {
    background: #b58900;
    color: #002b36;
    border: tall #b58900;
}

Button.-warning:hover, Button.warning:hover {
    background: #cb4b16;
    color: #fdf6e3;
}

Button.-error, Button.danger {
    background: #dc322f;
    color: #fdf6e3;
    border: tall #dc322f;
}

/* ── Move up/down buttons ── */
#move-buttons {
    height: 3;
    align: center middle;
    background: #002b36;
}

#move-buttons Button {
    min-width: 10;
    height: 1;
}

/* ── Results modal ── */
ResultsScreen {
    align: center middle;
    background: #002b3680;
}

#results-dialog {
    width: 82%;
    max-height: 80%;
    border: solid #268bd2;
    background: #002b36;
    padding: 1 2;
}

#results-title {
    text-style: bold;
    color: #b58900;
    margin-bottom: 1;
}

#results-scroll {
    height: 1fr;
    border: solid #073642;
    background: #073642;
    padding: 0 1;
    color: #839496;
}

.result-ok {
    color: #859900;
}

.result-fail {
    color: #dc322f;
}

/* ── Auto-order dialog ── */
AutoOrderScreen {
    align: center middle;
    background: #002b3680;
}

#autoorder-dialog {
    width: 62;
    border: solid #b58900;
    background: #002b36;
    padding: 1 2;
}

Rule {
    color: #073642;
    margin: 1 0;
}

Label {
    color: #839496;
}

/* ── Scrollbars ── */
ScrollBar {
    background: #073642;
    color: #268bd2;
}

ScrollBar > .scrollbar--bar {
    color: #586e75;
    background: #073642;
}

ScrollBar > .scrollbar--bar:hover {
    color: #268bd2;
}
"""


# =============================================================================
# WIDGETS
# =============================================================================

class VMRow(Static, can_focus=True):
    """Single VM row in the left list panel."""

    from textual.message import Message as _Message

    class Selected(_Message):
        """Posted when this row is clicked."""
        def __init__(self, vmid: int) -> None:
            super().__init__()
            self.vmid = vmid

    def __init__(self, vm: VMEntry, **kwargs):
        super().__init__(**kwargs)
        self.vm = vm
        self._selected = False

    def compose(self) -> ComposeResult:
        vm = self.vm
        status_color = {
            "running": "[green]▶[/green]",
            "stopped": "[red]■[/red]",
        }.get(vm.status, "[dim]?[/dim]")
        onboot_icon = "⏻" if vm.onboot else "○"

        yield Static(f"{vm.order:>3} ", classes="vm-order")
        yield Static(f"{vm.site:<4} ",  classes="vm-site")
        yield Static(f"{vm.vmid:<6} ",  classes="vm-vmid")
        yield Static(f"{onboot_icon} {vm.name}", classes="vm-name")
        yield Static(f" {status_color}",         classes="vm-status")

    def on_click(self, _) -> None:
        self.post_message(self.Selected(self.vm.vmid))

    def set_selected(self, val: bool) -> None:
        self._selected = val
        self.set_class(val, "selected")
        self.set_class(not self.vm.onboot, "onboot-off")


# =============================================================================
# MODAL SCREENS
# =============================================================================

class AutoOrderScreen(ModalScreen):
    """Confirm + configure auto-order assignment."""

    BINDINGS = [("escape", "dismiss(False)", "Cancel")]

    def compose(self) -> ComposeResult:
        with Container(id="autoorder-dialog"):
            yield Label("Auto-assign boot order", id="results-title")
            yield Rule()
            yield Static(
                "This will re-number all VM startup orders using the\n"
                "interleaved site+tier scheme:\n\n"
                "  FAL tier-1 → ODE tier-1 → BRK tier-1\n"
                "  FAL tier-2 → ODE tier-2 → BRK tier-2  …\n\n"
                "Within each group, current relative order is preserved.\n"
                "You can still drag VMs up/down after this."
            )
            yield Rule()
            with Horizontal(id="button-row"):
                yield Button("Apply", id="btn-autoorder-ok", variant="warning")
                yield Button("Cancel", id="btn-autoorder-cancel")

    @on(Button.Pressed, "#btn-autoorder-ok")
    def do_apply(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#btn-autoorder-cancel")
    def do_cancel(self) -> None:
        self.dismiss(False)


class ResultsScreen(ModalScreen):
    """Show apply results."""

    BINDINGS = [("escape", "dismiss", "Close"), ("q", "dismiss", "Close")]

    def __init__(self, results: list[tuple[VMEntry, bool, str]], **kwargs):
        super().__init__(**kwargs)
        self._results = results

    def compose(self) -> ComposeResult:
        ok_count   = sum(1 for _, s, _ in self._results if s)
        fail_count = len(self._results) - ok_count
        with Container(id="results-dialog"):
            yield Label(f"Apply results — {ok_count} OK / {fail_count} failed",
                        id="results-title")
            with ScrollableContainer(id="results-scroll"):
                for vm, success, msg in self._results:
                    cls   = "result-ok" if success else "result-fail"
                    icon  = "✓" if success else "✗"
                    from rich.text import Text
                    yield Static(
                        Text(f"{icon} [{vm.vmid}] {vm.name}: {msg}"),
                        classes=cls
                    )
            yield Button("Close", id="btn-close-results")

    @on(Button.Pressed, "#btn-close-results")
    def close(self) -> None:
        self.dismiss()


# =============================================================================
# MAIN APP
# =============================================================================

class BootOrderApp(App):
    """Proxmox VM boot order manager."""

    TITLE   = "pve-bootorder — Proxmox startup order manager"
    CSS     = CSS

    BINDINGS = [
        Binding("q",         "quit",         "Quit"),
        Binding("s",         "save_json",    "Save JSON"),
        Binding("a",         "auto_order",   "Auto-order"),
        Binding("up",        "move_up",      "Move up",   show=False),
        Binding("down",      "move_down",    "Move down", show=False),
        Binding("space",     "toggle_onboot","Toggle onboot", show=False),
        Binding("ctrl+a",    "apply",        "Apply"),
        Binding("?",         "help",         "Help"),
    ]

    selected_idx: reactive[int] = reactive(0)

    def __init__(self, vms: list[VMEntry], apply_fn, dry_run: bool = False,
                 known_sites: list[str] | None = None, **kwargs):
        super().__init__(**kwargs)
        self._vms        = list(vms)
        self._apply      = apply_fn
        self._dry_run    = dry_run
        self._dirty      = False
        # Site list for the selector — use live-discovered list if provided,
        # fall back to the global SITES.  Always append UNK as the last option.
        self._known_sites = list(known_sites or SITES)
        if "UNK" not in self._known_sites:
            self._known_sites.append("UNK")

    # ── Compose ──────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="app-grid"):
            # Left — VM list
            with Vertical(id="left-panel"):
                yield Static("  ORD  SITE  VMID    NAME                    ST",
                             id="left-title")
                yield ScrollableContainer(id="vm-list")
                with Horizontal(id="move-buttons"):
                    yield Button("Up",   id="btn-up",   variant="default")
                    yield Button("Down", id="btn-down", variant="default")

            # Right — edit panel
            with Vertical(id="right-panel"):
                yield Static("VM Settings", id="right-title", markup=False)
                yield Static("Select a VM to edit", id="no-selection")
                with Vertical(id="edit-form"):
                    yield Static("Boot settings", classes="section-head")

                    with Horizontal(classes="field-row"):
                        yield Label("Boot on host start",  classes="field-label")
                        yield Switch(id="sw-onboot", value=True)

                    with Horizontal(classes="field-row"):
                        yield Label("Startup order",       classes="field-label")
                        yield Input("100", id="inp-order",
                                    type="integer", classes="field-input")

                    with Horizontal(classes="field-row"):
                        yield Label("Startup delay (s)",   classes="field-label")
                        yield Input(str(DEFAULT_UP_DELAY), id="inp-up",
                                    type="integer", classes="field-input")

                    with Horizontal(classes="field-row"):
                        yield Label("Shutdown delay (s)",  classes="field-label")
                        yield Input(str(DEFAULT_DOWN_DELAY), id="inp-down",
                                    type="integer", classes="field-input")

                    with Horizontal(classes="field-row"):
                        yield Label("Site",                classes="field-label")
                        yield Select(
                            [(s, s) for s in self._known_sites],
                            id="sel-site",
                            value=self._known_sites[0] if self._known_sites else "UNK"
                        )

                    with Horizontal(classes="field-row"):
                        yield Label("Tier",                classes="field-label")
                        yield Select(
                            [(f"{t} — {TIER_LABELS[t]}", str(t)) for t in sorted(TIER_LABELS)],
                            id="sel-tier", value="4"
                        )

                    yield Static("", classes="section-head")  # spacer
                    yield Static("Proxmox startup string:", classes="section-head")
                    yield Static("", id="preview-box", markup=False)

                    with Horizontal(id="button-row"):
                        yield Button("Apply all",  id="btn-apply",
                                     variant="success")
                        yield Button("Auto-order", id="btn-auto",
                                     variant="warning")
                        yield Button("Save JSON",  id="btn-save")
                        yield Button("Quit",       id="btn-quit",
                                     variant="error")
        yield Footer()

    # ── On mount ─────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self._rebuild_list()
        self.query_one("#edit-form").display = False
        self.query_one("#no-selection").display = True

    def _rebuild_list(self) -> None:
        # Increment generation counter so new widget IDs never collide with
        # stale widgets that are queued for removal but not yet deregistered.
        self._gen = getattr(self, "_gen", 0) + 1
        gen = self._gen

        lst = self.query_one("#vm-list", ScrollableContainer)
        lst.remove_children()

        current_tier = None

        sorted_vms = sorted(
            self._vms,
            key=lambda v: (v.tier, SITE_ORDER.get(v.site, 99), v.order, v.vmid)
        )
        self._sorted_vms = sorted_vms

        new_widgets = []
        for vm in sorted_vms:
            if vm.tier != current_tier:
                current_tier = vm.tier
                new_widgets.append(Static(
                    f"  ── Tier {vm.tier}: {TIER_LABELS.get(vm.tier, '')} ──",
                    classes="tier-header"
                ))
            new_widgets.append(VMRow(vm, id=f"vmrow-{gen}-{vm.vmid}"))

        # Mount all at once — single pass, no intermediate state
        if new_widgets:
            lst.mount(*new_widgets)

        self._highlight_selected()

    def _highlight_selected(self) -> None:
        gen = getattr(self, "_gen", 1)
        for i, vm in enumerate(self._sorted_vms):
            try:
                row = self.query_one(f"#vmrow-{gen}-{vm.vmid}", VMRow)
                row.set_selected(i == self.selected_idx)
            except NoMatches:
                pass

    def _selected_vm(self) -> Optional[VMEntry]:
        if not self._sorted_vms:
            return None
        idx = max(0, min(self.selected_idx, len(self._sorted_vms) - 1))
        return self._sorted_vms[idx]

    def _load_vm_to_form(self, vm: VMEntry) -> None:
        self.query_one("#edit-form").display    = True
        self.query_one("#no-selection").display = False
        # #right-title is declared with markup=False so plain strings are safe
        self.query_one("#right-title", Static).update(
            f"VM {vm.vmid}  {vm.name}")
        self.query_one("#sw-onboot",  Switch).value = vm.onboot
        self.query_one("#inp-order",  Input).value  = str(vm.order)
        self.query_one("#inp-up",     Input).value  = str(vm.up_delay)
        self.query_one("#inp-down",   Input).value  = str(vm.down_delay)
        self.query_one("#sel-site",   Select).value = vm.site or "UNK"
        self.query_one("#sel-tier",   Select).value = str(vm.tier)
        self._update_preview(vm)

    def _update_preview(self, vm: VMEntry) -> None:
        # preview-box also declared markup=False — plain text safe
        self.query_one("#preview-box", Static).update(vm.qm_command())

    def _save_form_to_vm(self) -> None:
        vm = self._selected_vm()
        if not vm:
            return
        try:
            vm.onboot    = self.query_one("#sw-onboot",  Switch).value
            vm.order     = int(self.query_one("#inp-order",  Input).value or "100")
            vm.up_delay  = int(self.query_one("#inp-up",     Input).value or "10")
            vm.down_delay= int(self.query_one("#inp-down",   Input).value or "30")
            vm.site      = str(self.query_one("#sel-site",   Select).value)
            vm.tier      = int(self.query_one("#sel-tier",   Select).value)
        except (ValueError, NoMatches):
            pass
        self._dirty = True
        self._update_preview(vm)

    # ── Events ───────────────────────────────────────────────────────────────

    @on(VMRow.Selected)
    def on_vmrow_selected(self, event: VMRow.Selected) -> None:
        self._save_form_to_vm()
        for i, vm in enumerate(self._sorted_vms):
            if vm.vmid == event.vmid:
                self.selected_idx = i
                self._highlight_selected()
                self._load_vm_to_form(vm)
                return

    @on(Switch.Changed, "#sw-onboot")
    def on_onboot_changed(self, event: Switch.Changed) -> None:
        self._save_form_to_vm()
        self._rebuild_list()

    @on(Input.Changed)
    def on_input_changed(self, _) -> None:
        self._save_form_to_vm()

    @on(Select.Changed)
    def on_select_changed(self, _) -> None:
        self._save_form_to_vm()
        self._rebuild_list()
        self._highlight_selected()

    # ── Button handlers ───────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-up")
    def action_move_up(self) -> None:
        self._move_selected(-1)

    @on(Button.Pressed, "#btn-down")
    def action_move_down(self) -> None:
        self._move_selected(1)

    @on(Button.Pressed, "#btn-apply")
    def on_btn_apply(self) -> None:
        self.action_apply()

    @on(Button.Pressed, "#btn-auto")
    def on_btn_auto(self) -> None:
        self.action_auto_order()

    @on(Button.Pressed, "#btn-save")
    def on_btn_save(self) -> None:
        self.action_save_json()

    @on(Button.Pressed, "#btn-quit")
    def on_btn_quit(self) -> None:
        self.action_quit()

    # ── Key actions ──────────────────────────────────────────────────────────

    def action_move_up(self) -> None:
        self._move_selected(-1)

    def action_move_down(self) -> None:
        self._move_selected(1)

    def action_toggle_onboot(self) -> None:
        vm = self._selected_vm()
        if vm:
            vm.onboot = not vm.onboot
            self._dirty = True
            self._load_vm_to_form(vm)
            self._rebuild_list()

    def action_auto_order(self) -> None:
        def handle(confirmed: bool) -> None:
            if confirmed:
                self._vms = auto_assign_orders(self._vms)
                self._dirty = True
                self._rebuild_list()
                vm = self._selected_vm()
                if vm:
                    self._load_vm_to_form(vm)
                self.notify("Auto-order applied.", title="Done")
        self.push_screen(AutoOrderScreen(), handle)

    def action_apply(self) -> None:
        self._save_form_to_vm()
        tag = " (DRY RUN)" if self._dry_run else ""
        self.notify(f"Applying{tag}…", title="Applying")

        results = self._apply(self._vms, dry_run=self._dry_run)
        self._dirty = False
        self.push_screen(ResultsScreen(results))

    def action_save_json(self) -> None:
        self._save_form_to_vm()
        path = "vms.json"
        data = [asdict(v) for v in self._vms]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self.notify(f"Saved to {path}", title="Saved")
        self._dirty = False

    def action_quit(self) -> None:
        if self._dirty:
            self.notify("Unsaved changes — save first (s) or press q again",
                        title="Unsaved changes", severity="warning")
            self._dirty = False   # allow second q to quit
        else:
            self.exit()

    def action_help(self) -> None:
        self.notify(
            "↑/↓ = navigate   Space = toggle onboot\n"
            "a   = auto-order  Ctrl+A = apply\n"
            "s   = save JSON   q = quit",
            title="Keyboard shortcuts", timeout=8
        )

    # ── Move helpers ─────────────────────────────────────────────────────────

    def _move_selected(self, direction: int) -> None:
        """Move selected VM up (-1) or down (+1) within its tier+site group,
        swapping order values with its neighbour."""
        vm = self._selected_vm()
        if not vm:
            return

        # Find peers in the same tier+site
        peers = [v for v in self._sorted_vms
                 if v.tier == vm.tier and v.site == vm.site]
        if len(peers) < 2:
            return

        idx_in_peers = next((i for i, v in enumerate(peers) if v.vmid == vm.vmid), None)
        if idx_in_peers is None:
            return

        new_idx = idx_in_peers + direction
        if new_idx < 0 or new_idx >= len(peers):
            return

        neighbour = peers[new_idx]
        # Swap order values
        vm.order, neighbour.order = neighbour.order, vm.order
        self._dirty = True

        # Update selected_idx to follow the moved VM
        new_global_idx = next(
            (i for i, v in enumerate(self._sorted_vms) if v.vmid == neighbour.vmid), None
        )
        if new_global_idx is not None:
            self.selected_idx = new_global_idx

        self._rebuild_list()
        vm_new = self._selected_vm()
        if vm_new:
            self._load_vm_to_form(vm_new)


# =============================================================================
# DEMO / OFFLINE DATA
# =============================================================================

DEMO_VMS = [
    # FAL site
    VMEntry(vmid=100, name="EXAFWLFAL001", site="FAL", tier=1, onboot=True,  order=10,  up_delay=30, down_delay=60, status="running", node="EXAPVECLD001"),
    VMEntry(vmid=101, name="EXADCSFAL001", site="FAL", tier=2, onboot=True,  order=20,  up_delay=30, down_delay=60, status="running", node="EXAPVECLD001"),
    VMEntry(vmid=102, name="EXADCSFAL002", site="FAL", tier=2, onboot=True,  order=21,  up_delay=10, down_delay=60, status="running", node="EXAPVECLD001"),
    VMEntry(vmid=103, name="EXAANSCTL001", site="FAL", tier=3, onboot=True,  order=50,  up_delay=10, down_delay=30, status="running", node="EXAPVECLD001"),
    VMEntry(vmid=104, name="EXASVRFAL001", site="FAL", tier=3, onboot=True,  order=55,  up_delay=10, down_delay=30, status="stopped", node="EXAPVECLD001"),

    # ODE site
    VMEntry(vmid=200, name="EXAFWLODE001", site="ODE", tier=1, onboot=True,  order=11,  up_delay=30, down_delay=60, status="running", node="EXAPVECLD001"),
    VMEntry(vmid=201, name="EXADCSODE001", site="ODE", tier=2, onboot=True,  order=22,  up_delay=30, down_delay=60, status="stopped", node="EXAPVECLD001"),

    # BRK site
    VMEntry(vmid=300, name="EXAFWLBRK001", site="BRK", tier=1, onboot=True,  order=12,  up_delay=30, down_delay=60, status="stopped", node="EXAPVECLD001"),
    VMEntry(vmid=301, name="EXADCSBRK001", site="BRK", tier=2, onboot=False, order=23,  up_delay=30, down_delay=60, status="stopped", node="EXAPVECLD001"),

    # LND site (auto-detected as UNK if not in SITES list, can be extended)
    VMEntry(vmid=400, name="EXADCSLND001", site="UNK", tier=2, onboot=True,  order=25,  up_delay=30, down_delay=60, status="stopped", node="EXAPVECLD001"),
]


# =============================================================================
# ENTRY POINT
# =============================================================================

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Proxmox VM boot order TUI manager"
    )
    ap.add_argument("--host",     default=os.environ.get("PVE_HOST", ""),
                    help="Proxmox API host (or set PVE_HOST env var)")
    ap.add_argument("--user",     default=os.environ.get("PVE_USER", "root@pam"),
                    help="Proxmox API user (default: root@pam)")
    ap.add_argument("--password", default=os.environ.get("PVE_PASS", ""),
                    help="Proxmox API password (or set PVE_PASS env var)")
    ap.add_argument("--load",     metavar="FILE",
                    help="Load VM list from JSON file instead of live API")
    ap.add_argument("--demo",     action="store_true",
                    help="Use built-in demo data (no Proxmox needed)")
    ap.add_argument("--dry-run",  action="store_true",
                    help="Preview qm commands without running them")
    ap.add_argument("--local-qm", action="store_true",
                    help="Apply via local qm binary instead of API")
    ap.add_argument("--no-ssl-verify", action="store_true",
                    help="Disable SSL certificate verification")
    ap.add_argument("--add-site", metavar="SITE", action="append", default=[],
                    help="Add extra site code (e.g. --add-site LND --add-site SCH)")
    args = ap.parse_args()

    # Extend SITES list with any extras from --add-site flags
    for extra in args.add_site:
        code = extra.upper()
        if code not in SITES:
            SITES.append(code)
            SITE_ORDER[code] = len(SITE_ORDER)

    # ── Load VM list ──────────────────────────────────────────────────────────
    discovered_sites: list[str] = []
    _px = None   # authenticated ProxmoxAPI instance — reused for apply
    if args.demo:
        vms = DEMO_VMS
        print("[demo] Using built-in demo VM list.")
    elif args.load:
        with open(args.load) as f:
            raw = json.load(f)
        vms = [VMEntry.from_dict(d) for d in raw]
        # Re-derive sites from the loaded data
        discovered_sites = sorted({v.site for v in vms if v.site not in ("UNK", "")})
        print(f"[load] Loaded {len(vms)} VMs from {args.load}")
    elif args.host:
        print(f"[api]  Connecting to {args.host}…")
        password = args.password
        if not password:
            import getpass
            password = getpass.getpass(f"Password for {args.user}@{args.host}: ")
        vms, discovered_sites, _px = load_from_proxmox(
            host       = args.host,
            user       = args.user,
            password   = password,
            verify_ssl = not args.no_ssl_verify,
        )
        print(f"[api]  Loaded {len(vms)} VMs.")
        if discovered_sites:
            print(f"[api]  Sites from pools: {', '.join(discovered_sites)}")
    else:
        # Fallback: try local qm list
        r = subprocess.run(
            ["qm", "list"],
            capture_output=True, text=True
        ) if subprocess.run(["which", "qm"], capture_output=True).returncode == 0 \
        else type("R", (), {"returncode": 1})()

        if hasattr(r, "returncode") and r.returncode == 0:
            # Parse qm list output: VMID NAME STATUS ...
            vms = []
            for line in r.stdout.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        vmid = int(parts[0])
                        name = parts[1]
                        status = parts[2] if len(parts) > 2 else "unknown"
                        vms.append(VMEntry(
                            vmid=vmid, name=name,
                            site=detect_site(name), tier=detect_tier(name),
                            status=status, node="local"
                        ))
                    except ValueError:
                        pass
            print(f"[qm]   Found {len(vms)} VMs via local qm list.")
        else:
            print("[warn] No --host, --load, or --demo specified and qm not found.")
            print("       Starting with demo data.  Use --demo, --load, or --host.")
            vms = DEMO_VMS

    # ── Merge discovered sites into global SITES list ────────────────────────
    # Do this AFTER loading so the TUI site selector reflects reality.
    # Priority: FAL, ODE, BRK (the "primary" sites) come first, then
    # everything else alphabetically.
    primary = ["FAL", "ODE", "BRK"]
    extra_sites = sorted(s for s in discovered_sites if s not in primary)
    final_sites = [s for s in primary if s in set(discovered_sites) | set(SITES)] + extra_sites
    # Also include any --add-site entries not already there
    for s in SITES:
        if s not in final_sites:
            final_sites.append(s)
    SITES.clear()
    SITES.extend(final_sites)
    SITE_ORDER.clear()
    SITE_ORDER.update({s: i for i, s in enumerate(SITES)})

    # ── Apply function ────────────────────────────────────────────────────────
    if args.local_qm or not args.host:
        def apply_fn(vms, dry_run=False):
            return apply_via_qm(vms, dry_run=dry_run)
    else:
        # _px was authenticated at load time — reuse the same session.
        # proxmoxer uses a ticket (PVEAuthCookie) that expires after 2 hours;
        # if the session has aged out proxmoxer will raise an auth exception
        # and we re-authenticate transparently here.
        _apply_host       = args.host
        _apply_user       = args.user
        _apply_password   = password          # captured from getpass above
        _apply_verify_ssl = not args.no_ssl_verify

        def apply_fn(vms, dry_run=False):
            nonlocal _px
            if dry_run:
                return apply_to_proxmox(vms, _px, dry_run=True)
            try:
                return apply_to_proxmox(vms, _px, dry_run=False)
            except Exception as e:
                if "401" in str(e) or "auth" in str(e).lower() or _px is None:
                    # Ticket expired — re-authenticate and retry once
                    try:
                        from proxmoxer import ProxmoxAPI
                        _px = ProxmoxAPI(
                            _apply_host, user=_apply_user,
                            password=_apply_password,
                            verify_ssl=_apply_verify_ssl,
                        )
                        return apply_to_proxmox(vms, _px, dry_run=False)
                    except Exception as e2:
                        return [(vm, False, f"Re-auth failed: {e2}") for vm in vms]
                return [(vm, False, f"FAILED: {e}") for vm in vms]

    # ── Launch TUI ───────────────────────────────────────────────────────────
    app = BootOrderApp(vms=vms, apply_fn=apply_fn, dry_run=args.dry_run,
                       known_sites=list(SITES))
    app.run()


if __name__ == "__main__":
    main()
