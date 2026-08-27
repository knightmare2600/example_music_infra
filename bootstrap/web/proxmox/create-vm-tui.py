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

class Slider(Static, can_focus=True):
    """A minimal keyboard-driven slider. Value changes post a Slider.Changed message."""

    DEFAULT_CSS = """
    Slider {
        height: 1;
        border: round $primary;
        padding: 0 1;
    }
    Slider:focus {
        border: round $accent;
    }
    """

    BINDINGS = [
        Binding("left", "step(-1)", "−", show=False),
        Binding("right", "step(1)", "+", show=False),
        Binding("pageup", "step(10)", "+10", show=False),
        Binding("pagedown", "step(-10)", "−10", show=False),
        Binding("home", "to_min", "min", show=False),
        Binding("end", "to_max", "max", show=False),
    ]

    value: reactive[int] = reactive(0)

    class Changed(Message):
        def __init__(self, slider: "Slider", value: int) -> None:
            self.slider = slider
            self.value = value
            super().__init__()

    def __init__(self, min_value, max_value, value=None, step=1, suffix="", label="", id=None):
        # markup=False -- the rendered bar contains literal '[' ']' characters
        # (the bracket-and-block-glyph bar itself), which Textual's Static
        # otherwise parses as Rich console markup and fails on. Found via
        # the headless run_test() smoke test, not assumed safe.
        super().__init__(markup=False, id=id)
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.suffix = suffix
        self.label = label
        self.value = self._clamp(value if value is not None else min_value)

    def _clamp(self, value: int) -> int:
        return max(self.min_value, min(self.max_value, value))

    def watch_value(self, value: int) -> None:
        # Render only -- does NOT reassign self.value here. Reactive
        # watchers re-firing on their own attribute's assignment is exactly
        # the kind of recursive-update bug worth avoiding; every entry
        # point that changes value (constructor, action_step, to_min/max)
        # clamps via _clamp() before assigning instead.
        width = 20
        span = max(1, self.max_value - self.min_value)
        filled = int(width * (value - self.min_value) / span)
        bar = "█" * filled + "░" * (width - filled)
        prefix = f"{self.label}: " if self.label else ""
        self.update(f"{prefix}{bar} {value}{self.suffix}")
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

    def on_mount(self) -> None:
        self.watch_value(self.value)


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
        width: 60;
        height: auto;
        border: thick $primary;
        padding: 1 2;
        background: $surface;
    }
    #login-error {
        color: $error;
        height: auto;
        min-height: 1;
    }
    """

    def __init__(self, args):
        super().__init__()
        self._args = args

    def compose(self) -> ComposeResult:
        with Vertical(id="login-box"):
            yield Label("Proxmox VE — Connect")
            yield Label("Host / IP")
            yield Input(value=self._args.host or "", placeholder="192.168.139.5", id="host")
            yield Label("Port")
            yield Input(value=str(self._args.port), placeholder="8006", id="port")
            yield Label("Username (e.g. root@pam)")
            yield Input(value=self._args.user or "root@pam", id="user")
            yield Label("Auth method")
            with RadioSet(id="auth-method"):
                yield RadioButton("Password", value=True, id="auth-password")
                yield RadioButton("API Token", id="auth-token")
            yield Label("Password", id="password-label")
            yield Input(password=True, id="password")
            yield Label("Token name", id="token-name-label")
            yield Input(id="token-name", disabled=True)
            yield Label("Token value", id="token-value-label")
            yield Input(password=True, id="token-value", disabled=True)
            yield Static("", id="login-error")
            with Horizontal():
                yield Button("Connect", variant="primary", id="connect")
                yield Button("Quit", id="quit")

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
        width: 50; height: auto; border: thick $primary;
        padding: 1 2; background: $surface;
    }
    """

    def __init__(self, nodes):
        super().__init__()
        self._pve_nodes = nodes

    def compose(self) -> ComposeResult:
        with Vertical(id="node-box"):
            yield Label("Select Proxmox node")
            with RadioSet(id="node-choice"):
                for i, n in enumerate(self._pve_nodes):
                    status = n.get("status", "?")
                    yield RadioButton(f"{n['node']}  ({status})", value=(i == 0))
            yield Button("Continue", variant="primary", id="continue")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        radio_set = self.query_one("#node-choice", RadioSet)
        idx = radio_set.pressed_index if radio_set.pressed_index is not None else 0
        self.dismiss(self._pve_nodes[idx]["node"])


