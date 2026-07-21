# Example Music Limited — Australia Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## SYD — Sydney ⚠️ 🎭

**LAN:** `192.168.29.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSSYD001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (Australia) Pty Ltd · **Landline:** +61 2 9000 0xxx · **Mobile:** +61 400 900 2xxx

```mermaid
graph TD
    subgraph OLD_SYD ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWL["🧱 EXAFWLSYD001 · FortiGate 7.x · .1"]
      SW1["🔀 EXASWISYD001 · Cisco 9300 · .250"]
      SW2["🔀 EXASWISYD002 · Cisco 2960 · .251"]
      RAC["🔧 EXARACSYD001 · Dell iDRAC9 · .2"]
      PVE["🗂️ EXAPVESYD001 · Proxmox node 1 · .5"]
      DC["🔴 🗝️ EXADCSSYD001 · DC · Services stopped · .10"]
      SRV["🗄️ EXASRVSYD001 · WS2022 Local Infra · .20"]
      SBC["🛡️ EXASBCSYD001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYSYD001 · Rudder Relay · .12"]
      MBP["💻 EXAMBPSYD001 · MacBook Pro · .40"]
      WKS["🖥️ EXAWKSSYD001 · Win11 Workstation · .41"]
      PHN["📞 EXAPHNSYD001 · Android Phone"]
      TAB["📱 EXATABSYD001 · iPad · Setlists · .60"]
      WAP["📶 EXAWAPSYD001 · Ubiquiti UniFi"]
      CAM1["🎥 EXACAMSYD001 · Hikvision · Coffee cam · .82"]
      CAM2["🎥 EXACAMSYD002 · Hikvision · Reception · .83"]
      LCD["🖼️ EXALCDSYD001 · LG Signage Wallboard · .70"]
      PRN["🖨️ EXAPRNSYD001 · Brother Laser Printer · .80"]
      COF["🍵 EXACOFSYD001 · Smart Coffee Machine · RFC2324 · .83"]
      VPN["🔗 WireGuard → BRK"]

      INET --> FWL --> SW1 & SW2
      SW1 --> PVE --> DC & SRV & SBC
      RAC -.->|"manages"| PVE
      SW2 --> MBP & WKS & PHN & TAB & WAP
      SW2 --> CAM1 & CAM2 & LCD & PRN & COF
      FWL <-->|"WireGuard tunnel"| VPN

      SW1 --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_SYD fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:SYD:START
    subgraph NEW_SYD ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRSYD001 · RTR · .1"]
      N_SBC["🛡️ EXASBCSYD001 · SBC · .48"]
      N_DCS["🗝️ EXADCSSYD001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLSYD001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLSYD002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVESYD001 · PVE 1 · .5"]
      N_SRV["🗄️ EXASRVSYD001 · Local infra server · .20"]
      N_SWI["🔀 EXASWISYD001 · Core switch · .250"]
      N_SWI2["🔀 EXASWISYD002 · Access switch · .251"]
      N_MBP["💻 EXAMBPSYD001 · MacBook Pro"]
      N_WKS["🖥️ EXAWKSSYD001 · Workstation"]
      N_PHN["📞 EXAPHNSYD001 · Phone"]
      N_TAB["📱 EXATABSYD001 · iPad"]
      N_LCD["🖼️ EXALCDSYD001 · LG Signage wallboard"]
      N_PRN["🖨️ EXAPRNSYD001 · Laser printer"]
      N_CAM["🎥 EXACAMSYD001 · Camera"]
      N_CAM2["🎥 EXACAMSYD002 · Camera reception"]
      N_COF["🍵 EXACOFSYD001 · Coffee machine"]
    end
    style NEW_SYD fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:SYD:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

## MEL — Melbourne ⚠️ 🎨

**LAN:** `192.168.61.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSMEL001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (Australia) Pty Ltd · **Landline:** +61 3 9000 0xxx · **Mobile:** +61 400 901 2xxx

```mermaid
graph TD
    subgraph OLD_MEL ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWL["🧱 EXAFWLMEL001 · FortiGate 7.x · .1"]
      SW1["🔀 EXASWIMEL001 · Cisco 9300 · .250"]
      SW2["🔀 EXASWIMEL002 · Cisco 2960 · .251"]
      RAC["🔧 EXARACMEL001 · HPE iLO5 · .2"]
      PVE["🗂️ EXAPVEMEL001 · Proxmox node 1 · .5"]
      DC["🔴 🗝️ EXADCSMEL001 · DC · Services stopped · .10"]
      SRV["🗄️ EXASRVMEL001 · WS2022 File/Print · .20"]
      SBC["🛡️ EXASBCMEL001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYMEL001 · Rudder Relay · .12"]
      MBP["💻 EXAMBPMEL001 · MacBook Pro · .40"]
      WKS["🖥️ EXAWKSMEL001 · Win11 Workstation · .41"]
      PHN["📞 EXAPHNMEL001 · iOS Phone"]
      TAB["📱 EXATABMEL001 · iPad · .60"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      LCD["🖼️ EXALCDMEL001 · Samsung Signage · .70"]
      PRN["🖨️ EXAPRNMEL001 · HP LaserJet · .80"]
      NAS["🗃️ EXANASMEL001 · Synology NAS DSM 7.x · .81"]
      VPN["🔗 WireGuard → BRK"]

      INET --> FWL --> SW1 & SW2
      SW1 --> PVE --> DC & SRV & SBC
      RAC -.->|"manages"| PVE
      SW2 --> MBP & WKS & PHN & TAB & WAP & CAM
      SW2 --> LCD & PRN & NAS
      FWL <-->|"WireGuard tunnel"| VPN

      SW1 --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_MEL fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:MEL:START
    subgraph NEW_MEL ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRMEL001 · RTR · .1"]
      N_SBC["🛡️ EXASBCMEL001 · SBC · .48"]
      N_DCS["🗝️ EXADCSMEL001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLMEL001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLMEL002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEMEL001 · PVE 1 · .5"]
      N_SRV["🗄️ EXASRVMEL001 · Local file and print server · .20"]
      N_SWI["🔀 EXASWIMEL001 · Core switch · .250"]
      N_SWI2["🔀 EXASWIMEL002 · Access switch · .251"]
      N_MBP["💻 EXAMBPMEL001 · MacBook Pro"]
      N_WKS["🖥️ EXAWKSMEL001 · Workstation"]
      N_PHN["📞 EXAPHNMEL001 · Phone"]
      N_TAB["📱 EXATABMEL001 · iPad"]
      N_LCD["🖼️ EXALCDMEL001 · Signage display"]
      N_PRN["🖨️ EXAPRNMEL001 · LaserJet printer"]
    end
    style NEW_MEL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:MEL:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```
