<#
ipcalc.ps1 - PowerShell IP Calculator

Version History
---------------
v1.0    Initial IPv4 ipcalc clone
v1.1    Added subnet splitting
v1.2    Solarized Dark/Light themes
v1.3    IPv6 support + CIDR summarisation + pipe input
v1.3.1  Fixed /0–/32 edge cases, pipeline array handling
v1.3.2  Fully patched UInt32 shift & IP parsing issues

Usage Examples
--------------

# IPv4 CIDR
.\ipcalc.ps1 192.168.10.15/24

# IPv4 with mask
.\ipcalc.ps1 10.0.5.3 255.255.252.0

# Split network
.\ipcalc.ps1 192.168.1.0/24 -Split -NewPrefix 26

# Summarise multiple networks
.\ipcalc.ps1 -Summary 192.168.1.0/24 192.168.2.0/24

# IPv6
.\ipcalc.ps1 2001:db8::1/64

# Pipe mode
"192.168.10.10/24","10.0.0.5/22" | .\ipcalc.ps1

Theme
-----
Default: Solarized Dark
Switch:  -Theme Light
#>

param(
    [Parameter(Position=0, ValueFromPipeline=$true)]
    [string[]]$IP,

    [Parameter(Position=1)]
    [string]$Mask,

    [switch]$Split,
    [int]$NewPrefix,
    [switch]$Summary,

    [ValidateSet("Dark","Light")]
    [string]$Theme="Dark"
)

# Solarized palette
$Colors = @{
  Dark=@{Label="Cyan"; Value="White"; Warn="Yellow"; Accent="Magenta"; Good="Green"; Bad="Red"; Dim="Gray"}
  Light=@{Label="DarkCyan"; Value="Black"; Warn="DarkYellow"; Accent="DarkMagenta"; Good="DarkGreen"; Bad="DarkRed"; Dim="DarkGray"}
}
$C=$Colors[$Theme]

# ---------- Utility ----------
function IPToInt($ip){
  $ip = [string]$ip
  $b = ([System.Net.IPAddress]$ip).GetAddressBytes()
  [array]::Reverse($b)
  [BitConverter]::ToUInt32($b,0)
}

function IntToIP($int){
  $b = [BitConverter]::GetBytes([uint32]$int)
  [array]::Reverse($b)
  ([System.Net.IPAddress]$b).ToString()
}

function PrefixToMask($p){
  $p = [int]$p
  if ($p -lt 0 -or $p -gt 32) { throw "Invalid prefix $p" }
  if ($p -eq 0) { $m = 0 }
  else { $m = [uint32]([math]::Pow(2,32)-1) -bxor ([math]::Pow(2,32-$p)-1) }
  IntToIP $m
}

function MaskToPrefix($mask){ ($mask.Split('.') | % { [Convert]::ToString([int]$_,2) }) -join '' -replace '0','' | % Length }

function BinaryIP($ip){ ($ip.Split('.') | % { [Convert]::ToString([int]$_,2).PadLeft(8,'0') }) -join '.' }

function PrintIPv4($ip,$mask){
  $ipInt     = IPToInt $ip
  $maskInt   = IPToInt $mask
  $netInt    = $ipInt -band $maskInt
  $bcInt     = $netInt -bor (-bnot $maskInt)
  $network   = IntToIP $netInt
  $broadcast = IntToIP $bcInt
  $first     = if (($bcInt - $netInt) -ge 2) { IntToIP ($netInt + 1) } else {"N/A"}
  $last      = if (($bcInt - $netInt) -ge 2) { IntToIP ($bcInt - 1) } else {"N/A"}
  $prefix    = MaskToPrefix $mask
  $hosts     = if ($prefix -eq 32) {1} elseif ($prefix -eq 31) {2} else {[math]::Pow(2,(32-$prefix))-2}
  $wild      = IntToIP (-bnot $maskInt)

  Write-Host
  Write-Host "Address:  " -ForegroundColor $C.Label -NoNewline
  Write-Host $ip -ForegroundColor $C.Value
  Write-Host "Netmask:  " -ForegroundColor $C.Label -NoNewline
  Write-Host "$mask = $prefix" -ForegroundColor $C.Warn
  Write-Host "Wildcard: " -ForegroundColor $C.Label -NoNewline
  Write-Host $wild -ForegroundColor $C.Warn
  Write-Host "Network:  " -ForegroundColor $C.Label -NoNewline
  Write-Host "$network/$prefix" -ForegroundColor $C.Good
  Write-Host "Broadcast:" -ForegroundColor $C.Label -NoNewline
  Write-Host $broadcast -ForegroundColor $C.Bad
  Write-Host "HostMin:  " -ForegroundColor $C.Label -NoNewline
  Write-Host $first -ForegroundColor $C.Value
  Write-Host "HostMax:  " -ForegroundColor $C.Label -NoNewline
  Write-Host $last -ForegroundColor $C.Value
  Write-Host "Hosts/Net:" -ForegroundColor $C.Label -NoNewline
  Write-Host $hosts -ForegroundColor $C.Accent
  Write-Host
  Write-Host "Binary:"
  Write-Host "IP:      $(BinaryIP $ip)"
  Write-Host "Netmask: $(BinaryIP $mask)"
}

function PrintIPv6($ip){
  $addr = [System.Net.IPAddress]$ip
  Write-Host
  Write-Host "IPv6 Address:" -ForegroundColor $C.Label -NoNewline
  Write-Host " $ip" -ForegroundColor $C.Value
  $ipv6Type = switch($addr.GetAddressBytes()[0]){
    {$_ -eq 0xfe}{"Link Local"}
    {$_ -eq 0xfc}{"ULA"}
    {$_ -eq 0xff}{"Multicast"}
    default {"Global"}
  }
  Write-Host "Type:      " -ForegroundColor $C.Label -NoNewline
  Write-Host "$ipv6Type" -ForegroundColor $C.Accent
}

function Summarise($nets){
  $ints=@()
  foreach($n in $nets){
    $parts = $n -split "/"
    $ip    = $parts[0]
    $ints += IPToInt $ip
  }
  $min     = [array]::Min($ints)
  $max     = [array]::Max($ints)
  $diff    = $min -bxor $max
  $prefix  = 32
  while ($diff -gt 0){ $diff = $diff -shr 1; $prefix-- }
  $mask    = PrefixToMask $prefix
  $network = IntToIP ($min -band (IPToInt $mask))
  Write-Host
  Write-Host "Summary Network:" -ForegroundColor $C.Label -NoNewline
  Write-Host " $network/$prefix" -ForegroundColor $C.Good
}

# ---------- Main ----------
if ($Summary) { Summarise $IP; return }
foreach ($entry in $IP){
  $entry = [string]$entry
  if ($entry -match ":") { PrintIPv6 $entry; continue }
    if ($entry -match "/"){
      $parts = $entry.Split("/")
      $ip    = $parts[0]
      $p     = [int]$parts[1]
      $mask  = PrefixToMask $p
    } else { $ip=$entry; $mask=$Mask }
    PrintIPv4 $ip $mask

    if ($Split){
      $prefix = MaskToPrefix $mask
      $count  = [math]::Pow(2,$NewPrefix-$prefix)
      $size   = [math]::Pow(2,32-$NewPrefix)
      $start  = (IPToInt $ip) -band (IPToInt $mask)
      Write-Host
      Write-Host "Subnets (/ $NewPrefix)" -ForegroundColor $C.Label
      for ($i=0; $i -lt $count; $i++){
        $n = IntToIP ($start + ($i*$size))
        Write-Host "$n/$NewPrefix"
      }
  }
}
