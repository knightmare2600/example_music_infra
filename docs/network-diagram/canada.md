# Example Music Limited — Canada Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## BRK — Brockville *(NA/APAC Hub)* ⭐ 🍁

**LAN:** `192.168.136.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (NA/APAC hub) · **VPN parent:** CLD (NA/APAC backup)  
> ⚠️ `EXADCSBRK001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (Canada) Inc. · **Landline:** +1 613 555 6xxx · **Mobile:** +1 613 555 6xxx

```mermaid
graph TD
    subgraph OLD_BRK ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RTR["📡 EXARTRBRK001 · Cisco ISR 4331 · .254"]

      subgraph BMC ["BMC Pool"]
          RAC1["🔧 EXARACBRK001 · BMC node 1 · .2"]
          RAC2["🔧 EXARACBRK002 · BMC node 2 · .3"]
          RAC3["🔧 EXARACBRK003 · BMC node 3 · .4"]
      end

      subgraph PVE ["Proxmox Cluster (3-node)"]
          PVE1["🗂️ EXAPVEBRK001 · Proxmox node 1 · .5"]
          PVE2["🗂️ EXAPVEBRK002 · Proxmox node 2 · .6"]
          PVE3["🗂️ EXAPVEBRK003 · Proxmox node 3 · .7"]
      end

      DC["🔴 🗝️ EXADCSBRK001 · DC · Services stopped · .10"]
      SBC["🛡️ EXASBCBRK001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYBRK001 · Rudder Relay · .12"]
      LAP["💻 EXALAPBRK001 · Win11 Tour Laptop · .21"]
      WAP["📶 EXAWAPBRK001 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VND1["🍩 EXADONBRK001 · Tim Hortons Donut Vending · .60"]
      VND2["🍫 EXAVNDBRK001 · Maple Syrup Vending · .61"]
      VPN_CLD["🔗 WireGuard ← CLD · NA/APAC backup"]
      VPN_NA["🔗 WireGuard → NA/APAC spokes · TOR/MTL/LAX/NYC/NJC · MIA/ATL/CHI/SYD/MEL/AKL"]

      INET --> RTR
      RTR --> PVE1 & PVE2 & PVE3
      RTR --> DC & SBC
      RAC1 -.->|"manages"| PVE1
      RAC2 -.->|"manages"| PVE2
      RAC3 -.->|"manages"| PVE3
      RTR --> LAP & WAP & CAM & VND1 & VND2
      RTR <-->|"WireGuard tunnel"| VPN_CLD
      RTR -->|"WireGuard spokes"| VPN_NA

      PVE1 --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN_CLD
    end
    style OLD_BRK fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:BRK:START
    subgraph NEW_BRK ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRBRK001 · RTR · .1"]
      N_PRV["📦 EXAPRVBRK001 · PRV · .15"]
      N_SBC["🛡️ EXASBCBRK001 · SBC · .48"]
      N_DCS["🗝️ EXADCSBRK001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLBRK001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLBRK002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEBRK001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIBRK001 · SWI 1 · .250"]
      N_DON["🍩 EXADONBRK001 · Donut vending · .60"]
      N_LAP["💻 EXALAPBRK001 · Tour laptop"]
      N_VND["🍫 EXAVNDBRK001 · Vending machine"]
    end
    style NEW_BRK fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:BRK:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

## TOR — Toronto ⚠️ 🗼

**LAN:** `192.168.146.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSTOR001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (Canada) Inc. · **Landline:** +1 416 555 xxxx · **Mobile:** +1 647 555 xxxx

```mermaid
graph TD
    subgraph OLD_TOR ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACTOR001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVETOR001 · Proxmox node 1 · .5"]
      DC["🔴 🗝️ EXADCSTOR001 · DC · Services stopped · .10"]
      SBC["🛡️ EXASBCTOR001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYTOR001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → BRK"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_TOR fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:TOR:START
    subgraph NEW_TOR ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRTOR001 · RTR · .1"]
      N_PRV["📦 EXAPRVTOR001 · PRV · .15"]
      N_SBC["🛡️ EXASBCTOR001 · SBC · .48"]
      N_DCS["🗝️ EXADCSTOR001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLTOR001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLTOR002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVETOR001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWITOR001 · SWI 1 · .250"]
      N_DCR["🗝️ EXADCRTOR028 · Undocumented legacy AD install found on site, no-one on r..."]
    end
    style NEW_TOR fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:TOR:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

## MTL — Montreal ⚜️

**LAN:** `192.168.154.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
**Entity:** Example Music (Canada) Inc. · **Landline:** +1 514 400 0xxx · **Mobile:** +1 514 900 2xxx

```mermaid
graph TD
    subgraph OLD_MTL ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACMTL001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEMTL001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSMTL001 · DC · .10"]
      SBC["🛡️ EXASBCMTL001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYMTL001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → BRK"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_MTL fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:MTL:START
    subgraph NEW_MTL ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRMTL001 · RTR · .1"]
      N_PRV["📦 EXAPRVMTL001 · PRV · .15"]
      N_SBC["🛡️ EXASBCMTL001 · SBC · .48"]
      N_DCS["🗝️ EXADCSMTL001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLMTL001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLMTL002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEMTL001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIMTL001 · SWI 1 · .250"]
    end
    style NEW_MTL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:MTL:END
```
