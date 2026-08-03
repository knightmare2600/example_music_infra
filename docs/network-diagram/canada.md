# Example Music Limited — Canada Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## BRK — Brockville *(NA/APAC Hub)* ⭐ 🍁

**LAN:** `192.168.136.0/24` · **Domain:** `example.net`  
**PVE nodes:** 3 (NA/APAC hub) · **VPN parent:** CLD (NA/APAC backup)  
> ⚠️ `EXADCSBRK001` — DNS, Netlogon and KDC services stopped.  
**Entity:** Example Music (Canada) Inc. · **Landline:** +1 613 555 6xxx · **Mobile:** +1 613 555 6xxx

### 🕰️ Old Network (legacy, hand restyled — prototype, not yet generated)

> **Corrected against Robert's real facts, 2026-07-31.** Standing corrections applied (no SBC;
> no `RRY`; no WireGuard on old infra — including BRK's own hub/spoke relay to the NA/APAC sites,
> same "old sites had zero connectivity to each other" rule confirmed for both hub sites now).
> Like ODE: a genuinely real 3-node cluster — VMware ESXi, managed by a real vCenter
> (`EXAVCTBRK001`) plus per-node BMCs. **Presumed** the same HP ML310e/iLO hardware as every other
> confirmed site so far — not independently re-confirmed for BRK, flag if different. The DC's
> "services stopped" warning is real (confirmed, unlike NJC/ATL/CHI's copy-pasted version of the
> same text) — kept, and now correctly shown as a VM hosted on the cluster/vCenter rather than a
> standalone box, per Robert: "the DC node was on this vcentre." Laptop, WAP, and both vending
> machines (donut, maple syrup) all confirmed real.

> 🚨 **Migration priority — Tier 1 (highest).** DNS/Netlogon/KDC stopped on the NA/APAC hub
> site's own DC. Not a repair candidate — the fix is a new `EXADCSBRK001` build promoting and
> replicating against `EXADCSCLD001` (`ansible/playbooks/windows_dc/`), not restoring this node;
> the whole point of building `EXADCSCLD001` as forest root was to get every site's DC talking
> to it and replicating around, independent of whatever state the old box was in.

```mermaid
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    O_INET["🌐 Internet"]
    O_RTR["📡 EXARTRBRK001<br/>Cisco ISR 4331<br/>192.168.136.1"]
    O_INET --> O_RTR

    O_ILO1["🔧 EXARACBRK001<br/>HP iLO 1<br/>192.168.136.2"]
    O_ILO2["🔧 EXARACBRK002<br/>HP iLO 2<br/>192.168.136.3"]
    O_ILO3["🔧 EXARACBRK003<br/>HP iLO 3<br/>192.168.136.4"]
    O_ESX1["💾 EXAESXBRK001<br/>HP ML310e, VMware ESXi 1<br/>192.168.136.5"]
    O_ESX2["💾 EXAESXBRK002<br/>HP ML310e, VMware ESXi 2<br/>192.168.136.6"]
    O_ESX3["💾 EXAESXBRK003<br/>HP ML310e, VMware ESXi 3<br/>192.168.136.7"]
    O_VCT["🛰️ EXAVCTBRK001<br/>VMware vCenter · cluster management<br/>IP not recorded"]
    O_RTR --> O_ESX1
    O_RTR --> O_ESX2
    O_RTR --> O_ESX3
    O_RTR --> O_VCT
    O_ILO1 -.->|"manages"| O_ESX1
    O_ILO2 -.->|"manages"| O_ESX2
    O_ILO3 -.->|"manages"| O_ESX3
    O_VCT -.->|"manages"| O_ESX1
    O_VCT -.->|"manages"| O_ESX2
    O_VCT -.->|"manages"| O_ESX3

    O_DC["🔴🗝️ EXADCSBRK001<br/>DC · DNS/Netlogon/KDC services stopped, hosted on the vCenter cluster<br/>192.168.136.10"]
    O_VCT --> O_DC

    O_LAP["💻 EXALAPBRK001<br/>Win11 Tour Laptop<br/>192.168.136.21"]
    O_WAP["📶 EXAWAPBRK001<br/>Ubiquiti UniFi U6-Pro<br/>No IP Address"]
    O_CAM["🎥 CAMs — none yet, new build only"]
    O_VND1["🍩 EXADONBRK001<br/>Tim Hortons Donut Vending<br/>192.168.136.60"]
    O_VND2["🍫 EXAVNDBRK001<br/>Maple Syrup Vending<br/>192.168.136.61"]
    O_RTR --> O_LAP
    O_RTR --> O_WAP
    O_RTR --> O_CAM
    O_RTR --> O_VND1
    O_RTR --> O_VND2

    style O_INET fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_ILO1 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_ILO2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_ILO3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_ESX1 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_ESX2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_ESX3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_VCT fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_DC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_LAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_CAM fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_VND1 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_VND2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
```

