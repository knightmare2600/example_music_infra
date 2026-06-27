# Example Music Limited — DFS Namespace & Replication Setup

> **Classification:** Internal — Infrastructure
> **Forest:** `jukebox.internal`
> **Domains:** `example.net` · `example.org` · `example.com`
> **Provisioning network:** `192.168.139.0/24`
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-08 | Initial document — DFS Namespace and DFS-R setup procedure for jukebox.internal estate |

---

## Standard IP Convention

Every site follows this addressing scheme within its `/24` subnet.
Exceptions are noted in individual site entries.

| Address | Role | Hostname pattern |
|---------|------|-----------------|
| `.1` | Primary internet gateway | `EXAFWL<SITE>001` / `EXARTR<SITE>001` |
| `.2` | BMC pool slot 1 — DRAC / iLO | `EXARAC<SITE>001` |
| `.3` | BMC pool slot 2 — or RAC emulator VM on single-PVE-node sites | `EXARAC<SITE>002` |
| `.4` | BMC pool slot 3 — or RAC emulator VM on two-PVE-node sites | `EXARAC<SITE>003` |
| `.5` | PVE node 1 | `EXAPVE<SITE>001` |
| `.6` | PVE node 2 | `EXAPVE<SITE>002` |
| `.7` | PVE node 3 | `EXAPVE<SITE>003` |
| `.10` | Domain Controller — primary | `EXADCS<SITE>001` |
| `.11` | Domain Controller — secondary | `EXADCS<SITE>002` |
| `.48` | VOIP SBC — trunks to `EXACLDPBX001` | `EXASBC<SITE>001` |
| `.100`–`.249` | DHCP pool | — |
| `.250`–`.252` | RT switches | `EXASWI<SITE>001`–`003` |
| `.253` | Secondary internet gateway | — |

> **BMC pool:** `.2`/`.3`/`.4` are shared between physical DRAC/iLO interfaces and the RAC emulator VM. Physical PVE node BMCs consume from `.2` upward; the RAC VM (`EXARAC<SITE>00N`) takes the next free slot.
>
> ***NB: On three-PVE-node sites the pool is fully consumed by physical BMCs.***

---

## 1. Overview

This document describes the complete setup and ongoing administration of Distributed File System (DFS) Namespaces and DFS Replication (DFS-R) across the Example Music global estate on the `jukebox.internal` Active Directory forest.

The primary goal of this initial deployment is to ensure the existing `tools` share — currently hosted only on `EXADCSCPH001` — is replicated and accessible at all satellite sites before dedicated file servers are built out. DFS provides both the replication mechanism and the unified namespace that abstracts server location from end users and systems.

### 1.1 Scope

- Initial share: `\\EXADCSCPH001\tools` replicated estate-wide
- All 13 domain controllers across 13 sites participating as DFS-R members
- Tiered hub-and-spoke topology (three tiers)
- Read-only replication to all satellite sites; read/write at hub tier only
- DFS Namespace hosted on the `jukebox.internal` domain

### 1.2 Out of Scope

- Dedicated file servers (future phase)
- SYSVOL/NETLOGON replication (managed separately by AD)
- End-user home drives or roaming profiles

---

## 2. Background & Technology

### 2.1 What is DFS?

Distributed File System (DFS) is a set of Microsoft Windows Server client and server services that organise shared folders located on different servers into a single logical namespace. DFS has two distinct components that work together but serve different purposes:

| Component | Purpose |
|-----------|---------|
| **DFS Namespaces (DFS-N)** | Provides a single, unified UNC path (e.g. `\\jukebox.internal\shares\tools`) that transparently redirects clients to the appropriate server. Users and scripts reference one path regardless of which physical server holds the data or where the user is located. |
| **DFS Replication (DFS-R)** | A multi-master replication engine that keeps folder contents synchronised across multiple servers. Uses the Remote Differential Compression (RDC) algorithm to transfer only changed blocks rather than whole files, making it efficient over WAN links. |

DFS-N and DFS-R are independent — you can use DFS-N without DFS-R (pointing multiple namespace targets at independent servers), or DFS-R without DFS-N (replicating data without a unified namespace). For this deployment, both are used together.

### 2.2 Brief History

DFS was first introduced in Windows NT 4.0 as a standalone feature. Key milestones:

| Version | Milestone |
|---------|-----------|
| NT 4.0 / W2K | Initial DFS Namespace support; standalone and domain-based namespaces |
| Windows Server 2003 R2 | DFS-R introduced, replacing the older File Replication Service (FRS) for data replication. FRS remained for SYSVOL until 2008. |
| Windows Server 2008 | SYSVOL migration from FRS to DFS-R became possible. DFS-R gained read-only replication members. |
| Windows Server 2012+ | DFS-R gained cloned database support, faster initial sync, and improved staging management. |
| Windows Server 2016+ | Improved bandwidth throttling, diagnostic tooling. DFS-R remains the current replication solution for general file data. |
| Windows Server 2022 | Current baseline for this deployment. No fundamental DFS-R architecture changes; improvements are stability and performance focused. |

### 2.3 How DFS-R Works

