#!/usr/bin/env python3
"""
check_scenarios.py -- part of at_have_ryggen_fri.

Reads scenarios.yml -- the four bare-metal-to-working-estate scenarios
(PVE+Ansible node, DNS, firewall, Windows unattend) -- and confirms, for
each:
  1. Every file the scenario depends on still exists.
  2. Every registered content assertion (a specific phrase that must be
     present in a specific file) still holds.

This does NOT actually build a PVE node, DNS server, firewall, or Windows
box -- that needs real hardware/hypervisors this harness deliberately
doesn't touch (see README.md's design notes). What it catches is the
paper trail going stale: a required script/doc getting deleted or moved
without updating scenarios.yml, or a load-bearing warning/framing comment
being edited away by someone who didn't know why it was there.

Exit code: 0 if every scenario's files and assertions hold, 1 otherwise.
"""
import sys
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_FILE = Path(__file__).resolve().parent / "scenarios.yml"


def main():
    data = yaml.safe_load(SCENARIOS_FILE.read_text(encoding="utf-8"))
    scenarios = data.get("scenarios", [])

    total_files = 0
    total_assertions = 0
    failures = []

    for scenario in scenarios:
        name = scenario["name"]

        for rel_path in scenario.get("requires_files", []):
            total_files += 1
            if not (REPO_ROOT / rel_path).exists():
                failures.append((name, rel_path, "required file does not exist"))

        for assertion in scenario.get("content_assertions", []):
            total_assertions += 1
            rel_path = assertion["file"]
            needle = assertion["must_contain"]
            path = REPO_ROOT / rel_path
            if not path.exists():
                failures.append((name, rel_path, f'file does not exist (needed to check for "{needle}")'))
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if needle not in text:
                why = assertion.get("why", "")
                failures.append((name, rel_path, f'does not contain "{needle}"' +
                                  (f' -- {why}' if why else "")))

    print(f"Checked {len(scenarios)} scenario(s): {total_files} required file(s), "
          f"{total_assertions} content assertion(s) (scenarios.yml).")

    if failures:
        print(f"\n{len(failures)} failure(s):")
        for scenario_name, rel_path, detail in failures:
            print(f"  [{scenario_name}] {rel_path}: {detail}")
        return 1

    print("All scenario requirements and assertions hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
