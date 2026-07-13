# Mermaid render bisection — Q4

Throwaway debug file, sites: TOR, MTL, LAX, NYC, NJC, MIA, ATL, CHI, SEA, SFO, SYD, MEL, AKL

---

## TOR — Toronto ⚠️

**LAN:** `192.168.146.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSTOR001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (Canada) Inc. · **Landline:** +1 416 555 xxxx · **Mobile:** +1 647 555 xxxx

```mermaid
graph TD
    subgraph OLD_TOR ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACTOR001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVETOR001<br/>Proxmox node 1<br/>.5")]
      DC[("🔴 EXADCSTOR001<br/>DC · Services stopped<br/>.10")]
      SBC[("EXASBCTOR001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYTOR001<br/>Rudder Relay<br/>.12")]
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → BRK"])

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
      N_RTR{{"EXARTRTOR001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVTOR001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCTOR001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSTOR001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLTOR001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLTOR002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVETOR001<br/>PVE 1<br/>.5")]
    end
    style NEW_TOR fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:TOR:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

## MTL — Montreal

**LAN:** `192.168.154.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
**Entity:** Example Music (Canada) Inc. · **Landline:** +1 514 400 0xxx · **Mobile:** +1 514 900 2xxx

```mermaid
graph TD
    subgraph OLD_MTL ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACMTL001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEMTL001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSMTL001<br/>DC<br/>.10")]
      SBC[("EXASBCMTL001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYMTL001<br/>Rudder Relay<br/>.12")]
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → BRK"])

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
      N_RTR{{"EXARTRMTL001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVMTL001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCMTL001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSMTL001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLMTL001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLMTL002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEMTL001<br/>PVE 1<br/>.5")]
    end
    style NEW_MTL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:MTL:END
```

---

---

## 🇺🇸 United States

---

## LAX — Los Angeles ⚠️

**LAN:** `192.168.213.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSLAX001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (US) LLC. · **Landline:** +1 213 555 xxxx · **Mobile:** +1 213 555 xxx

