#!/usr/bin/env python3
"""
=============================================================================
Proxmox VM Creation — TUI (v2)
=============================================================================
Full-screen Textual TUI front end for creating Proxmox VMs following the
EXA<ROLE><SITE><NNN> convention. This is a NEW, INDEPENDENT file — it does
not import from, and does not modify, create-vm.py (v1). v1 stays exactly
as it is; this is a different front end onto the same real Proxmox API and
the same estate config files (sites.csv, role_codes.csv), not a
replacement.

Why a second file rather than adding a --tui flag to v1: v1's whole design
is a sequential prompt() loop -- retrofitting a full-screen TUI onto that
would mean rewriting nearly every function anyway, and Robert's explicit
instruction was "leave the original as is, do not change or touch it, make
a new file." The data-loading (_load_sites/_load_role_codes) and pure
config-building (build_vm_config) logic is duplicated here rather than
imported, so neither file can ever break the other by being edited
independently.

Requires:
    proxmoxer, requests   -- same as v1, real Proxmox API client
    textual                -- TUI framework (apt: python3-textual)

Usage:
    python3 create-vm-tui.py
    python3 create-vm-tui.py --dry-run
    python3 create-vm-tui.py --sites-csv /path/to/sites.csv --role-codes-csv /path/to/role_codes.csv
    python3 create-vm-tui.py --log ~/pve-vm-create.log

Design notes (see PLAN in git history / conversation for the full brief):
  - Real-time VM ID / name duplicate checking as you type, not just on
    submit -- checked against both the live server state AND every VM
    already created (or queued) earlier in the same bulk-mode session.
  - "Same size for all disks" checkbox, default ON -- unchecking reveals
    one independent size slider per disk.
  - Two-level BIOS picker: SeaBIOS/UEFI radio buttons, then a follow-on
    list of the specific SLIC ROM variant (x86_64 only -- arm64 keeps v1's
    simpler seabios/ovmf-only choice, no ROM file involved).
  - Bulk mode: build VM #1's full config, then VM #2..N reuse it as a
    starting template (hardware/storage/OS/BIOS/console/network/pool) --
    only Name and VMID are freshly suggested and remain independently
    editable/validated per VM.
=============================================================================
"""

import argparse
import csv
import datetime
import json
import os
import re
import sys
from pathlib import Path

try:
    from proxmoxer import ProxmoxAPI
except ImportError:
    print("ERROR: proxmoxer not installed.")
    print("  On Proxmox node : apt install python3-proxmoxer python3-requests")
    print("  On workstation  : pip3 install proxmoxer requests")
    sys.exit(1)

try:
    from textual import work
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, Vertical, VerticalScroll
    from textual.message import Message
    from textual.reactive import reactive
    from textual.screen import ModalScreen, Screen
    from textual.validation import ValidationResult, Validator
    from textual.widget import Widget
    from textual.widgets import (
        Button,
        Checkbox,
        Footer,
        Header,
        Input,
        Label,
        RadioButton,
        RadioSet,
        RichLog,
        Select,
        SelectionList,
        Static,
    )
    from textual.widgets.selection_list import Selection
except ImportError:
    print("ERROR: textual not installed.")
    print("  apt install python3-textual   (already staged on this estate's control hosts)")
    print("  or: pip3 install textual")
    sys.exit(1)


# =============================================================================
# DATA LOADERS — duplicated from create-vm.py (v1), not imported. See
# module docstring for why.
# =============================================================================

def _load_sites(csv_path=None):
    """
    Load site data from sites.csv.
    Searches: script directory, cwd, /etc/example-music/sites.csv,
    or $SITES_CSV env var / explicit csv_path.
    """
    if csv_path is None:
        csv_path = os.environ.get("SITES_CSV")
    if csv_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(script_dir, "sites.csv"),
            os.path.join(os.getcwd(), "sites.csv"),
            "/etc/example-music/sites.csv",
        ]
        for p in candidates:
            if os.path.isfile(p):
                csv_path = p
                break

    if not csv_path or not os.path.isfile(csv_path):
        print("ERROR: sites.csv not found.")
        print("  Looked in: script directory, cwd, /etc/example-music/sites.csv")
        print("  Set SITES_CSV=/path/to/sites.csv, or pass --sites-csv <path>")
        sys.exit(1)

    sites = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = row["Site"].strip().upper()
            subnet = row["Subnet"].strip()
            octet = int(subnet.split(".")[2]) if subnet and subnet != "N/A" else None
            sites[code] = {
                "city": row["City"].strip(),
                "country": row["Country"].strip(),
                "country_code": row["CountryCode"].strip(),
                "subnet": subnet,
                "octet": octet,
                "gateway": row["Gateway"].strip(),
                "dc": row["DC"].strip(),
                "fw": row["FW"].strip(),
                "timezone": row["Timezone"].strip(),
                "ansible_region": row["AnsibleRegion"].strip(),
                "entity": row.get("Entity", "Example Music Limited").strip(),
            }
    return sites


def _load_role_codes(csv_path=None):
    """Load role code -> display name mapping from role_codes.csv."""
    if csv_path is None:
        env_path = os.environ.get("ROLE_CODES_CSV")
        if env_path and os.path.isfile(env_path):
            csv_path = env_path
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            candidates = [
                os.path.join(script_dir, "role_codes.csv"),
                os.path.join(os.getcwd(), "role_codes.csv"),
                "/etc/example-music/role_codes.csv",
            ]
            for p in candidates:
                if os.path.isfile(p):
                    csv_path = p
                    break

    if not csv_path or not os.path.isfile(csv_path):
        print("ERROR: role_codes.csv not found.")
        print("  Searched: $ROLE_CODES_CSV env var, script directory, cwd,")
        print("            /etc/example-music/role_codes.csv")
        print("  Or pass --role-codes-csv <path>")
        sys.exit(1)

    codes = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = row["Code"].strip().upper()
            codes[code] = row["Name"].strip()
    return codes


SITES = _load_sites()
ROLE_CODES = _load_role_codes()

SERIAL_CONSOLE_ROLES = {"ANS", "FWL", "NIX", "PBX", "RTR", "RRY", "RUD", "SBC", "SLT"}
DUAL_NIC_ROLES = {"FWL", "RTR"}
WINDOWS_ROLES = {"DCS", "SRV", "SVR", "WKS", "LAP"}

# Same source/meaning as v1's OS_TYPES -- key is a stable internal id,
# value is (proxmox_ostype, display_name). Select widget uses (label, value)
# pairs directly from this, so the "proper name + the value Proxmox needs"
# ask is satisfied by the data shape already being right, no rework needed.
OS_TYPES = {
    "l26":     "Linux 2.6+ kernel (Debian, Ubuntu, Rocky, AlmaLinux, etc.)",
    "l24":     "Linux 2.4 kernel (legacy)",
    "win11":   "Windows 11 / Server 2022 / Server 2025",
    "win10":   "Windows 10 / Server 2016 / Server 2019",
    "win8":    "Windows 8.x / Server 2012 / Server 2012 R2",
    "win7":    "Windows 7 / Server 2008 R2",
    "w2k8":    "Windows Vista / Server 2008",
    "wxp":     "Windows XP / Server 2003",
    "solaris": "Solaris / OpenSolaris / illumos",
    "other":   "Other / Unknown / FreeBSD / OpenBSD",
}

# Friendly names for known x86_64 ROM files -- same table as v1.
# Keys are substrings matched case-insensitively against the filename.
ROM_DESCRIPTIONS = [
    ("WORKSTATION", "25H2", "DELL2.7", "BIOS.440", "Modded SeaBIOS -- Dell SLIC 2.7 / Win Server 2025 H2 SLP (legacy BIOS)"),
    ("WORKSTATION", "25H2", "DELL2.7", "EFI20-64", "Modded UEFI 2.0 64-bit -- Dell SLIC 2.7 / Win Server 2025 H2 SLP"),
    ("WORKSTATION", "25H2", "DELL2.7", "EFI64", "Modded UEFI 64-bit -- Dell SLIC 2.7 / Win Server 2025 H2 SLP"),
    ("BIOS.440", "", "", "", "Stock SeaBIOS 440 (no SLIC -- standard QEMU BIOS)"),
    ("EFI20-64", "", "", "", "Stock UEFI 2.0 64-bit (no SLIC)"),
    ("EFI64", "", "", "", "Stock UEFI 64-bit (no SLIC)"),
]

# Static fallback list -- v1's live enumeration via nodes(node).execute.post()
# doesn't actually work (that endpoint is a batch API-call runner, not a shell
# exec -- see create-vm.py's own detect_node_arch() changelog, 2026-08-18,
# for the confirmed real behaviour); v1 silently falls back to this same
# static list when live enumeration fails, which in practice is always.
# v2 uses the static list directly rather than repeat a call that doesn't work.
KNOWN_ROMS = [
    "WORKSTATION_25H2_DELL2.7_BIOS.440.ROM",
    "WORKSTATION_25H2_DELL2.7_EFI20-64.ROM",
    "WORKSTATION_25H2_DELL2.7_EFI64.ROM",
    "BIOS.440.ROM",
    "EFI20-64.ROM",
    "EFI64.ROM",
]


def _describe_rom(filename):
    upper = filename.upper()
    for *keywords, desc in ROM_DESCRIPTIONS:
        if all(k.upper() in upper or k == "" for k in keywords):
            return desc
    return "Custom ROM"


def _is_windows(ostype):
    return bool(ostype) and ostype.lower().startswith("win")


# =============================================================================
# BACKEND — Proxmox interaction + pure config building. Adapted from v1:
# console-printing functions (ok/warn/step/err) replaced with a log_fn
# callback so output can be routed into a Textual RichLog widget instead of
# raw print() (which would corrupt a running full-screen Textual app).
# build_vm_config() is unchanged in spirit -- it never printed anything in
# v1 either, it just builds and returns a dict.
# =============================================================================

def get_existing_vms(proxmox, node):
    """Return dict of {vmid: name} for all existing VMs on the node."""
    try:
        vms = proxmox.nodes(node).qemu.get()
        return {int(vm["vmid"]): vm.get("name", "") for vm in vms}
    except Exception:
        return {}


def next_free_vmid(existing_ids, start=1000):
    vmid = start
    while vmid in existing_ids:
        vmid += 1
    return vmid


def next_free_name_suffix(existing_names, role, site):
    prefix = f"EXA{role}{site}"
    used = set()
    for name in existing_names:
        if name.upper().startswith(prefix.upper()):
            suffix = name[len(prefix):]
            if suffix.isdigit():
                used.add(int(suffix))
    for n in range(1, 1000):
        if n not in used:
            return f"{n:03d}"
    raise RuntimeError(f"All 999 names for {prefix} are taken.")


def detect_node_arch(proxmox, node):
    """Real node architecture via GET /nodes/<node>/status -> current-kernel.machine.
    Same corrected approach as v1 (2026-08-18 fix) -- NOT nodes(node).execute.post(),
    that endpoint is a batch API-call runner, not a shell exec."""
    try:
        status = proxmox.nodes(node).status.get()
        machine = status.get("current-kernel", {}).get("machine", "x86_64")
        return "arm64" if machine in ("aarch64", "arm64") else "x86_64"
    except Exception:
        return "x86_64"


