# Example Music Limited — Beginner's Guide to Ansible

> **Classification:** Internal — Infrastructure
> **Forest:** `jukebox.internal`
> **Domains:** `example.net` · `example.org` · `example.com`
> **Provisioning network:** `192.168.139.0/24`
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Purpose

This document provides a practical introduction to Ansible using a real troubleshooting and learning session performed on `EXASRVCLD001`.

Unlike many introductory guides, this document includes actual command output captured during a live session. New administrators are encouraged to compare their own output with the examples shown here.

---

## What is Ansible?

Ansible is an automation framework used to configure, deploy and maintain systems.

Rather than manually logging into servers and performing repetitive administrative tasks, administrators write **playbooks** which describe the desired state of a system.

Typical uses include:

- Installing software
- Managing users
- Deploying configuration files
- Managing DNS
- Restarting services
- Provisioning infrastructure

At Example Music, Ansible is used as the primary Linux configuration and deployment platform.

---

## Example Environment

The following examples were captured from:

```text
Hostname : EXASRVCLD001
Address  : 192.168.139.8
Role     : DNS Server
Domain   : jukebox.internal
```

---

## Understanding an Ansible Playbook Command

The following command was executed:

```text
ansible@exasrvcld001[~/ansible]$ ansible-playbook -i /home/ansible/ansible/configs/inventory --limit ansiblehosts --check --diff --step playbooks/linux/tools.yml
```

Breaking this down:

| Option | Purpose |
|--------|---------|
| `ansible-playbook` | Executes a playbook |
| `-i` | Specifies inventory file |
| `--limit ansiblehosts` | Restricts execution to hosts in the `ansiblehosts` group |
| `--check` | Dry-run mode |
| `--diff` | Show changes that would occur |
| `--step` | Prompt before every task |
| `playbooks/linux/tools.yml` | Playbook being executed |

---

## Example Playbook Execution

The following output was captured exactly during execution:

```text
ansible@exasrvcld001[~/ansible]$ ansible-playbook -i /home/ansible/ansible/configs/inventory --limit ansiblehosts --check --diff --step playbooks/linux/tools.yml
[WARNING]: Deprecation warnings can be disabled by setting `deprecation_warnings=False` in ansible.cfg.
[DEPRECATION WARNING]: community.general.yaml has been deprecated. The plugin has been superseded by the the option `result_format=yaml` in callback plugin ansible.builtin.default from ansible-core 2.13 onwards. This feature will be removed from collection 'community.general' version 12.0.0.

PLAY [Deploy common tools] *************************************************************************************************************************************************
Perform task: TASK: Gathering Facts (N)o/(y)es/(c)ontinue: y

Perform task: TASK: Gathering Facts (N)o/(y)es/(c)ontinue: *****************************************************************************************************************

TASK [Gathering Facts] *****************************************************************************************************************************************************
ok: [192.168.139.8]
Perform task: TASK: Install common packages (N)o/(y)es/(c)ontinue: y

Perform task: TASK: Install common packages (N)o/(y)es/(c)ontinue: *********************************************************************************************************

TASK [Install common packages] *********************************************************************************************************************************************
The following additional packages will be installed:
  libblas3 liblinear4 liblua5.4-0 nmap-common
Suggested packages:
  liblinear-tools liblinear-dev ncat ndiff zenmap
The following NEW packages will be installed:
  libblas3 liblinear4 liblua5.4-0 nmap nmap-common
0 upgraded, 5 newly installed, 0 to remove and 0 not upgraded.
changed: [192.168.139.8]
Perform task: TASK: Set default shell to zsh for ansible user (N)o/(y)es/(c)ontinue: y

Perform task: TASK: Set default shell to zsh for ansible user (N)o/(y)es/(c)ontinue: ***************************************************************************************

TASK [Set default shell to zsh for ansible user] ***************************************************************************************************************************
changed: [192.168.139.8]

PLAY RECAP *****************************************************************************************************************************************************************
192.168.139.8             : ok=3    changed=2    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

---

## Understanding the Output

The play begins with:

```text
PLAY [Deploy common tools]
```

This indicates that Ansible has started executing a play called `Deploy common tools`.

The first task:

```text
TASK [Gathering Facts]
ok: [192.168.139.8]
```

collects information about the remote host including operating system, hostname, network interfaces, CPU information, and memory information.

The following line:

```text
changed: [192.168.139.8]
```

does **not** indicate an error. It indicates that Ansible believes a change would be required. Because this run used `--check`, the changes were simulated rather than executed.

---

## Understanding ansible.cfg

The `ansible.cfg` file is generated automatically by `ansibleme.sh` when the Ansible control node is first set up. The current production configuration is:

```ini
# =================================================================================================
# Ansible Configuration
#
# Purpose:
#   Central configuration for Example Music infrastructure automation.
#
# Used for:
#   - Initial host onboarding / bootstrap
#   - Inventory-driven configuration management
#   - Ongoing estate administration
#
# Environment assumptions:
#   - Hosts may be powered off at any time
#   - Inventory may be generated dynamically
#   - DNS may not exist during bootstrap
#   - SSH keys are distributed before Ansible runs
#
# Notes:
#   - Unreachable hosts are NOT ignored via ansible.cfg. That behaviour must be configured in
#     playbooks using:
#
#       ignore_unreachable: true
#
#     or handled explicitly with tasks/meta directives.
# =================================================================================================
[defaults]
# Automatically discover correct Python interpreter on remote systems sans warnings.
interpreter_python = auto_silent
host_key_checking  = True
# Primary inventory location.
inventory = /home/ansible/ansible/configs/inventory
# Default SSH user.
remote_user = ansible
# SSH private key used for authentication.
private_key_file = /home/ansible/ansible/configs/ansible-id_rsa
# Human-readable task output.
stdout_callback = ansible.builtin.default
result_format = yaml
# Enable callback plugins — required for exa_pretty and other custom callbacks.
bin_ansible_callbacks = True
# Number of parallel worker processes. Increasing improves performance when managing
# large numbers of hosts.
forks = 50
# SSH connection timeout (seconds). Important when hosts may be powered off.
timeout = 5
# Retry files record failed hosts. Store in /tmp rather than cluttering working directories.
retry_files_enabled = True
retry_files_save_path = /tmp

