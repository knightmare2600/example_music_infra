# Example Music Limited — UPN Suffixes, Internal DNS Zones & DHCP Dynamic DNS

> **Classification:** Internal — Infrastructure
> **Forest / AD Domain:** `jukebox.internal` (single domain — all machines join here)
> **UPN suffixes / internal DNS zones:** `example.net` · `example.org` · `example.com`
> **Provisioning network:** `192.168.139.0/24`
> **Credentials:** See password manager — do **not** store passwords in this document

> **Architecture note:** `example.net`, `example.org`, and `example.com` are **not** Active Directory child domains. They exist in this infrastructure as (a) UPN suffixes so users can log in with email-format credentials, and (b) internal DNS zones so these names resolve to internal services rather than their real public owners. All machines — servers, workstations, and DCs — join `jukebox.internal` directly.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-08 | Initial document — UPN suffixes, internal DNS zones, per-site reverse zones, dnsmasq DHCP dynamic DNS |
| 2026-03-14 | Clarified that example.* are UPN suffixes / DNS zones only, not AD child domains. Added DNS zone pre-creation requirement before domain join. Updated EXADCSODE001 status. ODE reverse zone created and verified. |
| 2026-03-14 | PSReadLine paste fix documented (SSH over PuTTY/pwsh). |

---

## Standard IP Convention

Every site follows this addressing scheme within its `/24` subnet.
Exceptions are noted in individual site entries.

| Address | Role | Hostname pattern |
|---------|------|-----------------|
| `.1` | Primary internet gateway | `EXAFWL<SITE>001` / `EXARTR<SITE>001` |
| `.2` | BMC pool slot 1 — DRAC / iLO | `EXARAC<SITE>001` |
| `.3` | BMC pool slot 2 — or RAC emulator VM on single-PVE-node sites | `EXARAC<SITE>002` |
| `.4` | BMC pool slot 3 — or RAC emulator VM on two-PVE-node sites | `EXARAC<SITE>003` |
| `.5` | PVE node 1 | `EXAPVE<SITE>001` |
| `.6` | PVE node 2 | `EXAPVE<SITE>002` |
| `.7` | PVE node 3 | `EXAPVE<SITE>003` |
| `.10` | Domain Controller — primary | `EXADCS<SITE>001` |
| `.11` | Domain Controller — secondary | `EXADCS<SITE>002` |
| `.48` | VOIP SBC — trunks to `EXACLDPBX001` | `EXASBC<SITE>001` |
| `.100`–`.249` | DHCP pool | — |
| `.250`–`.252` | RT switches | `EXASWI<SITE>001`–`003` |
| `.253` | Secondary internet gateway / dnsmasq DHCP+DNS node | `EXAFWL<SITE>001` |

> **BMC pool:** `.2`/`.3`/`.4` are shared between physical DRAC/iLO interfaces and the RAC emulator VM. Physical PVE node BMCs consume from `.2` upward; the RAC VM (`EXARAC<SITE>00N`) takes the next free slot.
>
> ***NB: On three-PVE-node sites the pool is fully consumed by physical BMCs.***

---

## 1. Overview

This procedure covers three related but distinct configurations that together allow users and devices across the Example Music estate to authenticate and resolve DNS correctly:

**Part A — UPN Suffixes**
Adds `example.com`, `example.org`, and `example.net` as alternative User Principal Name (UPN) suffixes to the `jukebox.internal` forest. This allows AD user accounts to have a login name matching their email address (e.g. `j.smith@example.com`) rather than the internal forest name (`j.smith@jukebox.internal`). A user logging in from any site — including visiting another country's office — will authenticate successfully with their email-format UPN.

**Part B — Internal DNS Zones**
Creates AD-integrated DNS zones for `example.com`, `example.org`, and `example.net` on all domain controllers. These are **internal-only** zones — they are not authoritative for public DNS and do not affect external resolution. They exist so that internal services (e.g. `provisioning.example.com`) resolve correctly on the estate. All zones replicate forest-wide automatically via AD replication, so a record added on any DC is visible on all DCs within the normal AD replication interval.

> **Important dependency:** These zones must be created on the primary DC **before** any machine attempts to join `jukebox.internal` with a UPN or service referencing `example.net/org/com`. If the zones do not exist, Windows DNS forwards these queries to the public internet, resolves them to Cloudflare/IANA addresses, and domain join or authentication operations fail. The AD domain join itself (to `jukebox.internal`) does not require these zones — but any post-join operations referencing the example.* names do.

**Part C — Per-Site Reverse DNS Zones**
Creates a `*.168.192.in-addr.arpa` reverse lookup zone on each site's primary DC, scoped to that site's `/24` subnet. All reverse zones replicate forest-wide, so PTR lookups for any site's devices succeed from any DC on the estate. The provisioning network reverse zone (`139.168.192.in-addr.arpa`) is hosted on `EXADCSCLD001`.

**Part D — dnsmasq DHCP and Dynamic DNS Updates**
Configures the `EXAFWL???001` firewall nodes (Debian Trixie, running dnsmasq at `.253`) to:
- Serve DHCP leases to site devices
- Maintain a local dnsmasq DNS cache for the site
- Send dynamic DNS updates (`nsupdate`) to the local DC (`.10`) whenever a DHCP lease is issued, updating both A and PTR records in Windows DNS
- Forward DNS queries for zones it does not own to the local DC

---

## 2. Scope

### 2.1 In Scope

