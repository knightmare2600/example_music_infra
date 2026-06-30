# Example Music Limited — Infrastructure Beginner's Guide

> **Classification:** Internal — Infrastructure  
> **Forest:** `jukebox.internal`  
> **Domains:** `example.net` · `example.org` · `example.com`  
> **Provisioning network:** `192.168.139.0/24` (OVH vRACK — see §4)  
> **Credentials:** See password manager — do **not** store passwords in this document  

---

## Changelog

| Date       | Change                    |
|------------|---------------------------|
| 2026-06-30 | Initial version           |
| 2026-06-30 | Add VRK site code; expand naming table; add AAR/DRS/DUS/FRE EU spokes |

---

## 1. Introduction

This document is for Malcolm and Jamie. If you are neither Malcolm nor Jamie, you are welcome to read it, but it was written specifically for the two of you.

Malcolm: you have been doing this since 1997. Most of this will be confirmation of things you already know, framed in the way we do them here. The sections on philosophy and order of operations are the ones that matter most — they explain *why* we have made certain choices, so that when something breaks at 2 AM you are not second-guessing the architecture.

Jamie: read this before you touch anything. Read it again after your first site build. It will make more sense the second time. The goal is that after reading this you can make a judgement call without having to ask Malcolm every five minutes.

### What this document covers

- What Example Music Limited's estate looks like
- The conventions that govern every hostname, IP address, and device in the estate
- The architecture — how sites connect, what connects to what
- The **order of operations** — what you build first and why; there is a correct sequence and deviating from it creates work
- Three guiding principles that will save you time and prevent arguments: **Known source of truth**, **Trust but verify**, **Prove a negative**
- The cardinal rule about existing site infrastructure
- Your workstation setup as an engineer on this estate

This document does **not** cover the step-by-step build of any individual component — that is what the buildsheets and runbooks are for. Those are linked in §12.

---

## 2. The Estate

### 2.1 What Example Music Limited is

Example Music Limited is the parent company. A number of subsidiary companies have been acquired across the UK, Europe, North America, and APAC. Each acquisition came with its own infrastructure — different vendors, different naming conventions, different AD domains, different subnets. The estate is therefore, at present, heterogeneous and disparate.

The goal is to bring everything under a single, consistent, well-documented infrastructure. This is a multi-year programme of work. We are in the early stages.

### 2.2 The acquisition approach

Sites are live. People are using them every day. You cannot simply turn off the existing infrastructure and rebuild from scratch — the business does not stop while you do it.

The approach is therefore: **build from the inside out while they use it.**

At each site, we build the new EXA infrastructure — firewall, domain controller, Proxmox hypervisors, switches, ILOs/DRACs — *alongside* the existing kit. We add devices, servers, and network equipment *around* what is already there. Once the new infrastructure is commissioned and stable, we cut over. Then the old kit is decommissioned.

This is proper IT. It is not PRINCE2 and Gantt charts.

### 2.3 The cardinal rule about existing infrastructure

> ⛔ **Existing site infrastructure MUST NOT be modified, reconfigured, or decommissioned until the new EXA infrastructure at that site is fully commissioned and signed off.**

If you are unsure whether something is "existing acquired infrastructure" or "new EXA infrastructure," check the build checklist for that site in [site-inventory.md](../site-inventory.md). If a device does not have an EXA hostname (`EXAXXX<SITE>NNN`), it is existing infrastructure. Hands off.

---

## 3. Known Source of Truth

*Credit: 0xDF*

When two sources of information conflict — a spreadsheet, a wiki page, someone's memory, a config file — one of them **wins**. The one that wins is the **known source of truth**.

In this estate, the known source of truth for site and subnet data is:

```
bootstrap/web/proxmox/sites.csv
```

(In production, a copy lives at `/etc/example-music/sites.csv` on managed nodes. The repo copy is authoritative — the production copy is deployed from it.)

If `sites.csv` says a site's subnet is `192.168.76.0/24`, it is `192.168.76.0/24`. If a note on a whiteboard says something different, the whiteboard is wrong. If a runbook from a previous engineer says something different, the runbook is wrong. If your memory says something different, your memory is wrong. `sites.csv` wins.

> **Why this matters:** In a multi-site estate with dozens of contributors and years of accumulated documentation, there will be conflicts. Having a defined known source of truth means you do not waste time arbitrating — you check the CSV and move on.

### 3.1 What sites.csv contains

