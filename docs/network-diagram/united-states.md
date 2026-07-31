# Example Music Limited — United States Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## LAX — Los Angeles ⚠️ 🎬

**LAN:** `192.168.213.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSLAX001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (US) LLC. · **Landline:** +1 213 555 xxxx · **Mobile:** +1 213 555 xxx

```mermaid
graph TD
    subgraph OLD_LAX ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWL["🧱 EXAFWLLAX001 · Palo Alto PAN-OS 10.x · .1"]
      SW1["🔀 EXASWILAX001 · Cisco 9300 · .250"]
      SW2["🔀 EXASWILAX002 · Cisco 2960 · .251"]
      RTR["📡 EXARTRLAX001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACLAX001 · Dell iDRAC9 · .2"]
      PVE["🗂️ EXAPVELAX001 · Proxmox node 1 · .5"]
      DC["🔴 🗝️ EXADCSLAX001 · DC · Services stopped · .10"]
      SRV["🗄️ EXASRVLAX001 · Rocky Linux · Local services/DB · .20"]
      SBC["🛡️ EXASBCLAX001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYLAX001 · Rudder Relay · .12"]
      MBP["💻 EXAMBPLAX001 · MacBook Pro · .41"]
      TAB["📱 EXATABLAX001 · iPad · Setlists · .61"]
      PHN["📞 EXAPHNLAX001 · Android Phone"]
      WAP["WAPs x3 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      MOO["💿 EXAMUSLAX001 · Moog One Synthesizer · .70"]
      LIN["💿 EXAMUSLAX002 · LinnDrum LM-2 · .71"]
      FCL["💿 EXAMUSLAX003 · Fairlight CMI IIx · .72"]
      AST["⌨️ EXATTYLAX001 · Atari ST · MIDI · .73"]
      PAY["☎️ EXAPAYLAX001 · Lobby Payphone · .74"]
      LCD["🖼️ EXALCDLAX001 · NEC PlasmaSync Display · .75"]
      VPN["🔗 WireGuard → BRK"]

      INET --> RTR --> FWL --> SW1 & SW2
      SW1 --> PVE --> DC & SRV & SBC
      RAC -.->|"manages"| PVE
      SW2 --> MBP & TAB & PHN & WAP & CAM
      SW2 --> MOO & LIN & FCL & AST & PAY & LCD
      FWL <-->|"WireGuard tunnel"| VPN

      SW1 --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_LAX fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:LAX:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRLAX001<br/>RTR<br/>192.168.213.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCLAX001<br/>BMC 1<br/>192.168.213.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVELAX001<br/>PVE 1<br/>192.168.213.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWILAX003<br/>SWI 3<br/>192.168.213.252"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWILAX001<br/>Core Switch<br/>192.168.213.250"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWILAX002<br/>Access Switch<br/>192.168.213.251"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASLAX001<br/>NAS<br/>192.168.213.19"]
    T_RDR["🔐 EXARDRLAX001<br/>RDR<br/>192.168.213.21"]
    T_MUS["💿 EXAMUSLAX001<br/>Synth<br/>192.168.213.70"]
    T_MUS2["💿 EXAMUSLAX002<br/>Drum Machine<br/>192.168.213.71"]
    T_MUS3["💿 EXAMUSLAX003<br/>Fairlight CMI<br/>192.168.213.72"]
    T_WAP["📶 EXAWAPLAX001<br/>WAP 1<br/>192.168.213.82"]
    T_SWI2 --> T_NAS --> T_RDR --> T_MUS --> T_MUS2 --> T_MUS3 --> T_WAP
    T_DCS["🗝️ EXADCSLAX001<br/>DCS 1<br/>192.168.213.10"]
    T_SBC["🛡️ EXASBCLAX001<br/>SBC<br/>192.168.213.48"]
    T_FWL["🧱 EXAFWLLAX001<br/>LAN Face<br/>192.168.213.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_SRV["🗄️ EXASRVLAX001<br/>Local Services DB<br/>192.168.213.20"]
    T_AST["🕹️ EXAASTLAX001<br/>Atari ST<br/>192.168.213.73"]
    T_PAY["☎️ EXAPAYLAX001<br/>Payphone<br/>192.168.213.74"]
    T_LCD["🖼️ EXALCDLAX001<br/>Status Wallboard<br/>192.168.213.75"]
    T_MBP["💻 EXAMBPLAX001<br/>MacBook Pro<br/>No IP Address"]
    T_TAB["📱 EXATABLAX001<br/>IPad<br/>No IP Address"]
    T_PHN["📞 EXAPHNLAX001<br/>Phone<br/>No IP Address"]
    T_SRV --> T_PAY --> T_MBP --> T_PHN
    T_AST --> T_LCD --> T_TAB
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
    style T_MUS2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_MUS3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SRV fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_AST fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PAY fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_LCD fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_MBP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_TAB fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PHN fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:LAX:END
```

---

## NYC — New York ⚠️ 🗽

**LAN:** `192.168.212.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSNYC001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (US) LLC. · **Landline:** +1 212 500 0xxx · **Mobile:** +1 917 900 2xxx

```mermaid
graph TD
    subgraph OLD_NYC ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACNYC001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVENYC001 · Proxmox node 1 · .5"]
      DC["🔴 🗝️ EXADCSNYC001 · DC · Services stopped · .10"]
      SBC["🛡️ EXASBCNYC001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYNYC001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → BRK"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_NYC fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:NYC:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRNYC001<br/>RTR<br/>192.168.212.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCNYC001<br/>BMC 1<br/>192.168.212.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVENYC001<br/>PVE 1<br/>192.168.212.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWINYC001<br/>SWI 1<br/>192.168.212.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWINYC002<br/>SWI 2<br/>192.168.212.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWINYC003<br/>SWI 3<br/>192.168.212.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASNYC001<br/>NAS<br/>192.168.212.19"]
    T_RDR["🔐 EXARDRNYC001<br/>RDR<br/>192.168.212.21"]
    T_WAP["📶 EXAWAPNYC001<br/>WAP 1<br/>192.168.212.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSNYC001<br/>DCS 1<br/>192.168.212.10"]
    T_SBC["🛡️ EXASBCNYC001<br/>SBC<br/>192.168.212.48"]
    T_FWL["🧱 EXAFWLNYC001<br/>LAN Face<br/>192.168.212.253"]
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
%% GENERATED:TOPOLOGY:NYC:END
```

---

## NJC — New Jersey ⚠️ 🚕

**LAN:** `192.168.201.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSNJC001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (US) LLC. · **Landline:** +1 201 400 0xxx · **Mobile:** +1 908 900 2xxx

```mermaid
graph TD
    subgraph OLD_NJC ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACNJC001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVENJC001 · Proxmox node 1 · .5"]
      DC["🔴 🗝️ EXADCSNJC001 · DC · Services stopped · .10"]
      SBC["🛡️ EXASBCNJC001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYNJC001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → BRK"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_NJC fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:NJC:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRNJC001<br/>RTR<br/>192.168.201.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCNJC001<br/>BMC 1<br/>192.168.201.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVENJC001<br/>PVE 1<br/>192.168.201.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWINJC001<br/>SWI 1<br/>192.168.201.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWINJC002<br/>SWI 2<br/>192.168.201.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWINJC003<br/>SWI 3<br/>192.168.201.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASNJC001<br/>NAS<br/>192.168.201.19"]
    T_RDR["🔐 EXARDRNJC001<br/>RDR<br/>192.168.201.21"]
    T_WAP["📶 EXAWAPNJC001<br/>WAP 1<br/>192.168.201.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSNJC001<br/>DCS 1<br/>192.168.201.10"]
    T_SBC["🛡️ EXASBCNJC001<br/>SBC<br/>192.168.201.48"]
    T_FWL["🧱 EXAFWLNJC001<br/>LAN Face<br/>192.168.201.253"]
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
%% GENERATED:TOPOLOGY:NJC:END
```

---

## MIA — Miami 🌴

**LAN:** `192.168.135.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
**Entity:** Example Music (US) LLC. · **Landline:** +1 305 555 xxxx · **Mobile:** +1 786 555 xxxx

```mermaid
graph TD
    subgraph OLD_MIA ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACMIA001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEMIA001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSMIA001 · DC · .10"]
      SBC["🛡️ EXASBCMIA001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYMIA001 · Rudder Relay · .12"]
      LAP["💻 EXALAPMIA001 · macOS Sonoma Laptop · .21"]
      COF["🍵 EXACOFMIA001 · Cuban Covfefe Machine · VxWorks · .60"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → BRK"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> LAP & COF & WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_MIA fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:MIA:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRMIA001<br/>RTR<br/>192.168.135.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCMIA001<br/>BMC 1<br/>192.168.135.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEMIA001<br/>PVE 1<br/>192.168.135.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIMIA001<br/>SWI 1<br/>192.168.135.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIMIA002<br/>SWI 2<br/>192.168.135.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIMIA003<br/>SWI 3<br/>192.168.135.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASMIA001<br/>NAS<br/>192.168.135.19"]
    T_RDR["🔐 EXARDRMIA001<br/>RDR<br/>192.168.135.21"]
    T_WAP["📶 EXAWAPMIA001<br/>WAP 1<br/>192.168.135.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSMIA001<br/>DCS 1<br/>192.168.135.10"]
    T_SBC["🛡️ EXASBCMIA001<br/>SBC<br/>192.168.135.48"]
    T_FWL["🧱 EXAFWLMIA001<br/>LAN Face<br/>192.168.135.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_COF["🍵 EXACOFMIA001<br/>Coffee Machine<br/>192.168.135.60"]
    T_LAP["💻 EXALAPMIA001<br/>MacBook<br/>No IP Address"]
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
    style T_COF fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_LAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:MIA:END
```

---

## ATL — Atlanta ⚠️ 🍑

**LAN:** `192.168.33.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSATL001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (US) LLC. · **Landline:** +1 334 300 0xxx · **Mobile:** +1 770 900 2xxx

```mermaid
graph TD
    subgraph OLD_ATL ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACATL001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEATL001 · Proxmox node 1 · .5"]
      DC["🔴 🗝️ EXADCSATL001 · DC · Services stopped · .10"]
      SBC["🛡️ EXASBCATL001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYATL001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → BRK"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_ATL fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:ATL:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRATL001<br/>RTR<br/>192.168.33.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCATL001<br/>BMC 1<br/>192.168.33.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEATL001<br/>PVE 1<br/>192.168.33.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIATL001<br/>SWI 1<br/>192.168.33.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIATL002<br/>SWI 2<br/>192.168.33.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIATL003<br/>SWI 3<br/>192.168.33.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASATL001<br/>NAS<br/>192.168.33.19"]
    T_RDR["🔐 EXARDRATL001<br/>RDR<br/>192.168.33.21"]
    T_WAP["📶 EXAWAPATL001<br/>WAP 1<br/>192.168.33.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSATL001<br/>DCS 1<br/>192.168.33.10"]
    T_SBC["🛡️ EXASBCATL001<br/>SBC<br/>192.168.33.48"]
    T_FWL["🧱 EXAFWLATL001<br/>LAN Face<br/>192.168.33.253"]
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
%% GENERATED:TOPOLOGY:ATL:END
```

---

## CHI — Chicago ⚠️ 🏠

**LAN:** `192.168.214.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSCHI001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (US) LLC. · **Landline:** +1 312 555 xxxx · **Mobile:** +1 773 900 xxxx

```mermaid
graph TD
    subgraph OLD_CHI ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACCHI001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVECHI001 · Proxmox node 1 · .5"]
      DC["🔴 🗝️ EXADCSCHI001 · DC · Services stopped · .10"]
      SBC["🛡️ EXASBCCHI001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYCHI001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → BRK"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_CHI fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:CHI:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRCHI001<br/>RTR<br/>192.168.214.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCCHI001<br/>BMC 1<br/>192.168.214.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVECHI001<br/>PVE 1<br/>192.168.214.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWICHI001<br/>SWI 1<br/>192.168.214.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWICHI002<br/>SWI 2<br/>192.168.214.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWICHI003<br/>SWI 3<br/>192.168.214.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASCHI001<br/>NAS<br/>192.168.214.19"]
    T_RDR["🔐 EXARDRCHI001<br/>RDR<br/>192.168.214.21"]
    T_WAP["📶 EXAWAPCHI001<br/>WAP 1<br/>192.168.214.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSCHI001<br/>DCS 1<br/>192.168.214.10"]
    T_SBC["🛡️ EXASBCCHI001<br/>SBC<br/>192.168.214.48"]
    T_FWL["🧱 EXAFWLCHI001<br/>LAN Face<br/>192.168.214.253"]
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
%% GENERATED:TOPOLOGY:CHI:END
```

---

## SEA — Seattle *(New Build)* ☕

**LAN:** `192.168.206.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 (reserved — see notes below) · **VPN parent:** BRK  
**Entity:** Example Music (US) LLC. · **Landline:** +1 206 555 xxxx · **Mobile:** +1 425 555 xxxx

> **New-build site.** No legacy infrastructure ever existed here — see the "New Build Location" box below in place of "Old Network." Standard-slot addresses are allocated in `benarbejde/address_policy.csv`/`sites.csv` the same as any other site, but no `devices.csv` exception rows exist yet.

```mermaid
graph TD
    subgraph OLD_SEA ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site. · No prior/legacy network existed before commissioning."]
    end
    style OLD_SEA fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:SEA:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRSEA001<br/>RTR<br/>192.168.206.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCSEA001<br/>BMC 1<br/>192.168.206.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVESEA001<br/>PVE 1<br/>192.168.206.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWISEA001<br/>SWI 1<br/>192.168.206.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWISEA002<br/>SWI 2<br/>192.168.206.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWISEA003<br/>SWI 3<br/>192.168.206.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASSEA001<br/>NAS<br/>192.168.206.19"]
    T_RDR["🔐 EXARDRSEA001<br/>RDR<br/>192.168.206.21"]
    T_WAP["📶 EXAWAPSEA001<br/>WAP 1<br/>192.168.206.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSSEA001<br/>DCS 1<br/>192.168.206.10"]
    T_SBC["🛡️ EXASBCSEA001<br/>SBC<br/>192.168.206.48"]
    T_FWL["🧱 EXAFWLSEA001<br/>LAN Face<br/>192.168.206.253"]
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
%% GENERATED:TOPOLOGY:SEA:END
```

---

## SFO — San Francisco *(New Build)* 🌁

**LAN:** `192.168.145.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 (reserved — see notes below) · **VPN parent:** BRK  
**Entity:** Example Music (US) LLC. · **Landline:** +1 415 555 xxxx · **Mobile:** +1 628 555 xxxx

> **New-build site.** No legacy infrastructure ever existed here — see the "New Build Location" box below in place of "Old Network." Standard-slot addresses are allocated in `benarbejde/address_policy.csv`/`sites.csv` the same as any other site, but no `devices.csv` exception rows exist yet.

```mermaid
graph TD
    subgraph OLD_SFO ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site. · No prior/legacy network existed before commissioning."]
    end
    style OLD_SFO fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:SFO:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRSFO001<br/>RTR<br/>192.168.145.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCSFO001<br/>BMC 1<br/>192.168.145.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVESFO001<br/>PVE 1<br/>192.168.145.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWISFO001<br/>SWI 1<br/>192.168.145.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWISFO002<br/>SWI 2<br/>192.168.145.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWISFO003<br/>SWI 3<br/>192.168.145.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASSFO001<br/>NAS<br/>192.168.145.19"]
    T_RDR["🔐 EXARDRSFO001<br/>RDR<br/>192.168.145.21"]
    T_WAP["📶 EXAWAPSFO001<br/>WAP 1<br/>192.168.145.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSSFO001<br/>DCS 1<br/>192.168.145.10"]
    T_SBC["🛡️ EXASBCSFO001<br/>SBC<br/>192.168.145.48"]
    T_FWL["🧱 EXAFWLSFO001<br/>LAN Face<br/>192.168.145.253"]
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
%% GENERATED:TOPOLOGY:SFO:END
```
