# windows_hygiene — Post-Build Windows Cleanup & Optimisation

Example Music Limited — `jukebox.internal` domain

## Overview

Runs against any Windows host after `windows_bootstrap`/`windows_dc` has already built it —
servers, desktops, and laptops alike. Safe to re-run on a schedule (all tasks are idempotent
except DISM, which is harmless to repeat). Chassis/OS detection (`00-preflight.yml`) is done
at runtime via WMI — no group_vars or inventory grouping required, so it works uniformly
across the whole fleet.

---

## Playbook order

`00` is always the preflight ("before take off"); major steps increment by 10.

| File | Tag(s) | Description |
|------|--------|-------------|
| `playbooks/00-preflight.yml` | `preflight` | Chassis/OS detection (`is_laptop`, `is_server`) via WMI |
| `playbooks/05-example-music-files.yml` | `example_music_files` | Deploy `sites.csv`/`devices.csv`/`role_codes.csv`/`address_policy.csv`/`ad_forest.json`/`ad_groups.json`/`ad_users.json`/`ad_computers.json` + `nodeinfo.json` to `C:\ProgramData\ExampleMusic\Config` |
| `playbooks/10-dism.yml` | `dism` | DISM component-store cleanup + `ResetBase` |
| `playbooks/20-hibernation-pagefile.yml` | `hibernation`, `pagefile` | Hibernation policy by chassis type + pagefile clear |
| `playbooks/30-choco.yml` | `choco` | Chocolatey `upgrade all` + WinDirStat + SDelete |
| `playbooks/35-winupdate-policy.yml` | `winupdate_policy` | Set Windows Update to manual download + manual install, and never force a reboot while a user is logged on |
| `playbooks/40-winupdate.yml` | `winupdate` | PSWindowsUpdate module + Windows Update |
| `playbooks/50-summary.yml` | `summary` | Print summary |

---

## Dependencies
Install galaxy collections first:
```
ansible-galaxy collection install -r requirements.yml
```

## Usage

Run from the `ansible/` root.

```bash
# Full hygiene pass, single host
ansible-playbook playbooks/windows_hygiene/site.yml -i configs/inventory --limit <host>

# Full hygiene pass, inventory group
ansible-playbook playbooks/windows_hygiene/site.yml -i configs/inventory -e target_hosts=windows_servers

# DISM only
ansible-playbook playbooks/windows_hygiene/site.yml -i configs/inventory --limit <host> --tags dism

# Quick pass, skip the slower DISM cleanup
ansible-playbook playbooks/windows_hygiene/site.yml -i configs/inventory --limit <host> --skip-tags dism

# Windows Update policy fix only -- safe to re-run against an already-built box,
# never triggers 40-winupdate.yml's own actual update-install run as a side effect
ansible-playbook playbooks/windows_hygiene/site.yml -i configs/inventory --limit <host> --tags winupdate_policy
```

**Why a separate tag from `winupdate`**: `--tags winupdate_policy` only ever matches
`35-winupdate-policy.yml`'s own tasks. `40-winupdate.yml` (actively running Windows Update
via PSWindowsUpdate) carries the separate `winupdate` tag deliberately — re-applying the
manual-update policy to an already-built, working box must never also kick off a real
update install as an unrelated side effect.

**Corrected 2026-10-04**: the single-host examples above previously showed
`-i <host>, -e target_hosts=<host>` — the same ad-hoc-inventory form
`windows_bootstrap` genuinely needs for its bare-DHCP-IP first run. This family
has no equivalent day-0 case of its own (it only ever runs against hosts
already bootstrapped and in `configs/inventory`), so that form was just
copied convention, not a real requirement — confirmed empirically
(`--list-hosts --limit <a-real-host>`, no `-e target_hosts=` at all) that
plain `-i configs/inventory --limit <host>` works correctly and is simpler.

Standalone plays can also be run directly without `site.yml`, e.g.:

```bash
ansible-playbook playbooks/windows_hygiene/playbooks/30-choco.yml -i configs/inventory
```

`20-hibernation-pagefile.yml` and `50-summary.yml` need `00-preflight.yml`'s facts — run those
together (or via `site.yml`) rather than standalone.

---

## Zabbix integration

`docs/zabbix_templates/WindowsHygiene.xml` is a Zabbix template whose trigger *descriptions*
name `windows_hygiene/site.yml --tags pagefile` by name, telling a human what to run when the
trigger fires — there is no remote-command item or Zabbix action in the template, so this is
not automated; someone has to read the trigger and run the playbook themselves. The tag names in
the table above are still a stable interface this template's trigger text depends on; don't
rename them without updating the template too.

---

## Changelog

- 2026-07-02  Initial file
- 2026-07-06  Added Chocolatey upgrade, WinDirStat, SDelete, PSWindowsUpdate/Windows Update
- 2026-07-06  Split the single monolithic play into numbered standalone `playbooks/NN-*.yml`
  files, matching the `00-preflight`/major-step-of-10 convention used by `windows_dc` and
  `windows_bootstrap`
- 2026-07-15  Added this README — the module had zero doc coverage anywhere in the repo until
  now (found during a docs-drift audit)
- 2026-10-04  Corrected the single-host Usage examples — they copied `windows_bootstrap`'s
  genuine bare-DHCP-IP ad-hoc-inventory form (`-i <host>, -e target_hosts=<host>`) despite
  this family having no day-0 case of its own (it only runs against already-onboarded hosts).
  Switched to `-i configs/inventory --limit <host>`, confirmed empirically correct.
- 2026-10-10  Added `35-winupdate-policy.yml` (Robert's ask): sets Windows Update to manual
  download + manual install (the same registry policy Group Policy's "Configure Automatic
  Updates" writes) and stops forced reboots while a user is logged on — background Windows
  Update behaviour was interfering with Ansible runs. Deliberately its own tag
  (`winupdate_policy`), not folded into `winupdate`, so it can be re-applied to an
  already-built box on its own without also triggering `40-winupdate.yml`'s real
  update-install run. Also found and fixed the same stale `-i <host>, -e target_hosts=<host>`
  pattern this entry already corrected here, still present in `site.yml`'s own header —
  fixed there too while adding the new tag to its usage examples.
