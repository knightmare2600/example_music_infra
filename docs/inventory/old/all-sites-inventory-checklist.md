> **ARCHIVE** — This document is superseded by current docs in `docs/` and `docs/inventory/`.
> Data here is intentionally stale (pre-2026-06-26). Do not use for operational reference.

# Example Music — All-Site Infrastructure Inventory & Checklist

**Version:** 1.0  
**Date:** 2026-03-17  
**Author:** IT Operations Team  

---

## Introduction

This document provides a comprehensive overview of all Example Music sites, servers, and infrastructure nodes. It is intended for use by operations, network, and systems teams to track deployment status, provisioning, and lifecycle management of production and test environments.

The checklist includes:

- Firewall (FWL) and core services (DCS) coverage per site  
- Server deployment status (SVR001–SVR003)  
- PBX, SBC, PVE, and UNIX/Linux hosts  
- Node-level details including IP addresses, OS, and purpose  
- Notes on special considerations or site-specific details  

This document is a **living record** and must be updated whenever infrastructure changes occur.

---

Checkboxes indicate deployment status:

- `[ ]   = Not started / pending`
- `[WIP] = Work in progress`
- `[N/A] = Not applicable`
- `[NB]  = Nota bene`
- `[Y]   = Completed`

# Example Music – All-Site Inventory Checklist

This document provides a **comprehensive view of infrastructure deployment, work-in-progress, and planned nodes** across all sites in the Example Music environment.  

It is intended as **production-ready documentation** for operations, auditing, and planning purposes.



## Site Inventory Overview

> # Example Music – All-Site Inventory Checklist

This document provides a **comprehensive view of infrastructure deployment, work-in-progress, and planned nodes** across all sites in the Example Music environment.  

It is intended as **production-ready documentation** for operations, auditing, and planning purposes.

**Legend:**

| Symbol | Meaning                   |
| ------ | ------------------------- |
| Y      | Done                      |
| N/A    | Not Applicable            |
| WIP    | In process of being built |
| NB     | See Note                  |

---

## Site Inventory Overview

| Site | FWL  | DCS  | SVR001 | SVR002 | SVR003 | PBX  | SBC  | PVE  | NIX  | Notes                                                        |
| ---- | ---- | ---- | ------ | ------ | ------ | ---- | ---- | ---- | ---- | ------------------------------------------------------------ |
| BRK  | WIP  |      |        |        |        | N/A  | -    |      |      |                                                              |
| CLD  | *    |      |        |        |        | WIP  | N/A  | Y    |      | The infra is a legal fiction as CLD is actually my house.    |
| FAL  | X    |      |        |        |        | N/A  |      |      |      |                                                              |
| NEW  | X    |      |        |        |        | N/A  |      |      |      |                                                              |
| SYD  |      |      |        |        |        | N/A  |      |      |      |                                                              |
| MEL  |      |      |        |        |        | N/A  |      |      |      |                                                              |
| TOR  |      |      |        |        |        | N/A  |      |      |      |                                                              |
| AKL  |      |      |        |        |        | N/A  |      |      |      |                                                              |
| LAX  |      |      |        |        |        | N/A  |      |      |      |                                                              |
| MIA  | WIP  |      |        |        |        | N/A  |      |      |      |                                                              |
| MCR  | X    |      |        |        |        | N/A  |      |      |      |                                                              |
| NEW  | X    |      |        |        |        | N/A  |      |      |      |                                                              |
| LIV  | X    |      |        |        |        | N/A  |      |      |      |                                                              |
| LON  | X    |      |        |        |        | N/A  |      |      |      |                                                              |
| DUN  |      |      |        |        |        | N/A  |      |      |      |                                                              |
| ABD  |      |      |        |        |        | N/A  |      |      |      |                                                              |
| EDI  | X    |      |        |        |        | N/A  |      |      |      |                                                              |
| GLA  | X    |      |        |        |        | N/A  |      |      |      |                                                              |
| HUL  | WIP  |      |        |        |        | N/A  |      |      |      |                                                              |
| BIR  | WIP  |      |        |        |        | N/A  |      |      |      |                                                              |
| ATL  | WIP  |      |        |        |        | N/A  |      |      |      |                                                              |
| CHI  | WIP  |      |        |        |        | N/A  |      |      |      |                                                              |
| NYC  | WIP  |      |        |        |        | N/A  |      |      |      |                                                              |
| NJC  | WIP  |      |        |        |        | N/A  |      |      |      |                                                              |
| ODE  | Y    | Y    |        |        |        | N/A  |      |      |      | Odense is domain joined and now an FSMO DC too               |
| KGE  | WIP  |      |        |        |        | N/A  |      |      |      |                                                              |
| CPH  | Y    | NB   |        |        |        | N/A  |      |      |      | It exists but is broken. Rebuild once FAL/ODE are going      |
| FAX  | WIP  |      |        |        |        | N/A  |      |      |      |                                                              |
| KOR  | WIP  |      |        |        |        | N/A  |      |      |      |                                                              |
| AAR  |      |      |        |        |        | N/A  |      |      |      |                                                              |
| GOT  | WIP  |      |        |        |        | N/A  |      |      |      |                                                              |
| OSL  | WIP  |      |        |        |        | N/A  |      |      |      |                                                              |
| BON  | Y    |      |        |        |        | N/A  |      |      |      |                                                              |
| BER  |      |      |        |        |        | N/A  |      |      |      |                                                              |
| VIE  |      |      |        |        |        | N/A  |      |      |      |                                                              |
| MIL  |      |      |        |        |        | N/A  |      |      |      |                                                              |
| AMS  | WIP  |      |        |        |        | N/A  |      |      |      |                                                              |
| MEL  | WIP  |      |        |        |        | N/A  |      |      |      |                                                              |
| PRV  | NB   | NB   | NB     | NB     | NB     | N/A  | N/A  | NB   | NB   | EXAPRVR001 Bootstrap/Provisioning node 192.168.139.50 There is no "Production" infra here, such as SBCs, PBXes, etc. |
## Node Details

