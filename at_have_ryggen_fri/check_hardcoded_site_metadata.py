#!/usr/bin/env python3
"""
check_hardcoded_site_metadata.py -- part of at_have_ryggen_fri.

Real bug, found live 2026-08-13: 4 of nodeinfo.yml's 9 real callers (salt,
rudder, tacticalrmm, meshcentral) sourced city/country/entity from static,
hand-typed host_vars (e.g. salt_site_city: "Edinburgh") instead of a live
sites.csv lookup like the other 5 (proxmox, truenas, firewallme,
linux/tools.yml, bind9-dns.yml) already did. Converting the 3 live ones
(salt/rudder/tacticalrmm) to a live lookup caught a real, live data bug in
all three: <role>_site_country was hardcoded "Scotland" -- wrong, sites.csv's
real Country value for CLD is "Global" (a virtual/cloud site, not physically
in Scotland). One of the three's own host_vars comment even claimed it had
been checked against sites.csv at the time it was written -- didn't stop it
drifting wrong regardless. Robert's own words, unambiguous: "everything is
supposed to use sites.csv... hard-coding stuff is very 1970s and verboten
here."

This check closes the gap generically: any host_vars/*/*.yml file that
defines a key matching <prefix>_site_(city|country|country_code|entity|
office_name|street|postal_code) is flagged -- these fields must always come
from a live sites.csv lookup at play time (hostname_facts.yml -> read_csv ->
selectattr('Site', 'equalto', ...) -- the pattern proxmox/truenas/firewallme/
linux/salt/rudder/tacticalrmm all now use), never hand-typed into host_vars,
where nothing can catch it drifting from the real data.

EXAMSHCLD001 is a deliberate, documented, narrow exception -- EXAMSHCLD001
was retired 2026-08-08 (TacticalRMM's bundled MeshCentral replaced it,
meshcentral_server.yml is dead code with no host to run it against), so its
leftover hand-typed block was never converted -- not worth the effort for a
host that will never run again. If EXAMSHCLD001/meshcentral_server.yml is
ever revived, convert it the same way the other 3 were and remove this
exception.

Exit code: 0 if no hand-typed site-metadata key is found outside the
EXAMSHCLD001 exception, 1 otherwise.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOST_VARS_DIR = REPO_ROOT / "ansible" / "configs" / "inventory" / "host_vars"

# EXAMSHCLD001 only -- see this file's own docstring for why.
EXCLUDED_HOSTS = {"EXAMSHCLD001"}

BANNED_SUFFIXES = (
    "city", "country", "country_code", "entity", "office_name", "street", "postal_code",
)
BANNED_KEY = re.compile(
    r"^\s*[a-z][a-z0-9_]*_site_(" + "|".join(BANNED_SUFFIXES) + r")\s*:"
)


def git_tracked_host_vars_files():
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--", "ansible/configs/inventory/host_vars/**/*.yml"],
        capture_output=True, text=True, timeout=30,
    ).stdout
    return [REPO_ROOT / line for line in out.splitlines() if line]


def main():
    checked = 0
    failures = []

    for path in git_tracked_host_vars_files():
        rel = path.relative_to(REPO_ROOT)
        host = rel.parts[4] if len(rel.parts) > 4 else ""
        if host in EXCLUDED_HOSTS:
            continue
        checked += 1
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            m = BANNED_KEY.match(line)
            if m:
                failures.append((rel, lineno, line.strip()))

    print(f"Checked {checked} host_vars file(s) (excluding {sorted(EXCLUDED_HOSTS)}) for "
          f"hand-typed site-metadata keys.")

    if failures:
        print(f"\n{len(failures)} hand-typed site-metadata key(s) found:")
        for rel, lineno, line in failures:
            print(f"  {rel}:{lineno}: {line}")
        print(
            "\nThese fields must come from a live sites.csv lookup at play time, not be "
            "hand-typed here -- see salt/rudder/tacticalrmm's own 00-preflight.yml/"
            "rudder_server.yml/tacticalrmm_server.yml for the established pattern "
            "(hostname_facts.yml -> read_csv -> selectattr). Hand-typed copies drift "
            "silently from the real data -- this exact class of bug was found live "
            "2026-08-13 (CLD's country hardcoded 'Scotland', really 'Global')."
        )
        return 1

    print("No hand-typed site-metadata keys found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
