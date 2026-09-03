# Example Music Limited — Zabbix Ansible Playbooks (Design Plan)

> **Classification:** Internal — Infrastructure
> **Status:** PLAN — not yet built. Written 2026-09-03 before implementation, per Robert's
> request to record the design before writing the code, given the scope (three new playbooks,
> PSK cryptography, live Zabbix API host creation).
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Purpose

`bootstrap/web/provision/zabbixme.sh` (the break-glass Zabbix 7.0 server bootstrap script) is
confirmed working end-to-end — see
[project history / `docs/management/zabbix-worldclocks-widget.md`'s sibling work]. Robert's
next step, per his own original stated sequencing ("Start by creating the zabbixme.sh once it's
good, we'll backport it to ansible, then we'll write one for ansible and salt for the zabbix
agent"): convert it to Ansible, and add two entirely new capabilities that never existed in the
bash script — a Zabbix proxy playbook, and a one-shot agent-onboarding playbook that installs the
agent, configures PSK encryption, and registers the host against the API with the right
templates.

Three playbooks, all under `ansible/playbooks/zabbix/`:

1. `zabbix_server.yml` — direct port of `zabbixme.sh`.
2. `zabbix_proxy.yml` — new. Deploys a Zabbix proxy.
3. `zabbix_agent.yml` — new. One-shot onboarding: install agent → configure PSK → register via
   API → link templates, run with `--limit <hostname>` against a single freshly-built node.

## Real facts verified before writing any code

Two things Robert's own brief assumed turned out not to match current Zabbix 7.0, checked
directly against the real `zabbix-frontend-php_7.0.30`/`zabbix-sql-scripts_7.0.30` packages
downloaded from `repo.zabbix.com` (same discipline as the World Clocks widget build — verify
against the real shipped source, not memory or the brief's own wording):

- **Template names.** `Template OS Linux`/`Template OS Windows` are pre-6.0 names, long gone.
  The real current names, confirmed against the shipped schema (`grep`'d the actual template
  `INSERT` rows in `server.sql.gz`): **`Linux by Zabbix agent`** and
  **`Windows by Zabbix agent`** (active-check variants: `Linux by Zabbix agent active` /
  `Windows by Zabbix agent active`).

- **Firewall "interface" monitoring.** Robert's brief: "for a firewall would also add interface
  ... network traffic NOT SNMP." Checked the real template contents directly: there is **no
  separate template for this** — `Linux by Zabbix agent` already ships a `Network interface
  discovery` LLD rule using the native agent key `net.if.discovery` (confirmed NOT SNMP — this
  key runs entirely through the Zabbix agent itself), which auto-creates
  `net.if.in[{#IFNAME}]`/`net.if.out[{#IFNAME}]` (incoming/outgoing traffic) items for every
  interface it discovers. **Conclusion: firewalls need no second template link at all** — linking
  the same `Linux by Zabbix agent` every Linux host gets already gives them per-interface traffic
  monitoring automatically, for free.

- **`host.create`'s `interfaces` parameter is optional**, not required (checked the real API
  parameter table) — confirmed via `repo.zabbix.com` docs that only `groups` is marked
  `required`. Relevant because this estate's agents will run **active checks only** (see below),
  so no passive-polling interface object is actually needed on any host, firewall or not.

- **PSK field names/semantics** (real `host` object reference, `zabbix.com/documentation/7.0`):
  `tls_connect` = connections **to** the host (server-initiated, i.e. passive), `tls_accept` =
  connections **from** the host (agent-initiated, i.e. active/trapper) — bitmask, `2` = PSK.
  `tls_psk_identity` + `tls_psk` (≥32 hex digits) required together whenever either field has the
  PSK bit set. Real official example (`Creating a host with PSK encryption`) sets both
  `tls_connect: 2` and `tls_accept: 2` together even for a PSK-only host — matched for
  consistency rather than inventing an asymmetric variant.

## Design decisions and their grounding

| Decision | Grounding |
|---|---|
| Active checks (agent pushes to server), not passive polling | `zabbixme.sh`'s own UFW section (Section 6, already live) opens port `10051/tcp` (Zabbix **trapper** — inbound to the server from every site subnet) — this only makes sense if agents are pushing data in, i.e. active checks. Treated as an already-established convention from the server script's own real, working firewall rules, not a new open question. |
| Linux/Windows split via existing Ansible inventory group membership, not hostname re-parsing | The generated `.ini` files already have real, current groups (`windows_dc`, `windows_server`, `windows_desktop`, `windows_laptop`, `firewalls`, etc.) derived from `devices.csv`/`role_codes.csv` — the actual single source of truth. Re-parsing the hostname a second time in the playbook would duplicate a derivation that already exists (`feedback_dont_hand_roll_sweep_fully`) and could disagree with it. Presumed rule: host is in any `windows_*` group → `Windows by Zabbix agent`; otherwise → `Linux by Zabbix agent`. |
| PSK auto-generated per host, saved locally under root-only perms | Matches `zabbixme.sh`'s own established convention exactly (`/root/.zabbix_db_credentials`, `/root/.zabbix_api_credentials` — both `0600`, root-owned, generated not hand-typed). The agent playbook will do the same for the PSK it generates. |
| Proxy playbook built generic/site-agnostic, not hardcoded to a count or site | Robert gave no topology detail ("another one for proxy"). Matches the precedent already in this exact repo — `rudder_relay.yml` is written the same way: parameterised by `host_vars`, deployable at any site as needed, the playbook itself doesn't know or care how many relays/proxies exist. Avoids forcing a topology decision that's operational, not structural. |
| Masked API credential prompt, not vault-stored | Robert's explicit instruction: "the playbook will, of course, prompt for API creds username and password (masked)." Real, established syntax already used in this repo — `windows_dc/playbooks/00-dc-preflight.yml`'s `dc_admin_user`/`dc_admin_password` pair (`private: false` / `private: true`), which also supports an optional vault-backed `default:` for non-interactive runs. Same pattern will be used here. |
| Remote commands enabled (`EnableRemoteCommands`) | Explicitly deferred to this exact playbook in `zabbixme.sh`'s own final banner ("Linux agent — Ansible playbook (EnableRemoteCommands, zabbix_agentd.conf)") and in Robert's own brief for this task. |
| New host placed in the `auto-registration` host group via the API, not relying on passive autoregistration alone | Robert's brief wants role-aware template linking (different templates for firewall vs Windows) at onboarding time, which plain Zabbix autoregistration can't do cleanly (autoregistration actions apply the same fixed group/action to everything that registers, not per-host template logic). API-driven `host.create` from the playbook — which is what makes masked API-credential prompting necessary in the first place — handles this deterministically instead. |

## Playbook conventions being followed (established elsewhere in this repo)

- Header/version-history block style, `host_vars` with interactive fallback, idempotency —
  matching `ansible/playbooks/rudder/rudder_server.yml` (the direct precedent for
  `zabbixme.sh` → Ansible conversions in this repo).
- Install-then-API-register flow, `delegate_to: localhost` for the API calls, `uri` module,
  per-host summary report at the end — matching `ansible/playbooks/rudder/rudder_onboard.yml`
  (the direct precedent for a one-shot onboarding playbook run with `--limit <hostname>`).
- Masked credential prompting — matching `ansible/playbooks/windows_dc/playbooks/00-dc-preflight.yml`.

## Outline

### `zabbix_server.yml`

Section-by-section port of `zabbixme.sh`'s 14 sections (hostname, OS detection, base packages,
network, UFW, MariaDB, Zabbix repo+packages, DB schema+config+housekeeping, frontend config,
Apache vhost, API readiness + Admin password rotation, auto-registration host group, MOTD),
following the same idempotency guarantees the bash script already has confirmed live.

### `zabbix_proxy.yml`

Zabbix proxy install + repo setup (same arch-aware `debian`/`debian-arm64` split as the server
script), proxy-mode config (`Server=`, `Hostname=`, local SQLite or MySQL storage — TBD at
implementation time based on expected proxy load), PSK config matching the agent-side convention
above so proxies can also authenticate to the server.

### `zabbix_agent.yml`

One-shot, `--limit <hostname>` targeted:

1. Detect target OS/arch, install the matching Zabbix repo + `zabbix-agent` package + toolkit
   (`fping`, etc. — same list as the server script's own monitoring toolkit where applicable).
2. Generate a random PSK (`openssl rand -hex 32`-equivalent), write `TLSPSKIdentity`/`TLSPSKFile`
   into `zabbix_agentd.conf`, save the PSK locally on the target (root-only, matching
   `zabbixme.sh`'s own credential-file convention).
3. Set `ServerActive=`, enable `EnableRemoteCommands`.
4. Prompt for API username/password (masked).
5. Determine Linux vs Windows from the target's own Ansible inventory group membership.
6. `host.create` via the API: `groups` = the `auto-registration` group (+ any relevant site
   group), `templates` = `Linux by Zabbix agent` or `Windows by Zabbix agent`, `tls_connect`/
   `tls_accept` = `2` (PSK), `tls_psk_identity`/`tls_psk` = the generated PSK.
7. Per-host summary report.

## Open items for implementation time (not blocking, noted for completeness)

- Exact `fping`/toolkit package list to mirror from `zabbixme.sh`'s Section 4.
- Proxy storage backend (SQLite vs MySQL) — SQLite is the simpler default for a lightly-loaded
  site proxy; will default to SQLite unless a specific site's expected load says otherwise.
- Whether the agent playbook should also add the target to a site-specific host group (in
  addition to `auto-registration`) — leaning yes, matching the estate's existing
  per-site-subnet-aware conventions elsewhere (e.g. `zabbixme.sh`'s own UFW trapper rules, one
  per site subnet), to be confirmed at implementation time if it isn't obvious from the API's own
  existing `auto-registration` action config.
