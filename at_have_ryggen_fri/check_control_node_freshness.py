#!/usr/bin/env python3
"""
check_control_node_freshness.py -- part of at_have_ryggen_fri.

Triggered by a real live crash (2026-07-26): bind9-dns.yml died with a raw Python
KeyError running generate_inventory.py against /etc/example-music/address_policy.json
-- traced to the Ansible control node's OWN served copy (every consumer reads it via
delegate_to: localhost or lookup('file', ...), which always evaluates on the
controller, never the play's remote target -- confirmed across all 12 real consumers
of /etc/example-music/*, see ansible/tasks/example_music_freshness_gate.yml). That
copy predated a benarbejde/ schema change because linux/tools.yml (the only thing
that deploys benarbejde/* to /etc/example-music/*) hadn't been re-run against the
control node itself in a while, even though its own git checkout was current.

This is the offline half of the fix: catch that class of drift here, in the harness,
before any playbook run ever hits it -- rather than only at Ansible-run time via each
playbook's own gate task (ansible/tasks/example_music_freshness_gate.yml, the other,
in-playbook half of this same fix).

Only meaningful when run ON the control node (or a checkout that happens to have
/etc/example-music/ present, e.g. EXAANSCLD001 itself). On any other machine -- a dev
workstation, CI, a fresh clone -- /etc/example-music/ simply won't exist, and that's
a legitimate, non-error state: skip cleanly rather than fail.

Checks the exact file list ansible/playbooks/linux/tools.yml deploys (its own
*_src vars, read directly -- not re-typed by hand a second time) against each file's
benarbejde/ source, by content hash. nodeinfo.json is deliberately excluded: it's
host-generated (ansible/tasks/nodeinfo.yml), not sourced from benarbejde/ at all, so
there's no source-of-truth copy to diff it against.

Exit code: 0 if /etc/example-music/ doesn't exist locally, or every present file
matches its benarbejde/ source. 1 if any file is missing on one side or the content
differs.
"""
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE = REPO_ROOT / "benarbejde"
EXAMPLE_MUSIC_DIR = Path("/etc/example-music")

SERVED_FILES = [
    "sites.csv",
    "devices.csv",
    "role_codes.csv",
    "address_policy.json",
    "ad_forest.json",
    "ad_groups.json",
    "ad_users.json",
    "ad_computers.json",
]

REFRESH_CMD = "ansible-playbook ansible/playbooks/linux/tools.yml --limit EXAANSCLD001"


def sha256_of(path):
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main():
    if not EXAMPLE_MUSIC_DIR.is_dir():
        print(f"{EXAMPLE_MUSIC_DIR} doesn't exist on this machine -- not the control node "
              f"(or pre-first-deploy). Nothing to check.")
        return 0

    problems = []
    checked = 0

    for name in SERVED_FILES:
        served = EXAMPLE_MUSIC_DIR / name
        source = BENARBEJDE / name

        if not source.is_file():
            problems.append(f"{source.relative_to(REPO_ROOT)} doesn't exist in this checkout "
                             f"at all -- can't compare, this repo checkout may itself be broken")
            continue
        if not served.is_file():
            problems.append(f"{served} is missing -- refresh: {REFRESH_CMD}")
            continue

        checked += 1
        if sha256_of(served) != sha256_of(source):
            problems.append(f"{served} is stale relative to {source.relative_to(REPO_ROOT)} "
                             f"-- refresh: {REFRESH_CMD}")

    print(f"Checked {checked}/{len(SERVED_FILES)} served file(s) in {EXAMPLE_MUSIC_DIR} "
          f"against their benarbejde/ source.")

    if problems:
        print(f"\n{len(problems)} issue(s) found:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"All {checked} served file(s) match their benarbejde/ source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
