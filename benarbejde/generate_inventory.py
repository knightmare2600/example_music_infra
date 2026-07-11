#!/usr/bin/env python3

# ==================================================================================================
# Example Music Inventory Generator
#
# Authoritative sources: /etc/example-music/sites.csv, /etc/example-music/devices.csv
#
# Requires an apt -y install python3-ipy to be run on your ansible node.
#
# Address allocation policy:
#
#   .1          RTR   Upstream router
#   .2-.4       BMC   iDRAC / iLO / Redfish
#   .5-.7       PVE   Proxmox nodes
#   .10         DCS1  Primary Domain Controller
#   .11         DCS2  Secondary Domain Controller
#   .15         PRV   Provisioning Server
#   .48         SBC   VoIP Session Border Controller
#   .100-.249   DHCP  DHCP Pool
#   .250-.252   SWI   Switches
#   .253        FWL1  Firewall
#   .254        FWL2  Firewall
#
# Everything else for a site — the long tail of real, non-standard devices (extra workstations,
# a Rudder server, a PBX, a NAS, right down to the vending machine — see devices.csv) — comes from
# devices.csv, joined in per-site on the Site column (sites.csv is the "left" table: one row per
# site drives which .ini gets written; devices.csv is the "right" table: zero or more rows per
# site, matched on Site, added into that site's .ini).
#
# Host naming:
#
#   EXA<ROLE><SITE><NNN>
# ==================================================================================================
# Changelog:
#  2026-07-05  Fixed offset_ip() — IPy's IP.__add__ is reserved for merging two adjacent IP()/net
#              objects into a parent CIDR block (see https://pypi.org/project/IPy/), not address
#              offsetting. base + offset with offset as a plain int made IPy's __add__ try to read
#              offset._ipversion, causing 'int' object has no attribute '_ipversion'. Fixed by
#              converting to the integer form with .int(), adding there, then rebuilding an IP from
#              the result.
#  2026-07-05  Rewrote build_ini() to use the standard header block & proper multi-group INI syntax
#              (firewalls/windows_server/windows_desktop/windows_laptop/windows:children), matching
#              windows_bootstrap/inventory/cld.ini's structure. Hostnames (FWL/DCS1/DCS2/WKS1/LAP1)
#              now come from build_hostname() instead of duplicated as inline EXA{ROLE}{SITE}001
#              string literals — known source of truth for EXA<ROLE><SITE><NNN> naming convention.
#              (2026-07-09 note: the "windows_bootstrap/inventory/cld.ini" this comment refers to
#              no longer exists under that path/structure -- see the 2026-07-09 entry below.)
#  2026-07-05  Wire in unused hostname_map (BMC/PVE) built in generate() into build_ini(). PVE nodes
#              get a real, uncommented [pvenodes] group (matching the existing group_vars/pvenodes/
#              directory) since they're genuinely Ansible-managed. BMC hosts (iDRAC/iLO/Redfish) are
#              not Ansible-managed, so added as commented reference lines only, no group header.
#  2026-07-05  register_ip() now skips "N/A" entirely instead of treating it as a real address. Two
#              unrelated sites both legitimately having "N/A" for Gateway/DC/FW (e.g. VRK, BRD) were
#              colliding with each other on the literal string "N/A". N/A is an established sentinel
#              elsewhere in this estate (ad_schema.yml rejectattr('Subnet', 'equalto', 'N/A')); this
#              brings register_ip() in line with that convention.
#  2026-07-07  Fixed two bugs that made this script unrunnable: a stray "." after
#              ROLE_OFFSETS["FWL"]'s value (hard SyntaxError, the script could not even be
#              imported), and OFFSETS_SINGLE["DCS"] in generate() — OFFSETS_SINGLE never had a
#              "DCS" key (DCS lives in ROLE_OFFSETS, since it's a two-instance role like BMC/FWL/PVE,
#              not a single-instance one like RTR/PRV/SBC/WKS/LAP) — that would have raised
#              KeyError: 'DCS' on the very first site as soon as the syntax error was fixed.
#  2026-07-07  Merged inventory_devices.py's functionality in — this script now reads devices.csv
#              directly (no separate devices_old.csv/devices_new.csv preprocessing pass) and joins
#              each site's device rows into that site's generated .ini. Standard-offset devices
#              (already covered by the address policy above — e.g. a WKS row sitting exactly at
#              .101) and RAC/PVE rows (per longstanding operator instruction: RAC is being
#              decommissioned in favour of BMC, and real PVE nodes are handled by the standard
#              template + group_vars/pvenodes, not the devices.csv exception path) are still
#              excluded, same as inventory_devices.py did. inventory_devices.py is removed —
#              its logic lives here now, applied at generation time instead of as a one-off
#              preprocessing script, so there's one source of truth instead of two files that can
#              drift (devices.csv used to need a separate devices_new.csv regenerated by hand).
#  2026-07-07  Extracted OFFSETS_SINGLE/ROLE_OFFSETS into address_policy.json (sibling to
#              sites.csv) instead of hardcoding them here — bind9-dns.yml's Play 2 needs the same
#              standard-slot address policy (to synthesise DNS records for the standard devices,
#              now that devices.csv is exceptions-only rather than a complete device list) and
#              would otherwise be a second hand-maintained copy that could drift from this one.
#  2026-07-07  Added --emit-devices-json (compute_standard_devices_for_site/emit_devices_for_dns)
#              — bind9-dns.yml consumes this directly instead of re-deriving the standard-slot +
#              devices.csv-exception merge in Jinja, so DNS and the .ini generator can never
#              disagree about which devices are real or what they're called. Only synthesizes
#              slots build_ini() shows uncommented (RTR/PRV/SBC, both FWL instances, first
#              DCS/PVE instance only) — synthesizing the "example" WKS/LAP slots or BMC/DCS2/PVE2/
#              PVE3 caused real hostname collisions with devices.csv's own numbering in testing
#              (e.g. FAL's real WKS Number=1 at octet .100 colliding with the WKS "example" slot's
#              assumed index 1). BRD (legacy alias for BER, identical subnet) is folded into BER
#              entirely, hostnames rebuilt under BER. VRK (provisioning network, manually-assigned
#              roles) never gets standard-slot synthesis, only its real devices.csv rows.
#  2026-07-08  build_ini()'s header now includes a "Site Information" block (legal entity, city,
#              country, timezone, landline/mobile, subnet, gateway, firewall, primary DC, Ansible
#              region) — for humans reading the generated .ini, not for Ansible. This data was
#              already in sites.csv, just never surfaced in the file itself.
#  2026-07-08  Added WAP to ROLE_OFFSETS (.82-.94, 13 slots) — a gap in the addressing convention
#              not used by any standard slot or any site's real devices.csv rows, for moving WAPs
#              off DHCP to static IPs. Unlike BMC/DCS/PVE/FWL, WAP count varies wildly per site
#              (FAL has 6, most sites have 1-2) — deliberately NOT added to DNS_SINGLE_ROLES/
#              DNS_MULTI_ALL_INSTANCES/DNS_MULTI_FIRST_INSTANCE_ONLY, so no DNS records are
#              auto-synthesized for it, same treatment as BMC. Devices.csv rows at .82-.94 ARE
#              excluded from the .ini/DNS output as "already standard" (same STANDARD_OFFSETS
#              mechanism as every other role_offsets entry) — this was an explicit, informed
#              choice: real per-device Notes are lost for WAPs at this range in favour of treating
#              the slot as standardised, same tradeoff already accepted for DCS/PVE/FWL/RTR.
#  2026-07-08  Wired up devices.csv's ConnectionType column (was always blank, never read by
#              anything since the schema migration). address_policy.json now has a
#              connection_types map (Type -> ssh/winrm/telnet/snmp/http/none) — populated every
#              existing devices.csv row from it. is_managed()/needs_review() now treat
#              ConnectionType as a signal between Managed (explicit override) and the OS-regex
#              guess (fallback): snmp/http/none are never managed regardless of OS, since Ansible
#              can't task-execute over those. render_device_line() now emits the right
#              ansible_connection for ssh/winrm/telnet, and documents snmp/http as a query
#              protocol in the comment instead (Ansible itself never connects that way).
#  2026-07-08  Added --emit-group-vars: writes ansible/group_vars/all/site_services.yml, deriving
#              well-known service addresses (both provisioning servers, DNS, Ansible control node,
#              PBX x2, Rudder, WAC) from sites.csv/devices.csv instead of the hand-maintained
#              literals scattered across group_vars/all/vars.yml and windows_bootstrap playbooks.
#              Also emits exa_asset_base/exa_wallpaper_url directly (the concrete vars those
#              playbooks already read) so migrating off the hardcoded copies is a pure deletion,
#              not a rewrite. group_vars/all/vars.yml still defines these too for now (loads after
#              site_services.yml alphabetically, so it still wins) -- removing the duplicate is a
#              separate, deliberate follow-up, not done as part of adding this generator.
#  2026-07-08  Removed exa_asset_base/exa_wallpaper_url emission -- windows_bootstrap's wallpaper
#              and binaries now win_copy from a local files/ directory instead of HTTP-fetching
#              from the provisioning server (that pattern only ever existed for the pre-Ansible
#              bootstrap scripts). The site_services dict itself (provisioning server hostnames/
#              IPs/URLs, still useful documentation) is unchanged.
#  2026-07-09  Consolidated the two parallel inventory locations this generator and windows_dc
#              onboarding had drifted into. ansible/inventory/ (this script's own --out default)
#              and ansible/configs/inventory/ (windows_dc's hand-curated cld.ini/fal.ini/liv.ini)
#              had different, incompatible group structures for the exact same sites -- this
#              script put DCS1 straight into [windows_server] with no windows_dc/windows_nodes
#              groups at all, while configs/inventory/*.ini used a distinct
#              windows_dc -> windows_server -> windows -> windows_nodes chain (needed for
#              group_vars/windows_dc/ and group_vars/windows_nodes/connection.yml to apply).
#              Running both meant whichever one a given operator invocation happened to load
#              silently determined whether DC-specific group_vars applied at all. build_ini() now
#              emits the windows_dc/windows_nodes structure directly (DEVICE_GROUP_MAP's DCS entry
#              moved from windows_server to windows_dc to match), and --out's default moved from
#              ~/ansible/inventory to ~/ansible/configs/inventory -- one location, one structure,
#              matching what windows_dc onboarding has always actually needed. ansible/inventory/
#              retired; see configs/inventory/README or the commit that made this change for the
#              migration.
#  2026-07-09  Moved ansible/group_vars/ and ansible/host_vars/ to ansible/configs/inventory/
#              (group_vars_out default and doc references here updated to match). Root cause:
#              Ansible's group_vars/host_vars auto-loading is anchored to the actual loaded
#              inventory PATH (ansible.builtin.host_group_vars vars plugin, "only applies to
#              inventory sources that are existing paths") -- confirmed empirically that it must
#              be inside that path, not just a sibling of it. ansible/group_vars/ was never inside
#              ansible/configs/inventory/, so it silently never applied to any numbered playbook,
#              regardless of correct inventory group membership -- this is the real root cause
#              behind the registry_common/domain_ou_role crashes fixed earlier this session.
#              A symlink-based fix was tried and reverted -- this repo is cloned on Windows, Linux,
#              and macOS, and symlinks don't survive that reliably. A real directory move is the
#              only fix that's identical on every platform.
# ==================================================================================================

