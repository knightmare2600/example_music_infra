# =============================================================================
# Build-WinPE.ps1
# Builds a lean WinPE WIM for virtual infrastructure deployment.
# Targets VMware (PVSCSI, VMXNET3) and Proxmox/KVM (VirtIO) on a single image.
# Runs on x86_64 or ARM64 Windows build box - architecture is auto-detected.
# Boots to cmd.exe. Drop tools into tools\amd64\ or tools\ARM64\ as needed.
#
# What this script produces under output\:
#   output\
#     boot_<arch>.wim          -- the WinPE WIM
#     boot_<arch>.iso          -- bootable ISO (BIOS boot via etfsboot.com)
#     winpe\
#       <arch>\                -- ready to copy to jukebox HTTP root
#         wimboot              -- EFI wimboot binary (UEFI boot)
#         wimboot.i386         -- BIOS wimboot binary (legacy BIOS boot)
#         bootmgr              -- BIOS boot manager from ADK
#         boot\
#           BCD                -- BIOS BCD  (winload.exe path)
#           BCD.efi            -- UEFI BCD  (winload.efi path)
#           boot.sdi           -- RAM disk descriptor from ADK
#         sources\
#           boot.wim           -- copy of the finished WIM
#
# Prerequisites:
#   - Windows ADK + WinPE Add-on installed for this architecture
#   - curl.exe available (inbox on Windows 10 1803+ / Server 2019+)
#   - 7-Zip installed OR 7za.exe portable (script downloads if neither found)
#   - VMware Tools source in one of:
#       sources\VMwareTools.exe   -- full installer EXE  (preferred)
#       sources\VMwareTools.msi   -- extracted MSI
#       sources\vmware-drivers\   -- loose INF/SYS files already extracted
#   - VirtIO drivers pre-extracted under drivers\virtio\ (see layout below)
#   - Run from an elevated PowerShell session
#
# All paths are relative to C:\WinPE_Build - script must live there.
#
# Expected folder layout under C:\WinPE_Build:
#   Build-WinPE.ps1
#   sources\
#     VMwareTools.exe            (or .msi, or vmware-drivers\ folder)
#   drivers\
#     virtio\
#       amd64\
#         vioscsi\
#         NetKVM\
#       ARM64\
#         vioscsi\
#         NetKVM\
#   tools\
#     amd64\
#     ARM64\
#
# Version history:
#   0.1.0  2025-03-31  Initial release
#   0.2.0  2025-03-31  Fix VMware extraction (7-Zip unpack + msiexec /a)
#                      Collapse all paths under C:\WinPE_Build
#                      Split tools\ by architecture (tools\amd64\, tools\ARM64\)
#                      Cleanup removes only scratch dirs, not the whole tree
#   0.3.0  2025-03-31  Build BCD fresh via bcdedit (fixes unbootable WIM)
#                      Build bootable ISO via oscdimg
#                      Assemble complete iPXE output folder
#                      Portable 7-Zip fallback via curl.exe if not installed
#                      Tolerant VMware driver search: EXE -> MSI -> loose files
#                      Script no longer throws if VMware drivers not found
#   0.3.1  2025-03-31  Fix Find-VMwareDriversInTree always returning [array]
#                      Fix 7-Zip exit code 1 (warnings) treated as success
#   0.4.0  2025-03-31  Build both BIOS and UEFI BCDs every run
#                      Download wimboot (EFI) and wimboot.i386 (BIOS)
#                      ISO uses BIOS BCD; iPXE folder carries both BCDs
#                      menu.ipxe updated to use wimboot.i386 for BIOS VMs
#   0.4.1  2025-03-31  Fix $OutputBCDBIOS variable not set before ISO build
#                      Write-Step output now always Cyan
#                      Auto-download VMware Tools EXE from packages.vmware.com
#   0.5.0  2025-03-31  startnet.cmd runs before cmd.exe via winpeshl.ini
#                      Tools folder moved to WIM root (X:\Tools\ in live PE)
#                      cecho.exe staged to System32; welcome banner added
#   0.5.1  2025-03-31  startnet.cmd prompts for server/share/user at runtime
#   0.6.0  2025-04-01  Add WinPE OC reference URL and fix install order
#                      Add WinPE-NetFX and WinPE-PowerShell to package list
#                      findstr.exe copied from build host into WIM System32
#                      DaRT Remote Recovery staged; RDP started from startnet.cmd
#   0.6.1  2025-04-01  Set-WinPERDP: auto-extract toolsX64.cab via 7-Zip
#                      Set-WinPERDP: full 11-file list from MDOP DaRT
#                      Search WinPE_OCs for DaRT cab; try DISM install first
#   0.6.2  2025-04-01  Fix Set-WinPERDP 7-Zip call (broken backtick quoting)
#   0.6.3  2025-04-01  Set-WinPERDP checks tools\<arch>\WinPERDP\ as fallback
#   0.6.4  2025-04-01  Fix .Count on scalar $missing under Set-StrictMode
#   0.7.0  2025-04-01  Save PS Gallery modules into WIM at build time
#                      Inject LOCALAPPDATA fix via PS profile + DEFAULT hive
#                      PackageManagement + PowerShellGet bootstrapped in WIM
#   0.7.1  2025-04-01  startnet.cmd ends with cmd.exe /k (persistent session)
#   0.7.2  2025-04-01  Set UK keyboard layout (0409:00000809) at PE startup
#   0.7.3  2025-04-01  Keyboard layout prompt: G=GB/UK D=Deutsch K=Danske U=US
#   0.7.4  2025-04-01  choice.exe copied from build host alongside findstr.exe
#                      Share map prompt added with Yes/No choice
#                      Keyboard and share map timeouts set to 30 seconds
#   0.8.0  2025-04-01  PS ExecutionPolicy set to Unrestricted in WIM hive
#                      BGInfo staged from tools; runs at startup for wallpaper
#                      Hypervisor+arch detect with V2V driver store hint
#                      DaRT startup checks inv32.xml for confirmation
#                      regedit.exe copied from build host into WIM
#                      Banner updated to wider 99-char format (v1.08)
#   0.9.0  2025-04-01  PowerShell 7.4 LTS added via ZIP expand into WIM
#                      PS7 PATH/PSModulePath/env vars written to SYSTEM hive
#                      PS Gallery modules saved to PS7 path as well as PS5.1
#                      regedit.exe fixed to copy from %windir% not System32
#                      DaRT inv32.xml parsed; ticket/IP/port shown at startup
#   0.9.1  2025-04-01  winpeshl.ini uses cmd.exe /k startnet.cmd (Ctrl+C safe)
#                      driverquery removed - replaced with reg query (no hangs)
#                      wmic replaced with reg query for arch detection
#   0.9.2  2025-04-01  DISM /Set-InputLocale:en-GB baked into WIM (fixes Shift+2)
#                      SetUserLocale + SetMuiLanguage added per layout selection
#                      DaRT start /d X:\ sets working dir so inv32.xml lands on X:
#   0.9.4  2025-04-01  DaRT rewritten as top-level CMD flow (fixes goto-in-parens)
#   0.9.5  2025-04-01  en-GB locale via DISM /Set-InputLocale + UILanguage + UserLocale
#                      Removed stale WinPELangPack cab search (ADK has no en-GB cab)
#   0.9.6  2025-04-01  Install lp.cab + per-OC cabs for en-gb, da-dk, de-de
#                      Locale folder is lowercase en-gb not en-GB (ADK naming)
#   0.9.7  2025-04-01  DaRT launched via wpeinit + Unattend.xml RunSynchronous
#                      inv32.xml path corrected to X:\Windows\System32\
#                      winpeshl.ini now runs wpeinit before startnet.cmd
#   0.9.8  2025-04-01  BGInfo /accepteula flag; wallpaper forced via user32.dll
#                      wallpaper.bmp staging from tools\amd64\wallpaper.bmp
#                      WIM cleanup (StartComponentCleanup) + export for size
#   0.9.9  2025-04-01  DaRT: correct winpeshl.ini sequence per Microsoft docs
#                      (netstart -> RemoteRecovery async -> WaitForConnection)
#                      Copy-Tools now mirrors dir structure onto WIM root
#                      VMware display/VGA drivers (vmsvga.inf) added to search
#                      Unattend.xml sets 1280x720 display; QRES.exe documented
#   1.0.0  2025-04-01  DaRT: .tpk is a ZIP - extract with 7-Zip, overlay onto WIM
#   1.0.1  2025-04-01  StartDaRT.cmd: waits for valid IP before RemoteRecovery
#   1.0.2  2025-04-05  Set-WinPEDaRT: Microsoft.Dart module loaded by full .psd1 path
#   1.0.3  2025-04-05  Pre-flight checks: cecho, Dart module, x86 ADK folders
#   1.0.4  2025-04-05  /Set-UILanguage removed (invalid for WinPE images)
#   1.0.5  2025-04-06  WinPE-SRT replaced with WinPE-DismCmdlets (removed from ADK 24H2)
#   1.0.6  2025-04-06  WaitForConnection removed - DaRT runs in background
#   1.0.7  2025-04-09  Arch prompt on amd64 host - select x64 or ARM64
#   1.0.8  2025-04-09  ARM64 cross-build fixes:
#   1.0.9  2025-04-11  Arch-namespaced scratch dirs for parallel builds
#   1.1.0  2025-04-11  Embedded BCD rebuilt as winload.exe (BIOS) with correct SDI path
#                      Host binary copy skipped on arch mismatch (no amd64 bins in ARM64 WIM)
#                      MiniNT registry key deleted in startnet.cmd (enables pwsh.exe)
#                      BCD + boot.sdi baked into WIM for self-contained PXE
#                        iPXE entry: kernel wimboot / initrd boot.wim / boot
#                      PSGalleryModules split: shared + PS7-only lists
#                        PS7-only: CompletionPredictor, ConsoleGuiTools, Pansies
#                        PSWriteColor confirmed in shared list
#                        DISM always uses amd64 binary (arm64 dism.exe wont run on x64 host)
#                        BIOS BCD + ISO skipped for ARM64 (UEFI HTTP Boot only)
#                        bootmgr search scoped to correct arch Media folder
#                      PS modules split by version: CompletionPredictor PS7-only
#                      Tools validation extended: ntop, jq, dua, edit, screenres
#                      Fonts sourced from tools\<arch>\Windows\System32\fonts\
#                      Symbols Nerd Font added to Windows Terminal settings
#                      -Arch param for unattended builds
#                      ARM64 iPXE: skip wimboot (UEFI HTTP Boot only)
#                      x86 pre-flight check skipped on ARM64 builds
#                      startnet.cmd replaced wholesale with corrected version
#                      dartparse.exe: single call /g ID /b /f inv32.xml
#                      %ID% shown in banner; DaRT non-blocking for console users
#                      StartDaRT.cmd: fixed netstart path, wpeutil WaitForNetwork
#                      dartparse.exe used for inv32.xml parsing; %ID% set for banner
#                      netstart.exe + dartparse.exe added to pre-flight validation
#                      WinPE-SRT added to OC list (required by Set-DartImage)
#                      cecho+bginfo unified to tools\<arch>\Windows\System32\
#                      DISM cleanup moved to pre-dismount (fixes error 267)
#                      Banner updated to wider format with platform/arch in footer
#                      Microsoft.Dart tries installed name then path fallback
#                      DaRT auto-skips if pre-staged in tools\<arch>\Windows\System32\
#                      Banner moved to last section in startnet.cmd
#                      Fixes DHCP race condition causing inv32.xml not created
#                      DartConfig.dat must be from DaRT Recovery Image Wizard
#                      Copy-Tools: skip existing files, catch access denied
#                      DaRT timeout is non-fatal - shell always shows
#                      cecho.exe: must be in tools\amd64\Windows\System32\
#                      PS profile updated to match user's exact PS7 profile
#                      Profile written to both PS5.1 and PS7 paths
#   0.9.3  2025-04-01  Windows Terminal portable downloaded and staged in WIM
#                      .portable marker enables self-contained settings
#                      wt.cmd wrapper in System32 - type 'wt' to launch
#                      settings.json baked in; PS7 uses direct path
#                      JetBrainsMono Nerd Font staged from tools\amd64\fonts\
# =============================================================================

#Requires -RunAsAdministrator

# -Arch can be passed on the command line to skip the interactive prompt:
#   .\Build-WinPE.ps1 -Arch amd64
#   .\Build-WinPE.ps1 -Arch arm64
param([string]$Arch = '')

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------

$BuildRoot = 'C:\WinPE_Build'

# VMware source - script tries each in order, uses first that yields drivers
# If VMwareTools.exe is absent the script downloads it from VMware's package server.
# URL structure: https://packages.vmware.com/tools/esx/latest/windows/<arch>/
# where <arch> is 'x64' for amd64 or 'arm64' for ARM64.
$VMwareToolsBaseUrl = 'https://packages.vmware.com/tools/esx/latest/windows'
$VMwareToolsEXE     = Join-Path $BuildRoot 'sources\VMwareTools.exe'
$VMwareToolsMSI     = Join-Path $BuildRoot 'sources\VMwareTools.msi'
$VMwareLooseDrivers = Join-Path $BuildRoot 'sources\vmware-drivers'

$VirtIODriverRoot   = Join-Path $BuildRoot 'drivers\virtio'

# DaRT Remote Recovery files for RDP-into-WinPE support.
# Extract toolsX64.cab (from MDOP DaRT) and place the files listed below
# into sources\WinPERDP\. The script will copy them into Windows\System32\
# inside the WIM. If the cab is present, the script can extract it automatically.
#
# Required files (all from toolsX64.cab):
#   RemoteRecovery.exe    -- RDP server process
#   RdpCore.dll           -- RDP core
#   rdpencom.dll          -- RDP encoding
#   MSDartCmn.dll         -- DaRT common
#   LockingHooks.dll      -- DaRT locking
#   FirewallExceptionChange.dll -- firewall helper
#   WaitForConnection.exe -- connection waiter
#   DartConfig.dat        -- DaRT configuration
#   mfc100u.dll           -- VC++ 2010 runtime (Unicode)
#   msvcp100.dll          -- VC++ 2010 C++ runtime
#   msvcr100.dll          -- VC++ 2010 C runtime
#
# Connect using the MSDaRT Remote Connection Viewer from another Windows machine.
# Ref: https://www.cb-net.co.uk/microsoft-articles/configmgr/
#      configmgr-dart-8-1-remote-viewer-and-windows-pe/
# PowerShell 7 ZIP - download the win-x64 or win-arm64 ZIP from:
# https://github.com/PowerShell/PowerShell/releases/tag/v7.4.13
# Place in sources\ - script picks the correct arch automatically.
# Ref: https://www.deploymentresearch.com/adding-powershell-7-to-winpe/
$PS7ZipX64   = Join-Path $BuildRoot 'sources\PowerShell-7.4.13-win-x64.zip'
$PS7ZipARM64 = Join-Path $BuildRoot 'sources\PowerShell-7.4.13-win-arm64.zip'
$RDPSourceDir  = Join-Path $BuildRoot 'sources\WinPERDP'
$RDPSourceCab  = Join-Path $BuildRoot 'sources\toolsX64.cab'

# DaRT 10 module location.
# The Microsoft.Dart module cannot be installed normally on ADK 24H2 (version
# conflict). Instead, extract the MSI with:
#   msiexec /a MSDaRT100.msi /qb TARGETDIR=C:\WinPE_Build\sources\DaRT_extract
# The .psd1 manifest uses relative paths so the module must be loaded by full
# path from its extracted location - do not move individual files.
# Set $DaRTModulePath = $null to skip the module and use .tpk fallback.
$DaRTExtractRoot = Join-Path $BuildRoot 'sources\DaRT_extract'
$DaRTModulePath  = Join-Path $DaRTExtractRoot 'v10\Modules\Microsoft.Dart\Microsoft.Dart.psd1'
$ToolsRoot          = Join-Path $BuildRoot 'tools'
$ScratchDir         = Join-Path $BuildRoot 'scratch'
$OutputDir          = Join-Path $BuildRoot 'output'

# Portable 7-Zip download - 7za.exe standalone, no install needed
# Source: 7-Zip standalone console binary from 7-zip.org
$SevenZipPortableUrl = 'https://www.7-zip.org/a/7za2409.exe'
$SevenZipPortablePath = Join-Path $ScratchDir '7za.exe'

# PowerShell Gallery modules to Save-Module into the WIM at build time.
# Ref: https://www.osdeploy.com/archive/blog/2021/winpe-powershell-gallery
#
# Two blockers exist in WinPE:
#   1. PackageManagement is absent - so Install-Module cannot run at boot.
#      Fix: Save-Module from the build host into the WIM during build.
#   2. LOCALAPPDATA env var is undefined (no HKCU Volatile Environment).
#      Fix: inject the registry key into the offline WIM hive at build time.
#
# Module compatibility notes:
#   PSWriteColor        - compatible with WinPE PS 5.1
#   PSReadLine          - ships with PS 5.1, saving a newer version is fine
#   Terminal-Icons      - compatible, but rendering needs a NerdFont terminal
#   CompletionPredictor - requires PS 7.2+; WinPE is PS 5.1 - saved but not loaded
#   NerdFonts           - font installer, irrelevant inside PE; omitted from WIM
# Modules for both PS5.1 and PS7
$PSGalleryModules = @(
  'PSWriteColor',
  'PSReadLine',
  'Terminal-Icons'
)

