#!/usr/bin/env python3

"""
Proxmox Environment Audit Tool

This script audits a Proxmox cluster against infrastructure conventions used
in the EXA lab environment.

It validates:

- Hostname structure (EXA + ROLE + SITE + ###)
- VLAN tagging vs site subnet conventions
- Role-based NIC policy
- Proxmox pool placement
- Backup configuration presence

The environment uses deterministic naming and networking rules where:

SITE → subnet third octet → VLAN ID → pool name

Example:
GLA → 192.168.141.0/24 → VLAN 141 → pool "GLA"

======================================================================
Proxmox Inventory Auditor
======================================================================

Full Version History:

v1.0   - Initial release
        • Basic inventory vs Proxmox VM comparison
        • Simple IP matching
        • Output [FOUND]/[FAILURE] flags
        • Hard-coded single IP per VM
        • 4-space indentation

v1.1   - Minor fixes
        • Fixed IP parsing for inventory
        • Added basic getent fallback for hostname resolution
        • Corrected minor output alignment

v1.2   - Multiple IPs handling
        • VMs can now have multiple IP addresses
        • Loopback and link-local IPs ignored
        • Updated output formatting for multiple IPs

v1.3   - Color coding introduced
        • [CONNECTED], [RUNNING], [WARNING], [FAILURE]
        • ANSI colors for better readability
        • Added info(), ok(), warn(), err() functions

v1.4   - DNS + getent hostname resolution
        • resolve_dns_or_getent() returns both IP and hostname
        • Fallback if DNS fails
        • Multiple attempts for matching inventory hosts

v1.5   - Confidence scoring
        • HIGH: hostname match
        • MEDIUM: IP match
        • LOW: unresolved
        • Flags list introduced for NO_IP, NO_BACKUP, SUBNET_MISMATCH

v1.6   - Subnet support
        • --subnet argument added
        • Checks if VM IPs fall within subnet
        • Marks SUBNET_MISMATCH in flags

v1.7   - Backup detection
        • detect_backups() queries cluster backup jobs
        • Flags NO_BACKUP if VM not in any backup job
        • Supports all-inclusive backup jobs (all=1)

v1.8   - [MISMATCH] status
        • VM name always wins
        • IPs are helpful, mismatch between inventory IP and VM IP flagged
        • Replaces older [FOUND]/[FAILURE] logic for running VMs

v1.9   - Audit improvements
        • Properly detects VMs not in inventory
        • Handles VMs with no IP addresses
        • Duplicate IP detection added

v2.0   - Clean-up & stability
        • 2-space indentation
        • Fixed inventory ↔ VM ↔ hostname matching
        • Proper getent parsing: returns IP and hostname
        • Status flags updated: [CONNECTED], [RUNNING], [WARNING], [FAILURE], [MISMATCH]
        • Colour coding preserved
        • History header updated to track all prior versions

v2.1   -  Enumerate mismatches
        • Added [MISMATCH] flag when inventory IP differs from VM IP
        • Preserved full history, multi-IP handling, subnet, and backup checks

v2.2   - Clean handling
        • Improved Proxmox authentication error handling
        • Script now exits cleanly on connection or credential failure
        • Prevents Python traceback crashes when API login fails

v2.3   - Pool verification
        • Added Proxmox pool validation
        • VM pool now checked against site code derived from hostname
        • Flags [Failure] when VM pool does not match expected site

v3.0   - NIC Parsing
        • Added role-aware multi-NIC parsing and validation
        • Script now inspects all NICs (net0..netN) in VM configuration
        • Implemented firewall NIC policy (≥1 untagged WAN + ≥1 tagged LAN)
        • Added infrastructure role enforcement (single NIC expected)

v3.1   - VLAN Tagging checks
        • Added multi-NIC role support for automation and monitoring systems
        • Roles such as ANS, MON, LAB may have multiple NICs
        • Validates VLAN tags against known site VLAN list

v4.0   - Hosts and Ansible inventory generation
        • --generate-hosts   generates /etc/hosts from sites.csv
        • --generate-inventory  generates Ansible inventory from sites.csv
        • Both can be used standalone (no Proxmox connection needed)
        • Hosts file: all known static IPs per site, grouped by role,
          sorted by subnet octet descending within each role group
        • Ansible inventory: INI format, grouped by role and by
          ansible_region, plus [all:vars] with common vars
        • BRD (legacy alias for BER) skipped -- BER entries cover it
        • EXARTR (.1) included in both -- unmanaged hardware, useful reference
        • Cross-check mode: --audit + --generate-hosts flags together
          flag discrepancies between live Proxmox state and expected hosts

v3.2   - Refactoring for maintenence 
        • Refactored code formatting to consistent two-space indentation
        • Normalised whitespace and removed excessive blank lines
        • Added function documentation and inline comments
        • Removed unused imports for improved maintainability

v5.0   - devices.csv integration
        • --devices-csv flag to specify devices.csv path (single source of
          truth for all devices across all sites)
        • devices.csv loaded alongside sites.csv when present
        • --validate-devices  validates devices.csv structure and cross-checks
          site codes against sites.csv, flags unknown sites, duplicate IPs,
          HostOctet conflicts against SUFFIX_MAP convention
        • --generate-hosts now uses devices.csv when available, falling back
          to SUFFIX_MAP derivation from sites.csv if not present
        • --generate-inventory likewise uses devices.csv when available
        • CLD black swan handling: CLD rows bypass convention checks since
          192.168.139.0/24 is the provisioning network with manually assigned
          IPs that do not follow the standard site SUFFIX_MAP
        • BRD site preserved as legacy code pending BER rename on reunification
        • Non-networked assets (blank HostOctet) included as comments in
          generated hosts file and skipped from Ansible inventory

======================================================================
"""

