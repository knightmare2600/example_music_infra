# Proxmox Datacenter Manager & Backup Server — Planning

**Document ID:** NET-PLAN-PDM-001  
**Classification:** Internal — Network Operations  
**Last Updated:** 2026-03-04  
**Status:** PLANNING — not yet in implementation

> This document covers two related Proxmox products: Proxmox Datacenter
> Manager (PDM) and Proxmox Backup Server (PBS). Both are planned for
> future implementation. A lab evaluation of PDM using nested
> virtualisation is the immediate next step — no production changes
> until evaluation is complete and enterprise support licensing is in place.

---

## Table of Contents

1. [What is Proxmox Datacenter Manager](#what-is-proxmox-datacenter-manager)
2. [What is Proxmox Backup Server](#what-is-proxmox-backup-server)
3. [How They Fit Together](#how-they-fit-together)
4. [Licensing — The Critical Constraint](#licensing--the-critical-constraint)
5. [Lab Evaluation — Nested PVE](#lab-evaluation--nested-pve)
6. [Planned Production Architecture — PDM](#planned-production-architecture--pdm)
7. [Planned Production Architecture — PBS](#planned-production-architecture--pbs)
8. [Implementation Phasing](#implementation-phasing)
9. [Related Documents](#related-documents)

---

## What is Proxmox Datacenter Manager

PDM is Proxmox's own official multi-cluster management plane — the
direct answer to VMware vCentre for the Proxmox ecosystem. It is built
and maintained by Proxmox Server Solutions GmbH (the same team that
builds PVE itself), which gives it native integration that third-party
tools like PegaProx cannot match.

A single PDM instance connects to all PVE clusters across all sites
via the Proxmox API. Each site's cluster appears as a "remote" in PDM.
From one browser window you can see and manage every VM, container,
node, storage pool, and backup datastore across the entire jukebox.internal
estate.

**Key capabilities:**

- Unified dashboard across all clusters and sites
- Cross-cluster live migration (move a VM from FAL to ODE without downtime)
- Centralised update management (see pending patches on all nodes, apply from one UI)
- VM and storage resource balancing across nodes
- Native Proxmox Backup Server integration — backup datastores appear
  alongside compute resources in the same view
- LDAP/AD and OpenID Connect authentication
- Role-based access control down to individual VM level
- Centralised SDN/EVPN management across sites
- Snapshot management across all clusters

**What it is not:**

PDM is a management and orchestration plane. It does not replace
Rudder for configuration management, does not manage non-Proxmox
infrastructure, and does not touch Windows or Linux guest OS configuration.
It is strictly a hypervisor-layer management tool.

---

## What is Proxmox Backup Server

PBS is a dedicated backup appliance for Proxmox environments. It runs
as its own ISO (like PVE itself) on dedicated hardware or a VM, and
provides enterprise-class backup capabilities specifically designed for
Proxmox workloads.

**Key capabilities:**

- Incremental, chunk-based, deduplicated backups — only changed blocks
  are transmitted after the first backup, dramatically reducing storage
  and network load
- Client-side encryption — backup data is encrypted before leaving the
  source node
- Ransomware protection — immutable backup retention with verify jobs
- Tape support for off-site archival
- S3-compatible object storage integration
- Backup verification jobs — PBS can restore and verify backup integrity
  automatically on a schedule, not just at restore time
- Proxmox VE integration — appears as a storage backend in PVE, backups
  scheduled directly from PVE or PBS

**What it is not:**

PBS is Proxmox-specific. It backs up PVE VMs and containers.
It does not back up Windows file shares, databases, or non-PVE workloads.
For those, you still need conventional backup tooling (Veeam, Bacula,
or similar). PBS covers the hypervisor layer; application-level backup
is a separate concern.

---

## How They Fit Together

```
                    ┌─────────────────────┐
                    │   PDM (at FAL)      │
                    │   Single pane       │
                    │   of glass          │
                    └──────┬──────────────┘
                           │ Proxmox API
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         FAL Cluster   ODE Cluster  BRK Cluster
         (PVE nodes)   (PVE nodes)  (PVE nodes)
              │            │            │
              ▼            ▼            ▼
         PBS at FAL    PBS at ODE   PBS at BRK
         (local VM     (local VM    (local VM
          backups)      backups)     backups)
```

PDM sees everything — compute and backup — in one unified view.
PBS instances are registered as remotes in PDM just like PVE clusters.
A backup job running on FAL's PVE cluster, storing to FAL's PBS instance,
shows up in PDM alongside the VM it's protecting.

---

## Licensing — The Critical Constraint

**PDM itself is free with active enterprise support subscriptions.**
There is no separate PDM licence key. However:

- PDM only works if the PVE clusters it manages have active enterprise
  support subscriptions
- PBS similarly has its own enterprise support subscription
- Without enterprise support, PDM cannot connect to the no-subscription
  PVE community repos

**Current status:** jukebox.internal runs on no-subscription community
repos. PDM cannot be used in production without purchasing enterprise
support for each PVE node.

**Cost model:** Proxmox enterprise support is licensed per CPU socket
per year. Current pricing is available at proxmox.com/en/proxmox-virtual-
environment/pricing — check for current rates as these change.

**The lab evaluation does not require licensing** — a nested PVE
instance running in a VM uses the no-subscription repo, and PDM can
connect to it for evaluation purposes. This is explicitly not production
use and carries no support obligations.

See the separate proposal document (`pdm-enterprise-proposal.docx`)
for the full cost-benefit analysis and licence recommendations
for budget approval.

---

## Lab Evaluation — Nested PVE

Before committing to enterprise licensing, evaluate PDM by running a
nested PVE instance inside an existing EXAPVEFAL001 VM. This costs
nothing and carries zero production risk.

### Nested PVE VM Specification

| Parameter | Value |
|-----------|-------|
| VM name | `LAB-PVE-NESTED-001` |
| Host | EXAPVEFAL001 |
| vCPU | 4 (with `host` CPU type for nested virt) |
| RAM | 8 GB |
| Disk | 60 GB |
| Network | Lab VLAN or isolated bridge |
| OS | Proxmox VE 9.1 (no-subscription) |
| Purpose | PDM evaluation target — not production |

### Enable Nested Virtualisation on the VM

```bash
# On EXAPVEFAL001 — enable nested virt for the lab VM
# Replace <VMID> with the lab VM's ID

# Check if nested virt is already enabled on the host
cat /sys/module/kvm_intel/parameters/nested
# or for AMD:
cat /sys/module/kvm_amd/parameters/nested
# Should return Y or 1

# Set CPU type to host in the VM config (required for nested PVE)
qm set <VMID> --cpu host

# Verify
qm config <VMID> | grep cpu
```

### Install PDM

PDM ships as an ISO or can be installed on an existing Debian/PVE system.
The easiest approach for lab evaluation is the ISO install on a small VM:

```bash
# Download PDM ISO from Proxmox
wget https://enterprise.proxmox.com/iso/proxmox-datacenter-manager_*.iso
# (or no-subscription equivalent — check downloads page)

# Or install on existing Debian node:
# Add PDM repo and install package
wget -qO - https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg \
    > /etc/apt/trusted.gpg.d/proxmox-release-bookworm.gpg

echo "deb https://pdm.proxmox.com/debian/pdm bookworm pdm-no-subscription" \
    > /etc/apt/sources.list.d/pdm.list

apt update && apt install -y proxmox-datacenter-manager
```

### Connect the Nested PVE as a Remote

1. Open PDM web UI: `https://<PDM-IP>:8443`
2. Navigate to **Remotes → Add Remote**
3. Enter the nested PVE IP and root credentials
4. PDM will discover clusters, nodes, VMs, and storage automatically

### What to Evaluate

During the lab evaluation, test and document:

- [ ] Cross-cluster migration works between nested PVE and a real test cluster
- [ ] AD/LDAP authentication connects and maps roles correctly
- [ ] Update management shows pending patches correctly
- [ ] PBS integration — add a PBS test instance and confirm backup visibility
- [ ] Performance overhead on the PDM node (RAM, CPU under load)
- [ ] Role-based access control — create read-only and operator roles
- [ ] API access — confirm automation hooks work for future Ansible integration

---

## Planned Production Architecture — PDM

Once licensing is in place, the production PDM deployment:

### PDM Server

| Parameter | Value |
|-----------|-------|
| Hostname | `EXAPDMFAL001` |
| Location | FAL — centralised, all sites connect to this |
| OS | PDM appliance (own ISO) or Debian |
| vCPU | 4 |
| RAM | 8 GB |
| Disk | 40 GB |
| IP | `192.168.76.13` |
| Web UI | `https://192.168.76.13:8443` |

### Remotes (Sites Managed)

Each site's PVE cluster is registered as a remote in PDM.
The connection travels over WireGuard for non-FAL sites.

| Remote name | Type | Address |
|-------------|------|---------|
| FAL-cluster | PVE | 192.168.76.5 |
| ODE-cluster | PVE | 192.168.126.5 |
| BRK-cluster | PVE | 192.168.136.5 |
| FAL-backup | PBS | 192.168.76.14 |
| ODE-backup | PBS | 192.168.126.14 |
| BRK-backup | PBS | 192.168.136.14 |
| (all spoke sites) | PVE | per network-inventory.md |

---

## Planned Production Architecture — PBS

One PBS instance per hub site minimum. Spoke sites back up to their
regional hub PBS over WireGuard.

### PBS Node Specification (per hub)

| Parameter | Value |
|-----------|-------|
| Hostname pattern | `EXAPBSFAL001`, `EXAPBSODE001`, `EXAPBSBRK001` |
| OS | Proxmox Backup Server (own ISO) |
| vCPU | 4 |
| RAM | 8 GB |
| OS Disk | 32 GB |
| Backup Datastore Disk | Size TBD — depends on VM count and retention |
| IP convention | `192.168.<octet>.14` |

### Backup Architecture

```
Spoke sites → backup to regional hub PBS over WireGuard
Hub sites   → backup to local PBS, replicate to tape/S3 for off-site

FAL VMs  → EXAPBSFAL001 (local)
EDI VMs  → EXAPBSFAL001 (over WireGuard — EDI is UK spoke)
ODE VMs  → EXAPBSODE001 (local EU hub)
MUN VMs  → EXAPBSODE001 (over WireGuard — MUN is EU spoke)
BRK VMs  → EXAPBSBRK001 (local NA hub)
NYC VMs  → EXAPBSBRK001 (over WireGuard — NYC is NA spoke)
```

### Retention Policy (proposed)

| Backup type | Retention |
|-------------|-----------|
| Daily | 7 days |
| Weekly | 4 weeks |
| Monthly | 6 months |
| Yearly | 2 years |

These are starting points — adjust per VM criticality and storage budget.

---

## Implementation Phasing

| Phase | Action | Prerequisite |
|-------|--------|-------------|
| Now | Lab evaluation — nested PVE + PDM | EXAPVEFAL001 online |
| Budget approval | Enterprise support subscriptions purchased | Proposal approved |
| PBS Phase 1 | Deploy EXAPBSFAL001 at FAL | Enterprise support active |
| PBS Phase 2 | Deploy EXAPBSODE001 and EXAPBSBRK001 | PBS Phase 1 complete |
| PDM Phase 1 | Deploy EXAPDMFAL001 | Enterprise support active on all clusters |
| PDM Phase 2 | Register all site clusters as remotes | WireGuard fabric stable |
| PDM Phase 3 | Configure RBAC, AD integration, automation hooks | PDM Phase 1-2 complete |

---

## Related Documents

| Document | Relationship |
|----------|-------------|
| `pdm-enterprise-proposal.docx` | Budget proposal for enterprise support licensing |
| `proxmox/pve-networking.md` | Network config PDM connects through |
| `wireguard/wireguard-troubleshooting.md` | Cross-site PDM-to-cluster connectivity |
| `network-inventory.md` | IP assignments for PDM and PBS nodes |
| `buildsheets/buildsheet-pve.md` | PVE build process PDM nodes follow |

---

*Internal Use Only — Network Engineering — jukebox.internal*
