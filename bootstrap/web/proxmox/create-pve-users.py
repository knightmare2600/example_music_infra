#!/usr/bin/env python3
"""
create-pve-users.py — Proxmox VE User Provisioning Script
Example Music Limited — Internal Infrastructure

Creates users on a Proxmox VE node following the EXA infrastructure convention.
For each user, the script:
  - Creates a PVE realm account (/access/users) via the proxmoxer API
  - Creates a matching Linux shell account (useradd -m -s /usr/bin/zsh) via SSH
  - Optionally installs an SSH public key into ~/.ssh/authorized_keys
  - Sets PVE group/role membership (default: PVEAuditor)
  - Offers API token creation or password auth for the PVE account

Changelog:
  2026-06-16  Initial script — PVE + Linux user creation, SSH key install,
              group/role selection (default PVEAuditor), token or password auth,
              token displayed once in red with clear warning, bulk mode,
              dry-run, logging. Connection/node/site patterns preserved from
              create-vm.py.
  2026-06-17  Fix: ISO upload/download in PVE UI requires Datastore.AllocateTemplate
              at the storage path level — root-path role assignment alone does
              not grant this. Added get_storage_pools(), STORAGE_ROLES dict,
              and select_storage_acls() which queries the node for available
              storage pools, prompts for which to grant access to (all or
              subset), and offers PVEDatastoreAdmin / PVEDatastoreUser /
              PVETemplateUser. ACLs applied via PUT /access/acl at
              /storage/<name> after the root-path role. Shown in summary and
              completion banner. Dry-run aware throughout.
  2026-06-17  Fix: script SSH'd back to the PVE node even when already running
              on it, causing a pointless loop-back connection. Added _is_local()
              which resolves the target host and compares against all local
              interface IPs (via socket + hostname -I). If local, _ssh_connect
              returns the sentinel "local" and _ssh_run delegates to _local_run
              (subprocess) instead of paramiko. ssh.close() guarded against the
              sentinel. Zero behaviour change when running remotely.

Usage:
  python3 create-pve-users.py [options]

Options:
  -h, --help              Show this help message and exit
  --host HOST             Proxmox host (e.g. 192.168.139.5 or pve.example.com)
  --port PORT             Proxmox API port (default: 8006)
  --user USER             Proxmox username for auth (e.g. root@pam)
  --token-name NAME       API token name for auth
  --token-value VALUE     API token value for auth
  --password PASSWORD     Password for auth (if no token specified)
  --node NODE             Proxmox node name (e.g. EXAPVEFAL001)
  --realm REALM           PVE realm for new users: pam or pve (default: pam)
  --dry-run               Show what would be created without making changes
  --bulk                  Loop user creation — prompts for another after each user
  --log FILE              Log file path (default: ~/pve-user-create.log)

Examples:
  # Fully interactive
  python3 create-pve-users.py

  # API token auth, dry run
  python3 create-pve-users.py --host 192.168.139.5 --user root@pam \\
    --token-name provisioning --token-value xxxx-xxxx --dry-run

  # Bulk mode — create multiple users in one session
  python3 create-pve-users.py --host 192.168.139.5 --bulk
"""

import argparse
import csv as _csv
import datetime
import getpass
import os
import re
import secrets
import string
import sys

try:
  from proxmoxer import ProxmoxAPI
except ImportError:
  print("ERROR: proxmoxer not installed.")
  print("  On Proxmox node : apt install python3-proxmoxer python3-requests")
  print("  On workstation  : pip3 install proxmoxer requests")
  sys.exit(1)

try:
  import paramiko
  _PARAMIKO = True
except ImportError:
  _PARAMIKO = False

# =============================================================================
# SITE DATA  (shared pattern with create-vm.py)
# =============================================================================

def _load_sites(csv_path=None):
  """Load site data from sites.csv. Searches same locations as create-vm.py."""
  if csv_path is None:
    env_path = os.environ.get("SITES_CSV")
    if env_path and os.path.isfile(env_path):
      csv_path = env_path
    else:
      script_dir = os.path.dirname(os.path.abspath(__file__))
      for p in [
        os.path.join(script_dir, "sites.csv"),
        os.path.join(os.getcwd(), "sites.csv"),
        "/etc/example-music/sites.csv",
      ]:
        if os.path.isfile(p):
          csv_path = p
          break

  if not csv_path or not os.path.isfile(csv_path):
    print("ERROR: sites.csv not found.")
    print("  Searched: $SITES_CSV, script dir, cwd, /etc/example-music/sites.csv")
    sys.exit(1)

  sites = {}
  with open(csv_path, newline="", encoding="utf-8") as f:
    for row in _csv.DictReader(f):
      code   = row["Site"].strip().upper()
      subnet = row["Subnet"].strip()
      octet  = int(subnet.split(".")[2]) if subnet and subnet != "N/A" else None
      sites[code] = {
        "city":    row["City"].strip(),
        "country": row["Country"].strip(),
        "dc":      row["DC"].strip(),
        "octet":   octet,
      }
  return sites

SITES = _load_sites()

# =============================================================================
# COLOURS  (identical to create-vm.py)
# =============================================================================

class C:
  R  = "\033[0;31m"
  G  = "\033[0;32m"
  Y  = "\033[1;33m"
  B  = "\033[0;34m"
  M  = "\033[0;35m"
  CY = "\033[0;36m"
  W  = "\033[1;37m"
  D  = "\033[2;37m"
  NC = "\033[0m"

def ok(msg):   print(f"  {C.G}[+]{C.NC} {msg}")
def info(msg): print(f"  {C.CY}[i]{C.NC} {msg}")
def warn(msg): print(f"  {C.Y}[!]{C.NC} {msg}")
def err(msg):  print(f"  {C.R}[X]{C.NC} {msg}"); sys.exit(1)
def step(msg): print(f"  {C.M}[->]{C.NC} {msg}")
def dry(msg):  print(f"  {C.B}[DRY]{C.NC} {msg}")

def section(title):
  print()
  print(f"{C.Y}  {'=' * 54}{C.NC}")
  print(f"{C.W}  {title}{C.NC}")
  print(f"{C.Y}  {'=' * 54}{C.NC}")
  print()

