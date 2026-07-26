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
    %% GENERATED:NEW-NETWORK:LAX:START
    subgraph NEW_LAX ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRLAX001 · RTR · .1"]
      N_SBC["🛡️ EXASBCLAX001 · SBC · .48"]
      N_NAS["🗃️ EXANASLAX001 · NAS · .19"]
      N_RDR["🔐 EXARDRLAX001 · RDR · .21"]
      N_BMC["🔧 EXABMCLAX001 · BMC 1 · .2"]
      N_DCS["🗝️ EXADCSLAX001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLLAX001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLLAX002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVELAX001 · PVE 1 · .5"]
      N_WAP["📶 EXAWAPLAX001 · WAP 1 · .82"]
      N_SRV["🗄️ EXASRVLAX001 · Local services DB · .20"]
      N_MUS["💿 EXAMUSLAX001 · Synth · .70"]
      N_MUS2["💿 EXAMUSLAX002 · Drum machine · .71"]
      N_MUS3["💿 EXAMUSLAX003 · Fairlight CMI · .72"]
      N_AST["🕹️ EXAASTLAX001 · Atari ST · .73"]
      N_PAY["☎️ EXAPAYLAX001 · Payphone · .74"]
      N_LCD["🖼️ EXALCDLAX001 · Status wallboard · .75"]
      N_SWI["🔀 EXASWILAX001 · Core switch · .250"]
      N_SWI2["🔀 EXASWILAX002 · Access switch · .251"]
      N_MBP["💻 EXAMBPLAX001 · MacBook Pro"]
      N_TAB["📱 EXATABLAX001 · iPad"]
      N_PHN["📞 EXAPHNLAX001 · Phone"]
    end
    style NEW_LAX fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:LAX:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
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
    %% GENERATED:NEW-NETWORK:NYC:START
    subgraph NEW_NYC ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRNYC001 · RTR · .1"]
      N_SBC["🛡️ EXASBCNYC001 · SBC · .48"]
      N_NAS["🗃️ EXANASNYC001 · NAS · .19"]
      N_RDR["🔐 EXARDRNYC001 · RDR · .21"]
      N_BMC["🔧 EXABMCNYC001 · BMC 1 · .2"]
      N_DCS["🗝️ EXADCSNYC001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLNYC001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLNYC002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVENYC001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWINYC001 · SWI 1 · .250"]
      N_WAP["📶 EXAWAPNYC001 · WAP 1 · .82"]
    end
    style NEW_NYC fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:NYC:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
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
    %% GENERATED:NEW-NETWORK:NJC:START
    subgraph NEW_NJC ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRNJC001 · RTR · .1"]
      N_SBC["🛡️ EXASBCNJC001 · SBC · .48"]
      N_NAS["🗃️ EXANASNJC001 · NAS · .19"]
      N_RDR["🔐 EXARDRNJC001 · RDR · .21"]
      N_BMC["🔧 EXABMCNJC001 · BMC 1 · .2"]
      N_DCS["🗝️ EXADCSNJC001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLNJC001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLNJC002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVENJC001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWINJC001 · SWI 1 · .250"]
      N_WAP["📶 EXAWAPNJC001 · WAP 1 · .82"]
    end
    style NEW_NJC fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:NJC:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
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
    %% GENERATED:NEW-NETWORK:MIA:START
    subgraph NEW_MIA ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRMIA001 · RTR · .1"]
      N_SBC["🛡️ EXASBCMIA001 · SBC · .48"]
      N_NAS["🗃️ EXANASMIA001 · NAS · .19"]
      N_RDR["🔐 EXARDRMIA001 · RDR · .21"]
      N_BMC["🔧 EXABMCMIA001 · BMC 1 · .2"]
      N_DCS["🗝️ EXADCSMIA001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLMIA001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLMIA002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEMIA001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIMIA001 · SWI 1 · .250"]
      N_WAP["📶 EXAWAPMIA001 · WAP 1 · .82"]
      N_COF["🍵 EXACOFMIA001 · Coffee machine · .60"]
      N_LAP["💻 EXALAPMIA001 · MacBook"]
    end
    style NEW_MIA fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:MIA:END
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
    %% GENERATED:NEW-NETWORK:ATL:START
    subgraph NEW_ATL ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRATL001 · RTR · .1"]
      N_SBC["🛡️ EXASBCATL001 · SBC · .48"]
      N_NAS["🗃️ EXANASATL001 · NAS · .19"]
      N_RDR["🔐 EXARDRATL001 · RDR · .21"]
      N_BMC["🔧 EXABMCATL001 · BMC 1 · .2"]
      N_DCS["🗝️ EXADCSATL001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLATL001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLATL002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEATL001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIATL001 · SWI 1 · .250"]
      N_WAP["📶 EXAWAPATL001 · WAP 1 · .82"]
    end
    style NEW_ATL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:ATL:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
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
    %% GENERATED:NEW-NETWORK:CHI:START
    subgraph NEW_CHI ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRCHI001 · RTR · .1"]
      N_SBC["🛡️ EXASBCCHI001 · SBC · .48"]
      N_NAS["🗃️ EXANASCHI001 · NAS · .19"]
      N_RDR["🔐 EXARDRCHI001 · RDR · .21"]
      N_BMC["🔧 EXABMCCHI001 · BMC 1 · .2"]
      N_DCS["🗝️ EXADCSCHI001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLCHI001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLCHI002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVECHI001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWICHI001 · SWI 1 · .250"]
      N_WAP["📶 EXAWAPCHI001 · WAP 1 · .82"]
    end
    style NEW_CHI fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:CHI:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

