#!/usr/bin/env python3
"""
check_facts.py -- part of at_have_ryggen_fri.

Reads facts.yml (a hand-curated list -- see that file's own header for why
this exists instead of a generic scanner) and confirms every file listed
under a fact's asserted_in still contains that fact's value verbatim.

This is deliberately narrow and precise: it only catches drift in a fact
someone has already registered. It will NOT catch a new, unregistered
inconsistency -- that's the tradeoff made explicitly (see facts.yml) in
exchange for zero false positives against changelog entries, historical
examples, or unrelated numbers that happen to look similar.

Exit code: 0 if every registered fact's value is present in every file
that's supposed to assert it, 1 otherwise.
"""
import sys
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FACTS_FILE = Path(__file__).resolve().parent / "facts.yml"


def main():
    data = yaml.safe_load(FACTS_FILE.read_text(encoding="utf-8"))
    facts = data.get("facts", [])

    total_checks = 0
    drifted = []

    for fact in facts:
        name = fact["name"]
        value = fact["value"]
        for rel_path in fact["asserted_in"]:
            total_checks += 1
            path = REPO_ROOT / rel_path
            if not path.exists():
                drifted.append((name, rel_path, f"file does not exist"))
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if value not in text:
                drifted.append((name, rel_path, f'does not contain "{value}"'))

    print(f"Checked {len(facts)} fact(s) against {total_checks} file assertion(s) "
          f"(facts.yml).")

    if drifted:
        print(f"\n{len(drifted)} drifted assertion(s):")
        for name, rel_path, detail in drifted:
            fact = next(f for f in facts if f["name"] == name)
            print(f"  [{name}] {rel_path}: {detail}")
            print(f"      expected (per {fact['source']}): \"{fact['value']}\"")
        return 1

    print("All registered facts hold in every file that asserts them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
