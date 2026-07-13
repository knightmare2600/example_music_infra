# Mermaid render bisection — Q1

Throwaway debug file, sites: CLD, FAL, EDI, GLA, CLY, DUN, PER, ABD, LND

---

## ☁️  — Cloud / Provisioning

**vRACK (`VRK`):** `192.168.139.0/24` · **CLD LAN:** `192.168.69.0/24` · **WireGuard VPN:** `10.0.139.0/24`
**Role:** WireGuard hub — routes to all sites. Central PBX, Ansible, Rudder, WAC.
CLD's own LAN is `192.168.69.0/24` — the vRACK (`192.168.139.0/24`) is a separate site code, `VRK`.  
**Entity:** Example Music Limited · **Landline:** N/A · **Mobile:** N/A

```mermaid
graph TD
    subgraph OLD_CLD ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      FWLCLD{{"EXAFWLVRK001<br/>Firewall / WireGuard Hub<br/>192.168.139.1"}}
      DNS[("EXADNSVRK001<br/>DNS / BIND9 Server<br/>192.168.139.8")]
      PRV[("EXAPRVVRK001<br/>Provisioning Server<br/>192.168.139.50")]
      RUD[("EXARDRCLD001<br/>Rudder Server<br/>192.168.69.12")]
      WAC[("EXASVRCLD002<br/>Windows Admin Centre<br/>192.168.69.20")]
      PBX[("EXAPBXCLD001<br/>3CX Central PBX<br/>192.168.69.48")]
      ANS[("EXAANSCLD001<br/>Ansible Control Node<br/>192.168.69.9")]

      VPN_FAL(["🔗 WireGuard → FAL primary"])
      VPN_ODE(["🔗 WireGuard → ODE EU backup"])
      VPN_BRK(["🔗 WireGuard → BRK NA/APAC backup"])

      INET --> FWLCLD
      FWLCLD --> DNS
      FWLCLD --> RUD
      FWLCLD --> WAC
      FWLCLD --> PBX
      FWLCLD --> PRV
      FWLCLD --> ANS
      FWLCLD --> VPN_FAL
      FWLCLD --> VPN_ODE
      FWLCLD --> VPN_BRK

    end
    style OLD_CLD fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:CLD:START
    subgraph NEW_CLD ["🆕 New Network (current)"]
      N_PRV[("EXAPRVCLD001<br/>PRV<br/>.15")]
      N_DCS[("EXADCSCLD001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLCLD001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLCLD002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVECLD001<br/>PVE 1<br/>.5")]
      N_ANS[("EXAANSCLD001<br/>Ansible control node<br/>.9")]
      N_RDR[("EXARDRCLD001<br/>Rudder configuration management server<br/>.12")]
      N_SVR[("EXASVRCLD002<br/>Windows Admin Centre<br/>.20")]
      N_PBX[("EXAPBXCLD001<br/>3CX PBX<br/>.48")]
      N_UFC[("EXAUFCCLD001<br/>UniFi Network Controller<br/>.82")]
    end
    style NEW_CLD fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:CLD:END
```

---

---

## 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland

---

## FAL — Falkirk *(Head Office)* ⭐