import csv
import json
import sys
import re
import argparse
from pathlib import Path
from IPy import IP

# ==================================================================================================
# ANSI colours
# ==================================================================================================
C = {
  "red": "\033[31m",
  "green": "\033[32m",
  "yellow": "\033[33m",
  "white": "\033[37m",
  "end": "\033[0m",
}

def msg(col, text):
  print(C[col] + text + C["end"])

# ==================================================================================================
# Address Policy
# ==================================================================================================
# Loaded at runtime from address_policy.json (sibling to sites.csv by default) — this is the
# single source of truth shared with bind9-dns.yml (Play 2 synthesises the same standard-slot
# devices for DNS, independently, from the same file). Do not hardcode a second copy here; if
# these dicts are empty, load_address_policy() hasn't run yet (see main()).
OFFSETS_SINGLE = {}
ROLE_OFFSETS = {}
STANDARD_OFFSETS = {}
TYPE_CONNECTION = {}

def load_address_policy(policy_path: Path):
  global OFFSETS_SINGLE, ROLE_OFFSETS, TYPE_CONNECTION
  if not policy_path.exists():
    raise ValueError(
      f"address_policy.json not found at {policy_path} — this is the shared source of truth "
      f"for the standard address policy (also used by bind9-dns.yml); it must exist alongside "
      f"sites.csv."
    )
  data = json.loads(policy_path.read_text())
  OFFSETS_SINGLE = data["offsets_single"]
  ROLE_OFFSETS = data["role_offsets"]

  # TYPE_CONNECTION: Type -> ConnectionType (ssh/winrm/telnet/snmp/http/none), flattened from
  # address_policy.json's connection_types. Single source of truth — not a second copy.
  TYPE_CONNECTION.clear()
  for conn, types in data.get("connection_types", {}).items():
    for t in types:
      TYPE_CONNECTION[t] = conn

  # STANDARD_OFFSETS: derived from the address policy just loaded (not a second, separately-
  # maintained copy — inventory_devices.py used to keep its own STANDARD_SINGLE/STANDARD_MULTI
  # tables, which could silently drift from OFFSETS_SINGLE/ROLE_OFFSETS; this builds them from
  # the same source instead). A devices.csv row whose Type+HostOctet exactly matches one of these
  # is already rendered by the standard template for that site — skip it rather than duplicate it.
  STANDARD_OFFSETS.clear()
  for role, offset in OFFSETS_SINGLE.items():
    STANDARD_OFFSETS.setdefault(role, set()).add(offset)
  for role, offsets in ROLE_OFFSETS.items():
    STANDARD_OFFSETS.setdefault(role, set()).update(offsets)

# ==================================================================================================
# devices.csv join — classification of "extra" per-site devices
# ==================================================================================================
# devices.csv columns: Site, Type, Number, HostOctet, OS, ConnectionType, Managed, Notes

