# Example Music Limited — Documentation Index

> **GitHub users:** This is the primary documentation index. The repo `README.md` links here.  
> All links below are relative paths and are clickable when browsing on GitHub.

> **Classification:** Internal — Infrastructure  
> **Forest:** `jukebox.internal` · **Domains:** `example.net` · `example.org` · `example.com`  
> **Last Updated:** 2026-03-06  
> **Credentials:** See password manager — never store passwords in documentation

---

## Quick Reference

| I need to… | Go to |
|------------|-------|
| Find a site's IP / device details | [network-inventory.md](network-inventory.md) |
| Check commissioning status of a site | [site-inventory.md](site-inventory.md) |
| Build a domain controller | [buildsheets/buildsheet-domainControllers.md](buildsheets/buildsheet-domainControllers.md) |
| Build a workstation or laptop | [buildsheets/buildsheet-workstation.md](buildsheets/buildsheet-workstation.md) |
| Build a member server | [buildsheets/buildsheet-server.md](buildsheets/buildsheet-server.md) |
| Build a Proxmox node | [buildsheets/buildsheet-pve.md](buildsheets/buildsheet-pve.md) |
| Build a firewall | [buildsheets/buildsheet-firewall.md](buildsheets/buildsheet-firewall.md) |
| Build the Windows Admin node | [buildsheets/buildsheet-winadmin.md](buildsheets/buildsheet-winadmin.md) |
| Build the Rudder server | [buildsheets/buildsheet-rudder.md](buildsheets/buildsheet-rudder.md) |
| Set up WireGuard / DC deployment | [bootstrap/ad-dc-wireguard-deployment.md](bootstrap/ad-dc-wireguard-deployment.md) |
| Set up a RAC emulator VM | [lab/rac-emulator.md](lab/rac-emulator.md) |
| Fix a ZFS disk | [proxmox/zfs-disk-replacement.md](proxmox/zfs-disk-replacement.md) |
| Troubleshoot WireGuard | [wireguard/wireguard-troubleshooting.md](wireguard/wireguard-troubleshooting.md) |

---

## Root

| File | Doc ID | Description |
|------|--------|-------------|
| [network-inventory.md](network-inventory.md) | NET-INV-001 | Comprehensive device and IP inventory — all sites, all nodes, health status, known issues |
| [site-inventory.md](site-inventory.md) | NET-SITE-001 | Per-site commissioning checklists — build tracking, ZFS status, endpoint and equipment sign-off |
| `README.md` | — | Repository overview and conventions |
| `INDEX.md` | — | This file |

---

## `active-directory/`

Active Directory configuration, tooling, and DNS management.

| File | Doc ID | Description |
|------|--------|-------------|
| [active-directory/corporate-livery.md](active-directory/corporate-livery.md) | NET-AD-LIV-001 | GPO-based corporate branding and livery deployment |
| [active-directory/CSVDE_Property_Mapping_Analysis.md](active-directory/CSVDE_Property_Mapping_Analysis.md) | NET-AD-CSV-001 | CSVDE attribute mapping analysis for bulk AD imports |
| [active-directory/demo_data_compatibility_analysis.md](active-directory/demo_data_compatibility_analysis.md) | NET-AD-DEMO-001 | Demo data compatibility analysis for AD test environments |
| [active-directory/easyDNS-TUI-QuickStart.md](active-directory/easyDNS-TUI-QuickStart.md) | NET-AD-DNS-001 | easyDNS TUI quick start — Windows AD DNS management |
| [active-directory/easyDNS-TUI-CHANGELOG.md](active-directory/easyDNS-TUI-CHANGELOG.md) | NET-AD-DNS-002 | easyDNS TUI changelog |

---

## `bootstrap/`

Procedures for provisioning new sites and nodes from scratch.

