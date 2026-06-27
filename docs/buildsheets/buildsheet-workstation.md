# Buildsheet — Windows 11 Workstations & Laptops

**Doc ID:** NET-BUILD-WKS-001  
**Last Updated:** 2026-03-05  
**Applies to:** Windows 11 Pro endpoints — office workstations, touring laptops, hot-desk machines  
**Cross-reference:** `buildsheet-server.md` (NET-BUILD-SRV-001) for WS2022 non-DC nodes  
**Deploy workflow:** `bootstrap/` — `preinit.cmd` → `SetupComplete.cmd` → `PostOOBE.cmd` → `Join-DomainAndBootstrap.ps1`

> ⚠️ **Autounattend files are in `C:\DeployTools\unattend_xml\`**  
> Use `autounattend_win11.xml` for all Win11 builds.  
> DeployTools share: `\\EXADCSCPH001\DeployTools` (future: DFS `\\jukebox.internal\DeployTools`)

---

## Standard Build — Windows 11 Pro

### Unattend XML
| File | Use |
|------|-----|
| `autounattend_win11.xml` | All Win11 Pro workstation and laptop builds |

### Hypervisor Detection
`Join-DomainAndBootstrap.ps1` detects platform automatically via WMI `Win32_ComputerSystem.Manufacturer`:

| Detected | Action |
|----------|--------|
| `VMware` | Installs VMware Tools via Chocolatey |
| `QEMU` / `Proxmox` | Installs QEMU guest agent via Chocolatey |
| Physical / other | Skips guest tools — logs manufacturer string |

> VMware builds are typically **Apple Silicon test VMs via VMware Fusion** (ARM64).  
> Use `autounattend_win11.xml` — the ARM64 WinPE build procedure is in `bootstrap/WinPE ARM64 Build Procedure.md`.

### Baseline Packages (Chocolatey)
All Win11 endpoints receive the standard baseline. Further software is managed by **Rudder** post-join.

| Package | Notes |
|---------|-------|
| `7zip.install` | |
| `notepadplusplus.install` | |
| `hyper` | Terminal |
| `putty.install` | |
| `winscp.install` | |
| `far` | File manager |
| `powershell-core` | PS7 |
| `rustdesk` | Remote support — replaces VNC |
| `dua-cli` | Disk usage |

### PowerShell 7 Modules
| Module | Notes |
|--------|-------|
| `PSConsoleTools` | |
| `PSWriteColor` | |
| `PSReadLine` | |
| `Terminal-Icons` | |
| `CompletionPredictor` | |

### RSAT (workstations only — skip on pure endpoints if not needed)
| Capability | Notes |
|-----------|-------|
| `RSAT.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0` | |
| `RSAT.DNS.Tools~~~~0.0.1.0` | |
| `RSAT.GroupPolicy.Management.Tools~~~~0.0.1.0` | |

---

## Site Checklist

> One row per workstation / laptop. Tick columns left to right.  
> **Columns:** HN = hostname set · IP = static/DHCP confirmed · RD = RDP enabled · SF = OpenSSH feature installed · SB = SSH service auto-start · SR = SSH restart confirmed · CH = Chocolatey · CP = Choco packages · P7 = PS7 · PM = PS7 modules · DJ = domain joined · OU = correct OU · RS = RSAT (if applicable) · RD2 = RustDesk installed · LPS = LAPS password rotated · OK = engineer sign-off

| HN | Site | IP | RD | SF | SB | SR | CH | CP | P7 | PM | DJ | OU | RS | RD2 | LPS | OK |
|----|------|----|----|----|----|----|----|----|----|----|----|----|----|----|-----|----|
| EXAWKSFAL001 | FAL | 192.168.76.100 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXAWKSFAL002 | FAL | 192.168.76.101 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXAWKSFAL003 | FAL | 192.168.76.102 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXALAPFAL001 | FAL | 192.168.76.103 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXASURFAL001 | FAL | DHCP | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | — | [ ] | [ ] | [ ] |
| EXAWKSGLA001 | GLA | 192.168.141.150 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXAWKSGLA002 | GLA | 192.168.141.151 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXALAPGLA001 | GLA | 192.168.141.152 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXASURDUN001 | DUN | 192.168.138.51 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | — | [ ] | [ ] | [ ] |
| EXASURDUN002 | DUN | 192.168.138.52 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | — | [ ] | [ ] | [ ] |
| EXASURPER001 | PER | 192.168.173.71 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | — | [ ] | [ ] | [ ] |
| EXAWKSEDI001 | EDI | 192.168.131.150 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXALAPEDI098 | EDI | 192.168.131.108 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXAWKSLND001 | LND | 192.168.20.150 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXALAPMCR001 | MCR | 192.168.161.150 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXALAPMCR002 | MCR | 192.168.161.151 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXAWKSMCR001 | MCR | 192.168.161.152 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXAWKSMCR002 | MCR | 192.168.161.153 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXAWKSNEW099 | NEW | 192.168.191.161 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ EXPIRED | [ ] |
| EXAWKSBON001 | BON | 192.168.228.151 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXAWKSBON002 | BON | 192.168.228.152 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXALAPBON002 | BON | 192.168.228.153 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXAWKSMUN001 | MUN | 192.168.189.150 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXALAPMUN001 | MUN | 192.168.189.151 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXALAPMUN002 | MUN | 192.168.189.152 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ EXPIRED | [ ] |
| EXALAPBRK001 | BRK | 192.168.136.150 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXALAPMIA001 | MIA | 192.168.135.150 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXAMBPLAX001 | LAX | 192.168.213.41 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | — | [ ] | — | [ ] |
| EXAWKSSYD001 | SYD | 192.168.29.41 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXAWKSAKL001 | AKL | 192.168.93.40 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| EXAWKSMEL001 | MEL | 192.168.61.41 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

> MacBooks (EXAMBP\*) are not built via this sheet — macOS endpoints are enrolled via MDM.  
> Add new endpoints as they are deployed. Rudder handles post-join configuration drift.

---

## Known Issues

| Hostname | Site | Issue |
|----------|------|-------|
| EXAWKSNEW099 | NEW | ⚠️ LAPS password expired — rotate immediately |
| EXALAPMUN002 | MUN | ⚠️ LAPS password expired 61 days — rotate immediately |
| EXALAPBON001 | BON | Disabled for maintenance — do not build until cleared |
| EXAMACLIV001 | LIV | Disabled for maintenance — do not build until cleared |

---

*Example Music Limited — Internal Infrastructure Documentation*  
*Do not distribute outside the organisation*  
*Credentials: See password manager — never store passwords in this document*
