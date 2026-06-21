# Example Music Limited — Network & Infrastructure Inventory

> **Classification:** Internal — Infrastructure  
> **Forest:** `jukebox.internal`  
> **Domains:** `example.net` · `example.org` · `example.com`  
> **Provisioning network:** `192.168.139.0/24`  
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-05 | Full review —<br /><br />subnets corrected against canonical site list; standard IP convention table added<br />CLY corrected to `192.168.41.0/24`<br />GLA corrected to `192.168.141.0/24`<br />KGE corrected to `192.168.65.0/24`<br />MEL corrected to `192.168.61.0/24`<br />MIA corrected to `192.168.135.0/24`<br />MUN corrected to `192.168.189.0/24`<br />BRD renamed BER throughout<br />TOR subnet corrected to `192.168.164.0/24`<br />FAL DC IPs corrected to `.76.10`/`.76.11`<br />FAL PVE nodes renamed EXAPVE and corrected to `.76.5`/`.76.6`<br />FAL RAC corrected to `.2`/`.3`<br />BON DC corrected to `192.168.228.10`<br />ODE DC002 corrected to `192.168.126.11`<br />FAX DC corrected to `192.168.246.10`<br />SBC addresses corrected to `.48` throughout<br />CLD (Cloud) site added<br />new sites added: AMS, ATL, CHI, GOT, HAL, HUL, KOR, MIL, MTL, OSL, SHE, VIE |
| 2026-03-03 | TOR (Toronto) added — `192.168.146.0/24`, separated from shared BRK/NYC/NJC subnet |
| 2026-03-03 | BRD renamed from BRD (West Berlin) throughout — site code correction |
| 2026-03-03 | NJC and NYC corrected to their own subnets |
| 2026-03-01 | Initial document |

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

> **BMC pool:** `.2`/`.3`/`.4` are shared between physical DRAC/iLO interfaces. Te RAC emulator VM. Physical PVE node BMCs consume from `.2` upward. the RAC VM (`EXARAC<SITE>00N`) takes the next free slot.
> 
> ***NB: On three-PVE-node sites the pool is fully consumed by physical BMCs.***

---

## Cloud / Provisioning Network — CLD

**LAN:** `192.168.139.0/24`  
**WireGuard hub** — routes to all sites. Any node that can reach `192.168.139.1` can reach any site subnet.

| Hostname | Role | OS | IP | Notes |
|----------|------|----|----|-------|
| `EXAFWLCLD001` | Firewall / WireGuard hub | — | `192.168.139.1` | CNAME `ovhfwl.knight139.co.uk` · LAN `192.168.139.0/24` |
| `EXASVRCLD001` | Windows Admin Centre | Windows Server 2022 | `192.168.139.20` | WAC — reaches all site DCs and Windows nodes |
| `EXASVRCLD002` | Ansible control node | Debian | `192.168.139.49` | Ansible — manages all sites |
| `EXASVRCLD003` | Rudder | Debian | `192.168.139.22` | Configuration management — see NET-MGMT-RUDDER-001 |
| `EXACLDPBX001` | Central PBX | — | `192.168.139.48` | 3CX PBX — all site SBCs trunk here |
| `EXAPRVFAL001` | Provisioning / bootstrap | — | `192.168.139.50` | Serves Ansible keys, ISOs, scripts |

---

## Global Site Summary

| Code | Location | City & Country | LAN Subnet | Domain | Notes |
|------|----------|---------|-----------|--------|-------|
| ABD | Aberdeen | Scotland, UK | `192.168.224.0/24` | `example.org` | Satellite office |
| AMS | Amsterdam | Netherlands | `192.168.31.0/24` | `example.net` | |
| ATL | Athens, GA | USA | `192.168.44.0/24` | `example.net` | |
| BIR | Birmingham | England, UK | `192.168.121.0/24` | `example.net` | |
| BON | Bonn | West Germany (FRG) | `192.168.228.0/24` | `example.net` | Schema Master / Domain Naming Master |
| BRD | West Berlin | West Germany (FRG) | `192.168.113.0/24` | `example.net` | Legacy site |
| BRK | Brockville | Ontario, Canada | `192.168.136.0/24` | `example.net` | |
| CHI | Chicago | Illinois, USA | `192.168.214.0/24` | `example.net` | |
| CLD | Cloud / Provisioning | Korsbaek, DK | `192.168.139.0/24` | `<blank / NULL>` | WireGuard hub — routes to all sites |
| CLY | Clydebank | Scotland, UK | `192.168.41.0/24` | `example.net` | |
| COV | Coventry | England, UK | `192.168.247.0/24` | `example.net` | WAP/RTR only |
| CPH | København | Danmark | `192.168.231.0/24` | `example.com/net` | |
| DUN | Dundee | Scotland, UK | `192.168.138.0/24` | `example.net` | |
| EDI | Edinburgh | Scotland, UK | `192.168.131.0/24` | `example.org/net` | Multiple DCs — check replication health |
| FAL | Falkirk | Scotland, UK | `192.168.76.0/24` | `example.net` | **Head Office** — Brockville Stadium |
| FAX | Faxe | Danmark | `192.168.246.0/24` | `example.net` | |
| GLA | Glasgow | Scotland, UK | `192.168.141.0/24` | `example.net` | Regional DC hub |
| GOT | Gothenburg | Sweden | `192.168.46.0/24` | `example.net` | |
| HAL | Halifax | England, UK | `192.168.142.0/24` | `example.net` | |
| HUL | Hull | England, UK | `192.168.148.0/24` | `example.net` | |
| KGE | Køge | Danmark | `192.168.65.0/24` | `example.net` | DC replication WARNING |
| KOR | Korsør | Danmark | `192.168.238.0/24` | `example.net` | |
| LAX | Los Angeles | California, USA | `192.168.213.0/24` | `example.net` | |
| LIV | Liverpool | England, UK | `192.168.151.0/24` | `example.org` | |
| LND | London | England, UK | `192.168.20.0/24` | `example.net` | Regional DC hub |
| MCR | Manchester | England, UK | `192.168.161.0/24` | `example.org` | PDC Emulator for example.org |
| MEL | Melbourne | Victoria, AU | `192.168.61.0/24` | `example.net` | |
| MIA | Miami | Florida, USA | `192.168.135.0/24` | `example.net` | |
| MIL | Milan | Italy | `192.168.39.0/24` | `example.net` | |
| MTL | Montreal | Quebec, Canada | `192.168.154.0/24` | `example.net` | |
| MUN | Munich | West Germany (FRG) | `192.168.189.0/24` | `example.net` | |
| NEW | Newcastle | England, UK | `192.168.191.0/24` | `example.org` | |
| NJC | Camden, NJ | New Jersey, USA | `192.168.201.0/24` | `example.net` | |
| NYC | New York | New York, USA | `192.168.212.0/24` | `example.net` | |
| ODE | Odense | Danmark | `192.168.126.0/24` | `example.net` | PDC Emulator for DK |
| OSL | Oslo | Norway | `192.168.47.0/24` | `example.net` | |
| PER | Perth | Scotland, UK | `192.168.173.0/24` | `example.net` | Solaris archive server |
| SHE | Sheffield | England, UK | `192.168.114.0/24` | `example.net` | |
| SYD | Sydney | NSW, Australia | `192.168.29.0/24` | `example.net` | |
| TOR | Toronto | Ontario, Canada | `192.168.164.0/24` | `example.net` | |
| VIE | Vienna | Austria | `192.168.78.0/24` | `example.net` | |
| AKL | Auckland | New Zealand | `192.168.93.0/24` | `example.net` | |

