# windows_bootstrap

Bootstraps and configures Windows machines (desktops, laptops, servers).
Ansible port of Join-DomainAndBootstrap.ps1.

## Usage
```
# Full run
ansible-playbook -i inventory/<site>.ini site.yml -e target=<host> --ask-vault-pass

# Single stage
ansible-playbook -i inventory/<site>.ini site.yml -e target=<host> --tags registry --ask-vault-pass

# Skip bootstrap (host already onboarded)
ansible-playbook -i inventory/<site>.ini site.yml -e target=<host> --skip-tags bootstrap --ask-vault-pass
```

## Dependencies
Install galaxy collections first:
```
ansible-galaxy collection install -r requirements.yml
```

## 00-preflight.yml — DNS decision

`00-preflight.yml` automatically determines which DNS servers to configure when
it applies the static IP (via the `EXA-ApplyStaticIP` boot-time scheduled task).
You are not prompted for DNS — the play probes from the control node and decides.

**How it decides (in order):**

| Condition | Primary DNS | Secondary DNS |
|-----------|-------------|---------------|
| Role=DCS AND is_first_dc=yes | BIND9 (`192.168.139.8`) | — |
| Site DC (`.10`) reachable via TCP 389 | site DC `.10` | BIND9 |
| Site DC offline, hub DC reachable | nearest hub DC (FAL/ODE/BRK) | BIND9 |
| No DC reachable anywhere | BIND9 | — |

**Known source of truth:** hub DC IPs come from the `DC` column of
`/etc/example-music/sites.csv`. No IPs are hardcoded in the playbook.

**Order of operations:** probe runs before the SSH connection to the target.
The operator sees the decided DNS in the pre-flight summary before confirming.

**For non-DCS hosts with no site DC yet:** the hub fallback is temporary.
Once `EXADCS<SITE>001` is commissioned, update DNS to `.10` manually or
re-run preflight with `target_ip` left blank (skips the scheduled task;
DNS change must be done through AD or via `Set-DnsClientServerAddress`).
