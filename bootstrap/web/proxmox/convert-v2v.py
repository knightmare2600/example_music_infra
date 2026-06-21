#!/usr/bin/env python3
"""
convert-v2v.py — VMware Workstation → Proxmox VE V2V Conversion Script
Example Music Limited — Internal Infrastructure

Converts one or more VMware VMs (from .vmx + .vmdk) to Proxmox VE using
virt-v2v. Parses VMX files to extract hardware config, names VMs using
the EXA[ROLE][SITE][NNN] convention, handles disk import, and wires up
the resulting VM on a Proxmox node.

Supports three execution modes (auto-detected):

  WORKSTATION (default — recommended)
      Script runs on any Linux box with virt-v2v installed (your laptop,
      a jump host, etc). virt-v2v converts the VMDK locally; only the
      resulting qcow2 is uploaded to Proxmox. Smallest network transfer.

  LOCAL
      Script runs directly on the Proxmox node. virt-v2v runs in-place.
      Use when the VM folder is already on the Proxmox node.

  REMOTE
      virt-v2v not available locally — invoked on the Proxmox node via
      SSH. Raw VMDKs uploaded first (larger transfer than qcow2).
      Script offers to switch to this if virt-v2v is missing locally.

Changelog:
    2026-03-22  Serial console guest OS advisory added -- after import, prints
                tailored steps for Linux (GRUB+getty) or Windows (bcdedit+EMS/SAC).
                Only shown when serial console is selected. print_serial_advisory().
    2026-03-22  BIOS ROM selection added (V2V variant) -- enumerates /usr/share/kvm/
                default: no custom ROM (SeaBIOS). select_bios_rom_v2v().
    2026-03-22  BMC/IPMI emulation added (V2V variant) -- KCS interface,
                default: No for appliance roles, Yes for server roles.
                select_bmc_v2v(). bios_type/bios_rom/bmc_type threaded
                through import_and_wire, write_log, print_conversion_summary.
    2026-03-04  Initial script — VMX discovery, VMX parsing, virt-v2v
                invocation, Proxmox disk import, VM wiring, NIC advisory,
                bulk mode, dry run, logging. Based on create-vm.py.
    2026-03-04  Three execution modes: WORKSTATION (default), LOCAL, REMOTE.
                Binary/dependency check with install hints and mode fallback.
    2026-03-07  sudo for sbin commands — modprobe, blockdev, and qm importdisk
                now prepend sudo when not running as root, matching host OS
                regardless of PATH; manual recovery hints updated to match
    2026-03-07  MAC preservation prompt — optionally carry VMware MACs into
                Proxmox NIC config; avoids DHCP/WireGuard/udev disruption
    2026-03-07  Multi-NIC (3+) handling fixed — each NIC now individually
                prompted for bridge and VLAN tag; no silent truncation
    2026-03-07  Role guesser rewritten — word-boundary matching, EXA naming
                authoritative, falls back to SRV not NIX
    2026-03-07  Site guesser added — deduces site from VMX filename/name
    2026-03-07  OS type table corrected — w2k12/w2k16/w2k19/w2k22 do not
                exist as Proxmox ostype values; win10 covers Win10/Server
                2016/2019, win11 covers Win11/Server 2022/2025
                Source: https://pve.proxmox.com/wiki/Manual:_qm.conf
    2026-03-07  sudo for sbin commands — modprobe, blockdev, and qm importdisk
                now prepend sudo when not running as root, matching host OS
                regardless of PATH; manual recovery hints updated to match
    2026-03-07  MAC preservation — configure_nics() now offers to carry
                VMware MAC addresses into Proxmox NIC config; defaults yes
                to protect DHCP reservations, WireGuard peers, udev rules
    2026-03-07  Role/site guesser fixed — EXA naming parsed directly from
                display name (EXARRRSSS### -> RRR role, SSS site); word-
                boundary matching replaces substring matching; site guesser
                added and wired into select_site() as default
    2026-03-07  NTFS dirty-flag check — scans VMDKs via qemu-nbd before
                conversion; offers ntfsfix -d on any dirty partitions.
                Prevents virt-v2v abort with 'unclean file system' caused
                by Windows suspend/Fast Startup/force-poweroff.
    2026-03-11  Post-conversion Linux boot fixes — apply_linux_boot_fixes()
                uses virt-customize to inject fixes into the converted guest
                disk before import: (1) NM ordering drop-in resolving the
                systemd cycle that silently skips NetworkManager on boot;
                (2) guestfs-firstboot disable when scripts dir is empty.
                virt-customize added to workstation/local binary check lists.
                SVR, WKS, LAP, SUR) now check /usr/share/virtio-win/ at
                OS selection time. When present, virt-v2v auto-injects
                vioscsi/NetKVM/balloon during conversion and the ISO is
                offered as an optional fallback. When absent, drivers are
                NOT injected (emulated IDE/RTL8139 fallback) and the ISO
                is offered as the primary injection path. The check gives
                clear remediation steps (first-boot.sh Step 3c). ISO
                attached as ide2; boot order updated when selected.

    2026-03-12  NTFS dirty flag auto-recovery in LOCAL mode — if virt-v2v exits
                non-zero and the log contains "unclean file system" / "metadata
                kept in Windows cache", the failure handler now: diagnoses the
                log, locates VMDKs from the VMX, connects each via qemu-nbd,
                runs ntfsfix -d on all NTFS partitions (with fallback to probing
                nbd0p1-p4 directly if lsblk returns no NTFS), then automatically
                retries virt-v2v. No manual intervention needed for the common
                "VM was not cleanly shut down" case.

                also checks for guest-agent/qemu-ga-x86_64.msi and returns
                (drivers_ok, agent_msi_path). New apply_windows_firstboot_fixes()
                uses virt-customize --copy-in + --firstboot-command to copy the
                MSI into C:\\Windows\\Temp\\ and register a RunOnce entry that runs
                msiexec silently on the VM's first boot. Wired in after
                apply_linux_boot_fixes() for WINDOWS_ROLES VMs.
    2026-03-12  check_virtio_drivers() now hard-exits (sys.exit(1)) when drivers
                are missing for a Windows VM — with a boxed FATAL message and
                step-by-step remediation. Conversion cannot safely proceed
                without drivers (emulated IDE fallback + BSOD risk).
    2026-03-12  OS type guess fix — VMware string "windows2019srvnext-64" now
                correctly maps to win11 (Server 2022/2025) rather than win10.
                Added explicit mapping for windows2022 and win11 VMX strings.
    2026-03-12  disk_size unbound variable fix — space check in preflight
                crashed in dry-run mode because disk_size was only assigned
                inside the non-dry-run branch. Initialised to 0 before the
                conditional so the space check is always safe.



Options:
    -h, --help              Show this help message and exit
    --host HOST             Proxmox host (e.g. 192.168.139.50)
    --port PORT             Proxmox API port (default: 8006)
    --user USER             Proxmox username (e.g. root@pam)
    --token-name NAME       API token name
    --token-value VALUE     API token value
    --password PASSWORD     Password (if no token)
    --node NODE             Proxmox node name
    --search-path PATH      Directory to search for .vmx files (default: CWD)
    --staging-dir DIR       Staging directory on Proxmox for virt-v2v output
                            (default: /tmp/v2v-import)
    --ssh-user USER         SSH user for remote mode (default: root)
    --ssh-key FILE          SSH private key for remote mode
    --dry-run               Show what would happen without making changes
    --bulk                  Convert multiple VMs in one session
    --log FILE              Log file (default: ~/pve-v2v-convert.log)

Examples:
    # Workstation mode (default) — virt-v2v local, qcow2 pushed to Proxmox
    python3 convert-v2v.py --host 192.168.139.50 --user root@pam

    # With SSH key (recommended for workstation/remote modes)
    python3 convert-v2v.py --host 192.168.139.50 --user root@pam \\
        --ssh-key ~/.ssh/id_rsa

    # Point at a specific directory full of VMX files
    python3 convert-v2v.py --search-path /mnt/vmware-exports/

    # Bulk — convert several VMs in one session
    python3 convert-v2v.py --bulk

    # Dry run — show what would happen, make no changes
    python3 convert-v2v.py --dry-run
"""

import argparse
import datetime
import getpass
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time

try:
    from proxmoxer import ProxmoxAPI
except ImportError:
    print("ERROR: proxmoxer not installed.")
    print("  On Proxmox node : apt install python3-proxmoxer python3-requests")
    print("  On workstation  : pip3 install proxmoxer requests")
    sys.exit(1)

# =============================================================================
# SITE AND ROLE TABLES  (loaded from sites.csv -- single source of truth)
# =============================================================================

import csv as _csv_mod
import os as _os

def _load_sites(csv_path=None):
    """
    Load site data from sites.csv.
    Searches: same directory as this script, then current working directory,
    then /etc/example-music/sites.csv.
    Override with SITES_CSV environment variable or csv_path argument.
    """
    if csv_path is None:
        csv_path = _os.environ.get("SITES_CSV")
    if csv_path is None:
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
        print("  Looked in: script directory, cwd, /etc/example-music/sites.csv")
        print("  Set SITES_CSV=/path/to/sites.csv to override.")
        import sys; sys.exit(1)

    sites = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in _csv_mod.DictReader(f):
            code   = row["Site"].strip().upper()
            subnet = row["Subnet"].strip()
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

SITES        = _load_sites()
SITE_OCTET   = {code: s["octet"]   for code, s in SITES.items() if s["octet"] is not None}
SITE_CITY    = {code: s["city"]    for code, s in SITES.items()}
SITE_COUNTRY = {code: s["country"] for code, s in SITES.items()}
SITE_SUBNETS = {code: s["subnet"]  for code, s in SITES.items() if s["subnet"] != "N/A"}
SITE_CODES   = set(SITES.keys())


