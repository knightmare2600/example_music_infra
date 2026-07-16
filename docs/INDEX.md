# Example Music Limited — Documentation Index

> **GitHub users:** This is the primary documentation index. The repo `README.md` links here.  
> All links below are relative paths and are clickable when browsing on GitHub.

> **Classification:** Internal — Infrastructure  
> **Forest:** `jukebox.internal` · **Domains:** `example.net` · `example.org` · `example.com`  
> **Last Updated:** 2026-07-12  
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
| Set up WireGuard / DC deployment | [active-directory/ad-dc-wireguard-deployment.md](active-directory/ad-dc-wireguard-deployment.md) |
| Set up a RAC emulator VM | [lab/rac-emulator.md](lab/rac-emulator.md) |
| Fix a ZFS disk | [proxmox/zfs-disk-replacement.md](proxmox/zfs-disk-replacement.md) |
| Troubleshoot WireGuard | [wireguard/wireguard-troubleshooting.md](wireguard/wireguard-troubleshooting.md) |
| Verify a change is safe before merging | [../ansible/at_have_ryggen_fri/README.md](../ansible/at_have_ryggen_fri/README.md) |
| Read about a past incident / outage | [INCIDENT-LOG.md](INCIDENT-LOG.md) |
| Plan a site cutover without taking the network down | [network-cutover.md](network-cutover.md) |

---

## Root

