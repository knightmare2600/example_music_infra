# Example Music Limited — Scotland Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## FAL — Falkirk *(Head Office)* ⭐ 🏛️

**Address:** Brockville Stadium, Hope Street, Falkirk  
**LAN:** `192.168.76.0/24` · **VPN:** `10.0.76.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (hub) · **VPN parent:** CLD (primary head node)  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 1324 500 0xxx · **Mobile:** +44 7700 903 2xxx

```mermaid
graph TD
    subgraph OLD_FAL ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RTR["📡 EXARTRFAL001 · Cisco ISR 4331 · .254"]
      FWL["🧱 EXAFWLFAL001 · FortiOS · .1"]
      SW1["🔀 EXASWIFAL001 · Cisco 9300 · .250"]
      SW2["🔀 EXASWIFAL002 · Cisco 9300 · .251"]

      subgraph BMC ["BMC Pool"]
          RAC1["🔧 EXARACFAL001 · Dell iDRAC9 · .2"]
          RAC2["🔧 EXARACFAL002 · Dell iDRAC9 · .3"]
          RAC3["🔧 EXARACFAL003 · Dell iDRAC9 · .4"]
      end

      subgraph PVE ["Proxmox Cluster (3-node)"]
          PVE1["🗂️ EXAPVEFAL001 · Proxmox node 1 · .5"]
          PVE2["🗂️ EXAPVEFAL002 · Proxmox node 2 · .6"]
          PVE3["🗂️ EXAPVEFAL003 · Proxmox node 3 · .7"]
      end

      subgraph DC ["Domain Controllers"]
          DC1["🗝️ EXADCSFAL001 · DC · PDC Emulator · .10"]
          DC2["🗝️ EXADCSFAL002 · DC secondary · .11"]
      end

      subgraph INFRA ["Infrastructure"]
          SBC["🛡️ EXASBCFAL001 · 3CX SBC → CLD PBX · .48"]
          RRY["🔁 EXARRYFAL001 · Rudder Relay · .12"]
          NAS["🗃️ EXANASFAL001 · FreeNAS 13.0-U6 · .32"]
          TAR["💽 EXATARFAL001 · Tape Archiver · .33"]
      end

      subgraph ENDPOINTS ["Endpoints"]
          WKS1["🖥️ EXAWKSFAL001 · Mixing Desk WKS · .100"]
          WKS2["🖥️ EXAWKSFAL002 · Reel-to-Reel WKS · .101"]
          WKS3["🖥️ EXAWKSFAL003 · Shared Editing WKS · .102"]
          LAP["💻 EXALAPFAL001 · Production Laptop · .103"]
          SUR["🖊️ EXASURFAL001 · Microsoft Surface · .104"]
          PHN["📞 EXAPHNFAL001-003 · Staff Phones"]
          PHN2["📞 EXAPHNFAL006-007 · Yealink T58A"]
          TAB["📱 EXATABFAL001 · Tablet"]
      end

      subgraph WAP_CAM ["Wireless & Security"]
          WAP["WAPs x6 · Ubiquiti UniFi U6-Pro · .5-.10"]
          CAM1["🎥 EXACAMFAL001 · Axis · Front entrance · .70"]
          CAM2["🎥 EXACAMFAL002 · Axis · Studio hallway · .71"]
          CAM3["🎥 EXACAMFAL003 · Axis · Car park · .72"]
          CAM4["🎥 EXACAMFAL004 · Axis · Loading bay · .73"]
          RDR["⚙️ EXARDRFAL001 · HID Signo Badge Reader · .16"]
      end

      subgraph SITE ["Site-Specific Equipment"]
          LCD["🖼️ EXALCDFAL001 · Samsung Tizen Display · .50"]
          VCU["🎧 EXAVCUFAL001 · Poly Studio X70 · .51"]
          JKB["💿 EXAMUSFAL001 · Pureline 128V Jukebox · .67"]
          PAY["☎️ EXAPAYFAL001 · GPO Kiosk No.6 Payphone · .95"]
          COF["🫖 EXATEAFAL001 · Smart Coffee Machine · .61"]
          VND1["🍩 EXADONFAL001 · Tim Hortons Vending · .62"]
          VND2["🍫 EXAVNDFAL002 · Irn-Bru Machine · .63"]
          VND3["🍫 EXAVNDFAL003 · McCowans Dispenser · .64"]
          VND4["🍫 EXAVNDFAL004 · Mrs Tily Dispenser · .65"]
          VND5["🍫 EXAVNDFAL005 · ¼lb Confectionery · .66"]
          PMP["⛽ EXAPMPFAL001 · Networked Petrol Pump · .60"]
          CLK["⏰ EXACLKFAL001 · NTP Clock · .80"]
      end

      VPN_CLD["🔗 WireGuard ← CLD · 10.0.76.0/24"]

      INET --> RTR --> FWL --> SW1 & SW2
      SW1 --> PVE1 & PVE2 & PVE3
      SW1 --> DC1 & DC2
      SW1 --> SBC & NAS & TAR
      SW2 --> WKS1
      SW2 --> WAP
      SW2 --> LCD
      RAC1 -.->|"manages"| PVE1
      RAC2 -.->|"manages"| PVE2
      RAC3 -.->|"manages"| PVE3
      FWL <-->|"WireGuard tunnel"| VPN_CLD

      SW1 --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN_CLD
    end
    style OLD_FAL fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:FAL:START
    subgraph NEW_FAL ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRFAL001 · RTR · .1"]
      N_PRV["📦 EXAPRVFAL001 · PRV · .15"]
      N_SBC["🛡️ EXASBCFAL001 · SBC · .48"]
      N_DCS["🗝️ EXADCSFAL001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLFAL001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLFAL002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEFAL001 · PVE 1 · .5"]
      N_RDR["⚙️ EXARDRFAL001 · HID Signo badge reader · .16"]
      N_SRV["🗄️ EXASRVFAL001 · Reserved · .20"]
      N_NAS["🗃️ EXANASFAL001 · Primary storage · .32"]
      N_TAR["💽 EXATARFAL001 · Legacy tape archive · .33"]
      N_LCD["🖼️ EXALCDFAL001 · Reception display · .50"]
      N_VCU["🎧 EXAVCUFAL001 · Video conferencing · .51"]
      N_PMP["⛽ EXAPMPFAL001 · Networked petrol pump · .60"]
      N_TEA["🫖 EXATEAFAL001 · Smart coffee machine · .61"]
      N_DON["🍩 EXADONFAL001 · Donut vending · .62"]
      N_VND["🍫 EXAVNDFAL002 · Vending machine · .63"]
      N_VND2["🍫 EXAVNDFAL003 · Vending machine · .64"]
      N_VND3["🍫 EXAVNDFAL004 · Vending machine · .65"]
      N_VND4["🍫 EXAVNDFAL005 · Confectionery machine · .66"]
      N_MUS["💿 EXAMUSFAL001 · Jukebox · .67"]
      N_CAM["🎥 EXACAMFAL001 · Camera front entrance · .70"]
      N_CAM2["🎥 EXACAMFAL002 · Camera studio hallway · .71"]
      N_CAM3["🎥 EXACAMFAL003 · Camera car park · .72"]
      N_CAM4["🎥 EXACAMFAL004 · Camera rear loading bay · .73"]
      N_CLK["⏰ EXACLKFAL001 · Embedded NTP clock · .80"]
      N_PAY["☎️ EXAPAYFAL001 · GPO Kiosk No.6 payphone · .95"]
      N_WKS["🖥️ EXAWKSFAL001 · Workstation Analog Mixing Desk v1 · .100"]
      N_WKS2["🖥️ EXAWKSFAL003 · Workstation shared editing · .102"]
      N_LAP["💻 EXALAPFAL001 · Production laptop · .103"]
      N_SUR["🖊️ EXASURFAL001 · Microsoft Surface · .104"]
      N_SWI["🔀 EXASWIFAL001 · Core switch 1 · .250"]
      N_SWI2["🔀 EXASWIFAL002 · Core switch 2 · .251"]
      N_PHN["📞 EXAPHNFAL001 · Phone 1"]
      N_PHN2["📞 EXAPHNFAL002 · Phone 2"]
      N_PHN3["📞 EXAPHNFAL003 · Phone 3"]
      N_PHN4["📞 EXAPHNFAL006 · Phone 6"]
      N_PHN5["📞 EXAPHNFAL007 · Phone 7"]
      N_TAB["📱 EXATABFAL001 · Tablet"]
      N_TTY["⌨️ EXATTYFAL001 · VT320 serial terminal"]
      N_BUS["🚌 EXABUSFAL001 · Tour bus 1"]
      N_BUS2["🚌 EXABUSFAL002 · Tour bus 2"]
      N_BUS3["🚌 EXABUSFAL003 · Tour bus 3"]
      N_CAR["🚗 EXACARFAL001 · Car 1"]
      N_CAR2["🚗 EXACARFAL002 · Car 2"]
      N_CAR3["🚗 EXACARFAL003 · Car 3"]
      N_CAR4["🚗 EXACARFAL004 · Car 4"]
      N_CAR5["🚗 EXACARFAL005 · Car 5"]
      N_TRK["🚚 EXATRKFAL001 · Truck 1"]
      N_TRK2["🚚 EXATRKFAL002 · Truck 2"]
      N_TRK3["🚚 EXATRKFAL003 · Truck 3"]
      N_TRK4["🚚 EXATRKFAL004 · Truck 4"]
      N_TRK5["🚚 EXATRKFAL005 · Truck 5"]
      N_JET["✈️ EXAJETFAL001 · Jet 1"]
      N_JET2["✈️ EXAJETFAL002 · Jet 2"]
      N_JET3["✈️ EXAJETFAL003 · Jet 3"]
      N_JET4["✈️ EXAJETFAL004 · Jet 4"]
      N_JET5["✈️ EXAJETFAL005 · Jet 5"]
    end
    style NEW_FAL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:FAL:END