DFS-R uses a multi-master model with configurable topology. Key concepts:

- **Replication Group:** A named collection of servers (members) that replicate one or more folders.
- **Replicated Folder:** A folder path on each member that is kept in sync.
- **Connection:** A directional link between two members. Bidirectional replication requires two connections.
- **Staging Folder:** A temporary area where changed files are assembled before and after transfer. Undersizing this is the most common cause of replication performance problems.
- **Conflict Resolution:** In multi-master (read/write) topologies, last-writer-wins. For read-only members this is not a concern.
- **RDC (Remote Differential Compression):** Only changed byte ranges within a file are transferred, not the whole file. Critical for WAN efficiency.
- **Initial Sync:** The first replication after adding a new member copies all data. This should be scheduled during off-peak hours over WAN links.

### 2.4 Topology Chosen: Tiered Hub and Spoke

A three-tier hub-and-spoke topology has been chosen for the Example Music estate. This topology minimises WAN traffic by ensuring that inter-continental replication only occurs between hub servers, and that local satellite sites pull only from their regional parent.

The topology is:

```
FAL — Falkirk, Scotland          (Global Hub / Read-Write)
├── MCR — Manchester, England    (Satellite / Read-Only, syncs from FAL)
├── LIV — Liverpool, England     (Satellite / Read-Only, syncs from FAL)
├── GLA — Glasgow, Scotland      (Satellite / Read-Only, syncs from FAL)
├── NEW — Newcastle, England     (Satellite / Read-Only, syncs from FAL)
├── ODE — Odense, Danmark        (European Regional Hub / Read-Write)
│   ├── CPH — København, DK      (Satellite / Read-Only, syncs from ODE)
│   ├── KGE — Køge, DK           (Satellite / Read-Only, syncs from ODE)
│   └── FAX — Faxe, DK           (Satellite / Read-Only, syncs from ODE)
└── BRK — Brockville, ON         (Americas/APAC Regional Hub / Read-Write)
    ├── TOR — Toronto, CA        (Satellite / Read-Only, syncs from BRK)
    ├── MTL — Montréal, CA       (Satellite / Read-Only, syncs from BRK)
    └── SYD — Sydney, AU         (Satellite / Read-Only, syncs from BRK)

Other sites as needed...
```

> ℹ FAL and ODE replicate bidirectionally. FAL and BRK replicate bidirectionally. ODE and BRK do **NOT** directly replicate — all inter-hub traffic flows through FAL. This prevents a full mesh at the hub tier and keeps topology manageable.

---

## 3. Infrastructure Reference

### 3.1 Domain Controller Inventory

All servers listed below are, or will be, Domain Controllers in the `jukebox.internal` forest. All will participate in DFS-R.

| Hostname | IP | Site | Location | Role | DFS Role |
|----------|----|------|----------|------|----------|
| `EXADCSCPH001` | `192.168.231.10` | CPH | København, Danmark | Existing DC (source) | Satellite (read-only) |
| `EXADCSFAL001` | `192.168.76.10` | FAL | Falkirk, Scotland | DC (to be promoted) | Global Hub (read-write) |
| `EXADCSFAL002` | `192.168.76.11` | FAL | Falkirk, Scotland | DC (to be promoted) | FAL secondary |
| `EXADCSODE001` | `192.168.126.10` | ODE | Odense, Danmark | DC (to be promoted) | European Hub (read-write) |
| `EXADCSODE002` | `192.168.126.11` | ODE | Odense, Danmark | DC (to be promoted) | ODE secondary |
| `EXADCSBRK001` | `192.168.136.10` | BRK | Brockville, Ontario | DC (to be promoted) | Americas/APAC Hub (read-write) |
| `EXADCSMCR001` | `192.168.161.10` | MCR | Manchester, England | DC (to be promoted) | Satellite (read-only) |
| `EXADCSLIV001` | `192.168.151.10` | LIV | Liverpool, England | DC (to be promoted) | Satellite (read-only) |
| `EXADCSGLA001` | `192.168.141.10` | GLA | Glasgow, Scotland | DC (to be promoted) | Satellite (read-only) |
| `EXADCSNEW001` | `192.168.191.10` | NEW | Newcastle, England | DC (to be promoted) | Satellite (read-only) |
| `EXADCSKGE001` | `192.168.65.10` | KGE | Køge, Danmark | DC (to be promoted) | Satellite (read-only) |
| `EXADCSFAX001` | `192.168.246.10` | FAX | Faxe, Danmark | DC (to be promoted) | Satellite (read-only) |
| `EXADCSTOR001` | `192.168.164.10` | TOR | Toronto, Ontario | DC (to be promoted) | Satellite (read-only) |
| `EXADCSMTL001` | `192.168.154.10` | MTL | Montréal, Québec | DC (to be promoted) | Satellite (read-only) |
| `EXADCSSYD001` | `192.168.29.10` | SYD | Sydney, Australia | DC (to be promoted) | Satellite (read-only) |

### 3.2 Network Infrastructure

