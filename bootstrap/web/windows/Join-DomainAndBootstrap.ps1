# =========================================================
# PostOOBE Domain Join & Bootstrap Script
# Example Music Limited
# Forest: jukebox.internal
# Domains: example.net / example.org / example.com
# =========================================================
# DeployTools share: \\EXADCSCPH001\DeployTools
# NOTE: DeployTools will migrate to DFS once all sites are commissioned. Update
# $DeployToolsShare at that point to \\jukebox.internal\DeployTools (DFS namespace).
#
# Credentials: JUKEBOX\Administrator is a forest-level DA.
#   It is valid across all child domains (example.net, example.org, example.com) via
#   the forest trust. Do NOT use a per-domain DA for DeployTools access.
#
# The script expects to be run from a mapped drive pointing at the DeployTools share.
# It does not care which drive letter is used -- it verifies the UNC path matches.
#
# Map the drive before running:
#   net use Z: \\EXADCSCPH001\DeployTools
#   (Windows will prompt for JUKEBOX\Administrator credentials)
#   Z:\Join-DomainAndBootstrap.ps1
#
# Compatible with Windows PowerShell 5.1 and PowerShell 7+. No PS7-only cmdlets used.
#
# Changelog:
#   2026-03-26  Stage 22b added -- Windows Terminal install + config.
#               Installs via choco install microsoft-windows-terminal.
#               Writes settings.json to both the Chocolatey unpackaged path
#               (%LOCALAPPDATA%\Microsoft\Windows Terminal\) and the Store/MSIX
#               path (%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\)
#               and pre-seeds the Default user profile Store path.
#               Writes per-user PS7 CurrentUserAllHosts profile with
#               PSWriteColor, Terminal-Icons, and PSReadLine options.
#               Font (JetBrainsMono Nerd Font) already handled in Stage 20.
#   2026-03-22  Stage 17b added -- Windows EMS / SAC serial console configuration.
#               Enables Windows Boot Manager serial redirect (boot menu over COM1)
#               and SAC (Special Administration Console). Gives ipmitool SOL a full
#               PowerShell-capable rescue console equivalent to Linux ttyS0 getty.
#               Auto-enabled on Server Core; prompted on Desktop Experience.
#               COM1 presence checked before configuring.
# =========================================================

$ErrorActionPreference = 'Stop'

# ---------- Configuration ----------
$DeployToolsShare = '\\EXADCSCPH001\DeployTools'   # Update to DFS path once live
$ForestRoot     = 'jukebox.internal'
$AllowedDomains   = @('jukebox.internal', 'example.com', 'example.net', 'example.org')
$WallpaperUrl   = 'http://192.168.139.50/ExampleMusicWallpaper.png'
$WallpaperDest  = 'C:\Windows\Web\Wallpaper\ExampleMusic\corporate.png'

# Ansible SSH public key -- deployed to administrators_authorized_keys.
# Grants Ansible access as any member of local Administrators or JUKEBOX\Domain Admins.
# Update this if the Ansible node is rebuilt.
$AnsiblePubKey = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCyEVQgZP5f3dSLQ/cK7CV1tjN152BhZGQ7evsOTARTG5o9AmMzn4xFurdvmkFli4dEr7HZ3Dp83jxAMbHJ7d0eVuYNHG1n7ktm4FwYPhzBS3Kni3UvM91TeB6kvNZU1jFVE3oaDlft/C104M5S72zUx9SIzI5XH3fUyssAQEGoEoLzW1u4Tj84pxdXoIdGAGJCZ/gZJJFoPGLNkn3m19ML5EQzIpD4sO6yhODVu7gc9RckFGJpTD1CgKa5q4RPWPMN2y3Xw/J95VTHV8+NCBNKGzoVGdxu1E94+aCV5UCaxvgtLGcjJfv4D8Yrnxd//ZTjFYmT+DdIc6XsgYDYvr7Eoanv+bg8mtVVKxhwsxD3XOoxVdLhvCfYlg9IjXPG65GoTDrZuRfkUA6e1YnEaC4wvyXtwcnMV5NaklwAiIH5VLLo6laK1lyxr1tZEVpYx0F0S9S+oVDRPdpoVH98zE8JkPGWI6xSwaekMUMrAu5fZ/7Dfw2LAwAG7dixMroAj3c= knightmare@ansible'

# Site code -> subnet third-octet map
$SubnetSiteMap = @{
  '76'  = @{ Site = 'FAL'; Domain = 'jukebox.internal' }   # Falkirk -- head office
  '131' = @{ Site = 'EDI'; Domain = 'jukebox.internal' }   # Edinburgh
  '141' = @{ Site = 'GLA'; Domain = 'jukebox.internal' }   # Glasgow
  '41'  = @{ Site = 'CLY'; Domain = 'jukebox.internal' }   # Clydebank
  '138' = @{ Site = 'DUN'; Domain = 'jukebox.internal' }   # Dundee
  '173' = @{ Site = 'PER'; Domain = 'jukebox.internal' }   # Perth
  '224' = @{ Site = 'ABD'; Domain = 'jukebox.internal' }   # Aberdeen
  '20'  = @{ Site = 'LND'; Domain = 'jukebox.internal' }   # London
  '121' = @{ Site = 'BIR'; Domain = 'jukebox.internal' }   # Birmingham
  '161' = @{ Site = 'MCR'; Domain = 'jukebox.internal' }   # Manchester
  '151' = @{ Site = 'LIV'; Domain = 'jukebox.internal' }   # Liverpool
  '191' = @{ Site = 'NEW'; Domain = 'jukebox.internal' }   # Newcastle
  '114' = @{ Site = 'SHE'; Domain = 'jukebox.internal' }   # Sheffield
  '142' = @{ Site = 'HAL'; Domain = 'jukebox.internal' }   # Halifax
  '148' = @{ Site = 'HUL'; Domain = 'jukebox.internal' }   # Hull
  '247' = @{ Site = 'COV'; Domain = 'jukebox.internal' }   # Coventry
  '231' = @{ Site = 'CPH'; Domain = 'jukebox.internal' }   # Kobenhavn (also example.net -- confirm)
  '126' = @{ Site = 'ODE'; Domain = 'jukebox.internal' }   # Odense -- EU hub
  '65'  = @{ Site = 'KGE'; Domain = 'jukebox.internal' }   # Koge
  '246' = @{ Site = 'FAX'; Domain = 'jukebox.internal' }   # Faxe
  '238' = @{ Site = 'KOR'; Domain = 'jukebox.internal' }   # Korsor
  '228' = @{ Site = 'BON'; Domain = 'jukebox.internal' }   # Bonn
  '113' = @{ Site = 'BER'; Domain = 'jukebox.internal' }   # West Berlin
  '189' = @{ Site = 'MUN'; Domain = 'jukebox.internal' }   # Munich
  '46'  = @{ Site = 'GOT'; Domain = 'jukebox.internal' }   # Gothenburg
  '47'  = @{ Site = 'OSL'; Domain = 'jukebox.internal' }   # Oslo
  '31'  = @{ Site = 'AMS'; Domain = 'jukebox.internal' }   # Amsterdam
  '39'  = @{ Site = 'MIL'; Domain = 'jukebox.internal' }   # Milan
  '78'  = @{ Site = 'VIE'; Domain = 'jukebox.internal' }   # Vienna
  '136' = @{ Site = 'BRK'; Domain = 'jukebox.internal' }   # Brockville -- NA/APAC hub
  '164' = @{ Site = 'TOR'; Domain = 'jukebox.internal' }   # Toronto
  '154' = @{ Site = 'MTL'; Domain = 'jukebox.internal' }   # Montreal
  '213' = @{ Site = 'LAX'; Domain = 'jukebox.internal' }   # Los Angeles
  '212' = @{ Site = 'NYC'; Domain = 'jukebox.internal' }   # New York
  '201' = @{ Site = 'NJC'; Domain = 'jukebox.internal' }   # New Jersey
  '135' = @{ Site = 'MIA'; Domain = 'jukebox.internal' }   # Miami
  '44'  = @{ Site = 'ATL'; Domain = 'jukebox.internal' }   # Athens GA
  '214' = @{ Site = 'CHI'; Domain = 'jukebox.internal' }   # Chicago
  '29'  = @{ Site = 'SYD'; Domain = 'jukebox.internal' }   # Sydney
  '61'  = @{ Site = 'MEL'; Domain = 'jukebox.internal' }   # Melbourne
  '93'  = @{ Site = 'AKL'; Domain = 'jukebox.internal' }   # Auckland
  '139' = @{ Site = 'CLD'; Domain = 'jukebox.internal' }   # Cloud / provisioning
}