import argparse
import getpass
import sys
import re

from proxmoxer import ProxmoxAPI
from proxmoxer.backends.https import AuthenticationError

class C:
  """ANSI colour constants for terminal output."""
  RED = "\033[91m"
  GREEN = "\033[92m"
  YELLOW = "\033[93m"
  CYAN = "\033[96m"
  RESET = "\033[0m"


# Site data loaded from sites.csv (single source of truth)

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

""" SITE_SUBNETS derived from CSV above -- used by audit checks below. """


# =============================================================================
# DEVICES.CSV -- single source of truth for all devices
# =============================================================================
# CLD BLACK SWAN:
#   CLD (192.168.139.0/24) is the provisioning network. Its devices have
#   manually assigned IPs that do not follow the standard SUFFIX_MAP convention.
#   Convention checks are bypassed for all rows where Site == "CLD".
#
# Schema: Site,Hostname,HostOctet,Role,OS,Notes
#   HostOctet  -- host portion of IP only. Blank = non-networked asset.
#   Full IP    -- derived as sites.csv subnet base + HostOctet.
#   CLD IPs    -- 192.168.139.{HostOctet} (provisioning network base).
# =============================================================================

CLD_SUBNET_BASE = "192.168.139"

def _load_devices(csv_path=None):
  """
  Load device data from devices.csv.

  Searches: same directory as this script, then cwd,
  then /etc/example-music/devices.csv.
  Override with DEVICES_CSV environment variable or csv_path argument.

  Returns a list of dicts with keys matching CSV columns plus:
    full_ip  -- resolved full IP (empty string if HostOctet is blank)
    subnet_base -- first three octets of the site subnet

  Non-networked assets (blank HostOctet) are included with empty full_ip.
  Returns empty list (not an error) if devices.csv is not found.
  """
  if csv_path is None:
    csv_path = _os.environ.get("DEVICES_CSV")
  if csv_path is None:
    script_dir = _os.path.dirname(_os.path.abspath(__file__))
    candidates = [
      _os.path.join(script_dir, "devices.csv"),
      _os.path.join(_os.getcwd(), "devices.csv"),
      "/etc/example-music/devices.csv",
    ]
    for p in candidates:
      if _os.path.isfile(p):
        csv_path = p
        break

  if not csv_path or not _os.path.isfile(csv_path):
    return []

  devices = []
  with open(csv_path, newline="", encoding="utf-8") as f:
    for row in _csv_mod.DictReader(
      (line for line in f if not line.startswith("#")),
    ):
      site = row.get("Site", "").strip().upper()
      if not site or site == "SITE":
        continue

      host_octet = row.get("HostOctet", "").strip()

      # Resolve subnet base
      if site == "CLD":
        subnet_base = CLD_SUBNET_BASE
      elif site in SITES and SITES[site].get("subnet") not in (None, "N/A"):
        parts = SITES[site]["subnet"].split(".")
        subnet_base = f"{parts[0]}.{parts[1]}.{parts[2]}"
      else:
        subnet_base = ""

      full_ip = f"{subnet_base}.{host_octet}" if subnet_base and host_octet else ""

      devices.append({
        "site":        site,
        "hostname":    row.get("Hostname", "").strip().upper(),
        "host_octet":  host_octet,
        "role":        row.get("Role", "").strip().upper(),
        "os":          row.get("OS", "").strip(),
        "notes":       row.get("Notes", "").strip(),
        "subnet_base": subnet_base,
        "full_ip":     full_ip,
      })

  return devices


