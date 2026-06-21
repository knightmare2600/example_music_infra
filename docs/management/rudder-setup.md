# Rudder Configuration Management — jukebox.internal

**Document ID:** NET-MGMT-RUDDER-001  
**Classification:** Internal — Network Operations  
**Last Updated:** 2026-03-04  
**Depends on:** NET-AD-DC-001, NET-BUILD-PVE-001, NET-VPN-WG-001

---

> **Architecture note:** The Rudder server (`EXASRVFAL002`) is a dedicated, single-function node. It does not serve files, host other services, or run any workloads beyond Rudder. PVE hypervisor nodes are explicitly exempt from Rudder management — they are infrastructure substrate and are managed via Proxmox's own tooling only.
> 
> **Java note:** The Rudder server runs Java (it is a Scala/Lift web application — this cannot be avoided on the server). The Rudder agent installed on Linux nodes (firewall VMs, Debian servers) is pure C/shell with zero Java dependency. Java never touches any node except `EXASRVFAL002`.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Node Specification and Values](#node-specification-and-values)
3. [Create the VM — EXASRVFAL002](#create-the-vm--exasrvfal002)
4. [Install Debian Trixie](#install-debian-trixie)
5. [Post-Install Base Configuration](#post-install-base-configuration)
6. [Install Rudder Server](#install-rudder-server)
7. [Initial Rudder Configuration](#initial-rudder-configuration)
8. [AD / LDAP Authentication](#ad--ldap-authentication)
9. [Install Rudder Agent — Linux](#install-rudder-agent--linux)
10. [Install Rudder Agent — Windows](#install-rudder-agent--windows)
11. [Relay Servers — ODE and BRK](#relay-servers--ode-and-brk)
12. [Node Groups](#node-groups)
13. [Deploying Packages via Chocolatey](#deploying-packages-via-chocolatey)
14. [Deploying Software Without a Package Manager](#deploying-software-without-a-package-manager)
15. [Cockpit Integration](#cockpit-integration)
16. [Deployment Phasing](#deployment-phasing)
17. [Monitoring and Health Checks](#monitoring-and-health-checks)
18. [Appendix A — Rudder Terminology vs Traditional Terms](#appendix-a--rudder-terminology-vs-traditional-terms)
19. [Appendix B — Agent Exemptions](#appendix-b--agent-exemptions)

---

## Prerequisites

### Infrastructure Prerequisites

| Requirement | Detail | Status |
|-------------|--------|--------|
| AD deployed | `jukebox.internal` domain with FAL as FSMO holder | See NET-AD-DC-001 |
| PVE node EXAPVEFAL001 online | FAL primary hypervisor for VM creation | See NET-BUILD-PVE-001 |
| WireGuard fabric up | FAL ↔ ODE ↔ BRK tunnels established | See NET-VPN-WG-001 |
| DNS working | `jukebox.internal` resolves from all sites | See NET-AD-DC-001 Phase 2 |
| Provisioning server online | `192.168.139.50` serving `create-vm.py` etc | See NET-BUILD-PVE-001 |
| `create-vm.py` deployed | On `EXAPVEFAL001` at `/usr/local/bin/` | See buildsheet-pve.md |

### Software Prerequisites

| Package | Where | Purpose |
|---------|-------|---------|
| `create-vm.py` | EXAPVEFAL001 `/usr/local/bin/` | VM provisioning |
| Debian Trixie ISO or PXE | EXAPVEFAL001 or provisioning server | OS install |
| Rudder 8.x repository | Downloaded during install | Rudder server package |

### Account Prerequisites

| Account | Where needed | Notes |
|---------|-------------|-------|
| Proxmox root or admin | EXAPVEFAL001 | VM creation |
| Local root | EXASRVFAL002 | Post-install configuration |
| Domain Admin | EXADCSFAL001 | AD/LDAP service account creation |
| Rudder admin | EXASRVFAL002 web UI | Created during initial setup |

### Network Prerequisites

The following ports must be open between Rudder server/relays and agents.
These travel over WireGuard for cross-site traffic.

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| 443 | TCP | Agent → Server/Relay | HTTPS — policy fetch, reporting |
| 5309 | TCP | Server → Agent | CFEngine — server-initiated checks |
| 5310 | TCP | Relay → Server | Relay communication |
| 80 | TCP | Agent → Server/Relay | HTTP redirect (redirects to 443) |

```bash
# On EXAFWLFAL001 — allow Rudder ports from all site VPN subnets
# Add to firewallme.sh or equivalent firewall rules

# Agents connecting to Rudder server
ufw allow from 10.0.0.0/8 to any port 443 proto tcp comment "Rudder agents HTTPS"
ufw allow from 10.0.0.0/8 to any port 5309 proto tcp comment "Rudder CFEngine"
```

---

## Node Specification and Values

### EXASRVFAL002 — Rudder Server

| Parameter | Value |
|-----------|-------|
| Hostname | `EXASRVFAL002` |
| FQDN | `EXASRVFAL002.jukebox.internal` |
| Function | Rudder configuration management server |
| OS | Debian GNU/Linux 13 (Trixie) |
| vCPU | 4 |
| RAM | 8 GB |
| Disk | 30 GB (ZFS thin-provisioned on EXAPVEFAL001) |
| IP | `192.168.76.12` |
| Gateway | `192.168.76.1` |
| DNS | `192.168.76.10` (EXADCSFAL001) |
| PVE host | EXAPVEFAL001 |
| VM ID | Assigned by `create-vm.py` |
| Rudder web UI | `https://192.168.76.12/rudder` |
| Rudder version | 8.x (current stable) |

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

## Create the VM — EXASRVFAL002

`create-vm.py` handles VM creation on the Proxmox host. Run this from `EXAPVEFAL001` or from the provisioning server.

```bash
# SSH to EXAPVEFAL001
ssh ansible@192.168.76.5

# Create the VM
python3 /usr/local/bin/create-vm.py --name EXASRVFAL002 --cores 4 --memory 8192 --disk 30 --os debian --ip 192.168.76.12 --gateway 192.168.76.1 --dns 192.168.76.10 --site FAL
```

> Refer to `proxmox/pve-create-vm.md` for full `create-vm.py` parameter reference and troubleshooting. The above uses standard FAL site values from `network-inventory.md`.

### Verify VM Created

```bash
# From EXAPVEFAL001
qm list | grep EXASRVFAL002

# Confirm disk and memory
qm config <VMID>
```

---

## Install Debian Trixie

Attach the Debian Trixie ISO via the Proxmox web UI or API and boot the VM.

### Recommended Partition Layout

| Mount | Size | Filesystem | Notes |
|-------|------|------------|-------|
| `/boot/efi` | 512 MB | FAT32 | EFI system partition |
| `/` | 20 GB | ext4 | Root — Rudder install is ~2GB |
| `/var` | 8 GB | ext4 | Rudder stores reports and DB here — keep separate |
| swap | 2 GB | swap | |

> Keeping `/var` on a separate partition prevents Rudder's report database from filling the root filesystem. If disk space is ever tight, `/var/rudder` is where the data lives.

### Installation Options

- **Software selection:** SSH server + standard system utilities only. No desktop environment, no print server.
- **Root password:** Set a strong temporary password — you will change it after first boot.
- **Create user:** `ansible` — this will be configured for SSH key auth in the post-install step.

---

## Post-Install Base Configuration

These steps mirror the standard Linux node bootstrap. Run as root immediately after first SSH login.

### Change Default Credentials

```bash
# Change root password immediately
passwd root

# Set ansible user password (temporary — key auth will replace this)
passwd ansible
```

### Fetch and Run Bootstrap

The same bootstrap procedure used for other Debian nodes applies here. Fetch the Ansible public key from the provisioning server and configure the standard user environment:

```bash
# Install sudo and curl if not present
apt install -y sudo curl wget

# Create ansible user if installer didn't
id ansible &>/dev/null || useradd -m -s /bin/bash ansible

# Install ansible SSH key
mkdir -p /home/ansible/.ssh
chmod 700 /home/ansible/.ssh
wget -qO - http://192.168.139.50/ansible_sshkey.pub >> /home/ansible/.ssh/authorized_keys
chmod 600 /home/ansible/.ssh/authorized_keys
chown -R ansible:ansible /home/ansible/.ssh

# Passwordless sudo for ansible
echo "ansible ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ansible
chmod 0440 /etc/sudoers.d/ansible

echo "[+] ansible user configured"
```

### Set Hostname and DNS

```bash
hostnamectl set-hostname EXASRVFAL002

# /etc/hosts
cat > /etc/hosts << 'EOF'
127.0.0.1       localhost
127.0.1.1       EXASRVFAL002.jukebox.internal EXASRVFAL002
192.168.76.10   EXADCSFAL001.jukebox.internal EXADCSFAL001
EOF

# DNS — point at the AD DC
cat > /etc/resolv.conf << 'EOF'
domain jukebox.internal
search jukebox.internal
nameserver 192.168.76.10
nameserver 192.168.231.10
EOF

# Prevent dhclient overwriting resolv.conf
echo 'make_resolv_conf() { :; }' > /etc/dhcp/dhclient-enter-hooks.d/nodnsupdate
chmod +x /etc/dhcp/dhclient-enter-hooks.d/nodnsupdate
```

### Update and Install Base Packages

```bash
sudo apt update && apt upgrade -y

sudo apt install -y vim git curl wget htop tree net-tools arping molly-guard ufw fail2ban ca-certificates gnupg lsb-release apt-transport-https
echo "[+] Base packages installed"
```

### Configure UFW

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   comment "SSH"
sudo ufw allow 443/tcp  comment "Rudder HTTPS"
sudo ufw allow 5309/tcp comment "Rudder CFEngine server-to-agent"
sudo ufw allow 5310/tcp comment "Rudder relay"
sudo ufw allow 80/tcp   comment "Rudder HTTP redirect"
sudo ufw --force enable
sudo ufw status verbose
```

### Join the Domain (optional but recommended)

Joining `EXASRVFAL002` to the domain allows AD users to log in via SSH and aligns with the rest of the `jukebox.internal` fleet.

```bash
sudo apt install -y realmd sssd sssd-tools adcli samba-common-bin oddjob oddjob-mkhomedir packagekit

# Discover the domain
realm discover jukebox.internal

# Join — requires Domain Admin credentials
realm join -U Administrator jukebox.internal

# Allow domain users to log in
realm permit --all

# Auto-create home directories on first login
echo "session required pam_mkhomedir.so skel=/etc/skel/ umask=0022" >> /etc/pam.d/common-session

# Verify
realm list
id Administrator@jukebox.internal
```

---

## Install Rudder Server

Rudder provides an official Debian repository. Always install from the official repository rather than building from source.

### Add Rudder Repository

```bash
# Add Rudder GPG key
sudo wget --quiet -O /etc/apt/keyrings/rudder_apt_key.gpg "https://repository.rudder.io/apt/rudder_apt_key.gpg"

# Add repository — Rudder 8.x for Debian Trixie
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/rudder_apt_key.gpg] http://repository.rudder.io/apt/9.0/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/rudder.list

sudo apt update
```

### Install Rudder Server

```bash
sudo apt install -y rudder-server

# This will install:
# - rudder-server (the main application)
# - rudder-webapp (web UI)
# - rudder-inventory-ldap (internal LDAP for node inventory)
# - rudder-reports (PostgreSQL-backed reporting)
# - Java runtime (OpenJDK — server only, not propagated to agents)
# - CFEngine (policy engine)
```

> The install takes several minutes — PostgreSQL and the Rudder database schema are initialised on first install. Watch progress with:
> `journalctl -fu rudder-server`

### Start and Enable Services

```bash
sudo systemctl enable rudder-server
sudo systemctl start  rudder-server

# Check all Rudder services came up
sudo systemctl status rudder-server
sudo systemctl status rudder-agent
sudo systemctl status postgresql

# Wait for web UI to become available (can take 2-3 minutes on first start)
watch -n5 'curl -sk https://localhost/rudder/api/info | python3 -m json.tool 2>/dev/null | head -5'
```

### Verify Installation

```bash
sudo rudder server health
[OK]
```

---

## Initial Rudder Configuration

### First Login

Open a browser and navigate to:
```
https://192.168.76.12/rudder
```

Accept the self-signed certificate (you will replace this with a Let's Encrypt cert — see `proxmox/pve-letsencrypt.md` for the pattern, adapted for an Apache/Nginx frontend rather than Proxmox).

**Default credentials:**

```
sudo rudder server create-user -u admin
Password: *****
Password: User 'admin' added, restarting the Rudder server

Username: admin
Password: admin
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

This is the address agents use to connect — must be correct before enrolling any agents.

### Configure Email (optional)

```
Administration → Settings → Notifications
  SMTP server: <your mail relay>
  From: rudder@jukebox.internal
  To: it-alerts@jukebox.internal
```

---

## AD / LDAP Authentication

Rudder supports LDAP/AD authentication for the web UI. AD is used as the primary auth source with local Rudder accounts as fallback.

> **Service account required:** Create a dedicated read-only AD account for the LDAP bind. Do not use a Domain Admin account for this.

### Create the LDAP Bind Account in AD

```powershell
# Run on EXADCSFAL001
New-ADUser -Name "Rudder LDAP Bind" -SamAccountName "svc_rudder_ldap" -UserPrincipalName "svc_rudder_ldap@jukebox.internal" `
-AccountPassword (ConvertTo-SecureString "RudderBind2026!" -AsPlainText -Force) -PasswordNeverExpires $true -CannotChangePassword $true ` -Enabled $true -Path "OU=Service Accounts,DC=jukebox,DC=example" -Description "Rudder web UI LDAP bind account — read only"

# Grant read access to user objects (default Domain Users already have this)
# No additional permissions needed for a basic bind
Write-Host "[+] svc_rudder_ldap created"
```

### Create Rudder Access Group in AD

```powershell
# Group for Rudder administrators
New-ADGroup -Name "Rudder Admins" -SamAccountName "GRP_Rudder_Admins" -GroupScope Global -GroupCategory Security `
 -Path "OU=IT Groups,DC=jukebox,DC=example" -Description "Members have full admin access to Rudder web UI"

# Add your admin account
Add-ADGroupMember -Identity "GRP_Rudder_Admins" -Members "Administrator"
```

### Configure LDAP in Rudder

Edit `/opt/rudder/etc/rudder-users.xml` to add the LDAP configuration:

```bash
cat > /opt/rudder/etc/rudder-users.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<authentication hash="bcrypt">

  <!--
    Local fallback account — keep this in case AD is unreachable.
    Password is bcrypt hashed. Generate with:
      htpasswd -bnBC 12 "" 'YourPassword' | tr -d ':\n'
  -->
  <user name="admin"
        password="$2y$12$REPLACE_WITH_BCRYPT_HASH"
        role="administrator"/>

  <!--
    LDAP / Active Directory configuration
    Rudder will try AD first; falls back to local accounts above if AD
    is unreachable.
  -->
  <ldap>
    <connection url="ldap://192.168.76.10:389"
                bind-dn="CN=Rudder LDAP Bind,OU=Service Accounts,DC=jukebox,DC=example"
                bind-password="RudderBind2026!"/>

    <search base="DC=jukebox,DC=example"
            filter="(&amp;(objectClass=user)(sAMAccountName={0}))"
            returnedAttribute="sAMAccountName"/>

    <roleMapping>
      <!--
        Map AD group to Rudder role.
        CN= must match the AD group name exactly.
        Available roles: administrator, read_only, workflow, deployer,
                         configuration, validator, compliance
      -->
      <roleMap role="administrator"
               group="CN=GRP_Rudder_Admins,OU=IT Groups,DC=jukebox,DC=example"/>
    </roleMapping>
  </ldap>

</authentication>
EOF

# Restart webapp to pick up changes
systemctl restart rudder-server
```

### Generate bcrypt Hash for Local Admin Password

```bash
# Install apache2-utils for htpasswd
apt install -y apache2-utils

# Generate hash — replace 'YourSecurePassword' with the real password
htpasswd -bnBC 12 "" 'YourSecurePassword' | tr -d ':\n'
# Copy the output (starts with $2y$12$...) into rudder-users.xml above
```

### Verify AD Login

1. Navigate to `https://192.168.76.12/rudder`
2. Log in with an AD account that is a member of `GRP_Rudder_Admins`
3. Verify you land on the dashboard with Administrator role
4. Log out and verify local `admin` account still works as fallback

---

## Install Rudder Agent — Linux

The Linux agent is a lightweight C daemon — no Java, no heavy runtime.
It runs as a background service, contacts the Rudder server every
30 minutes by default, fetches its assigned policies, enforces them,
and sends a compliance report back.

### Via Package Repository (recommended)

```bash
# Run on each Linux node to be managed
# Replace RUDDER_SERVER_IP with 192.168.76.12 (or relay IP for non-FAL sites)

RUDDER_SERVER="192.168.76.12"

# Add Rudder repository (same as server, but install rudder-agent not rudder-server)
wget -qO - https://repository.rudder.io/apt/rudder_apt_key.pub | gpg --dearmor > /usr/share/keyrings/rudder-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/rudder-archive-keyring.gpg] https://repository.rudder.io/apt/8.x/ trixie main" \
 > /etc/apt/sources.list.d/rudder.list

apt update
apt install -y rudder-agent

# Point agent at the Rudder server
rudder agent policy-server $RUDDER_SERVER

# Start and enable
systemctl enable rudder-agent
systemctl start  rudder-agent

# Run first check-in immediately (don't wait 30 minutes)
rudder agent run

echo "[+] Rudder agent installed and running"
echo "[+] Node will appear in Rudder UI under: Node Management → Accept new nodes"
```

### One-liner for Firewall VMs (Debian)

The firewall VMs (`EXAFWL<SITE>001`) run Debian — same procedure as above.
The agent is entirely passive on these nodes (no Java, minimal overhead,
~10MB RAM):

```bash
# Run on each firewall VM
RUDDER_SERVER="192.168.76.12"  # or relay for non-FAL sites

curl -s https://repository.rudder.io/apt/rudder_apt_key.pub | gpg --dearmor > /usr/share/keyrings/rudder-archive-keyring.gpg && \
apt install -y rudder-agent && rudder agent policy-server $RUDDER_SERVER && systemctl enable --now rudder-agent && \
rudder agent run
echo "[+] Agent installed on $(hostname)"
```

### Verify Agent is Running

```bash
# Check service
systemctl status rudder-agent

# Manual policy run with verbose output
rudder agent run -i

# Check last run status
rudder agent info

# Expected output includes:
# Policy server: 192.168.76.12
# Run interval:  30 minutes
# Last run:      <timestamp>
# Compliance:    <percentage>
```

---

## Install Rudder Agent — Windows

### Via Chocolatey (recommended)

Rudder is not currently in the public Chocolatey community repository, so this uses a local package or the Rudder-provided MSI via a choco
script. The cleanest approach for `jukebox.internal` is a GPO-delivered. Chocolatey install using a locally hosted package.

```powershell
# Run as Administrator on each Windows node
# Or deliver via GPO startup script / Rudder technique once bootstrapped

$rudderServer = "192.168.76.12"
$rudderVersion = "8.1.0"  # update to current release
$msiUrl = "https://$rudderServer/rudder/relay-api/shared-files/rudder-agent-$rudderVersion.msi"

# Download MSI from Rudder server's built-in file share
$msiPath = "$env:TEMP\rudder-agent.msi"
Invoke-WebRequest -Uri $msiUrl -OutFile $msiPath -UseBasicParsing

# Silent install — point at Rudder server
Start-Process msiexec.exe -Wait -ArgumentList @(
    "/i", $msiPath,
    "/quiet",
    "/norestart",
    "RUDDER_POLICY_SERVER=$rudderServer"
)

Write-Host "[+] Rudder agent installed"

# Start service
Start-Service rudder-agent
Set-Service rudder-agent -StartupType Automatic

# Run first check-in
& "C:\Program Files\Rudder\bin\rudder.exe" agent run

Write-Host "[+] Agent running — accept node in Rudder UI"
```

### Via Silent MSI (manual, no Chocolatey)

```batch
:: Run as Administrator
:: Download MSI from https://www.rudder.io/download/ or from your Rudder server
msiexec /i rudder-agent-8.x.x.msi /quiet /norestart RUDDER_POLICY_SERVER=192.168.76.12
```

### Verify Windows Agent

```powershell
# Check service
Get-Service rudder-agent | Select-Object Name, Status, StartType

# Check agent info
& "C:\Program Files\Rudder\bin\rudder.exe" agent info

# Force a policy run
& "C:\Program Files\Rudder\bin\rudder.exe" agent run
```

### Accept the Node in the Rudder UI

After the agent runs for the first time it appears in:

```
Node Management → Pending nodes
```

Click the node, verify the hostname and IP are correct, then click **Accept**. The node moves to **All nodes** and will receive policies on the next run interval.

> New nodes do not receive any policies until explicitly accepted. This is intentional — a safety gate against rogue agents.

---

## Relay Servers — ODE and BRK

Relay servers sit between remote agents and the Rudder server. Agents at EU sites connect to the `ODE` relay; NA sites connect to `BRK`. The relay forwards policy requests to `FAL` and aggregates compliance reports back. This reduces WireGuard traffic and means a WAN outage to `FAL` does not immediately break policy enforcement at remote sites (agents cache their last policy).

### Install Relay on ODE/BRK

Run on the designated relay node (a Debian VM at the hub site — e.g. a Debian node at `192.168.126.12` for `ODE`):

```bash
RUDDER_SERVER="192.168.76.12"   # FAL — the root server

# Add repo and install relay package (not rudder-server, not rudder-agent)
wget -qO - https://repository.rudder.io/apt/rudder_apt_key.pub | \
    gpg --dearmor > /usr/share/keyrings/rudder-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/rudder-archive-keyring.gpg] \
    https://repository.rudder.io/apt/8.x/ trixie main" \
    > /etc/apt/sources.list.d/rudder.list

apt update
apt install -y rudder-server-relay

# Point the relay at the root server
rudder agent policy-server $RUDDER_SERVER

systemctl enable --now rudder-agent
rudder agent run

echo "[+] Relay installed — accept in Rudder UI and promote to relay"
```

### Promote to Relay in the Rudder UI

1. Accept the new node in **Node Management → Pending nodes**
2. Navigate to **Node Management → All nodes → <relay node>**
3. Click **Change to relay**
4. Rudder automatically updates routing for nodes assigned to this relay

### Assign Nodes to a Relay

In the Rudder UI:

```
Node Management → All nodes → <node>
  Policy server: <select relay>
```

Or via API:

```bash
# Reassign a node to the ODE relay
# Replace NODE_UUID with the node's Rudder UUID (shown in node details)
# Replace RELAY_UUID with the ODE relay's UUID

curl -s -X POST -H "X-API-Token: <your-api-token>" -H "Content-Type: application/json" -d '{"policyServerId": "RELAY_UUID"}' \
 "https://192.168.76.12/rudder/api/latest/nodes/NODE_UUID"
```

---

## Node Groups

Node groups are how Rudder decides which policies apply to which nodes. Think of them as the equivalent of AD Organisational Units or security groups — you put nodes in groups, attach policies (directives) to groups.

### Create Groups via UI

```
Configuration Management → Groups → Create group
```

### Recommended Group Structure for jukebox.internal

| Group name | Membership criteria | Policies attached |
|------------|--------------------|--------------------|
| `All Windows DCs` | OS = Windows AND hostname starts with EXADCS | AD tools, DC-specific hardening |
| `All Windows Nodes` | OS = Windows | Chocolatey packages, GPO supplements |
| `All Linux Nodes` | OS = Linux | apt packages, baseline config |
| `All Firewall VMs` | hostname starts with EXAFWL | WireGuard health checks, fw config |
| `All FAL Site` | IP in 192.168.76.0/24 | Site-specific policies |
| `All ODE Site` | IP in 192.168.126.0/24 | Site-specific policies |
| `All Managed Nodes` | All nodes (wildcard) | Baseline — applies everywhere |

### Create a Dynamic Group via API

```bash
# Example: group all Windows nodes dynamically by OS
curl -s -X PUT -H "X-API-Token: <your-api-token>" -H "Content-Type: application/json" -d '{
      "displayName": "All Windows Nodes",
      "description": "All Windows domain-joined nodes",
      "dynamic": true,
      "query": {
        "select": "nodeAndPolicyServer",
        "composition": "And",
        "where": [
          { "objectType": "node",
            "attribute": "osName",
            "comparator": "regex",
            "value": ".*Windows.*" }
        ]
      }
    }' "https://192.168.76.12/rudder/api/latest/groups"
```

---

## Deploying Packages via Chocolatey

Rudder manages Windows package deployment through its built-in **Package management** technique combined with Chocolatey as the package manager. You define what should be installed; Rudder enforces it and reports compliance.

### Prerequisites on Windows Nodes

Chocolatey must be installed before Rudder can use it as a package manager. This is a chicken-and-egg bootstrap — install Chocolatey via the Rudder agent's built-in command execution technique, or ensure it is pre-installed via the build sheet.

For jukebox.internal, Chocolatey is installed during the DC build (see `buildsheets/buildsheet-dcs.md`), so it is already present on all managed Windows nodes.

### Create a Package Technique — Notepad++

This is the canonical example: deploy `notepadplusplus.install` via Chocolatey to all Windows nodes.

#### Via the Rudder UI

```
Configuration Management → Techniques → New technique
  Category:    Software
  Name:        Install Notepad++ via Chocolatey
  Description: Ensures Notepad++ is installed on all Windows nodes
```

Or use the built-in **Package management** technique:

```
Configuration Management → Techniques → Package management
  → New directive from this technique

  Directive name: Notepad++ installed
  Package name:   notepadplusplus.install
  Package manager: chocolatey
  Version:        any (latest)
  Action:         present (install if missing)
```

#### Attach to a Group

```
Configuration Management → Rules → New rule
  Name:    Windows - Core packages
  Groups:  All Windows Nodes
  Directives:
    + Notepad++ installed
    + (add other package directives here)
```

#### Via Rudder API

```bash
# Step 1: Create directive from Package management technique
curl -s -X PUT -H "X-API-Token: <your-api-token>" -H "Content-Type: application/json" -d '{
      "displayName": "Notepad++ installed",
      "techniqueName": "packageManagement",
      "techniqueVersion": "1.0",
      "parameters": {
        "package_name": "notepadplusplus.install",
        "package_manager": "chocolatey",
        "package_version": "",
        "package_state": "present"
      }
    }'  "https://192.168.76.12/rudder/api/latest/directives"
```

### Full Windows Core Package Directive

Deploy the standard jukebox.internal Windows package set in one rule:

```
Configuration Management → Rules → Windows - Core packages
  Directives:
    7zip installed              (7zip)
    Notepad++ installed         (notepadplusplus.install)
    Hyper terminal installed    (hyper)
    PuTTY installed             (putty)
    WinSCP installed            (winscp)
    FAR Manager installed       (far)
    PowerShell 7 installed      (pwsh)
```

Each is a separate directive from the Package management technique — one directive per package. This gives you granular compliance reporting (you can see exactly which package failed on which node) rather than one monolithic "packages" directive that passes or fails as a unit.

### Keeping Packages Updated

To enforce a specific version, set the version field in the directive. To always use latest, leave version blank — Rudder will run `choco upgrade <package>` on each agent run if a newer version is available.

> For production nodes where you want controlled updates rather than automatic latest, pin the version and create a change process for version bumps.

---

## Deploying Software Without a Package Manager

Some software is not available via Chocolatey or apt — Bloomberg Terminal is the canonical example. For these, Rudder uses the **File distribution** and **Command execution** techniques to push installers and run them silently.

### Strategy

1. Upload the installer to the Rudder server's shared file space
2. Create a File distribution directive to push it to target nodes
3. Create a Command execution directive to run the installer silently
4. Create a Rule combining both, targeted at the appropriate group
5. Add a compliance check so Rudder knows when the software is actually installed

### Step 1 — Upload Installer to Rudder Shared Files

```bash
# On EXASRVFAL002
# Rudder serves files from /var/rudder/configuration-repository/shared-files/

SHARED_FILES="/var/rudder/configuration-repository/shared-files"
mkdir -p "$SHARED_FILES/software/bloomberg"

# Copy installer (transfer via SCP from wherever you have it)
# scp bloomberg-setup-x.x.x.exe admin@192.168.76.12:/tmp/
cp /tmp/bloomberg-setup-x.x.x.exe "$SHARED_FILES/software/bloomberg/"

# Commit to git (Rudder tracks shared files in git)
cd /var/rudder/configuration-repository
git add shared-files/software/bloomberg/
git commit -m "Add Bloomberg installer"
```

### Step 2 — File Distribution Directive

```
Configuration Management → Techniques → File distribution
  → New directive

  Directive name:     Bloomberg installer
  Source file:        /shared-files/software/bloomberg/bloomberg-setup-x.x.x.exe
  Destination:        C:\Windows\Temp\bloomberg-setup.exe
  Post-copy command:  (leave blank — execution is a separate directive)
```

### Step 3 — Command Execution Directive

```
Configuration Management → Techniques → Command execution
  → New directive

  Directive name:     Install Bloomberg silently
  Command:            C:\Windows\Temp\bloomberg-setup.exe /S /silent /norestart
  Run condition:      Always  (or "if not installed" — see compliance check below)
```

### Step 4 — Compliance Check (Is It Actually Installed?)

Rather than running the installer every agent cycle, add a condition that checks whether Bloomberg is already installed before running it. This uses the **Condition from command** technique:

```
Configuration Management → Techniques → Condition from command
  Condition name:  bloomberg_installed
  Command:         powershell -Command "if (Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | Where-Object DisplayName -like '*Bloomberg*') { exit 0 } else { exit 1 }"
  True if exit code: 0
```

Then in the Command execution directive, set:

```
  Run condition: !bloomberg_installed
  (only run the installer if the condition is false — i.e. not installed)
```

### Step 5 — Combine into a Rule

```
Configuration Management → Rules → New rule
  Name:       Windows - Bloomberg Terminal
  Groups:     <group containing Bloomberg users — e.g. Trading Desks>
  Directives:
    + Bloomberg installer     (file distribution)
    + Install Bloomberg silently (command execution, condition: !bloomberg_installed)
```

### Generic Pattern for Any Non-Packaged Software

```
For any software without a package manager entry:

1. Upload installer to /var/rudder/configuration-repository/shared-files/software/<appname>/
2. File distribution directive → push to C:\Windows\Temp\ or equivalent
3. Condition check → detect if already installed (registry, file existence, etc)
4. Command execution → silent install, conditioned on step 3
5. Rule → target appropriate group
6. Monitor compliance dashboard for failures
```

---

## Cockpit Integration

Cockpit (`cockpit.service`) provides a web-based system management UI for Linux nodes. It runs on port 9090 and gives you a terminal, service management, log viewer, and basic metrics in a browser.

**Rudder and Cockpit coexist without conflict.** They serve completely different purposes — Cockpit is for interactive administration of a single node, Rudder is for policy enforcement across all nodes. There is no port conflict, no service conflict, and no shared component.

### Install Cockpit on EXASRVFAL002

```bash
apt install -y cockpit cockpit-pcp

systemctl enable --now cockpit.socket

# Open port
ufw allow 9090/tcp comment "Cockpit web UI"

echo "[+] Cockpit available at https://192.168.76.12:9090"
```

### Install Cockpit on Firewall VMs

```bash
# Same procedure — lightweight, no conflict with WireGuard or firewallme.sh
apt install -y cockpit
systemctl enable --now cockpit.socket
ufw allow 9090/tcp comment "Cockpit web UI"
```

### Cockpit + AD Authentication

If the node is domain-joined (via `realm join` as above), Cockpit automatically accepts AD credentials. Log in with `JUKEBOX\username` or `username@jukebox.internal`.

> Cockpit will show a Rudder agent running as a service in its Services panel — you can start/stop/restart the agent from the Cockpit UI as well as from the command line. Handy for diagnostics.

---

## Deployment Phasing

### Phase 1 — Rudder Server (now)

| Task | Node | Status |
|------|------|--------|
| Create VM via create-vm.py | EXAPVEFAL001 | [ ] |
| Install Debian Trixie | EXASRVFAL002 | [ ] |
| Post-install base config | EXASRVFAL002 | [ ] |
| Install Rudder server | EXASRVFAL002 | [ ] |
| Initial configuration + admin password changed | EXASRVFAL002 | [ ] |
| AD/LDAP authentication configured | EXASRVFAL002 | [ ] |
| AD login verified | EXASRVFAL002 | [ ] |
| Local admin fallback verified | EXASRVFAL002 | [ ] |
| Cockpit installed | EXASRVFAL002 | [ ] |

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
| Relay installed | EXASRVODE001 (or Debian relay VM) | [ ] |
| Relay promoted in Rudder UI | | [ ] |
| Linux agent installed | EXAFWLODE001 | [ ] |
| Windows agent installed | EXADCSODE001 | [ ] |
| EU spoke nodes pointed at ODE relay | All ODE-hub spokes | [ ] |

### Phase 4 — BRK Hub and Relay

| Task | Node | Status |
|------|------|--------|
| Relay installed | EXASRVBRK001 (or Debian relay VM) | [ ] |
| Relay promoted in Rudder UI | | [ ] |
| Linux agent installed | EXAFWLBRK001 | [ ] |
| Windows agent installed | EXADCSBRK001 | [ ] |
| NA/Pacific spoke nodes pointed at BRK relay | All BRK-hub spokes | [ ] |

### Phase 5 — All Remaining Sites

Roll out agents to all remaining site nodes. Point each agent at its regional relay (`ODE` for `EU`, `BRK` for `NA/Pacific`, direct to `FAL` for `UK` sites).

---

## Monitoring and Health Checks

### Dashboard

The Rudder web UI homepage shows:
- Global compliance percentage (target: 100%)
- Nodes with errors (should be 0)
- Recent policy changes
- Pending nodes waiting for acceptance

### CLI Health Check on Server

```bash
# Overall server status
rudder server status

# Check all agents have reported recently
rudder server check-agents

# View last policy generation
ls -lht /var/rudder/share/ | head -10

# PostgreSQL (report storage) health
sudo -u postgres psql -c "SELECT count(*) FROM ruddersysevents WHERE executionTimeStamp > NOW() - INTERVAL '2 hours';"
```

### Check Agent Compliance from CLI

```bash
# On any managed Linux node
rudder agent info         # last run, policy server, compliance
rudder agent run -i       # force run with verbose output
rudder agent health       # self-diagnostic
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
tail -f /var/log/rudder/agent/agent.log

# Watch for compliance errors
grep -i "error\|repair\|fail" /var/log/rudder/agent/agent.log | tail -20
```

---

## Appendix A — Rudder Terminology vs Traditional Terms

Understanding Rudder's terminology is half the battle. Everything has a specific meaning that maps (roughly) to familiar concepts.

| Rudder Term | Traditional Equivalent | Description |
|-------------|----------------------|-------------|
| **Node** | Managed endpoint / client | Any machine with a Rudder agent — Windows, Linux, whatever |
| **Root server** | Management server | The central Rudder server (`EXASRVFAL002`) |
| **Relay** | Distribution point / secondary server | Intermediate server that forwards policies and aggregates reports for a site |
| **Technique** | Policy template / script template | A reusable, parameterised policy definition. Think of it as a class — you don't use it directly, you instantiate it |
| **Directive** | Policy instance / GPO setting | A Technique with specific values filled in. "Install Notepad++" is a Directive of the "Package management" Technique |
| **Rule** | GPO Link / policy assignment | Binds one or more Directives to one or more Groups. Rules are what actually makes things happen on nodes |
| **Group** | AD OU / security group | A set of nodes, static or dynamic. Dynamic groups use criteria (OS, IP range, hostname pattern) to auto-populate |
| **Inventory** | SCCM Hardware Inventory / WMI | Rudder automatically collects OS, hardware, IP, installed software from each node |
| **Compliance** | GPO compliance / desired state | Percentage of nodes where the actual state matches the defined policy |
| **Repair** | Remediation / configuration drift fix | When Rudder detects a node is out of compliance and fixes it automatically |
| **Audit mode** | Reporting only / monitor mode | Rudder checks compliance but does not remediate — it just reports |
| **Enforce mode** | Active management | Rudder checks AND fixes — this is the normal production mode |
| **Run interval** | GPO refresh interval | How often the agent checks in with the server (default 30 minutes) |
| **Promise** | Desired state declaration | The lowest-level unit in CFEngine (the engine under Rudder) — a statement of what should be true |
| **API token** | Service account password | Used for API access — generate in Administration → API accounts |
| **Shared files** | SYSVOL / software distribution share | Files stored on the Rudder server and distributed to agents — used for software installers etc |
| **Category** | Folder / OU | Organisational grouping for Techniques, Rules, and Groups — cosmetic only |
| **Tag** | Label / metadata | Key-value pairs on nodes and rules for filtering and reporting |
| **Score** | Health rating | Rudder 8.x introduced a node health score based on compliance, inventory age, and error frequency |

### Rudder State Terms

| Rudder State | Meaning |
|-------------|---------|
| `Compliant` | Node matches policy exactly — nothing to do |
| `Repaired` | Node was out of compliance, Rudder fixed it automatically |
| `Error` | Node is out of compliance and Rudder could not fix it |
| `Not applicable` | The policy does not apply to this node (e.g. a Windows policy on a Linux node) |
| `No report` | Agent has not checked in recently — node may be offline |
| `Pending` | New node waiting to be accepted |

---

## Appendix B — Agent Exemptions

The following nodes **must not** have a Rudder agent installed. They are managed by their own tooling and are explicitly outside the scope of Rudder management.

| Node pattern | Reason |
|-------------|--------|
| `EXAPVE*` — all Proxmox VE hypervisors | Managed by Proxmox tooling. Substrate layer — not a managed endpoint. Rudder (and any future chaos monkey implementation) must never touch these nodes. |
| Proxmox cluster quorum nodes | Same as above |

This exemption is permanent. Adding a Rudder agent to a PVE node is not a future roadmap item — it is explicitly out of scope.

---

## Related Documents

| Document | Relationship |
|----------|-------------|
| `bootstrap/ad-dc-wireguard-deployment.md` | AD must be deployed before LDAP auth can be configured |
| `proxmox/pve-create-vm.md` | `create-vm.py` used to provision EXASRVFAL002 |
| `gpo/corporate-livery.md` | Rudder and GPO are complementary — GPO for domain policy, Rudder for package and config management |
| `dfs/dfs-replication.md` | SRV nodes managed by Rudder agents |
| `network-inventory.md` | Node IPs and site assignments |
| `wireguard/wireguard-troubleshooting.md` | Agent-to-server connectivity travels over WireGuard for cross-site nodes |

---

*Internal Use Only — Network Engineering — jukebox.internal*  
*Rudder version: 8.x — https://www.rudder.io/documentation/*
