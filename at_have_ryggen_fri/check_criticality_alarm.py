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

  B. Missing-counterpart detection, 2026-10-01 -- scoped and built after
     checking real data instead of guessing a per-Type list. The original
     worry (2026-09-24) was that "pure Linux control-plane infrastructure --
     ANS/DNS/RUD/ZAB/SLT/RMM/PVE control planes -- is never modelled in
     ad_computers.json at all" would make a naive "every real row needs a
     record" check cry wolf immediately. Checked live, 2026-10-01: that's no
     longer true -- ad_computers.json now carries real, Enabled: true,
     OS: "Debian" records for exactly those roles (EXAANSCLD001,
     EXARUDCLD001, EXARMMCLD001, ...). A full coverage scan across every
     real devices.csv hostname, grouped by Type, found ZERO Types with no
     ad_computers.json record at all -- the only Type without an Enabled:
     true record (DCR, a Legacy/historical alias for DCS) still has a real
     record, correctly Enabled: false, matching this estate's own
     Enabled-as-decommission-flag convention. So direction one needs no
     per-Type scoping table at all:

     B1. Every real devices.csv hostname must have AT LEAST one
         ad_computers.json record under that exact SamAccountName, in any
         Enabled state. Confirmed zero exceptions against current data
         before shipping this.

     The reverse direction is architecturally different, not just the same
     check run backwards: a standard site's own DCS/PVE/non-Legacy-RTR
     deliberately has NO devices.csv row at all once real (see
     generate_inventory.is_standard_synthesis_excluded(), and
     [[project_got_dc_computer_account_incident_2026_09_26]]'s own
     2026-09-28 resolution for EXADCSGOT001) -- flagging that as "missing"
     would be a false positive on the exact estate convention this harness
     elsewhere already protects. Confirmed live: ad_computers.json's PVE
     records show this same shape across EVERY standard site (an Enabled:
     false placeholder pair, matching that site's own still-Planned
     devices.csv rows) with Enabled: true only for FRD/VRK's genuinely
     NON_STANDARD_SITES real nodes -- no standard site has a real PVE with
     no devices.csv row, so the exclusion is real, not theoretical.

     B2. Every Enabled: true ad_computers.json record must have EITHER a
         real devices.csv row, OR be explained by
         generate_inventory.is_standard_synthesis_excluded() (same
         mechanism, reused, not a second copy) -- using
         generate_inventory.policy_expected_octet() (moved here from
         check_ad_data_integrity.py the same day, for this exact reuse) to
         get the expected octet from the record's own Role + instance
         number.

