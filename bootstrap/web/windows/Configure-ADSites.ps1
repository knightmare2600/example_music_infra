<#
.SYNOPSIS
  Configure AD Sites, Subnets and Site Links for jukebox.internal

.DESCRIPTION
  Creates AD replication sites, LAN and VPN subnets, and site links
  that mirror the WireGuard hub topology. Idempotent — skips objects
  that already exist. Use -WhatIf to preview without making changes.

  Topology:
    FAL = UK head office hub (UK sites connect here)
    ODE = EU hub       (EU sites connect here; ODE links to FAL)
    BRK = NA hub       (NA/Pacific sites connect here; BRK links to FAL)
    CPH = permanent site DC  (direct link to FAL, cost 10)

.PARAMETER Sites
  Optional subset of site codes to process. Default = all.

.PARAMETER MoveDCs
  After creating sites, move each DC into its correct site.
  Silently skips DCs that do not yet exist in AD.

.NOTES
  Document : NET-AD-DC-001 Phase 7
  Run on   : EXADCSFAL001
  Requires : ActiveDirectory PowerShell module
#>

[CmdletBinding(SupportsShouldProcess)]
param(
  [string[]] $Sites   = @(),
  [switch]   $MoveDCs
)

Import-Module ActiveDirectory -ErrorAction Stop

## =============================================================================
## SITE DATA TABLE
##
## Subnets (LAN/VPN) are loaded from sites.csv (single source of truth).
## sites.csv must be in the same directory as this script.
##
## Hub topology (Hub, Cost, Freq, DCs) is AD-specific and remains here.
## When a new site is added to sites.csv, add a topology row below to
## define its hub, replication cost, and DC hostnames.
##
## Hub   = parent hub site ($null = this is a hub -- see $HubLinks)
## Cost  = AD replication site link cost (lower = preferred)
## Freq  = replication frequency in minutes
## DCs   = DC hostnames used by -MoveDCs
## =============================================================================

## ── Load subnets from sites.csv ───────────────────────────────────────────────
$ScriptDir = Split-Path $PSCommandPath -Parent
$CsvPath   = Join-Path $ScriptDir 'sites.csv'

if (-not (Test-Path $CsvPath)) {
  Write-Warning "sites.csv not found at $CsvPath -- subnet data will be missing."
  Write-Warning "Place sites.csv alongside this script on the DeployTools share."
  $SiteSubnets = @{}
} else {
  $SiteSubnets = @{}
  Import-Csv $CsvPath | ForEach-Object {
    $code   = $_.Site.Trim().ToUpper()
    $subnet = $_.Subnet.Trim()
    if ($code -and $subnet -and $subnet -ne 'N/A') {
      $octet = $subnet.Split('.')[2]
      $SiteSubnets[$code] = @{
        LAN = $subnet
        VPN = "10.0.$octet.0/24"
      }
    }
  }
  Write-Host "  Subnets loaded from sites.csv ($($SiteSubnets.Count) sites)" -ForegroundColor DarkGray
}

## ── Topology table -- hub/cost/freq/DCs (AD-specific, not in sites.csv) ───────
## Subnets are filled in from $SiteSubnets above.
## TBC entries: sites in sites.csv that don't have a topology row yet will
## have their subnets created but no site link (they need a topology row first).

