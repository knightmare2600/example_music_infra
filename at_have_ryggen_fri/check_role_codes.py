#!/usr/bin/env python3
"""
check_role_codes.py -- part of at_have_ryggen_fri.

Robert, 2026-07-20, while cleaning up the retired PRV convention: "let's fix these
type of drifts when we find them." The same code->connection-method and code->emoji
data used to be hand-duplicated in three places (address_policy.json's
connection_types, generate_network_diagrams.py's TYPE_SYMBOLS, docs/emojis/README.md)
-- found one already drifted (MBP was ssh in one copy, winrm in another) while
consolidating them into benarbejde/role_codes.csv, the new single source of truth.
address_policy.json's connection_types and generate_network_diagrams.py's hardcoded
TYPE_SYMBOLS dict are gone -- both now load role_codes.csv directly, so they can't
drift from it by construction. The one copy that's still deliberately hand-maintained
is docs/emojis/README.md (a human-readable legend, not something worth generating
markdown prose for) -- this check is what keeps *that* one honest.

Checks:
  1. Every Code in role_codes.csv appears in docs/emojis/README.md with the same
     Emoji.
  2. Every Type/Symbol row in docs/emojis/README.md's tables has a matching Code/Emoji
     row in role_codes.csv (nothing in the doc that isn't in the CSV).

Clone-safe, always runs -- only needs benarbejde/role_codes.csv and
docs/emojis/README.md, no live host.
"""
import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROLE_CODES_CSV = REPO_ROOT / "benarbejde" / "role_codes.csv"
EMOJI_DOC = REPO_ROOT / "docs" / "emojis" / "README.md"

# Matches "| CODE | emoji | ..." table rows -- the emoji column is whatever's between
# the second pair of pipes, trimmed.
ROW_RE = re.compile(r"^\|\s*([A-Z]{2,4})\s*\|\s*([^|]+?)\s*\|")


def load_role_codes():
    if not ROLE_CODES_CSV.is_file():
        print(f"ERROR: {ROLE_CODES_CSV} not found.")
        sys.exit(1)
    with open(ROLE_CODES_CSV, newline="", encoding="utf-8") as f:
        return {row["Code"]: row["Emoji"] for row in csv.DictReader(f)}


def load_doc_emojis():
    if not EMOJI_DOC.is_file():
        print(f"ERROR: {EMOJI_DOC} not found.")
        sys.exit(1)
    doc_emojis = {}
    for line in EMOJI_DOC.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        code, symbol = m.group(1), m.group(2)
        if code == "Type":  # header row
            continue
        doc_emojis[code] = symbol
    return doc_emojis


def main():
    role_codes = load_role_codes()
    doc_emojis = load_doc_emojis()

    missing_from_doc = sorted(set(role_codes) - set(doc_emojis))
    missing_from_csv = sorted(set(doc_emojis) - set(role_codes))
    mismatched = sorted(
        code for code in (set(role_codes) & set(doc_emojis))
        if role_codes[code] != doc_emojis[code]
    )

    print(f"Checked {len(role_codes)} code(s) in benarbejde/role_codes.csv against "
          f"{len(doc_emojis)} code(s) in docs/emojis/README.md.")

    failed = False
    if missing_from_doc:
        failed = True
        print(f"\n{len(missing_from_doc)} code(s) in role_codes.csv missing from "
              f"docs/emojis/README.md's legend:")
        for c in missing_from_doc:
            print(f"  - {c} ({role_codes[c]})")

    if missing_from_csv:
        failed = True
        print(f"\n{len(missing_from_csv)} code(s) in docs/emojis/README.md not in "
              f"benarbejde/role_codes.csv:")
        for c in missing_from_csv:
            print(f"  - {c} ({doc_emojis[c]})")

    if mismatched:
        failed = True
        print(f"\n{len(mismatched)} code(s) with a different emoji in each place:")
        for c in mismatched:
            print(f"  - {c}: role_codes.csv={role_codes[c]!r}  docs/emojis/README.md={doc_emojis[c]!r}")

    if failed:
        print("\nUpdate whichever side is stale -- benarbejde/role_codes.csv is the "
              "source of truth (also used by generate_inventory.py and "
              "generate_network_diagrams.py); docs/emojis/README.md is the "
              "human-readable legend and should always agree with it exactly.")
        return 1

    print("Every role_codes.csv entry matches docs/emojis/README.md's legend exactly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
