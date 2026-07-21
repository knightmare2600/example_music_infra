#!/usr/bin/env python3
"""
check_salt_states.py -- part of at_have_ryggen_fri.

Salt's own equivalent of check 2 (ansible-playbook --syntax-check) plus a
couple of Salt-specific structural checks that have no Ansible analogue.
Every `.sls` file is Jinja *before* it's YAML -- a broken Jinja expression or
an undefined variable never shows up as a YAML error until a real minion
actually applies the state, which this harness never does (see run.sh's own
"nothing here touches a real host" guarantee). This renders every `.sls`
under salt/states/ with a generic mock grains/pillar/salt context and
confirms the result is valid YAML, the same "does this even parse" bar
check 2 sets for Ansible.

Three checks, in order:

  1. Render + parse -- every salt/states/**/*.sls (excluding _modules/, which
     is plain Python) renders via Jinja2 (StrictUndefined -- an undefined
     grain/pillar lookup that isn't guarded with .get()/default() is a real
     bug, not something to silently paper over) and the result parses as
     YAML. Uses a generic mock for every `salt['module.function'](...)` call
     found in these files today (cmd.run, file.*, grains.get, reg.read_value,
     user.info) -- a file using one this mock doesn't know about fails with a
     clear "unknown salt function" error naming exactly what to add, rather
     than a confusing downstream crash.

  2. top.sls / pillar/top.sls target validity -- every state name listed in
     salt/states/top.sls and every pillar name in salt/pillar/top.sls
     resolves to a real file (either <name>.sls or <name>/init.sls) --
     the same "does this reference actually exist" check
     check_references.py already does for Ansible's include_tasks/template
     paths, applied to Salt's own top-file mechanism.

  3. messagetype consistency -- every `messagetype:` value used in a
     screenprint.screen_print module.run call across all of salt/states/ is
     one screenprint.py's own MESSAGETYPE_COLOR dict actually maps to a
     colour (read directly from the module, not a hand-copied list here --
     if that dict ever changes, this check moves with it automatically).
     Added after `messagetype: "warn"` (not a real value -- only "warning"
     is) sat in bespoke_app_install's original source silently falling
     through to no colour at all, found by eye during a 2026-07-21 port, not
     by anything in this harness -- this check exists so the next one like
     it fails loudly instead.

Also folds in doc coverage for salt/ specifically: every real module
directory under salt/states/ (excluding _modules/) is named somewhere in
salt/README.md's own tree listing -- same spirit as
check_playbook_doc_coverage.py (18), scoped to Salt instead of Ansible
playbooks, since salt/README.md is hand-maintained prose with no generator
to keep it honest otherwise.

Exit code: 0 if everything above holds, 1 if anything failed.
"""
import importlib.util
import sys
from pathlib import Path

import jinja2
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SALT_DIR = REPO_ROOT / "salt"
STATES_DIR = SALT_DIR / "states"
PILLAR_DIR = SALT_DIR / "pillar"
README = SALT_DIR / "README.md"
SCREENPRINT_MODULE = STATES_DIR / "_modules" / "screenprint.py"


class _RegValue:
    """Mimics Salt's reg.read_value return object -- callers read .vdata off it."""

    def __init__(self, vdata):
        self.vdata = vdata


def load_valid_messagetypes():
    spec = importlib.util.spec_from_file_location("screenprint", SCREENPRINT_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.MESSAGETYPE_COLOR.keys())


class MockSaltDispatch(dict):
    """salt['module.function'](*args) -- generic stand-ins for every real call
    found in salt/states/ today. An unmapped key raises a clear error naming
    itself, rather than crashing obscurely deeper in a render."""

    _HANDLERS = {
        "cmd.run": lambda *a, **kw: "mock cmd.run output",
        "file.directory_exists": lambda *a, **kw: False,
        "file.file_exists": lambda *a, **kw: False,
        "file.read": lambda *a, **kw: "1.0.0",
        "grains.get": lambda *a, **kw: (a[1] if len(a) > 1 else kw.get("default", "")),
        "reg.read_value": lambda *a, **kw: _RegValue("mock-value"),
        "user.info": lambda *a, **kw: {"groups": []},
    }

    def __getitem__(self, key):
        if key not in self._HANDLERS:
            raise KeyError(
                f"check_salt_states.py's mock doesn't know salt['{key}'] -- "
                f"add a generic stand-in to MockSaltDispatch._HANDLERS."
            )
        return self._HANDLERS[key]


