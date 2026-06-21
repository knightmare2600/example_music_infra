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

def run_cli(cli, args, password):
  """
  Execute CLI with password via stdin.
  """
  try:
    proc = subprocess.run(
      [cli] + args,
        input=password.encode(),
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
      ], password)
    except Exception:
      run_cli(cli, [
        "add", db, path,
        "--username", username,
        "--password-prompt"
      ], password)

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
- No credentials stored on disk
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

# 9. Future Enhancements (Planned)

- JSON output mode for automation pipelines
- Ansible lookup plugin
- Proxmox credential integration
- Role-based access wrappers

------

# 10. Ownership

**Team:** Infrastructure / Automation
 **System Owner:** Example Music Limited
 **Review Cycle:** 6 months

------