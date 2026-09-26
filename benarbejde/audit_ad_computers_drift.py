#!/usr/bin/env python3
"""
audit_ad_computers_drift.py -- read-only audit, benarbejde/, not part of at_have_ryggen_fri.

Robert, 2026-09-26, after noticing Fyn/Odense's AD OU tree was missing an SBC and its PVE
nodes under Devices: "let's look at regenerating ad_computers.json from devices.csv properly."

Root cause (confirmed, not assumed -- see the conversation this script came out of):
ad_computers.json is NOT derived from devices.csv at all. It's generated offline by
benarbejde/parse_tdf.py from a completely separate, legacy, hand-authored
jukebox.example.tdf file -- parse_tdf.py's own header calls this out explicitly ("LEGACY /
DEFUNCT TOOL"). The two datasets have never been reconciled against each other, for any
site, not just Fyn.

Robert's explicit instruction: jukebox.example.tdf MUST NOT be used/consulted/handled in
any way by the harness. Confirmed before writing this: at_have_ryggen_fri/ does not
reference jukebox.example.tdf or parse_tdf.py anywhere today (grepped clean). This script
doesn't either -- it only ever reads devices.csv, sites.csv, role_codes.csv, and the
CURRENT ad_computers.json (a plain JSON file, not the TDF).

Robert also confirmed (2026-09-26): ad_computers.json's existing entries carry real,
hand-authored value devices.csv has no equivalent for at all -- personalised Descriptions
("Corporate iPhone - Annie Lennox") and specific OS/OperatingSystemVersion pairs with real
serial-number-style strings ("Cisco ISR 4331" / "ISR4331-ABD-552901"). A wholesale
regenerate-and-overwrite would destroy that. His call: MERGE, not replace -- keep every
existing entry's flavour text as-is, only ADD what's genuinely missing, and audit drift
before touching anything, not silently auto-correct it. This script is that audit --
READ-ONLY, writes nothing, ever. A separate, later script does the actual merge-write once
Robert has reviewed this output.

What this reports, in order:
  1. Devices in devices.csv with NO ad_computers.json counterpart at all (the real gap --
     e.g. Fyn's SBC and 2x PVE). Grouped by Type, with the hostname and AD OU sub-category
     this script would propose for each.
  2. Entries in ad_computers.json with NO devices.csv counterpart (legacy/fictional-only
     entries the TDF invented that were never real tracked network equipment -- e.g. the
     Fairlight CMI, LinnDrum, Moog One novelty items. NOT proposed for deletion -- this
     repo is additive-only throughout; flagged for awareness only).
  3. Entries present in BOTH datasets whose current ad_ou doesn't match what this script
     computes from devices.csv/sites.csv -- genuine placement drift on real devices.
  4. The Type -> AD OU sub-category mapping this script uses, split into "already
     documented" (copied verbatim from windows_adschema/playbooks/10-ad-schema.yml's own
     header comment) and "newly assigned by this script" (the 15 devices.csv Types that
     comment never covered at all -- ANS, BPS, DCR, DNS, FCL, ILO, LIN, RAC, RMM, RUD, SLT,
     TAR, TMP, UFC, ZAB). The new ones are inferred from benarbejde/role_codes.csv's own
     Category column plus docs/emojis/README.md's explicit "same symbol, same role"
     groupings (e.g. ILO/RAC -> Infrastructure, same as BMC; FCL/LIN -> Assets, same as
     MOO -- the doc's own words are "both 'a keyboard'"/"same class") -- not fabricated,
     but genuinely new judgement calls this script is surfacing for confirmation before
     anything gets written permanently, per Robert's own ask.

Usage:
  python3 benarbejde/audit_ad_computers_drift.py
"""
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BENARBEJDE = REPO_ROOT / "benarbejde"
SITES_CSV = BENARBEJDE / "sites.csv"
DEVICES_CSV = BENARBEJDE / "devices.csv"
ROLE_CODES_CSV = BENARBEJDE / "role_codes.csv"
AD_COMPUTERS_JSON = BENARBEJDE / "ad_computers.json"

sys.path.insert(0, str(BENARBEJDE))
from generate_inventory import build_hostname  # noqa: E402  -- single source of truth for EXA<TYPE><SITE><NNN>