ROLE_CODES = {
    "AST": "Atari ST (Retro Hardware)",
    "BPS": "Badge Programming Station",
    "CAM": "Security Camera",
    "CLK": "Time Clock / Punch Clock",
    "COF": "Coffee Machine",
    "DCS": "Domain Controller",
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
    "SYN": "Synthesizer (e.g. Moog)",
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

SERIAL_CONSOLE_ROLES = {"FWL", "RTR", "SBC", "PBX", "NIX"}

# =============================================================================
# BIOS ROM DESCRIPTIONS
# (mirrored from create-vm.py -- keep in sync)
# =============================================================================

ROM_DESCRIPTIONS = [
    ("WORKSTATION", "25H2", "DELL2.7", "BIOS.440", "Modded SeaBIOS -- Dell SLIC 2.7 / Win Server 2025 H2 SLP (legacy BIOS)"),
    ("WORKSTATION", "25H2", "DELL2.7", "EFI20-64", "Modded UEFI 2.0 64-bit -- Dell SLIC 2.7 / Win Server 2025 H2 SLP"),
    ("WORKSTATION", "25H2", "DELL2.7", "EFI64",    "Modded UEFI 64-bit -- Dell SLIC 2.7 / Win Server 2025 H2 SLP"),
    ("BIOS.440",    "",     "",        "",          "Stock SeaBIOS 440 (no SLIC -- standard QEMU BIOS)"),
    ("EFI20-64",    "",     "",        "",          "Stock UEFI 2.0 64-bit (no SLIC)"),
    ("EFI64",       "",     "",        "",          "Stock UEFI 64-bit (no SLIC)"),
]

def _describe_rom(filename):
    """Return a human-readable description for a ROM filename."""
    upper = filename.upper()
    for parts in ROM_DESCRIPTIONS:
        keywords = parts[:-1]
        desc = parts[-1]
        if all(k.upper() in upper or k == "" for k in keywords):
            return desc
    return "Custom ROM"
DUAL_NIC_ROLES        = {"FWL", "RTR"}
# Roles that are Windows-based VMs — triggers VirtIO ISO CDROM prompt
WINDOWS_ROLES         = {"DCS", "SRV", "SVR", "WKS", "LAP", "SUR"}

# =============================================================================
# COLOURS + OUTPUT HELPERS
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
    print(f"{C.Y}  {'=' * 60}{C.NC}")
    print(f"{C.W}  {title}{C.NC}")
    print(f"{C.Y}  {'=' * 60}{C.NC}")
    print()

def confirm(prompt_text, default="n"):
    yn = "y/N" if default == "n" else "Y/n"
    while True:
        resp = input(f"  {C.Y}{prompt_text} [{yn}]: {C.NC}").strip().lower()
        if resp == "":
            return default == "y"
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        print(f"  {C.R}Please enter y or n.{C.NC}")

def prompt(msg, default=None, validator=None, secret=False):
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

def prompt_int(msg, default, min_val, max_val):
    def validate(v):
        if not v.isdigit():
            return "Enter a whole number."
        if not (min_val <= int(v) <= max_val):
            return f"Enter a value between {min_val} and {max_val}."
        return True
    return int(prompt(msg, default=str(default), validator=validate))

# =============================================================================
# ARGUMENT PARSING
# =============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert VMware VMs to Proxmox using virt-v2v.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--host",         help="Proxmox host/IP")
    parser.add_argument("--port",         type=int, default=8006)
    parser.add_argument("--user",         help="Proxmox username (e.g. root@pam)")
    parser.add_argument("--token-name",   dest="token_name")
    parser.add_argument("--token-value",  dest="token_value")
    parser.add_argument("--password",     help="Password")
    parser.add_argument("--node",         help="Proxmox node name")
    parser.add_argument("--search-path",  dest="search_path",
                        default=os.getcwd(),
                        help="Directory to search for .vmx files (default: CWD)")
    parser.add_argument("--staging-dir",  dest="staging_dir",
                        default="/tmp/v2v-import",
                        help="Staging directory on Proxmox node (default: /tmp/v2v-import)")
    parser.add_argument("--ssh-user",     dest="ssh_user", default="root",
                        help="SSH username for remote mode (default: root)")
    parser.add_argument("--ssh-key",      dest="ssh_key",
                        help="SSH private key path for remote mode")
    parser.add_argument("--dry-run",      action="store_true", dest="dry_run")
    parser.add_argument("--bulk",         action="store_true")
    parser.add_argument("--log",          default=os.path.expanduser("~/pve-v2v-convert.log"))
    return parser.parse_args()

# =============================================================================
# MODE DETECTION
# =============================================================================

def detect_mode(host):
    """
    Determine execution mode — three possibilities:

    WORKSTATION (default)
        Script runs on a Linux workstation / jump host that is NOT the
        Proxmox node. virt-v2v runs locally here (fastest, cleanest).
        Only the converted qcow2 is uploaded to Proxmox — much smaller
        than shipping raw VMDKs across the network.

    LOCAL
        Script runs directly ON the Proxmox node.
        virt-v2v runs locally via subprocess; no uploads needed.

    REMOTE
        Script runs on a machine that does NOT have virt-v2v installed
        (e.g. a Windows Subsystem for Linux shell, or a minimal jump host).
        virt-v2v is invoked on the Proxmox node via SSH instead.
        Requires the raw VMDKs to be uploaded first.
    """
    try:
        local_ips = set()
        for addr_info in socket.getaddrinfo(socket.gethostname(), None):
            local_ips.add(addr_info[4][0])
        local_ips.add("127.0.0.1")
        local_ips.add("::1")

        target_ips = set()
        for addr_info in socket.getaddrinfo(host, None):
            target_ips.add(addr_info[4][0])

        if local_ips & target_ips:
            return "local"
    except Exception:
        pass

    # Not the Proxmox node — are we a capable workstation?
    if shutil.which("virt-v2v"):
        return "workstation"

    # virt-v2v not here — fall back to invoking it remotely over SSH
    return "remote"


# =============================================================================
# BINARY CHECKS
# =============================================================================

# Each entry: (binary, purpose, install_hint)
_BINARIES = {
    "workstation": [
        ("virt-v2v",       "VMware→KVM guest conversion",
         "apt install virt-v2v libguestfs-tools   # Debian/Ubuntu\n"
         "                    dnf install virt-v2v                       # RHEL/AlmaLinux\n"
         "                    pacman -S virt-v2v                         # Arch"),
        ("virt-customize", "Post-conversion guest disk surgery (boot fixes)",
         "apt install libguestfs-tools            # Debian/Ubuntu\n"
         "                    dnf install guestfs-tools                  # RHEL/AlmaLinux"),
        ("qemu-img",       "VMDK inspection and fallback conversion",
         "apt install qemu-utils                  # Debian/Ubuntu\n"
         "                    dnf install qemu-img                       # RHEL/AlmaLinux"),
        ("qemu-nbd",       "Expose VMDK as block device for NTFS dirty-flag check",
         "apt install qemu-utils                  # Debian/Ubuntu\n"
         "                    dnf install qemu-img                       # RHEL/AlmaLinux"),
        ("ntfsfix",        "Clear NTFS dirty flag before conversion",
         "apt install ntfs-3g                     # Debian/Ubuntu\n"
         "                    dnf install ntfs-3g                        # RHEL/AlmaLinux"),
        ("scp",            "Upload converted disk to Proxmox",
         "apt install openssh-client"),
        ("ssh",            "Remote command execution on Proxmox",
         "apt install openssh-client"),
    ],
    "local": [
        ("virt-v2v",       "VMware→KVM guest conversion",
         "apt install virt-v2v libguestfs-tools"),
        ("virt-customize", "Post-conversion guest disk surgery (boot fixes)",
         "apt install libguestfs-tools"),
        ("qemu-img",       "VMDK inspection and fallback conversion",
         "apt install qemu-utils"),
        ("qemu-nbd",       "Expose VMDK as block device for NTFS dirty-flag check",
         "apt install qemu-utils"),
        ("ntfsfix",        "Clear NTFS dirty flag before conversion",
         "apt install ntfs-3g"),
        ("qm",             "Proxmox VM management (disk import, config)",
         "Should be present on any Proxmox node — script will use sudo automatically"),
    ],
    "remote": [
        ("scp",        "Upload VMDK folder to Proxmox node",
         "apt install openssh-client"),
        ("ssh",        "Invoke virt-v2v on Proxmox node",
         "apt install openssh-client"),
        # virt-v2v and qm are checked on the remote side at runtime
    ],
}

# Known absolute paths for binaries that live outside standard PATH
# (e.g. /usr/sbin is not in PATH for non-root users on some distros)
_BINARY_FALLBACK_PATHS = {
    "qm":       ["/usr/sbin/qm",      "/sbin/qm"],
    "pvesh":    ["/usr/sbin/pvesh",   "/sbin/pvesh"],
    "pvesm":    ["/usr/sbin/pvesm",   "/sbin/pvesm"],
    "modprobe": ["/usr/sbin/modprobe","/sbin/modprobe"],
    "blockdev": ["/usr/sbin/blockdev","/sbin/blockdev"],
}

def _find_binary(name):
    """Return (path, via_fallback) for a binary, or (None, False) if not found.

    Checks shutil.which() first (respects PATH), then known absolute fallback
    paths for sbin tools that may not be on the ansible/non-root user's PATH.
    """
    path = shutil.which(name)
    if path:
        return path, False
    for candidate in _BINARY_FALLBACK_PATHS.get(name, []):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate, True
    return None, False


def check_binaries(mode):
    """
    Check required binaries are available for the given mode.
    Prints a clear table of found / missing, and exits if anything critical
    is absent (giving install hints).
    """
    section("BINARY / DEPENDENCY CHECK")

    required = _BINARIES.get(mode, [])
    if not required:
        info("No local binary checks defined for this mode.")
        return

    all_ok   = True
    missing  = []

    col_w = max(len(b[0]) for b in required) + 2

    for binary, purpose, hint in required:
        path, via_fallback = _find_binary(binary)
        if path:
            if via_fallback:
                ok(f"{binary:<{col_w}} {C.D}{path}{C.NC}  —  {purpose}  "
                   f"{C.Y}(not in PATH — found via absolute path, sudo will be used){C.NC}")
            else:
                ok(f"{binary:<{col_w}} {C.D}{path}{C.NC}  —  {purpose}")
        else:
            print(f"  {C.R}[X]{C.NC} {binary:<{col_w}} {C.R}NOT FOUND{C.NC}  —  {purpose}")
            missing.append((binary, hint))
            all_ok = False

    if missing:
        print()
        print(f"  {C.Y}The following required tools are missing:{C.NC}")
        print()
        for binary, hint in missing:
            print(f"  {C.R}  {binary}{C.NC}")
            print(f"  {C.D}    Install: {hint}{C.NC}")
            print()

        # virt-v2v missing in workstation mode is fatal — offer to switch
        if mode == "workstation" and any(b == "virt-v2v" for b, _ in missing):
            print(f"  {C.Y}virt-v2v is required for WORKSTATION mode.{C.NC}")
            print(f"  {C.CY}Options:{C.NC}")
            print(f"    {C.CY}1{C.NC}  Install virt-v2v and re-run  (recommended)")
            print(f"    {C.CY}2{C.NC}  Switch to REMOTE mode — virt-v2v runs on the Proxmox node via SSH")
            print()
            choice = prompt("How would you like to proceed?", default="1",
                            validator=lambda v: True if v in ("1", "2") else "Enter 1 or 2")
            if choice == "2":
                warn("Switching to REMOTE mode — virt-v2v will run on Proxmox node via SSH")
                warn("Raw VMDKs will be uploaded first (larger transfer than qcow2)")
                return "remote"
            else:
                err("Please install virt-v2v and re-run. See install hint above.")

        # scp/ssh missing is fatal regardless of mode
        if any(b in ("scp", "ssh") for b, _ in missing):
            err("scp and ssh are required — install openssh-client and re-run.")

        # qemu-img missing is a warning only — conversion can still proceed
        if all_ok is False and all(b == "qemu-img" for b, _ in missing):
            warn("qemu-img not found — fallback conversion method unavailable, continuing anyway")
            return mode

    else:
        ok("All required binaries present")

    return mode

# =============================================================================
# VMX DISCOVERY
# =============================================================================

def find_vmx_files(search_path):
    """
    Recursively find all .vmx files under search_path.
    Returns list of absolute paths.
    """
    found = []
    for root, dirs, files in os.walk(search_path):
        # Skip VMware snapshot/autosave directories
        dirs[:] = [d for d in dirs if d not in ("caches", ".lck", "autoprotect")]
        for f in files:
            if f.lower().endswith(".vmx"):
                found.append(os.path.join(root, f))
    return sorted(found)

def select_vmx(search_path):
    """
    Find .vmx files in search_path and prompt user to select one.
    Returns the selected .vmx path.
    """
    section("LOCATE SOURCE VM")
    info(f"Searching for .vmx files in: {search_path}")

    vmx_files = find_vmx_files(search_path)

    if not vmx_files:
        print()
        warn(f"No .vmx files found under {search_path}")
        print()
        custom = prompt("Enter full path to .vmx file manually")
        if not os.path.isfile(custom):
            err(f"File not found: {custom}")
        return custom

    print()
    print(f"  {C.W}Found {len(vmx_files)} VMX file(s):{C.NC}")
    print()
    for i, path in enumerate(vmx_files, 1):
        size_mb = _dir_size_mb(os.path.dirname(path))
        print(f"  {C.CY}  {i}{C.NC}  {os.path.basename(path):<40} "
              f"{C.D}({path}){C.NC}  [{size_mb}MB total]{C.NC}")
    print()

    def validate(v):
        if v.isdigit() and 1 <= int(v) <= len(vmx_files):
            return True
        return f"Enter a number between 1 and {len(vmx_files)}"

    choice = int(prompt("Select VMX to convert", default="1", validator=validate))
    selected = vmx_files[choice - 1]
    ok(f"Selected: {selected}")
    return selected

def _dir_size_mb(path):
    total = 0
    try:
        for root, dirs, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    except Exception:
        pass
    return round(total / 1024 / 1024, 1)

# =============================================================================
# VMX PARSING
# =============================================================================

def parse_vmx(vmx_path):
    """
    Parse a VMware .vmx file into a flat dict of key → value.
    VMX format: key = "value"  (values quoted, keys case-insensitive)
    """
    config = {}
    try:
        with open(vmx_path, "r", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip().lower()
                val = val.strip().strip('"')
                config[key] = val
    except Exception as e:
        err(f"Failed to read VMX file: {e}")
    return config

def extract_hardware(vmx, vmx_path):
    """
    Extract hardware config from parsed VMX dict.
    Returns a dict with: display_name, cpus, ram_mb, disk_paths, nics, os_guess
    """
    # --- Name ---
    display_name = vmx.get("displayname", os.path.splitext(os.path.basename(vmx_path))[0])

    # --- CPU ---
    # VMX uses numvcpus for total vCPUs; no socket/core split in VMX itself
    total_vcpus = int(vmx.get("numvcpus", vmx.get("numcpu", "1")))

    # --- RAM ---
    ram_mb = int(vmx.get("memsize", "2048"))

    # --- Disks ---
    # Find all scsiN:M.filename entries — these are the VMDKs
    disk_paths = []
    vmx_dir = os.path.dirname(vmx_path)
    disk_pattern = re.compile(r"^(scsi|ide|sata|nvme)\d+:\d+\.filename$")
    for key, val in vmx.items():
        if disk_pattern.match(key):
            if val.lower().endswith(".vmdk"):
                # Resolve relative paths against VMX directory
                full = val if os.path.isabs(val) else os.path.join(vmx_dir, val)
                disk_paths.append(full)

    # --- NICs ---
    # ethernet0.present, ethernet0.virtualdev, ethernet0.connectiontype etc.
    nics = []
    nic_indices = set()
    nic_pattern = re.compile(r"^ethernet(\d+)\.")
    for key in vmx.keys():
        m = nic_pattern.match(key)
        if m:
            nic_indices.add(int(m.group(1)))

    for idx in sorted(nic_indices):
        present = vmx.get(f"ethernet{idx}.present", "false").lower()
        if present != "true":
            continue
        vdev = vmx.get(f"ethernet{idx}.virtualdev", "e1000")
        conn = vmx.get(f"ethernet{idx}.connectiontype", "nat")
        mac  = vmx.get(f"ethernet{idx}.generatedaddress",
               vmx.get(f"ethernet{idx}.address", ""))
        nics.append({
            "vmware_index": idx,
            "virtualdev":   vdev,
            "connectiontype": conn,
            "mac":          mac,
        })

    # --- OS guess ---
    # Maps to Proxmox ostype enum. Valid values: l24, l26, other, solaris,
    # w2k, w2k3, w2k8, win7, win8, win10, win11, wvista, wxp
    # NOTE: w2k12/w2k16/w2k19/w2k22 do NOT exist.
    # win10 = Win10/Server2016/2019; win11 = Win11/Server2022/2025
    guest_os = vmx.get("guestos", "").lower()
    if "debian" in guest_os or "ubuntu" in guest_os or "rhel" in guest_os \
            or "centos" in guest_os or "rocky" in guest_os or "alma" in guest_os:
        os_guess = "l26"
    elif "windows9" in guest_os or "win10" in guest_os:
        os_guess = "win10"
    elif "windows2019srvnext" in guest_os or "windows2022" in guest_os \
            or "win11" in guest_os:
        # VMware uses "windows2019srvnext-64" for Server 2022 — maps to win11
        os_guess = "win11"
    elif "windows8" in guest_os or "server2012" in guest_os:
        os_guess = "win8"
    elif "windows7" in guest_os or "server2008" in guest_os:
        os_guess = "win7"
    elif "windowsxp" in guest_os or "server2003" in guest_os:
        os_guess = "wxp"
    elif "windows" in guest_os or "win" in guest_os:
        # Default for any unrecognised Windows: win10 covers 2016/2019,
        # win11 covers 2022/2025 -- caller can override in the OS prompt
        os_guess = "win10"
    elif "solaris" in guest_os or "freebsd" in guest_os or "openbsd" in guest_os:
        os_guess = "other"
    else:
        os_guess = "l26"

    return {
        "display_name": display_name,
        "total_vcpus":  total_vcpus,
        "ram_mb":       ram_mb,
        "disk_paths":   disk_paths,
        "nics":         nics,
        "os_guess":     os_guess,
        "guest_os_raw": vmx.get("guestos", "unknown"),
    }

def print_vmx_summary(hw):
    """Print what was found in the VMX."""
    print()
    print(f"  {C.W}Parsed from VMX:{C.NC}")
    print(f"    {C.CY}Display name  :{C.NC} {hw['display_name']}")
    print(f"    {C.CY}Guest OS (raw):{C.NC} {hw['guest_os_raw']}")
    print(f"    {C.CY}OS type guess :{C.NC} {hw['os_guess']}")
    print(f"    {C.CY}vCPUs         :{C.NC} {hw['total_vcpus']}")
    print(f"    {C.CY}RAM           :{C.NC} {hw['ram_mb']} MB")
    print()
    if hw["disk_paths"]:
        print(f"    {C.CY}Disk(s):{C.NC}")
        for i, d in enumerate(hw["disk_paths"]):
            exists = f"{C.G}found{C.NC}" if os.path.isfile(d) else f"{C.R}NOT FOUND{C.NC}"
            size_mb = round(os.path.getsize(d) / 1024 / 1024, 1) if os.path.isfile(d) else 0
            print(f"      {i+1}.  {d}  [{exists}]  {size_mb}MB on disk")
    else:
        print(f"    {C.Y}No VMDK disk paths found in VMX — check manually{C.NC}")
    print()
    if hw["nics"]:
        print(f"    {C.CY}NIC(s) detected:{C.NC}")
        for nic in hw["nics"]:
            print(f"      eth{nic['vmware_index']}  type={nic['virtualdev']}  "
                  f"conn={nic['connectiontype']}  mac={nic['mac'] or 'auto'}")
    else:
        print(f"    {C.Y}No NICs found in VMX{C.NC}")
    print()

# =============================================================================
# NIC ADVISORY
# =============================================================================

NIC_ADVISORY = """
  {Y}+-- NIC NAMING ADVISORY -----------------------------------------------+{NC}
  {Y}|{NC}                                                                      {Y}|{NC}
  {Y}|{NC}  VMware presents NICs as  ens33, ens34, etc.                         {Y}|{NC}
  {Y}|{NC}  Proxmox/virtio presents  enp6s18, enp7s18 — or eth0/eth1           {Y}|{NC}
  {Y}|{NC}  depending on udev rules and kernel parameters.                      {Y}|{NC}
  {Y}|{NC}                                                                      {Y}|{NC}
  {Y}|{NC}  After first boot, the guest's /etc/network/interfaces               {Y}|{NC}
  {Y}|{NC}  (Debian) or /etc/netplan/*.yaml (Ubuntu) may reference the         {Y}|{NC}
  {Y}|{NC}  OLD VMware NIC names — causing a silent no-network boot.            {Y}|{NC}
  {Y}|{NC}                                                                      {Y}|{NC}
  {Y}|{NC}  REMEDIATION OPTIONS (choose one):                                   {Y}|{NC}
  {Y}|{NC}                                                                      {Y}|{NC}
  {Y}|{NC}  1. {W}Force old-style names{NC} — add to GRUB before converting:         {Y}|{NC}
  {Y}|{NC}     Edit /etc/default/grub on the SOURCE VM:                        {Y}|{NC}
  {Y}|{NC}     GRUB_CMDLINE_LINUX="net.ifnames=0 biosdevname=0"                {Y}|{NC}
  {Y}|{NC}     Then: update-grub                                               {Y}|{NC}
  {Y}|{NC}     This restores eth0/eth1 naming — best if scripts hardcode NICs  {Y}|{NC}
  {Y}|{NC}                                                                      {Y}|{NC}
  {Y}|{NC}  2. {W}Fix after migration{NC} — on first boot via console:               {Y}|{NC}
  {Y}|{NC}     ip link show   (find new name)                                  {Y}|{NC}
  {Y}|{NC}     sed -i 's/ens33/enp6s18/g' /etc/network/interfaces             {Y}|{NC}
  {Y}|{NC}     systemctl restart networking                                    {Y}|{NC}
  {Y}|{NC}                                                                      {Y}|{NC}
  {Y}|{NC}  3. {W}WireGuard / firewallme.sh users{NC} — also update the systemd      {Y}|{NC}
  {Y}|{NC}     drop-in override.conf BindsTo= and After= interface names.      {Y}|{NC}
  {Y}|{NC}     See NET-VPN-WG-001 for the full procedure.                      {Y}|{NC}
  {Y}|{NC}                                                                      {Y}|{NC}
  {Y}+----------------------------------------------------------------------+{NC}
"""

def show_nic_advisory(hw):
    """Display NIC rename advisory if the source has more than one NIC,
    or if it's a firewall/router role."""
    formatted = NIC_ADVISORY.format(Y=C.Y, NC=C.NC, W=C.W)
    print(formatted)
    print()

# =============================================================================
# PROXMOX CONNECTION  (identical pattern to create-vm.py)
# =============================================================================

def connect(args):
    host = args.host or prompt("Proxmox host/IP")
    port = args.port
    user = args.user or prompt("Proxmox username (e.g. root@pam)", default="root@pam")

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
        choice = prompt("Select", default="1",
                        validator=lambda v: True if v in ("1", "2") else "Enter 1 or 2")
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
            proxmox = ProxmoxAPI(host, port=port, user=user,
                                 token_name=token_name, token_value=token_value,
                                 verify_ssl=False)
        else:
            proxmox = ProxmoxAPI(host, port=port, user=user,
                                 password=password, verify_ssl=False)
        proxmox.version.get()
        ok(f"Connected to {host}:{port}")
        return proxmox, host
    except Exception as e:
        err(f"Connection failed: {e}")

def select_node(proxmox, args):
    nodes = proxmox.nodes.get()
    if not nodes:
        err("No nodes found.")
    if args.node:
        names = [n["node"] for n in nodes]
        if args.node not in names:
            err(f"Node '{args.node}' not found. Available: {', '.join(names)}")
        ok(f"Node: {args.node}")
        return args.node
    if len(nodes) == 1:
        node = nodes[0]["node"]
        ok(f"Single node: {node}")
        return node
    print()
    print(f"  {C.W}Available nodes:{C.NC}")
    for i, n in enumerate(nodes, 1):
        status  = f"{C.G}online{C.NC}" if n.get("status") == "online" else f"{C.R}{n.get('status','?')}{C.NC}"
        mem_gb  = round(n.get("maxmem", 0) / 1024**3, 1)
        print(f"  {C.CY}  {i}{C.NC}  {n['node']}  ({status}, {mem_gb}GB RAM)")
    print()
    def validate_node(v):
        return True if (v.isdigit() and 1 <= int(v) <= len(nodes)) else f"Enter 1–{len(nodes)}"
    choice = int(prompt("Select node", validator=validate_node))
    return nodes[choice - 1]["node"]

# =============================================================================
# EXISTING VM HELPERS  (ported from create-vm.py)
# =============================================================================

def get_existing_vms(proxmox, node):
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
    err(f"All 999 names for {prefix} are taken.")

# =============================================================================
# NAMING  (role + site selection, identical UX to create-vm.py)
# =============================================================================

def select_role(suggested=None):
    print()
    print(f"  {C.W}Role codes:{C.NC}")
    codes = sorted(ROLE_CODES.keys())
    for i in range(0, len(codes), 3):
        row = codes[i:i+3]
        line = ""
        for code in row:
            line += f"  {C.CY}{code:4}{C.NC}  {ROLE_CODES[code]:<40}"
        print(f"  {line}")
    print()
    if suggested:
        info(f"Suggested role based on VMX guest OS: {C.W}{suggested}{C.NC}")
    def validate_role(v):
        return True if v.upper() in ROLE_CODES else "Unknown role code."
    role = prompt("Role code (e.g. FWL, NIX, SRV)", default=suggested, validator=validate_role)
    return role.upper()

def select_site(suggested=None):
    print()
    print(f"  {C.W}Known site codes:{C.NC}")
    codes = sorted(SITE_OCTET.keys())
    for i in range(0, len(codes), 6):
        row = codes[i:i+6]
        line = "  ".join(f"{C.CY}{c}{C.NC} {SITE_CITY.get(c,'?'):<18}" for c in row)
        print(f"    {line}")
    print()
    if suggested:
        info(f"Suggested site based on VM name: {C.W}{suggested}{C.NC}  ({SITE_CITY.get(suggested,'?')})")
    def validate_site(v):
        return True if v.upper() in SITE_OCTET else "Unknown site code."
    site = prompt("Site code (e.g. FAL, LND, BRK)", default=suggested, validator=validate_site)
    return site.upper()

def guess_role_from_vmx(hw):
    """
    Guess role code from display name and guest OS.

    Priority order:
    1. EXA naming convention EXARRRSSS### - extract RRR directly (authoritative)
    2. Word-boundary keyword matching on display name
    3. Guest OS fallback
    4. Default: SRV
    """
    name  = hw["display_name"].upper().strip()
    guest = hw["guest_os_raw"].lower()

    # 1. EXA naming - EXARRRSSS### e.g. EXADCSCPH001 -> DCS
    import re as _re
    m = _re.match(r"^EXA([A-Z]{3})[A-Z]{3}\d{3}$", name)
    if m:
        role = m.group(1)
        if role in ROLE_CODES:
            return role

    # 2. Word-boundary keyword matching
    keyword_map = [
        (r"\bFWL\b|\bFIREWALL\b",         "FWL"),
        (r"\bRTR\b|\bROUTER\b",            "RTR"),
        (r"\bDCS\b|\bDC\b|\bDOMAIN\b",   "DCS"),
        (r"\bPVE\b|\bPROXMOX\b",           "PVE"),
        (r"\bNAS\b",                          "NAS"),
        (r"\bPBX\b",                          "PBX"),
        (r"\bSBC\b",                          "SBC"),
        (r"\bWAP\b",                          "WAP"),
        (r"\bSWI\b|\bSWITCH\b",            "SWI"),
        (r"\bNIX\b|\bLINUX\b",             "NIX"),
        (r"\bSRV\b|\bSERVER\b",            "SRV"),
    ]
    for pattern, role in keyword_map:
        if _re.search(pattern, name):
            return role

    # 3. Guest OS fallback
    if "debian" in guest or "ubuntu" in guest or "rhel" in guest \
            or "centos" in guest or "rocky" in guest or "alma" in guest:
        return "NIX"
    if "windows" in guest or "win" in guest:
        return "SRV"

    return "SRV"


def guess_site_from_vmx(hw, vmx_path):
    """
    Guess site code from display name or VMX path.

    1. EXA naming EXARRRSSS### -> SSS (authoritative)
    2. Scan name/path for known site codes
    Returns site code string or None.
    """
    import re as _re
    name = hw["display_name"].upper().strip()

    # 1. EXA naming e.g. EXADCSCPH001 -> CPH
    m = _re.match(r"^EXA[A-Z]{3}([A-Z]{3})\d{3}$", name)
    if m:
        site = m.group(1)
        if site in SITE_OCTET:
            return site

    # 2. Scan name and path for known site codes
    candidates = [name, os.path.basename(vmx_path).upper(),
                  os.path.dirname(vmx_path).upper()]
    for text in candidates:
        for site in SITE_OCTET:
            if _re.search(rf"\b{site}\b", text):
                return site

    return None

# =============================================================================
# STORAGE SELECTION
# =============================================================================

# Storage types that require raw format (block-based, no file container support)
_BLOCK_STORAGE_TYPES = {"zfspool", "lvmthin", "lvm", "rbd", "sheepdog"}

# Human-readable labels for storage types
_STORAGE_TYPE_LABELS = {
    "dir":       "Directory",
    "zfspool":   "ZFS Pool",
    "lvmthin":   "LVM-Thin",
    "lvm":       "LVM",
    "nfs":       "NFS",
    "cifs":      "CIFS/SMB",
    "rbd":       "Ceph RBD",
    "btrfs":     "Btrfs",
    "glusterfs": "GlusterFS",
    "sheepdog":  "Sheepdog",
}

def get_disk_format(storage_type):
    """
    Return the correct virt-v2v / qm importdisk format for a storage type.
    Block-based storage (ZFS, LVM, Ceph) requires raw.
    File-based storage (dir, NFS, CIFS, Btrfs) can use qcow2.
    """
    if storage_type in _BLOCK_STORAGE_TYPES:
        return "raw"
    return "qcow2"

def select_storage(proxmox, node):
    """
    List image-capable storage on the node, prompt for selection.
    Returns (storage_name, storage_type, disk_format).
    """
    try:
        stores = proxmox.nodes(node).storage.get(content="images")
    except Exception as e:
        err(f"Failed to query storage: {e}")
    if not stores:
        err("No image-capable storage found on this node.")
    stores = sorted(stores, key=lambda s: s["storage"])
    print()
    print(f"  {C.W}Available storage:{C.NC}")
    for i, s in enumerate(stores, 1):
        avail_gb  = round(s.get("avail", 0) / 1024**3, 1)
        total_gb  = round(s.get("total", 0) / 1024**3, 1)
        stype     = s.get("type", "?")
        label     = _STORAGE_TYPE_LABELS.get(stype, stype)
        fmt       = get_disk_format(stype)
        active    = f"{C.G}active{C.NC}" if s.get("active") else f"{C.R}inactive{C.NC}"
        fmt_note  = f"{C.Y}raw{C.NC}" if fmt == "raw" else f"{C.D}qcow2{C.NC}"
        print(f"  {C.CY}  {i}{C.NC}  {s['storage']:<20} {label:<14} "
              f"{avail_gb}GB free of {total_gb}GB  fmt={fmt_note}  [{active}]")
    print()
    info("fmt=raw  → ZFS/LVM/Ceph block storage   (zvol/logical volume)")
    info("fmt=qcow2→ Directory/NFS file storage    (supports snapshots)")
    print()
    def validate_storage(v):
        return True if (v.isdigit() and 1 <= int(v) <= len(stores)) else f"Enter 1–{len(stores)}"
    choice       = int(prompt("Select storage for imported disk", validator=validate_storage))
    selected     = stores[choice - 1]
    storage_name = selected["storage"]
    storage_type = selected.get("type", "dir")
    disk_format  = get_disk_format(storage_type)
    avail_gb     = round(selected.get("avail", 0) / 1024**3, 1)
    ok(f"Storage : {storage_name}  ({_STORAGE_TYPE_LABELS.get(storage_type, storage_type)})")
    ok(f"Format  : {disk_format}  ({'block device — raw required' if disk_format == 'raw' else 'file-based — qcow2 supported'})")
    ok(f"Free    : {avail_gb} GB available")
    return storage_name, storage_type, disk_format

# =============================================================================
# POOL SELECTION
# =============================================================================

def select_pool(proxmox, site):
    try:
        pools    = proxmox.pools.get()
        pool_ids = sorted(p["poolid"] for p in pools)
    except Exception:
        info("Could not enumerate pools — skipping")
        return None
    if not pool_ids:
        info("No pools defined — skipping")
        return None
    site_match   = next((p for p in pool_ids if site.upper() in p.upper()), None)
    default_pool = site_match or ""
    info(f"Available pools: {', '.join(pool_ids)}")
    if default_pool:
        info(f"Pool matching site {site}: {C.W}{default_pool}{C.NC}")
    def validate_pool(v):
        return True if (v == "" or v in pool_ids) else f"Unknown pool '{v}'"
    raw  = prompt("Pool (blank = none)", default=default_pool, validator=validate_pool)
    pool = raw.strip() or None
    ok(f"Pool: {pool or 'none'}")
    return pool

# =============================================================================
# VIRTIO ISO SELECTION  (Windows VMs only)
# =============================================================================

def select_virtio_iso(proxmox, node, role, drivers_ready=False):
    """For Windows roles, offer to attach the VirtIO ISO as ide2 (CDROM).
    Returns volid string or None.

    Context for V2V conversions:
        virt-v2v auto-injects drivers from /usr/share/virtio-win/ if that
        directory is present and populated (see first-boot.sh Step 3c).
        In that case the CDROM is a convenience fallback, not critical.

        If /usr/share/virtio-win/ is absent or empty, the CDROM is the
        primary mechanism for driver injection:
          - Offline: boot to recovery console, run
              dism /image:C:\\ /add-driver /driver:D:\\ /recurse
          - Online: install via Device Manager after first boot
              (requires disabling Secure Boot and driver signing first)

    The ISO must be present at /var/lib/vz/template/iso/ on the Proxmox node.
    See first-boot.sh Step 3c for the download + extraction procedure.
    """
    if role not in WINDOWS_ROLES:
        return None

    section("VIRTIO DRIVERS ISO (CDROM)")

    if drivers_ready:
        info(f"VirtIO drivers are extracted at {VIRTIO_WIN_DIR}/ —")
        info("virt-v2v will inject them automatically during conversion.")
        info("The CDROM is still useful as a fallback for:")
        info("  - Guest Agent / balloon driver MSI installation post-boot")
        info("  - Manual driver install if auto-injection reports missing drivers")
        info("  - Offline DISM injection from recovery console if boot fails")
    else:
        warn(f"VirtIO drivers NOT extracted — CDROM is the primary injection method.")
        warn("Attach it and use the Windows recovery console:")
        warn("  dism /image:C:\\ /add-driver /driver:D:\\ /recurse")
        warn("Or install drivers online after first boot (disable Secure Boot + signing).")
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
        warn("No ISOs found in local storage.")
        warn("Download the VirtIO ISO to the Proxmox node:")
        warn("  wget -O /var/lib/vz/template/iso/virtio-win.iso \\")
        warn("    https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso")
        warn("Then re-run this step or attach it manually in the Proxmox UI.")
        return None

    # Prefer virtio-win ISO by name
    default_candidate = next(
        (c for c in candidates if "virtio" in c.lower()),
        None
    )

    print(f"  {'#':<4}  {'Volume ID'}")
    print(f"  {'-'*4}  {'-'*55}")
    for i, volid in enumerate(candidates, 1):
        marker = f"  {C.G}← virtio-win{C.NC}" if volid == default_candidate else ""
        print(f"  {C.CY}{i:<4}{C.NC}  {volid}{marker}")
    print(f"  {C.CY}0   {C.NC}  Skip — no ISO (attach manually later)")
    print()

    # Default: attach if drivers NOT ready (critical), skip if they are (optional)
    if default_candidate:
        default_idx = str(candidates.index(default_candidate) + 1)
    elif not drivers_ready:
        default_idx = "1" if candidates else "0"
    else:
        default_idx = "0"

    def validate_iso_choice(v):
        if not v.isdigit():
            return "Enter a number"
        v = int(v)
        if 0 <= v <= len(candidates):
            return True
        return f"Enter 0–{len(candidates)}"

    choice = int(prompt(f"Select VirtIO ISO [0–{len(candidates)}]",
                        default=default_idx,
                        validator=validate_iso_choice))

    if choice == 0:
        if not drivers_ready:
            warn("No VirtIO ISO attached — you WILL need to inject drivers manually.")
            warn("See bootstrapping.d for the offline DISM procedure.")
        else:
            ok("No VirtIO ISO attached — auto-injection should handle drivers.")
        return None

    selected = candidates[choice - 1]
    ok(f"VirtIO ISO: {selected}")
    return selected


# =============================================================================
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
        print(f"  {C.D}  After reboot: boot menu on serial, then SAC prompt. From SAC:{C.NC}")
        print(f"  {C.CY}    SAC> cmd{C.NC}             {C.D}# open CMD channel{C.NC}")
        print(f"  {C.CY}    SAC> ch -sn Cmd0001{C.NC}  {C.D}# switch to it, authenticate{C.NC}")
        print(f"  {C.CY}    C:\\> powershell{C.NC}     {C.D}# full PowerShell over serial{C.NC}")
        print()
        print(f"  {C.D}  Join-DomainAndBootstrap.ps1 Stage 17b does this automatically.{C.NC}")
        print(f"  {C.D}  See NET-BMC-001 Section 4b for full walkthrough.{C.NC}")
    else:
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
# BIOS ROM SELECTION  (V2V variant)
# =============================================================================

def select_bios_rom_v2v(proxmox, node):
    """
    V2V variant of BIOS ROM selection.

    Default is no custom ROM -- the converted VM boots with standard SeaBIOS.
    A custom ROM is useful if:
      - The source was a physical server and you want SLP/SLIC activation
      - You are converting a VMware VM that had a modded BIOS for activation

    The physical server's original BIOS/UEFI does not carry over in V2V --
    virt-v2v converts the disk only, not the firmware. This is your chance
    to add a custom ROM to the new VM.
    """
    print()
    print(f"  {C.W}BIOS ROM (optional):{C.NC}")
    print(f"  {C.D}virt-v2v converts the disk only -- the source firmware does not carry over.{C.NC}")
    print(f"  {C.D}A custom ROM can add SLIC/SLP activation to the converted VM.{C.NC}")
    print(f"  {C.D}Default: no custom ROM (standard SeaBIOS -- safe for all VM types).{C.NC}")
    print()

    roms = []
    try:
        result = proxmox.nodes(node).execute.post(
            command="ls /usr/share/kvm/*.ROM /usr/share/kvm/*.rom 2>/dev/null || true"
        )
        lines = result.get("data", "").strip().splitlines() if isinstance(result, dict) else str(result).strip().splitlines()
        roms = [l.strip() for l in lines if l.strip() and "ROM" in l.upper()]
    except Exception:
        pass

    if not roms:
        roms = [
            "/usr/share/kvm/WORKSTATION_25H2_DELL2.7_BIOS.440.ROM",
            "/usr/share/kvm/WORKSTATION_25H2_DELL2.7_EFI20-64.ROM",
            "/usr/share/kvm/WORKSTATION_25H2_DELL2.7_EFI64.ROM",
            "/usr/share/kvm/BIOS.440.ROM",
            "/usr/share/kvm/EFI20-64.ROM",
            "/usr/share/kvm/EFI64.ROM",
        ]

    print(f"  {C.CY}  0{C.NC}  No custom ROM  (default -- standard SeaBIOS)")
    print()
    for i, path in enumerate(roms, 1):
        fname = path.split("/")[-1]
        desc  = _describe_rom(fname)
        btype = "EFI" if any(x in fname.upper() for x in ("EFI", "OVMF", "UEFI")) else "SeaBIOS"
        print(f"  {C.CY}  {i}{C.NC}  [{btype}]  {fname}")
        print(f"       {C.D}{desc}{C.NC}")
    print()

    def validate_rom(v):
        return True if v.isdigit() and 0 <= int(v) <= len(roms) else f"Enter 0 to {len(roms)}"

    # Default 0 -- no custom ROM is the right default for V2V
    choice = int(prompt("Select BIOS ROM", default="0", validator=validate_rom))
    if choice == 0:
        ok("BIOS ROM: default SeaBIOS (no custom ROM)")
        return "seabios", None

    selected = roms[choice - 1]
    fname    = selected.split("/")[-1]
    is_efi   = any(x in fname.upper() for x in ("EFI", "OVMF", "UEFI"))
    ok(f"BIOS ROM: {fname}  ({_describe_rom(fname)})")
    return "ovmf" if is_efi else "seabios", selected


# =============================================================================
# BMC / IPMI EMULATION SELECTION  (V2V variant)
# =============================================================================

def select_bmc_v2v(role, hw):
    """
    V2V variant of BMC selection.

    Physical servers have real iDRAC/iLO. When converting to a VM we can
    restore equivalent out-of-band access via proxmoxbmc + ipmi-bmc-sim.

    Default is No -- most migrations don't need it immediately and it can
    always be added later by editing the VM's args in Proxmox. However for
    server roles (DCS, SRV, APP, FSR etc.) that came from physical hardware
    it is worth considering.

    Only KCS is offered -- there is no practical reason to choose BT in a
    V2V migration context.
    """
    print()
    print(f"  {C.W}BMC / IPMI emulation (optional):{C.NC}")
    print(f"  {C.D}Physical servers have iDRAC/iLO. This adds equivalent out-of-band{C.NC}")
    print(f"  {C.D}access to the converted VM via proxmoxbmc + ipmi-bmc-sim.{C.NC}")
    print(f"  {C.D}Gives the guest /dev/ipmi0 and enables ipmitool SOL serial console.{C.NC}")
    print(f"  {C.D}Requires proxmoxbmc installed on the Proxmox node (see NET-BMC-001).{C.NC}")
    print(f"  {C.D}Can be added later: edit VM args in Proxmox UI or via qm set.{C.NC}")
    print()

    # Suggest yes for server roles that would have had physical BMCs
    SERVER_ROLES = {"DCS", "SRV", "APP", "FSR", "SQL", "WEB", "MON", "ANS"}
    suggested = role.upper() in SERVER_ROLES
    default   = "y" if suggested else "n"

    if suggested:
        info(f"Role {role} is a server role -- BMC emulation recommended (defaulting to yes)")
    else:
        info(f"Role {role} -- BMC emulation optional (defaulting to no)")

    print()
    choice = prompt(f"Add BMC/IPMI emulation? [{'Y/n' if suggested else 'y/N'}]",
                    default=default,
                    validator=lambda v: True if v.lower() in ("y","n","yes","no","") else "Enter y or n")

    if choice.lower() in ("y", "yes"):
        ok("BMC: KCS IPMI interface (ipmi-bmc-sim) -- register with proxmoxbmc after import")
        return "kcs"
    else:
        ok("BMC: None")
        return None


# CONSOLE SELECTION
# =============================================================================

def select_console(role):
    default_combo = role in SERIAL_CONSOLE_ROLES
    print()
    print(f"  {C.W}Console type:{C.NC}")
    print(f"  {C.CY}  1{C.NC}  VGA only")
    print(f"  {C.CY}  2{C.NC}  VGA + Serial  (boot via VGA, OS console via ttyS0 — recommended for appliances)")
    print(f"  {C.CY}  3{C.NC}  Serial only   (fully headless)")
    print()
    default = "2" if default_combo else "1"
    choice  = prompt("Select console", default=default,
                     validator=lambda v: True if v in ("1", "2", "3") else "Enter 1, 2 or 3")
    mapping = {"1": "vga", "2": "both", "3": "serial"}
    result  = mapping[choice]
    ok(f"Console: {result}")
    return result

# =============================================================================
# NIC CONFIGURATION  (with rename advisory baked in)
# =============================================================================

def configure_nics(role, site, hw):
    """
    Build Proxmox NIC list.
    Shows the rename advisory, proposes a layout based on role + number of
    VMware NICs, lets user confirm or override.
    Offers MAC preservation — carries VMware MACs into Proxmox NIC config
    to avoid disrupting DHCP reservations, WireGuard peers, udev rules etc.
    """
    section("NETWORK CONFIGURATION")

    show_nic_advisory(hw)

    octet   = SITE_OCTET[site]
    vlan_id = octet
    dual    = (role in DUAL_NIC_ROLES) or (len(hw["nics"]) >= 2)

    if dual:
        info(f"Source VM has {len(hw['nics'])} NIC(s) — proposing dual-NIC layout:")
        info(f"  net0  vmbr0  untagged      (WAN / provisioning)")
        info(f"  net1  vmbr1  VLAN {vlan_id:<5}   (LAN — {site} site, 192.168.{octet}.0/24)")
    else:
        info(f"Source VM has {len(hw['nics'])} NIC(s) — proposing single-NIC layout:")
        info(f"  net0  vmbr1  VLAN {vlan_id:<5}   ({site} site, 192.168.{octet}.0/24)")

    print()
    if not confirm("Accept this NIC layout?", default="y"):
        warn("NIC layout skipped — configure NICs manually after creation.")
        return []

    # ── MAC preservation ──────────────────────────────────────────────────────
    # Default yes — for migrations you almost always want to keep MACs.
    # Changing MAC breaks: DHCP reservations, WireGuard peer routing,
    # udev persistent-net rules, any software keyed to MAC address.
    vmware_macs = [n["mac"] for n in hw["nics"] if n.get("mac")]
    preserve_mac = False
    if vmware_macs:
        print()
        info("VMware MAC addresses detected:")
        for i, n in enumerate(hw["nics"]):
            if n.get("mac"):
                info(f"  eth{n['vmware_index']}  {n['mac']}")
        print()
        warn("Preserving MACs is recommended — changing them breaks DHCP reservations,")
        warn("WireGuard peer routing, and any udev/software keyed to MAC address.")
        print()
        preserve_mac = confirm("Preserve VMware MAC addresses?", default="y")
    else:
        info("No VMware MACs found in VMX — Proxmox will assign random MACs.")

    nics = []
    if dual:
        nics.append({"id": "net0", "model": "virtio", "bridge": "vmbr0",
                     "vlan": None,    "mac": None, "desc": "WAN / provisioning (untagged)"})
        nics.append({"id": "net1", "model": "virtio", "bridge": "vmbr1",
                     "vlan": vlan_id, "mac": None, "desc": f"LAN — {site} site VLAN {vlan_id}"})
    else:
        nics.append({"id": "net0", "model": "virtio", "bridge": "vmbr1",
                     "vlan": vlan_id, "mac": None, "desc": f"{site} site VLAN {vlan_id}"})

    # Assign MACs from VMX in order if preserving
    if preserve_mac:
        for i, nic in enumerate(nics):
            if i < len(hw["nics"]) and hw["nics"][i].get("mac"):
                nic["mac"] = hw["nics"][i]["mac"]
                ok(f"{nic['id']}: preserving MAC {nic['mac']}")
            else:
                warn(f"{nic['id']}: no VMware MAC available — Proxmox will assign randomly")

    for nic in nics:
        vlan_str = f"tag={nic['vlan']}" if nic["vlan"] else "untagged"
        mac_str  = f"  mac={nic['mac']}" if nic["mac"] else "  mac=auto"
        ok(f"{nic['id']}  {nic['bridge']}  {vlan_str:<12}  virtio{mac_str}  — {nic['desc']}")
    return nics

# =============================================================================
# REMOTE MODE — FILE UPLOAD
# =============================================================================

def build_ssh_base(host, ssh_user, ssh_key):
    """Return base ssh/scp argument lists."""
    base = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes"]
    if ssh_key:
        base += ["-i", ssh_key]
    return base

def upload_vm_folder(vmx_path, host, ssh_user, ssh_key, staging_dir, dry_run=False):
    """
    Upload the entire VM folder (containing the VMX and VMDK) to
    staging_dir on the remote Proxmox node via scp -r.
    Returns the remote VMX path.
    """
    section("UPLOAD VM TO PROXMOX NODE")

    vm_folder    = os.path.dirname(vmx_path)
    vm_folder_name = os.path.basename(vm_folder)
    remote_path  = f"{staging_dir}/{vm_folder_name}"
    remote_vmx   = f"{remote_path}/{os.path.basename(vmx_path)}"
    folder_size  = _dir_size_mb(vm_folder)

    info(f"Source folder : {vm_folder}  ({folder_size} MB)")
    info(f"Destination   : {ssh_user}@{host}:{remote_path}")
    print()

    ssh_base = build_ssh_base(host, ssh_user, ssh_key)

    # Create staging dir on remote
    mkdir_cmd = ssh_base + [f"{ssh_user}@{host}", f"mkdir -p {shlex.quote(staging_dir)}"]
    if not dry_run:
        step("Creating staging directory on Proxmox...")
        result = subprocess.run(mkdir_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            err(f"Failed to create remote staging dir: {result.stderr}")
        ok(f"Remote staging dir ready: {staging_dir}")
    else:
        dry(f"Would run: {' '.join(mkdir_cmd)}")

    # SCP the folder
    scp_base = ["scp", "-r", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes"]
    if ssh_key:
        scp_base += ["-i", ssh_key]
    scp_cmd = scp_base + [vm_folder, f"{ssh_user}@{host}:{staging_dir}/"]

    if not dry_run:
        step(f"Uploading {folder_size}MB — this may take a while...")
        result = subprocess.run(scp_cmd)
        if result.returncode != 0:
            err("Upload failed — check SSH access and disk space on Proxmox node")
        ok(f"Upload complete → {remote_path}")
    else:
        dry(f"Would run: {' '.join(scp_cmd)}")
        ok(f"[DRY] Would upload to: {remote_path}")

    return remote_vmx

# =============================================================================
# virt-v2v INVOCATION
# =============================================================================

VIRTIO_WIN_DIR         = "/usr/share/virtio-win"
VIRTIO_GUEST_AGENT_DIR = os.path.join(VIRTIO_WIN_DIR, "guest-agent")
GUEST_AGENT_MSI        = "qemu-ga-x86_64.msi"   # 64-bit; i386 also present

def check_virtio_drivers():
    """Check whether the VirtIO drivers are extracted at /usr/share/virtio-win/.

    virt-v2v scans this directory at conversion time. When present it injects
    vioscsi, NetKVM, balloon etc. into the Windows guest during conversion —
    the VM boots directly with VirtIO devices and no manual driver work is needed.

    For Windows VMs this check is MANDATORY. If drivers are not found the script
    exits with a clear remediation message — conversion cannot safely proceed
    because virt-v2v will fall back to emulated IDE/RTL8139, and switching to
    VirtIO SCSI before driver installation causes INACCESSIBLE_BOOT_DEVICE (BSOD).

    Also checks for the guest agent MSI in guest-agent/ — used by
    apply_windows_firstboot_fixes() to schedule a silent install on first boot.

    Returns (drivers_ok: bool, agent_msi_path: str|None)
    """
    section("VIRTIO DRIVER CHECK")

    key_drivers    = ["vioscsi", "NetKVM", "balloon", "viostor"]
    found_drivers  = []
    missing_drivers = []
    drivers_ok     = False
    agent_msi_path = None

    # ── Check driver directories ──────────────────────────────────────────────
    if os.path.isdir(VIRTIO_WIN_DIR):
        for drv in key_drivers:
            if os.path.isdir(os.path.join(VIRTIO_WIN_DIR, drv)):
                found_drivers.append(drv)
            else:
                missing_drivers.append(drv)

        inf_count = sum(
            1 for _, _, files in os.walk(VIRTIO_WIN_DIR)
            for f in files if f.lower().endswith(".inf")
        )

        if found_drivers:
            ok(f"{VIRTIO_WIN_DIR}/ present — {inf_count} driver .inf files found")
            for d in found_drivers:
                ok(f"  [+] {d}")
            if missing_drivers:
                warn(f"Some key drivers not found: {', '.join(missing_drivers)}")
                warn("virt-v2v will inject what it finds — conversion may still succeed.")
            else:
                ok("All key drivers present — virt-v2v will inject automatically")
            drivers_ok = True
        else:
            warn(f"{VIRTIO_WIN_DIR}/ exists but contains no key driver subdirectories")
            warn("Directory may be empty or from an incomplete extraction.")
    else:
        warn(f"{VIRTIO_WIN_DIR}/ does not exist")

    # ── Hard exit if drivers are not available ────────────────────────────────
    if not drivers_ok:
        print()
        print(f"  {C.R}╔══════════════════════════════════════════════════════════════╗{C.NC}")
        print(f"  {C.R}║  FATAL — VirtIO drivers required for Windows VM conversion   ║{C.NC}")
        print(f"  {C.R}╚══════════════════════════════════════════════════════════════╝{C.NC}")
        print()
        warn("Without drivers at /usr/share/virtio-win/ virt-v2v falls back to:")
        warn("  - Emulated IDE disk controller  (poor performance)")
        warn("  - Emulated RTL8139 NIC          (poor performance)")
        warn("  - Switching to VirtIO SCSI BEFORE driver install = BSOD")
        warn("    (INACCESSIBLE_BOOT_DEVICE — VM will not boot)")
        print()
        info("Fix — run the following on this Proxmox node then re-run the script:")
        print()
        info("  # 1. Install extraction tool")
        info("  apt install -y p7zip-full")
        print()
        info("  # 2. Download the virtio-win ISO")
        info("  wget -O /var/lib/vz/template/iso/virtio-win.iso \\")
        info("    https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso")
        print()
        info(f"  # 3. Extract drivers to {VIRTIO_WIN_DIR}")
        info(f"  mkdir -p {VIRTIO_WIN_DIR}")
        info(f"  7z x /var/lib/vz/template/iso/virtio-win.iso -o{VIRTIO_WIN_DIR}")
        print()
        info(f"  # 4. Verify")
        info(f"  ls {VIRTIO_WIN_DIR}/vioscsi {VIRTIO_WIN_DIR}/NetKVM {VIRTIO_WIN_DIR}/guest-agent")
        print()
        sys.exit(1)

    # ── Check guest agent MSI ─────────────────────────────────────────────────
    msi_path = os.path.join(VIRTIO_GUEST_AGENT_DIR, GUEST_AGENT_MSI)
    if os.path.isfile(msi_path):
        ok(f"Guest agent MSI found: {msi_path}")
        ok("  Silent install will be scheduled on first Windows boot")
        agent_msi_path = msi_path
    else:
        warn(f"Guest agent MSI not found: {msi_path}")
        warn("QEMU guest agent will NOT be auto-installed on first boot.")
        warn(f"Install manually post-boot from the virtio-win ISO (D:\\guest-agent\\)")

    return drivers_ok, agent_msi_path


def check_ntfs_dirty(disk_paths, dry_run=False):
    """
    Check each VMDK for dirty NTFS partitions and offer to clear them with
    ntfsfix before conversion begins.

    Background
    ----------
    If a Windows VM was suspended, force-powered-off, or had Fast Startup /
    hibernation active, Windows leaves its NTFS journal in a "dirty" state.
    The ntfs-3g driver (used internally by virt-v2v / libguestfs) refuses to
    mount a dirty filesystem read-write, causing virt-v2v to abort early with:

        The disk contains an unclean file system (0, 0).
        Metadata kept in Windows cache, refused to mount.
        Falling back to read-only mount because the NTFS partition is in an
        unsafe state. Please run chkdsk.

    Since chkdsk requires booting Windows, the fix here is ntfsfix -d which
    clears only the dirty bit (no journal replay, safe on source VMDKs).

    Requires: qemu-nbd (qemu-utils), ntfsfix (ntfs-3g), nbd kernel module.
    Skipped for non-Windows guests (no NTFS partitions will be found).
    Skipped in dry-run mode (prints what would happen).
    """
    section("NTFS DIRTY-FLAG CHECK")

    info("Checking VMDKs for dirty NTFS partitions that would cause virt-v2v to abort.")
    info("This is common when a VM was suspended rather than cleanly shut down.")
    print()

    if not disk_paths:
        warn("No VMDK paths found in VMX — skipping NTFS check.")
        return

    if not shutil.which("qemu-nbd"):
        warn("qemu-nbd not found — skipping NTFS dirty check.")
        warn("Install: apt install qemu-utils")
        warn("If virt-v2v fails with 'unclean file system', run ntfsfix -d manually.")
        return

    if not shutil.which("ntfsfix"):
        warn("ntfsfix not found — skipping NTFS dirty check.")
        warn("Install: apt install ntfs-3g")
        warn("If virt-v2v fails with 'unclean file system', run ntfsfix -d manually.")
        return

    # sudo prefix for all commands that need root (qemu-nbd, ntfsfix, modprobe, blockdev)
    _s = ["sudo"] if os.geteuid() != 0 else []

    # Load nbd module
    if not dry_run:
        subprocess.run(_s + ["modprobe", "nbd"], capture_output=True)

    # Find a free /dev/nbdN device
    def find_free_nbd():
        for n in range(16):
            dev = f"/dev/nbd{n}"
            if not os.path.exists(dev):
                continue
            result = subprocess.run(_s + ["blockdev", "--getsize64", dev],
                                    capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip() == "0":
                return dev
        return None

    any_fixed = False

    for vmdk in disk_paths:
        info(f"Disk: {vmdk}")

        if dry_run:
            dry(f"Would connect {vmdk} via qemu-nbd and scan partitions for dirty NTFS")
            continue

        if not os.path.exists(vmdk):
            warn(f"  VMDK not found at path — skipping: {vmdk}")
            continue

        nbd_dev = find_free_nbd()
        if not nbd_dev:
            warn("  No free /dev/nbdN device found — skipping NTFS check for this disk.")
            warn("  You may need to: modprobe nbd max_part=8")
            continue

        step(f"  Connecting via {nbd_dev}...")
        connect = subprocess.run(
            _s + ["qemu-nbd", "--connect", nbd_dev, "--format=vmdk", vmdk],
            capture_output=True, text=True
        )
        if connect.returncode != 0:
            warn(f"  qemu-nbd connect failed: {connect.stderr.strip()}")
            warn("  Skipping NTFS check for this disk.")
            continue

        # Small pause for partition table to settle
        import time; time.sleep(1)

        try:
            # Enumerate partitions
            lsblk = subprocess.run(
                ["lsblk", "-lno", "NAME,FSTYPE", nbd_dev],
                capture_output=True, text=True
            )
            partitions = []
            for line in lsblk.stdout.splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1].lower() == "ntfs":
                    partitions.append(f"/dev/{parts[0]}")

            if not partitions:
                ok(f"  No NTFS partitions detected — nothing to check.")
            else:
                for part in partitions:
                    step(f"  Checking dirty flag on {part}...")
                    # ntfsfix -n is a dry-run / check-only mode
                    check = subprocess.run(
                        _s + ["ntfsfix", "-n", part],
                        capture_output=True, text=True
                    )
                    combined = (check.stdout + check.stderr).lower()
                    is_dirty = "dirty" in combined or "volume is dirty" in combined \
                               or "windows was hibernated" in combined \
                               or "unclean" in combined

                    if not is_dirty:
                        ok(f"  {part}: clean — no action needed.")
                    else:
                        warn(f"  {part}: DIRTY — filesystem was not cleanly unmounted.")
                        print()
                        print(f"  {C.Y}This will cause virt-v2v to abort with:{C.NC}")
                        print(f"  {C.D}    'The disk contains an unclean file system'")
                        print(f"    'Metadata kept in Windows cache, refused to mount'{C.NC}")
                        print()
                        print(f"  {C.CY}Fix: ntfsfix -d clears the dirty bit only (safe — no journal replay).{C.NC}")
                        print()
                        if confirm(f"Clear dirty flag on {part} now?", default="y"):
                            fix = subprocess.run(
                                _s + ["ntfsfix", "-d", part],
                                capture_output=True, text=True
                            )
                            if fix.returncode == 0:
                                ok(f"  {part}: dirty flag cleared.")
                                any_fixed = True
                            else:
                                err(f"  ntfsfix -d failed: {fix.stderr.strip()}")
                                warn("  Manual fix:")
                                warn(f"    qemu-nbd --connect {nbd_dev} --format=vmdk {vmdk}")
                                warn(f"    ntfsfix -d {part}")
                                warn(f"    qemu-nbd --disconnect {nbd_dev}")
                        else:
                            warn(f"  Skipped — virt-v2v will likely abort on this disk.")

        finally:
            step(f"  Disconnecting {nbd_dev}...")
            subprocess.run(_s + ["qemu-nbd", "--disconnect", nbd_dev], capture_output=True)

        print()

    if any_fixed:
        ok("Dirty flags cleared — proceeding to conversion.")
    elif not dry_run:
        ok("NTFS check complete.")


def run_virt_v2v(vmx_path, output_dir, host, ssh_user, ssh_key, mode, staging_dir, disk_format="qcow2", dry_run=False):
    """
    Run virt-v2v against vmx_path, output qcow2, return path to converted disk.

    WORKSTATION → virt-v2v runs locally; output disk is then SCP'd to Proxmox.
                  Only the converted disk crosses the network (much smaller than
                  the raw VMDK). Returns the REMOTE path on the Proxmox node.

    LOCAL       → virt-v2v runs locally via subprocess.
                  Returns the LOCAL path to the converted disk.

    REMOTE      → virt-v2v is invoked on the Proxmox node via SSH.
                  Raw VMDKs must already be uploaded. Returns REMOTE path.
    """
    section("virt-v2v CONVERSION")

    info(f"Mode        : {mode.upper()}")
    info(f"Source VMX  : {vmx_path}")
    info(f"Output dir  : {output_dir}  ({'local' if mode != 'remote' else 'remote on ' + host})")
    print()

    vm_name  = os.path.splitext(os.path.basename(vmx_path))[0]
    disk_out = f"{output_dir}/{vm_name}-sda"

    v2v_cmd = [
        "virt-v2v",
        "-i", "vmx", vmx_path,
        "-o", "local",
        "-of", disk_format,
        "-os", output_dir,
        "-v"
    ]

    # ── WORKSTATION mode: run locally, then SCP result to Proxmox ────────────
    if mode == "workstation":
        os.makedirs(output_dir, exist_ok=True)
        log_path = f"/tmp/v2v-{vm_name}.log"

        step(f"Running virt-v2v locally — logging to {log_path}")
        step(f"Command: {' '.join(v2v_cmd)}")
        print()

        if dry_run:
            dry("virt-v2v would run here locally")
            dry(f"Would then SCP {disk_out} → {ssh_user}@{host}:{staging_dir}/")
            return f"{staging_dir}/{vm_name}-sda"

        with open(log_path, "w") as log_f:
            result = subprocess.run(v2v_cmd, stdout=log_f, stderr=subprocess.STDOUT)

        if result.returncode != 0:
            warn(f"virt-v2v exited with code {result.returncode}")
            warn(f"Check log: {log_path}")
            warn("Common causes: config parse error, insufficient disk space, encrypted VMDK")
            warn("Hint: try the qemu-img fallback — see Appendix A of NET-VIRT-V2V-001")
            if not confirm("Continue anyway (disk import will likely fail)?", default="n"):
                err("Aborted after virt-v2v failure.")
        else:
            ok("virt-v2v completed successfully")

        # Find the output disk — virt-v2v names it <vmname>-sda (no extension)
        disk_out = _find_v2v_output(output_dir, disk_out, vm_name)
        size_mb  = round(os.path.getsize(disk_out) / 1024 / 1024, 1)
        ok(f"Converted disk: {disk_out}  ({size_mb} MB)")

        # SCP the qcow2 to Proxmox staging dir
        section("UPLOADING CONVERTED DISK TO PROXMOX")
        info(f"Pushing {size_mb} MB qcow2 → {ssh_user}@{host}:{staging_dir}/")
        info("(This is the converted disk only — much smaller than the raw VMDK)")

        ssh_base = build_ssh_base(host, ssh_user, ssh_key)
        mkdir_cmd = ssh_base + [f"{ssh_user}@{host}", f"mkdir -p {shlex.quote(staging_dir)}"]
        step("Creating staging directory on Proxmox...")
        subprocess.run(mkdir_cmd, check=True)

        scp_base = ["scp", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes"]
        if ssh_key:
            scp_base += ["-i", ssh_key]
        scp_cmd = scp_base + [disk_out, f"{ssh_user}@{host}:{staging_dir}/"]

        step(f"Uploading: {' '.join(scp_cmd)}")
        result = subprocess.run(scp_cmd)
        if result.returncode != 0:
            err("Upload failed — check SSH access and free space on Proxmox node")
        ok("Upload complete")

        remote_disk = f"{staging_dir}/{os.path.basename(disk_out)}"
        ok(f"Remote disk path: {remote_disk}")
        return remote_disk

    # ── LOCAL mode: run on Proxmox node itself ────────────────────────────────
    elif mode == "local":
        os.makedirs(output_dir, exist_ok=True)
        log_path = f"/tmp/v2v-{vm_name}.log"

        step(f"Running: {' '.join(v2v_cmd)}")
        step(f"Logging to {log_path}")

        if dry_run:
            dry("virt-v2v would run here — skipping in dry-run mode")
            return disk_out

        with open(log_path, "w") as log_f:
            result = subprocess.run(v2v_cmd, stdout=log_f, stderr=subprocess.STDOUT)

        if result.returncode != 0:
            warn(f"virt-v2v exited with code {result.returncode}")

            # ── Diagnose log for known recoverable errors ─────────────────────
            try:
                log_text = open(log_path).read()
            except Exception:
                log_text = ""

            dirty_signatures = [
                "unclean file system",
                "metadata kept in windows cache",
                "filesystem was mounted read-only",
                "windows hibernation",
                "fast restart",
            ]
            is_dirty = any(s in log_text.lower() for s in dirty_signatures)

            if is_dirty:
                print()
                warn("╔══════════════════════════════════════════════════════════════╗")
                warn("║  NTFS dirty flag detected — Windows was not cleanly shut     ║")
                warn("║  down before conversion. virt-v2v cannot mount read-write.   ║")
                warn("╚══════════════════════════════════════════════════════════════╝")
                print()
                info("This is automatically recoverable. The fix is ntfsfix -d which")
                info("clears the dirty bit only (no journal replay — safe on source VMDKs).")
                print()

                # Find the VMDK paths from the vmx_path
                vmx_dir  = os.path.dirname(os.path.abspath(vmx_path))
                vmdk_candidates = []
                try:
                    vmx_data = open(vmx_path).read()
                    import re as _re
                    for match in _re.finditer(r'fileName\s*=\s*"([^"]+\.vmdk)"', vmx_data, _re.I):
                        p = match.group(1)
                        full = p if os.path.isabs(p) else os.path.join(vmx_dir, p)
                        if os.path.isfile(full):
                            vmdk_candidates.append(full)
                except Exception:
                    pass

                if not vmdk_candidates:
                    # Fallback: find any .vmdk in the same directory as the VMX
                    vmdk_candidates = [
                        os.path.join(vmx_dir, f) for f in os.listdir(vmx_dir)
                        if f.lower().endswith(".vmdk")
                        and "-flat" not in f.lower()   # descriptor, not flat file
                    ]

                if not vmdk_candidates:
                    warn("Could not locate VMDKs to run ntfsfix — fix manually:")
                    warn(f"  qemu-nbd --connect /dev/nbd0 --format=vmdk <path-to.vmdk>")
                    warn(f"  ntfsfix -d /dev/nbd0p2   # adjust partition number")
                    warn(f"  qemu-nbd --disconnect /dev/nbd0")
                    warn(f"Then re-run this script.")
                    err("Aborted — NTFS dirty flag, manual fix required.")

                if confirm("Run ntfsfix -d on all NTFS partitions in these VMDKs and retry?",
                           default="y"):
                    fixed_any = False
                    _s = ["sudo"] if os.geteuid() != 0 else []
                    subprocess.run(_s + ["modprobe", "nbd"], capture_output=True)

                    for vmdk in vmdk_candidates:
                        info(f"Processing: {vmdk}")

                        # Find a free nbd device
                        nbd_dev = None
                        for n in range(16):
                            dev = f"/dev/nbd{n}"
                            if not os.path.exists(dev):
                                continue
                            r = subprocess.run(_s + ["blockdev", "--getsize64", dev],
                                               capture_output=True, text=True)
                            if r.returncode == 0 and r.stdout.strip() == "0":
                                nbd_dev = dev
                                break

                        if not nbd_dev:
                            warn("No free /dev/nbdN — skipping this VMDK")
                            continue

                        step(f"  Connecting {vmdk} → {nbd_dev}...")
                        conn = subprocess.run(
                            _s + ["qemu-nbd", "--connect", nbd_dev, "--format=vmdk", vmdk],
                            capture_output=True, text=True
                        )
                        if conn.returncode != 0:
                            warn(f"  qemu-nbd connect failed: {conn.stderr.strip()}")
                            continue

                        import time; time.sleep(2)  # let partition table settle

                        try:
                            lsblk = subprocess.run(
                                ["lsblk", "-lno", "NAME,FSTYPE", nbd_dev],
                                capture_output=True, text=True
                            )
                            ntfs_parts = [
                                f"/dev/{l.split()[0]}"
                                for l in lsblk.stdout.splitlines()
                                if len(l.split()) == 2 and l.split()[1].lower() == "ntfs"
                            ]

                            if not ntfs_parts:
                                # lsblk may not see NTFS through the nbd descriptor —
                                # try the numbered partitions directly
                                for pn in range(1, 5):
                                    candidate = f"{nbd_dev}p{pn}"
                                    if os.path.exists(candidate):
                                        ntfs_parts.append(candidate)

                            for part in ntfs_parts:
                                step(f"  Running ntfsfix -d {part}...")
                                fix = subprocess.run(
                                    _s + ["ntfsfix", "-d", part],
                                    capture_output=True, text=True
                                )
                                if fix.returncode == 0:
                                    ok(f"  {part}: dirty flag cleared.")
                                    fixed_any = True
                                else:
                                    warn(f"  {part}: ntfsfix failed: {fix.stderr.strip()}")
                        finally:
                            subprocess.run(_s + ["qemu-nbd", "--disconnect", nbd_dev],
                                           capture_output=True)
                            time.sleep(1)

                    if fixed_any:
                        ok("Dirty flags cleared — retrying virt-v2v...")
                        print()
                        with open(log_path, "w") as log_f:
                            result = subprocess.run(v2v_cmd, stdout=log_f,
                                                    stderr=subprocess.STDOUT)
                        if result.returncode == 0:
                            ok("virt-v2v completed successfully on retry.")
                        else:
                            warn("virt-v2v failed again after ntfsfix.")
                            warn(f"Check log: {log_path}")
                            if not confirm("Continue anyway?", default="n"):
                                err("Aborted after virt-v2v retry failure.")
                    else:
                        warn("No partitions were fixed — virt-v2v will likely fail again.")
                        if not confirm("Continue anyway?", default="n"):
                            err("Aborted — could not clear NTFS dirty flags.")
                else:
                    err("Aborted — NTFS dirty flag must be cleared before conversion.")

            else:
                # Not a dirty-flag error — generic failure path
                warn(f"Check log: {log_path}")
                warn("Common causes: config parse error, insufficient disk space, encrypted VMDK")
                if not confirm("Continue anyway?", default="n"):
                    err("Aborted after virt-v2v failure.")
        else:
            ok("virt-v2v completed successfully")

        return _find_v2v_output(output_dir, disk_out, vm_name)

    # ── REMOTE mode: SSH into Proxmox, run virt-v2v there ────────────────────
    else:
        ssh_base       = build_ssh_base(host, ssh_user, ssh_key)
        mkdir_cmd      = ssh_base + [f"{ssh_user}@{host}", f"mkdir -p {shlex.quote(output_dir)}"]
        v2v_remote_str = " ".join(shlex.quote(a) for a in v2v_cmd)
        ssh_v2v_cmd    = ssh_base + [f"{ssh_user}@{host}", v2v_remote_str]

        if dry_run:
            dry(f"Would run on {host}: {' '.join(v2v_cmd)}")
            return disk_out

        step("Creating output directory on Proxmox node...")
        subprocess.run(mkdir_cmd, check=True)

        step(f"Running virt-v2v on {host} — output will stream...")
        result = subprocess.run(ssh_v2v_cmd)
        if result.returncode != 0:
            warn("virt-v2v reported errors — check output above")
            if not confirm("Continue anyway?", default="n"):
                err("Aborted after virt-v2v failure.")
        else:
            ok("virt-v2v completed")

        return disk_out


def _find_v2v_output(output_dir, expected_path, vm_name):
    """
    Locate the converted disk file in output_dir.
    virt-v2v names output <vmname>-sda (no extension) by default.
    Falls back to scanning the directory if the expected path isn't found.
    """
    if os.path.isfile(expected_path):
        return expected_path

    warn(f"Expected output not found: {expected_path}")
    warn("Scanning output directory for converted disk...")
    candidates = [
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if not f.endswith(".xml") and os.path.isfile(os.path.join(output_dir, f))
    ]
    if not candidates:
        err(f"No converted disk found in {output_dir} — check virt-v2v log")
    if len(candidates) == 1:
        warn(f"Using: {candidates[0]}")
        return candidates[0]
    # Multiple candidates — ask user
    print()
    print(f"  {C.W}Multiple output files found — select the converted disk:{C.NC}")
    for i, c in enumerate(candidates, 1):
        size_mb = round(os.path.getsize(c) / 1024 / 1024, 1)
        print(f"  {C.CY}  {i}{C.NC}  {c}  ({size_mb} MB)")
    choice = int(prompt("Select", default="1",
                        validator=lambda v: True if (v.isdigit() and 1 <= int(v) <= len(candidates)) else "Invalid"))
    return candidates[choice - 1]

# =============================================================================
# PROXMOX DISK IMPORT + VM WIRING
# =============================================================================

def _cleanup_staging(paths, label="staging file"):
    """
    Attempt to remove a list of paths (files or directories).
    Reports result but never raises — cleanup failure is never fatal.
    """
    for path in paths:
        if not path or not os.path.exists(path):
            continue
        try:
            if os.path.isdir(path):
                import shutil as _shutil
                _shutil.rmtree(path)
                ok(f"Cleaned up {label}: {path}/")
            else:
                os.remove(path)
                ok(f"Cleaned up {label}: {path}")
        except Exception as e:
            warn(f"Could not remove {path}: {e} — remove manually")


def _check_disk_space(path, required_bytes, label="disk"):
    """
    Verify a path has at least required_bytes free.
    Returns True if OK, False if tight, logs a warning if under 10% headroom.
    """
    try:
        stat = os.statvfs(path)
        free = stat.f_bavail * stat.f_frsize
        if free < required_bytes:
            warn(f"Insufficient space on {label}: "
                 f"need {required_bytes//1024//1024}MB, "
                 f"have {free//1024//1024}MB free at {path}")
            return False
        headroom = free - required_bytes
        if headroom < required_bytes * 0.1:
            warn(f"Low headroom on {label} after import: only "
                 f"{headroom//1024//1024}MB will remain free")
        return True
    except Exception:
        return True   # can't check — don't block, just proceed


def _verify_disk_file(disk_out):
    """
    Verify the converted disk file looks sane before attempting import.
    Checks: exists, non-zero size, qemu-img can read it, not obviously truncated.
    Returns (ok: bool, size_bytes: int, format_detected: str)
    """
    section("PRE-IMPORT DISK VERIFICATION")

    if not os.path.isfile(disk_out):
        warn(f"Disk file not found: {disk_out}")
        return False, 0, "unknown"

    size_bytes = os.path.getsize(disk_out)
    size_mb    = round(size_bytes / 1024 / 1024, 1)
    ok(f"File exists   : {disk_out}")
    ok(f"Size on disk  : {size_mb} MB")

    if size_bytes == 0:
        warn("Disk file is zero bytes — virt-v2v likely failed silently")
        return False, 0, "unknown"

    if size_bytes < 10 * 1024 * 1024:   # < 10 MB is suspiciously small
        warn(f"Disk file is only {size_mb} MB — this seems too small for a VM disk")
        warn("virt-v2v may have only partially written the output")

    # Run qemu-img info to verify the image is readable and get virtual size
    fmt_detected = "unknown"
    virtual_size = 0
    qi = shutil.which("qemu-img")
    if qi:
        try:
            result = subprocess.run(
                ["qemu-img", "info", "--output=json", disk_out],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                info_data    = json.loads(result.stdout)
                fmt_detected = info_data.get("format", "unknown")
                virtual_size = info_data.get("virtual-size", 0)
                virtual_gb   = round(virtual_size / 1024**3, 2)
                ok(f"Image format  : {fmt_detected}  (qemu-img confirmed readable)")
                ok(f"Virtual size  : {virtual_gb} GB")
                if virtual_size < size_bytes:
                    warn("Virtual size < physical file size — image may be corrupt")
            else:
                warn(f"qemu-img info failed: {result.stderr.strip()}")
                warn("Image may be corrupt or in an unrecognised format")
        except subprocess.TimeoutExpired:
            warn("qemu-img info timed out — disk may be corrupt or very large")
        except json.JSONDecodeError:
            warn("qemu-img returned unexpected output — could not parse image info")
        except Exception as e:
            warn(f"qemu-img check failed: {e}")
    else:
        info("qemu-img not available — skipping image integrity check")

    return True, size_bytes, fmt_detected


def _wait_for_unused_disk(proxmox, node, vmid, timeout=30):
    """
    After qm importdisk, the disk appears as 'unused0' in the VM config.
    Poll until it appears, up to timeout seconds.
    Returns the unused disk identifier string (e.g. 'local-zfs:vm-100-disk-0')
    or None if it doesn't appear in time.
    """
    step(f"Waiting for imported disk to appear in VM {vmid} config...")
    for i in range(timeout):
        try:
            cfg = proxmox.nodes(node).qemu(vmid).config.get()
            # Look for any unusedN key
            for key, val in cfg.items():
                if key.startswith("unused"):
                    ok(f"Disk appeared as {key}: {val}")
                    return key, val
        except Exception:
            pass
        time.sleep(1)
    warn(f"Disk did not appear as unusedN within {timeout}s")
    return None, None


def import_and_wire(proxmox, node, disk_out, vmid, vm_name, hw, storage,
                    storage_type, disk_format, nics, console, ostype, pool,
                    virtio_iso=None, bios_type="seabios", bios_rom=None,
                    bmc_type=None, remote_staging_paths=None, dry_run=False):
    """
    Full pipeline: pre-flight checks → create VM → verify disk → import →
    attach → configure → post-import verification → cleanup staging files.

    remote_staging_paths: list of paths on the Proxmox node to clean up after
    successful import (e.g. the uploaded qcow2 or raw img in /tmp).
    """
    section("PRE-FLIGHT CHECKS")

    # ── 1. Confirm VMID not already in use ───────────────────────────────────
    step(f"Checking VMID {vmid} is free...")
    try:
        existing = {int(v["vmid"]) for v in proxmox.nodes(node).qemu.get()}
        if vmid in existing:
            err(f"VMID {vmid} is already in use on node {node} — cannot proceed")
        ok(f"VMID {vmid} is free")
    except Exception as e:
        warn(f"Could not verify VMID availability: {e} — proceeding with caution")

    # ── 2. Confirm VM name not already in use ────────────────────────────────
    step(f"Checking name '{vm_name}' is free...")
    try:
        existing_names = {v.get("name","").upper()
                          for v in proxmox.nodes(node).qemu.get()}
        if vm_name.upper() in existing_names:
            err(f"VM name '{vm_name}' already exists on node {node}")
        ok(f"Name '{vm_name}' is free")
    except Exception as e:
        warn(f"Could not verify name availability: {e}")

    # ── 3. Verify disk file (local path — workstation or local mode) ─────────
    disk_size = 0   # initialised here so space check below is safe in dry-run
    if not dry_run and os.path.isfile(disk_out):
        disk_ok, disk_size, fmt_detected = _verify_disk_file(disk_out)
        if not disk_ok:
            if not confirm("Disk verification failed — proceed anyway?", default="n"):
                err("Aborted at pre-import verification.")
        # Warn if detected format doesn't match what we're about to import as
        if fmt_detected not in ("unknown",) and fmt_detected != disk_format:
            warn(f"Format mismatch: file appears to be {fmt_detected} "
                 f"but storage requires {disk_format}")
            warn("This may cause qm importdisk to fail")
            if not confirm("Continue anyway?", default="n"):
                err("Aborted at format mismatch.")
    elif not dry_run:
        # Remote path — can't check locally, just note it
        info(f"Disk is on Proxmox node at {disk_out} — local verification skipped")
        disk_size = 0

    # ── 4. Check free space on Proxmox storage (API-based estimate) ──────────
    step("Checking available space on target storage...")
    try:
        stores    = proxmox.nodes(node).storage.get(content="images")
        store_inf = next((s for s in stores if s["storage"] == storage), None)
        if store_inf:
            avail_bytes = store_inf.get("avail", 0)
            avail_gb    = round(avail_bytes / 1024**3, 1)
            # Estimate required: virtual size (if we know it) or 2× physical size
            required = disk_size * 2 if disk_size else 0
            if required and avail_bytes < required:
                warn(f"Storage {storage} has {avail_gb}GB free — "
                     f"may not be enough for this disk")
                if not confirm("Continue anyway?", default="n"):
                    err("Aborted: insufficient storage space.")
            else:
                ok(f"Storage {storage}: {avail_gb}GB free — looks sufficient")
        else:
            warn(f"Could not find storage info for '{storage}' — space check skipped")
    except Exception as e:
        warn(f"Space check failed: {e} — proceeding")

    # ── 5. ZFS-specific advisory ──────────────────────────────────────────────
    if storage_type == "zfspool":
        print()
        info(f"ZFS storage detected ({storage})")
        info("Import will create a zvol — block device, not a file")
        info("Format: raw  (qcow2 is not supported on ZFS zvols)")
        info("Note: zvol volblocksize defaults to 8K on Proxmox (fine for most workloads)")
        print()

    if dry_run:
        dry(f"Would create VM {vmid} ({vm_name}) on node {node}")
        dry(f"Would import {disk_out} → {storage} as {disk_format}")
        dry(f"Would attach as scsi0, configure console={console}, {len(nics)} NIC(s)")
        if virtio_iso:
            dry(f"Would attach VirtIO ISO as ide2: {virtio_iso}")
        if remote_staging_paths:
            dry(f"Would clean up: {remote_staging_paths}")
        return True

    # ── Create VM shell ───────────────────────────────────────────────────────
    section("CREATING VM")
    step("Creating VM shell...")
    try:
        # Build QEMU args -- custom BIOS ROM and/or BMC emulation
        args_parts = []
        if bios_rom:
            args_parts.append(f"-bios {bios_rom}")
        if bmc_type == "kcs":
            args_parts.append("-device ipmi-bmc-sim,id=bmc0 -device isa-ipmi-kcs,bmc=bmc0,irq=5")
        elif bmc_type == "bt":
            args_parts.append("-device ipmi-bmc-sim,id=bmc0 -device isa-ipmi-bt,bmc=bmc0")
        extra_args = " ".join(args_parts)

        proxmox.nodes(node).qemu.post(
            vmid    = vmid,
            name    = vm_name,
            ostype  = ostype,
            cores   = hw["total_vcpus"],
            sockets = 1,
            cpu     = "host",
            memory  = hw["ram_mb"],
            balloon = 0,
            bios    = bios_type,
            onboot  = 0,
            agent   = "enabled=1",
            scsihw  = "virtio-scsi-pci",
            **({"pool": pool} if pool else {}),
            **({"args": extra_args} if extra_args else {}),
        )
        ok(f"VM {vmid} ({vm_name}) created on {node}")
        if bios_rom:
            ok(f"BIOS ROM: {bios_rom.split('/')[-1]}  ({_describe_rom(bios_rom.split('/')[-1])})")
        if bmc_type:
            bmc_port = 6000 + vmid
            ok(f"BMC: ipmi-bmc-sim KCS -- /dev/ipmi0 will be present in guest")
            warn(f"Register with proxmoxbmc after VM is stable:")
            warn(f"  pbmc add --port {bmc_port} --address <bind-ip>")
            warn(f"    --proxmox-address <pve-ip> --token-user root@pam")
            warn(f"    --token-name proxmoxbmc --token-value <token> {vmid}")
            warn(f"  pbmc start {vmid}")
            warn(f"  See NET-BMC-001 for --address VLAN binding guidance")
    except Exception as e:
        err(f"Failed to create VM shell: {e}")

    # ── Import disk ───────────────────────────────────────────────────────────
    section("DISK IMPORT")
    step(f"Importing: {disk_out}")
    step(f"       → : {storage}  (format: {disk_format})")

    import_ok = False
    # qm lives in /usr/sbin and requires root — use sudo if not already root
    qm_cmd = ["sudo", "qm"] if os.geteuid() != 0 else ["qm"]
    try:
        result = subprocess.run(
            qm_cmd + ["importdisk", str(vmid), disk_out, storage,
                      "--format", disk_format],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            ok("qm importdisk completed successfully")
            import_ok = True
        else:
            warn(f"qm importdisk exited {result.returncode}")
            warn(f"stdout: {result.stdout.strip()}")
            warn(f"stderr: {result.stderr.strip()}")
            warn("Manual recovery:")
            warn(f"  sudo qm importdisk {vmid} {disk_out} {storage} --format {disk_format}")
    except FileNotFoundError:
        warn("'qm' not found — is this a Proxmox node? Is sudo available?")
        warn(f"Run manually: sudo qm importdisk {vmid} {disk_out} {storage} --format {disk_format}")
    except Exception as e:
        warn(f"Import exception: {e}")

    if not import_ok:
        if not confirm("Import reported errors — attempt to continue configuring VM?",
                       default="n"):
            warn("VM shell exists but has no disk. Clean up with:")
            warn(f"  qm destroy {vmid}")
            err("Aborted after import failure.")

    # ── Wait for disk to appear in VM config, then attach ────────────────────
    unused_key, unused_val = _wait_for_unused_disk(proxmox, node, vmid)

    if unused_key:
        step(f"Attaching {unused_key} ({unused_val}) as scsi0...")
        try:
            proxmox.nodes(node).qemu(vmid).config.put(
                scsi0=unused_val
            )
            ok("Disk attached as scsi0")
        except Exception as e:
            warn(f"Could not attach disk: {e}")
            warn(f"Attach manually: Proxmox UI → VM {vmid} → Hardware → {unused_key} → Edit → scsi0")
    else:
        # Fall back to constructed disk identifier
        constructed = f"{storage}:vm-{vmid}-disk-0"
        warn(f"unusedN not found — attempting constructed path: {constructed}")
        try:
            proxmox.nodes(node).qemu(vmid).config.put(scsi0=constructed)
            ok(f"Disk attached as scsi0 (constructed path)")
        except Exception as e:
            warn(f"Fallback attach failed: {e}")
            warn(f"Attach manually in Proxmox UI: Hardware → unused0 → Edit → Add as scsi0")

    # ── Boot order ────────────────────────────────────────────────────────────
    step("Setting boot order: scsi0...")
    try:
        proxmox.nodes(node).qemu(vmid).config.put(boot="order=scsi0")
        ok("Boot order: scsi0")
    except Exception as e:
        warn(f"Could not set boot order: {e}")
        warn(f"Set manually: Proxmox UI → VM {vmid} → Options → Boot Order → scsi0")

    # ── Console ───────────────────────────────────────────────────────────────
    step("Configuring console...")
    try:
        if console == "serial":
            proxmox.nodes(node).qemu(vmid).config.put(serial0="socket", vga="serial0")
            ok("Console: Serial only (ttyS0) — connect: qm terminal {vmid}")
        elif console == "both":
            proxmox.nodes(node).qemu(vmid).config.put(serial0="socket", vga="std,memory=32")
            ok("Console: VGA + Serial ttyS0 — connect: qm terminal {vmid}")
        else:
            proxmox.nodes(node).qemu(vmid).config.put(vga="std,memory=32")
            ok("Console: VGA only")
    except Exception as e:
        warn(f"Console config failed: {e}")

    # ── NICs ──────────────────────────────────────────────────────────────────
    step("Configuring NICs...")
    for nic in nics:
        try:
            spec = f"virtio,bridge={nic['bridge']}"
            if nic["vlan"]:
                spec += f",tag={nic['vlan']}"
            if nic.get("mac"):
                spec += f",macaddr={nic['mac']}"
            proxmox.nodes(node).qemu(vmid).config.put(**{nic["id"]: spec})
            vlan_str = f"VLAN {nic['vlan']}" if nic["vlan"] else "untagged"
            mac_str  = f"  mac={nic['mac']}" if nic.get("mac") else "  mac=auto"
            ok(f"{nic['id']}: {nic['bridge']} {vlan_str} virtio{mac_str}")
        except Exception as e:
            warn(f"Failed to configure {nic['id']}: {e}")

    # ── VirtIO ISO CDROM (Windows VMs only) ───────────────────────────────────
    if virtio_iso:
        step("Attaching VirtIO ISO as ide2 (CDROM)...")
        try:
            proxmox.nodes(node).qemu(vmid).config.put(
                ide2=f"{virtio_iso},media=cdrom"
            )
            ok(f"VirtIO ISO attached: {virtio_iso.split('/')[-1]}")
            info("To inject drivers offline (from Windows recovery console):")
            info("  dism /image:C:\\ /add-driver /driver:D:\\ /recurse")
            info("Then reboot — disable Secure Boot (F2) and driver signing (F8) if needed.")
        except Exception as e:
            warn(f"Could not attach VirtIO ISO: {e}")
            warn(f"Attach manually: Proxmox UI → VM {vmid} → Hardware → Add → CD/DVD → {virtio_iso}")


    section("POST-IMPORT VERIFICATION")
    step("Verifying VM config looks sane...")
    config_ok = True
    try:
        cfg = proxmox.nodes(node).qemu(vmid).config.get()

        # Check disk attached
        if "scsi0" in cfg:
            ok(f"scsi0    : {cfg['scsi0']}")
        else:
            warn("scsi0 not present in VM config — disk may not be attached")
            config_ok = False

        # Check boot order
        if "boot" in cfg:
            ok(f"boot     : {cfg['boot']}")
        else:
            warn("boot order not set")

        # Check memory
        mem = cfg.get("memory", 0)
        if int(mem) >= 256:
            ok(f"memory   : {mem} MB")
        else:
            warn(f"memory is only {mem} MB — may be misconfigured")

        # Check no unusedN disks remain (would indicate attach failed)
        leftover = [k for k in cfg if k.startswith("unused")]
        if leftover:
            warn(f"Unused disk(s) still in config: {leftover}")
            warn("These may be unattached disks — check in Proxmox UI")

        # Check agent
        if cfg.get("agent", "").startswith("enabled=1"):
            ok("agent    : qemu-guest-agent enabled")
        else:
            info("agent    : not confirmed enabled — check manually")

    except Exception as e:
        warn(f"Could not retrieve VM config for verification: {e}")
        config_ok = False

    if not config_ok:
        warn("One or more post-import checks failed — review VM config before starting")
        warn(f"  qm config {vmid}")

    # ── Cleanup staging files ─────────────────────────────────────────────────
    if import_ok and remote_staging_paths:
        section("CLEANUP")
        info("Import succeeded — removing temporary staging files...")
        _cleanup_staging(remote_staging_paths, label="staging")
    elif not import_ok and remote_staging_paths:
        warn("Import had errors — preserving staging files for manual recovery:")
        for p in remote_staging_paths:
            warn(f"  {p}")

    return import_ok

# =============================================================================
# LOGGING
# =============================================================================

def write_log(log_file, vmid, vm_name, node, hw, storage, nics, console,
              vmx_path, pool, bios_type="seabios", bios_rom=None,
              bmc_type=None, dry_run=False):
    try:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        ts       = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        nics_str = "; ".join(
            f"{n['id']}={n['bridge']}({'VLAN'+str(n['vlan']) if n['vlan'] else 'untagged'})"
            for n in nics
        )
        bios_str = f"{bios_type}" + (f":{bios_rom.split('/')[-1]}" if bios_rom else "")
        bmc_str  = bmc_type or "none"
        line = (
            f"{ts}  "
            f"{'[DRY-RUN] ' if dry_run else ''}"
            f"VMID={vmid}  NAME={vm_name}  NODE={node}  "
            f"SOURCE={vmx_path}  "
            f"POOL={pool or 'none'}  "
            f"CPU={hw['total_vcpus']}vCPU  RAM={hw['ram_mb']}MB  "
            f"STORAGE={storage}  CONSOLE={console}  "
            f"BIOS={bios_str}  BMC={bmc_str}  "
            f"NICS=[{nics_str}]\n"
        )
        with open(log_file, "a") as f:
            f.write(line)
        ok(f"Logged to {log_file}")
    except Exception as e:
        warn(f"Failed to write log: {e}")

# =============================================================================
# SUMMARY PRINT
# =============================================================================

def print_conversion_summary(vmid, vm_name, vmx_path, hw, storage, nics,
                              console, ostype, pool, mode,
                              bios_type="seabios", bios_rom=None,
                              bmc_type=None, dry_run=False):
    tag = f"{C.B}[DRY RUN]{C.NC} " if dry_run else ""
    print()
    print(f"{C.Y}  {'=' * 60}{C.NC}")
    print(f"{C.W}  {tag}CONVERSION SUMMARY{C.NC}")
    print(f"{C.Y}  {'=' * 60}{C.NC}")
    print()
    print(f"  {C.W}Source{C.NC}")
    print(f"    {C.CY}VMX         :{C.NC} {vmx_path}")
    print(f"    {C.CY}Display name:{C.NC} {hw['display_name']}")
    print(f"    {C.CY}Guest OS    :{C.NC} {hw['guest_os_raw']} → {ostype}")
    print()
    print(f"  {C.W}Target{C.NC}")
    print(f"    {C.CY}VM ID   :{C.NC} {vmid}")
    print(f"    {C.CY}Name    :{C.NC} {vm_name}")
    print(f"    {C.CY}Pool    :{C.NC} {pool or '(none)'}")
    print(f"    {C.CY}Storage :{C.NC} {storage}")
    print(f"    {C.CY}Mode    :{C.NC} {mode.upper()} ({'runs locally' if mode=='local' else 'runs via SSH'})")
    print()
    print(f"  {C.W}Hardware (from VMX){C.NC}")
    print(f"    {C.CY}vCPUs   :{C.NC} {hw['total_vcpus']}")
    print(f"    {C.CY}RAM     :{C.NC} {hw['ram_mb']} MB")
    print(f"    {C.CY}Disk(s) :{C.NC} {len(hw['disk_paths'])} VMDK(s) detected")
    print()
    print(f"  {C.W}Console :{C.NC} {console}")
    bios_label = bios_type.upper()
    if bios_rom:
        rom_fname = bios_rom.split("/")[-1]
        print(f"  {C.W}BIOS ROM:{C.NC} {bios_label} -- {rom_fname}")
        print(f"           {C.D}{_describe_rom(rom_fname)}{C.NC}")
    else:
        print(f"  {C.W}BIOS ROM:{C.NC} {bios_label} (default -- no custom ROM)")
    if bmc_type:
        print(f"  {C.W}BMC     :{C.NC} IPMI {bmc_type.upper()} (ipmi-bmc-sim) -- port {6000 + vmid}")
        print(f"           {C.D}Register with proxmoxbmc after import (NET-BMC-001){C.NC}")
    else:
        print(f"  {C.W}BMC     :{C.NC} None")
    print()
    print(f"  {C.W}NICs{C.NC}")
    if nics:
        for nic in nics:
            vlan_str = f"VLAN {nic['vlan']}" if nic["vlan"] else "untagged"
            print(f"    {C.CY}{nic['id']:5}{C.NC}  {nic['bridge']}  {vlan_str:<10}  virtio  — {nic['desc']}")
    else:
        print(f"    {C.Y}None configured — set up manually after import{C.NC}")
    print()

# =============================================================================
# POST-CONVERSION LINUX BOOT FIXES
# =============================================================================

def apply_linux_boot_fixes(disk_path, ostype, dry_run=False):
    """
    Use virt-customize to inject post-v2v boot fixes into a Linux guest disk
    before it is imported into Proxmox.

    Fixes applied:
      1. NetworkManager ordering drop-in — resolves a systemd dependency cycle
         introduced by virt-v2v that causes NM to be silently skipped on boot.
         Symptom: NM dead with zero journal entries, nmcli shows no IPs.

      2. guestfs-firstboot disable — virt-v2v installs guestfs-firstboot.service
         which runs one-shot scripts on first boot then leaves itself enabled,
         contributing to the ordering cycle on every subsequent boot.

    Only runs for Linux ostypes (l24, l26, other). Skipped for Windows.
    virt-customize is a no-op if it cannot mount the disk (e.g. encrypted LVM)
    — in that case a warning is printed and the import continues.
    """
    if ostype not in ("l24", "l26", "other"):
        return  # Windows or unknown — skip

    if not shutil.which("virt-customize"):
        warn("virt-customize not found — skipping post-conversion boot fixes.")
        warn("Apply manually: see NET-VIRT-V2V-002 Scenario 1 Step 8.")
        return

    section("POST-CONVERSION LINUX BOOT FIXES")
    info("Injecting systemd fixes into guest disk via virt-customize...")
    info(f"Disk: {disk_path}")

    NM_DROPIN_DIR  = "/etc/systemd/system/NetworkManager.service.d"
    NM_DROPIN_FILE = f"{NM_DROPIN_DIR}/override.conf"
    NM_DROPIN_CONTENT = (
        "[Unit]\\n"
        "# Explicit ordering to fix cycle introduced by virt-v2v migration.\\n"
        "# NM brings up network.target -- it must not also wait for it.\\n"
        "# Written by convert-v2v.py\\n"
        "After=network-pre.target\\n"
        "After=dbus.service\\n"
        "Before=network.target\\n"
    )

    # Shell script that runs inside the guest disk
    # - Writes the NM drop-in
    # - Disables guestfs-firstboot if its scripts dir is empty
    inline_script = (
        f"mkdir -p {NM_DROPIN_DIR} && "
        f"printf '{NM_DROPIN_CONTENT}' > {NM_DROPIN_FILE} && "
        f"echo 'NM drop-in written' && "
        f"if systemctl is-enabled guestfs-firstboot.service 2>/dev/null; then "
        f"  if [ -z \"$(ls -A /usr/lib/virt-sysprep/scripts 2>/dev/null)\" ]; then "
        f"    systemctl disable guestfs-firstboot.service && "
        f"    echo 'guestfs-firstboot disabled'; "
        f"  else "
        f"    echo 'guestfs-firstboot has pending scripts - leaving enabled'; "
        f"  fi; "
        f"else "
        f"  echo 'guestfs-firstboot not present - skipping'; "
        f"fi"
    )

    cmd = [
        "virt-customize",
        "-a", disk_path,
        "--run-command", inline_script,
    ]

    if dry_run:
        dry(f"Would run: {' '.join(shlex.quote(a) for a in cmd)}")
        return

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            ok("NetworkManager ordering drop-in injected.")
            ok("guestfs-firstboot handled.")
            if result.stdout.strip():
                for line in result.stdout.strip().splitlines():
                    info(f"  {line}")
        else:
            warn("virt-customize exited non-zero — boot fixes may not have been applied.")
            warn("This can happen with encrypted LVM or unusual partition layouts.")
            warn("Apply manually post-boot: see NET-VIRT-V2V-002 Scenario 1 Step 8.")
            if result.stderr.strip():
                for line in result.stderr.strip().splitlines()[-10:]:
                    print(f"  {C.D}{line}{C.NC}")
    except subprocess.TimeoutExpired:
        warn("virt-customize timed out — boot fixes not applied.")
        warn("Apply manually post-boot: see NET-VIRT-V2V-002 Scenario 1 Step 8.")
    except Exception as e:
        warn(f"virt-customize failed: {e}")
        warn("Apply manually post-boot: see NET-VIRT-V2V-002 Scenario 1 Step 8.")


def _virtio_os_subdir(ostype, guest_os_raw):
    """Map Proxmox ostype + VMX guest OS string to the virtio-win driver subdirectory.

    virtio-win driver layout:
        /usr/share/virtio-win/<driver>/<os_subdir>/amd64/*.inf

    OS subdirectory names used by virtio-win:
        2k22   — Windows Server 2022
        2k19   — Windows Server 2019
        2k16   — Windows Server 2016
        2k12R2 — Windows Server 2012 R2
        2k12   — Windows Server 2012
        2k8R2  — Windows Server 2008 R2
        2k8    — Windows Server 2008
        w11    — Windows 11
        w10    — Windows 10
        w8.1   — Windows 8.1
        w8     — Windows 8
        w7     — Windows 7

    We check the raw VMX guest OS string first (most accurate), then fall back
    to the Proxmox ostype.
    """
    raw = guest_os_raw.lower()

    # VMX raw string — authoritative
    if "windows2019srvnext" in raw or "2022" in raw:
        return "2k22"
    if "windows2019srv" in raw or "2019" in raw:
        return "2k19"
    if "windows9srv" in raw or "2016" in raw:
        return "2k16"
    if "windows8srv" in raw and "r2" in raw:
        return "2k12R2"
    if "windows8srv" in raw:
        return "2k12"
    if "windows7srv" in raw and "r2" in raw:
        return "2k8R2"
    if "windows7srv" in raw:
        return "2k8"
    if "windows11" in raw or "win11" in raw:
        return "w11"
    if "windows9" in raw or "win10" in raw:
        return "w10"

    # Proxmox ostype fallback
    fallback = {
        "win11": "2k22",   # Server 2022 / Win11
        "win10": "2k19",   # Server 2019 / Win10 (conservative)
        "win8":  "2k12R2",
        "win7":  "2k8R2",
        "wvista":"2k8",
    }
    return fallback.get(ostype, "2k22")   # default to 2k22 if unknown


def apply_windows_driver_injection(disk_path, ostype, guest_os_raw, dry_run=False):
    """Inject VirtIO storage drivers offline into a Windows guest disk before
    import, preventing INACCESSIBLE_BOOT_DEVICE (BSOD 0x7B) on first boot.

    Root cause
    ----------
    virt-v2v converts the disk and switches the bus to virtio, but the SYSTEM
    registry hive in the guest still has the old VMware driver (vmscsi/pvscsi)
    registered as Start=0 (boot-start). vioscsi/viostor are either absent or
    set to Start=3 (demand-start). Windows cannot mount the boot volume and
    BSODs with INACCESSIBLE_BOOT_DEVICE before any user-mode code runs.

    Why --firstboot-command does NOT work here
    ------------------------------------------
    --firstboot-command runs inside Windows AFTER it boots. Windows never
    reaches that point — the BSOD is in the kernel during driver init.
    The fix must happen OFFLINE, before the disk is ever started.

    Correct approach — two offline steps
    --------------------------------------
    1. virt-customize --upload  : copies vioscsi.sys + viostor.sys into
       /Windows/System32/drivers/ on the guest disk. Pure file copy — no
       Windows involved.

    2. virt-win-reg --merge     : writes SERVICE registry keys directly into
       the offline SYSTEM hive via hivex. Equivalent to
         DISM /image:C:\ /add-driver
       but without needing a running Windows or a WinPE environment.
       Keys: HKLM\SYSTEM\{Current,001,002}\Services\{vioscsi,viostor}
       Both with Start=0 (SERVICE_BOOT_START), Type=1 (SERVICE_KERNEL_DRIVER).

    Tools required
    --------------
    - virt-customize  (apt install libguestfs-tools)
    - virt-win-reg    (apt install libguestfs-tools)
    Fallback: hivexregedit (apt install hivex) if virt-win-reg absent.

    OS subdir
    ---------
    virtio-win uses per-OS subdirs: 2k22, 2k19, 2k16, w10, w11, etc.
    _virtio_os_subdir() maps ostype + raw VMX guest OS string to the right one.
    """
    WIN_OSTYPES = {"win10", "win11", "win8", "win7", "wvista", "wxp",
                   "w2k8", "w2k3", "w2k"}
    if ostype not in WIN_OSTYPES:
        return

    section("WINDOWS — OFFLINE VIRTIO DRIVER INJECTION")
    info("Injecting vioscsi + viostor OFFLINE to prevent BSOD 0x7B (inaccessible boot device)...")
    info(f"Guest disk : {disk_path}")

    # ── Locate driver source files ────────────────────────────────────────────
    os_subdir   = _virtio_os_subdir(ostype, guest_os_raw)
    info(f"OS subdir  : {os_subdir}  (ostype={ostype}, raw='{guest_os_raw}')")

    vioscsi_dir = os.path.join(VIRTIO_WIN_DIR, "vioscsi", os_subdir, "amd64")
    viostor_dir = os.path.join(VIRTIO_WIN_DIR, "viostor",  os_subdir, "amd64")

    vioscsi_sys = os.path.join(vioscsi_dir, "vioscsi.sys")
    viostor_sys  = os.path.join(viostor_dir,  "viostor.sys")
    vioscsi_sys = vioscsi_sys if os.path.isfile(vioscsi_sys) else None
    viostor_sys  = viostor_sys  if os.path.isfile(viostor_sys)  else None

    if not vioscsi_sys and not viostor_sys:
        warn(f"Neither vioscsi.sys nor viostor.sys found under {VIRTIO_WIN_DIR}/")
        warn(f"  Looked in: {vioscsi_dir}")
        warn(f"             {viostor_dir}")
        warn("Cannot inject drivers offline — BSOD 0x7B likely on first boot.")
        warn("Manual fix from WinPE / Windows Recovery Environment:")
        warn(f"  dism /image:C:\\ /add-driver /driver:D:\\vioscsi\\{os_subdir}\\amd64 /recurse")
        warn(f"  dism /image:C:\\ /add-driver /driver:D:\\viostor\\{os_subdir}\\amd64  /recurse")
        return

    if dry_run:
        if vioscsi_sys: dry(f"Would upload {vioscsi_sys} → /Windows/System32/drivers/vioscsi.sys")
        if viostor_sys:  dry(f"Would upload {viostor_sys}  → /Windows/System32/drivers/viostor.sys")
        dry("Would write vioscsi + viostor SERVICE registry keys (Start=0) into offline SYSTEM hive")
        return

    # ── Step 1: upload .sys files into the guest disk ─────────────────────────
    # libguestfs mounts Windows C: at /  so the path is Unix-style
    upload_args = []
    uploaded    = []
    if vioscsi_sys:
        upload_args += ["--upload", f"{vioscsi_sys}:/Windows/System32/drivers/vioscsi.sys"]
        uploaded.append("vioscsi.sys")
    if viostor_sys:
        upload_args += ["--upload", f"{viostor_sys}:/Windows/System32/drivers/viostor.sys"]
        uploaded.append("viostor.sys")

    if not shutil.which("virt-customize"):
        warn("virt-customize not found — cannot upload .sys files (apt install libguestfs-tools)")
    else:
        info(f"Uploading {', '.join(uploaded)} → guest System32\\drivers\\...")
        r = subprocess.run(
            ["virt-customize", "-a", disk_path] + upload_args,
            capture_output=True, text=True, timeout=300
        )
        if r.returncode == 0:
            ok(f"  Uploaded: {', '.join(uploaded)}")
        else:
            warn(f"virt-customize --upload failed: {r.stderr.strip()[-300:]}")
            warn("Continuing to registry step — .sys files may already be present from virt-v2v.")

    # ── Step 2: write boot-start SERVICE keys into the offline SYSTEM hive ───
    # Minimum registry structure for a boot-start kernel driver:
    #   Type        = 1  (SERVICE_KERNEL_DRIVER)
    #   Start       = 0  (SERVICE_BOOT_START — loaded by bootmgr, before any disk access)
    #   ErrorControl = 1 (SERVICE_ERROR_NORMAL)
    #   ImagePath   = system32\drivers\<name>.sys  (REG_EXPAND_SZ)
    #   Group       = SCSI miniport  (load order group — ensures early load)
    #
    # We write to CurrentControlSet, ControlSet001, and ControlSet002 to cover
    # all boot paths (last known good, current, etc.)
    #
    # ImagePath as plain string (REG_SZ) is fine here — virt-win-reg handles it.
    # No need for UTF-16LE hex encoding in the .reg file.

    import tempfile
    reg_content = (
        "Windows Registry Editor Version 5.00\n\n"
    )
    for driver in ("vioscsi", "viostor"):
        for cs in ("CurrentControlSet", "ControlSet001", "ControlSet002"):
            reg_content += (
                f"[HKEY_LOCAL_MACHINE\\SYSTEM\\{cs}\\Services\\{driver}]\n"
                f"\"Type\"=dword:00000001\n"
                f"\"Start\"=dword:00000000\n"
                f"\"ErrorControl\"=dword:00000001\n"
                f"\"ImagePath\"=\"system32\\\\drivers\\\\{driver}.sys\"\n"
                f"\"Group\"=\"SCSI miniport\"\n\n"
            )

    reg_file = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".reg",
                                         prefix="virtio-drv-", delete=False) as f:
            f.write(reg_content)
            reg_file = f.name

        if shutil.which("virt-win-reg"):
            info("Writing SERVICE keys into offline SYSTEM hive via virt-win-reg...")
            r = subprocess.run(
                ["virt-win-reg", "--merge", disk_path, reg_file],
                capture_output=True, text=True, timeout=120
            )
            if r.returncode == 0:
                ok("vioscsi: Start=0 (boot-start) written to SYSTEM hive.")
                ok("viostor:  Start=0 (boot-start) written to SYSTEM hive.")
                info("VM should now boot without BSOD 0x7B.")
            else:
                warn(f"virt-win-reg --merge failed: {r.stderr.strip()[-300:]}")
                warn("Manual recovery — from WinPE or Windows Recovery Console:")
                warn(f"  dism /image:C:\\ /add-driver /driver:D:\\vioscsi\\{os_subdir}\\amd64 /recurse")
                warn(f"  dism /image:C:\\ /add-driver /driver:D:\\viostor\\{os_subdir}\\amd64  /recurse")

        elif shutil.which("hivexregedit"):
            warn("virt-win-reg not found — falling back to hivexregedit.")
            warn("This fallback is best-effort; install libguestfs-tools for the reliable path.")
            _try_hivexregedit_fallback(disk_path, reg_file, os_subdir)

        else:
            warn("Neither virt-win-reg nor hivexregedit found.")
            warn("Install: apt install libguestfs-tools   (provides virt-win-reg)")
            warn("Cannot write registry keys — BSOD 0x7B likely on first boot.")
            warn("Manual fix from WinPE or Windows Recovery Console:")
            warn(f"  dism /image:C:\\ /add-driver /driver:D:\\vioscsi\\{os_subdir}\\amd64 /recurse")
            warn(f"  dism /image:C:\\ /add-driver /driver:D:\\viostor\\{os_subdir}\\amd64  /recurse")
            warn("  (where D: is the virtio-win ISO attached as a CDROM)")

    finally:
        if reg_file and os.path.exists(reg_file):
            os.unlink(reg_file)


def _try_hivexregedit_fallback(disk_path, reg_file, os_subdir):
    """Fallback: inject SERVICE registry keys via hivexregedit when virt-win-reg
    is not installed. Mounts the disk read-only, extracts the SYSTEM hive,
    patches it, then writes it back via a separate rw guestmount.
    More fragile than virt-win-reg — treat as last resort.
    """
    import tempfile, shutil as _shutil
    mnt_ro = tempfile.mkdtemp(prefix="v2v-win-ro-")
    mnt_rw = tempfile.mkdtemp(prefix="v2v-win-rw-")
    rw_hive = os.path.join(tempfile.gettempdir(), "SYSTEM.v2v.tmp")
    try:
        # Mount read-only to extract the hive
        r = subprocess.run(
            ["guestmount", "-a", disk_path, "-i", "--ro", mnt_ro],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode != 0:
            warn(f"guestmount (ro) failed: {r.stderr.strip()[-200:]}")
            warn(f"hivexregedit fallback aborted.")
            warn(f"Manual fix: dism /image:C:\\ /add-driver /driver:D:\\vioscsi\\{os_subdir}\\amd64 /recurse")
            return

        hive = None
        for name in ("SYSTEM", "System", "system"):
            h = os.path.join(mnt_ro, "Windows", "System32", "config", name)
            if os.path.exists(h):
                hive = h
                break
        if not hive:
            warn("Could not locate SYSTEM hive — hivexregedit fallback failed.")
            return

        _shutil.copy2(hive, rw_hive)
        subprocess.run(["guestunmount", mnt_ro], capture_output=True)

        # Patch the hive
        r = subprocess.run(
            ["hivexregedit", "--merge", "--prefix",
             "HKEY_LOCAL_MACHINE\\SYSTEM", rw_hive, reg_file],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode != 0:
            warn(f"hivexregedit --merge failed: {r.stderr.strip()[-200:]}")
            return

        # Write back via rw mount
        r = subprocess.run(
            ["guestmount", "-a", disk_path, "-i", mnt_rw],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode != 0:
            warn(f"guestmount (rw) failed — cannot write patched hive back.")
            warn(f"Patched hive is at {rw_hive} if you want to copy it manually.")
            return

        dest = os.path.join(mnt_rw, "Windows", "System32", "config", os.path.basename(hive))
        _shutil.copy2(rw_hive, dest)
        subprocess.run(["guestunmount", mnt_rw], capture_output=True)
        ok("hivexregedit: SERVICE keys patched and written back to guest disk.")

    finally:
        for mnt in (mnt_ro, mnt_rw):
            subprocess.run(["guestunmount", mnt], capture_output=True, timeout=15)
            try: os.rmdir(mnt)
            except Exception: pass
        if os.path.exists(rw_hive):
            try: os.unlink(rw_hive)
            except Exception: pass

def apply_windows_firstboot_fixes(disk_path, agent_msi_path, dry_run=False):
    """Use virt-customize to inject a firstboot script into a Windows guest disk
    that silently installs the QEMU guest agent on the VM's first boot.

    Mechanism
    ---------
    virt-customize --firstboot-command injects a CMD script into the guest and
    registers it as a Windows RunOnce registry entry. On the first boot after
    conversion Windows runs the script once as SYSTEM, then removes the entry.

    The guest agent MSI lives on the host at:
        /usr/share/virtio-win/guest-agent/qemu-ga-x86_64.msi

    virt-customize copies it into the guest disk at:
        C:\\Windows\\Temp\\qemu-ga-x86_64.msi

    The firstboot CMD script then runs:
        msiexec /i C:\\Windows\\Temp\\qemu-ga-x86_64.msi /quiet /norestart

    This avoids relying on the virtio-win ISO CDROM being attached at the time
    the guest agent runs (the CDROM may not be drive D: if the VM has additional
    drives, and the ISO may be detached before first boot in some workflows).

    Only runs for Windows ostypes (win10, win11, win8, win7, wvista, wxp).
    Skipped if agent_msi_path is None (MSI not found — already warned upstream).
    Skipped if virt-customize is not available — warning printed, import continues.
    """
    win_ostypes = {"win10", "win11", "win8", "win7", "wvista", "wxp",
                   "w2k8", "w2k3", "w2k"}
    # ostype is not passed in directly — caller guards on WINDOWS_ROLES, but
    # we also accept any call and check agent_msi_path as the real gate.
    if not agent_msi_path:
        return   # already warned in check_virtio_drivers()

    if not shutil.which("virt-customize"):
        warn("virt-customize not found — skipping Windows firstboot guest agent install.")
        warn("Install manually post-boot from the virtio-win ISO (D:\\guest-agent\\)")
        return

    section("WINDOWS FIRSTBOOT — GUEST AGENT INSTALL")
    info("Injecting QEMU guest agent firstboot installer into guest disk...")
    info(f"Source MSI : {agent_msi_path}")
    info(f"Guest disk : {disk_path}")

    # Destination path inside the guest.
    # libguestfs mounts the Windows C: drive at / internally, so paths are
    # Unix-style: /Windows/Temp not C:\Windows\Temp
    guest_msi_dest = "/Windows/Temp/qemu-ga-x86_64.msi"

    # CMD command that runs as RunOnce on first boot.
    # We reference the Windows path here since this runs inside Windows.
    # /quiet = no UI, /norestart = don't reboot mid-firstboot sequence
    firstboot_cmd = (
        "msiexec /i \"C:\\Windows\\Temp\\qemu-ga-x86_64.msi\" /quiet /norestart "
        "&& del /f /q \"C:\\Windows\\Temp\\qemu-ga-x86_64.msi\""
    )

    cmd = [
        "virt-customize",
        "-a",               disk_path,
        "--copy-in",        f"{agent_msi_path}:/Windows/Temp",
        "--firstboot-command", firstboot_cmd,
    ]

    if dry_run:
        dry(f"Would run: {' '.join(shlex.quote(a) for a in cmd)}")
        dry(f"  Copies {GUEST_AGENT_MSI} into guest C:\\Windows\\Temp\\")
        dry(f"  Registers RunOnce: {firstboot_cmd}")
        return

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode == 0:
            ok(f"Guest agent MSI copied into guest disk.")
            ok(f"RunOnce entry registered — agent will install silently on first boot.")
            if result.stdout.strip():
                for line in result.stdout.strip().splitlines():
                    info(f"  {line}")
        else:
            warn("virt-customize exited non-zero — guest agent firstboot injection may have failed.")
            warn("Install manually post-boot from the virtio-win ISO (D:\\guest-agent\\)")
            if result.stderr.strip():
                for line in result.stderr.strip().splitlines()[-10:]:
                    print(f"  {C.D}{line}{C.NC}")
    except subprocess.TimeoutExpired:
        warn("virt-customize timed out — guest agent firstboot not injected.")
        warn("Install manually post-boot from the virtio-win ISO (D:\\guest-agent\\)")
    except Exception as e:
        warn(f"virt-customize failed: {e}")
        warn("Install manually post-boot from the virtio-win ISO (D:\\guest-agent\\)")


# =============================================================================
# ONE CONVERSION FLOW
# =============================================================================

def convert_one(args, proxmox, node, host, mode):
    """Full flow for one VM conversion. Returns True on success."""

    # ── Locate VMX ────────────────────────────────────────────────────────────
    vmx_path = select_vmx(args.search_path)
    vmx      = parse_vmx(vmx_path)
    hw       = extract_hardware(vmx, vmx_path)

    section("VMX PARSED HARDWARE")
    print_vmx_summary(hw)

    if not confirm("Proceed with this source VM?", default="y"):
        warn("Skipped.")
        return False

    # ── Naming ────────────────────────────────────────────────────────────────
    section("TARGET VM IDENTITY")

    existing_vms   = get_existing_vms(proxmox, node)
    existing_ids   = set(existing_vms.keys())
    existing_names = set(existing_vms.values())

    suggested_role = guess_role_from_vmx(hw)
    suggested_site = guess_site_from_vmx(hw, vmx_path)
    role = select_role(suggested=suggested_role)
    site = select_site(suggested=suggested_site)

    suggested_suffix = next_free_name_suffix(existing_names, role, site)
    suggested_name   = f"EXA{role}{site}{suggested_suffix}"
    info(f"Next available name: {C.W}{suggested_name}{C.NC}")

    def validate_name(v):
        v = v.upper()
        if not re.match(r"^EXA[A-Z]{3}[A-Z]{3}[0-9]{3}$", v):
            return "Name must follow pattern EXA[ROLE][SITE][NNN] e.g. EXAFWLFAL001"
        if v in {n.upper() for n in existing_names}:
            return f"Name {v} already exists on this node."
        return True

    vm_name = prompt("VM name", default=suggested_name, validator=validate_name).upper()
    ok(f"Name: {vm_name}")

    suggested_vmid = next_free_vmid(existing_ids)
    info(f"Next free VM ID: {C.W}{suggested_vmid}{C.NC}")

    def validate_vmid(v):
        if not v.isdigit():
            return "VM ID must be a number."
        vid = int(v)
        if vid < 1000:
            return "VM IDs must be >= 1000."
        if vid in existing_ids:
            return f"VM ID {vid} is already in use."
        return True

    vmid = int(prompt("VM ID", default=str(suggested_vmid), validator=validate_vmid))
    ok(f"VM ID: {vmid}")

    # ── OS type ───────────────────────────────────────────────────────────────
    section("OPERATING SYSTEM")
    info(f"VMX guest OS: {hw['guest_os_raw']}  →  suggested Proxmox ostype: {hw['os_guess']}")

    # Proxmox ostype enum — source: https://pve.proxmox.com/wiki/Manual:_qm.conf
    # Valid values: l24 | l26 | other | solaris | w2k | w2k3 | w2k8 |
    #               win7 | win8 | win10 | win11 | wvista | wxp
    #
    # IMPORTANT: w2k12, w2k16, w2k19, w2k22 do NOT exist as ostype values.
    # The Proxmox UI labels map as follows (confirmed via pve-qemu source):
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
    default_os_choice = next(
        (k for k, (t, _) in OS_TYPES.items() if t == hw["os_guess"]),
        "1"
    )
    print()
    for k, (ostype, desc) in OS_TYPES.items():
        print(f"  {C.CY}  {k:>2}{C.NC}  {desc}")
    print()
    os_choice = prompt("Select OS type", default=default_os_choice,
                       validator=lambda v: True if v in OS_TYPES else "Invalid choice")
    ostype = OS_TYPES[os_choice][0]
    ok(f"OS type: {OS_TYPES[os_choice][1]} ({ostype})")

    # ── VirtIO driver check (Windows VMs only) ────────────────────────────────
    # Check BEFORE storage/NIC prompts so the engineer understands the
    # implications before committing to the conversion settings.
    # Hard-exits if drivers are missing — see check_virtio_drivers() docstring.
    virtio_drivers_ready = False
    agent_msi_path       = None
    if role in WINDOWS_ROLES:
        virtio_drivers_ready, agent_msi_path = check_virtio_drivers()

    # ── Storage ───────────────────────────────────────────────────────────────
    section("STORAGE")
    storage, storage_type, disk_format = select_storage(proxmox, node)

    # ── Console ───────────────────────────────────────────────────────────────
    section("CONSOLE")
    console = select_console(role)

    # ── BIOS ROM ──────────────────────────────────────────────────────────────
    section("BIOS ROM")
    bios_type, bios_rom = select_bios_rom_v2v(proxmox, node)

    # ── BMC / IPMI emulation ──────────────────────────────────────────────────
    section("BMC / IPMI EMULATION")
    bmc_type = select_bmc_v2v(role, hw)

    # ── NICs ──────────────────────────────────────────────────────────────────
    nics = configure_nics(role, site, hw)

    # ── Pool ──────────────────────────────────────────────────────────────────
    section("POOL")
    pool = select_pool(proxmox, site)

    # ── VirtIO ISO CDROM (Windows VMs — optional fallback) ───────────────────
    # Drivers are injected by virt-v2v automatically from /usr/share/virtio-win/.
    # Guest agent is installed on first boot by apply_windows_firstboot_fixes().
    # The CDROM is still useful as a fallback for:
    #   a) Manual driver install via Device Manager if auto-injection missed any
    #   b) balloon driver MSI if not covered by virt-v2v injection
    #   c) 32-bit guest agent (qemu-ga-i386.msi) if needed
    virtio_iso = select_virtio_iso(proxmox, node, role, drivers_ready=virtio_drivers_ready)

    # ── Upload / file prep (mode-dependent) ──────────────────────────────────
    remote_vmx           = vmx_path
    remote_staging_paths = []   # files on Proxmox node to clean up after import

    if mode == "workstation":
        info("WORKSTATION mode — virt-v2v runs locally, then pushes converted disk to Proxmox")
        # The pushed disk will land here on the Proxmox node — mark for cleanup
        remote_staging_paths.append(
            f"{args.staging_dir}/{os.path.basename(vmx_path).replace('.vmx', '-sda')}"
        )

    elif mode == "remote":
        section("UPLOAD RAW VM FOLDER TO PROXMOX")
        warn("REMOTE mode — virt-v2v runs on the Proxmox node via SSH.")
        warn("Raw VMDKs must be uploaded first (larger transfer than qcow2).")
        warn("Consider installing virt-v2v locally to use WORKSTATION mode instead.")
        print()
        if confirm("Upload VM folder to Proxmox node now?", default="y"):
            remote_vmx = upload_vm_folder(
                vmx_path, host, args.ssh_user, args.ssh_key,
                args.staging_dir, dry_run=args.dry_run
            )
            remote_staging_paths.append(os.path.dirname(remote_vmx))
        else:
            info("Skipping upload — assuming files are already on Proxmox node.")
            remote_vmx = prompt("Remote VMX path on Proxmox node")

    # local mode: mark the virt-v2v output dir for cleanup
    if mode == "local":
        remote_staging_paths.append(args.staging_dir.rstrip("/") + "-output")

    # ── virt-v2v output dir ───────────────────────────────────────────────────
    v2v_output_dir = args.staging_dir.rstrip("/") + "-output"
    info(f"virt-v2v output directory : {v2v_output_dir}")
    info(f"Disk format for {storage} : {disk_format}"
         f"  ({'ZFS/LVM block storage' if disk_format == 'raw' else 'file-based storage'})")

    # ── Summary + confirmation ────────────────────────────────────────────────
    print_conversion_summary(vmid, vm_name, remote_vmx, hw, storage, nics,
                             console, ostype, pool, mode,
                             bios_type=bios_type, bios_rom=bios_rom,
                             bmc_type=bmc_type, dry_run=args.dry_run)
    if not confirm("Proceed with conversion?", default="n"):
        warn("Conversion cancelled.")
        return False

    # ── NTFS dirty-flag check ─────────────────────────────────────────────────
    # Only meaningful for local/workstation modes where we have direct VMDK
    # access. In remote mode the VMDKs are already on the Proxmox node and
    # ntfsfix would need to run there instead — skip with a reminder.
    if mode == "remote":
        info("NTFS dirty check skipped in REMOTE mode.")
        info("If virt-v2v fails with 'unclean file system' on the Proxmox node, run:")
        info("  qemu-nbd --connect /dev/nbd0 --format=vmdk <vmdk>")
        info("  ntfsfix -d /dev/nbd0pN")
        info("  qemu-nbd --disconnect /dev/nbd0")
    else:
        check_ntfs_dirty(hw["disk_paths"], dry_run=args.dry_run)

    # ── Run virt-v2v ──────────────────────────────────────────────────────────
    disk_out = run_virt_v2v(
        vmx_path    = remote_vmx,
        output_dir  = v2v_output_dir,
        host        = host,
        ssh_user    = args.ssh_user,
        ssh_key     = getattr(args, "ssh_key", None),
        mode        = mode,
        staging_dir = args.staging_dir,
        disk_format = disk_format,
        dry_run     = args.dry_run,
    )

    # ── Import + wire VM ──────────────────────────────────────────────────────
    # Apply OS-specific post-conversion fixes to the disk before importing.
    # Linux:   NM ordering drop-in + guestfs-firstboot disable (virt-customize)
    # Windows: offline driver injection (virt-win-reg) MUST run first to prevent
    #          BSOD 0x7B (INACCESSIBLE_BOOT_DEVICE) — writes vioscsi/viostor
    #          SERVICE keys with Start=0 directly into the offline SYSTEM hive.
    #          Then guest agent MSI is staged for RunOnce on first boot.
    apply_linux_boot_fixes(disk_out, ostype, dry_run=args.dry_run)
    if role in WINDOWS_ROLES:
        apply_windows_driver_injection(disk_out, ostype, hw["guest_os_raw"],
                                       dry_run=args.dry_run)
        apply_windows_firstboot_fixes(disk_out, agent_msi_path, dry_run=args.dry_run)

    success = import_and_wire(
        proxmox              = proxmox,
        node                 = node,
        disk_out             = disk_out,
        vmid                 = vmid,
        vm_name              = vm_name,
        hw                   = hw,
        storage              = storage,
        storage_type         = storage_type,
        disk_format          = disk_format,
        nics                 = nics,
        console              = console,
        ostype               = ostype,
        pool                 = pool,
        virtio_iso           = virtio_iso,
        bios_type            = bios_type,
        bios_rom             = bios_rom,
        bmc_type             = bmc_type,
        remote_staging_paths = remote_staging_paths,
        dry_run              = args.dry_run,
    )

    if success:
        write_log(args.log, vmid, vm_name, node, hw, storage, nics,
                  console, remote_vmx, pool,
                  bios_type=bios_type, bios_rom=bios_rom,
                  bmc_type=bmc_type, dry_run=args.dry_run)
        # Serial console guest OS advisory
        print_serial_advisory(
            vmid     = vmid,
            ostype   = ostype,
            console  = console,
            bmc_type = bmc_type,
        )

    # ── Start? ────────────────────────────────────────────────────────────────
    if success and not args.dry_run:
        section("START VM")
        warn("Before starting — verify NIC naming is correct (see advisory above).")
        warn("If firewallme.sh / WireGuard is on this VM, see NET-VPN-WG-001.")
        print()
        if confirm(f"Start VM {vmid} ({vm_name}) now?", default="n"):
            step(f"Starting VM {vmid}...")
            try:
                proxmox.nodes(node).qemu(vmid).status.start.post()
                ok(f"VM {vmid} started")
            except Exception as e:
                warn(f"Failed to start VM: {e}")
                warn(f"Start manually: qm start {vmid}")
        else:
            info(f"VM left stopped. Start when ready: qm start {vmid}")

    # ── Done ──────────────────────────────────────────────────────────────────
    print()
    print(f"{C.G}  +============================================================+{C.NC}")
    print(f"{C.G}  |{C.W}  {'[DRY RUN] ' if args.dry_run else ''}CONVERSION COMPLETE{'':<43}{C.G}|{C.NC}")
    print(f"{C.G}  +============================================================+{C.NC}")
    print()
    if not args.dry_run:
        ok(f"VM ID  : {C.W}{vmid}{C.NC}")
        ok(f"Name   : {C.W}{vm_name}{C.NC}")
        ok(f"Node   : {C.W}{node}{C.NC}")
    print()
    return success

# =============================================================================
# MAIN
# =============================================================================

def main():
    args = parse_args()

    print()
    print(f"{C.CY}  +============================================================+{C.NC}")
    print(f"{C.CY}  |{C.W}      PROXMOX VE — VMware V2V CONVERSION                  {C.CY}|{C.NC}")
    print(f"{C.CY}  |{C.D}             jukebox.internal                              {C.CY}|{C.NC}")
    if args.dry_run:
        print(f"{C.CY}  |{C.B}             *** DRY RUN — NO CHANGES ***               {C.CY}|{C.NC}")
    if args.bulk:
        print(f"{C.CY}  |{C.B}             *** BULK MODE — Ctrl+C to exit ***         {C.CY}|{C.NC}")
    print(f"{C.CY}  +============================================================+{C.NC}")
    print()

    # ── Connect ───────────────────────────────────────────────────────────────
    section("CONNECTING TO PROXMOX")
    if args.dry_run:
        warn("Dry run mode — no changes will be made")

    proxmox, host = connect(args)
    node          = select_node(proxmox, args)

    # ── Detect local vs remote ────────────────────────────────────────────────
    mode = detect_mode(host)

    if mode == "workstation":
        ok("Mode: WORKSTATION — virt-v2v runs here, only qcow2 pushed to Proxmox")
        info("This is the recommended mode — smallest network transfer, cleanest pipeline")
    elif mode == "local":
        ok("Mode: LOCAL — running directly on the Proxmox node")
        info("virt-v2v will run via subprocess; no file transfers needed")
    else:
        ok(f"Mode: REMOTE — virt-v2v not found locally, will run on {host} via SSH")
        warn("Raw VMDKs will need uploading before conversion — larger network transfer")
        warn("Consider: apt install virt-v2v  to switch to WORKSTATION mode")

    # ── Binary checks ─────────────────────────────────────────────────────────
    # check_binaries may switch mode from workstation→remote if virt-v2v is absent
    mode = check_binaries(mode) or mode

    # ── Conversion loop ───────────────────────────────────────────────────────
    vm_count = 0
    while True:
        try:
            convert_one(args, proxmox, node, host, mode)
            vm_count += 1
        except KeyboardInterrupt:
            print(f"\n\n  {C.Y}[!]{C.NC} Interrupted.\n")
            break

        if not args.bulk:
            break

        print()
        print(f"{C.CY}  ── Bulk mode: {vm_count} VM(s) converted this session ──────────────{C.NC}")
        if not confirm("Convert another VM?", default="y"):
            break

    if args.bulk and vm_count > 0:
        print()
        ok(f"Session complete — {vm_count} VM(s) converted.")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {C.Y}[!]{C.NC} Interrupted — no changes made.\n")
        sys.exit(0)
