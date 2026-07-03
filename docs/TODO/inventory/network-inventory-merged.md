# Example Music Limited — Network & Infrastructure Inventory

> **Classification:** Internal — Infrastructure
> **Forest:** `jukebox.internal`
> **Domains:** `example.net` · `example.org` · `example.com`
> **Provisioning network:** `192.168.139.0/24`
> **Credentials:** See password manager — do **not** store passwords in this document
> **Source of truth for subnets:** `sites.csv` — all subnet assignments derive from this file

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-29 | Merged `network-inventory.md` and `site-inventory.md` into single document. CLD EXASVR renumbering: 001=DNS, 002=WAC, 003=Ansible, 004=Rudder. ATL subnet corrected to `192.168.33.0/24` (sites.csv canonical). TOR subnet corrected to `192.168.146.0/24`. EXAPRVFAL001 renamed EXAPRVCLD001. EXAPRNGLA001 corrected hostname (was EXAPGLAGLA001 / EXAPRNZGLA001). EXAATTLAX001 corrected to EXAASTLAX001. EDI DC remediation plan added. BRD→BER rename plan documented. |
| 2026-03-05 | Full review — subnets corrected against sites.csv; new sites added |
| 2026-03-03 | TOR added; BRD renamed from BER; NJC/NYC corrected to own subnets |
| 2026-03-01 | Initial document |

---

## ⚠️ Hostname Warning — CLD EXASVR vs EXASRV

> **`EXASVRCLD001`** (DNS/BIND server) and the previous working name **`EXASRVCLD001`** differ by one transposed letter only.
> The correct prefix is **`EXASVR`** throughout. Any reference to `EXASRV` is an error.
> The full CLD server numbering is: **001** = DNS · **002** = WAC · **003** = Ansible · **004** = Rudder

---

## Standard IP Convention

Every site follows this addressing scheme within its `/24` subnet. Exceptions are noted per site.

| Address | Role | Hostname pattern |
|---------|------|-----------------|
| `.1` | Primary gateway / firewall | `EXAFWL<SITE>001` or `EXARTR<SITE>001` |
| `.2` | BMC pool slot 1 — DRAC/iLO (PVE node 1) | `EXARAC<SITE>001` |
| `.3` | BMC pool slot 2 — DRAC/iLO or RAC emulator VM | `EXARAC<SITE>002` |
| `.4` | BMC pool slot 3 — hub sites only | `EXARAC<SITE>003` |
| `.5` | PVE node 1 | `EXAPVE<SITE>001` |
| `.6` | PVE node 2 — hub sites | `EXAPVE<SITE>002` |
| `.7` | PVE node 3 — FAL/ODE/BRK only | `EXAPVE<SITE>003` |
| `.10` | Domain Controller — primary | `EXADCS<SITE>001` |
| `.11` | Domain Controller — secondary | `EXADCS<SITE>002` |
| `.48` | VOIP SBC — trunks to `EXACLDPBX001` | `EXASBC<SITE>001` |
| `.100`–`.249` | DHCP pool | — |
| `.250`–`.252` | Switches | `EXASWI<SITE>001`–`003` |
| `.253` | Secondary gateway / firewall | `EXAFWL<SITE>001` (if `.1` is router) |
| `.254` | WAN edge router | `EXARTR<SITE>001` or `EXARTR<SITE>002` |

> **BMC pool:** `.2`/`.3`/`.4` shared between physical DRAC/iLO interfaces and RAC emulator VMs.
> Physical PVE node BMCs consume from `.2` upward; the RAC emulator VM takes the next free slot.
> On three-PVE-node sites the pool is fully consumed by physical BMCs.

---

## Global Site Summary

| Code | Location | Country | LAN Subnet | Domain | Notes |
|------|----------|---------|-----------|--------|-------|
| CLD | Cloud / Provisioning | — | `192.168.139.0/24` | — | WireGuard hub |
| FAL | Falkirk | 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland | `192.168.76.0/24` | `example.net` | **Head Office** · 3-node hub |
| EDI | Edinburgh | 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland | `192.168.131.0/24` | `example.org`/`example.net` | ⚠️ DC issues |
| GLA | Glasgow | 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland | `192.168.141.0/24` | `example.net` | Regional DC hub |
| CLY | Clydebank | 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland | `192.168.41.0/24` | `example.net` | |
| DUN | Dundee | 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland | `192.168.138.0/24` | `example.net` | |
| PER | Perth | 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland | `192.168.173.0/24` | `example.net` | Solaris archive |
| ABD | Aberdeen | 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland | `192.168.224.0/24` | `example.org` | Satellite office |
| LND | London | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England | `192.168.20.0/24` | `example.net` | Regional DC hub |
| BIR | Birmingham | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England | `192.168.121.0/24` | `example.net` | |
| MCR | Manchester | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England | `192.168.161.0/24` | `example.org` | PDC Emulator for `example.org` |
| LIV | Liverpool | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England | `192.168.151.0/24` | `example.org` | |
| NEW | Newcastle | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England | `192.168.191.0/24` | `example.org` | |
| SHE | Sheffield | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England | `192.168.114.0/24` | `example.net` | |
| HAL | Halifax | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England | `192.168.142.0/24` | `example.net` | |
| HUL | Hull | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England | `192.168.148.0/24` | `example.net` | |
| COV | Coventry | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England | `192.168.247.0/24` | `example.net` | WAP/RTR only |
| CPH | København | 🇩🇰 Danmark | `192.168.231.0/24` | `example.com`/`example.net` | |
| ODE | Odense | 🇩🇰 Danmark | `192.168.126.0/24` | `example.net` | EU hub · 3-node |
| KGE | Køge | 🇩🇰 Danmark | `192.168.65.0/24` | `example.net` | ⚠️ DC EOL/out of sync |
| FAX | Faxe | 🇩🇰 Danmark | `192.168.246.0/24` | `example.net` | |
| KOR | Korsør | 🇩🇰 Danmark | `192.168.238.0/24` | `example.net` | |
| BON | Bonn | 🇩🇪 Deutschland | `192.168.228.0/24` | `example.net` | Schema/Domain Naming Master |
| BRD | West Berlin | 🇩🇪 Deutschland | `192.168.113.0/24` | `example.net` | ⚠️ Legacy code — see BER note |
| MUN | Munich | 🇩🇪 Deutschland | `192.168.189.0/24` | `example.net` | |
| GOT | Gothenburg | 🇸🇪 Sverige | `192.168.46.0/24` | `example.net` | |
| OSL | Oslo | 🇳🇴 Norge | `192.168.47.0/24` | `example.net` | |
| AMS | Amsterdam | 🇳🇱 Nederland | `192.168.31.0/24` | `example.net` | |
| MIL | Milan | 🇮🇹 Italia | `192.168.39.0/24` | `example.net` | |
| VIE | Vienna | 🇦🇹 Österreich | `192.168.78.0/24` | `example.net` | |
| BRK | Brockville | 🇨🇦 Canada | `192.168.136.0/24` | `example.net` | NA/APAC hub · 3-node · ⚠️ DC stopped |
| TOR | Toronto | 🇨🇦 Canada | `192.168.146.0/24` | `example.net` | ⚠️ DC stopped |
| MTL | Montreal | 🇨🇦 Canada | `192.168.154.0/24` | `example.net` | |
| LAX | Los Angeles | 🇺🇸 USA | `192.168.213.0/24` | `example.net` | ⚠️ DC stopped |
| NYC | New York | 🇺🇸 USA | `192.168.212.0/24` | `example.net` | ⚠️ DC stopped |
| NJC | New Jersey | 🇺🇸 USA | `192.168.201.0/24` | `example.net` | ⚠️ DC stopped |
| MIA | Miami | 🇺🇸 USA | `192.168.135.0/24` | `example.net` | DC/SBC present |
| ATL | Atlanta | 🇺🇸 USA | `192.168.33.0/24` | `example.net` | ⚠️ DC stopped |
| CHI | Chicago | 🇺🇸 USA | `192.168.214.0/24` | `example.net` | ⚠️ DC stopped |
| SYD | Sydney | 🇦🇺 Australia | `192.168.29.0/24` | `example.net` | ⚠️ DC stopped |
| MEL | Melbourne | 🇦🇺 Australia | `192.168.61.0/24` | `example.net` | ⚠️ DC stopped |
| AKL | Auckland | 🇳🇿 New Zealand | `192.168.93.0/24` | `example.net` | ⚠️ DC stopped |

---

## ⚠️ Known Issues & Actions Required

