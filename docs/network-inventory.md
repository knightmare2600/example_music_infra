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
| 2026-07-20 | Added `EXASLTCLD001` (Salt master, `192.168.69.22`) to the CLD LAN table — added to `devices.csv` the same day, missing from this doc until now. Also reachable as `salt.jukebox.internal` (new CNAME, `benarbejde/role_codes.csv`'s `DNSAlias` column). |
| 2026-07-20 | Rudder's role code split: `RDR` now means exclusively "Reader" (badge reader, physical, standard `.21` slot, new); the Rudder config-mgmt meaning moved to a new code, `RUD` — `EXARDRCLD001` is now `EXARUDCLD001`. Ironically reverses the 2026-07-08 entry below, which "fixed" `EXARUDCLD001` back to `EXARDRCLD001` as a typo — it wasn't; `RDR` just hadn't collided with badge readers yet at the time. Safe to do as a straight rename (not a live migration) since no Rudder infrastructure has actually been built yet — see `docs/proxmox/proxmox-dcm-pbs-planning.md` and `benarbejde/role_codes.csv` for the full rationale. |
| 2026-07-12 | FAL's "Completion checklist" listed the firewall as installed before the Proxmox nodes — backwards, since the firewall is a VM hosted on Proxmox (see `buildsheets/buildsheet-firewall.md` Step 1). Reordered. |
| 2026-07-08 | Fixed both "Cloud / Provisioning" sections, which wrongly labelled CLD's own LAN subnet as `192.168.139.0/24` (that's `VRK`, the vRACK — CLD's own LAN is `192.168.69.0/24`), a leftover from before the CLD/VRK split existed. Restructured into three clearly separated subsections (vRACK/CLD LAN/FRD); added `FRD` (Fredericia Havn) and `VRK` rows to the Global Site Summary, which previously had neither. Fixed `EXARUDCLD001` -> `EXARDRCLD001` (typo). Fixed stale forest name `jukebox.example` -> `jukebox.internal` (this repo's domain rename completed some time ago; this reference was never updated). |
| 2026-07-08 | WAPs moved off DHCP to static `.82`–`.94` (added to Standard IP Convention table). Per-site `**WAPs:**` lines updated. Added `EXAUFCCLD001` (UniFi Network Controller, CLD LAN `192.168.69.82`) — manages every site's WAPs; CLD itself has no physical WiFi |
| 2026-03-05 | Full review —<br /><br />subnets corrected against canonical site list; standard IP convention table added<br />CLY corrected to `192.168.41.0/24`<br />GLA corrected to `192.168.141.0/24`<br />KGE corrected to `192.168.65.0/24`<br />MEL corrected to `192.168.61.0/24`<br />MIA corrected to `192.168.135.0/24`<br />MUN corrected to `192.168.189.0/24`<br />BRD renamed BER throughout<br />TOR subnet corrected to `192.168.146.0/24`<br />FAL DC IPs corrected to `.76.10`/`.76.11`<br />FAL PVE nodes renamed EXAPVE and corrected to `.76.5`/`.76.6`<br />FAL RAC corrected to `.2`/`.3`<br />BON DC corrected to `192.168.228.10`<br />ODE DC002 corrected to `192.168.126.11`<br />FAX DC corrected to `192.168.246.10`<br />SBC addresses corrected to `.48` throughout<br />CLD (Cloud) site added<br />new sites added: AMS, ATL, CHI, GOT, HAL, HUL, KOR, MIL, MTL, OSL, SHE, VIE |
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
| `.1` | Router / upstream gateway | `EXARTR<SITE>001` |
| `.2` | BMC pool slot 1 — DRAC / iLO | `EXARAC<SITE>001` |
| `.3` | BMC pool slot 2 — or RAC emulator VM on single-PVE-node sites | `EXARAC<SITE>002` |
| `.4` | BMC pool slot 3 — or RAC emulator VM on two-PVE-node sites | `EXARAC<SITE>003` |
| `.5` | PVE node 1 | `EXAPVE<SITE>001` |
| `.6` | PVE node 2 | `EXAPVE<SITE>002` |
| `.7` | PVE node 3 | `EXAPVE<SITE>003` |
| `.10` | Domain Controller — primary | `EXADCS<SITE>001` |
| `.11` | Domain Controller — secondary | `EXADCS<SITE>002` |
| `.12` | Rudder Relay (Rudder Server on CLD) | `EXARRY<SITE>001` / `EXARUDCLD001` |
| `.48` | VOIP SBC — trunks to `EXAPBXCLD001` | `EXASBC<SITE>001` |
| `.82`–`.94` | WAPs (static, added 2026-07-08 — moved off DHCP). Count varies per site | `EXAWAP<SITE>001`–`013` |
| `.100`–`.249` | DHCP pool | — |
| `.250`–`.252` | RT switches | `EXASWI<SITE>001`–`003` |
| `.253` | Firewall — primary | `EXAFWL<SITE>001` |
| `.254` | Firewall — secondary | `EXAFWL<SITE>002` |

> **BMC pool:** `.2`/`.3`/`.4` are shared between physical DRAC/iLO interfaces. Te RAC emulator VM. Physical PVE node BMCs consume from `.2` upward. the RAC VM (`EXARAC<SITE>00N`) takes the next free slot.
> 
> ***NB: On three-PVE-node sites the pool is fully consumed by physical BMCs.***

---

## Cloud / Provisioning Network — CLD / VRK / FRD

CLD (Edinburgh, OVH datacentre) has two networks, each its own site code in `sites.csv` — its
own LAN (`CLD`) and the OVH vRACK provisioning network (`VRK`). `FRD` (Fredericia Havn) is a
second, standby provisioning network, same idea as `VRK`, at a different site entirely — see
`docs/ExampleMusic_Beginners_Guide.md` §4.2.

**vRACK — `VRK`, `192.168.139.0/24`**
**WireGuard hub** — routes to all sites. Any node that can reach `192.168.139.1` can reach any site subnet.

| Hostname | Role | OS | IP | Notes |
|----------|------|----|----|-------|
| `EXAFWLVRK001` | Firewall / WireGuard hub | — | `192.168.139.1` | CNAME `ovhfwl.knight139.co.uk` — same physical firewall as `EXAFWLCLD001` |
| `EXADNSVRK001` | DNS / BIND9 server | Debian | `192.168.139.8` | Authoritative DNS for `jukebox.internal` |
| — (bootstrap-only, no formal hostname) | Provisioning / bootstrap | — | `192.168.139.50` | Serves Ansible keys, ISOs, scripts |
| `EXAFWLVRK001` (WAN face) | Firewall — vRACK WAN | — | `192.168.139.69` | Same device as `EXAFWLCLD001` (LAN face, `192.168.69.253`) |

**CLD LAN — `CLD`, `192.168.69.0/24`**

| Hostname | Role | OS | IP | Notes |
|----------|------|----|----|-------|
| `EXABMCCLD001` | BMC / iDRAC / iLO / Redfish | — | `192.168.69.2` | Standard BMC slot 1 — real hardware in an Edinburgh datacentre |
| `EXAANSCLD001` | Ansible control node | Debian | `192.168.69.9` | Ansible — manages all sites |
| `EXARUDCLD001` | Rudder Server | Debian | `192.168.69.12` | Not in active use — dormant, kept as reference code only, see NET-MGMT-RUDDER-001 |
| `EXANASCLD001` | Storage (NAS/SAN) | — | `192.168.69.19` | Standard NAS slot |
| `EXARDRCLD001` | Badge reader | — | `192.168.69.21` | Standard RDR slot |
| `EXASVRCLD002` | Windows Admin Centre | Windows Server 2022 | `192.168.69.20` | WAC — reaches all site DCs and Windows nodes |
| `EXASLTCLD001` | Salt master | Debian | `192.168.69.22` | Config mgmt for all Windows nodes (client, server, DC) — see `ansible/playbooks/salt/README.md`. Also reachable as `salt.jukebox.internal` (CNAME) |
| `EXAPBXCLD001` | Central PBX | — | `192.168.69.48` | 3CX PBX — all site SBCs trunk here |
| `EXAUFCCLD001` | UniFi Network Controller | Debian trixie | `192.168.69.82` | Manages every site's WAPs. CLD has no physical WiFi itself; `.82` is WAP1's reserved octet elsewhere, deliberately reused here for the controller |
| `EXASWICLD001` | Switch | — | `192.168.69.250` | Standard SWI slot 1 |
| `EXAFWLCLD002` | Firewall (secondary) | — | `192.168.69.254` | Standard FWL slot 2 — not yet built |

**FRD — Fredericia Havn (standby), `172.16.124.0/24`**

