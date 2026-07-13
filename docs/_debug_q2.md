# Mermaid render bisection — Q2

Throwaway debug file, sites: BIR, MCR, LIV, NEW, SHE, HAL, HUL, COV, CPH, ODE, KGE, FAX, KOR, AAR, FRE

---

## BIR — Birmingham

**LAN:** `192.168.121.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 121 496 0xxx · **Mobile:** +44 7700 900 2xxx

```mermaid
graph TD
    subgraph OLD_BIR ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      FWL{{"EXAFWLBIR001<br/>Palo Alto PAN-OS<br/>.1"}}
      SW1{{"EXASWIBIR001<br/>Cisco 9300<br/>.250"}}
      SW2{{"EXASWIBIR002<br/>Access Switch<br/>.251"}}
      RTR{{"EXARTRBIR001<br/>Cisco ISR 4331<br/>.254"}}
      RAC[("EXARACBIR001<br/>Dell DRAC<br/>.2")]
      PVE[("EXAPVEBIR001<br/>Proxmox node 1<br/>.5")]
      DC1[("EXADCRBIR001<br/>DC primary<br/>.10")]
      DC2[("EXADCRBIR002<br/>DC secondary<br/>.11")]
      SRV[("EXASRVBIR001<br/>Rocky Linux · Oracle DB<br/>.20")]
      SBC[("EXASBCBIR001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYBIR001<br/>Rudder Relay<br/>.12")]
      MBP(["EXAMBPBIR001<br/>MacBook Pro<br/>.41"])
      TAB(["EXATABBIR001<br/>Samsung Galaxy Tab<br/>.61"])
      PHN(["EXAPHNBIR001<br/>Samsung S25 Ultra"])
      WAP["WAPs x2<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      MOO>"EXAMOOBIR001<br/>Moog One Synthesizer<br/>.70"]
      LIN>"EXALINBIR001<br/>LinnDrum LM-2<br/>.71"]
      FCL>"EXAFCLBIR001<br/>Fairlight CMI IIx<br/>.72"]
      AST>"EXAASTBIR001<br/>Atari ST · MIDI<br/>.73"]
      PAY>"EXAPAYBIR001<br/>GPO Kiosk No.6 Payphone<br/>.74"]
      LCD(["EXALCDBIR001<br/>NEC PlasmaSync NOC Display<br/>.75"])
      VPN(["🔗 WireGuard → FAL"])

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
      N_RTR{{"EXARTRBIR001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVBIR001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCBIR001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSBIR001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLBIR001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLBIR002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEBIR001<br/>PVE 1<br/>.5")]
      N_SRV[("EXASRVBIR001<br/>Oracle DB<br/>.20")]
      N_MOO>"🎹 EXAMOOBIR001<br/>Moog synth<br/>.70"]
      N_LIN>"🥁 EXALINBIR001<br/>Drum machine<br/>.71"]
      N_FCL>"🎹 EXAFCLBIR001<br/>Fairlight CMI<br/>.72"]
      N_AST>"🕹️ EXAASTBIR001<br/>Atari ST<br/>.73"]
      N_PAY>"☎️ EXAPAYBIR001<br/>Payphone<br/>.74"]
      N_LCD(["EXALCDBIR001<br/>NOC display<br/>.75"])
      N_SWI{{"EXASWIBIR001<br/>Core switch<br/>.250"}}
      N_SWI2{{"EXASWIBIR002<br/>Access switch<br/>.251"}}
      N_MBP(["EXAMBPBIR001<br/>MacBook"])
      N_TAB(["EXATABBIR001<br/>Galaxy Tab"])
      N_PHN(["EXAPHNBIR001<br/>Samsung S25"])
    end
    style NEW_BIR fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:BIR:END
```

---

## MCR — Manchester

**LAN:** `192.168.161.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 161 715 xxxx · **Mobile:** +44 770 090 6xxx

