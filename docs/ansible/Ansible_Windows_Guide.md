# Example Music Limited — Ansible Windows Playbook Guide

> **Classification:** Internal — Infrastructure
> **Forest:** `jukebox.internal`
> **Domains:** `example.net` · `example.org` · `example.com`
> **Provisioning network:** `192.168.139.0/24`
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Purpose

This document covers the day-to-day operation of the Example Music Ansible Windows playbook set — specifically `windows_bootstrap`, the chain that takes a freshly PXE-built Windows host and brings it to a known-good, domain-joined state. It is aimed at engineers who have infrastructure experience but may be unfamiliar with Ansible's specific idioms — particularly around inventory, variable precedence, vaults, and how Windows connectivity differs from Linux.

If you have used Salt or Puppet before, the mental model maps reasonably well: inventory ≈ Salt targeting / Puppet node classifier, group_vars ≈ Salt grains/pillars / Puppet Hiera, vault ≈ Salt pillar encryption / Puppet eyaml, handlers ≈ Salt reactors / Puppet notify/subscribe.

All commands below are run from the `ansible/` root of the repository.

---

## Quick Reference

| Task | Command |
|------|---------|
| Full bootstrap (new host) | `ansible-playbook -i configs/inventory playbooks/windows_bootstrap/site.yml -e target=<host> --ask-vault-pass` |
| Single stage | `ansible-playbook -i configs/inventory playbooks/windows_bootstrap/site.yml -e target=<host> --tags registry --ask-vault-pass` |
| Single playbook, standalone | `ansible-playbook -i configs/inventory playbooks/windows_bootstrap/playbooks/20-registry.yml -e target=<host> --ask-vault-pass` |
| Dry run | `ansible-playbook -i configs/inventory playbooks/windows_bootstrap/site.yml -e target=<host> --check --ask-vault-pass` |
| Ad-hoc connectivity test | `ansible -i configs/inventory <host> -m ansible.windows.win_ping` |
| Domain join only | `ansible-playbook -i configs/inventory playbooks/windows_bootstrap/playbooks/80-domainjoin.yml -e target=<host> --ask-vault-pass` |

A full run with no `--tags` runs every play in the chain, in order — this is deliberate, not a shorthand for "just the essentials". Every play is idempotent, so it's always safe to re-run the whole chain against an already-bootstrapped host; it converges to the same known-good state regardless of starting point. See [Running the Bootstrap](#running-the-bootstrap-new-host) below. DC promotion is a separate module (`windows_dc/site.yml`) run afterward, not part of this chain.

---

## Prerequisites

### On EXAANSCLD001

Required Ansible collections:

```bash
ansible@EXAANSCLD001:~> ansible-galaxy collection install -r playbooks/windows_bootstrap/requirements.yml
```

Verify:

```bash
ansible@EXAANSCLD001:~> ansible-galaxy collection list | grep -E "windows|chocolatey|microsoft"
```

Expected:

```text
ansible.windows         2.x.x
chocolatey.chocolatey   1.x.x
community.windows       2.x.x
microsoft.ad            1.x.x
```

