# Example Music Limited — Beginner's Guide to Ansible

> **Classification:** Internal — Infrastructure
> **Forest:** `jukebox.internal`
> **Domains:** `example.net` · `example.org` · `example.com`
> **Provisioning network:** `192.168.139.0/24`
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Purpose

This document provides a practical introduction to Ansible as it is actually used at
Example Music. It started as a write-up of one real troubleshooting/learning session on
`EXADNSVRK001` (the sudo/become/reboot walkthrough further down still uses that session's
real captured output — new administrators are encouraged to compare their own output
against it). It has since grown to cover the repository's actual architecture: how the
inventory is organised, where `group_vars`/`host_vars` have to live and why, how a
brand-new host gets correct variables before it's even in the inventory file, and what
"idempotent" means in practice rather than just in the textbook definition.

If you only read one thing before touching this repo, read
**[Inventory and group_vars — the part that isn't optional](#inventory-and-group_vars--the-part-that-isnt-optional)**.
It explains a mistake that is easy to make, silent when made, and was made once already
in this repo's own history.

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

At Example Music, Ansible is used as the primary Linux configuration and deployment platform, and (via `windows_bootstrap`/`windows_dc`/`windows_adschema`) the primary Windows one too.

---

## Example Environment

The following examples were captured from:

```text
Hostname : EXADNSVRK001
Address  : 192.168.139.8
Role     : DNS Server
Domain   : jukebox.internal
```

---

## How This Repository Is Organised

Everything Ansible needs to run — inventory, generated group variables, and (for the
Windows AD demo data) pre-generated JSON — is produced from a small set of hand-maintained
files in **`benarbejde/`** (Danish: roughly "the legwork done in advance"), at the repo
root, outside `ansible/` entirely:

| File | What it is |
|------|------------|
| `sites.csv` | One row per site — subnet, gateway, city, country, entity, timezone |
| `devices.csv` | **Exceptions only** — a device row is only needed if it doesn't fit the standard addressing convention |
| `address_policy.json` | The standard addressing convention (which host-role gets which octet offset) as data |
| `begyndelse.json` | Well-known service addresses (DNS, Ansible control node, PBX, Rudder…) for consumers that run *before* Ansible exists on a box (`bindme.sh`, `ansibleme.sh`) |
| `ad_forest.json` | AD forest identity — domain FQDN, NetBIOS name, DNS forwarders — single source for what used to be three separately hardcoded variables. `domain_fqdn` is genuinely changeable — every consumer derives from it rather than hardcoding `jukebox.internal` — one edit here (e.g. to an illustrative `disco.internal`, not a real value) is all a rename would take, no other file should need touching |
| `generate_inventory.py` | Reads all of the above, writes `ansible/configs/inventory/*.ini` (one file per site) plus `group_vars/all/site_services.yml` |

The rule that makes this work: **nothing downstream hardcodes a fact that one of these
files already states.** If you need to know a site's subnet, a device's IP, or the AD
domain name, there is exactly one file that says so, and every consumer — Ansible
playbooks, the pre-Ansible bootstrap shell scripts, `bind9-dns.yml`'s DNS zone generation —
reads the same one. `.githooks/pre-commit` auto-copies the subset of `benarbejde/` that the
PXE preseed web server needs into `bootstrap/web/proxmox/` on every commit, so that copy can
never drift from the source of truth by hand-editing.

### A worked example: `jukebox.example.tdf`

`benarbejde/jukebox.example.tdf` and `benarbejde/parse_tdf.py` are worth knowing about
specifically because they show where the "single source of truth" boundary is drawn. The
TDF file is old demo data (users, groups, computers, in a legacy PowerShell-literal format);
`parse_tdf.py` is a hand-run, offline script that turns it into `ad_users.json`/
`ad_groups.json`/`ad_computers.json`. **No playbook or task reads the TDF file or invokes
this script, at any point.** Only the JSON it produces — deployed to `/etc/example-music/`
— is a real Ansible dependency (read by `windows_adschema/playbooks/{20,30,40}-*.yml`). The
script's own header calls itself out as a "LEGACY / DEFUNCT TOOL" for exactly this reason:
it's useful for regenerating the demo data by hand, but it is deliberately *not* wired into
anything Ansible runs, so a change to that old PowerShell-literal format can never silently
break a live playbook run.

---

## Inventory and `group_vars` — the part that isn't optional

If you've used Puppet, you might look for Ansible's equivalent of `modules.pp` — a config
file that tells the tool "here's where to look for things." Ansible doesn't have a separate
one. **The inventory path you pass with `-i` *is* the search path.**

Specifically: `group_vars/` and `host_vars/` are auto-loaded by a built-in vars plugin
(`ansible.builtin.host_group_vars`). That plugin's own documentation says it "only applies
to inventory sources that are existing paths" — in practice this means `group_vars/` and
`host_vars/` are only discovered when they live **inside** the directory you actually pass
to `-i` (or that `ansible.cfg`'s `inventory =` points at). A directory sitting next to it —
even one directory up, even with an identical name — is not searched. There's no separate
"add this to the search path" setting to reach for; moving the inventory *is* the only lever.

This repo learned that the hard way. `group_vars/` used to sit at `ansible/group_vars/`,
sibling to `ansible/configs/inventory/` (the real, loaded inventory path). It looked correct
— same repo, one directory over — but it silently never applied to a single numbered
playbook, because it was never *inside* the loaded path. The result was a set of
`undefined variable` crashes deep into the `windows_dc` chain that only reproduced on a
fresh host, because a host that had already picked up variables from an earlier working
run kept them cached in its facts. Confirming this took an isolated test harness (a
throwaway inventory + a marker `group_vars/testgroup/vars.yml` file, moved between a
sibling location and a nested one, with `ansible-playbook -i <path> --limit testgroup`
run after each move) rather than reading documentation and guessing — the plugin's actual
behaviour was the only thing that settled it. This is a general lesson worth keeping,
not just an anecdote: when infrastructure behaviour is surprising, build the smallest
possible reproduction before proposing a fix.

The fix was to physically move the directory: `group_vars/` and `host_vars/` now live at
`ansible/configs/inventory/group_vars/` and `.../host_vars/` — genuinely inside the
`inventory =` target. **A symlink was tried first and explicitly rejected**, because this
repo is cloned on Windows, Linux, and macOS, and symlinks don't survive that reliably
(Windows needs special permissions to create them at all; git on Windows can check one out
as a plain text file containing the link target unless `core.symlinks=true` is set, which
isn't guaranteed on every clone). A real directory move, tracked by git like any other file,
works identically everywhere. See `ansible/README.md`'s "`group_vars`/`host_vars` location"
section for the full technical detail — this is deliberately not duplicated here beyond what
a beginner needs to know: **if `ansible.cfg`'s `inventory =` path ever changes, `group_vars`/
`host_vars` have to move with it, or every group-specific variable silently stops applying.**

### What `configs/inventory/` actually contains

```text
configs/inventory/
├── main.ini              ← pvenodes, ansiblehosts, dcs, firewalls (from discovery)
├── rudder.ini             ← Rudder server + relay hosts
├── cld.ini, fal.ini, …    ← one file per site (53 total), generated — do not hand-edit
├── group_vars/
│   ├── all/                ← every host (packages, colours, AD forest identity)
│   ├── linux/               ← Linux-only: privilege escalation
│   ├── windows_nodes/        ← every Windows host: SSH connection settings
│   ├── windows_dc/            ← Domain Controllers
│   └── …
└── host_vars/
    └── <hostname>.yml     ← rare, host-specific overrides
```

Ansible merges every `.ini` file in `configs/inventory/` automatically — you don't list them
individually. Regenerate the generated `.ini` files after changing `sites.csv`/`devices.csv`:

```bash
python3 benarbejde/generate_inventory.py benarbejde/sites.csv \
  -o ansible/configs/inventory --devices benarbejde/devices.csv
```

---

## Dynamic Inventory Registration — `add_host`

A practical problem falls out of the rule above: a *brand-new* host being bootstrapped for
the first time isn't in `configs/inventory/<site>.ini` yet — it can't be, the whole point of
the run is to bring it to a known-good state so it *can* be added. But without being in a
group, it gets none of that group's `group_vars` (its Windows connection settings, its
domain controller variables, whatever the role needs).

The naive fix is to require the operator to hand-edit the `.ini` file before every first
run. That works, but it's exactly the kind of manual, error-prone step this repo tries to
design out — and for someone still learning Ansible, being told to edit an inventory file
correctly *before* they've successfully run their first playbook is a bad place to start.

The actual fix, used in `windows_bootstrap/playbooks/00-preflight.yml`, is Ansible's
built-in `add_host` module. It registers a host into a group **for the rest of the current
run only** — it never touches any file on disk, and the registration doesn't survive past
the `ansible-playbook` process exiting:

```yaml
- name: "[H2] Register into {{ _permanent_groups | join(', ') }} for the rest of this run"
  add_host:
    name:         "{{ target_hostname | upper }}"
    groups:       "{{ _permanent_groups }}"
    ansible_host: "{{ static_ip }}"
  delegate_to: localhost
  become: false
```

Two things make this actually useful rather than just a curiosity:

1. **`delegate_to: localhost`** runs the `add_host` task on the control node (where the
   in-memory inventory lives), not on the remote target — this is what lets a later,
   separately-imported play's `hosts:` pattern see the new group membership, confirmed
   empirically with a two-play test harness before trusting it in a real bootstrap chain.
2. **Registering into the most specific group is enough.** Adding a host to `windows_dc`
   correctly inherits every parent group's `group_vars` too (`windows_server` →
   `windows` → `windows_nodes`), including connection settings like
   `group_vars/windows_nodes/connection.yml`'s SSH user/key/shell — there's no need to
   also pass those as explicit `add_host` variables.

This means a genuinely new host can be bootstrapped with nothing more than
`-e target=<hostname> -e static_ip=<ip>` and correct group variables resolve from the very
first task onward — no pre-editing an `.ini` file, no bare-IP inventory hack that bypasses
`group_vars` entirely. The host still gets added to `configs/inventory/<site>.ini` for real
once bootstrap completes; `add_host` only covers the run that gets it there.

---

## Understanding an Ansible Playbook Command

The following command was executed:

```text
ansible@exadnsvrk001[~/ansible]$ ansible-playbook -i /home/ansible/ansible/configs/inventory --limit ansiblehosts --check --diff --step playbooks/linux/tools.yml
```

Breaking this down:

| Option | Purpose |
|--------|---------|
| `ansible-playbook` | Executes a playbook |
| `-i` | Specifies the inventory — must be a path *containing* `group_vars`/`host_vars` for those to be picked up (see above) |
| `--limit ansiblehosts` | Restricts execution to hosts in the `ansiblehosts` group |
| `--check` | Dry-run mode |
| `--diff` | Show changes that would occur |
| `--step` | Prompt before every task |
| `playbooks/linux/tools.yml` | Playbook being executed |

---

## Example Playbook Execution

The following output was captured exactly during execution:

```text
ansible@exadnsvrk001[~/ansible]$ ansible-playbook -i /home/ansible/ansible/configs/inventory --limit ansiblehosts --check --diff --step playbooks/linux/tools.yml
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

## Idempotency — Why Re-running a Playbook Is Safe

A playbook is **idempotent** when running it twice produces the same end state as running
it once — the second run reports `ok` (nothing to do) for anything the first run already
handled, rather than erroring or re-doing work. This isn't automatic; Ansible modules are
generally written to check state before changing it, but a playbook can still break
idempotency if it's written carelessly (e.g. a `command:` task that isn't itself
idempotent, or `hosts:` that resolves inconsistently between runs).

A concrete example, found during a 2026-07-09 audit of the `windows_bootstrap` chain: two
of its numbered plays (`10-rename.yml`, `40-choco-packages.yml`) had
`hosts: "{{ target_hosts | default(target | default('all')) }}"`, while every other play in
the chain used the simpler `hosts: "{{ target | default('all') }}"`. The difference matters:
if an earlier play in the same run had set `target_hosts` as a fact (via `set_fact`), those
two plays would keep targeting the stale value instead of picking up the
[dynamically-registered](#dynamic-inventory-registration--add_host) group membership from
`add_host` in `00-preflight.yml` — silently bootstrapping the wrong host, or none at all, on
a re-run in the same process. The fix was mechanical (make the `hosts:` line consistent
across every numbered play), but finding it required tracing exactly what each play's
`hosts:` pattern resolves to on both a first run and a second, back-to-back run — not just
reading each file in isolation.

**Practical takeaway for a beginner:** it's always safe, and a good habit, to re-run a
playbook you've already run — a healthy chain converges to the same state regardless of
starting point, and a play reporting a change on a run where you expected none is a signal
worth investigating, not ignoring.

---

## Understanding `ansible.cfg`

`ansible.cfg` is generated automatically by `ansibleme.sh` when the Ansible control node is
first set up, and is also committed to the repo (`ansible/ansible.cfg`) as the actual source
of truth — every setting and value below is taken directly from that committed file, with its
inline comments trimmed for readability (see `ansible/ansible.cfg` itself for the full comments,
including the 2026-07-09 ini-section-bug story referenced below):

```ini
[defaults]
interpreter_python = auto_silent
host_key_checking  = True

# firewallme's playbook uses a real Ansible role at a non-default location.
roles_path = playbooks/firewallme/roles

# Single, consolidated inventory location (see "Inventory and group_vars" above).
inventory = /home/ansible/ansible/configs/inventory

remote_user = ansible
private_key_file   = /home/ansible/ansible/configs/ansible-id_rsa

# Colourised output — see "Colourised Output" section below.
callback_plugins   = /home/ansible/ansible/callback_plugins
stdout_callback    = exa_pretty
callback_whitelist = exa_pretty
result_format      = yaml
bin_ansible_callbacks = True

forks = 50
timeout = 5
retry_files_enabled = True
retry_files_save_path = /tmp
display_skipped_hosts = False
display_failed_stderr = False

[callback_exa_pretty]
suppress_unreachable   = True
show_unreachable_hosts = False

[privilege_escalation]
become        = False
become_method = sudo
become_user   = root

[ssh_connection]
ssh_args = -o ControlMaster=auto -o ControlPersist=60s -o StrictHostKeyChecking=accept-new
pipelining = True
connect_timeout = 5

[persistent_connection]
command_timeout = 30
connect_retry_timeout = 15
```

Important settings and why they differ from a default Ansible installation:

| Setting | Value | Reason |
|---------|-------|--------|
| `host_key_checking` | `True` | `accept-new` (below) handles new hosts correctly, so `True` here only ever catches a *changed* fingerprint — a MITM safeguard, not a nuisance |
| `roles_path` | `playbooks/firewallme/roles` | The only role in this repo lives outside Ansible's playbook-relative default location |
| `inventory` | single path | See [Inventory and group_vars](#inventory-and-group_vars--the-part-that-isnt-optional) — this used to be two paths with incompatible group structures |
| `become` | **`False`** | Global privilege escalation is deliberately **off** — see [Understanding Sudo and Become](#understanding-sudo-and-become) below, this is not a mistake |
| `StrictHostKeyChecking` | `accept-new` | Trusts a host's key on first connect, but hard-fails on a *changed* key — unlike `no`, which silently accepts a changed key too |
| `forks` | `50` | Default is 5 — increased for an estate this size |
| `timeout` / `connect_timeout` | `5` | Short — hosts may be powered off and long waits aren't useful |
| `[persistent_connection]` | present | Required for network modules and larger parallel runs |

> **Note on `StrictHostKeyChecking=accept-new`:** this is a deliberate security improvement over `no`. With `no`, a changed host key (e.g. from a rebuilt node or a MITM attack) is silently accepted. With `accept-new`, new hosts are trusted on first connect, but a changed fingerprint for a known host causes a hard failure with a clear error message.

> **A real lesson in ini section semantics (2026-07-09):** an earlier version of this
> repo's committed `ansible.cfg` had `forks`, `timeout`, `retry_files_enabled`,
> `retry_files_save_path`, `display_skipped_hosts`, and `display_failed_stderr` sitting
> textually *after* a `[callback_exa_pretty]`/`[ssh_connection]` section header instead of
> under `[defaults]`. The file still parsed without error — ini section membership is purely
> positional (every `key = value` belongs to whichever `[section]` header appeared most
> recently above it), so there was no syntax error to catch, just six settings that were
> silently using Ansible's built-in defaults instead of the values written in the file
> (`forks=5` not `50`, `timeout=10s` not `5s`, etc.). Confirmed with Ansible's own
> `ansible.config.manager.ConfigManager` (`get_config_value_and_origin()` reports whether a
> setting came from the file or from Ansible's built-in default) — `ansible-config dump
> --only-changed -c ansible.cfg` is the quicker command-line equivalent for a spot check.
> **The takeaway: a config file that parses cleanly is not the same as a config file that
> does what it looks like it does** — worth an occasional `ansible-config dump --only-changed`
> against production to confirm the settings you expect are actually the ones in effect.

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
callback_whitelist = exa_pretty
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

**Privilege escalation is off by default in this repo** — `ansible.cfg`'s
`[privilege_escalation]` section sets `become = False` globally, not `True`. This is
deliberate, not an oversight: Windows hosts connect over SSH but have no `sudo` concept at
all, so a global `become = True` would break every Windows playbook the moment it tried to
escalate. Become is switched on only where it's actually needed — for the `linux` group —
via `group_vars/linux/main.yml`:

```yaml
# group_vars/linux/main.yml
# Privilege escalation for all Linux hosts.
ansible_become:        true
ansible_become_method: sudo
ansible_become_user:   root
```

`group_vars/all/main.yml` (loaded for every host, Linux and Windows alike) deliberately has
no `become` setting at all — only `group_vars/linux/main.yml` sets it, so only hosts in the
`linux` group ever escalate. This was "battle-tested" (`ansibleme.sh`'s own changelog wording)
after a global `become = True` genuinely broke Windows connectivity in an earlier version of
this repo — if you're tempted to move privilege escalation back to the global `[defaults]`/
`[privilege_escalation]` block for convenience, don't; it will break Windows again.

For a Linux host in the `linux` group, becoming root still requires the target host to
actually grant it — which is where passwordless sudo comes in:

```text
ansible@exadnsvrk001[~/ansible]$ sudo cat /etc/sudoers.d/ansible

# Ansible automation - full passwordless sudo
ansible ALL=(ALL) NOPASSWD: ALL
```

A common troubleshooting step is verifying whether passwordless sudo is functioning correctly on the target host itself, independent of what Ansible thinks it configured.

---

## Investigating Passwordless Sudo

The following commands were used during troubleshooting.

Verify group membership:

```text
ansible@exadnsvrk001[~/ansible]$ groups

ansible adm cdrom sudo dip users kvm
```

Verify effective permissions:

```text
ansible@exadnsvrk001[~/ansible]$ sudo -l

Matching Defaults entries for ansible on exadnsvrk001:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin, use_pty

User ansible may run the following commands on exadnsvrk001:
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
ansible@exadnsvrk001[~/ansible]$ ls -l /etc/sudoers.d/ansible

-r--r----- 1 root root 78 Jun 14 11:19 /etc/sudoers.d/ansible
```

The sudoers configuration was validated:

```text
ansible@exadnsvrk001[~/ansible]$ sudo visudo -c

/etc/sudoers: parsed OK
/etc/sudoers.d/README: parsed OK
/etc/sudoers.d/ansible: parsed OK
```

This confirms there are no syntax errors.

---

## Understanding Include Order

The following commands were executed:

```text
ansible@exadnsvrk001[~/ansible]$ sudo grep -n "sudo" /etc/sudoers
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
ansible@exadnsvrk001[~/ansible]$ sudo -k
sudo id

uid=0(root) gid=0(root) groups=0(root)
```

and:

```text
ansible@exadnsvrk001[~/ansible]$ sudo -k
sudo whoami

root
```

These tests prove that sudo can execute privileged commands without prompting for a password.

---

## Reboot Verification

After troubleshooting, the server was rebooted:

```text
ansible@exadnsvrk001[~/ansible]$ sudo reboot
ansible@exadnsvrk001[~/ansible]$ Connection to 192.168.139.8 closed by remote host.
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
║           EXAMPLE MUSIC LIMITED: exadnsvrk001            ║
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
ansible@exadnsvrk001[~]$ sudo -k
sudo whoami

root
```

System uptime immediately after reboot:

```text
ansible@exadnsvrk001[~]$ uptime
 18:39:12 up 1 min,  1 user,  load average: 0.25, 0.15, 0.06
```

This confirms that the sudo configuration remained functional after reboot.

---

## Recommended Workflow for New Administrators

Before executing any unfamiliar playbook:

```bash
ansible-playbook -i configs/inventory --limit HOSTGROUP --check --diff --step playbook.yml
```

Review every task carefully. Once satisfied:

```bash
ansible-playbook -i configs/inventory --limit HOSTGROUP playbook.yml
```

Always verify inventory, target hosts, become configuration, and sudo permissions before running production changes. Specifically:

- **`-i` must point at `configs/inventory`** (or wherever `ansible.cfg`'s `inventory =`
  points) — a bare IP or a path that doesn't contain `group_vars`/`host_vars` will silently
  skip every group-specific variable. See [Inventory and group_vars](#inventory-and-group_vars--the-part-that-isnt-optional).
- **A brand-new host that isn't in the inventory yet** isn't necessarily a blocker — some
  chains (`windows_bootstrap`) register it dynamically for the run via `add_host`. Check
  whether the playbook you're running does this before hand-editing an `.ini` file.
- **Don't expect `become` to "just work"** on a host outside the `linux` group — it's off
  by default everywhere else, deliberately.
- **A second run reporting unexpected `changed` tasks is worth investigating**, not
  re-running until it goes green — see [Idempotency](#idempotency--why-re-running-a-playbook-is-safe).

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-14 | Initial document |
| 2026-06-20 | Updated `ansible.cfg` to reflect current `ansibleme.sh`-generated config (`ansible.builtin.default` callback, `result_format`, `StrictHostKeyChecking=accept-new`, `forks`, `[persistent_connection]`) |
| 2026-06-20 | Added colourised output section — `exa_pretty` callback and `group_vars/all/colours.yml` |
| 2026-07-09 | Major expansion: added "How This Repository Is Organised" (`benarbejde/` single source of truth), "Inventory and group_vars" (the `host_group_vars` plugin mechanism, why it only auto-loads from inside the loaded inventory path, and the symlink-rejected/real-move fix), "Dynamic Inventory Registration" (`add_host` in `windows_bootstrap`'s preflight), and "Idempotency" (the `target`/`target_hosts` `hosts:` pattern bug found in the 2026-07-09 chain audit). Rewrote "Understanding ansible.cfg" against the actual committed `ansible/ansible.cfg` (previous version was stale and internally inconsistent with the Colourised Output section below it — it showed `ansible.builtin.default` as the callback when `exa_pretty` had already been rolled out). Corrected "Understanding Sudo and Become": the previous version stated `become = True` as the current global setting — it is, and must stay, `False`; Linux-only escalation lives in `group_vars/linux/main.yml`, and a global `become = True` previously broke Windows connectivity in production. |
| 2026-07-09 | While writing the `ansible.cfg` section against the real file, found `forks`/`timeout`/`retry_files_enabled`/`retry_files_save_path`/`display_skipped_hosts`/`display_failed_stderr` were textually inside the wrong `[section]` and silently inert — confirmed with `ansible.config.manager.ConfigManager`, not just by reading the file. Fixed the real `ansible/ansible.cfg` (all 6 now verified reading from the file), and added the "real lesson in ini section semantics" callout in "Understanding ansible.cfg" above. |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