def validate_devices(devices, sites=None):
  """
  Validate devices.csv content.

  Checks:
    - Site code exists in sites.csv (CLD is a special case, always valid)
    - Hostname follows EXA+ROLE+SITE+NNN pattern
    - HostOctet is numeric (when present)
    - No duplicate full IPs within a site (excluding blank octets)
    - Warns if HostOctet falls inside DHCP pool (.100-.249) for non-CLD sites
    - Warns if HostOctet conflicts with SUFFIX_MAP standard assignments for
      a different role prefix

  CLD rows bypass convention checks -- see CLD BLACK SWAN note.
  """
  if sites is None:
    sites = SITES

  hostname_re = re.compile(r"^EXA[A-Z]{3}[A-Z]{3}[0-9]{3}$")

  # SUFFIX_MAP: octet -> expected role prefix (for convention conflict detection)
  suffix_role = {
    "1": "EXAFWL", "2": "EXARAC", "3": "EXARAC", "4": "EXARAC",
    "5": "EXAPVE", "6": "EXAPVE", "7": "EXAPVE",
    "10": "EXADCS", "11": "EXADCS",
    "48": "EXASBC",
    "250": "EXASWI", "251": "EXASWI", "252": "EXASWI",
    "253": "EXAFWL", "254": "EXARTR",
  }

  # Also allow EXARTR at .1 (FAL convention -- Cisco ASA as primary gateway)
  suffix_role_alt = {"1": "EXARTR"}

  errors = []
  warnings = []
  seen_ips = {}  # site -> set of full_ips

  for dev in devices:
    site = dev["site"]
    hostname = dev["hostname"]
    octet = dev["host_octet"]
    role = dev["role"]
    full_ip = dev["full_ip"]

    # Unknown site
    if site not in sites and site != "CLD":
      errors.append(f"{hostname}: unknown site code '{site}'")
      continue

    # Hostname pattern
    if hostname and not hostname_re.match(hostname):
      warnings.append(f"{hostname}: does not match EXA+ROLE+SITE+NNN pattern")

    # Non-numeric octet
    if octet and not octet.isdigit():
      errors.append(f"{hostname}: HostOctet '{octet}' is not numeric")
      continue

    # CLD black swan -- skip convention checks
    if site == "CLD":
      continue

    # Duplicate IP within site
    if full_ip:
      seen_ips.setdefault(site, set())
      if full_ip in seen_ips[site]:
        errors.append(f"{hostname}: duplicate IP {full_ip} in site {site}")
      else:
        seen_ips[site].add(full_ip)

    # DHCP pool warning
    if octet and octet.isdigit():
      oct_int = int(octet)
      if 100 <= oct_int <= 249:
        warnings.append(
          f"{hostname}: HostOctet {octet} is inside DHCP pool (.100-.249) -- "
          "may be a DHCP client or wrong IP"
        )

    # Convention conflict
    if octet and octet in suffix_role:
      expected = suffix_role[octet]
      alt = suffix_role_alt.get(octet)
      if role != expected and role != alt:
        warnings.append(
          f"{hostname}: HostOctet {octet} conventionally assigned to {expected} "
          f"but role is {role}"
        )

  return errors, warnings


def print_device_validation(devices):
  """Run and print device validation results."""
  header("devices.csv Validation")
  errors, warnings = validate_devices(devices)

  if not errors and not warnings:
    status("Running", f"devices.csv: {len(devices)} rows -- no issues found")
    return

  for e in errors:
    status("Failure", e)
  for w in warnings:
    status("Warning", w)

  if errors:
    print(f"\n{C.RED}[!] {len(errors)} error(s) found in devices.csv{C.RESET}")
  if warnings:
    print(f"\n{C.YELLOW}[!] {len(warnings)} warning(s) found in devices.csv{C.RESET}")


""" Roles expected to have exactly one NIC """
INFRA_ROLES = {"DCS","SQL","APP","FSR"}

""" Roles allowed to have many NICs """
MULTI_ROLES = {"ANS","MON","LAB"}


def header(title):
  """Print a coloured section header."""
  print(f"{C.CYAN}==== {title} ===={C.RESET}")


def status(state, message):
  """Print a coloured status line."""
  colours = {
    "Running": C.GREEN,
    "Failure": C.RED,
    "Warning": C.YELLOW
  }
  print(f"{colours.get(state, C.RESET)}[{state}] {message}{C.RESET}")


def connect(args):
  """
  Connect to the Proxmox API.

  Handles authentication and connection failures cleanly so the script
  does not crash with a Python traceback.
  """
  try:
    return ProxmoxAPI(
      args.host,
      user=args.user,
      password=args.password,
      verify_ssl=False
    )
  except AuthenticationError:
    status("Failure", "Authentication to Proxmox failed")
    sys.exit(2)
  except Exception as e:
    status("Failure", f"Unable to connect: {e}")
    sys.exit(2)


def get_pools(proxmox):
  """
  Build a dictionary mapping VMID → pool name.

  Pools correspond to site codes (GLA, EDI, etc).
  """
  pools = {}

  for pool in proxmox.pools.get():
    name = pool["poolid"]
    members = proxmox.pools(name).get()["members"]

    for member in members:
      if member["type"] == "qemu":
        pools[member["vmid"]] = name

  return pools


def parse_nics(config):
  """
  Extract NIC definitions from a VM config.

  Returns a list of dictionaries describing each NIC.
  """
  nics = []

  for key, val in config.items():
    if not key.startswith("net"):
      continue

    vlan = None
    bridge = None

    if "bridge=" in val:
      bridge = val.split("bridge=")[1].split(",")[0]

    if "tag=" in val:
      vlan = int(val.split("tag=")[1].split(",")[0])

    nics.append({
      "nic": key,
      "bridge": bridge,
      "vlan": vlan
    })

  return nics


