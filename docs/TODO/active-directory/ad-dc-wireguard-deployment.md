# Active Directory Domain Controller Deployment over WireGuard

---

**Document ID:** NET-AD-DC-001  
**Classification:** Internal — Network Operations  
**Author:** Network Engineering  
**Last Updated:** 2026-03-14  
**Version:** 1.0 — Updated to reflect EXADCSODE001 promotion (2026-03-13/14)  
**Depends on:** NET-VIRT-V2V-001, NET-VIRT-V2V-002, NET-VPN-WG-001

> **⚠️ PARTIAL DRAFT**  
> Phase 4 (FAL promotion) and Phase 5 (FSMO transfer) contain `[PENDING OUTPUT]` blocks to be filled when FAL is built. Phases 6 (ODE), 7, 9, and 10 verified against EXADCSODE001 on 2026-03-14.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Network & WireGuard Topology](#network--wireguard-topology)
4. [Execution Order](#execution-order--read-before-starting)
5. [Phase 1 — WireGuard Tunnel Verification](#phase-1--wireguard-tunnel-verification)
6. [Phase 2 — DNS Verification over the Tunnel](#phase-2--dns-verification-over-the-tunnel)
7. [Phase 3 — Verify Current FSMO State on CPH](#phase-3--verify-current-fsmo-state-on-cph)
8. [Phase 4 — Promote EXADCSFAL001](#phase-4--promote-exadcsfal001)
9. [Phase 5 — Transfer FSMO Roles to FAL](#phase-5--transfer-fsmo-roles-to-fal)
10. [Phase 6 — Promote Remaining Site DCs](#phase-6--promote-remaining-site-dcs)
11. [Phase 7 — AD Sites and Services Configuration](#phase-7--ad-sites-and-services-configuration)
12. [Phase 8 — Global Catalog Configuration](#phase-8--global-catalog-configuration)
13. [Phase 9 — Post-Promotion Verification](#phase-9--post-promotion-verification)
14. [Phase 10 — DFS Preparation (Hooks)](#phase-10--dfs-preparation-hooks)
15. [Connectivity Verification Reference](#connectivity-verification-reference)
16. [Troubleshooting](#troubleshooting)
17. [Output Collection Checklist](#output-collection-checklist)

---

## Introduction

This document covers the end-to-end procedure for:

1. Verifying WireGuard tunnel connectivity between sites before attempting any AD operations
2. Transferring FSMO roles from the current sole DC (`EXADCSCPH001`) to the head-office DC (`EXADCSFAL001`)
3. Promoting new Windows Server DCs at each site and joining them to the `JUKEBOX` domain (`jukebox.internal`)
4. Configuring AD Sites and Services to reflect the physical topology
5. Enabling Global Catalog on regional hub DCs
6. Verifying full AD replication across all sites over WireGuard

The procedure covers both **Windows** (PowerShell/CMD) and **Linux** commands for all connectivity verification steps, so it can be followed from any node on the network.

> **Key principle:** DNS must work over the WireGuard tunnel before any domain join or DC promotion is attempted. Approximately 80% of domain join failures are DNS failures in disguise. Phases 1 and 2 are mandatory — do not skip ahead.

---

## Prerequisites

### Domain

| Item | Value |
|------|-------|
| Forest / Domain | `jukebox.internal` |
| NetBIOS name | `JUKEBOX` |
| Forest functional level | Windows Server 2022 (verify — see Phase 1) |
| Domain functional level | Windows Server 2022 (verify — see Phase 1) |
| Current sole DC | `EXADCSCPH001` |
| Head office DC (FSMO target) | `EXADCSFAL001` |

> **Architecture note:** `example.net`, `example.org`, and `example.com` are **not** AD child domains. All machines join `jukebox.internal` directly. The three example.* names are registered as UPN suffixes only, allowing users to log in as `user@example.net` etc. Internal DNS zones for these names exist on all DCs to prevent them resolving externally to their real public owners. See `ExampleMusic_UPN_DNS_dnsmasq_Procedure.md` for detail.

### IP Addressing Convention

Every site follows the same pattern:

| Address type | Pattern | Example (FAL) | Example (ODE) |
|---|---|---|---|
| Site LAN subnet | `192.168.<octet>.0/24` | `192.168.76.0/24` | `192.168.126.0/24` |
| Site VPN subnet | `10.0.<octet>.0/24` | `10.0.76.0/24` | `10.0.126.0/24` |
| Primary DC — LAN | `192.168.<octet>.10` | `192.168.76.10` | `192.168.126.10` |
| Primary DC — VPN | `10.0.<octet>.10` | `10.0.76.10` | `10.0.126.10` |
| Secondary DC — LAN | `192.168.<octet>.11` | `192.168.76.11` | `192.168.126.11` |
| Additional DCs | `.12` `.13` `.14` | up to 5 DCs per site | — |

### Domain Controllers in Scope

| Hostname | Site | Role | LAN IP | VPN IP | OS |
|---|---|---|---|---|---|
| `EXADCSCPH001` | CPH | Current sole DC — all FSMO (transfers to FAL) | `192.168.231.10` | `10.0.231.10` | Server 2022 |
| `EXADCSFAL001` | FAL | Head office — FSMO target | `192.168.76.10` | `10.0.76.10` | Server 2022 |
| `EXADCSBRK001` | BRK | Americas hub — GC | `192.168.136.10` | `10.0.136.10` | Server 2019+ |
| `EXADCSODE001` | ODE | European hub — GC ✅ **Fully commissioned 2026-03-14** | `192.168.126.10` | `10.0.126.10` | Server 2022 Core |
| `EXADCSEDI001` | EDI | Scotland | `192.168.131.10` | `10.0.131.10` | Server 2016+ |
| `EXADCSGLA001` | GLA | Scotland | `192.168.141.10` | `10.0.141.10` | Server 2016+ |
| `EXADCSNEW001` | NEW | England | `192.168.191.10` | `10.0.191.10` | Server 2016+ |
| `EXADCSMCR001` | MCR | England | `192.168.161.10` | `10.0.161.10` | Server 2016+ |
| `EXADCSLND001` | LND | England | `192.168.20.10` | `10.0.20.10` | Server 2016+ |

> Add rows for additional sites as DCs are provisioned. All `.10` addresses are primary DCs. Secondary DCs follow `.11`–`.14`.

### WireGuard Prerequisites

- All site firewall VMs (`EXAFWL<SITE>001`) must be running and tunnels established
- See `NET-VPN-WG-001` for WireGuard troubleshooting if tunnels are down
- Verify tunnels are up using Phase 1 before proceeding

### Software Prerequisites

On each new DC before promotion:

- [ ] Windows Server installed and activated
- [ ] Static IP configured (LAN IP as per table above)
- [ ] DNS set to `192.168.231.10` (CPH) for FAL promotion; switch to `192.168.76.10` (FAL) for all subsequent DCs in Phase 6
- [ ] **Important:** `example.net`, `example.org`, `example.com` DNS zones must exist on the DC before domain join — otherwise Add-Computer resolves them to Cloudflare and fails. Zones are created as part of `ExampleMusic_UPN_DNS_dnsmasq_Procedure.md`. Verify with `Get-DnsServerZone | Select ZoneName` before Phase 4.
- [ ] Windows Firewall allows AD traffic (or is disabled for initial setup)
- [ ] `AD-Domain-Services` role installed (see Phase 4)
- [ ] Time sync configured — critical for Kerberos (max 5 minute skew)

### Required Credentials

- [ ] Domain Administrator account (`JUKEBOX\Administrator` or equivalent)
- [ ] Local Administrator on each new DC server

---

## Network & WireGuard Topology

### Hub Topology

```
                    ┌─────────────────┐
                    │  EXAFWLFAL001   │
                    │  FAL — Head     │
                    │  192.168.76.0   │
                    │  10.0.76.0      │
                    └────────┬────────┘
                             │ WireGuard tunnels
          ┌──────────────────┼──────────────────┐
          │                  │                  │
┌─────────┴───────┐ ┌────────┴────────┐ ┌───────┴─────────┐
│  EXAFWLODE001   │ │  EXAFWLBRK001   │ │  EXAFWLCPH001   │
│  ODE — EU Hub   │ │  BRK — NA Hub   │ │  CPH (existing) │
│  192.168.126.0  │ │  192.168.136.0  │ │  192.168.231.0  │
│  10.0.126.0     │ │  10.0.136.0     │ │  10.0.231.0     │
└────────┬────────┘ └────────┬────────┘ └─────────────────┘
         │                   │
    EU sites              NA sites
  (MCR,BIR,etc)         (NYC,MIA,etc)

UK sites connect directly to FAL:
  EDI, GLA, ABR, DUN, CLY, PER, MCR, LND, BIR, LIV, etc.
```

### AD Replication Paths

AD replication follows the WireGuard topology:

- **FAL ↔ CPH** — direct tunnel (CPH remains a permanent site DC serving Copenhagen users)
- **FAL ↔ ODE** — direct tunnel (ODE is EU hub)
- **FAL ↔ BRK** — direct tunnel (BRK is NA hub)
- **ODE ↔ EU site DCs** — via ODE hub tunnel
- **BRK ↔ NA site DCs** — via BRK hub tunnel
- **FAL ↔ UK site DCs** — direct from FAL

This will be formalised in AD Sites and Services in Phase 5.

---

> ## Execution Order — Read Before Starting
>
> The phases in this document must be followed **in the order presented**.
> There are no forward jumps or "come back later" steps.
>
> | Step | Phase | Run on | Gate before proceeding |
> |------|-------|--------|------------------------|
> | 1 | Phase 1 — WireGuard Verification | Any Linux host / firewall VM | Tunnels up, all AD ports open |
> | 2 | Phase 2 — DNS Verification | Any host | SRV records resolve over tunnel |
> | 3 | Phase 3 — Verify FSMO on CPH | `EXADCSCPH001` | Baseline confirmed, no changes yet |
> | 4 | Phase 4 — Promote FAL | `EXADCSFAL001` | FAL is a healthy DC, replication working |
> | 5 | Phase 5 — Transfer FSMO to FAL | `EXADCSCPH001` | All five roles confirmed on FAL |
> | 6 | Phase 6 — Promote remaining DCs | Each new DC server | All sites joined, replication healthy |
> | 7 | Phase 7 — AD Sites and Services | `EXADCSFAL001` | Sites, subnets, links created; DCs moved |
> | 8 | Phase 8 — Global Catalog | `EXADCSFAL001` | FAL, ODE, BRK, CPH confirmed as GC |
> | 9 | Phase 9 — Post-Promotion Verification | `EXADCSFAL001` + each DC | dcdiag clean, repadmin 0 errors |
> | 10 | Phase 10 — DFS Preparation | Hub DCs | DFS roles installed, hooks in place |

---

## Phase 1 — WireGuard Tunnel Verification

Before any AD operations, confirm every relevant tunnel is up and passing traffic.

### 1.1 — Check Tunnel Status on Firewall VMs

Run on each firewall VM (`EXAFWL<SITE>001`):

```bash
wg show
systemctl status wg-quick@wg0
ip addr show wg0
```

```
[PENDING OUTPUT]
Command : wg show (on EXAFWLFAL001)
Capture : Full output showing all peers, handshake times, transfer stats
Expected:
  interface: wg0
    public key: <key>
    listening port: 51820

  peer: <ODE-pubkey>
    endpoint: <ODE-WAN-IP>:51820
    allowed ips: 10.0.126.0/24, 192.168.126.0/24
    latest handshake: X seconds ago

  peer: <BRK-pubkey>
    allowed ips: 10.0.136.0/24, 192.168.136.0/24
    latest handshake: X seconds ago

  peer: <CPH-pubkey>
    allowed ips: 10.0.231.0/24, 192.168.231.0/24
    latest handshake: X seconds ago
```

> **Key check:** `latest handshake` must show a recent time (within 2–3 minutes).
> `(never)` means the tunnel is not established — see NET-VPN-WG-001.

### 1.2 — ICMP Ping Verification

#### From Linux

```bash
ping -c 4 10.0.231.10    # CPH
ping -c 4 10.0.126.10    # ODE
ping -c 4 10.0.136.10    # BRK
```

#### From Windows

```powershell
Test-NetConnection -ComputerName 10.0.231.10 -InformationLevel Detailed
Test-NetConnection -ComputerName 10.0.126.10 -InformationLevel Detailed
Test-NetConnection -ComputerName 10.0.136.10 -InformationLevel Detailed
```

```
[PENDING OUTPUT]
Command : ping -c 4 10.0.231.10 && ping -c 4 10.0.126.10 && ping -c 4 10.0.136.10
Capture : Output of all three pings
Expected: 0% packet loss  |  UK-EU ~20-50ms  |  UK-NA ~80-120ms
```

### 1.3 — AD Port Reachability

| Port | Protocol | Service |
|------|----------|---------|
| 53 | TCP+UDP | DNS |
| 88 | TCP+UDP | Kerberos |
| 135 | TCP | RPC Endpoint Mapper |
| 389 | TCP+UDP | LDAP |
| 445 | TCP | SMB / SYSVOL |
| 464 | TCP+UDP | Kerberos password change |
| 636 | TCP | LDAPS |
| 3268 | TCP | Global Catalog LDAP |
| 3269 | TCP | Global Catalog LDAPS |
| 49152–65535 | TCP | RPC dynamic ports |

#### From Linux

```bash
for port in 53 88 135 389 445 464 636 3268; do
    nc -zv -w 2 10.0.231.10 $port 2>&1 | grep -E "open|refused|timed"
done
```

#### From Windows

```powershell
$dc = "10.0.231.10"
foreach ($port in @(53,88,135,389,445,464,636,3268,3269)) {
    $r = Test-NetConnection -ComputerName $dc -Port $port -WarningAction SilentlyContinue
    Write-Host "Port $port : $(if($r.TcpTestSucceeded){'OPEN'}else{'CLOSED/BLOCKED'})"
}
```

```
[PENDING OUTPUT]
Command : PowerShell port test above against 10.0.231.10
Capture : Full output — all ports must show OPEN before proceeding
```

> **✅ Phase 1 complete when:** All tunnels show recent handshakes, ICMP passes to all hub sites, and all AD ports are open.

---

## Phase 2 — DNS Verification over the Tunnel

DNS must be working before any DC promotion or domain join is attempted. Approximately 80% of domain join failures are DNS failures in disguise.

### 2.1 — Verify DC Locator SRV Records

#### From Linux

```bash
dig @10.0.231.10 _ldap._tcp.jukebox.internal SRV
dig @10.0.231.10 _kerberos._tcp.jukebox.internal SRV
dig @10.0.231.10 _ldap._tcp.pdc._msdcs.jukebox.internal SRV
dig @10.0.231.10 _gc._tcp.jukebox.internal SRV
```

#### From Windows

```powershell
Resolve-DnsName -Name "_ldap._tcp.jukebox.internal" -Type SRV -Server 10.0.231.10
Resolve-DnsName -Name "_kerberos._tcp.jukebox.internal" -Type SRV -Server 10.0.231.10
Resolve-DnsName -Name "_ldap._tcp.pdc._msdcs.jukebox.internal" -Type SRV -Server 10.0.231.10
Resolve-DnsName -Name "_gc._tcp.jukebox.internal" -Type SRV -Server 10.0.231.10
nltest /dsgetdc:jukebox.internal /server:10.0.231.10
```

```
[PENDING OUTPUT]
Command : dig @10.0.231.10 _ldap._tcp.jukebox.internal SRV
Capture : Full dig output
Expected:
  ;; ANSWER SECTION:
  _ldap._tcp.jukebox.internal. 600 IN SRV 0 100 389 EXADCSCPH001.jukebox.internal.
  ;; ADDITIONAL SECTION:
  EXADCSCPH001.jukebox.internal. 3600 IN A 192.168.231.10
```

### 2.2 — Forward and Reverse DNS

```bash
dig @10.0.231.10 EXADCSCPH001.jukebox.internal A
dig @10.0.231.10 -x 192.168.231.10
dig @10.0.231.10 -x 10.0.231.10
```

```powershell
Resolve-DnsName -Name "EXADCSCPH001.jukebox.internal" -Server 10.0.231.10
Resolve-DnsName -Name "192.168.231.10" -Server 10.0.231.10
```

```
[PENDING OUTPUT]
Command : dig @10.0.231.10 EXADCSCPH001.jukebox.internal A
Capture : A record resolves to 192.168.231.10
```

### 2.3 — Kerberos Reachability

```bash
# Linux (requires: apt install krb5-user)
kinit Administrator@jukebox.internal && klist
```

```powershell
# Windows
nltest /sc_verify:jukebox.internal /server:EXADCSCPH001
```

### 2.4 — Domain Reachability Summary

```powershell
# One-shot: exercises DNS + Kerberos + LDAP together
nltest /dsgetdc:jukebox.internal /force
```

```
[PENDING OUTPUT]
Command : nltest /dsgetdc:jukebox.internal /force (from EXADCSFAL001)
Capture : Full output
Expected:
  DC: \\EXADCSCPH001
  Address: \\192.168.231.10
  Dom Name: jukebox.internal
  Flags: PDC GC DS LDAP KDC TIMESERV WRITABLE DNS_FOREST ...
  The command completed successfully
```

> **✅ Phase 2 complete when:** SRV records resolve, forward/reverse DNS works,
> Kerberos test passes, `nltest /dsgetdc` locates the domain.

---

## Phase 3 — Verify Current FSMO State on CPH

Record the baseline before making any changes. No modifications in this phase.

> **Run on:** `EXADCSCPH001`

```powershell
# Confirm all five roles are on CPH
netdom query fsmo

# Domain and forest functional levels
Get-ADDomain | Select-Object DomainMode
Get-ADForest | Select-Object ForestMode

# Detailed FSMO breakdown
Get-ADDomain | Select-Object PDCEmulator, RIDMaster, InfrastructureMaster
Get-ADForest | Select-Object SchemaMaster, DomainNamingMaster
```

```
[PENDING OUTPUT]
Command : netdom query fsmo (on EXADCSCPH001)
Capture : Full output
Expected:
  Schema master          EXADCSCPH001.jukebox.internal
  Domain naming master   EXADCSCPH001.jukebox.internal
  PDC                    EXADCSCPH001.jukebox.internal
  RID pool manager       EXADCSCPH001.jukebox.internal
  Infrastructure master  EXADCSCPH001.jukebox.internal
  The command completed successfully.
```

> **✅ Phase 3 complete when:** All five FSMO roles confirmed on CPH,
> functional levels noted. No changes made.

---

## Phase 4 — Promote EXADCSFAL001

FAL must exist as a DC before FSMO roles can be transferred to it. This phase covers FAL only — all other site DCs are promoted in Phase 6.

> **Run on:** `EXADCSFAL001`

### 4.1 — Pre-Promotion Checklist

```powershell
# Static IP set correctly?
Get-NetIPAddress -InterfaceAlias Ethernet* | Select InterfaceAlias, IPAddress, PrefixLength

# DNS pointing at CPH (the only DC right now)?
Get-DnsClientServerAddress | Select InterfaceAlias, ServerAddresses
# Expected: 192.168.231.10

# Time in sync? (Kerberos fails if skew > 5 minutes)
w32tm /query /status
w32tm /stripchart /computer:EXADCSCPH001.jukebox.internal /samples:5 /dataonly

# Domain reachable over WireGuard?
nltest /dsgetdc:jukebox.internal /force

# Computer name correct?
$env:COMPUTERNAME
# Must be EXADCSFAL001 — rename if not:
# Rename-Computer -NewName "EXADCSFAL001" -Restart
```

```
[PENDING OUTPUT]
Command : nltest /dsgetdc:jukebox.internal /force (on EXADCSFAL001 before promotion)
Capture : Domain reachable over WireGuard tunnel
```

### 4.2 — Install AD Domain Services Role

> **Server Core note:** On Server Core, `Add-WindowsCapability` does not work for RSAT or ADDS. Use `Install-WindowsFeature` exclusively. The `ADDSDeployment` module is not available until `AD-Domain-Services` is fully installed — do not attempt to `Import-Module ADDSDeployment` until the feature install reports `Success`.

```powershell
Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools
Get-WindowsFeature AD-Domain-Services
# Must show InstallState: Installed before proceeding
```

```
[PENDING OUTPUT]
Command : Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools
Expected: Success  No  Success  {Active Directory Domain Services, ...}
```

### 4.3 — Promote FAL as Additional DC

> **DSRM password:** The Directory Services Restore Mode password is a local emergency recovery credential, separate from the domain Administrator password. Store it in the password manager before running this command — it cannot be retrieved after the fact.

> **Get-Credential note:** On Server Core over SSH, `Get-Credential` pops an invisible GUI dialog and hangs. Use `Read-Host -AsSecureString` to collect credentials in-console as shown below.

```powershell
Import-Module ADDSDeployment

$DomainCred = New-Object System.Management.Automation.PSCredential(
    'JUKEBOX\Administrator',
    (Read-Host 'JUKEBOX\Administrator password' -AsSecureString)
)
$DSRMPass = Read-Host 'DSRM password (store this in password manager)' -AsSecureString

Install-ADDSDomainController -DomainName "jukebox.internal" -SiteName "Default-First-Site-Name" -InstallDns:$true -CreateDnsDelegation:$false -DatabasePath "C:\Windows\NTDS" -LogPath "C:\Windows\NTDS" -SysvolPath "C:\Windows\SYSVOL" -NoGlobalCatalog:$false -CriticalReplicationOnly:$false -Credential $DomainCred -SafeModeAdministratorPassword $DSRMPass -Force:$true
```

The server reboots automatically after promotion. The SSH session will drop — this is expected.

```
[PENDING OUTPUT]
Command : Install-ADDSDomainController (on EXADCSFAL001)
Capture : Full promotion output
Expected final line: The operation completed successfully.
```

### 4.4 — Post-Promotion Verification for FAL

```powershell
nltest /dsgetdc:jukebox.internal /force
dcdiag /test:advertising
repadmin /showrepl
repadmin /replsummary
dcdiag /test:dns /v
net share | findstr SYSVOL
```

```bash
# From Linux — FAL should now appear in DNS
dig @10.0.231.10 EXADCSFAL001.jukebox.internal A
nc -zv 10.0.76.10 389
nc -zv 10.0.76.10 88
```

```
[PENDING OUTPUT]
Command : repadmin /replsummary (on EXADCSFAL001 after promotion)
Expected: CPH and FAL listed, 0 failures, recent timestamps
```

> **✅ Phase 4 complete when:** FAL promoted, replication from CPH confirmed
> healthy, SYSVOL shared, SRV records registered.

---

## Phase 5 — Transfer FSMO Roles to FAL

FAL is now a healthy DC. Transfer all five FSMO roles from CPH to FAL.

> **Run on:** `EXADCSCPH001`

> **Transfer vs Seize:** Always transfer while the current holder is online.
> Seize is for disaster recovery only when the holder is permanently lost.

### 5.1 — Transfer Roles

```powershell
# Transfer one at a time (recommended — verify after each)
# or all five at once if you are confident replication is healthy

Move-ADDirectoryServerOperationMasterRole -Identity "EXADCSFAL001" -OperationMasterRole PDCEmulator

Move-ADDirectoryServerOperationMasterRole -Identity "EXADCSFAL001" -OperationMasterRole RIDMaster

Move-ADDirectoryServerOperationMasterRole -Identity "EXADCSFAL001" -OperationMasterRole InfrastructureMaster

# Schema Master requires Schema Admins group membership
Move-ADDirectoryServerOperationMasterRole -Identity "EXADCSFAL001" -OperationMasterRole SchemaMaster

Move-ADDirectoryServerOperationMasterRole -Identity "EXADCSFAL001" -OperationMasterRole DomainNamingMaster
```

Or all five at once:

```powershell
Move-ADDirectoryServerOperationMasterRole -Identity "EXADCSFAL001" -OperationMasterRole PDCEmulator,RIDMaster,InfrastructureMaster,SchemaMaster,DomainNamingMaster
```

### 5.2 — Verify Transfer

```powershell
# Run on EXADCSFAL001
netdom query fsmo
```

```
[PENDING OUTPUT]
Command : netdom query fsmo (on EXADCSFAL001 after transfer)
Expected:
  Schema master          EXADCSFAL001.jukebox.internal
  Domain naming master   EXADCSFAL001.jukebox.internal
  PDC                    EXADCSFAL001.jukebox.internal
  RID pool manager       EXADCSFAL001.jukebox.internal
  Infrastructure master  EXADCSFAL001.jukebox.internal
  The command completed successfully.
```

### 5.3 — CPH Post-Transfer State

CPH carries on permanently as a normal site DC. Nothing further to do.

| Attribute | Value |
|---|---|
| Still a DC? | ✅ Yes — permanently |
| Serves CPH users? | ✅ Yes |
| Holds FSMO roles? | ❌ No — transferred to FAL |
| Global Catalog? | ✅ Yes — keep enabled |
| DNS? | ✅ Yes — AD-integrated replica |
| Replication partner | FAL (direct, cost 10) |

> **Note:** Until Phase 7 (Sites and Services), CPH clients may authenticate against FAL rather than CPH. Harmless but wastes tunnel bandwidth. Phase 7 corrects this by associating the CPH subnet with the CPH site.

> **✅ Phase 5 complete when:** All five FSMO roles confirmed on FAL.

---

## Phase 6 — Promote Remaining Site DCs

With FAL holding all FSMO roles, promote DCs at all remaining sites.
Hub DCs (`ODE`, `BRK`) ***MUST*** be promoted before their spoke sites.

**Recommended promotion order:**
1. `EXADCSODE001` — EU hub
2. `EXADCSBRK001` — NA hub
3. All remaining site DCs in any order

> **Run on:** Each new DC server in turn.
> **DNS:** Primary `192.168.76.10` (FAL), secondary `192.168.231.10` (CPH).

### 6.1 — Pre-Promotion Checklist (Per DC)

```powershell
# DNS points at FAL (primary)?
Get-DnsClientServerAddress | Select InterfaceAlias, ServerAddresses

# Domain reachable?
nltest /dsgetdc:jukebox.internal /force

# Time in sync?
w32tm /stripchart /computer:EXADCSFAL001.jukebox.internal /samples:5 /dataonly

# Computer name correct?
$env:COMPUTERNAME
```

### 6.2 — Install Role and Promote (Per DC)

> See Phase 4.2/4.3 notes on Server Core and credential collection — the same applies here.

```powershell
Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools
# Verify InstallState: Installed before continuing
Get-WindowsFeature AD-Domain-Services

Import-Module ADDSDeployment

$DomainCred = New-Object System.Management.Automation.PSCredential(
    'JUKEBOX\Administrator',
    (Read-Host 'JUKEBOX\Administrator password' -AsSecureString)
)
$DSRMPass = Read-Host 'DSRM password (store in password manager)' -AsSecureString

Install-ADDSDomainController -DomainName "jukebox.internal" -SiteName "Default-First-Site-Name" -InstallDns:$true -CreateDnsDelegation:$false -DatabasePath "C:\Windows\NTDS" -LogPath "C:\Windows\NTDS" -SysvolPath "C:\Windows\SYSVOL" -NoGlobalCatalog:$false -CriticalReplicationOnly:$false -Credential $DomainCred -SafeModeAdministratorPassword $DSRMPass -Force:$true
```

### 6.3 — Post-Promotion Verification (Per DC)

```powershell
nltest /dsgetdc:jukebox.internal /force
dcdiag /test:advertising
repadmin /showrepl
dcdiag /test:dns /v
net share | findstr SYSVOL
```

```
[PENDING OUTPUT]
Command : repadmin /replsummary (on EXADCSFAL001 after all DCs promoted)
Expected: All DCs listed, 0 failures, recent replication timestamps
```

> **✅ Phase 6 complete when:** All site DCs promoted and replication confirmed healthy between all of them and FAL.

---

## Phase 7 — AD Sites and Services Configuration

AD Sites and Services tells the DC locator which DC is closest to each client. Without it every client hits `Default-First-Site-Name` regardless of location, and replication ignores the WireGuard hub topology.

All of Phase 7 is handled by a single idempotent script. Run it once; re-run safely at any time — it skips objects that already exist.

> **Run on:** `EXADCSFAL001`

### 7.1 — Configure-ADSites.ps1

**Usage:**

```powershell
# Preview — no changes made
.\Configure-ADSites.ps1 -WhatIf

# Full run
.\Configure-ADSites.ps1

# Move DCs into correct sites (run after Phase 6 is complete)
.\Configure-ADSites.ps1 -MoveDCs

# Add a single new site without touching existing config
.\Configure-ADSites.ps1 -Sites MCR
```

**Script:**

```powershell
<#
.SYNOPSIS
    Configure AD Sites, Subnets and Site Links for jukebox.internal

.DESCRIPTION
    Creates AD replication sites, LAN and VPN subnets, and site links
    that mirror the WireGuard hub topology. Idempotent — skips objects
    that already exist. Use -WhatIf to preview without making changes.

    Topology:
      FAL = UK head office hub (UK sites connect here)
      ODE = EU hub             (EU sites connect here; ODE links to FAL)
      BRK = NA hub             (NA/Pacific sites connect here; BRK links to FAL)
      CPH = permanent site DC  (direct link to FAL, cost 10)

.PARAMETER Sites
    Optional subset of site codes to process. Default = all.

.PARAMETER MoveDCs
    After creating sites, move each DC into its correct site.
    Silently skips DCs that do not yet exist in AD.

.NOTES
    Document : NET-AD-DC-001 Phase 7
    Run on   : EXADCSFAL001
    Requires : ActiveDirectory PowerShell module
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [string[]] $Sites   = @(),
    [switch]   $MoveDCs
)

Import-Module ActiveDirectory -ErrorAction Stop

# =============================================================================
# SITE DATA TABLE
#
# Hub   = parent hub site for the spoke link back to hub
#         $null means "this is a hub — no spoke link, see $HubLinks below"
# Cost  = AD replication site link cost (lower = preferred)
# Freq  = replication frequency in minutes
# DCs   = DC hostnames used by -MoveDCs
# =============================================================================

$SiteData = [ordered]@{

    # ── Hubs ─────────────────────────────────────────────────────────────────
    FAL = @{ LAN="192.168.76.0/24";  VPN="10.0.76.0/24";
             Hub=$null; Cost=$null; Freq=$null
             DCs=@("EXADCSFAL001","EXADCSFAL002") }

    ODE = @{ LAN="192.168.126.0/24"; VPN="10.0.126.0/24";
             Hub=$null; Cost=$null; Freq=$null
             DCs=@("EXADCSODE001") }

    BRK = @{ LAN="192.168.136.0/24"; VPN="10.0.136.0/24";
             Hub=$null; Cost=$null; Freq=$null
             DCs=@("EXADCSBRK001") }

    # ── CPH — direct to FAL ──────────────────────────────────────────────────
    CPH = @{ LAN="192.168.231.0/24"; VPN="10.0.231.0/24";
             Hub="FAL"; Cost=10; Freq=15
             DCs=@("EXADCSCPH001") }

    # ── UK sites — all connect directly to FAL ───────────────────────────────
    EDI = @{ LAN="192.168.131.0/24"; VPN="10.0.131.0/24"; Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSEDI001") }
    GLA = @{ LAN="192.168.141.0/24"; VPN="10.0.141.0/24"; Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSGLA001") }
    ABR = @{ LAN="192.168.224.0/24"; VPN="10.0.224.0/24"; Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSABR001") }
    MCR = @{ LAN="192.168.161.0/24"; VPN="10.0.161.0/24"; Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSMCR001") }
    LND = @{ LAN="192.168.20.0/24";  VPN="10.0.20.0/24";  Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSLND001") }
    BIR = @{ LAN="192.168.121.0/24"; VPN="10.0.121.0/24"; Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSBIR001") }
    LIV = @{ LAN="192.168.151.0/24"; VPN="10.0.151.0/24"; Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSLIV001") }
    NEW = @{ LAN="192.168.191.0/24"; VPN="10.0.191.0/24"; Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSNEW001") }
    SHE = @{ LAN="192.168.114.0/24"; VPN="10.0.114.0/24"; Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSSHE001") }
    HUL = @{ LAN="192.168.148.0/24"; VPN="10.0.148.0/24"; Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSHUL001") }
    COV = @{ LAN="192.168.247.0/24"; VPN="10.0.247.0/24"; Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSCOV001") }
    HAL = @{ LAN="192.168.142.0/24"; VPN="10.0.142.0/24"; Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSHAL001") }

    # ── EU sites — all connect via ODE ───────────────────────────────────────
    MUN = @{ LAN="192.168.189.0/24"; VPN="10.0.189.0/24"; Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSMUN001") }
    BON = @{ LAN="192.168.228.0/24"; VPN="10.0.228.0/24"; Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSBON001") }
    BER = @{ LAN="192.168.113.0/24"; VPN="10.0.113.0/24"; Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSBER001") }
    OSL = @{ LAN="192.168.47.0/24";  VPN="10.0.47.0/24";  Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSOSL001") }
    GOT = @{ LAN="192.168.46.0/24";  VPN="10.0.46.0/24";  Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSGOT001") }
    MIL = @{ LAN="192.168.39.0/24";  VPN="10.0.39.0/24";  Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSMIL001") }
    AMS = @{ LAN="192.168.31.0/24";  VPN="10.0.31.0/24";  Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSAMS001") }
    VIE = @{ LAN="192.168.78.0/24";  VPN="10.0.78.0/24";  Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSVIE001") }
    FAX = @{ LAN="192.168.TBC.0/24"; VPN="10.0.TBC.0/24"; Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSFAX001") }
    KGE = @{ LAN="192.168.TBC.0/24"; VPN="10.0.TBC.0/24"; Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSKGE001") }
    KOR = @{ LAN="192.168.TBC.0/24"; VPN="10.0.TBC.0/24"; Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSKOR001") }

    # ── NA sites — all connect via BRK ───────────────────────────────────────
    TOR = @{ LAN="192.168.146.0/24"; VPN="10.0.146.0/24"; Hub="BRK"; Cost=25; Freq=30; DCs=@("EXADCSTOR001") }
    MTL = @{ LAN="192.168.154.0/24"; VPN="10.0.154.0/24"; Hub="BRK"; Cost=25; Freq=30; DCs=@("EXADCSMTL001") }
    NYC = @{ LAN="192.168.212.0/24"; VPN="10.0.212.0/24"; Hub="BRK"; Cost=25; Freq=30; DCs=@("EXADCSNYC001") }
    LAX = @{ LAN="192.168.213.0/24"; VPN="10.0.213.0/24"; Hub="BRK"; Cost=25; Freq=30; DCs=@("EXADCSLAX001") }
    MIA = @{ LAN="192.168.135.0/24"; VPN="10.0.135.0/24"; Hub="BRK"; Cost=25; Freq=30; DCs=@("EXADCSMIA001") }
    NJC = @{ LAN="192.168.201.0/24"; VPN="10.0.201.0/24"; Hub="BRK"; Cost=25; Freq=30; DCs=@("EXADCSNJC001") }
    GAA = @{ LAN="192.168.33.0/24";  VPN="10.0.33.0/24";  Hub="BRK"; Cost=25; Freq=30; DCs=@("EXADCSGAA001") }

    # ── Pacific — connect via BRK ─────────────────────────────────────────────
    SYD = @{ LAN="192.168.29.0/24"; VPN="10.0.29.0/24"; Hub="BRK"; Cost=50; Freq=30; DCs=@("EXADCSSYD001") }
    MEL = @{ LAN="192.168.61.0/24"; VPN="10.0.61.0/24"; Hub="BRK"; Cost=50; Freq=30; DCs=@("EXADCSMEL001") }
    AKL = @{ LAN="192.168.93.0/24"; VPN="10.0.93.0/24"; Hub="BRK"; Cost=50; Freq=30; DCs=@("EXADCSAKL001") }
}

# Hub-to-hub links (different costs from spoke links)
$HubLinks = @(
    @{ Name="FAL-CPH"; Sites=@("FAL","CPH"); Cost=10;  Freq=15 }
    @{ Name="FAL-ODE"; Sites=@("FAL","ODE"); Cost=50;  Freq=15 }
    @{ Name="FAL-BRK"; Sites=@("FAL","BRK"); Cost=100; Freq=30 }
)

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Action { param([string]$A,[string]$O,[switch]$W)
    if($W){ Write-Host "  [WhatIf] Would $A : $O" -ForegroundColor Cyan }
    else  { Write-Host "  [+] $A : $O" -ForegroundColor Green } }
function Write-Skip { param([string]$O) Write-Host "  [=] Exists: $O" -ForegroundColor DarkGray }
function Write-Warn { param([string]$M) Write-Host "  [!] $M" -ForegroundColor Yellow }
function Exists-Site   { param([string]$N) try{Get-ADReplicationSite    -Identity $N -EA Stop|Out-Null;$true}catch{$false} }
function Exists-Subnet { param([string]$N) try{Get-ADReplicationSubnet  -Identity $N -EA Stop|Out-Null;$true}catch{$false} }
function Exists-Link   { param([string]$N) try{Get-ADReplicationSiteLink -Identity $N -EA Stop|Out-Null;$true}catch{$false} }

# ── Filter to requested sites ─────────────────────────────────────────────────
if($Sites.Count -gt 0){
    $f=[ordered]@{}
    foreach($s in $Sites){ if($SiteData.Contains($s)){$f[$s]=$SiteData[$s]}else{Write-Warn "Unknown site: $s"} }
    $SiteData=$f
}

# ── Step 1: Remove default site link ─────────────────────────────────────────
Write-Host "`n--- Step 1: Default Site Link ---" -ForegroundColor White
if(Exists-Link "DEFAULTIPSITELINK"){
    if($PSCmdlet.ShouldProcess("DEFAULTIPSITELINK","Remove")){
        Remove-ADReplicationSiteLink -Identity "DEFAULTIPSITELINK" -Confirm:$false
        Write-Action "Removed" "DEFAULTIPSITELINK"
    }
} else { Write-Skip "DEFAULTIPSITELINK (already removed)" }

# ── Step 2: Sites ─────────────────────────────────────────────────────────────
Write-Host "`n--- Step 2: Sites ---" -ForegroundColor White
foreach($e in $SiteData.GetEnumerator()){
    if(Exists-Site $e.Key){ Write-Skip "Site: $($e.Key)" }
    else{
        if($PSCmdlet.ShouldProcess($e.Key,"New-ADReplicationSite")){
            New-ADReplicationSite -Name $e.Key; Write-Action "Created site" $e.Key
        } else { Write-Action "Created site" $e.Key -W }
    }
}

# ── Step 3: Subnets ───────────────────────────────────────────────────────────
Write-Host "`n--- Step 3: Subnets ---" -ForegroundColor White
foreach($e in $SiteData.GetEnumerator()){
    foreach($subnet in @($e.Value.LAN,$e.Value.VPN)){
        if($subnet -match "TBC"){ Write-Warn "TBC subnet for $($e.Key) — fill octet first: $subnet"; continue }
        if(Exists-Subnet $subnet){ Write-Skip "Subnet: $subnet" }
        else{
            if($PSCmdlet.ShouldProcess($subnet,"New-ADReplicationSubnet")){
                New-ADReplicationSubnet -Name $subnet -Site $e.Key
                Write-Action "Created subnet" "$subnet → $($e.Key)"
            } else { Write-Action "Created subnet" "$subnet → $($e.Key)" -W }
        }
    }
}

# ── Step 4: Spoke links ───────────────────────────────────────────────────────
Write-Host "`n--- Step 4: Spoke Site Links ---" -ForegroundColor White
foreach($e in $SiteData.GetEnumerator()){
    if($null -eq $e.Value.Hub){ continue }
    $ln = "$($e.Value.Hub)-$($e.Key)"
    if(Exists-Link $ln){ Write-Skip "Link: $ln" }
    else{
        if($PSCmdlet.ShouldProcess($ln,"New-ADReplicationSiteLink")){
            New-ADReplicationSiteLink -Name $ln -SitesIncluded @($e.Value.Hub,$e.Key) `
                -Cost $e.Value.Cost -ReplicationFrequencyInMinutes $e.Value.Freq
            Write-Action "Created link" "$ln (cost=$($e.Value.Cost) freq=$($e.Value.Freq)min)"
        } else { Write-Action "Created link" "$ln (cost=$($e.Value.Cost) freq=$($e.Value.Freq)min)" -W }
    }
}

# ── Step 5: Hub-to-hub links ──────────────────────────────────────────────────
Write-Host "`n--- Step 5: Hub Links ---" -ForegroundColor White
foreach($link in $HubLinks){
    if(Exists-Link $link.Name){ Write-Skip "Hub link: $($link.Name)" }
    else{
        if($PSCmdlet.ShouldProcess($link.Name,"New-ADReplicationSiteLink (hub)")){
            New-ADReplicationSiteLink -Name $link.Name -SitesIncluded $link.Sites `
                -Cost $link.Cost -ReplicationFrequencyInMinutes $link.Freq
            Write-Action "Created hub link" "$($link.Name) (cost=$($link.Cost) freq=$($link.Freq)min)"
        } else { Write-Action "Created hub link" "$($link.Name)" -W }
    }
}

# ── Step 6: Move DCs (optional) ───────────────────────────────────────────────
if($MoveDCs){
    Write-Host "`n--- Step 6: Moving DCs ---" -ForegroundColor White
    foreach($e in $SiteData.GetEnumerator()){
        foreach($dc in $e.Value.DCs){
            try{
                $obj=Get-ADDomainController -Identity $dc -EA Stop
                if($obj.Site -eq $e.Key){ Write-Skip "$dc already in $($e.Key)" }
                else{
                    if($PSCmdlet.ShouldProcess($dc,"Move → $($e.Key)")){
                        Move-ADDirectoryServer -Identity $dc -Site $e.Key
                        Write-Action "Moved" "$dc : $($obj.Site) → $($e.Key)"
                    } else { Write-Action "Moved" "$dc → $($e.Key)" -W }
                }
            } catch { Write-Warn "DC '$dc' not found — promote it first" }
        }
    }
}

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host "`n--- Summary ---" -ForegroundColor White
Write-Host "  Sites   : $((Get-ADReplicationSite    -Filter * | Measure-Object).Count)"
Write-Host "  Subnets : $((Get-ADReplicationSubnet  -Filter * | Measure-Object).Count)"
Write-Host "  Links   : $((Get-ADReplicationSiteLink -Filter * | Measure-Object).Count)"
Write-Host "`n  Next steps:"
Write-Host "  1. Run with -MoveDCs once all Phase 6 DCs are promoted"
Write-Host "  2. repadmin /syncall /AdeP"
Write-Host "  3. Get-ADDomainController -Filter * | Select Name,Site,IsGlobalCatalog"
```

### 7.2 — Verify Sites and Services

```powershell
Get-ADReplicationSite    -Filter * | Sort Name | Select Name
Get-ADReplicationSubnet  -Filter * | Sort Name | Select Name, Site
Get-ADReplicationSiteLink -Filter * | Sort Name |
    Select Name, Cost, ReplicationFrequencyInMinutes,
           @{N="Sites";E={($_.SitesIncluded -join " <-> ")}}
Get-ADDomainController -Filter * | Select Name, Site, IsGlobalCatalog | Sort Site
```

```
Command : Configure-ADSites.ps1 (run 2026-03-14 on EXADCSODE001)
--- Step 1: Default Site Link ---
  [+] Removed : DEFAULTIPSITELINK

--- Step 2: Sites ---
  37 sites created: FAL ODE BRK CPH EDI GLA ABR MCR LND BIR LIV NEW SHE HUL COV HAL
                    MUN BON BER OSL GOT MIL AMS VIE FAX KGE KOR TOR MTL NYC LAX MIA
                    NJC GAA SYD MEL AKL

--- Step 3: Subnets ---
  68 subnets created (LAN + VPN per site)
  [!] TBC subnet for FAX/KGE/KOR -- fill octets when sites are commissioned

--- Step 4: Spoke Site Links ---
  34 spoke links created (FAL-*, ODE-*, BRK-*)

--- Step 5: Hub Links ---
  FAL-CPH (cost=10), FAL-ODE (cost=50), FAL-BRK (cost=100)

--- Step 6: Moving DCs (-MoveDCs pass) ---
  [+] Moved : EXADCSODE001 : Default-First-Site-Name → ODE
  Note: EXDCSCPH001 not moved -- being decommissioned and rebuilt as EXADCSCPH001

Summary: Sites=38  Subnets=68  Links=36
```

### 7.3 — Adding a New Site Later

Add one row to `$SiteData`, re-run with `-Sites <CODE>`:

```powershell
# Example — new UK site
LON2 = @{ LAN="192.168.XXX.0/24"; VPN="10.0.XXX.0/24";
           Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSLO2001") }
```

```powershell
.\Configure-ADSites.ps1 -Sites LON2 -WhatIf   # preview
.\Configure-ADSites.ps1 -Sites LON2            # create
.\Configure-ADSites.ps1 -Sites LON2 -MoveDCs   # and move DC
```

> **✅ Phase 7 complete when:** All sites, subnets and links created, all DCs
> in correct sites, `repadmin /replsummary` shows healthy replication on the
> new topology.

---

## Phase 8 — Global Catalog Configuration

The Global Catalog holds a partial replica of all forest objects and is required for user logon (group membership resolution).

> **Run on:** `EXADCSFAL001`

### GC Placement

| DC | Site | GC |
|---|---|---|
| `EXADCSFAL001` | FAL | ✅ Yes (default on promotion) |
| `EXADCSODE001` | ODE | ✅ Yes |
| `EXADCSBRK001` | BRK | ✅ Yes |
| `EXADCSCPH001` | CPH | ✅ Yes (was always GC) |
| All other site DCs | Various | Optional — enable for sites with >50 users |

```powershell
# Check current GC status across all DCs
Get-ADDomainController -Filter * | Select Name, IsGlobalCatalog, Site | Sort Site

# Enable GC on ODE if needed
Set-ADObject -Identity "CN=NTDS Settings,CN=EXADCSODE001,CN=Servers,CN=ODE,CN=Sites,CN=Configuration,DC=jukebox,DC=internal" -Replace @{options='1'}

# Enable GC on BRK if needed
Set-ADObject -Identity "CN=NTDS Settings,CN=EXADCSBRK001,CN=Servers,CN=BRK,CN=Sites,CN=Configuration,DC=jukebox,DC=internal" -Replace @{options='1'}
```

```
[PENDING OUTPUT]
Command : Get-ADDomainController -Filter * | Select Name, IsGlobalCatalog, Site
Expected: FAL, ODE, BRK, CPH all show IsGlobalCatalog: True
```

> **✅ Phase 8 complete when:** FAL, ODE, BRK and CPH all confirmed as GC servers.

---

## Phase 9 — Post-Promotion Verification

Full enterprise health check. Run after all phases above are complete.

> **Run on:** `EXADCSFAL001` unless noted.

### 9.1 — Replication Health

```powershell
repadmin /replsummary
repadmin /showrepl
repadmin /showrepl * /errorsonly   # should return nothing
repadmin /syncall /AdeP
```

```
Command : repadmin /replsummary (EXADCSODE001, 2026-03-14)
Source DSA          largest delta    fails/total %%   error
 EXADCSODE001              26m:58s    0 /   5    0
 EXDCSCPH001           10h:38m:06s    1 /   5   20  (8524) DNS lookup failure

Destination DSA     largest delta    fails/total %%   error
 EXADCSODE001          10h:38m:06s    1 /   5   20  (8524) DNS lookup failure
 EXDCSCPH001               26m:58s    0 /   5    0

Note: EXDCSCPH001 errors are expected -- this DC is being decommissioned and
rebuilt as EXADCSCPH001. EXADCSODE001 replication is clean (0 failures).
```

### 9.2 — DCDiag Enterprise Health Check

```powershell
dcdiag /v /c /e   # enterprise-wide, comprehensive, verbose

# Individual key tests
dcdiag /test:connectivity
dcdiag /test:replications
dcdiag /test:dns /v
dcdiag /test:fsmo
dcdiag /test:netlogons
dcdiag /test:services
dcdiag /test:sysvol
```

```
Command : dcdiag /test:replications (EXADCSODE001, 2026-03-14)
   Testing server: ODE\EXADCSODE001
      Starting test: Connectivity ......... EXADCSODE001 passed test Connectivity
      Starting test: Replications
         [Replications Check,EXADCSODE001] failure from EXDCSCPH001 (8524 DNS)
         Note: Expected -- EXDCSCPH001 being rebuilt. ODE itself is clean.
      Starting test: Advertising ......... EXADCSODE001 passed test Advertising

Command : nltest /dsgetdc:jukebox.internal /force (EXADCSODE001, 2026-03-14)
   DC: \EXADCSODE001.jukebox.internal
   Address: \192.168.126.10
   Dc Site Name: ODE
   Our Site Name: ODE
   Flags: GC DS LDAP KDC TIMESERV WRITABLE DNS_DC DNS_DOMAIN DNS_FOREST
          CLOSE_SITE FULL_SECRET WS DS_8 DS_9 DS_10 KEYLIST
   The command completed successfully
```

### 9.3 — SYSVOL Replication

```powershell
# DFSR (not legacy FRS) should be in use on Server 2016+
dfsrmig /getglobalstate

# SYSVOL shared on all DCs?
Invoke-Command -ComputerName EXADCSFAL001,EXADCSODE001,EXADCSBRK001,EXADCSCPH001 -ScriptBlock { net share | findstr SYSVOL }

# Check replication backlog between FAL and ODE
Get-DfsrBacklog -GroupName "Domain System Volume" -FolderName "SYSVOL Share" -SourceComputerName EXADCSFAL001 -DestinationComputerName EXADCSODE001
```



```
Command : dfsrmig /getglobalstate (EXADCSODE001, 2026-03-14)
Current DFSR global state: 'Eliminated'
Succeeded.

Command : net share | findstr SYSVOL
NETLOGON     C:\Windows\SYSVOL\sysvol\jukebox.internal\SCRIPTS
SYSVOL       C:\Windows\SYSVOL\sysvol        Logon server share
```

### 9.4 — End-to-End Connectivity Matrix

Run from a spoke DC (e.g. `EXADCSEDI001`) to confirm it reaches all hubs:

```powershell
$hubs = @{ FAL="10.0.76.10"; CPH="10.0.231.10"; ODE="10.0.126.10"; BRK="10.0.136.10" }
foreach($hub in $hubs.GetEnumerator()){
  Write-Host "`n=== $($hub.Key) ($($hub.Value)) ==="
  foreach($port in @(389,88,53,445)){
    $r = Test-NetConnection -ComputerName $hub.Value -Port $port -WarningAction SilentlyContinue
    Write-Host "  Port $port : $(if($r.TcpTestSucceeded){'OK'}else{'FAIL'})"
  }
}
```

```bash
declare -A HUBS=( [FAL]="10.0.76.10" [CPH]="10.0.231.10" [ODE]="10.0.126.10" [BRK]="10.0.136.10" )
for site in "${!HUBS[@]}"; do
  echo "=== $site (${HUBS[$site]}) ==="
  for port in 389 88 53 445; do
    nc -zw2 ${HUBS[$site]} $port 2>/dev/null && echo "  Port $port: OK" || echo "  Port $port: FAIL"
  done
done
```

```
[PENDING OUTPUT]
Command : connectivity matrix above from EXADCSEDI001
Expected: All ports OK for all four hub DCs
```

> **✅ Phase 9 complete when:** repadmin 0 errors, dcdiag all pass,
> SYSVOL replicated, connectivity matrix all green.

---

## Phase 10 — DFS Preparation (Hooks)

DFS will be configured in a later procedure. Install the roles now.

> **Run on:** `EXADCSFAL001`, `EXADCSODE001`, `EXADCSBRK001`

```powershell
Install-WindowsFeature -Name FS-DFS-Namespace,FS-DFS-Replication -IncludeManagementTools
Get-WindowsFeature FS-DFS-*
```

### Planned DFS Namespace Layout (reference)

| Namespace | Primary server | Replicas |
|---|---|---|
| `\\jukebox.internal\shared` | `EXADCSFAL001` | `EXADCSODE001`, `EXADCSBRK001` |
| `\\jukebox.internal\profiles` | `EXADCSFAL001` | TBD |
| `\\jukebox.internal\netlogon` | All DCs | AD-managed via SYSVOL |

```
Command : Install-WindowsFeature -Name FS-DFS-Namespace,FS-DFS-Replication -IncludeManagementTools
          (EXADCSODE001, 2026-03-14)
Success  Restart Needed  Exit Code  Feature Result
True     No              Success    {DFS Namespaces, DFS Replication}

Name               InstallState
----               ------------
FS-DFS-Namespace   Installed
FS-DFS-Replication Installed
```

> Full DFS configuration is out of scope for this document. Role installation above is the only action required at this stage.

---


---

## Connectivity Verification Reference

Quick reference card — use these commands any time you need to confirm AD connectivity over WireGuard tunnels.

### Windows — Quick Checks

```powershell
# Is the domain reachable?
nltest /dsgetdc:jukebox.internal /force

# Which DC am I using?
nltest /dsgetdc:jukebox.internal

# Is replication healthy?
repadmin /replsummary

# Who holds FSMO roles?
netdom query fsmo

# Is my secure channel healthy?
Test-ComputerSecureChannel -Verbose

# Can I reach the PDC over the tunnel?
Test-NetConnection -ComputerName 10.0.76.10 -Port 389

# DNS — do SRV records resolve?
Resolve-DnsName -Name "_ldap._tcp.jukebox.internal" -Type SRV

# Time sync status (Kerberos needs < 5 min skew)
w32tm /query /status
```

### Linux — Quick Checks

```bash
# Is a DC reachable and responding to LDAP?
nc -zv 10.0.76.10 389

# Do SRV records resolve over the tunnel?
dig @10.0.76.10 _ldap._tcp.jukebox.internal SRV
dig @10.0.76.10 _kerberos._tcp.jukebox.internal SRV

# Can I get a Kerberos ticket? (requires krb5-user)
kinit Administrator@jukebox.internal && klist

# WireGuard tunnel status
wg show
ip addr show wg0

# Is the tunnel passing AD traffic?
for port in 53 88 389 445 636 3268; do nc -zw2 10.0.76.10 $port 2>/dev/null && echo "Port $port: OK" || echo "Port $port: FAIL"
done
```

---

## Troubleshooting

### PSReadLine paste corruption over SSH (multi-line commands arrive garbled)

**Symptom:** Pasting multiple lines into a PS7 SSH session causes lines to arrive concatenated, reordered, or with literal `-FG Color` text appearing instead of coloured output.

**Cause:** PSReadLine's Windows edit mode conflicts with SSH PTY handling. Even with `xterm-256color` and bracketed paste enabled in the client, the inbox version of PSReadLine shipped with Windows Server PS7 does not handle bracketed paste correctly.

**Immediate fix (per session):**
```powershell
Remove-Module PSReadLine
```
This drops back to basic line editing — no syntax highlighting or prediction, but paste works cleanly. Sufficient for all AD administration tasks.

**Permanent fix (deploy to all DCs):**
```powershell
# Install full Gallery version of PSReadLine
Install-Module PSReadLine -Force -Scope AllUsers -AllowClobber

# Add to PS7 AllUsersAllHosts profile
Add-Content "$env:ProgramFiles\PowerShell\7\profile.ps1" "`nSet-PSReadLineOption -EditMode Emacs" -Encoding UTF8
Add-Content "$env:ProgramFiles\PowerShell\7\profile.ps1" "`nSet-PSReadLineOption -PredictionViewStyle InlineView" -Encoding UTF8
```

**Note:** The bootstrap script (Join-DomainAndBootstrap.ps1) has been updated to set `EditMode Emacs` and `PredictionViewStyle InlineView` in the PS7 profile on all future DCs. Existing DCs (EXADCSODE001, EXDCSCPH001) need the profile update applied manually.

---

### Domain join fails — "domain not found" or "no such domain"

Almost always DNS. Run Phase 2 checks first.

> **Known gotcha (learned in testing):** The internal DNS zones for `example.net`, `example.org`, and `example.com` must exist on the DC **before** attempting any domain join or promotion. If they do not exist, Windows resolves these names to their real public owners (Cloudflare in our case) and `Add-Computer` correctly reports it cannot contact the domain. Create the zones first with `Add-DnsServerPrimaryZone`, then run `Restart-Service netlogon` to populate SRV records. Verify with `Resolve-DnsName _ldap._tcp.example.net -Type SRV` before retrying.

> **Second known gotcha:** `LDAP://DC=jukebox,DC=internal` anonymous binds fail from unjoined machines on modern AD. Always bind by IP: `LDAP://192.168.231.10/DC=jukebox,DC=internal` with explicit credentials.

```powershell
# Confirm DNS server is set to a reachable DC
Get-DnsClientServerAddress
ipconfig /all | findstr "DNS Servers"

# Test DNS resolution directly
nslookup jukebox.internal 10.0.231.10
nslookup -type=SRV _ldap._tcp.jukebox.internal 10.0.231.10
```

### Domain join fails — "credentials are incorrect"

```powershell
# Verify time sync — Kerberos fails if skew > 5 minutes
w32tm /stripchart /computer:10.0.76.10 /samples:3 /dataonly

# If time is wrong, sync immediately
w32tm /config /manualpeerlist:10.0.76.10 /syncfromflags:manual /update
w32tm /resync /force
```

### Replication failing between sites

```powershell
# Identify which link is failing
repadmin /showrepl * /errorsonly

# Force replication and watch for errors
repadmin /syncall EXADCSFAL001 /AdeP

# Check if site link exists and is correct
Get-ADReplicationSiteLink -Filter * | Select Name, Cost, ReplicationFrequencyInMinutes
```

```bash
# Confirm WireGuard tunnel is up and RPC port is reachable
wg show | grep -A4 "peer"
nc -zv 10.0.76.10 135    # RPC endpoint mapper
nc -zv 10.0.76.10 445    # SMB (SYSVOL)
```

### SYSVOL not replicating

```powershell
# Check DFSR service on all DCs
Get-Service DFSR -ComputerName EXADCSFAL001, EXADCSODE001

# Check backlog
Get-DfsrBacklog -GroupName "Domain System Volume" -FolderName "SYSVOL Share" -SourceComputerName EXADCSFAL001 -DestinationComputerName EXADCSODE001

# Event log — DFSR errors
Get-EventLog -LogName "DFS Replication" -EntryType Error -Newest 20 | Select TimeGenerated, Message
```

### `nltest /dsgetdc` returns wrong site DC

```powershell
# Confirm subnets are configured in Sites and Services
Get-ADReplicationSubnet -Filter * | Select Name, Site

# Force DC locator to use correct site
nltest /dsgetdc:jukebox.internal /site:FAL /force

# Confirm DC is in the correct site
nltest /dsgetdc:jukebox.internal /server:EXADCSFAL001
```

---

## Output Collection Checklist

When the procedure is run in the live environment, collect the following output to fill in the `[PENDING OUTPUT]` blocks above.

### Phase 1 — WireGuard Verification
- [ ] `wg show` on `EXAFWLFAL001` showing all peers with recent handshakes
- [ ] `ping` results FAL→CPH, FAL→ODE, FAL→BRK (VPN IPs)
- [ ] PowerShell port test output against `10.0.76.10`

### Phase 2 — DNS Verification
- [ ] `dig @10.0.231.10 _ldap._tcp.jukebox.internal SRV`
- [ ] `dig @10.0.231.10 EXADCSCPH001.jukebox.internal A`
- [ ] `nltest /dsgetdc:jukebox.internal /force` from `EXADCSFAL001`
- [ ] `nltest /sc_verify:jukebox.internal /server:EXADCSCPH001`

### Phase 3 — FSMO
- [ ] `netdom query fsmo` before transfer (all roles on CPH)
- [ ] `netdom query fsmo` after transfer (all roles on FAL)

### Phase 4 — DC Promotion
- [ ] `Install-WindowsFeature` output
- [ ] `Install-ADDSDomainController` full promotion output (per DC)
- [ ] `repadmin /showrepl` after FAL promotion
- [ ] `dcdiag /test:dns /v` after FAL promotion

### Phase 7 — Post-Promotion
- [ ] `repadmin /replsummary` (all DCs)
- [ ] `dcdiag /v /c /e` (enterprise-wide)
- [ ] `dfsrmig /getglobalstate`
- [ ] Connectivity matrix output from a spoke DC (e.g. EDI)
- [ ] `Get-ADDomainController -Filter * | Select Name, IsGlobalCatalog, Site`

---

**Document End**  
*Internal Use Only — Network Engineering*  
*For questions or corrections, raise a ticket in the internal helpdesk.*

---