Inter-site connectivity is provided by WireGuard VPN tunnels. The WireGuard endpoints are hosted on dedicated firewall appliances with the naming convention `EXAFWL[SITE][SEQ]`.

| Hostname | Site | IP | Notes |
|----------|------|----|-------|
| `EXAFWLFAL001` | FAL | `192.168.76.1` | Global hub WireGuard endpoint |
| `EXAFWLODE001` | ODE | `192.168.126.1` | European hub WireGuard endpoint |
| `EXAFWLBRK001` | BRK | `192.168.136.1` | Americas/APAC hub WireGuard endpoint |
| `EXAFWLCPH001` | CPH | `192.168.231.1` | Existing site |
| `EXAFWLMCR001` | MCR | `192.168.161.1` | |
| `EXAFWLLIV001` | LIV | `192.168.151.1` | |
| `EXAFWLGLA001` | GLA | `192.168.141.1` | |
| `EXAFWLNEW001` | NEW | `192.168.191.1` | |
| `EXAFWLKGE001` | KGE | `192.168.65.1` | |
| `EXAFWLFAX001` | FAX | `192.168.246.1` | |
| `EXAFWLTOR001` | TOR | `192.168.164.1` | |
| `EXAFWLMTL001` | MTL | `192.168.154.1` | |
| `EXAFWLSYD001` | SYD | `192.168.29.1` | |

> ⚠ DFS-R replication traffic will traverse WireGuard tunnels. Ensure that TCP port 135 (RPC Endpoint Mapper) and dynamic RPC ports (49152–65535 by default) are permitted between all DC pairs that have replication connections. Consider restricting the dynamic RPC port range for DFS-R to a narrower range and opening only those ports on the firewalls.

### 3.3 AD Sites and Site Links

Before configuring DFS, Active Directory Sites and Services must accurately reflect the physical topology. Each site listed in section 3.1 must have a corresponding AD Site object, and site links must be configured to reflect the WireGuard topology.

- Create AD Site objects for all 13 sites if not already present
- Create site link objects reflecting: FAL–ODE, FAL–BRK, FAL–MCR, FAL–LIV, FAL–GLA, FAL–NEW, ODE–CPH, ODE–KGE, ODE–FAX, BRK–TOR, BRK–MTL, BRK–SYD
- Assign appropriate site link costs — lower cost = preferred path. Hub-to-hub links should have lower cost than hub-to-satellite
- Assign each DC's IP subnet to its correct AD Site

> ℹ DFS-R does not strictly require AD Sites to be configured, but correct site topology is essential for AD replication health and for DFS referral ordering, which directs clients to their closest DFS target.

---

## 4. Prerequisites

### 4.1 Active Directory

1. `jukebox.internal` forest is operational with forest functional level set to Windows Server 2022.
2. `EXADCSCPH001` is online and healthy. Verify with: `dcdiag /test:replications` on `EXADCSCPH001`.
3. All new DCs (FAL, ODE, BRK and satellite sites) have been promoted and AD replication is healthy before proceeding with DFS configuration.
4. AD Sites and Services is configured as described in section 3.3.
5. DNS is resolving all DC hostnames correctly across all sites.

### 4.2 Server Roles

The DFS roles must be installed on all servers that will participate in DFS (all 13 DCs). Run the following on each server:

```powershell
Install-WindowsFeature -Name FS-DFS-Namespace, FS-DFS-Replication -IncludeManagementTools
```

> ℹ This can be run remotely against all DCs simultaneously using a loop. See section 4.5 for a bulk PowerShell example.

### 4.3 The Source Share

The `tools` share on `EXADCSCPH001` must be in a known good state before replication begins:

1. Verify share exists: `net share` on `EXADCSCPH001` must list `tools`
2. Note the local path, e.g. `C:\Shares\tools` or `C:\tools`
3. Verify NTFS permissions are correct — these will replicate to all members
4. Note the current size of the share — this determines initial sync time

> ⚠ DFS-R replicates NTFS ACLs along with file data. Ensure permissions on the source are correct before replication begins, as they will be pushed to all members.

### 4.4 Firewall Ports

Ensure the following ports are open between all replicating server pairs across the WireGuard tunnels:

| Port / Protocol | Purpose | Direction |
|-----------------|---------|-----------|
| TCP 135 | RPC Endpoint Mapper | Bidirectional between all replicating DCs |
| TCP 49152–65535 | Dynamic RPC (DFS-R uses RPC) | Bidirectional between all replicating DCs |
| TCP/UDP 445 | SMB (DFS Namespace referrals) | Clients to all DCs |
| TCP/UDP 389 | LDAP (AD lookups) | Bidirectional between all DCs |

> ℹ It is strongly recommended to restrict the dynamic RPC range to reduce the firewall rule surface. Set the range on all DCs with `netsh int ipv4 set dynamicport tcp start=60000 num=1000` — then open only TCP 60000–61000 on the firewalls.

### 4.5 Bulk Role Installation (PowerShell)

To install DFS roles across all DCs simultaneously from a single admin session on FAL:

