#!/usr/bin/env python3
"""
check_required_tools.py -- part of at_have_ryggen_fri.

Generalises the existing per-tool pattern (check_gitleaks.py/check 33,
check_ssh_keys.py/check 11, check_mermaid.py/check 13 each hand-roll this
same shape for ONE tool) across every tool a script meant to run on THIS
host -- the control node, or wherever an operator runs benarbejde/*.py
scripts by hand -- actually needs, informational by default, --strict fails.

Written 2026-08-07 after Robert's live frustration, 2026-08-06:
`kpcli_wrapper.py` failed outright (`keepassxc-cli` not installed) with
nothing in the harness having warned beforehand -- "the entire point of the
harness is to catch all this type of stuff." See
PLAN-harness-and-bootstrap-backlog-2026-08-06.md item 1 for the fuller
design discussion.

Deliberately scoped to CONTROL-NODE tools only (Robert's own explicit
priority, 2026-08-07: "concern yourself more with A"), not
bootstrap/web/provision/*.sh's own target-host tool needs (bc, nmcli, wg,
...) -- those scripts already self-heal via their own `command -v X ||
BOOTSTRAP_PKGS+=(x)` + apt-get pattern on the machine actually being
provisioned, checking for their presence on the control node wouldn't mean
anything (the tool doesn't need to exist here at all, only on whatever
fresh box the script runs against later). That's a genuinely different
problem -- "does each provisioning script's own self-heal list actually
cover everything it uses" -- tracked separately, not built here.

REQUIRED_TOOLS is hand-maintained, not auto-derived from scanning
benarbejde/*.py's own subprocess calls -- considered, rejected: most
control-node scripts (kpcli_wrapper.py, push_credentials_to_keepass.py)
invoke external tools via a single, stable, well-known name
(keepassxc-cli), and a handful of entries is easier to keep honest by
inspection than a regex over subprocess.run(...) call sites that would also
false-positive on internal/always-present commands (git, python3, ...).
Same "kept in sync by hand, deliberately small and curated" precedent as
check_keepass_freshness.py's own KNOWN_ROLES / GROUP_FOR_ROLE pair.

keepassxc-cli's own OS-aware install lines mirror kpcli_wrapper.py's own
hardcoded ones exactly (that file's `find_cli()`/`main()` already do this
same check standalone, at the point of use -- this harness check exists to
catch the same gap proactively, before an operator gets that far) -- except
corrected per Robert's own more precise 2026-08-07 answer for the apt case:
Debian ships the CLI either as its own `keepassxc-cli` package or bundled
inside `keepassxc-full`, depending on release/repo, not a plain
`keepassxc` the way brew/choco's single package covers both GUI and CLI.

passlib (check_type: python_module, added 2026-08-08) is a real live gap
found the hard way: `playbooks/salt/playbooks/20-saltgui.yml`'s own header
already documented this exact prerequisite ("the password_hash Jinja filter
... needs passlib installed on the CONTROL node") but nothing ever actually
checked for it -- confirmed missing on the real EXAANSCLD001, causing a
generic, undiagnostic "unknown error" when the `user` module tried to
template `salt_saltgui_password | password_hash('sha512')`. A Python
module isn't a PATH binary -- `shutil.which()` can never find it -- so this
needed a second check_type, not just a new REQUIRED_TOOLS entry.

Exit code: 0 unless a required tool is missing (informational; --strict
promotes any missing tool to a hard failure).
"""
import importlib.util
import platform
import shutil
import sys

REQUIRED_TOOLS = {
    "keepassxc-cli": {
        "check_type": "binary",
        "required_by": [
            "benarbejde/kpcli_wrapper.py",
            "benarbejde/push_credentials_to_keepass.py",
        ],
        "install": {
            "Linux": "apt install keepassxc-cli (or keepassxc-full, if keepassxc-cli isn't in your repo)",
            "Darwin": "brew install keepassxc",
            "Windows": "choco install keepassxc",
        },
    },
    "passlib": {
        "check_type": "python_module",
        "required_by": [
            "ansible/playbooks/salt/playbooks/20-saltgui.yml "
            "(password_hash Jinja filter, control-node side only -- not needed on the target)",
        ],
        "install": {
            "Linux": "apt install python3-passlib",
            "Darwin": "brew install python3 && python3 -m pip install --user passlib "
                      "(no Homebrew formula for the module itself)",
            "Windows": "python -m pip install --user passlib",
        },
    },
}


def install_line_for_this_os(tool_install: dict) -> str:
    system = platform.system()
    line = tool_install.get(system)
    if line:
        return f"  {system}: {line}"
    # Unrecognised platform.system() value -- print every option rather than guess.
    return "\n".join(f"  {os_name}: {cmd}" for os_name, cmd in tool_install.items())


def is_present(tool: str, check_type: str) -> str | None:
    """Returns the thing found (path or module name) if present, else None."""
    if check_type == "python_module":
        return tool if importlib.util.find_spec(tool) is not None else None
    return shutil.which(tool)


def main() -> int:
    strict = "--strict" in sys.argv

    missing = []
    for tool, info in REQUIRED_TOOLS.items():
        found = is_present(tool, info.get("check_type", "binary"))
        if found:
            print(f"OK: {tool} ({found})")
            continue

        missing.append(tool)
        required_by = ", ".join(info["required_by"])
        print(f"MISSING: {tool} -- required by: {required_by}")
        print(install_line_for_this_os(info["install"]))

    if not missing:
        print(f"\nAll {len(REQUIRED_TOOLS)} required tool(s) present on this host.")
        return 0

    print(
        f"\n{len(missing)} required tool(s) missing on this host -- see above. "
        "Informational only unless --strict (a bare clone or CI runner genuinely "
        "might not have these; a host an operator actually runs these scripts from "
        "should)."
    )
    return 1 if strict else 0


if __name__ == "__main__":
    sys.exit(main())