```mermaid
graph TD
    subgraph OLD_MCR ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      SW{{"EXASWIMCR001<br/>Cisco 9300<br/>.250"}}
      RAC[("EXARACMCR001<br/>HPE iLO5<br/>.2")]
      PVE[("EXAPVEMCR001<br/>Proxmox node 1<br/>.5")]
      DC1[("EXADCRMCR001<br/>DC PDC · RID/Infra Master<br/>.10")]
      DC2[("EXADCSMCR002<br/>DC secondary<br/>.11")]
      SBC[("EXASBCMCR001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYMCR001<br/>Rudder Relay<br/>.12")]
      LAP1(["EXALAPMCR001<br/>Win11 Laptop<br/>.19"])
      LAP2(["EXALAPMCR002<br/>Win11 Laptop<br/>.150"])
      WKS1(["EXAWKSMCR001<br/>Front Desk WKS<br/>.152"])
      WKS2(["EXAWKSMCR002<br/>Finance WKS<br/>.153"])
      PRN(["EXAPRNMCR001<br/>Network Printer<br/>.16"])
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → FAL"])

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
      N_RTR{{"EXARTRMCR001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVMCR001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCMCR001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSMCR001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLMCR001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLMCR002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEMCR001<br/>PVE 1<br/>.5")]
      N_SWI{{"EXASWIMCR001<br/>Distribution switch<br/>.250"}}
      N_LAP(["EXALAPMCR001<br/>Laptop"])
      N_LAP2(["EXALAPMCR002<br/>Laptop"])
      N_WKS(["EXAWKSMCR001<br/>Desktop"])
      N_WKS2(["EXAWKSMCR002<br/>Desktop"])
      N_PRN(["EXAPRNMCR001<br/>Printer"])
    end
    style NEW_MCR fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:MCR:END
```

---

## LIV — Liverpool

**LAN:** `192.168.151.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 151 496 0xxx · **Mobile:** +44 770 090 5xxx

```mermaid
graph TD
    subgraph OLD_LIV ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      SW{{"EXASWILIV001<br/>Cisco 9200<br/>.250"}}
      RAC[("EXARACLIV001<br/>HPE iLO5<br/>.2")]
      PVE[("EXAPVELIV001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCRLIV001<br/>DC · WS2025<br/>.10")]
      SBC[("EXASBCLIV001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYLIV001<br/>Rudder Relay<br/>.12")]
      SRV[("EXASVRLIV001<br/>WS2022 File Server<br/>.10")]
      MBP(["EXAMBPLIV001<br/>MacBook Pro · macOS Tahoe<br/>.150"])
      MAC(["EXAMACLIV001<br/>iMac ⚠️ disabled<br/>.152"])
      RDR[("EXARDRLIV002<br/>HID Signo Badge Reader<br/>.16")]
      BPS(["EXABPSLIV001<br/>Badge Programming WKS<br/>.17"])
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → FAL"])

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
      N_RTR{{"EXARTRLIV001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVLIV001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCLIV001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSLIV001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLLIV001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLLIV002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVELIV001<br/>PVE 1<br/>.5")]
      N_SWI{{"EXASWILIV001<br/>Core switch<br/>.250"}}
      N_SVR[("EXASVRLIV001<br/>File server")]
      N_MBP(["EXAMBPLIV001<br/>MacBook Pro"])
      N_MAC(["EXAMACLIV001<br/>iMac DISABLED"])
      N_RDR[("EXARDRLIV002<br/>HID Signo badge reader")]
      N_BPS(["EXABPSLIV001<br/>Badge programming workstation"])
    end
    style NEW_LIV fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:LIV:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class MAC warn
```

---

## NEW — Newcastle

**LAN:** `192.168.191.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 191 496 0xxx · **Mobile:** +44 770 090 9xxx

