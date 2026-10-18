#!/usr/bin/env python3
"""
check_domain_consistency.py -- part of at_have_ryggen_fri.

benarbejde/ad_forest.json's own comment claims every consumer derives domain_fqdn
from it rather than hardcoding "jukebox.internal" -- "no other file should need
touching" if it were ever renamed. A repo-wide audit (Robert's ask, 2026-10-18) found
that claim mostly true, but with real exceptions in two categories this check exists
to cover going forward:

  1. Structured JSON data with the domain baked into literal field VALUES
     (ad_computers.json/ad_users.json/ad_groups.json/extracted_credentials.json) --
     genuinely can't be Jinja-templated (these are static data files consumed by
     PowerShell/manual inspection, not Ansible-rendered), so the fix isn't "make it a
     variable", it's "verify these records still agree with the one real source of
     truth".

  2. Static PXE/install-time artifacts (menu.ipxe, bootstrap.ipxe, the Debian preseed
     .seed files, the Proxmox autoinstall .toml files) -- served directly by the boot
     HTTP/TFTP server BEFORE Ansible ever runs, so there's no Jinja-rendering step in
     that part of the pipeline to hook into at all.

DELIBERATELY DOES NOT consult benarbejde/parse_tdf.py or the source .tdf file --
Robert's explicit instruction, 2026-10-18: "stop using parse_tdf.py because it's wrong
and legacy code... the harness needs to do it WITHOUT consulting parse_tdf.py OR the
actual tdf file." Every check below reads the real, CURRENT file content directly --
the same data Ansible/other consumers actually use -- not a freshly-regenerated
comparison. parse_tdf.py is slated for retirement once this check is confirmed working.

Read-only. Never writes, never suggests a specific replacement value beyond naming
what was found vs. what ad_forest.json currently says -- the actual rewrite (if any
drift is ever found) is Robert's own call, a separate tool, never automatic.

Checks:
  A. ad_computers.json -- every record's DNSHostName suffix + ad_ou's trailing
     DC=... form.
  B. ad_users.json -- UserPrincipalName/Email suffix + ad_ou/ad_band_parent's
     trailing DC=... form.
  C. ad_groups.json -- Email suffix.
  D. extracted_credentials.json -- an EXPLICITLY ENUMERATED list of entries (matched
     by their own stable "hostname" key, not a fragile array index), NOT a generic
     scan of every url/string field. This file genuinely mixes internal service URLs
     with real external ones (confirmed live, 2026-10-18: one entry's own url field
     is a third-party PAN-OS cheat-sheet PDF link) -- a blind "every url must contain
     the domain" rule would false-positive on exactly that kind of legitimate
     external reference.
  E. PXE/install-time static artifacts -- an EXPLICITLY ENUMERATED list of
     (file, regex) pairs, never a blind grep-replace across the whole repo (which
     would also flag docs/comments as false positives).

Any new consumer that embeds this domain as literal data needs adding to the
relevant list above by hand -- this check's own coverage is exactly what's
enumerated, not a generic "find every domain-shaped string anywhere" scan.
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"


def load_canonical_domain(problems):
    try:
        forest = json.loads((BENARBEJDE / "ad_forest.json").read_text())
        domain = forest.get("domain_fqdn")
        if not domain:
            problems.append("ad_forest.json: domain_fqdn field is missing or empty")
            return None
        return domain
    except Exception as e:
        problems.append(f"ad_forest.json: could not load/parse -- {e}")
        return None


def dc_form(domain):
    """'jukebox.internal' -> 'DC=jukebox,DC=internal' -- same LDAP DN convention
    rudderme.sh's own comment documents (ad_ou/ad_band_parent use this form)."""
    return "DC=" + ",DC=".join(domain.split("."))


