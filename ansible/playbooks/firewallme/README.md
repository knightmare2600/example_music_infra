# firewallme

Configures Linux firewall appliances (EXAFWL*). Ansible port of firewallme.sh.

## Usage
```
ansible-playbook -i inventory/kge.ini playbooks/firewallme/playbooks/90-firewall.yml \
  -e target=EXAFWLKGE001 --ask-vault-pass
```

## Tags
`firewall`, `preflight`, `interfaces`, `wan`, `wireguard`, `confirm`,
`packages`, `network`, `nftables`, `dnsmasq`, `ssh`, `cockpit`, `finish`
