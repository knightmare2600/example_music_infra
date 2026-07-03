# Example Music Limited — WinPE + DaRT 10 Build Guide

> **Classification:** Internal — Infrastructure  
> **Applies to:** Build box (fresh Win11, 60 GB+ free disk, Chocolatey installed)  
> **Target ADK:** `10.1.26100.2454` (Windows 11 24H2)  
> **Build output path:** `C:\WinPE_Build\`  
> **Credentials:** See password manager — do **not** store passwords in this document  

---

## Overview

A technician has just installed Windows 11 and needs to build a WinPE image with DaRT 10 integrated, ensuring compatibility with modern ADK (10.1.26100.2454). This procedure covers the full repeatable pipeline from a clean machine to a PXE-deployable WIM.

---

## References

The following links were helpful in confirming the nuance and crucially the install order and post-install fixes needed to allow x86_64 DaRT images to be integrated:

- <https://github.com/FriendsOfMDT/PSD/issues/83>
- <https://github.com/monosoul/MS-Deployment-toolkit-scripts/tree/master>
- <https://www.deploymentresearch.com/windows-11-deployment-using-mdt-8456-with-windows-adk-24h2-build-26100/>
- <https://www.reddit.com/r/PowerShell/comments/bkbxve/dart_10_setup_script/>
- <https://forums.mydigitallife.net/threads/ms-dart-offline-integration-tool-for-windows-7-8-1-10-and-11.87865/>
- <https://www.osdcloud.com/osdcloud-v1/osdcloud/setup>
- <https://learn.microsoft.com/en-us/windows-hardware/get-started/adk-install>
- <https://forums.powershell.org/t/manual-install-ps-modules-psmodulepath/21453/2>
- <https://chentiangemalc.wordpress.com/2022/11/29/dart-doesnt-detect-adk/>
- <https://learn.microsoft.com/en-us/intune/configmgr/mdt/use-the-mdt>
- https://github.com/FriendsOfMDT/PSD/issues/83
- https://byteittech.com/microsoft-diagnostics-and-recovery-toolset/
- https://www.deploymentresearch.com/software-assurance-pays-off-remote-connection-to-winpe-during-mdt-sccm-deployments/
- https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/winpe-add-packages--optional-components-reference?view=windows-11
- https://learn.microsoft.com/en-us/microsoft-desktop-optimization-pack/dart-v10/how-to-recover-remote-computers-by-using-the-dart-recovery-image-dart-10
- https://execmgrnet.wordpress.com/2016/02/02/dart-remote-control-winpe-the-nice-way/
- https://www.cb-net.co.uk/microsoft-articles/configmgr/configmgr-dart-8-1-remote-viewer-and-windows-pe/

**WinPE tools repo:** `<<winpe tools repo>>`

---

## Prerequisites

### Required files

Obtain and place in `C:\WinPE_Build\sources\` before running `Build-WinPE.ps1`:

```
adksetup.exe
adkwinpesetup.exe
MSDaRT100.msi
DaRT10.ps1          (optional — wizard-generated script)
Dart_w11.tpk        (from MDOP ISO — DaRT WinPE payload, ZIP renamed)
PowerShell-7.4.13-win-x64.zip
PowerShell-7.4.13-win-arm64.zip   (ARM64 build box only)
```

### Verified file hashes (SHA256)

```
adksetup.exe      7F61E29F2314BCDD7E0ABF67A8367D83A05AA4A7B9223F85C5FD2582A35CC6F4
adkwinpesetup.exe ADF53CA21CAE36821E0A8F3C31546752B9CE066944DE1D4F1673E491831255E2
MSDaRT100.msi     0D193A22DCC4AB3B53940281D65CB4BDAE9F20AA21ACFD8459AE1B049BA9CDB7
```

### Tools overlay — files required in `tools\amd64\Windows\System32\`

| File | Required | Source |
|------|----------|--------|
| `cecho.exe` | Yes | Built from `cecho.cpp` — see cecho build guide |
| `dartparse.exe` | Yes | Internal tool — see cecho build guide |
| `netstart.exe` | Recommended | Extract from `Dart_w11.tpk` → `1\Windows\System32\` |
| `bginfo.exe` | Optional | Sysinternals |
| `winpe.bgi` | Optional | Generated on Win11 — see Step 9 |
| `wallpaper.bmp` | Optional | Any 24-bit BMP |

> **Note:** Every tool called without a full path in `startnet.cmd` must be in `tools\amd64\Windows\System32\`. The build script mirrors this tree onto the WIM
> root so those files land in `X:\Windows\System32\` which is on `PATH`.

---

## Step 1 — Install ADK

Run `adksetup.exe` and select **Deployment Tools** only.

```cmd
adksetup.exe
```

Select:
- Deployment Tools

---

## Step 2 — Install WinPE Add-on

```cmd
adkwinpesetup.exe
```

Accept defaults. This installs the WinPE optional components and base WIM.

---

## Step 3 — Fix DaRT Detection Issues

ADK 24H2 omits x86 WinPE folders that both MDT and DaRT expect. Run the helper script which handles all of this automatically:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\Fix-MDTforADK24H2.ps1
```

