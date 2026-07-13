# Example Music Limited — Deutschland Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## BON — Bonn

**LAN:** `192.168.228.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Note:** Hosts Schema Master + Domain Naming Master  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 228 555 xxx · **Mobile:** +49 211 xxx xxxx

```mermaid
graph TD
    subgraph OLD_BON ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      SW["🔀 EXASWIBON001 · Cisco 2960X · .250"]
      RTR["📡 EXARTRBON001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACBON001 · Dell iDRAC9 · .2"]
      PVE["🗂️ EXAPVEBON001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSBON001 · DC · Schema Master · DN Master · .10"]
      SBC["🛡️ EXASBCBON001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYBON001 · Rudder Relay · .12"]
      WKS["🖥️ EXAWKSBON001 · Finance WKS · .151"]
      LAP1["💻 EXALAPBON001 · ThinkPad ⚠️ disabled · .150"]
      LAP2["💻 EXALAPBON002 · Finance Laptop · .153"]
      VCU["🎧 EXAVCUBON001 · Poly Studio X70 · Boardroom · .2"]
      CAM["🎥 EXACAMBON001 · Axis P3245-LVE CCTV · .17"]
      TV["📺 EXATVSBON001 · Samsung 65in · .18"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      VPN["🔗 WireGuard → ODE"]

      INET --> RTR --> SW
      SW --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      SW --> WKS & LAP1 & LAP2 & VCU & CAM & TV & WAP
      RTR <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_BON fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:BON:START
    subgraph NEW_BON ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRBON001 · RTR · .1"]
      N_PRV["📦 EXAPRVBON001 · PRV · .15"]
      N_SBC["🛡️ EXASBCBON001 · SBC · .48"]
      N_DCS["🗝️ EXADCSBON001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLBON001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLBON002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEBON001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIBON001 · Office switch · .250"]
      N_LAP["💻 EXALAPBON001 · ThinkPad DISABLED"]
      N_WKS["🖥️ EXAWKSBON001 · Finance workstation"]
      N_LAP2["💻 EXALAPBON002 · Finance laptop"]
      N_VCU["🎧 EXAVCUBON001 · Boardroom video conferencing"]
      N_CAM["🎥 EXACAMBON001 · CCTV camera"]
      N_TVS["📺 EXATVSBON001 · Display"]
    end
    style NEW_BON fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:BON:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class LAP1 warn
```

---

## BER — West Berlin

**LAN:** `192.168.113.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 311 555 xxx · **Mobile:** +49 211 xxx xxxx

```mermaid
graph TD
    subgraph OLD_BER ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RTR["📡 EXARTRBER001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACBER001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEBER001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSBER001 · DC · PDC Emulator · RID/Infra Master WS2019 · .10"]
      SBC["🛡️ EXASBCBER001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYBER001 · Rudder Relay · .12"]
      SRV["🗄️ EXASRVBER001 · WS2019 Legacy App Server · .21"]
      NIX["🐧 EXANIXBER001 · Debian 12 Server · .22"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → ODE"]

      INET --> RTR --> PVE --> DC & SBC & SRV & NIX
      RAC -.->|"manages"| PVE
      RTR --> WAP & CAM
      RTR <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_BER fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:BER:START
    subgraph NEW_BER ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRBER001 · RTR · .1"]
      N_PRV["📦 EXAPRVBER001 · PRV · .15"]
      N_SBC["🛡️ EXASBCBER001 · SBC · .48"]
      N_DCS["🗝️ EXADCSBER001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLBER001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLBER002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEBER001 · PVE 1 · .5"]
    end
    style NEW_BER fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:BER:END
```

---

## MUN — Munich

**LAN:** `192.168.189.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 893 555 33xx · **Mobile:** +49 893 555 99xx

```mermaid
graph TD
    subgraph OLD_MUN ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      SW["🔀 EXASWIMUN001 · Cisco 9200 · .250"]
      RAC["🔧 EXARACMUN001 · HPE iLO5 · .2"]
      PVE["🗂️ EXAPVEMUN001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSMUN001 · DC · .10"]
      SBC["🛡️ EXASBCMUN001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYMUN001 · Rudder Relay · .12"]
      WKS["🖥️ EXAWKSMUN001 · Hot Desk WKS · .150"]
      LAP1["💻 EXALAPMUN001 · Pool Laptop · .151"]
      LAP2["⚠️ 💻 EXALAPMUN002 · Pool Laptop · LAPS expired 61d · .152"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → ODE"]

      INET --> SW
      SW --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      SW --> WKS & LAP1 & LAP2 & WAP & CAM
      SW <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_MUN fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:MUN:START
    subgraph NEW_MUN ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRMUN001 · RTR · .1"]
      N_PRV["📦 EXAPRVMUN001 · PRV · .15"]
      N_SBC["🛡️ EXASBCMUN001 · SBC · .48"]
      N_DCS["🗝️ EXADCSMUN001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLMUN001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLMUN002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEMUN001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIMUN001 · Access switch · .250"]
      N_WKS["🖥️ EXAWKSMUN001 · Hot desk workstation"]
      N_LAP["💻 EXALAPMUN001 · Pool laptop"]
      N_LAP2["💻 EXALAPMUN002 · LAPS expired"]
    end
    style NEW_MUN fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:MUN:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class LAP2 warn
```

---

## DRS — Dresden

**LAN:** `192.168.153.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 351 555 xxx · **Mobile:** +49 172 xxx xxxx

```mermaid
graph TD
    subgraph OLD_DRS ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACDRS001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEDRS001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSDRS001 · DC · .10"]
      SBC["🛡️ EXASBCDRS001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYDRS001 · Rudder Relay · .12"]
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
    style OLD_DRS fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:DRS:START
    subgraph NEW_DRS ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRDRS001 · RTR · .1"]
      N_PRV["📦 EXAPRVDRS001 · PRV · .15"]
      N_SBC["🛡️ EXASBCDRS001 · SBC · .48"]
      N_DCS["🗝️ EXADCSDRS001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLDRS001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLDRS002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEDRS001 · PVE 1 · .5"]
    end
    style NEW_DRS fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:DRS:END
```

---

## DUS — Düsseldorf

**LAN:** `192.168.211.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 211 555 xxx · **Mobile:** +49 172 xxx xxxx

```mermaid
graph TD
    subgraph OLD_DUS ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACDUS001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEDUS001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSDUS001 · DC · .10"]
      SBC["🛡️ EXASBCDUS001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYDUS001 · Rudder Relay · .12"]
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
    style OLD_DUS fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:DUS:START
    subgraph NEW_DUS ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRDUS001 · RTR · .1"]
      N_PRV["📦 EXAPRVDUS001 · PRV · .15"]
      N_SBC["🛡️ EXASBCDUS001 · SBC · .48"]
      N_DCS["🗝️ EXADCSDUS001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLDUS001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLDUS002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEDUS001 · PVE 1 · .5"]
    end
    style NEW_DUS fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:DUS:END
```