<details>
<summary>Original hand-maintained Old Network box (pre-restyle, kept for reference during prototype review)</summary>

```mermaid
graph TD
    subgraph OLD_BRK ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RTR["📡 EXARTRBRK001 · Cisco ISR 4331 · .254"]

      subgraph BMC ["BMC Pool"]
          RAC1["🔧 EXARACBRK001 · BMC node 1 · .2"]
          RAC2["🔧 EXARACBRK002 · BMC node 2 · .3"]
          RAC3["🔧 EXARACBRK003 · BMC node 3 · .4"]
      end

      subgraph PVE ["Proxmox Cluster (3-node)"]
          PVE1["🗂️ EXAPVEBRK001 · Proxmox node 1 · .5"]
          PVE2["🗂️ EXAPVEBRK002 · Proxmox node 2 · .6"]
          PVE3["🗂️ EXAPVEBRK003 · Proxmox node 3 · .7"]
      end

      DC["🔴 🗝️ EXADCSBRK001 · DC · Services stopped · .10"]
      SBC["🛡️ EXASBCBRK001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYBRK001 · Rudder Relay · .12"]
      LAP["💻 EXALAPBRK001 · Win11 Tour Laptop · .21"]
      WAP["📶 EXAWAPBRK001 · Ubiquiti UniFi U6-Pro"]
      CAM["CAMs TODO"]
      VND1["🍩 EXADONBRK001 · Tim Hortons Donut Vending · .60"]
      VND2["🍫 EXAVNDBRK001 · Maple Syrup Vending · .61"]
      VPN_CLD["🔗 WireGuard ← CLD · NA/APAC backup"]
      VPN_NA["🔗 WireGuard → NA/APAC spokes · TOR/MTL/LAX/NYC/NJC · MIA/ATL/CHI/SYD/MEL/AKL"]

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
      RRY -. "→ EXARUDCLD001" .-> VPN_CLD
    end
    style OLD_BRK fill:#56B4E9,stroke:#0072B2,color:#000000
```

</details>

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:BRK:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRBRK001<br/>RTR<br/>192.168.136.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCBRK001<br/>BMC 1<br/>192.168.136.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEBRK001<br/>PVE 1<br/>192.168.136.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIBRK001<br/>SWI 1<br/>192.168.136.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIBRK003<br/>SWI 3<br/>192.168.136.252"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIBRK002<br/>Second Switch<br/>192.168.136.251"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASBRK001<br/>NAS<br/>192.168.136.19"]
    T_RDR["🔐 EXARDRBRK001<br/>RDR<br/>192.168.136.21"]
    T_WAP["📶 EXAWAPBRK001<br/>WAP 1<br/>192.168.136.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSBRK001<br/>DCS 1<br/>192.168.136.10"]
    T_SBC["🛡️ EXASBCBRK001<br/>SBC<br/>192.168.136.48"]
    T_FWL["🧱 EXAFWLBRK001<br/>LAN Face<br/>192.168.136.253"]
    T_PVE --> T_DCS --> T_SBC --> T_FWL
    T_DON["🍩 EXADONBRK001<br/>Donut Vending<br/>192.168.136.60"]
    T_LAP["💻 EXALAPBRK001<br/>Tour Laptop<br/>No IP Address"]
    T_VND["🍫 EXAVNDBRK001<br/>Vending Machine<br/>No IP Address"]
    T_DON --> T_VND
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
    style T_DON fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_LAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_VND fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:BRK:END
```

---

## TOR — Toronto ⚠️ 🗼

**LAN:** `192.168.146.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 · **VPN parent:** BRK  
**Entity:** Example Music (Canada) Inc. · **Landline:** +1 416 555 xxxx · **Mobile:** +1 647 555 xxxx

### 🕰️ Old Network (legacy, hand restyled — prototype, not yet generated)

> **Corrected against Robert's real facts, 2026-07-31.** Standing corrections applied (no SBC;
> no `RRY`; no WireGuard on old infra). TOR genuinely had **two** DCs, both bare metal on
> separate HP ML310e boxes with iLO cards, both decommissioned once the new network was up: the
> already-known `EXADCRTOR028` ("undocumented... no-one on record knew it existed", excluded
> from the *new* topology diagrams via check 29 but real, historical content that belongs here),
> and `EXADCSTOR001` — services stopped, and genuinely running on DHCP. Second iLO hostname
> (`EXARACTOR002`) follows the standard numbering convention, not independently confirmed
> per-device — flag if wrong. WAP/CAM confirmed genuinely never-installed.

> 🚨 **Migration priority — Tier 1.** `EXADCSTOR001` — services stopped and running on DHCP.
> Not a repair candidate — the fix is a new `EXADCSTOR001` build promoting and replicating
> against `EXADCSCLD001` (`ansible/playbooks/windows_dc/`), not restoring this node.
>
> 🚩 **Governance flag — undocumented node.** `EXADCRTOR028` — no-one on record knew this DC
> existed until this audit. Confirm its decommission status directly rather than presuming it's
> gone just because the new build never referenced it.

