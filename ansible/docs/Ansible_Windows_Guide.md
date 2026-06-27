# Example Music Limited — Ansible Windows Playbook Guide

> **Classification:** Internal — Infrastructure
> **Forest:** `jukebox.internal`
> **Domains:** `example.net` · `example.org` · `example.com`
> **Provisioning network:** `192.168.139.0/24`
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Purpose

This document covers the day-to-day operation of the Example Music Ansible Windows playbook set. It is aimed at engineers who have infrastructure experience but may be unfamiliar with Ansible's specific idioms — particularly around inventory, variable precedence, vaults, and how Windows connectivity differs from Linux.

If you have used Salt or Puppet before, the mental model maps reasonably well: inventory ≈ Salt targeting / Puppet node classifier, group_vars ≈ Salt grains/pillars / Puppet Hiera, vault ≈ Salt pillar encryption / Puppet eyaml, handlers ≈ Salt reactors / Puppet notify/subscribe.

---

## Quick Reference

| Task | Command |
|------|---------|
| Full bootstrap (new host) | `ansible-playbook -i inventory/<site>.ini site.yml -e target=<host> --ask-vault-pass` |
| Bootstrap only | `ansible-playbook -i inventory/<site>.ini site.yml -e target=<host> --tags bootstrap --ask-vault-pass` |
| Skip bootstrap, run everything else | `ansible-playbook -i inventory/<site>.ini site.yml -e target=<host> --skip-tags bootstrap --ask-vault-pass` |
| Single playbook | `ansible-playbook -i inventory/<site>.ini playbooks/20-registry.yml -e target=<host> --ask-vault-pass` |
| Single tag across all playbooks | `ansible-playbook -i inventory/<site>.ini site.yml -e target=<host> --tags registry --ask-vault-pass` |
| Dry run | `ansible-playbook -i inventory/<site>.ini site.yml -e target=<host> --check --ask-vault-pass` |
| Ad-hoc connectivity test | `ansible -i inventory/<site>.ini <host> -m ansible.windows.win_ping` |
| Domain join only | `ansible-playbook -i inventory/<site>.ini playbooks/80-domainjoin.yml -e target=<host> --ask-vault-pass` |

---

## Prerequisites

### On EXAANSCLD001

Python packages:

```bash
ansible@EXAANSCLD001:~> pip3 install pywinrm --break-system-packages
```

Required Ansible collections:

```bash
ansible@EXAANSCLD001:~> ansible-galaxy collection install \
  ansible.windows \
  community.windows \
  chocolatey.chocolatey \
  microsoft.ad
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

---

## Project Layout

```text
ansible/
├── ansible.cfg                         ← project config (SSH settings, collection paths)
├── site.yml                            ← entry point — runs everything in order
│
├── inventory/
│   ├── cld.ini                         ← CLD site hosts
│   ├── mcr.ini                         ← MCR site hosts
│   └── <site>.ini                      ← one file per site
│
├── group_vars/
│   ├── all/
│   │   ├── vars.yml                    ← variables for every host (URLs, domain, SSH key)
│   │   └── vault.yml                   ← encrypted secrets (passwords)
│   ├── windows/
│   │   └── vars.yml                    ← all Windows hosts (connection, common packages)
│   ├── windows_server/
│   │   └── vars.yml                    ← SRV/DCS hosts (no deadvertise, server packages)
│   ├── windows_desktop/
│   │   └── vars.yml                    ← WKS hosts (deadvertise on, desktop packages)
│   └── windows_laptop/
│       └── vars.yml                    ← LAP/SUR hosts (hibernation on, laptop packages)
│
├── handlers/
│   └── main.yml                        ← reboot, restart sshd/winrm/rdp, apply wallpaper
│
├── tasks/
│   ├── arch_facts.yml                  ← CPU arch detection (AMD64/ARM64 → x86_64/arm64)
│   ├── hostname_facts.yml              ← EXA[ROLE][SITE][NNN] hostname parsing
│   ├── preflight.yml                   ← Stage 0b — DC/DNS/URL reachability checks
│   ├── site_detection.yml              ← Stage 1+2 — hypervisor + IP-to-site mapping
│   ├── ou_selection.yml                ← Stage 4 — LDAP OU query + interactive selection
│   ├── guest_tools.yml                 ← Stage 12 — VMware/KVM tools
│   └── ps7_setup.yml                   ← Stages 19–22b — PS7 modules, fonts, terminals
│
└── playbooks/
    ├── 00-bootstrap.yml                ← Full PostOOBE (replaces Join-DomainAndBootstrap.ps1)
    ├── 10-rename.yml                   ← Hostname rename
    ├── 20-registry.yml                 ← Registry hardening
    ├── 25-deadvertise.yml              ← Advertising + telemetry suppression
    ├── 30-chocolatey.yml               ← Chocolatey installation
    ├── 40-choco-packages.yml           ← Package deployment
    ├── 50-binaries.yml                 ← Arch-aware binary + font deployment
    ├── 60-wallpaper.yml                ← Corporate wallpaper
    ├── 70-hibernation.yml              ← Hibernation policy by host type
    ├── 75-openssh.yml                  ← OpenSSH + Ansible key
    └── 80-domainjoin.yml               ← Domain join