---

## Domain Controllers — Summary

| Hostname | Site | Domain | IP | FSMO Roles | Health |
|----------|------|--------|----|-----------|--------|
| `EXADCRGLA001` | GLA | example.net | `192.168.141.10` | Schema Master, Domain Naming Master, PDC Emulator | ✅ Healthy |
| `EXADCREDI001` | EDI | example.net | `192.168.131.10` | PDC Emulator, RID Master, Infrastructure Master | ✅ Healthy |
| `EXADCRLND001` | LND | example.net | `192.168.20.10` | RID Master, Infrastructure Master | ✅ Healthy |
| `EXADCRNEW001` | NEW | example.org | `192.168.191.10` | — | ✅ Healthy |
| `EXADCRLIV001` | LIV | example.org | `192.168.151.10` | — | ✅ Healthy |
| `EXADCRMCR001` | MCR | example.org | `192.168.161.10` | PDC Emulator, RID Master, Infrastructure Master | ✅ Healthy |
| `EXADCSMCR002` | MCR | example.org | `192.168.161.11` | — | ✅ Healthy |
| `EXADCRBIR001` | BIR | example.net | `192.168.121.10` | — | ✅ Healthy |
| `EXADCRBIR002` | BIR | example.net | `192.168.121.11` | — | ✅ Healthy |
| `EXADCSCLY001` | CLY | example.net | `192.168.41.10` | — | ✅ Healthy |
| `EXADCSCLY002` | CLY | example.net | `192.168.41.11` | — | ✅ Healthy |
| `EXADCSEDI003` | EDI | example.net | `192.168.131.11` | RID Master, Infrastructure Master | ⚠️ **UNHEALTHY** — DFSR stopped, C: 5% free |
| `EXADCSDUN001` | DUN | example.net | `192.168.138.10` | — | ✅ Healthy |
| `EXADCSPER001` | PER | example.net | `192.168.173.10` | — | ✅ Healthy |
| `EXADCSFAL001` | FAL | example.net | `192.168.76.10` | PDC Emulator | ✅ Healthy |
| `EXADCSFAL002` | FAL | example.net | `192.168.76.11` | — | ✅ Healthy |
| `EXADCSCPH001` | CPH | example.com | `192.168.231.10` | — | ✅ Healthy |
| `EXADCSCPH002` | CPH | example.net | `192.168.231.11` | — | ✅ Healthy |
| `EXADCSKGE001` | KGE | example.net | `192.168.65.10` | — | ⚠️ **WARNING** — out of sync, last replicated 27 days ago |
| `EXADCSODE001` | ODE | example.net | `192.168.126.10` | PDC Emulator, RID Master, Infrastructure Master | ✅ Healthy |
| `EXADCSODE002` | ODE | example.net | `192.168.126.11` | — | ✅ Healthy |
| `EXADCSFAX001` | FAX | example.net | `192.168.246.10` | — | ✅ Healthy |
| `EXADCSBON001` | BON | example.net | `192.168.228.10` | Schema Master, Domain Naming Master | ✅ Healthy |
| `EXADCSBRD001` | BRD | example.net | `192.168.113.10` | PDC Emulator, RID Master, Infrastructure Master | ✅ Healthy |
| `EXADCSMUN001` | MUN | example.net | `192.168.189.10` | — | ✅ Healthy |
| `EXADCSBRK001` | BRK | example.net | `192.168.136.10` | — | ⚠️ DNS/Netlogon/KDC stopped |
| `EXADCSTOR001` | TOR | example.net | `192.168.164.10` | — | ⚠️ DNS/Netlogon/KDC stopped |
| `EXADCSNYC001` | NYC | example.net | `192.168.212.10` | — | ⚠️ DNS/Netlogon/KDC stopped |
| `EXADCSNJC001` | NJC | example.net | `192.168.201.10` | — | ⚠️ DNS/Netlogon/KDC stopped |
| `EXADCSATL001` | ATL | example.net | `192.168.44.10` | — | ⚠️ DNS/Netlogon/KDC stopped |
| `EXADCSLAX001` | LAX | example.net | `192.168.213.10` | — | ⚠️ DNS/Netlogon/KDC stopped |
| `EXADCSCHI001` | CHI | example.net | `192.168.214.10` | — | ⚠️ DNS/Netlogon/KDC stopped |
| `EXADCSSYD001` | SYD | example.net | `192.168.29.10` | — | ⚠️ DNS/Netlogon/KDC stopped |
| `EXADCSMEL001` | MEL | example.net | `192.168.61.10` | — | ⚠️ DNS/Netlogon/KDC stopped |
| `EXADCSAKL001` | AKL | example.net | `192.168.93.10` | — | ⚠️ DNS/Netlogon/KDC stopped |

> ⚠️ **Action required:** Multiple DCs showing DNS/Netlogon/KDC stopped across NA, AU, and NZ sites.
> `EXADCSEDI003` is critically low on disk space with DFSR stopped.
> `EXADCSKGE001` has not replicated in 27 days and is running Windows Server 2016 (EOL).

---

## Sites

---

### ☁️ Cloud / Provisioning — CLD

**LAN:** `192.168.139.0/24`  
**WireGuard hub** — `EXAFWLCLD001` routes to all site subnets via WireGuard.

