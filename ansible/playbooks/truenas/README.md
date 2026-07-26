# playbooks/truenas/

Ansible playbooks for configuring an already-installed, already-networked
site NAS/SAN (`EXANAS<SITE>001`, the `.19` standard slot — see
`docs/proxmox/proxmox-dcm-pbs-planning.md`'s "Site Storage — NAS/SAN
(TrueNAS)" section for the full addressing history).

**Install is NOT done here and never will be.** `arensb/ansible-truenas` has
no bootstrap/install capability of its own (checked directly against its
real module list, 2026-07-22) — Robert installs TrueNAS by hand, box by box
(no working answer-file/PXE mechanism exists for either CORE or SCALE),
then completes TrueNAS's own web-UI first-run setup (admin password, static
`.19` IP, at least one pool created) before any of this runs. **SSH is NOT
reliably part of that wizard** — confirmed live against `EXANASFAL001`,
2026-07-26 — so `playbooks/00-rest-bootstrap.yml` enables it via TrueNAS's
REST API first, if needed.

**No network/IP reconfiguration happens anywhere in this chain.** The
collection has no interface/IP module at all — `arensb.truenas.filesystem`/
`.hostname`/`.user` and everything else in it only ever talk to TrueNAS's
own middleware daemon (`midclt`/`client`), never `nmcli` or an equivalent.
Unlike `bind9-dns.yml`/`rudder_server.yml`/`salt/`'s own NM session-safety
pattern, there's nothing here for that pattern to apply to.

---

## Files

Numbered-stage chain, matching `proxmox`/`salt`/`windows_bootstrap`'s own
`00-preflight`/major-step-of-10 convention, driven by `site.yml`:

| File | What it does |
|------|-------------|
| `playbooks/00-rest-bootstrap.yml` | Enable SSH via TrueNAS's REST API — only needed if SSH doesn't already work; a genuinely separate API from `arensb.truenas` (local-socket-only), see that file's own header |
| `playbooks/00-preflight.yml` | SSH keypair connectivity check + hostname/site lookup |
| `playbooks/10-access.yml` | Dedicated `ansible` automation account (`arensb.truenas.user`, not `linux/tools.yml` — TrueNAS accounts are middleware-managed, not `/etc/passwd`), hostname, nodeinfo.json |
| `playbooks/20-storage.yml` | Pools/datasets/shares — deliberately minimal, see that file's own header (no real per-site spec exists yet) |
| `site.yml` | Orchestrator — imports the four stages above in order |
| `requirements.yml` | `arensb.truenas` collection — install with `ansible-galaxy collection install -r requirements.yml` |

## Usage

First run, brand new box where SSH doesn't work yet (needs
`group_vars/truenas_servers/vault.yml`'s REST credentials):
```bash
ansible-playbook playbooks/truenas/site.yml \
  --limit <hostname> --ask-vault-pass
```

First run, SSH already enabled via the web-UI wizard (rest-bootstrap not needed):
```bash
ansible-playbook playbooks/truenas/site.yml \
  --limit <hostname> --user root -k --skip-tags rest-bootstrap
```

Subsequent runs (ansible user + key):
```bash
ansible-playbook playbooks/truenas/site.yml \
  --limit <hostname> --skip-tags rest-bootstrap
```

Standalone plays can also be run directly without `site.yml`, e.g.:
```bash
ansible-playbook playbooks/truenas/playbooks/20-storage.yml
```
(`10-access.yml` and `20-storage.yml` both need `00-preflight.yml`'s facts —
run those together, or via `site.yml`, rather than standalone.)

## Inventory

Targets the `truenas_servers` group, populated automatically by
`generate_inventory.py` whenever a real `devices.csv` `Type=NAS` row exists
(`DEVICE_GROUP_MAP`, added 2026-07-22 alongside this module) — same
mechanism `firewalls`/`windows_dc`/etc already use. First real member,
`EXANASFAL001` (`192.168.76.19`), added 2026-07-26.

## Open, unresolved

- **Whether `/etc/example-music/nodeinfo.json` survives a TrueNAS
  boot-environment rollback/upgrade** is genuinely unverified — TrueNAS
  keeps its own config in a sqlite DB with boot-environment snapshots; an
  arbitrary file outside that DB may or may not persist the same way it
  does on a plain Debian box.
- **Real per-site dataset/share layout** — `20-storage.yml` creates one
  placeholder dataset only. No NFS/SMB shares configured at all yet.
- **Nothing here has been run against a real TrueNAS box.** `00-rest-bootstrap.yml`
  is new and untested against live middleware; `00-preflight.yml`/
  `10-access.yml`/`20-storage.yml`'s parameter names are confirmed against
  the installed collection's real argspec (`ansible-doc -j
  arensb.truenas.*`), not just its rendered docs — but live behaviour
  against a real middleware daemon is unverified for all four stages.
