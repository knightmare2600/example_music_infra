# Example Music Limited — Österreich Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## VIE — Vienna 🎻

**LAN:** `192.168.78.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Osterreich) GmbH · **Landline:** +43 800 078 0xx · **Mobile:** +43 664 665 xxx

```mermaid
graph TD
    subgraph OLD_VIE ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACVIE001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEVIE001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSVIE001 · DC · .10"]
      SBC["🛡️ EXASBCVIE001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYVIE001 · Rudder Relay · .12"]
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
    style OLD_VIE fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (draft, hand-drawn — not yet generated)

```mermaid
%% GENERATED:TOPOLOGY:VIE:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRVIE001 · RTR · 192.168.78.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCVIE001 · BMC 1 · 192.168.78.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEVIE001 · PVE 1 · 192.168.78.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIVIE001 · SWI 1 · 192.168.78.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIVIE002 · SWI 2 · 192.168.78.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIVIE003 · SWI 3 · 192.168.78.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASVIE001 · NAS · 192.168.78.19"]
    T_RDR["🔐 EXARDRVIE001 · RDR · 192.168.78.21"]
    T_WAP["📶 EXAWAPVIE001 · WAP 1 · 192.168.78.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSVIE001 · DCS 1 · 192.168.78.10"]
    T_SBC["🛡️ EXASBCVIE001 · SBC · 192.168.78.48"]
    T_FWL["🧱 EXAFWLVIE001 · LAN face · 192.168.78.253"]
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
%% GENERATED:TOPOLOGY:VIE:END
```
