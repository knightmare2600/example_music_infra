# =============================================================================
# Fix-MDTforADK24H2.ps1
# Applies workarounds to make MDT 8456 work with Windows ADK 24H2 (Build 26100).
# Run once after installing both MDT and the ADK, from an elevated PS session.
#
# Fixes applied:
#   1. Creates empty x86\WinPE_OCs folder - MDT crashes without it even though
#      x86 WinPE was removed from ADK in Windows 11 22H2.
#   2. Edits DeploymentTools.xml to add %RealPlatform% to imgmgr.exe path -
#      fixes catalog generation failure with architecture-specific WSIM.
#
# Source: https://www.deploymentresearch.com/
#   windows-11-deployment-using-mdt-8456-with-windows-adk-24h2-build-26100/
# Credit: Johan Arwidmark (fix 1), L. Ozon (fix 2)
#
# Version history:
#   1.0.0  2025-04-01  Initial release
# =============================================================================

#Requires -RunAsAdministrator

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step { param([string]$m) Write-Host "`n==> $m" -ForegroundColor Cyan }
function Write-OK   { param([string]$m) Write-Host "    [OK] $m" -ForegroundColor Green }
function Write-Warn { param([string]$m) Write-Host "    [WARN] $m" -ForegroundColor Yellow }
function Write-Info { param([string]$m) Write-Host "    $m" -ForegroundColor Gray }

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------

$ADKRoot = 'C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit'
$MDTRoot = 'C:\Program Files\Microsoft Deployment Toolkit'

$ADKAltRoot = 'C:\Program Files\Windows Kits\10\Assessment and Deployment Kit'
if (-not (Test-Path $ADKRoot) -and (Test-Path $ADKAltRoot)) {
  $ADKRoot = $ADKAltRoot
}

if (-not (Test-Path $ADKRoot)) {
  throw "Windows ADK not found. Install ADK 24H2 before running this script."
}
if (-not (Test-Path $MDTRoot)) {
  throw "MDT not found at $MDTRoot. Install MDT 8456 before running this script."
}

Write-Step 'Fix-MDTforADK24H2 starting'
Write-Info "ADK root : $ADKRoot"
Write-Info "MDT root : $MDTRoot"

# -----------------------------------------------------------------------------
# Fix 1 - Create empty x86\WinPE_OCs folder
# MDT checks for this folder on startup and throws DirectoryNotFoundException
# if it is absent. The folder can be empty - MDT only checks existence.
# -----------------------------------------------------------------------------

Write-Step 'Fix 1: Creating empty x86\WinPE_OCs folder'

$x86PE = Join-Path $ADKRoot 'Windows Preinstallation Environment\x86'

# Three folders are required - WinPE_OCs for MDT, Media and en-us for DaRT
foreach ($sub in @('WinPE_OCs', 'Media', 'en-us')) {
  $p = Join-Path $x86PE $sub
  if (Test-Path $p) {
    Write-OK "Already exists: $p"
  } else {
    $null = New-Item -ItemType Directory -Path $p -Force
    Write-OK "Created: $p"
  }
}

# -----------------------------------------------------------------------------
# Fix 2 - Edit DeploymentTools.xml to add %RealPlatform% to imgmgr.exe path
# ADK 24H2 is the first version to ship architecture-specific WSIM binaries.
# MDT's DeploymentTools.xml hardcodes the path without the platform subfolder,
# causing catalog generation to fail with a FileNotFoundException.
# The fix adds %RealPlatform% so MDT finds the correct architecture's imgmgr.exe.
# -----------------------------------------------------------------------------

Write-Step 'Fix 2: Patching DeploymentTools.xml for architecture-specific WSIM'

$deployToolsXml = Join-Path $MDTRoot 'Bin\DeploymentTools.xml'

if (-not (Test-Path $deployToolsXml)) {
  Write-Warn "DeploymentTools.xml not found at: $deployToolsXml"
  Write-Warn "Skipping Fix 2 - verify MDT installation path"
} else {
  # Back up the file before editing
  $backup = $deployToolsXml + '.bak'
  if (-not (Test-Path $backup)) {
    Copy-Item $deployToolsXml $backup -Force
    Write-OK "Backup created: $backup"
  } else {
    Write-Info "Backup already exists: $backup"
  }

  $xml = Get-Content $deployToolsXml -Raw

  # The line to find (may vary slightly between MDT versions):
  # <tool name="imgmgr.exe">%ADKPath%\Deployment Tools\WSIM</tool>
  # Target replacement:
  # <tool name="imgmgr.exe">%ADKPath%\Deployment Tools\WSIM\%RealPlatform%</tool>
  $oldLine = '<tool name="imgmgr.exe">%ADKPath%\Deployment Tools\WSIM</tool>'
  $newLine = '<tool name="imgmgr.exe">%ADKPath%\Deployment Tools\WSIM\%RealPlatform%</tool>'

  if ($xml -like "*$newLine*") {
    Write-OK 'DeploymentTools.xml already patched - skipping'
  } elseif ($xml -like "*$oldLine*") {
    $xml = $xml.Replace($oldLine, $newLine)
    Set-Content -Path $deployToolsXml -Value $xml -Encoding UTF8 -NoNewline
    Write-OK 'DeploymentTools.xml patched - imgmgr.exe now uses %RealPlatform%'
  } else {
    Write-Warn 'Expected imgmgr.exe line not found in DeploymentTools.xml'
    Write-Warn 'This MDT version may already be patched or use a different format'
    Write-Warn "Check manually: $deployToolsXml"
    Write-Warn "Look for: imgmgr.exe"
    Write-Warn "Add \\%RealPlatform% to the end of its path value"
  }
}

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

Write-Host "`nMDT / ADK 24H2 hotfixes applied.`n" -ForegroundColor Green
Write-Host "  Fix 1 (x86 WinPE folders) : WinPE_OCs, Media, en-us created" -ForegroundColor Gray
Write-Host "                             : prevents MDT console crash and enables DaRT installer" -ForegroundColor Gray
Write-Host "  Fix 2 (imgmgr.exe platform): fixes catalog generation failure" -ForegroundColor Gray
Write-Host "`n  NOTE: Johan Arwidmark recommends ADK 22H2 (build 22621) for production" -ForegroundColor Yellow
Write-Host "  ADK 24H2 has known PowerShell and servicing bugs with MDT 8456.`n" -ForegroundColor Yellow