```

---

## EDI — Edinburgh ⚠️ 🏰

**LAN:** `192.168.131.0/24` · **Domain:** `example.org` / `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
> ⚠️ `EXADCSEDI003` — DFSR stopped, C: drive at 5% free. Immediate action required.  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 131 496 0xxx · **Mobile:** +44 770 090 3xxx

```mermaid
graph TD
    subgraph OLD_EDI ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RTR["📡 EXARTREDI001 · Cisco ISR 4331 · .254"]
      SW1["🔀 EXASWIEDI001 · Cisco 2960X · .250"]
      SW2["🔀 EXASWIEDI002 · Cisco 2960X · .251"]
      RAC["🔧 EXARACEDI001 · Dell iDRAC9 · .2"]
      PVE["🗂️ EXAPVEEDI001 · Proxmox node 1 · .5"]
      DC["⚠️ 🗝️ EXADCSEDI003 · DC · DFSR stopped · C: 5% free · .11"]
      SBC["🛡️ EXASBCEDI001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYEDI001 · Rudder Relay · .12"]
      WKS["🖥️ EXAWKSEDI001 · Workstation · .150"]
      LAP["💻 EXALAPEDI098 · Pool Laptop · .108"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      COF["🫖 EXATEAEDI001 · Siemens EQ700 Coffee Machine · .60"]
      VPN["🔗 WireGuard → FAL"]

      INET --> RTR --> SW1 & SW2
      SW1 --> PVE --> DC
      SW1 --> SBC
      RAC -.->|"manages"| PVE
      SW2 --> WKS & LAP & WAP & CAM & COF
      RTR <-->|"WireGuard tunnel"| VPN

      SW1 --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_EDI fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:EDI:START
    subgraph NEW_EDI ["🆕 New Network (current)"]
      N_RTR["📡 EXARTREDI001 · RTR · .1"]
      N_PRV["📦 EXAPRVEDI001 · PRV · .15"]
      N_SBC["🛡️ EXASBCEDI001 · SBC · .48"]
      N_DCS["🗝️ EXADCSEDI001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLEDI001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLEDI002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEEDI001 · PVE 1 · .5"]
      N_DCR["🗝️ EXADCREDI002 · DC secondary needs rebuild corrected to .12 · .12"]
      N_DCR2["🗝️ EXADCREDI003 · DECOMMISSION PENDING corrected to .13 · .13"]
      N_WKS["🖥️ EXAWKSEDI001 · Shared desktop · .150"]
      N_LAP["💻 EXALAPEDI098 · Pool laptop · .108"]
      N_SWI["🔀 EXASWIEDI001 · Floor switch · .250"]
      N_SWI2["🔀 EXASWIEDI002 · 48-port switch · .251"]
      N_TEA["🫖 EXATEAEDI001 · Coffee machine · .60"]
    end
    style NEW_EDI fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:EDI:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

## GLA — Glasgow 🚧

**LAN:** `192.168.141.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 141 496 01xx · **Mobile:** +44 770 009 4xxx

