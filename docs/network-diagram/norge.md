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
    %% GENERATED:NEW-NETWORK:OSL:START
    subgraph NEW_OSL ["🆕 New Network (current)"]
      N_RTR["📡 EXARTROSL001 · RTR · .1"]
      N_SBC["🛡️ EXASBCOSL001 · SBC · .48"]
      N_NAS["🗃️ EXANASOSL001 · NAS · .19"]
      N_RDR["🔐 EXARDROSL001 · RDR · .21"]
      N_BMC["🔧 EXABMCOSL001 · BMC 1 · .2"]
      N_DCS["🗝️ EXADCSOSL001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLOSL001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLOSL002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEOSL001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIOSL001 · SWI 1 · .250"]
      N_WAP["📶 EXAWAPOSL001 · WAP 1 · .82"]
    end
    style NEW_OSL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:OSL:END
```
