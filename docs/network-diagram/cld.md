# Example Music Limited — Cloud (CLD) Network Diagrams

> **Classification:** Internal — Infrastructure
> **Part of:** [`../network-diagram.md`](../network-diagram.md) — see there for the Visual
> Standard (shape/colour/emoji convention), the full emoji legend, and links to every other
> region.

---

## ☁️  — Cloud / Provisioning

**vRACK (`VRK`):** `192.168.139.0/24` · **CLD LAN:** `192.168.69.0/24` · **WireGuard VPN:** `10.0.139.0/24`
**Role:** WireGuard hub — routes to all sites. Central PBX, Ansible, Rudder, WAC.
CLD's own LAN is `192.168.69.0/24` — the vRACK (`192.168.139.0/24`) is a separate site code, `VRK`.  
**Entity:** Example Music Limited · **Landline:** N/A · **Mobile:** N/A

```mermaid
graph TD
    subgraph OLD_CLD ["🕰️ Old Network (legacy)"]
      INET["🌐 Internet"]
      FWLCLD["🧱 EXAFWLVRK001 · Firewall / WireGuard Hub · 192.168.139.1"]
      DNS["🧭 EXADNSVRK001 · DNS / BIND9 Server · 192.168.139.8"]
      PRV["📦 EXAPRVVRK001 · Provisioning Server · 192.168.139.50"]
      RUD["⚙️ EXARDRCLD001 · Rudder Server · 192.168.69.12"]
      WAC["🗄️ EXASVRCLD002 · Windows Admin Centre · 192.168.69.20"]
      PBX["🔌 EXAPBXCLD001 · 3CX Central PBX · 192.168.69.48"]
      ANS["🤖 EXAANSCLD001 · Ansible Control Node · 192.168.69.9"]

      VPN_FAL["🔗 WireGuard → FAL primary"]
      VPN_ODE["🔗 WireGuard → ODE EU backup"]
      VPN_BRK["🔗 WireGuard → BRK NA/APAC backup"]

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
      N_PRV["📦 EXAPRVCLD001 · PRV · .15"]
      N_DCS["🗝️ EXADCSCLD001 · DCS 1 · .10"]
      N_FWL["🧱 EXAFWLCLD001 · FWL 1 · .253"]
      N_FWL2["🧱 EXAFWLCLD002 · FWL 2 · .254"]
      N_PVE["🗂️ EXAPVECLD001 · PVE 1 · .5"]
      N_ANS["🤖 EXAANSCLD001 · Ansible control node · .9"]
      N_RDR["⚙️ EXARDRCLD001 · Rudder configuration management server · .12"]
      N_SVR["🗄️ EXASVRCLD002 · Windows Admin Centre · .20"]
      N_PBX["🔌 EXAPBXCLD001 · 3CX PBX · .48"]
      N_UFC["🎛️ EXAUFCCLD001 · UniFi Network Controller · .82"]
    end
    style NEW_CLD fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:CLD:END
```