```mermaid
graph TD
    subgraph OLD_LAX ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      FWL{{"EXAFWLLAX001<br/>Palo Alto PAN-OS 10.x<br/>.1"}}
      SW1{{"EXASWILAX001<br/>Cisco 9300<br/>.250"}}
      SW2{{"EXASWILAX002<br/>Cisco 2960<br/>.251"}}
      RTR{{"EXARTRLAX001<br/>Cisco ISR 4331<br/>.254"}}
      RAC[("EXARACLAX001<br/>Dell iDRAC9<br/>.2")]
      PVE[("EXAPVELAX001<br/>Proxmox node 1<br/>.5")]
      DC[("🔴 EXADCSLAX001<br/>DC · Services stopped<br/>.10")]
      SRV[("EXASRVLAX001<br/>Rocky Linux · Local services/DB<br/>.20")]
      SBC[("EXASBCLAX001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYLAX001<br/>Rudder Relay<br/>.12")]
      MBP(["EXAMBPLAX001<br/>MacBook Pro<br/>.41"])
      TAB(["EXATABLAX001<br/>iPad · Setlists<br/>.61"])
      PHN(["EXAPHNLAX001<br/>Android Phone"])
      WAP["WAPs x3<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      MOO>"EXAMUSLAX001<br/>Moog One Synthesizer<br/>.70"]
      LIN>"EXAMUSLAX002<br/>LinnDrum LM-2<br/>.71"]
      FCL>"EXAMUSLAX003<br/>Fairlight CMI IIx<br/>.72"]
      AST>"EXATTYLAX001<br/>Atari ST · MIDI<br/>.73"]
      PAY>"EXAPAYLAX001<br/>Lobby Payphone<br/>.74"]
      LCD(["EXALCDLAX001<br/>NEC PlasmaSync Display<br/>.75"])
      VPN(["🔗 WireGuard → BRK"])

      INET --> RTR --> FWL --> SW1 & SW2
      SW1 --> PVE --> DC & SRV & SBC
      RAC -.->|"manages"| PVE
      SW2 --> MBP & TAB & PHN & WAP & CAM
      SW2 --> MOO & LIN & FCL & AST & PAY & LCD
      FWL <-->|"WireGuard tunnel"| VPN

      SW1 --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_LAX fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:LAX:START
    subgraph NEW_LAX ["🆕 New Network (current)"]
      N_RTR{{"EXARTRLAX001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVLAX001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCLAX001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSLAX001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLLAX001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLLAX002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVELAX001<br/>PVE 1<br/>.5")]
      N_SRV[("EXASRVLAX001<br/>Local services DB<br/>.20")]
      N_MUS>"💿 EXAMUSLAX001<br/>Synth<br/>.70"]
      N_MUS2>"💿 EXAMUSLAX002<br/>Drum machine<br/>.71"]
      N_MUS3>"💿 EXAMUSLAX003<br/>Fairlight CMI<br/>.72"]
      N_AST>"🕹️ EXAASTLAX001<br/>Atari ST<br/>.73"]
      N_PAY>"☎️ EXAPAYLAX001<br/>Payphone<br/>.74"]
      N_LCD(["EXALCDLAX001<br/>Status wallboard<br/>.75"])
      N_SWI{{"EXASWILAX001<br/>Core switch<br/>.250"}}
      N_SWI2{{"EXASWILAX002<br/>Access switch<br/>.251"}}
      N_MBP(["EXAMBPLAX001<br/>MacBook Pro"])
      N_TAB(["EXATABLAX001<br/>iPad"])
      N_PHN(["EXAPHNLAX001<br/>Phone"])
    end
    style NEW_LAX fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:LAX:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

## NYC — New York ⚠️

**LAN:** `192.168.212.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSNYC001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (US) LLC. · **Landline:** +1 212 500 0xxx · **Mobile:** +1 917 900 2xxx

```mermaid
graph TD
    subgraph OLD_NYC ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACNYC001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVENYC001<br/>Proxmox node 1<br/>.5")]
      DC[("🔴 EXADCSNYC001<br/>DC · Services stopped<br/>.10")]
      SBC[("EXASBCNYC001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYNYC001<br/>Rudder Relay<br/>.12")]
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → BRK"])

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_NYC fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:NYC:START
    subgraph NEW_NYC ["🆕 New Network (current)"]
      N_RTR{{"EXARTRNYC001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVNYC001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCNYC001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSNYC001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLNYC001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLNYC002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVENYC001<br/>PVE 1<br/>.5")]
    end
    style NEW_NYC fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:NYC:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

## NJC — New Jersey ⚠️

**LAN:** `192.168.201.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSNJC001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (US) LLC. · **Landline:** +1 201 400 0xxx · **Mobile:** +1 908 900 2xxx

```mermaid
graph TD
    subgraph OLD_NJC ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACNJC001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVENJC001<br/>Proxmox node 1<br/>.5")]
      DC[("🔴 EXADCSNJC001<br/>DC · Services stopped<br/>.10")]
      SBC[("EXASBCNJC001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYNJC001<br/>Rudder Relay<br/>.12")]
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → BRK"])

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_NJC fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:NJC:START
    subgraph NEW_NJC ["🆕 New Network (current)"]
      N_RTR{{"EXARTRNJC001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVNJC001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCNJC001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSNJC001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLNJC001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLNJC002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVENJC001<br/>PVE 1<br/>.5")]
    end
    style NEW_NJC fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:NJC:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

## MIA — Miami

**LAN:** `192.168.135.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
**Entity:** Example Music (US) LLC. · **Landline:** +1 305 555 xxxx · **Mobile:** +1 786 555 xxxx

