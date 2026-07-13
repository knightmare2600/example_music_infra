# Mermaid render bisection — Q3

Throwaway debug file, sites: FRD, NYB, BON, BER, MUN, DRS, DUS, GOT, OSL, AMS, MIL, VIE, BRT, BRK

---

## FRD — Fredericia Havn *(New Build)*

**LAN:** `172.16.124.0/24` · **Domain:** `example.net`  
**PVE nodes:** 0 — see notes below · **VPN parent:** CLD (direct, non-standard networking)  
**Entity:** Example Music Limited · **Landline:** N/A · **Mobile:** N/A

> **New-build site.** No legacy infrastructure ever existed here — see the "New Build Location" box below in place of "Old Network." Fredericia Havn is one machine today: a MacBook running `python3 -m http.server 8000` as a PXE mirror, plus a secondary 3CX PBX hostnamed under CLD (`EXAPBXCLD002`) but physically here — see `benarbejde/generate_inventory.py`'s `NON_STANDARD_SITES`/`SubnetSite` handling.

```mermaid
graph TD
    subgraph OLD_FRD ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site.<br/>No prior/legacy network existed before commissioning."]
    end
    style OLD_FRD fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:FRD:START
    subgraph NEW_FRD ["🆕 New Network (current)"]
      N_PRV[("EXAPRVFRD001<br/>Provisioning server (PXE, port 8000)<br/>.1")]
      N_PBX[("EXAPBXCLD002<br/>Secondary 3CX PBX (hostnamed under CLD)<br/>.48")]
    end
    style NEW_FRD fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:FRD:END
```

---

## NYB — Nyborg *(New Build)*

**LAN:** `192.168.90.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 (reserved — see notes below) · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 80 400 0xxx · **Mobile:** +45 200 900 2xxx

> **New-build site.** No legacy infrastructure ever existed here — see the "New Build Location" box below in place of "Old Network." Standard-slot addresses are allocated in `benarbejde/address_policy.json`/`sites.csv` the same as any other site (this is what makes the .ini/DNS generation already treat them as real, per the generated-file-freshness harness check) but no `devices.csv` exception rows exist yet — nothing beyond the standard template has been confirmed built on site.

```mermaid
graph TD
    subgraph OLD_NYB ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site.<br/>No prior/legacy network existed before commissioning."]
    end
    style OLD_NYB fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:NYB:START
    subgraph NEW_NYB ["🆕 New Network (current)"]
      N_RTR{{"EXARTRNYB001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVNYB001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCNYB001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSNYB001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLNYB001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLNYB002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVENYB001<br/>PVE 1<br/>.5")]
    end
    style NEW_NYB fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:NYB:END
```

---

---

## 🇩🇪 Deutschland

---

## BON — Bonn

**LAN:** `192.168.228.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Note:** Hosts Schema Master + Domain Naming Master  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 228 555 xxx · **Mobile:** +49 211 xxx xxxx