# Excluded unconditionally, regardless of octet (per longstanding operator instruction — RAC is
# being decommissioned in favour of BMC; real PVE nodes are handled by the standard template +
# group_vars/pvenodes/, not by the devices.csv exception path).
ALWAYS_EXCLUDE_TYPES = {"RAC", "PVE"}

# Known Type -> existing inventory group, for devices.csv rows that ARE Ansible-managed. Anything
# manageable but not in this map (e.g. a one-off NAS or Rudder relay) falls into a generic
# per-site [site_devices] group instead of a made-up group nothing else references.
DEVICE_GROUP_MAP = {
  "WKS": "windows_desktop",
  "LAP": "windows_laptop",
  "SVR": "windows_server",
  "DCS": "windows_dc",
  "FWL": "firewalls",
}

# Manageability default when devices.csv's own Managed column is blank (true for every row at the
# time this was written — nobody has gone through and filled it in yet). Managed=yes/no on a row
# always overrides this; this is only the fallback guess. A real, recognisable server OS is a
# reasonable signal that this is something we'd actually run Ansible against; an appliance OS
# (or no OS at all — a switch, a coffee machine, a payment terminal) is not.
MANAGEABLE_OS_PATTERN = re.compile(
  r"windows|debian|ubuntu|trixie|bookworm|bullseye|noble|red ?hat|rhel|centos|rocky|almalinux",
  re.IGNORECASE,
)

DEVICE_REQUIRED_COLUMNS = [
  "Site", "Type", "Number", "HostOctet", "OS", "ConnectionType", "Managed", "Notes"
]

# ==================================================================================================
# Special Sites
# ==================================================================================================

SPECIAL_SITES = {
  "VRK": "Virtual Rack / Cloud Abstraction Site (192.168.139.0/24)",
  "CLD": "Cloud Aggregation Site (192.168.69.0/24)",
}

# ==================================================================================================
# Collision Rules
# ==================================================================================================

## These roles are allowed to share same IP
ALLOWED_IP_ALIASES = {
  ("Gateway", "Firewall"),
  ("Firewall", "Gateway"),
}

## BRD / BER are allowed to overlap (legacy vs modern naming)
## Mohrenstraße 37 10117, Berlin, 18:53 CET, Donnerstag 9th November 1989
ALLOWED_SITE_OVERLAP = {
  ("BRD", "BER"),
  ("BER", "BRD"),
}

## Cloud/hub "black swan" sites (CLD, FRD — see site-inventory-audit.py's own black-swan
## handling) have no real standalone Router device; the standard template's Router slot (.1)
## is a documentation-only placeholder for them, not a real device. FRD's actual devices.csv PRV
## row legitimately claims .1 (the real boot-url, per menu.ipxe/late_command.sh) — registering
## the fictional Router slot first would collide with it. Skip that one registration for these
## sites; every other standard-slot registration (Gateway/DC/FW) still happens as normal.
NO_STANDARD_ROUTER_SITES = {"CLD", "FRD"}

# ==================================================================================================
# State
# ==================================================================================================

seen_subnets = {}
seen_ips = {}

# ==================================================================================================
# Helpers
# ==================================================================================================
def validate_cidr(subnet: str):
  subnet = str(subnet).strip().replace("\r", "").replace("\n", "").replace(" ", "")

  try:
    net = IP(str(subnet))   # <-- FIX HERE
  except Exception as e:
    raise ValueError(f"Invalid CIDR '{subnet}': {e}")

  if net.version() != 4:
    raise ValueError(f"IPv4 only supported: {subnet}")
  return net

def offset_ip(net: IP, offset: int) -> str:
  base = IP(net.strNormal(0).split('/')[0])

  # IPy's IP + IP merges adjacent CIDR blocks into a parent network — it is not address offsetting,
  # and fails with a confusing AttributeError if the right-hand side isn't also an IP object. Do the
  # arithmetic on the integer form instead, then rebuild an IP from the result.
  return str(IP(base.int() + offset))

def register_subnet(site: str, net: IP):
  net = IP(str(net))  # FORCE canonical IP object

  for existing_net, existing_site in seen_subnets.items():
    existing_net = IP(str(existing_net))  # FORCE same type

    if (site, existing_site) in ALLOWED_SITE_OVERLAP:
      continue
    if net.overlaps(existing_net):
      raise ValueError(
        f"\nCIDR overlap detected:\n"
        f"  {site} ({net})\n"
        f"  conflicts with {existing_site} ({existing_net})"
      )
  seen_subnets[net.strNormal()] = site

def register_ip(site: str, ip: str, role: str):
  # "N/A" is an established sentinel for "no real value" elsewhere in this estate (e.g. ad_schema.yml
  # rejectattr('Subnet', 'equalto', 'N/A')). It's NOT a real address & must never be collision-checked
  # — two unrelated sites both legitimately having "N/A" for a field is not a collision.
  if str(ip).strip().upper() in ("N/A", "NA", ""):
    return

  if ip in seen_ips:
    prev_site, prev_role = seen_ips[ip]

    # allow intentional role sharing
    if (role, prev_role) in ALLOWED_IP_ALIASES:
      return

    # allow BRD/BER coexistence
    if (site, prev_site) in ALLOWED_SITE_OVERLAP:
      return

    raise ValueError(
      f"\nIP collision detected:\n"
      f"  {ip}\n"
      f"  {site} ({role})\n"
      f"  already used by {prev_site} ({prev_role})"
    )
  seen_ips[ip] = (site, role)

def build_hostname(role: str, site: str, index: int) -> str:
  return f"EXA{role}{site}{index:03d}"

# ==================================================================================================
# devices.csv — load, classify, and join per site
# ==================================================================================================

def validate_devices_csv_structure(rows):
  if not rows:
    return
  header = rows[0].keys()
  for col in DEVICE_REQUIRED_COLUMNS:
    if col not in header:
      raise ValueError(f"devices.csv missing column: {col}")

# ConnectionType values that are real Ansible connection methods (task-execution capable).
# snmp/http are monitoring/query protocols, not Ansible connection methods — a device with one
# of those (or "none") is never treated as managed, regardless of what its OS looks like.
ANSIBLE_CAPABLE_CONNECTIONS = {"ssh", "winrm", "telnet"}

def is_managed(row: dict) -> bool:
  """
  Priority: Managed column (explicit operator override) > ConnectionType (address_policy.json's
  per-Type connection_types — a deliberate signal, not a guess) > OS-based guess (fallback for
  rows predating ConnectionType, or a Type with no entry in connection_types).
  """
  flag = row.get("Managed", "").strip().lower()
  if flag in ("yes", "y", "true", "1"):
    return True
  if flag in ("no", "n", "false", "0"):
    return False

  conn = row.get("ConnectionType", "").strip().lower()
  if conn:
    return conn in ANSIBLE_CAPABLE_CONNECTIONS

  return bool(MANAGEABLE_OS_PATTERN.search(row.get("OS", "") or ""))