```mermaid
graph TD
    subgraph OLD_MIA ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACMIA001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEMIA001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSMIA001<br/>DC<br/>.10")]
      SBC[("EXASBCMIA001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYMIA001<br/>Rudder Relay<br/>.12")]
      LAP(["EXALAPMIA001<br/>macOS Sonoma Laptop<br/>.21"])
      COF>"EXACOFMIA001<br/>Cuban Covfefe Machine<br/>VxWorks · .60"]
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → BRK"])

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> LAP & COF & WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_MIA fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:MIA:START
    subgraph NEW_MIA ["🆕 New Network (current)"]
      N_RTR{{"EXARTRMIA001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVMIA001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCMIA001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSMIA001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLMIA001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLMIA002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEMIA001<br/>PVE 1<br/>.5")]
      N_COF>"☕ EXACOFMIA001<br/>Coffee machine<br/>.60"]
      N_LAP(["EXALAPMIA001<br/>MacBook"])
    end
    style NEW_MIA fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:MIA:END
```

---

## ATL — Atlanta ⚠️

**LAN:** `192.168.33.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSATL001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (US) LLC. · **Landline:** +1 334 300 0xxx · **Mobile:** +1 770 900 2xxx

```mermaid
graph TD
    subgraph OLD_ATL ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACATL001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEATL001<br/>Proxmox node 1<br/>.5")]
      DC[("🔴 EXADCSATL001<br/>DC · Services stopped<br/>.10")]
      SBC[("EXASBCATL001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYATL001<br/>Rudder Relay<br/>.12")]
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → BRK"])

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_ATL fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:ATL:START
    subgraph NEW_ATL ["🆕 New Network (current)"]
      N_RTR{{"EXARTRATL001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVATL001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCATL001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSATL001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLATL001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLATL002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEATL001<br/>PVE 1<br/>.5")]
    end
    style NEW_ATL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:ATL:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

## CHI — Chicago ⚠️

**LAN:** `192.168.214.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSCHI001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (US) LLC. · **Landline:** +1 312 555 xxxx · **Mobile:** +1 773 900 xxxx

```mermaid
graph TD
    subgraph OLD_CHI ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACCHI001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVECHI001<br/>Proxmox node 1<br/>.5")]
      DC[("🔴 EXADCSCHI001<br/>DC · Services stopped<br/>.10")]
      SBC[("EXASBCCHI001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYCHI001<br/>Rudder Relay<br/>.12")]
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → BRK"])

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_CHI fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:CHI:START
    subgraph NEW_CHI ["🆕 New Network (current)"]
      N_RTR{{"EXARTRCHI001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVCHI001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCCHI001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSCHI001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLCHI001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLCHI002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVECHI001<br/>PVE 1<br/>.5")]
    end
    style NEW_CHI fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:CHI:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

## SEA — Seattle *(New Build)*

**LAN:** `192.168.206.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 (reserved — see notes below) · **VPN parent:** BRK  
**Entity:** Example Music (US) LLC. · **Landline:** +1 206 555 xxxx · **Mobile:** +1 425 555 xxxx

> **New-build site.** No legacy infrastructure ever existed here — see the "New Build Location" box below in place of "Old Network." Standard-slot addresses are allocated in `benarbejde/address_policy.json`/`sites.csv` the same as any other site, but no `devices.csv` exception rows exist yet.

```mermaid
graph TD
    subgraph OLD_SEA ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site.<br/>No prior/legacy network existed before commissioning."]
    end
    style OLD_SEA fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:SEA:START
    subgraph NEW_SEA ["🆕 New Network (current)"]
      N_RTR{{"EXARTRSEA001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVSEA001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCSEA001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSSEA001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLSEA001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLSEA002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVESEA001<br/>PVE 1<br/>.5")]
    end
    style NEW_SEA fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:SEA:END
