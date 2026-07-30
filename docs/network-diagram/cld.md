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

> **Draft, 2026-07-30.** Robert sketched this by hand as an ASCII diagram to fix the layout/flow he
> wants before any topology view gets built into `generate_network_diagrams.py` proper. This block
> is a first attempt at the same shape in real mermaid, hand-maintained (not marker-wrapped, so
> regeneration won't touch it) — for review, not final. Reads: `VRK` is the vRACK boundary the
> whole CLD network hangs off; `EXARTRCLD001` is the gateway router; `EXASWICLD001`/BMC pair/PVE
> pair all connect off the router; `EXAPVECLD001` hosts everything below it as VMs, fanning out from
> `EXAANSCLD001`. Dashed nodes (`EXABMCCLD002`, `EXAPVECLD002`) are the "not yet in production,
> future expansion" items from Robert's sketch.
>
> **Open questions before this is final** (the original ASCII was genuinely ambiguous at this level
> of detail, called out rather than guessed silently):
> - Does `EXASWICLD001` branch directly off the router, same as the BMC/PVE pairs, or off something
>   else? Drawn as a direct router child here.
> - Is the DCS/NAS/SVR/SLT/PBX/UFC/FWL1 block really a flat fan-out all hanging off
>   `EXAANSCLD001` (drawn that way below, reading the repeated `|--|` ladder in the ASCII as
>   siblings, not a chain), or did you mean something more specific by the ordering?
> - Not included yet, pending your call on whether/how they fit into this view: `EXARDRCLD001`
>   (badge reader), `EXAFWLCLD002` (2nd firewall, confirmed not yet in use), VRK's own real devices
>   (`EXADNSVRK001`, `EXAFWLVRK001` WAN face, the provisioning server), and `EXARUDCLD001` (Rudder —
>   confirmed dormant/reference-only, see `project_rudder_dormant_docs_correction` in memory food for
>   thought on whether it belongs in a *current* topology view at all).

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
    T_ANS --> T_DCS
    T_ANS --> T_NAS
    T_ANS --> T_SVR
    T_ANS --> T_SLT
    T_ANS --> T_PBX
    T_ANS --> T_UFC
    T_ANS --> T_FWL

    style T_VRK fill:#56B4E9,stroke:#0072B2,color:#000000
    style T_BMC2 fill:#E69F00,stroke:#D55E00,color:#000000,stroke-dasharray: 5 5
    style T_PVE2 fill:#E69F00,stroke:#D55E00,color:#000000,stroke-dasharray: 5 5
```
