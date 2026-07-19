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
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_AMS fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:AMS:START
    subgraph NEW_AMS ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRAMS001 · RTR · .1"]
      N_SBC["🛡️ EXASBCAMS001 · SBC · .48"]
      N_DCS["🗝️ EXADCSAMS001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLAMS001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLAMS002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEAMS001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIAMS001 · SWI 1 · .250"]
    end
    style NEW_AMS fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:AMS:END
```