```powershell
$dcs = @('EXADCSFAL001','EXADCSFAL002',
         'EXADCSODE001','EXADCSODE002',
         'EXADCSBRK001',
         'EXADCSCPH001',
         'EXADCSMCR001','EXADCSLIV001','EXADCSGLA001','EXADCSNEW001',
         'EXADCSKGE001','EXADCSFAX001',
         'EXADCSTOR001','EXADCSMTL001','EXADCSSYD001')

foreach ($dc in $dcs) {
    Invoke-Command -ComputerName $dc -ScriptBlock {
        Install-WindowsFeature -Name FS-DFS-Namespace, FS-DFS-Replication -IncludeManagementTools
    }
}
```

---

## 5. Prepare Shared Folders on Hub Servers

Before configuring DFS-R, the local folder path that will be the replicated folder must exist on each participating server. For hub servers (FAL, ODE, BRK), this folder must also be shared via SMB so it can serve as a DFS namespace target.

The satellite servers also need the local folder created, but do not need to share it independently — the DFS namespace target will point to the hub servers, and clients will be directed there by DFS referral.

### 5.1 Create Folders and Shares on Hub Servers

Run the following on `EXADCSFAL001`, `EXADCSODE001`, and `EXADCSBRK001` respectively, adjusting the drive letter to match your server's data volume:

```powershell
# On EXADCSFAL001
New-Item -ItemType Directory -Path 'C:\DFSRoots\tools' -Force
New-SmbShare -Name 'tools' -Path 'C:\DFSRoots\tools' -FullAccess 'JUKEBOX\Domain Admins' -ReadAccess 'JUKEBOX\Domain Users' -Description 'Example Music Tools Share'

# Repeat on EXADCSODE001 and EXADCSBRK001 with the same paths
```

> ⚠ The local folder path should be consistent across all members (e.g. `C:\DFSRoots\tools` on all servers) to simplify administration. If drive letters differ between servers, document this carefully.

Also create and share the namespace root on each hub:

```powershell
New-Item -ItemType Directory -Path 'C:\DFSRoots\shares' -Force
New-SmbShare -Name 'shares' -Path 'C:\DFSRoots\shares' -FullAccess 'JUKEBOX\Domain Admins' -ReadAccess 'JUKEBOX\Domain Users' -Description 'DFS Namespace Root'
```

### 5.2 Create Local Folders on Satellite Servers

Satellite servers need the local folder to exist for DFS-R to replicate into, but do not need an SMB share. Run on each satellite DC:

```powershell
New-Item -ItemType Directory -Path 'C:\DFSRoots\tools' -Force
```

This can be done in bulk:

```powershell
$satellites = @('EXADCSCPH001','EXADCSMCR001','EXADCSLIV001','EXADCSGLA001','EXADCSNEW001',
                'EXADCSKGE001','EXADCSFAX001','EXADCSTOR001','EXADCSMTL001','EXADCSSYD001')

foreach ($s in $satellites) { Invoke-Command -ComputerName $s -ScriptBlock { New-Item -ItemType Directory -Path 'C:\DFSRoots\tools' -Force } }
```

---

## 6. Configure DFS Namespace

A domain-based DFS Namespace provides the unified UNC path that clients and systems will use. The namespace is hosted in AD and can have multiple namespace servers for redundancy.

### 6.1 Create the Domain Namespace

Run the following on `EXADCSFAL001` (or any DC with RSAT DFS tools):

```powershell
# Create the domain-based namespace
New-DfsnRoot -Path '\\jukebox.internal\shares' -Type DomainV2 -TargetPath '\\EXADCSFAL001\shares' -Description 'Example Music Global File Shares'
```

> ℹ DomainV2 requires Windows Server 2008 domain functional level or higher — `jukebox.internal` at 2022 level satisfies this. DomainV2 supports access-based enumeration and improved scalability over the legacy Domain (V1) mode.

### 6.2 Add the Tools Folder to the Namespace

Create the namespace folder and add the hub servers as targets:

```powershell
# Create the namespace folder
New-DfsnFolder -Path '\\jukebox.internal\shares\tools' -TargetPath '\\EXADCSFAL001\tools' -Description 'Example Music Tools'

# Add ODE and BRK as additional targets
New-DfsnFolderTarget -Path '\\jukebox.internal\shares\tools' -TargetPath '\\EXADCSODE001\tools'
New-DfsnFolderTarget -Path '\\jukebox.internal\shares\tools' -TargetPath '\\EXADCSBRK001\tools'
```

Clients will now be directed to the nearest target based on AD site membership. A client in `ODE` will be directed to `EXADCSODE001`, a client in `FAX` will be directed to `EXADCSODE001` (its parent hub), and so on.

### 6.3 Add Additional Namespace Servers

For namespace availability, add ODE and BRK as additional namespace servers:

```powershell
New-DfsnRootTarget -Path '\\jukebox.internal\shares' -TargetPath '\\EXADCSODE001\shares'
New-DfsnRootTarget -Path '\\jukebox.internal\shares' -TargetPath '\\EXADCSBRK001\shares'
```

> ℹ Adding namespace servers requires the `shares` folder (`C:\DFSRoots\shares`) to also exist on ODE and BRK and be shared as `shares` — see section 5.1.