```mermaid
graph TD
    subgraph OLD_GLA ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      PVE["🗂️ EXAPVEGLA001 · Proxmox node 1 · .5"]
      RAC["🔧 EXARACGLA001 · BMC node 1 · .2"]
      DC["🗝️ EXADCRGLA001 · DC · Schema/DN Master · PDC Emulator · .10"]
      SBC["🛡️ EXASBCGLA001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYGLA001 · Rudder Relay · .12"]
      WKS1["🖥️ EXAWKSGLA001 · Hot Desk WKS · .150"]
      WKS2["🖥️ EXAWKSGLA002 · Hot Desk WKS · .151"]
      LAP["💻 EXALAPGLA001 · Pool Laptop · .152"]
      PRN["🖨️ EXAPRNGLA001 · HP LaserJet Pro · .16"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> PVE
      PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WKS1 & WKS2 & LAP & PRN & WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_GLA fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:GLA:START
    subgraph NEW_GLA ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRGLA001 · RTR · .1"]
      N_PRV["📦 EXAPRVGLA001 · PRV · .15"]
      N_SBC["🛡️ EXASBCGLA001 · SBC · .48"]
      N_DCS["🗝️ EXADCSGLA001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLGLA001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLGLA002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEGLA001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIGLA001 · SWI 1 · .250"]
      N_PRN["🖨️ EXAPRNGLA001 · Main floor printer · .16"]
      N_WKS["🖥️ EXAWKSGLA001 · Hot desk workstation · .150"]
      N_WKS2["🖥️ EXAWKSGLA002 · Hot desk workstation · .151"]
      N_LAP["💻 EXALAPGLA001 · Pool laptop · .152"]
    end
    style NEW_GLA fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:GLA:END
```