# ---------- UI helpers ----------
function Info($m) { Write-Host "[*] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[+] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "[!] $m" -ForegroundColor Yellow }
function Nope($m) { Write-Host "[X] $m" -ForegroundColor Red; Start-Sleep 2 }

# Helper: set a registry value, creating the key path if needed
function Set-RegValue {
  param([string]$Path, [string]$Name, $Value, [string]$Type = 'DWord')
  if (-not (Test-Path $Path)) { New-Item -Path $Path -Force | Out-Null }
  Set-ItemProperty -Path $Path -Name $Name -Value $Value -Type $Type
}

# Helper: convert domain name to DN -- PS5/7 compatible, no Join-String
function Convert-DomainToDN {
  param([string]$Domain)
  (($Domain -split '\.') | ForEach-Object { "DC=$_" }) -join ','
}

# ---------- Stage 0: Safety checks ----------

# Verify the script is running from the DeployTools share, not a local copy. We use Test-Path
# against a known file on the share rather than parsing net use output -- the share may be
# mounted by IP rather than hostname, so string matching on the UNC path is unreliable.
$ScriptDir = Split-Path $PSCommandPath -Parent
if (-not (Test-Path "$ScriptDir\PostOOBE.cmd")) {
  Nope "This script must be run from the DeployTools share, not a local copy."
  Nope "Map the share first:  net use Z: $DeployToolsShare"
  Nope "Then run from there:  Z:\Join-DomainAndBootstrap.ps1"
  exit 1
}

$Marker = 'C:\Windows\Temp\PostOOBE-Bootstrap.done'
if (Test-Path $Marker) {
  Warn "Bootstrap already completed (marker found at $Marker). Exiting."
  Warn "Delete $Marker and re-run if you want to force a re-bootstrap."
  exit 0
}

$CurrentPrincipal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $CurrentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Nope "Not running elevated. Right-click and run as Administrator."
  exit 1
}

# ---------- Stage 0b: Preflight checks ----------
# Inventory everything the script will need before touching anything. Reports found/missing for
# each item and asks for confirmation to proceed. Nothing is installed or changed during this
# stage.

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  PREFLIGHT CHECKS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$PreflightOk  = $true
$PreflightWarns = 0

function Check {
  param(
    [string]$Label,
    [bool]$Result,
    [string]$OkMsg,
    [string]$FailMsg,
    [bool]$Required = $false
  )
  if ($Result) {
    Write-Host ("  [OK]   {0,-40} {1}" -f $Label, $OkMsg) -ForegroundColor Green
  } elseif ($Required) {
    Write-Host ("  [FAIL] {0,-40} {1}" -f $Label, $FailMsg) -ForegroundColor Red
    $script:PreflightOk = $false
  } else {
    Write-Host ("  [WARN] {0,-40} {1}" -f $Label, $FailMsg) -ForegroundColor Yellow
    $script:PreflightWarns++
  }
}

# -- Network and DC --
$DcIp    = '192.168.231.10'
$DcReachable = (Test-Connection $DcIp -Count 1 -Quiet -ErrorAction SilentlyContinue)
Check 'Primary DC reachable' $DcReachable "$DcIp responded" "$DcIp not responding -- domain join will fail" -Required $true

$DnsOk = $false
try { $DnsOk = ([bool](Resolve-DnsName jukebox.internal -ErrorAction SilentlyContinue)) } catch {}
Check 'DNS: jukebox.internal resolves' $DnsOk 'OK' 'not resolving -- check DNS server settings' -Required $true

# -- Wallpaper (downloaded at runtime from internal web server, not from share) --
$WallpaperReachable = $false
try {
  $wr = Invoke-WebRequest -Uri $WallpaperUrl -Method Head -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
  $WallpaperReachable = ($wr.StatusCode -eq 200)
} catch {}
Check 'Wallpaper URL reachable' $WallpaperReachable $WallpaperUrl "not reachable -- wallpaper stage will be skipped"

