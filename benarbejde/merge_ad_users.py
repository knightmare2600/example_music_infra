#!/usr/bin/env python3
"""
merge_ad_users.py -- benarbejde/, replaces parse_tdf.py's --section users/groups.

Regenerates benarbejde/ad_users.json and benarbejde/ad_groups.json from
benarbejde/people.csv and benarbejde/groups.csv -- the new hand-authored source of
truth for people/band data, added 2026-10-18 (Robert's ask: parse_tdf.py and
jukebox.example.tdf are retired; people.csv/groups.csv replace them, backfilled from
the already-correct ad_users.json/ad_groups.json via export_people_csv.py, never from
the .tdf). Mirrors merge_ad_computers.py's relationship to devices.csv: a CSV Robert
edits by hand for every new person/band, one script that turns it into the real JSON
Ansible/windows_adschema reads.

Unlike merge_ad_computers.py, this is a full regenerate, not a merge-preserving-extras
-- people.csv/groups.csv's columns are a complete 1:1 backing for every field in the
JSON output (verified against all 369/158 real records when the CSVs were first
exported), so there's nothing left over to preserve.

OU derivation (ad_ou/ad_band_ou_name/ad_band_parent) is driven by people.csv's own
Site column -- a benarbejde/sites.csv code, exactly like a computer's Role+Site already
drives its OU via merge_ad_computers.py. No separate Continent/Country/Province/City
columns for OU placement; sites.csv is the one source for that geography, same as
everywhere else in this repo.

Usage:
  python3 benarbejde/merge_ad_users.py             # writes ad_users.json + ad_groups.json
  python3 benarbejde/merge_ad_users.py --dry-run   # prints counts, writes nothing
"""
import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"

_BOOL = {"true": True, "false": False, "": False}


def _bool(s):
    return _BOOL.get((s or "").strip().lower(), False)


def load_domain():
    return json.loads((BENARBEJDE / "ad_forest.json").read_text())["domain_fqdn"]


def load_sites():
    with open(BENARBEJDE / "sites.csv", newline="", encoding="utf-8") as f:
        return {row["Site"]: row for row in csv.DictReader(f)}


# Same convention CONTINENT_MAP/REGION_CONTINENT served in parse_tdf.py -- sites.csv's
# own AnsibleRegion is the real source now, same field merge_ad_computers.py already
# reads for the identical purpose.
REGION_CONTINENT = {
    "uk_site": "Europe", "de_site": "Europe", "dk_site": "Europe", "eu_site": "Europe",
    "lb_site": "Middle East", "us_site": "North America", "ca_site": "North America",
    "apac_site": "Asia Pacific", "cloud_site": "Cloud Infrastructure",
}


def build_ou(site_row, band, base_dn):
    city = site_row["City"]
    province = site_row.get("Province", "")
    country = site_row["Country"]
    continent = REGION_CONTINENT.get(site_row.get("AnsibleRegion", ""), "Europe")

    parts = []
    if band:
        parts.append(f"OU={band}")
    parts.append("OU=Users")
    parts.append(f"OU={city}")
    if province:
        parts.append(f"OU={province}")
    parts.append(f"OU={country}")
    parts.append(f"OU={continent}")
    parts.append("OU=Sites")
    parts.append(base_dn)

    ad_ou = ",".join(parts)
    ad_band_parent = ",".join(parts[1:]) if band else ""
    return ad_ou, ad_band_parent


def build_users(domain, sites_by_code):
    base_dn = "DC=" + ",DC=".join(domain.split("."))
    with open(BENARBEJDE / "people.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    results = []
    problems = []
    for row in rows:
        name = row["Name"]
        site_code = row.get("Site", "")
        band = row.get("Band", "")

        ad_ou = ad_band_parent = ""
        if site_code:
            site_row = sites_by_code.get(site_code)
            if not site_row:
                problems.append(f"{name}: Site '{site_code}' not found in sites.csv")
            else:
                ad_ou, ad_band_parent = build_ou(site_row, band, base_dn)
        elif band:
            problems.append(f"{name}: has Band '{band}' but no Site -- cannot place in OU")

        results.append({
            "Name": name,
            "SamAccountName": row["SamAccountName"],
            "UserPrincipalName": row["UserPrincipalName"],
            "Groups": [g for g in row.get("Groups", "").split(";") if g],
            "Title": row.get("Title", ""),
            "Email": row.get("Email", ""),
            "Country": row.get("Country", ""),
            "CountryCode": row.get("CountryCode", ""),
            "Manager": row.get("Manager", ""),
            "Disabled": _bool(row.get("Disabled")),
            "Locked": _bool(row.get("Locked")),
            "MustChangePassword": _bool(row.get("MustChangePassword")),
            "Department": row.get("Department", ""),
            "Company": row.get("Company", ""),
            "Description": row.get("Description", ""),
            "telephoneNumber": row.get("Phone", ""),
            "mobile": row.get("Mobile", ""),
            "Street": row.get("Street", ""),
            "City": row.get("City", ""),
            "PostalCode": row.get("PostalCode", ""),
            "physicalDeliveryOfficeName": row.get("Office", ""),
            "ad_ou": ad_ou,
            "ad_band_ou_name": band,
            "ad_band_parent": ad_band_parent,
        })

    return results, problems


def build_groups():
    """SamAccountName/NonMusicGroup are sparse in the real data (2 and 3 groups out of
    158 respectively) and were entirely ABSENT as keys on every other record, not just
    empty/false -- included here only when the CSV cell is actually non-blank, to match
    that shape exactly rather than padding every group with two new always-present
    fields nothing else expects."""
    with open(BENARBEJDE / "groups.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    results = []
    for row in rows:
        g = {
            "Name": row["Name"],
            "Description": row.get("Description", ""),
            "Type": row.get("Type", "") or "Security",
            "Scope": row.get("Scope", "") or "Global",
            "ManagedBy": row.get("ManagedBy", ""),
            "Email": row.get("Email", ""),
        }
        if row.get("Site"):
            g["Site"] = row["Site"]
        if row.get("SamAccountName"):
            g["SamAccountName"] = row["SamAccountName"]
        if _bool(row.get("NonMusicGroup")):
            g["NonMusicGroup"] = True
        results.append(g)
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    domain = load_domain()
    sites_by_code = load_sites()

    users, problems = build_users(domain, sites_by_code)
    groups = build_groups()

    if problems:
        print(f"{len(problems)} PROBLEM(S):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)

    if args.dry_run:
        print(f"Would write {len(users)} users to ad_users.json, {len(groups)} groups to ad_groups.json")
        return 1 if problems else 0

    with open(BENARBEJDE / "ad_users.json", "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(BENARBEJDE / "ad_groups.json", "w", encoding="utf-8") as f:
        json.dump(groups, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(users)} users to ad_users.json, {len(groups)} groups to ad_groups.json", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
