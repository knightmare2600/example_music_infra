#!/usr/bin/env python3
"""
merge_ad_computers.py -- one-off write tool, benarbejde/, not part of at_have_ryggen_fri.

The actual merge that benarbejde/audit_ad_computers_drift.py's read-only report led to.
Run once, by hand, after Robert reviewed that report and gave explicit per-item direction
(2026-09-26 conversation) -- this is NOT meant to be re-run routinely the way
generate_inventory.py is. Re-running it is safe (idempotent -- see each step below) but its
job is done once devices.csv and ad_computers.json agree.

Confirmed decisions this script implements, each one Robert's own call, not assumed:

  1. MERGE, not replace -- every existing entry's Description/OS/OperatingSystemVersion stays
     exactly as-is unless explicitly listed below. The whole point was to not destroy the
     hand-authored flavour text devices.csv has no equivalent for.

  2. Every real devices.csv device gets an AD record -- "no operational gaps... seeing
     something means it's unambiguously known about." This includes Planned=yes rows
     (warehouse stock, not yet installed -- Robert: "we have a warehouse full of equipment...
     give the team a chance") -- these get Enabled: false and a "(Planned -- pending
     installation)" Description suffix, so they're visibly tracked without being mistaken for
     a live joined machine.

  3. The 38 DCR devices (Legacy=yes VMware VMs of old domain controllers, confirmed real by
     Robert, never Planned) go straight to the Decommissioned OU, not their normally-computed
     Servers placement -- they're retired, not active servers waiting to be found.

  4. Reuse the EXISTING OU=Computers,OU=Disabled OU for decommissioned devices -- already built
     into the schema for exactly this, no new OU needed (10-ad-schema.yml unchanged for this
     part).

  5. Three NEW global OUs (10-ad-schema.yml v1.4.0, 2026-09-26) for the orphans that don't fit
     anywhere else: Vending Machines, Field Equipment, Vintage IT -- one per category, global,
     since the affected devices span multiple sites and aren't site-local equipment.

  6. Per-orphan disposition, Robert's own explicit call per item (see ORPHAN_DISPOSITIONS
     below) -- not a rule this script infers, a literal list of decisions.

  7. EXAWKSMUN001: real data-entry typo, not a devices.csv/ad_computers.json disagreement --
     Site was "BON" (Bonn), hostname and the device's own IP (192.168.189.150, which is
     Munich's real subnet, 192.168.189.0/24 -- confirmed live before writing this, NOT Bonn's,
     192.168.228.0/24) both say Munich. Fixed directly, ahead of the general drift pass below,
     so that pass's own recompute uses the corrected Site.

  8. General placement drift (12 found, all confirmed) -- rather than hardcode all 12 by hand,
     this script recomputes ad_ou/ad_device_sub_ou for every EXISTING entry that matches a
     real devices.csv device, using the exact same TYPE_TO_SUB_OU mapping the audit already
     confirmed. Safe and comprehensive: only entries that actually differ get touched, and any
     future drift of this same shape self-corrects on a re-run instead of needing another
     hand-written list.

Usage:
  python3 benarbejde/merge_ad_computers.py            # writes benarbejde/ad_computers.json
  python3 benarbejde/merge_ad_computers.py --dry-run   # prints what would change, writes nothing
"""
import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BENARBEJDE = REPO_ROOT / "benarbejde"
SITES_CSV = BENARBEJDE / "sites.csv"
DEVICES_CSV = BENARBEJDE / "devices.csv"
ROLE_CODES_CSV = BENARBEJDE / "role_codes.csv"
AD_COMPUTERS_JSON = BENARBEJDE / "ad_computers.json"

sys.path.insert(0, str(BENARBEJDE))
from generate_inventory import build_hostname  # noqa: E402
from audit_ad_computers_drift import (  # noqa: E402
    TYPE_TO_SUB_OU,
    load_sites,
    load_role_names,
    load_ad_computers,
    base_dn,
    compute_ad_ou,
)

