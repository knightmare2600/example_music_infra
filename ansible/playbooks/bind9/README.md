# bind9

Configures EXASVRCLD001 as the authoritative BIND9 DNS server for jukebox.internal.

## Usage
```
ansible-playbook -i ../../configs/inventory playbooks/bind9/bind9-dns.yml -e target=exasvrcld001 --ask-vault-pass
```

## Plays
- **Play 1** — Full BIND9 server setup (packages, network, config, zones, service)
- **Play 2** — Zone regeneration from devices.csv (run after adding/changing devices)

## Tags
`packages`, `network`, `config`, `zones`, `service`, `reload`, `aliases`, `motd`, `zones-full`
