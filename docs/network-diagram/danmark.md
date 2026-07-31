# Example Music Limited — Danmark Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## CPH — København 🧜‍♀️

**LAN:** `192.168.231.0/24` · **Domain:** `example.com` / `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_CPH ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      SW["🔀 EXASWICPH001 · TP-Link JetStream · .250"]
      RTR["📡 EXARTRCPH001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACCPH001 · Dell iDRAC9 · .2"]
      PVE["🗂️ EXAPVECPH001 · Proxmox node 1 · .5"]
      DC1["🗝️ EXADCSCPH001 · DC · example.com · .10"]
      DC2["🗝️ EXADCSCPH002 · DC · example.net · .11"]
      SBC["🛡️ EXASBCCPH001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYCPH001 · Rudder Relay · .12"]
      NTP["⏰ EXACLKCPH001 · Meinberg LANTIME M300 · NTP Clock · .18"]
      TV["📺 EXATVSCPH001 · Bella Kronik 42X · DR/TV2 · .17"]
      WAP["WAPs x3 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → ODE"]

      INET --> RTR --> SW
      SW --> PVE --> DC1 & DC2 & SBC
      RAC -.->|"manages"| PVE
      SW --> NTP & TV & WAP & CAM
      RTR <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_CPH fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:CPH:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRCPH001<br/>RTR<br/>192.168.231.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCCPH001<br/>BMC 1<br/>192.168.231.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVECPH001<br/>PVE 1<br/>192.168.231.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWICPH002<br/>SWI 2<br/>192.168.231.251"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWICPH003<br/>SWI 3<br/>192.168.231.252"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWICPH001<br/>Office Switch<br/>192.168.231.250"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASCPH001<br/>NAS<br/>192.168.231.19"]
    T_RDR["🔐 EXARDRCPH001<br/>RDR<br/>192.168.231.21"]
    T_WAP["📶 EXAWAPCPH001<br/>WAP 1<br/>192.168.231.82"]
    T_SWI3 --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSCPH001<br/>DCS 1<br/>192.168.231.10"]
    T_SBC["🛡️ EXASBCCPH001<br/>SBC<br/>192.168.231.48"]
    T_FWL["🧱 EXAFWLCPH001<br/>LAN Face<br/>192.168.231.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_CLK["⏰ EXACLKCPH001<br/>NTP Clock<br/>192.168.231.18"]
    T_TVS["📺 EXATVSCPH001<br/>Display<br/>192.168.231.17"]
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
    style T_CLK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_TVS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:CPH:END
```

---

## ODE — Odense *(EU Hub)* ⭐ 🎩

**LAN:** `192.168.126.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (EU hub) · **VPN parent:** CLD (EU backup)  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_ODE ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWL["🧱 EXAFWLODE001 · Cisco ASA 5506-X · .1"]

      subgraph BMC ["BMC Pool"]
          RAC1["🔧 EXARACODE001 · BMC node 1 · .2"]
          RAC2["🔧 EXARACODE002 · BMC node 2 · .3"]
          RAC3["🔧 EXARACODE003 · BMC node 3 · .4"]
      end

      subgraph PVE ["Proxmox Cluster (3-node)"]
          PVE1["🗂️ EXAPVEODE001 · Proxmox node 1 · .5"]
          PVE2["🗂️ EXAPVEODE002 · Proxmox node 2 · .6"]
          PVE3["🗂️ EXAPVEODE003 · Proxmox node 3 · .7"]
      end

      DC1["🗝️ EXADCSODE001 · DC PDC · RID/Infra Master · .10"]
      DC2["🗝️ EXADCSODE002 · DC secondary · .11"]
      SBC["🛡️ EXASBCODE001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYODE001 · Rudder Relay · .12"]
      MAC["🍎 EXAMACODE001 · iMac · macOS Tahoe · .150"]
      MBP["💻 EXAMBPODE002 · MacBook Pro · .151"]
      JKB["💿 EXAMUSODE001 · Pureline 128V Jukebox · .60"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN_CLD["🔗 WireGuard ← CLD · EU backup"]
      VPN_EU["🔗 WireGuard → EU spokes · CPH/KGE/FAX/KOR/AAR/FRE/BON/BER · DRS/DUS/MUN/GOT/OSL/AMS/MIL/VIE/BRT"]

      INET --> FWL
      FWL --> PVE1 & PVE2 & PVE3
      FWL --> DC1 & DC2 & SBC
      RAC1 -.->|"manages"| PVE1
      RAC2 -.->|"manages"| PVE2
      RAC3 -.->|"manages"| PVE3
      FWL --> MAC & MBP & JKB & WAP & CAM
      FWL <-->|"WireGuard tunnel"| VPN_CLD
      FWL -->|"WireGuard spokes"| VPN_EU

      PVE1 --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN_CLD
    end
    style OLD_ODE fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:ODE:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRODE001<br/>RTR<br/>192.168.126.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCODE001<br/>BMC 1<br/>192.168.126.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEODE001<br/>PVE 1<br/>192.168.126.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIODE001<br/>SWI 1<br/>192.168.126.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIODE003<br/>SWI 3<br/>192.168.126.252"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIODE002<br/>Second Switch<br/>192.168.126.251"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASODE001<br/>NAS<br/>192.168.126.19"]
    T_RDR["🔐 EXARDRODE001<br/>RDR<br/>192.168.126.21"]
    T_MUS["💿 EXAMUSODE001<br/>Jukebox<br/>192.168.126.60"]
    T_WAP["📶 EXAWAPODE001<br/>WAP 1<br/>192.168.126.82"]
    T_SWI --> T_NAS --> T_RDR --> T_MUS --> T_WAP
    T_DCS["🗝️ EXADCSODE001<br/>DCS 1<br/>192.168.126.10"]
    T_SBC["🛡️ EXASBCODE001<br/>SBC<br/>192.168.126.48"]
    T_FWL["🧱 EXAFWLODE001<br/>LAN Face<br/>192.168.126.253"]
    T_FWL2["🧱 EXAFWLODE002<br/>FWL 2<br/>192.168.126.254 — planned"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL --> T_FWL2
    T_MAC["🍎 EXAMACODE001<br/>IMac<br/>No IP Address"]
    T_MBP["💻 EXAMBPODE002<br/>MacBook Pro<br/>No IP Address"]
    style T_VRK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_MUS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_MAC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_MBP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:ODE:END
```

