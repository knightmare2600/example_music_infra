#!/usr/bin/env python3
"""
export_people_csv.py -- one-off write tool, benarbejde/, not part of at_have_ryggen_fri.

Produces benarbejde/people.csv and benarbejde/groups.csv from the CURRENT
benarbejde/ad_users.json/ad_groups.json -- not from benarbejde/jukebox.example.tdf or
parse_tdf.py. Run once, by hand, to backfill the new hand-authored source for
merge_ad_users.py (Robert's ask, 2026-10-18: replace parse_tdf.py's users/groups
functionality without consulting the .tdf file; "we don't use the tdf file as input").

Why the JSON and not the .tdf: parse_tdf.py's own header already documents that
ad_users.json/ad_groups.json have genuinely diverged from what the .tdf would produce
(7 users added directly to the JSON, never round-tripped; this script also independently
found 20 more UPN/Email authoring mismatches and 43 group Email mismatches that don't
mechanically derive from the record's own Name -- see below). The JSON files are the
real, current, already-correct data; the .tdf is not.

Column design, verified empirically against all 369/158 real records before being
trusted (never assumed):
  - UserPrincipalName/Email (people) and Email (groups) are AUTHORED columns, not
    derived at generation time. 20/369 users' UPN local-part doesn't match
    SamAccountName (e.g. kpatterson -> kevin.patterson@, manid -> mani@, two people
    sharing builders@) and 43/158 groups' Email local-part doesn't match a slug of
    Name (e.g. "The Proclaimers" -> proclaimers@, "Rocazino" -> alphabeat@, a historic
    stage-name alias). A mechanical derivation would have silently got these wrong.
  - people.csv's Site column (a real benarbejde/sites.csv code) replaces the old
    Continent/Country/Province/City positional OU array entirely -- every one of 369
    users' existing ad_ou reverse-parses to a city that matches exactly one sites.csv
    row, and that row's own Country matches the OU-derived country in all 369 cases.
    This mirrors how computers already derive their OU from Role+Site via sites.csv
    (merge_ad_computers.py/_computer_ou_path) -- same source of truth, same pattern.
  - people.csv's own City/Country/CountryCode columns are the separate PERSONAL
    mailing-address fields (telephoneNumber's locale, physicalDeliveryOfficeName's
    city, etc.) -- NOT the same as the Site's own city. These diverge in 75/369 real
    cases (e.g. Bruce Springsteen: personal City "Asbury Park", but Site NJC/Camden
    for AD placement purposes) -- remote/relocated-but-still-grouped-under-a-site
    people. Collapsing these into one column would have silently lost real data.

Usage:
  python3 benarbejde/export_people_csv.py            # writes people.csv + groups.csv
  python3 benarbejde/export_people_csv.py --dry-run   # prints what would be written
"""
import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"

PEOPLE_FIELDS = [
    "Name", "SamAccountName", "UserPrincipalName", "Email", "Site", "Band",
    "Title", "Department", "Company", "Description", "Manager",
    "Phone", "Mobile", "Street", "City", "PostalCode", "Office",
    "Country", "CountryCode",
    "Disabled", "Locked", "MustChangePassword", "Groups",
]

GROUP_FIELDS = ["Name", "SamAccountName", "Description", "Type", "Scope", "ManagedBy", "Email", "Site", "NonMusicGroup"]


def load_domain():
    forest = json.loads((BENARBEJDE / "ad_forest.json").read_text())
    return forest["domain_fqdn"]


def load_sites_by_city():
    with open(BENARBEJDE / "sites.csv", newline="", encoding="utf-8") as f:
        return {row["City"]: row for row in csv.DictReader(f)}