- UPN suffix registration for `example.com`, `example.org`, `example.net` on the `jukebox.internal` forest
- AD-integrated forward DNS zones for all three domains, forest-wide replication
- Initial DNS records: `provisioning.*` A records in all three zones
- Per-site `/24` reverse zones on each site's primary DC, forest-wide replication
- PTR record for `EXAPROVCLD001` (`192.168.139.50`) in the CLD reverse zone
- Windows DNS dynamic update permissions — non-secure, restricted to `.253` per site
- dnsmasq configuration: DHCP, local DNS, DNS forwarding to DC, `nsupdate` dynamic update script
- Verification of forest-wide replication for all zones

### 2.2 Out of Scope

- TSIG / DNSSEC / DNS security hardening (future phase)
- Public DNS delegation or external zone hosting
- Email routing or MX record configuration
- AD user account creation or UPN assignment to existing users (separate procedure)
- CLD site DC and reverse zone (pending — see reminder at end of document)

---

## 3. Infrastructure Reference

### 3.1 Key Servers

| Hostname | IP | Site | Role in this procedure |
|----------|----|------|----------------------|
| `EXADCSFAL001` | `192.168.76.10` | FAL | Primary DC — run forest-wide config from here |
| `EXADCSCLD001` | `192.168.139.8` | CLD | Hosts `139.168.192.in-addr.arpa` and provisioning records |
| `EXAPROVCLD001` | `192.168.139.50` | CLD | Provisioning web server — DNS target for `provisioning.*` |
| `EXAFWL<SITE>001` | `192.168.<SITE>.253` | All | dnsmasq DHCP+DNS, sends nsupdate to DC |
| `EXADCS<SITE>001` | `192.168.<SITE>.10` | All | Receives dynamic DNS updates from firewall |

### 3.2 DNS Zones to be Created

| Zone name | Type | Hosted on | Replication |
|-----------|------|-----------|-------------|
| `example.com` | Forward, AD-integrated | All DCs | Forest-wide |
| `example.org` | Forward, AD-integrated | All DCs | Forest-wide |
| `example.net` | Forward, AD-integrated | All DCs | Forest-wide |
| `76.168.192.in-addr.arpa` | Reverse, AD-integrated | `EXADCSFAL001` | Forest-wide |
| `231.168.192.in-addr.arpa` | Reverse, AD-integrated | `EXADCSCPH001` | Forest-wide |
| `126.168.192.in-addr.arpa` | Reverse, AD-integrated | `EXADCSODE001` | Forest-wide |
| `136.168.192.in-addr.arpa` | Reverse, AD-integrated | `EXADCSBRK001` | Forest-wide |
| `161.168.192.in-addr.arpa` | Reverse, AD-integrated | `EXADCSMCR001` | Forest-wide |
| `151.168.192.in-addr.arpa` | Reverse, AD-integrated | `EXADCSLIV001` | Forest-wide |
| `141.168.192.in-addr.arpa` | Reverse, AD-integrated | `EXADCSGLA001` | Forest-wide |
| `191.168.192.in-addr.arpa` | Reverse, AD-integrated | `EXADCSNEW001` | Forest-wide |
| `65.168.192.in-addr.arpa` | Reverse, AD-integrated | `EXADCSKGE001` | Forest-wide |
| `246.168.192.in-addr.arpa` | Reverse, AD-integrated | `EXADCSFAX001` | Forest-wide |
| `164.168.192.in-addr.arpa` | Reverse, AD-integrated | `EXADCSTOR001` | Forest-wide |
| `154.168.192.in-addr.arpa` | Reverse, AD-integrated | `EXADCSMTL001` | Forest-wide |
| `29.168.192.in-addr.arpa` | Reverse, AD-integrated | `EXADCSSYD001` | Forest-wide |
| `139.168.192.in-addr.arpa` | Reverse, AD-integrated | `EXADCSCLD001` | Forest-wide |

> ℹ As additional sites are built out and their DCs promoted, add the corresponding reverse zone to that site's DC following the pattern in section 6.

### 3.3 Initial DNS Records

| Zone | Record type | Name | Value |
|------|-------------|------|-------|
| `example.com` | A | `provisioning` | `192.168.139.50` |
| `example.org` | A | `provisioning` | `192.168.139.50` |
| `example.net` | A | `provisioning` | `192.168.139.50` |
| `139.168.192.in-addr.arpa` | PTR | `50` | `EXAPROVCLD001.jukebox.internal.` |

---

## 4. Prerequisites

1. `jukebox.internal` forest is operational at Windows Server 2022 functional level
2. All DCs listed in section 3.1 are promoted and AD replication is healthy — verify with `dcdiag /test:replications` on `EXADCSFAL001`
3. DNS role is installed and running on all DCs (`Get-Service DNS` returns `Running` on all)
4. `EXAPROVCLD001` is online at `192.168.139.50` and reachable from all sites via WireGuard
5. SSH access to each `EXAFWL???001` node is available for dnsmasq configuration
6. `bind9-dnsutils` package available on all firewall nodes (provides `nsupdate`)
7. Windows DNS dynamic updates are currently set to **Secure only** by default — this procedure changes them to **Nonsecure and Secure** restricted by ACL. Confirm this is acceptable before proceeding.

> ⚠ These procedures make forest-wide changes to AD and DNS. Run them from `EXADCSFAL001` during a maintenance window. Changes replicate automatically — they cannot easily be scoped to a single DC.

---

## Part A — UPN Suffixes

## 5. Add UPN Suffixes to the Forest

UPN suffixes are a forest-wide setting stored in the AD configuration partition. They are added once on any DC and replicate automatically to all DCs.

### 5.1 Add UPN Suffixes via PowerShell

Run on `EXADCSFAL001`:

