# Mermaid GitHub render debug

Throwaway file, not indexed, will be deleted once the CLD/network-diagram.md render bug is found.
kroki.io renders all of these fine — the point is to find which ones GitHub's renderer rejects.
For each one, tell me: renders fine, or "Unable to render rich display"?

## A — plain subgraph, no style, no comment (baseline, matches the pre-existing working pattern)

```mermaid
graph TD
    subgraph OLD_TEST ["Old Network (legacy)"]
      A1["Node one"]
      A2["Node two"]
      A1 --> A2
    end
```

## B — subgraph + style targeting the subgraph ID (this file's current New/Old Network pattern)

```mermaid
graph TD
    subgraph OLD_TEST ["Old Network (legacy)"]
      B1["Node one"]
      B2["Node two"]
      B1 --> B2
    end
    style OLD_TEST fill:#56B4E9,stroke:#0072B2,color:#000000
```

## C — subgraph + a %% comment right after end (isolates the GENERATED marker theory)

```mermaid
graph TD
    subgraph OLD_TEST ["Old Network (legacy)"]
      C1["Node one"]
      C2["Node two"]
      C1 --> C2
    end
    %% GENERATED:NEW-NETWORK:TEST:START
    subgraph NEW_TEST ["New Network (current)"]
      C3["Node three"]
    end
    %% GENERATED:NEW-NETWORK:TEST:END
```

## D — subgraph title WITH emoji + quotes (isolates the emoji-in-subgraph-title theory)

```mermaid
graph TD
    subgraph OLD_TEST ["🕰️ Old Network (legacy)"]
      D1["Node one"]
    end
```

## E — the five node shapes together (isolates the shape-syntax theory)

```mermaid
graph TD
    E1{{"hexagon"}}
    E2[("cylinder")]
    E3(("circle"))
    E4(["stadium"])
    E5>"flag"]
    E1 --> E2 --> E3 --> E4 --> E5
```

## F — style on subgraph AND emoji title AND %% comment together (closest full reproduction)

```mermaid
graph TD
    subgraph OLD_TEST ["🕰️ Old Network (legacy)"]
      F1["Node one"]
    end
    style OLD_TEST fill:#56B4E9,stroke:#0072B2,color:#000000
    %% GENERATED:NEW-NETWORK:TEST:START
    subgraph NEW_TEST ["🆕 New Network (current)"]
      F2[("Node two")]
    end
    style NEW_TEST fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:TEST:END
```

## G — CLD's actual real diagram, copied verbatim, as the control

```mermaid
graph TD
    subgraph OLD_CLD ["🕰️ Old Network (legacy)"]
      INET(("🌐 Internet"))
      FWLCLD{{"EXAFWLVRK001<br/>Firewall / WireGuard Hub<br/>192.168.139.1"}}
      DNS[("EXADNSVRK001<br/>DNS / BIND9 Server<br/>192.168.139.8")]
      PRV[("EXAPRVVRK001<br/>Provisioning Server<br/>192.168.139.50")]
      RUD[("EXARDRCLD001<br/>Rudder Server<br/>192.168.69.12")]
      WAC[("EXASVRCLD002<br/>Windows Admin Centre<br/>192.168.69.20")]
      PBX[("EXAPBXCLD001<br/>3CX Central PBX<br/>192.168.69.48")]
      ANS[("EXAANSCLD001<br/>Ansible Control Node<br/>192.168.69.9")]

      VPN_FAL(["🔗 WireGuard → FAL primary"])
      VPN_ODE(["🔗 WireGuard → ODE EU backup"])
      VPN_BRK(["🔗 WireGuard → BRK NA/APAC backup"])

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
      N_PRV[("EXAPRVCLD001<br/>PRV<br/>.15")]
      N_DCS[("EXADCSCLD001<br/>DCS 1<br/>.10")]
      N_FWL{{"EXAFWLCLD001<br/>FWL 1<br/>.253"}}
      N_FWL2{{"EXAFWLCLD002<br/>FWL 2<br/>.254"}}
      N_PVE[("EXAPVECLD001<br/>PVE 1<br/>.5")]
      N_ANS[("EXAANSCLD001<br/>Ansible control node<br/>.9")]
      N_RDR[("EXARDRCLD001<br/>Rudder configuration management server<br/>.12")]
      N_SVR[("EXASVRCLD002<br/>Windows Admin Centre<br/>.20")]
      N_PBX[("EXAPBXCLD001<br/>3CX PBX<br/>.48")]
      N_UFC[("EXAUFCCLD001<br/>UniFi Network Controller<br/>.82")]
    end
    style NEW_CLD fill:#E69F00,stroke:#D55E00,color:#000000
    %% GENERATED:NEW-NETWORK:CLD:END
```
