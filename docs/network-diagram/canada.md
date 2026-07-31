# Example Music Limited — Canada Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## BRK — Brockville *(NA/APAC Hub)* ⭐ 🍁

**LAN:** `192.168.136.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (NA/APAC hub) · **VPN parent:** CLD (NA/APAC backup)  
> ⚠️ `EXADCSBRK001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (Canada) Inc. · **Landline:** +1 613 555 6xxx · **Mobile:** +1 613 555 6xxx

```mermaid
graph TD
    subgraph OLD_BRK ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RTR["📡 EXARTRBRK001 · Cisco ISR 4331 · .254"]

      subgraph BMC ["BMC Pool"]
          RAC1["🔧 EXARACBRK001 · BMC node 1 · .2"]
          RAC2["🔧 EXARACBRK002 · BMC node 2 · .3"]
          RAC3["🔧 EXARACBRK003 · BMC node 3 · .4"]
      end

      subgraph PVE ["Proxmox Cluster (3-node)"]
          PVE1["🗂️ EXAPVEBRK001 · Proxmox node 1 · .5"]
          PVE2["🗂️ EXAPVEBRK002 · Proxmox node 2 · .6"]
          PVE3["🗂️ EXAPVEBRK003 · Proxmox node 3 · .7"]
      end

      DC["🔴 🗝️ EXADCSBRK001 · DC · Services stopped · .10"]
      SBC["🛡️ EXASBCBRK001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYBRK001 · Rudder Relay · .12"]
      LAP["💻 EXALAPBRK001 · Win11 Tour Laptop · .21"]
      WAP["📶 EXAWAPBRK001 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VND1["🍩 EXADONBRK001 · Tim Hortons Donut Vending · .60"]
      VND2["🍫 EXAVNDBRK001 · Maple Syrup Vending · .61"]
      VPN_CLD["🔗 WireGuard ← CLD · NA/APAC backup"]
      VPN_NA["🔗 WireGuard → NA/APAC spokes · TOR/MTL/LAX/NYC/NJC · MIA/ATL/CHI/SYD/MEL/AKL"]

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
    end
    style OLD_BRK fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:BRK:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRBRK001 · RTR · 192.168.136.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCBRK001 · BMC 1 · 192.168.136.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEBRK001 · PVE 1 · 192.168.136.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIBRK001 · SWI 1 · 192.168.136.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIBRK003 · SWI 3 · 192.168.136.252"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIBRK002 · Second switch · 192.168.136.251"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASBRK001 · NAS · 192.168.136.19"]
    T_RDR["🔐 EXARDRBRK001 · RDR · 192.168.136.21"]
    T_WAP["📶 EXAWAPBRK001 · WAP 1 · 192.168.136.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSBRK001 · DCS 1 · 192.168.136.10"]
    T_SBC["🛡️ EXASBCBRK001 · SBC · 192.168.136.48"]
    T_FWL["🧱 EXAFWLBRK001 · LAN face · 192.168.136.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_DON["🍩 EXADONBRK001 · Donut vending · 192.168.136.60"]
    T_LAP["💻 EXALAPBRK001 · Tour laptop"]
    T_VND["🍫 EXAVNDBRK001 · Vending machine"]
    T_BMC --> T_DON --> T_LAP --> T_VND
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
    style T_DON fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_LAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_VND fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:BRK:END
```

---

## TOR — Toronto ⚠️ 🗼

**LAN:** `192.168.146.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSTOR001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (Canada) Inc. · **Landline:** +1 416 555 xxxx · **Mobile:** +1 647 555 xxxx

```mermaid
graph TD
    subgraph OLD_TOR ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACTOR001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVETOR001 · Proxmox node 1 · .5"]
      DC["🔴 🗝️ EXADCSTOR001 · DC · Services stopped · .10"]
      SBC["🛡️ EXASBCTOR001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYTOR001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → BRK"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_TOR fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:TOR:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRTOR001 · RTR · 192.168.146.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCTOR001 · BMC 1 · 192.168.146.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVETOR001 · PVE 1 · 192.168.146.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWITOR001 · SWI 1 · 192.168.146.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWITOR002 · SWI 2 · 192.168.146.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWITOR003 · SWI 3 · 192.168.146.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASTOR001 · NAS · 192.168.146.19"]
    T_RDR["🔐 EXARDRTOR001 · RDR · 192.168.146.21"]
    T_WAP["📶 EXAWAPTOR001 · WAP 1 · 192.168.146.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSTOR001 · DCS 1 · 192.168.146.10"]
    T_SBC["🛡️ EXASBCTOR001 · SBC · 192.168.146.48"]
    T_FWL["🧱 EXAFWLTOR001 · LAN face · 192.168.146.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_DCR["🗝️ EXADCRTOR028 · Undocumented legacy AD install found on site, no-one on r..."]
    T_BMC --> T_DCR
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
    style T_DCR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:TOR:END
```

---

## MTL — Montreal ⚜️

**LAN:** `192.168.154.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
**Entity:** Example Music (Canada) Inc. · **Landline:** +1 514 400 0xxx · **Mobile:** +1 514 900 2xxx

```mermaid
graph TD
    subgraph OLD_MTL ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACMTL001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEMTL001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSMTL001 · DC · .10"]
      SBC["🛡️ EXASBCMTL001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYMTL001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → BRK"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_MTL fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:MTL:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRMTL001 · RTR · 192.168.154.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCMTL001 · BMC 1 · 192.168.154.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEMTL001 · PVE 1 · 192.168.154.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIMTL001 · SWI 1 · 192.168.154.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIMTL002 · SWI 2 · 192.168.154.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIMTL003 · SWI 3 · 192.168.154.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASMTL001 · NAS · 192.168.154.19"]
    T_RDR["🔐 EXARDRMTL001 · RDR · 192.168.154.21"]
    T_WAP["📶 EXAWAPMTL001 · WAP 1 · 192.168.154.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSMTL001 · DCS 1 · 192.168.154.10"]
    T_SBC["🛡️ EXASBCMTL001 · SBC · 192.168.154.48"]
    T_FWL["🧱 EXAFWLMTL001 · LAN face · 192.168.154.253"]
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
%% GENERATED:TOPOLOGY:MTL:END
```
