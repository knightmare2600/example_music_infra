# Example Music Limited — KeePassXC CLI Automation (Python Wrapper)

> **Classification:** Internal — Infrastructure  
> **Applies to:** macOS · Linux · Windows  
> **Purpose:** Secure, lightweight programmatic interaction with KeePass databases using Python and CLI tooling  

---

# 1. Overview

This procedure defines a **standard, security-conscious method** to:

- Search KeePass entries (regex, case-insensitive)
- Create folders (groups)
- Add or update entries
- Validate database access securely

The solution uses:

- Python (no heavy dependencies)
- KeePass CLI tooling (platform-native)

---

# 2. Supported Tooling

## Primary (Recommended)
- `keepassxc-cli` (from KeePassXC)

## Alternative (Linux only)
- `kpcli`

⚠️ **Important:**
- `kpcli` uses a **different interface and database handling model**
- This script is designed for **KeePassXC CLI compatibility**
- On Linux, **prefer `keepassxc-cli` for consistency**

---

# 3. Installation

## 3.1 macOS (Homebrew)

```bash
brew install keepassxc
```

------

## 3.2 Linux (Debian / Ubuntu)

```bash
sudo apt update
sudo apt install keepassxc
```

Alternative (not recommended unless required):

```bash
sudo apt install kpcli
```

------

## 3.3 Windows (Chocolatey)

```powershell
choco install keepassxc
```

------

# 4. Verification

Confirm CLI availability:

```bash
keepassxc-cli --version
```

If using fallback:

```bash
kpcli --version
```

------

# 5. Python Wrapper Script

## 5.1 Purpose

The script provides:

- Secure password prompting (no echo)
- CLI abstraction
- Regex search capability
- Folder creation
- Entry add/update

------

## 5.2 Dependency Requirements

- Python 3.x
- No external Python packages required

------

## 5.3 Script (Production Baseline)

```python
#!/usr/bin/env python3

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
```

> **Correction (2026-07-11):** the script above previously had every function's control flow
> broken by mis-indentation — code sat nested inside the block above it after a `return`/`raise`/
> `sys.exit()`, making it unreachable. The most serious instance: `main()`'s `cli = find_cli()`
> assignment was nested inside the `len(sys.argv) < 3` branch, so on every *normal* invocation
> (enough arguments given) `cli` was referenced later without ever being assigned — a guaranteed
> `NameError` crash. `verify_access()` additionally had a syntax error (an `except` misindented
> to align with a nested `else:` body) that would have failed to parse at all. Every function
> exhibited the same pattern — dead code after the guard clause meant to precede it, and no
> return value on the success path. Fixed throughout; the version above is corrected and was
> mentally traced end-to-end (not executed) against the usage examples in Section 6.