| Column | Description |
|--------|-------------|
| `Site` | Three-letter site code — e.g. `FAL`, `CLD`, `ODE` |
| `City` | Human-readable city name |
| `Country` | Country name |
| `CountryCode` | ISO country code |
| `Subnet` | `/24` subnet — this is the LAN for the site |
| `Gateway` | The `.253` address — the firewall LAN face |
| `DC` | The `.10` address — the primary domain controller |
| `FW` | The `.253` address — the firewall (same as Gateway) |
| `Landline` | Site landline (redacted for publication) |
| `Mobile` | Site mobile (redacted for publication) |
| `Timezone` | IANA timezone for the site |
| `AnsibleRegion` | Ansible group — e.g. `uk_site`, `eu_site`, `cloud_site` |
| `Entity` | Legal entity — e.g. `Example Music (Scotland) Ltd` |

### 3.2 A worked example

Malcolm asks: "What's the DC IP for FAL?"  
Jamie does not guess. Jamie runs:

```bash
grep '^FAL,' bootstrap/web/proxmox/sites.csv | cut -d',' -f7
```

Or reads the CSV and finds:

```
FAL,Falkirk,United Kingdom,UK,192.168.76.0/24,192.168.76.253,192.168.76.10,192.168.76.253,...
```

The answer is `192.168.76.10`. That is the answer. That answer did not come from memory, a wiki, or a guess. It came from the known source of truth.

---

## 4. IP Addressing Convention

Every site in the estate follows the same IP addressing scheme within its `/24` subnet. This convention is **not optional** — every EXA device MUST be assigned an address from this scheme.

| Address | Role | Hostname pattern |
|---------|------|-----------------|
| `.1` | Primary internet gateway / router | `EXARTR<SITE>001` |
| `.2` | BMC pool — DRAC/iLO slot 1 | `EXARAC<SITE>001` |
| `.3` | BMC pool — DRAC/iLO slot 2, or RAC emulator (single-PVE sites) | `EXARAC<SITE>002` |
| `.4` | BMC pool — DRAC/iLO slot 3, or RAC emulator (two-PVE sites) | `EXARAC<SITE>003` |
| `.5` | Proxmox VE node 1 | `EXAPVE<SITE>001` |
| `.6` | Proxmox VE node 2 | `EXAPVE<SITE>002` |
| `.7` | Proxmox VE node 3 | `EXAPVE<SITE>003` |
| `.10` | Domain Controller — primary | `EXADCS<SITE>001` |
| `.11` | Domain Controller — secondary | `EXADCS<SITE>002` |
| `.15` | Ansible/PXE node (where present) | `EXAPRV<SITE>001` |
| `.48` | VOIP SBC — trunks to `EXACLDPBX001` | `EXASBC<SITE>001` |
| `.100`–`.249` | DHCP pool | — |
| `.250`–`.252` | Layer 2 switches | `EXASWI<SITE>001`–`003` |
| `.253` | Secondary internet gateway / firewall LAN face | `EXAFWL<SITE>001` |

> **BMC pool:** `.2`, `.3`, `.4` are shared between physical DRAC/iLO interfaces and the RAC emulator VM. Physical PVE BMCs consume from `.2` upward. The RAC emulator VM takes the next free slot. On three-PVE-node sites the entire pool is consumed by physical BMCs — there is no free slot for a RAC VM.

> **Note on `.1` vs `.253`:** The firewall LAN face is always `.253`. The `.1` address is the upstream router/gateway presented by the ISP or the existing site infrastructure. These are two different devices on different legs of the network. Do not confuse them.

### 4.1 CLD — the exception

CLD (Edinburgh, OVH Pulseant datacentre) does not follow the single-subnet convention. It has two networks, each with its own site code in `sites.csv`:

| Site code | Network | Range | Gateway | Role |
|-----------|---------|-------|---------|------|
| `CLD` | LAN | `192.168.69.0/24` | `192.168.69.253` | Primary CLD site LAN — DCs, Ansible, workstations |
| `VRK` | vRACK | `192.168.139.0/24` | `192.168.139.254` | OVH provisioning network — DNS/BIND, PXE / provisioning server, FWL WAN face |

> `VRK` is the site code for the OVH vRACK in `sites.csv`. It follows the same known-source-of-truth rules as every other site — if you need a vRACK IP, look it up against `VRK`, not from memory.

The vRACK is an OVH product. It provides 256 statically routed IP addresses that OVH routes to your dedicated servers and VMs directly. Operationally, treat them as real-world IPs — they reach across OVH's network to other vRACK-attached machines, and site FWL WAN interfaces attach to this network to reach the provisioning server.