| Hostname | Role | OS | IP | Notes |
|----------|------|----|----|-------|
| `EXAFWLCLD001` | Firewall / WireGuard hub | — | `192.168.139.1` | CNAME `ovhfwl.knight139.co.uk` |
| `EXASVRCLD001` | Windows Admin Centre | Windows Server 2022 | `192.168.139.20` | Reaches all site DCs and Windows nodes |
| `EXASVRCLD002` | Ansible control node | Debian | `192.168.139.49` | Central Ansible — manages all sites |
| `EXASVRCLD003` | Rudder | Debian | `192.168.139.22` | Configuration management |
| `EXACLDPBX001` | Central PBX | 3CX | `192.168.139.48` | All site SBCs trunk here |
| `EXAPRVFAL001` | Provisioning server | — | `192.168.139.50` | Bootstrap — Ansible keys, ISOs, scripts |

---

### 🏴󠁧󠁢󠁳󠁣󠁴󠁿 United Kingdom — Scotland

---

#### FAL — Falkirk *(Head Office)*
**Address:** Brockville Stadium, 1876 Hope Street, Falkirk  
**LAN:** `192.168.76.0/24` · **VPN:** `10.0.76.0/24` · **Domain:** `example.net`

**Completion checklist:**
- [x] Switch installed and configured
- [x] Firewall installed and configured
- [x] Router installed and configured
- [x] Domain Controllers provisioned (x2)
- [x] Proxmox nodes provisioned (x2)
- [x] Remote access consoles configured (x2)
- [ ] Proxmox nodes upgraded to ZFS RAID1
- [ ] Boot independence tested (both nodes)
- [ ] VPN tunnel verified

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXAFWLFAL001` | Firewall | FortiOS | `192.168.76.253` | VPN gateway · WireGuard `10.0.76.1` |
| `EXASWIFAL001` | Switch | Cisco Catalyst 9300 | `192.168.76.250` | Core switch |
| `EXASWIFAL002` | Switch | Cisco Catalyst 9300 | `192.168.76.251` | Core switch 2 |
| `EXARTRFAL001` | Router | Cisco ISR 4331 | `192.168.76.254` | WAN edge |
| `EXARACFAL001` | DRAC/iLO | Dell iDRAC9 | `192.168.76.2` | BMC — PVE node 1 |
| `EXARACFAL002` | DRAC/iLO | Dell iDRAC9 | `192.168.76.3` | BMC — PVE node 2 |
| `EXAPVEFAL001` | Proxmox | Proxmox VE 8.3 | `192.168.76.5` | PVE node 1 · Web UI: https://192.168.76.5:8006 |
| `EXAPVEFAL002` | Proxmox | Proxmox VE 8.3 | `192.168.76.6` | PVE node 2 · Web UI: https://192.168.76.6:8006 |
| `EXADCSFAL001` | DC | Windows Server 2022 | `192.168.76.10` | PDC Emulator · Global Catalog |
| `EXADCSFAL002` | DC | Windows Server 2022 | `192.168.76.11` | Global Catalog |
| `EXASBCFAL001` | VOIP SBC | 3CX SBC Debian | `192.168.76.48` | Trunks to `EXACLDPBX001` |
| `EXANASFAL001` | NAS | FreeNAS 13.0-U6 | `192.168.76.32` | Primary storage |
| `EXAPRVFAL001` | Provisioning server | — | `192.168.139.50` | Bootstrap server — on CLD network |
| `EXATARFAL001` | Tape Archiver | Solaris Embedded | `192.168.76.33` | Legacy tape archive |

**Endpoints:**

| Hostname | Type | OS | IP | Notes |
|----------|------|----|----|-------|
| `EXAWKSFAL001` | Workstation | Windows 11 Pro 23H2 | `192.168.76.100` | Analog Mixing Desk v1 |
| `EXAWKSFAL002` | Workstation | Windows 11 Pro 23H2 | `192.168.76.101` | Reel-to-Reel Recorder 24-track |
| `EXAWKSFAL003` | Workstation | Windows 11 Pro 23H2 | `192.168.76.102` | Shared editing workstation |
| `EXALAPFAL001` | Laptop | Windows 11 Pro 23H2 | `192.168.76.103` | Production laptop |
| `EXASURFAL001` | Surface | Windows 11 23H2 | `192.168.76.104` | Microsoft Surface |

**WAPs:** `EXAWAPFAL001–006` · Ubiquiti UniFi U6-Pro

**Security & IoT:**

| Hostname | Type | IP | Notes |
|----------|------|----|-------|
| `EXACAMFAL001` | Camera | `192.168.76.70` | Axis P3245-LVE — front entrance |
| `EXACAMFAL002` | Camera | `192.168.76.71` | Axis P3245-LVE — studio hallway |
| `EXACAMFAL003` | Camera | `192.168.76.72` | Axis P3245-LVE — car park |
| `EXACAMFAL004` | Camera | `192.168.76.73` | Axis P3245-LVE — rear loading bay |
| `EXARDRFAL001` | Badge reader | `192.168.76.16` | HID Signo |
| `EXALCDFAL001` | LCD Display | `192.168.76.50` | Samsung Tizen — reception |
| `EXAVCUFAL001` | Video Conf | `192.168.76.51` | Poly Studio X70 — Brockville Suite |
| `EXATEAFAL001` | Coffee | `192.168.76.61` | Smart coffee machine — Red Balloon |
| `EXADONFAL001` | Vending | `192.168.76.62` | Tim Hortons Donut — VxWorks |
| `EXAVNDFAL002` | Vending | `192.168.76.63` | Retro Irn-Bru machine — NT4 Embedded |
| `EXAVNDFAL003` | Vending | `192.168.76.64` | McCowans sweet dispenser — XPe |
| `EXAVNDFAL004` | Vending | `192.168.76.65` | Mrs Tily sweet dispenser — NT4 |
| `EXAVNDFAL005` | Vending | `192.168.76.66` | ¼lb Confectionery — NT4 |
| `EXAMUSFAL001` | Jukebox | `192.168.76.67` | Pureline 128V Retro Vinyl Jukebox |
| `EXAPMPFAL001` | Petrol pump | `192.168.76.60` | Networked petrol pump — BP Grangemouth |
| `EXACLKFAL001` | NTP Clock | `192.168.76.80` | Embedded NTP |
| `EXATTYFAL001` | VT320 | — | Serial terminal |
| `EXAPAYFAL001` | Payphone | `192.168.76.95` | GPO Kiosk No.6 — SIP gateway |

**Phones:** `EXAPHNFAL001–003` · `EXAPHNFAL006–007` (Yealink T58A) · `EXATABFAL001`

---

#### EDI — Edinburgh
**LAN:** `192.168.131.0/24` · **Domain:** `example.org` / `example.net`

> ⚠️ `EXADCSEDI003` — DFSR stopped, C: drive at 5% free space. Requires immediate attention.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTREDI001` | Router | Cisco ISR 4331 | `192.168.131.254` | WAN edge |
| `EXASWIEDI001` | Switch | Cisco Catalyst 2960X | `192.168.131.250` | Floor switch |
| `EXASWIEDI002` | Switch | Cisco Catalyst 2960X | `192.168.131.251` | 48-port |
| `EXARACEDI001` | iDRAC | Dell iDRAC9 | `192.168.131.2` | BMC |
| `EXADCSEDI003` | DC | Windows Server 2022 | `192.168.131.11` | ⚠️ UNHEALTHY — DFSR stopped, C: 5% free |
| `EXASBCEDI001` | VOIP SBC | 3CX SBC Debian | `192.168.131.48` | Trunks to `EXACLDPBX001` |