DECOMMISSIONED_OU = f"OU=Computers,OU=Disabled,{base_dn()}"

# Robert's own explicit per-item call, 2026-09-26 -- not inferred, a literal list of decisions.
# ("decommissioned", new_description_or_None) -- None means keep the entry's existing
# Description untouched (it's already good/accurate as-is).
# ("global_ou", ou_name) -- one of the 3 new top-level OUs.
# ("site_workstations", None) -- the entry's OWN Site field's normal Workstations sub-OU.
ORPHAN_DISPOSITIONS = {
    "EXARTRFAL002": ("decommissioned", None),
    "EXANIXBRD002": ("decommissioned", None),
    "EXAPBXFAL001": (
        "decommissioned",
        "Nortel PBX, 50 lines + music-on-hold expansion card -- retired in favour of "
        "an SBC talking to EXAPBXCLD001",
    ),
    "EXACVNDER001": ("global_ou", "Vending Machines"),
    "EXATEAAKL001": ("global_ou", "Vending Machines"),
    "EXAKONBER001": ("global_ou", "Field Equipment"),
    "EXAPHNBER001": ("global_ou", "Field Equipment"),
    "EXAPSIBER001": ("global_ou", "Field Equipment"),
    "EXATTYLAX001": ("global_ou", "Vintage IT"),
    "EXAWRKAAR001": ("site_workstations", None),
    "EXAWRKHEL001": ("site_workstations", None),
}

# Real data-entry typo, not a devices.csv disagreement -- see module docstring point 7.
SITE_CORRECTIONS = {
    "EXAWKSMUN001": {
        "Site": "MUN",
        "Description": "Hot desk workstation - Munich office",
    },
}

PLANNED_SUFFIX = " (Planned -- pending installation)"


