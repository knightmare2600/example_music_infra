#!/usr/bin/env python3
# =============================================================================
# benarbejde/kpcli_wrapper.py
# Example Music Limited — KeePassXC CLI Automation (Python Wrapper)
# =============================================================================
# Materialised 2026-07-22 from "docs/Example Music Limited — KeePassXC CLI
# Automation.md" §5.3's "Production Baseline" code block -- documented since
# 2026-07-11 (indentation/control-flow fix) and corrected again 2026-07-14
# (add_entry's entry password was captured via getpass but never actually
# forwarded to keepassxc-cli's --password-prompt stdin, so `add` silently
# created entries with an EMPTY password -- fixed and verified live against
# a real database, see that doc's own changelog for both corrections). This
# file is that same, already-corrected script, finally given a real path in
# the repo -- previously it only existed as a code block inside the doc.
#
# Human-invoked only, same posture as benarbejde/push_credentials_to_keepass.py
# (see docs/.../KeePassXC CLI Automation.md §7a) -- prompts interactively for
# both the database unlock password and any entry password via getpass, never
# accepts either via CLI arguments or a non-interactive flag. Never call this
# from an Ansible task -- §7a's one-way credential flow (benarbejde/ ->
# ExampleMusic.kdbx -> Ansible/tooling reads, never the reverse) explicitly
# permits "a human-triggered script, never an Ansible task" for writes; this
# is that script, for anything that doesn't fit push_credentials_to_keepass.py's
# devices.csv-shaped extracted_credentials.json flow (e.g. a one-off local
# service account, like playbooks/salt/playbooks/20-saltgui.yml's saltgui
# login).
#
# Usage:
#   python3 benarbejde/kpcli_wrapper.py <db.kdbx> search <regex>
#   python3 benarbejde/kpcli_wrapper.py <db.kdbx> mkdir <group/path>
#   python3 benarbejde/kpcli_wrapper.py <db.kdbx> add <entry/path> <username>
# =============================================================================
# Changelog:
#   2026-07-22  Materialised as a real file (was doc-embedded code only).
#   2026-07-14  Fixed add_entry's entry password never reaching keepassxc-cli's
#               --password-prompt stdin (silently created empty-password
#               entries). Verified live.
#   2026-07-11  Fixed pervasive mis-indentation across every function --
#               dead code after guard clauses, cli assigned inside the wrong
#               branch in main(), a syntax error in verify_access().
# =============================================================================

import subprocess
import getpass
import shutil
import sys
import re

def find_cli():
  """
  Detect available KeePass CLI tool.
  Preference order:
  1. keepassxc-cli
  2. kpcli (Linux fallback)
  """
  if shutil.which("keepassxc-cli"):
    return "keepassxc-cli"
  if shutil.which("kpcli"):
    return "kpcli"
  return None

def run_cli(cli, args, password, entry_password=None):
  """
  Execute CLI with password via stdin. entry_password, if given, is sent as a
  second stdin line -- needed for any command using --password-prompt, which
  makes keepassxc-cli itself prompt for a second, per-entry password after
  the database unlock password.
  """
  stdin_payload = password
  if entry_password is not None:
    stdin_payload += "\n" + entry_password
  try:
    proc = subprocess.run(
      [cli] + args,
      input=stdin_payload.encode(),
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      timeout=15
    )
    if proc.returncode != 0:
      raise RuntimeError(proc.stderr.decode())
    return proc.stdout.decode()
  finally:
    password = "\0" * len(password)

def prompt_password():
  return getpass.getpass("Enter KeePass password: ")

def verify_access(cli, db, password):
  try:
    if cli == "keepassxc-cli":
      run_cli(cli, ["ls", db], password)
    else:
      # kpcli fallback (limited validation)
      run_cli(cli, ["--kdb", db, "--command", "ls"], password)
    return True
  except Exception:
    return False

def search(cli, db, password, pattern):
  if cli != "keepassxc-cli":
    raise NotImplementedError("Regex search requires keepassxc-cli")
  output = run_cli(cli, ["ls", "-R", db], password)
  regex = re.compile(pattern, re.IGNORECASE)
  return [line for line in output.splitlines() if regex.search(line)]

def create_group(cli, db, password, group):
  if cli != "keepassxc-cli":
    raise NotImplementedError("Group creation requires keepassxc-cli")
  run_cli(cli, ["mkdir", db, group], password)

def add_entry(cli, db, password, path, username):
  if cli != "keepassxc-cli":
    raise NotImplementedError("Entry management requires keepassxc-cli")
  entry_pw = getpass.getpass("Entry password: ")
  try:
    run_cli(cli, ["show", db, path], password)
    run_cli(cli, [
      "edit", db, path,
      "--username", username,
      "--password-prompt"
    ], password, entry_pw)
  except Exception:
    run_cli(cli, [
      "add", db, path,
      "--username", username,
      "--password-prompt"
    ], password, entry_pw)
  finally:
    entry_pw = "\0" * len(entry_pw)

def main():
  if len(sys.argv) < 3:
    print("Usage: script.py <db.kdbx> <command> [args]")
    sys.exit(1)

  cli = find_cli()
  if not cli:
    print("❌ No KeePass CLI tool found.")
    print("")
    print("Install one of the following:")
    print("  macOS:   brew install keepassxc")
    print("  Linux:   sudo apt install keepassxc")
    print("  Windows: choco install keepassxc")
    sys.exit(2)

  db = sys.argv[1]
  command = sys.argv[2]
  password = prompt_password()

  if not verify_access(cli, db, password):
    print("❌ Invalid password or database")
    sys.exit(3)

  try:
    if command == "search":
      results = search(cli, db, password, sys.argv[3])
      print("\n".join(results))
    elif command == "mkdir":
      create_group(cli, db, password, sys.argv[3])
      print("✅ Group created")
    elif command == "add":
      add_entry(cli, db, password, sys.argv[3], sys.argv[4])
      print("✅ Entry added/updated")
    else:
      print("Unknown command")
  finally:
    password = "\0" * len(password)

if __name__ == "__main__":
  main()
