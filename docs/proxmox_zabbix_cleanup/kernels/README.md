# docs/proxmox_zabbix_cleanup/kernels/

Deployment bundle for the monthly PVE maintenance hoover (script + systemd `.service`/`.timer` +
Zabbix monitoring items). Canonical procedure doc is
[pve-maintenance-automation.md](../../pve-maintenance-automation.md) — this directory holds the
actual files to deploy, kept in sync with `ansible/playbooks/proxmox/files/pve-monthly-hoover.sh`.

See [../../INDEX.md](../../INDEX.md) for the full file list and descriptions.
