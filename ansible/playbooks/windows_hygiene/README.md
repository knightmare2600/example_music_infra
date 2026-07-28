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
| `playbooks/10-dism.yml` | `dism` | DISM component-store cleanup + `ResetBase` |
| `playbooks/20-hibernation-pagefile.yml` | `hibernation`, `pagefile` | Hibernation policy by chassis type + pagefile clear |
| `playbooks/30-choco.yml` | `choco` | Chocolatey `upgrade all` + WinDirStat + SDelete |
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
ansible-playbook playbooks/windows_hygiene/site.yml -i <host>, -e target_hosts=<host>

# Full hygiene pass, inventory group
ansible-playbook playbooks/windows_hygiene/site.yml -i configs/inventory -e target_hosts=windows_servers

# DISM only
ansible-playbook playbooks/windows_hygiene/site.yml -i <host>, -e target_hosts=<host> --tags dism

# Quick pass, skip the slower DISM cleanup
ansible-playbook playbooks/windows_hygiene/site.yml -i <host>, -e target_hosts=<host> --skip-tags dism
```

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
