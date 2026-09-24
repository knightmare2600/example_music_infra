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
  5. Found live 2026-09-24, chasing a CLY/GLA subnet data-entry bug:
     ad_computers.json's IPv4Address values had silently drifted from
     devices.csv's own real per-hostname address across 56 records at 17
     sites (wrong subnet base, wrong octet, or both) -- Robert: "I thought
     we had a json file for IP ranges and conventions, can we consult
     that?" devices.csv (fed through the same load_devices()/build_hostname()
     generate_inventory.py itself uses, not a second hand-rolled copy of the
     convention) is exactly that source of truth for any hostname it
     defines, and nothing previously cross-checked ad_computers.json against
     it.
  6. Same investigation surfaced real IPv4Address duplicates WITHIN
     ad_computers.json itself, same site, two different real devices (e.g.
     an HP iLO and a Dell DRAC both claiming CLY's `.30`, two Falkirk iDRACs
     both claiming `.30`) -- devices.csv has no opinion on these (no real
     row exists for either device), so bug class 5's check can't catch
     them; a same-site duplicate-IP check catches this shape independently.
  7. Found live 2026-09-24, working through the remaining ABD/BIR/BON/LAX
     duplicate-IP pairs bug class 6 leaves unresolved when devices.csv also
     has no opinion: Robert's own proposed fix -- "we need a third known
     source of truth ... taking BIRSWI as our example, it documents
     switches at 251". Confirmed live: `address_policy.csv`'s own
     Type-and-instance-number convention (the same `OFFSETS_SINGLE`/
     `ROLE_OFFSETS` generate_inventory.py itself uses) is a genuinely
     THIRD, independent signal -- devices.csv's BIR,SWI,2 row (`.251`) and
     address_policy.csv's own SWI-slot-2 convention (`.251`) agree with
     each other and disagree with ad_computers.json's `.20`; 2-of-3
     agreeing makes the outlier obvious without a human needing to guess.
     Robert's framing, verbatim: "if all three disagree we print a message
     and then the user has to decide. This is called failsafe." Explicitly
     diagnostic only -- this check never edits data, matching Robert's
     "don't fix any of them for now, just write or expand the checking
     harness's checks" instruction.

  8. Found live 2026-09-24, resolving BIR's ILO/RAC pair: EXAILOBIR001 and
     EXARACBIR001 are two DIFFERENT real devices (an HP iLO and a Dell
     DRAC) at two DIFFERENT IPs (.30 and .6) -- so check F's same-IP
     duplicate check never saw them as related at all. But both records'
     DNSHostName field says "EXARACBIR001.jukebox.internal" -- the exact
     same string, on two different records. Two records both claiming to
     BE the same DNS name is a real bug independent of whether their IPs
     also happen to collide; nothing before this checked DNSHostName
     duplication on its own terms.
  9. Same investigation: neither EXAILOBIR001 nor EXARACBIR001 has ANY
     benarbejde/devices.csv row at all, for a Type (ILO/RAC) that
     address_policy.csv DOES have a real addressing convention for (the
     .2-.4 BMC pool) -- devices.csv is missing real data the harness had no
     way to notice, because every previous check only ever looked for
     devices.csv rows that DO exist and checked them against
     ad_computers.json, never the reverse direction (a real ad_computers.json
     record with a policy-governed Type and no devices.csv counterpart at
     all).
  10. Found live 2026-09-24, still resolving BIR: Robert, on EXARACBIR001's
      claimed '.6' -- "is that a BMC address? No, .6 is a PVE host IP."
      Devices.csv/ad_computers.json are ALSO missing BIR's real PVE nodes
      entirely, and '.6' being genuinely, exactly PVE's own reserved second
      slot is exactly why EXARACBIR001 ended up there -- a real, previously
      invisible bug class: a record's address can be implausible for its
      OWN Type while landing EXACTLY on a completely different Type's own
      reserved territory, and nothing before this checked one record's
      address against every OTHER role's convention, only its own role's
      or another record sharing the identical IP.
  11. Found live 2026-09-24: Robert, on the RTR/FWL slot collision at
      BIR/ABD -- "this would also be a thing the harness would look for --
      multiple devices using same IP which is a recipe for disaster. Does
      it already do that?" It didn't, for the cross-FILE shape specifically
      -- check E only compares a record against devices.csv's row for its
      OWN hostname, check F only compares ad_computers.json records against
      each other. Neither catches an ad_computers.json record's IP silently
      matching devices.csv's real address for a COMPLETELY DIFFERENT
      hostname. Confirmed live, whole-estate scan: 4 real instances (e.g.
      EXACLKCPH001 claiming the same IP as the real EXATVSBON001).
  12. Same conversation, Robert's own proposed detection strategy: "if I
      have 3 PVE nodes and only 2 RAC/ILOs then by definition one is
      missing ... every site needs a minimum of one switch, one firewall."
      PVE-vs-RAC/ILO ratio specifically isn't buildable from
      ad_computers.json (confirmed live: zero sites have a PVE-Role record
      in it at all -- Linux hypervisors were never going to be Windows AD
      computer objects, so there's no baseline to compare against), but
      SWI/RTR genuinely do vary and ARE reliably modelled when real --
      confirmed via a real device-count scan across every standard site.
  13. Same conversation: Robert's counter to bug class 12's PVE limitation --
      "they can be made to authenticate to AD ... they could go in already
      existing -- or new -- OUs for Firewalls, Telephony, Switches, etc."
      Correct, and it reframes bug class 12 properly: PVE/FWL/DCS aren't
      structurally UNABLE to be tracked (Proxmox genuinely supports an
      LDAP/AD realm), they're just not tracked YET. Doesn't unlock a
      per-site ratio check (the absence is estate-wide, no baseline
      anywhere to compare against), but is worth a standing, one-time
      advisory rather than silence.
  14. Found live 2026-09-24, same conversation, after resolving SYD/MEL/AKL's
      RAC addresses directly: Robert -- "every site has one [PVE], and each
      of those would have a RAC or ILO, for sites with more ILO/RACs that
      means they also have more PVEs ... since you clearly see a RAC/ILO it
      must have a PVE attached to it by design ... I'm sure the harness can
      'catch' such things and print a 'hey I found XYZ thing' for the user."
      Bug class 12 couldn't build a PVE-vs-RAC/ILO ratio check because
      ad_computers.json has literally zero PVE records anywhere to compare
      against -- but the same 1:1 hardware convention runs the other way
      round just as reliably: a real ILO/RAC record's mere existence implies
      a real PVE node behind it (each BMC belongs to exactly one hypervisor
      host, by design), even though nothing currently tracks that host
      itself. Confirmed live: 15 sites currently carry real ILO/RAC records
      (1 each at most, 2 each at BIR/CLY/FAL -- matching FAL's own
      already-confirmed 2-node Proxmox cluster exactly), so this is a
      genuinely useful inferred baseline for the still-open "how do we bring
      PVE in" question, not just a repeat of bug class 12/13's absence note.
  15. Found live 2026-09-24, cross-referencing MEL's real FWL/SBC/NAS records
      while working through the missing-devices.csv-row backlog: three MEL
      records (EXAFWLMEL001, EXASBCMEL001, EXANASMEL001) had IPv4Address
      values in a subnet that doesn't exist -- '192.168.361.x', an extra
      stray digit against MEL's real, sites.csv-confirmed '192.168.61.0/24'
      base. A whole-estate scan confirmed this is isolated to these 3
      records, no wider pattern. Nothing before this validated an
      IPv4Address's basic shape at all -- every previous IP-related check
      (E/F/G/J/K) compares one real value against another, which silently
      assumes both sides are at least well-formed.

This checks thirteen independent surfaces, all from the files themselves, no AD
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
  E. Every ad_computers.json record whose SamAccountName matches a real
     devices.csv hostname has the exact same IPv4Address devices.csv itself
     would generate (catches bug class 5).
  F. No two ad_computers.json records at the same Site share a non-blank
     IPv4Address (catches bug class 6).
  G. FAILSAFE TRIANGULATION (Robert's own naming, 2026-09-24) -- for every
     pair check F flags where devices.csv has no answer for at least one
     side, brings in address_policy.csv's own Type-and-instance-number
     convention as a third, independent signal and reports a verdict per
     record: RESOLVABLE (2 of the up-to-3 signals agree, names the
     outlier), PLAUSIBLE (only a pool-membership check available, e.g.
     ILO/RAC's shared .2-.4 range, not a majority vote), or AMBIGUOUS
     (devices.csv silent AND address_policy.csv has no convention at all
     for this Type -- a genuinely ad hoc device like VCU). Never resolves
     bug class 5's already-clear cases twice (those are devices.csv-backed
     outright, check E already reports them) -- this is purely for the
     harder cases check E and F together can't already settle.
  H. No two ad_computers.json records share the same DNSHostName value,
     regardless of whether their IPv4Address also matches (catches bug
     class 8 -- a strictly harder-to-spot shape than check F's, since two
     records can genuinely claim the same DNS identity while sitting at two
     different, non-colliding IPs).
  I. Every ad_computers.json record whose Role has a real
     address_policy.csv addressing convention (any Type in
     OFFSETS_SINGLE/ROLE_OFFSETS, or ILO/RAC sharing BMC's pool) has a
     matching devices.csv row (catches bug class 9 -- devices.csv silently
     missing real data, the reverse direction from check E). Deliberately
     scoped to policy-governed Types only, using the exact same
     policy_expected_octet() this file's own check G already relies on --
     ad hoc Types with no policy convention at all (VCU, LCD, SVR, and pure
     Linux control-plane infrastructure) are never expected to have a
     devices.csv row and are correctly never flagged, avoiding the
     false-alarm risk that kept this check parked when it was first
     proposed (see [[project_criticality_alarm_2026_09_24]]).
  J. No ad_computers.json record's claimed octet lands exactly on a DIFFERENT
     Type's own address_policy.csv reserved slot while being implausible for
     its OWN Type (catches bug class 10). Respects SUPPRESSED_STANDARD_ROLES
     (generate_inventory.py's own record of deliberate, already-approved
     slot reuse) so a genuinely intentional reuse is never misreported as a
     collision.
  K. No ad_computers.json record's IPv4Address matches devices.csv's own
     real address for a DIFFERENT hostname (catches bug class 11) -- two
     real devices sharing one live IP is worse than either check E or F
     alone catches, since it's a genuine network conflict, not just stale
     data.
  L. Every standard site (not in NON_STANDARD_SITES) with ANY real
     ad_computers.json presence has at least one real SWI and one real RTR
     record (catches bug class 12) -- deliberately narrow to these two, the
     oldest/most universal standard-template categories; newer, still-
     rolling-out categories (NAS/SBC/WAP) are legitimately absent at real
     sites that haven't been retrofitted yet and would just add noise.
  M. Every ad_computers.json record's IPv4Address, when non-blank, is a
     structurally valid IPv4 address -- four numeric octets, each 0-255
     (catches bug class 15). Runs before any comparison-based check (E/F/G/
     J/K), which all silently assume both sides of a comparison are
     well-formed to begin with.

Two non-failing, whole-estate ADVISORIES also run (they never affect exit
code): check_ldap_trackable_advisory (bug class 13 -- PVE/FWL/DCS are
LDAP-trackable in principle but currently have zero records anywhere) and
check_pve_inference_advisory (bug class 14 -- per site, infers a real PVE
node's existence from real ILO/RAC record(s) already present, since the BMC
count is a reliable 1:1 proxy for hypervisor host count even though PVE
itself is never tracked).

Exit code: 0 if nothing found, 1 otherwise.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"
sys.path.insert(0, str(BENARBEJDE))
import generate_inventory as gi  # noqa: E402  -- load_devices()/build_hostname(), not a second copy


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


def check_malformed_ipv4(problems, computers):
    """Found live 2026-09-24, cross-referencing MEL's EXAFWLMEL001 for a
    devices.csv row: its IPv4Address was '192.168.361.253' -- octet '361' is
    not a valid IPv4 octet (0-255) at all, an extra stray digit against the
    site's own real subnet base (192.168.61.0/24, confirmed via sites.csv and
    every other MEL record). No previous check validates IPv4Address's basic
    shape -- check E only compares against devices.csv when a row exists,
    which these MEL records didn't have (that's exactly why this was
    invisible until now). A malformed octet can't be a stale-data drift
    question -- it was never a valid address to begin with."""
    for c in computers:
        ip = (c.get("IPv4Address") or "").strip()
        if not ip:
            continue
        parts = ip.split(".")
        if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            problems.append(
                f"ad_computers.json: {c.get('SamAccountName', c.get('Name', '?'))}'s "
                f"IPv4Address '{ip}' is not a valid IPv4 address (an octet is "
                f"missing, non-numeric, or out of the 0-255 range) -- this was "
                f"never a valid address, not just stale data"
            )


def load_real_addresses(problems):
    """hostname -> real full IP, straight from devices.csv via the same
    load_devices()/build_hostname() generate_inventory.py itself uses for
    the .ini/DNS output -- not a second, separately-derived copy."""
    try:
        gi.load_address_policy(BENARBEJDE / "address_policy.csv")
        devices_by_site, _ = gi.load_devices(BENARBEJDE / "devices.csv")
        sites = {}
        with (BENARBEJDE / "sites.csv").open(newline="") as f:
            for row in csv.DictReader(f):
                try:
                    site = row["Site"].strip()
                    base = ".".join(row["Subnet"].strip().split("/")[0].split(".")[:3])
                    sites[site] = base
                except Exception:
                    continue
        real = {}
        for site, devs in devices_by_site.items():
            base = sites.get(site)
            if not base:
                continue
            for d in devs:
                if d["octet"] is not None:
                    real[d["hostname"]] = f"{base}.{d['octet']}"
        return real
    except Exception as e:
        problems.append(f"devices.csv: could not derive real addresses -- {e}")
        return {}


def check_ip_matches_devices_csv(problems, computers, real_addresses):
    for c in computers:
        sam = (c.get("SamAccountName") or "").rstrip("$")
        ip = (c.get("IPv4Address") or "").strip()
        if not sam or not ip or sam not in real_addresses:
            continue
        if ip != real_addresses[sam]:
            problems.append(
                f"ad_computers.json: {sam}'s IPv4Address is '{ip}', but "
                f"devices.csv's own real address for this exact hostname is "
                f"'{real_addresses[sam]}' -- ad_computers.json has drifted "
                f"from the source of truth"
            )


def check_cross_file_ip_collision(problems, computers, real_addresses):
    """Robert, 2026-09-24: "multiple devices using the same IP which is a recipe for
    disaster. So... does it already do that or not?" It didn't -- check E only ever
    compares a record against DEVICES.CSV'S ROW FOR THAT SAME HOSTNAME (catches drift),
    and check F only compares ad_computers.json records against EACH OTHER. Neither
    catches an ad_computers.json record's IP silently matching devices.csv's OWN real
    address for a COMPLETELY DIFFERENT hostname -- two real, unrelated devices sharing
    one live IP, worse than either bug class alone since it's a genuine network
    conflict, not just stale data. Confirmed live, whole-estate scan: 4 real instances
    (e.g. EXACLKCPH001 claims the same IP as the real EXATVSBON001) that nothing before
    this ever surfaced."""
    ip_to_devhost = {ip: hostname for hostname, ip in real_addresses.items()}
    for c in computers:
        sam = (c.get("SamAccountName") or "").rstrip("$")
        ip = (c.get("IPv4Address") or "").strip()
        if not sam or not ip or ip not in ip_to_devhost:
            continue
        devhost = ip_to_devhost[ip]
        if devhost != sam:
            problems.append(
                f"ad_computers.json: {sam} claims IPv4Address '{ip}', but devices.csv's "
                f"own real address book says that IP belongs to a DIFFERENT real device, "
                f"{devhost} -- two real devices sharing one live IP, not just stale data"
            )


def policy_expected_octet(role, number):
    """address_policy.csv's own opinion of where a given Type's Nth instance belongs,
    straight from the same OFFSETS_SINGLE/ROLE_OFFSETS generate_inventory.py itself
    uses -- not a second, hand-rolled copy of the convention.

    Returns ("exact", octet) when the Type+Number maps to one specific address (every
    OFFSETS_SINGLE/ROLE_OFFSETS Type, including BMC itself); ("pool", {octets}) for
    ILO/RAC, which share BMC's pool but have no fixed per-instance position (a real
    ILO/RAC can legitimately sit at whichever pool slot was physically free -- CLY's own
    real ILO/RAC landed on .3/.4, not .2/.3, see [[project_ilo_rac_bmc_convention_2026_09_24]]);
    or None when address_policy.csv has no convention for this Type at all (ad hoc
    device classes like VCU, LCD, SVR -- devices.csv's own real row, when one exists, is
    the only source of truth for these, and check E already covers that case).
    """
    if number == 1 and role in gi.OFFSETS_SINGLE:
        return ("exact", gi.OFFSETS_SINGLE[role])
    if role in gi.ROLE_OFFSETS and 1 <= number <= len(gi.ROLE_OFFSETS[role]):
        return ("exact", gi.ROLE_OFFSETS[role][number - 1])
    if role in ("ILO", "RAC") and "BMC" in gi.ROLE_OFFSETS:
        return ("pool", set(gi.ROLE_OFFSETS["BMC"]))
    return None


def build_octet_role_map():
    """octet -> set(roles) that reserve it, from OFFSETS_SINGLE + ROLE_OFFSETS. DHCP
    deliberately excluded -- it's a pool marker, not a device Type, and "a static device
    sits inside the dynamic pool range" is a different question from role-slot confusion,
    not something this specific check is trying to answer."""
    m = defaultdict(set)
    for role, octet in gi.OFFSETS_SINGLE.items():
        m[octet].add(role)
    for role, octets in gi.ROLE_OFFSETS.items():
        if role == "DHCP":
            continue
        for o in octets:
            m[o].add(role)
    return m


def check_cross_role_collision(problems, computers, octet_role_map, real_addresses):
    """Robert, 2026-09-24, live, on EXARACBIR001's claimed '.6': "is that a BMC address? No
    -- .6 is a PVE host IP." A record's claimed octet can be implausible for its OWN Role
    (fails policy_expected_octet()) while ALSO exactly matching a COMPLETELY DIFFERENT
    role's own reserved range -- strong, independent evidence the address is simply wrong,
    not merely unconfirmed. Never caught before: check F/G only ever compare a record
    against another ad_computers.json record sharing the exact same IP, and EXARACBIR001's
    '.6' doesn't collide with anything else in ad_computers.json at all -- a uniquely wrong
    address is invisible to every same-IP-duplicate check by definition. Confirmed live:
    devices.csv/ad_computers.json are ALSO missing BIR's real PVE nodes entirely (not just
    ILO/RAC) -- exactly the device Type '.6' really belongs to -- so this check's own
    "which role actually owns this address" signal is the only thing that caught it.
    Respects SUPPRESSED_STANDARD_ROLES (generate_inventory.py's own record of deliberate,
    already-approved slot reuse, e.g. CLY's real switch sitting on BMC's own '.2') -- a
    documented, intentional reuse is never a collision.

    Also checks devices.csv's own real address for this exact hostname, not just the
    generic address_policy.csv convention -- found live, 2026-09-24: FAL genuinely has 3
    real workstations at consecutive octets .100/.101/.102 (devices.csv-confirmed real
    rows), which doesn't match address_policy.csv's own single-instance WKS convention
    (.101, assuming only one WKS per site) at all -- without this, EXAWKSFAL001 (.100)
    would false-flag as a cross-role collision candidate purely because the GENERIC
    policy doesn't cover a legitimate, real, site-specific exception devices.csv already
    confirms."""
    for c in computers:
        sam = (c.get("SamAccountName") or "").rstrip("$")
        role = (c.get("Role") or "").strip().upper()
        site = (c.get("Site") or "").strip()
        ip = (c.get("IPv4Address") or "").strip()
        if not sam or not role or not ip:
            continue
        if real_addresses.get(sam) == ip:
            continue
        octet_str = ip.rsplit(".", 1)[-1]
        if not octet_str.isdigit():
            continue
        octet = int(octet_str)
        try:
            number = int(sam[-3:])
        except (ValueError, IndexError):
            number = None
        own_policy = policy_expected_octet(role, number) if number else None
        own_plausible = own_policy and (
            (own_policy[0] == "exact" and own_policy[1] == octet)
            or (own_policy[0] == "pool" and octet in own_policy[1])
        )
        if own_plausible:
            continue
        colliding = octet_role_map.get(octet, set()) - {role}
        colliding -= gi.SUPPRESSED_STANDARD_ROLES.get(site, set())
        if colliding:
            problems.append(
                f"ad_computers.json: {sam} (Role={role}) claims IPv4Address '{ip}' -- "
                f".{octet} doesn't match {role}'s own address_policy.csv convention, but "
                f"it IS exactly {'/'.join(sorted(colliding))}'s own reserved slot at this "
                f"site -- likely address confusion with a different device Type entirely, "
                f"not just an unconfirmed value"
            )


def check_minimum_standard_equipment(problems, computers):
    """Robert, 2026-09-24: "we know every site needs a minimum of one switch, one
    firewall ... there is methodology and scope in being able to find 'enough' standard
    site equipment to catch 'big' errors that can take a site down." PVE specifically
    can't be checked this way (see check K's own header -- ad_computers.json never
    tracks it, for any site, so there is no baseline to compare against), but SWI/RTR
    genuinely do vary site to site and ARE reliably modelled here when real -- confirmed
    live, a real device-count scan across every standard site. Deliberately narrow (just
    these two, the oldest and most universal standard-template categories) rather than
    also checking newer, still-rolling-out categories like NAS/SBC/WAP, which are
    legitimately absent at plenty of real sites that just haven't been retrofitted yet
    -- see docs/proxmox/proxmox-dcm-pbs-planning.md's own NAS rollout notes. A site with
    ad_computers.json presence but ZERO real SWI or RTR records is a genuinely different,
    much more concerning shape than "hasn't gotten a NAS yet.\""""
    by_site_role = defaultdict(set)
    for c in computers:
        site = (c.get("Site") or "").strip()
        role = (c.get("Role") or "").strip().upper()
        if site and role:
            by_site_role[site].add(role)
    for site, roles in by_site_role.items():
        if site in gi.NON_STANDARD_SITES:
            continue
        missing = [r for r in ("SWI", "RTR") if r not in roles]
        if missing:
            problems.append(
                f"ad_computers.json: {site} has real device records but ZERO for "
                f"{'/'.join(missing)} -- every real, built site needs at least one "
                f"switch and one router/firewall; a site missing either entirely in "
                f"ad_computers.json is worth checking directly, not just noting"
            )


def check_ldap_trackable_advisory(computers):
    """Robert, 2026-09-24: PVE/FWL aren't Windows and don't domain-join, but that's not
    the same as "can never be represented" -- Proxmox genuinely supports an LDAP/AD
    realm for its own auth, so there's no technical reason a PVE node (or a Linux
    firewall) couldn't get an AD-adjacent entry the same way SWI/RTR already do,
    existing Infrastructure OU or a new one. Confirmed live: right now, NONE of them do
    -- zero PVE, FWL, or DCS Role records exist anywhere in ad_computers.json, not at
    any single site. This is deliberately NOT a per-site "problem" (that would need a
    real baseline elsewhere to compare against, which doesn't exist -- see check L's own
    header) -- it's a one-time, whole-estate advisory: if/when this estate starts
    LDAP-tracking these Types the way it already does switches and routers, checks
    equivalent to K/L above would start working for them too, the same way they already
    do for SWI/RTR."""
    counts = defaultdict(int)
    for c in computers:
        role = (c.get("Role") or "").strip().upper()
        if role in ("PVE", "FWL", "DCS"):
            counts[role] += 1
    zero = [r for r in ("PVE", "FWL", "DCS") if counts[r] == 0]
    if not zero:
        return None
    return (
        f"ADVISORY (not a failure): {', '.join(zero)} have ZERO records anywhere in "
        f"ad_computers.json, at any site -- not a single-site gap, a whole-estate one. "
        f"PVE nodes and Linux firewalls aren't domain-joined, but Proxmox does support "
        f"LDAP/AD-realm auth, so there's no technical reason these couldn't be tracked "
        f"the same way SWI/RTR already are (existing Infrastructure OU or a new one). "
        f"If this estate starts doing that, checks K/L above would start covering these "
        f"Types too -- right now there's no baseline anywhere to check them against."
    )


def check_pve_inference_advisory(computers):
    """Robert, 2026-09-24: "every site has one [PVE], and each of those would
    have a RAC or ILO, for sites with more ILO/RACs that means they also have
    more PVEs ... since you clearly see a RAC/ILO it must have a PVE attached
    to it by design." The reverse of check_ldap_trackable_advisory's absence
    note: PVE itself is never tracked, but a real ILO/RAC record is a
    reliable 1:1 proxy for a real hypervisor host behind it, so its mere
    presence is a genuinely useful inferred baseline rather than nothing at
    all. Deliberately per-site and additive-only -- an inferred count, never
    a "problem," and never compared against anything else since there is
    still no independently-tracked PVE figure anywhere to check it against."""
    counts = defaultdict(int)
    for c in computers:
        role = (c.get("Role") or "").strip().upper()
        site = (c.get("Site") or "").strip()
        if role in ("ILO", "RAC") and site:
            counts[site] += 1
    if not counts:
        return None
    lines = [
        f"  - {site}: {n} real ILO/RAC record(s) -- implies {n} real PVE "
        f"node(s), none currently tracked in ad_computers.json"
        for site, n in sorted(counts.items())
    ]
    return (
        "ADVISORY (not a failure): inferred PVE node count by site, from "
        "real ILO/RAC records already present (each BMC implies one real "
        "hypervisor host behind it, by design):\n" + "\n".join(lines)
    )


def triangulate(c, real_addresses):
    """One record's own three possible signals for what its real address should be --
    devices.csv (exact, when a real row exists), address_policy.csv (exact or pool,
    when this Type has a convention), or neither (genuinely ad hoc, no independent
    opinion at all). Never guesses a Number from anything other than the hostname's own
    trailing NNN -- the same convention build_hostname()/EXA<ROLE><SITE><NNN> already
    uses estate-wide."""
    sam = (c.get("SamAccountName") or "").rstrip("$")
    role = (c.get("Role") or "").strip().upper()
    try:
        number = int(sam[-3:])
    except (ValueError, IndexError):
        number = None
    devices_octet = None
    if sam in real_addresses:
        devices_octet = real_addresses[sam].rsplit(".", 1)[-1]
    policy = policy_expected_octet(role, number) if (role and number) else None
    return sam, devices_octet, policy


def check_duplicate_ip_within_site(problems, computers, real_addresses):
    seen = defaultdict(list)
    for c in computers:
        site = c.get("Site")
        ip = (c.get("IPv4Address") or "").strip()
        if not site or not ip:
            continue
        seen[(site, ip)].append(c)
    for (site, ip), members in seen.items():
        if len(members) <= 1:
            continue
        names = [c.get("Name", c.get("SamAccountName", "?")) for c in members]
        claimed_octet = ip.rsplit(".", 1)[-1]
        verdicts = []
        for c in members:
            sam, devices_octet, policy = triangulate(c, real_addresses)
            if devices_octet and devices_octet != claimed_octet:
                verdicts.append(
                    f"{sam}: devices.csv's own real address for this hostname is "
                    f".{devices_octet}, not .{claimed_octet} -- RESOLVABLE, see the "
                    f"separate IPv4Address-drift finding for this hostname above"
                )
            elif policy and policy[0] == "exact" and str(policy[1]) != claimed_octet:
                verdicts.append(
                    f"{sam}: address_policy.csv's own convention for this Type/"
                    f"instance is .{policy[1]}, not .{claimed_octet}, and devices.csv "
                    f"has no row for it -- RESOLVABLE (policy vs. claimed IP disagree, "
                    f"devices.csv silent -- {sam}'s real address is very likely "
                    f".{policy[1]})"
                )
            elif policy and policy[0] == "pool":
                in_pool = claimed_octet.isdigit() and int(claimed_octet) in policy[1]
                verdicts.append(
                    f"{sam}: devices.csv has no row for it; address_policy.csv only "
                    f"confirms {sam}'s Type shares the .{{{','.join(str(o) for o in sorted(policy[1]))}}} "
                    f"pool, not a specific instance -- PLAUSIBLE" if in_pool else
                    f"{sam}: devices.csv has no row for it, and its claimed .{claimed_octet} "
                    f"falls OUTSIDE its Type's expected .{{{','.join(str(o) for o in sorted(policy[1]))}}} "
                    f"pool entirely -- AMBIGUOUS, likely a stale/placeholder address"
                )
            else:
                verdicts.append(
                    f"{sam}: devices.csv has no row for it, and address_policy.csv has "
                    f"no addressing convention for this Type at all -- AMBIGUOUS, "
                    f"needs a real answer from Robert, not an automated guess"
                )
        problems.append(
            f"ad_computers.json: {site}'s {', '.join(names)} all claim IPv4Address "
            f"'{ip}' -- either the same physical device recorded twice, or two real "
            f"devices that both need their own real address. FAILSAFE TRIANGULATION "
            f"(devices.csv + address_policy.csv as two more independent signals): "
            + "; ".join(verdicts)
        )


def check_duplicate_dns_hostname(problems, computers):
    """Found live 2026-09-24 resolving BIR's ILO/RAC pair: EXAILOBIR001 (.30) and
    EXARACBIR001 (.6) never shared an IP, so check F never related them -- but both
    records' DNSHostName says "EXARACBIR001.jukebox.internal", the identical string.
    Two records both claiming the same DNS identity is a real bug on its own terms,
    independent of whether their addresses also happen to collide."""
    seen = defaultdict(list)
    for c in computers:
        dns = (c.get("DNSHostName") or "").strip()
        if not dns:
            continue
        seen[dns.lower()].append(c)
    for dns_lower, members in seen.items():
        if len(members) <= 1:
            continue
        sams = [(c.get("SamAccountName") or "").rstrip("$") for c in members]
        self_owner = [s for s in sams if s.lower() == dns_lower.split(".")[0]]
        problems.append(
            f"ad_computers.json: {', '.join(sams)} all have DNSHostName "
            f"'{members[0].get('DNSHostName')}' -- only "
            f"{self_owner[0] if self_owner else 'none of them'} actually owns that "
            f"identity; the other(s) need their own real DNSHostName "
            f"({', '.join(s for s in sams if s not in self_owner)}.jukebox.internal, "
            f"unless they're a genuinely different device that needs a different "
            f"hostname entirely)"
        )


def load_legacy_site_types(problems):
    """Site -> set(Type), for devices.csv rows SPECIFICALLY marked Legacy=yes -- not
    "any row of this Type exists" (a live row for a different instance Number, e.g.
    BIR's real WAP,2, says nothing about whether WAP,1 has ITS OWN row, Legacy or
    otherwise, and conflating the two would misreport a genuinely-missing row as
    "explained by a legacy entry" when it isn't). A raw CSV read, deliberately NOT
    going through load_devices(), because load_devices() drops Legacy rows before
    check_missing_devices_csv_row() would ever see they existed at all. Found live
    2026-09-24: ABD's real RTR/FWL pair and BIR's own EXAFWLBIR001 both have a real
    devices.csv row (matching OS/octet) that's excluded purely for being Legacy=yes --
    without this, check I would call them "no row exists at all", which overstates the
    gap (a real, if old, row DOES exist, it's just not live-generation-eligible)."""
    try:
        by_site = defaultdict(set)
        with (BENARBEJDE / "devices.csv").open(newline="") as f:
            for row in csv.DictReader(f):
                site = (row.get("Site") or "").strip()
                dtype = (row.get("Type") or "").strip().upper()
                legacy = (row.get("Legacy") or "").strip().lower()
                if site and dtype and legacy in ("yes", "y", "true", "1"):
                    by_site[site].add(dtype)
        return by_site
    except Exception as e:
        problems.append(f"devices.csv: could not do a raw Legacy-aware read -- {e}")
        return {}


def check_missing_devices_csv_row(problems, computers, real_addresses, legacy_site_types):
    """Found live 2026-09-24, same BIR investigation: neither EXAILOBIR001 nor
    EXARACBIR001 has ANY devices.csv row at all, despite ILO/RAC being a Type
    address_policy.csv DOES have a real addressing convention for (the BMC pool).
    Every previous check only ever verified a devices.csv row that DOES exist against
    ad_computers.json -- never the reverse: a real, policy-governed ad_computers.json
    record with NO devices.csv counterpart. Deliberately scoped to policy_expected_octet()
    returning non-None (the same function check G already uses) -- ad hoc Types with no
    policy convention at all are never expected to have a devices.csv row and are
    correctly never flagged here."""
    for c in computers:
        sam = (c.get("SamAccountName") or "").rstrip("$")
        role = (c.get("Role") or "").strip().upper()
        site = (c.get("Site") or "").strip()
        if not sam or sam in real_addresses:
            continue
        try:
            number = int(sam[-3:])
        except (ValueError, IndexError):
            continue
        policy = policy_expected_octet(role, number)
        if policy is None:
            continue
        pool_or_exact = (
            "pool " + str(sorted(policy[1])) if policy[0] == "pool" else "." + str(policy[1])
        )
        if role in legacy_site_types.get(site, set()):
            problems.append(
                f"devices.csv: {sam} (Role={role}) has no LIVE devices.csv row (it "
                f"would need one for address_policy.csv's {pool_or_exact} convention to "
                f"apply), but a devices.csv row for {site}/{role} DOES exist -- it's "
                f"just Legacy=yes (old-network data, correctly excluded from live "
                f"generation). Worth checking whether that legacy row actually "
                f"describes THIS device (matching OS/Description) before assuming it's "
                f"unrelated -- see ABD's EXARTRABD001/EXAFWLABD001 for a confirmed "
                f"example of exactly this shape"
            )
        else:
            problems.append(
                f"devices.csv: no row exists for {sam} (Role={role}) at all, not even a "
                f"Legacy one, but address_policy.csv has a real addressing convention "
                f"for this Type ({pool_or_exact}) -- devices.csv is missing real data "
                f"the harness had no other way to notice, since this is the reverse "
                f"direction of check E (a real ad_computers.json record with no "
                f"devices.csv counterpart, not the other way round)"
            )


def main():
    problems = []

    users = load_json("ad_users.json", problems)
    groups = load_json("ad_groups.json", problems)
    computers = load_json("ad_computers.json", problems)
    provinces = load_sites_provinces(problems)
    real_addresses = load_real_addresses(problems)

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
    if computers is not None:
        check_malformed_ipv4(problems, computers)
    if computers is not None and real_addresses:
        check_ip_matches_devices_csv(problems, computers, real_addresses)
        check_cross_file_ip_collision(problems, computers, real_addresses)
    if computers is not None:
        check_duplicate_ip_within_site(problems, computers, real_addresses)
    if computers is not None:
        check_duplicate_dns_hostname(problems, computers)
    if computers is not None:
        legacy_site_types = load_legacy_site_types(problems)
        check_missing_devices_csv_row(problems, computers, real_addresses, legacy_site_types)
    if computers is not None:
        octet_role_map = build_octet_role_map()
        check_cross_role_collision(problems, computers, octet_role_map, real_addresses)
    if computers is not None:
        check_minimum_standard_equipment(problems, computers)

    advisory = check_ldap_trackable_advisory(computers) if computers is not None else None
    pve_advisory = check_pve_inference_advisory(computers) if computers is not None else None

    print(
        f"Checked {len(users or [])} users, {len(groups or [])} groups, "
        f"{len(computers or [])} computers for duplicate SamAccountNames, "
        f"group/user SamAccountName collisions, Groups: reference validity, "
        f"ad_ou Province consistency against {len(provinces)} "
        f"province-having site(s) in sites.csv, IPv4Address agreement with "
        f"devices.csv ({len(real_addresses)} real hostname(s) known), "
        f"same-site IPv4Address duplicates, duplicate DNSHostName values, and "
        f"policy-governed Types missing a devices.csv row."
    )

    if advisory:
        print(f"\n{advisory}")

    if pve_advisory:
        print(f"\n{pve_advisory}")

    if problems:
        print(f"\n{len(problems)} problem(s) found:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("No AD data integrity problems found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
