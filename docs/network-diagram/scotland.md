# Example Music Limited — Scotland Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## FAL — Falkirk *(Head Office)* ⭐ 🏛️

**Address:** Brockville Stadium, Hope Street, Falkirk  
**LAN:** `192.168.76.0/24` · **VPN:** `10.0.76.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (hub) · **VPN parent:** CLD (primary head node)  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 1324 500 0xxx · **Mobile:** +44 7700 903 2xxx

```mermaid
graph TD
    subgraph OLD_FAL ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RTR["📡 EXARTRFAL001 · Cisco ISR 4331 · .254"]
      FWL["🧱 EXAFWLFAL001 · FortiOS · .1"]
      SW1["🔀 EXASWIFAL001 · Cisco 9300 · .250"]
      SW2["🔀 EXASWIFAL002 · Cisco 9300 · .251"]

      subgraph BMC ["BMC Pool"]
          RAC1["🔧 EXARACFAL001 · Dell iDRAC9 · .2"]
          RAC2["🔧 EXARACFAL002 · Dell iDRAC9 · .3"]
          RAC3["🔧 EXARACFAL003 · Dell iDRAC9 · .4"]
      end

      subgraph PVE ["Proxmox Cluster (3-node)"]
          PVE1["🗂️ EXAPVEFAL001 · Proxmox node 1 · .5"]
          PVE2["🗂️ EXAPVEFAL002 · Proxmox node 2 · .6"]
          PVE3["🗂️ EXAPVEFAL003 · Proxmox node 3 · .7"]
      end

      subgraph DC ["Domain Controllers"]
          DC1["🗝️ EXADCSFAL001 · DC · PDC Emulator · .10"]
          DC2["🗝️ EXADCSFAL002 · DC secondary · .11"]
      end

      subgraph INFRA ["Infrastructure"]
          SBC["🛡️ EXASBCFAL001 · 3CX SBC → CLD PBX · .48"]
          RRY["🔁 EXARRYFAL001 · Rudder Relay · .12"]
          NAS["🗃️ EXANASFAL001 · FreeNAS 13.0-U6 · .32"]
          TAR["💽 EXATARFAL001 · Tape Archiver · .33"]
      end

      subgraph ENDPOINTS ["Endpoints"]
          WKS1["🖥️ EXAWKSFAL001 · Mixing Desk WKS · .100"]
          WKS2["🖥️ EXAWKSFAL002 · Reel-to-Reel WKS · .101"]
          WKS3["🖥️ EXAWKSFAL003 · Shared Editing WKS · .102"]
          LAP["💻 EXALAPFAL001 · Production Laptop · .103"]
          SUR["🖊️ EXASURFAL001 · Microsoft Surface · .104"]
          PHN["📞 EXAPHNFAL001-003 · Staff Phones"]
          PHN2["📞 EXAPHNFAL006-007 · Yealink T58A"]
          TAB["📱 EXATABFAL001 · Tablet"]
      end

      subgraph WAP_CAM ["Wireless & Security"]
          WAP["WAPs x6 · Ubiquiti UniFi U6-Pro · .5-.10"]
          CAM1["🎥 EXACAMFAL001 · Axis · Front entrance · .70"]
          CAM2["🎥 EXACAMFAL002 · Axis · Studio hallway · .71"]
          CAM3["🎥 EXACAMFAL003 · Axis · Car park · .72"]
          CAM4["🎥 EXACAMFAL004 · Axis · Loading bay · .73"]
          RDR["⚙️ EXARDRFAL001 · HID Signo Badge Reader · .16"]
      end

      subgraph SITE ["Site-Specific Equipment"]
          LCD["🖼️ EXALCDFAL001 · Samsung Tizen Display · .50"]
          VCU["🎧 EXAVCUFAL001 · Poly Studio X70 · .51"]
          JKB["💿 EXAMUSFAL001 · Pureline 128V Jukebox · .67"]
          PAY["☎️ EXAPAYFAL001 · GPO Kiosk No.6 Payphone · .95"]
          COF["🫖 EXATEAFAL001 · Smart Coffee Machine · .61"]
          VND1["🍩 EXADONFAL001 · Tim Hortons Vending · .62"]
          VND2["🍫 EXAVNDFAL002 · Irn-Bru Machine · .63"]
          VND3["🍫 EXAVNDFAL003 · McCowans Dispenser · .64"]
          VND4["🍫 EXAVNDFAL004 · Mrs Tily Dispenser · .65"]
          VND5["🍫 EXAVNDFAL005 · ¼lb Confectionery · .66"]
          PMP["⛽ EXAPMPFAL001 · Networked Petrol Pump · .60"]
          CLK["⏰ EXACLKFAL001 · NTP Clock · .80"]
      end

      VPN_CLD["🔗 WireGuard ← CLD · 10.0.76.0/24"]

      INET --> RTR --> FWL --> SW1 & SW2
      SW1 --> PVE1 & PVE2 & PVE3
      SW1 --> DC1 & DC2
      SW1 --> SBC & NAS & TAR
      SW2 --> WKS1
      SW2 --> WAP
      SW2 --> LCD
      RAC1 -.->|"manages"| PVE1
      RAC2 -.->|"manages"| PVE2
      RAC3 -.->|"manages"| PVE3
      FWL <-->|"WireGuard tunnel"| VPN_CLD

      SW1 --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN_CLD
    end
    style OLD_FAL fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:FAL:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRFAL001 · RTR · 192.168.76.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCFAL001 · BMC 1 · 192.168.76.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEFAL001 · PVE 1 · 192.168.76.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIFAL003 · SWI 3 · 192.168.76.252"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIFAL001 · Core switch 1 · 192.168.76.250"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIFAL002 · Core switch 2 · 192.168.76.251"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASFAL001 · Site NAS/SAN · 192.168.76.19"]
    T_RDR["🔐 EXARDRFAL001 · HID Signo badge reader · 192.168.76.16"]
    T_MUS["💿 EXAMUSFAL001 · Jukebox · 192.168.76.67"]
    T_WAP["📶 EXAWAPFAL001 · WAP 1 · 192.168.76.82"]
    T_SWI2 --> T_NAS --> T_RDR --> T_MUS --> T_WAP
    T_DCS["🗝️ EXADCSFAL001 · DCS 1 · 192.168.76.10"]
    T_SBC["🛡️ EXASBCFAL001 · SBC · 192.168.76.48"]
    T_FWL["🧱 EXAFWLFAL001 · LAN face · 192.168.76.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_OTHER["📎 Other devices — 46 confirmed, see devices.csv"]
    T_BMC --> T_OTHER
    style T_VRK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_MUS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_OTHER fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:FAL:END
```

---

## EDI — Edinburgh ⚠️ 🏰

**LAN:** `192.168.131.0/24` · **Domain:** `example.org` / `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
> ⚠️ `EXADCSEDI003` — DFSR stopped, C: drive at 5% free. Immediate action required.  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 131 496 0xxx · **Mobile:** +44 770 090 3xxx

```mermaid
graph TD
    subgraph OLD_EDI ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RTR["📡 EXARTREDI001 · Cisco ISR 4331 · .254"]
      SW1["🔀 EXASWIEDI001 · Cisco 2960X · .250"]
      SW2["🔀 EXASWIEDI002 · Cisco 2960X · .251"]
      RAC["🔧 EXARACEDI001 · Dell iDRAC9 · .2"]
      PVE["🗂️ EXAPVEEDI001 · Proxmox node 1 · .5"]
      DC["⚠️ 🗝️ EXADCSEDI003 · DC · DFSR stopped · C: 5% free · .11"]
      SBC["🛡️ EXASBCEDI001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYEDI001 · Rudder Relay · .12"]
      WKS["🖥️ EXAWKSEDI001 · Workstation · .150"]
      LAP["💻 EXALAPEDI098 · Pool Laptop · .108"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      COF["🫖 EXATEAEDI001 · Siemens EQ700 Coffee Machine · .60"]
      VPN["🔗 WireGuard → FAL"]

      INET --> RTR --> SW1 & SW2
      SW1 --> PVE --> DC
      SW1 --> SBC
      RAC -.->|"manages"| PVE
      SW2 --> WKS & LAP & WAP & CAM & COF
      RTR <-->|"WireGuard tunnel"| VPN

      SW1 --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_EDI fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:EDI:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTREDI001 · RTR · 192.168.131.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCEDI001 · BMC 1 · 192.168.131.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEEDI001 · PVE 1 · 192.168.131.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIEDI003 · SWI 3 · 192.168.131.252"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIEDI001 · Floor switch · 192.168.131.250"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIEDI002 · 48-port switch · 192.168.131.251"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASEDI001 · NAS · 192.168.131.19"]
    T_RDR["🔐 EXARDREDI001 · RDR · 192.168.131.21"]
    T_WAP["📶 EXAWAPEDI001 · WAP 1 · 192.168.131.82"]
    T_SWI2 --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSEDI001 · DCS 1 · 192.168.131.10"]
    T_SBC["🛡️ EXASBCEDI001 · SBC · 192.168.131.48"]
    T_FWL["🧱 EXAFWLEDI001 · LAN face · 192.168.131.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_OTHER["📎 Other devices — 5 confirmed, see devices.csv"]
    T_BMC --> T_OTHER
    style T_VRK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_OTHER fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:EDI:END
```

---

## GLA — Glasgow 🚧

**LAN:** `192.168.141.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 141 496 01xx · **Mobile:** +44 770 009 4xxx

```mermaid
graph TD
    subgraph OLD_GLA ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      PVE["🗂️ EXAPVEGLA001 · Proxmox node 1 · .5"]
      RAC["🔧 EXARACGLA001 · BMC node 1 · .2"]
      DC["🗝️ EXADCRGLA001 · DC · Schema/DN Master · PDC Emulator · .10"]
      SBC["🛡️ EXASBCGLA001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYGLA001 · Rudder Relay · .12"]
      WKS1["🖥️ EXAWKSGLA001 · Hot Desk WKS · .150"]
      WKS2["🖥️ EXAWKSGLA002 · Hot Desk WKS · .151"]
      LAP["💻 EXALAPGLA001 · Pool Laptop · .152"]
      PRN["🖨️ EXAPRNGLA001 · HP LaserJet Pro · .16"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> PVE
      PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WKS1 & WKS2 & LAP & PRN & WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_GLA fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:GLA:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRGLA001 · RTR · 192.168.141.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCGLA001 · BMC 1 · 192.168.141.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEGLA001 · PVE 1 · 192.168.141.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIGLA001 · SWI 1 · 192.168.141.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIGLA002 · SWI 2 · 192.168.141.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIGLA003 · SWI 3 · 192.168.141.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASGLA001 · NAS · 192.168.141.19"]
    T_RDR["🔐 EXARDRGLA001 · RDR · 192.168.141.21"]
    T_WAP["📶 EXAWAPGLA001 · WAP 1 · 192.168.141.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSGLA001 · DCS 1 · 192.168.141.10"]
    T_SBC["🛡️ EXASBCGLA001 · SBC · 192.168.141.48"]
    T_FWL["🧱 EXAFWLGLA001 · LAN face · 192.168.141.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_OTHER["📎 Other devices — 4 confirmed, see devices.csv"]
    T_BMC --> T_OTHER
    style T_VRK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_OTHER fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:GLA:END
```

---

## CLY — Clydebank 🚢

**LAN:** `192.168.41.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 141 496 00xx · **Mobile:** +44 770 090 5xxx

```mermaid
graph TD
    subgraph OLD_CLY ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWL["🧱 EXAFWLCLY001 · FortiOS 7.6.5 · .1"]
      RTR["📡 EXARTRCLY001 · Cisco ISR 4331 · .254"]
      SW["🔀 EXASWICLY001 · Cisco 9300 · .250"]
      RAC["🔧 EXARACCLY001 · HPE iLO5 · .2"]
      PVE["🗂️ EXAPVECLY001 · Proxmox node 1 · .5"]
      DC1["🗝️ EXADCSCLY001 · DC primary · .10"]
      DC2["🗝️ EXADCSCLY002 · DC secondary · .11"]
      SRV["🗄️ EXASRVCLY001 · Rocky Linux · Oracle DB · .20"]
      SBC["🛡️ EXASBCCLY001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYCLY001 · Rudder Relay · .12"]
      SUR["🖊️ EXASURCLY001 · Microsoft Surface · .51"]
      PHN["📞 EXAPHNCLY001 · iOS handset"]
      TAB["🖊️ EXASURCLY002 · Android Tablet"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> RTR --> FWL --> SW
      SW --> PVE --> DC1 & DC2 & SRV & SBC
      RAC -.->|"manages"| PVE
      SW --> SUR & PHN & TAB & WAP & CAM
      FWL <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_CLY fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:CLY:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRCLY001 · RTR · 192.168.41.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCCLY001 · BMC 1 · 192.168.41.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVECLY001 · PVE 1 · 192.168.41.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWICLY002 · SWI 2 · 192.168.41.251"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWICLY003 · SWI 3 · 192.168.41.252"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWICLY001 · Core switch · 192.168.41.250"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASCLY001 · NAS · 192.168.41.19"]
    T_RDR["🔐 EXARDRCLY001 · RDR · 192.168.41.21"]
    T_WAP["📶 EXAWAPCLY001 · WAP 1 · 192.168.41.82"]
    T_SWI3 --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSCLY001 · DCS 1 · 192.168.41.10"]
    T_SBC["🛡️ EXASBCCLY001 · SBC · 192.168.41.48"]
    T_FWL["🧱 EXAFWLCLY001 · LAN face · 192.168.41.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_OTHER["📎 Other devices — 4 confirmed, see devices.csv"]
    T_BMC --> T_OTHER
    style T_VRK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_OTHER fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:CLY:END
```

---

## DUN — Dundee 🛳️

**LAN:** `192.168.138.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 163 249 60xx · **Mobile:** +44 770 090 82xx

```mermaid
graph TD
    subgraph OLD_DUN ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RTR["📡 EXARTRDUN001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACDUN001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEDUN001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSDUN001 · DC · .10"]
      SBC["🛡️ EXASBCDUN001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYDUN001 · Rudder Relay · .12"]
      SUR1["🖊️ EXASURDUN001 · Surface · .51"]
      SUR2["🖊️ EXASURDUN002 · Surface · .52"]
      PHN1["📞 EXAPHNDUN001 · iOS Phone"]
      PHN2["📞 EXAPHNDUN002 · iOS Phone"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> RTR --> PVE
      PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      RTR --> SUR1 & SUR2 & PHN1 & PHN2 & WAP & CAM
      RTR <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_DUN fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:DUN:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRDUN001 · RTR · 192.168.138.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCDUN001 · BMC 1 · 192.168.138.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEDUN001 · PVE 1 · 192.168.138.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIDUN001 · SWI 1 · 192.168.138.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIDUN002 · SWI 2 · 192.168.138.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIDUN003 · SWI 3 · 192.168.138.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASDUN001 · NAS · 192.168.138.19"]
    T_RDR["🔐 EXARDRDUN001 · RDR · 192.168.138.21"]
    T_WAP["📶 EXAWAPDUN001 · WAP 1 · 192.168.138.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSDUN001 · DCS 1 · 192.168.138.10"]
    T_SBC["🛡️ EXASBCDUN001 · SBC · 192.168.138.48"]
    T_FWL["🧱 EXAFWLDUN001 · LAN face · 192.168.138.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_OTHER["📎 Other devices — 4 confirmed, see devices.csv"]
    T_BMC --> T_OTHER
    style T_VRK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_OTHER fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:DUN:END
```

---

## PER — Perth 👑

**LAN:** `192.168.173.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 173 849 60xx · **Mobile:** +44 770 0173 0xx

```mermaid
graph TD
    subgraph OLD_PER ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACPER001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEPER001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSPER001 · DC · .10"]
      SBC["🛡️ EXASBCPER001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYPER001 · Rudder Relay · .12"]
      NIX["🐧 EXANIXPER001 · Solaris 11.5 · MIDI/Music Archive · .40"]
      NAS["🗃️ EXANASPER001 · Synology NAS · .50"]
      MBP["💻 EXAMBPPER001 · MacBook Pro · .70"]
      SUR["🖊️ EXASURPER001 · Surface · .71"]
      PHN["📞 EXAPHNPER001-004 · Yealink T46G Phones · .80"]
      PRN["🖨️ EXAPRNPER001 · HP MFP Printer · .20"]
      VND["🍫 EXAVNDPER001 · Scone Palace Vending Machine · .60"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> PVE
      PVE --> DC & SBC & NIX & NAS
      RAC -.->|"manages"| PVE
      PVE --> MBP & SUR & PHN & PRN & VND & WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_PER fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:PER:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRPER001 · RTR · 192.168.173.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCPER001 · BMC 1 · 192.168.173.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEPER001 · PVE 1 · 192.168.173.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIPER001 · SWI 1 · 192.168.173.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIPER002 · SWI 2 · 192.168.173.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIPER003 · SWI 3 · 192.168.173.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASPER001 · NAS · 192.168.173.19"]
    T_RDR["🔐 EXARDRPER001 · RDR · 192.168.173.21"]
    T_WAP["📶 EXAWAPPER001 · WAP 1 · 192.168.173.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSPER001 · DCS 1 · 192.168.173.10"]
    T_SBC["🛡️ EXASBCPER001 · SBC · 192.168.173.48"]
    T_FWL["🧱 EXAFWLPER001 · LAN face · 192.168.173.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_OTHER["📎 Other devices — 9 confirmed, see devices.csv"]
    T_BMC --> T_OTHER
    style T_VRK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_OTHER fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:PER:END
```

---

## ABD — Aberdeen 🪨

**LAN:** `192.168.224.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 1224 496 0xxx · **Mobile:** +44 7700 900 2xxx

```mermaid
graph TD
    subgraph OLD_ABD ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWL["🧱 EXAFWLABD001 · Cisco ASA 5506-X · .1"]
      RTR["📡 EXARTRABD001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACABD001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEABD001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSABD001 · DC · .10"]
      SBC["🛡️ EXASBCABD001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYABD001 · Rudder Relay · .12"]
      MBP1["💻 EXAMBPABD001 · MacBook · .137"]
      MBP2["💻 EXAMBPABD002 · MacBook · .124"]
      PHN1["📞 EXAPHNABD001 · Corporate iPhone"]
      PHN2["📞 EXAPHNABD002 · Corporate iPhone"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> RTR --> FWL --> PVE
      PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      FWL --> MBP1 & MBP2 & PHN1 & PHN2 & WAP & CAM
      FWL <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_ABD fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:ABD:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRABD001 · RTR · 192.168.224.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCABD001 · BMC 1 · 192.168.224.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEABD001 · PVE 1 · 192.168.224.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIABD001 · SWI 1 · 192.168.224.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIABD002 · SWI 2 · 192.168.224.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIABD003 · SWI 3 · 192.168.224.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASABD001 · NAS · 192.168.224.19"]
    T_RDR["🔐 EXARDRABD001 · RDR · 192.168.224.21"]
    T_WAP["📶 EXAWAPABD001 · WAP 1 · 192.168.224.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSABD001 · DCS 1 · 192.168.224.10"]
    T_SBC["🛡️ EXASBCABD001 · SBC · 192.168.224.48"]
    T_FWL["🧱 EXAFWLABD001 · LAN face · 192.168.224.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_OTHER["📎 Other devices — 4 confirmed, see devices.csv"]
    T_BMC --> T_OTHER
    style T_VRK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_OTHER fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:ABD:END
```
