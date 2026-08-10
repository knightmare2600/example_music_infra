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

Found 2026-07-28, a second variant of the same gap: 11 of 12 real callers of
ansible/tasks/example_music_freshness_gate.yml passed "{{ playbook_dir
}}/../.." (etc) as example_music_gate_repo_root -- a BARE playbook_dir
expression with no trailing path fragment at all, assigned to an
intermediate vars: entry. The suffix ("/benarbejde/{{ item }}") is only
appended later, inside the shared gate file itself, using a different
variable name entirely -- so the original PATTERN below (which requires a
literal trailing segment in the SAME string) never matched these lines,
and the bug (every one but bind9-dns.yml was off by exactly one level
short) was invisible to this check the whole time it existed. Caught live,
not by this harness -- windows_bootstrap/site.yml crashed against a real
control node with a "missing benarbejde/sites.csv" false positive. Added
GATE_ROOT_PATTERN below to close this specific instance of the gap: any
bare "{{ playbook_dir }}" plus one or more /.. segments, assigned to
example_music_gate_repo_root, is resolved and confirmed to contain a real
benarbejde/ directory (the one suffix this variable is ever actually
combined with). Both patterns skip comment lines (a leading # after
stripping whitespace) -- example_music_freshness_gate.yml's own header has
a worked usage example containing this exact literal string, which would
otherwise self-match as a phantom failure the same way a similar comment
once did for a different check in this harness.

Found 2026-08-10, a third variant: 82-salt-minion.yml's ARM64-support change
introduced the first playbook_dir path with a genuine RUNTIME Jinja
expression embedded in the trailing filename ("Salt-Minion-Setup-
{{ host_arch }}.msi", host_arch resolved per-target at play time, not
knowable statically). The original tail pattern excluded "{"/"}" outright,
so it silently truncated the match at "Salt-Minion-Setup-" and reported a
real, correctly-committed file as unresolvable -- a false positive, not a
real bug. Fixed generically rather than special-cased to this one file:
the tail pattern now matches a complete {{ ... }} block as a unit, and
resolution substitutes any embedded Jinja expression with a glob wildcard,
requiring at least one real file to match rather than one exact literal
path -- holds for any future playbook_dir path with a runtime-templated
segment, not just this one.

Exit code: 0 if every playbook_dir-relative path resolves, 1 otherwise.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ANSIBLE_DIR = REPO_ROOT / "ansible"

JINJA_EXPR = re.compile(r"\{\{[^{}]*\}\}")


def path_exists(base_dir, tail):
    """A literal tail must exist exactly. A tail containing a runtime Jinja
    expression (e.g. "Salt-Minion-Setup-{{ host_arch }}.msi") can't be
    resolved to one real path statically -- substitute each {{ ... }} with
    a glob wildcard instead and require at least one real file to match,
    so a genuinely broken path (typo, wrong directory) still fails while a
    correct runtime-templated one passes."""
    if not JINJA_EXPR.search(tail):
        resolved = (base_dir / tail).resolve()
        return resolved.exists(), resolved
    glob_pattern = JINJA_EXPR.sub("*", tail)
    resolved = (base_dir / glob_pattern).resolve()
    matches = list(base_dir.glob(glob_pattern))
    return len(matches) > 0, resolved

# {{ playbook_dir }}, then one or more /.. segments, then a trailing path
# fragment up to whitespace or a quote. The fragment itself may contain a
# runtime Jinja expression (e.g. "Salt-Minion-Setup-{{ host_arch }}.msi",
# added 2026-08-10 for ARM64 Salt minion support) -- matched as a complete
# {{ ... }} unit (internal spaces allowed) rather than excluded outright,
# since the original tail pattern stopped dead at the first "{" and
# silently truncated the match instead of flagging it as unresolvable.
TAIL = r"(?:[^\s\"'{}]|\{\{[^{}]*\}\})+"
PATTERN = re.compile(r"\{\{\s*playbook_dir\s*\}\}((?:/\.\.)+)/(" + TAIL + r")")

# example_music_gate_repo_root: "{{ playbook_dir }}(/..)+ " -- bare, no
# trailing path fragment, only ever combined with /benarbejde later inside
# ansible/tasks/example_music_freshness_gate.yml itself.
GATE_ROOT_PATTERN = re.compile(
    r"example_music_gate_repo_root:\s*[\"']\{\{\s*playbook_dir\s*\}\}((?:/\.\.)+)[\"']"
)


def main():
    checked = 0
    failures = []

    for rel in subprocess_git_ls_files():
        path = REPO_ROOT / rel
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("#"):
                continue

            for match in PATTERN.finditer(line):
                up_segments, tail = match.groups()
                checked += 1
                levels = up_segments.count("/..")
                base_dir = (path.parent / ("../" * levels)).resolve()
                exists, resolved = path_exists(base_dir, tail)
                if not exists:
                    failures.append((rel, match.group(0), levels, resolved))

            for match in GATE_ROOT_PATTERN.finditer(line):
                up_segments = match.group(1)
                checked += 1
                levels = up_segments.count("/..")
                resolved = (path.parent / ("../" * levels) / "benarbejde").resolve()
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
