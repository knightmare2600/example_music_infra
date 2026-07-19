# Infrastructure Proposal — Proxmox Enterprise Support, Datacenter Manager & Backup Server

**Document Reference:** NET-PROP-PDM-001
**Prepared by:** Network Engineering
**Date:** March 2026 (architecture reworked 2026-07-19)
**Status:** Draft — Awaiting Approval
**Classification:** Confidential — Internal Distribution Only

> **Reworked 2026-07-19 (Robert):** the original architecture (below tables) put PDM and PBS at
> three "regional hubs" (FAL, ODE, BRK). That model is retired — CLD is now the estate's sole
> WireGuard hub, and FAL/ODE/BRK are ordinary spokes (still real AD/DFS hubs, just not WireGuard
> ones). This revision centralises **management** at CLD (`EXADCMCLD001`, one instance) and fully
> **decentralises backup** — every site, including CLD, gets its own local PBS instance. See
> `proxmox/proxmox-dcm-pbs-planning.md` for the full technical rationale and addressing detail.

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

> **Key Recommendation:** Purchase Proxmox VE Enterprise Support for CLD first, and evaluate PDM in a lab environment immediately. Deploy `EXADCMCLD001` (management) and `EXAPBSCLD001` (CLD's own local backup) as the first production site, then roll enterprise support and a local PBS out to the rest of the fleet site by site. There is no longer a "hub tier" to prioritise — every site's PBS deployment is identical in spec, so phasing is a rollout-pace decision, not an architectural one.

---

## Background and Current State

Example Music Group operates Proxmox VE across a growing estate — **53 sites** as of 2026-07-19, per `benarbejde/sites.csv` (re-derive this count at rollout time; it changes as the estate grows, don't treat this document's snapshot as current). Every site connects directly to CLD, the estate's sole WireGuard hub — no site intermediates WireGuard traffic for another. Each site runs one or more PVE nodes hosting virtual machines for domain controllers, file servers, firewall appliances, and application workloads.

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

PDM provides a single unified management interface for the entire Proxmox estate. In this estate it is deployed as one instance, `EXADCMCLD001`, at CLD — every site's cluster and every site's local PBS connect to it over WireGuard, via CLD as the sole hub. From a single browser window, administrators can see and manage every VM, container, node, storage pool, and backup datastore globally.

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

PBS is a purpose-built backup appliance for Proxmox workloads. It provides incremental, deduplicated, encrypted backups of VMs and containers, with built-in integrity verification and ransomware-resistant retention policies. In this estate, **every site gets its own local PBS instance** — backup data never crosses a WAN link.

| PBS Feature | Why It Matters |
|-------------|---------------|
| Incremental deduplicated backups | Only changed data is transmitted after the first backup. A 100GB VM with 1GB of daily changes transfers 1GB, not 100GB. Backup traffic stays entirely on the site's own LAN — this matters for storage/disk I/O, not WireGuard, since every site now backs up locally. |
| Client-side encryption | Backup data is encrypted before leaving the source node. Backup storage compromise does not expose VM data. |
| Ransomware protection | Immutable retention policies prevent backup deletion within the retention window, even by a compromised administrator account. |
| Automated verify jobs | PBS can automatically restore and verify backup integrity on a schedule. Backups are proven restorable without manual testing. |
| PDM integration | Every site's PBS instance appears alongside its PVE cluster in PDM. Backup status visible for every VM in the unified dashboard, regardless of how many sites there are. |

---

## Proposed Architecture

### Centralised Management, Decentralised Backup

One PDM instance at CLD manages every site. Every site — CLD included — has its own local PBS instance; backup data never leaves the site it was taken from.

```
                    ┌─────────────────────┐
                    │   EXADCMCLD001      │
                    │   PDM               │
                    │   Single pane       │
                    │   of glass          │
                    └──────┬──────────────┘
                           │ Proxmox API, over WireGuard (CLD is the sole hub)
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    CLD Cluster        FAL Cluster       ... every other
    (PVE nodes,        (PVE nodes)       site's cluster
     local)                                  │
         │                 │                 ▼
         ▼                 ▼            EXAPBS<SITE>001
    EXAPBSCLD001       EXAPBSFAL001      (local backup —
    (local backup)     (local backup —    never leaves
                         never leaves      that site)
                         FAL's LAN)
```

### Node Summary

| Node | Site | Type | Role |
|------|------|------|------|
| `EXADCMCLD001` | CLD | VM (Debian/PDM appliance) | PDM — manages all sites |
| `EXAPBS<SITE>001` | every site (53, growing) | Dedicated server or VM | PBS — that site's own local backups only |

### Connectivity

PDM-to-cluster and PDM-to-PBS **status/management** traffic for every non-CLD site travels over the existing WireGuard fabric, via CLD as the sole hub — no additional network infrastructure required. Actual **backup data transfer** (PVE → PBS) never touches WireGuard, or any WAN link, at any site — it is local-LAN traffic only, at every single site including CLD.

### Addressing (proposed, pending approval)

`EXADCMCLD001` at `192.168.69.13`; `EXAPBS<SITE>001` at `192.168.<site-octet>.14` on each
site's own subnet — both collision-checked against `benarbejde/address_policy.json` and every
real `benarbejde/devices.csv` row. Full rationale, exact collision checks, and the rollout
procedure (once approved) are in `proxmox/proxmox-dcm-pbs-planning.md`.

### Lab Evaluation (Pre-Licensing)

A nested PVE virtualisation lab environment has been scoped on EXAPVEFAL001 to evaluate PDM before committing to enterprise licensing. This uses Proxmox's no-subscription community repos and carries zero cost and zero production risk. See `proxmox/proxmox-dcm-pbs-planning.md` for the full lab evaluation procedure. The lab node's location (FAL) is unrelated to production placement — production `EXADCMCLD001` is built at CLD.

---

## Implementation Phasing

| Phase | Timing | Actions | Licences Required |
|-------|--------|---------|------------------|
| 0 | Now — no cost | Lab evaluation: nested PVE on EXAPVEFAL001, PDM test instance. Validate functionality before purchase. | None |
| 1 | Q2 2026 | Enterprise support for CLD's PVE node(s). Deploy `EXADCMCLD001`. Deploy `EXAPBSCLD001` — CLD's own local backup, and the first real-world proof of the per-site PBS pattern. | CLD only |
| 2 | Q3 2026+ | Roll enterprise support and a local `EXAPBS<SITE>001` out across the rest of the fleet, one site at a time — not a single estate-wide blast. Register each site's cluster and PBS as PDM remotes as it comes online. Configure RBAC and AD auth once a meaningful number of sites are registered. | Per-site, as onboarded |

There is deliberately no more "hub sites first, spokes deferred to Phase 3" tier — every site's
PBS deployment is now architecturally identical, so Phase 2's ordering is a rollout-pace and
budget decision each cycle, not something this document needs to fix in advance.

---

## Cost Considerations

### Proxmox Enterprise Support Pricing

Proxmox enterprise support is licensed per CPU socket per year. Current pricing is available at `proxmox.com/en/proxmox-virtual-environment/pricing` — the figures below are indicative and should be verified against current Proxmox pricing before budget approval.

| Site / Tier | Nodes | Sockets/Node | Total Sockets | Notes |
|-------------|-------|-------------|--------------|-------|
| CLD | 1+ (per `sites.csv`/`address_policy.json` PVE slots) | 1–2 | TBD | Phase 1 |
| Remaining fleet (52 sites and growing) | 1+ per site | 1–2 | TBD | Phase 2, rolled out incrementally |
| PBS nodes (one per site, 53 and growing) | 53 | 1 | ~53 | PBS also licensed — one per site now, not one per regional hub |

> **This table is deliberately a formula, not a fixed number** — the old (March 2026) version of
> this proposal counted "~30 sites" and three hub tiers; the real count is 53 sites today and
> growing, and there is no hub tier left to count separately. Re-derive actual node/socket counts
> from `pvesh get /nodes` or `benarbejde/address_policy.json`'s PVE slots at the point of ordering
> — this document should never be the source of truth for a live socket count. Each physical CPU
> socket requires one licence. Most 1U/2U servers are single or dual socket. Check with hardware
> vendor or `ipmitool`.

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
| VM data loss due to no backup (current state) | **High** | PBS deployment in Phase 1 (CLD) eliminates this risk at CLD immediately; Phase 2 eliminates it fleet-wide as each site is onboarded. Lab evaluation in Phase 0 validates backup and restore procedures before go-live. |
| PDM stability risk (currently in beta) | Low | PDM is a management plane only — it does not sit in the data path. A PDM outage means loss of the unified UI, not loss of VMs or services. PVE clusters continue operating independently, and — unlike a PDM outage — **backup jobs are entirely unaffected**, since PBS is per-site and local, not routed through PDM. |
| Enterprise support cost exceeds budget | Medium | Phase 1 covers CLD only (one site). The rest of the fleet is deliberately incremental in Phase 2, paced to budget rather than committed all at once. |
| WireGuard instability affecting PBS backup traffic | **None** — eliminated by this design, not just mitigated | Backup data never travels over WireGuard at any site, including spokes — every site backs up to its own local PBS over its own LAN. This is a strict improvement over the original (March 2026) design, where only hub-site backups were WireGuard-independent; every site's backup now is. |

---

## Recommendation and Approval Request

Network Engineering recommends the following actions for approval:

| # | Action | Timing |
|---|--------|--------|
| 1 | Approve lab evaluation of PDM using nested virtualisation on existing hardware (zero cost) | Immediate |
| 2 | Approve budget for Proxmox VE Enterprise Support for CLD's PVE node(s) | Q2 2026 |
| 3 | Approve deployment of `EXADCMCLD001` and `EXAPBSCLD001` at CLD | Q2 2026 |
| 4 | Approve the `.13`/`.14` addressing reservations in `proxmox/proxmox-dcm-pbs-planning.md` for write-in to `benarbejde/address_policy.json`/`devices.csv` | Q2 2026 |
| 5 | Approve incremental fleet-wide rollout (Phase 2), paced per available budget, not deferred to a fixed future quarter | Q3 2026+ |

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
| `proxmox/proxmox-dcm-pbs-planning.md` | Technical planning document this proposal is based on — full addressing rationale and rollout procedure |
| `ansible/README.md` | Current WireGuard topology (CLD sole hub) this design is built around |
| `docs/ansible/beginners_guide_to_ansible.md` | "Renumbering / Reworking Live Conventions" — the methodology for rolling the proposed addressing out safely once approved |
| `proxmox/pve-networking.md` | Network PDM connects through |
| `wireguard/wireguard-troubleshooting.md` | Cross-site PDM-to-cluster connectivity |
| `network-inventory.md` | IP assignments for planned PDM and PBS nodes |

---

*Internal Use Only — Network Engineering — jukebox.internal*
