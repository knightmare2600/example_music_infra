#!/usr/bin/env python3
"""
check_keepass_freshness.py -- part of at_have_ryggen_fri.

Robert, 2026-07-14, after finding two of the original TP-Link entries had a
stale/wrong password recorded and asking for the same "did the source and the
generated/live thing actually agree" pattern check 6/14 already apply to
Ansible inventory and network diagrams: "It also suggests you likely need to
plumb that into the harness." This is that check, for the one remaining
generated artefact those two don't cover -- the live KeePassXC vault.

Two tiers, same split as check_ssh_keys.py (see that file's own header for
the rationale) -- the vault itself is a local, gitignored .kdbx that a bare
clone will never have, so only the JSON side can be a hard, always-on check.

  Tier 1 (clone-safe, always runs, real failures are hard failures):
    benarbejde/extracted_credentials.json -- the JSON is well-formed, every
    entry has the required fields, every credential value matches the
    "username / password" convention every consumer (this file,
    push_credentials_to_keepass.py, the KeePassXC Automation doc) assumes,
    and every entry's role is one push_credentials_to_keepass.py's
    GROUP_FOR_ROLE actually knows how to place -- an unmapped role would
    otherwise fail silently (skipped, not erred) when the push script runs.

  Tier 2 (host-local, best-effort, informational unless --strict):
    If this host has both the live vault (~/KeePassXC/ExampleMusic.kdbx)
    and the automation master-password file
    (benarbejde/.keepassxc_master_password) available, runs
    push_credentials_to_keepass.py --dry-run and fails informationally if it
    reports anything it "would add" -- meaning extracted_credentials.json has
    moved ahead of the live vault (a new/edited entry was never actually
    pushed). Neither file is expected to exist on a bare clone or CI runner,
    matching check_ssh_keys.py's Tier 2 precedent exactly -- this tier is
    silently skipped (not failed) when they're absent.

  Tier 2b, added 2026-10-01 -- master-password file hygiene (host-local,
  informational, runs whenever the file exists regardless of whether the live
  vault does): Robert described a real vault lockout -- a master password "off
  by one character, maybe an LF/CR issue," recovered only by luck, finding an
  old working copy, never logged anywhere. Checks the file's own raw bytes for
  the shapes that actually cause this: an embedded \r (CRLF corruption), more
  than one line, or non-printable junk -- cheap, file-only, no live vault
  needed. Also sharpens the existing Tier 2 dry-run failure path: a wrong
  master password makes keepassxc-cli fail with a specific, recognisable
  "Invalid credentials" message -- previously dumped as a generic "unexpected
  output," now called out explicitly so this exact incident is unmistakable
  next time instead of a confusing dead end.

  Tier 2c, added 2026-10-01 -- live value verification (host-local,
  informational, same preconditions as Tier 2): push_credentials_to_keepass.py's
  own "already present" check only confirms an entry EXISTS at a path --
  never that its stored password is actually correct (confirmed directly:
  dedup is by `keepassxc-cli ls -R` path/hostname presence only, no `show`-
  and-compare step anywhere in that script). For every entry Tier 2 already
  confirms is present, does a read-only `keepassxc-cli show -s -a Password`
  and compares the live vault's actual stored value against
  extracted_credentials.json's own recorded value -- closes the real "was it
  ever actually added AND correct" gap this whole mechanism used to have.

  Tier 2d, added 2026-10-01 -- can the 'ansible' user actually read the
  master-password file (host-local, informational, runs whenever the file
  exists)? Scoping Phase F (opt-in, triple-checked DSRM password generation --
  see ansible/playbooks/windows_dc/playbooks/00-dc-preflight.yml) surfaced a
  real prerequisite: that feature needs Ansible, which runs as the 'ansible'
  user on the real control node, never root, to read this file for a live
  KeePass check. Robert: "on EXAANSCLD001 it is readable I think but add
  something to the harness to flag it" -- this is that flag, checked for
  real rather than assumed. Silently skipped (not failed) when no 'ansible'
  system user exists on this host at all (expected on a developer
  workstation, not the real control node).

Exit code: 0 unless a Tier 1 (JSON-side) check fails. Tier 2/2b/2c/2d drift is
printed and counted but never fails the run by itself -- run.sh's --strict
flag escalates it the same way it already does for check_ssh_keys.py.
"""
import grp
import json
import os
import pwd
import re
import stat
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE_DIR = REPO_ROOT / "benarbejde"
CREDENTIALS_JSON = BENARBEJDE_DIR / "extracted_credentials.json"
PUSH_SCRIPT = BENARBEJDE_DIR / "push_credentials_to_keepass.py"
MASTER_PASSWORD_FILE = BENARBEJDE_DIR / ".keepassxc_master_password"
DEFAULT_DB = Path.home() / "KeePassXC" / "ExampleMusic.kdbx"

