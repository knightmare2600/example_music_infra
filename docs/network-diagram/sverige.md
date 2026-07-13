# Example Music Limited — Sverige Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## GOT — Gothenburg ♠️

**LAN:** `192.168.46.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Sverige) AB · **Landline:** N/A · **Mobile:** N/A

```mermaid
graph TD
    subgraph OLD_GOT ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACGOT001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEGOT001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSGOT001 · DC · .10"]
      SBC["🛡️ EXASBCGOT001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYGOT001 · Rudder Relay · .12"]
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
    style OLD_GOT fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:GOT:START
    subgraph NEW_GOT ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRGOT001 · RTR · .1"]
      N_PRV["📦 EXAPRVGOT001 · PRV · .15"]
      N_SBC["🛡️ EXASBCGOT001 · SBC · .48"]
      N_DCS["🗝️ EXADCSGOT001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLGOT001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLGOT002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEGOT001 · PVE 1 · .5"]
    end
    style NEW_GOT fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:GOT:END
```
