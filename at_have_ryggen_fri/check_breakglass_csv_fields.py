#!/usr/bin/env python3
"""
check_breakglass_csv_fields.py -- part of at_have_ryggen_fri.

Robert, 2026-08-29, after a real live failure: EXAFWLCOV001's site-octet
derivation via firewallme.sh (the documented break-glass path) came out
blank -- WAN IP "192.168.139.", WireGuard tunnel "10.0..1". Root cause,
confirmed by direct reproduction: firewallme.sh's load_sites_csv() reads
benarbejde/sites.csv with a fixed, positional `while IFS=',' read -r
<field names...>` line written for an older, 13-column schema. Province/
OfficeName/Street/PostalCode were added to sites.csv between CountryCode
and Subnet at some point after that read line was last touched, and every
field from Subnet onward has been silently reading the WRONG column since
-- not just for COV, for every site (the WireGuard bomb-out Robert also
hit was the same bug again, one hop over: a spoke derives its hub's LAN/
tunnel subnets from CLD's own row through the identical broken read).
The exact same stale field list, byte-for-byte, was also found in
bindme.sh/rudderme.sh/ansibleme.sh -- all four were fixed the same day.

This check exists so that class of drift can never silently reappear.
sites.csv is allowed to gain columns -- that's normal, expected schema
evolution, not a mistake -- but every break-glass script's own copy of
the column layout has to be caught up whenever it does, and nothing
before this enforced that.

What it does:
1. Reads benarbejde/sites.csv's real header row, in order.
2. Scans every git-tracked *.sh file under bootstrap/web/ for a
   `while IFS=',' read -r <names...>` line that also references
   sites.csv somewhere in the same file (scoped narrowly on purpose --
   this repo has no other comma-split read loop shaped like this one,
   confirmed by grep before writing this check; a genuinely unrelated
   future one would need to avoid this exact shape to not be swept in,
   which is an acceptable false-positive direction to err in for a
   check like this).
3. For every KNOWN_FIELDS entry (the script's own lowercase/abbreviated
   variable name -> the real CSV column name it's supposed to hold) that
   appears in that script's field list, confirms its position in the
   list matches that column's real position in sites.csv's header.
   A script is free to only name a subset of columns (some don't
   capture Province/OfficeName/Street/PostalCode at all, `_rest`-
   discarding them via the overflow catch-all) -- only named fields are
   checked; an unnamed/skipped column is not itself a finding.

Exit code: 0 if every discovered break-glass script's named fields
still line up with sites.csv's real current column order, 1 otherwise.
"""
import csv
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITES_CSV = REPO_ROOT / "benarbejde" / "sites.csv"
SCAN_DIR = REPO_ROOT / "bootstrap" / "web"

# script variable name (as used in the `read -r ...` field list) -> the
# real benarbejde/sites.csv header name it's meant to capture. Every
# break-glass script found using this pattern so far (firewallme.sh,
# bindme.sh, rudderme.sh, ansibleme.sh) uses this same lowercase/
# abbreviated naming -- add to this map if a future script introduces a
# genuinely new column/name pairing, don't just silence a real mismatch.
KNOWN_FIELDS = {
    "site": "Site",
    "city": "City",
    "country": "Country",
    "cc": "CountryCode",
    "province": "Province",
    "officename": "OfficeName",
    "street": "Street",
    "postalcode": "PostalCode",
    "subnet": "Subnet",
    "gateway": "Gateway",
    "dc": "DC",
    "fw": "FW",
    "landline": "Landline",
    "mobile": "Mobile",
    "tz": "Timezone",
    "ansible_region": "AnsibleRegion",
    "entity": "Entity",
}

# Matches `while IFS=',' read -r <names...>` (single or double-quoted IFS
# value), capturing everything up to the first character that can't be
# part of a bash identifier list (backslash-continuation, `||`, or a
# genuine end-of-statement). Applied after collapsing backslash line
# continuations, so it works whether the real file wrote this on one
# physical line (firewallme.sh) or split across two with `\` (the other
# three).
READ_LINE_RE = re.compile(
    r"while\s+IFS=['\"],['\"]\s+read\s+-r\s+([A-Za-z0-9_ \t]+?)(?:\s*\\|\s*\|\|)"
)


def load_header():
    with SITES_CSV.open(encoding="utf-8") as f:
        return next(csv.reader(f))


def git_tracked_shell_scripts():
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z", "--", "bootstrap/web/*.sh",
         "bootstrap/web/**/*.sh"],
        capture_output=True, check=True,
    )
    paths = sorted(set(
        REPO_ROOT / p for p in result.stdout.decode("utf-8").split("\0") if p
    ))
    return paths


def find_read_field_lists(text):
    """Yield (line_number, [field_names]) for every matching read line in text."""
    normalised = text.replace("\\\n", " ")
    # Map offsets in the normalised text back to line numbers in the original
    # by counting newlines consumed up to each match start in a re-walk of
    # the original text alongside the normalised one is fragile; simpler and
    # robust enough here: re-run the regex against the original text too,
    # falling back to normalised-only line counting when a continuation was
    # involved (multi-line reads only span two lines in every real script
    # checked, and none of the field names themselves contain newlines).
    for m in re.finditer(READ_LINE_RE, normalised):
        fields = m.group(1).split()
        # Recover an approximate line number by finding this read line's
        # start in the ORIGINAL text (pre-normalisation) -- searching for the
        # first field name after "read -r" is enough to locate it uniquely
        # in every real file checked.
        anchor = f"read -r {fields[0]}"
        idx = text.find(anchor)
        line_no = text.count("\n", 0, idx) + 1 if idx != -1 else 0
        yield line_no, fields


def main():
    header = load_header()
    header_index = {name: i for i, name in enumerate(header)}

    scripts = git_tracked_shell_scripts()
    scanned = []
    findings = []

    for path in scripts:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "sites.csv" not in text:
            continue
        matches = list(find_read_field_lists(text))
        if not matches:
            continue
        rel = path.relative_to(REPO_ROOT)
        scanned.append(rel)
        for line_no, fields in matches:
            for pos, name in enumerate(fields):
                real_col = KNOWN_FIELDS.get(name)
                if real_col is None:
                    continue  # not a field this check knows how to verify (e.g. _rest/entity overflow) -- not itself a finding
                if real_col not in header_index:
                    findings.append((
                        rel, line_no, name,
                        f"maps to sites.csv column '{real_col}', which doesn't exist in the "
                        f"current header at all"
                    ))
                    continue
                expected_pos = header_index[real_col]
                if pos != expected_pos:
                    findings.append((
                        rel, line_no, name,
                        f"read at position {pos} but sites.csv's real '{real_col}' column "
                        f"is at position {expected_pos} -- field list is out of sync with "
                        f"the current header"
                    ))

    print(f"sites.csv header ({len(header)} columns): {', '.join(header)}")
    print(f"Scanned {len(scripts)} git-tracked *.sh file(s) under bootstrap/web/, "
          f"{len(scanned)} reference sites.csv with a matching read -r field list:")
    for rel in scanned:
        print(f"  {rel}")

    if findings:
        print(f"\n{len(findings)} field-position mismatch(es):")
        for rel, line_no, name, detail in findings:
            print(f"  {rel}:{line_no}: field '{name}' {detail}")
        return 1

    print("\nEvery discovered break-glass script's named sites.csv fields are in sync "
          "with the real current header.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
