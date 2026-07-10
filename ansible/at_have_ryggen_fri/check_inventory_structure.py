#!/usr/bin/env python3
"""
check_inventory_structure.py -- part of at_have_ryggen_fri.

Runs `ansible-inventory --list` against the REAL configs/inventory (no
connection to any host is made -- this is pure inventory+group_vars
resolution) and asserts the two things that were silently broken earlier
this project and must never regress silently again:

  1. The windows_dc -> windows_server -> windows -> windows_nodes group
     chain exists and actually contains the expected DC for a spread of
     real sites (not just the 3 that were hand-curated before the
     2026-07-09 inventory consolidation).
  2. group_vars actually resolves for a real, currently-loaded host in
     each of those groups -- becomes/connection settings that are only
     correct if group_vars/host_vars are being picked up from INSIDE the
     loaded -i path (see ansible/README.md's "group_vars/host_vars
     location" section). Specifically:
       - A Windows host must NEVER have ansible_become set (Windows has
         no sudo; a stray ansible_become=true here previously broke
         production connectivity).
       - A host in the linux group (via [linux:children]) must have
         ansible_become: true, ansible_become_method: sudo.
       - group_vars/all/colours.yml's `_c` dict must resolve for both.

Exit code: 0 if every assertion holds, 1 otherwise.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORY = REPO_ROOT / "ansible" / "configs" / "inventory"

# Real hosts to spot-check -- deliberately spans sites both inside and
# outside the original 3 hand-curated .ini files (cld/fal/liv), since the
# whole point of the 2026-07-09 consolidation was that every site should
# now have the same group structure, not just those three.
WINDOWS_DC_HOSTS = ["EXADCSCLD001", "EXADCSFAL001", "EXADCSLIV001", "EXADCSTOR001"]
LINUX_HOST = "192.168.69.9"  # EXAANSCLD001 -- [ansiblehosts] in main.ini uses bare-IP inventory_hostnames


def ansible_inventory_list():
    result = subprocess.run(
        ["ansible-inventory", "-i", str(INVENTORY), "--list"],
        capture_output=True, text=True, cwd=REPO_ROOT / "ansible",
    )
    if result.returncode != 0:
        print("ansible-inventory --list failed:")
        print(result.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def ansible_inventory_host(hostname):
    result = subprocess.run(
        ["ansible-inventory", "-i", str(INVENTORY), "--host", hostname],
        capture_output=True, text=True, cwd=REPO_ROOT / "ansible",
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def group_hosts(inv, group):
    return set((inv.get(group) or {}).get("hosts") or [])


def group_children(inv, group):
    return set((inv.get(group) or {}).get("children") or [])


def main():
    failures = []
    inv = ansible_inventory_list()

    # --- 1. group hierarchy ---------------------------------------------
    if "windows_dc" not in group_children(inv, "windows_server"):
        failures.append("windows_server does not have windows_dc as a child group")
    if "windows_server" not in group_children(inv, "windows"):
        failures.append("windows does not have windows_server as a child group")
    if "windows" not in group_children(inv, "windows_nodes"):
        failures.append("windows_nodes does not have windows as a child group")

    dc_hosts = group_hosts(inv, "windows_dc")
    for host in WINDOWS_DC_HOSTS:
        if host not in dc_hosts:
            failures.append(f"{host} expected in windows_dc group, not found "
                             f"(inventory has {len(dc_hosts)} windows_dc hosts total)")

    # --- 2. group_vars actually resolves for real hosts -----------------
    for host in WINDOWS_DC_HOSTS[:1] + [LINUX_HOST]:
        hv = ansible_inventory_host(host)
        if hv is None:
            failures.append(f"ansible-inventory --host {host} failed -- host not in inventory?")
            continue
        if "_c" not in hv or "G" not in hv.get("_c", {}):
            failures.append(f"{host}: group_vars/all/colours.yml's _c dict did not resolve "
                             f"-- group_vars/all/ is not being picked up for this host")

    win_host = WINDOWS_DC_HOSTS[0]
    hv = ansible_inventory_host(win_host)
    if hv is not None and hv.get("ansible_become"):
        failures.append(f"{win_host} (Windows) has ansible_become set -- "
                         f"this must NEVER happen, Windows has no sudo")

    hv = ansible_inventory_host(LINUX_HOST)
    if hv is not None:
        if hv.get("ansible_become") is not True:
            failures.append(f"{LINUX_HOST} (linux group): ansible_become did not resolve to "
                             f"true -- group_vars/linux/main.yml is not being picked up")
        if hv.get("ansible_become_method") != "sudo":
            failures.append(f"{LINUX_HOST}: ansible_become_method did not resolve to 'sudo'")

    # --- report -----------------------------------------------------------
    print(f"Checked windows_dc/windows_server/windows/windows_nodes hierarchy "
          f"and group_vars resolution against {INVENTORY.relative_to(REPO_ROOT)}")
    if failures:
        print(f"\n{len(failures)} FAILURE(s):")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("All inventory structure and group_vars assertions passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