# -- Share assets --
Check 'PostOOBE.cmd on share'           (Test-Path "$ScriptDir\PostOOBE.cmd")          'found' 'not found -- expected alongside this script' -Required $true
Check 'RustDesk installer on share'     (Test-Path "$ScriptDir\utils\rustdesk-1.4.5-x86_64.exe") 'found' 'not found -- will fall back to Chocolatey'
Check 'QEMU guest agent on share'       (Test-Path "$ScriptDir\drivers\virtio\guest-agent\qemu-ga-x86_64.msi") 'found' 'not found -- will fall back to Chocolatey'
Check 'VMware Tools installer on share' ([bool](Get-ChildItem "$ScriptDir\drivers\vmware\" -Filter 'VMware-tools-*.exe' -ErrorAction SilentlyContinue)) 'found' 'not found -- will fall back to Chocolatey'

# -- Internet reachability --
$ChocoReachable = $false
try {
  $cr = Invoke-WebRequest -Uri 'https://community.chocolatey.org' -Method Head -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
  $ChocoReachable = ($cr.StatusCode -eq 200)
} catch {}
Check 'Chocolatey.org reachable' $ChocoReachable 'reachable' 'not reachable -- package installs will fail without a local mirror'

$GithubReachable = $false
try {
  $gr = Invoke-WebRequest -Uri 'https://github.com' -Method Head -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
  $GithubReachable = ($gr.StatusCode -eq 200)
} catch {}
Check 'GitHub reachable (Nerd Fonts ZIP)' $GithubReachable 'reachable' 'not reachable -- JetBrainsMono font install will be skipped'

# -- Local machine state (informational) --
$AlreadyJoined = (Get-WmiObject Win32_ComputerSystem).PartOfDomain
Check 'Not already domain joined'     (-not $AlreadyJoined)                  'workgroup machine' 'already joined -- domain join stage will be skipped'
Check 'PowerShell 7 present'        (Test-Path 'C:\Program Files\PowerShell\7\pwsh.exe')   'found' 'not present -- will be installed via Chocolatey'
Check 'Chocolatey present'        ([bool](Get-Command choco.exe -ErrorAction SilentlyContinue)) 'found' 'not present -- will be installed'
Check 'OpenSSH already running'       ((Get-Service sshd -ErrorAction SilentlyContinue).Status -eq 'Running') 'running' 'not running -- will be installed and started'

Write-Host ""

if (-not $PreflightOk) {
  Write-Host "============================================================" -ForegroundColor Red
  Write-Host "  PREFLIGHT FAILED -- fix the FAIL items above" -ForegroundColor Red
  Write-Host "============================================================" -ForegroundColor Red
  exit 1
}

if ($PreflightWarns -gt 0) {
  Write-Host ("  Preflight passed with {0} warning(s). WARN items are non-fatal." -f $PreflightWarns) -ForegroundColor Yellow
} else {
  Write-Host "  All preflight checks passed." -ForegroundColor Green
}
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

if ((Read-Host "Continue? [YES to proceed]") -ne 'YES') {
  Warn "Aborted at preflight."
  exit 0
}

New-Item -ItemType File -Path $Marker -Force | Out-Null

Register-EngineEvent PowerShell.Exiting -Action {
  Write-Host "Session exit detected during bootstrap. Rebooting." -ForegroundColor Red
  Restart-Computer -Force
} | Out-Null

Info "Starting PostOOBE bootstrap..."
Write-Host ""

# ---------- Stage 1: Detect hypervisor ----------
Info "Detecting hypervisor platform..."
$HypervisorVendor = (Get-WmiObject Win32_ComputerSystem).Manufacturer

if ($HypervisorVendor -match 'VMware') {
  $Platform = 'VMware'
  Warn "VMware guest detected -- VMware Tools will be installed."
} elseif ($HypervisorVendor -match 'QEMU|Proxmox') {
  $Platform = 'Proxmox'
  Info "Proxmox/KVM guest detected -- VirtIO guest agent will be installed."
} else {
  $Platform = 'Physical'
  Info "Physical hardware or unknown hypervisor (Manufacturer: $HypervisorVendor)."
}

# ---------- Stage 2: Detect site from IP ----------
Info "Detecting site from network configuration..."
$LocalIP = (Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object {
    $_.IPAddress -notmatch '^127\.' -and
    $_.IPAddress -notmatch '^169\.254\.' -and
    $_.PrefixOrigin -ne 'WellKnown'
  } | Select-Object -First 1).IPAddress

$DetectedSite  = $null
$SuggestedDomain = $null

if ($LocalIP) {
  $ThirdOctet = ($LocalIP -split '\.')[2]
  if ($SubnetSiteMap.ContainsKey($ThirdOctet)) {
    $DetectedSite  = $SubnetSiteMap[$ThirdOctet].Site
    $SuggestedDomain = $SubnetSiteMap[$ThirdOctet].Domain
    Ok "Detected site: $DetectedSite (IP: $LocalIP, suggested domain: $SuggestedDomain)"
  } else {
    Warn "Subnet /$ThirdOctet not in site map. Manual entry required."
  }
} else {
  Warn "No routable IP found. Check network connectivity."
}

# ---------- Stage 3: Identity ----------
# Pre-fill hostname with the current machine name. Operator just hits Enter to confirm
# or types a new name if this is being run before the machine has been renamed.
$CurrentName = $env:COMPUTERNAME
Write-Host ""
Info "Current hostname: $CurrentName"
do {
  $HostInput = Read-Host "Hostname to join with (Enter to confirm '$CurrentName')"
  if ([string]::IsNullOrWhiteSpace($HostInput)) {
    $ComputerName = $CurrentName
  } else {
    $ComputerName = $HostInput
  }
  if ($ComputerName -notmatch '^[A-Za-z0-9-]{1,15}$') {
    Nope "Invalid hostname -- max 15 chars, letters/numbers/hyphens only."
    $ComputerName = $null
  }
} until ($ComputerName)

Write-Host ""
Info "Available domains in forest $ForestRoot :"
$AllowedDomains | ForEach-Object { Write-Host "  - $_" -ForegroundColor White }

if ($SuggestedDomain) {
  Write-Host ""
  Warn "Suggested domain based on site detection: $SuggestedDomain"
}

do {
  $TargetDomain = Read-Host "Enter target domain [$SuggestedDomain]"
  if ([string]::IsNullOrWhiteSpace($TargetDomain) -and $SuggestedDomain) {
    $TargetDomain = $SuggestedDomain
  }
  if ($TargetDomain -notin $AllowedDomains) {
    Nope "That domain is not authorised. Allowed: $($AllowedDomains -join ', ')"
    $TargetDomain = $null
  }
} until ($TargetDomain)

$BaseDN = Convert-DomainToDN $TargetDomain

# ---------- Stage 4: OU enumeration ----------
# Uses System.DirectoryServices with explicit credentials so the bind succeeds even before this
# machine is domain-joined. We collect credentials here and reuse them for the domain join in
# Stage 5.
Info "Enumerating OUs in $TargetDomain..."

# Collect join credentials now -- needed for both the LDAP query and Add-Computer.
# Read-Host -AsSecureString keeps the password masked in the console without
# popping a GUI dialog (which hangs over SSH and some console hosts).
Info "Enter credentials authorised to join $TargetDomain"
Info "(Use JUKEBOX\Administrator for forest-level access across all domains)"
$JoinUser = Read-Host "Domain join username [JUKEBOX\Administrator]"
if ([string]::IsNullOrWhiteSpace($JoinUser)) { $JoinUser = 'JUKEBOX\Administrator' }
$JoinPass = Read-Host "Password for $JoinUser" -AsSecureString
$Cred   = New-Object System.Management.Automation.PSCredential($JoinUser, $JoinPass)

# Convert SecureString to plain text only for the LDAP bind -- it never gets
# written anywhere, lives only in this variable for the duration of the query.
$JoinPassPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
  [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($JoinPass)
)

$OUs    = @()
$SelectedOU = $null

# Derive the primary DC IP from the local subnet.
# Convention: .10 is always the primary DC for any site (e.g. 192.168.231.10 for CPH).
# Unjoined machines cannot perform DC discovery via DNS SRV lookup, so we bind
# directly by IP. This bypasses the DC locator entirely and works reliably
# from workgroup state.
$LocalSubnet = ($LocalIP -split '\.')[0..2] -join '.'
$PrimaryDcIp = "$LocalSubnet.10"

# Fallback: if the derived IP doesn't respond, use the known forest root DC
if (-not (Test-Connection $PrimaryDcIp -Count 1 -Quiet -ErrorAction SilentlyContinue)) {
  Warn "Local DC $PrimaryDcIp not responding -- falling back to CPH primary (192.168.231.10)"
  $PrimaryDcIp = '192.168.231.10'
}

Info "Binding to DC at $PrimaryDcIp..."

try {
  $Entry  = New-Object System.DirectoryServices.DirectoryEntry("LDAP://$PrimaryDcIp/$BaseDN", $JoinUser, $JoinPassPlain)
  $Entry.RefreshCache() | Out-Null
  $Searcher = New-Object System.DirectoryServices.DirectorySearcher($Entry)
  $Searcher.Filter   = '(objectClass=organizationalUnit)'
  $Searcher.PageSize = 1000
  $OUs = @($Searcher.FindAll() |
    ForEach-Object { $_.Properties.distinguishedname[0] } |
    Sort-Object)
  Ok "Found $($OUs.Count) OUs."
} catch {
  Warn "LDAP enumeration failed: $($_.Exception.Message)"
} finally {
  $JoinPassPlain = $null
  [System.GC]::Collect()
}

if ($OUs.Count -gt 0) {
  Write-Host ""
  Info "Available OUs:"
  for ($i = 0; $i -lt $OUs.Count; $i++) {
    Write-Host ("  [{0}] {1}" -f $i, $OUs[$i]) -ForegroundColor White
  }
  Write-Host ""
  do {
    $OUInput = Read-Host "Select OU number"
    if ($OUInput -match '^\d+$' -and [int]$OUInput -lt $OUs.Count) {
      $SelectedOU = $OUs[[int]$OUInput]
    } else {
      Nope "Enter a number between 0 and $($OUs.Count - 1)."
    }
  } until ($SelectedOU)
} else {
  # Should not reach here in normal operation -- kept as a last resort
  Warn "No OUs returned from $PrimaryDcIp. Check DC connectivity and credentials."
  Info "Enter OU manually. Example: OU=Domain Controllers,$BaseDN"
  $SelectedOU = Read-Host "OU distinguished name"
}

Ok "Selected OU: $SelectedOU"

# ---------- Confirm ----------
Write-Host ""
Warn "About to join this machine to the domain with these settings:"
Write-Host "  Hostname : $ComputerName"
Write-Host "  Domain   : $TargetDomain"
Write-Host "  OU     : $SelectedOU"
Write-Host "  Platform : $Platform"
if ($DetectedSite) { Write-Host "  Site   : $DetectedSite" }
Write-Host ""

if ((Read-Host "Type YES to continue") -ne 'YES') {
  Nope "Aborted."
  Remove-Item $Marker -Force -ErrorAction SilentlyContinue
  exit 1
}

# Credentials already collected in Stage 4 -- $Cred is ready for Add-Computer.

# ---------- Stage 5: Rename + join ----------
if ($env:COMPUTERNAME -ne $ComputerName) {
  Info "Renaming computer to $ComputerName..."
  Rename-Computer -NewName $ComputerName -Force
}

Info "Joining $TargetDomain..."
Add-Computer -DomainName $TargetDomain -OUPath $SelectedOU -Credential $Cred -Force
Ok "Domain join successful."

# ---------- Stage 6: Power and pagefile ----------
Info "Configuring power settings..."
powercfg /h off
Ok "Hibernation disabled."
Set-RegValue -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management' -Name 'ClearPageFileAtShutdown' -Value 1
Ok "ClearPageFileAtShutdown set."

# ---------- Stage 7: Locale ----------
Info "Setting locale to British English (en-GB)..."
Set-WinSystemLocale -SystemLocale en-GB
Set-WinUserLanguageList -LanguageList en-GB -Force
Set-WinUILanguageOverride -Language en-GB
Set-WinHomeLocation -GeoId 242
Set-Culture en-GB
Set-TimeZone -Id 'GMT Standard Time'
# control.exe uses double-comma syntax that PS5 misparses as an argument list.
# Pass it through cmd /c to avoid the parser error.
cmd /c "control.exe intl.cpl,,/f:`"$env:SystemRoot\System32\en-GB`""
Ok "Locale set to en-GB, timezone GMT Standard Time."

# ---------- Stage 8: Screen lock ----------
Info "Configuring screen lock..."

$IsServerCore = $false
$GuiFeature   = Get-WindowsFeature Server-Gui-Shell -ErrorAction SilentlyContinue
$ProductType  = (Get-CimInstance Win32_OperatingSystem).ProductType
if ($GuiFeature -and -not $GuiFeature.Installed -and $ProductType -ne 1) {
  $IsServerCore = $true
}

if ($IsServerCore) {
  powercfg /change monitor-timeout-ac 0
  powercfg /change monitor-timeout-dc 0
  Info "Server Core -- console timeout disabled. RDP idle timeouts via GPO."
} else {
  # Layer 1: monitor off after 60 minutes
  powercfg /change monitor-timeout-ac 60
  powercfg /change monitor-timeout-dc 60

  # Layer 2: blank screensaver with password lock in Default user hive
  reg load HKLM\TempScreensaverHive 'C:\Users\Default\NTUSER.DAT' | Out-Null
  try {
    $SsPath = 'HKLM:\TempScreensaverHive\Control Panel\Desktop'
    Set-RegValue -Path $SsPath -Name 'ScreenSaveActive'  -Value '1'      -Type String
    Set-RegValue -Path $SsPath -Name 'ScreenSaverIsSecure' -Value '1'      -Type String
    Set-RegValue -Path $SsPath -Name 'ScreenSaveTimeOut'   -Value '3600'     -Type String
    Set-RegValue -Path $SsPath -Name 'SCRNSAVE.EXE'    -Value 'scrnsave.scr' -Type String
  } finally {
    [gc]::Collect()
    reg unload HKLM\TempScreensaverHive | Out-Null
  }

  # Apply to current user (Administrator) as well
  $CsPath = 'HKCU:\Control Panel\Desktop'
  Set-RegValue -Path $CsPath -Name 'ScreenSaveActive'  -Value '1'      -Type String
  Set-RegValue -Path $CsPath -Name 'ScreenSaverIsSecure' -Value '1'      -Type String
  Set-RegValue -Path $CsPath -Name 'ScreenSaveTimeOut'   -Value '3600'     -Type String
  Set-RegValue -Path $CsPath -Name 'SCRNSAVE.EXE'    -Value 'scrnsave.scr' -Type String

  # Layer 3: machine policy backstop
  Set-RegValue -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' -Name 'InactivityTimeoutSecs' -Value 3600
  Ok "Screen lock set to 60 minutes (screensaver + policy backstop)."
}

# ---------- Stage 9: Corporate wallpaper ----------
Info "Deploying corporate wallpaper..."
$WallpaperDir = Split-Path $WallpaperDest -Parent
if (-not (Test-Path $WallpaperDir)) { New-Item -ItemType Directory -Path $WallpaperDir -Force | Out-Null }

try {
  Invoke-WebRequest -Uri $WallpaperUrl -OutFile $WallpaperDest -UseBasicParsing
  Ok "Wallpaper downloaded to $WallpaperDest"
} catch {
  Warn "Could not download wallpaper -- $($_.Exception.Message)"
  Warn "Place corporate.png at $WallpaperDest manually."
}

if (Test-Path $WallpaperDest) {
  Set-RegValue -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\PersonalizationCSP' -Name 'DesktopImagePath'   -Value $WallpaperDest -Type String
  Set-RegValue -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\PersonalizationCSP' -Name 'DesktopImageUrl'  -Value $WallpaperDest -Type String
  Set-RegValue -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\PersonalizationCSP' -Name 'DesktopImageStatus' -Value 1
  Set-RegValue -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System'  -Name 'Wallpaper'      -Value $WallpaperDest -Type String
  Set-RegValue -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System'  -Name 'WallpaperStyle'   -Value '10'       -Type String
  Set-RegValue -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer'  -Name 'NoThemesTab'    -Value 1
  Ok "Wallpaper set and locked."
} else {
  Warn "Wallpaper file not present -- registry keys not written."
}

# ---------- Stage 10: Dark mode ----------
Info "Enabling dark mode..."
Set-RegValue -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize' -Name 'AppsUseLightTheme'  -Value 0
Set-RegValue -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize' -Name 'SystemUsesLightTheme' -Value 0

reg load HKLM\TempDarkHive 'C:\Users\Default\NTUSER.DAT' | Out-Null
try {
  $DarkPath = 'HKLM:\TempDarkHive\SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize'
  Set-RegValue -Path $DarkPath -Name 'AppsUseLightTheme'  -Value 0
  Set-RegValue -Path $DarkPath -Name 'SystemUsesLightTheme' -Value 0
} finally {
  [gc]::Collect()
  reg unload HKLM\TempDarkHive | Out-Null
}
Ok "Dark mode enabled (system + default user hive)."

# ---------- Stage 11: Chocolatey ----------
Info "Checking Chocolatey..."
if (-not (Get-Command choco.exe -ErrorAction SilentlyContinue)) {
  Set-ExecutionPolicy Bypass -Scope Process -Force
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  Invoke-Expression ((New-Object Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
  Ok "Chocolatey installed."
} else {
  Ok "Chocolatey already present."
}

# ---------- Stage 12: Platform-specific guest tools ----------
switch ($Platform) {
  'VMware'   {
    Info "Installing VMware Tools..."
    $VmwareLocal = Get-ChildItem "$ScriptDir\drivers\vmware\" -Filter 'VMware-tools-*.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($VmwareLocal) {
      Start-Process $VmwareLocal.FullName -ArgumentList '/S /v"/qn REBOOT=R"' -Wait
      Ok "VMware Tools installed from share."
    } else {
      choco install vmware-tools -y
      Ok "VMware Tools installed via Chocolatey."
    }
  }
  'Proxmox'  {
    Info "Installing VirtIO guest agent..."
    $QemuLocal = "$ScriptDir\drivers\virtio\guest-agent\qemu-ga-x86_64.msi"
    if (Test-Path $QemuLocal) {
      Start-Process msiexec.exe -ArgumentList "/i `"$QemuLocal`" /qn /norestart" -Wait
      Ok "VirtIO guest agent installed from share."
    } else {
      choco install qemu-guest-agent -y
      Ok "VirtIO guest agent installed via Chocolatey."
    }
  }
  'Physical' { Info "Physical hardware -- skipping hypervisor guest tools." }
}

