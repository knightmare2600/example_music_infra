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
| `zabbix_agent.yml` | Entry point — one-shot onboarding for an existing host, `--limit <hostname>` |
| `../../tasks/zabbix_agent_onboard.yml` | The real work: install, PSK, config, API `host.create`. Shared — also included automatically from `linux/tools.yml` for every new/re-run host going forward (Robert's own explicit choice) |

## Requires

- **`site_services.zabbix`** (`ip`/`hostname`) — generated from `devices.csv`'s `ZAB` row
  via `generate_inventory.py`'s `compute_site_services()`, same source-of-truth pattern as
  `site_services.dns`. Already wired up (2026-10-16).
- **`vault_zabbix_api_token`** in `configs/inventory/group_vars/all/vault.yml` (currently
  `"CHANGEME"`) — a **dedicated** Zabbix API token (Users → API tokens on `EXAZABCLD001`),
  deliberately not the `Admin` account's own password. Chosen specifically because this
  task file is included from `linux/tools.yml`, a routinely re-run, `hosts: all` by
  default play — a masked per-run credential prompt there would be a real UX regression.
  Presented as an `Authorization: Bearer` header, not the deprecated JSON-RPC `auth` field.

## Quick start

```bash
# Step 1 — create a dedicated API token on EXAZABCLD001 (Users -> API tokens in the UI),
#          then set it as a real value
ansible-vault edit configs/inventory/group_vars/all/vault.yml

# Step 2 — onboard a single, already-existing host
ansible-playbook -i configs/inventory playbooks/zabbix/zabbix_agent.yml --limit <hostname>

# From here on, every linux/tools.yml run onboards new/unregistered hosts automatically.
```

## Not yet built

- **`zabbix_server.yml`/`zabbix_proxy.yml`** — the Ansible ports of `zabbixme.sh` and a new
  Zabbix proxy playbook, both scoped in `docs/ansible/zabbix-playbooks-plan.md`. Deliberately
  deferred (Robert's own call) — the real server already works via the bash script and
  isn't blocking anything; the agent-onboarding piece was the actual prerequisite.
- **Windows agent rollout** — Salt's job (MSI install), explicitly out of scope here.
- **Live-tested against a real host.** Written and syntax-checked, harness-clean, but not
  yet run against anything real — next step is a disposable test VM (Robert's own choice,
  not the production estate) before this touches `linux/tools.yml`'s real `hosts: all`.
- **Per-playbook-family companion templates** (the actual original ask — "every playbook
  gets a companion Zabbix template"). This is the prerequisite only; template design/build/
  API-verify/export for `linux/tools.yml` itself (the agreed first "low hanging fruit")
  comes next, once agent registration is live-confirmed.