```powershell
Get-ADForest | Select-Object UPNSuffixes

$suffixes = @('example.com', 'example.org', 'example.net')
foreach ($suffix in $suffixes) {
    Get-ADForest | Set-ADForest -UPNSuffixes @{Add = $suffix}
}

# Verify
Get-ADForest | Select-Object -ExpandProperty UPNSuffixes
```

Expected output:

```
example.com
example.org
example.net
```

### 5.2 Assign a UPN Suffix to a User Account

Once suffixes are registered, assign them to user accounts individually. The suffix does not change automatically for existing accounts — this must be done explicitly:

```powershell
# Set a single user's UPN
Set-ADUser -Identity 'jsmith' -UserPrincipalName 'j.smith@example.com'

# Bulk-set all users in an OU to example.com
Get-ADUser -Filter * -SearchBase 'OU=Users,DC=jukebox,DC=example' | ForEach-Object {
    $newUPN = $_.SamAccountName + '@example.com'
    Set-ADUser $_ -UserPrincipalName $newUPN
}
```

> ℹ A user's UPN suffix does not have to match the domain they are physically located in. An Australian user visiting Edinburgh will authenticate successfully with `@example.com` regardless of which DC processes the authentication, as UPN suffixes are forest-wide.

> ⚠ Changing a user's UPN will affect any applications or services that use the UPN as an identifier (e.g. SAML-based SSO, Office 365 federation). Audit integrations before bulk-changing UPNs on existing accounts.

### 5.3 Verify UPN Login

From a domain-joined workstation, verify that a test account can log in using the new UPN suffix format (`testuser@example.com`). Confirm from at least one DC at each hub site (FAL, ODE, BRK) that the suffix is visible:

```powershell
# Run on EXADCSODE001 and EXADCSBRK001 to confirm replication
Get-ADForest | Select-Object -ExpandProperty UPNSuffixes
```

---

## Part B — Internal Forward DNS Zones

## 6. Create AD-Integrated Forward Zones

All three zones are created as AD-integrated primary zones with forest-wide replication. This means every DC in the `jukebox.internal` forest automatically hosts and serves these zones — no secondary zone configuration is required.

### 6.1 Create the Three Forward Zones

Run on `EXADCSFAL001`:

```powershell
$zones = @('example.com', 'example.org', 'example.net')

foreach ($zone in $zones) {
  Add-DnsServerPrimaryZone -Name $zone -ReplicationScope 'Forest' -DynamicUpdate 'NonsecureAndSecure' -ComputerName 'EXADCSFAL001'
  Write-Host "Created zone: $zone"
}
```

> ℹ `ReplicationScope 'Forest'` replicates the zone to all DCs in the forest via the `ForestDnsZones` AD application partition. This is the correct scope for zones that all sites need to resolve.

> ⚠ `DynamicUpdate 'NonsecureAndSecure'` allows dynamic DNS updates without Kerberos authentication. This is intentional — it allows dnsmasq/nsupdate on the firewall nodes to update DNS. Access is restricted by IP ACL in section 7.

### 6.2 Verify Zones Exist on All DCs

After AD replication (allow up to 15 minutes), verify the zones have replicated to hub DCs:

```powershell
$dcs = @('EXADCSFAL001','EXADCSODE001','EXADCSBRK001','EXADCSCPH001')
$zones = @('example.com','example.org','example.net')

foreach ($dc in $dcs) {
  foreach ($zone in $zones) {
    $result = Get-DnsServerZone -Name $zone -ComputerName $dc -ErrorAction SilentlyContinue
    if ($result) {
      Write-Host "$dc : $zone - OK"
    } else {
      Write-Host "$dc : $zone - MISSING" -ForegroundColor Red
    }
  }
}
```

### 6.3 Add Initial DNS Records

Add the `provisioning` A record to all three forward zones, pointing to `EXAPROVCLD001`:

```powershell
$zones = @('example.com', 'example.org', 'example.net')

foreach ($zone in $zones) {
  Add-DnsServerResourceRecordA -ZoneName $zone -Name 'provisioning' -IPv4Address '192.168.139.50' -ComputerName 'EXADCSFAL001' -TimeToLive '01:00:00'
  Write-Host "Added provisioning A record to $zone"
}
```

Verify:

```powershell
foreach ($zone in $zones) { Resolve-DnsName "provisioning.$zone" -Server 192.168.76.10 }
```

---

## Part C — Per-Site Reverse DNS Zones

## 7. Create Reverse Lookup Zones

Each site's reverse zone is created on that site's primary DC. Because all zones use `ReplicationScope 'Forest'`, every DC in the estate can resolve PTR queries for every site — no secondary zones are needed.

### 7.1 Create Reverse Zones — Bulk Script

Run this from `EXADCSFAL001`. The script creates each reverse zone on its respective DC. Ensure all listed DCs are online before running.

```powershell
$reverseZones = @(
  @{ Zone = '76.168.192.in-addr.arpa';  DC = 'EXADCSFAL001' },
  @{ Zone = '231.168.192.in-addr.arpa'; DC = 'EXADCSCPH001' },
  @{ Zone = '126.168.192.in-addr.arpa'; DC = 'EXADCSODE001' },
  @{ Zone = '136.168.192.in-addr.arpa'; DC = 'EXADCSBRK001' },
  @{ Zone = '161.168.192.in-addr.arpa'; DC = 'EXADCSMCR001' },
  @{ Zone = '151.168.192.in-addr.arpa'; DC = 'EXADCSLIV001' },
  @{ Zone = '141.168.192.in-addr.arpa'; DC = 'EXADCSGLA001' },
  @{ Zone = '191.168.192.in-addr.arpa'; DC = 'EXADCSNEW001' },
  @{ Zone = '65.168.192.in-addr.arpa';  DC = 'EXADCSKGE001' },
  @{ Zone = '246.168.192.in-addr.arpa'; DC = 'EXADCSFAX001' },
  @{ Zone = '164.168.192.in-addr.arpa'; DC = 'EXADCSTOR001' },
  @{ Zone = '154.168.192.in-addr.arpa'; DC = 'EXADCSMTL001' },
  @{ Zone = '29.168.192.in-addr.arpa';  DC = 'EXADCSSYD001' },
  @{ Zone = '139.168.192.in-addr.arpa'; DC = 'EXADCSCLD001' }
)

foreach ($entry in $reverseZones) {
  Add-DnsServerPrimaryZone -Name $entry.Zone -ReplicationScope 'Forest' -DynamicUpdate 'NonsecureAndSecure' -ComputerName $entry.DC
  Write-Host "Created $($entry.Zone) on $($entry.DC)"
}
```

