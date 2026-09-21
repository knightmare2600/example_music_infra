#!/usr/bin/env python3
"""
check_breakglass_zone_file_collisions.py -- part of at_have_ryggen_fri.

Found live 2026-09-21, building EXADNSFRD001: bindme.sh's per-site reverse-zone
generation writes to a file path derived from each site's own subnet (its first
three octets) -- e.g. db.172.16.124 for FRD, db.192.168.76 for FAL. VRK's own
subnet (192.168.139.0/24) is numerically identical to the provisioning network,
which already has its own separately-generated, earlier-written zone file at
that exact path (section 9a) -- but the per-site loop only excluded CLD, never
VRK, so every build silently truncated and overwrote the provisioning zone's
real ancillary-hosts/FWL-WAN content with VRK's own generic per-site data.
`named-checkzone`/`rndc zonestatus` both reported the zone loading cleanly with
no errors -- the file was syntactically valid, just not what named.conf.local's
stanza actually needed. Only `dig -x` against a real, previously-working PTR
entry surfaced it, returning authoritative NXDOMAIN. This bug predated the
2026-09-21 FRD work entirely -- it would have silently hit every single
build/rebuild of EXADNSVRK001 itself too.

A purely data-driven check (sites.csv alone) would NOT catch this: VRK sharing
its subnet with the provisioning network is correct, intentional data, by
design -- the bug was that bindme.sh's own exclusion logic didn't account for
it. This check instead cross-references sites.csv against bindme.sh's actual
per-site reverse-zone loops (identified structurally, via their own
`db.${net3}` file-path construction -- not by matching comment wording, which
can drift) and verifies every site whose subnet prefix collides with a
reserved, non-per-site zone path is actually excluded from every one of them.

RESERVED_NET3 encodes bindme.sh's two known reserved paths and which site is
*expected* to collide with each (VRK "reserving" the provisioning network's own
prefix, CLD "reserving" its own dedicated LAN zone's prefix -- both correct,
intentional design). A collision from any OTHER, unexpected site would also be
a real problem (two real sites sharing a subnet prefix) and is flagged
separately as a hard failure regardless of bindme.sh's exclusion lists.

Exit code: 1 if any expected-reserved-site is missing from one of bindme.sh's
own per-site reverse-zone loops, or if any two real sites (or a site not on the
reserved list) share a subnet prefix; 0 otherwise.
"""
import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITES_CSV = REPO_ROOT / "benarbejde" / "sites.csv"
BINDME_SH = REPO_ROOT / "bootstrap" / "web" / "provision" / "bindme.sh"

# net3 -> site that is EXPECTED to collide with this reserved, non-per-site zone path.
RESERVED_NET3 = {
    "192.168.139": "VRK",  # provisioning network zone (section 9a)
    "192.168.69": "CLD",  # CLD LAN zone (section 9c)
}

SORTED_SITES_LOOP_RE = re.compile(r'for site in "\$\{SORTED_SITES\[@\]\}"; do')
CONTINUE_RE = re.compile(r'\[\[\s*"\$\{site\}"\s*==\s*(.+?)\s*\]\]\s*&&\s*continue')
SITE_CODE_RE = re.compile(r'"([A-Z]{2,4})"')
NET3_FILE_RE = re.compile(r'/etc/bind/db\.\$\{net3\}')


def net3_of(subnet: str) -> str:
    return ".".join(subnet.split("/")[0].split(".")[:3])


def load_sites() -> dict:
    """Mirrors bindme.sh's own load_sites_csv(): skips BRD (legacy alias for BER, BER
    already covers it -- bindme.sh's own comment) at load time, same as the real script,
    so this check's site set matches what SORTED_SITES actually contains."""
    rows = list(csv.DictReader(SITES_CSV.open(newline="", encoding="utf-8")))
    sites = {}
    for r in rows:
        site = (r.get("Site") or "").strip()
        subnet = (r.get("Subnet") or "").strip()
        if not site or subnet in ("", "N/A") or site == "BRD":
            continue
        sites[site] = net3_of(subnet)
    return sites


