# Build Sheet — Rudder Configuration Management Node (EXASVRCLD003)

**Document ID:** NET-BUILD-RUDDER-001  
**Classification:** Internal — Network Operations  
**Last Updated:** 2026-03-05  
**Signed off by:** ___________________________  Date: ___________

---

## Standard Build Reference

### Node Details
```
Hostname : EXASVRCLD003
IP       : 192.168.139.22
Network  : CLD (192.168.139.0/24)
OS       : Debian GNU/Linux 13 (Trixie)
Role     : Rudder root server — configuration management for all sites
```

### Prerequisites
- CLD network reachable (`EXAFWLCLD001` up, WireGuard fabric operational)
- DNS resolving `jukebox.internal` from CLD network
- Ansible user exists with key from `EXAPRVFAL001` (`192.168.139.50`)
- Port `443` and `5309` open inbound from all site subnets (Rudder agent comms)

### Rudder Installation (Debian)

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

Web UI available at: `https://192.168.139.22/rudder`  
Default credentials: set on first login — store in password manager immediately.

### Post-Install Configuration
- Set the server FQDN: `EXASVRCLD003.jukebox.internal`
- Configure allowed networks — all site `/24` subnets plus CLD `192.168.139.0/24`
- Import existing techniques and rules if migrating (see NET-MGMT-RUDDER-001)
- Verify agent check-in from `EXASVRCLD002` (Ansible node) as a test node

### Rudder Agent Install (on managed nodes)
```bash
# On each node to be managed — Debian/Ubuntu
echo "deb http://repository.rudder.io/apt/8.0/ $(lsb_release -cs) main" \
    > /etc/apt/sources.list.d/rudder.list
apt-get update
apt-get install -y rudder-agent

# Point agent at the Rudder server
rudder agent server 192.168.139.22

# Accept node in Rudder web UI or via API
```

### Firewall Rules Required
```
Inbound to EXASVRCLD003:
  443/tcp   — Web UI + agent HTTPS reporting
  5309/tcp  — Rudder agent CFEngine comms

Outbound from EXASVRCLD003:
  Any — for package downloads, git, API calls to managed nodes
```

---

## Build Checklist

| Hostname | Hostname Set | Static IP Set | Ansible User Created + SSH Key Installed from EXAPRVFAL001 | Debian Trixie Installed and Updated | UFW Configured (Ports 22, 443, 5309 Open) | Rudder APT Repository Added and Signed | rudder-server Package Installed | rudder-server Service Running and Enabled | FQDN Set to EXASVRCLD003.jukebox.internal | Allowed Networks Configured (All Site /24s + CLD) | Web UI Admin Password Set and Stored in Password Manager | Test Agent Checked In and Accepted | Existing Rules / Techniques Imported | Notes |
|----------|------------------------------|------------------------------------|------------------------------------------------------------|--------------------------------------|-------------------------------------------|----------------------------------------|------------------------------|-------------------------------------------|-------------------------------------------|-----------------------------------------------|--------------------------------------------------|----------------------------------|----------------------------------|------|
| **EXASVRCLD003** | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | Rudder root server |

---

## Related Documents

| Document | Relevance |
|----------|-----------|
| `management/rudder-setup.md` (NET-MGMT-RUDDER-001) | Full Rudder configuration, techniques, and node management |
| `management/Example Music — Keeping Three Ansible Nodes in Sync.md` | Ansible coordination with Rudder |
| `bootstrap/ad-dc-wireguard-deployment.md` (NET-AD-DC-001) | WireGuard fabric that Rudder agents communicate over |

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Build engineer | | | |
| Network lead | | | |
| Operations manager | | | |

---

*Internal Use Only — Network Engineering*