MOCK_GRAINS = {
    "id": "EXAWKSCLD001",
    "apptype": "bespoke_app",
    "appversion": "none",
    "habitat": "production",
    "saltversion": "3008.1",
}
MOCK_PILLAR = {
    "sites": {"CLD": {"city": "CloudSite", "country": "Global", "entity": "Example Music Limited"}},
    "habitat": {},
    "bespoke_app": {"name": "bespoke_app", "version": "1.0.0"},
    "bespoke_app_data": {"EXAWKSCLD001": {"winuserid": "S-1-5-21-0-0-0-1000"}},
}


def render_and_parse(sls_path):
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    tmpl = env.from_string(sls_path.read_text())
    rendered = tmpl.render(grains=MOCK_GRAINS, pillar=MOCK_PILLAR, salt=MockSaltDispatch())
    return yaml.safe_load(rendered)


def check_render_and_parse(errors):
    sls_files = sorted(
        p for p in STATES_DIR.rglob("*.sls")
        if "_modules" not in p.relative_to(STATES_DIR).parts
    )
    for f in sls_files:
        rel = f.relative_to(REPO_ROOT)
        try:
            render_and_parse(f)
        except Exception as e:
            errors.append(f"{rel}: {type(e).__name__}: {e}")
    print(f"Rendered and parsed {len(sls_files)} .sls file(s) under salt/states/.")


def resolve_state_ref(name, base_dir):
    """A top.sls entry 'foo' means either foo.sls or foo/init.sls under base_dir."""
    return (base_dir / f"{name}.sls").exists() or (base_dir / name / "init.sls").exists()


def check_top_sls_targets(errors):
    top_sls = STATES_DIR / "top.sls"
    if not top_sls.exists():
        errors.append("salt/states/top.sls does not exist")
        return
    data = render_and_parse(top_sls)
    checked = 0
    for target_match, state_list in (data or {}).get("base", {}).items():
        for name in state_list or []:
            checked += 1
            if not resolve_state_ref(name, STATES_DIR):
                errors.append(
                    f"salt/states/top.sls: '{name}' (target '{target_match}') has no "
                    f"salt/states/{name}.sls or salt/states/{name}/init.sls"
                )
    print(f"Checked {checked} state reference(s) in salt/states/top.sls.")

    pillar_top = PILLAR_DIR / "top.sls"
    if not pillar_top.exists():
        errors.append("salt/pillar/top.sls does not exist")
        return
    pdata = render_and_parse(pillar_top)
    pchecked = 0
    for target_match, pillar_list in (pdata or {}).get("base", {}).items():
        for name in pillar_list or []:
            pchecked += 1
            if not resolve_state_ref(name, PILLAR_DIR):
                errors.append(
                    f"salt/pillar/top.sls: '{name}' (target '{target_match}') has no "
                    f"salt/pillar/{name}.sls or salt/pillar/{name}/init.sls"
                )
    print(f"Checked {pchecked} pillar reference(s) in salt/pillar/top.sls.")


def check_messagetypes(errors):
    valid = load_valid_messagetypes()
    sls_files = sorted(
        p for p in STATES_DIR.rglob("*.sls")
        if "_modules" not in p.relative_to(STATES_DIR).parts
    )
    checked = 0
    for f in sls_files:
        rel = f.relative_to(REPO_ROOT)
        for lineno, line in enumerate(f.read_text().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "messagetype:" not in stripped:
                continue
            value = stripped.split("messagetype:", 1)[1].strip().strip("'\",")
            checked += 1
            if value not in valid:
                errors.append(
                    f"{rel}:{lineno}: messagetype: '{value}' isn't one of screenprint.py's "
                    f"MESSAGETYPE_COLOR keys ({sorted(valid)}) -- falls through to no colour."
                )
    print(f"Checked {checked} messagetype value(s) against screenprint.py's own mapping.")


def check_doc_coverage(errors):
    if not README.exists():
        errors.append("salt/README.md does not exist")
        return
    readme_text = README.read_text()
    module_dirs = sorted(
        p.name for p in STATES_DIR.iterdir()
        if p.is_dir() and p.name != "_modules"
    )
    for name in module_dirs:
        if name not in readme_text:
            errors.append(
                f"salt/states/{name}/ isn't mentioned anywhere in salt/README.md"
            )
    print(f"Checked {len(module_dirs)} salt/states/ module director(y/ies) against salt/README.md.")


def main():
    errors = []
    check_render_and_parse(errors)
    check_top_sls_targets(errors)
    check_messagetypes(errors)
    check_doc_coverage(errors)

    if errors:
        print(f"\n{len(errors)} salt state issue(s) found:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("All salt/ states render+parse cleanly, top.sls/pillar/top.sls targets all "
          "resolve, every messagetype is valid, and every module directory is documented.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
