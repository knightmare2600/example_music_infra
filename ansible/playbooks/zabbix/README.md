# playbooks/zabbix/

Robert's ask, 2026-10-16: a companion Zabbix 7.0 monitoring template for every playbook
family in this repo. The real Zabbix server (`EXAZABCLD001`, built via
`bootstrap/web/provision/zabbixme.sh`, break-glass only) already exists and works — the
actual blocker was that nothing anywhere installed `zabbix-agent` or registered a host
against it (confirmed directly in `docs/zabbix_templates/README.md`'s own "unstated
prerequisite" note). This directory, and the shared task file it wraps
(`../../tasks/zabbix_agent_onboard.yml`), is that missing piece.

Classic `zabbix-agent` only (Robert: "agent is agent not agent2, I am not using agent2"),
matching `zabbixme.sh`'s own server-side choice. Linux only — Windows agent rollout is
Salt's job (MSI), per Robert's own stated sequencing, and not yet built.

Builds on the real design already recorded in `docs/ansible/zabbix-playbooks-plan.md`
(2026-09-03) — template names, PSK field semantics, and the active-checks-only convention
were all verified there against the real Zabbix 7.0 packages/docs, not re-derived here.
One detail updated past that doc, verified fresh: `EnableRemoteCommands` is deprecated in
7.0 — `AllowKey=system.run[*]` is the real current mechanism, used here instead.

## Files

| File | What it does |
|------|-------------|
| `zabbix_server.yml` | Ansible port of `zabbixme.sh` — the full Zabbix 7.0 server (MariaDB, packages, schema, frontend, Apache vhost, API readiness + Admin rotation, auto-registration group/action, UFW, MOTD) |
| `zabbix_agent.yml` | Entry point — one-shot agent onboarding for an existing host, `--limit <hostname>` |
| `../../tasks/zabbix_agent_onboard.yml` | The real agent-side work: install, PSK, config, API `host.create`. Shared — also included automatically from `linux/tools.yml` for every new/re-run host going forward (Robert's own explicit choice) |
| `../../tasks/zabbix_repo_install.yml` | Shared: arch-aware `zabbix-release` install (debian/debian-arm64 tree), used by both `zabbix_server.yml` and `zabbix_agent_onboard.yml` |
| `requirements.yml` | `community.general` (ufw, apache2_module) + `community.mysql` (mysql_db/mysql_user/mysql_variables/mysql_query) — `zabbix_server.yml`'s own dependencies |

## Requires

- **`site_services.zabbix`** (`ip`/`hostname`) — generated from `devices.csv`'s `ZAB` row
  via `generate_inventory.py`'s `compute_site_services()`, same source-of-truth pattern as
  `site_services.dns`. Already wired up (2026-10-16).
- **`vault_zabbix_api_token`** in `configs/inventory/group_vars/all/vault.yml` (currently
  `"CHANGEME"`) — a **dedicated** Zabbix API token (Users → API tokens on `EXAZABCLD001`),
  deliberately not the `Admin` account's own password. Chosen specifically because
  `zabbix_agent_onboard.yml` is included from `linux/tools.yml`, a routinely re-run,
  `hosts: all` by default play — a masked per-run credential prompt there would be a real
  UX regression. Presented as an `Authorization: Bearer` header, not the deprecated
  JSON-RPC `auth` field. Only needed for agent registration, NOT for `zabbix_server.yml`
  itself (that one bootstraps its own Admin password into KeePass on first run, same
  `keepass_credential_sync.yml` pattern `windows_dc`'s own domain-admin/local-admin
  passwords use).
- `ansible-galaxy collection install -r requirements.yml` before running `zabbix_server.yml`.

## Quick start

```bash
# Install this family's collection dependencies once
ansible-galaxy collection install -r playbooks/zabbix/requirements.yml

# Build/rebuild the full Zabbix server (already-named EXA<ROLE><SITE><NNN> host required --
# this does NOT prompt for hostname/site the way zabbixme.sh itself does)
ansible-playbook -i configs/inventory playbooks/zabbix/zabbix_server.yml --limit EXAZABCLD001

# Create a dedicated API token on the server (Users -> API tokens in the UI), then set it
ansible-vault edit configs/inventory/group_vars/all/vault.yml

# Onboard a single, already-existing host's agent
ansible-playbook -i configs/inventory playbooks/zabbix/zabbix_agent.yml --limit <hostname>

# From here on, every linux/tools.yml run onboards new/unregistered hosts' agents automatically.
```

## Not yet built

- **`zabbix_proxy.yml`** — the new Zabbix proxy playbook, scoped in
  `docs/ansible/zabbix-playbooks-plan.md` but not needed yet (no proxy topology decided).
- **Windows agent rollout** — Salt's job (MSI install), explicitly out of scope here.
- **Live-tested against a real host.** Both `zabbix_server.yml` and the agent onboarding
  are written, syntax-checked, and harness-clean, but `zabbix_server.yml` specifically has
  not yet been run for real (the agent side has — see its own commit history for the real
  bugs found and fixed on `EXAZABCLD001`'s rebuild test).
- **Per-playbook-family companion templates** (the actual original ask — "every playbook
  gets a companion Zabbix template"). The server + agent onboarding were the prerequisite
  only; template design/build/API-verify/export for `linux/tools.yml` itself (the agreed
  first "low hanging fruit") comes next.