**Address:** Brockville Stadium, Hope Street, Falkirk  
**LAN:** `192.168.76.0/24` · **VPN:** `10.0.76.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (hub) · **VPN parent:** CLD (primary head node)  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 1324 500 0xxx · **Mobile:** +44 7700 903 2xxx

```mermaid
graph TD
    subgraph OLD_FAL ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RTR{{"EXARTRFAL001<br/>Cisco ISR 4331<br/>.254"}}
      FWL{{"EXAFWLFAL001<br/>FortiOS<br/>.1"}}
      SW1{{"EXASWIFAL001<br/>Cisco 9300<br/>.250"}}
      SW2{{"EXASWIFAL002<br/>Cisco 9300<br/>.251"}}

      subgraph BMC ["BMC Pool"]
          RAC1[("EXARACFAL001<br/>Dell iDRAC9<br/>.2")]
          RAC2[("EXARACFAL002<br/>Dell iDRAC9<br/>.3")]
          RAC3[("EXARACFAL003<br/>Dell iDRAC9<br/>.4")]
      end

      subgraph PVE ["Proxmox Cluster (3-node)"]
          PVE1[("EXAPVEFAL001<br/>Proxmox node 1<br/>.5")]
          PVE2[("EXAPVEFAL002<br/>Proxmox node 2<br/>.6")]
          PVE3[("EXAPVEFAL003<br/>Proxmox node 3<br/>.7")]
      end

      subgraph DC ["Domain Controllers"]
          DC1[("EXADCSFAL001<br/>DC · PDC Emulator<br/>.10")]
          DC2[("EXADCSFAL002<br/>DC secondary<br/>.11")]
      end

      subgraph INFRA ["Infrastructure"]
          SBC[("EXASBCFAL001<br/>3CX SBC → CLD PBX<br/>.48")]
          RRY[("EXARRYFAL001<br/>Rudder Relay<br/>.12")]
          NAS[("EXANASFAL001<br/>FreeNAS 13.0-U6<br/>.32")]
          TAR[("EXATARFAL001<br/>Tape Archiver<br/>.33")]
      end

      subgraph ENDPOINTS ["Endpoints"]
          WKS1(["EXAWKSFAL001<br/>Mixing Desk WKS<br/>.100"])
          WKS2(["EXAWKSFAL002<br/>Reel-to-Reel WKS<br/>.101"])
          WKS3(["EXAWKSFAL003<br/>Shared Editing WKS<br/>.102"])
          LAP(["EXALAPFAL001<br/>Production Laptop<br/>.103"])
          SUR(["EXASURFAL001<br/>Microsoft Surface<br/>.104"])
          PHN(["EXAPHNFAL001-003<br/>Staff Phones"])
          PHN2(["EXAPHNFAL006-007<br/>Yealink T58A"])
          TAB(["EXATABFAL001<br/>Tablet"])
      end

      subgraph WAP_CAM ["Wireless & Security"]
          WAP["WAPs x6<br/>Ubiquiti UniFi U6-Pro<br/>.5-.10"]
          CAM1(["EXACAMFAL001<br/>Axis · Front entrance<br/>.70"])
          CAM2(["EXACAMFAL002<br/>Axis · Studio hallway<br/>.71"])
          CAM3(["EXACAMFAL003<br/>Axis · Car park<br/>.72"])
          CAM4(["EXACAMFAL004<br/>Axis · Loading bay<br/>.73"])
          RDR[("EXARDRFAL001<br/>HID Signo Badge Reader<br/>.16")]
      end

      subgraph SITE ["Site-Specific Equipment"]
          LCD(["EXALCDFAL001<br/>Samsung Tizen Display<br/>.50"])
          VCU(["EXAVCUFAL001<br/>Poly Studio X70<br/>.51"])
          JKB>"EXAMUSFAL001<br/>Pureline 128V Jukebox<br/>.67"]
          PAY>"EXAPAYFAL001<br/>GPO Kiosk No.6 Payphone<br/>.95"]
          COF>"EXATEAFAL001<br/>Smart Coffee Machine<br/>.61"]
          VND1>"EXADONFAL001<br/>Tim Hortons Vending<br/>.62"]
          VND2>"EXAVNDFAL002<br/>Irn-Bru Machine<br/>.63"]
          VND3>"EXAVNDFAL003<br/>McCowans Dispenser<br/>.64"]
          VND4>"EXAVNDFAL004<br/>Mrs Tily Dispenser<br/>.65"]
          VND5>"EXAVNDFAL005<br/>¼lb Confectionery<br/>.66"]
          PMP>"EXAPMPFAL001<br/>Networked Petrol Pump<br/>.60"]
          CLK>"EXACLKFAL001<br/>NTP Clock<br/>.80"]
      end

      VPN_CLD(["🔗 WireGuard ← CLD<br/>10.0.76.0/24"])

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
      N_RTR{{"EXARTRFAL001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVFAL001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCFAL001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSFAL001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLFAL001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLFAL002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEFAL001<br/>PVE 1<br/>.5")]
      N_RDR[("EXARDRFAL001<br/>HID Signo badge reader<br/>.16")]
      N_SRV[("EXASRVFAL001<br/>Reserved<br/>.20")]
      N_NAS[("EXANASFAL001<br/>Primary storage<br/>.32")]
      N_TAR[("💽 EXATARFAL001<br/>Legacy tape archive<br/>.33")]
      N_LCD(["EXALCDFAL001<br/>Reception display<br/>.50"])
      N_VCU(["🎧 EXAVCUFAL001<br/>Video conferencing<br/>.51"])
      N_PMP>"⛽ EXAPMPFAL001<br/>Networked petrol pump<br/>.60"]
      N_TEA>"🫖 EXATEAFAL001<br/>Smart coffee machine<br/>.61"]
      N_DON>"🍩 EXADONFAL001<br/>Donut vending<br/>.62"]
      N_VND>"🍫 EXAVNDFAL002<br/>Vending machine<br/>.63"]
      N_VND2>"🍫 EXAVNDFAL003<br/>Vending machine<br/>.64"]
      N_VND3>"🍫 EXAVNDFAL004<br/>Vending machine<br/>.65"]
      N_VND4>"🍫 EXAVNDFAL005<br/>Confectionery machine<br/>.66"]
      N_MUS>"💿 EXAMUSFAL001<br/>Jukebox<br/>.67"]
      N_CAM(["EXACAMFAL001<br/>Camera front entrance<br/>.70"])
      N_CAM2(["EXACAMFAL002<br/>Camera studio hallway<br/>.71"])
      N_CAM3(["EXACAMFAL003<br/>Camera car park<br/>.72"])
      N_CAM4(["EXACAMFAL004<br/>Camera rear loading bay<br/>.73"])
      N_CLK>"⏰ EXACLKFAL001<br/>Embedded NTP clock<br/>.80"]
      N_PAY>"☎️ EXAPAYFAL001<br/>GPO Kiosk No.6 payphone<br/>.95"]
      N_WKS(["EXAWKSFAL001<br/>Workstation Analog Mixing Desk v1<br/>.100"])
      N_WKS2(["EXAWKSFAL003<br/>Workstation shared editing<br/>.102"])
      N_LAP(["EXALAPFAL001<br/>Production laptop<br/>.103"])
      N_SUR(["EXASURFAL001<br/>Microsoft Surface<br/>.104"])
      N_SWI{{"EXASWIFAL001<br/>Core switch 1<br/>.250"}}
      N_SWI2{{"EXASWIFAL002<br/>Core switch 2<br/>.251"}}
      N_PHN(["EXAPHNFAL001<br/>Phone 1"])
      N_PHN2(["EXAPHNFAL002<br/>Phone 2"])
      N_PHN3(["EXAPHNFAL003<br/>Phone 3"])
      N_PHN4(["EXAPHNFAL006<br/>Phone 6"])
      N_PHN5(["EXAPHNFAL007<br/>Phone 7"])
      N_TAB(["EXATABFAL001<br/>Tablet"])
      N_TTY>"🖥️ EXATTYFAL001<br/>VT320 serial terminal"]
      N_BUS>"🚌 EXABUSFAL001<br/>Tour bus 1"]
      N_BUS2>"🚌 EXABUSFAL002<br/>Tour bus 2"]
      N_BUS3>"🚌 EXABUSFAL003<br/>Tour bus 3"]
      N_CAR>"🚗 EXACARFAL001<br/>Car 1"]
      N_CAR2>"🚗 EXACARFAL002<br/>Car 2"]
      N_CAR3>"🚗 EXACARFAL003<br/>Car 3"]
      N_CAR4>"🚗 EXACARFAL004<br/>Car 4"]
      N_CAR5>"🚗 EXACARFAL005<br/>Car 5"]
      N_TRK>"🚚 EXATRKFAL001<br/>Truck 1"]
      N_TRK2>"🚚 EXATRKFAL002<br/>Truck 2"]
      N_TRK3>"🚚 EXATRKFAL003<br/>Truck 3"]
      N_TRK4>"🚚 EXATRKFAL004<br/>Truck 4"]
      N_TRK5>"🚚 EXATRKFAL005<br/>Truck 5"]
      N_JET>"✈️ EXAJETFAL001<br/>Jet 1"]
      N_JET2>"✈️ EXAJETFAL002<br/>Jet 2"]
      N_JET3>"✈️ EXAJETFAL003<br/>Jet 3"]
      N_JET4>"✈️ EXAJETFAL004<br/>Jet 4"]
      N_JET5>"✈️ EXAJETFAL005<br/>Jet 5"]
    end
    style NEW_FAL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:FAL:END
