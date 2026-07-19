# Example Music Limited — England Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## LND — London 🥑

**LAN:** `192.168.20.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 207 496 0xxx · **Mobile:** +44 770 090 0xxx

```mermaid
graph TD
    subgraph OLD_LND ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWL["🧱 EXAFWLLND001 · Cisco ASA 5516-X · .1"]
      SW["🔀 EXASWILND001 · Cisco 9300 · .250"]
      RTR["📡 EXARTRLND001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACLND001 · Dell iDRAC9 · .2"]
      PVE["🗂️ EXAPVELND001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCRLND001 · DC · RID/Infra Master · .10"]
      SBC["🛡️ EXASBCLND001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYLND001 · Rudder Relay · .12"]
      WKS["🖥️ EXAWKSLND001 · Hot Desk WKS · .150"]
      PRN1["🖨️ EXAPRNLND001 · Xerox WorkCentre · .16"]
      PRN2["🖨️ EXAPRNLND002 · ProCAT Steno Writer · Court Device"]
      RAD["📻 EXARADLND001 · BBC Office Radio Mk II · .80"]
      MIC["🎤 EXAMICLND001 · Shure SM7 Microphone · Dante Audio · .81"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> RTR --> FWL --> SW
      SW --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      SW --> WKS & PRN1 & PRN2 & RAD & MIC & WAP & CAM
      FWL <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_LND fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:LND:START
    subgraph NEW_LND ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRLND001 · RTR · .1"]
      N_SBC["🛡️ EXASBCLND001 · SBC · .48"]
      N_DCS["🗝️ EXADCSLND001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLLND001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLLND002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVELND001 · PVE 1 · .5"]
      N_RAD["📻 EXARADLND001 · BBC Office Radio Mk II · .80"]
      N_MIC["🎤 EXAMICLND001 · Shure SM7 via Dante audio · .81"]
      N_SWI["🔀 EXASWILND001 · Core switch · .250"]
      N_WKS["🖥️ EXAWKSLND001 · Workstation · .150"]
      N_PRN["🖨️ EXAPRNLND001 · Printer"]
      N_PRN2["🖨️ EXAPRNLND002 · Steno writer no IP"]
    end
    style NEW_LND fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:LND:END
```

---

## BIR — Birmingham 🪠

**LAN:** `192.168.121.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 121 496 0xxx · **Mobile:** +44 7700 900 2xxx

```mermaid
graph TD
    subgraph OLD_BIR ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWL["🧱 EXAFWLBIR001 · Palo Alto PAN-OS · .1"]
      SW1["🔀 EXASWIBIR001 · Cisco 9300 · .250"]
      SW2["🔀 EXASWIBIR002 · Access Switch · .251"]
      RTR["📡 EXARTRBIR001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACBIR001 · Dell DRAC · .2"]
      PVE["🗂️ EXAPVEBIR001 · Proxmox node 1 · .5"]
      DC1["🗝️ EXADCRBIR001 · DC primary · .10"]
      DC2["🗝️ EXADCRBIR002 · DC secondary · .11"]
      SRV["🗄️ EXASRVBIR001 · Rocky Linux · Oracle DB · .20"]
      SBC["🛡️ EXASBCBIR001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYBIR001 · Rudder Relay · .12"]
      MBP["💻 EXAMBPBIR001 · MacBook Pro · .41"]
      TAB["📱 EXATABBIR001 · Samsung Galaxy Tab · .61"]
      PHN["📞 EXAPHNBIR001 · Samsung S25 Ultra"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      MOO["🎹 EXAMOOBIR001 · Moog One Synthesizer · .70"]
      LIN["🥁 EXALINBIR001 · LinnDrum LM-2 · .71"]
      FCL["🎹 EXAFCLBIR001 · Fairlight CMI IIx · .72"]
      AST["🕹️ EXAASTBIR001 · Atari ST · MIDI · .73"]
      PAY["☎️ EXAPAYBIR001 · GPO Kiosk No.6 Payphone · .74"]
      LCD["🖼️ EXALCDBIR001 · NEC PlasmaSync NOC Display · .75"]
      VPN["🔗 WireGuard → FAL"]

      INET --> RTR --> FWL --> SW1 & SW2
      SW1 --> PVE --> DC1 & DC2 & SRV & SBC
      RAC -.->|"manages"| PVE
      SW2 --> MBP & TAB & PHN & WAP & CAM
      SW2 --> MOO & LIN & FCL & AST & PAY & LCD
      FWL <-->|"WireGuard tunnel"| VPN

      SW1 --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_BIR fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:BIR:START
    subgraph NEW_BIR ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRBIR001 · RTR · .1"]
      N_SBC["🛡️ EXASBCBIR001 · SBC · .48"]
      N_DCS["🗝️ EXADCSBIR001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLBIR001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLBIR002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEBIR001 · PVE 1 · .5"]
      N_SRV["🗄️ EXASRVBIR001 · Oracle DB · .20"]
      N_MOO["🎹 EXAMOOBIR001 · Moog synth · .70"]
      N_LIN["🥁 EXALINBIR001 · Drum machine · .71"]
      N_FCL["🎹 EXAFCLBIR001 · Fairlight CMI · .72"]
      N_AST["🕹️ EXAASTBIR001 · Atari ST · .73"]
      N_PAY["☎️ EXAPAYBIR001 · Payphone · .74"]
      N_LCD["🖼️ EXALCDBIR001 · NOC display · .75"]
      N_SWI["🔀 EXASWIBIR001 · Core switch · .250"]
      N_SWI2["🔀 EXASWIBIR002 · Access switch · .251"]
      N_MBP["💻 EXAMBPBIR001 · MacBook"]
      N_TAB["📱 EXATABBIR001 · Galaxy Tab"]
      N_PHN["📞 EXAPHNBIR001 · Samsung S25"]
    end
    style NEW_BIR fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:BIR:END
```

---

## MCR — Manchester 🐝

**LAN:** `192.168.161.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 161 715 xxxx · **Mobile:** +44 770 090 6xxx

```mermaid
graph TD
    subgraph OLD_MCR ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      SW["🔀 EXASWIMCR001 · Cisco 9300 · .250"]
      RAC["🔧 EXARACMCR001 · HPE iLO5 · .2"]
      PVE["🗂️ EXAPVEMCR001 · Proxmox node 1 · .5"]
      DC1["🗝️ EXADCRMCR001 · DC PDC · RID/Infra Master · .10"]
      DC2["🗝️ EXADCSMCR002 · DC secondary · .11"]
      SBC["🛡️ EXASBCMCR001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYMCR001 · Rudder Relay · .12"]
      LAP1["💻 EXALAPMCR001 · Win11 Laptop · .19"]
      LAP2["💻 EXALAPMCR002 · Win11 Laptop · .150"]
      WKS1["🖥️ EXAWKSMCR001 · Front Desk WKS · .152"]
      WKS2["🖥️ EXAWKSMCR002 · Finance WKS · .153"]
      PRN["🖨️ EXAPRNMCR001 · Network Printer · .16"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> SW
      SW --> PVE --> DC1 & DC2 & SBC
      RAC -.->|"manages"| PVE
      SW --> LAP1 & LAP2 & WKS1 & WKS2 & PRN & WAP & CAM
      SW <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_MCR fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:MCR:START
    subgraph NEW_MCR ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRMCR001 · RTR · .1"]
      N_SBC["🛡️ EXASBCMCR001 · SBC · .48"]
      N_DCS["🗝️ EXADCSMCR001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLMCR001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLMCR002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEMCR001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIMCR001 · Distribution switch · .250"]
      N_LAP["💻 EXALAPMCR001 · Laptop"]
      N_LAP2["💻 EXALAPMCR002 · Laptop"]
      N_WKS["🖥️ EXAWKSMCR001 · Desktop"]
      N_WKS2["🖥️ EXAWKSMCR002 · Desktop"]
      N_PRN["🖨️ EXAPRNMCR001 · Printer"]
    end
    style NEW_MCR fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:MCR:END
```

---

## LIV — Liverpool 🎸

**LAN:** `192.168.151.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 151 496 0xxx · **Mobile:** +44 770 090 5xxx

```mermaid
graph TD
    subgraph OLD_LIV ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      SW["🔀 EXASWILIV001 · Cisco 9200 · .250"]
      RAC["🔧 EXARACLIV001 · HPE iLO5 · .2"]
      PVE["🗂️ EXAPVELIV001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCRLIV001 · DC · WS2025 · .10"]
      SBC["🛡️ EXASBCLIV001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYLIV001 · Rudder Relay · .12"]
      SRV["🗄️ EXASVRLIV001 · WS2022 File Server · .10"]
      MBP["💻 EXAMBPLIV001 · MacBook Pro · macOS Tahoe · .150"]
      MAC["🍎 EXAMACLIV001 · iMac ⚠️ disabled · .152"]
      RDR["⚙️ EXARDRLIV002 · HID Signo Badge Reader · .16"]
      BPS["🪪 EXABPSLIV001 · Badge Programming WKS · .17"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> SW
      SW --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      SW --> SRV & MBP & MAC & RDR & BPS & WAP & CAM
      SW <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_LIV fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:LIV:START
    subgraph NEW_LIV ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRLIV001 · RTR · .1"]
      N_SBC["🛡️ EXASBCLIV001 · SBC · .48"]
      N_DCS["🗝️ EXADCSLIV001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLLIV001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLLIV002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVELIV001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWILIV001 · Core switch · .250"]
      N_SVR["🗄️ EXASVRLIV001 · File server"]
      N_MBP["💻 EXAMBPLIV001 · MacBook Pro"]
      N_MAC["🍎 EXAMACLIV001 · iMac DISABLED"]
      N_RDR["⚙️ EXARDRLIV002 · HID Signo badge reader"]
      N_BPS["🪪 EXABPSLIV001 · Badge programming workstation"]
    end
    style NEW_LIV fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:LIV:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class MAC warn
```

---

## NEW — Newcastle 🌉

**LAN:** `192.168.191.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 191 496 0xxx · **Mobile:** +44 770 090 9xxx

```mermaid
graph TD
    subgraph OLD_NEW ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      SW["🔀 EXASWINEW001 · TP-Link JetStream · .250"]
      RAC["🔧 EXARACNEW001 · Dell iDRAC9 · .2"]
      PVE["🗂️ EXAPVENEW001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCRNEW001 · DC · .10"]
      SBC["🛡️ EXASBCNEW001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYNEW001 · Rudder Relay · .12"]
      SRV["🗄️ EXASRVNEW001 · WS2022 File/Print Server · .21"]
      WKS["⚠️ 🖥️ EXAWKSNEW099 · Win11 WKS · LAPS expired · .161"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> SW
      SW --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      SW --> SRV & WKS & WAP & CAM
      SW <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_NEW fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:NEW:START
    subgraph NEW_NEW ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRNEW001 · RTR · .1"]
      N_SBC["🛡️ EXASBCNEW001 · SBC · .48"]
      N_DCS["🗝️ EXADCSNEW001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLNEW001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLNEW002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVENEW001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWINEW001 · Access switch · .250"]
      N_SRV["🗄️ EXASRVNEW001 · File/print server"]
      N_WKS["🖥️ EXAWKSNEW099 · LAPS password expired"]
    end
    style NEW_NEW fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:NEW:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class WKS warn
```

---

## SHE — Sheffield 🥄

**LAN:** `192.168.114.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 114 250 0xxx · **Mobile:** +44 7700 905 2xxx

```mermaid
graph TD
    subgraph OLD_SHE ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACSHE001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVESHE001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSSHE001 · DC · .10"]
      SBC["🛡️ EXASBCSHE001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYSHE001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      EP["Endpoints TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM & EP
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_SHE fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:SHE:START
    subgraph NEW_SHE ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRSHE001 · RTR · .1"]
      N_SBC["🛡️ EXASBCSHE001 · SBC · .48"]
      N_DCS["🗝️ EXADCSSHE001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLSHE001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLSHE002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVESHE001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWISHE001 · SWI 1 · .250"]
    end
    style NEW_SHE fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:SHE:END
```

---

## HAL — Halifax 🏦

**LAN:** `192.168.142.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 1422 200 0xxx · **Mobile:** +44 7700 904 2xxx

```mermaid
graph TD
    subgraph OLD_HAL ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACHAL001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEHAL001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSHAL001 · DC · .10"]
      SBC["🛡️ EXASBCHAL001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYHAL001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      EP["Endpoints TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM & EP
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_HAL fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:HAL:START
    subgraph NEW_HAL ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRHAL001 · RTR · .1"]
      N_SBC["🛡️ EXASBCHAL001 · SBC · .48"]
      N_DCS["🗝️ EXADCSHAL001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLHAL001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLHAL002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEHAL001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIHAL001 · SWI 1 · .250"]
    end
    style NEW_HAL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:HAL:END
```

---

## HUL — Hull 🎣

**LAN:** `192.168.148.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 1482 300 0xxx · **Mobile:** +44 7700 902 2xxx

```mermaid
graph TD
    subgraph OLD_HUL ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACHUL001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEHUL001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSHUL001 · DC · .10"]
      SBC["🛡️ EXASBCHUL001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYHUL001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      EP["Endpoints TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM & EP
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_HUL fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:HUL:START
    subgraph NEW_HUL ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRHUL001 · RTR · .1"]
      N_SBC["🛡️ EXASBCHUL001 · SBC · .48"]
      N_DCS["🗝️ EXADCSHUL001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLHUL001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLHUL002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEHUL001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIHUL001 · SWI 1 · .250"]
    end
    style NEW_HUL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:HUL:END
```

---

## COV — Coventry 🐎

**LAN:** `192.168.247.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
*Note: WAP/RTR-only site — minimal infrastructure.*  
**Entity:** Example Music (England) Ltd · **Landline:** +44 247 765 0xxx · **Mobile:** +44 7700 901 2xxx

```mermaid
graph TD
    subgraph OLD_COV ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RTR["📡 EXARTRCOV001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACCOV001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVECOV001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSCOV001 · DC · .10"]
      SBC["🛡️ EXASBCCOV001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYCOV001 · Rudder Relay · .12"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> RTR --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      RTR --> WAP & CAM
      RTR <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_COV fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:COV:START
    subgraph NEW_COV ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRCOV001 · RTR · .1"]
      N_SBC["🛡️ EXASBCCOV001 · SBC · .48"]
      N_DCS["🗝️ EXADCSCOV001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLCOV001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLCOV002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVECOV001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWICOV001 · SWI 1 · .250"]
    end
    style NEW_COV fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:COV:END
```