def needs_review(row: dict) -> bool:
  """Ambiguous rows: no explicit Managed flag, no ConnectionType, AND no OS-based signal either way."""
  flag = row.get("Managed", "").strip().lower()
  if flag in ("yes", "y", "true", "1", "no", "n", "false", "0"):
    return False
  if row.get("ConnectionType", "").strip():
    return False
  return not (row.get("OS", "") or "").strip()

def load_devices(devices_path: Path):
  """
  Reads devices.csv and returns (devices_by_site, stats) where devices_by_site maps
  site -> list of processed extra-host dicts (hostname, ip, group, managed, notes, type),
  ready to hand to build_ini(). Applies the same exclusions inventory_devices.py used to
  apply as a separate preprocessing pass (standard-offset rows, RAC/PVE rows).
  """
  stats = {
    "total": 0, "excluded_standard": 0, "excluded_always": 0,
    "included_managed": 0, "included_reference": 0, "needs_review": 0,
  }
  devices_by_site = {}

  if not devices_path.exists():
    msg("yellow", f"devices.csv not found at {devices_path} — generating standard template only.")
    return devices_by_site, stats

  rows = list(csv.DictReader(devices_path.open()))
  validate_devices_csv_structure(rows)
  stats["total"] = len(rows)

  for r in rows:
    site = r["Site"].strip()
    dtype = r["Type"].strip().upper()
    octet_raw = r["HostOctet"].strip()

    if dtype in ALWAYS_EXCLUDE_TYPES:
      stats["excluded_always"] += 1
      continue

    octet = int(octet_raw) if octet_raw.isdigit() else None
    if octet is not None and octet in STANDARD_OFFSETS.get(dtype, set()):
      stats["excluded_standard"] += 1
      continue

    try:
      number = int(r["Number"])
    except (KeyError, ValueError):
      msg("yellow", f"Skipping devices.csv row with non-numeric Number: {r}")
      continue

    managed = is_managed(r)
    review = needs_review(r)
    if review:
      stats["needs_review"] += 1
    if managed:
      stats["included_managed"] += 1
    else:
      stats["included_reference"] += 1

    devices_by_site.setdefault(site, []).append({
      "hostname": build_hostname(dtype, site, number),
      "octet": octet,
      "type": dtype,
      "group": DEVICE_GROUP_MAP.get(dtype, "site_devices"),
      "managed": managed,
      "needs_review": review,
      "os": r.get("OS", ""),
      "notes": r.get("Notes", ""),
      "connection_type": r.get("ConnectionType", "").strip().lower(),
      # Optional -- set only when this device's real IP is on a DIFFERENT site's subnet than
      # the one its hostname/Site column names (e.g. a device hostnamed EXA...CLD... that
      # physically sits on FRD Havn's own network, sharing OVH's vRACK fabric with CLD but
      # keeping its own subnet behind its own firewall). Empty/absent for the overwhelming
      # majority of rows, where Site alone determines both hostname and subnet.
      "subnet_site": (r.get("SubnetSite") or "").strip() or None,
    })

  return devices_by_site, stats

def render_device_line(net: IP, dev: dict) -> str:
  conn = dev.get("connection_type", "")
  notes_parts = [dev["notes"]] if dev["notes"] else []

  # snmp/http aren't Ansible connection methods — document them as a query/monitoring protocol
  # instead, since Ansible itself will never be the one connecting to these.
  if conn in ("snmp", "http"):
    notes_parts.append(f"reachable via {conn.upper()}")
  note = f"  # {' -- '.join(notes_parts)}" if notes_parts else ""

  if dev["octet"] is None:
    return f"# {dev['hostname']}  (no HostOctet in devices.csv){note}"

  ip = offset_ip(net, dev["octet"])

  # ssh is Ansible's own default and needs no override; telnet/winrm do. Spelled out explicitly
  # for ssh too, for the same reason windows_dc/windows_bootstrap set it explicitly elsewhere in
  # this repo — makes it correct on an ungrouped/ad hoc run, not just when group_vars applies.
  conn_str = {
    "ssh":    "  ansible_connection=ssh",
    "winrm":  "  ansible_connection=winrm",
    "telnet": "  ansible_connection=community.general.telnet",
  }.get(conn, "")

  return f"{dev['hostname']}  ansible_host={ip}{conn_str}{note}"

# ==================================================================================================
# Output
# ==================================================================================================

def site_filename(site: str):
  return f"{site.lower()}.ini"