```mermaid
graph TD
    subgraph OLD_BON ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      SW{{"EXASWIBON001<br/>Cisco 2960X<br/>.250"}}
      RTR{{"EXARTRBON001<br/>Cisco ISR 4331<br/>.254"}}
      RAC[("EXARACBON001<br/>Dell iDRAC9<br/>.2")]
      PVE[("EXAPVEBON001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSBON001<br/>DC · Schema Master<br/>DN Master · .10")]
      SBC[("EXASBCBON001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYBON001<br/>Rudder Relay<br/>.12")]
      WKS(["EXAWKSBON001<br/>Finance WKS · .151"])
      LAP1(["EXALAPBON001<br/>ThinkPad ⚠️ disabled<br/>.150"])
      LAP2(["EXALAPBON002<br/>Finance Laptop · .153"])
      VCU(["EXAVCUBON001<br/>Poly Studio X70<br/>Boardroom · .2"])
      CAM(["EXACAMBON001<br/>Axis P3245-LVE CCTV<br/>.17"])
      TV(["EXATVSBON001<br/>Samsung 65in<br/>.18"])
      WAP["WAPs x2<br/>Ubiquiti UniFi U6-Pro"]
      VPN(["🔗 WireGuard → ODE"])

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
      N_RTR{{"EXARTRBON001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVBON001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCBON001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSBON001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLBON001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLBON002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEBON001<br/>PVE 1<br/>.5")]
      N_SWI{{"EXASWIBON001<br/>Office switch<br/>.250"}}
      N_LAP(["EXALAPBON001<br/>ThinkPad DISABLED"])
      N_WKS(["EXAWKSBON001<br/>Finance workstation"])
      N_LAP2(["EXALAPBON002<br/>Finance laptop"])
      N_VCU(["🎧 EXAVCUBON001<br/>Boardroom video conferencing"])
      N_CAM(["EXACAMBON001<br/>CCTV camera"])
      N_TVS(["EXATVSBON001<br/>Display"])
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
      INET(("🌐 Internet"))
      RTR{{"EXARTRBER001<br/>Cisco ISR 4331<br/>.254"}}
      RAC[("EXARACBER001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEBER001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSBER001<br/>DC · PDC Emulator<br/>RID/Infra Master WS2019 · .10")]
      SBC[("EXASBCBER001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYBER001<br/>Rudder Relay<br/>.12")]
      SRV[("EXASRVBER001<br/>WS2019 Legacy App Server<br/>.21")]
      NIX(["EXANIXBER001<br/>Debian 12 Server<br/>.22"])
      WAP["WAPs x2<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → ODE"])

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
      N_RTR{{"EXARTRBER001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVBER001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCBER001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSBER001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLBER001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLBER002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEBER001<br/>PVE 1<br/>.5")]
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
      INET(("🌐 Internet"))
      SW{{"EXASWIMUN001<br/>Cisco 9200<br/>.250"}}
      RAC[("EXARACMUN001<br/>HPE iLO5<br/>.2")]
      PVE[("EXAPVEMUN001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSMUN001<br/>DC<br/>.10")]
      SBC[("EXASBCMUN001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYMUN001<br/>Rudder Relay<br/>.12")]
      WKS(["EXAWKSMUN001<br/>Hot Desk WKS<br/>.150"])
      LAP1(["EXALAPMUN001<br/>Pool Laptop<br/>.151"])
      LAP2(["⚠️ EXALAPMUN002<br/>Pool Laptop<br/>LAPS expired 61d · .152"])
      WAP["WAPs TODO<br/>Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN(["🔗 WireGuard → ODE"])

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
      N_RTR{{"EXARTRMUN001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVMUN001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCMUN001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSMUN001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLMUN001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLMUN002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEMUN001<br/>PVE 1<br/>.5")]
      N_SWI{{"EXASWIMUN001<br/>Access switch<br/>.250"}}
      N_WKS(["EXAWKSMUN001<br/>Hot desk workstation"])
      N_LAP(["EXALAPMUN001<br/>Pool laptop"])
      N_LAP2(["EXALAPMUN002<br/>LAPS expired"])
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
      INET(("🌐 Internet"))
      RAC[("EXARACDRS001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEDRS001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSDRS001<br/>DC<br/>.10")]
      SBC[("EXASBCDRS001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYDRS001<br/>Rudder Relay<br/>.12")]
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
    style OLD_DRS fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:DRS:START
    subgraph NEW_DRS ["🆕 New Network (current)"]
      N_RTR{{"EXARTRDRS001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVDRS001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCDRS001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSDRS001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLDRS001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLDRS002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEDRS001<br/>PVE 1<br/>.5")]
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
      INET(("🌐 Internet"))
      RAC[("EXARACDUS001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEDUS001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSDUS001<br/>DC<br/>.10")]
      SBC[("EXASBCDUS001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYDUS001<br/>Rudder Relay<br/>.12")]
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
    style OLD_DUS fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:DUS:START
    subgraph NEW_DUS ["🆕 New Network (current)"]
      N_RTR{{"EXARTRDUS001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVDUS001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCDUS001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSDUS001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLDUS001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLDUS002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEDUS001<br/>PVE 1<br/>.5")]
    end
    style NEW_DUS fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:DUS:END
```