SSH is the default connection method (see [Windows Connectivity](#windows-connectivity) below) — no `pywinrm` install is needed unless you're specifically falling back to WinRM for a host that predates the standard PXE build process.

---

## Project Layout

```text
ansible/
├── ansible.cfg                                  ← project config (SSH settings, collection paths)
│
├── configs/inventory/
│   ├── main.ini                                 ← top-level inventory, includes the per-site files
│   ├── cld.ini / fal.ini / liv.ini               ← one file per site
│   └── rudder.ini
│
├── group_vars/
│   ├── all/
│   │   ├── vars.yml                             ← variables for every host (domain, SSH key, Chocolatey source)
│   │   └── vault.yml                             ← encrypted secrets (passwords)
│   ├── windows/vars.yml                          ← all Windows hosts (registry_common, choco packages)
│   ├── windows_server/vars.yml                   ← SRV/DCS hosts
│   ├── windows_desktop/vars.yml                  ← WKS hosts (deadvertise on)
│   ├── windows_laptop/vars.yml                   ← LAP/SUR hosts (hibernation on)
│   ├── windows_dc/{vars,vault}.yml               ← DC-specific (see windows_dc module, not this guide)
│   └── windows_nodes/connection.yml               ← shared connection settings (SSH, ports) for inventory-grouped hosts
│
└── playbooks/windows_bootstrap/
    ├── site.yml                                  ← entry point — chain-imports every stage below in order
    ├── requirements.yml
    ├── README.md                                 ← authoritative playbook-order table and tags
    ├── handlers/main.yml                          ← reboot, restart sshd/rdp, apply wallpaper
    ├── tasks/                                     ← shared logic included by multiple stages
    │   ├── arch_facts.yml                        ← CPU arch detection (AMD64/ARM64 → x86_64/arm64)
    │   ├── hostname_facts.yml                     ← EXA[ROLE][SITE][NNN] hostname parsing
    │   ├── preflight.yml                          ← DC/DNS/URL reachability checks (used by 00-preflight.yml)
    │   ├── site_detection.yml                     ← hypervisor + IP-to-site mapping
    │   ├── guest_tools.yml                         ← VMware/QEMU guest tools
    │   ├── ps7_setup.yml                           ← PS7 modules, fonts, terminal config
    │   └── ou_selection.yml                        ← NOT currently used — see its own header note
    └── playbooks/
        ├── 00-preflight.yml                       ← credentials, hostname, static IP, SSH hardening
        ├── 10-rename.yml                          ← rename to EXA convention
        ├── 15-locale-timezone.yml                 ← locale (en-GB) and timezone (GMT Standard Time)
        ├── 20-registry.yml                        ← registry hardening
        ├── 22-screenlock.yml                      ← screen lock and inactivity timeout
        ├── 25-deadvertise.yml                     ← advertising/telemetry suppression (desktop + laptop)
        ├── 30-chocolatey.yml                      ← Chocolatey installation
        ├── 35-guest-tools.yml                     ← hypervisor guest tools
        ├── 40-choco-packages.yml                  ← package deployment
        ├── 45-rsat.yml                            ← RSAT tools
        ├── 48-pswindowsupdate.yml                 ← PSWindowsUpdate module
        ├── 50-binaries.yml                        ← arch-aware binary + font deployment
        ├── 60-wallpaper.yml                       ← corporate wallpaper + dark mode
        ├── 70-hibernation.yml                     ← power management by host type
        ├── 75-openssh.yml                         ← OpenSSH + Ansible key
        ├── 77-rdp.yml                             ← RDP with NLA
        ├── 78-sac-ems.yml                         ← SAC/EMS serial console (Server OS only)
        ├── 79-ps7-setup.yml                       ← PS7 modules, fonts, profile, terminal config
        ├── 80-domainjoin.yml                      ← domain join
        └── 85-finish.yml                          ← remote-access summary + final reboot
```

The full, current playbook-order table (with tags) lives in `playbooks/windows_bootstrap/README.md` — treat that as the source of truth if this list and the README ever disagree.

---

## Inventory

### Structure

Ansible inventory maps hosts to groups. The Windows playbooks use four groups, organised as a hierarchy:

```ini
# configs/inventory/mcr.ini (illustrative — actual per-site files are cld.ini/fal.ini/liv.ini)

[windows_server]
EXASRVMCR001  ansible_host=192.168.161.20
EXADCSMCR001  ansible_host=192.168.161.10

[windows_desktop]
EXAWKSMCR001  ansible_host=192.168.161.105

[windows_laptop]
EXALAPMCR001  ansible_host=192.168.161.112

# windows is a group of groups — every host above inherits group_vars/windows/
[windows:children]
windows_server
windows_desktop
windows_laptop
```

The `[windows:children]` block is the key thing here. It means `group_vars/windows/vars.yml` applies to every host in all three subgroups — connection settings, common packages, and the common registry key list all come from there. The subgroup `vars.yml` files then layer on top with type-specific additions. This is Ansible's variable precedence in action: more specific groups win over less specific ones.

A freshly PXE-built host being bootstrapped for the first time is **not** in inventory at all — `windows_bootstrap`'s numbered playbooks are specifically designed to run against a bare IP with no group membership (see the design note in `40-choco-packages.yml` for why). Add it to inventory only *after* the bootstrap chain completes and it has its permanent name.

### Targeting Specific Hosts

Every playbook accepts a `target` variable that limits execution to a single host or group:

```bash
# Single host
ansible-playbook -i configs/inventory playbooks/windows_bootstrap/playbooks/20-registry.yml -e target=EXAWKSMCR001

# All hosts in a group
ansible-playbook -i configs/inventory playbooks/windows_bootstrap/playbooks/20-registry.yml -e target=windows_desktop
```

---

## Credentials and Vault

### How the Vault Works

Ansible Vault is symmetric encryption (AES-256) applied to a YAML file. The vault file lives alongside other `group_vars` files and is decrypted in memory at runtime — nothing is written to disk in plaintext. It is conceptually the same as Salt's encrypted pillar or Puppet's eyaml.

The main vault file is at `group_vars/all/vault.yml`. When encrypted it looks like:

```text
$ANSIBLE_VAULT;1.1;AES256
61383866623937623263663139343834346265646634653561323934383933373032313634356633
...
```

Variables defined in the vault are referenced in playbooks and `vars.yml` files exactly like any other variable — Ansible handles the decryption transparently. This repo commits vault files in **plaintext with `CHANGEME`/placeholder values** — they are templates for the operator to populate and `ansible-vault encrypt` locally, not pre-encrypted secrets.

### Variables in the Vault

```yaml
# group_vars/all/vault.yml (shown decrypted — encrypt this file before real use, never commit plaintext real secrets)
vault_local_admin_password:   "CHANGEME"
vault_domain_join_password:   "CHANGEME"
vault_winrm_password:         "CHANGEME"
```

The domain join user is derived from `benarbejde/ad_forest.json` (`exa_domain_join_user` in `group_vars/all/vars.yml`) — only the password is in the vault. Note: `00-preflight.yml`'s own `vars_prompt` also asks for `vault_domain_join_password` interactively at bootstrap time (see [Running the Bootstrap](#running-the-bootstrap-new-host)) — the vault value is the default if you just press Enter.

### Setting Up the Vault

```bash
ansible@EXAANSCLD001:~> ansible-vault encrypt group_vars/all/vault.yml
ansible@EXAANSCLD001:~> ansible-vault edit group_vars/all/vault.yml
ansible@EXAANSCLD001:~> ansible-vault view group_vars/all/vault.yml
ansible@EXAANSCLD001:~> ansible-vault rekey group_vars/all/vault.yml
```

### Providing the Vault Password at Runtime

**Option 1 — interactive prompt (safest for shared machines):**

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i configs/inventory playbooks/windows_bootstrap/site.yml \
  -e target=EXADCSMCR001 --ask-vault-pass
Vault password:
```

**Option 2 — vault password file (convenient for a dedicated control node):**

```bash
ansible@EXAANSCLD001:~> echo "YourVaultPassword" > ~/.vault_pass
ansible@EXAANSCLD001:~> chmod 600 ~/.vault_pass
```

Uncomment in `ansible.cfg`:

```ini
vault_password_file = ~/.vault_pass
```

After this, no `--ask-vault-pass` flag is needed. The vault password file must be `chmod 600` — Ansible refuses to use it otherwise.

**Option 3 — runtime override (emergency / no vault access):**

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i configs/inventory playbooks/windows_bootstrap/playbooks/80-domainjoin.yml \
  -e target=EXADCSMCR001 \
  -e vault_domain_join_password="YourPassword"
```

The password appears in the process table and shell history. Clear history afterwards:

```bash
ansible@EXAANSCLD001:~> history -d $(history 1 | awk '{print $1}')
```

Use Option 1 for routine work. Option 2 for `EXAANSCLD001` where you trust the machine. Option 3 only in an emergency.

---

## Windows Connectivity

### SSH vs WinRM

The playbooks default to SSH (installed by `UNATTEND.CMD` and configured/hardened by `75-openssh.yml`). WinRM is available as a fallback for hosts that predate the standard PXE build process and don't have SSH configured.

SSH is strongly preferred — it uses the same key-based auth as Linux, it is firewall-friendly (single port 22), and it does not require the certificate management overhead of WinRM HTTPS.

To switch a host to WinRM, override in the inventory entry:

```ini
[windows_desktop]
EXAWKSOLD001  ansible_host=192.168.161.99 \
  ansible_connection=winrm \
  ansible_winrm_transport=basic \
  ansible_winrm_server_cert_validation=ignore \
  ansible_port=5986
```

### Verify Connectivity

Before running any playbook, confirm Ansible can reach the host:

```bash
ansible@EXAANSCLD001:~> ansible -i configs/inventory EXAWKSMCR001 -m ansible.windows.win_ping
```

Expected output:

```text
EXAWKSMCR001 | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

If it fails, add `-vvv` for verbose output — shows the exact SSH/WinRM handshake:

```bash
ansible@EXAANSCLD001:~> ansible -i configs/inventory EXAWKSMCR001 -m ansible.windows.win_ping -vvv
```

Common failure reasons and fixes:

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Connection refused` on port 22 | sshd not running | RDP in, run `Start-Service sshd` |
| `Authentication failed` | Wrong user or key not deployed | Check `exa_ansible_pub_key` in `group_vars/all/vars.yml`, re-run `75-openssh.yml` |
| `Timeout` | Host unreachable / firewall | Check routing, check firewall rule on host |
| `WinRM connection error` | WinRM not configured | Host was never bootstrapped, or SSH was never enabled |

---

## Running the Bootstrap (New Host)

`00-preflight.yml` is the first stage in the chain and the only one with interactive prompts. It runs against the host's temporary DHCP address, confirms the target hostname and site, applies the static IP, and hardens SSH — every later stage in the chain then runs unattended.

### Before You Run

Confirm connectivity to the DHCP address first:

```bash
ansible@EXAANSCLD001:~> ansible -i 192.168.161.147, all -m ansible.windows.win_ping
```

### Run the Full Chain

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i 192.168.161.147, playbooks/windows_bootstrap/site.yml \
  -e target_hosts=192.168.161.147 --ask-vault-pass
```

### The Preflight Prompts

`00-preflight.yml`'s `vars_prompt` asks for six values, in this order:

```text
SSH Username to connect as [Administrator]:
Local Administrator password (blank if SSH key already deployed):
Domain join password (Domain Admin):
Target hostname (EXA[ROLE][SITE][NNN], e.g. EXADCSCLD001):
EXAWKSMCR002
Is this the FIRST domain controller being built for this site? (yes/no — no for all other host types) [no]:
Static IP to assign (leave blank if IP is already correct):
192.168.161.52
```

It then prints a pre-flight summary and pauses for confirmation before opening the SSH connection:

```text
── Pre-flight summary ───────────────────────────────────────────────
  Host target : 192.168.161.147
  SSH user    : Administrator
  Hostname    : EXAWKSMCR002
  Role        : WKS   First DC: no
  Site        : MCR — Manchester, United Kingdom
  Subnet      : 192.168.161.0/24   Gateway: 192.168.161.253
  Target IP   : 192.168.161.52
  DNS primary : 192.168.161.10
  DNS 2nd     : 192.168.139.8
  DNS reason  : site DC reachable
─────────────────────────────────────────────────────────────────────
Confirm (Enter to proceed, Ctrl+C → A to abort)
```

See `playbooks/windows_bootstrap/README.md`'s "00-preflight.yml — DNS decision" section for exactly how the DNS primary/secondary values are decided.

### What Happens After Preflight

Every stage from `15-locale-timezone.yml` onward runs unattended (no further prompts), in the order listed in [Project Layout](#project-layout) above — locale/timezone, registry hardening, telemetry suppression, Chocolatey, guest tools, packages, RSAT, PSWindowsUpdate, binaries/fonts, wallpaper, hibernation policy, OpenSSH, RDP, SAC/EMS (server only), PS7 setup, domain join, and finally the summary + reboot in `85-finish.yml`. (`10-rename.yml` used to sit between preflight and this unattended run, but it had its own independent hostname prompt — so this "unattended from here" claim was already one stage off even before 2026-07-14, when `10-rename.yml` was removed from the chain entirely; `00-preflight.yml`'s own Phase G now does the rename, using the answer already given up front.):

```text
══════════════════════════════════════════════════════════
 Bootstrap complete: EXAWKSMCR002
══════════════════════════════════════════════════════════
 SSH   : ssh Administrator@192.168.161.52 (port 22)
 RDP   : 192.168.161.52:3389
 SAC   : N/A (not a server OS)
 Domain: jukebox.internal / OU: OU=Workstations,OU=MCR,DC=jukebox,DC=internal
 Site  : MCR
 Arch  : x86_64
 Hyper : VMware
══════════════════════════════════════════════════════════
```

### After Bootstrap

Add the host to the appropriate `configs/inventory/<site>.ini` file with its permanent hostname and static IP, so future targeted runs (registry updates, package changes, etc.) can address it by name.

---

## Running Individual Playbooks

Each numbered playbook is independent and can be run on its own — this is the normal workflow for an already-bootstrapped host that needs a specific change applied, or for re-running a single stage of a fresh bootstrap that failed partway through.

### Registry hardening only

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i configs/inventory playbooks/windows_bootstrap/playbooks/20-registry.yml \
  -e target=EXAWKSMCR001 --ask-vault-pass
```

Expected output:

```text
PLAY [Windows — Registry hardening] *******************************************

TASK [Apply common registry keys]
changed: [EXAWKSMCR001] => (item=EnableLUA)
changed: [EXAWKSMCR001] => (item=ConsentPromptBehaviorAdmin)
changed: [EXAWKSMCR001] => (item=InactivityTimeoutSecs)
ok: [EXAWKSMCR001] => (item=fDenyTSConnections)       ← already correct, no change
ok: [EXAWKSMCR001] => (item=UserAuthentication)
changed: [EXAWKSMCR001] => (item=SMB1)
...

PLAY RECAP *********************************************************************
EXAWKSMCR001  : ok=4  changed=2  unreachable=0  failed=0
```

`ok` means the value was already correct — Ansible checked and made no change. `changed` means it was updated. This idempotency is the key difference from a shell script — you can re-run safely at any time.

### Wallpaper refresh on all desktops

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i configs/inventory playbooks/windows_bootstrap/playbooks/60-wallpaper.yml \
  -e target=windows_desktop --ask-vault-pass
```

### Upgrade all Chocolatey packages on a single host

The upgrade task is tagged `choco_upgrade` and marked `never` — it does not run in a normal playbook run. Call it explicitly:

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i configs/inventory playbooks/windows_bootstrap/playbooks/40-choco-packages.yml \
  -e target=EXAWKSMCR001 --tags choco_upgrade --ask-vault-pass
```

### Domain join only (host already renamed and in inventory)

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i configs/inventory playbooks/windows_bootstrap/playbooks/80-domainjoin.yml \
  -e target=EXADCSMCR001 --ask-vault-pass
```

Prompts once for a DNS override (only used if the domain can't already be resolved), then checks whether the host is already joined, skips cleanly for `is_first_dc` builds (nothing to join — the domain doesn't exist yet), and otherwise joins using the OU derived from `domain_ou_role` (group_vars) + the host's parsed site.

```text
PLAY [Windows — Domain join] ***************************************************

TASK [Include hostname facts]
ok: [EXADCSMCR001]

TASK [Check if already domain-joined]
ok: [EXADCSMCR001]

TASK [Build target OU path]
ok: [EXADCSMCR001]
  → OU=Servers,OU=MCR,DC=jukebox,DC=internal

TASK [Join domain]
changed: [EXADCSMCR001]

TASK [Reboot after domain join]
[rebooting... waiting up to 600s]
ok: [EXADCSMCR001]

PLAY RECAP *********************************************************************
EXADCSMCR001  : ok=5  changed=2  unreachable=0  failed=0
```

---

## Dry Run (Check Mode)

Ansible's `--check` flag runs the playbook in read-only mode — it connects to the host, evaluates every task, and reports what it *would* change, without actually changing anything. Equivalent to Salt's `test=True` or Puppet's `--noop`.

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i configs/inventory playbooks/windows_bootstrap/playbooks/20-registry.yml \
  -e target=EXAWKSMCR001 --check --ask-vault-pass
```

Output shows `changed` for tasks that would make changes, and `ok` for tasks already in the desired state — identical to a real run except nothing is written. Useful before touching production hosts.

> **Note:** Some tasks cannot meaningfully dry-run — `win_shell` commands report `changed` in check mode even if they would actually be a no-op. Tasks that reboot the host are skipped entirely in check mode.

Add `--diff` to also show the before/after diff for registry and file changes:

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i configs/inventory playbooks/windows_bootstrap/playbooks/20-registry.yml \
  -e target=EXAWKSMCR001 --check --diff --ask-vault-pass
```

---

## Variable Precedence

Ansible resolves variables in a strict precedence order — later sources win. The order relevant to this playbook set, from lowest to highest priority:

| Source | Example |
|--------|---------|
| `group_vars/all/vars.yml` | `exa_domain`, `exa_ansible_pub_key`, `exa_choco_source` |
| `group_vars/windows/vars.yml` | `registry_common`, `binaries_common` |
| `group_vars/windows_server/vars.yml` | Server-role additions |
| `group_vars/windows_desktop/vars.yml` | `exa_deadvertise_enabled: true`, desktop packages |
| `group_vars/windows_laptop/vars.yml` | `exa_hibernation_enabled: true`, laptop packages |
| `host_vars/<hostname>.yml` | Per-host overrides (not currently used — add as needed) |
| `-e` extra vars at runtime | Highest priority — overrides everything |

**Important caveat specific to this chain:** the numbered `windows_bootstrap` playbooks run against a bare IP with no inventory group membership (see [Inventory](#inventory) above), so `group_vars/windows*/` do **not** apply to them at all during the initial bootstrap run — each stage that needs a package list or similar keeps it self-contained in its own `vars:` block instead (see `40-choco-packages.yml`'s design note). `group_vars/windows*/` become relevant once the host is added to inventory and other playbooks are run against it afterward.

---

## Handlers

Handlers in Ansible are tasks that run at the end of a play, but only if they were notified by another task that made a change. They are conceptually the same as Salt reactors or Puppet notify/subscribe — deferred actions triggered by state changes.

Available handlers (defined in `playbooks/windows_bootstrap/handlers/main.yml`):

| Handler | Triggered when |
|---------|---------------|
| `reboot host` | Rename completes, domain join completes |
| `restart winrm` | WinRM config changed (fallback-connectivity hosts only) |
| `restart sshd` | SSH key written, DefaultShell changed, sshd installed |
| `restart rdp` | RDP registry key changed |
| `restart spooler` | Print spooler configuration changed |
| `refresh group policy` | Domain join completes |
| `apply wallpaper` | Wallpaper file deployed |

Handlers only fire once per play, regardless of how many tasks notify them. If three tasks all notify `restart sshd`, sshd restarts once at the end — not three times.

Force handlers to fire immediately rather than at end-of-play:

```yaml
- name: Flush handlers now
  meta: flush_handlers
```

This is used in the wallpaper playbook to apply the wallpaper change immediately rather than waiting until the end of the run.

---

## Tags

Tags let you run a subset of tasks without running everything. In `site.yml` each numbered stage has its own unique tag — there is no shared "early stages" grouping, so `--tags bootstrap` only ever matches `00-preflight.yml` specifically, not "just the essentials".

Run only `00-preflight.yml`:

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i configs/inventory playbooks/windows_bootstrap/site.yml \
  -e target=EXAWKSMCR001 --tags bootstrap --ask-vault-pass
```

Run only the registry stage:

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i configs/inventory playbooks/windows_bootstrap/site.yml \
  -e target=EXAWKSMCR001 --tags registry --ask-vault-pass
```

List all tags in the chain without running it:

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i configs/inventory playbooks/windows_bootstrap/site.yml --list-tags
```

The special tag `never` means a task is skipped by default and only runs when explicitly called by name. The `choco_upgrade` task uses this — it will never run in a normal playbook execution.

---

## Ad-Hoc Commands

For one-off tasks that do not warrant a playbook, Ansible's ad-hoc mode (`ansible` rather than `ansible-playbook`) runs a single module directly.

```bash
# Ping all hosts in inventory
ansible@EXAANSCLD001:~> ansible -i configs/inventory all -m ansible.windows.win_ping

# Run a PowerShell command on a single host
ansible@EXAANSCLD001:~> ansible -i configs/inventory EXAWKSMCR001 \
  -m ansible.windows.win_shell -a "Get-Date"

# Check disk space on all desktops
ansible@EXAANSCLD001:~> ansible -i configs/inventory windows_desktop \
  -m ansible.windows.win_shell \
  -a "Get-PSDrive C | Select-Object Used,Free"

# Copy a file to a host
ansible@EXAANSCLD001:~> ansible -i configs/inventory EXAWKSMCR001 \
  -m ansible.windows.win_copy \
  -a "src=/home/ansible/tool.exe dest=C:\\Windows\\tool.exe"

# Restart a service
ansible@EXAANSCLD001:~> ansible -i configs/inventory EXASRVMCR001 \
  -m ansible.windows.win_service \
  -a "name=spooler state=restarted"
```

---

## Troubleshooting

### Verbose Output

Add `-v`, `-vv`, or `-vvv` to any command. `-vvv` shows the full SSH/WinRM handshake, the exact module arguments, and the raw return values from the host. Useful for diagnosing connectivity issues or unexpected task behaviour.

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i configs/inventory playbooks/windows_bootstrap/playbooks/20-registry.yml \
  -e target=EXAWKSMCR001 -vvv --ask-vault-pass
```

### A Task Says `changed` Every Run

The task is not idempotent — it cannot determine whether the change is needed before making it. `win_shell` tasks are the usual culprit since Ansible has no way to know what a shell command does. The fix is `changed_when: false` (always report no change) or a conditional `register` + `when` pattern. Raise it and the task can be improved.

### A Task Fails Halfway Through

Ansible stops at the first failure by default. Fix the cause, then re-run the whole chain — already-completed tasks report `ok` (idempotent) and the run continues correctly regardless. Use `--start-at-task "task name"` to skip straight to a specific point if needed:

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i configs/inventory playbooks/windows_bootstrap/site.yml \
  -e target=EXAWKSMCR001 \
  --start-at-task "[Preflight] Check chocolatey.org reachable" \
  --ask-vault-pass
```

### Host Unreachable After Reboot

`win_reboot` tasks (rename, domain join, `85-finish.yml`'s final reboot) wait up to 600 seconds by default for the host to come back. If the host takes longer (slow hardware, a large Windows update applying), increase the timeout in the relevant task, or simply re-run the playbook — completed stages are idempotent and will pass quickly.

### Vault Decryption Error

```text
ERROR! Decryption failed (no vault secrets would decrypt)
```

Wrong vault password, or the file was not encrypted with `ansible-vault`. Verify with:

```bash
ansible@EXAANSCLD001:~> head -1 group_vars/all/vault.yml
$ANSIBLE_VAULT;1.1;AES256
```

If the first line is not `$ANSIBLE_VAULT`, the file is not encrypted. Encrypt it:

```bash
ansible@EXAANSCLD001:~> ansible-vault encrypt group_vars/all/vault.yml
```

---

## Open Items

| Item | Detail |
|------|--------|
| `host_vars/` | Not currently used. Create `host_vars/<hostname>.yml` for per-host overrides as needed (e.g. a specific host that needs a different wallpaper or package set) |
| Chocolatey mirror | Currently using `community.chocolatey.org`. For sites with restricted internet, set up an internal Nexus/ProGet instance and update `exa_choco_source` in `group_vars/all/vars.yml` |
| Ansible pub key rotation | `exa_ansible_pub_key` in `group_vars/all/vars.yml` is hardcoded. If `EXAANSCLD001` is rebuilt, update this value and re-run `75-openssh.yml` across all managed hosts |
| Dynamic inventory | Currently static `.ini` files per site. A dynamic inventory script reading `benarbejde/sites.csv`/`devices.csv` or querying Active Directory would reduce maintenance overhead as the estate grows |
| Windows Update | `PSWindowsUpdate` is installed (`48-pswindowsupdate.yml`) but no update policy playbook exists yet. Define an update schedule |
| `tasks/ou_selection.yml` | Currently unused/parked — was the interactive LDAP OU picker for hosts not yet in inventory, orphaned when `05-bootstrap.yml` (its only caller) was retired. May be reinstated later |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-20 | Initial document |
| 2026-07-09 | Full rewrite — the document had drifted badly from reality: it referenced a `00-bootstrap.yml` monolith that hadn't existed under that name for some time, described an interactive "Stage 3/Stage 4" hostname-confirm and LDAP OU-selection flow that no longer exists in the current chain, used `inventory/<site>.ini`/bare `playbooks/*.yml` paths instead of the real `configs/inventory`/`playbooks/windows_bootstrap/playbooks/*.yml` paths, and was missing more than half the current numbered stages (`15-`, `22-`, `35-`, `45-`, `48-`, `77-`, `78-`, `79-`, `85-`) entirely. Rewritten against the actual current `00-preflight.yml` prompts, `80-domainjoin.yml` behaviour, and `85-finish.yml` summary output. |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
