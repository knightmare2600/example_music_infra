#!/usr/bin/env python3
"""
check_collection_requirements.py -- part of at_have_ryggen_fri.

Found live 2026-07-28: a real windows_bootstrap/site.yml run against
EXADCSCLD001 completed end to end, but the very next module tried --
truenas/site.yml against EXANASFAL001 -- failed outright with "No module
named 'ansible_collections.arensb'". ansible/playbooks/truenas/
requirements.yml has always existed and correctly lists arensb.truenas, but
nothing on the control node's own control-node-setup path had ever run
`ansible-galaxy collection install -r requirements.yml` for it -- the
collection was only ever installed on the sandbox that built the module,
a different machine. Checked whether this was a one-off: it wasn't --
ansible/playbooks/windows_dc/ genuinely uses ansible.windows.* modules
(win_feature/win_reboot/win_shell -- real DC promotion, not builtin) and has
NO requirements.yml at all, and no README mention of installing anything.

Two related checks, both hard-fail (this is exactly the class of gap that
should never reach a live run silently):

1. EVERY collection FQCN module actually used in a playbook module directory
   (ansible/playbooks/<module>/, matching check_playbook_doc_coverage.py's
   own module-directory convention) must be declared in that directory's own
   requirements.yml. Detected by walking real YAML task nodes (not a blind
   text regex over the whole file -- that catches false positives like
   `item.item.fqdn` or `example1.co.uk` in a URL/Jinja string; a dotted
   three-part string only appears as a literal YAML mapping KEY when it's a
   genuine module reference, values don't count).

2. EVERY module directory that has a requirements.yml must document the
   install command somewhere a human would actually see it before running
   the playbook -- its own README.md, or (for modules without a directory
   README, e.g. a single-file module) the playbook's own top-of-file
   comment block. "ansible-galaxy collection install" is the literal string
   checked for -- matches this repo's own consistent convention across
   truenas/windows_bootstrap/windows_adschema's READMEs already.

ansible.builtin.* and ansible.legacy.* are never flagged -- no collection
install needed for either, ever.

Exit code: 1 if any collection is used without being declared in a
requirements.yml, or any requirements.yml exists without a documented
install command; 0 otherwise.
"""
import re
import sys
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS_DIR = REPO_ROOT / "ansible" / "playbooks"

FQCN_KEY_RE = re.compile(r"^([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)\.[a-z][a-z0-9_]+$")
BUILTIN_NAMESPACES = {"ansible.builtin", "ansible.legacy"}
RECURSE_KEYS = ("tasks", "pre_tasks", "post_tasks", "handlers", "block", "rescue", "always")
INSTALL_MARKER = "ansible-galaxy collection install"


def iter_nodes(node):
    if isinstance(node, list):
        for item in node:
            yield from iter_nodes(item)
    elif isinstance(node, dict):
        yield node
        for key in RECURSE_KEYS:
            if key in node:
                yield from iter_nodes(node[key])


def collections_used_in_file(yml_path):
    used = set()
    try:
        docs = list(yaml.safe_load_all(yml_path.read_text(encoding="utf-8", errors="replace")))
    except yaml.YAMLError:
        return used
    for doc in docs:
        if doc is None:
            continue
        for node in iter_nodes(doc):
            for key in node.keys():
                if not isinstance(key, str):
                    continue
                m = FQCN_KEY_RE.match(key)
                if m and m.group(1) not in BUILTIN_NAMESPACES:
                    used.add(m.group(1))
    return used


def declared_collections(requirements_path):
    try:
        data = yaml.safe_load(requirements_path.read_text(encoding="utf-8", errors="replace"))
    except yaml.YAMLError:
        return set()
    if not isinstance(data, dict):
        return set()
    declared = set()
    for entry in data.get("collections", []) or []:
        name = entry.get("name") if isinstance(entry, dict) else entry
        if isinstance(name, str):
            declared.add(name)
    return declared


def main():
    module_dirs = sorted(p for p in PLAYBOOKS_DIR.iterdir() if p.is_dir())

    undeclared = []   # (module_dir, {missing collections})
    undocumented = []  # module_dir with a requirements.yml but no install command anywhere
    checked_modules = 0

    for module_dir in module_dirs:
        used = set()
        for f in module_dir.rglob("*.yml"):
            used |= collections_used_in_file(f)
        if not used:
            continue
        checked_modules += 1

        req_path = module_dir / "requirements.yml"
        declared = declared_collections(req_path) if req_path.exists() else set()
        missing = used - declared
        if missing:
            undeclared.append((module_dir.relative_to(REPO_ROOT), sorted(missing)))

        if req_path.exists():
            readme = module_dir / "README.md"
            text_blobs = []
            if readme.exists():
                text_blobs.append(readme.read_text(encoding="utf-8", errors="replace"))
            for f in module_dir.glob("*.yml"):
                text_blobs.append(f.read_text(encoding="utf-8", errors="replace"))
            if not any(INSTALL_MARKER in blob for blob in text_blobs):
                undocumented.append(module_dir.relative_to(REPO_ROOT))

    print(f"Checked {len(module_dirs)} playbook module director(y/ies) under ansible/playbooks/, "
          f"{checked_modules} using at least one non-builtin collection module.")

    if undeclared:
        print(f"\n{len(undeclared)} module(s) using a collection not declared in their own "
              f"requirements.yml (missing entirely, or requirements.yml itself missing):")
        for mod, missing in undeclared:
            req = mod / "requirements.yml"
            state = "no requirements.yml at all" if not (REPO_ROOT / req).exists() else "requirements.yml exists but is incomplete"
            print(f"  - {mod}/  ({state}) -- missing: {', '.join(missing)}")

    if undocumented:
        print(f"\n{len(undocumented)} module(s) with a requirements.yml but no "
              f"'{INSTALL_MARKER}' string anywhere in their own README.md or playbook files "
              f"-- a fresh control node has no way to discover it needs to run one:")
        for mod in undocumented:
            print(f"  - {mod}/")

    if undeclared or undocumented:
        return 1

    print("\nEvery collection module used is declared in a requirements.yml, and every "
          "requirements.yml is documented with its install command.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