def confirm(prompt_text, default="n"):
  """Prompt for y/N confirmation. Returns True if confirmed."""
  yn = "y/N" if default == "n" else "Y/n"
  while True:
    resp = input(f"  {C.Y}{prompt_text} [{yn}]: {C.NC}").strip().lower()
    if resp == "":
      return default == "y"
    if resp in ("y", "yes"):
      return True
    if resp in ("n", "no"):
      return False
    print(f"  {C.R}Please enter y or n.{C.NC}")

def prompt(msg, default=None, validator=None, secret=False):
  """Generic prompt with optional default and validator."""
  suffix = f" [{default}]" if default is not None else ""
  while True:
    if secret:
      val = getpass.getpass(f"  {C.W}{msg}{suffix}: {C.NC}")
    else:
      val = input(f"  {C.W}{msg}{suffix}: {C.NC}").strip()
    if val == "" and default is not None:
      val = default
    if val == "":
      print(f"  {C.R}This field is required.{C.NC}")
      continue
    if validator:
      result = validator(val)
      if result is not True:
        print(f"  {C.R}{result}{C.NC}")
        continue
    return val

def prompt_optional(msg, default=""):
  """Prompt for an optional value — blank is acceptable."""
  val = input(f"  {C.W}{msg}{' [blank to skip]' if not default else f' [{default}]'}: {C.NC}").strip()
  return val if val else default

# =============================================================================
# ARGUMENT PARSING
# =============================================================================

def parse_args():
  parser = argparse.ArgumentParser(
    description="Create PVE + Linux users on a Proxmox node.",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=__doc__,
  )
  parser.add_argument("--host",        help="Proxmox host/IP")
  parser.add_argument("--port",        type=int, default=8006, help="API port (default: 8006)")
  parser.add_argument("--user",        help="Proxmox auth username (e.g. root@pam)")
  parser.add_argument("--token-name",  dest="token_name",  help="API token name for auth")
  parser.add_argument("--token-value", dest="token_value", help="API token value for auth")
  parser.add_argument("--password",    help="Auth password (if no token)")
  parser.add_argument("--node",        help="Proxmox node name")
  parser.add_argument("--realm",       default="pam",
                      help="PVE realm for new users: pam or pve (default: pam)")
  parser.add_argument("--dry-run",     action="store_true", dest="dry_run")
  parser.add_argument("--bulk",        action="store_true")
  parser.add_argument("--log",         default=os.path.expanduser("~/pve-user-create.log"))
  parser.add_argument("--sites-csv",   dest="sites_csv", default=None)
  return parser.parse_args()

# =============================================================================
# PROXMOX CONNECTION  (identical pattern to create-vm.py)
# =============================================================================

def connect(args):
  host = args.host or prompt("Proxmox host/IP")
  port = args.port
  user = args.user or prompt("Proxmox auth username (e.g. root@pam)", default="root@pam")

  if args.token_name and args.token_value:
    auth_method = "token"
    token_name  = args.token_name
    token_value = args.token_value
  elif args.password:
    auth_method = "password"
    password    = args.password
  else:
    print()
    print(f"  {C.W}Authentication method:{C.NC}")
    print(f"  {C.CY}  1{C.NC}  API Token (recommended)")
    print(f"  {C.CY}  2{C.NC}  Username + Password")
    print()
    choice = prompt("Select", default="1",
                    validator=lambda v: True if v in ("1", "2") else "Enter 1 or 2")
    if choice == "1":
      auth_method = "token"
      token_name  = prompt("Token name")
      token_value = prompt("Token value", secret=True)
    else:
      auth_method = "password"
      password    = prompt("Password", secret=True)

  step(f"Connecting to https://{host}:{port} as {user}...")

  try:
    if auth_method == "token":
      proxmox = ProxmoxAPI(
        host, port=port, user=user,
        token_name=token_name, token_value=token_value,
        verify_ssl=False,
      )
    else:
      proxmox = ProxmoxAPI(
        host, port=port, user=user,
        password=password, verify_ssl=False,
      )
    proxmox.version.get()
    ok(f"Connected to {host}:{port}")
    return host, proxmox
  except Exception as e:
    err(f"Connection failed: {e}")

# =============================================================================
# NODE SELECTION  (identical pattern to create-vm.py)
# =============================================================================

def select_node(proxmox, args):
  nodes = proxmox.nodes.get()
  if not nodes:
    err("No nodes found on this Proxmox instance.")

  if args.node:
    names = [n["node"] for n in nodes]
    if args.node not in names:
      err(f"Node '{args.node}' not found. Available: {', '.join(names)}")
    ok(f"Node: {args.node}")
    return args.node

  if len(nodes) == 1:
    node = nodes[0]["node"]
    ok(f"Single node detected: {node}")
    return node

  print()
  print(f"  {C.W}Available nodes:{C.NC}")
  for i, n in enumerate(nodes, 1):
    status = (f"{C.G}online{C.NC}" if n.get("status") == "online"
              else f"{C.R}{n.get('status', '?')}{C.NC}")
    mem_gb = round(n.get("maxmem", 0) / 1024**3, 1)
    print(f"  {C.CY}  {i}{C.NC}  {n['node']}  ({status}, {mem_gb}GB RAM)")
  print()

  def validate_node(v):
    if v.isdigit() and 1 <= int(v) <= len(nodes):
      return True
    return f"Enter a number between 1 and {len(nodes)}"

  choice = int(prompt("Select node", validator=validate_node))
  return nodes[choice - 1]["node"]

# =============================================================================
# PVE GROUPS / ROLES
# =============================================================================

# Default PVE roles available on a fresh install.
# Key = role name, value = description.
PVE_ROLES = {
  "PVEAdmin":        "Full PVE admin — create/delete VMs, manage storage, NO user management",
  "PVEAuditor":      "Read-only access to PVE — view VMs, tasks, logs (default)",
  "PVEDatastoreAdmin":"Full storage/datastore management",
  "PVEDatastoreUser":"Use (clone from) datastores — no management",
  "PVEPoolAdmin":    "Manage pools",
  "PVEPoolUser":     "Use pools",
  "PVESysAdmin":     "System administration — shell, logs, services",
  "PVETemplateUser": "Clone templates",
  "PVEVMAdmin":      "Full VM management — create, delete, configure, start/stop",
  "PVEVMUser":       "Start/stop/console VMs only",
  "Administrator":   "Full cluster administrator (equivalent to root — use sparingly)",
}

