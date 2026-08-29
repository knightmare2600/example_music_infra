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

Fattened up the same day with a second, independent check after a
follow-up finding: BRT and MIL's rows each had a genuinely
comma-containing value (a Street address) inside proper CSV double
quotes -- valid CSV, completely invisible to a real parser, but every
break-glass script's `IFS=','` read has no concept of quoting at all
and splits on that comma anyway, corrupting every field from that point
onward for that one row, regardless of whether the field LIST itself is
correctly positioned. MIL's instance was fixed by removing the comma
from the data (Robert's call, once the tradeoff -- fix the data, or
build a real CSV-quote-aware parser that also needs a dependency not
guaranteed present this early in a fresh install -- was laid out); BRT's
was deliberately left as-is. This check's second half exists so a
*future* site with a comma in any field is caught before it ever reaches
a live break-glass run, the same way the first half now catches a future
schema change before it does.

What it does:
1. Reads benarbejde/sites.csv's real header row, in order.
2. FIELD ALIGNMENT: scans every git-tracked *.sh file under bootstrap/web/
   for a `while IFS=',' read -r <names...>` line that also references
   sites.csv somewhere in the same file (scoped narrowly on purpose --
   this repo has no other comma-split read loop shaped like this one,
   confirmed by grep before writing this check; a genuinely unrelated
   future one would need to avoid this exact shape to not be swept in,
   which is an acceptable false-positive direction to err in for a
   check like this). For every KNOWN_FIELDS entry (the script's own
   lowercase/abbreviated variable name -> the real CSV column name it's
   supposed to hold) that appears in that script's field list, confirms
   its position in the list matches that column's real position in
   sites.csv's header. A script is free to only name a subset of columns
   -- only named fields are checked; an unnamed/skipped column is not
   itself a finding.
3. NAIVE-SPLIT SAFETY: independent of any script, checks sites.csv
   itself. For every data row, compares the field count from a real,
   quote-aware CSV parse against the field count from a naive
   `line.split(',')` -- the exact operation every break-glass script's
   `IFS=','` read performs. Any row where these disagree contains a
   properly-quoted comma that will corrupt every break-glass script's
   parse of that row, no matter how correct the field list itself is.

Exit code: 0 if every discovered break-glass script's named fields line
up with sites.csv's real current column order AND every row in
sites.csv naive-splits the same way it quote-parses, 1 otherwise.
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

# Known, individually-verified exceptions to the naive-split-safety check --
# site codes with a genuinely, deliberately unresolved quoted-comma value
# somewhere in their row. BRT's Street ("1st Floor, General Aviation
# Terminal") is the one case as of writing -- Robert's explicit call,
# 2026-08-29, after weighing it against building a real CSV-quote-aware
# parser (which would need a dependency, e.g. python3, not guaranteed
# present this early in a fresh Debian install). MIL had the identical
# problem and was fixed by removing the comma from the data instead --
# that's the preferred fix; this allowlist is for when that tradeoff has
# been made deliberately, not a default place to silence a new finding.
# Add to this only after actually confirming with Robert, the same way
# this entry was, not to make a build pass.
KNOWN_NAIVE_SPLIT_EXCEPTIONS = {"BRT"}

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


def check_naive_split_safety(header):
    """Every data row must produce the same field count whether parsed
    properly (respecting CSV quoting, via Python's csv module) or split
    naively on every literal comma -- the exact way every break-glass
    script's `IFS=',' read` does it. A row that doesn't is guaranteed to
    corrupt every field from its first embedded comma onward for every
    script that reads it, regardless of whether the field-list POSITIONS
    are correct (the check above). Found live via BRT/MIL, 2026-08-29 --
    MIL's own instance already fixed by removing the embedded comma from
    its address; BRT's is a known, deliberately unresolved exception, so
    this check is expected to keep flagging it until/unless that changes.

    Assumes no field in sites.csv spans multiple physical lines (true for
    every row as of writing -- a properly-quoted CSV field CAN legally
    contain a literal newline, which would break the naive
    row-index-equals-physical-line-number correlation used here; if that
    ever becomes genuinely needed, this check needs updating alongside
    it, not silently trusted past that point).

    Returns a list of (site, line_no, real_field_count, naive_field_count,
    [culprit column names]) tuples, one per affected row.
    """
    raw_lines = SITES_CSV.read_text(encoding="utf-8").splitlines()
    with SITES_CSV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    findings = []
    for row_idx, real_fields in enumerate(rows):
        if row_idx == 0:
            continue  # header
        line_no = row_idx + 1
        if line_no > len(raw_lines):
            continue  # shouldn't happen -- csv.reader() and splitlines() disagreeing on row count entirely is a different, more fundamental problem than this check is scoped to catch
        naive_fields = raw_lines[line_no - 1].split(",")
        if len(real_fields) == len(naive_fields):
            continue
        site = real_fields[0] if real_fields else "?"
        # A field that survived proper CSV parsing with a literal comma
        # still inside its value can only have gotten there via quoting
        # -- that's the culprit column, found directly rather than
        # guessed at from position arithmetic.
        culprits = [
            header[i] if i < len(header) else f"(column {i})"
            for i, value in enumerate(real_fields)
            if "," in value
        ]
        findings.append((site, line_no, len(real_fields), len(naive_fields), culprits))
    return findings


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

    ok = True

    if findings:
        ok = False
        print(f"\n{len(findings)} field-position mismatch(es):")
        for rel, line_no, name, detail in findings:
            print(f"  {rel}:{line_no}: field '{name}' {detail}")
    else:
        print("\nEvery discovered break-glass script's named sites.csv fields are in sync "
              "with the real current header.")

    all_split_findings = check_naive_split_safety(header)
    split_findings = [f for f in all_split_findings if f[0] not in KNOWN_NAIVE_SPLIT_EXCEPTIONS]
    known_split_findings = [f for f in all_split_findings if f[0] in KNOWN_NAIVE_SPLIT_EXCEPTIONS]

    if split_findings:
        ok = False
        print(f"\n{len(split_findings)} row(s) with a quoted comma that will corrupt every "
              f"break-glass script's naive IFS=',' parse of that row:")
        for site, line_no, real_count, naive_count, culprits in split_findings:
            culprit_desc = ", ".join(culprits) if culprits else "(not isolated -- check the row by hand)"
            print(f"  benarbejde/sites.csv:{line_no}: site '{site}' has {real_count} real "
                  f"field(s) but naive-splits into {naive_count} -- culprit column(s): {culprit_desc}")
    else:
        print("\nNo NEW rows with a quoted comma that would corrupt a break-glass script's "
              "naive IFS=',' parse.")

    if known_split_findings:
        print(f"{len(known_split_findings)} known, deliberately-unresolved exception(s) "
              f"(see KNOWN_NAIVE_SPLIT_EXCEPTIONS) -- not counted as a failure:")
        for site, line_no, real_count, naive_count, culprits in known_split_findings:
            culprit_desc = ", ".join(culprits) if culprits else "(not isolated -- check the row by hand)"
            print(f"  benarbejde/sites.csv:{line_no}: site '{site}' -- culprit column(s): {culprit_desc}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