### 7.2 Add the Provisioning PTR Record

Add the PTR record for `EXAPROVCLD001` to the CLD reverse zone:

```powershell
Add-DnsServerResourceRecordPtr -ZoneName '139.168.192.in-addr.arpa' -Name '50' -PtrDomainName 'EXAPROVCLD001.jukebox.internal.' -ComputerName 'EXADCSCLD001' -TimeToLive '01:00:00'
```

Verify:

```powershell
Resolve-DnsName '192.168.139.50' -Server 192.168.76.10
```

Expected output: `EXAPROVCLD001.jukebox.internal`

### 7.3 Set Dynamic Update ACLs on Reverse Zones

Each reverse zone must allow non-secure dynamic updates, but only from its local firewall (`.253`). This is set per-zone using PowerShell. The example below sets the ACL for FAL — repeat for each site substituting the zone name and firewall IP.

```powershell
# FAL reverse zone — allow updates from 192.168.76.253 only
$zone = '76.168.192.in-addr.arpa'
$firewallIP = '192.168.76.253'
$acl = Get-DnsServerZoneAging -ZoneName $zone -ComputerName 'EXADCSFAL001'

# Build the ACL entry — allow from firewall, deny all others
$accessRule = New-Object System.DirectoryServices.ActiveDirectoryAccessRule(
    [System.Security.Principal.NTAccount]"ANONYMOUS LOGON",
    [System.DirectoryServices.ActiveDirectoryRights]::GenericAll,
    [System.Security.AccessControl.AccessControlType]::Allow
)
```

> ℹ Windows DNS does not natively filter dynamic updates by source IP through PowerShell ACLs in the same way a firewall rule does. The most practical approach for a non-secure dynamic update environment is to restrict at the **firewall level** — ensure only traffic from `.253` on each site can reach port 53 (TCP/UDP) on the local DC (`.10`). The WireGuard tunnel ACLs on `EXAFWL???001` should enforce this. Document this as a firewall rule on each site's firewall config.

The Windows DNS setting `NonsecureAndSecure` combined with firewall-level restriction from `.253` → `.10` port 53 provides the equivalent protection without complex DACL management. If TSIG is added in a future phase, this can be revisited.

### 7.4 Adding a New Site's Reverse Zone

When a new site DC is promoted, add its reverse zone as follows. Replace `XXX` with the site code and `NNN` with the third octet of the site's subnet:

```powershell
Add-DnsServerPrimaryZone -Name 'NNN.168.192.in-addr.arpa' -ReplicationScope 'Forest' -DynamicUpdate 'NonsecureAndSecure' -ComputerName 'EXADCSXXX001'
```

The zone will replicate to all other DCs within the AD replication interval. No action is needed on other DCs.

---

## Part D — dnsmasq Configuration

## 8. dnsmasq Setup on EXAFWL???001

Each firewall node runs dnsmasq on Debian Trixie at `.253`. The configuration covers:

- DHCP server for the site's `/24` subnet (`.100`–`.249` pool per convention)
- Local DNS cache and resolution for the site
- DNS forwarding to the local DC (`.10`) for all `jukebox.internal`, `example.com`, `example.org`, `example.net`, and reverse zones
- A `dhcp-script` that calls `nsupdate` to push A and PTR records to the DC whenever a lease is issued or renewed

### 8.1 Install Required Packages

SSH into the firewall node and install `bind9-dnsutils` (provides `nsupdate`):

```bash
apt update && apt install -y bind9-dnsutils
```

Verify `nsupdate` is available:

```bash
nsupdate -v /dev/null && echo "nsupdate OK"
```

### 8.2 Create the dnsmasq Site Configuration

The main dnsmasq config for each site lives at `/etc/dnsmasq/lan.conf`. The example below is for **FAL** (`192.168.76.0/24`) — substitute site-specific values as noted.

```bash
cat > /etc/dnsmasq/lan.conf << 'EOF'
# =============================================================
# Example Music — dnsmasq site config
# Site:    FAL — Falkirk, Scotland
# Subnet:  192.168.76.0/24
# DC:      EXADCSFAL001 @ 192.168.76.10
# FW:      EXAFWLFAL001 @ 192.168.76.253
# =============================================================

# --- Interface binding ---
# Bind only to the LAN interface — adjust interface name to match
interface=eth1
bind-interfaces

# --- DHCP pool ---
# Pool: .100 to .249, 24 hour lease
dhcp-range=192.168.76.100,192.168.76.249,255.255.255.0,24h

# --- DHCP options ---
dhcp-option=option:router,192.168.76.1
dhcp-option=option:dns-server,192.168.76.253,192.168.76.10
dhcp-option=option:domain-name,jukebox.internal

# --- Local domain ---
local=/jukebox.internal/
domain=jukebox.internal

# --- DNS forwarding ---
# Forward all jukebox.internal and internal domain queries to the local DC
server=/jukebox.internal/192.168.76.10
server=/example.com/192.168.76.10
server=/example.org/192.168.76.10
server=/example.net/192.168.76.10

# Forward all reverse zones to the local DC
# The DC holds its own zone and replicates all others, so one forwarder covers all
server=/168.192.in-addr.arpa/192.168.76.10

# --- DHCP dynamic DNS update script ---
# Called on every lease event — see section 8.3
dhcp-script=/etc/dnsmasq/dhcp-dnsupdate.sh

# --- Logging ---
log-queries
log-dhcp
log-facility=/var/log/dnsmasq.log
EOF
```

