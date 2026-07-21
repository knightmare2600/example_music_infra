# Example Music Limited — Danmark Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## CPH — København 🧜‍♀️

**LAN:** `192.168.231.0/24` · **Domain:** `example.com` / `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_CPH ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      SW["🔀 EXASWICPH001 · TP-Link JetStream · .250"]
      RTR["📡 EXARTRCPH001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACCPH001 · Dell iDRAC9 · .2"]
      PVE["🗂️ EXAPVECPH001 · Proxmox node 1 · .5"]
      DC1["🗝️ EXADCSCPH001 · DC · example.com · .10"]
      DC2["🗝️ EXADCSCPH002 · DC · example.net · .11"]
      SBC["🛡️ EXASBCCPH001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYCPH001 · Rudder Relay · .12"]
      NTP["⏰ EXACLKCPH001 · Meinberg LANTIME M300 · NTP Clock · .18"]
      TV["📺 EXATVSCPH001 · Bella Kronik 42X · DR/TV2 · .17"]
      WAP["WAPs x3 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → ODE"]

      INET --> RTR --> SW
      SW --> PVE --> DC1 & DC2 & SBC
      RAC -.->|"manages"| PVE
      SW --> NTP & TV & WAP & CAM
      RTR <-->|"WireGuard tunnel"| VPN

      SW --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_CPH fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:CPH:START
    subgraph NEW_CPH ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRCPH001 · RTR · .1"]
      N_SBC["🛡️ EXASBCCPH001 · SBC · .48"]
      N_DCS["🗝️ EXADCSCPH001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLCPH001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLCPH002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVECPH001 · PVE 1 · .5"]
      N_CLK["⏰ EXACLKCPH001 · NTP clock · .18"]
      N_TVS["📺 EXATVSCPH001 · Display · .17"]
      N_SWI["🔀 EXASWICPH001 · Office switch · .250"]
    end
    style NEW_CPH fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:CPH:END
```

---

## ODE — Odense *(EU Hub)* ⭐ 🎩

**LAN:** `192.168.126.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (EU hub) · **VPN parent:** CLD (EU backup)  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_ODE ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWL["🧱 EXAFWLODE001 · Cisco ASA 5506-X · .1"]

      subgraph BMC ["BMC Pool"]
          RAC1["🔧 EXARACODE001 · BMC node 1 · .2"]
          RAC2["🔧 EXARACODE002 · BMC node 2 · .3"]
          RAC3["🔧 EXARACODE003 · BMC node 3 · .4"]
      end

      subgraph PVE ["Proxmox Cluster (3-node)"]
          PVE1["🗂️ EXAPVEODE001 · Proxmox node 1 · .5"]
          PVE2["🗂️ EXAPVEODE002 · Proxmox node 2 · .6"]
          PVE3["🗂️ EXAPVEODE003 · Proxmox node 3 · .7"]
      end

      DC1["🗝️ EXADCSODE001 · DC PDC · RID/Infra Master · .10"]
      DC2["🗝️ EXADCSODE002 · DC secondary · .11"]
      SBC["🛡️ EXASBCODE001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYODE001 · Rudder Relay · .12"]
      MAC["🍎 EXAMACODE001 · iMac · macOS Tahoe · .150"]
      MBP["💻 EXAMBPODE002 · MacBook Pro · .151"]
      JKB["💿 EXAMUSODE001 · Pureline 128V Jukebox · .60"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN_CLD["🔗 WireGuard ← CLD · EU backup"]
      VPN_EU["🔗 WireGuard → EU spokes · CPH/KGE/FAX/KOR/AAR/FRE/BON/BER · DRS/DUS/MUN/GOT/OSL/AMS/MIL/VIE/BRT"]

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
      RRY -. "→ EXARUDCLD001" .-> VPN_CLD
    end
    style OLD_ODE fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:ODE:START
    subgraph NEW_ODE ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRODE001 · RTR · .1"]
      N_SBC["🛡️ EXASBCODE001 · SBC · .48"]
      N_DCS["🗝️ EXADCSODE001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLODE001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLODE002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEODE001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIODE001 · SWI 1 · .250"]
      N_MUS["💿 EXAMUSODE001 · Jukebox · .60"]
      N_MAC["🍎 EXAMACODE001 · iMac"]
      N_MBP["💻 EXAMBPODE002 · MacBook Pro"]
    end
    style NEW_ODE fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:ODE:END
```