def select_role():
  """Prompt for PVE role. Defaults to PVEAuditor."""
  print()
  print(f"  {C.W}Available PVE roles:{C.NC}")
  print()
  roles = list(PVE_ROLES.items())
  for i, (role, desc) in enumerate(roles, 1):
    marker = f"  {C.G}← default{C.NC}" if role == "PVEAuditor" else ""
    print(f"  {C.CY}  {i:>2}{C.NC}  {role:<24}  {C.D}{desc}{C.NC}{marker}")
  print()

  def validate(v):
    if v.isdigit() and 1 <= int(v) <= len(roles):
      return True
    return f"Enter a number between 1 and {len(roles)}"

  # Find the index of PVEAuditor for the default
  default_idx = next(
    (str(i) for i, (r, _) in enumerate(roles, 1) if r == "PVEAuditor"), "2"
  )
  choice = int(prompt("Select role", default=default_idx, validator=validate))
  role_name = roles[choice - 1][0]
  ok(f"PVE role: {role_name}")
  return role_name

def get_pve_groups(proxmox):
  """Return list of existing PVE group IDs."""
  try:
    return sorted(g["groupid"] for g in proxmox.access.groups.get())
  except Exception:
    return []

def select_group(proxmox):
  """Prompt for an optional PVE group to add the user to."""
  groups = get_pve_groups(proxmox)
  if not groups:
    info("No groups defined on this cluster — skipping group assignment.")
    return None

  print()
  print(f"  {C.W}Available PVE groups:{C.NC}")
  print(f"  {C.CY}  0{C.NC}  None — no group assignment")
  for i, g in enumerate(groups, 1):
    print(f"  {C.CY}  {i}{C.NC}  {g}")
  print()

  def validate(v):
    if v.isdigit() and 0 <= int(v) <= len(groups):
      return True
    return f"Enter a number between 0 and {len(groups)}"

  choice = int(prompt("Select group (0 = none)", default="0", validator=validate))
  if choice == 0:
    info("No group assignment.")
    return None
  selected = groups[choice - 1]
  ok(f"Group: {selected}")
  return selected

# =============================================================================
# AUTH METHOD FOR NEW USER
# =============================================================================

def _generate_password(length=20):
  """Generate a secure random password."""
  alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
  return "".join(secrets.choice(alphabet) for _ in range(length))

def _generate_token_value():
  """Generate a UUID-style API token value."""
  h = secrets.token_hex(16)
  return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"

def select_auth_method(username, realm, proxmox, node, dry_run=False):
  """
  Prompt for PVE auth method: password or API token.
  Returns dict with keys: method, password/token_id/token_value.
  Token value is printed once in red — caller must not log it.
  """
  print()
  print(f"  {C.W}PVE authentication for {username}@{realm}:{C.NC}")
  print()
  print(f"  {C.CY}  1{C.NC}  Password  — set a password for PVE web UI / API login")
  print(f"  {C.CY}  2{C.NC}  API Token — generate a token (password-less, recommended for automation)")
  print()
  choice = prompt("Select auth method", default="1",
                  validator=lambda v: True if v in ("1", "2") else "Enter 1 or 2")

  if choice == "1":
    # Password
    print()
    print(f"  {C.W}Set password for {username}@{realm}:{C.NC}")
    print(f"  {C.D}  Leave blank to auto-generate a secure password.{C.NC}")
    print()
    raw = getpass.getpass(f"  {C.W}Password (blank = auto-generate): {C.NC}")
    if not raw:
      raw = _generate_password()
      print()
      print(f"  {C.R}+── AUTO-GENERATED PASSWORD — SHOWN ONCE ─────────────────────────+{C.NC}")
      print(f"  {C.R}│{C.NC}  {C.W}{raw}{C.NC}")
      print(f"  {C.R}+─────────────────────────────────────────────────────────────────+{C.NC}")
      print(f"  {C.R}  Record this now. It will NOT be shown again and is NOT logged.{C.NC}")
      print()
      input(f"  {C.Y}  Press Enter once you have recorded the password...{C.NC}")
    else:
      # Confirm
      confirm_pw = getpass.getpass(f"  {C.W}Confirm password: {C.NC}")
      if raw != confirm_pw:
        err("Passwords do not match.")
    ok(f"Auth: password set for {username}@{realm}")
    return {"method": "password", "password": raw}

  else:
    # API Token
    print()
    print(f"  {C.W}API Token for {username}@{realm}:{C.NC}")
    default_token_id = f"{username}-token"
    token_id = prompt("Token ID (alphanumeric, hyphens ok)", default=default_token_id,
                      validator=lambda v: (
                        True if re.match(r"^[A-Za-z0-9][A-Za-z0-9\-]*$", v)
                        else "Token ID must be alphanumeric with optional hyphens"
                      ))
    print()
    print(f"  {C.CY}Privilege separation:{C.NC}")
    print(f"  {C.D}  Tokens can be restricted to a subset of the user's permissions.{C.NC}")
    print(f"  {C.D}  Recommended for automation: enable privilege separation.{C.NC}")
    print()
    privsep = confirm("Enable privilege separation for this token?", default="y")

    # Generate the token value
    token_value = _generate_token_value()

    if not dry_run:
      step(f"Creating API token {token_id} for {username}@{realm}...")
      try:
        result = proxmox.access.users(f"{username}@{realm}").token(token_id).post(
          privsep=1 if privsep else 0,
        )
        # proxmoxer returns the token value in result["value"]
        if isinstance(result, dict) and "value" in result:
          token_value = result["value"]
        elif isinstance(result, dict) and "data" in result:
          d = result["data"]
          if isinstance(d, dict) and "value" in d:
            token_value = d["value"]
      except Exception as e:
        warn(f"Could not create token via API ({e}) — showing pre-generated value.")
        warn("Create manually: pveum user token add {username}@{realm} {token_id}")

    print()
    print(f"  {C.R}+── API TOKEN — SHOWN ONCE ────────────────────────────────────────+{C.NC}")
    print(f"  {C.R}│{C.NC}")
    print(f"  {C.R}│{C.NC}  {C.W}Token ID   :{C.NC}  {username}@{realm}!{token_id}")
    print(f"  {C.R}│{C.NC}  {C.W}Token Value:{C.NC}  {C.R}{token_value}{C.NC}")
    print(f"  {C.R}│{C.NC}")
    print(f"  {C.R}+──────────────────────────────────────────────────────────────────+{C.NC}")
    print(f"  {C.R}  This token value will NOT be shown again and is NOT logged.{C.NC}")
    print(f"  {C.R}  Record it now — treat it like a password.{C.NC}")
    print()
    input(f"  {C.Y}  Press Enter once you have recorded the token...{C.NC}")

    ok(f"Auth: API token '{token_id}' created for {username}@{realm}")
    return {
      "method":      "token",
      "token_id":    token_id,
      "token_value": token_value,   # caller must NOT log this
    }

