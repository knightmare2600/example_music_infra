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
