#!/usr/bin/env python3
"""
check_ssh_keys.py -- part of at_have_ryggen_fri.

Robert's 5-point spec, 2026-07-12 (triggered by the ansible-id_rsa private
key going missing on EXAANSCLD001 mid real-node test -- see
ansible/tasks/ssh_key_preflight.yml's own header for the incident, and
this repo's memory for the full spec). Point 1: the harness only ever
checked that a *public* key exists somewhere (repo file presence) -- it
needs to explicitly check for the *private* key too, and tell the operator
where to put it if missing.

Two tiers, same "independent source of truth" philosophy as the rest of
this harness (see README.md's Methodology section):

  Tier 1 (clone-safe, always runs, real failures are hard failures):
    bootstrap/web/ansible_sshkey.pub is the one committed, servable copy of
    the estate's public key (served over HTTP for first-boot.sh/the PVE
    installer to fetch). VRK-/FRD-answer.toml AND VRK-/FRD-degraded.toml's
    root-ssh-keys arrays (4 files total -- found while updating the real
    key 2026-07-12 that the original version of this check only covered
    the two non-degraded files, missing the degraded pair entirely) carry
    their own copies of the same key material, with an explicit "keep both
    in sync if it's ever rotated" comment already in every file -- this
    checks that promise actually holds, the same way check_facts.py checks
    a registered fact still holds everywhere it's asserted.

  Tier 2 (host-local, best-effort, informational unless --strict):
    Whether the *private* half ansible.cfg's private_key_file actually
    points at exists on disk. This only means anything on the real Ansible
    control node -- a bare clone genuinely won't have it, matching the
    existing drop-in-binary precedent (check_references.py / check 3) of
    "expected on a fresh clone, but --strict fails on it because you said
    you're about to deploy." Reads the configured path via `ansible-config
    dump` rather than hardcoding ansible.cfg's private_key_file a second
    time here -- if that value ever changes, this check follows it
    automatically. If the key is missing, scans ~/.ssh/ for a plausible
    candidate (any keypair whose .pub comment contains "exa", case-
    insensitive) and reports it, per Robert's point 1/2 -- with the
    explicit caveat that a genuine day-0 build should generate a fresh
    pair rather than hunt for an old one.

Exit code: 0 unless a Tier 1 (repo-data) check fails. Tier 2 issues are
printed and counted but never fail the run by themselves -- run.sh's
--strict flag escalates that count the same way it already does for
check_references.py's drop-in assets.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ANSIBLE_DIR = REPO_ROOT / "ansible"
PUB_KEY_FILE = REPO_ROOT / "bootstrap/web/ansible_sshkey.pub"
ANSWER_TOMLS = [
    "bootstrap/web/proxmox/VRK-answer.toml",
    "bootstrap/web/proxmox/FRD-answer.toml",
    "bootstrap/web/proxmox/VRK-degraded.toml",
    "bootstrap/web/proxmox/FRD-degraded.toml",
]


def check_pubkey_consistency():
    """Tier 1: bootstrap/web/ansible_sshkey.pub vs the two answer.toml copies."""
    failures = []

    if not PUB_KEY_FILE.exists():
        failures.append(f"{PUB_KEY_FILE.relative_to(REPO_ROOT)} does not exist -- "
                         f"this is the one committed, servable copy of the estate's "
                         f"public key (fetched by first-boot.sh/the PVE installer).")
        return failures

    pub_key = PUB_KEY_FILE.read_text(encoding="utf-8").strip()
    if not pub_key:
        failures.append(f"{PUB_KEY_FILE.relative_to(REPO_ROOT)} exists but is empty.")
        return failures

    for rel_path in ANSWER_TOMLS:
        path = REPO_ROOT / rel_path
        if not path.exists():
            failures.append(f"{rel_path} does not exist.")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if pub_key not in text:
            failures.append(
                f"{rel_path}: root-ssh-keys does not contain the same key material as "
                f"{PUB_KEY_FILE.relative_to(REPO_ROOT)} -- both files' own comments say "
                f"to keep these in sync if the key is ever rotated."
            )

    return failures


def resolve_configured_private_key():
    """Reads ansible.cfg's private_key_file via `ansible-config dump` -- the
    real, resolved value (defaults/env/ansible.cfg all considered), not a
    second hardcoded copy of the ini setting."""
    try:
        out = subprocess.run(
            ["ansible-config", "dump"],
            cwd=ANSIBLE_DIR,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"could not run ansible-config dump: {exc}"

    m = re.search(r"^DEFAULT_PRIVATE_KEY_FILE\([^)]*\)\s*=\s*(.+)$", out, re.MULTILINE)
    if not m or m.group(1).strip() in ("None", ""):
        return None, "ansible.cfg has no private_key_file configured"
    return m.group(1).strip(), None


def scan_ssh_dir_for_candidates():
    """Robert's point 1/2: if the configured key is missing, look in ~/.ssh/
    for any keypair whose .pub comment looks like it belongs to this estate
    (contains 'exa', case-insensitive), and report it as a candidate --
    caveat that a genuine day-0 build should generate fresh, not hunt."""
    ssh_dir = Path.home() / ".ssh"
    if not ssh_dir.is_dir():
        return []

    candidates = []
    for pub in sorted(ssh_dir.glob("*.pub")):
        try:
            content = pub.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if "exa" in content.lower():
            priv = pub.with_suffix("")
            candidates.append((str(pub), str(priv), priv.exists()))
    return candidates


def check_local_private_key():
    """Tier 2: host-local, informational. Returns (issues, info_lines)."""
    issues = []
    info = []

    key_path_str, err = resolve_configured_private_key()
    if err:
        issues.append(err)
        return issues, info

    key_path = Path(key_path_str)
    if key_path.exists():
        info.append(f"Configured private key found: {key_path}")
        pub_path = key_path.with_suffix(key_path.suffix + ".pub") if key_path.suffix else Path(str(key_path) + ".pub")
        if pub_path.exists() and PUB_KEY_FILE.exists():
            local_pub = pub_path.read_text(encoding="utf-8", errors="replace").strip()
            repo_pub = PUB_KEY_FILE.read_text(encoding="utf-8").strip()
            if repo_pub not in local_pub and local_pub not in repo_pub:
                issues.append(
                    f"{pub_path} exists but its content doesn't match "
                    f"{PUB_KEY_FILE.relative_to(REPO_ROOT)} -- the control node's local "
                    f"keypair has drifted from what's served/committed."
                )
        return issues, info

    issues.append(
        f"Configured private key ({key_path}) not found on this host. "
        f"Expected on a fresh clone/laptop -- but a showstopper on the real Ansible "
        f"control node (see ansible/tasks/ssh_key_preflight.yml)."
    )

    candidates = scan_ssh_dir_for_candidates()
    if candidates:
        info.append(f"Found {len(candidates)} plausible candidate keypair(s) in ~/.ssh/ "
                     f"(comment contains 'exa'):")
        for pub, priv, priv_exists in candidates:
            info.append(f"    {pub} (private half {'FOUND' if priv_exists else 'NOT FOUND'} at {priv})")
        info.append(
            "  If one of these is the estate's real key: never move/rename the private "
            "half into the repo. Point the public half at "
            f"{PUB_KEY_FILE.relative_to(REPO_ROOT)}, ansible/configs/ansible-id_rsa.pub, "
            "and VRK-answer.toml/FRD-answer.toml's root-ssh-keys if it's ever rotated."
        )
    else:
        info.append(
            "No plausible candidate found in ~/.ssh/. For a genuine day-0 control-node "
            "build, generate a fresh pair (matches bootstrap/web/provision/ansibleme.sh's "
            "own ssh-keygen invocation) rather than hunting for one that may be gone for good."
        )

    return issues, info


def main():
    print("-- Tier 1: bootstrap/web/ansible_sshkey.pub vs answer.toml root-ssh-keys --")
    pubkey_failures = check_pubkey_consistency()
    if pubkey_failures:
        print(f"{len(pubkey_failures)} inconsistenc(y/ies):")
        for f in pubkey_failures:
            print(f"  {f}")
    else:
        print(f"Consistent -- ansible_sshkey.pub matches all {len(ANSWER_TOMLS)} answer.toml files.")

    print()
    print("-- Tier 2: local private key (host-local, informational) --")
    local_issues, local_info = check_local_private_key()
    for line in local_info:
        print(f"  {line}")
    if local_issues:
        print(f"{len(local_issues)} local-only issue(s) (informational; --strict fails on this):")
        for issue in local_issues:
            print(f"  {issue}")

    if pubkey_failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
