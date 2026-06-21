#!/usr/bin/env python3
"""
create-vm.py — Proxmox VE VM Creation Script
Example Music Limited — Internal Infrastructure

Creates VMs on a Proxmox node following the EXA[ROLE][SITE][NNN] naming
convention. Supports API token or username/password authentication.

Changelog:
    2026-03-01  Initial script — VM creation, role/site validation, hardware defaults, storage/ISO selection, NIC config,
                serial/VGA console, boot order, dry run, logging
    2026-03-03  BRD renamed to BER, TOR added (192.168.146.0/24)
    2026-03-03  Role codes: added AST, DCS, FCL, IOT, LIN, MIC, MID, NAS, OBS, PAY, PVE, RAD, SYN; removed DRM/SMP
    2026-03-03  Hardware defaults: SRV/SVR & NIX split into separate profiles; PVE added with 4vCPU/8GB/120GB defaults
    2026-03-03  NIX added to serial console defaults; SRV is VGA (Windows)
    2026-03-03  CPU sockets × cores per socket with even-total validation
    2026-03-03  Pool enumeration & selection with site-code matching
    2026-03-03  qemu-guest-agent enabled by default (agent=1)
    2026-03-03  Bulk mode (--bulk) — loops VM creation, resets all variables per run, auth/node selected once per session
    2026-03-03  Graceful Ctrl+C handling
    2026-03-03  VirtIO driver disk (scsi1) auto-attached for Windows roles
    2026-03-07  OS type table corrected — w2k12/w2k16/w2k19/w2k22 don't exist as Proxmox ostype values; win10 covers Server
                2016/2019, win11 covers Win11/Server 2022/2025 per https://pve.proxmox.com/wiki/Manual:_qm.conf
    2026-03-07  Optional MAC address prompt added to configure_network() for DHCP reservation & physical node replacement
                workflows
    2026-03-07  Multi-NIC support; configure_network() now prompts for NIC count (1–10), each NIC individually prompted for
                bridge, VLAN, description & optional MAC; defaults from role
    2026-03-22  Serial console guest OS advisory added post VM creation, prints tailored steps: Linux gets GRUB+getty
                instructions, Windows gets bcdedit+EMS/SAC instructions. Only shown when serial console is in use.
    2026-03-22  BMC post-creation note updated with --address flag & VLAN binding guidance (NET-BMC-001). Port auto calc.
    2026-03-19  BMC/IPMI emulation option added; KCS or BT interface via ipmi-bmc-sim; proxmoxbmc registers each VM on a
                network port.
    2026-03-19  Custom BIOS ROM selection added; enumerates .ROM files from /usr/share/kvm/ on the Proxmox node, shows
                friendly names, applies via QEMU args: -bios flag per-VM.
    2026-03-19  sites.csv Entity column added -- shown in site selection table.
    2026-03-19  Site data moved to sites.csv (single source of truth). SITE_OCTET/SITE_CITY/SITE_COUNTRY derived from CSV
                at load time. --sites-csv <path> flag added to override default. Now shows subnet & country from CSV and
                configure_network() shows gateway, DC, & FW IPs from CSV.
    2026-03-19  SPICE console added as console option 4 (1 monitor, SPICE audio). SPICE is now the default for non-serial,
                non-appliance roles (replaces VGA-only as the standard desktop/server console). VGA-only kept as an
                explicit option for compatibility.
    2026-03-07  VirtIO ISO CDROM — Windows VMs (DCS, SRV, SVR, WKS, LAP, SUR) now prompted to select the virtio-win ISO
                via new select_virtio_iso(). ISO attached as ide2; iPXE moves to ide3 when both are present. Supports
                online driver install and offline DISM injection. print_summary() updated to show both ISO slots. In
                build_vm_config() updated to carry virtio_iso through the config dict.
    2026-05-29  select_iso() now prefers ipxe_amd64.iso over ipxe_arm64.iso when both are present.
                Two-pass auto-select: amd64 match first, any ipxe match as fallback. Proxmox has no arm64 build so (yet).
    2026-05-29  Blank VLAN input defaults to CLD (currently 139) rather than None/untagged. In this environment, blank/CLD
                are synonymous, this removes a class of bugs where prompt() would loop forever on an empty-string default
                (treated as a required field). Site-specific VLANs (ATL, FAL, BRK, NEW, etc.) still take precedence as the
                prompt default when a site VLAN is proposed; CLD is purely the fallback. The WAN port of dual-NIC roles
                (FWL/RTR) also default to CLD VLAN rather than untagged. "untagged" label removed from all display paths.
    2026-05-29  vmbr0 provisioning bridge special case: if NIC is on vmbr0 & user leaves/sets VLAN as the CLD default (or
                blank), script now correctly sets vlan=None (untagged). vmbr0 already sits on a port in 192.168.139.0/24 --
                adding VLAN tag 139 would double-tag frames & the switch could drop silently. Explicitly typed non-CLD VLAN
                on vmbr0 is unchanged. Show label: "VLAN untagged (vmbr0 provisioning)" across all three summary paths.


Usage:
    python3 create-vm.py [options]

Options:
    -h, --help              Show this help message and exit
    --host HOST             Proxmox host (e.g. 192.168.139.50 or pve.example.com)
    --port PORT             Proxmox API port (default: 8006)
    --user USER             Proxmox username (e.g. root@pam or user@pve)
    --token-name NAME       API token name (e.g. mytoken)
    --token-value VALUE     API token value
    --password PASSWORD     Password (used if no token specified)
    --node NODE             Proxmox node name (e.g. EXAPVEFAL001)
    --dry-run               Show what would be created without making any changes
    --bulk                  Loop VM creation — prompts for another after each VM (Ctrl+C to exit)
    --log FILE              Log file path (default: ~/pve-vm-create.log)

Examples:
    # Fully interactive
    python3 create-vm.py

    # Specify host and user, prompt for password
    python3 create-vm.py --host 192.168.139.50 --user root@pam

    # API token auth
    python3 create-vm.py --host 192.168.139.50 --user root@pam --token-name mytoken --token-value xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

    # Dry run
    python3 create-vm.py --host 192.168.139.50 --dry-run

    # Bulk mode — loop VM creation, Ctrl+C or decline prompt to exit
    python3 create-vm.py --host 192.168.139.50 --bulk
"""

import argparse
import datetime
import getpass
import json
import os
import sys
import re

try:
    from proxmoxer import ProxmoxAPI
except ImportError:
    print("ERROR: proxmoxer not installed.")
    print("  On Proxmox node : apt install python3-proxmoxer python3-requests")
    print("  On workstation  : pip3 install proxmoxer requests")
    sys.exit(1)

# =============================================================================
# SITE AND ROLE LOOKUP TABLES
# =============================================================================
#
# Site data is loaded from sites.csv, which must be in the same directory as
# this script. The CSV is the single source of truth for site codes, subnets,
# gateways, DC/FW IPs, timezones, and Ansible regions.
#
# To add a new site: add a row to sites.csv and re-run. No code changes needed.
#
# Expected CSV columns:
#   Site, City, Country, CountryCode, Subnet, Gateway, DC, FW,
#   Landline, Mobile, Timezone, AnsibleRegion
#
# BRD is a legacy alias for BER (West Berlin) -- same subnet, kept for v2v
# compatibility. Both are valid site codes.

import csv as _csv
import os as _os

def _load_sites(csv_path=None):
    """
    Load site data from sites.csv.
    Searches: same directory as this script, then current working directory.
    Returns dict keyed by site code.
    """
    if csv_path is None:
        # Check SITES_CSV environment variable first (set by profile.d on PVE nodes)
        env_path = _os.environ.get("SITES_CSV")
        if env_path and _os.path.isfile(env_path):
            csv_path = env_path
        else:
            script_dir = _os.path.dirname(_os.path.abspath(__file__))
            candidates = [
                _os.path.join(script_dir, "sites.csv"),
                _os.path.join(_os.getcwd(), "sites.csv"),
                "/etc/example-music/sites.csv",
            ]
            for p in candidates:
                if _os.path.isfile(p):
                    csv_path = p
                    break

    if not csv_path or not _os.path.isfile(csv_path):
        print("ERROR: sites.csv not found.")
        print("  Searched: $SITES_CSV env var, script directory, cwd,")
        print("            /etc/example-music/sites.csv")
        print("  Options:")
        print("    export SITES_CSV=/path/to/sites.csv")
        print("    place sites.csv alongside this script")
        print("    pass --sites-csv <path>  (create-vm.py / convert-v2v.py only)")
        import sys
        sys.exit(1)

    sites = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in _csv.DictReader(f):
            code = row["Site"].strip().upper()
            subnet = row["Subnet"].strip()   # e.g. 192.168.76.0/24
            octet  = int(subnet.split(".")[2]) if subnet and subnet != "N/A" else None
            sites[code] = {
                "city":           row["City"].strip(),
                "country":        row["Country"].strip(),
                "country_code":   row["CountryCode"].strip(),
                "subnet":         subnet,
                "octet":          octet,
                "gateway":        row["Gateway"].strip(),
                "dc":             row["DC"].strip(),
                "fw":             row["FW"].strip(),
                "timezone":       row["Timezone"].strip(),
                "ansible_region": row["AnsibleRegion"].strip(),
                "entity":         row.get("Entity", "Example Music Limited").strip(),
            }
    return sites

# Load once at import time -- all functions reference SITES directly
SITES = _load_sites()

# Convenience dicts kept for backward compatibility and display functions
SITE_OCTET  = {code: s["octet"]   for code, s in SITES.items() if s["octet"] is not None}
SITE_CITY   = {code: s["city"]    for code, s in SITES.items()}
SITE_COUNTRY= {code: s["country"] for code, s in SITES.items()}

