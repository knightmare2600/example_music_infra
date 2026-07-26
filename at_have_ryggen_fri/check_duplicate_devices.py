#!/usr/bin/env python3
"""
check_duplicate_devices.py -- part of at_have_ryggen_fri.

Catches the EXAFWLVRK001/EXAWKSFAL001/EXALAPFAL001 bug class: a standard-slot
template line in generate_inventory.py's build_ini() and a real devices.csv
row both resolving to the same hostname, at two different IPs. Each
standard-slot role now has a skip-if-devices.csv-already-covers-it guard
(2026-07-21/22), but nothing previously checked that a future role addition,
or a future devices.csv edit, doesn't reintroduce this class of bug.

Also catches the inverse: the CLD/WAP-UFC bug class (found+fixed by hand,
2026-07-26, before it ever touched a committed file -- see
generate_inventory.py's own changelog) -- two DIFFERENT hostnames landing on
the SAME IP, e.g. a synthesized WAP1 placeholder DNS record colliding with a
real UFC device sitting on the same standard octet. This is exactly the class
that opens up every time a role joins DNS_SINGLE_ROLES/DNS_MULTI_ALL_INSTANCES/
DNS_MULTI_FIRST_INSTANCE_ONLY -- SUPPRESSED_STANDARD_ROLES has to be updated by
hand for each real collision, and nothing previously checked that it was.

This checks three independent surfaces:
  1. Every committed ansible/configs/inventory/<site>.ini -- both live and
     commented "# HOSTNAME  ansible_host=..." reference lines -- for the same
     hostname appearing twice with two different IPs.
  2. generate_inventory.py --emit-devices-json's merged output (what
     bind9-dns.yml's zone templates actually consume, via a Jinja `first`
     filter that silently swallows duplicates rather than erroring) for
     duplicate Hostname values with differing full_ip.
  3. The same --emit-devices-json output for duplicate full_ip values under
     different Hostnames -- i.e. the inverse collision. BRD/BER's deliberate
     shared-subnet overlap (ALLOWED_SITE_OVERLAP in generate_inventory.py) is
     the one legitimate case of this and is read directly from the generator
     itself, not re-guessed here, so it can't drift out of sync.

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


def load_devices_json(problems):
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "benarbejde/sites.csv",
         "--devices", "benarbejde/devices.csv", "--emit-devices-json"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        problems.append(f"--emit-devices-json failed: {result.stderr.strip()}")
        return None
    return json.loads(result.stdout)


def load_allowed_site_overlap(problems):
    result = subprocess.run(
        [sys.executable, "-c",
         "import sys, json; sys.path.insert(0, sys.argv[1]); import generate_inventory as gi; "
         "print(json.dumps(sorted(set(map(tuple, gi.ALLOWED_SITE_OVERLAP)))))",
         str(BENARBEJDE)],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        problems.append(f"could not read ALLOWED_SITE_OVERLAP from generate_inventory.py: "
                         f"{result.stderr.strip()}")
        return set()
    return {tuple(pair) for pair in json.loads(result.stdout)}


def check_devices_json_hostnames(problems, devices):
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


def check_devices_json_ips(problems, devices, allowed_site_overlap):
    by_ip = {}
    for dev in devices:
        ip, hostname, site = dev.get("full_ip"), dev.get("Hostname"), dev.get("Site")
        if not ip or not hostname:
            continue
        by_ip.setdefault(ip, []).append((hostname, site))

    for ip, entries in sorted(by_ip.items()):
        hostnames = {h for h, _ in entries}
        if len(hostnames) <= 1:
            continue  # same hostname repeated is fine -- that's just the same device
        sites = {s for _, s in entries}
        if len(sites) == 2 and tuple(sorted(sites)) in {tuple(sorted(p)) for p in allowed_site_overlap}:
            continue  # e.g. BRD/BER's deliberate shared subnet
        problems.append(
            f"--emit-devices-json: {ip} is assigned to {len(hostnames)} different hostnames "
            f"({', '.join(sorted(hostnames))}) -- a standard-slot synthesized placeholder and a "
            f"real devices.csv row (or two real rows) are landing on the same address; needs a "
            f"SUPPRESSED_STANDARD_ROLES entry (see CLD/WAP-UFC, 2026-07-26 in generate_inventory.py's "
            f"changelog) or, if this is a deliberate shared-subnet pair like BRD/BER, an "
            f"ALLOWED_SITE_OVERLAP entry"
        )


def main():
    problems = []
    check_ini_files(problems)

    devices = load_devices_json(problems)
    if devices is not None:
        check_devices_json_hostnames(problems, devices)
        allowed_site_overlap = load_allowed_site_overlap(problems)
        check_devices_json_ips(problems, devices, allowed_site_overlap)

    print(f"Checked {len(list(INVENTORY_DIR.glob('*.ini'))) - len(NOT_GENERATOR_OWNED)} "
          f"generated .ini files and --emit-devices-json output for duplicate hostname/IP "
          f"collisions (both directions).")

    if problems:
        print(f"\n{len(problems)} collision(s) found:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("No duplicate hostname/IP collisions found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