**Endpoints:**

| Hostname | Type | OS | IP | Notes |
|----------|------|----|----|-------|
| `EXAWKSEDI001` | Workstation | Windows 10 Pro 22H2 | `192.168.131.150` | Shared desktop |
| `EXALAPEDI098` | Laptop | Windows 11 Pro 24H2 | `192.168.131.108` | Pool laptop |

**WAPs:** `EXAWAPEDI001–002` · Ubiquiti UniFi U6-Pro

**IoT:** `EXATEAEDI001` — Siemens EQ700 Coffee Machine (`192.168.131.60`)

---

#### GLA — Glasgow
**LAN:** `192.168.141.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCRGLA001` | DC | Windows Server 2022 | `192.168.141.10` | Schema Master · Domain Naming Master · PDC Emulator |

**Endpoints:**

| Hostname | Type | OS | IP | Notes |
|----------|------|----|----|-------|
| `EXAWKSGLA001` | Workstation | Windows 11 Pro | `192.168.141.150` | Hot desk |
| `EXAWKSGLA002` | Workstation | Windows 11 Pro | `192.168.141.151` | Hot desk |
| `EXALAPGLA001` | Laptop | Windows 11 Pro | `192.168.141.152` | Pool device |
| `EXAPGLAGLA001` | Printer | HP LaserJet Pro | `192.168.141.16` | Main floor |

---

#### CLY — Clydebank
**LAN:** `192.168.41.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXAFWLCLY001` | Firewall | FortiOS 7.6.5 | `192.168.41.1` | VPN gateway |
| `EXASWICLY001` | Switch | Cisco Catalyst 9300 | `192.168.41.250` | Core switch |
| `EXARTRCLY001` | Router | Cisco ISR 4331 | `192.168.41.254` | WAN edge |
| `EXARACLY001` | iLO | HPE iLO5 | `192.168.41.2` | BMC |
| `EXADCSCLY001` | DC | Windows Server 2022 | `192.168.41.10` | Global Catalog |
| `EXADCSCLY002` | DC | Windows Server 2022 | `192.168.41.11` | Global Catalog |
| `EXASRVCLY001` | Server | Rocky Linux | `192.168.41.20` | Oracle DB |
| `EXASBCCLY001` | VOIP SBC | 3CX SBC Debian | `192.168.41.48` | Trunks to `EXACLDPBX001` |

**WAPs:** `EXAWAPCLY001–002` · Ubiquiti UniFi U6-Pro

**Endpoints:** `EXASURCLY001` (Surface), `EXAPHNCLY001` (iOS), `EXASURCLY002` (Android tablet)

---

#### DUN — Dundee
**LAN:** `192.168.138.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRDUN001` | Router | Cisco ISR 4331 | `192.168.138.254` | WAN edge |
| `EXADCSDUN001` | DC | Windows Server 2022 | `192.168.138.10` | Global Catalog |

**WAPs:** `EXAWAPDUN001–002` · Ubiquiti UniFi U6-Pro

**Endpoints:** `EXASURDUN001–002` (Surface/Win11), `EXAPHNDUN001–002` (iOS)

---

#### PER — Perth
**LAN:** `192.168.173.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSPER001` | DC | Windows Server 2022 | `192.168.173.10` | Global Catalog |
| `EXASBCPER001` | VOIP SBC | 3CX SBC Debian | `192.168.173.48` | Trunks to `EXACLDPBX001` |
| `EXANIXPER001` | Unix | Solaris 11.5 | `192.168.173.40` | MIDI/Music archive — Fiction Factory |
| `EXANASPER001` | NAS | Synology DSM 7.1 | `192.168.173.50` | User profiles & music archive |

**Endpoints:** `EXAMBPPER001` (MacBook Pro), `EXASURPER001` (Surface), `EXAPHNPER001–004` (Yealink T46G)

**IoT:** `EXAPRNPER001` (HP MFP), `EXAVNDPER001` (Scone Palace vending — Embedded SP100)

---