ROLE_CODES = {
    "ANS": "Ansible Host",
    "AST": "Atari ST (Retro Hardware)",
    "BPS": "Badge Programming Station",
    "CAM": "Security Camera",
    "CLK": "Time Clock / Punch Clock",
    "COF": "Coffee Machine",
    "DCS": "Domain Controller",
    "DNS": "DNS Server",
    "DON": "Donut Vending Machine (Tim Hortons compatible)",
    "FCL": "Fairlight CMI Sampler",
    "FWL": "Firewall Appliance",
    "ILO": "Integrated Lights-Out (HP iLO)",
    "IOT": "IoT / Miscellaneous Embedded Device",
    "LAP": "Laptop (Windows)",
    "LCD": "LCD Wallboard / Information Display",
    "LIN": "LinnDrum Drum Machine",
    "MAC": "macOS Desktop",
    "MBP": "MacBook Pro",
    "MIC": "Microphone (IP/Dante Audio)",
    "MID": "MIDI Sequencer / Workstation",
    "MUS": "Music Workstation / Studio System / Jukebox",
    "NAS": "Network Attached Storage",
    "NIX": "Unix/Linux/Solaris System",
    "OBS": "Outside Broadcast Station",
    "PAY": "Payphone",
    "PBX": "PBX (Telephone Server)",
    "PHN": "Mobile / Desk Phone",
    "PMP": "Petrol Pump",
    "PRN": "Printer / MFD",
    "PVE": "Proxmox VE Node",
    "RAC": "Remote Access Controller (Dell iDRAC)",
    "RAD": "Radio Transmitter / Broadcast",
    "RDR": "Card Reader / Badge Reader",
    "RTR": "Router",
    "SBC": "Session Border Controller",
    "SRV": "Server (General Purpose)",
    "SUR": "Microsoft Surface Device",
    "SVR": "Server (Legacy / Non-Proxmox)",
    "SWI": "Network Switch",
    "SYN": "Synthesizer (e.g. Moog, Korg, Yamaha)",
    "TAB": "Tablet",
    "TAR": "Tape Archiver",
    "TEA": "Internet Connected Tea/Coffee Machine (RFC2324)",
    "TTY": "Teletype / Serial Terminal / VDU",
    "TVS": "Television / Digital Signage",
    "VCU": "Video Conferencing Unit",
    "VND": "Vending Machine",
    "WAP": "Wireless Access Point",
    "WKS": "Workstation (Desktop)",
}

# Roles that get serial console by default
SERIAL_CONSOLE_ROLES = {"FWL", "RTR", "SBC", "PBX", "NIX"}

# Roles that get two NICs (WAN + LAN)
DUAL_NIC_ROLES = {"FWL", "RTR"}

# Roles that get a VirtIO driver disk (scsi1) — Windows installs
WINDOWS_ROLES = {"SRV", "SVR", "WKS", "LAP"}

# OS type options — Proxmox ostype enum
# Source: https://pve.proxmox.com/wiki/Manual:_qm.conf
# Valid values: l24 | l26 | other | solaris | w2k | w2k3 | w2k8 | win7 | win8 | win10 | win11 | wvista | wxp
#
# IMPORTANT: w2k12, w2k16, w2k19, w2k22 do NOT exist as ostype values.
# Proxmox UI labels map as follows (confirmed via pve-qemu source):
#   win10  → Windows 10 / Server 2016 / Server 2019
#   win11  → Windows 11 / Server 2022 / Server 2025
# Source: https://forum.proxmox.com/threads/166525/
OS_TYPES = {
    "1":  ("l26",     "Linux 2.6+ kernel (Debian, Ubuntu, Rocky, AlmaLinux, etc.)"),
    "2":  ("l24",     "Linux 2.4 kernel (legacy)"),
    "3":  ("win11",   "Windows 11 / Server 2022 / Server 2025"),
    "4":  ("win10",   "Windows 10 / Server 2016 / Server 2019"),
    "5":  ("win8",    "Windows 8.x / Server 2012 / Server 2012 R2"),
    "6":  ("win7",    "Windows 7 / Server 2008 R2"),
    "7":  ("w2k8",    "Windows Vista / Server 2008"),
    "8":  ("wxp",     "Windows XP / Server 2003"),
    "9":  ("solaris", "Solaris / OpenSolaris / illumos"),
    "10": ("other",   "Other / Unknown / FreeBSD / OpenBSD"),
}

# =============================================================================
# COLOURS
# =============================================================================

class C:
    R  = "\033[0;31m"
    G  = "\033[0;32m"
    Y  = "\033[1;33m"
    B  = "\033[0;34m"
    M  = "\033[0;35m"
    CY = "\033[0;36m"
    W  = "\033[1;37m"
    D  = "\033[2;37m"
    NC = "\033[0m"

def ok(msg):    print(f"  {C.G}[+]{C.NC} {msg}")
def info(msg):  print(f"  {C.CY}[i]{C.NC} {msg}")
def warn(msg):  print(f"  {C.Y}[!]{C.NC} {msg}")
def err(msg):   print(f"  {C.R}[X]{C.NC} {msg}"); sys.exit(1)
def step(msg):  print(f"  {C.M}[->]{C.NC} {msg}")
def dry(msg):   print(f"  {C.B}[DRY]{C.NC} {msg}")

def section(title):
    print()
    print(f"{C.Y}  {'=' * 54}{C.NC}")
    print(f"{C.W}  {title}{C.NC}")
    print(f"{C.Y}  {'=' * 54}{C.NC}")
    print()

def confirm(prompt, default="n"):
    """Prompt for y/N confirmation. Returns True if confirmed."""
    yn = "y/N" if default == "n" else "Y/n"
    while True:
        resp = input(f"  {C.Y}{prompt} [{yn}]: {C.NC}").strip().lower()
        if resp == "":
            return default == "y"
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        print(f"  {C.R}Please enter y or n.{C.NC}")

def prompt(msg, default=None, validator=None, secret=False):
    """Generic prompt with optional default and validator."""
    suffix = f" [{default}]" if default is not None else ""
    while True:
        if secret:
            val = getpass.getpass(f"  {C.W}{msg}{suffix}: {C.NC}")
        else:
            val = input(f"  {C.W}{msg}{suffix}: {C.NC}").strip()
        if val == "" and default is not None:
            val = default
        if val == "":
            print(f"  {C.R}This field is required.{C.NC}")
            continue
        if validator:
            result = validator(val)
            if result is not True:
                print(f"  {C.R}{result}{C.NC}")
                continue
        return val

# =============================================================================
# ARGUMENT PARSING
# =============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a Proxmox VM following the EXA naming convention.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--host",         help="Proxmox host/IP")
    parser.add_argument("--port",         type=int, default=8006, help="API port (default: 8006)")
    parser.add_argument("--user",         help="Proxmox username (e.g. root@pam)")
    parser.add_argument("--token-name",   dest="token_name",  help="API token name")
    parser.add_argument("--token-value",  dest="token_value", help="API token value")
    parser.add_argument("--password",     help="Password (if not using token)")
    parser.add_argument("--node",         help="Proxmox node name")
    parser.add_argument("--dry-run",      action="store_true", dest="dry_run",
                        help="Show what would be created without making changes")
    parser.add_argument("--bulk",         action="store_true",
                        help="Loop VM creation — prompts for another VM after each one (Ctrl+C to exit)")
    parser.add_argument("--log",          default=os.path.expanduser("~/pve-vm-create.log"),
                        help="Log file path (default: ~/pve-vm-create.log)")
    parser.add_argument("--sites-csv",    dest="sites_csv", default=None,
                        help="Path to sites.csv (default: auto-detect alongside script or in cwd)")
    return parser.parse_args()

# =============================================================================
# PROXMOX CONNECTION
# =============================================================================

def connect(args):
    host = args.host or prompt("Proxmox host/IP")
    port = args.port
    user = args.user or prompt("Proxmox username (e.g. root@pam)", default="root@pam")

    # Determine auth method
    if args.token_name and args.token_value:
        auth_method = "token"
        token_name  = args.token_name
        token_value = args.token_value
    elif args.password:
        auth_method = "password"
        password    = args.password
    else:
        print()
        print(f"  {C.W}Authentication method:{C.NC}")
        print(f"  {C.CY}  1{C.NC}  API Token (recommended)")
        print(f"  {C.CY}  2{C.NC}  Username + Password")
        print()
        choice = prompt("Select", default="1", validator=lambda v: True if v in ("1","2") else "Enter 1 or 2")
        if choice == "1":
            auth_method = "token"
            token_name  = prompt("Token name")
            token_value = prompt("Token value", secret=True)
        else:
            auth_method = "password"
            password    = prompt("Password", secret=True)

    step(f"Connecting to https://{host}:{port} as {user}...")

    try:
        if auth_method == "token":
            proxmox = ProxmoxAPI(
                host, port=port, user=user,
                token_name=token_name, token_value=token_value,
                verify_ssl=False
            )
        else:
            proxmox = ProxmoxAPI(
                host, port=port, user=user,
                password=password, verify_ssl=False
            )
        # Test connection
        proxmox.version.get()
        ok(f"Connected to {host}:{port}")
        return proxmox
    except Exception as e:
        err(f"Connection failed: {e}")

# =============================================================================
# NODE SELECTION
# =============================================================================

def select_node(proxmox, args):
    nodes = proxmox.nodes.get()
    if not nodes:
        err("No nodes found on this Proxmox instance.")

    if args.node:
        names = [n["node"] for n in nodes]
        if args.node not in names:
            err(f"Node '{args.node}' not found. Available: {', '.join(names)}")
        ok(f"Node: {args.node}")
        return args.node

    if len(nodes) == 1:
        node = nodes[0]["node"]
        ok(f"Single node detected: {node}")
        return node

    print()
    print(f"  {C.W}Available nodes:{C.NC}")
    for i, n in enumerate(nodes, 1):
        status = f"{C.G}online{C.NC}" if n.get("status") == "online" else f"{C.R}{n.get('status','?')}{C.NC}"
        mem_gb = round(n.get("maxmem", 0) / 1024**3, 1)
        print(f"  {C.CY}  {i}{C.NC}  {n['node']}  ({status}, {mem_gb}GB RAM)")
    print()

    def validate_node(v):
        if v.isdigit() and 1 <= int(v) <= len(nodes):
            return True
        return f"Enter a number between 1 and {len(nodes)}"

    choice = int(prompt("Select node", validator=validate_node))
    return nodes[choice - 1]["node"]

