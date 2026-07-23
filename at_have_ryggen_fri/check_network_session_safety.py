#!/usr/bin/env python3
"""
check_network_session_safety.py -- part of at_have_ryggen_fri.

Catches the bind9-dns.yml/rudder_server.yml/10-master.yml bug class before it
ships a fourth time: a playbook that reconfigures a live NetworkManager
connection Ansible's own SSH session might be riding, using the old
`nmcli con(nection) delete` + `nmcli con(nection) add` pattern instead of the
session-safe templated-.nmconnection-keyfile + `nmcli connection reload`
pattern already established in roles/firewall/tasks/06_network_manager.yml.

All three real, live instances found this week (bind9-dns.yml on
EXADNSVRK001, then the identical copy-pasted pattern in rudder_server.yml and
salt/playbooks/10-master.yml) shared the same two symptoms in the same file:
  1. `nmcli con delete <profile>` followed elsewhere in the same file by
     `nmcli con add ... con-name <same profile>` -- nmcli deactivates an
     active connection before deleting it, so this always risks dropping
     whatever session rides that connection, and always reports "changed"
     regardless of whether anything actually needed to change.
  2. `nmcli connection up <profile>` with no `when:` guard at all, even
     though the same file templates that exact profile's .nmconnection file
     -- meaning this playbook CAN rewrite that connection's live address,
     with nothing stopping it from being applied live out from under the
     session running the play.

Two tiers:

  Tier 1 (hard fail): #1 above. Unambiguous -- a connection profile that's
    both deleted and re-added by name in the same file has no legitimate
    reason not to use the templated-keyfile pattern instead. Zero false
    positives against the current repo (06_network_manager.yml's own stale-
    profile cleanup loop deletes by `{{ item }}`, never a fixed name, and
    never re-adds anything -- it can never match here).

  Tier 2 (informational, escalated to a failure only with --strict): #2
    above. Deliberately not a hard fail -- 06_network_manager.yml's own
    `nmcli con up lan` has no strand-check either, and that's a reviewed,
    intentional judgement call (LAN is never the interface Ansible's own
    session rides in this estate's architecture, only WAN is) that this
    script has no way to know. Surfacing it lets a human confirm the same
    judgement call was actually made for each new instance, rather than
    silently assuming every unguarded `connection up` is fine because one
    of them, once, legitimately was.

KNOWN LIMITATION: task-level `when:` only. A task inside a `block:` that
relies on the block's own `when:` (not its own) will show as a false Tier 2
positive -- no file in this repo currently structures a network task this
way, but if one ever does, that's a real limitation, not a bug to silently
work around here.

Exit code: 1 if any Tier 1 (delete+recreate-same-connection) finding exists,
0 otherwise. Tier 2 findings are printed and counted but never fail the run
by themselves -- run.sh's --strict flag escalates them the same way it
already does for check_ssh_keys.py/check_keepass_freshness.py.
"""
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = [REPO_ROOT / "ansible" / "playbooks", REPO_ROOT / "ansible" / "tasks"]

RECURSE_KEYS = ("tasks", "pre_tasks", "post_tasks", "handlers", "block", "rescue", "always")
COMMAND_KEYS = ("command", "ansible.builtin.command", "shell", "ansible.builtin.shell")
TEMPLATE_KEYS = ("template", "ansible.builtin.template", "copy", "ansible.builtin.copy")

DELETE_RE = re.compile(r'nmcli\s+(?:connection|con)\s+delete\s+"?([A-Za-z0-9_.-]+)"?')
ADD_CONNAME_RE = re.compile(
    r'nmcli\s+(?:connection|con)\s+add\b.*?\bcon-name\s+"?([A-Za-z0-9_.-]+)"?', re.DOTALL
)
UP_RE = re.compile(r'nmcli\s+(?:connection|con)\s+up\s+"?([A-Za-z0-9_.-]+)"?')
NMCONNECTION_DEST_RE = re.compile(r'system-connections/([A-Za-z0-9_.-]+)\.nmconnection')


