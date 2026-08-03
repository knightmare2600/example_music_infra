#!/usr/bin/env python3
"""
check_legacy_devices.py -- part of at_have_ryggen_fri.

benarbejde/legacy-devices.csv (added 2026-08-03) holds old-network-only core
infrastructure that has no live/current counterpart -- RAC/iLO/iDRAC
out-of-band management, ESXi hypervisor hosts, vCenter -- transcribed from
the 33 real Old Network diagram sections in docs/network-diagram/*.md. It
deliberately does NOT feed generate_inventory.py or any generated .ini:
nothing in it is live, managed, or DNS-resolvable.

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
     recurring.

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
ALLOWED_TYPES = {"RAC", "ESX", "VCT"}


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
        if hostname in live_hostnames:
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