# =============================================================================
# VM NAME / ID HANDLING
# =============================================================================

def get_existing_vms(proxmox, node):
    """Return dict of {vmid: name} for all existing VMs."""
    try:
        vms = proxmox.nodes(node).qemu.get()
        return {int(vm["vmid"]): vm.get("name", "") for vm in vms}
    except Exception:
        return {}

def next_free_vmid(existing_ids, start=1000):
    """Find the next free VMID from start upwards."""
    vmid = start
    while vmid in existing_ids:
        vmid += 1
    return vmid

def next_free_name_suffix(existing_names, role, site):
    """Find the next free NNN suffix for EXA[ROLE][SITE]NNN."""
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
    err(f"All 999 names for {prefix} are taken.")

def select_role():
    """Prompt for VM role code."""
    print()
    print(f"  {C.W}Role codes:{C.NC}")
    codes = sorted(ROLE_CODES.keys())
    # Print in 3 columns
    for i in range(0, len(codes), 3):
        row = codes[i:i+3]
        line = ""
        for code in row:
            line += f"  {C.CY}{code:4}{C.NC}  {ROLE_CODES[code]:<40}"
        print(f"  {line}")
    print()

    def validate_role(v):
        if v.upper() in ROLE_CODES:
            return True
        return f"Unknown role code. See list above."

    role = prompt("Role code (e.g. FWL, SRV, NIX)", validator=validate_role)
    return role.upper()

def select_site():
    """Prompt for site code. Lists all sites from sites.csv."""
    print()
    print(f"  {C.W}Known site codes  (from sites.csv):{C.NC}")
    print()
    print(f"  {'Code':<5}  {'City':<22}  {'Country':<16}  {'Subnet':<20}  {'Entity'}")
    print(f"  {'-'*4}  {'-'*21}  {'-'*15}  {'-'*19}  {'-'*35}")
    for code in sorted(SITES.keys()):
        s = SITES[code]
        legacy = "  [legacy]" if "legacy" in s["city"].lower() else ""
        print(f"  {C.CY}{code:<5}{C.NC}  {s['city']:<22}  {s['country']:<16}  {s['subnet']:<20}  {s['entity']}{legacy}")
    print()

    def validate_site(v):
        if v.upper() in SITES:
            return True
        return f"Unknown site code. See list above."

    site = prompt("Site code (e.g. FAL, LND, BRK)", validator=validate_site)
    site = site.upper()
    s = SITES[site]
    ok(f"Site: {site} — {s['city']}, {s['country']}  ({s['subnet']})")
    return site

# =============================================================================
# STORAGE SELECTION
# =============================================================================

def select_storage(proxmox, node):
    """Query pvesm, filter to image-capable storage, present menu."""
    try:
        stores = proxmox.nodes(node).storage.get(content="images")
    except Exception as e:
        err(f"Failed to query storage: {e}")

    if not stores:
        err("No image-capable storage found on this node.")

    # Sort by name
    stores = sorted(stores, key=lambda s: s["storage"])

    print()
    print(f"  {C.W}Available storage:{C.NC}")
    for i, s in enumerate(stores, 1):
        used_gb  = round(s.get("used",    0) / 1024**3, 1)
        avail_gb = round(s.get("avail",   0) / 1024**3, 1)
        total_gb = round(s.get("total",   0) / 1024**3, 1)
        stype    = s.get("type", "?")
        active   = f"{C.G}active{C.NC}" if s.get("active") else f"{C.R}inactive{C.NC}"
        print(f"  {C.CY}  {i}{C.NC}  {s['storage']:<20} {stype:<10} "
              f"{used_gb}GB used / {avail_gb}GB free of {total_gb}GB  [{active}]")
    print()

    def validate_storage(v):
        if v.isdigit() and 1 <= int(v) <= len(stores):
            return True
        return f"Enter a number between 1 and {len(stores)}"

    choice = int(prompt("Select storage for VM disk", validator=validate_storage))
    selected = stores[choice - 1]["storage"]
    ok(f"Storage: {selected}")
    return selected

# =============================================================================
# ISO SELECTION
# =============================================================================

def select_iso(proxmox, node, label="ISO", required=True):
    """List ISOs in local storage, return selection or None."""
    try:
        isos = proxmox.nodes(node).storage("local").content.get(content="iso")
    except Exception:
        isos = []

    if not isos:
        if required:
            warn("No ISOs found in local storage.")
        return None

    isos = sorted(isos, key=lambda x: x.get("volid",""))

    print()
    print(f"  {C.W}Available ISOs ({label}):{C.NC}")
    if not required:
        print(f"  {C.CY}  0{C.NC}  None / skip")
    for i, iso in enumerate(isos, 1):
        volid = iso.get("volid", "?")
        name  = volid.split("/")[-1] if "/" in volid else volid
        size  = round(iso.get("size", 0) / 1024**2, 1)
        print(f"  {C.CY}  {i}{C.NC}  {name}  ({size}MB)")
    print()

    max_choice = len(isos)
    min_choice = 0 if not required else 1

    def validate_iso(v):
        if v.isdigit() and min_choice <= int(v) <= max_choice:
            return True
        return f"Enter a number between {min_choice} and {max_choice}"

    # Auto-select iPXE ISO — prefer ipxe_amd64.iso explicitly (Proxmox has no arm64 build).
    # Two-pass: first look for amd64, then fall back to any ipxe match.
    default = None
    volids  = [(i, iso.get("volid", "").lower()) for i, iso in enumerate(isos, 1)]
    for i, volid in volids:
        if "ipxe" in volid and "amd64" in volid:
            default = str(i)
            info(f"ipxe_amd64 ISO detected — pre-selected as option {i}")
            break
    if default is None:
        for i, volid in volids:
            if "ipxe" in volid:
                default = str(i)
                info(f"iPXE ISO detected — pre-selected as option {i}")
                break

    choice = int(prompt(f"Select {label}", default=default, validator=validate_iso))
    if choice == 0:
        return None
    selected = isos[choice - 1]["volid"]
    ok(f"{label}: {selected.split('/')[-1]}")
    return selected

# =============================================================================
# OS TYPE SELECTION
# =============================================================================

def select_os_type():
    print()
    print(f"  {C.W}OS type:{C.NC}")
    for k, (ostype, desc) in OS_TYPES.items():
        print(f"  {C.CY}  {k:>2}{C.NC}  {desc}")
    print()

    def validate_os(v):
        if v in OS_TYPES:
            return True
        return f"Enter a number between 1 and {len(OS_TYPES)}"

    choice = prompt("Select OS type", default="1", validator=validate_os)
    ostype, desc = OS_TYPES[choice]
    ok(f"OS type: {desc} ({ostype})")
    return ostype

# =============================================================================
# HARDWARE PROMPTS
# =============================================================================

def prompt_int(msg, default, min_val, max_val):
    def validate(v):
        if not v.isdigit():
            return "Enter a whole number."
        if not (min_val <= int(v) <= max_val):
            return f"Enter a value between {min_val} and {max_val}."
        return True
    val = prompt(msg, default=str(default), validator=validate)
    return int(val)

def prompt_hardware(role):
    """Prompt for CPU sockets, cores per socket, RAM, disk size. Returns dict."""
    section("HARDWARE CONFIGURATION")

    # Sensible defaults by role family
    if role in ("FWL", "RTR", "SBC", "PBX"):
        default_sockets = 1
        default_cores   = 2
        default_ram     = 2048
        default_disk    = 20
    elif role in ("PVE",):
        default_sockets = 1
        default_cores   = 4
        default_ram     = 8192
        default_disk    = 120
    elif role in ("SRV", "SVR"):
        # Windows servers — generous RAM, larger disk for OS + roles
        default_sockets = 1
        default_cores   = 4
        default_ram     = 8192
        default_disk    = 80
    elif role in ("NIX",):
        # Unix/Linux/Solaris — typically leaner, serial console default
        default_sockets = 1
        default_cores   = 2
        default_ram     = 2048
        default_disk    = 40
    elif role in ("WKS", "LAP", "MBP", "MAC", "SUR"):
        default_sockets = 1
        default_cores   = 2
        default_ram     = 4096
        default_disk    = 80
    else:
        default_sockets = 1
        default_cores   = 2
        default_ram     = 2048
        default_disk    = 32

    sockets = prompt_int("CPU sockets",     default=default_sockets, min_val=1, max_val=4)

    def validate_cores(v):
        if not v.isdigit():
            return "Enter a whole number."
        v = int(v)
        if v < 1:
            return "Must be at least 1"
        if v > 128:
            return "Unlikely to need more than 128 cores per socket"
        total = v * sockets
        if total > 1 and total % 2 != 0:
            return f"Total vCPUs ({v} × {sockets} = {total}) must be even"
        return True

    cores   = int(prompt("Cores per socket", default=str(default_cores), validator=validate_cores))
    ram     = prompt_int("RAM (MB)",         default=default_ram,     min_val=256, max_val=1048576)
    disk    = prompt_int("Disk size (GB)",   default=default_disk,    min_val=1,   max_val=65536)

    total_vcpus = sockets * cores
    ok(f"CPU: {sockets} socket(s) × {cores} core(s) = {total_vcpus} vCPU(s)  |  RAM: {ram}MB  |  Disk: {disk}GB")

    # ── BMC / IPMI emulation ──────────────────────────────────────────────────
    print()
    print(f"  {C.W}BMC / IPMI emulation:{C.NC}")
    print(f"  {C.D}Adds a simulated IPMI BMC device to the VM (ipmi-bmc-sim).{C.NC}")
    print(f"  {C.D}Requires proxmoxbmc on the Proxmox node for network IPMI access.{C.NC}")
    print(f"  {C.D}Gives the guest OS /dev/ipmi0 and enables SOL serial console.{C.NC}")
    print()
    print(f"  {C.CY}  1{C.NC}  No BMC emulation (default)")
    print(f"  {C.CY}  2{C.NC}  KCS interface  (keyboard controller style -- most compatible, use for Linux guests)")
    print(f"  {C.CY}  3{C.NC}  BT interface   (block transfer -- slightly faster, also well supported)")
    print()
    bmc_choice = prompt("BMC emulation", default="1",
                        validator=lambda v: True if v in ("1","2","3") else "Enter 1, 2 or 3")
    if bmc_choice == "2":
        bmc_type = "kcs"
        ok("BMC: KCS IPMI interface -- install proxmoxbmc on node for network access")
    elif bmc_choice == "3":
        bmc_type = "bt"
        ok("BMC: BT IPMI interface -- install proxmoxbmc on node for network access")
    else:
        bmc_type = None
        ok("BMC: None")

    return {"sockets": sockets, "cores": cores, "ram": ram, "disk": disk, "bmc_type": bmc_type}