## SEA — Seattle *(New Build)* ☕

**LAN:** `192.168.206.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 (reserved — see notes below) · **VPN parent:** BRK  
**Entity:** Example Music (US) LLC. · **Landline:** +1 206 555 xxxx · **Mobile:** +1 425 555 xxxx

> **New-build site.** No legacy infrastructure ever existed here — see the "New Build Location" box below in place of "Old Network." Standard-slot addresses are allocated in `benarbejde/address_policy.json`/`sites.csv` the same as any other site, but no `devices.csv` exception rows exist yet.

```mermaid
graph TD
    subgraph OLD_SEA ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site. · No prior/legacy network existed before commissioning."]
    end
    style OLD_SEA fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:SEA:START
    subgraph NEW_SEA ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRSEA001 · RTR · .1"]
      N_SBC["🛡️ EXASBCSEA001 · SBC · .48"]
      N_NAS["🗃️ EXANASSEA001 · NAS · .19"]
      N_RDR["🔐 EXARDRSEA001 · RDR · .21"]
      N_BMC["🔧 EXABMCSEA001 · BMC 1 · .2"]
      N_DCS["🗝️ EXADCSSEA001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLSEA001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLSEA002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVESEA001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWISEA001 · SWI 1 · .250"]
      N_WAP["📶 EXAWAPSEA001 · WAP 1 · .82"]
    end
    style NEW_SEA fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:SEA:END
```

---

## SFO — San Francisco *(New Build)* 🌁

**LAN:** `192.168.145.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 (reserved — see notes below) · **VPN parent:** BRK  
**Entity:** Example Music (US) LLC. · **Landline:** +1 415 555 xxxx · **Mobile:** +1 628 555 xxxx

> **New-build site.** No legacy infrastructure ever existed here — see the "New Build Location" box below in place of "Old Network." Standard-slot addresses are allocated in `benarbejde/address_policy.json`/`sites.csv` the same as any other site, but no `devices.csv` exception rows exist yet.

```mermaid
graph TD
    subgraph OLD_SFO ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site. · No prior/legacy network existed before commissioning."]
    end
    style OLD_SFO fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:SFO:START
    subgraph NEW_SFO ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRSFO001 · RTR · .1"]
      N_SBC["🛡️ EXASBCSFO001 · SBC · .48"]
      N_NAS["🗃️ EXANASSFO001 · NAS · .19"]
      N_RDR["🔐 EXARDRSFO001 · RDR · .21"]
      N_BMC["🔧 EXABMCSFO001 · BMC 1 · .2"]
      N_DCS["🗝️ EXADCSSFO001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLSFO001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLSFO002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVESFO001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWISFO001 · SWI 1 · .250"]
      N_WAP["📶 EXAWAPSFO001 · WAP 1 · .82"]
    end
    style NEW_SFO fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:SFO:END
```