#### ABD — Aberdeen
**LAN:** `192.168.224.0/24` · **Domain:** `example.org`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXAFWLABD001` | Firewall | Cisco ASA 5506-X | `192.168.224.1` | Edge firewall |
| `EXARTRABD001` | Router | Cisco ISR 4331 | `192.168.224.254` | WAN edge |

**WAPs:** `EXAWAPABD001–002` · Ubiquiti UniFi U6-Pro

**Endpoints:** `EXAMBPABD001–002` (MacBooks), `EXAPHNABD001–002` (iPhones)

---

### 🏴󠁧󠁢󠁥󠁮󠁧󠁿 United Kingdom — England

---

#### LND — London
**LAN:** `192.168.20.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXAFWLLND001` | Firewall | Cisco ASA 5516-X | `192.168.20.1` | Perimeter firewall · VPN gateway |
| `EXASWILND001` | Switch | Cisco Catalyst 9300 | `192.168.20.250` | Core switch |
| `EXARTRLND001` | Router | Cisco ISR 4331 | `192.168.20.254` | WAN edge |
| `EXARACLND001` | iDRAC | Dell iDRAC9 | `192.168.20.2` | BMC |
| `EXADCRLND001` | DC | Windows Server 2022 | `192.168.20.10` | RID Master · Infrastructure Master |
| `EXASBCLND001` | VOIP SBC | 3CX SBC Debian | `192.168.20.48` | Trunks to `EXACLDPBX001` |

**Endpoints:** `EXAWKSLND001` (Win11 hot desk `192.168.20.150`), `EXAPRNLND001` (Xerox WorkCentre)

**IoT:**

| Hostname | Type | IP | Notes |
|----------|------|----|-------|
| `EXARADLND001` | Radio TX | `192.168.20.80` | BBC Office Radio Mk II — FM-IP bridge |
| `EXAMICLND001` | Microphone | `192.168.20.81` | Shure SM7 via Dante audio |
| `EXAPRNLND002` | Steno Writer | — | ProCAT Stylus — court device |

---

#### BIR — Birmingham
**LAN:** `192.168.121.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXAFWLBIR001` | Firewall | Palo Alto PAN-OS | `192.168.121.1` | VPN gateway |
| `EXASWIBIR001` | Switch | Cisco Catalyst 9300 | `192.168.121.250` | Core switch |
| `EXASWIBIR002` | Switch | Cisco Catalyst 48-port | `192.168.121.251` | Access switch |
| `EXARTRBIR001` | Router | Cisco ISR 4331 | `192.168.121.254` | WAN edge |
| `EXARACBIR001` | DRAC | Dell DRAC | `192.168.121.2` | BMC |
| `EXADCRBIR001` | DC | Windows Server 2022 | `192.168.121.10` | Global Catalog |
| `EXADCRBIR002` | DC | Windows Server 2022 | `192.168.121.11` | Global Catalog |
| `EXASRVBIR001` | Server | Rocky Linux | `192.168.121.20` | Oracle DB |
| `EXASBCBIR001` | VOIP SBC | 3CX SBC Debian | `192.168.121.48` | Trunks to `EXACLDPBX001` |

**WAPs:** `EXAWAPBIR001–002` · Ubiquiti UniFi U6-Pro

**Endpoints:** `EXAMBPBIR001` (MacBook), `EXATABBIR001` (Samsung Galaxy Tab), `EXAPHNBIR001` (Samsung S25)

**Instruments & IoT:**

| Hostname | Type | IP | Notes |
|----------|------|----|-------|
| `EXAMOOBIR001` | Moog One | `192.168.121.70` | Synthesizer — MIDI |
| `EXALINBIR001` | LinnDrum LM-2 | `192.168.121.71` | Drum machine — MIDI |
| `EXAFCLBIR001` | Fairlight CMI IIx | `192.168.121.72` | Sampling workstation — QDOS 2.x |
| `EXAASTBIR001` | Atari ST | `192.168.121.73` | MIDI sequencing — TOS 1.04 |
| `EXAPAYBIR001` | Payphone | `192.168.121.74` | GPO Kiosk No.6 — KX6 Red |
| `EXALCDBIR001` | LCD Display | `192.168.121.75` | NEC PlasmaSync 42MP1 — NOC display |

---

#### MCR — Manchester
**LAN:** `192.168.161.0/24` · **Domain:** `example.org`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXASWIMCR001` | Switch | Cisco Catalyst 9300 | `192.168.161.250` | Distribution switch |
| `EXARACMCR001` | iLO | HPE iLO5 | `192.168.161.2` | BMC |
| `EXADCRMCR001` | DC | Windows Server 2022 | `192.168.161.10` | PDC Emulator · RID Master · Infrastructure Master |
| `EXADCSMCR002` | DC | Windows Server 2022 | `192.168.161.11` | Global Catalog |
| `EXASBCMCR001` | VOIP SBC | 3CX SBC Debian | `192.168.161.48` | Trunks to `EXACLDPBX001` |

**Endpoints:** `EXALAPMCR001–002` (Win11 laptops), `EXAWKSMCR001–002` (Win10 desktops), `EXAPRNMCR001` (printer)

---

#### LIV — Liverpool
**LAN:** `192.168.151.0/24` · **Domain:** `example.org`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXASWILIV001` | Switch | Cisco Catalyst 9200 | `192.168.151.250` | Core switch |
| `EXARACLIV001` | iLO | HPE iLO5 | `192.168.151.2` | BMC |
| `EXADCRLIV001` | DC | Windows Server 2025 | `192.168.151.10` | Global Catalog |
| `EXASBCLIV001` | VOIP SBC | 3CX SBC Debian | `192.168.151.48` | Trunks to `EXACLDPBX001` |

**Endpoints:** `EXASVRLIV001` (Win Server 2022 file server), `EXAMBPLIV001` (MacBook Pro — macOS Tahoe), `EXAMACLIV001` (iMac — **disabled, maintenance**)

**Security:** `EXARDRLIV002` (HID Signo badge reader), `EXABPSLIV001` (badge programming workstation)

---

#### NEW — Newcastle
**LAN:** `192.168.191.0/24` · **Domain:** `example.org`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXASWINEW001` | Switch | TP-Link JetStream | `192.168.191.250` | Access switch |
| `EXARACNEW001` | iDRAC | Dell iDRAC9 | `192.168.191.2` | BMC |
| `EXADCRNEW001` | DC | Windows Server 2022 | `192.168.191.10` | Global Catalog |
| `EXASBCNEW001` | VOIP SBC | 3CX SBC Debian | `192.168.191.48` | Trunks to `EXACLDPBX001` |

**Endpoints:** `EXASRVNEW001` (Win Server 2022 file/print), `EXAWKSNEW099` (Win11 — ⚠️ LAPS password expired)

---

#### COV — Coventry
**LAN:** `192.168.247.0/24` · **Domain:** `example.net`

**Infrastructure:** `EXARTRCOV001` (Cisco ISR 4331 — `192.168.247.254`)

**WAPs:** `EXAWAPCOV001–002` · Ubiquiti UniFi U6-Pro

---

#### HAL — Halifax
**LAN:** `192.168.142.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSHAL001` | DC | Windows Server 2022 | `192.168.142.10` | — |
| `EXASBCHAL001` | VOIP SBC | 3CX SBC Debian | `192.168.142.48` | Trunks to `EXACLDPBX001` |

---

#### HUL — Hull
**LAN:** `192.168.148.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSHUL001` | DC | Windows Server 2022 | `192.168.148.10` | — |
| `EXASBCHUL001` | VOIP SBC | 3CX SBC Debian | `192.168.148.48` | Trunks to `EXACLDPBX001` |

---

#### SHE — Sheffield
**LAN:** `192.168.114.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSSHE001` | DC | Windows Server 2022 | `192.168.114.10` | — |
| `EXASBCSHE001` | VOIP SBC | 3CX SBC Debian | `192.168.114.48` | Trunks to `EXACLDPBX001` |

---

### 🇩🇰 Danmark

---

