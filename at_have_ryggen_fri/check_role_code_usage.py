#!/usr/bin/env python3
"""
check_role_code_usage.py -- part of at_have_ryggen_fri.

Found live 2026-08-05/06 (Robert, building EXARMMCLD001/onboarding
EXAPVEVRK001): create-vm.py printed "Unknown role code" for RMM against a
live PVE node. Root cause turned out to be a stale deployed copy of
/etc/example-music/role_codes.csv on that one host (linux/tools.yml hadn't
been re-run) -- role_codes.csv itself was already correct in the repo. But
that live incident exposed a real, separate gap: nothing in this harness
ever checks that benarbejde/devices.csv's own Type column only uses Code
values that actually exist in benarbejde/role_codes.csv. Every existing
check_role_codes.py (check 20) cross-references role_codes.csv against
docs/emojis/README.md's legend -- a different pair entirely. If a devices.csv
row were ever committed with a typo'd or since-renamed Type, nothing would
catch it until someone hit "Unknown role code" live, the exact thing that
just happened. Robert: "the harness needs checks that check the CSV files to
see if any new codes have appeared, or any are missing from it."

legacy-devices.csv is NOT in scope here -- check_legacy_devices.py (check 30)
already enforces its own separate, deliberately small ALLOWED_TYPES allowlist
(RAC/ESX/VCT/RTR), which is not meant to track role_codes.csv 1:1 (legacy
device classes generally have no current role code at all).

bootstrap/web/proxmox/devices.csv and role_codes.csv are NOT re-checked here
-- check_generated_freshness.py (check 6) already guarantees they're
byte-identical mirrors of the benarbejde/ originals, so checking the
canonical copy is sufficient.

Checks:
  1. Every Type value used in benarbejde/devices.csv has a matching Code row
     in benarbejde/role_codes.csv. HARD FAIL -- this is the exact "Unknown
     role code" bug class, a real typo'd/missing Type silently breaks
     create-vm.py and any other Type->role_codes.csv lookup the moment it's
     hit live.
  2. Every Code in benarbejde/role_codes.csv that is never used by any
     devices.csv row -- informational only, never fails by default. A code
     can legitimately exist ahead of any device using it yet (e.g. RRY,
     "planned/future role, listed for when it appears" per its own Notes) --
     this is visibility, not a bug to gate on, same principle as check 27/29.
     --strict fails on it, matching check 28's own pattern, for anyone who
     wants to be prompted to prune truly dead codes.

Exit code: 1 if check 1 finds anything (always), or if check 2 finds
anything AND --strict was passed. 0 otherwise.
"""
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"
ROLE_CODES_CSV = BENARBEJDE / "role_codes.csv"
DEVICES_CSV = BENARBEJDE / "devices.csv"


def load_role_codes():
    with ROLE_CODES_CSV.open(newline="", encoding="utf-8") as f:
        return {row["Code"].strip() for row in csv.DictReader(f) if row.get("Code", "").strip()}


def load_device_types():
    """Returns {Type: [ (Site, Number) uses ]} so failures can name every real row, not just the code."""
    uses = {}
    with DEVICES_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rtype = (row.get("Type") or "").strip()
            site = (row.get("Site") or "").strip()
            number = (row.get("Number") or "").strip()
            if not rtype:
                continue
            uses.setdefault(rtype, []).append(f"{site},{rtype},{number}")
    return uses


def main():
    strict = "--strict" in sys.argv

    if not ROLE_CODES_CSV.is_file():
        print(f"ERROR: {ROLE_CODES_CSV} not found.")
        return 1
    if not DEVICES_CSV.is_file():
        print(f"ERROR: {DEVICES_CSV} not found.")
        return 1

    role_codes = load_role_codes()
    device_types = load_device_types()

    print(f"Checked {len(device_types)} distinct Type value(s) used across "
          f"benarbejde/devices.csv against {len(role_codes)} Code(s) in "
          f"benarbejde/role_codes.csv.")

    failed = False

    unknown_types = sorted(set(device_types) - role_codes)
    if unknown_types:
        failed = True
        print(f"\n{len(unknown_types)} devices.csv Type(s) with no matching "
              f"role_codes.csv Code:")
        for t in unknown_types:
            rows = device_types[t]
            print(f"  - {t}: used by {len(rows)} row(s) -- {', '.join(rows)}")
        print("\n  Either the Type is a typo (fix the devices.csv row(s) above), or "
              "it's a genuinely new role that needs adding to benarbejde/role_codes.csv "
              "first -- see docs/network-diagram.md and check_role_codes.py (check 20) "
              "for what a new role_codes.csv row needs (Code/Name/Category/"
              "ConnectionMethod/Emoji/DNSAlias/Notes).")

    unused_codes = sorted(role_codes - set(device_types))
    if unused_codes:
        msg = (f"\n{len(unused_codes)} role_codes.csv Code(s) never used by any "
               f"devices.csv row: {', '.join(unused_codes)}")
        if strict:
            failed = True
            print(msg)
            print("  Failing because --strict was passed. This is expected for "
                  "genuinely planned/future roles (check each Code's own Notes "
                  "column) -- re-run without --strict if that's the case here.")
        else:
            print(msg)
            print("  Informational only -- a code can legitimately exist ahead of any "
                  "device using it yet (check each Code's own Notes column). "
                  "Re-run with --strict to fail on this.")

    if failed:
        return 1

    print("\nEvery devices.csv Type has a matching role_codes.csv Code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
