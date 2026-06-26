# Example Music Limited — Per-Site Network Diagrams

> **Classification:** Internal — Infrastructure  
> **Generated:** 2026-03-06  
> **Note:** WAPs and cameras confirmed at all 42 sites — marked TODO where full inventory pending.  
> Legend: ⭐ = 3-node hub · ⚠️ = issue flagged · 🔴 = DC services stopped

---

## Table of Contents

### ☁️ Cloud (CLD)
- [CLD — Cloud / Provisioning](#cld--cloud--provisioning)

### 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland
- [FAL — Falkirk *(Head Office)*](#fal--falkirk-head-office-)
- [EDI — Edinburgh](#edi--edinburgh-)
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
- [ODE — Odense *(EU Hub)*](#ode--odense-eu-hub-)
- [KGE — Køge](#kge--kge-)
- [FAX — Faxe](#fax--faxe)
- [KOR — Korsør](#kor--korsr)

### 🇩🇪 Deutschland
- [BON — Bonn](#bon--bonn)
- [BER — West Berlin](#ber--west-berlin)
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
- [BRK — Brockville *(NA/APAC Hub)*](#brk--brockville-naapac-hub-)
- [TOR — Toronto](#tor--toronto-)
- [MTL — Montreal](#mtl--montreal)

### 🇺🇸 United States
- [LAX — Los Angeles](#lax--los-angeles-)
- [NYC — New York](#nyc--new-york-)
- [NJC — New Jersey](#njc--new-jersey-)
- [MIA — Miami](#mia--miami)
- [ATL — Athens GA](#atl--athens-ga-)
- [CHI — Chicago](#chi--chicago-)

### 🇦🇺 Australia
- [SYD — Sydney](#syd--sydney-)
- [MEL — Melbourne](#mel--melbourne-)

### 🇳🇿 New Zealand
- [AKL — Auckland](#akl--auckland-)

---

---

## ☁️  — Cloud / Provisioning

**LAN:** `192.168.139.0/24` · **WireGuard VPN:** `10.0.139.0/24`  
**Role:** WireGuard hub — routes to all sites. Central PBX, Ansible, Rudder, WAC.

```mermaid
graph TD
    INET(("🌐 Internet"))
    FWLCLD["EXAFWLCLD001\nFirewall / WireGuard Hub\n192.168.139.1"]
    DNS["EXADNSCLD001\nDNS / BIND9 Server\n192.168.139.8"]
    RUD["EXARUDCLD001\nRudder Server\n192.168.139.12"]
    WAC["EXASVRCLD002\nWindows Admin Centre\n192.168.139.20"]
    PBX["EXACLDPBX001\n3CX Central PBX\n192.168.139.48"]
    PRV["EXAPRVCLD001\nProvisioning Server\n192.168.139.50"]
    ANS["EXAANSCLD001\nAnsible Control Node\n192.168.139.9"]

    VPN_FAL(["🔗 WireGuard → FAL primary"])
    VPN_ODE(["🔗 WireGuard → ODE EU backup"])
    VPN_BRK(["🔗 WireGuard → BRK NA/APAC backup"])

    INET --> FWLCLD
    FWLCLD --> DNS
    FWLCLD --> RUD
    FWLCLD --> WAC
    FWLCLD --> PBX
    FWLCLD --> PRV
    FWLCLD --> ANS
    FWLCLD --> VPN_FAL
    FWLCLD --> VPN_ODE
    FWLCLD --> VPN_BRK

    classDef server fill:#1a1a2e,stroke:#4fc3f7,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    classDef vpn fill:#0d3b2e,stroke:#66bb6a,color:#e8f5e9
    classDef inet fill:#333,stroke:#aaa,color:#fff
    class FWLCLD,DNS,WAC,PBX,PRV,ANS server
    class RUD rudder
    class VPN_FAL,VPN_ODE,VPN_BRK vpn
    class INET inet
```

---

---

## 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland

---

## FAL — Falkirk *(Head Office)* ⭐

**Address:** Brockville Stadium, Hope Street, Falkirk  
**LAN:** `192.168.76.0/24` · **VPN:** `10.0.76.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (hub) · **VPN parent:** CLD (primary head node)

```mermaid
graph TD
    INET(("🌐 Internet"))
    RTR["EXARTRFAL001\nCisco ISR 4331\n.254"]
    FWL["EXAFWLFAL001\nFortiOS\n.1"]
    SW1["EXASWIFAL001\nCisco 9300\n.250"]
    SW2["EXASWIFAL002\nCisco 9300\n.251"]

    subgraph BMC ["BMC Pool"]
        RAC1["EXARACFAL001\nDell iDRAC9\n.2"]
        RAC2["EXARACFAL002\nDell iDRAC9\n.3"]
        RAC3["EXARACFAL003\nDell iDRAC9\n.4"]
    end

    subgraph PVE ["Proxmox Cluster (3-node)"]
        PVE1["EXAPVEFAL001\nProxmox node 1\n.5"]
        PVE2["EXAPVEFAL002\nProxmox node 2\n.6"]
        PVE3["EXAPVEFAL003\nProxmox node 3\n.7"]
    end

    subgraph DC ["Domain Controllers"]
        DC1["EXADCSFAL001\nDC · PDC Emulator\n.10"]
        DC2["EXADCSFAL002\nDC secondary\n.11"]
    end

    subgraph INFRA ["Infrastructure"]
        SBC["EXASBCFAL001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYFAL001\nRudder Relay\n.12"]
        NAS["EXANASFAL001\nFreeNAS 13.0-U6\n.32"]
        TAR["EXATARFAL001\nTape Archiver\n.33"]
    end

    subgraph ENDPOINTS ["Endpoints"]
        WKS1["EXAWKSFAL001\nMixing Desk WKS\n.100"]
        WKS2["EXAWKSFAL002\nReel-to-Reel WKS\n.101"]
        WKS3["EXAWKSFAL003\nShared Editing WKS\n.102"]
        LAP["EXALAPFAL001\nProduction Laptop\n.103"]
        SUR["EXASURFAL001\nMicrosoft Surface\n.104"]
        PHN["EXAPHNFAL001-003\nStaff Phones"]
        PHN2["EXAPHNFAL006-007\nYealink T58A"]
        TAB["EXATABFAL001\nTablet"]
    end

    subgraph WAP_CAM ["Wireless & Security"]
        WAP["WAPs x6\nUbiquiti UniFi U6-Pro\n.5-.10"]
        CAM1["EXACAMFAL001\nAxis · Front entrance\n.70"]
        CAM2["EXACAMFAL002\nAxis · Studio hallway\n.71"]
        CAM3["EXACAMFAL003\nAxis · Car park\n.72"]
        CAM4["EXACAMFAL004\nAxis · Loading bay\n.73"]
        RDR["EXARDRFAL001\nHID Signo Badge Reader\n.16"]
    end

    subgraph SITE ["Site-Specific Equipment"]
        LCD["EXALCDFAL001\nSamsung Tizen Display\n.50"]
        VCU["EXAVCUFAL001\nPoly Studio X70\n.51"]
        JKB["EXAMUSFAL001\nPureline 128V Jukebox\n.67"]
        PAY["EXAPAYFAL001\nGPO Kiosk No.6 Payphone\n.95"]
        COF["EXATEAFAL001\nSmart Coffee Machine\n.61"]
        VND1["EXADONFAL001\nTim Hortons Vending\n.62"]
        VND2["EXAVNDFAL002\nIrn-Bru Machine\n.63"]
        VND3["EXAVNDFAL003\nMcCowans Dispenser\n.64"]
        VND4["EXAVNDFAL004\nMrs Tily Dispenser\n.65"]
        VND5["EXAVNDFAL005\n¼lb Confectionery\n.66"]
        PMP["EXAPMPFAL001\nNetworked Petrol Pump\n.60"]
        CLK["EXACLKFAL001\nNTP Clock\n.80"]
    end

    VPN_CLD(["🔗 WireGuard ← CLD\n10.0.76.0/24"])

    INET --> RTR --> FWL --> SW1 & SW2
    SW1 --> PVE1 & PVE2 & PVE3
    SW1 --> DC1 & DC2
    SW1 --> SBC & NAS & TAR
    SW2 --> ENDPOINTS
    SW2 --> WAP_CAM
    SW2 --> SITE
    RAC1 -.->|"manages"| PVE1
    RAC2 -.->|"manages"| PVE2
    RAC3 -.->|"manages"| PVE3
    FWL <-->|"WireGuard tunnel"| VPN_CLD

    SW1 --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN_CLD
    classDef net fill:#0d3b2e,stroke:#66bb6a,color:#e8f5e9
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef site fill:#880e4f,stroke:#f48fb1,color:#fce4ec
    classDef bmc fill:#bf360c,stroke:#ff8a65,color:#fbe9e7
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class RTR,FWL,SW1,SW2 net
    class PVE1,PVE2,PVE3,DC1,DC2,SBC,NAS,TAR srv
    class RRY rudder
    class WKS1,WKS2,WKS3,LAP,SUR,PHN,PHN2,TAB,WAP,CAM1,CAM2,CAM3,CAM4,RDR ep
    class LCD,VCU,JKB,PAY,COF,VND1,VND2,VND3,VND4,VND5,PMP,CLK site
    class RAC1,RAC2,RAC3 bmc
    class VPN_CLD vpn
```

---

## EDI — Edinburgh ⚠️

**LAN:** `192.168.131.0/24` · **Domain:** `example.org` / `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
> ⚠️ `EXADCSEDI003` — DFSR stopped, C: drive at 5% free. Immediate action required.

```mermaid
graph TD
    INET(("🌐 Internet"))
    RTR["EXARTREDI001\nCisco ISR 4331\n.254"]
    SW1["EXASWIEDI001\nCisco 2960X\n.250"]
    SW2["EXASWIEDI002\nCisco 2960X\n.251"]
    RAC["EXARACEDI001\nDell iDRAC9\n.2"]
    PVE["EXAPVEEDI001\nProxmox node 1\n.5"]
    DC["⚠️ EXADCSEDI003\nDC · DFSR stopped\nC: 5% free · .11"]
    SBC["EXASBCEDI001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYEDI001\nRudder Relay\n.12"]
    WKS["EXAWKSEDI001\nWorkstation\n.150"]
    LAP["EXALAPEDI098\nPool Laptop\n.108"]
    WAP["WAPs x2\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    COF["EXATEAEDI001\nSiemens EQ700 Coffee Machine\n.60"]
    VPN(["🔗 WireGuard → FAL"])

    INET --> RTR --> SW1 & SW2
    SW1 --> PVE --> DC
    SW1 --> SBC
    RAC -.->|"manages"| PVE
    SW2 --> WKS & LAP & WAP & CAM & COF
    RTR <-->|"WireGuard tunnel"| VPN

    SW1 --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class RTR,SW1,SW2 net
    class DC warn
    class PVE,SBC,RAC srv
    class RRY rudder
    class WKS,LAP,WAP,CAM,COF ep
    class VPN vpn
```

---

## GLA — Glasgow

**LAN:** `192.168.141.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL

```mermaid
graph TD
    INET(("🌐 Internet"))
    PVE["EXAPVEGLA001\nProxmox node 1\n.5"]
    RAC["EXARACGLA001\nBMC node 1\n.2"]
    DC["EXADCRGLA001\nDC · Schema/DN Master\nPDC Emulator · .10"]
    SBC["EXASBCGLA001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYGLA001\nRudder Relay\n.12"]
    WKS1["EXAWKSGLA001\nHot Desk WKS\n.150"]
    WKS2["EXAWKSGLA002\nHot Desk WKS\n.151"]
    LAP["EXALAPGLA001\nPool Laptop\n.152"]
    PRN["EXAPRNGLA001\nHP LaserJet Pro\n.16"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → FAL"])

    INET --> PVE
    PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WKS1 & WKS2 & LAP & PRN & WAP & CAM
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WKS1,WKS2,LAP,PRN,WAP,CAM ep
    class VPN vpn
```

---

## CLY — Clydebank

**LAN:** `192.168.41.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL

```mermaid
graph TD
    INET(("🌐 Internet"))
    FWL["EXAFWLCLY001\nFortiOS 7.6.5\n.1"]
    RTR["EXARTRCLY001\nCisco ISR 4331\n.254"]
    SW["EXASWICLY001\nCisco 9300\n.250"]
    RAC["EXARACCLY001\nHPE iLO5\n.2"]
    PVE["EXAPVECLY001\nProxmox node 1\n.5"]
    DC1["EXADCSCLY001\nDC primary\n.10"]
    DC2["EXADCSCLY002\nDC secondary\n.11"]
    SRV["EXASRVCLY001\nRocky Linux · Oracle DB\n.20"]
    SBC["EXASBCCLY001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYCLY001\nRudder Relay\n.12"]
    SUR["EXASURCLY001\nMicrosoft Surface\n.51"]
    PHN["EXAPHNCLY001\niOS handset"]
    TAB["EXASURCLY002\nAndroid Tablet"]
    WAP["WAPs x2\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → FAL"])

    INET --> RTR --> FWL --> SW
    SW --> PVE --> DC1 & DC2 & SRV & SBC
    RAC -.->|"manages"| PVE
    SW --> SUR & PHN & TAB & WAP & CAM
    FWL <-->|"WireGuard tunnel"| VPN

    SW --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class FWL,RTR,SW net
    class PVE,DC1,DC2,SRV,SBC,RAC srv
    class RRY rudder
    class SUR,PHN,TAB,WAP,CAM ep
    class VPN vpn
```

---

## DUN — Dundee

**LAN:** `192.168.138.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL

```mermaid
graph TD
    INET(("🌐 Internet"))
    RTR["EXARTRDUN001\nCisco ISR 4331\n.254"]
    RAC["EXARACDUN001\nBMC node 1\n.2"]
    PVE["EXAPVEDUN001\nProxmox node 1\n.5"]
    DC["EXADCSDUN001\nDC\n.10"]
    SBC["EXASBCDUN001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYDUN001\nRudder Relay\n.12"]
    SUR1["EXASURDUN001\nSurface\n.51"]
    SUR2["EXASURDUN002\nSurface\n.52"]
    PHN1["EXAPHNDUN001\niOS Phone"]
    PHN2["EXAPHNDUN002\niOS Phone"]
    WAP["WAPs x2\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → FAL"])

    INET --> RTR --> PVE
    PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    RTR --> SUR1 & SUR2 & PHN1 & PHN2 & WAP & CAM
    RTR <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class RTR net
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class SUR1,SUR2,PHN1,PHN2,WAP,CAM ep
    class VPN vpn
```

---

## PER — Perth

**LAN:** `192.168.173.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACPER001\nBMC node 1\n.2"]
    PVE["EXAPVEPER001\nProxmox node 1\n.5"]
    DC["EXADCSPER001\nDC\n.10"]
    SBC["EXASBCPER001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYPER001\nRudder Relay\n.12"]
    NIX["EXANIXPER001\nSolaris 11.5\nMIDI/Music Archive · .40"]
    NAS["EXANASPER001\nSynology NAS\n.50"]
    MBP["EXAMBPPER001\nMacBook Pro\n.70"]
    SUR["EXASURPER001\nSurface\n.71"]
    PHN["EXAPHNPER001-004\nYealink T46G Phones\n.80"]
    PRN["EXAPRNPER001\nHP MFP Printer\n.20"]
    VND["EXAVNDPER001\nScone Palace Vending Machine\n.60"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → FAL"])

    INET --> PVE
    PVE --> DC & SBC & NIX & NAS
    RAC -.->|"manages"| PVE
    PVE --> MBP & SUR & PHN & PRN & VND & WAP & CAM
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef site fill:#880e4f,stroke:#f48fb1,color:#fce4ec
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,DC,SBC,NIX,NAS,RAC srv
    class RRY rudder
    class MBP,SUR,PHN,PRN,WAP,CAM ep
    class VND site
    class VPN vpn
```

---

## ABD — Aberdeen

**LAN:** `192.168.224.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL

```mermaid
graph TD
    INET(("🌐 Internet"))
    FWL["EXAFWLABD001\nCisco ASA 5506-X\n.1"]
    RTR["EXARTRABD001\nCisco ISR 4331\n.254"]
    RAC["EXARACABD001\nBMC node 1\n.2"]
    PVE["EXAPVEABD001\nProxmox node 1\n.5"]
    DC["EXADCSABD001\nDC\n.10"]
    SBC["EXASBCABD001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYABD001\nRudder Relay\n.12"]
    MBP1["EXAMBPABD001\nMacBook\n.137"]
    MBP2["EXAMBPABD002\nMacBook\n.124"]
    PHN1["EXAPHNABD001\nCorporate iPhone"]
    PHN2["EXAPHNABD002\nCorporate iPhone"]
    WAP["WAPs x2\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → FAL"])

    INET --> RTR --> FWL --> PVE
    PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    FWL --> MBP1 & MBP2 & PHN1 & PHN2 & WAP & CAM
    FWL <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class FWL,RTR net
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class MBP1,MBP2,PHN1,PHN2,WAP,CAM ep
    class VPN vpn
```

---

---

## 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England

---

## LND — London

**LAN:** `192.168.20.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL

```mermaid
graph TD
    INET(("🌐 Internet"))
    FWL["EXAFWLLND001\nCisco ASA 5516-X\n.1"]
    SW["EXASWILND001\nCisco 9300\n.250"]
    RTR["EXARTRLND001\nCisco ISR 4331\n.254"]
    RAC["EXARACLND001\nDell iDRAC9\n.2"]
    PVE["EXAPVELND001\nProxmox node 1\n.5"]
    DC["EXADCRLND001\nDC · RID/Infra Master\n.10"]
    SBC["EXASBCLND001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYLND001\nRudder Relay\n.12"]
    WKS["EXAWKSLND001\nHot Desk WKS\n.150"]
    PRN1["EXAPRNLND001\nXerox WorkCentre\n.16"]
    PRN2["EXAPRNLND002\nProCAT Steno Writer\nCourt Device"]
    RAD["EXARADLND001\nBBC Office Radio Mk II\n.80"]
    MIC["EXAMICLND001\nShure SM7 Microphone\nDante Audio · .81"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → FAL"])

    INET --> RTR --> FWL --> SW
    SW --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    SW --> WKS & PRN1 & PRN2 & RAD & MIC & WAP & CAM
    FWL <-->|"WireGuard tunnel"| VPN

    SW --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef site fill:#880e4f,stroke:#f48fb1,color:#fce4ec
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class FWL,SW,RTR net
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WKS,PRN1,WAP,CAM ep
    class PRN2,RAD,MIC site
    class VPN vpn
```

---

## BIR — Birmingham

**LAN:** `192.168.121.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL

```mermaid
graph TD
    INET(("🌐 Internet"))
    FWL["EXAFWLBIR001\nPalo Alto PAN-OS\n.1"]
    SW1["EXASWIBIR001\nCisco 9300\n.250"]
    SW2["EXASWIBIR002\nAccess Switch\n.251"]
    RTR["EXARTRBIR001\nCisco ISR 4331\n.254"]
    RAC["EXARACBIR001\nDell DRAC\n.2"]
    PVE["EXAPVEBIR001\nProxmox node 1\n.5"]
    DC1["EXADCRBIR001\nDC primary\n.10"]
    DC2["EXADCRBIR002\nDC secondary\n.11"]
    SRV["EXASRVBIR001\nRocky Linux · Oracle DB\n.20"]
    SBC["EXASBCBIR001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYBIR001\nRudder Relay\n.12"]
    MBP["EXAMBPBIR001\nMacBook Pro\n.41"]
    TAB["EXATABBIR001\nSamsung Galaxy Tab\n.61"]
    PHN["EXAPHNBIR001\nSamsung S25 Ultra"]
    WAP["WAPs x2\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    MOO["EXAMOOBIR001\nMoog One Synthesizer\n.70"]
    LIN["EXALINBIR001\nLinnDrum LM-2\n.71"]
    FCL["EXAFCLBIR001\nFairlight CMI IIx\n.72"]
    AST["EXAASTBIR001\nAtari ST · MIDI\n.73"]
    PAY["EXAPAYBIR001\nGPO Kiosk No.6 Payphone\n.74"]
    LCD["EXALCDBIR001\nNEC PlasmaSync NOC Display\n.75"]
    VPN(["🔗 WireGuard → FAL"])

    INET --> RTR --> FWL --> SW1 & SW2
    SW1 --> PVE --> DC1 & DC2 & SRV & SBC
    RAC -.->|"manages"| PVE
    SW2 --> MBP & TAB & PHN & WAP & CAM
    SW2 --> MOO & LIN & FCL & AST & PAY & LCD
    FWL <-->|"WireGuard tunnel"| VPN

    SW1 --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef site fill:#880e4f,stroke:#f48fb1,color:#fce4ec
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class FWL,SW1,SW2,RTR net
    class PVE,DC1,DC2,SRV,SBC,RAC srv
    class RRY rudder
    class MBP,TAB,PHN,WAP,CAM ep
    class MOO,LIN,FCL,AST,PAY,LCD site
    class VPN vpn
```

---

## MCR — Manchester

**LAN:** `192.168.161.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL

```mermaid
graph TD
    INET(("🌐 Internet"))
    SW["EXASWIMCR001\nCisco 9300\n.250"]
    RAC["EXARACMCR001\nHPE iLO5\n.2"]
    PVE["EXAPVEMCR001\nProxmox node 1\n.5"]
    DC1["EXADCRMCR001\nDC PDC · RID/Infra Master\n.10"]
    DC2["EXADCSMCR002\nDC secondary\n.11"]
    SBC["EXASBCMCR001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYMCR001\nRudder Relay\n.12"]
    LAP1["EXALAPMCR001\nWin11 Laptop\n.19"]
    LAP2["EXALAPMCR002\nWin11 Laptop\n.150"]
    WKS1["EXAWKSMCR001\nFront Desk WKS\n.152"]
    WKS2["EXAWKSMCR002\nFinance WKS\n.153"]
    PRN["EXAPRNMCR001\nNetwork Printer\n.16"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → FAL"])

    INET --> SW
    SW --> PVE --> DC1 & DC2 & SBC
    RAC -.->|"manages"| PVE
    SW --> LAP1 & LAP2 & WKS1 & WKS2 & PRN & WAP & CAM
    SW <-->|"WireGuard tunnel"| VPN

    SW --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class SW net
    class PVE,DC1,DC2,SBC,RAC srv
    class RRY rudder
    class LAP1,LAP2,WKS1,WKS2,PRN,WAP,CAM ep
    class VPN vpn
```

---

## LIV — Liverpool

**LAN:** `192.168.151.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL

```mermaid
graph TD
    INET(("🌐 Internet"))
    SW["EXASWILIV001\nCisco 9200\n.250"]
    RAC["EXARACLIV001\nHPE iLO5\n.2"]
    PVE["EXAPVELIV001\nProxmox node 1\n.5"]
    DC["EXADCRLIV001\nDC · WS2025\n.10"]
    SBC["EXASBCLIV001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYLIV001\nRudder Relay\n.12"]
    SRV["EXASVRLIV001\nWS2022 File Server\n.10"]
    MBP["EXAMBPLIV001\nMacBook Pro · macOS Tahoe\n.150"]
    MAC["EXAMACLIV001\niMac ⚠️ disabled\n.152"]
    RDR["EXARDRLIV002\nHID Signo Badge Reader\n.16"]
    BPS["EXABPSLIV001\nBadge Programming WKS\n.17"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → FAL"])

    INET --> SW
    SW --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    SW --> SRV & MBP & MAC & RDR & BPS & WAP & CAM
    SW <-->|"WireGuard tunnel"| VPN

    SW --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class SW net
    class PVE,DC,SBC,RAC,SRV srv
    class RRY rudder
    class MBP,RDR,BPS,WAP,CAM ep
    class MAC warn
    class VPN vpn
```

---

## NEW — Newcastle

**LAN:** `192.168.191.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL

```mermaid
graph TD
    INET(("🌐 Internet"))
    SW["EXASWINEW001\nTP-Link JetStream\n.250"]
    RAC["EXARACNEW001\nDell iDRAC9\n.2"]
    PVE["EXAPVENEW001\nProxmox node 1\n.5"]
    DC["EXADCRNEW001\nDC\n.10"]
    SBC["EXASBCNEW001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYNEW001\nRudder Relay\n.12"]
    SRV["EXASRVNEW001\nWS2022 File/Print Server\n.21"]
    WKS["⚠️ EXAWKSNEW099\nWin11 WKS · LAPS expired\n.161"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → FAL"])

    INET --> SW
    SW --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    SW --> SRV & WKS & WAP & CAM
    SW <-->|"WireGuard tunnel"| VPN

    SW --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class SW net
    class PVE,DC,SBC,RAC,SRV srv
    class RRY rudder
    class WAP,CAM ep
    class WKS warn
    class VPN vpn
```

---

## SHE — Sheffield

**LAN:** `192.168.114.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACSHE001\nBMC node 1\n.2"]
    PVE["EXAPVESHE001\nProxmox node 1\n.5"]
    DC["EXADCSSHE001\nDC\n.10"]
    SBC["EXASBCSHE001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYSHE001\nRudder Relay\n.12"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    EP["Endpoints TODO"]
    VPN(["🔗 WireGuard → FAL"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM & EP
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WAP,CAM,EP ep
    class VPN vpn
```

---

## HAL — Halifax

**LAN:** `192.168.142.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACHAL001\nBMC node 1\n.2"]
    PVE["EXAPVEHAL001\nProxmox node 1\n.5"]
    DC["EXADCSHAL001\nDC\n.10"]
    SBC["EXASBCHAL001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYHAL001\nRudder Relay\n.12"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    EP["Endpoints TODO"]
    VPN(["🔗 WireGuard → FAL"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM & EP
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WAP,CAM,EP ep
    class VPN vpn
```

---

## HUL — Hull

**LAN:** `192.168.148.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACHUL001\nBMC node 1\n.2"]
    PVE["EXAPVEHUL001\nProxmox node 1\n.5"]
    DC["EXADCSHUL001\nDC\n.10"]
    SBC["EXASBCHUL001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYHUL001\nRudder Relay\n.12"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    EP["Endpoints TODO"]
    VPN(["🔗 WireGuard → FAL"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM & EP
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WAP,CAM,EP ep
    class VPN vpn
```

---

## COV — Coventry

**LAN:** `192.168.247.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
*Note: WAP/RTR-only site — minimal infrastructure.*

```mermaid
graph TD
    INET(("🌐 Internet"))
    RTR["EXARTRCOV001\nCisco ISR 4331\n.254"]
    RAC["EXARACCOV001\nBMC node 1\n.2"]
    PVE["EXAPVECOV001\nProxmox node 1\n.5"]
    DC["EXADCSCOV001\nDC\n.10"]
    SBC["EXASBCCOV001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYCOV001\nRudder Relay\n.12"]
    WAP["WAPs x2\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → FAL"])

    INET --> RTR --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    RTR --> WAP & CAM
    RTR <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class RTR net
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WAP,CAM ep
    class VPN vpn
```

---

---

## 🇩🇰 Danmark

---

## CPH — København

**LAN:** `192.168.231.0/24` · **Domain:** `example.com` / `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE

```mermaid
graph TD
    INET(("🌐 Internet"))
    SW["EXASWICPH001\nTP-Link JetStream\n.250"]
    RTR["EXARTRCPH001\nCisco ISR 4331\n.254"]
    RAC["EXARACCPH001\nDell iDRAC9\n.2"]
    PVE["EXAPVECPH001\nProxmox node 1\n.5"]
    DC1["EXADCSCPH001\nDC · example.com\n.10"]
    DC2["EXADCSCPH002\nDC · example.net\n.11"]
    SBC["EXASBCCPH001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYCPH001\nRudder Relay\n.12"]
    NTP["EXACLKCPH001\nMeinberg LANTIME M300\nNTP Clock · .18"]
    TV["EXATVSCPH001\nBella Kronik 42X\nDR/TV2 · .17"]
    WAP["WAPs x3\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → ODE"])

    INET --> RTR --> SW
    SW --> PVE --> DC1 & DC2 & SBC
    RAC -.->|"manages"| PVE
    SW --> NTP & TV & WAP & CAM
    RTR <-->|"WireGuard tunnel"| VPN

    SW --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#880e4f,stroke:#f48fb1,color:#fce4ec
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef site fill:#880e4f,stroke:#f48fb1,color:#fce4ec
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class RTR,SW net
    class PVE,DC1,DC2,SBC,RAC srv
    class RRY rudder
    class NTP,TV site
    class WAP,CAM ep
    class VPN vpn
```

---

## ODE — Odense *(EU Hub)* ⭐

**LAN:** `192.168.126.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (EU hub) · **VPN parent:** CLD (EU backup)

```mermaid
graph TD
    INET(("🌐 Internet"))
    FWL["EXAFWLODE001\nCisco ASA 5506-X\n.1"]

    subgraph BMC ["BMC Pool"]
        RAC1["EXARACODE001\nBMC node 1\n.2"]
        RAC2["EXARACODE002\nBMC node 2\n.3"]
        RAC3["EXARACODE003\nBMC node 3\n.4"]
    end

    subgraph PVE ["Proxmox Cluster (3-node)"]
        PVE1["EXAPVEODE001\nProxmox node 1\n.5"]
        PVE2["EXAPVEODE002\nProxmox node 2\n.6"]
        PVE3["EXAPVEODE003\nProxmox node 3\n.7"]
    end

    DC1["EXADCSODE001\nDC PDC · RID/Infra Master\n.10"]
    DC2["EXADCSODE002\nDC secondary\n.11"]
    SBC["EXASBCODE001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYODE001\nRudder Relay\n.12"]
    MAC["EXAMACODE001\niMac · macOS Tahoe\n.150"]
    MBP["EXAMBPODE002\nMacBook Pro\n.151"]
    JKB["EXAMUSODE001\nPureline 128V Jukebox\n.60"]
    WAP["WAPs x2\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN_CLD(["🔗 WireGuard ← CLD\nEU backup"])
    VPN_EU(["🔗 WireGuard → EU spokes\nCPH/KGE/FAX/KOR/BON/BER/MUN\nGOT/OSL/AMS/MIL/VIE"])

    INET --> FWL
    FWL --> PVE1 & PVE2 & PVE3
    FWL --> DC1 & DC2 & SBC
    RAC1 -.->|"manages"| PVE1
    RAC2 -.->|"manages"| PVE2
    RAC3 -.->|"manages"| PVE3
    FWL --> MAC & MBP & JKB & WAP & CAM
    FWL <-->|"WireGuard tunnel"| VPN_CLD
    FWL -->|"WireGuard spokes"| VPN_EU

    PVE1 --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN_CLD
    classDef net fill:#0d3b2e,stroke:#66bb6a,color:#e8f5e9
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef site fill:#880e4f,stroke:#f48fb1,color:#fce4ec
    classDef bmc fill:#bf360c,stroke:#ff8a65,color:#fbe9e7
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class FWL net
    class PVE1,PVE2,PVE3,DC1,DC2,SBC srv
    class RRY rudder
    class MAC,MBP,WAP,CAM ep
    class JKB site
    class RAC1,RAC2,RAC3 bmc
    class VPN_CLD,VPN_EU vpn
```

---

## KGE — Køge ⚠️

**LAN:** `192.168.65.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
> ⚠️ DC out of sync 27 days · WS2016 EOL · disk space low — rebuild required

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACKGE001\nBMC node 1\n.2"]
    PVE["EXAPVEKGE001\nProxmox node 1\n.5"]
    DC["⚠️ EXADCSKGE001\nDC · WS2016 EOL\nOOS 27d · .10"]
    SBC["EXASBCKGE001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYKGE001\nRudder Relay\n.12"]
    WAP["EXAWAPKGE001\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    PRN["EXAPRNKGE001\nHP LaserJet MFP M528\n.16"]
    VPN(["🔗 WireGuard → ODE"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM & PRN
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,SBC,RAC srv
    class RRY rudder
    class DC warn
    class WAP,CAM,PRN ep
    class VPN vpn
```

---

## FAX — Faxe

**LAN:** `192.168.246.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE

```mermaid
graph TD
    INET(("🌐 Internet"))
    RTR["EXARTRFAX001\nCisco ISR 4331\n.254"]
    RAC["EXARACFAX001\nBMC node 1\n.2"]
    PVE["EXAPVEFAX001\nProxmox node 1\n.5"]
    DC["EXADCSFAX001\nDC\n.10"]
    SBC["EXASBCFAX001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYFAX001\nRudder Relay\n.12"]
    WAP["WAPs x2\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → ODE"])

    INET --> RTR --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    RTR --> WAP & CAM
    RTR <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#880e4f,stroke:#f48fb1,color:#fce4ec
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class RTR net
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WAP,CAM ep
    class VPN vpn
```

---

## KOR — Korsør

**LAN:** `192.168.238.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACKOR001\nBMC node 1\n.2"]
    PVE["EXAPVEKOR001\nProxmox node 1\n.5"]
    DC["EXADCSKOR001\nDC\n.10"]
    SBC["EXASBCKOR001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYKOR001\nRudder Relay\n.12"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → ODE"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WAP,CAM ep
    class VPN vpn
```

---

---

## 🇩🇪 Deutschland

---

## BON — Bonn

**LAN:** `192.168.228.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Note:** Hosts Schema Master + Domain Naming Master

```mermaid
graph TD
    INET(("🌐 Internet"))
    SW["EXASWIBON001\nCisco 2960X\n.250"]
    RTR["EXARTRBON001\nCisco ISR 4331\n.254"]
    RAC["EXARACBON001\nDell iDRAC9\n.2"]
    PVE["EXAPVEBON001\nProxmox node 1\n.5"]
    DC["EXADCSBON001\nDC · Schema Master\nDN Master · .10"]
    SBC["EXASBCBON001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYBON001\nRudder Relay\n.12"]
    WKS["EXAWKSBON001\nFinance WKS · .151"]
    LAP1["EXALAPBON001\nThinkPad ⚠️ disabled\n.150"]
    LAP2["EXALAPBON002\nFinance Laptop · .153"]
    VCU["EXAVCUBON001\nPoly Studio X70\nBoardroom · .2"]
    CAM["EXACAMBON001\nAxis P3245-LVE CCTV\n.17"]
    TV["EXATVSBON001\nSamsung 65\"\n.18"]
    WAP["WAPs x2\nUbiquiti UniFi U6-Pro"]
    VPN(["🔗 WireGuard → ODE"])

    INET --> RTR --> SW
    SW --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    SW --> WKS & LAP1 & LAP2 & VCU & CAM & TV & WAP
    RTR <-->|"WireGuard tunnel"| VPN

    SW --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#bf360c,stroke:#ff8a65,color:#fbe9e7
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef site fill:#880e4f,stroke:#f48fb1,color:#fce4ec
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class SW,RTR net
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WKS,LAP2,WAP ep
    class VCU,CAM,TV site
    class LAP1 warn
    class VPN vpn
```

---

## BER — West Berlin

**LAN:** `192.168.113.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE

```mermaid
graph TD
    INET(("🌐 Internet"))
    RTR["EXARTRBER001\nCisco ISR 4331\n.254"]
    RAC["EXARACBER001\nBMC node 1\n.2"]
    PVE["EXAPVEBER001\nProxmox node 1\n.5"]
    DC["EXADCSBER001\nDC · PDC Emulator\nRID/Infra Master WS2019 · .10"]
    SBC["EXASBCBER001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYBER001\nRudder Relay\n.12"]
    SRV["EXASRVBER001\nWS2019 Legacy App Server\n.21"]
    NIX["EXANIXBER001\nDebian 12 Server\n.22"]
    WAP["WAPs x2\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → ODE"])

    INET --> RTR --> PVE --> DC & SBC & SRV & NIX
    RAC -.->|"manages"| PVE
    RTR --> WAP & CAM
    RTR <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#bf360c,stroke:#ff8a65,color:#fbe9e7
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class RTR net
    class PVE,DC,SBC,SRV,NIX,RAC srv
    class RRY rudder
    class WAP,CAM ep
    class VPN vpn
```

---

## MUN — Munich

**LAN:** `192.168.189.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE

```mermaid
graph TD
    INET(("🌐 Internet"))
    SW["EXASWIMUN001\nCisco 9200\n.250"]
    RAC["EXARACMUN001\nHPE iLO5\n.2"]
    PVE["EXAPVEMUN001\nProxmox node 1\n.5"]
    DC["EXADCSMUN001\nDC\n.10"]
    SBC["EXASBCMUN001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYMUN001\nRudder Relay\n.12"]
    WKS["EXAWKSMUN001\nHot Desk WKS\n.150"]
    LAP1["EXALAPMUN001\nPool Laptop\n.151"]
    LAP2["⚠️ EXALAPMUN002\nPool Laptop\nLAPS expired 61d · .152"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → ODE"])

    INET --> SW
    SW --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    SW --> WKS & LAP1 & LAP2 & WAP & CAM
    SW <-->|"WireGuard tunnel"| VPN

    SW --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#bf360c,stroke:#ff8a65,color:#fbe9e7
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class SW net
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WKS,LAP1,WAP,CAM ep
    class LAP2 warn
    class VPN vpn
```

---

---

## 🇸🇪 Sverige

---

## GOT — Gothenburg

**LAN:** `192.168.46.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACGOT001\nBMC node 1\n.2"]
    PVE["EXAPVEGOT001\nProxmox node 1\n.5"]
    DC["EXADCSGOT001\nDC\n.10"]
    SBC["EXASBCGOT001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYGOT001\nRudder Relay\n.12"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → ODE"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WAP,CAM ep
    class VPN vpn
```

---

---

## 🇳🇴 Norge

---

## OSL — Oslo

**LAN:** `192.168.47.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACOSL001\nBMC node 1\n.2"]
    PVE["EXAPVEOSL001\nProxmox node 1\n.5"]
    DC["EXADCSOSL001\nDC\n.10"]
    SBC["EXASBCOSL001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYOSL001\nRudder Relay\n.12"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → ODE"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WAP,CAM ep
    class VPN vpn
```

---

---

## 🇳🇱 Nederland

---

## AMS — Amsterdam

**LAN:** `192.168.31.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACAMS001\nBMC node 1\n.2"]
    PVE["EXAPVEAMS001\nProxmox node 1\n.5"]
    DC["EXADCSAMS001\nDC\n.10"]
    SBC["EXASBCAMS001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYAMS001\nRudder Relay\n.12"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → ODE"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WAP,CAM ep
    class VPN vpn
```

---

---

## 🇮🇹 Italia

---

## MIL — Milan

**LAN:** `192.168.39.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACMIL001\nBMC node 1\n.2"]
    PVE["EXAPVEMIL001\nProxmox node 1\n.5"]
    DC["EXADCSMIL001\nDC\n.10"]
    SBC["EXASBCMIL001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYMIL001\nRudder Relay\n.12"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → ODE"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WAP,CAM ep
    class VPN vpn
```

---

---

## 🇦🇹 Österreich

---

## VIE — Vienna

**LAN:** `192.168.78.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACVIE001\nBMC node 1\n.2"]
    PVE["EXAPVEVIE001\nProxmox node 1\n.5"]
    DC["EXADCSVIE001\nDC\n.10"]
    SBC["EXASBCVIE001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYVIE001\nRudder Relay\n.12"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → ODE"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WAP,CAM ep
    class VPN vpn
```

---

---

## 🇨🇦 Canada

---

## BRK — Brockville *(NA/APAC Hub)* ⭐

**LAN:** `192.168.136.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (NA/APAC hub) · **VPN parent:** CLD (NA/APAC backup)  
> ⚠️ `EXADCSBRK001` — DNS, Netlogon and KDC services stopped.

```mermaid
graph TD
    INET(("🌐 Internet"))
    RTR["EXARTRBRK001\nCisco ISR 4331\n.254"]

    subgraph BMC ["BMC Pool"]
        RAC1["EXARACBRK001\nBMC node 1\n.2"]
        RAC2["EXARACBRK002\nBMC node 2\n.3"]
        RAC3["EXARACBRK003\nBMC node 3\n.4"]
    end

    subgraph PVE ["Proxmox Cluster (3-node)"]
        PVE1["EXAPVEBRK001\nProxmox node 1\n.5"]
        PVE2["EXAPVEBRK002\nProxmox node 2\n.6"]
        PVE3["EXAPVEBRK003\nProxmox node 3\n.7"]
    end

    DC["🔴 EXADCSBRK001\nDC · Services stopped\n.10"]
    SBC["EXASBCBRK001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYBRK001\nRudder Relay\n.12"]
    LAP["EXALAPBRK001\nWin11 Tour Laptop\n.21"]
    WAP["EXAWAPBRK001\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VND1["EXADONBRK001\nTim Hortons Donut Vending\n.60"]
    VND2["EXAVNDBRK001\nMaple Syrup Vending\n.61"]
    VPN_CLD(["🔗 WireGuard ← CLD\nNA/APAC backup"])
    VPN_NA(["🔗 WireGuard → NA/APAC spokes\nTOR/MTL/LAX/NYC/NJC\nMIA/ATL/CHI/SYD/MEL/AKL"])

    INET --> RTR
    RTR --> PVE1 & PVE2 & PVE3
    RTR --> DC & SBC
    RAC1 -.->|"manages"| PVE1
    RAC2 -.->|"manages"| PVE2
    RAC3 -.->|"manages"| PVE3
    RTR --> LAP & WAP & CAM & VND1 & VND2
    RTR <-->|"WireGuard tunnel"| VPN_CLD
    RTR -->|"WireGuard spokes"| VPN_NA

    PVE1 --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN_CLD
    classDef net fill:#0d3b2e,stroke:#66bb6a,color:#e8f5e9
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef site fill:#880e4f,stroke:#f48fb1,color:#fce4ec
    classDef bmc fill:#bf360c,stroke:#ff8a65,color:#fbe9e7
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class RTR net
    class PVE1,PVE2,PVE3,SBC srv
    class RRY rudder
    class DC warn
    class LAP,WAP,CAM ep
    class VND1,VND2 site
    class RAC1,RAC2,RAC3 bmc
    class VPN_CLD,VPN_NA vpn
```

---

## TOR — Toronto ⚠️

**LAN:** `192.168.146.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSTOR001` — DNS, Netlogon and KDC services stopped.

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACTOR001\nBMC node 1\n.2"]
    PVE["EXAPVETOR001\nProxmox node 1\n.5"]
    DC["🔴 EXADCSTOR001\nDC · Services stopped\n.10"]
    SBC["EXASBCTOR001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYTOR001\nRudder Relay\n.12"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → BRK"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,SBC,RAC srv
    class RRY rudder
    class DC warn
    class WAP,CAM ep
    class VPN vpn
```

---

## MTL — Montreal

**LAN:** `192.168.154.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACMTL001\nBMC node 1\n.2"]
    PVE["EXAPVEMTL001\nProxmox node 1\n.5"]
    DC["EXADCSMTL001\nDC\n.10"]
    SBC["EXASBCMTL001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYMTL001\nRudder Relay\n.12"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → BRK"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class WAP,CAM ep
    class VPN vpn
```

---

---

## 🇺🇸 United States

---

## LAX — Los Angeles ⚠️

**LAN:** `192.168.213.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSLAX001` — DNS, Netlogon and KDC services stopped.

```mermaid
graph TD
    INET(("🌐 Internet"))
    FWL["EXAFWLLAX001\nPalo Alto PAN-OS 10.x\n.1"]
    SW1["EXASWILAX001\nCisco 9300\n.250"]
    SW2["EXASWILAX002\nCisco 2960\n.251"]
    RTR["EXARTRLAX001\nCisco ISR 4331\n.254"]
    RAC["EXARACLAX001\nDell iDRAC9\n.2"]
    PVE["EXAPVELAX001\nProxmox node 1\n.5"]
    DC["🔴 EXADCSLAX001\nDC · Services stopped\n.10"]
    SRV["EXASRVLAX001\nRocky Linux · Local services/DB\n.20"]
    SBC["EXASBCLAX001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYLAX001\nRudder Relay\n.12"]
    MBP["EXAMBPLAX001\nMacBook Pro\n.41"]
    TAB["EXATABLAX001\niPad · Setlists\n.61"]
    PHN["EXAPHNLAX001\nAndroid Phone"]
    WAP["WAPs x3\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    MOO["EXAMUSLAX001\nMoog One Synthesizer\n.70"]
    LIN["EXAMUSLAX002\nLinnDrum LM-2\n.71"]
    FCL["EXAMUSLAX003\nFairlight CMI IIx\n.72"]
    AST["EXATTYLAX001\nAtari ST · MIDI\n.73"]
    PAY["EXAPAYLAX001\nLobby Payphone\n.74"]
    LCD["EXALCDLAX001\nNEC PlasmaSync Display\n.75"]
    VPN(["🔗 WireGuard → BRK"])

    INET --> RTR --> FWL --> SW1 & SW2
    SW1 --> PVE --> DC & SRV & SBC
    RAC -.->|"manages"| PVE
    SW2 --> MBP & TAB & PHN & WAP & CAM
    SW2 --> MOO & LIN & FCL & AST & PAY & LCD
    FWL <-->|"WireGuard tunnel"| VPN

    SW1 --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#1b5e20,stroke:#81c784,color:#f1f8e9
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef site fill:#880e4f,stroke:#f48fb1,color:#fce4ec
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class FWL,SW1,SW2,RTR net
    class PVE,SRV,SBC,RAC srv
    class RRY rudder
    class DC warn
    class MBP,TAB,PHN,WAP,CAM ep
    class MOO,LIN,FCL,AST,PAY,LCD site
    class VPN vpn
```

---

## NYC — New York ⚠️

**LAN:** `192.168.212.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSNYC001` — DNS, Netlogon and KDC services stopped.

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACNYC001\nBMC node 1\n.2"]
    PVE["EXAPVENYC001\nProxmox node 1\n.5"]
    DC["🔴 EXADCSNYC001\nDC · Services stopped\n.10"]
    SBC["EXASBCNYC001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYNYC001\nRudder Relay\n.12"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → BRK"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,SBC,RAC srv
    class RRY rudder
    class DC warn
    class WAP,CAM ep
    class VPN vpn
```

---

## NJC — New Jersey ⚠️

**LAN:** `192.168.201.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSNJC001` — DNS, Netlogon and KDC services stopped.

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACNJC001\nBMC node 1\n.2"]
    PVE["EXAPVENJC001\nProxmox node 1\n.5"]
    DC["🔴 EXADCSNJC001\nDC · Services stopped\n.10"]
    SBC["EXASBCNJC001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYNJC001\nRudder Relay\n.12"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → BRK"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,SBC,RAC srv
    class RRY rudder
    class DC warn
    class WAP,CAM ep
    class VPN vpn
```

---

## MIA — Miami

**LAN:** `192.168.135.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACMIA001\nBMC node 1\n.2"]
    PVE["EXAPVEMIA001\nProxmox node 1\n.5"]
    DC["EXADCSMIA001\nDC\n.10"]
    SBC["EXASBCMIA001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYMIA001\nRudder Relay\n.12"]
    LAP["EXALAPMIA001\nmacOS Sonoma Laptop\n.21"]
    COF["EXACOFMIA001\nCuban Covfefe Machine\nVxWorks · .60"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → BRK"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> LAP & COF & WAP & CAM
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef site fill:#880e4f,stroke:#f48fb1,color:#fce4ec
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,DC,SBC,RAC srv
    class RRY rudder
    class LAP,WAP,CAM ep
    class COF site
    class VPN vpn
```

---

## ATL — Athens, GA ⚠️

**LAN:** `192.168.33.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSATL001` — DNS, Netlogon and KDC services stopped.

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACATL001\nBMC node 1\n.2"]
    PVE["EXAPVEATL001\nProxmox node 1\n.5"]
    DC["🔴 EXADCSATL001\nDC · Services stopped\n.10"]
    SBC["EXASBCATL001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYATL001\nRudder Relay\n.12"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → BRK"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,SBC,RAC srv
    class RRY rudder
    class DC warn
    class WAP,CAM ep
    class VPN vpn
```

---

## CHI — Chicago ⚠️

**LAN:** `192.168.214.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSCHI001` — DNS, Netlogon and KDC services stopped.

```mermaid
graph TD
    INET(("🌐 Internet"))
    RAC["EXARACCHI001\nBMC node 1\n.2"]
    PVE["EXAPVECHI001\nProxmox node 1\n.5"]
    DC["🔴 EXADCSCHI001\nDC · Services stopped\n.10"]
    SBC["EXASBCCHI001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYCHI001\nRudder Relay\n.12"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    VPN(["🔗 WireGuard → BRK"])

    INET --> PVE --> DC & SBC
    RAC -.->|"manages"| PVE
    PVE --> WAP & CAM
    PVE <-->|"WireGuard tunnel"| VPN

    PVE --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class PVE,SBC,RAC srv
    class RRY rudder
    class DC warn
    class WAP,CAM ep
    class VPN vpn
```

---

---

## 🇦🇺 Australia

---

## SYD — Sydney ⚠️

**LAN:** `192.168.29.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSSYD001` — DNS, Netlogon and KDC services stopped.

```mermaid
graph TD
    INET(("🌐 Internet"))
    FWL["EXAFWLSYD001\nFortiGate 7.x\n.1"]
    SW1["EXASWISYD001\nCisco 9300\n.250"]
    SW2["EXASWISYD002\nCisco 2960\n.251"]
    RAC["EXARACSYD001\nDell iDRAC9\n.2"]
    PVE["EXAPVESYD001\nProxmox node 1\n.5"]
    DC["🔴 EXADCSSYD001\nDC · Services stopped\n.10"]
    SRV["EXASRVSYD001\nWS2022 Local Infra\n.20"]
    SBC["EXASBCSYD001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYSYD001\nRudder Relay\n.12"]
    MBP["EXAMBPSYD001\nMacBook Pro\n.40"]
    WKS["EXAWKSSYD001\nWin11 Workstation\n.41"]
    PHN["EXAPHNSYD001\nAndroid Phone"]
    TAB["EXATABSYD001\niPad · Setlists\n.60"]
    WAP["EXAWAPSYD001\nUbiquiti UniFi"]
    CAM1["EXACAMSYD001\nHikvision · Coffee cam\n.82"]
    CAM2["EXACAMSYD002\nHikvision · Reception\n.83"]
    LCD["EXALCDSYD001\nLG Signage Wallboard\n.70"]
    PRN["EXAPRNSYD001\nBrother Laser Printer\n.80"]
    COF["EXACOFSYD001\nSmart Coffee Machine\nRFC2324 · .83"]
    VPN(["🔗 WireGuard → BRK"])

    INET --> FWL --> SW1 & SW2
    SW1 --> PVE --> DC & SRV & SBC
    RAC -.->|"manages"| PVE
    SW2 --> MBP & WKS & PHN & TAB & WAP
    SW2 --> CAM1 & CAM2 & LCD & PRN & COF
    FWL <-->|"WireGuard tunnel"| VPN

    SW1 --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#f57f17,stroke:#ffee58,color:#1a1a1a
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef site fill:#880e4f,stroke:#f48fb1,color:#fce4ec
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class FWL,SW1,SW2 net
    class PVE,SRV,SBC,RAC srv
    class RRY rudder
    class DC warn
    class MBP,WKS,PHN,TAB,WAP ep
    class CAM1,CAM2,LCD,PRN,COF site
    class VPN vpn
```

---

## MEL — Melbourne ⚠️

**LAN:** `192.168.61.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSMEL001` — DNS, Netlogon and KDC services stopped.

```mermaid
graph TD
    INET(("🌐 Internet"))
    FWL["EXAFWLMEL001\nFortiGate 7.x\n.1"]
    SW1["EXASWIMEL001\nCisco 9300\n.250"]
    SW2["EXASWIMEL002\nCisco 2960\n.251"]
    RAC["EXARACMEL001\nHPE iLO5\n.2"]
    PVE["EXAPVEMEL001\nProxmox node 1\n.5"]
    DC["🔴 EXADCSMEL001\nDC · Services stopped\n.10"]
    SRV["EXASRVMEL001\nWS2022 File/Print\n.20"]
    SBC["EXASBCMEL001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYMEL001\nRudder Relay\n.12"]
    MBP["EXAMBPMEL001\nMacBook Pro\n.40"]
    WKS["EXAWKSMEL001\nWin11 Workstation\n.41"]
    PHN["EXAPHNMEL001\niOS Phone"]
    TAB["EXATABMEL001\niPad\n.60"]
    WAP["WAPs TODO\nUbiquiti UniFi U6-Pro"]
    CAM["CAMs TODO"]
    LCD["EXALCDMEL001\nSamsung Signage\n.70"]
    PRN["EXAPRNMEL001\nHP LaserJet\n.80"]
    NAS["EXANASMEL001\nSynology NAS DSM 7.x\n.81"]
    VPN(["🔗 WireGuard → BRK"])

    INET --> FWL --> SW1 & SW2
    SW1 --> PVE --> DC & SRV & SBC
    RAC -.->|"manages"| PVE
    SW2 --> MBP & WKS & PHN & TAB & WAP & CAM
    SW2 --> LCD & PRN & NAS
    FWL <-->|"WireGuard tunnel"| VPN

    SW1 --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#f57f17,stroke:#ffee58,color:#1a1a1a
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef site fill:#880e4f,stroke:#f48fb1,color:#fce4ec
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class FWL,SW1,SW2 net
    class PVE,SRV,SBC,RAC srv
    class RRY rudder
    class DC warn
    class MBP,WKS,PHN,TAB,WAP,CAM ep
    class LCD,PRN,NAS site
    class VPN vpn
```

---

---

## 🇳🇿 New Zealand

---

## AKL — Auckland ⚠️

**LAN:** `192.168.93.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSAKL001` — DNS, Netlogon and KDC services stopped.

```mermaid
graph TD
    INET(("🌐 Internet"))
    FWL["EXAFWLAKL001\nFortiGate 7.x\n.1"]
    SW1["EXASWIAKL001\nCisco 9300\n.250"]
    SW2["EXASWIAKL002\nCisco 2960\n.251"]
    RTR["EXARTRAKL001\nCisco ISR 4331\n.254"]
    RAC["EXARACAKL001\nHPE iLO5\n.2"]
    PVE["EXAPVEAKL001\nProxmox node 1\n.5"]
    DC["🔴 EXADCSAKL001\nDC · Services stopped\n.10"]
    SRV["EXASRVAKL001\nWS2022 Local Server\n.20"]
    SBC["EXASBCAKL001\n3CX SBC → CLD PBX\n.48"]
    RRY["EXARRYAKL001\nRudder Relay\n.12"]
    WKS["EXAWKSAKL001\nWin11 Workstation\n.40"]
    MBP["EXAMBPAKL001\nMacBook Pro\n.41"]
    PHN["EXAPHNAKL001\nAndroid Phone"]
    TAB["EXATABAKL001\niPad\n.60"]
    WAP1["EXAWAPAKL001\nUbiquiti UniFi"]
    WAP2["EXAWAPAKL002\nUbiquiti UniFi"]
    CAM["EXACAMAKL001\nAxis Camera\n.82"]
    LCD["EXALCDAKL001\nSamsung Signage\n.70"]
    PRN["EXAPRNAKL001\nHP LaserJet\n.80"]
    COF["EXACOFAKL001\nSmart Coffee Machine\n.83"]
    VPN(["🔗 WireGuard → BRK"])

    INET --> RTR --> FWL --> SW1 & SW2
    SW1 --> PVE --> DC & SRV & SBC
    RAC -.->|"manages"| PVE
    SW2 --> WKS & MBP & PHN & TAB & WAP1 & WAP2
    SW2 --> CAM & LCD & PRN & COF
    FWL <-->|"WireGuard tunnel"| VPN

    SW1 --> RRY
    RRY -. "→ EXARUDCLD001" .-> VPN
    classDef net fill:#f57f17,stroke:#ffee58,color:#1a1a1a
    classDef srv fill:#1a237e,stroke:#7986cb,color:#e8eaf6
    classDef warn fill:#b71c1c,stroke:#ef9a9a,color:#ffebee
    classDef ep fill:#4a148c,stroke:#ba68c8,color:#f3e5f5
    classDef site fill:#880e4f,stroke:#f48fb1,color:#fce4ec
    classDef vpn fill:#006064,stroke:#4dd0e1,color:#e0f7fa
    classDef rudder fill:#2d1b4e,stroke:#a569bd,color:#d7bde2
    class FWL,SW1,SW2,RTR net
    class PVE,SRV,SBC,RAC srv
    class RRY rudder
    class DC warn
    class WKS,MBP,PHN,TAB,WAP1,WAP2 ep
    class CAM,LCD,PRN,COF site
    class VPN vpn
```

---

*Example Music Limited — Internal Infrastructure Documentation*   *Do not distribute outside the organisation*cloud

