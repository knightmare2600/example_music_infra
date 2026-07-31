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

### 🕰️ Old Network (legacy, hand restyled — prototype, not yet generated)

> **Corrected against Robert's real facts, 2026-07-31.** Standing corrections applied (no SBC;
> no `RRY`; no WireGuard on old infra). BMC confirmed Dell iDRAC9 (kept as documented — HP was a
> same-day slip, same pattern as LAX). Real ESX, and `EXADCSSYD001` genuinely ran as a VM on it —
> the "services stopped" state is real, kept. `EXACAMSYD002` (reception camera) removed — Robert:
> "it's bleed, we added CCTV as part of the new build" — confirmed by `devices.csv`'s own
> `Legacy=no` flag on that specific row; also resolves an octet collision with the coffee machine
> (`.83`), which keeps its real IP now the bleed is gone. Everything else (FWL, both switches,
> local infra server, MacBook, workstation, phone, iPad, WAP, coffee-area camera, signage, and
> printer) confirmed real via `devices.csv`.

> 🚨 **Migration priority — Tier 1.** DNS/Netlogon/KDC stopped on the ESX-hosted DC. Not a
> repair candidate — the fix is a new `EXADCSSYD001` build promoting and replicating against
> `EXADCSCLD001` (`ansible/playbooks/windows_dc/`), not restoring this node.

```mermaid
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    O_INET["🌐 Internet"]
    O_FWL["🧱 EXAFWLSYD001<br/>FortiGate 7.x<br/>192.168.29.1"]
    O_INET --> O_FWL
    O_SW1["🔀 EXASWISYD001<br/>Cisco 9300<br/>192.168.29.250"]
    O_SW2["🔀 EXASWISYD002<br/>Cisco 2960<br/>192.168.29.251"]
    O_FWL --> O_SW1
    O_FWL --> O_SW2

    O_RAC["🔧 EXARACSYD001<br/>Dell iDRAC9<br/>192.168.29.2"]
    O_ESX["💾 EXAESXSYD001<br/>Dell Server, VMware ESXi<br/>192.168.29.5"]
    O_DC["🔴🗝️ EXADCSSYD001<br/>DC · services stopped, hosted as an ESX VM<br/>192.168.29.10"]
    O_SRV["🗄️ EXASRVSYD001<br/>WS2022 Local Infra<br/>192.168.29.20"]
    O_SW1 --> O_ESX
    O_RAC -.->|"manages"| O_ESX
    O_ESX --> O_DC
    O_SW1 --> O_SRV

    O_MBP["💻 EXAMBPSYD001<br/>MacBook Pro<br/>192.168.29.40"]
    O_WKS["🖥️ EXAWKSSYD001<br/>Win11 Workstation<br/>192.168.29.41"]
    O_PHN["📞 EXAPHNSYD001<br/>Android Phone<br/>No IP Address"]
    O_TAB["📱 EXATABSYD001<br/>iPad, Setlists<br/>192.168.29.60"]
    O_WAP["📶 EXAWAPSYD001<br/>Ubiquiti UniFi<br/>No IP Address"]
    O_CAM1["🎥 EXACAMSYD001<br/>Hikvision, Coffee Cam<br/>192.168.29.82"]
    O_LCD["🖼️ EXALCDSYD001<br/>LG Signage Wallboard<br/>192.168.29.70"]
    O_PRN["🖨️ EXAPRNSYD001<br/>Brother Laser Printer<br/>192.168.29.80"]
    O_COF["🍵 EXACOFSYD001<br/>Smart Coffee Machine, RFC2324<br/>192.168.29.83"]
    O_SW2 --> O_MBP
    O_SW2 --> O_WKS
    O_SW2 --> O_PHN
    O_SW2 --> O_TAB
    O_SW2 --> O_WAP
    O_SW2 --> O_CAM1
    O_SW2 --> O_LCD
    O_SW2 --> O_PRN
    O_SW2 --> O_COF

    style O_INET fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_SW1 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_SW2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_RAC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_ESX fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_DC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_SRV fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_MBP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_WKS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_PHN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_TAB fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_CAM1 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_LCD fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_PRN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_COF fill:#000000,stroke:#FFFFFF,color:#FFFFFF
```

