# windows_bootstrap

Bootstraps and configures Windows machines (desktops, laptops, servers).
Ansible port of Join-DomainAndBootstrap.ps1.

## Playbook order

`00-preflight.yml` chain-imports `05-bootstrap.yml` (the full PostOOBE
bootstrap, Stages 0b–23) as one combined play. Everything below that is a
separate standalone play that also runs inline as part of that same
bootstrap chain — see `05-bootstrap.yml`'s own "Stage map" comment for
which numbered stage each corresponds to, and its shared `tasks/*.yml`
files (e.g. `tasks/rdp.yml`) that both the chain and the standalone play
include, so there's one source of truth for the actual task logic.

| Playbook | Tag | Description |
|----------|-----|-------------|
| `00-preflight.yml` | `bootstrap` | Hostname/static IP/Ansible key, then chain-imports `05-bootstrap.yml` |
| `10-rename.yml` | `rename` | Rename to EXA convention |
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

A bare `site.yml` run with no `--tags` currently runs every play above in
sequence (the standalone plays aren't actually tagged `never`, despite
site.yml's changelog claiming otherwise) — use `--tags <name>` for a single
stage, or `--tags bootstrap` for bootstrap-only.

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
