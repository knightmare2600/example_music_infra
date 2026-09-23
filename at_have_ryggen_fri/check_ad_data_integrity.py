#!/usr/bin/env python3
"""
check_ad_data_integrity.py -- part of at_have_ryggen_fri.

benarbejde/ad_users.json, ad_groups.json, and ad_computers.json are all
documented as the "known source of truth" for windows_adschema's AD builds --
but nothing previously checked their own internal consistency. Found live,
2026-09-23, during one evening's populate_ad debugging: four distinct,
genuinely-live-breaking data bugs, each caught only by a real AD run failing
in a different way, not by any check beforehand:

  1. Two AD groups (Nena, Falco) had no explicit SamAccountName, so
     microsoft.ad.group defaulted it to their Name -- colliding
     case-insensitively with an existing user's own SamAccountName
     (SamAccountName must be unique across ALL security principals, not just
     within one object class). New-ADUser failed: "The specified group
     already exists".
  2. After giving those two groups an explicit SamAccountName override,
     8 ad_users.json Groups: [...] references still said the group's Name
     ("Nena"/"Falco") instead of its real SamAccountName ("Nena-Grp"/
     "Falco-Grp") -- microsoft.ad.user's groups: add: resolves identity by
     SamAccountName (via Get-ADObject -LDAPFilter "(sAMAccountName=...)"),
     not Name, so this silently re-resolved to the wrong object (a user, not
     the group) and failed trying to set a group-only attribute on it.
  3. ad_computers.json had two SamAccountName collisions: EXASWIEDI002 was a
     straight typo of EXASWIEDI001's SamAccountName (New-ADComputer failed:
     "The specified account already exists"), and EXASWICLY001 was
     genuinely reused across two different physical devices (a Cisco
     Catalyst and a TPLink switch) that both needed their own identity.
  4. Sydney/Melbourne's 29 computer records had an ad_ou missing the
     Province OU level (sites.csv lists a Province for both, same as
     Ontario/Quebec/US states) that ad_users.json's own records for the
     same two sites already had correctly -- New-ADComputer failed:
     "Directory object not found" for every single one.

This checks four independent surfaces, all from the files themselves, no AD
connection required:
  A. Duplicate SamAccountName within ad_users.json, and within
     ad_computers.json, case-insensitively (catches bug class 3's typo
     shape and bug class 3's genuine-reuse shape alike -- both need a human
     decision on which record is which, but this makes them visible instead
     of a live AD failure being the first sign).
  B. Case-insensitive SamAccountName collision between any ad_groups.json
     group and any ad_users.json user (catches bug class 1 before it ever
     reaches New-ADUser).
  C. Every ad_users.json Groups: [...] entry resolves, case-insensitively,
     to a real ad_groups.json group's SamAccountName (defaulting to Name
     when a group has no explicit SamAccountName override) -- catches bug
     class 2, including the exact "used the Name instead of the override"
     shape.
  D. Every ad_users.json/ad_computers.json record's ad_ou contains its own
     site's Province OU when sites.csv defines one for that site (catches
     bug class 4, and would catch the same gap for any future province-
     having site, not just re-verify Sydney/Melbourne specifically).

Exit code: 0 if nothing found, 1 otherwise.
"""
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"


def load_json(name, problems):
    path = BENARBEJDE / name
    try:
        return json.loads(path.read_text())
    except Exception as e:
        problems.append(f"{name}: could not load/parse -- {e}")
        return None


def load_sites_provinces(problems):
    path = BENARBEJDE / "sites.csv"
    provinces = {}
    try:
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                site = row.get("Site", "").strip()
                province = row.get("Province", "").strip()
                if site and province:
                    provinces[site] = province
    except Exception as e:
        problems.append(f"sites.csv: could not load/parse -- {e}")
    return provinces


def check_duplicate_sam(problems, records, filename, name_field):
    seen = {}
    for r in records:
        sam = (r.get("SamAccountName") or "").strip()
        if not sam:
            continue
        key = sam.lower()
        if key in seen:
            other_name = seen[key].get(name_field, "?")
            this_name = r.get(name_field, "?")
            problems.append(
                f"{filename}: SamAccountName '{sam}' is used by both "
                f"'{other_name}' and '{this_name}' -- these must be two "
                f"distinct identities (a typo needing correction, or two "
                f"genuinely different records that both need their own "
                f"real SamAccountName)"
            )
        else:
            seen[key] = r


