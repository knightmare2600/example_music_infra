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
    %% GENERATED:NEW-NETWORK:MIL:START
    subgraph NEW_MIL ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRMIL001 · RTR · .1"]
      N_SBC["🛡️ EXASBCMIL001 · SBC · .48"]
      N_DCS["🗝️ EXADCSMIL001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLMIL001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLMIL002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEMIL001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIMIL001 · SWI 1 · .250"]
    end
    style NEW_MIL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:MIL:END
```