<details>
<summary>Original hand-maintained Old Network box (pre-restyle, kept for reference during prototype review)</summary>

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
```

</details>

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:SYD:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRSYD001<br/>RTR<br/>192.168.29.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCSYD001<br/>BMC 1<br/>192.168.29.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVESYD001<br/>PVE 1<br/>192.168.29.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWISYD003<br/>SWI 3<br/>192.168.29.252"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWISYD001<br/>Core Switch<br/>192.168.29.250"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWISYD002<br/>Access Switch<br/>192.168.29.251"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASSYD001<br/>NAS<br/>192.168.29.19"]
    T_RDR["🔐 EXARDRSYD001<br/>RDR<br/>192.168.29.21"]
    T_WAP["📶 EXAWAPSYD001<br/>WAP 1<br/>192.168.29.82"]
    T_SWI2 --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSSYD001<br/>DCS 1<br/>192.168.29.10"]
    T_SBC["🛡️ EXASBCSYD001<br/>SBC<br/>192.168.29.48"]
    T_FWL["🧱 EXAFWLSYD001<br/>LAN Face<br/>192.168.29.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_SRV["🗄️ EXASRVSYD001<br/>Local Infra Server<br/>192.168.29.20"]
    T_MBP["💻 EXAMBPSYD001<br/>MacBook Pro<br/>No IP Address"]
    T_WKS["🖥️ EXAWKSSYD001<br/>Workstation<br/>No IP Address"]
    T_PHN["📞 EXAPHNSYD001<br/>Phone<br/>No IP Address"]
    T_TAB["📱 EXATABSYD001<br/>IPad<br/>No IP Address"]
    T_LCD["🖼️ EXALCDSYD001<br/>LG Signage Wallboard<br/>No IP Address"]
    T_PRN["🖨️ EXAPRNSYD001<br/>Laser Printer<br/>No IP Address"]
    T_OTH_CAM["🎥 EXACAMSYD001-002<br/>2 x CCTV Cameras<br/>No IP Address"]
    T_COF["🍵 EXACOFSYD001<br/>Coffee Machine<br/>No IP Address"]
    T_SRV --> T_WKS --> T_TAB --> T_PRN --> T_COF
    T_MBP --> T_PHN --> T_LCD --> T_OTH_CAM
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
    style T_SRV fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_MBP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WKS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PHN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_TAB fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_LCD fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PRN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_OTH_CAM fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_COF fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:SYD:END
```

---

## MEL — Melbourne ⚠️ 🎨