def build_ini(site, row, vals, hostnames, net, site_devices):
  managed_by_group = {}
  reference_lines = []
  review_lines = []

  # WAP (.82-.94, added 2026-07-08): count varies per site (unlike BMC/DCS/PVE/FWL's fixed
  # count), so every slot is commented/reference-only, never confirmed-real — matches BMC's
  # treatment. Rendered from ROLE_OFFSETS directly rather than hardcoded so this doesn't drift
  # if address_policy.json's WAP range is ever resized.
  #
  # CLD and VRK are skipped entirely: neither has physical WiFi (CLD is the datacenter/hub,
  # VRK is a virtual provisioning network) — showing a "you might put a WAP here" placeholder
  # at either would be actively misleading. CLD's .82 is instead a REAL device: the UniFi
  # Network Controller (see devices.csv, Type=UFC) that manages every site's WAPs — putting
  # controller/management infrastructure at the same octet the devices it manages use, at the
  # hub site that doesn't have any of those devices itself, is a deliberate convention, not a
  # collision to route around.
  if site in ("CLD", "VRK"):
    wap_block = (
      "# No WAP placeholder block here — this site has no physical WiFi (hub/provisioning\n"
      "# site, not a physical location that serves wireless clients)."
    )
  else:
    wap_count = len(ROLE_OFFSETS.get("WAP", []))
    wap_lines = "\n".join(
      f"# {hostnames[f'WAP{i}']}  {vals[f'WAP{i}']}" for i in range(1, wap_count + 1)
    )
    wap_block = (
      "# Wireless access points (.82-.94, static) — count varies per site, not\n"
      "# Ansible-managed, for reference only. Uncomment the ones that actually exist\n"
      "# at this site:\n"
      f"{wap_lines}"
    )

  for dev in site_devices:
    line = render_device_line(dev.get("_net", net), dev)
    if dev["needs_review"]:
      review_lines.append(f"# NEEDS REVIEW (no OS/Managed set): {line}")
    elif dev["managed"]:
      managed_by_group.setdefault(dev["group"], []).append(line)
    else:
      reference_lines.append(line)

  extra_group_blocks = ""
  for group, lines in managed_by_group.items():
    if group in ("windows_desktop", "windows_laptop", "windows_server", "windows_dc", "firewalls"):
      # These groups already exist above with their standard-template entries — append to
      # the SAME group rather than declaring it a second time (INI parsers merge repeated
      # group headers, but keeping it readable matters more than being clever here).
      continue
    extra_group_blocks += f"\n[{group}]\n" + "\n".join(lines) + "\n"

  # Devices destined for windows_desktop/windows_laptop/windows_dc/firewalls get folded
  # into those groups' existing blocks below via these lookups.
  def extra_for(group):
    lines = managed_by_group.get(group, [])
    return ("\n" + "\n".join(lines)) if lines else ""

  # windows_server has no standard-template hosts of its own any more (DCS moved to its own
  # windows_dc group below, :children-linked into windows_server) -- only devices.csv SVR-role
  # extras (a plain, non-DC server) put anything directly into windows_server. Only emit the
  # section if there's actually something to put in it, since an empty [windows_server] header
  # with nothing but a blank line under it is confusing next to windows_server:children below.
  windows_server_extra_block = ""
  if managed_by_group.get("windows_server"):
    windows_server_extra_block = "\n[windows_server]" + extra_for("windows_server") + "\n"

  other_devices_block = ""
  if reference_lines or review_lines:
    other_devices_block = (
      "\n# Other devices from devices.csv — not Ansible-managed (or not yet classified), "
      "for reference only:\n"
      + "\n".join(f"# {l}" for l in reference_lines)
      + ("\n" + "\n".join(review_lines) if review_lines else "")
      + "\n"
    )

  return f"""# ==================================================================================================
# inventory/{site_filename(site)}
# Example Music Limited — {vals['CITY']} ({site})
#
# --------------------------------------------------------------------------------------------------
# Site Information (for humans — Ansible does not read this block)
#
#   Legal entity  : {row['Entity']}
#   Location      : {row['City']}, {row['Country']} ({row['CountryCode']})
#   Timezone      : {row['Timezone']}
#   Landline      : {row['Landline']}
#   Mobile        : {row['Mobile']}
#
#   Subnet        : {row['Subnet']}
#   Gateway       : {row['Gateway']}
#   Firewall      : {row['FW']}
#   Primary DC    : {row['DC']}
#   Ansible region: {row['AnsibleRegion']}
# --------------------------------------------------------------------------------------------------
#
# THIS FILE IS AUTOMATICALLY GENERATED.
#
# Source:
# /etc/example-music/sites.csv (standard template)
# /etc/example-music/devices.csv (per-site extras, joined in on the Site column)
#
# DO NOT EDIT.
# Changes may be overwritten.
# --------------------------------------------------------------------------------------------------
#
# Addressing
#
# .10 Primary DC
# .11 Secondary DC
# .101 Example workstation
# .102 Example laptop
# .253 Primary Firewall
# .254 Secondary Firewall
#
# ==================================================================================================

[firewalls]
{hostnames['FWL1']}  ansible_host={vals['FW']}  ansible_user=ansible  ansible_connection=ssh
{hostnames['FWL2']}  ansible_host={vals['FW']}  ansible_user=ansible  ansible_connection=ssh{extra_for('firewalls')}

[windows_dc]
{hostnames['DCS1']}  ansible_host={vals['DCS1']}
# {hostnames['DCS2']}  ansible_host={vals['DCS2']}{extra_for('windows_dc')}

[windows_server:children]
windows_dc
{windows_server_extra_block}
[windows_desktop]
# {hostnames['WKS1']}  ansible_host={vals['WKS1']}{extra_for('windows_desktop')}

[windows_laptop]
# {hostnames['LAP1']}  ansible_host={vals['LAP1']}{extra_for('windows_laptop')}

[pvenodes]
{hostnames['PVE1']}  ansible_host={vals['PVE1']}
# {hostnames['PVE2']}  ansible_host={vals['PVE2']}
# {hostnames['PVE3']}  ansible_host={vals['PVE3']}

[windows:children]
windows_server
windows_desktop
windows_laptop

[windows_nodes:children]
windows
{extra_group_blocks}
# Out-of-band management (iDRAC/iLO/Redfish) — not Ansible-managed, for
# reference only:
# {hostnames['BMC1']}  {vals['BMC1']}
# {hostnames['BMC2']}  {vals['BMC2']}
# {hostnames['BMC3']}  {vals['BMC3']}

{wap_block}
{other_devices_block}"""

# ==================================================================================================
# CSV validation
# ==================================================================================================

REQUIRED_COLUMNS = [
  "Site", "City", "Country", "CountryCode", "Subnet", "Gateway", "DC", "FW", "Landline", "Mobile",
  "Timezone", "AnsibleRegion", "Entity"
]

def validate_csv_structure(rows):
  if not rows:
    raise ValueError("CSV empty")
  header = rows[0].keys()

  for col in REQUIRED_COLUMNS:
    if col not in header:
      raise ValueError(f"Missing column: {col}")

# ==================================================================================================
# Standard device synthesis — for consumers other than the .ini generator (e.g. bind9-dns.yml,
# which needs a DNS record for every confirmed-real standard-slot device now that devices.csv is
# exceptions-only rather than a complete device list — see address_policy.json's header comment)
# ==================================================================================================
# Only slots build_ini() shows UNCOMMENTED (confirmed real, not a "may not be built yet"
# placeholder) are synthesized here:
#   - RTR/PRV/SBC: single-instance infra roles, always physically present at a real site (even
#     though they're not Ansible-managed/not rendered in the .ini at all)
#   - FWL: both instances (FWL1/FWL2) are real in every site's .ini
#   - DCS/PVE: only the FIRST instance is real in the .ini (DCS2/PVE2/PVE3 are commented —
#     "may not be built yet"); synthesizing a DNS record for a DC/PVE node that might not exist
#     would be actively misleading, and WOULD collide with devices.csv's OWN numbering for real
#     extra instances at that site (devices.csv's Number is chosen independently by whoever
#     filled in the row, not guaranteed to skip index 1)
#   - WKS/LAP "example" slots and BMC (all always commented/reference-only in the .ini) are never
#     synthesized here for the same reason — see the Notes above about hostname collisions this
#     caused in testing (e.g. a real devices.csv "WKS Number=1" at a non-standard octet
#     legitimately reusing EXAWKS<SITE>001, the same hostname the "example" placeholder would use)
DNS_SINGLE_ROLES = ["RTR", "PRV", "SBC"]
DNS_MULTI_ALL_INSTANCES = {"FWL"}
DNS_MULTI_FIRST_INSTANCE_ONLY = {"DCS", "PVE"}

def compute_standard_devices_for_site(site: str, net: IP):
  """
  Returns every confirmed-real standard-slot device for one site as a flat list of dicts
  (Site, Hostname, HostOctet, Notes) — the same addresses build_ini() derives for the ones it
  shows uncommented, just shaped for JSON consumption instead of f-string interpolation.
  """
  suppressed = SUPPRESSED_STANDARD_ROLES.get(site, set())

  devices = []
  for role in DNS_SINGLE_ROLES:
    if role in suppressed:
      continue
    devices.append({
      "Site": site,
      "Hostname": build_hostname(role, site, 1),
      "HostOctet": str(OFFSETS_SINGLE[role]),
      "Notes": f"Standard {role} slot",
    })
  for role, offsets in ROLE_OFFSETS.items():
    if role in suppressed:
      continue
    if role in DNS_MULTI_ALL_INSTANCES:
      selected = list(enumerate(offsets, start=1))
    elif role in DNS_MULTI_FIRST_INSTANCE_ONLY:
      selected = [(1, offsets[0])]
    else:
      continue  # e.g. BMC — always commented/reference-only, never synthesized for DNS
    for i, offset in selected:
      devices.append({
        "Site": site,
        "Hostname": build_hostname(role, site, i),
        "HostOctet": str(offset),
        "Notes": f"Standard {role} slot {i}",
      })
  return devices