# =============================================================================
# CONSOLE SELECTION
# =============================================================================

def select_console(role):
    """Select console configuration."""
    section("CONSOLE CONFIGURATION")

    is_serial_role = role in SERIAL_CONSOLE_ROLES
    if is_serial_role:
        info(f"Role {role} defaults to VGA + Serial (boot via VGA, OS console via ttyS0)")
        default = "2"
    else:
        info(f"Role {role} defaults to SPICE (1 monitor) — recommended for desktop/server VMs")
        default = "4"

    print()
    print(f"  {C.W}Console type:{C.NC}")
    print(f"  {C.CY}  1{C.NC}  VGA only        (32MB, standard — use if SPICE client unavailable)")
    print(f"  {C.CY}  2{C.NC}  VGA + Serial    (VGA for boot/iPXE, ttyS0 for OS — recommended for appliances)")
    print(f"  {C.CY}  3{C.NC}  Serial only     (fully headless — iPXE must also be serial-capable)")
    print(f"  {C.CY}  4{C.NC}  SPICE           (1 monitor, SPICE audio — recommended for desktop/server VMs)")
    print()

    choice = prompt("Select console", default=default,
                    validator=lambda v: True if v in ("1","2","3","4") else "Enter 1, 2, 3 or 4")

    if choice == "2":
        ok("Console: VGA + Serial (ttyS0) — use 'qm terminal VMID' for OS console")
        return "both"
    elif choice == "3":
        ok("Console: Serial only (ttyS0) — use 'qm terminal VMID' to connect")
        return "serial"
    elif choice == "4":
        ok("Console: SPICE (1 monitor) — connect via virt-viewer or Proxmox web console")
        return "spice"
    else:
        ok("Console: VGA only (32MB)")
        return "vga"

# =============================================================================
# NETWORK CONFIGURATION
# =============================================================================

def _prompt_nic(idx, default_bridge, default_vlan, default_desc):
    """Prompt for a single NIC's bridge, VLAN, and optional MAC. Returns NIC dict."""
    import re as _re
    nic_id = f"net{idx}"
    print()
    info(f"  {nic_id}:")

    def validate_bridge(v):
        return True if re.match(r"^vmbr\d+$", v) else "Bridge must be vmbrN (e.g. vmbr0, vmbr1)"

    bridge = prompt(f"    Bridge for {nic_id}", default=default_bridge,
                    validator=validate_bridge)

    # CLD VLAN is the fallback — blank and CLD are synonymous in this environment.
    # Site-specific VLAN takes precedence when one is proposed (default_vlan is not None).
    cld_vlan       = SITES["CLD"]["octet"]
    effective_vlan = default_vlan if default_vlan is not None else cld_vlan
    vlan_label     = "" if default_vlan is not None else "  [CLD fallback]"
    vlan_raw = prompt(
        f"    VLAN tag for {nic_id}{vlan_label}",
        default=str(effective_vlan),
    )
    try:
        vlan = int(vlan_raw)
    except ValueError:
        warn(f"Invalid VLAN — using CLD VLAN {cld_vlan}")
        vlan = cld_vlan

    # vmbr0 SPECIAL CASE — provisioning bridge / "bridged mode"
    # ---------------------------------------------------------------
    # vmbr0 sits on vmnic0 which is a switch ACCESS port already on
    # 192.168.139.0/24 (the CLD / provisioning network). Access ports
    # carry traffic UNTAGGED — adding a VLAN tag here would produce
    # double-tagged frames that the switch drops silently.
    #
    # So: if the user picked vmbr0 AND left the VLAN at the CLD default
    # (i.e. they mean "provisioning network" not a specific tagged VLAN),
    # we collapse it to None (untagged). If they typed a different VLAN
    # number deliberately we leave it alone — they know what they're doing.
    if bridge == "vmbr0" and vlan == cld_vlan:
        vlan = None
        info(f"  {nic_id}: vmbr0 + CLD VLAN detected — using native/untagged (provisioning bridge mode)")

    desc = prompt(f"    Description for {nic_id}", default=default_desc)

    mac_val = input(f"  MAC for {nic_id} [blank = auto]: ").strip()
    mac = None
    if mac_val:
        if _re.match(r"^([0-9A-Fa-f]{2}:){{5}}[0-9A-Fa-f]{{2}}$", mac_val):
            mac = mac_val.lower()
            ok(f"{nic_id}: MAC set to {mac}")
        else:
            warn(f"Invalid MAC format — auto MAC will be assigned")

    return {
        "id":     nic_id,
        "model":  "virtio",
        "bridge": bridge,
        "vlan":   vlan,
        "mac":    mac,
        "desc":   desc,
    }


def configure_network(role, site):
    """
    Build NIC list based on role and site. Returns list of NIC dicts.

    Proposes a sensible default layout (single or dual NIC based on role),
    then asks how many NICs are needed. Each NIC is individually prompted
    for bridge, VLAN tag, description, and optional MAC address.
    Supports up to 10 NICs (Proxmox limit: net0–net9).
    """
    section("NETWORK CONFIGURATION")

    site_data = SITES[site]
    octet     = site_data["octet"]
    vlan_id   = octet
    subnet    = site_data["subnet"]
    gw        = site_data["gateway"]
    dc_ip     = site_data["dc"]
    fw_ip     = site_data["fw"]

    # CLD VLAN is the environment-wide fallback — blank and CLD are synonymous here.
    cld_vlan = SITES["CLD"]["octet"]

    dual_nic      = role in DUAL_NIC_ROLES
    default_count = 2 if dual_nic else 1

    if dual_nic:
        info(f"Role {role} — suggested dual NIC layout:")
        info(f"  net0  vmbr0  VLAN {cld_vlan:<5}   (WAN / provisioning — CLD)")
        info(f"  net1  vmbr1  VLAN {vlan_id:<5}   (LAN — {site}, {subnet}  gw={gw})")
    else:
        info(f"Role {role} — suggested single NIC layout:")
        info(f"  net0  vmbr1  VLAN {vlan_id:<5}   ({site}, {subnet}  gw={gw}  dc={dc_ip}  fw={fw_ip})")

    print()
    if not confirm("Configure NICs now?", default="y"):
        warn("Skipping NIC config — configure NICs manually after creation.")
        return []

    # How many NICs?
    nic_count = prompt_int("Number of NICs", default=default_count, min_val=1, max_val=10)

    # Build defaults for each NIC position
    # Position 0: WAN (vmbr0, CLD VLAN) for dual roles, else LAN (vmbr1, site VLAN)
    # Position 1: LAN (vmbr1, site VLAN) for dual roles
    # Position 2+: vmbr1, CLD VLAN fallback — user fills in
    # Note: None is never passed as default_vlan; _prompt_nic() maps None → cld_vlan
    #       but we pass cld_vlan explicitly here for clarity in the summary display.
    def _defaults(idx):
        if dual_nic:
            if idx == 0:
                return "vmbr0", cld_vlan, "WAN / provisioning (CLD)"
            elif idx == 1:
                return "vmbr1", vlan_id,  f"LAN — {site} VLAN {vlan_id} ({subnet})"
            else:
                return "vmbr1", cld_vlan, f"Additional NIC {idx}"
        else:
            if idx == 0:
                return "vmbr1", vlan_id,  f"{site} VLAN {vlan_id} ({subnet})"
            else:
                return "vmbr1", cld_vlan, f"Additional NIC {idx}"

    nics = []
    for i in range(nic_count):
        def_bridge, def_vlan, def_desc = _defaults(i)
        nic = _prompt_nic(i, def_bridge, def_vlan, def_desc)
        nics.append(nic)

    print()
    info("NIC configuration summary:")
    for nic in nics:
        if nic["bridge"] == "vmbr0" and nic["vlan"] is None:
            vlan_str = "VLAN untagged (vmbr0 provisioning)"
        else:
            vlan_ann = " (CLD)" if nic["vlan"] == cld_vlan else ""
            vlan_str = f"VLAN {nic['vlan']}{vlan_ann}"
        mac_str  = f"  mac={nic['mac']}" if nic["mac"] else ""
        ok(f"{nic['id']}  {nic['bridge']}  {vlan_str:<18}  virtio{mac_str}  — {nic['desc']}")

    return nics

# =============================================================================
# POOL SELECTION
# =============================================================================

def select_pool(proxmox, site):
    """Enumerate pools, suggest one matching the site code, let user pick or skip."""
    section("POOL")

    try:
        pools = proxmox.pools.get()
        pool_ids = sorted(p["poolid"] for p in pools)
    except Exception as e:
        warn(f"Could not enumerate pools: {e} — skipping pool assignment")
        return None

    if not pool_ids:
        info("No pools defined on this cluster — skipping pool assignment")
        return None

    # Look for a pool whose name contains the site code (case-insensitive)
    site_match = next(
        (p for p in pool_ids if site.upper() in p.upper()),
        None
    )

    info(f"Available pools: {', '.join(pool_ids)}")

    if site_match:
        info(f"Pool matching site {site}: {C.W}{site_match}{C.NC}")
        default_pool = site_match
    else:
        info(f"No pool found matching site code {site}")
        default_pool = ""

    print()
    print(f"  Enter pool name to assign, or leave blank for none.")
    if default_pool:
        print(f"  Press Enter to accept suggested pool {C.W}{default_pool}{C.NC}.")
    print()

    def validate_pool(v):
        if v == "":
            return True
        if v in pool_ids:
            return True
        return f"Unknown pool '{v}'. Available: {', '.join(pool_ids)}"

    raw = prompt("Pool (blank = none)", default=default_pool, validator=validate_pool)
    pool = raw.strip() or None

    if pool:
        ok(f"Pool: {pool}")
    else:
        ok("Pool: none")

    return pool


