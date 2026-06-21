# Corporate Livery & User Environment — jukebox.internal

**Document ID:** NET-GPO-LIVERY-001  
**Classification:** Internal — Network Operations  
**Last Updated:** 2026-03-04  
**Depends on:** NET-AD-DC-001 (AD must be deployed and Sites and Services configured)

> All Group Policy configuration is performed from `EXADCSFAL001` using the Group Policy Management Console (GPMC) or PowerShell. GPOs are linked at the domain level unless noted otherwise. Requires Domain Admin or Group Policy Creator Owners membership.

---

## Table of Contents

1. [Overview](#overview)
2. [GPO Structure](#gpo-structure)
3. [Pre-Login Disclaimer](#pre-login-disclaimer)
4. [Corporate Wallpaper](#corporate-wallpaper)
5. [BGInfo](#bginfo)
6. [Home Drive Mapping (H:)](#home-drive-mapping-h)
7. [Login Script](#login-script)
8. [Ansible SSH Key — Windows](#ansible-ssh-key--windows)
9. [Ansible SSH Key — Linux](#ansible-ssh-key--linux)
10. [Verification](#verification)

---

## Overview

This document covers the configuration of the standard jukebox.internal user environment, applied via Group Policy. It covers what users see before they log in (disclaimer), what they see when they log in (wallpaper, BGInfo overlay), and what they get when they log in (home drive, login script).

It also covers deploying the Ansible SSH public key to both Windows and Linux nodes so that Ansible can authenticate without passwords —
currently a manual bootstrap step, intended to be automated once Ansible itself is operational.

**Ansible public key:** `ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCyEVQgZP5f3dSLQ/cK7CV1tjN152BhZGQ7evsOTARTG5o9AmMzn4xFurdvmkFli4dEr7HZ3Dp83jxAMbHJ7d0eVuYNHG1n7ktm4FwYPhzBS3Kni3UvM91TeB6kvNZU1jFVE3oaDlft/C104M5S72zUx9SIzI5XH3fUyssAQEGoEoLzW1u4Tj84pxdXoIdGAGJCZ/gZJJFoPGLNkn3m19ML5EQzIpD4sO6yhODVu7gc9RckFGJpTD1CgKa5q4RPWPMN2y3Xw/J95VTHV8+NCBNKGzoVGdxu1E94+aCV5UCaxvgtLGcjJfv4D8Yrnxd//ZTjFYmT+DdIc6XsgYDYvr7Eoanv+bg8mtVVKxhwsxD3XOoxVdLhvCfYlg9IjXPG65GoTDrZuRfkUA6e1YnEaC4wvyXtwcnMV5NaklwAiIH5VLLo6laK1lyxr1tZEVpYx0F0S9S+oVDRPdpoVH98zE8JkPGWI6xSwaekMUMrAu5fZ/7Dfw2LAwAG7dixMroAj3c= knightmare@ansible`  
**Key URL:** `http://192.168.139.50/ansible_sshkey.pub`

---

## GPO Structure

Rather than cramming everything into one GPO, split by function. This makes troubleshooting, delegation, and rollback much cleaner.

| GPO Name | Linked to | Purpose |
|----------|-----------|---------|
| `JUKEBOX - Security - Login Disclaimer` | Domain | Pre-login message |
| `JUKEBOX - Desktop - Wallpaper` | Domain | Corporate wallpaper via policy |
| `JUKEBOX - Desktop - BGInfo` | Domain | BGInfo overlay via logon script |
| `JUKEBOX - Desktop - Windows 11 Settings` | Domain | Taskbar left, dark mode, no Copilot, no ads, no telemetry |
| `JUKEBOX - Users - Drive Mappings` | Domain | H: home drive |
| `JUKEBOX - Users - Logon Script` | Domain | User logon script |

### Create a New GPO

```powershell
# Run on EXADCSFAL001
Import-Module GroupPolicy

# Create each GPO
$gpos = @(
    "JUKEBOX - Security - Login Disclaimer",
    "JUKEBOX - Desktop - Wallpaper",
    "JUKEBOX - Desktop - BGInfo",
    "JUKEBOX - Desktop - Windows 11 Settings",
    "JUKEBOX - Users - Drive Mappings",
    "JUKEBOX - Users - Logon Script"
)

foreach ($gpo in $gpos) {
    New-GPO -Name $gpo -Domain "jukebox.internal"
    New-GPLink -Name $gpo -Target "DC=jukebox,DC=example" -LinkEnabled Yes
    Write-Host "[+] Created and linked: $gpo"
}
```

### SYSVOL Share Path

GPO files, scripts, and assets live under SYSVOL — accessible from any DC:

```
\\jukebox.internal\SYSVOL\jukebox.internal\Policies\
\\jukebox.internal\SYSVOL\jukebox.internal\scripts\
```

Create a standard scripts folder for logon scripts and BGInfo:

```powershell
$sysvol = "\\jukebox.internal\SYSVOL\jukebox.internal\scripts"
New-Item -ItemType Directory -Path "$sysvol\bginfo"   -Force
New-Item -ItemType Directory -Path "$sysvol\logon"    -Force
New-Item -ItemType Directory -Path "$sysvol\wallpaper" -Force
```

---

## Pre-Login Disclaimer

Displays an acceptable use policy message after Ctrl+Alt+Del, before the password prompt. Configured via the `JUKEBOX - Security - Login Disclaimer` GPO, applied to Computer Configuration so it shows on the machine regardless of which user logs in.

### Via GPMC (GUI)

```
GPO: JUKEBOX - Security - Login Disclaimer
  Computer Configuration
    Policies
      Windows Settings
        Security Settings
          Local Policies
            Security Options
              Interactive logon: Message title for users attempting to log on
              Interactive logon: Message text for users attempting to log on
```

**Suggested title:**
```
IMPORTANT — Authorised Use Only
```

**Suggested message text:**
```
This system is the property of Example Music Group and its subsidiaries.

Access is permitted only to authorised users for authorised business purposes. All activity on this system is monitored and logged. By logging in you confirm that you have read, understood, and agree to comply with the Example Music Group Acceptable Use Policy (AUP).

Unauthorised access or use is prohibited and may result in disciplinary action and/or criminal prosecution under the Computer Misuse Act 1990 and applicable regional legislation.

If you have reached this system in error, disconnect immediately and contact IT Support at: support@example.com
```

### Via PowerShell

```powershell
$gpoName  = "JUKEBOX - Security - Login Disclaimer"
$domain   = "jukebox.internal"

$title = "IMPORTANT — Authorised Use Only"
$message = @"
This system is the property of Example Music Group and its subsidiaries.

Access is permitted only to authorised users for authorised business purposes. All activity on this system is monitored and logged. By logging in you confirm that you have read, understood, and agree to comply with the Example Music Group Acceptable Use Policy (AUP).

Unauthorised access or use is prohibited and may result in disciplinary action and/or criminal prosecution under the Computer Misuse Act 1990 and applicable local legislation.

If you have reached this system in error, disconnect immediately and contact IT Support at: support@example.com
"@

# Set via registry key in the GPO
Set-GPRegistryValue -Name $gpoName -Domain $domain -Key "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" ` 
-ValueName "legalnoticecaption" -Type String -Value $title

Set-GPRegistryValue -Name $gpoName -Domain $domain -Key "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" ` 
-ValueName "legalnoticetext" -Type String -Value $message

Write-Host "[+] Login disclaimer configured"
```

---

## Corporate Wallpaper

Delivered via GPO policy setting — the wallpaper file is stored in SYSVOL so it replicates to all DCs automatically and is always reachable from any domain-joined machine.

### Prepare the Wallpaper File

```powershell
# Copy corporate wallpaper to SYSVOL
# Replace with actual wallpaper file
$wallpaperSource = "C:\wallpaper\corporate-wallpaper.jpg"
$wallpaperDest   = "\\jukebox.internal\SYSVOL\jukebox.internal\scripts\wallpaper\corporate-wallpaper.jpg"

Copy-Item $wallpaperSource $wallpaperDest -Force
Write-Host "[+] Wallpaper deployed to SYSVOL"
```

### Configure via GPMC (GUI)

```
GPO: JUKEBOX - Desktop - Wallpaper
  User Configuration
    Policies
      Administrative Templates
        Desktop
          Desktop
            Desktop Wallpaper
              Enabled
              Wallpaper Name: \\jukebox.internal\SYSVOL\jukebox.internal\scripts\wallpaper\corporate-wallpaper.jpg
              Wallpaper Style: Fill  (or Fit / Stretch as appropriate)
```

### Configure via PowerShell

```powershell
$gpoName      = "JUKEBOX - Desktop - Wallpaper"
$domain       = "jukebox.internal"
$wallpaperPath = "\\jukebox.internal\SYSVOL\jukebox.internal\scripts\wallpaper\corporate-wallpaper.jpg"

# Wallpaper path
Set-GPRegistryValue -Name $gpoName -Domain $domain -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System" ` 
-ValueName "Wallpaper" -Type String -Value $wallpaperPath

# Wallpaper style: 0=Centre, 2=Stretch, 6=Fit, 10=Fill, 22=Span
Set-GPRegistryValue -Name $gpoName -Domain $domain -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System" ` 
-ValueName "WallpaperStyle" -Type String -Value "10"

Write-Host "[+] Wallpaper policy configured"
```

> **Note:** Setting wallpaper via `Policies\System` prevents users from changing it through Display Settings. If you want users to be able to change it (policy as default rather than enforced), use `HKCU\Control Panel\Desktop` instead.

---

## BGInfo

BGInfo overlays system information (hostname, IP, OS version, last boot, logged-in user etc) directly onto the wallpaper. It runs as a logon script so the overlay is always current. BGInfo itself is a single portable executable — no installation required.

### Prepare BGInfo

1. Download `BGInfo.exe` from Sysinternals (or deploy from SCCM/Intune).
2. Create a BGInfo configuration file (`.bgi`) with the fields you want.
3. Copy both to SYSVOL:

```powershell
$bgInfoDir = "\\jukebox.internal\SYSVOL\jukebox.internal\scripts\bginfo"

Copy-Item "C:\tools\BGInfo.exe"       "$bgInfoDir\BGInfo.exe"  -Force
Copy-Item "C:\tools\jukebox.bgi"      "$bgInfoDir\jukebox.bgi" -Force

Write-Host "[+] BGInfo deployed to SYSVOL"
```

### BGInfo Logon Script

Create `\\jukebox.internal\SYSVOL\jukebox.internal\scripts\logon\bginfo.cmd`:

```batch
@echo off
REM BGInfo — run silently at logon, timeout 0 (no user prompt), all users
"\\jukebox.internal\SYSVOL\jukebox.internal\scripts\bginfo\BGInfo.exe" ^
    "\\jukebox.internal\SYSVOL\jukebox.internal\scripts\bginfo\jukebox.bgi" ^
    /silent /accepteula /timer:0
```

### Attach Script to GPO via GPMC (GUI)

```
GPO: JUKEBOX - Desktop - BGInfo
  User Configuration
    Policies
      Windows Settings
        Scripts (Logon/Logoff)
          Logon
            Add → bginfo.cmd
```

### Attach Script to GPO via PowerShell

```powershell
# Get the GPO GUID
$gpo    = Get-GPO -Name "JUKEBOX - Desktop - BGInfo" -Domain "jukebox.internal"
$gpoId  = $gpo.Id.ToString().ToUpper()

# Path to the GPO's user logon scripts folder in SYSVOL
$scriptDir = "\\jukebox.internal\SYSVOL\jukebox.internal\Policies\{$gpoId}\User\Scripts\Logon"
New-Item -ItemType Directory -Path $scriptDir -Force | Out-Null

# Copy bginfo.cmd into the GPO scripts folder
Copy-Item "\\jukebox.internal\SYSVOL\jukebox.internal\scripts\logon\bginfo.cmd" "$scriptDir\bginfo.cmd" -Force

# Write the scripts.ini that tells Windows about the logon script
$scriptsIni = "$scriptDir\scripts.ini"
@"
[Logon]
0CmdLine=bginfo.cmd
0Parameters=
"@ | Set-Content -Path $scriptsIni -Encoding Unicode

Write-Host "[+] BGInfo logon script attached to GPO"
```

### Suggested BGInfo Fields

Open `BGInfo.exe`, click Fields, and add:

| Field | Description |
|-------|-------------|
| `Host Name` | Machine hostname |
| `IP Address` | Primary IP |
| `Default Gateway` | Gateway |
| `OS` | Windows version |
| `Service Pack` | Patch level |
| `Boot Time` | Last reboot |
| `User Name` | Logged-in user |
| `Domain` | AD domain |
| `RAM` | Total memory |
| `CPU` | Processor |

Save as `jukebox.bgi`. Set background to semi-transparent black, font to white Segoe UI, position to bottom-left.

---

## Home Drive Mapping (H:)

Home drives are mapped to `\\jukebox.internal\homes\%username%` via Group Policy Preferences (GPP) Drive Maps. GPP drive maps are more flexible than legacy logon scripts — they support item-level targeting, reconnect on next logon, and show up in File Explorer with a label.

> **Pre-requisite:** The `homes` DFS namespace and underlying share on the SRV nodes must exist before enabling this policy. See `dfs-replication.md` for the share and namespace setup. Until the SRV nodes are built, comment out or disable this GPO.

### Configure via GPMC (GUI)

```
GPO: JUKEBOX - Users - Drive Mappings
  User Configuration
    Preferences
      Windows Settings
        Drive Maps
          New → Mapped Drive
            Action:    Create  (use Update once stable)
            Location:  \\jukebox.internal\homes\%username%
            Label:     Home (H:)
            Drive:     H:
            Reconnect: Checked
```

### Configure via PowerShell

GPP Drive Maps are stored as XML in the GPO — the cleanest way to set them is to write the XML directly to the GPO's Preferences folder in SYSVOL:

```powershell
$gpo   = Get-GPO -Name "JUKEBOX - Users - Drive Mappings" -Domain "jukebox.internal"
$gpoId = $gpo.Id.ToString().ToUpper()

$prefDir = "\\jukebox.internal\SYSVOL\jukebox.internal\Policies\{$gpoId}\User\Preferences\Drives"
New-Item -ItemType Directory -Path $prefDir -Force | Out-Null

# GPP Drive Map XML — Action C=Create, thisDrive H, label "Home (H:)"
$drivesXml = @'
<?xml version="1.0" encoding="UTF-8"?>
<Drives clsid="{8FDDCC1A-0C3C-43cd-A6B4-71A6DF20DA8C}">
  <Drive clsid="{935D1B74-9CB8-4e3c-9914-7DD559B7A417}"
         name="H:"
         status="H:"
         image="2"
         changed="2026-03-04 00:00:00"
         uid="{00000000-0000-0000-0000-000000000001}"
         bypassErrors="1">
    <Properties action="C"
                thisDrive="H"
                allDrives="NOCHANGE"
                userName=""
                path="\\jukebox.internal\homes\%username%"
                label="Home (H:)"
                persistent="1"
                useLetter="1"
                letter="H"/>
  </Drive>
</Drives>
'@

$drivesXml | Set-Content -Path "$prefDir\Drives.xml" -Encoding UTF8
Write-Host "[+] H: drive map written to GPO preferences"
```

---

## Login Script

A user logon script handles any tasks that GPP cannot — legacy application compatibility, per-user environment variables, etc. BGInfo is handled by its own GPO (see above), so this script is a general-purpose hook.

Create `\\jukebox.internal\SYSVOL\jukebox.internal\scripts\logon\logon.ps1`:

```powershell
# jukebox.internal — User Logon Script
# Runs in user context at logon via GPO
# Add per-user tasks here as required

# Example: set HOME environment variable to H: drive
[System.Environment]::SetEnvironmentVariable("HOME", "H:\", "User")

# Example: set time zone (useful for roaming users)
# Set-TimeZone -Id "GMT Standard Time"

# Example: map a printer (uncomment and adjust when print servers exist)
# Add-Printer -ConnectionName "\\printserver.jukebox.internal\Reception-HP"

Write-EventLog -LogName Application -Source "Logon Script" `
    -EventId 1000 -EntryType Information `
    -Message "Logon script completed for $env:USERNAME on $env:COMPUTERNAME"
```

### Attach to GPO

```
GPO: JUKEBOX - Users - Logon Script
  User Configuration
    Policies
      Windows Settings
        Scripts (Logon/Logoff)
          Logon
            PowerShell Scripts tab
              Add → logon.ps1
```

Or via the same `scripts.ini` method shown in the BGInfo section, using the `JUKEBOX - Users - Logon Script` GPO GUID.

### Allow PowerShell Logon Scripts

By default, PowerShell execution policy may block logon scripts. Set via GPO so it applies before the script runs:

```
GPO: JUKEBOX - Users - Logon Script
  Computer Configuration
    Policies
      Administrative Templates
        Windows Components
          Windows PowerShell
            Turn on Script Execution
              Enabled
              Execution Policy: Allow all scripts
              (or: Allow local scripts and remote signed scripts)
```

---

## Ansible SSH Key — Windows

On Windows, OpenSSH stores authorised keys in two different locations depending on whether the account is a member of the local Administrators group. **This is the most common gotcha with OpenSSH on Windows.**

| Account type | Authorised keys file |
|---|---|
| Standard user | `C:\Users\<username>\.ssh\authorized_keys` |
| Local Administrators group member | `C:\ProgramData\ssh\administrators_authorized_keys` |

Because `Administrator` is in the Administrators group, the key **must** go in `administrators_authorized_keys` — the per-user file is ignored for admin accounts. The file also has strict permission requirements: it must be owned by `SYSTEM` or `Administrators`, and no other accounts may have write access.

### Deploy the Key (per node — run as Administrator)

```powershell
# Run on each Windows node (DC, SRV, etc) as local Administrator

# Fetch the public key from the provisioning server
$keyUrl  = "http://192.168.139.50/ansible_sshkey.pub"
$keyFile = "$env:ProgramData\ssh\administrators_authorized_keys"

# Create the SSH directory if it doesn't exist
$sshDir = "$env:ProgramData\ssh"
if (-not (Test-Path $sshDir)) { New-Item -ItemType Directory -Path $sshDir -Force | Out-Null }

# Fetch and write the key
$key = (Invoke-WebRequest -Uri $keyUrl -UseBasicParsing).Content.Trim()
Set-Content -Path $keyFile -Value $key -Encoding UTF8

Write-Host "[+] Key written to $keyFile"

# Fix permissions — this file must be locked down or OpenSSH ignores it
# Remove all inherited permissions and set explicit ACL
$acl = New-Object System.Security.AccessControl.FileSecurity
$acl.SetAccessRuleProtection($true, $false)  # disable inheritance, remove inherited

# SYSTEM — Full Control
$acl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule("NT AUTHORITY\SYSTEM", "FullControl", "Allow")))

# Administrators — Full Control
$acl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule("BUILTIN\Administrators", "FullControl", "Allow")))

Set-Acl -Path $keyFile -AclObject $acl
Write-Host "[+] Permissions set on $keyFile"

# Verify OpenSSH is running and will pick up the change
Get-Service sshd | Select-Object Name, Status, StartType
Write-Host "[+] Done — test with: ssh Administrator@<this-node-ip>"
```

### Verify the Key Works

```powershell
# From the Ansible control node or any Linux host with the private key:
ssh -i ~/.ssh/ansible_key Administrator@192.168.76.10

# Or with verbose output to diagnose failures:
ssh -v -i ~/.ssh/ansible_key Administrator@192.168.76.10
```

### Common Failure: Wrong File Location

If SSH accepts the password but rejects the key, the key is almost certainly in the wrong file. Check the OpenSSH server log:

```powershell
# On the Windows node
Get-EventLog -LogName "OpenSSH/Operational" -Newest 20

# Or check the sshd log directly
Get-Content "$env:ProgramData\ssh\logs\sshd.log" -Tail 50
```

Look for: `AuthorizedKeysFile` — it will show you which file it tried. If it says `C:\Users\Administrator\.ssh\authorized_keys` the `sshd_config` is not pointing at the administrators file. Check:

```powershell
Get-Content "$env:ProgramData\ssh\sshd_config" | Select-String "AuthorizedKeys"
```

It will include:

```
AuthorizedKeysFile __PROGRAMDATA__/ssh/administrators_authorized_keys
```

If this line is commented out, uncomment it and restart sshd:

```powershell
Restart-Service sshd
```

---

## Ansible SSH Key — Linux

On Linux nodes the ansible user was created by the firstboot script (for PVE nodes) or needs to be created manually on other nodes. The key is added to `~ansible/.ssh/authorized_keys`.

### PVE Nodes (firstboot script already ran)

The firstboot script creates the ansible user and fetches the key automatically from the provisioning server. Verify it worked:

```bash
# On the PVE node
sudo cat /home/ansible/.ssh/authorized_keys

# Should contain:
# ssh-rsa AAAAB3NzaC1yc2E... knightmare@ansible

# Test login from Ansible control node:
ssh -i ~/.ssh/ansible_key ansible@192.168.76.5
```

### Other Linux Nodes (manual bootstrap)

For any Linux node where the firstboot script did not run:

```bash
# Run as root on the target node

KEY_URL="http://192.168.139.50/ansible_sshkey.pub"

# Create ansible user if it doesn't exist
id ansible &>/dev/null || useradd -m -s /bin/bash ansible
echo "ansible ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ansible
chmod 0440 /etc/sudoers.d/ansible

# Set up SSH directory
mkdir -p /home/ansible/.ssh
chmod 700 /home/ansible/.ssh

# Fetch and install the key
wget -qO - "$KEY_URL" >> /home/ansible/.ssh/authorized_keys
chmod 600 /home/ansible/.ssh/authorized_keys
chown -R ansible:ansible /home/ansible/.ssh

echo "[+] Ansible key installed for ansible@$(hostname)"
```

### Verify

```bash
# From Ansible control node
ssh -i ~/.ssh/ansible_key ansible@<node-ip>

# Should drop straight to a shell without a password prompt
# Confirm sudo works:
sudo whoami   # should return: root
```

### Firewall VMs (Debian — wg-quick nodes)

Same procedure as above. If the node uses `ufw`:

```bash
# Ensure SSH is allowed before locking anything down
ufw allow 22/tcp
ufw status
```

---

## Verification

### Check GPO Application on a Workstation

```powershell
# Force GPO refresh
gpupdate /force

# Show all applied GPOs and their status
gpresult /r

# Full HTML report — open in browser
gpresult /h C:\Temp\gpresult.html
Start-Process C:\Temp\gpresult.html
```

### Check GPO Replication Across DCs

```powershell
# Run on EXADCSFAL001
# Confirms SYSVOL is replicating to all DCs
Get-DfsrBacklog -GroupName "Domain System Volume" `
    -FolderName "SYSVOL Share" `
    -SourceComputerName EXADCSFAL001 `
    -DestinationComputerName EXADCSODE001

# Also check repadmin for GPO-relevant partitions
repadmin /showrepl
```

### Check Individual GPO Settings

```powershell
# Dump all settings for a specific GPO
Get-GPOReport -Name "JUKEBOX - Security - Login Disclaimer" `
    -ReportType HTML -Path C:\Temp\disclaimer-gpo.html
Start-Process C:\Temp\disclaimer-gpo.html
```

### Test Login Disclaimer

Log out of a domain-joined machine and press Ctrl+Alt+Del. The disclaimer title and message should appear before the password field. If it does not:

1. Run `gpupdate /force` and try again
2. Check `gpresult /r` to confirm the GPO is applied to the machine
3. Verify the GPO is linked at domain level and not blocked by a parent OU
4. Check the registry directly:

```powershell
Get-ItemProperty `
    -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" `
    -Name legalnoticecaption, legalnoticetext
```

---

## Windows 11 Desktop Policies

These settings are delivered via a dedicated GPO to keep them separate from wallpaper and BGInfo — easier to roll back if Microsoft breaks something in a feature update (which happens).

```
GPO: JUKEBOX - Desktop - Windows 11 Settings
  Linked to: Domain
```

```powershell
New-GPO -Name "JUKEBOX - Desktop - Windows 11 Settings" -Domain "jukebox.internal"
New-GPLink -Name "JUKEBOX - Desktop - Windows 11 Settings" `
    -Target "DC=jukebox,DC=example" -LinkEnabled Yes
```

---

### Taskbar Alignment — Start Menu on the Left

Windows 11 defaults to centring the Start button and taskbar icons. This moves everything back to the left.

```
GPO: JUKEBOX - Desktop - Windows 11 Settings
  User Configuration
    Policies
      Administrative Templates
        Start Menu and Taskbar
          Configure the taskbar alignment
            Enabled → Taskbar alignment: Left
```

```powershell
$gpo    = "JUKEBOX - Desktop - Windows 11 Settings"
$domain = "jukebox.internal"

Set-GPRegistryValue -Name $gpo -Domain $domain `
    -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" `
    -ValueName "TaskbarAl" `
    -Type DWord -Value 0   # 0 = Left, 1 = Centre (default)
```

---

### Dark Mode — System Default

Sets the Windows colour scheme to dark for both the system UI and apps. Applied as a sensible default — users can change it via Settings > Personalisation > Colours if they prefer light mode.

> To enforce dark mode and prevent users changing it, move these keys to `Computer Configuration` and add a registry lock policy. For now they sit in User Configuration as a default.

```powershell
# System theme — dark
Set-GPRegistryValue -Name $gpo -Domain $domain `
    -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize" `
    -ValueName "SystemUsesLightTheme" `
    -Type DWord -Value 0   # 0 = Dark, 1 = Light

# App theme — dark
Set-GPRegistryValue -Name $gpo -Domain $domain `
    -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize" `
    -ValueName "AppsUseLightTheme" `
    -Type DWord -Value 0   # 0 = Dark, 1 = Light
```

---

### Taskbar Search — Hide Search Box and Disable Search Highlights

Removes the search box from the taskbar entirely and disables the daily-changing search highlights graphic (the illustrated icon that appears when search is visible).

```
GPO: JUKEBOX - Desktop - Windows 11 Settings
  User Configuration
    Policies
      Administrative Templates
        Start Menu and Taskbar
          Search
            Configures search on the taskbar
              Enabled → Hide
            Allow search highlights
              Disabled
```

```powershell
# Hide taskbar search box entirely
# 0 = Hidden, 1 = Show search icon, 2 = Show search icon and label, 3 = Show search box
Set-GPRegistryValue -Name $gpo -Domain $domain `
    -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\Search" `
    -ValueName "SearchboxTaskbarMode" `
    -Type DWord -Value 0

# Disable search highlights (the daily illustrated icon)
Set-GPRegistryValue -Name $gpo -Domain $domain `
    -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\Feeds\DSB" `
    -ValueName "ShowDynamicContent" `
    -Type DWord -Value 0
```

---

### Disable Copilot

Two separate policies — the Copilot sidebar/button in the taskbar, and the dedicated Copilot hardware key on newer keyboards. Both are disabled.

#### Copilot Sidebar and Taskbar Button

```
GPO: JUKEBOX - Desktop - Windows 11 Settings
  User Configuration
    Policies
      Administrative Templates
        Windows Components
          Windows Copilot
            Turn off Windows Copilot
              Enabled
```

```powershell
# Disable Copilot sidebar
Set-GPRegistryValue -Name $gpo -Domain $domain `
    -Key "HKCU\Software\Policies\Microsoft\Windows\WindowsCopilot" `
    -ValueName "TurnOffWindowsCopilot" `
    -Type DWord -Value 1

# Remove Copilot button from taskbar
Set-GPRegistryValue -Name $gpo -Domain $domain `
    -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" `
    -ValueName "ShowCopilotButton" `
    -Type DWord -Value 0
```

#### Copilot Hardware Key

Disables the dedicated Copilot key present on some Windows 11 keyboards (Copilot+ PCs and newer OEM hardware). Without this, the key launches Copilot even if the sidebar is disabled via policy.

```
GPO: JUKEBOX - Desktop - Windows 11 Settings
  Computer Configuration
    Policies
      Administrative Templates
        Windows Components
          Windows Copilot
            Disable the Copilot hardware key
              Enabled
```

```powershell
# Note: Computer Configuration — applies machine-wide regardless of user
Set-GPRegistryValue -Name $gpo -Domain $domain `
    -Key "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot" `
    -ValueName "DisableCopilotHardwareKey" `
    -Type DWord -Value 1
```

---

### Disable Telemetry

Controls how much diagnostic data Windows sends to Microsoft.

> **SKU note:** Level 0 (Security — off completely) only applies to Windows Enterprise and Education editions. On Pro, the minimum enforced level is 1 (Basic). Both are documented below — use whichever matches your licence.

```
GPO: JUKEBOX - Desktop - Windows 11 Settings
  Computer Configuration
    Policies
      Administrative Templates
        Windows Components
          Data Collection and Preview Builds
            Allow Diagnostic Data
              Enabled
              Options: Diagnostic data off (not recommended)  ← Enterprise/Education only
              Options: Send required diagnostic data          ← Pro minimum
```

```powershell
# Telemetry level
# 0 = Off       (Enterprise/Education only — enforced as 1 on Pro)
# 1 = Basic / Required diagnostic data
# 2 = Enhanced  (removed in Windows 11 — maps to Basic)
# 3 = Full
Set-GPRegistryValue -Name $gpo -Domain $domain -Key "HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection" `
    -ValueName "AllowTelemetry" -Type DWord -Value 0   # Use 1 if not on Enterprise/Education

# Disable Connected User Experiences and Telemetry service
Set-GPRegistryValue -Name $gpo -Domain $domain -Key "HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection" `
    -ValueName "DisableEnterpriseAuthProxy" -Type DWord -Value 1

# Disable feedback notifications ("How satisfied are you with Windows?")
Set-GPRegistryValue -Name $gpo -Domain $domain -Key "HKCU\Software\Microsoft\Siuf\Rules" -ValueName "NumberOfSIUFInPeriod" -Type DWord -Value 0
```

---

### Disable Start Menu Ads and Suggested Content

Removes "suggested apps", sponsored content, tips, and "Get even more
out of Windows" prompts from the Start menu and Settings app.

```powershell
# Disable Start menu suggested apps / sponsored content
Set-GPRegistryValue -Name $gpo -Domain $domain -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" `
    -ValueName "SystemPaneSuggestionsEnabled" -Type DWord -Value 0

# Disable app suggestions in Start menu
Set-GPRegistryValue -Name $gpo -Domain $domain -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" `
    -ValueName "SubscribedContent-338388Enabled" -Type DWord -Value 0

# Disable tips and suggestions in Settings
Set-GPRegistryValue -Name $gpo -Domain $domain -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" `
    -ValueName "SubscribedContent-338389Enabled" -Type DWord -Value 0

# Disable "Get even more out of Windows" suggestions
Set-GPRegistryValue -Name $gpo -Domain $domain -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" `
    -ValueName "SubscribedContent-353694Enabled" -Type DWord -Value 0

# Disable Microsoft account promotional notifications
Set-GPRegistryValue -Name $gpo -Domain $domain -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" `
    -ValueName "SubscribedContent-353696Enabled" -Type DWord -Value 0

# Disable lock screen ads / Spotlight suggestions
Set-GPRegistryValue -Name $gpo -Domain $domain -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" `
    -ValueName "RotatingLockScreenOverlayEnabled" -Type DWord -Value 0

Set-GPRegistryValue -Name $gpo -Domain $domain -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" `
    -ValueName "SubscribedContent-338387Enabled" -Type DWord -Value 0
```

---

### Apply All Windows 11 Settings — Combined Script

Run this once to set all of the above in one pass:

```powershell
# Run on EXADCSFAL001 — sets all Windows 11 desktop policies in one go

$gpo    = "JUKEBOX - Desktop - Windows 11 Settings"
$domain = "jukebox.internal"

$settings = @(
  # Start menu left
  @{ Key="HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"; Name="TaskbarAl"; Value=0 }

  # Dark mode
  @{ Key="HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"; Name="SystemUsesLightTheme"; Value=0 }
  @{ Key="HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"; Name="AppsUseLightTheme"; Value=0 }

  # Hide search box and disable highlights
  @{ Key="HKCU\Software\Microsoft\Windows\CurrentVersion\Search"; Name="SearchboxTaskbarMode"; Value=0 }
  @{ Key="HKCU\Software\Microsoft\Windows\CurrentVersion\Feeds\DSB"; Name="ShowDynamicContent"; Value=0 }

  # Copilot — user
  @{ Key="HKCU\Software\Policies\Microsoft\Windows\WindowsCopilot"; Name="TurnOffWindowsCopilot"; Value=1 }
  @{ Key="HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"; Name="ShowCopilotButton"; Value=0 }

  # Telemetry — feedback
  @{ Key="HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection"; Name="AllowTelemetry"; Value=0 }
  @{ Key="HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection"; Name="DisableEnterpriseAuthProxy"; Value=1 }
  @{ Key="HKCU\Software\Microsoft\Siuf\Rules"; Name="NumberOfSIUFInPeriod"; Value=0 }

  # Copilot hardware key — machine-wide
  @{ Key="HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot"; Name="DisableCopilotHardwareKey"; Value=1 }

  # Start menu ads and suggestions
  @{ Key="HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name="SystemPaneSuggestionsEnabled"; Value=0 }
  @{ Key="HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name="SubscribedContent-338388Enabled"; Value=0 }
  @{ Key="HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name="SubscribedContent-338389Enabled"; Value=0 }
  @{ Key="HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name="SubscribedContent-353694Enabled"; Value=0 }
  @{ Key="HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name="SubscribedContent-353696Enabled"; Value=0 }
  @{ Key="HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name="RotatingLockScreenOverlayEnabled"; Value=0 }
  @{ Key="HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; Name="SubscribedContent-338387Enabled"; Value=0 }
)

foreach ($s in $settings) {
  Set-GPRegistryValue -Name $gpo -Domain $domain -Key $s.Key -ValueName $s.Name -Type DWord -Value $s.Value
  Write-Host "[+] Set $($s.Name) = $($s.Value)"
}

Write-Host "`n[+] All Windows 11 desktop policies applied to GPO: $gpo"
```

### Verify on a Test Machine

```powershell
# Force GPO refresh on a Windows 11 test workstation
gpupdate /force

# Confirm registry values applied
$checks = @(
  "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced\TaskbarAl",
  "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize\AppsUseLightTheme",
  "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search\SearchboxTaskbarMode",
  "HKCU:\Software\Policies\Microsoft\Windows\WindowsCopilot\TurnOffWindowsCopilot",
  "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection\AllowTelemetry"
)

foreach ($path in $checks) {
  $key  = Split-Path $path
  $name = Split-Path $path -Leaf
  $val  = (Get-ItemProperty -Path $key -Name $name -ErrorAction SilentlyContinue).$name
  Write-Host "$name = $val"
}
```

> **Note on Windows Updates:** Microsoft has a habit of re-enabling some of these settings (particularly ContentDeliveryManager and Copilot) after major feature updates. If settings revert after a Windows Update, run `gpupdate /force` again — the GPO will re-apply them. If the policy keys themselves have changed, check the ADMX templates are up to date on your DCs (`%SystemRoot%\PolicyDefinitions\`).

---

## Related Documents

| Document | Relationship |
|----------|-------------|
| `bootstrap/ad-dc-wireguard-deployment.md` | AD must be deployed before any GPO work |
| `dfs-replication.md` | H: drive mapping depends on DFS namespace and SRV shares |
| `buildsheets/buildsheet-dcs.md` | RSAT tools must be installed before GPMC is available |
| `network-inventory.md` | Node IPs for SSH key verification |

---

*Internal Use Only — Network Engineering — jukebox.internal*