# Copied verbatim from windows_adschema/playbooks/10-ad-schema.yml's own
# _region_continent dict -- keep in sync if that file's mapping ever changes.
REGION_CONTINENT = {
    "uk_site":    "Europe",
    "de_site":    "Europe",
    "dk_site":    "Europe",
    "eu_site":    "Europe",
    "lb_site":    "Middle East",
    "us_site":    "North America",
    "ca_site":    "North America",
    "apac_site":  "Asia Pacific",
    "cloud_site": "Cloud Infrastructure",
}

# Copied verbatim from windows_adschema/playbooks/10-ad-schema.yml's own header comment
# ("Align with Type prefixes from devices.csv"). This is the ALREADY-DOCUMENTED mapping --
# every code here was already an explicit design decision, not this script's own.
DOCUMENTED_SUB_OU = {
    "Workstations":   ["WKS", "LAP", "SUR", "MAC", "MBP"],
    "Servers":        ["DCS", "SRV", "SVR", "SBC", "RDR"],
    "Infrastructure": ["FWL", "RTR", "SWI", "BMC", "PVE", "NAS", "NIX"],
    "Telephony":      ["PHN", "PBX", "PAY"],
    "AV":             ["VCU", "LCD", "TVS", "MIC", "RAD"],
    "IoT":            ["CAM", "CLK", "WAP", "PMP", "TEA", "COF", "PRN", "DON", "VND", "MUS", "TTY"],
    "Assets":         ["BUS", "CAR", "TRK", "JET", "AST", "MOO", "TAB"],
}

# NEW judgement calls, not previously documented anywhere -- see this script's own
# docstring for the role_codes.csv Category / docs/emojis/README.md evidence behind each.
# Flagged separately in the report output rather than silently folded into the table
# above, so Robert can confirm or correct any of these before they become permanent.
NEWLY_ASSIGNED_SUB_OU = {
    "Servers":        ["ANS", "DNS", "RUD", "RMM", "SLT", "ZAB", "TMP", "TAR", "DCR", "UFC", "BPS"],
    "Infrastructure": ["ILO", "RAC"],
    "Assets":         ["LIN", "FCL"],
}

TYPE_TO_SUB_OU = {}
for _sub_ou, _codes in DOCUMENTED_SUB_OU.items():
    for _code in _codes:
        TYPE_TO_SUB_OU[_code] = _sub_ou
for _sub_ou, _codes in NEWLY_ASSIGNED_SUB_OU.items():
    for _code in _codes:
        TYPE_TO_SUB_OU[_code] = _sub_ou


def load_sites():
    with SITES_CSV.open(newline="", encoding="utf-8") as f:
        return {row["Site"].strip(): row for row in csv.DictReader(f)}


def load_role_names():
    with ROLE_CODES_CSV.open(newline="", encoding="utf-8") as f:
        return {row["Code"].strip(): row["Name"].strip() for row in csv.DictReader(f)}


def load_devices():
    with DEVICES_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_ad_computers():
    return json.loads(AD_COMPUTERS_JSON.read_text(encoding="utf-8"))


def base_dn():
    return "DC=jukebox,DC=internal"


def compute_ad_ou(site_row, sub_ou):
    region = site_row["AnsibleRegion"].strip()
    continent = REGION_CONTINENT.get(region)
    if continent is None:
        return None, f"unknown AnsibleRegion '{region}'"
    if continent == "Cloud Infrastructure":
        return f"OU={sub_ou},OU=Devices,OU=Cloud Infrastructure,OU=Sites,{base_dn()}", None
    country = site_row["Country"].strip()
    province = site_row["Province"].strip()
    city = site_row["City"].strip()
    cpath = f"OU={country},OU={continent},OU=Sites,{base_dn()}"
    if province:
        cpath = f"OU={province},{cpath}"
    return f"OU={sub_ou},OU=Devices,OU={city},{cpath}", None


