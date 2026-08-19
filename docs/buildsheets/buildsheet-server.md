# Buildsheet — Windows Server 2022 (Non-DC)

**Doc ID:** NET-BUILD-SRV-001  
**Last Updated:** 2026-03-05  
**Applies to:** WS2022 Standard / Core member servers — file servers, print servers, utility servers  
**Cross-reference:** `buildsheet-domainControllers.md` for DC builds · `buildsheet-workstation.md` (NET-BUILD-WKS-001) for Win11 endpoints  
**Deploy workflow:** unattend XML → OpenSSH reachable → `ansible/playbooks/windows_bootstrap/site.yml`
(`preinit.cmd`/`SetupComplete.cmd`/`PostOOBE.cmd`/`Join-DomainAndBootstrap.ps1` are a
historical, pre-Ansible artefact — see `docs/bootstrap/bootstrapping.md` — not the live path)

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

`ansible/playbooks/windows_bootstrap/tasks/site_detection.yml` (Stage 1) detects platform
automatically, via WMI `Win32_ComputerSystem.Manufacturer` plus loaded-driver signatures:

| Detected | Action |
|----------|--------|
| `VMware` | Installs VMware Tools — typical for Fusion lab/test VMs |
| `KVM` | Installs QEMU guest agent — real value for both QEMU and Proxmox VMs (driver signatures/manufacturer string `qemu`/`kvm` both resolve to the literal `"KVM"`, not `QEMU` or `Proxmox`) |
| Physical / other | Skips guest tools — logs manufacturer string |

---

## Baseline Packages (Chocolatey)

All member servers receive the standard baseline (`choco_packages_common`,
`40-choco-packages.yml`). Role-specific software is added manually or via Salt (Chocolatey-driven
installs and local-account housekeeping for WKS/LAP/SUR/SVR/DCS — see
`buildsheet-salt-minion.md`/`salt/README.md`), not Rudder — there is no automated Rudder-agent
onboarding path for Windows today.

| Package | Notes |
|---------|-------|
| `7zip.install` | |
| `notepadplusplus.install` | |
| `hyper` | Terminal |
| `putty.install` | |
| `winscp.install` | |
| `far` | File manager |
| `powershell-core` | PS7 |
| `rustdesk.install` | Remote support — replaces VNC |
| `edit` | |
| `sdelete` | |
| `wget` | |
| `busybox` | |
| `vcredist-all` | |
| `dotnetfx` | |
| `windirstat` | |
| `dua-cli` | Disk usage — NOT a Chocolatey package; fetched directly from its GitHub release by `tasks/dua_cli.yml`, dropped at `C:\Windows\dua.exe` |

`sysinternals` was removed from this list 2026-08-14 after a live SHA256 checksum-mismatch failure against `EXADCSLAX001` (upstream `download.sysinternals.com` zip updated in place without the Chocolatey package's checksum catching up). Individual Sysinternals tools (ProcExp, ADExplorer, etc.) are instead deployed as committed binaries under `ansible/playbooks/windows_bootstrap/playbooks/files/{x86_64,arm64}/` — same `50-binaries.yml` mechanism as `dua-cli` above.

## PowerShell 7 Modules

| Module |
|--------|
| `PSConsoleTools` |
| `PSWindowsUpdate` |
| `PSWriteColor` |
| `PSReadLine` |
| `Terminal-Icons` |
| `CompletionPredictor` |
| `NerdFonts` |

## RSAT

Server OS installs RSAT via `Install-WindowsFeature` (Server Manager), not the
`Add-WindowsCapability` mechanism client OSes use (see `buildsheet-workstation.md` for that one):

| Feature |
|---------|
| `RSAT-AD-PowerShell` |
| `RSAT-AD-AdminCenter` |
| `RSAT-ADDS-Tools` |
| `RSAT-DNS-Server` |
| `GPMC` |

---

## Role-Specific Notes

### File / NAS-adjacent member servers
- NAS devices (`.19` at each site, standard slot added 2026-07-19) are not built via this sheet — see `buildsheet-nas.md` (pending)
- If deploying a Windows file server to supplement NAS, add the `FS-FileServer` role:
  ```powershell
  Install-WindowsFeature FS-FileServer -IncludeManagementTools
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
