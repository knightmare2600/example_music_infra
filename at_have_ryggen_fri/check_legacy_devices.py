#!/usr/bin/env python3
"""
check_legacy_devices.py -- part of at_have_ryggen_fri.

benarbejde/legacy-devices.csv (added 2026-08-03) holds old-network-only core
infrastructure that has no live/current counterpart -- RAC/iLO/iDRAC
out-of-band management, ESXi hypervisor hosts, vCenter -- transcribed from
the 33 real Old Network diagram sections in docs/network-diagram/*.md. It
deliberately does NOT feed generate_inventory.py or any generated .ini:
nothing in it is live, managed, or DNS-resolvable.

RTR joined the allowed Types 2026-08-04 for one confirmed exception: FAL's
old Cisco ISR 4331 was decommissioned and its real historical hostname
(EXARTRFAL001) was subsequently reused by the *different* physical
FortiGate that replaced it (now devices.csv's own FAL,RTR,1 row) -- a
genuine hostname-reuse case, not the usual RTR continuity every other site
has (where the same physical device just changed IP old->new).

This file exists as a direct consequence of the EXAFWLFAL001 mess found
2026-08-03: a hand-built Old Network diagram invented a fictional device
under a hostname that turned out to collide with a real, live, current
device of the same name. legacy-devices.csv separates "device that used to
exist and nothing wears its name today" from devices.csv's "device that's
live right now" -- but that separation is only as good as this check
proving no row here ever computes a hostname that devices.csv/the generated
inventory also uses.

Checks:
  1. Required columns present (Site, Type, Number, HostOctet, OS, Notes,
     SubnetSite).
  2. Every Site code exists in sites.csv.
  3. No duplicate (Site, Type, Number) within legacy-devices.csv itself.
  4. Every row's Type is one of the types this file is actually for (RAC,
     ESX, VCT) -- anything else belongs in devices.csv instead, since it
     implies the device class has (or could have) a live counterpart.
  5. No row's computed hostname (EXA<Type><Site><Number:03d>) collides with
     a hostname the live generated inventory (--emit-devices-json) actually
     uses -- the specific bug class this file exists to prevent from
     recurring -- except the narrow, explicitly-confirmed cases in
     ALLOWED_HOSTNAME_REUSE below (a real historical hostname genuinely
     reused by a different physical device after the original was
     decommissioned, not a fictional-device collision).

Exit code: 1 if any check fails, 0 otherwise.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"
LEGACY_CSV = BENARBEJDE / "legacy-devices.csv"
SITES_CSV = BENARBEJDE / "sites.csv"
GENERATOR = BENARBEJDE / "generate_inventory.py"

REQUIRED_COLUMNS = {"Site", "Type", "Number", "HostOctet", "OS", "Notes", "SubnetSite"}
# RAC/ESX/VCT never have a live counterpart at all. RTR added 2026-08-04 for FAL specifically --
# a genuine hostname-reuse exception (EXARTRFAL001 was the old decommissioned Cisco's real
# historical name, then reused by the *different* physical FortiGate that replaced it) rather
# than the usual RTR continuity every other site has. Not a general invitation for RTR/SWI/etc.
# rows here -- those still belong in devices.csv's own Legacy=yes rows wherever the physical
# device genuinely persisted old->new.
ALLOWED_TYPES = {"RAC", "ESX", "VCT", "RTR"}

# Confirmed real, intentional hostname reuse -- NOT a fictional-device-collides-with-real-device
# bug. FAL's old Cisco ISR 4331 (EXARTRFAL001, decommissioned) had its real historical hostname
# reused by the different physical FortiGate that replaced it as FAL's live router (devices.csv
# FAL,RTR,1 -- shows up in --emit-devices-json as the generic "Standard RTR slot" synthesis, since
# the FortiGate's own devices.csv row sits at the same octet and gets excluded by
# generate_inventory.py's STANDARD_OFFSETS dedup the same as every other site's real RTR row).
# Robert confirmed this directly, 2026-08-04 -- add a new (Site, Type, Number) tuple here only for
# an equally explicitly-confirmed case, never to silence a check result without that confirmation.
ALLOWED_HOSTNAME_REUSE = {("FAL", "RTR", 1)}


def load_site_codes():
    with SITES_CSV.open(newline="", encoding="utf-8") as f:
        return {row[0].strip() for row in csv.reader(f) if row and row[0].strip()}


def load_live_hostnames(problems):
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "benarbejde/sites.csv",
         "--devices", "benarbejde/devices.csv", "--emit-devices-json"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        problems.append(f"--emit-devices-json failed: {result.stderr.strip()}")
        return set()
    devices = json.loads(result.stdout)
    return {d["Hostname"] for d in devices if d.get("Hostname")}


def main():
    problems = []

    if not LEGACY_CSV.exists():
        print(f"{LEGACY_CSV.relative_to(REPO_ROOT)} does not exist.")
        return 1

    rows = list(csv.DictReader(LEGACY_CSV.open(newline="", encoding="utf-8")))

    if rows and not REQUIRED_COLUMNS.issubset(rows[0].keys()):
        missing = REQUIRED_COLUMNS - set(rows[0].keys())
        problems.append(f"missing required column(s): {', '.join(sorted(missing))}")
        print(f"Checked {LEGACY_CSV.relative_to(REPO_ROOT)}: structural failure, "
              f"skipping row-level checks.")
        for p in problems:
            print(f"  - {p}")
        return 1

    site_codes = load_site_codes()
    seen_keys = {}
    for r in rows:
        site = (r.get("Site") or "").strip()
        rtype = (r.get("Type") or "").strip()
        number = (r.get("Number") or "").strip()

        if site not in site_codes:
            problems.append(f"{site},{rtype},{number}: Site '{site}' not found in sites.csv")

        if rtype not in ALLOWED_TYPES:
            problems.append(
                f"{site},{rtype},{number}: Type '{rtype}' not in {sorted(ALLOWED_TYPES)} -- "
                f"legacy-devices.csv is only for old-network-only device classes with no live "
                f"counterpart; a new Type here usually means it belongs in devices.csv instead"
            )

        key = (site, rtype, number)
        if key in seen_keys:
            problems.append(f"{site},{rtype},{number}: duplicate row (also seen for "
                             f"{seen_keys[key]})")
        seen_keys[key] = r.get("OS", "")

    live_hostnames = load_live_hostnames(problems)
    for r in rows:
        site = (r.get("Site") or "").strip()
        rtype = (r.get("Type") or "").strip()
        number = (r.get("Number") or "").strip()
        if not (site and rtype and number.isdigit()):
            continue
        hostname = f"EXA{rtype}{site}{int(number):03d}"
        if hostname in live_hostnames and (site, rtype, int(number)) not in ALLOWED_HOSTNAME_REUSE:
            problems.append(
                f"{hostname}: collides with a real, live hostname in the generated inventory -- "
                f"this is exactly the EXAFWLFAL001 bug class legacy-devices.csv exists to prevent; "
                f"either this row is wrong (the old device was actually something else) or the "
                f"live device needs renaming"
            )

    print(f"Checked {len(rows)} legacy-devices.csv row(s) against sites.csv and the live "
          f"generated inventory ({len(live_hostnames)} hostnames).")

    if problems:
        print(f"\n{len(problems)} problem(s) found:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("No structural problems, duplicate rows, or live-hostname collisions found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
