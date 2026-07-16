# docs/zabbix_templates/

Deployment assets, not documentation — real Zabbix template `.xml`/`.yaml` files, consumed
directly rather than described. `WindowsHygiene.xml` is triggered by name from
`ansible/playbooks/windows_hygiene/site.yml --tags pagefile` (see that playbook's own README);
`zabbix_template_proxmox_nicguard.yaml` monitors the NIC-guard units deployed by
`ansible/playbooks/proxmox/playbooks/40-scripts.yml`.

See [../INDEX.md](../INDEX.md) for the full documentation index (this folder's own carve-out note
is under `zabbix_templates/`).