```

---

## Inventory

### Structure

Ansible inventory maps hosts to groups. The Windows playbooks use four groups, organised as a hierarchy:

```ini
# inventory/mcr.ini

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

### Adding a New Host

1. Add the host to the appropriate site inventory file under the correct group.
2. Use the DHCP address initially (before rename and domain join).
3. After the bootstrap completes and the host has its permanent name and IP, update the inventory entry.

```ini
# Before bootstrap — DHCP address, temporary
[windows_desktop]
WINPEBUILD  ansible_host=192.168.161.147

# After bootstrap — permanent name and static/reserved IP
[windows_desktop]
EXAWKSMCR002  ansible_host=192.168.161.52
```

### Targeting Specific Hosts

Every playbook accepts a `target` variable that limits execution to a single host or group:

```bash
# Single host
ansible-playbook -i inventory/mcr.ini playbooks/20-registry.yml -e target=EXAWKSMCR001

# All hosts in a group
ansible-playbook -i inventory/mcr.ini playbooks/20-registry.yml -e target=windows_desktop

# All hosts in the inventory (default if target is not set)
ansible-playbook -i inventory/mcr.ini playbooks/20-registry.yml
```

---

## Credentials and Vault

### How the Vault Works

Ansible Vault is symmetric encryption (AES-256) applied to a YAML file. The vault file lives alongside other `group_vars` files and is decrypted in memory at runtime — nothing is written to disk in plaintext. It is conceptually the same as Salt's encrypted pillar or Puppet's eyaml.

The vault file is at `group_vars/all/vault.yml`. When encrypted it looks like:

```text
$ANSIBLE_VAULT;1.1;AES256
61383866623937623263663139343834346265646634653561323934383933373032313634356633
...
```

Variables defined in the vault are referenced in playbooks and `vars.yml` files exactly like any other variable — Ansible handles the decryption transparently.

### Variables in the Vault

```yaml
# group_vars/all/vault.yml (shown decrypted — encrypt this file, never commit plaintext)
vault_local_admin_password:   "stored-in-password-manager"
vault_domain_join_password:   "stored-in-password-manager"
vault_winrm_password:         "stored-in-password-manager"
```

The domain join user (`JUKEBOX\Administrator`) is in `group_vars/all/vars.yml` as plain text — only the password is in the vault.

### Setting Up the Vault

Create and populate the vault:

```bash
ansible@EXAANSCLD001:~> ansible-vault create group_vars/all/vault.yml
New Vault password: 
Confirm New Vault password: 
```

This drops you into `$EDITOR` (vi by default — set `EDITOR=nano` if preferred). Write the vault variables, save, and exit. The file is encrypted on disk immediately.

Edit an existing vault:

```bash
ansible@EXAANSCLD001:~> ansible-vault edit group_vars/all/vault.yml
Vault password:
```

View without editing:

```bash
ansible@EXAANSCLD001:~> ansible-vault view group_vars/all/vault.yml
```

Re-encrypt with a new password:

```bash
ansible@EXAANSCLD001:~> ansible-vault rekey group_vars/all/vault.yml
```

### Providing the Vault Password at Runtime

**Option 1 — interactive prompt (safest for shared machines):**

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini site.yml \
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
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini playbooks/80-domainjoin.yml \
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

The playbooks default to SSH (installed by `UNATTEND.CMD` and configured by bootstrap Stage 16). WinRM is available as a fallback and is commented out in `group_vars/windows/vars.yml`.