sys.path.insert(0, str(BENARBEJDE_DIR))
import push_credentials_to_keepass as pck  # noqa: E402 -- reuse GROUP_FOR_ROLE, not a second copy

REQUIRED_FIELDS = ("hostname", "site", "role", "credential")
# Kept in sync by hand with push_credentials_to_keepass.py's GROUP_FOR_ROLE --
# both files agree this is a known, small, deliberately-curated set.
KNOWN_ROLES = {"RAC", "ILO", "SWI", "RTR", "FWL", "SBC", "PHN", "RMM"}


def check_credentials_json():
    """Tier 1: extracted_credentials.json is well-formed and internally consistent.
    Returns (failures, entries) -- entries is None if the file couldn't even be loaded
    as a JSON array, otherwise the parsed list (2026-10-01: also returned now, not just
    failures, so Tier 2c can reuse this one load instead of a second, separate read)."""
    failures = []

    if not CREDENTIALS_JSON.exists():
        return [f"{CREDENTIALS_JSON.relative_to(REPO_ROOT)} does not exist."], None

    try:
        entries = json.loads(CREDENTIALS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{CREDENTIALS_JSON.relative_to(REPO_ROOT)} is not valid JSON: {exc}"], None

    if not isinstance(entries, list):
        return [f"{CREDENTIALS_JSON.relative_to(REPO_ROOT)} must be a JSON array at the top level."], None

    seen = set()
    for i, entry in enumerate(entries):
        label = entry.get("hostname", f"entry #{i}") if isinstance(entry, dict) else f"entry #{i}"

        if not isinstance(entry, dict):
            failures.append(f"{label}: not a JSON object")
            continue

        missing = [f for f in REQUIRED_FIELDS if f not in entry]
        if missing:
            failures.append(f"{label}: missing required field(s): {', '.join(missing)}")
            continue

        if entry["role"] not in KNOWN_ROLES:
            failures.append(
                f"{label}: role {entry['role']!r} is not in KNOWN_ROLES ({sorted(KNOWN_ROLES)}) -- "
                f"push_credentials_to_keepass.py's GROUP_FOR_ROLE won't know where to file it and "
                f"will silently skip it as unmapped."
            )

        if not re.match(r"^.+ / .+$", entry["credential"]):
            failures.append(
                f"{label}: credential {entry['credential']!r} doesn't match the "
                f"'username / password' convention every consumer of this file assumes."
            )

        key = (entry["hostname"], entry["role"])
        if key in seen:
            failures.append(f"{label}: duplicate (hostname, role) pair {key} -- would collide on push.")
        seen.add(key)

    return failures, entries


def check_live_vault_freshness():
    """Tier 2: host-local, informational. Returns (issues, info_lines)."""
    issues = []
    info = []

    if not DEFAULT_DB.exists():
        info.append(f"{DEFAULT_DB} not found on this host -- Tier 2 skipped (expected on a bare clone/CI runner).")
        return issues, info

    if not MASTER_PASSWORD_FILE.exists():
        info.append(
            f"{MASTER_PASSWORD_FILE.relative_to(REPO_ROOT)} not found on this host -- Tier 2 skipped "
            f"(local-only, gitignored automation copy; see docs/Example Music Limited — KeePassXC CLI "
            f"Automation.md §8a.4)."
        )
        return issues, info

    try:
        result = subprocess.run(
            [sys.executable, str(PUSH_SCRIPT), "--dry-run"],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        issues.append(f"Could not run {PUSH_SCRIPT.relative_to(REPO_ROOT)} --dry-run: {exc}")
        return issues, info

    m = re.search(r"^(\d+) added,", result.stdout, re.MULTILINE)
    if not m:
        # 2026-10-01: confirmed live (a real throwaway test vault) that keepassxc-cli's own
        # wrong-password error is always this exact substring -- call it out by name instead of
        # dumping a generic "unexpected output" block, so a corrupted .keepassxc_master_password
        # (the real incident this check exists to prevent a repeat of) is unmistakable rather than
        # a confusing dead end that takes luck to diagnose.
        if "Invalid credentials were provided" in result.stderr:
            issues.append(
                f"{MASTER_PASSWORD_FILE.relative_to(REPO_ROOT)} does NOT unlock the live vault -- "
                f"keepassxc-cli rejected it outright (\"Invalid credentials were provided\"). This "
                f"is exactly the shape of a real past incident: the file's content doesn't match "
                f"the vault's actual current master password (stale, corrupted, or never updated "
                f"after a rotation). Verify by hand: "
                f"keepassxc-cli ls {DEFAULT_DB} < {MASTER_PASSWORD_FILE.relative_to(REPO_ROOT)} -- "
                f"do not wait until a live credential push or DC build depends on this working."
            )
            return issues, info
        issues.append(
            f"{PUSH_SCRIPT.relative_to(REPO_ROOT)} --dry-run produced unexpected output -- couldn't "
            f"find the summary line. Output:\n{result.stdout}\n{result.stderr}"
        )
        return issues, info

    would_add = int(m.group(1))
    if would_add > 0:
        issues.append(
            f"{would_add} credential(s) in {CREDENTIALS_JSON.relative_to(REPO_ROOT)} have not been "
            f"pushed to the live vault yet -- run push_credentials_to_keepass.py (without --dry-run) "
            f"to bring it up to date:\n" + "\n".join(f"    {line}" for line in result.stdout.splitlines() if line.startswith("DRY-RUN"))
        )
    else:
        info.append("Live vault is up to date with extracted_credentials.json (0 would be added).")

    return issues, info


def check_master_password_file_hygiene():
    """Tier 2b, 2026-10-01: cheap, file-only checks on .keepassxc_master_password's own
    raw bytes, independent of whether the live vault is even present on this host --
    catches a corrupted/malformed master-password file before anything ever tries to use
    it for a real unlock. Robert: a real vault lockout happened from a password that was
    "off by one character, maybe an LF/CR issue" -- recovered only by luck, finding an old
    working copy, never logged or checked for anywhere. Reads raw bytes, not read_text(),
    deliberately -- push_credentials_to_keepass.py's own load_master_password() already
    does read_text().strip(), which silently absorbs a trailing \\n/\\r\\n and would never
    surface this class of corruption at all; this check looks at what's actually ON DISK."""
    issues = []
    info = []

    if not MASTER_PASSWORD_FILE.exists():
        info.append(
            f"{MASTER_PASSWORD_FILE.relative_to(REPO_ROOT)} not found on this host -- Tier 2b "
            f"skipped (local-only, gitignored automation copy)."
        )
        return issues, info

    raw = MASTER_PASSWORD_FILE.read_bytes()
    rel = MASTER_PASSWORD_FILE.relative_to(REPO_ROOT)

    if b"\r" in raw:
        issues.append(
            f"{rel} contains a carriage return (\\r) -- a classic CRLF-corruption shape "
            f"(a Windows-sourced copy/paste, or an editor that saved with CRLF line endings). "
            f"The real master password almost certainly does not include this character -- "
            f"this is exactly the kind of one-character-off difference that caused a real "
            f"lockout before. Re-save this file with LF-only line endings."
        )

    text = raw.decode("utf-8", errors="replace")
    non_empty_lines = [line for line in text.splitlines() if line != ""]

    if not non_empty_lines:
        issues.append(f"{rel} is empty -- no master password recorded at all.")
        return issues, info

    if len(non_empty_lines) > 1:
        issues.append(
            f"{rel} has {len(non_empty_lines)} non-empty lines -- the master password must be "
            f"exactly one line. Extra lines suggest a paste error (e.g. pasting a multi-line "
            f"clipboard, or appending instead of overwriting on a rotation)."
        )

    value = non_empty_lines[0]
    non_printable = sorted({c for c in value if not c.isprintable()})
    if non_printable:
        issues.append(
            f"{rel}'s first line contains non-printable character(s) "
            f"({', '.join(hex(ord(c)) for c in non_printable)}) -- worth confirming this is "
            f"genuinely part of the real password and not leftover corruption."
        )

    if not issues:
        info.append(f"{rel}: single line, LF-only, no non-printable characters -- hygiene OK.")

    return issues, info


def check_master_password_file_ansible_access():
    """Tier 2d, 2026-10-01: can the 'ansible' user actually READ
    .keepassxc_master_password on this host? Scoping Phase F (opt-in DSRM password
    generation) surfaced this as a real prerequisite -- that feature needs Ansible
    (which runs as 'ansible' on the real control node, never root) to read this file
    for a live, read-only KeePass check. Robert: "on EXAANSCLD001 it is readable I
    think but add something to the harness to flag it" -- checked for real, not
    assumed. Uses os.getgrouplist() for group membership (primary AND supplementary),
    not just the file's own primary gid, since a user's real read access depends on
    all the groups they belong to, not just one."""
    issues = []
    info = []

    if not MASTER_PASSWORD_FILE.exists():
        return issues, info  # Tier 2/2b already report this skip, don't repeat it

    try:
        ansible_pw = pwd.getpwnam("ansible")
    except KeyError:
        info.append(
            "No 'ansible' system user on this host -- skipping the ansible-readability "
            "check (expected on a developer workstation, not the real control node)."
        )
        return issues, info

    rel = MASTER_PASSWORD_FILE.relative_to(REPO_ROOT)
    st = MASTER_PASSWORD_FILE.stat()
    mode = stat.S_IMODE(st.st_mode)
    owner_readable = bool(mode & stat.S_IRUSR)
    group_readable = bool(mode & stat.S_IRGRP)
    other_readable = bool(mode & stat.S_IROTH)

    owner_name = pwd.getpwuid(st.st_uid).pw_name
    file_group_name = grp.getgrgid(st.st_gid).gr_name
    ansible_groups = set(os.getgrouplist(ansible_pw.pw_name, ansible_pw.pw_gid))

    if st.st_uid == ansible_pw.pw_uid and owner_readable:
        info.append(f"{rel}: owned by 'ansible' and owner-readable -- Phase F's live KeePass check can read it.")
    elif st.st_gid in ansible_groups and group_readable:
        info.append(
            f"{rel}: group-readable, and 'ansible' belongs to group '{file_group_name}' -- "
            f"Phase F's live KeePass check can read it."
        )
    elif other_readable:
        issues.append(
            f"{rel} is readable by 'ansible' only via its world-readable bit (owner="
            f"{owner_name}, group={file_group_name}, mode={oct(mode)}) -- 'ansible' CAN read "
            f"it, but so can every other user on this host. Worth tightening to owner-or-"
            f"group-only (chgrp ansible {rel} && chmod 640 {rel}, adjusted for this host's "
            f"real group name) once Phase F is live, rather than relying on this."
        )
    else:
        issues.append(
            f"{rel} is NOT readable by 'ansible' (owner={owner_name}, group={file_group_name}, "
            f"mode={oct(mode)}) -- Phase F's live KeePass pre-check would fail outright on "
            f"this host. Fix: chgrp ansible {rel} && chmod 640 {rel} (adjusted for this host's "
            f"real ansible group name)."
        )

    return issues, info


def check_live_vault_values(credentials):
    """Tier 2c, 2026-10-01: for every extracted_credentials.json entry the live vault
    already has AN entry for, read back its actual stored password (read-only --
    `keepassxc-cli show -s -a Password`, never add/edit) and compare it against the
    JSON's own recorded value. push_credentials_to_keepass.py's own "already present"
    check (list_existing_entries(), `keepassxc-cli ls -R`) only confirms a path EXISTS --
    confirmed directly, there is no show-and-compare step anywhere in that script, so a
    stale, manually-edited, or never-correctly-pushed value would report as "already
    present" forever and nothing would ever notice. This is the direct fix for Robert's
    "unsure if passwords were ever added AND correct" -- from here on, this check would
    notice. Same preconditions/gating as check_live_vault_freshness() -- only called when
    both the live vault and the master-password file already exist."""
    issues = []
    info = []
    password = MASTER_PASSWORD_FILE.read_text().strip()
    checked = 0
    mismatches = 0

    for entry in credentials:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        group_tmpl = pck.GROUP_FOR_ROLE.get(role)
        if group_tmpl is None:
            continue  # unmapped role -- Tier 1 already reports this
        site = entry.get("site")
        hostname = entry.get("hostname")
        cred = entry.get("credential") or ""
        if not site or not hostname or " / " not in cred:
            continue  # malformed -- Tier 1 already reports this
        group = group_tmpl.format(site=site)
        path = f"{group}/{hostname}"
        _, expected_password = cred.split(" / ", 1)

        try:
            result = subprocess.run(
                ["keepassxc-cli", "show", "-s", "-a", "Password", str(DEFAULT_DB), path],
                input=(password + "\n").encode(), capture_output=True, timeout=10,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            issues.append(f"{path}: could not run keepassxc-cli show to verify -- {exc}")
            continue

        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            if "Could not find entry" in stderr:
                # Not pushed yet -- check_live_vault_freshness() (Tier 2) already reports
                # this via its own "would add" count. Not this check's job to repeat it.
                continue
            issues.append(f"{path}: could not read back to verify -- {stderr.strip()}")
            continue

        actual_password = result.stdout.decode(errors="replace").strip()
        checked += 1
        if actual_password != expected_password:
            mismatches += 1
            issues.append(
                f"{path}: the password STORED in the live vault does not match "
                f"extracted_credentials.json's own recorded value for {hostname} -- either "
                f"the vault entry was manually edited/rotated without updating the JSON, or "
                f"the wrong value was pushed in the first place. This is exactly the gap "
                f"push_credentials_to_keepass.py's existence-only check can never catch on "
                f"its own."
            )

    if checked and not mismatches:
        info.append(
            f"Verified {checked} live vault password(s) against extracted_credentials.json's "
            f"own recorded values -- all match."
        )

    return issues, info


def main():
    # 2026-10-01: run.sh's own `grep -oE '^[0-9]+ local-only issue'` extracts exactly ONE
    # count from this script's stdout for its --strict arithmetic comparison -- confirmed
    # by reading run.sh directly before adding Tier 2b/2c, rather than printing a second/
    # third "N local-only issue(s)" line and silently breaking that contract. All
    # host-local, informational findings across every 2-tier accumulate into one combined
    # list; each tier still prints its own detail, but the summary line run.sh depends on
    # is printed exactly once, at the end, with the true total.
    all_local_issues = []

    print("-- Tier 1: benarbejde/extracted_credentials.json structure --")
    json_failures, entries = check_credentials_json()
    if json_failures:
        print(f"{len(json_failures)} problem(s):")
        for f in json_failures:
            print(f"  {f}")
    else:
        print("Well-formed, all required fields present, all roles known, no duplicate (hostname, role) pairs.")

    print()
    print("-- Tier 2: live vault freshness (host-local, informational) --")
    local_issues, local_info = check_live_vault_freshness()
    for line in local_info:
        print(f"  {line}")
    for issue in local_issues:
        print(f"  {issue}")
    all_local_issues += local_issues

    print()
    print("-- Tier 2b: .keepassxc_master_password file hygiene (host-local, informational) --")
    hygiene_issues, hygiene_info = check_master_password_file_hygiene()
    for line in hygiene_info:
        print(f"  {line}")
    for issue in hygiene_issues:
        print(f"  {issue}")
    all_local_issues += hygiene_issues

    print()
    print("-- Tier 2c: live vault value verification (host-local, informational) --")
    if entries and DEFAULT_DB.exists() and MASTER_PASSWORD_FILE.exists():
        value_issues, value_info = check_live_vault_values(entries)
        for line in value_info:
            print(f"  {line}")
        for issue in value_issues:
            print(f"  {issue}")
        all_local_issues += value_issues
    else:
        print("  Skipped -- needs Tier 1's entries plus both the live vault and master-password file.")

    print()
    print("-- Tier 2d: 'ansible' user can read the master-password file (host-local, informational) --")
    access_issues, access_info = check_master_password_file_ansible_access()
    for line in access_info:
        print(f"  {line}")
    for issue in access_issues:
        print(f"  {issue}")
    all_local_issues += access_issues

    print()
    if all_local_issues:
        print(
            f"{len(all_local_issues)} local-only issue(s) across Tiers 2/2b/2c/2d "
            f"(informational; --strict fails on this)."
        )

    if json_failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