def load_devices():
    with DEVICES_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compute_ip(row, sites):
    effective_site = (row.get("SubnetSite") or "").strip() or row["Site"].strip()
    host_octet = (row.get("HostOctet") or "").strip()
    if effective_site not in sites or not host_octet.isdigit():
        return ""
    subnet = sites[effective_site]["Subnet"].strip()
    prefix = subnet.split("/")[0].rsplit(".", 1)[0]
    return f"{prefix}.{host_octet}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="Print a summary, write nothing.")
    args = parser.parse_args()

    sites = load_sites()
    role_names = load_role_names()
    devices = load_devices()
    ad_computers = load_ad_computers()
    ad_by_name = {c["Name"].upper(): c for c in ad_computers}

    # --- Step 1: fix EXAWKSMUN001's Site/Description before anything else touches it ---
    for name, fields in SITE_CORRECTIONS.items():
        entry = ad_by_name.get(name)
        if entry:
            entry.update(fields)

    # --- Step 2: recompute ad_ou/ad_device_sub_ou drift for every existing entry that ---
    # --- matches a real (non-orphan, non-Planned) devices.csv device                  ---
    device_by_hostname = {}
    for row in devices:
        site_code = row["Site"].strip()
        dtype = row["Type"].strip()
        number_str = row["Number"].strip()
        if site_code not in sites or not number_str.isdigit():
            continue
        device_by_hostname[build_hostname(dtype, site_code, int(number_str)).upper()] = row

    drift_fixed = []
    for name, entry in ad_by_name.items():
        if name in ORPHAN_DISPOSITIONS:
            continue  # handled separately below, not by normal recompute
        row = device_by_hostname.get(name)
        if row is None:
            continue
        dtype = row["Type"].strip()
        if dtype == "DCR":
            continue  # DCR never gets normal placement, see Step 4
        sub_ou = TYPE_TO_SUB_OU.get(dtype)
        if sub_ou is None:
            continue
        computed_ou, err = compute_ad_ou(sites[entry["Site"].strip()], sub_ou)
        if err or computed_ou is None:
            continue
        if entry.get("ad_ou") != computed_ou or entry.get("ad_device_sub_ou") != sub_ou:
            drift_fixed.append((name, entry.get("ad_ou"), computed_ou))
            entry["ad_ou"] = computed_ou
            entry["ad_device_sub_ou"] = sub_ou

    # --- Step 3: apply Robert's explicit orphan dispositions ---
    orphans_applied = []
    for name, (disposition, extra) in ORPHAN_DISPOSITIONS.items():
        entry = ad_by_name.get(name)
        if entry is None:
            continue
        if disposition == "decommissioned":
            entry["ad_ou"] = DECOMMISSIONED_OU
            entry["ad_device_sub_ou"] = "Decommissioned"
            entry["Enabled"] = False
            if extra:
                entry["Description"] = extra
        elif disposition == "global_ou":
            entry["ad_ou"] = f"OU={extra},{base_dn()}"
            entry["ad_device_sub_ou"] = extra
        elif disposition == "site_workstations":
            site_code = entry["Site"].strip()
            computed_ou, err = compute_ad_ou(sites[site_code], "Workstations")
            if not err:
                entry["ad_ou"] = computed_ou
                entry["ad_device_sub_ou"] = "Workstations"
        orphans_applied.append(name)

    # --- Step 4: add every devices.csv device with no existing AD record ---
    added = []
    for row in devices:
        site_code = row["Site"].strip()
        dtype = row["Type"].strip()
        number_str = row["Number"].strip()
        if site_code not in sites or not number_str.isdigit():
            continue
        hostname = build_hostname(dtype, site_code, int(number_str))
        if hostname.upper() in ad_by_name:
            continue  # already has a record (existing entry, corrected above if needed)

        is_planned = row.get("Planned", "").strip().lower() == "yes"

        if dtype == "DCR":
            ad_ou = DECOMMISSIONED_OU
            sub_ou = "Decommissioned"
            enabled = False
        else:
            sub_ou = TYPE_TO_SUB_OU.get(dtype)
            if sub_ou is None:
                continue  # genuinely new Type since this script was written -- skip, don't guess
            computed_ou, err = compute_ad_ou(sites[site_code], sub_ou)
            if err:
                continue
            ad_ou = computed_ou
            enabled = not is_planned

        description = (row.get("Notes") or "").strip() or role_names.get(dtype, dtype)
        if is_planned:
            description = f"{description}{PLANNED_SUFFIX}"

        new_entry = {
            "Name": hostname,
            "SamAccountName": f"{hostname}$",
            "Role": dtype,
            "Site": site_code,
            "Description": description,
            "Enabled": enabled,
            "DNSHostName": f"{hostname}.jukebox.internal",
            "OS": (row.get("OS") or "").strip(),
            "OperatingSystemVersion": "",
            "IPv4Address": compute_ip(row, sites),
            "ad_ou": ad_ou,
            "ad_device_sub_ou": sub_ou,
        }
        ad_computers.append(new_entry)
        ad_by_name[hostname.upper()] = new_entry
        added.append(hostname)

    print(f"Site/Description corrections applied: {len(SITE_CORRECTIONS)}")
    print(f"Placement drift auto-corrected: {len(drift_fixed)}")
    for name, old, new in drift_fixed:
        print(f"  {name}: {old} -> {new}")
    print(f"Orphan dispositions applied: {len(orphans_applied)} ({', '.join(sorted(orphans_applied))})")
    print(f"New devices added: {len(added)} ({sum(1 for h in added if True)} total; "
          f"see --dry-run output above for the full per-Type breakdown if needed)")
    print(f"Total ad_computers.json entries: {len(ad_computers)} (was {len(ad_by_name) - len(added)})")

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    AD_COMPUTERS_JSON.write_text(
        json.dumps(ad_computers, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"\nWrote {AD_COMPUTERS_JSON.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
