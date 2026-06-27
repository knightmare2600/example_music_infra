# easyDNS TUI v0.4.0 - Changelog

## Overview
Enhanced Terminal.Gui version of easyDNS with comprehensive DNS management capabilities. This version adds significant new functionality compared to the initial v0.3.0 TUI conversion.

---

## What's New in v0.4.0

### 🗑️ DNS Record Deletion
**Previously:** Records could be created but not deleted
**Now:** Full CRUD operations for DNS records

- **Delete Record button** in Records view
- Confirmation dialog before deletion
- Automatic table refresh after deletion
- Supports all record types (A, AAAA, CNAME, TXT, etc.)

**Usage:**
1. Navigate to Records menu
2. Select a zone and load records
3. Select a record in the table
4. Click "Delete Record"
5. Confirm deletion

---

### 🔄 Reverse Zone Creation
**Previously:** Only forward zones could be created
**Now:** Full reverse zone management

- **Create Reverse Zone dialog** with network ID input
- Supports /24 and /16 networks
- Automatic conversion to `.in-addr.arpa` format
- Replication scope selection (Domain/Forest/Legacy)
- Helpful example text (e.g., "192.168.1 for /24")

**Usage:**
1. Navigate to Zones → Reverse Zones
2. Click "Create" button
3. Enter network ID (e.g., "192.168.1")
4. Select replication scope
5. Click "Create"

---

### 📤 Import/Export DNS Records
**Previously:** Placeholder "Coming soon" messages
**Now:** Full import/export functionality

#### Export Features:
- Export DNS records from any zone
- **Three formats:** CSV, JSON, XML
- Zone selector with ListView
- Automatic timestamped filenames
- Export includes: Name, Type, Data, TTL, Zone
- Files saved to `./Export/` directory

**Export Usage:**
1. File → Export Configuration
2. Select zone
3. Choose format (CSV/JSON/XML)
4. Records exported to `Export/DNS_Export_ZoneName_TIMESTAMP.ext`

#### Import Features:
- Import DNS records from CSV/JSON/XML files
- Automatic format detection
- Target zone selection
- Preview available files in import directory
- Batch record creation
- Error tracking and reporting
- Files read from `./Import/` directory

**Import Usage:**
1. Place import files in `./Import/` directory
2. File → Import Configuration
3. Select file from list
4. Specify target zone
5. Review import results

**File Format Example (CSV):**
```csv
Name,Type,Data,TTL,Zone
www,A,192.168.1.10,3600,example.com
mail,MX,10 mail.example.com,3600,example.com
```

---

### 🔧 Advanced Diagnostic Tools
**Previously:** Only Ping, Nslookup, Resolve
**Now:** Comprehensive diagnostic toolkit

#### New Tools:

1. **Traceroute**
   - Visual hop-by-hop route tracing
   - Uses Test-NetConnection -TraceRoute
   - Shows each router hop to destination

2. **DNS Cache Viewer**
   - Display DNS client cache
   - Shows up to 50 entries (configurable via MaxCacheDisplay)
   - Displays Name, Type, Data, TTL

3. **Clear DNS Cache**
   - One-click cache clearing
   - Uses Clear-DnsClientCache
   - Confirmation message

4. **DNS Benchmark**
   - Performance testing for DNS queries
   - 10 iterations per test
   - Reports: Average, Minimum, Maximum response times
   - Useful for troubleshooting slow DNS resolution

**Tools Menu Layout:**
```
Target: [___________]
[Ping] [Nslookup] [Resolve] [Traceroute]
[DNS Cache] [Clear Cache] [Benchmark]
```

**Benchmark Output Example:**
```
=== Benchmark - example.com ===
Test 1: 12ms
Test 2: 8ms
Test 3: 10ms
...
Test 10: 9ms

Results:
Average: 9.8ms
Minimum: 8ms
Maximum: 12ms
```

---

### ⏰ Auto-Refresh Functionality
**Previously:** Manual refresh only
**Now:** Automatic periodic refresh

- **Settings → Toggle Auto-Refresh** menu option
- Refreshes current view every 5 minutes (300 seconds)
- View-aware: tracks which view is active
- Supported views: Dashboard, Forward Zones, Reverse Zones
- Timer-based implementation using System.Timers.Timer
- Can be toggled on/off at any time

**How It Works:**
- When enabled, starts a timer
- Timer fires every 300 seconds (configurable)
- Automatically re-executes the current view function
- Keeps zone lists and dashboards up-to-date
- Useful for monitoring DNS changes

**Usage:**
1. Settings → Toggle Auto-Refresh
2. Confirmation message appears
3. Current view will refresh every 5 minutes
4. Toggle again to disable

---

## Enhanced Features from v0.3.0

### Button Improvements
- **Records View:** Added Delete and Refresh buttons
- **Reverse Zones:** Added Create button
- **Tool spacing:** Better button layout in diagnostic tools

### Menu Structure
New **Settings** menu added with:
- Auto-refresh toggle

### Error Handling
- Import operations track success/error counts
- Better error messages for all operations
- Confirmation dialogs for destructive operations

---

## Technical Details

### File Locations
```
./Logs/        - Application logs with rotation
./Export/      - Exported DNS records (CSV/JSON/XML)
./Import/      - Import files (place files here)
./Temp/        - Temporary files
```

