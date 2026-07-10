#!/usr/bin/env python3
"""
check_references.py -- part of at_have_ryggen_fri ("to have your back covered").

Walks every *.yml file under ansible/playbooks/ and confirms every file it
references by a literal (non-Jinja) path actually exists on disk:
  copy / ansible.builtin.copy / ansible.windows.win_copy   -> src:
  template / ansible.builtin.template                      -> src:
  include_tasks / import_tasks / import_playbook            -> the path itself
  (and their ansible.builtin.* fully-qualified equivalents)

Paths containing "{{" are dynamic (host_arch, item.src, etc.) and can't be
resolved statically -- counted separately, not treated as failures.

Resolution rules (matching this repo's own conventions, confirmed by reading
real tasks before writing this, not assumed):
  - include_tasks / import_tasks / import_playbook: relative to the
    directory of the file that references them (e.g. 00-preflight.yml's
    "../tasks/foo.yml" resolves from playbooks/<x>/playbooks/).
  - copy / win_copy / template: relative to the referencing file's own
    directory, OR to a files/ (copy/win_copy) or templates/ (template)
    subdirectory of it -- this is Ansible's own documented search path,
    used unmodified by roles and standalone playbooks alike.

Exit code: 0 if every static reference resolved, 1 otherwise.
"""
import sys
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAYBOOKS_DIR = REPO_ROOT / "ansible" / "playbooks"

COPY_KEYS = {"copy", "ansible.builtin.copy", "win_copy", "ansible.windows.win_copy"}
TEMPLATE_KEYS = {"template", "ansible.builtin.template"}
INCLUDE_KEYS = {
    "include_tasks", "ansible.builtin.include_tasks",
    "import_tasks", "ansible.builtin.import_tasks",
    "import_playbook", "ansible.builtin.import_playbook",
}

RECURSE_KEYS = ("tasks", "pre_tasks", "post_tasks", "handlers", "block", "rescue", "always")


def iter_nodes(node):
    """Yield every dict encountered anywhere in a parsed playbook/task-file tree."""
    if isinstance(node, list):
        for item in node:
            yield from iter_nodes(item)
    elif isinstance(node, dict):
        yield node
        for key in RECURSE_KEYS:
            if key in node:
                yield from iter_nodes(node[key])


def is_dynamic(path_str):
    return "{{" in path_str


def role_root(referencing_file):
    """If referencing_file sits under a .../roles/<name>/ tree, return that
    role's root dir (roles/<name>/) -- Ansible resolves template:/copy: src
    relative to the ROLE root's templates//files/, not the tasks/ file's own
    directory. This repo has exactly one role (firewallme/roles/firewall),
    found empirically while writing this checker -- the naive
    "task_dir/templates/" guess produced false positives against it."""
    parts = referencing_file.parts
    for i, part in enumerate(parts):
        if part == "roles" and i + 1 < len(parts):
            return Path(*parts[: i + 2])
    return None


def resolve_candidates(referencing_file, raw_path, key):
    base = referencing_file.parent
    candidates = []
    if key in INCLUDE_KEYS:
        candidates.append(base / raw_path)
        return candidates
    if key in COPY_KEYS:
        candidates += [base / raw_path, base / "files" / raw_path]
    elif key in TEMPLATE_KEYS:
        candidates += [base / raw_path, base / "templates" / raw_path]
    else:
        candidates.append(base / raw_path)

    role = role_root(referencing_file)
    if role is not None:
        subdir = "files" if key in COPY_KEYS else "templates"
        candidates.append(role / subdir / raw_path)

    return candidates


def check_file(yml_path, broken, skipped_dynamic, checked_count):
    try:
        text = yml_path.read_text(encoding="utf-8")
        docs = list(yaml.safe_load_all(text))
    except yaml.YAMLError as e:
        broken.append((yml_path, "include_tasks/copy/etc scan", f"YAML parse error: {e}"))
        return

    for doc in docs:
        if doc is None:
            continue
        for node in iter_nodes(doc):
            for key in (COPY_KEYS | TEMPLATE_KEYS | INCLUDE_KEYS) & node.keys():
                value = node[key]
                # copy/template's src is a subkey; include_*/import_* the value is the path itself
                if key in INCLUDE_KEYS:
                    raw = value if isinstance(value, str) else (value or {}).get("file")
                else:
                    raw = (value or {}).get("src") if isinstance(value, dict) else None
                if not raw or not isinstance(raw, str):
                    continue
                if is_dynamic(raw):
                    skipped_dynamic[0] += 1
                    continue
                checked_count[0] += 1
                candidates = resolve_candidates(yml_path, raw, key)
                if not any(c.exists() for c in candidates):
                    rel_candidates = [str(c.relative_to(REPO_ROOT)) for c in candidates]
                    broken.append((yml_path, key, f'"{raw}" -- tried: {rel_candidates}'))


def main():
    broken = []
    skipped_dynamic = [0]
    checked_count = [0]

    yml_files = sorted(PLAYBOOKS_DIR.rglob("*.yml"))
    for yml_path in yml_files:
        check_file(yml_path, broken, skipped_dynamic, checked_count)

    print(f"Scanned {len(yml_files)} YAML files under ansible/playbooks/.")
    print(f"Checked {checked_count[0]} literal file references; "
          f"skipped {skipped_dynamic[0]} dynamic (Jinja) references.")

    if broken:
        print(f"\n{len(broken)} BROKEN reference(s):")
        for path, key, detail in broken:
            rel = path.relative_to(REPO_ROOT)
            print(f"  [{key}] {rel}: {detail}")
        return 1

    print("All literal file references resolved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