def main():
    sites = load_sites()
    role_names = load_role_names()
    devices_all = load_devices()
    # Planned=yes rows are hardware that doesn't exist yet at all (known expansion
    # slots -- see generate_inventory.py's own "Planned=yes rows are hardware that
    # doesn't exist yet" comment). 488 of 864 devices.csv rows are Planned=yes --
    # confirmed live before this filter went in, the very first audit run counted
    # every one of them as a "missing AD record" for equipment that physically
    # isn't built. An AD computer object for a device that doesn't exist yet is
    # the opposite of "no operational gaps" -- it's a phantom record for
    # something nobody has actually seen. Excluded here, not just at write time,
    # so every count and list this script prints is accurate from the start.
    devices = [r for r in devices_all if r["Planned"].strip().lower() != "yes"]
    ad_computers = load_ad_computers()
    ad_by_name = {c["Name"].upper(): c for c in ad_computers}

    missing = []       # in devices.csv, no ad_computers.json counterpart
    matched_names = set()
    drift = []          # in both, but ad_ou doesn't match computed

    for row in devices:
        site_code = row["Site"].strip()
        dtype = row["Type"].strip()
        number_str = row["Number"].strip()
        if site_code not in sites or not number_str.isdigit():
            continue
        hostname = build_hostname(dtype, site_code, int(number_str))
        sub_ou = TYPE_TO_SUB_OU.get(dtype)
        if sub_ou is None:
            missing.append((hostname, dtype, site_code, "NO SUB-OU MAPPING AT ALL -- new Type since this script was written"))
            continue
        computed_ou, err = compute_ad_ou(sites[site_code], sub_ou)
        existing = ad_by_name.get(hostname.upper())
        if existing is None:
            missing.append((hostname, dtype, site_code, f"proposed OU: {computed_ou or err}"))
            continue
        matched_names.add(hostname.upper())
        if err:
            drift.append((hostname, "SITE ERROR", err))
        elif existing.get("ad_ou", "") != computed_ou:
            drift.append((hostname, existing.get("ad_ou", "(none)"), computed_ou))

    orphans = [c for c in ad_computers if c["Name"].upper() not in matched_names]

    print(f"({len(devices_all) - len(devices)} Planned=yes devices.csv row(s) excluded -- not built yet, no AD record possible)")
    print()
    print("=" * 88)
    print(f"1. MISSING from ad_computers.json ({len(missing)} device(s) real in devices.csv, absent from AD tracking)")
    print("=" * 88)
    by_type = {}
    for hostname, dtype, site_code, note in missing:
        by_type.setdefault(dtype, []).append((hostname, site_code, note))
    for dtype in sorted(by_type):
        name = role_names.get(dtype, "?")
        print(f"\n  {dtype} ({name}) -- {len(by_type[dtype])} missing:")
        for hostname, site_code, note in sorted(by_type[dtype]):
            print(f"    {hostname:20s} [{site_code}]  {note}")

    print()
    print("=" * 88)
    print(f"2. ORPHANS in ad_computers.json ({len(orphans)} entries with no devices.csv counterpart -- legacy/fictional-only, NOT proposed for deletion)")
    print("=" * 88)
    for c in sorted(orphans, key=lambda c: c["Name"]):
        print(f"  {c['Name']:20s} Role={c.get('Role','?'):6s} Site={c.get('Site','?'):5s} \"{c.get('Description','')}\"")

    print()
    print("=" * 88)
    print(f"3. PLACEMENT DRIFT ({len(drift)} device(s) present in both, current ad_ou doesn't match devices.csv-computed OU)")
    print("=" * 88)
    for hostname, current, computed in drift:
        print(f"  {hostname}")
        print(f"    current:  {current}")
        print(f"    computed: {computed}")

    print()
    print("=" * 88)
    print("4. Type -> AD OU sub-category mapping used above")
    print("=" * 88)
    print("\n  Already documented (windows_adschema/playbooks/10-ad-schema.yml's own header comment):")
    for sub_ou, codes in DOCUMENTED_SUB_OU.items():
        print(f"    {sub_ou:15s} {', '.join(codes)}")
    print("\n  NEWLY ASSIGNED by this script -- please confirm or correct before this becomes permanent:")
    for sub_ou, codes in NEWLY_ASSIGNED_SUB_OU.items():
        print(f"    {sub_ou:15s} {', '.join(codes)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