def get_vms(proxmox):
  """
  Retrieve VM information from all nodes in the cluster.

  Collects:
  - VM name
  - NIC configuration
  - IP configuration
  - pool membership
  - backup flag
  """
  vms = {}
  pools = get_pools(proxmox)

  for node in proxmox.nodes.get():
    node_name = node["node"]

    for vm in proxmox.nodes(node_name).qemu.get():
      vmid = vm["vmid"]
      config = proxmox.nodes(node_name).qemu(vmid).config.get()

      name = vm["name"]
      ips = []

      # Extract IP if cloud-init IP config exists
      if "ipconfig0" in config:
        try:
          ip = config["ipconfig0"].split(",")[0].split("=")[1]
          ips.append(ip.split("/")[0])
        except Exception:
          pass

      nics = parse_nics(config)
      backup = config.get("backup", "0") == "1"

      vms[name] = {
        "vmid": vmid,
        "node": node_name,
        "ips": ips,
        "nics": nics,
        "pool": pools.get(vmid),
        "backup": backup
      }

  return vms


def validate_hostname(inventory):
  """
  Validate hostname structure from inventory.

  Expected format:
  EXA + ROLE + SITE + ###
  """
  header("Inventory Hostname Structure")

  pattern = re.compile(r"^EXA[A-Z]{3}[A-Z]{3}[0-9]{3}$")

  for host in inventory:
    if not pattern.match(host):
      status("Failure", f"{host} invalid hostname format")
      continue

    site = host[6:9]

    if site not in SITE_SUBNETS:
      status("Failure", f"{host} unknown site {site}")
    else:
      status("Running", f"{host} hostname valid")


def check_nic_policy(vms):
  """
  Validate NIC configuration according to VM role.
  """
  header("VM NIC Policy Validation")

  for name, data in vms.items():
    if len(name) < 9:
      continue

    role = name[3:6]
    site = name[6:9]
    nics = data["nics"]

    tagged = [n for n in nics if n["vlan"]]
    untagged = [n for n in nics if not n["vlan"]]

    if role == "FWL":

      if not untagged:
        status("Failure", f"{name} firewall missing untagged WAN NIC")
        continue

      if not tagged:
        status("Failure", f"{name} firewall missing tagged LAN NIC")
        continue

      status("Running", f"{name} firewall NIC policy valid")

    elif role in INFRA_ROLES:

      if len(nics) != 1:
        status("Failure", f"{name} has {len(nics)} NICs but role expects one")
        continue

      expected_vlan = int(SITE_SUBNETS[site].split(".")[2])
      vlan = nics[0]["vlan"]

      if vlan != expected_vlan:
        status("Failure", f"{name} VLAN {vlan} expected {expected_vlan}")
      else:
        status("Running", f"{name} NIC policy valid")

    elif role in MULTI_ROLES:

      valid_vlans = [int(s.split(".")[2]) for s in SITE_SUBNETS.values()]

      for nic in tagged:
        if nic["vlan"] not in valid_vlans:
          status("Failure", f"{name} NIC {nic['nic']} invalid VLAN {nic['vlan']}")
          break
      else:
        status("Running", f"{name} {len(nics)} NICs valid")

    else:
      status("Running", f"{name} NICs unchecked role {role}")


def check_pool(vms):
  """
  Validate that each VM is placed in the correct Proxmox pool.
  """
  header("Proxmox Pool Placement")

  for name, data in vms.items():
    site = name[6:9]

    if data["pool"] != site:
      status("Failure", f"{name} pool {data['pool']} expected {site}")
    else:
      status("Running", f"{name} pool correct")


def check_backup(vms):
  """
  Check whether each VM has Proxmox backup enabled.
  """
  header("Proxmox Backup Coverage")

  for name, data in vms.items():
    if data["backup"]:
      status("Running", f"{name} backup configured")
    else:
      status("Warning", f"{name} has no backup job")


# =============================================================================
# FORMATTING HELPERS
# =============================================================================

# Total line width for section headers (including the leading "# ")
_HDR_WIDTH = 78

def _section_header(label):
  """
  Return a centred section header of exactly _HDR_WIDTH visible characters.

    # ──────────────────── Domain Controllers ────────────────────
  """
  inner   = _HDR_WIDTH - 2          # visible chars after "# "
  dashes  = inner - len(label) - 2  # 2 spaces around label
  left    = dashes // 2
  right   = dashes - left
  # Use ASCII hyphens for reliable width -- rendered as ─ is cosmetic only
  return f"# {'─' * left} {label} {'─' * right}"


# =============================================================================
# KNOWN ANCILLARY / SPECIAL-CASE HOSTS
# Hardcoded here because they are stable infrastructure not derivable from
# the standard suffix map. All CLD-based provisioning / management nodes.
# =============================================================================

KNOWN_ANCILLARY = [
  # (site, ip, hostname, in_ansible, comment)
  # CLD-specific hosts that are not derivable from SUFFIX_MAP
  ("CLD", "192.168.139.8",  "EXADNSCLD001", True,
   "DNS/BIND9 server -- jukebox.internal authoritative"),
  ("CLD", "192.168.139.20", "EXASVRCLD002", True,
   "Windows Admin Centre"),
  ("CLD", "192.168.139.50", "EXAPRVCLD001", True,
   "Provisioning server -- PXE, HTTP, iPXE, sites.csv, scripts"),
  ("CLD", "192.168.139.69", "EXAANSCLD001", True,
   "Ansible management node"),
]