```

---

## EDI — Edinburgh ⚠️

**LAN:** `192.168.131.0/24` · **Domain:** `example.org` / `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
> ⚠️ `EXADCSEDI003` — DFSR stopped, C: drive at 5% free. Immediate action required.  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 131 496 0xxx · **Mobile:** +44 770 090 3xxx

```mermaid
graph TD
    subgraph OLD_EDI ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RTR{{"EXARTREDI001<br/>Cisco ISR 4331<br/>.254"}}
      SW1{{"EXASWIEDI001<br/>Cisco 2960X<br/>.250"}}
      SW2{{"EXASWIEDI002<br/>Cisco 2960X<br/>.251"}}
      RAC[("EXARACEDI001<br/>Dell iDRAC9<br/>.2")]
      PVE[("EXAPVEEDI001<br/>Proxmox node 1<br/>.5")]
      DC[("⚠️ EXADCSEDI003<br/>DC · DFSR stopped<br/>C: 5% free · .11")]
      SBC[("EXASBCEDI001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYEDI001<br/>Rudder Relay<br/>.12")]
      WKS(["EXAWKSEDI001<br/>Workstation<br/>.150"])
      LAP(["EXALAPEDI098<br/>Pool Laptop<br/>.108"])
      WAP["WAPs x2<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      COF>"EXATEAEDI001<br/>Siemens EQ700 Coffee Machine<br/>.60"]
      VPN(["🔗 WireGuard → FAL"])

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
      N_RTR{{"EXARTREDI001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVEDI001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCEDI001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSEDI001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLEDI001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLEDI002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEEDI001<br/>PVE 1<br/>.5")]
      N_DCS2[("EXADCSEDI002<br/>DC secondary needs rebuild corrected to .12<br/>.12")]
      N_DCS3[("EXADCSEDI003<br/>DECOMMISSION PENDING corrected to .13<br/>.13")]
      N_WKS(["EXAWKSEDI001<br/>Shared desktop<br/>.150"])
      N_LAP(["EXALAPEDI098<br/>Pool laptop<br/>.108"])
      N_SWI{{"EXASWIEDI001<br/>Floor switch<br/>.250"}}
      N_SWI2{{"EXASWIEDI002<br/>48-port switch<br/>.251"}}
      N_TEA>"🫖 EXATEAEDI001<br/>Coffee machine<br/>.60"]
    end
    style NEW_EDI fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:EDI:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

## GLA — Glasgow

**LAN:** `192.168.141.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 141 496 01xx · **Mobile:** +44 770 009 4xxx