# ---------- Stage 13: RustDesk ----------
Info "Installing RustDesk..."
$RustDeskLocal = Join-Path $ScriptDir 'utils\rustdesk-1.4.5-x86_64.exe'
if (Test-Path $RustDeskLocal) {
  Start-Process -FilePath $RustDeskLocal -ArgumentList '--silent-install' -Wait
} else {
  choco install rustdesk -y
}
Ok "RustDesk installed."

# ---------- Stage 14: Baseline packages ----------
Info "Installing baseline packages..."
$Packages = @(
  'winscp.install'
  'putty.install'
  'hyper'
  'notepadplusplus.install'
  'powershell-core'
  '7zip.install'
  'far'
  'dua-cli'
)
foreach ($pkg in $Packages) {
  Info "  $pkg..."
  choco install $pkg -y
}
Ok "Baseline packages installed."

# ---------- Stage 15: RSAT ----------
# Server Core uses Install-WindowsFeature (ServerManager).
# Desktop/GUI Server uses Add-WindowsCapability.
# Both methods are tried so this stage works on any edition.
Info "Installing RSAT tools..."

if ($IsServerCore) {
  # Server Core -- Install-WindowsFeature is the only supported method.
  # AD-Domain-Services must be installed before the RSAT tools that depend on it.
  $RSATFeatures = @(
    'AD-Domain-Services'     # required before RSAT-AD-PowerShell on Core
    'RSAT-AD-PowerShell'
    'RSAT-DNS-Server'
    'GPMC'
  )
  foreach ($feat in $RSATFeatures) {
    $existing = Get-WindowsFeature -Name $feat -ErrorAction SilentlyContinue
    if ($existing -and $existing.Installed) {
      Ok "$feat already installed."
    } else {
      Install-WindowsFeature -Name $feat -IncludeManagementTools | Out-Null
      Ok "$feat installed."
    }
  }
} else {
  # Desktop / GUI Server -- Add-WindowsCapability
  $RSATCaps = @(
    'RSAT.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0'
    'RSAT.DNS.Tools~~~~0.0.1.0'
    'RSAT.GroupPolicy.Management.Tools~~~~0.0.1.0'
  )
  foreach ($cap in $RSATCaps) {
    $existing = Get-WindowsCapability -Online -Name $cap -ErrorAction SilentlyContinue
    if ($existing -and $existing.State -eq 'Installed') {
      Ok "$cap already installed."
    } else {
      Add-WindowsCapability -Online -Name $cap | Out-Null
      Ok "$cap installed."
    }
  }
}

