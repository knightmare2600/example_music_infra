# Example Music Limited — Italia Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## MIL — Milan 👔

**LAN:** `192.168.39.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Italia) S.p.a. · **Landline:** N/A · **Mobile:** N/A

```mermaid
graph TD
    subgraph OLD_MIL ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACMIL001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEMIL001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSMIL001 · DC · .10"]
      SBC["🛡️ EXASBCMIL001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYMIL001 · Rudder Relay · .12"]
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
    style OLD_MIL fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:MIL:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRMIL001 · RTR · 192.168.39.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCMIL001 · BMC 1 · 192.168.39.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEMIL001 · PVE 1 · 192.168.39.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIMIL001 · SWI 1 · 192.168.39.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIMIL002 · SWI 2 · 192.168.39.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIMIL003 · SWI 3 · 192.168.39.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASMIL001 · NAS · 192.168.39.19"]
    T_RDR["🔐 EXARDRMIL001 · RDR · 192.168.39.21"]
    T_WAP["📶 EXAWAPMIL001 · WAP 1 · 192.168.39.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSMIL001 · DCS 1 · 192.168.39.10"]
    T_SBC["🛡️ EXASBCMIL001 · SBC · 192.168.39.48"]
    T_FWL["🧱 EXAFWLMIL001 · LAN face · 192.168.39.253"]
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
%% GENERATED:TOPOLOGY:MIL:END
```
