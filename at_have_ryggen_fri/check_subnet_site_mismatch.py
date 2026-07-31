#!/usr/bin/env python3
"""
check_subnet_site_mismatch.py -- part of at_have_ryggen_fri.

Found live 2026-07-30, during the CLD topology diagram work: EXAPBXCLD002 is
hostnamed under CLD but its real IP sits on FRD Havn's own 172.16.124.0/24
subnet (a `SubnetSite` override in devices.csv, documented rationale from the
2026-07-11 Pulsant DC/FRD Havn rework) -- a real, deliberate, correct pattern,
but nothing in the harness or any check output ever surfaced it. Robert:
"these little things keep tripping you up... known source of truth...
192.168.124 sure as hell isn't 192.168.69 is it?"

This is purely informational -- SubnetSite existing and differing from Site
is a legitimate, intentional pattern (a device physically located somewhere
other than where its hostname says), not a bug to gate on. The point is
visibility: every "hostname says X, real subnet says Y" case should show up
in check output by default, not only be findable by reading devices.csv's
own comment column by hand.

Exit code: always 0. Prints the list (possibly empty) for the harness
summary; never fails the run.
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

    mismatches = []
    for r in rows:
        subnet_site = (r.get("SubnetSite") or "").strip()
        site = (r.get("Site") or "").strip()
        if subnet_site and subnet_site != site:
            mismatches.append(r)

    print(f"Checked {len(rows)} devices.csv row(s) for SubnetSite overrides differing from Site.")

    if mismatches:
        print(f"\n{len(mismatches)} device(s) hostnamed under one site but physically on another "
              f"(SubnetSite override) -- informational, confirm each is deliberate:")
        for r in mismatches:
            try:
                hostname = gi.build_hostname(r["Type"].strip(), r["Site"].strip(), int(r["Number"]))
            except (KeyError, ValueError):
                hostname = f"{r.get('Type', '?')} #{r.get('Number', '?')}"
            notes = (r.get("Notes") or "").strip()
            notes_short = notes[:80] + ("..." if len(notes) > 80 else "")
            print(f"  - {hostname} hostnamed under {r['Site']}, real subnet is {r['SubnetSite']}"
                  f"{': ' + notes_short if notes_short else ''}")
    else:
        print("No SubnetSite overrides found.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
