# Example Music Limited — Italia Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## MIL — Milan 👔

**LAN:** `192.168.39.0/24` · **Domain:** `example.net`  
**PVE nodes:** 1 (reserved — see notes below) · **VPN parent:** ODE  
**Entity:** Example Music (Italia) S.p.a. · **Landline:** N/A · **Mobile:** N/A

> **New-build site — corrected 2026-07-31.** The previous "Old Network" box here was entirely
> fabricated template content — zero real `devices.csv` rows exist for MIL, and Robert confirmed
> it's an expansion office. Converted to the same "New Build Location" placeholder pattern used
> for FRD/NYB/SEA/SFO/FRE/DRS/DUS/GOT/OSL/AMS.

```mermaid
graph TD
    subgraph OLD_MIL ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site. · No prior/legacy network existed before commissioning."]
    end
    style OLD_MIL fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:MIL:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRMIL001<br/>RTR<br/>192.168.39.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCMIL001<br/>BMC 1<br/>192.168.39.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEMIL001<br/>PVE 1<br/>192.168.39.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIMIL001<br/>SWI 1<br/>192.168.39.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIMIL002<br/>SWI 2<br/>192.168.39.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIMIL003<br/>SWI 3<br/>192.168.39.252"]
    T_RTR --> T_SWI3
    T_NAS["🗃️ EXANASMIL001<br/>NAS<br/>192.168.39.19"]
    T_RDR["🔐 EXARDRMIL001<br/>RDR<br/>192.168.39.21"]
    T_WAP["📶 EXAWAPMIL001<br/>WAP 1<br/>192.168.39.82"]
    T_SWI --> T_NAS --> T_RDR --> T_WAP
    T_DCS["🗝️ EXADCSMIL001<br/>DCS 1<br/>192.168.39.10"]
    T_SBC["🛡️ EXASBCMIL001<br/>SBC<br/>192.168.39.48"]
    T_FWL["🧱 EXAFWLMIL001<br/>LAN Face<br/>192.168.39.253"]
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
%% GENERATED:TOPOLOGY:MIL:END
```
