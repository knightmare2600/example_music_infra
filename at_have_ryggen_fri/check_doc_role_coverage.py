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

Extended 2026-08-04 (Robert: "can we make the harness look for things like
this and flag them?", re-raised while checking project_cld_nas_rdr_bmc_doc_
drift -- which turned out to already be fixed in site-inventory.md and
network-inventory.md by the time this ran, just never closed out in memory.
The actual gap was narrower than it looked: this check only ever covered
site-inventory.md. docs/network-inventory.md and docs/ExampleMusic_
Beginners_Guide.md's own CLD table had zero equivalent coverage -- if either
drifted the same way site-inventory.md once did, nothing would catch it.

Two independent cross-references, same underlying real-device data
(generate_network_diagrams.build_site_devices(), the exact function the
topology generator itself uses):

  1. Per-site sections -- docs/site-inventory.md ("## <CODE> -- ...") and
     docs/network-inventory.md ("#### <CODE> -- ..."). Every regular site
     that has a section in either file gets its real hostnames checked
     against that section's text.
  2. CLD's special combined coverage -- CLD is folded together with VRK
     (and, in network-inventory.md, FRD too) into a single hand-maintained
     section in both files, not a per-site "#### CLD" block, so it needs
     its own bounded-section check: docs/network-inventory.md's "Cloud /
     Provisioning Network -- CLD / VRK / FRD" section, and docs/
     ExampleMusic_Beginners_Guide.md's "4.1 CLD" (+ "4.2 FRD") sections.
     VRK/FRD are NON_STANDARD_SITES (no per-site section, no standard-slot
     synthesis) but genuinely can have real devices.csv exception rows
     (EXAPVEVRK001, EXAPVEFRD001, ...) -- pulled directly from
     devices_by_site, not through the NON_STANDARD_SITES-skipping wrapper
     load_real_devices_by_site() uses for the per-site check.

Deliberately does NOT flag a site/file for having no section at all --
that's a different, separate question (whether a doc should cover that
site), not this check's job.