```mermaid
graph TD
    subgraph OLD_GLA ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      PVE[("EXAPVEGLA001<br/>Proxmox node 1<br/>.5")]
      RAC[("EXARACGLA001<br/>BMC node 1<br/>.2")]
      DC[("EXADCRGLA001<br/>DC · Schema/DN Master<br/>PDC Emulator · .10")]
      SBC[("EXASBCGLA001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYGLA001<br/>Rudder Relay<br/>.12")]
      WKS1(["EXAWKSGLA001<br/>Hot Desk WKS<br/>.150"])
      WKS2(["EXAWKSGLA002<br/>Hot Desk WKS<br/>.151"])
      LAP(["EXALAPGLA001<br/>Pool Laptop<br/>.152"])
      PRN(["EXAPRNGLA001<br/>HP LaserJet Pro<br/>.16"])
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → FAL"])

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
      N_RTR{{"EXARTRGLA001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVGLA001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCGLA001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSGLA001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLGLA001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLGLA002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEGLA001<br/>PVE 1<br/>.5")]
      N_PRN(["EXAPRNGLA001<br/>Main floor printer<br/>.16"])
      N_WKS(["EXAWKSGLA001<br/>Hot desk workstation<br/>.150"])
      N_WKS2(["EXAWKSGLA002<br/>Hot desk workstation<br/>.151"])
      N_LAP(["EXALAPGLA001<br/>Pool laptop<br/>.152"])
    end
    style NEW_GLA fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:GLA:END
```

---

## CLY — Clydebank