def check_group_user_sam_collision(problems, groups, users):
    user_sams = {(u.get("SamAccountName") or "").lower(): u.get("SamAccountName")
                 for u in users if u.get("SamAccountName")}
    for g in groups:
        effective_sam = (g.get("SamAccountName") or g.get("Name") or "").strip()
        if not effective_sam:
            continue
        key = effective_sam.lower()
        if key in user_sams:
            problems.append(
                f"ad_groups.json: group '{g.get('Name')}' resolves to "
                f"SamAccountName '{effective_sam}', which collides "
                f"case-insensitively with user SamAccountName "
                f"'{user_sams[key]}' -- SamAccountName is unique across ALL "
                f"security principals, not just within one object class; "
                f"give the group an explicit SamAccountName override in "
                f"ad_groups.json that doesn't collide"
            )


def check_group_references(problems, groups, users):
    # What microsoft.ad.user's groups: add: actually resolves against --
    # a group's real effective SamAccountName, not its Name -- see bug
    # class 2 in this script's own header for why that distinction matters.
    valid_sams = {(g.get("SamAccountName") or g.get("Name") or "").lower()
                  for g in groups}
    group_names_only = {g.get("Name", "").lower() for g in groups}
    for u in users:
        for group_ref in u.get("Groups", []):
            ref_lower = group_ref.lower()
            if ref_lower in valid_sams:
                continue
            if ref_lower in group_names_only:
                # Exists as a Name but that group has a DIFFERENT effective
                # SamAccountName -- exactly bug class 2's shape.
                real_group = next(g for g in groups if g.get("Name", "").lower() == ref_lower)
                real_sam = real_group.get("SamAccountName") or real_group.get("Name")
                problems.append(
                    f"ad_users.json: {u.get('SamAccountName')}'s Groups "
                    f"references '{group_ref}' by Name, but that group's real "
                    f"SamAccountName is '{real_sam}' -- group membership "
                    f"resolves by SamAccountName, not Name, so this will "
                    f"silently resolve to the wrong object (or fail) at "
                    f"runtime; use '{real_sam}' in Groups: instead"
                )
            else:
                problems.append(
                    f"ad_users.json: {u.get('SamAccountName')}'s Groups "
                    f"references '{group_ref}', which matches no group's Name "
                    f"or SamAccountName in ad_groups.json at all"
                )


def check_ad_ou_province(problems, records, filename, provinces):
    for r in records:
        site = r.get("Site")
        ad_ou = r.get("ad_ou", "")
        if not site or site not in provinces or not ad_ou:
            continue
        province = provinces[site]
        expected_fragment = f"OU={province},"
        if expected_fragment not in ad_ou:
            problems.append(
                f"{filename}: {r.get('SamAccountName', r.get('Name', '?'))} "
                f"is at Site={site}, which sites.csv says has Province="
                f"'{province}', but its ad_ou doesn't contain "
                f"'{expected_fragment}': {ad_ou}"
            )


def main():
    problems = []

    users = load_json("ad_users.json", problems)
    groups = load_json("ad_groups.json", problems)
    computers = load_json("ad_computers.json", problems)
    provinces = load_sites_provinces(problems)

    if users is not None:
        check_duplicate_sam(problems, users, "ad_users.json", "Name")
    if computers is not None:
        check_duplicate_sam(problems, computers, "ad_computers.json", "Name")
    if groups is not None and users is not None:
        check_group_user_sam_collision(problems, groups, users)
        check_group_references(problems, groups, users)
    if users is not None and provinces:
        check_ad_ou_province(problems, users, "ad_users.json", provinces)
    if computers is not None and provinces:
        check_ad_ou_province(problems, computers, "ad_computers.json", provinces)

    print(
        f"Checked {len(users or [])} users, {len(groups or [])} groups, "
        f"{len(computers or [])} computers for duplicate SamAccountNames, "
        f"group/user SamAccountName collisions, Groups: reference validity, "
        f"and ad_ou Province consistency against {len(provinces)} "
        f"province-having site(s) in sites.csv."
    )

    if problems:
        print(f"\n{len(problems)} problem(s) found:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("No AD data integrity problems found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