def check_ad_computers(problems, domain, dc_suffix):
    path = BENARBEJDE / "ad_computers.json"
    try:
        records = json.loads(path.read_text())
    except Exception as e:
        problems.append(f"ad_computers.json: could not load/parse -- {e}")
        return
    for r in records:
        name = r.get("Name") or r.get("SamAccountName") or "?"
        dns = r.get("DNSHostName") or ""
        if dns and not dns.lower().endswith("." + domain.lower()):
            problems.append(
                f"ad_computers.json: {name}'s DNSHostName ('{dns}') doesn't end "
                f"in '.{domain}' (ad_forest.json's current domain_fqdn)"
            )
        ad_ou = r.get("ad_ou") or ""
        if ad_ou and not ad_ou.endswith(dc_suffix):
            problems.append(
                f"ad_computers.json: {name}'s ad_ou ('{ad_ou}') doesn't end in "
                f"'{dc_suffix}' (ad_forest.json's current domain_fqdn)"
            )


def check_ad_users(problems, domain, dc_suffix):
    path = BENARBEJDE / "ad_users.json"
    try:
        records = json.loads(path.read_text())
    except Exception as e:
        problems.append(f"ad_users.json: could not load/parse -- {e}")
        return
    for r in records:
        name = r.get("Name") or r.get("SamAccountName") or "?"
        for field in ("UserPrincipalName", "Email"):
            val = r.get(field) or ""
            if val and "@" in val and not val.lower().endswith("@" + domain.lower()):
                problems.append(
                    f"ad_users.json: {name}'s {field} ('{val}') doesn't end in "
                    f"'@{domain}' (ad_forest.json's current domain_fqdn)"
                )
        for field in ("ad_ou", "ad_band_parent"):
            val = r.get(field) or ""
            if val and not val.endswith(dc_suffix):
                problems.append(
                    f"ad_users.json: {name}'s {field} ('{val}') doesn't end in "
                    f"'{dc_suffix}' (ad_forest.json's current domain_fqdn)"
                )


def check_ad_groups(problems, domain):
    path = BENARBEJDE / "ad_groups.json"
    try:
        records = json.loads(path.read_text())
    except Exception as e:
        problems.append(f"ad_groups.json: could not load/parse -- {e}")
        return
    for r in records:
        name = r.get("Name") or "?"
        val = r.get("Email") or ""
        if val and "@" in val and not val.lower().endswith("@" + domain.lower()):
            problems.append(
                f"ad_groups.json: {name}'s Email ('{val}') doesn't end in "
                f"'@{domain}' (ad_forest.json's current domain_fqdn)"
            )


# See module docstring, section D, for why this is an explicit list keyed by each
# entry's own stable "hostname" field, not a generic scan.
CREDENTIALS_DOMAIN_ENTRIES = [
    "EXARMMCLD001-django-admin",
    "EXARMMCLD001-meshcentral-admin",
]


def check_extracted_credentials(problems, domain):
    path = BENARBEJDE / "extracted_credentials.json"
    try:
        records = json.loads(path.read_text())
    except Exception as e:
        problems.append(f"extracted_credentials.json: could not load/parse -- {e}")
        return
    by_hostname = {r.get("hostname"): r for r in records if isinstance(r, dict)}
    for key in CREDENTIALS_DOMAIN_ENTRIES:
        entry = by_hostname.get(key)
        if entry is None:
            problems.append(
                f"extracted_credentials.json: expected entry '{key}' not found at "
                f"all (this check's own CREDENTIALS_DOMAIN_ENTRIES list may need "
                f"updating if it was deliberately renamed/removed)"
            )
            continue
        url = entry.get("url") or ""
        if url and domain.lower() not in url.lower():
            problems.append(
                f"extracted_credentials.json: '{key}'s url ('{url}') doesn't "
                f"contain '{domain}' (ad_forest.json's current domain_fqdn)"
            )