**LAN:** `192.168.41.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 141 496 00xx · **Mobile:** +44 770 090 5xxx

```mermaid
graph TD
    subgraph OLD_CLY ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      FWL{{"EXAFWLCLY001<br/>FortiOS 7.6.5<br/>.1"}}
      RTR{{"EXARTRCLY001<br/>Cisco ISR 4331<br/>.254"}}
      SW{{"EXASWICLY001<br/>Cisco 9300<br/>.250"}}
      RAC[("EXARACCLY001<br/>HPE iLO5<br/>.2")]
      PVE[("EXAPVECLY001<br/>Proxmox node 1<br/>.5")]
      DC1[("EXADCSCLY001<br/>DC primary<br/>.10")]
      DC2[("EXADCSCLY002<br/>DC secondary<br/>.11")]
      SRV[("EXASRVCLY001<br/>Rocky Linux · Oracle DB<br/>.20")]
      SBC[("EXASBCCLY001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYCLY001<br/>Rudder Relay<br/>.12")]
      SUR(["EXASURCLY001<br/>Microsoft Surface<br/>.51"])
      PHN(["EXAPHNCLY001<br/>iOS handset"])
      TAB(["EXASURCLY002<br/>Android Tablet"])
      WAP["WAPs x2<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → FAL"])

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
      N_RTR{{"EXARTRCLY001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVCLY001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCCLY001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSCLY001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLCLY001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLCLY002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVECLY001<br/>PVE 1<br/>.5")]
      N_SRV[("EXASRVCLY001<br/>Oracle DB server<br/>.20")]
      N_SWI{{"EXASWICLY001<br/>Core switch<br/>.250"}}
      N_SUR(["EXASURCLY001<br/>Surface"])
      N_PHN(["EXAPHNCLY001<br/>Phone"])
      N_SUR2(["EXASURCLY002<br/>Android tablet"])
    end
    style NEW_CLY fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:CLY:END
```

---

## DUN — Dundee

**LAN:** `192.168.138.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 163 249 60xx · **Mobile:** +44 770 090 82xx

```mermaid
graph TD
    subgraph OLD_DUN ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RTR{{"EXARTRDUN001<br/>Cisco ISR 4331<br/>.254"}}
      RAC[("EXARACDUN001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEDUN001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSDUN001<br/>DC<br/>.10")]
      SBC[("EXASBCDUN001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYDUN001<br/>Rudder Relay<br/>.12")]
      SUR1(["EXASURDUN001<br/>Surface<br/>.51"])
      SUR2(["EXASURDUN002<br/>Surface<br/>.52"])
      PHN1(["EXAPHNDUN001<br/>iOS Phone"])
      PHN2(["EXAPHNDUN002<br/>iOS Phone"])
      WAP["WAPs x2<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → FAL"])

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
      N_RTR{{"EXARTRDUN001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVDUN001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCDUN001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSDUN001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLDUN001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLDUN002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEDUN001<br/>PVE 1<br/>.5")]
      N_SUR(["EXASURDUN001<br/>Surface"])
      N_SUR2(["EXASURDUN002<br/>Surface"])
      N_PHN(["EXAPHNDUN001<br/>Phone"])
      N_PHN2(["EXAPHNDUN002<br/>Phone"])
    end
    style NEW_DUN fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:DUN:END
```

---

## PER — Perth

**LAN:** `192.168.173.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 173 849 60xx · **Mobile:** +44 770 0173 0xx

```mermaid
graph TD
    subgraph OLD_PER ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACPER001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEPER001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSPER001<br/>DC<br/>.10")]
      SBC[("EXASBCPER001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYPER001<br/>Rudder Relay<br/>.12")]
      NIX(["EXANIXPER001<br/>Solaris 11.5<br/>MIDI/Music Archive · .40"])
      NAS[("EXANASPER001<br/>Synology NAS<br/>.50")]
      MBP(["EXAMBPPER001<br/>MacBook Pro<br/>.70"])
      SUR(["EXASURPER001<br/>Surface<br/>.71"])
      PHN(["EXAPHNPER001-004<br/>Yealink T46G Phones<br/>.80"])
      PRN(["EXAPRNPER001<br/>HP MFP Printer<br/>.20"])
      VND>"EXAVNDPER001<br/>Scone Palace Vending Machine<br/>.60"]
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → FAL"])

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
      N_RTR{{"EXARTRPER001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVPER001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCPER001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSPER001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLPER001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLPER002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEPER001<br/>PVE 1<br/>.5")]
      N_NIX(["🐧 EXANIXPER001<br/>MIDI archive<br/>.40"])
      N_NAS[("EXANASPER001<br/>NAS<br/>.50")]
      N_MBP(["EXAMBPPER001<br/>MacBook"])
      N_SUR(["EXASURPER001<br/>Surface"])
      N_PHN(["EXAPHNPER001<br/>Phone 1"])
      N_PHN2(["EXAPHNPER002<br/>Phone 2"])
      N_PHN3(["EXAPHNPER003<br/>Phone 3"])
      N_PHN4(["EXAPHNPER004<br/>Phone 4"])
      N_PRN(["EXAPRNPER001<br/>Printer"])
      N_VND>"🍫 EXAVNDPER001<br/>Vending machine"]
    end
    style NEW_PER fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:PER:END