If running manually instead:

### Create missing directories

```cmd
mkdir "C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\x86\Media"
mkdir "C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\x86\WinPE_OCs"
mkdir "C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\x86\en-us"
```

### Fix registry keys

Run PowerShell as Administrator:

```powershell
$KitsPath = "C:\Program Files (x86)\Windows Kits\10\"

New-Item -Path "HKLM:\SOFTWARE\Microsoft\Windows Kits\Installed Roots" -Force
New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows Kits\Installed Roots" -Name "KitsRoot10" -Value $KitsPath -PropertyType String -Force
New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows Kits\Installed Roots" -Name "KitsRoot81" -Value $KitsPath -PropertyType String -Force

New-Item -Path "HKLM:\SOFTWARE\Microsoft\Windows Kits\WinPE" -Force
New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows Kits\WinPE" -Name "Installed" -Value 1 -PropertyType DWord -Force
```

> **Note:** `Fix-MDTforADK24H2.ps1` creates the directories and registry keys above and additionally patches `DeploymentTools.xml` for MDT catalog generation. Run it rather than the manual steps unless specifically debugging.

---

## Step 4 — Install DaRT

Run **after** Step 3 — the installer checks for the x86 WinPE folders before proceeding.

```cmd
msiexec /i MSDaRT100.msi
```

If the installer fails with an ADK version error, re-run `Fix-MDTforADK24H2.ps1` and retry.

---

## Step 5 — Verify PowerShell Modules

```powershell
Import-Module Dism
Import-Module Microsoft.Dart
Get-Command -Module Microsoft.Dart
```

Expected: `New-DartConfiguration`, `Set-DartImage`, `Export-DartImage` are listed.

---

## Step 6 — Pre-flight Check Script

```powershell
function Test-Prereqs {
  $WinPEPath = "C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment"
  $dirs = @("$WinPEPath\amd64\Media", "$WinPEPath\amd64\WinPE_OCs")

  foreach ($dir in $dirs) {
    if (!(Test-Path $dir)) {
      Write-Warning "Missing $dir"
      pause
    }
  }

  Import-Module Microsoft.Dart -ErrorAction Stop
  Import-Module Dism -ErrorAction Stop
}
Test-Prereqs
```

---

## Step 7 — Build DaRT Image (WIM-based)

`Build-WinPE.ps1` handles the full build automatically. The DaRT integration it performs via the PowerShell module:

