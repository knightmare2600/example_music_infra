# Example Music Limited — Deutschland Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## BON — Bonn 🎼

**LAN:** `192.168.228.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Note:** Hosts Schema Master + Domain Naming Master  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 228 555 xxx · **Mobile:** +49 211 xxx xxxx

```mermaid
graph TD
    subgraph OLD_BON ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      SW["🔀 EXASWIBON001 · Cisco 2960X · .250"]
      RTR["📡 EXARTRBON001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACBON001 · Dell iDRAC9 · .2"]
      PVE["🗂️ EXAPVEBON001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSBON001 · DC · Schema Master · DN Master · .10"]
      SBC["🛡️ EXASBCBON001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYBON001 · Rudder Relay · .12"]
      WKS["🖥️ EXAWKSBON001 · Finance WKS · .151"]
      LAP1["💻 EXALAPBON001 · ThinkPad ⚠️ disabled · .150"]
      LAP2["💻 EXALAPBON002 · Finance Laptop · .153"]
      VCU["🎧 EXAVCUBON001 · Poly Studio X70 · Boardroom · .2"]
      CAM["🎥 EXACAMBON001 · Axis P3245-LVE CCTV · .17"]
      TV["📺 EXATVSBON001 · Samsung 65in · .18"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      VPN["🔗 WireGuard → ODE"]

      INET --> RTR --> SW
      SW --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      SW --> WKS & LAP1 & LAP2 & VCU & CAM & TV & WAP
      RTR <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_BON fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:BON:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRBON001 · RTR · 192.168.228.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCBON001 · BMC 1 · 192.168.228.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEBON001 · PVE 1 · 192.168.228.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIBON002 · SWI 2 · 192.168.228.251"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIBON003 · SWI 3 · 192.168.228.252"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIBON001 · Office switch · 192.168.228.250"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASBON001 · NAS · 192.168.228.19"]
    T_RDR["🔐 EXARDRBON001 · RDR · 192.168.228.21"]
    T_WAP["📶 EXAWAPBON001 · WAP 1 · 192.168.228.82"]
    T_SWI3 --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSBON001 · DCS 1 · 192.168.228.10"]
    T_SBC["🛡️ EXASBCBON001 · SBC · 192.168.228.48"]
    T_FWL["🧱 EXAFWLBON001 · LAN face · 192.168.228.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_OTHER["📎 Other devices — 6 confirmed, see devices.csv"]
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
%% GENERATED:TOPOLOGY:BON:END
```

---

## BER — West Berlin 🐻

**LAN:** `192.168.113.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 311 555 xxx · **Mobile:** +49 211 xxx xxxx

```mermaid
graph TD
    subgraph OLD_BER ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RTR["📡 EXARTRBER001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACBER001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEBER001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSBER001 · DC · PDC Emulator · RID/Infra Master WS2019 · .10"]
      SBC["🛡️ EXASBCBER001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYBER001 · Rudder Relay · .12"]
      SRV["🗄️ EXASRVBER001 · WS2019 Legacy App Server · .21"]
      NIX["🐧 EXANIXBER001 · Debian 12 Server · .22"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → ODE"]

      INET --> RTR --> PVE --> DC & SBC & SRV & NIX
      RAC -.->|"manages"| PVE
      RTR --> WAP & CAM
      RTR <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_BER fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:BER:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRBER001 · RTR · 192.168.113.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCBER001 · BMC 1 · 192.168.113.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEBER001 · PVE 1 · 192.168.113.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIBER001 · SWI 1 · 192.168.113.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIBER002 · SWI 2 · 192.168.113.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIBER003 · SWI 3 · 192.168.113.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASBER001 · NAS · 192.168.113.19"]
    T_RDR["🔐 EXARDRBER001 · RDR · 192.168.113.21"]
    T_WAP["📶 EXAWAPBER001 · WAP 1 · 192.168.113.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSBER001 · DCS 1 · 192.168.113.10"]
    T_SBC["🛡️ EXASBCBER001 · SBC · 192.168.113.48"]
    T_FWL["🧱 EXAFWLBER001 · LAN face · 192.168.113.253"]
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
%% GENERATED:TOPOLOGY:BER:END
```

---

## MUN — Munich 🍺

**LAN:** `192.168.189.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 893 555 33xx · **Mobile:** +49 893 555 99xx

```mermaid
graph TD
    subgraph OLD_MUN ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      SW["🔀 EXASWIMUN001 · Cisco 9200 · .250"]
      RAC["🔧 EXARACMUN001 · HPE iLO5 · .2"]
      PVE["🗂️ EXAPVEMUN001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSMUN001 · DC · .10"]
      SBC["🛡️ EXASBCMUN001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYMUN001 · Rudder Relay · .12"]
      WKS["🖥️ EXAWKSMUN001 · Hot Desk WKS · .150"]
      LAP1["💻 EXALAPMUN001 · Pool Laptop · .151"]
      LAP2["⚠️ 💻 EXALAPMUN002 · Pool Laptop · LAPS expired 61d · .152"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → ODE"]

      INET --> SW
      SW --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      SW --> WKS & LAP1 & LAP2 & WAP & CAM
      SW <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_MUN fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:MUN:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRMUN001 · RTR · 192.168.189.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCMUN001 · BMC 1 · 192.168.189.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEMUN001 · PVE 1 · 192.168.189.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIMUN002 · SWI 2 · 192.168.189.251"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIMUN003 · SWI 3 · 192.168.189.252"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIMUN001 · Access switch · 192.168.189.250"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASMUN001 · NAS · 192.168.189.19"]
    T_RDR["🔐 EXARDRMUN001 · RDR · 192.168.189.21"]
    T_WAP["📶 EXAWAPMUN001 · WAP 1 · 192.168.189.82"]
    T_SWI3 --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSMUN001 · DCS 1 · 192.168.189.10"]
    T_SBC["🛡️ EXASBCMUN001 · SBC · 192.168.189.48"]
    T_FWL["🧱 EXAFWLMUN001 · LAN face · 192.168.189.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_WKS["🖥️ EXAWKSMUN001 · Hot desk workstation"]
    T_LAP["💻 EXALAPMUN001 · Pool laptop"]
    T_LAP2["💻 EXALAPMUN002 · LAPS expired"]
    T_BMC --> T_WKS --> T_LAP --> T_LAP2
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
    style T_WKS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_LAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_LAP2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:MUN:END
```

---

## DRS — Dresden 🕺

**LAN:** `192.168.153.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 351 555 xxx · **Mobile:** +49 172 xxx xxxx

```mermaid
graph TD
    subgraph OLD_DRS ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACDRS001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEDRS001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSDRS001 · DC · .10"]
      SBC["🛡️ EXASBCDRS001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYDRS001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → ODE"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_DRS fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:DRS:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRDRS001 · RTR · 192.168.153.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCDRS001 · BMC 1 · 192.168.153.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEDRS001 · PVE 1 · 192.168.153.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIDRS001 · SWI 1 · 192.168.153.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIDRS002 · SWI 2 · 192.168.153.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIDRS003 · SWI 3 · 192.168.153.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASDRS001 · NAS · 192.168.153.19"]
    T_RDR["🔐 EXARDRDRS001 · RDR · 192.168.153.21"]
    T_WAP["📶 EXAWAPDRS001 · WAP 1 · 192.168.153.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSDRS001 · DCS 1 · 192.168.153.10"]
    T_SBC["🛡️ EXASBCDRS001 · SBC · 192.168.153.48"]
    T_FWL["🧱 EXAFWLDRS001 · LAN face · 192.168.153.253"]
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
%% GENERATED:TOPOLOGY:DRS:END
```

---

## DUS — Düsseldorf 👗

**LAN:** `192.168.211.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 211 555 xxx · **Mobile:** +49 172 xxx xxxx

```mermaid
graph TD
    subgraph OLD_DUS ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACDUS001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEDUS001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSDUS001 · DC · .10"]
      SBC["🛡️ EXASBCDUS001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYDUS001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → ODE"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_DUS fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:DUS:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRDUS001 · RTR · 192.168.211.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCDUS001 · BMC 1 · 192.168.211.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEDUS001 · PVE 1 · 192.168.211.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIDUS001 · SWI 1 · 192.168.211.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIDUS002 · SWI 2 · 192.168.211.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIDUS003 · SWI 3 · 192.168.211.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASDUS001 · NAS · 192.168.211.19"]
    T_RDR["🔐 EXARDRDUS001 · RDR · 192.168.211.21"]
    T_WAP["📶 EXAWAPDUS001 · WAP 1 · 192.168.211.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSDUS001 · DCS 1 · 192.168.211.10"]
    T_SBC["🛡️ EXASBCDUS001 · SBC · 192.168.211.48"]
    T_FWL["🧱 EXAFWLDUS001 · LAN face · 192.168.211.253"]
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
%% GENERATED:TOPOLOGY:DUS:END
```