# BRD (West Berlin) is a real, separate site that happens to share BER's exact subnet — see
# ALLOWED_SITE_OVERLAP above, which already treats this as intentional: the .ini generator gives
# BRD its own brd.ini with its own EXA...BRD... hostnames at the same IPs as BER's. Two hostnames
# resolving to the same address is normal DNS (like aliases), so BRD gets its own standard-slot
# synthesis and keeps its own devices.csv rows here too — it is NOT folded into BER. (An earlier
# version of this function did fold BRD into BER, which silently erased BRD's own identity and
# its real devices.csv rows — wrong, caught in review.)

# Sites that have a real sites.csv row/subnet but deliberately do NOT follow the standard
# per-site convention (per bind9-dns.yml's own "CLD BLACK SWAN" documentation for VRK: the
# provisioning network, with manually-assigned roles — no EXADCS, no EXAPVE, no EXASBC). Their
# standard-slot devices are never synthesized; only their real devices.csv rows appear.
# FRD (Fredericia Havn) gets the same treatment — it's one machine (a MacBook playing PXE
# server + secondary PBX), not a real office with DCS/FWL/PVE of its own.
NON_STANDARD_SITES = {"VRK", "FRD"}

# CLD has real DCS/FWL/PVE (unlike VRK/FRD), so it can't go in NON_STANDARD_SITES wholesale —
# but it deliberately reuses specific empty standard slots for real devices.csv devices (PBX on
# the SBC octet, since CLD has no SBC of its own — same pattern as the UniFi controller reusing
# WAP1's octet). Suppress just those specific standard roles per site, so the fictional
# standard-slot entry doesn't collide in the DNS output with the real device sitting there.
SUPPRESSED_STANDARD_ROLES = {
  "CLD": {"SBC"},
}

def emit_devices_for_dns(csv_path: Path, devices_path: Path):
  """
  Prints the FULL, deduplicated device list (every standard-slot device for every site, plus
  every devices.csv exception that isn't just a redundant description of a standard slot) as
  JSON to stdout, with full_ip already resolved — everything bind9-dns.yml needs to generate DNS
  records, computed by the exact same rules (STANDARD_OFFSETS/ALWAYS_EXCLUDE_TYPES exclusion,
  build_hostname, ALLOWED_SITE_OVERLAP) the .ini generator uses, so the two can never disagree
  about which devices are real or what they're called. BRD/BER's shared subnet duplicates IPs
  under different hostnames by design — bind9-dns.yml keeps BRD out of the per-site *reverse*
  zone loop only (a subnet can only have one authoritative reverse zone; BER owns it), not out of
  the forward zone.

  OPEN QUESTION (2026-07-11, not resolved here): a device with a SubnetSite override (see
  load_devices()) now gets a correct full_ip on its real subnet, so the FORWARD zone is right.
  The REVERSE zone is not necessarily right — bind9-dns.yml's per-site reverse-zone loop filters
  all_devices by Site (the hostname/naming site), not SubnetSite, and CLD doesn't go through
  that generic loop at all (it has its own dedicated db.192.168.139 handling, which has no
  awareness of FRD's 172.16.124.0/24 range). A CLD-hostnamed, FRD-subnetted device may end up
  with no PTR record at all rather than a wrong one -- confirmed safe-by-omission, not fixed.
  Needs a real decision (does FRD Havn get its own reverse zone at all?) before touching the
  reverse-zone templates further.
  """
  rows = list(csv.DictReader(csv_path.open()))
  validate_csv_structure(rows)

  subnet_base = {}
  all_devices = []
  for r in rows:
    try:
      net = validate_cidr(r["Subnet"])
    except ValueError:
      continue  # e.g. Subnet == "N/A" — same rows generate()'s per-site loop would also choke on
    subnet_base[r["Site"]] = ".".join(net.strNormal(0).split("/")[0].split(".")[:3])
    if r["Site"] in NON_STANDARD_SITES:
      continue  # e.g. VRK — no standard-convention devices, only its real devices.csv rows
    all_devices.extend(compute_standard_devices_for_site(r["Site"], net))

  devices_by_site, _stats = load_devices(devices_path)
  for site, site_devices in devices_by_site.items():
    for dev in site_devices:
      all_devices.append({
        "Site": site,
        # SubnetSite override (see load_devices()) -- which site's subnet this device's real
        # IP is actually on, if different from Site (its hostname/naming site). Empty string,
        # not None, so the reverse-zone consumer below can treat "" the same as "unset" without
        # a separate None check.
        "SubnetSite": dev["subnet_site"] or "",
        "Hostname": dev["hostname"],
        "HostOctet": str(dev["octet"]) if dev["octet"] is not None else "",
        "Notes": dev["notes"],
      })

  for d in all_devices:
    # Standard-slot devices (from compute_standard_devices_for_site()) never have a
    # SubnetSite key at all -- only devices.csv exceptions can carry one.
    base = subnet_base.get(d.get("SubnetSite") or d["Site"], "")
    d["full_ip"] = f"{base}.{d['HostOctet']}" if (base and d["HostOctet"]) else ""

  print(json.dumps(all_devices))

# ==================================================================================================
# Generated group_vars — well-known services
# ==================================================================================================
# Playbooks have historically hardcoded well-known service addresses (provisioning server,
# Ansible control node, PBX, etc) as literals scattered across many files — e.g.
# ansible/configs/inventory/group_vars/all/vars.yml's exa_asset_base, windows_bootstrap/playbooks/
# 05-bootstrap.yml's
# own duplicate copy of the same value, bind9-dns.yml's ancillary_hosts list. Every one of these
# is already a real devices.csv row; this emits them as a single generated group_vars file so
# Ansible reads one derived source instead of N hand-maintained copies that can silently drift
# (as CLD's PBX octet already did once this session — see generate_inventory.py's own changelog).

def find_device(devices_by_site: dict, site: str, dtype: str):
  """
  First devices.csv row matching (site, dtype), or None if there isn't one. Tries the direct
  Site bucket first (the common case), then falls back to scanning every site's devices for
  a SubnetSite match -- a device can be hostnamed/bucketed under one site while physically
  living on another's network (e.g. a CLD-hostnamed device whose real subnet is FRD Havn's),
  and callers here mean "physically at this site" (see prv_frd/pbx_frd below), not "hostnamed
  under this site". See load_devices()'s subnet_site field and the 2026-07-11 CLD/FRD rework.
  """
  for dev in devices_by_site.get(site, []):
    if dev["type"] == dtype:
      return dev
  for devs in devices_by_site.values():
    for dev in devs:
      if dev["type"] == dtype and dev.get("subnet_site") == site:
        return dev
  return None

