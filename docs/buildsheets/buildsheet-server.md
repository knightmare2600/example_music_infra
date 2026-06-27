# Buildsheet — Windows Server 2022 (Non-DC)

**Doc ID:** NET-BUILD-SRV-001  
**Last Updated:** 2026-03-05  
**Applies to:** WS2022 Standard / Core member servers — file servers, print servers, RRAS, utility servers  
**Cross-reference:** `buildsheet-domainControllers.md` for DC builds · `buildsheet-workstation.md` (NET-BUILD-WKS-001) for Win11 endpoints  
**Deploy workflow:** `bootstrap/` — `preinit.cmd` → `SetupComplete.cmd` → `PostOOBE.cmd` → `Join-DomainAndBootstrap.ps1`

> ⚠️ **Autounattend files are in `C:\DeployTools\unattend_xml\`**  
> DeployTools share: `\\EXADCSCPH001\DeployTools` (future: DFS `\\jukebox.internal\DeployTools`)

---

## Unattend XML Selection

| OS | File | Notes |
|----|------|-------|
| WS2022 Standard (Desktop Experience) | `autounattend_2022gui.xml` | Default for most member servers |
| WS2022 Standard Core | `autounattend_2022core.xml` | Headless / high-density deployments |
| WS2022 (generic — prompts for edition) | `autounattend2022.xml` | Use when edition is undecided at deploy time |
| WS2025 | `autounattend2025.xml` | New-build servers on supported hardware only |

---

## Hypervisor Detection

`Join-DomainAndBootstrap.ps1` detects platform automatically via WMI `Win32_ComputerSystem.Manufacturer`:

| Detected | Action |
|----------|--------|
| `VMware` | Installs VMware Tools — typical for Fusion lab/test VMs |
| `QEMU` / `Proxmox` | Installs QEMU guest agent |
| Physical / other | Skips guest tools — logs manufacturer string |

---

## Baseline Packages (Chocolatey)

All member servers receive the standard baseline. Role-specific software is added manually or via Rudder post-join.

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

## PowerShell 7 Modules

| Module |
|--------|
| `PSConsoleTools` |
| `PSWriteColor` |
| `PSReadLine` |
| `Terminal-Icons` |
| `CompletionPredictor` |
| `PSWindowsUpdate` |

## RSAT

| Capability |
|-----------|
| `RSAT.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0` |
| `RSAT.DNS.Tools~~~~0.0.1.0` |
| `RSAT.GroupPolicy.Management.Tools~~~~0.0.1.0` |

---

## Role-Specific Notes

### File / NAS-adjacent member servers
- NAS devices (`.32` at each site) are not built via this sheet — see `buildsheet-nas.md` (pending)
- If deploying a Windows file server to supplement NAS, add the `FS-FileServer` role:
  ```powershell
  Install-WindowsFeature FS-FileServer -IncludeManagementTools
  ```

### RRAS / Dial-up Gateway
- Planned for Psion Series 3 and legacy dial-up connectivity (FAL initially)
- Platform TBD: Windows RRAS or Linux SLIP — buildsheet will be created once platform is decided
- Reserve hostname `EXARRSFAL001` / IP `192.168.76.20` (verify against network inventory)
- Add `RemoteAccess` + `RSAT-RemoteAccess` roles if Windows:
  ```powershell
  Install-WindowsFeature RemoteAccess, RSAT-RemoteAccess -IncludeManagementTools
  Install-RemoteAccess -VpnType RoutingOnly
  ```

### Print servers
- Add `Print-Server` + `Print-Internet` roles as required
- Printer drivers should be staged in DeployTools under a `\drivers\` subfolder (create if needed)

### General role addition pattern
```powershell
# List available roles
Get-WindowsFeature | Where-Object { $_.InstallState -eq 'Available' } | Select-Object Name, DisplayName

# Install a role with management tools
Install-WindowsFeature <RoleName> -IncludeManagementTools -IncludeAllSubFeature
```

---

## Build Checklist

> One row per server. Tick columns left to right.  
> **Columns:** HN = hostname · IP = IP confirmed · OS = edition correct · HV = hypervisor tools · SF = OpenSSH · SVC = SSH/RDP services · CH = Chocolatey · CP = packages · P7 = PS7 · PM = modules · RS = RSAT · DJ = domain joined · OU = correct OU · RD = RustDesk · RL = role(s) installed · LPS = LAPS rotated · OK = sign-off

| Hostname | Site | IP | OS | HV | SF | SVC | CH | CP | P7 | PM | RS | DJ | OU | RD | RL | LPS | OK |
|----------|------|----|----|----|----|----|----|----|----|----|----|----|----|----|----|----|-----|
| EXARRSFAL001 | FAL | 192.168.76.20 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | RRAS | [ ] | [ ] |
| *(add as deployed)* | | | | | | | | | | | | | | | | | |

---

## Known Issues

| Hostname | Issue |
|----------|-------|
| *(none at commissioning)* | |

---

*Example Music Limited — Internal Infrastructure Documentation*  
*Do not distribute outside the organisation*  
*Credentials: See password manager — never store passwords in this document*
