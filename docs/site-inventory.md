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
| 2026-03-05 | Full rewrite — all sites added, standard IP convention applied, PVE node counts confirmed, RAC/BMC pool documented, site-specific equipment placeholders added |
| 2026-03-03 | BRD renamed from BER throughout |
| 2026-03-03 | TOR (Toronto) added |
| 2026-03-01 | Initial document |

---

## Standard IP Convention (Quick Reference)

| Address | Role |
|---------|------|
| `.1` | Firewall / primary gateway |
| `.2` | BMC pool slot 1 — physical DRAC/iLO (PVE node 1) |
| `.3` | BMC pool slot 2 — physical (PVE node 2) or RAC emulator VM on single-node sites |
| `.4` | BMC pool slot 3 — physical (PVE node 3) on hub sites only |
| `.5` | PVE node 1 |
| `.6` | PVE node 2 (hub sites) |
| `.7` | PVE node 3 (FAL/ODE/BRK only) |
| `.10` | DC primary |
| `.11` | DC secondary |
| `.48` | VOIP SBC — trunks to `EXACLDPBX001` |
| `.100`–`.249` | DHCP pool |
| `.250`–`.252` | Switches |
| `.253` | Secondary gateway / router |
| `.254` | WAN edge router |

> Full convention in `network-inventory.md` — Standard IP Convention section.

---

## Table of Contents