> ⚠ The `interface=` value (`eth1` above) must match the actual LAN-facing interface name on each firewall node. Verify with `ip link show` before applying. On some nodes this may be `ens3`, `enp2s0`, or similar.

> ℹ `server=/168.192.in-addr.arpa/192.168.76.10` forwards **all** `192.168.x.x` reverse lookups to the local DC. Because all reverse zones are forest-wide AD-integrated, the local DC can answer PTR queries for any site — this single forwarder covers the entire estate.

### 8.3 Create the DHCP Dynamic DNS Update Script

This script is called by dnsmasq on every DHCP lease event. It uses `nsupdate` to send dynamic DNS updates to the local Windows DC — adding or removing A and PTR records as leases are issued, renewed, or released.

```bash
cat > /etc/dnsmasq/dhcp-dnsupdate.sh << 'SCRIPT'
#!/bin/bash
# =============================================================
# Example Music — dnsmasq DHCP dynamic DNS update script
# Called by dnsmasq with: <action> <mac> <ip> [<hostname>]
# Actions: add, del, old
# =============================================================

ACTION="$1"
MAC="$2"
IP="$3"
HOSTNAME="${4:-}"

# --- Site-specific settings ---
# Substitute correct values per site
DC_IP="192.168.76.10"           # Local DC — EXADCS<SITE>001
DOMAIN="jukebox.internal"
ZONE_FORWARD="jukebox.internal"
TTL=3600

# Derive reverse zone and PTR name from IP
# e.g. 192.168.76.150 -> zone=76.168.192.in-addr.arpa, ptr=150
IFS='.' read -r o1 o2 o3 o4 <<< "$IP"
REVERSE_ZONE="${o3}.${o2}.${o1}.in-addr.arpa"
PTR_NAME="${o4}"

# If no hostname provided by client, generate one from MAC
if [ -z "$HOSTNAME" ]; then
  HOSTNAME="dhcp-${MAC//:/-}"
fi

FQDN="${HOSTNAME}.${DOMAIN}"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') [dns-update] $*" >> /var/log/dnsmasq-dnsupdate.log
}

case "$ACTION" in
  add|old)
    log "ADD/RENEW: $FQDN -> $IP (PTR: $PTR_NAME.$REVERSE_ZONE)"
    ## Forward A record
    nsupdate << EOF
server $DC_IP
zone $ZONE_FORWARD
update delete $FQDN A
update add $FQDN $TTL A $IP
send
EOF

# Reverse PTR record
nsupdate << EOF
server $DC_IP
zone $REVERSE_ZONE
update delete $PTR_NAME.$REVERSE_ZONE PTR
update add $PTR_NAME.$REVERSE_ZONE $TTL PTR $FQDN
send
EOF

log "Done: $FQDN / $IP"
;;

del)
  log "RELEASE: $FQDN -> $IP"
  ## Remove forward A record
  nsupdate << EOF
server $DC_IP
zone $ZONE_FORWARD
update delete $FQDN A
send
EOF

## Remove reverse PTR record
nsupdate << EOF
server $DC_IP
zone $REVERSE_ZONE
update delete $PTR_NAME.$REVERSE_ZONE PTR
send
EOF

log "Removed: $FQDN / $IP"
;;
esac

exit 0
SCRIPT

chmod +x /etc/dnsmasq/dhcp-dnsupdate.sh
```

> ℹ The script deletes then re-adds records (`update delete` before `update add`) to handle renewals cleanly — if the record already exists with the same or a stale IP, this prevents duplicate or conflicting entries.

> ℹ `action=old` is sent by dnsmasq on startup for existing leases that were active before dnsmasq was restarted. Treating `old` the same as `add` ensures DNS stays in sync after a firewall reboot.

### 8.4 Site-Specific Values to Substitute

When deploying to each site, change the following values in both `lan.conf` and `dhcp-dnsupdate.sh`:

| Variable | FAL example | Pattern |
|----------|-------------|---------|
| `interface=` | `eth1` | Match actual LAN interface — check with `ip link show` |
| `dhcp-range=` | `192.168.76.100,192.168.76.249` | Site subnet third octet |
| `dhcp-option=option:router` | `192.168.76.1` | Site `.1` |
| `dhcp-option=option:dns-server` | `192.168.76.253,192.168.76.10` | Site `.253` then `.10` |
| `server=/jukebox.internal/` | `192.168.76.10` | Site DC `.10` |
| `server=/example.com/` etc. | `192.168.76.10` | Site DC `.10` |
| `server=/168.192.in-addr.arpa/` | `192.168.76.10` | Site DC `.10` |
| `DC_IP` (in script) | `192.168.76.10` | Site DC `.10` |

A complete per-site substitution reference:

| Site | Subnet | `.1` gateway | `.10` DC | `.253` FW |
|------|--------|-------------|----------|-----------|
| ABD  | 192.168.224.0/24 | 192.168.224.1 | 192.168.224.10 | 192.168.224.253 |
| AMS  | 192.168.31.0/24  | 192.168.31.1  | 192.168.31.10  | 192.168.31.253  |
| ATL  | 192.168.44.0/24  | 192.168.44.1  | 192.168.44.10  | 192.168.44.253  |
| BIR  | 192.168.121.0/24 | 192.168.121.1 | 192.168.121.10 | 192.168.121.253 |
| BON  | 192.168.228.0/24 | 192.168.228.1 | 192.168.228.10 | 192.168.228.253 |
| BRD  | 192.168.113.0/24 | 192.168.113.1 | 192.168.113.10 | 192.168.113.253 |
| BRK  | 192.168.136.0/24 | 192.168.136.1 | 192.168.136.10 | 192.168.136.253 |
| CHI  | 192.168.214.0/24 | 192.168.214.1 | 192.168.214.10 | 192.168.214.253 |
| CLD  | 192.168.139.0/24 | 192.168.139.1 | 192.168.139.8 | 192.168.139.253 |
| CLY  | 192.168.41.0/24  | 192.168.41.1  | 192.168.41.10  | 192.168.41.253  |
| COV  | 192.168.247.0/24 | 192.168.247.1 | 192.168.247.10 | 192.168.247.253 |
| CPH  | 192.168.231.0/24 | 192.168.231.1 | 192.168.231.10 | 192.168.231.253 |
| DUN  | 192.168.138.0/24 | 192.168.138.1 | 192.168.138.10 | 192.168.138.253 |
| EDI  | 192.168.131.0/24 | 192.168.131.1 | 192.168.131.10 | 192.168.131.253 |
| FAL  | 192.168.76.0/24  | 192.168.76.1  | 192.168.76.10  | 192.168.76.253  |
| FAX  | 192.168.246.0/24 | 192.168.246.1 | 192.168.246.10 | 192.168.246.253 |
| GLA  | 192.168.141.0/24 | 192.168.141.1 | 192.168.141.10 | 192.168.141.253 |
| GOT  | 192.168.46.0/24  | 192.168.46.1  | 192.168.46.10  | 192.168.46.253  |
| HAL  | 192.168.142.0/24 | 192.168.142.1 | 192.168.142.10 | 192.168.142.253 |
| HUL  | 192.168.148.0/24 | 192.168.148.1 | 192.168.148.10 | 192.168.148.253 |
| KGE  | 192.168.65.0/24  | 192.168.65.1  | 192.168.65.10  | 192.168.65.253  |
| KOR  | 192.168.238.0/24 | 192.168.238.1 | 192.168.238.10 | 192.168.238.253 |
| LAX  | 192.168.213.0/24 | 192.168.213.1 | 192.168.213.10 | 192.168.213.253 |
| LIV  | 192.168.151.0/24 | 192.168.151.1 | 192.168.151.10 | 192.168.151.253 |
| LND  | 192.168.20.0/24  | 192.168.20.1  | 192.168.20.10  | 192.168.20.253  |
| MCR  | 192.168.161.0/24 | 192.168.161.1 | 192.168.161.10 | 192.168.161.253 |
| MEL  | 192.168.61.0/24  | 192.168.61.1  | 192.168.61.10  | 192.168.61.253  |
| MIA  | 192.168.135.0/24 | 192.168.135.1 | 192.168.135.10 | 192.168.135.253 |
| MIL  | 192.168.39.0/24  | 192.168.39.1  | 192.168.39.10  | 192.168.39.253  |
| MTL  | 192.168.154.0/24 | 192.168.154.1 | 192.168.154.10 | 192.168.154.253 |
| MUN  | 192.168.189.0/24 | 192.168.189.1 | 192.168.189.10 | 192.168.189.253 |
| NEW  | 192.168.191.0/24 | 192.168.191.1 | 192.168.191.10 | 192.168.191.253 |
| NJC  | 192.168.201.0/24 | 192.168.201.1 | 192.168.201.10 | 192.168.201.253 |
| NYC  | 192.168.212.0/24 | 192.168.212.1 | 192.168.212.10 | 192.168.212.253 |
| ODE  | 192.168.126.0/24 | 192.168.126.1 | 192.168.126.10 | 192.168.126.253 |
| OSL  | 192.168.47.0/24  | 192.168.47.1  | 192.168.47.10  | 192.168.47.253  |
| PER  | 192.168.173.0/24 | 192.168.173.1 | 192.168.173.10 | 192.168.173.253 |
| SHE  | 192.168.114.0/24 | 192.168.114.1 | 192.168.114.10 | 192.168.114.253 |
| SYD  | 192.168.29.0/24  | 192.168.29.1  | 192.168.29.10  | 192.168.29.253  |
| TOR  | 192.168.146.0/24 | 192.168.146.1 | 192.168.146.10 | 192.168.146.253 |
| VIE  | 192.168.78.0/24  | 192.168.78.1  | 192.168.78.10  | 192.168.78.253  |
| AKL  | 192.168.93.0/24  | 192.168.93.1  | 192.168.93.10  | 192.168.93.253  |

### 8.5 Restart and Enable dnsmasq

```bash
systemctl restart dnsmasq
systemctl enable dnsmasq
systemctl status dnsmasq
```

Verify dnsmasq is listening on the correct interface:

```bash
ss -ulnp | grep 53
ss -tlnp | grep 53
```

---

## 9. Verification

### 9.1 UPN Suffixes

```powershell
# From any DC — confirm all three suffixes present
Get-ADForest | Select-Object -ExpandProperty UPNSuffixes
```

### 9.2 Forward Zone Replication