def compute_site_services(csv_path: Path, devices_path: Path, ad_forest_path: Path = None) -> dict:
  """
  Well-known service hostnames/IPs/subnets derived from sites.csv + devices.csv, plus the AD
  forest's domain name (from ad_forest.json, if given) as "_domain_fqdn" -- underscore-prefixed
  since it's a single string, not a {hostname,ip,...} dict like the other entries. Shared by
  emit_group_vars() (site_services.yml, for Ansible) and emit_begyndelse_json() (begyndelse.json,
  for non-Ansible consumers like bindme.sh/menu.ipxe/firewallme) so the two outputs can never
  drift out of sync with each other -- this is the one place either is computed from.
  """
  rows = list(csv.DictReader(csv_path.open()))
  validate_csv_structure(rows)

  nets = {}
  for r in rows:
    try:
      nets[r["Site"]] = validate_cidr(r["Subnet"])
    except ValueError:
      continue  # e.g. Subnet == "N/A"

  devices_by_site, _stats = load_devices(devices_path)

  def lookup(site, dtype, with_subnet=False):
    dev = find_device(devices_by_site, site, dtype)
    if dev is None or dev["octet"] is None or site not in nets:
      return None
    result = {"hostname": dev["hostname"], "ip": offset_ip(nets[site], dev["octet"])}
    if with_subnet:
      result["subnet"] = str(nets[site])
    return result

  prv_edi = lookup("VRK", "PRV", with_subnet=True)
  prv_frd = lookup("FRD", "PRV", with_subnet=True)
  dns = lookup("VRK", "DNS")
  ans = lookup("CLD", "ANS")
  pbx_edi = lookup("CLD", "PBX")
  pbx_frd = lookup("FRD", "PBX")
  rdr = lookup("CLD", "RDR")
  wac = lookup("CLD", "SVR")

  # Port 8000 is a real, fixed detail of the Fredericia Havn MacBook's python3 http.server setup
  # (menu.ipxe/late_command.sh both hardcode it too) -- not derivable from devices.csv, which has
  # no port column. Documented here for reference even though nothing currently consumes these
  # URLs directly -- windows_bootstrap's assets moved to a local files/ win_copy (2026-07-08),
  # since HTTP-fetching from the provisioning server was only ever a pre-Ansible bootstrap thing.
  if prv_edi:
    prv_edi["url"] = f"http://{prv_edi['ip']}"
  if prv_frd:
    prv_frd["url"] = f"http://{prv_frd['ip']}:8000"

  result = {
    "provisioning_edinburgh": prv_edi,
    "provisioning_fredericia_havn": prv_frd,
    "dns": dns,
    "ansible_control": ans,
    "pbx_edinburgh": pbx_edi,
    "pbx_fredericia_havn": pbx_frd,
    "rudder": rdr,
    "wac": wac,
  }

  if ad_forest_path is not None and ad_forest_path.exists():
    ad_forest = json.loads(ad_forest_path.read_text())
    result["_domain_fqdn"] = ad_forest.get("domain_fqdn")

  return result


def emit_group_vars(csv_path: Path, devices_path: Path, ad_forest_path: Path = None) -> str:
  """
  Returns the full text of ansible/configs/inventory/group_vars/all/site_services.yml -- well-known service
  hostnames/IPs derived from sites.csv + devices.csv, plus domain_fqdn from ad_forest.json.
  """
  services = compute_site_services(csv_path, devices_path, ad_forest_path)
  domain_fqdn = services.pop("_domain_fqdn", None)

  def yaml_block(name, dev):
    if dev is None:
      return f"  {name}: null  # no matching devices.csv row found\n"
    lines = [f"  {name}:\n"]
    for key in ("hostname", "ip", "subnet", "url"):
      if key in dev:
        lines.append(f"    {key}: \"{dev[key]}\"\n")
    return "".join(lines)

  blocks = "".join(yaml_block(name, dev) for name, dev in services.items())
  domain_line = f'  domain_fqdn: "{domain_fqdn}"\n' if domain_fqdn else ""

  return f"""\
# =============================================================================
# ansible/configs/inventory/group_vars/all/site_services.yml
# Example Music Limited — well-known service addresses
#
# THIS FILE IS AUTOMATICALLY GENERATED by benarbejde/generate_inventory.py --emit-group-vars.
# Source: sites.csv + devices.csv (single source of truth) — do not hand-edit, regenerate instead.
#
# Documents well-known service addresses in one derived place instead of hardcoded literals
# scattered across playbooks (e.g. bind9-dns.yml's ancillary_hosts, migrated 2026-07-08 to read
# devices.csv directly rather than this file — see that playbook's own changelog). If a
# well-known service's IP ever changes, fix its devices.csv row and regenerate.
#
# For non-Ansible consumers (bindme.sh, menu.ipxe, etc.) see benarbejde/begyndelse.json instead
# -- same underlying data, JSON, jq-friendly. Both are generated from compute_site_services() in
# this script, so they never drift out of sync with each other.
# =============================================================================

site_services:
{domain_line}{blocks}"""


def emit_begyndelse_json(csv_path: Path, devices_path: Path, ad_forest_path: Path = None) -> str:
  """
  Returns the full text of benarbejde/begyndelse.json -- the same well-known service data as
  site_services.yml, in JSON, for non-Ansible consumers (bindme.sh/ansibleme.sh/firewallme.sh,
  menu.ipxe-adjacent tooling) to read via jq instead of hardcoding IPs.

  "Begyndelse" is Danish for "beginning"/"origin" -- matches benarbejde/'s own Danish naming.
  """
  services = compute_site_services(csv_path, devices_path, ad_forest_path)
  domain_fqdn = services.pop("_domain_fqdn", None)
  payload = {
    "_comment": (
      "Example Music Limited -- well-known service addresses. AUTOMATICALLY GENERATED by "
      "benarbejde/generate_inventory.py --emit-begyndelse-json. Source: sites.csv + devices.csv "
      "(single source of truth) -- do not hand-edit, regenerate instead. Same underlying data as "
      "ansible/configs/inventory/group_vars/all/site_services.yml (for Ansible); this file is for "
      "everything else."
    ),
    **({"domain_fqdn": domain_fqdn} if domain_fqdn else {}),
    **services,
  }
  return json.dumps(payload, indent=2) + "\n"

# ==================================================================================================
# Generator
# ==================================================================================================

