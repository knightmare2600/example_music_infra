# proxmox/ — PVE Node Onboarding & Management

Example Music Limited — Proxmox VE fleet

## Overview

**The authoritative, current procedure doc is `docs/proxmox/Procedure-PVE-Node-Onboarding.md`**
— full end-to-end walkthrough, real transcript excerpts, troubleshooting. This README is a
quick file-map, not a duplicate of that doc; keep the detailed procedure there.

| File | What it does |
|------|---------------|
| `bootstrap-new-node.yml` | First real step for a freshly-preseeded node: renames it from its DHCP placeholder to its real hostname, rewrites networking to static, then chains straight into `site.yml`'s full stage chain in the same run (one reboot, at the end). Not number-prefixed — a deliberate, one-time, higher-risk identity-rename operation, never run as a side effect of routine maintenance. |
| `site.yml` | Onboarding/refresh chain for an already-identified node — see playbook order below. Safe to re-run; by default only refreshes non-disruptive stages (packages, `/etc/example-music/`, scripts) unless `-e pve_force_full_onboard=true` is passed. |
| `cloud_templates.yml` | Builds Ubuntu Noble / Debian Trixie cloud-init VM templates on a node. Idempotent — skips if the template ID already exists. |
| `playbooks/00-preflight.yml` – `50-systemd-units.yml` | `site.yml`'s numbered stage chain (see below) |
| `files/` | Static assets deployed by the stages above |

### `site.yml` playbook order

`00` is always the preflight ("before take off"); major steps increment by 10.

| File | Tag | Description | Gated? |
|------|-----|--------------|--------|
| `playbooks/00-preflight.yml` | `preflight` | Site lookup (`sites.csv`) + onboarding-state detection | — |
| `playbooks/10-packages.yml` | `packages` | Management packages | Always |
| `playbooks/20-ansible-access.yml` | `ansible_access` | Ansible user/SSH key/sudoers/kvm group | **Only on first onboard**, or with `-e pve_force_full_onboard=true` |
| `playbooks/30-example-music.yml` | `example_music` | `/etc/example-music/` — `sites.csv`, `devices.csv`, `nodeinfo.json` | Always |
| `playbooks/40-scripts.yml` | `scripts` | Maintenance scripts (`convert-v2v.py`/`create-vm.py`/`manage-pool.py`), apt config, NIC-guard credentials dir | Always |
| `playbooks/45-virt-tools.yml` | `virt_tools` | V2V prereqs, VirtIO ISO, `proxmoxbmc`/BIOS ROM file placement | Always |
| `playbooks/46-proxmorph.yml` | `proxmorph` | [proxmorph](https://github.com/IT-BAER/proxmorph) UI themes + hardware sensor monitoring | Always |
| `playbooks/50-systemd-units.yml` | `systemd_units` | Systemd units + Zabbix agent + `proxmoxbmc` service | Gated, same as `20-ansible-access.yml` |

---

## Usage

Run from the `ansible/` root — see `docs/proxmox/Procedure-PVE-Node-Onboarding.md` for the full
walkthrough. Quick reference:

```bash
# Brand-new node (first ever run against it)
ansible-playbook playbooks/proxmox/bootstrap-new-node.yml \
  -i configs/inventory -i "<dhcp-ip>," -e target=<hostname-from-buildsheet>

# Routine refresh of an already-onboarded node
ansible-playbook playbooks/proxmox/site.yml -i configs/inventory -e target=<hostname>

# Force a full re-onboard (re-touches access + systemd/Zabbix state)
ansible-playbook playbooks/proxmox/site.yml -i configs/inventory \
  -e target=<hostname> -e pve_force_full_onboard=true

# Build cloud-init VM templates
ansible-playbook playbooks/proxmox/cloud_templates.yml -i configs/inventory --limit pvenodes
```

---

## Changelog

- 2026-07-15  Added this README — the directory had no directory-level doc coverage (found
  during a docs-drift audit; the full procedure was already well-documented in
  `docs/proxmox/Procedure-PVE-Node-Onboarding.md`, just not cross-referenced from here).