SSH is strongly preferred — it uses the same key-based auth as Linux, it is firewall-friendly (single port 22), and it does not require the certificate management overhead of WinRM HTTPS. The only reason to fall back to WinRM is if SSH is unavailable on an existing host that was not built via the standard PXE process.

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
ansible@EXAANSCLD001:~> ansible -i inventory/mcr.ini EXAWKSMCR001 -m ansible.windows.win_ping
```

Expected output:

```text
EXAWKSMCR001 | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

If it fails:

```bash
# Add -vvv for verbose output — shows the exact SSH/WinRM handshake
ansible@EXAANSCLD001:~> ansible -i inventory/mcr.ini EXAWKSMCR001 -m ansible.windows.win_ping -vvv
```

Common failure reasons and fixes:

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Connection refused` on port 22 | sshd not running | RDP in, run `Start-Service sshd` |
| `Authentication failed` | Wrong user or key not deployed | Check `exa_ansible_pub_key` in vault, re-run `75-openssh.yml` |
| `Timeout` | Host unreachable / firewall | Check routing, check firewall rule on host |
| `WinRM connection error` | WinRM not configured | Bootstrap Stage 16 not yet run |

---

## Running the Bootstrap (New Host)

The bootstrap playbook (`00-bootstrap.yml`) is the Ansible equivalent of `Join-DomainAndBootstrap.ps1`. It runs once on a freshly PXE-built host and handles all 23 stages. It is safe to re-run if interrupted — every task is idempotent.

### Before You Run

The host must be in inventory under its current DHCP address:

```ini
# inventory/mcr.ini
[windows_desktop]
WINPEBUILD  ansible_host=192.168.161.147
```

Verify connectivity:

```bash
ansible@EXAANSCLD001:~> ansible -i inventory/mcr.ini WINPEBUILD -m ansible.windows.win_ping
```

### Run the Bootstrap

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini playbooks/00-bootstrap.yml \
  -e target=WINPEBUILD --ask-vault-pass
```

### What You Will See

The bootstrap has two interactive points where Ansible pauses and waits for input. Everything else runs without interaction.

**Interactive point 1 — Stage 3, hostname confirmation:**

```text
── Stage 3 — Hostname ────────────────────────────────────────────────────

TASK [Stage 3 — Prompt operator to confirm or override hostname]
[pause]
Current hostname : WINPEBUILD
Detected site    : MCR (from IP 192.168.161.147)
Hostname site    : N/A (parsed from current name — no EXA prefix)
Role             : N/A
OS type          : Workstation
Chassis          : Desktop/Tower

Press Enter to keep 'WINPEBUILD'
Or type a new hostname (EXA[ROLE][SITE][NNN]) and press Enter:
EXAWKSMCR002
```

**Interactive point 2 — Stage 4, OU selection:**

```text
── Stage 4 — OU selection ────────────────────────────────────────────────

TASK [Stage 4 — Query OUs from DC at .10]
ok: [WINPEBUILD]

TASK [Stage 4 — Display OU list]
ok: [WINPEBUILD] => {
    "msg": [
        "1\tOU=Workstations,OU=MCR,DC=jukebox,DC=internal",
        "2\tOU=Laptops,OU=MCR,DC=jukebox,DC=internal",
        "3\tOU=Servers,OU=MCR,DC=jukebox,DC=internal",
        "4\tOU=DomainControllers,OU=MCR,DC=jukebox,DC=internal",
        "5\tOU=MCR,DC=jukebox,DC=internal",
        ...
    ]
}

[pause]
── OU Selection ──────────────────────────────────────────────────────────
OUs listed above. Enter the NUMBER of the target OU for this host.

Suggested for role WKS:
  Workstations → find OU=Workstations,OU=MCR,...

Enter OU number: 1
```

After that it runs unattended through all remaining stages. Abbreviated example output:

```text
── Stage 5 — Rename and domain join ──
TASK [Stage 5 — Rename computer]
changed: [WINPEBUILD]

TASK [Stage 5 — Reboot after rename]
[rebooting... waiting up to 600s]
ok: [WINPEBUILD]  ← reconnected as EXAWKSMCR002

TASK [Stage 5 — Join domain]
changed: [EXAWKSMCR002]

TASK [Stage 5 — Reboot after domain join]
[rebooting... waiting up to 600s]
ok: [EXAWKSMCR002]

── Stage 6 — Power and pagefile ──
changed: [EXAWKSMCR002]  ← powercfg /hibernate off

── Stage 7 — Locale and timezone ──
changed: [EXAWKSMCR002]  ← GMT Standard Time, en-GB

── Stage 8 — Screen lock ──
changed: [EXAWKSMCR002] x4  ← screensaver, timeout, monitor power

── Stage 9 — Corporate wallpaper ──
changed: [EXAWKSMCR002]  ← downloaded + PersonalizationCSP set
RUNNING HANDLER [apply wallpaper]
changed: [EXAWKSMCR002]  ← SystemParametersInfo called

── Stage 10 — Dark mode ──
changed: [EXAWKSMCR002] x3  ← HKLM + Default user hive

── Stage 11 — Chocolatey ──
changed: [EXAWKSMCR002]  ← installed from community.chocolatey.org

── Stage 12 — Guest tools ──
ok: [EXAWKSMCR002]  ← VMware Tools already present (installed by UNATTEND.CMD)

── Stage 13 — RustDesk ──
changed: [EXAWKSMCR002]  ← installed from asset server

── Stage 14 — Baseline packages ──
changed: [EXAWKSMCR002]  ← winscp, putty, hyper, notepadplusplus, ...
changed: [EXAWKSMCR002]  ← firefox, windirstat, windows-terminal  (desktop extras)

── Stage 15 — RSAT ──
changed: [EXAWKSMCR002]  ← AD, DNS, GPMC capabilities installed

── Stage 16 — OpenSSH and Ansible key ──
ok: [EXAWKSMCR002]   ← sshd already running (UNATTEND.CMD)
changed: [EXAWKSMCR002]  ← administrators_authorized_keys written
changed: [EXAWKSMCR002]  ← ACLs set (SYSTEM:F, Administrators:F, no inheritance)
changed: [EXAWKSMCR002]  ← DefaultShell → pwsh.exe (PS7 now installed)
RUNNING HANDLER [restart sshd]
changed: [EXAWKSMCR002]

── Stage 17 — RDP ──
ok: [EXAWKSMCR002]  ← already enabled, NLA confirmed

── Stage 17b — SAC/EMS serial console ──
ok: [EXAWKSMCR002]  ← Workstation OS — skipping SAC/EMS.

── Stage 18 — PSWindowsUpdate ──
changed: [EXAWKSMCR002]  ← installed from PSGallery

── Stages 19–22b — PS7 setup, fonts, terminal config ──
changed: [EXAWKSMCR002]  ← 7 PS7 modules installed (AllUsers)
changed: [EXAWKSMCR002]  ← 5 JetBrainsMono font files deployed + registered
changed: [EXAWKSMCR002]  ← PS7 AllUsersAllHosts profile written
changed: [EXAWKSMCR002]  ← .hyper.js written
changed: [EXAWKSMCR002]  ← Windows Terminal settings.json written (2 paths)

── Stage 23 — Finish ──
ok: [EXAWKSMCR002] => {
    "msg": [
        "══════════════════════════════════════════════════════════",
        " Bootstrap complete: EXAWKSMCR002",
        "══════════════════════════════════════════════════════════",
        " SSH   : ssh Administrator@192.168.161.147 (port 22)",
        " RDP   : 192.168.161.147:3389",
        " SAC   : N/A (not a server OS)",
        " Domain: jukebox.internal / OU: OU=Workstations,OU=MCR,DC=jukebox,DC=internal",
        " Site  : MCR",
        " Arch  : x86_64",
        " Hyper : VMware",
        "══════════════════════════════════════════════════════════",
        " NOTE: Run playbook 70-hibernation.yml on LAP/SUR devices",
        " to re-enable hibernation (disabled unconditionally here).",
        "══════════════════════════════════════════════════════════"
    ]
}

TASK [Stage 23 — Final reboot]
[rebooting...]
ok: [EXAWKSMCR002]

PLAY RECAP *********************************************************************
EXAWKSMCR002  : ok=61  changed=34  unreachable=0  failed=0  skipped=4
```

### After Bootstrap

Update the inventory entry with the permanent hostname:

```ini
# inventory/mcr.ini
[windows_desktop]
EXAWKSMCR002  ansible_host=192.168.161.147
```

For a laptop or tablet (`LAP`, `SUR`), re-enable hibernation:

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini playbooks/70-hibernation.yml \
  -e target=EXALAPMCR001 --ask-vault-pass
