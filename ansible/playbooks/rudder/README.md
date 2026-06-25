# playbooks/rudder/

Ansible playbooks for deploying and managing the Rudder configuration
management server across the `jukebox.internal` estate.

These are the Ansible equivalent of `rudderme.sh` and integrate into
the existing `example_music_infra` repo structure under `ansible/`.

---

## Files

| File | What it does |
|------|-------------|
| `rudder_server.yml` | Bootstraps EXASRVFAL002: hostname, static IP, packages, UFW, Rudder install, LDAP skeleton, Cockpit, MOTD, sentinel |
| `rudder_relay.yml` | Installs `rudder-server-relay` on ODE/BRK relay nodes (future) |
| `rudder_onboard.yml` | Installs the Rudder agent on a Linux node and registers it via API |

## Directory layout in the repo

```
ansible/
├── configs/
│   └── inventory                      ← add [rudder_servers] stanza (see inventory_snippet.ini)
├── group_vars/
│   ├── all/
│   │   ├── main.yml
│   │   └── colours.yml                ← existing — _c.R / _c.G etc.
│   ├── rudder_servers/
│   │   ├── main.yml                   ← Rudder group vars
│   │   └── vault.yml                  ← ENCRYPTED — API token, passwords
│   └── rudder_relays/
│       └── main.yml
├── host_vars/
│   └── EXASRVFAL002/
│       └── main.yml                   ← IP, hostname, site metadata
├── playbooks/
│   └── rudder/
│       ├── README.md                  ← this file
│       ├── rudder_server.yml
│       ├── rudder_relay.yml
│       └── rudder_onboard.yml
└── sites.csv                          ← single source of truth for subnets
```

---

## Quick start

### Step 1 — Add to inventory

Append the content of `inventory_snippet.ini` to `configs/inventory`.

### Step 2 — Populate host_vars

`host_vars/EXASRVFAL002/main.yml` is pre-filled for the FAL server.
For each additional relay or server, create a matching `host_vars/<hostname>/main.yml`.

If `rudder_static_ip` or `rudder_hostname` are absent from `host_vars`,
the playbook will prompt interactively before making any changes.

### Step 3 — Set up the vault

```bash
# Copy the template and fill in real values
cp group_vars/rudder_servers/vault.yml /tmp/rudder_vault_plain.yml
vim /tmp/rudder_vault_plain.yml

# Generate bcrypt hash for the admin password
htpasswd -bnBC 12 "" 'YourAdminPassword' | tr -d ':\n'

# Encrypt
ansible-vault encrypt group_vars/rudder_servers/vault.yml

# Verify
ansible-vault view group_vars/rudder_servers/vault.yml
```

> `rudder_api_token` can be left as `UNSET` for the first run.
> The playbook warns and skips the allowed-networks step.
> After your first UI login, create the token, update the vault, and re-run.

### Step 4 — First run (root login, before ansible user exists)

```bash
ansible-playbook playbooks/rudder/rudder_server.yml \
  --limit rudder_servers \
  --user root -k \
  --ask-vault-pass
```

### Step 5 — After first UI login: add API token to vault

```bash
# Log in to https://192.168.76.12/rudder
# Administration → API accounts → New API account
# Name: rudder-automation   Role: Read/Write
# Copy the token

ansible-vault edit group_vars/rudder_servers/vault.yml
# Set rudder_api_token: "your-token-here"
```

### Step 6 — Re-run to populate allowed networks

```bash
ansible-playbook playbooks/rudder/rudder_server.yml \
  --limit rudder_servers \
  --ask-vault-pass
```

This time the playbook POSTs all site subnets from `sites.csv` to the
Rudder API in one call, replacing the empty default allowed-networks list.

### Step 7 — Onboard nodes

```bash
# Linux nodes
ansible-playbook playbooks/rudder/rudder_onboard.yml \
  --limit <hostname or group> \
  --ask-vault-pass

# Windows — see rudder-setup.md section 11 for GPO/MSI approach
```

---

## Variable reference

### group_vars/rudder_servers/main.yml (non-secret)

