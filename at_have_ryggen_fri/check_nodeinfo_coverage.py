#!/usr/bin/env python3
"""
check_nodeinfo_coverage.py -- part of at_have_ryggen_fri.

Robert, 2026-09-26: "I want every playbook to update that JSON field."
nodeinfo.json's last_ansible_run (added 2026-09-24 for Linux via
ansible/tasks/nodeinfo.yml, extended 2026-09-26 to Windows via the new
ansible/tasks/nodeinfo_windows.yml -- see that file's own header for the full
writeup) is meant to answer "when did Ansible last genuinely touch this box,"
estate-wide, for every playbook family that manages a real host. Until
2026-09-26, three entire Windows families -- windows_bootstrap, windows_dc,
windows_adschema -- never wrote nodeinfo.json at all, discovered only because
Robert asked directly whether "every" playbook did.

Ansible itself has no mechanism to guarantee a task runs in every play
without that play explicitly referencing it -- group_vars/host_vars carry
data, never task logic, and there's no config-only "run this everywhere"
switch (see nodeinfo_windows.yml's own header for the full reasoning). The
two shared task files are the closest real answer to "move the functionality
so we don't have to keep re-adding it" -- this check is the other half: it
fails if any current or future playbook family that manages a real host
doesn't reference one of them anywhere in its own file tree, so a fourth
"actually, we forgot this one too" can't happen silently again.

2026-10-04, extended after a real live bug (Robert, EXADCSGOT001): a reference existing is
not the same as it actually working. tasks/nodeinfo_windows.yml's own tasks never got the
`tags: always` fix tasks/nodeinfo.yml (Linux) already had, and separately -- the bigger,
non-obvious finding -- even an UNTAGGED caller's include_tasks/block still gets excluded
entirely under an active --tags filter, confirmed empirically via `--list-tasks`, not assumed.
Every real caller needed `always` added. Robert's own worry, verbatim: "if the tags are
forgotten or omitted, then what?" -- there's no Ansible mechanism that makes a tag
un-forgettable (tags are opt-in, full stop), so the answer has to be the same one this whole
check already exists for: a harness check that fails loudly the moment a NEW caller gets
added without it, rather than relying on every future author remembering the convention.
This check now verifies not just that a reference exists, but that `always` is somewhere in
its effective tag set (its own tags, or any enclosing block's) -- a real YAML-structural
walk, not a second regex guess, since tag inheritance through nested block/rescue/always
containers genuinely needs the real structure to get right.

Scope, by design -- these are excluded, not overlooked:
  - meshcentral/ -- dead/retired (EXAMSHCLD001 decommissioned 2026-08-08),
    kept only in case a standalone instance is ever needed again. Explicitly
    never converted to the current nodeinfo.yml pattern either (see that
    file's own 2026-08-04 changelog note) -- not worth the effort for
    inactive code.
  - snmp/ -- targets network devices (switches, printers) over SNMP, not
    Ansible-managed hosts with a filesystem at all. There is no destination
    to write nodeinfo.json TO.
  - ssh_preflight_with_fallback.yml -- a pre-connectivity utility, imported
    BEFORE a play that needs a real SSH/become connection to even work yet.
    Runs too early to write anything meaningful, and every real play that
    imports it also does its own actual work afterward, which IS covered.

A family "has coverage" if ANY .yml file anywhere under its own directory
references either shared task file via include_tasks/import_tasks --
deliberately not stricter than that (e.g. requiring it in one specific
file) since different families wire their own "finish" stage differently,
and this check's job is "did anyone forget entirely," not "is it wired in
the one true place."
"""
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS_DIR = REPO_ROOT / "ansible" / "playbooks"

EXEMPT_FAMILIES = {"meshcentral", "snmp"}
EXEMPT_FILES = {"ssh_preflight_with_fallback.yml"}

NODEINFO_REF_RE = re.compile(r"(include|import)_tasks:.*nodeinfo(_windows)?\.yml")
NODEINFO_TARGET_RE = re.compile(r"nodeinfo(_windows)?\.yml$")
NODEINFO_INCLUDE_KEYS = (
    "include_tasks", "import_tasks",
    "ansible.builtin.include_tasks", "ansible.builtin.import_tasks",
)
# Containers that pass their own tags down to the tasks nested inside them --
# a block's (or rescue's/always's) tags are inherited by every task it wraps,
# same as Ansible's own real tag-inheritance semantics.
TASK_CONTAINER_KEYS = ("block", "rescue", "always", "tasks", "pre_tasks", "post_tasks", "handlers")


def family_has_coverage(family_dir: Path) -> bool:
    for f in family_dir.rglob("*.yml"):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if NODEINFO_REF_RE.search(text):
            return True
    return False


def _tag_set(value) -> frozenset:
    if value is None:
        return frozenset()
    if isinstance(value, str):
        return frozenset([value])
    if isinstance(value, (list, tuple)):
        return frozenset(str(v) for v in value)
    return frozenset()


def _is_nodeinfo_target(value) -> bool:
    if isinstance(value, str):
        path = value
    elif isinstance(value, dict):
        path = value.get("file", "")
    else:
        return False
    return bool(NODEINFO_TARGET_RE.search(path))


