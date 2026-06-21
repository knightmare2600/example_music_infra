# easyDNS TUI v0.4.0 - Quick Start Guide

## Installation

### Prerequisites
```powershell
# Run PowerShell as Administrator
# Install Terminal.Gui module
Install-Module Terminal.Gui -Force -Scope CurrentUser
```

### First Launch
```powershell
# Navigate to script directory
cd C:\Path\To\Script

# Run the application
.\easyDNS-TUI-v0.4.0.ps1
```

---

## Navigation

### Keyboard Shortcuts
- **F1** - Help/Documentation
- **F5** - Refresh current view
- **F10** - Quit application
- **Alt+Letter** - Access menu items (e.g., Alt+F for File)
- **Tab** - Move between controls
- **Enter** - Activate selected button/item
- **Esc** - Close dialogs

### Menu Structure
```
File     - Connection, Import/Export, Quit
Zones    - Forward/Reverse zone management
Records  - DNS record operations
DNSSEC   - Zone signing status
Tools    - Diagnostic utilities
Settings - Auto-refresh toggle
Help     - About and documentation
```

---

## Common Tasks

### 1. Connect to DNS Server

**Auto-Connect (Default):**
- Application automatically detects and connects to local DNS server
- If successful, shows Dashboard

**Manual Connect:**
1. **File → Connect to Server**
2. Enter DNS server name/IP
3. Click **Connect**
4. Status bar updates to show connection

---

### 2. Create Forward Zone

1. **Zones → Forward Zones**
2. Click **Create** button
3. **Zone Name:** `example.com`
4. **Replication:** Select from:
   - Domain (default)
   - Forest
   - Legacy
5. Click **Create**
6. Zone appears in list

---

### 3. Create Reverse Zone

1. **Zones → Reverse Zones**
2. Click **Create** button
3. **Network ID:** Enter network
   - For /24: `192.168.1`
   - For /16: `10.0`
4. **Replication:** Select scope
5. Click **Create**
6. Zone created as `1.168.192.in-addr.arpa`

---

### 4. Add DNS Records

1. Click **Records** menu
2. **Select Zone:** Choose from list
3. Click **Load Records**
4. Click **Create Record**
5. Fill in details:
   - **Name:** `www` (or `@` for zone root)
   - **Type:** Select from dropdown (A, AAAA, CNAME, TXT, etc.)
   - **Data:** 
     - A: `192.168.1.10`
     - CNAME: `server.example.com`
     - TXT: `"v=spf1 mx -all"`
   - **TTL:** `3600` (seconds)
6. Click **Create**

**Record Type Examples:**
```
A Record:     www → 192.168.1.10
AAAA Record:  www → 2001:db8::1
CNAME:        alias → server.example.com
MX:           @   → 10 mail.example.com
TXT:          @   → "v=spf1 mx -all"
```

---

### 5. Delete DNS Records

1. **Records** menu
2. Select zone and click **Load Records**
3. Select record in table
4. Click **Delete Record**
5. **Confirm deletion**
6. Record removed and table refreshes

---

### 6. Export DNS Records

1. **File → Export Configuration**
2. **Select Zone:** Choose zone to export
3. **Format:** Choose export format
   - **CSV** - Excel-compatible, human-readable
   - **JSON** - Programming/scripting
   - **XML** - PowerShell native format
4. Click **Export**
5. File saved to `./Export/` directory
6. Filename: `DNS_Export_ZoneName_YYYYMMDD_HHMMSS.ext`

**Export File Location:**
```
./Export/DNS_Export_example.com_20260208_143022.csv
```

---

### 7. Import DNS Records

**Prepare Import File:**

Create CSV file in `./Import/` directory:
```csv
Name,Type,Data,TTL,Zone
www,A,192.168.1.10,3600,example.com
mail,A,192.168.1.20,3600,example.com
ftp,CNAME,www.example.com,3600,example.com
@,MX,10 mail.example.com,3600,example.com
@,TXT,v=spf1 mx -all,3600,example.com
```