#### CPH — København
**LAN:** `192.168.231.0/24` · **Domain:** `example.com` / `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXASWICPH001` | Switch | TP-Link JetStream | `192.168.231.250` | Office switch |
| `EXARTRCPH001` | Router | Cisco ISR 4331 | `192.168.231.254` | WAN edge |
| `EXARACCPH001` | iDRAC | Dell iDRAC9 | `192.168.231.2` | BMC |
| `EXADCSCPH001` | DC | Windows Server 2022 | `192.168.231.10` | example.com |
| `EXADCSCPH002` | DC | Windows Server 2022 | `192.168.231.11` | example.net |
| `EXASBCCPH001` | VOIP SBC | 3CX SBC Debian | `192.168.231.48` | Trunks to `EXACLDPBX001` |

**WAPs:** `EXAWAPCPH001–003` · Ubiquiti UniFi U6-Pro

**IoT:** `EXACLKCPH001` (Meinberg LANTIME M300 NTP `192.168.231.18`), `EXATVSCPH001` (Bella Kronik 42X `192.168.231.17`)

---

#### ODE — Odense
**LAN:** `192.168.126.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXAFWLODE001` | Firewall | Cisco ASA 5506-X | `192.168.126.1` | Edge firewall |
| `EXADCSODE001` | DC | Windows Server 2022 | `192.168.126.10` | PDC Emulator · RID Master · Infrastructure Master |
| `EXADCSODE002` | DC | Windows Server 2022 | `192.168.126.11` | Global Catalog |
| `EXASBCODE001` | VOIP SBC | 3CX SBC Debian | `192.168.126.48` | Trunks to `EXACLDPBX001` |

**WAPs:** `EXAWAPODE001–002` · Ubiquiti UniFi U6-Pro

**Endpoints:** `EXAMACODE001` (iMac macOS Tahoe), `EXAMBPODE002` (MacBook Pro)

**IoT:** `EXAMUSODE001` — Pureline 128V Retro Vinyl Jukebox (`192.168.126.60`) *(First Hotel Grand Odense)*

---

#### KGE — Køge
**LAN:** `192.168.65.0/24` · **Domain:** `example.net`

> ⚠️ `EXADCSKGE001` — replication warning, last sync 27 days ago. Windows Server 2016 (EOL). Disk space low.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSKGE001` | DC | Windows Server 2016 | `192.168.65.10` | ⚠️ Out of sync · EOL OS |

**WAPs:** `EXAWAPKGE001` · Ubiquiti UniFi U6-Pro

**Other:** `EXAPRNKGE001` (HP LaserJet MFP M528)

---

#### FAX — Faxe
**LAN:** `192.168.246.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTFFAX001` | Router | Cisco ISR 4331 | `192.168.246.254` | WAN edge |
| `EXADCSFAX001` | DC | Windows Server 2022 | `192.168.246.10` | — |

**WAPs:** `EXAWAPFAX001–002` · Ubiquiti UniFi U6-Pro

---

#### KOR — Korsør
**LAN:** `192.168.238.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSKOR001` | DC | Windows Server 2022 | `192.168.238.10` | — |
| `EXASBCKOR001` | VOIP SBC | 3CX SBC Debian | `192.168.238.48` | Trunks to `EXACLDPBX001` |

---

### 🇩🇪 Deutschland

---

#### BON — Bonn
**LAN:** `192.168.228.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXASWIBON001` | Switch | Cisco Catalyst 2960X | `192.168.228.250` | Office switch |
| `EXARTRBON001` | Router | Cisco ISR 4331 | `192.168.228.254` | WAN edge |
| `EXARACBON001` | iDRAC | Dell iDRAC9 | `192.168.228.2` | BMC |
| `EXADCSBON001` | DC | Windows Server 2022 | `192.168.228.10` | **Schema Master · Domain Naming Master** |
| `EXASBCBON001` | VOIP SBC | 3CX SBC Debian | `192.168.228.48` | Trunks to `EXACLDPBX001` |

**WAPs:** `EXAWAPBON001–002` · Ubiquiti UniFi U6-Pro

**Endpoints:** `EXALAPBON001` (ThinkPad — **disabled, maintenance**), `EXAWKSBON001` (Win11 finance), `EXALAPBON002` (Win11 finance)

**IoT:** `EXAVCUBON001` (Poly Studio X70 boardroom), `EXACAMBON001` (Axis P3245-LVE CCTV), `EXATVSBON001` (Samsung 65")

---

#### BRD — West Berlin
**LAN:** `192.168.113.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRBRD001` | Router | Cisco ISR 4331 | `192.168.113.254` | WAN edge |
| `EXADCSBRD001` | DC | Windows Server 2019 | `192.168.113.10` | PDC Emulator · RID Master · Infrastructure Master |
| `EXASBCBRD001` | VOIP SBC | 3CX SBC Debian | `192.168.113.48` | Trunks to `EXACLDPBX001` |

**WAPs:** `EXAWAPBRD001–002` · Ubiquiti UniFi U6-Pro

**Endpoints:** `EXASRVBRD001` (WS2019 legacy app server), `EXANIXBRD001` (Debian 12)

---

#### MUN — Munich
**LAN:** `192.168.189.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXASWIMUN001` | Switch | Cisco Catalyst 9200 | `192.168.189.250` | Access switch |
| `EXARACMUN001` | iLO | HPE iLO5 | `192.168.189.2` | BMC |
| `EXADCSMUN001` | DC | Windows Server 2022 | `192.168.189.10` | Global Catalog |
| `EXASBCMUN001` | VOIP SBC | 3CX SBC Debian | `192.168.189.48` | Trunks to `EXACLDPBX001` |

**Endpoints:** `EXAWKSMUN001` (Win11 hot desk), `EXALAPMUN001` (Win11 pool), `EXALAPMUN002` (Win11 — ⚠️ LAPS expired 61 days ago)

---

### 🇸🇪 Sverige

---

#### GOT — Gothenburg
**LAN:** `192.168.46.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSGOT001` | DC | Windows Server 2022 | `192.168.46.10` | — |
| `EXASBCGOT001` | VOIP SBC | 3CX SBC Debian | `192.168.46.48` | Trunks to `EXACLDPBX001` |

---

### 🇳🇴 Norge

---

#### OSL — Oslo
**LAN:** `192.168.47.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSOSL001` | DC | Windows Server 2022 | `192.168.47.10` | — |
| `EXASBCOSL001` | VOIP SBC | 3CX SBC Debian | `192.168.47.48` | Trunks to `EXACLDPBX001` |

---

### 🇳🇱 Nederland

---

#### AMS — Amsterdam
**LAN:** `192.168.31.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSAMS001` | DC | Windows Server 2022 | `192.168.31.10` | — |
| `EXASBCAMS001` | VOIP SBC | 3CX SBC Debian | `192.168.31.48` | Trunks to `EXACLDPBX001` |

---

### 🇮🇹 Italia

---

#### MIL — Milan
**LAN:** `192.168.39.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSMIL001` | DC | Windows Server 2022 | `192.168.39.10` | — |
| `EXASBCMIL001` | VOIP SBC | 3CX SBC Debian | `192.168.39.48` | Trunks to `EXACLDPBX001` |

---

### 🇦🇹  Österreich

---

#### VIE — Vienna
**LAN:** `192.168.78.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSVIE001` | DC | Windows Server 2022 | `192.168.78.10` | — |
| `EXASBCVIE001` | VOIP SBC | 3CX SBC Debian | `192.168.78.48` | Trunks to `EXACLDPBX001` |

---

### 🇨🇦 Canada

---

#### BRK — Brockville, Ontario
**LAN:** `192.168.136.0/24` · **Domain:** `example.net`

> ⚠️ `EXADCSBRK001` — DNS, Netlogon and KDC services stopped.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRBRK001` | Router | Cisco ISR 4331 | `192.168.136.254` | WAN edge |
| `EXADCSBRK001` | DC | Windows Server 2022 | `192.168.136.10` | ⚠️ Services stopped |
| `EXASBCBRK001` | VOIP SBC | 3CX SBC Debian | `192.168.136.48` | Trunks to `EXACLDPBX001` |

