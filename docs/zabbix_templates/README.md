# docs/zabbix_templates/

Deployment assets, not documentation — real Zabbix template `.xml`/`.yaml` files, consumed
directly rather than described. `WindowsHygiene.xml` is triggered by name from
`ansible/playbooks/windows_hygiene/site.yml --tags pagefile` (see that playbook's own README);
`zabbix_template_proxmox_nicguard.yaml` monitors the NIC-guard units deployed by
`ansible/playbooks/proxmox/playbooks/50-systemd-units.yml` (`40-scripts.yml` only places the
script/credentials files — see that file's own header).

See [../INDEX.md](../INDEX.md) for the full documentation index (this folder's own carve-out note
is under `zabbix_templates/`).

**Unstated prerequisite (2026-07-21 audit):** no Ansible playbook in this repo installs the
`zabbix-agent`/`zabbix-agent2` package itself — `50-systemd-units.yml` only restarts it and
deploys a `.d` drop-in, on the assumption it's already present. If it isn't already on the node
some other way, these templates' items will never populate.