| File | Doc ID | Description |
|------|--------|-------------|
| [bootstrap/ad-dc-wireguard-deployment.md](bootstrap/ad-dc-wireguard-deployment.md) | NET-AD-DC-001 | AD DC promotion procedure + WireGuard site deployment — **required before DC buildsheet sign-off** |
| [bootstrap/ipxe-build.md](bootstrap/ipxe-build.md) | NET-BOOT-IPXE-001 | iPXE build and configuration for network booting |
| [bootstrap/TFTPD64_Debian_Headless_Rescue_Guide.md](bootstrap/TFTPD64_Debian_Headless_Rescue_Guide.md) | NET-BOOT-TFTP-001 | TFTPD64 setup on Debian for headless PXE rescue |
| [bootstrap/WinPE ARM64 Build Procedure.md](bootstrap/WinPE%20ARM64%20Build%20Procedure.md) | NET-BOOT-WINPE-001 | WinPE ARM64 build — deployment and recovery media |

**DeployTools scripts** (hosted on `\\EXADCSCPH001\DeployTools` — future DFS):

| File | Description |
|------|-------------|
| `panther/Join-DomainAndBootstrap.ps1` | Post-OOBE domain join, site detection, hypervisor detection, Chocolatey, RustDesk, RSAT, PS7 modules |
| `panther/PostOOBE.cmd` | Maps Z: to DeployTools, launches bootstrap script |
| `panther/SetupComplete.cmd` | First-boot — OpenSSH, RDP, firewall rules |
| `winpe_deploy.cmd` | WinPE offline image apply, GPT partitioning, bootloader |
| `unattend_xml/autounattend_win11.xml` | Win11 Pro unattended install |
| `unattend_xml/autounattend_2022gui.xml` | WS2022 Desktop Experience unattended |
| `unattend_xml/autounattend_2022core.xml` | WS2022 Core unattended |
| `unattend_xml/autounattend2022.xml` | WS2022 generic (prompts for edition) |
| `unattend_xml/autounattend2025.xml` | WS2025 unattended |

---

## `buildsheets/`

Per-role build checklists. Each sheet cross-references the relevant
runbook in `bootstrap/`, `proxmox/`, or `management/`. A checkbox on
a buildsheet feeds up to the commissioning record in `site-inventory.md`.

| File | Doc ID | Description |
|------|--------|-------------|
| [buildsheets/buildsheet-domainControllers.md](buildsheets/buildsheet-domainControllers.md) | NET-BUILD-DCS-001 | DC build checklist — all sites, grouped by region · references NET-AD-DC-001 |
| [buildsheets/buildsheet-workstation.md](buildsheets/buildsheet-workstation.md) | NET-BUILD-WKS-001 | Win11 Pro workstation and laptop build checklist — all sites |
| [buildsheets/buildsheet-server.md](buildsheets/buildsheet-server.md) | NET-BUILD-SRV-001 | WS2022 Standard / Core member server build checklist |
| [buildsheets/buildsheet-firewall.md](buildsheets/buildsheet-firewall.md) | NET-BUILD-FWL-001 | Firewall build checklist — all sites with known hardware |
| [buildsheets/buildsheet-pve.md](buildsheets/buildsheet-pve.md) | NET-BUILD-PVE-001 | Proxmox VE node build checklist |
| [buildsheets/buildsheet-rudder.md](buildsheets/buildsheet-rudder.md) | NET-BUILD-RUDDER-001 | Rudder server build checklist + inline install procedure |
| [buildsheets/buildsheet-winadmin.md](buildsheets/buildsheet-winadmin.md) | NET-BUILD-WIN-001 | Windows Admin Centre node build checklist (Desktop Experience) |

> **Pending:** `buildsheet-nas.md` — NAS build checklist (`.32` at each site) — not yet started

---

## `hardware/`

Vendor documentation and hardware reference.

| File | Doc ID | Description |
|------|--------|-------------|
| [hardware/S210-X12RS_UG.pdf](hardware/S210-X12RS_UG.pdf) | HW-REF-001 | Supermicro S210-X12RS user guide |

---

## `lab/`

Lab, wargaming, and test environment tooling. Not for production use.

| File | Doc ID | Description |
|------|--------|-------------|
| [lab/rac-emulator.md](lab/rac-emulator.md) | NET-RAC-001 | HPE iLO Redfish emulator runbook — setup, API reference, Ansible usage · full Redfish endpoint appendix |
| [lab/rac-setup.sh](lab/rac-setup.sh) | — | Automated setup script for `EXARAC<SITE>00N` RAC emulator VMs — dynamically allocates BMC pool IP |