---

## KGE — Køge ⚠️ 🏘️

**LAN:** `192.168.65.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
> ⚠️ DC out of sync 27 days · WS2016 EOL · disk space low — rebuild required  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_KGE ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACKGE001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEKGE001 · Proxmox node 1 · .5"]
      DC["⚠️ 🗝️ EXADCSKGE001 · DC · WS2016 EOL · OOS 27d · .10"]
      SBC["🛡️ EXASBCKGE001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYKGE001 · Rudder Relay · .12"]
      WAP["📶 EXAWAPKGE001 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      PRN["🖨️ EXAPRNKGE001 · HP LaserJet MFP M528 · .16"]
      VPN["🔗 WireGuard → ODE"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM & PRN
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_KGE fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:KGE:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRKGE001<br/>RTR<br/>192.168.65.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCKGE001<br/>BMC 1<br/>192.168.65.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEKGE001<br/>PVE 1<br/>192.168.65.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIKGE001<br/>SWI 1<br/>192.168.65.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIKGE002<br/>SWI 2<br/>192.168.65.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIKGE003<br/>SWI 3<br/>192.168.65.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASKGE001<br/>NAS<br/>192.168.65.19"]
    T_RDR["🔐 EXARDRKGE001<br/>RDR<br/>192.168.65.21"]
    T_WAP["📶 EXAWAPKGE001<br/>WAP 1<br/>192.168.65.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSKGE001<br/>DCS 1<br/>192.168.65.10"]
    T_SBC["🛡️ EXASBCKGE001<br/>SBC<br/>192.168.65.48"]
    T_FWL["🧱 EXAFWLKGE001<br/>LAN Face<br/>192.168.65.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_PRN["🖨️ EXAPRNKGE001<br/>Printer<br/>No IP Address"]
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
    style T_PRN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:KGE:END
```

---

## FAX — Faxe 🥤

**LAN:** `192.168.246.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_FAX ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RTR["📡 EXARTRFAX001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACFAX001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEFAX001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSFAX001 · DC · .10"]
      SBC["🛡️ EXASBCFAX001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYFAX001 · Rudder Relay · .12"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → ODE"]

      INET --> RTR --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      RTR --> WAP & CAM
      RTR <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_FAX fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:FAX:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRFAX001<br/>RTR<br/>192.168.246.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCFAX001<br/>BMC 1<br/>192.168.246.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEFAX001<br/>PVE 1<br/>192.168.246.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIFAX001<br/>SWI 1<br/>192.168.246.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIFAX002<br/>SWI 2<br/>192.168.246.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIFAX003<br/>SWI 3<br/>192.168.246.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASFAX001<br/>NAS<br/>192.168.246.19"]
    T_RDR["🔐 EXARDRFAX001<br/>RDR<br/>192.168.246.21"]
    T_WAP["📶 EXAWAPFAX001<br/>WAP 1<br/>192.168.246.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSFAX001<br/>DCS 1<br/>192.168.246.10"]
    T_SBC["🛡️ EXASBCFAX001<br/>SBC<br/>192.168.246.48"]
    T_FWL["🧱 EXAFWLFAX001<br/>LAN Face<br/>192.168.246.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
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
%% GENERATED:TOPOLOGY:FAX:END
```