**WAPs:** `EXAWAPBRK001` · Ubiquiti UniFi U6-Pro

**Endpoints:** `EXALAPBRK001` (Win11 tour laptop), `EXAVNDBRK001` (Maple syrup vending — XPe)

**IoT:** `EXADONBRK001` (Tim Hortons Donut vending — VxWorks `192.168.136.60`)

---

#### TOR — Toronto, Ontario
**LAN:** `192.168.164.0/24` · **Domain:** `example.net`

> ⚠️ `EXADCSTOR001` — DNS, Netlogon and KDC services stopped.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSTOR001` | DC | Windows Server 2022 | `192.168.164.10` | ⚠️ Services stopped |
| `EXASBCTOR001` | VOIP SBC | 3CX SBC Debian | `192.168.164.48` | Trunks to `EXACLDPBX001` |

---

#### MTL — Montreal, Quebec
**LAN:** `192.168.154.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSMTL001` | DC | Windows Server 2022 | `192.168.154.10` | — |
| `EXASBCMTL001` | VOIP SBC | 3CX SBC Debian | `192.168.154.48` | Trunks to `EXACLDPBX001` |

---

### 🇺🇸 United States

---

#### LAX — Los Angeles, California
**LAN:** `192.168.213.0/24` · **Domain:** `example.net`

> ⚠️ `EXADCSLAX001` — DNS, Netlogon and KDC services stopped.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXAFWLLAX001` | Firewall | Palo Alto PAN-OS 10.x | `192.168.213.1` | VPN gateway |
| `EXASWILAX001` | Switch | Cisco Catalyst 9300 | `192.168.213.250` | Core switch |
| `EXASWILAX002` | Switch | Cisco Catalyst 2960 | `192.168.213.251` | Access switch |
| `EXARTRLAX001` | Router | Cisco ISR 4331 | `192.168.213.254` | WAN edge |
| `EXARACLAX001` | iDRAC | Dell iDRAC9 | `192.168.213.2` | BMC |
| `EXADCSLAX001` | DC | Windows Server 2022 | `192.168.213.10` | ⚠️ Services stopped |
| `EXASRVLAX001` | Server | Rocky Linux 9.x | `192.168.213.20` | Local services / DB |
| `EXASBCLAX001` | VOIP SBC | 3CX SBC Debian | `192.168.213.48` | Trunks to `EXACLDPBX001` |

**WAPs:** `EXAWAPLAX001–003` · Ubiquiti UniFi U6-Pro

**Endpoints:** `EXAMBPLAX001` (MacBook Pro), `EXATABLAX001` (iPad setlists), `EXAPHNLAX001` (Android)

**Instruments & IoT:**

| Hostname | Type | IP | Notes |
|----------|------|----|-------|
| `EXAMUSLAX001` | Moog One | `192.168.213.70` | Synthesizer |
| `EXAMUSLAX002` | LinnDrum LM-2 | `192.168.213.71` | Drum machine — EPROM v7 |
| `EXAMUSLAX003` | Fairlight CMI IIx | `192.168.213.72` | Sampler — QDOS 2.x |
| `EXAATTLAX001` | Atari ST | `192.168.213.73` | MIDI sequencing — TOS 1.04 |
| `EXAPAYLAX001` | Payphone | `192.168.213.74` | Lobby payphone — SIP gateway |
| `EXALCDLAX001` | LCD Display | `192.168.213.75` | NEC PlasmaSync status wallboard |

---

#### NYC — New York, NY
**LAN:** `192.168.212.0/24` · **Domain:** `example.net`

> ⚠️ `EXADCSNYC001` — DNS, Netlogon and KDC services stopped.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSNYC001` | DC | Windows Server 2022 | `192.168.212.10` | ⚠️ Services stopped |
| `EXASBCNYC001` | VOIP SBC | 3CX SBC Debian | `192.168.212.48` | Trunks to `EXACLDPBX001` |

---

#### NJC — Camden, New Jersey
**LAN:** `192.168.201.0/24` · **Domain:** `example.net`

> ⚠️ `EXADCSNJC001` — DNS, Netlogon and KDC services stopped.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSNJC001` | DC | Windows Server 2022 | `192.168.201.10` | ⚠️ Services stopped |
| `EXASBCNJC001` | VOIP SBC | 3CX SBC Debian | `192.168.201.48` | Trunks to `EXACLDPBX001` |

---

#### MIA — Miami, Florida
**LAN:** `192.168.135.0/24` · **Domain:** `example.net`

**Endpoints:** `EXALAPMIA001` (MacBook — macOS Sonoma)

**IoT:** `EXACOFMIA001` (Cuban Covfefe machine — VxWorks `192.168.135.60`)

---

#### ATL — Athens, Georgia
**LAN:** `192.168.44.0/24` · **Domain:** `example.net`