| Priority | Site | Device | Issue |
|----------|------|--------|-------|
| 🔴 Critical | EDI | `EXADCSEDI002` (currently named `EXADCREDI001`) | Needs rebuild at `.11` before EDI003 can be decommissioned |
| 🔴 Critical | EDI | `EXADCSEDI003` | DFSR stopped · C: 5% free · to be decommissioned after EDI002 rebuilt |
| 🔴 Critical | KGE | `EXADCSKGE001` | No replication 27 days · Windows Server 2016 EOL · disk low |
| 🟠 High | BRK, TOR, NYC, NJC, ATL, LAX, CHI, SYD, MEL, AKL | Multiple DCs | DNS/Netlogon/KDC stopped |
| 🟡 Medium | NEW | `EXAWKSNEW099` | LAPS password expired |
| 🟡 Medium | MUN | `EXALAPMUN002` | LAPS expired 61 days · last login 95 days ago |
| 🟡 Medium | FAL | `EXAPVEFAL001`–`003` | Not on ZFS RAID1 · boot independence test pending |
| 🔵 Info | BIR, LAX | Instruments | Atari ST, Fairlight CMI, LinnDrum on production LAN — no security controls |
| 🔵 Info | FAL | Vending | Multiple legacy OS vending machines on production network (NT4, XPe, VxWorks) |
| 🔵 Info | All | BRD→BER | West Berlin site will be fully rebuilt and renamed BER on German reunification |

---

## Site Commissioning Summary

| Code | Site | Commissioned | Notes |
|------|------|:------------:|-------|
| CLD | Cloud / Provisioning | [ ] | |
| FAL | Falkirk | [ ] | Head office · 3-node hub |
| EDI | Edinburgh | [ ] | ⚠️ DC remediation required first |
| GLA | Glasgow | [ ] | IPs being corrected to convention |
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
| BRD | West Berlin | [ ] | ⚠️ Full rebuild on reunification → site code becomes BER |
| MUN | Munich | [ ] | |
| GOT | Gothenburg | [ ] | |
| OSL | Oslo | [ ] | |
| AMS | Amsterdam | [ ] | |
| MIL | Milan | [ ] | |
| VIE | Vienna | [ ] | |
| BRK | Brockville | [ ] | NA/APAC hub · 3-node · ⚠️ DC stopped |
| TOR | Toronto | [ ] | ⚠️ DC stopped |
| MTL | Montreal | [ ] | |
| LAX | Los Angeles | [ ] | ⚠️ DC stopped |
| NYC | New York | [ ] | ⚠️ DC stopped |
| NJC | New Jersey | [ ] | ⚠️ DC stopped |
| MIA | Miami | [ ] | |
| ATL | Atlanta | [ ] | ⚠️ DC stopped · subnet corrected to `192.168.33.0/24` |
| CHI | Chicago | [ ] | ⚠️ DC stopped |
| SYD | Sydney | [ ] | ⚠️ DC stopped |
| MEL | Melbourne | [ ] | ⚠️ DC stopped |
| AKL | Auckland | [ ] | ⚠️ DC stopped |

---

## ☁️ Cloud / Provisioning — CLD

**LAN:** `192.168.139.0/24`
**Role:** WireGuard hub — routes to all site subnets. Central PBX, DNS, Ansible, Rudder, WAC, Provisioning.

> ⚠️ **Hostname note:** `EXASVRCLD001` (DNS) and the former working name `EXASRVCLD001` differ by one transposed letter. The correct prefix is `EXASVR` throughout. See the warning at the top of this document.

### Infrastructure Checklist

- [ ] `EXAFWLCLD001` — Firewall / WireGuard hub (`192.168.139.1`) · CNAME `ovhfwl.knight139.co.uk`
- [ ] `EXASVRCLD001` — DNS/BIND server (`192.168.139.10`) · `jukebox.internal` authoritative
- [ ] `EXASVRCLD002` — Windows Admin Centre (`192.168.139.20`) · WS2022 · reaches all site DCs
- [ ] `EXASVRCLD004` — Rudder configuration management (`192.168.139.22`)
- [ ] `EXACLDPBX001` — Central 3CX PBX (`192.168.139.48`) · all site SBCs trunk here
- [ ] `EXASVRCLD003` — Ansible control node (`192.168.139.49`) · manages all sites
- [ ] `EXAPRVCLD001` — Provisioning server (`192.168.139.50`) · PXE · ISOs · Ansible keys · scripts
- [ ] WireGuard routes verified to all site subnets
- [ ] Ansible key distribution tested from `EXAPRVCLD001`
- [ ] Rudder agents checked in from test node
- [ ] DNS self-test: `dig @192.168.139.10 exasvrcld001.jukebox.internal`

| Hostname | Role | OS | IP | Notes |
|----------|------|----|----|-------|
| `EXAFWLCLD001` | Firewall / WireGuard hub | — | `192.168.139.1` | CNAME `ovhfwl.knight139.co.uk` |
| `EXASVRCLD001` | DNS/BIND server | Debian trixie | `192.168.139.10` | `jukebox.internal` authoritative |
| `EXASVRCLD002` | Windows Admin Centre | Windows Server 2022 | `192.168.139.20` | Reaches all site DCs |
| `EXASVRCLD004` | Rudder | Debian | `192.168.139.22` | Configuration management |
| `EXACLDPBX001` | Central PBX | 3CX | `192.168.139.48` | All site SBCs trunk here |
| `EXASVRCLD003` | Ansible control node | Debian | `192.168.139.49` | Central Ansible — manages all sites |
| `EXAPRVCLD001` | Provisioning server | — | `192.168.139.50` | PXE · ISOs · Ansible keys · scripts |

---

## 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland

---

### FAL — Falkirk *(Head Office)*

**Address:** Brockville Stadium, 1876 Hope Street, Falkirk
**Entity:** Example Music (Scotland) Ltd
**LAN:** `192.168.76.0/24` · **VPN:** `10.0.76.0/24` · **Domain:** `example.net`
**PVE nodes:** 3 (hub) · **BMC pool:** `.2` `.3` `.4` all physical

> ℹ️ FAL has two gateway devices: `EXARTRFAL001` (Cisco ASA) at `.1` acting as primary gateway, and `EXAFWLFAL001` (FortiGate) at `.253` as the VPN/WireGuard firewall. `EXARTRFAL002` (FortiGate WAN edge) is at `.254`.

### Infrastructure Checklist