[privilege_escalation]
# Standard privilege escalation settings.
become = True
become_method = sudo
become_user = root

[ssh_connection]
# SSH connection settings.
#
# ControlMaster=auto                Reuse existing SSH sessions where possible.
# ControlPersist=60s                Keep SSH control connections alive for 60 seconds.
# StrictHostKeyChecking=accept-new  Automatically trust new hosts; reject changed fingerprints.
ssh_args = -o ControlMaster=auto -o ControlPersist=60s -o StrictHostKeyChecking=accept-new
# Enable SSH pipelining — reduces SSH operations required, improves execution speed.
pipelining = True
# Fail quickly when a host is unavailable.
connect_timeout = 5

[persistent_connection]
# Settings used by persistent SSH connections (useful for larger environments and network modules).
# Maximum command runtime.
command_timeout = 30
# Time spent retrying persistent connections.
connect_retry_timeout = 15
# =================================================================================================
# RECOMMENDED PLAYBOOK SETTINGS FOR INTERMITTENT HOSTS
# =================================================================================================
#
# Example:
#
# - hosts: all
#   gather_facts: false
#   ignore_unreachable: true
#   strategy: free
#
# Explanation:
#
# gather_facts: false         Avoid immediate failures during fact gathering.
# ignore_unreachable: true    Continue processing remaining hosts even if some nodes are offline.
# strategy: free              Allows hosts to progress independently instead of waiting for the
#                             slowest host.
# =================================================================================================
```

Important settings and why they differ from a default Ansible installation:

| Setting | Value | Reason |
|---------|-------|--------|
| `host_key_checking` | `True` | Changed from the old `False` — `accept-new` handles new hosts correctly while `True` catches changed fingerprints as a MITM safeguard |
| `stdout_callback` | `ansible.builtin.default` | Correct for ansible-core 2.13+; the old bare `yaml` value was a `result_format` value not a callback name |
| `result_format` | `yaml` | Human-readable YAML output — set explicitly alongside `stdout_callback` |
| `StrictHostKeyChecking` | `accept-new` | Trusts new host keys on first connect but rejects changed keys — unlike `no` which accepts everything silently |
| `forks` | `50` | Default is 5 — increased for an estate this size |
| `timeout` | `5` | Short timeout — hosts may be powered off and we don't want long waits |
| `connect_timeout` | `5` | Same rationale as `timeout` |
| `[persistent_connection]` | Present | Required for network modules and larger parallel runs |

> **Note on `StrictHostKeyChecking=accept-new`:** this is a deliberate security improvement over `no`. With `no`, a changed host key (e.g. from a rebuilt node or a MITM attack) is silently accepted. With `accept-new`, new hosts are trusted on first connect, but a changed fingerprint for a known host causes a hard failure with a clear error message. See Section 7b of `ansibleme.sh` for how stale known_hosts entries from rebuilt nodes are pre-cleared before any scan runs.

---

## Colourised Output — exa_pretty Callback

All Example Music Ansible playbooks use a custom callback plugin (`callback_plugins/exa_pretty.py`) that provides colourised terminal output following the same colour scheme as `firewallme.sh` and `ansibleme.sh`:

| Symbol | Colour | Meaning |
|--------|--------|---------|
| `[+]` | Green | Task ok / no change needed |
| `[→]` | Cyan | Task changed something |
| `[!]` | Yellow | Skipped / warning |
| `[✗]` | Red | Failed / unreachable |

This is enabled in `ansible.cfg` via:

```ini
stdout_callback   = exa_pretty
callbacks_enabled = exa_pretty
```

### Colour Constants — group_vars/all/colours.yml

The same ANSI colour codes used in the shell scripts are available as Ansible variables to all playbooks and roles. They are defined in `group_vars/all/colours.yml` and loaded automatically for every host in every play — no `vars_files` reference is needed.

```yaml
# group_vars/all/colours.yml
# Example Music Limited — ANSI colour constants
# Available in all playbooks, roles, and task files as {{ _c.G }}, {{ _c.R }} etc.
#
# Mapping mirrors firewallme.sh / ansibleme.sh line 128:
#   RED    \033[0;31m  → _c.R
#   GREEN  \033[0;32m  → _c.G
#   YELLOW \033[1;33m  → _c.Y
#   ORANGE \033[38;5;208m → _c.O
#   CYAN   \033[0;36m  → _c.C
#   WHITE  \033[1;37m  → _c.W
#   NC     \033[0m     → _c.NC (reset)