# =============================================================================
# DRIVER DISK SELECTION
# =============================================================================

def select_driver_disk(proxmox, node, role):
    """For Windows roles, enumerate available driver disk images and prompt.
    Returns a storage path string (e.g. local:iso/virtio-drivers.img) or None."""

    if role not in WINDOWS_ROLES:
        return None

    section("VIRTIO DRIVER DISK")
    info(f"Role {role} is a Windows role — a VirtIO driver disk can be attached as scsi1")
    info("This provides drvload drivers for PhoenixPE and is required for disk/NIC visibility")
    print()

    # Enumerate ISO storage looking for .img files that look like driver disks
    try:
        stores = proxmox.nodes(node).storage.get(content="iso")
        candidates = []
        for store in stores:
            storage_name = store["storage"]
            try:
                items = proxmox.nodes(node).storage(storage_name).content.get(content="iso")
                for item in items:
                    volid = item.get("volid", "")
                    # Include .img files — driver disks are raw images stored in iso dir
                    if volid.lower().endswith(".img"):
                        candidates.append(volid)
            except Exception:
                pass
    except Exception as e:
        warn(f"Could not enumerate storage: {e}")
        candidates = []

    if not candidates:
        warn("No .img files found in ISO storage — skipping driver disk")
        warn("Build one with make-virtio-disk.sh and copy to /var/lib/vz/template/iso/")
        return None

    # Check for an obvious virtio driver disk by name
    default_candidate = next(
        (c for c in candidates if "virtio" in c.lower()),
        candidates[0]
    )

    print(f"  {'#':<4}  {'Volume ID'}")
    print(f"  {'-'*4}  {'-'*50}")
    for i, volid in enumerate(candidates, 1):
        marker = f"{C.G}←{C.NC}" if volid == default_candidate else ""
        print(f"  {C.CY}{i:<4}{C.NC}  {volid}  {marker}")
    print(f"  {C.CY}0{C.NC}     Skip — no driver disk")
    print()

    default_idx = candidates.index(default_candidate) + 1

    def validate_disk_choice(v):
        if not v.isdigit():
            return "Enter a number"
        v = int(v)
        if 0 <= v <= len(candidates):
            return True
        return f"Enter 0–{len(candidates)}"

    choice = prompt(f"Driver disk [0–{len(candidates)}]",
                    default=str(default_idx),
                    validator=validate_disk_choice)
    choice = int(choice)

    if choice == 0:
        ok("No driver disk — attach manually if needed")
        return None

    selected = candidates[choice - 1]
    ok(f"Driver disk: {selected}")
    return selected


def select_virtio_iso(proxmox, node, role):
    """For Windows roles, offer to attach the VirtIO ISO as ide2 (CDROM).
    Returns volid string or None.

    Context for new VM builds (this script):
        For fresh Windows installs, driver installation is handled by your
        unattended setup / postOOBE.cmd copying the VirtIO MSIs to
        C:\\Windows\\Setup\\. This CDROM is therefore optional — useful if
        you want the ISO available for manual driver installs or the Guest
        Agent MSI, but not critical. Default is to skip.

        Note: this is different from V2V migrations (convert-v2v.py) where
        the CDROM is the fallback if virt-v2v auto-injection from
        /usr/share/virtio-win/ has not been set up.

    The ISO is expected at /var/lib/vz/template/iso/ on the Proxmox node.
    See first-boot.sh Step 3c for how to download it.
    """
    if role not in WINDOWS_ROLES:
        return None

    section("VIRTIO DRIVERS ISO (CDROM) — optional for new VMs")
    info(f"Role {role} is a Windows VM.")
    info("For new VM builds, driver installation is typically handled by")
    info("your unattended setup / postOOBE.cmd (copies VirtIO MSIs from")
    info("C:\\Windows\\Setup\\) — so this CDROM is optional.")
    info("Attach it if you want the ISO available for manual installs or")
    info("the QEMU Guest Agent MSI. Default: skip.")
    print()

    try:
        stores = proxmox.nodes(node).storage.get(content="iso")
        candidates = []
        for store in stores:
            sname = store["storage"]
            try:
                items = proxmox.nodes(node).storage(sname).content.get(content="iso")
                for item in items:
                    volid = item.get("volid", "")
                    if volid.lower().endswith(".iso"):
                        candidates.append(volid)
            except Exception:
                pass
    except Exception as e:
        warn(f"Could not enumerate ISO storage: {e}")
        candidates = []

    if not candidates:
        info("No ISOs found in local storage — skipping.")
        info("If needed later: attach manually via Proxmox UI → Hardware → Add → CD/DVD")
        return None

    default_candidate = next(
        (c for c in candidates if "virtio" in c.lower()),
        None
    )

    print(f"  {'#':<4}  {'Volume ID'}")
    print(f"  {'-'*4}  {'-'*55}")
    for i, volid in enumerate(candidates, 1):
        marker = f"  {C.G}← virtio-win{C.NC}" if volid == default_candidate else ""
        print(f"  {C.CY}{i:<4}{C.NC}  {volid}{marker}")
    print(f"  {C.CY}0   {C.NC}  Skip — postOOBE.cmd handles drivers (recommended)")
    print()

    # Default to skip for new VMs — postOOBE handles it
    def validate_iso_choice(v):
        if not v.isdigit():
            return "Enter a number"
        v = int(v)
        if 0 <= v <= len(candidates):
            return True
        return f"Enter 0–{len(candidates)}"

    choice = int(prompt(f"Select VirtIO ISO [0–{len(candidates)}]",
                        default="0",
                        validator=validate_iso_choice))

    if choice == 0:
        ok("No VirtIO ISO — postOOBE.cmd will handle driver installation.")
        return None

    selected = candidates[choice - 1]
    ok(f"VirtIO ISO: {selected}")
    return selected


# =============================================================================
# BIOS ROM SELECTION
# =============================================================================

# Friendly names for known ROM files.
# Keys are substrings matched case-insensitively against the filename.
# First match wins -- order from most specific to least specific.
ROM_DESCRIPTIONS = [
    ("WORKSTATION",  "25H2",  "DELL2.7",  "BIOS.440",  "Modded SeaBIOS -- Dell SLIC 2.7 / Win Server 2025 H2 SLP (legacy BIOS)"),
    ("WORKSTATION",  "25H2",  "DELL2.7",  "EFI20-64",  "Modded UEFI 2.0 64-bit -- Dell SLIC 2.7 / Win Server 2025 H2 SLP"),
    ("WORKSTATION",  "25H2",  "DELL2.7",  "EFI64",     "Modded UEFI 64-bit -- Dell SLIC 2.7 / Win Server 2025 H2 SLP"),
    ("BIOS.440",     "",      "",         "",          "Stock SeaBIOS 440 (no SLIC -- standard QEMU BIOS)"),
    ("EFI20-64",     "",      "",         "",          "Stock UEFI 2.0 64-bit (no SLIC)"),
    ("EFI64",        "",      "",         "",          "Stock UEFI 64-bit (no SLIC)"),
]

def _describe_rom(filename):
    """Return a human-readable description for a ROM filename."""
    upper = filename.upper()
    for parts in ROM_DESCRIPTIONS:
        keywords, *_ = parts[:-1], parts[-1]
        desc = parts[-1]
        keywords = parts[:-1]
        if all(k.upper() in upper or k == "" for k in keywords):
            return desc
    return "Custom ROM"

def select_bios_rom(proxmox, node):
    """
    Enumerate .ROM files in /usr/share/kvm/ on the Proxmox node and present
    a selection menu. Returns (bios_type, rom_path) where bios_type is
    'seabios' or 'ovmf' and rom_path is the full path or None for default.

    The ROM path is passed to QEMU via the VM args field:
        args: -bios /usr/share/kvm/FILENAME.ROM
    for SeaBIOS-type ROMs, or:
        args: -bios /usr/share/kvm/FILENAME.ROM
    for EFI ROMs (Proxmox handles OVMF via the bios=ovmf config key separately,
    but custom EFI ROMs require the args override).
    """
    section("BIOS ROM")

    # Query the node for .ROM files in /usr/share/kvm/
    # We use the Proxmox API execute endpoint to run a shell command on the node.
    roms = []
    try:
        result = proxmox.nodes(node).execute.post(
            command="ls /usr/share/kvm/*.ROM /usr/share/kvm/*.rom 2>/dev/null || true"
        )
        lines = result.get("data", "").strip().splitlines() if isinstance(result, dict) else str(result).strip().splitlines()
        roms = [l.strip() for l in lines if l.strip() and ("ROM" in l.upper())]
    except Exception:
        # execute endpoint may not be available -- try via vzdump node API
        pass

    # Fallback: if API execute not available, list known ROM paths statically
    if not roms:
        warn("Could not enumerate ROMs via API -- showing known ROM names.")
        warn("Place .ROM files in /usr/share/kvm/ on the Proxmox node.")
        known = [
            "WORKSTATION_25H2_DELL2.7_BIOS.440.ROM",
            "WORKSTATION_25H2_DELL2.7_EFI20-64.ROM",
            "WORKSTATION_25H2_DELL2.7_EFI64.ROM",
            "BIOS.440.ROM",
            "EFI20-64.ROM",
            "EFI64.ROM",
        ]
        roms = [f"/usr/share/kvm/{r}" for r in known]

    print()
    print(f"  {C.W}Available BIOS ROMs  (/usr/share/kvm/ on {node}):{C.NC}")
    print()
    print(f"  {C.CY}  0{C.NC}  Default SeaBIOS (no custom ROM -- standard Proxmox behaviour)")
    print()

    for i, path in enumerate(roms, 1):
        fname = path.split("/")[-1]
        desc  = _describe_rom(fname)
        btype = "EFI" if any(x in fname.upper() for x in ("EFI", "OVMF", "UEFI")) else "SeaBIOS"
        print(f"  {C.CY}  {i}{C.NC}  [{btype}]  {fname}")
        print(f"       {C.D}{desc}{C.NC}")
    print()

    def validate_rom(v):
        if v.isdigit() and 0 <= int(v) <= len(roms):
            return True
        return f"Enter a number between 0 and {len(roms)}"

    choice = int(prompt("Select BIOS ROM", default="0", validator=validate_rom))

    if choice == 0:
        ok("BIOS: Default SeaBIOS (no custom ROM)")
        return "seabios", None

    selected_path = roms[choice - 1]
    fname = selected_path.split("/")[-1]
    is_efi = any(x in fname.upper() for x in ("EFI", "OVMF", "UEFI"))
    bios_type = "ovmf" if is_efi else "seabios"
    ok(f"BIOS ROM: {fname}  ({_describe_rom(fname)})")
    return bios_type, selected_path