def iter_nodes(node):
    if isinstance(node, list):
        for item in node:
            yield from iter_nodes(item)
    elif isinstance(node, dict):
        yield node
        for key in RECURSE_KEYS:
            if key in node:
                yield from iter_nodes(node[key])


def task_command_text(node):
    for key in COMMAND_KEYS:
        if key in node:
            value = node[key]
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                return value.get("cmd", "") or " ".join(value.get("argv", []) or [])
    return ""


def task_template_dest(node):
    for key in TEMPLATE_KEYS:
        if key in node and isinstance(node[key], dict):
            return node[key].get("dest", "") or ""
    return ""


def scan_file(yml_path, tier1, tier2):
    try:
        docs = list(yaml.safe_load_all(yml_path.read_text(encoding="utf-8", errors="replace")))
    except yaml.YAMLError:
        return

    delete_names = set()
    add_names = set()
    templated_profiles = set()
    up_tasks = []  # (task_name, profile, has_when)

    for doc in docs:
        if doc is None:
            continue
        for node in iter_nodes(doc):
            match = NMCONNECTION_DEST_RE.search(task_template_dest(node))
            if match:
                templated_profiles.add(match.group(1))

            text = task_command_text(node)
            if not text or "nmcli" not in text:
                continue

            for m in DELETE_RE.finditer(text):
                delete_names.add(m.group(1))
            for m in ADD_CONNAME_RE.finditer(text):
                add_names.add(m.group(1))
            for m in UP_RE.finditer(text):
                up_tasks.append((node.get("name", "(unnamed task)"), m.group(1), "when" in node))

    for name in sorted(delete_names & add_names):
        tier1.append(
            f"{yml_path.relative_to(REPO_ROOT)}: nmcli connection '{name}' is both deleted "
            f"(nmcli con delete) and re-added (nmcli con add) in the same file -- delete+"
            f"recreate always reports 'changed' regardless of whether anything actually "
            f"differs, and if '{name}' is the connection the current session rides, deleting "
            f"an active connection deactivates it before recreating it. Use a templated "
            f".nmconnection keyfile + `nmcli connection reload` instead (see "
            f"roles/firewall/tasks/06_network_manager.yml, or bind9-dns.yml/rudder_server.yml/"
            f"salt/playbooks/10-master.yml's own 2026-07-21/22 fixes for this exact pattern)."
        )

    for task_name, profile, has_when in up_tasks:
        if profile in templated_profiles and not has_when:
            tier2.append(
                f"{yml_path.relative_to(REPO_ROOT)}: task '{task_name}' runs `nmcli connection "
                f"up {profile}` with no `when:` guard at all, and this same file also templates "
                f"{profile}.nmconnection -- if this playbook can rewrite {profile}'s live "
                f"address, bringing it up unconditionally risks stranding a session riding that "
                f"connection. Confirm this interface can never be the one Ansible is connected "
                f"through (matching roles/firewall/tasks/06_network_manager.yml's own reviewed "
                f"'nmcli con up lan' judgement call), or add a live-address-mismatch strand-"
                f"check (see that same file's nm_wan_activate_would_strand_session)."
            )


def main():
    yml_files = []
    for d in SCAN_DIRS:
        yml_files.extend(sorted(d.rglob("*.yml")))

    tier1 = []
    tier2 = []
    for f in yml_files:
        scan_file(f, tier1, tier2)

    print(
        f"Scanned {len(yml_files)} YAML file(s) under ansible/playbooks/ and ansible/tasks/ "
        f"for nmcli delete+recreate and ungated connection-up patterns."
    )

    if tier2:
        print(f"\n{len(tier2)} informational finding(s) (Tier 2 -- confirm by hand; --strict fails on this):")
        for t in tier2:
            print(f"  - {t}")

    if tier1:
        print(f"\n{len(tier1)} FAILURE(s) (Tier 1 -- delete+recreate of the same named connection):")
        for t in tier1:
            print(f"  - {t}")
        return 1

    print(
        "\nNo delete+recreate-same-connection antipattern found."
        + ("" if not tier2 else " (Tier 2 informational findings above still worth a look.)")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
