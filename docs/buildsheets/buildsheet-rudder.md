# Build Sheet — Rudder Configuration Management Node (EXARUDCLD001)

**Document ID:** NET-BUILD-RUDDER-001  
**Classification:** Internal — Network Operations  
**Last Updated:** 2026-03-05  
**Signed off by:** ___________________________  Date: ___________

> **Status: no longer planned.** Robert confirmed (2026-07-30) that Rudder is not in use on the
> live network and rollout is not planned: "we tried this and here's some code if you want it
> but we're not using it." This buildsheet and the automation it describes are kept as reference
> material, not a build-in-progress — see `management/rudder-setup.md` for the fuller note.

---

## Standard Build Reference

### Node Details
```
Hostname : EXARUDCLD001
IP       : 192.168.69.12
Network  : CLD (192.168.69.0/24)
OS       : Debian GNU/Linux 13 (Trixie)
Role     : Rudder root server — configuration management for all sites
```

### Prerequisites
- CLD network reachable (`EXAFWLCLD001` up, WireGuard fabric operational)
- DNS resolving `jukebox.internal` from CLD network
- Ansible user exists with key from the provisioning server (`192.168.139.50` — or `172.16.124.1:8000` at
  Fredericia Havn, see `docs/bootstrap/bootstrapping.md` §4.1a)
- Ports `443`/`5309` (and, for relay/Cockpit use, `5310`/`9090`) open inbound from all site subnets (Rudder agent comms)

### Rudder Installation — automated (`ansible/playbooks/rudder/rudder_server.yml`)

> **Status: historical artefact, not a live path (documented 2026-07-15).** The manual
> apt-get sequence below predates `ansible/playbooks/rudder/rudder_server.yml`, which now
> automates the full install — hostname, static IP, packages, UFW, Rudder install, LDAP
> skeleton, Cockpit, MOTD, sentinel — in one idempotent, twice-run playbook (see
> `ansible/playbooks/rudder/README.md` for the full quick-start). Run from the `ansible/` root:
>
> ```bash
> # First run — install and start Rudder
> ansible-playbook playbooks/rudder/rudder_server.yml \
>   --limit rudder_servers --user root -k --ask-vault-pass
>
> # Second run, after creating an API token via the web UI —
> # configures allowed networks from sites.csv
> ansible-playbook playbooks/rudder/rudder_server.yml \
>   --limit rudder_servers --ask-vault-pass
> ```
>
> The manual procedure below is left as a reference for what the playbook actually does under
> the hood, not a recommended path.

Rudder requires Java. The installer handles this but verify the version
matches the Rudder release requirements before starting.

```bash
# Add Rudder apt repository
echo "deb http://repository.rudder.io/apt/8.0/ $(lsb_release -cs) main" \
    > /etc/apt/sources.list.d/rudder.list

curl -fsSL https://repository.rudder.io/apt/rudder_apt_key.pub \
    | gpg --dearmor -o /etc/apt/trusted.gpg.d/rudder.gpg

apt-get update
apt-get install -y rudder-server

# Start and enable
systemctl enable rudder-server
systemctl start  rudder-server
```

Web UI available at: `https://192.168.69.12/rudder`  
Default credentials: set on first login — store in password manager immediately.

### Post-Install Configuration
- Set the server FQDN: `EXARUDCLD001.jukebox.internal`
- Configure allowed networks — all site `/24` subnets plus CLD `192.168.69.0/24`
- Import existing techniques and rules if migrating (see NET-MGMT-RUDDER-001)
- Verify agent check-in from `EXAANSCLD001` (Ansible control node) as a test node
- **Section 12 (Windows baseline) runs automatically, no manual step needed:**
  `rudder_server.yml` creates a dynamic "Windows Nodes" group (OS type = Windows), pushes two
  real techniques via the Rudder REST API (`exa_windows_security_policy` — Defender/SmartScreen/
  Windows-Update lockdown; `exa_pswindowsupdate`), and creates/updates directives + an "EXA
  Windows baseline" rule binding them together, idempotently on every run. To add a binary to the
  Defender exclusion list: add it to `rudder_windows_excluded_binaries`
  (`group_vars/rudder_servers/main.yml`) and re-run the playbook.

### Rudder Agent Install (on managed nodes)

Automated by `ansible/playbooks/rudder/rudder_onboard.yml` (`--limit <hostname or group>
--ask-vault-pass`). Manual procedure, for reference:

```bash
# On each node to be managed — Debian/Ubuntu
echo "deb http://repository.rudder.io/apt/8.0/ $(lsb_release -cs) main" \
    > /etc/apt/sources.list.d/rudder.list
apt-get update
apt-get install -y rudder-agent

# Point agent at the Rudder server
rudder agent server 192.168.69.12

# Accept node in Rudder web UI or via API
```

### Firewall Rules Required
```
Inbound to EXARUDCLD001:
  22/tcp    — SSH
  80/tcp    — HTTP redirect (to 443)
  443/tcp   — Web UI + agent HTTPS reporting
  5309/tcp  — Rudder agent CFEngine comms (server to agent)
  5310/tcp  — Rudder relay communication
  9090/tcp  — Cockpit web UI

Outbound from EXARUDCLD001:
  Any — for package downloads, git, API calls to managed nodes
```

---

## Build Checklist

| Hostname | Hostname Set | Static IP Set | Ansible User Created + SSH Key Installed from provisioning server (192.168.139.50) | Debian Trixie Installed and Updated | UFW Configured (Ports 22, 80, 443, 5309, 5310, 9090 Open) | Rudder APT Repository Added and Signed | rudder-server Package Installed | rudder-server Service Running and Enabled | FQDN Set to EXARUDCLD001.jukebox.internal | Allowed Networks Configured (All Site /24s + CLD) | Web UI Admin Password Set and Stored in Password Manager | Test Agent Checked In and Accepted | Existing Rules / Techniques Imported | Notes |
|----------|------------------------------|------------------------------------|------------------------------------------------------------|--------------------------------------|-------------------------------------------|----------------------------------------|------------------------------|-------------------------------------------|-------------------------------------------|-----------------------------------------------|--------------------------------------------------|----------------------------------|----------------------------------|------|
| **EXARUDCLD001** | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | Rudder root server |

---

## Related Documents

| Document | Relevance |
|----------|-----------|
| `management/rudder-setup.md` (NET-MGMT-RUDDER-001) | Full Rudder configuration, techniques, and node management |
| `management/Example Music — Keeping Three Ansible Nodes in Sync.md` | Ansible coordination with Rudder |
| `active-directory/ad-dc-wireguard-deployment.md` (NET-AD-DC-001, historical) | WireGuard fabric that Rudder agents communicate over |

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Build engineer | | | |
| Network lead | | | |
| Operations manager | | | |

---

*Internal Use Only — Network Engineering*