# =============================================================================
# SSH / LINUX USER CREATION
# =============================================================================

def _is_local(host):
  """
  Return True if host resolves to an IP on this machine — i.e. the script
  is already running on the target PVE node and SSH would just loop back.
  """
  import socket, subprocess as _sp
  try:
    target_ip = socket.gethostbyname(host)
  except socket.gaierror:
    return False
  if target_ip.startswith("127.") or target_ip == "::1":
    return True
  try:
    local_ips = set()
    for info in socket.getaddrinfo(socket.gethostname(), None):
      local_ips.add(info[4][0])
    r = _sp.run(["hostname", "-I"], capture_output=True, text=True)
    for ip in r.stdout.split():
      local_ips.add(ip.strip())
    return target_ip in local_ips
  except Exception:
    return False


def _local_run(cmd, dry_run=False):
  """
  Run a shell command locally via subprocess.
  Returns (stdout, stderr, exit_code) — same interface as _ssh_run.
  """
  import subprocess as _sp
  if dry_run:
    dry(f"LOCAL: {cmd}")
    return "", "", 0
  result = _sp.run(cmd, shell=True, capture_output=True, text=True)
  return result.stdout.strip(), result.stderr.strip(), result.returncode


def _ssh_connect(host, proxmox_user=None, proxmox_token_name=None,
                 proxmox_token_value=None, proxmox_password=None):
  """
  Return a paramiko SSHClient, the sentinel string "local" if the script is
  already running on the target node, or None if connection is unavailable.

  The "local" sentinel means _ssh_run will delegate to _local_run, avoiding
  a pointless SSH loop-back when create-pve-users.py runs on the node itself.
  """
  if _is_local(host):
    ok(f"Already on {host} — using local subprocess instead of SSH.")
    return "local"

  if not _PARAMIKO:
    warn("paramiko not installed — cannot create Linux shell user automatically.")
    warn("  pip3 install paramiko   (on your workstation)")
    warn("  apt install python3-paramiko  (on the Proxmox node)")
    warn("Run manually on the node:")
    return None

  ssh = paramiko.SSHClient()
  ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

  ansible_key = os.path.expanduser("~/ansible/configs/ansible-id_rsa")
  key_paths   = [ansible_key] if os.path.isfile(ansible_key) else []
  ssh_user    = "root"

  try:
    if key_paths:
      step(f"SSH to {host} as {ssh_user} (key auth)...")
      ssh.connect(host, username=ssh_user, key_filename=key_paths[0], timeout=10)
    else:
      step(f"SSH to {host} as {ssh_user} (password auth)...")
      ssh_pw = getpass.getpass(f"  {C.W}SSH password for {ssh_user}@{host}: {C.NC}")
      ssh.connect(host, username=ssh_user, password=ssh_pw, timeout=10)
    ok(f"SSH connected to {host}")
    return ssh
  except Exception as e:
    warn(f"SSH connection failed: {e}")
    warn("Linux shell user will need to be created manually.")
    return None

def _ssh_run(ssh, cmd, dry_run=False):
  """
  Run a command on the remote host via SSH, or locally if ssh=="local".
  Returns (stdout, stderr, exit_code).
  """
  if ssh == "local":
    return _local_run(cmd, dry_run=dry_run)
  if dry_run:
    dry(f"SSH: {cmd}")
    return "", "", 0
  stdin, stdout, stderr = ssh.exec_command(cmd)
  out  = stdout.read().decode().strip()
  errs = stderr.read().decode().strip()
  rc   = stdout.channel.recv_exit_status()
  return out, errs, rc

def create_linux_user(ssh, username, shell="/usr/bin/zsh", ssh_pubkey=None, dry_run=False):
  """
  Create a Linux shell account on the Proxmox node.
    - useradd -m -s <shell> <username>
    - Optionally installs SSH public key
  Returns True on success.
  """
  section("LINUX SHELL USER")
  step(f"Creating Linux user '{username}' with shell {shell}...")

  if ssh is None:
    if dry_run:
      dry(f"useradd -m -s {shell} {username}")
      if ssh_pubkey:
        dry(f"mkdir -p /home/{username}/.ssh")
        dry(f"echo '<pubkey>' >> /home/{username}/.ssh/authorized_keys")
      return True
    warn("No SSH connection — print commands to run manually:")
    print(f"  {C.CY}  useradd -m -s {shell} {username}{C.NC}")
    if ssh_pubkey:
      print(f"  {C.CY}  mkdir -p /home/{username}/.ssh{C.NC}")
      print(f"  {C.CY}  chmod 700 /home/{username}/.ssh{C.NC}")
      print(f"  {C.CY}  echo '{ssh_pubkey}' >> /home/{username}/.ssh/authorized_keys{C.NC}")
      print(f"  {C.CY}  chmod 600 /home/{username}/.ssh/authorized_keys{C.NC}")
      print(f"  {C.CY}  chown -R {username}:{username} /home/{username}/.ssh{C.NC}")
    return False

  # Check if user already exists
  _, _, rc = _ssh_run(ssh, f"id {username}", dry_run=False)
  if rc == 0 and not dry_run:
    warn(f"Linux user '{username}' already exists — skipping useradd.")
  else:
    # -m creates home dir, -s sets shell
    out, errs, rc = _ssh_run(ssh, f"useradd -m -s {shell} {username}", dry_run)
    if rc != 0 and not dry_run:
      warn(f"useradd returned {rc}: {errs}")
      warn(f"  If shell path {shell} is wrong, check: which zsh")
      return False
    ok(f"Linux user '{username}' created (home: /home/{username}, shell: {shell})")

  # SSH public key
  if ssh_pubkey:
    step(f"Installing SSH public key for '{username}'...")
    cmds = [
      f"mkdir -p /home/{username}/.ssh",
      f"chmod 700 /home/{username}/.ssh",
      # Guard against missing trailing newline before appending
      f"[ -s /home/{username}/.ssh/authorized_keys ] && "
      f"tail -c1 /home/{username}/.ssh/authorized_keys | grep -qP '[^\\n]' && "
      f"printf '\\n' >> /home/{username}/.ssh/authorized_keys; "
      f"printf '%s\\n' '{ssh_pubkey}' >> /home/{username}/.ssh/authorized_keys",
      f"chmod 600 /home/{username}/.ssh/authorized_keys",
      f"chown -R {username}:{username} /home/{username}/.ssh",
    ]
    for cmd in cmds:
      out, errs, rc = _ssh_run(ssh, cmd, dry_run)
      if rc != 0 and not dry_run:
        warn(f"Command failed (rc={rc}): {cmd}")
        warn(f"  {errs}")
    ok(f"SSH public key installed for '{username}'")

  return True