```

---

## Skipping the Interactive OU Prompt

If you already know the OU — for example when deploying a batch of servers of the same type — pass it on the command line and Stage 4 skips the LDAP query entirely:

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini playbooks/00-bootstrap.yml \
  -e target=WINPEBUILD \
  -e bootstrap_ou_path="OU=Servers,OU=MCR,DC=jukebox,DC=internal" \
  --ask-vault-pass
```

---

## Running Individual Playbooks

Each playbook is independent and can be run on its own. This is the normal workflow for an already-bootstrapped host that needs a specific change applied.

### Registry hardening only

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini playbooks/20-registry.yml \
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

TASK [Ensure RDP service is running]
ok: [EXAWKSMCR001]

PLAY RECAP *********************************************************************
EXAWKSMCR001  : ok=4  changed=2  unreachable=0  failed=0
```

`ok` means the value was already correct — Ansible checked and made no change. `changed` means it was updated. This idempotency is the key difference from a shell script — you can re-run safely at any time.

### Wallpaper refresh on all desktops

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini playbooks/60-wallpaper.yml \
  -e target=windows_desktop --ask-vault-pass
```

### Upgrade all Chocolatey packages on a single host

The upgrade task is tagged `choco_upgrade` and marked `never` — it does not run in a normal playbook run. Call it explicitly:

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini playbooks/40-choco-packages.yml \
  -e target=EXAWKSMCR001 --tags choco_upgrade --ask-vault-pass
```

### Domain join only (host already renamed)

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini playbooks/80-domainjoin.yml \
  -e target=EXADCSMCR001 --ask-vault-pass
```

Expected output:

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
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini playbooks/20-registry.yml \
  -e target=EXAWKSMCR001 --check --ask-vault-pass
```

Output shows `changed` for tasks that would make changes, and `ok` for tasks already in the desired state — identical to a real run except nothing is written. Useful before touching production hosts.

> **Note:** Some tasks cannot meaningfully dry-run — `win_shell` commands report `changed` in check mode even if they would actually be a no-op. Tasks that reboot the host are skipped entirely in check mode.

Add `--diff` to also show the before/after diff for registry and file changes:

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini playbooks/20-registry.yml \
  -e target=EXAWKSMCR001 --check --diff --ask-vault-pass
```

---

## Variable Precedence

Ansible resolves variables in a strict precedence order — later sources win. The order relevant to this playbook set, from lowest to highest priority:

| Source | Example |
|--------|---------|
| `group_vars/all/vars.yml` | `exa_domain`, `exa_asset_base`, `exa_ansible_pub_key` |
| `group_vars/windows/vars.yml` | Connection settings, `choco_packages_common`, `registry_common` |
| `group_vars/windows_server/vars.yml` | `exa_hibernation_enabled: false`, server packages |
| `group_vars/windows_desktop/vars.yml` | `exa_deadvertise_enabled: true`, desktop packages |
| `group_vars/windows_laptop/vars.yml` | `exa_hibernation_enabled: true`, laptop packages |
| `host_vars/<hostname>.yml` | Per-host overrides (not currently used — add as needed) |
| `-e` extra vars at runtime | Highest priority — overrides everything |

Practical example: `exa_hibernation_enabled` is `false` in `windows_server` and `windows_desktop` but `true` in `windows_laptop`. The `70-hibernation.yml` playbook reads whichever value applies to the host it is running against — no `when: group_names contains ...` logic needed in the playbook itself. The variable does the work.

---

## Handlers

Handlers in Ansible are tasks that run at the end of a play, but only if they were notified by another task that made a change. They are conceptually the same as Salt reactors or Puppet notify/subscribe — deferred actions triggered by state changes.

Available handlers (defined in `handlers/main.yml`):

| Handler | Triggered when |
|---------|---------------|
| `reboot host` | Rename completes, domain join completes |
| `restart sshd` | SSH key written, DefaultShell changed, sshd installed |
| `restart rdp` | RDP registry key changed |
| `restart winrm` | WinRM config changed |
| `refresh group policy` | Domain join completes |
| `apply wallpaper` | Wallpaper file downloaded |

Handlers only fire once per play, regardless of how many tasks notify them. If three tasks all notify `restart sshd`, sshd restarts once at the end — not three times.

