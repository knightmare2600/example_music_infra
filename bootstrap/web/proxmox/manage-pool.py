#!/usr/bin/env python3

"""
===============================================================================
Proxmox Pool Manager
===============================================================================

This script connects to a Proxmox cluster and ensures the existence of one
or more specified pools. Pools are validated against known site codes and
enforced as uppercase.

Colour-coded output:
- RED     → Failure
- YELLOW  → Skipped (invalid/existing)
- GREEN   → Created
- CYAN    → Info

Example usage:

1) Bulk create pools (password prompt):

python3 manage-pool.py --host proxmox.example.com --user root@pam --create GLA EDI PRV --comment "Infrastructure pools"

2) Bulk create pools (API token)

python3 manage-pool.py --host pve.example.com --user root@pam --token-name poolmgr --token-value "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" --create GLA PRV --comment "Infrastructure pools"

3) List all VMs and Containers

python3 manage-pool.py --host proxmox.example.com --user root@pam --list

4) Add all firewall VMs via wildcard

python3 manage-pool.py --host proxmox.example.com --user root@pam --match "FW-*" --pool FIREWALLS

 5.) Dry-run creating pools GLA, EDI, and PRV
 
 python3 manage-pool.py --host proxmox.example.com --user root@pam --dry-run GLA EDI PRV

===============================================================================
Authentication priority:
  1. --token-name / --token-value  (preferred — no password in shell history)
  2. --user + password prompt      (interactive — never passed on command line)
===============================================================================

Full Version History:

v1.0 - Initial release
    • Connect to Proxmox cluster
    • Create one or more pools
    • Colour-coded status output
    • Supports username/password or API token authentication

v1.1 - Improvements
    • Handles multiple pool arguments
    • Reports skipped pools
    • Inline comments added
    • Clean exit on authentication or API failure

v1.2 - Validation & dry-run
    • Added validation against known site codes
    • Invalid pools skipped (yellow)
    • Added --dry-run mode to simulate actions
    • PRV site code added for provisioning
    • Output consistent with audit script colour scheme

v1.3 - Safety enhancements
    • Added mandatory confirmation prompt (type 'yes')
    • Default action is NO (safe by default)
    • Added cyan pre-flight summary of pools to be created
    • Dry-run bypasses confirmation step

v1.4 - Uppercase enforcement
    • All pool names automatically converted to uppercase
    • Prevents accidental mis-casing issues

v1.5 - Confirmation preview
    • Pre-flight summary now shows pools in uppercase
    • User must type 'yes' to proceed

v1.6 - Cosmetic fixes
    • Highlight invalid pools in yellow in confirmation preview
    • Verbose preview shows existing pools in cyan

"""

import argparse
import getpass
import sys
import fnmatch
from proxmoxer import ProxmoxAPI
from proxmoxer.backends.https import AuthenticationError
import requests

""" Disable SSL warnings (lab usage only) """
requests.packages.urllib3.disable_warnings()

""" ANSI Colours """
class C:
  RED = "\033[91m"
  GREEN = "\033[92m"
  YELLOW = "\033[93m"
  CYAN = "\033[96m"
  RESET = "\033[0m"

def info(msg): print(f"{C.CYAN}[INFO]{C.RESET} {msg}")
def ok(msg): print(f"{C.GREEN}[OK]{C.RESET} {msg}")
def warn(msg): print(f"{C.YELLOW}[SKIP]{C.RESET} {msg}")
def err(msg): print(f"{C.RED}[FAIL]{C.RESET} {msg}")

# Site codes loaded from sites.csv (single source of truth)

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


""" -----------------------------{ Connect to Proxmox ----------------------------- """
def connect_proxmox(args):
  try:
    if args.token_name and args.token_value:
      info(f"Connecting with API token {args.token_name}...")
      return ProxmoxAPI(
        args.host,
        user=args.user,
        token_name=args.token_name,
        token_value=args.token_value,
        verify_ssl=False
      )
    else:
      if not args.password:
        args.password = getpass.getpass(f"Password for {args.user}: ")
      info("Connecting with user/password...")
      return ProxmoxAPI(
        args.host,
        user=args.user,
        password=args.password,
        verify_ssl=False
      )
  except AuthenticationError:
    err("Authentication to Proxmox failed")
    sys.exit(2)
  except Exception as e:
    err(f"Unable to connect: {e}")
    sys.exit(2)

