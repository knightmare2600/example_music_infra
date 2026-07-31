# Example Music Limited — Norge Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## OSL — Oslo 🏔️

**LAN:** `192.168.47.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Norge) ASA · **Landline:** N/A · **Mobile:** N/A

```mermaid
graph TD
    subgraph OLD_OSL ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACOSL001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEOSL001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSOSL001 · DC · .10"]
      SBC["🛡️ EXASBCOSL001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYOSL001 · Rudder Relay · .12"]
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
    style OLD_OSL fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (draft, hand-drawn — not yet generated)

```mermaid
%% GENERATED:TOPOLOGY:OSL:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTROSL001 · RTR · 192.168.47.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCOSL001 · BMC 1 · 192.168.47.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEOSL001 · PVE 1 · 192.168.47.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIOSL001 · SWI 1 · 192.168.47.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIOSL002 · SWI 2 · 192.168.47.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIOSL003 · SWI 3 · 192.168.47.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASOSL001 · NAS · 192.168.47.19"]
    T_RDR["🔐 EXARDROSL001 · RDR · 192.168.47.21"]
    T_WAP["📶 EXAWAPOSL001 · WAP 1 · 192.168.47.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSOSL001 · DCS 1 · 192.168.47.10"]
    T_SBC["🛡️ EXASBCOSL001 · SBC · 192.168.47.48"]
    T_FWL["🧱 EXAFWLOSL001 · LAN face · 192.168.47.253"]
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
%% GENERATED:TOPOLOGY:OSL:END
```