---

---

## 🇸🇪 Sverige

---

## GOT — Gothenburg

**LAN:** `192.168.46.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Sverige) AB · **Landline:** N/A · **Mobile:** N/A

```mermaid
graph TD
    subgraph OLD_GOT ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACGOT001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEGOT001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSGOT001<br/>DC<br/>.10")]
      SBC[("EXASBCGOT001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYGOT001<br/>Rudder Relay<br/>.12")]
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
    style OLD_GOT fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:GOT:START
    subgraph NEW_GOT ["🆕 New Network (current)"]
      N_RTR{{"EXARTRGOT001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVGOT001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCGOT001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSGOT001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLGOT001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLGOT002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEGOT001<br/>PVE 1<br/>.5")]
    end
    style NEW_GOT fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:GOT:END
```

---

---

## 🇳🇴 Norge

---

## OSL — Oslo

**LAN:** `192.168.47.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Norge) ASA · **Landline:** N/A · **Mobile:** N/A

```mermaid
graph TD
    subgraph OLD_OSL ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACOSL001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEOSL001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSOSL001<br/>DC<br/>.10")]
      SBC[("EXASBCOSL001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYOSL001<br/>Rudder Relay<br/>.12")]
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
    style OLD_OSL fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:OSL:START
    subgraph NEW_OSL ["🆕 New Network (current)"]
      N_RTR{{"EXARTROSL001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVOSL001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCOSL001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSOSL001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLOSL001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLOSL002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEOSL001<br/>PVE 1<br/>.5")]
    end
    style NEW_OSL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:OSL:END
```

---

---

## 🇳🇱 Nederland

---

## AMS — Amsterdam

**LAN:** `192.168.31.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Nederland) B.V. · **Landline:** N/A · **Mobile:** N/A

```mermaid
graph TD
    subgraph OLD_AMS ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACAMS001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEAMS001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSAMS001<br/>DC<br/>.10")]
      SBC[("EXASBCAMS001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYAMS001<br/>Rudder Relay<br/>.12")]
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
    style OLD_AMS fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:AMS:START
    subgraph NEW_AMS ["🆕 New Network (current)"]
      N_RTR{{"EXARTRAMS001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVAMS001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCAMS001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSAMS001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLAMS001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLAMS002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEAMS001<br/>PVE 1<br/>.5")]
    end
    style NEW_AMS fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:AMS:END
```

---

---

## 🇮🇹 Italia

---

## MIL — Milan

**LAN:** `192.168.39.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Italia) S.p.a. · **Landline:** N/A · **Mobile:** N/A

```mermaid
graph TD
    subgraph OLD_MIL ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACMIL001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEMIL001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSMIL001<br/>DC<br/>.10")]
      SBC[("EXASBCMIL001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYMIL001<br/>Rudder Relay<br/>.12")]
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
    style OLD_MIL fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:MIL:START
    subgraph NEW_MIL ["🆕 New Network (current)"]
      N_RTR{{"EXARTRMIL001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVMIL001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCMIL001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSMIL001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLMIL001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLMIL002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEMIL001<br/>PVE 1<br/>.5")]
    end
    style NEW_MIL fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:MIL:END
```

---

---

## 🇦🇹 Österreich

---

## VIE — Vienna

**LAN:** `192.168.78.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Osterreich) GmbH · **Landline:** +43 800 078 0xx · **Mobile:** +43 664 665 xxx

```mermaid
graph TD
    subgraph OLD_VIE ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACVIE001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEVIE001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSVIE001<br/>DC<br/>.10")]
      SBC[("EXASBCVIE001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYVIE001<br/>Rudder Relay<br/>.12")]
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
    style OLD_VIE fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:VIE:START
    subgraph NEW_VIE ["🆕 New Network (current)"]
      N_RTR{{"EXARTRVIE001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVVIE001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCVIE001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSVIE001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLVIE001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLVIE002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEVIE001<br/>PVE 1<br/>.5")]
    end
    style NEW_VIE fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:VIE:END
