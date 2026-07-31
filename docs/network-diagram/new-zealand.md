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

### 🕰️ Old Network (legacy, hand restyled — prototype, not yet generated)

> **Corrected against Robert's real facts, 2026-07-31.** Standing corrections applied (no SBC;
> no `RRY`; no WireGuard on old infra). Real, working ESX on HP hardware, HPE iLO5-managed. The
> DC's "services stopped" warning confirmed real — "built and left in a bad state." Both WAPs
> confirmed genuinely real and in active use — not new-build bleed, and not still-boxed like
> several other sites — subsumed straight into the new build's UniFi controller.

> 🚨 **Migration priority — Tier 1.** DC "built and left in a bad state" — services stopped.
> Not a repair candidate — the fix is a new `EXADCSAKL001` build promoting and replicating
> against `EXADCSCLD001` (`ansible/playbooks/windows_dc/`), not restoring this node.

```mermaid
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    O_INET["🌐 Internet"]
    O_RTR["📡 EXARTRAKL001<br/>Cisco ISR 4331<br/>192.168.93.254"]
    O_INET --> O_RTR
    O_FWL["🧱 EXAFWLAKL001<br/>FortiGate 7.x<br/>192.168.93.1"]
    O_RTR --> O_FWL
    O_SW1["🔀 EXASWIAKL001<br/>Cisco 9300<br/>192.168.93.250"]
    O_SW2["🔀 EXASWIAKL002<br/>Cisco 2960<br/>192.168.93.251"]
    O_FWL --> O_SW1
    O_FWL --> O_SW2

    O_RAC["🔧 EXARACAKL001<br/>HPE iLO5<br/>192.168.93.2"]
    O_ESX["💾 EXAESXAKL001<br/>HP Server, VMware ESXi<br/>192.168.93.5"]
    O_DC["🔴🗝️ EXADCSAKL001<br/>DC · services stopped, left in a bad state<br/>192.168.93.10"]
    O_SRV["🗄️ EXASRVAKL001<br/>WS2022 Local Server<br/>192.168.93.20"]
    O_SW1 --> O_ESX
    O_RAC -.->|"manages"| O_ESX
    O_ESX --> O_DC
    O_ESX --> O_SRV

    O_WKS["🖥️ EXAWKSAKL001<br/>Win11 Workstation<br/>192.168.93.40"]
    O_MBP["💻 EXAMBPAKL001<br/>MacBook Pro<br/>192.168.93.41"]
    O_PHN["📞 EXAPHNAKL001<br/>Android Phone<br/>No IP Address"]
    O_TAB["📱 EXATABAKL001<br/>iPad<br/>192.168.93.60"]
    O_WAP1["📶 EXAWAPAKL001<br/>Ubiquiti UniFi<br/>No IP Address"]
    O_WAP2["📶 EXAWAPAKL002<br/>Ubiquiti UniFi<br/>No IP Address"]
    O_CAM["🎥 EXACAMAKL001<br/>Axis Camera<br/>192.168.93.82"]
    O_LCD["🖼️ EXALCDAKL001<br/>Samsung Signage<br/>192.168.93.70"]
    O_PRN["🖨️ EXAPRNAKL001<br/>HP LaserJet<br/>192.168.93.80"]
    O_COF["🍵 EXACOFAKL001<br/>Smart Coffee Machine<br/>192.168.93.83"]
    O_SW2 --> O_WKS
    O_SW2 --> O_MBP
    O_SW2 --> O_PHN
    O_SW2 --> O_TAB
    O_SW2 --> O_WAP1
    O_SW2 --> O_WAP2
    O_SW2 --> O_CAM
    O_SW2 --> O_LCD
    O_SW2 --> O_PRN
    O_SW2 --> O_COF

    style O_INET fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_SW1 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_SW2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_RAC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_ESX fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_DC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_SRV fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_WKS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_MBP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_PHN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_TAB fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_WAP1 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_WAP2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_CAM fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_LCD fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_PRN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_COF fill:#000000,stroke:#FFFFFF,color:#FFFFFF
```

<details>
<summary>Original hand-maintained Old Network box (pre-restyle, kept for reference during prototype review)</summary>

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
```

</details>

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:AKL:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRAKL001<br/>RTR<br/>192.168.93.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCAKL001<br/>BMC 1<br/>192.168.93.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEAKL001<br/>PVE 1<br/>192.168.93.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIAKL003<br/>SWI 3<br/>192.168.93.252"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIAKL001<br/>Core Switch<br/>192.168.93.250"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIAKL002<br/>Access Switch<br/>192.168.93.251"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASAKL001<br/>NAS<br/>192.168.93.19"]
    T_RDR["🔐 EXARDRAKL001<br/>RDR<br/>192.168.93.21"]
    T_WAP["📶 EXAWAPAKL001<br/>Wireless Access Point<br/>192.168.93.84"]
    T_WAP2["📶 EXAWAPAKL002<br/>Wireless Access Point<br/>192.168.93.85"]
    T_WAP3["📶 EXAWAPAKL003<br/>Wireless Access Point<br/>192.168.93.86"]
    T_SWI2 --> T_NAS --> T_RDR --> T_WAP --> T_WAP2 --> T_WAP3
    T_DCS["🗝️ EXADCSAKL001<br/>DCS 1<br/>192.168.93.10"]
    T_SBC["🛡️ EXASBCAKL001<br/>SBC<br/>192.168.93.48"]
    T_FWL["🧱 EXAFWLAKL001<br/>LAN Face<br/>192.168.93.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_SRV["🗄️ EXASRVAKL001<br/>Local Server<br/>192.168.93.20"]
    T_WKS["🖥️ EXAWKSAKL001<br/>Workstation<br/>No IP Address"]
    T_MBP["💻 EXAMBPAKL001<br/>MacBook Pro<br/>No IP Address"]
    T_PHN["📞 EXAPHNAKL001<br/>Phone<br/>No IP Address"]
    T_TAB["📱 EXATABAKL001<br/>IPad<br/>No IP Address"]
    T_LCD["🖼️ EXALCDAKL001<br/>Signage Display<br/>No IP Address"]
    T_PRN["🖨️ EXAPRNAKL001<br/>LaserJet Printer<br/>No IP Address"]
    T_CAM["🎥 EXACAMAKL001<br/>Camera<br/>192.168.93.82"]
    T_COF["🍵 EXACOFAKL001<br/>Coffee Machine<br/>No IP Address"]
    T_SRV --> T_MBP --> T_TAB --> T_PRN --> T_COF
    T_WKS --> T_PHN --> T_LCD --> T_CAM
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
    style T_WAP2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SRV fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WKS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_MBP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PHN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_TAB fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_LCD fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PRN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_CAM fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_COF fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:AKL:END
```

---

*Example Music Limited — Internal Infrastructure Documentation*   *Do not distribute outside the organisation*cloud
