# Example Music Limited — New Zealand Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## AKL — Auckland ⚠️ ⛵

**LAN:** `192.168.93.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSAKL001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (New Zealand) Tapui · **Landline:** +64 9 300 0xxx · **Mobile:** +64 21 900 2xxx

```mermaid
graph TD
    subgraph OLD_AKL ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWL["🧱 EXAFWLAKL001 · FortiGate 7.x · .1"]
      SW1["🔀 EXASWIAKL001 · Cisco 9300 · .250"]
      SW2["🔀 EXASWIAKL002 · Cisco 2960 · .251"]
      RTR["📡 EXARTRAKL001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACAKL001 · HPE iLO5 · .2"]
      PVE["🗂️ EXAPVEAKL001 · Proxmox node 1 · .5"]
      DC["🔴 🗝️ EXADCSAKL001 · DC · Services stopped · .10"]
      SRV["🗄️ EXASRVAKL001 · WS2022 Local Server · .20"]
      SBC["🛡️ EXASBCAKL001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYAKL001 · Rudder Relay · .12"]
      WKS["🖥️ EXAWKSAKL001 · Win11 Workstation · .40"]
      MBP["💻 EXAMBPAKL001 · MacBook Pro · .41"]
      PHN["📞 EXAPHNAKL001 · Android Phone"]
      TAB["📱 EXATABAKL001 · iPad · .60"]
      WAP1["📶 EXAWAPAKL001 · Ubiquiti UniFi"]
      WAP2["📶 EXAWAPAKL002 · Ubiquiti UniFi"]
      CAM["🎥 EXACAMAKL001 · Axis Camera · .82"]
      LCD["🖼️ EXALCDAKL001 · Samsung Signage · .70"]
      PRN["🖨️ EXAPRNAKL001 · HP LaserJet · .80"]
      COF["🍵 EXACOFAKL001 · Smart Coffee Machine · .83"]
      VPN["🔗 WireGuard → BRK"]

      INET --> RTR --> FWL --> SW1 & SW2
      SW1 --> PVE --> DC & SRV & SBC
      RAC -.->|"manages"| PVE
      SW2 --> WKS & MBP & PHN & TAB & WAP1 & WAP2
      SW2 --> CAM & LCD & PRN & COF
      FWL <-->|"WireGuard tunnel"| VPN

      SW1 --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_AKL fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:AKL:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRAKL001 · RTR · 192.168.93.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCAKL001 · BMC 1 · 192.168.93.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEAKL001 · PVE 1 · 192.168.93.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIAKL003 · SWI 3 · 192.168.93.252"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIAKL001 · Core switch · 192.168.93.250"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIAKL002 · Access switch · 192.168.93.251"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASAKL001 · NAS · 192.168.93.19"]
    T_RDR["🔐 EXARDRAKL001 · RDR · 192.168.93.21"]
    T_WAP["📶 EXAWAPAKL001 · WAP 1 · 192.168.93.82"]
    T_SWI2 --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSAKL001 · DCS 1 · 192.168.93.10"]
    T_SBC["🛡️ EXASBCAKL001 · SBC · 192.168.93.48"]
    T_FWL["🧱 EXAFWLAKL001 · LAN face · 192.168.93.253"]
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
%% GENERATED:TOPOLOGY:AKL:END
```

---

*Example Music Limited — Internal Infrastructure Documentation*   *Do not distribute outside the organisation*cloud
