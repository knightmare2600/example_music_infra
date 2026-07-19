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
    If this host has both the live vault (~/KeePassXC/Example Music.kdbx)
    and the automation master-password file
    (benarbejde/.keepassxc_master_password) available, runs
    push_credentials_to_keepass.py --dry-run and fails informationally if it
    reports anything it "would add" -- meaning extracted_credentials.json has
    moved ahead of the live vault (a new/edited entry was never actually
    pushed). Neither file is expected to exist on a bare clone or CI runner,
    matching check_ssh_keys.py's Tier 2 precedent exactly -- this tier is
    silently skipped (not failed) when they're absent.

Exit code: 0 unless a Tier 1 (JSON-side) check fails. Tier 2 drift is printed
and counted but never fails the run by itself -- run.sh's --strict flag
escalates it the same way it already does for check_ssh_keys.py.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENARBEJDE_DIR = REPO_ROOT / "benarbejde"
CREDENTIALS_JSON = BENARBEJDE_DIR / "extracted_credentials.json"
PUSH_SCRIPT = BENARBEJDE_DIR / "push_credentials_to_keepass.py"
MASTER_PASSWORD_FILE = BENARBEJDE_DIR / ".keepassxc_master_password"
DEFAULT_DB = Path.home() / "KeePassXC" / "Example Music.kdbx"

REQUIRED_FIELDS = ("hostname", "site", "role", "credential")
# Kept in sync by hand with push_credentials_to_keepass.py's GROUP_FOR_ROLE --
# both files agree this is a known, small, deliberately-curated set.
KNOWN_ROLES = {"RAC", "ILO", "SWI", "RTR", "FWL", "SBC", "PHN"}


def check_credentials_json():
    """Tier 1: extracted_credentials.json is well-formed and internally consistent."""
    failures = []

    if not CREDENTIALS_JSON.exists():
        return [f"{CREDENTIALS_JSON.relative_to(REPO_ROOT)} does not exist."]

    try:
        entries = json.loads(CREDENTIALS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{CREDENTIALS_JSON.relative_to(REPO_ROOT)} is not valid JSON: {exc}"]

    if not isinstance(entries, list):
        return [f"{CREDENTIALS_JSON.relative_to(REPO_ROOT)} must be a JSON array at the top level."]

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

    return failures


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


def main():
    print("-- Tier 1: benarbejde/extracted_credentials.json structure --")
    json_failures = check_credentials_json()
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
    if local_issues:
        print(f"{len(local_issues)} local-only issue(s) (informational; --strict fails on this):")
        for issue in local_issues:
            print(f"  {issue}")

    if json_failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
