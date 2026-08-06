#!/usr/bin/env python3
"""
check_data_refresh_doc_coverage.py -- part of at_have_ryggen_fri.

docs/refresh-after-data-changes.md (added 2026-08-06, Robert: "it needs a
small doc and harness checks to boot, where it says 'the following playbooks
need run on the following hosts'") names every playbook that includes
ansible/tasks/example_music_freshness_gate.yml -- the gate that gives a
playbook run through the control node an automatic, loud failure if
/etc/example-music/* is stale there. That list is exactly what makes the
doc's "what's already protected automatically" section true; if a future
playbook starts including the gate and the doc doesn't get updated, the doc
starts silently claiming a narrower protected set than actually exists --
not dangerous, but exactly the kind of doc/reality drift this harness exists
to catch (same principle as check_features.py, check 19).

This does NOT (and structurally cannot) check whether any specific live
host's OWN /etc/example-music/* copy is actually stale -- that's real
live-host state, out of scope for this clone-safe harness by design (see
check_control_node_freshness.py, check 24, and the doc's own final section
for why). This only checks that the STATIC list of gated playbooks --
derivable purely from grepping the repo -- is fully named in the doc that
claims to enumerate it.

A "gated playbook" here means: a git-tracked *.yml file under ansible/
that (a) references example_music_freshness_gate.yml, and (b) has its own
top-level `hosts:` key (i.e. it's a real play a human runs directly, not a
task fragment included by one of the four windows_adschema/windows_dc
playbooks that also happen to reference the gate).

Also checks ansible/playbooks/linux/tools.yml itself -- the one playbook
that actually DEPLOYS benarbejde/* to /etc/example-music/*, the doc's other
load-bearing fact -- is named in the doc.

Exit code: 1 if any gated playbook (or linux/tools.yml) isn't named
anywhere in the doc's text, 0 otherwise.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "refresh-after-data-changes.md"
GATE_TASK = "ansible/tasks/example_music_freshness_gate.yml"
DEPLOY_PLAYBOOK = "ansible/playbooks/linux/tools.yml"


def git_tracked_yaml():
    result = subprocess.run(
        ["git", "ls-files", "ansible/**/*.yml"],
        capture_output=True, text=True, cwd=REPO_ROOT, check=True,
    )
    return [REPO_ROOT / line for line in result.stdout.splitlines() if line.strip()]


def references_gate(path):
    text = path.read_text(encoding="utf-8")
    return "example_music_freshness_gate.yml" in text


def is_real_playbook(path):
    """Has its own top-level `hosts:` key -- excludes task fragments included by a real play."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("hosts:") or line.startswith("  hosts:"):
            return True
    return False


def main():
    if not DOC.is_file():
        print(f"ERROR: {DOC} not found.")
        return 1

    doc_text = DOC.read_text(encoding="utf-8")

    gated_playbooks = []
    for path in git_tracked_yaml():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel == GATE_TASK:
            continue
        if not path.is_file():
            continue
        if references_gate(path) and is_real_playbook(path):
            gated_playbooks.append(rel)

    required = sorted(gated_playbooks) + [DEPLOY_PLAYBOOK]

    print(f"Checked {len(required)} playbook(s) ({len(gated_playbooks)} gated via "
          f"{GATE_TASK} + {DEPLOY_PLAYBOOK} itself) against "
          f"{DOC.relative_to(REPO_ROOT)}'s text.")

    missing = [p for p in required if Path(p).name not in doc_text]

    if missing:
        print(f"\n{len(missing)} playbook(s) not named anywhere in "
              f"{DOC.relative_to(REPO_ROOT)}:")
        for p in missing:
            print(f"  - {p}")
        print(f"\nAdd each one to {DOC.relative_to(REPO_ROOT)}'s consumer list -- it's either "
              f"a newly-gated playbook (protected automatically) or, if it's "
              f"{DEPLOY_PLAYBOOK}, the doc's central claim about what actually deploys "
              f"/etc/example-music/*.")
        return 1

    print(f"\nEvery gated playbook and {DEPLOY_PLAYBOOK} are named in the doc.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
