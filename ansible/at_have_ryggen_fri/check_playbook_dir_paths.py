#!/usr/bin/env python3
"""
check_playbook_dir_paths.py -- part of at_have_ryggen_fri.

Found 2026-07-12: bootstrap-new-node.yml's sites_csv_src/address_policy_src/
ad_forest_src used "{{ playbook_dir }}/../../../../benarbejde/..." -- 4
levels of ../, copy-pasted from 00-preflight.yml/30-example-music.yml, which
live one directory deeper (under playbooks/proxmox/playbooks/) and correctly
need 4. bootstrap-new-node.yml itself lives directly under playbooks/proxmox/
and only needs 3 -- off by one the whole time.

This was invisible to both existing structural checks:
  - check_references.py only resolves literal (non-Jinja) src:/
    include_tasks:/import_tasks:/import_playbook: paths -- a Jinja
    "{{ playbook_dir }}/../.../X" string assigned to a vars: entry and later
    consumed by read_csv/lookup('file', ...)/a shell command isn't a
    reference it looks at.
  - ansible-playbook --syntax-check doesn't execute tasks, so a bad runtime
    path in a read_csv/lookup/command isn't a syntax error -- it only
    surfaces the first time a real run actually reaches that task, which
    for bootstrap-new-node.yml didn't happen until 2026-07-12 (every earlier
    attempt failed at SSH connect time -- see ssh_key_preflight.yml).

This check closes that gap generically: every "{{ playbook_dir }}/(../)+X"
expression in any git-tracked *.yml under ansible/ is resolved against the
file's real location and confirmed to point at something that actually
exists on disk -- the same "independent source of truth" tier-1 philosophy
as check_references.py, applied to the one path pattern it doesn't cover.

Exit code: 0 if every playbook_dir-relative path resolves, 1 otherwise.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANSIBLE_DIR = REPO_ROOT / "ansible"

# {{ playbook_dir }}, then one or more /.. segments, then a trailing path
# fragment up to whitespace, a quote, or a closing brace.
PATTERN = re.compile(r"\{\{\s*playbook_dir\s*\}\}((?:/\.\.)+)/([^\s\"'{}]+)")


def main():
    checked = 0
    failures = []

    for rel in subprocess_git_ls_files():
        path = REPO_ROOT / rel
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in PATTERN.finditer(text):
            up_segments, tail = match.groups()
            checked += 1
            levels = up_segments.count("/..")
            resolved = (path.parent / ("../" * levels) / tail).resolve()
            if not resolved.exists():
                failures.append((rel, match.group(0), levels, resolved))

    print(f"Checked {checked} playbook_dir-relative path expression(s).")

    if failures:
        print(f"\n{len(failures)} unresolved:")
        for rel, expr, levels, resolved in failures:
            print(f"  {rel}: {expr}")
            print(f"      resolves to {resolved} ({levels} level(s) of ../) -- does not exist")
        return 1

    print("All playbook_dir-relative paths resolve to real files.")
    return 0


def subprocess_git_ls_files():
    import subprocess
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--", "ansible/*.yml", "ansible/**/*.yml"],
        capture_output=True, text=True, timeout=30,
    ).stdout
    return [line for line in out.splitlines() if line]


if __name__ == "__main__":
    sys.exit(main())