# =============================================================================
# STATIC HOST MAP
# =============================================================================
# Defines the deterministic IP suffix → (role_prefix, seq, include_in_ansible)
# for every known static address in each /24 site subnet.
#
# Format: suffix: (hostname_prefix, sequence_number, in_ansible)
#   hostname_prefix  e.g. "EXARTR", "EXAFWL"
#   sequence_number  e.g. 1, 2, 3 -- becomes the NNN in the hostname
#   in_ansible       True = include in Ansible inventory
#
# Ordering note: EXARTR (.1) is unmanaged hardware -- included in both
# hosts and Ansible for reference but flagged with ansible_connection=local
# so Ansible does not try to SSH to it.

SUFFIX_MAP = {
  1:   ("EXARTR", 1, True),   # hardware router/gateway (Cisco etc) -- unmanaged
  2:   ("EXARAC", 1, True),   # BMC pool slot 1 (DRAC/iLO/RAC emulator)
  3:   ("EXARAC", 2, True),   # BMC pool slot 2
  4:   ("EXARAC", 3, True),   # BMC pool slot 3
  5:   ("EXAPVE", 1, True),   # Proxmox VE node 1
  6:   ("EXAPVE", 2, True),   # Proxmox VE node 2
  7:   ("EXAPVE", 3, True),   # Proxmox VE node 3
  10:  ("EXADCS", 1, True),   # Domain Controller primary
  11:  ("EXADCS", 2, True),   # Domain Controller secondary
  12:  ("EXARRY", 1, True),   # Rudder Relay (or Rudder Server for CLD -- handled below)
  48:  ("EXASBC", 1, True),   # VOIP SBC (or PBX for CLD -- handled below)
  250: ("EXASWI", 1, True),   # Switch 1
  251: ("EXASWI", 2, True),   # Switch 2
  252: ("EXASWI", 3, True),   # Switch 3
  253: ("EXAFWL", 1, True),   # Firewall (our Debian FWL node)
}

# Roles that are unmanaged hardware -- present in Ansible inventory but
# with ansible_connection=local so Ansible does not attempt SSH
UNMANAGED_ROLES = {"EXARTR", "EXASWI", "EXARAC"}


def _site_hosts(site_code, site_data):
  """
  Generate all static hostname→IP pairs for a given site.

  Returns a list of (ip, hostname, role_prefix, in_ansible) tuples.
  Skips BRD (legacy alias -- BER covers it).
  Handles CLD special case: .48 is EXAPBXCLD001, not EXASBC.
  """
  if "legacy alias" in site_data.get("city", "").lower():
    return []

  subnet_base = site_data["subnet"]
  if not subnet_base or subnet_base == "N/A":
    return []

  # Extract 192.168.X from the /24 string
  parts = subnet_base.split(".")
  base  = f"{parts[0]}.{parts[1]}.{parts[2]}"

  hosts = []
  for suffix, (prefix, seq, in_ansible) in SUFFIX_MAP.items():
    ip = f"{base}.{suffix}"
    # CLD special cases: .12 is Rudder Server (not Relay); .48 is PBX (not SBC)
    if suffix == 12 and site_code == "CLD":
      hostname = "EXARUDCLD001"
    elif suffix == 48 and site_code == "CLD":
      hostname = "EXAPBXCLD001"
    else:
      hostname = f"{prefix}{site_code}{seq:03d}"
    hosts.append((ip, hostname, prefix, in_ansible))

  return hosts


