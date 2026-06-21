# Infrastructure Proposal — Proxmox Enterprise Support, Datacenter Manager & Backup Server

**Document Reference:** NET-PROP-PDM-001  
**Prepared by:** Network Engineering  
**Date:** March 2026  
**Status:** Draft — Awaiting Approval  
**Classification:** Confidential — Internal Distribution Only

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Background and Current State](#background-and-current-state)
3. [Proposed Solution](#proposed-solution)
4. [Proposed Architecture](#proposed-architecture)
5. [Implementation Phasing](#implementation-phasing)
6. [Cost Considerations](#cost-considerations)
7. [Risks and Mitigations](#risks-and-mitigations)
8. [Recommendation and Approval Request](#recommendation-and-approval-request)

---

## Executive Summary

Example Music Group is completing a major infrastructure modernisation programme, migrating from VMware to Proxmox VE across all office locations. As this platform matures, two critical capability gaps have been identified that require investment to address properly: **unified multi-site management** and **reliable VM backup**.

This proposal requests budget approval for Proxmox Enterprise Support subscriptions across the production fleet, which will unlock two additional products at no extra licence cost: **Proxmox Datacenter Manager (PDM)** and **Proxmox Backup Server (PBS)**.

> **Key Recommendation:** Purchase Proxmox VE Enterprise Support for all production PVE nodes at hub sites (FAL, ODE, BRK) and evaluate PDM in a lab environment immediately. Roll enterprise support out to spoke sites in a second phase once hub management is proven.

---

## Background and Current State

Example Music Group operates Proxmox VE across multiple sites globally, connected via a WireGuard VPN mesh in a hub-and-spoke topology. The three regional hubs are Falkirk (FAL, UK), Odense (ODE, EU), and Brooklyn (BRK, NA). Each site runs one or more PVE nodes hosting virtual machines for domain controllers, file servers, firewall appliances, and application workloads.

Currently, each PVE cluster is managed independently through its own web interface. There is no unified view of the estate, no centralised backup infrastructure, and no mechanism for cross-site VM migration. Administrators must log in to individual cluster nodes to perform maintenance, apply updates, or investigate issues. As the number of managed nodes grows, this approach becomes unsustainable.

### What We Have Today

| Area | Current State |
|------|--------------|
| VM management | Per-cluster, per-node login required. No unified view. |
| Backup | No centralised backup infrastructure in place. At risk. |
| Cross-site migration | Not possible without manual export/import. |
| Patch management | Manual, per-node. No visibility across estate. |
| Access control | Local PVE accounts only. No AD integration at hypervisor layer. |
| Licensing | No-subscription community repos. No enterprise support. |

### Risk of Current State

- No VM backup means any hardware failure results in permanent data and service loss.
- Manual patch management across a growing node estate creates security exposure.
- No cross-site failover capability means a site outage takes services offline with no recovery path.
- Community repositories receive updates after enterprise repos — security patches arrive later.

---

## Proposed Solution

### Proxmox Enterprise Support

Proxmox Enterprise Support subscriptions are purchased per CPU socket per year. They provide access to the enterprise package repository (updated before community repos), official support from Proxmox Server Solutions GmbH, and — critically — they unlock both PDM and PBS as included products at no additional cost.

> There is no separate licence for PDM or PBS. Both are included with active enterprise support subscriptions on the managed infrastructure. This makes the effective cost of PDM and PBS zero once enterprise support is in place.

### Proxmox Datacenter Manager (PDM)

PDM provides a single unified management interface for the entire Proxmox estate. One PDM instance connects to all PVE clusters and PBS instances across all sites. From a single browser window, administrators can see and manage every VM, container, node, storage pool, and backup datastore globally.

| PDM Capability | VMware Equivalent | Business Value |
|----------------|-------------------|---------------|
| Unified multi-cluster dashboard | vCentre | Single pane of glass — no more per-node logins |
| Cross-cluster live migration | vMotion | Maintenance without downtime, cross-site failover |
| VM resource balancing | DRS | Automatic workload distribution, no overloaded nodes |
| CPU compatibility alignment | EVC | Safe migrations across mixed-generation hardware |
| Centralised patch management | vCentre Lifecycle Manager | Consistent patching across all nodes from one UI |
| AD/LDAP authentication | vCentre SSO | IT staff use AD credentials, no separate accounts |
| Role-based access control | vCentre permissions | Granular delegation, audit trail, least-privilege |

### Proxmox Backup Server (PBS)

PBS is a purpose-built backup appliance for Proxmox workloads. It provides incremental, deduplicated, encrypted backups of VMs and containers, with built-in integrity verification and ransomware-resistant retention policies.

| PBS Feature | Why It Matters |
|-------------|---------------|
| Incremental deduplicated backups | Only changed data is transmitted after the first backup. A 100GB VM with 1GB of daily changes transfers 1GB, not 100GB. Dramatically reduces network load over WireGuard. |
| Client-side encryption | Backup data is encrypted before leaving the source node. Backup storage compromise does not expose VM data. |
| Ransomware protection | Immutable retention policies prevent backup deletion within the retention window, even by a compromised administrator account. |
| Automated verify jobs | PBS can automatically restore and verify backup integrity on a schedule. Backups are proven restorable without manual testing. |
| PDM integration | PBS instances appear alongside PVE clusters in PDM. Backup status visible for every VM in the unified dashboard. |

---

## Proposed Architecture

### Hub-and-Spoke Model

One PDM instance at FAL (UK head office hub) and one PBS instance at each of the three regional hubs (FAL, ODE, BRK). Spoke sites back up to their regional hub PBS over the existing WireGuard fabric. All sites are managed through the single PDM instance at FAL.

```
                    ┌─────────────────────┐
                    │   EXAPDMFAL001      │
                    │   PDM               │
                    │   Single pane       │
                    │   of glass          │
                    └──────┬──────────────┘
                           │ Proxmox API over WireGuard
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         FAL Cluster   ODE Cluster  BRK Cluster
         (PVE nodes)   (PVE nodes)  (PVE nodes)
              │            │            │
              ▼            ▼            ▼
         EXAPBSFAL001  EXAPBSODE001 EXAPBSBRK001
         UK backups    EU backups   NA/Pacific
                                    backups
```

### Node Summary

| Node | Site | Type | Role |
|------|------|------|------|
| `EXAPDMFAL001` | FAL | VM (Debian/PDM appliance) | PDM — manages all sites |
| `EXAPBSFAL001` | FAL | Dedicated server | PBS — UK backups |
| `EXAPBSODE001` | ODE | Dedicated server | PBS — EU backups |
| `EXAPBSBRK001` | BRK | Dedicated server | PBS — NA/Pacific backups |

### Connectivity

All PDM-to-cluster and VM-to-PBS communication for non-FAL sites travels over the existing WireGuard VPN fabric. No additional network infrastructure is required.

### Lab Evaluation (Pre-Licensing)

A nested PVE virtualisation lab environment has been scoped on EXAPVEFAL001 to evaluate PDM before committing to enterprise licensing. This uses Proxmox's no-subscription community repos and carries zero cost and zero production risk. See `proxmox/proxmox-dcm-pbs-planning.md` for the full lab evaluation procedure.

---

## Implementation Phasing

| Phase | Timing | Actions | Licences Required |
|-------|--------|---------|------------------|
| 0 | Now — no cost | Lab evaluation: nested PVE on EXAPVEFAL001, PDM test instance. Validate functionality before purchase. | None |
| 1 | Q2 2026 | Enterprise support for FAL, ODE, BRK hub PVE nodes. Deploy EXAPBSFAL001. Deploy EXAPDMFAL001. | Hub nodes only |
| 2 | Q3 2026 | Deploy EXAPBSODE001, EXAPBSBRK001. Register all clusters in PDM. Configure RBAC and AD auth. | Hub nodes |
| 3 | Q4 2026+ | Roll enterprise support to spoke sites as estate grows. Spoke VMs back up to regional hub PBS. | Spoke nodes |

---

## Cost Considerations

### Proxmox Enterprise Support Pricing

Proxmox enterprise support is licensed per CPU socket per year. Current pricing is available at `proxmox.com/en/proxmox-virtual-environment/pricing` — the figures below are indicative and should be verified against current Proxmox pricing before budget approval.

| Site / Tier | Nodes | Sockets/Node | Total Sockets | Notes |
|-------------|-------|-------------|--------------|-------|
| FAL hub | 3 (EXAPVEFAL001–003) | 1–2 | 3–6 | Phase 1 |
| ODE hub | 2 (EXAPVEODE001–002) | 1–2 | 2–4 | Phase 1 |
| BRK hub | 2 (EXAPVEBRK001–002) | 1–2 | 2–4 | Phase 1 |
| Spoke sites (all) | 1 per site (~30 sites) | 1 | ~30 | Phase 3 |
| PBS nodes (3 hubs) | 3 | 1 | 3 | PBS also licensed |

> Verify exact socket counts per node before ordering. Each physical CPU socket requires one licence. Most 1U/2U servers are single or dual socket. Check with hardware vendor or `ipmitool`.

### What Enterprise Support Includes

- Access to Proxmox enterprise apt repositories (security patches before community release)
- Proxmox Datacenter Manager — included, no extra cost
- Proxmox Backup Server — separate product, included with active support
- Direct technical support from Proxmox Server Solutions GmbH
- Access to customer portal and release notes

### Cost-Benefit Summary

The enterprise support cost purchases three things simultaneously: faster security patches, official vendor support, and unlocks both PDM and PBS — which together eliminate the two largest operational gaps in the current infrastructure. Evaluated against the cost of a single serious incident caused by the absence of either — a VM loss with no backup, or a prolonged outage requiring manual node-by-node remediation — the subscription cost is readily justified.

---

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| VM data loss due to no backup (current state) | **High** | PBS deployment in Phase 1 eliminates this risk. Lab evaluation in Phase 0 validates backup and restore procedures before go-live. |
| PDM stability risk (currently in beta) | Low | PDM is a management plane only — it does not sit in the data path. A PDM outage means loss of the unified UI, not loss of VMs or services. PVE clusters continue operating independently. |
| Enterprise support cost exceeds budget | Medium | Phase 1 covers hub nodes only. Spoke sites deferred to Phase 3. Hub-only licensing delivers PDM and hub PBS at minimum cost. |
| WireGuard instability affecting PBS backup traffic | Low | PBS incremental deduplication means only changed blocks transfer. Backup jobs resume from where they failed. Hub sites back up locally — no WireGuard dependency for hub PBS. |

---

## Recommendation and Approval Request

Network Engineering recommends the following actions for approval:

| # | Action | Timing |
|---|--------|--------|
| 1 | Approve lab evaluation of PDM using nested virtualisation on existing hardware (zero cost) | Immediate |
| 2 | Approve budget for Proxmox VE Enterprise Support for FAL, ODE and BRK hub PVE nodes | Q2 2026 |
| 3 | Approve procurement of dedicated hardware for EXAPBSFAL001 (FAL backup server) | Q2 2026 |
| 4 | Defer spoke site licensing to Phase 3 pending hub rollout success | Q4 2026 |

> This proposal covers infrastructure licensing only. Application-level backup (file shares, databases, Microsoft 365) is a separate workstream and is not in scope for this document.

### Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Network Lead | | | |
| IT Manager | | | |
| Finance Approver | | | |
| Director | | | |

---

## Related Documents

| Document | Relationship |
|----------|-------------|
| `proxmox/proxmox-dcm-pbs-planning.md` | Technical planning document this proposal is based on |
| `proxmox/pve-networking.md` | Network PDM connects through |
| `wireguard/wireguard-troubleshooting.md` | Cross-site PDM-to-cluster connectivity |
| `network-inventory.md` | IP assignments for planned PDM and PBS nodes |

---

*Internal Use Only — Network Engineering — jukebox.internal*