# =============================================================================
# PVE USER CREATION
# =============================================================================

def get_storage_pools(proxmox, node):
  """
  Return list of storage pool IDs available on the given node.
  Filters to pools that can hold ISOs/templates (dir, nfs, cifs, glusterfs types)
  plus any pool with content type 'iso' or 'vztmpl'.
  """
  try:
    pools = proxmox.nodes(node).storage.get()
    result = []
    for p in pools:
      content = p.get("content", "")
      storage_type = p.get("type", "")
      # Include if it can hold ISOs/templates, or is a general-purpose store
      if any(c in content for c in ("iso", "vztmpl", "images", "rootdir")):
        result.append({
          "storage": p["storage"],
          "type":    storage_type,
          "content": content,
        })
    return sorted(result, key=lambda x: x["storage"])
  except Exception as e:
    warn(f"Could not query storage pools: {e}")
    return []

# Storage role options for per-pool ACL grants
STORAGE_ROLES = {
  "PVEDatastoreAdmin": "Full storage admin — upload ISOs, manage content, allocate",
  "PVEDatastoreUser":  "Use datastores — clone/download, no upload or management",
  "PVETemplateUser":   "Clone templates only — most restricted",
}

def select_storage_acls(proxmox, node, userid, dry_run=False):
  """
  Prompt whether to grant per-storage ACLs (needed for ISO upload/download
  in the PVE UI — not covered by root-path role assignment).
  Returns list of (storage_path, role) tuples that were applied.
  """
  pools = get_storage_pools(proxmox, node)
  if not pools:
    info("No storage pools found — skipping storage ACL assignment.")
    return []

  print()
  print(f"  {C.W}Storage pool permissions:{C.NC}")
  print(f"  {C.D}  The root-path role does not grant ISO upload/download in the PVE UI.{C.NC}")
  print(f"  {C.D}  Datastore.AllocateTemplate must be granted at the storage path itself.{C.NC}")
  print()

  if not confirm("Grant per-storage ACLs for this user?", default="y"):
    info("Skipping storage ACL assignment.")
    return []

  print()
  print(f"  {C.W}Available storage pools on {node}:{C.NC}")
  print()
  for i, p in enumerate(pools, 1):
    print(f"  {C.CY}  {i}{C.NC}  {p['storage']:<20}  {C.D}type={p['type']}  content={p['content']}{C.NC}")
  print(f"  {C.CY}  a{C.NC}  All of the above")
  print(f"  {C.CY}  0{C.NC}  None")
  print()

  def validate_pool(v):
    if v == "a" or v == "0":
      return True
    parts = v.replace(",", " ").split()
    if all(p.isdigit() and 1 <= int(p) <= len(pools) for p in parts):
      return True
    return f"Enter 0, a, or numbers 1-{len(pools)} space/comma-separated"

  pool_choice = prompt(
    "Select pools (e.g. 1 3 or a for all)",
    default="a",
    validator=validate_pool,
  )

  if pool_choice == "0":
    info("No storage pools selected.")
    return []

  selected_pools = (
    pools if pool_choice == "a"
    else [pools[int(x) - 1] for x in pool_choice.replace(",", " ").split()]
  )

  print()
  print(f"  {C.W}Storage role to grant:{C.NC}")
  print()
  storage_roles = list(STORAGE_ROLES.items())
  for i, (role, desc) in enumerate(storage_roles, 1):
    marker = f"  {C.G}← recommended{C.NC}" if role == "PVEDatastoreAdmin" else ""
    print(f"  {C.CY}  {i}{C.NC}  {role:<22}  {C.D}{desc}{C.NC}{marker}")
  print()

  def validate_srole(v):
    if v.isdigit() and 1 <= int(v) <= len(storage_roles):
      return True
    return f"Enter a number between 1 and {len(storage_roles)}"

  srole_choice = int(prompt("Select storage role", default="1", validator=validate_srole))
  storage_role = storage_roles[srole_choice - 1][0]
  ok(f"Storage role: {storage_role}")

  # Apply ACLs
  applied = []
  for pool in selected_pools:
    storage_path = f"/storage/{pool['storage']}"
    step(f"Granting {storage_role} to {userid} at {storage_path}...")
    if dry_run:
      dry(f"PUT /access/acl  path={storage_path}  users={userid}  roles={storage_role}")
      applied.append((storage_path, storage_role))
    else:
      try:
        proxmox.access.acl.put(
          path  = storage_path,
          users = userid,
          roles = storage_role,
        )
        ok(f"Granted {storage_role} at {storage_path}")
        applied.append((storage_path, storage_role))
      except Exception as e:
        warn(f"Failed to grant {storage_role} at {storage_path}: {e}")

  return applied


