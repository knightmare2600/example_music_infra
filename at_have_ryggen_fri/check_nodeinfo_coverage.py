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

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS_DIR = REPO_ROOT / "ansible" / "playbooks"

EXEMPT_FAMILIES = {"meshcentral", "snmp"}
EXEMPT_FILES = {"ssh_preflight_with_fallback.yml"}

NODEINFO_REF_RE = re.compile(r"(include|import)_tasks:.*nodeinfo(_windows)?\.yml")


def family_has_coverage(family_dir: Path) -> bool:
    for f in family_dir.rglob("*.yml"):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if NODEINFO_REF_RE.search(text):
            return True
    return False


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

    print(
        f"Checked {len(families)} playbook famil{'y' if len(families) == 1 else 'ies'} + "
        f"{len(standalone_files)} standalone playbook(s) under "
        f"{PLAYBOOKS_DIR.relative_to(REPO_ROOT)} "
        f"({len(EXEMPT_FAMILIES)} famil{'y' if len(EXEMPT_FAMILIES) == 1 else 'ies'} + "
        f"{len(EXEMPT_FILES)} file(s) explicitly exempt -- see this check's own header for why) "
        f"for a reference to ansible/tasks/nodeinfo.yml or nodeinfo_windows.yml anywhere "
        f"in their own file tree."
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
        return 1

    print(f"\nAll {len(covered)} playbook famil{'y' if len(covered) == 1 else 'ies'}/standalone playbook(s) have nodeinfo.json coverage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