**LAN:** `192.168.61.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSMEL001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (Australia) Pty Ltd · **Landline:** +61 3 9000 0xxx · **Mobile:** +61 400 901 2xxx

### 🕰️ Old Network (legacy, hand restyled — prototype, not yet generated)

> **Corrected against Robert's real facts, 2026-07-31.** Standing corrections applied (no SBC;
> no `RRY`; no WireGuard on old infra). Real, working ESX (HPE iLO5-managed), replaced by a new
> node in the new build. The DC's "services stopped" warning confirmed real. NAS
> (`EXANASMEL001`, Synology) confirmed real — replaced by a new TrueNAS node on new hardware, but
> the old Synology itself genuinely existed (missing from `devices.csv` for some other reason,
> not fabrication). WAPs confirmed never used — still in their boxes.

> 🚨 **Migration priority — Tier 1.** DNS/Netlogon/KDC stopped on the ESX-hosted DC. Not a
> repair candidate — the fix is a new `EXADCSMEL001` build promoting and replicating against
> `EXADCSCLD001` (`ansible/playbooks/windows_dc/`), not restoring this node.

```mermaid
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    O_INET["🌐 Internet"]
    O_FWL["🧱 EXAFWLMEL001<br/>FortiGate 7.x<br/>192.168.61.1"]
    O_INET --> O_FWL
    O_SW1["🔀 EXASWIMEL001<br/>Cisco 9300<br/>192.168.61.250"]
    O_SW2["🔀 EXASWIMEL002<br/>Cisco 2960<br/>192.168.61.251"]
    O_FWL --> O_SW1
    O_FWL --> O_SW2

    O_RAC["🔧 EXARACMEL001<br/>HPE iLO5<br/>192.168.61.2"]
    O_ESX["💾 EXAESXMEL001<br/>VMware ESXi<br/>192.168.61.5"]
    O_DC["🔴🗝️ EXADCSMEL001<br/>DC · services stopped<br/>192.168.61.10"]
    O_SRV["🗄️ EXASRVMEL001<br/>WS2022 File/Print<br/>192.168.61.20"]
    O_SW1 --> O_ESX
    O_RAC -.->|"manages"| O_ESX
    O_ESX --> O_DC
    O_ESX --> O_SRV

    O_MBP["💻 EXAMBPMEL001<br/>MacBook Pro<br/>192.168.61.40"]
    O_WKS["🖥️ EXAWKSMEL001<br/>Win11 Workstation<br/>192.168.61.41"]
    O_PHN["📞 EXAPHNMEL001<br/>iOS Phone<br/>No IP Address"]
    O_TAB["📱 EXATABMEL001<br/>iPad<br/>192.168.61.60"]
    O_WAP["📶 WAPs — none yet, still boxed on old infra"]
    O_CAM["🎥 CAMs — none yet, new build only"]
    O_LCD["🖼️ EXALCDMEL001<br/>Samsung Signage<br/>192.168.61.70"]
    O_PRN["🖨️ EXAPRNMEL001<br/>HP LaserJet<br/>192.168.61.80"]
    O_NAS["🗃️ EXANASMEL001<br/>Synology NAS, DSM 7.x<br/>192.168.61.81"]
    O_SW2 --> O_MBP
    O_SW2 --> O_WKS
    O_SW2 --> O_PHN
    O_SW2 --> O_TAB
    O_SW2 --> O_WAP
    O_SW2 --> O_CAM
    O_SW2 --> O_LCD
    O_SW2 --> O_PRN
    O_SW2 --> O_NAS

    style O_INET fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_SW1 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_SW2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_RAC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_ESX fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_DC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_SRV fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_MBP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_WKS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_PHN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_TAB fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_CAM fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_LCD fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_PRN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
```

<details>
<summary>Original hand-maintained Old Network box (pre-restyle, kept for reference during prototype review)</summary>

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
```

</details>

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:MEL:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRMEL001<br/>RTR<br/>192.168.61.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCMEL001<br/>BMC 1<br/>192.168.61.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEMEL001<br/>PVE 1<br/>192.168.61.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIMEL003<br/>SWI 3<br/>192.168.61.252"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIMEL001<br/>Core Switch<br/>192.168.61.250"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIMEL002<br/>Access Switch<br/>192.168.61.251"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASMEL001<br/>NAS<br/>192.168.61.19"]
    T_RDR["🔐 EXARDRMEL001<br/>RDR<br/>192.168.61.21"]
    T_WAP["📶 EXAWAPMEL001<br/>WAP 1<br/>192.168.61.82"]
    T_SWI2 --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSMEL001<br/>DCS 1<br/>192.168.61.10"]
    T_SBC["🛡️ EXASBCMEL001<br/>SBC<br/>192.168.61.48"]
    T_FWL["🧱 EXAFWLMEL001<br/>LAN Face<br/>192.168.61.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_SRV["🗄️ EXASRVMEL001<br/>Local File And Print Server<br/>192.168.61.20"]
    T_MBP["💻 EXAMBPMEL001<br/>MacBook Pro<br/>No IP Address"]
    T_WKS["🖥️ EXAWKSMEL001<br/>Workstation<br/>No IP Address"]
    T_PHN["📞 EXAPHNMEL001<br/>Phone<br/>No IP Address"]
    T_TAB["📱 EXATABMEL001<br/>IPad<br/>No IP Address"]
    T_LCD["🖼️ EXALCDMEL001<br/>Signage Display<br/>No IP Address"]
    T_PRN["🖨️ EXAPRNMEL001<br/>LaserJet Printer<br/>No IP Address"]
    T_SRV --> T_WKS --> T_TAB --> T_PRN
    T_MBP --> T_PHN --> T_LCD
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
    style T_SRV fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_MBP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WKS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PHN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_TAB fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_LCD fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PRN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:MEL:END
```