def find_untagged_nodeinfo_includes(node, inherited_tags: frozenset = frozenset()) -> list:
    """Recursively walk a parsed playbook/task-file structure (plays, tasks,
    blocks, rescue/always sections, nested includes) and return a list of
    (task_name, effective_tags) for every nodeinfo(.yml|_windows.yml) include
    whose EFFECTIVE tag set -- its own tags, unioned with every enclosing
    block's -- does not include 'always'. A real structural walk, not a
    second regex guess, because tag inheritance through nested
    block/rescue/always containers can't be reliably read off the text."""
    violations = []
    if isinstance(node, list):
        for item in node:
            violations.extend(find_untagged_nodeinfo_includes(item, inherited_tags))
    elif isinstance(node, dict):
        effective = inherited_tags | _tag_set(node.get("tags"))

        for key in NODEINFO_INCLUDE_KEYS:
            if key in node and _is_nodeinfo_target(node[key]) and "always" not in effective:
                violations.append((node.get("name", "<unnamed task>"), sorted(effective)))

        for container_key in TASK_CONTAINER_KEYS:
            if container_key in node:
                violations.extend(find_untagged_nodeinfo_includes(node[container_key], effective))
    return violations


def main():
    if not PLAYBOOKS_DIR.exists():
        print(f"{PLAYBOOKS_DIR.relative_to(REPO_ROOT)} does not exist.")
        return 1

    families = sorted(
        p.name for p in PLAYBOOKS_DIR.iterdir()
        if p.is_dir() and p.name not in EXEMPT_FAMILIES
    )
    standalone_files = sorted(
        p.name for p in PLAYBOOKS_DIR.iterdir()
        if p.is_file() and p.suffix == ".yml" and p.name not in EXEMPT_FILES
    )

    missing = []
    covered = []

    for family in families:
        if family_has_coverage(PLAYBOOKS_DIR / family):
            covered.append(family)
        else:
            missing.append(family)

    for fname in standalone_files:
        text = (PLAYBOOKS_DIR / fname).read_text(encoding="utf-8", errors="ignore")
        if NODEINFO_REF_RE.search(text):
            covered.append(fname)
        else:
            missing.append(fname)

    # Second pass: for every file that DOES reference a shared nodeinfo task file,
    # verify the include actually carries 'always' in its effective tag set -- a
    # reference existing is not the same as it actually running under a tag-scoped
    # invocation (see this file's own 2026-10-04 header entry for the real bug this
    # caught live).
    tag_violations = []
    for f in sorted(PLAYBOOKS_DIR.rglob("*.yml")):
        rel_parts = f.relative_to(PLAYBOOKS_DIR).parts
        if rel_parts and rel_parts[0] in EXEMPT_FAMILIES:
            continue
        if f.name in EXEMPT_FILES:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not NODEINFO_REF_RE.search(text):
            continue
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError:
            continue  # a real syntax error here is already caught by the syntax-check pass
        for task_name, tags in find_untagged_nodeinfo_includes(data):
            tag_violations.append((str(f.relative_to(REPO_ROOT)), task_name, tags))

    print(
        f"Checked {len(families)} playbook famil{'y' if len(families) == 1 else 'ies'} + "
        f"{len(standalone_files)} standalone playbook(s) under "
        f"{PLAYBOOKS_DIR.relative_to(REPO_ROOT)} "
        f"({len(EXEMPT_FAMILIES)} famil{'y' if len(EXEMPT_FAMILIES) == 1 else 'ies'} + "
        f"{len(EXEMPT_FILES)} file(s) explicitly exempt -- see this check's own header for why) "
        f"for a reference to ansible/tasks/nodeinfo.yml or nodeinfo_windows.yml anywhere "
        f"in their own file tree."
    )

    print(
        f"Checked the same files for whether each nodeinfo include actually carries "
        f"'always' in its effective tag set -- a reference existing is not the same as it "
        f"actually running under a tag-scoped invocation."
    )

    if missing:
        print(f"\n{len(missing)} playbook famil{'y' if len(missing) == 1 else 'ies'} with NO nodeinfo.json coverage at all:")
        for m in missing:
            print(f"  - {m}")
        print(
            "\nEvery playbook family that manages a real host is expected to write/refresh "
            "nodeinfo.json (Robert's ask, 2026-09-26: \"I want every playbook to update that "
            "JSON field\"). See ansible/tasks/nodeinfo.yml (Linux) or "
            "ansible/tasks/nodeinfo_windows.yml (Windows) for the shared implementation to "
            "include, and windows_dc/playbooks/40-dc-summary.yml for a real example of wiring "
            "it in non-fatally (block/rescue, not ignore_errors: on the include -- see that "
            "file's own 2026-09-26 changelog for why ignore_errors: alone doesn't work here)."
        )

    if tag_violations:
        print(f"\n{len(tag_violations)} nodeinfo include(s) found WITHOUT 'always' in their effective tags:")
        for rel, task_name, tags in tag_violations:
            print(f"  - {rel}: \"{task_name}\" (effective tags: {tags or '[]'})")
        print(
            "\nAdd 'always' to the task's own tags: (or, if it's wrapped in a block, to the "
            "block's tags:) so the write survives any --tags-scoped invocation -- confirmed "
            "live, 2026-10-04: an UNTAGGED include is just as exposed as a mismatched one, "
            "'always' has to be explicit. See ansible/tasks/nodeinfo_windows.yml's and "
            "windows_bootstrap/playbooks/85-finish.yml's own 2026-10-04 changelog entries for "
            "the full empirical writeup."
        )

    if missing or tag_violations:
        return 1

    print(f"\nAll {len(covered)} playbook famil{'y' if len(covered) == 1 else 'ies'}/standalone playbook(s) have nodeinfo.json coverage, every include correctly tagged 'always'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