```

---

## SFO — San Francisco *(New Build)*

**LAN:** `192.168.145.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 (reserved — see notes below) · **VPN parent:** BRK  
**Entity:** Example Music (US) LLC. · **Landline:** +1 415 555 xxxx · **Mobile:** +1 628 555 xxxx

> **New-build site.** No legacy infrastructure ever existed here — see the "New Build Location" box below in place of "Old Network." Standard-slot addresses are allocated in `benarbejde/address_policy.json`/`sites.csv` the same as any other site, but no `devices.csv` exception rows exist yet.

```mermaid
graph TD
    subgraph OLD_SFO ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site.<br/>No prior/legacy network existed before commissioning."]
    end
    style OLD_SFO fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:SFO:START
    subgraph NEW_SFO ["🆕 New Network (current)"]
      N_RTR{{"EXARTRSFO001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVSFO001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCSFO001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSSFO001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLSFO001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLSFO002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVESFO001<br/>PVE 1<br/>.5")]
    end
    style NEW_SFO fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:SFO:END
```

---

---

## 🇦🇺 Australia

---

## SYD — Sydney ⚠️

**LAN:** `192.168.29.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSSYD001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (Australia) Pty Ltd · **Landline:** +61 2 9000 0xxx · **Mobile:** +61 400 900 2xxx

```mermaid
graph TD
    subgraph OLD_SYD ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      FWL{{"EXAFWLSYD001<br/>FortiGate 7.x<br/>.1"}}
      SW1{{"EXASWISYD001<br/>Cisco 9300<br/>.250"}}
      SW2{{"EXASWISYD002<br/>Cisco 2960<br/>.251"}}
      RAC[("EXARACSYD001<br/>Dell iDRAC9<br/>.2")]
      PVE[("EXAPVESYD001<br/>Proxmox node 1<br/>.5")]
      DC[("🔴 EXADCSSYD001<br/>DC · Services stopped<br/>.10")]
      SRV[("EXASRVSYD001<br/>WS2022 Local Infra<br/>.20")]
      SBC[("EXASBCSYD001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYSYD001<br/>Rudder Relay<br/>.12")]
      MBP(["EXAMBPSYD001<br/>MacBook Pro<br/>.40"])
      WKS(["EXAWKSSYD001<br/>Win11 Workstation<br/>.41"])
      PHN(["EXAPHNSYD001<br/>Android Phone"])
      TAB(["EXATABSYD001<br/>iPad · Setlists<br/>.60"])
      WAP(("EXAWAPSYD001<br/>Ubiquiti UniFi"))
      CAM1(["EXACAMSYD001<br/>Hikvision · Coffee cam<br/>.82"])
      CAM2(["EXACAMSYD002<br/>Hikvision · Reception<br/>.83"])
      LCD(["EXALCDSYD001<br/>LG Signage Wallboard<br/>.70"])
      PRN(["EXAPRNSYD001<br/>Brother Laser Printer<br/>.80"])
      COF>"EXACOFSYD001<br/>Smart Coffee Machine<br/>RFC2324 · .83"]
      VPN(["🔗 WireGuard → BRK"])

      INET --> FWL --> SW1 & SW2
      SW1 --> PVE --> DC & SRV & SBC
      RAC -.->|"manages"| PVE
      SW2 --> MBP & WKS & PHN & TAB & WAP
      SW2 --> CAM1 & CAM2 & LCD & PRN & COF
      FWL <-->|"WireGuard tunnel"| VPN

      SW1 --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_SYD fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:SYD:START
    subgraph NEW_SYD ["🆕 New Network (current)"]
      N_RTR{{"EXARTRSYD001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVSYD001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCSYD001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSSYD001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLSYD001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLSYD002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVESYD001<br/>PVE 1<br/>.5")]
      N_SRV[("EXASRVSYD001<br/>Local infra server<br/>.20")]
      N_SWI{{"EXASWISYD001<br/>Core switch<br/>.250"}}
      N_SWI2{{"EXASWISYD002<br/>Access switch<br/>.251"}}
      N_MBP(["EXAMBPSYD001<br/>MacBook Pro"])
      N_WKS(["EXAWKSSYD001<br/>Workstation"])
      N_PHN(["EXAPHNSYD001<br/>Phone"])
      N_TAB(["EXATABSYD001<br/>iPad"])
      N_LCD(["EXALCDSYD001<br/>LG Signage wallboard"])
      N_PRN(["EXAPRNSYD001<br/>Laser printer"])
      N_CAM(["EXACAMSYD001<br/>Camera"])
      N_CAM2(["EXACAMSYD002<br/>Camera reception"])
      N_COF>"☕ EXACOFSYD001<br/>Coffee machine"]
    end
    style NEW_SYD fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:SYD:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