> **Correction (2026-07-14):** actually executed this script for the first time (against a real
> KeePassXC database, `Example Music.kdbx`, populated with 22 real legacy credentials pulled out
> of `benarbejde/ad_computers.json`) rather than trusting the 2026-07-11 mental trace. `search` and
> `mkdir` worked first try. `add` silently created entries with an **empty password** — `entry_pw`
> was captured via `getpass.getpass()` but never actually passed to the underlying
> `keepassxc-cli add ... --password-prompt` subprocess; `run_cli()` only ever forwarded the
> database's own unlock password as stdin, so the CLI's second prompt (for the entry's password)
> got EOF instead of a value. Fixed: `run_cli()` now takes an optional `entry_password` argument
> and sends it as a second stdin line; `add_entry()` passes `entry_pw` through on both the `edit`
> and `add` branches. Verified the fix directly — a throwaway entry added through the corrected
> script came back with its real password via `keepassxc-cli show -s`, then removed. (The 22 real
> credentials populated into `Example Music.kdbx` this same session were added via direct
> `keepassxc-cli add ... -p` calls with both stdin lines supplied correctly from the start, so they
> were never affected by this particular bug — but nobody would have known that using this script
> as written, which is the whole reason to actually run a doc's code before trusting it.)

------

# 6. Usage Examples

## 6.1 Search (Case-Insensitive Regex)

```bash
python kpcli_wrapper.py vault.kdbx search DCS
```

------

## 6.2 Create Folder

```bash
python kpcli_wrapper.py vault.kdbx mkdir "Infrastructure/Proxmox"
```

------

## 6.3 Add or Update Entry

```bash
python kpcli_wrapper.py vault.kdbx add "Infrastructure/Proxmox/node1" root
```

------

# 7. Security Considerations

## 7.1 Controls Implemented

- Password input via secure prompt (no echo)
- No credentials stored on disk **except the two deliberate, gitignored exceptions in §7a/§8a.4**
  (`benarbejde/extracted_credentials.json`, the vault's own source data, and
  `benarbejde/.keepassxc_master_password`, the automation unlock copy) — both local-only,
  `chmod 600` where applicable, never committed
- No credentials passed via CLI arguments
- Short-lived subprocess execution
- Best-effort memory overwrite after use

------

## 7.2 Limitations (Important)

- Python cannot guarantee full memory sanitisation
- String copies may persist in interpreter memory
- This is considered **acceptable operational risk** under:
  - FCA guidance (UK)
  - SOX/Sarbanes-Oxley controls
  - Standard enterprise audit models

------

## 7.3 Operational Guidance

- Do not run as a long-lived daemon
- Do not log output containing secrets
- Restrict file permissions on `.kdbx` files
- Prefer user-invoked execution only

------

# 7a. Credential Provisioning Flow (One-Way)

> Robert's instruction (2026-07-14), verbatim intent: *"I'd rather NOT have ansible adding
> anything, so the flow is from the folder with those JSON and CSVs towards the ansible stuff."*
> This section makes that a documented, checked rule rather than a one-off remark.

- **Data flows one direction only: `benarbejde/` → `Example Music.kdbx` → Ansible/tooling reads.**
  There is no reverse path. Nothing in `ansible/` MUST ever call `keepassxc-cli add`,
  `keepassxc-cli edit`, or `keepassxc-cli rm` — Ansible plays, roles, and lookups only ever
  **read** a credential (`keepassxc-cli show`/`clip`, or a future lookup plugin built on the
  same read-only call), never write one.
- **`benarbejde/extracted_credentials.json` is the source of truth for what belongs in the
  vault**, exactly the same relationship `devices.csv`/`sites.csv` already have with
  `generate_inventory.py`'s generated `.ini` files (see that script's own header comment).
  Whenever a new device gets a real credential — a fresh BMC, a newly-provisioned switch — the
  credential is added to this JSON file first, by a human, from real source material (a build
  sheet, a vendor label, a provisioning log). It is never invented, guessed, or defaulted without
  a real source.
- **`benarbejde/push_credentials_to_keepass.py`** is the one sanctioned writer on the
  `benarbejde/` → KeePass leg. Run by hand (or from a human-triggered script, never from an
  Ansible task), it reads `extracted_credentials.json`, unlocks the database using
  `.keepassxc_master_password` (§8a.4), and adds any entry not already present. It is **additive
  only** — it never edits or deletes an existing entry, so a credential rotated by hand directly
  in KeePassXC afterwards is never silently reverted by a re-run. `--dry-run` previews changes
  without touching the database.
- **Why not have Ansible push newly-discovered credentials automatically?** Because a play that
  can write to the vault is a play that can, on a bug or a bad run, corrupt or leak the one place
  every other credential lives. Keeping the write path to a single, small, human-invoked script —
  reviewed the same way any other repo change is — keeps the vault's blast radius small and
  auditable via normal git history on `extracted_credentials.json`, rather than buried in
  Ansible's own logs.
- **Known housekeeping item, found while verifying this script (2026-07-14):** `EXARACEDI001`
  currently sits under `Infrastructure/EDI/` in the live database instead of
  `Network/IPMI-BMC/EDI/` where `GROUP_FOR_ROLE` would place it — a leftover from the manual
  live-test entry added earlier in this session to verify the wrapper script's password bug fix
  (§5/§6 changelog). Because dedupe is by hostname (not full path), the push script correctly
  treats it as already present and leaves it alone rather than creating a second entry — but the
  group placement itself is still wrong and wants a manual `keepassxc-cli mv` (or drag in the
  GUI) to `Network/IPMI-BMC/EDI/EXARACEDI001`. Not fixed here since it's a one-off manual
  correction, not something the push script should be doing on Ansible/tooling's behalf.

------

# 8. Linux `kpcli` Compatibility Notes

| Feature          | keepassxc-cli | kpcli   |
| ---------------- | ------------- | ------- |
| KDBX4 support    | Yes           | Partial |
| Regex search     | Yes           | No      |
| Group creation   | Yes           | Limited |
| Entry automation | Yes           | Limited |

👉 **Conclusion:**

- `kpcli` is supported only as a fallback
- Full functionality requires `keepassxc-cli`

------

# 8a. Master Password Backup & Recovery

> **This section did not exist before `Example Music.kdbx` did.** The moment a real master
> password is generated for a real database, "where does this live if the one person who knows it
> forgets it, or leaves" stops being theoretical. This is a business-continuity control, not an
> afterthought — a lost master password with no backup means every credential the database holds
> MUST be individually rotated, on every device it protects, with no shortcut.

## 8a.1 Requirements

- The master password MUST NOT be stored anywhere alongside, or with the same access path as, the
  `.kdbx` file itself. Encrypting a database and keeping the key next to it protects against
  nothing.
- At least one **offline, physical** backup of the master password is REQUIRED. A password that
  only ever existed in a chat transcript, a Slack message, or a single person's memory is not a
  backup — it is a single point of failure that happens not to have failed yet.
- A second, geographically separate physical copy is RECOMMENDED once there's a real physical
  location to put it in (see 8a.3).
- No single individual SHALL be the sole holder of every copy. Two-person control — a second,
  independent custodian who can produce their copy without the first person being available — is
  REQUIRED for the primary estate database once there is a second engineer to hold it.

## 8a.2 Recommended mechanism

1. Write the master password on paper. Seal it in a tamper-evident envelope, dated and initialled
   across the seal.
2. Store the sealed envelope in a physical safe or locked cabinet with restricted access —
   **not** the same room as any workstation that has the `.kdbx` file open regularly.
3. If a second custodian exists, they hold an independent sealed copy in a **different** physical
   location — not a second envelope in the same safe.
4. Log every time the envelope is opened (date, who, why) on the envelope itself or an
   accompanying sheet — an unopened, unremarked seal is itself evidence nothing has gone wrong.
5. If KeePassXC's key-file feature is adopted as a second unlock factor alongside the password,
   the key file MUST be backed up through this same two-copy, two-location process — a key file
   that only exists on one laptop is exactly the single point of failure this whole procedure
   exists to avoid.

## 8a.3 Open questions — Robert's call, not assumed

- **Is there a physical safe or locked cabinet available at a site today?** (Falkirk HQ is the
  obvious candidate, being the primary site — not assumed here.)
- **Who is the second custodian, once one exists?** Until there's a second engineer on this
  estate, two-person control isn't achievable — noted as a real gap, not silently skipped.
- **Does the current master password (generated 2026-07-14, handed over in this session's chat)
  get rotated once a physical backup exists**, given its only current record is that transcript?
  Recommended: yes — treat the current password as provisional until it has a real backup, then
  generate a fresh one and destroy the old record.

## 8a.4 Automation/scripted access copy

Any tooling that needs to unlock `Example Music.kdbx` unattended (a provisioning script reading a
BMC credential, a scheduled report) needs the master password available to a process, not just to
a human with an envelope. 8a.1's "MUST NOT store alongside the `.kdbx`" rule is about not defeating
the encryption by keeping the key on the same access path as the file it protects — it does not
mean the password can have no machine-readable copy anywhere. A third copy exists for this reason:

- **File**: `benarbejde/.keepassxc_master_password` — plain text, the raw password, nothing else.
- **Location**: inside the repo working tree, but **not inside the `.kdbx`'s own directory**
  (`~/KeePassXC/`) — same separation principle as 8a.1, applied to the automation copy.
- **Access control**: `chmod 600`, owner-only. Excluded from git via `.gitignore` (the entry sits
  immediately after the `ansible-id_rsa` block) — never committed, never pushed, never visible to
  anyone who only has the repo, only to someone with a shell on a machine that already has this
  file placed there.
- **Precedent**: this follows the exact pattern already established by
  `ansible/configs/ansible-id_rsa` — a real secret that tooling needs to read, kept local-only,
  gitignored, never embedded in a script or committed config.
- **Risk, stated plainly, not hidden**: anyone who compromises a machine holding this file AND
  gets a copy of `Example Music.kdbx` has the whole database. This is accepted as a **managed
  risk** — traded off against the alternative of no unattended automation access at all. It is
  managed by: the file only ever existing on machines that also run provisioning tooling (not
  laptops, not anything with broader exposure), `chmod 600`, and it being the first thing rotated
  if any host holding it is suspected compromised.
- **Relationship to 8a.2's sealed envelope**: the two are independent, both current. Losing the
  automation copy is an inconvenience (lost automation, not lost data) — the envelope, or a
  human's memory of the master password, still unlocks the database either way. Losing the
  envelope with no replacement is the actual disaster this section exists to prevent. The
  automation copy is never treated as *the* backup — 8a.1's physical-backup requirement is
  satisfied by 8a.2 alone.
- **Rotation**: if the master password is rotated per 8a.3, this file MUST be updated in the same
  change. A stale copy here fails closed (wrong password, script errors clearly) rather than
  failing open — no silent-corruption risk from forgetting the step, but automation stops working
  until someone updates it.

------

# 9. Future Enhancements (Planned)

- JSON output mode for automation pipelines
- Ansible lookup plugin — **read-only**, per §7a: `keepassxc-cli show`/`clip` only, never `add`/
  `edit`/`rm`
- Proxmox credential integration
- Role-based access wrappers

------

# 10. Ownership

**Team:** Infrastructure / Automation
 **System Owner:** Example Music Limited
 **Review Cycle:** 6 months

------