```powershell
# Check all three zones exist on all DCs
$dcs = @('EXADCSFAL001','EXADCSODE001','EXADCSBRK001','EXADCSCPH001', 'EXADCSMCR001','EXADCSLIV001','EXADCSGLA001','EXADCSNEW001',
         'EXADCSKGE001','EXADCSFAX001','EXADCSTOR001','EXADCSMTL001','EXADCSSYD001')
$zones = @('example.com','example.org','example.net')

foreach ($dc in $dcs) {
  foreach ($zone in $zones) {
    $r = Get-DnsServerZone -Name $zone -ComputerName $dc -ErrorAction SilentlyContinue
    $status = if ($r) { 'OK' } else { 'MISSING' }
    Write-Host "$dc`t$zone`t$status"
  }
}
```

### 9.3 Provisioning A Record Resolution

```powershell
# Test from FAL DC — should resolve to 192.168.139.50 for all three zones
Resolve-DnsName 'provisioning.example.com' -Server 192.168.76.10
Resolve-DnsName 'provisioning.example.org' -Server 192.168.76.10
Resolve-DnsName 'provisioning.example.net' -Server 192.168.76.10
```

### 9.4 Reverse Zone Replication and PTR Resolution

```powershell
# PTR lookup for provisioning server — should work from any DC
Resolve-DnsName '192.168.139.50' -Server 192.168.76.10
Resolve-DnsName '192.168.139.50' -Server 192.168.231.10  # CPH DC
Resolve-DnsName '192.168.139.50' -Server 192.168.136.10  # BRK DC
```

### 9.5 Test dnsmasq DHCP and Dynamic DNS Update

On the firewall node, tail the update log while a test device requests a DHCP lease:

```bash
tail -f /var/log/dnsmasq-dnsupdate.log
```

Then from the Windows DC, verify the record appeared:

```powershell
# Check that a dynamically registered A record is present
Get-DnsServerResourceRecord -ZoneName 'jukebox.internal' -ComputerName 'EXADCSFAL001' | Where-Object { $_.RecordType -eq 'A' }

# Check corresponding PTR
Get-DnsServerResourceRecord -ZoneName '76.168.192.in-addr.arpa' -ComputerName 'EXADCSFAL001' | Where-Object { $_.RecordType -eq 'PTR' }
```

### 9.6 Cross-Site PTR Resolution Test

Verify that a device registered at FAL can be resolved by PTR from ODE's DC (confirming forest-wide replication of reverse zones):

```powershell
# From ODE DC — resolve a FAL device's IP
Resolve-DnsName '192.168.76.150' -Server 192.168.126.10
```

---

## 10. Adding a Record Manually

### 10.1 Add an A Record

```powershell
# Example: add EXASBCEDI001 to the jukebox.internal forward zone
Add-DnsServerResourceRecordA -ZoneName 'jukebox.internal' -Name 'EXASBCEDI001' -IPv4Address '192.168.131.48' -ComputerName 'EXADCSFAL001' -TimeToLive '01:00:00'
```

This record replicates forest-wide automatically. All other site DCs will be able to resolve `EXASBCEDI001.jukebox.internal` within the AD replication interval (typically under 15 minutes).

### 10.2 Add a PTR Record

```powershell
# PTR for EXASBCEDI001 — add to EDI's reverse zone on EXADCSEDI001
# (once EDI DC exists — see section 7.4 for creating the zone)
Add-DnsServerResourceRecordPtr -ZoneName '131.168.192.in-addr.arpa' -Name '48' -PtrDomainName 'EXASBCEDI001.jukebox.internal.' -ComputerName 'EXADCSEDI001' -TimeToLive '01:00:00'
```

> ℹ Always add both the A record and the PTR record together. The A record goes in `jukebox.internal` (or the relevant forward zone). The PTR goes in the site's reverse zone on the site's own DC. Both replicate forest-wide automatically.

---

## 11. Troubleshooting

### 11.1 UPN Suffix Not Appearing on Remote DCs

- AD replication lag — wait 15 minutes and re-check
- Force replication: `repadmin /syncall /AdeP` on `EXADCSFAL001`
- Check replication health: `repadmin /showrepl`

### 11.2 DNS Zone Not Replicating to a DC

- Verify the DC's DNS service is running: `Get-Service DNS -ComputerName EXADCSODE001`
- Check that the DC has the `ForestDnsZones` application partition: `Get-ADObject -Filter * -SearchBase "DC=ForestDnsZones,DC=jukebox,DC=internal"`
- Force DNS replication: `dnscmd EXADCSODE001 /ZoneRefresh example.com`
- Check AD replication is healthy first: `dcdiag /test:replications`

### 11.3 nsupdate Fails — Permission Denied

- Verify Windows DNS zone has `NonsecureAndSecure` dynamic updates: `Get-DnsServerZone -Name 'jukebox.internal' | Select-Object DynamicUpdate`
- Verify the firewall can reach port 53 on the DC: `nc -zv 192.168.76.10 53` from the firewall node
- Check the nsupdate log at `/var/log/dnsmasq-dnsupdate.log` for specific error messages
- Test nsupdate manually from the firewall:

```bash
nsupdate << EOF
server 192.168.76.10
zone jukebox.internal
update add test-entry.jukebox.internal 3600 A 192.168.76.199
send
EOF
# Then verify on DC:
# Resolve-DnsName 'test-entry.jukebox.internal' -Server 192.168.76.10
# Then clean up:
nsupdate << EOF
server 192.168.76.10
zone jukebox.internal
update delete test-entry.jukebox.internal A
send
EOF
```

### 11.4 dnsmasq Script Not Running

