# Example Music Limited — Nederland Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## AMS — Amsterdam 🚲

**LAN:** `192.168.31.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Nederland) B.V. · **Landline:** N/A · **Mobile:** N/A

```mermaid
graph TD
    subgraph OLD_AMS ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACAMS001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEAMS001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSAMS001 · DC · .10"]
      SBC["🛡️ EXASBCAMS001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYAMS001 · Rudder Relay · .12"]
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
    style OLD_AMS fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (draft, hand-drawn — not yet generated)

```mermaid
%% GENERATED:TOPOLOGY:AMS:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRAMS001 · RTR · 192.168.31.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCAMS001 · BMC 1 · 192.168.31.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEAMS001 · PVE 1 · 192.168.31.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIAMS001 · SWI 1 · 192.168.31.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIAMS002 · SWI 2 · 192.168.31.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIAMS003 · SWI 3 · 192.168.31.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASAMS001 · NAS · 192.168.31.19"]
    T_RDR["🔐 EXARDRAMS001 · RDR · 192.168.31.21"]
    T_WAP["📶 EXAWAPAMS001 · WAP 1 · 192.168.31.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSAMS001 · DCS 1 · 192.168.31.10"]
    T_SBC["🛡️ EXASBCAMS001 · SBC · 192.168.31.48"]
    T_FWL["🧱 EXAFWLAMS001 · LAN face · 192.168.31.253"]
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
%% GENERATED:TOPOLOGY:AMS:END
```