def generate_hosts(output_path=None, sites_csv=None, _extra_hosts=None):
  if _extra_hosts is None: _extra_hosts = []
  """
  Generate an /etc/hosts file from sites.csv.

  Format:
    - Header comment block
    - One section per role prefix (EXAFWL, EXADCS, EXAPVE etc.)
    - Within each role section, sites sorted by subnet octet descending
      (higher octet number = higher up in the file)
    - Loopback entries preserved at top

  Args:
    output_path: write to file if given, else print to stdout
    sites_csv:   override path to sites.csv
  """
  sites = _load_sites(sites_csv)

  # Build full host list grouped by role prefix
  # role → list of (octet, ip, hostname)
  from collections import defaultdict
  by_role = defaultdict(list)

  for code, data in sites.items():
    if "legacy alias" in data.get("city", "").lower():
      continue
    octet = data.get("octet")
    if not octet:
      continue
    for ip, hostname, prefix, _ in _site_hosts(code, data):
      by_role[prefix].append((octet, ip, hostname))

  # Sort each role group by octet descending
  for prefix in by_role:
    by_role[prefix].sort(key=lambda x: x[0], reverse=False)

  # Role display order
  role_order = [
    "EXAFWL", "EXARTR", "EXADCS", "EXAPVE",
    "EXARAC", "EXASWI", "EXASBC", "EXAPBX",
  ]
  # Any roles not in the explicit order go at the end alphabetically
  extra = sorted(r for r in by_role if r not in role_order)
  ordered_roles = [r for r in role_order if r in by_role] + extra

  lines = []
  lines.append("# ============================================================")
  lines.append("# /etc/hosts -- Example Music Limited")
  lines.append("# Generated by site-inventory-audit.py --generate-hosts")
  lines.append("# Source: sites.csv (single source of truth)")
  lines.append("#")
  lines.append("# Sorted by role, within each role by subnet octet descending")
  lines.append("# (higher octet = higher in file, e.g. .224 ABD before .41 CLY)")
  lines.append("#")
  lines.append("# This file is a SUPPLEMENT to DNS, not a replacement.")
  lines.append("# Regenerate with: site-inventory-audit.py --generate-hosts")
  lines.append("# ============================================================")
  lines.append("")
  lines.append("127.0.0.1   localhost")
  lines.append("127.0.1.1   $(hostname -f) $(hostname -s)")
  lines.append("::1         localhost ip6-localhost ip6-loopback")
  lines.append("ff02::1     ip6-allnodes")
  lines.append("ff02::2     ip6-allrouters")
  lines.append("")

  for prefix in ordered_roles:
    entries = by_role[prefix]
    if not entries:
      continue
    # Role label -- derive a human description
    role_labels = {
      "EXAFWL": "Firewalls (Debian FWL nodes)",
      "EXARTR": "Routers / hardware gateways (unmanaged)",
      "EXADCS": "Domain Controllers",
      "EXAPVE": "Proxmox VE nodes",
      "EXARAC": "BMC / RAC (iDRAC, iLO, RAC emulators)",
      "EXASWI": "Switches (unmanaged)",
      "EXASBC": "VOIP SBC nodes",
      "EXAPBX": "PBX (CLD)",
    }
    label = role_labels.get(prefix, prefix)
    lines.append(_section_header(label))
    for octet, ip, hostname in entries:
      fqdn = f"{hostname.lower()}.jukebox.internal"
      lines.append(f"{ip:<18} {fqdn:<45} {hostname.lower()}")
    lines.append("")

  # ── Known ancillary hosts (hardcoded stable infrastructure) ─────────────
  lines.append(_section_header("Ancillary / Management Infrastructure"))
  for site, ip, hostname, _, comment in KNOWN_ANCILLARY:
    fqdn = f"{hostname.lower()}.jukebox.internal"
    lines.append(f"{ip:<18} {fqdn:<45} {hostname.lower()}  # {comment}")
  lines.append("")

  # ── User-supplied ancillary hosts ────────────────────────────────────────
  if _extra_hosts:
    lines.append(_section_header("Site-Specific Ancillary Hosts"))
    for ip, hostname, comment, active in _extra_hosts:
      fqdn = f"{hostname.lower()}.jukebox.internal"
      prefix = "" if active else "# "
      suffix = f"  # {comment}" if comment else ""
      if not active:
        suffix = f"  # UNKNOWN IP -- verify and uncomment{(' -- ' + comment) if comment else ''}"
      lines.append(f"{prefix}{ip:<18} {fqdn:<45} {hostname.lower()}{suffix}")
    lines.append("")

  # ── Miscellaneous / IoT / Specialist devices ─────────────────────────────
  lines.append(_section_header(
    "Miscellaneous Devices (IoT, OT, Specialist -- document manually)"))
  lines.append("# Add site-specific specialist devices below.")
  lines.append("# These will never appear in Ansible but should be documented for network")
  lines.append("# management, monitoring, and troubleshooting.")
  lines.append("# Examples: petrol pumps, vending machines, jukeboxes, payphones, cameras,")
  lines.append("#           badge readers, PLCs, etc.")
  lines.append("#")
  lines.append("# Format:")
  lines.append("#      <ip>                      <fqdn>                  <short>              <description>")
  lines.append("# 192.168.41.100   exacofcly001.jukebox.internal       exacofcly001  # Internet connected coffee machine in CLY")
  lines.append("")

  output = "\n".join(lines)

  if output_path:
    with open(output_path, "w") as f:
      f.write(output)
    print(f"[+] Hosts file written: {output_path}")
    print(f"    {sum(1 for l in lines if l and not l.startswith('#'))} host entries")
  else:
    print(output)


