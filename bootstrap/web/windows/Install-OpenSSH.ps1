# ==============================================================================
# Example Music Limited
#
# Install-OpenSSH.ps1
#
# Version History
# ---------------
# 1.0.0   2026-06-28   Initial release
#
# Purpose
# -------
# Called by SetupComplete.cmd on first boot after Windows Setup.
# Runs as LocalSystem before any user logs in.
#
# Installs OpenSSH Client and Server Windows features, sets sshd to
# Automatic startup, starts the service, and opens TCP/22 in the firewall.
# Idempotent: safe to run multiple times.
#
# Log file
# --------
#   C:\ProgramData\ExampleMusic\Logs\Install-OpenSSH.log
#
# ==============================================================================

#Requires -Version 5.1

$ScriptVersion = '1.0.0'
$LogDir        = 'C:\ProgramData\ExampleMusic\Logs'
$LogFile       = "$LogDir\Install-OpenSSH.log"

if (-not (Test-Path -Path $LogDir)) {
  New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

Start-Transcript -Path $LogFile -Append -Force

Write-Host ''
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host '  Example Music Limited' -ForegroundColor Cyan
Write-Host "  Install-OpenSSH.ps1 v$ScriptVersion" -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ''

function Write-Status {
  param([string]$Message, [string]$Colour = 'White')
  Write-Host "  $Message" -ForegroundColor $Colour
}

# ------------------------------------------------------------------------------
# OpenSSH Client
# ------------------------------------------------------------------------------
Write-Status 'Checking OpenSSH Client...' Cyan
$cap = Get-WindowsCapability -Online -Name 'OpenSSH.Client~~~~0.0.1.0' -ErrorAction SilentlyContinue
if ($cap.State -eq 'Installed') {
  Write-Status 'OpenSSH Client already installed.' Green
} else {
  Write-Status 'Installing OpenSSH Client...' Yellow
  Add-WindowsCapability -Online -Name 'OpenSSH.Client~~~~0.0.1.0' | Out-Null
  Write-Status 'OpenSSH Client installed.' Green
}
Write-Host ''

# ------------------------------------------------------------------------------
# OpenSSH Server
# ------------------------------------------------------------------------------
Write-Status 'Checking OpenSSH Server...' Cyan
$cap = Get-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0' -ErrorAction SilentlyContinue
if ($cap.State -eq 'Installed') {
  Write-Status 'OpenSSH Server already installed.' Green
} else {
  Write-Status 'Installing OpenSSH Server...' Yellow
  Add-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0' | Out-Null
  Write-Status 'OpenSSH Server installed.' Green
}
Write-Host ''

# ------------------------------------------------------------------------------
# sshd service
# ------------------------------------------------------------------------------
Write-Status 'Configuring sshd...' Cyan
$svc = Get-Service -Name sshd -ErrorAction SilentlyContinue
if ($null -eq $svc) {
  Write-Status 'WARNING: sshd not found. OpenSSH Server may not have installed correctly.' Red
} else {
  Set-Service -Name sshd -StartupType Automatic
  Write-Status 'sshd set to Automatic.' Green
  if ($svc.Status -ne 'Running') {
    Start-Service -Name sshd
    Write-Status 'sshd started.' Green
  } else {
    Write-Status 'sshd already running.' Green
  }
}
Write-Host ''

# ------------------------------------------------------------------------------
# Firewall rule TCP/22
# ------------------------------------------------------------------------------
Write-Status 'Checking firewall rule for TCP/22...' Cyan
$fw = Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue
if ($null -ne $fw) {
  Write-Status 'Firewall rule already exists.' Green
} else {
  Write-Status 'Creating firewall rule...' Yellow
  New-NetFirewallRule `
    -Name        'OpenSSH-Server-In-TCP' `
    -DisplayName 'OpenSSH Server (TCP/22)' `
    -Description 'Created by Example Music Install-OpenSSH.ps1' `
    -Direction   Inbound `
    -Protocol    TCP `
    -LocalPort   22 `
    -Action      Allow `
    -Profile     Any | Out-Null
  Write-Status 'Firewall rule created.' Green
}
Write-Host ''

Write-Host '============================================================' -ForegroundColor Cyan
Write-Host '  Install-OpenSSH complete.' -ForegroundColor Green
Write-Host "  Log: $LogFile" -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ''

Stop-Transcript
exit 0