---

## CLY — Clydebank 🚢

**LAN:** `192.168.41.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 141 496 00xx · **Mobile:** +44 770 090 5xxx

```mermaid
graph TD
    subgraph OLD_CLY ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWL["🧱 EXAFWLCLY001 · FortiOS 7.6.5 · .1"]
      RTR["📡 EXARTRCLY001 · Cisco ISR 4331 · .254"]
      SW["🔀 EXASWICLY001 · Cisco 9300 · .250"]
      RAC["🔧 EXARACCLY001 · HPE iLO5 · .2"]
      PVE["🗂️ EXAPVECLY001 · Proxmox node 1 · .5"]
      DC1["🗝️ EXADCSCLY001 · DC primary · .10"]
      DC2["🗝️ EXADCSCLY002 · DC secondary · .11"]
      SRV["🗄️ EXASRVCLY001 · Rocky Linux · Oracle DB · .20"]
      SBC["🛡️ EXASBCCLY001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYCLY001 · Rudder Relay · .12"]
      SUR["🖊️ EXASURCLY001 · Microsoft Surface · .51"]
      PHN["📞 EXAPHNCLY001 · iOS handset"]
      TAB["🖊️ EXASURCLY002 · Android Tablet"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> RTR --> FWL --> SW
      SW --> PVE --> DC1 & DC2 & SRV & SBC
      RAC -.->|"manages"| PVE
      SW --> SUR & PHN & TAB & WAP & CAM
      FWL <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_CLY fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:CLY:START
    subgraph NEW_CLY ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRCLY001 · RTR · .1"]
      N_PRV["📦 EXAPRVCLY001 · PRV · .15"]
      N_SBC["🛡️ EXASBCCLY001 · SBC · .48"]
      N_DCS["🗝️ EXADCSCLY001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLCLY001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLCLY002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVECLY001 · PVE 1 · .5"]
      N_SRV["🗄️ EXASRVCLY001 · Oracle DB server · .20"]
      N_SWI["🔀 EXASWICLY001 · Core switch · .250"]
      N_SUR["🖊️ EXASURCLY001 · Surface"]
      N_PHN["📞 EXAPHNCLY001 · Phone"]
      N_TAB["📱 EXATABCLY001 · Android tablet"]
    end
    style NEW_CLY fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:CLY:END
```

---

## DUN — Dundee 🛳️

**LAN:** `192.168.138.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 163 249 60xx · **Mobile:** +44 770 090 82xx

```mermaid
graph TD
    subgraph OLD_DUN ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RTR["📡 EXARTRDUN001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACDUN001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEDUN001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSDUN001 · DC · .10"]
      SBC["🛡️ EXASBCDUN001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYDUN001 · Rudder Relay · .12"]
      SUR1["🖊️ EXASURDUN001 · Surface · .51"]
      SUR2["🖊️ EXASURDUN002 · Surface · .52"]
      PHN1["📞 EXAPHNDUN001 · iOS Phone"]
      PHN2["📞 EXAPHNDUN002 · iOS Phone"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> RTR --> PVE
      PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      RTR --> SUR1 & SUR2 & PHN1 & PHN2 & WAP & CAM
      RTR <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_DUN fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:DUN:START
    subgraph NEW_DUN ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRDUN001 · RTR · .1"]
      N_PRV["📦 EXAPRVDUN001 · PRV · .15"]
      N_SBC["🛡️ EXASBCDUN001 · SBC · .48"]
      N_DCS["🗝️ EXADCSDUN001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLDUN001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLDUN002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEDUN001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIDUN001 · SWI 1 · .250"]
      N_SUR["🖊️ EXASURDUN001 · Surface"]
      N_SUR2["🖊️ EXASURDUN002 · Surface"]
      N_PHN["📞 EXAPHNDUN001 · Phone"]
      N_PHN2["📞 EXAPHNDUN002 · Phone"]
    end
    style NEW_DUN fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:DUN:END
```

---

## PER — Perth 👑

**LAN:** `192.168.173.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 173 849 60xx · **Mobile:** +44 770 0173 0xx

```mermaid
graph TD
    subgraph OLD_PER ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACPER001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEPER001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSPER001 · DC · .10"]
      SBC["🛡️ EXASBCPER001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYPER001 · Rudder Relay · .12"]
      NIX["🐧 EXANIXPER001 · Solaris 11.5 · MIDI/Music Archive · .40"]
      NAS["🗃️ EXANASPER001 · Synology NAS · .50"]
      MBP["💻 EXAMBPPER001 · MacBook Pro · .70"]
      SUR["🖊️ EXASURPER001 · Surface · .71"]
      PHN["📞 EXAPHNPER001-004 · Yealink T46G Phones · .80"]
      PRN["🖨️ EXAPRNPER001 · HP MFP Printer · .20"]
      VND["🍫 EXAVNDPER001 · Scone Palace Vending Machine · .60"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> PVE
      PVE --> DC & SBC & NIX & NAS
      RAC -.->|"manages"| PVE
      PVE --> MBP & SUR & PHN & PRN & VND & WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_PER fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:PER:START
    subgraph NEW_PER ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRPER001 · RTR · .1"]
      N_PRV["📦 EXAPRVPER001 · PRV · .15"]
      N_SBC["🛡️ EXASBCPER001 · SBC · .48"]
      N_DCS["🗝️ EXADCSPER001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLPER001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLPER002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEPER001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIPER001 · SWI 1 · .250"]
      N_NIX["🐧 EXANIXPER001 · MIDI archive · .40"]
      N_NAS["🗃️ EXANASPER001 · NAS · .50"]
      N_MBP["💻 EXAMBPPER001 · MacBook"]
      N_SUR["🖊️ EXASURPER001 · Surface"]
      N_PHN["📞 EXAPHNPER001 · Phone 1"]
      N_PHN2["📞 EXAPHNPER002 · Phone 2"]
      N_PHN3["📞 EXAPHNPER003 · Phone 3"]
      N_PHN4["📞 EXAPHNPER004 · Phone 4"]
      N_PRN["🖨️ EXAPRNPER001 · Printer"]
      N_VND["🍫 EXAVNDPER001 · Vending machine"]
    end
    style NEW_PER fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:PER:END
```

---

## ABD — Aberdeen 🪨

**LAN:** `192.168.224.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 1224 496 0xxx · **Mobile:** +44 7700 900 2xxx

```mermaid
graph TD
    subgraph OLD_ABD ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWL["🧱 EXAFWLABD001 · Cisco ASA 5506-X · .1"]
      RTR["📡 EXARTRABD001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACABD001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEABD001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSABD001 · DC · .10"]
      SBC["🛡️ EXASBCABD001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYABD001 · Rudder Relay · .12"]
      MBP1["💻 EXAMBPABD001 · MacBook · .137"]
      MBP2["💻 EXAMBPABD002 · MacBook · .124"]
      PHN1["📞 EXAPHNABD001 · Corporate iPhone"]
      PHN2["📞 EXAPHNABD002 · Corporate iPhone"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → FAL"]

      INET --> RTR --> FWL --> PVE
      PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      FWL --> MBP1 & MBP2 & PHN1 & PHN2 & WAP & CAM
      FWL <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_ABD fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:ABD:START
    subgraph NEW_ABD ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRABD001 · RTR · .1"]
      N_PRV["📦 EXAPRVABD001 · PRV · .15"]
      N_SBC["🛡️ EXASBCABD001 · SBC · .48"]
      N_DCS["🗝️ EXADCSABD001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLABD001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLABD002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEABD001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIABD001 · SWI 1 · .250"]
      N_MBP["💻 EXAMBPABD001 · MacBook"]
      N_MBP2["💻 EXAMBPABD002 · MacBook"]
      N_PHN["📞 EXAPHNABD001 · iPhone"]
      N_PHN2["📞 EXAPHNABD002 · iPhone"]
    end
    style NEW_ABD fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:ABD:END
```