> **NB:** Technically, `192.168.139.0/24` is RFC 1918 private address space (see [RFC 1918 §3](https://datatracker.ietf.org/doc/html/rfc1918#section-3)). OVH's vRACK routes these addresses internally across their infrastructure — they are not routable on the public internet. In practice, for our purposes, treat them as if they were routed public IPs within OVH's network.

The CLD IP table is reproduced here for reference. These are authoritative — verified and in use:

| Hostname | IP | Network | Role |
|----------|----|---------|------|
| `EXAFWLCLD001` (WAN) | `192.168.139.68` | vRACK | Firewall WAN face |
| `EXAFWLCLD001` (LAN) | `192.168.69.253` | LAN | Firewall LAN face |
| `EXADNSCLD001` | `192.168.139.8` | vRACK | BIND9 — authoritative DNS for `jukebox.internal` |
| `EXAPRVCLD001` | `192.168.139.50` | vRACK | Provisioning / PXE server |
| `EXAANSCLD001` | `192.168.69.9` | LAN | Ansible control node |
| `EXADCSCLD001` | `192.168.69.10` | LAN | Domain Controller — primary |
| `EXADCSCLD002` | `192.168.69.11` | LAN | Domain Controller — secondary |
| `EXARDRCLD001` | `192.168.69.12` | LAN | Rudder configuration management server |
| `EXASVRCLD002` | `192.168.69.20` | LAN | Windows Admin Centre |
| `EXACLDPBX001` | `192.168.69.48` | LAN | Central 3CX PBX |

> **Common mistakes:** The FWL WAN face is `.139.68`, not `.139.139` (`.139.139` would be `EXAFWLVRK001` — not currently deployed). The FWL LAN face is `.69.253`, not `.69.1`. Rudder, WAC, and PBX are on the **LAN** (`.69.x`) — not the vRACK. The Ansible node is LAN-only at `.69.9`.

---

## 5. Naming Convention

Every device in the estate MUST follow the `EXA` naming scheme. No exceptions.

Format: `EXA` + `<ROLE>` + `<SITE>` + `<SEQ>`

- `<ROLE>` — three letters, from the table below
- `<SITE>` — three-letter site code, from `sites.csv`
- `<SEQ>` — three-digit sequence number, zero-padded — `001`, `002`, etc.

Example: `EXAFWLEDI001` — EXA estate, firewall role, Edinburgh site, first unit.

| Prefix | Role | Example |
|--------|------|---------|
| `EXAFWL` | Firewall / gateway | `EXAFWLFAL001` |
| `EXARTR` | Router (upstream / ISP gateway) | `EXARTRFAL001` |
| `EXASWI` | Switch | `EXASWIFAL001` |
| `EXADCS` | Domain Controller (site) | `EXADCSFAL001` |
| `EXADCR` | Domain Controller (regional) | `EXADCRLND001` |
| `EXAPVE` | Proxmox VE node | `EXAPVEFAL001` |
| `EXASRV` | Member server | `EXASRVCLD001` |
| `EXARAC` | Remote Access Console (DRAC/iLO/RAC emulator) | `EXARACFAL001` |
| `EXANAS` | NAS | `EXANASFAL001` |
| `EXASBC` | VOIP SBC | `EXASBCFAL001` |
| `EXAPBX` | PBX | `EXACLDPBX001` |
| `EXAPRV` | Provisioning / bootstrap server | `EXAPRVCLD001` |
| `EXAWAP` | WiFi access point | `EXAWAPFAL001` |
| `EXAWKS` | Workstation | `EXAWKSFAL001` |
| `EXALAP` | Laptop | `EXALAPFAL001` |
| `EXAMBP` | MacBook Pro | `EXAMBPFAL001` |
| `EXAMAC` | iMac | `EXAMACFAL001` |
| `EXASUR` | Surface | `EXASURFAL001` |
| `EXATAB` | Tablet | `EXATABBIR001` |
| `EXAPHN` | Phone | `EXAPHNFAL001` |
| `EXAPRN` | Printer | `EXAPRNLND001` |
| `EXAWAP` | WiFi access point | `EXAWAPFAL001` |
| `EXANIX` | Unix / legacy system | `EXANIXPER001` |
| `EXACLK` | NTP / wall clock | `EXACLKCPH001` |
| `EXATTY` | Serial terminal | `EXATTYFAL001` |
| `EXALCD` | LCD / signage display | `EXALCDFAL001` |
| `EXATVS` | TV / video screen | `EXATVSCPH001` |
| `EXAVCU` | Video conferencing unit | `EXAVCUFAL001` |
| `EXACAM` | Camera (CCTV / IP) | `EXACAMFAL001` |
| `EXARAD` | Radio / FM-IP bridge | `EXARADLND001` |
| `EXAMIC` | Microphone (Dante / networked) | `EXAMICLND001` |
| `EXARDR` | Badge reader | `EXARDRFAL001` |
| `EXABPS` | Badge programming station | `EXABPSLIV001` |
| `EXAMUS` | Jukebox / instrument | `EXAMUSFAL001` |
| `EXAMOO` | Moog synthesizer | `EXAMOOBIR001` |
| `EXALIN` | LinnDrum / drum machine | `EXALINBIR001` |
| `EXAFCL` | Fairlight CMI | `EXAFCLBIR001` |
| `EXAAST` | Atari ST (MIDI sequencing) | `EXAASTBIR001` |
| `EXAPAY` | Payphone | `EXAPAYFAL001` |
| `EXAVND` | Vending machine | `EXAVNDFAL002` |
| `EXADON` | Donut / food vending | `EXADONFAL001` |
| `EXATEA` | Smart appliance (coffee/tea machine) | `EXATEAFAL001` |
| `EXACOF` | Smart coffee machine | `EXACOFSYD001` |
| `EXAPMP` | Networked petrol pump | `EXAPMPFAL001` |
| `EXATAR` | Tape archive | `EXATARFAL001` |
| `EXABUS` | Tour bus | `EXABUSFAL001` |
| `EXACAR` | Car / vehicle | `EXACARFAL001` |
| `EXATRK` | Truck / van | `EXATRKFAL001` |
| `EXAJET` | Jet aircraft | `EXAJETFAL001` |

> **Devices that do not yet have EXA hostnames are existing acquired infrastructure.** See §2.3.

---

## 6. Architecture

### 6.1 The topology

CLD is the spine. Every site in the estate connects back to it — or will, once commissioned. It sits in OVH's Pulseant datacentre in Edinburgh: geographically close to Falkirk (head office), on physically separate infrastructure.

The connectivity layer is **WireGuard** — a modern, fast, kernel-level VPN. Every site firewall maintains a direct WireGuard tunnel to CLD. CLD is the sole WireGuard hub. Traffic between sites routes via CLD, not through intermediate sites.

FAL, ODE, and BRK are **AD / service hubs** — they host key AD roles, DFS namespaces, and in future will host Rudder proxy nodes for their regions. They are not WireGuard intermediaries. A spoke does not depend on FAL being up to establish its WireGuard tunnel — it depends on CLD being up.

| Site | AD / Service role | Region |
|------|-------------------|--------|
| FAL — Falkirk | AD hub · DFS · future Rudder proxy | UK head office |
| ODE — Odense | AD hub · DFS · future Rudder proxy | European head office |
| BRK — Brockville | AD hub · DFS · future Rudder proxy | North America / APAC head office |

```mermaid
graph TD
    CLD["🏴󠁧󠁢󠁳󠁣󠁴󠁿 CLD — Edinburgh\nvRACK (VRK): 192.168.139.0/24\nLAN: 192.168.69.0/24\n★ Sole WireGuard hub — all sites connect here"]

    subgraph UK ["🇬🇧 United Kingdom"]
        FAL["FAL · Falkirk · .76\n★ AD hub"]
        EDI["EDI · Edinburgh · .131"]
        GLA["GLA · Glasgow · .141"]
        CLY["CLY · Clydebank · .41"]
        DUN["DUN · Dundee · .138"]
        ABD["ABD · Aberdeen · .224"]
        PER["PER · Perth · .173"]
        LND["LND · London · .20"]
        MCR["MCR · Manchester · .161"]
        BIR["BIR · Birmingham · .121"]
        LIV["LIV · Liverpool · .151"]
        NEW["NEW · Newcastle · .191"]
        SHE["SHE · Sheffield · .114"]
        HUL["HUL · Hull · .148"]
        COV["COV · Coventry · .247"]
        HAL["HAL · Halifax · .142"]
    end

    subgraph EU ["🇪🇺 Europe"]
        ODE["ODE · Odense · .126\n★ AD hub"]
        CPH["CPH · Copenhagen · .231"]
        KGE["KGE · Køge · .65"]
        FAX["FAX · Faxe · .246"]
        KOR["KOR · Korsør · .238"]
        AAR["AAR · Aarhus · .86"]
        FRE["FRE · Fredericia · .75"]
        BON["BON · Bonn · .228"]
        BER["BER · Berlin · .113"]
        DRS["DRS · Dresden · .153"]
        DUS["DUS · Düsseldorf · .211"]
        MUN["MUN · Munich · .189"]
        GOT["GOT · Gothenburg · .46"]
        OSL["OSL · Oslo · .47"]
        AMS["AMS · Amsterdam · .31"]
        MIL["MIL · Milan · .39"]
        VIE["VIE · Vienna · .78"]
    end

    subgraph NAAPAC ["🌎 Americas, APAC & Middle East"]
        BRK["BRK · Brockville · .136\n★ AD hub"]
        TOR["TOR · Toronto · .146"]
        MTL["MTL · Montréal · .154"]
        NYC["NYC · New York · .212"]
        LAX["LAX · Los Angeles · .213"]
        MIA["MIA · Miami · .135"]
        NJC["NJC · New Jersey · .201"]
        CHI["CHI · Chicago · .214"]
        ATL["ATL · Atlanta · .33"]
        SYD["SYD · Sydney · .29"]
        MEL["MEL · Melbourne · .61"]
        AKL["AKL · Auckland · .93"]
        BRT["BRT · Beirut · .169"]
    end

    CLD <-->|WireGuard\n(all sites direct)| FAL
    CLD <-->|WireGuard\n(all sites direct)| ODE
    CLD <-->|WireGuard\n(all sites direct)| BRK
```

> **Reading this diagram:** Lines from CLD to FAL, ODE, and BRK are shown as representatives. In practice, every site in each group also maintains its own direct WireGuard tunnel to CLD. The lines are not WireGuard hops — they are logical groupings by AD / service region.

### 6.2 What "top of the tree" means in practice

Once CLD is fully commissioned:

- `EXADCSCLD001` (`192.168.69.10`) is the forest root DC for `jukebox.internal`. Every other site's DC is a child domain DC that replicates from it.
- `EXADNSCLD001` (`192.168.139.8`) is the authoritative BIND9 nameserver for `jukebox.internal`. Every site firewall forwards internal DNS queries to it across the WireGuard tunnel. It sits on the vRACK — every site FWL WAN interface can reach it directly without going through the LAN.
- `EXAANSCLD001` (`192.168.69.9`) is the Ansible control node. It runs playbooks against the entire estate. Reachable on the CLD LAN via WireGuard.
- `EXARDRCLD001` (`192.168.69.12`) is the Rudder configuration management server. All managed nodes report to it. Reachable on the CLD LAN via WireGuard.
- `EXACLDPBX001` (`192.168.69.48`) is the central 3CX PBX. Site SBCs (`EXASBC<SITE>001`) trunk to it.

When a spoke site comes up, it does not operate autonomously. It connects back to CLD for AD replication, DNS, config management, and telephony. CLD MUST exist before any of this works.

---

## 7. Order of Operations

*Credit: The British Military*

In military planning, the order of operations is the sequence in which objectives MUST be taken. You do not advance on objective B until objective A is secured. Attempting to do so leaves your flank exposed and your logistics broken.

Infrastructure is the same. There is a correct build sequence. Deviating from it creates dependency failures that are time-consuming and sometimes embarrassing to untangle.

### 7.1 Macro order — which site comes first

```
CLD → FAL → ODE → BRK → all spokes
```

**CLD first, always.** CLD is the sole WireGuard hub. Without it:
- There is no provisioning server (`EXAPRVCLD001` at `192.168.139.50`) to serve iPXE boot files, preseed configs, and the Ansible SSH key
- There is no DNS for `jukebox.internal`
- There is no forest root DC — child domains cannot exist
- There is no Ansible control node to run playbooks against anything
- There is no WireGuard hub — no site can reach any other site

Everything else depends on CLD. CLD MUST be commissioned before any other work begins.

**FAL second.** FAL is the UK head office and the AD hub for the UK region. From a WireGuard perspective, FAL is just another site — its tunnel goes directly to CLD like everyone else's. The reason it comes second is operational: FAL is the most complex site (3-node PVE cluster, PDC emulator, most AD FSMO roles, the most people using it), and getting it clean and into the new EXA infrastructure early means it is done properly rather than rushed. DFS namespaces hosted at FAL also need to be live before UK spoke sites can access shared storage.

**ODE third.** ODE is the European AD hub. Same logic as FAL — it is the most complex European site, will host DFS and a future Rudder proxy for the EU region, and doing it before the EU spokes means those services are available when spokes come up.

**BRK fourth.** BRK is the Americas/APAC AD hub. Same logic again. BRK also covers the Middle East (BRT — Beirut).

**Spokes after their AD hub.** From a WireGuard perspective, a spoke MUST only have CLD up before its tunnel can come up. However, a spoke site MUST NOT be fully commissioned — domain-joined, DFS-connected, Rudder-enrolled — until its regional AD hub is live. Doing it the other way is technically possible for WireGuard but leaves the spoke without the services it depends on.

### 7.2 Per-site build sequence

Within every site, the build sequence is:

```
FWL → DCS → (PVE hypervisors, workstations, and other devices)
```

**Step 1 — Build the FWL VM**

The firewall is the first thing built at every site, without exception. It provides:
- NAT and packet filtering between WAN and LAN
- DHCP and DNS for the site LAN (until the DC is up and providing these)
- The WireGuard tunnel back to CLD — this is what connects the site to the estate
- The iPXE/DHCP chain that allows other devices to PXE boot

At CLD, the FWL WAN interface takes a static IP from the OVH vRACK (`192.168.139.68`). At all other sites, the FWL WAN interface takes a DHCP or static IP from the existing upstream network (ISP / acquired infra), and its LAN face takes the site's `.253` address.

The firewall is built by running `firewallme.sh`. This script is interactive and handles interface detection, site code lookup, WireGuard key generation, and peer configuration. See [buildsheet-firewall.md](buildsheets/buildsheet-firewall.md) for the full procedure.

Once `firewallme.sh` completes and the FWL reboots, the WireGuard tunnel to CLD MUST be up and the site MUST be reachable from CLD. Do not proceed to the DCS build until you have confirmed this.

**Step 2 — Build the DCS**

With the FWL live and the WireGuard tunnel up, the site can talk to CLD. Now build the domain controller:

1. Create the DC VM on the site PVE node
2. Boot via iPXE (served from `EXAPRVCLD001` across the WireGuard tunnel)
3. Debian installs unattended via `lvm.seed` / `late_command.sh`
4. Run the `windows_dc` Ansible playbook from `EXAANSCLD001` — this promotes the VM to a DC, joins it to the appropriate child domain, and configures AD replication back to `EXADCSCLD001`
5. DNS at the site now resolves `jukebox.internal` locally via the new DC — update the FWL's dnsmasq to point to `.10` instead of CLD

The DC build is handled by Ansible. See [buildsheet-domainControllers.md](buildsheets/buildsheet-domainControllers.md) and the `windows_dc` playbook README.

**Step 3 — PVE hypervisors, switches, and everything else**

With FWL and DCS commissioned, the site has:
- Network connectivity to the estate
- AD authentication
- DNS
- Ansible management

From this point, additional PVE nodes, managed switches, ILOs/DRACs, workstations, laptops, printers, SBCs, and any other EXA devices can be commissioned in any order. The Ansible inventory for the site can now be fully populated and playbooks run against it.

### 7.3 The "inside out" in practice

At FAL, ODE, BRK, and every spoke site, there is already infrastructure in place. When you commission the new EXA infrastructure at a site, the sequence looks like this:

```
Existing site (running, untouched)
    │
    │  ← you build EXAPVEFAL001 on a new server
    │  ← you create EXAFWLFAL001 as a VM on EXAPVEFAL001
    │  ← firewallme.sh runs, WireGuard comes up to FAL (hub)
    │  ← EXADCSFAL001 VM is created, Ansible promotes it to DC
    │  ← AD replication begins — jukebox.internal data syncs from CLD
    │  ← Ansible adds EXAPVEFAL001 to inventory, playbooks run
    │
    │  (existing infra still running, users unaffected)
    │
    └─ when ready: cut-over DNS, DHCP, authentication to EXA infra
                   decommission existing kit
                   sign off site build checklist
```

The existing infrastructure does not know or care that the new infrastructure is being built alongside it. Users do not notice. You build, test, and verify in parallel, then cut over cleanly.

---

## 8. Trust But Verify

*Credit: The CIA*

You suspect something is correct. You have every reason to think it is correct. You MUST still verify it.

"Trust but verify" is not a sign of distrust — it is a systematic discipline. In infrastructure, the cost of assuming something is working and being wrong is always higher than the cost of running one extra check.

### 8.1 Verifying the FWL build

Before you sign off the FWL build and move to the DCS, verify the following. Every check MUST pass:

**WireGuard tunnel is up:**
```bash
sudo wg show
# Expect: peer listed, latest handshake within the last 2 minutes, transfer counts climbing
```

If the handshake is missing or stale, the tunnel is not up. Do not proceed. See [wireguard-troubleshooting.md](wireguard/wireguard-troubleshooting.md).

**Hub is reachable via tunnel IP:**
```bash
# FAL hub-primary
ping -c 3 10.0.76.1

# ODE hub-regional
ping -c 3 10.0.126.1

# BRK hub-regional
ping -c 3 10.0.136.1
```

**Hub LAN is reachable:**
```bash
ping -c 3 192.168.76.10    # FAL DC
```

**DNS is resolving:**
```bash
dig ansible.jukebox.internal @192.168.<site-octet>.253
# Expect: answer section with 192.0.8.131 or the local provisioning IP
```

**DHCP is serving:**
```bash
sudo journalctl -u dnsmasq | grep DHCPACK | tail -10
# Expect: recent leases being handed out
```

**Cockpit is accessible:**
```bash
curl -sk https://192.168.<site-octet>.253:9090 | grep -i cockpit
# Or open in browser on LAN
```

**Provisioning server is reachable:**
```bash
curl -s http://192.168.139.50/ansible_sshkey.pub | head -1
# Expect: ssh-rsa or ssh-ed25519 key material
```

### 8.2 Verifying the DCS build

Before signing off the DC build:

**DC is reachable from Ansible:**
```bash
# From EXAANSCLD001
ansible EXADCS<SITE>001 -m win_ping
```

**AD replication is healthy:**
```powershell
# On the new DC
repadmin /showrepl
# Expect: no errors; last attempt and last success times are recent
```

**DNS is resolving both ways:**
```powershell
# On the new DC — resolve a CLD host
Resolve-DnsName EXADCSCLD001.jukebox.internal

# From a spoke machine — resolve a CLD host
nslookup EXADCSCLD001.jukebox.internal 192.168.<site-octet>.10
```

**Authentication is working:**
```powershell
# Test a domain logon from a site machine
# If Kerberos is broken, logon will fail with Event ID 4771 or 4776 on the DC
```

**Sysvol is replicating:**
```powershell
Get-ADReplicationFailure -Target EXADCS<SITE>001
# Expect: no output (no failures)
```

### 8.3 General principle

At every build stage, write down what you verified and when. The buildsheet checklists have sign-off columns — use them. If something cannot be verified, note why and do not sign it off.

---

## 9. Prove a Negative

*Credit: Doug S*

When you are troubleshooting, you will frequently arrive at a list of possible causes. Some of those causes you are fairly confident are not the issue. Check them anyway, and cross them off the list explicitly.

This is **proving a negative** — confirming that something is *definitely not* the cause. It takes thirty seconds. It saves hours of argument later when someone asks "but did you check the gateway?" and you have to say "...well, no, because I was sure it was fine."

### 9.1 Why this matters

In a shared team, troubleshooting is often collaborative. If you have not proven the negative, you will be asked about it. If you cannot prove it, you will be required to check it anyway, at a time when you would rather be doing something else.

Prove it first. Write it down. Move on.

### 9.2 Common negatives to prove

**"The gateway is wrong"** — check it:
```bash
ip route show default
# Compare the gateway with sites.csv — does the third octet match? Is .253 correct?
ping -c 3 <gateway-ip>
```

**"The WireGuard key is wrong on the hub"** — check it:
```bash
# On the spoke
sudo cat /etc/wireguard/public.key

# On the hub, check the peer stanza
sudo wg show | grep -A 5 "peer:"
```

**"DNS is not resolving"** — test it explicitly and log the response:
```bash
dig jukebox.internal @192.168.139.8 +short
# If this returns nothing, DNS is broken — and you now have evidence
# If it returns a result, DNS is not the problem — and you have proven that
```

**"The firewall is blocking it"** — check the ruleset:
```bash
sudo nft list ruleset | grep -A 3 "forward"
sudo tcpdump -i <LAN-iface> host <target-ip> -n -c 20
```

**"The Ansible SSH key is wrong"** — test it directly:
```bash
ssh -i /home/ansible/.ssh/id_ed25519 ansible@<target-ip> 'echo OK'
```

**"The preseed / late_command failed"** — check what it actually installed:
```bash
dpkg -l ansible openssh-server sudo | grep ^ii
```

### 9.3 Documentation

When you prove a negative during an incident or build, add it to the incident notes or the site build checklist. "Checked: gateway correct (`192.168.76.253`), responds to ping. Not the cause." This prevents the same question being raised twice.

---

## 10. Existing Infrastructure — Hands Off

This has already been stated in §2.3, but it is important enough to repeat as a standalone section.

> ⛔ **Existing site infrastructure MUST NOT be modified, reconfigured, or decommissioned until the new EXA infrastructure at that site is fully commissioned and signed off.**

"Fully commissioned and signed off" means:
- FWL is live, WireGuard tunnel is up, build checklist signed off
- DCS is live, AD replication healthy, DNS working, build checklist signed off
- PVE hypervisors are onboarded to Ansible and Zabbix (where applicable)
- Site appears in Rudder with correct node classification
- All relevant buildsheets in `docs/buildsheets/` are completed and signed

Until all of the above are true: the existing infrastructure at that site is running the business. It MUST be left alone. If you inadvertently break existing infrastructure during a build, you own the recovery — and the recovery takes priority over the new build.

---

## 11. Engineer Workstation

Malcolm and Jamie both have MacBook Pros with VMware Fusion. This section covers what needs to be installed and configured before you can do anything useful.

### 11.1 Required tools

| Tool | Purpose | Install |
|------|---------|---------|
| VMware Fusion | ARM64 VM for testing firewall and Debian builds locally before touching production | vmware.com |
| iTerm2 | Terminal — colour support, split panes, profile support | iterm2.com |
| KeePassXC | Credential database — every password for every system lives here | keepassxc.org |
| `kpcli` | KeePassXC CLI — retrieve credentials in scripts without opening the GUI | `brew install kpcli` |
| OpenSSH | SSH client and agent — built into macOS | pre-installed |
| ssh-agent | Key management — load your Ansible key at session start | `ssh-add ~/.ssh/id_ansible_ed25519` |
| WinSCP | SFTP transfers to/from Windows machines | winscp.net |
| Wireshark | Packet capture — for when you need to prove a negative at L2/L3 | wireshark.org |
| ipcalc | Subnet calculator | `brew install ipcalc` |
| Virt-viewer | SPICE viewer for VM console access via Proxmox | gitlab.com/virt-viewer |
| `jq` | JSON parsing — useful for Proxmox API and `nodeinfo.json` queries | `brew install jq` |
| `wg` | WireGuard tools — key generation, peer inspection | `brew install wireguard-tools` |

### 11.2 KeePassXC database structure

Every engineer MUST maintain a KeePassXC database for this estate. The recommended structure:

```
Example Music.kdbx
├── Infrastructure
│   ├── CLD
│   │   ├── EXAPVECLD001 — root (PVE host)
│   │   ├── EXAFWLCLD001 — ansible user
│   │   ├── EXADCSCLD001 — Administrator
│   │   └── PVE root password (hash source for answer.toml)
│   ├── FAL
│   │   └── <site devices>
│   └── <other sites>
├── Active Directory
│   ├── JUKEBOX\Administrator (forest DA)
│   ├── DEPLOYTOOLS_PASS (used by PostOOBE.cmd)
│   └── Per-domain DA accounts
├── Network
│   ├── WireGuard pre-shared keys (per peer pair)
│   └── IPMI / BMC passwords (per server)
└── Bootstrap
    ├── Ansible SSH private key passphrase (if set)
    └── Preseed ansible user password
```

The database MUST be stored on an encrypted volume or in a secure location. Do not email it. Do not put it in Dropbox unless the Dropbox account has MFA and the database itself has a strong master password.

### 11.3 SSH key setup

The Ansible user across the estate uses a shared SSH keypair. The public key is served from `EXAPRVCLD001` at `http://192.168.139.50/ansible_sshkey.pub` and installed into every provisioned node during the preseed/first-boot stage.

You MUST have the corresponding private key to run Ansible playbooks or SSH directly as the `ansible` user. Retrieve it from KeePassXC under **Bootstrap → Ansible SSH private key**:

```bash
# Install the key into your SSH agent
ssh-add ~/.ssh/id_ansible_ed25519

# Verify it loaded
ssh-add -l

# Test against a known good host
ssh ansible@192.168.139.9   # EXAANSCLD001
```

### 11.4 VMware Fusion — testing locally

Both MacBook Pros run VMware Fusion on Apple Silicon (ARM64). The provisioning pipeline supports ARM64 — the iPXE ISO has an ARM64 build, and the Debian netboot images are amd64 but run under emulation in Fusion (acceptable for lab/test — MUST NOT be used in production).

For firewall testing locally in Fusion, use:
- **Host-Only** network adapter for the LAN interface (isolated from the Mac's real network)
- **Bridged** adapter for the WAN interface (reaches the real provisioning network, or another Host-Only net for an isolated WAN stub)

The `firewallme.sh` script detects which interface has a `192.168.139.x` DHCP lease and uses that as WAN automatically. This detection works correctly in Fusion as long as the bridged adapter is on a network where `EXAPRVCLD001` is reachable.

---

## 12. Quick Reference

| I need to… | Go to |
|-----------|-------|
| Find a site's IP / subnet | `sites.csv` — the **known source of truth** |
| Find a device's details / health | [network-inventory.md](network-inventory.md) |
| Check a site's commissioning status | [site-inventory.md](site-inventory.md) |
| Build a firewall | [buildsheets/buildsheet-firewall.md](buildsheets/buildsheet-firewall.md) |
| Build a domain controller | [buildsheets/buildsheet-domainControllers.md](buildsheets/buildsheet-domainControllers.md) |
| Build a Proxmox node | [buildsheets/buildsheet-pve.md](buildsheets/buildsheet-pve.md) |
| Build a member server | [buildsheets/buildsheet-server.md](buildsheets/buildsheet-server.md) |
| Build a workstation / laptop | [buildsheets/buildsheet-workstation.md](buildsheets/buildsheet-workstation.md) |
| Build a Windows Admin node | [buildsheets/buildsheet-winadmin.md](buildsheets/buildsheet-winadmin.md) |
| Set up WireGuard / DC deployment from scratch | [bootstrap/ad-dc-wireguard-deployment.md](bootstrap/ad-dc-wireguard-deployment.md) |
| Understand the full bootstrap pipeline (iPXE, PVE, Debian) | [bootstrap/bootstrapping.md](bootstrap/bootstrapping.md) |
| Troubleshoot a WireGuard tunnel | [wireguard/wireguard-troubleshooting.md](wireguard/wireguard-troubleshooting.md) |
| Fix a broken ZFS disk | [proxmox/zfs-disk-replacement.md](proxmox/zfs-disk-replacement.md) |
| Run an Ansible playbook | [ansible/README.md](../ansible/README.md) |
| Understand the full docs index | [INDEX.md](INDEX.md) |

---

*Example Music Limited — Internal Infrastructure Documentation*  
*Do not distribute outside the organisation*  
*Credentials: See password manager — never store passwords in this document*
