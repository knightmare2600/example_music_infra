#!/usr/bin/env python3
"""
check_jinja_test_names.py -- part of at_have_ryggen_fri.

Found live 2026-09-21: `select('length')` in 30-ad-users.yml ("Build
lowercase set of existing OU DNs" task) -- 'length' is a real, valid Jinja
token, but it's a FILTER name, not a TEST name, so select() (which expects
a test) only fails at *render* time ("TemplateRuntimeError: No test named
'length'"), not at parse/compile time. Robert's own framing: not "invalid
syntax", more "the wrong tool for the job" -- a real Jinja construct, just
the wrong kind, in a slot expecting a different kind.

Verified live, same investigation: neither of the two obvious "already have
this" tools catches this bug class. `ansible-lint` (even -p production)
only flagged an unrelated cosmetic rule -- its jinja rule checks template
*formatting*, not whether a named filter/test actually exists.
`ansible-playbook --syntax-check` validates YAML structure and Jinja
*syntax* only, never attempts to render, so a syntactically-valid-but-
semantically-wrong test name is invisible to it by design. A bespoke check
is needed -- this is it.

What it does: greps every real task file under ansible/playbooks/ for
select()/reject()/selectattr()/rejectattr() calls with a quoted
string-literal test-name argument (select/reject: 1st arg; selectattr/
rejectattr: 2nd arg, since the 1st is the attribute name), and flags any
name that isn't a real, currently-registered Jinja test.

The known-good name list is NOT a hardcoded snapshot -- it's queried live
from `ansible-doc -t test -l` (this control node's own real, currently-
installed ansible-core plus whatever collections this repo's own
requirements.yml files actually declare), so this check can never drift out
of sync with a real ansible-core upgrade or a newly-added collection
dependency the way a hand-maintained list would.

Exit code: 1 if any invalid test name is found, 0 otherwise.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS_DIR = REPO_ROOT / "ansible" / "playbooks"

# select('test', ...) / reject('test', ...) -- test name is the 1st arg, if quoted.
SELECT_REJECT_RE = re.compile(r"\b(select|reject)\(\s*(?:'([^']*)'|\"([^\"]*)\")")
# selectattr('attr', 'test', ...) / rejectattr('attr', 'test', ...) -- test name is
# the 2nd arg, if quoted (1st is always the attribute name, never a test).
SELECTATTR_REJECTATTR_RE = re.compile(
    r"\b(selectattr|rejectattr)\(\s*(?:'[^']*'|\"[^\"]*\")\s*,\s*(?:'([^']*)'|\"([^\"]*)\")"
)


def load_known_test_names(problems):
    """Queried live from ansible-doc, not hardcoded -- see module docstring.
    Scoped to ansible.builtin (always available) plus every collection this
    repo's own requirements.yml files actually declare as a dependency --
    ansible.utils/ovirt.ovirt etc. showing up in a full `ansible-doc -t test
    -l` are real Jinja tests too, just not ones this repo could actually use
    without a collection it never installs, so a bare name matching one of
    those would be just as wrong here as a genuinely made-up name."""
    declared_collections = {"ansible.builtin"}
    for req_file in PLAYBOOKS_DIR.rglob("requirements.yml"):
        for line in req_file.read_text().splitlines():
            m = re.search(r"^\s*-\s*name:\s*([\w.]+)", line)
            if m:
                declared_collections.add(m.group(1).strip())

    try:
        result = subprocess.run(
            ["ansible-doc", "-t", "test", "-l"],
            capture_output=True, text=True, check=True,
        )
    except Exception as e:
        problems.append(f"could not run 'ansible-doc -t test -l' -- {e}")
        return None, declared_collections

    names = set()
    for line in result.stdout.splitlines():
        fqcn = line.split()[0] if line.split() else ""
        if "." not in fqcn:
            continue
        collection, _, bare_name = fqcn.rpartition(".")
        if collection in declared_collections:
            names.add(bare_name)
    return names, declared_collections


def check_file(path, known_names, problems):
    lines = path.read_text().splitlines()
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # Strip a trailing same-line comment so a real call followed by an
        # explanatory "# ..." doesn't get the comment's own text scanned too
        # -- crude (doesn't understand quoted '#' inside a string) but safe
        # enough for this repo's own style, which never puts a literal '#'
        # inside a select()/selectattr() string argument.
        code_part = line.split(" #", 1)[0] if " #" in line else line

        for m in SELECT_REJECT_RE.finditer(code_part):
            test_name = m.group(2) if m.group(2) is not None else m.group(3)
            if test_name and test_name not in known_names:
                problems.append(
                    f"{path.relative_to(REPO_ROOT)}:{lineno}: "
                    f"{m.group(1)}('{test_name}', ...) -- '{test_name}' is not a real "
                    f"Jinja test name (it may be a filter, e.g. 'length' -- filters and "
                    f"tests are different things and not interchangeable here)"
                )

        for m in SELECTATTR_REJECTATTR_RE.finditer(code_part):
            test_name = m.group(2) if m.group(2) is not None else m.group(3)
            if test_name and test_name not in known_names:
                problems.append(
                    f"{path.relative_to(REPO_ROOT)}:{lineno}: "
                    f"{m.group(1)}(..., '{test_name}', ...) -- '{test_name}' is not a real "
                    f"Jinja test name (it may be a filter, e.g. 'length' -- filters and "
                    f"tests are different things and not interchangeable here)"
                )


def main():
    problems = []
    known_names, declared_collections = load_known_test_names(problems)
    if known_names is None:
        print("\n".join(problems))
        return 1

    yml_files = sorted(PLAYBOOKS_DIR.rglob("*.yml"))
    for path in yml_files:
        check_file(path, known_names, problems)

    print(
        f"Checked {len(yml_files)} YAML file(s) under ansible/playbooks/ for "
        f"select()/reject()/selectattr()/rejectattr() calls using an invalid Jinja test "
        f"name, against {len(known_names)} real test name(s) known to "
        f"{', '.join(sorted(declared_collections))} (queried live via 'ansible-doc -t test -l', "
        f"not a hardcoded snapshot)."
    )

    if problems:
        print(f"\n{len(problems)} problem(s) found:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("No invalid Jinja test names found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
