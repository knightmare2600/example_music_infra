# Example Music Limited — Lebanon Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## BRT — Beirut

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
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_BRT fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:BRT:START
    subgraph NEW_BRT ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRBRT001 · RTR · .1"]
      N_PRV["📦 EXAPRVBRT001 · PRV · .15"]
      N_SBC["🛡️ EXASBCBRT001 · SBC · .48"]
      N_DCS["🗝️ EXADCSBRT001 · DCS 1 · .10"]
      N_FWL["🔥 EXAFWLBRT001 · FWL 1 · .253"]
      N_FWL2["🔥 EXAFWLBRT002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEBRT001 · PVE 1 · .5"]
    end
    style NEW_BRT fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:BRT:END
```