```

---

---

## 🇱🇧 Lebanon

---

## BRT — Beirut

**LAN:** `192.168.169.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Lebanon) SAL · **Landline:** +961 1 555 xxxx · **Mobile:** +961 3 555 xxxx

```mermaid
graph TD
    subgraph OLD_BRT ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RAC[("EXARACBRT001<br/>BMC node 1<br/>.2")]
      PVE[("EXAPVEBRT001<br/>Proxmox node 1<br/>.5")]
      DC[("EXADCSBRT001<br/>DC<br/>.10")]
      SBC[("EXASBCBRT001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYBRT001<br/>Rudder Relay<br/>.12")]
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
    style OLD_BRT fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:BRT:START
    subgraph NEW_BRT ["🆕 New Network (current)"]
      N_RTR{{"EXARTRBRT001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVBRT001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCBRT001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSBRT001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLBRT001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLBRT002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEBRT001<br/>PVE 1<br/>.5")]
    end
    style NEW_BRT fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:BRT:END
```

---

---

## 🇨🇦 Canada

---

## BRK — Brockville *(NA/APAC Hub)* ⭐

**LAN:** `192.168.136.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (NA/APAC hub) · **VPN parent:** CLD (NA/APAC backup)  
> ⚠️ `EXADCSBRK001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (Canada) Inc. · **Landline:** +1 613 555 6xxx · **Mobile:** +1 613 555 6xxx

```mermaid
graph TD
    subgraph OLD_BRK ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      RTR{{"EXARTRBRK001<br/>Cisco ISR 4331<br/>.254"}}

      subgraph BMC ["BMC Pool"]
          RAC1[("EXARACBRK001<br/>BMC node 1<br/>.2")]
          RAC2[("EXARACBRK002<br/>BMC node 2<br/>.3")]
          RAC3[("EXARACBRK003<br/>BMC node 3<br/>.4")]
      end

      subgraph PVE ["Proxmox Cluster (3-node)"]
          PVE1[("EXAPVEBRK001<br/>Proxmox node 1<br/>.5")]
          PVE2[("EXAPVEBRK002<br/>Proxmox node 2<br/>.6")]
          PVE3[("EXAPVEBRK003<br/>Proxmox node 3<br/>.7")]
      end

      DC[("🔴 EXADCSBRK001<br/>DC · Services stopped<br/>.10")]
      SBC[("EXASBCBRK001<br/>3CX SBC → CLD PBX<br/>.48")]
      RRY[("EXARRYBRK001<br/>Rudder Relay<br/>.12")]
      LAP(["EXALAPBRK001<br/>Win11 Tour Laptop<br/>.21"])
      WAP(("EXAWAPBRK001<br/>Ubiquiti UniFi U6-Pro"))
      CAM["CAMs TODO"]
      VND1>"EXADONBRK001<br/>Tim Hortons Donut Vending<br/>.60"]
      VND2>"EXAVNDBRK001<br/>Maple Syrup Vending<br/>.61"]
      VPN_CLD(["🔗 WireGuard ← CLD<br/>NA/APAC backup"])
      VPN_NA(["🔗 WireGuard → NA/APAC spokes<br/>TOR/MTL/LAX/NYC/NJC<br/>MIA/ATL/CHI/SYD/MEL/AKL"])

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
      N_RTR{{"EXARTRBRK001<br/>RTR<br/>.1"}}
      N_PRV[("EXAPRVBRK001<br/>PRV<br/>.15")]
      N_SBC[("EXASBCBRK001<br/>SBC<br/>.48")]
      N_DCS[("EXADCSBRK001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLBRK001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLBRK002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVEBRK001<br/>PVE 1<br/>.5")]
      N_DON>"🍩 EXADONBRK001<br/>Donut vending<br/>.60"]
      N_LAP(["EXALAPBRK001<br/>Tour laptop"])
      N_VND>"🍫 EXAVNDBRK001<br/>Vending machine"]
    end
    style NEW_BRK fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:BRK:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---