Exit code: 1 if any conflict found, 0 otherwise. (See run.sh: this exit
code causes an immediate script exit, not just a FAILED_CHECKS entry.)
"""
import csv
import json
import sys
from collections import defaultdict
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


def load_legacy_site_types(problems):
    """Site -> {Type: OS}, for devices.csv rows SPECIFICALLY marked Legacy=yes -- not
    "any row of this Type exists" (a live row for a different instance Number, e.g.
    BIR's real WAP,2, says nothing about whether WAP,1 has ITS OWN row, Legacy or
    otherwise, and conflating the two would misreport a genuinely-missing row as
    "explained by a legacy entry" when it isn't). A raw CSV read, deliberately NOT
    going through load_devices(), because load_devices() drops Legacy rows before
    check_missing_devices_csv_row() would ever see they existed at all.

    Moved here 2026-10-01 from check_ad_data_integrity.py (consolidating Check B2 at
    the severity this direction actually deserves, not two copies of the same logic) --
    see that module's own git history for the original 2026-09-24 BIR investigation and
    the same-evening OS-comparison refinement this docstring used to carry in full."""
    try:
        by_site = defaultdict(dict)
        with (BENARBEJDE / "devices.csv").open(newline="") as f:
            for row in csv.DictReader(f):
                site = (row.get("Site") or "").strip()
                dtype = (row.get("Type") or "").strip().upper()
                legacy = (row.get("Legacy") or "").strip().lower()
                if site and dtype and legacy in ("yes", "y", "true", "1"):
                    by_site[site][dtype] = (row.get("OS") or "").strip()
        return by_site
    except Exception as e:
        problems.append(f"devices.csv: could not do a raw Legacy-aware read -- {e}")
        return {}


def load_planned_hostnames(problems):
    """Set of hostnames devices.csv marks Planned=yes -- warehouse stock, not yet
    installed, which still get a real, pre-staged ad_computers.json record (Enabled:
    false) via benarbejde/merge_ad_computers.py (2026-09-26, Robert's ask) -- a
    deliberate exception to this repo's otherwise-consistent "Planned isn't real yet"
    rule. Without this, every one of the ~488 Planned rows' new AD records would be
    flagged as "devices.csv is missing real data", when they're intentional,
    Robert-confirmed placeholders, not a gap. Moved here 2026-10-01, see
    load_legacy_site_types()'s own note on why."""
    try:
        hostnames = set()
        with (BENARBEJDE / "devices.csv").open(newline="") as f:
            for row in csv.DictReader(f):
                if (row.get("Planned") or "").strip().lower() != "yes":
                    continue
                site = (row.get("Site") or "").strip()
                dtype = (row.get("Type") or "").strip()
                number = (row.get("Number") or "").strip()
                if site and dtype and number.isdigit():
                    hostnames.add(gi.build_hostname(dtype, site, int(number)))
        return hostnames
    except Exception as e:
        problems.append(f"devices.csv: could not do a raw Planned-aware read -- {e}")
        return set()


def check_missing_ad_counterpart(problems, computers, real_hostnames):
    """Check B1, 2026-10-01: every real devices.csv hostname must have AT LEAST one
    ad_computers.json record under that exact SamAccountName, in any Enabled state.
    See this module's own docstring for the live coverage scan that found zero
    exceptions against current data before this was written -- every Type already
    achieves this except DCR (Legacy/historical), which still has a record, correctly
    Enabled: false, not "no record at all"."""
    ad_sams = set()
    for c in computers:
        sam = (c.get("SamAccountName") or "").rstrip("$")
        if sam:
            ad_sams.add(sam)
    for hostname, (site, dtype) in real_hostnames.items():
        if hostname not in ad_sams:
            problems.append(
                f"'{hostname}' ({site}, Type={dtype}) is a real devices.csv hostname, "
                f"but ad_computers.json has NO record at all under that name -- not even "
                f"a disabled/historical one. Every other real device of every Type in "
                f"this estate has at least a record; this one genuinely doesn't."
            )


def check_missing_devices_csv_row(problems, computers, real_hostnames, legacy_site_types, planned_hostnames):
    """Check B2, 2026-10-01 (consolidated here from check_ad_data_integrity.py's own
    check_missing_devices_csv_row() -- Robert's explicit choice: one real
    implementation, at alarm severity, not a second copy left behind at a lesser one).

    Found live 2026-09-24, BIR investigation: neither EXAILOBIR001 nor EXARACBIR001 had
    ANY devices.csv row at all, despite ILO/RAC being a Type address_policy.csv DOES
    have a real addressing convention for (the BMC pool) -- the reverse direction of
    Check B1 above (a real, policy-governed ad_computers.json record with NO devices.csv
    counterpart). Deliberately scoped to gi.policy_expected_octet() returning non-None --
    ad hoc Types with no policy convention at all are never expected to have a
    devices.csv row and are correctly never flagged here.

    A Legacy row's OS is compared directly against the real record's own OS
    (case-insensitive prefix match -- devices.csv's OS field is always the bare model,
    ad_computers.json's is the same model plus a serial-style suffix) -- a confirmed
    match is never reported; only a genuine mismatch, or a Legacy row with no OS to
    compare, gets the "worth checking" treatment.

    2026-09-28, GOT: building EXADCSGOT001 for real surfaced a genuine third category --
    a standard site's own DCS (or PVE, or a Legacy=no RTR) never gets an explicit
    devices.csv row at all once real, because its address comes purely from the
    standard-site synthesis mechanism (confirmed against FAL/CLY/GLA). Checked against
    gi.is_standard_synthesis_excluded() -- the exact rule load_devices() itself uses to
    drop a would-be-duplicate row -- not flagged as a gap."""
    for c in computers:
        sam = (c.get("SamAccountName") or "").rstrip("$")
        role = (c.get("Role") or "").strip().upper()
        site = (c.get("Site") or "").strip()
        if not sam or sam in real_hostnames or sam in planned_hostnames:
            continue
        try:
            number = int(sam[-3:])
        except (ValueError, IndexError):
            continue
        policy = gi.policy_expected_octet(role, number)
        if policy is None:
            continue
        if policy[0] == "exact" and gi.is_standard_synthesis_excluded(role, site, policy[1]):
            continue
        pool_or_exact = (
            "pool " + str(sorted(policy[1])) if policy[0] == "pool" else "." + str(policy[1])
        )
        if role in legacy_site_types.get(site, {}):
            legacy_os = legacy_site_types[site][role]
            real_os = (c.get("OS") or "").strip()
            if legacy_os and real_os and real_os.lower().startswith(legacy_os.lower()):
                continue
            problems.append(
                f"devices.csv: {sam} (Role={role}) has no LIVE devices.csv row (it "
                f"would need one for address_policy.csv's {pool_or_exact} convention to "
                f"apply), and a devices.csv row for {site}/{role} DOES exist (Legacy=yes) "
                f"but its OS ('{legacy_os}') doesn't match this record's own OS "
                f"('{real_os}') -- worth checking whether that legacy row actually "
                f"describes THIS device before assuming it's unrelated -- see ABD's "
                f"EXARTRABD001/EXAFWLABD001 for a confirmed example of exactly this shape"
            )
        else:
            problems.append(
                f"devices.csv: no row exists for {sam} (Role={role}) at all, not even a "
                f"Legacy one, but address_policy.csv has a real addressing convention "
                f"for this Type ({pool_or_exact}) -- devices.csv is missing real data "
                f"the harness had no other way to notice"
            )


def main():
    problems = []
    real_hostnames = load_real_hostnames(problems)
    computers = load_ad_computers(problems)

    if computers is not None and real_hostnames:
        check_hostname_ownership_conflict(problems, computers, real_hostnames)
        check_missing_ad_counterpart(problems, computers, real_hostnames)
        legacy_site_types = load_legacy_site_types(problems)
        planned_hostnames = load_planned_hostnames(problems)
        check_missing_devices_csv_row(
            problems, computers, real_hostnames, legacy_site_types, planned_hostnames
        )

    print(
        f"Checked {len(computers or [])} ad_computers.json record(s) against "
        f"{len(real_hostnames)} real devices.csv hostname(s) for cross-file ownership "
        f"conflicts and missing counterparts in either direction."
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
