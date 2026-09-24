# bind9

Configures EXADNSVRK001 as the authoritative BIND9 DNS server for jukebox.internal,
and (2026-09-24) EXADNSFRD001 as a genuine secondary/replica of the same zone.

## Usage

```bash
# Master (VRK) -- default target, unchanged behaviour
ansible-playbook -i ../../configs/inventory playbooks/bind9/bind9-dns.yml --ask-vault-pass

# Master, once a secondary exists -- scopes allow-transfer/notify to it
ansible-playbook -i ../../configs/inventory playbooks/bind9/bind9-dns.yml \
  -e dns_secondary_ip=172.16.124.8 --ask-vault-pass

# Secondary (FRD)
ansible-playbook -i ../../configs/inventory playbooks/bind9/bind9-dns.yml \
  -e target=EXADNSFRD001 -e dns_role=slave \
  -e dns_master_ip=192.168.139.8 -e dns_gateway=172.16.124.2 --ask-vault-pass
```

See `bind9-dns.yml`'s own header comment for the full variable reference --
`dns_master_ip` (slave) and `dns_gateway` (any non-default target) have no safe
default and the playbook's own preflight task fails loudly if either is missing,
rather than guess.

## Plays
- **Play 1** — Full BIND9 server setup (packages, network, config, zones, service).
  Supports either role (`dns_role=master`, the default, or `dns_role=slave`).
- **Play 2** — Zone regeneration from devices.csv (run after adding/changing devices).
  **Master-only, always targets EXADNSVRK001** -- a secondary never generates zone
  content locally, BIND9 pulls and caches it automatically via AXFR/IXFR from the
  master. Never run this against a slave target.

## Tags
`packages`, `network`, `config`, `zones`, `service`, `reload`, `aliases`, `motd`, `zones-full`