| Hostname | Role | IP | Notes |
|----------|------|----|-------|
| — (bootstrap-only, no formal hostname) | Provisioning / bootstrap (standby) | `172.16.124.1` | Port 8000, not 80 |
| `EXAPVEFRD001` | Proxmox VE node | `172.16.124.5` | Small Intel NUC — part of FRD's real "site kit" alongside the switch below, despite FRD being otherwise a legal-fiction single-MacBook provisioning network (confirmed by Robert, 2026-07-30) |
| `EXASWIFRD001` | Switch | `172.16.124.250` | 48-port — part of the site kit alongside the NUC above |
| `EXAPBXCLD002` | Secondary 3CX PBX | `172.16.124.48` | Physically at Fredericia Havn — hostnamed under CLD as part of the 2026-07-11 Pulsant DC / FRD Havn network rework (renamed from `EXAPBXFRD001`). Reuses the empty SBC slot, same pattern as CLD's own PBX (`EXAPBXCLD001`) |

---

## Global Site Summary

| Code | Location | City & Country | LAN Subnet | Domain | Notes |
|------|----------|---------|-----------|--------|-------|
| ABD | Aberdeen | Scotland, UK | `192.168.224.0/24` | `example.org` | Satellite office |
| AMS | Amsterdam | Netherlands | `192.168.31.0/24` | `example.net` | |
| ATL | Athens, GA | USA | `192.168.33.0/24` | `example.net` | |
| BIR | Birmingham | England, UK | `192.168.121.0/24` | `example.net` | |
| BON | Bonn | West Germany (FRG) | `192.168.228.0/24` | `example.net` | Schema Master / Domain Naming Master |
| BRD | West Berlin | West Germany (FRG) | `192.168.113.0/24` | `example.net` | Legacy site |
| BRK | Brockville | Ontario, Canada | `192.168.136.0/24` | `example.net` | |
| CHI | Chicago | Illinois, USA | `192.168.214.0/24` | `example.net` | |
| CLD | Cloud / Provisioning (LAN) | Korsbaek, DK | `192.168.69.0/24` | `<blank / NULL>` | DCs, Ansible, WAC, PBX, UniFi controller (Rudder present but dormant, not in active use) |
| CLY | Clydebank | Scotland, UK | `192.168.41.0/24` | `example.net` | |
| COV | Coventry | England, UK | `192.168.247.0/24` | `example.net` | WAP/RTR only |
| CPH | København | Danmark | `192.168.231.0/24` | `example.com/net` | |
| DUN | Dundee | Scotland, UK | `192.168.138.0/24` | `example.net` | |
| EDI | Edinburgh | Scotland, UK | `192.168.131.0/24` | `example.org/net` | Multiple DCs — check replication health |
| FAL | Falkirk | Scotland, UK | `192.168.76.0/24` | `example.net` | **Head Office** — Brockville Stadium |
| FAX | Faxe | Danmark | `192.168.246.0/24` | `example.net` | |
| FRD | Fredericia Havn (standby vRACK) | Danmark | `172.16.124.0/24` | `<blank / NULL>` | Standby provisioning network — not `FRE`, the real Fredericia office. Legal fiction run off a MacBook (`http.server`), but has a real "site kit" too — NUC running Proxmox VE + a 48-port switch, see FRD row above |
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
| TOR | Toronto | Ontario, Canada | `192.168.146.0/24` | `example.net` | |
| VIE | Vienna | Austria | `192.168.78.0/24` | `example.net` | |
| VRK | OVH vRACK (Edinburgh) | Scotland, UK | `192.168.139.0/24` | `<blank / NULL>` | Provisioning network — DNS, PXE/provisioning server, FWL WAN face. Not a real office |
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
| `EXADCSTOR001` | TOR | example.net | `192.168.146.10` | — | ⚠️ DNS/Netlogon/KDC stopped |
| `EXADCSNYC001` | NYC | example.net | `192.168.212.10` | — | ⚠️ DNS/Netlogon/KDC stopped |
| `EXADCSNJC001` | NJC | example.net | `192.168.201.10` | — | ⚠️ DNS/Netlogon/KDC stopped |
| `EXADCSATL001` | ATL | example.net | `192.168.33.10` | — | ⚠️ DNS/Netlogon/KDC stopped |
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

### ☁️ Cloud / Provisioning — CLD / VRK / FRD