| Node Name    | Function                      | IP Address     | Notes/Fate                                                   |
| ------------ | ----------------------------- | -------------- | ------------------------------------------------------------ |
| EXASVRCLD001 | Windows Admin Centre deployed | 192.168.139.20 | Has "feet" in all networks, so can reach all nodes inside LANs |
| EXAANSCLD001 | Ansible Server                | 192.168.139.49 | Originally called AlexAnsible, rename and v2v this           |
| EXASVRCLD003 | Rudder server                 | 192.168.139.22 | Linux node to be built - agents to be deployed on all nodes  |
| EXACLDPBX001 | 3CX PBX                       | 192.168.139.48 | Uses IP of SBC in CLD but is the company PBX                 |
| EXANASFAL001 | NAS                           | 192.168.76.32  | FreeNAS 13.0-U6 (build as a VM then decommission)            |
| EXATARFAL001 | Tape archiver                 | 192.168.76.33  | Solaris Embedded, build a new OpenIndiana device and migrate NFS to it |
| EXASRVCLY001 | Rocky Linux server            | 192.168.41.20  | Oracle DB build then decommission                            |
| EXANIXPER001 | Solaris 11.5                  | 192.168.173.40 | MIDI/Music archive server                                    |
| EXANASPER001 | Synology NAS                  | 192.168.173.50 | Same as FreeNAS, use as a learning tool                      |
| EXASRVAKL001 | WS2022 server                 | 192.168.93.20  | Local server - migrate data to DCS and decommission          |
| EXASRVBIR001 | Rocky Linux server            | 192.168.121.20 | Oracle DB                                                    |
| EXASRVLIV001 | Rocky Linux server            | 192.168.151.20 | Oracle DB (combine into cloud-hosted DB server with separate DBs) |
| EXASRVNEW001 | Rocky Linux server            | 192.168.191.20 | Oracle DB                                                    |
| EXASRVBER001 | WS2019 legacy app server      | ??             | Upgrade to 2022 and move bespoke apps here                   |
| EXANIXBER001 | Debian 12 server              | ??             | Debian Trixie is out, upgrade, runs Samba, migrate data to DCS |
| EXASRVLAX001 | Rocky Linux server            | 192.168.213.20 | Local services/DB                                            |
| EXASRVMEL001 | WS2022 server                 | 192.168.61.20  | Local file/print - migrate to DCS and set up file & print sharing |

**End of All-Site Inventory Checklist**


---

## Usage & Maintenance Notes

- Update this checklist **whenever a node is provisioned, decommissioned, or migrated**.  
- *Use `Y` for completed deployments, `WIP` for WIP, `<blank>` for pending, and `NB` for special attention notes.*  
- This file **must** be **stored in the version-controlled infrastructure repository** for auditing and team coordination.  
- When provisioning new sites, copy the `PRV` row as a template.  

---

*Example Music Limited — Internal Infrastructure Documentation*  
*Do not distribute outside the organisation*  
*Credentials: See password manager — never store passwords in this document*
