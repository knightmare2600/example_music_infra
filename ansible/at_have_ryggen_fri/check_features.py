#!/usr/bin/env python3
"""
check_features.py -- part of at_have_ryggen_fri.

Reads features.yml -- a short, hand-curated registry mapping a named
feature to its doc and its harness check -- and confirms, for each entry:
  1. The doc still exists on disk.
  2. The referenced check_*.py script still exists on disk.
  3. That script is still actually wired into run.sh (not just present but
     orphaned/de-wired -- an unwired check is exactly as broken in practice
     as a missing one).

This is the one check here that answers the literal question "if a feature
got a doc but nobody built a matching check (or vice versa), how would we
know?" -- checks 1-18 are all structural/link-based and can't see that
class of gap: a doc with zero broken links and a check that runs clean are
both individually invisible to this problem by construction, since neither
one's absence shows up as broken anything unless something is specifically
looking for the *pairing*.

Same honest limitation as scenarios.yml/facts.yml: this does NOT catch an
unregistered gap forming in the first place -- a brand new feature that
never gets an entry here is invisible to this check, same as it would be
to scenarios.yml or facts.yml. What it guarantees is narrower but real:
once a feature IS registered, its doc can't silently go missing and its
check can't silently get de-wired without this failing loudly.

Exit code: 0 if every registered feature's doc and check both hold, 1
otherwise.
"""
import sys
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FEATURES_FILE = Path(__file__).resolve().parent / "features.yml"
RUN_SH = Path(__file__).resolve().parent / "run.sh"


def main():
    data = yaml.safe_load(FEATURES_FILE.read_text(encoding="utf-8"))
    features = data.get("features", [])
    run_sh_text = RUN_SH.read_text(encoding="utf-8", errors="replace")

    failures = []

    for feature in features:
        name = feature["name"]

        doc_path = feature["doc"]
        if not (REPO_ROOT / doc_path).exists():
            failures.append((name, "doc", f'"{doc_path}" does not exist'))

        check_name = feature["check"]
        check_path = RUN_SH.parent / check_name
        if not check_path.exists():
            failures.append((name, "check", f'"{check_name}" does not exist'))
        elif check_name not in run_sh_text:
            failures.append((name, "check", f'"{check_name}" exists but is not wired into run.sh'))

    print(f"Checked {len(features)} registered feature(s) (features.yml): "
          f"doc exists + check exists + check wired into run.sh.")

    if failures:
        print(f"\n{len(failures)} failure(s):")
        for name, half, detail in failures:
            print(f"  [{name}] {half}: {detail}")
        return 1

    print("Every registered feature's doc and check both hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