```mermaid
graph TD
    subgraph OLD_NEW ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      SW{{"EXASWINEW001<br/>TP-Link JetStream<br/>.250"}}
      RAC[("EXARACNEW001<br/>Dell iDRAC9<br/>.2")]
      PVE[("EXAPVENEW001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCRNEW001<br/>DC<br/>.10")]
      SBC[("EXASBCNEW001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYNEW001<br/>Rudder Relay<br/>.12")]
      SRV[("EXASRVNEW001<br/>WS2022 File/Print Server<br/>.21")]
      WKS(["⚠️ EXAWKSNEW099<br/>Win11 WKS · LAPS expired<br/>.161"])
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → FAL"])

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
      N_RTR{{"EXARTRNEW001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVNEW001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCNEW001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSNEW001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLNEW001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLNEW002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVENEW001<br/>PVE 1<br/>.5")]
      N_SWI{{"EXASWINEW001<br/>Access switch<br/>.250"}}
      N_SRV[("EXASRVNEW001<br/>File/print server")]
      N_WKS(["EXAWKSNEW099<br/>LAPS password expired"])
    end
    style NEW_NEW fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:NEW:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class WKS warn
```

---

## SHE — Sheffield

**LAN:** `192.168.114.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 114 250 0xxx · **Mobile:** +44 7700 905 2xxx

```mermaid
graph TD
    subgraph OLD_SHE ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACSHE001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVESHE001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSSHE001<br/>DC<br/>.10")]
      SBC[("EXASBCSHE001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYSHE001<br/>Rudder Relay<br/>.12")]
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      EP["Endpoints TODO"]
      VPN(["🔗 WireGuard → FAL"])

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
      N_RTR{{"EXARTRSHE001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVSHE001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCSHE001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSSHE001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLSHE001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLSHE002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVESHE001<br/>PVE 1<br/>.5")]
    end
    style NEW_SHE fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:SHE:END
```

---

## HAL — Halifax

**LAN:** `192.168.142.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 1422 200 0xxx · **Mobile:** +44 7700 904 2xxx

```mermaid
graph TD
    subgraph OLD_HAL ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACHAL001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEHAL001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSHAL001<br/>DC<br/>.10")]
      SBC[("EXASBCHAL001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYHAL001<br/>Rudder Relay<br/>.12")]
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      EP["Endpoints TODO"]
      VPN(["🔗 WireGuard → FAL"])

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
      N_RTR{{"EXARTRHAL001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVHAL001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCHAL001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSHAL001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLHAL001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLHAL002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEHAL001<br/>PVE 1<br/>.5")]
    end
    style NEW_HAL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:HAL:END
```

---

## HUL — Hull

**LAN:** `192.168.148.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 1482 300 0xxx · **Mobile:** +44 7700 902 2xxx

```mermaid
graph TD
    subgraph OLD_HUL ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACHUL001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEHUL001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSHUL001<br/>DC<br/>.10")]
      SBC[("EXASBCHUL001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYHUL001<br/>Rudder Relay<br/>.12")]
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      EP["Endpoints TODO"]
      VPN(["🔗 WireGuard → FAL"])

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
      N_RTR{{"EXARTRHUL001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVHUL001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCHUL001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSHUL001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLHUL001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLHUL002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEHUL001<br/>PVE 1<br/>.5")]
    end
    style NEW_HUL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:HUL:END
```

---

## COV — Coventry

**LAN:** `192.168.247.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
*Note: WAP/RTR-only site — minimal infrastructure.*  
**Entity:** Example Music (England) Ltd · **Landline:** +44 247 765 0xxx · **Mobile:** +44 7700 901 2xxx

```mermaid
graph TD
    subgraph OLD_COV ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RTR{{"EXARTRCOV001<br/>Cisco ISR 4331<br/>.254"}}
      RAC[("EXARACCOV001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVECOV001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSCOV001<br/>DC<br/>.10")]
      SBC[("EXASBCCOV001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYCOV001<br/>Rudder Relay<br/>.12")]
      WAP["WAPs x2<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → FAL"])

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
      N_RTR{{"EXARTRCOV001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVCOV001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCCOV001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSCOV001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLCOV001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLCOV002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVECOV001<br/>PVE 1<br/>.5")]
    end
    style NEW_COV fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:COV:END
```

---

---

## 🇩🇰 Danmark

---

## CPH — København