```mermaid
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    O_INET["🌐 Internet"]
    O_RAC1["🔧 EXARACTOR001<br/>HP iLO<br/>192.168.146.2"]
    O_DCR["🗝️ EXADCRTOR028<br/>DC · Undocumented legacy AD install, no-one on record knew it existed, HP ML310e bare metal<br/>192.168.146.10"]
    O_RAC1 -.->|"manages"| O_DCR
    O_INET --> O_RAC1

    O_RAC2["🔧 EXARACTOR002<br/>HP iLO<br/>192.168.146.3"]
    O_DC["🔴🗝️ EXADCSTOR001<br/>DC · DNS/Netlogon/KDC services stopped, on DHCP, HP ML310e bare metal<br/>192.168.146.11"]
    O_RAC2 -.->|"manages"| O_DC
    O_INET --> O_RAC2

    O_WAP["📶 WAPs — none yet, new build only"]
    O_CAM["🎥 CAMs — none yet, new build only"]
    O_INET --> O_WAP
    O_INET --> O_CAM

    style O_INET fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_RAC1 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_DCR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_RAC2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_DC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style O_CAM fill:#000000,stroke:#FFFFFF,color:#FFFFFF
```

<details>
<summary>Original hand-maintained Old Network box (pre-restyle, kept for reference during prototype review)</summary>

```mermaid
graph TD
    subgraph OLD_TOR ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      RAC["🔧 EXARACTOR001 · BMC node 1 · .2"]
      PVE["🗂️ EXAPVETOR001 · Proxmox node 1 · .5"]
      DC["🔴 🗝️ EXADCSTOR001 · DC · Services stopped · .10"]
      SBC["🛡️ EXASBCTOR001 · 3CX SBC → CLD PBX · .48"]
      RRY["🔁 EXARRYTOR001 · Rudder Relay · .12"]
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
    style OLD_TOR fill:#56B4E9,stroke:#0072B2,color:#000000
```

</details>

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:TOR:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRTOR001<br/>RTR<br/>192.168.146.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCTOR001<br/>BMC 1<br/>192.168.146.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVETOR001<br/>PVE 1<br/>192.168.146.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWITOR001<br/>SWI 1<br/>192.168.146.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWITOR002<br/>SWI 2<br/>192.168.146.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWITOR003<br/>SWI 3<br/>192.168.146.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASTOR001<br/>NAS<br/>192.168.146.19"]
    T_RDR["🔐 EXARDRTOR001<br/>RDR<br/>192.168.146.21"]
    T_WAP["📶 EXAWAPTOR001<br/>WAP 1<br/>192.168.146.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSTOR001<br/>DCS 1<br/>192.168.146.10"]
    T_SBC["🛡️ EXASBCTOR001<br/>SBC<br/>192.168.146.48"]
    T_FWL["🧱 EXAFWLTOR001<br/>LAN Face<br/>192.168.146.253"]
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
%% GENERATED:TOPOLOGY:TOR:END
```

---

## MTL — Montreal ⚜️

**LAN:** `192.168.154.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 (reserved — see notes below) · **VPN parent:** BRK  
**Entity:** Example Music (Canada) Inc. · **Landline:** +1 514 400 0xxx · **Mobile:** +1 514 900 2xxx

> **New-build site — corrected 2026-07-31.** The previous "Old Network" box here was entirely
> fabricated template content — zero real `devices.csv` rows exist for MTL, and Robert confirmed
> it's an expansion office. Converted to the same "New Build Location" placeholder pattern used
> for FRD/NYB/SEA/SFO/FRE/DRS/DUS/GOT/OSL/AMS/MIL/VIE/BRT.

```mermaid
graph TD
    subgraph OLD_MTL ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site. · No prior/legacy network existed before commissioning."]
    end
    style OLD_MTL fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:MTL:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRMTL001<br/>RTR<br/>192.168.154.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCMTL001<br/>BMC 1<br/>192.168.154.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEMTL001<br/>PVE 1<br/>192.168.154.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIMTL001<br/>SWI 1<br/>192.168.154.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIMTL002<br/>SWI 2<br/>192.168.154.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIMTL003<br/>SWI 3<br/>192.168.154.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASMTL001<br/>NAS<br/>192.168.154.19"]
    T_RDR["🔐 EXARDRMTL001<br/>RDR<br/>192.168.154.21"]
    T_WAP["📶 EXAWAPMTL001<br/>WAP 1<br/>192.168.154.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSMTL001<br/>DCS 1<br/>192.168.154.10"]
    T_SBC["🛡️ EXASBCMTL001<br/>SBC<br/>192.168.154.48"]
    T_FWL["🧱 EXAFWLMTL001<br/>LAN Face<br/>192.168.154.253"]
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
%% GENERATED:TOPOLOGY:MTL:END
```
