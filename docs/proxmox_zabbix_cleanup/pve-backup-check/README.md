# docs/proxmox_zabbix_cleanup/pve-backup-check/

Self-contained deployment bundle for PVE guest backup-status monitoring (script +
systemd `.service`/`.timer`). Scores each guest against its own expected backup
cadence (pulled from the cluster's real job schedules), not a single fleet-wide
threshold. Writes a JSON report to `/tmp/pve-backup-check.json` every run.

Feeds the `Proxmox Health Checkup` Zabbix template
(`docs/zabbix_templates/zabbix_template_proxmox_health_checkup.json`) — its
checksum macro (`{$PVE_BACKUP_SCRIPT_CKSUM}`) and `Guest VM Discovery` LLD rule's
9 per-guest item prototypes both depend on this exact script.

Source: `private/pve-backup-check.time` was renamed to `.timer` here — a `.time`
extension is not a valid systemd unit suffix and would fail to load as-is.

See [../../INDEX.md](../../INDEX.md) for the full file list and descriptions.