### Configuration
All settings in `$global:AppConfig`:
- `AutoRefreshInterval`: 300 seconds (5 minutes)
- `MaxCacheDisplay`: 50 entries
- `DefaultTTL`: 3600 seconds
- `SupportedRecordTypes`: A, AAAA, CNAME, MX, PTR, TXT, SRV, NS, SOA

### Auto-Refresh Implementation
```powershell
$global:AutoRefresh = @{
    Enabled = $false
    Timer = $null
    IntervalSeconds = 300
    CurrentView = $null
}
```

---

## Feature Summary by Menu

### File Menu
- ✅ Connect to Server
- ✅ Export Configuration (CSV/JSON/XML)
- ✅ Import Configuration (CSV/JSON/XML)
- ✅ Quit

### Zones Menu
- ✅ Forward Zones (with Create/Delete/Refresh)
- ✅ Reverse Zones (with Create/Refresh)
- ✅ Refresh Zones

### Records
- ✅ View records by zone
- ✅ Create records (A/AAAA/CNAME/TXT)
- ✅ Delete records (NEW)
- ✅ Refresh records list (NEW)

### DNSSEC
- ℹ️ View DNSSEC status
- ℹ️ Note: Signing requires DNS Console

### Tools
- ✅ Ping
- ✅ Nslookup
- ✅ Resolve
- ✅ Traceroute (NEW)
- ✅ DNS Cache viewer (NEW)
- ✅ Clear Cache (NEW)
- ✅ Benchmark (NEW)

### Monitoring
- ⏳ Placeholder (future implementation)

### Settings
- ✅ Toggle Auto-Refresh (NEW)

### Help
- ✅ About
- ✅ Documentation

---

## Requirements

### PowerShell Modules
```powershell
#requires -RunAsAdministrator
#requires -Modules Terminal.Gui
```

### Installation
```powershell
# Install Terminal.Gui
Install-Module Terminal.Gui -Force

# Run the script
.\easyDNS-TUI-v0.4.0.ps1
```

### DNS Server Requirements
- Windows DNS Server (2012 R2+)
- DNS Server PowerShell module
- Local or remote DNS server access
- Administrator privileges

---

## Usage Guide

### First Launch
1. Application auto-detects local DNS server
2. Auto-connects if DNS service is running locally
3. Otherwise, prompts for server connection

### Common Workflows

**Create a Forward Zone:**
1. Zones → Forward Zones
2. Click "Create"
3. Enter zone name (e.g., "contoso.com")
4. Select replication scope
5. Click "Create"

**Create DNS Records:**
1. Records menu
2. Select zone from list
3. Click "Load Records"
4. Click "Create Record"
5. Fill in Name, Type, Data, TTL
6. Click "Create"

**Export Zone Records:**
1. File → Export Configuration
2. Select zone
3. Choose format (CSV recommended for Excel)
4. File saved to Export directory

**Import Records:**
1. Place CSV/JSON/XML file in Import directory
2. File → Import Configuration
3. Select file
4. Specify target zone
5. Review import results

**Run Diagnostics:**
1. Tools menu
2. Enter target hostname/IP
3. Click desired tool button
4. View results in output panel

**Enable Auto-Refresh:**
1. Settings → Toggle Auto-Refresh
2. Current view refreshes every 5 minutes
3. Toggle again to disable

---

## Future Enhancements (Not Yet Implemented)

- 📊 Real-time monitoring view with statistics
- 📝 Audit log viewing
- 🔐 DNSSEC signing operations (requires DNS Console)
- 📈 Advanced analytics and reporting
- 🔄 Zone transfer operations
- 🎯 Conditional forwarder management
- 📱 Query logging and analysis

---

## Troubleshooting

### Import Issues
- **Problem:** Import fails
- **Solution:** Check file format, ensure CSV has headers, verify zone exists

### Auto-Refresh Not Working
- **Problem:** Views don't refresh
- **Solution:** Re-toggle auto-refresh, check logs for errors

### Connection Issues
- **Problem:** Cannot connect to DNS server
- **Solution:** Verify DNS service running, check firewall, ensure admin rights

### Record Deletion Fails
- **Problem:** Cannot delete record
- **Solution:** Check permissions, ensure record exists, view error log

---

## Version History

### v0.4.0 (Current)
- ✅ DNS record deletion
- ✅ Reverse zone creation
- ✅ Import/Export (CSV/JSON/XML)
- ✅ Advanced diagnostic tools (Traceroute, Benchmark, Cache)
- ✅ Auto-refresh functionality
- ✅ Settings menu
- ✅ Enhanced button layouts

### v0.3.0
- Initial Terminal.Gui conversion from WPF
- Basic zone and record management
- Simple diagnostic tools
- Dashboard view

### v0.2.27 (Original WPF)
- Windows 11-style WPF interface
- Comprehensive DNS management

---

## Credits

**Original WPF Version:** easyDNS v0.2.27 by PHscripts.de | Andreas Hepp  
**TUI Conversion:** Claude (Anthropic) with Terminal.Gui  
**License:** Same as original easyDNS  
**Website:** https://github.com/PS-easyIT/

---

## Support

For issues or feature requests:
1. Check logs in `./Logs/` directory
2. Verify DNS server connectivity
3. Ensure Terminal.Gui module is installed
4. Run as Administrator

---

**End of Changelog**