def wait_for_task(proxmox, node, upid, timeout=60, poll_interval=1):
    import time
    start = time.time()
    while time.time() - start < timeout:
        try:
            status = proxmox.nodes(node).tasks(upid).status.get()
            if status.get("status") == "stopped":
                return status.get("exitstatus") == "OK"
        except Exception:
            pass
        time.sleep(poll_interval)
    return False


def build_vm_config(vmid, name, role, site, hw, storage, console,
                     nics, ostype, ipxe_iso, pool=None, driver_disk=None,
                     virtio_iso=None, bios_type="seabios", bios_rom=None,
                     storage_type=None, machine=None):
    """Build the full VM config dict — pure function, identical in shape to v1's."""
    bmc_type = hw.get("bmc_type")
    boot_order = "order=scsi0;ide2;net0"
    return {
        "vmid": vmid, "name": name, "ostype": ostype,
        "cores": hw["cores"], "sockets": hw["sockets"], "cpu": "host",
        "memory": hw["ram"], "balloon": 0,
        "bios": bios_type, "bios_rom": bios_rom, "machine": machine,
        "bmc_type": bmc_type, "boot": boot_order, "onboot": 0, "agent": 1,
        "storage": storage, "storage_type": storage_type,
        "disk_gb": hw["disk"], "disk_sizes": hw.get("disk_sizes"),
        "disk_count": hw.get("disk_count", 1),
        "console": console, "nics": nics, "ipxe_iso": ipxe_iso, "pool": pool,
        "driver_disk": driver_disk, "virtio_iso": virtio_iso,
    }


def create_vm(proxmox, node, cfg, log_fn, dry_run=False):
    """Issue API calls to create the VM. log_fn(msg, level) replaces v1's
    print-based ok/warn/step/err -- level is one of 'ok'/'warn'/'step'/'info'/'error'."""
    if dry_run:
        log_fn("Dry run — no changes made.", "info")
        return True

    vmid = cfg["vmid"]
    storage = cfg["storage"]

    log_fn(f"Creating VM {vmid} ({cfg['name']})...", "step")
    try:
        args_parts = []
        if cfg.get("bios_rom"):
            args_parts.append(f"-bios {cfg['bios_rom']}")
        if cfg.get("bmc_type") == "kcs":
            args_parts.append("-device ipmi-bmc-sim,id=bmc0 -device isa-ipmi-kcs,bmc=bmc0,irq=5")
        elif cfg.get("bmc_type") == "bt":
            args_parts.append("-device ipmi-bmc-sim,id=bmc0 -device isa-ipmi-bt,bmc=bmc0")
        extra_args = " ".join(args_parts)

        create_upid = proxmox.nodes(node).qemu.post(
            vmid=vmid, name=cfg["name"], ostype=cfg["ostype"],
            cores=cfg["cores"], sockets=cfg["sockets"], cpu="host",
            memory=cfg["memory"], balloon=0, bios=cfg["bios"],
            boot=cfg["boot"], onboot=0, agent="enabled=1",
            scsihw="virtio-scsi-pci",
            **({"pool": cfg["pool"]} if cfg["pool"] else {}),
            **({"args": extra_args} if extra_args else {}),
            **({"machine": cfg["machine"]} if cfg.get("machine") else {}),
        )
        if create_upid:
            log_fn("Waiting for VM creation task to finish...", "step")
            wait_for_task(proxmox, node, create_upid)
        log_fn(f"VM {vmid} created", "ok")
        if cfg.get("bmc_type"):
            bmc_port = 6000 + vmid
            log_fn(f"BMC emulation enabled — register with proxmoxbmc: pbmc add ... --port {bmc_port} {vmid}", "warn")
    except Exception as e:
        log_fn(f"Failed to create VM: {e}", "error")
        return False

    _discard_suffix = ",discard=on" if cfg.get("storage_type") in ("zfspool", "lvmthin") else ""
    if not _discard_suffix:
        log_fn(f"Storage type '{cfg.get('storage_type', '?')}' doesn't benefit from discard/TRIM "
               f"(only zfspool/lvmthin do) — not setting it.", "info")

    disk_count = cfg.get("disk_count", 1)
    disk_slots = ["scsi0"] + [f"scsi{i}" for i in range(2, 2 + disk_count - 1)]
    disk_sizes = cfg.get("disk_sizes") or [cfg["disk_gb"]] * disk_count

    log_fn(f"Adding disk(s) ({len(disk_slots)})...", "step")
    for slot, size in zip(disk_slots, disk_sizes):
        try:
            disk_spec = f"{storage}:{size}{_discard_suffix}"
            proxmox.nodes(node).qemu(vmid).config.put(**{slot: disk_spec})
            log_fn(f"Disk: {size}GB on {storage} ({slot}){' [discard=on]' if _discard_suffix else ''}", "ok")
        except Exception as e:
            log_fn(f"Failed to add disk {slot}: {e} — add manually", "warn")

    if cfg.get("virtio_iso"):
        log_fn("Attaching VirtIO ISO as ide2 (CDROM)...", "step")
        try:
            proxmox.nodes(node).qemu(vmid).config.put(ide2=f"{cfg['virtio_iso']},media=cdrom")
            log_fn(f"VirtIO ISO attached: {cfg['virtio_iso'].split('/')[-1]}", "ok")
        except Exception as e:
            log_fn(f"Failed to attach VirtIO ISO: {e} — attach manually as ide2", "warn")

    if cfg.get("ipxe_iso"):
        cdrom_slot = "ide3" if cfg.get("virtio_iso") else "ide2"
        log_fn(f"Attaching iPXE ISO as {cdrom_slot}...", "step")
        try:
            proxmox.nodes(node).qemu(vmid).config.put(**{cdrom_slot: f"{cfg['ipxe_iso']},media=cdrom"})
            log_fn(f"iPXE ISO attached ({cdrom_slot}): {cfg['ipxe_iso'].split('/')[-1]}", "ok")
        except Exception as e:
            log_fn(f"Failed to attach iPXE ISO: {e} — attach manually", "warn")

    log_fn("Configuring console...", "step")
    try:
        if cfg["console"] == "serial":
            proxmox.nodes(node).qemu(vmid).config.put(serial0="socket", vga="serial0")
        elif cfg["console"] == "both":
            proxmox.nodes(node).qemu(vmid).config.put(serial0="socket", vga="std,memory=32")
        elif cfg["console"] == "spice":
            proxmox.nodes(node).qemu(vmid).config.put(vga="qxl,memory=64")
        else:
            proxmox.nodes(node).qemu(vmid).config.put(vga="std,memory=32")
        log_fn(f"Console configured: {cfg['console']}", "ok")
    except Exception as e:
        log_fn(f"Failed to set console: {e}", "warn")

    log_fn("Configuring NICs...", "step")
    for nic in cfg["nics"]:
        try:
            nic_spec = f"virtio,bridge={nic['bridge']}"
            if nic["vlan"]:
                nic_spec += f",tag={nic['vlan']}"
            if nic.get("mac"):
                nic_spec += f",macaddr={nic['mac']}"
            proxmox.nodes(node).qemu(vmid).config.put(**{nic["id"]: nic_spec})
            log_fn(f"{nic['id']}: {nic['bridge']} {nic.get('vlan') or 'untagged'}", "ok")
        except Exception as e:
            log_fn(f"Failed to configure {nic['id']}: {e}", "warn")

    if cfg.get("driver_disk"):
        log_fn("Attaching VirtIO driver disk...", "step")
        try:
            proxmox.nodes(node).qemu(vmid).config.put(scsi1=f"{cfg['driver_disk']},media=disk")
            log_fn(f"Driver disk attached: {cfg['driver_disk'].split('/')[-1]} → scsi1", "ok")
        except Exception as e:
            log_fn(f"Failed to attach driver disk: {e} — attach manually as scsi1", "warn")

    return True


def write_log(log_file, cfg, node, dry_run=False):
    """Append a log entry for the created VM — same shape as v1's log format."""
    try:
        with open(os.path.expanduser(log_file), "a", encoding="utf-8") as f:
            ts = datetime.datetime.now().isoformat(timespec="seconds")
            tag = " [DRY RUN]" if dry_run else ""
            f.write(f"{ts}{tag} node={node} vmid={cfg['vmid']} name={cfg['name']} "
                    f"ostype={cfg['ostype']} storage={cfg['storage']} "
                    f"disk={cfg.get('disk_sizes') or cfg['disk_gb']}GB "
                    f"console={cfg['console']} bios={cfg['bios']}\n")
    except OSError:
        pass


# =============================================================================
# VALIDATORS — real-time duplicate checking
# =============================================================================

class VMIDValidator(Validator):
    """Rejects a VM ID that's <1000, not numeric, or already in use — either
    on the live server or already claimed earlier in the current bulk batch."""

    def __init__(self, taken_ids_fn):
        super().__init__()
        self._taken_ids_fn = taken_ids_fn

    def validate(self, value: str) -> ValidationResult:
        if not value.isdigit():
            return self.failure("VM ID must be a number.")
        vid = int(value)
        if vid < 1000:
            return self.failure("VM IDs must be 1000 or higher.")
        if vid in self._taken_ids_fn():
            return self.failure(f"VM ID {vid} is already in use.")
        return self.success()


class VMNameValidator(Validator):
    """Rejects a name that doesn't match EXA<ROLE><SITE><NNN>, or is already
    taken (server-side or earlier in the current bulk batch)."""

    _PATTERN = re.compile(r"^EXA[A-Z]{2,4}[A-Z]{3}[0-9]{3}$")

    def __init__(self, taken_names_fn):
        super().__init__()
        self._taken_names_fn = taken_names_fn

    def validate(self, value: str) -> ValidationResult:
        v = value.upper()
        if not self._PATTERN.match(v):
            return self.failure("Format: EXA[ROLE][SITE][NNN], e.g. EXAFWLFAL001")
        if v in {n.upper() for n in self._taken_names_fn()}:
            return self.failure(f"Name {v} already exists.")
        return self.success()


# =============================================================================
# SLIDER WIDGET — Textual has no stock Slider; this is a small custom one.
# Focusable, left/right/home/end adjust value within [min, max] by step.
# =============================================================================