def generate(csv_path: Path, out_dir: Path, devices_path: Path):
  rows = list(csv.DictReader(csv_path.open()))
  validate_csv_structure(rows)

  out_dir.mkdir(parents=True, exist_ok=True)

  devices_by_site, device_stats = load_devices(devices_path)

  # Full site -> subnet lookup, built before the main loop so a devices.csv row's optional
  # SubnetSite override (a device whose hostname/site-segment is one site but whose real IP
  # is on a different site's subnet -- e.g. a device folded into CLD's naming that still
  # physically sits on FRD Havn's own network) can resolve regardless of row order in
  # sites.csv. See the 2026-07-11 CLD/FRD Pulsant-vRACK rework.
  site_to_net = {r["Site"]: validate_cidr(r["Subnet"]) for r in rows}

  for r in rows:
    site = r["Site"]
    net = validate_cidr(r["Subnet"])

    register_subnet(site, net)

    vals = {
      "SITE": site,
      "CITY": r["City"],
      "COUNTRY": r["Country"],
      "SUBNET": r["Subnet"],
      "GATEWAY": r["Gateway"],
      "DC": r["DC"],
      "FW": r["FW"],
      "TZ": r["Timezone"],
      "REGION": r["AnsibleRegion"],
    }

    hostname_map = {}

    ## fixed single-role offsets
    vals["RTR"] = offset_ip(net, OFFSETS_SINGLE["RTR"])
    vals["PRV"] = offset_ip(net, OFFSETS_SINGLE["PRV"])
    vals["SBC"] = offset_ip(net, OFFSETS_SINGLE["SBC"])
    vals["WKS1"] = offset_ip(net, OFFSETS_SINGLE["WKS"])
    vals["LAP1"] = offset_ip(net, OFFSETS_SINGLE["LAP"])

    ## fixed multi-role offsets (BMC/PVE etc)
    for role, offsets in ROLE_OFFSETS.items():
      for i, off in enumerate(offsets, start=1):
        ip = offset_ip(net, off)
        vals[f"{role}{i}"] = ip

        # NEW: deterministic hostname (3-digit safe)
        hostname_map[f"{role}{i}"] = build_hostname(role, site, i)

    # DCS special (DCS is a two-instance role, defined in ROLE_OFFSETS — not OFFSETS_SINGLE)
    vals["DCS1"] = offset_ip(net, ROLE_OFFSETS["DCS"][0])
    vals["DCS2"] = offset_ip(net, ROLE_OFFSETS["DCS"][1])

    # Hostnames for roles that appear in .ini — built via build_hostname() so  EXA<ROLE><SITE><NNN>
    # convention lives in one place rather than being duplicated as inline string literals.
    hostnames = {
      "FWL1": build_hostname("FWL", site, 1),
      "DCS1": build_hostname("DCS", site, 1),
      "DCS2": build_hostname("DCS", site, 2),
      "WKS1": build_hostname("WKS", site, 1),
      "LAP1": build_hostname("LAP", site, 1),
    }
    hostnames.update(hostname_map)

    # register IPs — standard template
    register_ip(site, vals["GATEWAY"], "Gateway")
    register_ip(site, vals["DC"], "Domain Controller")
    register_ip(site, vals["FW"], "Firewall")
    if site not in NO_STANDARD_ROUTER_SITES:
      register_ip(site, vals["RTR"], "Router")

    # register IPs — devices.csv extras for this site (real collisions against the standard
    # template, or between two devices.csv rows, are still caught here)
    site_devices = devices_by_site.get(site, [])
    for dev in site_devices:
      dev["_net"] = site_to_net[dev["subnet_site"]] if dev["subnet_site"] else net
      if dev["octet"] is not None:
        register_ip(dev["subnet_site"] or site, offset_ip(dev["_net"], dev["octet"]), dev["type"])

    dest = out_dir / site_filename(site)

    if dest.exists():
      msg("yellow", f"{dest} exists")
      if input("Overwrite? [y/N]: ").strip().lower() != "y":
        continue

    dest.write_text(build_ini(site, r, vals, hostnames, net, site_devices))
    msg("green", f"Wrote {dest}")

  msg("white",
    f"\ndevices.csv: {device_stats['total']} rows read | "
    f"{device_stats['excluded_standard']} already-standard (skipped) | "
    f"{device_stats['excluded_always']} RAC/PVE (skipped) | "
    f"{device_stats['included_managed']} added as managed hosts | "
    f"{device_stats['included_reference']} added as reference-only | "
    f"{device_stats['needs_review']} flagged NEEDS REVIEW (no OS/Managed set)"
  )

# ==================================================================================================
# CLI
# ==================================================================================================

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("csv", type=Path, help="Path to sites.csv")
  parser.add_argument("-o", "--out", type=Path, default=Path.home() / "ansible/configs/inventory")
  parser.add_argument(
    "--devices", type=Path, default=None,
    help="Path to devices.csv (default: devices.csv next to sites.csv)"
  )
  parser.add_argument(
    "--policy", type=Path, default=None,
    help="Path to address_policy.json (default: address_policy.json next to sites.csv)"
  )
  parser.add_argument(
    "--ad-forest", type=Path, default=None,
    help="Path to ad_forest.json (default: ad_forest.json next to sites.csv). Used by "
         "--emit-group-vars/--emit-begyndelse-json to add a domain_fqdn field."
  )
  parser.add_argument(
    "--emit-devices-json", action="store_true",
    help="Print the full merged device list (standard-slot + devices.csv exceptions, full_ip "
         "resolved) as JSON to stdout instead of writing .ini files — used by bind9-dns.yml to "
         "generate DNS records from the exact same data the .ini generator uses."
  )
  parser.add_argument(
    "--emit-group-vars", action="store_true",
    help="Write ansible/configs/inventory/group_vars/all/site_services.yml — well-known service "
         "addresses (provisioning servers, DNS, Ansible control node, PBX, Rudder, WAC) derived "
         "from sites.csv + devices.csv, instead of writing .ini files."
  )
  parser.add_argument(
    "--group-vars-out", type=Path, default=None,
    help="Path to write with --emit-group-vars (default: "
         "ansible/configs/inventory/group_vars/all/site_services.yml, resolved relative to this "
         "script's own location)."
  )
  parser.add_argument(
    "--emit-begyndelse-json", action="store_true",
    help="Write benarbejde/begyndelse.json — the same well-known service addresses as "
         "--emit-group-vars, in JSON, for non-Ansible consumers (bindme.sh, menu.ipxe, etc.) to "
         "read via jq instead of hardcoding IPs."
  )
  parser.add_argument(
    "--begyndelse-out", type=Path, default=None,
    help="Path to write with --emit-begyndelse-json (default: begyndelse.json next to sites.csv)."
  )
  args = parser.parse_args()

  devices_path = args.devices if args.devices is not None else args.csv.parent / "devices.csv"
  policy_path = args.policy if args.policy is not None else args.csv.parent / "address_policy.json"
  ad_forest_path = args.ad_forest if args.ad_forest is not None else args.csv.parent / "ad_forest.json"

  try:
    load_address_policy(policy_path)
    if args.emit_devices_json:
      emit_devices_for_dns(args.csv, devices_path)
    elif args.emit_group_vars:
      group_vars_out = args.group_vars_out or (
        Path(__file__).resolve().parent.parent / "ansible" / "configs" / "inventory" / "group_vars"
        / "all" / "site_services.yml"
      )
      group_vars_out.parent.mkdir(parents=True, exist_ok=True)
      group_vars_out.write_text(emit_group_vars(args.csv, devices_path, ad_forest_path))
      msg("green", f"Wrote {group_vars_out}")
    elif args.emit_begyndelse_json:
      begyndelse_out = args.begyndelse_out or (args.csv.parent / "begyndelse.json")
      begyndelse_out.parent.mkdir(parents=True, exist_ok=True)
      begyndelse_out.write_text(emit_begyndelse_json(args.csv, devices_path, ad_forest_path))
      msg("green", f"Wrote {begyndelse_out}")
    else:
      generate(args.csv, args.out, devices_path)
  except Exception as e:
    msg("red", f"[FATAL]\n{e}")
    sys.exit(2)

if __name__ == "__main__":
  main()