---

## `management/`

Configuration management, automation, and orchestration.

| File | Doc ID | Description |
|------|--------|-------------|
| [management/rudder-setup.md](management/rudder-setup.md) | NET-MGMT-RUDDER-001 | Rudder full configuration guide — techniques, rules, node management |
| [management/Example Music — Keeping Three Ansible Nodes in Sync.md](management/Example%20Music%20—%20Keeping%20Three%20Ansible%20Nodes%20in%20Sync.md) | NET-MGMT-ANS-001 | Ansible multi-node synchronisation patterns |

---

## `proxmox/`

Proxmox VE administration, storage, networking, and planning documents.

| File | Doc ID | Description |
|------|--------|-------------|
| [proxmox/pve-create-vm.md](proxmox/pve-create-vm.md) | NET-PVE-VM-001 | VM creation procedure — includes `create-vm.py` usage |
| [proxmox/pve-networking.md](proxmox/pve-networking.md) | NET-PVE-NET-001 | Proxmox networking configuration — bridges, VLANs, WireGuard |
| [proxmox/pve-letsencrypt.md](proxmox/pve-letsencrypt.md) | NET-PVE-LE-001 | Let's Encrypt certificate setup for Proxmox web UI |
| [proxmox/proxmox-storage.md](proxmox/proxmox-storage.md) | NET-PVE-STG-001 | Proxmox storage configuration — ZFS, LVM, directories |
| [proxmox/zfs-disk-replacement.md](proxmox/zfs-disk-replacement.md) | NET-PVE-ZFS-001 | ZFS disk replacement procedure — RAID1 hot swap |
| [proxmox/zfs-raid0-to-raid1.md](proxmox/zfs-raid0-to-raid1.md) | NET-PVE-ZFS-002 | ZFS RAID0 → RAID1 upgrade procedure · **in progress at FAL** |
| [proxmox/slic-bios-proxmox.md](proxmox/slic-bios-proxmox.md) | NET-LAB-SLIC-001 | SLIC/MSDM BIOS extraction and Proxmox VM injection — lab/wargaming |
| [proxmox/virtio-driver-disk.md](proxmox/virtio-driver-disk.md) | NET-PVE-VIO-001 | VirtIO driver disk preparation for Windows VMs |
| [proxmox/v2v-scenario-walkthroughs.md](proxmox/v2v-scenario-walkthroughs.md) | NET-PVE-V2V-001 | V2V migration walkthroughs — physical/VMware/Hyper-V to Proxmox |
| [proxmox/proxmox-dcm-pbs-planning.md](proxmox/proxmox-dcm-pbs-planning.md) | NET-PVE-PBS-001 | Proxmox Backup Server and DC migration planning |
| [proxmox/pegaprox-evaluation.md](proxmox/pegaprox-evaluation.md) | NET-PVE-EVAL-001 | PegaProx evaluation notes |
| [proxmox/pdm-enterprise-proposal.md](proxmox/pdm-enterprise-proposal.md) | NET-PVE-PDM-001 | Proxmox Datacenter Manager enterprise proposal |

---

## `wireguard/`

WireGuard VPN configuration and troubleshooting.

| File | Doc ID | Description |
|------|--------|-------------|
| [wireguard/wireguard-troubleshooting.md](wireguard/wireguard-troubleshooting.md) | NET-WG-001 | WireGuard troubleshooting guide — tunnel diagnostics, re-keying, common failures |

---

## Document ID Registry

| Series | Scope |
|--------|-------|
| `NET-INV-*` | Inventory documents |
| `NET-SITE-*` | Site commissioning records |
| `NET-AD-*` | Active Directory and DNS |
| `NET-BOOT-*` | Bootstrap and provisioning |
| `NET-BUILD-*` | Buildsheets |
| `NET-LAB-*` | Lab / wargaming |
| `NET-MGMT-*` | Management and automation |
| `NET-PVE-*` | Proxmox VE |
| `NET-RAC-*` | Remote access console / BMC |
| `NET-WG-*` | WireGuard |
| `HW-REF-*` | Hardware reference |

---

*Example Music Limited — Internal Infrastructure Documentation*  
*Do not distribute outside the organisation*
