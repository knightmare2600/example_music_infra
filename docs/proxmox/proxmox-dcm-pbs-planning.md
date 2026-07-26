# Proxmox Datacenter Manager & Backup Server — Planning

**Document ID:** NET-PLAN-PDM-001
**Classification:** Internal — Network Operations
**Last Updated:** 2026-07-19
**Status:** PLANNING — not yet in implementation

> This document covers two related Proxmox products: Proxmox Datacenter
> Manager (PDM) and Proxmox Backup Server (PBS). Both are planned for
> future implementation. A lab evaluation of PDM using nested
> virtualisation is the immediate next step — no production changes
> until evaluation is complete and enterprise support licensing is in place.

> **Reworked 2026-07-19 (Robert):** the original architecture below (dated March 2026) put one
> PDM instance and one PBS instance at each of three "regional hubs" (FAL, ODE, BRK), with spoke
> sites backing up to their nearest regional hub over WireGuard. That premise no longer holds —
> as of the 2026-07-17/18 WireGuard rework, CLD is the **sole** WireGuard hub; FAL/ODE/BRK are
> ordinary spokes like any other site (still real AD/DFS hubs, just not WireGuard ones — see
> `ansible/README.md`'s WireGuard topology section). This revision replaces the three-hub design
> with: **one centralised DCM instance at CLD** (`EXADCMCLD001`) managing every site, and
> **one local PBS instance at every site, including CLD** (`EXAPBS<SITE>001`) — backup data never
> leaves a site's own LAN, which removes the WireGuard-dependency-for-backups risk entirely rather
> than just reducing it to "hub sites only." Every address below is a **proposed, collision-checked
> reservation pending approval** — see the addressing note in each architecture section — not yet
> written into `benarbejde/address_policy.json`. Once approved, follow
> `docs/ansible/beginners_guide_to_ansible.md`'s "Renumbering / Reworking Live Conventions" section
> for how to roll a new standard-slot convention out safely.

---

## Table of Contents

1. [What is Proxmox Datacenter Manager](#what-is-proxmox-datacenter-manager)
2. [What is Proxmox Backup Server](#what-is-proxmox-backup-server)
3. [How They Fit Together](#how-they-fit-together)
4. [Licensing — The Critical Constraint](#licensing--the-critical-constraint)
5. [Lab Evaluation — Nested PVE](#lab-evaluation--nested-pve)
6. [Planned Production Architecture — DCM](#planned-production-architecture--dcm)
7. [Planned Production Architecture — PBS](#planned-production-architecture--pbs)
8. [Site Storage — NAS/SAN (TrueNAS)](#site-storage--nassan-truenas)
9. [Implementation Phasing](#implementation-phasing)
10. [Related Documents](#related-documents)

---

## What is Proxmox Datacenter Manager

PDM is Proxmox's own official multi-cluster management plane — the
direct answer to VMware vCentre for the Proxmox ecosystem. It is built
and maintained by Proxmox Server Solutions GmbH (the same team that
builds PVE itself), which gives it native integration that third-party
tools like PegaProx cannot match.

In this estate, PDM is deployed as a single instance, `EXADCMCLD001`, at
CLD. It connects to every site's PVE cluster over the Proxmox API — the
same path every other management tool in this estate uses to reach a
site: over WireGuard, via CLD as the sole hub. Each site's cluster
appears as a "remote" in PDM. From one browser window you can see and
manage every VM, container, node, storage pool, and backup datastore
across the entire jukebox.internal estate.

**Key capabilities:**

- Unified dashboard across all clusters and sites
- Cross-cluster live migration (move a VM from one site to another without downtime)
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
                    │   EXADCMCLD001      │
                    │   PDM — single      │
                    │   pane of glass     │
                    └──────┬──────────────┘
                           │ Proxmox API, over WireGuard via CLD (sole hub)
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    FAL Cluster        ODE Cluster       ... 53 site
    (PVE nodes)        (PVE nodes)       clusters total
         │                 │                 │
         ▼                 ▼                 ▼
    EXAPBSFAL001      EXAPBSODE001      EXAPBS<SITE>001
    (local backup —   (local backup —   (local backup —
     never leaves      never leaves      never leaves
     FAL's LAN)         ODE's LAN)        that site's LAN)
```

PDM sees everything — compute and backup — in one unified view, reached
over WireGuard the same way any other management traffic reaches a
site. **The backup data path is deliberately separate from the
management path**: every site's PVE cluster backs up to that same
site's own local PBS instance, over the LAN, with zero WireGuard
involvement. PDM's visibility into backup status (job history,
verification results, datastore usage) still travels over WireGuard —
only the actual backup *data* stays local. A PBS instance is registered
as a remote in PDM exactly like a PVE cluster is; a backup job at any
site shows up in PDM alongside the VM it's protecting, regardless of
which site either lives at.

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

See the separate proposal document (`pdm-enterprise-proposal.md`)
for the full cost-benefit analysis and licence recommendations
for budget approval.

---

## Lab Evaluation — Nested PVE

Before committing to enterprise licensing, evaluate PDM by running a
nested PVE instance inside an existing EXAPVEFAL001 VM. This costs
nothing and carries zero production risk.

> **The lab node stays at FAL deliberately** — FAL is just a convenient existing node for a
> nested, non-production test VM, not a preview of production placement. The real, production
> `EXADCMCLD001` will be built at CLD (see below), unrelated to where this lab evaluation happens.

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

> **Note (2026-07-11):** this doc originally hardcoded `bookworm` here, dating from when this
> estate's PVE nodes still ran Debian Bookworm (PVE 8.x). They now run Trixie (PVE 9.x), but
> rather than swap the hardcoded value for another one that will just as surely go stale at the
> next Debian release, the commands below now derive the codename from the node itself with
> `lsb_release -c`. Proxmox has historically pinned some component repos to a specific Debian
> codename independent of the host OS release, so if PDM's repo genuinely doesn't have a build
> for your node's current codename yet, check `https://pdm.proxmox.com/debian/pdm` directly
> rather than assuming `lsb_release -c`'s output is automatically correct here.

```bash
# Download PDM ISO from Proxmox
wget https://enterprise.proxmox.com/iso/proxmox-datacenter-manager_*.iso
# (or no-subscription equivalent — check downloads page)

# Or install on existing Debian node:
# Add PDM repo and install package -- CODENAME is derived from the node itself, not hardcoded
CODENAME=$(lsb_release -c -s)

wget -qO - "https://enterprise.proxmox.com/debian/proxmox-release-${CODENAME}.gpg" \
    > "/etc/apt/trusted.gpg.d/proxmox-release-${CODENAME}.gpg"

echo "deb https://pdm.proxmox.com/debian/pdm ${CODENAME} pdm-no-subscription" \
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

## Planned Production Architecture — DCM

Once licensing is in place, the production PDM deployment — this estate names it
`EXADCMCLD001`, following the `Proxmox DCM` label `bootstrap/web/menu.ipxe` already uses for
this product, rather than a bare `PDM` role code:

### DCM Server

| Parameter | Value |
|-----------|-------|
| Hostname | `EXADCMCLD001` |
| Location | CLD — centralised, every site connects here over WireGuard |
| OS | PDM appliance (own ISO) or Debian |
| vCPU | 4 |
| RAM | 8 GB |
| Disk | 40 GB |
| IP | `192.168.69.13` *(proposed — see addressing note below)* |
| Web UI | `https://192.168.69.13:8443` |

> **Addressing note:** `192.168.69.13` is checked collision-free against both
> `benarbejde/address_policy.json`'s reserved ranges (`.1` RTR, `.2`–`.4` BMC, `.5`–`.7` PVE,
> `.10`–`.11` DCS, `.15` PRV, `.48` SBC, `.82`–`.94` WAP, `.100`–`.249` DHCP, `.250`–`.252` SWI,
> `.253`–`.254` FWL) and every real row in `benarbejde/devices.csv` (CLD's own existing
> `.9` ANS, `.12` RDR, `.20` SVR, `.48` PBX×2, `.82` UFC). It sits next to CLD's other
> management-plane singles (`.9` Ansible, `.12` Rudder) — a deliberate, memorable grouping, not
> arbitrary. **This is a proposed reservation, not yet live** — DCM is CLD-only (one instance,
> not a per-site role), so it belongs in `devices.csv` as a CLD-specific row once approved, the
> same way `EXAANSCLD001`/`EXARUDCLD001` already are — it does **not** need a
> `address_policy.json` `role_offsets`/`offsets_single` entry, since those are for conventions
> repeated at every site.

### Remotes (Sites Managed)

Every site's PVE cluster is registered as a remote in PDM, over WireGuard via CLD (the sole
hub) for every non-CLD site. As of 2026-07-19, `benarbejde/sites.csv` lists **53 sites** — this
number changes as the estate grows; re-derive it from `sites.csv` at rollout time rather than
trusting this document's snapshot.

| Remote name | Type | Address |
|-------------|------|---------|
| CLD-cluster | PVE | `192.168.69.5` (local — no WireGuard hop) |
| FAL-cluster | PVE | `192.168.76.5` |
| ODE-cluster | PVE | `192.168.126.5` |
| BRK-cluster | PVE | `192.168.136.5` |
| CLD-backup | PBS | `192.168.69.14` *(proposed)* |
| FAL-backup | PBS | `192.168.76.14` *(proposed)* |
| ODE-backup | PBS | `192.168.126.14` *(proposed)* |
| BRK-backup | PBS | `192.168.136.14` *(proposed)* |
| (every other site) | PVE + PBS | per `sites.csv` — `.5` (PVE) and `.14` (PBS, proposed) on that site's own `/24` |

---

## Planned Production Architecture — PBS

**One PBS instance per site, no exceptions** — including CLD and, per Robert's 2026-07-19
direction, VRK and FRD too. This is a genuine simplification over the old three-regional-hub
design: every site's spec is now identical, and there is no "spoke vs hub" distinction to
maintain in this document at all.

### PBS Node Specification (identical at every site)

| Parameter | Value |
|-----------|-------|
| Hostname pattern | `EXAPBS<SITE>001` |
| OS | Proxmox Backup Server (own ISO) |
| vCPU | 4 |
| RAM | 8 GB |
| OS Disk | 32 GB |
| Backup Datastore Disk | Size TBD — depends on VM count and retention, per site |
| IP convention | `192.168.<site-octet>.14` *(proposed — see addressing note below)* |

> **Addressing note:** `.14` is checked collision-free against the same two sources as the DCM
> address above — not reserved in `address_policy.json`, and not used by any real
> `benarbejde/devices.csv` row at any site (the nearest neighbours, `.12` and `.13`, are already
> taken at CLD/EDI by unrelated devices — `.14` sits cleanly between `DCS2` (`.11`) and `NAS`
> (`.19`, the retired `.15` PRV convention's replacement — see the Site Storage section below)
> in the existing "core infrastructure" cluster of low octets). **This is a proposed
> reservation, not yet live.** Unlike DCM, PBS genuinely is a per-site standard-slot role —
> once approved, the correct implementation is adding `"PBS": 14` to
> `benarbejde/address_policy.json`'s `offsets_single` (and a `PBS` row to
> `benarbejde/role_codes.csv`, `ConnectionMethod=ssh` — matching how `PVE`/`DCS`/`ANS` are
> already registered there; role/connection-method metadata moved out of `address_policy.json`
> into `role_codes.csv` on 2026-07-20, see that file's own header), **not** a per-site
> `devices.csv` row — `generate_inventory.py` and `bind9-dns.yml`'s standard-slot synthesis both
> read `address_policy.json` as their single source of truth for addressing, so one JSON edit
> (plus the `role_codes.csv` row) is genuinely all the generator-side change needs to be (see
> `benarbejde/generate_inventory.py`'s own WAP/SWI precedent). Follow
> `docs/ansible/beginners_guide_to_ansible.md`'s "Renumbering / Reworking Live
> Conventions" checklist when actually rolling this out — this is exactly the class of change
> that guide section exists for.

### Backup Architecture

```
Every site backs up to its own local PBS — zero WireGuard dependency, zero cross-site
backup traffic, full stop.

FAL VMs  → EXAPBSFAL001 (local)
EDI VMs  → EXAPBSEDI001 (local — EDI is an ordinary spoke, same as every other site)
ODE VMs  → EXAPBSODE001 (local)
CLD VMs  → EXAPBSCLD001 (local)
... every other site → its own EXAPBS<SITE>001 (local)
```

This is a deliberate improvement over the old regional-hub design, not just a consequence of
the WireGuard topology change: backup traffic previously had to cross a WAN link (spoke →
regional hub) for every non-hub site; now it never does, for any site, anywhere. See
"Risks and Mitigations" in `pdm-enterprise-proposal.md` for how this changes the WireGuard-
instability risk assessment.

### Retention Policy (proposed)

| Backup type | Retention |
|-------------|-----------|
| Daily | 7 days |
| Weekly | 4 weeks |
| Monthly | 6 months |
| Yearly | 2 years |

These are starting points — adjust per VM criticality and storage budget. Unchanged from the
original proposal; retention policy is independent of where each PBS instance physically sits.

---

## Site Storage — NAS/SAN (TrueNAS)

A separate, related decision made alongside the PBS work above (2026-07-19, Robert): general
site storage (NAS/SAN — used interchangeably in this estate) also moves to a real per-site
standard slot, and the vestigial `.15` PRV convention is retired in the same change.

### Why `.15` PRV was retired, not just left alone

`.15` PRV ("Provisioning Server") has been in `address_policy.json`'s `offsets_single` since
this addressing scheme was first written, treated the same as `RTR`/`SBC` — a "single-instance
infra role, always physically present at a real site" per `generate_inventory.py`'s own
`DNS_SINGLE_ROLES` synthesis. Checked, not assumed: a real `--emit-devices-json` run showed
every one of the 51 ordinary sites (i.e. every site except VRK and FRD) getting a synthesized
`EXAPRV<SITE>001` DNS record at `.15` — and `benarbejde/devices.csv` has never had a single real
`PRV` row for any of them. Provisioning in this estate is, and always has been, centralised at
VRK (Edinburgh) and FRD (Fredericia Havn) — their own real provisioning servers (`192.168.139.50`
and `172.16.124.1` respectively — corrected 2026-07-21, this was previously stated backwards)
sit at those addresses via the `devices.csv`-exception path, entirely unrelated to this
standard-slot mechanism, and are **unaffected** by this retirement (though as of 2026-07-21 they
are, separately, given no formal `EXA<ROLE><SITE><NNN>` hostname or DNS record at all any more —
see `README.md`'s Addressing table). `.15` was dead for every ordinary site from day one; this
just makes the addressing policy match reality.

### The new `.19` NAS/SAN slot

| Parameter | Value |
|-----------|-------|
| Hostname pattern | `EXANAS<SITE>001` |
| IP convention | `192.168.<site-octet>.19` |
| OS | TrueNAS (SCALE, most likely — CORE/SCALE choice not yet made) |
| Deployment | One per site, no exceptions — same "identical everywhere" simplification as PBS |

**Addressing check, same rigour as PBS's `.14`:** `.19` is free in both
`benarbejde/address_policy.json` (not reserved by any existing range) and every real
`benarbejde/devices.csv` row at every site — the nearest neighbours, `.16`/`.17`/`.18`, are
already taken by unrelated ad-hoc devices at FAL/GLA/CPH. It sits in the same low-octet core
cluster as PBS: `DCS1`/`DCS2` (`.10`/`.11`), `PBS` (`.14`), **NAS `.19`**.

**Unlike PBS, this one is already live**, not proposed-pending-approval — `address_policy.json`
was updated for real (PRV removed from `offsets_single`/`_addressing`/`connection_types.none`,
NAS added), `generate_inventory.py`'s inventory/DNS synthesis regenerated across all 53 sites,
and the 3 legacy ad-hoc NAS devices (`EXANASFAL001` at `.32`, `EXANASPER001` at `.50`,
`EXANASMEL001` with no fixed address — all flagged `Legacy=yes`) removed from `devices.csv` and
marked retired in `docs/site-inventory.md`. ~~**`NAS` is deliberately NOT in `DNS_SINGLE_ROLES`**
— unlike PVE/DCS/FWL, it isn't universally deployed yet, so treating it as "always real" would
recreate the exact PRV mistake just fixed, for a different role. It gets the same treatment as
`WAP`/`BMC`: a reserved, documented slot, synthesized into DNS only once a real `devices.csv`
row confirms a device actually exists at that site.~~ **Superseded, 2026-07-26 — see the
follow-up below.**

> **Follow-up, 2026-07-20:** `address_policy.json`'s `connection_types` block referenced above
> (2026-07-19's PRV-removal note) no longer exists at all — role/connection-method metadata for
> every device Type code moved to a new file, `benarbejde/role_codes.csv`, consolidating what
> used to be three separately hand-maintained copies of overlapping data (`address_policy.json`'s
> `connection_types`, `generate_network_diagrams.py`'s `TYPE_SYMBOLS`, `docs/emojis/README.md`).
> `NAS`'s `ConnectionMethod` is `ssh` there, same value as before — this is a pure consolidation,
> not a behaviour change (verified: regenerated diagrams and inventory both byte-identical
> before/after). See `README.md`'s `role_codes.csv` section for the full rationale.

> **Follow-up, 2026-07-26 — Robert's explicit policy call, reversing the above:** `NAS` (and
> `RDR`/`BMC`/`WAP`, same reasoning) now ARE in the DNS-synthesis lists
> (`generate_inventory.py`'s `DNS_SINGLE_ROLES`/`DNS_MULTI_FIRST_INSTANCE_ONLY`). The original
> reasoning above ("not universally deployed yet, so treating it as always real would recreate
> the PRV mistake") was a true fact but the wrong conclusion — PRV is structurally centralised
> at 2 sites only and will never exist elsewhere; NAS/RDR/BMC/WAP are roles every real site
> WILL eventually have, just not all physically racked yet. That's exactly `SWI`'s own
> treatment since 2026-07-14, which had already proven the distinction out with zero problems.
> `EXANASFAL001` (installed the same day, the first real NAS box in the estate) is what
> triggered re-examining this. See `generate_inventory.py`'s own 2026-07-26 changelog entry for
> the full detail, including a real collision this surfaced (CLD's UniFi Network Controller
> sits on WAP1's own octet by design, needed an explicit suppression entry) and a real bug
> caught before it touched any generated file (NAS/RDR needed `DNS_SINGLE_ROLES`, not
> `DNS_MULTI_FIRST_INSTANCE_ONLY` — different underlying offsets shape than BMC/WAP/SWI).

### Configuring TrueNAS once installed — `arensb/ansible-truenas`

Checked directly (not assumed): [`arensb/ansible-truenas`](https://github.com/arensb/ansible-truenas)
is a real, actively maintained Ansible collection (Apache-2.0, 17 releases, 568 commits) that
configures an **already-installed, already-networked** TrueNAS system over its own
API/middleware daemon (`midclt`/`client`) — hostname, services, jails, etc. **It has no
bootstrap/install capability of its own** — getting TrueNAS onto bare metal in the first place
is a separate problem this collection doesn't touch at all, the same shape as the Proxmox
situation this repo already solved differently (`select-pve-answer.sh` + `first-boot.sh`, not
an Ansible collection). Two distinct pieces of future work, not one:

1. **Install** — resolved 2026-07-21: manual, box by box, not iPXE-automated. Investigated
   directly against TrueNAS's own community forums — neither CORE (FreeBSD-based) nor SCALE
   (Debian-based) has any answer-file/kickstart hook in their installer, in any form (ISO, PXE,
   or USB). Manual install sidesteps this rather than chasing a fragile netboot path. See
   `at_have_ryggen_fri`/memory `project_truenas_manual_install_ansible_followup` for the full
   investigation.
2. **Configure** — built 2026-07-22: `ansible/playbooks/truenas/` (`site.yml` +
   `00-preflight`/`10-access`/`20-storage`, `arensb/ansible-truenas`) sets hostname, the
   dedicated `ansible` automation account, nodeinfo, and a placeholder dataset. No network/IP
   task anywhere — the collection has no interface module at all. Not yet run against a real
   box; `20-storage.yml` deliberately creates only one general-purpose dataset until a real
   per-site dataset/share layout is defined. See `ansible/playbooks/truenas/README.md`.

---

## Implementation Phasing

| Phase | Action | Prerequisite |
|-------|--------|-------------|
| Now | Lab evaluation — nested PVE + PDM at FAL (see above) | EXAPVEFAL001 online |
| Budget approval | Enterprise support subscriptions purchased (see `pdm-enterprise-proposal.md` for fleet-wide cost model — no more "hub nodes only" tier, since DCM/PBS aren't confined to specific sites any more) | Proposal approved |
| DCM Phase 1 | `address_policy.json`/`devices.csv` reservations above made live; deploy `EXADCMCLD001` at CLD | Enterprise support active on CLD |
| PBS Phase 1 | Deploy `EXAPBSCLD001` at CLD (co-located with DCM's own site — first real-world proof of the per-site pattern) | DCM Phase 1 complete |
| PBS Phase 2 | Roll `EXAPBS<SITE>001` out across the remaining sites, one at a time, per the "Renumbering / Reworking Live Conventions" migration procedure — not a single estate-wide blast | Enterprise support active per site as it's onboarded |
| DCM Phase 2 | Register every site's PVE cluster + local PBS as PDM remotes as each comes online; configure RBAC and AD auth | DCM Phase 1 + at least one PBS site complete |
| NAS — done | `.19` addressing live in `address_policy.json`, legacy FAL/PER/MEL NAS retired | — (already complete, 2026-07-19) |
| NAS — install | Manual install, box by box — no working answer-file/PXE mechanism exists for CORE or SCALE (investigated 2026-07-21, confirmed via TrueNAS's own community forums) | — (decision made, 2026-07-21) |
| NAS — configure | `ansible/playbooks/truenas/` (`arensb/ansible-truenas`, site.yml + 00-preflight/10-access/20-storage) built 2026-07-22 — not yet run against a real box, no real per-site dataset/share layout defined yet | NAS — install complete on at least one site |

---

## Related Documents

| Document | Relationship |
|----------|-------------|
| `pdm-enterprise-proposal.md` | Budget proposal for enterprise support licensing |
| `ansible/README.md` | Current WireGuard topology (CLD sole hub) this design is built around |
| `docs/ansible/beginners_guide_to_ansible.md` | "Renumbering / Reworking Live Conventions" — the rollout methodology for the proposed `.13`/`.14` addressing once approved |
| `proxmox/pve-networking.md` | Network config PDM connects through |
| `wireguard/wireguard-troubleshooting.md` | Cross-site PDM-to-cluster connectivity |
| `network-inventory.md` | IP assignments for PDM and PBS nodes |
| `buildsheets/buildsheet-pve.md` | PVE build process PDM nodes follow |

---

*Internal Use Only — Network Engineering — jukebox.internal*
