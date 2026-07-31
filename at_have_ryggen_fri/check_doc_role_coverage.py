#!/usr/bin/env python3
"""
check_doc_role_coverage.py -- part of at_have_ryggen_fri.

Found live 2026-07-29: the 2026-07-26 NAS/RDR/BMC/WAP synthesis policy
(generate_inventory.py's DNS_SINGLE_ROLES/DNS_MULTI_FIRST_INSTANCE_ONLY)
added EXANASCLD001/EXARDRCLD001/EXABMCCLD001 to CLD's real device list --
docs/network-diagram/cld.md (generated) picked them up automatically, but
docs/site-inventory.md's hand-maintained CLD Infrastructure Checklist never
did, and nothing caught it. Found only by a manual read, per Robert's own
"add a harness check for new 'things', flag if it's missing too" ask.

Cross-references generate_inventory.py's real per-site device list against
docs/site-inventory.md's per-site sections (bounded by "## <CODE> --..."
headers, same pattern generate_network_diagrams.py's insert_topology_into_
docs() already uses to scope a site's own content). For every site that HAS
a section there, flags any real device hostname that doesn't appear
anywhere (as a backtick-quoted string) in that site's own section text.

Deliberately does NOT flag a site for having no section at all -- that's a
different, separate question (whether site-inventory.md should cover that
site), not this check's job. VRK/FRD are structurally never flagged: they
have no site-inventory.md section (by design, see that file's own CLD
section note) and no standard-slot devices either (NON_STANDARD_SITES), so
there's nothing to compare.

Devices with no HostOctet (phones, tablets, vehicles -- physical assets with
no fixed IP) are skipped: site-inventory.md's separate "Endpoints Checklist"
convention for these is looser/grouped ("- [ ] EXAPHNFAL001-003 — Phones",
one line covering several hostnames), which a literal per-hostname substring
match would false-positive on constantly. Only devices with a real
HostOctet -- the kind that gets a DNS record and belongs in "Infrastructure
Checklist" -- are checked.

Exit code: 0 if every real, addressed device for every documented site is
mentioned somewhere in that site's own section. Informational (Tier 2,
escalated to failure only with --strict) otherwise -- this is a real
documentation gap worth surfacing, but not one that should block every
unrelated commit until someone manually reconciles 53 sites' worth of docs.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"
SITE_INVENTORY = REPO_ROOT / "docs" / "site-inventory.md"

sys.path.insert(0, str(BENARBEJDE))
import generate_inventory as gi  # noqa: E402
import generate_network_diagrams as gnd  # noqa: E402  -- build_site_devices(), not a second copy


def load_real_devices_by_site():
    """Reuses generate_network_diagrams.build_site_devices() -- the exact function the topology
    generator itself uses -- rather than calling gi.compute_standard_devices_for_site() directly.
    That matters: build_site_devices() also applies NO_STANDARD_ROUTER_SITES (CLD/FRD's RTR is a
    documentation-only DNS placeholder, not a real device) and strips the -LAN duplicate entry.
    Found live 2026-07-30: an earlier version of this function called compute_standard_devices_
    for_site() directly and skipped that filter, so it false-positived EXARTRCLD001 as "missing"
    from CLD's site-inventory.md section -- it was never supposed to be there at all."""
    sites, devices_by_site = gnd.load_all()

    by_site = {}
    for site, row in sites.items():
        try:
            net = gi.validate_cidr(row["Subnet"])
        except ValueError:
            continue
        if site in gi.NON_STANDARD_SITES:
            continue
        hostnames = set()
        for d in gnd.build_site_devices(site, net, devices_by_site):
            if d.get("subnet_site") or d.get("is_foreign"):
                continue  # foreign/foldeded-in entry, not this site's own box
            if d["type"] == "TMP":
                continue  # deliberately never gets a formal EXA<ROLE><SITE><NNN> hostname
                # (see generate_inventory.py's own TMP handling) -- site-inventory.md correctly
                # documents these by IP only, never a hostname string that doesn't exist.
            if not d.get("octet"):
                continue  # no fixed IP -- Endpoints Checklist's looser grouped convention
            hostnames.add(d["hostname"])
        by_site[site] = hostnames
    return by_site


def load_doc_sections():
    text = SITE_INVENTORY.read_text(encoding="utf-8")
    headers = list(re.finditer(r'^## ([A-Z]{3}) — .*$', text, re.MULTILINE))
    sections = {}
    for i, m in enumerate(headers):
        site = m.group(1)
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        sections[site] = text[start:end]
    return sections


def main():
    real_by_site = load_real_devices_by_site()
    doc_sections = load_doc_sections()

    checked_sites = 0
    findings = []
    for site, hostnames in real_by_site.items():
        if site not in doc_sections:
            continue
        checked_sites += 1
        section = doc_sections[site]
        missing = sorted(h for h in hostnames if h not in section)
        if missing:
            findings.append((site, missing))

    print(f"Checked {checked_sites} site(s) with a docs/site-inventory.md section against their "
          f"real device list (generate_inventory.py).")

    if findings:
        total_missing = sum(len(m) for _, m in findings)
        print(f"\n{total_missing} informational finding(s) -- device(s) missing from their own "
              f"site-inventory.md section (Tier 2 -- confirm by hand; --strict fails on this):")
        for site, missing in findings:
            print(f"  - {site}: {', '.join(missing)}")
    else:
        print("\nEvery real, addressed device is mentioned somewhere in its own site's "
              "site-inventory.md section.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
