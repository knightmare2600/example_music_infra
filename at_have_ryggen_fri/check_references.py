#!/usr/bin/env python3
"""
check_references.py -- part of at_have_ryggen_fri ("to have your back covered").

Walks every *.yml file under ansible/playbooks/ and confirms every file it
references by a literal (non-Jinja) path actually exists on disk:
  copy / ansible.builtin.copy / ansible.windows.win_copy   -> src:
  template / ansible.builtin.template                      -> src:
  include_tasks / import_tasks / import_playbook            -> the path itself
  (and their ansible.builtin.* fully-qualified equivalents)

Paths containing "{{" are dynamic and can't be resolved statically in
general -- BUT a common, checkable special case in this repo is a
`loop: "{{ some_group_vars_list }}"` combined with `src: "...{{ item.attr }}"`
(50-binaries.yml's x86_64/arm64 binary deployment). some_group_vars_list is
itself a static list defined in group_vars, so item.attr can genuinely be
resolved for every loop item -- this is done below (LOOP_VAR_RE /
resolve_group_vars_lists()) rather than silently lumping these in with
truly-dynamic paths (host_arch, a runtime-detected fact, is left dynamic).

These loop-resolved paths are reported separately, as "drop-in assets" --
this repo deliberately does not commit some binaries (see
playbooks/windows_bootstrap/playbooks/files/README.md; the .gitkeep files
in files/x86_64//arm64/ are the tell), so a missing one is expected on a
fresh clone, not a broken reference -- but it should be named explicitly,
not silently absorbed into a "skipped N dynamic" count.

Resolution rules (matching this repo's own conventions, confirmed by reading
real tasks before writing this, not assumed):
  - include_tasks / import_tasks / import_playbook: relative to the
    directory of the file that references them (e.g. 00-preflight.yml's
    "../tasks/foo.yml" resolves from playbooks/<x>/playbooks/).
  - copy / win_copy / template: relative to the referencing file's own
    directory, OR to a files/ (copy/win_copy) or templates/ (template)
    subdirectory of it -- this is Ansible's own documented search path,
    used unmodified by roles and standalone playbooks alike.

Exit code: 0 if every static reference resolved, 1 otherwise. Missing
drop-in assets do not affect the exit code -- they're expected, and the
whole point of this script is to tell you which ones, not to fail a fresh
clone that hasn't had them dropped in yet.
"""
import re
import sys
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS_DIR = REPO_ROOT / "ansible" / "playbooks"
GROUP_VARS_DIR = REPO_ROOT / "ansible" / "configs" / "inventory" / "group_vars"

COPY_KEYS = {"copy", "ansible.builtin.copy", "win_copy", "ansible.windows.win_copy"}
TEMPLATE_KEYS = {"template", "ansible.builtin.template"}
INCLUDE_KEYS = {
    "include_tasks", "ansible.builtin.include_tasks",
    "import_tasks", "ansible.builtin.import_tasks",
    "import_playbook", "ansible.builtin.import_playbook",
}

RECURSE_KEYS = ("tasks", "pre_tasks", "post_tasks", "handlers", "block", "rescue", "always")
LOOP_VAR_RE = re.compile(r"^\{\{\s*(\w+)")
ITEM_ATTR_RE = re.compile(r"\{\{\s*item\.(\w+)\s*\}\}")


def load_group_vars_index():
    """varname -> list of (source_file, list_value) for every top-level
    group_vars key whose value is a list -- e.g. binaries_extra is defined
    once per relevant group (windows_server/windows_desktop/windows_laptop),
    each with its own list of dicts."""
    index = {}
    if not GROUP_VARS_DIR.is_dir():
        return index
    for f in GROUP_VARS_DIR.rglob("*.yml"):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        for key, value in data.items():
            if isinstance(value, list):
                index.setdefault(key, []).append((f, value))
    return index


def resolve_loop_item_paths(raw_src, loop_expr, group_vars_index):
    """Given src: "...{{ item.attr }}..." and loop: "{{ varname | ... }}",
    return a list of (source_file, resolved_path_str) for every item in
    every group_vars definition of varname -- or None if loop_expr isn't a
    simple variable reference, or raw_src references something other than
    item.<attr> (still genuinely dynamic, e.g. host_arch)."""
    m = LOOP_VAR_RE.match(loop_expr.strip())
    if not m:
        return None
    varname = m.group(1)
    definitions = group_vars_index.get(varname)
    if not definitions:
        return None

    # Anything other than item.<attr> left in the template after stripping
    # those out means it's still genuinely dynamic (e.g. host_arch) --
    # don't pretend we can resolve it.
    remainder = ITEM_ATTR_RE.sub("", raw_src)
    if "{{" in remainder:
        return None

    resolved = []
    for source_file, items in definitions:
        for item in items:
            if not isinstance(item, dict):
                continue
            path_str = ITEM_ATTR_RE.sub(lambda mo: str(item.get(mo.group(1), "")), raw_src)
            resolved.append((source_file, path_str))
    return resolved


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


def check_file(yml_path, broken, skipped_dynamic, checked_count, drop_in, group_vars_index):
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
                    loop_expr = node.get("loop")
                    resolved = (
                        resolve_loop_item_paths(raw, loop_expr, group_vars_index)
                        if isinstance(loop_expr, str) else None
                    )
                    if resolved is None:
                        skipped_dynamic[0] += 1
                        continue
                    for source_file, path_str in resolved:
                        checked_count[0] += 1
                        candidates = resolve_candidates(yml_path, path_str, key)
                        if not any(c.exists() for c in candidates):
                            rel_candidates = [str(c.relative_to(REPO_ROOT)) for c in candidates]
                            drop_in.append((yml_path, key, path_str,
                                             source_file.relative_to(REPO_ROOT), rel_candidates))
                    continue
                checked_count[0] += 1
                candidates = resolve_candidates(yml_path, raw, key)
                if not any(c.exists() for c in candidates):
                    rel_candidates = [str(c.relative_to(REPO_ROOT)) for c in candidates]
                    broken.append((yml_path, key, f'"{raw}" -- tried: {rel_candidates}'))


def main():
    broken = []
    drop_in = []
    skipped_dynamic = [0]
    checked_count = [0]
    group_vars_index = load_group_vars_index()

    yml_files = sorted(PLAYBOOKS_DIR.rglob("*.yml"))
    for yml_path in yml_files:
        check_file(yml_path, broken, skipped_dynamic, checked_count, drop_in, group_vars_index)

    print(f"Scanned {len(yml_files)} YAML files under ansible/playbooks/.")
    print(f"Checked {checked_count[0]} literal + loop-resolved file references; "
          f"skipped {skipped_dynamic[0]} genuinely dynamic references "
          f"(runtime facts like host_arch).")

    if drop_in:
        print(f"\n{len(drop_in)} drop-in asset(s) referenced via a loop over group_vars "
              f"but not present on disk (expected on a fresh clone -- see "
              f"playbooks/windows_bootstrap/playbooks/files/README.md):")
        for path, key, resolved_src, source_file, candidates in drop_in:
            rel = path.relative_to(REPO_ROOT)
            print(f"  [{key}] {rel}: \"{resolved_src}\" (from {source_file}) -- tried: {candidates}")

    if broken:
        print(f"\n{len(broken)} BROKEN reference(s):")
        for path, key, detail in broken:
            rel = path.relative_to(REPO_ROOT)
            print(f"  [{key}] {rel}: {detail}")
        return 1

    print("\nAll literal and loop-resolved file references either exist or are known drop-in assets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