class Slider(Widget, can_focus=True):
    """A minimal keyboard-driven slider. Arrow keys nudge the value;
    Enter switches to a plain numeric Input for exact entry (confirm with
    Enter again, cancel with Escape or by tabbing away) -- typed values are
    clamped to [min_value, max_value] the same as arrow-key stepping, so a
    daft value (69MB of RAM) can't actually be entered either way. Value
    changes post a Slider.Changed message."""

    # Lean by design -- no border box (a boxed widget per field is exactly
    # the "crammed into massive boxes" look this was rebuilt away from).
    # Focus is shown with an underline instead, matching plain Input's own
    # focus style, so a slider reads as one more form field, not its own
    # separate framed panel. The nested edit Input reuses the app-wide
    # compact Input styling (CreateVMApp.CSS) automatically, no separate
    # rule needed for it here.
    DEFAULT_CSS = """
    Slider {
        height: 1;
    }
    Slider > #slider-bar {
        height: 1;
        width: 100%;
        color: $text;
    }
    Slider:focus > #slider-bar {
        text-style: underline;
        color: $accent;
    }
    Slider > #slider-edit {
        display: none;
    }
    Slider.-editing > #slider-bar {
        display: none;
    }
    Slider.-editing > #slider-edit {
        display: block;
    }
    """

    BINDINGS = [
        Binding("left", "step(-1)", "−", show=False),
        Binding("right", "step(1)", "+", show=False),
        Binding("pageup", "step(10)", "+10", show=False),
        Binding("pagedown", "step(-10)", "−10", show=False),
        Binding("home", "to_min", "min", show=False),
        Binding("end", "to_max", "max", show=False),
        Binding("enter", "start_edit", "Type value", show=False),
    ]

    value: reactive[int] = reactive(0)

    class Changed(Message):
        def __init__(self, slider: "Slider", value: int) -> None:
            self.slider = slider
            self.value = value
            super().__init__()

    def __init__(self, min_value, max_value, value=None, step=1, suffix="", label="", id=None):
        super().__init__(id=id)
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.suffix = suffix
        self.label = label
        self._initial_value = self._clamp(value if value is not None else min_value)

    def compose(self) -> ComposeResult:
        # markup=False -- the rendered bar contains literal '[' ']' characters
        # (the bracket-and-block-glyph bar itself), which Textual's Static
        # otherwise parses as Rich console markup and fails on. Found via
        # the headless run_test() smoke test in the very first version of
        # this widget, kept here for the same reason.
        yield Static(id="slider-bar", markup=False)
        yield Input(id="slider-edit", type="integer")

    def on_mount(self) -> None:
        self.value = self._initial_value

    def _clamp(self, value: int) -> int:
        return max(self.min_value, min(self.max_value, value))

    def watch_value(self, value: int) -> None:
        # Render only -- does NOT reassign self.value here. Reactive
        # watchers re-firing on their own attribute's assignment is exactly
        # the kind of recursive-update bug worth avoiding; every entry
        # point that changes value (on_mount, action_step, to_min/max,
        # _confirm_edit) clamps via _clamp() before assigning instead.
        #
        # No is_mounted guard here (a prior version had one, speculatively,
        # and it was a real bug: bars stayed blank until the operator's
        # first interaction). Confirmed by reading Textual's own
        # MessagePump._pre_process() -- it dispatches the Mount event
        # (which runs on_mount()) BEFORE calling _post_mount() (which is
        # what actually flips _is_mounted True). So the on_mount() call
        # below (self.value = self._initial_value) always fires this
        # watcher while is_mounted is still False, even though the child
        # #slider-bar Static from compose() is already real and queryable
        # by then -- an is_mounted check here was checking the wrong thing
        # entirely, not a genuine safety net.
        width = 20
        span = max(1, self.max_value - self.min_value)
        filled = int(width * (value - self.min_value) / span)
        bar = "█" * filled + "░" * (width - filled)
        prefix = f"{self.label}: " if self.label else ""
        self.query_one("#slider-bar", Static).update(f"{prefix}{bar} {value}{self.suffix}")
        self.post_message(self.Changed(self, value))

    def action_step(self, amount: int) -> None:
        if not self.disabled:
            self.value = self._clamp(self.value + amount * self.step)

    def action_to_min(self) -> None:
        if not self.disabled:
            self.value = self.min_value

    def action_to_max(self) -> None:
        if not self.disabled:
            self.value = self.max_value

    def action_start_edit(self) -> None:
        if self.disabled:
            return
        self.add_class("-editing")
        edit_input = self.query_one("#slider-edit", Input)
        edit_input.value = str(self.value)
        edit_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "slider-edit":
            self._confirm_edit(event.value)
            event.stop()

    def on_input_blurred(self, event: Input.Blurred) -> None:
        # Losing focus without pressing Enter -- e.g. Tab to the next field
        # -- is treated as a cancel, not a confirm, so an accidental Tab
        # mid-edit can't silently commit a half-typed number.
        if event.input.id == "slider-edit" and self.has_class("-editing"):
            self._cancel_edit()

    def on_key(self, event) -> None:
        if self.has_class("-editing") and event.key == "escape":
            self._cancel_edit()
            event.stop()

    def _confirm_edit(self, raw: str) -> None:
        self.remove_class("-editing")
        try:
            typed = int(raw)
        except ValueError:
            self.focus()
            return
        self.value = self._clamp(typed)
        self.focus()

    def _cancel_edit(self) -> None:
        self.remove_class("-editing")
        self.focus()


# =============================================================================
# THEME FOOTER — Textual's stock Footer plus a live "Current Theme: X"
# indicator, used everywhere a plain Footer() used to be so it's
# consistent across every screen (login, node picker, every wizard step,
# Help, About) -- matching how F1/F7/F9 were made consistent everywhere
# in earlier passes.
# =============================================================================

