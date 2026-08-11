#!/usr/bin/env python3
"""
check_windows_arch_fact.py -- part of at_have_ryggen_fri.

Real bug, found live 2026-08-11: Robert's first-ever live run of
82-salt-minion.yml against EXADCSCLD001 (a genuine AMD64 box) resolved
host_arch=x86. Root cause: ansible/playbooks/windows_bootstrap/tasks/
arch_facts.yml mapped ansible_architecture ('AMD64'/'ARM64'/'32-bit') to
host_arch -- but on Windows, ansible.windows.setup's ansible_architecture
fact reports OS BITNESS ('64-bit'/'32-bit'), not CPU architecture. It
cannot distinguish AMD64 from ARM64 at all -- both report '64-bit'. Every
branch fell straight through to the 'x86' default on every real Windows
box, 64-bit or not, since arch_facts.yml's first commit (2026-06-20) --
never caught because nothing depending on host_arch had been run live
before that day. Not scoped to one file either: arch_facts.yml is shared
by 6 playbooks/tasks files, all inherited the identical silent mismap.
Fixed (commit 3ff733f) by switching to ansible_architecture2, a separate
fact the ansible.windows collection provides specifically for this
ambiguity.

This check closes the gap generically rather than re-litigating the one
fixed instance: any git-tracked *.yml under a windows_* playbook
directory (ansible/playbooks/windows_bootstrap/, windows_dc/, etc. --
matched by directory NAME, not a hardcoded list, so a future windows_*
directory is covered automatically) that references the bare
ansible_architecture fact is flagged. This fact is only broken on
Windows -- ansible.builtin.setup on Linux genuinely returns CPU
architecture via this same name (confirmed real, correct usage exists in
ansible/playbooks/tacticalrmm/tacticalrmm_server.yml, a Linux-only
playbook, deliberately NOT flagged since it's outside any windows_*
directory), so this check is directory-scoped rather than a blanket
repo-wide ban on the fact name.

Comment lines are skipped (a leading # after stripping whitespace) --
arch_facts.yml's own changelog explains this exact bug in prose using the
literal string "ansible_architecture", which would otherwise self-match
as a phantom failure, the same class of false positive
check_playbook_dir_paths.py already guards against for its own worked
example.

Exit code: 0 if no bare ansible_architecture usage found under any
windows_* directory, 1 otherwise.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ANSIBLE_DIR = REPO_ROOT / "ansible"

# Matches "ansible_architecture" but not "ansible_architecture2" -- \b after
# "architecture" only fires between a word char and a non-word char, and "2"
# is a word char, so the trailing \b already excludes the _2 variant with no
# lookahead needed (confirmed: "ansible_architecture2" has no boundary
# between "e" and "2").
BARE_FACT = re.compile(r"\bansible_architecture\b")


def is_windows_dir(path):
    return any(part.lower().startswith("windows") for part in path.parts)


def git_tracked_yml_files():
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--", "ansible/**/*.yml", "ansible/*.yml"],
        capture_output=True, text=True, timeout=30,
    ).stdout
    return [REPO_ROOT / line for line in out.splitlines() if line]


def main():
    checked = 0
    failures = []

    for path in git_tracked_yml_files():
        rel = path.relative_to(REPO_ROOT)
        if not is_windows_dir(rel.relative_to("ansible")):
            continue
        checked += 1
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            if BARE_FACT.search(line):
                failures.append((rel, lineno, line.strip()))

    print(f"Checked {checked} *.yml file(s) under windows_* playbook directories for bare "
          f"ansible_architecture usage.")

    if failures:
        print(f"\n{len(failures)} use(s) of the bare (broken-on-Windows) fact found:")
        for rel, lineno, line in failures:
            print(f"  {rel}:{lineno}: {line}")
        print(
            "\nOn Windows, ansible_architecture reports OS bitness ('64-bit'/'32-bit'), not "
            "CPU architecture -- it cannot distinguish AMD64 from ARM64. Use "
            "ansible_architecture2 instead (see tasks/arch_facts.yml's own 2026-08-11 "
            "changelog entry for the full story)."
        )
        return 1

    print("No bare ansible_architecture usage found under any windows_* directory.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
