# windows_bootstrap

Bootstraps and configures Windows machines (desktops, laptops, servers).
Ansible port of Join-DomainAndBootstrap.ps1.

## Playbook order

`00-preflight.yml` (hostname/static IP/Ansible key — including the actual
rename, Phase G) hands off to the rest of the chain below, ending with
`85-finish.yml` (remote-access summary + final reboot). The old
`05-bootstrap.yml` monolith that used to duplicate this chain inline as one
combined play was retired 2026-07-09 — every stage it contained was
confirmed to have a granular standalone equivalent first (two real gaps
found in the process were fixed before removal: see `00-preflight.yml`'s
and `80-domainjoin.yml`'s own changelogs). The standalone plays share
`tasks/*.yml` files (e.g. `tasks/rdp.yml`) with each other, so there's one
source of truth for the actual task logic.

`10-rename.yml` is deliberately **not** chained here (removed 2026-07-14) —
`00-preflight.yml`'s Phase G already renames the host using the same answer
given once, up front; chaining `10-rename.yml` straight after meant asking
the same question again independently, which produced a real typo during a
live forest-root DC build (`ansible-core`'s `vars_prompt` can't be
conditionally skipped based on an already-set fact — only a CLI extra-var
suppresses it). Still real and still standalone-usable, for renaming an
already-bootstrapped host later without a full re-bootstrap:
`ansible-playbook playbooks/10-rename.yml -i <ip>,`.

| Playbook | Tag | Description |
|----------|-----|-------------|
| `00-preflight.yml` | `bootstrap` | Hostname/static IP/Ansible key/rename, then hands off to the rest of the chain |
| `15-locale-timezone.yml` | `locale_timezone` | Locale (en-GB) and timezone (GMT Standard Time) |
| `20-registry.yml` | `registry` | Registry hardening |
| `22-screenlock.yml` | `screenlock` | Screen lock and inactivity timeout |
| `25-deadvertise.yml` | `deadvertise` | Advertising/telemetry suppression |
| `30-chocolatey.yml` | `chocolatey` | Chocolatey installation |
| `35-guest-tools.yml` | `guest_tools` | VMware Tools / QEMU guest agent by hypervisor |
| `40-choco-packages.yml` | `choco_packages` | Package deployment |
| `45-rsat.yml` | `rsat` | RSAT tools |
| `48-pswindowsupdate.yml` | `pswindowsupdate` | PSWindowsUpdate module |
| `50-binaries.yml` | `binaries` | Arch-aware binary + font deployment |
| `60-wallpaper.yml` | `wallpaper` | Corporate wallpaper + dark mode |
| `70-hibernation.yml` | `hibernation` | Power management: hibernation, pagefile, SConfig |
| `75-openssh.yml` | `openssh` | OpenSSH + Ansible key |
| `77-rdp.yml` | `rdp` | RDP with NLA |
| `78-sac-ems.yml` | `sac_ems` | SAC/EMS serial console (Server OS only) |
| `79-ps7-setup.yml` | `ps7_setup` | PS7 modules, fonts, profile, terminal config |
| `80-domainjoin.yml` | `domainjoin` | Join JUKEBOX domain |
| `85-finish.yml` | `finish` | Remote-access summary + final reboot |

`82-salt-minion.yml` (tag `salt`, all Windows nodes — WKS/LAP/SUR/SVR/DCS) is deliberately **not**
imported by `site.yml` — see `ansible/playbooks/salt/README.md` and
`docs/buildsheets/buildsheet-salt-minion.md`. Its numbered position exists purely for tidy
ordering alongside the plays above, not because it's chained in. Run it explicitly:
`ansible-playbook playbooks/windows_bootstrap/site.yml --tags salt -e target=<host>`.

A bare `site.yml` run with no `--tags` runs every play in the table above in sequence —
this is deliberate, not a gap. Each play is idempotent (checks its own
"already done" condition before acting), so a full run converges *any*
host — freshly built or already bootstrapped — to the same known-good
bootstrap state every time. That convergent state (renamed, packages
installed, hardened, domain-joined) is the prerequisite for the next,
separate step: DC promotion via `windows_dc/site.yml`, Salt minion install
(`--tags salt`, above), or any other module-specific action.
Use `--tags <name>` to re-run or debug a single
stage in isolation. `--tags bootstrap` only ever matches `00-preflight.yml`
(each play has its own unique tag, there's no shared "early stages" group)
— it is not a shorthand for "the minimal subset", just that one stage.

## Usage

Run from the `ansible/` root:

```
# Full run
ansible-playbook -i configs/inventory playbooks/windows_bootstrap/site.yml \
  -e target=<host> --ask-vault-pass

# Single stage
ansible-playbook -i configs/inventory playbooks/windows_bootstrap/site.yml \
  -e target=<host> --tags registry --ask-vault-pass

# Skip bootstrap (host already onboarded)
ansible-playbook -i configs/inventory playbooks/windows_bootstrap/site.yml \
  -e target=<host> --skip-tags bootstrap --ask-vault-pass
```

## Dependencies
Install galaxy collections first:
```
ansible-galaxy collection install -r requirements.yml
```

## 00-preflight.yml — DNS decision

`00-preflight.yml` automatically determines which DNS servers to configure when
it applies the static IP (via the `EXA-ApplyStaticIP` boot-time scheduled task).
You are not prompted for DNS — the play probes from the control node and decides.

**How it decides (in order):**

| Condition | Primary DNS | Secondary DNS |
|-----------|-------------|---------------|
| Role=DCS AND is_first_dc=yes | BIND9 (`192.168.139.8`) | — |
| Site DC (`.10`) reachable via TCP 389 | site DC `.10` | BIND9 |
| Site DC offline, hub DC reachable | nearest hub DC (FAL/ODE/BRK) | BIND9 |
| No DC reachable anywhere | BIND9 | — |

**Known source of truth:** hub DC IPs come from the `DC` column of
`/etc/example-music/sites.csv`. No IPs are hardcoded in the playbook.

**Order of operations:** probe runs before the SSH connection to the target.
The operator sees the decided DNS in the pre-flight summary before confirming.

**For non-DCS hosts with no site DC yet:** the hub fallback is temporary.
Once `EXADCS<SITE>001` is commissioned, update DNS to `.10` manually or
re-run preflight with `target_ip` left blank (skips the scheduled task;
DNS change must be done through AD or via `Set-DnsClientServerAddress`).