_c:
  R:  "\e[0;31m"
  G:  "\e[0;32m"
  Y:  "\e[1;33m"
  O:  "\e[38;5;208m"
  C:  "\e[0;36m"
  W:  "\e[1;37m"
  NC: "\e[0m"
```

Because it is in `group_vars/all/`, the `_c` dict is available everywhere without any import. Use it in `debug` task messages and `pause` prompt strings:

```yaml
- name: Show a colourised message
  ansible.builtin.debug:
    msg: "{{ _c.G }}[+]{{ _c.NC }} Task completed on {{ _c.W }}{{ inventory_hostname }}{{ _c.NC }}"

- name: Prompt operator with colour
  ansible.builtin.pause:
    prompt: |
      {{ _c.Y }}[!]{{ _c.NC }} Review the above carefully.
      Type {{ _c.G }}yes{{ _c.NC }} to proceed
```

> **Why `group_vars/all/` and not the role's `vars/` directory?** Placing it in `group_vars/all/` means the colour constants are available to every play — Windows playbooks, the bootstrap playbook, the firewall role, and any future playbooks — without needing a `vars_files:` reference in each one. A `vars/` file inside a role is only loaded when that role runs.

---

## Understanding Sudo and Become

When Ansible executes package management tasks it usually requires root privileges. This configuration enables automatic privilege escalation:

```ini
[privilege_escalation]
become       = True
become_method = sudo
become_user  = root
```

A common troubleshooting step is verifying whether passwordless sudo is functioning correctly.

---

## Investigating Passwordless Sudo

The following commands were used during troubleshooting.

Verify the sudoers entry:

```text
ansible@exasrvcld001[~/ansible]$ sudo cat /etc/sudoers.d/ansible

# Ansible automation - full passwordless sudo
ansible ALL=(ALL) NOPASSWD: ALL
```

Verify group membership:

```text
ansible@exasrvcld001[~/ansible]$ groups

ansible adm cdrom sudo dip users kvm
```

Verify effective permissions:

```text
ansible@exasrvcld001[~/ansible]$ sudo -l

