
#=============================================================================
# Export-ADInventory.ps1
# Export the complete Active Directory domain hierarchy and object inventory
#=============================================================================

Import-Module ActiveDirectory -ErrorAction Stop

$Domain = Get-ADDomain
$Server = $Domain.PDCEmulator
$BaseDN = $Domain.DistinguishedName
$OutDir = Join-Path $PWD "AD-Inventory"

New-Item -Path $OutDir -ItemType Directory -Force | Out-Null

Write-Host "Domain : $($Domain.DNSRoot)" -ForegroundColor Cyan
Write-Host "DC     : $Server" -ForegroundColor Cyan
Write-Host "Search : $BaseDN" -ForegroundColor Cyan

#-----------------------------------------------------------------------------
# Retrieve every live object in the domain naming context
#-----------------------------------------------------------------------------

Write-Host "`nQuerying Active Directory..." -ForegroundColor Cyan

$Properties = @(
  'objectClass'
  'objectGUID'
  'objectSid'
  'sAMAccountName'
  'userPrincipalName'
  'canonicalName'
  'whenCreated'
  'whenChanged'
  'description'
  'adminCount'
  'isCriticalSystemObject'
)

$Objects = @(Get-ADObject -Server $Server -SearchBase $BaseDN -SearchScope Subtree -LDAPFilter '(objectClass=*)' -Properties $Properties -ResultPageSize 1000 -ResultSetSize $null)
Write-Host "Retrieved $($Objects.Count) objects." -ForegroundColor Green

#-----------------------------------------------------------------------------
# Build an inventory indexed by distinguished name
#-----------------------------------------------------------------------------

$ObjectMap = @{}

foreach ($Object in $Objects) { $ObjectMap[$Object.DistinguishedName] = $Object }

# Find the parent DN by locating the first unescaped comma. This handles common escaped commas in LDAP distinguished names.
function Get-ParentDN {
  param([string]$DN)

  $Backslashes = 0

  for ($i = 0; $i -lt $DN.Length; $i++) {
    $Char = $DN[$i]

    if ($Char -eq '\') {
      $Backslashes++
      continue
    }
    if ($Char -eq ',' -and ($Backslashes % 2) -eq 0) {
      return $DN.Substring($i + 1)
    }

    $Backslashes = 0
  }
  return $null
}

#-----------------------------------------------------------------------------
# Generate CSV records and build the tree's parent-child index
#-----------------------------------------------------------------------------

$Rows = [System.Collections.Generic.List[object]]::new()
$Children = @{}

foreach ($Object in $Objects) {
  $DN       = $Object.DistinguishedName
  $ParentDN = Get-ParentDN -DN $DN
  $Class    = @($Object.ObjectClass)[-1]
  $SID = if ($Object.ObjectSid) { $Object.ObjectSid.Value }
         else { '' }
  $Name = if ($Object.Name) { $Object.Name }
          else { $DN }

  $Rows.Add([PSCustomObject]@{
    Name                  = $Name
    ObjectClass           = $Class
    DistinguishedName     = $DN
    ParentDN              = $ParentDN
    CanonicalName         = $Object.CanonicalName
    SamAccountName        = $Object.SamAccountName
    UserPrincipalName     = $Object.UserPrincipalName
    ObjectGUID            = $Object.ObjectGUID
    ObjectSID             = $SID
    Description           = $Object.Description
    WhenCreated           = $Object.WhenCreated
    WhenChanged           = $Object.WhenChanged
    AdminCount            = $Object.adminCount
    IsCriticalSystemObject = $Object.isCriticalSystemObject
  })

  if (-not $Children.ContainsKey($ParentDN)) { $Children[$ParentDN] = [System.Collections.Generic.List[object]]::new() }
  $Children[$ParentDN].Add($Object)
}

#-----------------------------------------------------------------------------
# Write the full hierarchy
#-----------------------------------------------------------------------------

$TreeFile = Join-Path $OutDir 'AD-Tree.txt'
$CsvFile  = Join-Path $OutDir 'AD-Objects.csv'
$Lines    = [System.Collections.Generic.List[string]]::new()

$Lines.Add($Domain.DNSRoot)
$Lines.Add("|")

function Write-ADTree {
  param(
    [string]$ParentDN,
    [string]$Prefix = ''
  )

  if (-not $Children.ContainsKey($ParentDN)) { return }
  $Sorted = @( $Children[$ParentDN] | Sort-Object Name, ObjectClass, DistinguishedName )

  for ($i = 0; $i -lt $Sorted.Count; $i++) {
    $Object = $Sorted[$i]
    $Last   = ($i -eq ($Sorted.Count - 1))
    if ($Last) {
      $Branch = '\-- '
      $NextPrefix = "$Prefix    "
      }
    else {
      $Branch = '+-- '
      $NextPrefix = "$Prefix|   "
      }
    $Class = @($Object.ObjectClass)[-1]
    $Lines.Add( "$Prefix$Branch$($Object.Name) [$Class]" )

    Write-ADTree -ParentDN $Object.DistinguishedName -Prefix $NextPrefix
  }
}

# Start at the domain root. This includes default CN containers,
# OUs, and every descendant object returned by the LDAP query.

Write-ADTree -ParentDN $BaseDN

$Lines | Set-Content -Path $TreeFile -Encoding utf8

#-----------------------------------------------------------------------------
# Write the full object inventory
#-----------------------------------------------------------------------------

$Rows | Sort-Object CanonicalName, DistinguishedName | Export-Csv -Path $CsvFile -NoTypeInformation -Encoding utf8

#-----------------------------------------------------------------------------
# Summary
#-----------------------------------------------------------------------------

Write-Host "`nExport complete." -ForegroundColor Green
Write-Host "Tree    : $TreeFile"
Write-Host "CSV     : $CsvFile"
Write-Host "Objects : $($Rows.Count)"

Write-Host "`nObject classes:" -ForegroundColor Cyan

$Rows | Group-Object ObjectClass | Sort-Object Count -Descending | Format-Table Count, Name -AutoSize
