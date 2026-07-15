#!/usr/bin/env python3
"""
check_playbook_doc_coverage.py -- part of at_have_ryggen_fri.

Two related but distinct checks, catching "a playbook module shipped with
no documentation at all" -- the windows_hygiene/ gap found 2026-07-15 (six
real playbooks, zero doc coverage anywhere in the repo, until a docs-drift
audit happened to notice) is exactly the class of bug this exists to catch
automatically, going forward, without needing a human to stumble on it.

1. DIRECTORY README COVERAGE (hard fail): every ansible/playbooks/<module>/
   directory containing at least one real playbook (*.yml with a top-level
   hosts: key -- the same convention check 2's --syntax-check scan already
   uses to distinguish real plays from task-fragment files) must have its
   own README.md. Binary, zero false-positive risk.

2. ORPHANED PLAYBOOK FILES (warn only): every real playbook .yml file must
   be either (a) named -- its filename appearing verbatim -- somewhere in
   its own directory's README.md, ansible/README.md, or any file under
   docs/, or (b) the resolved target of an include_tasks/import_tasks/
   import_playbook from another tracked .yml file (internal sub-plays and
   task-fragments referenced only by automation, never expected to be
   prose-named on their own -- e.g. windows_bootstrap's numbered stage
   files, imported from site.yml). Warn, not fail -- matches
   check_doc_index.py's own precedent that a needs-human-triage finding
   shouldn't autofail a fresh clone (e.g. 10-rename.yml is deliberately
   not chained but is still prose-described in windows_bootstrap/README.md,
   not tabled -- a plain substring match already handles that correctly).

Exit code: 1 if any module directory lacks a README.md, 0 otherwise --
orphaned files never affect the exit code.
"""
import re
import sys
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAYBOOKS_DIR = REPO_ROOT / "ansible" / "playbooks"
DOCS_DIR = REPO_ROOT / "docs"
ANSIBLE_README = REPO_ROOT / "ansible" / "README.md"

HOSTS_RE = re.compile(r"^\s*hosts:", re.MULTILINE)
INCLUDE_KEYS = {
    "include_tasks", "ansible.builtin.include_tasks",
    "import_tasks", "ansible.builtin.import_tasks",
    "import_playbook", "ansible.builtin.import_playbook",
}
RECURSE_KEYS = ("tasks", "pre_tasks", "post_tasks", "handlers", "block", "rescue", "always")


def is_real_playbook(yml_path):
    try:
        text = yml_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(HOSTS_RE.search(text))


def iter_nodes(node):
    if isinstance(node, list):
        for item in node:
            yield from iter_nodes(item)
    elif isinstance(node, dict):
        yield node
        for key in RECURSE_KEYS:
            if key in node:
                yield from iter_nodes(node[key])


def find_included_targets(yml_path):
    """Resolved absolute paths this file include_tasks/import_tasks/
    import_playbook's to, relative to the file's own directory (matching
    check_references.py's own resolution rule for these keys)."""
    targets = set()
    try:
        docs = list(yaml.safe_load_all(yml_path.read_text(encoding="utf-8", errors="replace")))
    except yaml.YAMLError:
        return targets
    for doc in docs:
        if doc is None:
            continue
        for node in iter_nodes(doc):
            for key in INCLUDE_KEYS & node.keys():
                value = node[key]
                raw = value if isinstance(value, str) else (value or {}).get("file")
                if raw and isinstance(raw, str) and "{{" not in raw:
                    targets.add((yml_path.parent / raw).resolve())
    return targets


def main():
    module_dirs = sorted(p for p in PLAYBOOKS_DIR.iterdir() if p.is_dir())

    missing_readme = []
    all_playbooks = []   # (module_dir, yml_path)
    referenced = set()   # resolved paths targeted by include_tasks/import_tasks/import_playbook

    for module_dir in module_dirs:
        real_playbooks = [f for f in module_dir.rglob("*.yml") if is_real_playbook(f)]
        for f in module_dir.rglob("*.yml"):
            referenced |= find_included_targets(f)
        if not real_playbooks:
            continue
        all_playbooks.extend((module_dir, f) for f in real_playbooks)
        if not (module_dir / "README.md").exists():
            missing_readme.append(module_dir.relative_to(REPO_ROOT))

    ansible_readme_text = (
        ANSIBLE_README.read_text(encoding="utf-8", errors="replace") if ANSIBLE_README.exists() else ""
    )
    docs_text = ""
    for f in DOCS_DIR.rglob("*"):
        if f.is_file() and f.suffix in (".md", ".txt"):
            docs_text += f.read_text(encoding="utf-8", errors="replace")

    orphans = []
    for module_dir, f in all_playbooks:
        if f.resolve() in referenced:
            continue
        readme = module_dir / "README.md"
        readme_text = readme.read_text(encoding="utf-8", errors="replace") if readme.exists() else ""
        if f.name in readme_text or f.name in ansible_readme_text or f.name in docs_text:
            continue
        orphans.append(f.relative_to(REPO_ROOT))

    print(f"Checked {len(module_dirs)} playbook module director(y/ies) under ansible/playbooks/, "
          f"{len(all_playbooks)} real playbook file(s) (top-level hosts: key).")

    if orphans:
        print(f"\n{len(orphans)} playbook file(s) not named in any README/docs, and not the "
              f"resolved target of an include_tasks/import_tasks/import_playbook elsewhere "
              f"(orphaned -- needs human triage, not a hard failure):")
        for o in orphans:
            print(f"  - {o}")

    if missing_readme:
        print(f"\n{len(missing_readme)} playbook module directory/ies with no README.md:")
        for m in missing_readme:
            print(f"  - {m}/")
        return 1

    print("\nEvery playbook module directory has a README.md." +
          (" (orphans above are a warning, not a failure.)" if orphans else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
