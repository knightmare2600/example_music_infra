#!/usr/bin/env python3
"""
check_duplicate_devices.py -- part of at_have_ryggen_fri.

Catches the EXAFWLVRK001/EXAWKSFAL001/EXALAPFAL001 bug class: a standard-slot
template line in generate_inventory.py's build_ini() and a real devices.csv
row both resolving to the same hostname, at two different IPs. Each
standard-slot role now has a skip-if-devices.csv-already-covers-it guard
(2026-07-21/22), but nothing previously checked that a future role addition,
or a future devices.csv edit, doesn't reintroduce this class of bug.

This checks two independent surfaces:
  1. Every committed ansible/configs/inventory/<site>.ini -- both live and
     commented "# HOSTNAME  ansible_host=..." reference lines -- for the same
     hostname appearing twice with two different IPs.
  2. generate_inventory.py --emit-devices-json's merged output (what
     bind9-dns.yml's zone templates actually consume, via a Jinja `first`
     filter that silently swallows duplicates rather than erroring) for
     duplicate Hostname values with differing full_ip.

Exit code: 0 if no duplicate hostname/IP collisions found, 1 otherwise.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"
GENERATOR = BENARBEJDE / "generate_inventory.py"
INVENTORY_DIR = REPO_ROOT / "ansible" / "configs" / "inventory"

NOT_GENERATOR_OWNED = {"main.ini", "rudder.ini", "salt.ini"}

HOST_LINE_RE = re.compile(r"^#?\s*(?P<hostname>EXA[A-Z0-9]+)\s+ansible_host=(?P<ip>[0-9.]+)")


def check_ini_files(problems):
    for ini_path in sorted(INVENTORY_DIR.glob("*.ini")):
        if ini_path.name in NOT_GENERATOR_OWNED:
            continue
        seen = {}
        for line in ini_path.read_text().splitlines():
            m = HOST_LINE_RE.match(line.strip())
            if not m:
                continue
            hostname, ip = m.group("hostname"), m.group("ip")
            if hostname in seen and seen[hostname] != ip:
                problems.append(
                    f"{ini_path.relative_to(REPO_ROOT)}: {hostname} appears with two different "
                    f"IPs ({seen[hostname]} and {ip}) -- a standard-slot template line and a real "
                    f"devices.csv row are colliding on the same hostname"
                )
            seen.setdefault(hostname, ip)


def check_devices_json(problems):
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "benarbejde/sites.csv",
         "--devices", "benarbejde/devices.csv", "--emit-devices-json"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        problems.append(f"--emit-devices-json failed: {result.stderr.strip()}")
        return

    devices = json.loads(result.stdout)
    seen = {}
    for dev in devices:
        hostname, ip = dev.get("Hostname"), dev.get("full_ip")
        if not hostname or not ip:
            continue
        if hostname in seen and seen[hostname] != ip:
            problems.append(
                f"--emit-devices-json: {hostname} appears with two different IPs "
                f"({seen[hostname]} and {ip}) -- bind9-dns.yml's zone templates use a Jinja "
                f"`first` filter here, so this would silently pick one and drop the other, "
                f"not error"
            )
        seen.setdefault(hostname, ip)


def main():
    problems = []
    check_ini_files(problems)
    check_devices_json(problems)

    print(f"Checked {len(list(INVENTORY_DIR.glob('*.ini'))) - len(NOT_GENERATOR_OWNED)} "
          f"generated .ini files and --emit-devices-json output for duplicate hostname/IP "
          f"collisions.")

    if problems:
        print(f"\n{len(problems)} collision(s) found:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("No duplicate hostname/IP collisions found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
