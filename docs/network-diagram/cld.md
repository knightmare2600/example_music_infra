# Example Music Limited — Cloud (CLD) Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## ☁️  — Cloud / Provisioning

```
vRACK (VRK):   192.168.139.0/24
CLD LAN:       192.168.69.0/24
WireGuard VPN: 10.0.69.0/24
Role:          WireGuard hub — routes to all sites.
Central PBX, Ansible, WAC. CLD's own LAN is 192.168.69.0/24 — the vRACK (192.168.139.0/24) is a separate site code, VRK.
Entity: Example Music Limited
Landline: N/A
Mobile: N/A
```

> **CLD and VRK never had a legacy network — confirmed, not assumed.** Neither appears anywhere in
> `benarbejde/ad_computers.json` (the real pre-project Active Directory export the TDF file
> captured) — zero entries for either site code. Both are purely current infrastructure, added as
> part of this project. The box below reflects that. The auto-generated "New Network" box (which
> used to fold VRK's real devices in — `EXADNSVRK001`, its provisioning server, `EXAFWLVRK001`)
> has been retired in favour of the hand-drawn topology sketch further down; that sketch currently
> represents VRK only as a single boundary node, not its individual devices — a known
> simplification, not an omission to chase down.

```mermaid
graph TD
    subgraph OLD_CLD ["☁️ No Legacy Network — Cloud-Native, Never Existed Before This Project"]
      N_OLD_NOTE["Confirmed via benarbejde/ad_computers.json: zero pre-project AD entries for CLD or VRK."]
    end
    style OLD_CLD fill:#56B4E9,stroke:#0072B2,color:#000000
```

---

## 🗺️ Topology sketch (generated — see benarbejde/generate_network_diagrams.py)

```mermaid
%% GENERATED:TOPOLOGY:CLD:START
%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%
graph TD
    T_VRK["☁️ VRK — vRACK, 192.168.139.0/24"]
    T_RTR["📡 EXARTRCLD001<br/>RTR 1<br/>192.168.69.1"]
    T_VRK --> T_RTR
    T_BMC["🔧 EXABMCCLD001<br/>BMC 1<br/>192.168.69.2"]
    T_RTR --> T_BMC
    T_PVE["🗂️ EXAPVECLD001<br/>PVE 1<br/>192.168.69.5"]
    T_RTR --> T_PVE
    T_SWI["🔀 EXASWICLD001<br/>SWI 1<br/>192.168.69.250"]
    T_RTR --> T_SWI
    T_SWI2["🔀 EXASWICLD002<br/>SWI 2<br/>192.168.69.251"]
    T_RTR --> T_SWI2
    T_SWI3["🔀 EXASWICLD003<br/>SWI 3<br/>192.168.69.252"]
    T_RTR --> T_SWI3
    T_BMC2["🔧 EXABMCCLD002<br/>BMC 2<br/>192.168.69.3 — planned"]
    T_RTR --> T_BMC2
    T_PVE2["🗂️ EXAPVECLD002<br/>PVE 2<br/>192.168.69.6 — planned"]
    T_RTR --> T_PVE2
    T_NAS["🗃️ EXANASCLD001<br/>NAS<br/>192.168.69.19"]
    T_RDR["🔐 EXARDRCLD001<br/>RDR<br/>192.168.69.21"]
    T_SWI --> T_NAS --> T_RDR
    T_ANS["🤖 EXAANSCLD001<br/>Ansible Control Node<br/>192.168.69.9"]
    T_DCS["🗝️ EXADCSCLD001<br/>DCS 1<br/>192.168.69.10"]
    T_SVR["🗄️ EXASVRCLD002<br/>Windows Admin Centre<br/>192.168.69.20"]
    T_SLT["🧂 EXASLTCLD001<br/>Salt Master<br/>192.168.69.22"]
    T_PBX["🔌 EXAPBXCLD001<br/>3CX PBX<br/>192.168.69.48"]
    T_UFC["🎛️ EXAUFCCLD001<br/>UniFi Network Controller<br/>192.168.69.82"]
    T_FWL["🧱 EXAFWLCLD001<br/>FWL 1<br/>192.168.69.253"]
    T_PVE --> T_ANS --> T_DCS --> T_SVR --> T_SLT --> T_PBX --> T_UFC --> T_FWL
    style T_VRK fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RTR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SWI3 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_BMC2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PVE2 fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_NAS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_RDR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_ANS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_DCS fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SVR fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_SLT fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_PBX fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_UFC fill:#000000,stroke:#FFFFFF,color:#FFFFFF
    style T_FWL fill:#000000,stroke:#FFFFFF,color:#FFFFFF
%% GENERATED:TOPOLOGY:CLD:END
```
