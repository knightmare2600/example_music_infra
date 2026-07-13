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
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_VIE fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:VIE:START
    subgraph NEW_VIE ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRVIE001 · RTR · .1"]
      N_PRV["📦 EXAPRVVIE001 · PRV · .15"]
      N_SBC["🛡️ EXASBCVIE001 · SBC · .48"]
      N_DCS["🗝️ EXADCSVIE001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLVIE001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLVIE002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEVIE001 · PVE 1 · .5"]
    end
    style NEW_VIE fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:VIE:END
```