# =============================================================================
# SERIAL CONSOLE / BMC GUEST OS ADVISORY
# =============================================================================

def _is_windows(ostype):
    """True if ostype is a Windows variant."""
    return ostype and ostype.lower().startswith("win")

def print_serial_advisory(vmid, ostype, console, bmc_type=None):
    """
    Print guest OS configuration steps needed to make the serial console
    and/or BMC SOL connection actually work.

    Called after VM creation/import when serial console is enabled.
    Tailored to OS type: Linux gets GRUB + getty instructions,
    Windows gets bcdedit + EMS/SAC instructions.

    Only prints if serial is in use (console = serial or both).
    """
    if console not in ("serial", "both"):
        return

    bmc_active = bool(bmc_type)
    is_win     = _is_windows(ostype)

    print()
    print(f"  {C.Y}+-- SERIAL CONSOLE: GUEST OS CONFIGURATION REQUIRED {'─'*20}+{C.NC}")
    print(f"  {C.Y}|{C.NC}  The Proxmox serial port is wired up but the guest OS also needs   {C.Y}|{C.NC}")
    print(f"  {C.Y}|{C.NC}  configuring to use it. Steps below depend on OS type.             {C.Y}|{C.NC}")
    if bmc_active:
        print(f"  {C.Y}|{C.NC}  {C.W}BMC emulation is enabled -- connect via: ipmitool sol activate{C.NC}  {C.Y}|{C.NC}")
    print(f"  {C.Y}+{'─'*68}+{C.NC}")
    print()

    if is_win:
        # Windows: bcdedit + EMS/SAC
        print(f"  {C.W}Windows: Enable EMS / SAC (run as Administrator inside the guest){C.NC}")
        print()
        print(f"  {C.D}  # Redirect boot menu to COM1 (the GRUB menu equivalent){C.NC}")
        print(f"  {C.CY}  bcdedit /set '{{bootmgr}}' displaybootmenu yes{C.NC}")
        print(f"  {C.CY}  bcdedit /set '{{bootmgr}}' timeout 10{C.NC}")
        print(f"  {C.CY}  bcdedit /set '{{bootmgr}}' bootems yes{C.NC}")
        print()
        print(f"  {C.D}  # Enable SAC and redirect OS serial output to COM1{C.NC}")
        print(f"  {C.CY}  bcdedit /ems '{{current}}' on{C.NC}")
        print(f"  {C.CY}  bcdedit /emssettings EMSPORT:1 EMSBAUDRATE:115200{C.NC}")
        print()
        print(f"  {C.D}  # Verify{C.NC}")
        print(f"  {C.CY}  bcdedit /enum '{{bootmgr}}'  # should show bootems Yes{C.NC}")
        print()
        print(f"  {C.D}  After reboot, connect via SOL and you will see the boot menu,{C.NC}")
        print(f"  {C.D}  then the SAC prompt. From SAC:{C.NC}")
        print(f"  {C.CY}    SAC> cmd{C.NC}             {C.D}# open CMD channel{C.NC}")
        print(f"  {C.CY}    SAC> ch -sn Cmd0001{C.NC}  {C.D}# switch to it, authenticate{C.NC}")
        print(f"  {C.CY}    C:\\> powershell{C.NC}     {C.D}# full PowerShell over serial{C.NC}")
        print()
        print(f"  {C.D}  Join-DomainAndBootstrap.ps1 Stage 17b does this automatically.{C.NC}")
        print(f"  {C.D}  See NET-BMC-001 Section 4b for full walkthrough.{C.NC}")
    else:
        # Linux: GRUB + serial getty
        print(f"  {C.W}Linux: Configure GRUB and serial getty (inside the guest){C.NC}")
        print()
        print(f"  {C.D}  # Step 1: Edit /etc/default/grub{C.NC}")
        print(f"  {C.CY}  GRUB_CMDLINE_LINUX=\"console=ttyS0,115200n8 console=tty0\"{C.NC}")
        print(f"  {C.CY}  GRUB_TERMINAL=\"serial console\"{C.NC}")
        print(f"  {C.CY}  GRUB_SERIAL_COMMAND=\"serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1\"{C.NC}")
        print()
        print(f"  {C.D}  # Step 2: Regenerate GRUB config{C.NC}")
        print(f"  {C.CY}  update-grub                           {C.D}# Debian/Ubuntu{C.NC}")
        print(f"  {C.CY}  grub-mkconfig -o /boot/grub/grub.cfg  {C.D}# Arch/RHEL{C.NC}")
        print()
        print(f"  {C.D}  # Step 3: Serial getty (belt-and-braces){C.NC}")
        print(f"  {C.CY}  systemctl enable --now serial-getty@ttyS0.service{C.NC}")
        print()
        print(f"  {C.D}  After reboot: GRUB menu, kernel messages, login -- all on ttyS0.{C.NC}")
        print(f"  {C.D}  Verify: dmesg | grep ttyS  (should show 16550A at 0x3f8){C.NC}")
        print(f"  {C.D}  See NET-BMC-001 Section 4 for full walkthrough.{C.NC}")

    print()
    if bmc_active:
        bmc_port = 6000 + vmid
        print(f"  {C.D}  Connect to this VM via SOL:{C.NC}")
        print(f"  {C.CY}  ipmitool -I lanplus -H <pve-ip> -p {bmc_port} -U admin -P <pass> sol activate{C.NC}")
        print(f"  {C.D}  Exit SOL: ~ then . (tilde, full stop){C.NC}")
    else:
        print(f"  {C.D}  Connect to this VM serial console via Proxmox:{C.NC}")
        print(f"  {C.CY}  qm terminal {vmid}{C.NC}")
    print()

# =============================================================================
# VM CREATION
# =============================================================================

def build_vm_config(vmid, name, role, site, hw, storage, console,
                    nics, ostype, ipxe_iso, pool=None, driver_disk=None,
                    virtio_iso=None, bios_type="seabios", bios_rom=None):
    bmc_type = hw.get("bmc_type")
    """Build the full VM config dict for display and creation."""

    # Boot order: disk first, CDROM (ide2) fallback, then PXE
    boot_order = "order=scsi0;ide2;net0"

    cfg = {
        "vmid":    vmid,
        "name":    name,
        "ostype":  ostype,
        "cores":   hw["cores"],
        "sockets": hw["sockets"],
        "cpu":     "host",
        "memory":  hw["ram"],
        "balloon": 0,
        "bios":    bios_type,
        "bios_rom": bios_rom,  # None = default SeaBIOS; path = custom ROM via args
        "bmc_type":  bmc_type,   # None = no BMC; kcs or bt = IPMI interface type
        "boot":    boot_order,
        "onboot":  0,
        "agent":   1,           # qemu-guest-agent enabled by default
        # Disk
        "storage": storage,
        "disk_gb": hw["disk"],
        # Console
        "console": console,
        # NICs
        "nics":    nics,
        # ISO
        "ipxe_iso":    ipxe_iso,
        # Pool
        "pool":        pool,
        # VirtIO driver disk (Windows roles — PhoenixPE .img)
        "driver_disk": driver_disk,
        # VirtIO ISO CDROM (Windows roles — for driver injection/install)
        "virtio_iso":  virtio_iso,
    }
    return cfg