""" -----------------------------{ List all VMs and CTs }----------------------------- """
def list_vms(proxmox):
  resources = proxmox.cluster.resources.get(type="vm")
  vm_map = {}
  print("\nAvailable VMs/CTs:")
  print("--------------------------------------------------")
  for r in resources:
    vmid = str(r["vmid"])
    name = r.get("name","unknown")
    node = r.get("node","unknown")
    status = r.get("status","unknown")
    vm_map[name] = vmid
    print(f"{vmid:>5} | {name:<25} | {node:<10} | {status}")
  print("--------------------------------------------------\n")
  return vm_map

""" -----------------------------{ Create one or more pools }----------------------------- """
def create_pools(proxmox, pools, comment=None, dry_run=False):
  to_create = []
  invalid = []
  existing = set(p["poolid"].upper() for p in proxmox.pools.get())
  for pool in pools:
    pool = pool.upper()
    if pool not in SITE_CODES:
      invalid.append(pool)
      warn(f"{pool} invalid site code")
    elif pool in existing:
      existing.add(pool)
      warn(f"{pool} already exists")
    else:
      to_create.append(pool)
  if not to_create:
    info("Nothing to do")
    return
  """ Pre-flight preview """
  preview = []
  for p in to_create + invalid + list(existing):
    if p in invalid:
      preview.append(f"{C.YELLOW}{p}{C.RESET}")
    elif p in existing:
      preview.append(f"{C.CYAN}{p}{C.RESET}")
    else:
      preview.append(p)
  print(f"\n{C.CYAN}Pools to be created (uppercase preview):{C.RESET} {', '.join(preview)}")
  """ Confirm """
  confirm = input("Type 'yes' to proceed (default=no): ").strip()
  if confirm.lower() != "yes":
    warn("Aborted (confirmation not given)")
    return
  """ Create pools """
  for pool in to_create:
    if dry_run:
      info(f"[DRY-RUN] Would create '{pool}'")
      continue
    try:
      proxmox.pools.post(poolid=pool, comment=comment or "")
      ok(f"Pool '{pool}' created")
    except Exception as e:
      err(f"Failed to create '{pool}': {e}")

""" -----------------------------{ Resolve wildcard patterns to VMIDs }----------------------------- """
def resolve_patterns(vm_map, patterns):
  matched_vmids = []
  for pattern in patterns:
    matches = [vm_map[name] for name in vm_map if fnmatch.fnmatch(name, pattern)]
    if not matches:
      warn(f"No matches for pattern: {pattern}")
    else:
      info(f"{pattern} -> {matches}")
      matched_vmids.extend(matches)
  return list(set(matched_vmids))

""" -----------------------------{ Add VMs to pool }----------------------------- """
def add_members(proxmox, pool_id, vmids):
  try:
    proxmox.pools(pool_id).put(vms=",".join(vmids))
    ok(f"Added VMIDs to pool '{pool_id}': {vmids}")
  except Exception as e:
    err(f"Failed adding members: {e}")
    sys.exit(1)

""" -----------------------------{ Main }----------------------------- """
def main():
  parser = argparse.ArgumentParser(description="Proxmox Pool Manager (Bulk + Wildcard + Colour-Coded)")
  parser.add_argument("--host", required=True)
  parser.add_argument("--user")
  parser.add_argument("--password")
  parser.add_argument("--token-name")
  parser.add_argument("--token-value")
  parser.add_argument("--create", nargs="+", metavar="POOL", help="Create one or more pools")
  parser.add_argument("--comment", help="Comment for created pools")
  parser.add_argument("--list", action="store_true", help="List all VMs/CTs")
  parser.add_argument("--match", nargs="+", metavar="PATTERN", help="Wildcard VM name patterns")
  parser.add_argument("--pool", help="Pool to assign matched VMs into")
  parser.add_argument("--dry-run", action="store_true", help="Dry-run (simulate creation)")

  args = parser.parse_args()
  proxmox = connect_proxmox(args)

  """ Create pools """
  if args.create:
    create_pools(proxmox, args.create, comment=args.comment, dry_run=args.dry_run)

  """ List VMs """
  vm_map = None
  if args.list or args.match:
    vm_map = list_vms(proxmox)

  """ Wildcard match + pool assignment """
  if args.match:
    if not args.pool:
      err("--pool is required when using --match")
      sys.exit(1)
    vmids = resolve_patterns(vm_map, args.match)
    if not vmids:
      info("No VMs matched.")
      sys.exit(0)
    print(f"\n{C.CYAN}Will add VMs to pool '{args.pool}': {C.RESET} {vmids}")
    confirm = input("Type 'yes' to proceed (default=no): ").strip()
    if confirm.lower() == "yes":
      add_members(proxmox, args.pool, vmids)
    else:
      warn("Cancelled wildcard pool assignment")

if __name__ == "__main__":
  main()