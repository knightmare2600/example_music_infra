# docs/proxmox_zabbix_cleanup/kernels/

Deployment bundle for the monthly PVE maintenance hoover (script + systemd `.service`/`.timer` +
Zabbix monitoring items). Canonical procedure doc is
[pve-maintenance-automation.md](../../pve-maintenance-automation.md) — this directory holds the
actual files to deploy, kept in sync with `ansible/playbooks/proxmox/files/pve-monthly-hoover.sh`.

See [../../INDEX.md](../../INDEX.md) for the full file list and descriptions.

**Unverified assumption (2026-07-21 audit):** the "PVE - Hoover Last Run Timestamp" Zabbix item
greps `/var/log/syslog` for the hoover script's `logger` output. No playbook in this repo installs
or configures `rsyslog` on a PVE 9.x (Debian Trixie) node — `10-packages.yml`'s `pve_packages`
list has no `rsyslog` entry — so whether `/var/log/syslog` actually exists as a flat file rests on
whatever the base Proxmox ISO ships with, not on anything checked or guaranteed here.
