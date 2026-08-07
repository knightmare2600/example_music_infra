#!/usr/bin/env python3

# ==================================================================================================
# Example Music KeePassXC Credential Push
#
# Authoritative source: benarbejde/extracted_credentials.json
#
# One-way flow only: benarbejde/ -> ExampleMusic.kdbx. This script is the sole writer into the
# KeePass database on the benarbejde/ side of that flow. Nothing in ansible/ MUST ever call
# keepassxc-cli add/edit/rm -- Ansible only reads (see docs/Example Music Limited — KeePassXC CLI
# Automation.md §7a). Robert's explicit instruction (2026-07-14): "I'd rather NOT have ansible
# adding anything, so the flow is from the folder with those JSON and CSVs towards the ansible
# stuff."
#
# Additive only: existing entries are never edited or overwritten by this script, even if
# extracted_credentials.json's value for that hostname has since changed. A human may have rotated
# a credential directly in KeePassXC after a device build -- this script re-running MUST NOT stomp
# on that. To update an existing entry's password, do it in KeePassXC (or via keepassxc-cli edit)
# directly, not through this script.
#
# Requires the keepassxc-cli package to already be installed (apt install keepassxc).
# ==================================================================================================
# Changelog:
#  2026-07-14  First version. Promoted from a throwaway job-tmp script used to do the initial
#              22-credential (now 31) population, into a real, idempotent, checked-in tool --
#              the original threw away dedupe state in a hardcoded DONE set, which only worked
#              for a single one-off run. This version queries the live database's existing
#              entries via `keepassxc-cli ls -R` and skips anything already present, so it is
#              safe to re-run any time extracted_credentials.json gains new rows.
#  2026-07-14  Added optional "note"/"url" fields on a credential entry, passed through to
#              keepassxc-cli add's --notes/--url. Needed for the vendor-shared credential entries
#              (one Cisco Catalyst login covering 20 switches, one FortiOS login covering 5
#              firewalls/routers, etc.) where the Notes field is the only place to record which
#              real hostnames a shared entry actually covers, plus secondary fields like a Cisco
#              enable password or a vendor cheatsheet URL that don't fit username/password alone.
#  2026-08-07  Added RMM role (Infrastructure/{site}, same template as SBC) -- Robert, live,
#              after tacticalrmm_server.yml's first full end-to-end run against EXARMMCLD001:
#              "fix the entire setup and harness so it can, in fact, add passwords to keepassxc".
#              This script already was that mechanism (non-interactive, master password from a
#              file, no getpass in the normal path) -- kpcli_wrapper.py's own interactive-only
#              design was correctly left untouched; this file is the one meant for exactly this.
#              Covers application/service-account credentials for a role-coded server (Postgres
#              roles, Django admin, MeshCentral admin) the same way SBC already covers other
#              non-network-gear infrastructure hosts -- one entry per distinct credential, not
#              one entry per hostname, since a single server can hold several.
#  2026-08-07  Renamed the default vault filename from "Example Music.kdbx" to "ExampleMusic.kdbx"
#              (default path still ~/KeePassXC/) -- Robert: a space in a filename is "playing with
#              fire" on Unix/macOS shell usage. No functional risk in THIS script specifically
#              (subprocess calls already use list-argv, not shell=True string interpolation, so the
#              space was never actually exploitable here) but a real day-to-day hazard for anyone
#              typing a raw shell command against the file by hand. This is a rename of the
#              EXPECTED filename only -- does not touch/rename any real, live .kdbx file, which
#              lives wherever Robert actually keeps it; he renames that copy himself, or overrides
#              --db to point at whatever the real file is still called.
# ==================================================================================================

import argparse
import getpass
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_DB = Path.home() / "KeePassXC" / "ExampleMusic.kdbx"
DEFAULT_CREDENTIALS_JSON = Path(__file__).parent / "extracted_credentials.json"
DEFAULT_MASTER_PASSWORD_FILE = Path(__file__).parent / ".keepassxc_master_password"

GROUP_FOR_ROLE = {
  "RAC": "Network/IPMI-BMC",
  "ILO": "Network/IPMI-BMC",
  "SWI": "Network/Switches",
  "RTR": "Network/Routers",
  "FWL": "Network/Firewalls",
  "SBC": "Infrastructure/{site}",
  "PHN": "Network/Phones",
  "RMM": "Infrastructure/{site}",
}


def load_master_password(master_password_file):
  if master_password_file.exists():
    return master_password_file.read_text().strip()
  return getpass.getpass(f"{master_password_file} not found -- enter master password manually: ")


