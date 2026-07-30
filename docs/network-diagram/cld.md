# Example Music Limited — Cloud (CLD) Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## ☁️  — Cloud / Provisioning

**vRACK (`VRK`):** `192.168.139.0/24` · **CLD LAN:** `192.168.69.0/24` · **WireGuard VPN:** `10.0.69.0/24`
**Role:** WireGuard hub — routes to all sites. Central PBX, Ansible, Rudder, WAC.
CLD's own LAN is `192.168.69.0/24` — the vRACK (`192.168.139.0/24`) is a separate site code, `VRK`.  
**Entity:** Example Music Limited · **Landline:** N/A · **Mobile:** N/A

> **CLD and VRK never had a legacy network — confirmed, not assumed.** Neither appears anywhere in
> `benarbejde/ad_computers.json` (the real pre-project Active Directory export the TDF file
> captured) — zero entries for either site code. Both are purely current infrastructure, added as
> part of this project. The box below reflects that; VRK's real devices (it has no diagram section
> of its own) now show up in the New Network box, folded in by `generate_network_diagrams.py`.

```mermaid
graph TD
    subgraph OLD_CLD ["☁️ No Legacy Network — Cloud-Native, Never Existed Before This Project"]
      N_OLD_NOTE["Confirmed via benarbejde/ad_computers.json: zero pre-project AD entries for CLD or VRK."]
    end
    style OLD_CLD fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:CLD:START
    subgraph NEW_CLD ["🆕 New Network (current)"]
      N_NAS["🗃️ EXANASCLD001 · NAS · .19"]
      N_RDR["🔐 EXARDRCLD001 · RDR · .21"]
      N_BMC["🔧 EXABMCCLD001 · BMC 1 · .2"]
      N_DCS["🗝️ EXADCSCLD001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLCLD001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLCLD002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVECLD001 · PVE 1 · .5"]
      N_SWI["🔀 EXASWICLD001 · SWI 1 · .250"]
      N_ANS["🤖 EXAANSCLD001 · Ansible control node · .9"]
      N_RUD["⚙️ EXARUDCLD001 · Rudder configuration management server · .12"]
      N_SLT["🧂 EXASLTCLD001 · Salt master · .22"]
      N_SVR["🗄️ EXASVRCLD002 · Windows Admin Centre · .20"]
      N_PBX["🔌 EXAPBXCLD001 · 3CX PBX · .48"]
      N_UFC["🎛️ EXAUFCCLD001 · UniFi Network Controller · .82"]
      N_DNS["🧭 EXADNSVRK001 · DNS/BIND server (VRK) · .8"]
      N_TMP["📦 Provisioning server (VRK) · .50"]
      N_FWL3["🧱 EXAFWLVRK001 · Firewall WAN face (vRACK) (VRK) · .69"]
    end
    style NEW_CLD fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:CLD:END
```

---

## 🗺️ Topology sketch (draft, hand-drawn — not yet generated)

```mermaid
graph TD
    T_VRK{{"☁️ VRK — vRACK, 192.168.139.0/24"}}
    T_RTR["📡 EXARTRCLD001 · RTR · .1"]
    T_SWI["🔀 EXASWICLD001 · SWI 1 · .250"]
    T_BMC1["🔧 EXABMCCLD001 · BMC 1 · .2"]
    T_BMC2["🔧 EXABMCCLD002 · BMC 2 · .3 — planned"]
    T_PVE1["🗂️ EXAPVECLD001 · PVE 1 · .5"]
    T_PVE2["🗂️ EXAPVECLD002 · PVE 2 · ? — planned"]
    T_OTHER["📎 Other devices — PHN / WKS / LAP / etc."]
    T_ANS["🤖 EXAANSCLD001 · Ansible control node · .9"]
    T_DCS["🗝️ EXADCSCLD001 · DCS 1 · .10"]
    T_NAS["🗃️ EXANASCLD001 · NAS · .19"]
    T_SVR["🗄️ EXASVRCLD002 · Windows Admin Centre · .20"]
    T_SLT["🧂 EXASLTCLD001 · Salt master · .22"]
    T_PBX["🔌 EXAPBXCLD001 · 3CX PBX · .48"]
    T_UFC["🎛️ EXAUFCCLD001 · UniFi Network Controller · .82"]
    T_FWL["🧱 EXAFWLCLD001 · FWL 1 · .253"]

    T_VRK --> T_RTR
    T_RTR --> T_SWI
    T_RTR --> T_BMC1
    T_RTR --> T_BMC2
    T_RTR --> T_PVE1
    T_RTR --> T_PVE2
    T_PVE1 --> T_OTHER
    T_PVE1 --> T_ANS
    T_PVE1 --> T_DCS
    T_PVE1 --> T_NAS
    T_PVE1 --> T_SVR
    T_PVE1 --> T_SLT
    T_PVE1 --> T_PBX
    T_PVE1 --> T_UFC
    T_PVE1 --> T_FWL

    style T_VRK fill:#56B4E9,stroke:#0072B2,color:#000000
    style T_BMC2 fill:#E69F00,stroke:#D55E00,color:#000000,stroke-dasharray: 5 5
    style T_PVE2 fill:#E69F00,stroke:#D55E00,color:#000000,stroke-dasharray: 5 5
```