# =============================================================================
# MAIN VM FORM SCREEN
# =============================================================================

class VMFormScreen(Screen):
    """One scrollable form covering identity/OS/hardware/storage/ISO/console/
    network/BIOS/pool — grouped into bordered sections mirroring v1's own
    section() groupings. Reused across bulk-mode VMs: subsequent VMs get
    this same screen re-populated from the previous VM's settings, with
    only Name/VMID freshly suggested."""

    DEFAULT_CSS = """
    .section {
        border: round $primary;
        margin: 1 0;
        padding: 1 2;
    }
    .section-title {
        text-style: bold;
        color: $accent;
    }
    .field-row {
        height: auto;
        margin-bottom: 1;
    }
    #summary-log {
        height: 12;
        border: round $secondary;
    }
    """

    BINDINGS = [Binding("ctrl+c", "quit", "Quit")]

    def __init__(self, proxmox, node, node_arch, args, bulk_total=1, bulk_index=1,
                 template_cfg=None, template_role=None, template_site=None,
                 batch_names=None, batch_ids=None):
        super().__init__()
        self.proxmox = proxmox
        self.node = node
        self.node_arch = node_arch
        self.args = args
        self.bulk_total = bulk_total
        self.bulk_index = bulk_index
        self.template_cfg = template_cfg  # previous VM's cfg dict, for bulk pre-population
        self.template_role = template_role
        self.template_site = template_site
        # Carried forward across the whole bulk batch, not just this screen —
        # see _create_current_vm()/_after_create() for how each new VM adds
        # to these before the next screen is pushed.
        self._inherited_batch_names = batch_names or set()
        self._inherited_batch_ids = batch_ids or set()

        # Local session-wide dupe tracking -- combined with live server state
        # so two not-yet-created siblings in the same bulk batch can't
        # collide with each other either. Seeded from every prior VM in this
        # batch (passed down from the previous screen), not just this one.
        self.batch_names = set(self._inherited_batch_names)
        self.batch_ids = set(self._inherited_batch_ids)

        self.existing_vms = {}
        self.existing_ids = set()
        self.existing_names = set()

        self.storage_options = []   # list of (name, type) tuples
        self.iso_options = []       # list of volid strings
        self.pool_options = []      # list of poolid strings
        self.driver_disk_options = []
        self.virtio_iso_options = []
        self.selected_storage_type = None
        self.selected_role = None
        self.selected_site = None
        self.disk_sliders = []      # list of Slider widgets, rebuilt on disk-count change
        self._last_auto_name = None  # tracks the last auto-suggested Name, so role/site
        self._last_auto_vmid = None  # changes keep re-suggesting until the user types their own

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with VerticalScroll(id="form-scroll"):
            yield Static(f"VM {self.bulk_index} of {self.bulk_total}", id="bulk-indicator")

            with Vertical(classes="section"):
                yield Label("IDENTITY", classes="section-title")
                yield Label("Role")
                yield Select(
                    [(f"{code} — {ROLE_CODES[code]}", code) for code in sorted(ROLE_CODES)],
                    id="role", allow_blank=False,
                )
                yield Label("Site")
                yield Select(
                    [(f"{code} — {SITES[code]['city']}, {SITES[code]['country']}", code)
                     for code in sorted(SITES)],
                    id="site", allow_blank=False,
                )
                yield Label("VM Name")
                yield Input(id="name")
                yield Label("VM ID")
                yield Input(id="vmid", validators=[VMIDValidator(self._all_taken_ids)],
                            validate_on=["changed"])
                yield Static("", id="identity-error")

            with Vertical(classes="section"):
                yield Label("OPERATING SYSTEM", classes="section-title")
                yield Select(
                    [(desc, ostype) for ostype, desc in OS_TYPES.items()],
                    id="ostype", value="l26", allow_blank=False,
                )

            with Vertical(classes="section"):
                yield Label("HARDWARE", classes="section-title")
                yield Label("CPU sockets")
                yield Input(value="1", id="sockets", type="integer")
                yield Label("Cores per socket")
                yield Input(value="2", id="cores", type="integer")
                yield Slider(256, 131072, value=2048, step=256, suffix="MB", label="RAM", id="ram")
                yield Label("Number of disks")
                yield Input(value="1", id="disk-count", type="integer")
                yield Checkbox("Same size for all disks", value=True, id="same-disk-size")
                yield Vertical(id="disk-sliders")
                yield Label("BMC / IPMI emulation")
                with RadioSet(id="bmc-type"):
                    yield RadioButton("None", value=True, id="bmc-none")
                    yield RadioButton("KCS interface", id="bmc-kcs")
                    yield RadioButton("BT interface", id="bmc-bt")

            with Vertical(classes="section"):
                yield Label("STORAGE", classes="section-title")
                yield Select([("Loading...", "")], id="storage", allow_blank=False)

            with Vertical(classes="section"):
                yield Label("iPXE ISO", classes="section-title")
                yield SelectionList(id="iso-list")

            with Vertical(classes="section"):
                yield Label("CONSOLE", classes="section-title")
                with RadioSet(id="console"):
                    yield RadioButton("VGA only", id="console-vga")
                    yield RadioButton("VGA + Serial", id="console-both")
                    yield RadioButton("Serial only", id="console-serial")
                    yield RadioButton("SPICE", value=True, id="console-spice")

            with Vertical(classes="section"):
                yield Label("NETWORK", classes="section-title")
                yield Label("Number of NICs")
                yield Input(value="1", id="nic-count", type="integer")
                yield Vertical(id="nic-rows")

            with Vertical(classes="section"):
                yield Label("BIOS", classes="section-title")
                with RadioSet(id="bios-type"):
                    yield RadioButton("SeaBIOS", value=True, id="bios-seabios")
                    yield RadioButton("UEFI", id="bios-uefi")
                yield Label("ROM variant (x86_64 only)", id="rom-label")
                yield Select([("Default (no custom ROM)", "")], id="bios-rom", allow_blank=False)

            with Vertical(classes="section"):
                yield Label("POOL", classes="section-title")
                yield Select([("(none)", "")], id="pool", allow_blank=False)

            with Vertical(classes="section", id="windows-section"):
                yield Label("WINDOWS EXTRAS (driver disk / VirtIO ISO)", classes="section-title")
                yield Label("VirtIO driver disk (scsi1)")
                yield Select([("(none)", "")], id="driver-disk", allow_blank=False)
                yield Label("VirtIO drivers ISO (ide2/ide3, optional)")
                yield Select([("(none — postOOBE.cmd handles it)", "")], id="virtio-iso", allow_blank=False)

            with Vertical(classes="section"):
                yield Label("BULK MODE", classes="section-title")
                yield Label("Number of VMs to create (this one counts as #1)")
                yield Input(value=str(self.bulk_total), id="bulk-count", type="integer")

            yield RichLog(id="summary-log", markup=True)

            with Horizontal():
                yield Button("Create VM", variant="primary", id="create")
                yield Button("Quit", id="quit")
        yield Footer()

    # ------------------------------------------------------------------
    # Mount / live data loading
    # ------------------------------------------------------------------

    async def on_mount(self) -> None:
        self._log(f"Connected — node: {self.node} ({self.node_arch})", "info")
        self._load_existing_vms()
        self._load_live_options()
        # Role/site must be set BEFORE the first _on_role_or_site_changed()
        # call for a bulk-mode VM -- that method only fills Name/VMID when
        # they're still blank, so if it ran once against the default
        # role/site first, the (wrong) suggestion would already be set and
        # never get corrected once the template's real role/site landed.
        # Setting .value here queues its own on_select_changed (fires later,
        # asynchronously, via Textual's message pump) -- harmless now that
        # the rebuild methods below are properly awaited/idempotent, just a
        # possible extra redundant run, not a crash risk like before.
        if self.template_role:
            self.query_one("#role", Select).value = self.template_role
        if self.template_site:
            self.query_one("#site", Select).value = self.template_site
        # _on_role_or_site_changed() already awaits _rebuild_nic_rows()
        # internally -- do not also call it directly here (that duplicate
        # call, racing an un-awaited remove_children(), was the original
        # DuplicateIds crash the run_test() smoke test caught).
        await self._on_role_or_site_changed()
        await self._rebuild_disk_sliders()
        self._update_windows_section_visibility()
        self._update_bios_rom_visibility()
        if self.template_cfg:
            await self._apply_template(self.template_cfg)

    def _log(self, message: str, level: str = "info") -> None:
        colours = {"ok": "green", "warn": "yellow", "error": "red", "step": "cyan", "info": "white"}
        colour = colours.get(level, "white")
        self.query_one("#summary-log", RichLog).write(f"[{colour}]{message}[/{colour}]")

    def _all_taken_ids(self):
        return self.existing_ids | self.batch_ids

    def _all_taken_names(self):
        return self.existing_names | self.batch_names

    def _load_existing_vms(self) -> None:
        self.existing_vms = get_existing_vms(self.proxmox, self.node)
        self.existing_ids = set(self.existing_vms.keys())
        self.existing_names = set(self.existing_vms.values())

    @work(thread=True)
    def _load_live_options(self) -> None:
        try:
            stores = self.proxmox.nodes(self.node).storage.get(content="images")
            storage_opts = [(s["storage"], s.get("type", "?")) for s in sorted(stores, key=lambda s: s["storage"])]
        except Exception:
            storage_opts = []

        try:
            isos = self.proxmox.nodes(self.node).storage("local").content.get(content="iso")
            iso_opts = sorted((i.get("volid", "") for i in isos), key=str)
        except Exception:
            iso_opts = []

        try:
            pools = self.proxmox.pools.get()
            pool_opts = sorted(p["poolid"] for p in pools)
        except Exception:
            pool_opts = []

        driver_disk_opts = []
        virtio_iso_opts = []
        try:
            stores = self.proxmox.nodes(self.node).storage.get(content="iso")
            for store in stores:
                try:
                    items = self.proxmox.nodes(self.node).storage(store["storage"]).content.get(content="iso")
                    for item in items:
                        volid = item.get("volid", "")
                        if volid.lower().endswith(".img"):
                            driver_disk_opts.append(volid)
                        elif volid.lower().endswith(".iso"):
                            virtio_iso_opts.append(volid)
                except Exception:
                    pass
        except Exception:
            pass

        self.app.call_from_thread(
            self._on_live_options_loaded, storage_opts, iso_opts, pool_opts,
            driver_disk_opts, virtio_iso_opts,
        )

    def _on_live_options_loaded(self, storage_opts, iso_opts, pool_opts, driver_disk_opts, virtio_iso_opts) -> None:
        self.storage_options = storage_opts
        self.iso_options = iso_opts
        self.pool_options = pool_opts
        self.driver_disk_options = driver_disk_opts
        self.virtio_iso_options = virtio_iso_opts

        storage_select = self.query_one("#storage", Select)
        if storage_opts:
            storage_select.set_options([(f"{name} ({stype})", name) for name, stype in storage_opts])
            self.selected_storage_type = storage_opts[0][1]
        else:
            storage_select.set_options([("No image-capable storage found", "")])
            self._log("No image-capable storage found on this node.", "warn")

        iso_list = self.query_one("#iso-list", SelectionList)
        iso_list.clear_options()
        for volid in iso_opts:
            name = volid.split("/")[-1] if "/" in volid else volid
            iso_list.add_option(Selection(name, volid, False))

        pool_select = self.query_one("#pool", Select)
        pool_select.set_options([("(none)", "")] + [(p, p) for p in pool_opts])

        driver_select = self.query_one("#driver-disk", Select)
        driver_select.set_options(
            [("(none)", "")] + [(v.split("/")[-1], v) for v in driver_disk_opts]
        )
        virtio_select = self.query_one("#virtio-iso", Select)
        virtio_select.set_options(
            [("(none — postOOBE.cmd handles it)", "")] + [(v.split("/")[-1], v) for v in virtio_iso_opts]
        )

        self._log(f"Loaded {len(storage_opts)} storage, {len(iso_opts)} ISO(s), "
                   f"{len(pool_opts)} pool(s).", "ok")

    # ------------------------------------------------------------------
    # Identity: role/site drive name+vmid suggestions; console default
    # ------------------------------------------------------------------

    async def _on_role_or_site_changed(self) -> None:
        role_select = self.query_one("#role", Select)
        site_select = self.query_one("#site", Select)
        role = role_select.value if role_select.value != Select.BLANK else sorted(ROLE_CODES)[0]
        site = site_select.value if site_select.value != Select.BLANK else sorted(SITES)[0]
        self.selected_role = role
        self.selected_site = site

        # Re-suggest whenever the field is still blank OR still holds exactly
        # what was last auto-suggested -- i.e. keep tracking role/site as
        # long as the user hasn't actually typed something of their own.
        # Found via the headless smoke test: a plain "if not value" guard
        # (matching v1's one-shot CLI prompt) left a stale name/VMID in
        # place after a *second* role/site change, since v1 never has this
        # problem in the first place -- its prompts are strictly sequential,
        # role and site are always already locked in before name is asked.
        suggested_suffix = next_free_name_suffix(self._all_taken_names(), role, site)
        suggested_name = f"EXA{role}{site}{suggested_suffix}"
        name_input = self.query_one("#name", Input)
        name_input.validators = [VMNameValidator(self._all_taken_names)]
        name_input.validate_on = ["changed"]
        if name_input.value in ("", self._last_auto_name):
            name_input.value = suggested_name
            self._last_auto_name = suggested_name

        vmid_input = self.query_one("#vmid", Input)
        if vmid_input.value in ("", self._last_auto_vmid):
            suggested_vmid = str(next_free_vmid(self._all_taken_ids()))
            vmid_input.value = suggested_vmid
            self._last_auto_vmid = suggested_vmid

        # Console default follows role, same as v1's select_console()
        console_set = self.query_one("#console", RadioSet)
        if role in SERIAL_CONSOLE_ROLES:
            console_set.query_one("#console-both", RadioButton).value = True
        else:
            console_set.query_one("#console-spice", RadioButton).value = True

        # NIC/BMC defaults follow role family, same as v1's prompt_hardware()/configure_network()
        nic_count_input = self.query_one("#nic-count", Input)
        nic_count_input.value = "2" if role in DUAL_NIC_ROLES else "1"
        await self._rebuild_nic_rows()

        self._update_windows_section_visibility()

    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id in ("role", "site"):
            await self._on_role_or_site_changed()
        elif event.select.id == "storage":
            for name, stype in self.storage_options:
                if name == event.value:
                    self.selected_storage_type = stype
                    break

    def _update_windows_section_visibility(self) -> None:
        is_windows_role = self.selected_role in WINDOWS_ROLES
        self.query_one("#windows-section", Vertical).display = is_windows_role

    # ------------------------------------------------------------------
    # Disks: count + "same size" checkbox drive how many sliders show
    # ------------------------------------------------------------------

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "disk-count":
            await self._rebuild_disk_sliders()
        elif event.input.id == "nic-count":
            await self._rebuild_nic_rows()

    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "same-disk-size":
            await self._rebuild_disk_sliders()

    def _disk_count(self) -> int:
        raw = self.query_one("#disk-count", Input).value
        try:
            n = int(raw)
        except ValueError:
            n = 1
        return max(1, min(8, n))

    async def _rebuild_disk_sliders(self) -> None:
        # async + awaited removal/mount throughout -- Widget.remove_children()/
        # mount() both return awaitables rather than completing synchronously.
        # Found live via the headless run_test() smoke test: calling this
        # (and _rebuild_nic_rows) back-to-back as plain sync calls raced the
        # removal, so the second rebuild tried to mount widgets with IDs the
        # first rebuild's removal hadn't actually finished clearing yet --
        # DuplicateIds crash. Every caller awaits this now, not fire-and-forget.
        container = self.query_one("#disk-sliders", Vertical)
        old_values = [s.value for s in self.disk_sliders]
        await container.remove_children()
        self.disk_sliders = []

        n = self._disk_count()
        same_size = self.query_one("#same-disk-size", Checkbox).value

        if same_size:
            default = old_values[0] if old_values else 32
            slider = Slider(1, 8192, value=default, suffix="GB", label="Disk size (all disks)", id="disk-size-0")
            self.disk_sliders.append(slider)
            await container.mount(slider)
        else:
            for i in range(n):
                default = old_values[i] if i < len(old_values) else (old_values[0] if old_values else 32)
                slider = Slider(1, 8192, value=default, suffix="GB", label=f"Disk {i + 1} size", id=f"disk-size-{i}")
                self.disk_sliders.append(slider)
                await container.mount(slider)

    def _disk_sizes(self) -> list:
        same_size = self.query_one("#same-disk-size", Checkbox).value
        n = self._disk_count()
        if same_size:
            size = self.disk_sliders[0].value if self.disk_sliders else 32
            return [size] * n
        return [s.value for s in self.disk_sliders]

    # ------------------------------------------------------------------
    # NICs: dynamically-built rows, same defaulting logic as v1's
    # configure_network()/_prompt_nic() (VRK native/untagged special case,
    # dual-NIC WAN+LAN layout, CLD-VLAN fallback, vmbr0 auto-untag).
    # ------------------------------------------------------------------

    def _nic_defaults(self, idx: int, role: str, site: str):
        cld_vlan = SITES["CLD"]["octet"]
        vrk_octet = SITES["VRK"]["octet"]
        if site == "VRK":
            return "vmbr0", "", "vRACK (native, untagged)"
        site_data = SITES[site]
        vlan_id = site_data["octet"]
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

        raw = self.query_one("#nic-count", Input).value
        try:
            n = max(1, min(10, int(raw)))
        except ValueError:
            n = 1

        role = self.selected_role or sorted(ROLE_CODES)[0]
        site = self.selected_site or sorted(SITES)[0]

        for i in range(n):
            bridge, vlan, desc = self._nic_defaults(i, role, site)
            row = Horizontal(classes="field-row", id=f"nic-row-{i}")
            await container.mount(row)
            await row.mount(
                Label(f"net{i}:"),
                Input(value=bridge, id=f"nic-bridge-{i}", placeholder="vmbrN"),
                Input(value=vlan, id=f"nic-vlan-{i}", placeholder="VLAN (blank=untagged)"),
                Input(value=desc, id=f"nic-desc-{i}", placeholder="description"),
                Input(id=f"nic-mac-{i}", placeholder="MAC (blank=auto)"),
            )

    def _gather_nics(self) -> list:
        cld_vlan = SITES["CLD"]["octet"]
        vrk_octet = SITES["VRK"]["octet"]
        raw = self.query_one("#nic-count", Input).value
        try:
            n = max(1, min(10, int(raw)))
        except ValueError:
            n = 1
        nics = []
        for i in range(n):
            bridge = self.query_one(f"#nic-bridge-{i}", Input).value.strip() or "vmbr1"
            vlan_raw = self.query_one(f"#nic-vlan-{i}", Input).value.strip()
            desc = self.query_one(f"#nic-desc-{i}", Input).value.strip()
            mac = self.query_one(f"#nic-mac-{i}", Input).value.strip() or None
            vlan = int(vlan_raw) if vlan_raw.isdigit() else None
            # vmbr0 provisioning-bridge special case -- same collapse-to-untagged
            # rule as v1's _prompt_nic() (an access port, tagging it double-tags frames)
            if bridge == "vmbr0" and vlan in (cld_vlan, vrk_octet, None):
                vlan = None
            if mac and not re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", mac):
                mac = None
            nics.append({"id": f"net{i}", "model": "virtio", "bridge": bridge,
                         "vlan": vlan, "mac": mac, "desc": desc})
        return nics

    # ------------------------------------------------------------------
    # BIOS: two-level -- SeaBIOS/UEFI radio, then a filtered ROM list.
    # arm64 keeps v1's simpler seabios/ovmf-only choice, no ROM file.
    # ------------------------------------------------------------------

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "bios-type":
            self._update_bios_rom_visibility()

    def _update_bios_rom_visibility(self) -> None:
        rom_label = self.query_one("#rom-label", Label)
        rom_select = self.query_one("#bios-rom", Select)

        if self.node_arch == "arm64":
            rom_label.display = False
            rom_select.display = False
            return

        rom_label.display = True
        rom_select.display = True
        is_efi = self.query_one("#bios-uefi", RadioButton).value
        matching = [r for r in KNOWN_ROMS if ("EFI" in r.upper()) == is_efi]
        rom_select.set_options(
            [("Default (no custom ROM)", "")]
            + [(f"{r} — {_describe_rom(r)}", f"/usr/share/kvm/{r}") for r in matching]
        )

    # ------------------------------------------------------------------
    # Create / bulk flow
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
        elif event.button.id == "create":
            self._create_current_vm()

    def _collect_hw(self) -> dict:
        def _int(id_, default):
            try:
                return int(self.query_one(f"#{id_}", Input).value)
            except (ValueError, LookupError):
                return default

        sockets = _int("sockets", 1)
        cores = _int("cores", 2)
        ram = self.query_one("#ram", Slider).value
        disk_count = self._disk_count()
        disk_sizes = self._disk_sizes()

        bmc_type = None
        if self.query_one("#bmc-kcs", RadioButton).value:
            bmc_type = "kcs"
        elif self.query_one("#bmc-bt", RadioButton).value:
            bmc_type = "bt"

        return {
            "sockets": sockets, "cores": cores, "ram": ram,
            "disk": disk_sizes[0] if disk_sizes else 32,
            "disk_sizes": disk_sizes, "disk_count": disk_count,
            "bmc_type": bmc_type,
        }

    def _collect_console(self) -> str:
        if self.query_one("#console-serial", RadioButton).value:
            return "serial"
        if self.query_one("#console-both", RadioButton).value:
            return "both"
        if self.query_one("#console-spice", RadioButton).value:
            return "spice"
        return "vga"

    def _collect_bios(self):
        is_efi = self.query_one("#bios-uefi", RadioButton).value
        bios_type = "ovmf" if is_efi else "seabios"
        if self.node_arch == "arm64":
            return bios_type, None
        rom_select = self.query_one("#bios-rom", Select)
        rom_path = rom_select.value if rom_select.value not in (Select.BLANK, "") else None
        return bios_type, rom_path

    def on_selection_list_selection_toggled(self, event: SelectionList.SelectionToggled) -> None:
        # The ISO list is single-select in spirit ("attach one, or none") even
        # though SelectionList itself is a multi-select widget -- ticking a
        # new entry un-ticks whatever was previously ticked, so "add it,
        # remove it" behaves like a real single choice rather than silently
        # keeping only the first-by-list-order item if two ended up checked.
        if event.selection_list.id != "iso-list":
            return
        iso_list = event.selection_list
        if event.selection.value in iso_list.selected:
            for volid in list(iso_list.selected):
                if volid != event.selection.value:
                    iso_list.deselect(volid)

    def _selected_iso(self):
        iso_list = self.query_one("#iso-list", SelectionList)
        selected = iso_list.selected
        return selected[0] if selected else None

    def _create_current_vm(self) -> None:
        name_input = self.query_one("#name", Input)
        vmid_input = self.query_one("#vmid", Input)

        if not name_input.is_valid or not vmid_input.is_valid:
            self._log("Fix the Name/VM ID errors above before creating.", "error")
            return

        vm_name = name_input.value.upper()
        vmid = int(vmid_input.value)
        role = self.selected_role
        site = self.selected_site

        ostype = self.query_one("#ostype", Select).value
        hw = self._collect_hw()
        console = self._collect_console()
        bios_type, bios_rom = self._collect_bios()
        nics = self._gather_nics()

        storage_select = self.query_one("#storage", Select)
        storage = storage_select.value if storage_select.value not in (Select.BLANK, "") else None
        if not storage:
            self._log("Select a storage pool before creating.", "error")
            return

        pool_select = self.query_one("#pool", Select)
        pool = pool_select.value or None

        driver_disk = None
        virtio_iso = None
        if role in WINDOWS_ROLES:
            dd = self.query_one("#driver-disk", Select).value
            driver_disk = dd or None
            vi = self.query_one("#virtio-iso", Select).value
            virtio_iso = vi or None

        machine = "virt" if self.node_arch == "arm64" else None
        ipxe_iso = self._selected_iso()

        cfg = build_vm_config(
            vmid=vmid, name=vm_name, role=role, site=site, hw=hw,
            storage=storage, console=console, nics=nics, ostype=ostype,
            ipxe_iso=ipxe_iso, pool=pool, driver_disk=driver_disk,
            virtio_iso=virtio_iso, bios_type=bios_type, bios_rom=bios_rom,
            storage_type=self.selected_storage_type, machine=machine,
        )

        self.batch_names.add(vm_name)
        self.batch_ids.add(vmid)

        self._log(f"Submitting {vm_name} (VMID {vmid})...", "step")
        self._run_create(cfg)

    @work(thread=True, exclusive=True)
    def _run_create(self, cfg: dict) -> None:
        def log_fn(msg, level):
            self.app.call_from_thread(self._log, msg, level)

        success = create_vm(self.proxmox, self.node, cfg, log_fn, dry_run=self.args.dry_run)
        if success:
            write_log(self.args.log, cfg, self.node, dry_run=self.args.dry_run)
        self.app.call_from_thread(self._after_create, success, cfg)

    def _after_create(self, success: bool, cfg: dict) -> None:
        if not success:
            self._log("VM creation failed — see log above. Fix and try again.", "error")
            return

        self._log(f"VM {cfg['vmid']} ({cfg['name']}) done ({self.bulk_index}/{self.bulk_total}).", "ok")

        try:
            bulk_total = max(1, int(self.query_one("#bulk-count", Input).value))
        except ValueError:
            bulk_total = self.bulk_total

        if self.bulk_index >= bulk_total:
            self._log("Bulk session complete.", "ok")
            return

        # Next VM in the batch: same screen, re-populated from this cfg,
        # only Name/VMID freshly suggested (and still independently
        # editable/validated) -- see plan's "clone and repopulate" design.
        # role/site and the running batch dupe-set are threaded through
        # explicitly -- build_vm_config()'s cfg dict doesn't carry role/site
        # at all (matches v1's shape, which never needed to), so they can't
        # be recovered from cfg alone.
        self.app.push_screen(
            VMFormScreen(
                self.proxmox, self.node, self.node_arch, self.args,
                bulk_total=bulk_total, bulk_index=self.bulk_index + 1,
                template_cfg=cfg, template_role=self.selected_role,
                template_site=self.selected_site,
                batch_names=self.batch_names, batch_ids=self.batch_ids,
            )
        )

    async def _apply_template(self, cfg: dict) -> None:
        """Pre-populate this (new VM #N) screen from the previous VM's cfg.
        Name/VMID are deliberately NOT copied -- they're freshly suggested
        by _on_role_or_site_changed() instead, and stay independently
        editable/validated. Role/site are already set by on_mount() before
        this runs, not here -- see that method's own comment for why the
        ordering matters."""
        self.query_one("#ostype", Select).value = cfg["ostype"]
        self.query_one("#sockets", Input).value = str(cfg["sockets"])
        self.query_one("#cores", Input).value = str(cfg["cores"])
        self.query_one("#ram", Slider).value = cfg["memory"]
        self.query_one("#disk-count", Input).value = str(cfg.get("disk_count", 1))
        await self._rebuild_disk_sliders()
        for i, size in enumerate(cfg.get("disk_sizes") or [cfg["disk_gb"]]):
            if i < len(self.disk_sliders):
                self.disk_sliders[i].value = size
        console_ids = {"vga": "console-vga", "both": "console-both",
                        "serial": "console-serial", "spice": "console-spice"}
        self.query_one(f"#{console_ids.get(cfg['console'], 'console-spice')}", RadioButton).value = True
        if cfg.get("bios") == "ovmf":
            self.query_one("#bios-uefi", RadioButton).value = True
        self._update_bios_rom_visibility()
        if cfg.get("pool"):
            self.query_one("#pool", Select).value = cfg["pool"]
        self._log(f"Pre-populated from {cfg['name']} — set a new Name/VM ID for this one.", "info")


# =============================================================================
# APP — ties LoginModal -> (NodeModal if >1 node) -> VMFormScreen together.
# =============================================================================

class CreateVMApp(App):
    TITLE = "Proxmox VE — VM Creation (jukebox.internal)"
    BINDINGS = [Binding("ctrl+c", "quit", "Quit")]

    def __init__(self, args):
        super().__init__()
        self.args = args

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
        self.call_from_thread(self._start_form, proxmox, node, arch)

    def _start_form(self, proxmox, node, arch) -> None:
        self.push_screen(VMFormScreen(proxmox, node, arch, self.args))


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