# ---------- Stage 16: OpenSSH ----------
Info "Configuring OpenSSH Server..."

# OpenSSH is already installed and started by SetupComplete.cmd (autounattend build).
# If this machine was not built via autounattend, install it here.
$sshdSvc = Get-Service sshd -ErrorAction SilentlyContinue
if (-not $sshdSvc -or $sshdSvc.Status -ne 'Running') {
  Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 | Out-Null
  Set-Service -Name sshd -StartupType Automatic
  Start-Service -Name sshd
  Ok "OpenSSH installed and started."
} else {
  Set-Service -Name sshd -StartupType Automatic
  Ok "OpenSSH already running."
}

$AdminKeyFile = 'C:\ProgramData\ssh\administrators_authorized_keys'
if (-not (Test-Path (Split-Path $AdminKeyFile -Parent))) {
  New-Item -ItemType Directory -Path (Split-Path $AdminKeyFile -Parent) -Force | Out-Null
}
Set-Content -Path $AdminKeyFile -Value $AnsiblePubKey -Encoding UTF8
icacls $AdminKeyFile /inheritance:r | Out-Null
icacls $AdminKeyFile /grant 'SYSTEM:(F)' | Out-Null
icacls $AdminKeyFile /grant 'BUILTIN\Administrators:(F)' | Out-Null