**LAN:** `192.168.231.0/24` · **Domain:** `example.com` / `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_CPH ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      SW{{"EXASWICPH001<br/>TP-Link JetStream<br/>.250"}}
      RTR{{"EXARTRCPH001<br/>Cisco ISR 4331<br/>.254"}}
      RAC[("EXARACCPH001<br/>Dell iDRAC9<br/>.2")]
      PVE[("EXAPVECPH001<br/>Proxmox node 1<br/>.5")]
      DC1[("EXADCSCPH001<br/>DC · example.com<br/>.10")]
      DC2[("EXADCSCPH002<br/>DC · example.net<br/>.11")]
      SBC[("EXASBCCPH001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYCPH001<br/>Rudder Relay<br/>.12")]
      NTP>"EXACLKCPH001<br/>Meinberg LANTIME M300<br/>NTP Clock · .18"]
      TV(["EXATVSCPH001<br/>Bella Kronik 42X<br/>DR/TV2 · .17"])
      WAP["WAPs x3<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → ODE"])

      INET --> RTR --> SW
      SW --> PVE --> DC1 & DC2 & SBC
      RAC -.->|"manages"| PVE
      SW --> NTP & TV & WAP & CAM
      RTR <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_CPH fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:CPH:START
    subgraph NEW_CPH ["🆕 New Network (current)"]
      N_RTR{{"EXARTRCPH001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVCPH001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCCPH001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSCPH001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLCPH001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLCPH002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVECPH001<br/>PVE 1<br/>.5")]
      N_CLK>"⏰ EXACLKCPH001<br/>NTP clock<br/>.18"]
      N_TVS(["EXATVSCPH001<br/>Display<br/>.17"])
      N_SWI{{"EXASWICPH001<br/>Office switch<br/>.250"}}
    end
    style NEW_CPH fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:CPH:END
```

---

## ODE — Odense *(EU Hub)* ⭐

**LAN:** `192.168.126.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (EU hub) · **VPN parent:** CLD (EU backup)  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_ODE ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      FWL{{"EXAFWLODE001<br/>Cisco ASA 5506-X<br/>.1"}}

      subgraph BMC ["BMC Pool"]
          RAC1[("EXARACODE001<br/>BMC node 1<br/>.2")]
          RAC2[("EXARACODE002<br/>BMC node 2<br/>.3")]
          RAC3[("EXARACODE003<br/>BMC node 3<br/>.4")]
      end

      subgraph PVE ["Proxmox Cluster (3-node)"]
          PVE1[("EXAPVEODE001<br/>Proxmox node 1<br/>.5")]
          PVE2[("EXAPVEODE002<br/>Proxmox node 2<br/>.6")]
          PVE3[("EXAPVEODE003<br/>Proxmox node 3<br/>.7")]
      end

      DC1[("EXADCSODE001<br/>DC PDC · RID/Infra Master<br/>.10")]
      DC2[("EXADCSODE002<br/>DC secondary<br/>.11")]
      SBC[("EXASBCODE001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYODE001<br/>Rudder Relay<br/>.12")]
      MAC(["EXAMACODE001<br/>iMac · macOS Tahoe<br/>.150"])
      MBP(["EXAMBPODE002<br/>MacBook Pro<br/>.151"])
      JKB>"EXAMUSODE001<br/>Pureline 128V Jukebox<br/>.60"]
      WAP["WAPs x2<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN_CLD(["🔗 WireGuard ← CLD<br/>EU backup"])
      VPN_EU(["🔗 WireGuard → EU spokes<br/>CPH/KGE/FAX/KOR/AAR/FRE/BON/BER<br/>DRS/DUS/MUN/GOT/OSL/AMS/MIL/VIE/BRT"])

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
      RRY -. "→ EXARDRCLD001" .-> VPN_CLD
    end
    style OLD_ODE fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:ODE:START
    subgraph NEW_ODE ["🆕 New Network (current)"]
      N_RTR{{"EXARTRODE001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVODE001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCODE001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSODE001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLODE001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLODE002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEODE001<br/>PVE 1<br/>.5")]
      N_MUS>"💿 EXAMUSODE001<br/>Jukebox<br/>.60"]
      N_MAC(["EXAMACODE001<br/>iMac"])
      N_MBP(["EXAMBPODE002<br/>MacBook Pro"])
    end
    style NEW_ODE fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:ODE:END
```

---

## KGE — Køge ⚠️