Matching Defaults entries for ansible on exasrvcld001:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin, use_pty

User ansible may run the following commands on exasrvcld001:
    (ALL : ALL) ALL
    (ALL) NOPASSWD: ALL
```

The important line is:

```text
(ALL) NOPASSWD: ALL
```

which confirms that passwordless sudo has been granted.

---

## Verifying Sudoers Configuration

The configuration file permissions were checked:

```text
ansible@exasrvcld001[~/ansible]$ ls -l /etc/sudoers.d/ansible

-r--r----- 1 root root 78 Jun 14 11:19 /etc/sudoers.d/ansible
```

The sudoers configuration was validated:

```text
ansible@exasrvcld001[~/ansible]$ sudo visudo -c

/etc/sudoers: parsed OK
/etc/sudoers.d/README: parsed OK
/etc/sudoers.d/ansible: parsed OK
```

This confirms there are no syntax errors.

---

## Understanding Include Order

The following commands were executed:

```text
ansible@exasrvcld001[~/ansible]$ sudo grep -n "sudo" /etc/sudoers
sudo grep -n "includedir" /etc/sudoers

49:# Allow members of group sudo to execute any command
50:%sudo        ALL=(ALL:ALL) ALL

54:@includedir /etc/sudoers.d
54:@includedir /etc/sudoers.d
```

This is important because `@includedir /etc/sudoers.d` appears after `%sudo ALL=(ALL:ALL) ALL`, which means the custom file `/etc/sudoers.d/ansible` is processed afterwards.

---

## Testing Passwordless Sudo Correctly

Many administrators use `sudo -v` when testing sudo. The following commands were used instead:

```text
ansible@exasrvcld001[~/ansible]$ sudo -k
sudo id

uid=0(root) gid=0(root) groups=0(root)
```

and:

```text
ansible@exasrvcld001[~/ansible]$ sudo -k
sudo whoami

root
```

These tests prove that sudo can execute privileged commands without prompting for a password.

---

## Reboot Verification

After troubleshooting, the server was rebooted:

```text
ansible@exasrvcld001[~/ansible]$ sudo reboot
ansible@exasrvcld001[~/ansible]$ Connection to 192.168.139.8 closed by remote host.
Connection to 192.168.139.8 closed.
```

The administrator then reconnected:

```text
knightmare@orangepipc:~$ ssh ansible@192.168.139.8
ansible@192.168.139.8's password:
```

The login banner confirmed successful startup:

```text
╔══════════════════════════════════════════════════════════════╗
║           EXAMPLE MUSIC LIMITED: exasrvcld001            ║
╚══════════════════════════════════════════════════════════════╝

  Role     : DNS Server -- jukebox.internal
  Zone     : jukebox.internal  (708 A records, serial serial)

  ── Network ──────────────────────────────────────────────────
    DNS IP   : 192.168.139.8
    BIND9    : active

  ── System ───────────────────────────────────────────────────
    Uptime   : up 1 minute
    Load     : 0.27 0.15 0.06
    Memory   : 189MB used of 425MB
    Disk /   : 1.8G used of 3.7G (52%)
```

Passwordless sudo was tested again:

```text
ansible@exasrvcld001[~]$ sudo -k
sudo whoami

root
```

System uptime immediately after reboot:

```text
ansible@exasrvcld001[~]$ uptime
 18:39:12 up 1 min,  1 user,  load average: 0.25, 0.15, 0.06
```

This confirms that the sudo configuration remained functional after reboot.

---

## Recommended Workflow for New Administrators

Before executing any unfamiliar playbook:

```bash
ansible-playbook -i inventory --limit HOSTGROUP --check --diff --step playbook.yml
```

Review every task carefully. Once satisfied:

```bash
ansible-playbook -i inventory --limit HOSTGROUP playbook.yml
```

Always verify inventory, target hosts, become configuration, and sudo permissions before running production changes.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-14 | Initial document |
| 2026-06-20 | Updated `ansible.cfg` to reflect current `ansibleme.sh`-generated config (`ansible.builtin.default` callback, `result_format`, `StrictHostKeyChecking=accept-new`, `forks`, `[persistent_connection]`) |
| 2026-06-20 | Added colourised output section — `exa_pretty` callback and `group_vars/all/colours.yml` |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