```powershell
Import-Module Dism
Import-Module Microsoft.Dart

$MountDir = "C:\WinPE_Build\scratch\mount"
$BootWim  = "C:\WinPE_Build\scratch\boot_x64.wim"

Mount-WindowsImage -ImagePath $BootWim -Index 1 -Path $MountDir

$config = New-DartConfiguration -AddAllTools -RemotePort 3389 `
  -RemoteMessage "Welcome To The WinPE Deployment environment`r`n`r`nYou will find tools in X:\Tools`r`nPowershell is also available for you`r`nAs well as Microsoft DART 10 tools`r`n"
$config | Set-DartImage -Path $MountDir

Dismount-WindowsImage -Path $MountDir -Save
```

> **NB:** `Build-WinPE.ps1` uses index 1 (custom WinPE WIM). The DaRT wizard uses index 2 when working from full Windows media — do not change this.

To run the full build:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
cd C:\WinPE_Build
.\Build-WinPE.ps1
```

---

## Step 8 — Populate the Build Tree

Full expected layout:

```
C:\WinPE_Build\
  Build-WinPE.ps1
  Fix-MDTforADK24H2.ps1

  sources\
    PowerShell-7.4.13-win-x64.zip
    Dart_w11.tpk
    toolsX64.cab              (fallback DaRT source)
    WinPERDP\                 (fallback pre-extracted DaRT files)

  tools\
    amd64\
      Windows\
        System32\
          cecho.exe
          dartparse.exe
          bginfo.exe          (optional)
          winpe.bgi           (optional)
          wallpaper.bmp       (optional)
          netstart.exe        (optional — from Dart_w11.tpk image 1)
      fonts\
        JetBrainsMonoNerdFont-Regular.ttf
        JetBrainsMonoNerdFont-Bold.ttf
        JetBrainsMonoNerdFont-Italic.ttf
        JetBrainsMonoNerdFont-BoldItalic.ttf

  drivers\
    virtio\
      amd64\  vioscsi\  NetKVM\
```

---

## Step 9 — Create winpe.bgi (optional)

On the Win11 build box run `bginfo.exe`. Configure the fields (Computer Name, IP Address, OS, Build Number, Date/Time), set the background image to `wallpaper.bmp` under Background settings, then **File > Save As > winpe.bgi**. Place in `tools\amd64\Windows\System32\`.

---

## Notes

- This method avoids DaRT installer detection issues
- Uses official Microsoft tooling via PowerShell (`Microsoft.Dart` module)
- Ensures RDP + full toolset is included
- Fully repeatable pipeline
- `DartConfig.dat` generated by `New-DartConfiguration` is version-matched to your DaRT install — this is the fix for `inv32.xml` not being created on boot

---

## Recommended Workflow

```
Install ADK → Install WinPE add-on → Fix-MDTforADK24H2.ps1 → Install DaRT → Build-WinPE.ps1
```

---

## Final Result

- Clean WinPE
- Full DaRT integration
- Remote tools (RDP via DaRT Remote Connection Viewer — not mstsc)
- Scriptable, repeatable process

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `inv32.xml` not created | `DartConfig.dat` mismatch or no network at DaRT start | Rebuild with `Microsoft.Dart` module — regenerates correct `DartConfig.dat` |
| Keyboard still US after GB selected | `Set-InputLocale` not applied at build time | Rebuild — the script applies `DISM /Set-InputLocale:0809:00000809` |
| `cecho.exe not found` | File in `tools\amd64\` not `tools\amd64\Windows\System32\` | Move to correct subfolder and rebuild |
| `Set-DartImage` fails with missing package | `WinPE-DismCmdlets` not installed in WIM | Check `$WinPEPackages` in `Build-WinPE.ps1` |
| DaRT installer rejects ADK version | x86 WinPE folders missing | Run `Fix-MDTforADK24H2.ps1` then retry `msiexec /i MSDaRT100.msi` |

---

## Changelog

| Date | Change |
|------|--------|
| 2025-04-06 | Initial document |

---

*Example Music Limited — Internal Infrastructure Documentation*  
*Do not distribute outside the organisation*  
*Credentials: See password manager — never store passwords in this document*
