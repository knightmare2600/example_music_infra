#!/usr/bin/env python3
"""
check_criticality_alarm.py -- part of at_have_ryggen_fri.

THE CRITICALITY ALARM. Named after a nuclear plant's own criticality alarm
(Robert, 2026-09-24) -- deliberately not styled like this harness's other 43
checks. Every other check here reports a bug in derived/generated data
against its one real source of truth. This one exists for a rarer, more
serious situation: two files this repo BOTH treats as a real source of
truth -- today, benarbejde/devices.csv and benarbejde/ad_computers.json --
turn out to disagree about which real, physical device owns a given
hostname. When that happens, nothing downstream of either file can be
trusted until a human resolves which one is actually right. That is not an
ordinary bug to fix and move on from -- it is a "we don't actually know the
truth right now" situation, and the harness has no business quietly
continuing to check 40+ other things against data that might be wrong at
the root.

So, unlike every other check: THIS ONE RUNS FIRST, and if it fires, run.sh
prints the alarm and exits immediately -- no other section runs at all.
See run.sh's own top-of-file changelog for exactly where this is wired in.

Concrete trigger case (found live, 2026-09-24, auditing the vending-machine
estate): benarbejde/devices.csv has a real row, PER,VND,1, which computes to
hostname EXAVNDPER001. benarbejde/ad_computers.json has NO record under that
name at all -- but it DOES have a record named EXACVNDER001 (the "Scone
Palace vending machine") whose own DNSHostName field says
"EXAVNDPER001.jukebox.internal". Robert confirmed live: EXACVNDER001 and
whatever devices.csv's PER,VND,1 row describes ARE genuinely two different
real devices (his own call, 2026-07-14, recorded as an inline comment on
that exact devices.csv row) -- so "EXAVNDPER001" is a hostname that TWO
different real devices' data both implicate, and nothing before this check
ever surfaced that as a problem.

Checks:
  A. Hostname ownership conflict -- for every real devices.csv hostname H,
     no ad_computers.json record may have DNSHostName == H unless that
     record's OWN SamAccountName-derived hostname also equals H. A
     different record claiming (via DNSHostName) to BE a real device that
     devices.csv says is something else is exactly the PER shape above.

  B. Missing-counterpart detection is deliberately NOT implemented yet.
     Robert's original ask covers "missing data" too (a real devices.csv
     row with no ad_computers.json record at all, and vice versa), but
     unlike check A there is no clean, low-false-positive way to know
     which devices.csv Types are EXPECTED to have an ad_computers.json
     counterpart and which genuinely never do (pure Linux control-plane
     infrastructure -- ANS/DNS/RUD/ZAB/SLT/RMM/PVE control planes -- is
     never modelled in ad_computers.json at all, on purpose, and a naive
     "every real row needs a record" check would alarm on all of that
     immediately). Given this check hard-stops the entire harness the
     moment it fires, shipping a scope that's likely to cry wolf on its
     first real run is worse than not having it yet. Flagged here,
     explicitly, for Robert to scope before it's added.

Exit code: 1 if any conflict found, 0 otherwise. (See run.sh: this exit
code causes an immediate script exit, not just a FAILED_CHECKS entry.)
"""
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"
sys.path.insert(0, str(BENARBEJDE))
import generate_inventory as gi  # noqa: E402 -- load_devices()/build_hostname(), not a second copy


def load_real_hostnames(problems):
    """Every real devices.csv hostname -> the (Site, Type, Number) that produced it,
    for a useful error message. Same load_devices() this whole repo's generation
    already trusts, not a second, hand-rolled derivation."""
    try:
        gi.load_address_policy(BENARBEJDE / "address_policy.csv")
        devices_by_site, _ = gi.load_devices(BENARBEJDE / "devices.csv")
    except Exception as e:
        problems.append(f"devices.csv: could not load -- {e}")
        return {}
    real = {}
    for site, devs in devices_by_site.items():
        for d in devs:
            real[d["hostname"]] = (site, d["type"])
    return real


def load_ad_computers(problems):
    path = BENARBEJDE / "ad_computers.json"
    try:
        return json.loads(path.read_text())
    except Exception as e:
        problems.append(f"ad_computers.json: could not load/parse -- {e}")
        return None


def check_hostname_ownership_conflict(problems, computers, real_hostnames):
    for c in computers:
        own_sam = (c.get("SamAccountName") or "").rstrip("$")
        dns = (c.get("DNSHostName") or "").split(".")[0]
        if not own_sam or not dns or dns == own_sam:
            continue
        if dns in real_hostnames:
            site, dtype = real_hostnames[dns]
            problems.append(
                f"'{dns}' is a real devices.csv hostname ({site}, Type={dtype}), but "
                f"ad_computers.json's '{own_sam}' record claims it via its own DNSHostName "
                f"field ('{c.get('DNSHostName')}') -- devices.csv and ad_computers.json "
                f"disagree about which real device '{dns}' actually is. This needs a human "
                f"decision, not an automated fix: is '{own_sam}' the same physical device as "
                f"'{dns}' (in which case DNSHostName is simply wrong and should say "
                f"'{own_sam}.jukebox.internal'), or are they genuinely two different real "
                f"devices (in which case '{own_sam}'s DNSHostName needs its OWN real "
                f"hostname, not '{dns}''s)?"
            )


def main():
    problems = []
    real_hostnames = load_real_hostnames(problems)
    computers = load_ad_computers(problems)

    if computers is not None and real_hostnames:
        check_hostname_ownership_conflict(problems, computers, real_hostnames)

    print(
        f"Checked {len(computers or [])} ad_computers.json record(s) against "
        f"{len(real_hostnames)} real devices.csv hostname(s) for cross-file ownership "
        f"conflicts."
    )

    if problems:
        print(f"\n{len(problems)} CRITICALITY ALARM(S):")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("No source-of-truth conflicts found between devices.csv and ad_computers.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