def create_pve_user(proxmox, username, realm, role, group, comment, auth_info,
                    storage_acls=None, dry_run=False):
  """
  Create a PVE user account and assign role + group.
  storage_acls is a list of (path, role) tuples for per-storage ACL grants
  (needed for ISO upload/download in the PVE UI — the root-path role alone
  does not grant Datastore.AllocateTemplate at the storage level).
  """
  section("PVE USER")
  userid = f"{username}@{realm}"
  step(f"Creating PVE user {userid}...")

  if dry_run:
    dry(f"POST /access/users  userid={userid}  comment={comment!r}")
    dry(f"PUT  /access/acl    users/{userid}  role={role}  path=/")
    if group:
      dry(f"PUT  /access/users/{userid}  groups={group}")
    for path, srole in (storage_acls or []):
      dry(f"PUT  /access/acl    users/{userid}  role={srole}  path={path}")
    return True

  # Create the user
  try:
    kwargs = {
      "userid":  userid,
      "comment": comment,
      "enable":  1,
    }
    if auth_info["method"] == "password" and realm == "pve":
      # pve realm users: password can be set at creation time
      kwargs["password"] = auth_info["password"]

    proxmox.access.users.post(**kwargs)
    ok(f"PVE user {userid} created")
  except Exception as e:
    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
      warn(f"PVE user {userid} already exists — continuing with role/group assignment.")
    else:
      warn(f"Failed to create PVE user: {e}")
      return False

  # Assign role at root path
  step(f"Assigning role {role} to {userid} at /...")
  try:
    proxmox.access.acl.put(
      path  = "/",
      users = userid,
      roles = role,
    )
    ok(f"Role '{role}' assigned at path '/'")
  except Exception as e:
    warn(f"Failed to assign role: {e}")

  # Group membership
  if group:
    step(f"Adding {userid} to group {group}...")
    try:
      proxmox.access.users(userid).put(groups=group)
      ok(f"Added to group '{group}'")
    except Exception as e:
      warn(f"Failed to add to group: {e}")

  # PAM realm users: password is set via the shell (passwd command)
  # PVE manages PAM accounts via /etc/shadow — we set it on the Linux side
  if realm == "pam" and auth_info["method"] == "password":
    info(f"PAM realm: password will be set via 'chpasswd' on the Linux host.")

  return True

def set_linux_password(ssh, username, password, dry_run=False):
  """Set the Linux (PAM) password for a user via chpasswd."""
  if ssh is None:
    if dry_run:
      dry(f"echo '{username}:<password>' | chpasswd")
    else:
      warn(f"No SSH — set password manually: echo '{username}:<password>' | chpasswd")
    return
  step(f"Setting Linux password for '{username}' (PAM realm)...")
  # Use chpasswd — pipe username:password to it. Password is not logged or echoed.
  cmd = f"echo '{username}:{password}' | chpasswd"
  out, errs, rc = _ssh_run(ssh, cmd, dry_run)
  if rc != 0 and not dry_run:
    warn(f"chpasswd failed (rc={rc}): {errs}")
  else:
    ok(f"Linux password set for '{username}'")

# =============================================================================
# USER SUMMARY
# =============================================================================

def print_user_summary(username, realm, role, group, comment, auth_info,
                       ssh_pubkey, shell, storage_acls=None, dry_run=False):
  """Print a full summary of what will be / was created."""
  tag = f"{C.B}[DRY RUN]{C.NC} " if dry_run else ""
  print()
  print(f"{C.Y}  {'=' * 54}{C.NC}")
  print(f"{C.W}  {tag}USER CONFIGURATION SUMMARY{C.NC}")
  print(f"{C.Y}  {'=' * 54}{C.NC}")
  print()
  print(f"  {C.W}PVE Account{C.NC}")
  print(f"    {C.CY}User ID  :{C.NC} {username}@{realm}")
  print(f"    {C.CY}Comment  :{C.NC} {comment or '(none)'}")
  print(f"    {C.CY}Role     :{C.NC} {role}  (at path /)")
  print(f"    {C.CY}Group    :{C.NC} {group or '(none)'}")
  print(f"    {C.CY}Auth     :{C.NC} {auth_info['method']}")
  if auth_info["method"] == "token":
    print(f"    {C.CY}Token ID :{C.NC} {username}@{realm}!{auth_info.get('token_id', '?')}")
    print(f"    {C.CY}Token Val:{C.NC} {C.R}(shown above — not repeated here){C.NC}")
  if storage_acls:
    print(f"    {C.CY}Storage  :{C.NC}")
    for path, srole in storage_acls:
      print(f"               {path}  →  {srole}")
  else:
    print(f"    {C.CY}Storage  :{C.NC} (no per-storage ACLs)")
  print()
  print(f"  {C.W}Linux Account{C.NC}")
  print(f"    {C.CY}Username :{C.NC} {username}")
  print(f"    {C.CY}Home     :{C.NC} /home/{username}")
  print(f"    {C.CY}Shell    :{C.NC} {shell}")
  if ssh_pubkey:
    truncated = ssh_pubkey[:40] + "..." if len(ssh_pubkey) > 40 else ssh_pubkey
    print(f"    {C.CY}SSH Key  :{C.NC} {truncated}")
  else:
    print(f"    {C.CY}SSH Key  :{C.NC} (none)")
  print()

# =============================================================================
# LOGGING
# =============================================================================

def write_log(log_file, username, realm, role, group, node, auth_method, dry_run=False):
  """Append a log entry. Token values and passwords are never logged."""
  try:
    os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
    ts   = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = (
      f"{ts}  "
      f"{'[DRY-RUN] ' if dry_run else ''}"
      f"USER={username}@{realm}  "
      f"NODE={node}  "
      f"ROLE={role}  "
      f"GROUP={group or 'none'}  "
      f"AUTH={auth_method}\n"
    )
    with open(log_file, "a") as f:
      f.write(line)
    ok(f"Logged to {log_file}")
  except Exception as e:
    warn(f"Failed to write log: {e}")

# =============================================================================
# MAIN USER CREATION FLOW
# =============================================================================

