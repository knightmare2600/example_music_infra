# Example Music Limited — New Zealand Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## AKL — Auckland ⚠️ ⛵

**LAN:** `192.168.93.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSAKL001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (New Zealand) Tapui · **Landline:** +64 9 300 0xxx · **Mobile:** +64 21 900 2xxx

```mermaid
graph TD
    subgraph OLD_AKL ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWL["🧱 EXAFWLAKL001 · FortiGate 7.x · .1"]
      SW1["🔀 EXASWIAKL001 · Cisco 9300 · .250"]
      SW2["🔀 EXASWIAKL002 · Cisco 2960 · .251"]
      RTR["📡 EXARTRAKL001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACAKL001 · HPE iLO5 · .2"]
      PVE["🗂️ EXAPVEAKL001 · Proxmox node 1 · .5"]
      DC["🔴 🗝️ EXADCSAKL001 · DC · Services stopped · .10"]
      SRV["🗄️ EXASRVAKL001 · WS2022 Local Server · .20"]
      SBC["🛡️ EXASBCAKL001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYAKL001 · Rudder Relay · .12"]
      WKS["🖥️ EXAWKSAKL001 · Win11 Workstation · .40"]
      MBP["💻 EXAMBPAKL001 · MacBook Pro · .41"]
      PHN["📞 EXAPHNAKL001 · Android Phone"]
      TAB["📱 EXATABAKL001 · iPad · .60"]
      WAP1["📶 EXAWAPAKL001 · Ubiquiti UniFi"]
      WAP2["📶 EXAWAPAKL002 · Ubiquiti UniFi"]
      CAM["🎥 EXACAMAKL001 · Axis Camera · .82"]
      LCD["🖼️ EXALCDAKL001 · Samsung Signage · .70"]
      PRN["🖨️ EXAPRNAKL001 · HP LaserJet · .80"]
      COF["🍵 EXACOFAKL001 · Smart Coffee Machine · .83"]
      VPN["🔗 WireGuard → BRK"]

      INET --> RTR --> FWL --> SW1 & SW2
      SW1 --> PVE --> DC & SRV & SBC
      RAC -.->|"manages"| PVE
      SW2 --> WKS & MBP & PHN & TAB & WAP1 & WAP2
      SW2 --> CAM & LCD & PRN & COF
      FWL <-->|"WireGuard tunnel"| VPN

      SW1 --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_AKL fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:AKL:START
    subgraph NEW_AKL ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRAKL001 · RTR · .1"]
      N_SBC["🛡️ EXASBCAKL001 · SBC · .48"]
      N_NAS["🗃️ EXANASAKL001 · NAS · .19"]
      N_RDR["🔐 EXARDRAKL001 · RDR · .21"]
      N_BMC["🔧 EXABMCAKL001 · BMC 1 · .2"]
      N_DCS["🗝️ EXADCSAKL001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLAKL001 · LAN face · .253"]
      N_FWL2["🧱 EXAFWLAKL002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEAKL001 · PVE 1 · .5"]
      N_WAP["📶 EXAWAPAKL001 · WAP 1 · .82"]
      N_SRV["🗄️ EXASRVAKL001 · Local server · .20"]
      N_SWI["🔀 EXASWIAKL001 · Core switch · .250"]
      N_SWI2["🔀 EXASWIAKL002 · Access switch · .251"]
      N_WKS["🖥️ EXAWKSAKL001 · Workstation"]
      N_MBP["💻 EXAMBPAKL001 · MacBook Pro"]
      N_PHN["📞 EXAPHNAKL001 · Phone"]
      N_TAB["📱 EXATABAKL001 · iPad"]
      N_LCD["🖼️ EXALCDAKL001 · Signage display"]
      N_PRN["🖨️ EXAPRNAKL001 · LaserJet printer"]
      N_CAM["🎥 EXACAMAKL001 · Camera"]
      N_COF["🍵 EXACOFAKL001 · Coffee machine"]
    end
    style NEW_AKL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:AKL:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

*Example Music Limited — Internal Infrastructure Documentation*   *Do not distribute outside the organisation*cloud
