#!/usr/bin/env python3
"""
suggest_free_ip.py -- advisory helper, not part of at_have_ryggen_fri.

Robert, 2026-08-06, after RMM/MSH's .13/.14 octets turned out to have been
picked by hand (scanning a generated .ini) with no discussion: "the harness
could, by virtue of knowing the subnets, 'find' some spaces and offer up a
suggestion... IPs 14, 69, 100-101 are free, please select one." This is that
tool -- given a site code, computes which octets in that site's subnet are
genuinely free, so a human picks the next device's IP from an actual list
instead of a hand grep of the generated inventory (or worse, a guess).

SUGGESTS ONLY -- never writes to any file. Adding the chosen row to
benarbejde/devices.csv (and picking which octet from the list to actually
use) stays a human decision every time -- see docs/adding-a-new-device.md for
the full workflow this feeds into.

Two sources combine to compute "occupied":
  1. benarbejde/devices.csv -- every real row whose EFFECTIVE subnet (its
     SubnetSite override if set, otherwise its own Site) matches the site
     asked about. A device hostnamed under one site but physically on
     another's subnet (SubnetSite, e.g. EXAPBXCLD002 on FRD's subnet) is
     correctly attributed to the subnet its HostOctet actually lives in, not
     the site its hostname implies -- see check_subnet_site_mismatch.py
     (check 27) for the same distinction.
  2. benarbejde/address_policy.csv -- every standard-slot octet (RTR .1, BMC
     .2-.4, DCS .10-.11, NAS .19, RDR .21, PVE .5-.7, SWI .250-.252, FWL
     .253-.254, WAP .82-.94, WKS .101, LAP .102, etc.) is reserved
     estate-wide regardless of whether THIS site currently has a device
     using it -- a site with no NAS yet still can't hand out .19 to
     something else, the slot is reserved for when it gets one.

Usage:
  python3 benarbejde/suggest_free_ip.py CLD
  python3 benarbejde/suggest_free_ip.py FAL --count 5 --low 60 --high 99

Exit code: 0 if the site was found and the subnet has at least one free
octet in range; 1 on an unknown site code or a fully-occupied range (both
genuine problems worth a non-zero exit, this is a real check-your-input
tool, not a harness pass/fail check).
"""
import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BENARBEJDE = REPO_ROOT / "benarbejde"
SITES_CSV = BENARBEJDE / "sites.csv"
DEVICES_CSV = BENARBEJDE / "devices.csv"
ADDRESS_POLICY_CSV = BENARBEJDE / "address_policy.csv"


def load_sites():
    with SITES_CSV.open(newline="", encoding="utf-8") as f:
        return {row["Site"].strip(): row for row in csv.DictReader(f)}


def load_reserved_octets():
    """Every octet address_policy.csv reserves estate-wide, regardless of site."""
    reserved = {}
    with ADDRESS_POLICY_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            octet = int(row["Octet"].strip())
            reserved.setdefault(octet, []).append(
                f"{row['Type'].strip()} ({row['Notes'].strip()})" if row.get("Notes", "").strip()
                else row["Type"].strip()
            )
    return reserved


def load_occupied_octets(site_code):
    """Real devices.csv rows whose effective subnet (SubnetSite or Site) is site_code."""
    occupied = {}
    with DEVICES_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            effective_site = (row.get("SubnetSite") or "").strip() or (row.get("Site") or "").strip()
            if effective_site != site_code:
                continue
            octet_str = (row.get("HostOctet") or "").strip()
            if not octet_str.isdigit():
                continue
            octet = int(octet_str)
            label = f"{row['Site']},{row['Type']},{row['Number']}"
            occupied.setdefault(octet, []).append(label)
    return occupied


def format_ranges(octets):
    """Compact ['.14', '.69', '.100-.101'] style formatting for a sorted list of free octets."""
    if not octets:
        return "(none)"
    ranges = []
    start = prev = octets[0]
    for o in octets[1:]:
        if o == prev + 1:
            prev = o
            continue
        ranges.append((start, prev))
        start = prev = o
    ranges.append((start, prev))
    return ", ".join(f".{a}" if a == b else f".{a}-.{b}" for a, b in ranges)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("site", help="Site code, e.g. CLD, FAL")
    parser.add_argument("--count", type=int, default=10,
                         help="How many free octets to highlight as suggestions (default: 10)")
    parser.add_argument("--low", type=int, default=2, help="Low end of range to scan (default: 2)")
    parser.add_argument("--high", type=int, default=254, help="High end of range to scan (default: 254)")
    args = parser.parse_args()

    sites = load_sites()
    site_code = args.site.strip().upper()
    if site_code not in sites:
        print(f"ERROR: site '{site_code}' not found in {SITES_CSV.relative_to(REPO_ROOT)}.")
        print(f"Known site codes: {', '.join(sorted(sites))}")
        return 1

    subnet = sites[site_code]["Subnet"].strip()
    prefix = subnet.split("/")[0].rsplit(".", 1)[0]

    reserved = load_reserved_octets()
    occupied = load_occupied_octets(site_code)

    print(f"Site {site_code}: subnet {subnet} ({prefix}.x)\n")

    if occupied:
        print(f"Occupied by a real device ({len(occupied)} octet(s)):")
        for o in sorted(occupied):
            print(f"  {prefix}.{o:<3}  {', '.join(occupied[o])}")
        print()

    print(f"Reserved estate-wide by address_policy.csv ({len(reserved)} octet(s), "
          f"whether or not {site_code} has one yet): "
          + ", ".join(f".{o}" for o in sorted(reserved)))
    print()

    all_used = set(occupied) | set(reserved)
    free = [o for o in range(args.low, args.high + 1) if o not in all_used]

    if not free:
        print(f"No free octets in .{args.low}-.{args.high} -- widen the range with --low/--high.")
        return 1

    print(f"{len(free)} free octet(s) in .{args.low}-.{args.high}: {format_ranges(free)}\n")

    suggestions = free[:args.count]
    print(f"Suggested (first {len(suggestions)}): "
          + ", ".join(f"{prefix}.{o}" for o in suggestions))
    print()
    print("Advisory only -- nothing here writes to any file. Confirm the choice with Robert, "
          "then add the row to benarbejde/devices.csv yourself. See "
          "docs/adding-a-new-device.md for the full workflow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