| File | Doc ID | Description |
|------|--------|-------------|
| [ExampleMusic_Beginners_Guide.md](ExampleMusic_Beginners_Guide.md) | NET-BEGIN-001 | **Start here** — estate overview, IP/naming conventions, architecture, order of operations, trust but verify, prove a negative |
| [network-inventory.md](network-inventory.md) | NET-INV-001 | Comprehensive device and IP inventory — all sites, all nodes, health status, known issues |
| [site-inventory.md](site-inventory.md) | NET-SITE-001 | Per-site commissioning checklists — build tracking, ZFS status, endpoint and equipment sign-off |
| [INCIDENT-LOG.md](INCIDENT-LOG.md) | OPS-INC-001 | Blameless incident log — chronological, oldest first; what went wrong, root cause, and what changed as a result |
| [linux-recovery-runbook.md](linux-recovery-runbook.md) | OPS-RECOVERY-001 | Recovering a Linux node where the `ansible` account is rejected entirely (console and SSH both) — GRUB rescue mode, unlock, verify |
| [network-diagram.md](network-diagram.md) | NET-DIAG-001 | Per-site network diagrams index — Visual Standard, emoji legend, links to every region file below. Split from one 51-diagram file into per-region files 2026-07-13 (GitHub's mermaid renderer got unreliable with that many diagrams on one page) |
| [network-diagram/cld.md](network-diagram/cld.md) | NET-DIAG-001-CLD | Cloud (CLD) network diagram |
| [network-diagram/scotland.md](network-diagram/scotland.md) | NET-DIAG-001-SCT | Scotland network diagrams (FAL, EDI, GLA, CLY, DUN, PER, ABD) |
| [network-diagram/england.md](network-diagram/england.md) | NET-DIAG-001-ENG | England network diagrams (LND, BIR, MCR, LIV, NEW, SHE, HAL, HUL, COV) |
| [network-diagram/danmark.md](network-diagram/danmark.md) | NET-DIAG-001-DNK | Danmark network diagrams (CPH, ODE, KGE, FAX, KOR, AAR, FRE, FRD, NYB) |
| [network-diagram/deutschland.md](network-diagram/deutschland.md) | NET-DIAG-001-DEU | Deutschland network diagrams (BON, BER, MUN, DRS, DUS) |
| [network-diagram/sverige.md](network-diagram/sverige.md) | NET-DIAG-001-SWE | Sverige network diagram (GOT) |
| [network-diagram/norge.md](network-diagram/norge.md) | NET-DIAG-001-NOR | Norge network diagram (OSL) |
| [network-diagram/nederland.md](network-diagram/nederland.md) | NET-DIAG-001-NLD | Nederland network diagram (AMS) |
| [network-diagram/italia.md](network-diagram/italia.md) | NET-DIAG-001-ITA | Italia network diagram (MIL) |
| [network-diagram/osterreich.md](network-diagram/osterreich.md) | NET-DIAG-001-AUT | Österreich network diagram (VIE) |
| [network-diagram/lebanon.md](network-diagram/lebanon.md) | NET-DIAG-001-LBN | Lebanon network diagram (BRT) |
| [network-diagram/canada.md](network-diagram/canada.md) | NET-DIAG-001-CAN | Canada network diagrams (BRK, TOR, MTL) |
| [network-diagram/united-states.md](network-diagram/united-states.md) | NET-DIAG-001-USA | United States network diagrams (LAX, NYC, NJC, MIA, ATL, CHI, SEA, SFO) |
| [network-diagram/australia.md](network-diagram/australia.md) | NET-DIAG-001-AUS | Australia network diagrams (SYD, MEL) |
| [network-diagram/new-zealand.md](network-diagram/new-zealand.md) | NET-DIAG-001-NZL | New Zealand network diagram (AKL) |
| [network-cutover.md](network-cutover.md) | NET-DIAG-002 | Old-vs-New Network diagram disagreements — what to check before cutover so a network doesn't go down |
| [emojis/README.md](emojis/README.md) | NET-DIAG-003 | Icon legend for network-diagram.md's device symbols — what each emoji means and why |
| [example_music_branding_guide.md](example_music_branding_guide.md) | NET-BRAND-001 | 1980s touring-identity branding guide — livery, colours, fonts |
| [gitleaks_guide.md](gitleaks_guide.md) | NET-TOOL-GITLEAKS-001 | Gitleaks pre-commit secret-scanning guide (Windows) |
| [Example Music Limited — KeePassXC CLI Automation.md](Example%20Music%20Limited%20%E2%80%94%20KeePassXC%20CLI%20Automation.md) | NET-TOOL-KEEPASS-001 | KeePassXC CLI automation — Python wrapper for scripted credential retrieval |
| [solarized-dark-terminal-setup.md](solarized-dark-terminal-setup.md) | NET-TOOL-TERM-001 | Solarized Dark terminal colour setup — fixes low-contrast ANSI colours |
| [ExampleMusic_Procedure_Template.md](ExampleMusic_Procedure_Template.md) | — | Template for writing a new procedure doc — copy this, don't start from scratch |
| `README.md` | — | Repository overview and conventions |
| `INDEX.md` | — | This file |

---

## `active-directory/`

Active Directory configuration, tooling, and DNS management.

| File | Doc ID | Description |
|------|--------|-------------|
| [active-directory/ad-dc-wireguard-deployment.md](active-directory/ad-dc-wireguard-deployment.md) | NET-AD-DC-001 | AD DC promotion procedure + WireGuard site deployment — **required before DC buildsheet sign-off** |
| [active-directory/corporate-livery.md](active-directory/corporate-livery.md) | NET-AD-LIV-001 | GPO-based corporate branding and livery deployment |
| [active-directory/CSVDE_Property_Mapping_Analysis.md](active-directory/CSVDE_Property_Mapping_Analysis.md) | NET-AD-CSV-001 | CSVDE attribute mapping analysis for bulk AD imports |
| [active-directory/demo_data_compatibility_analysis.md](active-directory/demo_data_compatibility_analysis.md) | NET-AD-DEMO-001 | Demo data compatibility analysis for AD test environments |
| [active-directory/easyDNS-TUI-QuickStart.md](active-directory/easyDNS-TUI-QuickStart.md) | NET-AD-DNS-001 | easyDNS TUI quick start — Windows AD DNS management |
| [active-directory/easyDNS-TUI-CHANGELOG.md](active-directory/easyDNS-TUI-CHANGELOG.md) | NET-AD-DNS-002 | easyDNS TUI changelog |
| [active-directory/ExampleMusic_DFS_Procedure.md](active-directory/ExampleMusic_DFS_Procedure.md) | NET-AD-DFS-001 | DFS namespace and replication setup |
| [active-directory/ExampleMusic_UPN_DNS_dnsmasq_Procedure.md](active-directory/ExampleMusic_UPN_DNS_dnsmasq_Procedure.md) | NET-AD-UPN-001 | UPN suffixes, internal DNS zones, and DHCP dynamic DNS |
| [active-directory/ExampleMusic_WAPT_Deployment_Procedure_v1.0.md](active-directory/ExampleMusic_WAPT_Deployment_Procedure_v1.0.md) | NET-AD-WAPT-001 | WAPT server and agent deployment |
| [active-directory/domain-rename-procedure.md](active-directory/domain-rename-procedure.md) | NET-AD-RENAME-001 | Bulk domain name replace after AD forest rebuild |

---

## `ansible/`

Ansible usage and reference — day-to-day operation, not build procedures (those live in `buildsheets/` and `bootstrap/`).

| File | Doc ID | Description |
|------|--------|-------------|
| [ansible/beginners_guide_to_ansible.md](ansible/beginners_guide_to_ansible.md) | NET-ANS-BEGIN-001 | **Start here for Ansible** — inventory/group_vars architecture, `add_host`, idempotency, `ansible.cfg`, sudo/become |
| [ansible/Ansible_Windows_Guide.md](ansible/Ansible_Windows_Guide.md) | NET-ANS-WIN-001 | Day-to-day operation of the Windows playbook set (`windows_bootstrap` chain) |

---

## `bootstrap/`

Procedures for provisioning new sites and nodes from scratch.

| File | Doc ID | Description |
|------|--------|-------------|
| [bootstrap/ipxe-build.md](bootstrap/ipxe-build.md) | NET-BOOT-IPXE-001 | iPXE build and configuration for network booting |
| [bootstrap/TFTPD64_Debian_Headless_Rescue_Guide.md](bootstrap/TFTPD64_Debian_Headless_Rescue_Guide.md) | NET-BOOT-TFTP-001 | TFTPD64 setup on Debian for headless PXE rescue |
| [bootstrap/WinPE ARM64 Build Procedure.md](bootstrap/WinPE%20ARM64%20Build%20Procedure.md) | NET-BOOT-WINPE-001 | WinPE ARM64 build — deployment and recovery media |
| [bootstrap/bootstrapping.md](bootstrap/bootstrapping.md) | NET-BOOT-FULL-001 | Full infrastructure bootstrapping guide — provisioning server, iPXE, first-boot scripts, real command transcripts |
| [bootstrap/ExampleMusic_ExaRescue_ARM64_Build_Procedure.md](bootstrap/ExampleMusic_ExaRescue_ARM64_Build_Procedure.md) | NET-BOOT-RESCUE-001 | ExaRescue arm64 live rescue image build procedure |
| [bootstrap/ExampleMusic_Procedure_iPXE_ARM64_ISO.md](bootstrap/ExampleMusic_Procedure_iPXE_ARM64_ISO.md) | NET-BOOT-IPXEISO-001 | Building an ARM64 iPXE boot ISO |
| [bootstrap/WinPE_DaRT_Build_Guide.md](bootstrap/WinPE_DaRT_Build_Guide.md) | NET-BOOT-DART-001 | WinPE + DaRT 10 build guide |
| [bootstrap/cecho_dartparse_build_guide.md](bootstrap/cecho_dartparse_build_guide.md) | NET-BOOT-CECHO-001 | `cecho`/`dartparse` build procedure — binaries required by WinPE's `startnet.cmd` |
| [arch-pxe-setup.md](arch-pxe-setup.md) | NET-BOOT-ARCH-001 | Arch Linux PXE boot setup |
| [Windows 11 Deployment - Using MDT 8456 with Windows ADK 24H2 (Build 26100) - Deployment Research.pdf](Windows%2011%20Deployment%20-%20Using%20MDT%208456%20with%20Windows%20ADK%2024H2%20%28Build%2026100%29%20-%20Deployment%20Research.pdf) | NET-BOOT-MDT-001 | Windows 11 MDT/ADK deployment research (external reference PDF) |

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

> **Pending:** `buildsheet-nas.md` — NAS build checklist — not yet started. No fixed octet
> convention exists for `NAS` in `address_policy.json`; `devices.csv` currently has it as an
> exception at each site that has one (FAL `.32`, PER `.50`, MEL unset) — confirm per-site via
> `devices.csv`, don't assume `.32`.

---

## `hardware/`

Vendor documentation and hardware reference.

| File | Doc ID | Description |
|------|--------|-------------|
| [hardware/S210-X12RS_UG.pdf](hardware/S210-X12RS_UG.pdf) | HW-REF-001 | Supermicro S210-X12RS user guide |
| [hardware/ExampleMusic_ASAv_Proxmox_Procedure.md](hardware/ExampleMusic_ASAv_Proxmox_Procedure.md) | HW-REF-002 | Cisco ASAv QEMU VM on Proxmox |

---

## `inventory/`

Per-device operational runbooks. Cross-references `network-inventory.md`/`site-inventory.md` for
the device's IP/commissioning record rather than duplicating it.

| File | Doc ID | Description |
|------|--------|-------------|
| [inventory/EXADNSVRK001-dns.md](inventory/EXADNSVRK001-dns.md) | NET-INV-DNS-001 | `EXADNSVRK001` — BIND9 DNS server operations guide |

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
| [proxmox/NET-BMC-001-proxmoxbmc-setup.md](proxmox/NET-BMC-001-proxmoxbmc-setup.md) | NET-BMC-001 | Virtual BMC / IPMI emulation (`proxmoxbmc`) setup |
| [proxmox/Procedure-PVE-Node-Onboarding.md](proxmox/Procedure-PVE-Node-Onboarding.md) | NET-PVE-ONBOARD-001 | PVE node onboarding procedure — `site.yml`'s eight stages, troubleshooting, SSH keypair recovery |
| [proxmox/ExampleMusic_SLIC_Injection_Procedure_v1.0.md](proxmox/ExampleMusic_SLIC_Injection_Procedure_v1.0.md) | NET-PVE-SLIC-002 | Proxmox VM SLIC table injection and SMBIOS spoofing (SeaBIOS VMs) — distinct from NET-LAB-SLIC-001's BIOS-extraction/import procedure, not a duplicate |
| [Proxmox Networking for VMware vSphere admins - Virtualization Howto.pdf](Proxmox%20Networking%20for%20VMware%20vSphere%20admins%20-%20Virtualization%20Howto.pdf) | NET-PVE-VMW-001 | Proxmox networking primer for VMware vSphere admins (external reference PDF) |
| [VM204-disk-migration-runbook.md](VM204-disk-migration-runbook.md) | NET-PVE-DISK-001 | VM 1023 (EXASVRCLD01) disk right-sizing + PBS space-crisis runbook — SATA-hotplug/i440fx gotchas, ZFS zvol sizing, live Oracle DB handling, PBS GC grace-period behaviour (13 July 2026 session, real transcript) |

---

## `proxmox_zabbix_cleanup/`

Self-contained deployment packages (script + systemd service/timer + procedure doc + Zabbix
triggers) for Proxmox VE maintenance automation. Each subdirectory is meant to be a complete,
standalone bundle — see `zabbix_vms_on_wrong_pool/` for the canonical shape.

| File | Doc ID | Description |
|------|--------|-------------|
| [pve-maintenance-automation.md](pve-maintenance-automation.md) | NET-PVE-ZBX-HOOVER-001 | PVE maintenance automation setup — monthly hoover (journals/temps/coredumps/old kernels), Zabbix monitoring. Deployment bundle (`.service`/`.timer`/script) lives in `proxmox_zabbix_cleanup/kernels/` |
| [proxmox_zabbix_cleanup/zabbix_vms_on_wrong_pool/README.md](proxmox_zabbix_cleanup/zabbix_vms_on_wrong_pool/README.md) | NET-PVE-ZBX-POOL-001 | ZFS VM pool-placement audit setup |
| [proxmox_zabbix_cleanup/pve-snapshot-check/PVE-Snapshot-Check-Procedure.md](proxmox_zabbix_cleanup/pve-snapshot-check/PVE-Snapshot-Check-Procedure.md) | NET-PVE-ZBX-SNAP-001 | PVE snapshot check automation setup |

> **Resolved 2026-07-15, per Robert:** `pve-maintenance-automation.md` above is the one exception
> to "each subdirectory is a self-contained bundle" — it lived both at `docs/` root and as
> `proxmox_zabbix_cleanup/kernels/PVE-Trixie-Setup-PFY-Procedure.md`, a genuine content fork (not
> byte-identical). Checked both against the real deployed
> `ansible/playbooks/proxmox/files/pve-monthly-hoover.sh`: root's content and dates matched exactly
> (`proxmox-kernel-*.*.*-*-pve-signed`, 2026-06-09 v1.2.0); the `kernels/` copy had drifted a month
> later onto a shorter, wrong pattern and was missing several sections. Root kept as canonical, the
> `kernels/` doc deleted. While reconciling, found `kernels/pve-monthly-hoover.sh`
> (+ `.service`/`.timer`) — the actual manual-deploy bundle files, not just the doc — had the same
> staleness (pre-PVE-9.x `pve-kernel-*` pattern, silently matches nothing and cleans up no kernels
> on PVE 9.x); synced all three from the canonical `ansible/playbooks/proxmox/files/` copies.

> **Resolved 2026-07-13, per Robert:** two byte-identical stray duplicates deleted rather than
> kept-and-flagged — `PVE-Snapshot-Check-Procedure.md` (formerly at docs/ root, identical to
> `pve-snapshot-check/PVE-Snapshot-Check-Procedure.md` above) and the whole
> `proxmox_zabbix_cleanup/pve-hoover-update/` directory (identical to `kernels/` on every file
> present, and missing `pve-monthly-hoover.timer` besides — `kernels/` was always the more
> complete copy). `kernels/` and `pve-snapshot-check/` above are now each the only copy.

---

## `zabbix_templates/`

Not indexed above (deployment assets — `.xml`/`.yaml` Zabbix template files, not documentation
— same carve-out as `proxmox_zabbix_cleanup/`'s script bundles). Real, consumed files, listed
here for discoverability:

- `WindowsHygiene.xml` — triggers `ansible/playbooks/windows_hygiene/site.yml --tags pagefile`
  by name. See `ansible/playbooks/windows_hygiene/README.md`'s "Zabbix integration" section.
- `zabbix_template_proxmox_nicguard.yaml` — monitors the NIC-guard credentials/units deployed by
  `ansible/playbooks/proxmox/playbooks/40-scripts.yml`. See `ansible/playbooks/proxmox/README.md`.

---

## `testing/`

Repo-wide verification. Lives under `ansible/` rather than `docs/`, unlike
everything else in this index, because it's a runnable tool colocated with
the code it checks (matching every other subsystem's own `README.md` —
`ansible/README.md`, `ansible/playbooks/firewallme/README.md`, etc. — none
of which are indexed here either). Listed anyway, deliberately, because
running it belongs in everyone's workflow, not just people working inside
that one directory.

| File | Doc ID | Description |
|------|--------|-------------|
| [../ansible/at_have_ryggen_fri/README.md](../ansible/at_have_ryggen_fri/README.md) | NET-QA-001 | `at_have_ryggen_fri` — repo-wide verification harness. YAML validity, `ansible-playbook --syntax-check`, file-reference integrity, inventory structure, `add_host` visibility, generated-file freshness, markdown link integrity, cross-file fact consistency, and the estate's bare-metal bootstrap scenarios. Run `ansible/at_have_ryggen_fri/run.sh` before merging anything that touches inventory, `group_vars`, `ansible.cfg`, `benarbejde/`, or `docs/` |

---

## `wireguard/`

WireGuard VPN configuration and troubleshooting.

| File | Doc ID | Description |
|------|--------|-------------|
| [wireguard/NET-VPN-WG-001-wireguard-routing.md](wireguard/NET-VPN-WG-001-wireguard-routing.md) | NET-VPN-WG-001 | WireGuard inter-hub routing — fabric provisioning, AllowedIPs, re-keying |
| [wireguard/wireguard-troubleshooting.md](wireguard/wireguard-troubleshooting.md) | NET-VPN-WG-002 | WireGuard troubleshooting guide — tunnel diagnostics, re-keying, common failures |
| [wireguard/Troubleshooting-fwl-post-v2v.md](wireguard/Troubleshooting-fwl-post-v2v.md) | NET-FW-TROUBLESHOOT-001 | Firewall recovery after V2V migration — nftables/NetworkManager on Proxmox VE |

---

## Personal Tooling (Porting Work)

Not Example Music infrastructure — build/release docs for Robert's own side-project ARM64
ports and forks, listed in root `README.md`'s ["Porting Work"](../README.md#porting-work)
table. Kept here rather than deleted (still actively built/maintained; the upstream doesn't
maintain the original much) and catalogued rather than left as an orphan.

| File | Doc ID | Description |
|------|--------|-------------|
| [ColorEcho GitHub Actions Build & Release Documentation.md](ColorEcho%20GitHub%20Actions%20Build%20%26%20Release%20Documentation.md) | — | GitHub Actions build/release pipeline for `ColorEcho` (ARM64 port, patches merged upstream) — win-x64/win-arm64 matrix build, release automation |

---

## Document ID Registry

| Series | Scope |
|--------|-------|
| `NET-BEGIN-*` | Beginner's guide and onboarding |
| `NET-INV-*` | Inventory documents |
| `NET-SITE-*` | Site commissioning records |
| `NET-AD-*` | Active Directory and DNS |
| `NET-BOOT-*` | Bootstrap and provisioning |
| `NET-BUILD-*` | Buildsheets |
| `NET-LAB-*` | Lab / wargaming |
| `NET-MGMT-*` | Management and automation |
| `NET-PVE-*` | Proxmox VE |
| `NET-RAC-*` | Remote access console / BMC |
| `NET-BMC-*` | Virtual BMC / IPMI emulation |
| `NET-VPN-WG-*` | WireGuard |
| `NET-FW-*` | Firewall troubleshooting |
| `HW-REF-*` | Hardware reference |
| `NET-DIAG-*` | Network diagrams |
| `NET-BRAND-*` | Branding / livery |
| `NET-TOOL-*` | General tooling guides (not estate-specific infra) |
| `OPS-INC-*` | Incident log |

---

*Example Music Limited — Internal Infrastructure Documentation*  
*Do not distribute outside the organisation*
