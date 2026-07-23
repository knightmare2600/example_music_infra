# playbooks/salt/

Ansible playbook for bootstrapping the Salt master that manages every Windows
node — client endpoints, member servers, and domain controllers
(`WKS`/`LAP`/`SUR`/`SVR`/`DCS` per `benarbejde/role_codes.csv`'s `SLT` row).
Not `FWL`/`PVE`/Linux generally. `TAB` only counts when `devices.csv`'s `OS`
column genuinely says Windows (most real `TAB` rows are Android/iPadOS —
see `benarbejde/generate_inventory.py`'s `DEVICE_GROUP_MAP` comment).
`MAC`/`MBP` (macOS) are future plans, not current scope.

Scope revised twice on 2026-07-20 (was "client endpoints only" at the start
of the day): first widened to include member servers (Chocolatey-driven
pull-based software management benefits them too, same as client
endpoints), then widened again to include domain controllers — Robert's
explicit call both times. Still weighed against extending the old
(never-built) Rudder plan; see `ansible/README.md`'s `## rudder` section for
why that plan's broader scope doesn't apply here.

Minions are installed by `ansible/playbooks/windows_bootstrap/playbooks/
82-salt-minion.yml`, not by anything in this directory — see
`docs/buildsheets/buildsheet-salt-minion.md` for the full minion-side
install and the manual fallback. This runs late in the windows_bootstrap
chain (after domain join), deliberately not at Windows-Setup time via the
unattend XML — see that buildsheet and `82-salt-minion.yml`'s own header
for why (random Setup-time hostnames would otherwise pollute the master's
key list with dead entries).

---

## Files

Numbered-stage chain (2026-07-22 — replaced the single monolithic
`salt_master.yml`, matching the `00-preflight`/major-step-of-10 convention
already used by `proxmox`/`windows_bootstrap`/`windows_dc`), driven by
`site.yml`:

| File | What it does |
|------|-------------|
| `playbooks/00-preflight.yml` | SSH keypair connectivity check + prompts/validates `salt_hostname`/`salt_static_ip`/`salt_gateway` |
| `playbooks/10-master.yml` | Hostname, static IP, packages, UFW, Salt master install (version-pinned to `salt_version_major`), master config, nodeinfo |
| `playbooks/20-saltgui.yml` | `salt-api` + SaltGUI web dashboard — dedicated local PAM account, not the `ansible` automation account |
| `site.yml` | Orchestrator — imports the three stages above in order |

## Directory layout in the repo

```
ansible/
├── configs/
│   └── inventory/
│       ├── salt.ini                    ← [salt_servers] / [salt_minions] groups
│       ├── group_vars/
│       │   └── salt_servers/main.yml   ← Salt master group vars
│       └── host_vars/
│           └── EXASLTCLD001/main.yml   ← IP, hostname, site metadata
└── playbooks/
    └── salt/
        ├── README.md                   ← this file
        ├── site.yml                    ← orchestrator
        └── playbooks/
            ├── 00-preflight.yml
            ├── 10-master.yml
            ├── 20-saltgui.yml
            └── templates/
                └── salt-static.nmconnection.j2
```

## Usage

First run (before ansible user exists, using root + password):
```bash
ansible-playbook playbooks/salt/site.yml \
  --limit salt_servers \
  --user root -k
```

Subsequent runs (ansible user + key):
```bash
ansible-playbook playbooks/salt/site.yml \
  --limit salt_servers
```

Standalone plays can also be run directly without `site.yml`, e.g.:
```bash
ansible-playbook playbooks/salt/playbooks/20-saltgui.yml
```
(`10-master.yml` and `20-saltgui.yml` both need `00-preflight.yml`'s facts —
run those together, or via `site.yml`, rather than standalone.)

## Version alignment

`group_vars/salt_servers/main.yml`'s `salt_version_major` pins the Debian
apt install to that major line via `/etc/apt/preferences.d/salt-pin`. The
Windows minion installer (`docs/buildsheets/buildsheet-salt-minion.md`) must
be fetched from the same major line — master and minions on mismatched major
versions is an unsupported combination upstream. Bump both together when
either needs updating.

## Built since this was written

- **Salt states/pillar source — settled 2026-07-20.** They live in this
  repo's own top-level `salt/{states,pillar}/`, served to the master via
  `gitfs`/`git_pillar` directly from the git remote (Section 6 of
  `playbooks/10-master.yml`) — no local clone/sync step, no credentials
  (public repo). See `salt/README.md` for the full reasoning and what
  replaced the hand-rolled clone-and-cron approach an earlier dropped-in
  Salt state used.
- **SaltGUI — built 2026-07-22.** `playbooks/20-saltgui.yml` installs
  `salt-api` and erwindon/SaltGUI (a plain static app served by
  `salt-api`'s own `rest_cherrypy`, no separate web server or npm build
  step). Auth is local PAM via a dedicated `saltgui` account — deliberately
  not the `ansible` automation account, which is key/sudo-only with no real
  password by design (see `linux/tools.yml`). TLS not yet done — see that
  file's own header.

## Not yet built

- **SaltGUI TLS.** `20-saltgui.yml` ships with `disable_ssl: true` — fine
  for an internal VPN/LAN-only tool, not for anything wider. Revisit before
  exposing this further.
- **Syndic tier.** Judged premature at current scale (~49 client-endpoint
  devices across the estate). If ever needed, it would go at a handful of
  regional hub sites, not as a universal per-site standard slot.
