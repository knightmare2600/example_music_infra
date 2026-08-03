# Example Music Limited — Deutschland Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## BON — Bonn 🎼

**LAN:** `192.168.228.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Note:** Hosts Schema Master + Domain Naming Master  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 228 555 xxx · **Mobile:** +49 211 xxx xxxx

### 🕰️ Old Network (legacy, hand restyled — prototype, not yet generated)

> **Corrected against Robert's real facts, 2026-07-31.** Standing corrections applied (no SBC;
> no `RRY`; no WireGuard on old infra). Octet collision resolved — `.2` belongs to `EXARACBON001`
> (real), not `EXAVCUBON001`; the VCU turned out to be new-build-supplied kit with "no business
> being in the old network" at all — removed entirely (it uses DHCP in the new build, explaining
> the stray octet clash). `EXADCSBON001` (Schema Master, Domain Naming Master) confirmed real,
> bare metal on the HP ML310e attached to the Dell iDRAC9. Workstation, both laptops (including
> the ⚠️ disabled ThinkPad), CCTV camera, display, and WAPs all confirmed real and kept.

```mermaid
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    O_INET["🌐 Internet"]
    O_RTR["📡 EXARTRBON001<br/>Cisco ISR 4331<br/>192.168.228.1"]
    O_INET --> O_RTR
    O_SW["🔀 EXASWIBON001<br/>Cisco 2960X<br/>192.168.228.250"]
    O_RTR --> O_SW

    O_RAC["🔧 EXARACBON001<br/>Dell iDRAC9<br/>192.168.228.2"]
    O_DC["🗝️ EXADCSBON001<br/>DC · Schema Master, DN Master, HP ML310e bare metal<br/>192.168.228.10"]
    O_SW --> O_RAC
    O_RAC -.->|"manages"| O_DC

    O_WKS["🖥️ EXAWKSBON001<br/>Finance WKS<br/>192.168.228.151"]
    O_LAP1["💻 ⚠️ EXALAPBON001<br/>ThinkPad, disabled<br/>192.168.228.150"]
    O_LAP2["💻 EXALAPBON002<br/>Finance Laptop<br/>192.168.228.153"]
    O_CAM["🎥 EXACAMBON001<br/>Axis P3245-LVE CCTV<br/>192.168.228.17"]
    O_TV["📺 EXATVSBON001<br/>Samsung 65in<br/>192.168.228.18"]
    O_WAP["📶 EXAWAPBON001-002<br/>2x Ubiquiti UniFi U6-Pro<br/>No IP Address"]
    O_SW --> O_WKS
    O_SW --> O_LAP1
    O_SW --> O_LAP2
    O_SW --> O_CAM
    O_SW --> O_TV
    O_SW --> O_WAP

    style O_INET fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_SW fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_RAC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_DC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_WKS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_LAP1 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_LAP2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_CAM fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_TV fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
```

<details>
<summary>Original hand-maintained Old Network box (pre-restyle, kept for reference during prototype review)</summary>

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
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_BON fill:#56B4E9,stroke:#0072B2,color:#000000
```