- [ ] `EXARTRFAL001` — Cisco ASA primary gateway (`192.168.76.1`)
- [ ] `EXASWIFAL001` — Core switch 1 (`192.168.76.250`) · Cisco Catalyst 9300
- [ ] `EXASWIFAL002` — Core switch 2 (`192.168.76.251`) · Cisco Catalyst 9300
- [ ] `EXAFWLFAL001` — FortiGate firewall / WireGuard (`192.168.76.253`) · WireGuard `10.0.76.1`
- [ ] `EXARTRFAL002` — FortiGate WAN edge (`192.168.76.254`)
- [ ] `EXARACFAL001` — BMC node 1 (`192.168.76.2`) · Dell iDRAC9
- [ ] `EXARACFAL002` — BMC node 2 (`192.168.76.3`) · Dell iDRAC9
- [ ] `EXARACFAL003` — BMC node 3 (`192.168.76.4`) · Dell iDRAC9
- [ ] `EXAPVEFAL001` — Proxmox node 1 (`192.168.76.5`) · PVE 8.3 · ⚠️ ZFS RAID1 pending
- [ ] `EXAPVEFAL002` — Proxmox node 2 (`192.168.76.6`) · PVE 8.3 · ⚠️ ZFS RAID1 pending
- [ ] `EXAPVEFAL003` — Proxmox node 3 (`192.168.76.7`) · PVE 8.3 · ⚠️ ZFS RAID1 pending
- [ ] `EXADCSFAL001` — DC primary (`192.168.76.10`) · WS2022 · PDC Emulator · Global Catalog
- [ ] `EXADCSFAL002` — DC secondary (`192.168.76.11`) · WS2022 · Global Catalog
- [ ] `EXASBCFAL001` — VOIP SBC (`192.168.76.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] `EXANASFAL001` — NAS (`192.168.76.32`) · FreeNAS 13.0-U6 · primary storage
- [ ] `EXATARFAL001` — Tape archiver (`192.168.76.33`) · Solaris Embedded · legacy archive
- [ ] WireGuard tunnel verified
- [ ] DHCP pool `.100`–`.249` confirmed active
- [ ] DNS resolving `jukebox.internal` from site
- [ ] ⚠️ Boot independence test pending (both nodes must boot solo from ZFS mirror)

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEFAL001 | rpool | mirror-0 | sda3 | sdb3 | ⚠️ pending | [ ] | [ ] |
| EXAPVEFAL002 | rpool | mirror-0 | sda3 | sdb3 | ⚠️ pending | [ ] | [ ] |
| EXAPVEFAL003 | rpool | mirror-0 | sda3 | sdb3 | ⚠️ pending | [ ] | [ ] |

### Endpoints Checklist

- [ ] `EXAWKSFAL001` — Workstation (`192.168.76.100`) · Win11 Pro 23H2 · Analog Mixing Desk v1
- [ ] `EXAWKSFAL002` — Workstation (`192.168.76.101`) · Win11 Pro 23H2 · Reel-to-Reel 24-track
- [ ] `EXAWKSFAL003` — Workstation (`192.168.76.102`) · Win11 Pro 23H2 · Shared editing
- [ ] `EXALAPFAL001` — Laptop (`192.168.76.103`) · Win11 Pro 23H2 · Production
- [ ] `EXASURFAL001` — Surface (`192.168.76.104`) · Win11 23H2
- [ ] `EXAPHNFAL001`–`003` · `EXAPHNFAL006`–`007` — Yealink T58A phones
- [ ] `EXATABFAL001` — Tablet
- [ ] WAPs `EXAWAPFAL001`–`006` — Ubiquiti UniFi U6-Pro

### Security & Building Systems

- [ ] `EXACAMFAL001` — Camera (`192.168.76.70`) · Axis P3245-LVE · front entrance
- [ ] `EXACAMFAL002` — Camera (`192.168.76.71`) · Axis P3245-LVE · studio hallway
- [ ] `EXACAMFAL003` — Camera (`192.168.76.72`) · Axis P3245-LVE · car park
- [ ] `EXACAMFAL004` — Camera (`192.168.76.73`) · Axis P3245-LVE · rear loading bay
- [ ] `EXARDRFAL001` — Badge reader (`192.168.76.16`) · HID Signo
- [ ] `EXACLKFAL001` — NTP clock (`192.168.76.80`) · embedded NTP
- [ ] `EXATTYFAL001` — VT320 serial terminal · no IP

### Site-Specific Equipment

- [ ] `EXAPMPFAL001` — Networked petrol pump (`192.168.76.60`) · BP Grangemouth
- [ ] `EXALCDFAL001` — Samsung Tizen display (`192.168.76.50`) · reception
- [ ] `EXAVCUFAL001` — Poly Studio X70 (`192.168.76.51`) · Brockville Suite video conf
- [ ] `EXATEAFAL001` — Smart coffee machine (`192.168.76.61`) · Red Balloon
- [ ] `EXADONFAL001` — Tim Hortons vending (`192.168.76.62`) · VxWorks
- [ ] `EXAVNDFAL002` — Retro Irn-Bru machine (`192.168.76.63`) · NT4 Embedded
- [ ] `EXAVNDFAL003` — McCowans sweet dispenser (`192.168.76.64`) · XPe
- [ ] `EXAVNDFAL004` — Mrs Tily sweet dispenser (`192.168.76.65`) · NT4
- [ ] `EXAVNDFAL005` — ¼lb Confectionery machine (`192.168.76.66`) · NT4
- [ ] `EXAMUSFAL001` — Pureline 128V Retro Vinyl Jukebox (`192.168.76.67`)
- [ ] `EXAPAYFAL001` — GPO Kiosk No.6 payphone (`192.168.76.95`) · SIP gateway

### Vehicle & Transport Fleet *(non-networked assets)*

- [ ] `EXABUSFAL001` — 1980 Leyland National 2 tour bus · `EXABUS1` (GB)
- [ ] `EXABUSFAL002` — 1983 Leyland DAB tour bus · `EXABUS2` (DK)
- [ ] `EXABUSFAL003` — 1980 MCI MC-9 Crusader tour bus · `EXABUS3` (CA)
- [ ] `EXACARFAL001` — Navy Blue Rover SD1 · `FFC 1876` (GB)
- [ ] `EXACARFAL002` — Black Mercedes-Benz W12 · `BN EH K89` (DE/Bonn)
- [ ] `EXACARFAL003` — Blue 1983 Saab 900 soft-top · `OB 1997` (DK)
- [ ] `EXACARFAL004` — Metallic Blue Caprice Classic Landau · `F 1876` (CA)
- [ ] `EXACARFAL005` — White Rolls-Royce Silver Shadow · `FIN 139` (USA/FL)
- [ ] `EXATRKFAL001` — 1985 Ford Cargo Flatbed · `ETRK1` (GB)
- [ ] `EXATRKFAL002` — 1985 Ford Cargo Box Truck · `ETRK2` (GB)
- [ ] `EXATRKFAL003` — 1985 Ford Cargo Elongated Box Truck · `ETRK3` (GB)
- [ ] `EXATRKFAL004` — 1985 Ford Cargo Articulated Truck · `ETRK4` (GB)
- [ ] `EXATRKFAL005` — 1985 Ford Transit Van · `ETRK5` (GB)
- [ ] `EXAJETFAL001` — Learjet 36B "Clipper Helle Vikner" · EU · `OY-EHV` (DK) · 8 seats
- [ ] `EXAJETFAL002` — Learjet 36B "Clipper Sannie Carlson" · UK · `OY-ESC` (DK) · 8 seats
- [ ] `EXAJETFAL003` — Learjet 36B "Clipper Stephanie Nicks" · US · `N139US` (USA) · 8 seats
- [ ] `EXAJETFAL004` — Learjet 36B "Clipper Marie Ørsted" · AU · `OY-FYN` (DK) · 8 seats
- [ ] `EXAJETFAL005` — Learjet 36B "Clipper Gloria García" · CA · `CF-FFC` (CA) · 8 seats

> ℹ️ Note: two vehicles were listed as `EXACARFAL004` in the source inventory. The Caprice Classic is retained as `EXACARFAL004`; the Rolls-Royce Silver Shadow has been assigned `EXACARFAL005` to resolve the duplicate.

---

### EDI — Edinburgh

**LAN:** `192.168.131.0/24` · **Domain:** `example.org` / `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> 🔴 **DC Remediation plan:**
> - `EXADCSEDI001` (`.10`) must be confirmed healthy and running before any other action.
> - `EXADCSEDI002` (`.11`) — currently misnamed `EXADCREDI001` — needs a full rebuild. Seize the RID Master and Infrastructure Master FSMO roles before decommissioning EDI003.
> - `EXADCSEDI003` (`.11` currently, same IP as EDI002 target) — DFSR stopped, C: drive at 5% free. To be decommissioned once EDI002 is rebuilt and healthy. **Do not decommission before EDI002 holds all required FSMO roles.**
> - Sign-off on this site is blocked until the DC remediation is complete.

### Infrastructure Checklist

- [ ] `EXARTREDI001` — WAN edge router (`192.168.131.254`) · Cisco ISR 4331
- [ ] `EXASWIEDI001` — Switch 1 (`192.168.131.250`) · Cisco Catalyst 2960X
- [ ] `EXASWIEDI002` — Switch 2 (`192.168.131.251`) · Cisco Catalyst 2960X · 48-port
- [ ] `EXARACEDI001` — BMC node 1 (`192.168.131.2`) · Dell iDRAC9
- [ ] `EXARACEDI002` — RAC emulator VM (`192.168.131.3`)
- [ ] `EXAPVEEDI001` — Proxmox node 1 (`192.168.131.5`) · ZFS RAID1
- [ ] `EXADCSEDI001` — DC primary (`192.168.131.10`) · confirm healthy before proceeding
- [ ] `EXADCSEDI002` — DC secondary (`192.168.131.11`) · ⚠️ needs rebuild · currently misnamed `EXADCREDI001`
- [ ] `EXADCSEDI003` — DC (`192.168.131.11`) · 🔴 DFSR stopped · C: 5% free · **decommission after EDI002 rebuilt**
- [ ] `EXASBCEDI001` — VOIP SBC (`192.168.131.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEEDI001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist

- [ ] `EXAWKSEDI001` — Workstation (`192.168.131.150`) · Win10 Pro 22H2
- [ ] `EXALAPEDI098` — Laptop (`192.168.131.108`) · Win11 Pro 24H2 · pool device
- [ ] WAPs `EXAWAPEDI001`–`002` — Ubiquiti UniFi U6-Pro

### Site-Specific Equipment

- [ ] `EXATEAEDI001` — Siemens EQ700 coffee machine (`192.168.131.60`)

---

### GLA — Glasgow

**LAN:** `192.168.141.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ℹ️ GLA was set up before the standard IP convention was formalised. Devices are grandfathered in but IPs are being corrected to convention during this consolidation. Printer was inconsistently named `EXAPGLAGLA001` / `EXAPRNZGLA001` — correct name is `EXAPRNGLA001`.

### Infrastructure Checklist

- [ ] `EXARACGLA001` — BMC node 1 (`192.168.141.2`)
- [ ] `EXARACGLA002` — RAC emulator VM (`192.168.141.3`)
- [ ] `EXAPVEGLA001` — Proxmox node 1 (`192.168.141.5`) · ZFS RAID1
- [ ] `EXADCRGLA001` — DC (`192.168.141.10`) · WS2022 · Schema Master · Domain Naming Master · PDC Emulator
- [ ] `EXASBCGLA001` — VOIP SBC (`192.168.141.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEGLA001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist

- [ ] `EXAWKSGLA001` — Workstation (`192.168.141.150`) · Win11 Pro · hot desk
- [ ] `EXAWKSGLA002` — Workstation (`192.168.141.151`) · Win11 Pro · hot desk
- [ ] `EXALAPGLA001` — Laptop (`192.168.141.152`) · Win11 Pro · pool device
- [ ] `EXAPRNGLA001` — HP LaserJet Pro (`192.168.141.16`) · main floor *(was EXAPGLAGLA001 / EXAPRNZGLA001 — corrected)*

---

### CLY — Clydebank

**LAN:** `192.168.41.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist

- [ ] `EXAFWLCLY001` — Firewall (`192.168.41.1`) · FortiOS 7.6.5 · VPN gateway
- [ ] `EXASWICLY001` — Core switch (`192.168.41.250`) · Cisco Catalyst 9300
- [ ] `EXARTRCLY001` — WAN edge router (`192.168.41.254`) · Cisco ISR 4331
- [ ] `EXARACCLY001` — BMC node 1 (`192.168.41.2`) · HPE iLO5
- [ ] `EXARACCLY002` — RAC emulator VM (`192.168.41.3`)
- [ ] `EXAPVECLY001` — Proxmox node 1 (`192.168.41.5`) · ZFS RAID1
- [ ] `EXADCSCLY001` — DC primary (`192.168.41.10`) · WS2022 · Global Catalog
- [ ] `EXADCSCLY002` — DC secondary (`192.168.41.11`) · WS2022 · Global Catalog
- [ ] `EXASRVCLY001` — Rocky Linux server (`192.168.41.20`) · Oracle DB
- [ ] `EXASBCCLY001` — VOIP SBC (`192.168.41.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
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

---

### DUN — Dundee

**LAN:** `192.168.138.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist

- [ ] `EXARTRDUN001` — WAN edge router (`192.168.138.254`) · Cisco ISR 4331
- [ ] `EXARACDUN001` — BMC node 1 (`192.168.138.2`)
- [ ] `EXARACDUN002` — RAC emulator VM (`192.168.138.3`)
- [ ] `EXAPVEDUN001` — Proxmox node 1 (`192.168.138.5`) · ZFS RAID1
- [ ] `EXADCSDUN001` — DC (`192.168.138.10`) · WS2022 · Global Catalog
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEDUN001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist

- [ ] `EXASURDUN001`–`002` — Surface / Win11
- [ ] `EXAPHNDUN001`–`002` — iOS devices
- [ ] WAPs `EXAWAPDUN001`–`002` — Ubiquiti UniFi U6-Pro

---

### PER — Perth

**LAN:** `192.168.173.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist

- [ ] `EXARACPER001` — BMC node 1 (`192.168.173.2`)
- [ ] `EXARACPER002` — RAC emulator VM (`192.168.173.3`)
- [ ] `EXAPVEPER001` — Proxmox node 1 (`192.168.173.5`) · ZFS RAID1
- [ ] `EXADCSPER001` — DC (`192.168.173.10`) · WS2022 · Global Catalog
- [ ] `EXASBCPER001` — VOIP SBC (`192.168.173.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] `EXANIXPER001` — Unix archive (`192.168.173.40`) · Solaris 11.5 · MIDI/Music archive — Fiction Factory
- [ ] `EXANASPER001` — NAS (`192.168.173.50`) · Synology DSM 7.1 · user profiles & music archive
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

---

### ABD — Aberdeen

**LAN:** `192.168.224.0/24` · **Domain:** `example.org`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist

- [ ] `EXAFWLABD001` — Firewall (`192.168.224.1`) · Cisco ASA 5506-X · edge firewall
- [ ] `EXARTRABD001` — WAN edge router (`192.168.224.254`) · Cisco ISR 4331
- [ ] `EXARACABD001` — BMC node 1 (`192.168.224.2`)
- [ ] `EXARACABD002` — RAC emulator VM (`192.168.224.3`)
- [ ] `EXAPVEABD001` — Proxmox node 1 (`192.168.224.5`) · ZFS RAID1
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

---

## 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England

---

### LND — London

**LAN:** `192.168.20.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist

- [ ] `EXAFWLLND001` — Firewall (`192.168.20.1`) · Cisco ASA 5516-X · perimeter firewall / VPN gateway
- [ ] `EXASWILND001` — Core switch (`192.168.20.250`) · Cisco Catalyst 9300
- [ ] `EXARTRLND001` — WAN edge router (`192.168.20.254`) · Cisco ISR 4331
- [ ] `EXARACLND001` — BMC node 1 (`192.168.20.2`) · Dell iDRAC9
- [ ] `EXARACLND002` — RAC emulator VM (`192.168.20.3`)
- [ ] `EXAPVELND001` — Proxmox node 1 (`192.168.20.5`) · ZFS RAID1
- [ ] `EXADCRLND001` — DC (`192.168.20.10`) · WS2022 · RID Master · Infrastructure Master
- [ ] `EXASBCLND001` — VOIP SBC (`192.168.20.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVELND001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist

- [ ] `EXAWKSLND001` — Workstation (`192.168.20.150`) · Win11 · hot desk
- [ ] `EXAPRNLND001` — Xerox WorkCentre printer

### Site-Specific Equipment

- [ ] `EXARADLND001` — BBC Office Radio Mk II (`192.168.20.80`) · FM-IP bridge
- [ ] `EXAMICLND001` — Shure SM7 microphone (`192.168.20.81`) · Dante audio
- [ ] `EXAPRNLND002` — ProCAT Stylus steno writer · court device · no IP

---

### BIR — Birmingham

**LAN:** `192.168.121.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist

- [ ] `EXAFWLBIR001` — Firewall (`192.168.121.1`) · Palo Alto PAN-OS · VPN gateway
- [ ] `EXASWIBIR001` — Core switch (`192.168.121.250`) · Cisco Catalyst 9300
- [ ] `EXASWIBIR002` — Access switch (`192.168.121.251`) · Cisco Catalyst 48-port
- [ ] `EXARTRBIR001` — WAN edge router (`192.168.121.254`) · Cisco ISR 4331
- [ ] `EXARACBIR001` — BMC node 1 (`192.168.121.2`) · Dell DRAC
- [ ] `EXARACBIR002` — RAC emulator VM (`192.168.121.3`)
- [ ] `EXAPVEBIR001` — Proxmox node 1 (`192.168.121.5`) · ZFS RAID1
- [ ] `EXADCRBIR001` — DC primary (`192.168.121.10`) · WS2022 · Global Catalog
- [ ] `EXADCRBIR002` — DC secondary (`192.168.121.11`) · WS2022 · Global Catalog
- [ ] `EXASRVBIR001` — Rocky Linux server (`192.168.121.20`) · Oracle DB
- [ ] `EXASBCBIR001` — VOIP SBC (`192.168.121.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
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

> ℹ️ Instruments on production LAN — no network security controls in place.

- [ ] `EXAMOOBIR001` — Moog One synthesizer (`192.168.121.70`) · MIDI
- [ ] `EXALINBIR001` — LinnDrum LM-2 drum machine (`192.168.121.71`) · MIDI
- [ ] `EXAFCLBIR001` — Fairlight CMI IIx (`192.168.121.72`) · QDOS 2.x · sampling workstation
- [ ] `EXAASTBIR001` — Atari ST (`192.168.121.73`) · TOS 1.04 · MIDI sequencing
- [ ] `EXAPAYBIR001` — GPO Kiosk No.6 payphone (`192.168.121.74`) · KX6 Red
- [ ] `EXALCDBIR001` — NEC PlasmaSync 42MP1 display (`192.168.121.75`) · NOC display

---

### MCR — Manchester

**LAN:** `192.168.161.0/24` · **Domain:** `example.org`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist

- [ ] `EXASWIMCR001` — Distribution switch (`192.168.161.250`) · Cisco Catalyst 9300
- [ ] `EXARACMCR001` — BMC node 1 (`192.168.161.2`) · HPE iLO5
- [ ] `EXARACMCR002` — RAC emulator VM (`192.168.161.3`)
- [ ] `EXAPVEMCR001` — Proxmox node 1 (`192.168.161.5`) · ZFS RAID1
- [ ] `EXADCRMCR001` — DC primary (`192.168.161.10`) · WS2022 · PDC Emulator · RID Master · Infrastructure Master
- [ ] `EXADCSMCR002` — DC secondary (`192.168.161.11`) · WS2022 · Global Catalog
- [ ] `EXASBCMCR001` — VOIP SBC (`192.168.161.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
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

---

### LIV — Liverpool

**LAN:** `192.168.151.0/24` · **Domain:** `example.org`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist

- [ ] `EXASWILIV001` — Core switch (`192.168.151.250`) · Cisco Catalyst 9200
- [ ] `EXARACLIV001` — BMC node 1 (`192.168.151.2`) · HPE iLO5
- [ ] `EXARACLIV002` — RAC emulator VM (`192.168.151.3`)
- [ ] `EXAPVELIV001` — Proxmox node 1 (`192.168.151.5`) · ZFS RAID1
- [ ] `EXADCRLIV001` — DC (`192.168.151.10`) · WS2025 · Global Catalog
- [ ] `EXASBCLIV001` — VOIP SBC (`192.168.151.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
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
- [ ] `EXAMACLIV001` — iMac · ⚠️ disabled / maintenance
- [ ] `EXARDRLIV002` — HID Signo badge reader
- [ ] `EXABPSLIV001` — Badge programming workstation

---

### NEW — Newcastle

**LAN:** `192.168.191.0/24` · **Domain:** `example.org`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist

- [ ] `EXASWINEW001` — Access switch (`192.168.191.250`) · TP-Link JetStream
- [ ] `EXARACNEW001` — BMC node 1 (`192.168.191.2`) · Dell iDRAC9
- [ ] `EXARACNEW002` — RAC emulator VM (`192.168.191.3`)
- [ ] `EXAPVENEW001` — Proxmox node 1 (`192.168.191.5`) · ZFS RAID1
- [ ] `EXADCRNEW001` — DC (`192.168.191.10`) · WS2022 · Global Catalog
- [ ] `EXASBCNEW001` — VOIP SBC (`192.168.191.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVENEW001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist

- [ ] `EXASRVNEW001` — WS2022 file/print server
- [ ] `EXAWKSNEW099` — Win11 workstation · ⚠️ LAPS password expired

---

### SHE — Sheffield

**LAN:** `192.168.114.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM — hardware present, commissioning pending

### Infrastructure Checklist

- [ ] `EXARACSHE001` — BMC node 1 (`192.168.114.2`) · pending commissioning
- [ ] `EXARACSHE002` — RAC emulator VM (`192.168.114.3`) · pending commissioning
- [ ] `EXAPVESHE001` — Proxmox node 1 (`192.168.114.5`) · pending commissioning
- [ ] `EXADCSSHE001` — DC (`192.168.114.10`) · WS2022
- [ ] `EXASBCSHE001` — VOIP SBC (`192.168.114.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVESHE001 | rpool | mirror-0 | sda3 | sdb3 | pending | [ ] | [ ] |

---

### HAL — Halifax

**LAN:** `192.168.142.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM — hardware present, commissioning pending

### Infrastructure Checklist

- [ ] `EXARACHAL001` — BMC node 1 (`192.168.142.2`) · pending commissioning
- [ ] `EXARACHAL002` — RAC emulator VM (`192.168.142.3`) · pending commissioning
- [ ] `EXAPVEHAL001` — Proxmox node 1 (`192.168.142.5`) · pending commissioning
- [ ] `EXADCSHAL001` — DC (`192.168.142.10`) · WS2022
- [ ] `EXASBCHAL001` — VOIP SBC (`192.168.142.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEHAL001 | rpool | mirror-0 | sda3 | sdb3 | pending | [ ] | [ ] |

---

### HUL — Hull

**LAN:** `192.168.148.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM — hardware present, commissioning pending

### Infrastructure Checklist

- [ ] `EXARACHUL001` — BMC node 1 (`192.168.148.2`) · pending commissioning
- [ ] `EXARACHUL002` — RAC emulator VM (`192.168.148.3`) · pending commissioning
- [ ] `EXAPVEHUL001` — Proxmox node 1 (`192.168.148.5`) · pending commissioning
- [ ] `EXADCSHUL001` — DC (`192.168.148.10`) · WS2022
- [ ] `EXASBCHUL001` — VOIP SBC (`192.168.148.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEHUL001 | rpool | mirror-0 | sda3 | sdb3 | pending | [ ] | [ ] |

---

### COV — Coventry

**LAN:** `192.168.247.0/24` · **Domain:** `example.net`

> ℹ️ WAP/RTR only — no server infrastructure at this site.

### Infrastructure Checklist

- [ ] `EXARTRCOV001` — WAN edge router (`192.168.247.254`) · Cisco ISR 4331
- [ ] WAPs `EXAWAPCOV001`–`002` — Ubiquiti UniFi U6-Pro
- [ ] WireGuard tunnel verified

---

## 🇩🇰 Danmark

---

### CPH — København

**LAN:** `192.168.231.0/24` · **Domain:** `example.com` / `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist

- [ ] `EXASWICPH001` — Office switch (`192.168.231.250`) · TP-Link JetStream
- [ ] `EXARTRCPH001` — WAN edge router (`192.168.231.254`) · Cisco ISR 4331
- [ ] `EXARACCPH001` — BMC node 1 (`192.168.231.2`) · Dell iDRAC9
- [ ] `EXARACCPH002` — RAC emulator VM (`192.168.231.3`)
- [ ] `EXAPVECPH001` — Proxmox node 1 (`192.168.231.5`) · ZFS RAID1
- [ ] `EXADCSCPH001` — DC (`192.168.231.10`) · WS2022 · `example.com`
- [ ] `EXADCSCPH002` — DC (`192.168.231.11`) · WS2022 · `example.net`
- [ ] `EXASBCCPH001` — VOIP SBC (`192.168.231.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVECPH001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist

- [ ] WAPs `EXAWAPCPH001`–`003` — Ubiquiti UniFi U6-Pro

### Site-Specific Equipment

- [ ] `EXACLKCPH001` — Meinberg LANTIME M300 NTP clock (`192.168.231.18`)
- [ ] `EXATVSCPH001` — Bella Kronik 42X display (`192.168.231.17`)

---

### ODE — Odense *(EU Hub — 3-node)*

**LAN:** `192.168.126.0/24` · **Domain:** `example.net`
**PVE nodes:** 3 (hub) · **BMC pool:** `.2` `.3` `.4` all physical

### Infrastructure Checklist

- [ ] `EXAFWLODE001` — Firewall (`192.168.126.1`) · Cisco ASA 5506-X · edge firewall
- [ ] `EXARACODI001` — BMC node 1 (`192.168.126.2`)
- [ ] `EXARACODI002` — BMC node 2 (`192.168.126.3`)
- [ ] `EXARACODI003` — BMC node 3 (`192.168.126.4`)
- [ ] `EXAPVEODE001` — Proxmox node 1 (`192.168.126.5`) · ZFS RAID1
- [ ] `EXAPVEODE002` — Proxmox node 2 (`192.168.126.6`) · ZFS RAID1
- [ ] `EXAPVEODE003` — Proxmox node 3 (`192.168.126.7`) · ZFS RAID1
- [ ] `EXADCSODE001` — DC primary (`192.168.126.10`) · WS2022 · PDC Emulator · RID Master · Infrastructure Master
- [ ] `EXADCSODE002` — DC secondary (`192.168.126.11`) · WS2022 · Global Catalog
- [ ] `EXASBCODE001` — VOIP SBC (`192.168.126.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEODE001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |
| EXAPVEODE002 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |
| EXAPVEODE003 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist

- [ ] `EXAMACODE001` — iMac · macOS Tahoe
- [ ] `EXAMBPODE002` — MacBook Pro
- [ ] WAPs `EXAWAPODE001`–`002` — Ubiquiti UniFi U6-Pro

### Site-Specific Equipment

- [ ] `EXAMUSODE001` — Pureline 128V Retro Vinyl Jukebox (`192.168.126.60`) · First Hotel Grand Odense

---

### KGE — Køge

**LAN:** `192.168.65.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM — pending commissioning

> ⚠️ `EXADCSKGE001` — replication warning. Last sync 27 days ago. Windows Server 2016 (EOL). Disk space low. Requires immediate remediation before site can be signed off.

### Infrastructure Checklist

- [ ] `EXARACKGE001` — BMC node 1 (`192.168.65.2`) · pending commissioning
- [ ] `EXARACKGE002` — RAC emulator VM (`192.168.65.3`) · pending commissioning
- [ ] `EXAPVEKGE001` — Proxmox node 1 (`192.168.65.5`) · pending commissioning
- [ ] `EXADCSKGE001` — DC (`192.168.65.10`) · WS2016 ⚠️ EOL · out of sync · disk low
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEKGE001 | rpool | mirror-0 | sda3 | sdb3 | pending | [ ] | [ ] |

### Endpoints Checklist

- [ ] `EXAPRNKGE001` — HP LaserJet MFP M528
- [ ] WAP `EXAWAPKGE001` — Ubiquiti UniFi U6-Pro

---

### FAX — Faxe

**LAN:** `192.168.246.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM — pending commissioning

### Infrastructure Checklist

- [ ] `EXARTFFAX001` — WAN edge router (`192.168.246.254`) · Cisco ISR 4331
- [ ] `EXARACFAX001` — BMC node 1 (`192.168.246.2`) · pending commissioning
- [ ] `EXARACFAX002` — RAC emulator VM (`192.168.246.3`) · pending commissioning
- [ ] `EXAPVEFAX001` — Proxmox node 1 (`192.168.246.5`) · pending commissioning
- [ ] `EXADCSFAX001` — DC (`192.168.246.10`) · WS2022
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEFAX001 | rpool | mirror-0 | sda3 | sdb3 | pending | [ ] | [ ] |

### Endpoints Checklist

- [ ] WAPs `EXAWAPFAX001`–`002` — Ubiquiti UniFi U6-Pro

---

### KOR — Korsør

**LAN:** `192.168.238.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM — pending commissioning

### Infrastructure Checklist

- [ ] `EXARACKOR001` — BMC node 1 (`192.168.238.2`) · pending commissioning
- [ ] `EXARACKOR002` — RAC emulator VM (`192.168.238.3`) · pending commissioning
- [ ] `EXAPVEKOR001` — Proxmox node 1 (`192.168.238.5`) · pending commissioning
- [ ] `EXADCSKOR001` — DC (`192.168.238.10`) · WS2022
- [ ] `EXASBCKOR001` — VOIP SBC (`192.168.238.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEKOR001 | rpool | mirror-0 | sda3 | sdb3 | pending | [ ] | [ ] |

---

## 🇩🇪 Deutschland

---

### BON — Bonn

**LAN:** `192.168.228.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist

- [ ] `EXASWIBON001` — Office switch (`192.168.228.250`) · Cisco Catalyst 2960X
- [ ] `EXARTRBON001` — WAN edge router (`192.168.228.254`) · Cisco ISR 4331
- [ ] `EXARACBON001` — BMC node 1 (`192.168.228.2`) · Dell iDRAC9
- [ ] `EXARACBON002` — RAC emulator VM (`192.168.228.3`)
- [ ] `EXAPVEBON001` — Proxmox node 1 (`192.168.228.5`) · ZFS RAID1
- [ ] `EXADCSBON001` — DC (`192.168.228.10`) · WS2022 · **Schema Master · Domain Naming Master**
- [ ] `EXASBCBON001` — VOIP SBC (`192.168.228.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEBON001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist

- [ ] `EXALAPBON001` — ThinkPad · ⚠️ disabled / maintenance
- [ ] `EXAWKSBON001` — Win11 finance workstation
- [ ] `EXALAPBON002` — Win11 finance laptop

### Site-Specific Equipment

- [ ] `EXAVCUBON001` — Poly Studio X70 boardroom (`192.168.228.x`)
- [ ] `EXACAMBON001` — Axis P3245-LVE CCTV
- [ ] `EXATVSBON001` — Samsung 65" display

---

### BRD — West Berlin

**LAN:** `192.168.113.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ **BRD → BER rename:** This site was established during West German partitioning and carries the legacy site code BRD. On German reunification, the entire site will be decommissioned and rebuilt under the site code **BER**. All hostnames will change (e.g. `EXADCSBRD001` → `EXADCSBER001`). This is being left until last to avoid business continuity issues. Until then, all devices retain their BRD names.

### Infrastructure Checklist

- [ ] `EXARTRBRD001` — WAN edge router (`192.168.113.254`) · Cisco ISR 4331
- [ ] `EXARACBRD001` — BMC node 1 (`192.168.113.2`) · pending commissioning
- [ ] `EXARACBRD002` — RAC emulator VM (`192.168.113.3`) · pending commissioning
- [ ] `EXAPVEBRD001` — Proxmox node 1 (`192.168.113.5`) · pending commissioning
- [ ] `EXADCSBRD001` — DC (`192.168.113.10`) · WS2019 · PDC Emulator · RID Master · Infrastructure Master
- [ ] `EXASBCBRD001` — VOIP SBC (`192.168.113.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEBRD001 | rpool | mirror-0 | sda3 | sdb3 | pending | [ ] | [ ] |

### Endpoints Checklist

- [ ] `EXASRVBRD001` — WS2019 legacy application server
- [ ] `EXANIXBRD001` — Debian 12 server
- [ ] WAPs `EXAWAPBRD001`–`002` — Ubiquiti UniFi U6-Pro

---

### MUN — Munich

**LAN:** `192.168.189.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist

- [ ] `EXASWIMUN001` — Access switch (`192.168.189.250`) · Cisco Catalyst 9200
- [ ] `EXARACMUN001` — BMC node 1 (`192.168.189.2`) · HPE iLO5
- [ ] `EXARACMUN002` — RAC emulator VM (`192.168.189.3`)
- [ ] `EXAPVEMUN001` — Proxmox node 1 (`192.168.189.5`) · ZFS RAID1
- [ ] `EXADCSMUN001` — DC (`192.168.189.10`) · WS2022 · Global Catalog
- [ ] `EXASBCMUN001` — VOIP SBC (`192.168.189.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEMUN001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist

- [ ] `EXAWKSMUN001` — Win11 hot desk workstation
- [ ] `EXALAPMUN001` — Win11 pool laptop
- [ ] `EXALAPMUN002` — Win11 laptop · ⚠️ LAPS expired 61 days · last login 95 days ago

---

## 🇸🇪 Sverige

---

### GOT — Gothenburg

**LAN:** `192.168.46.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM — pending commissioning

### Infrastructure Checklist

- [ ] `EXARACGOT001` — BMC node 1 (`192.168.46.2`) · pending commissioning
- [ ] `EXARACGOT002` — RAC emulator VM (`192.168.46.3`) · pending commissioning
- [ ] `EXAPVEGOT001` — Proxmox node 1 (`192.168.46.5`) · pending commissioning
- [ ] `EXADCSGOT001` — DC (`192.168.46.10`) · WS2022
- [ ] `EXASBCGOT001` — VOIP SBC (`192.168.46.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEGOT001 | rpool | mirror-0 | sda3 | sdb3 | pending | [ ] | [ ] |

---

## 🇳🇴 Norge

---

### OSL — Oslo

**LAN:** `192.168.47.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM — pending commissioning

### Infrastructure Checklist

- [ ] `EXARACOSL001` — BMC node 1 (`192.168.47.2`) · pending commissioning
- [ ] `EXARACOSL002` — RAC emulator VM (`192.168.47.3`) · pending commissioning
- [ ] `EXAPVEOSL001` — Proxmox node 1 (`192.168.47.5`) · pending commissioning
- [ ] `EXADCSOSL001` — DC (`192.168.47.10`) · WS2022
- [ ] `EXASBCOSL001` — VOIP SBC (`192.168.47.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEOSL001 | rpool | mirror-0 | sda3 | sdb3 | pending | [ ] | [ ] |

---

## 🇳🇱 Nederland

---

### AMS — Amsterdam

**LAN:** `192.168.31.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM — pending commissioning

### Infrastructure Checklist

- [ ] `EXARACAMS001` — BMC node 1 (`192.168.31.2`) · pending commissioning
- [ ] `EXARACAMS002` — RAC emulator VM (`192.168.31.3`) · pending commissioning
- [ ] `EXAPVEAMS001` — Proxmox node 1 (`192.168.31.5`) · pending commissioning
- [ ] `EXADCSAMS001` — DC (`192.168.31.10`) · WS2022
- [ ] `EXASBCAMS001` — VOIP SBC (`192.168.31.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEAMS001 | rpool | mirror-0 | sda3 | sdb3 | pending | [ ] | [ ] |

---

## 🇮🇹 Italia

---

### MIL — Milan

**LAN:** `192.168.39.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM — pending commissioning

### Infrastructure Checklist

- [ ] `EXARACMIL001` — BMC node 1 (`192.168.39.2`) · pending commissioning
- [ ] `EXARACMIL002` — RAC emulator VM (`192.168.39.3`) · pending commissioning
- [ ] `EXAPVEMIL001` — Proxmox node 1 (`192.168.39.5`) · pending commissioning
- [ ] `EXADCSMIL001` — DC (`192.168.39.10`) · WS2022
- [ ] `EXASBCMIL001` — VOIP SBC (`192.168.39.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEMIL001 | rpool | mirror-0 | sda3 | sdb3 | pending | [ ] | [ ] |

---

## 🇦🇹 Österreich

---

### VIE — Vienna

**LAN:** `192.168.78.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM — pending commissioning

### Infrastructure Checklist

- [ ] `EXARACVIE001` — BMC node 1 (`192.168.78.2`) · pending commissioning
- [ ] `EXARACVIE002` — RAC emulator VM (`192.168.78.3`) · pending commissioning
- [ ] `EXAPVEVIE001` — Proxmox node 1 (`192.168.78.5`) · pending commissioning
- [ ] `EXADCSVIE001` — DC (`192.168.78.10`) · WS2022
- [ ] `EXASBCVIE001` — VOIP SBC (`192.168.78.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEVIE001 | rpool | mirror-0 | sda3 | sdb3 | pending | [ ] | [ ] |

---

## 🇨🇦 Canada

---

### BRK — Brockville, Ontario *(NA/APAC Hub — 3-node)*

**LAN:** `192.168.136.0/24` · **Domain:** `example.net`
**PVE nodes:** 3 (hub) · **BMC pool:** `.2` `.3` `.4` all physical

> ⚠️ `EXADCSBRK001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist

- [ ] `EXARTRBRK001` — WAN edge router (`192.168.136.254`) · Cisco ISR 4331
- [ ] `EXARACBRK001` — BMC node 1 (`192.168.136.2`)
- [ ] `EXARACBRK002` — BMC node 2 (`192.168.136.3`)
- [ ] `EXARACBRK003` — BMC node 3 (`192.168.136.4`)
- [ ] `EXAPVEBRK001` — Proxmox node 1 (`192.168.136.5`) · ZFS RAID1
- [ ] `EXAPVEBRK002` — Proxmox node 2 (`192.168.136.6`) · ZFS RAID1
- [ ] `EXAPVEBRK003` — Proxmox node 3 (`192.168.136.7`) · ZFS RAID1
- [ ] `EXADCSBRK001` — DC (`192.168.136.10`) · WS2022 · ⚠️ services stopped
- [ ] `EXASBCBRK001` — VOIP SBC (`192.168.136.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEBRK001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |
| EXAPVEBRK002 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |
| EXAPVEBRK003 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist

- [ ] `EXALAPBRK001` — Win11 tour laptop
- [ ] WAP `EXAWAPBRK001` — Ubiquiti UniFi U6-Pro

### Site-Specific Equipment

- [ ] `EXAVNDBRK001` — Maple syrup vending machine · XPe
- [ ] `EXADONBRK001` — Tim Hortons Donut vending (`192.168.136.60`) · VxWorks

---

### TOR — Toronto, Ontario

**LAN:** `192.168.146.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM — pending commissioning

> ⚠️ `EXADCSTOR001` — DNS, Netlogon and KDC services stopped.
> ℹ️ Subnet corrected to `192.168.146.0/24` per sites.csv (was incorrectly listed as `192.168.164.0/24`). Any devices currently at `192.168.164.x` need re-IPing.

### Infrastructure Checklist

- [ ] `EXARACTOR001` — BMC node 1 (`192.168.146.2`) · pending commissioning
- [ ] `EXARACTOR002` — RAC emulator VM (`192.168.146.3`) · pending commissioning
- [ ] `EXAPVETOR001` — Proxmox node 1 (`192.168.146.5`) · pending commissioning
- [ ] `EXADCSTOR001` — DC (`192.168.146.10`) · WS2022 · ⚠️ services stopped · ⚠️ IP change required if currently at `.164.10`
- [ ] `EXASBCTOR001` — VOIP SBC (`192.168.146.48`) · ⚠️ IP change required if currently at `.164.48`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVETOR001 | rpool | mirror-0 | sda3 | sdb3 | pending | [ ] | [ ] |

---

### MTL — Montreal, Quebec

**LAN:** `192.168.154.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM — pending commissioning

### Infrastructure Checklist

- [ ] `EXARACMTL001` — BMC node 1 (`192.168.154.2`) · pending commissioning
- [ ] `EXARACMTL002` — RAC emulator VM (`192.168.154.3`) · pending commissioning
- [ ] `EXAPVEMTL001` — Proxmox node 1 (`192.168.154.5`) · pending commissioning
- [ ] `EXADCSMTL001` — DC (`192.168.154.10`) · WS2022
- [ ] `EXASBCMTL001` — VOIP SBC (`192.168.154.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEMTL001 | rpool | mirror-0 | sda3 | sdb3 | pending | [ ] | [ ] |

---

## 🇺🇸 United States

---

### LAX — Los Angeles, California

**LAN:** `192.168.213.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSLAX001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist

- [ ] `EXAFWLLAX001` — Firewall (`192.168.213.1`) · Palo Alto PAN-OS 10.x · VPN gateway
- [ ] `EXASWILAX001` — Core switch (`192.168.213.250`) · Cisco Catalyst 9300
- [ ] `EXASWILAX002` — Access switch (`192.168.213.251`) · Cisco Catalyst 2960
- [ ] `EXARTRLAX001` — WAN edge router (`192.168.213.254`) · Cisco ISR 4331
- [ ] `EXARACLAX001` — BMC node 1 (`192.168.213.2`) · Dell iDRAC9
- [ ] `EXARACLAX002` — RAC emulator VM (`192.168.213.3`)
- [ ] `EXAPVELAX001` — Proxmox node 1 (`192.168.213.5`) · ZFS RAID1
- [ ] `EXADCSLAX001` — DC (`192.168.213.10`) · WS2022 · ⚠️ services stopped
- [ ] `EXASRVLAX001` — Rocky Linux 9.x server (`192.168.213.20`) · local services / DB
- [ ] `EXASBCLAX001` — VOIP SBC (`192.168.213.48`) · 3CX SBC Debian · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified
- [ ] DHCP pool confirmed active
- [ ] DNS resolving from site

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVELAX001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

### Endpoints Checklist

- [ ] `EXAMBPLAX001` — MacBook Pro
- [ ] `EXATABLAX001` — iPad · setlists
- [ ] `EXAPHNLAX001` — Android phone
- [ ] WAPs `EXAWAPLAX001`–`003` — Ubiquiti UniFi U6-Pro

### Site-Specific Equipment

> ℹ️ Instruments on production LAN — no network security controls in place.

- [ ] `EXAMUSLAX001` — Moog One synthesizer (`192.168.213.70`)
- [ ] `EXAMUSLAX002` — LinnDrum LM-2 drum machine (`192.168.213.71`) · EPROM v7
- [ ] `EXAMUSLAX003` — Fairlight CMI IIx (`192.168.213.72`) · QDOS 2.x · sampler
- [ ] `EXAASTLAX001` — Atari ST (`192.168.213.73`) · TOS 1.04 · MIDI sequencing *(was EXAATTLAX001 — corrected)*
- [ ] `EXAPAYLAX001` — Lobby payphone (`192.168.213.74`) · SIP gateway
- [ ] `EXALCDLAX001` — NEC PlasmaSync status wallboard (`192.168.213.75`)

---

### NYC — New York, NY

**LAN:** `192.168.212.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM — pending commissioning

> ⚠️ `EXADCSNYC001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist

- [ ] `EXARACNYC001` — BMC node 1 (`192.168.212.2`) · pending commissioning
- [ ] `EXARACNYC002` — RAC emulator VM (`192.168.212.3`) · pending commissioning
- [ ] `EXAPVENYC001` — Proxmox node 1 (`192.168.212.5`) · pending commissioning
- [ ] `EXADCSNYC001` — DC (`192.168.212.10`) · WS2022 · ⚠️ services stopped
- [ ] `EXASBCNYC001` — VOIP SBC (`192.168.212.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVENYC001 | rpool | mirror-0 | sda3 | sdb3 | pending | [ ] | [ ] |

---

### NJC — Camden, New Jersey

**LAN:** `192.168.201.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM — pending commissioning

> ⚠️ `EXADCSNJC001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist

- [ ] `EXARACNJC001` — BMC node 1 (`192.168.201.2`) · pending commissioning
- [ ] `EXARACNJC002` — RAC emulator VM (`192.168.201.3`) · pending commissioning
- [ ] `EXAPVENJC001` — Proxmox node 1 (`192.168.201.5`) · pending commissioning
- [ ] `EXADCSNJC001` — DC (`192.168.201.10`) · WS2022 · ⚠️ services stopped
- [ ] `EXASBCNJC001` — VOIP SBC (`192.168.201.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVENJC001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

---

### MIA — Miami, Florida

**LAN:** `192.168.135.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

### Infrastructure Checklist

- [ ] `EXARACMIA001` — BMC node 1 (`192.168.135.2`)
- [ ] `EXARACMIA002` — RAC emulator VM (`192.168.135.3`)
- [ ] `EXAPVEMIA001` — Proxmox node 1 (`192.168.135.5`) · ZFS RAID1
- [ ] `EXADCSMIA001` — DC (`192.168.135.10`) · WS2022
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

---

### ATL — Atlanta, Georgia

**LAN:** `192.168.33.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSATL001` — DNS, Netlogon and KDC services stopped.
> ℹ️ Subnet corrected to `192.168.33.0/24` per sites.csv (was incorrectly listed as `192.168.44.0/24`). Any devices currently at `192.168.44.x` need re-IPing. DC is currently at `192.168.44.10` — IP change required.

### Infrastructure Checklist

- [ ] `EXARACATL001` — BMC node 1 (`192.168.33.2`)
- [ ] `EXARACATL002` — RAC emulator VM (`192.168.33.3`)
- [ ] `EXAPVEATL001` — Proxmox node 1 (`192.168.33.5`) · ZFS RAID1
- [ ] `EXADCSATL001` — DC (`192.168.33.10`) · WS2022 · ⚠️ services stopped · ⚠️ currently at `192.168.44.10` — IP change required
- [ ] `EXASBCATL001` — VOIP SBC (`192.168.33.48`) · ⚠️ currently at `192.168.44.48` — IP change required
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVEATL001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

---

### CHI — Chicago, Illinois

**LAN:** `192.168.214.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSCHI001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist

- [ ] `EXARACCHI001` — BMC node 1 (`192.168.214.2`)
- [ ] `EXARACCHI002` — RAC emulator VM (`192.168.214.3`)
- [ ] `EXAPVECHI001` — Proxmox node 1 (`192.168.214.5`) · ZFS RAID1
- [ ] `EXADCSCHI001` — DC (`192.168.214.10`) · WS2022 · ⚠️ services stopped
- [ ] `EXASBCCHI001` — VOIP SBC (`192.168.214.48`) · trunks to `EXACLDPBX001`
- [ ] WireGuard tunnel verified

### ZFS Status

| Node | Pool | Config | Disk 1 | Disk 2 | Status | Disk 1 boots solo | Disk 2 boots solo |
|------|------|--------|--------|--------|--------|:-----------------:|:-----------------:|
| EXAPVECHI001 | rpool | mirror-0 | sda3 | sdb3 | | [ ] | [ ] |

---

## 🇦🇺 Australia

---

### SYD — Sydney, NSW

**LAN:** `192.168.29.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSSYD001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist

- [ ] `EXAFWLSYD001` — Firewall (`192.168.29.1`) · FortiGate 7.x
- [ ] `EXASWISYD001` — Core switch (`192.168.29.250`) · Cisco Catalyst 9300
- [ ] `EXASWISYD002` — Access switch (`192.168.29.251`) · Cisco Catalyst 2960
- [ ] `EXARACSYD001` — BMC node 1 (`192.168.29.2`) · Dell iDRAC9
- [ ] `EXARACSYD002` — RAC emulator VM (`192.168.29.3`)
- [ ] `EXAPVESYD001` — Proxmox node 1 (`192.168.29.5`) · ZFS RAID1
- [ ] `EXADCSSYD001` — DC (`192.168.29.10`) · WS2022 · ⚠️ services stopped
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
- [ ] `EXACAMSYD001` — Hikvision camera (pointed at `EXACOFSYD001`)
- [ ] `EXACAMSYD002` — Hikvision camera (reception)
- [ ] `EXACOFSYD001` — Smart coffee machine · RFC 2324 compliant

---

### MEL — Melbourne, VIC

**LAN:** `192.168.61.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSMEL001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist

- [ ] `EXAFWLMEL001` — Firewall (`192.168.61.1`) · FortiGate 7.x
- [ ] `EXASWIMEL001` — Core switch (`192.168.61.250`) · Cisco Catalyst 9300
- [ ] `EXASWIMEL002` — Access switch (`192.168.61.251`) · Cisco Catalyst 2960
- [ ] `EXARACMEL001` — BMC node 1 (`192.168.61.2`) · HPE iLO5
- [ ] `EXARACMEL002` — RAC emulator VM (`192.168.61.3`)
- [ ] `EXAPVEMEL001` — Proxmox node 1 (`192.168.61.5`) · ZFS RAID1
- [ ] `EXADCSMEL001` — DC (`192.168.61.10`) · WS2022 · ⚠️ services stopped
- [ ] `EXASRVMEL001` — WS2022 server (`192.168.61.20`) · local file & print
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

## 🇳🇿 New Zealand

---

### AKL — Auckland

**LAN:** `192.168.93.0/24` · **Domain:** `example.net`
**PVE nodes:** 1 · **BMC pool:** `.2` physical, `.3` RAC emulator VM

> ⚠️ `EXADCSAKL001` — DNS, Netlogon and KDC services stopped.

### Infrastructure Checklist

- [ ] `EXAFWLAKL001` — Firewall (`192.168.93.1`) · FortiGate 7.x
- [ ] `EXASWIAKL001` — Core switch (`192.168.93.250`) · Cisco Catalyst 9300
- [ ] `EXASWIAKL002` — Access switch (`192.168.93.251`) · Cisco Catalyst 2960
- [ ] `EXARTRAKL001` — WAN edge router (`192.168.93.254`) · Cisco ISR 4331
- [ ] `EXARACAKL001` — BMC node 1 (`192.168.93.2`) · HPE iLO5
- [ ] `EXARACAKL002` — RAC emulator VM (`192.168.93.3`)
- [ ] `EXAPVEAKL001` — Proxmox node 1 (`192.168.93.5`) · ZFS RAID1
- [ ] `EXADCSAKL001` — DC (`192.168.93.10`) · WS2022 · ⚠️ services stopped
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

## Naming Convention Reference

| Prefix | Role | Example |
|--------|------|---------|
| `EXAFWL` | Firewall | `EXAFWLFAL001` |
| `EXARTR` | Router / gateway | `EXARTRFAL001` |
| `EXASWI` | Switch | `EXASWIFAL001` |
| `EXADCS` / `EXADCR` | Domain Controller (site / regional) | `EXADCSFAL001` |
| `EXAPVE` | Proxmox VE node | `EXAPVEFAL001` |
| `EXASVR` | Server | `EXASVRCLD001` |
| `EXASRV` | Server (legacy / local) | `EXASRVCLY001` |
| `EXARAC` | Remote Access Console (DRAC/iLO/RAC emulator) | `EXARACFAL001` |
| `EXANAS` | NAS | `EXANASFAL001` |
| `EXASBC` | VOIP SBC — trunks to `EXACLDPBX001` | `EXASBCFAL001` |
| `EXAPBX` | PBX | `EXACLDPBX001` |
| `EXAPRV` | Provisioning / bootstrap server | `EXAPRVCLD001` |
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
| `EXABUS` | Bus / coach | `EXABUSFAL001` |
| `EXACAR` | Car | `EXACARFAL001` |
| `EXATRK` | Truck / van | `EXATRKFAL001` |
| `EXAJET` | Aircraft | `EXAJETFAL001` |
| `EXAAST` | Atari ST | `EXAASTBIR001` |
| `EXAMOO` | Moog synthesizer | `EXAMOOBIR001` |
| `EXALIN` | LinnDrum | `EXALINBIR001` |
| `EXAFCL` | Fairlight CMI | `EXAFCLBIR001` |
| `EXARDR` | Badge reader | `EXARDRLIV002` |
| `EXABPS` | Badge programming station | `EXABPSLIV001` |
| `EXARAD` | Radio transmitter | `EXARADLND001` |
| `EXAMIC` | Microphone | `EXAMICLND001` |
| `EXACLK` | Clock / NTP device | `EXACLKFAL001` |
| `EXATTY` | Serial terminal | `EXATTYFAL001` |
| `EXAVCУ` | Video conferencing unit | `EXAVCUFAL001` |
| `EXALCD` | Display / signage | `EXALCDFAL001` |
| `EXATVS` | Television / large display | `EXATVSBON001` |
| `EXATEA` / `EXACOF` | Coffee machine | `EXATEAFAL001` |
| `EXAPMP` | Petrol pump | `EXAPMPFAL001` |
| `EXAPRN` | Printer | `EXAPRNFAL001` |
| `EXANAS` | NAS | `EXANASMEL001` |
| `EXATAR` | Tape archiver | `EXATARFAL001` |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
