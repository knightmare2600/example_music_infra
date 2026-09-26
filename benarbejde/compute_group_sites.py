#!/usr/bin/env python3
"""
compute_group_sites.py -- one-off/re-runnable write tool, benarbejde/.

Robert, 2026-09-26: "in the security groups, can we not do what we do in the
other OUs and have them by location... instead of just 'IT Groups > Security
Groups > 100s of groups' in a mess?"

ad_groups.json has no location field at all -- a group's real-world site has
to be inferred from where its actual members are (ad_users.json's own
ad_ou), which is itself only meaningful for a genuinely single-city group. A
band whose members are scattered across many cities (Bassists, VPN-Users,
Sales, ...) has no single home and must stay in the central OU regardless.

This script only ever ADDS/UPDATES the "Site" field (a real 3-letter site
code, matching devices.csv/ad_computers.json's own convention -- NOT a bare
city name, since ad_groups.json should use the same identifier everything
else in this estate does) for groups it can determine UNAMBIGUOUSLY:
exactly one real member, or every real member at the same single city.

Deliberately conservative in three ways:
  1. Never touches a group that already has an explicit "Site" field --
     preserves Robert's own manual overrides for the 6 genuinely two-city
     bands (Split Enz, TV-2, The Proclaimers, Then Jerico, Ultravox, Tina
     Turner -- Private Dancer), each hand-assigned to a specific city rather
     than left to whichever one this script's own inference would have
     picked. NEVER_STORE_SITE below covers those explicitly, alongside
     the confirmed-cross-cutting groups and the 3 groups going to the new
     Non-Music OU instead of a real site.
  2. Never guesses for a genuinely multi-city or zero-member group -- those
     stay exactly as they are (no Site field), which 20-ad-groups.yml
     correctly treats as "stays in the central Security Groups OU."
  3. Resolves group membership the same way 30-ad-users.yml's own
     _group_add_todo does -- checking a user's Groups: entries against BOTH
     a group's Name and its (if set) real SamAccountName, not Name alone.
     Confirmed live, 2026-09-26: an earlier, simpler version of this exact
     check (Name only) produced a false "zero members" for Nena/Falco, both
     of which DO have real members referencing them by their real
     SamAccountName (Nena-Grp/Falco-Grp) rather than their bare Name.

Usage:
  python3 benarbejde/compute_group_sites.py            # writes ad_groups.json
  python3 benarbejde/compute_group_sites.py --dry-run   # prints what would change
"""
import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BENARBEJDE = REPO_ROOT / "benarbejde"
SITES_CSV = BENARBEJDE / "sites.csv"
AD_USERS_JSON = BENARBEJDE / "ad_users.json"
AD_GROUPS_JSON = BENARBEJDE / "ad_groups.json"

# Groups this script must never assign a Site to, even if membership happens
# to look single-city -- Robert's own explicit, hand-made calls (2026-09-26
# conversation), not something to silently recompute later:
#   - The 6 two-city bands: Robert picked one specific city per band, which
#     doesn't match "which city has more/any members" (several are 1-1
#     splits) -- these are set directly by this script's own
#     MANUAL_SITE_OVERRIDES below, not inferred.
#   - Broadcasters/2FA Users/Disabled Users: going to the new Non-Music OU
#     instead of a real site -- see MANUAL_NON_MUSIC_GROUPS below.
MANUAL_SITE_OVERRIDES = {
    "Split Enz": "MEL",
    "TV-2": "AAR",
    "The Proclaimers": "EDI",
    "Then Jerico": "LND",
    "Ultravox": "VIE",
    "Tina Turner – Private Dancer": "LAX",
}

MANUAL_NON_MUSIC_GROUPS = {"Broadcasters", "2FA Users", "Disabled Users"}


def load_city_to_site():
    city_to_site = {}
    with SITES_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            city_to_site[row["City"]] = row["Site"]
    return city_to_site


def load_group_membership():
    """{group Name (lower): set(of member cities)} -- checks a user's Groups:
    entries against both a group's Name and its own SamAccountName, matching
    30-ad-users.yml's own real membership-resolution semantics."""
    groups = json.loads(AD_GROUPS_JSON.read_text(encoding="utf-8"))
    users = json.loads(AD_USERS_JSON.read_text(encoding="utf-8"))

    # alias (lowercase) -> real group Name -- a group matches on EITHER its
    # own Name or its SamAccountName (if distinct), same as ad_users.json's
    # Groups: entries are actually resolved live.
    alias_to_name = {}
    for g in groups:
        alias_to_name[g["Name"].lower()] = g["Name"]
        sam = g.get("SamAccountName")
        if sam and sam.lower() != g["Name"].lower():
            alias_to_name[sam.lower()] = g["Name"]

    membership = defaultdict(set)
    for u in users:
        m = re.search(r"OU=Users,(.+)$", u.get("ad_ou", ""))
        if not m:
            continue
        city = m.group(1).split(",")[0].replace("OU=", "")
        for g_ref in u.get("Groups", []):
            real_name = alias_to_name.get(g_ref.lower())
            if real_name:
                membership[real_name].add(city)

    return groups, membership


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    city_to_site = load_city_to_site()
    groups, membership = load_group_membership()

    updated = []
    skipped_already_set = []
    skipped_multi_or_zero = []
    non_music_applied = []
    manual_applied = []

    for g in groups:
        name = g["Name"]

        if name in MANUAL_NON_MUSIC_GROUPS:
            if not g.get("NonMusicGroup"):
                g["NonMusicGroup"] = True
                non_music_applied.append(name)
            continue

        if "Site" in g:
            skipped_already_set.append(name)
            continue

        if name in MANUAL_SITE_OVERRIDES:
            g["Site"] = MANUAL_SITE_OVERRIDES[name]
            manual_applied.append((name, g["Site"]))
            continue

        cities = membership.get(name, set())
        if len(cities) != 1:
            skipped_multi_or_zero.append((name, sorted(cities)))
            continue

        city = next(iter(cities))
        site_code = city_to_site.get(city)
        if not site_code:
            skipped_multi_or_zero.append((name, [f"{city} (no matching sites.csv row)"]))
            continue

        g["Site"] = site_code
        updated.append((name, site_code))

    print(f"Newly assigned Site (single-city, inferred): {len(updated)}")
    print(f"Manually assigned Site (two-city override): {len(manual_applied)}")
    for n, s in manual_applied:
        print(f"  {n} -> {s}")
    print(f"Assigned NonMusicGroup: {len(non_music_applied)} ({', '.join(non_music_applied)})")
    print(f"Already had a Site (untouched): {len(skipped_already_set)}")
    print(f"Left alone (multi-city or zero-member, stays central): {len(skipped_multi_or_zero)}")

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    AD_GROUPS_JSON.write_text(
        json.dumps(groups, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"\nWrote {AD_GROUPS_JSON.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