| Variable | Default | Description |
|----------|---------|-------------|
| `rudder_domain` | `jukebox.internal` | AD domain |
| `rudder_dc_hostname` | `EXADCSFAL001` | Primary AD DC hostname |
| `rudder_version` | `8.x` | Rudder package stream |
| `rudder_admin_user` | `admin` | Rudder web UI local admin username |
| `rudder_ldap_bind_dn` | `CN=Rudder LDAP Bind,...` | AD LDAP bind account DN |
| `rudder_ldap_base` | `DC=jukebox,DC=example` | LDAP search base |
| `rudder_ldap_admin_group` | `CN=GRP_Rudder_Admins,...` | AD group → Rudder admin role |
| `sites_csv_path` | `../../sites.csv` | Path to sites.csv on control node |
| `rudder_base_packages` | (list) | Base packages installed in section 3 |
| `rudder_site_ufw_rules` | (list) | UFW rules for agent connectivity |

### group_vars/rudder_servers/vault.yml (secrets — encrypted)

| Variable | Description |
|----------|-------------|
| `rudder_admin_password` | bcrypt hash for local admin fallback |
| `rudder_api_token` | Rudder REST API token (set after first UI login) |
| `rudder_ldap_bind_pass` | Password for `svc_rudder_ldap` AD account |

### host_vars/EXASRVFAL002/main.yml (per-host)

| Variable | Example | Description |
|----------|---------|-------------|
| `rudder_hostname` | `EXASRVFAL002` | Hostname (uppercase, EXA convention) |
| `rudder_static_ip` | `192.168.76.12` | Static IP for this node |
| `rudder_gateway` | `192.168.76.1` | Default gateway |
| `rudder_dns` | `192.168.76.10` | DNS / AD DC IP |
| `rudder_prefix` | `24` | Subnet prefix length |
| `rudder_network_interface` | `""` | Interface to configure (blank = auto-detect) |
| `rudder_site_code` | `FAL` | Site code (matches sites.csv) |
| `rudder_site_city` | `Falkirk` | Site city (used in MOTD) |
| `rudder_site_country` | `Scotland` | Site country (used in MOTD) |
| `rudder_site_entity` | `Example Music Limited` | Entity name (used in MOTD) |

---

## Notes

### Why two-step (vault token on second run)?

Rudder generates the API token through the web UI after the server is up —
there is no way to pre-provision it. The playbook is designed to be run
twice: once to install and start Rudder, once to configure it via API after
the token exists. Both runs are fully idempotent.

### Static IP and SSH sessions

The `nmcli con add` task writes the static IP profile but does not apply it
immediately — applying NetworkManager changes during an active SSH session
drops the connection. The profile takes effect on reboot, which is the same
behaviour as `rudderme.sh`. At the local console (or cloud serial console),
run `nmcli con up rudder-static` to apply without rebooting.

### CLD IP conflict check

`EXASRVFAL002` is cloud-hosted. Some cloud providers filter ICMP within the
virtual network, so the ping-based IP conflict check may return a false
negative. The playbook emits a warning in that case rather than failing —
the operator is expected to verify the IP is free via the cloud console.

### sites.csv path

The playbook reads `sites.csv` from the Ansible control node (not the
target). The default path is `../../sites.csv` relative to the playbook
file, which resolves to the repo root when the standard directory layout
is used. Override with `--extra-vars "sites_csv_path=/path/to/sites.csv"`
if your layout differs.

### Rudder API — allowed-networks replaces, not appends

The Rudder API endpoint `POST /rudder/api/latest/settings/allowed_networks/root`
**replaces** the entire allowed-networks list on each call. The playbook
always sends the complete list derived from `sites.csv`. If you add subnets
manually in the UI between playbook runs, they will be removed on the next
run unless you also add them to `sites.csv`.

---

## Related documents

| Document | Where |
|----------|-------|
| `rudder-setup.md` | Full manual procedure — server setup, agent onboarding, API reference |
| `rudderme.sh` | Shell equivalent of this playbook |
| `ansibleme.sh` | Ansible node bootstrap (style reference) |
| `buildsheets/buildsheet-dcs.md` | AD DC build — prerequisite for LDAP |