## MEL — Melbourne ⚠️

**LAN:** `192.168.61.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSMEL001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (Australia) Pty Ltd · **Landline:** +61 3 9000 0xxx · **Mobile:** +61 400 901 2xxx

```mermaid
graph TD
    subgraph OLD_MEL ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      FWL{{"EXAFWLMEL001<br/>FortiGate 7.x<br/>.1"}}
      SW1{{"EXASWIMEL001<br/>Cisco 9300<br/>.250"}}
      SW2{{"EXASWIMEL002<br/>Cisco 2960<br/>.251"}}
      RAC[("EXARACMEL001<br/>HPE iLO5<br/>.2")]
      PVE[("EXAPVEMEL001<br/>Proxmox node 1<br/>.5")]
      DC[("🔴 EXADCSMEL001<br/>DC · Services stopped<br/>.10")]
      SRV[("EXASRVMEL001<br/>WS2022 File/Print<br/>.20")]
      SBC[("EXASBCMEL001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYMEL001<br/>Rudder Relay<br/>.12")]
      MBP(["EXAMBPMEL001<br/>MacBook Pro<br/>.40"])
      WKS(["EXAWKSMEL001<br/>Win11 Workstation<br/>.41"])
      PHN(["EXAPHNMEL001<br/>iOS Phone"])
      TAB(["EXATABMEL001<br/>iPad<br/>.60"])
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      LCD(["EXALCDMEL001<br/>Samsung Signage<br/>.70"])
      PRN(["EXAPRNMEL001<br/>HP LaserJet<br/>.80"])
      NAS[("EXANASMEL001<br/>Synology NAS DSM 7.x<br/>.81")]
      VPN(["🔗 WireGuard → BRK"])

      INET --> FWL --> SW1 & SW2
      SW1 --> PVE --> DC & SRV & SBC
      RAC -.->|"manages"| PVE
      SW2 --> MBP & WKS & PHN & TAB & WAP & CAM
      SW2 --> LCD & PRN & NAS
      FWL <-->|"WireGuard tunnel"| VPN

      SW1 --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_MEL fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:MEL:START
    subgraph NEW_MEL ["🆕 New Network (current)"]
      N_RTR{{"EXARTRMEL001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVMEL001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCMEL001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSMEL001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLMEL001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLMEL002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEMEL001<br/>PVE 1<br/>.5")]
      N_SRV[("EXASRVMEL001<br/>Local file and print server<br/>.20")]
      N_SWI{{"EXASWIMEL001<br/>Core switch<br/>.250"}}
      N_SWI2{{"EXASWIMEL002<br/>Access switch<br/>.251"}}
      N_MBP(["EXAMBPMEL001<br/>MacBook Pro"])
      N_WKS(["EXAWKSMEL001<br/>Workstation"])
      N_PHN(["EXAPHNMEL001<br/>Phone"])
      N_TAB(["EXATABMEL001<br/>iPad"])
      N_LCD(["EXALCDMEL001<br/>Signage display"])
      N_PRN(["EXAPRNMEL001<br/>LaserJet printer"])
      N_NAS[("EXANASMEL001<br/>NAS")]
    end
    style NEW_MEL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:MEL:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