```

---

## ABD — Aberdeen

**LAN:** `192.168.224.0/24` · **Domain:** `example.org`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (Scotland) Ltd · **Landline:** +44 1224 496 0xxx · **Mobile:** +44 7700 900 2xxx

```mermaid
graph TD
    subgraph OLD_ABD ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      FWL{{"EXAFWLABD001<br/>Cisco ASA 5506-X<br/>.1"}}
      RTR{{"EXARTRABD001<br/>Cisco ISR 4331<br/>.254"}}
      RAC[("EXARACABD001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEABD001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSABD001<br/>DC<br/>.10")]
      SBC[("EXASBCABD001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYABD001<br/>Rudder Relay<br/>.12")]
      MBP1(["EXAMBPABD001<br/>MacBook<br/>.137"])
      MBP2(["EXAMBPABD002<br/>MacBook<br/>.124"])
      PHN1(["EXAPHNABD001<br/>Corporate iPhone"])
      PHN2(["EXAPHNABD002<br/>Corporate iPhone"])
      WAP["WAPs x2<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → FAL"])

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
      N_RTR{{"EXARTRABD001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVABD001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCABD001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSABD001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLABD001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLABD002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEABD001<br/>PVE 1<br/>.5")]
      N_MBP(["EXAMBPABD001<br/>MacBook"])
      N_MBP2(["EXAMBPABD002<br/>MacBook"])
      N_PHN(["EXAPHNABD001<br/>iPhone"])
      N_PHN2(["EXAPHNABD002<br/>iPhone"])
    end
    style NEW_ABD fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:ABD:END
```

---

---

## 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England

---

## LND — London

**LAN:** `192.168.20.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** FAL  
**Entity:** Example Music (England) Ltd · **Landline:** +44 207 496 0xxx · **Mobile:** +44 770 090 0xxx

```mermaid
graph TD
    subgraph OLD_LND ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      FWL{{"EXAFWLLND001<br/>Cisco ASA 5516-X<br/>.1"}}
      SW{{"EXASWILND001<br/>Cisco 9300<br/>.250"}}
      RTR{{"EXARTRLND001<br/>Cisco ISR 4331<br/>.254"}}
      RAC[("EXARACLND001<br/>Dell iDRAC9<br/>.2")]
      PVE[("EXAPVELND001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCRLND001<br/>DC · RID/Infra Master<br/>.10")]
      SBC[("EXASBCLND001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYLND001<br/>Rudder Relay<br/>.12")]
      WKS(["EXAWKSLND001<br/>Hot Desk WKS<br/>.150"])
      PRN1(["EXAPRNLND001<br/>Xerox WorkCentre<br/>.16"])
      PRN2(["EXAPRNLND002<br/>ProCAT Steno Writer<br/>Court Device"])
      RAD>"EXARADLND001<br/>BBC Office Radio Mk II<br/>.80"]
      MIC>"EXAMICLND001<br/>Shure SM7 Microphone<br/>Dante Audio · .81"]
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → FAL"])

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
      N_RTR{{"EXARTRLND001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVLND001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCLND001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSLND001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLLND001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLLND002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVELND001<br/>PVE 1<br/>.5")]
      N_RAD>"📻 EXARADLND001<br/>BBC Office Radio Mk II<br/>.80"]
      N_MIC>"🎤 EXAMICLND001<br/>Shure SM7 via Dante audio<br/>.81"]
      N_SWI{{"EXASWILND001<br/>Core switch<br/>.250"}}
      N_WKS(["EXAWKSLND001<br/>Workstation<br/>.150"])
      N_PRN(["EXAPRNLND001<br/>Printer"])
      N_PRN2(["EXAPRNLND002<br/>Steno writer no IP"])
    end
    style NEW_LND fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:LND:END
```

---