See the [Cloud / Provisioning Network — CLD / VRK / FRD](#cloud--provisioning-network--cld--vrk--frd) section above for the full breakdown (vRACK vs CLD LAN vs FRD standby).

---

### 🏴󠁧󠁢󠁳󠁣󠁴󠁿 United Kingdom — Scotland

---

#### FAL — Falkirk *(Head Office)*
**Address:** Brockville Stadium, 1876 Hope Street, Falkirk  
**LAN:** `192.168.76.0/24` · **VPN:** `10.0.76.0/24` · **Domain:** `example.net`

**Completion checklist:**
- [x] Switch installed and configured
- [x] Router installed and configured
- [x] Remote access console configured
- [x] Proxmox node provisioned
- [x] Firewall installed and configured (VM on Proxmox)
- [x] Domain Controller provisioned
- [ ] Proxmox node upgraded to ZFS RAID1
- [ ] VPN tunnel verified

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXAFWLFAL001` | Firewall | Debian Linux (PVE VM) | `192.168.76.253` | nftables + WireGuard — site-to-site VPN, replaced RTR's earlier VPN role. Same pattern at every site (Robert, 2026-08-04) |
| `EXASWIFAL001` | Switch | Cisco Catalyst 9300 | `192.168.76.250` | Core switch |
| `EXASWIFAL002` | Switch | Cisco Catalyst 9300 | `192.168.76.251` | Core switch 2 |
| `EXARTRFAL001` | Router | FortiGate | `192.168.76.1` | WAN edge — renamed/moved from `EXARTRFAL02` (`192.168.79.1/24`) when it took over primary-router duty from the decommissioned original Cisco ISR 4331 |
| `EXABMCFAL001` | BMC | — | `192.168.76.2` | Standard BMC slot 1 |
| `EXAPVEFAL001` | Proxmox | — | `192.168.76.5` | PVE node 1 |
| `EXADCSFAL001` | DC | — | `192.168.76.10` | Domain Controller |
| `EXASBCFAL001` | VOIP SBC | — | `192.168.76.48` | Trunks to `EXAPBXCLD001` |
| `EXANASFAL001` | NAS | TrueNAS SCALE | `192.168.76.19` | Site NAS/SAN — installed 2026-07-26, bare metal, replaces the retired legacy FreeNAS box (was `.32`) |
| `EXASRVFAL001` | Server | — | `192.168.76.20` | Reserved — standard convention slot, not yet in use |
| `EXATARFAL001` | Tape Archiver | Solaris Embedded | `192.168.76.33` | Legacy tape archive |

> The shared cross-site provisioning server (`192.168.139.50`) has no formal hostname or DNS record — bootstrap-only, IP-referenced only (see §4.1 of the Beginners Guide). It's not specific to this site, so it's not listed as an Infrastructure row above.

**Endpoints:**

| Hostname | Type | OS | IP | Notes |
|----------|------|----|----|-------|
| `EXAWKSFAL001` | Workstation | Windows 11 Pro 23H2 | `192.168.76.100` | Analog Mixing Desk v1 |
| `EXAWKSFAL002` | Workstation | Windows 11 Pro 23H2 | `192.168.76.101` | Reel-to-Reel Recorder 24-track |
| `EXAWKSFAL003` | Workstation | Windows 11 Pro 23H2 | `192.168.76.102` | Shared editing workstation |
| `EXALAPFAL001` | Laptop | Windows 11 Pro 23H2 | `192.168.76.103` | Production laptop |
| `EXASURFAL001` | Surface | Windows 11 23H2 | `192.168.76.104` | Microsoft Surface |

**WAPs:** `EXAWAPFAL001–006` · Ubiquiti UniFi U6-Pro — static, `.82`–`.87`

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

> This site also has legacy-naming domain controllers pending rebuild/decommission
> (`EXADCREDI002`/`EXADCREDI003`) — not shown below (this section covers current/live
> infrastructure only), see `docs/network-diagram/scotland.md`'s Old Network section for
> EDI and `at_have_ryggen_fri/check_dcr_devices.py`'s output for current status.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTREDI001` | Router | Cisco ISR 4331 | `192.168.131.1` | WAN edge |
| `EXAFWLEDI001` | Firewall | Debian Linux (PVE VM) | `192.168.131.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIEDI001` | Switch | Cisco Catalyst 2960X | `192.168.131.250` | Floor switch |
| `EXASWIEDI002` | Switch | Cisco Catalyst 2960X | `192.168.131.251` | 48-port |
| `EXABMCEDI001` | BMC | — | `192.168.131.2` | Standard BMC slot 1 |
| `EXAPVEEDI001` | Proxmox | — | `192.168.131.5` | PVE node 1 |
| `EXADCSEDI001` | DC | — | `192.168.131.10` | Domain Controller |
| `EXASBCEDI001` | VOIP SBC | — | `192.168.131.48` | Trunks to `EXAPBXCLD001` |
| `EXANASEDI001` | NAS | — | `192.168.131.19` | Standard NAS slot |
| `EXARDREDI001` | Badge reader | — | `192.168.131.21` | Standard RDR slot |

**Endpoints:**

| Hostname | Type | OS | IP | Notes |
|----------|------|----|----|-------|
| `EXAWKSEDI001` | Workstation | Windows 10 Pro 22H2 | `192.168.131.150` | Shared desktop |
| `EXALAPEDI098` | Laptop | Windows 11 Pro 24H2 | `192.168.131.108` | Pool laptop |

**WAPs:** `EXAWAPEDI001–002` · Ubiquiti UniFi U6-Pro — static, `.82`–`.83`

**IoT:** `EXATEAEDI001` — Siemens EQ700 Coffee Machine (`192.168.131.60`)

---

#### GLA — Glasgow
**LAN:** `192.168.141.0/24` · **Domain:** `example.net`

> This site also has a legacy-naming domain controller (`EXADCRGLA001`, Schema/Domain Naming
> Master, PDC Emulator) — not shown below (this section covers current/live infrastructure
> only), see `docs/network-diagram/scotland.md`'s Old Network section for GLA.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRGLA001` | Router | — | `192.168.141.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLGLA001` | Firewall | Debian Linux (PVE VM) | `192.168.141.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIGLA001` | Switch | — | `192.168.141.250` | Standard SWI slot 1 |
| `EXABMCGLA001` | BMC | — | `192.168.141.2` | Standard BMC slot 1 |
| `EXAPVEGLA001` | Proxmox | — | `192.168.141.5` | PVE node 1 |
| `EXADCSGLA001` | DC | — | `192.168.141.10` | Domain Controller |
| `EXASBCGLA001` | VOIP SBC | — | `192.168.141.48` | Trunks to `EXAPBXCLD001` |
| `EXANASGLA001` | NAS | — | `192.168.141.19` | Standard NAS slot |
| `EXARDRGLA001` | Badge reader | — | `192.168.141.21` | Standard RDR slot |
| `EXAPRNGLA001` | Printer | HP LaserJet Pro | `192.168.141.16` | Main floor printer |

**Endpoints:**

| Hostname | Type | OS | IP | Notes |
|----------|------|----|----|-------|
| `EXAWKSGLA001` | Workstation | Windows 11 Pro | `192.168.141.150` | Hot desk |
| `EXAWKSGLA002` | Workstation | Windows 11 Pro | `192.168.141.151` | Hot desk |
| `EXALAPGLA001` | Laptop | Windows 11 Pro | `192.168.141.152` | Pool device |

**WAPs:** `EXAWAPGLA001` · Ubiquiti UniFi U6-Pro — static, `.82`

---

#### CLY — Clydebank
**LAN:** `192.168.41.0/24` · **Domain:** `example.net`

> This site also has legacy-naming domain controllers (`EXADCRCLY001`/`EXADCRCLY002`,
> Primary/Secondary — neither ever had a host built) — not shown below (this section covers
> current/live infrastructure only), see `docs/network-diagram/scotland.md`'s Old Network
> section for CLY.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRCLY001` | Router | FortiOS 7.6.5 | `192.168.41.1` | WAN edge |
| `EXAFWLCLY001` | Firewall | Debian Linux (PVE VM) | `192.168.41.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWICLY001` | Switch | Cisco Catalyst 9300 | `192.168.41.250` | Core switch |
| `EXABMCCLY001` | BMC | — | `192.168.41.2` | Standard BMC slot 1 |
| `EXAPVECLY001` | Proxmox | — | `192.168.41.5` | PVE node 1 |
| `EXADCSCLY001` | DC | — | `192.168.41.10` | Domain Controller |
| `EXASRVCLY001` | Server | Rocky Linux | `192.168.41.20` | Oracle DB |
| `EXASBCCLY001` | VOIP SBC | — | `192.168.41.48` | Trunks to `EXAPBXCLD001` |
| `EXANASCLY001` | NAS | — | `192.168.41.19` | Standard NAS slot |
| `EXARDRCLY001` | Badge reader | — | `192.168.41.21` | Standard RDR slot |

**WAPs:** `EXAWAPCLY001–002` · Ubiquiti UniFi U6-Pro — static, `.82`–`.83`

**Endpoints:** `EXASURCLY001` (Surface), `EXAPHNCLY001` (iOS), `EXATABCLY001` (Android tablet)

---

#### DUN — Dundee
**LAN:** `192.168.138.0/24` · **Domain:** `example.net`

> This site also has a legacy-naming domain controller (`EXADCRDUN001`, Windows Server 2003,
> unmaintained) — not shown below (this section covers current/live infrastructure only), see
> `docs/network-diagram/scotland.md`'s Old Network section for DUN.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRDUN001` | Router | Cisco ISR 4331 | `192.168.138.1` | WAN edge |
| `EXAFWLDUN001` | Firewall | Debian Linux (PVE VM) | `192.168.138.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIDUN001` | Switch | — | `192.168.138.250` | Standard SWI slot 1 |
| `EXABMCDUN001` | BMC | — | `192.168.138.2` | Standard BMC slot 1 |
| `EXAPVEDUN001` | Proxmox | — | `192.168.138.5` | PVE node 1 |
| `EXADCSDUN001` | DC | — | `192.168.138.10` | Domain Controller |
| `EXASBCDUN001` | VOIP SBC | — | `192.168.138.48` | Trunks to `EXAPBXCLD001` |
| `EXANASDUN001` | NAS | — | `192.168.138.19` | Standard NAS slot |
| `EXARDRDUN001` | Badge reader | — | `192.168.138.21` | Standard RDR slot |

**WAPs:** `EXAWAPDUN001–002` · Ubiquiti UniFi U6-Pro — static, `.82`–`.83`

**Endpoints:** `EXASURDUN001–002` (Surface/Win11), `EXAPHNDUN001–002` (iOS)

---

#### PER — Perth
**LAN:** `192.168.173.0/24` · **Domain:** `example.net`

> This site also has a legacy-naming domain controller (`EXADCRPER001`, physical HP ML310e,
> never switched on) — not shown below (this section covers current/live infrastructure only),
> see `docs/network-diagram/scotland.md`'s Old Network section for PER.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRPER001` | Router | — | `192.168.173.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLPER001` | Firewall | Debian Linux (PVE VM) | `192.168.173.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIPER001` | Switch | — | `192.168.173.250` | Standard SWI slot 1 |
| `EXABMCPER001` | BMC | — | `192.168.173.2` | Standard BMC slot 1 |
| `EXAPVEPER001` | Proxmox | — | `192.168.173.5` | PVE node 1 |
| `EXADCSPER001` | DC | — | `192.168.173.10` | Domain Controller |
| `EXASBCPER001` | VOIP SBC | — | `192.168.173.48` | Trunks to `EXAPBXCLD001` |
| `EXANASPER001` | NAS | — | `192.168.173.19` | Standard NAS slot — the old Synology at `.50` this doc previously listed is retired |
| `EXARDRPER001` | Badge reader | — | `192.168.173.21` | Standard RDR slot |
| `EXANIXPER001` | Unix | Solaris 11.5 | `192.168.173.40` | MIDI/Music archive — Fiction Factory |
| `EXAPRNPER001` | Printer | HP MFP | `192.168.173.20` | — |

**WAPs:** `EXAWAPPER001` · Ubiquiti UniFi U6-Pro — static, `.82`

**Endpoints:** `EXAMBPPER001` (MacBook), `EXASURPER001` (Surface), `EXAPHNPER001–004` (Yealink T46G)

**IoT:** `EXAVNDPER001` (Scone Palace vending — Embedded SP100)

---

#### ABD — Aberdeen
**LAN:** `192.168.224.0/24` · **Domain:** `example.org`

> This site also has a legacy-naming domain controller (`EXADCRABD001`, Windows Server 2008R2,
> bare metal, no hypervisor layer) — not shown below (this section covers current/live
> infrastructure only), see `docs/network-diagram/scotland.md`'s Old Network section for ABD.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRABD001` | Router | Cisco ASA 5506-X | `192.168.224.1` | WAN edge |
| `EXAFWLABD001` | Firewall | Debian Linux (PVE VM) | `192.168.224.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIABD001` | Switch | — | `192.168.224.250` | Standard SWI slot 1 |
| `EXABMCABD001` | BMC | — | `192.168.224.2` | Standard BMC slot 1 |
| `EXAPVEABD001` | Proxmox | — | `192.168.224.5` | PVE node 1 |
| `EXADCSABD001` | DC | — | `192.168.224.10` | Domain Controller |
| `EXASBCABD001` | VOIP SBC | — | `192.168.224.48` | Trunks to `EXAPBXCLD001` |
| `EXANASABD001` | NAS | — | `192.168.224.19` | Standard NAS slot |
| `EXARDRABD001` | Badge reader | — | `192.168.224.21` | Standard RDR slot |

**WAPs:** `EXAWAPABD001–002` · Ubiquiti UniFi U6-Pro — static, `.82`–`.83`

**Endpoints:** `EXAMBPABD001–002` (MacBooks), `EXAPHNABD001–002` (iPhones)

---

### 🏴󠁧󠁢󠁥󠁮󠁧󠁿 United Kingdom — England

---

#### LND — London
**LAN:** `192.168.20.0/24` · **Domain:** `example.net`

> This site also has a legacy-naming domain controller (`EXADCRLND001`, RID/Infra Master) — not
> shown below (this section covers current/live infrastructure only), see
> `docs/network-diagram/england.md`'s Old Network section for LND.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRLND001` | Router | Cisco ASA 5516-X | `192.168.20.1` | WAN edge |
| `EXAFWLLND001` | Firewall | Debian Linux (PVE VM) | `192.168.20.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWILND001` | Switch | Cisco Catalyst 9300 | `192.168.20.250` | Core switch |
| `EXABMCLND001` | BMC | — | `192.168.20.2` | Standard BMC slot 1 |
| `EXAPVELND001` | Proxmox | — | `192.168.20.5` | PVE node 1 |
| `EXADCSLND001` | DC | — | `192.168.20.10` | Domain Controller |
| `EXASBCLND001` | VOIP SBC | — | `192.168.20.48` | Trunks to `EXAPBXCLD001` |
| `EXANASLND001` | NAS | — | `192.168.20.19` | Standard NAS slot |
| `EXARDRLND001` | Badge reader | — | `192.168.20.21` | Standard RDR slot |

**WAPs:** `EXAWAPLND001` · Ubiquiti UniFi U6-Pro — static, `.82`

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

> This site also has legacy-naming domain controllers (`EXADCRBIR001`/`EXADCRBIR002`,
> Primary/Secondary) — not shown below (this section covers current/live infrastructure only),
> see `docs/network-diagram/england.md`'s Old Network section for BIR.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRBIR001` | Router | Palo Alto PanOS | `192.168.121.1` | WAN edge |
| `EXAFWLBIR001` | Firewall | Debian Linux (PVE VM) | `192.168.121.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIBIR001` | Switch | Cisco Catalyst 9300 | `192.168.121.250` | Core switch |
| `EXASWIBIR002` | Switch | Cisco Catalyst 48-port | `192.168.121.251` | Access switch |
| `EXABMCBIR001` | BMC | — | `192.168.121.2` | Standard BMC slot 1 |
| `EXAPVEBIR001` | Proxmox | — | `192.168.121.5` | PVE node 1 |
| `EXADCSBIR001` | DC | — | `192.168.121.10` | Domain Controller |
| `EXASRVBIR001` | Server | Rocky Linux | `192.168.121.20` | Oracle DB |
| `EXASBCBIR001` | VOIP SBC | — | `192.168.121.48` | Trunks to `EXAPBXCLD001` |
| `EXANASBIR001` | NAS | — | `192.168.121.19` | Standard NAS slot |
| `EXARDRBIR001` | Badge reader | — | `192.168.121.21` | Standard RDR slot |

**WAPs:** `EXAWAPBIR001–002` · Ubiquiti UniFi U6-Pro — static, `.82`–`.83`

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

> This site also has legacy-naming domain controllers (`EXADCRMCR001`/`EXADCRMCR002`, PDC/RID/
> Infra Master and Secondary) — not shown below (this section covers current/live
> infrastructure only), see `docs/network-diagram/england.md`'s Old Network section for MCR.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRMCR001` | Router | — | `192.168.161.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLMCR001` | Firewall | Debian Linux (PVE VM) | `192.168.161.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIMCR001` | Switch | Cisco Catalyst 9300 | `192.168.161.250` | Distribution switch |
| `EXABMCMCR001` | BMC | — | `192.168.161.2` | Standard BMC slot 1 |
| `EXAPVEMCR001` | Proxmox | — | `192.168.161.5` | PVE node 1 |
| `EXADCSMCR001` | DC | — | `192.168.161.10` | Domain Controller |
| `EXASBCMCR001` | VOIP SBC | — | `192.168.161.48` | Trunks to `EXAPBXCLD001` |
| `EXANASMCR001` | NAS | — | `192.168.161.19` | Standard NAS slot |
| `EXARDRMCR001` | Badge reader | — | `192.168.161.21` | Standard RDR slot |

**WAPs:** `EXAWAPMCR001` · Ubiquiti UniFi U6-Pro — static, `.82`

**Endpoints:** `EXALAPMCR001` (Win11 laptop, `192.168.161.19` — shares NAS's standard octet, a
confirmed real exception), `EXALAPMCR002` (Win11 laptop, `.150`), `EXAWKSMCR001–002` (Win10
desktops, `.152`–`.153`), `EXAPRNMCR001` (printer, `.16`)

---

#### LIV — Liverpool
**LAN:** `192.168.151.0/24` · **Domain:** `example.org`

> This site also has a legacy-naming domain controller (`EXADCRLIV001`, WS2025, unauthorized
> build, also hosts file shares) — not shown below (this section covers current/live
> infrastructure only), see `docs/network-diagram/england.md`'s Old Network section for LIV.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRLIV001` | Router | — | `192.168.151.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLLIV001` | Firewall | Debian Linux (PVE VM) | `192.168.151.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWILIV001` | Switch | Cisco Catalyst 9200 | `192.168.151.250` | Core switch |
| `EXABMCLIV001` | BMC | — | `192.168.151.2` | Standard BMC slot 1 |
| `EXAPVELIV001` | Proxmox | — | `192.168.151.5` | PVE node 1 |
| `EXADCSLIV001` | DC | — | `192.168.151.10` | Domain Controller |
| `EXASBCLIV001` | VOIP SBC | — | `192.168.151.48` | Trunks to `EXAPBXCLD001` |
| `EXANASLIV001` | NAS | — | `192.168.151.19` | Standard NAS slot |
| `EXARDRLIV002` | Badge reader | — | `192.168.151.21` | HID Signo |

**WAPs:** `EXAWAPLIV001` · Ubiquiti UniFi U6-Pro — static, `.82`

**Endpoints:** `EXASVRLIV001` (Win Server 2022 file server), `EXAMBPLIV001` (MacBook Pro — macOS Tahoe), `EXAMACLIV001` (iMac — **disabled**)

**Security:** `EXABPSLIV001` (badge programming workstation, `192.168.151.17`)

---

#### NEW — Newcastle
**LAN:** `192.168.191.0/24` · **Domain:** `example.org`

> This site also has a legacy-naming domain controller (`EXADCRNEW001`, AD running, no real
> users/shares ever set up) — not shown below (this section covers current/live infrastructure
> only), see `docs/network-diagram/england.md`'s Old Network section for NEW.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRNEW001` | Router | — | `192.168.191.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLNEW001` | Firewall | Debian Linux (PVE VM) | `192.168.191.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWINEW001` | Switch | TP-Link JetStream | `192.168.191.250` | Access switch |
| `EXABMCNEW001` | BMC | — | `192.168.191.2` | Standard BMC slot 1 |
| `EXAPVENEW001` | Proxmox | — | `192.168.191.5` | PVE node 1 |
| `EXADCSNEW001` | DC | — | `192.168.191.10` | Domain Controller |
| `EXASBCNEW001` | VOIP SBC | — | `192.168.191.48` | Trunks to `EXAPBXCLD001` |
| `EXANASNEW001` | NAS | — | `192.168.191.19` | Standard NAS slot |

**WAPs:** `EXAWAPNEW001` · Ubiquiti UniFi U6-Pro — static, `.82`

**Endpoints:** `EXASRVNEW001` (Win Server 2022 file/print, `192.168.191.21` — real device sitting on RDR's usual standard octet; no separate badge reader confirmed built here), `EXAWKSNEW099` (Win11 — ⚠️ LAPS password expired)

---

#### COV — Coventry
**LAN:** `192.168.247.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRCOV001` | Router | Cisco ISR 4331 | `192.168.247.1` | WAN edge — no server infra at this site |
| `EXAFWLCOV001` | Firewall | Debian Linux (PVE VM) | `192.168.247.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWICOV001` | Switch | — | `192.168.247.250` | Standard SWI slot 1 |
| `EXABMCCOV001` | BMC | — | `192.168.247.2` | Standard BMC slot 1 |
| `EXAPVECOV001` | Proxmox | — | `192.168.247.5` | PVE node 1 |
| `EXADCSCOV001` | DC | — | `192.168.247.10` | Domain Controller |
| `EXASBCCOV001` | VOIP SBC | — | `192.168.247.48` | Trunks to `EXAPBXCLD001` |
| `EXANASCOV001` | NAS | — | `192.168.247.19` | Standard NAS slot |
| `EXARDRCOV001` | Badge reader | — | `192.168.247.21` | Standard RDR slot |

**WAPs:** `EXAWAPCOV001–002` · Ubiquiti UniFi U6-Pro — static, `.82`–`.83`

---

#### HAL — Halifax
**LAN:** `192.168.142.0/24` · **Domain:** `example.net`

> This site also has a legacy-naming domain controller (`EXADCRHAL001`, Windows Server on a
> Dell OptiPlex tower) — not shown below (this section covers current/live infrastructure
> only), see `docs/network-diagram/england.md`'s Old Network section for HAL.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRHAL001` | Router | — | `192.168.142.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLHAL001` | Firewall | Debian Linux (PVE VM) | `192.168.142.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIHAL001` | Switch | — | `192.168.142.250` | Standard SWI slot 1 |
| `EXABMCHAL001` | BMC | — | `192.168.142.2` | Standard BMC slot 1 |
| `EXAPVEHAL001` | Proxmox | — | `192.168.142.5` | PVE node 1 |
| `EXADCSHAL001` | DC | — | `192.168.142.10` | Domain Controller |
| `EXASBCHAL001` | VOIP SBC | — | `192.168.142.48` | Trunks to `EXAPBXCLD001` |
| `EXANASHAL001` | NAS | — | `192.168.142.19` | Standard NAS slot |
| `EXARDRHAL001` | Badge reader | — | `192.168.142.21` | Standard RDR slot |

**WAPs:** `EXAWAPHAL001` · Ubiquiti UniFi U6-Pro — static, `.82`

---

#### HUL — Hull
**LAN:** `192.168.148.0/24` · **Domain:** `example.net`

> This site also has a legacy-naming domain controller (`EXADCRHUL001`, Windows Server on a
> Dell OptiPlex tower) — not shown below (this section covers current/live infrastructure
> only), see `docs/network-diagram/england.md`'s Old Network section for HUL.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRHUL001` | Router | — | `192.168.148.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLHUL001` | Firewall | Debian Linux (PVE VM) | `192.168.148.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIHUL001` | Switch | — | `192.168.148.250` | Standard SWI slot 1 |
| `EXABMCHUL001` | BMC | — | `192.168.148.2` | Standard BMC slot 1 |
| `EXAPVEHUL001` | Proxmox | — | `192.168.148.5` | PVE node 1 |
| `EXADCSHUL001` | DC | — | `192.168.148.10` | Domain Controller |
| `EXASBCHUL001` | VOIP SBC | — | `192.168.148.48` | Trunks to `EXAPBXCLD001` |
| `EXANASHUL001` | NAS | — | `192.168.148.19` | Standard NAS slot |
| `EXARDRHUL001` | Badge reader | — | `192.168.148.21` | Standard RDR slot |

**WAPs:** `EXAWAPHUL001` · Ubiquiti UniFi U6-Pro — static, `.82`

---

#### SHE — Sheffield
**LAN:** `192.168.114.0/24` · **Domain:** `example.net`

> This site also has a legacy-naming domain controller (`EXADCRSHE001`, Windows Server on a
> Dell OptiPlex tower) — not shown below (this section covers current/live infrastructure
> only), see `docs/network-diagram/england.md`'s Old Network section for SHE.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRSHE001` | Router | — | `192.168.114.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLSHE001` | Firewall | Debian Linux (PVE VM) | `192.168.114.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWISHE001` | Switch | — | `192.168.114.250` | Standard SWI slot 1 |
| `EXABMCSHE001` | BMC | — | `192.168.114.2` | Standard BMC slot 1 |
| `EXAPVESHE001` | Proxmox | — | `192.168.114.5` | PVE node 1 |
| `EXADCSSHE001` | DC | — | `192.168.114.10` | Domain Controller |
| `EXASBCSHE001` | VOIP SBC | — | `192.168.114.48` | Trunks to `EXAPBXCLD001` |
| `EXANASSHE001` | NAS | — | `192.168.114.19` | Standard NAS slot |
| `EXARDRSHE001` | Badge reader | — | `192.168.114.21` | Standard RDR slot |

**WAPs:** `EXAWAPSHE001` · Ubiquiti UniFi U6-Pro — static, `.82`

---

### 🇩🇰 Danmark

---

#### CPH — København
**LAN:** `192.168.231.0/24` · **Domain:** `example.com` / `example.net`

> This site also has legacy-naming domain controllers (`EXADCRCPH001`/`EXADCRCPH002`,
> example.com/example.net) — not shown below (this section covers current/live infrastructure
> only), see `docs/network-diagram/danmark.md`'s Old Network section for CPH.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRCPH001` | Router | Cisco ISR 4331 | `192.168.231.1` | WAN edge |
| `EXAFWLCPH001` | Firewall | Debian Linux (PVE VM) | `192.168.231.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWICPH001` | Switch | TP-Link JetStream | `192.168.231.250` | Office switch |
| `EXABMCCPH001` | BMC | — | `192.168.231.2` | Standard BMC slot 1 |
| `EXAPVECPH001` | Proxmox | — | `192.168.231.5` | PVE node 1 |
| `EXADCSCPH001` | DC | — | `192.168.231.10` | Domain Controller |
| `EXASBCCPH001` | VOIP SBC | — | `192.168.231.48` | Trunks to `EXAPBXCLD001` |
| `EXANASCPH001` | NAS | — | `192.168.231.19` | Standard NAS slot |
| `EXARDRCPH001` | Badge reader | — | `192.168.231.21` | Standard RDR slot |

**WAPs:** `EXAWAPCPH001–003` · Ubiquiti UniFi U6-Pro — static, `.82`–`.84`

**IoT:** `EXACLKCPH001` (Meinberg LANTIME M300 NTP `192.168.231.18`), `EXATVSCPH001` (Bella Kronik 42X `192.168.231.17`)

---

#### ODE — Odense
**LAN:** `192.168.126.0/24` · **Domain:** `example.net`

> This site also has legacy-naming domain controllers (`EXADCRODE001`/`EXADCRODE002`, PDC/RID/
> Infra Master and Secondary) — not shown below (this section covers current/live infrastructure
> only), see `docs/network-diagram/danmark.md`'s Old Network section for ODE.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRODE001` | Router | Cisco ASA 5506-X | `192.168.126.1` | WAN edge |
| `EXAFWLODE001` | Firewall | Debian Linux (PVE VM) | `192.168.126.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIODE001` | Switch | — | `192.168.126.250` | Standard SWI slot 1 |
| `EXASWIODE002` | Switch | — | `192.168.126.251` | Second switch — confirmed real, vendor/model TBD |
| `EXABMCODE001` | BMC | — | `192.168.126.2` | Standard BMC slot 1 |
| `EXAPVEODE001` | Proxmox | — | `192.168.126.5` | PVE node 1 |
| `EXADCSODE001` | DC | — | `192.168.126.10` | Domain Controller |
| `EXASBCODE001` | VOIP SBC | — | `192.168.126.48` | Trunks to `EXAPBXCLD001` |
| `EXANASODE001` | NAS | — | `192.168.126.19` | Standard NAS slot |
| `EXARDRODE001` | Badge reader | — | `192.168.126.21` | Standard RDR slot |

**WAPs:** `EXAWAPODE001–002` · Ubiquiti UniFi U6-Pro — static, `.82`–`.83`

**Endpoints:** `EXAMACODE001` (iMac macOS Tahoe), `EXAMBPODE002` (MacBook Pro)

**IoT:** `EXAMUSODE001` — Jukebox (`192.168.126.60`)

---

#### KGE — Køge
**LAN:** `192.168.65.0/24` · **Domain:** `example.net`

> This site also has a legacy-naming domain controller (`EXADCRKGE001`, WS2016 EOL, 27 days out
> of sync, disk space low, bare metal) — not shown below (this section covers current/live
> infrastructure only), see `docs/network-diagram/danmark.md`'s Old Network section for KGE.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRKGE001` | Router | — | `192.168.65.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLKGE001` | Firewall | Debian Linux (PVE VM) | `192.168.65.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIKGE001` | Switch | — | `192.168.65.250` | Standard SWI slot 1 |
| `EXABMCKGE001` | BMC | — | `192.168.65.2` | Standard BMC slot 1 |
| `EXAPVEKGE001` | Proxmox | — | `192.168.65.5` | PVE node 1 |
| `EXADCSKGE001` | DC | — | `192.168.65.10` | Domain Controller |
| `EXASBCKGE001` | VOIP SBC | — | `192.168.65.48` | Trunks to `EXAPBXCLD001` |
| `EXANASKGE001` | NAS | — | `192.168.65.19` | Standard NAS slot |
| `EXARDRKGE001` | Badge reader | — | `192.168.65.21` | Standard RDR slot |
| `EXAPRNKGE001` | Printer | HP LaserJet MFP M528 | `192.168.65.16` | — |

**WAPs:** `EXAWAPKGE001` · Ubiquiti UniFi U6-Pro — static, `.82`

---

#### FAX — Faxe
**LAN:** `192.168.246.0/24` · **Domain:** `example.net`

> This site also has a legacy-naming domain controller (`EXADCRFAX001`, present but never used,
> bare metal) — not shown below (this section covers current/live infrastructure only), see
> `docs/network-diagram/danmark.md`'s Old Network section for FAX.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRFAX001` | Router | Cisco ISR 4331 | `192.168.246.1` | WAN edge |
| `EXAFWLFAX001` | Firewall | Debian Linux (PVE VM) | `192.168.246.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIFAX001` | Switch | — | `192.168.246.250` | Standard SWI slot 1 |
| `EXABMCFAX001` | BMC | — | `192.168.246.2` | Standard BMC slot 1 |
| `EXAPVEFAX001` | Proxmox | — | `192.168.246.5` | PVE node 1 |
| `EXADCSFAX001` | DC | — | `192.168.246.10` | Domain Controller |
| `EXASBCFAX001` | VOIP SBC | — | `192.168.246.48` | Trunks to `EXAPBXCLD001` |
| `EXANASFAX001` | NAS | — | `192.168.246.19` | Standard NAS slot |
| `EXARDRFAX001` | Badge reader | — | `192.168.246.21` | Standard RDR slot |

**WAPs:** `EXAWAPFAX001–002` · Ubiquiti UniFi U6-Pro — static, `.82`–`.83`

---

#### KOR — Korsør
**LAN:** `192.168.238.0/24` · **Domain:** `example.net`

> This site also has a legacy-naming domain controller (`EXADCRKOR001`, HP ML310e, bare metal)
> — not shown below (this section covers current/live infrastructure only), see
> `docs/network-diagram/danmark.md`'s Old Network section for KOR.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRKOR001` | Router | — | `192.168.238.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLKOR001` | Firewall | Debian Linux (PVE VM) | `192.168.238.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIKOR001` | Switch | — | `192.168.238.250` | Standard SWI slot 1 |
| `EXABMCKOR001` | BMC | — | `192.168.238.2` | Standard BMC slot 1 |
| `EXAPVEKOR001` | Proxmox | — | `192.168.238.5` | PVE node 1 |
| `EXADCSKOR001` | DC | — | `192.168.238.10` | Domain Controller |
| `EXASBCKOR001` | VOIP SBC | — | `192.168.238.48` | Trunks to `EXAPBXCLD001` |
| `EXANASKOR001` | NAS | — | `192.168.238.19` | Standard NAS slot |
| `EXARDRKOR001` | Badge reader | — | `192.168.238.21` | Standard RDR slot |

**WAPs:** `EXAWAPKOR001` · Ubiquiti UniFi U6-Pro — static, `.82`

---

### 🇩🇪 Deutschland

---

#### BON — Bonn
**LAN:** `192.168.228.0/24` · **Domain:** `example.net`

> This site also has a legacy-naming domain controller (`EXADCRBON001`, Schema Master, DN
> Master, HP ML310e bare metal) — not shown below (this section covers current/live
> infrastructure only), see `docs/network-diagram/deutschland.md`'s Old Network section for BON.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRBON001` | Router | Cisco ISR 4331 | `192.168.228.1` | WAN edge |
| `EXAFWLBON001` | Firewall | Debian Linux (PVE VM) | `192.168.228.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIBON001` | Switch | Cisco Catalyst 2960X | `192.168.228.250` | Office switch |
| `EXABMCBON001` | BMC | — | `192.168.228.2` | Standard BMC slot 1 |
| `EXAPVEBON001` | Proxmox | — | `192.168.228.5` | PVE node 1 |
| `EXADCSBON001` | DC | — | `192.168.228.10` | Domain Controller |
| `EXASBCBON001` | VOIP SBC | — | `192.168.228.48` | Trunks to `EXAPBXCLD001` |
| `EXANASBON001` | NAS | — | `192.168.228.19` | Standard NAS slot |
| `EXARDRBON001` | Badge reader | — | `192.168.228.21` | Standard RDR slot |

**WAPs:** `EXAWAPBON001–002` · Ubiquiti UniFi U6-Pro — static, `.82`–`.83`

**Endpoints:** `EXALAPBON001` (ThinkPad — **disabled**), `EXAWKSBON001` (Win11 finance), `EXALAPBON002` (Win11 finance)

**IoT:** `EXAVCUBON001` (Poly Studio X70 boardroom), `EXACAMBON001` (Axis P3245-LVE CCTV), `EXATVSBON001` (Samsung 65")

---

#### BRD — West Berlin
**LAN:** `192.168.113.0/24` · **Domain:** `example.net`

> **Being consolidated into BER** — relocating there, possible decommission after the move
> (Robert, 2026-07-31). This section reflects current state, not the post-move plan.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRBRD001` | Router | Cisco ISR 4331 | `192.168.113.1` | WAN edge |
| `EXAFWLBRD001` | Firewall | Debian Linux (PVE VM) | `192.168.113.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIBRD001` | Switch | — | `192.168.113.250` | Standard SWI slot 1 |
| `EXABMCBRD001` | BMC | — | `192.168.113.2` | Standard BMC slot 1 |
| `EXAPVEBRD001` | Proxmox | — | `192.168.113.5` | PVE node 1 |
| `EXADCSBRD001` | DC | — | `192.168.113.10` | Domain Controller |
| `EXASBCBRD001` | VOIP SBC | — | `192.168.113.48` | Trunks to `EXAPBXCLD001` |
| `EXANASBRD001` | NAS | — | `192.168.113.19` | Standard NAS slot |
| `EXARDRBRD001` | Badge reader | — | `192.168.113.21` | Standard RDR slot |

**WAPs:** `EXAWAPBRD001–002` · Ubiquiti UniFi U6-Pro — static, `.82`–`.83`

**Endpoints:** `EXASRVBRD001` (legacy app server, Windows Server 2019), `EXANIXBRD001` (Debian 12 server)

---

#### MUN — Munich
**LAN:** `192.168.189.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRMUN001` | Router | — | `192.168.189.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLMUN001` | Firewall | Debian Linux (PVE VM) | `192.168.189.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIMUN001` | Switch | Cisco Catalyst 9200 | `192.168.189.250` | Access switch |
| `EXABMCMUN001` | BMC | — | `192.168.189.2` | Standard BMC slot 1 |
| `EXAPVEMUN001` | Proxmox | — | `192.168.189.5` | PVE node 1 |
| `EXADCSMUN001` | DC | — | `192.168.189.10` | Domain Controller |
| `EXASBCMUN001` | VOIP SBC | — | `192.168.189.48` | Trunks to `EXAPBXCLD001` |
| `EXANASMUN001` | NAS | — | `192.168.189.19` | Standard NAS slot |
| `EXARDRMUN001` | Badge reader | — | `192.168.189.21` | Standard RDR slot |

**WAPs:** `EXAWAPMUN001` · Ubiquiti UniFi U6-Pro — static, `.82`

**Endpoints:** `EXAWKSMUN001` (Win11 hot desk), `EXALAPMUN001` (Win11 pool), `EXALAPMUN002` (Win11 — ⚠️ LAPS expired)

---

#### DRS — Dresden
**LAN:** `192.168.153.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRDRS001` | Router | — | `192.168.153.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLDRS001` | Firewall | Debian Linux (PVE VM) | `192.168.153.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIDRS001` | Switch | — | `192.168.153.250` | Standard SWI slot 1 |
| `EXABMCDRS001` | BMC | — | `192.168.153.2` | Standard BMC slot 1 |
| `EXAPVEDRS001` | Proxmox | — | `192.168.153.5` | PVE node 1 |
| `EXADCSDRS001` | DC | — | `192.168.153.10` | Domain Controller |
| `EXASBCDRS001` | VOIP SBC | — | `192.168.153.48` | Trunks to `EXAPBXCLD001` |
| `EXANASDRS001` | NAS | — | `192.168.153.19` | Standard NAS slot |
| `EXARDRDRS001` | Badge reader | — | `192.168.153.21` | Standard RDR slot |

**WAPs:** `EXAWAPDRS001` · Ubiquiti UniFi U6-Pro — static, `.82`

---

#### DUS — Düsseldorf
**LAN:** `192.168.211.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRDUS001` | Router | — | `192.168.211.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLDUS001` | Firewall | Debian Linux (PVE VM) | `192.168.211.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIDUS001` | Switch | — | `192.168.211.250` | Standard SWI slot 1 |
| `EXABMCDUS001` | BMC | — | `192.168.211.2` | Standard BMC slot 1 |
| `EXAPVEDUS001` | Proxmox | — | `192.168.211.5` | PVE node 1 |
| `EXADCSDUS001` | DC | — | `192.168.211.10` | Domain Controller |
| `EXASBCDUS001` | VOIP SBC | — | `192.168.211.48` | Trunks to `EXAPBXCLD001` |
| `EXANASDUS001` | NAS | — | `192.168.211.19` | Standard NAS slot |
| `EXARDRDUS001` | Badge reader | — | `192.168.211.21` | Standard RDR slot |

**WAPs:** `EXAWAPDUS001` · Ubiquiti UniFi U6-Pro — static, `.82`

---

### 🇸🇪 Sverige

---

#### GOT — Gothenburg
**LAN:** `192.168.46.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRGOT001` | Router | — | `192.168.46.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLGOT001` | Firewall | Debian Linux (PVE VM) | `192.168.46.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIGOT001` | Switch | — | `192.168.46.250` | Standard SWI slot 1 |
| `EXABMCGOT001` | BMC | — | `192.168.46.2` | Standard BMC slot 1 |
| `EXAPVEGOT001` | Proxmox | — | `192.168.46.5` | PVE node 1 |
| `EXADCSGOT001` | DC | — | `192.168.46.10` | Domain Controller |
| `EXASBCGOT001` | VOIP SBC | — | `192.168.46.48` | Trunks to `EXAPBXCLD001` |
| `EXANASGOT001` | NAS | — | `192.168.46.19` | Standard NAS slot |
| `EXARDRGOT001` | Badge reader | — | `192.168.46.21` | Standard RDR slot |

**WAPs:** `EXAWAPGOT001` · Ubiquiti UniFi U6-Pro — static, `.82`

---

### 🇳🇴 Norge

---

#### OSL — Oslo
**LAN:** `192.168.47.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTROSL001` | Router | — | `192.168.47.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLOSL001` | Firewall | Debian Linux (PVE VM) | `192.168.47.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIOSL001` | Switch | — | `192.168.47.250` | Standard SWI slot 1 |
| `EXABMCOSL001` | BMC | — | `192.168.47.2` | Standard BMC slot 1 |
| `EXAPVEOSL001` | Proxmox | — | `192.168.47.5` | PVE node 1 |
| `EXADCSOSL001` | DC | — | `192.168.47.10` | Domain Controller |
| `EXASBCOSL001` | VOIP SBC | — | `192.168.47.48` | Trunks to `EXAPBXCLD001` |
| `EXANASOSL001` | NAS | — | `192.168.47.19` | Standard NAS slot |
| `EXARDROSL001` | Badge reader | — | `192.168.47.21` | Standard RDR slot |

**WAPs:** `EXAWAPOSL001` · Ubiquiti UniFi U6-Pro — static, `.82`

---

### 🇳🇱 Nederland

---

#### AMS — Amsterdam
**LAN:** `192.168.31.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRAMS001` | Router | — | `192.168.31.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLAMS001` | Firewall | Debian Linux (PVE VM) | `192.168.31.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIAMS001` | Switch | — | `192.168.31.250` | Standard SWI slot 1 |
| `EXABMCAMS001` | BMC | — | `192.168.31.2` | Standard BMC slot 1 |
| `EXAPVEAMS001` | Proxmox | — | `192.168.31.5` | PVE node 1 |
| `EXADCSAMS001` | DC | — | `192.168.31.10` | Domain Controller |
| `EXASBCAMS001` | VOIP SBC | — | `192.168.31.48` | Trunks to `EXAPBXCLD001` |
| `EXANASAMS001` | NAS | — | `192.168.31.19` | Standard NAS slot |
| `EXARDRAMS001` | Badge reader | — | `192.168.31.21` | Standard RDR slot |

**WAPs:** `EXAWAPAMS001` · Ubiquiti UniFi U6-Pro — static, `.82`

---

### 🇮🇹 Italia

---

#### MIL — Milan
**LAN:** `192.168.39.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRMIL001` | Router | — | `192.168.39.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLMIL001` | Firewall | Debian Linux (PVE VM) | `192.168.39.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIMIL001` | Switch | — | `192.168.39.250` | Standard SWI slot 1 |
| `EXABMCMIL001` | BMC | — | `192.168.39.2` | Standard BMC slot 1 |
| `EXAPVEMIL001` | Proxmox | — | `192.168.39.5` | PVE node 1 |
| `EXADCSMIL001` | DC | — | `192.168.39.10` | Domain Controller |
| `EXASBCMIL001` | VOIP SBC | — | `192.168.39.48` | Trunks to `EXAPBXCLD001` |
| `EXANASMIL001` | NAS | — | `192.168.39.19` | Standard NAS slot |
| `EXARDRMIL001` | Badge reader | — | `192.168.39.21` | Standard RDR slot |

**WAPs:** `EXAWAPMIL001` · Ubiquiti UniFi U6-Pro — static, `.82`

---

### 🇦🇹  Österreich

---

#### VIE — Vienna
**LAN:** `192.168.78.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRVIE001` | Router | — | `192.168.78.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLVIE001` | Firewall | Debian Linux (PVE VM) | `192.168.78.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIVIE001` | Switch | — | `192.168.78.250` | Standard SWI slot 1 |
| `EXABMCVIE001` | BMC | — | `192.168.78.2` | Standard BMC slot 1 |
| `EXAPVEVIE001` | Proxmox | — | `192.168.78.5` | PVE node 1 |
| `EXADCSVIE001` | DC | — | `192.168.78.10` | Domain Controller |
| `EXASBCVIE001` | VOIP SBC | — | `192.168.78.48` | Trunks to `EXAPBXCLD001` |
| `EXANASVIE001` | NAS | — | `192.168.78.19` | Standard NAS slot |
| `EXARDRVIE001` | Badge reader | — | `192.168.78.21` | Standard RDR slot |

**WAPs:** `EXAWAPVIE001` · Ubiquiti UniFi U6-Pro — static, `.82`

---

### 🇱🇧 Lebanon

---

#### BRT — Beirut
**LAN:** `192.168.169.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRBRT001` | Router | — | `192.168.169.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLBRT001` | Firewall | Debian Linux (PVE VM) | `192.168.169.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIBRT001` | Switch | — | `192.168.169.250` | Standard SWI slot 1 |
| `EXABMCBRT001` | BMC | — | `192.168.169.2` | Standard BMC slot 1 |
| `EXAPVEBRT001` | Proxmox | — | `192.168.169.5` | PVE node 1 |
| `EXADCSBRT001` | DC | — | `192.168.169.10` | Domain Controller |
| `EXASBCBRT001` | VOIP SBC | — | `192.168.169.48` | Trunks to `EXAPBXCLD001` |
| `EXANASBRT001` | NAS | — | `192.168.169.19` | Standard NAS slot |
| `EXARDRBRT001` | Badge reader | — | `192.168.169.21` | Standard RDR slot |

**WAPs:** `EXAWAPBRT001` · Ubiquiti UniFi U6-Pro — static, `.82`

---

### 🇨🇦 Canada

---

#### BRK — Brockville, Ontario
**LAN:** `192.168.136.0/24` · **Domain:** `example.net`

> This site also has a legacy-naming domain controller (`EXADCRBRK001`, DNS/Netlogon/KDC
> services stopped, hosted on the vCenter cluster) — not shown below (this section covers
> current/live infrastructure only), see `docs/network-diagram/canada.md`'s Old Network section
> for BRK.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRBRK001` | Router | Cisco ISR 4331 | `192.168.136.1` | WAN edge |
| `EXAFWLBRK001` | Firewall | Debian Linux (PVE VM) | `192.168.136.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIBRK001` | Switch | — | `192.168.136.250` | Standard SWI slot 1 |
| `EXASWIBRK002` | Switch | — | `192.168.136.251` | Second switch — confirmed real, vendor/model TBD |
| `EXABMCBRK001` | BMC | — | `192.168.136.2` | Standard BMC slot 1 |
| `EXAPVEBRK001` | Proxmox | — | `192.168.136.5` | PVE node 1 |
| `EXADCSBRK001` | DC | — | `192.168.136.10` | Domain Controller |
| `EXASBCBRK001` | VOIP SBC | — | `192.168.136.48` | Trunks to `EXAPBXCLD001` |
| `EXANASBRK001` | NAS | — | `192.168.136.19` | Standard NAS slot |

**WAPs:** `EXAWAPBRK001` · Ubiquiti UniFi U6-Pro — static, `.82`

**Endpoints:** `EXALAPBRK001` (Win11 tour laptop, `192.168.136.21` — real device sitting on RDR's usual standard octet; no separate badge reader confirmed built here), `EXAVNDBRK001` (Maple syrup vending — XPe)

**IoT:** `EXADONBRK001` (Tim Hortons Donut vending — VxWorks `192.168.136.60`)

---

#### TOR — Toronto, Ontario
**LAN:** `192.168.146.0/24` · **Domain:** `example.net`

> This site also has two legacy-naming domain controllers — `EXADCRTOR001` (DNS/Netlogon/KDC
> services stopped, on DHCP, HP ML310e bare metal) and `EXADCRTOR028` (undocumented legacy AD
> install, no-one on record knew it existed until found; HostOctet genuinely unknown, needs
> on-site discovery) — not shown below (this section covers current/live infrastructure only),
> see `docs/network-diagram/canada.md`'s Old Network section for TOR and
> `at_have_ryggen_fri/check_dcr_devices.py`'s output for current status.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRTOR001` | Router | — | `192.168.146.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLTOR001` | Firewall | Debian Linux (PVE VM) | `192.168.146.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWITOR001` | Switch | — | `192.168.146.250` | Standard SWI slot 1 |
| `EXABMCTOR001` | BMC | — | `192.168.146.2` | Standard BMC slot 1 |
| `EXAPVETOR001` | Proxmox | — | `192.168.146.5` | PVE node 1 |
| `EXADCSTOR001` | DC | — | `192.168.146.10` | Domain Controller |
| `EXASBCTOR001` | VOIP SBC | — | `192.168.146.48` | Trunks to `EXAPBXCLD001` |
| `EXANASTOR001` | NAS | — | `192.168.146.19` | Standard NAS slot |
| `EXARDRTOR001` | Badge reader | — | `192.168.146.21` | Standard RDR slot |

**WAPs:** `EXAWAPTOR001` · Ubiquiti UniFi U6-Pro — static, `.82`

---

#### MTL — Montreal, Quebec
**LAN:** `192.168.154.0/24` · **Domain:** `example.net`

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXARTRMTL001` | Router | — | `192.168.154.1` | WAN edge — vendor not yet confirmed |
| `EXAFWLMTL001` | Firewall | Debian Linux (PVE VM) | `192.168.154.253` | nftables + WireGuard — site-to-site VPN |
| `EXASWIMTL001` | Switch | — | `192.168.154.250` | Standard SWI slot 1 |
| `EXABMCMTL001` | BMC | — | `192.168.154.2` | Standard BMC slot 1 |
| `EXAPVEMTL001` | Proxmox | — | `192.168.154.5` | PVE node 1 |
| `EXADCSMTL001` | DC | — | `192.168.154.10` | Domain Controller |
| `EXASBCMTL001` | VOIP SBC | — | `192.168.154.48` | Trunks to `EXAPBXCLD001` |
| `EXANASMTL001` | NAS | — | `192.168.154.19` | Standard NAS slot |
| `EXARDRMTL001` | Badge reader | — | `192.168.154.21` | Standard RDR slot |

**WAPs:** `EXAWAPMTL001` · Ubiquiti UniFi U6-Pro — static, `.82`

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
| `EXASBCLAX001` | VOIP SBC | 3CX SBC Debian | `192.168.213.48` | Trunks to `EXAPBXCLD001` |

**WAPs:** `EXAWAPLAX001–003` · Ubiquiti UniFi U6-Pro — static, `.82`–`.94` range (see [Standard IP Convention](#standard-ip-convention))

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
| `EXASBCNYC001` | VOIP SBC | 3CX SBC Debian | `192.168.212.48` | Trunks to `EXAPBXCLD001` |

---

#### NJC — Camden, New Jersey
**LAN:** `192.168.201.0/24` · **Domain:** `example.net`

> ⚠️ `EXADCSNJC001` — DNS, Netlogon and KDC services stopped.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSNJC001` | DC | Windows Server 2022 | `192.168.201.10` | ⚠️ Services stopped |
| `EXASBCNJC001` | VOIP SBC | 3CX SBC Debian | `192.168.201.48` | Trunks to `EXAPBXCLD001` |

---

#### MIA — Miami, Florida
**LAN:** `192.168.135.0/24` · **Domain:** `example.net`

**Endpoints:** `EXALAPMIA001` (MacBook — macOS Sonoma)

**IoT:** `EXACOFMIA001` (Cuban Covfefe machine — VxWorks `192.168.135.60`)

---

#### ATL — Athens, Georgia
**LAN:** `192.168.33.0/24` · **Domain:** `example.net`

> ⚠️ `EXADCSATL001` — DNS, Netlogon and KDC services stopped.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSATL001` | DC | Windows Server 2022 | `192.168.33.10` | ⚠️ Services stopped |
| `EXASBCATL001` | VOIP SBC | 3CX SBC Debian | `192.168.33.48` | Trunks to `EXAPBXCLD001` |

---

#### CHI — Chicago, Illinois
**LAN:** `192.168.214.0/24` · **Domain:** `example.net`

> ⚠️ `EXADCSCHI001` — DNS, Netlogon and KDC services stopped.

**Infrastructure:**

| Hostname | Role | OS / Model | IP | Notes |
|----------|------|------------|----|-------|
| `EXADCSCHI001` | DC | Windows Server 2022 | `192.168.214.10` | ⚠️ Services stopped |
| `EXASBCCHI001` | VOIP SBC | 3CX SBC Debian | `192.168.214.48` | Trunks to `EXAPBXCLD001` |

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
| `EXASBCSYD001` | VOIP SBC | 3CX SBC | `192.168.29.48` | Trunks to `EXAPBXCLD001` |

**WAPs:** `EXAWAPSYD001` · Ubiquiti UniFi — static, `.82`–`.94` range (see [Standard IP Convention](#standard-ip-convention))

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
| `EXASBCMEL001` | VOIP SBC | 3CX SBC | `192.168.61.48` | Trunks to `EXAPBXCLD001` |

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
| `EXASBCAKL001` | VOIP SBC | 3CX SBC | `192.168.93.48` | Trunks to `EXAPBXCLD001` |

**WAPs:** `EXAWAPAKL001`, `EXAWAPAKL002` · Ubiquiti UniFi — static, `.82`–`.94` range (see [Standard IP Convention](#standard-ip-convention))

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
| `EXASRV` | Server | `EXADNSVRK001` |
| `EXARAC` | Remote Access Console (DRAC/iLO/RAC emulator) | `EXARACFAL001` |
| `EXANAS` | NAS/SAN storage (e.g. TrueNAS) — standard `.19` slot | `EXANAS<SITE>001` |
| `EXASBC` | VOIP SBC — trunks to `EXAPBXCLD001` | `EXASBCFAL001` |
| `EXAPBX` | PBX | `EXAPBXCLD001` |
| `TMP` | Provisioning / bootstrap server — VRK/FRD only, not a per-site convention (was `PRV`, retired as a per-site convention 2026-07-19; VRK/FRD's own two devices deliberately given no formal hostname 2026-07-21) | `192.168.139.50` (VRK), `172.16.124.1` (FRD) — IP only |
| `EXAWAP` | WiFi Access Point | `EXAWAPFAL001` |
| `EXAUFC` | UniFi Network Controller (CLD only — manages every site's WAPs) | `EXAUFCCLD001` |
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