def print_summary(cfg, dry_run=False):
    """Print a human-readable summary of the VM config."""
    tag = f"{C.B}[DRY RUN]{C.NC} " if dry_run else ""
    print()
    print(f"{C.Y}  {'=' * 54}{C.NC}")
    print(f"{C.W}  {tag}VM CONFIGURATION SUMMARY{C.NC}")
    print(f"{C.Y}  {'=' * 54}{C.NC}")
    print()
    print(f"  {C.W}Identity{C.NC}")
    print(f"    {C.CY}VM ID  :{C.NC} {cfg['vmid']}")
    print(f"    {C.CY}Name   :{C.NC} {cfg['name']}")
    print(f"    {C.CY}OS Type:{C.NC} {cfg['ostype']}")
    print(f"    {C.CY}Pool   :{C.NC} {cfg['pool'] if cfg['pool'] else '(none)'}")
    print(f"    {C.CY}Agent  :{C.NC} {'enabled' if cfg['agent'] else 'disabled'}")
    print()
    print(f"  {C.W}Hardware{C.NC}")
    print(f"    {C.CY}CPU    :{C.NC} {cfg['sockets']} socket(s) × {cfg['cores']} core(s) = {cfg['sockets'] * cfg['cores']} vCPU(s), type=host")
    print(f"    {C.CY}RAM    :{C.NC} {cfg['memory']}MB (ballooning disabled)")
    print(f"    {C.CY}Disk   :{C.NC} {cfg['disk_gb']}GB on {cfg['storage']} (scsi0, VirtIO SCSI)")
    bios_label = cfg.get("bios", "seabios").upper()
    bios_rom   = cfg.get("bios_rom")
    if bios_rom:
        rom_fname = bios_rom.split("/")[-1]
        print(f"    {C.CY}BIOS   :{C.NC} {bios_label} -- custom ROM: {rom_fname}")
        print(f"    {C.CY}       {C.NC}   {C.D}{_describe_rom(rom_fname)}{C.NC}")
    else:
        print(f"    {C.CY}BIOS   :{C.NC} {bios_label} (default)")
    bmc = cfg.get("bmc_type")
    if bmc:
        vmid = cfg.get("vmid", "VMID")
        print(f"    {C.CY}BMC    :{C.NC} IPMI {bmc.upper()} interface (ipmi-bmc-sim)")
        print(f"    {C.D}           /dev/ipmi0 will be present in guest OS{C.NC}")
        print(f"    {C.D}           Register with proxmoxbmc on the Proxmox node after creation:{C.NC}")
        print(f"    {C.D}           pbmc add --port {6000 + int(vmid) if isinstance(vmid, int) else '6000+VMID'} --address <bind-ip> <vmid>{C.NC}")
        print(f"    {C.D}           --address: use provisioning VLAN IP to restrict access (see NET-BMC-001){C.NC}")
        print(f"    {C.D}           --address 0.0.0.0 binds to ALL interfaces -- avoid in production{C.NC}")
    else:
        print(f"    {C.CY}BMC    :{C.NC} None")
    print()
    print(f"  {C.W}Console{C.NC}")
    if cfg["console"] == "serial":
        print(f"    {C.CY}Type   :{C.NC} Serial only (ttyS0) — connect via: qm terminal {cfg['vmid']}")
    elif cfg["console"] == "both":
        print(f"    {C.CY}Type   :{C.NC} VGA (boot/iPXE) + Serial ttyS0 (OS) — connect via: qm terminal {cfg['vmid']}")
        print(f"    {C.CY}Video  :{C.NC} 32MB")
    elif cfg["console"] == "spice":
        print(f"    {C.CY}Type   :{C.NC} SPICE (1 monitor, SPICE audio)")
        print(f"    {C.CY}Connect:{C.NC} Proxmox web console or virt-viewer")
    else:
        print(f"    {C.CY}Type   :{C.NC} VGA only")
        print(f"    {C.CY}Video  :{C.NC} 32MB")
    print()
    print(f"  {C.W}Boot Order{C.NC}")
    print(f"    {C.CY}1st    :{C.NC} scsi0 (disk)")
    print(f"    {C.CY}2nd    :{C.NC} ide2  (iPXE ISO / VirtIO CDROM)")
    print(f"    {C.CY}3rd    :{C.NC} net0  (PXE network)")
    if cfg["ipxe_iso"]:
        print(f"    {C.CY}iPXE   :{C.NC} {cfg['ipxe_iso'].split('/')[-1]}")
    else:
        print(f"    {C.CY}iPXE   :{C.NC} None attached")
    if cfg.get("virtio_iso"):
        print(f"    {C.CY}VirtIO :{C.NC} {cfg['virtio_iso'].split('/')[-1]} (ide2 — driver injection)")
    if cfg["driver_disk"]:
        print(f"    {C.CY}DrvDisk:{C.NC} {cfg['driver_disk'].split('/')[-1]} (scsi1 — VirtIO drivers for WinPE)")
    print()
    print(f"  {C.W}Network{C.NC}")
    if cfg["nics"]:
        cld_vlan = SITES["CLD"]["octet"]
        for nic in cfg["nics"]:
            if nic["bridge"] == "vmbr0" and nic["vlan"] is None:
                vlan_str = "VLAN untagged (vmbr0 provisioning)"
            else:
                vlan_ann = " (CLD)" if nic["vlan"] == cld_vlan else ""
                vlan_str = f"VLAN {nic['vlan']}{vlan_ann}"
            print(f"    {C.CY}{nic['id']:5}{C.NC}  {nic['bridge']}  {vlan_str:<18}  virtio  — {nic['desc']}")
    else:
        print(f"    {C.Y}No NICs configured — add manually after creation{C.NC}")
    print()

def create_vm(proxmox, node, cfg, dry_run=False):
    """Issue API calls to create the VM."""

    if dry_run:
        dry("Dry run — no changes made.")
        return True

    vmid    = cfg["vmid"]
    storage = cfg["storage"]

    step("Creating VM...")
    try:
        # Custom BIOS ROM is passed via QEMU -bios flag in the args field.
        # This is per-VM and does not affect other VMs on the node.
        # Build QEMU args -- custom BIOS ROM and/or BMC emulation
        args_parts = []
        if cfg.get("bios_rom"):
            args_parts.append(f"-bios {cfg['bios_rom']}")
        if cfg.get("bmc_type") == "kcs":
            args_parts.append("-device ipmi-bmc-sim,id=bmc0 -device isa-ipmi-kcs,bmc=bmc0,irq=5")
        elif cfg.get("bmc_type") == "bt":
            args_parts.append("-device ipmi-bmc-sim,id=bmc0 -device isa-ipmi-bt,bmc=bmc0")
        extra_args = " ".join(args_parts)

        proxmox.nodes(node).qemu.post(
            vmid    = vmid,
            name    = cfg["name"],
            ostype  = cfg["ostype"],
            cores   = cfg["cores"],
            sockets = cfg["sockets"],
            cpu     = "host",
            memory  = cfg["memory"],
            balloon = 0,
            bios    = cfg["bios"],
            boot    = cfg["boot"],
            onboot  = 0,
            agent   = "enabled=1",
            scsihw  = "virtio-scsi-pci",
            **({"pool": cfg["pool"]} if cfg["pool"] else {}),
            **({"args": extra_args} if extra_args else {}),
        )
        ok(f"VM {vmid} created")
        if cfg.get("bmc_type"):
            bmc_port = 6000 + vmid
            warn("BMC emulation enabled -- register with proxmoxbmc on the Proxmox node:")
            warn(f"  pbmc add --username admin --password <bmc-pass>")
            warn(f"    --port {bmc_port}")
            warn(f"    --address <bind-ip>  (provisioning VLAN IP recommended -- see NET-BMC-001)")
            warn(f"    --proxmox-address <pve-ip>")
            warn(f"    --token-user root@pam --token-name proxmoxbmc --token-value <token>")
            warn(f"    {vmid}")
            warn(f"  pbmc start {vmid}")
            warn(f"  pbmc list")
    except Exception as e:
        err(f"Failed to create VM: {e}")

    step("Adding disk...")
    try:
        disk_spec = f"{storage}:{cfg['disk_gb']}"
        proxmox.nodes(node).qemu(vmid).config.put(scsi0=disk_spec)
        ok(f"Disk: {cfg['disk_gb']}GB on {storage}")
    except Exception as e:
        warn(f"Failed to add disk: {e} — add manually")

    # ── CDROM / ISO attachment ─────────────────────────────────────────────────
    # VirtIO ISO takes ide2 (highest priority — needed for driver injection on
    # first boot).  iPXE moves to ide3 when VirtIO ISO is also present.
    if cfg.get("virtio_iso"):
        step("Attaching VirtIO ISO as ide2 (CDROM)...")
        try:
            proxmox.nodes(node).qemu(vmid).config.put(
                ide2=f"{cfg['virtio_iso']},media=cdrom"
            )
            ok(f"VirtIO ISO attached: {cfg['virtio_iso'].split('/')[-1]}")
            info("To inject drivers offline (Windows recovery console):")
            info("  dism /image:C:\\ /add-driver /driver:D:\\ /recurse")
            info("Disable Secure Boot (F2) and driver signing (F8) if needed on first boot.")
        except Exception as e:
            warn(f"Failed to attach VirtIO ISO: {e} — attach manually as ide2")

    if cfg["ipxe_iso"]:
        # Use ide3 if VirtIO ISO already occupies ide2, otherwise ide2
        cdrom_slot = "ide3" if cfg.get("virtio_iso") else "ide2"
        step(f"Attaching iPXE ISO as {cdrom_slot}...")
        try:
            proxmox.nodes(node).qemu(vmid).config.put(
                **{cdrom_slot: f"{cfg['ipxe_iso']},media=cdrom"}
            )
            ok(f"iPXE ISO attached ({cdrom_slot}): {cfg['ipxe_iso'].split('/')[-1]}")
        except Exception as e:
            warn(f"Failed to attach iPXE ISO: {e} — attach manually")

    step("Configuring console...")
    try:
        if cfg["console"] == "serial":
            # Fully headless — serial only, no VGA
            proxmox.nodes(node).qemu(vmid).config.put(
                serial0="socket",
                vga="serial0"
            )
            ok("Console: Serial only (ttyS0) — 'qm terminal VMID' to connect")
        elif cfg["console"] == "both":
            # VGA for boot/iPXE, serial available for OS console
            proxmox.nodes(node).qemu(vmid).config.put(
                serial0="socket",
                vga="std,memory=32"
            )
            ok("Console: VGA (boot/iPXE) + Serial ttyS0 (OS) — 'qm terminal VMID' for serial")
        elif cfg["console"] == "spice":
            # SPICE -- setting vga=qxl is all Proxmox needs to enable the SPICE server.
            # There is no separate "spice" API parameter -- it does not exist in the
            # qm.conf schema and causes a 400 Bad Request if passed.
            proxmox.nodes(node).qemu(vmid).config.put(
                vga="qxl,memory=64",
            )
            ok("Console: SPICE (1 monitor, QXL, 64MB) -- connect via Proxmox web console or virt-viewer")
        else:
            # VGA only
            proxmox.nodes(node).qemu(vmid).config.put(vga="std,memory=32")
            ok("Console: VGA only (32MB video RAM)")
    except Exception as e:
        warn(f"Failed to set console: {e}")

    step("Configuring NICs...")
    for nic in cfg["nics"]:
        try:
            nic_spec = f"virtio,bridge={nic['bridge']}"
            if nic["vlan"]:
                nic_spec += f",tag={nic['vlan']}"
            if nic.get("mac"):
                nic_spec += f",macaddr={nic['mac']}"
            proxmox.nodes(node).qemu(vmid).config.put(**{nic["id"]: nic_spec})
            cld_vlan = SITES["CLD"]["octet"]
            if nic["bridge"] == "vmbr0" and nic["vlan"] is None:
                vlan_str = "VLAN untagged (vmbr0 provisioning)"
            else:
                vlan_ann = " (CLD)" if nic["vlan"] == cld_vlan else ""
                vlan_str = f"VLAN {nic['vlan']}{vlan_ann}"
            mac_str  = f"  mac={nic['mac']}" if nic.get("mac") else ""
            ok(f"{nic['id']}: {nic['bridge']} {vlan_str} virtio{mac_str}")
        except Exception as e:
            warn(f"Failed to configure {nic['id']}: {e}")

    if cfg["driver_disk"]:
        step("Attaching VirtIO driver disk...")
        try:
            proxmox.nodes(node).qemu(vmid).config.put(
                scsi1=f"{cfg['driver_disk']},media=disk"
            )
            ok(f"Driver disk attached: {cfg['driver_disk'].split('/')[-1]} → scsi1")
        except Exception as e:
            warn(f"Failed to attach driver disk: {e} — attach manually as scsi1")

    return True