---

## KGE — Køge ⚠️ 🏘️

**LAN:** `192.168.65.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
> ⚠️ DC out of sync 27 days · WS2016 EOL · disk space low — rebuild required  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_KGE ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACKGE001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEKGE001 · Proxmox node 1 · .5"]
      DC["⚠️ 🗝️ EXADCSKGE001 · DC · WS2016 EOL · OOS 27d · .10"]
      SBC["🛡️ EXASBCKGE001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYKGE001 · Rudder Relay · .12"]
      WAP["📶 EXAWAPKGE001 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      PRN["🖨️ EXAPRNKGE001 · HP LaserJet MFP M528 · .16"]
      VPN["🔗 WireGuard → ODE"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM & PRN
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_KGE fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:KGE:START
    subgraph NEW_KGE ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRKGE001 · RTR · .1"]
      N_SBC["🛡️ EXASBCKGE001 · SBC · .48"]
      N_DCS["🗝️ EXADCSKGE001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLKGE001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLKGE002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEKGE001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIKGE001 · SWI 1 · .250"]
      N_PRN["🖨️ EXAPRNKGE001 · Printer"]
    end
    style NEW_KGE fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:KGE:END
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class DC warn
```

---

## FAX — Faxe 🥤

**LAN:** `192.168.246.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_FAX ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RTR["📡 EXARTRFAX001 · Cisco ISR 4331 · .254"]
      RAC["🔧 EXARACFAX001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEFAX001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSFAX001 · DC · .10"]
      SBC["🛡️ EXASBCFAX001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYFAX001 · Rudder Relay · .12"]
      WAP["WAPs x2 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → ODE"]

      INET --> RTR --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      RTR --> WAP & CAM
      RTR <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_FAX fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:FAX:START
    subgraph NEW_FAX ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRFAX001 · RTR · .1"]
      N_SBC["🛡️ EXASBCFAX001 · SBC · .48"]
      N_DCS["🗝️ EXADCSFAX001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLFAX001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLFAX002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEFAX001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIFAX001 · SWI 1 · .250"]
    end
    style NEW_FAX fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:FAX:END
```

---

## KOR — Korsør 🚂

**LAN:** `192.168.238.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_KOR ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACKOR001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEKOR001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSKOR001 · DC · .10"]
      SBC["🛡️ EXASBCKOR001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYKOR001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → ODE"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_KOR fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:KOR:START
    subgraph NEW_KOR ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRKOR001 · RTR · .1"]
      N_SBC["🛡️ EXASBCKOR001 · SBC · .48"]
      N_DCS["🗝️ EXADCSKOR001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLKOR001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLKOR002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEKOR001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIKOR001 · SWI 1 · .250"]
    end
    style NEW_KOR fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:KOR:END
```

---

## AAR — Aarhus 🎓