---

## KOR — Korsør 🚂

**LAN:** `192.168.238.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_KOR ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACKOR001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEKOR001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSKOR001 · DC · .10"]
      SBC["🛡️ EXASBCKOR001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYKOR001 · Rudder Relay · .12"]
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
    style OLD_KOR fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:KOR:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRKOR001<br/>RTR<br/>192.168.238.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCKOR001<br/>BMC 1<br/>192.168.238.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEKOR001<br/>PVE 1<br/>192.168.238.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIKOR001<br/>SWI 1<br/>192.168.238.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIKOR002<br/>SWI 2<br/>192.168.238.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIKOR003<br/>SWI 3<br/>192.168.238.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASKOR001<br/>NAS<br/>192.168.238.19"]
    T_RDR["🔐 EXARDRKOR001<br/>RDR<br/>192.168.238.21"]
    T_WAP["📶 EXAWAPKOR001<br/>WAP 1<br/>192.168.238.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSKOR001<br/>DCS 1<br/>192.168.238.10"]
    T_SBC["🛡️ EXASBCKOR001<br/>SBC<br/>192.168.238.48"]
    T_FWL["🧱 EXAFWLKOR001<br/>LAN Face<br/>192.168.238.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
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
%% GENERATED:TOPOLOGY:KOR:END
```

---

## AAR — Aarhus 🎓

**LAN:** `192.168.86.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_AAR ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACAAR001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEAAR001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSAAR001 · DC · .10"]
      SBC["🛡️ EXASBCAAR001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYAAR001 · Rudder Relay · .12"]
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
    style OLD_AAR fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:AAR:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRAAR001<br/>RTR<br/>192.168.86.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCAAR001<br/>BMC 1<br/>192.168.86.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEAAR001<br/>PVE 1<br/>192.168.86.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIAAR001<br/>SWI 1<br/>192.168.86.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIAAR002<br/>SWI 2<br/>192.168.86.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIAAR003<br/>SWI 3<br/>192.168.86.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASAAR001<br/>NAS<br/>192.168.86.19"]
    T_RDR["🔐 EXARDRAAR001<br/>RDR<br/>192.168.86.21"]
    T_WAP["📶 EXAWAPAAR001<br/>WAP 1<br/>192.168.86.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSAAR001<br/>DCS 1<br/>192.168.86.10"]
    T_SBC["🛡️ EXASBCAAR001<br/>SBC<br/>192.168.86.48"]
    T_FWL["🧱 EXAFWLAAR001<br/>LAN Face<br/>192.168.86.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
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
%% GENERATED:TOPOLOGY:AAR:END
```

---

## FRE — Fredericia 🏯