def create_one_user(args, host, proxmox, node):
  """Run through the user creation questions for a single user. Returns True on success."""

  section("USER IDENTITY")

  # Username
  def validate_username(v):
    if not re.match(r"^[a-z][a-z0-9_\-]{0,31}$", v):
      return "Username must be lowercase, start with a letter, max 32 chars (a-z, 0-9, _, -)"
    return True

  username = prompt("Username (e.g. jsmith, ansible, readonly)",
                    validator=validate_username)
  ok(f"Username: {username}")

  # Realm
  realm_default = getattr(args, "realm", "pam")
  print()
  print(f"  {C.W}PVE realm:{C.NC}")
  print(f"  {C.CY}  1{C.NC}  pam  — Linux PAM (system account + PVE access, recommended)")
  print(f"  {C.CY}  2{C.NC}  pve  — PVE internal (PVE web only, no Linux shell login)")
  print()
  realm_choice = prompt(
    "Realm",
    default="1" if realm_default == "pam" else "2",
    validator=lambda v: True if v in ("1", "2") else "Enter 1 or 2",
  )
  realm = "pam" if realm_choice == "1" else "pve"
  ok(f"Realm: {realm}")

  # Comment / display name
  comment = prompt_optional(f"Display name / comment for {username}@{realm}")

  # Shell
  section("SHELL")
  print(f"  {C.W}Login shell:{C.NC}")
  print(f"  {C.CY}  1{C.NC}  /usr/bin/zsh    (default — consistent with infrastructure convention)")
  print(f"  {C.CY}  2{C.NC}  /bin/bash")
  print(f"  {C.CY}  3{C.NC}  /bin/sh")
  print(f"  {C.CY}  4{C.NC}  /usr/sbin/nologin   (PVE-only account — no shell access)")
  print()
  shell_choice = prompt("Select shell", default="1",
                        validator=lambda v: True if v in ("1","2","3","4") else "Enter 1-4")
  shell_map = {
    "1": "/usr/bin/zsh",
    "2": "/bin/bash",
    "3": "/bin/sh",
    "4": "/usr/sbin/nologin",
  }
  shell = shell_map[shell_choice]
  ok(f"Shell: {shell}")

  # SSH public key (optional)
  section("SSH PUBLIC KEY")
  info("Optionally add an SSH public key to this user's authorized_keys.")
  info("This is required if the user needs SSH access to this or other nodes.")
  print()
  ssh_pubkey = None
  if confirm("Add an SSH public key for this user?", default="y"):
    print()
    print(f"  {C.W}Paste the SSH public key (single line, e.g. ssh-rsa AAAA... user@host):{C.NC}")
    raw_key = input(f"  {C.CY}  Public key: {C.NC}").strip()
    if raw_key.startswith("ssh-") or raw_key.startswith("ecdsa-") or raw_key.startswith("sk-"):
      ssh_pubkey = raw_key
      ok("SSH public key accepted.")
    else:
      warn("Key does not look like a valid SSH public key — skipping.")

  # PVE role
  section("PVE ROLE")
  role = select_role()

  # PVE group (optional)
  section("PVE GROUP")
  group = select_group(proxmox)

  # Storage ACLs — needed for ISO upload/download in PVE UI
  section("STORAGE PERMISSIONS")
  info("The root-path role does not grant ISO upload or download in the PVE UI.")
  info("Per-storage ACLs (Datastore.AllocateTemplate) are required for that.")
  storage_acls = select_storage_acls(proxmox, node, f"{username}@{realm}",
                                     dry_run=args.dry_run)

  # Auth method — password or token
  # Note: token creation needs the PVE user to exist first.
  # We create the user, then create the token in select_auth_method().
  section("AUTHENTICATION")
  info("Choose how this user authenticates to PVE.")
  info("Token values and passwords are shown ONCE and are never written to the log.")
  print()

  # For the auth flow, we need to know the method before user creation
  # so we can set the password at POST time for pve realm users.
  # We pre-collect auth info here; token is actually created after user exists.
  print(f"  {C.W}Auth method for {username}@{realm}:{C.NC}")
  print()
  print(f"  {C.CY}  1{C.NC}  Password  — PVE web UI / API login with username+password")
  print(f"  {C.CY}  2{C.NC}  API Token — token-based auth (recommended for automation)")
  print()
  auth_choice = prompt("Select auth method", default="1",
                       validator=lambda v: True if v in ("1","2") else "Enter 1 or 2")

  # Collect password now; token created after user exists (below)
  auth_info = {}
  if auth_choice == "1":
    print()
    print(f"  {C.W}Set password for {username}@{realm}:{C.NC}")
    print(f"  {C.D}  Leave blank to auto-generate.{C.NC}")
    print()
    raw = getpass.getpass(f"  {C.W}Password (blank = auto-generate): {C.NC}")
    if not raw:
      raw = _generate_password()
      print()
      print(f"  {C.R}+── AUTO-GENERATED PASSWORD — SHOWN ONCE ─────────────────────────+{C.NC}")
      print(f"  {C.R}│{C.NC}  {C.W}{raw}{C.NC}")
      print(f"  {C.R}+─────────────────────────────────────────────────────────────────+{C.NC}")
      print(f"  {C.R}  Record this now. It will NOT be shown again and is NOT logged.{C.NC}")
      print()
      input(f"  {C.Y}  Press Enter once you have recorded the password...{C.NC}")
    else:
      confirm_pw = getpass.getpass(f"  {C.W}Confirm password: {C.NC}")
      if raw != confirm_pw:
        err("Passwords do not match.")
    auth_info = {"method": "password", "password": raw}
    ok(f"Password collected for {username}@{realm}")
  else:
    # Token ID collected now; token created after PVE user exists
    default_token_id = f"{username}-token"
    token_id = prompt(
      "Token ID (alphanumeric, hyphens ok)",
      default=default_token_id,
      validator=lambda v: (
        True if re.match(r"^[A-Za-z0-9][A-Za-z0-9\-]*$", v)
        else "Token ID must be alphanumeric with optional hyphens"
      ),
    )
    privsep = confirm("Enable privilege separation for this token?", default="y")
    auth_info = {
      "method":   "token",
      "token_id": token_id,
      "privsep":  privsep,
    }

  # Summary before doing anything
  print_user_summary(
    username, realm, role, group, comment,
    auth_info, ssh_pubkey, shell,
    storage_acls=storage_acls,
    dry_run=args.dry_run,
  )

  if not confirm("Proceed with user creation?", default="n"):
    warn("Aborted — no changes made.")
    return False

  # ── Create PVE user ───────────────────────────────────────────────────────
  pve_ok = create_pve_user(
    proxmox, username, realm, role, group, comment, auth_info,
    storage_acls=storage_acls,
    dry_run=args.dry_run,
  )

  # ── Create API token (after user exists) ─────────────────────────────────
  if pve_ok and auth_info["method"] == "token":
    section("API TOKEN")
    userid    = f"{username}@{realm}"
    token_id  = auth_info["token_id"]
    privsep   = auth_info.get("privsep", True)
    token_value = _generate_token_value()   # fallback if API call fails

    if not args.dry_run:
      step(f"Creating token '{token_id}' for {userid}...")
      try:
        result = proxmox.access.users(userid).token(token_id).post(
          privsep=1 if privsep else 0,
        )
        if isinstance(result, dict):
          tv = result.get("value") or (result.get("data") or {}).get("value")
          if tv:
            token_value = tv
      except Exception as e:
        warn(f"Token creation via API failed: {e}")
        warn("Create manually on the node:")
        warn(f"  pveum user token add {userid} {token_id}")
    else:
      dry(f"POST /access/users/{userid}/token/{token_id}  privsep={1 if privsep else 0}")

    print()
    print(f"  {C.R}+── API TOKEN — SHOWN ONCE ─────────────────────────────────────────+{C.NC}")
    print(f"  {C.R}│{C.NC}")
    print(f"  {C.R}│{C.NC}  {C.W}Token ID   :{C.NC}  {userid}!{token_id}")
    print(f"  {C.R}│{C.NC}  {C.W}Token Value:{C.NC}  {C.R}{token_value}{C.NC}")
    print(f"  {C.R}│{C.NC}")
    print(f"  {C.R}+───────────────────────────────────────────────────────────────────+{C.NC}")
    print(f"  {C.R}  This token value will NOT be shown again and is NOT logged.{C.NC}")
    print(f"  {C.R}  Record it now — treat it like a password.{C.NC}")
    print()
    input(f"  {C.Y}  Press Enter once you have recorded the token...{C.NC}")
    ok(f"API token '{token_id}' created for {userid}")
    auth_info["token_value"] = "__REDACTED__"   # ensure it never propagates to logs

  # ── Linux shell user (pam realm only, or if explicitly requested) ─────────
  linux_ok = True
  if realm == "pam" or shell != "/usr/sbin/nologin":
    section("SSH CONNECTION")
    if realm != "pam":
      info("Non-PAM realm selected but shell account requested — creating Linux user anyway.")
    ssh = _ssh_connect(host, proxmox_user=None)
    linux_ok = create_linux_user(
      ssh, username, shell=shell, ssh_pubkey=ssh_pubkey, dry_run=args.dry_run,
    )
    # Set PAM password on Linux side
    if realm == "pam" and auth_info["method"] == "password" and linux_ok:
      set_linux_password(ssh, username, auth_info["password"], dry_run=args.dry_run)
    if ssh and ssh != "local":
      ssh.close()
  else:
    info("PVE-only realm with nologin shell — skipping Linux account creation.")

  # ── Log (no secrets) ─────────────────────────────────────────────────────
  write_log(
    args.log, username, realm, role, group, node,
    auth_info["method"], dry_run=args.dry_run,
  )

  # ── Done ─────────────────────────────────────────────────────────────────
  print()
  print(f"{C.G}  +======================================================+{C.NC}")
  print(f"{C.G}  |{C.W}  {'DRY RUN COMPLETE' if args.dry_run else 'USER CREATION COMPLETE':<50}{C.G}  |{C.NC}")
  print(f"{C.G}  +======================================================+{C.NC}")
  print()
  ok(f"PVE User : {username}@{realm}")
  ok(f"Role     : {role}  (at path /)")
  if storage_acls:
    for path, srole in storage_acls:
      ok(f"Storage  : {srole}  at {path}")
  if group:
    ok(f"Group    : {group}")
  ok(f"Shell    : {shell}")
  ok(f"Node     : {node}")
  print()
  return True