</details>

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:BON:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRBON001<br/>RTR<br/>192.168.228.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCBON001<br/>BMC 1<br/>192.168.228.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEBON001<br/>PVE 1<br/>192.168.228.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIBON002<br/>SWI 2<br/>192.168.228.251"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIBON003<br/>SWI 3<br/>192.168.228.252"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIBON001<br/>Office Switch<br/>192.168.228.250"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASBON001<br/>NAS<br/>192.168.228.19"]
    T_RDR["🔐 EXARDRBON001<br/>RDR<br/>192.168.228.21"]
    T_WAP["📶 EXAWAPBON001<br/>WAP 1<br/>192.168.228.82"]
    T_WAP2["📶 EXAWAPBON002<br/>Wireless Access Point<br/>192.168.228.83"]
    T_SWI3 --> T_NAS --> T_RDR --> T_WAP --> T_WAP2
    T_DCS["🗝️ EXADCSBON001<br/>DCS 1<br/>192.168.228.10"]
    T_SBC["🛡️ EXASBCBON001<br/>SBC<br/>192.168.228.48"]
    T_FWL["🧱 EXAFWLBON001<br/>LAN Face<br/>192.168.228.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_OTH_LAP["💻 EXALAPBON001-002<br/>2 x Laptops<br/>No IP Address"]
    T_WKS["🖥️ EXAWKSBON001<br/>Finance Workstation<br/>No IP Address"]
    T_VCU["🎧 EXAVCUBON001<br/>Boardroom Video Conferencing<br/>No IP Address"]
    T_CAM["🎥 EXACAMBON001<br/>CCTV Camera<br/>192.168.228.17"]
    T_TVS["📺 EXATVSBON001<br/>Display<br/>No IP Address"]
    T_OTH_LAP --> T_VCU --> T_TVS
    T_WKS --> T_CAM
    style T_VRK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_OTH_LAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WKS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_VCU fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_CAM fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_TVS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:BON:END
```

---

## BER — West Berlin 🐻

**LAN:** `192.168.113.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 311 555 xxx · **Mobile:** +49 211 xxx xxxx

### 🕰️ Old Network (legacy, hand restyled — prototype, not yet generated)

> **Corrected against Robert's real facts, 2026-07-31.** Standing corrections applied (no SBC;
> no `RRY`; no WireGuard on old infra). All three "servers" were Dell OptiPlex consumer PCs —
> `EXADCSBER001` (PDC Emulator/RID-Infra Master), `EXASRVBER001` (WS2019 Legacy App Server), and
> `EXANIXBER001` (Debian 12), all confirmed separate real devices. `EXARACBER001` "was called RAC
> but wasn't a real RAC" — a basic PCI remote-power-on add-in card, not a genuine enterprise
> BMC/iLO/iDRAC; kept as `RAC` type (role_codes.csv's own definition already covers "RAC
> emulator") with that nuance stated plainly. Replaced by a proper PVE-hosted hypervisor in the
> new build. WAPs (×2) confirmed never opened — still shrink-wrapped — moved straight into the
> new UniFi controller cluster rather than ever deployed on old infra.

```mermaid
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    O_INET["🌐 Internet"]
    O_RTR["📡 EXARTRBER001<br/>Cisco ISR 4331<br/>192.168.113.1"]
    O_INET --> O_RTR

    O_RAC["🔧 EXARACBER001<br/>PCI remote-power card on OptiPlex, not a real BMC<br/>192.168.113.2"]
    O_DC["🗝️ EXADCSBER001<br/>DC · PDC Emulator, RID/Infra Master, WS2019, Dell OptiPlex<br/>192.168.113.10"]
    O_RTR --> O_RAC
    O_RAC -.->|"manages"| O_DC

    O_SRV["🗄️ EXASRVBER001<br/>WS2019 Legacy App Server, Dell OptiPlex<br/>192.168.113.21"]
    O_NIX["🐧 EXANIXBER001<br/>Debian 12, Dell OptiPlex<br/>192.168.113.22"]
    O_WAP["📶 WAPs — never opened, moved straight into new UniFi controller cluster"]
    O_CAM["🎥 CAMs — none yet, new build only"]
    O_RTR --> O_SRV
    O_RTR --> O_NIX
    O_RTR --> O_WAP
    O_RTR --> O_CAM

    style O_INET fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_RAC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_DC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_SRV fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_NIX fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_CAM fill:#000000,stroke:#FFFFFF,color:#FFFFFF
```

<details>
<summary>Original hand-maintained Old Network box (pre-restyle, kept for reference during prototype review)</summary>

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
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_BER fill:#56B4E9,stroke:#0072B2,color:#000000
```

</details>

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:BER:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRBER001<br/>RTR<br/>192.168.113.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCBER001<br/>BMC 1<br/>192.168.113.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEBER001<br/>PVE 1<br/>192.168.113.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIBER001<br/>SWI 1<br/>192.168.113.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIBER002<br/>SWI 2<br/>192.168.113.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIBER003<br/>SWI 3<br/>192.168.113.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASBER001<br/>NAS<br/>192.168.113.19"]
    T_RDR["🔐 EXARDRBER001<br/>RDR<br/>192.168.113.21"]
    T_WAP["📶 EXAWAPBER001<br/>WAP 1<br/>192.168.113.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSBER001<br/>DCS 1<br/>192.168.113.10"]
    T_SBC["🛡️ EXASBCBER001<br/>SBC<br/>192.168.113.48"]
    T_FWL["🧱 EXAFWLBER001<br/>LAN Face<br/>192.168.113.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    style T_VRK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:BER:END
```

---

## MUN — Munich 🍺

**LAN:** `192.168.189.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** ODE  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 893 555 33xx · **Mobile:** +49 893 555 99xx

### 🕰️ Old Network (legacy, hand restyled — prototype, not yet generated)

> **Corrected against Robert's real facts, 2026-07-31.** Standing corrections applied (no SBC;
> no `RRY`; no WireGuard on old infra). No DC, no hypervisor, no BMC ever existed here — Robert:
> "if you didn't find them then no, they are not there" (confirmed against `devices.csv`, which
> only has the switch and endpoints, nothing BMC/DC-shaped). `EXARACMUN001`/`EXADCSMUN001`
> removed entirely. WAP confirmed never deployed. Switch, hot-desk WKS, and both pool laptops
> (including `⚠️ LAPS expired 61d`, kept per the standing rule) all confirmed real.

```mermaid
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    O_INET["🌐 Internet"]
    O_SW["🔀 EXASWIMUN001<br/>Cisco 9200<br/>192.168.189.250"]
    O_INET --> O_SW

    O_WKS["🖥️ EXAWKSMUN001<br/>Hot Desk WKS<br/>192.168.189.150"]
    O_LAP1["💻 EXALAPMUN001<br/>Pool Laptop<br/>192.168.189.151"]
    O_LAP2["💻 ⚠️ EXALAPMUN002<br/>Pool Laptop, LAPS expired 61d<br/>192.168.189.152"]
    O_WAP["📶 WAPs — none yet, new build only"]
    O_CAM["🎥 CAMs — none yet, new build only"]
    O_SW --> O_WKS
    O_SW --> O_LAP1
    O_SW --> O_LAP2
    O_SW --> O_WAP
    O_SW --> O_CAM

    style O_INET fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_SW fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_WKS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_LAP1 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_LAP2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_CAM fill:#000000,stroke:#FFFFFF,color:#FFFFFF
```

<details>
<summary>Original hand-maintained Old Network box (pre-restyle, kept for reference during prototype review)</summary>

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
      RRY -. "→ EXARUDCLD001" .-> VPN
    end
    style OLD_MUN fill:#56B4E9,stroke:#0072B2,color:#000000
```

</details>

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:MUN:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRMUN001<br/>RTR<br/>192.168.189.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCMUN001<br/>BMC 1<br/>192.168.189.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEMUN001<br/>PVE 1<br/>192.168.189.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIMUN002<br/>SWI 2<br/>192.168.189.251"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIMUN003<br/>SWI 3<br/>192.168.189.252"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIMUN001<br/>Access Switch<br/>192.168.189.250"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASMUN001<br/>NAS<br/>192.168.189.19"]
    T_RDR["🔐 EXARDRMUN001<br/>RDR<br/>192.168.189.21"]
    T_WAP["📶 EXAWAPMUN001<br/>WAP 1<br/>192.168.189.82"]
    T_SWI3 --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSMUN001<br/>DCS 1<br/>192.168.189.10"]
    T_SBC["🛡️ EXASBCMUN001<br/>SBC<br/>192.168.189.48"]
    T_FWL["🧱 EXAFWLMUN001<br/>LAN Face<br/>192.168.189.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_WKS["🖥️ EXAWKSMUN001<br/>Hot Desk Workstation<br/>No IP Address"]
    T_OTH_LAP["💻 EXALAPMUN001-002<br/>2 x Laptops<br/>No IP Address"]
    style T_VRK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WKS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_OTH_LAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:MUN:END
```

---

## DRS — Dresden 🕺

**LAN:** `192.168.153.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 (reserved — see notes below) · **VPN parent:** ODE  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 351 555 xxx · **Mobile:** +49 172 xxx xxxx

> **New-build site — corrected 2026-07-31.** The previous "Old Network" box here was entirely
> fabricated template content, not real history — zero real `devices.csv` rows exist for DRS,
> and Robert confirmed: "it's an expansion office." Converted to the same "New Build Location"
> placeholder pattern used for FRD/NYB/SEA/SFO/FRE. Standard-slot addresses are allocated the
> same as any other site, but no `devices.csv` exception rows exist yet — nothing beyond the
> standard template has been confirmed built here.

```mermaid
graph TD
    subgraph OLD_DRS ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site. · No prior/legacy network existed before commissioning."]
    end
    style OLD_DRS fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:DRS:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRDRS001<br/>RTR<br/>192.168.153.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCDRS001<br/>BMC 1<br/>192.168.153.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEDRS001<br/>PVE 1<br/>192.168.153.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIDRS001<br/>SWI 1<br/>192.168.153.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIDRS002<br/>SWI 2<br/>192.168.153.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIDRS003<br/>SWI 3<br/>192.168.153.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASDRS001<br/>NAS<br/>192.168.153.19"]
    T_RDR["🔐 EXARDRDRS001<br/>RDR<br/>192.168.153.21"]
    T_WAP["📶 EXAWAPDRS001<br/>WAP 1<br/>192.168.153.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSDRS001<br/>DCS 1<br/>192.168.153.10"]
    T_SBC["🛡️ EXASBCDRS001<br/>SBC<br/>192.168.153.48"]
    T_FWL["🧱 EXAFWLDRS001<br/>LAN Face<br/>192.168.153.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    style T_VRK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:DRS:END
```

---

## DUS — Düsseldorf 👗

**LAN:** `192.168.211.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 (reserved — see notes below) · **VPN parent:** ODE  
**Entity:** Example Music (Deutschland) GmbH · **Landline:** +49 211 555 xxx · **Mobile:** +49 172 xxx xxxx

> **New-build site — corrected 2026-07-31.** The previous "Old Network" box here was entirely
> fabricated template content — zero real `devices.csv` rows exist for DUS, and Robert confirmed
> it's an expansion office. Converted to the same "New Build Location" placeholder pattern used
> for FRD/NYB/SEA/SFO/FRE/DRS. Standard-slot addresses are allocated the same as any other site,
> but no `devices.csv` exception rows exist yet.

```mermaid
graph TD
    subgraph OLD_DUS ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site. · No prior/legacy network existed before commissioning."]
    end
    style OLD_DUS fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:DUS:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRDUS001<br/>RTR<br/>192.168.211.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCDUS001<br/>BMC 1<br/>192.168.211.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEDUS001<br/>PVE 1<br/>192.168.211.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIDUS001<br/>SWI 1<br/>192.168.211.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIDUS002<br/>SWI 2<br/>192.168.211.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIDUS003<br/>SWI 3<br/>192.168.211.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASDUS001<br/>NAS<br/>192.168.211.19"]
    T_RDR["🔐 EXARDRDUS001<br/>RDR<br/>192.168.211.21"]
    T_WAP["📶 EXAWAPDUS001<br/>WAP 1<br/>192.168.211.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSDUS001<br/>DCS 1<br/>192.168.211.10"]
    T_SBC["🛡️ EXASBCDUS001<br/>SBC<br/>192.168.211.48"]
    T_FWL["🧱 EXAFWLDUS001<br/>LAN Face<br/>192.168.211.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    style T_VRK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:DUS:END
```