$Pwsh7 = 'C:\Program Files\PowerShell\7\pwsh.exe'
$DefaultShell = if (Test-Path $Pwsh7) { $Pwsh7 } else { 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' }
Set-RegValue -Path 'HKLM:\SOFTWARE\OpenSSH' -Name 'DefaultShell'        -Value $DefaultShell -Type String
Set-RegValue -Path 'HKLM:\SOFTWARE\OpenSSH' -Name 'DefaultShellCommandOption' -Value '-NoLogo'   -Type String

if (-not (Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
}

Ok "Ansible key written to $AdminKeyFile"
Ok "SSH default shell: $DefaultShell"

# ---------- Stage 17: RDP ----------
Info "Confirming RDP enabled with NLA..."
Set-RegValue -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server'           -Name 'fDenyTSConnections' -Value 0
Set-RegValue -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name 'UserAuthentication' -Value 1
Enable-NetFirewallRule -DisplayGroup 'Remote Desktop' -ErrorAction SilentlyContinue
Set-Service -Name TermService -StartupType Automatic
Start-Service -Name TermService -ErrorAction SilentlyContinue
Ok "RDP confirmed, NLA enforced."

# ---------- Stage 17b: Serial Console / EMS / SAC ----------
# Configures Windows Emergency Management Services (EMS) and the boot manager
# serial redirect -- giving the VM an equivalent to Linux's GRUB serial menu
# and ttyS0 getty.
#
# What this enables:
#   1. Windows Boot Manager menu appears on COM1 at 115200 -- you can select
#      boot entries, access WinRE, and set advanced boot flags over SOL.
#   2. SAC (Special Administration Console) runs in the background from boot.
#      Connect via ipmitool sol activate and you get the SAC prompt.
#   3. From SAC you can open a CMD channel and launch PowerShell over serial.
#      This is the Windows equivalent of a ttyS0 rescue shell.
#
# Requires serial0: socket in the Proxmox VM config (set by create-vm.py
# when BMC emulation is enabled). COM1 must be present in the guest.
#
# SAC quick reference (from ipmitool sol activate):
#   SAC> cmd              -- open a CMD channel
#   SAC> ch -sn Cmd0001   -- switch to the CMD channel
#   (login prompt)
#   C:\> powershell       -- launch PowerShell from CMD
#   Exit SAC: <Esc>+<Tab>+<Esc> to return to SAC, then 'exit'

Info "Checking for COM1 (serial port)..."

$HasCOM1 = [bool](Get-WmiObject Win32_SerialPort -ErrorAction SilentlyContinue | Where-Object { $_.DeviceID -eq 'COM1' })
if ($HasCOM1) {
  Ok "COM1 detected -- serial port is present."
} else {
  Warn "COM1 not detected. EMS/SAC requires serial0: socket in the Proxmox VM config."
  Warn "Skipping EMS configuration. Re-run after adding the serial port."
}

if ($HasCOM1) {
  # On Server Core: default yes -- there is no GUI, serial is the primary recovery path.
  # On Desktop Experience: ask -- serial is useful but less critical.
  if ($IsServerCore) {
    $ConfigureEMS = $true
    Info "Server Core detected -- enabling EMS/SAC by default (no GUI recovery path)."
  } else {
    $ans = Read-Host "[?] Enable EMS / SAC serial console? (Windows boot menu + SAC over COM1) [Y/n]"
    $ConfigureEMS = ($ans -eq '' -or $ans -match '^[Yy]')
  }

  if ($ConfigureEMS) {
    Info "Configuring Windows Boot Manager serial redirect..."

    # Enable boot menu on serial -- this is the "GRUB menu" equivalent.
    # Without this the boot menu is silent on serial even with EMS enabled.
    bcdedit /set '{bootmgr}' displaybootmenu yes | Out-Null
    bcdedit /set '{bootmgr}' timeout 10         | Out-Null
    bcdedit /set '{bootmgr}' bootems yes         | Out-Null

    # Enable EMS for the current boot entry -- this starts SAC in the OS.
    bcdedit /ems '{current}' on | Out-Null

    # Set COM1 at 115200 8N1 -- must match Proxmox serial0 and ipmitool settings.
    bcdedit /emssettings EMSPORT:1 EMSBAUDRATE:115200 | Out-Null

    Ok "EMS enabled: boot menu + SAC on COM1 at 115200 8N1."

    # Verify -- bcdedit /enum confirms the settings were applied
    $bdout = bcdedit /enum '{bootmgr}' 2>$null
    if ($bdout -match 'bootems\s+Yes') {
      Ok "Verified: bootems Yes (boot manager will redirect to COM1)."
    } else {
      Warn "Could not verify bootems -- check manually: bcdedit /enum '{bootmgr}'"
    }

    # Enable the Special Administration Console (SAC) service.
    # sacsvr is the SAC driver -- it starts on demand when EMS is active.
    # On some minimal installs it may need to be enabled explicitly.
    $sacsvc = Get-Service sacsvr -ErrorAction SilentlyContinue
    if ($sacsvc) {
      Set-Service sacsvr -StartupType Automatic -ErrorAction SilentlyContinue
      Ok "sacsvr (SAC service) set to Automatic."
    } else {
      Warn "sacsvr not found -- SAC may not be available on this edition."
      Warn "SAC is present on: Server 2016/2019/2022/2025 Standard and Datacenter."
      Warn "It is NOT present on: Windows 10/11, Server Core Essentials."
    }

    # Print the SOL + SAC workflow for the technician
    Write-Host ""
    Write-Host "  [*] EMS / SAC Serial Console Workflow" -ForegroundColor Cyan
    Write-Host "  ──────────────────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host "  From any machine with ipmitool and access to the Proxmox node:" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  1. Connect via SOL:" -ForegroundColor White
    Write-Host "       ipmitool -I lanplus -H <pve-ip> -p <port> -U admin -P <pass> sol activate" -ForegroundColor DarkCyan
    Write-Host ""
    Write-Host "  2. On reboot you will see the Windows Boot Manager menu on the serial port." -ForegroundColor Gray
    Write-Host "     Select a boot entry or wait for auto-boot." -ForegroundColor Gray
    Write-Host ""
    Write-Host "  3. Once booted, the SAC prompt appears:" -ForegroundColor Gray
    Write-Host "       SAC>" -ForegroundColor DarkCyan
    Write-Host ""
    Write-Host "  4. Open a CMD channel:" -ForegroundColor White
    Write-Host "       SAC> cmd" -ForegroundColor DarkCyan
    Write-Host "       SAC> ch -sn Cmd0001" -ForegroundColor DarkCyan
    Write-Host ""
    Write-Host "  5. Authenticate (local admin or domain admin):" -ForegroundColor White
    Write-Host "       Username: Administrator" -ForegroundColor DarkCyan
    Write-Host "       Domain:   (press Enter for local)" -ForegroundColor DarkCyan
    Write-Host "       Password: (from password manager)" -ForegroundColor DarkCyan
    Write-Host ""
    Write-Host "  6. You now have a CMD prompt. Launch PowerShell:" -ForegroundColor White
    Write-Host "       C:\> powershell" -ForegroundColor DarkCyan
    Write-Host "       PS C:\> " -ForegroundColor DarkCyan
    Write-Host ""
    Write-Host "  7. Exit SOL: ~ then . (tilde, full stop) -- standard ipmitool escape." -ForegroundColor Gray
    Write-Host "  ──────────────────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host ""

  } else {
    Info "EMS/SAC configuration skipped."
    Info "To enable later, run as Administrator:"
    Info "  bcdedit /set '{bootmgr}' bootems yes"
    Info "  bcdedit /ems '{current}' on"
    Info "  bcdedit /emssettings EMSPORT:1 EMSBAUDRATE:115200"
    Info "  bcdedit /set '{bootmgr}' displaybootmenu yes"
    Info "  bcdedit /set '{bootmgr}' timeout 10"
  }
}

# ---------- Stage 18: PSWindowsUpdate ----------
Info "Checking PSWindowsUpdate..."
if (-not (Get-Module -ListAvailable -Name PSWindowsUpdate)) {
  Install-Module -Name PSWindowsUpdate -Force -Confirm:$false -ErrorAction SilentlyContinue
  if (Get-Module -ListAvailable -Name PSWindowsUpdate) { Ok "PSWindowsUpdate installed." }
  else { Warn "PSWindowsUpdate install failed -- install manually if needed." }
} else {
  Ok "PSWindowsUpdate already present."
}

# ---------- Stage 19: PowerShell 7 modules ----------
$Pwsh = 'C:\Program Files\PowerShell\7\pwsh.exe'
if (-not (Test-Path $Pwsh)) {
  Nope "pwsh.exe not found -- was powershell-core installed in Stage 14?"
  exit 1
}

Info "Installing PowerShell 7 modules (AllUsers scope)..."
$PS7Modules = 'PSConsoleTools','PSWindowsUpdate','PSWriteColor','PSReadLine','Terminal-Icons','CompletionPredictor','NerdFonts'

& $Pwsh -NoProfile -NonInteractive -Command {
  param($mods)
  foreach ($m in $mods) {
    if (-not (Get-Module -ListAvailable -Name $m)) {
      Install-Module $m -Force -Confirm:$false -Scope AllUsers -ErrorAction SilentlyContinue
    }
  }
} -args (,$PS7Modules)

Ok "PowerShell 7 modules installed."

# ---------- Stage 20: JetBrainsMono Nerd Font ----------
Info "Installing JetBrainsMono Nerd Font..."
$FontZip  = "$env:TEMP\JetBrainsMono.zip"
$FontDir  = "$env:TEMP\JetBrainsMono"
$FontDest = 'C:\Windows\Fonts'
$FontReg  = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'

try {
  Invoke-WebRequest -Uri 'https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip' -OutFile $FontZip -UseBasicParsing
  Expand-Archive -Path $FontZip -DestinationPath $FontDir -Force

  Get-ChildItem -Path $FontDir -Recurse -Include '*.ttf','*.otf' |
    Where-Object { $_.Name -notmatch 'Windows Compatible' } |
    ForEach-Object {
      $dest = Join-Path $FontDest $_.Name
      if (-not (Test-Path $dest)) { Copy-Item -Path $_.FullName -Destination $dest -Force }
      Set-RegValue -Path $FontReg -Name ($_.BaseName + ' (TrueType)') -Value $_.Name -Type String
    }

  Remove-Item $FontZip, $FontDir -Recurse -Force -ErrorAction SilentlyContinue
  Ok "JetBrainsMono Nerd Font installed system-wide."
} catch {
  Warn "Font download failed: $($_.Exception.Message)"
  Warn "Install JetBrainsMono Nerd Font manually from https://www.nerdfonts.com"
}

# ---------- Stage 21: PowerShell 7 profile ----------
Info "Writing PS7 AllUsersAllHosts profile..."
$PS7ProfileDir = "$env:ProgramFiles\PowerShell\7"
$PS7Profile  = "$PS7ProfileDir\profile.ps1"
if (-not (Test-Path $PS7ProfileDir)) { New-Item -ItemType Directory -Path $PS7ProfileDir -Force | Out-Null }

$ProfileContent = @'
# Example Music -- PowerShell 7 baseline profile
# Written by PostOOBE bootstrap

if (Get-Module -ListAvailable -Name PSReadLine) {
  # Emacs edit mode is required for clean paste behaviour over SSH.
  # Windows edit mode conflicts with SSH PTY handling and causes multi-line
  # pastes to arrive garbled or concatenated. Do not change to Windows mode.
  Set-PSReadLineOption -EditMode Emacs -ErrorAction SilentlyContinue
  Set-PSReadLineOption -PredictionSource HistoryAndPlugin -ErrorAction SilentlyContinue
  Set-PSReadLineOption -PredictionViewStyle InlineView -ErrorAction SilentlyContinue
}
if (Get-Module -ListAvailable -Name Terminal-Icons) {
  Import-Module Terminal-Icons -ErrorAction SilentlyContinue
}
if (Get-Module -ListAvailable -Name CompletionPredictor) {
  Import-Module CompletionPredictor -ErrorAction SilentlyContinue
}
if (Get-Module -ListAvailable -Name NerdFonts) {
  Import-Module NerdFonts -ErrorAction SilentlyContinue
}
'@

if (-not (Test-Path $PS7Profile)) {
  Set-Content -Path $PS7Profile -Value $ProfileContent -Encoding UTF8
} else {
  $existing = Get-Content $PS7Profile -Raw
  if ($existing -notmatch 'Example Music') {
    Add-Content -Path $PS7Profile -Value ("`n" + $ProfileContent) -Encoding UTF8
  }
}
Ok "PS7 profile written."

# ---------- Stage 22: Hyper config ----------
Info "Deploying Hyper terminal configuration..."

$HyperConfig = @'
"use strict";
module.exports = {
  config: {
  updateChannel: 'stable',
  fontSize: 16,
  fontFamily: '"JetBrainsMono Nerd Font", Menlo, Monaco, "Courier New", monospace',
  fontWeight: 'normal',
  fontWeightBold: 'bold',
  lineHeight: 1,
  letterSpacing: 0,
  cursorColor: '#00cc00',
  cursorAccentColor: '#000',
  cursorShape: 'BLOCK',
  cursorBlink: true,
  foregroundColor: '#00cc00',
  backgroundColor: '#002b36',
  selectionColor: 'rgba(255, 255, 255, 1)',
  borderColor: '#073642',
  css: '',
  termCSS: '',
  workingDirectory: '',
  showHamburgerMenu: '',
  showWindowControls: '',
  padding: '12px 14px',
  colors: {
    black:    '#002b36',
    red:      '#dc322f',
    green:    '#859900',
    yellow:     '#b58900',
    blue:     '#268bd2',
    magenta:    '#d33682',
    cyan:     '#2aa198',
    white:    '#93a1a1',
    lightBlack:   '#657b83',
    lightRed:   '#cb4b16',
    lightGreen:   '#586e75',
    lightYellow:  '#839496',
    lightBlue:  '#6c71c4',
    lightMagenta: '#d33682',
    lightCyan:  '#2aa198',
    lightWhite:   '#fdf6e3',
  },
  shell: 'C:\\Program Files\\PowerShell\\7\\pwsh.exe',
  shellArgs: ['-NoLogo'],
  env: {},
  bell: 'SOUND',
  copyOnSelect: false,
  defaultSSHApp: true,
  quickEdit: false,
  webGLRenderer: true,
  disableLigatures: true,
  disableAutoUpdates: false,
  preserveCWD: true,
  },
  plugins: [
  'hyper-search',
  'hyper-pane',
  'hypercwd',
  'hyper-tabs-enhanced',
  'hyper-rename-tab',
  'hyper-tab-icons-plus',
  ],
  localPlugins: [],
  keymaps: {
  'tab:rename': 'ctrl+shift+r',
  'tab:new':  'ctrl+shift+t',
  },
};
'@

$HyperDir = "$env:APPDATA\Hyper"
if (-not (Test-Path $HyperDir)) { New-Item -ItemType Directory -Path $HyperDir -Force | Out-Null }
Set-Content -Path "$HyperDir\.hyper.js" -Value $HyperConfig -Encoding UTF8

$DefaultHyperDir = 'C:\Users\Default\AppData\Roaming\Hyper'
if (-not (Test-Path $DefaultHyperDir)) { New-Item -ItemType Directory -Path $DefaultHyperDir -Force | Out-Null }
Set-Content -Path "$DefaultHyperDir\.hyper.js" -Value $HyperConfig -Encoding UTF8

Ok "Hyper config deployed."

# ---------- Stage 22b: Windows Terminal install + config ----------
# Chocolatey package name:  microsoft-windows-terminal
#   Source: https://github.com/microsoft/terminal (official repo README)
#         https://community.chocolatey.org/packages/microsoft-windows-terminal
#
# settings.json path varies by install method (confirmed via MS docs):
#   Store / MSIX install : %LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json
#   Chocolatey (unpackaged) : %LOCALAPPDATA%\Microsoft\Windows Terminal\settings.json
#   Source: https://learn.microsoft.com/en-us/windows/terminal/install
#
# We write to BOTH paths so the config is present regardless of which
# install method ends up active (choco install, Store pre-existing, or later
# Store upgrade). Both dirs are created if absent.
#
# $Profile for PS7 AllUsersAllHosts is already handled in Stage 21.
# The per-user CurrentUserAllHosts profile ($PROFILE) is written here for
# the calling user only, using $PROFILE which PS7 resolves automatically.
# Ref: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_profiles
#
# Font: JetBrainsMono Nerd Font -- already installed system-wide in Stage 20
# via the NerdFonts GitHub release zip. Stage 19 installs the NerdFonts PS
# module (AllUsers) which provides Get-NerdFont / Install-NerdFont, but we
# used the direct zip approach in Stage 20 to avoid requiring pwsh for the
# font install itself. The settings.json references "JetBrainsMono Nerd Font"
# which matches the font family name registered in Stage 20.

Info "Installing Windows Terminal via Chocolatey..."
# choco install exits 0 (already installed) or 0 (freshly installed).
# Exit code 3010 means install succeeded but a reboot is required -- treat as OK.
# Ref: https://docs.chocolatey.org/en-us/choco/commands/install
$chocoResult = & choco install microsoft-windows-terminal -y --no-progress 2>&1
if ($LASTEXITCODE -notin @(0, 3010)) {
  Warn "Windows Terminal choco install returned exit code $LASTEXITCODE -- check output above."
} else {
  Ok "Windows Terminal installed (or already present)."
}

# Build the settings.json content. defaultProfile GUID
# {574e775e-4f2a-5b96-ac1e-a2962a402336} is the PowerShell (Core) profile,
# which matches the source "Windows.Terminal.PowershellCore" dynamic profile.
# Ref: https://learn.microsoft.com/en-us/windows/terminal/dynamic-profiles
$WTSettingsJson = @'
{
  "$help": "https://aka.ms/terminal-documentation",
  "$schema": "https://aka.ms/terminal-profiles-schema",
  "actions": [
    {
      "command": { "action": "copy", "singleLine": false },
      "id": "User.copy.644BA8F2"
    },
    {
      "command": "paste",
      "id": "User.paste"
    },
    {
      "command": { "action": "splitPane", "split": "auto", "splitMode": "duplicate" },
      "id": "User.splitPane.A6751878"
    },
    {
      "command": "find",
      "id": "User.find"
    }
  ],
  "copyFormatting": "none",
  "copyOnSelect": false,
  "defaultProfile": "{574e775e-4f2a-5b96-ac1e-a2962a402336}",
  "keybindings": [
    { "id": "User.copy.644BA8F2",    "keys": "ctrl+c" },
    { "id": "User.paste",            "keys": "ctrl+v" },
    { "id": "User.find",             "keys": "ctrl+shift+f" },
    { "id": "User.splitPane.A6751878", "keys": "alt+shift+d" }
  ],
  "newTabMenu": [
    { "type": "remainingProfiles" }
  ],
  "profiles": {
    "defaults": {
      "font": {
        "face": "JetBrainsMono Nerd Font"
      }
    },
    "list": [
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
        "hidden": false,
        "name": "Azure Cloud Shell",
        "source": "Windows.Terminal.Azure"
      },
      {
        "guid": "{574e775e-4f2a-5b96-ac1e-a2962a402336}",
        "hidden": false,
        "name": "PowerShell",
        "source": "Windows.Terminal.PowershellCore"
      }
    ]
  },
  "schemes": [],
  "themes": []
}
'@

# Path 1: Chocolatey / unpackaged install
# Ref: https://learn.microsoft.com/en-us/windows/terminal/install
$WTChocoDir = "$env:LOCALAPPDATA\Microsoft\Windows Terminal"
if (-not (Test-Path $WTChocoDir)) { New-Item -ItemType Directory -Path $WTChocoDir -Force | Out-Null }
Set-Content -Path "$WTChocoDir\settings.json" -Value $WTSettingsJson -Encoding UTF8

# Path 2: Store / MSIX install (pre-seeded for current user)
# Ref: https://learn.microsoft.com/en-us/windows/terminal/install
$WTStoreDir = "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState"
if (-not (Test-Path $WTStoreDir)) { New-Item -ItemType Directory -Path $WTStoreDir -Force | Out-Null }
Set-Content -Path "$WTStoreDir\settings.json" -Value $WTSettingsJson -Encoding UTF8

Ok "Windows Terminal settings.json written to both Chocolatey and Store paths."

# Also pre-seed the Default user profile so any new user created after
# bootstrap gets the config automatically on first login.
# Only the Store path is worth pre-seeding here -- the choco path is per-user
# and would need a logon script for new users anyway.
$WTDefaultStoreDir = "C:\Users\Default\AppData\Local\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState"
if (-not (Test-Path $WTDefaultStoreDir)) { New-Item -ItemType Directory -Path $WTDefaultStoreDir -Force | Out-Null }
Set-Content -Path "$WTDefaultStoreDir\settings.json" -Value $WTSettingsJson -Encoding UTF8
Ok "Windows Terminal settings.json pre-seeded into Default user profile."

# Per-user PS7 profile (CurrentUserAllHosts) for the calling user.
# $PROFILE here is the PS5 profile path; we want the PS7 equivalent which
# lives at Documents\PowerShell\profile.ps1 regardless of PS version.
# Ref: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_profiles
$UserPS7ProfileDir = "$([Environment]::GetFolderPath('MyDocuments'))\PowerShell"
$UserPS7Profile    = "$UserPS7ProfileDir\profile.ps1"
if (-not (Test-Path $UserPS7ProfileDir)) { New-Item -ItemType Directory -Path $UserPS7ProfileDir -Force | Out-Null }

# PSWriteColor, Terminal-Icons, PSReadLine already installed AllUsers in Stage 19.
# PredictionSource HistoryAndPlugin requires PSReadLine 2.2+ and PS7.2+.
# PredictionViewStyle ListView is the multi-line suggestion list view.
# Ref: https://learn.microsoft.com/en-us/powershell/module/psreadline/set-psreadlineoption
$UserProfileContent = @'
# Example Music -- PS7 per-user profile
# Written by PostOOBE bootstrap (Stage 22b)

# Enable Terminal-Icons (requires Nerd Font -- installed system-wide in Stage 20)
Import-Module PSWriteColor
Import-Module Terminal-Icons
Set-PSReadLineOption -PredictionSource HistoryAndPlugin
Set-PSReadLineOption -PredictionViewStyle ListView
'@

if (-not (Test-Path $UserPS7Profile)) {
  Set-Content -Path $UserPS7Profile -Value $UserProfileContent -Encoding UTF8
  Ok "PS7 per-user profile written to $UserPS7Profile"
} else {
  $existing = Get-Content $UserPS7Profile -Raw
  if ($existing -notmatch 'Example Music') {
    Add-Content -Path $UserPS7Profile -Value ("`n" + $UserProfileContent) -Encoding UTF8
    Ok "PS7 per-user profile updated at $UserPS7Profile"
  } else {
    Ok "PS7 per-user profile already contains Example Music block -- skipped."
  }
}

# ---------- Stage 23: Finish ----------
# Print a quick summary of remote access methods available on this VM
Write-Host ""
Write-Host "  [+] Remote Access Summary" -ForegroundColor Green
Write-Host "  ──────────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  SSH (Ansible/admin) : port 22 -- key auth, PS7 default shell" -ForegroundColor Gray
Write-Host "  RDP                 : port 3389 -- NLA enforced" -ForegroundColor Gray
if ($HasCOM1 -and $ConfigureEMS) {
  Write-Host "  SAC / SOL           : ipmitool sol activate -> SAC> cmd -> powershell" -ForegroundColor Gray
  Write-Host "  Boot menu on serial : COM1 115200 8N1 -- select entries over SOL" -ForegroundColor Gray
} else {
  Write-Host "  SAC / SOL           : not configured (no COM1 or skipped)" -ForegroundColor DarkGray
}
Write-Host "  ──────────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""
New-Item -ItemType File -Path $Marker -Force | Out-Null
Warn "Bootstrap complete. Rebooting in 20 seconds."
Start-Sleep 20
Restart-Computer -Force