# Additional modules for PS7 only (requires PS 7.2+)
# These are saved to the PS7 module path only, not PS5.1
$PSGalleryModulesPS7Only = @(
  'CompletionPredictor',
  'Microsoft.PowerShell.ConsoleGuiTools',
  'Pansies'
)

# Windows Terminal portable ZIP - downloaded automatically at build time.
# Uses the GitHub releases API to find the latest stable x64 portable ZIP.
# Set to $false to skip Windows Terminal entirely.
$InstallWindowsTerminal = $true

# wimboot download URLs - both EFI and BIOS binaries from same release
$WimbootUrlEFI  = 'https://github.com/ipxe/wimboot/releases/latest/download/wimboot'
$WimbootUrlBIOS = 'https://github.com/ipxe/wimboot/releases/latest/download/wimboot.i386'

# DISM optional components to add to the WIM.
# Full reference:
# https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/
#   winpe-add-packages--optional-components-reference?view=windows-11
#
# Install order matters - WMI before StorageWMI, NetFX before PowerShell.
# WinPE-HTA     : HTML Application host (IE-based UI capability)
# WinPE-WMI     : WMI provider - required by StorageWMI and PowerShell
# WinPE-NetFX   : .NET Framework subset - required by PowerShell
# WinPE-Scripting: WSH / wscript / cscript support
# WinPE-PowerShell: PowerShell (requires WMI + NetFX first)
# WinPE-StorageWMI: Storage cmdlets via WMI
# WinPE-DismCmdlets: DISM PowerShell cmdlets
# Note: WinPE-SRT was removed from ADK 24H2. Set-DartImage works without it.

$WinPEPackages = @(
  'WinPE-HTA',
  'WinPE-WMI',
  'WinPE-NetFX',
  'WinPE-Scripting',
  'WinPE-PowerShell',
  'WinPE-StorageWMI',
  'WinPE-DismCmdlets'
)

# 7-Zip installed binary search paths
$SevenZipCandidates = @(
  'C:\Program Files\7-Zip\7z.exe',
  'C:\Program Files (x86)\7-Zip\7z.exe'
)

# -----------------------------------------------------------------------------
# FUNCTIONS -- output helpers
# -----------------------------------------------------------------------------