**Import Process:**
1. Save file to `./Import/` directory
2. **File → Import Configuration**
3. **File:** Select from list or type filename
4. **Target Zone:** Enter zone name (e.g., `example.com`)
5. Click **Import**
6. Review import results (success/error counts)

---

### 8. Run Diagnostic Tools

#### Ping
1. **Tools** menu
2. **Target:** `8.8.8.8` or `google.com`
3. Click **Ping**
4. View results: Response time, TTL

#### DNS Lookup (Nslookup)
1. **Tools** menu
2. **Target:** `example.com`
3. Click **Nslookup**
4. View DNS records from your DNS server

#### Traceroute
1. **Tools** menu
2. **Target:** `example.com`
3. Click **Traceroute**
4. View hop-by-hop route to destination

#### DNS Benchmark
1. **Tools** menu
2. **Target:** `example.com`
3. Click **Benchmark**
4. View performance statistics:
   - 10 test iterations
   - Average, Min, Max response times
   - Useful for troubleshooting slow DNS

#### DNS Cache Management
**View Cache:**
1. **Tools** menu
2. Click **DNS Cache**
3. View cached entries (up to 50)

**Clear Cache:**
1. **Tools** menu
2. Click **Clear Cache**
3. Confirmation message appears

---

### 9. Enable Auto-Refresh

1. **Settings → Toggle Auto-Refresh**
2. Confirmation: "Auto-refresh enabled"
3. Current view refreshes every 5 minutes
4. Works for:
   - Dashboard
   - Forward Zones
   - Reverse Zones

**To Disable:**
1. **Settings → Toggle Auto-Refresh** again
2. Confirmation: "Auto-refresh disabled"

---

## Dashboard Information

The Dashboard displays:

### Server Information
- Operating System
- Current user
- DNS Server name
- Connection status

### DNS Statistics
- Forward Zones count
- Reverse Zones count

### Quick Actions
- Connect to Server
- Forward Zones
- Reverse Zones
- DNS Records

---

## File Structure

```
./
├── easyDNS-TUI-v0.4.0.ps1    # Main application
├── Logs/                      # Application logs
│   └── easyDNS_YYYYMMDD.log
├── Export/                    # Exported DNS records
│   └── DNS_Export_*.{csv,json,xml}
├── Import/                    # Import files (place here)
│   └── *.{csv,json,xml}
└── Temp/                      # Temporary files
```

---

## Tips & Best Practices

### Zone Management
- Use descriptive zone names
- Choose replication scope carefully:
  - **Domain** - Most common, replicates to domain DCs
  - **Forest** - Replicates to all DCs in forest
  - **Legacy** - For compatibility with older systems

### Record Management
- Use consistent TTL values (3600 = 1 hour is standard)
- Document TXT records (SPF, DKIM, etc.)
- Test changes with nslookup before going live
- Use CNAME for aliases, A/AAAA for actual IPs

### Import/Export
- **CSV** is easiest for manual editing
- Export regularly for backups
- Test imports on test zones first
- Check import results for errors

### Diagnostics
- Use Benchmark to identify DNS performance issues
- Clear cache when troubleshooting resolution problems
- Traceroute helps identify network path issues
- Nslookup verifies records are in DNS

### Auto-Refresh
- Enable for monitoring environments
- Disable for manual configuration work
- 5-minute interval prevents excessive queries

---

## Troubleshooting

### Cannot Connect to DNS Server
**Symptoms:** "Not connected to DNS server" error

**Solutions:**
1. Verify DNS service is running:
   ```powershell
   Get-Service DNS
   ```
2. Check firewall allows DNS queries
3. Ensure running as Administrator
4. Try connecting to `localhost` if local server

---

### Import Fails
**Symptoms:** "Import failed" or errors during import

**Solutions:**
1. **Check file format:**
   - CSV must have headers: Name,Type,Data,TTL,Zone
   - No extra columns
   - Data properly formatted for each type
2. **Verify zone exists**
3. **Check permissions**

