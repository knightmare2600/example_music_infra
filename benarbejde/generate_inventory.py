#!/usr/bin/env python3

# =============================================================================
# Example Music Inventory Generator
#
# Authoritative source:
#     /etc/example-music/sites.csv
#
# Requires an apt -y install python3-ipy to be run on your ansible node.
#
# Address allocation policy
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
#   .253        FWL   Firewall
#
# Host naming:
#
#   EXA<ROLE><SITE><NNN>
# =============================================================================
# Changelog:
#   2026-07-05  Fixed offset_ip() — IPy's IP.__add__ is reserved for merging
#               two adjacent IP()/network objects into a parent CIDR block
#               (see https://pypi.org/project/IPy/), it is not address
#               offsetting. `base + offset` with offset as a plain int made
#               IPy's __add__ try to read offset._ipversion, causing
#               "'int' object has no attribute '_ipversion'". Fixed by
#               converting to the integer form with .int(), adding there,
#               then rebuilding an IP from the result.
# =============================================================================

import csv
import sys
import argparse
from pathlib import Path
from IPy import IP

# =============================================================================
# ANSI colours
# =============================================================================

C = {
  "red": "\033[31m",
  "green": "\033[32m",
  "yellow": "\033[33m",
  "white": "\033[37m",
  "end": "\033[0m",
}

def msg(col, text):
  print(C[col] + text + C["end"])

# =============================================================================
# Address Policy
# =============================================================================

OFFSETS_SINGLE = {
  "RTR": 1,
  "DCS": [10, 11],
  "PRV": 15,
  "SBC": 48,
  "WKS": 101,
  "LAP": 102,
  "FWL": 253,
}

ROLE_OFFSETS = {
  "BMC": [2, 3, 4],
  "PVE": [5, 6, 7],
}

# =============================================================================
# Special Sites
# =============================================================================

SPECIAL_SITES = {
  "VRK": "Virtual Rack / Cloud Abstraction Site (192.168.139.0/24)",
  "CLD": "Cloud Aggregation Site (192.168.69.0/24)",
}

# =============================================================================
# Collision Rules
# =============================================================================

# These roles are allowed to share same IP
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

# =============================================================================
# State
# =============================================================================

seen_subnets = {}
seen_ips = {}

# =============================================================================
# Helpers
# =============================================================================
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
  # IPy's IP + IP merges adjacent CIDR blocks into a parent network — it is
  # not address offsetting, and fails with a confusing AttributeError if the
  # right-hand side isn't also an IP object. Do the arithmetic on the
  # integer form instead, then rebuild an IP from the result.
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

# =============================================================================
# Output
# =============================================================================

def site_filename(site: str):
  return f"{site.lower()}.ini"


def build_ini(site, row, vals):
  return f"""
[network]
SITE={vals['SITE']}
CITY={vals['CITY']}
COUNTRY={vals['COUNTRY']}
SUBNET={vals['SUBNET']}
GATEWAY={vals['GATEWAY']}
DC={vals['DC']}
FW={vals['FW']}
TZ={vals['TZ']}
REGION={vals['REGION']}

[infra]
RTR={vals['RTR']}

BMC1={vals['BMC1']}
BMC2={vals['BMC2']}
BMC3={vals['BMC3']}

PVE1={vals['PVE1']}
PVE2={vals['PVE2']}
PVE3={vals['PVE3']}

DCS1={vals['DCS1']}
DCS2={vals['DCS2']}

PRV={vals['PRV']}
SBC={vals['SBC']}

WKS1={vals['WKS1']}
LAP1={vals['LAP1']}
"""

# =============================================================================
# CSV validation
# =============================================================================

REQUIRED_COLUMNS = [
  "Site", "City", "Country", "CountryCode",
  "Subnet", "Gateway", "DC", "FW",
  "Landline", "Mobile", "Timezone",
  "AnsibleRegion", "Entity"
]

def validate_csv_structure(rows):
  if not rows:
    raise ValueError("CSV empty")

  header = rows[0].keys()

  for col in REQUIRED_COLUMNS:
    if col not in header:
      raise ValueError(f"Missing column: {col}")

# =============================================================================
# Generator
# =============================================================================

def generate(csv_path: Path, out_dir: Path):
  rows = list(csv.DictReader(csv_path.open()))
  validate_csv_structure(rows)

  out_dir.mkdir(parents=True, exist_ok=True)

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

    # fixed single-role offsets
    vals["RTR"] = offset_ip(net, OFFSETS_SINGLE["RTR"])
    vals["PRV"] = offset_ip(net, OFFSETS_SINGLE["PRV"])
    vals["SBC"] = offset_ip(net, OFFSETS_SINGLE["SBC"])
    vals["WKS1"] = offset_ip(net, OFFSETS_SINGLE["WKS"])
    vals["LAP1"] = offset_ip(net, OFFSETS_SINGLE["LAP"])

    # fixed multi-role offsets (BMC/PVE etc)
    for role, offsets in ROLE_OFFSETS.items():
      for i, off in enumerate(offsets, start=1):
        ip = offset_ip(net, off)
        vals[f"{role}{i}"] = ip

        # NEW: deterministic hostname (3-digit safe)
        hostname_map[f"{role}{i}"] = build_hostname(role, site, i)

    # DCS special
    vals["DCS1"] = offset_ip(net, OFFSETS_SINGLE["DCS"][0])
    vals["DCS2"] = offset_ip(net, OFFSETS_SINGLE["DCS"][1])

    # register IPs
    register_ip(site, vals["GATEWAY"], "Gateway")
    register_ip(site, vals["DC"], "Domain Controller")
    register_ip(site, vals["FW"], "Firewall")
    register_ip(site, vals["RTR"], "Router")

    dest = out_dir / site_filename(site)

    if dest.exists():
      msg("yellow", f"{dest} exists")
      if input("Overwrite? [y/N]: ").strip().lower() != "y":
        continue

    dest.write_text(build_ini(site, r, vals))
    msg("green", f"Wrote {dest}")

# =============================================================================
# CLI
# =============================================================================

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("csv", type=Path)
  parser.add_argument("-o", "--out", type=Path, default=Path.home() / "ansible/inventory")
  args = parser.parse_args()

  try:
    generate(args.csv, args.out)
  except Exception as e:
    msg("red", f"[FATAL]\n{e}")
    sys.exit(2)

if __name__ == "__main__":
  main()