def list_existing_entries(db, password):
  result = subprocess.run(
    ["keepassxc-cli", "ls", "-R", str(db)],
    input=(password + "\n").encode(), capture_output=True,
  )
  if result.returncode != 0:
    print("Failed to list existing entries:", result.stderr.decode().strip(), file=sys.stderr)
    sys.exit(1)
  # ls -R prints an indented tree (group names end in "/", "[empty]" marks an empty group), not
  # one full path per line -- verified against real output 2026-07-14. Reconstruct full paths from
  # indentation depth (2 spaces per level, confirmed against real output) rather than trusting a
  # flat line, and also return the bare leaf names for the cross-group-collision check below.
  paths = set()
  leaf_names = set()
  stack = []  # (depth, name) of open groups
  for line in result.stdout.decode().splitlines():
    if not line.strip():
      continue
    depth = (len(line) - len(line.lstrip(" "))) // 2
    token = line.strip()
    if token == "[empty]":
      continue
    stack = stack[:depth]
    if token.endswith("/"):
      stack.append(token.rstrip("/"))
      continue
    paths.add("/".join(stack + [token]))
    leaf_names.add(token)
  return paths, leaf_names


def mkdir(db, password, group, created_groups):
  if group in created_groups:
    return
  subprocess.run(
    ["keepassxc-cli", "mkdir", "-q", str(db), group],
    input=(password + "\n").encode(), capture_output=True,
  )
  created_groups.add(group)


def add_entry(db, password, path, username, entry_password, note, url, dry_run):
  if dry_run:
    print(f"DRY-RUN would add: {path} ({username})" + (" [+notes]" if note else ""))
    return True
  cmd = ["keepassxc-cli", "add", "-u", username]
  if note:
    cmd += ["--notes", note]
  if url:
    cmd += ["--url", url]
  cmd += ["-p", str(db), path]
  result = subprocess.run(
    cmd,
    input=(password + "\n" + entry_password + "\n").encode(), capture_output=True,
  )
  ok = result.returncode == 0
  print(f"{'OK' if ok else 'FAIL'}: {path} ({username})")
  if not ok:
    print("  ", result.stdout.decode().strip(), result.stderr.decode().strip())
  return ok


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"Path to .kdbx (default: {DEFAULT_DB})")
  parser.add_argument("--credentials-json", type=Path, default=DEFAULT_CREDENTIALS_JSON)
  parser.add_argument("--master-password-file", type=Path, default=DEFAULT_MASTER_PASSWORD_FILE)
  parser.add_argument("--dry-run", action="store_true", help="Show what would be added, touch nothing")
  args = parser.parse_args()

  if not args.db.exists():
    print(f"Database not found: {args.db}", file=sys.stderr)
    sys.exit(1)

  password = load_master_password(args.master_password_file)
  credentials = json.load(open(args.credentials_json))
  existing_paths, existing_leaf_names = list_existing_entries(args.db, password)

  created_groups = set()
  added, skipped, failed, unmapped = 0, 0, 0, 0

  for entry in credentials:
    role = entry["role"]
    group_tmpl = GROUP_FOR_ROLE.get(role)
    if group_tmpl is None:
      print(f"SKIP (no group mapping for role {role!r}): {entry['hostname']}")
      unmapped += 1
      continue
    group = group_tmpl.format(site=entry["site"])
    path = f"{group}/{entry['hostname']}"

    # SHARED-* entries deliberately reuse the same leaf name across multiple groups (one login
    # covering many real devices in different KeePass groups) -- dedupe those by exact path only.
    # Real per-device hostnames (EXA<ROLE><SITE><NNN>) are meant to be globally unique, so a match
    # anywhere in the tree counts as "already recorded", even under an unexpected group (e.g. a
    # manually-misfiled entry) -- skip rather than risk creating a second entry for the same device.
    is_shared = entry["hostname"].startswith("SHARED-")
    if is_shared:
      if path in existing_paths:
        skipped += 1
        continue
    elif entry["hostname"] in existing_leaf_names:
      skipped += 1
      continue

    cred = entry["credential"]
    if " / " not in cred:
      print(f"SKIP (unparseable credential): {entry['hostname']}")
      unmapped += 1
      continue
    username, entry_password = cred.split(" / ", 1)

    mkdir(args.db, password, group, created_groups)
    note = entry.get("note")
    url = entry.get("url")
    if add_entry(args.db, password, path, username, entry_password, note, url, args.dry_run):
      added += 1
    else:
      failed += 1

  print(f"\n{added} added, {skipped} already present (skipped), {failed} failed, {unmapped} unmapped "
        f"(of {len(credentials)} total in {args.credentials_json.name})")
  sys.exit(1 if failed else 0)


if __name__ == "__main__":
  main()