**Valid CSV Example:**
```csv
Name,Type,Data,TTL,Zone
www,A,192.168.1.10,3600,example.com
```

---

### Records Don't Appear
**Symptoms:** Created record doesn't show in table

**Solutions:**
1. Click **Refresh** button
2. Reload the zone (select zone again)
3. Check DNS server directly:
   ```powershell
   Get-DnsServerResourceRecord -ZoneName example.com
   ```
4. Verify record was actually created (check logs)

---

### Auto-Refresh Not Working
**Symptoms:** Views don't update automatically

**Solutions:**
1. Toggle auto-refresh off then on again
2. Check if on supported view (Dashboard, Zones)
3. Review logs for errors
4. Restart application

---

### Diagnostic Tools Timeout
**Symptoms:** "Error: timeout" in tool output

**Solutions:**
1. Check network connectivity
2. Verify target is reachable
3. Check firewall rules
4. Try different target

---

## Advanced Usage

### Batch Operations

**Export All Zones:**
1. Export each zone individually
2. Combine CSV files if needed
3. Use JSON for programmatic processing

**Bulk Record Creation:**
1. Create CSV with all records
2. Import to appropriate zone
3. Review results for errors
4. Fix errors and re-import if needed

---

### Monitoring Workflows

**Daily DNS Health Check:**
1. Enable auto-refresh
2. Navigate to Dashboard
3. Monitor zone counts
4. Run benchmark on critical domains
5. Review logs for errors

**Record Audit:**
1. Export zones to CSV
2. Review in Excel
3. Identify outdated records
4. Clean up as needed

---

## Support & Resources

### Getting Help
1. Press **F1** for built-in help
2. Check logs in `./Logs/` directory
3. Review this Quick Start Guide
4. Check CHANGELOG.md for new features

### Log Files
Location: `./Logs/easyDNS_YYYYMMDD.log`

Contains:
- Connection events
- Operation success/failures
- Error details
- Performance metrics

**View Recent Logs:**
```powershell
Get-Content ./Logs/easyDNS_$(Get-Date -Format yyyyMMdd).log -Tail 50
```

---

## Quick Reference

### Common Record Types

| Type | Purpose | Example Data |
|------|---------|-------------|
| A | IPv4 address | `192.168.1.10` |
| AAAA | IPv6 address | `2001:db8::1` |
| CNAME | Alias | `server.example.com` |
| MX | Mail server | `10 mail.example.com` |
| TXT | Text data | `"v=spf1 mx -all"` |
| PTR | Reverse lookup | `server.example.com` |
| NS | Name server | `ns1.example.com` |
| SRV | Service location | `0 5 5060 sipserver.example.com` |

---

### TTL Values

| TTL | Seconds | Usage |
|-----|---------|-------|
| 5 min | 300 | Testing/changes |
| 1 hour | 3600 | Standard (recommended) |
| 1 day | 86400 | Stable records |

---

## Sample Workflows

### Scenario: New Domain Setup

1. **Create forward zone:** `contoso.com`
2. **Create reverse zone:** Network `192.168.1`
3. **Add A records:**
   - `@` → `192.168.1.10` (root)
   - `www` → `192.168.1.10`
   - `mail` → `192.168.1.20`
4. **Add MX record:** `@` → `10 mail.contoso.com`
5. **Add TXT record:** `@` → `"v=spf1 mx -all"`
6. **Test with nslookup**
7. **Export zone** for backup

---

### Scenario: Migrate Records

1. **On source DNS:**
   - Export zone to CSV
   - Copy file to new server
2. **On target DNS:**
   - Create zone
   - Place CSV in Import directory
   - Import records
   - Verify import results
   - Test critical records

---

### Scenario: Troubleshoot Slow DNS

1. **Run benchmark** on problem domain
2. **Check DNS cache** for stale entries
3. **Clear cache** if needed
4. **Run benchmark again** to compare
5. **Use traceroute** to check network path
6. **Review logs** for errors

---

**Happy DNS Managing! 🎉**

For detailed feature information, see **easyDNS-TUI-CHANGELOG.md**
