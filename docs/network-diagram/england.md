# Example Music Limited — England Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## LND — London 🥑

**LAN:** `192.168.20.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 207 496 0xxx · **Mobile:** +44 770 090 0xxx

```mermaid
graph TD
    subgraph OLD_LND ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWL["🧱 EXAFWLLND001 · Cisco ASA 5516-X · .1"]
      SW["🔀 EXASWILND001 · Cisco 9300 · .250"]
      RTR["📡 EXARTRLND001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACLND001 · Dell iDRAC9 · .2"]
      PVE["🗂️ EXAPVELND001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCRLND001 · DC · RID/Infra Master · .10"]
      SBC["🛡️ EXASBCLND001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYLND001 · Rudder Relay · .12"]
      WKS["🖥️ EXAWKSLND001 · Hot Desk WKS · .150"]
      PRN1["🖨️ EXAPRNLND001 · Xerox WorkCentre · .16"]
      PRN2["🖨️ EXAPRNLND002 · ProCAT Steno Writer · Court Device"]
      RAD["📻 EXARADLND001 · BBC Office Radio Mk II · .80"]
      MIC["🎤 EXAMICLND001 · Shure SM7 Microphone · Dante Audio · .81"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> RTR --> FWL --> SW
      SW --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      SW --> WKS & PRN1 & PRN2 & RAD & MIC & WAP & CAM
      FWL <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_LND fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:LND:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRLND001 · RTR · 192.168.20.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCLND001 · BMC 1 · 192.168.20.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVELND001 · PVE 1 · 192.168.20.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWILND002 · SWI 2 · 192.168.20.251"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWILND003 · SWI 3 · 192.168.20.252"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWILND001 · Core switch · 192.168.20.250"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASLND001 · NAS · 192.168.20.19"]
    T_RDR["🔐 EXARDRLND001 · RDR · 192.168.20.21"]
    T_WAP["📶 EXAWAPLND001 · WAP 1 · 192.168.20.82"]
    T_SWI3 --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSLND001 · DCS 1 · 192.168.20.10"]
    T_SBC["🛡️ EXASBCLND001 · SBC · 192.168.20.48"]
    T_FWL["🧱 EXAFWLLND001 · LAN face · 192.168.20.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_RAD["📻 EXARADLND001 · BBC Office Radio Mk II · 192.168.20.80"]
    T_MIC["🎤 EXAMICLND001 · Shure SM7 via Dante audio · 192.168.20.81"]
    T_WKS["🖥️ EXAWKSLND001 · Workstation · 192.168.20.150"]
    T_OTH_PRN["🖨️ 2x Printers · EXAPRNLND001-002 · No IP Address"]
    T_RAD --> T_WKS
    T_MIC --> T_OTH_PRN
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
    style T_RAD fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_MIC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WKS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_OTH_PRN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:LND:END
```

---

## BIR — Birmingham 🪠

**LAN:** `192.168.121.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 121 496 0xxx · **Mobile:** +44 7700 900 2xxx

```mermaid
graph TD
    subgraph OLD_BIR ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWL["🧱 EXAFWLBIR001 · Palo Alto PAN-OS · .1"]
      SW1["🔀 EXASWIBIR001 · Cisco 9300 · .250"]
      SW2["🔀 EXASWIBIR002 · Access Switch · .251"]
      RTR["📡 EXARTRBIR001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACBIR001 · Dell DRAC · .2"]
      PVE["🗂️ EXAPVEBIR001 · Proxmox node 1 · .5"]
      DC1["🗝️ EXADCRBIR001 · DC primary · .10"]
      DC2["🗝️ EXADCRBIR002 · DC secondary · .11"]
      SRV["🗄️ EXASRVBIR001 · Rocky Linux · Oracle DB · .20"]
      SBC["🛡️ EXASBCBIR001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYBIR001 · Rudder Relay · .12"]
      MBP["💻 EXAMBPBIR001 · MacBook Pro · .41"]
      TAB["📱 EXATABBIR001 · Samsung Galaxy Tab · .61"]
      PHN["📞 EXAPHNBIR001 · Samsung S25 Ultra"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      MOO["🎹 EXAMOOBIR001 · Moog One Synthesizer · .70"]
      LIN["🥁 EXALINBIR001 · LinnDrum LM-2 · .71"]
      FCL["🎹 EXAFCLBIR001 · Fairlight CMI IIx · .72"]
      AST["🕹️ EXAASTBIR001 · Atari ST · MIDI · .73"]
      PAY["☎️ EXAPAYBIR001 · GPO Kiosk No.6 Payphone · .74"]
      LCD["🖼️ EXALCDBIR001 · NEC PlasmaSync NOC Display · .75"]
      VPN["🔗 WireGuard → FAL"]

      INET --> RTR --> FWL --> SW1 & SW2
      SW1 --> PVE --> DC1 & DC2 & SRV & SBC
      RAC -.->|"manages"| PVE
      SW2 --> MBP & TAB & PHN & WAP & CAM
      SW2 --> MOO & LIN & FCL & AST & PAY & LCD
      FWL <-->|"WireGuard tunnel"| VPN

      SW1 --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_BIR fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:BIR:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRBIR001 · RTR · 192.168.121.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCBIR001 · BMC 1 · 192.168.121.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEBIR001 · PVE 1 · 192.168.121.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIBIR003 · SWI 3 · 192.168.121.252"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIBIR001 · Core switch · 192.168.121.250"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIBIR002 · Access switch · 192.168.121.251"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASBIR001 · NAS · 192.168.121.19"]
    T_RDR["🔐 EXARDRBIR001 · RDR · 192.168.121.21"]
    T_WAP["📶 EXAWAPBIR001 · WAP 1 · 192.168.121.82"]
    T_SWI2 --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSBIR001 · DCS 1 · 192.168.121.10"]
    T_SBC["🛡️ EXASBCBIR001 · SBC · 192.168.121.48"]
    T_FWL["🧱 EXAFWLBIR001 · LAN face · 192.168.121.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_SRV["🗄️ EXASRVBIR001 · Oracle DB · 192.168.121.20"]
    T_MOO["🎹 EXAMOOBIR001 · Moog synth · 192.168.121.70"]
    T_LIN["🥁 EXALINBIR001 · Drum machine · 192.168.121.71"]
    T_FCL["🎹 EXAFCLBIR001 · Fairlight CMI · 192.168.121.72"]
    T_AST["🕹️ EXAASTBIR001 · Atari ST · 192.168.121.73"]
    T_PAY["☎️ EXAPAYBIR001 · Payphone · 192.168.121.74"]
    T_LCD["🖼️ EXALCDBIR001 · NOC display · 192.168.121.75"]
    T_MBP["💻 EXAMBPBIR001 · MacBook"]
    T_TAB["📱 EXATABBIR001 · Galaxy Tab"]
    T_PHN["📞 EXAPHNBIR001 · Samsung S25"]
    T_SRV --> T_LIN --> T_AST --> T_LCD --> T_TAB
    T_MOO --> T_FCL --> T_PAY --> T_MBP --> T_PHN
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
    style T_SRV fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_MOO fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_LIN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FCL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_AST fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PAY fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_LCD fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_MBP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_TAB fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PHN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:BIR:END
```

---

## MCR — Manchester 🐝

**LAN:** `192.168.161.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 161 715 xxxx · **Mobile:** +44 770 090 6xxx

```mermaid
graph TD
    subgraph OLD_MCR ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      SW["🔀 EXASWIMCR001 · Cisco 9300 · .250"]
      RAC["🔧 EXARACMCR001 · HPE iLO5 · .2"]
      PVE["🗂️ EXAPVEMCR001 · Proxmox node 1 · .5"]
      DC1["🗝️ EXADCRMCR001 · DC PDC · RID/Infra Master · .10"]
      DC2["🗝️ EXADCSMCR002 · DC secondary · .11"]
      SBC["🛡️ EXASBCMCR001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYMCR001 · Rudder Relay · .12"]
      LAP1["💻 EXALAPMCR001 · Win11 Laptop · .19"]
      LAP2["💻 EXALAPMCR002 · Win11 Laptop · .150"]
      WKS1["🖥️ EXAWKSMCR001 · Front Desk WKS · .152"]
      WKS2["🖥️ EXAWKSMCR002 · Finance WKS · .153"]
      PRN["🖨️ EXAPRNMCR001 · Network Printer · .16"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> SW
      SW --> PVE --> DC1 & DC2 & SBC
      RAC -.->|"manages"| PVE
      SW --> LAP1 & LAP2 & WKS1 & WKS2 & PRN & WAP & CAM
      SW <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_MCR fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:MCR:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRMCR001 · RTR · 192.168.161.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCMCR001 · BMC 1 · 192.168.161.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEMCR001 · PVE 1 · 192.168.161.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIMCR002 · SWI 2 · 192.168.161.251"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIMCR003 · SWI 3 · 192.168.161.252"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIMCR001 · Distribution switch · 192.168.161.250"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASMCR001 · NAS · 192.168.161.19"]
    T_RDR["🔐 EXARDRMCR001 · RDR · 192.168.161.21"]
    T_WAP["📶 EXAWAPMCR001 · WAP 1 · 192.168.161.82"]
    T_SWI3 --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSMCR001 · DCS 1 · 192.168.161.10"]
    T_SBC["🛡️ EXASBCMCR001 · SBC · 192.168.161.48"]
    T_FWL["🧱 EXAFWLMCR001 · LAN face · 192.168.161.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_OTH_LAP["💻 2x Laptops · EXALAPMCR001-002 · No IP Address"]
    T_OTH_WKS["🖥️ 2x Workstations · EXAWKSMCR001-002 · No IP Address"]
    T_PRN["🖨️ EXAPRNMCR001 · Printer"]
    T_OTH_LAP --> T_PRN
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
    style T_OTH_LAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_OTH_WKS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PRN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:MCR:END
```

---

## LIV — Liverpool 🎸

**LAN:** `192.168.151.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 151 496 0xxx · **Mobile:** +44 770 090 5xxx

```mermaid
graph TD
    subgraph OLD_LIV ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      SW["🔀 EXASWILIV001 · Cisco 9200 · .250"]
      RAC["🔧 EXARACLIV001 · HPE iLO5 · .2"]
      PVE["🗂️ EXAPVELIV001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCRLIV001 · DC · WS2025 · .10"]
      SBC["🛡️ EXASBCLIV001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYLIV001 · Rudder Relay · .12"]
      SRV["🗄️ EXASVRLIV001 · WS2022 File Server · .10"]
      MBP["💻 EXAMBPLIV001 · MacBook Pro · macOS Tahoe · .150"]
      MAC["🍎 EXAMACLIV001 · iMac ⚠️ disabled · .152"]
      RDR["⚙️ EXARDRLIV002 · HID Signo Badge Reader · .16"]
      BPS["🪪 EXABPSLIV001 · Badge Programming WKS · .17"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> SW
      SW --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      SW --> SRV & MBP & MAC & RDR & BPS & WAP & CAM
      SW <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_LIV fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:LIV:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRLIV001 · RTR · 192.168.151.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCLIV001 · BMC 1 · 192.168.151.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVELIV001 · PVE 1 · 192.168.151.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWILIV002 · SWI 2 · 192.168.151.251"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWILIV003 · SWI 3 · 192.168.151.252"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWILIV001 · Core switch · 192.168.151.250"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASLIV001 · NAS · 192.168.151.19"]
    T_RDR["🔐 EXARDRLIV002 · HID Signo badge reader · 192.168.151.21"]
    T_WAP["📶 EXAWAPLIV001 · WAP 1 · 192.168.151.82"]
    T_SWI3 --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSLIV001 · DCS 1 · 192.168.151.10"]
    T_SVR["🗄️ EXASVRLIV001 · File server"]
    T_SBC["🛡️ EXASBCLIV001 · SBC · 192.168.151.48"]
    T_FWL["🧱 EXAFWLLIV001 · LAN face · 192.168.151.253"]
    T_PVE --> T_DCS --> T_SVR --> T_SBC --> T_FWL
    T_MBP["💻 EXAMBPLIV001 · MacBook Pro"]
    T_MAC["🍎 EXAMACLIV001 · iMac DISABLED"]
    T_BPS["🪪 EXABPSLIV001 · Badge programming workstation"]
    T_MBP --> T_BPS
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
    style T_SVR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_MBP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_MAC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BPS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:LIV:END
```

---

## NEW — Newcastle 🌉

**LAN:** `192.168.191.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 191 496 0xxx · **Mobile:** +44 770 090 9xxx

```mermaid
graph TD
    subgraph OLD_NEW ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      SW["🔀 EXASWINEW001 · TP-Link JetStream · .250"]
      RAC["🔧 EXARACNEW001 · Dell iDRAC9 · .2"]
      PVE["🗂️ EXAPVENEW001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCRNEW001 · DC · .10"]
      SBC["🛡️ EXASBCNEW001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYNEW001 · Rudder Relay · .12"]
      SRV["🗄️ EXASRVNEW001 · WS2022 File/Print Server · .21"]
      WKS["⚠️ 🖥️ EXAWKSNEW099 · Win11 WKS · LAPS expired · .161"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> SW
      SW --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      SW --> SRV & WKS & WAP & CAM
      SW <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_NEW fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:NEW:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRNEW001 · RTR · 192.168.191.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCNEW001 · BMC 1 · 192.168.191.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVENEW001 · PVE 1 · 192.168.191.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWINEW002 · SWI 2 · 192.168.191.251"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWINEW003 · SWI 3 · 192.168.191.252"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWINEW001 · Access switch · 192.168.191.250"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASNEW001 · NAS · 192.168.191.19"]
    T_RDR["🔐 EXARDRNEW001 · RDR · 192.168.191.21"]
    T_WAP["📶 EXAWAPNEW001 · WAP 1 · 192.168.191.82"]
    T_SWI3 --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSNEW001 · DCS 1 · 192.168.191.10"]
    T_SBC["🛡️ EXASBCNEW001 · SBC · 192.168.191.48"]
    T_FWL["🧱 EXAFWLNEW001 · LAN face · 192.168.191.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_SRV["🗄️ EXASRVNEW001 · File/print server"]
    T_WKS["🖥️ EXAWKSNEW099 · LAPS password expired"]
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
    style T_SRV fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WKS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:NEW:END
```

---

## SHE — Sheffield 🥄

**LAN:** `192.168.114.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 114 250 0xxx · **Mobile:** +44 7700 905 2xxx

```mermaid
graph TD
    subgraph OLD_SHE ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACSHE001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVESHE001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSSHE001 · DC · .10"]
      SBC["🛡️ EXASBCSHE001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYSHE001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      EP["Endpoints TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM & EP
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_SHE fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:SHE:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRSHE001 · RTR · 192.168.114.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCSHE001 · BMC 1 · 192.168.114.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVESHE001 · PVE 1 · 192.168.114.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWISHE001 · SWI 1 · 192.168.114.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWISHE002 · SWI 2 · 192.168.114.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWISHE003 · SWI 3 · 192.168.114.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASSHE001 · NAS · 192.168.114.19"]
    T_RDR["🔐 EXARDRSHE001 · RDR · 192.168.114.21"]
    T_WAP["📶 EXAWAPSHE001 · WAP 1 · 192.168.114.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSSHE001 · DCS 1 · 192.168.114.10"]
    T_SBC["🛡️ EXASBCSHE001 · SBC · 192.168.114.48"]
    T_FWL["🧱 EXAFWLSHE001 · LAN face · 192.168.114.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
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
%% GENERATED:TOPOLOGY:SHE:END
```

---

## HAL — Halifax 🏦

**LAN:** `192.168.142.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 1422 200 0xxx · **Mobile:** +44 7700 904 2xxx

```mermaid
graph TD
    subgraph OLD_HAL ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACHAL001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEHAL001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSHAL001 · DC · .10"]
      SBC["🛡️ EXASBCHAL001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYHAL001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      EP["Endpoints TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM & EP
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_HAL fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:HAL:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRHAL001 · RTR · 192.168.142.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCHAL001 · BMC 1 · 192.168.142.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEHAL001 · PVE 1 · 192.168.142.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIHAL001 · SWI 1 · 192.168.142.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIHAL002 · SWI 2 · 192.168.142.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIHAL003 · SWI 3 · 192.168.142.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASHAL001 · NAS · 192.168.142.19"]
    T_RDR["🔐 EXARDRHAL001 · RDR · 192.168.142.21"]
    T_WAP["📶 EXAWAPHAL001 · WAP 1 · 192.168.142.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSHAL001 · DCS 1 · 192.168.142.10"]
    T_SBC["🛡️ EXASBCHAL001 · SBC · 192.168.142.48"]
    T_FWL["🧱 EXAFWLHAL001 · LAN face · 192.168.142.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
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
%% GENERATED:TOPOLOGY:HAL:END
```

---

## HUL — Hull 🎣

**LAN:** `192.168.148.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 1482 300 0xxx · **Mobile:** +44 7700 902 2xxx

```mermaid
graph TD
    subgraph OLD_HUL ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACHUL001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEHUL001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSHUL001 · DC · .10"]
      SBC["🛡️ EXASBCHUL001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYHUL001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      EP["Endpoints TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM & EP
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_HUL fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:HUL:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRHUL001 · RTR · 192.168.148.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCHUL001 · BMC 1 · 192.168.148.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEHUL001 · PVE 1 · 192.168.148.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIHUL001 · SWI 1 · 192.168.148.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIHUL002 · SWI 2 · 192.168.148.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIHUL003 · SWI 3 · 192.168.148.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASHUL001 · NAS · 192.168.148.19"]
    T_RDR["🔐 EXARDRHUL001 · RDR · 192.168.148.21"]
    T_WAP["📶 EXAWAPHUL001 · WAP 1 · 192.168.148.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSHUL001 · DCS 1 · 192.168.148.10"]
    T_SBC["🛡️ EXASBCHUL001 · SBC · 192.168.148.48"]
    T_FWL["🧱 EXAFWLHUL001 · LAN face · 192.168.148.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
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
%% GENERATED:TOPOLOGY:HUL:END
```

---

## COV — Coventry 🐎

**LAN:** `192.168.247.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
*Note: WAP/RTR-only site — minimal infrastructure.*  
**Entity:** Example Music (England) Ltd · **Landline:** +44 247 765 0xxx · **Mobile:** +44 7700 901 2xxx

```mermaid
graph TD
    subgraph OLD_COV ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RTR["📡 EXARTRCOV001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACCOV001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVECOV001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSCOV001 · DC · .10"]
      SBC["🛡️ EXASBCCOV001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYCOV001 · Rudder Relay · .12"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> RTR --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      RTR --> WAP & CAM
      RTR <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_COV fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:COV:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRCOV001 · RTR · 192.168.247.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCCOV001 · BMC 1 · 192.168.247.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVECOV001 · PVE 1 · 192.168.247.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWICOV001 · SWI 1 · 192.168.247.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWICOV002 · SWI 2 · 192.168.247.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWICOV003 · SWI 3 · 192.168.247.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASCOV001 · NAS · 192.168.247.19"]
    T_RDR["🔐 EXARDRCOV001 · RDR · 192.168.247.21"]
    T_WAP["📶 EXAWAPCOV001 · WAP 1 · 192.168.247.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSCOV001 · DCS 1 · 192.168.247.10"]
    T_SBC["🛡️ EXASBCCOV001 · SBC · 192.168.247.48"]
    T_FWL["🧱 EXAFWLCOV001 · LAN face · 192.168.247.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
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
%% GENERATED:TOPOLOGY:COV:END
```