# =============================================================================
# MAIN
# =============================================================================

def main():
  args = parse_args()

  print()
  print(f"{C.CY}  +========================================================+{C.NC}")
  print(f"{C.CY}  |{C.W}            PROXMOX VE — USER PROVISIONING{C.CY}              |{C.NC}")
  print(f"{C.CY}  |{C.D}                    jukebox.internal                    {C.CY}|{C.NC}")
  if args.dry_run:
    print(f"{C.CY}  |{C.B}              *** DRY RUN — NO CHANGES ***              {C.CY}|{C.NC}")
  if args.bulk:
    print(f"{C.CY}  |{C.B}           *** BULK MODE — Ctrl+C to exit ***           {C.CY}|{C.NC}")
  print(f"{C.CY}  +========================================================+{C.NC}")
  print()

  global SITES
  if args.sites_csv:
    SITES = _load_sites(args.sites_csv)
    ok(f"Sites loaded from {args.sites_csv} ({len(SITES)} sites)")

  section("CONNECTING TO PROXMOX")
  if args.dry_run:
    warn("Dry run mode — no users will be created")

  host, proxmox = connect(args)
  node          = select_node(proxmox, args)

  user_count = 0
  while True:
    create_one_user(args, host, proxmox, node)
    user_count += 1

    if not args.bulk:
      break

    print()
    print(f"{C.CY}  ── Bulk mode: {user_count} user(s) created this session ───────────{C.NC}")
    if not confirm("Create another user?", default="y"):
      break

  if args.bulk and user_count > 0:
    print()
    ok(f"Bulk session complete — {user_count} user(s) created.")
    print()


if __name__ == "__main__":
  try:
    main()
  except KeyboardInterrupt:
    print(f"\n\n  {C.Y}[!]{C.NC} Interrupted — no changes made.\n")
    sys.exit(0)