Force handlers to fire immediately rather than at end-of-play:

```yaml
- name: Flush handlers now
  meta: flush_handlers
```

This is used in the wallpaper playbook to apply the wallpaper change immediately via `SystemParametersInfo` rather than waiting until the end of the run.

---

## Tags

Tags let you run a subset of tasks across all playbooks without running everything. A tag can be applied to a single task, an entire playbook, or an `import_playbook` in `site.yml`.

Run only tasks tagged `registry`:

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini site.yml \
  -e target=EXAWKSMCR001 --tags registry --ask-vault-pass
```

Run everything except bootstrap:

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini site.yml \
  -e target=EXAWKSMCR001 --skip-tags bootstrap --ask-vault-pass
```

Run fonts only (subset of the binaries playbook):

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini playbooks/50-binaries.yml \
  -e target=EXAWKSMCR001 --tags fonts --ask-vault-pass
```

List all tags in a playbook without running it:

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini site.yml --list-tags
```

The special tag `never` means a task is skipped by default and only runs when explicitly called by name. The `choco_upgrade` task uses this — it will never run in a normal playbook execution.

---

## Ad-Hoc Commands

For one-off tasks that do not warrant a playbook, Ansible's ad-hoc mode (`ansible` rather than `ansible-playbook`) runs a single module directly.

```bash
# Ping all hosts in inventory
ansible@EXAANSCLD001:~> ansible -i inventory/mcr.ini all -m ansible.windows.win_ping

# Run a PowerShell command on a single host
ansible@EXAANSCLD001:~> ansible -i inventory/mcr.ini EXAWKSMCR001 \
  -m ansible.windows.win_shell -a "Get-Date"

# Check disk space on all desktops
ansible@EXAANSCLD001:~> ansible -i inventory/mcr.ini windows_desktop \
  -m ansible.windows.win_shell \
  -a "Get-PSDrive C | Select-Object Used,Free"

# Copy a file to a host
ansible@EXAANSCLD001:~> ansible -i inventory/mcr.ini EXAWKSMCR001 \
  -m ansible.windows.win_copy \
  -a "src=/home/ansible/tool.exe dest=C:\\Windows\\tool.exe"

# Restart a service
ansible@EXAANSCLD001:~> ansible -i inventory/mcr.ini EXASRVMCR001 \
  -m ansible.windows.win_service \
  -a "name=spooler state=restarted"
```

---

## Troubleshooting

### Verbose Output

Add `-v`, `-vv`, or `-vvv` to any command. `-vvv` shows the full SSH/WinRM handshake, the exact module arguments, and the raw return values from the host. Useful for diagnosing connectivity issues or unexpected task behaviour.

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini playbooks/20-registry.yml \
  -e target=EXAWKSMCR001 -vvv --ask-vault-pass
```

### A Task Says `changed` Every Run

The task is not idempotent — it cannot determine whether the change is needed before making it. `win_shell` tasks are the usual culprit since Ansible has no way to know what a shell command does. The fix is `changed_when: false` (always report no change) or a conditional `register` + `when` pattern. Raise it and the task can be improved.

### A Task Fails Halfway Through

Ansible stops at the first failure by default. Fix the cause, then re-run — already-completed tasks will report `ok` (idempotent) and the run will continue from where it effectively left off. Use `--start-at-task "task name"` to skip to a specific point if needed:

```bash
ansible@EXAANSCLD001:~> ansible-playbook -i inventory/mcr.ini playbooks/00-bootstrap.yml \
  -e target=EXAWKSMCR001 \
  --start-at-task "[Stage 14] Install common baseline packages" \
  --ask-vault-pass
```

### Host Unreachable After Reboot

The bootstrap playbook uses `win_reboot` which waits up to 600 seconds for the host to come back. If the host takes longer than that (slow hardware, large Windows update applying), increase the timeout:

```yaml
ansible.windows.win_reboot:
  reboot_timeout: 1200
```

Or simply re-run the playbook — the completed stages are idempotent and will pass quickly.

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
| Dynamic inventory | Currently static `.ini` files per site. A dynamic inventory script reading `sites_extended.csv` or querying Active Directory would reduce maintenance overhead as the estate grows |
| Windows Update | `PSWindowsUpdate` is installed (Stage 18) but no update policy playbook exists yet. Define an update schedule and write `85-updates.yml` |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-20 | Initial document |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
