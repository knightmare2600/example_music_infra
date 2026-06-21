# PegaProx — Evaluation and Decision Record

**Document ID:** NET-EVAL-PEGAPROX-001  
**Classification:** Internal — Network Engineering  
**Last Updated:** 2026-03-04  
**Status:** Evaluated — Not Adopted

> This document records the evaluation of PegaProx as a Proxmox
> multi-cluster management tool and the decision to adopt Proxmox
> Datacenter Manager (PDM) instead. It exists so this ground does
> not get re-covered in the future.

---

## Table of Contents

1. [What is PegaProx](#what-is-pegaprox)
2. [Why It Was Evaluated](#why-it-was-evaluated)
3. [What It Does Well](#what-it-does-well)
4. [Why PDM Was Chosen Instead](#why-pdm-was-chosen-instead)
5. [When PegaProx Would Be the Right Choice](#when-pegaprox-would-be-the-right-choice)
6. [Summary Decision](#summary-decision)
7. [Related Documents](#related-documents)

---

## What is PegaProx

PegaProx is an open-source, community-developed unified management
platform for Proxmox VE clusters. It is built by a small independent
team (Nico Schmidt, Marcus Kellermann, Laura Weber) and provides a
single web UI that connects to multiple Proxmox clusters via SSH and
the Proxmox API.

**Source:** `https://pegaprox.com`  
**GitHub:** `https://github.com/PegaProx/project-pegaprox`  
**Licence:** Open source  
**Cost:** Free

### Installation

PegaProx ships as a ready-to-use appliance (LXC or VM), a deployment
script, or a manual git clone. It also has Docker support. The VM
appliance is the recommended production installation method — the LXC
appliance does not support live migration of containers due to Proxmox
limitations.

```bash
# Quickest evaluation — Docker
docker run -p 5000:5000 cr.gyptazy.com/pegaprox/pegaprox:latest

# Or import the VM appliance directly into an existing PVE cluster
# https://cdn.gyptazy.com/proxmox/pegaprox/images/vzdump-qemu-109-2026_01_25-12_25_45.vma.zst
```

Web UI listens on port `5000`. Default credentials: `pegaprox` / `admin`.

### How It Connects to PVE

PegaProx connects to Proxmox clusters using SSH first (some features
are not available in the Proxmox API and require SSH access), then
also via the Proxmox API. There is no agent to install on PVE nodes —
PegaProx reaches out to them. There is no practical limit on the number
of clusters that can be connected.

---

## Why It Was Evaluated

During infrastructure planning, the need for a unified management plane
across all jukebox.internal PVE clusters was identified. PegaProx was
surfaced as a promising open-source option that addressed this gap
without requiring enterprise licensing. It was evaluated on its merits
before Proxmox's own PDM product was fully understood.

---

## What It Does Well

PegaProx is a genuinely impressive project for its size and origin.
The feature set it delivers for a free, open-source tool is substantial:

- **Unified multi-cluster dashboard** — all PVE clusters, nodes, VMs, and
  containers in one view. Works well.
- **VM and storage resource scheduling** — integrates the author's own
  ProxLB load balancing logic, which is a proven and widely used tool.
- **CPU compatibility alignment** — integrates ProxCLMC to determine the
  safe baseline CPU type across mixed-generation nodes before live migration.
- **Cross-cluster live migration** — with pre-flight validation that checks
  for common blockers (attached ISOs, storage availability) before starting.
- **Snapshot management** — cluster-wide snapshot overview, sorted by age.
  Makes it easy to identify and clean up forgotten snapshots.
- **Node patch management** — can display and apply pending updates directly
  from the UI, using SSH since the Proxmox API does not expose this.
- **Tenancy and RBAC** — users, groups, tenancies, and per-resource permissions.
- **Themes** — multiple UI themes, dark mode included.
- **No licensing cost** — completely free.

For a small team building something useful for the Proxmox community,
this is a solid piece of work.

---

## Why PDM Was Chosen Instead

The decision to adopt PDM over PegaProx comes down to four factors:

### 1. PDM is the Official Proxmox Product

PDM is built and maintained by Proxmox Server Solutions GmbH — the same
team that builds PVE itself. This means:

- API access is first-class, not a workaround. PegaProx uses SSH for
  some operations because the Proxmox API does not expose them. PDM
  gets API access to things PegaProx cannot reach without SSH hacks,
  because Proxmox can add the endpoints PDM needs.
- PDM is on the Proxmox release cycle. When PVE 10 ships, PDM will
  support it on day one. PegaProx depends on a small volunteer team
  keeping up.
- Bugs in PDM are bugs in a supported product with a vendor to raise
  them with. Bugs in PegaProx are GitHub issues that may or may not
  be addressed.

### 2. Native PBS Integration

PDM treats Proxmox Backup Server instances as first-class remotes,
appearing alongside PVE clusters in the same unified dashboard. Backup
status is visible for every VM. PegaProx has no PBS integration — it
manages compute only.

For jukebox.internal, where PBS is a core part of the planned
infrastructure, this is a significant gap in PegaProx's capability.

### 3. Cost is the Same

The decision is sometimes framed as "free PegaProx vs paid PDM."
This framing is wrong for jukebox.internal. PDM is included with
Proxmox enterprise support subscriptions, which are being purchased
for other reasons (faster security patches, vendor support, PBS).
Once enterprise support is in place, PDM costs nothing additional.
The marginal cost of PDM over PegaProx is zero.

### 4. Production Stability Expectations

PegaProx is currently at version `0.6b` — a beta. For a lab
environment or a homelab, this is fine. For infrastructure managing
production workloads across 40+ sites, a beta with no commercial
backing and a three-person development team carries more operational
risk than is acceptable.

PDM is also relatively new, but it is a supported product from an
established vendor with a commercial interest in its stability.

### Comparison Summary

| Factor | PegaProx | PDM |
|--------|----------|-----|
| Cost | Free | Included with enterprise support |
| Vendor | Community (3 developers) | Proxmox Server Solutions GmbH |
| PVE API access | SSH + API (some limitations) | Full native API |
| PBS integration | None | Full — first-class remote |
| Maturity | v0.6b (beta) | Active development, vendor-supported |
| Support | GitHub issues | Official Proxmox support |
| AD/LDAP auth | Yes | Yes |
| Cross-cluster migration | Yes | Yes |
| VM balancing | Yes (ProxLB) | Yes |
| Snapshot management | Yes (ProxSnap) | Yes |
| Node patch management | Yes (SSH-based) | Yes |
| RBAC / tenancy | Yes | Yes |
| SDN / EVPN management | No | Yes |

---

## When PegaProx Would Be the Right Choice

PegaProx is the right choice in one specific scenario: you need unified
Proxmox management, you are not purchasing enterprise support for other
reasons, and you accept the community-supported stability profile.

If jukebox.internal were running a smaller estate with no PBS requirement,
no plans for enterprise support, and a higher tolerance for beta software,
PegaProx would be a reasonable choice and worth deploying. It is not
the wrong tool — it is the wrong tool *for this situation*.

It is worth watching. If the project matures, adds PBS integration, and
reaches a stable release, the comparison changes. The decision recorded
here is for March 2026 and should be revisited if circumstances change.

---

## Summary Decision

**PegaProx is not being adopted for jukebox.internal.**

The decision is not a reflection on the quality of the project — it
is a good piece of open-source software. The decision reflects that
PDM is the officially supported Proxmox product, is included in the
enterprise support cost already being incurred, and provides native
PBS integration that PegaProx does not offer.

PegaProx may be worth re-evaluating if enterprise support subscriptions
are not renewed, or if PDM proves unstable in the lab evaluation.

---

## Related Documents

| Document | Relationship |
|----------|-------------|
| `proxmox/proxmox-dcm-pbs-planning.md` | PDM planning — the chosen alternative |
| `pdm-enterprise-proposal.md` | Budget proposal for enterprise support that unlocks PDM |

---

*Internal Use Only — Network Engineering — jukebox.internal*
