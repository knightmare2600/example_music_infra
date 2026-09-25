#!/usr/bin/env python3
"""
check_vault_placeholders.py -- part of at_have_ryggen_fri.

Found live, 2026-09-25: `vault_ad_new_user_password` in
ansible/configs/inventory/group_vars/windows_dc/vault.yml was still the
literal placeholder string "CHANGEME" -- never actually set. That value is
only 8 characters, all-uppercase, no digit, no symbol, so it fails AD's
default password complexity policy outright, and every genuinely-new user
create using it (populate_ad's Section B0) failed live with "New-ADUser
failed: The password does not meet the length, complexity, or history
requirement of the domain." It had evidently worked once before, on the
now-decommissioned EXADCSFRD001 forest, most likely because that test
forest's password policy was relaxed for ease of testing -- a genuinely
fresh forest (EXADCSGOT001) with the standard, unmodified policy correctly
rejected it, and nothing had ever caught the unfilled placeholder itself
before that point.

Also found the same evening, checking further: none of this repo's
group_vars/*/vault.yml files have ever actually been ansible-vault
encrypted (confirmed via `ansible-vault view` itself failing with "Input is
not vault encrypted data", and via git history showing zero
$ANSIBLE_VAULT-prefixed content at any point) -- they're plain YAML that
just happens to be named vault.yml, with --ask-vault-pass consistently
prompting for a password that's never actually used to decrypt anything.
Robert's own call on whether/when to actually vault-encrypt these files;
this check works either way -- a genuinely encrypted file is skipped
(informational only, no placeholder inside it can be checked without the
vault password, which this harness deliberately never has), a plain-text
one (the current state of every vault.yml in this repo) is parsed and
checked directly.

A second placeholder found the same sweep, ansible/configs/inventory/
group_vars/all/vault.yml, had FOUR more unfilled CHANGEME values
(vault_local_admin_password, vault_domain_join_password,
vault_winrm_password, vault_snmp_write_community) -- none had been hit live
yet, but the same class of live failure was waiting for whichever playbook
reached them first. truenas_servers/vault.yml and rudder_servers/vault.yml
use a different placeholder convention ("REPLACE_WITH_..."/"UNSET") for the
same underlying problem -- this check recognises both conventions rather
than only the one that happened to be hit live first.

Deliberately does NOT flag a genuinely empty string ("") -- confirmed via
00-dc-preflight.yml's own vars_prompt (vault_dc_dsrm_password/
vault_dc_admin_password) that blank is this repo's own established,
intentional convention for "always prompt the operator interactively,
never store this one at rest", not an unfilled placeholder. Flagging that
too would be a false positive against a real, deliberate design choice.

Scope is every vault*.yml file under ansible/configs/inventory/group_vars/,
discovered dynamically (glob), not a hardcoded list of the 4 known today --
a future new vault.yml file is covered automatically. Deliberately does NOT
grep the whole repo for the word CHANGEME: check_jinja_test_names.py's own
history already showed the cost of a check matching prose/comment text that
merely mentions the thing it's checking for (e.g. ansible/playbooks/snmp/
sysinfo.yml's own inline guard message, which legitimately contains the
literal word CHANGEME as documentation, not as an unfilled value) -- scoping
to real vault.yml files and parsing them as structured YAML (checking
VALUES, not raw text) avoids that whole false-positive class by construction.

Exit code: 0 if no vault*.yml file has an unfilled placeholder value, 1 if
any do (a real, unaddressed security/functionality gap, not advisory).
"""
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GROUP_VARS_DIR = REPO_ROOT / "ansible" / "configs" / "inventory" / "group_vars"

# Case-insensitive. PLACEHOLDER_EXACT must match the WHOLE value -- these are
# short/generic enough (xxx, tbd, ...) that a "contains" check would risk a
# false positive against a real value that happens to contain one incidentally.
# PLACEHOLDER_MARKERS only need to appear ANYWHERE in the value -- found live,
# rudder_servers/vault.yml's rudder_admin_password is "$2y$12$REPLACE_WITH_
# BCRYPT_HASH", a real bcrypt-format prefix ($2y$12$) followed by the actual
# placeholder text, not a plain "replace_with"-prefixed string -- a
# startswith()-only check misses this shape entirely. Covers every convention
# actually found in this repo's own vault.yml files (CHANGEME, UNSET,
# REPLACE_WITH_...) plus a couple of other extremely common ones.
PLACEHOLDER_EXACT = {"changeme", "change_me", "unset", "todo", "fixme", "xxx", "tbd", "n/a"}
PLACEHOLDER_MARKERS = ("replace_with", "replace-with", "insert_", "<your_", "changeme")


def is_placeholder(value):
    if not isinstance(value, str):
        return False
    v = value.strip().lower()
    if v == "":
        return False  # intentional "always prompt, never store" convention -- not a placeholder
    if v in PLACEHOLDER_EXACT:
        return True
    return any(m in v for m in PLACEHOLDER_MARKERS)


def walk(value, path):
    """Yield (path, value) for every scalar leaf in a possibly-nested structure --
    every real vault.yml in this repo today is a flat mapping, but this doesn't
    assume that stays true."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield from walk(v, path + [str(k)])
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from walk(v, path + [f"[{i}]"])
    else:
        yield (path, value)


def main():
    vault_files = sorted(GROUP_VARS_DIR.glob("*/vault.yml"))
    if not vault_files:
        print(f"No vault.yml files found under {GROUP_VARS_DIR} -- nothing to check.")
        return 0

    checked_files = 0
    skipped_encrypted = []
    failures = []

    for path in vault_files:
        rel = path.relative_to(REPO_ROOT)
        text = path.read_text(encoding="utf-8", errors="replace")

        if text.lstrip().startswith("$ANSIBLE_VAULT"):
            skipped_encrypted.append(rel)
            continue

        try:
            data = yaml.safe_load(text) or {}
        except yaml.YAMLError as e:
            failures.append((rel, ["<parse error>"], str(e)))
            continue

        checked_files += 1
        for key_path, value in walk(data, []):
            if is_placeholder(value):
                failures.append((rel, key_path, value))

    print(f"Checked {checked_files} plain-text vault.yml file(s) under {GROUP_VARS_DIR.relative_to(REPO_ROOT)}/.")
    if skipped_encrypted:
        print(f"{len(skipped_encrypted)} genuinely ansible-vault encrypted file(s) skipped (can't check without the vault password, which this harness never has):")
        for rel in skipped_encrypted:
            print(f"  {rel}")

    if failures:
        print(f"\n{len(failures)} unfilled placeholder value(s) found:")
        for rel, key_path, value in failures:
            print(f"  {rel}: {'.'.join(key_path)} = {value!r}")
        print(
            "\nEach of these will fail the FIRST time a live playbook actually tries to use "
            "it (a New-ADUser/Set-Password-style failure, or a silent no-op like Rudder's "
            "UNSET API token) -- set a real value before running anything that consumes it."
        )
        return 1

    print("No unfilled placeholder values found in any plain-text vault.yml.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
