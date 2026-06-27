# Rudder Configuration Management — jukebox.internal

**Document ID:** NET-MGMT-RUDDER-001  
**Classification:** Internal — Network Operations  
**Last Updated:** 2026-06-23  
**Depends on:** NET-AD-DC-001, NET-BUILD-PVE-001, NET-VPN-WG-001

---

> **Architecture note:** The Rudder server (`EXASRVFAL002`) is a dedicated, single-function node. It does not serve files, host other services, or run any workloads beyond Rudder. PVE hypervisor nodes are explicitly exempt from Rudder management — they are infrastructure substrate and are managed via Proxmox's own tooling only.
>
> **Java note:** The Rudder server runs Java (it is a Scala/Lift web application — this cannot be avoided on the server). The Rudder agent installed on Linux nodes (firewall VMs, Debian servers) is pure C/shell with zero Java dependency. Java never touches any node except `EXASRVFAL002`.
>
> **Cloud note:** `EXASRVFAL002` lives in the cloud. The setup script (`rudderme.sh`) handles hostname and static IP configuration with CLD-aware checks. Because the node is cloud-hosted, skip the PVE VM creation section and use whatever provisioning method your cloud provider offers.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Node Specification and Values](#2-node-specification-and-values)
3. [Create the VM — EXASRVFAL002](#3-create-the-vm--exasrvfal002)
4. [Install Debian Trixie](#4-install-debian-trixie)
5. [Post-Install Base Configuration](#5-post-install-base-configuration)
6. [Install Rudder Server](#6-install-rudder-server)
7. [Initial Rudder Configuration](#7-initial-rudder-configuration)
8. [Allowed Networks — Adding All Site Subnets](#8-allowed-networks--adding-all-site-subnets)
9. [AD / LDAP Authentication](#9-ad--ldap-authentication)
10. [Install Rudder Agent — Linux](#10-install-rudder-agent--linux)
11. [Install Rudder Agent — Windows](#11-install-rudder-agent--windows)
12. [Onboarding Nodes — Accepting and Verifying](#12-onboarding-nodes--accepting-and-verifying)
13. [Relay Servers — ODE and BRK](#13-relay-servers--ode-and-brk)
14. [Node Groups](#14-node-groups)
15. [Deploying Packages via Chocolatey](#15-deploying-packages-via-chocolatey)
16. [Deploying Software Without a Package Manager](#16-deploying-software-without-a-package-manager)
17. [Cockpit Integration](#17-cockpit-integration)
18. [Rudder REST API](#18-rudder-rest-api)
19. [Ansible Integration — Registering Nodes via API](#19-ansible-integration--registering-nodes-via-api)
20. [Deployment Phasing](#20-deployment-phasing)
21. [Monitoring and Health Checks](#21-monitoring-and-health-checks)
22. [Appendix A — Rudder Terminology vs Traditional Terms](#appendix-a--rudder-terminology-vs-traditional-terms)
23. [Appendix B — Agent Exemptions](#appendix-b--agent-exemptions)
24. [Appendix C — Related Documents](#appendix-c--related-documents)

---

## 1. Prerequisites

### Infrastructure Prerequisites

| Requirement | Detail | Status |
|-------------|--------|--------|
| AD deployed | `jukebox.internal` domain with FAL as FSMO holder | See NET-AD-DC-001 |
| PVE node EXAPVEFAL001 online | FAL primary hypervisor (on-prem deployments only) | See NET-BUILD-PVE-001 |
| WireGuard fabric up | FAL ↔ ODE ↔ BRK tunnels established | See NET-VPN-WG-001 |
| DNS working | `jukebox.internal` resolves from all sites | See NET-AD-DC-001 Phase 2 |
| Provisioning server online | `192.168.139.50` (on-prem only) | See NET-BUILD-PVE-001 |
| `create-vm.py` deployed | On `EXAPVEFAL001` at `/usr/local/bin/` (on-prem only) | See buildsheet-pve.md |

> For the **cloud-hosted** Rudder server: skip the PVE VM creation step entirely. Provision a Debian Trixie cloud instance with the spec in section 2, then run `rudderme.sh`.

### Software Prerequisites

| Package | Where | Purpose |
|---------|-------|---------|
| `create-vm.py` | EXAPVEFAL001 (on-prem only) | VM provisioning |
| Debian Trixie ISO or PXE | EXAPVEFAL001 or cloud provider | OS install |
| Rudder 8.x repository | Downloaded during install | Rudder server package |
| `rudderme.sh` | This repository | Automated Rudder server setup |
| `sites.csv` | Same directory as `rudderme.sh` | Site/subnet data for allowed-networks population |

### Account Prerequisites

| Account | Where needed | Notes |
|---------|-------------|-------|
| Proxmox root or admin | EXAPVEFAL001 (on-prem only) | VM creation |
| Local root | EXASRVFAL002 | Post-install configuration |
| Domain Admin | EXADCSFAL001 | AD/LDAP service account creation |
| Rudder admin | EXASRVFAL002 web UI | Created during initial setup |

### Network Prerequisites

The following ports must be open between Rudder server/relays and agents.
Cross-site traffic travels over WireGuard.

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| 443 | TCP | Agent → Server/Relay | HTTPS — policy fetch, reporting |
| 5309 | TCP | Server → Agent | CFEngine — server-initiated checks |
| 5310 | TCP | Relay → Server | Relay communication |
| 80 | TCP | Agent → Server/Relay | HTTP redirect (redirects to 443) |

```bash
# On EXAFWLFAL001 — allow Rudder ports from all site VPN subnets
ufw allow from 10.0.0.0/8 to any port 443  proto tcp comment "Rudder agents HTTPS"
ufw allow from 10.0.0.0/8 to any port 5309 proto tcp comment "Rudder CFEngine"
```

---

## 2. Node Specification and Values

### EXASRVFAL002 — Rudder Server (Cloud)

| Parameter | Value |
|-----------|-------|
| Hostname | `EXASRVFAL002` |
| FQDN | `EXASRVFAL002.jukebox.internal` |
| Function | Rudder configuration management server |
| OS | Debian GNU/Linux 13 (Trixie) |
| vCPU | 4 |
| RAM | 8 GB |
| Disk | 30 GB minimum (SSD — PostgreSQL is I/O-sensitive) |
| IP | `192.168.76.12` |
| Gateway | `192.168.76.1` |
| DNS | `192.168.76.10` (EXADCSFAL001) |
| Rudder web UI | `https://192.168.76.12/rudder` |
| Rudder version | 8.x (current stable) |

> **Disk sizing:** Rudder's PostgreSQL report database grows with managed nodes and retention period. The Rudder documentation estimates ~76–114 GB for 500 nodes with 50 directives each. At current `jukebox.internal` scale, 30 GB is adequate; plan to expand `/var` if the node count exceeds ~100.

### EXASRVODE001 — ODE Relay (future)

| Parameter | Value |
|-----------|-------|
| Hostname | `EXASRVODE001` |
| Function | Rudder relay — EU hub |
| IP | `192.168.126.12` |

### EXASRVBRK001 — BRK Relay (future)

| Parameter | Value |
|-----------|-------|
| Hostname | `EXASRVBRK001` |
| Function | Rudder relay — NA hub |
| IP | `192.168.136.12` |

---

## 3. Create the VM — EXASRVFAL002

### On-Premises (PVE)

```bash
# SSH to EXAPVEFAL001
ansible@EXAPVECLD001[~]$ ssh ansible@192.168.76.5

# Create the VM
ansible@EXAPVECLD001[~]$ python3 /usr/local/bin/create-vm.py --name EXASRVFAL002 --cores 4 --memory 8192 --disk 30 --os debian --ip 192.168.76.12 --gateway 192.168.76.1 --dns 192.168.76.10 --site FAL
```

*Refer to `proxmox/pve-create-vm.md` for full `create-vm.py` parameter reference.*

### Cloud (CLD site)

Provision a Debian Trixie instance at your cloud provider with the spec above. Ensure:

- SSH is accessible from your management network before running `rudderme.sh`
- Inbound ports 22, 80, 443, 5309, 5310 are permitted in the cloud security group / firewall rules

`rudderme.sh` handles hostname, static IP, and all Rudder configuration from there.

### Verify VM Created (on-prem only)

```bash
# From EXAPVEFAL001
ansible@EXAPVECLD001[~]$ qm list | grep EXASRVFAL002
ansible@EXAPVECLD001[~]$ qm config <VMID>
```

---

## 4. Install Debian Trixie

Attach the Debian Trixie ISO via the Proxmox web UI, or boot from the cloud provider's installer image.

### Recommended Partition Layout

| Mount | Size | Filesystem | Notes |
|-------|------|------------|-------|
| `/boot/efi` | 512 MB | FAT32 | EFI system partition |
| `/` | 20 GB | ext4 | Root — Rudder install is ~2 GB |
| `/var` | 8 GB | ext4 | Rudder stores reports and DB here — keep separate |
| swap | 2 GB | swap | |

> Keeping `/var` on a separate partition prevents Rudder's report database from filling the root filesystem. `/var/rudder` is where the data lives.

### Installation Options

- **Software selection:** SSH server + standard system utilities only. No desktop environment.
- **Root password:** Set a strong temporary password — change it after first boot.
- **Create user:** `ansible` — will be configured for SSH key auth in the post-install step.

---

## 5. Post-Install Base Configuration

Run as root immediately after first SSH login. `rudderme.sh` handles most of this automatically; this section covers what the script does and provides the manual equivalents.

### Change Default Credentials

```bash
ansible@EXASVRCLD004[~]$ passwd root
ansible@EXASVRCLD004[~]$ passwd ansible
```

### Fetch and Run Bootstrap

```bash
ansible@EXASVRCLD004[~]$ apt install -y sudo curl wget

# Create ansible user if installer did not
ansible@EXASVRCLD004[~]$ id ansible &>/dev/null || useradd -m -s /bin/bash ansible

ansible@EXASVRCLD004[~]$ mkdir -p /home/ansible/.ssh
ansible@EXASVRCLD004[~]$ chmod 700 /home/ansible/.ssh
ansible@EXASVRCLD004[~]$ wget -qO - http://192.168.139.50/ansible_sshkey.pub >> /home/ansible/.ssh/authorized_keys
ansible@EXASVRCLD004[~]$ chmod 600 /home/ansible/.ssh/authorized_keys
ansible@EXASVRCLD004[~]$ chown -R ansible:ansible /home/ansible/.ssh

ansible@EXASVRCLD004[~]$ echo "ansible ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ansible
ansible@EXASVRCLD004[~]$ chmod 0440 /etc/sudoers.d/ansible
```

### Set Hostname and DNS

`rudderme.sh` prompts for these interactively. Manual equivalent:

```bash
ansible@EXASVRCLD004[~]$ hostnamectl set-hostname EXASRVFAL002

ansible@EXASVRCLD004[~]$ cat > /etc/hosts << 'EOF'
127.0.0.1       localhost
127.0.1.1       EXASRVFAL002.jukebox.internal EXASRVFAL002
192.168.76.10   EXADCSFAL001.jukebox.internal EXADCSFAL001
EOF

ansible@EXASVRCLD004[~]$ cat > /etc/resolv.conf << 'EOF'
domain jukebox.internal
search jukebox.internal
nameserver 192.168.76.10
nameserver 192.168.231.10
EOF

# Prevent dhclient overwriting resolv.conf
ansible@EXASVRCLD004[~]$ echo 'make_resolv_conf() { :; }' > /etc/dhcp/dhclient-enter-hooks.d/nodnsupdate
ansible@EXASVRCLD004[~]$ chmod +x /etc/dhcp/dhclient-enter-hooks.d/nodnsupdate
```

### Update and Install Base Packages

```bash
ansible@EXASVRCLD004[~]$ apt update && apt upgrade -y
ansible@EXASVRCLD004[~]$ apt install -y vim git curl wget htop tree net-tools arping molly-guard ufw fail2ban ca-certificates gnupg lsb-release apt-transport-https python3 jq
```

### Configure UFW

```bash
ansible@EXASVRCLD004[~]$ ufw default deny incoming
ansible@EXASVRCLD004[~]$ ufw default allow outgoing
ansible@EXASVRCLD004[~]$ ufw allow 22/tcp   comment "SSH"
ansible@EXASVRCLD004[~]$ ufw allow 443/tcp  comment "Rudder HTTPS"
ansible@EXASVRCLD004[~]$ ufw allow 5309/tcp comment "Rudder CFEngine server-to-agent"
ansible@EXASVRCLD004[~]$ ufw allow 5310/tcp comment "Rudder relay"
ansible@EXASVRCLD004[~]$ ufw allow 80/tcp   comment "Rudder HTTP redirect"
ansible@EXASVRCLD004[~]$ ufw --force enable
ansible@EXASVRCLD004[~]$ ufw status verbose
```

### Configure Static IP

`rudderme.sh` handles this via NetworkManager, with CLD-aware checks (ping + arping) to ensure the target IP is not already in use before assigning it. Manual equivalent:

```bash
# Check the target IP is free before assigning
ansible@EXASVRCLD004[~]$ ping -c1 -W1 192.168.76.12 && echo "IP IN USE — resolve conflict first" && exit 1

ansible@EXASVRCLD004[~]$ nmcli con add type ethernet ifname eth0 con-name rudder-static ipv4.method manual ipv4.addresses "192.168.76.12/24" ipv4.gateway "192.168.76.1" ipv4.dns "192.168.76.10" ipv4.dns-search "jukebox.internal" ipv6.method ignore connection.autoconnect yes connection.autoconnect-priority 100
```

***NB: Static IP takes effect on reboot, or immediately with `nmcli con up rudder-static` if at the local console.***

### Join the Domain (optional but recommended)

```bash
ansible@EXASVRCLD004[~]$ apt install -y realmd sssd sssd-tools adcli samba-common-bin oddjob oddjob-mkhomedir packagekit
ansible@EXASVRCLD004[~]$ realm discover jukebox.internal
ansible@EXASVRCLD004[~]$ realm join -U Administrator jukebox.internal
ansible@EXASVRCLD004[~]$ realm permit --all
ansible@EXASVRCLD004[~]$ echo "session required pam_mkhomedir.so skel=/etc/skel/ umask=0022" >> /etc/pam.d/common-session
ansible@EXASVRCLD004[~]$ realm list
id Administrator@jukebox.internal
```

---

## 6. Install Rudder Server

**Reference:** https://docs.rudder.io/reference/8.3/installation/server/debian.html

Always install from the official Rudder repository. The current stable version for `jukebox.internal` is 8.x.

### Add Rudder Repository

```bash
ansible@EXASVRCLD004[~]$ wget --quiet -O /etc/apt/keyrings/rudder_apt_key.gpg "https://repository.rudder.io/apt/rudder_apt_key.gpg"
ansible@EXASVRCLD004[~]$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/rudder_apt_key.gpg] \
  http://repository.rudder.io/apt/8.x/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/rudder.list
ansible@EXASVRCLD004[~]$ apt update
```

### Install Rudder Server

```bash
ansible@EXASVRCLD004[~]$ apt install -y rudder-server

# This installs:
#   rudder-server         — the main application
#   rudder-webapp         — web UI
#   rudder-inventory-ldap — internal LDAP for node inventory
#   rudder-reports        — PostgreSQL-backed reporting
#   Java runtime          — OpenJDK; server only, not propagated to agents
#   CFEngine              — policy engine
```

*NB: The install takes several minutes — PostgreSQL and the Rudder database schema are initialised on first install. Watch progress: `journalctl -fu rudder-server`*

### Start and Enable Services

```bash
ansible@EXASVRCLD004[~]$ systemctl enable rudder-server
ansible@EXASVRCLD004[~]$ systemctl start  rudder-server

ansible@EXASVRCLD004[~]$ systemctl status rudder-server
ansible@EXASVRCLD004[~]$ systemctl status rudder-agent
ansible@EXASVRCLD004[~]$ systemctl status postgresql

# Wait for web UI (can take 2-3 minutes on first start)
ansible@EXASVRCLD004[~]$ watch -n5 'curl -sk https://localhost/rudder/api/info | python3 -m json.tool 2>/dev/null | head -5'
```

### Verify Installation

```bash
ansible@EXASVRCLD004[~]$ sudo rudder server health
# Expected: [OK]
```

---

## 7. Initial Rudder Configuration

### First Login

Navigate to:

```
https://192.168.76.12/rudder
```

Accept the self-signed certificate (replace with a Let's Encrypt cert later).

### Create Admin User

```bash
ansible@EXASVRCLD004[~]$ sudo rudder server create-user -u admin
# Prompts for password twice; the server restarts automatically
```

**Change the admin password immediately:**

```
Administration → User Management → admin → Change password
```

Or via CLI:

```bash
rudder server change-password admin
```

### Set the Server FQDN

```
Administration → Settings → General
  Rudder server hostname: EXASRVFAL002.jukebox.internal
```

This is the address agents use to connect. Set this before enrolling any agents.

### Configure Email (optional)

```
Administration → Settings → Notifications
  SMTP server: <your mail relay>
  From: rudder@jukebox.internal
  To: it-alerts@jukebox.internal
```

### Generate an API Token

You need an API token for all API operations. Create one now — you will need it in section 8.

```
Administration → API accounts → New API account
  Name:        rudder-automation
  Description: Used by rudderme.sh and Ansible integration
  Token type:  Read/Write
```

Save the token to a password manager. It is only shown once.

---

## 8. Allowed Networks — Adding All Site Subnets

Rudder uses an **Allowed Networks** list to control which subnets agents are permitted to connect from. Agents connecting from a subnet not in this list are refused policy distribution by `cf-serverd` (port 5309) — even if they are accepted nodes.

**Reference:** https://docs.rudder.io/reference/8.3/administration/server.html (Settings → General → Allowed Networks)

### Why This Matters

Every site in `jukebox.internal` has a `/24` subnet (`192.168.x.0/24`). Each of those subnets must be in the Allowed Networks list, otherwise agents at those sites will connect and appear as nodes, but `cf-serverd` will refuse to serve them policies and they will remain non-compliant with "No report" status.

WireGuard tunnel subnets (`10.0.x.0/24`) may also need to be added if agents connect via VPN addresses.

### Via the Web UI (manual, single entry)

```
Administration → Settings → General → Allowed Networks → Add
```

Format: `networkip/mask`, e.g. `192.168.42.0/24`. Add one entry per site subnet.

### Via the Rudder API

The API endpoint `POST /rudder/api/latest/settings/allowed_networks/root` **replaces** the full list (not append). Always include the full list of desired networks in each call.

```bash
RUDDER_URL="https://192.168.76.12"
RUDDER_TOKEN="<your-api-token>"

# View current allowed networks
curl -sk -H "X-API-Token: ${RUDDER_TOKEN}" "${RUDDER_URL}/rudder/api/latest/settings/allowed_networks/root" | python3 -m json.tool

# Set all site subnets in one call
curl -sk -X POST -H "X-API-Token: ${RUDDER_TOKEN}" -H "Content-Type: application/json" -d '{
    "allowed_networks": [
      "192.168.76.0/24",
      "192.168.113.0/24",
      "192.168.126.0/24",
      "192.168.136.0/24",
      "10.0.76.0/24",
      "10.0.113.0/24"
    ]
  }' "${RUDDER_URL}/rudder/api/latest/settings/allowed_networks/root"
```

***NB: For relay servers, substitute the relay node UUID: `allowed_networks/<relay-node-uuid>***

### Automatic Population via rudderme.sh

`rudderme.sh` reads `sites.csv` and constructs the full allowed-networks list from the `subnet` column of every site. It then POSTs the complete list to the Rudder API in one call.

This is the recommended approach — `sites.csv` is the single source of truth for subnets. When you add a new site to `sites.csv` and re-run `rudderme.sh` (or its network-update section), Rudder's allowed-networks list is updated automatically.

```bash
# What rudderme.sh does internally — shown here for transparency
# Reads sites.csv, extracts subnets, builds JSON, POSTs to API

ansible@EXASVRCLD004[~]$ python3 - << 'PYEOF'
import csv, json, subprocess, sys

subnets = []
with open("sites.csv") as f:
  for row in csv.DictReader(f):
    subnet = row.get("subnet", "").strip()
    if subnet:
      # Convert host address to network address e.g. 192.168.76.5 -> 192.168.76.0/24
      parts = subnet.split(".")
      if len(parts) == 4:
        subnets.append(f"{parts[0]}.{parts[1]}.{parts[2]}.0/24")

print(json.dumps({"allowed_networks": list(set(subnets))}, indent=2))
PYEOF
```

---

## 9. AD / LDAP Authentication

Rudder supports LDAP/AD authentication for the web UI. AD is used as the primary auth source with local Rudder accounts as fallback.

***Service account required:** Create a dedicated read-only AD account for the LDAP bind. Never use a Domain Admin account for this.*

### Create the LDAP Bind Account in AD

```powershell
# Run on EXADCSFAL001
New-ADUser -Name "Rudder LDAP Bind" -SamAccountName "svc_rudder_ldap" -UserPrincipalName "svc_rudder_ldap@jukebox.internal" -AccountPassword (ConvertTo-SecureString "RudderBind2026!" -AsPlainText -Force) -PasswordNeverExpires $true  -CannotChangePassword $true -Enabled $true -Path "OU=Service Accounts,DC=jukebox,DC=example" -Description "Rudder web UI LDAP bind account — read only"
```

### Create Rudder Access Group in AD

```powershell
New-ADGroup -Name "Rudder Admins" -SamAccountName "GRP_Rudder_Admins" -GroupScope Global -GroupCategory Security -Path "OU=IT Groups,DC=jukebox,DC=example" -Description "Members have full admin access to Rudder web UI"
Add-ADGroupMember -Identity "GRP_Rudder_Admins" -Members "Administrator"
```

### Configure LDAP in Rudder

```bash
ansible@EXASVRCLD004[~]$ cat > /opt/rudder/etc/rudder-users.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<authentication hash="bcrypt">

  <!--
    Local fallback account — keep this in case AD is unreachable.
    Generate the hash with:
      htpasswd -bnBC 12 "" 'YourPassword' | tr -d ':\n'
  -->
  <user name="admin"
        password="$2y$12$REPLACE_WITH_BCRYPT_HASH"
        role="administrator"/>

  <ldap>
    <connection url="ldap://192.168.76.10:389"
                bind-dn="CN=Rudder LDAP Bind,OU=Service Accounts,DC=jukebox,DC=example"
                bind-password="RudderBind2026!"/>

    <search base="DC=jukebox,DC=example"
            filter="(&amp;(objectClass=user)(sAMAccountName={0}))"
            returnedAttribute="sAMAccountName"/>

    <roleMapping>
      <!--
        Available roles: administrator, read_only, workflow, deployer,
                         configuration, validator, compliance
      -->
      <roleMap role="administrator"
               group="CN=GRP_Rudder_Admins,OU=IT Groups,DC=jukebox,DC=example"/>
    </roleMapping>
  </ldap>

</authentication>
EOF

systemctl restart rudder-server
```

### Generate bcrypt Hash for Local Admin Password

```bash
ansible@EXASVRCLD004[~]$ apt install -y apache2-utils
htpasswd -bnBC 12 "" 'YourSecurePassword' | tr -d ':\n'
# Copy the output (starts with $2y$12$...) into rudder-users.xml above
```

### Verify AD Login

1. Navigate to `https://192.168.76.12/rudder`
2. Log in with an AD account that is a member of `GRP_Rudder_Admins`
3. Verify Administrator role on the dashboard
4. Log out and verify local `admin` account still works as fallback

---

## 10. Install Rudder Agent — Linux

The Linux agent is a lightweight C daemon — no Java, no heavy runtime. It runs every 30 minutes by default, fetches policies, enforces them, and reports compliance back.

### Via Package Repository (recommended)

```bash
RUDDER_SERVER="192.168.76.12"   # or relay IP for non-FAL sites

wget -qO - https://repository.rudder.io/apt/rudder_apt_key.pub | sudo gpg --dearmor > /usr/share/keyrings/rudder-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/rudder-archive-keyring.gpg] \
  https://repository.rudder.io/apt/8.x/ trixie main" > /etc/apt/sources.list.d/rudder.list

ansible@EXASVRCLD004[~]$ apt update
ansible@EXASVRCLD004[~]$ apt install -y rudder-agent

ansible@EXASVRCLD004[~]$ rudder agent policy-server $RUDDER_SERVER

ansible@EXASVRCLD004[~]$ systemctl enable rudder-agent
ansible@EXASVRCLD004[~]$ systemctl start  rudder-agent

# Force first check-in immediately
ansible@EXASVRCLD004[~]$ rudder agent run
```

### One-liner for Firewall VMs (Debian)

```bash
RUDDER_SERVER="192.168.76.12"

curl -s https://repository.rudder.io/apt/rudder_apt_key.pub | gpg --dearmor > /usr/share/keyrings/rudder-archive-keyring.gpg && apt install -y rudder-agent && rudder agent policy-server $RUDDER_SERVER && systemctl enable --now rudder-agent && rudder agent run
```

### Verify Agent is Running

```bash
systemctl status rudder-agent
rudder agent run -i      # verbose policy run
rudder agent info        # last run, policy server, compliance
```

---

## 11. Install Rudder Agent — Windows

### Via MSI

```powershell
# Run as Administrator
$rudderServer = "192.168.76.12"
$rudderVersion = "8.1.0"  # update to current — check https://www.rudder.io/download/
$msiPath = "$env:TEMP\rudder-agent.msi"

Invoke-WebRequest -Uri "https://${rudderServer}/rudder/relay-api/shared-files/rudder-agent-${rudderVersion}.msi" `
  -OutFile $msiPath -UseBasicParsing

Start-Process msiexec.exe -Wait -ArgumentList @(
  "/i", $msiPath, "/quiet", "/norestart",
  "RUDDER_POLICY_SERVER=$rudderServer"
)

Start-Service rudder-agent
Set-Service rudder-agent -StartupType Automatic

& "C:\Program Files\Rudder\bin\rudder.exe" agent run
Write-Host "[+] Agent running — accept node in Rudder UI"
```

### Via Silent MSI (batch)

```batch
msiexec /i rudder-agent-8.x.x.msi /quiet /norestart RUDDER_POLICY_SERVER=192.168.76.12
```

### GPO Delivery (fleet rollout)

For rolling the agent out across all Windows nodes:

1. Place the MSI in `SYSVOL\jukebox.internal\Policies\scripts\`
2. Create a GPO under the correct OU
3. Under `Computer Configuration → Windows Settings → Scripts → Startup`, add a PowerShell startup script

```powershell
# Save as Deploy-RudderAgent.ps1 in SYSVOL
$rudderServer = "192.168.76.12"
$agentPath    = "C:\Program Files\Rudder\bin\rudder.exe"

if (-Not (Test-Path $agentPath)) {
  $msiPath = "\\jukebox.internal\SYSVOL\jukebox.internal\Policies\scripts\rudder-agent.msi"
  Start-Process msiexec.exe -Wait -ArgumentList @(
    "/i", $msiPath, "/quiet", "/norestart",
    "RUDDER_POLICY_SERVER=$rudderServer"
  )
  Start-Service rudder-agent
  Set-Service rudder-agent -StartupType Automatic
}
```

### Verify Windows Agent

```powershell
Get-Service rudder-agent | Select-Object Name, Status, StartType
& "C:\Program Files\Rudder\bin\rudder.exe" agent info
& "C:\Program Files\Rudder\bin\rudder.exe" agent run
```

---

## 12. Onboarding Nodes — Accepting and Verifying

After the agent runs for the first time it appears as a pending node in the Rudder UI. New nodes do not receive any policies until explicitly accepted — this is a deliberate safety gate.

### Manual Acceptance via Web UI

```
Node Management → Pending nodes
```

Click the node. Verify:

- Hostname matches what you expect
- IP address is correct
- OS is correctly detected
- Node is at the correct site

Click **Accept**. The node moves to **All nodes** and receives policies on the next run interval.

### Bulk Acceptance via API

```bash
RUDDER_URL="https://192.168.76.12"
RUDDER_TOKEN="<your-api-token>"

# List all pending nodes
curl -sk -H "X-API-Token: ${RUDDER_TOKEN}" "${RUDDER_URL}/rudder/api/latest/nodes/pending" | python3 -m json.tool

# Accept a specific node by UUID
NODE_UUID="<uuid-from-pending-list>"
curl -sk -X POST -H "X-API-Token: ${RUDDER_TOKEN}" -H "Content-Type: application/json"   -d '{"status": "accepted"}' "${RUDDER_URL}/rudder/api/latest/nodes/pending/${NODE_UUID}"
```

### Accept All Pending Nodes (use with caution)

```bash
# Retrieve all pending UUIDs and accept them in a loop
curl -sk -H "X-API-Token: ${RUDDER_TOKEN}" "${RUDDER_URL}/rudder/api/latest/nodes/pending" | python3 -c "import sys,json; [print(n['id']) for n in json.load(sys.stdin)['data']['nodes']]" | while read uuid; do
  echo "Accepting ${uuid}..."
  curl -sk -X POST -H "X-API-Token: ${RUDDER_TOKEN}" -H "Content-Type: application/json" -d '{"status": "accepted"}'  "${RUDDER_URL}/rudder/api/latest/nodes/pending/${uuid}" | python3 -m json.tool
    done
```

### Verify Node is Receiving Policies

```bash
# On the newly onboarded Linux node — trigger a manual run
rudder agent run -i
# Expect: "Rudder agent run: OK"
```

---

## 13. Relay Servers — ODE and BRK

Relay servers sit between remote agents and the Rudder server. Agents at EU sites connect to the `ODE` relay; NA sites connect to `BRK`. The relay forwards policy requests to `FAL` and aggregates compliance reports back.

### Install Relay on ODE/BRK

```bash
RUDDER_SERVER="192.168.76.12"   # FAL root server

ansible@EXASVRCLD004[~]$ wget -qO - https://repository.rudder.io/apt/rudder_apt_key.pub | sudo gpg --dearmor > /usr/share/keyrings/rudder-archive-keyring.gpg

ansible@EXASVRCLD004[~]$ echo "deb [signed-by=/usr/share/keyrings/rudder-archive-keyring.gpg] \
  https://repository.rudder.io/apt/8.x/ trixie main" > /etc/apt/sources.list.d/rudder.list

ansible@EXASVRCLD004[~]$ apt update
ansible@EXASVRCLD004[~]$ apt install -y rudder-server-relay   # relay package — not rudder-server, not rudder-agent

ansible@EXASVRCLD004[~]$ rudder agent policy-server $RUDDER_SERVER

ansible@EXASVRCLD004[~]$ systemctl enable --now rudder-agent
ansible@EXASVRCLD004[~]$ rudder agent run
```

### Promote to Relay in the Rudder UI

1. Accept the new node in **Node Management → Pending nodes**
2. Navigate to **Node Management → All nodes → <relay node>**
3. Click **Change to relay**
4. Rudder automatically updates routing for nodes assigned to this relay

### Assign Nodes to a Relay

Via UI:

```
Node Management → All nodes → <node> → Policy server: <select relay>
```

Via API:

```bash
curl -sk -X POST -H "X-API-Token: ${RUDDER_TOKEN}" -H "Content-Type: application/json" -d '{"policyServerId": "RELAY_UUID"}' "${RUDDER_URL}/rudder/api/latest/nodes/${NODE_UUID}"
```

---

## 14. Node Groups

Node groups are how Rudder decides which policies apply to which nodes — equivalent to AD Organisational Units. Groups can be static (manually managed) or dynamic (auto-populated by criteria). Dynamic groups are preferred.

### Create Groups via UI

```
Configuration Management → Groups → Create group
```

### Recommended Group Structure for jukebox.internal

| Group name | Membership criteria | Policies attached |
|------------|--------------------|-------------------|
| `All Windows DCs` | OS = Windows AND hostname starts with EXADCS | AD tools, DC-specific hardening |
| `All Windows Nodes` | OS = Windows | Chocolatey packages, GPO supplements |
| `All Linux Nodes` | OS = Linux | apt packages, baseline config |
| `All Firewall VMs` | hostname starts with EXAFWL | WireGuard health checks, fw config |
| `All FAL Site` | IP in 192.168.76.0/24 | Site-specific policies |
| `All ODE Site` | IP in 192.168.126.0/24 | Site-specific policies |
| `All Managed Nodes` | All nodes (wildcard) | Baseline — applies everywhere |

### Create a Dynamic Group via API

```bash
ansible@EXASVRCLD004[~]$ curl -sk -X PUT -H "X-API-Token: ${RUDDER_TOKEN}" -H "Content-Type: application/json" -d '{
    "displayName": "All Windows Nodes",
    "description": "All Windows domain-joined nodes",
    "dynamic": true,
    "query": {
      "select": "nodeAndPolicyServer",
      "composition": "And",
      "where": [
        {
          "objectType": "node",
          "attribute": "osName",
          "comparator": "regex",
          "value": ".*Windows.*"
        }
      ]
    }
  }' "${RUDDER_URL}/rudder/api/latest/groups"
```

---

## 15. Deploying Packages via Chocolatey

Rudder manages Windows package deployment through its built-in **Package management** technique combined with Chocolatey.

### Prerequisites

Chocolatey must be installed on Windows nodes before Rudder can manage packages. For `jukebox.internal`, Chocolatey is installed during the DC build — see `buildsheets/buildsheet-dcs.md`.

### Create a Package Directive

```
Configuration Management → Techniques → Package management
  → New directive

  Directive name:  Notepad++ installed
  Package name:    notepadplusplus.install
  Package manager: chocolatey
  Version:         any (latest)
  Action:          present
```

### Attach to a Group via a Rule

```
Configuration Management → Rules → New rule
  Name:       Windows - Core packages
  Groups:     All Windows Nodes
  Directives:
    + Notepad++ installed
    + 7zip installed (7zip)
    + PuTTY installed (putty)
    + WinSCP installed (winscp)
    + PowerShell 7 installed (pwsh)
    + FAR Manager installed (far)
```

Create one directive per package — this gives granular compliance reporting per package per node.

### Via API

```bash
ansible@EXASVRCLD004[~]$ curl -sk -X PUT -H "X-API-Token: ${RUDDER_TOKEN}" -H "Content-Type: application/json" -d '{
    "displayName": "Notepad++ installed",
    "techniqueName": "packageManagement",
    "techniqueVersion": "1.0",
    "parameters": {
      "package_name": "notepadplusplus.install",
      "package_manager": "chocolatey",
      "package_version": "",
      "package_state": "present"
    }
  }' "${RUDDER_URL}/rudder/api/latest/directives"
```

---

## 16. Deploying Software Without a Package Manager

For software not available via Chocolatey or apt (Bloomberg Terminal is the canonical example), Rudder uses **File distribution** and **Command execution** techniques.

### Strategy

1. Upload the installer to Rudder's shared file space on the server
2. File distribution directive → push installer to target nodes
3. Condition check → detect whether the software is already installed
4. Command execution directive → silent install, conditioned on step 3
5. Rule combining both → target the appropriate group

### Step 1 — Upload Installer

```bash
# On EXASRVFAL002
SHARED_FILES="/var/rudder/configuration-repository/shared-files"
ansible@EXASVRCLD004[~]$ mkdir -p "${SHARED_FILES}/software/bloomberg"
ansible@EXASVRCLD004[~]$ cp /tmp/bloomberg-setup-x.x.x.exe "${SHARED_FILES}/software/bloomberg/"
ansible@EXASVRCLD004[~]$ cd /var/rudder/configuration-repository
ansible@EXASVRCLD004[~]$ git add shared-files/software/bloomberg/
ansible@EXASVRCLD004[~]$ git commit -m "Add Bloomberg installer"
```

### Steps 2–5 — Directives and Rule

```
File distribution directive:
  Source:      /shared-files/software/bloomberg/bloomberg-setup-x.x.x.exe
  Destination: C:\Windows\Temp\bloomberg-setup.exe

Condition from command:
  Name:    bloomberg_installed
  Command: powershell -Command "if (Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | Where-Object DisplayName -like '*Bloomberg*') { exit 0 } else { exit 1 }"
  True if exit code: 0

Command execution directive:
  Command:       C:\Windows\Temp\bloomberg-setup.exe /S /silent /norestart
  Run condition: !bloomberg_installed

Rule:
  Name:       Windows - Bloomberg Terminal
  Groups:     Bloomberg Users
  Directives: Bloomberg installer + Install Bloomberg silently
```

---

## 17. Cockpit Integration

Cockpit provides a web-based system management UI for Linux nodes on port 9090. Rudder and Cockpit coexist without conflict — they serve different purposes.

### Install Cockpit on EXASRVFAL002

```bash
ansible@EXASVRCLD004[~]$ apt install -y cockpit cockpit-pcp
ansible@EXASVRCLD004[~]$ systemctl enable --now cockpit.socket
ansible@EXASVRCLD004[~]$ ufw allow 9090/tcp comment "Cockpit web UI"
```

### Install Cockpit on Firewall VMs

```bash
ansible@EXASVRCLD004[~]$ apt install -y cockpit
ansible@EXASVRCLD004[~]$ systemctl enable --now cockpit.socket
ansible@EXASVRCLD004[~]$ ufw allow 9090/tcp comment "Cockpit web UI"
```

### Cockpit + AD Authentication

If the node is domain-joined (via `realm join`), Cockpit automatically accepts AD credentials. Log in with `JUKEBOX\username` or `username@jukebox.internal`.

---

## 18. Rudder REST API

Rudder provides a full REST API that exposes the same features as the web interface, and several that are not available in the UI at all.

**Reference:** https://docs.rudder.io/api/

### Authentication

All API calls require a token passed in the `X-API-Token` header. Create tokens at:

```
Administration → API accounts → New API account
```

```bash
# Test API access
ansible@EXASVRCLD004[~]$ curl -sk -H "X-API-Token: ${RUDDER_TOKEN}" "https://192.168.76.12/rudder/api/latest/nodes" | python3 -m json.tool
```

### Useful Endpoints

| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/api/latest/nodes` | GET | List all accepted nodes |
| `/api/latest/nodes/pending` | GET | List nodes waiting for acceptance |
| `/api/latest/nodes/pending/<uuid>` | POST | Accept or refuse a pending node |
| `/api/latest/nodes/<uuid>` | GET | Get node details |
| `/api/latest/nodes/<uuid>` | POST | Update node (e.g. assign relay) |
| `/api/latest/nodes/<uuid>` | DELETE | Delete a node |
| `/api/latest/groups` | GET/PUT | List/create node groups |
| `/api/latest/directives` | GET/PUT | List/create directives |
| `/api/latest/rules` | GET/PUT | List/create rules |
| `/api/latest/settings/allowed_networks/root` | GET/POST | View/update allowed networks |
| `/api/latest/nodes/pending` | GET | Pending nodes — used by Ansible integration |
| `/relay-api/1/remote-run/nodes/<uuid>` | POST | Trigger agent run on a specific node |

### Trigger an Immediate Agent Run on a Node

```bash
# Force the agent to run right now (requires port 5309 open from server to node)
ansible@EXASVRCLD004[~]$ curl -sk -X POST -H "X-API-Token: ${RUDDER_TOKEN}" "https://192.168.76.12/rudder/relay-api/1/remote-run/nodes/${NODE_UUID}?keep_output=true"
```

### Get Compliance Summary

```bash
# Global compliance
ansible@EXASVRCLD004[~]$ curl -sk -H "X-API-Token: ${RUDDER_TOKEN}" "https://192.168.76.12/rudder/api/latest/compliance" | python3 -m json.tool

# Per-node compliance
ansible@EXASVRCLD004[~]$ curl -sk -H "X-API-Token: ${RUDDER_TOKEN}" "https://192.168.76.12/rudder/api/latest/compliance/nodes" | python3 -m json.tool
```

---

## 19. Ansible Integration — Registering Nodes via API

Rudder has a REST API and Ansible can call it. The integration pattern is: Ansible onboards a node (installs the agent, starts the service) and then calls the Rudder API to accept it, so the node starts receiving policies without a human clicking through the web UI.

This section documents the pattern. The full Ansible playbook (`rudder_onboard.yml`) is in the playbooks directory.

### Flow

```
Ansible playbook runs against a new node
  → installs rudder-agent
  → sets policy server
  → starts agent service
  → runs rudder agent run
  → waits for node UUID to appear in Rudder pending list
  → calls Rudder API to accept the node
  → (optionally) assigns node to correct relay based on site
  → (optionally) tags node with site and role metadata
```

### API Token for Ansible

Create a dedicated API token for Ansible:

```
Administration → API accounts → New API account
  Name:    ansible-integration
  Role:    Read/Write (needs to accept nodes and update relay assignments)
```

Store the token in Ansible Vault:

```bash
ansible-vault create group_vars/all/rudder_vault.yml
# Add:
#   rudder_api_token: "your-token-here"
#   rudder_url: "https://192.168.76.12"
```

### Ansible Task: Wait for Node to Appear in Rudder

After installing the agent, the node appears in the pending list after its first inventory run. This typically takes 1–3 minutes.

```yaml
# In rudder_onboard.yml — after installing and starting the agent

- name: Get node hostname for Rudder lookup
  set_fact:
    node_fqdn: "{{ ansible_fqdn }}"

- name: Wait for node to appear in Rudder pending list (up to 5 minutes)
  uri:
    url: "{{ rudder_url }}/rudder/api/latest/nodes/pending"
    method: GET
    headers:
      X-API-Token: "{{ rudder_api_token }}"
    validate_certs: false
    return_content: true
  register: rudder_pending_response
  until: >
    rudder_pending_response.json.data.nodes
    | selectattr('hostname', 'equalto', node_fqdn)
    | list | length > 0
  retries: 30
  delay: 10
  delegate_to: localhost

- name: Extract node UUID from pending list
  set_fact:
    rudder_node_uuid: >
      {{ rudder_pending_response.json.data.nodes
        | selectattr('hostname', 'equalto', node_fqdn)
        | map(attribute='id') | first }}
```

### Ansible Task: Accept the Node

```yaml
- name: Accept node in Rudder
  uri:
    url: "{{ rudder_url }}/rudder/api/latest/nodes/pending/{{ rudder_node_uuid }}"
    method: POST
    headers:
      X-API-Token: "{{ rudder_api_token }}"
      Content-Type: "application/json"
    body: '{"status": "accepted"}'
    body_format: json
    validate_certs: false
    status_code: 200
  delegate_to: localhost
  register: rudder_accept_result

- name: Confirm node accepted
  debug:
    msg: "Node {{ node_fqdn }} ({{ rudder_node_uuid }}) accepted in Rudder"
```

### Ansible Task: Assign Node to Correct Relay

```yaml
# relay_uuid is looked up by site code from a variable mapping in group_vars
- name: Assign node to site relay
  uri:
    url: "{{ rudder_url }}/rudder/api/latest/nodes/{{ rudder_node_uuid }}"
    method: POST
    headers:
      X-API-Token: "{{ rudder_api_token }}"
      Content-Type: "application/json"
    body: "{{ {'policyServerId': rudder_relay_uuid[site_code]} | to_json }}"
    body_format: json
    validate_certs: false
    status_code: 200
  delegate_to: localhost
  when: site_code is defined and site_code != 'FAL'
  # FAL nodes connect directly to the root server — no relay assignment needed
```

### group_vars for Relay UUIDs

```yaml
# group_vars/all/rudder.yml
# Rudder relay UUID mapping — get UUIDs from:
#   curl -sk -H "X-API-Token: TOKEN" https://192.168.76.12/rudder/api/latest/nodes
#   (look for nodes where "rudder.roles" includes "rudder-policy-server-relay")

rudder_relay_uuid:
  ODE: "replace-with-ode-relay-uuid"
  BRK: "replace-with-brk-relay-uuid"
  # FAL nodes connect directly to root — no entry needed
```

### Full Onboarding Playbook Skeleton

```yaml
---
# playbooks/rudder/rudder_onboard.yml
# Installs the Rudder agent and registers the node in Rudder via API.
#
# Run after a node has been provisioned and is reachable via Ansible:
#   ansible-playbook playbooks/rudder/rudder_onboard.yml \
#     --limit <hostname or group> --ask-vault-pass
#
# Variables:
#   rudder_server  — Rudder server or relay IP (default: 192.168.76.12)
#   site_code      — Site code from sites.csv (e.g. FAL, ODE, BRK)

- name: Install and register Rudder agent
  hosts: "{{ target_hosts | default('all') }}"
  become: true
  vars_files:
    - ../../group_vars/all/rudder_vault.yml

  vars:
    rudder_server: "192.168.76.12"
    rudder_apt_keyring: /usr/share/keyrings/rudder-archive-keyring.gpg
    rudder_version: "8.x"

  tasks:

    - name: Add Rudder GPG key
      shell: >
        curl -s https://repository.rudder.io/apt/rudder_apt_key.pub
        | gpg --dearmor > {{ rudder_apt_keyring }}
      args:
        creates: "{{ rudder_apt_keyring }}"

    - name: Add Rudder apt repository
      copy:
        dest: /etc/apt/sources.list.d/rudder.list
        content: |
          deb [signed-by={{ rudder_apt_keyring }}]
            https://repository.rudder.io/apt/{{ rudder_version }}/ {{ ansible_distribution_release }} main
        mode: '0644'

    - name: Install rudder-agent
      apt:
        name: rudder-agent
        update_cache: true
        state: present

    - name: Point agent at policy server
      command: "rudder agent policy-server {{ rudder_server }}"
      changed_when: true

    - name: Enable and start rudder-agent
      systemd:
        name: rudder-agent
        enabled: true
        state: started

    - name: Trigger first inventory run
      command: rudder agent run
      changed_when: true

    # --- API registration (runs from localhost against Rudder) ---

    - name: Wait for node to appear in Rudder pending list
      uri:
        url: "{{ rudder_url }}/rudder/api/latest/nodes/pending"
        method: GET
        headers:
          X-API-Token: "{{ rudder_api_token }}"
        validate_certs: false
        return_content: true
      register: rudder_pending_response
      until: >
        rudder_pending_response.json.data.nodes
        | selectattr('hostname', 'equalto', ansible_fqdn)
        | list | length > 0
      retries: 30
      delay: 10
      delegate_to: localhost

    - name: Extract node UUID
      set_fact:
        rudder_node_uuid: >
          {{ rudder_pending_response.json.data.nodes
            | selectattr('hostname', 'equalto', ansible_fqdn)
            | map(attribute='id') | first }}

    - name: Accept node in Rudder
      uri:
        url: "{{ rudder_url }}/rudder/api/latest/nodes/pending/{{ rudder_node_uuid }}"
        method: POST
        headers:
          X-API-Token: "{{ rudder_api_token }}"
          Content-Type: application/json
        body: '{"status": "accepted"}'
        body_format: json
        validate_certs: false
        status_code: 200
      delegate_to: localhost

    - name: Assign to site relay (non-FAL sites only)
      uri:
        url: "{{ rudder_url }}/rudder/api/latest/nodes/{{ rudder_node_uuid }}"
        method: POST
        headers:
          X-API-Token: "{{ rudder_api_token }}"
          Content-Type: application/json
        body: "{{ {'policyServerId': rudder_relay_uuid[site_code]} | to_json }}"
        body_format: json
        validate_certs: false
        status_code: 200
      delegate_to: localhost
      when:
        - site_code is defined
        - site_code != 'FAL'
        - rudder_relay_uuid[site_code] is defined

    - name: Report
      debug:
        msg: >
          Node {{ ansible_fqdn }} (UUID: {{ rudder_node_uuid }})
          accepted in Rudder and assigned to
          {{ 'FAL root server' if site_code == 'FAL' else site_code + ' relay' }}.
```

---

## 20. Deployment Phasing

### Phase 1 — Rudder Server

| Task | Node | Status |
|------|------|--------|
| Provision VM (PVE) or cloud instance | EXAPVEFAL001 / cloud | [ ] |
| Install Debian Trixie | EXASRVFAL002 | [ ] |
| Run `rudderme.sh` (sets hostname, IP, installs Rudder) | EXASRVFAL002 | [ ] |
| Initial configuration + admin password changed | EXASRVFAL002 | [ ] |
| Allowed networks populated from sites.csv | EXASRVFAL002 | [ ] |
| AD/LDAP authentication configured | EXASRVFAL002 | [ ] |
| AD login verified | EXASRVFAL002 | [ ] |
| Local admin fallback verified | EXASRVFAL002 | [ ] |
| Cockpit installed | EXASRVFAL002 | [ ] |
| API token generated for Ansible integration | EXASRVFAL002 | [ ] |

### Phase 2 — FAL Site Agents

| Task | Node | Status |
|------|------|--------|
| Linux agent installed | EXAFWLFAL001 | [ ] |
| Node accepted in Rudder UI | EXAFWLFAL001 | [ ] |
| Windows agent installed | EXADCSFAL001 | [ ] |
| Node accepted in Rudder UI | EXADCSFAL001 | [ ] |
| Windows agent installed | EXASRVFAL001 | [ ] |
| Node accepted in Rudder UI | EXASRVFAL001 | [ ] |
| Node groups created | EXASRVFAL002 | [ ] |
| Core package rule applied and compliant | All Windows FAL | [ ] |

### Phase 3 — ODE Hub and Relay

| Task | Node | Status |
|------|------|--------|
| Relay installed | EXASRVODE001 | [ ] |
| Relay promoted in Rudder UI | | [ ] |
| Linux agent installed | EXAFWLODE001 | [ ] |
| Windows agent installed | EXADCSODE001 | [ ] |
| EU spoke nodes pointed at ODE relay | All ODE-hub spokes | [ ] |

### Phase 4 — BRK Hub and Relay

| Task | Node | Status |
|------|------|--------|
| Relay installed | EXASRVBRK001 | [ ] |
| Relay promoted in Rudder UI | | [ ] |
| Linux agent installed | EXAFWLBRK001 | [ ] |
| Windows agent installed | EXADCSBRK001 | [ ] |
| NA/Pacific spoke nodes pointed at BRK relay | All BRK-hub spokes | [ ] |

### Phase 5 — All Remaining Sites

Roll out agents to all remaining site nodes. Point each agent at its regional relay (`ODE` for EU sites, `BRK` for NA/Pacific, direct to `FAL` for UK sites). Use `rudder_onboard.yml` playbook for automation.

---

## 21. Monitoring and Health Checks

### Dashboard

The Rudder web UI homepage shows:

- Global compliance percentage (target: 100%)
- Nodes with errors (should be 0)
- Recent policy changes
- Pending nodes waiting for acceptance

### CLI Health Check on Server

```bash
# Overall server status
ansible@EXASVRCLD004[~]$ rudder server status

# Check all agents have reported recently
ansible@EXASVRCLD004[~]$ rudder server check-agents

# View last policy generation
ansible@EXASVRCLD004[~]$ ls -lht /var/rudder/share/ | head -10

# PostgreSQL (report storage) health
ansible@EXASVRCLD004[~]$ sudo -u postgres psql -c "SELECT count(*) FROM ruddersysevents WHERE executionTimeStamp > NOW() - INTERVAL '2 hours';"
```

### Check Agent Compliance from CLI

```bash
# On any managed Linux node
ansible@EXASVRCLD004[~]$ rudder agent info        # last run, policy server, compliance
ansible@EXASVRCLD004[~]$ rudder agent run -i      # force run with verbose output
ansible@EXASVRCLD004[~]$ rudder agent health      # self-diagnostic
```

### Key Log Locations

| Log | Location | What it contains |
|-----|----------|-----------------| 
| Agent runs | `/var/log/rudder/agent/` | Policy enforcement output |
| Server | `/var/log/rudder/webapp/` | Web UI and API logs |
| CFEngine | `/var/log/rudder/core/` | Policy engine output |
| Reports | PostgreSQL `rudder` database | Compliance history |

```bash
# Watch agent run in real time
ansible@EXASVRCLD004[~]$ tail -f /var/log/rudder/agent/agent.log

# Watch for compliance errors
ansible@EXASVRCLD004[~]$ grep -i "error\|repair\|fail" /var/log/rudder/agent/agent.log | tail -20
```

---

## Appendix A — Rudder Terminology vs Traditional Terms

| Rudder Term | Traditional Equivalent | Description |
|-------------|----------------------|-------------|
| **Node** | Managed endpoint / client | Any machine with a Rudder agent |
| **Root server** | Management server | The central Rudder server (`EXASRVFAL002`) |
| **Relay** | Distribution point / secondary server | Intermediate server forwarding policies and aggregating reports |
| **Technique** | Policy template | A reusable, parameterised policy definition — you do not use it directly, you instantiate it |
| **Directive** | Policy instance / GPO setting | A Technique with specific values filled in. "Install Notepad++" is a Directive of the "Package management" Technique |
| **Rule** | GPO Link / policy assignment | Binds Directives to Groups. Rules are what actually makes things happen on nodes |
| **Group** | AD OU / security group | A set of nodes, static or dynamic |
| **Inventory** | SCCM Hardware Inventory / WMI | Automatically collected OS, hardware, IP, installed software from each node |
| **Compliance** | Desired state | Percentage of nodes where actual state matches defined policy |
| **Repair** | Remediation | When Rudder detects a node is out of compliance and fixes it automatically |
| **Audit mode** | Reporting only | Rudder checks compliance but does not remediate |
| **Enforce mode** | Active management | Rudder checks AND fixes — normal production mode |
| **Run interval** | GPO refresh interval | How often the agent checks in (default 30 minutes) |
| **API token** | Service account password | Used for API access — generate in Administration → API accounts |
| **Shared files** | SYSVOL / software distribution share | Files stored on the Rudder server and distributed to agents |
| **Score** | Health rating | Node health score based on compliance, inventory age, and error frequency (Rudder 8.x+) |

### Rudder State Terms

| Rudder State | Meaning |
|-------------|---------|
| `Compliant` | Node matches policy exactly — nothing to do |
| `Repaired` | Node was out of compliance, Rudder fixed it automatically |
| `Error` | Node is out of compliance and Rudder could not fix it |
| `Not applicable` | The policy does not apply to this node |
| `No report` | Agent has not checked in recently — node may be offline |
| `Pending` | New node waiting to be accepted |

---

## Appendix B — Agent Exemptions

The following nodes **must not** have a Rudder agent installed.

| Node pattern | Reason |
|-------------|--------|
| `EXAPVE*` — all Proxmox VE hypervisors | Managed by Proxmox tooling. Substrate layer — not a managed endpoint. Rudder must never touch these nodes. |
| Proxmox cluster quorum nodes | Same as above |

This exemption is permanent and is not a future roadmap item.

---

## Appendix C — Related Documents

| Document | Relationship |
|----------|-------------|
| `bootstrap/ad-dc-wireguard-deployment.md` | AD must be deployed before LDAP auth can be configured |
| `proxmox/pve-create-vm.md` | `create-vm.py` used to provision EXASRVFAL002 (on-prem) |
| `gpo/corporate-livery.md` | Rudder and GPO are complementary — GPO for domain policy, Rudder for package and config management |
| `dfs/dfs-replication.md` | SRV nodes managed by Rudder agents |
| `network-inventory.md` | Node IPs and site assignments |
| `wireguard/wireguard-troubleshooting.md` | Agent-to-server connectivity travels over WireGuard for cross-site nodes |

---

*Internal Use Only — Network Engineering — jukebox.internal*  
*Rudder version: 8.x — https://www.rudder.io/documentation/*  
*Rudder API reference: https://docs.rudder.io/api/*