class ThemeFooter(Footer):
    """Appends "| Current Theme: <name>" after the key-binding list.
    Textual's Footer.compose() sets self.styles.grid_size_columns to
    exactly the number of visible key bindings it renders (confirmed by
    reading its source, not assumed) -- appending one more grid child
    without bumping that count would just get clipped, so it's
    incremented by 1 here to make room for the extra cell."""

    DEFAULT_CSS = """
    ThemeFooter > #footer-theme {
        width: auto;
        color: $footer-foreground;
        background: $footer-background;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        if not self._bindings_ready:
            return
        yield from super().compose()
        self.styles.grid_size_columns += 1
        yield Static(f"| Current Theme: {self.app.theme}", id="footer-theme")

    def on_mount(self) -> None:
        # Cross-widget reactive watch (Textual's own DOMNode.watch(), not
        # hand-rolled) -- keeps the label live when F7 changes the theme
        # without needing the whole screen to recompose. init=False: the
        # label is already correct from compose() above, no need to fire
        # once immediately on mount too.
        self.watch(self.app, "theme", self._on_theme_changed, init=False)

    def _on_theme_changed(self, old_value: str, new_value: str) -> None:
        for label in self.query("#footer-theme"):
            label.update(f"| Current Theme: {new_value}")


# =============================================================================
# LOGIN MODAL
# =============================================================================

class LoginResult:
    def __init__(self, host, port, user, password=None, token_name=None, token_value=None):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.token_name = token_name
        self.token_value = token_value


class LoginModal(ModalScreen):
    """First thing shown on startup. Blocks the main app until dismissed
    with a working ProxmoxAPI connection."""

    DEFAULT_CSS = """
    LoginModal {
        align: center middle;
    }
    #login-box {
        width: 38;
        height: auto;
        border: round $primary;
        padding: 0 1;
        background: $surface;
    }
    #login-title {
        text-style: bold;
        margin-bottom: 0;
    }
    .field-label {
        color: $text-muted;
        margin-top: 0;
    }
    #login-error {
        color: $error;
        height: auto;
        min-height: 1;
    }
    #login-actions {
        height: auto;
    }
    """

    # F1/F7/F9 mirror CreateVMApp's own priority Help/Theme/About bindings,
    # purely for Footer display order -- see WizardScreen.BINDINGS for the
    # full explanation of why this duplication is needed (Footer.compose()
    # displays active_bindings in first-discovered order, and an App-only
    # binding is always discovered last regardless of its own list
    # position). The App's copies win any real keypress since they're
    # priority=True; these delegate to the same action so they'd still be
    # correct if that ever changed.
    BINDINGS = [
        Binding("f1", "show_help", "Help", show=True),
        Binding("f2", "do_connect", "Connect", show=True),
        Binding("f7", "cycle_theme", "Theme", show=True),
        Binding("f9", "show_about", "About", show=True),
        Binding("f10", "app_quit", "Quit", show=True),
    ]

    def __init__(self, args):
        super().__init__()
        self._args = args

    def action_show_help(self) -> None:
        self.app.action_show_help()

    def action_show_about(self) -> None:
        self.app.action_show_about()

    def action_cycle_theme(self) -> None:
        self.app.action_cycle_theme()

    def compose(self) -> ComposeResult:
        with Vertical(id="login-box"):
            yield Label("Proxmox VE — Connect", id="login-title")
            yield Label("Host / IP", classes="field-label")
            yield Input(value=self._args.host or "", placeholder="192.168.139.5", id="host")
            yield Label("Port", classes="field-label")
            yield Input(value=str(self._args.port), placeholder="8006", id="port")
            yield Label("Username", classes="field-label")
            yield Input(value=self._args.user or "root@pam", placeholder="root@pam", id="user")
            yield Label("Password", classes="field-label", id="password-label")
            yield Input(password=True, id="password")
            yield Label("Auth method", classes="field-label")
            with RadioSet(id="auth-method"):
                yield RadioButton("Password", value=True, id="auth-password")
                yield RadioButton("API Token", id="auth-token")
            yield Label("Token name", classes="field-label", id="token-name-label")
            yield Input(id="token-name", disabled=True)
            yield Label("Token value", classes="field-label", id="token-value-label")
            yield Input(password=True, id="token-value", disabled=True)
            yield Static("", id="login-error")
            # id + explicit height:auto (see DEFAULT_CSS) matters here --
            # Horizontal's own default CSS is height:1fr, and an fr-height
            # child inside an auto-height parent (#login-box) makes the
            # *parent* expand to fill the whole screen instead of
            # shrink-wrapping its content -- this was the actual cause of
            # the whole dialog running the full window height.
            with Horizontal(id="login-actions"):
                yield Button("Connect (F2)", variant="primary", id="connect")
                yield Button("Quit (F10)", id="quit")
        yield ThemeFooter()

    def action_app_quit(self) -> None:
        self.app.exit()

    def action_do_connect(self) -> None:
        self._try_connect()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        is_token = event.pressed.id == "auth-token"
        self.query_one("#password", Input).disabled = is_token
        self.query_one("#token-name", Input).disabled = not is_token
        self.query_one("#token-value", Input).disabled = not is_token

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
        elif event.button.id == "connect":
            self._try_connect()

    def _try_connect(self) -> None:
        host = self.query_one("#host", Input).value.strip()
        port_raw = self.query_one("#port", Input).value.strip()
        user = self.query_one("#user", Input).value.strip()
        error = self.query_one("#login-error", Static)

        if not host or not user:
            error.update("Host and username are required.")
            return
        try:
            port = int(port_raw) if port_raw else 8006
        except ValueError:
            error.update("Port must be a number.")
            return

        is_token = self.query_one("#auth-token", RadioButton).value
        if is_token:
            token_name = self.query_one("#token-name", Input).value.strip()
            token_value = self.query_one("#token-value", Input).value.strip()
            if not token_name or not token_value:
                error.update("Token name and value are required.")
                return
            result = LoginResult(host, port, user, token_name=token_name, token_value=token_value)
        else:
            password = self.query_one("#password", Input).value
            if not password:
                error.update("Password is required.")
                return
            result = LoginResult(host, port, user, password=password)

        error.update("Connecting...")
        self._connect_worker(result)

    @work(thread=True, exclusive=True)
    def _connect_worker(self, result: LoginResult) -> None:
        try:
            if result.token_name:
                proxmox = ProxmoxAPI(
                    result.host, port=result.port, user=result.user,
                    token_name=result.token_name, token_value=result.token_value,
                    verify_ssl=False,
                )
            else:
                proxmox = ProxmoxAPI(
                    result.host, port=result.port, user=result.user,
                    password=result.password, verify_ssl=False,
                )
            proxmox.version.get()
        except Exception as e:
            self.app.call_from_thread(self._on_connect_failed, str(e))
            return
        self.app.call_from_thread(self._on_connect_ok, proxmox, result.host, result.port)

    def _on_connect_failed(self, message: str) -> None:
        self.query_one("#login-error", Static).update(f"Connection failed: {message}")

    def _on_connect_ok(self, proxmox, host, port) -> None:
        self.dismiss((proxmox, host, port))


# =============================================================================
# NODE SELECTION MODAL — only shown if the Proxmox instance has >1 node.
# =============================================================================

class NodeModal(ModalScreen):
    DEFAULT_CSS = """
    NodeModal { align: center middle; }
    #node-box {
        width: 38; height: auto; border: round $primary;
        padding: 0 1; background: $surface;
    }
    #node-title { text-style: bold; margin-bottom: 0; }
    """

    # F1/F7/F9 mirror CreateVMApp's own priority Help/Theme/About bindings,
    # purely for Footer display order -- see WizardScreen.BINDINGS for the
    # full explanation.
    BINDINGS = [
        Binding("f1", "show_help", "Help", show=True),
        Binding("f2", "do_continue", "Continue", show=True),
        Binding("f7", "cycle_theme", "Theme", show=True),
        Binding("f9", "show_about", "About", show=True),
        Binding("f10", "app_quit", "Quit", show=True),
    ]

    def __init__(self, nodes):
        super().__init__()
        self._pve_nodes = nodes

    def action_cycle_theme(self) -> None:
        self.app.action_cycle_theme()

    def action_show_help(self) -> None:
        self.app.action_show_help()

    def action_show_about(self) -> None:
        self.app.action_show_about()

    def compose(self) -> ComposeResult:
        with Vertical(id="node-box"):
            yield Label("Select Proxmox Node", id="node-title")
            with RadioSet(id="node-choice"):
                for i, n in enumerate(self._pve_nodes):
                    status = n.get("status", "?")
                    yield RadioButton(f"{n['node']}  ({status})", value=(i == 0))
            yield Button("Continue (F2)", variant="primary", id="continue")
        yield ThemeFooter()

    def action_app_quit(self) -> None:
        self.app.exit()

    def action_do_continue(self) -> None:
        self._continue()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self._continue()

    def _continue(self) -> None:
        radio_set = self.query_one("#node-choice", RadioSet)
        idx = radio_set.pressed_index if radio_set.pressed_index is not None else 0
        self.dismiss(self._pve_nodes[idx]["node"])


# =============================================================================
# WIZARD — draft/context objects + a lean multi-screen flow, one focused
# step per screen, rather than one long scrolling form. Rebuilt 2026-08-27
# after Robert's direct feedback on the first version: unlabeled fields,
# everything crammed into bordered boxes on one page, no visible F-key
# navigation. Every field below has an explicit label; screens carry no
# outer border (a modal dialog box is normal TUI language, a boxed *form
# section* on every screen is not); Back/Next/Quit are real, visible
# Footer-bound F-keys (F1/F2/F10) on every screen, not just Ctrl+C.
# =============================================================================

class VMDraft:
    """Everything collected across the wizard for one VM. Plain container,
    not a dataclass, to match this file's existing style. Bulk mode reuses
    one draft's values as the starting point for the next VM -- see
    ReviewScreen._after_create()."""

    def __init__(self):
        self.role = None
        self.site = None
        self.name = ""
        self.vmid = ""
        self.ostype = "l26"
        self.sockets = 1
        self.cores = 2
        self.ram = 2048
        self.disk_count = 1
        self.same_disk_size = True
        self.disk_sizes = [32]
        self.bmc_type = None
        self.storage = None
        self.iso = None
        self.console = None  # resolved from role default on first visit
        self.nics = []
        self.bios_type = "seabios"
        self.bios_rom = None
        self.pool = None
        self.driver_disk = None
        self.virtio_iso = None
        self.bulk_total = 1
        self.vm_index = 1

    def clone_for_next_vm(self):
        """VM #2..N starting point -- everything carries forward except
        Name/VMID, which must be unique per VM and are reset to blank so
        IdentityScreen re-suggests them fresh."""
        import copy
        new = copy.deepcopy(self)
        new.name = ""
        new.vmid = ""
        new.vm_index = self.vm_index + 1
        return new


class WizardContext:
    """Live state shared read-only-ish across every screen: the Proxmox
    connection, the target node, and everything loaded from it once up
    front (existing VMs, storage/ISO/pool/driver-disk options) -- so
    individual screens never need their own loading spinner, they just
    read already-populated lists."""

    def __init__(self, proxmox, node, node_arch, args):
        self.proxmox = proxmox
        self.node = node
        self.node_arch = node_arch
        self.args = args

        self.existing_vms = {}
        self.existing_ids = set()
        self.existing_names = set()
        # Session-wide dupe tracking across a bulk batch -- combined with
        # existing_ids/names so two not-yet-created siblings can't collide
        # with each other either, not just with what's already on the node.
        self.batch_ids = set()
        self.batch_names = set()

        self.storage_options = []   # [(name, type), ...]
        self.iso_options = []       # [volid, ...]
        self.pool_options = []      # [poolid, ...]
        self.driver_disk_options = []
        self.virtio_iso_options = []

    def all_taken_ids(self):
        return self.existing_ids | self.batch_ids

    def all_taken_names(self):
        return self.existing_names | self.batch_names

    def load(self) -> None:
        """Blocking -- call from a worker thread, not the UI thread."""
        self.existing_vms = get_existing_vms(self.proxmox, self.node)
        self.existing_ids = set(self.existing_vms.keys())
        self.existing_names = set(self.existing_vms.values())

        try:
            stores = self.proxmox.nodes(self.node).storage.get(content="images")
            self.storage_options = [(s["storage"], s.get("type", "?"))
                                     for s in sorted(stores, key=lambda s: s["storage"])]
        except Exception:
            self.storage_options = []

        try:
            isos = self.proxmox.nodes(self.node).storage("local").content.get(content="iso")
            self.iso_options = sorted((i.get("volid", "") for i in isos), key=str)
        except Exception:
            self.iso_options = []

        try:
            pools = self.proxmox.pools.get()
            self.pool_options = sorted(p["poolid"] for p in pools)
        except Exception:
            self.pool_options = []

        self.driver_disk_options = []
        self.virtio_iso_options = []
        try:
            stores = self.proxmox.nodes(self.node).storage.get(content="iso")
            for store in stores:
                try:
                    items = self.proxmox.nodes(self.node).storage(store["storage"]).content.get(content="iso")
                    for item in items:
                        volid = item.get("volid", "")
                        if volid.lower().endswith(".img"):
                            self.driver_disk_options.append(volid)
                        elif volid.lower().endswith(".iso"):
                            self.virtio_iso_options.append(volid)
                except Exception:
                    pass
        except Exception:
            pass


class LoadingScreen(Screen):
    """Brief interstitial while WizardContext.load() runs in a worker --
    avoids a dead blank screen while storage/ISO/pool load."""

    DEFAULT_CSS = """
    LoadingScreen { align: center middle; }
    #loading-label { text-style: bold; }
    """

    def __init__(self, ctx, on_done):
        super().__init__()
        self.ctx = ctx
        self._on_done = on_done

    def compose(self) -> ComposeResult:
        yield Label("Loading node data…", id="loading-label")

    def on_mount(self) -> None:
        self._load()

    @work(thread=True, exclusive=True)
    def _load(self) -> None:
        self.ctx.load()
        self.app.call_from_thread(self._on_done, self.ctx)


# =============================================================================
# WIZARD SCREEN BASE — shared nav (F1 Back / F2 Next / F10 Quit, all real
# Footer-visible bindings), shared lean CSS, shared step-title handling.
# =============================================================================

class WizardScreen(Screen):
    STEP_NUM = 1
    STEP_TOTAL = 5
    STEP_TITLE = ""

    # F1/F9 duplicate CreateVMApp's own Help/About bindings -- the App's
    # copies are priority=True (needed to reach through LoginModal/
    # NodeModal, see CreateVMApp.BINDINGS) and will always intercept the
    # keypress first, so these two never actually fire in practice. They
    # exist here purely so the Footer displays them in the right position:
    # Footer.compose() renders self.screen.active_bindings in whatever
    # order those bindings were first discovered while walking the
    # binding chain (confirmed by reading Footer's own compose() source,
    # not assumed), and that chain is screen-first-then-App -- so an
    # App-only binding always gets discovered LAST and displays LAST,
    # regardless of where it sits in CreateVMApp.BINDINGS itself. Duplicating
    # it here, in the position it should visually appear, is what actually
    # controls footer ordering. Both delegate to the real App action
    # (action_show_help/action_show_about above) so they're correct even
    # in the hypothetical case they did fire, not just decorative.
    BINDINGS = [
        Binding("f1", "show_help", "Help", show=True),
        Binding("f2", "wizard_back", "Back", show=True),
        Binding("f3", "wizard_next", "Next", show=True),
        Binding("f7", "cycle_theme", "Theme", show=True),
        Binding("f9", "show_about", "About", show=True),
        Binding("f10", "wizard_quit", "Quit", show=True),
        # Ctrl+P/Ctrl+N as a second Back/Next shortcut alongside F2/F3 --
        # not shown in the footer (F2/F3 already cover that) to avoid a
        # cluttered duplicate entry. Landed on this pair after ruling out
        # every more "obvious" candidate by actually checking what already
        # claims it, not by assuming: plain Left/Right and PageUp/PageDown
        # are both bound by VerticalScroll itself (every field on every
        # screen sits inside one, for page/line scrolling) and would
        # silently swallow the key before it ever reached this binding;
        # PageUp/PageDown are also bound by Slider (±10 step) while it has
        # focus; Ctrl+Left/Right are bound by Input for word-jump, and
        # Input fields are half of what's on this page. Ctrl+N/Ctrl+P
        # (checked against every widget class actually used in this file)
        # are the first pair genuinely unclaimed everywhere, so they bubble
        # straight up to this binding regardless of which field has focus.
        Binding("ctrl+p", "wizard_back", "Back", show=False),
        Binding("ctrl+n", "wizard_next", "Next", show=False),
    ]

    # Density lineage: fields themselves are still MC-tight (Input/Select/
    # Checkbox collapsed to 1 row each via App.CSS, no gap between a label
    # and its own field) -- but as more fields piled onto fewer pages
    # across several merge rounds, that produced screens that read as one
    # unbroken wall of fields ("squashed up"). margin-top:1 on .field-label/
    # .field-hint puts exactly one blank row before each new field group
    # (i.e. after the previous field's widget) -- header, field, blank
    # line, next header -- without reintroducing the old multi-row-tall
    # bordered-box padding this design moved away from in the first place.
    DEFAULT_CSS = """
    WizardScreen {
        layout: vertical;
    }
    .step-body {
        padding: 0 2;
        height: 1fr;
    }
    .field-label {
        color: $text-muted;
        margin-top: 1;
    }
    .field-row {
        height: 1;
        margin-top: 1;
    }
    .field-row .field-label {
        margin-top: 0;
        width: auto;
        margin-right: 1;
    }
    .field-hint {
        color: $text-muted;
        text-style: italic;
        margin-top: 1;
    }
    #step-error {
        color: $error;
        min-height: 1;
    }
    /* Same root cause as the login dialog stretch (see LoginModal's
       #login-actions comment): a plain Vertical()'s own default CSS is
       height:1fr, and an fr-height container inside the 1fr .step-body
       greedily claims all remaining vertical space instead of sizing to
       its actual rebuilt content -- pushing everything below it (BMC/IPMI,
       the network extras) down into empty dead space. Both are dynamic
       rebuild targets (_rebuild_disk_sliders/_rebuild_nic_rows), so their
       true content height varies at runtime -- auto is what's wanted. */
    #disk-sliders, #nic-rows {
        height: auto;
    }
    .nav-row {
        height: 1;
        margin-top: 1;
    }
    """

    def __init__(self, draft: VMDraft, ctx: WizardContext):
        super().__init__()
        self.draft = draft
        self.ctx = ctx

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with VerticalScroll(classes="step-body"):
            yield from self.compose_fields()
            yield Static("", id="step-error")
        with Horizontal(classes="nav-row"):
            if self.STEP_NUM > 1:
                yield Button("< Back (F2)", id="nav-back")
            yield Button(self.next_button_label(), variant="primary", id="nav-next")
        yield ThemeFooter()

    def next_button_label(self) -> str:
        return "Next > (F3)"

    def on_mount(self) -> None:
        self.sub_title = f"Step {self.STEP_NUM} of {self.STEP_TOTAL} — {self.STEP_TITLE}"

    def compose_fields(self) -> ComposeResult:
        yield from ()

    def action_wizard_back(self) -> None:
        # Step 1 (Identity) has nothing wizard-shaped underneath it to go
        # back TO -- Login/Node are a separate connection phase already
        # completed by this point, not part of the step numbering. Popping
        # anyway lands the operator on the App's own bare default Screen:
        # no Header, no Footer, no fields, no way back into the wizard --
        # confirmed directly (not assumed) via a headless repro before
        # this guard existed. The nav-back BUTTON was already correctly
        # hidden for step 1; this closes the same hole for the F2/Ctrl+P
        # keyboard shortcuts, which weren't gated the same way.
        if self.STEP_NUM <= 1:
            return
        self.app.pop_screen()

    def action_wizard_next(self) -> None:
        self._try_next()

    def action_wizard_quit(self) -> None:
        self.app.exit()

    def action_show_help(self) -> None:
        self.app.action_show_help()

    def action_show_about(self) -> None:
        self.app.action_show_about()

    def action_cycle_theme(self) -> None:
        self.app.action_cycle_theme()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "nav-back":
            self.action_wizard_back()
        elif event.button.id == "nav-next":
            self._try_next()

    def _try_next(self) -> None:
        error = self.commit()
        if error:
            self.query_one("#step-error", Static).update(error)
            return
        nxt = self.next_screen()
        if nxt is not None:
            self.app.push_screen(nxt)

    def commit(self):
        """Validate + write this screen's fields into self.draft.
        Return an error string to block navigation, or None/'' to proceed."""
        return None

    def next_screen(self):
        """Screen instance to push next -- each concrete screen names its
        own successor directly, keeping the chain easy to follow."""
        return None


# =============================================================================
# 1. IDENTITY
# =============================================================================

class IdentityScreen(WizardScreen):
    STEP_NUM = 1
    STEP_TITLE = "Identity"

    # EXA<ROLE 2-4><SITE 3><NNN> -- same convention VMNameValidator checks,
    # used here to parse Role/Site straight out of a typed name.
    NAME_PATTERN = re.compile(r"^EXA([A-Z]{2,4})([A-Z]{3})(\d{3})$")

    def __init__(self, draft, ctx):
        super().__init__(draft, ctx)
        # One-shot suppression flags guarding the two-way name<->role/site
        # sync against re-triggering itself. Input.Changed/Select.Changed
        # are POSTED messages (queued, dispatched on a later event-loop
        # tick), not synchronous calls -- confirmed by reading Input's own
        # _watch_value() source, not assumed. A naive "set True, do the
        # assignment, set False" guard is therefore useless: by the time
        # the queued handler actually runs, the flag is already back to
        # False. Each flag here is instead consumed (reset) BY the handler
        # itself, the one time it's actually meant to skip.
        self._suppress_name_sync = False
        self._suppress_role_site_sync = 0  # counter, not bool -- role AND
        # site can both be reassigned in one _sync_role_site_from_name()
        # call, each queuing its OWN separate Select.Changed message; a
        # plain bool only suppresses the first of the two.

    def compose_fields(self) -> ComposeResult:
        # Name first -- role/site/console/NIC defaults all flow from it, so
        # it's the field everything else is downstream of, not an
        # afterthought once role/site have already been picked.
        yield Label("VM Name (role/site are parsed from this automatically)", classes="field-label")
        yield Input(value=self.draft.name, id="name",
                    validators=[VMNameValidator(self.ctx.all_taken_names)],
                    validate_on=["changed"])
        yield Label("Role", classes="field-label")
        yield Select(
            [(f"{code} — {ROLE_CODES[code]}", code) for code in sorted(ROLE_CODES)],
            id="role", allow_blank=False,
            value=self.draft.role or sorted(ROLE_CODES)[0],
        )
        yield Label("Site", classes="field-label")
        yield Select(
            [(f"{code} — {SITES[code]['city']}, {SITES[code]['country']}", code)
             for code in sorted(SITES)],
            id="site", allow_blank=False,
            value=self.draft.site or sorted(SITES)[0],
        )
        yield Label("VM ID", classes="field-label")
        yield Input(value=self.draft.vmid, id="vmid",
                    validators=[VMIDValidator(self.ctx.all_taken_ids)],
                    validate_on=["changed"])

        # Folded in from the old, separate OS/Hardware screen -- these are
        # all "who/what is this VM" essentials that belong with Name/Role/
        # Site/VMID on one page now that MC-density fields are 1 row each;
        # disk sizing stays on its own page (Storage & ISO) since it's a
        # dynamic, potentially-multi-row section in its own right.
        yield Label("Operating System", classes="field-label")
        yield Select(
            [(desc, ostype) for ostype, desc in OS_TYPES.items()],
            id="ostype", value=self.draft.ostype, allow_blank=False,
        )
        yield Label("CPU Sockets", classes="field-label")
        yield Input(value=str(self.draft.sockets), id="sockets", type="integer")
        yield Label("CPU Cores per Socket", classes="field-label")
        yield Input(value=str(self.draft.cores), id="cores", type="integer")
        yield Label("RAM (Enter to type a value, ←/→ to nudge, PgUp/PgDn ×10)", classes="field-label")
        yield Slider(256, 131072, value=self.draft.ram, step=256, suffix=" MB", id="ram")
        with Horizontal(classes="field-row"):
            yield Label("BMC / IPMI Emulation:", classes="field-label")
            with RadioSet(id="bmc-type"):
                yield RadioButton("None", value=(self.draft.bmc_type is None), id="bmc-none")
                yield RadioButton("KCS interface", value=(self.draft.bmc_type == "kcs"), id="bmc-kcs")
                yield RadioButton("BT interface", value=(self.draft.bmc_type == "bt"), id="bmc-bt")

        # Folded in from the old, separate Storage & ISO screen -- storage
        # pool + disk sizing are as much "what is this VM" as CPU/RAM are.
        # ISO selection stays behind on its own page (now just ISOScreen):
        # unlike the other fields here it isn't something every VM needs
        # an opinion on, and the SelectionList itself can run to several
        # rows, so keeping it separate is the deliberate "don't go
        # overboard" line rather than an oversight.
        yield Label("Storage Pool", classes="field-label")
        if self.ctx.storage_options:
            yield Select(
                [(f"{name} ({stype})", name) for name, stype in self.ctx.storage_options],
                id="storage", allow_blank=False,
                value=self.draft.storage or self.ctx.storage_options[0][0],
            )
        else:
            yield Select([("No image-capable storage found", "")], id="storage", allow_blank=False)
        yield Label("Number of Disks", classes="field-label")
        yield Input(value=str(self.draft.disk_count), id="disk-count", type="integer")
        yield Checkbox("Same size for all disks", value=self.draft.same_disk_size, id="same-disk-size")
        yield Vertical(id="disk-sliders")

    async def on_mount(self) -> None:
        super().on_mount()
        self._suggest_if_blank()
        await self._rebuild_disk_sliders()

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "disk-count":
            await self._rebuild_disk_sliders()
            return
        if event.input.id != "name":
            return
        if self._suppress_name_sync:
            self._suppress_name_sync = False
            return
        self._sync_role_site_from_name(event.value)

    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "same-disk-size":
            await self._rebuild_disk_sliders()

    def _disk_count(self) -> int:
        try:
            n = int(self.query_one("#disk-count", Input).value)
        except ValueError:
            n = 1
        return max(1, min(8, n))

    async def _rebuild_disk_sliders(self) -> None:
        container = self.query_one("#disk-sliders", Vertical)
        old_values = [s.value for s in container.query(Slider)]
        await container.remove_children()

        n = self._disk_count()
        same_size = self.query_one("#same-disk-size", Checkbox).value

        if same_size:
            default = old_values[0] if old_values else (self.draft.disk_sizes[0] if self.draft.disk_sizes else 32)
            await container.mount(Label("Disk size (all disks)", classes="field-label"))
            await container.mount(Slider(1, 8192, value=default, suffix=" GB", id="disk-size-0"))
        else:
            for i in range(n):
                default = old_values[i] if i < len(old_values) else (
                    old_values[0] if old_values else (
                        self.draft.disk_sizes[i] if i < len(self.draft.disk_sizes) else 32
                    )
                )
                await container.mount(Label(f"Disk {i + 1} size", classes="field-label"))
                await container.mount(Slider(1, 8192, value=default, suffix=" GB", id=f"disk-size-{i}"))

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id not in ("role", "site"):
            return
        if self._suppress_role_site_sync > 0:
            self._suppress_role_site_sync -= 1
            return
        self._suggest_if_blank()

    def _sync_role_site_from_name(self, name: str) -> None:
        """A fully-typed, valid name drives Role/Site, not the other way
        round -- e.g. typing EXAFWLDRS001 directly sets Role=FWL, Site=DRS
        without needing them picked from the dropdowns first."""
        match = self.NAME_PATTERN.match(name.upper())
        if not match:
            return
        role, site, _suffix = match.groups()
        if role not in ROLE_CODES or site not in SITES:
            return
        role_select = self.query_one("#role", Select)
        site_select = self.query_one("#site", Select)
        if role_select.value != role:
            self._suppress_role_site_sync += 1
            role_select.value = role
        if site_select.value != site:
            self._suppress_role_site_sync += 1
            site_select.value = site
        # The name was just typed deliberately -- track it as "the last
        # thing WE suggested" too, so a later role/site tweak that happens
        # to still match this exact name is free to re-suggest, but doesn't
        # clobber a genuinely different name the operator typed since.
        self._last_auto_name = name.upper()

    def _suggest_if_blank(self) -> None:
        role = self.query_one("#role", Select).value
        site = self.query_one("#site", Select).value
        name_input = self.query_one("#name", Input)
        vmid_input = self.query_one("#vmid", Input)

        # Re-suggest whenever the field is blank OR still holds exactly the
        # last thing this screen auto-suggested -- keeps tracking role/site
        # right up until the operator types a name/VMID of their own.
        last_name = getattr(self, "_last_auto_name", None)
        last_vmid = getattr(self, "_last_auto_vmid", None)
        if name_input.value in ("", last_name):
            suggested = f"EXA{role}{site}{next_free_name_suffix(self.ctx.all_taken_names(), role, site)}"
            self._suppress_name_sync = True  # setting .value below would otherwise loop back into _sync_role_site_from_name
            name_input.value = suggested
            self._last_auto_name = suggested
        if vmid_input.value in ("", last_vmid):
            suggested_vmid = str(next_free_vmid(self.ctx.all_taken_ids()))
            vmid_input.value = suggested_vmid
            self._last_auto_vmid = suggested_vmid

    def commit(self):
        name_input = self.query_one("#name", Input)
        vmid_input = self.query_one("#vmid", Input)
        if not name_input.is_valid:
            return "Fix the VM Name before continuing."
        if not vmid_input.is_valid:
            return "Fix the VM ID before continuing."
        try:
            sockets = int(self.query_one("#sockets", Input).value)
            cores = int(self.query_one("#cores", Input).value)
        except ValueError:
            return "CPU sockets/cores must be whole numbers."
        if sockets < 1 or cores < 1:
            return "CPU sockets/cores must be at least 1."
        total = sockets * cores
        if total > 1 and total % 2 != 0:
            return f"Total vCPUs ({cores} × {sockets} = {total}) must be even."

        self.draft.role = self.query_one("#role", Select).value
        self.draft.site = self.query_one("#site", Select).value
        self.draft.name = name_input.value.upper()
        self.draft.vmid = vmid_input.value
        self.draft.ostype = self.query_one("#ostype", Select).value
        self.draft.sockets = sockets
        self.draft.cores = cores
        self.draft.ram = self.query_one("#ram", Slider).value
        if self.query_one("#bmc-kcs", RadioButton).value:
            self.draft.bmc_type = "kcs"
        elif self.query_one("#bmc-bt", RadioButton).value:
            self.draft.bmc_type = "bt"
        else:
            self.draft.bmc_type = None

        storage_select = self.query_one("#storage", Select)
        if storage_select.value in (Select.BLANK, ""):
            return "Select a storage pool before continuing."
        self.draft.storage = storage_select.value

        same_size = self.query_one("#same-disk-size", Checkbox).value
        n = self._disk_count()
        sliders = self.query_one("#disk-sliders", Vertical).query(Slider)
        slider_values = [s.value for s in sliders]
        self.draft.disk_count = n
        self.draft.same_disk_size = same_size
        self.draft.disk_sizes = [slider_values[0]] * n if same_size else slider_values
        return None

    def next_screen(self):
        return ISOScreen(self.draft, self.ctx)


# =============================================================================
# 2. ISO
# =============================================================================

class ISOScreen(WizardScreen):
    STEP_NUM = 2
    STEP_TITLE = "ISO"

    def compose_fields(self) -> ComposeResult:
        yield Label("iPXE ISO (optional — tick one, or leave blank)", classes="field-label")
        iso_list = SelectionList(id="iso-list")
        yield iso_list

    def on_mount(self) -> None:
        super().on_mount()
        iso_list = self.query_one("#iso-list", SelectionList)
        for volid in self.ctx.iso_options:
            name = volid.split("/")[-1] if "/" in volid else volid
            iso_list.add_option(Selection(name, volid, volid == self.draft.iso))

    def on_selection_list_selection_toggled(self, event: SelectionList.SelectionToggled) -> None:
        # Single-select in spirit ("attach one, or none") even though
        # SelectionList itself is multi-select -- ticking a new entry
        # un-ticks whatever was previously ticked.
        if event.selection_list.id != "iso-list":
            return
        iso_list = event.selection_list
        if event.selection.value in iso_list.selected:
            for volid in list(iso_list.selected):
                if volid != event.selection.value:
                    iso_list.deselect(volid)

    def commit(self):
        selected = self.query_one("#iso-list", SelectionList).selected
        self.draft.iso = selected[0] if selected else None
        return None

    def next_screen(self):
        return NetworkScreen(self.draft, self.ctx)


# =============================================================================
# 3. NETWORK
# =============================================================================

class NetworkScreen(WizardScreen):
    STEP_NUM = 3
    STEP_TITLE = "Network"

    def compose_fields(self) -> ComposeResult:
        default_count = len(self.draft.nics) or (2 if self.draft.role in DUAL_NIC_ROLES else 1)
        yield Label("Number of NICs", classes="field-label")
        yield Input(value=str(default_count), id="nic-count", type="integer")
        yield Vertical(id="nic-rows")

        # Folded in from the old, separate Console & BIOS screen -- grouped
        # here with NICs at Robert's request rather than with Identity.
        # Unlike when this lived on Identity, self.draft.role is always
        # already set by the time NetworkScreen is reached (Identity is
        # screen 1 and always commits first in this linear wizard), so the
        # role-based console default can just read it directly -- no need
        # for the compose-time "effective role" fallback Identity needed
        # when Console sat on the same page as the Role dropdown itself.
        default_console = self.draft.console or ("both" if self.draft.role in SERIAL_CONSOLE_ROLES else "spice")
        with Horizontal(classes="field-row"):
            yield Label("Console Type:", classes="field-label")
            with RadioSet(id="console"):
                yield RadioButton("VGA only", value=(default_console == "vga"), id="console-vga")
                yield RadioButton("VGA + Serial", value=(default_console == "both"), id="console-both")
                yield RadioButton("Serial only", value=(default_console == "serial"), id="console-serial")
                yield RadioButton("SPICE", value=(default_console == "spice"), id="console-spice")

        with Horizontal(classes="field-row"):
            yield Label("BIOS:", classes="field-label")
            with RadioSet(id="bios-type"):
                yield RadioButton("SeaBIOS", value=(self.draft.bios_type != "ovmf"), id="bios-seabios")
                yield RadioButton("UEFI", value=(self.draft.bios_type == "ovmf"), id="bios-uefi")

        if self.ctx.node_arch != "arm64":
            yield Label("ROM Variant (x86_64 only)", classes="field-label")
            yield Select([("Default (no custom ROM)", "")], id="bios-rom", allow_blank=False)
        else:
            yield Label("arm64 target — no SLIC ROM menu applies here.", classes="field-hint")

        # Folded in from Identity -- Resource Pool and bulk VM count were
        # briefly on the bottom of the Identity page, now grouped here
        # with Console/BIOS instead per Robert's request.
        yield Label("Resource Pool (optional)", classes="field-label")
        yield Select(
            [("(none)", "")] + [(p, p) for p in self.ctx.pool_options],
            id="pool", allow_blank=False, value=self.draft.pool or "",
        )
        yield Label("Number of VMs to create (bulk mode — this one counts as #1)", classes="field-label")
        yield Input(value=str(self.draft.bulk_total), id="bulk-total", type="integer")

    async def on_mount(self) -> None:
        super().on_mount()
        self._update_rom_list()
        await self._rebuild_nic_rows()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "bios-type":
            self._update_rom_list()

    def _update_rom_list(self) -> None:
        if self.ctx.node_arch == "arm64":
            return
        rom_select = self.query_one("#bios-rom", Select)
        is_efi = self.query_one("#bios-uefi", RadioButton).value
        matching = [r for r in KNOWN_ROMS if ("EFI" in r.upper()) == is_efi]
        rom_select.set_options(
            [("Default (no custom ROM)", "")]
            + [(f"{r} — {_describe_rom(r)}", f"/usr/share/kvm/{r}") for r in matching]
        )
        if self.draft.bios_rom:
            rom_select.value = self.draft.bios_rom

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "nic-count":
            await self._rebuild_nic_rows()

    def _nic_defaults(self, idx: int):
        role, site = self.draft.role, self.draft.site
        cld_vlan = SITES["CLD"]["octet"]
        vrk_octet = SITES["VRK"]["octet"]
        if site == "VRK":
            return "vmbr0", "", "vRACK (native, untagged)"
        vlan_id = SITES[site]["octet"]
        dual_nic = role in DUAL_NIC_ROLES
        if dual_nic:
            if idx == 0:
                return "vmbr0", str(vrk_octet), "WAN / provisioning (vRACK)"
            elif idx == 1:
                return "vmbr1", str(vlan_id), f"LAN — {site} VLAN {vlan_id}"
            return "vmbr1", str(cld_vlan), f"Additional NIC {idx}"
        if idx == 0:
            return "vmbr1", str(vlan_id), f"{site} VLAN {vlan_id}"
        return "vmbr1", str(cld_vlan), f"Additional NIC {idx}"

    async def _rebuild_nic_rows(self) -> None:
        container = self.query_one("#nic-rows", Vertical)
        await container.remove_children()

        try:
            n = max(1, min(10, int(self.query_one("#nic-count", Input).value)))
        except ValueError:
            n = 1

        for i in range(n):
            if i < len(self.draft.nics):
                nic = self.draft.nics[i]
                bridge, vlan, desc = nic["bridge"], ("" if nic["vlan"] is None else str(nic["vlan"])), nic["desc"]
                mac = nic.get("mac") or ""
            else:
                bridge, vlan, desc = self._nic_defaults(i)
                mac = ""
            await container.mount(Label(f"NIC net{i}", classes="field-label"))
            await container.mount(Label("  Bridge", classes="field-hint"))
            await container.mount(Input(value=bridge, id=f"nic-bridge-{i}", placeholder="vmbrN"))
            await container.mount(Label("  VLAN (blank = untagged)", classes="field-hint"))
            await container.mount(Input(value=vlan, id=f"nic-vlan-{i}"))
            await container.mount(Label("  Description", classes="field-hint"))
            await container.mount(Input(value=desc, id=f"nic-desc-{i}"))
            await container.mount(Label("  MAC (blank = auto)", classes="field-hint"))
            await container.mount(Input(value=mac, id=f"nic-mac-{i}"))

    def commit(self):
        cld_vlan = SITES["CLD"]["octet"]
        vrk_octet = SITES["VRK"]["octet"]
        try:
            n = max(1, min(10, int(self.query_one("#nic-count", Input).value)))
        except ValueError:
            n = 1
        nics = []
        for i in range(n):
            bridge = self.query_one(f"#nic-bridge-{i}", Input).value.strip() or "vmbr1"
            if not re.match(r"^vmbr\d+$", bridge):
                return f"NIC net{i}: bridge must be vmbrN (e.g. vmbr0, vmbr1)."
            vlan_raw = self.query_one(f"#nic-vlan-{i}", Input).value.strip()
            desc = self.query_one(f"#nic-desc-{i}", Input).value.strip()
            mac = self.query_one(f"#nic-mac-{i}", Input).value.strip() or None
            vlan = int(vlan_raw) if vlan_raw.isdigit() else None
            if bridge == "vmbr0" and vlan in (cld_vlan, vrk_octet, None):
                vlan = None
            if mac and not re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", mac):
                mac = None
            nics.append({"id": f"net{i}", "model": "virtio", "bridge": bridge,
                         "vlan": vlan, "mac": mac, "desc": desc})
        self.draft.nics = nics

        if self.query_one("#console-serial", RadioButton).value:
            self.draft.console = "serial"
        elif self.query_one("#console-both", RadioButton).value:
            self.draft.console = "both"
        elif self.query_one("#console-spice", RadioButton).value:
            self.draft.console = "spice"
        else:
            self.draft.console = "vga"

        is_efi = self.query_one("#bios-uefi", RadioButton).value
        self.draft.bios_type = "ovmf" if is_efi else "seabios"
        if self.ctx.node_arch == "arm64":
            self.draft.bios_rom = None
        else:
            rom_select = self.query_one("#bios-rom", Select)
            self.draft.bios_rom = rom_select.value if rom_select.value not in (Select.BLANK, "") else None

        pool_select = self.query_one("#pool", Select)
        self.draft.pool = pool_select.value or None
        try:
            bulk_total = max(1, int(self.query_one("#bulk-total", Input).value))
        except ValueError:
            bulk_total = 1
        self.draft.bulk_total = bulk_total
        return None

    def next_screen(self):
        return ExtrasScreen(self.draft, self.ctx)


# =============================================================================
# 4. EXTRAS — Windows driver disk / VirtIO ISO only
# =============================================================================

class ExtrasScreen(WizardScreen):
    STEP_NUM = 4
    STEP_TITLE = "Extras"

    def next_button_label(self) -> str:
        return "Review > (F3)"

    def compose_fields(self) -> ComposeResult:
        # Resource Pool and bulk VM count moved onto Identity (page 1) at
        # Robert's request. What's left here is genuinely role-conditional
        # (Windows-only) -- for every other role this page is just Back/
        # Next with a note, which is expected, not an oversight.
        if self.draft.role in WINDOWS_ROLES:
            yield Label("VirtIO Driver Disk (scsi1)", classes="field-label")
            yield Select(
                [("(none)", "")] + [(v.split("/")[-1], v) for v in self.ctx.driver_disk_options],
                id="driver-disk", allow_blank=False, value=self.draft.driver_disk or "",
            )
            yield Label("VirtIO Drivers ISO (optional — postOOBE.cmd usually handles this)", classes="field-label")
            yield Select(
                [("(none)", "")] + [(v.split("/")[-1], v) for v in self.ctx.virtio_iso_options],
                id="virtio-iso", allow_blank=False, value=self.draft.virtio_iso or "",
            )
        else:
            yield Label("No extra options for this role.", classes="field-hint")

    def commit(self):
        if self.draft.role in WINDOWS_ROLES:
            dd = self.query_one("#driver-disk", Select).value
            self.draft.driver_disk = dd or None
            vi = self.query_one("#virtio-iso", Select).value
            self.draft.virtio_iso = vi or None
        return None

    def next_screen(self):
        return ReviewScreen(self.draft, self.ctx, vm_index=self.draft.vm_index)


# =============================================================================
# 5. REVIEW + CREATE
# =============================================================================

class ReviewScreen(WizardScreen):
    STEP_NUM = 5
    STEP_TITLE = "Review & Create"

    BINDINGS = [
        Binding("f1", "show_help", "Help", show=True),
        Binding("f2", "wizard_back", "Back", show=True),
        Binding("f3", "do_create", "Create", show=True),
        Binding("f7", "cycle_theme", "Theme", show=True),
        Binding("f9", "show_about", "About", show=True),
        Binding("f10", "wizard_quit", "Quit", show=True),
        Binding("ctrl+p", "wizard_back", "Back", show=False),
        Binding("ctrl+n", "do_create", "Create", show=False),
    ]

    def __init__(self, draft, ctx, vm_index=1):
        super().__init__(draft, ctx)
        self.vm_index = vm_index

    def next_button_label(self) -> str:
        return "Create VM (F3)"

    def compose_fields(self) -> ComposeResult:
        d = self.draft
        disk_desc = (f"{d.disk_count} × {d.disk_sizes[0]}GB" if d.same_disk_size
                     else " / ".join(f"{s}GB" for s in d.disk_sizes))
        bmc_desc = {"kcs": "KCS", "bt": "BT"}.get(d.bmc_type, "None")
        iso_desc = d.iso.split("/")[-1] if d.iso else "(none)"
        nic_desc = ", ".join(f"{n['id']}={n['bridge']}"
                              + (f"/vlan{n['vlan']}" if n['vlan'] else "/untagged")
                              for n in d.nics) or "(none)"

        yield Label(f"VM {self.vm_index} of {d.bulk_total}", classes="field-hint")
        for line in [
            f"Name        {d.name}    (VMID {d.vmid})",
            f"Role / Site  {d.role} / {d.site}",
            f"OS           {OS_TYPES.get(d.ostype, d.ostype)}",
            f"CPU          {d.sockets} socket(s) × {d.cores} core(s)",
            f"RAM          {d.ram} MB",
            f"Disks        {disk_desc} on {d.storage}",
            f"BMC          {bmc_desc}",
            f"Console      {d.console}",
            f"BIOS         {d.bios_type}" + (f" ({d.bios_rom.split('/')[-1]})" if d.bios_rom else ""),
            f"ISO          {iso_desc}",
            f"NICs         {nic_desc}",
            f"Pool         {d.pool or '(none)'}",
        ]:
            yield Static(line)
        yield RichLog(id="create-log", markup=True)

    def commit(self):
        return None

    def next_screen(self):
        return None

    def action_do_create(self) -> None:
        self._create()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "nav-back":
            self.action_wizard_back()
        elif event.button.id == "nav-next":
            self._create()

    def _log(self, message: str, level: str = "info") -> None:
        colours = {"ok": "green", "warn": "yellow", "error": "red", "step": "cyan", "info": "white"}
        self.query_one("#create-log", RichLog).write(f"[{colours.get(level, 'white')}]{message}[/{colours.get(level, 'white')}]")

    def _create(self) -> None:
        d = self.draft
        machine = "virt" if self.ctx.node_arch == "arm64" else None
        hw = {"sockets": d.sockets, "cores": d.cores, "ram": d.ram,
              "disk": d.disk_sizes[0] if d.disk_sizes else 32,
              "disk_sizes": d.disk_sizes, "disk_count": d.disk_count,
              "bmc_type": d.bmc_type}
        storage_type = next((stype for name, stype in self.ctx.storage_options if name == d.storage), None)

        cfg = build_vm_config(
            vmid=int(d.vmid), name=d.name, role=d.role, site=d.site, hw=hw,
            storage=d.storage, console=d.console, nics=d.nics, ostype=d.ostype,
            ipxe_iso=d.iso, pool=d.pool, driver_disk=d.driver_disk,
            virtio_iso=d.virtio_iso, bios_type=d.bios_type, bios_rom=d.bios_rom,
            storage_type=storage_type, machine=machine,
        )
        self.ctx.batch_names.add(d.name)
        self.ctx.batch_ids.add(int(d.vmid))
        self._log(f"Submitting {d.name} (VMID {d.vmid})…", "step")
        self._run_create(cfg)

    @work(thread=True, exclusive=True)
    def _run_create(self, cfg: dict) -> None:
        def log_fn(msg, level):
            self.app.call_from_thread(self._log, msg, level)
        success = create_vm(self.ctx.proxmox, self.ctx.node, cfg, log_fn, dry_run=self.ctx.args.dry_run)
        if success:
            write_log(self.ctx.args.log, cfg, self.ctx.node, dry_run=self.ctx.args.dry_run)
        self.app.call_from_thread(self._after_create, success)

    def _after_create(self, success: bool) -> None:
        if not success:
            self._log("VM creation failed — see log above.", "error")
            return
        self._log(f"Done ({self.vm_index}/{self.draft.bulk_total}).", "ok")
        if self.vm_index >= self.draft.bulk_total:
            self._log("Bulk session complete.", "ok")
            return
        next_draft = self.draft.clone_for_next_vm()
        self.app.push_screen(IdentityScreen(next_draft, self.ctx))


# =============================================================================
# HELP + ABOUT MODALS — F1 opens Help from anywhere in the app; Help links
# through to About rather than giving About its own dedicated shortcut.
# =============================================================================

class AboutModal(ModalScreen):
    """A small About box. Its own easter egg: type 'ø' while this is open
    and it reveals a Dannebrog (the Danish flag) -- confirmed via a
    headless key-press test that Textual reports both event.key and
    event.character as the literal 'ø' for this input, so a plain
    character comparison in on_key() is enough; no special Unicode-key
    binding syntax needed."""

    DEFAULT_CSS = """
    AboutModal { align: center middle; }
    #about-box {
        width: 48; height: auto; border: round $primary;
        padding: 0 1; background: $surface;
    }
    #about-title { text-style: bold; margin-bottom: 0; }
    #about-egg { color: $accent; text-style: bold; min-height: 1; }
    """

    BINDINGS = [
        Binding("escape", "close_about", "Close", show=True),
        Binding("f10", "close_about", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="about-box"):
            yield Label("About", id="about-title")
            yield Static("create-vm-tui.py — Proxmox VE VM creation wizard")
            yield Static("Textual TUI v2 of create-vm.py.")
            yield Static("EXA<ROLE><SITE><NNN> naming convention.")
            yield Static("jukebox.internal estate tooling.")
            yield Static("", id="about-egg", markup=False)
            yield Button("Close (Esc)", id="about-close")
        yield ThemeFooter()

    def action_close_about(self) -> None:
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "about-close":
            self.dismiss()

    def on_key(self, event) -> None:
        if event.character == "ø":
            self.query_one("#about-egg", Static).update("🇩🇰 Dannebrog!")


class HelpModal(ModalScreen):
    """Traditional F1-opens-help, reachable from any screen in the app
    (LoginModal, NodeModal, every wizard step) since it's bound at the
    App level, not per-screen. A quick reference, not full documentation
    -- keeps this in step with the rest of the app's lean-modal style
    rather than growing into its own multi-page thing."""

    DEFAULT_CSS = """
    HelpModal { align: center middle; }
    #help-box {
        width: 56; height: auto; border: round $primary;
        padding: 0 1; background: $surface;
    }
    #help-title { text-style: bold; margin-bottom: 0; }
    .help-line { color: $text; }
    #help-actions { height: auto; margin-top: 1; }
    """

    # No F1-to-close binding here -- CreateVMApp's own F1 is priority=True
    # (needed so F1 reaches Help from inside LoginModal/NodeModal, which
    # are themselves modals and would otherwise truncate the normal
    # bubble-up chain before it ever reached the App). A priority binding
    # always wins the check before this screen's own bindings are even
    # looked at, so an F1 binding here would just be dead code -- Escape/
    # F10/the Close button are the real ways out of this modal.
    BINDINGS = [
        Binding("escape", "close_help", "Close", show=True),
        Binding("f10", "close_help", "Close", show=False),
    ]

    HELP_LINES = [
        "F1              Help (this screen)",
        "F2              Back",
        "F3              Next / Create",
        "F7              Cycle colour theme",
        "F9              About",
        "F10             Quit",
        "Ctrl+P / Ctrl+N Back / Next (alternate)",
        "Enter           On a slider: type an exact value",
        "← / →           On a slider: nudge by 1 step",
        "PgUp / PgDn     On a slider: nudge by 10 steps",
        "Tab / Shift+Tab Move between fields",
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-box"):
            yield Label("Keyboard Shortcuts", id="help-title")
            for line in self.HELP_LINES:
                yield Static(line, classes="help-line", markup=False)
            with Horizontal(id="help-actions"):
                yield Button("About", id="help-about")
                yield Button("Close (Esc)", id="help-close")
        yield ThemeFooter()

    def action_close_help(self) -> None:
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "help-close":
            self.dismiss()
        elif event.button.id == "help-about":
            self.app.push_screen(AboutModal())


# =============================================================================
# APP — ties LoginModal -> (NodeModal if >1 node) -> VMFormScreen together.
# =============================================================================

class CreateVMApp(App):
    TITLE = "Proxmox VE — VM Creation (jukebox.internal)"
    # F1 = Help, app-wide -- traditional Help key, freed up by moving
    # wizard Back/Next off F1/F2 onto F2/F3 (see WizardScreen.BINDINGS).
    # priority=True is load-bearing, not decoration: LoginModal/NodeModal
    # are themselves ModalScreens, and Textual's normal (non-priority) key
    # dispatch walks _modal_binding_chain, which truncates right at the
    # first modal screen it finds -- meaning a plain App-level F1 binding
    # would never even be checked while either of those two is showing
    # (confirmed empirically: F1 silently did nothing from LoginModal
    # until this was made priority). Priority bindings instead use the
    # untruncated chain and are checked App-down before the key is
    # forwarded to whatever's focused, so this reaches Help from anywhere,
    # including underneath a modal.
    # F9 = About, same reasoning and same priority=True requirement as F1
    # -- reachable directly (not just via Help's About button) from
    # anywhere, including LoginModal/NodeModal.
    # F7 = cycle colour theme -- steps through Textual's built-in themes
    # (self.available_themes), wrapping round. Deliberately NOT using
    # App.action_change_theme()/search_themes() -- that opens a full
    # CommandPalette fuzzy-search overlay, a different interaction model
    # entirely from "scroll through themes" one key at a time, and this
    # app already turned the command palette off (ENABLE_COMMAND_PALETTE
    # below) for the Ctrl+P conflict two passes ago; search_themes() would
    # have worked around that (it's a separate code path from the
    # App-level ctrl+p binding), but a direct cycle matches the ask and
    # this app's whole keyboard-first, no-popup-search style better.
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("f1", "show_help", "Help", show=True, priority=True),
        Binding("f7", "cycle_theme", "Theme", show=True, priority=True),
        Binding("f9", "show_about", "About", show=True, priority=True),
    ]
    # Textual reserves ctrl+p for its own command palette (App.
    # COMMAND_PALETTE_BINDING, wired in as a system binding -- it doesn't
    # show up in App.BINDINGS itself, only found by reading the source).
    # This tool has no custom commands registered for it to search, and it
    # was silently winning over the wizard's own Ctrl+P "Back" shortcut
    # (confirmed empirically -- Ctrl+P was opening the palette instead of
    # navigating). Disabled rather than picking yet another key, since the
    # palette isn't a feature this tool uses.
    ENABLE_COMMAND_PALETTE = False

    # Compact, Midnight-Commander-density widget sizing, applied app-wide.
    # Textual's stock Input/Select default to a "tall" (2-row) border, which
    # is what actually made every field look oversized -- a single-line
    # Input renders as 3 real terminal rows (border-top + content +
    # border-bottom) no matter which border *style* is used, tall/round/
    # solid all cost the same 3 rows; the only way to genuinely collapse a
    # single-line field to 1 row is no border at all. That drops Textual's
    # only built-in invalid-state cue (a red border), so it's replaced here
    # with a red background tint instead -- still an immediate, unambiguous
    # visual signal, just not one that costs two extra rows to show.
    CSS = """
    Input {
        height: 1;
        border: none;
        background: $boost;
        padding: 0 1;
    }
    Input:focus {
        background: $panel;
    }
    Input.-invalid {
        background: $error 30%;
    }
    Input.-invalid:focus {
        background: $error 50%;
    }
    Select > SelectCurrent {
        height: 1;
        border: none;
        background: $boost;
        padding: 0 1;
    }
    Select:focus > SelectCurrent {
        background: $panel;
    }
    RadioSet {
        border: none;
        padding: 0;
        background: transparent;
        height: auto;
    }
    RadioSet#console, RadioSet#bmc-type, RadioSet#bios-type {
        layout: horizontal;
        width: auto;
        height: 1;
    }
    RadioSet#console > RadioButton, RadioSet#bmc-type > RadioButton, RadioSet#bios-type > RadioButton {
        width: auto;
        margin-right: 2;
    }
    Checkbox {
        border: none;
        background: transparent;
        padding: 0 1;
        height: 1;
    }
    Checkbox:focus {
        background: $boost;
    }
    Button {
        height: 1;
        min-width: 10;
        border-top: none;
        border-bottom: none;
        padding: 0 1;
    }
    """

    def __init__(self, args):
        super().__init__()
        self.args = args
        # Textual's own built-in default already happens to be
        # textual-dark (confirmed directly, not assumed) -- pinned here
        # explicitly anyway so the choice is documented as deliberate
        # rather than an accident of whatever Textual's upstream default
        # happens to be in a given version. Robert's own preference, and
        # it genuinely helps: better contrast for glaucoma and other
        # visual impairments than a light theme. F7 still freely cycles
        # away from it for the rest of the session as normal -- this only
        # pins the starting point.
        self.theme = "textual-dark"

    def action_show_help(self) -> None:
        # Guard against stacking a second Help modal on top of itself if
        # F1 is pressed again while it's already open.
        if not isinstance(self.screen, HelpModal):
            self.push_screen(HelpModal())

    def action_show_about(self) -> None:
        # Same double-open guard as Help, and the same reasoning applies
        # if F9 is pressed again while About is already showing.
        if not isinstance(self.screen, AboutModal):
            self.push_screen(AboutModal())

    def action_cycle_theme(self) -> None:
        names = sorted(self.available_themes)
        current = self.theme
        next_index = (names.index(current) + 1) % len(names) if current in names else 0
        self.theme = names[next_index]

    def on_mount(self) -> None:
        self.push_screen(LoginModal(self.args), self._on_login_done)

    def _on_login_done(self, result) -> None:
        if result is None:
            self.exit()
            return
        proxmox, host, port = result
        self._select_node(proxmox)

    @work(thread=True, exclusive=True)
    def _select_node(self, proxmox) -> None:
        try:
            nodes = proxmox.nodes.get()
        except Exception as e:
            self.call_from_thread(self.exit, message=f"Failed to list nodes: {e}")
            return
        if not nodes:
            self.call_from_thread(self.exit, message="No nodes found on this Proxmox instance.")
            return
        if self.args.node:
            names = [n["node"] for n in nodes]
            if self.args.node not in names:
                self.call_from_thread(self.exit, message=f"Node '{self.args.node}' not found. Available: {', '.join(names)}")
                return
            self.call_from_thread(self._on_node_chosen, proxmox, self.args.node)
        elif len(nodes) == 1:
            self.call_from_thread(self._on_node_chosen, proxmox, nodes[0]["node"])
        else:
            self.call_from_thread(self.push_screen, NodeModal(nodes),
                                   lambda node: self._on_node_chosen(proxmox, node))

    def _on_node_chosen(self, proxmox, node) -> None:
        self._detect_arch_and_start(proxmox, node)

    @work(thread=True, exclusive=True)
    def _detect_arch_and_start(self, proxmox, node) -> None:
        arch = detect_node_arch(proxmox, node)
        self.call_from_thread(self._start_loading, proxmox, node, arch)

    def _start_loading(self, proxmox, node, arch) -> None:
        ctx = WizardContext(proxmox, node, arch, self.args)
        self.push_screen(LoadingScreen(ctx, self._start_wizard))

    def _start_wizard(self, ctx: WizardContext) -> None:
        self.pop_screen()  # drop LoadingScreen
        self.push_screen(IdentityScreen(VMDraft(), ctx))


# =============================================================================
# ENTRY POINT
# =============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Create Proxmox VMs following the EXA naming convention — TUI (v2).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--host", help="Proxmox host/IP (pre-fills the login screen)")
    parser.add_argument("--port", type=int, default=8006, help="API port (default: 8006)")
    parser.add_argument("--user", help="Proxmox username (e.g. root@pam)")
    parser.add_argument("--node", help="Proxmox node name (skips the node-selection screen)")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="Show what would be created without making changes")
    parser.add_argument("--log", default=os.path.expanduser("~/pve-vm-create.log"),
                        help="Log file path (default: ~/pve-vm-create.log)")
    parser.add_argument("--sites-csv", dest="sites_csv", default=None,
                        help="Path to sites.csv (default: auto-detect alongside script or in cwd)")
    parser.add_argument("--role-codes-csv", dest="role_codes_csv", default=None,
                        help="Path to role_codes.csv (default: auto-detect alongside script or in cwd)")
    return parser.parse_args()


def main():
    global SITES, ROLE_CODES
    args = parse_args()

    if args.sites_csv:
        SITES = _load_sites(args.sites_csv)
    if args.role_codes_csv:
        ROLE_CODES = _load_role_codes(args.role_codes_csv)

    app = CreateVMApp(args)
    app.run()


if __name__ == "__main__":
    main()
