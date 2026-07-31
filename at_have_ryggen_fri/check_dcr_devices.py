#!/usr/bin/env python3
"""
check_dcr_devices.py -- part of at_have_ryggen_fri.

Found live 2026-07-31: EXADCREDI002/EXADCREDI003 and EXADCRTOR028 (Type=DCR,
"Domain controller (legacy naming)" in role_codes.csv) were showing up on
EDI's and TOR's *new-network* topology diagrams -- Robert: "legacy devices
have seeped into the new diagrams which isn't supposed to happen, we are
deploying new hypervisors, new DCS new SBCs etc." Fixed by adding DCR to
generate_network_diagrams.py's TOPOLOGY_EXCLUDE_TYPES -- but that made DCR
rows invisible everywhere instead: no diagram, no dedicated report, nothing
short of reading devices.csv by hand. Robert's follow-up ask: "add a check
to the harness to catch DCR and alert if found" -- the same "explicit
visibility beats silent omission" principle behind check 27
(check_subnet_site_mismatch.py) and the NAS/RDR/BMC/WAP synthesis policy.

role_codes.csv's own DCR row claims "devices.csv rows using DCR are typos
and treated as DCS" -- that was never actually implemented anywhere in this
repo, and every real DCR row found so far describes genuinely legacy/broken/
pending-decommission hardware, not a mistyped current DC. This check doesn't
try to guess which case a new DCR row is -- it just makes sure a human sees
it, every run, rather than it staying invisible now that the topology
diagram excludes it.

Exit code: always 0. Purely informational -- a DCR row isn't necessarily
wrong (it may be legitimately awaiting decommission), just something that
needs a human's eyes: either fix devices.csv's Type to DCS if it's actually
current, or note it for cleanup if it's confirmed legacy/dead.
"""
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEVICES_CSV = REPO_ROOT / "benarbejde" / "devices.csv"
BENARBEJDE = REPO_ROOT / "benarbejde"

sys.path.insert(0, str(BENARBEJDE))
import generate_inventory as gi  # noqa: E402  -- build_hostname(), not a second copy of the convention


def main():
    rows = list(csv.DictReader(DEVICES_CSV.open(newline="", encoding="utf-8")))

    dcr_rows = [r for r in rows if (r.get("Type") or "").strip().upper() == "DCR"]

    print(f"Checked {len(rows)} devices.csv row(s) for Type=DCR (legacy-naming domain "
          f"controllers, excluded from topology diagrams).")

    if dcr_rows:
        print(f"\n{len(dcr_rows)} DCR device(s) found -- informational, these are hidden from "
              f"every topology diagram (generate_network_diagrams.py's TOPOLOGY_EXCLUDE_TYPES) "
              f"and need a human decision, not just silence:")
        for r in dcr_rows:
            try:
                hostname = gi.build_hostname("DCR", r["Site"].strip(), int(r["Number"]))
            except (KeyError, ValueError):
                hostname = f"DCR #{r.get('Number', '?')}"
            notes = (r.get("Notes") or "").strip()
            notes_short = notes[:90] + ("..." if len(notes) > 90 else "")
            print(f"  - {hostname} ({r['Site']}){': ' + notes_short if notes_short else ''}")
        print("\nFor each: either correct devices.csv's Type to DCS if this is genuinely a "
              "current domain controller (a real typo), or leave as DCR with a clear Notes "
              "entry if it's confirmed legacy/pending decommission.")
    else:
        print("No DCR devices found.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