def generate_inventory(output_path=None, sites_csv=None, _extra_hosts=None):
  if _extra_hosts is None: _extra_hosts = []
  """
  Generate an Ansible inventory (INI format) from sites.csv.

  Groups produced:
    [exafwl]         -- all FWL nodes
    [exadcs]         -- all DC nodes
    [exapve]         -- all PVE nodes
    [exarac]         -- all BMC/RAC nodes
    [exaswi]         -- all switches
    [exasbc]         -- all SBC/PBX nodes
    [exartr]         -- all hardware routers (ansible_connection=local)
    [<ansible_region>]  -- e.g. [uk_site], [dk_site] etc.
    [all:vars]       -- common variables

  Within each group, hosts are sorted by subnet octet descending.
  """
  sites = _load_sites(sites_csv)

  from collections import defaultdict
  # role_lower → list of (octet, hostname, ip, ansible_vars)
  by_role    = defaultdict(list)
  by_region  = defaultdict(list)

  for code, data in sites.items():
    if "legacy alias" in data.get("city", "").lower():
      continue
    octet = data.get("octet")
    if not octet:
      continue
    region = data.get("ansible_region", "ungrouped")

    for ip, hostname, prefix, in_ansible in _site_hosts(code, data):
      if not in_ansible:
        continue
      role_key = prefix.lower()
      host_line = f"{hostname.lower()}.jukebox.internal"

      vars_parts = [f"ansible_host={ip}"]
      # Unmanaged hardware -- do not SSH, just record in inventory
      if prefix in UNMANAGED_ROLES:
        vars_parts.append("ansible_connection=local")
        vars_parts.append("# unmanaged hardware")
      # Add site metadata as host vars
      vars_parts.append(f"site={code}")
      vars_parts.append(f"site_subnet={data['subnet']}")

      entry = (octet, host_line, " ".join(vars_parts))
      by_role[role_key].append(entry)
      by_region[region].append((octet, host_line, f"ansible_host={ip}"))

  # Sort all groups by octet descending
  for g in by_role:
    by_role[g].sort(key=lambda x: x[0], reverse=False)
  for g in by_region:
    by_region[g].sort(key=lambda x: x[0], reverse=False)

  role_order = ["exafwl","exartr","exadcs","exapve",
                "exarac","exaswi","exasbc"]
  region_order = sorted(by_region.keys())

  lines = []
  lines.append("# ============================================================")
  lines.append("# Ansible Inventory -- Example Music Limited")
  lines.append("# Generated by site-inventory-audit.py --generate-inventory")
  lines.append("# Source: sites.csv (single source of truth)")
  lines.append("#")
  lines.append("# Groups: by role (exafwl, exadcs etc)")
  lines.append("#         by ansible_region (uk_site, dk_site etc)")
  lines.append("# Sorted by subnet octet ascending within each group")
  lines.append("# ============================================================")
  lines.append("")

  # Role groups
  lines.append(_section_header("Role Groups"))
  extra_roles = sorted(r for r in by_role if r not in role_order)
  for role in role_order + extra_roles:
    entries = by_role.get(role, [])
    if not entries:
      continue
    lines.append(f"[{role}]")
    for _, host_line, vars_str in entries:
      lines.append(f"{host_line}  {vars_str}")
    lines.append("")

  # Region groups
  lines.append(_section_header("Region Groups"))
  for region in region_order:
    entries = by_region[region]
    if not entries:
      continue
    lines.append(f"[{region}]")
    for _, host_line, vars_str in entries:
      lines.append(f"{host_line}  {vars_str}")
    lines.append("")

  # ── Known ancillary hosts ────────────────────────────────────────────────
  lines.append(_section_header("Ancillary / Management Infrastructure"))
  lines.append("[ancillary]")
  for site, ip, hostname, in_ansible, comment in KNOWN_ANCILLARY:
    if in_ansible:
      host_line = f"{hostname.lower()}.jukebox.internal"
      lines.append(f"{host_line}  ansible_host={ip} site={site}  # {comment}")
  if _extra_hosts:
    for ip, hostname, comment, active in _extra_hosts:
      host_line = f"{hostname.lower()}.jukebox.internal"
      prefix = "" if active else "# "
      note   = f"  # {comment}" if comment else ""
      if not active:
        note = f"  # UNKNOWN IP -- verify and uncomment{(' -- ' + comment) if comment else ''}"
      lines.append(f"{prefix}{host_line}  ansible_host={ip}{note}")
  lines.append("")

  # all:vars
  lines.append(_section_header("Common Variables"))
  lines.append("[all:vars]")
  lines.append("ansible_user=ansible")
  lines.append("ansible_python_interpreter=/usr/bin/python3")
  lines.append("domain=jukebox.internal")
  lines.append("")

  output = "\n".join(lines)

  if output_path:
    with open(output_path, "w") as f:
      f.write(output)
    total = sum(len(v) for v in by_role.values())
    print(f"[+] Ansible inventory written: {output_path}")
    print(f"    {total} host entries across {len(by_role)} role groups")
    print(f"    {len(by_region)} region groups: {', '.join(region_order)}")
  else:
    print(output)


def prompt_ancillary():
  """
  Interactively collect any additional site-specific hosts not in the
  standard suffix map.

  Called during generate_hosts / generate_inventory runs.
  Press Enter at the hostname prompt to finish.

  Returns a list of (ip, hostname, comment, active) tuples where:
    active=False means the IP was unknown -- line is commented out.
  """
  print()
  print(f"\033[96m[?]\033[0m  Additional / ancillary hosts (press Enter to skip):")
  print(     "     Enter any hosts not in the standard suffix map.")
  print(     "     If IP is unknown, leave blank -- the line will be commented out.")
  print()

  extras = []
  while True:
    hostname = input("     Hostname (e.g. EXASVR FAL002) or Enter to finish: ").strip().upper()
    if not hostname:
      break
    # Normalise spaces that might have been typed
    hostname = hostname.replace(" ", "")
    comment  = input(f"     Description for {hostname}: ").strip()
    ip_raw   = input(f"     IP address for {hostname} (Enter if unknown): ").strip()
    if ip_raw:
      active = True
      ip     = ip_raw
    else:
      # Derive subnet from hostname if it follows EXA[ROLE][SITE][NNN] convention
      ip = "?.?.?.?"
      if len(hostname) >= 9:
        site_code = hostname[6:9]
        if site_code in SITES and SITES[site_code].get("octet"):
          octet = SITES[site_code]["octet"]
          ip = f"192.168.{octet}.?"
      active = False
    extras.append((ip, hostname, comment, active))
    print()

  return extras