**LAN:** `192.168.86.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 00 000 xxx · **Mobile:** +45 2x xxx xxx

```mermaid
graph TD
    subgraph OLD_AAR ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACAAR001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEAAR001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSAAR001 · DC · .10"]
      SBC["🛡️ EXASBCAAR001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYAAR001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → ODE"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_AAR fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:AAR:START
    subgraph NEW_AAR ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRAAR001 · RTR · .1"]
      N_SBC["🛡️ EXASBCAAR001 · SBC · .48"]
      N_DCS["🗝️ EXADCSAAR001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLAAR001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLAAR002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEAAR001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIAAR001 · SWI 1 · .250"]
    end
    style NEW_AAR fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:AAR:END
```

---

## FRE — Fredericia 🏯

**LAN:** `192.168.75.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 75 xx xx xx · **Mobile:** +45 2x xx xx xx

```mermaid
graph TD
    subgraph OLD_FRE ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACFRE001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVEFRE001 · Proxmox node 1 · .5"]
      DC["🗝️ EXADCSFRE001 · DC · .10"]
      SBC["🛡️ EXASBCFRE001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYFRE001 · Rudder Relay · .12"]
      WAP["WAPs TODO · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VPN["🔗 WireGuard → ODE"]

      INET --> PVE --> DC & SBC
      RAC -.->|"manages"| PVE
      PVE --> WAP & CAM
      PVE <-->|"WireGuard tunnel"| VPN

      PVE --> RRY
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_FRE fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:FRE:START
    subgraph NEW_FRE ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRFRE001 · RTR · .1"]
      N_SBC["🛡️ EXASBCFRE001 · SBC · .48"]
      N_DCS["🗝️ EXADCSFRE001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLFRE001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLFRE002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVEFRE001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWIFRE001 · SWI 1 · .250"]
    end
    style NEW_FRE fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:FRE:END
```

---

## FRD — Fredericia Havn *(New Build)* ⚓

**LAN:** `172.16.124.0/24` · **Domain:** `example.net`  
**PVE nodes:** 0 — see notes below · **VPN parent:** CLD (direct, non-standard networking)  
**Entity:** Example Music Limited · **Landline:** N/A · **Mobile:** N/A

> **New-build site.** No legacy infrastructure ever existed here — see the "New Build Location" box below in place of "Old Network." Fredericia Havn is one machine today: a MacBook running `python3 -m http.server 8000` as a PXE mirror, plus a secondary 3CX PBX hostnamed under CLD (`EXAPBXCLD002`) but physically here — see `benarbejde/generate_inventory.py`'s `NON_STANDARD_SITES`/`SubnetSite` handling.

```mermaid
graph TD
    subgraph OLD_FRD ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site. · No prior/legacy network existed before commissioning."]
    end
    style OLD_FRD fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:FRD:START
    subgraph NEW_FRD ["🆕 New Network (current)"]
      N_TMP["📦 Provisioning server (PXE, port 8000) · .1"]
      N_PBX["🔌 EXAPBXCLD002 · Secondary 3CX PBX (hostnamed under CLD) · .48"]
    end
    style NEW_FRD fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:FRD:END
```

---

## NYB — Nyborg *(New Build)* 📜

**LAN:** `192.168.90.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 (reserved — see notes below) · **VPN parent:** ODE  
**Entity:** Example Music (Danmark) ApS · **Landline:** +45 80 400 0xxx · **Mobile:** +45 200 900 2xxx

> **New-build site.** No legacy infrastructure ever existed here — see the "New Build Location" box below in place of "Old Network." Standard-slot addresses are allocated in `benarbejde/address_policy.json`/`sites.csv` the same as any other site (this is what makes the .ini/DNS generation already treat them as real, per the generated-file-freshness harness check) but no `devices.csv` exception rows exist yet — nothing beyond the standard template has been confirmed built on site.

```mermaid
graph TD
    subgraph OLD_NYB ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site. · No prior/legacy network existed before commissioning."]
    end
    style OLD_NYB fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:NYB:START
    subgraph NEW_NYB ["🆕 New Network (current)"]
      N_RTR["📡 EXARTRNYB001 · RTR · .1"]
      N_SBC["🛡️ EXASBCNYB001 · SBC · .48"]
      N_DCS["🗝️ EXADCSNYB001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLNYB001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLNYB002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVENYB001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWINYB001 · SWI 1 · .250"]
    end
    style NEW_NYB fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:NYB:END
```
