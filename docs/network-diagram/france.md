# Example Music Limited — France Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## MRS — Marseille ⚓

**LAN:** `192.168.91.0/24` · **Domain:** `jukebox.internal`
**PVE nodes:** 1 (reserved — see notes below) · **VPN parent:** ODE
**Entity:** Example Music (France) SARL · **Landline:** +33 4 91 555 0xxx · **Mobile:** +33 6 91 555 2xxx

> **New-build site, added 2026-10-08** — zero real `devices.csv` rows exist yet (standard
> boilerplate only, all `Planned=yes`, via `check_new_site_boilerplate.py --apply MRS`). Same
> "New Build Location" placeholder pattern used for AMS/FRD/NYB/SEA/SFO/FRE/DRS/DUS/GOT/OSL.

```mermaid
graph TD
    subgraph OLD_MRS ["🏗️ New Build Location — no legacy infrastructure existed here"]
      N_OLD_NOTE["This is a new-build site. · No prior/legacy network existed before commissioning."]
    end
    style OLD_MRS fill:#56B4E9,stroke:#0072B2,color:#000000
```

### 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:MRS:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRMRS001<br/>RTR<br/>192.168.91.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCMRS001<br/>BMC 1<br/>192.168.91.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVEMRS001<br/>PVE 1<br/>192.168.91.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWIMRS001<br/>SWI 1<br/>192.168.91.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWIMRS002<br/>SWI 2<br/>192.168.91.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWIMRS003<br/>SWI 3<br/>192.168.91.252"]
    T_RTR --> T_SWI3
    T_SWI["🔀 EXASWIMRS001<br/>SWI 1<br/>192.168.91.250 — planned"]
    T_RTR --> T_SWI
    T_PVE["🗂️ EXAPVEMRS001<br/>PVE 1<br/>192.168.91.5 — planned"]
    T_RTR --> T_PVE
    T_PVE2["🗂️ EXAPVEMRS002<br/>PVE 2<br/>192.168.91.6 — planned"]
    T_RTR --> T_PVE2
    T_NAS["🗃️ EXANASMRS001<br/>NAS<br/>192.168.91.19"]
    T_NAS["🗃️ EXANASMRS001<br/>NAS 1<br/>192.168.91.19 — planned"]
    T_RDR["🔐 EXARDRMRS001<br/>RDR<br/>192.168.91.21"]
    T_RDR["🔐 EXARDRMRS001<br/>RDR 1<br/>192.168.91.21 — planned"]
    T_WAP["📶 EXAWAPMRS001<br/>WAP 1<br/>192.168.91.82"]
    T_WAP["📶 EXAWAPMRS001<br/>WAP 1<br/>192.168.91.82 — planned"]
    T_SWI --> T_NAS --> T_NAS --> T_RDR --> T_RDR --> T_WAP --> T_WAP
    T_DCS["🗝️ EXADCSMRS001<br/>DCS 1<br/>192.168.91.10"]
    T_DCS["🗝️ EXADCSMRS001<br/>DCS 1<br/>192.168.91.10 — planned"]
    T_SBC["🛡️ EXASBCMRS001<br/>SBC<br/>192.168.91.48"]
    T_SBC["🛡️ EXASBCMRS001<br/>SBC 1<br/>192.168.91.48 — planned"]
    T_FWL["🧱 EXAFWLMRS001<br/>LAN Face<br/>192.168.91.253"]
    T_FWL["🧱 EXAFWLMRS001<br/>FWL 1<br/>192.168.91.253 — planned"]
    T_PVE --> T_DCS --> T_DCS --> T_SBC --> T_SBC --> T_FWL --> T_FWL
    T_ILO["🔧 EXAILOMRS001<br/>ILO 1<br/>192.168.91.3 — planned"]
    T_RAC["🔧 EXARACMRS002<br/>RAC 2<br/>192.168.91.4 — planned"]
    style T_VRK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_WAP fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SBC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_ILO fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RAC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:MRS:END
```