- Verify the script is executable: `ls -la /etc/dnsmasq/dhcp-dnsupdate.sh` — must show `x` bit
- Verify dnsmasq config references the script: `grep dhcp-script /etc/dnsmasq/lan.conf`
- Check dnsmasq logs: `journalctl -u dnsmasq -f` and `/var/log/dnsmasq.log`
- Test the script manually: `/etc/dnsmasq/dhcp-dnsupdate.sh add aa:bb:cc:dd:ee:ff 192.168.76.150 test-device`

### 11.5 PTR Records Not Resolving from Remote Sites

- Confirm the reverse zone was created with `ReplicationScope 'Forest'`
- Check the zone's replication scope: `Get-DnsServerZone -Name '76.168.192.in-addr.arpa' | Select-Object ReplicationScope`
- Force zone replication to a specific DC: `dnscmd EXADCSODE001 /ZoneRefresh 76.168.192.in-addr.arpa`

### 11.6 Client Getting Wrong DNS Server

- Verify DHCP option 6 (dns-server) in `lan.conf` lists `.253` first, then `.10`
- Check client's actual DNS config: `ipconfig /all` (Windows) or `resolvectl status` (Linux)
- Verify dnsmasq is forwarding to the DC: `dig @192.168.76.253 provisioning.example.com` should return `192.168.139.50`

---

## 12. Deployment Checklist

| # | Task | Done |
|---|------|------|
| 1 | `bind9-dnsutils` installed on all `EXAFWL???001` nodes | ☐ |
| 2 | UPN suffixes `example.com`, `example.org`, `example.net` added to forest | ✅ Done 2026-03-13 |
| 3 | UPN suffixes confirmed replicated to ODE and BRK DCs | ✅ ODE confirmed 2026-03-13 — BRK pending |
| 4 | Forward zone `example.com` created — forest-wide, nonsecure dynamic update | ✅ Done 2026-03-13 |
| 5 | Forward zone `example.org` created — forest-wide, nonsecure dynamic update | ✅ Done 2026-03-13 |
| 6 | Forward zone `example.net` created — forest-wide, nonsecure dynamic update | ✅ Done 2026-03-13 |
| 7 | All three forward zones confirmed replicated to all DCs | ☐ |
| 8 | `provisioning.example.com/org/net` A records added → `192.168.139.50` | ☐ |
| 9 | A record resolution confirmed from FAL, ODE, BRK DCs | ☐ |
| 10 | Reverse zone created on each site DC (13 zones + CLD) | ✅ ODE done 2026-03-14 — remaining sites pending DC promotion |
| 11 | PTR record for `EXAPROVCLD001` added to `139.168.192.in-addr.arpa` | ☐ |
| -- | PTR record for EXADCSODE001 (192.168.126.10) added to `126.168.192.in-addr.arpa` | ✅ Done 2026-03-14 |
| 12 | PTR resolution for `192.168.139.50` confirmed from FAL, CPH, BRK DCs | ☐ |
| -- | PTR resolution for `192.168.126.10` confirmed from EXADCSODE001 | ✅ Done 2026-03-14 |
| 13 | `lan.conf` deployed and validated on all `EXAFWL???001` nodes | ☐ |
| 14 | `dhcp-dnsupdate.sh` deployed and executable on all `EXAFWL???001` nodes | ☐ |
| 15 | dnsmasq restarted and enabled on all firewall nodes | ☐ |
| 16 | Test DHCP lease issued — A and PTR records confirmed on DC | ☐ |
| 17 | Cross-site PTR resolution confirmed (FAL device resolved from ODE DC) | ☐ |
| 18 | UPN login tested — user signs in with `@example.com` UPN successfully | ☐ |

---

> 📌 **Reminder:** CLD site DC (`EXADCSCLD001`) reverse zone (`139.168.192.in-addr.arpa`) is included in this procedure but the CLD site itself has not yet been formally added to the DFS replication topology or the infrastructure inventory. Add CLD to both when the site is ready.

---

## Naming Convention Reference

| Prefix | Role | Example |
|--------|------|---------|
| `EXAFWL` | Firewall | `EXAFWLFAL001` |
| `EXARTR` | Router | `EXARTRFAL001` |
| `EXASWI` | Switch | `EXASWIFAL001` |
| `EXADCS` / `EXADCR` | Domain Controller (site/regional) | `EXADCSFAL001` |
| `EXAPVE` | Proxmox VE node | `EXAPVEFAL001` |
| `EXASRV` | Server | `EXADNSCLD001` |
| `EXARAC` | Remote Access Console (DRAC/iLO/RAC emulator) | `EXARACFAL001` |
| `EXANAS` | NAS | `EXANASFAL001` |
| `EXASBC` | VOIP SBC — trunks to `EXACLDPBX001` | `EXASBCFAL001` |
| `EXAPBX` | PBX | `EXACLDPBX001` |
| `EXAPRV` | Provisioning / bootstrap server | `EXAPRVFAL001` |
| `EXAWAP` | WiFi Access Point | `EXAWAPFAL001` |
| `EXAWKS` | Workstation | `EXAWKSFAL001` |
| `EXALAP` | Laptop | `EXALAPFAL001` |
| `EXAMBP` | MacBook Pro | `EXAMBPFAL001` |
| `EXAMAC` | iMac | `EXAMACFAL001` |
| `EXASUR` | Surface | `EXASURFAL001` |
| `EXATAB` | Tablet | `EXATABFAL001` |
| `EXAPHN` | Phone | `EXAPHNFAL001` |
| `EXACAM` | Camera | `EXACAMFAL001` |
| `EXAVND` / `EXADON` | Vending machine | `EXAVNDFAL001` |
| `EXAMUS` | Jukebox / instrument | `EXAMUSFAL001` |
| `EXAPAY` | Payphone | `EXAPAYFAL001` |
| `EXANIX` | Unix / legacy system | `EXANIXPER001` |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