def find_per_site_zone_loops(text: str):
    """
    Yields (loop_start_line, excluded_site_codes) for every "for site in
    SORTED_SITES" loop that structurally writes a per-site file at
    /etc/bind/db.${net3} -- identified by that literal construction appearing
    inside the loop body, not by matching comment text (which can drift).
    """
    lines = text.splitlines()
    starts = [i for i, l in enumerate(lines) if SORTED_SITES_LOOP_RE.search(l)]
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        block = "\n".join(lines[start:end])
        if not NET3_FILE_RE.search(block):
            continue  # not one of the file-writing loops -- e.g. forward zone append loops
        excluded = set()
        for m in CONTINUE_RE.finditer(block):
            excluded.update(SITE_CODE_RE.findall(m.group(1)))
        yield start + 1, excluded


def main():
    sites = load_sites()
    bindme_text = BINDME_SH.read_text(encoding="utf-8")

    failures = []

    # 1. Data-level collisions: any two real sites sharing a subnet prefix, or a
    #    site landing on a reserved prefix that ISN'T the site expected to.
    by_net3 = {}
    for site, net3 in sites.items():
        by_net3.setdefault(net3, []).append(site)

    for net3, site_list in sorted(by_net3.items()):
        expected = RESERVED_NET3.get(net3)
        if expected and expected not in site_list:
            failures.append(
                f"Reserved prefix {net3} (bindme.sh's own {'provisioning network' if expected == 'VRK' else 'CLD LAN'} "
                f"zone) is expected to belong to {expected}, but sites.csv doesn't have {expected} on that prefix "
                f"at all -- check for a stale RESERVED_NET3 mapping in this check, or a real sites.csv change."
            )
        # A collision is >1 real site sharing this exact prefix -- for a reserved prefix,
        # the one EXPECTED site is normal/fine; only EXTRA sites on top of it (or on a
        # non-reserved prefix at all) are the actual problem.
        if len(site_list) > 1:
            failures.append(
                f"Subnet prefix {net3} is shared by multiple sites.csv site(s): "
                f"{', '.join(sorted(site_list))}. Two sites sharing a /24 prefix means "
                f"bindme.sh's per-site reverse-zone file (db.{net3}) would collide between them."
            )

    reserved_sites_needed = set(RESERVED_NET3.values()) & set(sites)

    # 2. Code-level check: every per-site zone-file loop in bindme.sh must exclude
    #    every reserved site actually present in sites.csv.
    loops_found = list(find_per_site_zone_loops(bindme_text))
    print(
        f"Checked sites.csv ({len(sites)} sites) against bindme.sh's "
        f"{len(loops_found)} per-site reverse-zone file-writing loop(s) for "
        f"{', '.join(sorted(reserved_sites_needed))} exclusion."
    )

    if not loops_found:
        failures.append(
            "No per-site reverse-zone loop (a \"for site in ${SORTED_SITES[@]}\" block containing "
            "/etc/bind/db.${net3}) found in bindme.sh at all -- either the script was restructured "
            "and this check needs updating, or the reverse-zone generation itself is missing."
        )

    for line_no, excluded in loops_found:
        missing = reserved_sites_needed - excluded
        if missing:
            failures.append(
                f"bindme.sh:{line_no}: per-site reverse-zone loop excludes {sorted(excluded) or '(nothing)'} "
                f"but not {sorted(missing)} -- {', '.join(sorted(missing))} share{'s' if len(missing) == 1 else ''} "
                f"a subnet prefix with a reserved, non-per-site zone file "
                f"(see this check's own RESERVED_NET3), so this loop will silently truncate and overwrite "
                f"that reserved zone's real content the same way it did for VRK/the provisioning zone,"
                f" 2026-09-21."
            )

    if failures:
        print(f"\n{len(failures)} FAILURE(s):")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("No subnet-prefix collisions found; every reserved site is excluded from every "
          "per-site reverse-zone file-writing loop.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