---

## 7. Configure DFS Replication — Hub Tier

DFS-R is configured in stages, starting with the hub tier (FAL ↔ ODE and FAL ↔ BRK). The hub tier is configured first so that ODE and BRK have a complete copy of the data before their satellite sites begin syncing from them.

> ⚠ Do not proceed to configuring satellite replication until initial sync between FAL and both regional hubs is confirmed complete. Satellites syncing from a hub that is itself still receiving data will cause extended replication delays.

### 7.1 Create the Replication Group

A single replication group will contain all members. This simplifies management and ensures all servers share a common replication topology.

```powershell
# Create the replication group
New-DfsReplicationGroup -GroupName 'ExampleMusic-Tools' -DomainName 'jukebox.internal'
```

### 7.2 Create the Replicated Folder

```powershell
New-DfsReplicatedFolder -GroupName 'ExampleMusic-Tools' -FolderName 'tools' -DomainName 'jukebox.internal'
```

### 7.3 Add Hub Members

Add FAL, ODE, and BRK as members. FAL is the primary (it holds the authoritative copy from CPH's data). Staging quota is set to 16GB — adjust based on the size of your tools share. A good rule of thumb is staging = 32x the size of the largest file, minimum 4GB.

```powershell
# Add hub members
Add-DfsrMember -GroupName 'ExampleMusic-Tools' -ComputerName 'EXADCSFAL001' -DomainName 'jukebox.internal'
Add-DfsrMember -GroupName 'ExampleMusic-Tools' -ComputerName 'EXADCSODE001' -DomainName 'jukebox.internal'
Add-DfsrMember -GroupName 'ExampleMusic-Tools' -ComputerName 'EXADCSBRK001' -DomainName 'jukebox.internal'
```

### 7.4 Set Replicated Folder Paths on Hub Members

```powershell
Set-DfsrMembership -GroupName 'ExampleMusic-Tools' -FolderName 'tools' -ComputerName 'EXADCSFAL001' -ContentPath 'C:\DFSRoots\tools' -StagingPathQuotaInMB 16384 -PrimaryMember $true -DomainName 'jukebox.internal'
Set-DfsrMembership -GroupName 'ExampleMusic-Tools' -FolderName 'tools' -ComputerName 'EXADCSODE001' -ContentPath 'C:\DFSRoots\tools' -StagingPathQuotaInMB 16384 -DomainName 'jukebox.internal'
Set-DfsrMembership -GroupName 'ExampleMusic-Tools' -FolderName 'tools' -ComputerName 'EXADCSBRK001' -ContentPath 'C:\DFSRoots\tools' -StagingPathQuotaInMB 16384 -DomainName 'jukebox.internal'
```

### 7.5 Create Hub-Tier Replication Connections

Create bidirectional connections between FAL and each regional hub. Note: ODE and BRK do NOT connect directly to each other — all inter-hub traffic flows through FAL.

```powershell
# FAL <----> ODE (bidirectional)
Add-DfsrConnection -GroupName 'ExampleMusic-Tools' -SourceComputerName 'EXADCSFAL001' -DestinationComputerName 'EXADCSODE001' -DomainName 'jukebox.internal'
Add-DfsrConnection -GroupName 'ExampleMusic-Tools' -SourceComputerName 'EXADCSODE001' -DestinationComputerName 'EXADCSFAL001' -DomainName 'jukebox.internal'

# FAL <----> BRK (bidirectional)
Add-DfsrConnection -GroupName 'ExampleMusic-Tools' -SourceComputerName 'EXADCSFAL001' -DestinationComputerName 'EXADCSBRK001' -DomainName 'jukebox.internal'
Add-DfsrConnection -GroupName 'ExampleMusic-Tools' -SourceComputerName 'EXADCSBRK001' -DestinationComputerName 'EXADCSFAL001' -DomainName 'jukebox.internal'
```

### 7.6 Seed FAL from CPH

The data currently lives on `EXADCSCPH001`. Before CPH is added as a satellite member, the data needs to be copied to FAL so FAL becomes the primary. The cleanest method is robocopy:

Run on `EXADCSFAL001`:

```powershell
robocopy \\EXADCSCPH001\tools C:\DFSRoots\tools /MIR /COPYALL /DCOPY:DAT /R:3 /W:5 /LOG:C:\Logs\tools-seed.log
```

> ⚠ Run this robocopy during a maintenance window or off-peak hours. The `/MIR` flag will mirror the source exactly. Ensure no one is writing to the CPH share during this operation to avoid inconsistencies.

After robocopy completes, verify file counts match between source and destination before proceeding.

### 7.7 Monitor Initial Hub Sync

After connections are created, DFS-R will begin initial synchronisation between FAL and ODE, and FAL and BRK. Monitor progress:

```powershell
# Check replication state on FAL
Get-DfsrState -ComputerName EXADCSFAL001 -Verbose

# Check backlog between FAL and ODE
Get-DfsrBacklog -GroupName 'ExampleMusic-Tools' -FolderName 'tools' -SourceComputerName 'EXADCSFAL001' -DestinationComputerName 'EXADCSODE001' -DomainName 'jukebox.internal'
```

> ℹ A backlog of 0 on both hub connections indicates initial sync is complete. Only then proceed to section 8.

---

## 8. Configure DFS Replication — UK Satellites (FAL)

Once FAL has completed initial sync with ODE and BRK, add the UK satellite sites. These are MCR, LIV, GLA, and NEW — all syncing read-only from FAL.

### 8.1 Add UK Satellite Members

```powershell
$ukSatellites = @('EXADCSMCR001','EXADCSLIV001','EXADCSGLA001','EXADCSNEW001')
foreach ($s in $ukSatellites) { Add-DfsrMember -GroupName 'ExampleMusic-Tools' -ComputerName $s -DomainName 'jukebox.internal' }
```

### 8.2 Set Membership Paths — UK Satellites

```powershell
foreach ($s in $ukSatellites) { Set-DfsrMembership -GroupName 'ExampleMusic-Tools' -FolderName 'tools' -ComputerName $s -ContentPath 'C:\DFSRoots\tools' -StagingPathQuotaInMB 4096 -ReadOnly $true -DomainName 'jukebox.internal' }
```

### 8.3 Create Connections — UK Satellites (FAL as source)

UK satellites receive data from FAL only. Only one connection direction is needed per satellite (FAL → satellite). No reverse connection is required as the folders are read-only.

```powershell
foreach ($s in $ukSatellites) { Add-DfsrConnection -GroupName 'ExampleMusic-Tools' -SourceComputerName 'EXADCSFAL001' -DestinationComputerName $s -DomainName 'jukebox.internal' }
```

> ℹ Read-only members cannot originate changes so a reverse connection would serve no purpose. This also prevents any accidental writes from propagating up.

---

## 9. Configure DFS Replication — Danish Satellites (ODE)

Add CPH, KGE, and FAX as read-only satellites under ODE. Note that CPH is the original source of the data but is being repositioned as a satellite once FAL has the authoritative copy.

> ⚠ Confirm that the robocopy seed from CPH to FAL (section 7.6) is complete and that hub sync is confirmed healthy before adding CPH as a satellite member. Adding CPH before this could cause replication conflicts.

### 9.1 Add Danish Satellite Members

```powershell
$dkSatellites = @('EXADCSCPH001','EXADCSKGE001','EXADCSFAX001')
foreach ($s in $dkSatellites) { Add-DfsrMember -GroupName 'ExampleMusic-Tools' -ComputerName $s -DomainName 'jukebox.internal' }
```

### 9.2 Set Membership Paths — Danish Satellites

```powershell
foreach ($s in $dkSatellites) { Set-DfsrMembership -GroupName 'ExampleMusic-Tools' -FolderName 'tools' -ComputerName $s -ContentPath 'C:\DFSRoots\tools' -StagingPathQuotaInMB 4096 -ReadOnly $true -DomainName 'jukebox.internal' }
```

### 9.3 Create Connections — Danish Satellites (ODE as source)

```powershell
foreach ($s in $dkSatellites) { Add-DfsrConnection -GroupName 'ExampleMusic-Tools' -SourceComputerName 'EXADCSODE001' -DestinationComputerName $s -DomainName 'jukebox.internal' }
```

---

## 10. Configure DFS Replication — Americas/APAC Satellites (BRK)

Add TOR, MTL, and SYD as read-only satellites under BRK.

### 10.1 Add Americas/APAC Satellite Members

```powershell
$amSatellites = @('EXADCSTOR001','EXADCSMTL001','EXADCSSYD001')
foreach ($s in $amSatellites) { Add-DfsrMember -GroupName 'ExampleMusic-Tools' -ComputerName $s -DomainName 'jukebox.internal' }
```

### 10.2 Set Membership Paths — Americas/APAC Satellites

```powershell
foreach ($s in $amSatellites) { Set-DfsrMembership -GroupName 'ExampleMusic-Tools' -FolderName 'tools' -ComputerName $s -ContentPath 'C:\DFSRoots\tools' -StagingPathQuotaInMB 4096 -ReadOnly $true -DomainName 'jukebox.internal' }
```

### 10.3 Create Connections — Americas/APAC Satellites (BRK as source)

```powershell
foreach ($s in $amSatellites) { Add-DfsrConnection -GroupName 'ExampleMusic-Tools' -SourceComputerName 'EXADCSBRK001' -DestinationComputerName $s -DomainName 'jukebox.internal' }
```

> ℹ SYD is geographically distant from BRK. Initial sync may be slow depending on the WireGuard tunnel bandwidth. Consider scheduling the initial sync during off-peak Sydney hours and monitor staging folder utilisation on BRK.

---

## 11. Verification & Health Checks

### 11.1 DFS-R Health Check Commands

Run these commands from any DC with RSAT DFS tools installed:

```powershell
# Overall group health
Get-DfsReplicationGroup -GroupName 'ExampleMusic-Tools' -DomainName 'jukebox.internal'

# List all members
Get-DfsrMember -GroupName 'ExampleMusic-Tools' -DomainName 'jukebox.internal'

# Check backlog from FAL to all members
$members = Get-DfsrMember -GroupName 'ExampleMusic-Tools' -DomainName 'jukebox.internal'
foreach ($m in $members) {
    if ($m.ComputerName -ne 'EXADCSFAL001') {
        Get-DfsrBacklog -GroupName 'ExampleMusic-Tools' -FolderName 'tools' -SourceComputerName 'EXADCSFAL001' -DestinationComputerName $m.ComputerName -DomainName 'jukebox.internal'
    }
}

# Generate a full health report (HTML)
Write-DfsrHealthReport -GroupName 'ExampleMusic-Tools' -ReferenceComputerName 'EXADCSFAL001' -Path 'C:\Logs\DFSRHealth.html' -DomainName 'jukebox.internal'
```

### 11.2 DFS Namespace Verification

```powershell
# List namespace roots
Get-DfsnRoot -Path '\\jukebox.internal\shares'

# List namespace targets
Get-DfsnFolderTarget -Path '\\jukebox.internal\shares\tools'

# Test access from a client
dir \\jukebox.internal\shares\tools
```

### 11.3 Event Log Monitoring

DFS-R logs events to the DFS Replication event log on each member server. Key event IDs to monitor:

| Event ID | Meaning | Action |
|----------|---------|--------|
| 4102 | DFS-R service started | Informational |
| 4104 | Initial sync complete | Informational — confirm for each new member |
| 4204 | Staging quota has been exceeded | Increase staging quota on the affected member |
| 5002 | DFS-R has been disconnected from a partner | Investigate network/firewall between the pair |
| 5004 | DFS-R reconnected to a partner after a disconnection | Informational |
| 9026 | The DFS Replication service failed to update a file | Check NTFS permissions and disk space |

---

## 12. Ongoing Administration

### 12.1 Adding a New Share to the Namespace and Replication

When dedicated file servers are built out, or when a new share needs to be replicated estate-wide, the process is:

1. Create the folder and share on FAL (and hub servers if desired).
2. Add a new DFS namespace folder: `New-DfsnFolder` pointing at the new share.
3. Add a new replicated folder to the existing `ExampleMusic-Tools` replication group, or create a new replication group if the share has different membership requirements.
4. Set membership for all participating servers.
5. Create connections following the same hub-and-spoke topology.

### 12.2 Adding a New Site

To add a new site to the estate in future:

1. Promote a DC at the new site and confirm AD replication is healthy.
2. Create the local folder on the new DC.
3. Add the new DC as a member: `Add-DfsrMember`
4. Set membership with `-ReadOnly $true` and the appropriate staging quota.
5. Create a connection from the appropriate hub to the new member.
6. If the new site is itself a regional hub, create bidirectional connections to FAL.

### 12.3 Bandwidth Scheduling

DFS-R connections can be throttled by schedule to prevent replication traffic from saturating WAN links during business hours. Configure a schedule on hub-to-hub connections:

```powershell
# Example: throttle FAL-BRK to 1024Kbps (1MB) 08:00-18:00 Mon-Fri, unlimited outside those hours
$schedule = New-DfsrSchedule -Day Monday,Tuesday,Wednesday,Thursday,Friday -BandwidthDetail @{StartTime='08:00';EndTime='18:00';BandwidthLevel=1024}

Set-DfsrConnection -GroupName 'ExampleMusic-Tools' -SourceComputerName 'EXADCSFAL001' -DestinationComputerName 'EXADCSBRK001' -Schedule $schedule -DomainName 'jukebox.internal'
```

### 12.4 Staging Folder Sizing

The staging folder is one of the most commonly misconfigured aspects of DFS-R. If the staging quota is too small, DFS-R will delete staged files before they are transferred, causing re-transmission of entire files and poor replication performance.

- Minimum recommended: 4GB for satellite sites with low change rates
- Recommended for hub servers: 16GB or higher depending on share size and change rate
- Rule of thumb: staging quota should be at least 32x the size of the largest file being replicated
- Monitor Event ID 4204 (staging quota exceeded) and increase quotas proactively

```powershell
# Increase staging quota on a member
Set-DfsrMembership -GroupName 'ExampleMusic-Tools' -FolderName 'tools' -ComputerName 'EXADCSFAL001' -StagingPathQuotaInMB 32768 -DomainName 'jukebox.internal'
```

### 12.5 Removing a Member

```powershell
# Remove a satellite from replication
Remove-DfsrMember -GroupName 'ExampleMusic-Tools' -ComputerName 'EXADCSMCR001' -DomainName 'jukebox.internal' -Force
```

> ⚠ Removing a member does not delete the local data on that server. The replicated folder will remain on the server's disk but will no longer receive updates. Remove it manually if no longer needed.

---

## 13. Troubleshooting

### 13.1 Replication Not Starting

- Verify DFS Replication service is running on all members: `Get-Service DFSR`
- Verify firewall ports are open (section 4.4)
- Check AD replication is healthy first: `dcdiag /test:replications`
- DFS-R configuration changes replicate via AD before taking effect — allow up to 15 minutes after configuration changes for AD replication to propagate

### 13.2 Large Backlog Not Clearing

- Check available disk space on both source and destination
- Check staging folder size — Event ID 4204 indicates staging is full
- Check WAN link health to the affected site via `EXAFWL[SITE]001`
- Use dfsrdiag ReplicationState to get detailed sync status: `dfsrdiag ReplicationState /rgname:'ExampleMusic-Tools' /all`

### 13.3 DFS Namespace Target Not Available

- Verify the SMB share exists on the target server: `net share`
- Verify the DFS Namespace service (Dfs) is running on the namespace server
- Check namespace target is enabled: `Get-DfsnFolderTarget`
- Verify client is in the correct AD Site for referral ordering to work

### 13.4 Files Not Replicating from CPH After Seeding

If CPH was the original source and files written to CPH after the robocopy seed are not appearing on FAL:

- Confirm CPH has been added as a DFS-R member (section 9)
- Confirm the connection from ODE to CPH is established (CPH is under ODE, which gets data from FAL)
- Note that CPH as a read-only member cannot originate writes — any new data should be written to FAL or ODE directly

> ⚠ Once CPH is a read-only DFS-R member, any files written locally to `C:\DFSRoots\tools` on CPH will be moved to the `ConflictAndDeleted` folder and replaced with the version from ODE. Ensure all write operations are redirected to the hub servers.

---

## 14. Deployment Summary Checklist

Use this checklist to track progress through the deployment:

| # | Task | Completed |
|---|------|-----------|
| 1 | All 13 DCs promoted and AD replication healthy | ☐ |
| 2 | AD Sites and Services configured for all 13 sites | ☐ |
| 3 | DFS roles installed on all 13 DCs | ☐ |
| 4 | Firewall ports opened on all EXAFWL devices | ☐ |
| 5 | Folders created and shared on FAL, ODE, BRK | ☐ |
| 6 | Local folders created on all 10 satellite DCs | ☐ |
| 7 | DFS Namespace `\\jukebox.internal\shares` created | ☐ |
| 8 | `tools` namespace folder created with FAL/ODE/BRK targets | ☐ |
| 9 | Replication group `ExampleMusic-Tools` created | ☐ |
| 10 | Robocopy seed from CPH to FAL complete and verified | ☐ |
| 11 | Hub members (FAL/ODE/BRK) added and connections created | ☐ |
| 12 | FAL ↔ ODE initial sync confirmed complete (backlog = 0) | ☐ |
| 13 | FAL ↔ BRK initial sync confirmed complete (backlog = 0) | ☐ |
| 14 | UK satellites (MCR/LIV/GLA/NEW) added under FAL | ☐ |
| 15 | Danish satellites (CPH/KGE/FAX) added under ODE | ☐ |
| 16 | Americas/APAC satellites (TOR/MTL/SYD) added under BRK | ☐ |
| 17 | All satellite initial syncs confirmed complete | ☐ |
| 18 | DFS-R health report generated and reviewed | ☐ |
| 19 | Test file written on FAL, confirmed present on all members | ☐ |
| 20 | Bandwidth schedules configured on hub-to-hub WAN connections | ☐ |

---

## Naming Convention Reference

| Prefix | Role | Example |
|--------|------|---------|
| `EXAFWL` | Firewall | `EXAFWLFAL001` |
| `EXARTR` | Router | `EXARTRFAL001` |
| `EXASWI` | Switch | `EXASWIFAL001` |
| `EXADCS` / `EXADCR` | Domain Controller (site/regional) | `EXADCSFAL001` |
| `EXAPVE` | Proxmox VE node | `EXAPVEFAL001` |
| `EXASRV` | Server | `EXASVRCLD001` |
| `EXARAC` | Remote Access Console (DRAC/iLO/RAC emulator) | `EXARACFAL001` |
| `EXANAS` | NAS | `EXANASFAL001` |
| `EXASBC` | VOIP SBC — trunks to `EXACLDPBX001` | `EXASBCFAL001` |
| `EXAPBX` | PBX | `EXACLDPBX001` |
| `EXAPRV` | Provisioning / bootstrap server | `EXAPRVFAL001` |
| `EXAWAP` | WiFi Access Point | `EXAWAPFAL001` |
| `EXAWKS` | Workstation | `EXAWKSFAL001` |
| `EXALAP` | Laptop | `EXALAPFAL001` |
| `EXAMBP` | MacBook Pro | `EXAMBPFAL001` |
| `EXAMAC` | iMac | `EXAMACFAL001` |
| `EXASUR` | Surface | `EXASURFAL001` |
| `EXATAB` | Tablet | `EXATABFAL001` |
| `EXAPHN` | Phone | `EXAPHNFAL001` |
| `EXACAM` | Camera | `EXACAMFAL001` |
| `EXAVND` / `EXADON` | Vending machine | `EXAVNDFAL001` |
| `EXAMUS` | Jukebox / instrument | `EXAMUSFAL001` |
| `EXAPAY` | Payphone | `EXAPAYFAL001` |
| `EXANIX` | Unix / legacy system | `EXANIXPER001` |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