# See module docstring, section E -- explicitly enumerated (file, regex-with-one-
# capture-group) pairs. Every regex verified empirically against the real file
# content before being added here, not assumed to work.
PXE_ARTIFACT_PATTERNS = [
    ("bootstrap/web/menu.ipxe", r"domain=([\w.-]+)"),
    ("bootstrap/web/bootstrap.ipxe", r"set boot-domain\s+([\w.-]+)"),
    ("bootstrap/web/debian/lvm-bios-bookworm.seed", r"d-i netcfg/get_domain string ([\w.-]+)"),
    ("bootstrap/web/debian/lvm-bios-trixie.seed", r"d-i netcfg/get_domain string ([\w.-]+)"),
    ("bootstrap/web/debian/lvm-efi-bookworm.seed", r"d-i netcfg/get_domain string ([\w.-]+)"),
    ("bootstrap/web/debian/lvm-efi-trixie.seed", r"d-i netcfg/get_domain string ([\w.-]+)"),
    ("bootstrap/web/proxmox/VRK-answer.toml", r'fqdn\s*=\s*"[^".]+\.([\w.-]+)"'),
    ("bootstrap/web/proxmox/VRK-answer.toml", r'mailto\s*=\s*"[^@"]+@([\w.-]+)"'),
    ("bootstrap/web/proxmox/VRK-degraded.toml", r'fqdn\s*=\s*"[^".]+\.([\w.-]+)"'),
    ("bootstrap/web/proxmox/VRK-degraded.toml", r'mailto\s*=\s*"[^@"]+@([\w.-]+)"'),
    ("bootstrap/web/proxmox/FRD-answer.toml", r'fqdn\s*=\s*"[^".]+\.([\w.-]+)"'),
    ("bootstrap/web/proxmox/FRD-answer.toml", r'mailto\s*=\s*"[^@"]+@([\w.-]+)"'),
    ("bootstrap/web/proxmox/FRD-degraded.toml", r'fqdn\s*=\s*"[^".]+\.([\w.-]+)"'),
    ("bootstrap/web/proxmox/FRD-degraded.toml", r'mailto\s*=\s*"[^@"]+@([\w.-]+)"'),
]


def check_pxe_artifacts(problems, domain):
    for rel_path, pattern in PXE_ARTIFACT_PATTERNS:
        full_path = REPO_ROOT / rel_path
        if not full_path.is_file():
            problems.append(
                f"{rel_path}: file not found (this check's own PXE_ARTIFACT_PATTERNS "
                f"list may be stale)"
            )
            continue
        content = full_path.read_text()
        matches = set(re.findall(pattern, content))
        if not matches:
            problems.append(
                f"{rel_path}: pattern {pattern!r} found no match at all (file format "
                f"may have changed -- this check's own pattern may need updating)"
            )
            continue
        for m in matches:
            if m.lower() != domain.lower():
                problems.append(
                    f"{rel_path}: found domain '{m}', expected '{domain}' "
                    f"(ad_forest.json's current domain_fqdn)"
                )


def main():
    problems = []
    domain = load_canonical_domain(problems)

    computers = users = groups = 0
    if domain:
        dc_suffix = dc_form(domain)
        try:
            computers = len(json.loads((BENARBEJDE / "ad_computers.json").read_text()))
        except Exception:
            pass
        try:
            users = len(json.loads((BENARBEJDE / "ad_users.json").read_text()))
        except Exception:
            pass
        try:
            groups = len(json.loads((BENARBEJDE / "ad_groups.json").read_text()))
        except Exception:
            pass
        check_ad_computers(problems, domain, dc_suffix)
        check_ad_users(problems, domain, dc_suffix)
        check_ad_groups(problems, domain)
        check_extracted_credentials(problems, domain)
        check_pxe_artifacts(problems, domain)

    print(
        f"Checked ad_forest.json's domain_fqdn ('{domain}') against "
        f"{computers} ad_computers.json record(s), {users} ad_users.json record(s), "
        f"{groups} ad_groups.json record(s), {len(CREDENTIALS_DOMAIN_ENTRIES)} "
        f"extracted_credentials.json entry/entries, and {len(PXE_ARTIFACT_PATTERNS)} "
        f"PXE/install-time artifact pattern(s)."
    )

    if problems:
        print(f"\n{len(problems)} DOMAIN CONSISTENCY PROBLEM(S):")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("No domain inconsistencies found across any enumerated file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
