# Example Music Limited — Lebanon Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## BRT — Beirut 🌲

**LAN:** `192.168.169.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Lebanon) SAL · **Landline:** +961 1 555 xxxx · **Mobile:** +961 3 555 xxxx

```mermaid
graph TD
    subgraph OLD_BRT ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACBRT001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEBRT001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSBRT001 · DC · .10"]
      SBC["🛡️ EXASBCBRT001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYBRT001 · Rudder Relay · .12"]
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
    style OLD_BRT fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:BRT:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRBRT001<br/>RTR<br/>192.168.169.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCBRT001<br/>BMC 1<br/>192.168.169.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEBRT001<br/>PVE 1<br/>192.168.169.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIBRT001<br/>SWI 1<br/>192.168.169.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIBRT002<br/>SWI 2<br/>192.168.169.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIBRT003<br/>SWI 3<br/>192.168.169.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASBRT001<br/>NAS<br/>192.168.169.19"]
    T_RDR["🔐 EXARDRBRT001<br/>RDR<br/>192.168.169.21"]
    T_WAP["📶 EXAWAPBRT001<br/>WAP 1<br/>192.168.169.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSBRT001<br/>DCS 1<br/>192.168.169.10"]
    T_SBC["🛡️ EXASBCBRT001<br/>SBC<br/>192.168.169.48"]
    T_FWL["🧱 EXAFWLBRT001<br/>LAN Face<br/>192.168.169.253"]
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
%% GENERATED:TOPOLOGY:BRT:END
```