# =============================================================================
# LOGGING
# =============================================================================

def write_log(log_file, cfg, node, dry_run=False):
    """Append a log entry for the created VM."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        nics_str  = "; ".join(
            f"{n['id']}={n['bridge']}{'(VLAN '+str(n['vlan'])+')' if n['vlan'] else ''}"
            for n in cfg["nics"]
        )
        line = (
            f"{timestamp}  "
            f"{'[DRY-RUN] ' if dry_run else ''}"
            f"VMID={cfg['vmid']}  "
            f"NAME={cfg['name']}  "
            f"NODE={node}  "
            f"POOL={cfg['pool'] or 'none'}  "
            f"OS={cfg['ostype']}  "
            f"CPU={cfg['sockets']}s×{cfg['cores']}c({cfg['sockets'] * cfg['cores']}vCPU)  "
            f"RAM={cfg['memory']}MB  "
            f"DISK={cfg['disk_gb']}GB@{cfg['storage']}  "
            f"CONSOLE={cfg['console']}  "
            f"AGENT={cfg['agent']}  "
            f"DRVDISK={cfg['driver_disk'].split('/')[-1] if cfg['driver_disk'] else 'none'}  "
            f"NICS=[{nics_str}]\n"
        )
        with open(log_file, "a") as f:
            f.write(line)
        ok(f"Logged to {log_file}")
    except Exception as e:
        warn(f"Failed to write log: {e}")

# =============================================================================
# MAIN
# =============================================================================

def create_one_vm(args, proxmox, node):
    """Run through the VM creation questions for a single VM. Returns True on success."""

    # ── VM identity ───────────────────────────────────────────────────────────
    section("VM IDENTITY")

    existing_vms   = get_existing_vms(proxmox, node)
    existing_ids   = set(existing_vms.keys())
    existing_names = set(existing_vms.values())

    role = select_role()
    site = select_site()

    # Suggest next free name
    suggested_suffix = next_free_name_suffix(existing_names, role, site)
    suggested_name   = f"EXA{role}{site}{suggested_suffix}"
    info(f"Next available name: {C.W}{suggested_name}{C.NC}")

    def validate_name(v):
        v = v.upper()
        pattern = r"^EXA[A-Z]{3}[A-Z]{3}[0-9]{3}$"
        if not re.match(pattern, v):
            return "Name must follow pattern EXA[ROLE][SITE][NNN] e.g. EXAFWLFAL001"
        if v in {n.upper() for n in existing_names}:
            return f"Name {v} already exists on this node."
        return True

    vm_name = prompt("VM name", default=suggested_name,
                     validator=validate_name).upper()
    ok(f"Name: {vm_name}")

    # VM ID
    suggested_vmid = next_free_vmid(existing_ids)
    info(f"Next free VM ID: {C.W}{suggested_vmid}{C.NC}")

    def validate_vmid(v):
        if not v.isdigit():
            return "VM ID must be a number."
        vid = int(v)
        if vid < 1000:
            return "VM IDs must be 1000 or higher."
        if vid in existing_ids:
            return f"VM ID {vid} is already in use."
        return True

    vmid = int(prompt("VM ID", default=str(suggested_vmid), validator=validate_vmid))
    ok(f"VM ID: {vmid}")

    # ── OS type ───────────────────────────────────────────────────────────────
    section("OPERATING SYSTEM")
    ostype = select_os_type()

    # ── Hardware ──────────────────────────────────────────────────────────────
    hw = prompt_hardware(role)

    if not confirm("Accept hardware settings?", default="y"):
        err("Aborted by user.")

    # ── Storage ───────────────────────────────────────────────────────────────
    section("STORAGE")
    storage = select_storage(proxmox, node)

    if not confirm("Accept storage selection?", default="y"):
        err("Aborted by user.")

    # ── ISO ───────────────────────────────────────────────────────────────────
    section("iPXE ISO")
    info("Select the iPXE ISO to attach for PXE boot fallback.")
    ipxe_iso = select_iso(proxmox, node, label="iPXE ISO", required=False)

    if not confirm("Accept ISO selection?", default="y"):
        err("Aborted by user.")

    # ── Console ───────────────────────────────────────────────────────────────
    console = select_console(role)

    if not confirm("Accept console selection?", default="y"):
        err("Aborted by user.")

    # ── Network ───────────────────────────────────────────────────────────────
    nics = configure_network(role, site)

    # ── Pool ─────────────────────────────────────────────────────────────────
    pool = select_pool(proxmox, site)

    # ── BIOS ROM (optional) ───────────────────────────────────────────────────
    bios_type, bios_rom = select_bios_rom(proxmox, node)

    # ── Driver disk (Windows roles only) ─────────────────────────────────────
    driver_disk = select_driver_disk(proxmox, node, role)

    # ── VirtIO ISO CDROM (Windows roles only) ─────────────────────────────────
    virtio_iso = select_virtio_iso(proxmox, node, role)

    # ── Build config ──────────────────────────────────────────────────────────
    cfg = build_vm_config(
        vmid=vmid, name=vm_name, role=role, site=site,
        hw=hw, storage=storage, console=console,
        nics=nics, ostype=ostype, ipxe_iso=ipxe_iso, pool=pool,
        driver_disk=driver_disk, virtio_iso=virtio_iso,
        bios_type=bios_type, bios_rom=bios_rom
    )

    # ── Final summary and confirmation ────────────────────────────────────────
    print_summary(cfg, dry_run=args.dry_run)

    if not confirm("Create this VM?", default="n"):
        err("Aborted by user.")

    # ── Create ────────────────────────────────────────────────────────────────
    section("CREATING VM")
    success = create_vm(proxmox, node, cfg, dry_run=args.dry_run)

    if success:
        write_log(args.log, cfg, node, dry_run=args.dry_run)
        # Serial console guest OS advisory -- only shown when serial is in use
        print_serial_advisory(
            vmid     = cfg["vmid"],
            ostype   = cfg["ostype"],
            console  = cfg["console"],
            bmc_type = cfg.get("bmc_type"),
        )

    # ── Start? ────────────────────────────────────────────────────────────────
    if success and not args.dry_run:
        section("START VM")
        if confirm(f"Start VM {vmid} ({vm_name}) now?", default="n"):
            step(f"Starting VM {vmid}...")
            try:
                proxmox.nodes(node).qemu(vmid).status.start.post()
                ok(f"VM {vmid} started")
            except Exception as e:
                warn(f"Failed to start VM: {e} — start manually: qm start {vmid}")
        else:
            info(f"VM left stopped. Start when ready: qm start {vmid}")

    # ── Done ──────────────────────────────────────────────────────────────────
    print()
    print(f"{C.G}  +======================================================+{C.NC}")
    print(f"{C.G}  |{C.W}  {'DRY RUN COMPLETE' if args.dry_run else 'VM CREATION COMPLETE':<50}{C.G}  |{C.NC}")
    print(f"{C.G}  +======================================================+{C.NC}")
    print()
    if not args.dry_run:
        ok(f"VM ID   : {C.W}{vmid}{C.NC}")
        ok(f"Name    : {C.W}{vm_name}{C.NC}")
        ok(f"Node    : {C.W}{node}{C.NC}")
        ok(f"Web UI  : {C.W}Select node → {vm_name} in Proxmox web UI{C.NC}")
    print()
    return success


def main():
    args = parse_args()

    # ── Header ────────────────────────────────────────────────────────────────
    print()
    print(f"{C.CY}  +========================================================+{C.NC}")
    print(f"{C.CY}  |{C.W}                PROXMOX VE — VM CREATION{C.CY}                |{C.NC}")
    print(f"{C.CY}  |{C.D}                    jukebox.internal                    {C.CY}|{C.NC}")
    if args.dry_run:
        print(f"{C.CY}  |{C.B}              *** DRY RUN — NO CHANGES ***              {C.CY}|{C.NC}")
    if args.bulk:
        print(f"{C.CY}  |{C.B}           *** BULK MODE — Ctrl+C to exit ***           {C.CY}|{C.NC}")
    print(f"{C.CY}  +========================================================+{C.NC}")
    print()

    # ── Reload sites if --sites-csv was passed ────────────────────────────────
    global SITES, SITE_OCTET, SITE_CITY, SITE_COUNTRY
    if args.sites_csv:
        SITES        = _load_sites(args.sites_csv)
        SITE_OCTET   = {code: s["octet"]   for code, s in SITES.items() if s["octet"] is not None}
        SITE_CITY    = {code: s["city"]    for code, s in SITES.items()}
        SITE_COUNTRY = {code: s["country"] for code, s in SITES.items()}
        ok(f"Sites loaded from {args.sites_csv} ({len(SITES)} sites)")

    # ── Connect once ──────────────────────────────────────────────────────────
    section("CONNECTING TO PROXMOX")
    if args.dry_run:
        warn("Dry run mode — VMs will not be created")

    proxmox = connect(args)
    node    = select_node(proxmox, args)

    # ── VM creation loop ──────────────────────────────────────────────────────
    vm_count = 0
    while True:
        create_one_vm(args, proxmox, node)
        vm_count += 1

        if not args.bulk:
            break

        print()
        print(f"{C.CY}  ── Bulk mode: {vm_count} VM(s) created this session ─────────────{C.NC}")
        if not confirm("Create another VM?", default="y"):
            break

    if args.bulk and vm_count > 0:
        print()
        ok(f"Bulk session complete — {vm_count} VM(s) created.")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {C.Y}[!]{C.NC} Interrupted — no changes made.\n")
        sys.exit(0)