---

## 🇳🇿 New Zealand

---

## AKL — Auckland ⚠️

**LAN:** `192.168.93.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
> ⚠️ `EXADCSAKL001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (New Zealand) Tapui · **Landline:** +64 9 300 0xxx · **Mobile:** +64 21 900 2xxx

```mermaid
graph TD
    subgraph OLD_AKL ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      FWL{{"EXAFWLAKL001<br/>FortiGate 7.x<br/>.1"}}
      SW1{{"EXASWIAKL001<br/>Cisco 9300<br/>.250"}}
      SW2{{"EXASWIAKL002<br/>Cisco 2960<br/>.251"}}
      RTR{{"EXARTRAKL001<br/>Cisco ISR 4331<br/>.254"}}
      RAC[("EXARACAKL001<br/>HPE iLO5<br/>.2")]
      PVE[("EXAPVEAKL001<br/>Proxmox node 1<br/>.5")]
      DC[("🔴 EXADCSAKL001<br/>DC · Services stopped<br/>.10")]
      SRV[("EXASRVAKL001<br/>WS2022 Local Server<br/>.20")]
      SBC[("EXASBCAKL001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYAKL001<br/>Rudder Relay<br/>.12")]
      WKS(["EXAWKSAKL001<br/>Win11 Workstation<br/>.40"])
      MBP(["EXAMBPAKL001<br/>MacBook Pro<br/>.41"])
      PHN(["EXAPHNAKL001<br/>Android Phone"])
      TAB(["EXATABAKL001<br/>iPad<br/>.60"])
      WAP1(("EXAWAPAKL001<br/>Ubiquiti UniFi"))
      WAP2(("EXAWAPAKL002<br/>Ubiquiti UniFi"))
      CAM(["EXACAMAKL001<br/>Axis Camera<br/>.82"])
      LCD(["EXALCDAKL001<br/>Samsung Signage<br/>.70"])
      PRN(["EXAPRNAKL001<br/>HP LaserJet<br/>.80"])
      COF>"EXACOFAKL001<br/>Smart Coffee Machine<br/>.83"]
      VPN(["🔗 WireGuard → BRK"])

      INET --> RTR --> FWL --> SW1 & SW2
      SW1 --> PVE --> DC & SRV & SBC
      RAC -.->|"manages"| PVE
      SW2 --> WKS & MBP & PHN & TAB & WAP1 & WAP2
      SW2 --> CAM & LCD & PRN & COF
      FWL <-->|"WireGuard tunnel"| VPN

      SW1 --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_AKL fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:AKL:START
    subgraph NEW_AKL ["🆕 New Network (current)"]
      N_RTR{{"EXARTRAKL001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVAKL001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCAKL001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSAKL001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLAKL001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLAKL002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEAKL001<br/>PVE 1<br/>.5")]
      N_SRV[("EXASRVAKL001<br/>Local server<br/>.20")]
      N_SWI{{"EXASWIAKL001<br/>Core switch<br/>.250"}}
      N_SWI2{{"EXASWIAKL002<br/>Access switch<br/>.251"}}
      N_WKS(["EXAWKSAKL001<br/>Workstation"])
      N_MBP(["EXAMBPAKL001<br/>MacBook Pro"])
      N_PHN(["EXAPHNAKL001<br/>Phone"])
      N_TAB(["EXATABAKL001<br/>iPad"])
      N_LCD(["EXALCDAKL001<br/>Signage display"])
      N_PRN(["EXAPRNAKL001<br/>LaserJet printer"])
      N_CAM(["EXACAMAKL001<br/>Camera"])
      N_COF>"☕ EXACOFAKL001<br/>Coffee machine"]
    end
    style NEW_AKL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:AKL:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

*Example Music Limited — Internal Infrastructure Documentation*   *Do not distribute outside the organisation*cloud