def main():
  """Program entry point."""

  parser = argparse.ArgumentParser(
    description="Proxmox Environment Audit + Host/Inventory Generator",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  # Run full audit against live Proxmox cluster
  %(prog)s --host pve.jukebox.internal --user root@pam --inventory hosts.txt

  # Generate /etc/hosts from sites.csv (no Proxmox connection needed)
  %(prog)s --generate-hosts
  %(prog)s --generate-hosts --hosts-out /etc/hosts.d/example-music

  # Generate Ansible inventory from sites.csv
  %(prog)s --generate-inventory
  %(prog)s --generate-inventory --inventory-out /etc/ansible/hosts

  # Generate both at once
  %(prog)s --generate-hosts --generate-inventory

  # Audit + cross-check against generated hosts
  %(prog)s --host pve.jukebox.internal --user root@pam \
           --inventory hosts.txt --generate-hosts
""")

  # Proxmox connection (required for audit, not for generation)
  parser.add_argument("--host",      help="Proxmox API host")
  parser.add_argument("--user",      help="Proxmox API user (e.g. root@pam)")
  parser.add_argument("--inventory", help="Ansible inventory file to audit")

  # Generation flags
  parser.add_argument("--generate-hosts",
    action="store_true",
    help="Generate /etc/hosts from sites.csv (or devices.csv if present)")
  parser.add_argument("--hosts-out",
    metavar="FILE", default=None,
    help="Write hosts to FILE (default: hosts.txt when --generate-hosts used)")
  parser.add_argument("--generate-inventory",
    action="store_true",
    help="Generate Ansible inventory (INI) from sites.csv (or devices.csv if present)")
  parser.add_argument("--inventory-out",
    metavar="FILE", default=None,
    help="Write inventory to FILE (default: inventory.txt when --generate-inventory used)")
  parser.add_argument("--sites-csv",
    metavar="FILE",
    help="Override path to sites.csv")
  parser.add_argument("--devices-csv",
    metavar="FILE",
    help="Override path to devices.csv (single source of truth for all devices). "
         "If not specified, the script searches the same locations as sites.csv.")
  parser.add_argument("--validate-devices",
    action="store_true",
    help="Validate devices.csv against sites.csv -- check site codes, hostname "
         "patterns, duplicate IPs, DHCP pool conflicts, convention mismatches. "
         "CLD rows bypass convention checks (provisioning network black swan).")

  args = parser.parse_args()

  # Load devices.csv if available (used by generation modes and --validate-devices)
  devices = _load_devices(args.devices_csv if hasattr(args, 'devices_csv') else None)
  if devices:
    print(f"[*] Loaded {len(devices)} device rows from devices.csv")
  else:
    print("[*] devices.csv not found -- generation will use SUFFIX_MAP derivation")

  # --validate-devices standalone mode
  if hasattr(args, 'validate_devices') and args.validate_devices:
    if not devices:
      print(f"{C.RED}[ERROR] --validate-devices requires devices.csv{C.RESET}")
      sys.exit(1)
    print_device_validation(devices)
    if not (args.generate_hosts or args.generate_inventory or args.host):
      return

  # Handle generation modes (no Proxmox connection needed)
  extra_hosts = []
  if args.generate_hosts or args.generate_inventory:
    extra_hosts = prompt_ancillary()

  if args.generate_hosts:
    hosts_out = args.hosts_out if args.hosts_out else "hosts.txt"
    generate_hosts(output_path=hosts_out, sites_csv=args.sites_csv,
                   _extra_hosts=extra_hosts)

  if args.generate_inventory:
    inv_out = args.inventory_out if args.inventory_out else "inventory.txt"
    generate_inventory(output_path=inv_out, sites_csv=args.sites_csv,
                       _extra_hosts=extra_hosts)

  # If either generation flag was given but no audit requested, we are done
  if (args.generate_hosts or args.generate_inventory) and not args.host:
    return

  # Audit mode requires --host, --user, --inventory
  if not args.host:
    parser.error("--host is required for audit mode")
  if not args.user:
    parser.error("--user is required for audit mode")
  if not args.inventory:
    parser.error("--inventory is required for audit mode")

  args.password = getpass.getpass(f"Password for {args.user}: ")

  proxmox = connect(args)
  vms     = get_vms(proxmox)

  with open(args.inventory) as f:
    inventory = [
      line.strip()
      for line in f
      if line.strip() and not line.startswith("[")
    ]

  validate_hostname(inventory)
  check_nic_policy(vms)
  check_pool(vms)
  check_backup(vms)


if __name__ == "__main__":
  main()