> ⚠️ `EXADCSATL001` — DNS, Netlogon and KDC services stopped.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSATL001` | DC | Windows Server 2022 | `192.168.44.10` | ⚠️ Services stopped |
| `EXASBCATL001` | VOIP SBC | 3CX SBC Debian | `192.168.44.48` | Trunks to `EXACLDPBX001` |

---

#### CHI — Chicago, Illinois
**LAN:** `192.168.214.0/24` · **Domain:** `example.net`

> ⚠️ `EXADCSCHI001` — DNS, Netlogon and KDC services stopped.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSCHI001` | DC | Windows Server 2022 | `192.168.214.10` | ⚠️ Services stopped |
| `EXASBCCHI001` | VOIP SBC | 3CX SBC Debian | `192.168.214.48` | Trunks to `EXACLDPBX001` |

---

### 🇦🇺 Australia

---

#### SYD — Sydney, NSW
**LAN:** `192.168.29.0/24` · **Domain:** `example.net`

> ⚠️ `EXADCSSYD001` — DNS, Netlogon and KDC services stopped.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXAFWLSYD001` | Firewall | FortiGate 7.x | `192.168.29.1` | Site firewall |
| `EXASWISYD001` | Switch | Cisco Catalyst 9300 | `192.168.29.250` | Core switch |
| `EXASWISYD002` | Switch | Cisco Catalyst 2960 | `192.168.29.251` | Access switch |
| `EXARACSYD001` | iDRAC | Dell iDRAC9 | `192.168.29.2` | BMC |
| `EXADCSSYD001` | DC | Windows Server 2022 | `192.168.29.10` | ⚠️ Services stopped |
| `EXASRVSYD001` | Server | Windows Server 2022 | `192.168.29.20` | Local infra |
| `EXASBCSYD001` | VOIP SBC | 3CX SBC | `192.168.29.48` | Trunks to `EXACLDPBX001` |

**WAPs:** `EXAWAPSYD001` · Ubiquiti UniFi

**Endpoints:** `EXAMBPSYD001` (MacBook Pro), `EXAWKSSYD001` (Win11), `EXAPHNSYD001` (Android), `EXATABSYD001` (iPad)

**IoT:** `EXALCDSYD001` (LG Signage wallboard), `EXAPRNSYD001` (Brother Laser), `EXACAMSYD001` (Hikvision camera), `EXACOFSYD001` (Smart coffee machine)

---

#### MEL — Melbourne, VIC
**LAN:** `192.168.61.0/24` · **Domain:** `example.net`

> ⚠️ `EXADCSMEL001` — DNS, Netlogon and KDC services stopped.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXAFWLMEL001` | Firewall | FortiGate 7.x | `192.168.61.1` | Site firewall |
| `EXASWIMEL001` | Switch | Cisco Catalyst 9300 | `192.168.61.250` | Core switch |
| `EXASWIMEL002` | Switch | Cisco Catalyst 2960 | `192.168.61.251` | Access switch |
| `EXARACMEL001` | iLO | HPE iLO5 | `192.168.61.2` | BMC |
| `EXADCSMEL001` | DC | Windows Server 2022 | `192.168.61.10` | ⚠️ Services stopped |
| `EXASRVMEL001` | Server | Windows Server 2022 | `192.168.61.20` | Local file & print |
| `EXASBCMEL001` | VOIP SBC | 3CX SBC | `192.168.61.48` | Trunks to `EXACLDPBX001` |

**Endpoints:** `EXAMBPMEL001` (MacBook Pro), `EXAWKSMEL001` (Win11), `EXAPHNMEL001` (iOS), `EXATABMEL001` (iPad)

**IoT:** `EXALCDMEL001` (Samsung Signage), `EXAPRNMEL001` (HP LaserJet), `EXANASMEL001` (Synology DSM 7.x)

---

### 🇳🇿 New Zealand

---

#### AKL — Auckland
**LAN:** `192.168.93.0/24` · **Domain:** `example.net`

> ⚠️ `EXADCSAKL001` — DNS, Netlogon and KDC services stopped.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXAFWLAKL001` | Firewall | FortiGate 7.x | `192.168.93.1` | Site firewall |
| `EXASWIAKL001` | Switch | Cisco Catalyst 9300 | `192.168.93.250` | Core switch |
| `EXASWIAKL002` | Switch | Cisco Catalyst 2960 | `192.168.93.251` | Access switch |
| `EXARTRAKL001` | Router | Cisco ISR 4331 | `192.168.93.254` | WAN edge |
| `EXARACAKL001` | iLO | HPE iLO5 | `192.168.93.2` | BMC |
| `EXADCSAKL001` | DC | Windows Server 2022 | `192.168.93.10` | ⚠️ Services stopped |
| `EXASRVAKL001` | Server | Windows Server 2022 | `192.168.93.20` | Local server |
| `EXASBCAKL001` | VOIP SBC | 3CX SBC | `192.168.93.48` | Trunks to `EXACLDPBX001` |

**WAPs:** `EXAWAPAKL001`, `EXAWAPAKL002` · Ubiquiti UniFi

**Endpoints:** `EXAWKSAKL001` (Win11), `EXAMBPAKL001` (MacBook Pro), `EXAPHNAKL001` (Android), `EXATABAKL001` (iPad)

**IoT:** `EXALCDAKL001` (Samsung Signage), `EXAPRNAKL001` (HP LaserJet), `EXACAMAKL001` (Axis camera), `EXACOFAKL001` (Smart coffee machine)

---

## ⚠️ Known Issues & Actions Required

| Priority | Site | Device | Issue |
|----------|------|--------|-------|
| 🔴 Critical | EDI | `EXADCSEDI003` | DFSR stopped · C: drive 5% free · holds RID Master / Infrastructure Master |
| 🔴 Critical | KGE | `EXADCSKGE001` | No replication for 27 days · Windows Server 2016 (EOL) · disk space low |
| 🟠 High | BRK, TOR, NYC, NJC, ATL, LAX, CHI, SYD, MEL, AKL | Multiple DCs | DNS, Netlogon, KDC all stopped — requires investigation |
| 🟡 Medium | NEW | `EXAWKSNEW099` | LAPS password expired |
| 🟡 Medium | MUN | `EXALAPMUN002` | LAPS expired 61 days ago · last logged on 95 days ago |
| 🟡 Medium | FAL | `EXAPVEFAL001–002` | Not yet on ZFS RAID1 · boot independence test pending |
| 🔵 Info | BIR, LAX | Instruments | Atari ST, Fairlight CMI, LinnDrum on production LAN — no security controls |
| 🔵 Info | FAL | Vending | 3x NT4 Embedded vending machines on production network |

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
