# Example Music Limited — Site Inventory & Commissioning Record

> **Classification:** Internal — Infrastructure  
> **Purpose:** Per-site build tracking and commissioning record.  
> Each site has a completion checklist covering all infrastructure,  
> endpoints, and site-specific equipment. Ticking a checkbox here  
> confirms the corresponding buildsheet (where applicable) is complete.  
> **Cross-reference:** `network-inventory.md` for IP/health reference,  
> `buildsheets/` for per-role build procedures.  
> **Credentials:** See password manager — never store passwords here.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-31 | Full reconciliation against `check_doc_role_coverage.py` (check 28)'s 355 findings across 42 sites. Three fixes, in order: (1) renamed `EXARAC<SITE>001` → `EXABMC<SITE>001` estate-wide (41 sites) and deleted the fictional `EXARAC<SITE>002` "RAC emulator VM" line — never backed by real hardware on single/dual-node sites; FAL/ODE/BRK's genuine physical BMC2 (and BMC3) were restored under the new naming rather than deleted, confirmed real via their 3-PVE-node hub status. Also dropped the RAC-emulator-VM language from the per-site header summary line (38 sites) and the Quick Reference table's `.3` row. (2) Fixed `EXARTR<SITE>001`'s octet — every existing line read `.254` (FWL's real octet), ground truth is `.1`; the 2026-07-12 fix above only ever corrected FWL's line, never RTR's. (3) Renamed stale `EXADCR<SITE>001`/`002` → `EXADCS<SITE>001`/`002` on 6 sites (GLA, LND, BIR, MCR, LIV, NEW) with no real `devices.csv` DCR row backing them — distinct from EDI's and TOR's genuine DCR devices, which check 29 tracks separately and were left as DCR. With those three fixes applied, appended the remaining genuinely-missing standard-slot lines (second FWL, NAS, RDR, SWI, WAP, RTR, occasional DCS/one-offs) per site, sourced directly from `generate_inventory.py`'s real device list. Check 28 now passes clean (0/355 remaining). |
| 2026-07-19 | `EXANASFAL001`/`EXANASPER001`/`EXANASMEL001` marked retired — replaced by the new standard `.19` NAS/SAN slot (TrueNAS), rolled out per site rather than the old ad-hoc addressing (`.32`/`.50`/none). See `README.md`'s Addressing table and `docs/proxmox/proxmox-dcm-pbs-planning.md` for the full rationale, including why `.15` PRV was retired in the same change. |
| 2026-07-12 | Fixed a second error in the same 10 sites' checklists (plus CLD): the firewall's IP was given as `.1` throughout, which is actually `RTR` (upstream router) per `address_policy.json`'s `role_offsets` — the firewall's real offset is `.253`/`.254`. Corrected all 10 standard-site entries to `.253`, matching `network-inventory.md`. CLD's `EXAFWLVRK001` line needed a different fix, not `.253` — it's the dual-interface exception, WAN/vRACK face at `.69`, LAN face (`EXAFWLCLD001`) at `.253`; corrected to state both explicitly rather than reuse the standard-site pattern verbatim. |
| 2026-07-12 | Fixed build-order errors in 10 sites' Infrastructure Checklists (CLD, FAL, CLY, ABD, LND, BIR, ODE, LAX, SYD, MEL, AKL): the firewall line was listed before the Proxmox node line, but every site's firewall is a VM running on that site's PVE node (see `buildsheets/buildsheet-firewall.md` Step 1 — "Create the VM on Proxmox") — the hypervisor has to exist first. Reordered each to PVE node(s) → Firewall → DC, matching actual build dependency. CLD's checklist was also missing `EXAPVECLD001`/`EXADCSCLD001` entirely (both real, onboarded hosts per `ansible/configs/inventory/cld.ini`) — added in the correct position, and moved `EXADNSVRK001` ahead of the firewall to match the real first-site bootstrap order (PVE → DNS → firewall → DC). |
| 2026-07-08 | Fixed CLD's checklist: several devices were listed with `192.168.139.x` (the vRACK octet range) when they're actually CLD-LAN-only (`192.168.69.x`) — Ansible/Rudder/WAC/PBX. Fixed `EXAPRVFAL001` -> `EXAPRVVRK001` (copy-paste error — FAL is a different site entirely). Fixed `EXAFWLCLD001` -> `EXAFWLVRK001` for the `.1` WireGuard-hub address specifically (same physical firewall, vRACK-facing role). Fixed stale forest name `jukebox.example` -> `jukebox.internal`. |
| 2026-07-08 | WAPs moved off DHCP to static `.82`–`.94` (added to Quick Reference table, per-site checklist items updated). Added `EXAUFCCLD001` (UniFi Network Controller, CLD LAN `192.168.69.82`) checklist item |
| 2026-03-05 | Full rewrite — all sites added, standard IP convention applied, PVE node counts confirmed, RAC/BMC pool documented, site-specific equipment placeholders added |
| 2026-03-03 | BRD renamed from BER throughout |
| 2026-03-03 | TOR (Toronto) added |
| 2026-03-01 | Initial document |

---

## Standard IP Convention (Quick Reference)

| Address | Role |
|---------|------|
| `.1` | Router / upstream gateway |
| `.2` | BMC pool slot 1 — physical DRAC/iLO (PVE node 1) |
| `.3` | BMC pool slot 2 — physical (PVE node 2) on hub sites only |
| `.4` | BMC pool slot 3 — physical (PVE node 3) on hub sites only |
| `.5` | PVE node 1 |
| `.6` | PVE node 2 (hub sites) |
| `.7` | PVE node 3 (FAL/ODE/BRK only) |
| `.10` | DC primary |
| `.11` | DC secondary |
| `.12` | Rudder Relay (`EXARRY<SITE>001`) / Rudder Server on CLD (`EXARUDCLD001`) |
| `.48` | VOIP SBC — trunks to `EXAPBXCLD001` |
| `.82`–`.94` | WAPs (static, added 2026-07-08 — moved off DHCP). Count varies per site |
| `.100`–`.249` | DHCP pool |
| `.250`–`.252` | Switches |
| `.253` | Firewall — primary |
| `.254` | Firewall — secondary |

> Full convention in `network-inventory.md` — Standard IP Convention section.

---

## Table of Contents

### Cloud
- [CLD — Cloud / Provisioning](#cld--cloud--provisioning)

### 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland
- [FAL — Falkirk *(Head Office)*](#fal--falkirk-head-office) ⭐ 3-node AD hub
- [EDI — Edinburgh](#edi--edinburgh)
- [GLA — Glasgow](#gla--glasgow)
- [CLY — Clydebank](#cly--clydebank)
- [DUN — Dundee](#dun--dundee)
- [PER — Perth](#per--perth)
- [ABD — Aberdeen](#abd--aberdeen)

### 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England
- [LND — London](#lnd--london)
- [BIR — Birmingham](#bir--birmingham)
- [MCR — Manchester](#mcr--manchester)
- [LIV — Liverpool](#liv--liverpool)
- [NEW — Newcastle](#new--newcastle)
- [SHE — Sheffield](#she--sheffield)
- [HAL — Halifax](#hal--halifax)
- [HUL — Hull](#hul--hull)
- [COV — Coventry](#cov--coventry)

### 🇩🇰 Danmark
- [CPH — København](#cph--kbenhavn)
- [ODE — Odense](#ode--odense) ⭐ 3-node AD hub (EU)
- [KGE — Køge](#kge--kge) ⚠️
- [FAX — Faxe](#fax--faxe)
- [KOR — Korsør](#kor--korsr)

### 🇩🇪 Deutschland
- [BON — Bonn](#bon--bonn)
- [BER — West Berlin](#brd--west-berlin)
- [MUN — Munich](#mun--munich)

### 🇸🇪 Sverige
- [GOT — Gothenburg](#got--gothenburg)

### 🇳🇴 Norge
- [OSL — Oslo](#osl--oslo)

### 🇳🇱 Nederland
- [AMS — Amsterdam](#ams--amsterdam)

### 🇮🇹 Italia
- [MIL — Milan](#mil--milan)

### 🇦🇹 Österreich
- [VIE — Vienna](#vie--vienna)

### 🇨🇦 Canada
- [BRK — Brockville](#brk--brockville-ontario) ⭐ 3-node AD hub (NA/APAC)
- [TOR — Toronto](#tor--toronto-ontario) ⚠️
- [MTL — Montreal](#mtl--montreal-quebec)

### 🇺🇸 United States
- [LAX — Los Angeles](#lax--los-angeles-california)
- [NYC — New York](#nyc--new-york-ny) ⚠️
- [NJC — New Jersey](#njc--camden-new-jersey) ⚠️
- [MIA — Miami](#mia--miami-florida)
- [ATL — Atlanta, GA](#atl--atlanta-georgia) ⚠️
- [CHI — Chicago](#chi--chicago-illinois) ⚠️

### 🇦🇺 Australia
- [SYD — Sydney](#syd--sydney-nsw) ⚠️
- [MEL — Melbourne](#mel--melbourne-vic) ⚠️

### 🇳🇿 New Zealand
- [AKL — Auckland](#akl--auckland) ⚠️

---

## Site Completion Summary

| Code | Site | Commissioned | Notes |
|------|------|:------------:|-------|
| CLD | Cloud / Provisioning | [ ] | |
| FAL | Falkirk | [ ] | Head office · 3-node AD hub |
| EDI | Edinburgh | [ ] | ⚠️ EXADCSEDI003 unhealthy |
| GLA | Glasgow | [ ] | |
| CLY | Clydebank | [ ] | |
| DUN | Dundee | [ ] | |
| PER | Perth | [ ] | |
| ABD | Aberdeen | [ ] | |
| LND | London | [ ] | |
| BIR | Birmingham | [ ] | |
| MCR | Manchester | [ ] | |
| LIV | Liverpool | [ ] | |
| NEW | Newcastle | [ ] | |
| SHE | Sheffield | [ ] | |
| HAL | Halifax | [ ] | |
| HUL | Hull | [ ] | |
| COV | Coventry | [ ] | WAP/RTR only |
| CPH | København | [ ] | |
| ODE | Odense | [ ] | EU AD hub · 3-node |
| KGE | Køge | [ ] | ⚠️ DC EOL/out of sync |
| FAX | Faxe | [ ] | |
| KOR | Korsør | [ ] | |
| BON | Bonn | [ ] | Schema/Domain Naming Master |
| BER | West Berlin | [ ] | Legacy site code: BRD |
| MUN | Munich | [ ] | |
| GOT | Gothenburg | [ ] | |
| OSL | Oslo | [ ] | |
| AMS | Amsterdam | [ ] | |
| MIL | Milan | [ ] | |
| VIE | Vienna | [ ] | |
| BRK | Brockville | [ ] | NA/APAC AD hub · 3-node · ⚠️ DC stopped |
| TOR | Toronto | [ ] | ⚠️ DC stopped |
| MTL | Montreal | [ ] | |
| LAX | Los Angeles | [ ] | |
| NYC | New York | [ ] | ⚠️ DC stopped |
| NJC | New Jersey | [ ] | ⚠️ DC stopped |
| MIA | Miami | [ ] | |
| ATL | Atlanta, GA | [ ] | ⚠️ DC stopped |
| CHI | Chicago | [ ] | ⚠️ DC stopped |
| SYD | Sydney | [ ] | ⚠️ DC stopped |
| MEL | Melbourne | [ ] | ⚠️ DC stopped |
| AKL | Auckland | [ ] | ⚠️ DC stopped |

---

---

## CLD — Cloud / Provisioning

**vRACK (`VRK`):** `192.168.139.0/24` · **CLD LAN:** `192.168.69.0/24`
**Role:** WireGuard hub — routes to all sites. Central PBX, Ansible, WAC.
See `docs/ExampleMusic_Beginners_Guide.md` §4.1 for the full CLD/VRK split, and §4.2 for `FRD`
(Fredericia Havn — CLD's DR sister site, broadened 2026-08-04 beyond just VRK's provisioning
backup; `EXAPBXCLD002` standing in for CLD's own PBX is a real, current example of the failover
relationship. Not tracked as a build checklist here — it has its own real devices, but this
section covers CLD specifically).

### Infrastructure Checklist
- [ ] `EXABMCCLD001` — BMC / iDRAC online (`192.168.69.2`) — real hardware in an Edinburgh datacentre, standard BMC slot 1
- [ ] `EXAPVECLD001` — Proxmox node online (`192.168.69.5`) · ZFS RAID1 — build this first, everything below except the provisioning server (`192.168.139.50`, bootstrap-only, no formal hostname)/`EXAANSCLD001` runs as a VM on top of it
- [ ] `EXADNSVRK001` — DNS/BIND9 server online (`192.168.139.8`)
- [ ] `EXAFWLVRK001` — Firewall / WireGuard hub online (`192.168.139.69`, WAN/vRACK face — same physical firewall as `EXAFWLCLD001`, whose LAN face is `192.168.69.253`)
- [ ] `EXAPVEVRK001` — Proxmox VE node on the vRACK provisioning network (`192.168.139.5`) — Quanta S210-X22RQ
- [ ] `EXABMCVRK001` — BMC for `EXAPVEVRK001` (`192.168.139.215`) — SuperMicro (chassis is Quanta, BMC card is SuperMicro)
- [ ] `EXADCSCLD001` — Domain Controller online (`192.168.69.10`) — first DC in the forest; see `windows_bootstrap/site.yml` then `windows_dc/site.yml`'s `dc_is_first_in_forest` prompt
- [ ] Provisioning server online (`192.168.139.50` — bootstrap-only, no formal hostname)
- [ ] `EXAANSCLD001` — Ansible control node online (`192.168.69.9`)
- [ ] `EXANASCLD001` — Storage (NAS/SAN) online (`192.168.69.19`) — standard NAS slot
- [ ] `EXARDRCLD001` — Badge reader online (`192.168.69.21`) — standard RDR slot
- [ ] `EXASLTCLD001` — Salt master online (`192.168.69.22`) — manages all Windows nodes estate-wide, see `ansible/playbooks/salt/README.md`
- [ ] `EXAZABCLD001` — Zabbix monitoring server (`192.168.69.13`, reused from the retired `EXAMSHCLD001` slot) — added 2026-09-02, Zabbix 7.0/MariaDB/Apache, built via `bootstrap/web/provision/zabbixme.sh` (break-glass); in progress as of this entry, Ansible backport and agent playbooks not yet started
- [ ] `EXASVRCLD002` — Windows Admin Centre deployed (`192.168.69.20`)
- [ ] `EXAPBXCLD001` — Central 3CX PBX online (`192.168.69.48`)
- [ ] `EXAUFCCLD001` — UniFi Network Controller online (`192.168.69.82`, CLD's **LAN** — not vRACK; manages every site's WAPs)
- [ ] `EXARMMCLD001` — TacticalRMM online (`192.168.69.14`) — endpoint inventory/monitoring/alerting, added 2026-08-04. Confirmed live end to end 2026-08-07, incl. a real agent deployment and real remote-access use via its own bundled MeshCentral 2026-08-07/08 (which replaced the standalone `EXAMSHCLD001` build, RETIRED — see `ansible/playbooks/tacticalrmm/README.md`)
- [ ] `EXASWICLD001` — Core switch online (`192.168.69.250`) — standard SWI slot 1
- [ ] `EXAFWLCLD002` — Secondary firewall (`192.168.69.254`, standard FWL slot 2) — not yet built, planned
- [ ] `EXASWICLD002` — Switch 2 (`192.168.69.251`)
- [ ] `EXASWICLD003` — Switch 3 (`192.168.69.252`)
- [ ] WireGuard routes verified to all site subnets
- [ ] Ansible key distribution tested from the provisioning server (`192.168.139.50`)

`EXARUDCLD001` (Rudder Server, `192.168.69.12`) is **not in active use** — confirmed dormant,
kept as reference code only, not a build-checklist item.

### ZFS / Storage
*Not applicable — CLD nodes are cloud-hosted VMs.*

### Site-Specific Equipment
*Not applicable.*

---

---

## 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland

---

## FAL — Falkirk *(Head Office)*

**Address:** Brockville Stadium, Hope Street, Falkirk  
**Entity:** Example Music (Scotland) Ltd  
**LAN:** `192.168.76.0/24` · **VPN:** `10.0.76.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (AD hub) · **BMC pool:** `.2` `.3` `.4` all physical

### Infrastructure Checklist
- [ ] `EXASWIFAL001` — Core switch 1 (`192.168.76.250`)
- [ ] `EXASWIFAL002` — Core switch 2 (`192.168.76.251`)
- [ ] `EXARTRFAL001` — WAN edge router (`192.168.76.1`)
- [ ] `EXABMCFAL001` — BMC node 1 (`192.168.76.2`) · Dell iDRAC9
- [ ] `EXABMCFAL002` — BMC node 2 (`192.168.76.3`) · Dell iDRAC9
- [ ] `EXABMCFAL003` — BMC node 3 (`192.168.76.4`) · Dell iDRAC9
- [ ] `EXAPVEFAL001` — Proxmox node 1 (`192.168.76.5`) · ZFS RAID1
- [ ] `EXAPVEFAL002` — Proxmox node 2 (`192.168.76.6`) · ZFS RAID1
- [ ] `EXAPVEFAL003` — Proxmox node 3 (`192.168.76.7`) · ZFS RAID1
- [ ] `EXAFWLFAL001` — Firewall online (`192.168.76.253`) · FortiOS
- [ ] `EXADCSFAL001` — DC primary (`192.168.76.10`) · PDC Emulator
- [ ] `EXADCSFAL002` — DC secondary (`192.168.76.11`)
- [ ] `EXASBCFAL001` — VOIP SBC (`192.168.76.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXANASFAL001` — installed 2026-07-26 (bare metal, TrueNAS SCALE) at the standard `.19` slot, replacing the retired legacy FreeNAS box (was `192.168.76.32`) — Ansible onboarding in progress, not yet complete
- [ ] `EXATARFAL001` — Tape archiver (`192.168.76.33`) · Solaris Embedded
- [ ] `EXAFWLFAL002` — Firewall secondary (`192.168.76.254`)
- [ ] `EXASVRFAL001` — Reserved — standard convention slot (`192.168.76.20`)
- [ ] `EXASWIFAL003` — Switch 3 (`192.168.76.252`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool `.100`–`.249` confirmed active
- [ ] DNS resolving `jukebox.internal` from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEFAL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |
| EXAPVEFAL002 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |
| EXAPVEFAL003 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXAWKSFAL001` — Workstation (`192.168.76.100`) · Mixing Desk v1
- [ ] `EXAWKSFAL002` — Workstation (`192.168.76.101`) · Reel-to-Reel 24-track
- [ ] `EXAWKSFAL003` — Workstation (`192.168.76.102`) · Shared editing
- [ ] `EXALAPFAL001` — Laptop (`192.168.76.103`) · Production
- [ ] `EXASURFAL001` — Surface (`192.168.76.104`)
- [ ] `EXAPHNFAL001`–`003` — Phones
- [ ] `EXAPHNFAL006`–`007` — Yealink T58A phones
- [ ] `EXATABFAL001` — Tablet
- [ ] WAPs `EXAWAPFAL001`, `EXAWAPFAL002`, `EXAWAPFAL003`, `EXAWAPFAL004`, `EXAWAPFAL005`, `EXAWAPFAL006` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Security & Building Systems
- [ ] `EXACAMFAL001` — Camera (`192.168.76.70`) · Front entrance
- [ ] `EXACAMFAL002` — Camera (`192.168.76.71`) · Studio hallway
- [ ] `EXACAMFAL003` — Camera (`192.168.76.72`) · Car park
- [ ] `EXACAMFAL004` — Camera (`192.168.76.73`) · Rear loading bay
- [ ] `EXARDRFAL001` — Badge reader (`192.168.76.16`) · HID Signo
- [ ] `EXACLKFAL001` — NTP Clock (`192.168.76.80`)
- [ ] `EXATTYFAL001` — VT320 serial terminal

### Site-Specific Equipment
- [ ] `EXALCDFAL001` — Samsung Tizen display (`192.168.76.50`) · Reception
- [ ] `EXAVCUFAL001` — Poly Studio X70 (`192.168.76.51`) · Brockville Suite
- [ ] `EXATEAFAL001` — Coffee machine (`192.168.76.61`) · Red Balloon
- [ ] `EXADONFAL001` — Tim Hortons vending (`192.168.76.62`) · VxWorks
- [ ] `EXAVNDFAL002` — Irn-Bru machine (`192.168.76.63`) · NT4 Embedded
- [ ] `EXAVNDFAL003` — McCowans dispenser (`192.168.76.64`) · XPe
- [ ] `EXAVNDFAL004` — Mrs Tily dispenser (`192.168.76.65`) · NT4
- [ ] `EXAVNDFAL005` — ¼lb Confectionery (`192.168.76.66`) · NT4
- [ ] `EXAMUSFAL001` — Pureline 128V Jukebox (`192.168.76.67`)
- [ ] `EXAPMPFAL001` — Networked petrol pump (`192.168.76.60`) · BP Grangemouth
- [ ] `EXAPAYFAL001` — GPO Kiosk No.6 payphone (`192.168.76.95`) · SIP gateway

---

## EDI — Edinburgh

**LAN:** `192.168.131.0/24` · **Domain:** `example.org` / `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

> ⚠️ `EXADCSEDI003` — DFSR stopped, C: drive 5% free. Immediate action required.

### Infrastructure Checklist
- [ ] `EXARTREDI001` — WAN edge router (`192.168.131.1`)
- [ ] `EXASWIEDI001` — Switch 1 (`192.168.131.250`) · Cisco 2960X
- [ ] `EXASWIEDI002` — Switch 2 (`192.168.131.251`) · Cisco 2960X
- [ ] `EXABMCEDI001` — BMC node 1 (`192.168.131.2`) · Dell iDRAC9
- [ ] `EXAPVEEDI001` — Proxmox node 1 (`192.168.131.5`) · ZFS RAID1
- [ ] `EXADCSEDI003` — DC (`192.168.131.11`) ⚠️ DFSR stopped — resolve before sign-off
- [ ] `EXASBCEDI001` — VOIP SBC (`192.168.131.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXADCREDI002` — DC secondary needs rebuild corrected to .12 (`192.168.131.12`)
- [ ] `EXADCREDI003` — DECOMMISSION PENDING corrected to .13 (`192.168.131.13`)
- [ ] `EXADCSEDI001` — DC (`192.168.131.10`)
- [ ] `EXAFWLEDI001` — Firewall (`192.168.131.253`)
- [ ] `EXAFWLEDI002` — Firewall secondary (`192.168.131.254`)
- [ ] `EXANASEDI001` — Storage (NAS/SAN) — standard NAS slot (`192.168.131.19`)
- [ ] `EXARDREDI001` — Badge reader — standard RDR slot (`192.168.131.21`)
- [ ] `EXASWIEDI003` — Switch 3 (`192.168.131.252`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEEDI001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXAWKSEDI001` — Workstation (`192.168.131.150`)
- [ ] `EXALAPEDI098` — Laptop (`192.168.131.108`)
- [ ] WAPs `EXAWAPEDI001`, `EXAWAPEDI002` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
- [ ] `EXATEAEDI001` — Siemens EQ700 coffee machine (`192.168.131.60`)
<!-- Additional site-specific equipment to be documented -->

---

## GLA — Glasgow

**LAN:** `192.168.141.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXABMCGLA001` — BMC node 1 (`192.168.141.2`)
- [ ] `EXAPVEGLA001` — Proxmox node 1 (`192.168.141.5`) · ZFS RAID1
- [ ] `EXADCSGLA001` — DC (`192.168.141.10`) · Schema/Domain Naming Master/PDC Emulator
- [ ] `EXASBCGLA001` — VOIP SBC (`192.168.141.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLGLA001` — Firewall (`192.168.141.253`)
- [ ] `EXAFWLGLA002` — Firewall secondary (`192.168.141.254`)
- [ ] `EXANASGLA001` — Storage (NAS/SAN) — standard NAS slot (`192.168.141.19`)
- [ ] `EXAPRNGLA001` — Main floor printer (`192.168.141.16`)
- [ ] `EXARDRGLA001` — Badge reader — standard RDR slot (`192.168.141.21`)
- [ ] `EXARTRGLA001` — WAN edge router (`192.168.141.1`)
- [ ] `EXASWIGLA001` — Switch 1 (`192.168.141.250`)
- [ ] `EXASWIGLA002` — Switch 2 (`192.168.141.251`)
- [ ] `EXASWIGLA003` — Switch 3 (`192.168.141.252`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEGLA001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPGLA001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXAWKSGLA001` — Workstation (`192.168.141.150`) · Hot desk
- [ ] `EXAWKSGLA002` — Workstation (`192.168.141.151`) · Hot desk
- [ ] `EXALAPGLA001` — Laptop (`192.168.141.152`)
- [ ] `EXAPRNZGLA001` — HP LaserJet Pro (`192.168.141.16`)

### Site-Specific Equipment
<!-- To be documented -->

---

## CLY — Clydebank

**LAN:** `192.168.41.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXASWICLY001` — Core switch (`192.168.41.250`) · Cisco 9300
- [ ] `EXARTRCLY001` — WAN edge router (`192.168.41.1`)
- [ ] `EXABMCCLY001` — BMC node 1 (`192.168.41.2`) · HPE iLO5
- [ ] `EXAPVECLY001` — Proxmox node 1 (`192.168.41.5`) · ZFS RAID1
- [ ] `EXAFWLCLY001` — Firewall (`192.168.41.253`) · FortiOS 7.6.5
- [ ] `EXADCSCLY001` — DC primary (`192.168.41.10`)
- [ ] `EXADCSCLY002` — DC secondary (`192.168.41.11`)
- [ ] `EXASVRCLY001` — Rocky Linux server (`192.168.41.20`) · Oracle DB
- [ ] `EXASBCCLY001` — VOIP SBC (`192.168.41.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLCLY002` — Firewall secondary (`192.168.41.254`)
- [ ] `EXANASCLY001` — Storage (NAS/SAN) — standard NAS slot (`192.168.41.19`)
- [ ] `EXARDRCLY001` — Badge reader — standard RDR slot (`192.168.41.21`)
- [ ] `EXASWICLY002` — Switch 2 (`192.168.41.251`)
- [ ] `EXASWICLY003` — Switch 3 (`192.168.41.252`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVECLY001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXASURCLY001` — Surface
- [ ] `EXAPHNCLY001` — iOS device
- [ ] `EXASURCLY002` — Android tablet
- [ ] WAPs `EXAWAPCLY001`, `EXAWAPCLY002` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
<!-- To be documented -->

---

## DUN — Dundee

**LAN:** `192.168.138.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXARTRDUN001` — WAN edge router (`192.168.138.1`)
- [ ] `EXABMCDUN001` — BMC node 1 (`192.168.138.2`)
- [ ] `EXAPVEDUN001` — Proxmox node 1 (`192.168.138.5`) · ZFS RAID1
- [ ] `EXADCSDUN001` — DC (`192.168.138.10`)
- [ ] `EXASBCDUN001` — VOIP SBC (`192.168.138.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLDUN001` — Firewall (`192.168.138.253`)
- [ ] `EXAFWLDUN002` — Firewall secondary (`192.168.138.254`)
- [ ] `EXANASDUN001` — Storage (NAS/SAN) — standard NAS slot (`192.168.138.19`)
- [ ] `EXARDRDUN001` — Badge reader — standard RDR slot (`192.168.138.21`)
- [ ] `EXASWIDUN001` — Switch 1 (`192.168.138.250`)
- [ ] `EXASWIDUN002` — Switch 2 (`192.168.138.251`)
- [ ] `EXASWIDUN003` — Switch 3 (`192.168.138.252`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEDUN001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXASURDUN001`–`002` — Surfaces
- [ ] `EXAPHNDUN001`–`002` — iOS devices
- [ ] WAPs `EXAWAPDUN001`, `EXAWAPDUN002` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
<!-- To be documented -->

---

## PER — Perth

**LAN:** `192.168.173.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXABMCPER001` — BMC node 1 (`192.168.173.2`)
- [ ] `EXAPVEPER001` — Proxmox node 1 (`192.168.173.5`) · ZFS RAID1
- [ ] `EXADCSPER001` — DC (`192.168.173.10`)
- [ ] `EXASBCPER001` — VOIP SBC (`192.168.173.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXANIXPER001` — Solaris 11.5 (`192.168.173.40`) · MIDI/Music archive
- [ ] `EXANASPER001` — **Retired 2026-07-19** (was `192.168.173.50`, Synology) — replaced by the standard `EXANASPER001` slot at `.19` (TrueNAS), not yet built
- [ ] `EXAFWLPER001` — Firewall (`192.168.173.253`)
- [ ] `EXAFWLPER002` — Firewall secondary (`192.168.173.254`)
- [ ] `EXARDRPER001` — Badge reader — standard RDR slot (`192.168.173.21`)
- [ ] `EXARTRPER001` — WAN edge router (`192.168.173.1`)
- [ ] `EXASWIPER001` — Switch 1 (`192.168.173.250`)
- [ ] `EXASWIPER002` — Switch 2 (`192.168.173.251`)
- [ ] `EXASWIPER003` — Switch 3 (`192.168.173.252`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEPER001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPPER001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXAMBPPER001` — MacBook Pro
- [ ] `EXASURPER001` — Surface
- [ ] `EXAPHNPER001`–`004` — Yealink T46G phones

### Site-Specific Equipment
- [ ] `EXAPRNPER001` — HP MFP printer
- [ ] `EXAVNDPER001` — Scone Palace vending machine · Embedded SP100
<!-- Additional site-specific equipment to be documented -->

---

## ABD — Aberdeen

**LAN:** `192.168.224.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXARTRABD001` — WAN edge router (`192.168.224.1`)
- [ ] `EXABMCABD001` — BMC node 1 (`192.168.224.2`)
- [ ] `EXAPVEABD001` — Proxmox node 1 (`192.168.224.5`) · ZFS RAID1
- [ ] `EXAFWLABD001` — Firewall (`192.168.224.253`) · Cisco ASA 5506-X
- [ ] `EXADCSABD001` — DC (`192.168.224.10`)
- [ ] `EXASBCABD001` — VOIP SBC (`192.168.224.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLABD002` — Firewall secondary (`192.168.224.254`)
- [ ] `EXANASABD001` — Storage (NAS/SAN) — standard NAS slot (`192.168.224.19`)
- [ ] `EXARDRABD001` — Badge reader — standard RDR slot (`192.168.224.21`)
- [ ] `EXASWIABD001` — Switch 1 (`192.168.224.250`)
- [ ] `EXASWIABD002` — Switch 2 (`192.168.224.251`)
- [ ] `EXASWIABD003` — Switch 3 (`192.168.224.252`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEABD001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXAMBPABD001`–`002` — MacBooks
- [ ] `EXAPHNABD001`–`002` — iPhones
- [ ] WAPs `EXAWAPABD001`, `EXAWAPABD002` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England

---

## LND — London

**LAN:** `192.168.20.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXASWILND001` — Core switch (`192.168.20.250`) · Cisco 9300
- [ ] `EXARTRLND001` — WAN edge router (`192.168.20.1`)
- [ ] `EXABMCLND001` — BMC node 1 (`192.168.20.2`) · Dell iDRAC9
- [ ] `EXAPVELND001` — Proxmox node 1 (`192.168.20.5`) · ZFS RAID1
- [ ] `EXAFWLLND001` — Firewall (`192.168.20.253`) · Cisco ASA 5516-X
- [ ] `EXADCSLND001` — DC (`192.168.20.10`) · RID Master · Infrastructure Master
- [ ] `EXASBCLND001` — VOIP SBC (`192.168.20.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLLND002` — Firewall secondary (`192.168.20.254`)
- [ ] `EXANASLND001` — Storage (NAS/SAN) — standard NAS slot (`192.168.20.19`)
- [ ] `EXARDRLND001` — Badge reader — standard RDR slot (`192.168.20.21`)
- [ ] `EXASWILND002` — Switch 2 (`192.168.20.251`)
- [ ] `EXASWILND003` — Switch 3 (`192.168.20.252`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVELND001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPLND001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXAWKSLND001` — Workstation (`192.168.20.150`)
- [ ] `EXAPRNLND001` — Xerox WorkCentre

### Site-Specific Equipment
- [ ] `EXARADLND001` — BBC Office Radio Mk II (`192.168.20.80`) · FM-IP bridge
- [ ] `EXAMICLND001` — Shure SM7 microphone (`192.168.20.81`) · Dante audio
- [ ] `EXAPRNLND002` — ProCAT Stylus steno writer · court device

---

## BIR — Birmingham

**LAN:** `192.168.121.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXASWIBIR001` — Core switch (`192.168.121.250`) · Cisco 9300
- [ ] `EXASWIBIR002` — Access switch (`192.168.121.251`)
- [ ] `EXARTRBIR001` — WAN edge router (`192.168.121.1`)
- [ ] `EXABMCBIR001` — BMC node 1 (`192.168.121.2`) · Dell DRAC
- [ ] `EXAPVEBIR001` — Proxmox node 1 (`192.168.121.5`) · ZFS RAID1
- [ ] `EXAFWLBIR001` — Firewall (`192.168.121.253`) · Palo Alto PAN-OS
- [ ] `EXADCSBIR001` — DC primary (`192.168.121.10`)
- [ ] `EXADCSBIR002` — DC secondary (`192.168.121.11`)
- [ ] `EXASVRBIR001` — Rocky Linux server (`192.168.121.20`) · Oracle DB
- [ ] `EXASBCBIR001` — VOIP SBC (`192.168.121.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLBIR002` — Firewall secondary (`192.168.121.254`)
- [ ] `EXANASBIR001` — Storage (NAS/SAN) — standard NAS slot (`192.168.121.19`)
- [ ] `EXARDRBIR001` — Badge reader — standard RDR slot (`192.168.121.21`)
- [ ] `EXASWIBIR003` — Switch 3 (`192.168.121.252`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEBIR001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXAMBPBIR001` — MacBook
- [ ] `EXATABBIR001` — Samsung Galaxy Tab
- [ ] `EXAPHNBIR001` — Samsung S25
- [ ] WAPs `EXAWAPBIR001`, `EXAWAPBIR002` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
- [ ] `EXAMOOBIR001` — Moog One synthesizer (`192.168.121.70`) · MIDI
- [ ] `EXALINBIR001` — LinnDrum LM-2 (`192.168.121.71`) · MIDI
- [ ] `EXAFCLBIR001` — Fairlight CMI IIx (`192.168.121.72`) · QDOS 2.x
- [ ] `EXAASTBIR001` — Atari ST (`192.168.121.73`) · TOS 1.04 · MIDI sequencing
- [ ] `EXAPAYBIR001` — GPO Kiosk No.6 payphone (`192.168.121.74`) · KX6 Red
- [ ] `EXALCDBIR001` — NEC PlasmaSync 42MP1 (`192.168.121.75`) · NOC display

---

## MCR — Manchester

**LAN:** `192.168.161.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXASWIMCR001` — Distribution switch (`192.168.161.250`) · Cisco 9300
- [ ] `EXABMCMCR001` — BMC node 1 (`192.168.161.2`) · HPE iLO5
- [ ] `EXAPVEMCR001` — Proxmox node 1 (`192.168.161.5`) · ZFS RAID1
- [ ] `EXADCSMCR001` — DC primary (`192.168.161.10`) · PDC Emulator · RID/Infra Master
- [ ] `EXADCSMCR002` — DC secondary (`192.168.161.11`)
- [ ] `EXASBCMCR001` — VOIP SBC (`192.168.161.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLMCR001` — Firewall (`192.168.161.253`)
- [ ] `EXAFWLMCR002` — Firewall secondary (`192.168.161.254`)
- [ ] `EXANASMCR001` — Storage (NAS/SAN) — standard NAS slot (`192.168.161.19`)
- [ ] `EXARDRMCR001` — Badge reader — standard RDR slot (`192.168.161.21`)
- [ ] `EXARTRMCR001` — WAN edge router (`192.168.161.1`)
- [ ] `EXASWIMCR002` — Switch 2 (`192.168.161.251`)
- [ ] `EXASWIMCR003` — Switch 3 (`192.168.161.252`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEMCR001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPMCR001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXALAPMCR001`–`002` — Win11 laptops
- [ ] `EXAWKSMCR001`–`002` — Win10 desktops
- [ ] `EXAPRNMCR001` — Printer

### Site-Specific Equipment
<!-- To be documented -->

---

## LIV — Liverpool

**LAN:** `192.168.151.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXASWILIV001` — Core switch (`192.168.151.250`) · Cisco 9200
- [ ] `EXABMCLIV001` — BMC node 1 (`192.168.151.2`) · HPE iLO5
- [ ] `EXAPVELIV001` — Proxmox node 1 (`192.168.151.5`) · ZFS RAID1
- [ ] `EXADCSLIV001` — DC (`192.168.151.10`) · WS2025
- [ ] `EXASBCLIV001` — VOIP SBC (`192.168.151.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLLIV001` — Firewall (`192.168.151.253`)
- [ ] `EXAFWLLIV002` — Firewall secondary (`192.168.151.254`)
- [ ] `EXANASLIV001` — Storage (NAS/SAN) — standard NAS slot (`192.168.151.19`)
- [ ] `EXARTRLIV001` — WAN edge router (`192.168.151.1`)
- [ ] `EXASWILIV002` — Switch 2 (`192.168.151.251`)
- [ ] `EXASWILIV003` — Switch 3 (`192.168.151.252`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVELIV001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPLIV001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXASVRLIV001` — WS2022 file server
- [ ] `EXAMBPLIV001` — MacBook Pro · macOS Tahoe
- [ ] `EXAMACLIV001` — iMac ⚠️ disabled/maintenance
- [ ] `EXARDRLIV002` — HID Signo badge reader
- [ ] `EXABPSLIV001` — Badge programming workstation

### Site-Specific Equipment
<!-- To be documented -->

---

## NEW — Newcastle

**LAN:** `192.168.191.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXASWINEW001` — Access switch (`192.168.191.250`) · TP-Link JetStream
- [ ] `EXABMCNEW001` — BMC node 1 (`192.168.191.2`) · Dell iDRAC9
- [ ] `EXAPVENEW001` — Proxmox node 1 (`192.168.191.5`) · ZFS RAID1
- [ ] `EXADCSNEW001` — DC (`192.168.191.10`)
- [ ] `EXASBCNEW001` — VOIP SBC (`192.168.191.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLNEW001` — Firewall (`192.168.191.253`)
- [ ] `EXAFWLNEW002` — Firewall secondary (`192.168.191.254`)
- [ ] `EXANASNEW001` — Storage (NAS/SAN) — standard NAS slot (`192.168.191.19`)
- [ ] `EXARDRNEW001` — Badge reader — standard RDR slot (`192.168.191.21`)
- [ ] `EXARTRNEW001` — WAN edge router (`192.168.191.1`)
- [ ] `EXASWINEW002` — Switch 2 (`192.168.191.251`)
- [ ] `EXASWINEW003` — Switch 3 (`192.168.191.252`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVENEW001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPNEW001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXASVRNEW001` — WS2022 file/print server
- [ ] `EXAWKSNEW099` — Win11 workstation ⚠️ LAPS expired

### Site-Specific Equipment
<!-- To be documented -->

---

## SHE — Sheffield

**LAN:** `192.168.114.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXABMCSHE001` — BMC node 1 (`192.168.114.2`)
- [ ] `EXAPVESHE001` — Proxmox node 1 (`192.168.114.5`) · ZFS RAID1
- [ ] `EXADCSSHE001` — DC (`192.168.114.10`)
- [ ] `EXASBCSHE001` — VOIP SBC (`192.168.114.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLSHE001` — Firewall (`192.168.114.253`)
- [ ] `EXAFWLSHE002` — Firewall secondary (`192.168.114.254`)
- [ ] `EXANASSHE001` — Storage (NAS/SAN) — standard NAS slot (`192.168.114.19`)
- [ ] `EXARDRSHE001` — Badge reader — standard RDR slot (`192.168.114.21`)
- [ ] `EXARTRSHE001` — WAN edge router (`192.168.114.1`)
- [ ] `EXASWISHE001` — Switch 1 (`192.168.114.250`)
- [ ] `EXASWISHE002` — Switch 2 (`192.168.114.251`)
- [ ] `EXASWISHE003` — Switch 3 (`192.168.114.252`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVESHE001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPSHE001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
<!-- To be documented -->

### Site-Specific Equipment
<!-- To be documented -->

---

## HAL — Halifax

**LAN:** `192.168.142.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXABMCHAL001` — BMC node 1 (`192.168.142.2`)
- [ ] `EXAPVEHAL001` — Proxmox node 1 (`192.168.142.5`) · ZFS RAID1
- [ ] `EXADCSHAL001` — DC (`192.168.142.10`)
- [ ] `EXASBCHAL001` — VOIP SBC (`192.168.142.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLHAL001` — Firewall (`192.168.142.253`)
- [ ] `EXAFWLHAL002` — Firewall secondary (`192.168.142.254`)
- [ ] `EXANASHAL001` — Storage (NAS/SAN) — standard NAS slot (`192.168.142.19`)
- [ ] `EXARDRHAL001` — Badge reader — standard RDR slot (`192.168.142.21`)
- [ ] `EXARTRHAL001` — WAN edge router (`192.168.142.1`)
- [ ] `EXASWIHAL001` — Switch 1 (`192.168.142.250`)
- [ ] `EXASWIHAL002` — Switch 2 (`192.168.142.251`)
- [ ] `EXASWIHAL003` — Switch 3 (`192.168.142.252`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEHAL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPHAL001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
<!-- To be documented -->

### Site-Specific Equipment
<!-- To be documented -->

---

## HUL — Hull

**LAN:** `192.168.148.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXABMCHUL001` — BMC node 1 (`192.168.148.2`)
- [ ] `EXAPVEHUL001` — Proxmox node 1 (`192.168.148.5`) · ZFS RAID1
- [ ] `EXADCSHUL001` — DC (`192.168.148.10`)
- [ ] `EXASBCHUL001` — VOIP SBC (`192.168.148.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLHUL001` — Firewall (`192.168.148.253`)
- [ ] `EXAFWLHUL002` — Firewall secondary (`192.168.148.254`)
- [ ] `EXANASHUL001` — Storage (NAS/SAN) — standard NAS slot (`192.168.148.19`)
- [ ] `EXARDRHUL001` — Badge reader — standard RDR slot (`192.168.148.21`)
- [ ] `EXARTRHUL001` — WAN edge router (`192.168.148.1`)
- [ ] `EXASWIHUL001` — Switch 1 (`192.168.148.250`)
- [ ] `EXASWIHUL002` — Switch 2 (`192.168.148.251`)
- [ ] `EXASWIHUL003` — Switch 3 (`192.168.148.252`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEHUL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPHUL001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
<!-- To be documented -->

### Site-Specific Equipment
<!-- To be documented -->

---

## COV — Coventry

**LAN:** `192.168.247.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical  
*Note: WAP/RTR-only site — minimal infrastructure.*

### Infrastructure Checklist
- [ ] `EXARTRCOV001` — WAN edge router (`192.168.247.1`) · Cisco ISR 4331
- [ ] `EXABMCCOV001` — BMC node 1 (`192.168.247.2`)
- [ ] `EXAPVECOV001` — Proxmox node 1 (`192.168.247.5`) · ZFS RAID1
- [ ] `EXADCSCOV001` — DC (`192.168.247.10`)
- [ ] `EXASBCCOV001` — VOIP SBC (`192.168.247.48`) · trunks to `EXAPBXCLD001`
- [ ] WAPs `EXAWAPCOV001`, `EXAWAPCOV002` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXAFWLCOV001` — Firewall (`192.168.247.253`)
- [ ] `EXAFWLCOV002` — Firewall secondary (`192.168.247.254`)
- [ ] `EXANASCOV001` — Storage (NAS/SAN) — standard NAS slot (`192.168.247.19`)
- [ ] `EXARDRCOV001` — Badge reader — standard RDR slot (`192.168.247.21`)
- [ ] `EXASWICOV001` — Switch 1 (`192.168.247.250`)
- [ ] `EXASWICOV002` — Switch 2 (`192.168.247.251`)
- [ ] `EXASWICOV003` — Switch 3 (`192.168.247.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVECOV001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇩🇰 Danmark

---

## CPH — København

**LAN:** `192.168.231.0/24` · **Domain:** `example.com` / `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXASWICPH001` — Office switch (`192.168.231.250`) · TP-Link JetStream
- [ ] `EXARTRCPH001` — WAN edge router (`192.168.231.1`)
- [ ] `EXABMCCPH001` — BMC node 1 (`192.168.231.2`) · Dell iDRAC9
- [ ] `EXAPVECPH001` — Proxmox node 1 (`192.168.231.5`) · ZFS RAID1
- [ ] `EXADCSCPH001` — DC primary (`192.168.231.10`) · example.com
- [ ] `EXADCSCPH002` — DC secondary (`192.168.231.11`) · example.net
- [ ] `EXASBCCPH001` — VOIP SBC (`192.168.231.48`) · trunks to `EXAPBXCLD001`
- [ ] WAPs `EXAWAPCPH001`, `EXAWAPCPH002`, `EXAWAPCPH003` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXAFWLCPH001` — Firewall (`192.168.231.253`)
- [ ] `EXAFWLCPH002` — Firewall secondary (`192.168.231.254`)
- [ ] `EXANASCPH001` — Storage (NAS/SAN) — standard NAS slot (`192.168.231.19`)
- [ ] `EXARDRCPH001` — Badge reader — standard RDR slot (`192.168.231.21`)
- [ ] `EXASWICPH002` — Switch 2 (`192.168.231.251`)
- [ ] `EXASWICPH003` — Switch 3 (`192.168.231.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVECPH001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
<!-- To be documented -->

### Site-Specific Equipment
- [ ] `EXACLKCPH001` — Meinberg LANTIME M300 NTP server (`192.168.231.18`)
- [ ] `EXATVSCPH001` — Bella Kronik 42X TV (`192.168.231.17`) · DR/TV2

---

## ODE — Odense *(EU Hub)*

**LAN:** `192.168.126.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (EU AD hub) · **BMC pool:** `.2` `.3` `.4` all physical

### Infrastructure Checklist
- [ ] `EXABMCODE001` — BMC node 1 (`192.168.126.2`)
- [ ] `EXABMCODE002` — BMC node 2 (`192.168.126.3`)
- [ ] `EXABMCODE003` — BMC node 3 (`192.168.126.4`)
- [ ] `EXAPVEODE001` — Proxmox node 1 (`192.168.126.5`) · ZFS RAID1
- [ ] `EXAPVEODE002` — Proxmox node 2 (`192.168.126.6`) · ZFS RAID1
- [ ] `EXAPVEODE003` — Proxmox node 3 (`192.168.126.7`) · ZFS RAID1
- [ ] `EXAFWLODE001` — Firewall (`192.168.126.253`) · Cisco ASA 5506-X
- [ ] `EXADCSODE001` — DC primary (`192.168.126.10`) · PDC Emulator · RID/Infra Master
- [ ] `EXADCSODE002` — DC secondary (`192.168.126.11`)
- [ ] `EXASBCODE001` — VOIP SBC (`192.168.126.48`) · trunks to `EXAPBXCLD001`
- [ ] WAPs `EXAWAPODE001`, `EXAWAPODE002` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXAFWLODE002` — Firewall secondary (`192.168.126.254`)
- [ ] `EXANASODE001` — Storage (NAS/SAN) — standard NAS slot (`192.168.126.19`)
- [ ] `EXARDRODE001` — Badge reader — standard RDR slot (`192.168.126.21`)
- [ ] `EXARTRODE001` — WAN edge router (`192.168.126.1`)
- [ ] `EXASWIODE001` — Switch 1 (`192.168.126.250`)
- [ ] `EXASWIODE002` — Switch 2 (`192.168.126.251`)
- [ ] `EXASWIODE003` — Switch 3 (`192.168.126.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEODE001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |
| EXAPVEODE002 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |
| EXAPVEODE003 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXAMACODE001` — iMac · macOS Tahoe
- [ ] `EXAMBPODE002` — MacBook Pro

### Site-Specific Equipment
- [ ] `EXAMUSODE001` — Pureline 128V Retro Vinyl Jukebox (`192.168.126.60`) · First Hotel Grand Odense

---

## KGE — Køge

**LAN:** `192.168.65.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

> ⚠️ `EXADCSKGE001` — out of sync 27 days, Windows Server 2016 EOL, disk space low.

### Infrastructure Checklist
- [ ] `EXABMCKGE001` — BMC node 1 (`192.168.65.2`)
- [ ] `EXAPVEKGE001` — Proxmox node 1 (`192.168.65.5`) · ZFS RAID1
- [ ] `EXADCSKGE001` — DC (`192.168.65.10`) ⚠️ WS2016 EOL — rebuild required
- [ ] `EXASBCKGE001` — VOIP SBC (`192.168.65.48`) · trunks to `EXAPBXCLD001`
- [ ] WAP `EXAWAPKGE001` — Ubiquiti UniFi U6-Pro
- [ ] `EXAFWLKGE001` — Firewall (`192.168.65.253`)
- [ ] `EXAFWLKGE002` — Firewall secondary (`192.168.65.254`)
- [ ] `EXANASKGE001` — Storage (NAS/SAN) — standard NAS slot (`192.168.65.19`)
- [ ] `EXARDRKGE001` — Badge reader — standard RDR slot (`192.168.65.21`)
- [ ] `EXARTRKGE001` — WAN edge router (`192.168.65.1`)
- [ ] `EXASWIKGE001` — Switch 1 (`192.168.65.250`)
- [ ] `EXASWIKGE002` — Switch 2 (`192.168.65.251`)
- [ ] `EXASWIKGE003` — Switch 3 (`192.168.65.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEKGE001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXAPRNKGE001` — HP LaserJet MFP M528

### Site-Specific Equipment
<!-- To be documented -->

---

## FAX — Faxe

**LAN:** `192.168.246.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXARTRFAX001` — WAN edge router (`192.168.246.1`)
- [ ] `EXABMCFAX001` — BMC node 1 (`192.168.246.2`)
- [ ] `EXAPVEFAX001` — Proxmox node 1 (`192.168.246.5`) · ZFS RAID1
- [ ] `EXADCSFAX001` — DC (`192.168.246.10`)
- [ ] `EXASBCFAX001` — VOIP SBC (`192.168.246.48`) · trunks to `EXAPBXCLD001`
- [ ] WAPs `EXAWAPFAX001`, `EXAWAPFAX002` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXAFWLFAX001` — Firewall (`192.168.246.253`)
- [ ] `EXAFWLFAX002` — Firewall secondary (`192.168.246.254`)
- [ ] `EXANASFAX001` — Storage (NAS/SAN) — standard NAS slot (`192.168.246.19`)
- [ ] `EXARDRFAX001` — Badge reader — standard RDR slot (`192.168.246.21`)
- [ ] `EXASWIFAX001` — Switch 1 (`192.168.246.250`)
- [ ] `EXASWIFAX002` — Switch 2 (`192.168.246.251`)
- [ ] `EXASWIFAX003` — Switch 3 (`192.168.246.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEFAX001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Site-Specific Equipment
<!-- To be documented -->

---

## KOR — Korsør

**LAN:** `192.168.238.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXABMCKOR001` — BMC node 1 (`192.168.238.2`)
- [ ] `EXAPVEKOR001` — Proxmox node 1 (`192.168.238.5`) · ZFS RAID1
- [ ] `EXADCSKOR001` — DC (`192.168.238.10`)
- [ ] `EXASBCKOR001` — VOIP SBC (`192.168.238.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLKOR001` — Firewall (`192.168.238.253`)
- [ ] `EXAFWLKOR002` — Firewall secondary (`192.168.238.254`)
- [ ] `EXANASKOR001` — Storage (NAS/SAN) — standard NAS slot (`192.168.238.19`)
- [ ] `EXARDRKOR001` — Badge reader — standard RDR slot (`192.168.238.21`)
- [ ] `EXARTRKOR001` — WAN edge router (`192.168.238.1`)
- [ ] `EXASWIKOR001` — Switch 1 (`192.168.238.250`)
- [ ] `EXASWIKOR002` — Switch 2 (`192.168.238.251`)
- [ ] `EXASWIKOR003` — Switch 3 (`192.168.238.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEKOR001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPKOR001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇩🇪 Deutschland

---

## BON — Bonn

**LAN:** `192.168.228.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXASWIBON001` — Office switch (`192.168.228.250`) · Cisco 2960X
- [ ] `EXARTRBON001` — WAN edge router (`192.168.228.1`)
- [ ] `EXABMCBON001` — BMC node 1 (`192.168.228.2`) · Dell iDRAC9
- [ ] `EXAPVEBON001` — Proxmox node 1 (`192.168.228.5`) · ZFS RAID1
- [ ] `EXADCSBON001` — DC (`192.168.228.10`) · **Schema Master · Domain Naming Master**
- [ ] `EXASBCBON001` — VOIP SBC (`192.168.228.48`) · trunks to `EXAPBXCLD001`
- [ ] WAPs `EXAWAPBON001`, `EXAWAPBON002` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXAFWLBON001` — Firewall (`192.168.228.253`)
- [ ] `EXAFWLBON002` — Firewall secondary (`192.168.228.254`)
- [ ] `EXANASBON001` — Storage (NAS/SAN) — standard NAS slot (`192.168.228.19`)
- [ ] `EXARDRBON001` — Badge reader — standard RDR slot (`192.168.228.21`)
- [ ] `EXASWIBON002` — Switch 2 (`192.168.228.251`)
- [ ] `EXASWIBON003` — Switch 3 (`192.168.228.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEBON001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXALAPBON001` — ThinkPad ⚠️ disabled/maintenance
- [ ] `EXAWKSBON001` — Win11 workstation · finance
- [ ] `EXALAPBON002` — Win11 laptop · finance

### Site-Specific Equipment
- [ ] `EXAVCUBON001` — Poly Studio X70 · boardroom
- [ ] `EXACAMBON001` — Axis P3245-LVE CCTV
- [ ] `EXATVSBON001` — Samsung 65" display

---

## BER — West Berlin (Formally BRD)

**LAN:** `192.168.113.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXARTRBER001` — WAN edge router (`192.168.113.1`)
- [ ] `EXABMCBER001` — BMC node 1 (`192.168.113.2`)
- [ ] `EXAPVEBER001` — Proxmox node 1 (`192.168.113.5`) · ZFS RAID1
- [ ] `EXADCSBER001` — DC (`192.168.113.10`) · WS2019 · PDC Emulator · RID/Infra Master
- [ ] `EXASBCBER001` — VOIP SBC (`192.168.113.48`) · trunks to `EXAPBXCLD001`
- [ ] WAPs `EXAWAPBER001`–`002` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXAFWLBER001` — Firewall (`192.168.113.253`)
- [ ] `EXAFWLBER002` — Firewall secondary (`192.168.113.254`)
- [ ] `EXANASBER001` — Storage (NAS/SAN) — standard NAS slot (`192.168.113.19`)
- [ ] `EXARDRBER001` — Badge reader — standard RDR slot (`192.168.113.21`)
- [ ] `EXASWIBER001` — Switch 1 (`192.168.113.250`)
- [ ] `EXASWIBER002` — Switch 2 (`192.168.113.251`)
- [ ] `EXASWIBER003` — Switch 3 (`192.168.113.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEBER001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXASVRBER001` — WS2019 legacy app server
- [ ] `EXANIXBER001` — Debian 12 server

### Site-Specific Equipment
<!-- To be documented -->

---

## MUN — Munich

**LAN:** `192.168.189.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXASWIMUN001` — Access switch (`192.168.189.250`) · Cisco 9200
- [ ] `EXABMCMUN001` — BMC node 1 (`192.168.189.2`) · HPE iLO5
- [ ] `EXAPVEMUN001` — Proxmox node 1 (`192.168.189.5`) · ZFS RAID1
- [ ] `EXADCSMUN001` — DC (`192.168.189.10`)
- [ ] `EXASBCMUN001` — VOIP SBC (`192.168.189.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLMUN001` — Firewall (`192.168.189.253`)
- [ ] `EXAFWLMUN002` — Firewall secondary (`192.168.189.254`)
- [ ] `EXANASMUN001` — Storage (NAS/SAN) — standard NAS slot (`192.168.189.19`)
- [ ] `EXARDRMUN001` — Badge reader — standard RDR slot (`192.168.189.21`)
- [ ] `EXARTRMUN001` — WAN edge router (`192.168.189.1`)
- [ ] `EXASWIMUN002` — Switch 2 (`192.168.189.251`)
- [ ] `EXASWIMUN003` — Switch 3 (`192.168.189.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEMUN001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPMUN001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXAWKSMUN001` — Win11 hot desk
- [ ] `EXALAPMUN001` — Win11 pool laptop
- [ ] `EXALAPMUN002` — Win11 laptop ⚠️ LAPS expired 61 days

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇸🇪 Sverige

---

## GOT — Gothenburg

**LAN:** `192.168.46.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXABMCGOT001` — BMC node 1 (`192.168.46.2`)
- [ ] `EXAPVEGOT001` — Proxmox node 1 (`192.168.46.5`) · ZFS RAID1
- [ ] `EXADCSGOT001` — DC (`192.168.46.10`)
- [ ] `EXASBCGOT001` — VOIP SBC (`192.168.46.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLGOT001` — Firewall (`192.168.46.253`)
- [ ] `EXAFWLGOT002` — Firewall secondary (`192.168.46.254`)
- [ ] `EXANASGOT001` — Storage (NAS/SAN) — standard NAS slot (`192.168.46.19`)
- [ ] `EXARDRGOT001` — Badge reader — standard RDR slot (`192.168.46.21`)
- [ ] `EXARTRGOT001` — WAN edge router (`192.168.46.1`)
- [ ] `EXASWIGOT001` — Switch 1 (`192.168.46.250`)
- [ ] `EXASWIGOT002` — Switch 2 (`192.168.46.251`)
- [ ] `EXASWIGOT003` — Switch 3 (`192.168.46.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEGOT001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPGOT001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇳🇴 Norge

---

## OSL — Oslo

**LAN:** `192.168.47.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXABMCOSL001` — BMC node 1 (`192.168.47.2`)
- [ ] `EXAPVEOSL001` — Proxmox node 1 (`192.168.47.5`) · ZFS RAID1
- [ ] `EXADCSOSL001` — DC (`192.168.47.10`)
- [ ] `EXASBCOSL001` — VOIP SBC (`192.168.47.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLOSL001` — Firewall (`192.168.47.253`)
- [ ] `EXAFWLOSL002` — Firewall secondary (`192.168.47.254`)
- [ ] `EXANASOSL001` — Storage (NAS/SAN) — standard NAS slot (`192.168.47.19`)
- [ ] `EXARDROSL001` — Badge reader — standard RDR slot (`192.168.47.21`)
- [ ] `EXARTROSL001` — WAN edge router (`192.168.47.1`)
- [ ] `EXASWIOSL001` — Switch 1 (`192.168.47.250`)
- [ ] `EXASWIOSL002` — Switch 2 (`192.168.47.251`)
- [ ] `EXASWIOSL003` — Switch 3 (`192.168.47.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEOSL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPOSL001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇳🇱 Nederland

---

## AMS — Amsterdam

**LAN:** `192.168.31.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXABMCAMS001` — BMC node 1 (`192.168.31.2`)
- [ ] `EXAPVEAMS001` — Proxmox node 1 (`192.168.31.5`) · ZFS RAID1
- [ ] `EXADCSAMS001` — DC (`192.168.31.10`)
- [ ] `EXASBCAMS001` — VOIP SBC (`192.168.31.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLAMS001` — Firewall (`192.168.31.253`)
- [ ] `EXAFWLAMS002` — Firewall secondary (`192.168.31.254`)
- [ ] `EXANASAMS001` — Storage (NAS/SAN) — standard NAS slot (`192.168.31.19`)
- [ ] `EXARDRAMS001` — Badge reader — standard RDR slot (`192.168.31.21`)
- [ ] `EXARTRAMS001` — WAN edge router (`192.168.31.1`)
- [ ] `EXASWIAMS001` — Switch 1 (`192.168.31.250`)
- [ ] `EXASWIAMS002` — Switch 2 (`192.168.31.251`)
- [ ] `EXASWIAMS003` — Switch 3 (`192.168.31.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEAMS001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPAMS001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇮🇹 Italia

---

## MIL — Milan

**LAN:** `192.168.39.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXABMCMIL001` — BMC node 1 (`192.168.39.2`)
- [ ] `EXAPVEMIL001` — Proxmox node 1 (`192.168.39.5`) · ZFS RAID1
- [ ] `EXADCSMIL001` — DC (`192.168.39.10`)
- [ ] `EXASBCMIL001` — VOIP SBC (`192.168.39.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLMIL001` — Firewall (`192.168.39.253`)
- [ ] `EXAFWLMIL002` — Firewall secondary (`192.168.39.254`)
- [ ] `EXANASMIL001` — Storage (NAS/SAN) — standard NAS slot (`192.168.39.19`)
- [ ] `EXARDRMIL001` — Badge reader — standard RDR slot (`192.168.39.21`)
- [ ] `EXARTRMIL001` — WAN edge router (`192.168.39.1`)
- [ ] `EXASWIMIL001` — Switch 1 (`192.168.39.250`)
- [ ] `EXASWIMIL002` — Switch 2 (`192.168.39.251`)
- [ ] `EXASWIMIL003` — Switch 3 (`192.168.39.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEMIL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPMIL001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇦🇹 Österreich

---

## VIE — Vienna

**LAN:** `192.168.78.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXABMCVIE001` — BMC node 1 (`192.168.78.2`)
- [ ] `EXAPVEVIE001` — Proxmox node 1 (`192.168.78.5`) · ZFS RAID1
- [ ] `EXADCSVIE001` — DC (`192.168.78.10`)
- [ ] `EXASBCVIE001` — VOIP SBC (`192.168.78.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLVIE001` — Firewall (`192.168.78.253`)
- [ ] `EXAFWLVIE002` — Firewall secondary (`192.168.78.254`)
- [ ] `EXANASVIE001` — Storage (NAS/SAN) — standard NAS slot (`192.168.78.19`)
- [ ] `EXARDRVIE001` — Badge reader — standard RDR slot (`192.168.78.21`)
- [ ] `EXARTRVIE001` — WAN edge router (`192.168.78.1`)
- [ ] `EXASWIVIE001` — Switch 1 (`192.168.78.250`)
- [ ] `EXASWIVIE002` — Switch 2 (`192.168.78.251`)
- [ ] `EXASWIVIE003` — Switch 3 (`192.168.78.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEVIE001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPVIE001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇨🇦 Canada

---

## BRK — Brockville, Ontario *(NA/APAC Hub)*

**LAN:** `192.168.136.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (NA/APAC AD hub) · **BMC pool:** `.2` `.3` `.4` all physical

> ⚠️ `EXADCSBRK001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXARTRBRK001` — WAN edge router (`192.168.136.1`)
- [ ] `EXABMCBRK001` — BMC node 1 (`192.168.136.2`)
- [ ] `EXABMCBRK002` — BMC node 2 (`192.168.136.3`)
- [ ] `EXABMCBRK003` — BMC node 3 (`192.168.136.4`)
- [ ] `EXAPVEBRK001` — Proxmox node 1 (`192.168.136.5`) · ZFS RAID1
- [ ] `EXAPVEBRK002` — Proxmox node 2 (`192.168.136.6`) · ZFS RAID1
- [ ] `EXAPVEBRK003` — Proxmox node 3 (`192.168.136.7`) · ZFS RAID1
- [ ] `EXADCSBRK001` — DC (`192.168.136.10`) ⚠️ Services stopped — resolve before sign-off
- [ ] `EXASBCBRK001` — VOIP SBC (`192.168.136.48`) · trunks to `EXAPBXCLD001`
- [ ] WAP `EXAWAPBRK001` — Ubiquiti UniFi U6-Pro
- [ ] `EXAFWLBRK001` — Firewall (`192.168.136.253`)
- [ ] `EXAFWLBRK002` — Firewall secondary (`192.168.136.254`)
- [ ] `EXANASBRK001` — Storage (NAS/SAN) — standard NAS slot (`192.168.136.19`)
- [ ] `EXARDRBRK001` — Badge reader — standard RDR slot (`192.168.136.21`)
- [ ] `EXASWIBRK001` — Switch 1 (`192.168.136.250`)
- [ ] `EXASWIBRK002` — Switch 2 (`192.168.136.251`)
- [ ] `EXASWIBRK003` — Switch 3 (`192.168.136.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEBRK001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |
| EXAPVEBRK002 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |
| EXAPVEBRK003 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXALAPBRK001` — Win11 tour laptop

### Site-Specific Equipment
- [ ] `EXAVNDBRK001` — Maple syrup vending machine (`192.168.136.61`) · XPe
- [ ] `EXADONBRK001` — Tim Hortons Donut vending (`192.168.136.60`) · VxWorks

---

## TOR — Toronto, Ontario

**LAN:** `192.168.146.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

> ⚠️ `EXADCSTOR001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXABMCTOR001` — BMC node 1 (`192.168.146.2`)
- [ ] `EXAPVETOR001` — Proxmox node 1 (`192.168.146.5`) · ZFS RAID1
- [ ] `EXADCSTOR001` — DC (`192.168.146.10`) ⚠️ Services stopped
- [ ] `EXASBCTOR001` — VOIP SBC (`192.168.146.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLTOR001` — Firewall (`192.168.146.253`)
- [ ] `EXAFWLTOR002` — Firewall secondary (`192.168.146.254`)
- [ ] `EXANASTOR001` — Storage (NAS/SAN) — standard NAS slot (`192.168.146.19`)
- [ ] `EXARDRTOR001` — Badge reader — standard RDR slot (`192.168.146.21`)
- [ ] `EXARTRTOR001` — WAN edge router (`192.168.146.1`)
- [ ] `EXASWITOR001` — Switch 1 (`192.168.146.250`)
- [ ] `EXASWITOR002` — Switch 2 (`192.168.146.251`)
- [ ] `EXASWITOR003` — Switch 3 (`192.168.146.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVETOR001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPTOR001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
<!-- To be documented -->

---

## MTL — Montreal, Quebec

**LAN:** `192.168.154.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXABMCMTL001` — BMC node 1 (`192.168.154.2`)
- [ ] `EXAPVEMTL001` — Proxmox node 1 (`192.168.154.5`) · ZFS RAID1
- [ ] `EXADCSMTL001` — DC (`192.168.154.10`)
- [ ] `EXASBCMTL001` — VOIP SBC (`192.168.154.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLMTL001` — Firewall (`192.168.154.253`)
- [ ] `EXAFWLMTL002` — Firewall secondary (`192.168.154.254`)
- [ ] `EXANASMTL001` — Storage (NAS/SAN) — standard NAS slot (`192.168.154.19`)
- [ ] `EXARDRMTL001` — Badge reader — standard RDR slot (`192.168.154.21`)
- [ ] `EXARTRMTL001` — WAN edge router (`192.168.154.1`)
- [ ] `EXASWIMTL001` — Switch 1 (`192.168.154.250`)
- [ ] `EXASWIMTL002` — Switch 2 (`192.168.154.251`)
- [ ] `EXASWIMTL003` — Switch 3 (`192.168.154.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEMTL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPMTL001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇺🇸 United States

---

## LAX — Los Angeles, California

**LAN:** `192.168.213.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

> ⚠️ `EXADCSLAX001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXASWILAX001` — Core switch (`192.168.213.250`) · Cisco 9300
- [ ] `EXASWILAX002` — Access switch (`192.168.213.251`) · Cisco 2960
- [ ] `EXARTRLAX001` — WAN edge router (`192.168.213.1`)
- [ ] `EXABMCLAX001` — BMC node 1 (`192.168.213.2`) · Dell iDRAC9
- [ ] `EXAPVELAX001` — Proxmox node 1 (`192.168.213.5`) · ZFS RAID1
- [ ] `EXAFWLLAX001` — Firewall (`192.168.213.253`) · Palo Alto PAN-OS 10.x
- [ ] `EXADCSLAX001` — DC (`192.168.213.10`) ⚠️ Services stopped
- [ ] `EXASVRLAX001` — Rocky Linux server (`192.168.213.20`) · local services/DB
- [ ] `EXASBCLAX001` — VOIP SBC (`192.168.213.48`) · trunks to `EXAPBXCLD001`
- [ ] WAPs `EXAWAPLAX001`, `EXAWAPLAX002`, `EXAWAPLAX003` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXAASTLAX001` — Atari ST (`192.168.213.73`)
- [ ] `EXAFWLLAX002` — Firewall secondary (`192.168.213.254`)
- [ ] `EXANASLAX001` — Storage (NAS/SAN) — standard NAS slot (`192.168.213.19`)
- [ ] `EXARDRLAX001` — Badge reader — standard RDR slot (`192.168.213.21`)
- [ ] `EXASWILAX003` — Switch 3 (`192.168.213.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVELAX001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXAMBPLAX001` — MacBook Pro
- [ ] `EXATABLAX001` — iPad setlists
- [ ] `EXAPHNLAX001` — Android phone

### Site-Specific Equipment
- [ ] `EXAMUSLAX001` — Moog One synthesizer (`192.168.213.70`)
- [ ] `EXAMUSLAX002` — LinnDrum LM-2 (`192.168.213.71`) · EPROM v7
- [ ] `EXAMUSLAX003` — Fairlight CMI IIx (`192.168.213.72`) · QDOS 2.x
- [ ] `EXAATTLAX001` — Atari ST (`192.168.213.73`) · TOS 1.04 · MIDI sequencing
- [ ] `EXAPAYLAX001` — Lobby payphone (`192.168.213.74`) · SIP gateway
- [ ] `EXALCDLAX001` — NEC PlasmaSync wallboard (`192.168.213.75`)
<!-- Additional site-specific equipment to be documented -->

---

## NYC — New York, NY

**LAN:** `192.168.212.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

> ⚠️ `EXADCSNYC001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXABMCNYC001` — BMC node 1 (`192.168.212.2`)
- [ ] `EXAPVENYC001` — Proxmox node 1 (`192.168.212.5`) · ZFS RAID1
- [ ] `EXADCSNYC001` — DC (`192.168.212.10`) ⚠️ Services stopped
- [ ] `EXASBCNYC001` — VOIP SBC (`192.168.212.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLNYC001` — Firewall (`192.168.212.253`)
- [ ] `EXAFWLNYC002` — Firewall secondary (`192.168.212.254`)
- [ ] `EXANASNYC001` — Storage (NAS/SAN) — standard NAS slot (`192.168.212.19`)
- [ ] `EXARDRNYC001` — Badge reader — standard RDR slot (`192.168.212.21`)
- [ ] `EXARTRNYC001` — WAN edge router (`192.168.212.1`)
- [ ] `EXASWINYC001` — Switch 1 (`192.168.212.250`)
- [ ] `EXASWINYC002` — Switch 2 (`192.168.212.251`)
- [ ] `EXASWINYC003` — Switch 3 (`192.168.212.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVENYC001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPNYC001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
<!-- To be documented -->

---

## NJC — Camden, New Jersey

**LAN:** `192.168.201.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

> ⚠️ `EXADCSNJC001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXABMCNJC001` — BMC node 1 (`192.168.201.2`)
- [ ] `EXAPVENJC001` — Proxmox node 1 (`192.168.201.5`) · ZFS RAID1
- [ ] `EXADCSNJC001` — DC (`192.168.201.10`) ⚠️ Services stopped
- [ ] `EXASBCNJC001` — VOIP SBC (`192.168.201.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLNJC001` — Firewall (`192.168.201.253`)
- [ ] `EXAFWLNJC002` — Firewall secondary (`192.168.201.254`)
- [ ] `EXANASNJC001` — Storage (NAS/SAN) — standard NAS slot (`192.168.201.19`)
- [ ] `EXARDRNJC001` — Badge reader — standard RDR slot (`192.168.201.21`)
- [ ] `EXARTRNJC001` — WAN edge router (`192.168.201.1`)
- [ ] `EXASWINJC001` — Switch 1 (`192.168.201.250`)
- [ ] `EXASWINJC002` — Switch 2 (`192.168.201.251`)
- [ ] `EXASWINJC003` — Switch 3 (`192.168.201.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVENJC001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPNJC001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
<!-- To be documented -->

---

## MIA — Miami, Florida

**LAN:** `192.168.135.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

### Infrastructure Checklist
- [ ] `EXABMCMIA001` — BMC node 1 (`192.168.135.2`)
- [ ] `EXAPVEMIA001` — Proxmox node 1 (`192.168.135.5`) · ZFS RAID1
- [ ] `EXADCSMIA001` — DC (`192.168.135.10`) · pending build
- [ ] `EXASBCMIA001` — VOIP SBC (`192.168.135.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLMIA001` — Firewall (`192.168.135.253`)
- [ ] `EXAFWLMIA002` — Firewall secondary (`192.168.135.254`)
- [ ] `EXANASMIA001` — Storage (NAS/SAN) — standard NAS slot (`192.168.135.19`)
- [ ] `EXARDRMIA001` — Badge reader — standard RDR slot (`192.168.135.21`)
- [ ] `EXARTRMIA001` — WAN edge router (`192.168.135.1`)
- [ ] `EXASWIMIA001` — Switch 1 (`192.168.135.250`)
- [ ] `EXASWIMIA002` — Switch 2 (`192.168.135.251`)
- [ ] `EXASWIMIA003` — Switch 3 (`192.168.135.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEMIA001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPMIA001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXALAPMIA001` — MacBook · macOS Sonoma

### Site-Specific Equipment
- [ ] `EXACOFMIA001` — Cuban Covfefe machine (`192.168.135.60`) · VxWorks
<!-- Additional site-specific equipment to be documented -->

---

## ATL — Atlanta, Georgia

**LAN:** `192.168.33.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

> ⚠️ `EXADCSATL001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXABMCATL001` — BMC node 1 (`192.168.33.2`)
- [ ] `EXAPVEATL001` — Proxmox node 1 (`192.168.33.5`) · ZFS RAID1
- [ ] `EXADCSATL001` — DC (`192.168.33.10`) ⚠️ Services stopped
- [ ] `EXASBCATL001` — VOIP SBC (`192.168.33.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLATL001` — Firewall (`192.168.33.253`)
- [ ] `EXAFWLATL002` — Firewall secondary (`192.168.33.254`)
- [ ] `EXANASATL001` — Storage (NAS/SAN) — standard NAS slot (`192.168.33.19`)
- [ ] `EXARDRATL001` — Badge reader — standard RDR slot (`192.168.33.21`)
- [ ] `EXARTRATL001` — WAN edge router (`192.168.33.1`)
- [ ] `EXASWIATL001` — Switch 1 (`192.168.33.250`)
- [ ] `EXASWIATL002` — Switch 2 (`192.168.33.251`)
- [ ] `EXASWIATL003` — Switch 3 (`192.168.33.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEATL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPATL001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
<!-- To be documented -->

---

## CHI — Chicago, Illinois

**LAN:** `192.168.214.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

> ⚠️ `EXADCSCHI001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXABMCCHI001` — BMC node 1 (`192.168.214.2`)
- [ ] `EXAPVECHI001` — Proxmox node 1 (`192.168.214.5`) · ZFS RAID1
- [ ] `EXADCSCHI001` — DC (`192.168.214.10`) ⚠️ Services stopped
- [ ] `EXASBCCHI001` — VOIP SBC (`192.168.214.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLCHI001` — Firewall (`192.168.214.253`)
- [ ] `EXAFWLCHI002` — Firewall secondary (`192.168.214.254`)
- [ ] `EXANASCHI001` — Storage (NAS/SAN) — standard NAS slot (`192.168.214.19`)
- [ ] `EXARDRCHI001` — Badge reader — standard RDR slot (`192.168.214.21`)
- [ ] `EXARTRCHI001` — WAN edge router (`192.168.214.1`)
- [ ] `EXASWICHI001` — Switch 1 (`192.168.214.250`)
- [ ] `EXASWICHI002` — Switch 2 (`192.168.214.251`)
- [ ] `EXASWICHI003` — Switch 3 (`192.168.214.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVECHI001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPCHI001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇦🇺 Australia

---

## SYD — Sydney, NSW

**LAN:** `192.168.29.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

> ⚠️ `EXADCSSYD001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXASWISYD001` — Core switch (`192.168.29.250`) · Cisco 9300
- [ ] `EXASWISYD002` — Access switch (`192.168.29.251`) · Cisco 2960
- [ ] `EXABMCSYD001` — BMC node 1 (`192.168.29.2`) · Dell iDRAC9
- [ ] `EXAPVESYD001` — Proxmox node 1 (`192.168.29.5`) · ZFS RAID1
- [ ] `EXAFWLSYD001` — Firewall (`192.168.29.253`) · FortiGate 7.x
- [ ] `EXADCSSYD001` — DC (`192.168.29.10`) ⚠️ Services stopped
- [ ] `EXASVRSYD001` — WS2022 server (`192.168.29.20`) · local infra
- [ ] `EXASBCSYD001` — VOIP SBC (`192.168.29.48`) · trunks to `EXAPBXCLD001`
- [ ] WAP `EXAWAPSYD001` — Ubiquiti UniFi
- [ ] `EXAFWLSYD002` — Firewall secondary (`192.168.29.254`)
- [ ] `EXANASSYD001` — Storage (NAS/SAN) — standard NAS slot (`192.168.29.19`)
- [ ] `EXARDRSYD001` — Badge reader — standard RDR slot (`192.168.29.21`)
- [ ] `EXARTRSYD001` — WAN edge router (`192.168.29.1`)
- [ ] `EXASWISYD003` — Switch 3 (`192.168.29.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVESYD001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXAMBPSYD001` — MacBook Pro
- [ ] `EXAWKSSYD001` — Win11 workstation
- [ ] `EXAPHNSYD001` — Android phone
- [ ] `EXATABSYD001` — iPad

### Site-Specific Equipment
- [ ] `EXALCDSYD001` — LG Signage wallboard
- [ ] `EXAPRNSYD001` — Brother laser printer
- [ ] `EXACAMSYD001` — Hikvision camera (pointed towards [EXACOFSYD001](https://en.wikipedia.org/wiki/Trojan_Room_coffee_pot?useskin=vector))
- [ ] `EXACAMSYD002` — Hikvision camera (Reception)
- [ ] `EXACOFSYD001` — Smart coffee machine. RFC2324 compliant

---

## MEL — Melbourne, VIC

**LAN:** `192.168.61.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

> ⚠️ `EXADCSMEL001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXASWIMEL001` — Core switch (`192.168.61.250`) · Cisco 9300
- [ ] `EXASWIMEL002` — Access switch (`192.168.61.251`) · Cisco 2960
- [ ] `EXABMCMEL001` — BMC node 1 (`192.168.61.2`) · HPE iLO5
- [ ] `EXAPVEMEL001` — Proxmox node 1 (`192.168.61.5`) · ZFS RAID1
- [ ] `EXAFWLMEL001` — Firewall (`192.168.61.253`) · FortiGate 7.x
- [ ] `EXADCSMEL001` — DC (`192.168.61.10`) ⚠️ Services stopped
- [ ] `EXASVRMEL001` — WS2022 server (`192.168.61.20`) · local file/print
- [ ] `EXASBCMEL001` — VOIP SBC (`192.168.61.48`) · trunks to `EXAPBXCLD001`
- [ ] `EXAFWLMEL002` — Firewall secondary (`192.168.61.254`)
- [ ] `EXARDRMEL001` — Badge reader — standard RDR slot (`192.168.61.21`)
- [ ] `EXARTRMEL001` — WAN edge router (`192.168.61.1`)
- [ ] `EXASWIMEL003` — Switch 3 (`192.168.61.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEMEL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] WAPs `EXAWAPMEL001` — Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXAMBPMEL001` — MacBook Pro
- [ ] `EXAWKSMEL001` — Win11 workstation
- [ ] `EXAPHNMEL001` — iOS phone
- [ ] `EXATABMEL001` — iPad

### Site-Specific Equipment
- [ ] `EXALCDMEL001` — Samsung Signage display
- [ ] `EXAPRNMEL001` — HP LaserJet
- [ ] `EXANASMEL001` — **Retired 2026-07-19** (was Synology DSM 7.x, no fixed address) — replaced by the standard `EXANASMEL001` slot at `.19` (TrueNAS), not yet built

---

---

## 🇳🇿 New Zealand

---

## AKL — Auckland

**LAN:** `192.168.93.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical

> ⚠️ `EXADCSAKL001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXASWIAKL001` — Core switch (`192.168.93.250`) · Cisco 9300
- [ ] `EXASWIAKL002` — Access switch (`192.168.93.251`) · Cisco 2960
- [ ] `EXARTRAKL001` — WAN edge router (`192.168.93.1`)
- [ ] `EXABMCAKL001` — BMC node 1 (`192.168.93.2`) · HPE iLO5
- [ ] `EXAPVEAKL001` — Proxmox node 1 (`192.168.93.5`) · ZFS RAID1
- [ ] `EXAFWLAKL001` — Firewall (`192.168.93.253`) · FortiGate 7.x
- [ ] `EXADCSAKL001` — DC (`192.168.93.10`) ⚠️ Services stopped
- [ ] `EXASVRAKL001` — WS2022 server (`192.168.93.20`) · local server
- [ ] `EXASBCAKL001` — VOIP SBC (`192.168.93.48`) · trunks to `EXAPBXCLD001`
- [ ] WAPs `EXAWAPAKL001`, `EXAWAPAKL002`, `EXAWAPAKL003` — Ubiquiti UniFi — static, `.82`–`.94` range (see Standard IP Convention)
- [ ] `EXAFWLAKL002` — Firewall secondary (`192.168.93.254`)
- [ ] `EXANASAKL001` — Storage (NAS/SAN) — standard NAS slot (`192.168.93.19`)
- [ ] `EXARDRAKL001` — Badge reader — standard RDR slot (`192.168.93.21`)
- [ ] `EXASWIAKL003` — Switch 3 (`192.168.93.252`)
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEAKL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXAWKSAKL001` — Win11 workstation
- [ ] `EXAMBPAKL001` — MacBook Pro
- [ ] `EXAPHNAKL001` — Android phone
- [ ] `EXATABAKL001` — iPad

### Site-Specific Equipment
- [ ] `EXALCDAKL001` — Samsung Signage display
- [ ] `EXAPRNAKL001` — HP LaserJet
- [ ] `EXACAMAKL001` — Axis camera
- [ ] `EXACOFAKL001` — Smart coffee machine

---

*Example Music Limited — Internal Infrastructure Documentation*  
*Do not distribute outside the organisation*  
*Credentials: See password manager — never store passwords in this document*