$SiteTopology = [ordered]@{
  ## ── Hubs ──────────────────────────────────────────────────────────────────
  FAL = @{ Hub=$null; Cost=$null; Freq=$null; DCs=@("EXADCSFAL001","EXADCSFAL002") }
  ODE = @{ Hub=$null; Cost=$null; Freq=$null; DCs=@("EXADCSODE001") }
  BRK = @{ Hub=$null; Cost=$null; Freq=$null; DCs=@("EXADCSBRK001") }

  ## ── CPH -- direct to FAL ──────────────────────────────────────────────────
  CPH = @{ Hub="FAL"; Cost=10; Freq=15; DCs=@("EXADCSCPH001") }

  ## ── UK sites -- connect via FAL ───────────────────────────────────────────
  EDI = @{ Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSEDI001") }
  GLA = @{ Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSGLA001") }
  ABD = @{ Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSABD001") }
  MCR = @{ Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSMCR001") }
  LND = @{ Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSLND001") }
  BIR = @{ Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSBIR001") }
  LIV = @{ Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSLIV001") }
  NEW = @{ Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSNEW001") }
  SHE = @{ Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSSHE001") }
  HUL = @{ Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSHUL001") }
  COV = @{ Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSCOV001") }
  HAL = @{ Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSHAL001") }
  CLY = @{ Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSCLY001") }
  DUN = @{ Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSDUN001") }
  PER = @{ Hub="FAL"; Cost=25; Freq=15; DCs=@("EXADCSPER001") }

  ## ── EU sites -- connect via ODE ───────────────────────────────────────────
  MUN = @{ Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSMUN001") }
  BON = @{ Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSBON001") }
  BER = @{ Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSBER001") }
  OSL = @{ Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSOSL001") }
  GOT = @{ Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSGOT001") }
  MIL = @{ Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSMIL001") }
  AMS = @{ Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSAMS001") }
  VIE = @{ Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSVIE001") }
  FAX = @{ Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSFAX001") }
  KGE = @{ Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSKGE001") }
  KOR = @{ Hub="ODE"; Cost=25; Freq=15; DCs=@("EXADCSKOR001") }

  ## ── NA sites -- connect via BRK ───────────────────────────────────────────
  TOR = @{ Hub="BRK"; Cost=25; Freq=30; DCs=@("EXADCSTOR001") }
  MTL = @{ Hub="BRK"; Cost=25; Freq=30; DCs=@("EXADCSMTL001") }
  NYC = @{ Hub="BRK"; Cost=25; Freq=30; DCs=@("EXADCSNYC001") }
  LAX = @{ Hub="BRK"; Cost=25; Freq=30; DCs=@("EXADCSLAX001") }
  MIA = @{ Hub="BRK"; Cost=25; Freq=30; DCs=@("EXADCSMIA001") }
  NJC = @{ Hub="BRK"; Cost=25; Freq=30; DCs=@("EXADCSNJC001") }
  ATL = @{ Hub="BRK"; Cost=25; Freq=30; DCs=@("EXADCSATL001") }
  CHI = @{ Hub="BRK"; Cost=25; Freq=30; DCs=@("EXADCSCHI001") }

  ## ── Pacific -- connect via BRK ────────────────────────────────────────────
  SYD = @{ Hub="BRK"; Cost=50; Freq=30; DCs=@("EXADCSSYD001") }
  MEL = @{ Hub="BRK"; Cost=50; Freq=30; DCs=@("EXADCSMEL001") }
  AKL = @{ Hub="BRK"; Cost=50; Freq=30; DCs=@("EXADCSAKL001") }
}

## ── Merge subnets into topology to produce $SiteData ─────────────────────────
$SiteData = [ordered]@{}
foreach ($code in $SiteTopology.Keys) {
  $topo   = $SiteTopology[$code]
  $subnet = $SiteSubnets[$code]
  if (-not $subnet) {
    Write-Warning "No subnet in sites.csv for site '$code' -- site will be created without subnet."
    $lan = 'MISSING'
    $vpn = 'MISSING'
  } else {
    $lan = $subnet.LAN
    $vpn = $subnet.VPN
  }
  $SiteData[$code] = @{
    LAN  = $lan
    VPN  = $vpn
    Hub  = $topo.Hub
    Cost = $topo.Cost
    Freq = $topo.Freq
    DCs  = $topo.DCs
  }
}

## Hub-to-hub links (different costs from spoke links)
$HubLinks = @(
  @{ Name="FAL-CPH"; Sites=@("FAL","CPH"); Cost=10;  Freq=15 }
  @{ Name="FAL-ODE"; Sites=@("FAL","ODE"); Cost=50;  Freq=15 }
  @{ Name="FAL-BRK"; Sites=@("FAL","BRK"); Cost=100; Freq=30 }
)

## ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Action { param([string]$A,[string]$O,[switch]$W)
  if($W){ Write-Host "  [WhatIf] Would $A : $O" -ForegroundColor Cyan }
  else  { Write-Host "  [+] $A : $O" -ForegroundColor Green } }
function Write-Skip { param([string]$O) Write-Host "  [=] Exists: $O" -ForegroundColor DarkGray }
function Write-Warn { param([string]$M) Write-Host "  [!] $M" -ForegroundColor Yellow }
function Exists-Site   { param([string]$N) try{Get-ADReplicationSite  -Identity $N -EA Stop|Out-Null;$true}catch{$false} }
function Exists-Subnet { param([string]$N) try{Get-ADReplicationSubnet  -Identity $N -EA Stop|Out-Null;$true}catch{$false} }
function Exists-Link   { param([string]$N) try{Get-ADReplicationSiteLink -Identity $N -EA Stop|Out-Null;$true}catch{$false} }

## ── Filter to requested sites ─────────────────────────────────────────────────
if($Sites.Count -gt 0){
  $f=[ordered]@{}
  foreach($s in $Sites){ if($SiteData.Contains($s)){$f[$s]=$SiteData[$s]}else{Write-Warn "Unknown site: $s"} }
  $SiteData=$f
}

## ── Step 1: Remove default site link ─────────────────────────────────────────
Write-Host "`n--- Step 1: Default Site Link ---" -FG White
if(Exists-Link "DEFAULTIPSITELINK"){
  if($PSCmdlet.ShouldProcess("DEFAULTIPSITELINK","Remove")){
    Remove-ADReplicationSiteLink -Identity "DEFAULTIPSITELINK" -Confirm:$false
    Write-Action "Removed" "DEFAULTIPSITELINK"
  }
} else { Write-Skip "DEFAULTIPSITELINK (already removed)" }

## ── Step 2: Sites ─────────────────────────────────────────────────────────────
Write-Host "`n--- Step 2: Sites ---" -FG White
foreach($e in $SiteData.GetEnumerator()){
  if(Exists-Site $e.Key){ Write-Skip "Site: $($e.Key)" }
  else{
    if($PSCmdlet.ShouldProcess($e.Key,"New-ADReplicationSite")){
      New-ADReplicationSite -Name $e.Key; Write-Action "Created site" $e.Key
    } else { Write-Action "Created site" $e.Key -W }
  }
}

## ── Step 3: Subnets ───────────────────────────────────────────────────────────
Write-Host "`n--- Step 3: Subnets ---" -FG White
foreach($e in $SiteData.GetEnumerator()){
  foreach($subnet in @($e.Value.LAN,$e.Value.VPN)){
    if($subnet -match "TBC"){ Write-Warn "TBC subnet for $($e.Key) — fill octet first: $subnet"; continue }
    if(Exists-Subnet $subnet){ Write-Skip "Subnet: $subnet" }
    else{
      if($PSCmdlet.ShouldProcess($subnet,"New-ADReplicationSubnet")){
        New-ADReplicationSubnet -Name $subnet -Site $e.Key
        Write-Action "Created subnet" "$subnet → $($e.Key)"
      } else { Write-Action "Created subnet" "$subnet → $($e.Key)" -W }
    }
  }
}

## ── Step 4: Spoke links ───────────────────────────────────────────────────────
Write-Host "`n--- Step 4: Spoke Site Links ---" -FG White
foreach($e in $SiteData.GetEnumerator()){
  if($null -eq $e.Value.Hub){ continue }
  $ln = "$($e.Value.Hub)-$($e.Key)"
  if(Exists-Link $ln){ Write-Skip "Link: $ln" }
  else{
    if($PSCmdlet.ShouldProcess($ln,"New-ADReplicationSiteLink")){
      New-ADReplicationSiteLink -Name $ln -SitesIncluded @($e.Value.Hub,$e.Key) `
        -Cost $e.Value.Cost -ReplicationFrequencyInMinutes $e.Value.Freq
      Write-Action "Created link" "$ln (cost=$($e.Value.Cost) freq=$($e.Value.Freq)min)"
    } else { Write-Action "Created link" "$ln (cost=$($e.Value.Cost) freq=$($e.Value.Freq)min)" -W }
  }
}

## ── Step 5: Hub-to-hub links ──────────────────────────────────────────────────
Write-Host "`n--- Step 5: Hub Links ---" -FG White
foreach($link in $HubLinks){
  if(Exists-Link $link.Name){ Write-Skip "Hub link: $($link.Name)" }
  else{
    if($PSCmdlet.ShouldProcess($link.Name,"New-ADReplicationSiteLink (hub)")){
      New-ADReplicationSiteLink -Name $link.Name -SitesIncluded $link.Sites `
        -Cost $link.Cost -ReplicationFrequencyInMinutes $link.Freq
      Write-Action "Created hub link" "$($link.Name) (cost=$($link.Cost) freq=$($link.Freq)min)"
    } else { Write-Action "Created hub link" "$($link.Name)" -W }
  }
}

## ── Step 6: Move DCs (optional) ───────────────────────────────────────────────
if($MoveDCs){
  Write-Host "`n--- Step 6: Moving DCs ---" -FG White
  foreach($e in $SiteData.GetEnumerator()){
    foreach($dc in $e.Value.DCs){
      try{
        $obj=Get-ADDomainController -Identity $dc -EA Stop
        if($obj.Site -eq $e.Key){ Write-Skip "$dc already in $($e.Key)" }
        else{
          if($PSCmdlet.ShouldProcess($dc,"Move → $($e.Key)")){
            Move-ADDirectoryServer -Identity $dc -Site $e.Key
            Write-Action "Moved" "$dc : $($obj.Site) → $($e.Key)"
          } else { Write-Action "Moved" "$dc → $($e.Key)" -W }
        }
      } catch { Write-Warn "DC '$dc' not found — promote it first" }
    }
  }
}

## ── Summary ───────────────────────────────────────────────────────────────────
Write-Host "`n--- Summary ---" -ForegroundColor White
Write-Host "  Sites   : $((Get-ADReplicationSite  -Filter * | Measure-Object).Count)"
Write-Host "  Subnets : $((Get-ADReplicationSubnet  -Filter * | Measure-Object).Count)"
Write-Host "  Links   : $((Get-ADReplicationSiteLink -Filter * | Measure-Object).Count)"
Write-Host "`n  Next steps:"
Write-Host "  1. Run with -MoveDCs once all Phase 6 DCs are promoted"
Write-Host "  2. repadmin /syncall /AdeP"
Write-Host "  3. Get-ADDomainController -Filter * | Select Name,Site,IsGlobalCatalog"