def reverse_ou_to_site(ad_ou, band, domain, sites_by_city):
    """Reverse an ad_ou DN back to a sites.csv Site code, via the OU-placement city.

    The DN's fixed shape (see parse_tdf.py's _user_ou_path, which this mirrors in
    reverse): [OU=band?] OU=Users [OU=city?] [OU=province?] [OU=country?] [OU=continent?]
    OU=Sites DC=... -- 'Users' is the one unconditional anchor token, always right
    after band (or first if no band), which makes popping the known trailing
    continent/country tokens and reading whatever's left between 'Users' and them
    unambiguous. Returns '' if ad_ou is empty or the city doesn't match any real site
    (the latter never observed in practice -- see this script's own header).
    """
    if not ad_ou:
        return ""

    dn_parts = [p.split("=", 1)[1] for p in ad_ou.split(",")]
    # Strip the fixed 'Sites', domain-DC... tail.
    domain_parts = domain.split(".")
    tail_len = 1 + len(domain_parts)  # 'Sites' + one DC token per domain label
    middle = dn_parts[:-tail_len]

    if not middle:
        return ""
    middle.pop()  # continent -- always present, not needed (we get it back via sites.csv)

    if middle:
        middle.pop()  # country -- omitted only for the 'Global' country case, not
                       # observed in any real record; if ever hit, city_ou below is
                       # wrong and this function returns '' via the no-site-match path.
    if band:
        if not middle or middle[0] != band:
            return ""
        middle = middle[1:]
    if not middle or middle[0] != "Users":
        return ""
    middle = middle[1:]

    if not middle:
        return ""
    city_ou = middle[0]
    site = sites_by_city.get(city_ou)
    return site["Site"] if site else ""


def export_people(users, domain, sites_by_city, dry_run):
    rows = []
    unmatched = []
    for r in users:
        site_code = reverse_ou_to_site(r.get("ad_ou", ""), r.get("ad_band_ou_name", ""), domain, sites_by_city)
        if r.get("ad_ou") and not site_code:
            unmatched.append(r["Name"])
        rows.append({
            "Name": r.get("Name", ""),
            "SamAccountName": r.get("SamAccountName", ""),
            "UserPrincipalName": r.get("UserPrincipalName", ""),
            "Email": r.get("Email", ""),
            "Site": site_code,
            "Band": r.get("ad_band_ou_name", ""),
            "Title": r.get("Title", ""),
            "Department": r.get("Department", ""),
            "Company": r.get("Company", ""),
            "Description": r.get("Description", ""),
            "Manager": r.get("Manager", ""),
            "Phone": r.get("telephoneNumber", ""),
            "Mobile": r.get("mobile", ""),
            "Street": r.get("Street", ""),
            "City": r.get("City", ""),
            "PostalCode": r.get("PostalCode", ""),
            "Office": r.get("physicalDeliveryOfficeName", ""),
            "Country": r.get("Country", ""),
            "CountryCode": r.get("CountryCode", ""),
            "Disabled": r.get("Disabled", False),
            "Locked": r.get("Locked", False),
            "MustChangePassword": r.get("MustChangePassword", False),
            "Groups": ";".join(r.get("Groups", [])),
        })

    if unmatched:
        print(f"WARNING: {len(unmatched)} user(s) had an ad_ou but no matching sites.csv "
              f"city -- Site column left blank, needs manual fixup: {unmatched}", file=sys.stderr)

    if dry_run:
        print(f"Would write {len(rows)} rows to benarbejde/people.csv")
        return

    out = BENARBEJDE / "people.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PEOPLE_FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out}", file=sys.stderr)


def export_groups(groups, dry_run):
    rows = [{
        "Name": r.get("Name", ""),
        "SamAccountName": r.get("SamAccountName", ""),
        "Description": r.get("Description", ""),
        "Type": r.get("Type", ""),
        "Scope": r.get("Scope", ""),
        "ManagedBy": r.get("ManagedBy", ""),
        "Email": r.get("Email", ""),
        "Site": r.get("Site", ""),
        "NonMusicGroup": r.get("NonMusicGroup", False),
    } for r in groups]

    if dry_run:
        print(f"Would write {len(rows)} rows to benarbejde/groups.csv")
        return

    out = BENARBEJDE / "groups.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=GROUP_FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    domain = load_domain()
    sites_by_city = load_sites_by_city()
    users = json.loads((BENARBEJDE / "ad_users.json").read_text())
    groups = json.loads((BENARBEJDE / "ad_groups.json").read_text())

    export_people(users, domain, sites_by_city, args.dry_run)
    export_groups(groups, args.dry_run)


if __name__ == "__main__":
    main()
