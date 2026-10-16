# docs/zabbix_templates/

Deployment assets, not documentation — real Zabbix template `.xml`/`.yaml`/`.json` files,
consumed directly rather than described. `WindowsHygiene.xml` is triggered by name from
`ansible/playbooks/windows_hygiene/site.yml --tags pagefile` (see that playbook's own README);
`zabbix_template_proxmox_nicguard.yaml` monitors the NIC-guard units deployed by
`ansible/playbooks/proxmox/playbooks/50-systemd-units.yml` (`40-scripts.yml` only places the
script/credentials files — see that file's own header); `zabbix_template_linuxtools.json`
(2026-10-16) is the first of Robert's "every playbook gets a companion Zabbix template"
initiative — reads `/etc/example-music/zabbix_status/linux_tools.json`, written by
`ansible/playbooks/linux/tools.yml` itself at the end of every run.

See [../INDEX.md](../INDEX.md) for the full documentation index (this folder's own carve-out note
is under `zabbix_templates/`).

**Agent install is no longer an unstated prerequisite (2026-10-16)** — this used to be a real
gap (no playbook anywhere installed `zabbix-agent`/`zabbix-agent2`, confirmed 2026-07-21).
Fixed: `ansible/tasks/zabbix_agent_onboard.yml` (classic agent, PSK, API registration) is now
included automatically from `linux/tools.yml`, and available standalone via
`ansible/playbooks/zabbix/zabbix_agent.yml` for onboarding an existing host. Still genuinely true
for hosts NOT yet covered by either path — e.g. `WindowsHygiene.xml`'s own Windows targets
(Windows agent rollout is Salt's job, not yet built).

**`zabbix_template_linuxtools.json` has NOT been confirmed to import cleanly yet** (hand-authored
directly into JSON export format, same caveat `WindowsHygiene.xml`/the nicguard template already
had before this note was updated — neither of those three, including this new one, had been
test-imported against a real Zabbix instance at the time this line was last touched). First real
`configuration.import` attempt is the actual test.