### Cloud
- [CLD — Cloud / Provisioning](#cld--cloud--provisioning)

### 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland
- [FAL — Falkirk *(Head Office)*](#fal--falkirk-head-office) ⭐ 3-node hub
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
- [ODE — Odense](#ode--odense) ⭐ 3-node hub (EU)
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
- [BRK — Brockville](#brk--brockville-ontario) ⭐ 3-node hub (NA/APAC)
- [TOR — Toronto](#tor--toronto-ontario) ⚠️
- [MTL — Montreal](#mtl--montreal-quebec)

### 🇺🇸 United States
- [LAX — Los Angeles](#lax--los-angeles-california)
- [NYC — New York](#nyc--new-york-ny) ⚠️
- [NJC — New Jersey](#njc--camden-new-jersey) ⚠️
- [MIA — Miami](#mia--miami-florida)
- [ATL — Athens, GA](#atl--athens-georgia) ⚠️
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
| FAL | Falkirk | [ ] | Head office · 3-node hub |
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
| ODE | Odense | [ ] | EU hub · 3-node |
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
| BRK | Brockville | [ ] | NA/APAC hub · 3-node · ⚠️ DC stopped |
| TOR | Toronto | [ ] | ⚠️ DC stopped |
| MTL | Montreal | [ ] | |
| LAX | Los Angeles | [ ] | |
| NYC | New York | [ ] | ⚠️ DC stopped |
| NJC | New Jersey | [ ] | ⚠️ DC stopped |
| MIA | Miami | [ ] | |
| ATL | Athens, GA | [ ] | ⚠️ DC stopped |
| CHI | Chicago | [ ] | ⚠️ DC stopped |
| SYD | Sydney | [ ] | ⚠️ DC stopped |
| MEL | Melbourne | [ ] | ⚠️ DC stopped |
| AKL | Auckland | [ ] | ⚠️ DC stopped |

---

---

## CLD — Cloud / Provisioning

**LAN:** `192.168.139.0/24`  
**Role:** WireGuard hub — routes to all sites. Central PBX, Ansible, Rudder, WAC.

### Infrastructure Checklist
- [ ] `EXAFWLCLD001` — Firewall / WireGuard hub online (`192.168.139.1`)
- [ ] `EXASVRCLD001` — Windows Admin Centre deployed (`192.168.139.20`)
- [ ] `EXASVRCLD002` — Ansible control node online (`192.168.139.49`)
- [ ] `EXASVRCLD003` — Rudder server online (`192.168.139.22`)
- [ ] `EXACLDPBX001` — Central 3CX PBX online (`192.168.139.48`)
- [ ] `EXAPRVFAL001` — Provisioning server online (`192.168.139.50`)
- [ ] WireGuard routes verified to all site subnets
- [ ] Ansible key distribution tested from `EXAPRVFAL001`
- [ ] Rudder agents checked in from test node

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
**PVE nodes:** 3 (hub) · **BMC pool:** `.2` `.3` `.4` all physical

### Infrastructure Checklist
- [ ] `EXAFWLFAL001` — Firewall online (`192.168.76.1`) · FortiOS
- [ ] `EXASWIFAL001` — Core switch 1 (`192.168.76.250`)
- [ ] `EXASWIFAL002` — Core switch 2 (`192.168.76.251`)
- [ ] `EXARTRFAL001` — WAN edge router (`192.168.76.254`)
- [ ] `EXARACFAL001` — BMC node 1 (`192.168.76.2`) · Dell iDRAC9
- [ ] `EXARACFAL002` — BMC node 2 (`192.168.76.3`) · Dell iDRAC9
- [ ] `EXARACFAL003` — BMC node 3 (`192.168.76.4`) · Dell iDRAC9
- [ ] `EXAPVEFAL001` — Proxmox node 1 (`192.168.76.5`) · ZFS RAID1
- [ ] `EXAPVEFAL002` — Proxmox node 2 (`192.168.76.6`) · ZFS RAID1
- [ ] `EXAPVEFAL003` — Proxmox node 3 (`192.168.76.7`) · ZFS RAID1
- [ ] `EXADCSFAL001` — DC primary (`192.168.76.10`) · PDC Emulator
- [ ] `EXADCSFAL002` — DC secondary (`192.168.76.11`)
- [ ] `EXASBCFAL001` — VOIP SBC (`192.168.76.48`) · trunks to `EXACLDPBX001`
- [ ] `EXANASFAL001` — NAS (`192.168.76.32`) · FreeNAS 13.0-U6
- [ ] `EXATARFAL001` — Tape archiver (`192.168.76.33`) · Solaris Embedded
- [ ] WireGuard tunnel verified
- [ ] DHCP pool `.100`–`.249` confirmed active
- [ ] DNS resolving `jukebox.example` from site

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
- [ ] WAPs `EXAWAPFAL001`–`006` — Ubiquiti UniFi U6-Pro

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
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSEDI003` — DFSR stopped, C: drive 5% free. Immediate action required.

### Infrastructure Checklist
- [ ] `EXARTREDI001` — WAN edge router (`192.168.131.254`)
- [ ] `EXASWIEDI001` — Switch 1 (`192.168.131.250`) · Cisco 2960X
- [ ] `EXASWIEDI002` — Switch 2 (`192.168.131.251`) · Cisco 2960X
- [ ] `EXARACEDI001` — BMC node 1 (`192.168.131.2`) · Dell iDRAC9
- [ ] `EXARACEDI002` — RAC emulator VM (`192.168.131.3`)
- [ ] `EXAPVEEDI001` — Proxmox node 1 (`192.168.131.5`) · ZFS RAID1
- [ ] `EXADCSEDI003` — DC (`192.168.131.11`) ⚠️ DFSR stopped — resolve before sign-off
- [ ] `EXASBCEDI001` — VOIP SBC (`192.168.131.48`) · trunks to `EXACLDPBX001`
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
- [ ] WAPs `EXAWAPEDI001`–`002` — Ubiquiti UniFi U6-Pro

### Site-Specific Equipment
- [ ] `EXATEAEDI001` — Siemens EQ700 coffee machine (`192.168.131.60`)
<!-- Additional site-specific equipment to be documented -->

---

## GLA — Glasgow

**LAN:** `192.168.141.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARACGLA001` — BMC node 1 (`192.168.141.2`)
- [ ] `EXARACGLA002` — RAC emulator VM (`192.168.141.3`)
- [ ] `EXAPVEGLA001` — Proxmox node 1 (`192.168.141.5`) · ZFS RAID1
- [ ] `EXADCRGLA001` — DC (`192.168.141.10`) · Schema/Domain Naming Master/PDC Emulator
- [ ] `EXASBCGLA001` — VOIP SBC (`192.168.141.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEGLA001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXAWKSGLA001` — Workstation (`192.168.141.150`) · Hot desk
- [ ] `EXAWKSGLA002` — Workstation (`192.168.141.151`) · Hot desk
- [ ] `EXALAPGLA001` — Laptop (`192.168.141.152`)
- [ ] `EXAPRNZGLA001` — HP LaserJet Pro (`192.168.141.16`)

### Site-Specific Equipment
<!-- To be documented -->

---

## CLY — Clydebank

**LAN:** `192.168.41.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXAFWLCLY001` — Firewall (`192.168.41.1`) · FortiOS 7.6.5
- [ ] `EXASWICLY001` — Core switch (`192.168.41.250`) · Cisco 9300
- [ ] `EXARTRCLY001` — WAN edge router (`192.168.41.254`)
- [ ] `EXARACCLY001` — BMC node 1 (`192.168.41.2`) · HPE iLO5
- [ ] `EXARACCLY002` — RAC emulator VM (`192.168.41.3`)
- [ ] `EXAPVECLY001` — Proxmox node 1 (`192.168.41.5`) · ZFS RAID1
- [ ] `EXADCSCLY001` — DC primary (`192.168.41.10`)
- [ ] `EXADCSCLY002` — DC secondary (`192.168.41.11`)
- [ ] `EXASRVCLY001` — Rocky Linux server (`192.168.41.20`) · Oracle DB
- [ ] `EXASBCCLY001` — VOIP SBC (`192.168.41.48`) · trunks to `EXACLDPBX001`
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
- [ ] WAPs `EXAWAPCLY001`–`002` — Ubiquiti UniFi U6-Pro

### Site-Specific Equipment
<!-- To be documented -->

---

## DUN — Dundee

**LAN:** `192.168.138.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARTRDUN001` — WAN edge router (`192.168.138.254`)
- [ ] `EXARACDUN001` — BMC node 1 (`192.168.138.2`)
- [ ] `EXARACDUN002` — RAC emulator VM (`192.168.138.3`)
- [ ] `EXAPVEDUN001` — Proxmox node 1 (`192.168.138.5`) · ZFS RAID1
- [ ] `EXADCSDUN001` — DC (`192.168.138.10`)
- [ ] `EXASBCDUN001` — VOIP SBC (`192.168.138.48`) · trunks to `EXACLDPBX001`
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
- [ ] WAPs `EXAWAPDUN001`–`002` — Ubiquiti UniFi U6-Pro

### Site-Specific Equipment
<!-- To be documented -->

---

## PER — Perth

**LAN:** `192.168.173.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARACPER001` — BMC node 1 (`192.168.173.2`)
- [ ] `EXARACPER002` — RAC emulator VM (`192.168.173.3`)
- [ ] `EXAPVEPER001` — Proxmox node 1 (`192.168.173.5`) · ZFS RAID1
- [ ] `EXADCSPER001` — DC (`192.168.173.10`)
- [ ] `EXASBCPER001` — VOIP SBC (`192.168.173.48`) · trunks to `EXACLDPBX001`
- [ ] `EXANIXPER001` — Solaris 11.5 (`192.168.173.40`) · MIDI/Music archive
- [ ] `EXANASPER001` — Synology NAS (`192.168.173.50`)
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEPER001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
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
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXAFWLABD001` — Firewall (`192.168.224.1`) · Cisco ASA 5506-X
- [ ] `EXARTRABD001` — WAN edge router (`192.168.224.254`)
- [ ] `EXARACABD001` — BMC node 1 (`192.168.224.2`)
- [ ] `EXARACABD002` — RAC emulator VM (`192.168.224.3`)
- [ ] `EXAPVEABD001` — Proxmox node 1 (`192.168.224.5`) · ZFS RAID1
- [ ] `EXADCSABD001` — DC (`192.168.224.10`)
- [ ] `EXASBCABD001` — VOIP SBC (`192.168.224.48`) · trunks to `EXACLDPBX001`
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
- [ ] WAPs `EXAWAPABD001`–`002` — Ubiquiti UniFi U6-Pro

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England

---

## LND — London

**LAN:** `192.168.20.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXAFWLLND001` — Firewall (`192.168.20.1`) · Cisco ASA 5516-X
- [ ] `EXASWILND001` — Core switch (`192.168.20.250`) · Cisco 9300
- [ ] `EXARTRLND001` — WAN edge router (`192.168.20.254`)
- [ ] `EXARACLND001` — BMC node 1 (`192.168.20.2`) · Dell iDRAC9
- [ ] `EXARACLND002` — RAC emulator VM (`192.168.20.3`)
- [ ] `EXAPVELND001` — Proxmox node 1 (`192.168.20.5`) · ZFS RAID1
- [ ] `EXADCRLND001` — DC (`192.168.20.10`) · RID Master · Infrastructure Master
- [ ] `EXASBCLND001` — VOIP SBC (`192.168.20.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVELND001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXAWKSLND001` — Workstation (`192.168.20.150`)
- [ ] `EXAPRNLND001` — Xerox WorkCentre

### Site-Specific Equipment
- [ ] `EXARADLND001` — BBC Office Radio Mk II (`192.168.20.80`) · FM-IP bridge
- [ ] `EXAMICLND001` — Shure SM7 microphone (`192.168.20.81`) · Dante audio
- [ ] `EXAPRNLND002` — ProCAT Stylus steno writer · court device

---

## BIR — Birmingham

**LAN:** `192.168.121.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXAFWLBIR001` — Firewall (`192.168.121.1`) · Palo Alto PAN-OS
- [ ] `EXASWIBIR001` — Core switch (`192.168.121.250`) · Cisco 9300
- [ ] `EXASWIBIR002` — Access switch (`192.168.121.251`)
- [ ] `EXARTRBIR001` — WAN edge router (`192.168.121.254`)
- [ ] `EXARACBIR001` — BMC node 1 (`192.168.121.2`) · Dell DRAC
- [ ] `EXARACBIR002` — RAC emulator VM (`192.168.121.3`)
- [ ] `EXAPVEBIR001` — Proxmox node 1 (`192.168.121.5`) · ZFS RAID1
- [ ] `EXADCRBIR001` — DC primary (`192.168.121.10`)
- [ ] `EXADCRBIR002` — DC secondary (`192.168.121.11`)
- [ ] `EXASRVBIR001` — Rocky Linux server (`192.168.121.20`) · Oracle DB
- [ ] `EXASBCBIR001` — VOIP SBC (`192.168.121.48`) · trunks to `EXACLDPBX001`
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
- [ ] WAPs `EXAWAPBIR001`–`002` — Ubiquiti UniFi U6-Pro

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
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXASWIMCR001` — Distribution switch (`192.168.161.250`) · Cisco 9300
- [ ] `EXARACMCR001` — BMC node 1 (`192.168.161.2`) · HPE iLO5
- [ ] `EXARACMCR002` — RAC emulator VM (`192.168.161.3`)
- [ ] `EXAPVEMCR001` — Proxmox node 1 (`192.168.161.5`) · ZFS RAID1
- [ ] `EXADCRMCR001` — DC primary (`192.168.161.10`) · PDC Emulator · RID/Infra Master
- [ ] `EXADCSMCR002` — DC secondary (`192.168.161.11`)
- [ ] `EXASBCMCR001` — VOIP SBC (`192.168.161.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEMCR001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXALAPMCR001`–`002` — Win11 laptops
- [ ] `EXAWKSMCR001`–`002` — Win10 desktops
- [ ] `EXAPRNMCR001` — Printer

### Site-Specific Equipment
<!-- To be documented -->

---

## LIV — Liverpool

**LAN:** `192.168.151.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXASWILIV001` — Core switch (`192.168.151.250`) · Cisco 9200
- [ ] `EXARACLIV001` — BMC node 1 (`192.168.151.2`) · HPE iLO5
- [ ] `EXARACLIV002` — RAC emulator VM (`192.168.151.3`)
- [ ] `EXAPVELIV001` — Proxmox node 1 (`192.168.151.5`) · ZFS RAID1
- [ ] `EXADCRLIV001` — DC (`192.168.151.10`) · WS2025
- [ ] `EXASBCLIV001` — VOIP SBC (`192.168.151.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVELIV001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
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
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXASWINEW001` — Access switch (`192.168.191.250`) · TP-Link JetStream
- [ ] `EXARACNEW001` — BMC node 1 (`192.168.191.2`) · Dell iDRAC9
- [ ] `EXARACNEW002` — RAC emulator VM (`192.168.191.3`)
- [ ] `EXAPVENEW001` — Proxmox node 1 (`192.168.191.5`) · ZFS RAID1
- [ ] `EXADCRNEW001` — DC (`192.168.191.10`)
- [ ] `EXASBCNEW001` — VOIP SBC (`192.168.191.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVENEW001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXASRVNEW001` — WS2022 file/print server
- [ ] `EXAWKSNEW099` — Win11 workstation ⚠️ LAPS expired

### Site-Specific Equipment
<!-- To be documented -->

---

## SHE — Sheffield

**LAN:** `192.168.114.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARACSHE001` — BMC node 1 (`192.168.114.2`)
- [ ] `EXARACSHE002` — RAC emulator VM (`192.168.114.3`)
- [ ] `EXAPVESHE001` — Proxmox node 1 (`192.168.114.5`) · ZFS RAID1
- [ ] `EXADCSSHE001` — DC (`192.168.114.10`)
- [ ] `EXASBCSHE001` — VOIP SBC (`192.168.114.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVESHE001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
<!-- To be documented -->

### Site-Specific Equipment
<!-- To be documented -->

---

## HAL — Halifax

**LAN:** `192.168.142.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARACHAL001` — BMC node 1 (`192.168.142.2`)
- [ ] `EXARACHAL002` — RAC emulator VM (`192.168.142.3`)
- [ ] `EXAPVEHAL001` — Proxmox node 1 (`192.168.142.5`) · ZFS RAID1
- [ ] `EXADCSHAL001` — DC (`192.168.142.10`)
- [ ] `EXASBCHAL001` — VOIP SBC (`192.168.142.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEHAL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
<!-- To be documented -->

### Site-Specific Equipment
<!-- To be documented -->

---

## HUL — Hull

**LAN:** `192.168.148.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARACHUL001` — BMC node 1 (`192.168.148.2`)
- [ ] `EXARACHUL002` — RAC emulator VM (`192.168.148.3`)
- [ ] `EXAPVEHUL001` — Proxmox node 1 (`192.168.148.5`) · ZFS RAID1
- [ ] `EXADCSHUL001` — DC (`192.168.148.10`)
- [ ] `EXASBCHUL001` — VOIP SBC (`192.168.148.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEHUL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
<!-- To be documented -->

### Site-Specific Equipment
<!-- To be documented -->

---

## COV — Coventry

**LAN:** `192.168.247.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM  
*Note: WAP/RTR-only site — minimal infrastructure.*

### Infrastructure Checklist
- [ ] `EXARTRCOV001` — WAN edge router (`192.168.247.254`) · Cisco ISR 4331
- [ ] `EXARACCOV001` — BMC node 1 (`192.168.247.2`)
- [ ] `EXARACCOV002` — RAC emulator VM (`192.168.247.3`)
- [ ] `EXAPVECOV001` — Proxmox node 1 (`192.168.247.5`) · ZFS RAID1
- [ ] `EXADCSCOV001` — DC (`192.168.247.10`)
- [ ] `EXASBCCOV001` — VOIP SBC (`192.168.247.48`) · trunks to `EXACLDPBX001`
- [ ] WAPs `EXAWAPCOV001`–`002` — Ubiquiti UniFi U6-Pro
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
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXASWICPH001` — Office switch (`192.168.231.250`) · TP-Link JetStream
- [ ] `EXARTRCPH001` — WAN edge router (`192.168.231.254`)
- [ ] `EXARACCPH001` — BMC node 1 (`192.168.231.2`) · Dell iDRAC9
- [ ] `EXARACCPH002` — RAC emulator VM (`192.168.231.3`)
- [ ] `EXAPVECPH001` — Proxmox node 1 (`192.168.231.5`) · ZFS RAID1
- [ ] `EXADCSCPH001` — DC primary (`192.168.231.10`) · example.com
- [ ] `EXADCSCPH002` — DC secondary (`192.168.231.11`) · example.net
- [ ] `EXASBCCPH001` — VOIP SBC (`192.168.231.48`) · trunks to `EXACLDPBX001`
- [ ] WAPs `EXAWAPCPH001`–`003` — Ubiquiti UniFi U6-Pro
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
**PVE nodes:** 3 (EU hub) · **BMC pool:** `.2` `.3` `.4` all physical

### Infrastructure Checklist
- [ ] `EXAFWLODE001` — Firewall (`192.168.126.1`) · Cisco ASA 5506-X
- [ ] `EXARACODE001` — BMC node 1 (`192.168.126.2`)
- [ ] `EXARACODE002` — BMC node 2 (`192.168.126.3`)
- [ ] `EXARACODE003` — BMC node 3 (`192.168.126.4`)
- [ ] `EXAPVEODE001` — Proxmox node 1 (`192.168.126.5`) · ZFS RAID1
- [ ] `EXAPVEODE002` — Proxmox node 2 (`192.168.126.6`) · ZFS RAID1
- [ ] `EXAPVEODE003` — Proxmox node 3 (`192.168.126.7`) · ZFS RAID1
- [ ] `EXADCSODE001` — DC primary (`192.168.126.10`) · PDC Emulator · RID/Infra Master
- [ ] `EXADCSODE002` — DC secondary (`192.168.126.11`)
- [ ] `EXASBCODE001` — VOIP SBC (`192.168.126.48`) · trunks to `EXACLDPBX001`
- [ ] WAPs `EXAWAPODE001`–`002` — Ubiquiti UniFi U6-Pro
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
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSKGE001` — out of sync 27 days, Windows Server 2016 EOL, disk space low.

### Infrastructure Checklist
- [ ] `EXARACKGE001` — BMC node 1 (`192.168.65.2`)
- [ ] `EXARACKGE002` — RAC emulator VM (`192.168.65.3`)
- [ ] `EXAPVEKGE001` — Proxmox node 1 (`192.168.65.5`) · ZFS RAID1
- [ ] `EXADCSKGE001` — DC (`192.168.65.10`) ⚠️ WS2016 EOL — rebuild required
- [ ] `EXASBCKGE001` — VOIP SBC (`192.168.65.48`) · trunks to `EXACLDPBX001`
- [ ] WAP `EXAWAPKGE001` — Ubiquiti UniFi U6-Pro
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
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARTRFAX001` — WAN edge router (`192.168.246.254`)
- [ ] `EXARACFAX001` — BMC node 1 (`192.168.246.2`)
- [ ] `EXARACFAX002` — RAC emulator VM (`192.168.246.3`)
- [ ] `EXAPVEFAX001` — Proxmox node 1 (`192.168.246.5`) · ZFS RAID1
- [ ] `EXADCSFAX001` — DC (`192.168.246.10`)
- [ ] `EXASBCFAX001` — VOIP SBC (`192.168.246.48`) · trunks to `EXACLDPBX001`
- [ ] WAPs `EXAWAPFAX001`–`002` — Ubiquiti UniFi U6-Pro
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
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARACKOR001` — BMC node 1 (`192.168.238.2`)
- [ ] `EXARACKOR002` — RAC emulator VM (`192.168.238.3`)
- [ ] `EXAPVEKOR001` — Proxmox node 1 (`192.168.238.5`) · ZFS RAID1
- [ ] `EXADCSKOR001` — DC (`192.168.238.10`)
- [ ] `EXASBCKOR001` — VOIP SBC (`192.168.238.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEKOR001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇩🇪 Deutschland

---

## BON — Bonn

**LAN:** `192.168.228.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXASWIBON001` — Office switch (`192.168.228.250`) · Cisco 2960X
- [ ] `EXARTRBON001` — WAN edge router (`192.168.228.254`)
- [ ] `EXARACBON001` — BMC node 1 (`192.168.228.2`) · Dell iDRAC9
- [ ] `EXARACBON002` — RAC emulator VM (`192.168.228.3`)
- [ ] `EXAPVEBON001` — Proxmox node 1 (`192.168.228.5`) · ZFS RAID1
- [ ] `EXADCSBON001` — DC (`192.168.228.10`) · **Schema Master · Domain Naming Master**
- [ ] `EXASBCBON001` — VOIP SBC (`192.168.228.48`) · trunks to `EXACLDPBX001`
- [ ] WAPs `EXAWAPBON001`–`002` — Ubiquiti UniFi U6-Pro
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
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARTRBER001` — WAN edge router (`192.168.113.254`)
- [ ] `EXARACBER001` — BMC node 1 (`192.168.113.2`)
- [ ] `EXARACBER002` — RAC emulator VM (`192.168.113.3`)
- [ ] `EXAPVEBER001` — Proxmox node 1 (`192.168.113.5`) · ZFS RAID1
- [ ] `EXADCSBER001` — DC (`192.168.113.10`) · WS2019 · PDC Emulator · RID/Infra Master
- [ ] `EXASBCBER001` — VOIP SBC (`192.168.113.48`) · trunks to `EXACLDPBX001`
- [ ] WAPs `EXAWAPBER001`–`002` — Ubiquiti UniFi U6-Pro
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEBER001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXASRVBER001` — WS2019 legacy app server
- [ ] `EXANIXBER001` — Debian 12 server

### Site-Specific Equipment
<!-- To be documented -->

---

## MUN — Munich

**LAN:** `192.168.189.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXASWIMUN001` — Access switch (`192.168.189.250`) · Cisco 9200
- [ ] `EXARACMUN001` — BMC node 1 (`192.168.189.2`) · HPE iLO5
- [ ] `EXARACMUN002` — RAC emulator VM (`192.168.189.3`)
- [ ] `EXAPVEMUN001` — Proxmox node 1 (`192.168.189.5`) · ZFS RAID1
- [ ] `EXADCSMUN001` — DC (`192.168.189.10`)
- [ ] `EXASBCMUN001` — VOIP SBC (`192.168.189.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEMUN001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
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
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARACGOT001` — BMC node 1 (`192.168.46.2`)
- [ ] `EXARACGOT002` — RAC emulator VM (`192.168.46.3`)
- [ ] `EXAPVEGOT001` — Proxmox node 1 (`192.168.46.5`) · ZFS RAID1
- [ ] `EXADCSGOT001` — DC (`192.168.46.10`)
- [ ] `EXASBCGOT001` — VOIP SBC (`192.168.46.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEGOT001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇳🇴 Norge

---

## OSL — Oslo

**LAN:** `192.168.47.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARACOSL001` — BMC node 1 (`192.168.47.2`)
- [ ] `EXARACOSL002` — RAC emulator VM (`192.168.47.3`)
- [ ] `EXAPVEOSL001` — Proxmox node 1 (`192.168.47.5`) · ZFS RAID1
- [ ] `EXADCSOSL001` — DC (`192.168.47.10`)
- [ ] `EXASBCOSL001` — VOIP SBC (`192.168.47.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEOSL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇳🇱 Nederland

---

## AMS — Amsterdam

**LAN:** `192.168.31.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARACAMS001` — BMC node 1 (`192.168.31.2`)
- [ ] `EXARACAMS002` — RAC emulator VM (`192.168.31.3`)
- [ ] `EXAPVEAMS001` — Proxmox node 1 (`192.168.31.5`) · ZFS RAID1
- [ ] `EXADCSAMS001` — DC (`192.168.31.10`)
- [ ] `EXASBCAMS001` — VOIP SBC (`192.168.31.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEAMS001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇮🇹 Italia

---

## MIL — Milan

**LAN:** `192.168.39.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARACMIL001` — BMC node 1 (`192.168.39.2`)
- [ ] `EXARACMIL002` — RAC emulator VM (`192.168.39.3`)
- [ ] `EXAPVEMIL001` — Proxmox node 1 (`192.168.39.5`) · ZFS RAID1
- [ ] `EXADCSMIL001` — DC (`192.168.39.10`)
- [ ] `EXASBCMIL001` — VOIP SBC (`192.168.39.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEMIL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇦🇹 Österreich

---

## VIE — Vienna

**LAN:** `192.168.78.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARACVIE001` — BMC node 1 (`192.168.78.2`)
- [ ] `EXARACVIE002` — RAC emulator VM (`192.168.78.3`)
- [ ] `EXAPVEVIE001` — Proxmox node 1 (`192.168.78.5`) · ZFS RAID1
- [ ] `EXADCSVIE001` — DC (`192.168.78.10`)
- [ ] `EXASBCVIE001` — VOIP SBC (`192.168.78.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEVIE001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇨🇦 Canada

---

## BRK — Brockville, Ontario *(NA/APAC Hub)*

**LAN:** `192.168.136.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (NA/APAC hub) · **BMC pool:** `.2` `.3` `.4` all physical

> ⚠️ `EXADCSBRK001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXARTRBRK001` — WAN edge router (`192.168.136.254`)
- [ ] `EXARACBRK001` — BMC node 1 (`192.168.136.2`)
- [ ] `EXARACBRK002` — BMC node 2 (`192.168.136.3`)
- [ ] `EXARACBRK003` — BMC node 3 (`192.168.136.4`)
- [ ] `EXAPVEBRK001` — Proxmox node 1 (`192.168.136.5`) · ZFS RAID1
- [ ] `EXAPVEBRK002` — Proxmox node 2 (`192.168.136.6`) · ZFS RAID1
- [ ] `EXAPVEBRK003` — Proxmox node 3 (`192.168.136.7`) · ZFS RAID1
- [ ] `EXADCSBRK001` — DC (`192.168.136.10`) ⚠️ Services stopped — resolve before sign-off
- [ ] `EXASBCBRK001` — VOIP SBC (`192.168.136.48`) · trunks to `EXACLDPBX001`
- [ ] WAP `EXAWAPBRK001` — Ubiquiti UniFi U6-Pro
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

**LAN:** `192.168.164.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSTOR001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXARACTOR001` — BMC node 1 (`192.168.164.2`)
- [ ] `EXARACTOR002` — RAC emulator VM (`192.168.164.3`)
- [ ] `EXAPVETOR001` — Proxmox node 1 (`192.168.164.5`) · ZFS RAID1
- [ ] `EXADCSTOR001` — DC (`192.168.164.10`) ⚠️ Services stopped
- [ ] `EXASBCTOR001` — VOIP SBC (`192.168.164.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVETOR001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Site-Specific Equipment
<!-- To be documented -->

---

## MTL — Montreal, Quebec

**LAN:** `192.168.154.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARACMTL001` — BMC node 1 (`192.168.154.2`)
- [ ] `EXARACMTL002` — RAC emulator VM (`192.168.154.3`)
- [ ] `EXAPVEMTL001` — Proxmox node 1 (`192.168.154.5`) · ZFS RAID1
- [ ] `EXADCSMTL001` — DC (`192.168.154.10`)
- [ ] `EXASBCMTL001` — VOIP SBC (`192.168.154.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEMTL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇺🇸 United States

---

## LAX — Los Angeles, California

**LAN:** `192.168.213.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSLAX001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXAFWLLAX001` — Firewall (`192.168.213.1`) · Palo Alto PAN-OS 10.x
- [ ] `EXASWILAX001` — Core switch (`192.168.213.250`) · Cisco 9300
- [ ] `EXASWILAX002` — Access switch (`192.168.213.251`) · Cisco 2960
- [ ] `EXARTRLAX001` — WAN edge router (`192.168.213.254`)
- [ ] `EXARACLAX001` — BMC node 1 (`192.168.213.2`) · Dell iDRAC9
- [ ] `EXARACLAX002` — RAC emulator VM (`192.168.213.3`)
- [ ] `EXAPVELAX001` — Proxmox node 1 (`192.168.213.5`) · ZFS RAID1
- [ ] `EXADCSLAX001` — DC (`192.168.213.10`) ⚠️ Services stopped
- [ ] `EXASRVLAX001` — Rocky Linux server (`192.168.213.20`) · local services/DB
- [ ] `EXASBCLAX001` — VOIP SBC (`192.168.213.48`) · trunks to `EXACLDPBX001`
- [ ] WAPs `EXAWAPLAX001`–`003` — Ubiquiti UniFi U6-Pro
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
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSNYC001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXARACNYC001` — BMC node 1 (`192.168.212.2`)
- [ ] `EXARACNYC002` — RAC emulator VM (`192.168.212.3`)
- [ ] `EXAPVENYC001` — Proxmox node 1 (`192.168.212.5`) · ZFS RAID1
- [ ] `EXADCSNYC001` — DC (`192.168.212.10`) ⚠️ Services stopped
- [ ] `EXASBCNYC001` — VOIP SBC (`192.168.212.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVENYC001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Site-Specific Equipment
<!-- To be documented -->

---

## NJC — Camden, New Jersey

**LAN:** `192.168.201.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSNJC001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXARACNJC001` — BMC node 1 (`192.168.201.2`)
- [ ] `EXARACNJC002` — RAC emulator VM (`192.168.201.3`)
- [ ] `EXAPVENJC001` — Proxmox node 1 (`192.168.201.5`) · ZFS RAID1
- [ ] `EXADCSNJC001` — DC (`192.168.201.10`) ⚠️ Services stopped
- [ ] `EXASBCNJC001` — VOIP SBC (`192.168.201.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVENJC001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Site-Specific Equipment
<!-- To be documented -->

---

## MIA — Miami, Florida

**LAN:** `192.168.135.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist
- [ ] `EXARACMIA001` — BMC node 1 (`192.168.135.2`)
- [ ] `EXARACMIA002` — RAC emulator VM (`192.168.135.3`)
- [ ] `EXAPVEMIA001` — Proxmox node 1 (`192.168.135.5`) · ZFS RAID1
- [ ] `EXADCSMIA001` — DC (`192.168.135.10`) · pending build
- [ ] `EXASBCMIA001` — VOIP SBC (`192.168.135.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEMIA001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXALAPMIA001` — MacBook · macOS Sonoma

### Site-Specific Equipment
- [ ] `EXACOFMIA001` — Cuban Covfefe machine (`192.168.135.60`) · VxWorks
<!-- Additional site-specific equipment to be documented -->

---

## ATL — Athens, Georgia

**LAN:** `192.168.44.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSATL001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXARACATL001` — BMC node 1 (`192.168.44.2`)
- [ ] `EXARACATL002` — RAC emulator VM (`192.168.44.3`)
- [ ] `EXAPVEATL001` — Proxmox node 1 (`192.168.44.5`) · ZFS RAID1
- [ ] `EXADCSATL001` — DC (`192.168.44.10`) ⚠️ Services stopped
- [ ] `EXASBCATL001` — VOIP SBC (`192.168.44.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEATL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Site-Specific Equipment
<!-- To be documented -->

---

## CHI — Chicago, Illinois

**LAN:** `192.168.214.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSCHI001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXARACCHI001` — BMC node 1 (`192.168.214.2`)
- [ ] `EXARACCHI002` — RAC emulator VM (`192.168.214.3`)
- [ ] `EXAPVECHI001` — Proxmox node 1 (`192.168.214.5`) · ZFS RAID1
- [ ] `EXADCSCHI001` — DC (`192.168.214.10`) ⚠️ Services stopped
- [ ] `EXASBCCHI001` — VOIP SBC (`192.168.214.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVECHI001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Site-Specific Equipment
<!-- To be documented -->

---

---

## 🇦🇺 Australia

---

## SYD — Sydney, NSW

**LAN:** `192.168.29.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSSYD001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXAFWLSYD001` — Firewall (`192.168.29.1`) · FortiGate 7.x
- [ ] `EXASWISYD001` — Core switch (`192.168.29.250`) · Cisco 9300
- [ ] `EXASWISYD002` — Access switch (`192.168.29.251`) · Cisco 2960
- [ ] `EXARACSYD001` — BMC node 1 (`192.168.29.2`) · Dell iDRAC9
- [ ] `EXARACSYD002` — RAC emulator VM (`192.168.29.3`)
- [ ] `EXAPVESYD001` — Proxmox node 1 (`192.168.29.5`) · ZFS RAID1
- [ ] `EXADCSSYD001` — DC (`192.168.29.10`) ⚠️ Services stopped
- [ ] `EXASRVSYD001` — WS2022 server (`192.168.29.20`) · local infra
- [ ] `EXASBCSYD001` — VOIP SBC (`192.168.29.48`) · trunks to `EXACLDPBX001`
- [ ] WAP `EXAWAPSYD001` — Ubiquiti UniFi
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
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSMEL001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXAFWLMEL001` — Firewall (`192.168.61.1`) · FortiGate 7.x
- [ ] `EXASWIMEL001` — Core switch (`192.168.61.250`) · Cisco 9300
- [ ] `EXASWIMEL002` — Access switch (`192.168.61.251`) · Cisco 2960
- [ ] `EXARACMEL001` — BMC node 1 (`192.168.61.2`) · HPE iLO5
- [ ] `EXARACMEL002` — RAC emulator VM (`192.168.61.3`)
- [ ] `EXAPVEMEL001` — Proxmox node 1 (`192.168.61.5`) · ZFS RAID1
- [ ] `EXADCSMEL001` — DC (`192.168.61.10`) ⚠️ Services stopped
- [ ] `EXASRVMEL001` — WS2022 server (`192.168.61.20`) · local file/print
- [ ] `EXASBCMEL001` — VOIP SBC (`192.168.61.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEMEL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist
- [ ] `EXAMBPMEL001` — MacBook Pro
- [ ] `EXAWKSMEL001` — Win11 workstation
- [ ] `EXAPHNMEL001` — iOS phone
- [ ] `EXATABMEL001` — iPad

### Site-Specific Equipment
- [ ] `EXALCDMEL001` — Samsung Signage display
- [ ] `EXAPRNMEL001` — HP LaserJet
- [ ] `EXANASMEL001` — Synology NAS · DSM 7.x

---

---

## 🇳🇿 New Zealand

---

## AKL — Auckland

**LAN:** `192.168.93.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSAKL001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist
- [ ] `EXAFWLAKL001` — Firewall (`192.168.93.1`) · FortiGate 7.x
- [ ] `EXASWIAKL001` — Core switch (`192.168.93.250`) · Cisco 9300
- [ ] `EXASWIAKL002` — Access switch (`192.168.93.251`) · Cisco 2960
- [ ] `EXARTRAKL001` — WAN edge router (`192.168.93.254`)
- [ ] `EXARACAKL001` — BMC node 1 (`192.168.93.2`) · HPE iLO5
- [ ] `EXARACAKL002` — RAC emulator VM (`192.168.93.3`)
- [ ] `EXAPVEAKL001` — Proxmox node 1 (`192.168.93.5`) · ZFS RAID1
- [ ] `EXADCSAKL001` — DC (`192.168.93.10`) ⚠️ Services stopped
- [ ] `EXASRVAKL001` — WS2022 server (`192.168.93.20`) · local server
- [ ] `EXASBCAKL001` — VOIP SBC (`192.168.93.48`) · trunks to `EXACLDPBX001`
- [ ] WAPs `EXAWAPAKL001`–`002` — Ubiquiti UniFi
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
