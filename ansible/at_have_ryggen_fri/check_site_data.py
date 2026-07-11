#!/usr/bin/env python3
"""
check_site_data.py -- part of at_have_ryggen_fri.

Two checks against benarbejde/sites.csv (the estate's single source of
truth for site identity/addressing), run fresh against whatever's
currently committed there every time this harness runs -- so a change to
sites.csv (or a doc that goes stale relative to it) is caught the next
run, not just the day someone happened to audit by hand:

1. SITE-CODE COVERAGE: every Site code in sites.csv appears at least once,
   as a whole word, somewhere in docs/*.md (git-tracked, excluding
   docs/inventory/old/ -- archived/superseded, not live documentation).
   Catches a new site added to sites.csv that never made it into any doc.

2. OCTET CONSISTENCY: for every docs/*.md line that contains exactly one
   recognised site code AND at least one literal 192.168.<N>.<M> or
   172.16.<N>.<M> address, N must match that site's real third octet from
   sites.csv's Subnet column (FRD is the one 172.16.x.x site; everything
   else is 192.168.x.x). Lines with more than one recognised site code are
   skipped for this check -- too ambiguous to know which address belongs
   to which code -- but still count toward check 1's coverage. Templated
   placeholders (`192.168.<site-octet>.10`, `192.168.X.10`, etc.) never
   match the literal-IP regex, so they're skipped automatically, not
   flagged.

   This is deliberately narrower than "every subnet/gateway/DC/FW/phone
   number matches exactly" (phone numbers in sites.csv are themselves
   templated placeholders -- "+44 1224 496 0xxx" -- there is no real value
   to check them against). Octet consistency is the check that actually
   catches the class of error found repeatedly by hand in this repo (a
   site's address quoted under the wrong site code, or a site code that
   doesn't exist in sites.csv at all used as if it did) -- see the
   2026-07-11 ABR/GAA findings this check was built to generalise.

Exit code: 0 if every site code is covered and no octet mismatch is found,
1 otherwise.
"""
import csv
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SITES_CSV = REPO_ROOT / "benarbejde" / "sites.csv"
DOCS_DIR = REPO_ROOT / "docs"

EXCLUDED_PREFIXES = ("inventory/old/",)

IPV4_RE = re.compile(r"\b(192\.168|172\.16)\.(\d{1,3})\.(\d{1,3})\b")


def load_sites():
    sites = {}
    with SITES_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = row["Site"].strip()
            subnet = row["Subnet"].strip()
            m = re.match(r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.\d{1,3}/\d+", subnet)
            octet = int(m.group(3)) if m else None
            base = f"{m.group(1)}.{m.group(2)}" if m else None
            sites[code] = {"octet": octet, "base": base, "row": row}
    return sites


def git_tracked_docs():
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z", "--", "docs/*.md"],
        capture_output=True, check=True,
    )
    paths = [REPO_ROOT / p for p in result.stdout.decode("utf-8").split("\0") if p]
    return [p for p in paths
            if not any(p.relative_to(DOCS_DIR).as_posix().startswith(pfx) for pfx in EXCLUDED_PREFIXES)]


def main():
    sites = load_sites()
    code_re = re.compile(r"\b(" + "|".join(re.escape(c) for c in sites) + r")\b")

    docs = git_tracked_docs()
    all_text = ""
    mismatches = []

    for doc in docs:
        text = doc.read_text(encoding="utf-8", errors="replace")
        all_text += text
        for lineno, line in enumerate(text.splitlines(), start=1):
            # A trailing "# CODE ..." comment (e.g. annotating which DC's IP a
            # command targets) is naming something *about* that site, not
            # asserting an address belongs to it -- only look at the code
            # before any '#', matching how a reader would actually parse it.
            code_scope = line.split("#", 1)[0]
            codes_here = set(code_re.findall(code_scope))
            if len(codes_here) != 1:
                continue
            code = next(iter(codes_here))
            ips = IPV4_RE.findall(line)
            if not ips:
                continue
            if len(ips) > 3:
                continue  # a line asserting >3 literal IPs is virtually always a multi-site
                          # reference/command (e.g. a sed AllowedIPs edit folding in every
                          # spoke's subnet) rather than a claim about the one site code found --
                          # too ambiguous to attribute any single IP to it safely.
            if code == "CLD":
                continue  # CLD is dual-homed (LAN 192.168.69.x + vRACK 192.168.139.x) -- see
                          # docs/inventory/EXADNSVRK001-dns.md's "FWL WAN IP (prov.)" section;
                          # a single per-site octet can't represent it, too many legitimate
                          # false positives to check usefully.
            expected_octet = sites[code]["octet"]
            expected_base = sites[code]["base"]
            for base, o2, o3 in ips:
                if base != expected_base:
                    continue  # different address family entirely (e.g. a 172.16 line unrelated to FRD) -- not this site's concern
                if int(o2) == 139 and base == "192.168" and int(o3) == expected_octet:
                    continue  # every site's firewall also has a WAN IP on the provisioning
                              # network at 192.168.139.<site's own octet> -- documented,
                              # deliberate convention, see EXADNSVRK001-dns.md. Not a mismatch.
                if int(o2) != expected_octet:
                    mismatches.append((doc, lineno, code, f"{base}.{o2}.{o3}", expected_base, expected_octet))

    missing = [code for code in sites if not re.search(r"\b" + re.escape(code) + r"\b", all_text)]

    print(f"Loaded {len(sites)} site(s) from benarbejde/sites.csv.")
    print(f"Scanned {len(docs)} git-tracked docs/*.md file(s) (excluding docs/inventory/old/).")

    ok = True

    if missing:
        ok = False
        print(f"\n{len(missing)} site code(s) from sites.csv not found anywhere in docs/*.md:")
        for code in sorted(missing):
            row = sites[code]["row"]
            print(f"  {code} ({row['City']}, {row['Country']})")
    else:
        print("Every site code in sites.csv appears somewhere in docs/*.md.")

    if mismatches:
        ok = False
        print(f"\n{len(mismatches)} octet mismatch(es) (site code and IP on the same line disagree with sites.csv):")
        for doc, lineno, code, ip, expected_base, expected_octet in mismatches:
            rel = doc.relative_to(REPO_ROOT)
            print(f"  {rel}:{lineno}: [{code}] uses {ip}, but sites.csv says {code} is "
                  f"{expected_base}.{expected_octet}.x")
    else:
        print("No octet mismatches found.")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