**LAN:** `192.168.75.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 75 xx xx xx · **Mobile:** +45 2x xx xx xx

```mermaid
graph TD
    subgraph OLD_FRE ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACFRE001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEFRE001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSFRE001 · DC · .10"]
      SBC["🛡️ EXASBCFRE001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYFRE001 · Rudder Relay · .12"]
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
    style OLD_FRE fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:FRE:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRFRE001<br/>RTR<br/>192.168.75.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCFRE001<br/>BMC 1<br/>192.168.75.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEFRE001<br/>PVE 1<br/>192.168.75.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIFRE001<br/>SWI 1<br/>192.168.75.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIFRE002<br/>SWI 2<br/>192.168.75.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIFRE003<br/>SWI 3<br/>192.168.75.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASFRE001<br/>NAS<br/>192.168.75.19"]
    T_RDR["🔐 EXARDRFRE001<br/>RDR<br/>192.168.75.21"]
    T_WAP["📶 EXAWAPFRE001<br/>WAP 1<br/>192.168.75.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSFRE001<br/>DCS 1<br/>192.168.75.10"]
    T_SBC["🛡️ EXASBCFRE001<br/>SBC<br/>192.168.75.48"]
    T_FWL["🧱 EXAFWLFRE001<br/>LAN Face<br/>192.168.75.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
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
%% GENERATED:TOPOLOGY:FRE:END
```

---

## FRD — Fredericia Havn *(New Build)* ⚓

**LAN:** `172.16.124.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 (`EXAPVEFRD001`, real hardware) · **VPN parent:** CLD (direct, non-standard networking)  
**Entity:** Example Music Limited · **Landline:** N/A · **Mobile:** N/A

> **New-build site.** No legacy infrastructure ever existed here — see the "New Build Location" box below in place of "Old Network." Fredericia Havn is a legal fiction run off a MacBook (`python3 -m http.server 8000` as a PXE mirror) — but it has a real "site kit" alongside that: a small Intel NUC running Proxmox VE (`EXAPVEFRD001`) and a 48-port switch (`EXASWIFRD001`), confirmed by Robert 2026-07-30. Also physically here, though hostnamed under CLD: a secondary 3CX PBX (`EXAPBXCLD002`) — see `benarbejde/generate_inventory.py`'s `NON_STANDARD_SITES`/`SubnetSite` handling.
>
> **Possible future addition:** a QNAP NAS may be added to the site kit, to support either Proxmox Backup Server or a VMware→Proxmox migration path (Robert, 2026-07-30). Proxmox VE already ships an official, built-in migration tool for this — the Import Wizard (since 8.2, connects directly to the ESXi API and imports a VM with on-the-fly disk conversion via Datacenter → Storage → Add → ESXi, then right-click → Import; see https://pve.proxmox.com/wiki/Migrate_to_Proxmox_VE). Nothing bespoke is needed here — not yet built, no timeline.

```mermaid
graph TD
    subgraph OLD_FRD ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site. · No prior/legacy network existed before commissioning."]
    end
    style OLD_FRD fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

> Robert, 2026-07-30: FRD is "literally just online, it's a legal function but we treat it like a
> fallback VRK site." `172.16.124.253` (`sites.csv`'s `FW` field) doesn't have a real device yet —
> unlike VRK's own `.254` (confirmed OVH's, not ours), this one is genuinely planned, mirroring
> VRK's own `EXAFWLVRK001`. `EXAPBXCLD002` is confirmed to belong here — hostnamed under CLD,
> physically at FRD. Robert's own words on the naming: "note the naming convention, this might
> cause some shenanigans, if it does you have my permission to call it `EXAPBXFRD001`" — not
> renamed here, no actual conflict has come up; this is standing permission for later, not
> something exercised pre-emptively.

```mermaid
%% GENERATED:TOPOLOGY:FRD:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_FRD["☁️ FRD — Fredericia Havn network fabric, 172.16.124.0/24"]
    T_TMP["📦<br/>Provisioning Server (PXE, Port 8000)<br/>172.16.124.1"]
    T_PVE["🗂️ EXAPVEFRD001<br/>Small Intel NUC Running Proxmox VE<br/>172.16.124.5"]
    T_SWI["🔀 EXASWIFRD001<br/>48-port Switch<br/>172.16.124.250"]
    T_PBX["🔌 EXAPBXCLD002<br/>Secondary 3CX PBX (hostnamed Under CLD)<br/>172.16.124.48"]
    T_FWL["🧱 EXAFWLFRD001<br/>FWL 1<br/>172.16.124.253 — planned"]
    T_FRD --> T_TMP --> T_PVE --> T_SWI --> T_PBX --> T_FWL
    style T_FRD fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_TMP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PBX fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:FRD:END
```

---

## NYB — Nyborg *(New Build)* 📜

**LAN:** `192.168.90.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 (reserved — see notes below) · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 80 400 0xxx · **Mobile:** +45 200 900 2xxx

> **New-build site.** No legacy infrastructure ever existed here — see the "New Build Location" box below in place of "Old Network." Standard-slot addresses are allocated in `benarbejde/address_policy.csv`/`sites.csv` the same as any other site (this is what makes the .ini/DNS generation already treat them as real, per the generated-file-freshness harness check) but no `devices.csv` exception rows exist yet — nothing beyond the standard template has been confirmed built on site.

```mermaid
graph TD
    subgraph OLD_NYB ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site. · No prior/legacy network existed before commissioning."]
    end
    style OLD_NYB fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:NYB:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRNYB001<br/>RTR<br/>192.168.90.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCNYB001<br/>BMC 1<br/>192.168.90.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVENYB001<br/>PVE 1<br/>192.168.90.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWINYB001<br/>SWI 1<br/>192.168.90.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWINYB002<br/>SWI 2<br/>192.168.90.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWINYB003<br/>SWI 3<br/>192.168.90.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASNYB001<br/>NAS<br/>192.168.90.19"]
    T_RDR["🔐 EXARDRNYB001<br/>RDR<br/>192.168.90.21"]
    T_WAP["📶 EXAWAPNYB001<br/>WAP 1<br/>192.168.90.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSNYB001<br/>DCS 1<br/>192.168.90.10"]
    T_SBC["🛡️ EXASBCNYB001<br/>SBC<br/>192.168.90.48"]
    T_FWL["🧱 EXAFWLNYB001<br/>LAN Face<br/>192.168.90.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
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
%% GENERATED:TOPOLOGY:NYB:END
```
