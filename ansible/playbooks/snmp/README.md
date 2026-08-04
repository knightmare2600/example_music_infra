# playbooks/snmp/

Phase 1 of Robert's SNMP rollout (2026-08-04, following the site-address work —
`sites.csv`'s `Street`/`PostalCode` columns, commit `01f6d54`): sets `sysLocation`
(standard SNMPv2-MIB OID `.1.3.6.1.2.1.1.6.0`, RFC 1213/3418 — identical across
every vendor, not device-specific) on every `devices.csv` row with
`ConnectionType=snmp` (switches, network printers — ~36 devices as of 2026-08-04,
mostly Cisco/TP-Link/HP) to match that site's real address. GET before SET, only
writes when the value's actually wrong.

Deliberately scoped to exactly one OID — see `tasks/set_syslocation.yml`'s own
header for the full reasoning. `sysContact`/`sysName` are out of scope for now:
no source-of-truth value exists yet for a per-site contact, and `sysName` often
already carries a meaningful vendor-configured value on real hardware that
shouldn't be silently overwritten.

Phase 2 (cross-vendor monitoring via Zabbix, once that exists) is separate and
later — Zabbix's own built-in vendor templates handle OID differences, not
custom MIB parsing here. This directory only ever touches `sysLocation`.

## Files

| File | What it does |
|------|-------------|
| `sysinfo.yml` | Entry point — loads `sites.csv`+`devices.csv`, loops every SNMP-managed device |
| `tasks/set_syslocation.yml` | Per-device include: derive IP, GET current value, SET only if wrong |

## Requires

- **net-snmp tools** (`snmpget`/`snmpset`) on the control node — not installed by
  this playbook. `apt install snmp` (Debian/Ubuntu).
- **`vault_snmp_write_community`** populated with a real value in
  `configs/inventory/group_vars/all/vault.yml` (currently `"CHANGEME"`) — the
  SNMP v2c write community actually configured on these switches. If none is
  configured yet, that has to happen on the switches themselves first — this
  playbook only ever speaks to what's already there, it never configures SNMP
  access itself.

## Quick start

```bash
# Step 1 — install net-snmp tools on the control node
apt install snmp

# Step 2 — set the real SNMP write community
ansible-vault edit configs/inventory/group_vars/all/vault.yml

# Step 3 — dry run against one site first
ansible-playbook playbooks/snmp/sysinfo.yml --ask-vault-pass --check -e snmp_site_filter=FAL

# Step 4 — for real, one site, then everywhere
ansible-playbook playbooks/snmp/sysinfo.yml --ask-vault-pass -e snmp_site_filter=FAL
ansible-playbook playbooks/snmp/sysinfo.yml --ask-vault-pass
```

## Not yet built

- **`sysContact`.** No per-site contact value exists in `sites.csv` yet — add a
  column and extend `set_syslocation.yml`'s allow-list once there's a real value
  to write, following the exact same GET-before-SET pattern.
- **SNMP view/ACL scoping on the devices themselves.** This playbook restricts
  itself in software (one OID, nothing else, ever) — for defence in depth, the
  write community should also be scoped device-side to an SNMP view covering
  only the system group, where the vendor supports it (most managed switches
  do). Not done yet — a device-config task, not something this playbook can do
  over SNMP itself.
- **Live-tested against real hardware.** Confirmed working against the full
  ~36-device set with stubbed `snmpget`/`snmpset` (correct IPs, correct
  addresses, correct idempotent skip/GET/SET/unreachable branches) — not yet
  run against an actual switch. Test one site (`-e snmp_site_filter=FAL`)
  before trusting it unattended.