Devices with no HostOctet (phones, tablets, vehicles -- physical assets with
no fixed IP) are skipped throughout: the hand-maintained docs' separate
"Endpoints"-style convention for these is looser/grouped ("- [ ] EXAPHNFAL001-003
— Phones", one line covering several hostnames), which a literal
per-hostname substring match would false-positive on constantly. Only
devices with a real HostOctet -- the kind that gets a DNS record and
belongs in an infrastructure table/checklist -- are checked.

Exit code: 0 if every real, addressed device for every documented site/
section is mentioned somewhere in its own text. Informational (Tier 2,
escalated to failure only with --strict) otherwise -- this is a real
documentation gap worth surfacing, but not one that should block every
unrelated commit until someone manually reconciles every doc by hand.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"
SITE_INVENTORY = REPO_ROOT / "docs" / "site-inventory.md"
NETWORK_INVENTORY = REPO_ROOT / "docs" / "network-inventory.md"
BEGINNERS_GUIDE = REPO_ROOT / "docs" / "ExampleMusic_Beginners_Guide.md"

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
                # (see generate_inventory.py's own TMP handling) -- these docs correctly
                # document these by IP only, never a hostname string that doesn't exist.
            if not d.get("octet"):
                continue  # no fixed IP -- looser grouped Endpoints-style convention
            hostnames.add(d["hostname"])
        by_site[site] = hostnames
    return by_site


def load_raw_site_hostnames(devices_by_site, site):
    """Real devices.csv exception-row hostnames for a NON_STANDARD_SITES site (VRK/FRD) --
    straight from devices_by_site, bypassing load_real_devices_by_site()'s skip. These sites get
    no standard-slot synthesis, but real exception rows (EXAPVEVRK001, EXAPVEFRD001, ...) still
    exist and still belong in CLD's combined-section coverage below."""
    hostnames = set()
    for d in devices_by_site.get(site, []):
        if d.get("subnet_site"):
            continue
        if d["type"] == "TMP" or not d.get("octet"):
            continue
        hostnames.add(d["hostname"])
    return hostnames


def load_headered_sections(path: Path, level: int):
    """{SITE_CODE: section_text} for every '#'*level + ' <CODE> -- ...' header in path -- same
    pattern generate_network_diagrams.py's insert_topology_into_docs() already uses to scope a
    site's own content, parameterised by heading level since site-inventory.md uses '##' and
    network-inventory.md uses '####' for the equivalent per-site sections."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    marker = "#" * level
    headers = list(re.finditer(rf'^{marker} ([A-Z]{{3}}) — .*$', text, re.MULTILINE))
    sections = {}
    for i, m in enumerate(headers):
        site = m.group(1)
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        sections[site] = text[start:end]
    return sections


def bounded_section(path: Path, start_pattern: str, end_pattern: str) -> str:
    """Text between the first line matching start_pattern and the next line matching end_pattern
    (or end of file) -- for CLD's combined coverage, which isn't a per-site header at all in
    network-inventory.md/the Beginners Guide, just one shared block covering CLD (+VRK, +FRD)."""
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    m = re.search(start_pattern, text, re.MULTILINE)
    if not m:
        return ""
    rest = text[m.end():]
    end = re.search(end_pattern, rest, re.MULTILINE)
    return rest[:end.start()] if end else rest


RANGE_MENTION_RE = re.compile(r'(EXA[A-Z]{3}[A-Z]{3})(\d{3})[-–](\d{3})')


def expand_range_mentions(text: str) -> set:
    """Several docs deliberately group consecutive same-Type devices into one grouped mention
    instead of listing every hostname individually (e.g. 'EXAWAPFAL001-006', or two ranges in one
    line: 'EXAPHNFAL001-003 EXAPHNFAL006-007') -- both an en dash and a plain hyphen show up across
    the real docs. A literal substring check against every real hostname false-positives on every
    one of these (found live 2026-08-04, checking FAL specifically: EXAWAPFAL002-006 flagged
    'missing' when the doc already covers them via 'EXAWAPFAL001-006'). Expands every such mention
    in a block of text into the individual hostnames it implies, so those count as covered."""
    covered = set()
    for prefix, start, end in RANGE_MENTION_RE.findall(text):
        start_n, end_n = int(start), int(end)
        if end_n < start_n or end_n - start_n > 100:
            continue  # not a real range (or a false match on unrelated dashed digits) -- skip
        for n in range(start_n, end_n + 1):
            covered.add(f"{prefix}{n:03d}")
    return covered


def check_per_site(real_by_site, doc_sections, doc_label):
    """Returns (checked_count, findings) for one file's per-site header coverage."""
    checked = 0
    findings = []
    for site, hostnames in real_by_site.items():
        if site not in doc_sections:
            continue
        checked += 1
        section = doc_sections[site]
        covered_by_range = expand_range_mentions(section)
        missing = sorted(h for h in hostnames if h not in section and h not in covered_by_range)
        if missing:
            findings.append((site, missing))
    return checked, findings


def check_combined_section(hostnames, section_text, label):
    """Returns sorted missing hostnames from one bounded section (CLD's combined coverage)."""
    if not section_text:
        return None  # section not found at all -- different problem, not this check's job
    covered_by_range = expand_range_mentions(section_text)
    return sorted(h for h in hostnames if h not in section_text and h not in covered_by_range)


def main():
    real_by_site = load_real_devices_by_site()
    _, devices_by_site = gnd.load_all()

    all_findings = []

    # -- Per-site sections: site-inventory.md ("##") and network-inventory.md ("####") --
    site_inv_sections = load_headered_sections(SITE_INVENTORY, level=2)
    net_inv_sections = load_headered_sections(NETWORK_INVENTORY, level=4)

    checked_site_inv, findings_site_inv = check_per_site(real_by_site, site_inv_sections, "site-inventory.md")
    checked_net_inv, findings_net_inv = check_per_site(real_by_site, net_inv_sections, "network-inventory.md")

    print(f"Checked {checked_site_inv} site(s) with a docs/site-inventory.md section, "
          f"{checked_net_inv} with a docs/network-inventory.md section, against their real "
          f"device list (generate_inventory.py).")

    for site, missing in findings_site_inv:
        all_findings.append(f"docs/site-inventory.md, {site}: {', '.join(missing)}")
    for site, missing in findings_net_inv:
        all_findings.append(f"docs/network-inventory.md, {site}: {', '.join(missing)}")

    # -- CLD's combined coverage: CLD (+VRK, +FRD) real hostnames against the shared sections --
    cld_vrk_hostnames = (
        real_by_site.get("CLD", set())
        | load_raw_site_hostnames(devices_by_site, "VRK")
    )
    cld_vrk_frd_hostnames = cld_vrk_hostnames | load_raw_site_hostnames(devices_by_site, "FRD")

    net_inv_cloud_section = bounded_section(
        NETWORK_INVENTORY,
        r'^## Cloud / Provisioning Network.*$',
        r'^## .*$',
    )
    missing = check_combined_section(cld_vrk_frd_hostnames, net_inv_cloud_section,
                                      "network-inventory.md's Cloud/Provisioning section")
    if missing:
        all_findings.append(
            f"docs/network-inventory.md, Cloud/Provisioning section (CLD+VRK+FRD): "
            f"{', '.join(missing)}"
        )
    elif missing is None:
        all_findings.append(
            "docs/network-inventory.md: 'Cloud / Provisioning Network' section not found at all "
            "-- structure may have changed, this check needs updating"
        )

    guide_41_section = bounded_section(
        BEGINNERS_GUIDE, r'^### 4\.1 CLD.*$', r'^### .*$',
    )
    missing = check_combined_section(cld_vrk_hostnames, guide_41_section,
                                      "Beginners Guide §4.1 (CLD+VRK)")
    if missing:
        all_findings.append(f"docs/ExampleMusic_Beginners_Guide.md §4.1 (CLD+VRK): {', '.join(missing)}")
    elif missing is None:
        all_findings.append(
            "docs/ExampleMusic_Beginners_Guide.md: '4.1 CLD' section not found at all -- "
            "structure may have changed, this check needs updating"
        )

    guide_42_section = bounded_section(
        BEGINNERS_GUIDE, r'^### 4\.2 FRD.*$', r'^### .*$',
    )
    frd_only = load_raw_site_hostnames(devices_by_site, "FRD")
    missing = check_combined_section(frd_only, guide_42_section, "Beginners Guide §4.2 (FRD)")
    if missing:
        all_findings.append(f"docs/ExampleMusic_Beginners_Guide.md §4.2 (FRD): {', '.join(missing)}")
    elif missing is None:
        all_findings.append(
            "docs/ExampleMusic_Beginners_Guide.md: '4.2 FRD' section not found at all -- "
            "structure may have changed, this check needs updating"
        )

    if all_findings:
        print(f"\n{len(all_findings)} informational finding(s) -- device(s) missing from their own "
              f"documented section, or a tracked section that's gone missing entirely (Tier 2 -- "
              f"confirm by hand; --strict fails on this):")
        for f in all_findings:
            print(f"  - {f}")
    else:
        print("\nEvery real, addressed device is mentioned somewhere in its own site's/section's "
              "coverage across site-inventory.md, network-inventory.md, and the Beginners Guide's "
              "CLD/VRK/FRD sections.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