**LAN:** `192.168.65.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
> ⚠️ DC out of sync 27 days · WS2016 EOL · disk space low — rebuild required  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_KGE ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACKGE001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEKGE001<br/>Proxmox node 1<br/>.5")]
      DC[("⚠️ EXADCSKGE001<br/>DC · WS2016 EOL<br/>OOS 27d · .10")]
      SBC[("EXASBCKGE001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYKGE001<br/>Rudder Relay<br/>.12")]
      WAP(("EXAWAPKGE001<br/>Ubiquiti UniFi U6-Pro"))
      CAM["CAMs TODO"]
      PRN(["EXAPRNKGE001<br/>HP LaserJet MFP M528<br/>.16"])
      VPN(["🔗 WireGuard → ODE"])

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM & PRN
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_KGE fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:KGE:START
    subgraph NEW_KGE ["🆕 New Network (current)"]
      N_RTR{{"EXARTRKGE001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVKGE001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCKGE001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSKGE001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLKGE001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLKGE002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEKGE001<br/>PVE 1<br/>.5")]
      N_PRN(["EXAPRNKGE001<br/>Printer"])
    end
    style NEW_KGE fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:KGE:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

## FAX — Faxe

**LAN:** `192.168.246.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_FAX ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RTR{{"EXARTRFAX001<br/>Cisco ISR 4331<br/>.254"}}
      RAC[("EXARACFAX001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEFAX001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSFAX001<br/>DC<br/>.10")]
      SBC[("EXASBCFAX001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYFAX001<br/>Rudder Relay<br/>.12")]
      WAP["WAPs x2<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → ODE"])

      INET --> RTR --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      RTR --> WAP & CAM
      RTR <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_FAX fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:FAX:START
    subgraph NEW_FAX ["🆕 New Network (current)"]
      N_RTR{{"EXARTRFAX001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVFAX001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCFAX001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSFAX001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLFAX001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLFAX002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEFAX001<br/>PVE 1<br/>.5")]
    end
    style NEW_FAX fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:FAX:END
```

---

## KOR — Korsør

**LAN:** `192.168.238.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_KOR ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACKOR001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEKOR001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSKOR001<br/>DC<br/>.10")]
      SBC[("EXASBCKOR001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYKOR001<br/>Rudder Relay<br/>.12")]
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → ODE"])

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_KOR fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:KOR:START
    subgraph NEW_KOR ["🆕 New Network (current)"]
      N_RTR{{"EXARTRKOR001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVKOR001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCKOR001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSKOR001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLKOR001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLKOR002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEKOR001<br/>PVE 1<br/>.5")]
    end
    style NEW_KOR fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:KOR:END
```

---

## AAR — Aarhus

**LAN:** `192.168.86.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_AAR ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACAAR001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEAAR001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSAAR001<br/>DC<br/>.10")]
      SBC[("EXASBCAAR001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYAAR001<br/>Rudder Relay<br/>.12")]
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → ODE"])

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_AAR fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:AAR:START
    subgraph NEW_AAR ["🆕 New Network (current)"]
      N_RTR{{"EXARTRAAR001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVAAR001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCAAR001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSAAR001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLAAR001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLAAR002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEAAR001<br/>PVE 1<br/>.5")]
    end
    style NEW_AAR fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:AAR:END
```

---

## FRE — Fredericia

**LAN:** `192.168.75.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 75 xx xx xx · **Mobile:** +45 2x xx xx xx

```mermaid
graph TD
    subgraph OLD_FRE ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACFRE001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEFRE001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSFRE001<br/>DC<br/>.10")]
      SBC[("EXASBCFRE001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYFRE001<br/>Rudder Relay<br/>.12")]
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → ODE"])

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARDRCLD001" .-> VPN
    end
    style OLD_FRE fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:FRE:START
    subgraph NEW_FRE ["🆕 New Network (current)"]
      N_RTR{{"EXARTRFRE001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVFRE001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCFRE001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSFRE001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLFRE001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLFRE002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEFRE001<br/>PVE 1<br/>.5")]
    end
    style NEW_FRE fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:FRE:END
```

---
