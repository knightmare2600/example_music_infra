#!/usr/bin/env python3
"""
check_new_site_boilerplate.py -- part of at_have_ryggen_fri.

Robert, 2026-09-24, on PHI/DET (both real sites.csv entries with zero real
equipment anywhere): "the harness needs to look for and identify new sites
which do not have any devices... you know the IPs, the subnets, the other
stuff, so can build a diagram, even if it's not feature filled out yet."

A "new" site here means genuinely zero rows in devices.csv AND zero records
in ad_computers.json for that Site -- not "missing one device type" (that's
check_ad_data_integrity.py's own, much narrower, job). For each one found,
prints the full day-one boilerplate equipment list with real, computed
hostnames and IPs -- everything a brand-new standard site is now confirmed
to get (see benarbejde/standard_site_boilerplate.json for the underlying
rules, all confirmed live with Robert the same evening):

  - RTR (.1, FortiGate), FWL (.253, vendor TBD per site)
  - SWI (.250, 96-port)
  - WAP (.82), SBC (.48), RDR (.21, badge reader), NAS (.19)
  - Two PVE nodes + their BMCs: server 1 is always HP/ILO (.5 / .3),
    server 2 is always Dell/RAC (.6 / .4) -- .2 is deliberately skipped,
    reserved for a second/legacy RTR (see README.md's Addressing section)
  - DCS (.10)

Deliberately excludes WKS/LAP (headcount-driven, not site-driven) and
CLD/VRK/FRD (each architecturally special -- see
standard_site_boilerplate.json's own excluded_sites_notes).

This is an ADVISORY only -- it never fails the harness (always exits 0).
It doesn't create any file or record; it's a "here's what to build" report,
the same non-committal shape as check_ad_data_integrity.py's own
check_pve_inference_advisory.
"""
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"
sys.path.insert(0, str(BENARBEJDE))
import generate_inventory as gi  # noqa: E402


def load_sites(problems):
    sites = {}
    try:
        with (BENARBEJDE / "sites.csv").open(newline="") as f:
            for row in csv.reader(f):
                if not row or not row[0].strip():
                    continue
                site = row[0].strip()
                subnet = row[8].strip()
                base = ".".join(subnet.split("/")[0].split(".")[:3])
                sites[site] = base
    except Exception as e:
        problems.append(f"sites.csv: could not load -- {e}")
    return sites


def load_devices_sites(problems):
    sites = set()
    try:
        with (BENARBEJDE / "devices.csv").open(newline="") as f:
            for row in csv.DictReader(f):
                site = (row.get("Site") or "").strip()
                if site:
                    sites.add(site)
    except Exception as e:
        problems.append(f"devices.csv: could not load -- {e}")
    return sites


def load_ad_computers_sites(problems):
    sites = set()
    try:
        computers = json.loads((BENARBEJDE / "ad_computers.json").read_text())
        for c in computers:
            site = (c.get("Site") or "").strip()
            if site:
                sites.add(site)
    except Exception as e:
        problems.append(f"ad_computers.json: could not load -- {e}")
    return sites


def load_boilerplate(problems):
    try:
        return json.loads((BENARBEJDE / "standard_site_boilerplate.json").read_text())
    except Exception as e:
        problems.append(f"standard_site_boilerplate.json: could not load -- {e}")
        return None


def build_boilerplate_list(site, base, boilerplate):
    """Real hostname + IP for every day-one device a brand-new standard site
    gets, using address_policy.csv's own octets (via generate_inventory.py's
    already-loaded OFFSETS_SINGLE/ROLE_OFFSETS) plus this file's vendor
    conventions for anything address_policy.csv doesn't specify."""
    lines = []
    vendors = boilerplate.get("vendor_defaults", {})

    def add(role, number, octet, vendor=None, note=""):
        hostname = gi.build_hostname(role, site, number)
        vendor_str = f" ({vendor})" if vendor else ""
        note_str = f" -- {note}" if note else ""
        lines.append(f"    {hostname}  {base}.{octet}{vendor_str}{note_str}")

    add("RTR", 1, gi.OFFSETS_SINGLE.get("RTR", 1), vendors.get("RTR"))
    add("FWL", 1, gi.ROLE_OFFSETS.get("FWL", [253])[0], note="vendor varies per site, no default")
    add("SWI", 1, gi.ROLE_OFFSETS.get("SWI", [250])[0], vendors.get("SWI"), "96-port")
    add("WAP", 1, gi.ROLE_OFFSETS.get("WAP", [82])[0], vendors.get("WAP"))
    add("SBC", 1, gi.OFFSETS_SINGLE.get("SBC", 48), vendors.get("SBC"))
    add("RDR", 1, gi.OFFSETS_SINGLE.get("RDR", 21), vendors.get("RDR"), "badge reader")
    add("NAS", 1, gi.OFFSETS_SINGLE.get("NAS", 19), vendors.get("NAS"))

    pve_conv = boilerplate.get("pve_convention", {})
    pve_octets = gi.ROLE_OFFSETS.get("PVE", [5, 6])
    bmc_octets = gi.ROLE_OFFSETS.get("BMC", [2, 3, 4])
    # .2 deliberately skipped -- reserved for a second/legacy RTR (README.md Addressing)
    usable_bmc_octets = [o for o in bmc_octets if o != 2]
    for i, (num_str, conv) in enumerate(sorted(pve_conv.items())):
        num = int(num_str)
        pve_octet = pve_octets[num - 1] if num - 1 < len(pve_octets) else "?"
        bmc_octet = usable_bmc_octets[i] if i < len(usable_bmc_octets) else "?"
        add("PVE", num, pve_octet, conv.get("vendor"))
        add(conv.get("bmc_type", "BMC"), num, bmc_octet, note=f"BMC for PVE{num}")

    add("DCS", 1, gi.OFFSETS_SINGLE.get("DCS") or (gi.ROLE_OFFSETS.get("DCS", [10])[0]))

    return lines


def main():
    problems = []

    sites = load_sites(problems)
    devices_sites = load_devices_sites(problems)
    ad_sites = load_ad_computers_sites(problems)
    boilerplate = load_boilerplate(problems)

    if problems:
        print("\n".join(problems))
        return 0

    gi.load_address_policy(BENARBEJDE / "address_policy.csv")

    excluded = set(boilerplate.get("excluded_sites", []))
    new_sites = sorted(
        s for s in sites
        if s not in excluded and s not in devices_sites and s not in ad_sites
    )

    print(
        f"Checked {len(sites)} site(s) in sites.csv against devices.csv/ad_computers.json "
        f"for zero real equipment anywhere ({len(excluded)} architecturally-special site(s) "
        f"excluded: {', '.join(sorted(excluded))})."
    )

    if not new_sites:
        print("No genuinely new (zero-equipment) sites found.")
        return 0

    print(
        f"\n{len(new_sites)} new site(s) found with zero real equipment -- "
        f"day-one boilerplate for each (ADVISORY, not a failure):"
    )
    for site in new_sites:
        base = sites[site]
        print(f"\n  {site} ({base}.0/24):")
        for line in build_boilerplate_list(site, base, boilerplate):
            print(line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