function Write-Step {
  param([string]$Message)
  Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Write-OK {
  param([string]$Message)
  Write-Host "    [OK] $Message" -ForegroundColor Green
}

function Write-Warn {
  param([string]$Message)
  Write-Host "    [WARN] $Message" -ForegroundColor Yellow
}

function Write-Info {
  param([string]$Message)
  Write-Host "    $Message" -ForegroundColor Gray
}

function Assert-Path {
  param([string]$Path, [string]$Description)
  if (-not (Test-Path $Path)) {
    throw "Required path not found: $Path`n       ($Description)"
  }
}

# -----------------------------------------------------------------------------
# FUNCTIONS -- environment detection
# -----------------------------------------------------------------------------

function Get-BuildArch {
  # Returns the architecture to build for.
  # On an amd64 host the user is prompted - ADK 24H2 ships both amd64 and arm64
  # WinPE_OCs on an amd64 install so cross-building ARM64 WIM is fully supported.
  # On an ARM64 host ARM64 is the only option.
  param([string]$Override = '')

  $hostArch = switch ($env:PROCESSOR_ARCHITECTURE) {
    'AMD64' { 'amd64' }
    'ARM64' { 'arm64' }
    default { throw "Unsupported host architecture: $($env:PROCESSOR_ARCHITECTURE)" }
  }

  # If an override was passed on the command line, validate and use it
  if ($Override -ne '') {
    $o = $Override.ToLower()
    if ($o -notin @('amd64','arm64','x64')) {
      throw "Invalid -Arch value '$Override'. Use amd64, x64, or arm64."
    }
    if ($o -eq 'x64') { $o = 'amd64' }
    if ($o -eq 'arm64' -and $hostArch -eq 'amd64') {
      Write-Host '    [INFO] Cross-building ARM64 WIM on amd64 host' -ForegroundColor Cyan
    }
    return $o
  }

  # ARM64 host - no choice needed
  if ($hostArch -eq 'arm64') {
    Write-Host '    ARM64 host detected - building ARM64 WIM' -ForegroundColor Cyan
    return 'arm64'
  }

  # amd64 host - prompt with 30s timeout defaulting to x64
  Write-Host ''
  Write-Host '  Select target architecture:' -ForegroundColor Cyan
  Write-Host '    [1]  x64 / amd64  (default - 30s timeout)' -ForegroundColor Yellow
  Write-Host '    [2]  ARM64         (cross-build - ADK 24H2 required)' -ForegroundColor Yellow
  Write-Host ''
  $choice = $null
  $timeout = 30
  $start = [datetime]::Now
  while (-not $choice) {
    $elapsed = ([datetime]::Now - $start).TotalSeconds
    $remaining = [int]($timeout - $elapsed)
    if ($remaining -le 0) { $choice = '1'; break }
    Write-Host "`r  Choice (auto-selecting x64 in $remaining`s): " -NoNewline -ForegroundColor Gray
    if ([Console]::KeyAvailable) {
      $key = [Console]::ReadKey($true)
      if ($key.KeyChar -eq '1') { $choice = '1' }
      elseif ($key.KeyChar -eq '2') { $choice = '2' }
    }
    Start-Sleep -Milliseconds 200
  }
  Write-Host ''
  if ($choice -eq '2') {
    Write-Host '    [INFO] Selected: ARM64 (cross-build on amd64 host)' -ForegroundColor Cyan
    return 'arm64'
  }
  Write-Host '    [INFO] Selected: x64' -ForegroundColor Cyan
  return 'amd64'
}

function Get-WimArch {
  param([string]$BuildArch)
  switch ($BuildArch) {
    'amd64' { return 'x64' }
    'arm64' { return 'arm64' }
  }
}

function Get-ToolsArch {
  param([string]$BuildArch)
  switch ($BuildArch) {
    'amd64' { return 'amd64' }
    'arm64' { return 'ARM64' }
  }
}

function Get-iPXEArch {
  # Returns the folder name used under winpe\ in the iPXE output tree
  param([string]$BuildArch)
  switch ($BuildArch) {
    'amd64' { return 'x86_64' }
    'arm64' { return 'arm64' }
  }
}

function Get-ADKRoot {
  $candidates = @(
    'C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit',
    'C:\Program Files\Windows Kits\10\Assessment and Deployment Kit'
  )
  foreach ($c in $candidates) {
    if (Test-Path $c) { return $c }
  }
  throw 'Windows ADK not found. Install the ADK + WinPE Add-on before running.'
}

function Get-OscdimgPath {
  param([string]$ADKRoot)
  # oscdimg lives under the Deployment Tools component of the ADK
  $candidates = @(
    (Join-Path $ADKRoot 'Deployment Tools\x86\Oscdimg\oscdimg.exe'),
    (Join-Path $ADKRoot 'Deployment Tools\amd64\Oscdimg\oscdimg.exe')
  )
  foreach ($c in $candidates) {
    if (Test-Path $c) { return $c }
  }
  throw "oscdimg.exe not found under ADK. Ensure the Deployment Tools component is installed."
}

# -----------------------------------------------------------------------------
# FUNCTIONS -- 7-Zip acquisition
# -----------------------------------------------------------------------------

function Get-SevenZipPath {
  param([string]$ScratchDir)

  # Check installed copies first
  foreach ($c in $SevenZipCandidates) {
    if (Test-Path $c) {
      Write-Info "7-Zip found (installed): $c"
      return $c
    }
  }

  # Check if we already downloaded 7za.exe this session or a prior run
  if (Test-Path $SevenZipPortablePath) {
    Write-Info "7za.exe found (portable, cached): $SevenZipPortablePath"
    return $SevenZipPortablePath
  }

  # Download portable 7za.exe via curl.exe (inbox since Windows 10 1803)
  Write-Step 'Downloading portable 7za.exe (7-Zip not installed)'
  $curlExe = 'curl.exe'
  try {
    $null = & $curlExe --version 2>&1
  } catch {
    throw 'curl.exe not found. Install 7-Zip or ensure curl.exe is available (inbox on Windows 10 1803+ / Server 2019+).'
  }

  $null = New-Item -ItemType Directory -Path $ScratchDir -Force
  & $curlExe -L --silent --show-error -o $SevenZipPortablePath $SevenZipPortableUrl
  if (-not (Test-Path $SevenZipPortablePath)) {
    throw "Failed to download 7za.exe from $SevenZipPortableUrl"
  }
  Write-OK "7za.exe downloaded to $SevenZipPortablePath"
  return $SevenZipPortablePath
}

# -----------------------------------------------------------------------------
# FUNCTIONS -- wimboot acquisition
# -----------------------------------------------------------------------------

function Get-Wimboot {
  param([string]$DestPath, [string]$Url)

  if (Test-Path $DestPath) {
    Write-Info "wimboot already present: $(Split-Path $DestPath -Leaf)"
    return
  }

  Write-Info "Downloading $(Split-Path $DestPath -Leaf) from $Url"
  & curl.exe -L --silent --show-error -o $DestPath $Url
  if (-not (Test-Path $DestPath)) {
    throw "Failed to download wimboot from $Url"
  }
  Write-OK "Downloaded: $DestPath"
}

# -----------------------------------------------------------------------------
# FUNCTIONS -- VMware Tools EXE download
# -----------------------------------------------------------------------------

function Get-VMwareToolsEXE {
  # Downloads VMware Tools EXE from the VMware package server if not present.
  # Architecture-aware: picks x64 or arm64 subdirectory to match build host.
  param(
    [string]$DestPath,
    [string]$BuildArch,   # amd64 or arm64
    [string]$BaseUrl
  )

  if (Test-Path $DestPath) {
    Write-Info "VMware Tools EXE already present: $DestPath"
    return
  }

  # VMware package server uses 'x64' for amd64, 'arm64' for arm64
  $urlArch = switch ($BuildArch) {
    'amd64' { 'x64' }
    'arm64' { 'arm64' }
  }

  # Index the directory listing to find the current EXE filename
  $indexUrl = "$BaseUrl/$urlArch/"
  Write-Step "Fetching VMware Tools EXE index from $indexUrl"

  $indexContent = & curl.exe -L --silent --show-error $indexUrl 2>&1
  # Extract .exe filename from directory listing href
  $exeMatch = [regex]::Match($indexContent, 'href="(VMware-tools-[^"]+\.exe)"')
  if (-not $exeMatch.Success) {
    Write-Warn "Could not parse VMware Tools EXE filename from $indexUrl"
    Write-Warn "Place VMwareTools.exe manually at: $DestPath"
    return
  }

  $exeFile = $exeMatch.Groups[1].Value
  $exeUrl  = "$indexUrl$exeFile"
  Write-Info "Downloading $exeFile"
  $null = New-Item -ItemType Directory -Path (Split-Path $DestPath -Parent) -Force
  & curl.exe -L --silent --show-error --progress-bar -o $DestPath $exeUrl
  if (Test-Path $DestPath) {
    $dlMB = [math]::Round((Get-Item $DestPath).Length / 1MB, 1)
    Write-OK "Downloaded VMware Tools EXE ($dlMB MB) to $DestPath"
  } else {
    Write-Warn "Download failed - place VMwareTools.exe manually at: $DestPath"
  }
}

# -----------------------------------------------------------------------------
# FUNCTIONS -- VMware driver extraction
# Tries EXE -> MSI -> loose folder, in that order.
# Returns the path containing driver subfolders, or $null if nothing found.
# Never throws - callers decide whether missing VMware drivers are fatal.
# -----------------------------------------------------------------------------

function Invoke-7Zip {
  param([string]$SevenZip, [string]$Source, [string]$Destination)
  $proc = Start-Process -FilePath $SevenZip -ArgumentList "x `"$Source`" -o`"$Destination`" -y" -Wait -PassThru -NoNewWindow
  return $proc.ExitCode
}

function Find-VMwareDriversInTree {
  # Recursively searches a path for PVSCSI and VMXNET3 INF files.
  # Typed as [string[]] and returned with the unary comma operator so
  # PowerShell never unwraps the array - .Count is always safe to call
  # under Set-StrictMode -Version Latest.
  param([string]$SearchRoot)

  # pvscsi = SCSI storage, vmxnet3 = network, vmsvga/vm3dgl = display
  $targets = @('pvscsi.inf', 'vmxnet3.inf', 'vmxnet3ndis6.inf', 'vmsvga.inf', 'vm3dgl.inf')
  [string[]]$found = @()

  foreach ($t in $targets) {
    $hits = Get-ChildItem -Path $SearchRoot -Filter $t -Recurse -ErrorAction SilentlyContinue
    foreach ($h in $hits) {
      if ($found -notcontains $h.DirectoryName) {
        $found += $h.DirectoryName
        Write-OK "Found VMware driver INF [$t]: $($h.DirectoryName)"
      }
    }
  }

  return ,$found
}

function Get-VMwareDriverPaths {
  param(
    [string]$SevenZip,
    [string]$EXEPath,
    [string]$MSIPath,
    [string]$LoosePath,
    [string]$ExtractEXETo,
    [string]$ExtractMSITo
  )

  # --- Attempt 1: EXE -> unpack with 7-Zip -> msiexec /a ---
  if (Test-Path $EXEPath) {
    Write-Step "VMware drivers: unpacking EXE with 7-Zip"
    $null = New-Item -ItemType Directory -Path $ExtractEXETo -Force
    $rc = Invoke-7Zip -SevenZip $SevenZip -Source $EXEPath -Destination $ExtractEXETo
    # 7-Zip exit codes: 0=OK, 1=warnings (normal for self-extracting EXEs), 2+=error
    if ($rc -le 1) {
      Write-OK "EXE unpacked to $ExtractEXETo"
      $msi = Get-ChildItem -Path $ExtractEXETo -Filter '*.msi' -Recurse |
        Sort-Object { $_.Name -like 'VMware Tools*' } -Descending |
        Select-Object -First 1
      if ($msi) {
        Write-Info "Found MSI inside EXE: $($msi.FullName)"
        $null = New-Item -ItemType Directory -Path $ExtractMSITo -Force
        $proc = Start-Process 'msiexec.exe' `
          -ArgumentList "/a `"$($msi.FullName)`" /qn TARGETDIR=`"$ExtractMSITo`"" `
          -Wait -PassThru -NoNewWindow
        if ($proc.ExitCode -eq 0) {
          Write-OK "msiexec /a succeeded - searching for driver INFs"
          $paths = Find-VMwareDriversInTree -SearchRoot $ExtractMSITo
          if ($paths.Count -gt 0) { return $paths }
          Write-Warn "msiexec /a ran but no driver INFs found under $ExtractMSITo"
        } else {
          Write-Warn "msiexec /a failed (exit $($proc.ExitCode)) - falling through"
        }
      } else {
        Write-Warn "No MSI found inside EXE extract - falling through"
      }
      # MSI extraction failed or yielded nothing - try searching the raw EXE extract
      Write-Info "Searching raw EXE extract for driver INFs"
      $paths = Find-VMwareDriversInTree -SearchRoot $ExtractEXETo
      if ($paths.Count -gt 0) { return $paths }
    } else {
      Write-Warn "7-Zip extraction of EXE failed (exit $rc) - falling through"
    }
  }

  # --- Attempt 2: standalone MSI -> msiexec /a ---
  if (Test-Path $MSIPath) {
    Write-Step "VMware drivers: running msiexec /a on standalone MSI"
    $null = New-Item -ItemType Directory -Path $ExtractMSITo -Force
    $proc = Start-Process 'msiexec.exe' `
      -ArgumentList "/a `"$MSIPath`" /qn TARGETDIR=`"$ExtractMSITo`"" `
      -Wait -PassThru -NoNewWindow
    if ($proc.ExitCode -eq 0) {
      $paths = Find-VMwareDriversInTree -SearchRoot $ExtractMSITo
      if ($paths.Count -gt 0) { return $paths }
      Write-Warn "msiexec /a ran but no driver INFs found under $ExtractMSITo"
    } else {
      Write-Warn "msiexec /a on standalone MSI failed (exit $($proc.ExitCode)) - falling through"
    }
  }

  # --- Attempt 3: loose driver folder ---
  if (Test-Path $LoosePath) {
    Write-Step "VMware drivers: searching loose driver folder $LoosePath"
    $paths = Find-VMwareDriversInTree -SearchRoot $LoosePath
    if ($paths.Count -gt 0) { return $paths }
    Write-Warn "Loose driver folder exists but contains no recognised driver INFs"
  }

  # Nothing worked - warn and return empty, caller decides
  Write-Warn "No VMware drivers found - WIM will boot without PVSCSI/VMXNET3"
  Write-Warn "Place VMwareTools.exe, VMwareTools.msi, or extracted INFs in sources\"
  return @()
}

# -----------------------------------------------------------------------------
# FUNCTIONS -- VirtIO drivers
# -----------------------------------------------------------------------------

function Get-VirtIODriverPaths {
  param([string]$VirtIORoot, [string]$Arch)

  $virtioArch = switch ($Arch) {
    'amd64' { 'amd64' }
    'arm64' { 'ARM64' }
  }

  $archRoot = Join-Path $VirtIORoot $virtioArch
  if (-not (Test-Path $archRoot)) {
    Write-Warn "VirtIO driver root not found: $archRoot - WIM will boot without VirtIO drivers"
    return @()
  }

  $paths = @()
  foreach ($d in @('vioscsi', 'NetKVM')) {
    $p = Join-Path $archRoot $d
    if (Test-Path $p) {
      $paths += $p
      Write-OK "Found VirtIO driver: $p"
    } else {
      Write-Warn "VirtIO driver folder not found: $p - WIM will boot without it"
    }
  }
  return $paths
}

# -----------------------------------------------------------------------------
# FUNCTIONS -- WIM construction
# -----------------------------------------------------------------------------

function Add-WinPEPackage {
  param([string]$MountPath, [string]$PackagePath)
  Write-Info "Adding: $(Split-Path $PackagePath -Leaf)"
  Add-WindowsPackage -Path $MountPath -PackagePath $PackagePath -IgnoreCheck | Out-Null
}

function Set-WinPEShell {
  param([string]$MountPath)

  # winpeshl.ini:
  #   1. StartDaRT.cmd - inits networking, starts RemoteRecovery.exe async
  #      Does NOT call WaitForConnection.exe - DaRT runs in background.
  #      This allows startnet.cmd (keyboard/share/banner) to run immediately
  #      without waiting for a DaRT connection or console cancel.
  #      Remote operators connect using the ticket shown in the banner.
  #   2. cmd.exe /k startnet.cmd - keyboard, network, share, banner
  # Ctrl+C in startnet.cmd only kills the batch; cmd.exe stays alive.
  $ini = "[LaunchApps]`r`n"
  $ini += "`"%WINDIR%\\System32\\StartDaRT.cmd`"`r`n"
  $ini += "cmd.exe /k %SYSTEMROOT%\\System32\\startnet.cmd`r`n"
  Set-Content -Path (Join-Path $MountPath 'Windows\System32\winpeshl.ini') `
    -Value $ini -Encoding ASCII
  Write-OK 'winpeshl.ini written - StartDaRT.cmd -> startnet.cmd'

  # Write StartDaRT.cmd - handles network init + DaRT launch with IP wait.
  # This solves the DHCP race condition where RemoteRecovery.exe starts
  # before a valid IP is assigned and silently fails to write inv32.xml.
  # DartConfig.dat must be a valid file generated by the DaRT Recovery
  # Image Wizard (same DaRT version as RemoteRecovery.exe).
  $startDart = @'
@echo off

:: Initialise networking.
:: netstart.exe is a DaRT binary - stage it from tools\amd64\Windows\System32\
:: (copy from your .tpk extraction: DART_EXTRACT\v10 or tpk image 1\Windows\System32)
if exist %WINDIR%\System32\netstart.exe (
  %WINDIR%\System32\netstart.exe -network -remount
) else (
  wpeinit
)

:: Skip DaRT if RemoteRecovery.exe is not staged
if not exist %WINDIR%\System32\RemoteRecovery.exe goto dart_skip

:: Wait for network - wpeutil WaitForNetwork is the correct WinPE mechanism
:: It blocks until a NIC has a valid IP, up to ~30 seconds.
wpeutil WaitForNetwork

:: Extra guard: wait for a non-APIPA address (top-level loop, no parens)
set IPWAIT=0
:ip_wait_loop
ipconfig | findstr /i "IPv4" | findstr /v "169\.254" >nul 2>&1
if not errorlevel 1 goto launch_dart
if %IPWAIT% GEQ 15 goto launch_dart
ping -n 2 127.0.0.1 >nul
set /a IPWAIT+=1
goto ip_wait_loop

:launch_dart
:: RemoteRecovery.exe runs in the background - no WaitForConnection.
:: startnet.cmd runs immediately after; ticket shown in banner.
:: Remote operators connect any time using the DaRT Remote Connection Viewer.
start /min "DaRT" %WINDIR%\System32\RemoteRecovery.exe -nomessage

:dart_skip
:dart_done
'@
  $startDartPath = Join-Path $MountPath 'Windows\System32\StartDaRT.cmd'
  Set-Content -Path $startDartPath -Value $startDart -Encoding ASCII
  Write-OK 'StartDaRT.cmd written - handles IP wait + DaRT async launch'
}

function Copy-Tools {
  # Mirrors tools\<arch>\ onto the WIM root as an overlay.
  # The folder name under tools\ must match what Get-ToolsArch returns:
  #   x64 build  -> tools\amd64\
  #   ARM64 build -> tools\ARM64\
  #
  # Directory structure is preserved relative to the arch folder root:
  #   tools\amd64\Windows\System32\cecho.exe  -> WIM:\Windows\System32\cecho.exe
  #   tools\amd64\Windows\System32\bginfo.exe -> WIM:\Windows\System32\bginfo.exe
  #   tools\amd64\some.exe                    -> WIM:\some.exe  (X:\ in live PE)
  #
  # IMPORTANT: cecho.exe and any tool called without a path in startnet.cmd
  # MUST be placed under tools\amd64\Windows\System32\ so they land on PATH.
  param([string]$ToolsRoot, [string]$ToolsArch, [string]$MountPath)

  $src = Join-Path $ToolsRoot $ToolsArch
  if (-not (Test-Path $src)) {
    Write-Warn "tools\$ToolsArch\ not found at $src - skipping"
    Write-Warn "Create tools\$ToolsArch\ and place files in the correct subfolder"
    return
  }
  $files = Get-ChildItem -Path $src -Recurse -File
  if ($files.Count -eq 0) {
    Write-Warn "tools\$ToolsArch\ is empty - skipping"
    return
  }
  $copied  = 0
  $skipped = 0
  foreach ($file in $files) {
    # Relative path from arch root, e.g. 'Windows\System32\cecho.exe'
    $rel     = $file.FullName.Substring($src.Length).TrimStart('\\')
    $dest    = Join-Path $MountPath $rel
    $destDir = Split-Path $dest -Parent
    $null    = New-Item -ItemType Directory -Path $destDir -Force
    # Skip files that already exist in the WIM and are not ours to overwrite.
    # WIM system files (WerFault.exe etc) are read-only and access-denied.
    # Only overwrite if the destination does not exist yet.
    if (Test-Path $dest) {
      Write-Info "  skip (exists): $rel"
      $skipped++
      continue
    }
    try {
      Copy-Item $file.FullName $dest -Force -ErrorAction Stop
      Write-Info "  overlay: $rel"
      $copied++
    } catch {
      Write-Warn "  access denied - skipping: $rel"
      $skipped++
    }
  }
  Write-OK "Mirrored $copied file(s) from tools\$ToolsArch\ onto WIM root ($skipped skipped)"
}

function Set-WinPEDaRT {
  # Stages DaRT Remote Recovery into the WIM.
  #
  # Priority order:
  #   1. DaRT files already in tools\<arch>\Windows\System32\ (skip everything)
  #   2. Microsoft.Dart module loaded by full .psd1 path from extracted MSI
  #      Uses New-DartConfiguration | Set-DartImage - correct, version-matched
  #   3. Dart_w11.tpk in sources\ (ZIP extraction + overlay)
  #   4. Manual file staging from sources\WinPERDP\ or toolsX64.cab
  #
  # The Microsoft.Dart module is the preferred method - it generates a correct
  # DartConfig.dat. A mismatched DartConfig.dat is the most common cause of
  # inv32.xml not being written on boot.
  # Extract MSDaRT100.msi with: msiexec /a MSDaRT100.msi /qb TARGETDIR=<path>
  # Module path: <path>\v10\Modules\Microsoft.Dart\Microsoft.Dart.psd1
  param(
    [string]$MountPath,
    [string]$BuildRoot,
    [string]$ScratchDir,
    [string]$ToolsRoot,
    [string]$ToolsArch,
    [string]$DaRTModulePath,  # full path to Microsoft.Dart.psd1 in extracted MSI
    [string]$RDPSourceDir,
    [string]$ToolsRDPDir,
    [string]$RDPSourceCab,
    [string]$SevenZip,
    [string]$RemoteMessage = 'Welcome to the WinPE Deployment Environment',
    [int]$RemotePort = 3389
  )

  $sys32 = Join-Path $MountPath 'Windows\System32'

  # ── Method 1: Pre-staged in tools\<arch>\Windows\System32\ ────────────────
  # If RemoteRecovery.exe is already there (placed by the user or a previous
  # build) skip all staging - Copy-Tools will have already overlaid the files.
  $preStaged = Join-Path $ToolsRoot "$ToolsArch\Windows\System32\RemoteRecovery.exe"
  if (Test-Path $preStaged) {
    Write-OK "DaRT pre-staged in tools\$ToolsArch\Windows\System32\ - skipping staging"
    Write-Info "Remove RemoteRecovery.exe from tools\$ToolsArch\ to re-stage from source"
    return
  }

  # ── Method 2: Microsoft.Dart module from extracted MSI ───────────────────────
  # The module cannot be installed normally on ADK 24H2 but loads fine from
  # the extracted MSI location via its full .psd1 path.
  # Extract with: msiexec /a MSDaRT100.msi /qb TARGETDIR=<path>
  # Module is at: <path>\v10\Modules\Microsoft.Dart\Microsoft.Dart.psd1
  Write-Step 'Attempting DaRT staging via Microsoft.Dart module'
  $dartModule = $false

  # Try by module name first (DaRT properly installed)
  # then fall back to full .psd1 path (MSI extracted but not installed)
  try {
    Import-Module 'Microsoft.Dart' -ErrorAction Stop
    $dartModule = $true
    Write-OK 'Microsoft.Dart module loaded (installed)'
  } catch {
    Write-Info 'Microsoft.Dart not installed by name - trying path'
    if ($DaRTModulePath -and (Test-Path $DaRTModulePath)) {
      try {
        Import-Module $DaRTModulePath -ErrorAction Stop
        $dartModule = $true
        Write-OK "Microsoft.Dart module loaded from: $DaRTModulePath"
      } catch {
        Write-Warn "Microsoft.Dart load failed: $($_.Exception.Message)"
        Write-Info 'Falling back to .tpk extraction'
      }
    } else {
      Write-Info 'DaRTModulePath not set or not found - skipping module method'
      Write-Info 'Install DaRT 10 (msiexec /i MSDaRT100.msi) to enable this method'
    }
  }

  if ($dartModule) {
    try {
      Write-Info "Configuring DaRT: port $RemotePort"
      $config = New-DartConfiguration `
        -AddAllTools `
        -RemotePort $RemotePort `
        -RemoteMessage $RemoteMessage
      $config | Set-DartImage -Path $MountPath
      Write-OK "DaRT staged via Microsoft.Dart module (port $RemotePort)"
      Write-OK 'DartConfig.dat generated correctly - inv32.xml will be written on boot'
      return
    } catch {
      Write-Warn "Microsoft.Dart staging failed: $($_.Exception.Message)"
      Write-Info 'Falling back to .tpk extraction'
    }
  }

  # ── Method 3: Extract Dart_w11.tpk (plain ZIP) ───────────────────────────────
  $dartTpk     = Join-Path $BuildRoot 'sources\Dart_w11.tpk'
  $dartExtract = Join-Path $ScratchDir "$BuildArch\DaRT_extract"

  if (Test-Path $dartTpk) {
    Write-Step 'Extracting DaRT from Dart_w11.tpk (ZIP)'
    if (Test-Path $dartExtract) { Remove-Item $dartExtract -Recurse -Force }
    $null = New-Item -ItemType Directory -Path $dartExtract -Force

    & $SevenZip x $dartTpk "-o$dartExtract" -y 2>&1 | ForEach-Object { Write-Info "  7z: $_" }

    if ($LASTEXITCODE -ne 0) {
      Write-Warn ".tpk extraction failed (exit $LASTEXITCODE)"
    } else {
      Write-OK '.tpk extracted'
      $imgFolders = Get-ChildItem $dartExtract -Directory | Sort-Object Name
      foreach ($imgDir in $imgFolders) {
        Write-Info "Overlaying DaRT payload '$($imgDir.Name)'"
        $dartFiles   = Get-ChildItem $imgDir.FullName -Recurse -File
        $dartCopied  = 0
        $dartSkipped = 0
        foreach ($df in $dartFiles) {
          $rel     = $df.FullName.Substring($imgDir.FullName.Length).TrimStart('\')
          $dest    = Join-Path $MountPath $rel
          $destDir = Split-Path $dest -Parent
          $null    = New-Item -ItemType Directory -Path $destDir -Force
          if (Test-Path $dest) { $dartSkipped++; continue }
          try {
            Copy-Item $df.FullName $dest -Force -ErrorAction Stop
            $dartCopied++
          } catch {
            Write-Info "  skip (access denied): $rel"
            $dartSkipped++
          }
        }
        Write-OK "Payload '$($imgDir.Name)': $dartCopied copied, $dartSkipped skipped"
      }
      Remove-Item $dartExtract -Recurse -Force -ErrorAction SilentlyContinue
      Write-OK 'DaRT staged from .tpk'
      return
    }
    Remove-Item $dartExtract -Recurse -Force -ErrorAction SilentlyContinue
  } else {
    Write-Info 'Dart_w11.tpk not found - trying manual staging'
    Write-Info "Place Dart_w11.tpk in $BuildRoot\sources\ or install DaRT 10 for automatic staging"
  }

  # ── Method 4: Manual staging from pre-extracted folder or cab ────────────────
  $required = @(
    'RemoteRecovery.exe','RdpCore.dll','rdpencom.dll','MSDartCmn.dll',
    'LockingHooks.dll','FirewallExceptionChange.dll','WaitForConnection.exe',
    'DartConfig.dat','mfc100u.dll','msvcp100.dll','msvcr100.dll'
  )

  $needExtract = $false
  if (-not (Test-Path $RDPSourceDir)) {
    $needExtract = $true
  } else {
    [string[]]$missing = @($required | Where-Object {
      -not (Test-Path (Join-Path $RDPSourceDir $_))
    })
    if ($missing.Count -gt 0) {
      Write-Warn "$($missing.Count) file(s) missing from $RDPSourceDir - attempting cab extraction"
      $needExtract = $true
    }
  }

  if ($needExtract) {
    if (Test-Path $RDPSourceCab) {
      Write-Step "Extracting DaRT files from $(Split-Path $RDPSourceCab -Leaf)"
      $null = New-Item -ItemType Directory -Path $RDPSourceDir -Force
      $proc7z = Start-Process -FilePath $SevenZip `
        -ArgumentList "e", "`"$RDPSourceCab`"", "-o`"$RDPSourceDir`"", "-y" `
        -Wait -PassThru -NoNewWindow
      if ($proc7z.ExitCode -le 1) {
        Write-OK "Cab extracted to $RDPSourceDir"
      } else {
        Write-Warn "7-Zip extraction failed (exit $($proc7z.ExitCode))"
      }
    } elseif (-not (Test-Path $RDPSourceDir)) {
      Write-Warn 'No DaRT source found - DaRT RDP will not be available'
      Write-Warn 'Options: install DaRT 10, place Dart_w11.tpk in sources\, or populate sources\WinPERDP\'
      return
    }
  }

  [string[]]$stageMissing = @()
  foreach ($f in $required) {
    $src = Join-Path $RDPSourceDir $f
    if (-not (Test-Path $src) -and $ToolsRDPDir) { $src = Join-Path $ToolsRDPDir $f }
    if (Test-Path $src) {
      Copy-Item $src (Join-Path $sys32 $f) -Force
      Write-OK "Staged: $f"
    } else {
      $stageMissing += $f
      Write-Warn "Missing: $f"
    }
  }

  if ($stageMissing.Count -gt 0) {
    Write-Warn "$($stageMissing.Count) DaRT file(s) missing - RemoteRecovery.exe may not work"
    Write-Warn "IMPORTANT: DartConfig.dat must be generated by DaRT Recovery Image Wizard"
    Write-Warn "  Run: msiexec /i MSDaRT100.msi then use Start > DaRT Recovery Image wizard"
  } else {
    Write-OK 'All DaRT files staged to Windows\System32\'
  }
}

function Set-WinPEStartnet {
  # Writes startnet.cmd into the mounted WIM and copies echo.exe
  # from X:\Tools\ into System32 so it is on PATH in the live PE.
  param([string]$MountPath, [string]$ToolsRoot, [string]$ToolsArch)

  # cecho.exe + bginfo.exe + winpe.bgi + wallpaper.bmp are all staged by
  # Copy-Tools from tools\<arch>\Windows\System32\ onto the WIM.
  # They MUST be placed under Windows\System32\ in the tools folder so
  # they land on PATH in the live PE.
  #
  # Correct layout:
  #   tools\amd64\Windows\System32\cecho.exe
  #   tools\amd64\Windows\System32\bginfo.exe
  #   tools\amd64\Windows\System32\winpe.bgi
  #   tools\amd64\Windows\System32\wallpaper.bmp
  #
  # Validate they are present now and warn if not - Copy-Tools runs later.
  $sys32Tools = Join-Path $ToolsRoot "$ToolsArch\Windows\System32"
  # netstart.exe: DaRT binary for network init in StartDaRT.cmd
  #   Source: your .tpk extraction under Windows\System32\ in image 1
  #   Or from DART_EXTRACT\v10\ (it may be there directly)
  # dartparse.exe: custom XML parser for inv32.xml ticket extraction
  foreach ($toolFile in @(
    'cecho.exe',    # colour console output
    'dartparse.exe', # inv32.xml ticket extraction
    'netstart.exe',  # DaRT network init
    'bginfo.exe',    # desktop wallpaper info
    'ntop.exe',      # process monitor
    'jq.exe',        # JSON processor
    'dua.exe',       # disk usage analyser
    'edit.exe',      # text editor
    'screenres.exe'  # screen resolution changer
  )) {
    $tp = Join-Path $sys32Tools $toolFile
    if (Test-Path $tp) {
      Write-OK "$toolFile found"
    } else {
      Write-Warn "$toolFile NOT found - place in tools\$ToolsArch\Windows\System32\"
    }
  }
  foreach ($toolFile in @('winpe.bgi','wallpaper.bmp')) {
    $tp = Join-Path $sys32Tools $toolFile
    if (-not (Test-Path $tp)) {
      Write-Info "Optional: $toolFile not found in tools\$ToolsArch\Windows\System32\ - BGInfo will use defaults"
    }
  }

  # findstr.exe, choice.exe, regedit.exe - copy from build host only when the
  # host architecture matches the target WIM architecture. Copying amd64 binaries
  # into an ARM64 WIM (or vice versa) produces a WIM that fails to boot.
  # If architectures don't match, rely on the tools overlay in tools\<arch>\.
  $hostArch = switch ($env:PROCESSOR_ARCHITECTURE) {
    'AMD64' { 'amd64' }
    'ARM64' { 'arm64' }
    default { 'unknown' }
  }
  $archMatch = ($hostArch -eq $ToolsArch.ToLower()) -or `
               ($hostArch -eq 'amd64' -and $ToolsArch -eq 'amd64')

  if ($archMatch) {
    # regedit.exe lives in %windir% directly, NOT in System32
    $regeditSrc = Join-Path $env:SystemRoot 'regedit.exe'
    $regeditDst = Join-Path $MountPath 'Windows\regedit.exe'
    if (-not (Test-Path $regeditDst)) {
      if (Test-Path $regeditSrc) {
        Copy-Item $regeditSrc $regeditDst -Force
        Write-OK 'regedit.exe copied from build host into Windows\'
      } else {
        Write-Warn 'regedit.exe not found on build host'
      }
    } else {
      Write-Info 'regedit.exe already present in WIM - skipping'
    }

    foreach ($hostBin in @('findstr.exe', 'choice.exe')) {
      $dst = Join-Path $MountPath "Windows\System32\$hostBin"
      if (-not (Test-Path $dst)) {
        $src = Join-Path $env:SystemRoot "System32\$hostBin"
        if (Test-Path $src) {
          Copy-Item $src $dst -Force
          Write-OK "$hostBin copied from build host into Windows\System32\"
        } else {
          Write-Warn "$hostBin not found on build host"
        }
      } else {
        Write-Info "$hostBin already present in WIM - skipping"
      }
    }
  } else {
    Write-Info "Skipping host binary copy: host is $hostArch, WIM target is $($ToolsArch.ToLower())"
    Write-Info 'Place findstr.exe, choice.exe, regedit.exe in tools\<arch>\Windows\System32\ for cross-builds'
  }

  # PowerShell execution policy - set to Unrestricted in the offline WIM hive.
  # In WinPE anyone who has booted the image already has full access - this just
  # removes the friction of policy blocking scripts.
  Write-Step 'Setting PS execution policy to Unrestricted in WIM'
  $psHive = Join-Path $MountPath 'Windows\System32\WindowsPowerShell\v1.0'
  $softwareHive = Join-Path $MountPath 'Windows\System32\config\SOFTWARE'
  try {
    reg load 'HKLM\WinPE_SW' $softwareHive | Out-Null
    reg add 'HKLM\WinPE_SW\Microsoft\PowerShell\1\ShellIds\Microsoft.PowerShell' `
      /v ExecutionPolicy /t REG_SZ /d Unrestricted /f | Out-Null
    Write-OK 'PS ExecutionPolicy set to Unrestricted in WIM SOFTWARE hive'
  } catch {
    Write-Warn "PS execution policy hive write failed: $($_.Exception.Message)"
  } finally {
    [gc]::Collect()
    Start-Sleep -Seconds 1
    reg unload 'HKLM\WinPE_SW' | Out-Null
  }

  # BGInfo staging - copy bginfo.exe and winpe.bgi from tools into the WIM.
  # BGInfo runs at startup, generates a BMP with system info, and sets it
  # as the desktop wallpaper. Config is in winpe.bgi (create on your Win11
  # box: run bginfo.exe, configure fields, File > Save As > winpe.bgi).
  # Suggested fields: Computer Name, IP Address, OS, Build, Date/Time.
  # Place both files in tools\amd64\ (or tools\ARM64\ for ARM64 builds).
  # BGInfo files:
  #   tools\amd64\bginfo.exe     - BGInfo binary
  #   tools\amd64\winpe.bgi      - BGInfo config (fields/layout)
  #   tools\amd64\wallpaper.bmp  - background image (BMP recommended;
  #                                 BGInfo composites text over it)
  # To create winpe.bgi: run bginfo.exe on Win11, configure fields,
  #   set background image to wallpaper.bmp, File > Save As > winpe.bgi
  #
  # Screen resolution: set via Unattend.xml <Display> element (see below).
  # For on-the-fly resolution changes in WinPE, QRES.exe is recommended:
  #   https://www.softpedia.com/get/System/System-Info/QRes.shtml
  #   Place qres.exe in tools\amd64\ and run: qres /x:1920 /y:1080
  #   It has no dependencies and works reliably in WinPE.
  #
  # The Unattend.xml placed at X:\ sets the initial boot resolution.
  # 1024x768 is the safe WinPE default; increase if your display supports it.
  # bginfo.exe, winpe.bgi, wallpaper.bmp staging is handled by Copy-Tools above.
  # See tools\<arch>\Windows\System32\ placement notes in the cecho section.

  $startnet = @'
@echo off
echo+

:: -----------------------------------------------------------------------
:: startnet.cmd - Example Music WinPE startup
:: Runs automatically via winpeshl.ini before the interactive shell opens.
:: -----------------------------------------------------------------------

:: Keyboard layout selection
:: CHOICE waits 30 seconds then defaults to 1 (GB/UK).
:: CHOICE errorlevel: 1=GB/UK, 2=DE, 3=DK, 4=US
cecho.exe  {03} "[INFO] Select keyboard layout - defaulting to British English in 30s..." {\n}{##}
cecho.exe  {0e} "       [1] GB / UK - British English (default)" {\n}{##}
cecho.exe  {0e} "       [2] DE      - Deutsch" {\n}{##}
cecho.exe  {0e} "       [3] DK      - Danske" {\n}{##}
cecho.exe  {0e} "       [4] US      - US English" {\n}{##}
echo+
CHOICE /C 1234 /T 30 /D 1 /N >nul
if errorlevel 4 goto :kb_us
if errorlevel 3 goto :kb_dk
if errorlevel 2 goto :kb_de
if errorlevel 1 goto :kb_gb

:kb_gb
wpeutil SetKeyboardLayout 0409:00000809
wpeutil SetUserLocale en-GB
wpeutil SetMuiLanguage en-GB;en-US
cecho.exe  {0a} "[ OK ] Keyboard layout: British English (GB/UK)" {\n}{##}
goto :kb_done

:kb_de
wpeutil SetKeyboardLayout 0409:00000407
wpeutil SetUserLocale de-DE
wpeutil SetMuiLanguage de-DE;en-US
cecho.exe  {0a} "[ OK ] Keyboard layout: Deutsch (DE)" {\n}{##}
goto :kb_done

:kb_dk
wpeutil SetKeyboardLayout 0409:00000406
wpeutil SetUserLocale da-DK
wpeutil SetMuiLanguage da-DK;en-US
cecho.exe  {0a} "[ OK ] Keyboard layout: Danske (DK)" {\n}{##}
goto :kb_done

:kb_us
wpeutil SetKeyboardLayout 0409:00000409
wpeutil SetUserLocale en-US
wpeutil SetMuiLanguage en-US
cecho.exe  {0a} "[ OK ] Keyboard layout: US English (US)" {\n}{##}
goto :kb_done

:kb_done
echo+

:: -----------------------------------------------------------------------
:: Remove MiniNT registry key so PowerShell 7 runs correctly.
:: WinPE sets HKLM\SYSTEM\CurrentControlSet\Control\MiniNT which causes
:: pwsh.exe to abort on launch with a cryptic exit code.
:: This is safe - the key only affects .NET host detection logic.
:: -----------------------------------------------------------------------
reg query "HKLM\SYSTEM\CurrentControlSet\Control\MiniNT" >nul 2>&1
if not errorlevel 1 (
  reg delete "HKLM\SYSTEM\CurrentControlSet\Control\MiniNT" /f >nul 2>&1
  cecho.exe  {0a} "[ OK ] MiniNT registry key removed (pwsh.exe enabled)" {\n}{##}
)

:: Networking
cecho.exe  {03} "[INFO] Starting networking... please wait..." {\n}{##}
echo+
wpeutil InitializeNetwork
ping -n 6 127.0.0.1 >nul

:: Get IP for banner footer
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /i "IPv4"') do (
  set IP=%%A
  goto :gotip
)
:gotip
set IP=%IP: =%
set "IPF=%IP%               "
set "IPF=%IPF:~0,15%"

:: Firewall
cecho.exe  {03} "[INFO] Disabling firewall..." {\n}{##}
echo+
wpeutil DisableFirewall

:: Map Z: drive - ask first, default to Yes after 30 seconds
echo+
cecho.exe  {03} "[INFO] Map a deployment share to Z: ? Defaulting to Yes in 30s..." {\n}{##}
cecho.exe  {0e} "       [1] Yes - map a share  [2] No - skip" {\n}{##}
echo+
CHOICE /C 12 /T 30 /D 1 /N >nul
if errorlevel 2 goto :share_skip
if errorlevel 1 goto :share_map

:share_map
cecho.exe  {03} "[INFO] Please enter the deployment server details below." {\n}{##}
echo+
SET /P DEPLOY_HOST=  Deploy server (IP or hostname, e.g. 192.168.1.50): 
SET /P DEPLOY_SHARE=  Share name (e.g. DeployTools): 
SET /P DEPLOY_USER=  Username (e.g. JUKEBOX\Administrator): 
echo+
cecho.exe  {03} "[INFO] Mapping Z: to \\%DEPLOY_HOST%\%DEPLOY_SHARE% ..." {\n}{##}
NET USE Z: \\%DEPLOY_HOST%\%DEPLOY_SHARE% /USER:%DEPLOY_USER% *
echo+
goto :share_done

:share_skip
cecho.exe  {0e} "[WARN] Share mapping skipped - Z: drive not mapped" {\n}{##}
echo+

:share_done

:: -----------------------------------------------------------------------
:: Hypervisor + architecture detection
:: -----------------------------------------------------------------------
set ARCH=unknown
set PLATFORM=unknown
set LOG=X:\vm_detect.log
echo [INFO] WinPE hypervisor detection > %LOG%

set OSARCH=
for /f "tokens=3" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PROCESSOR_ARCHITECTURE 2^>nul') do set OSARCH=%%A
if /i "%OSARCH%"=="AMD64" set ARCH=x64
if /i "%OSARCH%"=="ARM64" set ARCH=arm64
if "%ARCH%"=="unknown" set ARCH=%PROCESSOR_ARCHITECTURE%
echo [INFO] ARCH=%ARCH% >> %LOG%

set BIOS=
for /f "tokens=1,2,*" %%A in ('reg query "HKLM\HARDWARE\DESCRIPTION\System\BIOS" /v SystemManufacturer 2^>nul') do set BIOS=%%C
echo [INFO] BIOS=%BIOS% >> %LOG%

echo %BIOS% | findstr /i "vmware" >nul && set PLATFORM=vmware
echo %BIOS% | findstr /i "qemu" >nul && set PLATFORM=kvm
echo %BIOS% | findstr /i "bochs" >nul && set PLATFORM=kvm
echo %BIOS% | findstr /i "microsoft corporation" >nul && set PLATFORM=hyperv

set PROD=
for /f "tokens=1,2,*" %%A in ('reg query "HKLM\HARDWARE\DESCRIPTION\System\BIOS" /v SystemProductName 2^>nul') do set PROD=%%C
echo %PROD% | findstr /i "standard pc" >nul && set PLATFORM=kvm
echo %PROD% | findstr /i "vmware" >nul && set PLATFORM=vmware
echo [INFO] PLATFORM=%PLATFORM% >> %LOG%

cecho.exe  {03} " *******************************************************************************************" {\n}{##}
cecho.exe  {03} " **                          Hypervisor + Architecture Summary                            **" {\n}{##}
cecho.exe  {03} " *******************************************************************************************" {\n}{##}
cecho.exe  {0a} "   Architecture : %ARCH%" {\n}{##}
cecho.exe  {0a} "   Platform     : %PLATFORM%" {\n}{##}
cecho.exe  {03} " **                                                                                       **" {\n}{##}
cecho.exe  {0e} "   Drivers injected at build time - no runtime loading needed" {\n}{##}
cecho.exe  {0e} "   For V2V migrations, driver store is at:" {\n}{##}
cecho.exe  {0e} "     X:\Windows\System32\DriverStore\FileRepository\" {\n}{##}
cecho.exe  {03} " *******************************************************************************************" {\n}{##}
echo+

:: -----------------------------------------------------------------------
:: BGInfo - set desktop wallpaper with system info
:: -----------------------------------------------------------------------
if not exist %SystemRoot%\System32\bginfo.exe goto bginfo_skip

if exist %SystemRoot%\System32\winpe.bgi (
  %SystemRoot%\System32\bginfo.exe %SystemRoot%\System32\winpe.bgi /accepteula /timer:0 /silent
) else (
  %SystemRoot%\System32\bginfo.exe /accepteula /timer:0 /silent
  cecho.exe  {0e} "[WARN] BGInfo using default config (winpe.bgi not found)" {\n}{##}
)

RUNDLL32.EXE user32.dll,UpdatePerUserSystemParameters ,1 ,True
cecho.exe  {0a} "[ OK ] BGInfo wallpaper set and refreshed" {\n}{##}
goto bginfo_done

:bginfo_skip
cecho.exe  {0e} "[WARN] bginfo.exe not found - wallpaper not set" {\n}{##}

:bginfo_done
echo+

:: -----------------------------------------------------------------------
:: DaRT connection details
:: RemoteRecovery.exe runs in the background (launched by StartDaRT.cmd).
:: We read inv32.xml to get the ticket ID for display in the banner.
:: Remote operators connect any time using the DaRT Remote Connection Viewer.
:: -----------------------------------------------------------------------
set ID=
if not exist %SystemRoot%\System32\RemoteRecovery.exe goto dart_unavailable

set DART_WAIT=0
:dart_wait_loop
if exist %SystemRoot%\System32\inv32.xml goto dart_parse
if %DART_WAIT% GEQ 10 goto dart_timeout
ping -n 2 127.0.0.1 >nul
set /a DART_WAIT+=1
goto dart_wait_loop

:dart_timeout
cecho.exe  {0e} "[WARN] DaRT not available - inv32.xml not found after 10s" {\n}{##}
cecho.exe  {0e} "       (DaRT failure is non-fatal - continuing)" {\n}{##}
goto dart_done

:dart_parse
if exist %SystemRoot%\System32\dartparse.exe (
  for /f "delims=" %%A in ('dartparse.exe /g ID /b /f inv32.xml') do set "ID=%%A"
) else (
  set DART_RAW=
  for /f "tokens=2 delims==" %%T in ('findstr /i "<A " %SystemRoot%\System32\inv32.xml') do set DART_RAW=%%T
  if defined DART_RAW set ID=%DART_RAW:">=%
  if defined ID set ID=%ID:"=%
)
cecho.exe  {0a} "[ OK ] DaRT running - Ticket: %ID% - IP: %IPF% - Port: 3389" {\n}{##}
goto dart_done

:dart_unavailable
cecho.exe  {0e} "[WARN] RemoteRecovery.exe not found - RDP not available" {\n}{##}

:dart_done
echo+

:: -----------------------------------------------------------------------
:: Banner
:: -----------------------------------------------------------------------
cecho.exe  {03} " *************************************************************************************************" {\n}{##}
cecho.exe  {03} " **                                     Example Music Group                                     **" {\n}{##}
cecho.exe  {03} " **                            WinPE Deployment Environment Ready                               **" {\n}{##}
cecho.exe  {03} " *************************************************************************************************" {\n}{##}
cecho.exe  {03} " **                                                                                             **" {\n}{##}
cecho.exe  {03} " ** {0F} To install Windows, run setup.exe then copy the panther file: {03}                             **" {\n}{##}
cecho.exe  {03} " **                                                                                             **" {\n}{##}
cecho.exe  {03} " ** {0a} 1.) X:\Sources\setup.exe /unattend:Z:\unattend_xml\file.xml /noreboot                     {03} **" {\n}{##}
cecho.exe  {03} " ** {0a} 2.) mkdir C:\Windows\Setup\Scripts                                                        {03} **" {\n}{##}
cecho.exe  {03} " ** {0a} 3.) COPY Z:\panther\setupcomplete.cmd C:\Windows\Setup\Scripts\                           {03} **" {\n}{##}
cecho.exe  {03} " **                                                                                             **" {\n}{##}
cecho.exe  {03} " **~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~( {0F}Other Information{03} )~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~**" {\n}{##}
cecho.exe  {03} " **                                                                                             **" {\n}{##}
cecho.exe  {03} " **  {0e} (o) Tools such as wget and utilities live in X:\Tools\ {03}                                   **" {\n}{##}
cecho.exe  {03} " **  {0e} (o) Open DaRT Remote Connection Viewer - NOT mstsc - and enter the below values {03}          **" {\n}{##}
cecho.exe  {03} " **  {0e}     Raw XML: %SystemRoot%\System32\inv32.xml {03}                                               **" {\n}{##}
cecho.exe  {03} " **  {0e} (o) Answer files live in Z:\unattend_xml\ {03}                                                **" {\n}{##}
cecho.exe  {03} " **  {0e} (o) Post-install (panther) scripts live in Z:\Panther\ {03}                                   **" {\n}{##}
cecho.exe  {03} " **  {0e} (o) Remember to rename the computer after installing Windows {03}                             **" {\n}{##}
cecho.exe  {03} " **  {0e} (o) The V2V migrations driver store is: X:\Windows\System32\DriverStore\FileRepository\ {03}  **" {\n}{##}
cecho.exe  {03} " **                                                                                             **" {\n}{##}
cecho.exe  {03} " *************************************************************************************************" {\n}{##}
cecho.exe  {03} " **  DeployPE v 1.09      **  {0F}Architecture: %ARCH%    {03}**{0F} Platform: %PLATFORM% {03}  **{04} Internal Use Only   {03}**" {\n}{##}
cecho.exe  {03} " **  {0a}IP: %IPF% {03} ** {0a} Ticket: %ID% {03} **{0a} RDP Port: 3389     {03}** {01}Example {0f}Music {04}Group {03}**" {\n}{##}
cecho.exe  {03} " *************************************************************************************************" {\n}{##}
echo+

:: startnet.cmd exits here - cmd.exe /k in winpeshl.ini keeps the session alive.

'@

  $startnetPath = Join-Path $MountPath 'Windows\System32\startnet.cmd'
  Set-Content -Path $startnetPath -Value $startnet -Encoding ASCII
  Write-OK 'startnet.cmd written to Windows\System32\'

  # Write Unattend.xml to WIM root for screen resolution.
  # 1280x720 is a good default for virtual machines - change as needed.
  # DaRT no longer uses this; it's purely for display initialisation.
  $displayUnattend = @'
<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
  <settings pass="windowsPE">
    <component name="Microsoft-Windows-Setup"
      processorArchitecture="amd64"
      publicKeyToken="31bf3856ad364e35"
      language="neutral"
      versionScope="nonSxS"
      xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
      <Display>
        <ColorDepth>32</ColorDepth>
        <HorizontalResolution>1280</HorizontalResolution>
        <RefreshRate>60</RefreshRate>
        <VerticalResolution>720</VerticalResolution>
      </Display>
    </component>
  </settings>
</unattend>
'@
  $unattendPath = Join-Path $MountPath 'Unattend.xml'
  Set-Content -Path $unattendPath -Value $displayUnattend -Encoding UTF8
  Write-OK 'Unattend.xml written - display resolution 1280x720'
}

function Install-WinPEPS7 {
  # Expands PS7 ZIP into the WIM and updates the SYSTEM hive so pwsh.exe
  # is on PATH and PSModulePath includes both PS7 and PS5.1 module paths.
  # Also sets LOCALAPPDATA/APPDATA/HOMEDRIVE/HOMEPATH for PS Gallery support.
  # Ref: https://www.deploymentresearch.com/adding-powershell-7-to-winpe/
  param(
    [string]$MountPath,
    [string]$PS7Zip,      # full path to PowerShell-7.x.x-win-<arch>.zip
    [string]$BuildArch    # amd64 or arm64
  )

  if (-not (Test-Path $PS7Zip)) {
    Write-Warn "PS7 ZIP not found: $PS7Zip"
    Write-Warn 'Download from https://github.com/PowerShell/PowerShell/releases'
    Write-Warn 'Place the win-x64 or win-arm64 ZIP in sources\ and re-run'
    return
  }

  Write-Step "Installing PowerShell 7 from $(Split-Path $PS7Zip -Leaf)"
  $ps7Dest = Join-Path $MountPath 'Program Files\PowerShell\7'
  $null = New-Item -ItemType Directory -Path $ps7Dest -Force
  Expand-Archive -Path $PS7Zip -DestinationPath $ps7Dest -Force
  Write-OK "PS7 expanded to $ps7Dest"

  # Update SYSTEM hive - Path, PSModulePath, and PS Gallery env vars
  $hive = Join-Path $MountPath 'Windows\System32\config\SYSTEM'
  try {
    reg load 'HKLM\WinPE_SYS' $hive | Out-Null
    Start-Sleep -Seconds 2
    $key = 'HKLM:\WinPE_SYS\ControlSet001\Control\Session Manager\Environment'

    # PATH - append PS7 folder
    $curPath = (Get-Item $key).GetValue('Path','','DoNotExpandEnvironmentNames')
    $newPath = $curPath + ';%ProgramFiles%\PowerShell\7\'
    New-ItemProperty $key -Name Path -PropertyType ExpandString `
      -Value $newPath -Force | Out-Null

    # PSModulePath - include PS7, PS5.1, and system profile paths
    $curMod = (Get-Item $key).GetValue('PSModulePath','','DoNotExpandEnvironmentNames')
    $newMod = $curMod + `
      ';%ProgramFiles%\PowerShell\' + `
      ';%ProgramFiles%\PowerShell\7\' + `
      ';%SystemRoot%\system32\config\systemprofile\Documents\PowerShell\Modules\'
    New-ItemProperty $key -Name PSModulePath -PropertyType ExpandString `
      -Value $newMod -Force | Out-Null

    # PS Gallery support env vars
    New-ItemProperty $key -Name APPDATA -PropertyType String `
      -Value '%SystemRoot%\System32\Config\SystemProfile\AppData\Roaming' `
      -Force | Out-Null
    New-ItemProperty $key -Name HOMEDRIVE -PropertyType String `
      -Value '%SystemDrive%' -Force | Out-Null
    New-ItemProperty $key -Name HOMEPATH -PropertyType String `
      -Value '%SystemRoot%\System32\Config\SystemProfile' -Force | Out-Null
    New-ItemProperty $key -Name LOCALAPPDATA -PropertyType String `
      -Value '%SystemRoot%\System32\Config\SystemProfile\AppData\Local' `
      -Force | Out-Null
    # Suppress PS7 update nags in WinPE
    New-ItemProperty $key -Name POWERSHELL_UPDATECHECK `
      -Value 'LTS' -Force | Out-Null

    Write-OK 'PS7 environment variables written to SYSTEM hive'
  } catch {
    Write-Warn "PS7 hive update failed: $($_.Exception.Message)"
  } finally {
    Remove-Variable key -ErrorAction SilentlyContinue
    [gc]::Collect()
    Start-Sleep -Seconds 3
    reg unload 'HKLM\WinPE_SYS' | Out-Null
  }

  # PS7 execution policy - write into the PS7-specific hive path
  # PS7 uses a different registry path than PS5.1
  $sw = Join-Path $MountPath 'Windows\System32\config\SOFTWARE'
  try {
    reg load 'HKLM\WinPE_SW7' $sw | Out-Null
    Start-Sleep -Seconds 1
    reg add 'HKLM\WinPE_SW7\Microsoft\PowerShell\1\ShellIds\Microsoft.PowerShell' `
      /v ExecutionPolicy /t REG_SZ /d Unrestricted /f | Out-Null
    # PS7 also checks this path
    reg add 'HKLM\WinPE_SW7\Microsoft\PowerShell\1\ShellIds\pwsh' `
      /v ExecutionPolicy /t REG_SZ /d Unrestricted /f | Out-Null
    Write-OK 'PS7 ExecutionPolicy set to Unrestricted'
  } catch {
    Write-Warn "PS7 execution policy hive write failed: $($_.Exception.Message)"
  } finally {
    [gc]::Collect()
    Start-Sleep -Seconds 1
    reg unload 'HKLM\WinPE_SW7' | Out-Null
  }

  Write-OK "PowerShell 7 installed - launch with: pwsh.exe"
}

function Install-WinPEPSGallery {
  # Saves PS Gallery modules from the build host into the mounted WIM.
  # Also injects the LOCALAPPDATA registry fix so PackageManagement works
  # at runtime in WinPE without a network call to the Gallery.
  #
  # The WIM module path is: Windows\System32\WindowsPowerShell\v1.0\Modules\
  # This is on the default PSModulePath in WinPE so modules load without
  # any profile or path manipulation.
  param(
    [string]$MountPath,
    [string[]]$Modules,           # saved to both PS5.1 and PS7 paths
    [string[]]$ModulesPS7Only = @() # saved to PS7 path only
  )

  if ($Modules.Count -eq 0 -and $ModulesPS7Only.Count -eq 0) {
    Write-Warn 'No PS Gallery modules configured - skipping'
    return
  }

  # Ensure PSGallery is trusted on the build host so Save-Module does not prompt
  $repo = Get-PSRepository -Name PSGallery -ErrorAction SilentlyContinue
  if (-not $repo) {
    Write-Warn 'PSGallery repository not found on build host - skipping PS Gallery modules'
    Write-Warn 'Run: Register-PSRepository -Default; Set-PSRepository PSGallery -InstallationPolicy Trusted'
    return
  }
  if ($repo.InstallationPolicy -ne 'Trusted') {
    Write-Info 'Setting PSGallery as trusted on build host'
    Set-PSRepository -Name PSGallery -InstallationPolicy Trusted
  }

  # Ensure NuGet provider is available - Save-Module needs it
  $nuget = Get-PackageProvider -Name NuGet -ErrorAction SilentlyContinue
  if (-not $nuget -or $nuget.Version -lt [version]'2.8.5.201') {
    Write-Info 'Installing NuGet provider on build host'
    Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force | Out-Null
  }

  # Destination module path inside the mounted WIM - PS5.1 path
  $wimModulePath = Join-Path $MountPath `
    'Windows\System32\WindowsPowerShell\v1.0\Modules'

  # Also save to PS7 module path if PS7 is installed in the WIM
  $ps7ModulePath = Join-Path $MountPath 'Program Files\PowerShell\7\Modules'

  # Module routing:
  #   $Modules (both):        PSWriteColor, Terminal-Icons, PSReadLine -> PS5.1 + PS7
  #   $ModulesPS7Only (PS7):  CompletionPredictor, ConsoleGuiTools etc -> PS7 only
  #   PackageManagement/PowerShellGet always go to PS5.1 path only
  $ps51Modules = @('PackageManagement', 'PowerShellGet')
  $bothModules = $Modules
  $ps7Available    = (Test-Path $ps7ModulePath)

  function Save-ToPath {
    param([string]$Mod, [string]$Path, [string]$Label)
    $destDir = Join-Path $Path $Mod
    if (Test-Path $destDir) {
      Write-Info "Module already present ($Label): $Mod"
      return
    }
    try {
      Save-Module -Name $Mod -Path $Path -Force -ErrorAction Stop
      Write-OK "Saved ($Label): $Mod"
    } catch {
      Write-Warn "Failed to save $Mod to $Label`: $($_.Exception.Message)"
    }
  }

  Write-Info 'Staging PS5.1 modules (PackageManagement, PowerShellGet, common)'
  foreach ($mod in ($ps51Modules + $bothModules)) {
    Save-ToPath -Mod $mod -Path $wimModulePath -Label 'PS5.1'
  }

  if ($ps7Available) {
    Write-Info 'Staging PS7 modules (common + PS7-only)'
    foreach ($mod in ($bothModules + $ModulesPS7Only)) {
      Save-ToPath -Mod $mod -Path $ps7ModulePath -Label 'PS7'
    }
  } else {
    Write-Warn "PS7 not installed in WIM - skipping PS7-only modules ($($ModulesPS7Only -join ', '))"
  }

  # ── LOCALAPPDATA registry fix ───────────────────────────────────────────
  # WinPE has no HKCU\Volatile Environment, so LOCALAPPDATA is undefined.
  # PackageManagement and PowerShellGet fail silently without it.
  # Fix: load the WIM's SOFTWARE hive, add a SpecialFolders key that sets
  # LOCALAPPDATA, then unload.
  #
  # We also write a small profile script that sets the env var at PS startup
  # as a belt-and-braces approach since registry injection into HKCU offline
  # is unreliable - WinPE creates a fresh HKCU at boot from the default hive.
  Write-Step 'Injecting LOCALAPPDATA fix for PS Gallery in WinPE'

  # Belt: PowerShell profile that sets LOCALAPPDATA if undefined
  $psProfileDir = Join-Path $MountPath `
    'Windows\System32\WindowsPowerShell\v1.0'
  $profilePath = Join-Path $psProfileDir 'profile.ps1'
  $profileContent = @'
# WinPE PowerShell profile - injected by Build-WinPE.ps1

# LOCALAPPDATA fix - required for PackageManagement and PowerShellGet
if (-not $env:LOCALAPPDATA) {
  $env:LOCALAPPDATA = $env:TEMP
}

# PSGallery registration
if (-not (Get-PSRepository -Name PSGallery -ErrorAction SilentlyContinue)) {
  Register-PSRepository -Default -ErrorAction SilentlyContinue
  Set-PSRepository -Name PSGallery -InstallationPolicy Trusted -ErrorAction SilentlyContinue
}

# Enable Terminal-Icons (requires Nerd Font terminal - CascadiaCode NF etc.)
Import-Module PSWriteColor -ErrorAction SilentlyContinue
Import-Module Terminal-Icons -ErrorAction SilentlyContinue
Set-PSReadLineOption -PredictionSource HistoryAndPlugin -ErrorAction SilentlyContinue
Set-PSReadLineOption -PredictionViewStyle ListView -ErrorAction SilentlyContinue
'@
  Set-Content -Path $profilePath -Value $profileContent -Encoding UTF8
  Write-OK 'PS5.1 profile written'

  # Write same profile to PS7 path if PS7 is installed in the WIM
  $ps7ProfileDir = Join-Path $MountPath 'Program Files\PowerShell\7'
  if (Test-Path $ps7ProfileDir) {
    $ps7ProfilePath = Join-Path $ps7ProfileDir 'profile.ps1'
    Set-Content -Path $ps7ProfilePath -Value $profileContent -Encoding UTF8
    Write-OK 'PS7 profile written (pwsh.exe will auto-load on launch)'
  }

  # Braces: inject into the WIM DEFAULT user hive so it applies to any user
  $defaultHive = Join-Path $MountPath 'Users\Default\NTUSER.DAT'
  if (Test-Path $defaultHive) {
    try {
      reg load 'HKLM\WinPE_Default' $defaultHive | Out-Null
      reg add 'HKLM\WinPE_Default\Volatile Environment' /f | Out-Null
      reg add 'HKLM\WinPE_Default\Volatile Environment' `
        /v LOCALAPPDATA /t REG_EXPAND_SZ /d '%TEMP%' /f | Out-Null
      Write-OK 'LOCALAPPDATA injected into DEFAULT user hive'
    } catch {
      Write-Warn "Hive injection failed: $($_.Exception.Message)"
    } finally {
      [gc]::Collect()
      Start-Sleep -Seconds 1
      reg unload 'HKLM\WinPE_Default' | Out-Null
    }
  } else {
    Write-Warn "Default user hive not found at $defaultHive - skipping registry fix"
  }

  Write-OK "PS Gallery modules staged. Load in WinPE with: Import-Module <name>"
}

function Install-WinPEWindowsTerminal {
  # Downloads the Windows Terminal portable (unpackaged) ZIP from GitHub,
  # extracts it into the WIM at X:\Tools\WindowsTerminal\, creates the
  # .portable marker file so settings stay local, and adds a wt.cmd wrapper
  # to X:\Windows\System32\ so typing 'wt' launches it.
  #
  # The portable ZIP bundles Microsoft.UI.Xaml and all dependencies, so no
  # additional packages are needed. WinPE build 19041+ is required.
  #
  # Note: WindowsTerminal.exe cannot be run directly - launch via wt.exe.
  param(
    [string]$MountPath,
    [string]$ScratchDir,
    [string]$BuildArch,   # amd64 only - no arm64 portable zip from Microsoft
    [string]$ToolsRoot,   # needed for font staging
    [string]$ToolsArch    # needed for font staging
  )

  if ($BuildArch -ne 'amd64') {
    Write-Warn 'Windows Terminal portable ZIP is x64 only - skipping on ARM64'
    return
  }

  # Query GitHub releases API for the latest stable portable ZIP
  Write-Step 'Finding latest Windows Terminal portable release'
  $apiUrl = 'https://api.github.com/repos/microsoft/terminal/releases/latest'
  $wtZipCache = Join-Path $ScratchDir 'WindowsTerminal_portable.zip'

  try {
    $releaseJson = & curl.exe -L --silent --show-error `
      -H 'Accept: application/vnd.github+json' $apiUrl 2>&1
    # Find the x64 portable ZIP asset URL
    $wtZipUrl = [regex]::Match(
      $releaseJson,
      '"browser_download_url":\s*"(https://[^"]+_x64\.zip)"'
    ).Groups[1].Value
    if (-not $wtZipUrl) {
      Write-Warn 'Could not parse Windows Terminal ZIP URL from GitHub API'
      Write-Warn 'Check https://github.com/microsoft/terminal/releases and'
      Write-Warn 'place the x64 portable ZIP at sources\WindowsTerminal_x64.zip'
      # Try local fallback
      $localZip = Join-Path (Split-Path $MountPath -Parent) `
        '..\sources\WindowsTerminal_x64.zip'
      if (Test-Path $localZip) {
        $wtZipCache = $localZip
        Write-OK "Using local ZIP: $localZip"
      } else {
        return
      }
    } else {
      Write-Info "Downloading: $wtZipUrl"
      & curl.exe -L --silent --show-error --progress-bar -o $wtZipCache $wtZipUrl
      if (-not (Test-Path $wtZipCache)) {
        Write-Warn 'Windows Terminal ZIP download failed - skipping'
        return
      }
      $dlMB = [math]::Round((Get-Item $wtZipCache).Length / 1MB, 1)
      Write-OK "Downloaded Windows Terminal ZIP ($dlMB MB)"
    }
  } catch {
    Write-Warn "Windows Terminal download failed: $($_.Exception.Message)"
    return
  }

  # Extract into WIM at Tools\WindowsTerminal\
  $wtDest = Join-Path $MountPath 'Tools\WindowsTerminal'
  $null = New-Item -ItemType Directory -Path $wtDest -Force
  Write-Step 'Extracting Windows Terminal into WIM'
  Expand-Archive -Path $wtZipCache -DestinationPath $wtDest -Force

  # The ZIP extracts with a versioned subfolder - flatten it so wt.exe is
  # directly under Tools\WindowsTerminal\
  $subFolder = Get-ChildItem $wtDest -Directory | Select-Object -First 1
  if ($subFolder) {
    Get-ChildItem $subFolder.FullName | Move-Item -Destination $wtDest -Force
    Remove-Item $subFolder.FullName -Recurse -Force
  }

  # Create .portable marker so settings live next to wt.exe (no LOCALAPPDATA needed)
  $portableMarker = Join-Path $wtDest '.portable'
  Set-Content -Path $portableMarker -Value '' -Encoding ASCII
  Write-OK 'Portable mode marker created (.portable)'

  # Verify wt.exe is present
  $wtExe = Join-Path $wtDest 'wt.exe'
  if (-not (Test-Path $wtExe)) {
    Write-Warn 'wt.exe not found after extraction - check ZIP structure'
    return
  }

  # Write settings.json into the portable settings folder.
  # PS7 uses a direct commandline path since Windows.Terminal.PowershellCore
  # source is not registered in WinPE. Azure Cloud Shell is hidden.
  # JetBrainsMono Nerd Font set as default - requires font staged below.
  # Default profile is Windows PowerShell (always present in WinPE);
  # if PS7 is installed it will also appear in the profile list.
  $wtSettingsDir = Join-Path $wtDest 'settings'
  $null = New-Item -ItemType Directory -Path $wtSettingsDir -Force
  $wtSettingsJson = @'
{
    "$help": "https://aka.ms/terminal-documentation",
    "$schema": "https://aka.ms/terminal-profiles-schema",
    "actions": [
        {
            "command": { "action": "copy", "singleLine": false },
            "id": "User.copy.644BA8F2"
        },
        { "command": "paste", "id": "User.paste" },
        {
            "command": { "action": "splitPane", "split": "auto", "splitMode": "duplicate" },
            "id": "User.splitPane.A6751878"
        },
        { "command": "find", "id": "User.find" }
    ],
    "copyFormatting": "none",
    "copyOnSelect": false,
    "defaultProfile": "{61c54bbd-c2c6-5271-96e7-009a87ff44bf}",
    "keybindings": [
        { "id": "User.copy.644BA8F2", "keys": "ctrl+c" },
        { "id": "User.paste", "keys": "ctrl+v" },
        { "id": "User.find", "keys": "ctrl+shift+f" },
        { "id": "User.splitPane.A6751878", "keys": "alt+shift+d" }
    ],
    "newTabMenu": [{ "type": "remainingProfiles" }],
    "profiles": {
        "defaults": {
            "font": {
                "face": "JetBrainsMono Nerd Font",
                "size": 11
            }
        },
        "list": [
            {
                "commandline": "%ProgramFiles%\\PowerShell\\7\\pwsh.exe",
                "guid": "{574e775e-4f2a-5b96-ac1e-a2962a402336}",
                "hidden": false,
                "name": "PowerShell 7",
                "icon": "ms-appx:///ProfileIcons/{574e775e-4f2a-5b96-ac1e-a2962a402336}.png"
            },
            {
                "commandline": "%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                "guid": "{61c54bbd-c2c6-5271-96e7-009a87ff44bf}",
                "hidden": false,
                "name": "Windows PowerShell"
            },
            {
                "commandline": "%SystemRoot%\\System32\\cmd.exe",
                "guid": "{0caa0dad-35be-5f56-a8ff-afceeeaa6101}",
                "hidden": false,
                "name": "Command Prompt"
            },
            {
                "guid": "{b453ae62-4e3d-5e58-b989-0a998ec441b8}",
                "hidden": true,
                "name": "Azure Cloud Shell",
                "source": "Windows.Terminal.Azure"
            }
        ]
    },
    "schemes": [],
    "themes": []
}
'@
  Set-Content -Path (Join-Path $wtSettingsDir 'settings.json') `
    -Value $wtSettingsJson -Encoding UTF8
  Write-OK 'settings.json written to Terminal settings folder'

  # Stage JetBrainsMono Nerd Font files into Windows\Fonts\ in the WIM.
  # Place font files in tools\amd64\fonts\ (TTF or OTF).
  # Download JetBrainsMono.zip from:
  # https://github.com/ryanoasis/nerd-fonts/releases/latest
  # Fonts live in tools\<arch>\Windows\System32\fonts\ (matching the overlay layout)
  $fontsToolsDir = Join-Path $ToolsRoot "$ToolsArch\Windows\System32\fonts"
  $wimFontsDir   = Join-Path $MountPath 'Windows\Fonts'
  if (Test-Path $fontsToolsDir) {
    $fontFiles = Get-ChildItem $fontsToolsDir -Include '*.ttf','*.otf' -Recurse
    if ($fontFiles.Count -gt 0) {
      foreach ($f in $fontFiles) {
        Copy-Item $f.FullName (Join-Path $wimFontsDir $f.Name) -Force
        Write-OK "Font staged: $($f.Name)"
      }
      # Register fonts in the offline WIM registry so GDI can find them
      $swHive = Join-Path $MountPath 'Windows\System32\config\SOFTWARE'
      try {
        reg load 'HKLM\WinPE_FONTS' $swHive | Out-Null
        Start-Sleep -Seconds 1
        foreach ($f in $fontFiles) {
          $fontName = $f.BaseName + ' (TrueType)'
          reg add 'HKLM\WinPE_FONTS\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts' `
            /v $fontName /t REG_SZ /d $f.Name /f | Out-Null
        }
        Write-OK "$($fontFiles.Count) font(s) registered in WIM registry"
      } catch {
        Write-Warn "Font registry write failed: $($_.Exception.Message)"
      } finally {
        [gc]::Collect()
        Start-Sleep -Seconds 1
        reg unload 'HKLM\WinPE_FONTS' | Out-Null
      }
    } else {
      Write-Warn "No font files found in $fontsToolsDir"
      Write-Warn 'Terminal will fall back to Cascadia Mono (JetBrainsMono glyphs will not render)'
    }
  } else {
    Write-Warn "Font tools folder not found: $fontsToolsDir"
    Write-Warn 'Place TTF files in tools\<arch>\Windows\System32\fonts\'
    Write-Warn 'Required: JetBrainsMonoNerdFont-Regular.ttf, SymbolsNerdFont-Regular.ttf, SymbolsNerdFontMono-Regular.ttf'
  }

  # Write a wt.cmd wrapper to System32 so 'wt' works from any prompt
  $wtCmd = Join-Path $MountPath 'Windows\System32\wt.cmd'
  $wtCmdContent = "@echo off`r`nX:\Tools\WindowsTerminal\wt.exe %*`r`n"
  Set-Content -Path $wtCmd -Value $wtCmdContent -Encoding ASCII
  Write-OK "wt.cmd wrapper written to System32 - type 'wt' to launch Terminal"

  Write-OK 'Windows Terminal portable installed at X:\Tools\WindowsTerminal\'
  Write-Info 'Launch with: wt  (or wt -p "PowerShell 7" to open PS7 directly)'
}

# -----------------------------------------------------------------------------
# FUNCTIONS -- BCD construction
# Builds a minimal WinPE BCD store from scratch using bcdedit.
# The store is created as a file (not the live system BCD) then placed into
# the iPXE output folder and the ISO media folder.
#
# BCD GUID conventions used here:
#   {bootmgr}  -- the Windows Boot Manager entry
#   {default}  -- the default boot entry (points at our ramdisk loader)
#   {ramdiskoptions} -- ramdisk options shared across entries
#
# The ramdisk device points at boot.wim via a ramdisk SDI device.
# The path inside the WIM must match exactly what bootmgr expects.
# -----------------------------------------------------------------------------

function New-WinPEBCD {
  # Builds a WinPE BCD store from scratch via bcdedit.
  # BootMode 'BIOS' uses winload.exe and the BIOS boot manager path.
  # BootMode 'UEFI' uses winload.efi and the EFI boot manager path.
  param(
    [string]$BCDPath,               # full path where the BCD file will be written
    [string]$BootSDIPath,           # path to boot.sdi (informational only - not embedded)
    [string]$Arch,                  # amd64 or arm64
    [ValidateSet('BIOS','UEFI')]
    [string]$BootMode = 'BIOS'
  )

  if (Test-Path $BCDPath) { Remove-Item $BCDPath -Force }

  Write-Info "Creating $BootMode BCD store at $BCDPath"
  & bcdedit /createstore $BCDPath | Out-Null

  # Ramdisk options - identical for BIOS and UEFI
  & bcdedit /store $BCDPath /create '{ramdiskoptions}' /d 'Ramdisk options' | Out-Null
  & bcdedit /store $BCDPath /set    '{ramdiskoptions}' ramdisksdidevice boot | Out-Null
  & bcdedit /store $BCDPath /set    '{ramdiskoptions}' ramdisksdipath '\boot\boot.sdi' | Out-Null

  # OS loader - path differs by boot mode
  $createOutput = & bcdedit /store $BCDPath /create /d 'WinPE' /application osloader
  $loaderGuid = ($createOutput | Select-String '\{[0-9a-f\-]+\}').Matches[0].Value
  if (-not $loaderGuid) {
    throw "Could not parse loader GUID from bcdedit output: $createOutput"
  }
  Write-Info "  OS loader GUID : $loaderGuid"

  $winloadPath = if ($BootMode -eq 'BIOS') {
    '\windows\system32\winload.exe'
  } else {
    '\windows\system32\winload.efi'
  }

  & bcdedit /store $BCDPath /set $loaderGuid device    "ramdisk=[boot]\sources\boot.wim,{ramdiskoptions}" | Out-Null
  & bcdedit /store $BCDPath /set $loaderGuid osdevice  "ramdisk=[boot]\sources\boot.wim,{ramdiskoptions}" | Out-Null
  & bcdedit /store $BCDPath /set $loaderGuid path      $winloadPath | Out-Null
  & bcdedit /store $BCDPath /set $loaderGuid systemroot '\windows' | Out-Null
  & bcdedit /store $BCDPath /set $loaderGuid detecthal yes | Out-Null
  & bcdedit /store $BCDPath /set $loaderGuid winpe     yes | Out-Null
  & bcdedit /store $BCDPath /set $loaderGuid description 'WinPE' | Out-Null

  # Boot manager - path differs by boot mode
  $bootmgrPath = if ($BootMode -eq 'BIOS') {
    '\windows\system32\bootmgr'
  } else {
    '\EFI\Microsoft\Boot\bootmgfw.efi'
  }

  & bcdedit /store $BCDPath /create '{bootmgr}' /d 'Windows Boot Manager' | Out-Null
  & bcdedit /store $BCDPath /set    '{bootmgr}' device boot | Out-Null
  & bcdedit /store $BCDPath /set    '{bootmgr}' path $bootmgrPath | Out-Null
  & bcdedit /store $BCDPath /set    '{bootmgr}' displayorder $loaderGuid | Out-Null
  & bcdedit /store $BCDPath /set    '{bootmgr}' default $loaderGuid | Out-Null
  & bcdedit /store $BCDPath /set    '{bootmgr}' timeout 30 | Out-Null

  Write-OK "$BootMode BCD built: $BCDPath"
}

# -----------------------------------------------------------------------------
# FUNCTIONS -- ISO construction
# -----------------------------------------------------------------------------

function New-WinPEISO {
  param(
    [string]$OscdimgPath,
    [string]$MediaRoot,   # folder with the full media tree (bootmgr, boot\, sources\)
    [string]$ISOPath,
    [string]$BuildArch
  )

  # etfsboot.com is the El Torito boot sector for BIOS boot - from ADK
  # efisys.bin is the EFI system partition image - from ADK
  # Both live alongside oscdimg in the Deployment Tools
  $oscdimgDir = Split-Path $OscdimgPath -Parent
  $etfsboot   = Join-Path $oscdimgDir 'etfsboot.com'
  $efisys     = Join-Path $oscdimgDir 'efisys.bin'

  if (-not (Test-Path $etfsboot)) {
    Write-Warn "etfsboot.com not found alongside oscdimg - ISO will be EFI-only"
    $bootArgs = "-b`"$efisys`" -e"
  } else {
    # Dual boot: BIOS El Torito + UEFI
    $bootArgs = "-b`"$etfsboot`" -pEF -u2 -udfver102 -bootdata:2#p0,e,b`"$etfsboot`"#pEF,e,b`"$efisys`""
  }

  Write-Info "Running oscdimg to build ISO"
  $proc = Start-Process -FilePath $OscdimgPath `
    -ArgumentList "$bootArgs -o -m -u2 `"$MediaRoot`" `"$ISOPath`"" `
    -Wait -PassThru -NoNewWindow
  if ($proc.ExitCode -ne 0) {
    throw "oscdimg failed (exit code $($proc.ExitCode))"
  }
  Write-OK "ISO built: $ISOPath"
}

# -----------------------------------------------------------------------------
# FUNCTIONS -- output assembly
# -----------------------------------------------------------------------------

function Build-iPXEFolder {
  # Assembles the complete folder structure ready to copy to the jukebox.
  # Produces both BIOS and UEFI wimboot binaries and both BCDs so the same
  # folder works regardless of which firmware the target VM is using.
  param(
    [string]$OutputDir,
    [string]$iPXEArch,         # x86_64 or arm64
    [string]$WIMSource,        # finished WIM file
    [string]$BCDBIOSSource,    # BIOS BCD (winload.exe)
    [string]$BCDEFISource,     # UEFI BCD (winload.efi)
    [string]$BootSDISource,    # boot.sdi from ADK
    [string]$BootmgrSource,    # BIOS bootmgr from ADK WinPE media
    [string]$ScratchDir        # where wimboot binaries will be cached
  )

  $root = Join-Path $OutputDir "winpe\$iPXEArch"
  $bootDir    = Join-Path $root 'boot'
  $sourcesDir = Join-Path $root 'sources'

  foreach ($d in @($root, $bootDir, $sourcesDir)) {
    $null = New-Item -ItemType Directory -Path $d -Force
  }

  # WIM
  Copy-Item $WIMSource     (Join-Path $sourcesDir 'boot.wim') -Force
  Write-OK "Copied boot.wim     -> winpe\$iPXEArch\sources\"

  # BCDs - ARM64 has UEFI only; x64 gets both
  if ($BCDBIOSSource) {
    Copy-Item $BCDBIOSSource (Join-Path $bootDir 'BCD') -Force
    Write-OK "Copied BCD (BIOS)   -> winpe\$iPXEArch\boot\BCD"
  }
  Copy-Item $BCDEFISource (Join-Path $bootDir 'BCD.efi') -Force
  Write-OK "Copied BCD (UEFI)   -> winpe\$iPXEArch\boot\BCD.efi"

  # boot.sdi
  Copy-Item $BootSDISource (Join-Path $bootDir 'boot.sdi') -Force
  Write-OK "Copied boot.sdi     -> winpe\$iPXEArch\boot\"

  # BIOS bootmgr
  if ($BootmgrSource -and (Test-Path $BootmgrSource)) {
    Copy-Item $BootmgrSource (Join-Path $root 'bootmgr') -Force
    Write-OK "Copied bootmgr      -> winpe\$iPXEArch\"
  }

  # wimboot - x64 only. ARM64 boots via UEFI HTTP Boot directly from the
  # BCD + boot.wim; it does not use wimboot at all.
  if ($iPXEArch -eq 'x86_64') {
    $wimbootEFIDest  = Join-Path $root 'wimboot'
    $wimbootBIOSDest = Join-Path $root 'wimboot.i386'
    $wimbootEFICache  = Join-Path $ScratchDir 'wimboot'
    $wimbootBIOSCache = Join-Path $ScratchDir 'wimboot.i386'

    Get-Wimboot -DestPath $wimbootEFICache  -Url $WimbootUrlEFI
    Get-Wimboot -DestPath $wimbootBIOSCache -Url $WimbootUrlBIOS
    Copy-Item $wimbootEFICache  $wimbootEFIDest  -Force
    Copy-Item $wimbootBIOSCache $wimbootBIOSDest -Force
    Write-OK "wimboot (EFI)       -> winpe\$iPXEArch\wimboot"
    Write-OK "wimboot (BIOS)      -> winpe\$iPXEArch\wimboot.i386"
  } else {
    Write-Info 'ARM64: skipping wimboot - UEFI HTTP Boot uses BCD + boot.wim directly'
  }
}

function Remove-ScratchDirs {
  param([string]$ScratchDir, [string]$BuildArch)
  # Clean the arch-namespaced subdirectory - leaves other arch's scratch intact
  $archScratch = Join-Path $ScratchDir $BuildArch
  if (Test-Path $archScratch) {
    Remove-Item -Path $archScratch -Recurse -Force
    Write-OK "Removed scratch dir: $archScratch"
  }
  # Remove portable 7za.exe if we downloaded it (save re-downloading next run
  # by NOT removing it - comment this out to keep it)
  # Remove-Item $SevenZipPortablePath -Force -ErrorAction SilentlyContinue
}

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

$BuildArch     = Get-BuildArch -Override $Arch
$WimArch       = Get-WimArch   -BuildArch $BuildArch
$ToolsArch     = Get-ToolsArch -BuildArch $BuildArch
$iPXEArch      = Get-iPXEArch  -BuildArch $BuildArch
$ADKRoot       = Get-ADKRoot
$OscdimgPath   = Get-OscdimgPath -ADKRoot $ADKRoot
$SevenZip      = Get-SevenZipPath -ScratchDir $ScratchDir

$WinPEOCRoot   = Join-Path $ADKRoot "Windows Preinstallation Environment\$BuildArch\WinPE_OCs"
$SourceWIM     = Join-Path $ADKRoot "Windows Preinstallation Environment\$BuildArch\en-us\winpe.wim"

# boot.sdi lives in the ADK WinPE media builder output area
# It is also present in the WinPE add-on under \amd64\Media\boot\
$BootSDI       = Join-Path $ADKRoot "Windows Preinstallation Environment\$BuildArch\Media\boot\boot.sdi"
# bootmgr for x86_64 wimboot boot
$Bootmgr       = Join-Path $ADKRoot "Windows Preinstallation Environment\$BuildArch\Media\bootmgr"

# All scratch subdirectories are namespaced by architecture so two build
# instances (one amd64, one arm64) can run simultaneously without collision.
$MountPath     = Join-Path $ScratchDir "$BuildArch\mount"
$VMwareEXEDir  = Join-Path $ScratchDir "$BuildArch\vmware_exe"
$VMwareMSIDir  = Join-Path $ScratchDir "$BuildArch\vmware_msi"
$ISOMediaDir   = Join-Path $ScratchDir "$BuildArch\iso_media"
$WorkWIM       = Join-Path $ScratchDir "$BuildArch\boot_$WimArch.wim"
$OutputWIM     = Join-Path $OutputDir  "boot_$WimArch.wim"
$OutputISO     = Join-Path $OutputDir  "boot_$WimArch.iso"
$OutputBCDBIOS = Join-Path $OutputDir  "BCD_${WimArch}_bios"
$OutputBCDEFI  = Join-Path $OutputDir  "BCD_${WimArch}_efi"

Write-Step 'Build-WinPE starting'
Write-Info "Architecture  : $BuildArch ($WimArch / iPXE: $iPXEArch)"
Write-Info "ADK root      : $ADKRoot"
Write-Info "Source WIM    : $SourceWIM"
Write-Info "Output WIM    : $OutputWIM"
Write-Info "Output ISO    : $OutputISO"
Write-Info "iPXE folder   : $(Join-Path $OutputDir "winpe\$iPXEArch")"
Write-Info "Tools arch    : tools\$ToolsArch\"
Write-Info "7-Zip         : $SevenZip"
Write-Info "oscdimg       : $OscdimgPath"

Assert-Path $SourceWIM   'WinPE base WIM - is the WinPE Add-on installed?'
Assert-Path $WinPEOCRoot 'WinPE optional components directory'

# ── Pre-flight checks ──────────────────────────────────────────────────────
# Warn and pause for any missing components so the user can fix them
# before the build starts and fails partway through.
Write-Step 'Pre-flight checks'
$preflightOK = $true

# cecho.exe - required for coloured output in startnet.cmd
# Pre-flight uses the overlay path - cecho must be in Windows\System32\ subfolder
  $cechoCheck = Join-Path $ToolsRoot "$ToolsArch\Windows\System32\cecho.exe"
if (-not (Test-Path $cechoCheck)) {
  Write-Warn "cecho.exe not found at: $cechoCheck"
  Write-Warn 'Place cecho.exe in tools\<arch>\Windows\System32\ (must be on WinPE PATH)'
  Write-Warn 'Download from: https://github.com/jscheuch/cecho/releases'
  $preflightOK = $false
} else {
  Write-OK "cecho.exe found"
}

# Microsoft.Dart module - needed for correct DartConfig.dat generation
$dartModuleOK = $false
try {
  Import-Module 'Microsoft.Dart' -ErrorAction Stop
  Remove-Module 'Microsoft.Dart' -ErrorAction SilentlyContinue
  $dartModuleOK = $true
  Write-OK 'Microsoft.Dart module available (installed)'
} catch {
  if ($DaRTModulePath -and (Test-Path $DaRTModulePath)) {
    $dartModuleOK = $true
    Write-OK "Microsoft.Dart module available (extracted at: $DaRTModulePath)"
  } else {
    Write-Warn 'Microsoft.Dart module not found - DaRT will use .tpk or manual fallback'
    Write-Warn 'For best results: install DaRT 10 (MSDaRT100.msi) then re-run'
    Write-Warn 'Run Fix-MDTforADK24H2.ps1 first to create required x86 WinPE folders'
    Write-Warn '(x86\Media, x86\WinPE_OCs, x86\en-us) then install MSDaRT100.msi'
  }
}

# x86 WinPE folders - required by DaRT installer on amd64 builds
# ADK does not ship x86 WinPE at all; these are stub folders created by Fix-MDTforADK24H2.ps1
if ($BuildArch -eq 'amd64') {
  $x86PE = Join-Path $ADKRoot 'Windows Preinstallation Environment\x86'
  $x86Dirs = @('Media', 'WinPE_OCs', 'en-us')
  foreach ($d in $x86Dirs) {
    $p = Join-Path $x86PE $d
    if (-not (Test-Path $p)) {
      Write-Warn "Missing x86 WinPE folder (needed by DaRT): $p"
      Write-Warn 'Run Fix-MDTforADK24H2.ps1 to create these folders'
      $preflightOK = $false
    }
  }
} else {
  Write-Info 'ARM64 build: skipping x86 WinPE folder check (not required)'
}

if (-not $preflightOK) {
  Write-Host ''
  Write-Host 'Pre-flight checks found issues. Press ENTER to continue anyway, or Ctrl+C to abort.' -ForegroundColor Yellow
  $null = Read-Host
} else {
  Write-OK 'All pre-flight checks passed'
}

if (-not (Test-Path $BootSDI)) {
  Write-Warn "boot.sdi not found at expected ADK path: $BootSDI"
  Write-Warn "Searching ADK tree for boot.sdi..."
  $sdiHit = Get-ChildItem -Path $ADKRoot -Filter 'boot.sdi' -Recurse -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if ($sdiHit) {
    $BootSDI = $sdiHit.FullName
    Write-OK "Found boot.sdi at: $BootSDI"
  } else {
    throw "boot.sdi not found anywhere under ADK root. Reinstall the WinPE Add-on."
  }
}

if ($BuildArch -eq 'arm64') {
  # ARM64 uses UEFI HTTP Boot only - no bootmgr required
  Write-Info 'ARM64 build: bootmgr not required (UEFI HTTP Boot only)'
  $Bootmgr = $null
} elseif (-not (Test-Path $Bootmgr)) {
  Write-Warn "bootmgr not found at expected ADK path: $Bootmgr"
  # Scope search to the correct arch Media folder only - not the whole ADK
  $archMediaPath = Join-Path $ADKRoot "Windows Preinstallation Environment\$BuildArch"
  $bmHit = Get-ChildItem -Path $archMediaPath -Filter 'bootmgr' `
    -Recurse -ErrorAction SilentlyContinue | `
    Where-Object { $_.Length -gt 100KB } | Select-Object -First 1
  if ($bmHit) {
    $Bootmgr = $bmHit.FullName
    Write-OK "Found bootmgr at: $Bootmgr"
  } else {
    Write-Warn 'bootmgr not found - iPXE output folder will not include it'
    $Bootmgr = $null
  }
}

# Create working directories
Write-Step 'Preparing directories'
foreach ($d in @($ScratchDir, $MountPath, $OutputDir)) {
  $null = New-Item -ItemType Directory -Path $d -Force
}
Write-OK 'Directories ready'

# Copy base WIM into scratch - never modify the ADK original
Write-Step 'Copying base WIM into scratch'
Copy-Item -Path $SourceWIM -Destination $WorkWIM -Force
Set-ItemProperty -Path $WorkWIM -Name IsReadOnly -Value $false
Write-OK "Working WIM: $WorkWIM"

# Mount
Write-Step 'Mounting WIM'
Mount-WindowsImage -ImagePath $WorkWIM -Index 1 -Path $MountPath | Out-Null
Write-OK "Mounted at $MountPath"

try {
  # Optional components
  Write-Step 'Adding WinPE optional components'
  foreach ($pkg in $WinPEPackages) {
    $pkgPath = Join-Path $WinPEOCRoot "$pkg.cab"
    if (Test-Path $pkgPath) {
      Add-WinPEPackage -MountPath $MountPath -PackagePath $pkgPath
    } else {
      Write-Warn "Package not found, skipping: $pkgPath"
    }
    $lp = Join-Path $WinPEOCRoot "en-us\${pkg}_en-us.cab"
    if (Test-Path $lp) {
      Add-WinPEPackage -MountPath $MountPath -PackagePath $lp
    }
  }
  Write-OK 'Optional components added'

  # Install language packs for all supported locales.
  # lp.cab is the base language pack; the per-component cabs localise each OC.
  # Install lp.cab first, then the per-OC cabs that match installed components.
  # All three locales are staged so the runtime keyboard picker works correctly.
  # en-gb is set as the default UI/input locale via DISM after cab install.
  #
  # Folder names in WinPE_OCs are lowercase (en-gb, da-dk, de-de).
  Write-Step 'Installing language packs (en-gb, da-dk, de-de)'

  # OCs we installed - only install language cabs for these (skip others)
  $installedOCs = $WinPEPackages

  $localeFolders = @('en-gb', 'da-dk', 'de-de')
  foreach ($locale in $localeFolders) {
    $localeDir = Join-Path $WinPEOCRoot $locale
    if (-not (Test-Path $localeDir)) {
      Write-Warn "Locale folder not found: $localeDir - skipping"
      continue
    }
    Write-Info "Installing language pack: $locale"

    # lp.cab first - base language pack
    $lpCab = Join-Path $localeDir 'lp.cab'
    if (Test-Path $lpCab) {
      Add-WindowsPackage -Path $MountPath -PackagePath $lpCab `
        -IgnoreCheck | Out-Null
      Write-OK "$locale lp.cab installed"
    }

    # Per-OC language cabs - only for OCs we actually installed
    foreach ($oc in $installedOCs) {
      $ocLangCab = Join-Path $localeDir "${oc}_${locale}.cab"
      if (Test-Path $ocLangCab) {
        Add-WindowsPackage -Path $MountPath -PackagePath $ocLangCab `
          -IgnoreCheck | Out-Null
        Write-Info "  $oc language cab installed ($locale)"
      }
    }
  }
  Write-OK 'Language packs installed'

  # Set en-GB as the default locale in the WIM via DISM offline commands.
  # /Set-InputLocale bakes the keyboard layout so Shift+2 gives " not @.
  # /Set-UILanguage sets the default UI strings to en-GB.
  # /Set-UserLocale sets date/time/number format to en-GB.
  # The ADK dism.exe is preferred over the inbox version for compatibility.
  Write-Step 'Setting WIM default locale to en-GB'
  # When cross-building ARM64 on an amd64 host, the arm64\DISM\dism.exe
  # is an ARM64 binary and cannot run. Always prefer amd64 DISM - it can
  # service any WIM architecture. Fall back to inbox dism.exe last.
  $dismExe = Join-Path $ADKRoot 'Deployment Tools\amd64\DISM\dism.exe'
  if (-not (Test-Path $dismExe)) {
    $dismExe = Join-Path $ADKRoot "Deployment Tools\$BuildArch\DISM\dism.exe"
  }
  if (-not (Test-Path $dismExe)) { $dismExe = 'dism.exe' }
  Write-Info "Using DISM: $dismExe"

  # /Set-UILanguage is only valid for full Windows images, not WinPE.
  # WinPE locale is controlled by InputLocale and UserLocale only.
  $localeArgs = @(
    @('/Set-InputLocale:0809:00000809', 'Input locale (keyboard - en-GB)'),
    @('/Set-UserLocale:en-GB',          'User locale (date/number format)')
  )
  foreach ($arg in $localeArgs) {
    $proc = Start-Process -FilePath $dismExe `
      -ArgumentList "/Image:`"$MountPath`" $($arg[0])" `
      -Wait -PassThru -NoNewWindow
    if ($proc.ExitCode -eq 0) {
      Write-OK $arg[1]
    } else {
      Write-Warn "DISM $($arg[0]) failed (exit $($proc.ExitCode))"
    }
  }

  # DaRT OC cab - search WinPE_OCs folder for a DaRT cab and install if found.
  # The cab must be a proper DISM package (not just a flat file archive).
  # toolsX64.cab from MDOP is a flat cab - it will be rejected by DISM.
  # Only cabs with valid package identity (e.g. from ADK DaRT add-on) install here.
  Write-Step 'Searching for DaRT optional component cab'
  $dartCabCandidates = Get-ChildItem -Path $WinPEOCRoot `
    -Include '*dart*','*DaRT*','toolsX64.cab','toolsX86.cab' `
    -Recurse -ErrorAction SilentlyContinue
  if ($dartCabCandidates) {
    foreach ($dartCab in $dartCabCandidates) {
      Write-Info "Trying DaRT cab as DISM package: $($dartCab.Name)"
      try {
        Add-WindowsPackage -Path $MountPath `
          -PackagePath $dartCab.FullName -IgnoreCheck | Out-Null
        Write-OK "DaRT OC installed from: $($dartCab.Name)"
        # If DISM accepted it, the files are already in the WIM
        # Set-WinPERDP will still run but will find files already staged
      } catch {
        Write-Warn "DISM rejected $($dartCab.Name) as a package (likely flat cab - OK)"
        Write-Info 'Set-WinPERDP will handle file extraction and staging instead'
      }
    }
  } else {
    Write-Info 'No DaRT cab found in WinPE_OCs - will use sources\WinPERDP\ or toolsX64.cab'
  }

  # VMware drivers - download EXE if not already present
  Get-VMwareToolsEXE -DestPath $VMwareToolsEXE -BuildArch $BuildArch -BaseUrl $VMwareToolsBaseUrl

  Write-Step 'Locating VMware drivers'
  $vmwarePaths = Get-VMwareDriverPaths `
    -SevenZip     $SevenZip `
    -EXEPath      $VMwareToolsEXE `
    -MSIPath      $VMwareToolsMSI `
    -LoosePath    $VMwareLooseDrivers `
    -ExtractEXETo $VMwareEXEDir `
    -ExtractMSITo $VMwareMSIDir
  if ($vmwarePaths.Count -gt 0) {
    Write-Step 'Injecting VMware drivers'
    foreach ($dp in $vmwarePaths) {
      Write-Info "Injecting: $dp"
      Add-WindowsDriver -Path $MountPath -Driver $dp -Recurse -ForceUnsigned | Out-Null
    }
    Write-OK 'VMware drivers injected'
  }

  # VirtIO drivers
  Write-Step 'Locating VirtIO drivers'
  $virtioPaths = Get-VirtIODriverPaths -VirtIORoot $VirtIODriverRoot -Arch $BuildArch
  if ($virtioPaths.Count -gt 0) {
    Write-Step 'Injecting VirtIO drivers'
    foreach ($dp in $virtioPaths) {
      Write-Info "Injecting: $dp"
      Add-WindowsDriver -Path $MountPath -Driver $dp -Recurse -ForceUnsigned | Out-Null
    }
    Write-OK 'VirtIO drivers injected'
  }

  # Tools
  Write-Step 'Copying arch-specific tools'
  Copy-Tools -ToolsRoot $ToolsRoot -ToolsArch $ToolsArch -MountPath $MountPath

  # Windows Terminal portable
  if ($InstallWindowsTerminal) {
    Write-Step 'Installing Windows Terminal portable'
    Install-WinPEWindowsTerminal `
      -MountPath  $MountPath `
      -ScratchDir $ScratchDir `
      -BuildArch  $BuildArch `
      -ToolsRoot  $ToolsRoot `
      -ToolsArch  $ToolsArch
  }

  # PowerShell 7
  Write-Step 'Installing PowerShell 7'
  $ps7Zip = if ($BuildArch -eq 'arm64') { $PS7ZipARM64 } else { $PS7ZipX64 }
  Install-WinPEPS7 -MountPath $MountPath -PS7Zip $ps7Zip -BuildArch $BuildArch

  # PS Gallery modules (saves to both PS5.1 and PS7 paths)
  Write-Step 'Staging PowerShell Gallery modules'
  Install-WinPEPSGallery `
    -MountPath       $MountPath `
    -Modules         $PSGalleryModules `
    -ModulesPS7Only  $PSGalleryModulesPS7Only

  # Shell config and startup script
  Write-Step 'Configuring WinPE shell and startup'
  Set-WinPEShell    -MountPath $MountPath
  Set-WinPEDaRT `
    -MountPath      $MountPath `
    -BuildRoot      $BuildRoot `
    -ScratchDir     $ScratchDir `
    -ToolsRoot      $ToolsRoot `
    -ToolsArch      $ToolsArch `
    -DaRTModulePath $DaRTModulePath `
    -RDPSourceDir   $RDPSourceDir `
    -ToolsRDPDir    (Join-Path $ToolsRoot "$ToolsArch\WinPERDP") `
    -RDPSourceCab   $RDPSourceCab `
    -SevenZip       $SevenZip `
    -RemoteMessage  'Welcome to the WinPE Deployment Environment' `
    -RemotePort     3389
  Set-WinPEStartnet -MountPath $MountPath -ToolsRoot $ToolsRoot -ToolsArch $ToolsArch

  # Cleanup while mounted - DISM /Cleanup-Image requires a mounted image path.
  # Running it after dismount against the WIM file causes error 267.
  Write-Step 'Cleaning up mounted WIM (StartComponentCleanup)'
  $dismExeClean = Join-Path $ADKRoot 'Deployment Tools\amd64\DISM\dism.exe'
  if (-not (Test-Path $dismExeClean)) {
    $dismExeClean = Join-Path $ADKRoot "Deployment Tools\$BuildArch\DISM\dism.exe"
  }
  if (-not (Test-Path $dismExeClean)) { $dismExeClean = 'dism.exe' }
  $cleanProc = Start-Process -FilePath $dismExeClean `
    -ArgumentList "/Image:`"$MountPath`" /Cleanup-Image /StartComponentCleanup" `
    -Wait -PassThru -NoNewWindow
  if ($cleanProc.ExitCode -eq 0) {
    Write-OK 'Component cleanup complete'
  } else {
    Write-Warn "Component cleanup failed (exit $($cleanProc.ExitCode)) - continuing"
  }

  # Commit WIM
  Write-Step 'Unmounting and committing WIM'
  Dismount-WindowsImage -Path $MountPath -Save | Out-Null
  Write-OK 'WIM committed'

} catch {
  Write-Warn 'Error encountered - discarding mount cleanly'
  try {
    Dismount-WindowsImage -Path $MountPath -Discard | Out-Null
  } catch {
    Write-Warn "Mount discard failed - run manually:`n       dism /unmount-wim /mountdir:`"$MountPath`" /discard"
  }
  throw
}

# Move WIM to output
Write-Step 'Writing output WIM'
$null = New-Item -ItemType Directory -Path $OutputDir -Force
Move-Item -Path $WorkWIM -Destination $OutputWIM -Force
$sizeMB = [math]::Round((Get-Item $OutputWIM).Length / 1MB, 1)
Write-OK "Output WIM : $OutputWIM  ($sizeMB MB) - before cleanup"

# WIM export - compacts internal free space and recompresses.
# Cleanup was already done pre-dismount while the image was mounted.
Write-Step 'Compacting WIM via export'
$ExportWIM = Join-Path $OutputDir "boot_${WimArch}_export.wim"
Write-Info 'Exporting WIM to compact free space (this takes a moment)...'
Export-WindowsImage -SourceImagePath $OutputWIM -SourceIndex 1 `
  -DestinationImagePath $ExportWIM -CompressionType maximum | Out-Null
if (Test-Path $ExportWIM) {
  $exportMB = [math]::Round((Get-Item $ExportWIM).Length / 1MB, 1)
  $savedMB  = [math]::Round($sizeMB - $exportMB, 1)
  Remove-Item $OutputWIM -Force
  Rename-Item $ExportWIM $OutputWIM
  $sizeMB = $exportMB
  Write-OK "WIM compacted: $sizeMB MB (saved $savedMB MB)"
} else {
  Write-Warn 'WIM export failed - keeping original'
}

# BCDs - ARM64 is UEFI only (no legacy BIOS boot path)
if ($BuildArch -eq 'arm64') {
  Write-Step 'Building UEFI BCD (arm64 - UEFI only)'
  New-WinPEBCD -BCDPath $OutputBCDEFI -BootSDIPath $BootSDI -Arch $BuildArch -BootMode UEFI
  Write-Info 'ARM64: skipping BIOS BCD (not supported on ARM64)'
  $OutputBCDBIOS = $null
} else {
  Write-Step 'Building BIOS BCD (winload.exe - default)'
  New-WinPEBCD -BCDPath $OutputBCDBIOS -BootSDIPath $BootSDI -Arch $BuildArch -BootMode BIOS

  Write-Step 'Building UEFI BCD (winload.efi)'
  New-WinPEBCD -BCDPath $OutputBCDEFI -BootSDIPath $BootSDI -Arch $BuildArch -BootMode UEFI
}

# ISO - x64 only. ARM64 deploys via UEFI HTTP Boot - no ISO needed.
$isoMB = 0
if ($BuildArch -eq 'arm64') {
  Write-Info 'ARM64: skipping ISO build (UEFI HTTP Boot deployment only)'
  $OutputISO = $null
} else {
  Write-Step 'Building ISO media tree'
  $isoSourcesDir = Join-Path $ISOMediaDir 'sources'
  $isoBootDir    = Join-Path $ISOMediaDir 'boot'
  foreach ($d in @($ISOMediaDir, $isoSourcesDir, $isoBootDir)) {
    $null = New-Item -ItemType Directory -Path $d -Force
  }
  Copy-Item $OutputWIM     (Join-Path $isoSourcesDir 'boot.wim') -Force
  Copy-Item $OutputBCDBIOS (Join-Path $isoBootDir    'BCD')      -Force
  Copy-Item $BootSDI       (Join-Path $isoBootDir    'boot.sdi') -Force
  if ($Bootmgr) { Copy-Item $Bootmgr (Join-Path $ISOMediaDir 'bootmgr') -Force }

  Write-Step 'Building bootable ISO'
  New-WinPEISO -OscdimgPath $OscdimgPath -MediaRoot $ISOMediaDir -ISOPath $OutputISO -BuildArch $BuildArch
  $isoMB = [math]::Round((Get-Item $OutputISO).Length / 1MB, 1)
  Write-OK "ISO : $OutputISO  ($isoMB MB)"
}

# Bake BCD + boot.sdi into the WIM so PXE only needs wimboot + boot.wim.
# With a self-contained WIM the iPXE entry is simply:
#   kernel http://server/winpe/x86_64/wimboot
#   initrd http://server/winpe/x86_64/boot.wim
#   boot
# Wimboot reads the BCD from \boot\BCD inside the WIM, loads winload.exe,
# and winload finds boot.sdi at \boot\boot.sdi - all from within the WIM.
Write-Step 'Baking BCD and boot.sdi into WIM (self-contained PXE)'
$wimBootDir = Join-Path $ScratchDir "$BuildArch\wim_inject"
$null = New-Item -ItemType Directory -Path $wimBootDir -Force

# Mount the finished WIM to inject boot files
$injectMount = Join-Path $ScratchDir "$BuildArch\inject_mount"
$null = New-Item -ItemType Directory -Path $injectMount -Force
Mount-WindowsImage -ImagePath $OutputWIM -Index 1 -Path $injectMount | Out-Null
try {
  $wimBootSubDir = Join-Path $injectMount 'boot'
  $null = New-Item -ItemType Directory -Path $wimBootSubDir -Force

  # Build a dedicated embedded BCD for wimboot PXE.
  # - Uses winload.exe (not .efi) because wimboot is a BIOS-mode chainloader
  #   even on UEFI firmware; winload.exe is what WinPE expects from wimboot.
  # - ramdisksdipath points to \boot\boot.sdi which is where we place it
  #   inside the WIM - wimboot serves it from the in-memory WIM filesystem.
  # - ramdisksdidevice stays as 'boot' - wimboot intercepts this correctly.
  $embeddedBCDPath = Join-Path $wimBootSubDir 'BCD'
  & bcdedit /createstore $embeddedBCDPath | Out-Null
  & bcdedit /store $embeddedBCDPath /create '{ramdiskoptions}' /d 'Ramdisk options' | Out-Null
  & bcdedit /store $embeddedBCDPath /set '{ramdiskoptions}' ramdisksdidevice boot | Out-Null
  & bcdedit /store $embeddedBCDPath /set '{ramdiskoptions}' ramdisksdipath '\boot\boot.sdi' | Out-Null
  $co = & bcdedit /store $embeddedBCDPath /create /d 'WinPE' /application osloader
  $lg = ($co | Select-String '\{[0-9a-f\-]+\}').Matches[0].Value
  & bcdedit /store $embeddedBCDPath /set $lg device   'ramdisk=[boot]\sources\boot.wim,{ramdiskoptions}' | Out-Null
  & bcdedit /store $embeddedBCDPath /set $lg osdevice 'ramdisk=[boot]\sources\boot.wim,{ramdiskoptions}' | Out-Null
  & bcdedit /store $embeddedBCDPath /set $lg path     '\windows\system32\winload.exe' | Out-Null
  & bcdedit /store $embeddedBCDPath /set $lg systemroot '\windows' | Out-Null
  & bcdedit /store $embeddedBCDPath /set $lg detecthal yes | Out-Null
  & bcdedit /store $embeddedBCDPath /set $lg winpe     yes | Out-Null
  & bcdedit /store $embeddedBCDPath /set $lg description 'WinPE' | Out-Null
  & bcdedit /store $embeddedBCDPath /create '{bootmgr}' /d 'Windows Boot Manager' | Out-Null
  & bcdedit /store $embeddedBCDPath /set '{bootmgr}' device boot | Out-Null
  & bcdedit /store $embeddedBCDPath /set '{bootmgr}' path '\windows\system32\bootmgr' | Out-Null
  & bcdedit /store $embeddedBCDPath /set '{bootmgr}' displayorder $lg | Out-Null
  & bcdedit /store $embeddedBCDPath /set '{bootmgr}' default $lg | Out-Null
  & bcdedit /store $embeddedBCDPath /set '{bootmgr}' timeout 30 | Out-Null
  Write-OK 'Embedded BCD built (winload.exe, \boot\boot.sdi) at \boot\BCD'

  Copy-Item $BootSDI (Join-Path $wimBootSubDir 'boot.sdi') -Force
  Write-OK 'boot.sdi baked into WIM at \boot\boot.sdi'

  Dismount-WindowsImage -Path $injectMount -Save | Out-Null
  Write-OK 'WIM dismounted after boot file injection'
} catch {
  Dismount-WindowsImage -Path $injectMount -Discard -ErrorAction SilentlyContinue | Out-Null
  Write-Warn "Boot file injection failed: $($_.Exception.Message)"
  Write-Warn 'WIM is still usable but PXE will need BCD served separately'
}
Remove-Item $injectMount -Recurse -Force -ErrorAction SilentlyContinue

# Re-export WIM after injection to compact the added files
$postInjectExport = Join-Path $OutputDir "boot_${WimArch}_final.wim"
Export-WindowsImage -SourceImagePath $OutputWIM -SourceIndex 1 `
  -DestinationImagePath $postInjectExport -CompressionType maximum | Out-Null
if (Test-Path $postInjectExport) {
  Remove-Item $OutputWIM -Force
  Rename-Item $postInjectExport $OutputWIM
  $sizeMB = [math]::Round((Get-Item $OutputWIM).Length / 1MB, 1)
  Write-OK "Final WIM (self-contained): $sizeMB MB"
}

# Assemble iPXE deployment folder
Write-Step 'Assembling iPXE deployment folder'
Build-iPXEFolder `
  -OutputDir      $OutputDir `
  -iPXEArch       $iPXEArch `
  -WIMSource      $OutputWIM `
  -BCDBIOSSource  $OutputBCDBIOS `
  -BCDEFISource   $OutputBCDEFI `
  -BootSDISource  $BootSDI `
  -BootmgrSource  $Bootmgr `
  -ScratchDir     $ScratchDir
Write-OK "iPXE folder ready: $(Join-Path $OutputDir "winpe\$iPXEArch")"

# Cleanup scratch
Write-Step 'Cleaning up scratch directories'
Remove-ScratchDirs -ScratchDir $ScratchDir -BuildArch $BuildArch
Write-OK 'Scratch dirs removed'

# Summary
$iPXEFolder = Join-Path $OutputDir "winpe\$iPXEArch"
Write-Host "`nBuild complete.`n" -ForegroundColor Green
Write-Host "  Architecture : $BuildArch" -ForegroundColor Gray
Write-Host "  WIM          : $OutputWIM  ($sizeMB MB)" -ForegroundColor Gray
if ($OutputISO) {
  Write-Host "  ISO          : $OutputISO  ($isoMB MB)" -ForegroundColor Gray
} else {
  Write-Host "  ISO          : (skipped - ARM64 uses UEFI HTTP Boot)" -ForegroundColor Gray
}
if ($OutputBCDBIOS) {
  Write-Host "  BCD (BIOS)   : $OutputBCDBIOS" -ForegroundColor Gray
}
Write-Host "  BCD (UEFI)   : $OutputBCDEFI" -ForegroundColor Gray
Write-Host "  iPXE folder  : $iPXEFolder" -ForegroundColor Gray
$jukePath = Join-Path $OutputDir 'winpe'
Write-Host "`n  Copy contents of $jukePath to jukebox HTTP root under winpe/" -ForegroundColor Gray
if ($BuildArch -eq 'arm64') {
  Write-Host "  arm64 : UEFI HTTP Boot - BCD.efi + boot.wim (no wimboot)" -ForegroundColor Gray
} else {
  Write-Host "  BIOS VMs : wimboot.i386, BCD = boot\BCD" -ForegroundColor Gray
  Write-Host "  UEFI VMs : wimboot, BCD = boot\BCD.efi" -ForegroundColor Gray
  Write-Host "  arm64    : boot.wim only (UEFI HTTP Boot - no wimboot needed)" -ForegroundColor Gray
}
Write-Host '' -ForegroundColor Gray
